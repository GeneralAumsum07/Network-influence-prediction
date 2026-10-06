"""Focused no-fit checks for the structural-tier bootstrap runner."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import probe_structural_target_noise_refit as mod


class StructuralTargetNoiseTests(unittest.TestCase):
    def provenance(self, reps=1):
        config = {"reps": reps, "tier": mod.FULL}
        return {"configuration": config,
                "configuration_sha256": mod.stable_digest(config),
                "input_sha256": {"fixture": "abc"},
                "resample_index_sha256": {network: [f"{network}-rep-0"]
                                            for network in mod.NETWORKS},
                "alignment": {network: {"structural_feature_counts":
                                          {str(radius): 1 for radius in mod.RADII}}
                              for network in mod.NETWORKS}}

    def completed_row(self, provenance, **changes):
        row = {"network": "ca-GrQc", "target": "spread_mean", "radius": 0,
               "tier": mod.FULL, "rep": 0, "tau_refit": .1, "n_features": 1,
               "configuration_sha256": provenance["configuration_sha256"],
               "resample_sha256": "ca-GrQc-rep-0"}
        row.update(changes)
        row["row_sha256"] = mod.result_row_digest(row)
        return row

    def test_resample_identity_is_deterministic_and_shared_by_design(self):
        first = mod.replicate_indices(11, 3, 0)
        second = mod.replicate_indices(11, 3, 0)
        self.assertEqual([mod.index_digest(v) for v in first],
                         [mod.index_digest(v) for v in second])
        # There is one vector per replicate, before any target/radius loop.
        self.assertEqual(len(first), 3)
        self.assertEqual(first[0].shape, (11,))

    def test_structural_selection_excludes_dynamic_features(self):
        registry = pd.DataFrame({"feature": ["node0", "edge1", "sub2", "dyn0"],
                                 "hop": [0, 1, 2, 0],
                                 "tier": ["node", "edge", "subgraph", "dynamic"]})
        features = pd.DataFrame({"node0": [0.], "edge1": [0.],
                                 "sub2": [0.], "dyn0": [0.]})
        self.assertEqual(mod.structural_features(registry, features, 0), ["node0"])
        self.assertEqual(mod.structural_features(registry, features, 2),
                         ["node0", "edge1", "sub2"])

    def test_matching_sweep_requires_exact_ten_seeds(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "sweep.csv"
            # The runner compares registry-derived structural column counts with
            # the headline sweep.  Include a stable fixture count because the
            # production sweep intentionally requires that evidence.
            rows = [(target, radius, mod.FULL, seed, .1, 2)
                    for target in mod.MC_TARGETS for radius in mod.RADII
                    for seed in range(10)]
            pd.DataFrame(rows, columns=["target", "radius", "richness", "seed",
                                        "kendall_tau", "n_features"]).to_csv(path, index=False)
            mod.validate_sweep(path)
            pd.read_csv(path).drop(columns=["n_features"]).to_csv(path, index=False)
            with self.assertRaises(ValueError):
                mod.validate_sweep(path)
            pd.DataFrame(rows, columns=["target", "radius", "richness", "seed",
                                        "kendall_tau", "n_features"]).to_csv(path, index=False)
            pd.read_csv(path).iloc[:-1].to_csv(path, index=False)
            with self.assertRaises(ValueError):
                mod.validate_sweep(path)

    def test_resume_rejects_changed_provenance_and_duplicate_cells(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            out, prov_path = root / "out.csv", root / "provenance.json"
            provenance = self.provenance()
            empty, done = mod.load_resume(out, prov_path, provenance, 1)
            self.assertTrue(empty.empty)
            self.assertFalse(done)
            row = pd.DataFrame([self.completed_row(provenance)])
            mod.atomic_csv(row, out)
            _, done = mod.load_resume(out, prov_path, provenance, 1)
            self.assertEqual(done, {("ca-GrQc", "spread_mean", 0, 0)})
            changed = json.loads(json.dumps(provenance))
            changed["input_sha256"]["fixture"] = "different"
            with self.assertRaises(RuntimeError):
                mod.load_resume(out, prov_path, changed, 1)
            mod.atomic_csv(pd.concat([row, row], ignore_index=True), out)
            with self.assertRaises(ValueError):
                mod.load_resume(out, prov_path, provenance, 1)

    def test_resume_rejects_row_payload_corruption_and_wrong_feature_count(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            out, prov_path = root / "out.csv", root / "provenance.json"
            provenance = self.provenance()
            mod.load_resume(out, prov_path, provenance, 1)
            clean = self.completed_row(provenance)
            for changes in ({"tau_refit": .2}, {"n_features": 2}):
                # Apply the change after digest construction: this models an
                # accidental text edit, which the row-local digest must expose.
                broken = dict(clean)
                broken.update(changes)
                mod.atomic_csv(pd.DataFrame([broken]), out)
                with self.subTest(changes=changes):
                    with self.assertRaises(ValueError):
                        mod.load_resume(out, prov_path, provenance, 1)
            # A recomputed digest cannot excuse an incompatible feature set;
            # provenance alignment binds that field independently.
            wrong_count = self.completed_row(provenance, n_features=2)
            mod.atomic_csv(pd.DataFrame([wrong_count]), out)
            with self.assertRaises(ValueError):
                mod.load_resume(out, prov_path, provenance, 1)

    def test_resume_requires_both_checkpoint_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            out, prov_path = root / "out.csv", root / "provenance.json"
            provenance = self.provenance()
            mod.atomic_json(provenance, prov_path)
            with self.assertRaises(RuntimeError):
                mod.load_resume(out, prov_path, provenance, 1)

    def test_resume_accepts_json_tuple_round_trip(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            out, prov_path = root / "out.csv", root / "provenance.json"
            provenance = self.provenance()
            # Real preflight provenance contains tuple-valued fixed scope.
            provenance["configuration"]["networks"] = mod.NETWORKS
            provenance["configuration"]["radii"] = mod.RADII
            mod.load_resume(out, prov_path, provenance, 1)
            row = pd.DataFrame([self.completed_row(provenance)])
            mod.atomic_csv(row, out)
            _, done = mod.load_resume(out, prov_path, provenance, 1)
            self.assertEqual(done, {("ca-GrQc", "spread_mean", 0, 0)})

    def test_resume_preserves_high_precision_tau_through_csv(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            out, prov_path = root / "out.csv", root / "provenance.json"
            provenance = self.provenance()
            mod.load_resume(out, prov_path, provenance, 1)
            row = pd.DataFrame([self.completed_row(provenance,
                                                    tau_refit=.9334276102646076)])
            mod.atomic_csv(row, out)
            restored, _ = mod.load_resume(out, prov_path, provenance, 1)
            self.assertEqual(float(restored.iloc[0].tau_refit), .9334276102646076)


if __name__ == "__main__":
    unittest.main(verbosity=2)

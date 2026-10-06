"""Deterministic verifier for the Phase 6 radius-one structural ablation.

Created 2026-09-10 by Claude Opus 5 for Phase 6 Task 5 (r=1 ablation scope gap).

CONTRACT: this file must never fit the five-network corpus. It may read the real
caches read-only to check the feature contract, but it must not call
`out_of_fold_predictions`, `RandomForestRegressor.fit`, any cache writer or any
training script. That is what makes it safe to run before the fitting lane, and
it is asserted by `test_verifier_does_not_train` below.
"""
from __future__ import annotations

import json
import sys
import unittest
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from influence.r1_ablation import (  # noqa: E402
    NETWORKS,
    ORBIT_INDEX_SPLIT,
    R1ContractError,
    SEEDS,
    SET_IDS,
    TARGETS,
    assert_full_set_matches_select_features,
    canonical_sha256,
    cell_name,
    expected_keys,
    fold_digest,
    objective_for,
    require_finite,
    select_r1_sets,
    sort_key,
)

# Expected set sizes, from the brief's inspection of the five live registries.
# 2026-09-12, Claude Opus 5: top rung repinned 62 -> 56. Task 6 finding P1-01
# retagged six 5-node orbits (56, 57, 65, 66, 68, 70) from hop 1 to hop 2 in
# every cache_registry_*.csv on 2026-09-11, so `full_r1_structural` now holds
# 56 columns. The registry is the authority; this pin records it, and the
# pre-retag 800-cell run is archived under
# results/phase6_r1_ablation_pre_orbit5_retag_20260910/.
EXPECTED_SIZES = (38, 40, 45, 56)


def _synthetic_registry() -> tuple[pd.DataFrame, pd.DataFrame]:
    """A tiny registry exercising every classification branch at once.

    Deliberately includes `eorbit_02_x`: an EDGE-tier name that starts with a
    string a careless regex would treat as a node orbit. If it ever leaves Set 1
    the whole ladder is wrong, so it is pinned here rather than trusted.
    """
    rows = [
        ("degree", 0, "node"),
        ("boundary_porosity", 1, "edge"),
        ("eorbit_02_x", 1, "edge"),            # edge tier, NOT a node orbit
        ("ego_betweenness", 1, "subgraph"),    # non-orbit subgraph
        ("triangle_count", 1, "subgraph"),     # non-orbit subgraph
        ("orbit_02_P3_centre", 1, "subgraph"),  # index 2  -> Set 3
        ("orbit_23_g5", 1, "subgraph"),        # index 23 -> Set 4
        ("spread_cv_neighbourhood", 1, "dynamic"),  # excluded entirely
        ("deep_thing", 2, "subgraph"),         # hop 2 -> out of scope
    ]
    registry = pd.DataFrame(rows, columns=["feature", "hop", "tier"])
    features = pd.DataFrame({name: np.arange(4, dtype=float) for name, _, _ in rows})
    return features, registry


class R1ContractTests(unittest.TestCase):
    """Task 1: the pure contract."""

    def test_synthetic_membership_places_every_branch_correctly(self):
        features, registry = _synthetic_registry()
        sets = select_r1_sets(features, registry)

        self.assertEqual(sets["node_edge"], ["degree", "boundary_porosity", "eorbit_02_x"])
        self.assertIn("eorbit_02_x", sets["node_edge"],
                      "an edge-tier eorbit_ name must stay in the common baseline")

        # orbit_02 enters only at Set 3; orbit_23 only at Set 4.
        self.assertNotIn("orbit_02_P3_centre", sets["plus_nonorbit_subgraph"])
        self.assertIn("orbit_02_P3_centre", sets["plus_orbit_lt15"])
        self.assertNotIn("orbit_23_g5", sets["plus_orbit_lt15"])
        self.assertIn("orbit_23_g5", sets["full_r1_structural"])

        # Dynamic tier and hop-2 features never appear at any rung.
        for set_id in SET_IDS:
            self.assertNotIn("spread_cv_neighbourhood", sets[set_id])
            self.assertNotIn("deep_thing", sets[set_id])

    def test_sets_are_strictly_nested_prefixes(self):
        features, registry = _synthetic_registry()
        sets = select_r1_sets(features, registry)
        for lower, higher in zip(SET_IDS, SET_IDS[1:]):
            self.assertEqual(sets[higher][:len(sets[lower])], sets[lower])
            self.assertGreater(len(sets[higher]), len(sets[lower]))

    def test_contract_violations_raise(self):
        features, registry = _synthetic_registry()

        with self.subTest("unknown tier"):
            bad = registry.copy()
            bad.loc[0, "tier"] = "quantum"
            with self.assertRaises(R1ContractError):
                select_r1_sets(features, bad)

        with self.subTest("duplicate feature"):
            bad = pd.concat([registry, registry.iloc[[0]]], ignore_index=True)
            with self.assertRaises(R1ContractError):
                select_r1_sets(features, bad)

        with self.subTest("selected feature missing from table"):
            with self.assertRaises(R1ContractError):
                select_r1_sets(features.drop(columns=["degree"]), registry)

        with self.subTest("malformed orbit name"):
            bad = registry.copy()
            bad.loc[5, "feature"] = "orbit_bogus"
            worse = features.rename(columns={"orbit_02_P3_centre": "orbit_bogus"})
            with self.assertRaises(R1ContractError):
                select_r1_sets(worse, bad)

    def test_objective_routing(self):
        objective_id, factory = objective_for("betweenness", rf_n_jobs=4)
        self.assertEqual(objective_id, "rf_log1p")
        model = factory(0)
        self.assertEqual(model.regressor.n_estimators, 120)
        self.assertEqual(model.regressor.min_samples_leaf, 2)
        self.assertEqual(model.regressor.n_jobs, 4)

        for target in ("spread_mean", "spread_cv", "spread_resid"):
            objective_id, factory = objective_for(target, rf_n_jobs=1)
            self.assertEqual(objective_id, "rf")
            model = factory(3)
            self.assertEqual(model.n_estimators, 120)
            self.assertEqual(model.min_samples_leaf, 2)
            self.assertEqual(model.n_jobs, 1)
            self.assertEqual(model.random_state, 3)

        with self.assertRaises(R1ContractError):
            objective_for("not_a_target", rf_n_jobs=1)
        for bad_jobs in (0, -1, 1.5, True):
            with self.assertRaises(R1ContractError):
                objective_for("spread_mean", rf_n_jobs=bad_jobs)

    def test_fold_digest_is_repeatable_and_discriminating(self):
        first = fold_digest(1000, seed=0)
        self.assertEqual(first, fold_digest(1000, seed=0), "digest must be deterministic")
        self.assertNotEqual(first, fold_digest(1000, seed=1), "seed must change the digest")
        self.assertNotEqual(first, fold_digest(1001, seed=0), "n_rows must change the digest")
        self.assertEqual(len(first), 64)
        with self.assertRaises(R1ContractError):
            fold_digest(3, seed=0)  # fewer rows than folds

    def test_expected_key_universe_is_exactly_800(self):
        keys = expected_keys()
        self.assertEqual(len(keys), 800)
        self.assertEqual(len(keys), len(NETWORKS) * len(TARGETS) * len(SET_IDS) * len(SEEDS))
        for tag in NETWORKS:
            self.assertEqual(sum(1 for k in keys if k[0] == tag), 160)

    def test_sort_order_follows_declared_grid_not_alphabet(self):
        keys = sorted(expected_keys(), key=lambda k: sort_key(*k))
        self.assertEqual(keys[0], ("ca-GrQc", "spread_mean", "node_edge", 0))
        # spread_mean precedes betweenness by declaration, though not alphabetically.
        first_targets = [k[1] for k in keys[:640]]
        self.assertEqual(first_targets[0], "spread_mean")

    def test_canonical_hash_ignores_key_order_but_not_content(self):
        self.assertEqual(canonical_sha256({"a": 1, "b": 2}), canonical_sha256({"b": 2, "a": 1}))
        self.assertNotEqual(canonical_sha256({"a": 1}), canonical_sha256({"a": 2}))
        with self.assertRaises(ValueError):
            canonical_sha256({"a": float("nan")})  # NaN must not be silently serialised

    def test_require_finite_rejects_nan_and_inf(self):
        require_finite("ok", [1.0, 2.0])
        for bad in ([1.0, np.nan], [np.inf, 1.0]):
            with self.assertRaises(R1ContractError):
                require_finite("bad", bad)

    def test_cell_name_is_stable(self):
        self.assertEqual(cell_name("ca-GrQc", "betweenness", "node_edge", 7),
                         "ca-GrQc__betweenness__node_edge__s7")


class RealCacheContractTests(unittest.TestCase):
    """Task 4: check the REAL cache contract, still without fitting anything."""

    @classmethod
    def setUpClass(cls):
        cls.missing = [tag for tag in NETWORKS
                       if not (ROOT / f"cache_registry_{tag}.csv").exists()]

    def test_all_five_registries_produce_the_declared_ladder(self):
        if self.missing:
            self.skipTest(f"caches absent: {self.missing}")
        for tag in NETWORKS:
            with self.subTest(tag=tag):
                features = pd.read_csv(ROOT / f"cache_features_{tag}.csv", nrows=5)
                registry = pd.read_csv(ROOT / f"cache_registry_{tag}.csv")
                sets = select_r1_sets(features, registry)
                sizes = tuple(len(sets[s]) for s in SET_IDS)
                self.assertEqual(sizes, EXPECTED_SIZES,
                                 f"{tag} ladder is {sizes}, expected {EXPECTED_SIZES}")
                assert_full_set_matches_select_features(sets, features, registry)

                # The nine eorbit_ edge features belong to the common baseline.
                eorbits = [c for c in sets["node_edge"] if c.startswith("eorbit_")]
                self.assertEqual(len(eorbits), 9, f"{tag}: eorbit_ count moved")

    def test_all_five_targets_available(self):
        if self.missing:
            self.skipTest(f"caches absent: {self.missing}")
        for tag in NETWORKS:
            columns = pd.read_csv(ROOT / f"cache_targets_{tag}.csv", nrows=1).columns
            for target in TARGETS:
                self.assertIn(target, columns, f"{tag} lacks target {target}")

    def test_legacy_oof_archives_carry_no_provenance_and_are_ineligible(self):
        """The reuse decision, asserted rather than asserted-in-prose.

        If a future reader wonders why 800 cells were refit rather than read out
        of the existing OOF stores, this test is the answer: the archives hold
        bare prediction arrays and no manifest member of any kind, so nothing in
        them can establish the column list, objective or fold allocation the
        paired contrast depends on.
        """
        checked = 0
        for tag in NETWORKS:
            archive = ROOT / f"cache_oof_{tag}.npz"
            if not archive.exists():
                continue
            with zipfile.ZipFile(archive) as bundle:
                names = [n[:-4] if n.endswith(".npy") else n for n in bundle.namelist()]
            self.assertEqual(len(names), 640, f"{tag}: expected 640 bare keys, got {len(names)}")
            for name in names:
                self.assertEqual(len(name.split("|")), 4,
                                 f"{tag}: {name!r} is not a bare target|radius|richness|seed key")
            for provenance in ("manifest", "columns", "fold_digest", "objective", "run_id"):
                self.assertNotIn(provenance, names,
                                 f"{tag}: unexpected provenance member {provenance!r}")
            # Both radius-1 betweenness endpoints exist yet remain unusable.
            for key in ("betweenness|1|node+edge|0", "betweenness|1|node+edge+subgraph|0"):
                if key in names:
                    self.assertNotIn(f"{key}|columns", names)
            checked += 1
        if checked == 0:
            self.skipTest("no legacy OOF archives present")

    def test_verifier_does_not_train(self):
        """Assert the no-fit contract structurally, over this file's own AST.

        A substring scan cannot express this: the test would match the very
        string literals it uses to name what is forbidden, so it fails on its
        own evidence. Parsing instead asks the question that actually matters --
        is any of these ever CALLED, or any training module IMPORTED -- and a
        name appearing inside a literal is correctly ignored.

        Narrowed 2026-09-10 by Claude Opus 5. The import ban originally also
        covered `probe_r1_ablation` and `analyse_r1_ablation`, which was an
        over-broad proxy for the real contract. The brief's Task 4 forbids
        CALLING `out_of_fold_predictions`, `RandomForestRegressor.fit`, cache
        writers or a training script -- and importing a module fits nothing.
        Task 3 explicitly requires testing the analyzer's paired arithmetic
        against fixed seed vectors, which is impossible if it cannot be
        imported. So the call ban is widened to the runner's fitting entry
        points instead, which is the property actually worth guarding.
        """
        import ast

        # NOT "main": this file legitimately calls `unittest.main()`, and the
        # AST check matches on the attribute name alone.
        forbidden_calls = {"out_of_fold_predictions", "fit", "locality_sweep",
                           "run_cell", "run_pilot", "load_or_create_pilot"}
        forbidden_imports = {"stage2_sweep", "stage1_prepare", "run_experiment"}

        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        called: set[str] = set()
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    called.add(func.id)
                elif isinstance(func, ast.Attribute):
                    called.add(func.attr)
            elif isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])

        self.assertEqual(called & forbidden_calls, set(),
                         f"verifier must not call {called & forbidden_calls}")
        self.assertEqual(imported & forbidden_imports, set(),
                         f"verifier must not import {imported & forbidden_imports}")


class PairedArithmeticTests(unittest.TestCase):
    """Task 3: the contrast arithmetic, on fixed vectors, with no fitting.

    Added 2026-09-10 by Claude Opus 5. These build cell frames by hand rather
    than running cells, so the arithmetic is checked against numbers whose
    answer is known in advance instead of against whatever a fit happened to
    produce.
    """

    @staticmethod
    def _frame(gains_by_key: dict[tuple[str, str], list[float]]) -> pd.DataFrame:
        """One full 800-key-shaped frame is unnecessary; build only what is read.

        `paired_contrasts` iterates the declared grid, so every (network,
        target) must be present. Baselines are zero and the upper set carries
        the requested gain, which makes `gain = tau_high - tau_low` exactly the
        vector handed in.
        """
        from influence.r1_ablation import NETWORKS, SEEDS, SET_IDS, TARGETS
        rows = []
        for network in NETWORKS:
            for target in TARGETS:
                gains = gains_by_key.get((network, target), [0.0] * len(SEEDS))
                for set_id in SET_IDS:
                    for index, seed in enumerate(SEEDS):
                        # Only the last contrast's upper endpoint carries the
                        # gain; the three lower rungs stay flat at zero.
                        tau = gains[index] if set_id == "full_r1_structural" else 0.0
                        rows.append({
                            "network": network, "target": target, "set_id": set_id,
                            "seed": seed, "kendall_tau": float(tau),
                        })
        return pd.DataFrame(rows)

    def test_mixed_sign_gains_produce_exact_counts_and_sample_sd(self):
        from analyse_r1_ablation import paired_contrasts

        gains = [0.10, -0.05, 0.00, 0.20, -0.10, 0.05, 0.00, 0.15, -0.20, 0.25]
        frame = self._frame({("ca-GrQc", "spread_mean"): gains})
        pairs = paired_contrasts(frame)
        self.assertEqual(len(pairs), 60)

        row = pairs[(pairs.network == "ca-GrQc") & (pairs.target == "spread_mean")
                    & (pairs.contrast == "add_remaining_g5_orbits")].iloc[0]
        self.assertEqual(row.n_pairs, 10)
        self.assertEqual(row.positive_count, 5)
        self.assertEqual(row.zero_count, 2)
        self.assertEqual(row.negative_count, 3)
        self.assertAlmostEqual(row.mean_gain, float(np.mean(gains)), places=12)
        # ddof=1: the sample SD of ten paired differences, not the population SD.
        self.assertAlmostEqual(row.paired_sd, float(np.std(gains, ddof=1)), places=12)
        self.assertNotAlmostEqual(row.paired_sd, float(np.std(gains, ddof=0)), places=6)

    def test_star_boundary_is_strictly_greater_than(self):
        from analyse_r1_ablation import paired_contrasts

        # A constant nonzero gain has a sample SD of zero in exact arithmetic,
        # but numpy computes it through the mean, so it lands at ~1e-17 rather
        # than 0. That is close enough to make the comparison `|mean| > ~0`,
        # which must star -- but it is NOT an exact boundary, so it is not
        # asserted as one.
        starred = paired_contrasts(self._frame({("ca-GrQc", "spread_mean"): [0.3] * 10}))
        row = starred[(starred.network == "ca-GrQc") & (starred.target == "spread_mean")
                      & (starred.contrast == "add_remaining_g5_orbits")].iloc[0]
        self.assertLess(row.paired_sd, 1e-15)
        self.assertTrue(row.heuristic_star)

        # The all-zero vector IS exact -- every deviation is exactly 0.0 -- so
        # this reaches the equality case `0 > 0` with no float slack, and it
        # must NOT star.
        flat = paired_contrasts(self._frame({("ca-GrQc", "spread_mean"): [0.0] * 10}))
        row = flat[(flat.network == "ca-GrQc") & (flat.target == "spread_mean")
                   & (flat.contrast == "add_remaining_g5_orbits")].iloc[0]
        self.assertEqual(row.mean_gain, 0.0)
        self.assertEqual(row.paired_sd, 0.0)
        self.assertFalse(row.heuristic_star)

    def test_negative_mean_can_star(self):
        from analyse_r1_ablation import paired_contrasts

        # abs() is deliberate: a consistent LOSS from adding features is a
        # finding, and must not be silently unflagged.
        pairs = paired_contrasts(self._frame({("ca-HepTh", "betweenness"): [-0.4] * 10}))
        row = pairs[(pairs.network == "ca-HepTh") & (pairs.target == "betweenness")
                    & (pairs.contrast == "add_remaining_g5_orbits")].iloc[0]
        self.assertLess(row.mean_gain, 0)
        self.assertTrue(row.heuristic_star)
        self.assertEqual(row.negative_count, 10)

    def test_missing_seed_endpoint_is_rejected(self):
        from analyse_r1_ablation import paired_contrasts

        frame = self._frame({})
        trimmed = frame[~((frame.network == "ca-GrQc") & (frame.target == "spread_mean")
                          & (frame.set_id == "full_r1_structural") & (frame.seed == 7))]
        with self.assertRaisesRegex(Exception, "seed 7 missing an endpoint"):
            paired_contrasts(trimmed)

    def test_every_declared_cell_appears_exactly_once(self):
        from analyse_r1_ablation import CONTRASTS, paired_contrasts
        from influence.r1_ablation import NETWORKS, TARGETS

        pairs = paired_contrasts(self._frame({}))
        self.assertEqual(len(pairs), len(NETWORKS) * len(TARGETS) * len(CONTRASTS))
        self.assertFalse(pairs.duplicated(["network", "target", "contrast"]).any())


class CellRecordIntegrityTests(unittest.TestCase):
    """Task 2 resume protocol, exercised on temporary artifacts only.

    Added 2026-09-10 by Claude Opus 5. A cell is skipped -- its fit NOT
    repeated -- purely on the strength of `read_verified_cell`, so each way it
    can be lied to gets a test.
    """

    def setUp(self):
        import tempfile

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _valid_record(self) -> dict:
        from probe_r1_ablation import record_checksum

        record = {
            "schema": "phase6_r1_ablation_cell_v1", "run_id": "a" * 64,
            "network": "ca-GrQc", "target": "spread_mean",
            "set_id": "node_edge", "seed": 0, "radius": 1, "n_splits": 5,
            "objective_id": "rf", "rf_n_jobs": 4, "n_rows": 100, "n_columns": 38,
            "columns_sha256": "b" * 64, "target_sha256": "c" * 64,
            "fold_digest": "d" * 64,
            "metrics": {"kendall_tau": 0.5, "rmse": 1.0}, "fit_seconds": 1.5,
        }
        record["content_sha256"] = record_checksum(record)
        return record

    def _write(self, record: dict, stem: str | None = None) -> Path:
        from probe_r1_ablation import write_atomic_json

        name = stem or "ca-GrQc__spread_mean__node_edge__s0"
        path = self.root / f"{name}.json"
        write_atomic_json(path, record)
        return path

    def test_valid_cell_round_trips(self):
        from probe_r1_ablation import read_verified_cell

        path = self._write(self._valid_record())
        record = read_verified_cell(path, "a" * 64)
        self.assertEqual(record["network"], "ca-GrQc")
        self.assertEqual(record["metrics"]["kendall_tau"], 0.5)

    def test_tampered_metric_breaks_the_checksum(self):
        from probe_r1_ablation import read_verified_cell

        record = self._valid_record()
        record["metrics"]["kendall_tau"] = 0.99  # checksum not recomputed
        path = self._write(record)
        with self.assertRaisesRegex(Exception, "checksum"):
            read_verified_cell(path, "a" * 64)

    def test_foreign_run_id_is_rejected(self):
        from probe_r1_ablation import read_verified_cell

        path = self._write(self._valid_record())
        with self.assertRaisesRegex(Exception, "run_id"):
            read_verified_cell(path, "e" * 64)

    def test_filename_must_match_its_own_key(self):
        from probe_r1_ablation import read_verified_cell

        # A record renamed onto another cell's filename would otherwise be
        # accepted as that cell, silently substituting one result for another.
        path = self._write(self._valid_record(),
                           stem="ca-GrQc__spread_mean__node_edge__s3")
        with self.assertRaisesRegex(Exception, "filename does not match"):
            read_verified_cell(path, "a" * 64)

    def test_changed_fold_count_is_rejected(self):
        from probe_r1_ablation import read_verified_cell, record_checksum

        record = self._valid_record()
        record["n_splits"] = 10
        record["content_sha256"] = record_checksum(record)  # internally consistent
        path = self._write(record)
        with self.assertRaisesRegex(Exception, "fold count"):
            read_verified_cell(path, "a" * 64)

    def test_nonfinite_metric_is_rejected(self):
        from probe_r1_ablation import read_verified_cell, record_checksum

        # `experiment.evaluate` RETURNS NaN rather than refusing it, so a NaN
        # can reach a record; it must not survive a read.
        record = self._valid_record()
        record["metrics"]["kendall_tau"] = float("nan")
        with self.assertRaises(Exception):
            # canonical JSON forbids NaN outright, which is the first line of
            # defence; the reader is the second.
            record["content_sha256"] = record_checksum(record)

    def test_atomic_write_leaves_no_deterministic_temp(self):
        from probe_r1_ablation import write_atomic_json

        path = self.root / "cell.json"
        write_atomic_json(path, {"a": 1})
        write_atomic_json(path, {"a": 2})
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 2})
        # Unique temp names per attempt: nothing predictable is left behind for
        # a later attempt to collide with or mistakenly reuse.
        self.assertEqual(list(self.root.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

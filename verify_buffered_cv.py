"""Focused fixtures for the isolated Phase 6 buffered-CV harness.

These tests deliberately use constructed graphs and temporary checkpoints.  They
exercise split, buffer, transform, and transaction invariants without reading
the project corpus or fitting the full forest sweep.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import scipy.sparse as sp

import analyse_structural_moran_correlogram as structural_moran
import analyse_buffered_cv as buffered_analysis
import probe_buffered_cv as buffered


def adjacency(edges: list[tuple[int, int]], n: int, *, scramble: bool = False) -> sp.csr_matrix:
    rows, cols = zip(*[(u, v) for u, v in edges] + [(v, u) for u, v in edges])
    adj = sp.csr_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)), shape=(n, n))
    adj.sort_indices()
    if scramble:
        # A valid CSR can have each row's indices in another order.  BFS must
        # impose ascending-neighbour traversal itself rather than trust it.
        for v in range(n):
            lo, hi = adj.indptr[v], adj.indptr[v + 1]
            adj.indices[lo:hi] = adj.indices[lo:hi][::-1]
    return adj


def nbrs(adj: sp.csr_matrix) -> list[np.ndarray]:
    return [adj.indices[adj.indptr[v]:adj.indptr[v + 1]] for v in range(adj.shape[0])]


class BufferedCvTests(unittest.TestCase):
    def test_bfs_is_seeded_deterministic_and_folds_cover_once(self):
        graph = adjacency([(0, 2), (0, 1), (1, 3), (2, 4), (4, 5), (3, 6), (6, 7), (7, 8), (8, 9)], 10,
                          scramble=True)
        first, root = buffered.bfs_order(nbrs(graph), 7)
        second, root2 = buffered.bfs_order(nbrs(graph), 7)
        self.assertEqual(root, root2)
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(np.sort(first), np.arange(10))
        folds = buffered.region_folds(nbrs(graph), 7)
        self.assertEqual(len(folds), 5)
        np.testing.assert_array_equal(np.sort(np.concatenate(folds)), np.arange(10))

    def test_path_and_cycle_buffer_masks_match_shortest_distances(self):
        path = adjacency([(i, i + 1) for i in range(6)], 7)
        got = buffered.exclusion_mask(path, np.array([3]), 2)
        expected = np.array([False, True, True, True, True, True, False])
        np.testing.assert_array_equal(got, expected)
        cycle = adjacency([(i, (i + 1) % 8) for i in range(8)], 8)
        got_cycle = buffered.exclusion_mask(cycle, np.array([0]), 2)
        np.testing.assert_array_equal(got_cycle,
                                      np.array([True, True, True, False, False, False, True, True]))

    def test_complete_graph_records_buffer_exhaustion_without_fallback(self):
        n = 40
        complete = adjacency([(u, v) for u in range(n) for v in range(u + 1, n)], n)
        plans = buffered.build_fold_plans("fixture", "spread_mean", 0, 0, 0, complete,
                                          np.arange(7), measured_buffer=None)
        by_arm = {plan.logical_arm: plan for plan in plans}
        self.assertEqual(by_arm["region"].status, buffered.READY)
        self.assertEqual(by_arm["buffer_b1"].status, buffered.INFEASIBLE)
        self.assertEqual(by_arm["buffer_b1"].train_ids.size, 0)
        self.assertEqual(by_arm["control_b1"].status, buffered.SOURCE_INFEASIBLE)
        self.assertEqual(by_arm["buffer_measured"].status, buffered.UNRESOLVED)

    def test_controls_match_counts_and_measured_one_is_an_alias(self):
        n = 70
        path = adjacency([(i, i + 1) for i in range(n - 1)], n)
        test_ids = np.arange(20, 34)
        plans = buffered.build_fold_plans("fixture", "spread_cv", 2, 3, 1, path,
                                          test_ids, measured_buffer=1)
        by_arm = {plan.logical_arm: plan for plan in plans}
        self.assertEqual(by_arm["buffer_b1"].status, buffered.READY)
        self.assertEqual(by_arm["control_b1"].status, buffered.READY)
        self.assertEqual(by_arm["buffer_b1"].train_ids.size, by_arm["control_b1"].train_ids.size)
        self.assertFalse(np.intersect1d(test_ids, by_arm["control_b1"].train_ids).size)
        np.testing.assert_array_equal(by_arm["control_b1"].train_ids,
                                      np.sort(by_arm["control_b1"].train_ids))
        self.assertEqual(by_arm["buffer_measured"].alias_of, "buffer_b1")
        self.assertEqual(by_arm["control_measured"].alias_of, "control_b1")
        self.assertEqual(by_arm["control_measured"].canonical_arm, "control_b1")

    def test_control_seed_binds_every_declared_dimension(self):
        base = buffered.control_seed("a", "spread_mean", 0, 1, 2, "control_b1")
        self.assertEqual(base, buffered.control_seed("a", "spread_mean", 0, 1, 2, "control_b1"))
        self.assertNotEqual(base, buffered.control_seed("a", "spread_cv", 0, 1, 2, "control_b1"))
        self.assertNotEqual(base, buffered.control_seed("a", "spread_mean", 1, 1, 2, "control_b1"))

    def test_log_transform_is_betweenness_only(self):
        y = np.array([0.0, 2.0, 8.0])
        np.testing.assert_allclose(buffered.fit_target(y, "betweenness"), np.log1p(y))
        np.testing.assert_array_equal(buffered.fit_target(y, "spread_mean"), y)
        np.testing.assert_allclose(buffered.restore_prediction(np.log1p(y), "betweenness"), y)
        np.testing.assert_array_equal(buffered.restore_prediction(y, "spread_cv"), y)

    def test_structural_moran_paths_and_unresolved_readoff(self):
        self.assertEqual(structural_moran.structural_oof_path("ca-GrQc", "spread_mean"),
                         Path("cache_oof_ca-GrQc.npz"))
        self.assertEqual(structural_moran.structural_oof_path("ca-GrQc", "betweenness"),
                         Path("estimators/cache_oof_ca-GrQc__rf_log1p.npz"))
        rows = [
            {"network": "n", "target": "t", "radius": 0, "seed": seed,
             "residual": "rank", "lag": 1, "testable": True, "sig": True,
             "p_perm": .01}
            for seed in range(10)
        ]
        table = structural_moran.measured_buffers(rows)
        self.assertEqual(table[0]["status"], structural_moran.UNRESOLVED_NO_NONSIG)

    def test_checkpoint_round_trip_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provenance = {"configuration_sha256": "abc", "expected": ["k"]}
            state = {"fold_rows": [{"key": "k", "value": 1}], "cell_rows": [], "oof": {}}
            buffered.write_checkpoint(root, provenance, state)
            restored = buffered.load_checkpoint(root, provenance)
            self.assertEqual(restored["fold_rows"], state["fold_rows"])
            pointer = root / buffered.CHECKPOINT_POINTER
            pointer.write_text('{"generation":"missing","sha256":"bad"}', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                buffered.load_checkpoint(root, provenance)

    def test_checkpoint_rejects_changed_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provenance = {"configuration_sha256": "abc", "expected": ["k"]}
            buffered.write_checkpoint(root, provenance, {"fold_rows": [], "cell_rows": [], "oof": {}})
            with self.assertRaises(RuntimeError):
                buffered.load_checkpoint(root, {"configuration_sha256": "changed", "expected": ["k"]})

    def test_cell_checkpoint_stops_then_resumes_from_one_immutable_assignment_archive(self):
        n = 60
        graph = adjacency([(i, i + 1) for i in range(n - 1)], n)
        network, target, radius, seed = "fixture", "spread_mean", 0, 0
        key = buffered.cell_key(network, target, radius, seed)
        rows, arrays = [], {}
        for fold, test_ids in enumerate(buffered.region_folds(nbrs(graph), seed)):
            for plan in buffered.build_fold_plans(network, target, radius, seed, fold, graph, test_ids, None):
                row = buffered.plan_row(network, target, radius, seed, fold, plan)
                rows.append(row)
                for field, values in (("test_ids", plan.test_ids), ("train_ids", plan.train_ids),
                                      ("excluded_ids", plan.excluded_ids)):
                    arrays[buffered.assignment_key(network, target, radius, seed, fold,
                                                    plan.logical_arm, field)] = values
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            assignment = temp_path / "assignments.npz"
            buffered.atomic_npz(arrays, assignment)
            assignment_hash = buffered.digest_file(assignment)
            for row in rows:
                row["assignment_file"] = assignment.as_posix()
                row["assignment_file_sha256"] = assignment_hash
                for field in ("test_ids", "train_ids", "excluded_ids"):
                    values = arrays[buffered.assignment_key(network, target, radius, seed, int(row["fold"]),
                                                             row["logical_arm"], field)]
                    row[f"{field}_sha256"] = buffered.stable_digest(values)
                row["preflight_row_sha256"] = buffered.stable_digest(row)
            preflight = {"fold_rows": rows, "assignment_files": {key: {"path": assignment.as_posix(),
                                                                          "sha256": assignment_hash}}}
            provenance = {"configuration_sha256": "fixture-config", "identity_sha256": "fixture-input", "preflight_sha256": "fixture-preflight"}
            old_root = buffered.CHECKPOINT_ROOT
            try:
                buffered.CHECKPOINT_ROOT = temp_path / "checkpoints"
                X = np.arange(n * 2, dtype=float).reshape(n, 2)
                y = np.arange(n, dtype=float)
                with patch("probe_buffered_cv.fit_region_fold",
                           side_effect=lambda _X, _y, _tr, te, *_rest: np.full(len(te), .5)) as mocked:
                    fitted, stopped = buffered._run_cell(network, target, radius, seed, X, y, preflight,
                                                          provenance, 1, 1, 0)
                    self.assertTrue(stopped)
                    self.assertEqual(fitted, 1)
                    fitted, stopped = buffered._run_cell(network, target, radius, seed, X, y, preflight,
                                                          provenance, 1, None, fitted)
                    self.assertFalse(stopped)
                    self.assertGreater(mocked.call_count, 1)
                state = buffered.load_checkpoint(buffered._cell_checkpoint_root(key), provenance)
                self.assertEqual(len(state["cell_rows"]), 5)
                self.assertTrue(any(row["status"] == buffered.COMPLETE for row in state["cell_rows"]))
                corrupt_rows = [dict(row) for row in rows]
                corrupt_rows[0]["assignment_sha256"] = "corrupted-but-unchecked"
                corrupt_preflight = {**preflight, "fold_rows": corrupt_rows}
                with self.assertRaises(RuntimeError):
                    buffered._load_cell_assignments(corrupt_preflight, key)
            finally:
                buffered.CHECKPOINT_ROOT = old_root

    def test_analysis_rejects_duplicate_or_missing_seed_arm_keys(self):
        rows = [{"network": network, "target": target, "radius": radius, "seed": seed,
                 "logical_arm": arm, "status": buffered.UNRESOLVED, "kendall_tau": np.nan}
                for network in buffered.NETWORKS for target in buffered.TARGETS for radius in buffered.RADII
                for seed in buffered.SEEDS for arm in buffered_analysis.ARMS]
        for row in rows:
            row.update({"configuration_sha256": "fixture-config", "preflight_identity_sha256": "fixture-input"})
            row["row_sha256"] = buffered.stable_digest(row)
        frame = __import__("pandas").DataFrame(rows)
        buffered_analysis.validate_cells(frame)
        with self.assertRaises(ValueError):
            buffered_analysis.validate_cells(__import__("pandas").concat([frame, frame.iloc[[0]]], ignore_index=True))
        with self.assertRaises(ValueError):
            buffered_analysis.validate_cells(frame.iloc[1:])

    def test_immutable_assignment_reader_rejects_missing_logical_id_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            network, target, radius, seed, fold = "fixture", "spread_mean", 0, 0, 0
            key = buffered.cell_key(network, target, radius, seed)
            graph = adjacency([(i, i + 1) for i in range(39)], 40)
            plan = buffered.build_fold_plans(network, target, radius, seed, fold, graph,
                                             np.arange(8), None)[0]
            row = buffered.plan_row(network, target, radius, seed, fold, plan)
            archive = temp_path / "truncated.npz"
            only_test = {buffered.assignment_key(network, target, radius, seed, fold,
                                                 plan.logical_arm, "test_ids"): plan.test_ids}
            buffered.atomic_npz(only_test, archive)
            archive_hash = buffered.digest_file(archive)
            row["assignment_file_sha256"] = archive_hash
            preflight = {"fold_rows": [row], "assignment_files": {key: {"path": archive.as_posix(),
                                                                          "sha256": archive_hash}}}
            with self.assertRaises(RuntimeError):
                buffered._load_cell_assignments(preflight, key)

    def test_analysis_emits_paired_covariance_only_for_complete_arms(self):
        rows = [{"network": network, "target": target, "radius": radius, "seed": seed,
                 "logical_arm": arm, "status": buffered.COMPLETE,
                 "kendall_tau": .4 + .01 * seed + .001 * buffered_analysis.ARMS.index(arm)}
                for network in buffered.NETWORKS for target in buffered.TARGETS for radius in buffered.RADII
                for seed in buffered.SEEDS for arm in buffered_analysis.ARMS]
        for row in rows:
            row.update({"configuration_sha256": "fixture-config", "preflight_identity_sha256": "fixture-input"})
            row["row_sha256"] = buffered.stable_digest(row)
        result = buffered_analysis.descriptive_contrasts(__import__("pandas").DataFrame(rows))
        self.assertTrue((result.status == "scored").all())
        self.assertTrue(np.isfinite(result.covariance).all())

    def test_structural_moran_tiny_producer_cli_checks_alignment_finiteness_and_null_metadata(self):
        network, n = "ca-GrQc", 31
        graph = adjacency([(index, (index + 1) % n) for index in range(n)], n)
        original_ids = np.arange(n, dtype=np.int64) + 100
        with tempfile.TemporaryDirectory() as temp:
            root, old_cwd, old_argv = Path(temp), Path.cwd(), sys.argv
            try:
                (root / "estimators").mkdir()
                raw = root / "raw.txt"
                raw.write_text("fixture graph\n", encoding="utf-8")
                targets = {"node": np.arange(n)}
                for index, target in enumerate(structural_moran.TARGETS):
                    targets[target] = np.arange(n, dtype=float) + index
                __import__("pandas").DataFrame(targets).to_csv(root / f"cache_targets_{network}.csv", index=False)
                __import__("pandas").DataFrame({"node": np.arange(n), "original_id": original_ids}).to_csv(
                    root / f"cache_features_{network}.csv", index=False)
                (root / f"cache_registry_{network}.csv").write_text("feature,hop,tier\nf,0,node\n", encoding="utf-8")
                spreading, beta = {}, {}
                for target in structural_moran.TARGETS:
                    store = beta if target == "betweenness" else spreading
                    for radius in structural_moran.RADII:
                        for seed in structural_moran.SEEDS:
                            # Seed zero deliberately has a defined but constant residual;
                            # its undefined Moran/null statistics must be untestable.
                            store[f"{target}|{radius}|{structural_moran.STRUCTURAL_TIER}|{seed}"] = np.roll(np.arange(n, dtype=float), seed)
                np.savez_compressed(root / f"cache_oof_{network}.npz", **spreading)
                np.savez_compressed(root / "estimators" / f"cache_oof_{network}__rf_log1p.npz", **beta)
                os.chdir(root)
                net = SimpleNamespace(n=n, adj=graph, original_ids=original_ids)
                with patch("analyse_structural_moran_correlogram.load_edgelist", return_value=net), \
                     patch("analyse_structural_moran_correlogram.manifest_paths", return_value={network: raw}):
                    sys.argv = ["structural", "--tags", network, "--perms", "1", "--batch", "8",
                                "--out", "out.csv", "--provenance", "provenance.json"]
                    self.assertEqual(structural_moran.main(), 0)
                produced = __import__("pandas").read_csv(root / "out.csv")
                sidecar = __import__("json").loads((root / "provenance.json").read_text(encoding="utf-8"))
                self.assertEqual(len(produced), len(structural_moran.TARGETS) * len(structural_moran.RADII)
                                 * len(structural_moran.SEEDS) * 7)
                self.assertEqual(sidecar["configuration"]["blas_threads"], 4)
                self.assertEqual(sidecar["configuration"]["null_reference_seed"], 0)
                self.assertIn("producer_source_sha256", sidecar)
                self.assertTrue((produced[produced.seed == 0].testable == False).all())
                self.assertTrue((produced.null_reference_seed == 0).all())
                # A non-finite OOF is rejected before it can enter rank residuals.
                spreading[next(iter(spreading))] = np.full(n, np.nan)
                np.savez_compressed(root / f"cache_oof_{network}.npz", **spreading)
                with patch("analyse_structural_moran_correlogram.load_edgelist", return_value=net):
                    with self.assertRaises(ValueError):
                        structural_moran._rows_for_network(network, raw, perms=1, batch=8, random_seed=0)
                # Cache original IDs are likewise a hard alignment boundary.
                __import__("pandas").DataFrame({"node": np.arange(n), "original_id": original_ids[::-1]}).to_csv(
                    root / f"cache_features_{network}.csv", index=False)
                with patch("analyse_structural_moran_correlogram.load_edgelist", return_value=net):
                    with self.assertRaises(ValueError):
                        structural_moran._rows_for_network(network, raw, perms=1, batch=8, random_seed=0)
            finally:
                os.chdir(old_cwd)
                sys.argv = old_argv

    def test_structural_moran_rejects_altered_producer_source_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            csv = root / "moran.csv"
            csv.write_text("placeholder\n", encoding="utf-8")
            sidecar = {"protocol": buffered.STRUCTURAL_MORAN_PROTOCOL,
                       "configuration": {"tier": __import__("analyse").FULL, "targets": list(buffered.TARGETS),
                                         "radii": list(buffered.RADII), "seeds": list(buffered.SEEDS), "lags": 7,
                                         "blas_threads": 4, "null_reference_seed": 0,
                                         "p_perm_interpretation": structural_moran.NULL_REFERENCE_DESCRIPTION},
                       "producer_source_sha256": {"altered": "source"}}
            (root / "sidecar.json").write_text(__import__("json").dumps(sidecar), encoding="utf-8")
            with self.assertRaises(ValueError):
                buffered.validate_structural_moran(csv, root / "sidecar.json")

    def test_source_key_shim_accepts_this_root_and_rejects_foreign_absolute_keys(self):
        # Added 2026-09-11 (Claude Opus 5, Task 6 finding P2-02). Artifacts
        # recorded before that date key source hashes on ABSOLUTE paths; the
        # shim must map a key from THIS checkout to its root-relative form and
        # leave a foreign checkout's key untouched so it fails the comparison
        # instead of silently matching a same-named file here.
        current = structural_moran.producer_source_hashes()
        self.assertTrue(all(not Path(k).is_absolute() for k in current), current.keys())
        self.assertIn("influence/preprocessing.py", current)
        absolute = {(structural_moran.PROJECT_ROOT / k).as_posix(): v for k, v in current.items()}
        self.assertEqual(structural_moran.normalise_source_keys(absolute), current)
        foreign = {"/home/someone/else/checkout/definitely_not_a_file_here.py": "abc"}
        self.assertEqual(structural_moran.normalise_source_keys(foreign), foreign)
        # A foreign absolute key whose basename exists here would be a false
        # match if the shim were name-based; it is suffix-under-root based, and
        # 'analyse.py' does exist under the root, so this case documents the
        # accepted limit: the longest existing suffix wins.
        collide = {"/elsewhere/analyse.py": "abc"}
        self.assertEqual(structural_moran.normalise_source_keys(collide), {"analyse.py": "abc"})

    def test_structural_moran_consumer_rejects_non_authoritative_permutation_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            csv = root / "moran.csv"
            csv.write_text("placeholder\n", encoding="utf-8")
            config = {"tier": __import__("analyse").FULL, "targets": list(buffered.TARGETS),
                      "radii": list(buffered.RADII), "seeds": list(buffered.SEEDS), "lags": 7,
                      "blas_threads": 4, "null_reference_seed": 0,
                      "p_perm_interpretation": structural_moran.NULL_REFERENCE_DESCRIPTION,
                      "perms": 199, "batch": 512, "random_seed": 0}
            for field, changed in (("perms", 1), ("batch", 8), ("random_seed", 17)):
                altered = dict(config)
                altered[field] = changed
                sidecar = {"protocol": buffered.STRUCTURAL_MORAN_PROTOCOL, "configuration": altered,
                           "producer_source_sha256": structural_moran.producer_source_hashes()}
                sidecar_path = root / f"{field}.json"
                sidecar_path.write_text(__import__("json").dumps(sidecar), encoding="utf-8")
                with self.assertRaises(ValueError, msg=field):
                    buffered.validate_structural_moran(csv, sidecar_path)

    def test_structural_moran_sidecar_rejects_dynamic_or_unbound_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            csv = root / "moran.csv"
            rows = [{"network": network, "target": target, "radius": radius, "seed": seed,
                     "residual": "rank", "lag": 1, "testable": True, "sig": False}
                    for network in buffered.NETWORKS for target in buffered.TARGETS for radius in buffered.RADII
                    for seed in buffered.SEEDS]
            __import__("pandas").DataFrame(rows).to_csv(csv, index=False)
            (root / "moran_provenance.json").write_text('{"protocol":"dynamic-c6"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                buffered.validate_structural_moran(csv, root / "moran_provenance.json")

    def test_checkpoint_rejects_changed_input_identity_with_same_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = {"configuration_sha256": "same", "identity_sha256": "input-old"}
            buffered.write_checkpoint(root, first, {"fold_rows": [], "cell_rows": [], "oof": {}})
            with self.assertRaises(RuntimeError):
                buffered.load_checkpoint(root, {"configuration_sha256": "same", "identity_sha256": "input-new"})

    def test_compact_export_rows_never_embed_node_id_arrays(self):
        row = {"network": "n", "test_ids": [1, 2], "train_ids": [0, 3], "excluded_ids": [4],
               "test_ids_sha256": "a", "train_ids_sha256": "b", "excluded_ids_sha256": "c"}
        compact = buffered.compact_fold_row(row)
        self.assertNotIn("test_ids", compact)
        self.assertNotIn("train_ids", compact)
        self.assertNotIn("excluded_ids", compact)
        self.assertEqual(compact["test_ids_sha256"], "a")

    def test_analyzer_rejects_mixed_configuration_and_bad_row_digest(self):
        rows = [{"network": network, "target": target, "radius": radius, "seed": seed,
                 "logical_arm": arm, "status": buffered.UNRESOLVED, "kendall_tau": np.nan,
                 "configuration_sha256": "one", "preflight_identity_sha256": "identity"}
                for network in buffered.NETWORKS for target in buffered.TARGETS for radius in buffered.RADII
                for seed in buffered.SEEDS for arm in buffered_analysis.ARMS]
        for row in rows:
            row["row_sha256"] = buffered.stable_digest(row)
        frame = __import__("pandas").DataFrame(rows)
        buffered_analysis.validate_cells(frame)
        mixed = frame.copy()
        mixed.loc[0, "configuration_sha256"] = "two"
        with self.assertRaises(ValueError):
            buffered_analysis.validate_cells(mixed)
        corrupt = frame.copy()
        corrupt.loc[0, "row_sha256"] = "corrupt"
        with self.assertRaises(ValueError):
            buffered_analysis.validate_cells(corrupt)

    def test_analyzer_requires_untampered_final_manifest(self):
        rows = [{"network": network, "target": target, "radius": radius, "seed": seed,
                 "logical_arm": arm, "status": buffered.UNRESOLVED, "kendall_tau": None,
                 "configuration_sha256": "fixture-config", "preflight_identity_sha256": "fixture-input"}
                for network in buffered.NETWORKS for target in buffered.TARGETS for radius in buffered.RADII
                for seed in buffered.SEEDS for arm in buffered_analysis.ARMS]
        for row in rows:
            row["row_sha256"] = buffered.stable_digest(row)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cells_path, oof_path, manifest_path = root / "cells.csv", root / "oof.json", root / "results.json"
            __import__("pandas").DataFrame(rows).to_csv(cells_path, index=False)
            frame = __import__("pandas").read_csv(cells_path, float_precision="round_trip")
            buffered.atomic_json({"protocol": buffered.PROTOCOL, "configuration_sha256": "fixture-config", "preflight_identity_sha256": "fixture-input",
                                  "archives": {}}, oof_path)
            manifest = {"protocol": buffered.PROTOCOL, "configuration_sha256": "fixture-config", "preflight_identity_sha256": "fixture-input",
                        "cells_csv": cells_path.as_posix(), "cells_sha256": buffered.digest_file(cells_path),
                        "oof_manifest": oof_path.as_posix(), "oof_manifest_sha256": buffered.digest_file(oof_path),
                        "expected_logical_cell_keys": buffered_analysis._cell_key_strings(frame),
                        "completed_oof_keys": []}
            manifest["results_sha256"] = buffered.stable_digest(manifest)
            buffered.atomic_json(manifest, manifest_path)
            buffered_analysis.validate_result_manifest(cells_path, frame, manifest_path)
            manifest["cells_sha256"] = "tampered"
            manifest["results_sha256"] = buffered.stable_digest({key: value for key, value in manifest.items()
                                                                    if key != "results_sha256"})
            buffered.atomic_json(manifest, manifest_path)
            with self.assertRaises(ValueError):
                buffered_analysis.validate_result_manifest(cells_path, frame, manifest_path)

    def test_pilot_equivalence_is_scale_aware_and_rejects_tau_or_prediction_drift(self):
        reference = np.array([1.0e8, 2.0e8])
        equivalent = buffered.pilot_equivalence(reference, reference + 1.0e-5, .5, .5)
        self.assertTrue(equivalent["numerically_equivalent_to_jobs1"])
        tau_drift = buffered.pilot_equivalence(reference, reference, .5, .5 + 1.0e-8)
        self.assertFalse(tau_drift["numerically_equivalent_to_jobs1"])
        prediction_drift = buffered.pilot_equivalence(reference, reference + 1.0, .5, .5)
        self.assertFalse(prediction_drift["numerically_equivalent_to_jobs1"])

    def test_pilot_selection_is_fastest_valid_bounded_setting(self):
        selected = buffered.select_pilot_job([
            {"rf_jobs": 1, "valid": True, "elapsed_seconds": 4.0},
            {"rf_jobs": 4, "valid": True, "elapsed_seconds": 2.0},
            {"rf_jobs": 8, "valid": False, "elapsed_seconds": 1.0},
        ])
        self.assertEqual(selected, 4)


    def test_csv_round_trip_preserves_high_precision_tau_and_missing_row_digest_fields(self):
        rows = [{"network": network, "target": target, "radius": radius, "seed": seed,
                 "logical_arm": arm, "status": buffered.UNRESOLVED, "kendall_tau": None,
                 "buffer": None, "failure_reason": "", "testable": False,
                 "configuration_sha256": "fixture-config", "preflight_identity_sha256": "fixture-input"}
                for network in buffered.NETWORKS for target in buffered.TARGETS for radius in buffered.RADII
                for seed in buffered.SEEDS for arm in buffered_analysis.ARMS]
        rows[0].update({"status": buffered.COMPLETE, "kendall_tau": 0.9334276102646076,
                        "buffer": 1, "failure_reason": None, "testable": True})
        for row in rows:
            row["row_sha256"] = buffered.stable_digest(row)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cells.csv"
            __import__("pandas").DataFrame(rows).to_csv(path, index=False)
            restored = __import__("pandas").read_csv(path, float_precision="round_trip")
        self.assertEqual(restored.loc[0, "kendall_tau"], 0.9334276102646076)
        buffered_analysis.validate_cells(restored)

    def test_reported_random_reference_uses_log1p_betweenness_and_geometry_label(self):
        rows = [{"target": target, "radius": radius, "seed": seed, "richness": __import__("analyse").FULL,
                 "kendall_tau": .25 + .01 * seed}
                for target in buffered.TARGETS for radius in buffered.RADII for seed in buffered.SEEDS]
        reported = __import__("pandas").DataFrame(rows)
        with patch("analyse_buffered_cv.Path.is_file", return_value=True), \
             patch("analyse_buffered_cv.digest_file", side_effect=lambda path: f"hash:{path.as_posix()}"), \
             patch("analyse_buffered_cv.analyse.load", return_value=reported):
            result = buffered_analysis.reported_random_cv_reference()
        beta = result[result.target == "betweenness"]
        self.assertTrue(beta.source_path.str.startswith("estimators/sweep_").all())
        self.assertTrue((result.geometry == buffered_analysis.GEOMETRY_LABEL).all())
        self.assertTrue((beta.reported_objective == "rf_log1p").all())


if __name__ == "__main__":
    unittest.main()

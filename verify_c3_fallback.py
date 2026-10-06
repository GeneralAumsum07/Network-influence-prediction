"""Fail-closed, nodewise reinforcement of C3's existing five-network P4 fallback.

Run ``python verify_c3_fallback.py --self-test`` for synthetic regressions,
or run without arguments to verify the cached project targets and write evidence.
No fitting, shortest-path recomputation, external-corpus traversal or scoring occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from analyse_c3_benchmarks import build_csr, load_edges, shares, zero_set
from influence.preprocessing import load_edgelist


ROOT = Path(__file__).resolve().parent
PROJECT_NETWORKS = ("ca-GrQc", "ca-HepTh", "p2p-Gnutella08",
                    "email-Eu-core", "facebook_combined")


def audit_network(name, graph_path, target_path, mapping_path, *, zero_rule=zero_set):
    """Compare independent C3 certificates against exact cached targets by identity.

    Missing/malformed inputs raise, so callers cannot turn absent evidence into a
    successful zero-mismatch count. A genuine mask disagreement is returned with
    both directions and original IDs intact, rather than stopping at a count.
    """
    for path in (graph_path, target_path, mapping_path):
        if not Path(path).is_file():
            raise FileNotFoundError(f"required input missing: {path}")

    edges, n_all = load_edges(Path(graph_path))
    if edges.ndim != 2 or edges.shape[1] != 2 or n_all == 0:
        raise ValueError("raw edge-list shape is invalid or empty")
    # C3's compact labels are sorted original labels, not encounter order. Keep
    # the inverse mapping explicitly: equal zero totals alone cannot validate it.
    raw = np.loadtxt(graph_path, dtype=np.int64, comments=("#", "%"),
                     usecols=(0, 1), ndmin=2)
    original_ids = np.unique(raw)
    if len(original_ids) != n_all or not np.array_equal(original_ids[edges], raw):
        raise ValueError("C3 raw node relabelling/order disagrees with original IDs")
    adj = build_csr(edges, n_all, symmetrise=True)
    _, labels = connected_components(adj, directed=False)
    keep = np.flatnonzero(labels == np.bincount(labels).argmax())
    adj = adj[keep][:, keep].tocsr()
    adj.sort_indices()
    original_ids = original_ids[keep]
    n = len(keep)

    # Stage 1 delegates preprocessing to this loader, but the certificate above
    # uses C3's own loader/CSR. Reconcile topology as well as labels to catch any
    # future self-loop, LCC or symmetrisation divergence before using a cache.
    pipeline = load_edgelist(graph_path)
    if not np.array_equal(pipeline.original_ids, original_ids):
        raise ValueError("pipeline original node IDs/order disagree with independent graph")
    if pipeline.adj.shape != adj.shape or (pipeline.adj != adj).nnz:
        raise ValueError("pipeline topology disagrees with independent graph")

    targets = pd.read_csv(target_path, usecols=["node", "betweenness"])
    mapping = pd.read_csv(mapping_path, usecols=["node", "original_id"])
    for label, table in (("target", targets), ("mapping", mapping)):
        if len(table) != n:
            raise ValueError(f"{label} shape: {len(table)} rows, expected {n}")
        # Sorting would hide a broken cache contract: stage1 writes targets and
        # features in this exact order, with node = arange(net.n) in both tables.
        if not np.array_equal(table.node.to_numpy(), np.arange(n)):
            raise ValueError(f"{label} node IDs/order must be exactly 0..n-1")
    if not np.array_equal(mapping.original_id.to_numpy(), original_ids):
        raise ValueError("cached original node IDs/order disagree with independent graph")
    truth = targets.betweenness.to_numpy(dtype=float)
    if not np.all(np.isfinite(truth)) or np.any(truth < 0):
        raise ValueError("cached betweenness must be finite and nonnegative")
    rule = np.asarray(zero_rule(adj, adj, n))
    if rule.shape != (n,) or rule.dtype != np.dtype(bool):
        raise ValueError("zero rule must return one Boolean per aligned node")

    cached_zero = truth == 0  # Exact zeros: no tolerance or quantisation waiver.
    false_zero = rule & ~cached_zero
    missed_zero = ~rule & cached_zero
    summary = {
        "network": name, "n": n, "m": int(adj.nnz // 2),
        "structural_zeros": int(rule.sum()), "cached_zeros": int(cached_zero.sum()),
        "rule_zero_cached_positive": int(false_zero.sum()),
        "rule_positive_cached_zero": int(missed_zero.sum()),
        "w_exact": shares(n, int(rule.sum()))["w_exact"],
        "ok": not bool(np.any(false_zero | missed_zero)),
    }
    nodes = pd.DataFrame({
        "network": name, "node": np.arange(n), "original_id": original_ids,
        "structural_zero": rule, "cached_betweenness": truth,
        "cached_zero": cached_zero, "rule_zero_cached_positive": false_zero,
        "rule_positive_cached_zero": missed_zero, "mismatch": false_zero | missed_zero,
    })
    return summary, nodes


def _audit_project(root):
    summaries, nodes, lines, inputs = [], [], [], []
    for name in PROJECT_NETWORKS:
        paths = (root / "data" / f"{name}.txt", root / f"cache_targets_{name}.csv",
                 root / f"cache_features_{name}.csv")
        inputs.extend(paths)
        try:
            summary, frame = audit_network(name, *paths)
        except (OSError, ValueError, IndexError) as exc:
            # Fail each absent graph explicitly; never return success because a
            # loop happened to verify zero graphs. Other graphs still get checked.
            lines.append(f"{name}: FAIL {type(exc).__name__}: {exc}")
            continue
        summaries.append(summary)
        nodes.append(frame)
        lines.append(
            f"{name}: {'PASS' if summary['ok'] else 'FAIL'} n={summary['n']} "
            f"structural_zeros={summary['structural_zeros']} cached_zeros={summary['cached_zeros']} "
            f"rule_zero_cached_positive={summary['rule_zero_cached_positive']} "
            f"rule_positive_cached_zero={summary['rule_positive_cached_zero']} "
            f"w_exact={summary['w_exact']:.12f}")
    ok = len(summaries) == len(PROJECT_NETWORKS) and all(s['ok'] for s in summaries)
    lines.append(f"Required networks checked: {len(summaries)}/{len(PROJECT_NETWORKS)}; "
                 f"nodes checked: {sum(s['n'] for s in summaries)}")
    lines.append("ALL CHECKS PASSED" if ok else "FALLBACK VERIFICATION FAILED")
    return ok, "\n".join(lines), nodes, inputs


def gate_project_fallback(root=ROOT):
    """Reusable gate; always requires all five networks and writes no artifacts."""
    ok, report, _, _ = _audit_project(Path(root))
    return ok, report


def write_evidence(root=ROOT):
    """Persist measured nodes and hashes without changing any scored verdict."""
    root = Path(root)
    ok, report, nodes, inputs = _audit_project(root)
    output = root / "results"
    output.mkdir(exist_ok=True)
    node_path = output / "c3_fallback_nodes.csv"
    (pd.concat(nodes, ignore_index=True) if nodes else pd.DataFrame()).to_csv(
        node_path, index=False, lineterminator="\n")
    # Full input-file hashes bind this evidence to cached values and the mapping,
    # while source hashes identify the verifier and both preprocessing paths.
    sources = [ROOT / name for name in ("verify_c3_fallback.py", "analyse_c3_benchmarks.py",
               "influence/preprocessing.py", "influence/targets.py", "stage1_prepare.py")]
    hashes = []
    for path in inputs + sources + [node_path]:
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"
        # Keep the evidence portable across checkouts; hashes bind file contents,
        # while repository-relative names avoid encoding the local user profile.
        # A caller may audit a separate data root; source files still belong to
        # this module's checkout, so resolve their labels against that checkout.
        base = ROOT if path in sources else root
        hashes.append(f"SHA256 {digest}  {path.relative_to(base).as_posix()}")
    text = (
        "C3 existing five-network P4 fallback: independent nodewise verification\n"
        "Reinforcement only; no new conditional, thresholds or scored verdict changes.\n"
        "Raw C3 topology and original IDs agree with stage1 preprocessing; cached feature\n"
        "node/original_id mapping and cached target row order are required to agree exactly.\n"
        "Both mismatch directions must be zero. Exact cached b == 0; no tolerance.\n"
        "Independent w-table reproduction remains a separate existing gate.\n"
        "Scope: verifies zero masks, not every positive betweenness magnitude; no fitting,\n"
        "checkpoint execution, shortest-path recomputation or external corpus traversal.\n\n"
        + report + "\n\n" + "\n".join(hashes) + "\n")
    (output / "RESULTS_c3_fallback.txt").write_text(text, encoding="utf-8")
    return ok, report


class FallbackTests(unittest.TestCase):
    """Fixtures use hand-derived path centralities and gapped original labels."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.graph = self.root / "graph.txt"
        # The 99--100 component must be removed before cached row alignment.
        self.graph.write_text("10 20\n20 30\n99 100\n", encoding="utf-8")
        self.targets = self.root / "targets.csv"
        self.mapping = self.root / "features.csv"
        pd.DataFrame({"node": [0, 1, 2], "betweenness": [0., 1., 0.]}).to_csv(
            self.targets, index=False)
        pd.DataFrame({"node": [0, 1, 2], "original_id": [10, 20, 30]}).to_csv(
            self.mapping, index=False)

    def audit(self, **kwargs):
        self.assertTrue(callable(globals().get("audit_network")),
                        "nodewise audit has not been implemented")
        return audit_network("fixture", self.graph, self.targets, self.mapping, **kwargs)

    def test_gapped_ids_and_lcc_match_each_cached_node(self):
        summary, nodes = self.audit()
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["n"], 3)
        self.assertEqual(summary["structural_zeros"], 2)
        self.assertEqual(nodes.original_id.tolist(), [10, 20, 30])
        self.assertEqual(nodes.structural_zero.tolist(), [True, False, True])

    def test_count_preserving_wrong_mask_reports_both_directions(self):
        summary, nodes = self.audit(zero_rule=lambda a, b, n: np.array([False, True, True]))
        self.assertFalse(summary["ok"])
        self.assertEqual(summary["structural_zeros"], summary["cached_zeros"])
        self.assertEqual(summary["rule_zero_cached_positive"], 1)
        self.assertEqual(summary["rule_positive_cached_zero"], 1)
        self.assertEqual(nodes.loc[nodes.mismatch, "original_id"].tolist(), [10, 20])

    def test_each_missing_input_fails(self):
        for path in (self.graph, self.targets, self.mapping):
            saved = path.read_bytes()
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                self.audit()
            path.write_bytes(saved)

    def test_target_order_is_not_silently_repaired(self):
        table = pd.read_csv(self.targets).iloc[[1, 0, 2]]
        table.to_csv(self.targets, index=False)
        with self.assertRaisesRegex(ValueError, "target.*order"):
            self.audit()

    def test_original_id_permutation_fails_even_with_same_zero_count(self):
        pd.DataFrame({"node": [0, 1, 2], "original_id": [20, 10, 30]}).to_csv(
            self.mapping, index=False)
        with self.assertRaisesRegex(ValueError, "original.*order"):
            self.audit()

    def test_target_shape_duplicate_ids_and_nonfinite_values_fail(self):
        for frame in (
            pd.DataFrame({"node": [0, 1], "betweenness": [0., 1.]}),
            pd.DataFrame({"node": [0, 0, 2], "betweenness": [0., 1., 0.]}),
            pd.DataFrame({"node": [0, 1, 2], "betweenness": [0., np.nan, 0.]}),
            pd.DataFrame({"node": [0, 1, 2], "betweenness": [0., -1., 0.]}),
        ):
            with self.subTest(frame=frame.to_dict()):
                frame.to_csv(self.targets, index=False)
                with self.assertRaises(ValueError):
                    self.audit()

    def test_missing_mapping_column_fails(self):
        pd.DataFrame({"node": [0, 1, 2]}).to_csv(self.mapping, index=False)
        with self.assertRaises(ValueError):
            self.audit()

    def test_wrong_rule_shape_or_nonboolean_mask_fails(self):
        for mask in (np.array([True]), np.ones((3, 1), dtype=bool), np.array([1, 0, 1])):
            with self.subTest(shape=mask.shape, dtype=str(mask.dtype)):
                with self.assertRaises(ValueError):
                    self.audit(zero_rule=lambda a, b, n: mask)

    def test_all_five_networks_are_required(self):
        self.assertTrue(callable(globals().get("gate_project_fallback")),
                        "fail-closed five-network gate has not been implemented")
        ok, report = gate_project_fallback(self.root)
        self.assertFalse(ok)
        for name in ("ca-GrQc", "ca-HepTh", "p2p-Gnutella08", "email-Eu-core", "facebook_combined"):
            self.assertIn(name, report)

    def test_zero_set_empty_edges_and_isolated_node(self):
        # Vacuous simpliciality must work without indexing an empty edge-key array.
        for n in (0, 1, 3):
            empty = csr_matrix((n, n), dtype=np.int8)
            np.testing.assert_array_equal(zero_set(empty, empty, n), np.ones(n, dtype=bool))
        path_and_isolate = csr_matrix(np.array([
            [0, 1, 0, 0], [1, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 0]]))
        np.testing.assert_array_equal(zero_set(path_and_isolate, path_and_isolate, 4),
                                      [True, False, True, True])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=[__file__], verbosity=2)
    else:
        success, report = write_evidence()
        print(report)
        sys.exit(0 if success else 1)

"""Synthetic, no-raw-data regression checks for the Phase 6 precision witness.

Run with the pinned interpreter.  The fixtures deliberately exercise the C3
identity and topology semantics without loading a public raw benchmark.
"""
from __future__ import annotations

import csv
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


# Importing the wished-for interface is intentional: this verifier is written
# before the production module, so the first run must fail until the feature is
# implemented.
from precision_witness import (  # noqa: E402
    GraphSpec,
    PrecisionWitnessError,
    SPECS,
    assert_pinned_hashes_wellformed,
    build_topology,
    run_precision_witness,
    threshold_decision,
    validate_preflight_spec,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PrecisionWitnessTests(unittest.TestCase):
    """Fixtures keep graph identity, selector, and witness claims inspectable."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.brava = self.root / "brava"
        self.data = self.brava / "datasets" / "abcde"
        self.data.mkdir(parents=True)
        self.output = self.root / "results" / "phase6_precision_witness"

    def write_fixture(self, name: str, edge_text: str, score_text: str,
                      *, expected_nodes: int, expected_arcs: int,
                      expected_targets: int) -> GraphSpec:
        edge = self.data / f"{name}.txt"
        score = self.data / f"{name}-score.txt"
        edge.write_text(edge_text, encoding="utf-8", newline="\n")
        score.write_text(score_text, encoding="utf-8", newline="\n")
        rows = sum(
            1 for line in edge_text.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "%"))
        )
        return GraphSpec(
            graph=name,
            edge_sha256=digest(edge), score_sha256=digest(score),
            nodes=expected_nodes, arcs=expected_arcs,
            selected_targets=expected_targets, raw_rows=rows,
            edge_bytes=edge.stat().st_size, score_rows=expected_nodes,
            score_bytes=score.stat().st_size,
        )

    def test_bounded_constructor_matches_c3_fixture_semantics(self):
        # Label 7 appears only in a loop and must remain a compact node with an
        # empty row; reversed duplicates and loops must not become simple edges.
        spec = self.write_fixture(
            "fixture",
            "# comment\n30 -5\n-5 30\n30 10\n10 30\n7 7\n% comment\n-5 -5\n",
            "0\n0\n0\n0\n",
            expected_nodes=4, expected_arcs=4, expected_targets=1,
        )
        topology = build_topology(spec, self.brava, self.output, payload_bytes=96)
        self.assertEqual(topology.original_ids.tolist(), [-5, 7, 10, 30])
        self.assertEqual(topology.indptr.tolist(), [0, 1, 1, 2, 4])
        self.assertEqual(topology.indices.tolist(), [3, 3, 0, 2])
        self.assertEqual(int(topology.original_ids[1]), 7)
        self.assertEqual(int(topology.indptr[2] - topology.indptr[1]), 0)
        self.assertEqual(topology.raw_rows, 6)
        # Existing C3 code is a small-fixture semantic oracle only.  The raw
        # production path must never call it because it materialises arrays that
        # break the Phase 6 resource contract.
        from analyse_c3_benchmarks import build_csr, load_edges
        c3_edges, c3_nodes = load_edges(self.data / "fixture.txt")
        c3 = build_csr(c3_edges, c3_nodes, symmetrise=True)
        raw = np.loadtxt(self.data / "fixture.txt", dtype=np.int64, comments=("#", "%"), ndmin=2)
        self.assertTrue(np.array_equal(topology.original_ids, np.unique(raw)))
        self.assertTrue(np.array_equal(topology.indptr, c3.indptr))
        self.assertTrue(np.array_equal(topology.indices, c3.indices))

    def test_selector_and_diamond_witness_keep_sorted_score_identity(self):
        # Sorted IDs are [10, 20, 30, 40, 50]; 20 is v.  Its three mutually
        # nonadjacent neighbours share exactly v and 40, so every usable pair
        # has c=2 while v still meets the protocol's degree floor of three.
        spec = self.write_fixture(
            "diamond",
            "20 10\n30 20\n20 50\n10 40\n40 30\n40 50\n",
            "1.0\n0E-20\n1\n1\n1\n",
            expected_nodes=5, expected_arcs=12, expected_targets=1,
        )
        result = run_precision_witness(spec, self.brava, self.output, payload_bytes=96)
        self.assertEqual(result["target_count"], 1)
        target_path = self.output / "diamond_targets.csv"
        witness_path = self.output / "diamond_witnesses.csv"
        with target_path.open(newline="", encoding="utf-8") as stream:
            targets = list(csv.DictReader(stream))
        with witness_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(targets[0]["score_row"], "1")
        self.assertEqual(targets[0]["compact_id"], "1")
        self.assertEqual(targets[0]["original_node_id"], "20")
        self.assertEqual(rows[0]["a_original_node_id"], "10")
        self.assertEqual(rows[0]["b_original_node_id"], "30")
        self.assertEqual(rows[0]["common_neighbor_count"], "2")
        self.assertEqual(rows[0]["rational_numerator"], "2")
        self.assertEqual(rows[0]["rational_denominator"], "24")
        self.assertEqual(rows[0]["usable_pair_count"], "3")
        self.assertEqual(rows[0]["gt_5e15_qualifying_pair_count"], "3")
        self.assertEqual(rows[0]["gt_1e14_qualifying_pair_count"], "3")
        self.assertEqual(result["usable_pair_count"], 3)
        self.assertEqual(result["gt_5e15_qualifying_pair_count"], 3)
        self.assertEqual(result["gt_1e14_qualifying_pair_count"], 3)
        summary = json.loads((self.output / "diamond_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["usable_pair_count"], 3)
        self.assertIn("precision_witness.py", summary["source_sha256"])

    def test_witness_scans_all_pairs_and_prefers_smallest_c_then_ids(self):
        # The first lexicographic pair (10, 30) has c=2 via 20 and 40;
        # (10, 50) has c=1.  A first-witness shortcut would return the wrong
        # lower bound, so this establishes the full bounded scan contract.
        spec = self.write_fixture(
            "minimum",
            "20 10\n20 30\n20 50\n10 40\n40 30\n",
            "1\n0\n1\n1\n1\n",
            expected_nodes=5, expected_arcs=10, expected_targets=1,
        )
        run_precision_witness(spec, self.brava, self.output, payload_bytes=96)
        with (self.output / "minimum_witnesses.csv").open(newline="", encoding="utf-8") as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual((row["a_original_node_id"], row["b_original_node_id"]), ("10", "50"))
        self.assertEqual(row["common_neighbor_count"], "1")
        self.assertEqual(row["usable_pair_count"], "3")

    def test_zero_selected_targets_is_a_completed_control_result(self):
        """Added 2026-09-11 by Claude Opus 5.

        A graph can contain printed zeros and still select NO targets: if every
        printed-zero node's neighbourhood is a clique, no nonadjacent neighbour
        pair exists, and every printed zero is structurally consistent with a
        true zero. That is not an error and not an empty run -- it is the
        control outcome the design predicts for an UNCLAMPED reference graph,
        and it is what all three of amazon, dblp and com-youtube actually
        produce (0 targets among 3,030,420 printed zeros between them).

        Before this test the production path could not express that outcome:
        `_select_targets` fell through to `int(min_degree)` with `min_degree`
        still None, so a legitimate null crashed with a TypeError instead of
        publishing a summary saying zero. The triangle below is the smallest
        graph exhibiting it -- three mutually adjacent nodes, all printed zero.
        """
        spec = self.write_fixture(
            "clique",
            "10 20\n20 30\n10 30\n",
            "0\n0\n0\n",
            expected_nodes=3, expected_arcs=6, expected_targets=0,
        )
        result = run_precision_witness(spec, self.brava, self.output, payload_bytes=96)
        self.assertEqual(result["target_count"], 0)
        # Degrees are reported as 0 because no target was selected -- not because
        # a degree of 0 was observed. The target count is what disambiguates.
        self.assertEqual(result["minimum_degree"], 0)
        self.assertEqual(result["maximum_degree"], 0)
        self.assertEqual(result["total_pair_scan"], 0)
        self.assertEqual(result["usable_pair_count"], 0)
        self.assertEqual(result["gt_5e15_qualifying_pair_count"], 0)
        self.assertEqual(result["gt_1e14_qualifying_pair_count"], 0)
        # A header-only witness file must still be published: a null result is a
        # result, and it has to leave the same artifact trail as a positive one.
        witnesses = self.output / "clique_witnesses.csv"
        self.assertTrue(witnesses.is_file())
        self.assertEqual(witnesses.read_text(encoding="utf-8").strip().count("\n"), 0)

    def test_degree_two_structurally_positive_node_is_a_valid_target(self):
        """Added 2026-09-10 by Claude Opus 5.

        The selector's own predicate is "printed score is zero AND some pair of
        neighbours is nonadjacent". A degree-two node whose two neighbours are
        nonadjacent satisfies it, and is structurally positive for the same
        reason any other selected node is: a-v-b is a length-two shortest path,
        so BC(v) >= 1/c > 0. Two is therefore the structural MINIMUM degree of a
        selectable target, not an anomaly.

        The design pinned a preflight range of [3,18] as "previously reported".
        Nothing in the repository records that measurement, the witness had
        never run, and when it finally did it rejected the majority of its own
        targets: on cit-Patents 424 of 662 selected rows have degree two
        (measured range [2,6]). The counts the same run reproduced exactly --
        709,724 printed zeros and 662 selected -- establish the topology is the
        intended graph, so the degree prediction alone was wrong.

        Path 10-20-30 with 20 scored zero: c = 1 via 20 itself.
        """
        spec = self.write_fixture(
            "path",
            "10 20\n20 30\n",
            "1\n0\n1\n",
            expected_nodes=3, expected_arcs=4, expected_targets=1,
        )
        result = run_precision_witness(spec, self.brava, self.output, payload_bytes=96)
        self.assertEqual(result["target_count"], 1)
        self.assertEqual(result["minimum_degree"], 2)
        self.assertEqual(result["maximum_degree"], 2)
        with (self.output / "path_witnesses.csv").open(newline="", encoding="utf-8") as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(row["degree"], "2")
        self.assertEqual((row["a_original_node_id"], row["b_original_node_id"]), ("10", "30"))
        self.assertEqual(row["common_neighbor_count"], "1")

    def test_pair_scan_budget_replaces_the_degree_ceiling(self):
        """Added 2026-09-10 by Claude Opus 5.

        The old ceiling of 18 was not a resource guard in its own right: it was
        a second consequence of the same wrong inherited degree claim, used to
        state a pair budget of 1,748 * C(18,2) = 267,444. cit-Patents passed
        under it only because its measured maximum is 6; com-lj then failed at
        degree 34, with a measured range of [2,111] and 412 of its 1,086
        targets above 18.

        The real cumulative scan is 1,459 + 293,013 = 294,472 pairs, about 10%
        over the quoted figure -- and the design states these intersection
        scans are constant-extra-memory streaming work, so the count bounds
        time, not memory. Guarding cumulative pairs therefore protects the
        quantity that was actually at stake, while a per-node degree cap
        rejects lawful targets to limit it only indirectly.
        """
        from precision_witness import MAX_TOTAL_PAIR_SCAN, MIN_TARGET_DEGREE

        self.assertEqual(MIN_TARGET_DEGREE, 2)
        # The budget must not bind on either real graph.
        self.assertGreater(MAX_TOTAL_PAIR_SCAN, 294_472)

        # A degree-34 target -- the exact com-lj failure -- must now be accepted.
        hub_edges = "".join(f"0 {n}\n" for n in range(1, 35))
        spec = self.write_fixture(
            "hub", hub_edges, "0\n" + "1\n" * 34,
            expected_nodes=35, expected_arcs=68, expected_targets=1,
        )
        result = run_precision_witness(spec, self.brava, self.output, payload_bytes=96)
        self.assertEqual(result["target_count"], 1)
        self.assertEqual(result["maximum_degree"], 34)
        # A star's centre has C(34,2) nonadjacent pairs, every one usable.
        self.assertEqual(result["total_pair_scan"], 34 * 33 // 2)
        self.assertEqual(result["usable_pair_count"], 34 * 33 // 2)

    def test_clique_candidate_is_structural_zero_and_target_count_fails_closed(self):
        spec = self.write_fixture(
            "clique",
            "1 2\n1 3\n2 3\n",
            "0\n1\n1\n",
            expected_nodes=3, expected_arcs=6, expected_targets=1,
        )
        with self.assertRaisesRegex(PrecisionWitnessError, "selected target count"):
            run_precision_witness(spec, self.brava, self.output, payload_bytes=96)
        self.assertFalse((self.output / "clique_targets.csv").exists())
        self.assertFalse((self.output / "clique_witnesses.csv").exists())

    def test_threshold_boundaries_are_strict_integer_cross_products(self):
        # The design's integer boundary cases must remain independent of float
        # formatting and equality must not be upgraded to a qualifying witness.
        for graph, n, passing_5, passing_1 in (
            ("cit-Patents", 3_764_117, 28, 14),
            ("com-lj", 3_997_962, 25, 12),
        ):
            self.assertTrue(threshold_decision(n, passing_5)["gt_5e15"])
            self.assertFalse(threshold_decision(n, passing_5 + 1)["gt_5e15"])
            self.assertTrue(threshold_decision(n, passing_1)["gt_1e14"])
            self.assertFalse(threshold_decision(n, passing_1 + 1)["gt_1e14"])
        # Equality is not a pass: 2e15 == 5 * ((3-1)(3-2) * 2e14).
        self.assertFalse(threshold_decision(3, 200_000_000_000_000)["gt_5e15"])

    def test_bad_hash_malformed_line_and_workers_fail_before_result_publication(self):
        spec = self.write_fixture(
            "bad",
            "1 2\nnot-an-edge\n",
            "0\n1\n",
            expected_nodes=2, expected_arcs=2, expected_targets=1,
        )
        with self.assertRaisesRegex(PrecisionWitnessError, "malformed edge"):
            run_precision_witness(spec, self.brava, self.output, payload_bytes=96)
        self.assertFalse((self.output / "bad_targets.csv").exists())
        good = self.write_fixture(
            "worker",
            "1 2\n2 3\n",
            "1\n0\n1\n",
            expected_nodes=3, expected_arcs=4, expected_targets=1,
        )
        with self.assertRaisesRegex(PrecisionWitnessError, "workers must be 1"):
            run_precision_witness(good, self.brava, self.output, payload_bytes=96, workers=2)
        changed = GraphSpec(**{**good.__dict__, "edge_sha256": "0" * 64})
        with self.assertRaisesRegex(PrecisionWitnessError, "edge SHA-256"):
            run_precision_witness(changed, self.brava, self.output, payload_bytes=96)
        self.assertFalse((self.output / "worker_targets.csv").exists())

    def test_helper_does_not_import_forbidden_execution_stacks(self):
        # This is deliberately a source-level guard: a witness is local exact
        # integer accounting, never all-source centrality, fitting, or GPU work.
        module_path = Path(sys.modules["precision_witness"].__file__)
        source = module_path.read_text(encoding="utf-8").lower()
        for forbidden in ("networkx", "betweenness_centrality", "sklearn", "torch", "pytorch",
                          "analyse_c3_benchmarks", "load_edges", "zero_set"):
            self.assertNotIn(forbidden, source)

    def test_cli_accepts_one_pinned_graph_and_requires_brava(self):
        # The command is intentionally one graph per process; accepting an
        # all-graphs mode could overlap the disk-backed resource envelopes.
        from probe_c3_precision_witness import build_parser
        parser = build_parser()
        args = parser.parse_args(["--graph", "cit-Patents", "--brava", "C:/brava"])
        self.assertEqual(args.graph, "cit-Patents")
        self.assertEqual(args.workers, 1)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["--graph", "com-lj"])

    def test_accepted_input_preflight_matches_every_production_spec(self):
        """Renamed 2026-09-12 by Claude Opus 5 (Task 6 finding P3-06): the name
        said "both" from when only cit-Patents and com-lj were in scope; the
        witness now runs on all five ABCDE graphs and this iterates SPECS."""
        for spec in SPECS.values():
            validate_preflight_spec(spec)

    def test_every_pinned_hash_is_a_wellformed_sha256(self):
        """Added 2026-09-10 by Claude Opus 5.

        A 61-character com-lj score hash previously survived every check,
        because it had been transcribed identically into both the spec and the
        preflight -- and the identity test above only asserts that those two
        AGREE. Agreement between two copies of the same defect proves nothing.
        This check needs no second copy, which is why it catches that class.
        """
        assert_pinned_hashes_wellformed()
        for name, spec in sorted(SPECS.items()):
            for field, digest in (("edge_sha256", spec.edge_sha256),
                                  ("score_sha256", spec.score_sha256)):
                self.assertEqual(len(digest), 64, f"{name}.{field} is not 64 chars")
                self.assertRegex(digest, r"^[0-9a-f]{64}$", f"{name}.{field} is not lowercase hex")


if __name__ == "__main__":
    unittest.main(verbosity=2)

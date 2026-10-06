"""C3 — zero-set inflation on the external betweenness-learning benchmarks.

Pre-registered in `docs/prereg_C3_benchmark_inflation.md` (2026-09-06). Read that first;
every threshold scored here was fixed there before any value was computed.

WHAT THIS DOES, AND WHY IT IS CHEAP
-----------------------------------
§24.1 of the study doc proves the betweenness zero set is decidable from the radius-1 ego
graph: b(v) = 0 iff v is simplicial. §24.4 turns that into a closed form for the share of
Kendall tau-b's *scored* pairs that are decided by zero-set membership alone, as a function
of the zero fraction z. BRAVA-GNN (github.com/justindachille/BRAVA-GNN) ships, for 14
benchmark graphs and ~400 configurations, BOTH the all-node tau they publish AND a
nonzero-subset tau they compute but never report. That makes the decomposition externally
falsifiable: compute z from structure alone, then predict one of their columns from the other.

Nothing is trained here and no shortest path is ever computed on the corpus. This respects
Decision 9 (nothing gets fit on the Windows env until WSL + cuML is up) — C3 is graph
statistics plus arithmetic on a CSV somebody else published.

THE THREE THINGS THAT CAN QUIETLY MAKE THIS MEANINGLESS
-------------------------------------------------------
1. *Wrong graph regime.* 8 of the 14 graphs are genuinely directed and 5 are undirected;
   computing z under the wrong one measures a different graph than the one their tau was
   scored on. Their own `graph_regimes.py` table is adopted verbatim (see REGIME below)
   rather than re-derived, because re-deriving it is exactly the place to introduce a
   silent disagreement.
2. *Wrong zero rule in the directed case.* §24.1 is an undirected proposition. The directed
   analogue (in-neighbour / out-neighbour form) is derived in the prereg and is VERIFIED
   here against networkx before any z computed under it is used — P4 is a gate, not a
   report: if it fails, nothing else is printed.
3. *Materialising deg^2 pairs.* wiki-Talk and soc-LiveJournal1 have hubs with ~10^5
   neighbours. The check is therefore early-exit, with a vectorised pre-filter that
   disposes of almost every non-simplicial node without a Python-level loop.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

# ---------------------------------------------------------------------------
# Where the external corpus lives. Not vendored into the repo: it is ~3 GB of
# public, re-downloadable data, fetched by BRAVA's own datasets/download.py.
# Override with a positional argument if this copy is removed.
#
# Repointed 2026-09-10 by Claude Opus 5. The previous default was a session-
# scoped agent scratchpad under %TEMP%, which any cleanup deletes -- it was the
# single largest execution risk to the Phase 6 precision witness, since losing
# it makes the witness unrunnable and the C3 corpus unreproducible. The corpus
# now lives under the project at data/brava/ (gitignored: ~3 GB of public,
# re-downloadable third-party data, not ours to vendor). Its identity is
# recorded in results/phase6_brava_corpus_identity_20260910.json and re-checked
# by verify_brava_corpus_identity.py.
# ---------------------------------------------------------------------------
DEFAULT_BRAVA = Path(__file__).resolve().parent / "data" / "brava"

# Output locations, anchored to this file rather than to the cwd (Task 6 finding
# P3-04, Claude Opus 5, 2026-09-12). Until then the two CSVs were written to
# whatever directory the interpreter happened to be in, while verify_docs.py and
# score_c3_results.py read them from the repository root; run from anywhere else
# and the scorer would silently keep reading the previous traversal's files.
ROOT = Path(__file__).resolve().parent
RESULTS_TXT = ROOT / "results" / "RESULTS_c3_benchmarks.txt"
STRUCTURE_CSV = ROOT / "results_c3_structure.csv"
CELLS_CSV = ROOT / "results_c3_cells.csv"
# Where a GATE FAILED transcript goes. It is deliberately NOT the file above:
# score_c3_results.py asserts against RESULTS_c3_benchmarks.txt and
# c3_scored_provenance.json binds its hash, so a failed gate must never
# overwrite the transcript of a traversal that passed.
GATE_FAILED_TXT = ROOT / "results" / "RESULTS_c3_benchmarks.GATE_FAILED.txt"

# BRAVA's regime declarations, copied verbatim from their graph_regimes.py.
# "directed" = genuinely directed, scored as such.
# "undirected" = nx.Graph in their pipeline (the five ABCDE graphs).
# "sym_digraph" = stored as a digraph but semantically undirected; symmetrised at load.
REGIME = {
    "wiki-Talk": "directed",
    "wiki-topcats": "directed",
    "email-EuAll": "directed",
    "web-Google": "directed",
    "soc-Epinions1": "directed",
    "soc-Pokec": "directed",
    "soc-LiveJournal1": "directed",
    "soc-Slashdot0902": "directed",
    "cit-Patents": "undirected",
    "amazon": "undirected",
    "com-youtube": "undirected",
    "dblp": "undirected",
    "com-lj": "undirected",
    "p2p-Gnutella31": "sym_digraph",
}
ABCDE_GRAPHS = {"cit-Patents", "amazon", "com-youtube", "dblp", "com-lj"}


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------
def load_edges(path: Path) -> np.ndarray:
    """Read a two-column edge list into an (E, 2) int64 array of relabelled ids.

    Mirrors BRAVA's datasets/generate_graph.py::load_real_data: the node set is
    exactly the set of ids appearing in the edge list (no isolated nodes are
    invented), and ids are compacted to 0..n-1. Their relabelling is
    first-appearance order and mine is sorted order; that is a permutation, and
    z, w and the floor are all permutation-invariant.
    """
    arr = np.loadtxt(path, dtype=np.int64, comments=("#", "%"), usecols=(0, 1))
    uniq, inv = np.unique(arr, return_inverse=True)
    return inv.reshape(arr.shape).astype(np.int64), len(uniq)


def build_csr(edges: np.ndarray, n: int, symmetrise: bool) -> csr_matrix:
    """Adjacency as CSR with sorted indices, self-loops dropped, duplicates collapsed."""
    src, dst = edges[:, 0], edges[:, 1]
    keep = src != dst  # self-loops carry no betweenness information and break the pair logic
    src, dst = src[keep], dst[keep]
    if symmetrise:
        src, dst = np.concatenate([src, dst]), np.concatenate([dst, src])
    a = csr_matrix((np.ones(len(src), dtype=np.int8), (src, dst)), shape=(n, n))
    a.sum_duplicates()
    a.data[:] = 1
    a.sort_indices()
    return a


# ---------------------------------------------------------------------------
# The zero set
# ---------------------------------------------------------------------------
def _edge_keys(a: csr_matrix, n: int) -> np.ndarray:
    """Sorted int64 keys u*n + v for every arc, for vectorised edge-existence tests.

    Costs 8 bytes per arc (~550 MB on soc-LiveJournal1) and buys a fully vectorised
    has_edge over arrays, which is what makes the pre-filter possible at all.
    """
    rows = np.repeat(np.arange(n, dtype=np.int64), np.diff(a.indptr))
    return np.sort(rows * n + a.indices.astype(np.int64))


def _has_edge(keys: np.ndarray, n: int, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    k = u.astype(np.int64) * n + v.astype(np.int64)
    pos = np.searchsorted(keys, k)
    pos = np.minimum(pos, len(keys) - 1)
    return keys[pos] == k


def zero_set(a_out: csr_matrix, a_in: csr_matrix, n: int) -> np.ndarray:
    """Boolean mask of nodes with betweenness exactly zero, by the local certificate.

    Undirected case (a_in is a_out): v is zero iff N(v) induces a clique (§24.1).
    Directed case: v is zero iff every in-neighbour u and out-neighbour w (u != w)
    has an arc u -> w. Both reduce to the same statement:

        for every u in In(v):  Out(v) \\ {u}  is a subset of  Out(u)

    Strategy: a cheap vectorised pre-filter kills the overwhelming majority of nodes
    (any single witness pair with no connecting arc proves b(v) > 0), then the small
    surviving candidate set is checked exhaustively with early exit.
    """
    out_deg = np.diff(a_out.indptr)
    in_deg = np.diff(a_in.indptr)
    keys = _edge_keys(a_out, n)

    # Vacuously simplicial: no in-neighbours or no out-neighbours means no path can
    # pass through v at all. This is the degree-<2 case of §24.1 in directed form.
    cand = (in_deg > 0) & (out_deg > 0)
    zero = ~cand.copy()

    # --- vectorised pre-filter -------------------------------------------------
    # Probe a handful of (in-neighbour, out-neighbour) witness pairs per candidate.
    # Any probe with u != w and no arc u->w settles b(v) > 0 immediately. Offsets are
    # taken from both ends of the neighbour lists so that the probes are not all
    # drawn from the same (id-ordered, hence often correlated) region of the graph.
    rng = np.random.default_rng(0)
    for probe in range(8):
        idx = np.flatnonzero(cand)
        if idx.size == 0:
            break
        if probe < 4:
            oi = np.array([0, 1, 0, 1])[probe]
            wi = np.array([0, 0, 1, 1])[probe]
            u = a_in.indices[a_in.indptr[idx] + np.minimum(oi, in_deg[idx] - 1)]
            w = a_out.indices[a_out.indptr[idx] + np.minimum(wi, out_deg[idx] - 1)]
        else:
            u = a_in.indices[a_in.indptr[idx] + (rng.random(idx.size) * in_deg[idx]).astype(np.int64)]
            w = a_out.indices[a_out.indptr[idx] + (rng.random(idx.size) * out_deg[idx]).astype(np.int64)]
        informative = u != w  # u == w is not a witness pair; skip without concluding
        missing = informative & ~_has_edge(keys, n, u, w)
        cand[idx[missing]] = False  # settled: nonzero betweenness

    # --- exhaustive check on the survivors ------------------------------------
    # Survivors are dominated by genuinely simplicial nodes (which must be confirmed
    # in full) plus a thin tail of nodes whose random probes happened to hit arcs.
    survivors = np.flatnonzero(cand)
    for v in survivors:
        ins = a_in.indices[a_in.indptr[v]:a_in.indptr[v + 1]]
        outs = a_out.indices[a_out.indptr[v]:a_out.indptr[v + 1]]
        simplicial = True
        for u in ins:
            need = outs[outs != u]
            if need.size == 0:
                continue
            row = a_out.indices[a_out.indptr[u]:a_out.indptr[u + 1]]  # sorted
            pos = np.searchsorted(row, need)
            pos = np.minimum(pos, max(len(row) - 1, 0))
            if len(row) == 0 or not np.all(row[pos] == need):
                simplicial = False
                break  # early exit: one missing arc is a complete proof
        zero[v] = simplicial
    return zero


# ---------------------------------------------------------------------------
# Closed forms from §24.4 / §24.5 — imported rather than re-typed where possible
# ---------------------------------------------------------------------------
def shares(n: int, n_z: int) -> dict:
    """Boundary share w, its asymptotic form, and the tau-b floor.

    Deliberately re-derived from counts here rather than calling
    analyse_betweenness.boundary_share, because that function is wired to this
    project's own cached target columns (it takes a betweenness VECTOR). The
    agreement between the two is asserted in main() at 1e-9 - see
    `assert_floor_matches_pipeline` - so a divergence from the single source of
    truth cannot pass silently.

    CORRECTED 2026-09-12 by Claude Opus 5 (Task 6 finding P3-02). Until then
    `tau_floor` was w_exact * sqrt(1 - z^2), which is NOT the pipeline's floor.
    The pipeline's is cross / sqrt(scoreable * total) = w_exact *
    sqrt(scoreable / total), and scoreable / total = 1 - n_z (n_z - 1) / (n (n - 1))
    equals 1 - z^2 only in the n -> inf limit; the two differ by O(z / n) in the
    floor (about 3e-5 on ca-GrQc, below 1e-6 on the BRAVA graphs, all of which
    have n >= 3e5). Also until then the docstring promised a 1e-9 identity
    assertion that did not exist - main() asserted only |w_exact - w_asym| < 5e-3,
    which is an asymptotic sanity check, not an identity. Both are now true.
    The approximate form is kept under a name that says what it is.

    Consequence for stored artefacts: `results_c3_structure.csv`,
    `results_c3_scored_cells.csv` (column `tau_floor`) and everything
    `score_c3_results.py` / `audit_c4_support.py` / `c4_two_numbers.py` derive
    through this function change in the sixth decimal or below on the next
    traversal. Whether any registered P3 hit (tau_all <= tau_floor + 0.05)
    flips is a question for that traversal's report, not something to assume
    here.
    """
    n_m = n - n_z
    total = n * (n - 1) / 2
    scoreable = total - n_z * (n_z - 1) / 2
    cross = n_z * n_m
    w_exact = cross / scoreable if scoreable > 0 else float("nan")
    z = n_z / n
    w_asym = 2 * z / (1 + z)
    return {
        "n": n, "n_zero": n_z, "n_nonzero": n_m, "z": z,
        "total_pairs": total, "scoreable_pairs": scoreable, "cross_pairs": cross,
        "w_exact": w_exact, "w_asym": w_asym,
        # Exact tau-b floor of the zero-skill reference method: every boundary
        # pair concordant, nothing else, over tau-b's denominator with n2 = 0.
        # Same expression as analyse_betweenness.boundary_share.
        "tau_floor": cross / np.sqrt(scoreable * total) if scoreable > 0 else float("nan"),
        # The large-n closed form w * sqrt(1 - z^2) that the study quotes; kept
        # for the prose, never for a hit test.
        "tau_floor_wz_approx": w_exact * np.sqrt(1 - z * z),
        "tau_floor_asym": 2 * z * np.sqrt((1 - z) / (1 + z)),
    }


def assert_floor_matches_pipeline(s: dict, tol: float = 1e-9) -> None:
    """Pin `shares()` to analyse_betweenness.boundary_share at 1e-9.

    Added 2026-09-12 by Claude Opus 5 (P3-02): the assertion the shares()
    docstring had always claimed. Builds the smallest betweenness vector with
    the same zero count - n_z zeros then ones - because boundary_share only
    looks at the zero/nonzero partition, and compares the floor and the share.
    Cheap (one boolean pass over n entries) even at cit-Patents scale.
    """
    from analyse_betweenness import boundary_share

    bc = np.ones(int(s["n"]), dtype=np.float64)
    bc[: int(s["n_zero"])] = 0.0
    ref = boundary_share(bc)
    for mine, theirs in (("tau_floor", "tau_floor"), ("w_exact", "w_exact"),
                         ("scoreable_pairs", "scoreable"), ("cross_pairs", "cross")):
        assert abs(s[mine] - ref[theirs]) <= tol * max(1.0, abs(ref[theirs])), (
            f"shares()[{mine}] = {s[mine]!r} disagrees with "
            f"analyse_betweenness.boundary_share()[{theirs}] = {ref[theirs]!r}")


def predict_tau_all(tau_filt: np.ndarray, s: dict) -> np.ndarray:
    """P1's mixture identity: predict published all-node tau-b from nonzero-subset tau.

    Assumes PERFECT zero-set classification, so every boundary pair (n_z * n_m of
    them) is concordant, and the nonzero block contributes tau_filt * C(n_m, 2).
    Divide by tau-b's denominator sqrt(scoreable * total) — NOT by scoreable; that
    confusion is precisely the error §24.5 was revised for on 2026-09-05.
    """
    n_m = s["n_nonzero"]
    cross = s["n_zero"] * n_m
    nonzero_pairs = n_m * (n_m - 1) / 2
    return (cross + tau_filt * nonzero_pairs) / np.sqrt(s["scoreable_pairs"] * s["total_pairs"])


def predict_tau_all_tied(tau_filt: np.ndarray, s: dict) -> np.ndarray:
    """The same mixture when the PREDICTIONS are tied on the zero set as well.

    POST-HOC — not registered. It is here because the registered form (above) failed
    badly and this one explains the failure exactly; see §26i of the study doc.

    tau-b's denominator is sqrt((n0 - n1)(n0 - n2)). `predict_tau_all` assumes n2 = 0.
    CORRECTED 2026-09-07: this docstring used to justify that by saying the assumption
    "is right for this project's forests (continuous output, no ties)". That is FALSE as
    a statement about the forests - `cache_oof_ca-GrQc.npz` key `betweenness|0|node|0`
    holds 201 distinct values over 4,158 nodes, and 98 over the 2,288 true zeros, because
    a random forest averages a finite set of leaf means. What n2 = 0 is actually right
    for is the HYPOTHETICAL zero-skill method the floor describes (`analyse_betweenness.py`
    lines 136-170), which is defined to score continuously and was checked against 200
    simulated draws to 5.1e-4. No reported number changes: every tau this project reports
    comes from scipy's `kendalltau`, which is tie-aware and counts the forests' real ties
    itself, and the floor is only ever printed as a margin reference, never used to
    compute a reported tau. The assumption IS wrong for a model whose preprocessing
    zeroes the adjacency rows of the zero set: those nodes
    then have identical embeddings, hence one identical score, hence n2 = n1 = C(n_z, 2).
    The denominator collapses from the geometric mean sqrt(scoreable * total) to
    `scoreable`, and the mixture becomes the plain arithmetic one:

        tau_all = w + (1 - w) * tau_filtered

    which is precisely the form §24.5 published before 2026-09-05 and then revised away
    as an error. It was not an error for this class of method — it was an error for THIS
    project's estimator. Both forms are correct; which applies is a property of the
    scored predictions, not of the metric.
    """
    return s["w_exact"] + (1 - s["w_exact"]) * tau_filt


# ---------------------------------------------------------------------------
# P4 — the gate
# ---------------------------------------------------------------------------
def gate_directed_rule(n_graphs: int = 30) -> tuple[bool, str]:
    """Verify the directed zero rule exhaustively against networkx exact betweenness."""
    import networkx as nx

    rng = np.random.default_rng(20260906)
    mismatches = 0
    checked = 0
    for i in range(n_graphs):
        n = int(rng.integers(30, 300))
        p = float(rng.uniform(0.005, 0.12))
        g = nx.gnp_random_graph(n, p, seed=int(rng.integers(1 << 30)), directed=True)
        a = csr_matrix(nx.to_scipy_sparse_array(g, format="csr", dtype=np.int8))
        a.sort_indices()
        got = zero_set(a, csr_matrix(a.T.tocsr()), n)
        bc = nx.betweenness_centrality(g, normalized=False)  # once per graph, not per node
        want = np.array([bc[v] == 0 for v in range(n)])
        mismatches += int((got != want).sum())
        checked += n
    ok = mismatches == 0
    return ok, f"directed rule: {mismatches} mismatches over {checked} nodes in {n_graphs} random digraphs"


def check_tie_denominator() -> tuple[bool, str]:
    """Prove, on synthetic data, that BOTH mixture forms are right for their own tie regime.

    This is a claim about scipy's tau-b, not about any graph, so it is checked directly
    rather than argued: build a truth column with an exact zero block, score it with
    (a) continuous predictions and (b) predictions tied on that block, and confirm each
    matches its formula to 1e-9. Without this, "the denominator collapses" is arithmetic
    on a whiteboard; with it, the C3 diagnosis rests on a executed check.
    """
    from scipy.stats import kendalltau

    rng = np.random.default_rng(7)
    n, n_z = 4000, 2600
    truth = np.concatenate([np.zeros(n_z), rng.random(n - n_z) + 0.5])
    s = shares(n, n_z)
    lines, ok = [], True

    # (a) continuous predictions everywhere: no prediction ties, geometric denominator.
    # They must still SEPARATE the zero set perfectly (zeros drawn below nonzeros), because
    # that is what the formula assumes; a randomly-ordered prediction tests nothing.
    pred_c = np.concatenate([rng.random(n_z), rng.random(n - n_z) + 1.0])
    tau_all = kendalltau(pred_c, truth).statistic
    tau_f = kendalltau(pred_c[n_z:], truth[n_z:]).statistic
    got = predict_tau_all(np.array([tau_f]), s)[0]
    d = abs(got - tau_all)
    ok &= d < 1e-9
    lines.append(f"  continuous predictions  tau={tau_all:+.6f} formula={got:+.6f} |d|={d:.2e}")

    # (b) predictions tied on the zero block, and ranked below it: n2 = n1, arithmetic form.
    pred_t = np.concatenate([np.zeros(n_z), rng.random(n - n_z) + 1.0])
    tau_all = kendalltau(pred_t, truth).statistic
    tau_f = kendalltau(pred_t[n_z:], truth[n_z:]).statistic
    got = predict_tau_all_tied(np.array([tau_f]), s)[0]
    d = abs(got - tau_all)
    ok &= d < 1e-9
    lines.append(f"  tied on the zero set    tau={tau_all:+.6f} formula={got:+.6f} |d|={d:.2e}")
    return ok, "\n".join(lines)


def gate_project_table() -> tuple[bool, str]:
    """Reproduce §24.4's published w table from raw edge lists, through this file's code.

    This is the strongest available check that `zero_set` and `shares` agree with the
    pipeline: it starts from `data/<net>.txt` and touches none of the cached feature or
    target columns, yet must land on the same five percentages the study doc prints.

    The largest connected component is taken here because that is what stage1 does; the
    external corpus is NOT restricted that way, because BRAVA's loader is not (their node
    set is exactly the ids appearing in the edge list). Mixing the two conventions would
    compute z for a different graph than the tau it is being compared against — which is
    the whole reason this gate exists.
    """
    from scipy.sparse.csgraph import connected_components

    published = {  # study_doc_v2.md §24.4, "w exact" column, in percent
        "ca-GrQc": 71.0008, "ca-HepTh": 65.3519, "p2p-Gnutella08": 43.5280,
        "email-Eu-core": 26.2787, "facebook_combined": 15.6164,
    }
    lines, ok = [], True
    for net, want in published.items():
        p = Path("data") / f"{net}.txt"
        if not p.exists():
            # This five-graph check is a prerequisite, not an optional inventory.
            # Skipping a missing graph would certify a partial (even empty) corpus.
            lines.append(f"  {net:<20} FAIL (no {p})")
            ok = False
            continue
        edges, n = load_edges(p)
        a = build_csr(edges, n, symmetrise=True)
        _, lab = connected_components(a, directed=False)
        keep = np.flatnonzero(lab == np.argmax(np.bincount(lab)))
        sub = a[keep][:, keep].tocsr()
        sub.sort_indices()
        s = shares(len(keep), int(zero_set(sub, sub, len(keep)).sum()))
        got = s["w_exact"] * 100
        agree = abs(got - want) < 5e-4  # the doc prints four decimals
        ok &= agree
        lines.append(f"  {net:<20} w = {got:8.4f}%  published {want:8.4f}%  "
                     f"{'OK' if agree else 'MISMATCH'}")
    return ok, "\n".join(lines)


# The two ABCDE files whose shipped scores are quantised finely enough that real
# positives round to zero. HARD-CODED on purpose, 2026-09-07, replacing an unsound
# auto-detector. Read the note below before changing either the set or the mechanism.
#
# WHY HARD-CODED. The previous gate inferred "clamped" from a mass of >= 100 nodes
# sitting on a file's smallest positive value. That heuristic is unsound in BOTH
# directions, and an adversarial review demonstrated a concrete false pass: on 100
# disconnected three-node paths with EXACT ground truth, a deliberately broken rule
# that calls every node nonzero made the old gate return True, relabel the exact
# minimum as "clamped at 1.0e+00", and excuse 200 genuine rule errors. Legitimate
# graph symmetry produces repeated minima, so the test fires on correct data; and 100
# is an absolute count with no relation to corpus size, so heavy truncation can leave
# a real artefact below it and be missed. Tightening the number narrows the
# adversarial surface without closing it. This corpus is 14 graphs - small enough that
# direct verification beats a statistical proxy outright. Reach for a proxy when the
# corpus is too large to check by hand; this one is not.
#
# HOW THESE TWO WERE IDENTIFIED, independently of the detector they replace:
#   1. Every value in all five shipped score files is an exact integer multiple of
#      1e-14 - checked on the printed decimal text with Decimal, not on floats, over
#      15,043,174 values, with zero exceptions. The release is rounded to 14 decimal
#      places. This establishes quantisation for the whole release without reference
#      to any per-file mass or threshold.
#      COUNT CORRECTED 2026-09-07: this comment and the prereg's third amendment both
#      said 14,943,174, which is 100,000 too small - a transcription slip in the summed
#      figure, caught by audit_c4_support.py's independent streaming recount. The
#      per-file counts (3,764,117 + 3,997,962 + 2,146,057 + 4,000,148 + 1,134,890) were
#      always right and sum to 15,043,174, and "zero exceptions" is unchanged, so the
#      argument this number supports is untouched; only the total was mistyped.
#   2. Rounding to that grid only reaches zero where a graph has true positives below
#      half a grid step. cit-Patents and com-lj are the two files that actually show
#      it: 662 and 1,086 nodes where the certificate says nonzero and the file says
#      zero, with the reverse direction occurring zero times. amazon, dblp and
#      com-youtube show no discrepancy in either direction.
# So the set below is a verified observation about two named files, not the cached
# output of the heuristic that was removed.
CLAMPED_ABCDE = {"cit-Patents", "com-lj"}


def detect_quantisation(scores: np.ndarray) -> dict:
    """NON-BLOCKING DIAGNOSTIC. Never gate on this - see the warning.

    Reports what a human should look at when a NEW file enters the corpus: the grid
    the values appear to lie on, the smallest positive value, and how many nodes sit
    on it.

    KNOWN UNSOUND FOR AUTOMATIC GATING. The mass-on-minimum signal this reports is
    exactly the heuristic that was removed from the gate on 2026-09-07, for the
    reasons in the CLAMPED_ABCDE comment: it false-passes on legitimate graph
    symmetry and false-negatives under heavy truncation. Its output must not change
    any downstream classification, exclusion, or verdict. It exists so a person can
    look at a new file and decide; nothing may branch on it.

    The `grid_exact` field is the trustworthy part - "every value is a multiple of g"
    is a checkable property of the file, not an inference from a threshold.
    """
    nz = scores[scores > 0]
    if nz.size == 0:
        return {"grid": None, "grid_exact": False, "min_pos": None, "at_min": 0}
    m = float(nz.min())
    scaled = scores * 1e14
    grid_exact = bool(np.all(np.abs(scaled - np.round(scaled)) < 1e-6))
    return {"grid": 1e-14 if grid_exact else None,
            "grid_exact": grid_exact,
            "min_pos": m,
            "at_min": int((scores == m).sum())}


def gate_undirected_abcde(brava: Path) -> tuple[bool, str, dict]:
    """Check the undirected rule against the ABCDE release's shipped ground-truth BC.

    Two files - cit-Patents and com-lj, named in CLAMPED_ABCDE above - carry scores
    quantised finely enough that true positives round to zero. Prereg P4 registered
    this contingency ahead of the run ("conditional on those scores being exact rather
    than sampled; if the release ... shows they are approximate, this arm is reported
    as consistency, not verification"), and the membership of that set is now a
    hard-coded, independently verified fact rather than something inferred at runtime.

    Criterion, by file:
      NOT in CLAMPED_ABCDE - both mismatch directions must be zero, as registered.
      IN CLAMPED_ABCDE     - only `rule = 0 & shipped > 0` can fail the gate. Rounding
                             pushes true nonzeros DOWN to a printed zero; it can never
                             lift a true zero UP to a printed positive. So that
                             direction survives as a real test on quantised data,
                             while the opposite direction is counted and reported but
                             cannot fail a file already known to be quantised.

    This is a genuine WEAKENING of the gate on those two files, not a strengthening,
    and it is recorded as such in the pre-registration. It supports the consistency
    downgrade; it does not establish exactness.
    """
    lines = []
    detail = {}
    ok = True
    for name in sorted(ABCDE_GRAPHS):
        gp = brava / "datasets" / "abcde" / f"{name}.txt"
        sp = brava / "datasets" / "abcde" / f"{name}-score.txt"
        if not (gp.exists() and sp.exists()):
            lines.append(f"  {name:<14} FAIL (required input not downloaded)")
            ok = False
            continue
        edges, n = load_edges(gp)
        a = build_csr(edges, n, symmetrise=True)
        got = zero_set(a, a, n)
        # Score file: BRAVA's import_abcde_datasets.py reads it as one score per line
        # in node-id order. Load defensively and say so if the shape disagrees.
        sc = np.loadtxt(sp, dtype=np.float64)
        if sc.ndim == 2:
            sc = sc[:, -1]
        if len(sc) != n:
            lines.append(f"  {name:<14} FAIL (score rows {len(sc)} != nodes {n})")
            ok = False
            continue
        want = sc == 0

        quantised = name in CLAMPED_ABCDE      # hard-coded, NOT detected
        diag = detect_quantisation(sc)          # reported only, never branched on

        false_zero = int((got & ~want).sum())   # rule=0, shipped>0 - falsifying
        under = int((~got & want).sum())        # rule>0, shipped=0 - rounding artefact
        detail[name] = {"false_zero": false_zero, "under": under,
                        "quantised": quantised, "n": n, "diagnostic": diag,
                        # main predicts BRAVA's filtered column, so it needs the
                        # observed SHIPPED support rather than a structural fallback.
                        # clamped is the legacy name for the registered two-file arm,
                        # not a newly inferred rounding mechanism or precision flag.
                        "n_zero_shipped": int(want.sum()), "clamped": quantised}
        graph_ok = (false_zero == 0) if quantised else (false_zero == 0 and under == 0)
        ok &= graph_ok
        if quantised:
            lines.append(f"  {name:<14} {false_zero} rule failures over {n} nodes "
                         f"(CONSISTENCY only: known-quantised file, grid 1e-14; "
                         f"{under} sub-grid zeros)")
        else:
            lines.append(f"  {name:<14} {false_zero + under} mismatches over {n} nodes"
                         f"  (both directions tested)")
    return ok, "\n".join(lines), detail


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None, out_root: Path | None = None) -> int:
    """Run the traversal. `out_root` relocates every output (tests only).

    All three artefacts - the transcript and the two CSVs - are written to
    staging files beside their final names and promoted with os.replace only
    once the whole traversal has succeeded, so an exception half-way through
    (or a failed gate) leaves the previous traversal's files exactly as they
    were. Added 2026-09-12 by Claude Opus 5 (P3-04); see GATE_FAILED_TXT.
    """
    import os

    args = sys.argv[1:] if argv is None else argv
    brava = Path(args[0]) if args else DEFAULT_BRAVA
    if out_root is None:
        out_txt, struct_csv, cells_csv, failed_txt = (
            RESULTS_TXT, STRUCTURE_CSV, CELLS_CSV, GATE_FAILED_TXT)
    else:
        out_root = Path(out_root)
        out_txt = out_root / "results" / RESULTS_TXT.name
        struct_csv = out_root / STRUCTURE_CSV.name
        cells_csv = out_root / CELLS_CSV.name
        failed_txt = out_root / "results" / GATE_FAILED_TXT.name
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    staged: dict[Path, Path] = {}          # final -> staging, promoted at the end

    def stage(final: Path) -> Path:
        tmp = final.with_name(final.name + ".staging")
        staged[final] = tmp
        return tmp

    rep = []

    def say(s=""):
        print(s)
        rep.append(s)

    say("=" * 78)
    say("C3 — zero-set inflation on the BRAVA-GNN benchmark corpus")
    say("Pre-registration: docs/prereg_C3_benchmark_inflation.md")
    say("=" * 78)

    # ---- P4 gate first. Nothing else runs if this fails. --------------------
    say("\n[P4 gate] directed rule vs networkx exact betweenness")
    t0 = time.time()
    ok_dir, msg = gate_directed_rule()
    say(f"  {msg}  ({time.time() - t0:.1f}s)")
    say("\n[check] both mixture forms against scipy tau-b on synthetic tie regimes")
    ok_tie, msg_tie = check_tie_denominator()
    say(msg_tie)
    say("\n[P4 gate] undirected rule + closed forms vs this project's published §24.4 table")
    ok_proj, msg3 = gate_project_table()
    say(msg3)
    say("\n[P4 gate] undirected rule vs ABCDE shipped ground-truth betweenness")
    ok_und, msg2, abcde_detail = gate_undirected_abcde(brava)
    say(msg2)
    if not (ok_dir and ok_und and ok_proj and ok_tie
            and set(abcde_detail) == ABCDE_GRAPHS):
        say("\nGATE FAILED — P1/P2/P3 not reported (prereg §3, P4).")
        say(f"(transcript written to {failed_txt.name}; {out_txt.name} left untouched)")
        # Sidecar, not the transcript: see GATE_FAILED_TXT.
        failed_txt.write_text("\n".join(rep), encoding="utf-8")
        return 1
    say("  GATE PASSED")

    # ---- structural quantities per graph ------------------------------------
    say("\n[structure] zero fraction, boundary share and tau floor per graph")
    rows = []
    for name, regime in sorted(REGIME.items()):
        sub = "abcde" if name in ABCDE_GRAPHS else "raw"
        gp = brava / "datasets" / sub / f"{name}.txt"
        if not gp.exists():
            say(f"  {name:<18} MISSING {gp}")
            continue
        t0 = time.time()
        edges, n = load_edges(gp)
        sym = regime in ("undirected", "sym_digraph")
        a = build_csr(edges, n, symmetrise=sym)
        a_in = a if sym else csr_matrix(a.T.tocsr())
        z_mask = zero_set(a, a_in, n)
        s = shares(n, int(z_mask.sum()))
        s["graph"] = name
        s["regime"] = regime
        s["arcs"] = int(a.nnz)
        s["seconds"] = round(time.time() - t0, 1)
        # Keep the graph certificate separate from the support of BRAVA's scored
        # target. On the two clamped files, their keep=true_arr>0 uses the latter.
        detail = abcde_detail.get(name, {})
        n_zero_shipped = detail.get("n_zero_shipped", s["n_zero"])
        shipped = shares(n, n_zero_shipped)
        s["n_zero_shipped"] = n_zero_shipped
        s["z_shipped"] = shipped["z"]
        s["w_shipped"] = shipped["w_exact"]
        s["tau_floor_shipped"] = shipped["tau_floor"]
        s["clamped"] = detail.get("clamped", False)
        # The two forms of w must agree to O(1/n); assert that, do not print past it.
        # This is an asymptotic sanity check. The IDENTITY check - shares() against
        # the pipeline's boundary_share at 1e-9 - is the line after it (P3-02).
        assert abs(s["w_exact"] - s["w_asym"]) < 5e-3, f"{name}: w forms disagree grossly"
        assert_floor_matches_pipeline(s)
        assert_floor_matches_pipeline(shipped)
        rows.append(s)
        say(f"  {name:<18} {regime:<12} n={n:>9,d} arcs={a.nnz:>11,d} "
            f"z={s['z']:.4f} w={s['w_exact']:.4f} floor={s['tau_floor']:.4f} "
            f"({s['seconds']}s)")

    struct = pd.DataFrame(rows).set_index("graph")
    assert set(struct.index) == set(REGIME), "Incomplete corpus: do not score P1-P3"
    struct.to_csv(stage(struct_csv))

    # ---- pair BRAVA's shipped plain / _filtered columns ----------------------
    res = pd.read_csv(brava / "results" / "betweenness" / "all_results.csv")
    res = res.set_index("Algorithm")
    filt = res[res.index.str.endswith("_filtered")]
    filt.index = filt.index.str.removesuffix("_filtered")
    plain = res[~res.index.str.endswith("_filtered")]
    common = plain.index.intersection(filt.index)
    say(f"\n[pairing] {len(plain)} plain rows, {len(filt)} filtered rows, "
        f"{len(common)} configurations with both")

    recs = []
    for g in struct.index:
        if g not in plain.columns:
            continue
        s = struct.loc[g].to_dict()
        # P1 predicts THEIR column, so its zero count must describe THEIR target.
        # P2 and registered P3 retain independently measured structural z/floor.
        shipped = shares(int(s["n"]), int(s["n_zero_shipped"]))
        ta = pd.to_numeric(plain.loc[common, g], errors="coerce")
        tf = pd.to_numeric(filt.loc[common, g], errors="coerce")
        m = ta.notna() & tf.notna()
        pred = predict_tau_all(tf[m].to_numpy(), shipped)
        pred_t = predict_tau_all_tied(tf[m].to_numpy(), shipped)
        occurrences = {}
        for alg, a_, f_, p_, pt_ in zip(ta[m].index, ta[m], tf[m], pred, pred_t):
            occurrence = occurrences.get(alg, 0)
            occurrences[alg] = occurrence + 1
            # baseline_* is the masked family supported by the code diagnosis.
            # Unknown/external prediction ties are not silently inferred as masked.
            masked = alg.startswith("baseline_")
            recs.append({"graph": g, "algorithm": alg, "tau_all": a_, "tau_filtered": f_,
                         "occurrence": occurrence, "masked_family": masked,
                         "tau_all_pred": p_, "err": p_ - a_,
                         "tau_all_pred_tied": pt_, "err_tied": pt_ - a_,
                         "drop": a_ - f_, "z": s["z"],
                         "tau_floor": s["tau_floor"], "w_exact": s["w_exact"],
                         # The form the pre-registration wrote down for P3
                         # (prereg_C3_benchmark_inflation.md: tau_floor = w*sqrt(1-z^2)).
                         # `tau_floor` above is the exact pipeline floor (P3-02).
                         "tau_floor_registered": s["tau_floor_wz_approx"],
                         "z_shipped": shipped["z"], "w_shipped": shipped["w_exact"],
                         "floor_regime": shipped["w_exact"] if masked else shipped["tau_floor"]})
    cells = pd.DataFrame(recs)
    cells.to_csv(stage(cells_csv), index=False)
    say("[support] P1 uses shipped target zeros; P2/P3 registered tests use structural zeros.")
    for g in struct.index[struct["clamped"]]:
        s = struct.loc[g]
        say(f"  {g}: structural zeros={int(s['n_zero'])}, shipped zeros={int(s['n_zero_shipped'])}; "
            f"w {s['w_exact']:.7f} -> {s['w_shipped']:.7f}")
    say(f"[pairing] {len(cells)} paired (algorithm, graph) cells across "
        f"{cells['graph'].nunique()} graphs")

    # ---- P1 -----------------------------------------------------------------
    mae = cells["err"].abs().median()
    mse = cells["err"].median()
    p1 = (mae <= 0.05) and (mse >= 0)
    say("\n[P1] mixture identity predicts published all-node tau")
    say(f"  median |error| = {mae:.4f}   (registered threshold <= 0.05)")
    say(f"  median  error  = {mse:+.4f}   (registered sign >= 0)")
    say(f"  P1: {'SUPPORTED' if p1 else 'FALSIFIED'}")

    # POST-HOC, and labelled as such wherever it is quoted: the tie-matched form.
    mae_t = cells["err_tied"].abs().median()
    say("\n[P1 diagnosis — POST-HOC, NOT REGISTERED] tie-matched mixture w + (1-w)*tau_f")
    say(f"  median |error| = {mae_t:.4f}   (registered form above: {mae:.4f})")
    say(f"  max    |error| = {cells['err_tied'].abs().max():.4f}")
    say("  per-graph median signed error, registered form vs tie-matched:")
    for g in sorted(cells["graph"].unique()):
        sub = cells[cells.graph == g]
        say(f"    {g:<18} z={sub['z'].iloc[0]:.4f}  geometric {sub['err'].median():+.4f}"
            f"   tied {sub['err_tied'].median():+.4f}")

    # ---- P2 -----------------------------------------------------------------
    from scipy.stats import spearmanr
    per_graph = cells.groupby("graph").agg(drop=("drop", "median"), z=("z", "first"))
    rho = spearmanr(per_graph["z"], per_graph["drop"]).statistic
    p2 = rho >= 0.5
    say("\n[P2] median drop tracks z across graphs (secondary; see prereg §0)")
    say(f"  Spearman rho = {rho:.3f} over {len(per_graph)} graphs "
        f"(registered threshold >= 0.5)")
    say(f"  P2: {'SUPPORTED' if p2 else 'FALSIFIED'}")

    # ---- P3 -----------------------------------------------------------------
    say("\n[P3] published numbers within 0.05 of the free floor")
    # The registered test uses the floor AS PRE-REGISTERED, w*sqrt(1-z^2). Since
    # 2026-09-12 (P3-02) `tau_floor` holds the exact pipeline floor instead, which
    # exceeds the registered form by O(z/n) - under 1e-6 on every BRAVA graph.
    # The verdict is scored on the registered column so the registration is
    # honoured to the letter; the exact-floor hit count is printed beside it and
    # the two are asserted to agree, so a divergence would be a transcript
    # difference, not a silent re-scoring.
    hits = []
    exact_disagreements = []
    for g, sub in cells.groupby("graph"):
        floor = sub["tau_floor_registered"].iloc[0]
        floor_exact = sub["tau_floor"].iloc[0]
        n_at = int((sub["tau_all"] <= floor + 0.05).sum())
        n_at_exact = int((sub["tau_all"] <= floor_exact + 0.05).sum())
        if n_at_exact != n_at:
            exact_disagreements.append((g, n_at, n_at_exact))
        # The floor that actually applies to a tie-matched scorer is w itself: with
        # n2 = n1 the sqrt(1 - z^2) discount disappears. Reported alongside, post-hoc.
        w = sub["w_exact"].iloc[0]
        n_at_w = int((sub["tau_all"] <= w + 0.05).sum())
        hits.append((g, floor, w, sub["tau_all"].min(), n_at, n_at_w, len(sub)))
    n_graphs_hit = sum(1 for h in hits if h[4] > 0)
    n_graphs_hit_w = sum(1 for h in hits if h[5] > 0)
    p3 = n_graphs_hit >= 7
    for g, floor, w, lo, k, kw, tot in sorted(hits):
        say(f"    {g:<18} floor={floor:.4f} (tied floor w={w:.4f})  min published tau={lo:.4f}  "
            f"{k}/{tot} under floor+0.05  |  {kw}/{tot} under w+0.05")
    say(f"  POST-HOC, against the tie-matched floor w: {n_graphs_hit_w}/{len(hits)} graphs")
    max_gap = float((cells["tau_floor"] - cells["tau_floor_registered"]).abs().max())
    say(f"  registered floor w*sqrt(1-z^2) vs exact cross/sqrt(S*T): max gap {max_gap:.2e}; "
        f"per-graph hit counts under the exact floor "
        f"{'identical' if not exact_disagreements else 'DIFFER: ' + str(exact_disagreements)}")
    assert not exact_disagreements, (
        "P3 hit counts differ between the registered and the exact floor; report "
        f"this rather than picking one: {exact_disagreements}")
    matched_hits = cells.assign(hit=cells.tau_all <= cells.floor_regime + 0.05).groupby("graph").hit.any()
    say(f"  POST-HOC, masked family uses shipped w, others geometric: {int(matched_hits.sum())}/14 graphs")
    say(f"  graphs with at least one such configuration: {n_graphs_hit}/{len(hits)} "
        f"(registered threshold >= 7)")
    say(f"  P3: {'SUPPORTED' if p3 else 'FALSIFIED'}")

    say("\n" + "=" * 78)
    say(f"VERDICT  P1 {'PASS' if p1 else 'FAIL'} | P2 {'PASS' if p2 else 'FAIL'} | "
        f"P3 {'PASS' if p3 else 'FAIL'} | P4 PASS (gate)")
    say("=" * 78)
    stage(out_txt).write_text("\n".join(rep), encoding="utf-8")
    # Everything succeeded: promote the staging files over the previous
    # traversal's outputs. os.replace is atomic per file on both NTFS and POSIX.
    for final, tmp in staged.items():
        os.replace(tmp, final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

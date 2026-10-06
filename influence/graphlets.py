"""
graphlets.py
============
Graphlet orbit counts - the honest test of the subgraph tier.

WHY THIS EXISTS
---------------
The depth-versus-richness result (study doc section 20) says richness helps the
structural target and nothing else. Its standing caveat has always been that
the subgraph tier is thin: `ego_betweenness`, `triangle_count` (which is
algebraically derived from node-tier columns anyway) and `ball2_edges`. Three
features, one of which is not information. Concluding "subgraph structure does
not help" from that is concluding something about our table rather than about
networks.

Graphlet orbits are the standard answer. A graphlet is a small connected
induced subgraph; an ORBIT is a position within one, up to automorphism. The
orbit vector of a node counts, for each such position, how many times the node
occupies it. For graphlets on up to 4 nodes there are 15 orbits; on up to 5
there are 73.

WHY WE USE ORCA RATHER THAN WRITING IT
--------------------------------------
Naive orbit counting enumerates every connected 4-subgraph. ORCA instead
counts the few expensive orbits directly and recovers the rest from a system
of linear equations relating them, which is far faster.

This is the same call already made for the generators in generators.py:
implement what IS the contribution, use a reference implementation for what is
merely an input, and verify it. The contribution here is the radius framing,
not the counting algorithm. So `brute_force_node_orbits` below enumerates every
connected induced subgraph directly and classifies it from first principles,
and verify_pipeline.py checks ORCA against it. If they ever disagree, we find
out.

THE PART THAT IS OURS: ORBITS HAVE DIFFERENT RADII
--------------------------------------------------
Every treatment of graphlet features we found adds all 15 orbits as one block.
For this project that would be wrong, because the orbits do not cost the same
radius.

A graphlet containing v spans some distance from v. The radius needed to count
an orbit is the ECCENTRICITY OF v WITHIN THAT GRAPHLET - the furthest any other
member sits from v along the graphlet's own edges. To recognise an orbit you
must see all its members and every edge among them (the subgraph is induced, so
absent edges are as meaningful as present ones), and the r-ball gives exactly
that for r = the eccentricity.

Working it through orbit by orbit gives a distribution across the ladder rather
than a lump at the deepest rung:

    hop 1 : orbits 2, 7, 11, 13, 14   (v adjacent to every other member)
    hop 2 : orbits 1, 5, 6, 8, 9, 10, 12
    hop 3 : orbit 4                   (v at the end of an induced 4-path)

Only ONE of the fifteen genuinely needs three hops. That matters for the cost
side of the depth-versus-richness comparison: adding graphlets is not a single
expensive block bolted onto the deepest radius, it is a set of features that
mostly live at radius 1 and 2.

The tagging is CONSERVATIVE, which is the safe direction. Graphlet distance is
an upper bound on distance in the host graph: two members three steps apart
within an induced 4-path might be two steps apart through some node outside the
graphlet. So an orbit may be tagged deeper than strictly necessary, never
shallower - a radius-r observer is never credited with something it could not
have computed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from itertools import combinations
from pathlib import Path

import numpy as np
import scipy.sparse as sp

from .preprocessing import Network

# --------------------------------------------------------------------------
# The orbit table
# --------------------------------------------------------------------------
# name, and the eccentricity of the orbit's node within its graphlet, which is
# the radius required to count it. Derived by hand and confirmed against ORCA
# on graphs whose orbit counts can be worked out on paper (see the diamond case
# in verify_pipeline.py).
ORBIT_SPEC: dict[int, tuple[str, int]] = {
    0:  ("edge_endpoint",        1),
    1:  ("P3_end",               2),
    2:  ("P3_centre",            1),
    3:  ("triangle",             1),
    4:  ("P4_end",               3),
    5:  ("P4_middle",            2),
    6:  ("claw_leaf",            2),
    7:  ("claw_centre",          1),
    8:  ("C4",                   2),
    9:  ("paw_tail",             2),
    # ORCA numbers the paw the opposite way round from the obvious guess: the
    # DEGREE-2 triangle nodes are orbit 10 and the DEGREE-3 hub is orbit 11.
    # Established by running ORCA on a hand-built paw, after the brute-force
    # check disagreed on exactly these two orbits and no others. The radii
    # follow: the hub touches every member, while a degree-2 triangle node is
    # two steps from the tail.
    10: ("paw_triangle",         2),
    11: ("paw_hub",              1),
    12: ("diamond_deg2",         2),
    13: ("diamond_deg3",         1),
    14: ("K4",                   1),
}

# --------------------------------------------------------------------------
# 5-node node orbits: radius per orbit, MEASURED not derived
# --------------------------------------------------------------------------
# Fifteen orbits can be reasoned through by hand. Seventy-three cannot, so the
# radii below were measured with the operational definition directly:
#
#   orbit k is available at radius r  <=>  for every node v, counting k on the
#   induced r-ball of v equals counting it on the whole graph
#
# which is exactly what "a radius-r observer could compute this" means here.
# The measurement was validated first by re-deriving the 4-node table: it
# reproduced all fifteen hand-derived tags exactly (see _calib.py). The value
# per orbit is the MAXIMUM over several graph families, since a dense graph
# whose 2-ball already covers everything will understate the radius.
#
# Distribution: 18 orbits at radius 1, 43 at radius 2, 11 at radius 3, and one
# - orbit 15, the endpoint of an induced 5-path - at radius 4. The same shape
# as the 4-node case: most of the enrichment lives near the node, and the long
# thin chains are what cost depth.
#
# CORRECTED 2026-09-11 (Claude Opus 5, Task 6 audit finding P1-01). The table
# shipped from 2026-08-31 to 2026-09-11 had orbits 56, 57, 65, 66, 68 and 70 at
# radius 1. _calib.calibrate was not taking the maximum over families: the first
# family to touch an orbit fixed it, and a family that did not contain the orbit
# still voted "1". BA and HK both measure these six at 2, and the exact
# reference - the eccentricity of the orbit's node inside its own graphlet
# (_calib.derive_node_radius) - is 2 as well: each of the six is the node of a
# dense 5-graphlet that is NOT adjacent to one other member (K5 minus an edge,
# orbit 70, is the clearest case: the two endpoints of the missing edge are two
# steps apart). A radius-1 observer cannot see that far. verify_calibration.py
# now holds this table to the derivation, and the r=1 cells that used the six
# columns were refitted (see docs/phase6_claude_worklog_20260910.md).
ORBIT5_RADIUS: dict[int, int] = {}
for _k in (0, 2, 3, 7, 11, 13, 14, 23, 33, 42, 44, 55, 58, 61,
           67, 69, 71, 72):
    ORBIT5_RADIUS[_k] = 1
for _k in (1, 5, 6, 8, 9, 10, 12, 17, 20, 21, 22, 25, 26, 28, 30, 31, 32, 34,
           37, 38, 39, 40, 41, 43, 47, 48, 49, 50, 51, 52, 53, 54, 56, 57, 59, 60,
           62, 63, 64, 65, 66, 68, 70):
    ORBIT5_RADIUS[_k] = 2
for _k in (4, 16, 18, 19, 24, 27, 29, 35, 36, 45, 46):
    ORBIT5_RADIUS[_k] = 3
ORBIT5_RADIUS[15] = 4
assert len(ORBIT5_RADIUS) == 73, "5-node radius table must cover every orbit"

# Orbit 15 needs four hops. With max_hop = 3 it can never be selected, so it is
# registered honestly at hop 4 and simply never appears in a sweep cell. Raising
# max_hop would bring it in without any further change.


# --------------------------------------------------------------------------
# Edge orbits
# --------------------------------------------------------------------------

def count_edge_orbits(net: Network, graphlet_size: int = 4,
                      binary: Path | None = None):
    """
    Orbit counts per EDGE: returns (eu, ev, orbits) with orbits of shape
    (m, 12) for graphlet_size=4 and (m, 68) for 5.

    An edge orbit is a position an EDGE can occupy in a graphlet, which is a
    different decomposition from the node orbits and not recoverable from them.
    To use them as node features they are aggregated over each node's incident
    edges - see edge_orbit_node_features.

    ORCA writes edge results in the order it read the edges, so the returned
    (eu, ev) is the alignment and must be used rather than reconstructed.
    """
    binary = binary or orca_binary()
    if binary is None:
        return None, None, None
    if graphlet_size not in (4, 5):
        raise ValueError("graphlet_size must be 4 or 5")

    coo = sp.triu(net.adj, k=1).tocoo()
    eu, ev = coo.row.astype(np.int64), coo.col.astype(np.int64)
    tmp = tempfile.mkdtemp(prefix="orca_e_")
    fin, fout = os.path.join(tmp, "g.in"), os.path.join(tmp, "g.out")
    try:
        with open(fin, "w") as fh:
            fh.write(f"{net.n} {len(eu)}" + chr(10))
            for u, v in zip(eu.tolist(), ev.tolist()):
                fh.write(f"{u} {v}" + chr(10))
        res = subprocess.run(
            [str(binary), "edge", str(graphlet_size), fin, fout],
            capture_output=True, text=True)
        _raise_if_orca_failed(res, fout, "edge")
        out = np.loadtxt(fout, dtype=np.float64)
        if out.ndim == 1:
            out = out.reshape(1, -1)
        if out.shape[0] != len(eu):
            raise RuntimeError(
                f"orca returned {out.shape[0]} edge rows for {len(eu)} edges")
        return eu, ev, out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def edge_orbit_node_features(net: Network, eu, ev, orbits,
                             stats=("mean", "max", "std")):
    """
    Turn per-edge orbit counts into per-node features by summarising over each
    node's incident edges.

    `sum` is deliberately NOT among the defaults. Summing an edge-orbit count
    over a node's incident edges counts each graphlet once per incident edge in
    it, which for several orbits is an exact multiple of a node-orbit count
    already in the table - a derived column by construction. The mean, max and
    spread describe the DISTRIBUTION across a node's edges, which nothing else
    does.
    """
    n, K = net.n, orbits.shape[1]
    # Group each node's incident-edge rows by sorting the (node, row) pairs once
    # and slicing per node. This IS still a Python loop over n nodes - what the
    # sort buys is that each iteration slices a contiguous block instead of
    # rescanning all m edges to find the ones incident to v, which is the
    # difference between O(m log m + n) and O(n * m).
    order = np.argsort(np.concatenate([eu, ev]), kind="stable")
    node_of = np.concatenate([eu, ev])[order]
    row_of = np.concatenate([np.arange(len(eu)), np.arange(len(eu))])[order]
    bounds = np.searchsorted(node_of, np.arange(n + 1))

    out = {}
    for name in stats:
        out[name] = np.zeros((n, K), dtype=np.float64)
    for v in range(n):
        rows = row_of[bounds[v]:bounds[v + 1]]
        if len(rows) == 0:
            continue
        block = orbits[rows]
        if "mean" in out:
            out["mean"][v] = block.mean(axis=0)
        if "max" in out:
            out["max"][v] = block.max(axis=0)
        if "std" in out:
            out["std"][v] = block.std(axis=0)
        if "min" in out:
            out["min"][v] = block.min(axis=0)
        if "sum" in out:
            out["sum"][v] = block.sum(axis=0)
    return out


# Orbits that are EXACTLY features we already have, so adding them would put
# duplicate columns in the table and inflate the subgraph tier with nothing:
#   orbit 0 == degree
#   orbit 3 == triangle_count
# The feature audit would flag them after the fact; better not to add them.
REDUNDANT_ORBITS = (0, 3)

VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor"


# --------------------------------------------------------------------------
# Running ORCA
# --------------------------------------------------------------------------

def orca_binary() -> Path | None:
    """
    Locate the ORCA executable, or return None.

    Returning None rather than raising is deliberate: graphlet features are an
    optional enrichment, and a machine without the binary should still be able
    to run the whole pipeline. `extract_features` simply omits the columns.
    """
    for cand in (VENDOR_DIR / "orca.exe", VENDOR_DIR / "orca"):
        if cand.exists():
            return cand
    found = shutil.which("orca")
    return Path(found) if found else None


def _raise_if_orca_failed(res: subprocess.CompletedProcess, fout: str,
                          kind: str) -> None:
    """
    Decide whether an ORCA run failed, from everything it left behind.

    Task 6 audit finding P1-07 (Claude Opus 5, 2026-09-11). Upstream ORCA
    returned exit code 0 after every init() failure, and init() creates the
    output file BEFORE validating the graph - so the original test here,
    `returncode != 0 or not exists(fout)`, was False on a self-loop, a
    duplicate edge, an out-of-range id or an unreadable input. Only the
    row-count backstop downstream caught those, with the wrong message.

    vendor/orca.cpp now returns 1 on that branch (see vendor/BUILD_20260911.md),
    but the boundary should not depend on the binary being the patched one: a
    zero-byte output file or anything on stderr is also treated as failure.
    ORCA writes its progress to stdout and reserves stderr for errors, so a
    non-empty stderr from a successful run would itself be new information.
    """
    err = res.stderr.strip()
    if res.returncode != 0 or not os.path.exists(fout) or err:
        raise RuntimeError(
            f"orca {kind} failed (rc={res.returncode}): {err[:300] or '<no stderr>'}")
    if os.path.getsize(fout) == 0:
        raise RuntimeError(
            f"orca {kind} produced an empty output file with rc=0 and no "
            f"stderr - an init failure on an unpatched binary, or an empty graph")


def count_node_orbits(net: Network, graphlet_size: int = 4,
                      binary: Path | None = None) -> np.ndarray | None:
    """
    Orbit counts for every node: an (n, 15) array for graphlet_size=4.

    ORCA's input is 'n m' followed by m lines of '0-indexed u v'. Our Network
    is already reindexed to 0..n-1 with self-loops and multi-edges removed by
    the preprocessing protocol, which is exactly what ORCA requires - so no
    special-casing is needed, and nothing about the graph is altered on the way
    in or out.
    """
    binary = binary or orca_binary()
    if binary is None:
        return None
    if graphlet_size not in (4, 5):
        raise ValueError("graphlet_size must be 4 or 5")

    coo = sp.triu(net.adj, k=1).tocoo()
    tmp = tempfile.mkdtemp(prefix="orca_")
    fin, fout = os.path.join(tmp, "g.in"), os.path.join(tmp, "g.out")
    try:
        with open(fin, "w") as fh:
            fh.write(f"{net.n} {len(coo.row)}\n")
            for u, v in zip(coo.row.tolist(), coo.col.tolist()):
                fh.write(f"{u} {v}\n")

        res = subprocess.run(
            [str(binary), "node", str(graphlet_size), fin, fout],
            capture_output=True, text=True)
        _raise_if_orca_failed(res, fout, "node")

        out = np.loadtxt(fout, dtype=np.float64)
        if out.ndim == 1:                      # a single-node graph
            out = out.reshape(1, -1)
        if out.shape[0] != net.n:
            raise RuntimeError(
                f"orca returned {out.shape[0]} rows for {net.n} nodes")
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# The independent reference
# --------------------------------------------------------------------------

def brute_force_node_orbits(net: Network) -> np.ndarray:
    """
    Orbit counts by direct enumeration, for graphlets up to 4 nodes.

    Enumerates every connected induced subgraph on 2, 3 and 4 nodes and
    classifies it from first principles - by edge count and degree sequence,
    which together identify all six connected 4-node graphlets uniquely:

        3 edges, degrees [1,1,1,3]  claw      leaf -> 6,  centre -> 7
        3 edges, degrees [1,2,2,1]  path P4   end  -> 4,  middle -> 5
        4 edges, degrees [2,2,2,2]  cycle C4  all  -> 8
        4 edges, degrees [1,2,2,3]  paw       tail -> 9, triangle -> 10, hub -> 11
        5 edges, degrees [2,2,3,3]  diamond   deg2 -> 12, deg3 -> 13
        6 edges, degrees [3,3,3,3]  K4        all  -> 14

    O(n^4) and therefore only for small graphs - it exists to check ORCA, not
    to replace it. That is the same arrangement used for Brandes betweenness
    and the Ihara-Bass eigenvalue elsewhere in this project: write the
    obvious-but-slow version, verify the fast one against it, then use the fast
    one and keep the reference so the check can be repeated.
    """
    n = net.n
    orb = np.zeros((n, 15), dtype=np.float64)
    A = np.asarray(net.adj.todense(), dtype=bool)

    # orbit 0: the node's edges.
    orb[:, 0] = A.sum(axis=1)

    # 3-node connected induced subgraphs.
    for trio in combinations(range(n), 3):
        a, b, c = trio
        e = int(A[a, b]) + int(A[a, c]) + int(A[b, c])
        if e < 2:
            continue                                    # not connected
        if e == 3:
            for v in trio:
                orb[v, 3] += 1                          # triangle
        else:
            deg = {v: sum(int(A[v, w]) for w in trio if w != v) for v in trio}
            for v in trio:
                orb[v, 2 if deg[v] == 2 else 1] += 1    # P3 centre / end

    # 4-node connected induced subgraphs.
    for quad in combinations(range(n), 4):
        pairs = list(combinations(quad, 2))
        e = sum(int(A[u, w]) for u, w in pairs)
        if e < 3:
            continue
        deg = {v: sum(int(A[v, w]) for w in quad if w != v) for v in quad}
        ds = sorted(deg.values())
        # Connectivity: with >= 3 edges on 4 nodes the only disconnected shape
        # is a triangle plus an isolated node, i.e. some node of degree 0.
        if ds[0] == 0:
            continue

        if e == 3 and ds == [1, 1, 1, 3]:               # claw
            for v in quad:
                orb[v, 7 if deg[v] == 3 else 6] += 1
        elif e == 3 and ds == [1, 1, 2, 2]:             # path P4
            for v in quad:
                orb[v, 5 if deg[v] == 2 else 4] += 1
        elif e == 4 and ds == [2, 2, 2, 2]:             # cycle C4
            for v in quad:
                orb[v, 8] += 1
        elif e == 4 and ds == [1, 2, 2, 3]:             # paw
            # deg 1 = the tail, deg 2 = the two triangle nodes it does not
            # touch, deg 3 = the hub joining them. See the note on ORBIT_SPEC.
            for v in quad:
                orb[v, {1: 9, 2: 10, 3: 11}[deg[v]]] += 1
        elif e == 5:                                    # diamond
            for v in quad:
                orb[v, 13 if deg[v] == 3 else 12] += 1
        elif e == 6:                                    # K4
            for v in quad:
                orb[v, 14] += 1
    return orb


# --------------------------------------------------------------------------
# The independent reference, 5 nodes (Task 6 finding P1-08)
# --------------------------------------------------------------------------
# Added 2026-09-11 by Claude Opus 5. Until now the 5-node orbit counts had no
# in-project reference at all: brute_force_node_orbits stops at 4 nodes, so
# the 58 five-node columns were inherited from ORCA (Hocevar & Demsar) on
# trust. This closes most of that gap WITHOUT hand-transcribing the Przulj
# orbit figure, which would just be a second copy of the same convention:
#
#   * enumerate every connected induced 5-node subgraph containing each node
#     and classify it from first principles - isomorphism class by canonical
#     form over all 120 relabellings, the node's position by its automorphism
#     orbit within that class. That yields, per node, a count for each of the
#     58 (class, orbit) pairs under a numbering of OUR OWN;
#   * then ask whether ORCA's 58 five-node columns are the same 58 vectors up
#     to ONE permutation shared by every node of every fixture.
#
# What that establishes: ORCA's 5-node equations produce exactly the induced
# orbit counts, column by column, on the fixtures - a wrong equation would
# make some column match no reference vector. What it does NOT establish on
# its own: which ORCA index carries which Przulj label. Three labels whose
# structure is unambiguous (K5 -> 72, K5 minus an edge -> 70/71, the 5-path
# -> 15/16/17) are pinned separately in verify_pipeline as a check on that.
# The radius tags in ORBIT5_RADIUS were MEASURED per column (_calib.py), so
# the feature table never depended on the labels being right - only on the
# counts, which is what is checked here.

_FIVE_PAIRS = tuple(combinations(range(5), 2))          # 10 bit positions


def _five_node_tables() -> tuple[dict[int, int], dict[int, tuple[int, ...]]]:
    """
    For every 10-bit adjacency code of a labelled 5-node graph: its canonical
    code (min over the 120 relabellings) and, per labelled position, the
    canonical id of its automorphism orbit. Only connected codes are kept.
    """
    from itertools import permutations
    perms = list(permutations(range(5)))
    bit_of = {pair: i for i, pair in enumerate(_FIVE_PAIRS)}

    def relabel(code: int, p) -> int:
        out = 0
        for i, (a, b) in enumerate(_FIVE_PAIRS):
            if code >> i & 1:
                x, y = p[a], p[b]
                out |= 1 << bit_of[(x, y) if x < y else (y, x)]
        return out

    def connected(code: int) -> bool:
        adj = [[False] * 5 for _ in range(5)]
        for i, (a, b) in enumerate(_FIVE_PAIRS):
            if code >> i & 1:
                adj[a][b] = adj[b][a] = True
        seen, stack = {0}, [0]
        while stack:
            v = stack.pop()
            for w in range(5):
                if adj[v][w] and w not in seen:
                    seen.add(w)
                    stack.append(w)
        return len(seen) == 5

    canon: dict[int, int] = {}
    orbit_of: dict[int, tuple[int, ...]] = {}
    for code in range(1 << 10):
        if not connected(code):
            continue
        images = [(relabel(code, p), p) for p in perms]
        cmin = min(c for c, _ in images)
        canon[code] = cmin
        # Position i's automorphism orbit: the set of canonical positions it
        # can be sent to by a relabelling achieving the canonical code. Two
        # positions in the same orbit share that set, so its minimum is a
        # stable id for the orbit.
        achieving = [p for c, p in images if c == cmin]
        orbit_of[code] = tuple(min(p[i] for p in achieving) for i in range(5))
    return canon, orbit_of


def brute_force_five_node_orbits(net: Network) -> tuple[list[tuple[int, int]], np.ndarray]:
    """
    Per-node counts of every (5-node graphlet class, automorphism orbit) pair
    by direct enumeration, under this module's own canonical numbering.

    Returns (keys, counts) with counts of shape (n, len(keys)); keys are
    (canonical_code, orbit_id) and there are 58 of them across all connected
    5-node graphs, though a given fixture may not realise every one. O(n^5):
    a 30-node fixture is ~140k subsets and a few seconds. Reference only.
    """
    canon, orbit_of = _five_node_tables()
    A = np.asarray(net.adj.todense(), dtype=bool)
    keys = sorted({(c, o) for code, c in canon.items() for o in set(orbit_of[code])})
    col = {k: j for j, k in enumerate(keys)}
    counts = np.zeros((net.n, len(keys)), dtype=np.float64)
    for quint in combinations(range(net.n), 5):
        code = 0
        for i, (a, b) in enumerate(_FIVE_PAIRS):
            if A[quint[a], quint[b]]:
                code |= 1 << i
        c = canon.get(code)
        if c is None:                                   # disconnected
            continue
        orbs = orbit_of[code]
        for pos, v in enumerate(quint):
            counts[v, col[(c, orbs[pos])]] += 1
    return keys, counts


def match_orbit_columns(orca_cols: np.ndarray, ref_cols: np.ndarray
                        ) -> tuple[dict[int, int], list[tuple[list[int], list[int]]], list[int]]:
    """
    Pair ORCA columns with reference columns that are IDENTICAL vectors.

    Returns (matched: orca_col -> ref_col for uniquely matched columns,
    ambiguous: groups of [orca cols], [ref cols] that share one vector and
    cannot be told apart on this data, unmatched: orca cols whose vector
    appears in no reference column). A correct ORCA gives unmatched == [] and
    every group's two lists the same length; a permuted or wrong column shows
    up in `unmatched`.
    """
    by_vec_ref: dict[tuple, list[int]] = {}
    for j in range(ref_cols.shape[1]):
        by_vec_ref.setdefault(tuple(ref_cols[:, j].tolist()), []).append(j)
    by_vec_orca: dict[tuple, list[int]] = {}
    for j in range(orca_cols.shape[1]):
        by_vec_orca.setdefault(tuple(orca_cols[:, j].tolist()), []).append(j)
    matched, ambiguous, unmatched = {}, [], []
    for vec, ocols in by_vec_orca.items():
        rcols = by_vec_ref.get(vec)
        if rcols is None:
            unmatched.extend(ocols)
        elif len(ocols) == 1 and len(rcols) == 1:
            matched[ocols[0]] = rcols[0]
        else:
            ambiguous.append((ocols, rcols))
    return matched, ambiguous, sorted(unmatched)



# --------------------------------------------------------------------------
# Edge orbits: radius per orbit, measured the same way
# --------------------------------------------------------------------------
# The question for an edge orbit used as a NODE feature is: how far must node u
# see, to know the orbit of every edge incident to it? That is the eccentricity
# of u within the graphlet, and it is measured with the same ball-versus-full
# comparison as the node orbits (see _calib_edge.py).
#
# Note edge orbit 0 sits at radius 2, not 1: it is the edge of a 3-path, so
# from one endpoint the far node is two steps away. Nothing about being an edge
# feature makes it a radius-1 feature.
EDGE_ORBIT4_RADIUS: dict[int, int] = {
    1: 1, 10: 1, 11: 1,
    0: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2, 9: 2,
    2: 3,
}
assert len(EDGE_ORBIT4_RADIUS) == 12

# 5-node EDGE orbits, measured the same way. 68 orbits: 7 at radius 1, 48 at
# radius 2, 12 at radius 3, and one - orbit 12 - at radius 4.
#
# CORRECTED 2026-09-11 (Claude Opus 5, finding P1-01): orbits 49, 50, 51, 59,
# 60, 61, 63, 64 and 65 moved from radius 1 to 2 for the same aggregation defect
# as ORBIT5_RADIUS above (_calib_edge.derive_edge_radius gives 2 for all nine).
# No production sweep uses 5-node edge orbits, so no fitted number depends on
# this retag; the historical analyse_edge5.py comparison that did use them is
# labelled as pre-correction in results/RESULTS_edge5.txt.
#
# These are available but OFF BY DEFAULT. 68 orbits x 3 summary statistics is
# 204 columns, which against everything measured so far about how little most
# orbit columns contribute is disproportionate, and it roughly doubles the
# feature table. Turn them on with edge_graphlet_size=5 and expect sweeps to
# take substantially longer.
EDGE_ORBIT5_RADIUS: dict[int, int] = {}
for _k in (1, 10, 11, 48, 62, 66, 67):
    EDGE_ORBIT5_RADIUS[_k] = 1
for _k in (0, 3, 4, 5, 6, 7, 8, 9, 16, 17, 19, 20, 22, 25, 26, 27, 28, 31, 32,
           33, 34, 35, 36, 37, 40, 41, 42, 43, 44, 45, 46, 47, 49, 50, 51, 52,
           53, 54, 55, 56, 57, 58, 59, 60, 61, 63, 64, 65):
    EDGE_ORBIT5_RADIUS[_k] = 2
for _k in (2, 13, 14, 15, 18, 21, 23, 24, 29, 30, 38, 39):
    EDGE_ORBIT5_RADIUS[_k] = 3
EDGE_ORBIT5_RADIUS[12] = 4
assert len(EDGE_ORBIT5_RADIUS) == 68

EDGE_ORBIT_RADIUS = {4: EDGE_ORBIT4_RADIUS, 5: EDGE_ORBIT5_RADIUS}

# --------------------------------------------------------------------------
# Feature naming
# --------------------------------------------------------------------------

def orbit_columns(orbits: np.ndarray) -> list[tuple[str, np.ndarray, int]]:
    """
    (name, values, hop) for every node orbit worth adding.

    Handles both graphlet sizes: the first 15 orbits are the same in either
    case, so the 4-node names are reused where they exist and the rest are
    numbered.

    Skips the two that duplicate existing columns, and skips any orbit that is
    identically zero on this graph - a constant column inflates the feature
    count and carries nothing.
    """
    out = []
    n_orb = orbits.shape[1]
    radii = ORBIT5_RADIUS if n_orb > 15 else {k: h for k, (_, h) in ORBIT_SPEC.items()}
    for idx in range(n_orb):
        if idx in REDUNDANT_ORBITS:
            continue
        v = orbits[:, idx]
        if not np.any(v):
            continue
        name = ORBIT_SPEC[idx][0] if idx in ORBIT_SPEC else "g5"
        out.append((f"orbit_{idx:02d}_{name}", v, radii[idx]))
    return out


def edge_orbit_columns(per_stat: dict[str, np.ndarray]
                       ) -> list[tuple[str, np.ndarray, int]]:
    """
    (name, values, hop) for the aggregated edge-orbit features.

    Only 4-node edge orbits carry a measured radius table, so anything wider is
    refused rather than guessed at - a wrong radius tag would silently credit a
    radius-r observer with information it could not have had, which is the one
    error this project cannot tolerate quietly.
    """
    out = []
    any_arr = next(iter(per_stat.values()))
    K = any_arr.shape[1]
    radii = next((t for t in EDGE_ORBIT_RADIUS.values() if len(t) == K), None)
    if radii is None:
        raise ValueError(
            f"no measured radius table for {K} edge orbits; run _calib_edge.py")
    for idx in range(K):
        for stat, arr in per_stat.items():
            v = arr[:, idx]
            if not np.any(v):
                continue
            out.append((f"eorbit_{idx:02d}_{stat}", v, radii[idx]))
    return out

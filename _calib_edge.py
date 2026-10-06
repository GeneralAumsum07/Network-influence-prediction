"""Measure the radius each EDGE orbit needs, from a node's point of view.

CORRECTED 2026-09-11 (Claude Opus 5, Task 6 audit finding P1-01). The
aggregation had the same two defects as _calib.calibrate - first family wins,
and absent orbits vote "radius 1" - so nine 5-node edge orbits (49, 50, 51, 59,
60, 61, 63, 64, 65) were tagged 1 when the eccentricity says 2. 5-node edge
orbits are off by default and appear in no production sweep, so that retag
changes no fitted number; the 4-node edge table was unaffected. Per-family
measurement, seen-only votes and an explicit maximum are now shared with
_calib.py, and `derive_edge_radius` gives the exact reference.
"""
import sys
import numpy as np
sys.path.insert(0, ".")
from influence import generators as gen
from influence.graphlets import count_edge_orbits
from influence.preprocessing import build_network
from _calib import ball_subgraph


def node_edge_orbits(net, gs):
    """(n, K): each node's incident-edge orbit vectors, summed over its edges."""
    eu, ev, orb = count_edge_orbits(net, gs)
    out = np.zeros((net.n, orb.shape[1]))
    np.add.at(out, eu, orb)
    np.add.at(out, ev, orb)
    return out


def calibrate_edge_one(net, gs, max_r=4):
    """Per-orbit radius on ONE graph; see _calib.calibrate_one for the contract."""
    K = 12 if gs == 4 else 68
    full = node_edge_orbits(net, gs)
    seen = (full != 0).any(axis=0)
    radius = np.zeros(K, dtype=int)
    for r in range(1, max_r + 1):
        got = np.zeros_like(full)
        ok = np.ones(net.n, dtype=bool)
        for v in range(net.n):
            sub, iv = ball_subgraph(net, v, r)
            if sub is None:
                ok[v] = False
                continue
            got[v] = node_edge_orbits(sub, gs)[iv]
        for k in range(K):
            if seen[k] and radius[k] == 0 and np.array_equal(got[ok, k], full[ok, k]):
                radius[k] = r
    radius[(radius == 0) & seen] = max_r + 1
    return radius, seen


def calibrate_edge(graphs, gs, max_r=4):
    """Maximum over families of the per-family radius; only families that
    contain the orbit vote. Order-invariant by construction."""
    K = 12 if gs == 4 else 68
    radius = np.zeros(K, dtype=int)
    seen_any = np.zeros(K, dtype=bool)
    for _, net in graphs:
        r_one, seen = calibrate_edge_one(net, gs, max_r)
        radius = np.where(seen, np.maximum(radius, r_one), radius)
        seen_any |= seen
    return radius, seen_any


def derive_edge_radius(gs):
    """
    Exact radius of each edge orbit used as a NODE feature.

    The node feature sums the orbit vectors of a node's incident edges, so node
    u must see the whole graphlet of every incident edge in orbit k, whichever
    endpoint u is. That is the larger of the two endpoints' eccentricities in
    the graphlet, maximised over the edges of the orbit. Same atlas rule as
    _calib.derive_node_radius: the orbit belongs to the smallest connected graph
    in which every edge carrying it has count exactly 1.
    """
    import networkx as nx
    from networkx.generators.atlas import graph_atlas_g
    K = 12 if gs == 4 else 68
    best = {}
    for g in graph_atlas_g():
        m = g.number_of_nodes()
        if m < 2 or m > gs or not nx.is_connected(g):
            continue
        net = build_network(list(g.edges()), name="atlas")
        eu, ev, orb = count_edge_orbits(net, gs)
        ecc = nx.eccentricity(g)
        for k in range(K):
            col = orb[:, k]
            idx = [i for i in range(len(col)) if col[i] > 0]
            if not idx or any(col[i] != 1 for i in idx):
                continue
            r = max(max(ecc[int(net.original_ids[eu[i]])], ecc[int(net.original_ids[ev[i]])])
                    for i in idx)
            if k not in best or best[k][1] > m:
                best[k] = (r, m)
    return {k: r for k, (r, _) in sorted(best.items())}


if __name__ == "__main__":
    gs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    graphs = [("ER", gen.erdos_renyi(60, 6, seed=1)),
              ("BA", gen.barabasi_albert(60, 3, seed=2)),
              ("HK", gen.holme_kim(50, 3, 0.6, seed=3)),
              ("dense", gen.erdos_renyi(28, 14, seed=7))]
    rad, seen = calibrate_edge(graphs, gs, max_r=4)
    byr = {}
    for k in range(len(rad)):
        byr.setdefault(int(rad[k]) if seen[k] else "unseen", []).append(k)
    print(f"edge orbits, graphlet_size={gs}:")
    for key in sorted(byr, key=lambda x: (isinstance(x, str), x)):
        print(f"  radius {key}: {len(byr[key])} -> {byr[key]}")
    derived = derive_edge_radius(gs)
    bad = [(k, int(rad[k]), derived[k]) for k in range(len(rad)) if seen[k] and rad[k] > derived[k]]
    print("measured above the eccentricity derivation (must be empty):", bad)

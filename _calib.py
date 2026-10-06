"""
Measure, rather than derive, the radius each graphlet orbit needs.

THE OPERATIONAL DEFINITION
--------------------------
A radius-r observer sees exactly the induced subgraph on the r-ball. So orbit k
is computable at radius r if and only if, for every node v, counting orbit k on
the induced r-ball of v gives the same answer as counting it on the whole
graph. That is directly testable, and it is what "the feature is available at
radius r" means in this project.

Deriving it by hand from graphlet eccentricity works for 15 orbits and is not
practical for 73. So: measure it, and validate the measurement against the
hand-derived 4-node table. If the automatic method reproduces all fifteen, it
can be trusted for the seventy-three.

CORRECTED 2026-09-11 (Claude Opus 5, Task 6 audit finding P1-01)
------------------------------------------------------------------
The original `calibrate` had two defects that together made the table NOT the
maximum over families that influence/graphlets.py claimed it was:

  * it recorded `radius[k] = r` only while `radius[k] == 0`, so the first
    family to touch orbit k fixed it for every later family; and
  * an orbit ABSENT from a family (all-zero column) "agrees" trivially at r=1,
    and that agreement was recorded as a radius-1 vote.

Six 5-node orbits (56, 57, 65, 66, 68, 70) were tagged 1 when both BA and HK
measure them at 2. `calibrate` now measures each family on its own, lets a
family vote only on orbits it contains, and takes the maximum. `derive_node_radius`
adds the exact reference the measurement can only understate: the eccentricity
of the orbit's node inside its own graphlet, computed from the networkx atlas.
verify_calibration.py holds the tables to both.
"""
import sys
import numpy as np
import scipy.sparse as sp

sys.path.insert(0, ".")
from influence import generators as gen
from influence.graphlets import count_node_orbits, ORBIT_SPEC
from influence.preprocessing import build_network


def ball_subgraph(net, v, r):
    """Induced subgraph on the r-ball of v; returns (Network, index of v)."""
    seen = {v}
    frontier = {v}
    for _ in range(r):
        nxt = set()
        for u in frontier:
            nxt.update(net.nbrs[u].tolist())
        nxt -= seen
        seen |= nxt
        frontier = nxt
    nodes = sorted(seen)
    pos = {u: i for i, u in enumerate(nodes)}
    sub = net.adj[nodes][:, nodes].tocoo()
    edges = [(pos_u, pos_w) for pos_u, pos_w in zip(sub.row.tolist(), sub.col.tolist())
             if pos_u < pos_w]
    if not edges:
        return None, None
    # build_network reindexes by sorted unique label, and our labels are already
    # 0..k-1 contiguous ONLY if every node appears in an edge. Isolated nodes in
    # the ball cannot participate in any graphlet, so dropping them is safe -
    # but we must then re-locate v.
    net_sub = build_network(edges, name="ball")
    orig = net_sub.original_ids.tolist()
    if pos[v] not in orig:
        return None, None
    return net_sub, orig.index(pos[v])


def calibrate_one(net, graphlet_size, max_r=4):
    """
    Radius per orbit on ONE graph: the smallest r at which every node's r-ball
    reproduces its whole-graph count. max_r + 1 when no r <= max_r does.

    Returns (radius, seen). `seen[k]` is False when orbit k never occurs on this
    graph; its radius entry is then 0 and MUST be ignored by the caller - an
    all-zero column agrees with itself at every r and carries no information.
    """
    n_orb = 15 if graphlet_size == 4 else 73
    full = count_node_orbits(net, graphlet_size)
    seen = (full != 0).any(axis=0)
    radius = np.zeros(n_orb, dtype=int)
    for r in range(1, max_r + 1):
        ballv = np.zeros_like(full)
        ok_node = np.ones(net.n, dtype=bool)
        for v in range(net.n):
            sub, iv = ball_subgraph(net, v, r)
            if sub is None:
                ok_node[v] = False
                continue
            o = count_node_orbits(sub, graphlet_size)
            ballv[v] = o[iv]
        for k in range(n_orb):
            if seen[k] and radius[k] == 0 and np.array_equal(ballv[ok_node, k], full[ok_node, k]):
                radius[k] = r
    radius[(radius == 0) & seen] = max_r + 1
    return radius, seen


def calibrate(graphs, graphlet_size, max_r=4):
    """
    MAXIMUM over families of the per-family radius, as graphlets.py documents.

    A dense family whose 2-ball already covers everything understates the
    radius; a sparse one may not contain the orbit at all. Only families that
    contain the orbit vote, and the tag is the largest vote, so adding a family
    can raise a radius but never lower it, and the order of `graphs` cannot
    change the answer.
    """
    n_orb = 15 if graphlet_size == 4 else 73
    radius = np.zeros(n_orb, dtype=int)
    seen_any = np.zeros(n_orb, dtype=bool)
    for _, net in graphs:
        r_one, seen = calibrate_one(net, graphlet_size, max_r)
        radius = np.where(seen, np.maximum(radius, r_one), radius)
        seen_any |= seen
    return radius, seen_any


def derive_node_radius(graphlet_size):
    """
    The exact 'never shallower' radius of every orbit: the eccentricity of the
    orbit's node inside its own graphlet.

    Every induced copy of the graphlet containing v lies inside v's r-ball once
    r reaches v's eccentricity in the graphlet (whole-graph distances are never
    longer than within-graphlet ones), and a copy with no shortcut needs
    exactly that. Computed from the networkx graph atlas so nothing is
    transcribed by hand: each orbit belongs to the SMALLEST connected graph in
    which it appears with count exactly 1 at every member node - that graph is
    the graphlet itself - and its members are one automorphism class, so they
    share one eccentricity.
    """
    import networkx as nx
    from networkx.generators.atlas import graph_atlas_g
    n_orb = 15 if graphlet_size == 4 else 73
    best = {}                      # orbit -> (eccentricity, graph order)
    for g in graph_atlas_g():
        m = g.number_of_nodes()
        if m < 2 or m > graphlet_size or not nx.is_connected(g):
            continue
        net = build_network(list(g.edges()), name="atlas")
        orb = count_node_orbits(net, graphlet_size)
        ecc = nx.eccentricity(g)
        for k in range(n_orb):
            col = orb[:, k]
            members = [v for v in range(m) if col[v] > 0]
            if not members or any(col[v] != 1 for v in members):
                continue
            eccs = {ecc[int(net.original_ids[v])] for v in members}
            if len(eccs) != 1:
                continue
            if k not in best or best[k][1] > m:
                best[k] = (eccs.pop(), m)
    return {k: e for k, (e, _) in sorted(best.items())}


if __name__ == "__main__":
    gs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    graphs = [("ER", gen.erdos_renyi(60, 6, seed=1)),
              ("BA", gen.barabasi_albert(60, 3, seed=2)),
              ("HK", gen.holme_kim(50, 3, 0.6, seed=3))]
    rad, seen = calibrate(graphs, gs, max_r=4)

    print(f"graphlet_size={gs}: measured radius per orbit")
    byr = {}
    for k in range(len(rad)):
        if not seen[k]:
            byr.setdefault("never seen", []).append(k)
        else:
            byr.setdefault(int(rad[k]), []).append(k)
    for key in sorted(byr, key=lambda x: (isinstance(x, str), x)):
        print(f"  radius {key}: {len(byr[key])} orbits -> {byr[key]}")

    if gs == 4:
        print("\nvalidation against the hand-derived table:")
        bad = [k for k in range(15)
               if seen[k] and int(rad[k]) != ORBIT_SPEC[k][1]]
        for k in range(15):
            mark = "ok " if (not seen[k] or int(rad[k]) == ORBIT_SPEC[k][1]) else "MISMATCH"
            print(f"  orbit {k:2d} {ORBIT_SPEC[k][0]:16s} hand={ORBIT_SPEC[k][1]} "
                  f"measured={int(rad[k]) if seen[k] else '-'}  {mark}")
        print("\nMETHOD VALIDATED" if not bad else f"\nMISMATCHES: {bad}")

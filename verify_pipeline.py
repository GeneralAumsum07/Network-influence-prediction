"""
verify_pipeline.py
==================
Regression checks for the core pipeline.

`verify_generators.py` covers the synthetic corpus and the structural
measurements. This file covers the other half: feature extraction, the cost
model, the dynamics helpers and the leakage guard - specifically the parts that
were changed in the August 2026 correctness pass, so that a future edit which
quietly breaks one of them fails loudly here instead of silently in a result
table.

Same standard as everywhere else in this project: nothing is asserted, it is
checked against an independent reference or against a property that must hold.

Eight checks:
  1. The merged shell+CI traversal reproduces the reference implementations
     BIT FOR BIT.
  2. Skipping the final BFS expansion changes nothing.
  3. Trivalency probabilities agree between the percolation and direct paths.
  4. ignition_probability uses the network size, not the seed-sample size.
  5. Every registered feature has a cost group, and every cost group has a
     timing key.
  6. Hop tags are consistent: feature counts grow with radius, and the
     neighbour-structure aggregates sit at hop 2.
  7. The leakage guard catches forbidden names and allows the exceptions.
  8. The column ORDER behind every stored sweep cell still matches what the
     registry yields today - a retag that merely moves a registry row changes
     which forest gets built, and nothing else here would notice.

Run:  python verify_pipeline.py [edgelist]
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
import scipy.sparse as sp

from influence.preprocessing import load_edgelist
from influence import dynamics as dyn
from influence.features import (bfs_shells, collective_influence, ego_betweenness,
                                _ego_betweenness_sets,
                                shell_and_ci_pass, extract_features,
                                select_features)
from influence.experiment import feature_cost, TIER_LADDER
from influence import structure as st
from influence.targets import assert_no_leakage, ALLOWED_EXCEPTIONS

MAX_HOP = 3
FAIL: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label:52s} {detail}")
    if not ok:
        FAIL.append(label)


def check_c4() -> None:
    """N12: independent pair arithmetic catches filtering and tie-regime errors."""
    print("N12. C4 TWO-NUMBER REPORTER (CODE CORRECTNESS ONLY)")
    try:
        from c4_two_numbers import report
    except ImportError:
        check("C4 reporting implementation exists", False)
        return
    def run(y, s, decision=None):
        if decision is None:
            decision = np.asarray(s) == 0
        return report(y, s, predicted_zero=decision, decision_provenance="synthetic fixed rule")

    # Three positive pairs: two concordances and one discordance => tau=1/3.
    # Deliberately declare a positive scored zero: it MUST stay in the ranking.
    a = run([0, 0, 1, 2, 3], [0, 1, 0, 3, 2])
    check("C4 accuracy and reference-only positive filtering",
          a['zero_accuracy'] == .6 and np.isclose(a['tau_positive'], 1/3))
    check("C4 zero-labelled confusion counts and rates",
          [a[k] for k in ['true_zero', 'missed_zero', 'false_zero', 'true_positive']] == [1, 1, 1, 2]
          and a['missed_zero_rate'] == .5 and np.isclose(a['false_zero_rate'], 1/3))
    tied = run([0, 0, 1, 2, 3], [0, 0, 1, 3, 2])
    untied = run([0, 0, 1, 2, 3], [-2, -1, 1, 3, 2])
    # Six cross concordances + one net positive concordance, denominator 9 or sqrt(90).
    check("C4 tied and untied regimes use the two N11 mixtures",
          tied['mixture_regime'] == 'zero_block_tied'
          and untied['mixture_regime'] == 'untied'
          and np.isclose(tied['tau_all'], 7/9)
          and np.isclose(untied['tau_all'], 7/np.sqrt(90))
          and np.isclose(tied['mixture_prediction'], 7/9)
          and np.isclose(untied['mixture_prediction'], 7/np.sqrt(90)))
    check("C4 tie counts include boundary and positive ties",
          a['prediction_ties_cross'] == 1 and tied['prediction_ties_zero'] == 1
          and tied['distinct_predictions_zero'] == 1
          and a['mixture_regime'] == 'general_pair_accounting')
    for y, s, reason in [([], [], 'fewer_than_two_positives'),
                         ([0, 0], [0, 1], 'fewer_than_two_positives'),
                         ([0, 1], [0, 1], 'fewer_than_two_positives'),
                         ([1, 1], [1, 2], 'constant_positive_reference'),
                         ([1, 2], [1, 1], 'constant_positive_prediction')]:
        b = run(y, s)
        check('C4 undefined tau: ' + str(y) + ' / ' + reason,
              np.isnan(b['tau_positive']) and b['tau_positive_na_reason'] == reason)
    empty, nozero, allzero = run([], []), run([1, 2], [1, 2]), run([0, 0], [0, 0])
    check("C4 empty/absent-class rates remain NA",
          np.isnan(empty['zero_accuracy']) and np.isnan(nozero['missed_zero_rate'])
          and np.isnan(allzero['false_zero_rate']) and np.isnan(allzero['tau_all']))
    missing = report([0, 1], [0, 1], predicted_zero=None, decision_provenance='not supplied')
    check("C4 absent decision never inferred from scores",
          np.isnan(missing['zero_accuracy']) and missing['zero_accuracy_na_reason'] == 'no_declared_zero_decision')
    # Reference-positive ties invalidate both simplified mixtures even with a tied zero block.
    b = run([0, 0, 1, 1, 2], [0, 0, 1, 2, 3])
    check("C4 positive reference ties require actual pair accounting",
          b['reference_ties_positive'] == 1 and b['mixture_regime'] == 'general_pair_accounting')

    # REGRESSION GUARD, added 2026-09-07 after a real failure. tau-b's denominator is
    # sqrt((n0 - n1)(n0 - n2)), and n0 = n(n-1)/2 grows quadratically: at n = 200,000 the
    # PRODUCT of the two factors is ~4e20, past int64's 9.22e18. An earlier draft of
    # `report` handed that product to NumPy, which either overflows or silently promotes
    # to dtype=object and then fails in sqrt. The counts must stay exact - they are pair
    # counts, and rounding them defeats the point of computing them - so `report` keeps
    # them as Python ints and converts to float only at the final square root. A small
    # case cannot catch this: it needs n large enough to cross the boundary, which is why
    # this check is here and not in the fixture set above.
    #
    # This is the UNTIED half of the overflow guard - strictly increasing scores, so n2 = 0
    # and the denominator is the geometric sqrt((T - Z) * T). The check immediately below
    # covers the opposite extreme, two large equal blocks where almost every pair is tied.
    # Both are kept: the two regimes take different branches through the pair arithmetic,
    # and an overflow reintroduced on one would not necessarily show up on the other.
    #
    # The expected value is computed here from the closed form, independently of `report`:
    # with continuous scores there are no prediction ties, so the denominator is
    # sqrt((T - Z) * T) with T = n(n-1)/2 the total pairs and Z = n_z(n_z-1)/2 the pairs
    # tied in the reference. Nothing below calls into c4_two_numbers to build it.
    big_n, big_z = 200_000, 160_000
    big_y = np.zeros(big_n)
    big_y[big_z:] = np.arange(1, big_n - big_z + 1, dtype=float)
    big_s = np.arange(big_n, dtype=float)          # strictly increasing: no ties at all
    big = report(big_y, big_s, predicted_zero=(big_y == 0),
                 decision_provenance="synthetic overflow regression")
    T = big_n * (big_n - 1) // 2
    Z = big_z * (big_z - 1) // 2
    want_den = float(np.sqrt(float((T - Z) * T)))
    check("C4 pair counts stay exact past int64 (n=200k)",
          big['total_pairs'] == T and big['reference_ties'] == Z
          and np.isfinite(big['tau_b_denominator'])
          and np.isclose(big['tau_b_denominator'], want_den, rtol=0, atol=1e-3),
          f"denominator {big['tau_b_denominator']:.6g} vs {want_den:.6g}; product {(T - Z) * T:.3e} > int64")
    # Large pair-count products exceed int64 even for moderate benchmark graphs.
    # Two equal blocks have 10^10 concordances and denominator 10^10 exactly.
    big = np.repeat([0., 1.], 100000)
    b = run(big, big)
    check("C4 denominator handles pair products above int64",
          b['tau_b_denominator'] == 1e10 and np.isclose(b['tau_all'], 1))
    for y, s, d in [([0, -1], [0, 1], [True, False]),
                    ([0, 1], [0, np.nan], [True, False]),
                    ([0, 1], [0], [True, False]),
                    ([0, 1], [0, 1], [0, 1])]:
        try:
            run(y, s, d)
        except ValueError:
            check("C4 invalid input rejected", True)
        else:
            check("C4 invalid input rejected", False)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/email-Eu-core.txt"
    net = load_edgelist(path)
    print("=" * 78)
    print(f"verify_pipeline on {net.name}  (n={net.n:,} m={net.m:,})")
    print("=" * 78)

    # ---------------------------------------------------------------- 1, 2
    print("\n1-2. MERGED SHELL + CI TRAVERSAL vs THE REFERENCE IMPLEMENTATIONS")
    sc, sdm, sdx, ci, hop_s = shell_and_ci_pass(net, MAX_HOP)

    sc_o = np.zeros((net.n, MAX_HOP))
    sdm_o = np.zeros((net.n, MAX_HOP))
    sdx_o = np.zeros((net.n, MAX_HOP))
    for i in range(net.n):
        for h, sh in enumerate(bfs_shells(net, i, MAX_HOP)):
            sc_o[i, h] = len(sh)
            if len(sh):
                d = net.degree[sh].astype(np.float64)
                sdm_o[i, h] = d.mean()
                sdx_o[i, h] = d.max()
    ci_o = np.column_stack([collective_influence(net, l)
                            for l in range(1, MAX_HOP + 1)])

    check("shell counts bit-identical", np.array_equal(sc, sc_o))
    check("shell degree mean bit-identical", np.array_equal(sdm, sdm_o))
    check("shell degree max bit-identical", np.array_equal(sdx, sdx_o))
    check("collective influence bit-identical", np.array_equal(ci, ci_o))
    # The reference expands one level past what it returns; the merged pass
    # does not. If that mattered, the arrays above would differ.
    check("skipping the final expansion is safe",
          np.array_equal(sc, sc_o) and np.array_equal(ci, ci_o))
    check("per-hop timings are all positive",
          all(t > 0 for t in hop_s), f"{['%.3f' % t for t in hop_s]}")

    # ------------------------------------------------------------------ 2b
    print("\n2b. EGO-BETWEENNESS: FAST PATH vs THE SET-BASED REFERENCE")
    fast = ego_betweenness(net)
    ref = np.zeros(net.n)
    for i in range(net.n):
        nb = net.nbrs[i]
        if len(nb) >= 2:
            ref[i] = _ego_betweenness_sets(net, nb, len(nb))
    d = float(np.abs(fast - ref).max())
    scale = max(float(ref.max()), 1e-12)
    # Not bit-identity: the two sum the same terms in a different order, and
    # floating-point addition is not associative. Relative agreement is the
    # right bar, and it is the same bar used for ego-betweenness against
    # brute-force betweenness elsewhere in the project.
    check("fast path matches reference", d / scale < 1e-11,
          f"max|diff|={d:.2e} relative={d/scale:.2e}")
    # Task 6 finding P3-05 (Claude Opus 5, 2026-09-11): this used to be
    # check(..., True, ...) - a line that could never fail. The dense k x k
    # path is only taken at degree >= EGO_DENSE_MIN_DEGREE, so on a sparse
    # fixture the fast-vs-reference comparison above never touches it. Call it
    # directly on the highest-degree nodes instead, whatever the fixture.
    from influence.features import EGO_DENSE_MIN_DEGREE, _ego_betweenness_dense
    top = [int(i) for i in np.argsort(-net.degree)[:5] if len(net.nbrs[i]) >= 2]
    worst = 0.0
    for i in top:
        nb = net.nbrs[i]
        a = _ego_betweenness_dense(net, nb, len(nb))
        b = _ego_betweenness_sets(net, nb, len(nb))
        worst = max(worst, abs(a - b) / max(abs(b), 1e-12))
    hub = int((net.degree >= EGO_DENSE_MIN_DEGREE).sum())
    check("dense ego-betweenness path agrees with the set-based reference on the top-degree nodes",
          bool(top) and worst < 1e-11,
          f"max relative diff {worst:.2e} over {len(top)} nodes; {hub} node(s) at degree >= "
          f"{EGO_DENSE_MIN_DEGREE} take the dense path in production on this fixture")

    # ------------------------------------------------------------------ 2c
    print("\n2c. GRAPHLET ORBITS: ORCA vs DIRECT ENUMERATION")
    from influence.graphlets import (orca_binary, count_node_orbits,
                                     brute_force_node_orbits, ORBIT_SPEC)
    if orca_binary() is None:
        print("      (no orca binary in vendor/, skipping - build it with:")
        print("       g++ -O2 -std=c++11 -static -o vendor/orca.exe vendor/orca.cpp)")
    else:
        # Small graphs only: the reference is O(n^4) by construction. Several
        # families, because a disagreement can hide in a structure one family
        # never produces - the paw orbit convention was caught exactly this way.
        from influence import generators as _gen
        for nm, g in [("ER", _gen.erdos_renyi(40, 5, seed=1)),
                      ("BA", _gen.barabasi_albert(40, 3, seed=2)),
                      ("WS", _gen.watts_strogatz(40, 6, 0.3, seed=3)),
                      ("HK", _gen.holme_kim(35, 3, 0.6, seed=4))]:
            got = count_node_orbits(g, 4)
            ref = brute_force_node_orbits(g)
            bad = sorted({int(c) for c in np.argwhere(got != ref)[:, 1]})
            check(f"all 15 orbits match on {nm} (n={g.n})", not bad,
                  "" if not bad else f"differing orbits: {bad}")

        # The radius tag on each orbit is the eccentricity of the node within
        # its graphlet, and every orbit must carry one.
        hops = sorted({h for _, h in ORBIT_SPEC.values()})
        check("every orbit has a radius tag", len(ORBIT_SPEC) == 15,
              f"radii present: {hops}")
        deep = [i for i, (_, h) in ORBIT_SPEC.items() if h == 3]
        check("only the induced-P4 endpoint needs 3 hops", deep == [4],
              f"hop-3 orbits: {deep}")

        # ------------------------------------------------------------ 2c-5
        # Added 2026-09-11 by Claude Opus 5 (Task 6 findings P1-08, P3-05).
        # 5-node orbits: ORCA's 58 columns must be, up to ONE permutation
        # shared by every node of every fixture, the 58 (isomorphism class,
        # automorphism orbit) count vectors that direct enumeration produces.
        # See the note above brute_force_five_node_orbits for what this does
        # and does not establish. Four fixtures because a sparse graph never
        # realises K5 and a dense one rarely realises an induced 5-path; all
        # 58 reference columns must be non-zero somewhere or a column could
        # match by being identically zero on both sides.
        print("\n2c-5. FIVE-NODE ORBITS: ORCA vs FIRST-PRINCIPLES ENUMERATION")
        from influence.graphlets import (brute_force_five_node_orbits,
                                         match_orbit_columns, _five_node_tables,
                                         _FIVE_PAIRS, ORBIT5_RADIUS)
        canon, orbit_of = _five_node_tables()
        check("connected 5-node graphs: 21 classes, 58 orbits from first principles",
              len(set(canon.values())) == 21
              and len({(c, o) for code, c in canon.items() for o in set(orbit_of[code])}) == 58)
        O, R, keys = [], [], None
        for nm, g in [("ER-sparse", _gen.erdos_renyi(30, 4, seed=11)),
                      ("ER-dense", _gen.erdos_renyi(16, 9, seed=12)),
                      ("HK", _gen.holme_kim(24, 3, 0.7, seed=13)),
                      ("WS", _gen.watts_strogatz(24, 6, 0.2, seed=14))]:
            k, ref = brute_force_five_node_orbits(g)
            keys = keys or k
            orca5 = count_node_orbits(g, 5)
            check(f"{nm} (n={g.n}): ORCA and enumeration count the same number of 5-node orbit memberships",
                  orca5.shape[1] == 73 and np.isclose(orca5[:, 15:].sum(), ref.sum()),
                  f"{int(orca5[:, 15:].sum())} vs {int(ref.sum())}")
            O.append(orca5[:, 15:])
            R.append(ref)
        O, R = np.vstack(O), np.vstack(R)
        check("every reference orbit is realised on at least one fixture",
              bool((R.sum(axis=0) > 0).all()), f"{int((R.sum(axis=0) > 0).sum())}/58")
        matched, ambiguous, unmatched = match_orbit_columns(O, R)
        check("all 58 ORCA 5-node columns match a reference vector under one bijection",
              len(matched) == 58 and not ambiguous and not unmatched,
              f"matched {len(matched)}, ambiguous groups {len(ambiguous)}, unmatched ORCA columns {unmatched}")
        # Three labels whose structure is unambiguous, as a check on the
        # numbering convention (Przulj 2007 as followed by ORCA). Only these
        # three graphlets are pinned by label; the rest are pinned by count.
        ref_to_orca = {r: o + 15 for o, r in matched.items()}
        bit = {p: i for i, p in enumerate(_FIVE_PAIRS)}
        k5 = (1 << 10) - 1
        k5e = k5 ^ 1                                  # K5 minus edge (0,1)
        p5 = sum(1 << bit[(a, a + 1)] for a in range(4))   # path 0-1-2-3-4
        def label(code, pos):
            return ref_to_orca.get(keys.index((canon[code], orbit_of[code][pos])))
        check("K5 node is ORCA orbit 72", label(k5, 0) == 72, f"got {label(k5, 0)}")
        check("K5-minus-edge: degree-3 node is orbit 70, degree-4 node is orbit 71",
              label(k5e, 0) == 70 and label(k5e, 2) == 71,
              f"got {label(k5e, 0)}, {label(k5e, 2)}")
        check("5-path: end 15, next-to-end 16, centre 17",
              (label(p5, 0), label(p5, 1), label(p5, 2)) == (15, 16, 17),
              f"got {(label(p5, 0), label(p5, 1), label(p5, 2))}")

        # Radius-tag regression gate (P3-05). The P1-01 retag of 2026-09-11
        # moved orbits 56,57,65,66,68,70 from hop 1 to hop 2; until now no gate
        # here would have noticed a table edit in either direction. The
        # derivation is exact eccentricity per orbit (_calib.derive_node_radius,
        # ~2 s); verify_calibration.py holds the fuller measurement checks.
        from _calib import derive_node_radius
        derived5 = derive_node_radius(5)
        diff5 = [(k, ORBIT5_RADIUS.get(k), v) for k, v in sorted(derived5.items())
                 if ORBIT5_RADIUS.get(k) != v]
        check("ORBIT5_RADIUS equals the exact eccentricity derivation for all 73 orbits",
              len(derived5) == 73 and not diff5,
              "" if not diff5 else f"(orbit, shipped, derived) {diff5[:10]}")
        check("retagged orbits 56,57,65,66,68,70 sit at hop 2",
              all(ORBIT5_RADIUS[k] == 2 for k in (56, 57, 65, 66, 68, 70)))

    # ------------------------------------------------------------------- 3
    print("\n3. TRIVALENCY: ONE DRAW PATH, NOT TWO")
    eu, ev, per_edge = dyn.symmetric_edge_probabilities(
        net, "trivalency", 0.0, np.random.default_rng(7))
    arc_p = dyn.edge_probabilities(net, "trivalency", 0.0,
                                   np.random.default_rng(7))
    rows = np.repeat(np.arange(net.n), np.diff(net.adj.indptr))
    cols = net.adj.indices
    lo = np.minimum(rows, cols).astype(np.int64)
    hi = np.maximum(rows, cols).astype(np.int64)
    key = eu.astype(np.int64) * net.n + ev.astype(np.int64)
    order = np.argsort(key)
    expect = per_edge[order][np.searchsorted(key[order], lo * net.n + hi)]
    check("percolation and direct paths agree", np.array_equal(arc_p, expect))
    A = sp.csr_matrix((arc_p, net.adj.indices, net.adj.indptr),
                      shape=net.adj.shape)
    check("both arcs of an edge carry the same p",
          float(abs(A - A.T).max()) < 1e-15)

    # ------------------------------------------------------------------- 4
    print("\n4. IGNITION THRESHOLD USES THE NETWORK SIZE")
    sub = np.arange(min(5, net.n))
    res = dyn.simulate_ic_direct(net, p=0.02, n_sims=30, convention="uniform",
                                 seed=0, nodes=sub, verbose=False)
    check("n_nodes is the network, not the sample",
          res.n_nodes == net.n,
          f"n_nodes={res.n_nodes} rows={res.sizes.shape[0]}")

    # --------------------------------------------------------------- 5, 6
    print("\n5-6. REGISTRY: COST GROUPS AND HOP TAGS")
    X, reg, timings = extract_features(net, max_hop=MAX_HOP, verbose=False)
    check("every feature has a cost group", reg["group"].notna().all())
    unknown = sorted(set(reg["group"]) - set(timings))
    check("every cost group has a timing key", not unknown, f"{unknown}")

    counts = {r: len(select_features(X, reg, max_hop=r,
                                     tiers=TIER_LADDER["node+edge+subgraph"]))
              for r in range(MAX_HOP + 1)}
    check("feature count is non-decreasing in radius",
          all(counts[r] <= counts[r + 1] for r in range(MAX_HOP)),
          f"{counts}")

    nbr_struct = [f for f in reg.feature
                  if f.startswith(("nbr_clustering_", "nbr_triangles_"))]
    hops = set(reg[reg.feature.isin(nbr_struct)]["hop"])
    check("neighbour clustering/triangle aggregates are hop 2",
          hops == {2}, f"found hops {sorted(hops)} over {len(nbr_struct)} features")
    nbr_deg = [f for f in reg.feature if f.startswith("nbr_degree_")]
    check("neighbour degree aggregates stay hop 1",
          set(reg[reg.feature.isin(nbr_deg)]["hop"]) == {1})

    # THE 2-BALL FAMILY MUST SHARE ONE TIER.
    #
    # ball2_edges, ball2_density and local_conductance_2 are three readings of
    # ONE array (P["ball2_edges"], plus the ball's size and degree volume). From
    # 2026-08-31 back to the day they were written, the first was tagged
    # `subgraph` and the other two `edge`. Because the richness ladder is nested,
    # that let the `node+edge` rung at r>=2 reconstruct ball2_edges exactly and
    # so read 2-ball structure it was supposed to be blind to - which inflated
    # the measured edge-tier gain and deflated the subgraph-tier gain, and put
    # the whole of Finding 10 on the wrong rung.
    #
    # A tier is a claim about what an observer is allowed to describe. Splitting
    # one quantity across two tiers makes that claim false whichever way the
    # ladder is read, so the invariant is simply: same source, same tier.
    ball2 = ["ball2_edges", "ball2_density", "local_conductance_2"]
    present = reg[reg.feature.isin(ball2)]
    tiers_2b = set(present["tier"])
    check("the 2-ball family shares one tier (one array, one rung)",
          len(present) == len(ball2) and tiers_2b == {"subgraph"},
          f"{dict(zip(present.feature, present.tier))}")

    costs = {r: feature_cost(
        select_features(X, reg, max_hop=r,
                        tiers=TIER_LADDER["node+edge+subgraph"]), reg, timings)
        for r in range(MAX_HOP + 1)}
    check("feature cost strictly increases with radius",
          all(costs[r] < costs[r + 1] for r in range(MAX_HOP)),
          " ".join(f"r{r}={c:.3f}s" for r, c in costs.items()))

    # ------------------------------------------------------------------- 6b
    print("\n6b. PER-NODE GLOBAL QUANTITIES (profiling axes for the atlas)")
    core = st.core_numbers(net)
    try:
        import igraph as ig
        coo = sp.triu(net.adj, k=1).tocoo()
        g = ig.Graph(n=net.n,
                     edges=list(zip(coo.row.tolist(), coo.col.tolist())),
                     directed=False)
        check("core_numbers matches igraph exactly",
              np.array_equal(core, np.asarray(g.coreness())),
              f"max core = {int(core.max())}")
    except ImportError:
        print("      (igraph absent, skipping coreness cross-check)")

    # The H-index ladder approaches coreness FROM ABOVE, not below:
    #     degree = h^(0) >= h^(1) >= h^(2) >= ... >= coreness
    # Each application of the H-operator can only shrink the value, and the
    # fixed point is the core number. So h^(3) is an over-estimate of coreness,
    # and the gap h^(3) - coreness is the amount by which a bounded local view
    # over-reads how deeply embedded a node is. That gap is a profiling axis in
    # the failure atlas, so its sign has to be right.
    h3 = X["h_index_3"].to_numpy() if "h_index_3" in X.columns else None
    if h3 is not None:
        check("h_index_3 is an upper bound on coreness", bool((h3 >= core).all()),
              f"max over-read = {int((h3 - core).max())}, "
              f"exact on {100 * (h3 == core).mean():.0f}% of nodes")
        deg = X["degree"].to_numpy()
        h1 = X["h_index_1"].to_numpy()
        h2 = X["h_index_2"].to_numpy()
        check("the ladder is non-increasing in order",
              bool((deg >= h1).all() and (h1 >= h2).all() and (h2 >= h3).all()))

    d_hub = st.distance_to_hubs(net)
    check("hub distance is finite everywhere inside the LCC",
          bool((d_hub < net.n).all()), f"max = {int(d_hub.max())} hops")
    check("hub distance is zero exactly at the hubs",
          int((d_hub == 0).sum()) == max(1, int(round(0.01 * net.n))))

    # ------------------------------------------------------------------- 6c
    print("\n6c. THE TIER LADDER MUST ACTUALLY VARY INFORMATION")
    # Five of the six original edge/subgraph features were exact algebraic
    # functions of node-tier columns, so the richness axis of the
    # depth-vs-richness experiment was barely varying at all. These identities
    # are checked here as a standing guard: if a future edit reintroduces a
    # derived column, it fails loudly rather than inflating the feature count.
    gv = {c: X[c].to_numpy(dtype=np.float64) for c in X.columns
          if c not in ("node", "original_id")}
    kk = gv["degree"]
    tri = gv["clustering_coefficient"] * kk * (kk - 1) / 2.0
    for nm, recon in [("triangle_count", tri),
                      ("ego_net_edges", tri + kk),
                      ("edges_leaving_ego",
                       gv["nbr_degree_sum"] - 2 * tri - kk),
                      ("ego_net_size", kk + 1.0)]:
        err = float(np.abs(recon - gv[nm]).max())
        check(f"'{nm}' is still a known derived column", err < 1e-8,
              f"max|err|={err:.1e} - documented, not a bug")

    # The features added to make the tier axis mean something must NOT be
    # derived. If one of these ever became recoverable in closed form it would
    # be back to decorating the ladder.
    genuinely_new = ["edge_overlap_std", "edge_embeddedness_std",
                     "local_conductance_2", "ball2_edges", "ego_betweenness"]
    present = [f for f in genuinely_new if f in gv]
    check("the independent edge/subgraph features are present",
          len(present) == len(genuinely_new), f"{len(present)}/{len(genuinely_new)}")
    # Cheap necessary condition: none of them may be rank-identical to degree.
    from scipy.stats import spearmanr as _sr
    worst_nm, worst_rho = None, 0.0
    for f in present:
        r = abs(float(_sr(gv[f], kk).statistic))
        if r > worst_rho:
            worst_nm, worst_rho = f, r
    check("none of them duplicates degree", worst_rho < 0.999,
          f"max |rho| to degree = {worst_rho:.4f} ({worst_nm})")

    # ------------------------------------------------------------------- 7
    print("\n7. THE LEAKAGE GUARD")
    good = select_features(X, reg, max_hop=MAX_HOP,
                           tiers=TIER_LADDER["node+edge+subgraph"])
    try:
        assert_no_leakage(good)
        check("real feature set passes", True, f"{len(good)} features")
    except ValueError as e:
        check("real feature set passes", False, str(e)[:60])

    for bad in ["betweenness", "log_pagerank", "closeness_centrality",
                "coreness", "spread_mean", "k_shell_index"]:
        try:
            assert_no_leakage(good + [bad])
            check(f"guard catches '{bad}'", False, "NOT CAUGHT")
        except ValueError:
            check(f"guard catches '{bad}'", True)

    try:
        assert_no_leakage(list(ALLOWED_EXCEPTIONS))
        check("guard allows the documented exceptions", True)
    except ValueError as e:
        check("guard allows the documented exceptions", False, str(e)[:60])

    # ------------------------------------------------------------------
    # 8. Column ORDER still matches what produced the stored sweeps.
    #
    # This check exists because of a bug that nothing else here could see.
    # `select_features` returns columns in registry ROW ORDER, and a random
    # forest draws its per-split candidate features from its RNG BY INDEX - so
    # a fixed random_state fixes the index sequence, not the features. Permute
    # the columns and you get a different forest from the same seed and the
    # same feature set.
    #
    # On 2026-08-31 two features were retagged edge -> subgraph, which rewrote
    # the registry and MOVED their rows (65, 90 -> 107, 109). The audit
    # compared feature SETS, correctly refitted the 400 node+edge cells where
    # the set shrank, and left the richest tiers alone because their set was
    # unchanged. Their order was not. 800 cells silently stopped matching the
    # code that would produce them, by up to 1.1e-03 in tau - larger than
    # several of the gains this project reports.
    #
    # A retag is a one-line diff with no visible consequence, which is exactly
    # why it needs a machine to notice. `sweep_<tag>.columns.json` records the
    # ordered column list behind every cell; this compares it against what the
    # registry yields today. Regenerate it ONLY by re-running the affected
    # cells (see repair_column_order.py) - never by overwriting it to make this
    # check pass, which would restore precisely the silence it exists to break.
    print("\n[8] stored sweeps still match the current column order")
    fingerprints = sorted(glob.glob("sweep_*.columns.json"))
    if not fingerprints:
        check("column-order fingerprints present", False,
              "none found - run repair_column_order.py --apply")
    for fp_path in fingerprints:
        tag = os.path.basename(fp_path)[len("sweep_"):-len(".columns.json")]
        with open(fp_path) as fh:
            stored = json.load(fh)
        try:
            Xh = pd.read_csv(f"cache_features_{tag}.csv", nrows=1)
            regh = pd.read_csv(f"cache_registry_{tag}.csv")
        except FileNotFoundError:
            check(f"{tag}: caches present", False, "feature/registry cache missing")
            continue

        bad = []
        for key, cols in stored.items():
            r, tier_name = key.split("|")
            now = select_features(Xh, regh, max_hop=int(r),
                                  tiers=TIER_LADDER[tier_name])
            if now != cols:
                # Name the failure mode - a reorder and a genuine feature
                # change need completely different responses.
                bad.append(f"{key} ({'reordered' if set(now) == set(cols) else 'set changed'})")
        check(f"{tag}: column order unchanged", not bad,
              f"{len(stored)} cells" if not bad else "; ".join(bad[:3]))

    # ------------------------------------------------------------------- N9
    # The reported-objective splice (adopted 2026-09-04).
    #
    # analyse.load() reports betweenness from the log1p arm and everything else
    # from the raw sweep. That is a silent, read-time substitution, so it is
    # exactly the kind of thing that can revert without anyone noticing - a
    # deleted file, a truncated re-sweep, an accidental raw=True. These checks
    # make the substitution assert itself on every run.
    print("\nN9. THE REPORTED-OBJECTIVE SPLICE")
    import analyse as _an

    tags = [t for t in _an.discover_networks() if "__" not in t]
    check("networks discovered", len(tags) == 5, f"{len(tags)}: {tags}")

    worst_spread, n_moved, missing = 0.0, 0, []
    for tag in tags:
        src = _an.REPORTED_BETWEENNESS.format(tag=tag)
        if not os.path.exists(src):
            missing.append(tag)
            continue
        raw, rep = _an.load(tag, raw=True), _an.load(tag)

        # The three spreading targets must pass through UNTOUCHED. If the
        # splice ever widened beyond betweenness it would silently re-base
        # 2,400 cells that were never eligible for the transform.
        for t in ("spread_mean", "spread_cv", "spread_resid"):
            k = ["radius", "richness", "seed"]
            j = raw[raw.target == t].merge(rep[rep.target == t], on=k,
                                           suffixes=("_a", "_b"))
            worst_spread = max(
                worst_spread,
                float((j.kendall_tau_a - j.kendall_tau_b).abs().max()))

        # And betweenness must actually have MOVED, or the splice is a no-op
        # and the correction is not in force at all.
        ka = raw[raw.target == "betweenness"].kendall_tau.mean()
        kb = rep[rep.target == "betweenness"].kendall_tau.mean()
        n_moved += abs(ka - kb) > 1e-9

    check("log1p betweenness present for every network", not missing,
          f"missing: {missing}")
    check("spreading targets pass through untouched",
          worst_spread == 0.0, f"worst |dtau| = {worst_spread:.3e}")
    check("betweenness is actually re-based (splice is not a no-op)",
          n_moved == len(tags), f"{n_moved}/{len(tags)} networks moved")

    # The B2 comparison must stay entirely inside the raw arm, or "estimator
    # disagreement" would partly be Finding 11's objective effect in disguise.
    import analyse_estimators as _ae
    import inspect
    check("analyse_estimators baseline pinned to raw",
          "raw=True" in inspect.getsource(_ae.sweep_for))

    # ------------------------------------------------------------------ N10
    # C1: the zero-inflation closed form (study_doc_v2.md 24.4-24.5).
    #
    # w_exact carries more weight than its one line suggests: 24.5's tau floor,
    # the ordering reversal that makes facebook the corpus's BEST betweenness
    # result rather than its worst, and the whole D2 scoring critique are all
    # computed from it. analyse_betweenness.py asserts it, but that script is
    # run by hand; a guarantee nobody executes is a guarantee in prose only.
    #
    # These call analyse_betweenness.boundary_share rather than recomputing the
    # formula, deliberately. A second copy here would verify that this file
    # agrees with itself, which is worth nothing - the failure mode being
    # guarded is the two implementations drifting apart.
    #
    # The published table is pinned too. The identity holding says the
    # arithmetic is self-consistent; it does NOT say the corpus still has the
    # zero fractions the study doc reports. A re-cached target column with a
    # different endpoint convention would satisfy the identity perfectly and
    # silently invalidate every number in 24.4 and 24.5.
    print()
    print("N10. ZERO-INFLATION CLOSED FORM (C1)")
    from analyse_betweenness import boundary_share

    # study_doc_v2.md 24.4, to the three decimals the plan requires.
    # 24.5 (this check caught it, 2026-09-04 - a truncation, not a round).
    PUBLISHED_W = {"ca-GrQc": 0.710, "ca-HepTh": 0.654,   # 0.653519 -> rounds UP; the doc read 0.653 until
                   "p2p-Gnutella08": 0.435, "email-Eu-core": 0.263,
                   "facebook_combined": 0.156}

    worst_gap, drifted, seen = 0.0, [], 0
    for tag, want in PUBLISHED_W.items():
        f = f"cache_targets_{tag}.csv"
        if not os.path.exists(f):
            drifted.append(f"{tag}: no {f}")
            continue
        seen += 1
        B = boundary_share(pd.read_csv(f)["betweenness"].to_numpy(float))
        worst_gap = max(worst_gap, B["gap"])
        if round(B["w_exact"], 3) != want:
            drifted.append(f"{tag}: {B['w_exact']:.4f} vs published {want}")

    # The tau floor, pinned separately from w and for a different reason.
    #
    # w and the floor are DIFFERENT QUANTITIES and conflating them is exactly
    # the error this check was added to prevent (2026-09-05): 24.5 asserted
    # tau_floor = w, which silently assumed tau = (C-D)/scoreable rather than
    # tau-b's (C-D)/sqrt(scoreable*total). Pinning only w would leave that
    # confusion re-derivable by anyone reading the table.
    PUBLISHED_FLOOR = {"ca-GrQc": 0.593, "ca-HepTh": 0.571,
                       "p2p-Gnutella08": 0.418, "email-Eu-core": 0.260,
                       "facebook_combined": 0.156}

    floor_drift = []
    for tag, want in PUBLISHED_FLOOR.items():
        f = f"cache_targets_{tag}.csv"
        if not os.path.exists(f):
            continue
        B = boundary_share(pd.read_csv(f)["betweenness"].to_numpy(float))
        if round(B["tau_floor"], 3) != want:
            floor_drift.append(f"{tag}: {B['tau_floor']:.4f} vs published {want}")
        # w must NOT equal the floor - if a refactor ever collapses them, the
        # 24.5 error is back. z > 0 on every corpus network, so sqrt(1-z^2) < 1
        # strictly and the two must differ.
        if abs(B["tau_floor"] - B["w_exact"]) < 1e-9:
            floor_drift.append(f"{tag}: tau_floor collapsed onto w_exact")

    check("all five networks present", seen == 5, f"{seen}/5")
    check("tau floor matches study_doc_v2 24.5 to 3 dp", not floor_drift,
          "; ".join(floor_drift) if floor_drift else "all five agree")
    check("w_exact == counted share (identity)", worst_gap < 1e-12,
          f"worst gap = {worst_gap:.3e}")
    check("w_exact matches study_doc_v2 24.4 to 3 dp", not drifted,
          "; ".join(drifted) if drifted else "all five agree")

    # ------------------------------------------------------------------ N11
    # C5: betweenness_k, and the bridge between it and the 24.1 Proposition.
    #
    # Two claims are pinned here, and the second one is the interesting one.
    #
    # (i) TRUNCATION IS EXACT IN THE LIMIT. b_k with k >= the graph diameter
    #     must reproduce full betweenness exactly. This is the end-to-end test
    #     of the vectorised early-terminated Brandes in targets.py - the
    #     forward sigma recursion, the backward accumulation and the /2 are all
    #     wrong-able independently, and any of them being wrong would produce a
    #     plausible-looking ranking rather than an obvious failure.
    #
    # (ii) b_2's SUPPORT IS EXACTLY THE NONZERO SET. b_2(v) counts precisely
    #     the pairs of NON-ADJACENT NEIGHBOURS of v (those are the only pairs at
    #     distance 2 with v interior), so b_2(v) > 0 iff N(v) is not a clique
    #     iff v is not simplicial iff b(v) > 0 by the Proposition of 24.1.
    #     b_2 IS that proposition, arithmetised. Checking it here means the
    #     proposition now has a second, independent computational witness -
    #     one that never touches ego_betweenness, which is what the existing
    #     canary in analyse_betweenness.py uses.
    #
    # Cost: b_2 on all five (~13 s) plus one k=diameter run on the smallest
    # network. The diameter identity is checked on email-Eu-core alone because
    # b_k at k = diameter is full Brandes and there is no point paying for it
    # five times to test one recursion.
    print()
    print("N11. BETWEENNESS_K TRUNCATION AND THE 24.1 PROPOSITION (C5)")
    # `load_edgelist` is already imported at module scope - re-importing it
    # here would shadow it as a local for the WHOLE function, including the
    # calls hundreds of lines above this point, which is exactly what happened
    # the first time this block was written.
    import networkx as nx
    from analyse_betweenness_k import manifest_paths
    from influence.targets import truncated_betweenness, exact_betweenness

    paths = manifest_paths()
    support_bad, seen_k = [], 0
    for tag in PUBLISHED_W:
        f, p = f"cache_targets_{tag}.csv", paths.get(tag)
        if p is None or not os.path.exists(f) or not os.path.exists(p):
            continue
        seen_k += 1
        net = load_edgelist(p, name=tag)
        bc = pd.read_csv(f)["betweenness"].to_numpy(float)
        if not np.array_equal(truncated_betweenness(net, 2) > 0, bc > 0):
            support_bad.append(tag)

    check("b_2 support == nonzero betweenness set (24.1, arithmetised)",
          not support_bad and seen_k == 5,
          f"{seen_k}/5 networks" + (f"; FAILED on {support_bad}" if support_bad else ""))

    small = "email-Eu-core"
    if small in paths and os.path.exists(paths[small]):
        net = load_edgelist(paths[small], name=small)
        g = nx.Graph()
        g.add_nodes_from(range(net.n))
        coo = sp.triu(net.adj, k=1).tocoo()
        g.add_edges_from(zip(coo.row.tolist(), coo.col.tolist()))
        diam = nx.diameter(g)
        gap = float(np.abs(truncated_betweenness(net, diam)
                           - exact_betweenness(net)).max())
        check(f"b_k at k=diameter ({diam}) == exact betweenness [{small}]",
              gap < 1e-6, f"max |diff| = {gap:.3e}")

    # ------------------------------------------------------------------ N11
    # C3: the two mixture forms, and the independent zero-set implementation.
    #
    # analyse_c3_benchmarks.py computes z straight from data/<net>.txt without
    # touching a single cached column, so it is the only path in the repo that can
    # contradict 24.4's published w table on independent evidence. If it ever stops
    # reproducing that table, either the local certificate or the loader has moved,
    # and every external number in 26i is computed on sand.
    #
    # The tie check pins the OTHER half of 26i: which denominator tau-b uses depends
    # on whether the scored predictions tie on the zero set. 24.5 was revised on
    # 2026-09-05 on the premise that predictions are continuous.
    #
    # CORRECTED 2026-09-07. That premise was stated here as "true of this project's
    # forests", which is false: a random forest averages finitely many leaf means, and
    # cache_oof_ca-GrQc.npz holds 201 distinct predictions over 4,158 nodes (98 over the
    # 2,288 true zeros). The premise is true of the HYPOTHETICAL zero-skill method whose
    # floor 24.5 derives, not of the forests. Nothing measured moves: reported taus come
    # from scipy's kendalltau, which handles the forests' real ties, and the floor is a
    # printed margin reference only. It remains false of a masked GNN, which is the
    # contrast this check exists to pin. Both forms are asserted here so that neither can
    # be quietly promoted into "the" formula again.
    print()
    print("N11. C3 MIXTURE FORMS AND INDEPENDENT ZERO SET")
    from analyse_c3_benchmarks import check_tie_denominator, gate_project_table

    ok_tie, tie_msg = check_tie_denominator()
    check("both tau-b mixture forms match scipy on synthetic tie regimes",
          ok_tie, " | ".join(x.strip() for x in tie_msg.splitlines() if x.strip()))

    ok_tab, tab_msg = gate_project_table()
    check("independent zero-set implementation reproduces 24.4's w table",
          ok_tab, " | ".join(x.strip() for x in tab_msg.splitlines() if x.strip()))

    # Equal zero counts can hide opposite nodewise mistakes. Require aligned raw
    # IDs, cache order and both mismatch directions on every fallback graph.
    from verify_c3_fallback import gate_project_fallback
    ok_fallback, fallback_msg = gate_project_fallback()
    check("C3 fallback agrees nodewise on all five required graphs",
          ok_fallback, fallback_msg.splitlines()[-1])

    # verify_c3_scoring reports with bare asserts, so until 2026-09-11 a
    # failure there aborted this gate mid-run and the C4 checks below never
    # printed (Task 6 finding P3-05, Claude Opus 5). Fold it into the FAIL
    # list instead; its own stdout still shows which assertion tripped.
    from verify_c3_scoring import main as check_c3_scoring_provenance
    try:
        check_c3_scoring_provenance()
        check("C3 scoring provenance fixtures", True)
    except Exception as exc:                          # noqa: BLE001 - any failure is a FAIL line
        check("C3 scoring provenance fixtures", False,
              f"{type(exc).__name__}: {str(exc)[:200]}")

    check_c4()
    print("\n" + "=" * 78)
    if FAIL:
        print(f"FAILURES ({len(FAIL)}):")
        for f in FAIL:
            print("   -", f)
        raise SystemExit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()

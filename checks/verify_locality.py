"""
checks/verify_locality.py
=========================
Semantic locality gate: every feature tagged hop h must be computable from
what a radius-h observer can see.

WHY THIS EXISTS
---------------
The leakage guard in influence/targets.py matches column NAMES. It stops a
global quantity called `betweenness` from becoming an input, but it says
nothing about whether a column honestly tagged `hop=1` really needs only one
hop. Hop tags are hand-assigned, and this project has already been bitten by
tags that were too shallow (neighbour clustering once sat at hop 1, six
5-node orbits sat at hop 1 when they need hop 2). A tag that is too shallow
does not crash anything: it feeds a deeper budget into every shallower cell
and produces a plausible, wrong locality curve. This gate tests the tags
against their definition instead of trusting them.

THE OBSERVER'S VIEW
-------------------
The project's convention is that a radius-r observer at v knows the nodes
within r hops, every edge among them, and the degree of each node on the
boundary. That view is built here as a real graph:

  * the induced subgraph on the ball B_r(v);
  * for every node at distance exactly r, one pendant "stub" leaf per
    neighbour it has outside the ball, so its degree equals its true degree.

Stubs sit at distance r + 1 from v, outside what any hop <= r feature may use.
Nodes at distance < r need no stubs: all their neighbours are inside the ball.

THE TEST
--------
For sampled nodes v on several graph families and every r in 0..MAX_HOP,
extract the full feature table on the view and compare it, at v, with the
table extracted on the whole graph. Every column registered at hop <= r must
agree. A mismatch means the column needs more than its tag admits.

One column is exempt by design: `degree_normalized` divides by n, a global
constant the project documents as a rescaling rather than structure. The
dynamic tier is compared too, with the same p on both sides; p is assumed
known by that tier's definition.

The report also lists, informationally, columns whose value never changed
between the radius-(h-1) view and the truth on any sampled node. Such a tag
may be deeper than necessary - conservative, so harmless to the experiment,
but it under-credits the shallower radius.

Run:  python checks/verify_locality.py [--nodes K]
Needs vendor/orca (or orca.exe) for the graphlet columns; without it those
columns are absent on both sides and the check covers the rest.
"""
import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import argparse
import sys

import numpy as np

from influence import generators as gen
from influence.features import bfs_shells, extract_features
from influence.graphlets import orca_binary
from influence.preprocessing import Network, build_network

MAX_HOP = 3
P_TRANSMISSION = 0.2          # any fixed p in (0, 1): the dynamic tier is a function of it
EXEMPT = {"degree_normalized"}
RTOL, ATOL = 1e-9, 1e-9


def observer_view(net: Network, v: int, r: int) -> tuple[Network, int]:
    """The radius-r view of v as a Network, and v's index inside it."""
    shells = bfs_shells(net, v, r) if r > 0 else []
    ball = np.concatenate([np.array([v], dtype=np.int64)] + [s.astype(np.int64) for s in shells])
    inball = np.zeros(net.n, dtype=bool)
    inball[ball] = True
    boundary = shells[r - 1] if r > 0 else np.array([v], dtype=np.int64)

    edges = []
    for u in ball.tolist():
        for w in net.nbrs[u].tolist():
            if u < w and inball[w]:
                edges.append((u, w))
    next_label = net.n                      # stub labels never collide with node labels
    for u in boundary.tolist():
        missing = int(net.degree[u] - inball[net.nbrs[u]].sum())
        for _ in range(missing):
            edges.append((u, next_label))
            next_label += 1
    if not edges:                           # an isolated v cannot occur inside an LCC
        raise ValueError(f"empty view for node {v} at r={r}")
    view = build_network(edges, name=f"view_v{v}_r{r}")
    idx = int(np.flatnonzero(view.original_ids == v)[0])
    return view, idx


def features_at(net: Network, idx: int) -> tuple[dict[str, float], dict[str, int]]:
    X, reg, _ = extract_features(net, max_hop=MAX_HOP, verbose=False,
                                 p_transmission=P_TRANSMISSION)
    row = X.iloc[idx]
    values = {c: float(row[c]) for c in reg["feature"] if c in X.columns}
    hops = dict(zip(reg["feature"], reg["hop"].astype(int)))
    return values, hops


def families(seed: int):
    """Small graphs that exercise different local structure."""
    return [
        ("HK clustered", gen.holme_kim(160, 3, 0.7, seed=seed)),
        ("BA hubs", gen.barabasi_albert(160, 2, seed=seed)),
        ("WS lattice", gen.watts_strogatz(160, 6, 0.1, seed=seed)),
        ("ER sparse", gen.erdos_renyi(160, 3.0, seed=seed)),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", type=int, default=12, help="sampled nodes per graph")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    print("=" * 78)
    print("verify_locality - every hop-h feature must be computable from the h-ball")
    print("=" * 78)
    has_orca = orca_binary() is not None
    print(f"ORCA binary: {'found' if has_orca else 'absent - graphlet columns not covered'}")

    rng = np.random.default_rng(args.seed)
    violations: dict[str, list[str]] = {}
    ever_changed: dict[str, bool] = {}
    hop_of: dict[str, int] = {}
    n_compared = 0

    for fam, net in families(args.seed):
        truth_rows = None
        sample = rng.choice(net.n, size=min(args.nodes, net.n), replace=False)
        X_full, reg_full, _ = extract_features(net, max_hop=MAX_HOP, verbose=False,
                                               p_transmission=P_TRANSMISSION)
        hop_of.update(dict(zip(reg_full["feature"], reg_full["hop"].astype(int))))
        truth_rows = X_full
        fam_bad = 0
        for v in sample.tolist():
            truth = truth_rows.iloc[v]
            for r in range(0, MAX_HOP + 1):
                view, idx = observer_view(net, v, r)
                seen, _ = features_at(view, idx)
                for col, h in hop_of.items():
                    if col in EXEMPT or col not in truth_rows.columns:
                        continue
                    t = float(truth[col])
                    s = seen.get(col, 0.0)     # an all-zero orbit is dropped from a small view
                    same = bool(np.isclose(s, t, rtol=RTOL, atol=ATOL))
                    if h <= r:
                        n_compared += 1
                        if not same:
                            fam_bad += 1
                            violations.setdefault(col, []).append(
                                f"{fam} v={v} r={r}: view={s:.6g} truth={t:.6g}")
                    elif h == r + 1 and not same:
                        ever_changed[col] = True
        print(f"  {fam:14s} n={net.n:4d}  sampled {len(sample)} nodes x r=0..{MAX_HOP}"
              f"   locality violations: {fam_bad}")

    print(f"\ncomparisons at hop <= r: {n_compared:,}")
    if violations:
        print(f"\nFAIL  {len(violations)} column(s) need more than their hop tag:")
        for col, cases in sorted(violations.items()):
            print(f"  {col} (tagged hop {hop_of[col]}), {len(cases)} case(s); e.g. {cases[0]}")
    else:
        print("PASS  every column registered at hop h matched the truth on every h-ball view")

    deep = sorted(c for c, h in hop_of.items()
                  if 1 <= h <= MAX_HOP and c not in EXEMPT and not ever_changed.get(c, False))
    print(f"\nINFO  {len(deep)} column(s) never differed between the (h-1)-view and the truth"
          " on the sampled nodes (tag possibly deeper than needed; harmless):")
    for c in deep:
        print(f"    hop {hop_of[c]}  {c}")

    print("\n" + "=" * 78)
    if violations:
        print(f"FAILURES ({len(violations)})")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()

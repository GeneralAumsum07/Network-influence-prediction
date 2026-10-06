"""
C6 / O1 confound check: is betweenness's residual autocorrelation just the
SIMPLICIAL ZERO SET?

WHY THIS RUNS BEFORE THE HEADLINE IS WRITTEN
--------------------------------------------
The full correlogram (`analyse_moran_correlogram.py`) returns a clean split:
lag-1 Moran's I on the three spreading targets COLLAPSES as r deepens
(facebook `spread_mean` 0.534 -> 0.032 -> 0.017 -> 0.011), while on
`betweenness` it stays flat or RISES on four of five networks (p2p 0.144 ->
0.147 -> 0.155 -> 0.163). Read naively that is O1's headline: correlation that
does not shrink as features deepen cannot be feature overlap, so it must be the
target.

There is an alternative explanation that produces the identical signature and
has nothing to do with target-level autocorrelation:

  - roughly half of every corpus network is SIMPLICIAL, with b(v) = 0 exactly
    (§24.1's proposition; §26f's `b_2` witness);
  - simplicial nodes are spatially CLUSTERED - they are low-degree and sit
    inside cliques, so a simplicial node's neighbours are disproportionately
    simplicial too;
  - the model has systematically signed residuals on that set, because ranking
    a mass of exact ties against a continuous prediction cannot be done well;
  - and crucially, NO amount of extra feature radius fixes that, because the
    zero set is already decidable at radius 1. So the piece of the residual
    field that comes from the zero set is BOTH spatially clustered AND immune
    to r - which is exactly "flat and long-range regardless of r".

This is the same confound that has already been caught twice in this project
(§26f's dip investigation, where correcting the reference population from the
whole graph to {v : b(v) > 0} REVERSED ca-HepTh's conclusion). Writing the
headline without running this check would be repeating that mistake a third
time, on a bigger claim.

THE TEST
--------
Recompute the betweenness correlogram on the nonzero subset only - sources,
shell membership and denominator all restricted to {v : b(v) > 0} - with hop
distances still taken on the FULL graph, since the question is about positions
in the network, not about the induced subgraph's own geometry.

  - If I collapses toward the null on the subset, the flat-and-long-range
    signature was the zero set, and O1's headline is a statement about
    zero-inflation - which is D2's territory, not a new phenomenon.
  - If I survives at comparable magnitude, the autocorrelation is carried by
    the nodes that actually have a ranking problem, and the headline stands.

Usage:
    python probe_moran_zeroset.py [--perms 199]
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

import analyse
from analyse_betweenness_k import manifest_paths
from analyse_moran_correlogram import (FULL, SEEDS, morans_i, oof_store,
                                       rank_pct)
from influence.preprocessing import load_edgelist

RADII = (0, 1, 2, 3)
DMAX = 7


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=199)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results_moran_zeroset.csv")
    args = ap.parse_args()

    paths = manifest_paths()
    rows = []

    for tag in [t for t in analyse.discover_networks() if t in paths]:
        net = load_edgelist(paths[tag], name=tag)
        n = net.n
        bc = pd.read_csv(f"cache_targets_{tag}.csv")["betweenness"].to_numpy(float)
        nz = bc > 0
        store = oof_store(tag, "betweenness")
        if not store:
            continue
        print(f"\n=== {tag}  n={n:,}  nonzero={int(nz.sum()):,} "
              f"({nz.mean():.1%}) ===", flush=True)

        # Is the zero set itself clustered? If it is not, the confound cannot
        # operate and the rest of this script is moot - so measure it rather
        # than assuming it. Moran's I of the 0/1 indicator at lag 1.
        ind = nz.astype(float)[:, None]
        ind = ind - ind.mean()
        I_ind, _ = morans_i(net.adj.astype(np.float32), ind, 1, args.batch)
        print(f"  lag-1 Moran's I of the nonzero INDICATOR itself: "
              f"{I_ind[0, 0]:+.4f}   (0 => zero set is spatially unclustered, "
              f"confound impossible)", flush=True)

        # Rank residuals, ranked WITHIN the nonzero subset. Ranking over all n
        # and then slicing would carry the zero block's rank mass into the
        # subset and defeat the purpose.
        y_nz = bc[nz]
        ypct = rank_pct(y_nz)
        cols, meta = [], []
        for r in RADII:
            for s in SEEDS:
                key = f"betweenness|{r}|{FULL}|{s}"
                if key in store:
                    v = np.zeros(n)
                    v[nz] = ypct - rank_pct(store[key][nz])
                    cols.append(v)
                    meta.append((r, s))

        # Permutation null: shuffle WITHIN the subset, so the null preserves
        # which nodes are in play and asks only whether the arrangement matters.
        rng = np.random.default_rng(args.seed)
        base = {r: cols[meta.index((r, 0))] for r in RADII if (r, 0) in meta}
        perm_meta = []
        idx_nz = np.flatnonzero(nz)
        for r, vec in base.items():
            sub = vec[nz]
            for p in range(args.perms):
                v = np.zeros(n)
                v[idx_nz] = sub[rng.permutation(len(sub))]
                cols.append(v)
                perm_meta.append(r)

        Z = np.column_stack(cols)
        Z[nz] -= Z[nz].mean(axis=0, keepdims=True)   # centre over the subset
        n_cells = len(meta)
        I, empty = morans_i(net.adj.astype(np.float32), Z, DMAX, args.batch,
                            keep=nz)

        null = {}
        for j, r in enumerate(perm_meta):
            null.setdefault(r, []).append(n_cells + j)
        for i, (r, s) in enumerate(meta):
            for d in range(1, DMAX + 1):
                obs = I[d - 1, i]
                nd = I[d - 1, null.get(r, [])]
                nd = nd[np.isfinite(nd)]
                p = ((np.sum(np.abs(nd) >= abs(obs)) + 1) / (len(nd) + 1)
                     if len(nd) else np.nan)
                rows.append({"network": tag, "radius": r, "seed": s, "lag": d,
                             "morans_I": obs, "p_perm": p,
                             "sig": bool(p < 0.05 / d) if p == p else False,
                             "n_used": int(nz.sum()) - int(empty[d - 1]),
                             "indicator_I1": float(I_ind[0, 0])})

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"\nWrote {args.out} ({len(df):,} rows)")

    print("\n" + "=" * 74)
    print("LAG-1 MORAN'S I on betweenness residuals, NONZERO SUBSET only")
    print("compare against the all-node figures in results_moran_correlogram")
    print("=" * 74)
    print(df[df.lag == 1].groupby(["network", "radius"]).morans_I
          .median().unstack("radius").round(4).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())

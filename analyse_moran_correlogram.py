"""
C6 / O1 - residual network autocorrelation, as a HOP-LAG CORRELOGRAM.

WHAT THIS MEASURES, AND WHY IT IS NOT A7
----------------------------------------
Every uncertainty figure in this project quantifies model-FITTING variability
(seed sd) or, since A7, Monte Carlo noise in the TARGET. Neither touches the
possibility that the residuals themselves are spatially structured: nodes with
overlapping neighbourhoods have overlapping features, so their errors may be
correlated. That effect would exist under noise-free ground truth, which is
exactly what makes it a separate question - and it is the standard reason
random k-fold CV is optimistically biased in the spatial-statistics literature.

THE WEIGHTING DECISION - A CORRELOGRAM, NOT A MATRIX *(Rachit, 2026-09-05)*
--------------------------------------------------------------------------
The obvious implementations are plain adjacency, or one fixed k-hop decay.
Both are refused here, and for a reason specific to this project rather than a
generic preference: **the premise under examination is that reach-of-structure
changes with r.** Any single fixed weights matrix chosen up front assumes an
answer to the question this analysis exists to measure.

So Moran's I is computed SEPARATELY AT EACH HOP-LAG d, each using the
"hollow" indicator matrix for that lag - weight 1 for pairs at distance
EXACTLY d, 0 otherwise - row-normalised. This is the standard spatial-statistics
correlogram (Legendre & Legendre, *Numerical Ecology*; reference implementations
`spdep::sp.correlogram` and `ncf::correlog`).

**Exactly-d, not cumulative and not decayed.** A cumulative (<= d) or a
continuously-decayed matrix mixes the lags together, and the shape across lags
is the only thing a correlogram is for. Lag d for a cell built at radius r runs
d = 1 .. 2r+1: far enough past the feature radius to see the correlation die
off, which is what the buffer radius below needs.

THE TWO READINGS THIS PRODUCES
------------------------------
  (a) BUFFER RADIUS - the smallest d at which I is indistinguishable from the
      permutation null, reported PER CELL rather than as one global number.
      That is the block size a graph-distance-blocked CV would need.
  (b) DOES CORRELATION LENGTH SCALE WITH r? If cells built at deeper r show
      correlation reaching further, the mechanism is FEATURE OVERLAP -
      overlapping r-balls, correlated residuals - which is expected, clean, and
      a CV footnote. If correlation length is flat and long-range regardless of
      r, the TARGET ITSELF is network-autocorrelated independently of feature
      construction, which is a claim about the phenomenon rather than about the
      protocol, and is the headline if it appears.

SIGNIFICANCE: PERMUTATION, NOT THE ANALYTIC VARIANCE
----------------------------------------------------
The classical closed-form variance of Moran's I is derived for near-regular
spatial contiguity. These degree distributions are heavy-tailed (facebook's
max degree is three orders above its median), which is exactly the regime where
that formula misbehaves. The null here is empirical: permute residuals across
nodes, recompute I, repeat.

MULTIPLICITY: PROGRESSIVE BONFERRONI
------------------------------------
Each cell yields up to 2r+1 tests. Because the lags are ORDERED - lag 1 is
tested first and interest decays outward - the correction is the progressive
(sequential) Bonferroni standard for correlograms: lag d is tested at alpha/d.
That is not BH; BH is for exchangeable hypotheses, and these are not. The
method is named in the output so a reader never has to infer it.

Usage:
    python analyse_moran_correlogram.py [--perms 199] [--batch 512]
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

import analyse
from analyse_betweenness_k import manifest_paths
from influence.preprocessing import load_edgelist

FULL = "node+edge+subgraph+dynamic"
TARGETS = ("spread_mean", "spread_cv", "spread_resid", "betweenness")
RADII = (0, 1, 2, 3)
SEEDS = range(10)
ALPHA = 0.05
MIN_SOURCES = 30   # see the graph-exhaustion guard in main()


def oof_store(tag: str, target: str) -> dict:
    """
    The stored OOF predictions for one target, from the arm this project
    REPORTS.

    betweenness comes from `estimators/cache_oof_<tag>__rf_log1p.npz`, not the
    top-level cache: §26b/§26d re-based betweenness onto the log1p objective and
    the top-level file is the superseded squared-error arm. Reading the wrong
    one here would compute residual structure for a configuration the project no
    longer reports, and the two are close enough in tau that nothing downstream
    would flag it.
    """
    path = (os.path.join("estimators", f"cache_oof_{tag}__rf_log1p.npz")
            if target == "betweenness" else f"cache_oof_{tag}.npz")
    if not os.path.exists(path):
        return {}
    with np.load(path) as z:
        return {k: z[k] for k in z.files
                if k.startswith(f"{target}|")}


def rank_pct(x: np.ndarray) -> np.ndarray:
    """Percentile ranks in [0, 1], ties averaged - the atlas's own convention."""
    from scipy.stats import rankdata
    return (rankdata(x) - 1) / (len(x) - 1)


def shell_masks(adj: sp.csr_matrix, srcs: np.ndarray, dmax: int):
    """
    Yield (d, mask) for d = 1..dmax, where mask[v, j] is True iff v is at
    distance EXACTLY d from source srcs[j].

    Multi-source BFS by sparse-dense frontier expansion, the same structure as
    `influence.targets.truncated_betweenness`. Reusing that shape rather than
    calling `features.bfs_shells` per node is deliberate: bfs_shells is
    single-source and returns Python lists of index arrays, which is the right
    interface for per-node feature extraction but would force an n-times Python
    loop here, for every lag, for every one of thousands of vectors. The
    membership computed is identical - shells at exact distance d - and the
    batched form is what makes the correlogram affordable at all.
    """
    n = adj.shape[0]
    b = len(srcs)
    frontier = np.zeros((n, b), dtype=bool)
    frontier[srcs, np.arange(b)] = True
    visited = frontier.copy()
    for d in range(1, dmax + 1):
        nxt = (adj @ frontier.astype(np.float32)) > 0
        nxt &= ~visited
        visited |= nxt
        yield d, nxt
        frontier = nxt


def morans_i(adj: sp.csr_matrix, Z: np.ndarray, dmax: int,
             batch: int,
             keep: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """
    Moran's I at every lag 1..dmax, for every column of Z at once.

    Z must already be column-centred. Returns (I, n_empty) with shapes
    (dmax, n_vectors) and (dmax,).

    ```math
    I_d = \\frac{n}{S_0}\\,
          \\frac{\\sum_i z_i \\, \\overline{z}_{\\,\\mathcal{S}_d(i)}}
                {\\sum_i z_i^2}
    ```

    where the inner term is the mean of z over i's exact-distance-d shell.

    S_0 is the number of nodes with a NON-EMPTY shell at that lag, which under
    row-normalisation is the sum of all weights. Nodes with an empty shell
    contribute nothing to the numerator and are excluded from S_0 - this is
    spdep's `zero.policy=TRUE` behaviour, and it matters here because at large d
    a substantial fraction of nodes have run out of graph. `n_empty` is returned
    so that a lag computed on a small remnant of the network can be spotted
    rather than read as a real signal.

    Cost is n^2 * n_vectors floating-point work per lag, done as BLAS dense
    products (mask.T @ Z) rather than as a sparse structure, because the
    exact-distance-d matrix is NOT sparse for d beyond 3 or 4 on these graphs -
    at d = 6 it is most of n^2, and materialising it would cost more memory than
    the product costs time.

    `keep`, when given, restricts the statistic to a SUBSET of nodes while
    leaving hop distances defined on the FULL graph. That distinction is the
    whole point of the parameter: the subset arm asks whether residual structure
    survives among nodes that share a property, and re-deriving distances inside
    an induced subgraph would silently change the question to one about the
    subgraph's own geometry. Rows outside `keep` are excluded as sources, dropped
    from every shell, and dropped from the denominator; the caller is responsible
    for having centred Z over the subset.
    """
    n, V = Z.shape
    if keep is not None:
        keep = np.asarray(keep, dtype=bool)
        assert keep.shape == (n,)
    num = np.zeros((dmax, V), dtype=np.float64)
    s0 = np.zeros(dmax, dtype=np.float64)
    empty = np.zeros(dmax, dtype=np.int64)
    Z32 = np.ascontiguousarray(Z, dtype=np.float32)

    n_eff = n if keep is None else int(keep.sum())
    for start in range(0, n, batch):
        srcs = np.arange(start, min(start + batch, n))
        if keep is not None:
            srcs = srcs[keep[srcs]]
            if not len(srcs):
                continue
        zsrc = Z[srcs, :]                                  # (b, V)
        for d, mask in shell_masks(adj, srcs, dmax):
            if keep is not None:
                mask = mask & keep[:, None]
            cnt = mask.sum(axis=0).astype(np.float64)      # (b,)
            ok = cnt > 0
            if not ok.any():
                empty[d - 1] += len(srcs)
                continue
            # (b, V) = shell sums, then row-normalised to shell MEANS.
            ssum = (mask.astype(np.float32).T @ Z32).astype(np.float64)
            lagmean = np.zeros_like(ssum)
            lagmean[ok] = ssum[ok] / cnt[ok, None]
            num[d - 1] += (zsrc[ok] * lagmean[ok]).sum(axis=0)
            s0[d - 1] += ok.sum()
            empty[d - 1] += int((~ok).sum())

    denom = ((Z if keep is None else Z[keep]) ** 2).sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        I = np.where(s0[:, None] > 0,
                     (n_eff / np.maximum(s0, 1))[:, None] * num / denom, np.nan)
    return I, empty


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=199,
                    help="permutation draws per (target, radius, lag) null")
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results_moran_correlogram.csv")
    ap.add_argument("--tags", default="", help="comma-separated subset, for timing runs")
    args = ap.parse_args()

    paths = manifest_paths()
    tags = [t for t in analyse.discover_networks() if t in paths]
    if args.tags:
        want = set(args.tags.split(","))
        tags = [t for t in tags if t in want]
    rows = []

    for tag in tags:
        t0 = time.time()
        net = load_edgelist(paths[tag], name=tag)
        truth = pd.read_csv(f"cache_targets_{tag}.csv")
        n = net.n
        print(f"\n=== {tag} (n={n:,}) ===", flush=True)

        # --------------------------------------------------------------- the
        # vector table. Columns are stacked so that ONE pass over the lag
        # structure serves every cell and every permutation draw; the lag pass
        # is the expensive part and it does not care how many columns it
        # carries.
        cols, meta = [], []
        for target in TARGETS:
            if target not in truth.columns:
                continue
            store = oof_store(tag, target)
            if not store:
                print(f"  {target}: no OOF arm on disk - skipped")
                continue
            y = truth[target].to_numpy(float)
            ypct = rank_pct(y)
            for r in RADII:
                for s in SEEDS:
                    key = f"{target}|{r}|{FULL}|{s}"
                    if key not in store:
                        continue
                    pred = store[key]
                    # RANK residual is primary. The targets are heavy-tailed
                    # (betweenness spans six orders); a raw residual would make
                    # Moran's I a statement about a handful of hubs rather than
                    # about the field. This also matches the convention Finding
                    # 8's failure atlas already uses, so the two are comparable.
                    cols.append(ypct - rank_pct(pred))
                    meta.append((target, r, s, "rank"))
                    # RAW residual, point estimate only, as a robustness note -
                    # the scale choice is a real modelling decision and printing
                    # only one of them would hide it.
                    cols.append(y - pred)
                    meta.append((target, r, s, "raw"))

        if not cols:
            print("  nothing to do")
            continue

        # Permutation columns. ONE null per (target, radius, lag) built from
        # that cell's SEED-0 residual, reused across the ten seeds.
        #
        # This is an approximation and it is stated rather than hidden. A
        # permutation null depends on the weights and on the residual MULTISET.
        # Moran's I is invariant to affine rescaling of that multiset - numerator
        # and denominator are both quadratic in the centred residual - so the
        # null does NOT depend on residual scale, only on distribution SHAPE.
        # Ten seeds of the same (target, radius) differ only by model-fitting
        # noise, so their shapes are near-identical. The alternative - a separate
        # null per seed - costs ten times as much for a null that would agree to
        # within its own Monte Carlo error. The across-seed spread of excess
        # kurtosis (the shape moment the null is actually sensitive to, not sd)
        # is printed below so the assumption is checkable rather than asserted.
        rng = np.random.default_rng(args.seed)
        perm_meta = []
        base = {}
        for (target, r, s, kind) in meta:
            if s == 0 and kind == "rank":
                base[(target, r)] = cols[meta.index((target, r, 0, "rank"))]
        for (target, r), vec in base.items():
            for p in range(args.perms):
                cols.append(vec[rng.permutation(n)])
                perm_meta.append((target, r, p))

        Z = np.column_stack(cols).astype(np.float64)
        Z -= Z.mean(axis=0, keepdims=True)
        n_cells = len(meta)

        from scipy.stats import kurtosis
        ks = pd.DataFrame([{"target": t, "radius": r,
                            "k": kurtosis(Z[:, i], fisher=True)}
                           for i, (t, r, s, k) in enumerate(meta) if k == "rank"])
        spread = (ks.groupby(["target", "radius"]).k
                  .agg(lambda v: v.max() - v.min()).max())
        print(f"  excess-kurtosis spread across seeds (max range): {spread:.4f} "
              f"- the seed-shared null assumes the residual SHAPE is stable",
              flush=True)

        dmax = min(7, 2 * max(RADII) + 1)
        print(f"  {Z.shape[1]:,} vectors ({n_cells} cells + "
              f"{len(perm_meta):,} permutations), lags 1..{dmax}", flush=True)

        adj = net.adj.astype(np.float32)
        I, empty = morans_i(adj, Z, dmax, args.batch)
        print(f"  lag pass: {time.time() - t0:.1f}s", flush=True)

        # ---------------------------------------------------------- assemble
        null = {}
        for j, (target, r, p) in enumerate(perm_meta):
            null.setdefault((target, r), []).append(n_cells + j)

        for i, (target, r, s, kind) in enumerate(meta):
            # Lags run to the COMMON ceiling, not to the spec's per-cell 2r+1.
            #
            # The spec sets the reported range at d = 1..2r+1 so that every cell
            # is probed past its own feature radius, and that rule is honoured -
            # it is recorded per row as `in_spec_range` and read-off (a) obeys it.
            # But at r=0 the rule admits exactly ONE lag, so a cell whose
            # correlation is still significant at lag 1 has no lag left to become
            # insignificant at, and its buffer is undefined by construction. That
            # would make read-off (b) - the comparison of correlation length
            # ACROSS r - a comparison of unequal probe ranges, which is precisely
            # the confound (b) exists to avoid.
            #
            # The lag pass already computed every lag to dmax for every column, so
            # extending the rows is free. (b) uses the common ceiling; (a) uses
            # the spec range. Both are labelled wherever they are reported.
            idx = null.get((target, r), [])
            for d in range(1, dmax + 1):
                obs = I[d - 1, i]
                nd = I[d - 1, idx] if idx else np.array([])
                nd = nd[np.isfinite(nd)]
                # Two-sided empirical p, with the +1 that keeps it from ever
                # being exactly zero (Davison & Hinkley) - reporting p = 0 from
                # 199 draws would overstate what 199 draws can show.
                p_emp = ((np.sum(np.abs(nd) >= abs(obs)) + 1) / (len(nd) + 1)
                         if len(nd) else np.nan)
                # THE GRAPH-EXHAUSTION GUARD, and it is not cosmetic.
                #
                # At large d most nodes have no shell left - on email-Eu-core
                # (effective diameter 2.9) lag 7 has 984 of 986 sources empty, so
                # I is computed from TWO nodes. Both the statistic and its null
                # then have enormous variance, p is close to 1, and the lag looks
                # "indistinguishable from the null". Reading a buffer radius off
                # that would report the point where the network RAN OUT, dressed
                # up as the point where correlation died. Those are different
                # facts and the second is the one being claimed.
                #
                # So a lag is only TESTABLE when at least 30 sources contribute.
                # Untestable lags are written to the CSV - suppressing them would
                # hide exactly the coverage story email exists to tell - but they
                # are excluded from the buffer-radius read-off downstream.
                n_used = n - int(empty[d - 1])
                rows.append({
                    "network": tag, "target": target, "radius": r, "seed": s,
                    "residual": kind, "lag": d, "morans_I": obs,
                    "in_spec_range": bool(d <= 2 * r + 1),
                    "p_perm": p_emp,
                    # PROGRESSIVE BONFERRONI: lag d tested at alpha/d. Named in
                    # the column so nobody has to reverse-engineer it.
                    "alpha_d": ALPHA / d,
                    "sig": bool(p_emp < ALPHA / d) if p_emp == p_emp else False,
                    "null_mean": float(nd.mean()) if len(nd) else np.nan,
                    "null_sd": float(nd.std(ddof=1)) if len(nd) > 1 else np.nan,
                    "n_empty_rows": int(empty[d - 1]), "n_used": n_used,
                    "testable": bool(n_used >= MIN_SOURCES),
                    "perms": len(nd), "correction": "progressive_bonferroni",
                })

    if not rows:
        print("\nNothing computed.")
        return 1
    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"\nWrote {args.out}  ({len(df):,} rows)")
    report(df)
    return 0


def buffer_radius(g: pd.DataFrame) -> float:
    """
    The smallest lag at which I is indistinguishable from the permutation null.

    Read on TESTABLE lags only (see the graph-exhaustion guard). NaN when every
    testable lag is still significant - which is an answer, not a failure: it
    says the correlation outlasts the range this cell can probe, and it must be
    reported as such rather than silently rounded to the last lag.
    """
    for _, row in g[g.testable].sort_values("lag").iterrows():
        if not row.sig:
            return float(row.lag)
    return np.nan


def report(df: pd.DataFrame) -> None:
    """Print the two read-offs the study doc needs, (a) then (b)."""
    d = df[df.residual == "rank"]

    # (a) BUFFER RADIUS, per (network, target, radius) cell. Deliberately not one
    #     global number: the whole point of the correlogram is that reach differs.
    #     Seeds are collapsed by MEDIAN, with the across-seed range printed beside
    #     it so a cell whose buffer is itself unstable is visible rather than
    #     averaged away.
    recs = []
    for (tag, tgt, r, s), g in d.groupby(["network", "target", "radius", "seed"]):
        recs.append({"network": tag, "target": tgt, "radius": r, "seed": s,
                     "buffer": buffer_radius(g[g.in_spec_range]),
                     "buffer_common": buffer_radius(g)})
    B = pd.DataFrame(recs)
    print("\n" + "=" * 78)
    print("(a) BUFFER RADIUS - smallest hop-lag indistinguishable from the "
          "permutation null")
    print("    spec range d <= 2r+1; progressive Bonferroni, lag d at alpha/d, "
          "alpha=0.05")
    print("    NaN = still significant at every testable lag in range")
    print("=" * 78)
    agg = (B.groupby(["network", "target", "radius"])
           .buffer.agg(median="median", lo="min", hi="max",
                       n_nan=lambda v: int(v.isna().sum())))
    print(agg.to_string())

    # (b) DOES CORRELATION LENGTH SCALE WITH r? The discriminating comparison,
    #     stated as the plan states it: if the buffer grows with r the mechanism
    #     is feature overlap (a CV footnote); if it is flat the target itself is
    #     autocorrelated independently of how features were built (the headline).
    print("\n" + "=" * 78)
    print("(b) DOES CORRELATION LENGTH SCALE WITH r?")
    print("    buffer at r=3 minus buffer at r=0, per (network, target).")
    print("    positive => deeper features reach further => FEATURE OVERLAP")
    print("    ~zero    => reach is a property of the TARGET, not the features")
    print("    computed on the COMMON lag ceiling, so every r is probed equally")
    print("=" * 78)
    aggc = B.groupby(["network", "target", "radius"]).buffer_common.median()
    piv = aggc.unstack("radius")
    piv["delta_r3_r0"] = piv.get(3) - piv.get(0)
    print(piv.to_string())
    fin = piv["delta_r3_r0"].dropna()
    if len(fin):
        print(f"\n    cells with a finite delta: {len(fin)} of {len(piv)}")
        print(f"    grew (>0): {int((fin > 0).sum())}   "
              f"flat (==0): {int((fin == 0).sum())}   "
              f"shrank (<0): {int((fin < 0).sum())}")

    # Lag-1 strength, because a buffer radius means nothing if there was no
    # autocorrelation to begin with. A cell with buffer 1 and I_1 ~ 0 is not a
    # "short correlation length", it is an absence of signal, and the two would
    # be indistinguishable in the table above.
    print("\n" + "=" * 78)
    print("Lag-1 Moran's I (median over seeds) - is there anything to buffer?")
    print("=" * 78)
    l1 = (d[d.lag == 1].groupby(["network", "target", "radius"])
          .morans_I.median().unstack("radius").round(4))
    print(l1.to_string())

    # The raw-residual arm, one line, as the robustness note it is.
    raw = df[df.residual == "raw"]
    if len(raw):
        m = (raw[raw.lag == 1].groupby(["network", "target"]).morans_I.median())
        print("\nRaw-residual arm, lag-1 median I (rank arm is primary):")
        print(m.round(4).to_string())


if __name__ == "__main__":
    sys.exit(main())

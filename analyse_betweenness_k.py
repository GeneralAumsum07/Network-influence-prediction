"""
C5 - `betweenness_k` as a zero-training local baseline for the radius protocol.

WHY THIS SCRIPT EXISTS
----------------------
M2 of the technical review: this project has run ZERO published methods, in a
field with at least six comparable systems since 2019. Every "the model needs
radius r" statement is therefore a statement about our model with nothing
beside it.

`betweenness_k` - ordinary betweenness restricted to source-target pairs at
distance <= k, from Appendix A.4 of arXiv 2601.16236 - is the cheapest real
answer available, and it is a better answer than its cost suggests, for one
reason: **it is a radius-k local rule by construction** (proof in
`influence/targets.py::truncated_betweenness`). It therefore drops into the
existing radius protocol at MATCHED r, with no training, no features, no seeds
and no hyperparameters. A 171-feature random forest at radius r versus a closed
form that sees the same ball is the comparison the locality claim has always
needed and has never had.

WHAT IS BEING ASKED, PRECISELY
------------------------------
Not "is the model good". The model is trained on the target; b_k is not, and a
trained model beating an untrained formula is not news. The question is about
the RADIUS AXIS:

  Does the model's advantage at radius r come from learning, or is most of the
  r-ball's information already extractable by a formula anyone could write down
  in 2026 without fitting anything?

Both outcomes are reportable and the project's own culture forbids burying
either. Beating b_k at matched r is the cleanest "value of learning" result the
corpus can produce. Failing to beat it is a finding about the feature
vocabulary, and it would have to be published as one.

WHAT IS NOT CLAIMED
-------------------
b_k is NOT a published *learned* method and running it does not discharge M2.
DrBC, ABCDE, BRAVA-GNN and 1D-CGS remain unrun (Part D1). This closes the
"no external comparison point of any kind" gap, not the baselines gap.

Usage:
    python analyse_betweenness_k.py [--kmax 6] [--batch 128]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

import analyse
from analyse_betweenness import boundary_share
from influence.experiment import precision_at_k
from influence.preprocessing import load_edgelist
from influence.targets import exact_betweenness, truncated_betweenness

FULL = "node+edge+subgraph+dynamic"


def manifest_paths() -> dict:
    """
    tag -> edge-list path, from data/manifest.json.

    Read from the manifest rather than globbed from data/ because the manifest
    is the file that carries the sha256 the rest of the project verifies
    against; picking up a stray edge list with a matching name would rebuild a
    DIFFERENT graph from the one the cache was built on, and the canary below
    would then fail for a reason nobody could diagnose.
    """
    with open(os.path.join("data", "manifest.json")) as fh:
        entries = json.load(fh)
    return {e["name"]: e["path"].replace("\\", os.sep) for e in entries}


def rebuild(tag: str, path: str):
    """
    Rebuild the Network, and refuse to continue unless it is THE graph the
    cached targets were computed on.

    This canary is doing real work, not ceremony. `truncated_betweenness`
    returns an array indexed by the internal node id assigned during
    `build_network`; every comparison below joins it to `cache_targets_*.csv`
    positionally. If the preprocessing ever reordered nodes - a different
    largest-connected-component tie-break, a changed relabelling - every tau in
    this script would be computed against a permuted truth column and would
    come out near zero, which reads as "the baseline is weak" rather than as
    "the join is broken". Comparing full betweenness against the cached column
    catches that in one line.
    """
    net = load_edgelist(path, name=tag)
    cached = pd.read_csv(f"cache_targets_{tag}.csv")["betweenness"].to_numpy(float)
    if net.n != len(cached):
        raise AssertionError(
            f"{tag}: rebuilt graph has {net.n} nodes, cache has {len(cached)}. "
            f"The cache was not built from {path}.")

    full = exact_betweenness(net)
    scale = max(1.0, float(np.abs(cached).max()))
    gap = float(np.abs(full - cached).max()) / scale
    if gap > 1e-9:
        raise AssertionError(
            f"{tag}: recomputed exact betweenness disagrees with "
            f"cache_targets_{tag}.csv by {gap:.3e} (relative). Either the node "
            f"ordering has drifted or the cache is from a different graph; "
            f"joining b_k to that column positionally would be meaningless.")
    return net, cached, full


def score(true: np.ndarray, pred: np.ndarray) -> dict:
    """
    The project's reporting metrics, on the axes `analyse.py` already uses.

    `rmse` is deliberately omitted: b_k is on a different scale from full
    betweenness (it counts fewer pairs), so an error norm would measure the
    truncation's scale offset rather than its ranking quality, and would look
    catastrophic while saying nothing. Every metric here is rank-based or
    set-based and therefore scale-free.
    """
    n = len(true)
    return {
        "kendall_tau": float(kendalltau(true, pred).statistic),
        "spearman": float(spearmanr(true, pred).statistic),
        "precision_at_1pct": precision_at_k(true, pred, max(1, n // 100)),
        "precision_at_5pct": precision_at_k(true, pred, max(1, n // 20)),
    }


def model_curve(tag: str) -> pd.DataFrame:
    """
    The ML model's betweenness row at the richest tier, per radius, with its
    seed spread.

    Goes through `analyse.load`, which applies the log1p-objective splice for
    betweenness (§ THE REPORTED OBJECTIVE). Using the raw sweep here would
    silently compare b_k against a configuration the project has already
    corrected and no longer reports.
    """
    d = analyse.load(tag)
    d = d[(d.target == "betweenness") & (d.richness == FULL)]
    g = d.groupby("radius").agg(
        tau_model=("kendall_tau", "mean"),
        tau_model_sd=("kendall_tau", "std"),
        p5_model=("precision_at_5pct", "mean"),
        seeds=("kendall_tau", "size"),
    ).reset_index()
    return g


def model_nonzero_tau(tag: str, nz: np.ndarray, true: np.ndarray) -> dict:
    """
    The model's tau on the nonzero-nonzero pairs, per radius, from the REPORTED
    betweenness arm's stored OOF predictions.

    Two things make the file choice non-obvious and both are load-bearing:

    - It must be `estimators/cache_oof_<tag>__rf_log1p.npz`, not
      `cache_oof_<tag>.npz`. The project reports betweenness from the log1p
      objective (analyse.REPORTED_BETWEENNESS); the top-level cache is the
      superseded squared-error arm. tau over ALL nodes happens to be nearly the
      same either way, which is precisely what would let the wrong file pass
      unnoticed.
    - The subset must be taken on the TRUE zero set, not on nodes the model
      predicted as zero. §24.5's whole point is that the zero set is known
      exactly at radius 1; conditioning on a prediction would smuggle the
      model's own errors into the definition of the harder subproblem.

    Returns radius -> mean tau over seeds, or {} if the arm is not on disk.
    """
    path = os.path.join("estimators", f"cache_oof_{tag}__rf_log1p.npz")
    if not os.path.exists(path):
        return {}
    out = {}
    with np.load(path) as z:
        keys = set(z.files)
        for r in (0, 1, 2, 3):
            taus = [kendalltau(true[nz], z[k][nz]).statistic
                    for s in range(10)
                    if (k := f"betweenness|{r}|{FULL}|{s}") in keys]
            if taus:
                out[r] = (float(np.mean(taus)), float(np.std(taus, ddof=1)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kmax", type=int, default=6,
                    help="largest k to compute (default 6; the project's own "
                         "radius protocol stops at 3, but 2601.16236 uses 6 "
                         "and 10, and the trajectory past r=3 is what shows "
                         "whether b_k is still climbing)")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--out", default="results_betweenness_k.csv")
    args = ap.parse_args()

    paths = manifest_paths()
    tags = [t for t in analyse.discover_networks() if t in paths]
    if not tags:
        print("No networks discovered - run from the project root.")
        return 1

    rows = []
    for tag in tags:
        print(f"\n=== {tag} ===", flush=True)
        net, cached, full = rebuild(tag, paths[tag])
        B = boundary_share(cached)
        nz = cached > 0
        print(f"  n={net.n:,}  m={net.m:,}  zero fraction z={B['nz']/B['n']:.4f}  "
              f"tau floor={B['tau_floor']:.4f}", flush=True)
        print(f"  canary: recomputed exact betweenness matches "
              f"cache_targets_{tag}.csv", flush=True)

        for k in range(1, args.kmax + 1):
            t0 = time.time()
            bk = truncated_betweenness(net, k, batch=args.batch)
            secs = time.time() - t0

            # Degenerate by definition, not by accident - see the docstring of
            # truncated_betweenness. kendalltau of a constant vector is nan, so
            # this is special-cased rather than left to produce a silent nan
            # that a reader would mistake for a failed computation.
            if not np.any(bk > 0):
                m = {"kendall_tau": 0.0, "spearman": 0.0,
                     "precision_at_1pct": np.nan, "precision_at_5pct": np.nan}
                m_nz = dict(m)
            else:
                m = score(cached, bk)
                # D2's metric: the same score with the radius-1-decidable zero
                # set removed, so b_k is not credited for the part of tau that
                # is free (§24.5). Reported for the baseline for exactly the
                # reason the project demands it of everyone else.
                m_nz = (score(cached[nz], bk[nz]) if nz.sum() > 2 else
                        {kk: np.nan for kk in m})

            rows.append({
                "network": tag, "k": k,
                **{f"{kk}": vv for kk, vv in m.items()},
                **{f"{kk}_nonzero": vv for kk, vv in m_nz.items()},
                "n_nonzero_bk": int((bk > 0).sum()),
                "seconds": secs, "n": net.n,
            })
            print(f"  b_{k}: tau={m['kendall_tau']:+.4f}  "
                  f"tau(nonzero)={m_nz['kendall_tau']:+.4f}  "
                  f"p@5%={m['precision_at_5pct'] if m['precision_at_5pct'] == m['precision_at_5pct'] else float('nan'):.3f}  "
                  f"({secs:.1f}s)", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"\nWrote {args.out}  ({len(df)} rows)")

    # ------------------------------------------------------------------ the
    # comparison the script exists for: MATCHED RADIUS.
    #
    # b_k sees the k-ball; the model at radius r sees the r-ball. Lining them
    # up at k == r is the only comparison that isolates learning from reach.
    # Any other pairing lets one side see further than the other and answers a
    # different question.
    print("\n" + "=" * 78)
    print("MATCHED RADIUS: 171-feature random forest vs a closed form, same ball")
    print("=" * 78)
    for tag in tags:
        mc = model_curve(tag)
        sub = df[df.network == tag].set_index("k")
        print(f"\n{tag}")
        print(f"  {'r':>2} {'model tau':>12} {'sd':>8} {'b_r tau':>10} "
              f"{'model - b_r':>12}   verdict")
        for _, row in mc.iterrows():
            r = int(row.radius)
            if r not in sub.index:
                continue
            bt = sub.loc[r, "kendall_tau"]
            gap = row.tau_model - bt
            sd = row.tau_model_sd
            # "beats" is judged against the model's own seed spread, the same
            # 2-sd rule the sweep uses to award a star. A gap smaller than that
            # is not a win, and calling it one here would be exactly the
            # multiplicity sloppiness A4 was written to stop.
            verdict = ("model wins" if gap > 2 * sd else
                       "b_k wins" if gap < -2 * sd else
                       "TIE (within 2 seed sd)")
            print(f"  {r:>2} {row.tau_model:>12.4f} {sd:>8.5f} {bt:>10.4f} "
                  f"{gap:>+12.4f}   {verdict}")

    # ------------------------------------------------------------- and again
    # on D2's own metric. This project's C4 proposes that every learned-
    # betweenness paper report tau on the nonzero-nonzero pairs. Judging our
    # baseline comparison on the all-node number while demanding the subset
    # number of everyone else would be indefensible, so both are printed.
    print("\n" + "=" * 78)
    print("THE SAME COMPARISON ON D2's METRIC: tau over nonzero-nonzero pairs")
    print("=" * 78)
    print("(the radius-1-decidable zero set removed from BOTH sides, so neither")
    print(" is credited for the part of tau that is free - see study_doc 24.5)")
    for tag in tags:
        cached = pd.read_csv(f"cache_targets_{tag}.csv")["betweenness"].to_numpy(float)
        nz = cached > 0
        mz = model_nonzero_tau(tag, nz, cached)
        if not mz:
            print(f"\n{tag}: no estimators/cache_oof_{tag}__rf_log1p.npz - skipped")
            continue
        sub = df[df.network == tag].set_index("k")
        print(f"\n{tag}   (nonzero nodes: {int(nz.sum()):,} of {len(nz):,})")
        print(f"  {'r':>2} {'model tau_nz':>13} {'sd':>8} {'b_r tau_nz':>12} "
              f"{'model - b_r':>12}   verdict")
        for r in sorted(mz):
            if r not in sub.index:
                continue
            mt, msd = mz[r]
            bt = sub.loc[r, "kendall_tau_nonzero"]
            gap = mt - bt
            verdict = ("model wins" if gap > 2 * msd else
                       "b_k wins" if gap < -2 * msd else
                       "TIE (within 2 seed sd)")
            print(f"  {r:>2} {mt:>13.4f} {msd:>8.5f} {bt:>12.4f} "
                  f"{gap:>+12.4f}   {verdict}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

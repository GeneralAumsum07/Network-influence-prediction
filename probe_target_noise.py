"""
A7 / N6 - the target-noise bootstrap.

THE QUESTION
------------
Every error bar this project reports is a SEED sd: refit the same cell with ten
different random_state values, take the spread of tau. That quantifies
model-fitting variability and nothing else.

There is a second noise source it cannot see. The percolation shortcut draws
4,000 live-edge samples ONCE and evaluates every seed node on that same set.
`spread_mean(v)` is therefore a Monte Carlo estimate, and - this is the part
that matters - the estimates for different v are NOT independent, because they
share the samples. Positive covariance across nodes means the effective sample
size behind the target column is far below 4,000, and no amount of refitting
the model reveals it: the target is held fixed across all ten seeds.

So the reported tau carries an uncertainty the reported error bar does not
describe. This script measures it.

WHY THE BOOTSTRAP UNIT IS THE COLUMN, NOT THE NODE
--------------------------------------------------
The independent replicate in this design is the live-edge sample, not the node.
Resampling nodes would answer "how much does tau depend on which nodes are in
the graph", which is a different question and one with no clean answer here (the
graph is the population, not a sample from one). Resampling the 4,000 sample
indices with replacement reproduces exactly the sampling process that produced
the target column, and - because the same resampled index set is applied to
every node's row simultaneously - it preserves the cross-node covariance that
is the whole reason this noise source is not negligible.

WHAT IS HELD FIXED, AND THE LIMITATION THAT CREATES
---------------------------------------------------
The model is FROZEN. Each replicate perturbs the target column and re-scores the
existing out-of-fold predictions against it; nothing is refit. That isolates the
effect of target noise on the SCORE.

This is NOT cleanly a lower bound, and an earlier draft of this comment claimed
it was. The sign of the bias is genuinely ambiguous, and both directions are
real:

  - It omits a channel, which pushes the figure DOWN. A different target column
    would also have trained a different model, and that path is not measured.

  - It scores a model against a realisation it was not fitted to, which pushes
    the figure UP. The predictions are out-of-fold, so no node's own target
    leaked into its own prediction - but every OTHER node's target did, and all
    of those share the same 4,000 live-edge samples. Realisation A's noise is
    therefore baked into the fitted model, and re-scoring it against replicate B
    charges tau for that mismatch on top of the target noise itself.

Which channel wins cannot be settled by this script; it needs one cell re-fit
per replicate, with the model allowed to adapt to each perturbed target. Until
that is run, the number below is "the movement in tau when the target is
resampled and the model is not allowed to react", which is a well-defined
quantity and the honest way to describe it - not a bound in either direction.

WHY BETWEENNESS IS EXCLUDED
---------------------------
`betweenness` is computed exactly, by Brandes, on the whole graph. It has no
Monte Carlo noise whatsoever. Running it through this bootstrap would produce a
column of identical taus and a target-noise sd of exactly zero, which reads like
a bug rather than a fact about the estimator. It is excluded here and the reason
is stated in the output, which is more informative than a row of zeros.

Usage:
    python probe_target_noise.py [--reps 200] [--tier <tier>] [--out FILE]
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from analyse import discover_networks
from influence.targets import variance_residual

# The three targets that are Monte Carlo estimates. `spread_ignition` and
# `spread_std` are not swept, so they are not here; `betweenness` is exact - see
# the module docstring.
MC_TARGETS = ("spread_mean", "spread_cv", "spread_resid")

# The richest rung. A7 is an appendix result about the noise floor, not a
# richness study, so it is quoted at one tier rather than all four; the richest
# is the one the headline numbers are reported at.
DEFAULT_TIER = "node+edge+subgraph+dynamic"


def targets_from_cascades(c: np.ndarray) -> dict:
    """
    Rebuild the Monte Carlo target columns from a cascade matrix.

    `c` is (n_nodes, n_samples) - spread size for each seed under each live-edge
    sample. This mirrors influence/targets.py::build_targets exactly; if that
    function's definitions ever change, this one has to follow, and the
    self-check in main() against the published cache_targets_*.csv is what will
    catch the drift.

    The subtlety is `spread_resid`. variance_residual bins nodes on their mean
    and subtracts a within-bin median, so it is a function of the WHOLE column,
    not of one node. It must therefore be recomputed inside every replicate from
    that replicate's own mean and std. Reusing the published residual - or
    applying the published bin edges - would hold most of the noise constant and
    report a target-noise figure far smaller than the truth.
    """
    mean = c.mean(axis=1)
    std = c.std(axis=1, ddof=1)

    # Guard the ratio the same way the pipeline's CascadeResults.cv does: a seed
    # whose mean is zero cannot happen here (a seed always infects itself, so
    # spread >= 1), but the guard costs nothing and documents the assumption.
    cv = np.divide(std, mean, out=np.zeros_like(std), where=mean > 0)

    return {"spread_mean": mean,
            "spread_cv": cv,
            "spread_resid": variance_residual(mean, std)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=200,
                    help="bootstrap replicates (default 200)")
    ap.add_argument("--tier", default=DEFAULT_TIER)
    ap.add_argument("--seed", type=int, default=0,
                    help="RNG seed for the resampling itself")
    ap.add_argument("--pred-seed", type=int, default=0,
                    help="which sweep seed's OOF predictions to freeze")
    ap.add_argument("--out", default="results_target_noise.csv")
    args = ap.parse_args()

    tags = discover_networks()
    if not tags:
        print("No networks discovered - run from the project root.")
        return 1

    rows = []
    for tag in tags:
        casc_f = f"cache_cascades_{tag}.npy"
        oof_f = f"cache_oof_{tag}.npz"
        targ_f = f"cache_targets_{tag}.csv"
        missing = [f for f in (casc_f, oof_f, targ_f) if not os.path.exists(f)]
        if missing:
            print(f"{tag}: SKIP (missing {', '.join(missing)})")
            continue

        print(f"\n=== {tag} ===")
        c = np.load(casc_f)                      # (n_nodes, n_samples)
        n_nodes, n_samples = c.shape
        published = pd.read_csv(targ_f)
        oof = np.load(oof_f)

        # SELF-CHECK, and it is not decorative. This script re-derives the
        # target columns from the cascade matrix rather than reading them. If
        # that derivation disagrees with the file the sweep actually trained
        # against, every bootstrap number below is measuring the wrong quantity.
        # Raise, do not warn - a silent mismatch here would produce plausible
        # figures attached to the wrong target.
        rebuilt = targets_from_cascades(c)
        for t in MC_TARGETS:
            gap = float(np.max(np.abs(rebuilt[t] - published[t].to_numpy(float))))
            if gap > 1e-9:
                raise AssertionError(
                    f"{tag}/{t}: rebuilding the target from "
                    f"{casc_f} disagrees with {targ_f} by {gap:.3e}. "
                    f"targets_from_cascades() has drifted from "
                    f"influence/targets.py::build_targets, so the bootstrap "
                    f"below would perturb a column the sweep never used."
                )
        print(f"  self-check: 3/3 targets rebuilt from cascades exactly "
              f"(n={n_nodes}, samples={n_samples})")

        # Draw the replicate index sets ONCE and share them across every target
        # and radius. Two reasons: it is far cheaper (the expensive step is
        # rebuilding the target columns, which is done once per replicate rather
        # than once per cell), and it means the target-noise figures for
        # different cells are driven by the same perturbations, so they can be
        # compared to each other rather than only to their own baselines.
        rng = np.random.default_rng(args.seed)
        idx_sets = [rng.integers(0, n_samples, size=n_samples)
                    for _ in range(args.reps)]

        print(f"  bootstrapping {args.reps} replicates over sample indices...")
        boot_targets = []
        for r, idx in enumerate(idx_sets):
            boot_targets.append(targets_from_cascades(c[:, idx]))
            if (r + 1) % 50 == 0:
                print(f"    {r + 1}/{args.reps}")

        for target in MC_TARGETS:
            y_pub = published[target].to_numpy(float)
            for radius in (0, 1, 2, 3):
                key = f"{target}|{radius}|{args.tier}|{args.pred_seed}"
                if key not in oof:
                    continue
                pred = oof[key]

                # Seed noise: the target is fixed, the model varies. This
                # reproduces the project's existing error bar, which doubles as
                # a check that this script is reading the right cells.
                seed_taus = []
                for s in range(10):
                    k = f"{target}|{radius}|{args.tier}|{s}"
                    if k in oof:
                        seed_taus.append(kendalltau(y_pub, oof[k]).statistic)
                seed_sd = float(np.std(seed_taus, ddof=1)) if len(seed_taus) > 1 else np.nan

                # Target noise: the model is fixed, the target varies.
                boot_taus = np.array([kendalltau(bt[target], pred).statistic
                                      for bt in boot_targets], dtype=float)
                lo, hi = np.percentile(boot_taus, [2.5, 97.5])

                rows.append({
                    "network": tag, "target": target, "radius": radius,
                    "tier": args.tier,
                    "tau_published": float(kendalltau(y_pub, pred).statistic),
                    "target_noise_sd": float(boot_taus.std(ddof=1)),
                    "target_ci_lo": float(lo), "target_ci_hi": float(hi),
                    "seed_sd": seed_sd,
                    "ratio_seed_over_target": (
                        float(seed_sd / boot_taus.std(ddof=1))
                        if boot_taus.std(ddof=1) > 0 else np.inf),
                    "reps": args.reps, "n_samples": n_samples,
                })
                print(f"  {target:<13} r={radius}  tau={rows[-1]['tau_published']:.4f}  "
                      f"target sd={rows[-1]['target_noise_sd']:.5f}  "
                      f"seed sd={seed_sd:.5f}  "
                      f"ratio={rows[-1]['ratio_seed_over_target']:.1f}x")

        del c, boot_targets

    if not rows:
        print("\nNo cells scored.")
        return 1

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"\nWrote {args.out}  ({len(df)} cells)")

    # The headline the appendix needs, stated as a comparison rather than as two
    # separate numbers the reader has to divide themselves.
    print("\n--- summary: how much bigger is seed noise than target noise? ---")
    print(df.groupby("target")["ratio_seed_over_target"]
            .describe()[["min", "50%", "max"]].round(2).to_string())
    worse = df[df.ratio_seed_over_target < 1]
    if len(worse):
        print(f"\n{len(worse)} cells where TARGET noise exceeds seed noise:")
        print(worse[["network", "target", "radius", "target_noise_sd",
                     "seed_sd"]].to_string(index=False))
    else:
        print("\nNo cell has target noise exceeding seed noise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

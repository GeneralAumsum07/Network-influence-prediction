"""
Does r*(eps) move when the training objective is corrected?

WHY THIS EXISTS
---------------
Finding 11 established that every fit in this project minimises squared error
while every score is Kendall tau, and that on betweenness (skew 28.88) closing
that gap is worth +0.18 tau - more than any feature tier. HANDOFF.md section 13
then records an explicit TBC:

    "does r*(eps) for betweenness change under a log1p training objective?
     Nobody knows. Do not guess it in a write-up."

This script answers exactly that question and nothing else. It is deliberately
NOT a corpus re-sweep: the decision to re-base the published numbers is open and
is Rachit's, and this probe is meant to INFORM that decision rather than pre-empt
it. It writes to `results/`, touches no `sweep_*.csv`, and changes no default.

WHY BOTH ARMS ARE RECOMPUTED HERE
---------------------------------
The raw-objective numbers already exist in `sweep_<tag>.csv`, so the cheap
version of this probe would compute only the log1p arm and difference it against
the published one. That would be a confound: any difference in fold
construction, estimator hyperparameters or column ordering between this script
and `stage2_sweep.py` would land in the measured effect and be indistinguishable
from it. This project has been bitten twice this week by exactly that class of
error - a benchmark that varied the library and the device together, and an
estimator comparison that varied the leaf floor and the inductive bias together.

So both arms go through the SAME call, `out_of_fold_predictions`, with the same
folds and the same estimator, and the only thing that differs between them is
the transform applied to the training target. The raw arm is then checked
against the published sweep as a free correctness test on the harness - if it
does not reproduce, this script is wrong and its log1p arm is worthless.

WHY THE SPREADING CONTROL IS NOT OPTIONAL
-----------------------------------------
`spread_mean` is far less skewed than betweenness. If the transform moved
horizons on BOTH targets, the honest reading would be "the transform perturbs
r*" - a fact about the intervention rather than about the objective mismatch. It
is only evidence about the mismatch if the effect tracks the skew. The control
is what makes the betweenness result interpretable either way.

TAU IS ALWAYS SCORED AGAINST THE ORIGINAL TARGET
------------------------------------------------
Kendall tau is invariant to monotone transforms of the ground truth, so training
on log1p(y) while scoring against the untransformed y changes what the model
optimises and not what it is judged against. That is the whole reason this is a
better-conditioned objective rather than a relaxed metric, and it is enforced
below by never letting the transformed target reach `kendalltau`.
"""
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, skew

from analyse import FULL, r_star_per_seed, seed_matrix
from influence.experiment import out_of_fold_predictions
from influence.features import select_features

NETS = ["ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined",
        "p2p-Gnutella08"]
# betweenness is the contaminated target; spread_mean is the low-skew control.
TARGETS = ["betweenness", "spread_mean"]
RADII = [0, 1, 2, 3]
SEEDS = range(10)                       # the project's convention; r* stability
                                        # across seeds is itself a reported result
EPS = [0.20, 0.10, 0.05, 0.02, 0.01]    # the published tolerance ladder

# The two objectives. Identical in every other respect - same folds, same
# estimator, same columns, same seed.
OBJECTIVES = {
    "raw": lambda v: v,
    "log1p": np.log1p,
}

# The tier ladder entry for FULL. r*(eps) is read off the richest STRUCTURAL
# tier, which is what `analyse.py` uses, so only this one rung is needed.
TIERS_FULL = ["node", "edge", "subgraph"]

OUT = "results/objective_horizon_probe.csv"


def run_network(tag: str) -> pd.DataFrame:
    """Every (target, radius, seed, objective) cell for one network."""
    X = pd.read_csv(f"cache_features_{tag}.csv")
    Y = pd.read_csv(f"cache_targets_{tag}.csv")
    reg = pd.read_csv(f"cache_registry_{tag}.csv")

    rows = []
    for target in TARGETS:
        y = Y[target].to_numpy(np.float64)
        sk = skew(y)
        for r in RADII:
            cols = select_features(X, reg, max_hop=r, tiers=TIERS_FULL)
            Xm = X[cols].to_numpy(np.float64)
            for name, tf in OBJECTIVES.items():
                yt = tf(y)
                for seed in SEEDS:
                    # estimator=None keeps the ORIGINAL inline forest, which is
                    # what produced every published number - see the long note
                    # in out_of_fold_predictions. Using the registry here would
                    # silently change the instrument.
                    p = out_of_fold_predictions(Xm, yt, seed=seed,
                                                estimator=None)
                    # Scored against the UNTRANSFORMED target, always.
                    rows.append({
                        "network": tag, "target": target, "radius": r,
                        "richness": FULL, "seed": seed, "objective": name,
                        "kendall_tau": kendalltau(y, p).statistic,
                        "n_features": len(cols), "target_skew": sk,
                    })
    return pd.DataFrame(rows)


def main():
    frames = []
    for tag in NETS:
        t0 = time.time()
        f = run_network(tag)
        frames.append(f)
        print(f"  {tag:<20s} {len(f):4d} cells  {time.time() - t0:7.1f}s",
              flush=True)
    d = pd.concat(frames, ignore_index=True)
    d.to_csv(OUT, index=False)
    print(f"\nwrote {OUT}  ({len(d)} rows)")


if __name__ == "__main__":
    sys.exit(main())

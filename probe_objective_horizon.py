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
import os
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


def write_atomic(d: pd.DataFrame) -> None:
    """Write OUT via a sibling temp file and one rename (see main()'s flush).

    os.replace is a single MoveFileEx(REPLACE_EXISTING) on Windows and rename(2)
    on POSIX, so a reader - or a resume after a hard cut - sees the old file or
    the new one, never a mixture. The temp file sits next to OUT so the rename
    never crosses a volume, which would silently become a copy.
    """
    tmp = OUT + ".tmp"
    d.to_csv(tmp, index=False)
    os.replace(tmp, OUT)


def run_network(tag: str, done: set, flush=None) -> list:
    """Every (target, radius, seed, objective) cell for one network.

    Cells whose key (network, target, radius, objective, seed) is in `done` are
    skipped - they are already on disk from an interrupted run. `flush` is
    called with the rows finished so far after each (target, radius) block; see
    the note on main()'s flush for why. Returns only the NEW rows.
    """
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
                    # Resume. Each cell is a pure function of (data, columns,
                    # transform, seed) - out_of_fold_predictions seeds its own
                    # folds and forest - so a skipped cell's on-disk value is
                    # the value this loop would have recomputed, and skipping
                    # it cannot change any other cell.
                    if (tag, target, r, name, seed) in done:
                        continue
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
            # One (target, radius) block - both objectives x all seeds - done.
            if flush is not None:
                flush(rows)
    return rows


def main():
    # Resume on the CSV. Until 2026-10-07 this probe held every row in memory
    # and wrote once at the very end, so an interruption at fit 790 of 800 lost
    # all 800. That happened twice on 2026-10-07 (08:53 a closed console window;
    # 09:32 stopped deliberately because the laptop was on battery), each time
    # discarding up to two hours of fits.
    done, frames = set(), []
    if os.path.exists(OUT):
        # round_trip: the default C parser can be 1 ulp off on re-read, and these
        # rows are written back out on every flush. The raw arm is checked for
        # reproduction against the published sweep, so carried-over values must
        # be bit-for-bit what the fit produced. Same choice as
        # probe_structural_target_noise_refit.py and analyse_buffered_cv.py.
        prev = pd.read_csv(OUT, float_precision="round_trip")
        frames.append(prev)
        done = set(zip(prev.network, prev.target, prev.radius,
                       prev.objective, prev.seed))
        print(f"resuming: {len(done)} cells already done", flush=True)

    for tag in NETS:
        t0 = time.time()

        def flush(rows_so_far, _frames=frames):
            """
            Checkpoint after every (target, radius) block, not once at the end.

            THE HOST HARD-CUTS UNDER SUSTAINED LOAD - see HANDOFF.md section 12
            - and the queue can be stopped or killed from outside. A block is 20
            fits (2 objectives x 10 seeds), a few minutes, so that is the most an
            interruption can now cost. probe_sample_efficiency.py checkpoints at
            the same granularity for the same reason.

            The whole file is rewritten each time (earlier networks + this
            network's rows so far) into a temporary file that then replaces OUT
            in one rename. A cut mid-write therefore leaves either the previous
            checkpoint or the new one, never a truncated row - a half-written
            last line would otherwise parse as a row with NaN tau and be
            "done" forever. This changes WHEN the file is written and nothing
            about what is in it: same columns, same row order as an
            uninterrupted run, because blocks are always finished in loop order.

            `_frames` is bound as a default argument rather than closed over so
            the callback keeps working if the loop variable is ever rebound.
            """
            if rows_so_far:
                write_atomic(pd.concat(_frames + [pd.DataFrame(rows_so_far)],
                                       ignore_index=True))

        rows = run_network(tag, done, flush)
        if rows:
            frames.append(pd.DataFrame(rows))
        print(f"  {tag:<20s} {len(rows):4d} new cells  "
              f"{time.time() - t0:7.1f}s", flush=True)
    d = pd.concat(frames, ignore_index=True)
    # The final write is a no-op in content (the last flush already wrote these
    # rows) but keeps the old guarantee that a completed run always leaves OUT.
    write_atomic(d)
    print(f"\nwrote {OUT}  ({len(d)} rows)")


if __name__ == "__main__":
    sys.exit(main())

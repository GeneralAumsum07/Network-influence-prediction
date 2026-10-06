"""
B1 - sample efficiency. Supervisor directive 5, outstanding since July 2026.

Two questions, in order of who asked:

  1. The lab's ~20% claim: how much of the performance survives when you can
     only label a fraction of the nodes?
  2. The on-thesis one: does the measured locality horizon r*(eps) SHIFT when
     training data is scarce?

Design, confounds and the dated predictions are in
`docs/prereg_B1_sample_efficiency.md`, written before this ran. Read that first;
this file is the instrument, not the argument.

WHY THE TEST FOLD IS NEVER SUBSAMPLED
-------------------------------------
Only the TRAINING portion of each fold shrinks. If the test fold shrank too,
tau at 5% and tau at 100% would be computed over different node sets and the
curve would confound "less training data" with "noisier measurement". Holding
the test fold whole makes every fraction an estimate of the SAME quantity, so
the fractions are paired within seed and the differences mean something.

WHY THIS RE-IMPLEMENTS THE OOF LOOP INSTEAD OF CALLING out_of_fold_predictions
-----------------------------------------------------------------------------
`out_of_fold_predictions` has no way to subsample a training fold, and adding
one would edit the function that produced 3,200 published cells - including its
`estimator=None` branch, whose entire job is to be untouchable. So the loop is
duplicated here, deliberately, and the duplication is then CHECKED rather than
trusted: the fraction=1.0 arm must reproduce `sweep_<tag>.csv` at the FULL tier
to within the documented n_jobs=-1 tolerance (~5e-08 in tau). If it does not,
this script differs from the pipeline in some way I did not intend and every
number it produces is worthless. Run `--check` before believing anything.

THE ONE LINE THAT MAKES THAT CHECK POSSIBLE
-------------------------------------------
At fraction >= 1.0 the training indices are passed through UNTOUCHED. Drawing
"100% without replacement" via rng.choice would return the same rows in a
different ORDER, and a random forest's bootstrap draws depend on row order - so
the 100% arm would differ from the published files by a small random amount and
the reproduction check would fail for a reason that has nothing to do with
sample efficiency. See `subsample()`.
"""
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import kendalltau
from sklearn.model_selection import KFold

from analyse import FULL
from influence.estimators import make_rf
from influence.features import select_features

NETS = ["ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined",
        "p2p-Gnutella08"]
TARGETS = ["betweenness", "spread_mean", "spread_cv", "spread_resid"]
RADII = [0, 1, 2, 3]
FRACTIONS = [0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00]
SEEDS = range(10)
TIERS_FULL = ["node", "edge", "subgraph"]      # the FULL structural tier
N_SPLITS = 5

OUT = "results/sample_efficiency.csv"


def subsample(train_idx: np.ndarray, frac: float, rng) -> np.ndarray:
    """
    Take `frac` of one fold's training rows, uniformly and without replacement.

    The >= 1.0 short-circuit is load-bearing, not an optimisation: see the
    module docstring. Returning `train_idx` itself keeps row ORDER identical to
    the published pipeline, which is what lets the 100% arm serve as a
    correctness test on this whole file.

    Uniform rather than stratified on purpose. Betweenness is 40-70% zeros here,
    so a 5% draw may hold very few nonzero nodes - but that IS label scarcity,
    and stratifying it away would answer an easier question. The realised
    nonzero count is logged per cell so a collapse can be attributed instead of
    guessed at.
    """
    if frac >= 1.0:
        return train_idx
    k = max(1, int(round(frac * len(train_idx))))
    return rng.choice(train_idx, size=k, replace=False)


def oof_subsampled(X, y, seed: int, frac: float):
    """
    Out-of-fold predictions with a shrunken training set.

    Mirrors `out_of_fold_predictions` exactly apart from the subsample: same
    KFold(shuffle=True, random_state=seed), same forest via `make_rf(seed)`,
    same one-integer-means-one-draw convention (the seed picks the fold split,
    the forest's randomness AND the subsample together).

    Returns (predictions, mean training rows used, mean nonzero targets in the
    training rows) - the last two so the prereg's "attribute, don't guess"
    requirement can actually be met at 5%.
    """
    preds = np.zeros(len(y), dtype=np.float64)
    kf = KFold(n_splits=N_SPLITS, shuffle=True, random_state=seed)
    rng = np.random.default_rng(seed)

    n_rows, n_nz = [], []
    for train_idx, test_idx in kf.split(X):
        sub = subsample(train_idx, frac, rng)
        n_rows.append(len(sub))
        n_nz.append(int((y[sub] != 0).sum()))
        model = make_rf(seed)
        model.fit(X[sub], y[sub])
        preds[test_idx] = model.predict(X[test_idx])

    return preds, float(np.mean(n_rows)), float(np.mean(n_nz))


def run_network(tag: str, done: set, flush=None) -> list:
    """
    Every (target, radius, fraction, seed) cell for one network.

    `flush` is called with the rows finished so far after each (target, radius)
    block. See the comment on main()'s flush for why the write cadence matters.
    """
    X = pd.read_csv(f"cache_features_{tag}.csv")
    Y = pd.read_csv(f"cache_targets_{tag}.csv")
    reg = pd.read_csv(f"cache_registry_{tag}.csv")

    rows = []
    for target in TARGETS:
        y = Y[target].to_numpy(np.float64)
        for r in RADII:
            cols = select_features(X, reg, max_hop=r, tiers=TIERS_FULL)
            Xm = X[cols].to_numpy(np.float64)
            for frac in FRACTIONS:
                for seed in SEEDS:
                    key = (tag, target, r, frac, seed)
                    if key in done:          # resume; see main()
                        continue
                    t0 = time.time()
                    p, nrow, nnz = oof_subsampled(Xm, y, seed, frac)
                    rows.append({
                        "network": tag, "target": target, "radius": r,
                        "richness": FULL, "fraction": frac, "seed": seed,
                        "kendall_tau": kendalltau(y, p).statistic,
                        "n_features": len(cols),
                        "train_rows": nrow, "train_nonzero": nnz,
                        "fit_seconds": time.time() - t0,
                    })
            # One (target, radius) block done - checkpoint it.
            if flush is not None:
                flush(rows)
    return rows


def check():
    """
    The fraction=1.0 arm against the published sweep. Run this FIRST.

    Compares a handful of cells rather than all 200: the failure mode being
    guarded against (a structurally different loop) shows up on the first cell,
    not the hundredth.
    """
    print("fraction=1.0 vs published sweep_<tag>.csv at the FULL tier")
    print(f"  {'network':<20s}{'target':<14s}{'r':>2s}{'seed':>5s}"
          f"{'published':>11s}{'here':>11s}{'|d|':>12s}")
    worst = 0.0
    cases = [("ca-GrQc", "betweenness", 2, 0),
             ("ca-HepTh", "spread_mean", 1, 0),
             ("facebook_combined", "betweenness", 2, 3),
             ("p2p-Gnutella08", "spread_cv", 3, 1)]
    for tag, target, r, seed in cases:
        X = pd.read_csv(f"cache_features_{tag}.csv")
        Y = pd.read_csv(f"cache_targets_{tag}.csv")
        reg = pd.read_csv(f"cache_registry_{tag}.csv")
        y = Y[target].to_numpy(np.float64)
        cols = select_features(X, reg, max_hop=r, tiers=TIERS_FULL)
        p, _, _ = oof_subsampled(X[cols].to_numpy(np.float64), y, seed, 1.0)
        got = kendalltau(y, p).statistic

        s = pd.read_csv(f"sweep_{tag}.csv")
        exp = s[(s.target == target) & (s.radius == r) & (s.seed == seed)
                & (s.richness == FULL)].kendall_tau.iloc[0]
        d = abs(got - exp)
        worst = max(worst, d)
        print(f"  {tag:<20s}{target:<14s}{r:>2d}{seed:>5d}"
              f"{exp:>11.6f}{got:>11.6f}{d:>12.2e}")

    ok = worst < 1e-6
    print(f"\n  worst |dtau| = {worst:.3e} -> "
          f"{'PASS' if ok else 'FAIL - this script is not the pipeline; run is VOID'}")
    return 0 if ok else 1


def main():
    if "--check" in sys.argv:
        return check()

    os.makedirs("results", exist_ok=True)
    # Resume on the CSV. 5,600 cells is a long night and an interrupted run
    # should not start over - the same reason stage2_sweep.py resumes.
    done, frames = set(), []
    if os.path.exists(OUT):
        prev = pd.read_csv(OUT)
        frames.append(prev)
        done = set(zip(prev.network, prev.target, prev.radius,
                       prev.fraction, prev.seed))
        print(f"resuming: {len(done)} cells already done")

    for tag in NETS:
        t0 = time.time()

        def flush(rows_so_far, _frames=frames):
            """
            Checkpoint after every (target, radius) block, not just per network.

            THE HOST HARD-CUTS UNDER SUSTAINED LOAD - see HANDOFF.md section 12.
            Two instant power losses on 2026-09-04 (01:19 and 10:36), no
            bugcheck, no dump, and no precursor in 2-second HWiNFO telemetry.
            Under the old per-network write, a cut 80% of the way through
            facebook_combined would have discarded all 1,120 of its cells -
            hours of work - because none of them had been written yet.

            Flushing per block bounds the loss to one block (70 cells, minutes).
            The resume key (network, target, radius, fraction, seed) is
            unchanged, so this changes WHEN the file is written and nothing
            whatsoever about what goes into it.

            `_frames` is bound as a default argument rather than closed over so
            the callback keeps working if the loop variable is ever rebound.
            """
            if rows_so_far:
                pd.concat(_frames + [pd.DataFrame(rows_so_far)],
                          ignore_index=True).to_csv(OUT, index=False)

        rows = run_network(tag, done, flush)
        if rows:
            frames.append(pd.DataFrame(rows))
            pd.concat(frames, ignore_index=True).to_csv(OUT, index=False)
        print(f"  {tag:<20s} {len(rows):4d} new cells  "
              f"{time.time() - t0:8.1f}s", flush=True)

    d = pd.concat(frames, ignore_index=True)
    print(f"\nwrote {OUT}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

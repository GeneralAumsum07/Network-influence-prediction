"""
Stage 2: the locality sweep, run from cached features/targets.

Writes each grid cell to disk as it completes, so a slow or interrupted run
never loses finished work.

WHY EVERY CELL IS NOW RUN AT SEVERAL SEEDS
------------------------------------------
This project's whole claim is that the neighbourhood radius is a MEASURED
quantity rather than a hyperparameter. A measurement without an uncertainty is
not a measurement, and the numbers the conclusions rest on are small:

    betweenness r1 -> r2 on ca-GrQc   +0.0010
    richness effects, every network   +/- 0.001
    volatility r2 -> r3 on ca-GrQc    +0.0146

At a single seed there is no way to tell any of those from run-to-run noise,
and r*(eps) is an integer that can flip on a different fold split. We already
refused to report gamma without a bootstrap; the primary metric gets the same
treatment.

Varying `seed` varies two things at once, which is exactly what we want:
  - which nodes land in which cross-validation fold
  - the random forest's own tree construction
Together they are the full sampling variability of one (cell, dataset) result.

Cost: linear in the number of seeds. With n_jobs=-1 that is affordable - the
whole point of fixing the core count first.

OUT-OF-FOLD PREDICTIONS ARE KEPT
--------------------------------
Every cell computes a prediction for every node from a model that never saw it,
scores it, and used to throw the predictions away - which meant the failure
analysis (Angle 3) could not be done without recomputing the entire sweep.
They are now written to `cache_oof_<tag>.npz`, keyed by
`target|radius|richness|seed`.

The cost is one float per node per cell: about 24 MB for the largest pilot
network, against the ~15 minutes of model fitting that produced them. Storing
the cheap thing rather than recomputing the expensive one is the same trade
stage1 already makes with the cascades.

WHICH LEARNER, AND WHERE ITS OUTPUT GOES
----------------------------------------
Added 2026-09-01 for the estimator-invariance sweep (M4). The optional fifth
argument names an entry in `influence/estimators.py`; it defaults to `rf`, the
random forest that produced every existing number.

`rf` writes `sweep_<tag>.csv` and `cache_oof_<tag>.npz` exactly as before, and
takes the untouched default code path inside `out_of_fold_predictions` - so a
re-run reproduces the published files rather than a lookalike of them.

ANY OTHER ESTIMATOR WRITES INTO `estimators/`, AND THAT IS NOT COSMETIC.
`analyse.py::discover_networks` finds networks by globbing `sweep_*.csv` and
regexing `sweep_(.+)\\.csv`. A file called `sweep_ca-GrQc__ridge.csv` sitting
beside the others would therefore be silently discovered as a NETWORK named
`ca-GrQc__ridge`, and would corrupt `analyse.py`, `analyse_topk.py`,
`analyse_multiplicity.py`, `make_fig1.py` and `verify_docs.py` - all five share
that glob, and none of them would error. The glob is non-recursive, so a
subdirectory is invisible to it and nothing existing changes.

Do not "just add an estimator column" instead: `analyse.load` and every
consumer of it assume one estimator per file.

INPUT IDENTITY (added 2026-09-11, Claude Opus 5, Task 6 findings P1-02/P2-04/P2-05)
--------------------------------------------------------------------------------
Before the first cell is fitted the run now refuses if (a) the edge list on
disk does not hash to the value the cache was built from, (b) the four
stage-1 files do not hash to what this sweep's existing rows were fitted on
(`<sweep>.inputs.json`, written on first write), or (c) the estimator is
rf_log1p and any target other than betweenness was requested. None of these
changes a number; each turns a silent mispairing into an error message. The
guards live in influence/sweep_inputs.py so run_experiment.py, which shells
out to this script, inherits them without a second implementation.

Usage:
    python stage2_sweep.py <tag> <targets> [max_hop] [n_seeds] [estimator]
    python stage2_sweep.py ca-GrQc spread_mean,spread_cv,betweenness 3 10
    python stage2_sweep.py ca-GrQc betweenness 3 10 ridge
"""
import sys, json, os, time
import numpy as np
import pandas as pd

from influence.features import select_features
from influence.experiment import (out_of_fold_predictions, evaluate,
                                  TIER_LADDER, feature_cost)
from influence.estimators import DEFAULT_ESTIMATOR, get_estimator
from influence.targets import assert_no_leakage
from influence.sweep_inputs import bind_inputs, check_source_identity

tag = sys.argv[1]
target_cols = sys.argv[2].split(",") if len(sys.argv) > 2 else ["spread_mean"]
max_hop = int(sys.argv[3]) if len(sys.argv) > 3 else 3
n_seeds = int(sys.argv[4]) if len(sys.argv) > 4 else 10
est_name = sys.argv[5] if len(sys.argv) > 5 else DEFAULT_ESTIMATOR

# Validate before reading any data, so a typo costs a second rather than a
# cache load. get_estimator raises on an unknown name.
get_estimator(est_name)

# P2-05 (Task 6 audit, Claude Opus 5, 2026-09-11). rf_log1p is the REPORTED
# betweenness arm and is scoped to betweenness only: log1p of spread_resid is
# NaN (negative on all five networks) and spread_cv is left-skewed on p2p, so
# the transform is not a neutral choice for them. Until now that scope lived
# in docstrings; a default four-target invocation would have written
# ineligible targets into the file analyse.py splices as the reported arm.
if est_name == "rf_log1p" and any(t != "betweenness" for t in target_cols):
    raise SystemExit(
        f"estimator rf_log1p is scoped to betweenness only (see "
        f"influence/estimators.make_rf_log1p); got targets {target_cols}")

# None, not `make_rf`, for the baseline. `out_of_fold_predictions` reproduces
# the published numbers only on its estimator=None branch; handing it an
# equivalent-looking factory would produce the same model today and would be
# one edit away from not doing so.
estimator = None if est_name == DEFAULT_ESTIMATOR else get_estimator(est_name)

X = pd.read_csv(f"cache_features_{tag}.csv")
Y = pd.read_csv(f"cache_targets_{tag}.csv")
reg = pd.read_csv(f"cache_registry_{tag}.csv")
meta = json.load(open(f"cache_meta_{tag}.json"))
timings = meta["timings"]

# Baseline output stays exactly where it has always been; every other
# estimator is quarantined in `estimators/` so the `sweep_*.csv` glob that
# five scripts use to discover NETWORKS cannot mistake a learner for a graph.
# See the module docstring - this is the single sharpest trap in this change.
if est_name == DEFAULT_ESTIMATOR:
    out_path = f"sweep_{tag}.csv"
    oof_path = f"cache_oof_{tag}.npz"
else:
    os.makedirs("estimators", exist_ok=True)
    out_path = os.path.join("estimators", f"sweep_{tag}__{est_name}.csv")
    oof_path = os.path.join("estimators", f"cache_oof_{tag}__{est_name}.npz")

print(f"estimator: {est_name}   -> {out_path}")

# Input identity (Task 6 audit P1-02 / P2-04, Claude Opus 5, 2026-09-11).
# Two refusals, both BEFORE the CSV is touched:
#   - the edge list on disk must hash to what the cache was built from;
#   - the four stage-1 files must hash to what this sweep's rows were fitted
#     on (recorded in <sweep>.inputs.json on first write).
# See influence/sweep_inputs.py for why each exists and what a mismatch means.
print(check_source_identity(tag, meta))
print(bind_inputs(out_path, tag))

# Resume key includes the seed, so an interrupted multi-seed run picks up at
# the exact cell it stopped on rather than redoing a whole seed.
done = set()
if os.path.exists(out_path):
    prev = pd.read_csv(out_path)
    if "seed" not in prev.columns:
        # A sweep from before seeds were recorded cannot be merged with one
        # that has them - we would not know which rows were which seed, and
        # silently averaging them would be worse than starting over.
        raise SystemExit(
            f"{out_path} predates seed tracking. Delete it and re-run:\n"
            f"    del {out_path}")
    done = {(r.target, r.radius, r.richness, r.seed) for r in prev.itertuples()}
    print(f"resuming: {len(done)} cells already done")

# Out-of-fold predictions, keyed target|radius|richness|seed. Loaded first so a
# resumed run extends the store rather than replacing it. (`oof_path` was set
# alongside `out_path` above, because the two must agree about which estimator
# this run is - a resume that read one estimator's predictions and appended
# another's metrics would be undetectable afterwards.)
oof: dict[str, np.ndarray] = {}
if os.path.exists(oof_path):
    with np.load(oof_path) as z:
        oof = {k: z[k] for k in z.files}
    print(f"loaded {len(oof)} stored prediction vectors")


def flush_oof() -> None:
    """Write the prediction store. Called periodically, not just at the end."""
    if oof:
        np.savez_compressed(oof_path, **oof)

total_cells = len(target_cols) * (max_hop + 1) * len(TIER_LADDER) * n_seeds
completed = 0
t_start = time.time()

for target_col in target_cols:
    if target_col not in Y.columns:
        print(f"  [skip] {target_col} not in cache_targets_{tag}.csv")
        continue
    y = Y[target_col].to_numpy(dtype=np.float64)
    print(f"\n=== target: {target_col} ===", flush=True)

    for r in range(0, max_hop + 1):
        for tier_name, tiers in TIER_LADDER.items():
            cols = select_features(X, reg, max_hop=r, tiers=tiers)
            if not cols:
                continue
            assert_no_leakage(cols)          # every cell, every time

            Xm = X[cols].to_numpy(dtype=np.float64)
            taus = []

            for seed in range(n_seeds):
                completed += 1
                # A cell counts as done only if BOTH its metrics row and its
                # prediction vector survived. The CSV is appended per cell but
                # the prediction store is flushed per grid row, so an
                # interruption can leave a handful of cells scored but with
                # their predictions lost - and the failure atlas would then be
                # silently missing those nodes. Requiring both closes that gap
                # at the cost of refitting at most a few cells.
                key = f"{target_col}|{r}|{tier_name}|{seed}"
                if (target_col, r, tier_name, seed) in done and key in oof:
                    continue

                t0 = time.perf_counter()
                preds = out_of_fold_predictions(Xm, y, n_splits=5, seed=seed,
                                                estimator=estimator)
                fit_s = time.perf_counter() - t0

                oof[f"{target_col}|{r}|{tier_name}|{seed}"] = preds
                m = evaluate(y, preds)
                m.update({"radius": r, "richness": tier_name,
                          "n_features": len(cols), "fit_seconds": fit_s,
                          "feature_seconds": feature_cost(cols, reg, timings),
                          "target": target_col, "network": tag, "seed": seed})
                taus.append(m["kendall_tau"])

                # Append immediately - never lose a finished cell.
                pd.DataFrame([m]).to_csv(
                    out_path, mode="a", header=not os.path.exists(out_path),
                    index=False)

            if taus:
                mean_tau = float(np.mean(taus))
                sd_tau = float(np.std(taus, ddof=1)) if len(taus) > 1 else 0.0
                elapsed = time.time() - t_start
                eta = elapsed / max(completed, 1) * (total_cells - completed)
                print(f"  r={r} {tier_name:20s} f={len(cols):3d} "
                      f"tau={mean_tau:.4f} +/- {sd_tau:.4f} "
                      f"(n={len(taus)} seeds, eta {eta/60:.1f}m)", flush=True)
                # Checkpoint the predictions alongside the metrics, so an
                # interruption costs at most one grid row of refitting.
                flush_oof()

flush_oof()
print(f"\nwrote {out_path}  ({time.time()-t_start:.0f}s)")
print(f"wrote {oof_path}  ({len(oof)} prediction vectors)")

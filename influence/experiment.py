"""
experiment.py
=============
The locality budget experiment: how far out must you look?

THE CORE MEASUREMENT
--------------------
We give a model access to strictly more information, one hop at a time, and
watch where performance stops improving.

    P(r)    = best ranking quality achievable using only the r-ball
    r*(eps) = smallest r with P(r) >= (1 - eps) * max_r' P(r')

The published work in this area picks a radius ad hoc - 2 hops here, 3 there -
and justifies it afterwards with benchmark numbers. We measure it instead.

NOTE ON THE CEILING. The reference point is the BEST radius observed, not the
deepest one. Those differ whenever P(r) is non-monotonic, which it is in
practice - on email-Eu-core, betweenness peaks at r=1 and then declines
slightly out to r=3, so P(r_max) is not the ceiling. Normalising by the
deepest radius would let a network that gets slightly worse with more
information report an artificially small r*. This file previously documented
the P(r_max) form while implementing the max form; the max form is correct and
is what locality_horizon does.

TWO AXES, NOT ONE
-----------------
Radius is not the only way to spend a compute budget. You can also look
RICHER at the same radius: node-level features, plus edge-level, plus
subgraph-level. So the real object is a surface over
(radius x richness), and the practical question is which direction buys more
accuracy per second.

That is why extract_features records timings per group, and why every cell of
the grid below reports cost alongside quality.

METRICS
-------
Influence is heavily skewed: a few enormous nodes, thousands near zero. Raw
error is dominated by the big ones and hides whether the ORDER is right, which
is what actually matters for finding influencers. So we lead with:

    Kendall tau   - did we rank every pair in the right order?
    precision@k   - of the true top k, how many did we catch?

RMSE is computed but never headlined.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

from .features import select_features
from .targets import assert_no_leakage


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------

def precision_at_k(y_true: np.ndarray, y_pred: np.ndarray, k: int) -> float:
    """Overlap between the true top-k and the predicted top-k."""
    if k <= 0 or k > len(y_true):
        return np.nan
    true_top = set(np.argsort(y_true)[::-1][:k].tolist())
    pred_top = set(np.argsort(y_pred)[::-1][:k].tolist())
    return len(true_top & pred_top) / k


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """All metrics for one prediction vector."""
    n = len(y_true)
    tau = kendalltau(y_true, y_pred).statistic
    rho = spearmanr(y_true, y_pred).statistic
    return {
        "kendall_tau": float(tau) if tau is not None else np.nan,
        "spearman": float(rho) if rho is not None else np.nan,
        "precision_at_1pct": precision_at_k(y_true, y_pred, max(1, n // 100)),
        "precision_at_5pct": precision_at_k(y_true, y_pred, max(1, n // 20)),
        "rmse": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
    }


# ----------------------------------------------------------------------------
# Honest predictions
# ----------------------------------------------------------------------------

def out_of_fold_predictions(X: np.ndarray, y: np.ndarray,
                            n_splits: int = 5,
                            seed: int = 0,
                            n_estimators: int = 120,
                            estimator=None) -> np.ndarray:
    """
    Predict every node with a model that never trained on it.

    Without this, a flexible model partly memorises the training nodes and its
    errors look artificially small - which would wreck the failure analysis,
    since we would be studying memorisation artefacts instead of genuine
    structural blind spots.

    Known limitation, stated openly: on a SINGLE graph the held-out nodes'
    features are still computed on a graph that contains the training nodes.
    This is not fully independent transfer. Testing on entirely separate
    networks is the clean version, and this pipeline supports it.

    CHOOSING THE LEARNER (added 2026-09-01)
    ---------------------------------------
    `estimator` is a factory `(seed) -> unfitted regressor`; see
    `influence/estimators.py` for the contract and the registry. It exists
    because r*(eps) is claimed to be a property of the (network, target) pair,
    and until this parameter existed there was no way to test that - every
    number in the project came from one random forest.

    `estimator=None` is not merely "the usual default": it keeps the ORIGINAL
    inline construction below, byte for byte, including honouring an explicit
    `n_estimators`. That is deliberate. 3,200 published cells came from this
    branch, and the regression test for this refactor is that they still
    reproduce to within the n_jobs=-1 tolerance documented below. Routing the
    default through the registry would be tidier and would put an entire
    corpus one careless edit away from silent invalidation.

    `n_estimators` is random-forest-specific and is IGNORED when a factory is
    supplied - a factory owns its own hyperparameters.
    """
    preds = np.zeros(len(y), dtype=np.float64)
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)

    for train_idx, test_idx in kf.split(X):
        # The seed is handed to the factory rather than fixed here, so that
        # one `seed` continues to mean one coherent draw of sampling
        # variability: the same integer picks the fold split AND the model's
        # internal randomness, which is what stage2_sweep.py's header promises
        # the error bars are measuring.
        if estimator is not None:
            model = estimator(seed)
        else:
            model = RandomForestRegressor(
                n_estimators=n_estimators,
                # -1 uses every core. Trees are independent, so the speedup is
                # close to linear and it is what makes ten seeds per cell
                # affordable.
                #
                # ONE CAVEAT, MEASURED RATHER THAN ASSUMED. random_state still
                # fixes which trees get built, but sklearn accumulates their
                # predictions in whatever order the workers finish, and
                # floating-point addition is not associative. So predictions are
                # reproducible only to the last bits: two identical runs on
                # p2p-Gnutella08 differ by 5.7e-14 at n_jobs=-1 and by exactly 0
                # at n_jobs=1. Because Kendall tau is a rank statistic, that
                # amplifies to about 5e-08 in tau - a last-bit difference can flip
                # a near-tie, which moves tau by a discrete step.
                #
                # 5e-08 sits five orders of magnitude below the seed-to-seed
                # spread we actually report (~1e-3), so it cannot affect a
                # conclusion. Set this to 1 if you need bit-exact reproduction for
                # an audit, and accept roughly a tenfold slowdown.
                n_jobs=-1,
                random_state=seed,
                min_samples_leaf=2,
            )
        model.fit(X[train_idx], y[train_idx])
        preds[test_idx] = model.predict(X[test_idx])

    return preds


# ----------------------------------------------------------------------------
# The sweep
# ----------------------------------------------------------------------------

# The richness ladder. Each rung adds a kind of object the observer may
# describe, holding the radius fixed.
#
# A FOURTH RUNG WAS ADDED, AND ITS SEPARATION IS THE POINT. The `dynamic` tier
# holds the truncated percolation estimate - a local approximation of the
# cascade itself rather than a structural proxy for it. It is the only family
# that assumes the observer knows the transmission probability p, which is a
# modelling assumption and not a structural one. Keeping it on its own rung
# means no general claim about "richness" can quietly depend on it, and it can
# be dropped from any analysis by deleting one line.
TIER_LADDER = {
    "node": ("node",),
    "node+edge": ("node", "edge"),
    "node+edge+subgraph": ("node", "edge", "subgraph"),
    "node+edge+subgraph+dynamic": ("node", "edge", "subgraph", "dynamic"),
}


def locality_sweep(features: pd.DataFrame,
                   registry: pd.DataFrame,
                   targets: pd.DataFrame,
                   target_col: str,
                   timings: dict | None = None,
                   max_hop: int = 3,
                   n_splits: int = 5,
                   seed: int = 0,
                   verbose: bool = True,
                   estimator=None) -> pd.DataFrame:
    """
    Run the full (radius x richness) grid for one target.

    Returns one row per cell with quality metrics, the feature count, and the
    wall-clock cost of the features that cell was allowed to use.

    `estimator` is passed straight through to `out_of_fold_predictions`; None
    keeps the random forest that produced every published number. Note that
    the production sweep does NOT come through here - `stage2_sweep.py` calls
    `out_of_fold_predictions` directly because it needs per-cell checkpointing.
    This path is the one `run_experiment.py` uses.
    """
    y = targets[target_col].to_numpy(dtype=np.float64)
    rows = []

    for r in range(0, max_hop + 1):
        for tier_name, tiers in TIER_LADDER.items():
            cols = select_features(features, registry, max_hop=r, tiers=tiers)
            if len(cols) == 0:
                continue

            # The guard runs on EVERY cell, not once at the start.
            assert_no_leakage(cols)

            X = features[cols].to_numpy(dtype=np.float64)

            t0 = time.perf_counter()
            preds = out_of_fold_predictions(X, y, n_splits=n_splits, seed=seed,
                                            estimator=estimator)
            fit_time = time.perf_counter() - t0

            metrics = evaluate(y, preds)
            metrics.update({
                "radius": r,
                "richness": tier_name,
                "n_features": len(cols),
                "fit_seconds": fit_time,
                "feature_seconds": feature_cost(cols, registry, timings),
                "target": target_col,
            })
            rows.append(metrics)

            if verbose:
                print(f"    r={r} {tier_name:20s} "
                      f"feats={len(cols):3d}  tau={metrics['kendall_tau']:.4f}  "
                      f"p@5%={metrics['precision_at_5pct']:.3f}")

    return pd.DataFrame(rows)


# Extraction groups that are inherently CUMULATIVE: producing level k requires
# having produced every level below it. A BFS cannot reach shell 3 without
# first building shells 1 and 2, and h^(3) is defined by iterating on h^(2).
#
# In the sweep this closure never actually binds, because select_features takes
# every feature with hop <= r and both families are tier 'node', so the lower
# levels are always selected alongside the higher ones. We expand it anyway so
# that feature_cost stays correct for an arbitrary hand-picked column subset -
# which is exactly the situation the old cost model got wrong.
CUMULATIVE_GROUP_FAMILIES = ("shells_ci_hop_", "h_index_order_")


def feature_cost(cols: list[str], registry: pd.DataFrame,
                 timings: dict | None) -> float:
    """
    Wall-clock seconds this cell's features actually cost to extract.

    HOW THIS WORKS NOW, AND WHAT IT REPLACES
    ----------------------------------------
    Each feature records the timed extraction group that produced it, so the
    cost of a cell is just the sum over the distinct groups its columns touch.
    No inference, no mapping to keep in sync.

    The previous version inferred the group from hop and tier, and was wrong
    in both directions at once. It charged the whole collective-influence and
    H-ladder cost at r=1, including the CI_2 and CI_3 work that a radius-1
    observer cannot use, and it charged nothing extra for r=2 -> r=3, so those
    two rows carried identical costs on every network. Any Pareto frontier
    built on it was ranking noise.

    Returns NaN when no timings are available, which is the honest answer for
    a sweep run from a cache that predates timing.
    """
    if not timings:
        return np.nan

    if "group" not in registry.columns:
        raise ValueError(
            "registry has no 'group' column, so feature cost cannot be "
            "attributed. It was written by an older features.py - re-run "
            "stage1_prepare.py for this network.")

    sel = registry[registry["feature"].isin(cols)]
    groups = set(sel["group"].dropna().tolist())

    # Pull in the prerequisites of any cumulative family that got selected.
    for fam in CUMULATIVE_GROUP_FAMILIES:
        levels = [int(g[len(fam):]) for g in groups
                  if g.startswith(fam) and g[len(fam):].isdigit()]
        if levels:
            groups.update(f"{fam}{k}" for k in range(1, max(levels) + 1))

    return float(sum(timings.get(g, 0.0) for g in groups))


# ----------------------------------------------------------------------------
# r* extraction
# ----------------------------------------------------------------------------

def locality_horizon(sweep: pd.DataFrame, epsilon: float = 0.1,
                     richness: str = "node+edge+subgraph",
                     metric: str = "kendall_tau") -> dict:
    """
    r*(eps): the smallest radius reaching (1 - eps) of the best observed value.

    eps = 0.1 means "90 percent as good as the richest, furthest-looking
    configuration we measured".
    """
    sub = sweep[sweep["richness"] == richness].sort_values("radius")
    if len(sub) == 0:
        return {}

    ceiling = sub[metric].max()

    # The tolerance is MULTIPLICATIVE, which silently inverts when the ceiling
    # is negative: (1 - eps) * (-0.10) = -0.09, which is ABOVE the ceiling, so
    # nothing qualifies and r* comes back None on a curve that plainly has a
    # best radius. "90% as good" is only meaningful when better means larger and
    # the scale has a zero at chance, which is true of tau and precision@k and
    # is why those are the only metrics passed here.
    #
    # Currently latent - all 3,204 swept rows have tau > 0 - so this changes no
    # existing number. It is guarded rather than left to be discovered by the
    # first genuinely hard (network, target) pair, where a negative tau is an
    # ordinary outcome and a silent None would read as "no horizon exists".
    if ceiling <= 0:
        raise ValueError(
            f"locality_horizon needs a positive ceiling to apply a relative "
            f"tolerance; {metric} peaks at {ceiling:.4f} on richness="
            f"{richness!r}. A negative or zero ceiling means the model does no "
            f"better than chance at every radius, so r*(eps) is undefined "
            f"rather than large - report the curve instead.")

    threshold = (1 - epsilon) * ceiling

    qualifying = sub[sub[metric] >= threshold]
    r_star = int(qualifying["radius"].min()) if len(qualifying) else None

    return {
        "r_star": r_star,
        "epsilon": epsilon,
        "ceiling": float(ceiling),
        "threshold": float(threshold),
        "metric": metric,
        "richness": richness,
        "curve": sub[["radius", metric]].to_dict("records"),
    }

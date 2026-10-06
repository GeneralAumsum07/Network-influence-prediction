"""
estimators.py - the learners the sweep is allowed to use.

WHY THIS MODULE EXISTS
----------------------
Every number in this project is measured under exactly one learner: a random
forest, constructed inline inside `out_of_fold_predictions`. That was fine
while the claim was "these features predict this target". It is not fine any
more, because the headline claim is now that r*(eps) is a property of the
(network, target) PAIR rather than of the model - and nothing in the project
tests that.

The 2026-08-31 audit made this urgent rather than merely incomplete. Finding
10's carrying feature, `local_conductance_2`, turned out to be ~99%
reconstructible from columns already in the table (held-out R^2 ~ +0.99 by two
protocols) and is STILL worth +0.117 tau. So what that feature buys is
ACCESSIBILITY, not information: a forest splitting on axis-aligned thresholds
cannot form the ratio cut/vol out of a dozen shell columns, and handing it the
ratio directly is worth a third of a hop.

An accessibility gain is precisely the kind of effect a different inductive
bias erases. A linear model computes ratios for free in the space where they
matter. If ridge shows no subgraph-tier gain on facebook, Finding 10 is a
statement about random forests and the write-up has to say so. That is the
falsification test this module exists to make runnable.

THE FACTORY CONTRACT
--------------------
A factory is `(seed: int) -> unfitted regressor`. It takes the seed rather
than being nullary because every estimator that has any randomness must be
seeded from the SAME seed that chose the fold split - that is what makes a
"seed" in this project one coherent draw of sampling variability (fold
assignment AND model construction together), which is what `stage2_sweep.py`'s
header already promises.

ADDING ONE
----------
Register it in ESTIMATORS below. Anything with sklearn's fit/predict contract
works, including a cuML regressor (that is deliberate - see the GPU timing
gate in the plan; a cuML forest should be a factory here, not a port).
"""
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import numpy as np


def make_rf(seed: int):
    """
    The project default, reproduced EXACTLY as it was constructed inline.

    Do not "improve" these hyperparameters. Every published number in
    `sweep_*.csv` came from this construction, and the regression test for the
    estimator refactor is that the default path still reproduces those files
    to within the documented n_jobs=-1 tolerance (~5e-08 in tau). A changed
    default silently invalidates 3,200 cells.
    """
    return RandomForestRegressor(
        n_estimators=120,
        # -1 uses every core; see the long note in experiment.py on why this
        # costs bit-exactness and why that is acceptable.
        n_jobs=-1,
        random_state=seed,
        min_samples_leaf=2,
    )


def make_ridge(seed: int):
    """
    Linear baseline - the actual falsification test for Finding 10.

    THE SCALER IS NOT OPTIONAL AND ITS PLACEMENT IS THE WHOLE POINT.
    The feature table mixes raw counts (shell_2_count, in the thousands),
    degrees, bounded ratios (clustering, conductance, in [0,1]) and
    log-transformed columns - four orders of magnitude apart. Ridge penalises
    coefficients, so an unscaled fit would shrink the small-scale columns to
    nothing and we would measure FEATURE SCALING rather than inductive bias.
    The verdict "invariance fails" would then be an artefact of our own
    preprocessing, which is exactly the class of error this project keeps
    catching in other people's work.

    `make_pipeline` fits the scaler on the training fold only, inside
    `out_of_fold_predictions`' KFold loop. Scaling the whole matrix once
    before the split would leak the test fold's mean and variance into
    training - a small leak, but this project does not get to publish a
    leakage critique and then commit one.

    `seed` is unused: ridge with a fixed alpha grid is deterministic given the
    fold split, and the fold split is already seeded by the caller. Keeping
    the parameter keeps every factory one interface.
    """
    return make_pipeline(
        StandardScaler(),
        # A wide log grid rather than a hand-picked alpha: the right amount of
        # shrinkage varies by an order of magnitude between a 35-column node
        # cell and a 171-column full cell, and picking one alpha would hand
        # ridge a handicap that varies systematically ALONG THE RADIUS AXIS -
        # i.e. exactly along the axis we are trying to measure.
        #
        # RidgeCV's default is efficient leave-one-out on the training fold,
        # so this costs almost nothing and never touches the test fold.
        RidgeCV(alphas=np.logspace(-3, 6, 40)),
    )


def make_hgb(seed: int):
    """
    Histogram gradient boosting - a second non-linear learner.

    Included because it is a DIFFERENT non-linear bias, not just a faster
    forest: boosting fits residuals sequentially, so a feature that a forest
    needs many correlated splits to approximate can be picked up in a few
    boosting rounds. If Finding 10's gain survives ridge's disappearance but
    tracks the forest here, that localises the effect to axis-aligned
    ensembling rather than to non-linearity as such.

    It is also already a project dependency: `analyse_features.py`'s
    reconstructibility probe uses it, so nothing new is being installed - which
    matters, because installing into this env is how the OpenBLAS/MKL abort
    gets reintroduced.

    Single-threaded per fit is NOT set here; HGB uses OpenMP internally and
    respects OMP_NUM_THREADS.
    """
    return HistGradientBoostingRegressor(random_state=seed)


def make_hgb_matched(seed: int):
    """
    `hgb`, but with its leaf floor matched to the forest's. POST-HOC.

    WHY THIS EXISTS, AND WHY IT IS NOT A REPLACEMENT FOR `hgb`
    ----------------------------------------------------------
    The pre-registered `hgb` arm compared a learner at sklearn's DEFAULT
    min_samples_leaf=20 against `rf` pinned at 2. That is a comparison of leaf
    floors, not of inductive biases, and P3 was scored against it.

    Isolating one hyperparameter at a time on facebook betweenness r=2
    (seed 0, node+edge+subgraph) showed how much that mattered:

        hgb as swept (min_samples_leaf=20)      0.2076
        ONLY min_samples_leaf=2                 0.6286   <- 68% of the gap
        ONLY max_iter=1000                      0.1303   (worse)
        ONLY max_leaf_nodes=255                 0.2024   (flat)
        rf as swept                             0.8231

    So the leaf floor alone explains most of it, while the two obvious
    "capacity" knobs explain none. Note that this is the SAME error the module
    docstring above congratulates itself for avoiding on ridge's scaler - a
    learner crippled by a hyperparameter nobody chose, reported as inductive
    bias. It hid inside a default, which is why it was missed.

    `min_samples_leaf` is the ONLY change. max_iter and max_leaf_nodes stay at
    their defaults despite being tempting, because the isolation shows neither
    helps and because changing three things at once is what caused this.

    THIS DOES NOT UN-FALSIFY P3. P3 is falsified and stays falsified; see
    `docs/posthoc_B2_hgb_capacity.md`, which was written before this ran. The
    pre-registered `hgb` arm's output files are KEPT alongside this one so the
    confound stays inspectable rather than being tidied away.
    """
    return HistGradientBoostingRegressor(min_samples_leaf=2, random_state=seed)


def make_rf_log1p(seed: int):
    """
    The pinned forest, trained on log1p(y) instead of y. Added 2026-09-03.

    WHY THIS IS A CORRECTION AND NOT A METRIC RELAXATION
    ----------------------------------------------------
    Every fit in this project minimises squared error; every score is Kendall
    tau. On betweenness that gap is not academic - the target's skew runs from
    4.77 (p2p) to 28.88 (facebook), so squared error spends nearly all of its
    budget on the few enormous nodes and buys ranking accuracy nowhere. Finding
    11 measured the cost at +0.1838 tau on facebook betweenness r=2, larger
    than any feature tier in the project.

    Kendall tau is invariant to monotone transforms of the GROUND TRUTH, so
    training on log1p(y) while scoring tau against the untransformed y changes
    what the model optimises and not what it is judged against. That is what
    makes this a better-conditioned objective rather than an easier test.

    `TransformedTargetRegressor` applies expm1 to the predictions on the way
    out. That is a no-op for our purposes - expm1 is strictly increasing, so it
    cannot change a single pairwise ordering and therefore cannot change tau -
    but it is kept rather than bypassed so that `rmse`, which IS reported in
    the sweep and is NOT rank-invariant, stays in the target's own units and
    remains comparable to the published column. Predictions live in roughly
    [0, 15.2] in log space (facebook's max betweenness is 3.9e6), nowhere near
    expm1's overflow range.

    WHY THIS IS A REGISTRY ENTRY RATHER THAN A NEW PARAMETER
    -------------------------------------------------------
    The alternative was threading a target-transform argument through
    `out_of_fold_predictions` -> `locality_sweep` -> `stage2_sweep.py`. That
    touches the exact code path that produced 3,200 published cells, including
    the `estimator=None` branch whose whole job is to be untouchable. A factory
    reaches the same place through the door that already exists: no signature
    changes, no risk to the default path, and the output lands in `estimators/`
    where the `sweep_*.csv` glob cannot see it.

    SCOPE: BETWEENNESS ONLY. This must not be swept over the other three
    targets, and the reason is arithmetic rather than stylistic:
      - `spread_resid` is a RESIDUAL and is negative on all five networks
        (min -0.9364 on facebook), so log1p is undefined or wrong there.
      - `spread_cv` is left-skewed on p2p-Gnutella08 (-0.96); log1p would make
        the conditioning worse, not better.
    A transform applied where it is not indicated is an intervention, not a
    correction. See `docs/decl_objective_resweep.md`.
    """
    return TransformedTargetRegressor(
        # The SAME construction as `make_rf`, called rather than duplicated, so
        # the objective is provably the only thing that differs between this
        # arm and the published one.
        regressor=make_rf(seed),
        func=np.log1p,
        inverse_func=np.expm1,
        # Left at its default True deliberately: it round-trips a subsample and
        # warns if func/inverse disagree. log1p/expm1 are exact inverses, so
        # this is free, and it would catch a later edit that broke the pair.
        check_inverse=True,
    )


# The registry. Keys are what appears in output filenames and on the CLI, so
# keep them short, lowercase and filename-safe.
ESTIMATORS = {
    "rf": make_rf,
    "ridge": make_ridge,
    "hgb": make_hgb,
    # Post-hoc, added 2026-09-01. Not part of the B2 pre-registration.
    "hgb_matched": make_hgb_matched,
    # Objective correction, added 2026-09-03. Betweenness only - see the
    # docstring; the other three targets are not eligible for log1p.
    "rf_log1p": make_rf_log1p,
}

# The one that produced every existing number. Named rather than hard-coded at
# each use site so "which estimator is the baseline" has a single answer.
DEFAULT_ESTIMATOR = "rf"


def get_estimator(name: str):
    """Look up a factory by name, failing loudly on a typo."""
    if name not in ESTIMATORS:
        raise KeyError(
            f"unknown estimator {name!r}; known: {sorted(ESTIMATORS)}")
    return ESTIMATORS[name]

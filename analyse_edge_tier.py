"""
analyse_edge_tier.py - what inside one richness rung rescues betweenness?

WHY THIS EXISTS
---------------
Until the corpus reached five networks, the edge tier looked like a citable
null. On ca-GrQc, email-Eu-core and p2p-Gnutella08 it bought at most a few
thousandths, and the write-up said so: supervisor directive 4 was satisfied by
building the tier, not by the tier mattering.

facebook_combined broke that. At radius 2, predicting betweenness, one rung of
the ladder bought roughly +0.15 tau against a seed sd of ~0.005 - a ~27 sd
effect, and roughly five times larger than any richness gain previously
measured anywhere in this project. A number that big, appearing on exactly one
network, is either a real structural fact or an artefact - and it overturns a
documented finding either way, so it gets isolated rather than reported off the
sweep table. That is what this script does.

WHICH RUNG - AND WHY THAT IS NOW A PARAMETER
--------------------------------------------
Originally this script was hard-wired to the edge tier, because the two columns
that carry the effect,

    ball2_density        how dense the 2-ball is internally
    local_conductance_2  what fraction of the 2-ball's edge volume leaves it

were both registered as `edge`. The 2026-08-31 code audit found that tagging
was wrong: the edge tier is defined as the distribution of structure across a
node's INCIDENT edges, whereas both of these aggregate edges AMONG 2-ball
members - which is what the subgraph tier means, and which is how the third
column off the same array, `ball2_edges`, was already tagged. Both were
retagged `subgraph`, and every sweep cell that depended on the boundary was
refitted.

Nothing about the machinery here was ever edge-specific, so `--tier` now
selects the rung. The baseline is every rung BELOW the one under test and the
ceiling is that baseline plus the whole rung, which is exactly the nested
comparison the sweep table reports:

    --tier edge      node                -> node + edge
    --tier subgraph  node + edge         -> node + edge + subgraph

Run BOTH before writing the finding up. The retag moved the two carrying
columns one rung along; the prediction is unchanged, but which rung earns the
credit is precisely the claim, so it has to be measured on each rung rather
than assumed to have moved wholesale.

THE HYPOTHESIS BEING TESTED
---------------------------
facebook_combined is a union of ego networks. Betweenness there is dominated by
the handful of nodes bridging otherwise separate friend groups. A bridge is
invisible to node-tier features - a bridging node need not have unusual degree,
clustering or H-index - but it is exactly what a boundary measurement sees: the
edges leaving the ball do not come back.

`local_conductance_2` is a bridge detector by construction. So the prediction
is that it, and not the orbit columns that arrive at the same radius, carries
the effect. If instead the orbit columns carry it, the story is the opposite -
the gain is about local subgraph vocabulary, not boundary geometry - and the
write-up has to say that instead. Both outcomes are publishable; guessing is
not.

WHY GROUPS AND NOT SINGLE COLUMNS
---------------------------------
The registry already partitions each tier into named cost groups, and those
groups are what a practitioner would switch on or off. Ablating a single column
out of a correlated block mostly measures how well a random forest routes
around it - the orbit_04 result was a reminder that 0.99 correlation is not
redundancy. Groups keep the question answerable.

Everything is paired across seeds: the same seed's baseline and variant share a
fold split, so the difference cancels the shared noise. Unpaired, a +0.005
effect would be unreadable.

WHICH OBJECTIVE - ADDED 2026-09-12
----------------------------------
Every number this script printed before 2026-09-12 was fitted under the raw
squared-error objective: `out_of_fold_predictions` with its default estimator.
For betweenness that is the HISTORICAL arm. Since 2026-09-04 the study reports
betweenness from the `rf_log1p` arm (train on log1p(y), score tau against y),
and Task 6 finding P2-11 recorded that the two arms can disagree by a lot on
exactly this rung: +0.1291 raw vs +0.0436 log1p for the r=2 subgraph rung on
facebook. So `--objective` now exists. `raw` (the default) keeps the historical
construction byte for byte, so the 2026-09-01 output files still reproduce;
`reported` routes betweenness through the registry's `rf_log1p` factory and
leaves every other target on `rf`, which is what "reported" means for them.
The header line names the arm so no output can be quoted without it.
(Added 2026-09-12 by Claude Opus 5, Task 6 root integration run C8.)

Run:  python analyse_edge_tier.py [tag ...] [--tier subgraph]
                                  [--target betweenness] [--seeds 10]
                                  [--objective raw|reported]
"""
import argparse

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from influence.features import select_features
from influence.experiment import out_of_fold_predictions, TIER_LADDER
from influence.estimators import ESTIMATORS
from influence.targets import assert_no_leakage

# The reference tier is the richest STRUCTURAL one, deliberately excluding
# `dynamic` - same rule as analyse.py. The dynamic tier assumes the observer
# knows p, and no headline claim may quietly depend on that.
NODE_ONLY = TIER_LADDER["node"]
NODE_EDGE = TIER_LADDER["node+edge"]

# Which rung is being isolated. Parameterised on 2026-08-31: the two features
# that carry this whole finding (`ball2_density`, `local_conductance_2`) were
# retagged edge -> subgraph by the code audit, so the question "which group
# inside the tier carries the gain" now has to be askable of the subgraph tier
# too. Nothing about the machinery was edge-specific; only the constant was.
RUNG = {
    "edge":     (TIER_LADDER["node"], TIER_LADDER["node+edge"]),
    "subgraph": (TIER_LADDER["node+edge"], TIER_LADDER["node+edge+subgraph"]),
}


def objective_factory(target: str, objective: str):
    """
    Which estimator factory `out_of_fold_predictions` gets, and its label.

    `None` is not a shortcut: it selects the ORIGINAL inline forest inside
    `out_of_fold_predictions`, which is the construction every pre-2026-09-12
    output of this script came from. Only the reported betweenness arm needs a
    different learner; every other target's reported objective is plain `rf`,
    so it stays on the default path and reproduces exactly.
    """
    if objective == "reported" and target == "betweenness":
        return ESTIMATORS["rf_log1p"], "log1p betweenness (reported arm)"
    if target == "betweenness":
        return None, "raw betweenness (historical arm; the study reports log1p)"
    return None, f"raw squared error ({target}: reported == raw)"


def score(X: pd.DataFrame, cols: list[str], y: np.ndarray,
          n_seeds: int, estimator=None) -> np.ndarray:
    """
    Kendall tau at each seed, from out-of-fold predictions.

    Returns the per-seed vector rather than its mean so the caller can pair.
    """
    assert_no_leakage(cols)              # every variant, every time
    Xm = X[cols].to_numpy(dtype=np.float64)
    return np.array([
        kendalltau(y, out_of_fold_predictions(Xm, y, 5, s,
                                              estimator=estimator)).statistic
        for s in range(n_seeds)
    ])


def paired(variant: np.ndarray, base: np.ndarray) -> tuple[float, float, bool]:
    """
    Paired mean gain, its sd, and whether it clears twice that sd.

    Paired because radius/richness variants at the same seed share their fold
    split; differencing first removes the shared component and is a far
    sharper test than comparing two independent means.
    """
    d = variant - base
    mean = float(d.mean())
    sd = float(d.std(ddof=1)) if len(d) > 1 else 0.0
    return mean, sd, abs(mean) > 2 * sd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="*",
                    default=["facebook_combined", "ca-HepTh", "ca-GrQc",
                             "email-Eu-core", "p2p-Gnutella08"])
    ap.add_argument("--target", default="betweenness")
    ap.add_argument("--radius", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--tier", default="edge", choices=sorted(RUNG),
                    help="which rung of the richness ladder to isolate")
    ap.add_argument("--objective", default="raw", choices=["raw", "reported"],
                    help="raw = historical squared-error arm (reproduces the "
                         "2026-09-01 files); reported = rf_log1p for betweenness")
    args = ap.parse_args()
    BASE_TIERS, FULL_TIERS = RUNG[args.tier]
    estimator, objective_label = objective_factory(args.target, args.objective)

    print("=" * 78)
    print(f"{args.tier.upper()} TIER ABLATION   target={args.target}  "
          f"radius={args.radius}  seeds={args.seeds}")
    print("  paired within seed; * = |gain| > 2 x sd of the paired difference")
    # Objective label added 2026-09-12 (Claude Opus 5, Task 6 findings
    # P2-11/P3-08): an output of this script must never be quoted without its arm.
    print(f"  objective: {objective_label}")
    print("=" * 78)

    for tag in args.tags:
        X = pd.read_csv(f"cache_features_{tag}.csv")
        Y = pd.read_csv(f"cache_targets_{tag}.csv")
        reg = pd.read_csv(f"cache_registry_{tag}.csv")

        if args.target not in Y.columns:
            print(f"\n{tag}: no target {args.target} - skipped")
            continue
        y = Y[args.target].to_numpy(dtype=np.float64)

        # Baseline: every rung BELOW the one under test, at this radius.
        base_cols = select_features(X, reg, max_hop=args.radius,
                                    tiers=BASE_TIERS)
        # Ceiling: the same plus the whole rung under test.
        full_cols = select_features(X, reg, max_hop=args.radius,
                                    tiers=FULL_TIERS)

        base = score(X, base_cols, y, args.seeds, estimator)
        full = score(X, full_cols, y, args.seeds, estimator)
        g_full, sd_full, sig_full = paired(full, base)

        print(f"\n{tag}   (n={len(y)})")
        print(f"  below {args.tier:<14s} f={len(base_cols):3d}  "
              f"tau={base.mean():.4f} +/- {base.std(ddof=1):.4f}")
        print(f"  + FULL {args.tier:<13s} f={len(full_cols):3d}  "
              f"tau={full.mean():.4f}   gain {g_full:+.4f} +/- {sd_full:.4f}"
              f"{'*' if sig_full else ' '}")

        # Now one group at a time, each added to the node baseline alone, so
        # the groups do not mask each other. The edge tier's groups are read
        # from the registry rather than hard-coded - a new edge feature
        # registered with a new group name appears here automatically.
        edge = reg[(reg.tier == args.tier) & (reg.hop <= args.radius)]
        if edge.empty:
            continue

        print(f"  {'-' * 66}")
        print(f"  {'added group':<26s} {'f':>4s}  {'tau':>7s}  "
              f"{'gain vs node':>14s}")

        rows = []
        for group, sub in edge.groupby("group"):
            add = sub.feature.tolist()
            cols = base_cols + [c for c in add if c in X.columns]
            s = score(X, cols, y, args.seeds, estimator)
            g, sd, sig = paired(s, base)
            rows.append((group, len(add), s.mean(), g, sd, sig))

        # Largest effect first - the point of the table is which group carries
        # the gain, so ordering by it is the readable presentation.
        for group, nf, tau, g, sd, sig in sorted(rows, key=lambda r: -r[3]):
            print(f"  {group:<26s} {nf:>4d}  {tau:.4f}  "
                  f"{g:+.4f} +/- {sd:.4f}{'*' if sig else ' '}")

    print()


if __name__ == "__main__":
    main()

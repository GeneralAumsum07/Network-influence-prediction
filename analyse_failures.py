"""
analyse_failures.py - the failure atlas (Angle 3).

THE QUESTION
------------
Every other analysis in this project asks *how accurate* local prediction is.
This one asks a different and more interesting question: **what is locality
blind to?** Not "we reach tau = 0.94" but "here is the kind of node a bounded
neighbourhood cannot see, and here is what it has in common."

That reframing is the point. A number like 0.94 is a benchmark result; a
characterisation of the residual is a finding about the structure of the
problem.

THE RESIDUAL
------------
Influence is heavily skewed, so raw error is dominated by the few enormous
nodes and says nothing about ordering. We work in rank space throughout:

    delta(v) = pct_true(v) - pct_pred(v)

where pct is the percentile rank, 1.0 being the most influential node. Then

    delta > 0  the node is genuinely more important than we said
               -> UNDER-PREDICTED, a "hidden influencer"
    delta < 0  the node looked more important than it turned out to be
               -> OVER-PREDICTED, a "false promise"

delta is computed inside each seed and then averaged across the ten, so a node
lands in a tail because the model consistently misplaces it rather than
because one fold split happened to.

AND THEN THE MECHANICAL PART IS REMOVED
---------------------------------------
Raw delta is not usable as-is, for two separate reasons - see
`standardise_residual` for the full argument.

The first is shrinkage: every regression pulls predictions toward the middle,
so high-influence nodes get positive delta and low-influence nodes negative
delta purely as an artefact of fitting. The second, which is easier to miss, is
that residual VARIANCE is wildly non-constant - thousands of near-tied
peripheral nodes are misranked far more loosely than well-connected ones, so
the tails of the residual fill up with the periphery regardless of structure.

Both are removed by standardising within bins of true influence: subtract the
median, divide by the median absolute deviation. A node then earns a tail place
by being misranked far RELATIVE TO HOW PRECISELY NODES LIKE IT CAN BE RANKED.

THREE TABLES, AND THE THIRD IS THE SHARP ONE
--------------------------------------------
Each tail is profiled against the well-ranked middle, which answers "what makes
a node hard to rank at all". Those two tables tend to look alike, because being
hard to rank is largely one property.

The third table compares the two tails against EACH OTHER. That cancels
everything they share and leaves only what decides the SIGN of the error -
whether a node is a hidden influencer or a false promise. If that table is flat,
the model has no directional blind spot: it is imprecise on an identifiable
population but not biased about it. That is a real result and a different one
from "we found the hidden influencers", so the two must not be conflated.

The report also prints the median true percentile of each tail and the overlap
with the unadjusted tail, so the corrections above are checkable rather than
asserted.

PROFILING AGAINST WHAT THE MODEL COULD NOT SEE
----------------------------------------------
The atlas can only explain a blind spot using information that was withheld
from the model. So the profiling axes are deliberately GLOBAL - coreness,
distance to the nearest hub, the gap between global coreness and its local
H-index proxy. These come from structure.py, never from features.py, and the
leakage guard would abort the sweep if any of them ever became a column in the
feature matrix.

Local features are profiled too, but as context rather than explanation: they
say what the failing nodes look like from the inside, which is what a
practitioner would actually have.

EFFECT SIZE, NOT JUST SIGNIFICANCE
----------------------------------
Comparisons use Cliff's delta, a rank-based effect size in [-1, 1]. With
several thousand nodes almost any difference is "significant", so a p-value
alone would rank every variable as important. Cliff's delta says how large the
separation actually is, and being rank-based it is immune to the heavy tails
that would wreck a t-test on these quantities. p-values are reported alongside
but the table is sorted by effect size.

Run:
    python analyse_failures.py [--targets spread_mean,betweenness] [--tail 0.05]
                               [--arm reported|raw]

OBJECTIVE ARM (added 2026-09-11, Claude Opus 5, Task 6 audit finding P2-03)
Betweenness has two prediction archives: the top-level cache_oof_<tag>.npz is
the historical squared-error ("raw") forest, and estimators/
cache_oof_<tag>__rf_log1p.npz is the log1p-objective forest the study reports.
This script used to open the top-level file for every target, so the atlas and
fig2 described the raw arm while the Moran correlogram described the reported
one. It now reads each target's REPORTED arm by default (see
influence/oof_arms.py), records the arm in every result dict as
`objective_arm`, prints it in the header, and `--arm raw` reproduces the
historical (Finding 8-era) atlas, labelled.
"""
import argparse
import glob
import json
import os
import re

import numpy as np
import pandas as pd
from scipy.stats import rankdata, mannwhitneyu

from influence.oof_arms import arm_label, load_oof as load_oof_arm
from influence.preprocessing import load_edgelist
from influence import structure as st

FULL = "node+edge+subgraph"


# ---------------------------------------------------------------------------
# Residuals
# ---------------------------------------------------------------------------

def pct_rank(x: np.ndarray) -> np.ndarray:
    """Percentile rank in [0, 1]; 1.0 is the largest value. Ties averaged."""
    return rankdata(x, method="average") / len(x)


def standardise_residual(delta: np.ndarray, pct_true: np.ndarray,
                         n_bins: int = 20) -> np.ndarray:
    """
    Remove BOTH mechanical distortions from the residual: the level and the
    scale. What survives is structural.

    TRAP 1 - SHRINKAGE (the level)
    ------------------------------
    Any regression pulls predictions toward the middle: the truly top node is
    predicted a little low, the truly bottom node a little high. In rank space
    that gives high-influence nodes positive delta and low-influence nodes
    negative delta as a pure artefact of fitting. Take raw tails and the atlas
    reports that the under-predicted nodes are the influential ones - true,
    mechanical, and not a finding.

    TRAP 2 - HETEROSCEDASTICITY (the scale)
    ---------------------------------------
    This one is subtler and it bit us. Residual VARIANCE is far from constant:
    on ca-GrQc, degree-2 peripheral nodes are misranked much more loosely than
    well-connected ones, simply because there are thousands of near-tied
    peripheral nodes and almost nothing separates them. The tails of a residual
    with non-constant variance are then dominated by the high-variance region
    no matter what the structure is.

    Centring alone leaves that intact, and the symptom is unmistakable: BOTH
    tails profile identically. Before this fix, ca-GrQc's under-predicted and
    over-predicted groups both came out as low-degree (median 2 vs 4), low
    coreness, high boundary porosity. That is not two blind spots, it is one
    population - the periphery - showing up at both ends because that is where
    the residual is noisiest.

    THE FIX
    -------
    Bin on the true percentile and, within each bin, subtract the median and
    divide by the median absolute deviation. Both the expected residual and its
    typical size are estimated non-parametrically, so no functional form is
    assumed - the same spirit as `variance_residual` in targets.py, which
    decouples cascade variance from cascade mean for exactly this reason.

    A node then lands in a tail because it is misranked FAR RELATIVE TO HOW
    PRECISELY NODES LIKE IT CAN BE RANKED AT ALL, which is what "locality is
    blind to this particular node" has to mean if it means anything.
    """
    edges = np.unique(np.quantile(pct_true, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 3:
        return delta - np.median(delta)
    idx = np.clip(np.searchsorted(edges, pct_true, side="right") - 1,
                  0, len(edges) - 2)

    # Global fallback scale, for bins too degenerate to estimate one.
    global_mad = np.median(np.abs(delta - np.median(delta))) or 1.0

    adj = delta.astype(np.float64).copy()
    for b in range(len(edges) - 1):
        m = idx == b
        if not m.any():
            continue
        centred = delta[m] - np.median(delta[m])
        mad = np.median(np.abs(centred))
        adj[m] = centred / (mad if mad > 0 else global_mad)
    return adj


# Kept under the old name so nothing silently calls a function that no longer
# does what its name says.
remove_shrinkage = standardise_residual


def mean_delta(oof: dict, target: str, radius: int, y: np.ndarray,
               richness: str = FULL) -> tuple[np.ndarray, np.ndarray]:
    """
    Rank residual averaged over seeds, plus how often each node fell in the
    top/bottom tail.

    Returns (delta_bar, per_seed_delta) where per_seed_delta is (n_seeds, n).
    """
    keys = [k for k in oof
            if k.startswith(f"{target}|{radius}|{richness}|")]
    if not keys:
        return None, None
    pt = pct_rank(y)
    rows = [pt - pct_rank(oof[k]) for k in sorted(keys)]
    per_seed = np.vstack(rows)
    return per_seed.mean(axis=0), per_seed


# ---------------------------------------------------------------------------
# Effect size
# ---------------------------------------------------------------------------

def cliffs_delta(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """
    Cliff's delta and a two-sided Mann-Whitney p-value.

    Cliff's delta is P(a > b) - P(a < b), with ties counted as half. That is
    exactly what the Mann-Whitney U statistic already measures, so we derive it
    from U rather than doing the O(|a||b|) pairwise comparison:

        d = 2U / (|a| |b|) - 1

    Conventional reading: |d| < 0.15 negligible, < 0.33 small, < 0.47 medium,
    otherwise large.
    """
    if len(a) < 3 or len(b) < 3:
        return np.nan, np.nan
    if np.all(a == a[0]) and np.all(b == b[0]) and a[0] == b[0]:
        return 0.0, 1.0
    u, p = mannwhitneyu(a, b, alternative="two-sided")
    return 2.0 * u / (len(a) * len(b)) - 1.0, float(p)


def profile(values: dict[str, np.ndarray], mask: np.ndarray,
            rest: np.ndarray) -> pd.DataFrame:
    """Compare one group against the rest across every profiling variable."""
    rows = []
    for name, v in values.items():
        d, p = cliffs_delta(v[mask], v[rest])
        rows.append({"variable": name,
                     "median_group": float(np.median(v[mask])),
                     "median_rest": float(np.median(v[rest])),
                     "cliffs_d": d, "p": p})
    out = pd.DataFrame(rows)
    return out.reindex(out.cliffs_d.abs().sort_values(ascending=False).index)


def magnitude(d: float) -> str:
    a = abs(d)
    return ("negligible" if a < 0.15 else "small" if a < 0.33
            else "medium" if a < 0.47 else "LARGE")


# ---------------------------------------------------------------------------
# Profiling axes
# ---------------------------------------------------------------------------

def build_profile_vars(net, X: pd.DataFrame, Y: pd.DataFrame,
                       target: str) -> dict[str, np.ndarray]:
    """
    The axes the failing nodes get described on.

    GLOBAL axes are the explanatory ones - the model was denied them, so a
    large separation on one of them names something locality genuinely cannot
    see. LOCAL axes are context: they describe the failing node as it appears
    from inside its own neighbourhood.
    """
    core = st.core_numbers(net)
    dist_hub = st.distance_to_hubs(net, top_fraction=0.01)
    h3 = X["h_index_3"].to_numpy(dtype=np.float64)
    reach3 = X["reach_within_3"].to_numpy(dtype=np.float64)

    v: dict[str, np.ndarray] = {}

    # --- global: what the model could not see -----------------------------
    v["[G] coreness"] = core.astype(np.float64)
    # The H-index ladder approaches coreness FROM ABOVE:
    #     degree = h^(0) >= h^(1) >= h^(2) >= ... >= coreness
    # so h^(3) is always an over-estimate, and this gap is the amount by which
    # a bounded local view over-reads how deeply embedded the node is. A large
    # gap means "looks well-embedded from inside its own neighbourhood, is not
    # actually in a deep core" - precisely a locality illusion, and exactly the
    # kind of thing the atlas is for. Only the global core number reveals it.
    v["[G] h_index_3 - coreness (local over-read)"] = h3 - core
    v["[G] hops to nearest hub"] = dist_hub.astype(np.float64)
    if target != "betweenness" and "betweenness" in Y.columns:
        v["[G] betweenness"] = Y["betweenness"].to_numpy(dtype=np.float64)
    # Fraction of the network inside the 3-ball: how much of the graph the
    # node can see at all.
    v["[G] visible fraction (3-ball/n)"] = reach3 / net.n
    if "spread_mean" in Y.columns:
        # Cascade size relative to the visible ball. Above 1 means the average
        # cascade escapes everything the node could observe - the locality gap
        # in its most direct form (Angle 5).
        sm = Y["spread_mean"].to_numpy(dtype=np.float64)
        v["[G] spread / visible ball"] = sm / np.maximum(reach3, 1.0)

    # --- local: what the node looks like from inside -----------------------
    for col, label in [("degree", "degree"),
                       ("clustering_coefficient", "clustering"),
                       ("boundary_porosity", "boundary porosity"),
                       ("ego_betweenness", "ego betweenness"),
                       ("growth_ratio_3", "growth ratio r3"),
                       ("h_index_3", "h_index_3"),
                       # The features added to make the tier axis mean
                       # something. They describe kinds of local structure the
                       # table could not previously express, so they are the
                       # ones most likely to name a blind spot the older
                       # columns could only gesture at.
                       ("edge_overlap_mean", "edge overlap (mean)"),
                       ("edge_embeddedness_std", "edge embeddedness (std)"),
                       ("local_conductance_2", "2-ball conductance"),
                       ("ball2_density", "2-ball density"),
                       ("local_entropy_norm", "neighbourhood entropy")]:
        if col in X.columns:
            v[f"[L] {label}"] = X[col].to_numpy(dtype=np.float64)
    return v


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def show(title: str, table: pd.DataFrame, top: int = 8) -> None:
    print(f"\n  {title}")
    print(f"    {'variable':34s} {'median(grp)':>12s} {'median(rest)':>12s} "
          f"{'Cliff d':>8s}  {'size':<11s} {'p':>9s}")
    for _, r in table.head(top).iterrows():
        print(f"    {r.variable:34s} {r.median_group:12.4g} "
              f"{r.median_rest:12.4g} {r.cliffs_d:8.3f}  "
              f"{magnitude(r.cliffs_d):<11s} {r.p:9.2e}")


def compute(tag: str, target: str, tail: float = 0.05,
            arm: str | None = None) -> dict | None:
    """
    Everything the atlas needs for one (network, target), without printing.

    Separated from the reporting so the figure and the text report are computed
    by the same code rather than by two implementations that can drift.

    `arm` selects the objective arm of the predictions: None = the reported arm
    for this target, "raw" = the historical top-level archive. The arm actually
    read is returned as `objective_arm` so every downstream artifact can say
    which model it describes.
    """
    meta = json.load(open(f"cache_meta_{tag}.json"))
    X = pd.read_csv(f"cache_features_{tag}.csv")
    Y = pd.read_csv(f"cache_targets_{tag}.csv")
    if target not in Y.columns:
        return None
    net = load_edgelist(meta["provenance"]["source"].replace("\\", "/"))
    # "raw" is the only arm that exists for non-betweenness targets, so an
    # explicit --arm log1p must not be forced onto spread_*; None resolves to
    # each target's own reported arm.
    oof, arm_used = load_oof_arm(tag, target, None if arm in (None, "reported") else arm)
    if oof is None:
        return None

    max_hop = meta.get("max_hop", 3)
    y = Y[target].to_numpy(dtype=np.float64)
    delta, per_seed = mean_delta(oof, target, max_hop, y)
    if delta is None:
        return None

    n = len(delta)
    k = max(10, int(round(tail * n)))
    pt = pct_rank(y)

    # Tails are defined on the SHRINKAGE-ADJUSTED residual, so a node earns its
    # place by being misranked relative to others of similar true influence
    # rather than by being extreme. See remove_shrinkage.
    delta_adj = remove_shrinkage(delta, pt)
    order = np.argsort(delta_adj)
    under, over, rest = order[-k:], order[:k], order[k:-k]

    # How reproducible is tail membership across seeds? A node that only lands
    # in the tail on one split is noise, not a blind spot.
    per_seed_tail = np.zeros(n, dtype=int)
    for s in range(per_seed.shape[0]):
        adj_s = remove_shrinkage(per_seed[s], pt)
        per_seed_tail[np.argsort(adj_s)[-k:]] += 1
    stable = int((per_seed_tail[under] >= 8).sum())

    # Diagnostic: how much shrinkage was there to remove? If the raw and
    # adjusted tails coincide, shrinkage was not driving the result.
    raw_under = set(np.argsort(delta)[-k:].tolist())
    overlap = len(raw_under & set(under.tolist())) / k

    pv = build_profile_vars(net, X, Y, target)
    keys = sorted(kk for kk in oof
                  if kk.startswith(f"{target}|{max_hop}|{FULL}|"))
    pred_bar = np.mean([pct_rank(oof[kk]) for kk in keys], axis=0)

    res = {"tag": tag, "target": target, "n": n, "k": k, "max_hop": max_hop,
           "objective_arm": arm_used, "objective_label": arm_label(target, arm_used),
           "delta": delta, "delta_adj": delta_adj,
           "under": under, "over": over, "rest": rest,
           "stable": stable, "raw_overlap": overlap,
           "pct_true": pt, "pct_pred": pred_bar,
           "median_pct_true_under": float(np.median(pt[under])),
           "median_pct_true_over": float(np.median(pt[over])),
           "table_under": profile(pv, under, rest),
           "table_over": profile(pv, over, rest),
           # The directional contrast. Comparing each tail against the middle
           # tells you what makes a node hard to rank; comparing the tails
           # against EACH OTHER cancels everything they share and leaves only
           # what decides the SIGN of the error. That is the sharper question,
           # and it is robust to any remaining common structure in the tails.
           "table_direction": profile(pv, under, over)}

    d1, _ = mean_delta(oof, target, 1, y)
    if d1 is not None:
        # Compare like with like: both radii shrinkage-adjusted before the
        # improvement is measured.
        gain = np.abs(remove_shrinkage(d1, pt)) - np.abs(delta_adj)
        g_order = np.argsort(gain)
        res["mad_r1"] = float(np.abs(d1).mean())
        res["table_rescued"] = profile(pv, g_order[-k:], g_order[k:-k])
    return res


def analyse(tag: str, targets: list[str], tail: float,
            arm: str | None = None) -> dict:
    out = {}
    header_done = False
    for target in targets:
        r = compute(tag, target, tail, arm)
        if r is None:
            continue
        if not header_done:
            print("\n" + "=" * 78)
            print(f"{tag}   n={r['n']:,}   reference: r={r['max_hop']}, {FULL}")
            print("=" * 78)
            header_done = True

        print(f"\n--- target: {target} ---")
        print(f"  {r['objective_label']}")
        print(f"  mean |delta| = {np.abs(r['delta']).mean():.4f}   "
              f"tail size = {r['k']} nodes ({100*r['k']/r['n']:.1f}%)")
        print(f"  residual STANDARDISED within influence bins (level + scale); "
              f"overlap with raw tail {100*r['raw_overlap']:.0f}%")
        print(f"  median true percentile:  under={r['median_pct_true_under']:.2f}"
              f"   over={r['median_pct_true_over']:.2f}"
              f"   (near 0.5 = shrinkage is not driving the split)")
        print(f"  in the tail for >=8 of 10 seeds: "
              f"{r['stable']}/{r['k']} ({100*r['stable']/r['k']:.0f}%)")

        show("UNDER-PREDICTED vs the well-ranked middle "
             "(what makes a node hard to rank)", r["table_under"])
        show("OVER-PREDICTED vs the well-ranked middle", r["table_over"])
        show("UNDER vs OVER - the DIRECTIONAL contrast "
             "(what decides the sign of the error)", r["table_direction"])
        if "table_rescued" in r:
            print(f"\n  WHAT HOPS 2-{r['max_hop']} RESCUE  (mean |delta| "
                  f"{r['mad_r1']:.4f} at r=1 -> "
                  f"{np.abs(r['delta']).mean():.4f} at r={r['max_hop']})")
            show("MOST RESCUED by the extra hops", r["table_rescued"], top=5)
        out[target] = r
    return out


def discover() -> list[str]:
    tags = []
    for path in sorted(glob.glob("cache_oof_*.npz")):
        tags.append(re.match(r"cache_oof_(.+)\.npz$",
                             os.path.basename(path)).group(1))
    return tags


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="spread_mean,betweenness")
    ap.add_argument("--tail", type=float, default=0.05,
                    help="fraction of nodes in each failure tail")
    ap.add_argument("--networks", default="")
    ap.add_argument("--arm", default="reported", choices=["reported", "raw"],
                    help="objective arm of the predictions: each target's "
                         "reported arm (default; log1p for betweenness) or "
                         "the historical raw squared-error archive")
    args = ap.parse_args()

    tags = args.networks.split(",") if args.networks else discover()
    if not tags:
        raise SystemExit("no cache_oof_*.npz found - re-run stage2_sweep.py")

    targets = args.targets.split(",")
    print(f"objective arm: {args.arm}"
          + ("  (betweenness from estimators/cache_oof_<tag>__rf_log1p.npz)"
             if args.arm == "reported" else
             "  (betweenness from the historical top-level cache_oof_<tag>.npz)"))
    results = {}
    for tag in tags:
        results[tag] = analyse(tag, targets, args.tail, args.arm)

    # The raw-arm atlas is a historical artifact and must not overwrite the
    # reported one that make_fig2.py reads.
    atlas = "cache_failure_atlas.npy" if args.arm == "reported" else "cache_failure_atlas_raw.npy"
    np.save(atlas, results, allow_pickle=True)
    print(f"\nsaved {atlas} (for make_fig2.py)")


if __name__ == "__main__":
    main()

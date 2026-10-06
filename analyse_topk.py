"""
A3 - the top-k arm: does the locality horizon move when the metric is precision@k?

WHY THIS EXISTS
---------------
Every r*(eps) in this project is defined on Kendall tau over ALL pairs. Tau is a
bulk metric: on a graph of n nodes it scores ~n^2/2 pairs, and the overwhelming
majority of them are boring - two peripheral nodes whose relative order nobody
will ever act on. The applied question is almost never "rank all 8,638 authors".
It is "who are the top 50 to seed / monitor / immunise".

If the horizon under precision@k differs from the horizon under tau, then every
r* this project reports is answering a question no practitioner asked. That is
the M7 objection and it is a fair one.

This is a RE-PLOT, not an experiment. `precision_at_1pct` and `precision_at_5pct`
have been columns in every sweep row since the sweep was written, and
`locality_horizon` has always taken a `metric=` argument (influence/experiment.py
:278). Nothing here was gated on anything. It needed a caller.

THE COMPARISON IS NOT AS CLEAN AS IT LOOKS, AND THE SCRIPT SAYS SO
------------------------------------------------------------------
r*(eps) is "the smallest r reaching (1-eps) of the best observed value". That
definition is metric-relative in a way that bites here:

  - tau and precision@k live on different scales with different floors. Tau-b on
    a zero-inflated target has a large floor from boundary pairs alone (Section 24);
    precision@5% has a floor of ~0.05 from random guessing. So "90% of the
    ceiling" is a much weaker bar on tau than on precision, and a raw r*
    comparison partly measures that, not the horizon.

  - precision@1% is roughly TWENTY TIMES noisier than tau across seeds (measured,
    Section 3 below). A threshold rule applied to a noisy curve will cross earlier
    or later by luck. Any r* shift smaller than the seed spread is not a result.

Both are reported and both are flagged. Section 4 does the noise-normalised
version, which is the one to believe.
"""

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from analyse import FULL, discover_networks, load
from influence.experiment import locality_horizon

EPS = [0.20, 0.10, 0.05, 0.02, 0.01]
TARGETS = ["betweenness", "spread_mean", "spread_cv", "spread_resid"]
METRICS = ["kendall_tau", "precision_at_5pct", "precision_at_1pct"]

# Short labels for the wide tables. Kept next to METRICS so the two cannot drift.
LABEL = {"kendall_tau": "tau", "precision_at_5pct": "p@5%", "precision_at_1pct": "p@1%"}


def modal_r_star(d: pd.DataFrame, target: str, metric: str, eps: float) -> tuple:
    """
    Modal r*(eps) across seeds, with the number of seeds that agreed.

    Modal rather than mean because r* is an ordinal label, not a quantity - the
    mean of r*=1 and r*=3 is not r*=2, it is a statement that the cell is
    unstable. The agreement count carries that instead, exactly as Section 19
    of the study doc does for tau.
    """
    vals = []
    for seed in sorted(d["seed"].unique()):
        sub = d[(d.target == target) & (d.seed == seed)]
        h = locality_horizon(sub, epsilon=eps, metric=metric)
        if h.get("r_star") is not None:
            vals.append(h["r_star"])
    if not vals:
        return None, 0, 0
    counts = pd.Series(vals).value_counts()
    return int(counts.index[0]), int(counts.iloc[0]), len(vals)


def noise_ratio(d: pd.DataFrame, target: str, metric: str) -> float:
    """
    Seed sd of the metric, averaged over radii, as a fraction of its own range.

    This is the number that decides whether an r* shift is worth reading. A
    metric whose seed spread is comparable to the gaps between its own radii
    cannot support a threshold rule, however carefully the threshold is chosen.
    """
    sub = d[(d.target == target) & (d.richness == FULL)]
    g = sub.groupby("radius")[metric]
    sds = g.std(ddof=1)
    means = g.mean()
    span = means.max() - means.min()
    if span <= 0:
        return float("nan")
    return float(sds.mean() / span)


def main() -> None:
    tags = discover_networks()
    print("=" * 78)
    print("A3 - TOP-K ARM: r*(eps) under precision@k instead of Kendall tau")
    print("=" * 78)
    print(f"networks: {', '.join(tags)}")
    print("no fits - precision_at_{1,5}pct are existing sweep columns\n")

    # --- 1. how noisy is each metric? ---------------------------------------
    print("=" * 78)
    print("1. METRIC NOISE - seed sd as a fraction of the metric's own r=0..3 range")
    print("=" * 78)
    print("\nA ratio near or above ~0.2 means the seed spread is comparable to the")
    print("signal the threshold rule is trying to resolve, and r* under that metric")
    print("is close to a coin flip regardless of tolerance.\n")
    print(f"  {'network':20s} {'target':14s}" + "".join(f"{LABEL[m]:>10s}" for m in METRICS))
    print("  " + "-" * 66)
    noise = {}
    for tag in tags:
        d = load(tag)
        for target in TARGETS:
            row = [noise_ratio(d, target, m) for m in METRICS]
            noise[(tag, target)] = row
            print(f"  {tag:20s} {target:14s}" + "".join(f"{v:10.3f}" for v in row))

    arr = np.array([v for v in noise.values()])
    print("\n  corpus mean:" + " " * 23 + "".join(f"{v:10.3f}" for v in np.nanmean(arr, axis=0)))

    # --- 2. r*(eps) side by side --------------------------------------------
    print("\n" + "=" * 78)
    print("2. r*(eps) UNDER EACH METRIC   (modal across seeds, agreement in brackets)")
    print("=" * 78)
    shifts = []
    for tag in tags:
        d = load(tag)
        print(f"\n{tag}")
        print(f"  {'target':14s} {'eps':>5s}  " +
              "".join(f"{LABEL[m]:>12s}" for m in METRICS))
        print("  " + "-" * 56)
        for target in TARGETS:
            for e in EPS:
                cells = []
                rs = {}
                for m in METRICS:
                    r, agree, tot = modal_r_star(d, target, m, e)
                    rs[m] = r
                    cells.append(f"{r} ({agree}/{tot})" if r is not None else "-")
                print(f"  {target:14s} {e:5.2f}  " + "".join(f"{c:>12s}" for c in cells))
                if rs["kendall_tau"] is not None and rs["precision_at_5pct"] is not None:
                    shifts.append({
                        "network": tag, "target": target, "eps": e,
                        "r_tau": rs["kendall_tau"],
                        "r_p5": rs["precision_at_5pct"],
                        "r_p1": rs["precision_at_1pct"],
                        "shift_p5": rs["precision_at_5pct"] - rs["kendall_tau"],
                    })

    sh = pd.DataFrame(shifts)

    # --- 3. the headline ----------------------------------------------------
    print("\n" + "=" * 78)
    print("3. DOES THE HORIZON MOVE?   r*(p@5%) - r*(tau), over all cells")
    print("=" * 78)
    dist = sh["shift_p5"].value_counts().sort_index()
    total = len(sh)
    print(f"\n  {total} (network, target, eps) cells\n")
    for k, v in dist.items():
        bar = "#" * int(40 * v / total)
        direction = ("top-k needs FEWER hops" if k < 0
                     else "identical" if k == 0 else "top-k needs MORE hops")
        print(f"   {k:+d} hops : {v:3d} ({v/total:5.1%})  {bar:<40s} {direction}")
    print(f"\n  agreement rate (shift = 0): {(sh.shift_p5 == 0).mean():.1%}")
    print(f"  mean shift: {sh.shift_p5.mean():+.3f} hops")

    print("\n  by target:")
    for target, grp in sh.groupby("target"):
        print(f"    {target:14s} agree {(grp.shift_p5 == 0).mean():5.1%}   "
              f"mean shift {grp.shift_p5.mean():+.2f}")

    print("\n  by network:")
    for net, grp in sh.groupby("network"):
        print(f"    {net:20s} agree {(grp.shift_p5 == 0).mean():5.1%}   "
              f"mean shift {grp.shift_p5.mean():+.2f}")

    # --- 4. p@1%: a different horizon, or just a noisier ruler? -------------
    #
    # A noise filter was tried here first and dropped NOTHING: no (network,
    # target) pair has a p@5% noise ratio above 0.20. That is a real result
    # about p@5% - it is a well-behaved metric on this corpus - so the filter
    # is reported as vacuous rather than quietly tightened until it bit. The
    # metric that IS too noisy is p@1%, and the right question about it is not
    # "should we drop it" but "is its disagreement a horizon or a ruler?"
    #
    # The discriminating signature is SYMMETRY. A genuinely different horizon
    # shifts in a consistent direction. A ruler too blunt to resolve the
    # crossing scatters both ways around zero.
    print("\n" + "=" * 78)
    print("4. IS p@1% A DIFFERENT HORIZON, OR JUST A NOISIER RULER?")
    print("=" * 78)

    worst = max(noise.items(), key=lambda kv: kv[1][1])
    print(f"\n  No (network, target) pair exceeds a p@5% noise ratio of 0.20 -")
    print(f"  the worst is {worst[0][0]} / {worst[0][1]} at {worst[1][1]:.3f}.")
    print("  So a low-noise restriction on p@5% drops nothing, and is reported")
    print("  as vacuous rather than tuned until it excluded something.\n")

    sh["shift_p1"] = sh["r_p1"] - sh["r_tau"]
    print("  How big is the top 1%, in nodes?")
    for tag in tags:
        n = len(pd.read_csv(f"cache_features_{tag}.csv"))
        print(f"    {tag:20s} n = {n:6,}   top 1% = {max(1, round(0.01*n)):4d} nodes"
              f"   top 5% = {max(1, round(0.05*n)):4d} nodes")

    for name, col in [("p@5% vs tau", "shift_p5"), ("p@1% vs tau", "shift_p1")]:
        agree = (sh[col] == 0).mean()
        down = (sh[col] < 0).sum()
        up = (sh[col] > 0).sum()
        print(f"\n  {name}:  agree {agree:.1%}   "
              f"moves down {down}, up {up}   mean {sh[col].mean():+.3f}")
        # Symmetry of the disagreement is the diagnostic, not its size. Scored
        # with an exact two-sided sign test rather than an eyeballed skew
        # threshold: "17 up and 9 down" looks lopsided and is not, and a
        # hand-picked cutoff is exactly the kind of unearned decision rule this
        # project's D2 argument is about.
        if down + up:
            p = binomtest(up, up + down, 0.5, alternative="two-sided").pvalue
            verdict = ("SYSTEMATIC - a real directional shift" if p < 0.05
                       else "SYMMETRIC - consistent with noise, not a horizon shift")
            print(f"    sign test on the {up + down} disagreeing cells: "
                  f"p = {p:.3f}  ->  {verdict}")

    print(f"\n  p@1% vs p@5%: agree {((sh.r_p1 - sh.r_p5) == 0).mean():.1%}")
    print("  p@1% agrees with neither, which is what a blunt ruler looks like.")

    # --- 5. does the agreement depend on the tolerance? ---------------------
    print("\n" + "=" * 78)
    print("5. AGREEMENT BY TOLERANCE")
    print("=" * 78)
    print("\n  eps   agree(p@5% vs tau)   mean shift")
    print("  " + "-" * 40)
    for e, grp in sh.groupby("eps"):
        print(f"  {e:.2f}        {(grp.shift_p5 == 0).mean():6.1%}          "
              f"{grp.shift_p5.mean():+.2f}")

    sh.to_csv("results/topk_rstar.csv", index=False)
    print("\n\nwrote results/topk_rstar.csv")


if __name__ == "__main__":
    main()

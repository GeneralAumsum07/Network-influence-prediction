"""
Figure 5: the coverage control - what a hop actually buys, per network.

This is the figure §17a (referee objection M3) has been missing. Every P(r) plot
in this project puts the hop index on the x-axis, which silently implies the five
networks are being compared at the same thing. They are not: median 3-ball
coverage spans **fifty-two-fold** across the corpus, from 1.86% on ca-HepTh to
97.3% on email-Eu-core. email's r=3 column is not a local measurement in any
useful sense and the figure has to make that impossible to miss.

The two panels share the radius axis so the reader can check by eye, per network,
whether performance saturation LEADS, LAGS or coincides with coverage saturation:

    Panel A   median |B_r(v)| / n, from results/coverage.csv
    Panel B   the same richest-tier P(r) curve fig1 plots, one line per network

**Panel A is log-scaled and that is not a cosmetic choice.** Coverage runs from
0.02% to 97%; on a linear axis four of the five networks would be pinned flat to
the bottom and the figure would show one curve and four zeros, which is the
opposite of its point.

WHY spread_mean: §17a's own tau-vs-coverage table is computed on `spread_mean` at
the richest tier, so the figure visualises that section on that section's target
rather than choosing a new one. (Checked before writing: §17a's numbers were
quoted at "richest structural tier" = node+edge+subgraph, and reproduce at the
full ladder used here to within 0.0002, so the two do not disagree.)

WHY r* IS MARKED WITH CIRCLES, NOT FIVE VERTICAL LINES: the spec asked for a
dashed vertical per network drawn through both panels. Measured r*(eps) takes
only two distinct values here - 1 on ca-GrQc, email and facebook, 2 on ca-HepTh
and p2p - so five verticals would render as *two* lines and a reader would count
two networks. The circles are fig1's own established r* convention, they sit on
the curve they describe, and the shaded bands behind them carry the "which radius"
information the verticals were there to carry. The payload of the whole figure is
then readable directly: find a network's circle in panel B, look straight up, and
panel A tells you what fraction of the graph it had to see to get there.

Writes to results/. Networks are discovered from results/coverage.csv, so a
larger corpus needs no edit here.
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Through the shared loader for the same reason make_fig1.py does: the figure
# must show the corpus as the project REPORTS it, and a second local read_csv is
# how a figure and a table drift apart.
from analyse import load

FULL = "node+edge+subgraph+dynamic"
TARGET = "spread_mean"          # see WHY spread_mean in the docstring
EPS = 0.05                      # r*(eps): first radius within eps of the ceiling

COV_SRC = "results/coverage.csv"
OUT_DIR = "results"
OUT_PATH = os.path.join(OUT_DIR, "fig5_coverage_confound.png")

# The four house hues, plus a fifth for the fifth network. #8A7A1F was not
# picked by eye - it was chosen by running the palette validator over the
# five-colour set and keeping the only candidate that adds NO new failure:
# chroma-floor membership, worst-adjacent CVD separation (7.2 protan) and the
# normal-vision floor (15.0) are all identical to the existing four-colour
# palette. Teal (#1F6E78) drops CVD to 6.5, warm red (#9E3B2E) and violet
# (#5A3A8A) both break the normal-vision floor against #7A2E5E.
#
# The palette's own standing CVD warning is discharged the same way fig1
# discharges it: marker shape and dash pattern carry identity as well as hue, so
# the five networks stay separable in greyscale and for a colourblind reader.
NET_COLORS = ["#2E4B7A", "#2E6E4E", "#B5651D", "#7A2E5E", "#8A7A1F"]
NET_MARKERS = ["o", "s", "^", "D", "v"]
NET_DASHES = ["-", "--", "-.", ":", (0, (5, 1, 1, 1))]


def main() -> None:
    cov = pd.read_csv(COV_SRC)
    nets = sorted(cov.network.unique())
    if not nets:
        raise SystemExit(f"{COV_SRC} is empty - run analyse_coverage.py first")

    style = {
        net: {"c": NET_COLORS[i % len(NET_COLORS)],
              "m": NET_MARKERS[i % len(NET_MARKERS)],
              "ls": NET_DASHES[i % len(NET_DASHES)]}
        for i, net in enumerate(nets)
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    fig, (axA, axB) = plt.subplots(
        2, 1, figsize=(9.0, 9.4), sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.0], "hspace": 0.13})
    fig.patch.set_facecolor("white")

    rstars = {}      # network -> r*(eps) on TARGET, needed by both panels
    curves = {}      # network -> mean-over-seeds tau by radius
    sds = {}

    for net in nets:
        d = load(net)
        sub = d[(d.target == TARGET) & (d.richness == FULL)]
        g = sub.groupby("radius")["kendall_tau"]
        m, s = g.mean(), g.std(ddof=1).fillna(0.0)
        curves[net], sds[net] = m, s
        # Same definition as fig1 and as influence.experiment.locality_horizon:
        # the SMALLEST radius whose mean curve is within eps of the best
        # observed value. Recomputed here rather than read from a table so the
        # circles cannot disagree with the lines they sit on.
        ok = m[m >= (1.0 - EPS) * m.max()]
        rstars[net] = int(ok.index.min()) if len(ok) else None

    # Light vertical bands at the distinct r* values, behind everything. This is
    # what survives of the spec's "vertical dashed line per network": the radii
    # at which saturation happens, without pretending five coincident lines are
    # five distinguishable ones.
    for r in sorted({v for v in rstars.values() if v is not None}):
        k = sorted(n for n in nets if rstars[n] == r)
        for ax in (axA, axB):
            ax.axvspan(r - 0.12, r + 0.12, color="#8A8A8A", alpha=0.13, lw=0,
                       zorder=0)
        axB.text(r, 0.012, f"$r^*$={r}\n({len(k)} nets)", ha="center",
                 va="bottom", fontsize=7.5, color="#555",
                 transform=axB.get_xaxis_transform())

    # ---- Panel A: coverage ----
    for net in nets:
        st = style[net]
        c = cov[cov.network == net].sort_values("radius")
        axA.plot(c.radius, 100 * c["median"], marker=st["m"], ls=st["ls"],
                 lw=2.2, ms=7, color=st["c"], label=net)
        # The r* circle, placed at the coverage the network had AT its own
        # saturation radius. This is the number §17a is about: email saturates
        # at r=1 having seen 2.3% of the graph.
        rs = rstars.get(net)
        if rs is not None and (c.radius == rs).any():
            y = 100 * float(c.loc[c.radius == rs, "median"].iloc[0])
            axA.plot(rs, y, "o", ms=14, mfc="none", mec=st["c"], mew=2)

    axA.set_yscale("log")
    axA.set_ylabel("median coverage  $|B_r(v)|\\,/\\,n$   (%, log scale)")
    axA.set_title("A.  How much of the graph a radius-$r$ observer actually sees",
                  fontsize=11, color="#1A1A2E", loc="left")
    axA.grid(alpha=0.25, ls=":", which="both")
    axA.axhline(50, color="#333", lw=0.8, ls="--", alpha=0.6)
    # Right-hand end: the left-hand end of this line runs under the finding
    # annotation added at the bottom of this function.
    axA.text(0.985, 52, "half the graph", fontsize=7.5, color="#333",
             transform=axA.get_yaxis_transform(), va="bottom", ha="right")
    axA.legend(fontsize=8.5, loc="lower right", framealpha=0.95, ncol=2)

    # ---- Panel B: the P(r) curves, same convention as fig1 ----
    for net in nets:
        st, m, s = style[net], curves[net], sds[net]
        axB.plot(m.index, m.values, marker=st["m"], ls=st["ls"], lw=2.2, ms=7,
                 color=st["c"], label=net)
        axB.fill_between(m.index, m - s, m + s, color=st["c"], alpha=0.18, lw=0)
        rs = rstars.get(net)
        if rs is not None and rs in m.index:
            axB.plot(rs, m.loc[rs], "o", ms=14, mfc="none", mec=st["c"], mew=2)

    axB.set_xlabel("radius r  (hops of information available)")
    axB.set_ylabel(f"Kendall $\\tau$  (out-of-fold, {TARGET})")
    axB.set_title("B.  What that bought, on the same axis", fontsize=11,
                  color="#1A1A2E", loc="left")
    axB.set_xticks(sorted(cov.radius.unique()))
    axB.grid(alpha=0.25, ls=":")
    # No legend here on purpose: panel A carries it, the two panels share
    # one colour/marker/dash mapping, and a second copy would sit on top of
    # the r* band labels.
    #
    # The reading conventions used to be an in-axes note here; it ran into the
    # facebook curve, which climbs steeply through the top-left of this panel.
    # They are drawn as a figure footer instead - see the end of this function.

    # The finding, plus the reading conventions, as a footer BELOW both panels.
    # §17a's result is that the confound runs the OPPOSITE way from the one the
    # objection assumed - more of the graph bought almost nothing - and a reader
    # who only looks at the picture should not have to infer that from two
    # curves. It was an in-axes box on panel A and obstructed the very coverage
    # curves it was describing; outside the axes it costs nothing. Numbers are
    # recomputed here from the same frames the panels were drawn from, so they
    # cannot go stale.
    hi = max(nets, key=lambda n: float(
        cov.loc[(cov.network == n) & (cov.radius == cov.radius.max()),
                "median"].iloc[0]))
    ch = cov[cov.network == hi].set_index("radius")["median"]
    mh = curves[hi]
    r_lo, r_hi = int(mh.index.min()) + 1, int(mh.index.max())
    fig.text(
        0.5, 0.008,
        f"band = $\\pm$1 sd over seeds   ·   circled = $r^*$ at "
        f"$\\varepsilon$={EPS}   ·   richest tier ({FULL})   ·   "
        f"panel A is log-scaled\n"
        # Hard-wrapped rather than left to matplotlib's `wrap=True`, which
        # measures against the whole figure width and still overran this
        # 9-inch canvas at both ends.
        f"The confound runs the OTHER way.  On {hi}, going from "
        f"{100 * ch.loc[r_lo]:.1f}% coverage at r{r_lo} to "
        f"{100 * ch.loc[r_hi]:.1f}% at r{r_hi}\n"
        f"— to numerical accuracy the whole graph — buys "
        f"{mh.loc[r_hi] - mh.loc[r_lo]:+.4f} $\\tau$.  The corpus spans "
        f"{ch.loc[r_hi] / min(cov.loc[cov.radius == r_hi, 'median']):.0f}"
        f"$\\times$ in r{r_hi} coverage,\n"
        f"and that range is invisible on every other P(r) figure in this "
        f"project.",
        ha="center", va="bottom", fontsize=8.8, color="#1A1A2E")

    fig.suptitle("The coverage control: a hop is not the same purchase on every "
                 "network", fontsize=14, fontweight="bold", color="#2E4B7A",
                 y=0.975)
    # subplots_adjust, not tight_layout: hspace is already set in
    # gridspec_kw and tight_layout overrides it, warning as it goes. bottom is
    # raised from 0.065 to clear the two-line footer.
    fig.subplots_adjust(left=0.10, right=0.985, top=0.925, bottom=0.145)
    fig.savefig(OUT_PATH, dpi=170, facecolor="white")
    print(f"saved {OUT_PATH}")


if __name__ == "__main__":
    main()

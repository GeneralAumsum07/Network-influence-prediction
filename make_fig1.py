"""
Figure 1: the locality budget curve - the plot the supervisor asked for.

Now with error bars, which is the whole point. The figure exists to argue that
the radius is a MEASURED quantity; a measurement drawn without its uncertainty
argues the opposite of what we intend. Bands are +/- 1 sd across seeds, and the
marginal-gain bars use the PAIRED per-seed difference, so the error bar shown
is the uncertainty on the gain itself rather than the difference of two
independent error bars.

Writes to results/. Networks are discovered from sweep_*.csv rather than
hard-coded, so the synthetic corpus does not require editing this file.
"""
import json
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Through the shared loader, not a local read_csv. This figure is the artefact
# people actually look at, so it must show the corpus as the project REPORTS it
# - which since 2026-09-04 means betweenness from the log1p objective. It also
# retires a second copy of the de-duplication rule that used to live here; two
# copies is how the figure and the tables eventually disagree, which is exactly
# the make_fig2.py incident this project already had once.
# discover_networks is imported rather than re-implemented (Task 6 finding
# P3-06, Claude Opus 5, 2026-09-12): this file used to carry its own copy of the
# sweep_*.csv glob, and two copies of a discovery rule are how a figure and the
# tables it is meant to match end up reading different corpora.
from analyse import discover_networks, load

# The richest rung. Changed 2026-09-06 from "node+edge+subgraph" to the full
# ladder: the figure was showing the second-richest tier while every table in the
# study doc reports the richest, which is the same figure-vs-tables divergence
# the header above warns about. Checked before switching: 0 of 20 r* cells move
# and the peak tau shifts by at most 0.0013, so no published number is affected.
FULL = "node+edge+subgraph+dynamic"
COLORS = {"spread_mean": "#2E4B7A", "spread_cv": "#B5651D",
          "betweenness": "#2E6E4E", "spread_resid": "#7A2E5E"}
# Secondary encoding, and it is not decoration. The house palette's worst
# adjacent pair under simulated protanopia is betweenness (#2E6E4E) against
# spread_cv (#B5651D) at dE ~7.2 - inside the 6-8 band that is admissible ONLY
# when identity is carried by something besides hue. Marker shape and dash
# pattern carry it here, so the four targets stay separable in greyscale print
# and for a red-green colourblind reader. Do not drop these to "clean up" the
# plot without repainting the palette first.
#
# VALIDATED 2026-09-07 (Rachit): the house system passes and is EXTENDED, not replaced.
# Checked across fig1-3, fig5, fig6. Most series are redundantly encoded - colour plus marker
# shape plus linestyle - and that redundancy, not the particular hues, is what carries the
# colourblind-safety burden.
#   CORRECTED 2026-09-07 after review: the original wording here said EVERY series in every
#   figure is redundantly encoded. That is false. make_fig3.py's per-method line series all
#   share the same "o-" marker and dash, and fig2's residual scatter categories are
#   colour-only. Both are logged in those files. The verdict below still stands - the system
#   is coherent and worth extending rather than replacing - but it rests on the palette plus
#   MOSTLY-redundant encoding, not on a property that holds everywhere. fig5 reuses this blue/green/
# orange for its first three networks and adds maroon and olive for the other two, each with
# its own marker and dash; fig6 follows the blue = "primary/expected" vs orange = "the
# surprising contrast case" convention already set by fig2 and fig3.
#
# The earlier suggestion to default to a named palette (Okabe-Ito) is therefore WITHDRAWN.
# It was made before there was a real system to inspect. Switching now would mean reworking
# fig1-3 for no accessibility gain, at the cost of consistency across the whole set. Do not
# reopen this without new evidence of an actual legibility failure.
#
# One known gap, minor and deliberately not scheduled: the scatter panels in fig2/fig3
# (over-predicted / under-predicted / well-predicted) separate those three categories by
# colour ALONE, with no marker-shape difference - the single place this discipline slipped.
# Blue/orange is among the more robust pairs across colourblindness types, so practical risk
# is low. Add a shape distinction if those panels are ever revised; it does not warrant a
# dedicated task.
MARKERS = {"spread_mean": "o", "betweenness": "s",
           "spread_cv": "^", "spread_resid": "D"}
DASHES = {"spread_mean": "-", "betweenness": "--",
          "spread_cv": "-.", "spread_resid": ":"}
HATCH = {"spread_mean": "", "betweenness": "//",
         "spread_cv": "..", "spread_resid": "xx"}
LABELS = {"spread_mean": "Spread influence (mean)",
          "spread_cv": "Spread volatility (CV)",
          "betweenness": "Bridge influence (betweenness)",
          "spread_resid": "Volatility residual (mean removed)"}
ORDER = ["spread_mean", "betweenness", "spread_cv", "spread_resid"]

# The panel that gets the headline annotated on it, and the two targets the
# headline contrasts. Named here rather than inline so that a corpus without
# ca-GrQc simply draws no annotation instead of raising.
CAPTION_NET = "ca-GrQc"

OUT_DIR = "results"
OUT_PATH = os.path.join(OUT_DIR, "fig1_locality_budget.png")


def main() -> None:
    nets = discover_networks()
    if not nets:
        raise SystemExit("no sweep_*.csv found - run stage2_sweep.py first")

    os.makedirs(OUT_DIR, exist_ok=True)
    ncols = len(nets)
    fig, axes = plt.subplots(2, ncols, figsize=(5.5 * ncols, 8.6), squeeze=False)
    fig.patch.set_facecolor("white")

    # Shared y-limits computed from the data, so a curve that scores low is
    # never silently clipped off the axis.
    lo, hi = 1.0, 0.0
    for tag in nets:
        d = load(tag)
        v = d[d.richness == FULL]["kendall_tau"]
        lo, hi = min(lo, float(v.min())), max(hi, float(v.max()))
    pad = 0.05 * max(hi - lo, 0.1)
    ylim = (max(-1.0, lo - pad), min(1.0, hi + pad))

    # Filled in by the CAPTION_NET panel below; stays empty (and the footer
    # simply omits the line) on a corpus that does not contain that network.
    headline = ""

    for col, tag in enumerate(nets):
        d = load(tag)
        try:
            meta = json.load(open(f"cache_meta_{tag}.json"))
            subtitle = (f"n={meta['n']:,}  $\\langle k \\rangle$="
                        f"{meta['mean_degree']:.1f}  "
                        f"p={meta['multiple']}$\\times\\beta_c$")
        except FileNotFoundError:
            subtitle = ""

        targets = [t for t in ORDER if t in set(d.target)]

        # ---- top row: P(r) with seed spread ----
        ax = axes[0, col]
        curves = {}          # target -> mean-over-seeds tau, indexed by radius
        sds = {}             # target -> sd-over-seeds, same index
        for target in targets:
            sub = d[(d.target == target) & (d.richness == FULL)]
            g = sub.groupby("radius")["kendall_tau"]
            m, s = g.mean(), g.std(ddof=1).fillna(0.0)
            curves[target], sds[target] = m, s
            c = COLORS.get(target, "#555")
            ax.plot(m.index, m.values, marker=MARKERS.get(target, "o"),
                    ls=DASHES.get(target, "-"), lw=2.2, ms=7, color=c,
                    label=LABELS.get(target, target))
            ax.fill_between(m.index, m - s, m + s, color=c, alpha=0.18, lw=0)

            # r* at eps=0.05, from the mean curve
            ceil = m.max()
            ok = m[m >= 0.95 * ceil]
            if len(ok):
                rs = int(ok.index.min())
                ax.plot(rs, m.loc[rs], "o", ms=14, mfc="none", mec=c, mew=2)

        # ---- the headline, computed here, DRAWN BELOW THE FIGURE ----
        # Angle 2's quotable result is that targets have different horizons on
        # the SAME network, and until now it lived only in prose. Every number
        # is recomputed from the curves just plotted rather than pasted in, so
        # the caption cannot drift away from the figure it describes.
        #
        # It is emitted as a figure-level footer rather than an in-axes box:
        # every quadrant of the ca-GrQc panel has a curve running through it, so
        # an in-axes annotation necessarily sits on top of data. Outside the
        # axes it obstructs nothing and stays just as close to the panel.
        #
        # NOTE on what this says. An earlier draft of this caption (and the
        # figures spec that requested it) claimed the contrast is "betweenness
        # flat by r=1, spread_mean still climbing at r=3". That is FALSE at the
        # richest tier: spread_mean's r* is also 1, and it gains only +0.024
        # from r1 to r3. The real contrast is betweenness against the two
        # VOLATILITY targets, which gain an order of magnitude more.
        if tag == CAPTION_NET and {"betweenness", "spread_cv"} <= set(curves):
            def _gain(t: str) -> float:
                m = curves[t]
                return float(m.loc[m.index.max()] - m.loc[sorted(m.index)[1]])

            g_bet = _gain("betweenness")
            vol = [t for t in ("spread_cv", "spread_resid") if t in curves]
            g_vol = [_gain(t) for t in vol]
            # 2 sd over seeds at the deepest radius - the project's own
            # significance bar. Quoted so "flat" is a comparison against the
            # noise floor rather than an eyeball judgement.
            bar = 2 * float(sds["betweenness"].loc[
                curves["betweenness"].index.max()])
            headline = (
                f"{tag} — same network, different horizons:  betweenness gains "
                f"only {g_bet:+.3f} $\\tau$ from r1$\\to$r3 (2 sd = {bar:.3f}), "
                f"so it is done at r=1;  the two volatility targets gain "
                f"{min(g_vol):+.3f} to {max(g_vol):+.3f}, "
                f"~{min(g_vol) / g_bet:.0f}$\\times$ more, and are still "
                f"climbing at r=3.")

        ax.set_xlabel("radius r  (hops of information available)")
        ax.set_ylabel("Kendall $\\tau$  (out-of-fold)")
        ax.set_title(f"{tag}\n{subtitle}", fontsize=11, color="#1A1A2E")
        ax.set_xticks(sorted(d.radius.unique()))
        ax.set_ylim(*ylim)
        ax.grid(alpha=0.25, ls=":")
        ax.legend(fontsize=8, loc="lower right", framealpha=0.95)

        # ---- bottom row: paired marginal gain ----
        ax = axes[1, col]
        radii = sorted(d.radius.unique())
        steps = list(zip(radii[:-1], radii[1:]))
        width = 0.8 / max(len(targets), 1)
        xs = np.arange(len(steps))
        for i, target in enumerate(targets):
            mat = (d[(d.target == target) & (d.richness == FULL)]
                   .pivot_table(index="radius", columns="seed",
                                values="kendall_tau"))
            means, errs = [], []
            for a, b in steps:
                if a in mat.index and b in mat.index:
                    diff = (mat.loc[b] - mat.loc[a]).dropna()
                    means.append(diff.mean())
                    errs.append(diff.std(ddof=1) if len(diff) > 1 else 0.0)
                else:
                    means.append(np.nan); errs.append(0.0)
            off = (i - (len(targets) - 1) / 2) * width
            # hatch is the bars' half of the secondary encoding described at
            # HATCH's definition - the bars cannot use marker shape.
            ax.bar(xs + off, means, width, yerr=errs, capsize=2,
                   color=COLORS.get(target, "#555"), alpha=0.9,
                   hatch=HATCH.get(target, ""), edgecolor="white", lw=0.4,
                   label=LABELS.get(target, target),
                   error_kw={"lw": 0.9, "ecolor": "#333"})
        ax.axhline(0, color="#333", lw=0.8)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"r{a} $\\to$ r{b}" for a, b in steps])
        ax.set_ylabel("gain in $\\tau$ from one more hop")
        ax.set_title("Marginal value of each extra hop (paired)", fontsize=10.5)
        ax.grid(alpha=0.25, ls=":", axis="y")
        if col == 0:
            ax.legend(fontsize=7.5, loc="upper right")

    # Reading conventions and the ca-GrQc headline, both below the axes. These
    # used to be in-axes text boxes; they obstructed the curves they were
    # describing, which for a figure whose whole argument is the SHAPE of those
    # curves is a straight loss.
    footer = ("band = $\\pm$1 sd over seeds   ·   circled = $r^*$ at "
              f"$\\varepsilon$=0.05   ·   richest tier ({FULL})")
    if headline:
        footer += "\n" + headline
    fig.text(0.5, 0.008, footer, ha="center", va="bottom", fontsize=9.5,
             color="#1A1A2E")

    fig.suptitle("Locality budget: how far must you look to predict influence?",
                 fontsize=14, fontweight="bold", color="#2E4B7A", y=0.985)
    # Bottom of the rect lifted off 0 to leave the footer its two lines.
    fig.tight_layout(rect=[0, 0.055, 1, 0.96])
    fig.savefig(OUT_PATH, dpi=170, facecolor="white")
    print(f"saved {OUT_PATH}")


if __name__ == "__main__":
    main()

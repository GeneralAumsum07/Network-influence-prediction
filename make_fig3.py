"""
Figure 3: Angle 4 - what survives damage.

One panel per (target, network). Each shows how well three methods recover the
CLEAN ranking when given only a graph with a fraction rho of its edges deleted:

    local      local features on the damaged graph, through a model trained on
               clean data
    recompute  the global score computed directly on the damaged graph
    degree     degree on the damaged graph, as a floor

At rho = 0 the recompute line is 1.0 by construction - it IS the truth - so the
local line starts behind by whatever the model's clean-data error is. The
question the figure asks is not who starts ahead but who falls faster, and
whether the lines cross.

Dashed lines repeat local and recompute on the subset where the clean target is
nonzero. That is the skew control: betweenness has 15-55% exact zeros, so a
method that merely preserves the zero/nonzero split would look robust on the
solid line while being useless for ranking the nodes that matter. A gap that
survives the dashed lines is real.

Shaded bands are the spread over independent edge-deletion draws.
"""
# ACCESSIBILITY GAP, logged 2026-09-07, corrected same day after review.
# An earlier version of this comment described "residual scatter panels" separating
# over-/under-/well-predicted by colour alone. THIS FILE HAS NO SUCH PANELS - that note
# belonged in make_fig2.py only, and has been left there. The real gap here is different
# and was missed by the 2026-09-07 palette validation: the per-method line series below
# all use the same "o-" marker and linestyle (see the ax.plot call), so they are separated
# by COLOUR ALONE. The claim in make_fig1.py that every series in every figure is
# redundantly encoded does not hold for this file. Give these series distinct markers if
# it is revised; risk is low but the discipline is real.

import argparse
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Two arms since 2026-09-12 (Claude Opus 5, plan §0): the historical raw-objective
# CSV that every published Angle 4 number came from, and the log1p arm that
# `analyse_robustness.py --objective reported` writes to its own path. The
# figure's subtitle must name whichever arm it was drawn from (P3-08), so the
# arm picks the source, the output and the label together and cannot be mixed.
ARMS = {
    "raw": ("results/robustness.csv", "results/fig3_robustness.png",
            "objective: raw betweenness (historical arm; horizon tables "
            "report log1p)"),
    "reported": ("results/robustness_log1p.csv",
                 "results/fig3_robustness_log1p.png",
                 "objective: log1p betweenness (the arm the horizon tables "
                 "report; --objective reported)"),
}
COLOR = {"local": "#2E4B7A", "recompute": "#B5651D", "degree": "#8A8A8A"}
LABEL = {"local": "local model on damaged graph",
         "recompute": "recompute global score on damaged graph",
         "degree": "degree on damaged graph"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--objective", default="raw", choices=sorted(ARMS),
                    help="which analyse_robustness.py arm to draw (default raw, "
                         "the historical figure)")
    ap.add_argument("--src", default=None, help="override the arm's CSV")
    ap.add_argument("--out", default=None, help="override the arm's PNG")
    args = ap.parse_args()
    src_default, out_default, arm_label = ARMS[args.objective]
    SRC = args.src or src_default
    OUT = args.out or out_default

    if not os.path.exists(SRC):
        raise SystemExit(f"{SRC} not found - run analyse_robustness.py first")
    df = pd.read_csv(SRC)
    nets = list(df.network.unique())
    targets = [t for t in ("betweenness", "spread_mean") if t in set(df.target)]

    fig, axes = plt.subplots(len(targets), len(nets),
                             figsize=(5.4 * len(nets), 4.6 * len(targets)),
                             squeeze=False)
    fig.patch.set_facecolor("white")

    for r, target in enumerate(targets):
        for c, net in enumerate(nets):
            ax = axes[r, c]
            sub = df[(df.network == net) & (df.target == target)]
            for method in ("local", "recompute", "degree"):
                m = sub[sub.method == method]
                if m.empty:
                    continue
                g = m.groupby("rho")["tau"]
                mean, sd = g.mean(), g.std(ddof=1).fillna(0.0)
                ax.plot(mean.index, mean.values, "o-", lw=2.1, ms=5.5,
                        color=COLOR[method], label=LABEL[method], zorder=3)
                ax.fill_between(mean.index, mean - sd, mean + sd,
                                color=COLOR[method], alpha=0.15, lw=0)
                # skew control
                if method in ("local", "recompute") and m.tau_nonzero.notna().any():
                    gn = m.groupby("rho")["tau_nonzero"].mean()
                    ax.plot(gn.index, gn.values, "--", lw=1.4, alpha=0.85,
                            color=COLOR[method], zorder=2)

            # mark where local overtakes recompute, if it does
            piv = sub.pivot_table(index="rho", columns="method", values="tau",
                                  aggfunc="mean")
            if {"local", "recompute"} <= set(piv.columns):
                diff = piv["local"] - piv["recompute"]
                won = diff[diff > 0]
                if len(won):
                    ax.axvline(float(won.index.min()), color="#2E6E4E",
                               ls=":", lw=1.6, zorder=1)
                    ax.text(float(won.index.min()), 0.02,
                            f"  local ahead from\n  $\\rho$={won.index.min():g}",
                            transform=ax.get_xaxis_transform(), fontsize=7.5,
                            color="#2E6E4E", va="bottom")

            ax.set_xlabel("$\\rho$   (fraction of edges deleted)")
            ax.set_ylabel("Kendall $\\tau$ vs the CLEAN truth")
            ax.set_title(f"{net}\ntarget: {target}", fontsize=10.5,
                         color="#1A1A2E")
            ax.grid(alpha=0.25, ls=":")
            if r == 0 and c == 0:
                ax.legend(fontsize=7.5, loc="lower left", framealpha=0.95)
                ax.text(0.98, 0.97,
                        "dashed = nonzero subset\n(skew control)",
                        transform=ax.transAxes, fontsize=7.5, ha="right",
                        va="top", style="italic", color="#555")

    fig.suptitle("Angle 4: does local prediction degrade more gracefully "
                 "than recomputing on broken data?",
                 fontsize=13.5, fontweight="bold", color="#2E4B7A", y=0.995)
    # Objective label added 2026-09-11 (Claude Opus 5, Task 6 finding P3-08):
    # analyse_robustness.py fits betweenness under the raw squared-error
    # objective - the historical arm - not the log1p arm the study reports in
    # the horizon tables. The figure must say so on its face. Since 2026-09-12
    # the label comes from ARMS so the reported-arm figure names its arm too.
    fig.text(0.5, 0.965,
             "at $\\rho$=0 the recompute line is 1.0 by construction - it is "
             "the truth. What matters is the slope, not the intercept.   |   "
             + arm_label,
             ha="center", fontsize=9, color="#555", style="italic")
    fig.tight_layout(rect=[0, 0, 1, 0.955])
    fig.savefig(OUT, dpi=170, facecolor="white")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()

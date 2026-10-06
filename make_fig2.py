"""
Figure 2: the failure atlas.

Three rows per network, answering three different questions.

TOP - WHERE the model goes wrong. Predicted rank against true rank, every node
plotted; perfect prediction is the diagonal. Points above the line are
under-predicted, points below are over-predicted.

MIDDLE - what makes a node HARD TO RANK. Cliff's delta between the mis-ranked
tail and the well-ranked middle, for each profiling variable. Bars are coloured
by whether the model had the variable: GLOBAL bars (information it was denied)
are explanatory, LOCAL bars are context.

BOTTOM - what decides the DIRECTION of the error: the two tails compared
against each other rather than against the middle. This cancels everything the
tails share and isolates what separates a hidden influencer from a false
promise. If these bars are flat, the model is imprecise on an identifiable
population but not biased about it - which is a real finding, and a different
one from "we found the hidden influencers". The panel title states the verdict
so it cannot be misread from bar length alone.

Effect size rather than p-value throughout, because at several thousand nodes
almost any difference is significant and a p-value would rank everything as
important.

Computation is imported from analyse_failures rather than duplicated, so the
figure and the text report cannot disagree.
"""
# ACCESSIBILITY GAP, logged 2026-09-07, deliberately not scheduled.
# The residual scatter panels below separate over-/under-/well-predicted by COLOUR
# ALONE - no marker-shape difference. This is the one place the redundant-encoding
# discipline documented in make_fig1.py slipped. Blue/orange is among the more robust
# pairs across colourblindness types so practical risk is low, but if these panels are
# ever revised, give the three categories distinct marker shapes.

import argparse

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyse_failures import compute, discover

# The historical filename, kept for the default target so that every existing
# reference to `fig2_failure_atlas.png` in the docs still resolves.
OUT_PATH = "results/fig2_failure_atlas.png"
DEFAULT_TARGET = "spread_mean"
G_COLOR = "#2E4B7A"     # global - what the model could not see
L_COLOR = "#B5651D"     # local  - what it had


def out_path_for(target: str, tail: float) -> str:
    """
    Where this figure belongs on disk.

    The script takes a --target flag but used to write to one fixed path, so
    two perfectly legitimate runs would silently overwrite each other and the
    only symptom was a figure that quietly meant something other than its
    caption. The tail is in the name for the same reason: --tail 0.05 and
    --tail 0.10 are different experiments, not different views of one.
    """
    if target == DEFAULT_TARGET and abs(tail - 0.05) < 1e-12:
        return OUT_PATH
    return f"results/fig2_failure_atlas_{target}_tail{int(round(tail * 100))}.png"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=DEFAULT_TARGET)
    ap.add_argument("--tail", type=float, default=0.05)
    ap.add_argument("--networks", default="")
    ap.add_argument("--out", default="",
                    help="override the derived output path")
    # Added 2026-09-11 (Claude Opus 5, Task 6 audit findings P2-03/P3-08): the
    # atlas now reads each target's REPORTED objective arm; `--arm raw`
    # reproduces the historical Finding 8 figure under a distinct filename and
    # prints the arm in the subtitle so the two can never be confused.
    ap.add_argument("--arm", default="reported", choices=["reported", "raw"])
    args = ap.parse_args()

    tags = args.networks.split(",") if args.networks else discover()
    res = [r for r in (compute(t, args.target, args.tail, args.arm) for t in tags)
           if r is not None]
    if not res:
        raise SystemExit("nothing to plot - run stage2_sweep.py then "
                         "analyse_failures.py")

    import os
    os.makedirs("results", exist_ok=True)

    ncols = len(res)
    fig, axes = plt.subplots(3, ncols, figsize=(5.6 * ncols, 13.2),
                             squeeze=False,
                             gridspec_kw={"height_ratios": [1.15, 1.0, 1.0]})
    fig.patch.set_facecolor("white")

    for col, r in enumerate(res):
        pt, pp = r["pct_true"], r["pct_pred"]

        # ---------------- top: rank vs rank ----------------
        ax = axes[0, col]
        ax.scatter(pp[r["rest"]], pt[r["rest"]], s=4, c="#BBBBBB",
                   alpha=0.45, lw=0, label="well predicted")
        ax.scatter(pp[r["over"]], pt[r["over"]], s=13, c="#B5651D",
                   alpha=0.85, lw=0, label=f"over-predicted ({r['k']})")
        ax.scatter(pp[r["under"]], pt[r["under"]], s=13, c="#2E4B7A",
                   alpha=0.85, lw=0, label=f"under-predicted ({r['k']})")
        ax.plot([0, 1], [0, 1], ls="--", lw=1.1, c="#333", zorder=5)

        ax.set_xlabel("predicted percentile rank")
        ax.set_ylabel("true percentile rank")
        ax.set_title(f"{r['tag']}\nn={r['n']:,}   mean |$\\Delta$| = "
                     f"{np.abs(r['delta']).mean():.3f}",
                     fontsize=11, color="#1A1A2E")
        ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
        ax.grid(alpha=0.22, ls=":")
        ax.legend(fontsize=7.5, loc="lower right", framealpha=0.95,
                  markerscale=1.8)
        if col == 0:
            ax.text(0.03, 0.97, "above the line = under-predicted",
                    transform=ax.transAxes, fontsize=8, va="top",
                    style="italic", color="#555")

        # ---- middle: what makes a node hard to rank at all ----
        # Each row picks its OWN top variables from its OWN contrast table.
        #
        # This row used to fix the variable order for the row below it, so the
        # two bar charts could be scanned down a column. That alignment was
        # actively harmful. The two rows are different contrasts over different
        # node sets: this one is (mis-ranked tail vs well-ranked middle), the
        # one below is (under-predicted vs over-predicted). A variable that
        # separates the two tails from each other can be flat against the
        # middle, because it pushes the two tails in opposite directions and
        # they cancel. Selecting the lower row by this row's ranking therefore
        # systematically hides exactly the strongest directional effects.
        #
        # On facebook_combined betweenness that hid five LARGE effects (ego
        # betweenness 0.735, coreness 0.730, h_index_3 0.725, edge embeddedness
        # 0.722, degree 0.703) and understated max |d| as 0.54. Worse, on
        # ca-HepTh spread_mean and p2p-Gnutella08 betweenness it pushed the
        # reported max below the 0.15 threshold and made the panel print
        # "no directional blind spot" - asserting the ABSENCE of an effect that
        # was present at 0.19 and 0.29 respectively. A figure may understate an
        # effect by accident; it may not announce a null that its own data
        # contradicts.
        t = r["table_under"].head(7).iloc[::-1]
        order = list(t.variable)
        labels = [v.replace("[G] ", "").replace("[L] ", "") for v in order]
        colors = [G_COLOR if v.startswith("[G]") else L_COLOR for v in order]
        ypos = np.arange(len(order))

        ax = axes[1, col]
        ax.barh(ypos, t.cliffs_d.values, color=colors, alpha=0.9)
        ax.set_yticks(ypos); ax.set_yticklabels(labels, fontsize=8.5)
        ax.axvline(0, color="#333", lw=0.8)
        for thr in (-0.33, 0.33):
            ax.axvline(thr, color="#999", lw=0.7, ls=":")
        ax.set_xlabel("Cliff's $\\delta$   (mis-ranked tail vs well-ranked middle)")
        ax.set_xlim(-1, 1)
        ax.set_title("What makes a node hard to rank", fontsize=10.5)
        ax.grid(alpha=0.22, ls=":", axis="x")

        # ---- bottom: what decides the DIRECTION of the error ----
        # Selected from table_direction, ranked by that table - see the note
        # above for why it must not inherit the row above's variable set.
        dt = r["table_direction"].head(7).iloc[::-1]
        d_order = list(dt.variable)
        d_labels = [v.replace("[G] ", "").replace("[L] ", "") for v in d_order]
        d_colors = [G_COLOR if v.startswith("[G]") else L_COLOR
                    for v in d_order]
        d_ypos = np.arange(len(d_order))

        ax = axes[2, col]
        ax.barh(d_ypos, dt.cliffs_d.values, color=d_colors, alpha=0.9)
        ax.set_yticks(d_ypos); ax.set_yticklabels(d_labels, fontsize=8.5)
        ax.axvline(0, color="#333", lw=0.8)
        for thr in (-0.33, 0.33):
            ax.axvline(thr, color="#999", lw=0.7, ls=":")
        ax.set_xlabel("Cliff's $\\delta$   (under-predicted vs over-predicted)")
        ax.set_xlim(-1, 1)
        # Over the WHOLE directional table, not just the drawn bars. The drawn
        # bars are now that table's own top 7, so the two agree by construction
        # - but the verdict is a claim about the data, not about the figure,
        # and it should not silently depend on how many bars fit.
        biggest = float(np.nanmax(
            np.abs(r["table_direction"].cliffs_d.values)))
        verdict = ("no directional blind spot"
                   if biggest < 0.15 else "directional signal present")
        # Three decimals, not two: the verdict threshold is 0.15, and a true
        # value of 0.149 printed as "0.15 - no directional blind spot" reads as
        # a contradiction of itself. facebook_combined spread_mean sits exactly
        # there.
        ax.set_title(f"What decides the direction of the error\n"
                     f"max |$\\delta$| = {biggest:.3f} - {verdict}",
                     fontsize=10.5)
        ax.grid(alpha=0.22, ls=":", axis="x")

    # One figure-level legend below the panels. Putting it inside the bar axes
    # overlaps whichever bar happens to be shortest, and which bar that is
    # changes per network - so it cannot be placed reliably in-axes.
    handles = [plt.Rectangle((0, 0), 1, 1, color=G_COLOR),
               plt.Rectangle((0, 0), 1, 1, color=L_COLOR)]
    fig.legend(handles,
               ["global - information the model was DENIED (explanatory)",
                "local - information the model had (context)"],
               fontsize=9 if ncols > 1 else 8,
               loc="lower center", ncol=2 if ncols > 1 else 1,
               frameon=False, bbox_to_anchor=(0.5, 0.004))

    # Title scales with the figure so it does not clip when only one network
    # is plotted.
    fig.suptitle("Failure atlas: what is local prediction blind to?",
                 fontsize=min(15, 6.5 + 2.6 * ncols), fontweight="bold",
                 color="#2E4B7A", y=0.995)
    fig.text(0.5, 0.972, f"target: {args.target}   |   {res[0]['objective_label']}"
                         f"   |   residual standardised within influence bins"
                         f"   |   {int(args.tail * 100)}% tails",
             ha="center", fontsize=9.5, color="#555", style="italic")
    fig.tight_layout(rect=[0, 0.045 if ncols == 1 else 0.03, 1, 0.962])
    out = args.out or out_path_for(args.target, args.tail)
    if args.arm == "raw" and not args.out:
        out = out.replace(".png", "_rawarm.png")
    fig.savefig(out, dpi=170, facecolor="white")
    print(f"saved {out}")


if __name__ == "__main__":
    main()

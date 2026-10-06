"""
Figure 6: the multiplicity landscape - which comparisons the star rule missed.

Source: results/multiplicity.csv (analyse_multiplicity.py, referee objection
M5b). 240 comparisons, four correction families of 60.

WHAT THE FIGURE IS FOR. This project awards a star at "beats 2 x the paired seed
sd". On ten seeds that is |t_9| > 2*sqrt(10) = 6.32, a two-sided alpha of
1.4e-4 per comparison (corrected 2026-09-11 by Claude Opus 5, Task 6 finding
P3-01; this docstring previously said "roughly alpha = 0.046", which is
P(|z| > 2) and not the rule's level). It takes no account of how many
comparisons were made. §M5b re-tested every comparison under Benjamini-Hochberg
WITHIN its family. The crosstab on the current corpus (multiplicity.csv
regenerated 2026-09-12 after the 5-node orbit radius retag and r=1 refit,
Task 6 finding P1-01; the pre-refit crosstab was 129 / 31 / 0 / 80 and is
kept in results/RESULTS_multiplicity_pre_orbit5_refit_20260901.txt) is

    starred AND BH-significant   113
    BH-significant, NOT starred   36   <- the point of this figure
    starred, NOT BH-significant    0
    neither                       91

The figure recomputes every count from the CSV it plots, so these four
numbers are documentation, not inputs.

**Stars are a strict subset of the BH-significant set BY CONSTRUCTION.** Every
starred row has p_t <= 1.4e-4 and the smallest BH threshold a 60-comparison
family can set at q = 0.05 is 8.3e-4, so the zero in the third row is a
property of the rule, not something the correction discovered. What the
correction DID find is the second row: 36 real effects never got a star. The
project has been under-claiming, not over-claiming, and this figure is the
visual evidence for that sentence.

It also means the figure has NO counterweight to draw: there is no
"significant-looking but killed by BH" population, because that set is empty. A
reader who expects a volcano plot's usual story - the corrected test culling
over-eager claims - has to be told explicitly that the cull found nothing, or
they will read the empty region as an oversight. Hence the annotation.

WHY EACH FAMILY GETS ITS OWN AXES. BH was applied within family, so a q-value in
`hop_gain` and a q-value in `dynamic_tier` were computed against different
numbers of hypotheses and are not on a common scale. Sharing a y-axis would
invite exactly the cross-family comparison the correction structure forbids. The
x-scales differ for a blunter reason too: hop gains reach +0.69 tau while the
whole tier story lives inside +/-0.035, and one shared x-axis would collapse
three of the four panels onto the zero line.

NO VERTICAL "NEGLIGIBLE EFFECT" LINE, and this is a finding rather than an
omission. The spec asked for one if the project defines a negligible-effect
threshold. It does not define a fixed one: the star rule is |mean| > 2 x sd with
sd measured PER CELL, so the effect size that earns a star varies from cell to
cell. It varies enough to invert - the smallest starred effect in this corpus is
+0.00013 tau and the largest BH-significant UNstarred effect is 0.0240 (it was
0.0347 before the 2026-09-11 r=1 refit; the caption recomputes both), roughly
190x bigger. The star rule is a statement about a cell's seed noise, not about
how big the effect is, and drawing a single vertical line would imply otherwise.

Writes to results/.
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SRC = "results/multiplicity.csv"
OUT_DIR = "results"
OUT_PATH = os.path.join(OUT_DIR, "fig6_multiplicity_landscape.png")

ALPHA = 0.05        # the BH level analyse_multiplicity.py corrects at

# Three categories, not two. Colours: two house hues plus a neutral for the
# null population. #5E5E5E was chosen with the palette validator rather than by
# eye - the obvious mid-grey #8A8A8A sits at dE 13.8 against #B5651D, below the
# normal-vision floor of 15, so full-colour readers would struggle to separate
# the null cloud from the very points the figure exists to highlight. #5E5E5E
# clears the floor (16.7), clears CVD (12.0 protan) and clears 3:1 contrast
# against the surface. Marker shape and size carry identity as well, so the
# categories survive greyscale printing.
CATS = ["star", "bh_only", "neither"]
CAT_COLOR = {"star": "#2E4B7A", "bh_only": "#B5651D", "neither": "#5E5E5E"}
CAT_MARKER = {"star": "o", "bh_only": "^", "neither": "."}
CAT_SIZE = {"star": 34, "bh_only": 78, "neither": 18}
CAT_LABEL = {
    "star": "starred (beats 2$\\times$ seed sd) — and BH-significant",
    "bh_only": "BH-significant but NEVER STARRED",
    "neither": "neither",
}

# Family order: the three richness tiers in ladder order, then hop gains. Fixed
# here so the panel order does not depend on however the CSV happens to sort.
FAMILY_ORDER = ["hop_gain", "edge_tier", "subgraph_tier", "dynamic_tier"]
FAMILY_TITLE = {
    "hop_gain": "hop gains  (r$\\to$r+1)",
    "edge_tier": "edge tier",
    "subgraph_tier": "subgraph tier",
    "dynamic_tier": "dynamic tier",
}


def main() -> None:
    d = pd.read_csv(SRC)

    # -log10(q). q can be exactly 1.0, which maps to 0 - fine. It cannot be 0
    # (BH returns adjusted p-values), so no guard is needed on the log.
    d["nlq"] = -np.log10(d.q_bh)
    d["bh"] = d.q_bh < ALPHA

    # The three categories are mutually exclusive by construction. The
    # "starred but NOT BH-significant" cell is empty in this corpus, and if a
    # future corpus ever populates it this assignment would silently file those
    # points under "star" - so assert rather than assume.
    bad = int((d.star & ~d.bh).sum())
    assert bad == 0, (
        f"{bad} comparisons are starred but fail BH. The figure's headline "
        f"('stars are a strict subset') is false for this data and the "
        f"annotation below would be a lie - add a fourth category before "
        f"regenerating.")

    def cat(row) -> str:
        if row.star:
            return "star"
        return "bh_only" if row.bh else "neither"

    d["cat"] = d.apply(cat, axis=1)

    fams = [f for f in FAMILY_ORDER if f in set(d.family)]
    fams += sorted(set(d.family) - set(FAMILY_ORDER))
    if not fams:
        raise SystemExit(f"{SRC} has no `family` column values")

    os.makedirs(OUT_DIR, exist_ok=True)
    fig, axes = plt.subplots(1, len(fams), figsize=(4.6 * len(fams), 5.6),
                             squeeze=False)
    fig.patch.set_facecolor("white")

    for j, fam in enumerate(fams):
        ax = axes[0, j]
        sub = d[d.family == fam]
        for c in CATS:
            s = sub[sub.cat == c]
            if not len(s):
                continue
            ax.scatter(s["mean"], s.nlq, s=CAT_SIZE[c], c=CAT_COLOR[c],
                       marker=CAT_MARKER[c],
                       # White edge on the two data-bearing categories: the
                       # clouds overlap near the origin and unringed marks merge
                       # into a single blob there.
                       edgecolors="white" if c != "neither" else "none",
                       linewidths=0.6, alpha=0.9 if c != "neither" else 0.75,
                       zorder=3 if c == "bh_only" else 2,
                       label=CAT_LABEL[c] if j == 0 else None)

        ax.axhline(-np.log10(ALPHA), color="#333", lw=1.0, ls="--", alpha=0.7)
        ax.axvline(0, color="#333", lw=0.8, alpha=0.5)
        ax.text(0.985, -np.log10(ALPHA), f" q={ALPHA}", fontsize=8,
                color="#333", va="bottom", ha="right",
                transform=ax.get_yaxis_transform())

        n_bh = int((sub.cat == "bh_only").sum())
        ax.set_title(f"{FAMILY_TITLE.get(fam, fam)}\n"
                     f"{int((sub.cat == 'star').sum())} starred, "
                     f"{n_bh} BH-only, "
                     f"{int((sub.cat == 'neither').sum())} neither",
                     fontsize=10.5, color="#1A1A2E")
        ax.set_xlabel("effect size  $\\Delta\\tau$  (mean over seeds)")
        if j == 0:
            ax.set_ylabel("$-\\log_{10}$ q  (BH, within family)")
        ax.grid(alpha=0.25, ls=":")
        ax.xaxis.set_major_locator(mticker.MaxNLocator(5))

    # Figure-level legend, in the strip under the suptitle rather than inside
    # the first panel. In-axes it sat on top of the hop_gain cloud, and the
    # hop_gain panel is the densest of the four.
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(CATS),
               fontsize=9, frameon=False, bbox_to_anchor=(0.5, 0.945))

    # The sentence the figure exists to support, with its own counts recomputed
    # from the frame that was just plotted.
    n_star = int((d.cat == "star").sum())
    n_bh = int((d.cat == "bh_only").sum())
    n_none = int((d.cat == "neither").sum())
    small_star = float(d.loc[d.cat == "star", "mean"].abs().min())
    big_unstarred = float(d.loc[d.cat == "bh_only", "mean"].abs().max())
    fig.text(
        0.5, 0.012,
        f"{n_star} starred · {n_bh} BH-significant but never starred · "
        f"{n_none} neither · "
        # \\bf, not \b: a single backslash here is Python's backspace escape and
        # mathtext then chokes on the remains. And `bad` rather than a literal
        # 0 - it is the same number the assertion above pinned, so the caption
        # cannot outlive the fact.
        f"and $\\bf{{{bad}}}$ starred results fail BH.  Stars are a strict SUBSET "
        f"of the "
        f"corrected-significant set, so multiplicity control removes nothing "
        f"and adds {n_bh} real effects: this corpus under-claims.  "
        f"The two rules disagree because the star rule tracks a cell's seed "
        f"noise, not its effect size — the smallest starred effect is "
        f"{small_star:.5f} $\\tau$ while the largest unstarred BH-significant "
        f"one is {big_unstarred:.4f}.",
        ha="center", va="bottom", fontsize=8.6, color="#1A1A2E", wrap=True)

    fig.suptitle("The multiplicity landscape: correcting for multiple tests "
                 "found nothing to remove",
                 fontsize=14, fontweight="bold", color="#2E4B7A", y=0.975)
    # top lowered from 0.845 to make room for the figure legend now sitting
    # between the suptitle and the panels.
    fig.subplots_adjust(left=0.055, right=0.99, top=0.795, bottom=0.175,
                        wspace=0.16)
    fig.savefig(OUT_PATH, dpi=170, facecolor="white")
    print(f"saved {OUT_PATH}")


if __name__ == "__main__":
    main()

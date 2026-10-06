"""
analyse_estimators.py - is r*(eps) a property of the pair, or of the forest?

WHY THIS EXISTS
---------------
This project's headline claim is that the locality horizon r*(eps) is a
MEASURED property of the (network, target) pair rather than a hyperparameter
someone picked. Every number supporting that came from one random forest. If
the horizon moves when the learner changes, the claim is about the forest and
the thesis sentence has to say so.

Review objection M4 asked for exactly this and it was outstanding until now.

WHAT MADE IT URGENT RATHER THAN MERELY OUTSTANDING
--------------------------------------------------
The 2026-08-31 audit found that Finding 10's carrying feature,
`local_conductance_2`, is ~99% reconstructible from columns already in the
table (held-out R^2 ~ +0.99) and is STILL worth +0.117 tau. What it buys is
ACCESSIBILITY, not information: a forest splitting on axis-aligned thresholds
does not spontaneously form the ratio cut/vol out of a dozen shell columns.

A linear model forms ratios for free. So Finding 10 is the one result here with
a named mechanistic reason to be estimator-specific, and section 3 below is its
pre-registered falsification test (see `docs/prereg_B2_estimator.md`).

THE ONE THING TO GET RIGHT IN THE COMPARISON
--------------------------------------------
r*(eps) is computed against EACH ESTIMATOR'S OWN CEILING. A weaker learner is
not thereby a shorter-sighted one, and scoring a weak learner against a strong
learner's absolute threshold would manufacture disagreement out of nothing.
`r_star_per_seed` already normalises within the seed's own curve, which is why
it is reused here rather than reimplemented.

Seed stability is printed beside every horizon. Without it there is no way to
tell an estimator disagreeing from two estimators both being unstable, and
those need opposite responses.

Run:  python analyse_estimators.py [--eps 0.05]
"""
import argparse
import glob
import os
import re

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analyse import FULL, load, curve, seed_matrix, r_star_per_seed

BASELINE = "rf"
EST_DIR = "estimators"


# Files in `estimators/` that are NOT estimators. `rf_log1p` is the baseline
# random forest under a different OBJECTIVE, swept on betweenness only, and it
# is spliced into the reported numbers by `analyse.load`. Treating it as a
# learner here compared a 1-target arm against 4-target sweeps and recorded 15
# nonexistent cells per network as "horizon disagreements" (Task 6 audit
# finding P2-01; excluded 2026-09-11 by Claude Opus 5).
OBJECTIVE_ARMS = frozenset({"rf_log1p"})


def discover() -> dict[str, list[str]]:
    """
    {tag: [estimators available]}, always with the baseline first.

    The baseline lives in the repo root as `sweep_<tag>.csv`; everything else
    lives in `estimators/` as `sweep_<tag>__<est>.csv`. That split is load
    bearing, not tidiness - see the note in `analyse.load`.
    """
    out: dict[str, list[str]] = {}
    for path in sorted(glob.glob(os.path.join(EST_DIR, "sweep_*__*.csv"))):
        m = re.match(r"sweep_(.+)__(.+)\.csv$", os.path.basename(path))
        if m and m.group(2) not in OBJECTIVE_ARMS:
            out.setdefault(m.group(1), []).append(m.group(2))
    return {tag: [BASELINE] + sorted(ests) for tag, ests in sorted(out.items())
            if os.path.exists(f"sweep_{tag}.csv")}


def sweep_for(tag: str, est: str) -> pd.DataFrame:
    """
    One (network, estimator) sweep, through the shared loader.

    RAW ON PURPOSE. As of 2026-09-04 `analyse.load()` reports betweenness from
    the log1p-objective arm, but this script's whole job is to vary the
    ESTIMATOR with everything else held fixed. The `ridge` and `hgb` sweeps on
    disk were fitted under the squared-error objective, so taking the default
    here would compare rf(log1p) against ridge(squared) and hgb(squared) - two
    things differing at once, and the resulting "estimator disagreement" would
    partly be Finding 11's objective effect wearing an estimator's name.

    Re-basing B2 onto the corrected objective would mean re-running ridge and
    hgb under log1p, which is a separate decision and a separate compute cost.
    Until that happens this comparison stays entirely inside the raw arm, and
    every number it prints carries "under a squared-error objective".
    """
    if est == BASELINE:
        return load(tag, raw=True)
    return load(tag, os.path.join(EST_DIR, f"sweep_{tag}__{est}.csv"))


def horizon(d: pd.DataFrame, target: str, eps: float) -> tuple:
    """
    (modal r*, support, n_seeds) on the richest STRUCTURAL tier.

    Deliberately not the richest tier overall: the `dynamic` rung assumes the
    observer knows p, and the headline locality result must not depend on that.
    Same choice as analyse.py.
    """
    vals = r_star_per_seed(seed_matrix(d, target, FULL), eps)
    if not vals:
        return None, 0, 0
    counts = pd.Series(vals).value_counts()
    return int(counts.idxmax()), int(counts.max()), len(vals)


def section_horizons(avail: dict[str, list[str]], eps: float) -> list[dict]:
    """Section 1: does r*(eps) agree across estimators?"""
    print("=" * 78)
    print(f"1. r*(eps={eps}) BY ESTIMATOR   (richness={FULL})")
    print("   cell = modal r* (support/seeds). Disagreement with the baseline")
    print("   is flagged '!' - but read the support first: a 4/10 mode is not")
    print("   a horizon, it is a coin flip, and two coin flips disagreeing is")
    print("   not evidence that the estimator matters.")
    print("=" * 78)

    rows = []
    for tag, ests in avail.items():
        sweeps = {e: sweep_for(tag, e) for e in ests}
        targets = sorted(set(sweeps[BASELINE].target.unique()))
        print(f"\n{tag}")
        print(f"  {'target':<16s}" + "".join(f"{e:>16s}" for e in ests))
        for target in targets:
            base_r, _, _ = horizon(sweeps[BASELINE], target, eps)
            cells = []
            for e in ests:
                r, sup, n = horizon(sweeps[e], target, eps)
                flag = "!" if (e != BASELINE and r != base_r) else " "
                cells.append(f"{'-' if r is None else r}({sup}/{n}){flag}")
                rows.append({"network": tag, "target": target, "estimator": e,
                             "r_star": r, "support": sup, "n_seeds": n,
                             "agrees": e == BASELINE or r == base_r})
            print(f"  {target:<16s}" + "".join(f"{c:>16s}" for c in cells))
    return rows


def section_shape(avail: dict[str, list[str]]) -> list[dict]:
    """
    Section 2: is the SHAPE of P(r) invariant even where the level is not?

    This is the quantity r*(eps) is actually read off, so it is a sharper
    question than "do the taus match" - and a much lower bar to clear, which
    is why P6 in the pre-registration predicts shape survives where level does
    not. Spearman on four points is coarse; it is reported with the raw curve
    means so a perfect rho on a flat curve cannot pass unnoticed.
    """
    print("\n" + "=" * 78)
    print("2. SHAPE OF P(r) vs THE BASELINE   (Spearman over the 4 radii)")
    print("   `range` is the baseline's tau span across radii. A high rho on a")
    print("   near-flat curve means nothing - check that column first.")
    print("=" * 78)

    rows = []
    for tag, ests in avail.items():
        sweeps = {e: sweep_for(tag, e) for e in ests}
        base = sweeps[BASELINE]
        print(f"\n{tag}")
        print(f"  {'target':<16s} {'range':>8s}  " +
              "  ".join(f"{'rho ' + e:>14s}" for e in ests if e != BASELINE))
        for target in sorted(set(base.target.unique())):
            cb = curve(base, target)["tau_mean"]
            cells = []
            for e in ests:
                if e == BASELINE:
                    continue
                ce = curve(sweeps[e], target)["tau_mean"]
                idx = cb.index.intersection(ce.index)
                rho = (spearmanr(cb[idx], ce[idx]).statistic
                       if len(idx) >= 3 else np.nan)
                cells.append(f"{rho:>14.3f}")
                rows.append({"network": tag, "target": target, "estimator": e,
                             "rho_shape": rho,
                             "baseline_range": float(cb.max() - cb.min())})
            print(f"  {target:<16s} {cb.max() - cb.min():>8.4f}  " +
                  "  ".join(cells))
    return rows


def section_finding10(avail: dict[str, list[str]]) -> None:
    """
    Section 3: the pre-registered falsification test.

    The subgraph rung on facebook betweenness at r=2 - the largest richness
    effect in the project, and the one the audit showed is an ACCESSIBILITY
    gain rather than an information gain.

    Read off the sweep table rather than refitted: `analyse_edge_tier.py`
    isolates cost groups within the rung and needs its own fits, but the rung
    itself is just two cells that every sweep already contains, and re-fitting
    them here would risk quoting a different number from the same experiment.

    Paired within seed. The two rungs at one seed share a fold split, so
    differencing first removes the shared component; an unpaired read of a
    +0.03 effect is unreadable.
    """
    print("\n" + "=" * 78)
    print("3. FINDING 10 UNDER EACH ESTIMATOR  (pre-registered, P1/P2/P3)")
    print("   facebook_combined, betweenness, r=2:")
    print("   node+edge -> node+edge+subgraph, paired within seed.")
    print("   Pre-registered threshold: ridge < +0.040 confirms P1;")
    print("   hgb >= +0.040 confirms P3.  See docs/prereg_B2_estimator.md")
    print("=" * 78)

    tag, target, r = "facebook_combined", "betweenness", 2
    if tag not in avail:
        print(f"\n  {tag} has no alternative-estimator sweep yet - skipped")
        return

    print(f"\n  {'estimator':<10s} {'node+edge':>11s} {'+subgraph':>11s} "
          f"{'gain':>10s} {'sd':>9s}  verdict")
    for est in avail[tag]:
        d = sweep_for(tag, est)
        sub = d[(d.target == target) & (d.radius == r)]
        piv = sub.pivot_table(index="seed", columns="richness",
                              values="kendall_tau")
        if not {"node+edge", FULL} <= set(piv.columns):
            print(f"  {est:<10s} (missing a rung)")
            continue
        diff = (piv[FULL] - piv["node+edge"]).dropna()
        g, sd = float(diff.mean()), float(diff.std(ddof=1))
        # '*' is this project's standing bar: the gain clears twice the sd of
        # the PAIRED per-seed difference.
        star = "*" if abs(g) > 2 * sd else " "
        verdict = ""
        if est == "ridge":
            verdict = "P1 CONFIRMED" if g < 0.040 else "P1 FALSIFIED"
        elif est == "hgb":
            verdict = "P3 CONFIRMED" if g >= 0.040 else "P3 FALSIFIED"
        print(f"  {est:<10s} {piv['node+edge'].mean():>11.4f} "
              f"{piv[FULL].mean():>11.4f} {g:>+10.4f} {sd:>9.4f}{star} "
              f"{verdict}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eps", type=float, default=0.05)
    args = ap.parse_args()

    avail = discover()
    if not avail:
        raise SystemExit(
            f"no {EST_DIR}/sweep_<tag>__<est>.csv found. Run e.g.\n"
            f"    python stage2_sweep.py ca-GrQc "
            f"spread_mean,spread_cv,betweenness,spread_resid 3 10 ridge")

    print(f"estimators found: "
          + ", ".join(f"{t}: {'/'.join(e)}" for t, e in avail.items()))

    h = section_horizons(avail, args.eps)
    s = section_shape(avail)
    section_finding10(avail)

    # Summary last, because it is the line most likely to be quoted and it
    # should not be readable without the support counts above it.
    hd = pd.DataFrame(h)
    hd = hd[hd.estimator != BASELINE]
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    for est, g in hd.groupby("estimator"):
        print(f"  r* agrees with {BASELINE}: {int(g.agrees.sum())}/{len(g)} "
              f"(network x target) cells under {est}")
    sd = pd.DataFrame(s)
    for est, g in sd.groupby("estimator"):
        print(f"  P(r) shape rho vs {BASELINE}, median {est}: "
              f"{g.rho_shape.median():.3f}")

    os.makedirs("results", exist_ok=True)
    pd.DataFrame(h).to_csv("results/estimator_horizons.csv", index=False)
    pd.DataFrame(s).to_csv("results/estimator_shape.csv", index=False)
    print("\nwrote results/estimator_horizons.csv, results/estimator_shape.csv")


if __name__ == "__main__":
    main()

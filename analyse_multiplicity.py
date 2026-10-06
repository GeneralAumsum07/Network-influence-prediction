"""
A4 - multiplicity control: how many of this project's stars survive correction?

WHY THIS EXISTS
---------------
Throughout this project a claim earns a star when its paired per-seed gain beats
TWICE the standard deviation of that paired difference. That rule takes no
account of how many comparisons were made across a corpus of 3,204 swept cells,
and it was never stated as a significance level at all - so this script asks
what level it actually is, and what survives a proper correction.

(Corrected 2026-09-11 by Claude Opus 5, Task 6 finding P3-01. Earlier versions
of this docstring, of the printed `expected under a global null` line and of
study section 19b said the 2-sd rule is "roughly alpha = 0.046 two-sided" and
that a 60-comparison family therefore "expects about three false stars".
Both numbers were wrong by the arithmetic below: 0.046 is P(|z| > 2), which is
neither the rule's statistic nor its distribution.)

WHAT THE STAR RULE ACTUALLY IS
------------------------------
The "2 sd" rule is |mean| > 2*sd(ddof=1) of the ten paired differences. The
paired t-statistic is mean/(sd/sqrt(n)) = sqrt(n) * (mean/sd), so on n = 10
seeds the rule is |t_9| > 2*sqrt(10) = 6.32. Two-sided, that is

    P(|t_9| > 6.32) = 1.37e-4          (scipy.stats.t.sf(6.325, 9) * 2)

per comparison - not 0.046, and not even P(|t_9| > 2) = 0.077. Under a global
null the expected number of false stars is therefore 3204 * 1.37e-4 = 0.44
over the whole corpus and 60 * 1.37e-4 = 0.008 in a 60-comparison family.

That has one consequence this script's output must be read with: **a star can
never fail Benjamini-Hochberg here.** Every starred row has p_t <= 1.37e-4,
and the smallest BH threshold in a family of 60 at q = 0.05 is 0.05/60 =
8.3e-4, so "starred, NOT BH-significant = 0" is a theorem about the rule, not
an empirical outcome of the correction. The FINDING in the crosstab is the
other off-diagonal: comparisons that pass BH and were never starred - the
project has been under-claiming. The `expected_null` printed per family is now
n * P(|t_{n-1}| > 2*sqrt(n)), computed from the t distribution, rather than the
0.046 * n it used to be.

This script does not re-run anything. It recomputes each claim's p-value
properly, applies Benjamini-Hochberg WITHIN each analysis family, and reports
q-values beside the existing stars so every claim can be re-read at its
corrected significance.

TWO ASSUMPTIONS, BOTH FLAGGED RATHER THAN BURIED
-------------------------------------------------
1. The paired t-test on ten seed differences assumes those differences are
   approximately normal. With n=10 that is not checkable in any serious way. A
   sign test is reported alongside as a distribution-free floor - it is far less
   powerful (its smallest attainable two-sided p at n=10 is 0.002) but it assumes
   nothing.

2. Benjamini-Hochberg controls FDR under independence or positive regression
   dependence. These cells are positively dependent - radii share seeds and
   therefore fold splits, which is the whole point of pairing - so BH is
   appropriate rather than merely convenient. Benjamini-Yekutieli, which holds
   under ARBITRARY dependence, is reported as the conservative bound.
"""

import numpy as np
import pandas as pd
from scipy.stats import ttest_rel, binomtest, t as t_dist

from analyse import discover_networks, load

TARGETS = ["betweenness", "spread_mean", "spread_cv", "spread_resid"]
NODE, EDGE, FULL, DYN = ("node", "node+edge", "node+edge+subgraph",
                         "node+edge+subgraph+dynamic")


def paired(d: pd.DataFrame, target: str, richness: str,
           key: str, a, b) -> np.ndarray | None:
    """
    Per-seed paired differences between two cells that differ in one coordinate.

    `key` is the coordinate being stepped - "radius" for a hop gain, "richness"
    for a tier gain. Returns None if either cell is missing at any seed, rather
    than silently averaging over a ragged set: a family with a hole in it would
    otherwise get a smaller effective n and a quietly wrong p-value.
    """
    sub = d[d.target == target]
    if key == "radius":
        sub = sub[sub.richness == richness]
    else:
        sub = sub[sub.radius == richness]  # `richness` carries the radius here

    pa = sub[sub[key] == a].set_index("seed")["kendall_tau"]
    pb = sub[sub[key] == b].set_index("seed")["kendall_tau"]
    common = pa.index.intersection(pb.index)
    if len(common) < 3:
        return None
    return (pb[common] - pa[common]).to_numpy()


def score(diffs: np.ndarray) -> dict:
    """Effect size, the project's own star rule, a t-test, and a sign test."""
    mean, sd = float(diffs.mean()), float(diffs.std(ddof=1))
    n = len(diffs)
    star = abs(mean) > 2 * sd if sd > 0 else abs(mean) > 0

    # The zero-variance cases are NOT one case and must not share a fallback.
    # An earlier version returned p = 0 whenever sd == 0, which scored "every
    # seed differed by exactly nothing" as maximally significant - and since the
    # dynamic tier adds no columns at all at r=1, that fabricated 20 significant
    # results out of cells whose differences were identically zero. Caught by the
    # +0.0000 +/- 0.0000  q=0.0000 rows in the first run.
    #   all differences exactly zero  -> no effect whatsoever  -> p = 1
    #   constant NON-zero difference  -> a perfectly repeatable effect -> p = 0
    if sd == 0:
        t_p = 1.0 if mean == 0 else 0.0
    else:
        t_p = float(ttest_rel(diffs, np.zeros_like(diffs)).pvalue)
    pos = int((diffs > 0).sum())
    nz = int((diffs != 0).sum())
    sign_p = float(binomtest(pos, nz, 0.5).pvalue) if nz else 1.0
    return {"mean": mean, "sd": sd, "n": n, "star": star,
            "p_t": t_p, "p_sign": sign_p}


def bh(pvals: np.ndarray) -> np.ndarray:
    """
    Benjamini-Hochberg step-up q-values.

    Written out rather than imported so the monotonicity enforcement is visible:
    the cumulative-minimum pass from the largest p downward is what makes the
    q-values a valid step-up procedure, and it is the step most hand-rolled BH
    implementations get wrong.
    """
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    ranked = p[order] * m / (np.arange(m) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(m)
    q[order] = np.clip(ranked, 0, 1)
    return q


def by(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Yekutieli - BH scaled by the harmonic number; holds under any dependence."""
    m = len(pvals)
    c_m = np.sum(1.0 / np.arange(1, m + 1))
    return np.clip(bh(pvals) * c_m, 0, 1)


def build_families(tags: list[str]) -> dict[str, pd.DataFrame]:
    """
    The four families the document actually makes claims in.

    A "family" is the set of comparisons a reader would scan together looking for
    stars. That is the right unit for FDR: correcting across all 3,204 cells would
    be correcting across questions nobody asks jointly, and correcting within a
    single row would not be correcting at all.
    """
    fams = {"hop_gain": [], "edge_tier": [], "subgraph_tier": [], "dynamic_tier": []}

    for tag in tags:
        d = load(tag)
        for target in TARGETS:
            # Family 1: marginal value of one more hop, at the richest structural tier.
            for a, b in [(0, 1), (1, 2), (2, 3)]:
                diffs = paired(d, target, FULL, "radius", a, b)
                if diffs is not None:
                    fams["hop_gain"].append(
                        {"network": tag, "target": target, "comparison": f"r{a}->r{b}",
                         **score(diffs)})
            # Families 2-4: marginal value of one more tier, at fixed radius.
            for fam, lo, hi in [("edge_tier", NODE, EDGE),
                                ("subgraph_tier", EDGE, FULL),
                                ("dynamic_tier", FULL, DYN)]:
                for r in [1, 2, 3]:
                    diffs = paired(d, target, r, "richness", lo, hi)
                    if diffs is not None:
                        fams[fam].append(
                            {"network": tag, "target": target, "comparison": f"r={r}",
                             **score(diffs)})

    out = {}
    for name, rows in fams.items():
        if not rows:
            continue
        f = pd.DataFrame(rows)
        f["q_bh"] = bh(f["p_t"].to_numpy())
        f["q_by"] = by(f["p_t"].to_numpy())
        out[name] = f
    return out


def main() -> None:
    tags = discover_networks()
    print("=" * 78)
    print("A4 - MULTIPLICITY CONTROL")
    print("=" * 78)
    print(f"networks: {', '.join(tags)}")
    print("no fits - every p-value below is computed from cached per-seed tau\n")

    print("The existing star rule is |mean| > 2*sd of the paired per-seed difference.")
    print("On n seeds the paired t-statistic is sqrt(n)*(mean/sd), so the rule is")
    print("|t_(n-1)| > 2*sqrt(n): on 10 seeds |t_9| > 6.32, two-sided alpha = 1.4e-4.")
    print("Every star therefore clears any BH threshold a family of this size can")
    print("set (smallest is 0.05/60 = 8.3e-4): 'starred but not BH-significant' is")
    print("0 by construction. The informative count is the reverse - BH-significant")
    print("comparisons that were never starred. (Corrected 2026-09-11, P3-01.)\n")

    fams = build_families(tags)
    summary = []

    for name, f in fams.items():
        n = len(f)
        stars = int(f["star"].sum())
        # Expected false stars if every effect in the family were truly zero:
        # sum over comparisons of P(|t_{k-1}| > 2*sqrt(k)) at each comparison's
        # own seed count k (all 10 today, so this is n * 1.37e-4). Computed
        # from the t distribution rather than the old 0.046 * n, which was
        # P(|z| > 2) applied to the wrong statistic (P3-01, 2026-09-11).
        star_alpha = 2.0 * t_dist.sf(2.0 * np.sqrt(f["n"].to_numpy(dtype=float)),
                                     f["n"].to_numpy(dtype=float) - 1)
        expected_null = float(star_alpha.sum())
        print("=" * 78)
        print(f"FAMILY: {name}   ({n} comparisons)")
        print("=" * 78)
        print(f"  starred by the 2-sd rule      : {stars}")
        print(f"  expected under a global null  : {expected_null:.3f}   "
              f"(star rule two-sided alpha at n=10: {2.0 * t_dist.sf(2.0 * np.sqrt(10), 9):.2e})")
        for thr in (0.05, 0.01):
            print(f"  survive BH at q < {thr:<5}       : {int((f.q_bh < thr).sum())}"
                  f"    (BY, any dependence: {int((f.q_by < thr).sum())})")

        # The interesting rows: starred but not surviving, or surviving unstarred.
        lost = f[(f.star) & (f.q_bh >= 0.05)]
        gained = f[(~f.star) & (f.q_bh < 0.05)]
        print(f"\n  starred but q >= 0.05 (would be withdrawn): {len(lost)}")
        for _, r in lost.iterrows():
            print(f"    {r.network:20s} {r.target:13s} {r.comparison:8s} "
                  f"{r['mean']:+.4f} +/- {r['sd']:.4f}   q={r.q_bh:.3f}")
        print(f"  unstarred but q < 0.05 (currently under-claimed): {len(gained)}")
        for _, r in gained.head(8).iterrows():
            print(f"    {r.network:20s} {r.target:13s} {r.comparison:8s} "
                  f"{r['mean']:+.4f} +/- {r['sd']:.4f}   q={r.q_bh:.4f}")
        if len(gained) > 8:
            print(f"    ... and {len(gained) - 8} more")

        # A star on an effect smaller than the project's own reporting precision
        # is a different problem from a star that fails FDR, and needs saying.
        tiny = f[(f.star) & (f["mean"].abs() < 0.001)]
        print(f"\n  starred AND |gain| < 0.001 (significant but below 3-dp reporting): "
              f"{len(tiny)}")
        for _, r in tiny.head(6).iterrows():
            print(f"    {r.network:20s} {r.target:13s} {r.comparison:8s} "
                  f"{r['mean']:+.5f}   q={r.q_bh:.4f}")
        if len(tiny) > 6:
            print(f"    ... and {len(tiny) - 6} more")
        print()

        summary.append({"family": name, "n": n, "stars": stars,
                        "expected_null": round(expected_null, 4),
                        "bh_05": int((f.q_bh < 0.05).sum()),
                        "by_05": int((f.q_by < 0.05).sum()),
                        "withdrawn": len(lost), "tiny": len(tiny)})

    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(pd.DataFrame(summary).to_string(index=False))

    allf = pd.concat([f.assign(family=k) for k, f in fams.items()])
    allf.to_csv("results/multiplicity.csv", index=False)
    print("\nwrote results/multiplicity.csv")


if __name__ == "__main__":
    main()

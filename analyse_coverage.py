"""
A2 - ball coverage: how much of each graph does a radius-r observer actually see?

WHY THIS EXISTS
---------------
Every headline in this project is indexed by RADIUS. The referee objection (M3) is
that radius is a proxy for something much less interesting: the FRACTION OF THE
GRAPH YOU ARE ALLOWED TO SEE. On a graph with a small effective diameter, r=3 is
not a "local" view at all - it is the whole graph with extra steps, and a result
that says "three hops is enough" collapses into "seeing everything is enough".

SNAP publishes a 90th-percentile effective diameter of 2.9 for email-Eu-core.
email is also the corpus outlier in two independent findings. Those two facts have
to be put next to each other before either is quoted again.

This script does that. It computes NOTHING new - the ball sizes have been sitting
in cache_features_*.csv the whole time - and it fits NOTHING. It is a re-plot of
existing results against a different x-axis. That is the entire contribution, and
it is enough, because the axis was never plotted.

THE PREDICTIONS WERE WRITTEN FIRST
----------------------------------
docs/prereg_A2_coverage.md, dated 2026-08-28, before any number below was computed.
Section 5 of this script scores them mechanically. That ordering is the point: this
analysis can undermine the project's own framing, which is exactly the situation
where a post-hoc prediction is worth nothing.

Sections:
  1. Coverage distributions - median, IQR, share of nodes seeing over half the graph.
  2. What drives coverage: n or density?
  3. P(r) re-plotted against coverage and against measured feature cost.
  4. The email question, stated as a matched-coverage comparison.
  5. Mechanical scoring of the five pre-registered predictions.
"""

import glob
import os
import re

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# Reuse the sweep-side helpers rather than reimplementing them. `curve` in
# particular already handles the paired-seed structure correctly, and a second
# implementation of it here would be the obvious place for the two to drift.
from analyse import FULL, curve, discover_networks, load

RADII = [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# 1. Coverage
# ---------------------------------------------------------------------------

def ball_sizes(tag: str) -> pd.DataFrame:
    """
    |B_r(v)| for every node, from columns that are already cached.

    The `1 +` is not cosmetic: `reach_within_r` counts nodes reachable within r
    hops EXCLUDING v itself, and `degree` obviously excludes v too. A ball
    contains its centre. Getting this wrong would understate coverage by 1/n per
    node, which is negligible on Gnutella and not negligible on email at n=986.

    r=0 is the node alone. That is the degenerate case the sweep actually runs -
    "radius 0" in this project means "degree-tier features only", i.e. what you
    can say about v without leaving v - so |B_0| = 1 is the honest entry, and it
    is what makes the r=0 coverage column a sanity check (1/n) rather than data.
    """
    feats = pd.read_csv(f"cache_features_{tag}.csv")
    n = len(feats)

    balls = pd.DataFrame(index=feats.index)
    balls[0] = 1.0
    balls[1] = 1.0 + feats["degree"]
    balls[2] = 1.0 + feats["reach_within_2"]
    balls[3] = 1.0 + feats["reach_within_3"]

    # A ball cannot be bigger than the graph, and cannot shrink as r grows.
    # Both have been true every time this has been run; they are asserted rather
    # than assumed because a silently monotone-broken column would produce a
    # perfectly plausible-looking coverage table.
    for r in RADII:
        assert (balls[r] <= n).all(), f"{tag}: |B_{r}| exceeds n"
    for a, b in zip(RADII, RADII[1:]):
        assert (balls[b] >= balls[a]).all(), f"{tag}: |B_{b}| < |B_{a}| for some node"

    cov = balls / n
    cov["n"] = n
    return cov


def coverage_table(tags: list[str]) -> pd.DataFrame:
    """Median / IQR / share-over-half, per network per radius."""
    rows = []
    for tag in tags:
        cov = ball_sizes(tag)
        n = int(cov["n"].iloc[0])
        feats = pd.read_csv(f"cache_features_{tag}.csv")
        mean_degree = float(feats["degree"].mean())
        for r in RADII:
            c = cov[r]
            rows.append({
                "network": tag, "n": n, "mean_degree": mean_degree, "radius": r,
                "median": float(c.median()),
                "q25": float(c.quantile(0.25)), "q75": float(c.quantile(0.75)),
                "share_over_half": float((c > 0.5).mean()),
                "median_ball": float((c * n).median()),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 5. Scoring the pre-registration
# ---------------------------------------------------------------------------

def directional_deltas(path: str = "results/RESULTS_failures.txt") -> dict:
    """
    max |Cliff's d| in the DIRECTIONAL contrast, per (network, target).

    Parsed from the text dump rather than the study doc, deliberately. The
    make_fig2.py incident (Finding 8) was precisely a case of a derived artefact
    disagreeing with the text dump it came from, and the dump was the one that
    was right. So the dump is the source of truth here, and if this parser ever
    disagrees with the study doc's table the dump wins.

    Returns {} rather than raising if the file is absent - P5 then reports as
    unscoreable, which is the honest outcome, not a crash.
    """
    if not os.path.exists(path):
        return {}

    out = {}
    net = target = None
    in_directional = False

    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^(\S+)\s+n=[\d,]+\s+reference:", line)
        if m:
            net, target, in_directional = m.group(1), None, False
            continue
        m = re.match(r"^--- target: (\S+) ---", line)
        if m:
            target, in_directional = m.group(1), False
            continue
        if "UNDER vs OVER" in line:
            in_directional = True
            continue
        # A BLANK LINE ends the block. This is the terminator that matters and
        # the first version of this parser got it wrong: it listed the section
        # headers it expected to see next and missed "WHAT HOPS 2-3 RESCUE",
        # so it ran on into the rescue table and returned that table's maximum.
        # Caught by cross-checking against the study doc's own numbers - four of
        # five networks disagreed - which is the only reason it is not still
        # here. Blank-line termination needs no list to keep up to date.
        if in_directional and not line.strip():
            in_directional = False
            continue
        if in_directional and net and target:
            # Rows look like: "    [L] label   median  median  d  size  p"
            # The Cliff d is the third-from-last numeric field.
            fields = line.split()
            if len(fields) >= 4 and fields[0] in ("[L]", "[G]"):
                try:
                    d = float(fields[-3])
                except ValueError:
                    continue
                key = (net, target)
                out[key] = max(out.get(key, 0.0), abs(d))
    return out


def score_predictions(covt: pd.DataFrame, deltas: dict) -> None:
    print("\n" + "=" * 78)
    print("5. SCORING docs/prereg_A2_coverage.md  (written before these numbers existed)")
    print("=" * 78)

    at3 = covt[covt.radius == 3].set_index("network")
    order = at3["median"].sort_values(ascending=False)

    # --- P1 -----------------------------------------------------------------
    em = at3.loc["email-Eu-core", "median"] if "email-Eu-core" in at3.index else np.nan
    p1 = (order.index[0] == "email-Eu-core") and (em > 0.90)
    print(f"\nP1  email has highest 3-ball coverage, median > 0.90")
    print(f"    email median = {em:.4f}; rank 1 = {order.index[0]}")
    print(f"    -> {'CONFIRMED' if p1 else 'FALSIFIED'}")

    # --- P2 -----------------------------------------------------------------
    # Does coverage track 1/n better than it tracks mean degree? Spearman on
    # five points is a description, not an estimate - reported as such.
    rho_n = spearmanr(at3["n"], at3["median"]).statistic
    rho_k = spearmanr(at3["mean_degree"], at3["median"]).statistic
    fb_below_email = (at3.loc["facebook_combined", "median"]
                      < at3.loc["email-Eu-core", "median"])
    p2 = abs(rho_n) > abs(rho_k) and fb_below_email
    print(f"\nP2  coverage driven by n, not density")
    print(f"    spearman(n, coverage)      = {rho_n:+.3f}")
    print(f"    spearman(<k>, coverage)    = {rho_k:+.3f}")
    print(f"    facebook below email?        {fb_below_email}")
    print(f"    -> {'CONFIRMED' if p2 else 'FALSIFIED'}  (n=5; a description of five points)")

    # --- P3 -----------------------------------------------------------------
    ratios = []
    for r in RADII[1:]:
        a = covt[(covt.network == "ca-GrQc") & (covt.radius == r)]["median"].iloc[0]
        b = covt[(covt.network == "ca-HepTh") & (covt.radius == r)]["median"].iloc[0]
        ratios.append(max(a, b) / min(a, b))
    p3 = max(ratios) <= 2.0
    print(f"\nP3  collaboration pair within a factor of 2 at every r")
    print(f"    ratios at r=1,2,3: " + ", ".join(f"{x:.2f}x" for x in ratios))
    print(f"    -> {'CONFIRMED' if p3 else 'FALSIFIED'}")

    # --- P4 -----------------------------------------------------------------
    # Untestable-by-design case: does ANY other network reach email's r=3
    # coverage (within 0.10) at ANY radius? If not, the comparison cannot be
    # made on this corpus and must be reported as such - see the prereg.
    matches = []
    for _, row in covt.iterrows():
        if row.network == "email-Eu-core":
            continue
        if abs(row["median"] - em) <= 0.10:
            matches.append((row.network, int(row.radius), row["median"]))
    print(f"\nP4  email's anomalies sit at a coverage nobody else reaches")
    if matches:
        print("    matched-coverage cells found:")
        for nm, r, v in matches:
            print(f"      {nm} at r={r}: {v:.4f}")
        print("    -> TESTABLE; compare email's behaviour against these cells (section 4)")
    else:
        print(f"    no other (network, radius) cell within 0.10 of email's {em:.4f}")
        print("    -> UNTESTABLE ON THIS CORPUS. Per the prereg this is NOT support;")
        print("       it is the strongest argument in the project for the synthetic corpus.")

    # --- P5 -----------------------------------------------------------------
    print(f"\nP5  directional blind spot is partly a coverage effect (|rho| >= 0.7)")
    if not deltas:
        print("    results/RESULTS_failures.txt not parsed - UNSCOREABLE")
        return
    pairs = [(at3.loc[net, "median"], d)
             for (net, tgt), d in deltas.items()
             if tgt == "spread_mean" and net in at3.index]
    if len(pairs) < 3:
        print(f"    only {len(pairs)} networks parsed - UNSCOREABLE")
        return
    cov_v, del_v = zip(*pairs)
    rho = spearmanr(cov_v, del_v).statistic
    print(f"    n = {len(pairs)} networks, spearman(coverage_r3, max|delta|) = {rho:+.3f}")
    print(f"    -> {'CONFIRMED' if abs(rho) >= 0.7 else 'FALSIFIED'}")
    print("    NOTE: whichever way this falls it is five points. Finding 8's own")
    print("          rho = 0.900 carries the same caveat and the same n.")


# ---------------------------------------------------------------------------

def main() -> None:
    tags = discover_networks()
    print("=" * 78)
    print("A2 - BALL COVERAGE: what a radius-r observer actually sees")
    print("=" * 78)
    print(f"networks: {', '.join(tags)}")
    print("no fits, no traversal - every number below is a read of cached columns")

    covt = coverage_table(tags)

    # --- 1 ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("1. COVERAGE DISTRIBUTIONS  |B_r(v)| / n")
    print("=" * 78)
    for tag in tags:
        sub = covt[covt.network == tag]
        n = int(sub["n"].iloc[0])
        k = float(sub["mean_degree"].iloc[0])
        print(f"\n{tag}  (n = {n:,}, <k> = {k:.1f})")
        print("  r | median cov |      IQR       | >50% of graph | median |B_r|")
        print("  --+------------+----------------+---------------+--------------")
        for _, row in sub.iterrows():
            print(f"  {int(row.radius)} |   {row['median']:.4f}   | "
                  f"{row.q25:.4f}-{row.q75:.4f} |     {row.share_over_half:6.1%}    |"
                  f" {row.median_ball:10,.0f}")

    # --- 2 ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("2. WHAT DRIVES COVERAGE - n OR DENSITY?")
    print("=" * 78)
    at3 = covt[covt.radius == 3].sort_values("median", ascending=False)
    print("\n  network              n      <k>   median cov r=3   >50% at r=3")
    print("  " + "-" * 68)
    for _, row in at3.iterrows():
        print(f"  {row.network:20s} {row.n:6,}  {row.mean_degree:5.1f}   "
              f"    {row['median']:.4f}       {row.share_over_half:8.1%}")

    # --- 3 ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("3. P(r) RE-PLOTTED AGAINST COVERAGE AND AGAINST MEASURED COST")
    print("=" * 78)
    print("\nThe cost column is `feature_seconds` from the sweep itself - measured")
    print("wall clock, not a proxy. It is the honest x-axis for 'what did this hop")
    print("cost me', and it is the one a practitioner actually pays.\n")
    for tag in tags:
        d = load(tag)
        cov_by_r = covt[covt.network == tag].set_index("radius")["median"]
        print(f"\n{tag}")
        print("  target        r  median cov   feat sec        tau")
        print("  " + "-" * 54)
        for target in ["spread_mean", "betweenness"]:
            c = curve(d, target)
            for r in c.index:
                sec = d[(d.target == target) & (d.richness == FULL)
                        & (d.radius == r)]["feature_seconds"].mean()
                print(f"  {target:12s} {int(r)}      {cov_by_r[r]:.4f}   {sec:8.1f}"
                      f"   {c.loc[r, 'tau_mean']:.4f}")

    # --- 4 ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("4. THE EMAIL QUESTION, AS A MATCHED-COVERAGE COMPARISON")
    print("=" * 78)
    em3 = covt[(covt.network == "email-Eu-core") & (covt.radius == 3)]["median"].iloc[0]
    print(f"\nemail-Eu-core median 3-ball coverage: {em3:.4f}")
    print("Every other (network, radius) cell, by distance from it:\n")
    others = covt[covt.network != "email-Eu-core"].copy()
    others["gap"] = (others["median"] - em3).abs()
    for _, row in others.sort_values("gap").head(8).iterrows():
        print(f"  {row.network:20s} r={int(row.radius)}  cov={row['median']:.4f}"
              f"   gap={row.gap:.4f}")

    # --- 5 ------------------------------------------------------------------
    score_predictions(covt, directional_deltas())

    covt.to_csv("results/coverage.csv", index=False)
    print("\n\nwrote results/coverage.csv")


if __name__ == "__main__":
    main()

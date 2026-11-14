"""
analysis/analyse_transfer.py
============================
Scores the leave-one-graph-out transfer run against docs/prereg/prereg_transfer.md.

Reads results/transfer/transfer_cells.csv (from probes/probe_transfer.py), the
within-graph sweeps through `analyse.load`, and the closed-form table from
analysis/analyse_closed_form.py. Writes results/RESULTS_transfer.txt.

HOW EACH PREDICTION IS SCORED
-----------------------------
All comparisons use the mean over the three transfer seeds.

  gap       = within-graph P(r) - transfer tau, at the same radius and tier.
              Positive means transfer is worse.
  P1        spread_mean, r=3: gap > 0 on every network and mean gap >= 0.02.
  P2        per target: transfer(r=3) - transfer(r=0) > 2 x sd on >= 4 of 5
            networks. The sd is that of the per-seed difference, over the three
            seeds: the project's paired-seed star rule. The probe draws a fresh
            training subsample per radius, so the pairing is by seed index only.
  P3        betweenness, r=3: gap >= 0.05 on email-Eu-core or facebook_combined.
  P4        spread_mean, r=3: transfer beats the best closed-form rule at r=3
            on >= 3 of 5 networks. Counter: the rule matches or beats it on >= 3.

The post-hoc arms are printed beside the primary when their folders exist:
`no-size` drops `degree_normalized` (addendum 1), `pct-feat` replaces every
feature by its per-graph percentile rank (addendum 2, not a strictly local
predictor). Neither enters the scoring.

Run from the repository root, after the probe and analyse_closed_form.py:
    python analysis/analyse_transfer.py
"""
import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import io
import os
import sys
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

from analyse import FULL, load

PRIMARY = os.path.join("results", "transfer", "transfer_cells.csv")
# Post-hoc arms (prereg addenda 1 and 2): label -> cells file. Printed, never scored.
POSTHOC = {
    "no-size": os.path.join("results", "transfer_nosize", "transfer_cells.csv"),
    "pct-feat": os.path.join("results", "transfer_featrank", "transfer_cells.csv"),
}
CLOSED = os.path.join("results", "closed_form", "closed_form_baselines.csv")
OUT_TXT = os.path.join("results", "RESULTS_transfer.txt")
DENSE = ("email-Eu-core", "facebook_combined")


def summarise(cells: pd.DataFrame) -> pd.DataFrame:
    g = cells.groupby(["target", "holdout", "radius"])
    out = g.agg(tau=("kendall_tau", "mean"), sd=("kendall_tau", "std"),
                seeds=("kendall_tau", "size"),
                p1=("precision_at_1pct", "mean"), p5=("precision_at_5pct", "mean"),
                n_features=("n_features", "first")).reset_index()
    return out


def within_graph(tags: list[str], targets: list[str]) -> pd.DataFrame:
    rows = []
    for tag in tags:
        d = load(tag)
        d = d[(d.richness == FULL) & d.target.isin(targets)]
        for (target, r), x in d.groupby(["target", "radius"]):
            rows.append({"target": target, "holdout": tag, "radius": int(r),
                         "within": float(x.kendall_tau.mean()),
                         "within_sd": float(x.kendall_tau.std(ddof=1))})
    return pd.DataFrame(rows)


def closed_form() -> pd.DataFrame:
    if not os.path.exists(CLOSED):
        raise SystemExit(f"{CLOSED} missing - run analysis/analyse_closed_form.py first")
    cf = pd.read_csv(CLOSED)
    return cf.rename(columns={"network": "holdout"})[
        ["holdout", "target", "radius", "best_rule", "best_rule_tau",
         "best_structural_rule", "best_structural_tau", "tau_degree"]]


def paired_gain(cells: pd.DataFrame, target: str, hold: str) -> tuple[float, float]:
    """Mean and sd over seeds of tau(r=3) - tau(r=0), paired by seed index."""
    c = cells[(cells.target == target) & (cells.holdout == hold)]
    a = c[c.radius == 3].set_index("seed").kendall_tau
    b = c[c.radius == 0].set_index("seed").kendall_tau
    d = (a - b).dropna()
    return float(d.mean()), float(d.std(ddof=1)) if len(d) > 1 else np.nan


def verdict(ok: bool) -> str:
    return "SUPPORTED" if ok else "NOT SUPPORTED"


def report(cells: pd.DataFrame, tab: pd.DataFrame, post: dict[str, pd.DataFrame]) -> str:
    buf = io.StringIO()
    tags = sorted(tab.holdout.unique())
    targets = [t for t in ("spread_mean", "betweenness") if t in set(tab.target)]
    with redirect_stdout(buf):
        print("=" * 78)
        print("LEAVE-ONE-GRAPH-OUT TRANSFER (pre-registered: docs/prereg/prereg_transfer.md)")
        print("transfer = train on the other four networks, rank every node of this one")
        print("within   = the project's within-graph out-of-fold P(r), same tier")
        print("gap      = within - transfer (positive = transfer is worse)")
        print("rule     = best closed-form rule at that radius, in-sample (analyse_closed_form)")
        if "no-size" in post:
            print("no-size  = POST-HOC arm 1, without degree_normalized; not scored")
        if "pct-feat" in post:
            print("pct-feat = POST-HOC arm 2, per-graph percentile features; not scored and")
            print("           not strictly local (reads each column's distribution over the graph)")
        print("=" * 78)
        for target in targets:
            for hold in tags:
                g = tab[(tab.target == target) & (tab.holdout == hold)].sort_values("radius")
                deg = g.tau_degree.dropna()
                print(f"\n{hold} / {target}   tau_b(y, degree) = "
                      f"{deg.iloc[0] if len(deg) else np.nan:.4f}")
                head = (f"  {'r':>2} {'transfer':>17} {'within':>8} {'gap':>8} "
                        f"{'rule':>8} {'P@1%':>6} {'P@5%':>6}")
                for label in post:
                    head += f" {label:>8}"
                print(head)
                for _, x in g.iterrows():
                    line = (f"  {int(x.radius):>2} {x.tau:>8.4f} +/-{x.sd:.4f} {x.within:>8.4f} "
                            f"{x.within - x.tau:>+8.4f} {x.best_rule_tau:>8.4f} "
                            f"{x.p1:>6.3f} {x.p5:>6.3f}")
                    for arm in post.values():
                        m = arm[(arm.target == target) & (arm.holdout == hold)
                                & (arm.radius == x.radius)]
                        line += f" {m.tau.iloc[0]:>8.4f}" if len(m) else f" {'-':>8}"
                    print(line)

        print("\n" + "=" * 78)
        print("PREDICTIONS")
        print("=" * 78)
        r3 = tab[tab.radius == 3].set_index(["target", "holdout"])

        if "spread_mean" in targets:
            s = r3.loc["spread_mean"]
            gaps = s.within - s.tau
            p1 = bool(len(gaps) == len(tags) and (gaps > 0).all() and gaps.mean() >= 0.02)
            print(f"\nP1  spread_mean r=3, gap > 0 on all and mean gap >= 0.02: {verdict(p1)}")
            for h, v in gaps.items():
                print(f"      {h:18s} gap {v:+.4f}")
            print(f"      mean gap {gaps.mean():+.4f}")

        print("\nP2  transfer(r=3) - transfer(r=0) > 2 x paired seed sd on >= 4 of 5")
        for target in targets:
            hits = 0
            for hold in tags:
                m, sd = paired_gain(cells, target, hold)
                ok = bool(np.isfinite(sd) and m > 2 * sd)
                hits += ok
                print(f"      {target:12s} {hold:18s} gain {m:+.4f}  sd {sd:.4f}  "
                      f"{'*' if ok else ' '}")
            print(f"    {target}: {hits}/{len(tags)} -> {verdict(hits >= 4)}")

        if "betweenness" in targets:
            b = r3.loc["betweenness"]
            gaps = b.within - b.tau
            p3 = bool(any(gaps.get(h, -np.inf) >= 0.05 for h in DENSE))
            print(f"\nP3  betweenness r=3, gap >= 0.05 on email-Eu-core or facebook_combined: "
                  f"{verdict(p3)}")
            for h, v in gaps.items():
                print(f"      {h:18s} gap {v:+.4f}{'   (dense)' if h in DENSE else ''}")

        if "spread_mean" in targets:
            s = r3.loc["spread_mean"]
            margin = s.tau - s.best_rule_tau
            wins = int((margin > 0).sum())
            print(f"\nP4  spread_mean r=3, transfer beats the best closed-form rule on >= 3 of 5: "
                  f"{verdict(wins >= 3)}  ({wins}/{len(s)})")
            print(f"    Counter (rule matches or beats transfer on >= 3 of 5): "
                  f"{verdict(len(s) - wins >= 3)}")
            for h, x in s.iterrows():
                print(f"      {h:18s} transfer {x.tau:.4f}  {x.best_rule:22s} {x.best_rule_tau:.4f}"
                      f"  margin {x.tau - x.best_rule_tau:+.4f}")
            print("    Not pre-registered: perc_reach_r is in the dynamic tier (it uses p, which")
            print("    the transferred forest does not see). Against the best STRUCTURAL rule:")
            for h, x in s.iterrows():
                print(f"      {h:18s} transfer {x.tau:.4f}  {x.best_structural_rule:22s} "
                      f"{x.best_structural_tau:.4f}  margin {x.tau - x.best_structural_tau:+.4f}")

        if post:
            print("\n" + "=" * 78)
            print("POST-HOC ARMS AT r=3 (not scored): mean tau over networks, and wins over")
            print("the best structural rule")
            print("=" * 78)
            arms = {"registered": tab[["target", "holdout", "radius", "tau"]], **post}
            for target in targets:
                ref = tab[(tab.target == target) & (tab.radius == 3)].set_index("holdout")
                for label, arm in arms.items():
                    a = arm[(arm.target == target) & (arm.radius == 3)].set_index("holdout").tau
                    a = a.reindex(ref.index)
                    if a.isna().all():
                        continue
                    wins = int((a > ref.best_structural_tau).sum())
                    print(f"  {target:12s} {label:10s} mean tau {a.mean():.4f}   "
                          f"beats rule on {wins}/{a.notna().sum()}   "
                          f"mean gap to within-graph {(ref.within - a).mean():+.4f}")

        print("\n" + "=" * 78)
        print("NOT PRE-REGISTERED: transfer at r=0 against the degree ranking")
        print("=" * 78)
        print("At r=0 the only inputs are degree and degree_normalized = k/(n-1). The best")
        print("possible ranking is degree itself; anything below tau_b(y, degree) is lost in")
        print("the forest, not in the information.")
        z = tab[tab.radius == 0]
        for _, x in z.sort_values(["target", "holdout"]).iterrows():
            line = (f"  {x.target:12s} {x.holdout:18s} tau_b(y,deg) {x.tau_degree:.4f}  "
                    f"transfer {x.tau:.4f} +/-{x.sd:.4f}")
            arm = post.get("no-size")
            if arm is not None:
                m = arm[(arm.target == x.target) & (arm.holdout == x.holdout) & (arm.radius == 0)]
                if len(m):
                    line += f"  no-size {m.tau.iloc[0]:.4f} +/-{m.sd.iloc[0]:.4f}"
            print(line)
    return buf.getvalue()


def main() -> None:
    if not os.path.exists(PRIMARY):
        raise SystemExit(f"{PRIMARY} missing - run probes/probe_transfer.py first")
    cells = pd.read_csv(PRIMARY).drop_duplicates(
        subset=["target", "holdout", "radius", "seed"], keep="last")
    s = summarise(cells)
    incomplete = s[s.seeds < 3]
    if len(incomplete):
        print(f"WARNING: {len(incomplete)} (target, holdout, radius) cells have < 3 seeds; "
              "the run is not finished and the verdicts below are provisional.\n")
    tags = sorted(s.holdout.unique())
    targets = sorted(s.target.unique())
    tab = (s.merge(within_graph(tags, targets), on=["target", "holdout", "radius"], how="left")
             .merge(closed_form(), on=["target", "holdout", "radius"], how="left"))
    # tau_b(y, degree) lives on the r=0 row of the closed-form table; carry it to every radius.
    deg = tab[tab.radius == 0].set_index(["target", "holdout"]).tau_degree
    tab["tau_degree"] = [deg.get((t, h), np.nan) for t, h in zip(tab.target, tab.holdout)]

    post = {label: summarise(pd.read_csv(path).drop_duplicates(
                subset=["target", "holdout", "radius", "seed"], keep="last"))
            for label, path in POSTHOC.items() if os.path.exists(path)}

    text = report(cells, tab, post)
    with open(OUT_TXT, "w", encoding="utf-8") as fh:
        fh.write(text)
    sys.stdout.write(text)
    print(f"\nwrote {OUT_TXT}")


if __name__ == "__main__":
    main()

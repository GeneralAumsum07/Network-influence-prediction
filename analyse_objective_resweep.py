"""
Score the betweenness re-sweep against `docs/decl_objective_resweep.md`.

Three questions, and only the third is genuinely open:

  1. Does the richness ladder COMPRESS under a corrected objective? Declared
     prediction: every facebook rung gain shrinks, and the r=2 subgraph rung
     lands near the +0.0436 already measured rather than the +0.1291 published.
  2. Do the other four networks stay put? Declared: no rung gain moves by
     more than 0.02.
  3. What happens to TOP-K? NO PREDICTION WAS OFFERED. Squared error
     over-weights exactly the huge-betweenness nodes that precision@1% cares
     about, so the correction may well help bulk tau and HURT precision@1%.
     That outcome is a result and must be reported, not buried.

WHAT "RAW" MEANS HERE
---------------------
The published `sweep_<tag>.csv`, filtered to betweenness. Both arms therefore
come from the same pipeline, the same folds and the same forest; the training
objective is the only difference. That equivalence is not assumed - it was
checked before the run (registry `rf_log1p` reproduces the probe's log1p arm to
1.11e-16, and `make_rf` reproduces the published inline forest to 1.11e-16).
"""
import os

import numpy as np
import pandas as pd

NETS = ["ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined",
        "p2p-Gnutella08"]
RADII = [0, 1, 2, 3]

# The nested ladder, as rungs. Each pair is (lower tier, higher tier); the gain
# is what the higher tier's columns buy on top of everything below them.
RUNGS = [
    ("node", "node+edge", "edge"),
    ("node+edge", "node+edge+subgraph", "subgraph"),
    ("node+edge+subgraph", "node+edge+subgraph+dynamic", "dynamic"),
]


def load():
    """Both arms, betweenness only, tagged by objective."""
    frames = []
    for tag in NETS:
        raw = pd.read_csv(f"sweep_{tag}.csv")
        raw = raw[raw.target == "betweenness"].copy()
        raw["objective"] = "raw"
        frames.append(raw)

        p = os.path.join("estimators", f"sweep_{tag}__rf_log1p.csv")
        if not os.path.exists(p):
            print(f"  (missing {p} - re-sweep incomplete for {tag})")
            continue
        lg = pd.read_csv(p)
        lg = lg[lg.target == "betweenness"].copy()
        lg["objective"] = "log1p"
        frames.append(lg)
    return pd.concat(frames, ignore_index=True)


def is_degenerate(d, tag, r, lo, hi):
    """
    True when the two tiers hold the SAME columns, so the rung is 0 by
    construction rather than by measurement.

    This is not hypothetical and it is not confined to r=0. On ca-GrQc:

        radius  node  node+edge  +subgraph  +dynamic
          0        2      2          2         2      <- every rung degenerate
          1       17     38         62        62      <- dynamic rung degenerate
          2       35     80        144       145
          3       45     93        168       170

    Detected from the recorded column count rather than derived from the radius,
    because the pattern differs per network and a hardcoded rule would quietly
    be wrong on one of them. A degenerate rung reported as "+0.0000, unchanged"
    would read as evidence that the objective did not matter there, when in fact
    nothing was measured.
    """
    sub = d[(d.network == tag) & (d.radius == r)]
    n = sub.pivot_table(index="richness", values="n_features", aggfunc="first")
    if lo not in n.index or hi not in n.index:
        return False
    return n.loc[lo, "n_features"] == n.loc[hi, "n_features"]


def rung(d, tag, r, lo, hi, obj, metric):
    """
    Paired-within-seed gain for one rung. The project's standard: pair on seed,
    then take the mean and sd of the DIFFERENCES, never the difference of means.
    """
    sub = d[(d.network == tag) & (d.radius == r) & (d.objective == obj)]
    piv = sub.pivot_table(index="seed", columns="richness", values=metric)
    if not {lo, hi} <= set(piv.columns):
        return None
    diff = (piv[hi] - piv[lo]).dropna()
    if diff.empty:
        return None
    return diff.mean(), diff.std(ddof=1)


def table(d, metric, title):
    """Rung gains under both objectives, for one metric."""
    print("\n" + "=" * 82)
    print(title)
    print("=" * 82)
    print(f"\n  {'network':<20s} {'r':>2s}  {'rung':<10s}"
          f"{'raw':>10s}{'log1p':>10s}{'change':>10s}")
    out = []
    for tag in NETS:
        for r in RADII:
            for lo, hi, name in RUNGS:
                a = rung(d, tag, r, lo, hi, "raw", metric)
                b = rung(d, tag, r, lo, hi, "log1p", metric)
                if a is None or b is None:
                    continue
                if is_degenerate(d, tag, r, lo, hi):
                    # Shown, not hidden - but never scored, and never counted
                    # as a rung that "did not move".
                    print(f"  {tag:<20s} {r:>2d}  {name:<10s}"
                          f"{'':>10s}{'':>10s}{'':>4s}  (degenerate: "
                          f"identical columns)")
                    continue
                # A star marks a rung the project would call real under the raw
                # arm (|mean| > 2*sd), so a star that vanishes is visible.
                s_raw = "*" if abs(a[0]) > 2 * a[1] else " "
                s_log = "*" if abs(b[0]) > 2 * b[1] else " "
                out.append({"network": tag, "radius": r, "rung": name,
                            "raw": a[0], "log1p": b[0], "delta": b[0] - a[0]})
                print(f"  {tag:<20s} {r:>2d}  {name:<10s}"
                      f"{a[0]:>+9.4f}{s_raw}{b[0]:>+9.4f}{s_log}"
                      f"{b[0] - a[0]:>+10.4f}")
    return pd.DataFrame(out)


def main():
    d = load()
    if "log1p" not in set(d.objective):
        print("no log1p arm on disk yet - run the re-sweep first")
        return 1

    T = table(d, "kendall_tau",
              "1. RICHNESS RUNGS, betweenness - Kendall tau (the reported metric)")

    # --- the declared predictions -----------------------------------------
    print("\n" + "=" * 82)
    print("2. SCORING THE DECLARED PREDICTIONS")
    print("=" * 82)

    fb = T[T.network == "facebook_combined"]
    if fb.empty:
        # An empty frame makes every "all of them did X" test vacuously true.
        # This project does not get to report a prediction as MET on no data.
        print("\n  P1 facebook rungs shrink: NOT SCORED - no facebook log1p "
              "rows on disk (re-sweep incomplete)")
    else:
        shrank = int((fb.log1p.abs() < fb.raw.abs()).sum())
        print(f"\n  P1 facebook rungs shrink: {shrank}/{len(fb)} shrank"
              f"  -> {'MET' if shrank == len(fb) else 'NOT MET'}")

    cell = fb[(fb.radius == 2) & (fb.rung == "subgraph")]
    if not cell.empty:
        v = cell.log1p.iloc[0]
        print(f"  P1 facebook r=2 subgraph rung: published {cell.raw.iloc[0]:+.4f}"
              f" -> {v:+.4f}   (independently measured earlier: +0.0436;"
              f" agreement {abs(v - 0.0436):.4f})")

    others = T[T.network != "facebook_combined"]
    n_other_nets = others.network.nunique()
    big = others[others.delta.abs() > 0.02]
    if n_other_nets < 4:
        print(f"\n  P2 other four networks move <0.02: PARTIAL - only "
              f"{n_other_nets}/4 networks on disk, not scored")
    else:
        print(f"\n  P2 other four networks move <0.02: "
              f"{len(big)} of {len(others)} rungs exceed it"
              f"  -> {'MET' if big.empty else 'NOT MET'}")
    for _, x in big.iterrows():
        print(f"        {x.network:<20s} r={x.radius} {x.rung:<10s}"
              f" {x.raw:+.4f} -> {x['log1p']:+.4f}  ({x.delta:+.4f})")

    # --- the open question -------------------------------------------------
    for metric in ("precision_at_1pct", "precision_at_5pct"):
        table(d, metric, f"3. THE OPEN QUESTION - {metric} (no prediction made)")

    print("\n" + "=" * 82)
    print("4. DOES THE CORRECTION HELP TAU AND HURT TOP-K?")
    print("   The declaration flagged this as possible and refused to guess.")
    print("=" * 82)
    print(f"\n  {'network':<20s}{'r':>2s}{'tau raw':>9s}{'tau log':>9s}"
          f"{'p@1 raw':>9s}{'p@1 log':>9s}{'tau d':>9s}{'p@1 d':>9s}")
    FULLD = "node+edge+subgraph+dynamic"
    for tag in NETS:
        for r in RADII:
            row = {}
            for obj in ("raw", "log1p"):
                s = d[(d.network == tag) & (d.radius == r)
                      & (d.objective == obj) & (d.richness == FULLD)]
                if s.empty:
                    row = None
                    break
                row[obj] = (s.kendall_tau.mean(), s.precision_at_1pct.mean())
            if not row:
                continue
            dt = row["log1p"][0] - row["raw"][0]
            dp = row["log1p"][1] - row["raw"][1]
            flag = "  <-- tau up, top-k down" if dt > 0.002 and dp < -0.002 else ""
            print(f"  {tag:<20s}{r:>2d}{row['raw'][0]:>9.4f}{row['log1p'][0]:>9.4f}"
                  f"{row['raw'][1]:>9.4f}{row['log1p'][1]:>9.4f}"
                  f"{dt:>+9.4f}{dp:>+9.4f}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

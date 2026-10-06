"""
Read `probe_objective_horizon.py`'s output and answer one question:
does r*(eps) move when the training objective is corrected?

WHAT A READER SHOULD TAKE FROM EACH TABLE
-----------------------------------------
1. **Level.** How much tau the transform buys, per network and target. This is
   the effect whose SIZE was already known on one cell (+0.1838 on facebook
   betweenness r=2); here it is measured across the corpus. If it does not
   track target skew, the mechanism proposed in Finding 11 is wrong.

2. **Horizon.** The actual question. r*(eps) is recomputed with the project's
   own `r_star_per_seed`, not a reimplementation, so the numbers are directly
   comparable to the published horizons.

3. **Stability.** How often the modal r* wins across seeds, under each
   objective. A horizon that "does not move" but was never stable to begin with
   has not been shown to be robust - it has been shown to be noisy in the same
   way twice.

WHY THE CONTROL MATTERS FOR READING TABLE 2
-------------------------------------------
If horizons move on betweenness and NOT on spread_mean, the movement tracks the
skew and is attributable to the objective mismatch. If they move on both, the
transform is perturbing r* for some reason unrelated to the mismatch, and the
result is about the intervention rather than about Finding 11. Read table 2
against table 1 before concluding anything.
"""
import numpy as np
import pandas as pd

from analyse import r_star_per_seed

SRC = "results/objective_horizon_probe.csv"
EPS = [0.20, 0.10, 0.05, 0.02, 0.01]

TARGETS = ["betweenness", "spread_mean"]


def matrix(sub):
    """radius x seed table of tau, the shape r_star_per_seed expects."""
    return sub.pivot_table(index="radius", columns="seed", values="kendall_tau")


def main(src: str = SRC) -> None:
    # Wrapped in main() on 2026-09-11 by Claude Opus 5 (Task 6 finding
    # P2-10(c)): the analysis ran at import time, so importing this module
    # for its helpers re-ran the whole report. Behaviour when executed as a
    # script is unchanged.
    d = pd.read_csv(src)
    NETS = sorted(d.network.unique())

    # --- 1. what the transform buys, by target and network ---------------------
    print("=" * 78)
    print("1. LEVEL - tau at the richest structural tier, raw vs log1p objective")
    print("   (tau is scored against the ORIGINAL target under both)")
    print("=" * 78)
    print(f"\n  {'network':<20s} {'target':<13s} {'skew':>8s} {'r':>2s}"
          f" {'raw':>9s} {'log1p':>9s} {'gain':>9s}")
    level = []
    for tag in NETS:
        for target in TARGETS:
            sub = d[(d.network == tag) & (d.target == target)]
            sk = sub.target_skew.iloc[0]
            for r in sorted(sub.radius.unique()):
                a = sub[(sub.radius == r) & (sub.objective == "raw")]
                b = sub[(sub.radius == r) & (sub.objective == "log1p")]
                # Paired within seed, as every other gain in this project is.
                piv = (pd.merge(a[["seed", "kendall_tau"]],
                                b[["seed", "kendall_tau"]],
                                on="seed", suffixes=("_raw", "_log")))
                g = (piv.kendall_tau_log - piv.kendall_tau_raw)
                level.append({"network": tag, "target": target, "skew": sk,
                              "radius": r, "gain": g.mean(), "sd": g.std(ddof=1)})
                star = "*" if abs(g.mean()) > 2 * g.std(ddof=1) else " "
                print(f"  {tag:<20s} {target:<13s} {sk:>8.2f} {r:>2d}"
                      f" {piv.kendall_tau_raw.mean():>9.4f}"
                      f" {piv.kendall_tau_log.mean():>9.4f}"
                      f" {g.mean():>+9.4f}{star}")
    L = pd.DataFrame(level)

    print("\n  Mean gain from correcting the objective, by target:")
    for target in TARGETS:
        s = L[L.target == target]
        print(f"    {target:<14s} {s.gain.mean():>+8.4f}   "
              f"(max {s.gain.max():+.4f}, min {s.gain.min():+.4f}, "
              # s["skew"] not s.skew - the latter resolves to DataFrame.skew, the
              # method, and silently shadows the column.
              f"mean skew {s['skew'].mean():.2f})")

    # --- 2. THE QUESTION: does the horizon move? -------------------------------
    print("\n" + "=" * 78)
    print("2. HORIZON - modal r*(eps) under each objective")
    print("=" * 78)
    moved, total = [], 0
    print(f"\n  {'network':<20s} {'target':<13s} {'eps':>5s}"
          f" {'raw':>5s} {'log1p':>7s}  {'verdict'}")
    for tag in NETS:
        for target in TARGETS:
            for eps in EPS:
                cells = {}
                for obj in ("raw", "log1p"):
                    sub = d[(d.network == tag) & (d.target == target)
                            & (d.objective == obj)]
                    vals = r_star_per_seed(matrix(sub), eps)
                    cells[obj] = (int(pd.Series(vals).value_counts().idxmax()),
                                  len(vals))
                total += 1
                a, b = cells["raw"][0], cells["log1p"][0]
                same = a == b
                if not same:
                    moved.append((tag, target, eps, a, b))
                print(f"  {tag:<20s} {target:<13s} {eps:>5.2f}"
                      f" {a:>5d} {b:>7d}  {'' if same else '<-- MOVED'}")

    print(f"\n  {len(moved)} of {total} (network x target x eps) horizon cells "
          f"moved under the corrected objective")
    if moved:
        print("\n  Movements, split by target - this is the split that matters:")
        for target in TARGETS:
            m = [x for x in moved if x[1] == target]
            n = total // (len(NETS) * len(TARGETS)) * len(NETS)
            print(f"    {target:<14s} {len(m):>2d} / {n} moved")
            for tag, _, eps, a, b in m:
                print(f"        {tag:<20s} eps={eps:<5.2f} r*: {a} -> {b}")

    # --- 3. was the horizon ever stable? ---------------------------------------
    print("\n" + "=" * 78)
    print("3. STABILITY - how often the modal r* wins across the 10 seeds")
    print("   (a horizon that does not move but was never stable has not been")
    print("    shown robust - only shown noisy twice)")
    print("=" * 78)
    print(f"\n  {'network':<20s} {'target':<13s} {'eps':>5s}"
          f" {'raw support':>12s} {'log1p support':>14s}")
    for tag in NETS:
        for target in TARGETS:
            for eps in (0.05, 0.01):     # the two tightest, where r* is least stable
                out = []
                for obj in ("raw", "log1p"):
                    sub = d[(d.network == tag) & (d.target == target)
                            & (d.objective == obj)]
                    vals = pd.Series(r_star_per_seed(matrix(sub), eps))
                    out.append(f"{vals.value_counts().max()}/{len(vals)}")
                print(f"  {tag:<20s} {target:<13s} {eps:>5.2f}"
                      f" {out[0]:>12s} {out[1]:>14s}")


if __name__ == "__main__":
    main()

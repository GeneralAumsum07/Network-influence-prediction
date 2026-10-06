"""
verify_robustness_rerun.py - two checks on the 2026-09-12 Angle 4 re-run.

Written 2026-09-12 by Claude Opus 5 (plan §0 "queue Angle 4"; Task 6 findings
P2-11 / P3-08). Run by results/phase6_root_integration_stage4_20260912.ps1 after
both arms of analyse_robustness.py finish; can be re-run by hand at any time.

CHECK 1 - the raw arm reproduces the 2026-08-27 file.
    results/HISTORICAL_LANES_NOTE_20260912.md claimed the raw re-run "would
    reproduce identical numbers" because the lane is retag-independent (fits at
    max_hop 3) and every seed is pinned. That was an inference, not a
    measurement. This check measures it: every (network, target, rho,
    damage_seed, method) row of the new results/robustness.csv is aligned with
    the archived results/c8_historical_pre_20260912/robustness.csv and the
    largest absolute difference per metric is reported. The pass bar is the
    documented n_jobs=-1 tolerance for this forest (~5e-08 in tau; see
    influence/estimators.py make_rf), rounded up to 1e-06. A miss means
    something in the feature or preprocessing path changed since 2026-08-27 and
    the historical Angle 4 numbers in the study must be re-quoted, not merely
    relabelled.

CHECK 2 - the reported arm differs from the raw arm only where it should.
    The log1p arm was run with --targets betweenness. Its recompute and degree
    rows do not depend on the objective at all, so they must equal the raw
    arm's rows exactly; the local and local_trained_damaged rows are the
    addendum and are tabulated per (network, rho) as log1p minus raw, over all
    nodes and over the nonzero subset. Nothing is asserted about their sign -
    the prediction is recorded in the plan, not here.

Exit status is non-zero if check 1 misses its bar or check 2's invariant rows
disagree, so the controller's log carries a FAILED line rather than a quiet
mismatch.
"""
import sys

import numpy as np
import pandas as pd

KEYS = ["network", "target", "rho", "damage_seed", "method"]
METRICS = ["tau", "tau_nonzero", "p_at_5pct"]
NEW_RAW = "results/robustness.csv"
OLD_RAW = "results/c8_historical_pre_20260912/robustness.csv"
NEW_LOG = "results/robustness_log1p.csv"
TOL = 1e-6


def aligned(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    """Inner-join two runs on the row keys; a row present in only one side is
    reported as such rather than silently dropped."""
    m = a.merge(b, on=KEYS, how="outer", suffixes=("_a", "_b"), indicator=True)
    odd = m[m._merge != "both"]
    if len(odd):
        print(f"  WARNING {len(odd)} rows present on one side only:")
        print("   " + odd[KEYS + ["_merge"]].to_string().replace("\n", "\n   "))
    return m[m._merge == "both"]


def main() -> int:
    ok = True
    new_raw = pd.read_csv(NEW_RAW)
    old_raw = pd.read_csv(OLD_RAW)

    print("=" * 78)
    print("CHECK 1  raw arm re-run (2026-09-12) vs archived 2026-08-27 file")
    print(f"  {NEW_RAW}: {len(new_raw)} rows   {OLD_RAW}: {len(old_raw)} rows")
    print("=" * 78)
    m = aligned(new_raw, old_raw)
    for met in METRICS:
        d = (m[f"{met}_a"] - m[f"{met}_b"]).abs()
        worst = d.max()
        flag = "ok" if worst <= TOL else "MISS"
        print(f"  {met:<12} max |delta| = {worst:.3e}   ({flag}, bar {TOL:.0e})")
        if worst > TOL:
            ok = False
            w = m.loc[d.idxmax(), KEYS + [f"{met}_a", f"{met}_b"]]
            print("   worst row: " + ", ".join(f"{k}={v}" for k, v in w.items()))
    print(f"  verdict: {'raw arm reproduces the archive' if ok else 'raw arm DIFFERS from the archive'}")

    print()
    print("=" * 78)
    print("CHECK 2  reported (log1p) arm vs raw arm, betweenness")
    print("=" * 78)
    new_log = pd.read_csv(NEW_LOG)
    raw_b = new_raw[new_raw.target == "betweenness"]
    log_b = new_log[new_log.target == "betweenness"]
    m2 = aligned(log_b, raw_b)

    # Objective-independent rows must be byte-equal (same damage draw, same
    # exact betweenness on it, same degree).
    inv = m2[m2.method.isin(["recompute", "degree"])]
    for met in METRICS:
        worst = (inv[f"{met}_a"] - inv[f"{met}_b"]).abs().max()
        flag = "ok" if worst == 0 or np.isnan(worst) else "MISS"
        print(f"  invariant rows (recompute, degree) {met:<12} max |delta| = "
              f"{worst:.3e}  ({flag})")
        if not (worst == 0 or np.isnan(worst)):
            ok = False

    # The addendum: what the objective is worth under damage.
    dep = m2[m2.method.isin(["local", "local_trained_damaged"])].copy()
    for met in ("tau", "tau_nonzero", "p_at_5pct"):
        dep[f"d_{met}"] = dep[f"{met}_a"] - dep[f"{met}_b"]
    print("\n  log1p minus raw, mean over damage draws (positive = log1p arm "
          "ranks the CLEAN truth better on the damaged graph)")
    for method in ("local", "local_trained_damaged"):
        sub = dep[dep.method == method]
        if sub.empty:
            continue
        print(f"\n  method = {method}")
        for met in ("tau", "tau_nonzero", "p_at_5pct"):
            piv = sub.pivot_table(index="rho", columns="network",
                                  values=f"d_{met}", aggfunc="mean")
            print(f"\n    delta {met}")
            print("     " + piv.round(4).to_string().replace("\n", "\n     "))

    print()
    print("ALL CHECKS PASSED" if ok else "CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

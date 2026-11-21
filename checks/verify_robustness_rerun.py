"""
checks/verify_robustness_rerun.py - two checks on the 2026-09-12 Angle 4 re-run.

Written (plan §0 "queue Angle 4"; Task 6 findings
P2-11 / P3-08). Run by results/phase6_root_integration_stage4_20260912.ps1 after
both arms of analysis/analyse_robustness.py finish; can be re-run by hand at any time.

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

    Outcome (2026-10-12) and the pinned form (2026-11-21). The check missed:
    the model rows (local, local_trained_damaged) differ by up to 0.012 in
    tau, while the recompute and degree rows are identical. The cause was
    traced to the ORDER of the feature columns fed to the seeded forest,
    which two registry retags changed; the content is the same, and with the
    archived order one cell reproduces the archive exactly. The study was
    re-quoted from the new file. See the "Outcome" section of
    results/HISTORICAL_LANES_NOTE_20260912.md.
    Both inputs are fixed files, so after that the check could only ever give
    the same miss: it tested no current code, and because the script already
    exited 1 it also took away check 2's power to fail the gate. It now pins
    the explained state instead of re-reporting it:
      - both CSVs must have the sha256 they had when the drift was traced;
      - recompute and degree rows must still agree within the bar above;
      - each model method's largest difference must equal the value
        recorded at the trace (to float round-off), and is printed as a
        known, explained divergence;
      - any other method, or a missing one, fails.
    So the gate fails if either file, the comparison, or the set of methods
    changes; a change is a reason to redo the trace, not to re-pin.

CHECK 2 - the reported arm differs from the raw arm only where it should.
    The log1p arm was run with --targets betweenness. Its recompute and degree
    rows do not depend on the objective at all, so they must equal the raw
    arm's rows exactly; the local and local_trained_damaged rows are the
    addendum and are tabulated per (network, rho) as log1p minus raw, over all
    nodes and over the nonzero subset. Nothing is asserted about their sign -
    the prediction is recorded in the plan, not here.

Exit status is non-zero if check 1 departs from its pinned state or check 2's
invariant rows disagree, so the controller's log carries a FAILED line rather than a quiet
mismatch. It is also non-zero if either comparison is unsound: a row key
repeated, a row on one side only, nothing aligned, or (check 2) no invariant
rows at all - a check that compared nothing has not passed.
"""
import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import hashlib
import sys

import numpy as np
import pandas as pd

KEYS = ["network", "target", "rho", "damage_seed", "method"]
METRICS = ["tau", "tau_nonzero", "p_at_5pct"]
NEW_RAW = "results/robustness.csv"
OLD_RAW = "results/c8_historical_pre_20260912/robustness.csv"
NEW_LOG = "results/robustness_log1p.csv"
TOL = 1e-6

# CHECK 1's pinned state, recorded 2026-11-21 from the files the 2026-10-12
# trace examined. Raw-byte hashes are clone-independent because the repo
# stores every file byte-for-byte (.gitattributes: * -text).
PINNED_SHA256 = {
    NEW_RAW: "e7c3b7b6853af7becac1d0ffe68f7ddc826c5b09093ddb7d758941518f3b8ee7",
    OLD_RAW: "7852fad17d0494729ff947b876096a8c141ae9ead97eb193ea823bf157272831",
}
# Objective-free rows: same damage draw, same exact recompute or degree.
# These reproduced exactly, so they keep the reproduction bar.
REPRODUCING_METHODS = ("recompute", "degree")
# Model rows: largest |new - archive| per metric at the trace. The drift is
# explained (column order), not tolerated as noise, so the pin is the exact
# measured value; PIN_ROUNDOFF only absorbs float parsing, not drift.
KNOWN_DRIFT = {
    "local": {"tau": 0.012013632944690308,
              "tau_nonzero": 0.010962933537257899,
              "p_at_5pct": 0.04081632653061218},
    "local_trained_damaged": {"tau": 0.009221891194019838,
                              "tau_nonzero": 0.006574167921002183,
                              "p_at_5pct": 0.02487562189054729},
}
PIN_ROUNDOFF = 1e-12


def sha256_of(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# D-16 (2026-11-16). Both checks used to pass vacuously in three ways:
# a row on one side only was printed as a WARNING and dropped; an empty
# overlap gave max() = NaN, and `NaN > TOL` is False, so CHECK 1 read "ok";
# CHECK 2 treated NaN explicitly as ok. A comparison that compared nothing,
# or compared fewer rows than both files hold, now FAILS. A NaN on both sides
# of a row counts as equal (the metric is undefined for that row in both
# runs); a NaN on one side only is a difference and is scored as infinite.
# On the 2026-09-12 files none of this fires: 640/640 raw rows and 320/320
# betweenness rows align, with no NaNs and no duplicate keys.


def aligned(a: pd.DataFrame, b: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Join two runs on the row keys. Returns (rows present on both sides,
    sound), where sound is False if either side repeats a key (the join would
    multiply rows), any row is present on one side only, or nothing aligns."""
    sound = True
    for side, df in (("a", a), ("b", b)):
        dup = int(df.duplicated(KEYS).sum())
        if dup:
            print(f"  FAIL side {side} repeats {dup} row keys")
            sound = False
    m = a.merge(b, on=KEYS, how="outer", suffixes=("_a", "_b"), indicator=True)
    odd = m[m._merge != "both"]
    if len(odd):
        print(f"  FAIL {len(odd)} rows present on one side only:")
        print("   " + odd[KEYS + ["_merge"]].to_string().replace("\n", "\n   "))
        sound = False
    both = m[m._merge == "both"]
    if both.empty:
        print("  FAIL no rows align; there is nothing to compare")
        sound = False
    print(f"  {len(both)} rows aligned")
    return both, sound


def abs_delta(x: pd.Series, y: pd.Series) -> pd.Series:
    """|x - y| per row, with NaN on both sides = 0 and NaN on one side = inf,
    so that max() is never NaN and a one-sided NaN cannot read as a pass."""
    nx, ny = x.isna(), y.isna()
    d = (x - y).abs()
    d[nx & ny] = 0.0
    d[nx ^ ny] = np.inf
    return d


def main() -> int:
    ok = True
    new_raw = pd.read_csv(NEW_RAW)
    old_raw = pd.read_csv(OLD_RAW)

    print("=" * 78)
    print("CHECK 1  raw arm re-run (2026-09-12) vs archived 2026-08-27 file (pinned)")
    print(f"  {NEW_RAW}: {len(new_raw)} rows   {OLD_RAW}: {len(old_raw)} rows")
    print("=" * 78)
    ok1 = True
    # A changed file means the traced explanation no longer covers it. The
    # content checks below still run, so the log shows what moved.
    for path, want in PINNED_SHA256.items():
        got = sha256_of(path)
        if got != want:
            print(f"  FAIL {path} sha256 {got[:16]}... is not the pinned {want[:16]}...;"
                  " redo the trace before re-pinning")
            ok1 = False
    m, sound = aligned(new_raw, old_raw)
    ok1 = ok1 and sound

    present = set(m.method) if not m.empty else set()
    expected = set(REPRODUCING_METHODS) | set(KNOWN_DRIFT)
    if present != expected:
        print(f"  FAIL methods {sorted(present)} are not the pinned {sorted(expected)}")
        ok1 = False
    for method in sorted(present & expected):
        rows = m[m.method == method]
        for met in METRICS:
            d = abs_delta(rows[f"{met}_a"], rows[f"{met}_b"])
            worst = d.max()
            if method in REPRODUCING_METHODS:
                good = worst <= TOL
                note = f"bar {TOL:.0e}"
            else:
                pin = KNOWN_DRIFT[method][met]
                good = abs(worst - pin) <= PIN_ROUNDOFF
                note = f"pinned {pin:.3e}, known drift"
            print(f"  {method:<22} {met:<12} max |delta| = {worst:.3e}   "
                  f"({'ok' if good else 'MISS'}, {note})")
            if not good:
                ok1 = False
                w = rows.loc[d.idxmax(), KEYS + [f"{met}_a", f"{met}_b"]]
                print("   worst row: " + ", ".join(f"{k}={v}" for k, v in w.items()))
    print("  verdict: " + (
        "recompute and degree reproduce the archive; model rows differ by the "
        "known column-order drift (results/HISTORICAL_LANES_NOTE_20260912.md, Outcome)"
        if ok1 else "CHECK 1 has departed from its pinned state"))
    ok = ok and ok1

    print()
    print("=" * 78)
    print("CHECK 2  reported (log1p) arm vs raw arm, betweenness")
    print("=" * 78)
    new_log = pd.read_csv(NEW_LOG)
    raw_b = new_raw[new_raw.target == "betweenness"]
    log_b = new_log[new_log.target == "betweenness"]
    m2, sound = aligned(log_b, raw_b)
    ok = ok and sound

    # Objective-independent rows must be byte-equal (same damage draw, same
    # exact betweenness on it, same degree). An empty invariant set used to
    # read as ok (max of nothing is NaN); it now fails, because then the
    # invariant was never tested.
    inv = m2[m2.method.isin(["recompute", "degree"])]
    if inv.empty:
        print("  FAIL no recompute or degree rows; the invariant was not tested")
        ok = False
    for met in METRICS:
        if inv.empty:
            break
        worst = abs_delta(inv[f"{met}_a"], inv[f"{met}_b"]).max()
        flag = "ok" if worst == 0 else "MISS"
        print(f"  invariant rows (recompute, degree) {met:<12} max |delta| = "
              f"{worst:.3e}  ({flag}, {len(inv)} rows)")
        if worst != 0:
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

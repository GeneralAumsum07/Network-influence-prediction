"""Gate: may probe_objective_horizon.py resume on a partial results/objective_horizon_probe.csv?

Why this exists. Until 2026-10-07 the objective-horizon probe wrote its CSV once, at
the end of all 800 fits. It was lost twice that day (08:53, a closed console window;
09:32, stopped because the laptop was on battery) and so it was made resumable: it
now checkpoints after every (target, radius) block and skips keys already on disk.
That creates a file that can exist mid-run, and the stage 2 step that used to sit in
front of the probe (Remove-PreRefit) refuses any file that is not the archived
pre-refit copy, so a relaunch after an interruption would stop the queue. This
script takes its place, exactly as check_b1_resume.py does for B1.

Accepted only if ALL hold; any failure exits 1 and the controller stops:
  1. Same columns, same order, as the archived pre-refit file (same producer,
     same schema; a column change would mean a different probe wrote it).
  2. No duplicate resume keys (network, target, radius, objective, seed). A
     duplicate would mean two writers, and the analyser would double-count.
  3. Every key lies inside the 800-cell grid, taken from the archived pre-refit
     file (a full run of the same grid).
  4. Every (network, target, radius) block present is whole (2 objectives x 10
     seeds). The probe writes only at block boundaries, so a partial block means
     the file was written some other way.
  5. No NaN kendall_tau. The probe writes atomically, so a truncated row should be
     impossible; a NaN would otherwise count as "done" and never be refitted.
  6. tau identical to the pre-refit row: REPORTED, not failed. The pre-refit file
     was removed on 2026-09-13 20:26, before any of these runs, so an identical
     row is either carried-over data or a cell the retag did not touch.
Not checked here, and why: whether the INPUTS changed since the rows were written.
run.py hash-pins the caches and sweep CSVs, and refuses to start if any differ
from sources.json.

Read-only. Exit 0 = resume (or a fresh start) is safe; exit 1 = stop.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PARTIAL = ROOT / "results/objective_horizon_probe.csv"
ARCHIVED = ROOT / "results/phase6_c5_pre_orbit5_refit_20260906/objective_horizon_probe.csv"
KEY = ["network", "target", "radius", "objective", "seed"]
BLOCK = ["network", "target", "radius"]


def main() -> int:
    if not PARTIAL.exists():
        # Nothing to resume: the probe starts fresh. Safe by construction.
        print("no partial file - objective-horizon probe starts from cell 1")
        return 0
    cur = pd.read_csv(PARTIAL, float_precision="round_trip")
    old = pd.read_csv(ARCHIVED, float_precision="round_trip")
    failures = []

    # 1. schema
    if list(cur.columns) != list(old.columns):
        failures.append(f"columns differ: {list(cur.columns)} vs archived {list(old.columns)}")
        # The remaining checks index by column name; stop before they raise.
        for f in failures:
            print("FAIL:", f)
        return 1

    # 2. key uniqueness
    dup = int(cur.duplicated(KEY).sum())
    if dup:
        failures.append(f"{dup} duplicate resume keys")

    # 3. keys inside the grid
    grid = set(map(tuple, old[KEY].itertuples(index=False)))
    outside = [k for k in map(tuple, cur[KEY].itertuples(index=False)) if k not in grid]
    if outside:
        failures.append(f"{len(outside)} keys outside the {len(grid)}-cell grid, e.g. {outside[:3]}")

    # 4. whole blocks only: a block's size in the archive is its full size
    full = old.groupby(BLOCK).size()
    have = cur.groupby(BLOCK).size()
    partial_blocks = [b for b, n in have.items() if n != full.get(b, -1)]
    if partial_blocks:
        failures.append(f"{len(partial_blocks)} incomplete blocks, e.g. {partial_blocks[:3]}")

    # 5. no NaN scores
    nan = int(cur.kendall_tau.isna().sum())
    if nan:
        failures.append(f"{nan} rows with NaN kendall_tau")

    # 6. carry-over report (informational)
    m = cur.merge(old[KEY + ["kendall_tau"]], on=KEY, suffixes=("", "_pre"))
    same = int((m.kendall_tau == m.kendall_tau_pre).sum())

    print(f"partial rows: {len(cur)} of {len(old)}  |  blocks whole: {len(have)} of {len(full)}")
    print("per network:", cur.groupby("network").size().to_dict())
    print(f"tau identical to pre-refit (informational): {same} of {len(m)}")
    if failures:
        for f in failures:
            print("FAIL:", f)
        return 1
    print("PASS - probe_objective_horizon.py may resume on this file")
    return 0


if __name__ == "__main__":
    sys.exit(main())

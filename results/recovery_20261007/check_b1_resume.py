"""Gate: may probe_sample_efficiency.py resume on the partial results/sample_efficiency.csv?

Why this exists. The 2026-09-14 recovery run was killed (no shutdown or power-loss
event; inferred: its launching session closed) partway through the B1 sweep, leaving
1,540 of 5,600 cells on disk. The probe resumes on its own CSV by key alone
(network, target, radius, fraction, seed) and checks nothing about what produced the
existing rows. The old stage 2 step in front of it (Remove-PreRefit) would refuse to
delete this file, because it is not the archived pre-refit copy, and would stop the
queue. This script takes its place for B1 and states exactly what is accepted.

Accepted only if ALL hold; any failure exits 1 and the controller stops:
  1. Same columns, same order, as the archived pre-refit file. Same producer, same
     schema; a column change would mean a different probe wrote it.
  2. No duplicate resume keys. A duplicate would mean two writers, or a resume that
     re-ran cells, and the analyser would double-count them.
  3. Every key lies inside the 5,600-cell grid, taken from the archived pre-refit
     file (a full run of the same grid). Rules out a different grid or typo'd keys.
  4. Every (network, target, radius) block present is whole (all fraction x seed
     cells). The probe writes only at block boundaries, so a partial block means
     the file was written some other way.
  5. No existing row is identical to its pre-refit counterpart on kendall_tau. The
     pre-refit file was removed on 2026-09-13 20:26, before this run, so a
     tau-identical row is either carried-over data or a cell the retag did not
     touch. Reported, not failed: some cells may legitimately be unchanged.
Not checked here, and why: whether the INPUTS changed since the rows were written.
run.py hash-pins the caches and sweep CSVs at launch and before every stage, and
2026-10-07 inspection found none modified after the sweep began (2026-09-14 17:29).

Read-only. Exit 0 = resume is safe; exit 1 = stop.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PARTIAL = ROOT / "results/sample_efficiency.csv"
ARCHIVED = ROOT / "results/phase6_c5_pre_orbit5_refit_20260906/sample_efficiency.csv"
KEY = ["network", "target", "radius", "fraction", "seed"]
BLOCK = ["network", "target", "radius"]


def main() -> int:
    if not PARTIAL.exists():
        # Nothing to resume: the probe starts fresh. That is safe by construction.
        print("no partial file - B1 starts from cell 1")
        return 0
    cur = pd.read_csv(PARTIAL)
    old = pd.read_csv(ARCHIVED)
    failures = []

    # 1. schema
    if list(cur.columns) != list(old.columns):
        failures.append(f"columns differ: {list(cur.columns)} vs archived {list(old.columns)}")

    # 2. key uniqueness
    dup = int(cur.duplicated(KEY).sum())
    if dup:
        failures.append(f"{dup} duplicate resume keys")

    # 3. keys inside the grid
    grid = set(map(tuple, old[KEY].itertuples(index=False)))
    outside = [k for k in map(tuple, cur[KEY].itertuples(index=False)) if k not in grid]
    if outside:
        failures.append(f"{len(outside)} keys outside the 5,600-cell grid, e.g. {outside[:3]}")

    # 4. whole blocks only: a block's size in the archive is its full size
    full = old.groupby(BLOCK).size()
    have = cur.groupby(BLOCK).size()
    partial_blocks = [b for b, n in have.items() if n != full.get(b, -1)]
    if partial_blocks:
        failures.append(f"{len(partial_blocks)} incomplete blocks, e.g. {partial_blocks[:3]}")

    # 5. carry-over report (informational)
    m = cur.merge(old[KEY + ["kendall_tau"]], on=KEY, suffixes=("", "_pre"))
    same = int((m.kendall_tau == m.kendall_tau_pre).sum())

    print(f"partial rows: {len(cur)} of {len(old)}  |  blocks whole: {len(have)} of {len(full)}")
    print("per network:", cur.groupby("network").size().to_dict())
    print(f"tau identical to pre-refit (informational): {same} of {len(m)}")
    if failures:
        for f in failures:
            print("FAIL:", f)
        return 1
    print("PASS - probe_sample_efficiency.py may resume on this file")
    return 0


if __name__ == "__main__":
    sys.exit(main())

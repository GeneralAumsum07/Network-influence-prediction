"""Gate: may Stage 2 enter the A7 block after an interruption?

Why this exists. stage2.ps1 guards the A7 block with five Remove-PreRefit calls.
Each deletes its file only if it is byte-identical to the archived pre-refit copy,
and THROWS otherwise. That was right on 2026-10-07, when all five were absent. Once
the A7 frozen arm has run, its output is new and differs from the archive, so any
relaunch stops at the first call - before probe_target_noise_refit.py, which
resumes by key, is reached. The 2026-10-07 09:00 LOG line "the A7 refit arm
resumes by key" is true of the script and false of the queue. This gate replaces
the five calls, as check_b1_resume.py replaced the B1 one. It is not wired in
yet: stage2.ps1 is hash-pinned while the queue runs, so the swap happens at the
next relaunch (2026-10-10 audit-fix plan, Task 2).

What each file needs:
  results_target_noise.csv                  frozen arm, rewritten whole at its end
  results_target_noise_scored.csv           score_a7_arm2.py, rewritten whole
  results/results_paired_target_noise.csv   analyse_paired_target_noise.py, rewritten whole
  results/RESULTS_paired_target_noise.txt   same
      -> a fresh copy may stay: its producer runs again and overwrites it. A copy
         byte-identical to the archived PRE-refit file is refused - pre-retag data
         reappearing is the one thing the old guard existed to catch.
  results_target_noise_refit.csv            refit arm, appended per (cell, rep), resumed
      -> validated row by row, because every row it holds is reused unrefitted.

Refit file accepted only if ALL hold:
  0. not byte-identical to the archived pre-refit file;
  1. ends in a newline (a reset mid-append leaves a torn last row);
  2. same columns, same order, as the archive;
  3. no NaN anywhere;
  4. no duplicate (network, target, radius, rep);
  5. every key inside the archived grid, tier among the archive's tiers;
  6. reps are 0..k and every rep below k is complete - the arm loops replicate
     OUTERMOST, so any other shape means a second writer or a different loop;
  7. n_features constant within each (network, target, radius).
Reported, not failed: rows whose tau_refit equals the pre-refit value.
Not checked: whether inputs changed since rows were written - run.py hash-pins
caches and scripts at launch and before every stage.

Read-only. Exit 0 = the A7 block may run; exit 1 = stop.
"""
import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent.parent
ARCHIVE_DIR = "results/phase6_c5_pre_orbit5_refit_20260906"
REFIT = "results_target_noise_refit.csv"
OVERWRITTEN = ["results_target_noise.csv", "results_target_noise_scored.csv",
               "results/results_paired_target_noise.csv",
               "results/RESULTS_paired_target_noise.txt"]
KEY = ["network", "target", "radius", "rep"]
CELL = ["network", "target", "radius"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archived(root: Path, rel: str) -> Path:
    # The archive is flat: Remove-PreRefit looked copies up by leaf name.
    return root / ARCHIVE_DIR / Path(rel).name


def check_overwritten(root: Path) -> list[str]:
    failures = []
    for rel in OVERWRITTEN:
        path, copy = root / rel, archived(root, rel)
        if not path.exists():
            print(f"{rel}: absent")
        elif copy.exists() and sha(path) == sha(copy):
            failures.append(f"{rel} is byte-identical to its archived pre-refit copy "
                            f"({copy.relative_to(root).as_posix()}); move it out, then relaunch")
        else:
            print(f"{rel}: present and not the pre-refit copy - its producer overwrites it")
    return failures


def check_refit(root: Path) -> list[str]:
    path, copy = root / REFIT, archived(root, REFIT)
    if not path.exists():
        print(f"{REFIT}: absent - refit arm starts at replicate 0")
        return []
    if sha(path) == sha(copy):
        return [f"{REFIT} is byte-identical to the archived pre-refit copy; resuming "
                f"would reuse every pre-retag fit"]
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        tail = raw[raw.rfind(b"\n") + 1:][:80]
        return [f"{REFIT} ends in a torn row {tail!r}; delete that last partial line "
                f"by hand (nothing else), then relaunch"]
    try:
        cur = pd.read_csv(path, float_precision="round_trip")
    except Exception as exc:                       # noqa: BLE001 - report, never guess
        return [f"{REFIT} does not parse: {exc}"]
    old = pd.read_csv(copy, float_precision="round_trip")

    if list(cur.columns) != list(old.columns):
        # Every later check indexes these columns; stop here.
        return [f"columns differ: {list(cur.columns)} vs archived {list(old.columns)}"]

    failures = []
    nan_rows = int(cur.isna().any(axis=1).sum())
    if nan_rows:
        failures.append(f"{nan_rows} rows contain NaN")
    dup = int(cur.duplicated(KEY).sum())
    if dup:
        failures.append(f"{dup} duplicate resume keys")
    grid = set(old[KEY].itertuples(index=False, name=None))
    outside = [k for k in cur[KEY].itertuples(index=False, name=None) if k not in grid]
    if outside:
        failures.append(f"{len(outside)} keys outside the archived grid, e.g. {outside[:3]}")
    bad_tier = sorted(set(cur.tier) - set(old.tier))
    if bad_tier:
        failures.append(f"unexpected tier(s) {bad_tier}")

    n_cells = old.groupby(CELL).ngroups
    per_rep = cur.groupby("rep").size()
    reps = [int(r) for r in per_rep.index]
    if reps != list(range(len(reps))):
        failures.append(f"replicates are not 0..k: {reps[:5]}...{reps[-3:]}")
    holes = [r for r in reps[:-1] if per_rep[r] != n_cells]
    if holes:
        failures.append(f"replicates below the last are incomplete: {holes[:5]} "
                        f"(need {n_cells} cells each)")
    varying = cur.groupby(CELL).n_features.nunique()
    varying = varying[varying > 1]
    if len(varying):
        failures.append(f"n_features varies within {len(varying)} cells, e.g. {list(varying.index[:3])}")

    merged = cur.merge(old[KEY + ["tau_refit"]], on=KEY, suffixes=("", "_pre"))
    same = int((merged.tau_refit == merged.tau_refit_pre).sum())
    print(f"{REFIT}: {len(cur)} of {len(old)} rows; replicates 0..{reps[-1] if reps else '-'}; "
          f"last replicate {per_rep.iloc[-1] if reps else 0}/{n_cells} cells")
    print(f"tau identical to pre-refit (informational): {same} of {len(merged)}")
    return failures


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=REPO)
    root = ap.parse_args(argv).root
    failures = check_overwritten(root) + check_refit(root)
    for f in failures:
        print("FAIL:", f)
    if failures:
        return 1
    print("PASS - the A7 block may run; the refit arm resumes on what is there")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Fixture test for check_a7_resume.py. Builds throwaway fake repos in a temp dir.

Why a fixture and not the real files: on 2026-10-10 the real A7 outputs do not
exist yet (Stage 2 is in the objective-horizon probe), and when they do exist the
gate is guarding a 30+ h run - the wrong moment to discover it rejects a valid
file. Every scenario below is a state an interrupted Stage 2 can actually leave.

Exit 0 = every scenario gave the expected verdict.
"""
import contextlib
import importlib.util
import io
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gate", HERE / "check_a7_resume.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)          # -I safe: loaded by path, not by sys.path

COLS = ["network", "target", "radius", "tier", "rep", "tau_refit", "n_features"]
TIER = "node+edge+subgraph+dynamic"
CELLS = [(n, t, r) for n in ("netA", "netB") for t in ("spread_mean",) for r in (0, 1)]
REPS = 3                               # archive grid: 4 cells x 3 reps = 12 rows


def refit_rows(reps, tau_offset=0.0):
    """Rows in the arm's real order: replicate OUTER, cells inner."""
    return [dict(network=n, target=t, radius=r, tier=TIER, rep=k,
                 tau_refit=0.5 + 0.01 * k + 0.001 * r + tau_offset, n_features=3 + r)
            for k in reps for (n, t, r) in CELLS]


def make_repo(tmp: Path) -> Path:
    """A fake repo holding only the archive the gate compares against."""
    arch = tmp / gate.ARCHIVE_DIR
    arch.mkdir(parents=True)
    (tmp / "results").mkdir(exist_ok=True)
    # gate.archived() is the ONLY place the gate looks: a flat archive keyed by
    # leaf name. Until 2026-11-15 this wrote to arch / gate.REFIT, a nested
    # results/ path that does not exist, so the fixture crashed before its
    # first scenario and the gate was never exercised.
    pd.DataFrame(refit_rows(range(REPS)), columns=COLS).to_csv(
        gate.archived(tmp, gate.REFIT), index=False)
    for rel in gate.OVERWRITTEN:
        gate.archived(tmp, rel).write_text("archived pre-refit bytes\n")
    return tmp


def write_refit(root: Path, rows):
    pd.DataFrame(rows, columns=COLS).to_csv(root / gate.REFIT, index=False)


def scenario(name, expect, mutate, reason=None):
    """expect: exit code. reason: text that must appear on a FAIL line.

    The exit code alone cannot tell "rejected for the reason this scenario
    builds" from "rejected by some other check": a torn file that also tripped
    the duplicate check would pass on exit 1 while the torn-row check was dead.
    """
    tmp = Path(tempfile.mkdtemp(prefix=f"a7gate_{name}_"))
    try:
        root = make_repo(tmp)
        mutate(root)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = gate.main(["--root", str(root)])
        fails = [line for line in out.getvalue().splitlines() if line.startswith("FAIL:")]
        ok = got == expect and (reason is None or any(reason in f for f in fails))
        print(f"{'ok ' if ok else 'BAD'} {name}: exit {got}, expected {expect}"
              + (f"; wanted FAIL containing {reason!r}" if reason else "")
              + ("" if ok else f"; got {fails}"))
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Each mutation leaves one on-disk state a reset or a stray writer could produce.
def m_nothing(root): pass
def m_fresh_frozen(root): (root / gate.OVERWRITTEN[0]).write_text("fresh frozen arm\n")
def m_frozen_is_archive(root):
    shutil.copy(root / gate.ARCHIVE_DIR / Path(gate.OVERWRITTEN[0]).name, root / gate.OVERWRITTEN[0])
def m_partial(root): write_refit(root, refit_rows([0], 0.1) + refit_rows([1], 0.1)[:2])
def m_refit_is_archive(root):
    shutil.copy(gate.archived(root, gate.REFIT), root / gate.REFIT)
def m_torn(root):
    m_partial(root)
    with open(root / gate.REFIT, "ab") as f:
        f.write(b"netB,spread_mean,1,node+ed")             # no newline: torn append
def m_dup(root): write_refit(root, refit_rows([0], 0.1) + refit_rows([0], 0.1)[:1])
def m_rep_gap(root): write_refit(root, refit_rows([0, 2], 0.1))
def m_hole(root): write_refit(root, refit_rows([0], 0.1)[:3] + refit_rows([1], 0.1))
def m_nan(root):
    rows = refit_rows([0], 0.1); rows[1]["tau_refit"] = float("nan"); write_refit(root, rows)
def m_outside(root):
    rows = refit_rows([0], 0.1); rows[0]["network"] = "netZ"; write_refit(root, rows)
def m_nfeat(root):
    rows = refit_rows([0, 1], 0.1); rows[4]["n_features"] = 99; write_refit(root, rows)
def m_columns(root):
    pd.DataFrame(refit_rows([0], 0.1), columns=COLS[::-1]).to_csv(root / gate.REFIT, index=False)


# (name, expected exit, mutation, text the rejecting FAIL line must contain).
# The reason strings are fragments of check_a7_resume.py's own messages.
CASES = [("nothing_on_disk", 0, m_nothing, None), ("fresh_frozen", 0, m_fresh_frozen, None),
         ("frozen_is_archive", 1, m_frozen_is_archive, "byte-identical to its archived"),
         ("partial_refit", 0, m_partial, None),
         ("refit_is_archive", 1, m_refit_is_archive, "byte-identical to the archived"),
         ("torn", 1, m_torn, "torn row"),
         ("duplicate_key", 1, m_dup, "duplicate resume keys"),
         ("rep_gap", 1, m_rep_gap, "replicates are not 0..k"),
         ("hole_below_last_rep", 1, m_hole, "replicates below the last are incomplete"),
         ("nan", 1, m_nan, "contain NaN"),
         ("key_outside_grid", 1, m_outside, "keys outside the archived grid"),
         ("n_features_varies", 1, m_nfeat, "n_features varies"),
         ("column_order", 1, m_columns, "columns differ")]

if __name__ == "__main__":
    results = [scenario(*case) for case in CASES]
    print(f"{sum(results)}/{len(results)} scenarios as expected")
    sys.exit(0 if all(results) else 1)

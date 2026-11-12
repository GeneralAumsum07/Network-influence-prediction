"""Fixture test for check_a7_resume.py. Builds throwaway fake repos in a temp dir.

Why a fixture and not the real files: on 2026-10-10 the real A7 outputs do not
exist yet (Stage 2 is in the objective-horizon probe), and when they do exist the
gate is guarding a 30+ h run - the wrong moment to discover it rejects a valid
file. Every scenario below is a state an interrupted Stage 2 can actually leave.

Exit 0 = every scenario gave the expected verdict.
"""
import importlib.util
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
    pd.DataFrame(refit_rows(range(REPS)), columns=COLS).to_csv(arch / gate.REFIT, index=False)
    for rel in gate.OVERWRITTEN:
        (arch / Path(rel).name).write_text("archived pre-refit bytes\n")
    return tmp


def write_refit(root: Path, rows):
    pd.DataFrame(rows, columns=COLS).to_csv(root / gate.REFIT, index=False)


def scenario(name, expect, mutate):
    tmp = Path(tempfile.mkdtemp(prefix=f"a7gate_{name}_"))
    try:
        root = make_repo(tmp)
        mutate(root)
        got = gate.main(["--root", str(root)])
        ok = got == expect
        print(f"{'ok ' if ok else 'BAD'} {name}: exit {got}, expected {expect}")
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
    shutil.copy(root / gate.ARCHIVE_DIR / gate.REFIT, root / gate.REFIT)
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


CASES = [("nothing_on_disk", 0, m_nothing), ("fresh_frozen", 0, m_fresh_frozen),
         ("frozen_is_archive", 1, m_frozen_is_archive), ("partial_refit", 0, m_partial),
         ("refit_is_archive", 1, m_refit_is_archive), ("torn", 1, m_torn),
         ("duplicate_key", 1, m_dup), ("rep_gap", 1, m_rep_gap),
         ("hole_below_last_rep", 1, m_hole), ("nan", 1, m_nan),
         ("key_outside_grid", 1, m_outside), ("n_features_varies", 1, m_nfeat),
         ("column_order", 1, m_columns)]

if __name__ == "__main__":
    results = [scenario(n, e, m) for n, e, m in CASES]
    print(f"{sum(results)}/{len(results)} scenarios as expected")
    sys.exit(0 if all(results) else 1)

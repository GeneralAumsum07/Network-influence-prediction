"""
Phase 6.5 L1 controller: the beta/beta_c sweep, one (network, multiple) unit at
a time, resumable after a kill or a host reset.

Specification: docs/prereg/prereg_phase6_5_lanes.md, lane L1, the 2026-09-14
12:16 scope clarification and the 2026-10-12 12:15 execution definitions.
This file runs the registered grid. It decides nothing the prereg leaves open.

    python probe_beta_sweep.py [--only TAG@M ...] [--dry-run]

    python probe_beta_sweep.py --dry-run                    # preconditions only
    python probe_beta_sweep.py --only email-Eu-core@1.25    # the pilot
    python probe_beta_sweep.py                              # the full sweep

WHAT ONE UNIT IS
----------------
A unit is one (network, multiple). Its directory is analyse_beta_sweep.mult_dir(m),
for example results/phase6_5_beta/m1.25/. That directory is shared by the five
networks at that multiple; every file in it is tagged with the network name.
The name is imported from the analyser rather than re-derived, so the
controller and the scorer cannot disagree about where a multiple lives.

1. stage 1 (stage1_prepare.py <edge list> 4000 <m> uniform), run with the unit
   directory as its cwd. It writes the five cache files there, never at the
   repo root. Skipped when cache_meta_<tag>.json is already there and records
   this multiple: stage 1 writes the meta file last, so its presence means the
   other four were written first.
2. The per-multiple E3 check (prereg E3, "repeated against each m directory's
   4,000-draw cache once stage 1 has written it"). See check_multiple_identity.
   A failure stops the controller before any fit at that multiple.
3. stage 2 (stage2_sweep.py <tag> <targets> 3 10), same cwd. stage 2 resumes
   cell by cell itself and refuses if its stage-1 inputs changed underneath a
   partial sweep (influence/sweep_inputs.py).
4. Refit reconciliation (added 2026-10-13 after a host reset): see
   reconcile_refits. stage 2 refits a cell whose CSV row survived but whose
   prediction vector did not, and appends a second row for it.
5. A completeness check: the sweep CSV holds exactly the registered cells and
   the OOF store has a prediction for each. Only then is the unit logged COMPLETE.

The targets are every spread column, with spread_cv and spread_resid dropped
below m = 1.25 as registered: 480 cells at m = 0.8 and 1.0, 800 above, 16,800
in all. That total is the one the 2026-09-14 clarification computed; the
verifier checks the arithmetic.

WHY THE ORDER IS PRIMARY NETWORKS FIRST
---------------------------------------
email-Eu-core and p2p-Gnutella08 carry the registered H1 claim. Running their
ten units first means the primary claim can be scored at the earliest moment,
and a run cut short still leaves complete primary series. The order affects
nothing else: units are independent.

RESUME ON A HOST THAT RESETS ITSELF
-----------------------------------
The 2026-10-07 recovery controller was killed twice by host resets, and each
time a person had to inspect and rename its lock before it could resume. Here
that check is automatic. results/phase6_5_beta/active.lock holds the
controller's PID.
- If that PID is still a live python.exe, the controller refuses to start:
  two writers on one CSV is the one failure resume cannot repair.
- If it is not, the lock is a leftover from a kill. It is renamed to
  stale_lock_<pid>_<HHMMSS>.txt as evidence and the run continues.
Windows recycles PIDs. A recycled PID that lands on an unrelated python.exe
therefore refuses, which is the safe direction.

WHAT IS PINNED, AND WHY NOT MORE
--------------------------------
results/phase6_5_beta/sources.json records the SHA-256 of everything that
decides a fitted number:
- stage1_prepare.py and stage2_sweep.py;
- every repo module they import, transitively (found by parsing their imports,
  so a module added later is covered without editing a list);
- the five edge lists;
- the five recorded locator files.
Every later start, and the gap before every unit, compares against it. A
mismatch stops the run. The recorded hash is never rewritten to get past this
(CLAUDE.md protocol, point 7). The fix is a decision recorded in the LOG.

This file and the analyser are deliberately NOT pinned. They decide where
files go and which cells are expected, not what a fit returns, and pinning
them would block every scoring fix until the sweep ends. Their hashes are
logged at each start, so a change is still visible after the fact.

Deck-lane modules that the stages do not import (L7's branch_anisotropy.py
among them) fall outside the import closure. They stay editable while the
sweep runs, which the "L7 before L1" ordering needs.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import inspect
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import analyse_beta_sweep as ab
from influence.criticality import leading_eigenvalue, transmission_probability
from influence.dynamics import simulate_ic_percolation
from influence.preprocessing import load_edgelist

ROOT = Path(__file__).resolve().parent

# How closely stage 1's recomputed beta_c must match the root cache's. It is
# read from the eigensolve's own convergence tolerance rather than chosen by
# hand: ARPACK only promises the leading eigenvalue to `tol` relative, so two
# solves of the same matrix may differ by up to that much, and any tighter
# bound is a guess about solver noise. 1e-12 was such a guess (set from one
# 1.7e-14 observation) and stopped the sweep at ca-GrQc@1.25 on 2026-10-14
# with a 1.37e-12 difference and bit-identical draws. A wrong graph or method
# moves beta_c by far more than 1e-8; the exact draw bit-identity check in
# check_multiple_identity is the guard that matters. (Rachit, 2026-10-15.)
BETA_C_RTOL = inspect.signature(leading_eigenvalue).parameters["tol"].default
OUT = ROOT / ab.OUT
LOG = OUT / "controller.log"
LOCK = OUT / "active.lock"
MANIFEST = OUT / "sources.json"

# Registered grid (prereg L1 and the 2026-09-14 clarification). Changing any of
# these changes the registration.
SPREAD_TARGETS = ("spread_mean", "spread_std", "spread_cv", "spread_resid", "spread_ignition")
TIERS = ("node", "node+edge", "node+edge+subgraph", "node+edge+subgraph+dynamic")
MAX_HOP = 3                     # radii 0..3
N_SEEDS = 10
N_SIMS = 4000
CONVENTION = "uniform"
STAGE_SCRIPTS = ("stage1_prepare.py", "stage2_sweep.py")
ORDER = ab.PRIMARY_NETWORKS + tuple(t for t in ab.NETWORKS if t not in ab.PRIMARY_NETWORKS)


def log(message: str) -> None:
    """One timestamped line to stdout and to the controller log."""
    line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}"
    print(line, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# The grid
# ---------------------------------------------------------------------------

def stage_targets(m: float) -> list[str]:
    """Spread targets fitted at multiple m.

    The exclusion is registered: spread_cv and spread_resid are ill-defined
    when the mean spread is close to 1, which happens below m = 1.25. The
    threshold is the analyser's constant, so the scorer and the controller
    cannot drift apart.
    """
    return [t for t in SPREAD_TARGETS
            if not (t in ("spread_cv", "spread_resid") and m < ab.CV_RESID_MIN_M)]


def expected_keys(m: float) -> set[tuple[str, int, str, int]]:
    """Every (target, radius, tier, seed) cell a complete unit must contain."""
    return {(t, r, tier, s) for t in stage_targets(m) for r in range(MAX_HOP + 1)
            for tier in TIERS for s in range(N_SEEDS)}


def all_units() -> list[tuple[str, float]]:
    return [(tag, m) for tag in ORDER for m in ab.SWEEP_MULTIPLES]


def parse_only(specs: list[str] | None) -> list[tuple[str, float]]:
    """--only TAG@M, checked against the registered grid. An off-grid
    multiple or an unknown network is an error, not a new unit."""
    if not specs:
        return all_units()
    units = []
    for spec in specs:
        tag, _, m = spec.partition("@")
        try:
            m = float(m)
        except ValueError:
            raise SystemExit(f"--only {spec!r}: expected TAG@MULTIPLE")
        if (tag, m) not in all_units():
            raise SystemExit(f"--only {spec!r}: not a registered unit "
                             f"(networks {ab.NETWORKS}, multiples {ab.SWEEP_MULTIPLES})")
        units.append((tag, m))
    return units


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

def local_imports(entry: Path, root: Path = ROOT) -> set[Path]:
    """Repo files reachable from `entry` through import statements.

    It parses the source rather than importing it, so nothing runs. It walks
    every import node, including the ones inside functions, because
    influence/features.py imports some heavy modules lazily. A name that
    resolves to no file under `root` is a third-party package and is skipped.
    """
    seen, todo = set(), [entry.resolve()]
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        pkg = path.parent.relative_to(root).parts
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".") for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = list(pkg[: len(pkg) - node.level + 1]) if node.level else []
                mod = node.module.split(".") if node.module else []
                # "from . import x" and "from pkg import mod" can name modules
                # as well as attributes, so try both readings.
                names = [base + mod] + [base + mod + [a.name] for a in node.names]
            for parts in names:
                for cand in (root.joinpath(*parts).with_suffix(".py"),
                             root.joinpath(*parts, "__init__.py")):
                    if parts and cand.is_file():
                        todo.append(cand.resolve())
    return seen


def identity_sources() -> list[Path]:
    files = set()
    for script in STAGE_SCRIPTS:
        files |= local_imports(ROOT / script)
    # The ORCA binary computes the graphlet columns. It is not Python, so the
    # import walk cannot see it, but a rebuilt binary changes those features.
    files.add(ROOT / "vendor" / "orca.exe")
    files |= {ROOT / "data" / f"{tag}.txt" for tag in ab.NETWORKS}
    files |= {ROOT / ab.LOCATOR_DIR / f"{tag}.json" for tag in ab.NETWORKS}
    return sorted(files)


def current_identity() -> dict[str, str]:
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in identity_sources()}


def check_manifest(identity: dict[str, str], write: bool) -> str:
    """Compare against the recorded manifest; record it on the first real run."""
    if not MANIFEST.exists():
        if write:
            MANIFEST.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
            return f"manifest recorded: {len(identity)} files pinned"
        return f"no manifest yet; {len(identity)} files would be pinned"
    recorded = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed = sorted(k for k in recorded.keys() | identity.keys()
                     if recorded.get(k) != identity.get(k))
    if changed:
        raise RuntimeError(f"source identity differs from {MANIFEST.name} in {changed}; "
                           "refusing. Do not rewrite the manifest to pass this; record "
                           "the decision in the LOG first.")
    return f"manifest MATCHES ({len(identity)} files)"


# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------

def pid_is_live_python(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FI", "IMAGENAME eq python.exe",
                          "/NH", "/FO", "CSV"], capture_output=True, text=True).stdout
    return f'"{pid}"' in out


def take_lock(lock: Path = LOCK) -> str:
    """Create the lock, or explain why not.

    O_EXCL makes creation atomic, so two controllers started together cannot
    both succeed. A leftover lock from a dead process is renamed rather than
    deleted: it is the only record that a run was killed.
    """
    note = "lock taken"
    if lock.exists():
        pid = int(lock.read_text().strip())
        if pid_is_live_python(pid):
            raise RuntimeError(f"{lock.name} names PID {pid}, which is a live python.exe; "
                               "another controller may be writing. Refusing.")
        stale = lock.with_name(f"stale_lock_{pid}_{datetime.now():%H%M%S}.txt")
        os.replace(lock, stale)
        note = f"stale lock from PID {pid} (not alive) renamed to {stale.name}; resuming"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return note


# ---------------------------------------------------------------------------
# Per-unit checks
# ---------------------------------------------------------------------------

def stage1_done(d: Path, tag: str, m: float) -> bool:
    meta_path = d / f"cache_meta_{tag}.json"
    if not meta_path.exists():
        return False
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    # A meta file for a different setting in this directory is not "done";
    # it is a contradiction, and refitting on top of it would hide that.
    want = {"multiple": m, "n_sims": N_SIMS, "convention": CONVENTION, "max_hop": MAX_HOP}
    got = {k: meta.get(k) for k in want}
    if got != want:
        raise RuntimeError(f"{meta_path} records {got}, expected {want}")
    return all((d / f"{kind}_{tag}.{ext}").exists() for kind, ext in
               (("cache_features", "csv"), ("cache_targets", "csv"),
                ("cache_registry", "csv"), ("cache_cascades", "npy")))


def unit_done(d: Path, tag: str, m: float) -> tuple[bool, str]:
    """Complete means exactly the registered cells, each with its OOF prediction."""
    sweep, oof = d / f"sweep_{tag}.csv", d / f"cache_oof_{tag}.npz"
    if not (sweep.exists() and oof.exists()):
        return False, "no sweep yet"
    df = pd.read_csv(sweep)
    keys = [(r.target, int(r.radius), r.richness, int(r.seed)) for r in df.itertuples()]
    want = expected_keys(m)
    if len(keys) != len(set(keys)):
        return False, f"{len(keys) - len(set(keys))} duplicate rows"
    if set(keys) != want:
        return False, f"{len(want - set(keys))} cells missing, {len(set(keys) - want)} unexpected"
    with np.load(oof) as store:
        missing = [k for k in want if f"{k[0]}|{k[1]}|{k[2]}|{k[3]}" not in store.files]
    if missing:
        return False, f"{len(missing)} OOF predictions missing"
    return True, f"{len(want)} cells"


# The one column a deterministic refit is allowed to change: wall-clock fit
# time. feature_seconds comes from stage-1 timings, so it must repeat exactly.
REFIT_FREE_COLUMNS = ("fit_seconds",)


def reconcile_refits(d: Path, tag: str) -> int:
    """Remove the stale copy of each cell stage 2 refitted after an interruption.

    WHY DUPLICATES APPEAR. stage2_sweep.py appends each cell's CSV row at once
    but flushes the OOF prediction store once per grid row (ten seeds). A host
    reset inside a grid row leaves cells with a row and no prediction vector.
    On resume stage 2 counts a cell as done only if it has both, so it refits
    those cells, which is deliberate, and appends a second row for each. Seen
    first on 2026-10-13: the 05:36 reset left seeds 0-3 of
    (spread_resid, r=3, node+edge) at p2p-Gnutella08@2.0 with rows but no
    predictions.

    WHAT COUNTS AS A SAFE DUPLICATE. Every fit is seeded, so a refit must
    reproduce its earlier row exactly. The rows are compared as raw CSV text,
    not parsed floats, so nothing is re-serialised and "equal" means
    byte-equal in every field except fit_seconds. Any other difference would
    mean the fit is not reproducible, and that is a failure, not something to
    tidy away. Each duplicated cell must also have its vector in the OOF
    store, which only the refit can have written.

    WHICH COPY IS KEPT. The last one: it belongs to the same run as the stored
    prediction vector. The removed lines are appended to
    refit_duplicates_<tag>.csv next to the sweep as evidence. The sweep is
    rewritten atomically, and every other line is kept byte for byte.

    stage2_sweep.py is pinned, so the fix lives here rather than in its
    resume logic. Returns the number of lines removed (0 = nothing to do).
    """
    sweep = d / f"sweep_{tag}.csv"
    oof = d / f"cache_oof_{tag}.npz"
    if not sweep.exists():
        return 0
    raw = sweep.read_bytes().decode("utf-8")
    lines = raw.splitlines(keepends=True)
    header = next(csv.reader([lines[0]]))
    col = {name: i for i, name in enumerate(header)}
    free = {col[c] for c in REFIT_FREE_COLUMNS}

    # Map each cell key to the indices of its data lines, in file order.
    seen: dict[tuple[str, str, str, str], list[int]] = {}
    fields: dict[int, list[str]] = {}
    for i in range(1, len(lines)):
        row = next(csv.reader([lines[i]]))
        fields[i] = row
        key = (row[col["target"]], row[col["radius"]], row[col["richness"]], row[col["seed"]])
        seen.setdefault(key, []).append(i)
    groups = {k: v for k, v in seen.items() if len(v) > 1}
    if not groups:
        return 0

    with np.load(oof) as store:
        stored = set(store.files)
    drop: list[int] = []
    for key, idx in groups.items():
        ref = [f for j, f in enumerate(fields[idx[-1]]) if j not in free]
        for i in idx[:-1]:
            other = [f for j, f in enumerate(fields[i]) if j not in free]
            if other != ref:
                raise RuntimeError(f"{tag}: cell {key} was refitted with a different result; "
                                   "the fit is not reproducible, refusing to reconcile")
        if "|".join(key) not in stored:
            raise RuntimeError(f"{tag}: cell {key} is duplicated but has no OOF prediction")
        drop.extend(idx[:-1])

    # Evidence first, then the rewrite. A crash in between leaves the evidence
    # and the old sweep; the next run reconciles again and appends the same
    # lines a second time, which is harmless.
    evidence = d / f"refit_duplicates_{tag}.csv"
    with open(evidence, "a", encoding="utf-8", newline="") as f:
        if f.tell() == 0:
            f.write(lines[0])
        f.writelines(lines[i] for i in sorted(drop))
    keep = "".join(line for i, line in enumerate(lines) if i not in set(drop))
    tmp = sweep.with_name(sweep.name + ".tmp")
    tmp.write_bytes(keep.encode("utf-8"))
    os.replace(tmp, sweep)
    return len(drop)


def check_multiple_identity(tag: str, d: Path, m: float) -> dict:
    """Prereg E3 at multiple m, against the stage-1 cache in d.

    Three checks, all required:
    - beta_c and p in this directory's cache agree with the values the locator
      used (the root cache's beta_c, and transmission_probability at m) to a
      relative BETA_C_RTOL, the eigensolve's own tolerance. Stage 1
      recomputes beta_c, and ARPACK reproduces it only to within that
      tolerance, so equality is not available. A real mismatch (a different
      graph or method) is many orders larger.
    - The first 500 cached draws equal a fresh 500-draw run at seed 0 BIT FOR
      BIT, so the fitted targets come from the same live-edge draws the
      locator measured at this m. chi of those draws must equal the recorded
      locator row.
    - The registered test: chi from all 4,000 draws is within 3 bootstrap SE
      of the 500-draw chi.
    The bootstrap is the same as analyse_beta_sweep.check_root_identity (seed,
    reps, resampling). That function is pinned to the root 1.5x cache, which
    is why the few lines are repeated here.
    """
    root_meta = json.loads((ROOT / f"cache_meta_{tag}.json").read_text(encoding="utf-8"))
    meta = json.loads((d / f"cache_meta_{tag}.json").read_text(encoding="utf-8"))
    p = transmission_probability(root_meta["beta_c"], m)
    net = load_edgelist(str(ROOT / "data" / f"{tag}.txt"))
    cached = np.load(d / f"cache_cascades_{tag}.npy", mmap_mode="r")
    fresh = simulate_ic_percolation(net, p=p, n_sims=ab.FINE_DRAWS, convention=CONVENTION,
                                    seed=ab.FINE_SEED, verbose=False).sizes
    identical = bool(np.array_equal(np.asarray(cached[:, :ab.FINE_DRAWS]), fresh))
    s1_all, _ = ab.largest_two(np.asarray(cached))
    s1_fresh, _ = ab.largest_two(fresh)
    chi_all, chi_fresh = ab.susceptibility(s1_all), ab.susceptibility(s1_fresh)
    rng = np.random.default_rng(ab.BOOT_SEED)
    boot = [ab.susceptibility(s1_fresh[rng.integers(0, ab.FINE_DRAWS, ab.FINE_DRAWS)])
            for _ in range(ab.BOOT_REPS)]
    se = float(np.std(boot, ddof=1))
    z = abs(chi_all - chi_fresh) / se if se > 0 else float("inf")
    curve = pd.read_csv(ROOT / ab.LOCATOR_DIR / f"{tag}.csv")
    chi_recorded = float(curve.loc[np.isclose(curve["m"], m), "chi"].iloc[0])
    # beta_c is compared to the eigensolve's tolerance (BETA_C_RTOL), not
    # exactly. The first pilot (email-Eu-core@1.25, 2026-10-12 13:59) found
    # stage 1's recomputed beta_c 1.7e-14 away from the root cache's, and
    # ca-GrQc@1.25 (2026-10-14) 1.37e-12, both with bit-identical draws.
    # Bit-identity of the draws is the property the locator needs, and it
    # stays exact.
    rel_beta = abs(meta["beta_c"] - root_meta["beta_c"]) / root_meta["beta_c"]
    rel_p = abs(meta["p"] - p) / p
    res = {"network": tag, "m": m,
           "beta_c_rel_diff": rel_beta, "p_rel_diff": rel_p,
           "beta_c_rtol": BETA_C_RTOL,
           "beta_c_matches_locator": bool(rel_beta <= BETA_C_RTOL),
           "p_matches_locator": bool(rel_p <= BETA_C_RTOL),
           "first_500_columns_identical": identical,
           "chi_fresh_500": chi_fresh, "chi_recorded_locator": chi_recorded,
           "chi_matches_locator": bool(np.isclose(chi_fresh, chi_recorded, rtol=1e-12, atol=0)),
           "chi_cache_4000": chi_all, "bootstrap_se_500": se, "abs_diff_in_se": z,
           "within_3_se": bool(z <= 3.0)}
    res["pass"] = all(res[k] for k in ("beta_c_matches_locator", "p_matches_locator",
                                       "first_500_columns_identical", "chi_matches_locator",
                                       "within_3_se"))
    return res


# ---------------------------------------------------------------------------
# Running a stage
# ---------------------------------------------------------------------------

def child_env() -> dict:
    """The conda env's DLL folders first on PATH, as `conda activate` would put
    them. A WMI-launched process inherits the system PATH, not an activated
    shell's, and a numpy that loads the wrong BLAS aborts with no traceback
    (vault brain/Gotchas.md: the OpenBLAS/MKL conflict)."""
    env_root = Path(sys.executable).parent
    extra = [env_root, env_root / "Library" / "mingw-w64" / "bin",
             env_root / "Library" / "usr" / "bin", env_root / "Library" / "bin",
             env_root / "Scripts"]
    path = os.pathsep.join(str(p) for p in extra if p.is_dir())
    return dict(os.environ, PATH=path + os.pathsep + os.environ.get("PATH", ""),
                PYTHONIOENCODING="utf-8")


def run_stage(name: str, args: list[str], cwd: Path, tag: str) -> float:
    """Run one stage with its output in files beside its caches; return seconds."""
    t0 = time.time()
    with (cwd / f"{name}_{tag}.out.log").open("ab") as out, \
            (cwd / f"{name}_{tag}.err.log").open("ab") as err:
        rc = subprocess.run([sys.executable, *args], cwd=cwd, env=child_env(),
                            stdin=subprocess.DEVNULL, stdout=out, stderr=err).returncode
    if rc:
        raise RuntimeError(f"{name} {tag} exited {rc}; see {cwd.name}/{name}_{tag}.err.log")
    return time.time() - t0


def run_unit(tag: str, m: float, identity: dict[str, str]) -> None:
    d = ROOT / ab.mult_dir(m)
    d.mkdir(parents=True, exist_ok=True)
    done, why = unit_done(d, tag, m)
    if done:
        log(f"SKIP {tag}@{m} already complete ({why})")
        return
    if current_identity() != identity:
        raise RuntimeError("a pinned file changed while the controller was running; "
                           "stopping before the next unit")
    log(f"BEGIN {tag}@{m}")
    if stage1_done(d, tag, m):
        log(f"  stage1 {tag}@{m} cached")
    else:
        # A relative path keeps the absolute location out of the cache's
        # provenance. stage 2 resolves it against the same cwd.
        edges = os.path.relpath(ROOT / "data" / f"{tag}.txt", d)
        secs = run_stage("stage1", [str(ROOT / "stage1_prepare.py"), edges, str(N_SIMS),
                                    repr(m), CONVENTION], d, tag)
        log(f"  stage1 {tag}@{m} {secs:.0f}s")
        if not stage1_done(d, tag, m):
            raise RuntimeError(f"stage1 {tag}@{m} exited 0 but its caches are incomplete")
    # extract_features drops the graphlet columns WITHOUT an error when it
    # cannot find ORCA. Then the subgraph tier would be quietly thinner than
    # at every other multiple. The root cache was built with the full set, so
    # the column list must match it exactly. Only the values of the
    # p-dependent dynamic columns may differ.
    cols = list(pd.read_csv(d / f"cache_features_{tag}.csv", nrows=0).columns)
    root_cols = list(pd.read_csv(ROOT / f"cache_features_{tag}.csv", nrows=0).columns)
    if cols != root_cols:
        raise RuntimeError(f"{tag}@{m}: feature columns differ from the root cache "
                           f"({len(cols)} vs {len(root_cols)}); was ORCA found?")
    e3_path = d / f"e3_{tag}.json"
    e3 = check_multiple_identity(tag, d, m)
    ab.write_atomic(e3_path, json.dumps(e3, indent=2) + "\n")
    if not e3["pass"]:
        raise RuntimeError(f"E3 failed at {tag}@{m}; see {d.name}/{e3_path.name}")
    log(f"  E3 {tag}@{m} PASS (chi 4000 vs 500: {e3['abs_diff_in_se']:.2f} SE)")
    secs = run_stage("stage2", [str(ROOT / "stage2_sweep.py"), tag, ",".join(stage_targets(m)),
                                str(MAX_HOP), str(N_SEEDS)], d, tag)
    removed = reconcile_refits(d, tag)
    if removed:
        log(f"  reconciled {tag}@{m}: {removed} stale row(s) of refitted cells removed "
            f"(identical except fit_seconds; see refit_duplicates_{tag}.csv)")
    done, why = unit_done(d, tag, m)
    if not done:
        raise RuntimeError(f"stage2 {tag}@{m} exited 0 but the unit is incomplete: {why}")
    log(f"COMPLETE {tag}@{m} ({why}; stage2 {secs:.0f}s)")


def preconditions(units) -> None:
    missing = [p for p in identity_sources() if not p.exists()]
    if missing:
        raise RuntimeError(f"missing inputs: {[p.relative_to(ROOT).as_posix() for p in missing]}")
    # Prereg B: the locator is fixed before any cell. A network without a
    # recorded locator gets no cells.
    for tag, _ in units:
        if not (ROOT / ab.LOCATOR_DIR / f"{tag}.json").exists():
            raise RuntimeError(f"{tag}: no recorded locator; L1 cells may not run before it")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase 6.5 L1 beta/beta_c sweep controller")
    ap.add_argument("--only", nargs="+", metavar="TAG@M", help="run only these units")
    ap.add_argument("--dry-run", action="store_true",
                    help="check preconditions and identity, launch nothing")
    args = ap.parse_args(argv)
    units = parse_only(args.only)
    preconditions(units)
    identity = current_identity()
    if args.dry_run:
        print(check_manifest(identity, write=False))
        for tag, m in units:
            d = ROOT / ab.mult_dir(m)
            print(f"  {tag}@{m}: {unit_done(d, tag, m)[1]}; {len(expected_keys(m))} cells registered")
        print(f"dry run: preconditions PASS; {len(units)} units; nothing launched")
        return 0

    log(f"START pid={os.getpid()} units={len(units)} {take_lock()}")
    ok = False
    try:
        log(check_manifest(identity, write=True))
        log(f"  unpinned: probe_beta_sweep.py {digest(Path(__file__))[:16]}, "
            f"analyse_beta_sweep.py {digest(ROOT / 'analyse_beta_sweep.py')[:16]}")
        for tag, m in units:
            run_unit(tag, m, identity)
        ok = True
        log(f"ALL UNITS COMPLETE ({len(units)})")
    except Exception as exc:
        log(f"FAILED {exc}")
        raise
    finally:
        # Reached on a normal exit or an exception. A killed process never gets
        # here, so its lock stays and the next start renames it.
        LOCK.unlink(missing_ok=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

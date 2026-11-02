"""L6 certificate on the synthetic corpus (= Phase 7's D3 prerequisite).

Registered in docs/prereg/prereg_phase6_5_lanes.md, "L6 execution definitions"
(2026-11-02 19:53). The corpus is stage0_generate.py's gamma family (8 Chung-Lu
graphs, <k> = 6) plus the ER / BA / WS controls, n = 5000, seed 0.

prepare (0 fits). Per graph, in registered order:
  - records corpus.json: each edge list's sha256, stage 0's manifest row, the
    size after the largest-component step, and nb_spectral_gap (part E);
  - runs unmodified stage1_prepare.py <edgelist> 4000 1.5 uniform with
    cwd=results/phase7_certificate/, so its caches never touch the repo root.
    The edge list is passed relative to that cwd, which is what lets stage 2's
    source guard rehash it later without an absolute path in any file;
  - records sources.json, the hashes the fit step pins.

fit. Per graph: unmodified stage2_sweep.py twice,
  spread_mean   rf (default)  -> sweep_<tag>.csv,                       primary
  betweenness   rf_log1p      -> estimators/sweep_<tag>__rf_log1p.csv,  control
  radii 0-3, all four rungs, 5 seeds: 80 cells each. Resumable; the L1
  controller's lock, stage runner and refit reconciliation are imported, as in
  L5, because they are the versions that survived three host resets.

Run from the repo root:
  python probe_certificate.py prepare
  python probe_certificate.py fit [--only TAG ...]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from influence.experiment import TIER_LADDER
from influence.nb_spectrum import nb_spectral_gap
from influence.preprocessing import load_edgelist
from probe_beta_sweep import local_imports, reconcile_refits, run_stage, take_lock
from probe_threshold_arm import sha256, write_atomic

ROOT = Path(__file__).resolve().parent
OUT = Path("results/phase7_certificate")
SYN = Path("data/synthetic")
LOCK = OUT / "active.lock"

# Part A. The gamma family in gamma order, then the controls. Tags are the
# edge-list stems stage 0 writes (net.name), which stage 1 reuses as its tag.
GAMMAS = (2.1, 2.3, 2.5, 2.8, 3.0, 3.3, 3.6, 4.0)
GAMMA_TAGS = tuple(f"CL_n5000_g{g:g}_k6" for g in GAMMAS)
CONTROL_TAGS = ("ER_n5000_k6", "BA_n5000_m3", "WS_n5000_k6_b0.1")
PLAN = GAMMA_TAGS + CONTROL_TAGS

# Part B. stage 1 at the root's settings; stage 2's reduced protocol.
N_SIMS, MULTIPLE, CONVENTION = 4000, 1.5, "uniform"
MAX_HOP, N_SEEDS = 3, 5
ARMS = (("spread_mean", "rf"), ("betweenness", "rf_log1p"))


def log(message: str) -> None:
    from datetime import datetime
    line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}"
    print(line, flush=True)
    with (OUT / "controller.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def edgelist(tag: str) -> Path:
    return SYN / f"{tag}.txt"


def rel_from_out(path: Path) -> str:
    # The path stage 1 receives and records in cache_meta: relative to OUT,
    # forward slashes, so the recorded provenance holds no machine path.
    return Path(os.path.relpath(ROOT / path, ROOT / OUT)).as_posix()


def pinned_files() -> list[Path]:
    """Every repo file that decides a number here, as repo-relative paths."""
    files = set()
    for entry in ("stage1_prepare.py", "stage2_sweep.py"):
        files |= {p.relative_to(ROOT) for p in local_imports(ROOT / entry)}
    files |= {edgelist(t) for t in PLAN}
    return sorted(files)


def current_sources() -> dict[str, str]:
    return {p.as_posix(): sha256(ROOT / p) for p in pinned_files()}


def check_sources() -> None:
    recorded = json.loads((OUT / "sources.json").read_text(encoding="utf-8"))
    current = current_sources()
    changed = sorted(k for k in recorded.keys() | current.keys()
                     if recorded.get(k) != current.get(k))
    if changed:
        raise RuntimeError(f"pinned inputs changed since prepare: {changed}; refusing")


def stage1_done(tag: str) -> bool:
    names = [f"cache_{kind}_{tag}.csv" for kind in ("features", "targets", "registry")]
    names.append(f"cache_meta_{tag}.json")
    if not all((OUT / n).is_file() for n in names):
        return False
    meta = json.loads((OUT / f"cache_meta_{tag}.json").read_text(encoding="utf-8"))
    # A cache built under other settings is not this lane's cache.
    return (meta["n_sims"], meta["multiple"], meta["convention"], meta["max_hop"]) == \
        (N_SIMS, MULTIPLE, CONVENTION, MAX_HOP)


def run_prepare() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {Path(row["path"]).stem: row
                for row in json.loads((SYN / "manifest.json").read_text(encoding="utf-8"))}
    missing = [t for t in PLAN if t not in manifest or not edgelist(t).is_file()]
    if missing:
        raise SystemExit(f"run stage0_generate.py first (part A); missing {missing}")

    corpus = {"registered_in": "prereg 2026-11-02 19:53 L6 parts A, E",
              "generator_command": "python stage0_generate.py --n 5000 "
                                   "--families gamma,controls --seed 0 --bootstrap 200",
              "graphs": {}}
    for tag in PLAN:
        net = load_edgelist(str(edgelist(tag)))
        row = {k: v for k, v in manifest[tag].items() if k != "path"}
        corpus["graphs"][tag] = {
            "edge_list": edgelist(tag).as_posix(),
            "edge_list_sha256": sha256(edgelist(tag)),
            # Stage 0 profiles the generated graph; stage 1 fits its largest
            # component. Both are kept because they differ (part A confound).
            "stage0_profile": row,
            "lcc_n": int(net.n), "lcc_m": int(net.m),
            "lcc_mean_degree": float(net.mean_degree),
            **nb_spectral_gap(net)}
        g = corpus["graphs"][tag]
        print(f"{tag:22s} lcc n={g['lcc_n']:5d} <k>={g['lcc_mean_degree']:.2f} "
              f"gap={g['nb_spectral_gap']:.4f} ({g['nb_method']})", flush=True)
    write_atomic(OUT / "corpus.json", json.dumps(corpus, indent=2, default=str) + "\n")

    for tag in PLAN:
        if stage1_done(tag):
            print(f"stage1 {tag} cached", flush=True)
            continue
        secs = run_stage("stage1", [str(ROOT / "stage1_prepare.py"), rel_from_out(edgelist(tag)),
                                    str(N_SIMS), str(MULTIPLE), CONVENTION], OUT, tag)
        if not stage1_done(tag):
            raise RuntimeError(f"stage1 {tag} exited 0 without its caches")
        print(f"stage1 {tag} {secs:.0f}s", flush=True)

    write_atomic(OUT / "sources.json", json.dumps(current_sources(), indent=2) + "\n")
    print("wrote", OUT / "corpus.json", "and", OUT / "sources.json")
    return 0


def arm_paths(tag: str, est: str) -> tuple[Path, Path, Path, str]:
    """(dir, sweep, oof, reconcile tag) where stage 2 writes this arm."""
    if est == "rf":
        return OUT, OUT / f"sweep_{tag}.csv", OUT / f"cache_oof_{tag}.npz", tag
    d = OUT / "estimators"
    return d, d / f"sweep_{tag}__{est}.csv", d / f"cache_oof_{tag}__{est}.npz", f"{tag}__{est}"


def arm_done(tag: str, target: str, est: str) -> tuple[bool, str]:
    """Done means exactly the expected cells, each with its OOF prediction."""
    _, sweep, oof, _ = arm_paths(tag, est)
    if not (sweep.exists() and oof.exists()):
        return False, "no sweep yet"
    df = pd.read_csv(sweep)
    keys = [(r.target, int(r.radius), r.richness, int(r.seed)) for r in df.itertuples()]
    want = {(target, r, rung, s) for r in range(MAX_HOP + 1)
            for rung in TIER_LADDER for s in range(N_SEEDS)}
    if len(keys) != len(set(keys)):
        return False, f"{len(keys) - len(set(keys))} duplicate rows"
    if set(keys) != want:
        return False, f"{len(want - set(keys))} cells missing, {len(set(keys) - want)} unexpected"
    with np.load(oof) as store:
        missing = [k for k in want if "|".join(map(str, k)) not in store.files]
    if missing:
        return False, f"{len(missing)} OOF predictions missing"
    return True, f"{len(want)} cells"


def run_fit(only: list[str] | None) -> int:
    plan = [t for t in PLAN if not only or t in only]
    unknown = set(only or ()) - set(PLAN)
    if unknown:
        raise SystemExit(f"not an L6 graph: {sorted(unknown)}")
    if not all(stage1_done(t) for t in plan):
        raise SystemExit("run prepare first: a stage-1 cache is missing")
    log(f"START fit pid={os.getpid()} graphs={plan} {take_lock(LOCK)}")
    ok = False
    try:
        for tag in plan:
            for target, est in ARMS:
                # Checked before every arm, not once: a file edited mid-run must
                # stop the next fit, not be fitted into it.
                check_sources()
                done, why = arm_done(tag, target, est)
                if done:
                    log(f"SKIP {tag} {target}/{est} already complete ({why})")
                    continue
                log(f"BEGIN {tag} {target}/{est}")
                secs = run_stage(f"stage2_{target}", [str(ROOT / "stage2_sweep.py"), tag, target,
                                                      str(MAX_HOP), str(N_SEEDS), est], OUT, tag)
                d, _, _, rtag = arm_paths(tag, est)
                removed, worst = reconcile_refits(d, rtag)
                if removed:
                    log(f"  reconciled {tag} {target}: {removed} stale row(s) removed "
                        f"(largest score difference {worst:.3g})")
                done, why = arm_done(tag, target, est)
                if not done:
                    raise RuntimeError(f"stage2 {tag} {target} exited 0 but is incomplete: {why}")
                log(f"COMPLETE {tag} {target}/{est} ({why}; stage2 {secs:.0f}s)")
        ok = True
        log(f"ALL GRAPHS COMPLETE ({len(plan)})")
    except Exception as exc:
        log(f"FAILED {exc}")
        raise
    finally:
        # A killed process never reaches this, so its lock stays and the next
        # start renames it as evidence (take_lock).
        LOCK.unlink(missing_ok=True)
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["prepare", "fit"])
    ap.add_argument("--only", nargs="+", metavar="TAG", help="fit: only these graphs")
    args = ap.parse_args(argv)
    return run_prepare() if args.command == "prepare" else run_fit(args.only)


if __name__ == "__main__":
    sys.exit(main())

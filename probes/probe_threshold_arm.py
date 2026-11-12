"""Complex-contagion arm: the ignition gate, then the stage-2 fits.

Registered in docs/prereg/prereg_phase6_5_lanes.md: "complex-contagion execution definitions"
(2026-11-02 10:55) and "complex-contagion run status" (2026-11-02 16:09).

gate (0 fits), 10:55 part C. Per (network, theta):
  spread_theta(i) = final size of the fractional-threshold cascade seeded on N[i]
  ignites(i)      = spread_theta(i) > 0.05 * n   (strict, as production's
                    CascadeResults.ignition_probability(0.05))
  gate passes     = mean ignites in [0.1, 0.9], inclusive.

prepare (0 fits), 16:09 part B. For every network with a passing theta, lays
  out stage 2's cwd: byte-identical copies of the root feature, registry and
  meta caches, plus a new cache_targets_<tag>.csv holding spread_theta<x>
  (primary) and ignites_theta<x> (secondary) built from sizes_<tag>.npz.
  Records sources.json, the hashes the fit step pins.

fit, 16:09 part B. Unmodified pipeline/stage2_sweep.py per network, smallest first,
  resumable. The lock, stage runner and refit reconciliation are the beta-sweep
  controller's own (probes/probe_beta_sweep.py), imported rather than copied, because
  they are the versions that already survived three host resets.

Everything is written under results/phase7_threshold/, never the repo root:
  sizes_<tag>.npz  per-node sizes at every theta, with node order and original
                   ids, so the fits use these exact numbers rather than a re-run
  gate.json        the verdict per (network, theta), with source hashes
  sources.json     hashes pinned for the fits
  controller.log   one timestamped line per fit-step event

Run from the repo root:
  python probes/probe_threshold_arm.py gate
  python probes/probe_threshold_arm.py prepare
  python probes/probe_threshold_arm.py fit [--only TAG ...]
"""
import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyse_beta_sweep import NETWORKS, load_network
from influence.experiment import TIER_LADDER
from influence.threshold_dynamics import exact_theta, threshold_cascade_sizes
# The beta-sweep controller's machinery. Importing the module runs only its constant
# definitions (no sweep starts on import).
from probe_beta_sweep import local_imports, reconcile_refits, run_stage, take_lock

THETAS = (0.1, 0.2)
IGNITION_FRAC = 0.05          # strict ">", the production spread_ignition cut
GATE_BAND = (0.1, 0.9)        # inclusive
OUT = Path("results/phase7_threshold")
ROOT = Path(__file__).resolve().parents[1]

# Fit grid, 16:09 part B. Stage 2 fits every TIER_LADDER rung; the dynamic
# rung is fitted but never scored (the disclosed deviation), so the expected
# cell set is built from the full ladder, not from the three scored rungs.
MAX_HOP = 3
N_SEEDS = 10
# Copied byte for byte from the root into stage 2's cwd. The targets file is
# NOT in this list: it is the one file this arm writes itself.
# Copied from the repo cache (ROOT_CACHE) into OUT, where they sit flat beside
# the sweep like every sub-run folder's cache.
ROOT_CACHE = Path("data/cache")
COPIED = ("cache_features_{tag}.csv", "cache_registry_{tag}.csv", "cache_meta_{tag}.json")
AUDIT = "cache_provenance_audit_20260911.json"
LOCK = OUT / "active.lock"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, text: str) -> None:
    # Write-then-rename, so a host reset mid-write can never leave a truncated
    # gate.json that reads as a valid (and wrong) verdict.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def gate_one(sizes: np.ndarray, n: int) -> dict:
    """Gate verdict for one (network, theta) from its per-node sizes."""
    ignites = sizes > IGNITION_FRAC * n
    frac = float(ignites.mean())
    q = np.quantile(sizes, [0, .1, .25, .5, .75, .9, 1])
    return {"ignition_fraction": frac,
            "passes": bool(GATE_BAND[0] <= frac <= GATE_BAND[1]),
            "n_ignite": int(ignites.sum()),
            "size_quantiles": dict(zip(["min", "q10", "q25", "median", "q75", "q90", "max"],
                                       [float(x) for x in q])),
            # Distinct sizes: a target with very few distinct values ranks
            # mostly by ties, which matters for reading tau later.
            "n_distinct_sizes": int(np.unique(sizes).size)}


def run_gate() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {p: sha256(Path(p)) for p in
               ("probes/probe_threshold_arm.py", "influence/threshold_dynamics.py",
                "analysis/analyse_beta_sweep.py")}
    result = {"registered_in": "prereg addendum 2026-11-02 10:55 IST, part C",
              "ignition": f"size > {IGNITION_FRAC} * n", "band": list(GATE_BAND),
              "thetas": list(THETAS), "sources": sources, "networks": {}}
    for tag in NETWORKS:
        net, meta, path = load_network(tag)
        per = {"n": net.n, "m": net.m, "edge_list_sha256": sha256(path)}
        arrays = {"node": np.arange(net.n), "original_id": np.asarray(net.original_ids)}
        for theta in THETAS:
            t0 = time.perf_counter()
            sizes = threshold_cascade_sizes(net, theta)
            secs = time.perf_counter() - t0
            g = gate_one(sizes, net.n)
            g["seconds"] = round(secs, 2)
            per[f"theta{theta}"] = g
            arrays[f"theta{theta}"] = sizes
            print(f"{tag:18s} theta={theta}: ignition {g['ignition_fraction']:.3f} "
                  f"({'PASS' if g['passes'] else 'fail'}), median size "
                  f"{g['size_quantiles']['median']:.0f} of n={net.n}, {secs:.1f} s", flush=True)
        np.savez(OUT / f"sizes_{tag}.npz", **arrays)
        result["networks"][tag] = per
    passing = [(t, th) for t in NETWORKS for th in THETAS
               if result["networks"][t][f"theta{th}"]["passes"]]
    result["passing"] = [f"{t}@{th}" for t, th in passing]
    result["verdict"] = ("gate passes on some pairs: fits run on those only" if passing
                         else "gate fails everywhere: report the gate, no fits (prereg section 3)")
    write_atomic(OUT / "gate.json", json.dumps(result, indent=2) + "\n")
    print(f"passing: {result['passing'] or 'none'}")
    return 0


def log(message: str) -> None:
    """One timestamped line to stdout and to controller.log."""
    line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}"
    print(line, flush=True)
    with (OUT / "controller.log").open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def passing_plan() -> dict[str, list[str]]:
    """{tag: [theta, ...]} for every passing pair, smallest network first.

    Read from gate.json rather than recomputed, so the fits can only ever run
    on the pairs the recorded gate passed. Smallest first: the first network
    completes in minutes and shows whether the plumbing works before the long
    ones start.
    """
    gate = json.loads((OUT / "gate.json").read_text(encoding="utf-8"))
    plan: dict[str, list[str]] = {}
    for pair in gate["passing"]:
        tag, theta = pair.split("@")
        plan.setdefault(tag, []).append(theta)
    return dict(sorted(plan.items(), key=lambda kv: gate["networks"][kv[0]]["n"]))


def targets_for(thetas: list[str]) -> list[str]:
    # Primary first, then the secondary added 16:09 part A, for every theta.
    return [f"{kind}_theta{t}" for t in thetas for kind in ("spread", "ignites")]


def pinned_files(plan: dict[str, list[str]]) -> list[Path]:
    """Everything that decides a fitted number, as repo-relative paths."""
    files = {p.relative_to(ROOT) for p in local_imports(ROOT / "pipeline/stage2_sweep.py")}
    files.add(Path("influence/threshold_dynamics.py"))
    files.add(ROOT_CACHE / AUDIT)
    for tag in plan:
        files.add(Path("data") / f"{tag}.txt")
        files |= {ROOT_CACHE / name.format(tag=tag) for name in COPIED}
    return sorted(files)


def run_prepare() -> int:
    plan = passing_plan()
    if not plan:
        print("gate passed nowhere: nothing to prepare (prereg section 3)")
        return 0
    audit = json.loads((ROOT / ROOT_CACHE / AUDIT).read_text(encoding="utf-8"))["networks"]
    for tag, thetas in plan.items():
        # The edge list must be the one the root cache was built from. Stage 2
        # cannot check this from its cwd (it reports the file as missing and
        # carries on), so it is checked here, once, before anything is copied.
        edge_sha = sha256(ROOT / "data" / f"{tag}.txt")
        if audit[tag]["source_sha256"] != edge_sha:
            raise SystemExit(f"{tag}: data/{tag}.txt does not hash to the root cache's "
                             "recorded edge list; refusing")
        for name in (*(n.format(tag=tag) for n in COPIED), AUDIT):
            src, dst = ROOT / ROOT_CACHE / name, OUT / name
            if dst.exists():
                # Never overwrite: an existing copy that differs means a
                # sweep may already have been bound to it.
                if sha256(dst) != sha256(src):
                    raise SystemExit(f"{dst} exists and differs from the root copy; refusing")
            else:
                shutil.copyfile(src, dst)
                if sha256(dst) != sha256(src):
                    raise SystemExit(f"copy of {name} does not hash to its original")

        # Row alignment. Stage 2 pairs feature row j with target row j by
        # POSITION, so the targets must be in the feature cache's node order.
        # Both came from the same loader, but that is checked, not assumed.
        feats = pd.read_csv(OUT / f"cache_features_{tag}.csv", usecols=["node", "original_id"])
        with np.load(OUT / f"sizes_{tag}.npz") as z:
            sizes = {k: z[k] for k in z.files}
        if not (np.array_equal(feats["node"].to_numpy(), sizes["node"])
                and np.array_equal(feats["original_id"].to_numpy(), sizes["original_id"])):
            raise SystemExit(f"{tag}: feature cache and sizes_{tag}.npz disagree on node order")

        n = len(sizes["node"])
        cols = {"node": sizes["node"]}
        for t in thetas:
            s = sizes[f"theta{t}"]
            cols[f"spread_theta{t}"] = s
            # The gate's own indicator, same strict cut, so the secondary
            # target cannot drift from what the gate measured.
            cols[f"ignites_theta{t}"] = (s > IGNITION_FRAC * n).astype(np.int64)
        text = pd.DataFrame(cols).to_csv(index=False, lineterminator="\n")
        dst = OUT / f"cache_targets_{tag}.csv"
        if dst.exists() and dst.read_text(encoding="utf-8") != text:
            raise SystemExit(f"{dst} exists with different contents; refusing")
        write_atomic(dst, text)
        print(f"{tag}: prepared {targets_for(thetas)} for n={n}")

    sources = {p.as_posix(): sha256(ROOT / p) for p in pinned_files(plan)}
    sources["cache_targets"] = {tag: sha256(OUT / f"cache_targets_{tag}.csv") for tag in plan}
    path = OUT / "sources.json"
    if path.exists():
        recorded = json.loads(path.read_text(encoding="utf-8"))
        if recorded != sources:
            raise SystemExit("sources.json already records different hashes; refusing. "
                             "Do not rewrite it to pass; record the decision in the LOG.")
    else:
        write_atomic(path, json.dumps(sources, indent=2) + "\n")
    print(f"sources.json: {len(sources) - 1} files and {len(plan)} target files pinned")
    return 0


def check_sources(plan: dict[str, list[str]]) -> None:
    recorded = json.loads((OUT / "sources.json").read_text(encoding="utf-8"))
    current = {p.as_posix(): sha256(ROOT / p) for p in pinned_files(plan)}
    current["cache_targets"] = {tag: sha256(OUT / f"cache_targets_{tag}.csv") for tag in plan}
    changed = sorted(k for k in recorded.keys() | current.keys()
                     if recorded.get(k) != current.get(k))
    if changed:
        raise RuntimeError(f"pinned inputs changed since prepare: {changed}; refusing")


def expected_cells(thetas: list[str]) -> set[tuple[str, int, str, int]]:
    return {(t, r, rung, s) for t in targets_for(thetas) for r in range(MAX_HOP + 1)
            for rung in TIER_LADDER for s in range(N_SEEDS)}


def network_done(tag: str, thetas: list[str]) -> tuple[bool, str]:
    """Done means exactly the expected cells, each with its OOF prediction."""
    sweep, oof = OUT / f"sweep_{tag}.csv", OUT / f"cache_oof_{tag}.npz"
    if not (sweep.exists() and oof.exists()):
        return False, "no sweep yet"
    df = pd.read_csv(sweep)
    keys = [(r.target, int(r.radius), r.richness, int(r.seed)) for r in df.itertuples()]
    want = expected_cells(thetas)
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
    plan = passing_plan()
    if only:
        unknown = set(only) - set(plan)
        if unknown:
            raise SystemExit(f"not a passing network: {sorted(unknown)}")
        plan = {t: th for t, th in plan.items() if t in only}
    log(f"START fit pid={os.getpid()} networks={list(plan)} {take_lock(LOCK)}")
    ok = False
    try:
        for tag, thetas in plan.items():
            # Checked before every network, not once: a file edited mid-run
            # must stop the next network, not be fitted into it.
            check_sources(plan)
            done, why = network_done(tag, thetas)
            if done:
                log(f"SKIP {tag} already complete ({why})")
                continue
            log(f"BEGIN {tag} targets={targets_for(thetas)}")
            secs = run_stage("stage2", [str(ROOT / "pipeline/stage2_sweep.py"), tag,
                                        ",".join(targets_for(thetas)), str(MAX_HOP),
                                        str(N_SEEDS)], OUT, tag)
            removed, worst = reconcile_refits(OUT, tag)
            if removed:
                log(f"  reconciled {tag}: {removed} stale row(s) removed "
                    f"(largest score difference {worst:.3g})")
            done, why = network_done(tag, thetas)
            if not done:
                raise RuntimeError(f"stage2 {tag} exited 0 but is incomplete: {why}")
            log(f"COMPLETE {tag} ({why}; stage2 {secs:.0f}s)")
        ok = True
        log(f"ALL NETWORKS COMPLETE ({len(plan)})")
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
    ap.add_argument("command", choices=["gate", "prepare", "fit"])
    ap.add_argument("--only", nargs="+", metavar="TAG", help="fit: only these networks")
    args = ap.parse_args(argv)
    # Validate the registered thetas once, up front, rather than mid-run.
    for theta in THETAS:
        exact_theta(theta)
    if args.command == "gate":
        return run_gate()
    if args.command == "prepare":
        return run_prepare()
    return run_fit(args.only)


if __name__ == "__main__":
    sys.exit(main())

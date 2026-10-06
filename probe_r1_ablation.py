"""Provenance-bound runner for the Phase 6 radius-one structural ablation.

Created 2026-09-10 by Claude Opus 5 for Phase 6 Task 5 (r=1 ablation scope gap).
Specification: docs/phase6_r1_ablation_implementation_brief.md Task 2, as
corrected by docs/phase6_r1_ablation_readiness_addendum.md items 1-6.

WHAT THIS PRODUCES
------------------
800 authoritative cells = 5 networks x 4 targets x 4 nested feature sets x 10
seeds, each a fresh five-fold out-of-fold fit bound to a complete input
identity. Plus one `pilot.json` (three fits, NOT part of the 800) that proves
the bounded inner worker count does not change the numbers.

WHY EVERY CELL IS REFIT RATHER THAN READ FROM A CACHE
-----------------------------------------------------
The historical `cache_oof_<network>.npz` endpoints look like they could answer
this question and cannot. They hold bare `target|radius|richness|seed` arrays
with no embedded manifest, no selected-column list or hash, no cache input
hash, no target-objective id, no fold digest and no estimator hash. A matching
column COUNT is not provenance. The root archive's `betweenness` endpoint also
belongs to the RAW objective while this design reports `rf_log1p`. Both
rejected candidates are hashed and named in the manifest (addendum item 4) so
the rejection is on the record rather than implied by silence.

RESUME POLICY (addendum item 5, stated once and tested)
--------------------------------------------------------
Every write attempt gets a UNIQUE temporary name, is fsynced, then atomically
replaces the final `<cell>.json`. A deterministic `<cell>.tmp` cannot both
survive as evidence of an interruption and be reused as the next attempt's
scratch file, so this runner never reuses a temp: stale uniquely-named temps
are ignored and left in place as interruption evidence. Resume reads only
final `cells/*.json`, and validates each one completely -- key, run_id, every
bound hash and the record checksum -- before it is allowed to skip a fit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
import tracemalloc
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn

from influence.experiment import evaluate, out_of_fold_predictions
from influence.preprocessing import load_edgelist
from influence.r1_ablation import (
    NETWORKS,
    N_SPLITS,
    RADIUS,
    SEEDS,
    SET_IDS,
    TARGETS,
    R1ContractError,
    assert_full_set_matches_select_features,
    canonical_sha256,
    cell_name,
    expected_keys,
    fold_digest,
    objective_for,
    require_finite,
    select_r1_sets,
    sort_key,
)
from influence.targets import assert_no_leakage

DEFAULT_OUT = Path("results/phase6_r1_ablation")

# Source files whose content changes the meaning of a cell. Hashed into the
# manifest so a mid-run edit to the estimator or the fold machinery cannot be
# absorbed silently by a resume -- the failure this project already hit once,
# when a stage-1 source changed under a running sweep.
SOURCE_FILES = (
    Path("probe_r1_ablation.py"),
    Path("analyse_r1_ablation.py"),
    Path("influence/r1_ablation.py"),
    Path("influence/estimators.py"),
    Path("influence/experiment.py"),
    Path("influence/features.py"),
    Path("influence/targets.py"),
)

# Pilot equivalence tolerances. Fixed here rather than chosen after seeing the
# numbers, which is the only way a gate means anything.
PILOT_JOBS = (1, 4, 8)
PILOT_ABS_TOL = 1e-10
PILOT_REL_TOL = 1e-9
PILOT_TAU_TOL = 1e-12
PILOT_CELL = ("ca-GrQc", "spread_mean", "full_r1_structural", 0)


class R1RunError(RuntimeError):
    """Raised when the run's identity or output contract cannot be satisfied."""


# ---------------------------------------------------------------------------
# Hashing and atomic I/O
# ---------------------------------------------------------------------------

def digest(path: Path) -> str:
    """SHA-256 of a file, streamed so a large cache is not held in memory."""
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def write_atomic_json(path: Path, record: dict) -> None:
    """Write via a UNIQUE temp, fsync, then atomically replace.

    The unique name is the addendum item 5 policy: a deterministic temp cannot
    serve as both interruption evidence and reusable scratch. `os.replace` is
    atomic on Windows and POSIX alike, so a reader never observes a half-written
    cell, and a crash leaves either the old final file or none at all.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False)
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def record_checksum(record: dict) -> str:
    """Checksum over the canonical record EXCLUDING the checksum field itself."""
    return canonical_sha256({k: v for k, v in record.items() if k != "content_sha256"})


# ---------------------------------------------------------------------------
# Input identity
# ---------------------------------------------------------------------------

def cache_paths(tag: str) -> dict[str, Path]:
    return {
        "features": Path(f"cache_features_{tag}.csv"),
        "targets": Path(f"cache_targets_{tag}.csv"),
        "registry": Path(f"cache_registry_{tag}.csv"),
        "meta": Path(f"cache_meta_{tag}.json"),
    }


def rejected_oof_paths(tag: str) -> dict[str, Path]:
    """Both historical endpoint candidates (addendum item 4).

    Recording only the root archive would leave the REPORTED betweenness
    endpoint -- the log1p one this design actually reports -- unaccounted for.
    """
    return {
        "root_raw_objective": Path(f"cache_oof_{tag}.npz"),
        "reported_log1p_betweenness": Path(f"estimators/cache_oof_{tag}__rf_log1p.npz"),
    }


def raw_paths() -> dict[str, Path]:
    """Map network name -> raw edge file, from the data manifest."""
    manifest_path = Path("data/manifest.json")
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {entry["name"]: Path(entry["path"].replace("\\", os.sep)) for entry in entries}


def load_bundle(tag: str, raw_path: Path) -> dict[str, object]:
    """Load one network's caches and bind their identity before any fit.

    Addendum item 3: `cache_meta` alone cannot establish node identity, so this
    rebuilds the LCC from the raw edge list and requires the cached
    `original_id` column to match it exactly. Without that, a feature row could
    silently belong to a different node than the target row beside it.
    """
    paths = cache_paths(tag)
    for name, path in paths.items():
        if not path.is_file():
            raise R1RunError(f"{tag}: {name} cache missing at {path}")
    features = pd.read_csv(paths["features"])
    targets = pd.read_csv(paths["targets"])
    registry = pd.read_csv(paths["registry"])
    meta = json.loads(paths["meta"].read_text(encoding="utf-8"))

    n_nodes = len(features)
    if len(targets) != n_nodes:
        raise R1RunError(f"{tag}: targets rows {len(targets)} != features rows {n_nodes}")
    for name, table in (("features", features), ("targets", targets)):
        if "node" not in table.columns:
            raise R1RunError(f"{tag}: {name} lacks a node column")
        if not np.array_equal(table["node"].to_numpy(), np.arange(n_nodes)):
            raise R1RunError(f"{tag}: {name}.node is not arange({n_nodes})")

    rebuilt = load_edgelist(raw_path, name=tag)
    if rebuilt.n != n_nodes:
        raise R1RunError(f"{tag}: rebuilt LCC nodes {rebuilt.n} != cache nodes {n_nodes}")
    if "original_id" not in features.columns:
        raise R1RunError(f"{tag}: feature cache lacks original_id")
    if not np.array_equal(features["original_id"].to_numpy(), rebuilt.original_ids):
        raise R1RunError(f"{tag}: cached original_id order differs from the rebuilt graph")
    if int(meta.get("n", -1)) != n_nodes:
        raise R1RunError(f"{tag}: cache metadata n does not match cache rows")

    for target in TARGETS:
        if target not in targets.columns:
            raise R1RunError(f"{tag}: cached target {target} is absent")
        require_finite(f"{tag}/{target}", targets[target].to_numpy(float))

    sets = select_r1_sets(features, registry)
    assert_full_set_matches_select_features(sets, features, registry)
    return {"features": features, "targets": targets, "registry": registry,
            "meta": meta, "sets": sets, "n_nodes": n_nodes}


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def build_manifest(root: Path, tags: tuple[str, ...]) -> dict:
    """Assemble the immutable launch configuration.

    `run_id` is the canonical SHA-256 of this document, so a cell that names a
    run_id is claiming provenance over every hash in it. Any input edit changes
    the run_id and therefore cannot be silently resumed into.
    """
    raws = raw_paths()
    inputs: dict[str, str] = {}
    rejected: dict[str, dict[str, str]] = {}
    node_counts: dict[str, int] = {}
    set_sizes: dict[str, dict[str, int]] = {}

    for tag in tags:
        if tag not in raws:
            raise R1RunError(f"{tag}: absent from data/manifest.json")
        bundle = load_bundle(tag, raws[tag])
        node_counts[tag] = int(bundle["n_nodes"])
        set_sizes[tag] = {set_id: len(columns)
                          for set_id, columns in bundle["sets"].items()}
        for name, path in {**cache_paths(tag), "raw": raws[tag]}.items():
            inputs[path.as_posix()] = digest(path)
        rejected[tag] = {}
        for reason, path in rejected_oof_paths(tag).items():
            # Inspected and NOT loaded as fit input. Recorded so the rejection
            # is auditable rather than implicit.
            rejected[tag][reason] = digest(path) if path.is_file() else "absent"

    inputs["data/manifest.json"] = digest(Path("data/manifest.json"))
    sources = {path.as_posix(): (digest(path) if path.is_file() else "absent")
               for path in SOURCE_FILES}

    manifest = {
        "schema": "phase6_r1_ablation_manifest_v1",
        "created_by": "Claude Opus 5",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "networks": list(tags),
        "targets": list(TARGETS),
        "set_ids": list(SET_IDS),
        "seeds": list(SEEDS),
        "radius": RADIUS,
        "n_splits": N_SPLITS,
        "estimator": {"kind": "RandomForestRegressor", "n_estimators": 120,
                      "min_samples_leaf": 2,
                      "log1p_wrapped_targets": ["betweenness"]},
        "objectives": {target: objective_for(target, 1)[0] for target in TARGETS},
        "node_counts": node_counts,
        "set_sizes": set_sizes,
        "input_sha256": inputs,
        "source_sha256": sources,
        "rejected_oof_reuse": {
            "reason": ("bare target|radius|richness|seed arrays with no manifest, "
                       "no selected-column list or hash, no cache input hash, no "
                       "target-objective id, no fold digest and no estimator hash; "
                       "root betweenness endpoint is the RAW objective while this "
                       "design reports rf_log1p"),
            "candidates": rejected,
        },
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
        },
    }
    manifest["run_id"] = canonical_sha256(manifest)
    return manifest


def validate_manifest(root: Path, manifest: dict) -> None:
    """Recompute every bound hash and the run_id before any cell is trusted."""
    stored = manifest.get("run_id")
    recomputed = canonical_sha256({k: v for k, v in manifest.items() if k != "run_id"})
    if stored != recomputed:
        raise R1RunError("manifest run_id does not match its own content")
    for name, expected in manifest["input_sha256"].items():
        path = Path(name)
        if not path.is_file():
            raise R1RunError(f"bound input {name} has disappeared")
        if digest(path) != expected:
            raise R1RunError(f"bound input {name} changed since the manifest was created")
    for name, expected in manifest["source_sha256"].items():
        path = Path(name)
        actual = digest(path) if path.is_file() else "absent"
        if actual != expected:
            raise R1RunError(f"bound source {name} changed since the manifest was created")


def load_or_create_manifest(root: Path, tags: tuple[str, ...]) -> dict:
    """Exclusive-create on first launch; strict revalidation on every resume."""
    path = root / "manifest.json"
    if path.is_file():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        validate_manifest(root, manifest)
        if tuple(manifest["networks"]) != tags:
            raise R1RunError(
                f"manifest networks {manifest['networks']} != requested {list(tags)}; "
                "this output path is authoritative and does not accept a subset"
            )
        return manifest
    manifest = build_manifest(root, tags)
    root.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: two runners racing here must not both win.
    temp = path.with_name(f"manifest.{uuid.uuid4().hex}.tmp")
    with temp.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=True, allow_nan=False))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    return manifest


# ---------------------------------------------------------------------------
# Cells
# ---------------------------------------------------------------------------

def run_cell(features: pd.DataFrame, targets: pd.DataFrame, columns: list[str],
             target: str, seed: int, rf_n_jobs: int) -> dict:
    """One five-fold out-of-fold fit, with its metrics and binding identities.

    `evaluate` is called against the ORIGINAL y even for the log1p objective:
    the transform is a conditioning choice for the regressor, not a change to
    the quantity being scored. Kendall tau is invariant to monotone transforms
    of the ground truth, so this is a better-conditioned objective rather than
    an easier test.
    """
    assert_no_leakage(columns)
    X = features[columns].to_numpy(np.float64)
    y = targets[target].to_numpy(np.float64)
    require_finite(f"X/{target}", X)
    require_finite(f"y/{target}", y)

    objective_id, factory = objective_for(target, rf_n_jobs)
    started = time.perf_counter()
    predictions = out_of_fold_predictions(X, y, n_splits=N_SPLITS, seed=seed,
                                          estimator=factory)
    elapsed = time.perf_counter() - started

    # experiment.evaluate RETURNS NaN for an undefined rank statistic rather
    # than refusing it, and a NaN reaching a cell record becomes a silently
    # dropped pair in the analyzer. Reject it here, at the boundary.
    require_finite(f"predictions/{target}", predictions)
    metrics = evaluate(y, predictions)
    require_finite(f"metrics/{target}", list(metrics.values()))

    return {
        "objective_id": objective_id,
        "rf_n_jobs": int(rf_n_jobs),
        "metrics": {name: float(value) for name, value in metrics.items()},
        "fit_seconds": float(elapsed),
        "n_rows": int(len(y)),
        "n_columns": len(columns),
        "columns_sha256": canonical_sha256(list(columns)),
        "target_sha256": hashlib.sha256(y.astype("<f8").tobytes()).hexdigest(),
        "fold_digest": fold_digest(len(y), seed),
        "predictions": predictions,
    }


def build_cell_record(manifest: dict, tag: str, target: str, set_id: str, seed: int,
                      outcome: dict) -> dict:
    record = {
        "schema": "phase6_r1_ablation_cell_v1",
        "run_id": manifest["run_id"],
        "network": tag, "target": target, "set_id": set_id, "seed": int(seed),
        "radius": RADIUS, "n_splits": N_SPLITS,
        "objective_id": outcome["objective_id"],
        "rf_n_jobs": outcome["rf_n_jobs"],
        "n_rows": outcome["n_rows"], "n_columns": outcome["n_columns"],
        "columns_sha256": outcome["columns_sha256"],
        "target_sha256": outcome["target_sha256"],
        "fold_digest": outcome["fold_digest"],
        "metrics": outcome["metrics"],
        "fit_seconds": outcome["fit_seconds"],
    }
    record["content_sha256"] = record_checksum(record)
    return record


def read_verified_cell(path: Path, run_id: str) -> dict:
    """Read one final cell and refuse it unless every binding value holds.

    A cell is skipped -- i.e. its fit is NOT repeated -- only on the strength of
    this function, so it validates rather than parses.
    """
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise R1RunError(f"{path.name}: not valid JSON") from exc
    if record.get("schema") != "phase6_r1_ablation_cell_v1":
        raise R1RunError(f"{path.name}: unexpected schema")
    if record.get("run_id") != run_id:
        raise R1RunError(f"{path.name}: run_id does not match the current manifest")
    if record.get("content_sha256") != record_checksum(record):
        raise R1RunError(f"{path.name}: record checksum does not match its content")
    key = (record.get("network"), record.get("target"),
           record.get("set_id"), record.get("seed"))
    if path.stem != cell_name(*key):
        raise R1RunError(f"{path.name}: filename does not match its own key {key}")
    if record.get("radius") != RADIUS or record.get("n_splits") != N_SPLITS:
        raise R1RunError(f"{path.name}: radius/fold count differs from the contract")
    require_finite(f"{path.name}/metrics", list(record["metrics"].values()))
    return record


# ---------------------------------------------------------------------------
# Pilot (addendum item 2) -- three fits, NOT part of the 800
# ---------------------------------------------------------------------------

def run_pilot(root: Path, manifest: dict, bundles: dict[str, dict]) -> dict:
    """Prove the bounded inner worker count changes nothing but the clock.

    The whole reason a bounded `n_jobs` exists here is that `make_rf` hardcodes
    `n_jobs=-1` and could not be asked for this comparison. Having introduced a
    private factory, the burden is to show it is the same model -- so this fits
    ONE representative cell at 1, 4 and 8 jobs and requires the predictions to
    agree, not merely the summary statistics.

    Memory is `tracemalloc` peak: Python-level allocation only, NOT process
    RSS. psutil is unavailable in this environment and installing into it is
    prohibited, so the weaker measurement is reported as what it is.
    """
    tag, target, set_id, seed = PILOT_CELL
    bundle = bundles[tag]
    columns = bundle["sets"][set_id]
    runs: dict[str, dict] = {}
    reference: np.ndarray | None = None

    for jobs in PILOT_JOBS:
        tracemalloc.start()
        before, _ = tracemalloc.get_traced_memory()
        outcome = run_cell(bundle["features"], bundle["targets"], columns,
                           target, seed, jobs)
        after, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        predictions = outcome.pop("predictions")
        if reference is None:
            reference = predictions
            abs_gap = rel_gap = tau_gap = 0.0
        else:
            abs_gap = float(np.max(np.abs(predictions - reference)))
            scale = float(np.max(np.abs(reference))) or 1.0
            rel_gap = abs_gap / scale
            tau_gap = abs(outcome["metrics"]["kendall_tau"]
                          - runs[str(PILOT_JOBS[0])]["metrics"]["kendall_tau"])
        runs[str(jobs)] = {
            "rf_n_jobs": jobs,
            "fit_seconds": outcome["fit_seconds"],
            "metrics": outcome["metrics"],
            "max_abs_prediction_gap": abs_gap,
            "max_rel_prediction_gap": rel_gap,
            "abs_tau_gap": tau_gap,
            "tracemalloc_before_bytes": int(before),
            "tracemalloc_after_bytes": int(after),
            "tracemalloc_peak_bytes": int(peak),
            "predictions_finite": True,
        }

    equivalent = all(
        run["max_abs_prediction_gap"] <= PILOT_ABS_TOL
        and run["max_rel_prediction_gap"] <= PILOT_REL_TOL
        and run["abs_tau_gap"] <= PILOT_TAU_TOL
        for run in runs.values()
    )
    valid = {jobs: runs[str(jobs)] for jobs in PILOT_JOBS}
    fastest = min(valid, key=lambda jobs: valid[jobs]["fit_seconds"])
    pilot = {
        "schema": "phase6_r1_ablation_pilot_v1",
        "run_id": manifest["run_id"],
        "cell": {"network": tag, "target": target, "set_id": set_id, "seed": seed},
        "jobs": list(PILOT_JOBS),
        "tolerances": {"abs": PILOT_ABS_TOL, "rel": PILOT_REL_TOL, "tau": PILOT_TAU_TOL},
        "runs": runs,
        "equivalent": bool(equivalent),
        "selected_rf_n_jobs": int(fastest),
        "memory_measure": "tracemalloc_python_allocation_not_process_rss",
        "extrapolated_800_cell_seconds": float(valid[fastest]["fit_seconds"] * 800),
        "note": ("pilot fits are separate from the 800 authoritative cells and "
                 "are never written as cell checkpoints"),
    }
    pilot["content_sha256"] = record_checksum(pilot)
    write_atomic_json(root / "pilot.json", pilot)
    if not equivalent:
        raise R1RunError("pilot worker counts are not numerically equivalent; refusing to run")
    return pilot


def load_or_create_pilot(root: Path, manifest: dict, bundles: dict[str, dict]) -> dict:
    path = root / "pilot.json"
    if not path.is_file():
        return run_pilot(root, manifest, bundles)
    pilot = json.loads(path.read_text(encoding="utf-8"))
    if pilot.get("run_id") != manifest["run_id"]:
        raise R1RunError("pilot.json belongs to a different run_id")
    if pilot.get("content_sha256") != record_checksum(pilot):
        raise R1RunError("pilot.json checksum does not match its content")
    if not pilot.get("equivalent"):
        raise R1RunError("pilot.json records a non-equivalent worker comparison")
    if sorted(pilot.get("runs", {})) != sorted(str(j) for j in PILOT_JOBS):
        raise R1RunError("pilot.json is incomplete")
    return pilot


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Phase 6 r=1 structural ablation (800 cells).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    # The grid is fixed by the brief. These flags exist so a mistaken value is
    # REJECTED loudly rather than quietly producing a subset under the
    # authoritative output path, which a later reader would mistake for a run.
    parser.add_argument("--tags", nargs="+", default=list(NETWORKS))
    parser.add_argument("--radius", type=int, default=RADIUS)
    parser.add_argument("--n-splits", type=int, default=N_SPLITS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--workers", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if tuple(args.tags) != NETWORKS:
        raise R1RunError(f"--tags must be exactly {list(NETWORKS)}")
    if args.radius != RADIUS:
        raise R1RunError(f"--radius must be {RADIUS}")
    if args.n_splits != N_SPLITS:
        raise R1RunError(f"--n-splits must be {N_SPLITS}")
    if tuple(args.seeds) != SEEDS:
        raise R1RunError(f"--seeds must be {list(SEEDS)}")
    if args.workers != 1:
        raise R1RunError("--workers must be 1; this runner is single-process by design")

    root: Path = args.out
    tags = tuple(args.tags)
    manifest = load_or_create_manifest(root, tags)
    print(f"run_id {manifest['run_id']}", flush=True)

    raws = raw_paths()
    bundles = {tag: load_bundle(tag, raws[tag]) for tag in tags}
    pilot = load_or_create_pilot(root, manifest, bundles)
    rf_n_jobs = int(pilot["selected_rf_n_jobs"])
    print(f"pilot selected rf_n_jobs={rf_n_jobs} "
          f"(equivalent across {list(PILOT_JOBS)})", flush=True)

    cells_dir = root / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    wanted = expected_keys(tags)

    # Resume reads ONLY final .json files. Uniquely-named .tmp files are left
    # untouched as interruption evidence and never counted.
    done: set[tuple[str, str, str, int]] = set()
    for path in sorted(cells_dir.glob("*.json")):
        record = read_verified_cell(path, manifest["run_id"])
        key = (record["network"], record["target"], record["set_id"], record["seed"])
        if key not in wanted:
            raise R1RunError(f"{path.name}: cell is outside the declared 800-cell grid")
        if key in done:
            raise R1RunError(f"{path.name}: duplicate cell key {key}")
        done.add(key)

    todo = sorted(wanted - done, key=lambda key: sort_key(*key))
    print(f"{len(done)} verified cells present, {len(todo)} to run", flush=True)

    for tag, target, set_id, seed in todo:
        bundle = bundles[tag]
        outcome = run_cell(bundle["features"], bundle["targets"],
                           bundle["sets"][set_id], target, seed, rf_n_jobs)
        outcome.pop("predictions")
        record = build_cell_record(manifest, tag, target, set_id, seed, outcome)
        write_atomic_json(cells_dir / f"{cell_name(tag, target, set_id, seed)}.json", record)
        done.add((tag, target, set_id, seed))
        print(f"{cell_name(tag, target, set_id, seed)} "
              f"tau={record['metrics'].get('kendall_tau', float('nan')):.6f} "
              f"({len(wanted) - len(done)} remaining)", flush=True)

    if done != wanted:
        raise R1RunError(f"incomplete corpus: {len(done)} of {len(wanted)} cells")
    print(f"complete: {len(done)} cells under {root}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (R1RunError, R1ContractError) as error:
        print(f"probe_r1_ablation.py: error: {error}", file=sys.stderr)
        sys.exit(2)

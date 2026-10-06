"""Resumable, graph-buffered CV follow-up for Phase 6.

This runner is deliberately separate from ``influence.experiment``: that module
owns the published shuffled-KFold protocol.  Here folds are graph-only seeded
BFS regions and each buffered result is a follow-up evaluand, not a replacement
for the historical random-CV sweep.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
import platform
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy
import scipy.sparse as sp
import sklearn
from scipy.stats import kendalltau
from sklearn.ensemble import RandomForestRegressor

import analyse
from influence.preprocessing import load_edgelist
from probe_structural_target_noise_refit import structural_features, validate_sweep


PROTOCOL = "phase6-buffer-v1"
SPLIT_VERSION = "bfs-fifo-sorted-neighbours-v1"
NETWORKS = ("ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined", "p2p-Gnutella08")
TARGETS = ("spread_mean", "spread_cv", "spread_resid", "betweenness")
RADII = (0, 1, 2, 3)
SEEDS = tuple(range(10))
FOLDS = 5
MIN_TRAIN_ROWS = 30
RESULTS = Path("results")
PREFLIGHT_PATH = RESULTS / "phase6_buffered_cv_preflight.json"
PROVENANCE_PATH = RESULTS / "phase6_buffered_cv_provenance.json"
ASSIGNMENT_ROOT = RESULTS / "phase6_buffered_cv_assignments"
CHECKPOINT_ROOT = RESULTS / "phase6_buffered_cv_checkpoints"
CHECKPOINT_POINTER = "current.json"
PILOT_PATH = RESULTS / "phase6_buffered_cv_pilot.json"
RESULTS_MANIFEST_PATH = RESULTS / "phase6_buffered_cv_results_manifest.json"
STRUCTURAL_MORAN_PROTOCOL = "phase6-structural-moran-v1"
MIN_AVAILABLE_MEMORY_BYTES = 512 * 1024 * 1024
# Declared before observing pilot timings.  The relative component scales with
# target magnitude (notably log1p-restored betweenness); tau is rank based.
PILOT_ABSOLUTE_TOLERANCE = 1e-10
PILOT_RELATIVE_TOLERANCE = 1e-12
PILOT_KENDALL_TOLERANCE = 1e-12

READY = "ready"
COMPLETE = "complete"
INFEASIBLE = "infeasible_lt30"
SOURCE_INFEASIBLE = "source_infeasible"
UNRESOLVED = "unresolved_seedwise_buffer"


@dataclass(frozen=True)
class FoldPlan:
    """One logical arm's fixed assignment for one graph region."""

    logical_arm: str
    canonical_arm: str
    status: str
    buffer: int | None
    test_ids: np.ndarray
    train_ids: np.ndarray
    excluded_ids: np.ndarray
    alias_of: str | None = None
    failure_reason: str | None = None
    rng_seed: int | None = None


def json_native(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return value.as_posix()
    raise TypeError(f"cannot JSON encode {type(value).__name__}")


def _canonical_digest_value(value: Any) -> Any:
    """Make JSON and CSV representations agree on missing scalar values."""
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, np.ndarray):
        return [_canonical_digest_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _canonical_digest_value(value.item())
    if isinstance(value, dict):
        return {str(key): _canonical_digest_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_digest_value(item) for item in value]
    # CSV writes None as an empty field and pandas reads it as NaN.  A digest
    # must authenticate scientific content, not that formatting distinction.
    if value is None or value is pd.NA or value == "" or (isinstance(value, float) and np.isnan(value)):
        return None
    # A nullable integer CSV column is parsed as float (for example 1 -> 1.0).
    # Its numeric identity must survive the round trip without weakening a
    # genuinely high-precision statistic such as Kendall tau.
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def stable_digest(value: Any) -> str:
    raw = json.dumps(_canonical_digest_value(value), sort_keys=True, separators=(",", ":"),
                     default=json_native).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def available_memory_bytes() -> int | None:
    """Read Windows available physical memory without adding a package dependency."""
    if os.name != "nt":
        return None
    import ctypes
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    state = MEMORYSTATUSEX()
    state.dwLength = ctypes.sizeof(state)
    return int(state.ullAvailPhys) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)) else None


def select_pilot_job(rows: list[dict[str, Any]]) -> int:
    """Pre-registered worker selection: fastest numerically equivalent bounded run."""
    valid = [row for row in rows if bool(row.get("valid"))]
    if not valid:
        raise RuntimeError("no bounded worker setting passed the pilot validity guard")
    return int(min(valid, key=lambda row: (float(row["elapsed_seconds"]), int(row["rf_jobs"])))["rf_jobs"])


def pilot_equivalence(reference_prediction: np.ndarray, prediction: np.ndarray,
                      reference_tau: float, tau: float) -> dict[str, Any]:
    """Measure the predeclared worker-count numerical-equivalence contract."""
    difference = np.abs(np.asarray(prediction, dtype=np.float64) -
                        np.asarray(reference_prediction, dtype=np.float64))
    scale = max(1.0, float(np.max(np.abs(reference_prediction))))
    max_abs = float(np.max(difference))
    max_rel = float(max_abs / scale)
    tau_difference = float(abs(tau - reference_tau)) if np.isfinite(tau) and np.isfinite(reference_tau) else np.inf
    return {"max_abs_difference_from_jobs1": max_abs,
            "max_relative_difference_from_jobs1": max_rel,
            "kendall_difference_from_jobs1": tau_difference,
            "numerically_equivalent_to_jobs1": bool(max_abs <= PILOT_ABSOLUTE_TOLERANCE
                + PILOT_RELATIVE_TOLERANCE * scale and tau_difference <= PILOT_KENDALL_TOLERANCE)}


def atomic_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                     dir=path.parent, suffix=".tmp") as stream:
        temp = Path(stream.name)
        json.dump(value, stream, indent=2, sort_keys=True, default=json_native)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def atomic_npz(arrays: dict[str, np.ndarray], path: Path) -> None:
    """Replace an NPZ only after its complete temporary archive exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent,
                                     suffix=".npz") as stream:
        temp = Path(stream.name)
    try:
        np.savez_compressed(temp, **arrays)
        with temp.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def atomic_csv(rows: list[dict[str, Any]], path: Path) -> None:
    """Atomically replace a CSV checkpoint/report with a fully written frame."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False,
                                     dir=path.parent, suffix=".tmp") as stream:
        temp = Path(stream.name)
        pd.DataFrame(rows).to_csv(stream, index=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def compact_fold_row(row: dict[str, Any]) -> dict[str, Any]:
    """Remove ID arrays from final exports; archives remain the authoritative store."""
    return {key: value for key, value in row.items()
            if key not in {"test_ids", "train_ids", "excluded_ids"}}


def _stream_csv_rows(rows: Any, path: Path) -> str:
    """Atomically write a row iterator without aggregating corpus-wide fold rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False,
                                     dir=path.parent, suffix=".tmp") as stream:
        temp = Path(stream.name)
        writer: csv.DictWriter | None = None
        for row in rows:
            if writer is None:
                writer = csv.DictWriter(stream, fieldnames=list(row), extrasaction="raise")
                writer.writeheader()
            writer.writerow(row)
        if writer is None:
            raise RuntimeError(f"refusing to publish an empty required CSV: {path}")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    return digest_file(path)


def bfs_order(nbrs: list[np.ndarray], seed: int) -> tuple[np.ndarray, int]:
    """Return the exact seed-defined FIFO BFS permutation for a connected LCC."""
    n = len(nbrs)
    if n == 0:
        raise ValueError("cannot split an empty graph")
    root = int(np.random.default_rng(seed).integers(n))
    order = np.empty(n, dtype=np.int64)
    seen = np.zeros(n, dtype=bool)
    queue = np.empty(n, dtype=np.int64)
    head = tail = 0
    queue[tail] = root
    tail += 1
    seen[root] = True  # enqueue-time marking prevents duplicate FIFO entries.
    while head < tail:
        node = int(queue[head])
        head += 1
        order[head - 1] = node
        # CSR rows are normally sorted, but sorting here makes the construction
        # independent of an accidental adjacency-order change.
        for neighbour in np.sort(nbrs[node]):
            neighbour = int(neighbour)
            if not seen[neighbour]:
                seen[neighbour] = True
                queue[tail] = neighbour
                tail += 1
    if tail != n or not np.array_equal(np.sort(order), np.arange(n)):
        raise ValueError("BFS did not cover the validated connected graph exactly once")
    return order, root


def region_folds(nbrs: list[np.ndarray], seed: int) -> list[np.ndarray]:
    order, _ = bfs_order(nbrs, seed)
    folds = [part.astype(np.int64, copy=False) for part in np.array_split(order, FOLDS)]
    if any(len(part) == 0 for part in folds):
        raise ValueError(f"{len(order)} nodes cannot form {FOLDS} nonempty regions")
    if not np.array_equal(np.sort(np.concatenate(folds)), np.arange(len(order))):
        raise AssertionError("region folds do not cover every node exactly once")
    return folds


def exclusion_mask(adj: sp.csr_matrix, test_ids: np.ndarray, buffer: int) -> np.ndarray:
    """Mark nodes at full-graph distance at most ``buffer`` from any test node."""
    if buffer < 0:
        raise ValueError("buffer must be nonnegative")
    n = adj.shape[0]
    test_ids = np.asarray(test_ids, dtype=np.int64)
    if test_ids.ndim != 1 or not len(test_ids) or test_ids.min() < 0 or test_ids.max() >= n:
        raise ValueError("test IDs must be a nonempty in-range vector")
    seen = np.zeros(n, dtype=bool)
    frontier = np.unique(test_ids)
    seen[frontier] = True
    for _ in range(buffer):
        neighbours = np.concatenate([adj.indices[adj.indptr[v]:adj.indptr[v + 1]] for v in frontier])
        frontier = np.unique(neighbours[~seen[neighbours]]) if len(neighbours) else np.empty(0, dtype=np.int64)
        if not len(frontier):
            break
        seen[frontier] = True
    return seen


def control_seed(network: str, target: str, radius: int, seed: int, fold: int, arm: str) -> int:
    material = f"{network}|{target}|{radius}|{seed}|{fold}|{arm}|{PROTOCOL}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "little", signed=False)


def _buffer_plan(arm: str, candidates: np.ndarray, excluded: np.ndarray, test_ids: np.ndarray,
                 buffer: int) -> FoldPlan:
    train_ids = candidates[~excluded[candidates]]
    removed = candidates[excluded[candidates]]
    status = READY if len(train_ids) >= MIN_TRAIN_ROWS else INFEASIBLE
    return FoldPlan(arm, arm, status, buffer, test_ids, train_ids, removed,
                    failure_reason=None if status == READY else f"{len(train_ids)} retained rows < {MIN_TRAIN_ROWS}")


def _control_plan(control_arm: str, source: FoldPlan, network: str, target: str,
                  radius: int, seed: int, fold: int, candidates: np.ndarray) -> FoldPlan:
    if source.status != READY:
        return FoldPlan(control_arm, control_arm, SOURCE_INFEASIBLE, source.buffer,
                        source.test_ids, np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64),
                        failure_reason=f"{source.logical_arm} is {source.status}")
    rng_value = control_seed(network, target, radius, seed, fold, control_arm)
    chosen = np.sort(np.random.default_rng(rng_value).choice(candidates, size=len(source.train_ids), replace=False))
    if len(chosen) != len(source.train_ids):
        raise AssertionError("control sample size differs from buffered training size")
    return FoldPlan(control_arm, control_arm, READY, source.buffer, source.test_ids,
                    chosen.astype(np.int64), np.empty(0, dtype=np.int64), rng_seed=rng_value)


def _alias(plan: FoldPlan, logical_arm: str, alias_of: str) -> FoldPlan:
    return replace(plan, logical_arm=logical_arm, alias_of=alias_of)


def build_fold_plans(network: str, target: str, radius: int, seed: int, fold: int,
                     adj: sp.csr_matrix, test_ids: np.ndarray,
                     measured_buffer: int | None) -> list[FoldPlan]:
    """Build all logical arms without fitting, including explicit alias/status rows."""
    n = adj.shape[0]
    test_ids = np.asarray(test_ids, dtype=np.int64)
    candidates = np.setdiff1d(np.arange(n, dtype=np.int64), test_ids, assume_unique=False)
    region_status = READY if len(candidates) >= MIN_TRAIN_ROWS else INFEASIBLE
    region = FoldPlan("region", "region", region_status, 0, test_ids, candidates,
                      np.empty(0, dtype=np.int64),
                      failure_reason=None if region_status == READY else f"{len(candidates)} retained rows < {MIN_TRAIN_ROWS}")
    b1 = _buffer_plan("buffer_b1", candidates, exclusion_mask(adj, test_ids, 1), test_ids, 1)
    c1 = _control_plan("control_b1", b1, network, target, radius, seed, fold, candidates)
    plans = [region, b1, c1]
    if measured_buffer is None:
        empty = np.empty(0, dtype=np.int64)
        plans.extend([
            FoldPlan("buffer_measured", "buffer_measured", UNRESOLVED, None, test_ids, empty, empty,
                     failure_reason="at least one seed lacked a testable non-significant Moran lag"),
            FoldPlan("control_measured", "control_measured", UNRESOLVED, None, test_ids, empty, empty,
                     failure_reason="at least one seed lacked a testable non-significant Moran lag"),
        ])
    elif measured_buffer == 1:
        plans.extend([_alias(b1, "buffer_measured", "buffer_b1"),
                      _alias(c1, "control_measured", "control_b1")])
    else:
        measured = _buffer_plan("buffer_measured", candidates,
                                exclusion_mask(adj, test_ids, measured_buffer), test_ids, measured_buffer)
        control = _control_plan("control_measured", measured, network, target, radius,
                                seed, fold, candidates)
        plans.extend([measured, control])
    for plan in plans:
        if np.intersect1d(plan.test_ids, plan.train_ids).size:
            raise AssertionError("a test label entered its arm's training IDs")
        if plan.logical_arm.startswith("buffer_") and plan.status == READY:
            mask = exclusion_mask(adj, plan.test_ids, int(plan.buffer))
            if mask[plan.train_ids].any():
                raise AssertionError("a buffered training ID is not farther than its buffer")
    return plans


def fit_target(y: np.ndarray, target: str) -> np.ndarray:
    y = np.asarray(y, dtype=np.float64)
    return np.log1p(y) if target == "betweenness" else y


def restore_prediction(prediction: np.ndarray, target: str) -> np.ndarray:
    prediction = np.asarray(prediction, dtype=np.float64)
    return np.expm1(prediction) if target == "betweenness" else prediction


def fit_region_fold(X: np.ndarray, y: np.ndarray, train_ids: np.ndarray, test_ids: np.ndarray,
                    model_seed: int, rf_jobs: int, target: str) -> np.ndarray:
    if len(train_ids) < MIN_TRAIN_ROWS:
        raise ValueError(f"refusing fit with fewer than {MIN_TRAIN_ROWS} training rows")
    model = RandomForestRegressor(n_estimators=120, min_samples_leaf=2,
                                  random_state=model_seed, n_jobs=rf_jobs)
    model.fit(X[train_ids], fit_target(y[train_ids], target))
    return restore_prediction(model.predict(X[test_ids]), target)


def assignment_key(network: str, target: str, radius: int, seed: int, fold: int,
                   arm: str, field: str) -> str:
    return f"{network}|{target}|r{radius}|s{seed}|f{fold}|{arm}|{field}"


def assignment_path(key: str) -> Path:
    """A compact, collision-resistant file name for one immutable cell plan."""
    return ASSIGNMENT_ROOT / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.npz"


def plan_row(network: str, target: str, radius: int, seed: int, fold: int,
             plan: FoldPlan) -> dict[str, Any]:
    row = {"network": network, "target": target, "radius": radius, "seed": seed,
           "fold": fold, "logical_arm": plan.logical_arm,
           "canonical_arm": plan.canonical_arm, "alias_of": plan.alias_of,
           "status": plan.status, "buffer": plan.buffer, "n_test": len(plan.test_ids),
           "n_train": len(plan.train_ids), "n_excluded": len(plan.excluded_ids),
           "failure_reason": plan.failure_reason, "control_rng_seed": plan.rng_seed}
    # This binds the logical protocol fields; the three explicit ID digests are
    # appended when the immutable assignment archive is written.
    row["assignment_sha256"] = stable_digest({k: row[k] for k in row if k != "failure_reason"})
    return row


def write_checkpoint(root: Path, provenance: dict[str, Any], state: dict[str, Any]) -> None:
    """Commit one checkpoint generation, publishing only its verified pointer."""
    root.mkdir(parents=True, exist_ok=True)
    generation = f"generation-{time.time_ns()}"
    directory = root / generation
    directory.mkdir()
    files = {"fold_rows.json": state.get("fold_rows", []),
             "cell_rows.json": state.get("cell_rows", [])}
    for name, value in files.items():
        atomic_json(value, directory / name)
    atomic_npz({key: np.asarray(value) for key, value in state.get("oof", {}).items()},
               directory / "oof.npz")
    # Configuration identifies the protocol.  Identity/preflight digests bind
    # resume to the immutable sources and assignment plan, not merely settings.
    manifest = {"protocol": PROTOCOL,
                "configuration_sha256": provenance["configuration_sha256"],
                "identity_sha256": provenance.get("identity_sha256"),
                "preflight_sha256": provenance.get("preflight_sha256"),
                "execution_identity_sha256": provenance.get("execution_identity_sha256"),
                "files": {name: digest_file(directory / name)
                          for name in (*files, "oof.npz")}}
    atomic_json(manifest, directory / "manifest.json")
    atomic_json({"generation": generation, "sha256": digest_file(directory / "manifest.json")},
                root / CHECKPOINT_POINTER)


def load_checkpoint(root: Path, provenance: dict[str, Any]) -> dict[str, Any]:
    pointer_path = root / CHECKPOINT_POINTER
    if not pointer_path.exists():
        return {"fold_rows": [], "cell_rows": [], "oof": {}}
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if set(pointer) != {"generation", "sha256"}:
        raise RuntimeError("checkpoint pointer is malformed")
    directory = root / str(pointer["generation"])
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file() or digest_file(manifest_path) != pointer["sha256"]:
        raise RuntimeError("checkpoint pointer does not reference an intact generation")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_identity = {"protocol": PROTOCOL,
                         "configuration_sha256": provenance["configuration_sha256"],
                         "identity_sha256": provenance.get("identity_sha256"),
                         "preflight_sha256": provenance.get("preflight_sha256"),
                         "execution_identity_sha256": provenance.get("execution_identity_sha256")}
    if any(manifest.get(field) != value for field, value in expected_identity.items()):
        raise RuntimeError("checkpoint protocol or preflight/input provenance differs")
    if set(manifest.get("files", {})) != {"fold_rows.json", "cell_rows.json", "oof.npz"}:
        raise RuntimeError("checkpoint generation has an unexpected artifact key set")
    for name, expected in manifest["files"].items():
        path = directory / name
        if not path.is_file() or digest_file(path) != expected:
            raise RuntimeError(f"checkpoint artifact {name} is missing or changed")
    with np.load(directory / "oof.npz") as archive:
        oof = {name: archive[name] for name in archive.files}
    return {"fold_rows": json.loads((directory / "fold_rows.json").read_text(encoding="utf-8")),
            "cell_rows": json.loads((directory / "cell_rows.json").read_text(encoding="utf-8")),
            "oof": oof}

def _manifest_paths() -> dict[str, Path]:
    raw = json.loads(Path("data/manifest.json").read_text(encoding="utf-8"))
    return {entry["name"]: Path(entry["path"].replace("\\", os.sep)) for entry in raw}


def _input_paths(network: str, raw_path: Path) -> list[Path]:
    return [raw_path, Path(f"cache_features_{network}.csv"), Path(f"cache_targets_{network}.csv"),
            Path(f"cache_registry_{network}.csv"), Path(f"cache_meta_{network}.json"),
            Path(f"sweep_{network}.csv")]


def validate_structural_moran(path: Path, provenance_path: Path) -> pd.DataFrame:
    """Authenticate the structural Moran prerequisite before any split is built.

    A C6-shaped CSV alone is deliberately insufficient: the sidecar binds the
    lag table to structural OOF inputs and their current source hashes.
    """
    if not path.is_file() or not provenance_path.is_file():
        raise ValueError("structural Moran CSV and provenance sidecar must both exist")
    sidecar = json.loads(provenance_path.read_text(encoding="utf-8"))
    config = sidecar.get("configuration", {})
    if sidecar.get("protocol") != STRUCTURAL_MORAN_PROTOCOL:
        raise ValueError("Moran sidecar is not the structural buffered-CV protocol")
    import analyse_structural_moran_correlogram as structural_moran
    # Keys normalised to root-relative before comparison (P2-02 shim, 2026-09-11):
    # the sidecar shipped on 2026-09-10 carries absolute keys and must not be
    # rewritten; see structural_moran.normalise_source_keys.
    recorded = structural_moran.normalise_source_keys(sidecar.get("producer_source_sha256", {}))
    if recorded != structural_moran.producer_source_hashes():
        raise ValueError("Moran sidecar producer-source hashes differ")
    expected_config = {"tier": analyse.FULL, "targets": list(TARGETS), "radii": list(RADII),
                       "seeds": list(SEEDS), "lags": 7, "blas_threads": 4,
                       "null_reference_seed": 0,
                       "p_perm_interpretation": "permutations use the fit-seed-0 residual per target/radius and provide a shared seed-0-reference tail area for every fit seed",
                       "perms": 199, "batch": 512, "random_seed": 0}
    for name, expected in expected_config.items():
        if config.get(name) != expected:
            raise ValueError(f"Moran sidecar {name} differs from structural protocol")
    if sidecar.get("output_sha256") != digest_file(path):
        raise ValueError("Moran CSV digest differs from its sidecar")
    frame = pd.read_csv(path)
    required = {"network", "target", "radius", "seed", "tier", "residual", "lag", "testable", "sig",
                "source_oof_path", "graph_sha256", "cache_features_sha256", "cache_targets_sha256",
                "cache_registry_sha256", "oof_sha256", "null_reference_seed", "p_perm_interpretation"}
    if missing := required.difference(frame.columns):
        raise ValueError(f"structural Moran CSV missing {sorted(missing)}")
    if set(frame.tier) != {analyse.FULL} or set(frame.residual) != {"rank"}:
        raise ValueError("Moran CSV is not rank-residual structural-tier output")
    if set(frame.null_reference_seed) != {0} or frame.p_perm_interpretation.nunique(dropna=False) != 1:
        raise ValueError("Moran CSV does not disclose the shared seed-0 null reference")
    expected_rows = {(network, target, radius, seed, lag) for network in NETWORKS for target in TARGETS
                     for radius in RADII for seed in SEEDS for lag in range(1, 8)}
    observed_rows = set(map(tuple, frame[["network", "target", "radius", "seed", "lag"]]
                                .itertuples(index=False, name=None)))
    if observed_rows != expected_rows or len(frame) != len(expected_rows):
        raise ValueError("Moran CSV does not have the exact structural lag key set")
    manifest = _manifest_paths()
    source_hashes = sidecar.get("input_sha256", {})
    for network in NETWORKS:
        reported = source_hashes.get(network)
        if not isinstance(reported, dict):
            raise ValueError(f"Moran sidecar lacks per-network hashes for {network}")
        expected_files = {
            "graph_sha256": manifest[network],
            "cache_features_sha256": Path(f"cache_features_{network}.csv"),
            "cache_targets_sha256": Path(f"cache_targets_{network}.csv"),
            "cache_registry_sha256": Path(f"cache_registry_{network}.csv"),
        }
        for field, file_path in expected_files.items():
            if reported.get(field) != digest_file(Path(file_path)):
                raise ValueError(f"Moran sidecar {field} is stale for {network}")
            if set(frame.loc[frame.network == network, field]) != {reported[field]}:
                raise ValueError(f"Moran CSV {field} disagrees with its sidecar for {network}")
        for target in TARGETS:
            oof_path = (Path("estimators") / f"cache_oof_{network}__rf_log1p.npz"
                        if target == "betweenness" else Path(f"cache_oof_{network}.npz"))
            oof_key = f"oof:{oof_path.as_posix()}"
            oof_hash = digest_file(oof_path)
            if reported.get(oof_key) != oof_hash:
                raise ValueError(f"Moran sidecar OOF source is stale for {network}/{target}")
            subset = frame[(frame.network == network) & (frame.target == target)]
            if set(subset.source_oof_path) != {oof_path.as_posix()} or set(subset.oof_sha256) != {oof_hash}:
                raise ValueError(f"Moran CSV OOF source differs for {network}/{target}")
    return frame


def _measured_buffer_map(path: Path, provenance_path: Path) -> dict[tuple[str, str, int], int | None]:
    """Read an authenticated structural prerequisite, never a dynamic C6 lookalike."""
    import analyse_structural_moran_correlogram as structural_moran
    rows = validate_structural_moran(path, provenance_path).to_dict("records")
    records = structural_moran.measured_buffers(rows)
    result = {(row["network"], row["target"], int(row["radius"])):
            (None if row["status"] != "resolved" else int(row["measured_buffer"]))
            for row in records}
    expected = {(network, target, radius) for network in NETWORKS for target in TARGETS for radius in RADII}
    if set(result) != expected:
        missing = sorted(expected.difference(result))
        extra = sorted(set(result).difference(expected))
        raise ValueError(f"structural Moran summary differs from buffered protocol; missing={missing}, extra={extra}")
    return result


def _validate_alignment(network: str, net, features: pd.DataFrame, targets: pd.DataFrame,
                        registry: pd.DataFrame) -> None:
    n = net.n
    for name, table in (("features", features), ("targets", targets)):
        if len(table) != n or "node" not in table or not np.array_equal(table.node.to_numpy(), np.arange(n)):
            raise ValueError(f"{network}: {name} rows/node order do not match rebuilt graph")
    if "original_id" not in features or not np.array_equal(features.original_id.to_numpy(), net.original_ids):
        raise ValueError(f"{network}: cached original IDs disagree with rebuilt graph")
    needed = {"feature", "hop", "tier"}
    if missing := needed.difference(registry.columns):
        raise ValueError(f"{network}: registry missing {sorted(missing)}")
    if registry.feature.duplicated().any():
        raise ValueError(f"{network}: registry repeats feature names")
    if missing := set(TARGETS).difference(targets.columns):
        raise ValueError(f"{network}: target cache missing {sorted(missing)}")


def preflight(moran_path: Path, moran_provenance_path: Path, *, write: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    """Make all split/control decisions with zero model fits."""
    if not moran_path.is_file():
        raise FileNotFoundError(f"structural Moran prerequisite missing: {moran_path}")
    buffer_map = _measured_buffer_map(moran_path, moran_provenance_path)
    manifest = _manifest_paths()
    hashes: dict[str, str] = {"data/manifest.json": digest_file(Path("data/manifest.json")),
                               moran_path.as_posix(): digest_file(moran_path),
                               moran_provenance_path.as_posix(): digest_file(moran_provenance_path)}
    semantic = [Path(__file__), Path("analyse.py"), Path("analyse_moran_correlogram.py"),
                Path("analyse_structural_moran_correlogram.py"), Path("influence/experiment.py"),
                Path("influence/preprocessing.py"), Path("probe_structural_target_noise_refit.py")]
    for source in semantic:
        if not source.is_file():
            raise FileNotFoundError(source)
        # Root-relative key (P2-02, 2026-09-11): Path(__file__) used to be
        # recorded absolute, which pinned the artifact to one checkout.
        import analyse_structural_moran_correlogram as structural_moran
        hashes[structural_moran.relative_source_key(source)] = digest_file(source)
    all_rows: list[dict[str, Any]] = []
    assignment_files: dict[str, dict[str, str]] = {}
    feature_counts: dict[str, dict[str, int]] = {}
    for network in NETWORKS:
        if network not in manifest:
            raise ValueError(f"{network}: absent from manifest")
        paths = _input_paths(network, manifest[network])
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(path)
            hashes[path.as_posix()] = digest_file(path)
        net = load_edgelist(manifest[network], name=network)
        features, targets, registry = (pd.read_csv(paths[1]), pd.read_csv(paths[2]), pd.read_csv(paths[3]))
        _validate_alignment(network, net, features, targets, registry)
        sweep_counts = validate_sweep(paths[5])
        feature_counts[network] = {}
        for radius in RADII:
            cols = structural_features(registry, features, radius)
            if len(cols) != sweep_counts[radius]:
                raise ValueError(f"{network}/r{radius}: structural feature count differs from sweep")
            feature_counts[network][str(radius)] = len(cols)
        for target in TARGETS:
            for radius in RADII:
                measured = buffer_map[(network, target, radius)]
                for seed in SEEDS:
                    key = cell_key(network, target, radius, seed)
                    arrays: dict[str, np.ndarray] = {}
                    rows: list[dict[str, Any]] = []
                    for fold, test_ids in enumerate(region_folds(net.nbrs, seed)):
                        plans = build_fold_plans(network, target, radius, seed, fold, net.adj, test_ids, measured)
                        for plan in plans:
                            rows.append(plan_row(network, target, radius, seed, fold, plan))
                            for field, value in (("test_ids", plan.test_ids), ("train_ids", plan.train_ids),
                                                 ("excluded_ids", plan.excluded_ids)):
                                arrays[assignment_key(network, target, radius, seed, fold,
                                                      plan.logical_arm, field)] = value
                    path = assignment_path(key)
                    if write:
                        atomic_npz(arrays, path)
                    # The archive is immutable once hashed; a later checkpoint
                    # refers to this digest instead of retaining its arrays.
                    archive_hash = digest_file(path) if write else stable_digest(arrays)
                    assignment_files[key] = {"path": path.as_posix(), "sha256": archive_hash}
                    for row in rows:
                        row["assignment_file"] = path.as_posix()
                        row["assignment_file_sha256"] = archive_hash
                        for field in ("test_ids", "train_ids", "excluded_ids"):
                            values = arrays[assignment_key(network, target, radius, seed, int(row["fold"]),
                                                           row["logical_arm"], field)]
                            row[f"{field}_sha256"] = stable_digest(values)
                        row["preflight_row_sha256"] = stable_digest(row)
                    all_rows.extend(rows)
        del features, targets, registry, net
        gc.collect()
    config = {"protocol": PROTOCOL, "split_version": SPLIT_VERSION, "networks": NETWORKS,
              "targets": TARGETS, "radii": RADII, "seeds": SEEDS, "folds": FOLDS,
              "tier": analyse.FULL, "minimum_train_rows": MIN_TRAIN_ROWS,
              "outer_workers": 1, "moran_path": moran_path.as_posix(),
              "moran_provenance_path": moran_provenance_path.as_posix()}
    canonical = {(r["network"], r["target"], r["radius"], r["seed"], r["fold"], r["canonical_arm"])
                 for r in all_rows if r["status"] == READY and r["alias_of"] is None}
    logical_keys = sorted("|".join(map(str, (r["network"], r["target"], r["radius"], r["seed"], r["fold"],
                                               r["logical_arm"]))) for r in all_rows)
    preflight_doc = {"configuration": config, "configuration_sha256": stable_digest(config),
                     "feature_counts": feature_counts, "fold_rows": all_rows,
                     "canonical_fit_count": len(canonical), "logical_fold_count": len(all_rows),
                     "expected_logical_fold_keys": logical_keys}
    preflight_doc["assignment_files"] = assignment_files
    preflight_doc["expected_logical_cell_keys"] = sorted({"|".join(map(str, (r["network"], r["target"], r["radius"], r["seed"], r["logical_arm"]))) for r in all_rows})
    preflight_doc["identity_sha256"] = stable_digest({"configuration": config, "input_sha256": hashes,
                                                       "assignment_index_sha256": stable_digest(assignment_files),
                                                       "expected_logical_fold_keys": logical_keys,
                                                       "expected_canonical_keys": sorted("|".join(map(str, key)) for key in canonical)})
    provenance = {"protocol": PROTOCOL, "configuration": config,
                  "configuration_sha256": preflight_doc["configuration_sha256"],
                  "input_sha256": hashes, "runtime_versions": {
                      "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                      "scipy": scipy.__version__, "scikit_learn": sklearn.__version__},
                  "assignment_index_sha256": stable_digest(assignment_files),
                  "expected_logical_fold_keys": logical_keys,
                  "expected_canonical_keys": sorted("|".join(map(str, key)) for key in canonical),
                  "expected_logical_cell_keys": preflight_doc["expected_logical_cell_keys"],
                  "identity_sha256": preflight_doc["identity_sha256"]}
    provenance["preflight_sha256"] = stable_digest(preflight_doc)
    if write:
        atomic_json(preflight_doc, PREFLIGHT_PATH)
        atomic_json(provenance, PROVENANCE_PATH)
    return preflight_doc, provenance


def _load_preflight() -> tuple[dict[str, Any], dict[str, Any]]:
    if PREFLIGHT_PATH.exists() != PROVENANCE_PATH.exists():
        raise RuntimeError("execution requires preflight and provenance together")
    preflight_doc = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    if preflight_doc.get("configuration_sha256") != provenance.get("configuration_sha256"):
        raise RuntimeError("preflight and provenance configuration hashes differ")
    if preflight_doc.get("identity_sha256") != provenance.get("identity_sha256"):
        raise RuntimeError("preflight and provenance scientific/input identities differ")
    if stable_digest(preflight_doc) != provenance.get("preflight_sha256"):
        raise RuntimeError("preflight document differs from its recorded provenance digest")
    current_hashes = {}
    import analyse_structural_moran_correlogram as structural_moran
    # P2-02 shim (2026-09-11): absolute keys recorded by the 2026-09-10 run are
    # matched by root-relative suffix; the recorded hashes themselves are never
    # altered, so identity_sha256 (which folds them in) stays verifiable.
    for stored_path, expected in structural_moran.normalise_source_keys(
            provenance.get("input_sha256", {})).items():
        path = Path(stored_path)
        if not path.is_file() or (actual := digest_file(path)) != expected:
            raise RuntimeError(f"preflight input/source hash differs for {stored_path}")
        current_hashes[stored_path] = actual
    if not current_hashes:
        raise RuntimeError("provenance lacks required input/source hashes")
    assignment_files = preflight_doc.get("assignment_files", {})
    if stable_digest(assignment_files) != provenance.get("assignment_index_sha256"):
        raise RuntimeError("assignment index differs from recorded provenance")
    for key, record in assignment_files.items():
        path = Path(record["path"])
        if not path.is_file() or digest_file(path) != record["sha256"]:
            raise RuntimeError(f"immutable assignment archive differs for {key}")
    expected_rows = FOLDS * len(NETWORKS) * len(TARGETS) * len(RADII) * len(SEEDS) * 5
    if len(preflight_doc.get("fold_rows", [])) != expected_rows:
        raise RuntimeError("preflight logical fold-key set is incomplete")
    if preflight_doc.get("expected_logical_fold_keys") != provenance.get("expected_logical_fold_keys"):
        raise RuntimeError("preflight expected logical key set differs from provenance")
    if preflight_doc.get("expected_logical_cell_keys") != provenance.get("expected_logical_cell_keys"):
        raise RuntimeError("preflight expected cell key set differs from provenance")
    return preflight_doc, provenance



def benchmark(preflight_doc: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    """Time one frozen canonical fold at each allowed inner-worker count.

    Pilot fits intentionally never create a cell checkpoint, so an interrupted or
    rejected benchmark cannot be mistaken for an authoritative result.
    """
    candidates = [row for row in preflight_doc["fold_rows"]
                  if row["status"] == READY and row["alias_of"] is None]
    if not candidates:
        raise RuntimeError("preflight has no feasible canonical fold for the worker pilot")
    row = candidates[0]
    network, target = row["network"], row["target"]
    radius, seed, fold = int(row["radius"]), int(row["seed"]), int(row["fold"])
    features = pd.read_csv(f"cache_features_{network}.csv")
    targets = pd.read_csv(f"cache_targets_{network}.csv")
    registry = pd.read_csv(f"cache_registry_{network}.csv")
    X = features[structural_features(registry, features, radius)].to_numpy(dtype=np.float64)
    y = targets[target].to_numpy(dtype=np.float64)
    assignments = _load_cell_assignments(preflight_doc, cell_key(network, target, radius, seed))
    train_ids = _assignment(assignments, network, target, radius, seed, fold,
                            row["logical_arm"], "train_ids")
    test_ids = _assignment(assignments, network, target, radius, seed, fold,
                           row["logical_arm"], "test_ids")
    results: list[dict[str, Any]] = []
    reference_prediction: np.ndarray | None = None
    reference_tau: float | None = None
    for rf_jobs in (1, 4, 8):
        before = available_memory_bytes()
        started = time.perf_counter()
        prediction = fit_region_fold(X, y, train_ids, test_ids, seed, rf_jobs, target)
        elapsed = time.perf_counter() - started
        after = available_memory_bytes()
        finite = bool(np.isfinite(prediction).all())
        tau = float(kendalltau(y[test_ids], prediction).statistic)
        if reference_prediction is None:
            reference_prediction = prediction.copy()
            reference_tau = tau
            max_abs_diff, max_rel_diff, tau_difference, equivalent = 0.0, 0.0, 0.0, bool(np.isfinite(tau))
        else:
            equivalence = pilot_equivalence(reference_prediction, prediction, reference_tau, tau)
            max_abs_diff = equivalence["max_abs_difference_from_jobs1"]
            max_rel_diff = equivalence["max_relative_difference_from_jobs1"]
            tau_difference = equivalence["kendall_difference_from_jobs1"]
            equivalent = equivalence["numerically_equivalent_to_jobs1"]
        memory_ok = before is None or after is None or min(before, after) >= MIN_AVAILABLE_MEMORY_BYTES
        results.append({"rf_jobs": rf_jobs, "elapsed_seconds": elapsed,
                        "available_memory_before_bytes": before,
                        "available_memory_after_bytes": after,
                        "finite_prediction": finite, "memory_guard_passed": memory_ok,
                        "kendall_tau": tau, "max_abs_difference_from_jobs1": max_abs_diff,
                        "max_relative_difference_from_jobs1": max_rel_diff,
                        "kendall_difference_from_jobs1": tau_difference,
                        "numerically_equivalent_to_jobs1": equivalent,
                        "valid": bool(finite and memory_ok and equivalent)})
        del prediction
        gc.collect()
    selected = select_pilot_job(results)
    artifact = {"protocol": PROTOCOL,
                "configuration_sha256": provenance["configuration_sha256"],
                "preflight_identity_sha256": provenance["identity_sha256"],
                "preflight_sha256": provenance["preflight_sha256"],
                "selection_rule": "fastest finite, memory-bounded 1/4/8 fit numerically equivalent to rf_jobs=1; ties choose lower rf_jobs",
                "numerical_equivalence_tolerances": {"absolute": PILOT_ABSOLUTE_TOLERANCE,
                                                       "relative": PILOT_RELATIVE_TOLERANCE,
                                                       "kendall_tau": PILOT_KENDALL_TOLERANCE},
                "representative_fold": {key: row[key] for key in ("network", "target", "radius", "seed", "fold", "logical_arm")},
                "canonical_fit_count": preflight_doc["canonical_fit_count"],
                "measurements": results,
                "selected_rf_jobs": selected,
                "estimated_full_seconds": float(next(item["elapsed_seconds"] for item in results
                                                     if item["rf_jobs"] == selected)
                                                * preflight_doc["canonical_fit_count"])}
    artifact["pilot_sha256"] = stable_digest(artifact)
    atomic_json(artifact, PILOT_PATH)
    return artifact


def _validated_pilot(preflight_doc: dict[str, Any], provenance: dict[str, Any], rf_jobs: int) -> dict[str, Any]:
    """Require the selected worker count from the immutable preflight-bound pilot."""
    if not PILOT_PATH.is_file():
        raise RuntimeError("execution requires phase6_buffered_cv_pilot.json")
    pilot = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    claimed = pilot.get("pilot_sha256")
    unsigned = dict(pilot)
    unsigned.pop("pilot_sha256", None)
    if claimed != stable_digest(unsigned):
        raise RuntimeError("pilot artifact digest differs")
    required = {"protocol": PROTOCOL, "configuration_sha256": provenance["configuration_sha256"],
                "preflight_identity_sha256": provenance["identity_sha256"],
                "preflight_sha256": provenance["preflight_sha256"],
                "canonical_fit_count": preflight_doc["canonical_fit_count"]}
    if any(pilot.get(key) != value for key, value in required.items()):
        raise RuntimeError("pilot does not bind this scientific/preflight identity")
    rows = pilot.get("measurements", [])
    if {int(item.get("rf_jobs", -1)) for item in rows} != {1, 4, 8}:
        raise RuntimeError("pilot lacks the required 1/4/8 worker measurements")
    declared_tolerances = {"absolute": PILOT_ABSOLUTE_TOLERANCE, "relative": PILOT_RELATIVE_TOLERANCE,
                           "kendall_tau": PILOT_KENDALL_TOLERANCE}
    if pilot.get("numerical_equivalence_tolerances") != declared_tolerances:
        raise RuntimeError("pilot numerical-equivalence tolerances differ from protocol")
    if not all(bool(item.get("numerically_equivalent_to_jobs1")) for item in rows):
        raise RuntimeError("pilot worker settings are not numerically equivalent to rf_jobs=1")
    if int(pilot.get("selected_rf_jobs", -1)) != select_pilot_job(rows):
        raise RuntimeError("pilot selected worker count violates the pre-registered rule")
    if rf_jobs != int(pilot["selected_rf_jobs"]):
        raise RuntimeError("execution rf_jobs differs from the preflight-bound pilot selection")
    return pilot

def cell_key(network: str, target: str, radius: int, seed: int) -> str:
    return f"{network}|{target}|r{radius}|s{seed}"


def _cell_checkpoint_root(key: str) -> Path:
    # A digest produces a Windows-safe component while the readable key remains
    # inside each generation's rows for audit and collision detection.
    return CHECKPOINT_ROOT / hashlib.sha256(key.encode("utf-8")).hexdigest()


def _cell_rows(preflight_doc: dict[str, Any], network: str, target: str,
               radius: int, seed: int) -> list[dict[str, Any]]:
    rows = [dict(row) for row in preflight_doc["fold_rows"]
            if (row["network"], row["target"], int(row["radius"]), int(row["seed"]))
            == (network, target, radius, seed)]
    if len(rows) != FOLDS * 5:
        raise RuntimeError(f"{cell_key(network, target, radius, seed)}: preflight rows are incomplete")
    keys = {(int(row["fold"]), row["logical_arm"]) for row in rows}
    if len(keys) != len(rows):
        raise RuntimeError("preflight contains duplicate logical fold keys")
    return rows


def _assignment(assignments: dict[str, np.ndarray], network: str, target: str, radius: int,
                seed: int, fold: int, arm: str, field: str) -> np.ndarray:
    key = assignment_key(network, target, radius, seed, fold, arm, field)
    if key not in assignments:
        raise RuntimeError(f"assignment archive missing {key}")
    return np.asarray(assignments[key], dtype=np.int64)


def _load_cell_assignments(preflight_doc: dict[str, Any], key: str) -> dict[str, np.ndarray]:
    record = preflight_doc["assignment_files"].get(key)
    if record is None:
        raise RuntimeError(f"preflight lacks immutable assignments for {key}")
    path = Path(record["path"])
    if not path.is_file() or digest_file(path) != record["sha256"]:
        raise RuntimeError(f"assignment archive changed for {key}")
    with np.load(path) as archive:
        arrays = {name: archive[name] for name in archive.files}
    rows = [row for row in preflight_doc["fold_rows"]
            if cell_key(row["network"], row["target"], int(row["radius"]), int(row["seed"])) == key]
    expected = {assignment_key(row["network"], row["target"], int(row["radius"]), int(row["seed"]),
                               int(row["fold"]), row["logical_arm"], field)
                for row in rows for field in ("test_ids", "train_ids", "excluded_ids")}
    if set(arrays) != expected:
        raise RuntimeError(f"assignment archive key set is incomplete or has extras for {key}")
    if any(row.get("assignment_file_sha256") != record["sha256"] for row in rows):
        raise RuntimeError(f"preflight rows disagree with assignment archive digest for {key}")
    logical_fields = ("network", "target", "radius", "seed", "fold", "logical_arm", "canonical_arm",
                      "alias_of", "status", "buffer", "n_test", "n_train", "n_excluded", "control_rng_seed")
    for row in rows:
        expected_assignment = stable_digest({field: row[field] for field in logical_fields})
        if row.get("assignment_sha256") != expected_assignment:
            raise RuntimeError(f"preflight assignment digest differs for {key}")
        unsigned = dict(row)
        recorded_row_digest = unsigned.pop("preflight_row_sha256", None)
        if recorded_row_digest != stable_digest(unsigned):
            raise RuntimeError(f"preflight row digest differs for {key}")
        for field in ("test_ids", "train_ids", "excluded_ids"):
            values = _assignment(arrays, row["network"], row["target"], int(row["radius"]), int(row["seed"]),
                                 int(row["fold"]), row["logical_arm"], field)
            if row.get(f"{field}_sha256") != stable_digest(values):
                raise RuntimeError(f"preflight ID digest differs for {key}/{field}")
    return arrays


def _validate_resumed_rows(rows: list[dict[str, Any]], expected_rows: list[dict[str, Any]],
                           assignments: dict[str, np.ndarray], key: str) -> None:
    observed = {(int(row["fold"]), row["logical_arm"]) for row in rows}
    expected = {(int(row["fold"]), row["logical_arm"]) for row in expected_rows}
    if observed != expected or len(rows) != len(observed):
        raise RuntimeError(f"checkpoint logical fold-key set differs for {key}")
    expected_by_key = {(int(row["fold"]), row["logical_arm"]): row for row in expected_rows}
    immutable_fields = ("assignment_sha256", "preflight_row_sha256", "assignment_file",
                        "assignment_file_sha256", "test_ids_sha256", "train_ids_sha256",
                        "excluded_ids_sha256", "canonical_arm", "alias_of", "buffer")
    for row in rows:
        reference = expected_by_key[(int(row["fold"]), row["logical_arm"])]
        for field in immutable_fields:
            if row.get(field) != reference.get(field):
                raise RuntimeError(f"checkpoint immutable {field} differs for {key}")
        for field in ("test_ids", "train_ids", "excluded_ids"):
            expected_array = _assignment(assignments, row["network"], row["target"], int(row["radius"]),
                                         int(row["seed"]), int(row["fold"]), row["logical_arm"], field)
            if not np.array_equal(np.asarray(row.get(field), dtype=np.int64), expected_array):
                raise RuntimeError(f"checkpoint {field} differs from immutable assignments for {key}")
            if stable_digest(expected_array) != reference[f"{field}_sha256"]:
                raise RuntimeError(f"preflight ID digest differs for {key}/{field}")


def _cell_complete_rows(rows: list[dict[str, Any]], n: int, y: np.ndarray,
                        state_oof: dict[str, np.ndarray]) -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    """Create cell scores only after every required fold for an arm succeeded."""
    cells: list[dict[str, Any]] = []
    full_oof: dict[str, np.ndarray] = {}
    for arm in ("region", "buffer_b1", "control_b1", "buffer_measured", "control_measured"):
        arm_rows = [row for row in rows if row["logical_arm"] == arm]
        statuses = {row["status"] for row in arm_rows}
        canonical = arm_rows[0]["canonical_arm"]
        if statuses == {COMPLETE}:
            prediction = np.full(n, np.nan, dtype=np.float64)
            for row in arm_rows:
                key = f"f{row['fold']}|{canonical}"
                if key not in state_oof:
                    raise RuntimeError(f"completed fold lacks checkpoint prediction {key}")
                test = np.asarray(row["test_ids"], dtype=np.int64)
                value = np.asarray(state_oof[key], dtype=np.float64)
                if value.shape != (len(test),):
                    raise RuntimeError(f"checkpoint prediction shape differs for {key}")
                prediction[test] = value
            if not np.isfinite(prediction).all():
                raise RuntimeError(f"{arm}: a claimed full OOF vector has gaps")
            full_oof[canonical] = prediction
            tau = float(kendalltau(y, prediction).statistic)
            status = COMPLETE
            oof_digest = stable_digest(prediction)
        else:
            if COMPLETE in statuses or READY in statuses:
                # Partial predictions remain only in the per-cell checkpoint;
                # no cell score or final OOF key can silently represent a subset.
                status, tau, oof_digest = "incomplete", np.nan, None
            elif UNRESOLVED in statuses:
                status, tau, oof_digest = UNRESOLVED, np.nan, None
            elif INFEASIBLE in statuses or SOURCE_INFEASIBLE in statuses:
                status, tau, oof_digest = INFEASIBLE, np.nan, None
            else:
                raise RuntimeError(f"{arm}: unknown status set {statuses}")
        cells.append({"logical_arm": arm, "canonical_arm": canonical, "status": status,
                      "kendall_tau": tau, "oof_sha256": oof_digest})
    return cells, full_oof


def _run_cell(network: str, target: str, radius: int, seed: int, X: np.ndarray, y: np.ndarray,
              preflight_doc: dict[str, Any], provenance: dict[str, Any],
              rf_jobs: int, stop_after: int | None, fitted_so_far: int) -> tuple[int, bool]:
    """Resume-safe transaction loop for one target/radius/seed cell.

    A cell checkpoint contains at most five region predictions per canonical arm;
    it is small enough to atomically regenerate after each fit and never retains
    another network's feature matrix.
    """
    key = cell_key(network, target, radius, seed)
    assignments = _load_cell_assignments(preflight_doc, key)
    root = _cell_checkpoint_root(key)
    state = load_checkpoint(root, provenance)
    if state["fold_rows"]:
        rows = state["fold_rows"]
        if {row.get("cell_key") for row in rows} != {key}:
            raise RuntimeError("checkpoint belongs to another buffered cell")
        _validate_resumed_rows(rows, _cell_rows(preflight_doc, network, target, radius, seed), assignments, key)
    else:
        rows = _cell_rows(preflight_doc, network, target, radius, seed)
        for row in rows:
            row["cell_key"] = key
            row["test_ids"] = _assignment(assignments, network, target, radius, seed,
                                            int(row["fold"]), row["logical_arm"], "test_ids").tolist()
            row["train_ids"] = _assignment(assignments, network, target, radius, seed,
                                             int(row["fold"]), row["logical_arm"], "train_ids").tolist()
            row["excluded_ids"] = _assignment(assignments, network, target, radius, seed,
                                                int(row["fold"]), row["logical_arm"], "excluded_ids").tolist()
        state["fold_rows"] = rows
        state["cell_rows"] = []
        write_checkpoint(root, provenance, state)
    # Each canonical arm is fitted once per fold.  Aliases inherit the exact
    # prediction and digest, including the b=1 measured-buffer coincidence.
    for fold in range(FOLDS):
        for canonical in ("region", "buffer_b1", "control_b1", "buffer_measured", "control_measured"):
            canonical_rows = [row for row in rows if int(row["fold"]) == fold
                              and row["canonical_arm"] == canonical]
            source = next((row for row in canonical_rows if row["logical_arm"] == canonical), None)
            if source is None or source["status"] != READY:
                continue
            pred_key = f"f{fold}|{canonical}"
            if pred_key not in state["oof"]:
                test_ids = np.asarray(source["test_ids"], dtype=np.int64)
                train_ids = np.asarray(source["train_ids"], dtype=np.int64)
                started = time.perf_counter()
                prediction = fit_region_fold(X, y, train_ids, test_ids, seed, rf_jobs, target)
                elapsed = time.perf_counter() - started
                state["oof"][pred_key] = prediction
                source["status"] = COMPLETE
                source["prediction_sha256"] = stable_digest(prediction)
                source["fit_seconds"] = elapsed
                for alias in canonical_rows:
                    if alias is not source:
                        alias["status"] = COMPLETE
                        alias["prediction_sha256"] = source["prediction_sha256"]
                        alias["fit_seconds"] = source["fit_seconds"]
                write_checkpoint(root, provenance, state)
                fitted_so_far += 1
                if stop_after is not None and fitted_so_far >= stop_after:
                    return fitted_so_far, True
            else:
                # A checkpoint may have been written after the prediction but
                # before an older process updated aliases; repair only metadata
                # whose value is fully determined by the recorded prediction.
                source["status"] = COMPLETE
                source["prediction_sha256"] = stable_digest(state["oof"][pred_key])
                for alias in canonical_rows:
                    if alias is not source:
                        alias["status"] = COMPLETE
                        alias["prediction_sha256"] = source["prediction_sha256"]
    cells, _full = _cell_complete_rows(rows, len(y), y, state["oof"])
    for row in cells:
        row.update({"network": network, "target": target, "radius": radius, "seed": seed,
                    "n_features": int(X.shape[1]), "cell_key": key,
                    "configuration_sha256": provenance["configuration_sha256"],
                    "preflight_identity_sha256": provenance["identity_sha256"]})
        row["row_sha256"] = stable_digest(row)
    state["cell_rows"] = cells
    write_checkpoint(root, provenance, state)
    return fitted_so_far, False


def _materialize_final(preflight_doc: dict[str, Any], provenance: dict[str, Any]) -> None:
    """Publish compact aggregate files while holding only one cell/network at once."""
    expected_cells = [(network, target, radius, seed) for network in NETWORKS for target in TARGETS
                      for radius in RADII for seed in SEEDS]

    def state_for(network: str, target: str, radius: int, seed: int) -> dict[str, Any]:
        state = load_checkpoint(_cell_checkpoint_root(cell_key(network, target, radius, seed)), provenance)
        if len(state["cell_rows"]) != 5:
            raise RuntimeError("cannot materialize an incomplete buffered corpus")
        _validate_resumed_rows(state["fold_rows"], _cell_rows(preflight_doc, network, target, radius, seed),
                               _load_cell_assignments(preflight_doc, cell_key(network, target, radius, seed)),
                               cell_key(network, target, radius, seed))
        return state

    # The generator drops each checkpoint before loading the next.  IDs are
    # replaced by their immutable archive references/digests before CSV output.
    def compact_folds():
        seen: set[tuple[Any, ...]] = set()
        for network, target, radius, seed in expected_cells:
            state = state_for(network, target, radius, seed)
            for row in state["fold_rows"]:
                key = (row["network"], row["target"], row["radius"], row["seed"], row["fold"], row["logical_arm"])
                if key in seen:
                    raise RuntimeError("checkpoint transactions contain duplicate final fold keys")
                seen.add(key)
                yield compact_fold_row(row)
            del state
            gc.collect()

    folds_path = RESULTS / "phase6_buffered_cv_folds.csv"
    folds_sha = _stream_csv_rows(compact_folds(), folds_path)
    cells: list[dict[str, Any]] = []  # 4,000 scalar rows, no expanded graph memberships.
    oof_root = RESULTS / "phase6_buffered_cv_oof"
    oof_manifest: dict[str, dict[str, Any]] = {}
    completed_oof_keys: list[str] = []
    for network in NETWORKS:
        network_oof: dict[str, np.ndarray] = {}
        for _network, target, radius, seed in (item for item in expected_cells if item[0] == network):
            state = state_for(network, target, radius, seed)
            cells.extend(state["cell_rows"])
            for row in state["cell_rows"]:
                if row["status"] != COMPLETE or row["logical_arm"] != row["canonical_arm"]:
                    continue
                arm_rows = [item for item in state["fold_rows"] if item["logical_arm"] == row["logical_arm"]]
                n = sum(int(item["n_test"]) for item in arm_rows)
                vector = np.full(n, np.nan, dtype=np.float64)
                for item in arm_rows:
                    test = np.asarray(item["test_ids"], dtype=np.int64)
                    vector[test] = state["oof"][f"f{item['fold']}|{item['canonical_arm']}"]
                if not np.isfinite(vector).all():
                    raise RuntimeError("final OOF reconstruction found a partial vector")
                output_key = f"{network}|{target}|r{radius}|s{seed}|{row['canonical_arm']}"
                network_oof[output_key] = vector
                completed_oof_keys.append(output_key)
            del state
            gc.collect()
        network_path = oof_root / f"{network}.npz"
        atomic_npz(network_oof, network_path)
        oof_manifest[network] = {"path": network_path.as_posix(), "sha256": digest_file(network_path),
                                 "keys": sorted(network_oof)}
        del network_oof
        gc.collect()
    cell_keys = [(r["network"], r["target"], r["radius"], r["seed"], r["logical_arm"]) for r in cells]
    if len(cell_keys) != len(set(cell_keys)):
        raise RuntimeError("checkpoint transactions contain duplicate final cell keys")
    cells_path = RESULTS / "phase6_buffered_cv_cells.csv"
    atomic_csv(cells, cells_path)
    oof_manifest_path = RESULTS / "phase6_buffered_cv_oof_manifest.json"
    atomic_json({"protocol": PROTOCOL, "configuration_sha256": provenance["configuration_sha256"],
                 "preflight_identity_sha256": provenance["identity_sha256"], "archives": oof_manifest},
                oof_manifest_path)
    results_manifest = {"protocol": PROTOCOL, "configuration_sha256": provenance["configuration_sha256"],
                        "preflight_identity_sha256": provenance["identity_sha256"],
                        "preflight_sha256": provenance["preflight_sha256"],
                        "cells_csv": cells_path.as_posix(), "cells_sha256": digest_file(cells_path),
                        "folds_csv": folds_path.as_posix(), "folds_sha256": folds_sha,
                        "oof_manifest": oof_manifest_path.as_posix(), "oof_manifest_sha256": digest_file(oof_manifest_path),
                        "expected_logical_cell_keys": provenance["expected_logical_cell_keys"],
                        "completed_oof_keys": sorted(completed_oof_keys)}
    results_manifest["results_sha256"] = stable_digest(results_manifest)
    atomic_json(results_manifest, RESULTS_MANIFEST_PATH)

def execute(rf_jobs: int, stop_after: int | None = None) -> None:
    """Run the previously frozen preflight plan with one network resident at a time."""
    if rf_jobs not in (1, 4, 8):
        raise ValueError("rf_jobs must be one of the measured bounded values 1, 4, 8")
    preflight_doc, provenance = _load_preflight()
    pilot = _validated_pilot(preflight_doc, provenance, rf_jobs)
    # Worker selection is execution provenance, deliberately downstream of the
    # immutable scientific/preflight identity so its benchmark is not circular.
    provenance = dict(provenance)
    provenance["execution_identity_sha256"] = stable_digest({"preflight_identity_sha256": provenance["identity_sha256"],
                                                               "pilot_sha256": pilot["pilot_sha256"], "rf_jobs": rf_jobs})
    if preflight_doc["configuration"].get("outer_workers") != 1:
        raise RuntimeError("buffered protocol permits exactly one outer worker")
    fitted = 0
    for network in NETWORKS:
        features = pd.read_csv(f"cache_features_{network}.csv")
        targets = pd.read_csv(f"cache_targets_{network}.csv")
        registry = pd.read_csv(f"cache_registry_{network}.csv")
        for target in TARGETS:
            y = targets[target].to_numpy(dtype=np.float64)
            for radius in RADII:
                columns = structural_features(registry, features, radius)
                X = features[columns].to_numpy(dtype=np.float64)
                for seed in SEEDS:
                    fitted, stopped = _run_cell(network, target, radius, seed, X, y, preflight_doc,
                                                 provenance, rf_jobs, stop_after, fitted)
                    if stopped:
                        print(f"Controlled stop after {fitted} canonical fits; rerun with identical provenance.")
                        return
        del features, targets, registry
        gc.collect()
    _materialize_final(preflight_doc, provenance)
    print(f"Complete buffered corpus after {fitted} newly fitted canonical folds.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--moran", default="results/phase6_structural_moran_correlogram.csv")
    parser.add_argument("--moran-provenance", default="results/phase6_structural_moran_correlogram_provenance.json")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--benchmark-only", action="store_true")
    # Accepted in benchmark mode solely for command symmetry; the pilot always
    # measures all three pre-registered settings before selecting one.
    parser.add_argument("--rf-jobs", type=int, choices=(1, 4, 8))
    parser.add_argument("--stop-after-canonical-fits", type=int)
    args = parser.parse_args()
    if args.preflight_only and args.benchmark_only:
        parser.error("--preflight-only and --benchmark-only are mutually exclusive")
    if args.preflight_only:
        if args.rf_jobs is not None or args.stop_after_canonical_fits is not None:
            parser.error("resource and stop controls do not apply to --preflight-only")
        doc, _provenance = preflight(Path(args.moran), Path(args.moran_provenance), write=True)
        print(f"Preflight wrote {PREFLIGHT_PATH}: {doc['canonical_fit_count']} canonical fits; zero models fitted.")
        return 0
    if args.benchmark_only:
        if args.stop_after_canonical_fits is not None:
            parser.error("stop control does not apply to --benchmark-only")
        doc, provenance = _load_preflight()
        pilot = benchmark(doc, provenance)
        print(f"Pilot wrote {PILOT_PATH}: selected rf_jobs={pilot['selected_rf_jobs']}; no checkpoint was written.")
        return 0
    if args.rf_jobs is None:
        parser.error("--rf-jobs is required for execution after the selected pilot")
    execute(args.rf_jobs, args.stop_after_canonical_fits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

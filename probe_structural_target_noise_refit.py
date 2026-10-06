"""Resumable structural-tier target-bootstrap refits for Phase 6 Task 1.

This is a new follow-up arm.  It never appends to or interprets the historical
A7 dynamic-tier CSV.  The outer worker count is deliberately fixed at one;
within-forest job counts are explicitly measured and bounded so Windows does
not make simultaneous process copies of the cache-heavy bootstrap workload.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import sys
import tempfile
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau
import scipy
import sklearn
from sklearn.ensemble import RandomForestRegressor

from analyse import FULL
from influence.experiment import out_of_fold_predictions
from influence.preprocessing import load_edgelist
from probe_target_noise import MC_TARGETS, targets_from_cascades
# P2-07 (Task 6 audit, Claude Opus 5, 2026-09-11): the registry-tier filter
# below is the only thing keeping target-derived columns out of the structural
# feature set, and it relies on the registry being tagged correctly - the same
# class of assumption the 5-node orbit retag (P1-01) just falsified. The name
# blacklist in influence.targets is the independent second check every other
# fitting lane runs; this runner now runs it too.
from influence.targets import assert_no_leakage


NETWORKS = ("ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined",
            "p2p-Gnutella08")
RADII = (0, 1, 2, 3)
FIT_SEED = 0
RESAMPLE_SEED = 0
PROTOCOL = "phase6-structural-target-refit-v1"


def bounded_forest(seed: int, n_jobs: int) -> RandomForestRegressor:
    """The published RF hyperparameters with measured, bounded tree parallelism."""
    return RandomForestRegressor(n_estimators=120, n_jobs=n_jobs, random_state=seed,
                                 min_samples_leaf=2)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    """Replace a checkpoint atomically so a power loss leaves its prior CSV intact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False,
                                     dir=path.parent, suffix=".tmp") as stream:
        temp = Path(stream.name)
        frame.to_csv(stream, index=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def atomic_json(value: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                     dir=path.parent, suffix=".tmp") as stream:
        temp = Path(stream.name)
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def replicate_indices(n_samples: int, reps: int, seed: int) -> list[np.ndarray]:
    """Draw one resample per replicate; a resample is shared over targets/radii."""
    rng = np.random.default_rng(seed)
    return [rng.integers(0, n_samples, size=n_samples) for _ in range(reps)]


def index_digest(indices: np.ndarray) -> str:
    # Include dtype/shape in the identity; identical bytes under another shape
    # would otherwise be a different bootstrap draw but the same digest.
    header = f"{indices.dtype.str}|{indices.shape}".encode("ascii")
    return hashlib.sha256(header + indices.tobytes(order="C")).hexdigest()


def structural_features(registry: pd.DataFrame, features: pd.DataFrame,
                        radius: int) -> list[str]:
    wanted = set(FULL.split("+"))
    cols = registry[(registry.hop <= radius) & registry.tier.isin(wanted)].feature.tolist()
    if not cols:
        raise ValueError(f"radius {radius}: no {FULL} feature columns")
    absent = sorted(set(cols).difference(features.columns))
    if absent:
        raise ValueError(f"radius {radius}: registry-selected features missing from cache: {absent}")
    # The dynamic tier is excluded by construction and asserted for auditability.
    leaked = registry[(registry.feature.isin(cols)) & (registry.tier == "dynamic")]
    if len(leaked):
        raise AssertionError("structural tier unexpectedly selected dynamic features")
    # Independent of the registry tags: refuse any column whose NAME says it was
    # derived from a target (P2-07, 2026-09-11). Recorded as a post-run source
    # change - the 2026-09-10 12,000-cell output was produced without this line
    # and its provenance binds the pre-change source hash.
    assert_no_leakage(cols)
    return cols


def validate_sweep(path: Path) -> dict[int, int]:
    """Require the exact ten-seed structural cells used for headline comparisons."""
    d = pd.read_csv(path)
    required = {"target", "radius", "richness", "seed", "kendall_tau"}
    required.add("n_features")
    if missing := required.difference(d.columns):
        raise ValueError(f"{path}: missing sweep columns {sorted(missing)}")
    # This is the established resume convention used by analyse.py.
    d = d.drop_duplicates(["target", "radius", "richness", "seed"], keep="last")
    d = d[(d.richness == FULL) & d.target.isin(MC_TARGETS)]
    expected = set(product(MC_TARGETS, RADII, range(10)))
    observed = set(zip(d.target, d.radius, d.seed))
    if observed != expected:
        raise ValueError(f"{path}: expected exactly 3 targets x 4 radii x 10 seeds")
    if not np.isfinite(pd.to_numeric(d.kendall_tau, errors="coerce").to_numpy(float)).all():
        raise ValueError(f"{path}: selected structural seed tau is nonfinite")
    counts: dict[int, int] = {}
    for radius, block in d.groupby("radius"):
        values = set(pd.to_numeric(block.n_features, errors="coerce").tolist())
        if len(values) != 1 or not np.isfinite(next(iter(values))):
            raise ValueError(f"{path}: radius {radius} has inconsistent/nonfinite feature count")
        counts[int(radius)] = int(next(iter(values)))
    return counts


def validate_original_ids(network: str, features: pd.DataFrame,
                          original_ids: np.ndarray) -> None:
    """Ensure cached row i is the original graph node reconstructed as i."""
    if "original_id" not in features.columns:
        raise ValueError(f"{network}: feature cache lacks original_id")
    cached = features.original_id.to_numpy()
    if not np.array_equal(cached, original_ids):
        raise ValueError(f"{network}: cached original_id order differs from rebuilt graph")


def validate_alignment(network: str, cascades: np.ndarray, features: pd.DataFrame,
                       targets: pd.DataFrame, registry: pd.DataFrame, raw_path: Path,
                       metadata: dict, sweep_counts: dict[int, int]) -> dict[str, object]:
    n_nodes, n_samples = cascades.shape
    for name, table in (("features", features), ("targets", targets)):
        if len(table) != n_nodes:
            raise ValueError(f"{network}: {name} rows {len(table)} != cascade nodes {n_nodes}")
        if "node" not in table.columns or not table.node.is_unique:
            raise ValueError(f"{network}: {name} lacks unique node IDs")
        if not np.array_equal(table.node.to_numpy(), np.arange(n_nodes)):
            raise ValueError(f"{network}: {name} node order does not match cascade rows")
    required_reg = {"feature", "hop", "tier"}
    if missing := required_reg.difference(registry.columns):
        raise ValueError(f"{network}: registry missing {sorted(missing)}")
    if registry.feature.duplicated().any():
        raise ValueError(f"{network}: registry repeats a feature name")
    rebuilt_network = load_edgelist(raw_path, name=network)
    if rebuilt_network.n != n_nodes:
        raise ValueError(f"{network}: rebuilt graph nodes {rebuilt_network.n} != cache nodes {n_nodes}")
    validate_original_ids(network, features, rebuilt_network.original_ids)
    if int(metadata.get("n", -1)) != n_nodes or int(metadata.get("n_sims", -1)) != n_samples:
        raise ValueError(f"{network}: cache metadata n/n_sims does not match cascade shape")
    rebuilt = targets_from_cascades(cascades)
    gaps = {}
    for target in MC_TARGETS:
        if target not in targets.columns:
            raise ValueError(f"{network}: cached target {target} is absent")
        value = targets[target].to_numpy(float)
        if not np.isfinite(value).all():
            raise ValueError(f"{network}/{target}: cached target is nonfinite")
        gap = float(np.max(np.abs(rebuilt[target] - value)))
        if gap > 1e-9:
            raise AssertionError(f"{network}/{target}: rebuilt cache gap {gap:.3e}")
        gaps[target] = gap
    # Force selection at every radius before CPU work begins.
    counts = {str(radius): len(structural_features(registry, features, radius))
              for radius in RADII}
    if {radius: counts[str(radius)] for radius in RADII} != sweep_counts:
        raise ValueError(f"{network}: registry structural feature counts differ from headline sweep")
    return {"nodes": n_nodes, "samples": n_samples, "target_max_abs_gap": gaps,
            "structural_feature_counts": counts}


def input_paths(network: str, raw_path: Path) -> list[Path]:
    return [Path(f"cache_cascades_{network}.npy"), Path(f"cache_features_{network}.csv"),
            Path(f"cache_targets_{network}.csv"), Path(f"cache_registry_{network}.csv"),
            Path(f"cache_meta_{network}.json"), Path(f"sweep_{network}.csv"), raw_path]


def preflight(reps: int, rf_jobs: int) -> tuple[dict[str, dict], dict[str, object]]:
    """Validate all input identities before creating any result checkpoint."""
    corpus: dict[str, dict] = {}
    input_hashes: dict[str, str] = {}
    resamples: dict[str, list[str]] = {}
    alignment: dict[str, dict] = {}
    manifest_path = Path("data/manifest.json")
    manifest = {entry["name"]: Path(entry["path"].replace("\\", os.sep))
                for entry in json.loads(manifest_path.read_text(encoding="utf-8"))}
    for network in NETWORKS:
        if network not in manifest:
            raise ValueError(f"{network}: absent from data manifest")
        paths = input_paths(network, manifest[network])
        absent = [str(path) for path in paths if not path.is_file()]
        if absent:
            raise FileNotFoundError(f"{network}: missing inputs {absent}")
        sweep_counts = validate_sweep(Path(f"sweep_{network}.csv"))
        # Keep no full cascade matrices resident across networks.  The available
        # physical memory is intentionally treated as scarce on this workstation.
        cascades = np.load(paths[0], mmap_mode="r")
        features = pd.read_csv(paths[1])
        targets = pd.read_csv(paths[2])
        registry = pd.read_csv(paths[3])
        metadata = json.loads(paths[4].read_text(encoding="utf-8"))
        alignment[network] = validate_alignment(network, cascades, features, targets, registry,
                                                paths[6], metadata, sweep_counts)
        indices = replicate_indices(cascades.shape[1], reps, RESAMPLE_SEED)
        resamples[network] = [index_digest(index) for index in indices]
        corpus[network] = {"paths": [str(path) for path in paths[:4]],
                           "indices": indices}
        input_hashes.update({path.as_posix(): digest(path) for path in paths})
        # validate_alignment materialises a rebuilt target once.  Drop every
        # per-network table before continuing so the next network does not add
        # to its RSS; the execution loop loads exactly one network at a time.
        del cascades, features, targets, registry
        gc.collect()
    input_hashes[manifest_path.as_posix()] = digest(manifest_path)
    semantic_sources = [Path(__file__).resolve(), Path("analyse.py"), Path("probe_target_noise.py"),
                        Path("influence/experiment.py"), Path("influence/targets.py"),
                        Path("influence/preprocessing.py")]
    for source in semantic_sources:
        input_hashes[source.name if source.is_absolute() else source.as_posix()] = digest(source)
    config = {"protocol": PROTOCOL, "networks": NETWORKS, "targets": MC_TARGETS,
              "radii": RADII, "tier": FULL, "reps": reps,
              "resample_seed": RESAMPLE_SEED, "fit_seed": FIT_SEED,
              "outer_workers": 1, "rf_n_jobs": rf_jobs,
              "target_builder": "probe_target_noise.targets_from_cascades"}
    provenance = {"configuration": config, "configuration_sha256": stable_digest(config),
                  "input_sha256": input_hashes, "resample_index_sha256": resamples,
                  "alignment": alignment,
                  "runtime_versions": {"python": platform.python_version(),
                                       "numpy": np.__version__, "pandas": pd.__version__,
                                       "scipy": scipy.__version__, "scikit_learn": sklearn.__version__}}
    return corpus, provenance


def expected_keys(reps: int) -> set[tuple[str, str, int, int]]:
    return set(product(NETWORKS, MC_TARGETS, RADII, range(reps)))


def result_row_digest(row: dict[str, object]) -> str:
    """Bind a completed result's identity, value, and feature count in its CSV row.

    This is a corruption check for a resumable local checkpoint.  It detects an
    accidental edit of a row while avoiding a second checkpoint file whose
    update could be torn by a crash.  It is not an authentication mechanism:
    someone who deliberately edits both payload and digest can recompute it.
    """
    fields = ("network", "target", "radius", "tier", "rep", "tau_refit",
              "n_features", "configuration_sha256", "resample_sha256")
    missing = set(fields).difference(row)
    if missing:
        raise ValueError(f"cannot digest incomplete result row: {sorted(missing)}")
    # pandas exposes scalar cells as NumPy types after a CSV reload.  Convert
    # those to their JSON-native equivalents before hashing the same logical
    # payload that was emitted by the runner.
    payload = {field: (row[field].item() if isinstance(row[field], np.generic) else row[field])
               for field in fields}
    return stable_digest(payload)


def load_resume(out: Path, provenance_path: Path, provenance: dict,
                reps: int) -> tuple[pd.DataFrame, set[tuple[str, str, int, int]]]:
    if out.exists() != provenance_path.exists():
        raise RuntimeError("resume requires both result CSV and provenance, or neither")
    if not out.exists():
        atomic_json(provenance, provenance_path)
        return pd.DataFrame(), set()
    saved = json.loads(provenance_path.read_text(encoding="utf-8"))
    # Execution checks are appended after the first pilot refit.  They document
    # validation evidence, but cannot change the fixed configuration/provenance.
    saved_core = dict(saved)
    saved_core.pop("execution_checks", None)
    # JSON round-trips tuples as lists.  Compare the canonical JSON form so
    # unchanged protocol tuples do not make an interrupted valid run impossible
    # to resume, while every value remains provenance-bound.
    if stable_digest(saved_core) != stable_digest(provenance):
        raise RuntimeError("resume provenance differs: inputs, code, config, or resample identity changed")
    # A row digest includes tau at full Python-float precision.  The round-trip
    # parser avoids the lower-precision CSV conversion mode changing a valid
    # checkpoint's binary float before its digest is checked.
    frame = pd.read_csv(out, float_precision="round_trip")
    required = {"network", "target", "radius", "tier", "rep", "tau_refit",
                "n_features", "configuration_sha256", "resample_sha256", "row_sha256"}
    if missing := required.difference(frame.columns):
        raise ValueError(f"resume CSV missing columns {sorted(missing)}")
    keys = list(zip(frame.network, frame.target, frame.radius, frame.rep))
    if len(keys) != len(set(keys)):
        raise ValueError("resume CSV contains duplicate completed cells")
    if not set(keys).issubset(expected_keys(reps)):
        raise ValueError("resume CSV contains cells outside this configured protocol")
    if set(frame.tier) != {FULL}:
        raise ValueError("resume CSV tier differs from structural protocol")
    if not np.isfinite(pd.to_numeric(frame.tau_refit, errors="coerce").to_numpy(float)).all():
        raise ValueError("resume CSV contains nonfinite tau")
    if set(frame.configuration_sha256) != {provenance["configuration_sha256"]}:
        raise ValueError("resume CSV configuration hash differs from provenance")
    for row in frame.itertuples(index=False):
        row_dict = {field: getattr(row, field) for field in
                    ("network", "target", "radius", "tier", "rep", "tau_refit",
                     "n_features", "configuration_sha256", "resample_sha256")}
        if row.row_sha256 != result_row_digest(row_dict):
            raise ValueError("resume CSV row digest differs; checkpoint row was altered or corrupted")
        if row.resample_sha256 != provenance["resample_index_sha256"][row.network][int(row.rep)]:
            raise ValueError("resume CSV resample identity differs from provenance")
        counts = provenance["alignment"][row.network]["structural_feature_counts"]
        expected_features = int(counts[str(int(row.radius))])
        if int(row.n_features) != expected_features:
            raise ValueError("resume CSV feature count differs from validated structural registry")
    return frame, set(keys)


def validate_parallel_equivalence(network: str, data: dict, rf_jobs: int) -> dict[str, object]:
    """Check the selected bounded forest against the established default OOF construction."""
    cascades_path, features_path, _targets_path, registry_path = map(Path, data["paths"])
    cascades = np.load(cascades_path, mmap_mode="r")
    features = pd.read_csv(features_path)
    registry = pd.read_csv(registry_path)
    boot = targets_from_cascades(cascades[:, data["indices"][0]])
    target, radius = MC_TARGETS[0], RADII[0]
    X = features[structural_features(registry, features, radius)].to_numpy(float)
    # The default uses the historical inner parallelism; the selected factory is
    # the production mode for this follow-up.  Last-bit differences are bounded
    # on predictions and on tau before pilot results exist.
    parallel = out_of_fold_predictions(X, boot[target], seed=FIT_SEED)
    bounded = out_of_fold_predictions(X, boot[target], seed=FIT_SEED,
                                      estimator=lambda seed: bounded_forest(seed, rf_jobs))
    max_abs = float(np.max(np.abs(parallel - bounded)))
    tau_parallel = float(kendalltau(boot[target], parallel).statistic)
    tau_bounded = float(kendalltau(boot[target], bounded).statistic)
    tau_gap = abs(tau_parallel - tau_bounded)
    if max_abs > 1e-10 or tau_gap > 1e-6:
        raise AssertionError(f"bounded/default OOF equivalence failed: max prediction "
                             f"gap {max_abs:.3e}, tau gap {tau_gap:.3e}")
    return {"network": network, "target": target, "radius": radius,
            "rep": 0, "rf_n_jobs": rf_jobs, "max_abs_prediction_gap": max_abs,
            "tau_default": tau_parallel, "tau_bounded": tau_bounded,
            "abs_tau_gap": tau_gap, "prediction_tolerance": 1e-10,
            "tau_tolerance": 1e-6}


def available_memory_bytes() -> int | None:
    """Read available Windows memory without adding a psutil dependency."""
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


def benchmark_jobs(corpus: dict[str, dict], provenance: dict, output: Path) -> None:
    """Measure one cache-heavy representative cell before the all-cell pilot."""
    network, target, radius, rep = "ca-HepTh", "spread_mean", 3, 0
    data = corpus[network]
    cascades_path, features_path, _targets_path, registry_path = map(Path, data["paths"])
    cascades = np.load(cascades_path, mmap_mode="r")
    features, registry = pd.read_csv(features_path), pd.read_csv(registry_path)
    y = targets_from_cascades(cascades[:, data["indices"][rep]])[target]
    X = features[structural_features(registry, features, radius)].to_numpy(float)
    rows, baseline = [], None
    for jobs in (1, 4, 8):
        before = available_memory_bytes()
        start = time.perf_counter()
        prediction = out_of_fold_predictions(X, y, seed=FIT_SEED,
                                             estimator=lambda seed: bounded_forest(seed, jobs))
        elapsed = time.perf_counter() - start
        tau = float(kendalltau(y, prediction).statistic)
        if baseline is None:
            baseline = prediction
            max_gap, tau_gap = 0.0, 0.0
        else:
            max_gap = float(np.max(np.abs(prediction - baseline)))
            tau_gap = abs(tau - float(kendalltau(y, baseline).statistic))
        rows.append({"rf_n_jobs": jobs, "elapsed_seconds": elapsed, "tau": tau,
                     "max_abs_prediction_gap_vs_1": max_gap,
                     "abs_tau_gap_vs_1": tau_gap,
                     "available_memory_before": before,
                     "available_memory_after": available_memory_bytes()})
        print(f"benchmark n_jobs={jobs}: {elapsed:.1f}s tau={tau:.8f} "
              f"max-gap-vs-1={max_gap:.3e} tau-gap={tau_gap:.3e}", flush=True)
    atomic_json({"protocol": PROTOCOL, "representative_cell": {"network": network,
                 "target": target, "radius": radius, "rep": rep,
                 "n_nodes": len(y), "n_features": X.shape[1]},
                 "provenance": provenance, "results": rows}, output)


def run(args: argparse.Namespace) -> int:
    if args.workers != 1:
        raise ValueError("outer workers must be 1: sklearn forests already parallelise internally")
    if args.reps < 1 or args.stop_after_reps is not None and args.stop_after_reps < 1:
        raise ValueError("reps and stop-after-reps must be positive")
    out, provenance_path = Path(args.out), Path(args.provenance)
    corpus, provenance = preflight(args.reps, args.rf_jobs)
    if args.benchmark_only:
        benchmark_jobs(corpus, provenance, Path(args.benchmark_out))
        return 0
    frame, done = load_resume(out, provenance_path, provenance, args.reps)
    saved = json.loads(provenance_path.read_text(encoding="utf-8"))
    if "execution_checks" not in saved:
        check = validate_parallel_equivalence(NETWORKS[0], corpus[NETWORKS[0]], args.rf_jobs)
        saved["execution_checks"] = {"bounded_default_ooF_equivalence": check}
        atomic_json(saved, provenance_path)
        print("Bounded/default OOF equivalence passed: "
              f"max prediction gap {check['max_abs_prediction_gap']:.3e}, "
              f"tau gap {check['abs_tau_gap']:.3e}.", flush=True)
    print(f"Preflight passed: tier={FULL}, reps={args.reps}, workers=1; "
          f"{len(done)}/{len(expected_keys(args.reps))} cells already complete.", flush=True)
    started, completed_reps, new = time.perf_counter(), 0, 0
    for network in NETWORKS:
        data = corpus[network]
        cascades_path, features_path, _targets_path, registry_path = map(Path, data["paths"])
        cascades = np.load(cascades_path, mmap_mode="r")
        features = pd.read_csv(features_path)
        registry = pd.read_csv(registry_path)
        for rep, index in enumerate(data["indices"]):
            pending = [(target, radius) for target in MC_TARGETS for radius in RADII
                       if (network, target, radius, rep) not in done]
            if not pending:
                continue
            boot = targets_from_cascades(cascades[:, index])
            for target, radius in pending:
                cols = structural_features(registry, features, radius)
                X = features[cols].to_numpy(float)
                pred = out_of_fold_predictions(X, boot[target], seed=FIT_SEED,
                                               estimator=lambda seed: bounded_forest(seed, args.rf_jobs))
                tau = float(kendalltau(boot[target], pred).statistic)
                if not np.isfinite(tau):
                    raise RuntimeError(f"{network}/{target}/r{radius}/rep{rep}: nonfinite tau")
                row = {"network": network, "target": target, "radius": radius,
                       "tier": FULL, "rep": rep, "tau_refit": tau,
                       "n_features": len(cols),
                       "configuration_sha256": provenance["configuration_sha256"],
                       "resample_sha256": provenance["resample_index_sha256"][network][rep]}
                row["row_sha256"] = result_row_digest(row)
                frame = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
                atomic_csv(frame, out)
                done.add((network, target, radius, rep))
                new += 1
                elapsed = time.perf_counter() - started
                print(f"{network} rep {rep + 1}/{args.reps} {target} r={radius}: "
                      f"tau={tau:.6f}; {len(done)}/{len(expected_keys(args.reps))} "
                      f"({elapsed / max(new, 1):.1f}s/new refit)", flush=True)
            completed_reps += 1
            if args.stop_after_reps is not None and completed_reps >= args.stop_after_reps:
                print("Controlled stop reached; rerun with identical provenance to resume.", flush=True)
                return 0
        del cascades, features, registry
        gc.collect()
    print(f"Complete: {len(done)} cells written to {out}; elapsed {(time.perf_counter()-started)/60:.1f} min.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=200)
    parser.add_argument("--out", default="results/results_target_noise_refit_structural.csv")
    parser.add_argument("--provenance", default="results/provenance_target_noise_refit_structural.json")
    parser.add_argument("--workers", type=int, default=1, choices=[1])
    parser.add_argument("--rf-jobs", type=int, choices=[1, 4, 8],
                        help="bounded in-forest workers; benchmark 1, 4 and 8 before choosing")
    parser.add_argument("--benchmark-only", action="store_true",
                        help="time ca-HepTh/spread_mean/r3 at n_jobs 1, 4 and 8; no result CSV")
    parser.add_argument("--benchmark-out", default="results/structural_target_noise_pilot_benchmark.json")
    parser.add_argument("--stop-after-reps", type=int,
                        help="controlled checkpoint test: stop after this many newly processed replicates")
    args = parser.parse_args()
    if args.benchmark_only:
        # Benchmark needs deterministic index identity but no full 200-rep plan.
        args.reps = 1
        args.rf_jobs = 1
    elif args.rf_jobs is None:
        parser.error("--rf-jobs is required after reviewing --benchmark-only output")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())

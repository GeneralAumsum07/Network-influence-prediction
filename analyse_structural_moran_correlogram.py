"""Structural-tier rank-residual Moran correlogram for buffered-CV preflight.

The historical C6 ``results_moran_correlogram.csv`` uses the dynamic tier and
is intentionally not read or overwritten here.  This script recomputes the
same lag-wise diagnostic for ``analyse.FULL`` structural OOF vectors so the
buffered follow-up has a provenance-bound input of its own.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy
import sklearn
from threadpoolctl import threadpool_limits

import analyse
from analyse_betweenness_k import manifest_paths
from analyse_moran_correlogram import ALPHA, MIN_SOURCES, morans_i, rank_pct
from influence.preprocessing import load_edgelist


PROTOCOL = "phase6-structural-moran-v1"
STRUCTURAL_TIER = analyse.FULL
TARGETS = ("spread_mean", "spread_cv", "spread_resid", "betweenness")
RADII = (0, 1, 2, 3)
SEEDS = tuple(range(10))
NULL_REFERENCE_SEED = 0
NULL_REFERENCE_DESCRIPTION = "permutations use the fit-seed-0 residual per target/radius and provide a shared seed-0-reference tail area for every fit seed"
UNRESOLVED_NO_NONSIG = "unresolved_no_testable_nonsig"
# This cap is local to the new structural runner.  It prevents dense BLAS from
# competing with the concurrently running CPU forests without mutating global
# environment settings or the historical dynamic-tier runner.
BLAS_THREADS = 4


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


PROJECT_ROOT = Path(__file__).resolve().parent


def relative_source_key(path: Path) -> str:
    """
    Root-relative posix key for a source file, e.g. 'influence/preprocessing.py'.

    Until 2026-09-11 producer hashes were keyed on ABSOLUTE paths (Task 6 audit
    finding P2-02), so an artifact could only be re-validated from the checkout
    that produced it. Keys are now relative to the project root. Files outside
    the root keep their absolute posix path - there are none today, and hiding
    one behind a relative name would be worse than the original defect.
    """
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def normalise_source_keys(mapping: dict[str, str]) -> dict[str, str]:
    """
    Compatibility shim for artifacts recorded before 2026-09-11.

    The two shipped provenance files (results/phase6_buffered_cv_provenance.json,
    results/phase6_structural_moran_correlogram_provenance.json) carry absolute
    keys, and their recorded hashes are folded into identity digests that 800
    checkpoint manifests bind to - so the FILES must not be rewritten. Instead a
    validator maps each recorded key to its root-relative suffix before
    comparing. Purely lexical: a recorded absolute key is rewritten to its
    longest suffix that names an existing file under the current root, and
    left alone otherwise. The SAFETY is still the hash comparison that follows
    - a key mapped onto a same-named file with different bytes fails there;
    the shim only decides which file the recorded hash is held against.
    (Claude Opus 5, P2-02)
    """
    out: dict[str, str] = {}
    for key, value in mapping.items():
        p = Path(key)
        # A posix-absolute key ("/home/...") is not is_absolute() on Windows and
        # vice versa for "C:/..." on posix; the artifact may have been written
        # on either, so test both spellings.
        if p.is_absolute() or key.startswith("/"):
            parts = p.as_posix().split("/")
            # Longest PROPER suffix that names an existing file under the root.
            # i starts at 1 because joining the root with a still-absolute
            # candidate would just return the absolute path and "match".
            for i in range(1, len(parts)):
                candidate = "/".join(parts[i:])
                if not Path(candidate).is_absolute() and (PROJECT_ROOT / candidate).is_file():
                    key = candidate
                    break
        out[key] = value
    return out


def producer_source_hashes() -> dict[str, str]:
    """Bind the structural artifact to every source module that creates it."""
    root = PROJECT_ROOT
    sources = (Path(__file__).resolve(), root / "analyse.py", root / "analyse_moran_correlogram.py",
               root / "analyse_betweenness_k.py", root / "influence/preprocessing.py")
    missing = [path.as_posix() for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"structural Moran producer source missing: {missing}")
    # Root-relative keys since 2026-09-11 (P2-02); see relative_source_key.
    return {relative_source_key(path): digest(path) for path in sources}


def structural_oof_path(network: str, target: str) -> Path:
    """Return the reported structural OOF source, including log1p betweenness."""
    if target == "betweenness":
        return Path("estimators") / f"cache_oof_{network}__rf_log1p.npz"
    return Path(f"cache_oof_{network}.npz")


def structural_oof_store(network: str, target: str) -> dict[str, np.ndarray]:
    path = structural_oof_path(network, target)
    if not path.is_file():
        raise FileNotFoundError(path)
    prefix = f"{target}|"
    with np.load(path) as archive:
        return {key: archive[key] for key in archive.files if key.startswith(prefix)}


def first_nonsig(rows: list[dict[str, Any]]) -> tuple[int | None, bool]:
    """Read the first testable primary non-significant lag and later-sig flag."""
    ordered = sorted((row for row in rows if bool(row.get("testable"))), key=lambda row: int(row["lag"]))
    for index, row in enumerate(ordered):
        if not bool(row["sig"]):
            return int(row["lag"]), any(bool(later["sig"]) for later in ordered[index + 1:])
    return None, False


def measured_buffers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse only complete ten-seed rank curves into measured buffer decisions."""
    frame = pd.DataFrame(rows)
    if frame.empty:
        return []
    need = {"network", "target", "radius", "seed", "residual", "lag", "testable", "sig"}
    missing = need.difference(frame.columns)
    if missing:
        raise ValueError(f"Moran rows missing {sorted(missing)}")
    rank = frame[frame.residual == "rank"]
    result: list[dict[str, Any]] = []
    for (network, target, radius), group in rank.groupby(["network", "target", "radius"], sort=True):
        seed_records = []
        for seed in SEEDS:
            curve = group[group.seed == seed].to_dict("records")
            cutoff, later = first_nonsig(curve)
            seed_records.append({"seed": seed, "first_nonsig": cutoff, "later_testable_sig": later})
        unresolved = [record["seed"] for record in seed_records if record["first_nonsig"] is None]
        result.append({"network": network, "target": target, "radius": int(radius),
                       "status": "resolved" if not unresolved else UNRESOLVED_NO_NONSIG,
                       "measured_buffer": (int(np.ceil(np.median([record["first_nonsig"] for record in seed_records])) )
                                           if not unresolved else None),
                       "unresolved_seeds": unresolved, "seedwise": seed_records,
                       "later_testable_sig": any(record["later_testable_sig"] for record in seed_records)})
    return result


def _rows_for_network(network: str, raw_path: Path, perms: int, batch: int, random_seed: int) -> tuple[list[dict[str, Any]], dict[str, str]]:
    net = load_edgelist(raw_path, name=network)
    target_path = Path(f"cache_targets_{network}.csv")
    feature_path = Path(f"cache_features_{network}.csv")
    registry_path = Path(f"cache_registry_{network}.csv")
    truth = pd.read_csv(target_path)
    features = pd.read_csv(feature_path)
    # OOF vector positions are only meaningful when both cache tables use the
    # rebuilt LCC's contiguous node order; original IDs bind that order to the
    # raw graph rather than merely checking equal lengths.
    expected_nodes = np.arange(net.n)
    if (len(truth) != net.n or "node" not in truth
            or not np.array_equal(truth["node"].to_numpy(), expected_nodes)):
        raise ValueError(f"{network}: target cache node order differs from rebuilt graph")
    if (len(features) != net.n or {"node", "original_id"}.difference(features.columns)
            or not np.array_equal(features["node"].to_numpy(), expected_nodes)
            or not np.array_equal(features["original_id"].to_numpy(), net.original_ids)):
        raise ValueError(f"{network}: feature cache node/original-ID order differs from rebuilt graph")
    hashes = {"graph_sha256": digest(raw_path), "cache_features_sha256": digest(feature_path),
              "cache_targets_sha256": digest(target_path),
              "cache_registry_sha256": digest(registry_path)}
    columns: list[np.ndarray] = []
    meta: list[tuple[str, int, int, Path]] = []
    source_hashes: dict[str, str] = {}
    for target in TARGETS:
        if target not in truth:
            raise ValueError(f"{network}: missing target {target}")
        store = structural_oof_store(network, target)
        path = structural_oof_path(network, target)
        source_hashes[path.as_posix()] = digest(path)
        y_rank = rank_pct(truth[target].to_numpy(float))
        for radius in RADII:
            for seed in SEEDS:
                key = f"{target}|{radius}|{STRUCTURAL_TIER}|{seed}"
                if key not in store:
                    raise ValueError(f"{path}: missing structural OOF key {key}")
                prediction = store[key]
                if prediction.shape != (net.n,):
                    raise ValueError(f"{path}: {key} has shape {prediction.shape}, expected {(net.n,)}")
                if not np.isfinite(prediction).all():
                    raise ValueError(f"{path}: {key} contains non-finite structural OOF values")
                columns.append(y_rank - rank_pct(prediction))
                meta.append((target, radius, seed, path))
    n_cells = len(columns)
    if not n_cells:
        return [], {**hashes, **{f"oof:{k}": v for k, v in source_hashes.items()}}
    rng = np.random.default_rng(random_seed)
    null_indices: dict[tuple[str, int], list[int]] = {}
    base: dict[tuple[str, int], np.ndarray] = {}
    for index, (target, radius, seed, _path) in enumerate(meta):
        if seed == NULL_REFERENCE_SEED:
            base[(target, radius)] = columns[index]
    for target_radius, vector in base.items():
        for _ in range(perms):
            null_indices.setdefault(target_radius, []).append(len(columns))
            columns.append(vector[rng.permutation(net.n)])
    # column_stack already preserves the float64 residual columns; astype here
    # would briefly allocate another large dense matrix.  Release the list of
    # per-cell vectors before the BLAS work begins on the consolidated matrix.
    Z = np.column_stack(columns)
    del columns
    gc.collect()
    Z -= Z.mean(axis=0, keepdims=True)
    with threadpool_limits(limits=BLAS_THREADS, user_api="blas"):
        I, empty = morans_i(net.adj.astype(np.float32), Z, 7, batch)
    rows: list[dict[str, Any]] = []
    for index, (target, radius, seed, source_path) in enumerate(meta):
        indices = null_indices[(target, radius)]
        for lag in range(1, 8):
            observed = I[lag - 1, index]
            null = I[lag - 1, indices]
            null = null[np.isfinite(null)]
            p_value = ((np.sum(np.abs(null) >= abs(observed)) + 1) / (len(null) + 1)
                       if len(null) else np.nan)
            n_used = net.n - int(empty[lag - 1])
            primary_sig = bool(p_value < ALPHA / lag) if np.isfinite(p_value) else False
            # A NaN observed statistic or null distribution is untestable; it
            # cannot be reinterpreted as a non-significant lag and thereby
            # produce a false measured buffer of one.
            is_testable = bool(n_used >= MIN_SOURCES and np.isfinite(observed) and np.isfinite(p_value))
            rows.append({"network": network, "target": target, "radius": radius, "seed": seed,
                         "tier": STRUCTURAL_TIER, "residual": "rank", "lag": lag,
                         "morans_I": float(observed), "p_perm": float(p_value), "alpha_d": ALPHA / lag,
                         "sig": primary_sig, "sig_bonferroni7": bool(p_value < ALPHA / 7) if np.isfinite(p_value) else False,
                         "n_empty_rows": int(empty[lag - 1]), "n_used": n_used,
                         "testable": is_testable, "perms": len(null),
                         "null_reference_seed": NULL_REFERENCE_SEED,
                         "p_perm_interpretation": NULL_REFERENCE_DESCRIPTION,
                         "correction": "progressive_bonferroni", "source_oof_path": source_path.as_posix(),
                         **hashes, "oof_sha256": source_hashes[source_path.as_posix()]})
    frame = pd.DataFrame(rows)
    for _, indices in frame.groupby(["network", "target", "radius", "seed"], sort=False).groups.items():
        curve = frame.loc[indices].to_dict("records")
        cutoff, later = first_nonsig(curve)
        frame.loc[indices, "first_nonsig"] = cutoff if cutoff is not None else np.nan
        frame.loc[indices, "later_testable_sig"] = later
    return frame.to_dict("records"), {**hashes, **{f"oof:{k}": v for k, v in source_hashes.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--perms", type=int, default=199)
    parser.add_argument("--batch", type=int, default=512)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="results/phase6_structural_moran_correlogram.csv")
    parser.add_argument("--provenance", default="results/phase6_structural_moran_correlogram_provenance.json")
    parser.add_argument("--tags", default="")
    args = parser.parse_args()
    if args.perms < 1 or args.batch < 1:
        parser.error("--perms and --batch must be positive")
    paths = manifest_paths()
    tags = [tag for tag in ("ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined", "p2p-Gnutella08") if tag in paths]
    if args.tags:
        requested = set(args.tags.split(","))
        tags = [tag for tag in tags if tag in requested]
    rows: list[dict[str, Any]] = []
    all_hashes: dict[str, dict[str, str]] = {}
    for network in tags:
        print(f"{network}: structural rank-residual Moran lags 1..7", flush=True)
        network_rows, hashes = _rows_for_network(network, Path(paths[network]), args.perms, args.batch, args.seed)
        rows.extend(network_rows)
        all_hashes[network] = hashes
    if not rows:
        raise RuntimeError("no structural Moran rows were produced")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    summary = measured_buffers(rows)
    provenance = {"protocol": PROTOCOL, "configuration": {"tier": STRUCTURAL_TIER, "targets": TARGETS,
                  "radii": RADII, "seeds": SEEDS, "lags": 7, "perms": args.perms, "batch": args.batch,
                  "random_seed": args.seed, "blas_threads": BLAS_THREADS,
                  "null_reference_seed": NULL_REFERENCE_SEED,
                  "p_perm_interpretation": NULL_REFERENCE_DESCRIPTION}, "input_sha256": all_hashes,
                  "producer_source_sha256": producer_source_hashes(), "output_sha256": digest(out),
                  "measured_buffers": summary, "runtime_versions": {"python": platform.python_version(),
                  "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
                  "scikit_learn": sklearn.__version__}}
    Path(args.provenance).parent.mkdir(parents=True, exist_ok=True)
    Path(args.provenance).write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(rows)} rows) and {args.provenance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Describe structural-tier paired target-bootstrap radius gains for Phase 6.

This reads the dedicated structural refit corpus and current structural seed
sweeps.  It never regenerates targets or fits a model, and keeps the historical
dynamic-tier A7 analysis separate from this follow-up arm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from analyse import FULL
from analyse_paired_target_noise import NETWORKS, RADII, SEEDS, paired_matrix, pair_summary
from probe_target_noise import MC_TARGETS

REPS = tuple(range(200))


def validate_refit_corpus(frame: pd.DataFrame, provenance: dict) -> None:
    """Reject a partial or differently configured checkpoint before comparing gains."""
    required = {"network", "target", "radius", "tier", "rep", "tau_refit",
                "configuration_sha256", "resample_sha256"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"structural refit corpus missing columns: {sorted(missing)}")
    if frame[list(required)].isna().any().any():
        raise ValueError("structural refit corpus has missing required values")
    configuration = provenance.get("configuration", {})
    expected_config = {
        "tier": FULL, "reps": len(REPS), "networks": list(NETWORKS),
        "targets": list(MC_TARGETS), "radii": list(RADII),
        "fit_seed": 0, "resample_seed": 0, "outer_workers": 1,
    }
    for key, value in expected_config.items():
        if configuration.get(key) != value:
            raise ValueError(f"provenance configuration {key!r} differs from the fixed design")
    config_hash = provenance.get("configuration_sha256")
    if not config_hash or set(frame.configuration_sha256) != {config_hash}:
        raise ValueError("refit corpus configuration hash differs from provenance")
    expected_cells = set(product(NETWORKS, MC_TARGETS, RADII, [FULL]))
    observed_cells = set(zip(frame.network, frame.target, frame.radius, frame.tier))
    if observed_cells != expected_cells:
        raise ValueError("structural refit cells differ from the fixed 5 x 3 x 4 scope")
    if frame.duplicated(["network", "target", "radius", "tier", "rep"]).any():
        raise ValueError("structural refit corpus has duplicate cell-replicate observations")
    tau = pd.to_numeric(frame.tau_refit, errors="coerce").to_numpy(float)
    if not np.isfinite(tau).all():
        raise ValueError("structural refit corpus has nonfinite tau_refit")
    identities = provenance.get("resample_index_sha256", {})
    for cell, sub in frame.groupby(["network", "target", "radius", "tier"], sort=False):
        reps = set(pd.to_numeric(sub.rep, errors="coerce").tolist())
        if reps != set(REPS):
            raise ValueError(f"{cell}: expected replicate IDs 0--199 exactly")
    for row in frame.itertuples(index=False):
        if row.resample_sha256 != identities.get(row.network, [])[int(row.rep)]:
            raise ValueError("refit corpus resample identity differs from provenance")


def structural_seed_matrix(network: str) -> dict[str, np.ndarray]:
    """Load exactly the ten keep-last structural seed observations per cell."""
    path = Path(f"sweep_{network}.csv")
    sweep = pd.read_csv(path)
    required = {"target", "radius", "richness", "seed", "kendall_tau"}
    missing = required.difference(sweep.columns)
    if missing:
        raise ValueError(f"{path}: missing sweep columns {sorted(missing)}")
    sweep = sweep.drop_duplicates(["target", "radius", "richness", "seed"], keep="last")
    sweep = sweep[(sweep.richness == FULL) & sweep.target.isin(MC_TARGETS)]
    expected = set(product(MC_TARGETS, RADII, SEEDS))
    if set(zip(sweep.target, sweep.radius, sweep.seed)) != expected:
        raise ValueError(f"{path}: expected exactly 3 targets x 4 radii x 10 structural seed cells")
    if not np.isfinite(pd.to_numeric(sweep.kendall_tau, errors="coerce").to_numpy(float)).all():
        raise ValueError(f"{path}: selected structural seed tau is nonfinite")
    return {target: paired_matrix(sweep[sweep.target == target], "seed", "kendall_tau", max(RADII))
            for target in MC_TARGETS}


def run_analysis(refit_path: Path, provenance_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(refit_path)
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    validate_refit_corpus(frame, provenance)
    rows: list[dict[str, object]] = []
    for network in NETWORKS:
        seeds = structural_seed_matrix(network)
        for target in MC_TARGETS:
            refits = paired_matrix(frame[(frame.network == network) & (frame.target == target)],
                                   "rep", "tau_refit", max(RADII))
            for radius in RADII[:-1]:
                target_summary = pair_summary(refits[radius], refits[radius + 1])
                seed_summary = pair_summary(seeds[target][radius], seeds[target][radius + 1])
                row: dict[str, object] = {"network": network, "target": target,
                                          "radius_from": radius, "radius_to": radius + 1}
                row.update({f"target_{key}": value for key, value in target_summary.items()})
                row.update({f"seed_{key}": value for key, value in seed_summary.items()})
                row["target_over_seed_sd"] = (target_summary["sd"] / seed_summary["sd"]
                                                if seed_summary["sd"] else np.nan)
                row["flag_change"] = ("retained" if target_summary["heuristic_star"] and seed_summary["heuristic_star"] else
                                      "lost" if seed_summary["heuristic_star"] else
                                      "new" if target_summary["heuristic_star"] else "neither")
                rows.append(row)
    out = pd.DataFrame(rows)
    if len(out) != 45:
        raise AssertionError(f"expected 45 adjacent-radius contrasts, got {len(out)}")
    return out


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_report(out: pd.DataFrame, path: Path, inputs: list[Path], output: Path) -> None:
    flags = out.flag_change.value_counts()
    ratio = out.target_over_seed_sd.replace([np.inf, -np.inf], np.nan)
    lines = [
        "PHASE 6 STRUCTURAL-TIER PAIRED RADIUS-GAIN TARGET-NOISE ANALYSIS", "",
        "Read-only analysis of the completed structural-tier target-bootstrap corpus and current",
        "keep-last structural seed sweeps. No targets, fits, or simulations ran during analysis.",
        "Scope: 45 adjacent-radius contrasts (5 networks x 3 Monte Carlo targets x 3 gains),",
        "node+edge+subgraph only; 200 paired target-bootstrap replicates and 10 paired seeds.", "",
        "Heuristic copied from analyse.py: |mean paired gain| > 2 * sample SD.",
        f"Seed flags: {int(out.seed_heuristic_star.sum())}/45; target-bootstrap flags: {int(out.target_heuristic_star.sum())}/45.",
        ("Flag changes (target-bootstrap relative to seed): retained="
         f"{int(flags.get('retained', 0))}, lost={int(flags.get('lost', 0))}, "
         f"new={int(flags.get('new', 0))}, neither={int(flags.get('neither', 0))}."),
        ("Target/seed paired-SD ratio: median "
         f"{ratio.median():.3f}; range {ratio.min():.3f}--{ratio.max():.3f} "
         f"over {ratio.notna().sum()} nonzero-denominator contrasts."), "",
        "Percentile spans are observed distribution percentiles, not CIs, p-values, or",
        "multiplicity-adjusted tests. The target-bootstrap and seed distributions condition on",
        "different perturbations; their SDs are not combined into total uncertainty.", "",
        "Input/source SHA-256 (repository-relative labels):",
        *[f"SHA256 {sha256(source)}  {source.as_posix()}" for source in inputs],
        f"SHA256 {sha256(output)}  {output.as_posix()}", "",
        "Per contrast (gain = tau(r+1) - tau(r); variance identity = var(lower) +",
        "var(upper) - 2*covariance):", out.to_csv(index=False, float_format="%.9g"),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refit", type=Path, default=Path("results/results_target_noise_refit_structural.csv"))
    parser.add_argument("--provenance", type=Path, default=Path("results/provenance_target_noise_refit_structural.json"))
    parser.add_argument("--out", type=Path, default=Path("results/results_paired_target_noise_structural.csv"))
    parser.add_argument("--report", type=Path, default=Path("results/RESULTS_paired_target_noise_structural.txt"))
    args = parser.parse_args()
    out = run_analysis(args.refit, args.provenance)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    inputs = [args.refit, args.provenance, *[Path(f"sweep_{network}.csv") for network in NETWORKS],
              Path(__file__).resolve().relative_to(Path.cwd()), Path("analyse_paired_target_noise.py")]
    write_report(out, args.report, inputs, args.out)
    print(f"Wrote {args.out} and {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

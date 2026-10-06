"""Describe A7 target-bootstrap noise in adjacent-radius gains.

This is intentionally a read-only analysis of the completed A7 refit CSV and
the current seed sweeps.  It neither reconstructs targets nor fits models.
"""

from __future__ import annotations

import hashlib
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


NETWORKS = (
    "ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined",
    "p2p-Gnutella08",
)
TARGETS = ("spread_cv", "spread_mean", "spread_resid")
TIER = "node+edge+subgraph+dynamic"
RADII = (0, 1, 2, 3)
REPS = tuple(range(200))
SEEDS = tuple(range(10))


def paired_matrix(d: pd.DataFrame, key: str, value: str,
                  max_radius: int) -> np.ndarray:
    """Return radius x key values after proving the two dimensions align.

    A pivot table would quietly average duplicate rows.  A plain pivot and the
    explicit checks below turn a resumed or damaged input into an error instead
    of a plausible-looking paired gain.
    """
    required = {key, "radius", value}
    absent = required.difference(d.columns)
    if absent:
        raise ValueError(f"missing paired-matrix columns: {sorted(absent)}")
    if d[[key, "radius"]].isna().any().any():
        raise ValueError("missing replicate/seed or radius key")
    if d.duplicated([key, "radius"]).any():
        raise ValueError("duplicate replicate/seed-radius observation")
    vals = pd.to_numeric(d[value], errors="coerce")
    if not np.isfinite(vals.to_numpy(float)).all():
        raise ValueError("nonfinite paired value")

    expected_radii = list(range(max_radius + 1))
    observed_radii = sorted(d.radius.unique().tolist())
    if observed_radii != expected_radii:
        raise ValueError(f"expected radii {expected_radii}, got {observed_radii}")
    mat = d.pivot(index="radius", columns=key, values=value).sort_index()
    if list(mat.index) != expected_radii or mat.isna().any().any():
        raise ValueError("missing or unpaired replicate/seed observation")
    return mat.to_numpy(float)


def pair_summary(lower: np.ndarray, upper: np.ndarray) -> dict[str, object]:
    """Summarise upper-minus-lower with the project’s strict paired heuristic."""
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    if lower.ndim != 1 or upper.ndim != 1 or len(lower) != len(upper) or not len(lower):
        raise ValueError("paired vectors must be nonempty, one-dimensional, and equal length")
    if not (np.isfinite(lower).all() and np.isfinite(upper).all()):
        raise ValueError("paired vectors contain nonfinite values")
    gain = upper - lower
    sd = float(gain.std(ddof=1)) if len(gain) > 1 else float("nan")
    lower_var = float(lower.var(ddof=1)) if len(lower) > 1 else float("nan")
    upper_var = float(upper.var(ddof=1)) if len(upper) > 1 else float("nan")
    covariance = (float(np.cov(lower, upper, ddof=1)[0, 1])
                  if len(gain) > 1 else float("nan"))
    variance_identity = lower_var + upper_var - 2 * covariance
    mean = float(gain.mean())
    return {
        "n": int(len(gain)), "mean": mean, "sd": sd,
        "positive": int((gain > 0).sum()), "zero": int((gain == 0).sum()),
        "negative": int((gain < 0).sum()),
        "p025": float(np.percentile(gain, 2.5, method="linear")),
        "p975": float(np.percentile(gain, 97.5, method="linear")),
        "lower_variance": lower_var, "upper_variance": upper_var,
        "covariance": covariance, "variance_identity": variance_identity,
        # This is deliberately the same strict algebra as analyse.py section 3.
        "heuristic_star": bool(abs(mean) > 2 * sd),
    }


def validate_corpus(d: pd.DataFrame) -> None:
    """Require exactly the completed 5 x 3 x 4 x 200 A7 refit corpus."""
    required = {"network", "target", "radius", "tier", "rep", "tau_refit"}
    absent = required.difference(d.columns)
    if absent:
        raise ValueError(f"A7 corpus missing columns: {sorted(absent)}")
    if d[list(required)].isna().any().any():
        raise ValueError("A7 corpus has missing required values")
    expected_cells = set(product(NETWORKS, TARGETS, RADII, [TIER]))
    observed_cells = set(zip(d.network, d.target, d.radius, d.tier))
    if observed_cells != expected_cells:
        missing = expected_cells.difference(observed_cells)
        extra = observed_cells.difference(expected_cells)
        raise ValueError(f"A7 cells differ from fixed scope; missing={len(missing)}, extra={len(extra)}")
    if d.duplicated(["network", "target", "radius", "tier", "rep"]).any():
        raise ValueError("A7 corpus has duplicate cell-replicate observations")
    if not np.isfinite(pd.to_numeric(d.tau_refit, errors="coerce").to_numpy(float)).all():
        raise ValueError("A7 corpus has nonfinite tau_refit")
    for cell, sub in d.groupby(["network", "target", "radius", "tier"], sort=False):
        reps = set(pd.to_numeric(sub.rep, errors="coerce").tolist())
        if reps != set(REPS):
            raise ValueError(f"{cell}: expected replicate indices 0--199 exactly")


def seed_matrix(network: str) -> dict[str, np.ndarray]:
    """Load one current sweep using its established keep-last resume convention."""
    path = Path(f"sweep_{network}.csv")
    d = pd.read_csv(path)
    required = {"target", "radius", "richness", "seed", "kendall_tau"}
    absent = required.difference(d.columns)
    if absent:
        raise ValueError(f"{path}: missing sweep columns {sorted(absent)}")
    # This mirrors analyse._read_dedup: a later resumed result supersedes an
    # earlier checkpoint for the same experiment cell.
    d = d.drop_duplicates(["target", "radius", "richness", "seed"], keep="last")
    d = d[(d.richness == TIER) & d.target.isin(TARGETS)]
    if d.empty:
        raise ValueError(f"{path}: no matching dynamic-tier A7 targets")
    if d[["target", "radius", "seed"]].isna().any().any():
        raise ValueError(f"{path}: missing selected sweep key")
    if not np.isfinite(pd.to_numeric(d.kendall_tau, errors="coerce").to_numpy(float)).all():
        raise ValueError(f"{path}: nonfinite selected sweep tau")
    expected = set(product(TARGETS, RADII, SEEDS))
    observed = set(zip(d.target, d.radius, d.seed))
    if observed != expected:
        raise ValueError(f"{path}: selected sweep must contain exactly 3x4x10 A7 cells")
    if d.duplicated(["target", "radius", "seed"]).any():
        raise ValueError(f"{path}: duplicate selected sweep cell after deduplication")
    matrices = {}
    for target in TARGETS:
        matrices[target] = paired_matrix(
            d[d.target == target], "seed", "kendall_tau", max(RADII))
    return matrices


def run_analysis(refit_path: Path = Path("results_target_noise_refit.csv")) -> pd.DataFrame:
    refit = pd.read_csv(refit_path)
    validate_corpus(refit)
    rows: list[dict[str, object]] = []
    for network in NETWORKS:
        seed_matrices = seed_matrix(network)
        for target in TARGETS:
            sub = refit[(refit.network == network) & (refit.target == target)]
            target_mat = paired_matrix(sub, "rep", "tau_refit", max(RADII))
            for radius in RADII[:-1]:
                t = pair_summary(target_mat[radius], target_mat[radius + 1])
                s = pair_summary(seed_matrices[target][radius], seed_matrices[target][radius + 1])
                row: dict[str, object] = {
                    "network": network, "target": target,
                    "radius_from": radius, "radius_to": radius + 1,
                }
                row.update({f"target_{k}": v for k, v in t.items()})
                row.update({f"seed_{k}": v for k, v in s.items()})
                row["target_over_seed_sd"] = (t["sd"] / s["sd"]
                                               if s["sd"] != 0 else np.nan)
                row["seed_over_target_sd"] = (s["sd"] / t["sd"]
                                               if t["sd"] != 0 else np.nan)
                row["flag_change"] = (
                    "retained" if t["heuristic_star"] and s["heuristic_star"] else
                    "lost" if s["heuristic_star"] else
                    "new" if t["heuristic_star"] else "neither"
                )
                rows.append(row)
    out = pd.DataFrame(rows)
    if len(out) != 45:
        raise AssertionError(f"expected 45 adjacent-radius contrasts, got {len(out)}")
    return out


def sha256(path: Path) -> str:
    """Hash a recorded input without making its absolute local path evidence."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_report(out: pd.DataFrame, path: Path, input_paths: list[Path],
                 csv_path: Path) -> None:
    flags = out.flag_change.value_counts()
    seed_flags = int(out.seed_heuristic_star.sum())
    target_flags = int(out.target_heuristic_star.sum())
    ratio = out.target_over_seed_sd.replace([np.inf, -np.inf], np.nan)
    lines = [
        "A7 PAIRED RADIUS-GAIN TARGET-NOISE ANALYSIS",
        "",
        "Read-only descriptive follow-through on results_target_noise_refit.csv and the",
        "current keep-last sweep_<network>.csv files.  No targets, fits, or simulations ran.",
        "Scope: 45 adjacent-radius contrasts (5 networks x 3 Monte Carlo targets x 3 gains),",
        "richest dynamic tier only; 200 paired target-bootstrap replicates and 10 paired seeds.",
        "",
        "Heuristic copied from analyse.py section 3: |mean paired gain| > 2 * sample SD.",
        f"Seed flags: {seed_flags}/45; paired target-bootstrap flags: {target_flags}/45.",
        ("Flag changes (target-bootstrap relative to seed): "
         f"retained={int(flags.get('retained', 0))}, lost={int(flags.get('lost', 0))}, "
         f"new={int(flags.get('new', 0))}, neither={int(flags.get('neither', 0))}."),
        ("Target/seed paired-SD ratio: median "
         f"{ratio.median():.3f}; range {ratio.min():.3f}--{ratio.max():.3f} "
         f"over {ratio.notna().sum()} nonzero-denominator contrasts."),
        "",
        "Percentile spans are observed distribution percentiles, not CIs, p-values, or",
        "multiplicity-adjusted tests. The two distributions are conditional on different",
        "perturbations; their SDs are not combined and this is not a total-uncertainty claim.",
        "The refit CSV covers the richest dynamic tier, while headline radius tables use the",
        "richest structural tier. Results here do not alter headline stars or all-star claims.",
        "",
        "Input/source SHA-256 (repository-relative labels):",
        *[f"SHA256 {sha256(source)}  {source.as_posix()}" for source in input_paths],
        f"SHA256 {sha256(csv_path)}  {csv_path.as_posix()}",
        "",
        "Per contrast (gain = tau(r+1) - tau(r); variance identity = var(lower) +",
        "var(upper) - 2*covariance):",
        out.to_csv(index=False, float_format="%.9g"),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    out = run_analysis()
    result_dir = Path("results")
    result_dir.mkdir(exist_ok=True)
    csv_path = result_dir / "results_paired_target_noise.csv"
    report_path = result_dir / "RESULTS_paired_target_noise.txt"
    out.to_csv(csv_path, index=False)
    inputs = [Path("results_target_noise_refit.csv"),
              *[Path(f"sweep_{network}.csv") for network in NETWORKS],
              Path(__file__).resolve().relative_to(Path.cwd())]
    write_report(out, report_path, inputs, csv_path)
    print(f"Wrote {csv_path} and {report_path}")
    print(out.flag_change.value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

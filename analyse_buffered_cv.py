"""Descriptive analysis for the authenticated Phase 6 buffered-CV follow-up."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyse
from probe_buffered_cv import (COMPLETE, NETWORKS, PROTOCOL, RADII, RESULTS_MANIFEST_PATH, SEEDS, TARGETS,
                               digest_file, stable_digest)


ARMS = ("region", "buffer_b1", "control_b1", "buffer_measured", "control_measured")
PAIRS = (("buffer_b1", "region"), ("control_b1", "region"),
         ("buffer_measured", "region"), ("control_measured", "region"),
         ("buffer_b1", "control_b1"), ("buffer_measured", "control_measured"))
GEOMETRY_LABEL = "separate_reference_different_split_geometry_random_kfold_vs_bfs_region"


def _cell_key_strings(frame: pd.DataFrame) -> list[str]:
    return sorted("|".join(map(str, row)) for row in frame[["network", "target", "radius", "seed", "logical_arm"]]
                  .itertuples(index=False, name=None))


def validate_cells(frame: pd.DataFrame) -> None:
    """Reject unauthenticated, mixed, missing, or duplicate logical cell rows."""
    required = {"network", "target", "radius", "seed", "logical_arm", "status", "kendall_tau",
                "configuration_sha256", "preflight_identity_sha256", "row_sha256"}
    if missing := required.difference(frame.columns):
        raise ValueError(f"buffered cell CSV missing {sorted(missing)}")
    key = ["network", "target", "radius", "seed", "logical_arm"]
    if frame.duplicated(key).any():
        raise ValueError("buffered cell CSV contains duplicate logical keys")
    expected = {(network, target, radius, seed, arm) for network in NETWORKS for target in TARGETS
                for radius in RADII for seed in SEEDS for arm in ARMS}
    observed = set(map(tuple, frame[key].itertuples(index=False, name=None)))
    if observed != expected:
        raise ValueError(f"buffered cell key set differs; missing={len(expected - observed)}, extra={len(observed - expected)}")
    for column in ("configuration_sha256", "preflight_identity_sha256"):
        if frame[column].nunique(dropna=False) != 1 or not isinstance(frame[column].iloc[0], str):
            raise ValueError(f"buffered cells mix or lack {column}")
    for row in frame.to_dict("records"):
        digest = row.pop("row_sha256")
        if not isinstance(digest, str) or digest != stable_digest(row):
            raise ValueError("buffered cell row digest differs")


def validate_result_manifest(cells_path: Path, frame: pd.DataFrame,
                             manifest_path: Path = RESULTS_MANIFEST_PATH) -> None:
    """Bind analysis to final packaged CSV/OOF artifacts from one preflight."""
    if not manifest_path.is_file():
        raise ValueError("buffered results manifest is required for analysis")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    claimed = manifest.get("results_sha256")
    unsigned = dict(manifest)
    unsigned.pop("results_sha256", None)
    if claimed != stable_digest(unsigned):
        raise ValueError("buffered results manifest digest differs")
    if manifest.get("protocol") != PROTOCOL:
        raise ValueError("buffered results manifest protocol differs")
    if manifest.get("cells_csv") != cells_path.as_posix() or manifest.get("cells_sha256") != digest_file(cells_path):
        raise ValueError("cells CSV differs from final buffered manifest")
    if manifest.get("configuration_sha256") != frame.configuration_sha256.iloc[0]:
        raise ValueError("cells configuration differs from final buffered manifest")
    if manifest.get("preflight_identity_sha256") != frame.preflight_identity_sha256.iloc[0]:
        raise ValueError("cells preflight identity differs from final buffered manifest")
    if manifest.get("expected_logical_cell_keys") != _cell_key_strings(frame):
        raise ValueError("cells logical-key set differs from final buffered manifest")
    oof_path = Path(manifest.get("oof_manifest", ""))
    if not oof_path.is_file() or manifest.get("oof_manifest_sha256") != digest_file(oof_path):
        raise ValueError("OOF manifest differs from final buffered manifest")
    oof = json.loads(oof_path.read_text(encoding="utf-8"))
    if (oof.get("protocol") != PROTOCOL
            or oof.get("configuration_sha256") != manifest["configuration_sha256"]
            or oof.get("preflight_identity_sha256") != manifest["preflight_identity_sha256"]):
        raise ValueError("OOF manifest provenance differs")
    observed_oof: set[str] = set()
    for network, record in oof.get("archives", {}).items():
        path = Path(record.get("path", ""))
        if not path.is_file() or record.get("sha256") != digest_file(path):
            raise ValueError(f"OOF archive differs for {network}")
        with np.load(path) as archive:
            if set(archive.files) != set(record.get("keys", [])):
                raise ValueError(f"OOF archive key set differs for {network}")
        observed_oof.update(record["keys"])
    if sorted(observed_oof) != manifest.get("completed_oof_keys"):
        raise ValueError("completed OOF key set differs from final buffered manifest")


def descriptive_contrasts(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute only predeclared within-seed descriptive contrasts."""
    validate_cells(frame)
    rows: list[dict] = []
    for network in NETWORKS:
        for target in TARGETS:
            for radius in RADII:
                block = frame[(frame.network == network) & (frame.target == target) & (frame.radius == radius)]
                for left, right in PAIRS:
                    lhs = block[block.logical_arm == left].set_index("seed").sort_index()
                    rhs = block[block.logical_arm == right].set_index("seed").sort_index()
                    if not lhs.index.equals(pd.Index(SEEDS)) or not rhs.index.equals(pd.Index(SEEDS)):
                        raise ValueError("seed alignment changed after cell-key validation")
                    complete = (lhs.status == COMPLETE).all() and (rhs.status == COMPLETE).all()
                    # Task 6 finding P2-10(a) (Claude Opus 5, 2026-09-11). When
                    # the measured buffer is 1 the *_measured arm is an ALIAS
                    # of the *_b1 arm (same folds, same predictions, copied
                    # digest), so its contrast against `region` repeats the
                    # b1 contrast number for number, and (buffer_measured,
                    # control_measured) repeats (buffer_b1, control_b1). Those
                    # rows are kept - the table is predeclared as one row per
                    # (cell, pair) - but flagged, so prose counts contrasts
                    # that are independent measurements and not rows.
                    alias_arms = []
                    for arm_name, block_rows in ((left, lhs), (right, rhs)):
                        if "canonical_arm" in block_rows.columns and (block_rows.canonical_arm != arm_name).any():
                            alias_arms.append(arm_name)
                    canon_left = str(lhs.canonical_arm.iloc[0]) if left in alias_arms else left
                    canon_right = str(rhs.canonical_arm.iloc[0]) if right in alias_arms else right
                    base = {"network": network, "target": target, "radius": radius,
                            "left_arm": left, "right_arm": right, "n_seeds": len(SEEDS),
                            "is_alias": bool(alias_arms),
                            "alias_of_pair": f"{canon_left}|{canon_right}" if alias_arms else ""}
                    if not complete:
                        rows.append({**base, "status": "unscored_incomplete_or_infeasible",
                                     "mean_left": np.nan, "mean_right": np.nan, "mean_difference": np.nan,
                                     "sd_difference": np.nan, "covariance": np.nan,
                                     "descriptive_abs_mean_gt_2sd": False})
                        continue
                    left_values, right_values = lhs.kendall_tau.to_numpy(float), rhs.kendall_tau.to_numpy(float)
                    if not np.isfinite(left_values).all() or not np.isfinite(right_values).all():
                        raise ValueError("complete buffered cell has a nonfinite tau")
                    difference = left_values - right_values
                    sd = float(np.std(difference, ddof=1))
                    rows.append({**base, "status": "scored", "mean_left": float(left_values.mean()),
                                 "mean_right": float(right_values.mean()), "mean_difference": float(difference.mean()),
                                 "sd_difference": sd, "covariance": float(np.cov(left_values, right_values, ddof=1)[0, 1]),
                                 "descriptive_abs_mean_gt_2sd": bool(abs(float(difference.mean())) > 2 * sd)})
    return pd.DataFrame(rows)


def reported_random_cv_reference() -> pd.DataFrame:
    """Read the published random-CV result separately, preserving its geometry label."""
    rows: list[dict] = []
    for network in NETWORKS:
        root = Path(f"sweep_{network}.csv")
        log1p = Path(analyse.REPORTED_BETWEENNESS.format(tag=network))
        if not root.is_file() or not log1p.is_file():
            raise FileNotFoundError(f"reported random-CV source missing for {network}")
        reported = analyse.load(network)
        for target in TARGETS:
            source = log1p if target == "betweenness" else root
            subset = reported[(reported.target == target) & (reported.richness == analyse.FULL)]
            for radius in RADII:
                values = subset[subset.radius == radius].sort_values("seed")
                if not values.seed.to_list() == list(SEEDS) or len(values) != len(SEEDS):
                    raise ValueError(f"reported random-CV rows are incomplete for {network}/{target}/r{radius}")
                rows.append({"network": network, "target": target, "radius": radius,
                             "reference": "reported_random_cv", "geometry": GEOMETRY_LABEL,
                             "n_seeds": len(SEEDS), "mean_kendall_tau": float(values.kendall_tau.mean()),
                             "sd_kendall_tau": float(values.kendall_tau.std(ddof=1)),
                             "source_path": source.as_posix(), "source_sha256": digest_file(source),
                             "reported_objective": "rf_log1p" if target == "betweenness" else "reported_root"})
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", default="results/phase6_buffered_cv_cells.csv")
    parser.add_argument("--manifest", default=RESULTS_MANIFEST_PATH.as_posix())
    parser.add_argument("--out", default="results/phase6_buffered_cv_analysis.csv")
    parser.add_argument("--random-reference-out", default="results/phase6_buffered_cv_reported_random_reference.csv")
    args = parser.parse_args()
    cells_path = Path(args.cells)
    cells = pd.read_csv(cells_path, float_precision="round_trip")
    validate_cells(cells)
    validate_result_manifest(cells_path, cells, Path(args.manifest))
    result = descriptive_contrasts(cells)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    reference = reported_random_cv_reference()
    reference.to_csv(args.random_reference_out, index=False)
    n_alias = int(result.is_alias.sum()) if "is_alias" in result.columns else 0
    print(f"Wrote {output} ({len(result)} descriptive contrast rows, of which {n_alias} are alias "
          f"duplicates of a b1 row and {len(result) - n_alias} are distinct measurements) and "
          f"{args.random_reference_out} (separate random-CV reference).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

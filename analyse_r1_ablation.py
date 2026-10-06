"""Paired analyzer for the Phase 6 radius-one structural ablation.

Created 2026-09-10 by Claude Opus 5 for Phase 6 Task 5 (r=1 ablation scope gap).
Specification: docs/phase6_r1_ablation_implementation_brief.md Task 3.

WHAT THIS COMPUTES, AND WHAT IT REFUSES TO
------------------------------------------
Three nested contrasts per (network, target), ten same-seed pairs each:

    node_edge -> +non-orbit subgraph -> +node orbits index <15 -> +the rest

5 networks x 4 targets x 3 contrasts = exactly 60 rows.

`heuristic_star = abs(mean_gain) > 2 * paired_sd` is a DESCRIPTIVE flag, not a
test. There is no null distribution here, no multiplicity correction and no
p-value; ten seeds resampled from one graph are not ten independent graphs. The
report says so in its own text, because a star in a table gets quoted long
after the caveat in the prose is forgotten.

`pivot_table` is deliberately not used anywhere below: it silently AVERAGES
duplicate rows, so a corpus containing the same cell twice would produce a
plausible number instead of an error. Duplicates are rejected first.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from influence.r1_ablation import (
    NETWORKS,
    SEEDS,
    SET_IDS,
    TARGETS,
    R1ContractError,
    cell_name,
    expected_keys,
    sort_key,
)
from probe_r1_ablation import (
    DEFAULT_OUT,
    R1RunError,
    read_verified_cell,
    validate_manifest,
    write_atomic_json,
)

CONTRASTS = (
    ("add_nonorbit_subgraph", "node_edge", "plus_nonorbit_subgraph"),
    ("add_orbit_lt15", "plus_nonorbit_subgraph", "plus_orbit_lt15"),
    ("add_remaining_g5_orbits", "plus_orbit_lt15", "full_r1_structural"),
)

CELL_COLUMNS = ("network", "target", "set_id", "seed", "radius", "n_splits",
                "objective_id", "n_rows", "n_columns", "columns_sha256",
                "target_sha256", "fold_digest", "kendall_tau", "fit_seconds")


def load_complete_cells(root: Path) -> pd.DataFrame:
    """Read all 800 cells, validating each against the immutable manifest.

    A partial corpus is an INCOMPLETE RUN, not a smaller result: reporting 700
    cells as if they were the design would silently change which seeds and
    networks the conclusions rest on.
    """
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise R1RunError(f"no manifest at {manifest_path}; nothing to analyse")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(root, manifest)
    run_id = manifest["run_id"]

    wanted = expected_keys(tuple(manifest["networks"]))
    rows: list[dict] = []
    seen: set[tuple[str, str, str, int]] = set()

    for path in sorted((root / "cells").glob("*.json")):
        record = read_verified_cell(path, run_id)
        key = (record["network"], record["target"], record["set_id"], record["seed"])
        if key not in wanted:
            raise R1RunError(f"{path.name}: cell outside the declared grid")
        if key in seen:
            raise R1RunError(f"{path.name}: duplicate cell key {key}")
        seen.add(key)
        if "kendall_tau" not in record["metrics"]:
            raise R1RunError(f"{path.name}: no kendall_tau metric")
        rows.append({
            "network": record["network"], "target": record["target"],
            "set_id": record["set_id"], "seed": record["seed"],
            "radius": record["radius"], "n_splits": record["n_splits"],
            "objective_id": record["objective_id"],
            "n_rows": record["n_rows"], "n_columns": record["n_columns"],
            "columns_sha256": record["columns_sha256"],
            "target_sha256": record["target_sha256"],
            "fold_digest": record["fold_digest"],
            "kendall_tau": float(record["metrics"]["kendall_tau"]),
            "fit_seconds": float(record["fit_seconds"]),
        })

    missing = wanted - seen
    if missing:
        raise R1RunError(
            f"incomplete corpus: {len(missing)} of {len(wanted)} cells absent, "
            f"first {sorted(missing, key=lambda k: sort_key(*k))[0]}"
        )

    cells = pd.DataFrame(rows, columns=list(CELL_COLUMNS))
    cells = cells.iloc[[i for i, _ in sorted(
        enumerate(rows), key=lambda pair: sort_key(
            pair[1]["network"], pair[1]["target"], pair[1]["set_id"], pair[1]["seed"]))]]
    cells = cells.reset_index(drop=True)

    # Within one (network, target) every set must share the target vector and
    # the fold allocation, or a "gain" would be comparing different problems.
    for (network, target), block in cells.groupby(["network", "target"], sort=False):
        if block["objective_id"].nunique() != 1:
            raise R1RunError(f"{network}/{target}: mixed objective ids")
        if block["target_sha256"].nunique() != 1:
            raise R1RunError(f"{network}/{target}: mixed target vectors")
        for seed, seed_block in block.groupby("seed", sort=False):
            if seed_block["fold_digest"].nunique() != 1:
                raise R1RunError(f"{network}/{target}/s{seed}: mixed fold allocations")
    return cells


def paired_contrasts(cells: pd.DataFrame) -> pd.DataFrame:
    """Align the ten same-seed tau values per contrast and describe the gain."""
    lookup: dict[tuple[str, str, str, int], float] = {
        (row.network, row.target, row.set_id, int(row.seed)): float(row.kendall_tau)
        for row in cells.itertuples()
    }
    out: list[dict] = []
    for network in NETWORKS:
        for target in TARGETS:
            for name, lower, upper in CONTRASTS:
                gains = []
                for seed in SEEDS:
                    low_key = (network, target, lower, seed)
                    high_key = (network, target, upper, seed)
                    if low_key not in lookup or high_key not in lookup:
                        raise R1RunError(
                            f"{network}/{target}/{name}: seed {seed} missing an endpoint")
                    gains.append(lookup[high_key] - lookup[low_key])
                values = np.asarray(gains, dtype=np.float64)
                if not np.all(np.isfinite(values)):
                    raise R1RunError(f"{network}/{target}/{name}: nonfinite gain")
                mean_gain = float(values.mean())
                paired_sd = float(values.std(ddof=1))
                out.append({
                    "network": network, "target": target, "contrast": name,
                    "lower_set": lower, "upper_set": upper,
                    "n_pairs": len(values),
                    "mean_gain": mean_gain,
                    "paired_sd": paired_sd,
                    "positive_count": int((values > 0).sum()),
                    "zero_count": int((values == 0).sum()),
                    "negative_count": int((values < 0).sum()),
                    # Strict greater-than: equality is NOT a star.
                    "heuristic_star": bool(abs(mean_gain) > 2 * paired_sd),
                })
    if len(out) != len(NETWORKS) * len(TARGETS) * len(CONTRASTS):
        raise R1RunError(f"expected 60 contrasts, built {len(out)}")
    return pd.DataFrame(out)


def _write_csv_atomic(path: Path, frame: pd.DataFrame) -> None:
    import os
    import uuid
    temp = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        frame.to_csv(stream, index=False, lineterminator="\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def _report_text(root: Path, cells: pd.DataFrame, pairs: pd.DataFrame) -> str:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    lines: list[str] = []
    add = lines.append
    add("Phase 6 -- radius-one structural ablation")
    add("=========================================")
    add("")
    # Dates come from the manifest, not a literal (Task 6 finding P2-10(b)):
    # the run's own timestamp is the one a reader can cross-check.
    add(f"Run created {manifest.get('created_utc', '<created_utc missing>')} by "
        f"{manifest.get('created_by', '<created_by missing>')}; report produced "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} by analyse_r1_ablation.py.")
    add(f"run_id: {manifest['run_id']}")
    add("")
    add("SCOPE AND PROVENANCE")
    add("--------------------")
    add(f"{len(cells)} cells: {len(NETWORKS)} networks x {len(TARGETS)} targets x "
        f"{len(SET_IDS)} nested feature sets x {len(SEEDS)} paired seeds.")
    add("Every cell is a FRESH five-fold out-of-fold fit bound to the manifest.")
    add("No historical cache_oof endpoint was reused: those archives carry bare")
    add("prediction keys with no manifest, no column list or hash, no fold digest")
    add("and no objective id, and the root betweenness endpoint belongs to the RAW")
    add("objective while this report uses rf_log1p.")
    add("")
    add("This covers RADIUS ONE ONLY. It says nothing about any other radius.")
    add("")
    add("HOW TO READ THE STARS")
    add("---------------------")
    add("heuristic_star = abs(mean_gain) > 2 * paired_sd, over ten seeds.")
    add("It is DESCRIPTIVE. There is no null distribution, no multiplicity")
    add("correction and no p-value. Ten seeds on one graph are not ten graphs.")
    add("")
    add("RESULTS BY NETWORK -- read these per graph, not as one claim")
    add("------------------------------------------------------------")
    for network in NETWORKS:
        add("")
        add(f"{network}")
        block = pairs[pairs.network == network]
        for _, row in block.iterrows():
            star = "*" if row.heuristic_star else " "
            add(f"  {star} {row.target:<14} {row.contrast:<26} "
                f"mean {row.mean_gain:+.5f}  sd {row.paired_sd:.5f}  "
                f"(+{row.positive_count}/0:{row.zero_count}/-{row.negative_count})")
    add("")
    add("SUMMARY OF FLAGS PER CONTRAST")
    add("-----------------------------")
    for name, _lower, _upper in CONTRASTS:
        block = pairs[pairs.contrast == name]
        flagged = block[block.heuristic_star]
        add(f"  {name}: {len(flagged)} of {len(block)} (network, target) cells flagged")
        if len(flagged):
            add("    flagged: " + ", ".join(
                f"{row.network}/{row.target}" for _, row in flagged.iterrows()))
        nulls = block[~block.heuristic_star]
        if len(nulls):
            add("    not flagged: " + ", ".join(
                f"{row.network}/{row.target}" for _, row in nulls.iterrows()))
    add("")
    add("QUALIFICATION -- REQUIRED")
    add("-------------------------")
    add("These effects are qualified BY GRAPH. A contrast that is flagged on some")
    add("networks and null on others is exactly that, and must not be restated as")
    add("a universal claim about structural expressive power. Null and")
    add("contradictory per-network effects above are retained, not dropped.")
    add("")
    add("This file does not alter Finding 3 or any study prose. Reconciliation is")
    add("a separate step and happens only against these measured artifacts.")
    add("")
    return "\n".join(lines)


def write_final_artifacts(root: Path, cells: pd.DataFrame, pairs: pd.DataFrame) -> None:
    import os
    import uuid
    _write_csv_atomic(root / "cells.csv", cells)
    _write_csv_atomic(root / "paired.csv", pairs)
    text = _report_text(root, cells, pairs)
    path = root / "RESULTS_r1_ablation.txt"
    temp = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyse the Phase 6 r=1 structural ablation (60 paired contrasts).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cells = load_complete_cells(args.out)
    pairs = paired_contrasts(cells)
    write_final_artifacts(args.out, cells, pairs)
    flagged = int(pairs.heuristic_star.sum())
    print(f"{len(cells)} cells -> {len(pairs)} contrasts, {flagged} flagged", flush=True)
    print(f"wrote {args.out / 'cells.csv'}, {args.out / 'paired.csv'}, "
          f"{args.out / 'RESULTS_r1_ablation.txt'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (R1RunError, R1ContractError) as error:
        print(f"analyse_r1_ablation.py: error: {error}", file=sys.stderr)
        sys.exit(2)

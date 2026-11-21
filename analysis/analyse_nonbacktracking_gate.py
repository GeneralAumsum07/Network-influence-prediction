"""
Iterative-metrics lane (L2): the R^2 reconstruction gate for the truncated
non-backtracking walk counts.

    python analysis/analyse_nonbacktracking_gate.py

Specification: docs/prereg/prereg_phase6_5_lanes.md - the 2026-09-12
clarification ("R^2 uses that existing held-out protocol, including max 4000
rows and seed 0"), the lane text ("register from r=2 and gate on
analyse_features' new-information R^2 before any fit") and the iterative-metrics
execution definitions (2026-09-13 18:11):

  * threshold inherited from analyse_features.DERIVED_R2 = 0.999;
    R^2 >= 0.999 marks the candidate reconstructible, undefined R^2 cannot pass;
  * predictors: existing NODE-tier features available at the candidate's
    declared information radius; the candidate itself is excluded;
  * 4,000-row maximum, seed 0, 30% held-out HGB protocol.

WHICH CANDIDATES
----------------
nb_walks_1 is degree, so it is not gated. "Register from r=2" is read as the
walk-length index, so nb_walks_2 (information radius 1) and nb_walks_3
(information radius 2) are both gated. nb_walks_3 is in scope under either
reading of "r"; nb_walks_2 is in scope only under the walk-length reading, and
the output says so rather than picking one silently.

WHY THERE IS A SECOND, EXACT CHECK
----------------------------------
nb_walks_2 = sum over neighbours v of (deg(v) - 1) = nbr_degree_sum - degree,
an exact identity in two cached radius-1 node features. analyse_features'
own docstring warns that a tree probe UNDERSTATES exact algebraic relations
(triangle_count scored 0.998, not 1.0). So the HGB verdict is reported as
registered, and beside it, descriptively, the maximum absolute error of the
closed form. The exact check never changes the registered verdict; it is there
so a "pass" that is really an identity cannot be read as new information.

WHAT IT DOES NOT ANSWER
-----------------------
A pass makes a network eligible for an add-one fit. It is not evidence the
feature helps ("reconstructible is not accessible" holds in both directions).
The add-one fit itself has no registered protocol - no target, tier, seed count
or pairing is written down - so none runs here.

Fits: 2 per network, 10 in all, seconds.
"""
from __future__ import annotations

import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from analyse_features import DERIVED_R2, MAX_ROWS, predictability

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase6_5_nonbacktracking"
TAGS = ("ca-GrQc", "ca-HepTh", "p2p-Gnutella08", "email-Eu-core", "facebook_combined")
# Walk length L has information radius L - 1 under this repo's convention
# (2026-09-12 clarification: length 1 is degree, radius 0).
CANDIDATES = {"nb_walks_2": 1, "nb_walks_3": 2}
TIER = "node"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate(tag: str) -> dict:
    status = json.loads((OUT / f"{tag}.json").read_text(encoding="utf-8"))
    data_path = OUT / f"{tag}.npz"
    # Gate only the scored full run, and only if its bytes are the ones the
    # status file vouches for - otherwise the R^2 would sit beside numbers
    # nobody can trace back to the scored standalone addendum.
    if status.get("status") != "complete" or status.get("pilot"):
        raise ValueError(f"{tag}: probe output is not a complete full run")
    if sha(data_path) != status["output_sha256"]:
        raise ValueError(f"{tag}: probe output hash differs from its status file")
    feat_path = ROOT / f"data/cache/cache_features_{tag}.csv"
    # The candidate was computed against this feature cache; if the cache has
    # been regenerated since, node order or values may differ. Refuse rather
    # than gate against a different table.
    if sha(feat_path) != status["identity"]["inputs"]["features"]["sha256"]:
        raise ValueError(f"{tag}: feature cache changed since the standalone run")
    feats = pd.read_csv(feat_path)
    reg = pd.read_csv(ROOT / f"data/cache/cache_registry_{tag}.csv")
    reg = reg[reg.feature.isin(feats.columns)]

    with np.load(data_path, allow_pickle=False) as d:
        node = d["node"]
        cand = {c: d[c].astype(np.float64) for c in CANDIDATES}
    if not np.array_equal(node, feats["node"].to_numpy()):
        raise ValueError(f"{tag}: probe nodes and cache rows are not aligned")

    n = len(feats)
    # Same subsample analyse_features.analyse draws, so the rows are the
    # registered ones and not a fresh draw per candidate.
    rng = np.random.default_rng(0)
    idx = rng.choice(n, MAX_ROWS, replace=False) if n > MAX_ROWS else np.arange(n)

    rows = {}
    for c, radius in CANDIDATES.items():
        preds = sorted(reg.loc[(reg.tier == TIER) & (reg.hop <= radius)
                               & (reg.feature != c), "feature"])
        X = feats[preds].to_numpy(dtype=np.float64)
        r2 = predictability(X[idx], cand[c][idx], seed=0)
        verdict = ("unscored" if not np.isfinite(r2)
                   else "reconstructible" if r2 >= DERIVED_R2 else "pass")
        rows[c] = {"information_radius": radius, "n_predictors": len(preds),
                   "predictors": preds,
                   "r2": None if not np.isfinite(r2) else float(r2), "verdict": verdict}

    # Descriptive only: the closed form for nb_walks_2 (see module docstring).
    closed = feats["nbr_degree_sum"].to_numpy(np.float64) - feats["degree"].to_numpy(np.float64)
    rows["nb_walks_2"]["closed_form"] = {
        "formula": "nbr_degree_sum - degree",
        "max_abs_error": float(np.abs(closed - cand["nb_walks_2"]).max())}

    return {"network": tag, "n": n, "rows_used": int(len(idx)), "gate": rows,
            "inputs": {"probe_output_sha256": status["output_sha256"],
                       "cache_features_sha256": sha(feat_path),
                       "cache_registry_sha256": sha(ROOT / f"data/cache/cache_registry_{tag}.csv")}}


def main() -> int:
    results = {tag: gate(tag) for tag in TAGS}
    out = {"registered_in": "prereg 2026-09-12 clarification; lane text (iterative metrics); "
                            "iterative-metrics execution definitions 2026-09-13 18:11",
           "protocol": {"function": "analyse_features.predictability", "max_rows": MAX_ROWS,
                        "seed": 0, "held_out": 0.3, "threshold": DERIVED_R2,
                        "rule": "R2 >= threshold -> reconstructible; undefined -> unscored",
                        "predictors": f"tier == '{TIER}' and hop <= candidate radius"},
           "scope_note": "nb_walks_3 is gated under either reading of 'register from r=2'; "
                         "nb_walks_2 only under the walk-length reading",
           "closed_form_note": "descriptive; does not change the registered verdict",
           "add_one": "NOT RUN: no registered add-one protocol (target, tier, seeds, pairing)",
           "networks": results}
    tmp = OUT / "gate.json.tmp"
    tmp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, OUT / "gate.json")
    fmt = lambda v: "   n/a" if v is None else f"{v:.4f}"
    for tag, r in results.items():
        g = r["gate"]
        print(f"{tag:18s} NB2 R2={fmt(g['nb_walks_2']['r2'])} ({g['nb_walks_2']['verdict']}, "
              f"{g['nb_walks_2']['n_predictors']} preds, closed-form err "
              f"{g['nb_walks_2']['closed_form']['max_abs_error']:.3g})  "
              f"NB3 R2={fmt(g['nb_walks_3']['r2'])} ({g['nb_walks_3']['verdict']}, "
              f"{g['nb_walks_3']['n_predictors']} preds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

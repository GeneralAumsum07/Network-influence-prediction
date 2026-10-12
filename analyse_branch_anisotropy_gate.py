"""
Phase 6.5 L7: the R^2 reconstruction gate for the two branch-anisotropy
features, plus the tail-boundary tie count the 2026-10-13 run-status
addendum promised.

    python analyse_branch_anisotropy_gate.py

Specification: docs/prereg/prereg_phase6_5_lanes.md, the 2026-09-12
clarification ("R^2 uses that existing held-out protocol, including max 4000
rows and seed 0"), the L7 execution definitions (2026-09-13 18:17) and the L7
run status (2026-10-13 01:56).

WHAT THE GATE ASKS
------------------
Can max_branch_share or branch_entropy_nats be rebuilt from the features the
repo already has at radius <= 2 that describe the same thing: ego_betweenness
and the four edge_overlap_* summaries? If so (R^2 >= 0.95), the feature adds
no new information and the lane's counter says drop it.

The probe is `analyse_features.predictability`, imported rather than copied:
an HGB regressor, max_iter 120, 70/30 split, seed 0, scored on held-out rows.
The row subsample repeats `analyse_features.analyse` exactly:
default_rng(0).choice(n, 4000, replace=False) when n > 4000. Each candidate
is reconstructed on its own.

WHAT IT DOES NOT ANSWER
-----------------------
A pass makes a network eligible for an add-one fit. It is not evidence that
the feature helps. Vault gotcha: "reconstructible is not accessible" (a
column at R^2 ~ 0.99 was still worth +0.117 tau), and the converse holds as
well. No add-one protocol is registered yet, so none runs (addendum part B).

Fits: 2 per network, 10 in all, a few seconds.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from analyse_features import MAX_ROWS, predictability

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "phase6_5_anisotropy"
TAGS = ("ca-GrQc", "ca-HepTh", "p2p-Gnutella08", "email-Eu-core", "facebook_combined")
CANDIDATES = ("max_branch_share", "branch_entropy_nats")
PREDICTORS = ("ego_betweenness", "edge_overlap_max", "edge_overlap_mean",
              "edge_overlap_min", "edge_overlap_std")
THRESHOLD = 0.95                    # R2 < 0.95 passes; >= 0.95 fails (registered)
MAX_GATE_HOP = 2                    # predictors available by radius 2
ARMS = ("primary_reported_betweenness", "sensitivity_raw_betweenness",
        "sensitivity_spread_mean")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate(tag: str) -> dict:
    status = json.loads((OUT / f"{tag}.json").read_text(encoding="utf-8"))
    data_path = OUT / f"{tag}.npz"
    # Only a completed, uncorrupted full-run output is gated. A pilot or a
    # half-written file would put an R2 next to numbers nobody can trace.
    if status.get("status") != "complete" or status.get("pilot"):
        raise ValueError(f"{tag}: probe output is not a complete full run")
    if sha(data_path) != status["output_sha256"]:
        raise ValueError(f"{tag}: probe output hash differs from its status file")
    feats = pd.read_csv(ROOT / f"cache_features_{tag}.csv")
    reg = pd.read_csv(ROOT / f"cache_registry_{tag}.csv").set_index("feature")
    # The registry says which radius a column needs. A predictor beyond
    # radius 2 would be a different gate from the one registered.
    hops = {c: int(reg.loc[c, "hop"]) for c in PREDICTORS}
    if any(h > MAX_GATE_HOP for h in hops.values()):
        raise ValueError(f"{tag}: a gate predictor needs radius > 2: {hops}")

    with np.load(data_path, allow_pickle=False) as d:
        node = d["node"]
        cand = {c: d[c].astype(np.float64) for c in CANDIDATES}
        adjusted = {a: d[f"adjusted_delta_{a}"] for a in ARMS}
    if not np.array_equal(node, feats["node"].to_numpy()):
        raise ValueError(f"{tag}: probe nodes and cache rows are not aligned")

    X = feats[list(PREDICTORS)].to_numpy(dtype=np.float64)
    n = len(X)
    rng = np.random.default_rng(0)
    idx = rng.choice(n, MAX_ROWS, replace=False) if n > MAX_ROWS else np.arange(n)
    rows = {}
    for c in CANDIDATES:
        r2 = predictability(X[idx], cand[c][idx], seed=0)
        verdict = ("unscored" if not np.isfinite(r2)
                   else "pass" if r2 < THRESHOLD else "fail")
        rows[c] = {"r2": None if not np.isfinite(r2) else float(r2), "verdict": verdict}

    # Boundary ties (addendum part C): how many nodes share the adjusted
    # residual of the k-th node at either tail boundary. Zero means the tie
    # rule never decided membership.
    k = max(10, round(0.05 * n))
    ties = {}
    for a, adj in adjusted.items():
        s = np.sort(adj)
        ties[a] = {"over_boundary": int(np.sum(adj == s[k - 1]) - 1),
                   "under_boundary": int(np.sum(adj == s[n - k]) - 1)}
    return {"network": tag, "n": n, "rows_used": int(len(idx)), "predictors": hops,
            "gate": rows, "network_passes": any(r["verdict"] == "pass" for r in rows.values()),
            "tail_k": k, "boundary_ties": ties,
            "inputs": {"probe_output_sha256": status["output_sha256"],
                       "cache_features_sha256": sha(ROOT / f"cache_features_{tag}.csv")}}


def main() -> int:
    results = {tag: gate(tag) for tag in TAGS}
    out = {"registered_in": "prereg 2026-09-12 clarification; L7 execution definitions "
                            "2026-09-13 18:17; L7 run status 2026-10-13 01:56",
           "protocol": {"function": "analyse_features.predictability", "max_rows": MAX_ROWS,
                        "seed": 0, "threshold": THRESHOLD, "predictors": list(PREDICTORS)},
           "add_one": "NOT RUN: no registered protocol (run-status addendum part B)",
           "networks": results}
    tmp = OUT / "gate.json.tmp"
    tmp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, OUT / "gate.json")
    for tag, r in results.items():
        g = r["gate"]
        print(f"{tag:18s} R2 max_share={g['max_branch_share']['r2']:.3f} "
              f"({g['max_branch_share']['verdict']})  entropy={g['branch_entropy_nats']['r2']:.3f} "
              f"({g['branch_entropy_nats']['verdict']})  ties={r['boundary_ties']['primary_reported_betweenness']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

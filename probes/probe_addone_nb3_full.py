"""
NB3 full-tier follow-up: does nb_walks_3 still add to spread_mean once the edge
and subgraph tiers are in the base?

    python probes/probe_addone_nb3_full.py

Specification: docs/prereg/prereg_phase6_5_lanes.md, "NB3 full-tier follow-up -
execution definitions - 2026-11-21 18:33 IST". It differs from the 16:18 add-one
definitions only in the base set (node+edge+subgraph instead of node) and in
re-running the R^2 gate against that richer base.

WHY THIS FILE IMPORTS probe_addone_lanes INSTEAD OF EXTENDING IT
----------------------------------------------------------------
The committed add-one manifest records the sha256 of probe_addone_lanes.py as part
of its run_id. Adding a lane to that file would change its hash and leave the
committed manifest pointing at bytes that no longer exist. So the shared pieces
(atomic writes, the hash-checked candidate loader, the fit, the base check bound)
are imported unchanged, and this file's own hash goes into this run's manifest.

WHY THE GATE IS RE-RUN
----------------------
The 16:10 gate asked whether the NODE tier reconstructs NB3. Against the full tier
the model has more inputs, so NB3 can only get easier to reconstruct. The rule says
a reconstructible candidate (R^2 >= 0.999) is not fitted, so eligibility has to be
re-asked against exactly the columns the base model will see.
"""
from __future__ import annotations

import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from analyse_features import DERIVED_R2, MAX_ROWS, predictability
from influence.features import select_features
from influence.targets import assert_no_leakage
import probe_addone_lanes as lanes
from probe_addone_lanes import (BASE_TOL, AddOneError, canon, candidate_array,
                                fit_tau, sha, write_atomic)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase6_5_addone_nb3_full"
TAGS = lanes.TAGS
SEEDS = lanes.SEEDS
RADIUS = lanes.RADIUS
TARGET = "spread_mean"
TIERS = ("node", "edge", "subgraph")
RICHNESS = "node+edge+subgraph"     # the published sweep's label for this base
CANDIDATE = "nb_walks_3"
SWEEP = "data/cache/sweep_{tag}.csv"
# 17:00 node-tier gains (results/phase6_5_addone/summary.json). Read from the file at
# run time, not copied here, so the reading rule uses the committed numbers.
NODE_SUMMARY = ROOT / "results" / "phase6_5_addone" / "summary.json"
SOURCES = ("probes/probe_addone_nb3_full.py", "probes/probe_addone_lanes.py",
           "analysis/analyse_features.py", "influence/experiment.py",
           "influence/estimators.py", "influence/features.py")


def manifest() -> dict:
    inputs = {}
    for tag in TAGS:
        for p in (f"data/cache/cache_features_{tag}.csv", f"data/cache/cache_targets_{tag}.csv",
                  f"data/cache/cache_registry_{tag}.csv", SWEEP.format(tag=tag),
                  f"results/phase6_5_nonbacktracking/{tag}.npz",
                  f"results/phase6_5_nonbacktracking/{tag}.json"):
            inputs[p] = sha(ROOT / p)
    inputs["results/phase6_5_addone/summary.json"] = sha(NODE_SUMMARY)
    m = {"schema": "phase6_5_addone_nb3_full_manifest_v1",
         "prereg": "NB3 full-tier follow-up - execution definitions - 2026-11-21 18:33 IST",
         "target": TARGET, "tiers": list(TIERS), "candidate": CANDIDATE,
         "radius": RADIUS, "seeds": list(SEEDS), "base_tol": BASE_TOL,
         "gate_threshold": DERIVED_R2,
         "input_sha256": inputs, "source_sha256": {p: sha(ROOT / p) for p in SOURCES}}
    m["run_id"] = canon(m)
    return m


def gate_r2(X: np.ndarray, cand: np.ndarray) -> float:
    """Same probe and the same row draw as the 16:10 gate, on the full-tier columns."""
    n = len(cand)
    rng = np.random.default_rng(0)
    idx = rng.choice(n, MAX_ROWS, replace=False) if n > MAX_ROWS else np.arange(n)
    return float(predictability(X[idx], cand[idx], seed=0))


def published_tau(tag: str, seed: int, n_features: int) -> float:
    s = pd.read_csv(ROOT / SWEEP.format(tag=tag))
    row = s[(s.radius == RADIUS) & (s.richness == RICHNESS)
            & (s.target == TARGET) & (s.seed == seed)]
    if len(row) != 1:
        raise AddOneError(f"{tag}/s{seed}: {len(row)} published base rows, need 1")
    if int(row.n_features.iloc[0]) != n_features:
        raise AddOneError(f"{tag}/s{seed}: n_features {n_features} != published "
                          f"{int(row.n_features.iloc[0])}")
    return float(row.kendall_tau.iloc[0])


def main() -> int:
    m = manifest()
    OUT.mkdir(parents=True, exist_ok=True)
    mpath = OUT / "manifest.json"
    if mpath.is_file() and json.loads(mpath.read_text(encoding="utf-8"))["run_id"] != m["run_id"]:
        raise AddOneError("an input or source changed since the existing manifest; "
                          "refusing to resume into it")
    write_atomic(mpath, m)
    print(f"run_id {m['run_id']}", flush=True)

    cells = OUT / "cells"
    gate = {}
    for tag in TAGS:
        feats = pd.read_csv(ROOT / f"data/cache/cache_features_{tag}.csv")
        reg = pd.read_csv(ROOT / f"data/cache/cache_registry_{tag}.csv")
        y = pd.read_csv(ROOT / f"data/cache/cache_targets_{tag}.csv")[TARGET].to_numpy(np.float64)
        base = select_features(feats, reg, max_hop=RADIUS, tiers=TIERS)
        assert_no_leakage(base)
        if CANDIDATE in feats.columns:
            raise AddOneError(f"{CANDIDATE} is already a cached column; add-one is undefined")
        Xb = feats[base].to_numpy(np.float64)
        # "L2" only selects the source directory; the loader checks completeness,
        # the npz hash and node alignment exactly as in the 17:00 run.
        cand = candidate_array("L2", tag, CANDIDATE, feats["node"].to_numpy())

        r2 = gate_r2(Xb, cand)
        verdict = ("unscored" if not np.isfinite(r2)
                   else "reconstructible" if r2 >= DERIVED_R2 else "pass")
        gate[tag] = {"n_predictors": len(base), "r2": r2 if np.isfinite(r2) else None,
                     "verdict": verdict}
        print(f"gate {tag}: R2 {r2:.5f} -> {verdict}", flush=True)
        if verdict != "pass":
            continue

        sets = {"base": Xb, CANDIDATE: np.column_stack([Xb, cand])}
        for seed in SEEDS:
            for set_id, X in sets.items():
                path = cells / f"{tag}__{set_id}__s{seed}.json"
                if path.is_file():
                    rec = json.loads(path.read_text(encoding="utf-8"))
                    if rec.get("run_id") == m["run_id"]:
                        continue
                    raise AddOneError(f"{path.name}: belongs to another run_id")
                tau, secs = fit_tau(X, y, "rf", seed)
                rec = {"run_id": m["run_id"], "network": tag, "set_id": set_id,
                       "seed": seed, "target": TARGET, "objective": "rf",
                       "n_features": int(X.shape[1]), "kendall_tau": tau, "fit_seconds": secs}
                if set_id == "base":
                    pub = published_tau(tag, seed, X.shape[1])
                    rec["published_tau"] = pub
                    if abs(tau - pub) > BASE_TOL:
                        raise AddOneError(f"{tag}/s{seed}: base tau {tau!r} does not "
                                          f"reproduce the published {pub!r}")
                write_atomic(path, rec)
                print(f"{path.stem} tau={tau:.6f} {secs:.1f}s", flush=True)

    write_atomic(OUT / "gate.json", {"run_id": m["run_id"], "networks": gate})
    summarise(m, gate)
    return 0


def read_rule(g_full: float, g_node: float, positive: int) -> str:
    # Fixed in the 18:33 prereg section before any fit: absorbed below half the
    # node-tier gain; persists at or above half AND on >= 9/10 seeds; else mixed.
    if g_full < g_node / 2:
        return "absorbed"
    if positive >= 9:
        return "persists"
    return "mixed"


def summarise(m: dict, gate: dict) -> None:
    node = json.loads(NODE_SUMMARY.read_text(encoding="utf-8"))
    g_node = {r["network"]: r["gain_mean"] for r in node["lanes"]["L2"]["rows"]
              if r["candidate"] == CANDIDATE}
    cells = OUT / "cells"
    rows = []
    for tag in TAGS:
        if gate[tag]["verdict"] != "pass":
            rows.append({"network": tag, "eligible": False, "gate_r2": gate[tag]["r2"]})
            continue

        def tau(set_id, s):
            rec = json.loads((cells / f"{tag}__{set_id}__s{s}.json").read_text(encoding="utf-8"))
            if rec["run_id"] != m["run_id"]:
                raise AddOneError(f"{tag}/{set_id}/s{s}: stale cell")
            return rec["kendall_tau"]
        base = np.array([tau("base", s) for s in SEEDS])
        gain = np.array([tau(CANDIDATE, s) for s in SEEDS]) - base
        pos = int((gain > 0).sum())
        rows.append({"network": tag, "eligible": True, "gate_r2": gate[tag]["r2"],
                     "base_tau_mean": float(base.mean()),
                     "gain_mean": float(gain.mean()), "gain_sd": float(gain.std(ddof=1)),
                     "gain_min": float(gain.min()), "gain_max": float(gain.max()),
                     "seeds_positive": pos, "node_tier_gain": g_node[tag],
                     "ratio_to_node_tier": float(gain.mean() / g_node[tag]),
                     "reading": read_rule(float(gain.mean()), g_node[tag], pos)})
    write_atomic(OUT / "summary.json", {"run_id": m["run_id"], "prereg": m["prereg"],
                                        "target": TARGET, "base": RICHNESS, "radius": RADIUS,
                                        "candidate": CANDIDATE, "rows": rows})
    print(f"\n{CANDIDATE} on {TARGET}, base {RICHNESS} r={RADIUS}")
    for r in rows:
        if not r["eligible"]:
            print(f"  {r['network']:18s} not eligible (gate R2 {r['gate_r2']})")
            continue
        print(f"  {r['network']:18s} base {r['base_tau_mean']:.4f} gain {r['gain_mean']:+.5f} "
              f"sd {r['gain_sd']:.5f} [{r['gain_min']:+.5f},{r['gain_max']:+.5f}] "
              f"pos {r['seeds_positive']}/10 node {r['node_tier_gain']:+.5f} "
              f"ratio {r['ratio_to_node_tier']:.2f} -> {r['reading']}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AddOneError as err:
        print(f"probes/probe_addone_nb3_full.py: error: {err}", file=sys.stderr)
        sys.exit(2)

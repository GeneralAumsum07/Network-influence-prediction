"""
Add-one fits for the iterative-metrics (L2) and anisotropy (L7) lanes.

    python probes/probe_addone_lanes.py

Specification: docs/prereg/prereg_phase6_5_lanes.md, "Add-one execution
definitions (iterative metrics and anisotropy) - 2026-11-21 16:18 IST". Read
that section first; this docstring only explains the code's choices.

WHAT ONE "GAIN" IS
------------------
For a (network, candidate, seed): fit the base feature set, fit the base set
plus the one candidate column, and subtract the two Kendall taus.
(Each tau also carries ~1e-6 run-to-run noise from the n_jobs=-1 forest; see
BASE_TOL. That is far below anything the prereg scores.) Both fits use
the same seed, which in `out_of_fold_predictions` fixes BOTH the fold split and
the forest's randomness - so the only thing that differs between the pair is
the extra column. Averaging that paired difference over ten seeds is what the
prereg scores.

WHY THE BASE IS CHECKED AGAINST THE PUBLISHED SWEEP
---------------------------------------------------
The base fit IS a published sweep cell (same set, radius, estimator, seed). If
it does not reproduce that cell, something about the selection, column order or
estimator differs, and the "gain" would be measured from a base nobody has
published. So every base fit must match within BASE_TOL (1e-5 tau, see the note
at the constant for why it is not 1e-6), or the run stops before reporting
anything.

RESUME
------
Each fit is written as its own JSON cell, atomically, carrying the run_id (a
hash over every input and source file). A restart skips only cells whose
run_id matches; any change to an input or to this file changes the run_id and
the old cells are refused rather than silently reused.
"""
from __future__ import annotations

import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from influence.estimators import make_rf_log1p
from influence.experiment import evaluate, out_of_fold_predictions
from influence.features import select_features
from influence.targets import assert_no_leakage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase6_5_addone"
TAGS = ("ca-GrQc", "ca-HepTh", "p2p-Gnutella08", "email-Eu-core", "facebook_combined")
SEEDS = tuple(range(10))
RADIUS = 2
# Base-vs-published |dtau| bound. Was 1e-6, set from the single ~5e-8 observation
# documented in experiment.py; the first launch stopped on L7/ca-HepTh/s9 at 1.16e-6,
# and two refits of that cell differed from EACH OTHER by 3.4e-7 - the n_jobs=-1
# log1p forest is not reproducible to 1e-6 there. Amended to 1e-5 (prereg "Add-one
# base-check amendment", 2026-11-21 16:35): ~9x the worst observed run-to-run gap,
# ~100x below the seed spread, 500x below the 0.005 prediction bound.
BASE_TOL = 1e-5
PREDICTION_BOUND = 0.005  # L7: mean gain < 0.005 holds (registered 2026-09-12)

# One entry per lane. `sweep` is where the published base cell lives; the
# betweenness base comes from the reported (log1p) sweep, not the raw one.
LANES = {
    "L2": {"target": "spread_mean", "objective": "rf", "tiers": ("node",),
           "richness": "node", "sweep": "data/cache/sweep_{tag}.csv",
           "source_dir": "results/phase6_5_nonbacktracking",
           "candidates": ("nb_walks_2", "nb_walks_3"), "prediction": None},
    "L7": {"target": "betweenness", "objective": "rf_log1p",
           "tiers": ("node", "edge", "subgraph"), "richness": "node+edge+subgraph",
           "sweep": "estimators/sweep_{tag}__rf_log1p.csv",
           "source_dir": "results/phase6_5_anisotropy",
           "candidates": ("max_branch_share", "branch_entropy_nats"),
           "prediction": PREDICTION_BOUND},
}
SOURCES = ("probes/probe_addone_lanes.py", "influence/experiment.py",
           "influence/estimators.py", "influence/features.py")


class AddOneError(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canon(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def write_atomic(path: Path, record: dict) -> None:
    # Unique temp, fsync, replace: a crash leaves the old file or none, never half.
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True, indent=1, allow_nan=False))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def eligible(lane: str, tag: str) -> list[str]:
    """Candidates whose scored gate verdict is 'pass' on this network."""
    gate = json.loads((ROOT / LANES[lane]["source_dir"] / "gate.json").read_text(encoding="utf-8"))
    verdicts = gate["networks"][tag]["gate"]
    return [c for c in LANES[lane]["candidates"] if verdicts[c]["verdict"] == "pass"]


def candidate_array(lane: str, tag: str, name: str, nodes: np.ndarray) -> np.ndarray:
    """A candidate column, only from a complete, hash-verified, node-aligned output."""
    d = ROOT / LANES[lane]["source_dir"]
    status = json.loads((d / f"{tag}.json").read_text(encoding="utf-8"))
    if status.get("status") != "complete" or status.get("pilot"):
        raise AddOneError(f"{lane}/{tag}: source output is not a complete full run")
    if sha(d / f"{tag}.npz") != status["output_sha256"]:
        raise AddOneError(f"{lane}/{tag}: source output hash differs from its status file")
    with np.load(d / f"{tag}.npz", allow_pickle=False) as z:
        if not np.array_equal(z["node"], nodes):
            raise AddOneError(f"{lane}/{tag}: candidate nodes not aligned with the cache")
        col = z[name].astype(np.float64)
    if not np.all(np.isfinite(col)):
        raise AddOneError(f"{lane}/{tag}/{name}: nonfinite values")
    return col


def manifest() -> dict:
    inputs = {}
    for tag in TAGS:
        for p in (f"data/cache/cache_features_{tag}.csv", f"data/cache/cache_targets_{tag}.csv",
                  f"data/cache/cache_registry_{tag}.csv"):
            inputs[p] = sha(ROOT / p)
        for lane in LANES.values():
            for p in (lane["sweep"].format(tag=tag), f"{lane['source_dir']}/{tag}.npz",
                      f"{lane['source_dir']}/{tag}.json", f"{lane['source_dir']}/gate.json"):
                inputs[p] = sha(ROOT / p)
    m = {"schema": "phase6_5_addone_manifest_v1",
         "prereg": "Add-one execution definitions - 2026-11-21 16:18 IST",
         "radius": RADIUS, "seeds": list(SEEDS), "base_tol": BASE_TOL,
         "lanes": {k: {kk: (list(vv) if isinstance(vv, tuple) else vv)
                       for kk, vv in v.items()} for k, v in LANES.items()},
         "input_sha256": inputs, "source_sha256": {p: sha(ROOT / p) for p in SOURCES}}
    m["run_id"] = canon(m)
    return m


def fit_tau(X: np.ndarray, y: np.ndarray, objective: str, seed: int) -> tuple[float, int]:
    est = make_rf_log1p if objective == "rf_log1p" else None   # None = published default rf
    t0 = time.perf_counter()
    pred = out_of_fold_predictions(X, y, n_splits=5, seed=seed, estimator=est)
    secs = time.perf_counter() - t0
    tau = float(evaluate(y, pred)["kendall_tau"])
    if not np.isfinite(tau):
        raise AddOneError("undefined tau")
    return tau, secs


def published_tau(lane: str, tag: str, seed: int, n_features: int) -> float:
    cfg = LANES[lane]
    s = pd.read_csv(ROOT / cfg["sweep"].format(tag=tag))
    row = s[(s.radius == RADIUS) & (s.richness == cfg["richness"])
            & (s.target == cfg["target"]) & (s.seed == seed)]
    if len(row) != 1:
        raise AddOneError(f"{lane}/{tag}/s{seed}: {len(row)} published base rows, need 1")
    if int(row.n_features.iloc[0]) != n_features:
        raise AddOneError(f"{lane}/{tag}/s{seed}: n_features {n_features} != published "
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
    for lane, cfg in LANES.items():
        for tag in TAGS:
            feats = pd.read_csv(ROOT / f"data/cache/cache_features_{tag}.csv")
            reg = pd.read_csv(ROOT / f"data/cache/cache_registry_{tag}.csv")
            y = pd.read_csv(ROOT / f"data/cache/cache_targets_{tag}.csv")[cfg["target"]].to_numpy(np.float64)
            base = select_features(feats, reg, max_hop=RADIUS, tiers=cfg["tiers"])
            assert_no_leakage(base)
            Xb = feats[base].to_numpy(np.float64)
            nodes = feats["node"].to_numpy()
            sets = {"base": Xb}
            for c in eligible(lane, tag):
                if c in feats.columns:
                    raise AddOneError(f"{c} is already a cached column; add-one is undefined")
                sets[c] = np.column_stack([Xb, candidate_array(lane, tag, c, nodes)])
            for seed in SEEDS:
                for set_id, X in sets.items():
                    path = cells / f"{lane}__{tag}__{set_id}__s{seed}.json"
                    if path.is_file():
                        rec = json.loads(path.read_text(encoding="utf-8"))
                        if rec.get("run_id") == m["run_id"]:
                            continue
                        raise AddOneError(f"{path.name}: belongs to another run_id")
                    tau, secs = fit_tau(X, y, cfg["objective"], seed)
                    rec = {"run_id": m["run_id"], "lane": lane, "network": tag,
                           "set_id": set_id, "seed": seed, "target": cfg["target"],
                           "objective": cfg["objective"], "n_features": int(X.shape[1]),
                           "kendall_tau": tau, "fit_seconds": secs}
                    if set_id == "base":
                        pub = published_tau(lane, tag, seed, X.shape[1])
                        rec["published_tau"] = pub
                        if abs(tau - pub) > BASE_TOL:
                            raise AddOneError(f"{lane}/{tag}/s{seed}: base tau {tau!r} does not "
                                              f"reproduce the published {pub!r}")
                    write_atomic(path, rec)
                    print(f"{path.stem} tau={tau:.6f} {secs:.1f}s", flush=True)

    summarise(m)
    return 0


def summarise(m: dict) -> None:
    """Paired gains from the cells; the scored quantity is the mean over seeds."""
    cells = OUT / "cells"
    out = {"run_id": m["run_id"], "prereg": m["prereg"], "lanes": {}}
    for lane, cfg in LANES.items():
        rows = []
        for tag in TAGS:
            def tau(set_id, s):
                rec = json.loads((cells / f"{lane}__{tag}__{set_id}__s{s}.json").read_text(encoding="utf-8"))
                if rec["run_id"] != m["run_id"]:
                    raise AddOneError(f"{lane}/{tag}/{set_id}/s{s}: stale cell")
                return rec["kendall_tau"]
            base = np.array([tau("base", s) for s in SEEDS])
            for c in eligible(lane, tag):
                gain = np.array([tau(c, s) for s in SEEDS]) - base
                row = {"network": tag, "candidate": c, "base_tau_mean": float(base.mean()),
                       "gain_mean": float(gain.mean()), "gain_sd": float(gain.std(ddof=1)),
                       "gain_min": float(gain.min()), "gain_max": float(gain.max()),
                       "seeds_positive": int((gain > 0).sum())}
                if cfg["prediction"] is not None:
                    row["prediction_holds"] = bool(gain.mean() < cfg["prediction"])
                rows.append(row)
        entry = {"target": cfg["target"], "objective": cfg["objective"],
                 "base": cfg["richness"], "radius": RADIUS, "rows": rows}
        if cfg["prediction"] is not None:
            k = sum(r["prediction_holds"] for r in rows)
            entry["prediction"] = {"rule": f"mean paired gain < {cfg['prediction']}",
                                   "holds_on": k, "eligible": len(rows),
                                   "universal_holds": k == len(rows)}
        out["lanes"][lane] = entry
    write_atomic(OUT / "summary.json", out)
    for lane, e in out["lanes"].items():
        print(f"\n{lane} ({e['target']}, {e['objective']}, base {e['base']} r={RADIUS})")
        for r in e["rows"]:
            print(f"  {r['network']:18s} {r['candidate']:20s} gain {r['gain_mean']:+.5f} "
                  f"sd {r['gain_sd']:.5f} [{r['gain_min']:+.5f},{r['gain_max']:+.5f}] "
                  f"pos {r['seeds_positive']}/10" + (f" holds={r['prediction_holds']}"
                                                      if "prediction_holds" in r else ""))
        if "prediction" in e:
            print(f"  prediction: {e['prediction']}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AddOneError as err:
        print(f"probes/probe_addone_lanes.py: error: {err}", file=sys.stderr)
        sys.exit(2)

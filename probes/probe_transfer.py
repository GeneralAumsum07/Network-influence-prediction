"""
probes/probe_transfer.py
========================
Leave-one-graph-out transfer: train on four networks, rank the fifth.

Pre-registered in docs/prereg/prereg_transfer.md before any cell was fitted;
read that first. Scored by analysis/analyse_transfer.py.

WHAT A CELL IS
--------------
(target, held-out network, radius, seed). The model is the project's frozen
forest (`influence.estimators.make_rf`), trained on up to PER_NETWORK nodes
from each of the other four networks, with features restricted to the richest
structural tier at hop <= r. It predicts every node of the held-out network,
and the prediction is scored against that network's ORIGINAL target.

WHY THE TARGET IS RANK-ENCODED
------------------------------
Each network runs at 1.5 x its own beta_c, and its cascades live on a
different absolute scale (mean spread 1.8 nodes on ca-GrQc, 39 on
email-Eu-core). Pooling raw targets would ask the forest to learn those scale
differences from features that cannot see them. Replacing each network's
target with its within-network percentile rank is monotone per graph, so it
changes no ordering that Kendall tau can see, and it puts every training
graph on the same [0, 1] scale. It also makes a separate log1p arm for
betweenness unnecessary: the rank transform subsumes it.

RESUMING
--------
Each finished cell is appended to results/transfer/transfer_cells.csv at once.
A rerun skips cells already present, provided results/transfer/run_meta.json
records the same configuration and cache hashes; otherwise it refuses.

Run from the repository root:
    python probes/probe_transfer.py                      # the registered grid
    python probes/probe_transfer.py --seeds 1 --radii 3  # a quick partial run
    python probes/probe_transfer.py --drop degree_normalized --out results/transfer_nosize
                                                         # post-hoc arm 1 (prereg addendum 1)
    python probes/probe_transfer.py --feature-encoding rank --out results/transfer_featrank
                                                         # post-hoc arm 2 (prereg addendum 2)
"""
import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import argparse
import glob
import json
import os
import re
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from influence.estimators import make_rf
from influence.experiment import evaluate
from influence.preprocessing import file_sha256
from influence.targets import assert_no_leakage

TIERS = ("node", "edge", "subgraph")
OUT_DIR = os.path.join("results", "transfer")
CELLS = os.path.join(OUT_DIR, "transfer_cells.csv")
META = os.path.join(OUT_DIR, "run_meta.json")


def set_output(out_dir: str) -> None:
    """Point the run at its own folder (the post-hoc arm must not mix with the primary)."""
    global OUT_DIR, CELLS, META
    OUT_DIR = out_dir
    CELLS = os.path.join(OUT_DIR, "transfer_cells.csv")
    META = os.path.join(OUT_DIR, "run_meta.json")


def networks() -> list[str]:
    tags = []
    for p in sorted(glob.glob("data/cache/cache_registry_*.csv")):
        m = re.match(r"cache_registry_(.+)\.csv$", os.path.basename(p))
        if m:
            tags.append(m.group(1))
    return tags


def load_network(tag: str) -> dict:
    reg = pd.read_csv(f"data/cache/cache_registry_{tag}.csv")
    X = pd.read_csv(f"data/cache/cache_features_{tag}.csv")
    Y = pd.read_csv(f"data/cache/cache_targets_{tag}.csv")
    if len(X) != len(Y) or not (X["node"].to_numpy() == Y["node"].to_numpy()).all():
        raise ValueError(f"{tag}: feature and target rows do not align")
    return {"reg": reg, "X": X, "Y": Y}


def columns_at(reg: pd.DataFrame, X: pd.DataFrame, r: int,
               drop: tuple[str, ...] = ()) -> list[str]:
    sel = reg[(reg["hop"] <= r) & (reg["tier"].isin(TIERS))]
    return [c for c in sel["feature"] if c in X.columns and c not in drop]


def cache_hashes(tags: list[str]) -> dict[str, str]:
    out = {}
    for tag in tags:
        for kind in ("features", "targets", "registry"):
            p = f"data/cache/cache_{kind}_{tag}.csv"
            out[p] = file_sha256(p)
    return out


def bind_run(config: dict, tags: list[str]) -> None:
    """Record the run's configuration and inputs, or refuse a mismatched resume."""
    current = {"config": config, "inputs": cache_hashes(tags)}
    if os.path.exists(META):
        with open(META, encoding="utf-8") as fh:
            recorded = json.load(fh)
        if {k: recorded.get(k) for k in current} != current:
            raise SystemExit(f"REFUSING: {META} records a different configuration or "
                             f"different caches. Move {OUT_DIR} aside to start a new run.")
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    current["created_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    current["probe_sha256"] = file_sha256(__file__)
    with open(META, "w", encoding="utf-8") as fh:
        json.dump(current, fh, indent=2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="spread_mean,betweenness")
    ap.add_argument("--radii", default="0,1,2,3")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--per-network", type=int, default=2000)
    ap.add_argument("--drop", default="",
                    help="comma-separated columns to exclude (post-hoc arm; see the prereg addendum)")
    ap.add_argument("--feature-encoding", choices=("raw", "rank"), default="raw",
                    help="rank = per-graph percentile rank of every column (post-hoc arm 2)")
    ap.add_argument("--out", default=OUT_DIR, help="output folder")
    args = ap.parse_args()
    set_output(args.out)
    drop = tuple(c for c in args.drop.split(",") if c)

    targets = args.targets.split(",")
    radii = [int(r) for r in args.radii.split(",")]
    tags = networks()
    if len(tags) < 3:
        raise SystemExit("need at least three prepared networks under data/cache/")
    data = {t: load_network(t) for t in tags}

    feats = [tuple(d["reg"]["feature"]) for d in data.values()]
    if len(set(feats)) != 1:
        raise SystemExit("feature registries differ between networks; transfer needs one schema")
    for t in tags:
        for target in targets:
            if target not in data[t]["Y"].columns:
                raise SystemExit(f"{t} has no target {target}")

    config = {"per_network": args.per_network, "tiers": list(TIERS),
              "target_encoding": "within-network percentile rank", "model": "make_rf",
              "networks": tags}
    # Keys for the post-hoc arms are added only when used, so the registered run's
    # recorded configuration (which predates them) still matches on resume.
    if drop:
        config["dropped_columns"] = list(drop)
    if args.feature_encoding != "raw":
        config["feature_encoding"] = "within-network percentile rank"
    bind_run(config, tags)

    done = set()
    if os.path.exists(CELLS):
        prev = pd.read_csv(CELLS)
        done = {(r.target, r.holdout, int(r.radius), int(r.seed)) for r in prev.itertuples()}
        print(f"resuming: {len(done)} cells already done")

    # Within-network percentile ranks, computed once on ALL nodes of each graph.
    pct = {t: {tg: rankdata(data[t]["Y"][tg].to_numpy(float)) / len(data[t]["Y"])
               for tg in targets} for t in tags}

    def design(t: str, cols: list[str]) -> np.ndarray:
        A = data[t]["X"][cols].to_numpy(float)
        if args.feature_encoding == "rank":
            # Per-graph percentile rank of each column: unlabelled, but it reads the
            # whole graph's distribution of that column (see prereg addendum 2).
            A = np.column_stack([rankdata(a) / len(a) for a in A.T])
        return A

    todo = [(tg, h, r, s) for tg in targets for h in tags for r in radii
            for s in range(args.seeds) if (tg, h, r, s) not in done]
    print(f"{len(todo)} cells to fit")
    t_start = time.time()
    for i, (target, hold, r, seed) in enumerate(todo, 1):
        cols = columns_at(data[hold]["reg"], data[hold]["X"], r, drop)
        assert_no_leakage(cols)
        rng = np.random.default_rng([seed, r, tags.index(hold)])
        Xs, ys, sizes = [], [], {}
        for src in tags:
            if src == hold:
                continue
            n = len(data[src]["X"])
            take = np.sort(rng.choice(n, size=min(n, args.per_network), replace=False))
            Xs.append(design(src, cols)[take])
            ys.append(pct[src][target][take])
            sizes[src] = len(take)
        X_train, y_train = np.vstack(Xs), np.concatenate(ys)

        t0 = time.perf_counter()
        model = make_rf(seed)
        model.fit(X_train, y_train)
        pred = model.predict(design(hold, cols))
        fit_s = time.perf_counter() - t0

        y_hold = data[hold]["Y"][target].to_numpy(float)
        m = evaluate(y_hold, pred)
        m.update({"target": target, "holdout": hold, "radius": r, "seed": seed,
                  "n_features": len(cols), "n_train": len(y_train),
                  "train_networks": "|".join(sizes), "fit_seconds": fit_s})
        pd.DataFrame([m]).to_csv(CELLS, mode="a", header=not os.path.exists(CELLS), index=False)

        eta = (time.time() - t_start) / i * (len(todo) - i)
        print(f"  [{i:3d}/{len(todo)}] {target:12s} holdout={hold:18s} r={r} seed={seed} "
              f"tau={m['kendall_tau']:.4f}  ({fit_s:.0f}s, eta {eta/60:.0f}m)", flush=True)
    print(f"done: {CELLS}")


if __name__ == "__main__":
    main()

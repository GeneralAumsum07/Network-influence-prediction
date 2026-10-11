"""
analyse_edge5.py - do 5-node EDGE orbits earn their 204 columns?

WHY THIS IS A TARGETED TEST AND NOT A FULL SWEEP
------------------------------------------------
Turning on 5-node edge orbits takes the feature table from 171 columns to 339.
A full radius x richness x seed sweep at that width costs several hours, and
everything measured so far says most orbit columns contribute nothing: of the
thirteen 4-node NODE orbits, twelve were worth zero and one carried the whole
effect; of the subgraph tier at radius 1, only the 5-node orbits mattered.

So the question is asked directly instead. At each radius, compare the full
structural tier with 4-node edge orbits against the same thing with 5-node edge
orbits, paired across seeds. If the answer is a clear win, a full sweep is
justified; if it is noise, that is the result and the columns stay off by
default.

This is the same discipline as the orbit_04 and 5-node-hop-1 ablations: isolate
the one thing that changed rather than re-running everything and reading a
difference off two large tables.

RESUMING (added 2026-10-11)
--------------------------
`--checkpoint PATH` makes a run resumable after a crash or host reset: every
fold-seed tau is recorded the moment it is computed, and each finished
network's whole printed block is recorded too, so a rerun replays finished
networks without even re-extracting their features and refits only the seeds
it never reached. A resumed run prints the same bytes as an uninterrupted one
(see influence/checkpoint.py). Without the flag nothing changes.

Run:  python analyse_edge5.py [tag ...] [--seeds 10] [--checkpoint PATH]
"""
import argparse
import glob
import json
import os
import re

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from influence.preprocessing import load_edgelist
from influence.features import extract_features, select_features
from influence.experiment import out_of_fold_predictions, TIER_LADDER
from influence.estimators import ESTIMATORS
from influence.targets import assert_no_leakage
from influence.checkpoint import Checkpoint

FULL = TIER_LADDER["node+edge+subgraph"]

# Inert unless main() replaces it; keeps run()/analyse() callable as before
# from anything that imports this module.
NO_CHECKPOINT = Checkpoint(None, "", {}, {})


def objective_factory(target: str, objective: str):
    """
    Estimator factory for `out_of_fold_predictions`, plus a label for the header.

    Added 2026-09-12 by Claude Opus 5 (Task 6 root integration run C8, findings
    P2-11/P3-08). `None` is the ORIGINAL inline forest - the construction the
    2026-08-26 output came from - so `--objective raw` reproduces it byte for
    byte. `reported` swaps in the registry's `rf_log1p` factory for betweenness
    only; the spread targets are reported from `rf`, so for them the two
    objectives coincide and the default path is kept deliberately.
    """
    if objective == "reported" and target == "betweenness":
        return ESTIMATORS["rf_log1p"]
    return None


def run(X: pd.DataFrame, cols, y: np.ndarray, n_seeds: int,
        estimator=None, ck: Checkpoint = NO_CHECKPOINT,
        key: str = "") -> np.ndarray:
    Xm = X[cols].to_numpy(dtype=np.float64)
    # One checkpoint unit per seed: the finest grain that is still one
    # complete, deterministic fit. float() turns numpy's float64 into the
    # Python float JSON round-trips exactly; the value is unchanged, so the
    # array below is bit-identical whether a seed was fitted or replayed.
    return np.array([ck.unit(f"{key}|seed={s}", lambda s=s: float(kendalltau(
                         y, out_of_fold_predictions(
                             Xm, y, 5, s, estimator=estimator)).statistic))
                     for s in range(n_seeds)])


def analyse(tag: str, n_seeds: int, targets, objective: str = "raw",
            ck: Checkpoint = NO_CHECKPOINT) -> None:
    meta = json.load(open(f"cache_meta_{tag}.json"))
    net = load_edgelist(meta["provenance"]["source"].replace("\\", "/"))
    Y = pd.read_csv(f"cache_targets_{tag}.csv")
    p, mh = meta["p"], meta.get("max_hop", 3)

    X4, r4, _ = extract_features(net, mh, verbose=False, p_transmission=p,
                                 edge_graphlet_size=4)
    X5, r5, _ = extract_features(net, mh, verbose=False, p_transmission=p,
                                 edge_graphlet_size=5)

    print("\n" + "=" * 78)
    print(f"{tag}   n={net.n:,}   {len(r4)} features with 4-node edge orbits, "
          f"{len(r5)} with 5-node")
    # Provenance lines added 2026-09-11 (Claude Opus 5, Task 6 findings P3-08
    # and P1-01). Every target here is fitted under the raw squared-error
    # objective (out_of_fold_predictions with its default estimator), which for
    # betweenness is the historical arm, not the log1p arm the study reports.
    # And the 5-node EDGE orbit radius table was corrected on 2026-09-11: nine
    # orbits moved from hop 1 to hop 2, so an r=1 row produced before that date
    # used columns a radius-1 observer cannot compute.
    if objective == "reported":
        print("objective: reported arms - rf_log1p for betweenness, rf for the "
              "spread targets (--objective reported, added 2026-09-12)")
    else:
        print("objective: raw squared-error for every target "
              "(historical arm; the study reports log1p for betweenness)")
    print("edge-orbit radius table: EDGE_ORBIT5_RADIUS as corrected 2026-09-11 "
          "(orbits 49,50,51,59,60,61,63,64,65 at hop 2)")
    print("=" * 78)

    for target in targets:
        if target not in Y.columns:
            continue
        y = Y[target].to_numpy(dtype=np.float64)
        print(f"\n  {target}   ({n_seeds} seeds, paired)")
        for r in range(mh + 1):
            c4 = select_features(X4, r4, max_hop=r, tiers=FULL)
            c5 = select_features(X5, r5, max_hop=r, tiers=FULL)
            if not c4 or len(c5) == len(c4):
                continue
            assert_no_leakage(c4)
            assert_no_leakage(c5)
            est = objective_factory(target, objective)
            cell = f"tau|{tag}|{target}|r={r}"
            a = run(X4, c4, y, n_seeds, est, ck, cell + "|4node")
            b = run(X5, c5, y, n_seeds, est, ck, cell + "|5node")
            d = b - a
            star = "*" if abs(d.mean()) > 2 * d.std(ddof=1) else " "
            print(f"    r={r}  4-node {a.mean():.4f}  ->  5-node {b.mean():.4f}"
                  f"   gain {d.mean():+.4f} +/- {d.std(ddof=1):.4f}{star}"
                  f"   (+{len(c5)-len(c4)} columns)")


def discover():
    return [re.match(r"cache_features_(.+)\.csv$", os.path.basename(q)).group(1)
            for q in sorted(glob.glob("cache_features_*.csv"))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="*")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--targets", default="spread_mean,spread_cv,betweenness")
    ap.add_argument("--objective", default="raw", choices=["raw", "reported"],
                    help="raw = historical squared-error arm (reproduces the "
                         "2026-08-26 file); reported = rf_log1p for betweenness")
    ap.add_argument("--checkpoint", default=None,
                    help="resume log (JSON lines); see influence/checkpoint.py")
    a = ap.parse_args()
    tags = a.tags or discover()
    targets = a.targets.split(",")

    # The checkpoint header pins what decides the answer: arguments (the tag
    # list included, so a new cache appearing changes it), the bytes of every
    # input, and the loaded project code. Inputs are labelled by file name,
    # never by an absolute path.
    inputs = {}
    for t in tags:
        meta_path = f"cache_meta_{t}.json"
        src = json.load(open(meta_path))["provenance"]["source"].replace("\\", "/")
        inputs.update({meta_path: meta_path, f"cache_targets_{t}.csv":
                       f"cache_targets_{t}.csv", src: src})
    ck = Checkpoint(a.checkpoint, "analyse_edge5.py",
                    {"tags": tags, "seeds": a.seeds, "targets": targets,
                     "objective": a.objective}, inputs)

    # A whole network is also a unit, wrapping its per-seed units, so a
    # finished network replays its printed block and skips the 5-node edge
    # orbit extraction entirely - that extraction is the one cost per-seed
    # replay alone could not avoid.
    for t in tags:
        ck.unit(f"tag|{t}", lambda t=t: analyse(t, a.seeds, targets,
                                                a.objective, ck))

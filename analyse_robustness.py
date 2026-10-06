"""
analyse_robustness.py - Angle 4: does local prediction survive damage better
than recomputing the global score on damaged data?

THE EXPERIMENT
--------------
Delete a fraction rho of edges. Then compare two ways of ranking nodes by their
TRUE (clean-graph) influence, both given only the damaged graph:

    LOCAL      compute local features on the damaged graph, feed them to a
               model learned from clean data
    RECOMPUTE  compute the global score directly on the damaged graph

and a third line as a floor:

    DEGREE     rank by degree on the damaged graph

Ground truth is always the CLEAN graph's score. The question is which method's
ranking survives the damage.

THE TWO TRAINING ARMS
---------------------
(Reworded 2026-09-11 by Claude Opus 5, Task 6 finding P2-08: the previous
version of this paragraph said training on damaged features against clean
targets "would leak the answer", which contradicted the `--train-on damaged`
arm this file has carried since the trainmode comparison. Both arms are
sound; the paragraph now describes both.)

The primary arm trains on CLEAN data. It is the realistic setting and the
fair one: you learn the mapping from local structure to influence once, on
good data - a curated corpus, a fully observed subnetwork - and then deploy it
against a graph you can only observe imperfectly. Five-fold, the model for
node i is fitted on the CLEAN features and CLEAN targets of the other folds,
then shown node i's DAMAGED features. No model sees the node it scores.

The secondary arm (`--train-on damaged`, column `local_trained_damaged`)
trains on DAMAGED features against the clean target - but on a DIFFERENT
damage draw at the same rho from the one it is scored on, and again
out-of-fold. That answers a different question - "does knowing what damage
looks like at training time help?" - and it is not a leak: the clean target
is the quantity being predicted in both arms, and the model for node i never
sees node i's row from any draw. What WOULD leak is training and scoring on
the same damaged realisation, which the other-draw rule in run_network
prevents by construction (and which is why the arm needs >= 2 draws at
rho > 0 and collapses to the clean arm at rho = 0).

The folds are fitted ONCE per (network, target) and reused across every noise
level, which is both far cheaper and more correct - the same model faces every
level of damage, so differences between levels are the damage and nothing else.

CONTROLLING FOR SKEW, WHICH IS WHERE THE WIN COULD BE FAKE
-----------------------------------------------------------
Betweenness is brutally skewed: 15% to 55% of nodes have it exactly zero, and
section 24 of the study doc shows a single local feature identifies that set
perfectly. A tau computed over all nodes is therefore dominated by the
zero-versus-nonzero split, and a method that merely keeps that split intact
under damage would look robust while being useless for ranking the nodes that
matter.

So every comparison is reported twice: over all nodes, and over the subset
where the clean target is nonzero. A win that survives the second column is
real; a win that only appears in the first is an artefact of the skew. The same
is done with precision@5%, which ignores the tied mass entirely.

`spread_mean` is run alongside as a target with no zeros at all, so it carries
none of this problem - if the effect appears there too, skew is not driving it.

THE OBJECTIVE ARMS (added 2026-09-12)
-------------------------------------
(Claude Opus 5, plan §0 "queue Angle 4", after Task 6 findings P2-11/P3-08.)
Every forest here was fit on raw y. For betweenness that is the historical
squared-error arm; since 2026-09-04 the study's horizon tables report the
`rf_log1p` arm instead, and the two differ by up to +0.1291 vs +0.0436 tau on
one rung (P2-11), so a raw-arm Angle 4 number cannot be quoted beside a log1p
horizon. `--objective reported` wraps the SAME forest (same trees, leaf floor,
seeds, folds) in log1p/expm1 for betweenness only - exactly the construction
of `influence.estimators.make_rf_log1p`, applied to this file's own forest
rather than to `make_rf` so that the objective is provably the only change
between the two arms of this file. The spread targets are unchanged under
`reported` (their reported arm IS the raw arm), which is why the controller
runs the reported arm with `--targets betweenness`. `--objective raw` is the
default and reproduces the 2026-08-27 files; the output path defaults differ
per arm so the reported arm can never overwrite the historical CSV.

Run:  python analyse_robustness.py [--networks a,b] [--rhos 0.05,0.1,...]
      python analyse_robustness.py --objective reported --targets betweenness
"""
import argparse
import glob
import json
import os
import re

import numpy as np
import pandas as pd
from scipy.stats import kendalltau
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

from influence.preprocessing import load_edgelist
from influence.features import extract_features, select_features
from influence.experiment import TIER_LADDER, precision_at_k
from influence.robustness import delete_edges, align_features
from influence.targets import exact_betweenness, assert_no_leakage
from influence.dynamics import simulate_ic_percolation

FULL = TIER_LADDER["node+edge+subgraph"]
N_FOLDS = 5
N_TREES = 120


def fit_folds(Xc: np.ndarray, y: np.ndarray, seed: int = 0,
              log1p: bool = False):
    """Fit one model per fold on CLEAN data; return (models, fold test indices).

    `log1p=True` (2026-09-12) trains the identical forest on log1p(y) and maps
    predictions back through expm1. Kendall tau and precision@k are invariant
    to that monotone map, so it changes what the forest optimises and not what
    it is judged against - the same argument as `make_rf_log1p`'s docstring.
    The fold split and the forest's seed are untouched, so the two arms differ
    in the objective and nothing else.
    """
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
    models, tests = [], []
    for tr, te in kf.split(Xc):
        m = RandomForestRegressor(n_estimators=N_TREES, n_jobs=-1,
                                  random_state=seed, min_samples_leaf=2)
        if log1p:
            m = TransformedTargetRegressor(regressor=m, func=np.log1p,
                                           inverse_func=np.expm1,
                                           check_inverse=True)
        m.fit(Xc[tr], y[tr])
        models.append(m)
        tests.append(te)
    return models, tests


def predict_damaged(models, tests, Xd: np.ndarray) -> np.ndarray:
    """Each node scored by the fold-model that never trained on it."""
    out = np.zeros(len(Xd), dtype=np.float64)
    for m, te in zip(models, tests):
        out[te] = m.predict(Xd[te])
    return out


def score(y_true: np.ndarray, pred: np.ndarray, nz: np.ndarray) -> dict:
    """tau over everything, tau over the nonzero subset, and precision@5%."""
    n = len(y_true)
    return {
        "tau": float(kendalltau(y_true, pred).statistic),
        "tau_nonzero": (float(kendalltau(y_true[nz], pred[nz]).statistic)
                        if nz.sum() > 20 else np.nan),
        "p_at_5pct": precision_at_k(y_true, pred, max(1, n // 20)),
    }


def use_log1p(target: str, objective: str) -> bool:
    """Betweenness only, and only under the reported arm - see the module
    docstring and `make_rf_log1p` for why the other targets are ineligible."""
    return objective == "reported" and target == "betweenness"


def run_network(tag: str, rhos, dseeds, targets, train_modes,
                objective: str = "raw") -> pd.DataFrame:
    meta = json.load(open(f"cache_meta_{tag}.json"))
    net = load_edgelist(meta["provenance"]["source"].replace("\\", "/"))
    Xc_df = pd.read_csv(f"cache_features_{tag}.csv")
    Y = pd.read_csv(f"cache_targets_{tag}.csv")
    reg = pd.read_csv(f"cache_registry_{tag}.csv")
    cols = select_features(Xc_df, reg, max_hop=meta.get("max_hop", 3), tiers=FULL)
    assert_no_leakage(cols)
    Xc = Xc_df[cols].to_numpy(dtype=np.float64)
    p = meta["p"]

    print(f"\n{'='*78}\n{tag}   n={net.n:,}  m={net.m:,}  "
          f"{len(cols)} features   objective={objective}\n{'='*78}", flush=True)

    # One set of fold models per target, reused at every noise level.
    fitted = {}
    for t in targets:
        if t in Y.columns:
            fitted[t] = fit_folds(Xc, Y[t].to_numpy(dtype=np.float64),
                                  log1p=use_log1p(t, objective))

    rows = []
    for rho in rhos:
        draws = dseeds if rho > 0 else [0]

        # Extract every damage draw at this rho FIRST. The damaged-training
        # variant needs a draw to train on that is not the draw it is tested
        # on, and having them all in hand makes that a lookup rather than a
        # second extraction.
        Xd, dmg_of = {}, {}
        for ds in draws:
            dmg = delete_edges(net, rho, seed=ds)
            Xd_df, _, _ = extract_features(dmg, max_hop=meta.get("max_hop", 3),
                                           verbose=False, p_transmission=p)
            Xd[ds] = align_features(Xd_df, cols).to_numpy(dtype=np.float64)
            dmg_of[ds] = dmg
            print(f"  rho={rho:<5g} seed={ds}  "
                  f"edges {dmg.provenance['edges_after']:,}/{net.m:,}  "
                  f"isolated {dmg.provenance['isolated_nodes']}", flush=True)

        for ds in draws:
            dmg = dmg_of[ds]
            recomputed = {}
            if "betweenness" in targets:
                recomputed["betweenness"] = exact_betweenness(dmg)
            if "spread_mean" in targets:
                recomputed["spread_mean"] = simulate_ic_percolation(
                    dmg, p=p, n_sims=meta["n_sims"], seed=0, verbose=False).mean

            for t in fitted:
                y = Y[t].to_numpy(dtype=np.float64)
                nz = y != 0
                preds = {}

                if "clean" in train_modes:
                    models, tests = fitted[t]
                    preds["local"] = predict_damaged(models, tests, Xd[ds])

                if "damaged" in train_modes and rho > 0 and len(draws) > 1:
                    # Train on a DIFFERENT draw at the same rho. Same draw
                    # would let the model learn that particular realisation of
                    # the damage rather than the regime, which is not what a
                    # deployed model would get.
                    other = draws[(draws.index(ds) + 1) % len(draws)]
                    m2, t2 = fit_folds(Xd[other], y,
                                       log1p=use_log1p(t, objective))
                    preds["local_trained_damaged"] = predict_damaged(m2, t2, Xd[ds])
                elif "damaged" in train_modes and rho == 0:
                    # At rho=0 "damaged" and "clean" are the same thing.
                    models, tests = fitted[t]
                    preds["local_trained_damaged"] = predict_damaged(
                        models, tests, Xd[ds])

                preds["recompute"] = recomputed.get(t)
                preds["degree"] = dmg.degree.astype(float)

                for method, pred in preds.items():
                    if pred is None:
                        continue
                    rows.append({"network": tag, "target": t, "rho": rho,
                                 "damage_seed": ds, "method": method,
                                 **score(y, pred, nz)})
    return pd.DataFrame(rows)


def report(df: pd.DataFrame, objective: str = "raw") -> None:
    for tag in df.network.unique():
        for t in df[df.network == tag].target.unique():
            sub = df[(df.network == tag) & (df.target == t)]
            print(f"\n{'='*78}")
            print(f"{tag}   target = {t}")
            print("  tau against the CLEAN truth. 'nonzero' restricts to nodes")
            print("  where the clean target is not zero - the skew control.")
            # Objective label added 2026-09-12 (Claude Opus 5, Task 6 findings
            # P2-11/P3-08). Under the default arm the forest is fit on raw y for
            # every target; for betweenness that is the historical squared-error
            # arm, not the log1p arm the study's horizon tables report. The label
            # exists so a re-run of this file can never be quoted without its
            # arm; the 2026-08-27 outputs predate it and are labelled in
            # results/HISTORICAL_LANES_NOTE_20260912.md instead. Same day, the
            # `--objective reported` arm was added and labels itself here too.
            if t == "betweenness":
                if use_log1p(t, objective):
                    print("  objective: log1p betweenness (rf_log1p construction; "
                          "the arm the study reports, --objective reported)")
                else:
                    print("  objective: raw betweenness (historical arm; the "
                          "study reports log1p)")
            print("=" * 78)
            for metric in ("tau", "tau_nonzero", "p_at_5pct"):
                piv = sub.pivot_table(index="rho", columns="method",
                                      values=metric, aggfunc="mean")
                if piv.isna().all().all():
                    continue
                order = [c for c in ("local", "local_trained_damaged",
                                     "recompute", "degree")
                         if c in piv.columns]
                piv = piv[order]
                if "local" in piv and "recompute" in piv:
                    piv["local - recompute"] = piv["local"] - piv["recompute"]
                if "local_trained_damaged" in piv and "recompute" in piv:
                    piv["dmg-trained - recompute"] = (
                        piv["local_trained_damaged"] - piv["recompute"])
                if "local_trained_damaged" in piv and "local" in piv:
                    piv["dmg-trained - clean-trained"] = (
                        piv["local_trained_damaged"] - piv["local"])
                print(f"\n  {metric}")
                print("   " + piv.round(4).to_string().replace("\n", "\n   "))


def discover() -> list[str]:
    return [re.match(r"cache_features_(.+)\.csv$", os.path.basename(p)).group(1)
            for p in sorted(glob.glob("cache_features_*.csv"))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--networks", default="")
    ap.add_argument("--rhos", default="0,0.05,0.1,0.2,0.3,0.5")
    ap.add_argument("--damage-seeds", type=int, default=3)
    ap.add_argument("--targets", default="betweenness,spread_mean")
    ap.add_argument("--train-on", default="clean,damaged",
                    help="clean | damaged | clean,damaged")
    ap.add_argument("--objective", default="raw", choices=["raw", "reported"],
                    help="raw = squared error on y for every target (the "
                         "historical arm, reproduces the 2026-08-27 files); "
                         "reported = log1p objective for betweenness, the arm "
                         "the study reports (added 2026-09-12)")
    ap.add_argument("--out", default=None,
                    help="defaults to results/robustness.csv for --objective "
                         "raw and results/robustness_log1p.csv for reported, "
                         "so the reported arm cannot overwrite the historical "
                         "CSV that make_fig3.py and the study read")
    args = ap.parse_args()

    tags = args.networks.split(",") if args.networks else discover()
    rhos = [float(x) for x in args.rhos.split(",")]
    dseeds = list(range(args.damage_seeds))
    targets = args.targets.split(",")
    out = args.out or ("results/robustness.csv" if args.objective == "raw"
                       else "results/robustness_log1p.csv")

    train_modes = args.train_on.split(",")
    all_rows = [run_network(t, rhos, dseeds, targets, train_modes,
                            args.objective) for t in tags]
    df = pd.concat(all_rows, ignore_index=True)
    os.makedirs("results", exist_ok=True)
    df.to_csv(out, index=False)
    report(df, args.objective)
    print(f"\nwrote {out}   (objective={args.objective})")


if __name__ == "__main__":
    main()

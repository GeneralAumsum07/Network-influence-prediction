"""
analysis/analyse_closed_form.py
===============================
Zero-training baselines at matched radius, beside the learned P(r).

WHAT THIS ANSWERS
-----------------
Every P(r) curve in this project is a random forest's out-of-fold Kendall tau.
Without a reference at the SAME radius, "the model needs radius r" cannot be
told apart from "radius r already holds a one-line rule this good". The
stage-1 cache already contains the classical closed-form local scores, each
tagged with the radius it needs, so they can be scored for free:

    r=0  degree
    r=1  h_index_1, collective_influence_1, local_gravity_1, cluster_rank,
         ego_betweenness, nbr_degree_sum - degree  (= non-backtracking walks
         of length 2, the walk count behind CI_1)
    r=2  h_index_2, collective_influence_2, local_gravity_2, reach_within_2,
         perc_reach_2
    r=3  h_index_3, collective_influence_3, local_gravity_3, reach_within_3,
         perc_reach_3, semilocal_centrality

`perc_reach_r` is the truncated percolation message-passing estimate. On a
tree it equals 1 + sum_{l<=r} p^l NBW_l(i), the beta-weighted
non-backtracking walk series, so it is the cached stand-in for that estimator.
It is registered in the DYNAMIC tier: it needs p = 1.5 x beta_c, and beta_c =
1/lambda_1 of the non-backtracking matrix is a global spectral quantity. The
forest it is compared with (node+edge+subgraph) never sees p. So the report
gives a second, like-for-like reference, `best structural rule`, which excludes
the dynamic tier.

No model is fitted and no simulation is run. Each rule is a fixed function of
the node's r-ball, so its tau is computed in-sample over all nodes with
nothing to overfit.

ORIENTATION. A rule ranks nodes in one direction or the other. For
spread_mean and betweenness every rule is oriented "larger = more
influential". For spread_cv and spread_resid there is no natural direction -
hubs are typically the LEAST volatile - so each rule is scored by |tau| and
its sign is recorded. That is one bit of in-sample choice per rule, stated
rather than hidden.

TWO READINGS ARE REPORTED, AND THEY ANSWER DIFFERENT QUESTIONS
--------------------------------------------------------------
* `best rule`: the best of the rules available at radius r, chosen per
  (network, target, radius) cell. Choosing the best of a handful on the same
  data flatters the closed form slightly; it is an upper reference for "one
  closed-form rule".
* `fixed rule`: one rule per radius, fixed in advance - degree at r=0 and the
  h-index ladder above it, the iterative family this literature uses most.

THE r=0 TIE ARTEFACT
--------------------
At r=0 the forest sees `degree` and `degree_normalized`, both rank-identical
to degree. For a target that rises with degree (spread_mean, betweenness) its
best possible ranking is therefore degree itself. Its out-of-fold P(0)
nevertheless sits below tau_b(y, degree). Nodes of equal degree fall in
different folds, the five fold models score them slightly differently, and
tau-b counts those arbitrary orderings as concordant or discordant pairs
instead of ties. The gap is printed per network: it is how much of every
reported r0 -> r1 gain is this artefact rather than information. Beside it is
tau with degree ties broken uniformly at random (mean of TIE_DRAWS draws). Where
the forest's P(0) matches that number, random tie-breaking is the whole gap.
For the
volatility targets the forest may legitimately beat |tau_b(y, degree)|: it can
learn a NON-monotone function of degree, which no ranking by degree can.

Run from the repository root:
    python analysis/analyse_closed_form.py
Writes results/closed_form/closed_form_baselines.csv and
results/RESULTS_closed_form.txt.
"""
import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import io
import os
import sys
from contextlib import redirect_stdout

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from analyse import FULL, discover_networks, load

TARGETS = ("spread_mean", "spread_cv", "spread_resid", "betweenness")
# Targets where influence rises with every rule, so the sign is fixed at +1.
ORIENTED = ("spread_mean", "betweenness")
RULES = {
    0: ["degree"],
    1: ["h_index_1", "collective_influence_1", "local_gravity_1", "cluster_rank",
        "ego_betweenness", "nbw_2"],
    2: ["h_index_2", "collective_influence_2", "local_gravity_2", "reach_within_2",
        "perc_reach_2"],
    3: ["h_index_3", "collective_influence_3", "local_gravity_3", "reach_within_3",
        "perc_reach_3", "semilocal_centrality"],
}
FIXED = {0: "degree", 1: "h_index_1", 2: "h_index_2", 3: "h_index_3"}
TIE_DRAWS = 5
OUT_DIR = os.path.join("results", "closed_form")
OUT_CSV = os.path.join(OUT_DIR, "closed_form_baselines.csv")
OUT_TXT = os.path.join("results", "RESULTS_closed_form.txt")


def rule_columns(X: pd.DataFrame, reg: pd.DataFrame) -> dict[str, tuple[np.ndarray, int]]:
    """Each rule's values and the hop its registry entry (or derivation) needs."""
    hop = dict(zip(reg["feature"], reg["hop"].astype(int)))
    tier = dict(zip(reg["feature"], reg["tier"]))
    out = {}
    for r, names in RULES.items():
        for name in names:
            if name == "nbw_2":
                # sum over neighbours of (k_j - 1): both inputs are hop <= 1.
                vals = X["nbr_degree_sum"].to_numpy(float) - X["degree"].to_numpy(float)
                need = max(hop["nbr_degree_sum"], hop["degree"])
            elif name in X.columns:
                vals, need = X[name].to_numpy(float), hop[name]
            else:
                continue
            if need > r:
                raise ValueError(f"{name} needs hop {need} but is listed at r={r}")
            out[name] = (vals, r, tier.get(name, "node"))
    return out


def tau(y: np.ndarray, x: np.ndarray) -> float:
    t = kendalltau(y, x).statistic
    return float(t) if t is not None and np.isfinite(t) else np.nan


def random_tiebreak_tau(y: np.ndarray, x: np.ndarray, draws: int = TIE_DRAWS) -> float:
    """tau of x against y with x's ties broken at random: jitter far below x's resolution."""
    rng = np.random.default_rng(0)
    gaps = np.diff(np.unique(x))
    eps = (gaps.min() if gaps.size else 1.0) * 1e-3
    return float(np.mean([tau(y, x + rng.uniform(0, eps, x.size)) for _ in range(draws)]))


def analyse_network(tag: str) -> list[dict]:
    X = pd.read_csv(f"data/cache/cache_features_{tag}.csv")
    Y = pd.read_csv(f"data/cache/cache_targets_{tag}.csv")
    reg = pd.read_csv(f"data/cache/cache_registry_{tag}.csv")
    sweep = load(tag)                       # reported arm: log1p betweenness spliced in
    rules = rule_columns(X, reg)
    rows = []
    for target in TARGETS:
        if target not in Y.columns:
            continue
        y = Y[target].to_numpy(float)
        cell = sweep[(sweep.target == target) & (sweep.richness == FULL)]
        for r in sorted(RULES):
            rf = cell[cell.radius == r].kendall_tau
            raw = {name: tau(y, vals) for name, (vals, rr, _) in rules.items() if rr <= r}
            # Fixed orientation where it exists, |tau| (sign recorded) where it does not.
            scores = raw if target in ORIENTED else {k: abs(v) for k, v in raw.items()}
            key = lambda k: -np.inf if np.isnan(scores[k]) else scores[k]  # noqa: E731
            best = max(scores, key=key)
            best_s = max((k for k in scores if rules[k][2] != "dynamic"), key=key)
            rows.append({
                "network": tag, "target": target, "radius": r,
                "rf_tau_mean": float(rf.mean()), "rf_tau_sd": float(rf.std(ddof=1)),
                "rf_seeds": int(rf.size),
                "best_rule": best, "best_rule_tau": scores[best],
                "best_structural_rule": best_s, "best_structural_tau": scores[best_s],
                "fixed_rule": FIXED[r], "fixed_rule_tau": scores[FIXED[r]],
                "best_rule_sign": int(np.sign(raw[best])) if np.isfinite(raw[best]) else 0,
                "rf_minus_best_rule": float(rf.mean()) - scores[best],
                "tau_degree_random_ties": (random_tiebreak_tau(y, X["degree"].to_numpy(float))
                                           if r == 0 and target in ORIENTED else np.nan),
                **{f"tau_{k}": v for k, v in raw.items()},
            })
    return rows


def report(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        print("=" * 78)
        print("CLOSED-FORM LOCAL RULES AT MATCHED RADIUS vs THE LEARNED P(r)")
        print("rf = random forest, richest structural tier, mean +/- sd over seeds")
        print("     (betweenness from the reported log1p arm)")
        print("best rule = best closed-form rule available at that radius (in-sample choice);")
        print("            for spread_cv / spread_resid scored as |tau|, '(-)' = ranked ascending")
        print("            [d] = dynamic tier (perc_reach_r): uses p, which the forest does not see;")
        print("            'struct' = the best rule without the dynamic tier")
        print("=" * 78)
        for (tag, target), g in df.groupby(["network", "target"], sort=True):
            print(f"\n{tag} / {target}")
            print(f"  {'r':>2} {'rf tau':>16} {'best rule':>26} {'tau':>7} "
                  f"{'rf - rule':>9} {'struct':>7} {'h-index tau':>12}")
            for _, x in g.sort_values("radius").iterrows():
                rule = (x.best_rule + (" [d]" if x.best_rule.startswith("perc_reach") else "")
                        + (" (-)" if x.best_rule_sign < 0 else ""))
                print(f"  {int(x.radius):>2} {x.rf_tau_mean:>9.4f} +/-{x.rf_tau_sd:.4f} "
                      f"{rule:>26} {x.best_rule_tau:>7.4f} {x.rf_minus_best_rule:>+9.4f} "
                      f"{x.best_structural_tau:>7.4f} {x.fixed_rule_tau:>12.4f}")

        print("\n" + "=" * 78)
        print("THE r=0 TIE ARTEFACT: forest P(0) vs the degree ranking it can at best reproduce")
        print("=" * 78)
        z = df[(df.radius == 0) & df.target.isin(ORIENTED)]
        print(f"  {'network':18s} {'target':13s} {'tau_b(y,degree)':>16} {'random ties':>12} "
              f"{'rf P(0)':>9} {'gap':>8} {'gap / rf sd':>12}")
        for _, x in z.sort_values(["target", "network"]).iterrows():
            gap = x.rf_tau_mean - x.best_rule_tau
            print(f"  {x.network:18s} {x.target:13s} {x.best_rule_tau:>16.4f} "
                  f"{x.tau_degree_random_ties:>12.4f} {x.rf_tau_mean:>9.4f} "
                  f"{gap:>+8.4f} {gap / x.rf_tau_sd if x.rf_tau_sd > 0 else np.nan:>12.1f}")
        print("  random ties = tau of degree with its ties broken uniformly at random. Where the")
        print("  forest matches it, the gap is the tie artefact alone; where the forest is lower,")
        print("  its fold models are also non-monotone in degree.")

        print("\n" + "=" * 78)
        print("WHERE THE FOREST DOES NOT BEAT ONE CLOSED-FORM RULE (rf - best rule <= 2 x rf sd)")
        print("=" * 78)
        tie = df[(df.radius > 0) & (df.rf_minus_best_rule <= 2 * df.rf_tau_sd)]
        if tie.empty:
            print("  none: at every radius >= 1 the forest beats the best single rule")
        for _, x in tie.iterrows():
            print(f"  {x.network:18s} {x.target:13s} r={int(x.radius)}  rf {x.rf_tau_mean:.4f} "
                  f"vs {x.best_rule} {x.best_rule_tau:.4f}")
    return buf.getvalue()


def main() -> None:
    nets = discover_networks()
    if not nets:
        raise SystemExit("no data/cache/sweep_*.csv found - run pipeline/stage2_sweep.py first")
    rows = [row for tag in nets for row in analyse_network(tag)]
    df = pd.DataFrame(rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    text = report(df)
    with open(OUT_TXT, "w", encoding="utf-8") as fh:
        fh.write(text)
    sys.stdout.write(text)
    print(f"\nwrote {OUT_CSV} and {OUT_TXT}")


if __name__ == "__main__":
    main()

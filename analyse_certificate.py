"""Score L6, the certificate on the synthetic corpus (prereg 2026-11-02 19:53, parts C-D).

Primary, part C. For spread_mean, tier node+edge+subgraph:
  rho_{g,s} = tau(r=1) / tau(r=3), paired within seed s (same seed, same folds)
  rho_g     = seed mean, sd_g = seed sd (ddof 1); unscored if seed-mean tau3 <= 0
  T         = Kendall tau-b(gamma_target, rho_g) over the scored gamma graphs
  magnitude = |rho(2.1) - rho(4.0)| > 2 * sqrt(mean_g sd_g^2)
  PREDICTION SUPPORTED  T <= -t_crit and magnitude
  COUNTER SUPPORTED     T >= +t_crit and magnitude
  FLAT                  otherwise;  UNDECIDED if fewer than 6 gamma graphs scored
t_crit is the smallest |T| whose exact one-sided null p is <= 0.05 at the
scored n (0.571 at n = 8, computed by enumeration here rather than copied).

Reported, part D: r* (relative eps 0.05, modal), hop-gain area, the same rho
and T for betweenness (rf_log1p), the controls, and the structure table from
corpus.json with Kendall tau of the NB gap and duel ratio against gamma.

Refuses to run unless every graph's arms are complete (probe_certificate.arm_done).
Writes results/phase7_certificate/{ratios.csv, verdict.json}.
"""
import itertools
import json
import sys
from math import factorial

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from analyse_beta_sweep import r_star_relative
from probe_certificate import (ARMS, CONTROL_TAGS, GAMMA_TAGS, GAMMAS, OUT, PLAN,
                               arm_done, arm_paths, sha256)

TIER = "node+edge+subgraph"
EPS = 0.05
ALPHA = 0.05
MIN_SCORED = 6


def t_crit(n: int, alpha: float = ALPHA) -> float:
    """Smallest Kendall tau whose exact one-sided null p is <= alpha (no ties)."""
    pairs = n * (n - 1) // 2
    counts = np.zeros(pairs + 1, dtype=np.int64)
    for p in itertools.permutations(range(n)):
        counts[sum(p[i] < p[j] for i in range(n) for j in range(i + 1, n))] += 1
    tail = np.cumsum(counts[::-1])[::-1] / factorial(n)      # P(C >= c)
    c = min(c for c in range(pairs + 1) if tail[c] <= alpha)
    return (2 * c - pairs) / pairs


def ratio_row(sweep: pd.DataFrame, target: str) -> dict:
    sub = sweep[(sweep.target == target) & (sweep.richness == TIER)]
    tau = sub.pivot_table(index="seed", columns="radius", values="kendall_tau")
    rho = tau[1] / tau[3]
    mean = tau.mean()
    gain = sum((mean[r] - mean[0]) for r in (1, 2, 3)) / (mean[3] - mean[0]) \
        if mean[3] != mean[0] else np.nan
    rs = r_star_relative(sweep, target, TIER, EPS)
    return {"tau0": mean[0], "tau1": mean[1], "tau2": mean[2], "tau3": mean[3],
            "scored": bool(mean[3] > 0), "rho": rho.mean(), "rho_sd": rho.std(ddof=1),
            "hop_gain_area": gain, "r_star": rs["r_star"], "r_star_agree": f"{rs['agree']}/{rs['n']}"}


def trend(df: pd.DataFrame) -> dict:
    fam = df[df.family == "gamma"]
    scored = fam[fam.scored]
    n = len(scored)
    if n < MIN_SCORED:
        return {"outcome": "UNDECIDED", "n_scored": n}
    crit = t_crit(n)
    T = kendalltau(scored.gamma_target, scored.rho).statistic
    sd_pool = float(np.sqrt((scored.rho_sd ** 2).mean()))
    ends = fam.set_index("gamma_target")
    have_ends = {2.1, 4.0} <= set(scored.gamma_target)
    delta = float(ends.loc[2.1, "rho"] - ends.loc[4.0, "rho"]) if have_ends else np.nan
    big = bool(have_ends and abs(delta) > 2 * sd_pool)
    # T is a ratio of integers computed in floating point, so a T exactly at
    # the critical value can land one ulp on the wrong side; 1e-12 is far below
    # the 1/28 spacing between attainable values.
    if T <= -crit + 1e-12 and big:
        outcome = "PREDICTION SUPPORTED"
    elif T >= crit - 1e-12 and big:
        outcome = "COUNTER SUPPORTED"
    else:
        outcome = "FLAT"
    return {"outcome": outcome, "n_scored": n, "T": float(T), "t_crit": crit,
            "delta_2.1_minus_4.0": delta, "sd_pool": sd_pool, "magnitude_ok": big}


def main() -> int:
    for tag in PLAN:
        for target, est in ARMS:
            done, why = arm_done(tag, target, est)
            if not done:
                raise SystemExit(f"refusing: {tag} {target}/{est} incomplete ({why})")
    corpus = json.loads((OUT / "corpus.json").read_text(encoding="utf-8"))["graphs"]
    rows = []
    for tag in PLAN:
        g = corpus[tag]
        base = {"graph": tag, "family": "gamma" if tag in GAMMA_TAGS else "control",
                "gamma_target": GAMMAS[GAMMA_TAGS.index(tag)] if tag in GAMMA_TAGS else np.nan,
                "lcc_n": g["lcc_n"], "lcc_mean_degree": g["lcc_mean_degree"],
                "gamma_fit": g["stage0_profile"]["gamma"],
                "gamma_fit_sd": g["stage0_profile"].get("gamma_std"),
                "gamma_reliable": g["stage0_profile"].get("gamma_reliable"),
                "duel_ratio": g["stage0_profile"]["duel_ratio"],
                "nb_spectral_gap": g["nb_spectral_gap"],
                "clustering": g["stage0_profile"]["average_clustering"],
                "assortativity": g["stage0_profile"]["assortativity"]}
        for target, est in ARMS:
            _, sweep, _, _ = arm_paths(tag, est)
            rows.append({**base, "target": target, "estimator": est,
                         **ratio_row(pd.read_csv(sweep), target)})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "ratios.csv", index=False)

    spread = df[df.target == "spread_mean"].reset_index(drop=True)
    betw = df[df.target == "betweenness"].reset_index(drop=True)
    fam = spread[spread.family == "gamma"]
    structure = {f"kendall_{a}_vs_{b}": float(kendalltau(fam[a], fam[b]).statistic)
                 for a, b in (("nb_spectral_gap", "gamma_target"), ("duel_ratio", "gamma_target"),
                              ("nb_spectral_gap", "duel_ratio"))}
    verdict = {"registered_in": "prereg 2026-11-02 19:53 L6 parts C, D",
               "primary": trend(spread),
               "betweenness_reported": trend(betw),
               "structure_reported": structure,
               "sources": {p: sha256(p) for p in ("analyse_certificate.py", "probe_certificate.py",
                                                    "analyse_beta_sweep.py")}}
    (OUT / "verdict.json").write_text(json.dumps(verdict, indent=2, default=float) + "\n",
                                      encoding="utf-8")
    cols = ["graph", "lcc_n", "lcc_mean_degree", "duel_ratio", "nb_spectral_gap",
            "tau1", "tau3", "rho", "rho_sd", "hop_gain_area", "r_star", "r_star_agree"]
    pd.set_option("display.width", 200)
    print("spread_mean (primary):\n", spread[cols].round(4).to_string(index=False))
    print("\nbetweenness (rf_log1p, reported):\n", betw[cols].round(4).to_string(index=False))
    print("\nprimary:", verdict["primary"])
    print("betweenness:", verdict["betweenness_reported"])
    print("structure:", structure)
    return 0


if __name__ == "__main__":
    sys.exit(main())

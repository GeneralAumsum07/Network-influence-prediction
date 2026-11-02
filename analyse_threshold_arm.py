"""Score lane L5: part D of the 2026-11-02 10:55 definitions, both targets.

docs/prereg/prereg_phase6_5_lanes.md:
  "L5 execution definitions" (10:55), part D   - the rule and the verdict
  "L5 run status" (16:09), parts A and C       - ignites_theta is secondary,
                                                 outside the lane verdict

Per passing (network, theta), on the node+edge+subgraph rung only:
  primary  r*_rel at eps 0.05 (analyse_beta_sweep.r_star_relative: modal over
           the ten seeds, ties to the smaller r), with its seed agreement
  beside   eps 0.10 and 0.02; rule 2 (paired noise), reported, not scored
  compare  the same rule on the ROOT 1.5x sweep's spread_mean
  outcome  prediction  r*_theta >= r*_mean + 1
           counter     r*_theta <= 2
           both        both hold -> counts for neither
  unscored ceiling tau <= 0 (locality_horizon cannot apply a relative rule)

Lane verdict, spread_theta pairs only, excluding "both" and unscored:
  SUPPORTED (prediction on all) / NOT SUPPORTED (on none) / MIXED, and the
  counter likewise; UNDECIDED if nothing is left.

The dynamic rung is fitted (stage 2 cannot skip it) and is shown in the
curves table labelled unscored; no r* reads it, because locality_horizon
filters to the requested rung before taking its ceiling.

Writes results/phase7_threshold/rstar.csv and verdict.json.
Run from the repo root once the fits are complete: python analyse_threshold_arm.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from analyse_beta_sweep import (PRIMARY_TIER, RELATIVE_EPS, r_star_noise, r_star_relative,
                                sha256, tau_table, write_atomic)
from influence.experiment import locality_horizon
from probe_threshold_arm import OUT, network_done, passing_plan

PRIMARY_EPS = 0.05
# The comparison values the 10:55 addendum printed, computed then from the
# root sweeps. Recomputed here and checked: a mismatch means the root sweep
# changed after registration, and scoring against a moved baseline is refused.
REGISTERED_R_MEAN = {"ca-GrQc": 1, "ca-HepTh": 2, "email-Eu-core": 1,
                     "facebook_combined": 1, "p2p-Gnutella08": 2}


def score_target(sweep: pd.DataFrame, target: str) -> dict:
    """All r* variants for one target on the scored rung."""
    tab = tau_table(sweep, target, PRIMARY_TIER)
    noise = r_star_noise(tab)
    out = {"ceiling_tau": noise["ceiling"], "rule2": noise["r_star"],
           "rule2_r_ceiling": noise["r_ceiling"]}
    if noise["ceiling"] <= 0:
        # Registered: unscored. r_star_relative would raise on it anyway.
        out.update({"scored": False, "relative": {}})
        return out
    out["scored"] = True
    out["relative"] = {eps: r_star_relative(sweep, target, PRIMARY_TIER, eps)
                       for eps in RELATIVE_EPS}
    return out


def outcome(r_theta: int, r_mean: int) -> str:
    pred = r_theta >= r_mean + 1
    ctr = r_theta <= 2
    if pred and ctr:
        return "both"
    if pred:
        return "prediction"
    if ctr:
        return "counter"
    return "neither"


def aggregate(outcomes: list[str], side: str) -> str:
    counted = [o for o in outcomes if o != "both"]
    if not counted:
        return "UNDECIDED"
    hits = sum(o == side for o in counted)
    if hits == len(counted):
        return "SUPPORTED"
    if hits == 0:
        return "NOT SUPPORTED"
    return "MIXED"


# ---------------------------------------------------------------------------
# Somers' D sensitivity, registered 2026-11-02 17:15 part B
# ---------------------------------------------------------------------------

# Stored predictions must reproduce the recorded tau to this bound, or they
# are not the predictions that were scored. Both come from the same float64
# vectors through the same scipy call, so anything above float noise is a
# real mismatch, not rounding.
SOMERS_TAU_ATOL = 1e-9


def tied_pairs(v: np.ndarray) -> int:
    counts = np.unique(v, return_counts=True)[1]
    return int((counts * (counts - 1) // 2).sum())


def somers_d(target: np.ndarray, pred: np.ndarray) -> tuple[float, float]:
    """(Somers' D with the target as the reference, tau-b), both from one tau-b call.

    tau-b = S / sqrt((n0 - n1)(n0 - n2)) with S = concordant - discordant,
    n1 / n2 the pairs tied in prediction / target. Somers' D divides the same
    S by (n0 - n2) only: pairs the target ties are excluded, so a prediction
    that orders them loses nothing, while a prediction that ties what the
    target separates still loses (those pairs stay in the denominator).
    Recovering S from tau-b keeps this O(n log n); a pairwise count would be
    O(n^2), about 37 million pairs on ca-HepTh per cell.
    """
    n = len(target)
    n0 = n * (n - 1) // 2
    n1, n2 = tied_pairs(pred), tied_pairs(target)
    tb = float(kendalltau(target, pred).statistic)
    if np.isnan(tb) or n0 == n2:
        return float("nan"), tb
    s = tb * np.sqrt(float(n0 - n1) * float(n0 - n2))
    return s / (n0 - n2), tb


def somers_table(sweep: pd.DataFrame, oof_path: Path, y: np.ndarray, target: str) -> pd.DataFrame:
    """Somers' D for every (radius, seed) cell of one target on the scored rung."""
    sub = sweep[(sweep.target == target) & (sweep.richness == PRIMARY_TIER)]
    rows = []
    with np.load(oof_path) as store:
        for r in sub.itertuples():
            key = f"{target}|{int(r.radius)}|{PRIMARY_TIER}|{int(r.seed)}"
            d, tb = somers_d(y, store[key])
            if not abs(tb - r.kendall_tau) <= SOMERS_TAU_ATOL:
                raise SystemExit(f"{oof_path.name} {key}: recomputed tau {tb!r} vs recorded "
                                 f"{r.kendall_tau!r}; the stored predictions are not the "
                                 "scored ones, refusing (17:15 part B)")
            rows.append({"target": target, "radius": int(r.radius), "seed": int(r.seed),
                         "richness": PRIMARY_TIER, "kendall_tau": tb, "somers_d": d})
    return pd.DataFrame(rows)


def r_star_metric(tab: pd.DataFrame, metric: str, eps: float) -> dict:
    """analyse_beta_sweep.r_star_relative's rule (per-seed locality_horizon,
    modal across seeds, ties to the smaller r) on any metric column. That
    function hard-wires kendall_tau, so the rule is restated here, not edited
    there, keeping the L1 analyser's hash unchanged."""
    vals = []
    for seed in sorted(tab["seed"].unique()):
        h = locality_horizon(tab[tab.seed == seed], epsilon=eps, richness=PRIMARY_TIER,
                             metric=metric)
        if h.get("r_star") is not None:
            vals.append(h["r_star"])
    if not vals:
        return {"r_star": None, "agree": 0, "n": 0}
    counts = pd.Series(vals).value_counts()
    top = counts.max()
    return {"r_star": int(min(v for v, c in counts.items() if c == top)),
            "agree": int(top), "n": len(vals)}


def somers_sensitivity(plan: dict[str, list[str]]) -> tuple[dict, list[dict]]:
    rows, pairs = [], {}
    for tag, thetas in plan.items():
        root_y = pd.read_csv(f"cache_targets_{tag}.csv")["spread_mean"].to_numpy(np.float64)
        root_tab = somers_table(pd.read_csv(f"sweep_{tag}.csv"), Path(f"cache_oof_{tag}.npz"),
                                root_y, "spread_mean")
        r_mean = r_star_metric(root_tab, "somers_d", PRIMARY_EPS)
        ys = pd.read_csv(OUT / f"cache_targets_{tag}.csv")
        sweep = pd.read_csv(OUT / f"sweep_{tag}.csv")
        for theta in thetas:
            for kind in ("spread", "ignites"):
                target = f"{kind}_theta{theta}"
                tab = somers_table(sweep, OUT / f"cache_oof_{tag}.npz",
                                   ys[target].to_numpy(np.float64), target)
                ceiling = tab.groupby("radius").somers_d.mean().max()
                row = {"network": tag, "target": target, "ceiling_somers": float(ceiling),
                       "r_mean_somers": r_mean["r_star"],
                       "agree_mean": f"{r_mean['agree']}/{r_mean['n']}"}
                if ceiling <= 0:
                    row.update({"r_star_somers": None, "outcome": "unscored"})
                else:
                    rs = r_star_metric(tab, "somers_d", PRIMARY_EPS)
                    row.update({"r_star_somers": rs["r_star"],
                                "agree": f"{rs['agree']}/{rs['n']}",
                                "outcome": outcome(rs["r_star"], r_mean["r_star"])})
                rows.append(row)
                pairs.setdefault(kind, []).append(row["outcome"])
    spread = [o for o in pairs.get("spread", []) if o != "unscored"]
    summary = {"registered_in": "prereg 2026-11-02 17:15 part B (sensitivity, not the verdict)",
               "lane_prediction": aggregate(spread, "prediction"),
               "lane_counter": aggregate(spread, "counter"),
               "spread_outcomes": pairs.get("spread", []),
               "ignites_outcomes_secondary": pairs.get("ignites", []),
               "pairs": rows}
    return summary, rows


def main() -> int:
    plan = passing_plan()
    rows, curves, pairs = [], [], {}
    for tag, thetas in plan.items():
        done, why = network_done(tag, thetas)
        if not done:
            raise SystemExit(f"{tag}: fits incomplete ({why}); not scoring a partial sweep")
        sweep = pd.read_csv(OUT / f"sweep_{tag}.csv")
        root = pd.read_csv(f"sweep_{tag}.csv")
        r_mean = r_star_relative(root, "spread_mean", PRIMARY_TIER, PRIMARY_EPS)
        if r_mean["r_star"] != REGISTERED_R_MEAN[tag]:
            raise SystemExit(f"{tag}: root r*(spread_mean) is {r_mean['r_star']}, registered "
                             f"{REGISTERED_R_MEAN[tag]}; the baseline moved, refusing")
        mean_rule2 = r_star_noise(tau_table(root, "spread_mean", PRIMARY_TIER))["r_star"]

        # Seed-mean tau per (target, radius, rung), every rung, for the report.
        # The dynamic rung is labelled so nobody reads it as scored.
        for (target, rung, r), g in sweep.groupby(["target", "richness", "radius"]):
            curves.append({"network": tag, "target": target, "richness": rung,
                           "radius": int(r), "tau_mean": g.kendall_tau.mean(),
                           "tau_sd": g.kendall_tau.std(ddof=1),
                           "scored_rung": rung == PRIMARY_TIER})

        for theta in thetas:
            for kind in ("spread", "ignites"):
                target = f"{kind}_theta{theta}"
                s = score_target(sweep, target)
                row = {"network": tag, "theta": float(theta), "target": target,
                       "role": "primary" if kind == "spread" else "secondary (post-gate)",
                       "ceiling_tau": s["ceiling_tau"], "scored": s["scored"],
                       "r_star_rule2": s["rule2"],
                       "r_mean_rel005": r_mean["r_star"], "r_mean_rule2": mean_rule2}
                for eps, v in s["relative"].items():
                    row[f"r_star_rel{eps:g}"] = v["r_star"]
                    row[f"agree_rel{eps:g}"] = f"{v['agree']}/{v['n']}"
                row["outcome"] = (outcome(row[f"r_star_rel{PRIMARY_EPS:g}"], r_mean["r_star"])
                                  if s["scored"] else "unscored")
                rows.append(row)
                pairs.setdefault(kind, []).append(row["outcome"])

    spread = [o for o in pairs.get("spread", []) if o != "unscored"]
    verdict = {
        "registered_in": ["prereg 2026-11-02 10:55 part D", "prereg 2026-11-02 16:09 parts A, C"],
        "lane_prediction": aggregate(spread, "prediction"),
        "lane_counter": aggregate(spread, "counter"),
        "spread_outcomes": pairs.get("spread", []),
        "ignites_outcomes_secondary": pairs.get("ignites", []),
        "pairs": rows,
        "sources": {p: sha256(Path(p)) for p in
                    ("analyse_threshold_arm.py", "analyse_beta_sweep.py", "probe_threshold_arm.py")},
    }
    somers, somers_rows = somers_sensitivity(plan)
    verdict["somers_sensitivity"] = somers
    pd.DataFrame(somers_rows).to_csv(OUT / "somers.csv", index=False, lineterminator="\n")
    pd.DataFrame(rows).to_csv(OUT / "rstar.csv", index=False, lineterminator="\n")
    pd.DataFrame(curves).to_csv(OUT / "curves.csv", index=False, lineterminator="\n")
    write_atomic(OUT / "verdict.json", json.dumps(verdict, indent=2, default=str) + "\n")
    print(pd.DataFrame(rows).drop(columns=["theta"]).to_string(index=False))
    print(f"\nlane: prediction {verdict['lane_prediction']}, counter {verdict['lane_counter']}")
    print("\nSomers' D sensitivity (17:15 part B, not the verdict):")
    print(pd.DataFrame(somers_rows).to_string(index=False))
    print(f"lane under Somers' D: prediction {somers['lane_prediction']}, "
          f"counter {somers['lane_counter']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

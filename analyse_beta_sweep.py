"""
Phase 6.5 L1 analyser: the criticality locator and the r* rules for the
beta/beta_c sweep.

Specification: docs/prereg/prereg_phase6_5_lanes.md, the section "L1 execution
definitions - 2026-10-12 12:15 IST" (parts B to E). Read that first; this file
implements it and is not allowed to decide anything it leaves open.

TWO SUBCOMMANDS, AND THE ORDER MATTERS
--------------------------------------
    python analyse_beta_sweep.py locator [--nets TAG ...] [--force]
    python analyse_beta_sweep.py score

`locator` runs NO fits. For every network it draws 500 bond-percolation
realisations at each of 51 multiples m = 0.50, 0.55, ..., 3.00 and records the
susceptibility chi(m) = Var(S1) / Mean(S1) of the largest cluster S1, plus
two secondary locators. It writes results/phase6_5_beta/locator/<tag>.csv and
<tag>.json, and it refuses to overwrite them. The prereg requires the locator
to be fixed BEFORE any L1 cell runs, so an existing locator file is treated as
a registered fact, not as a cache to refresh.

`score` reads each multiple's sweep_<tag>.csv under results/phase6_5_beta/
m<m>/ and computes r* under the registered rules. It refuses to run for a
network whose locator has not been recorded, for the same reason.

THE THIRD r* RULE
-----------------
The target-noise rule follows the prereg section "L1 target-noise rule -
2026-10-12 12:31 IST": a column bootstrap of the live-edge draws, frozen seed-0
OOF predictions, paired across radii, and the same threshold form as rule 2.
It is REPORTED ONLY; the verdict stays on rule 2. Its one registered use is
the robustness label (prereg addendum 13:44): "robust to target noise" when
H1 stands under rule 2 and under rule 3 through the same verdict logic.

Everything is single-process and deterministic: fixed seeds for the draws and
the bootstraps, and no model fits anywhere in this file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from analyse import FULL
# Reused, not re-derived: A7 validated this rebuild against the published
# target columns, and a second copy here could drift from build_targets.
from probe_target_noise import targets_from_cascades
from influence.criticality import transmission_probability
from influence.dynamics import simulate_ic_percolation
from influence.experiment import locality_horizon
from influence.preprocessing import load_edgelist

# ---------------------------------------------------------------------------
# Registered constants (prereg addendum 2026-10-12 12:15, parts B and C).
# Changing any of these is a change to the registration, not a tuning knob.
# ---------------------------------------------------------------------------
NETWORKS = ("ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined",
            "p2p-Gnutella08")
PRIMARY_NETWORKS = ("email-Eu-core", "p2p-Gnutella08")   # the H1 primary claim
SWEEP_MULTIPLES = (0.8, 1.0, 1.25, 2.0, 3.0)

# 0.50 .. 3.00 in steps of 0.05. Built from integers and rounded so that 1.50
# is exactly 1.5 (a float accumulation would give 1.5000000000000002, which
# changes p in the last bit and breaks the bit-identity check E3 relies on).
FINE_GRID = tuple(round(0.50 + 0.05 * k, 2) for k in range(51))
FINE_DRAWS = 500
FINE_SEED = 0         # common seed: draws are coupled across m (prereg B, E2)
BOOT_REPS = 200
BOOT_SEED = 0

PRIMARY_TIER = FULL                              # "node+edge+subgraph"
FULL_TIER = "node+edge+subgraph+dynamic"         # reported beside it
RELATIVE_EPS = (0.10, 0.05, 0.02)
# spread_cv and spread_resid are ill-defined when mean spread is about 1, so
# the prereg excludes them below m = 1.25. Enforced here, not just assumed.
CV_RESID_MIN_M = 1.25
PREDICTED_PEAK = (1.0, 1.25)                     # H1 prediction, inclusive

# Rule 3 (prereg addendum 2026-10-12 12:31): 200 column-bootstrap replicates,
# resampling seed 0, frozen OOF predictions of sweep seed 0 (A7's default).
TN_REPS = 200
TN_SEED = 0
TN_PRED_SEED = 0
TN_SELF_CHECK_TOL = 1e-9

ROOT_MULTIPLE = 1.5          # the root caches were built at 1.5 x beta_c
OUT = Path("results/phase6_5_beta")
LOCATOR_DIR = OUT / "locator"


def mult_dir(m: float) -> Path:
    """Canonical per-multiple directory, results/phase6_5_beta/m0.80 etc.

    Two decimals always, so m=1.0 and m=1.25 cannot collide with anything and
    the controller (which must import this, not re-derive it) agrees on names.
    """
    return OUT / f"m{m:.2f}"


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_atomic(path: Path, text: str) -> None:
    """Write via a temp file and rename, so a kill mid-write leaves no half file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Cluster sizes from a cascade matrix (prereg B, "needs no new draws")
# ---------------------------------------------------------------------------

def largest_two(sizes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """S1 and S2 per draw, from an (n_nodes, n_draws) percolation size matrix.

    simulate_ic_percolation stores, for node i in draw j, the size of i's
    connected component. So a component of size s shows up as exactly s
    entries equal to s, and the number of components of size s is
    count(s) / s. That makes the whole cluster-size distribution recoverable
    from the stored matrix without re-drawing anything.

    S2 is the second-largest COMPONENT, not the second-largest distinct size:
    if two components tie for largest, S2 equals S1. With a single component
    there is no second one and S2 is 0.

    Raises if any count(s) is not a multiple of s. That cannot happen for a
    genuine percolation matrix, so it means the input is something else (a
    direct-simulation matrix, a subsampled one, or corruption), and every
    number computed from it would be meaningless.
    """
    sizes = np.asarray(sizes)
    n_draws = sizes.shape[1]
    s1 = np.empty(n_draws, dtype=np.int64)
    s2 = np.empty(n_draws, dtype=np.int64)
    for j in range(n_draws):
        vals, counts = np.unique(sizes[:, j], return_counts=True)
        if np.any(counts % vals):
            raise ValueError(f"draw {j}: count(s) is not a multiple of s; "
                             "not a bond-percolation component-size column")
        n_comp = counts // vals
        s1[j] = vals[-1]
        if n_comp[-1] >= 2:
            s2[j] = vals[-1]              # two (or more) largest components tie
        elif len(vals) >= 2:
            s2[j] = vals[-2]
        else:
            s2[j] = 0                     # one component covers the graph
    return s1, s2


def susceptibility(s1: np.ndarray) -> float:
    """chi = Var(S1) / Mean(S1), sample variance (ddof = 1), as registered."""
    s1 = np.asarray(s1, dtype=float)
    return float(s1.var(ddof=1) / s1.mean())


def between_node_cv(sizes: np.ndarray) -> float:
    """sd_i / mean_i of each node's mean reached-set size.

    ddof = 0 across nodes: the graph is the population, not a sample from one
    (the same position probe_target_noise.py takes). The prereg does not fix
    this; it is a secondary locator, and with thousands of nodes the choice
    moves the value by well under 0.1%.
    """
    per_node = np.asarray(sizes, dtype=float).mean(axis=1)
    return float(per_node.std(ddof=0) / per_node.mean())


def first_argmax(values, grid) -> float:
    """Grid value at the maximum; np.argmax takes the first, i.e. the smallest m
    on a tie, which is the registered tie rule."""
    return float(grid[int(np.argmax(np.asarray(values, dtype=float)))])


def locator_bin(m_star: float | None) -> float | None:
    """m_loc: the smallest sweep multiple at or above m*_chi (prereg B)."""
    if m_star is None:
        return None
    above = [m for m in SWEEP_MULTIPLES if m >= m_star - 1e-12]
    return min(above) if above else None


def is_boundary(m_star: float) -> bool:
    """An argmax at either end of the fine grid means the peak may lie outside
    it, so the locator is undetermined for that network (prereg B)."""
    return abs(m_star - FINE_GRID[0]) < 1e-12 or abs(m_star - FINE_GRID[-1]) < 1e-12


def bootstrap_argmax(s1_by_m: np.ndarray, reps: int = BOOT_REPS,
                     seed: int = BOOT_SEED) -> np.ndarray:
    """Spread of m*_chi over a bootstrap of the draws.

    s1_by_m is (len(FINE_GRID), n_draws). The SAME resampled draw indices are
    applied at every m in a replicate: draw j at every m comes from the same
    uniforms (the coupling), so resampling j independently per m would break
    the structure that makes the curve smooth and overstate the argmax noise.
    Reported only; the verdict uses the point estimate.
    """
    rng = np.random.default_rng(seed)
    n_draws = s1_by_m.shape[1]
    out = np.empty(reps)
    for b in range(reps):
        idx = rng.integers(0, n_draws, size=n_draws)
        chis = [susceptibility(row[idx]) for row in s1_by_m]
        out[b] = first_argmax(chis, FINE_GRID)
    return out


# ---------------------------------------------------------------------------
# The locator run
# ---------------------------------------------------------------------------

def load_network(tag: str):
    """The network exactly as stage 1 loads it, with beta_c from its cache meta.

    beta_c is read rather than recomputed: it is the value stage 1 records and
    recomputes deterministically, and reusing it avoids a second sparse
    eigensolve. The edge-list path is checked against the cache's provenance
    so a renamed or substituted file cannot pass silently.
    """
    meta = json.loads(Path(f"cache_meta_{tag}.json").read_text(encoding="utf-8"))
    path = Path("data") / f"{tag}.txt"
    recorded = Path(str(meta["provenance"]["source"]).replace("\\", "/"))
    if recorded.as_posix() != path.as_posix():
        raise ValueError(f"{tag}: cache provenance names {recorded}, expected {path}")
    net = load_edgelist(str(path))
    if net.n != meta["n"] or net.m != meta["m"]:
        raise ValueError(f"{tag}: loaded n={net.n}, m={net.m}; cache meta says "
                         f"n={meta['n']}, m={meta['m']}")
    return net, meta, path


def check_root_identity(tag: str, net, meta: dict) -> dict:
    """Prereg E3, against the root 1.5x caches, with no new fits.

    Both stage 1 and this file call simulate_ic_percolation with seed 0, and
    the generator is consumed the same way per draw, so the first 500 columns
    of the root 4,000-draw cache must equal a fresh 500-draw run at m = 1.5
    BIT FOR BIT. That is stronger than the registered "within 3 bootstrap SE"
    test, which is also computed and reported.
    """
    p = transmission_probability(meta["beta_c"], ROOT_MULTIPLE)
    if p != meta["p"]:
        raise ValueError(f"{tag}: p at 1.5 x beta_c is {p!r}; the cache records {meta['p']!r}")
    root = np.load(f"cache_cascades_{tag}.npy", mmap_mode="r")
    fresh = simulate_ic_percolation(net, p=p, n_sims=FINE_DRAWS, convention="uniform",
                                    seed=FINE_SEED, verbose=False).sizes
    identical = bool(np.array_equal(np.asarray(root[:, :FINE_DRAWS]), fresh))
    # The registered SE test: chi from all 4,000 cached draws vs chi from the
    # 500 fresh ones, scaled by the bootstrap SE of the 500-draw value.
    s1_root, _ = largest_two(np.asarray(root))
    s1_fresh, _ = largest_two(fresh)
    chi_root, chi_fresh = susceptibility(s1_root), susceptibility(s1_fresh)
    rng = np.random.default_rng(BOOT_SEED)
    boot = [susceptibility(s1_fresh[rng.integers(0, FINE_DRAWS, FINE_DRAWS)])
            for _ in range(BOOT_REPS)]
    se = float(np.std(boot, ddof=1))
    z = abs(chi_root - chi_fresh) / se if se > 0 else float("inf")
    return {"first_500_columns_identical": identical, "chi_root_4000": chi_root,
            "chi_fresh_500": chi_fresh, "bootstrap_se_500": se, "abs_diff_in_se": z,
            "within_3_se": bool(z <= 3.0), "pass": bool(identical and z <= 3.0)}


def run_locator(tag: str, force: bool = False) -> dict:
    csv_path, json_path = LOCATOR_DIR / f"{tag}.csv", LOCATOR_DIR / f"{tag}.json"
    if json_path.exists() and not force:
        # Fail closed: a recorded locator is part of the registration.
        raise FileExistsError(f"{json_path} exists; the locator is recorded once, "
                              "before any L1 cell. Pass --force only with a LOG entry saying why.")
    t0 = time.time()
    net, meta, edge_path = load_network(tag)
    e3 = check_root_identity(tag, net, meta)
    if not e3["pass"]:
        raise AssertionError(f"{tag}: E3 failed, refusing to record a locator: {e3}")

    rows, s1_rows = [], []
    for m in FINE_GRID:
        p = transmission_probability(meta["beta_c"], m)
        sizes = simulate_ic_percolation(net, p=p, n_sims=FINE_DRAWS, convention="uniform",
                                        seed=FINE_SEED, verbose=False).sizes
        s1, s2 = largest_two(sizes)
        s1_rows.append(s1)
        rows.append({"network": tag, "m": m, "p": p, "beta_c": meta["beta_c"],
                     "n_draws": FINE_DRAWS, "chi": susceptibility(s1),
                     "s1_mean": float(s1.mean()), "s2_mean": float(s2.mean()),
                     "cv_between": between_node_cv(sizes)})
    curve = pd.DataFrame(rows)
    s1_by_m = np.vstack(s1_rows)

    # Coupling sanity on the real graph (E2 is the unit test; this is the
    # same property on the data the verdict will use): S1 per draw never
    # shrinks as m grows.
    coupled = bool(np.all(np.diff(s1_by_m, axis=0) >= 0))

    m_chi = first_argmax(curve["chi"], FINE_GRID)
    determined = not is_boundary(m_chi)
    boot = bootstrap_argmax(s1_by_m)
    summary = {
        "network": tag, "registered_in": "prereg addendum 2026-10-12 12:15 IST, part B",
        "grid": [FINE_GRID[0], FINE_GRID[-1], 0.05], "n_draws": FINE_DRAWS,
        "seed": FINE_SEED, "beta_c": meta["beta_c"],
        "m_star_chi": m_chi, "determined": determined,
        "m_loc": locator_bin(m_chi) if determined else None,
        "secondary": {"m_star_s2": first_argmax(curve["s2_mean"], FINE_GRID),
                      "m_star_cv": first_argmax(curve["cv_between"], FINE_GRID)},
        "bootstrap": {"reps": BOOT_REPS, "seed": BOOT_SEED,
                      "q025": float(np.quantile(boot, 0.025)),
                      "median": float(np.median(boot)),
                      "q975": float(np.quantile(boot, 0.975)),
                      "share_at_point_estimate": float(np.mean(np.isclose(boot, m_chi)))},
        "coupled_s1_nondecreasing": coupled, "e3_root_identity": e3,
        "inputs": {"edge_list": edge_path.as_posix(), "edge_list_sha256": sha256(edge_path),
                   "analyser_sha256": sha256(Path(__file__))},
        "seconds": round(time.time() - t0, 1),
    }
    if not coupled:
        raise AssertionError(f"{tag}: S1 decreased with m on some draw; the draws are not coupled")
    write_atomic(csv_path, curve.to_csv(index=False, lineterminator="\n"))
    write_atomic(json_path, json.dumps(summary, indent=2) + "\n")
    return summary


# ---------------------------------------------------------------------------
# r* rules (prereg C) and the verdict (prereg D)
# ---------------------------------------------------------------------------

def tau_table(sweep: pd.DataFrame, target: str, tier: str) -> pd.DataFrame:
    """Kendall tau as a (radius x seed) table for one target and tier.

    Only seeds present at every radius are kept, so every difference below is
    genuinely paired. Fewer than two such seeds is an error: an SD over one
    value does not exist.
    """
    sub = sweep[(sweep.target == target) & (sweep.richness == tier)]
    if sub.duplicated(["radius", "seed"]).any():
        raise ValueError(f"{target}/{tier}: duplicate (radius, seed) rows")
    tab = sub.pivot(index="radius", columns="seed", values="kendall_tau").sort_index()
    tab = tab.dropna(axis=1)
    if tab.shape[1] < 2:
        raise ValueError(f"{target}/{tier}: fewer than 2 seeds at every radius")
    return tab


def r_star_noise(tab: pd.DataFrame) -> dict:
    """Noise-normalised r* (prereg C rule 2, primary for H1).

    r_c is the radius with the best seed-mean tau (the smaller radius on a
    tie). For each radius r, d_s(r) = tau_s(r_c) - tau_s(r) per seed, and r*
    is the smallest r with mean_s d_s(r) <= 2 * sd_s(d_s(r)), ddof = 1.

    Paired because seed s draws the same folds at every radius. A7 found every
    such covariance positive, so the SD of the difference is far smaller than
    the unpaired SD, and an unpaired yardstick would pass radii too easily and
    bias r* low. r_c always qualifies (d is identically 0 there).
    """
    mean_tau = tab.mean(axis=1)
    r_c = int(mean_tau.index[int(np.argmax(mean_tau.to_numpy()))])
    d = tab.loc[r_c] - tab                         # (radius x seed) paired gaps
    gap = d.mean(axis=1)
    sd = d.std(axis=1, ddof=1)
    ok = gap <= 2 * sd
    r_star = int(min(r for r in tab.index if ok.loc[r]))
    return {"r_star": r_star, "r_ceiling": r_c, "ceiling": float(mean_tau.loc[r_c]),
            "gap": {int(r): float(gap.loc[r]) for r in tab.index},
            "paired_sd": {int(r): float(sd.loc[r]) for r in tab.index},
            "n_seeds": int(tab.shape[1])}


def r_star_relative(sweep: pd.DataFrame, target: str, tier: str, eps: float) -> dict:
    """Relative r*(eps) (prereg C rule 1), reported only.

    Per seed through locality_horizon as implemented, then the MODAL value
    across seeds with its agreement count, the convention analyse_topk.py's
    modal_r_star uses: r* is an ordinal label, so its mean is not meaningful.
    """
    vals = []
    sub = sweep[sweep.target == target]
    for seed in sorted(sub["seed"].unique()):
        h = locality_horizon(sub[sub.seed == seed], epsilon=eps, richness=tier)
        if h.get("r_star") is not None:
            vals.append(h["r_star"])
    if not vals:
        return {"r_star": None, "agree": 0, "n": 0}
    counts = pd.Series(vals).value_counts()
    # value_counts breaks ties by first appearance; make the tie rule explicit
    # (smaller r) so the result cannot depend on seed order.
    top = counts.max()
    return {"r_star": int(min(v for v, c in counts.items() if c == top)),
            "agree": int(top), "n": len(vals)}


def replicate_targets(c: np.ndarray, targets, published: pd.DataFrame,
                      reps: int = TN_REPS, seed: int = TN_SEED) -> dict[str, list]:
    """Rule 3's bootstrap targets: one rebuilt column per replicate per target.

    c is the (n_nodes, n_draws) cascade matrix of one m directory. Each
    replicate resamples the draw indices with replacement and rebuilds the
    targets from those columns. The SAME index set serves every target in a
    replicate (and, through the caller, every radius and tier), which is what
    makes the per-radius differences paired.

    First, the rebuild must reproduce the published targets to 1e-9. If it
    does not, the bootstrap would perturb a column the sweep never trained on,
    and every number from it would be about the wrong quantity, so it raises.
    """
    rebuilt = targets_from_cascades(c)
    for t in targets:
        if not np.allclose(rebuilt[t], published[t].to_numpy(float),
                           rtol=0, atol=TN_SELF_CHECK_TOL, equal_nan=True):
            raise AssertionError(f"{t}: rebuilt target differs from cache_targets "
                                 f"by more than {TN_SELF_CHECK_TOL}")
    rng = np.random.default_rng(seed)
    n_draws = c.shape[1]
    out = {t: [] for t in targets}
    for _ in range(reps):
        idx = rng.integers(0, n_draws, size=n_draws)
        rep = targets_from_cascades(c[:, idx])
        for t in targets:
            out[t].append(rep[t])
    return out


def target_noise_sd(y_reps: list, preds: dict, r_c: int) -> dict:
    """sd_target(r) = SD over replicates of D_b(r) = tau(y_b, pred[r_c]) - tau(y_b, pred[r]).

    Both taus in a replicate are scored against the SAME resampled target, so
    the target noise they share cancels in the difference, exactly as shared
    folds cancel in rule 2. At r = r_c the difference is identically 0.
    """
    out = {}
    for r, pred in preds.items():
        if r == r_c:
            out[int(r)] = 0.0
            continue
        d = [kendalltau(y, preds[r_c]).statistic - kendalltau(y, pred).statistic
             for y in y_reps]
        out[int(r)] = float(np.std(d, ddof=1))
    return out


def r_star_target(gap: dict, sd_target: dict) -> int:
    """Rule 3: the smallest r with (rule 2's seed-mean gap) <= 2 * sd_target(r).

    The left side is deliberately rule 2's gap, so rules 2 and 3 differ only in
    which noise the yardstick measures.
    """
    if set(gap) != set(sd_target):
        raise ValueError(f"radii differ: gap {sorted(gap)} vs sd {sorted(sd_target)}")
    return int(min(r for r in sorted(gap) if gap[r] <= 2 * sd_target[r]))


def verdict(r_by_m: dict, locator: dict) -> dict:
    """Prereg D for one network: flat, m_peak, the prediction and H1.

    r_by_m maps each sweep multiple to the primary series' r*_noise. All five
    multiples must be present; a partial series gets no verdict, because a
    peak found on four of five points could move when the fifth arrives.
    """
    missing = [m for m in SWEEP_MULTIPLES if r_by_m.get(m) is None]
    if missing:
        return {"status": "incomplete", "missing": missing}
    series = [r_by_m[m] for m in SWEEP_MULTIPLES]
    if len(set(series)) == 1:
        return {"status": "scored", "flat": True, "m_peak": None,
                "prediction_met": False, "h1_stands": False,
                "note": "flat: under decision 5, L6 uses one multiple"}
    top = max(series)
    m_peak = min(m for m in SWEEP_MULTIPLES if r_by_m[m] == top)
    determined = bool(locator.get("determined"))
    m_loc = locator.get("m_loc")
    return {"status": "scored", "flat": False, "m_peak": m_peak,
            "prediction_met": PREDICTED_PEAK[0] <= m_peak <= PREDICTED_PEAK[1],
            "locator_determined": determined, "m_loc": m_loc,
            # H1 is not scored where the locator is undetermined (prereg B).
            "h1_stands": (m_peak <= m_loc + 1e-12) if determined else None}


ROBUST = "robust to target noise"
SEED_ONLY = "stands under seed noise; not resolved against target noise"


def robust_label(v_rule2: dict, v_rule3: dict) -> str | None:
    """The registered qualifier on the H1 wording (prereg addendum 13:44).

    A label, not a second verdict: it only says whether a conclusion that
    already stands under rule 2 survives when rule 3's series goes through the
    same verdict logic with the same locator. Where H1 does not stand under
    rule 2, or is not scored, there is nothing to qualify, so no label. The
    frozen-model caveat (rule 3 understates target noise, A7: x1.24 median)
    belongs to any text that quotes the label.
    """
    if v_rule2.get("h1_stands") is not True:
        return None
    return ROBUST if v_rule3.get("h1_stands") is True else SEED_ONLY


def targets_for(m: float, present) -> list[str]:
    """Spread targets scored at multiple m, with the registered exclusion."""
    keep = []
    for t in ("spread_mean", "spread_cv", "spread_resid"):
        if t not in present:
            continue
        if t in ("spread_cv", "spread_resid") and m < CV_RESID_MIN_M:
            continue
        keep.append(t)
    return keep


def run_score() -> int:
    rows, verdicts = [], {}
    for tag in NETWORKS:
        loc_path = LOCATOR_DIR / f"{tag}.json"
        if not loc_path.exists():
            print(f"{tag}: no recorded locator; refusing to score (prereg B: locator first)")
            continue
        locator = json.loads(loc_path.read_text(encoding="utf-8"))
        primary, primary_target_rule = {}, {}
        for m in SWEEP_MULTIPLES:
            path = mult_dir(m) / f"sweep_{tag}.csv"
            if not path.exists():
                continue
            sweep = pd.read_csv(path)
            scored = targets_for(m, set(sweep.target))
            # Rule 3's inputs, from the same directory the sweep was fitted in.
            d = mult_dir(m)
            c = np.load(d / f"cache_cascades_{tag}.npy")
            y_reps = replicate_targets(c, scored, pd.read_csv(d / f"cache_targets_{tag}.csv"))
            del c
            oof = np.load(d / f"cache_oof_{tag}.npz")
            for target in scored:
                for tier in (PRIMARY_TIER, FULL_TIER):
                    res = r_star_noise(tau_table(sweep, target, tier))
                    rows.append({"network": tag, "m": m, "target": target, "tier": tier,
                                 "rule": "noise_paired_2sd", "eps": None,
                                 "r_star": res["r_star"], "agree": None,
                                 "r_ceiling": res["r_ceiling"], "ceiling": res["ceiling"]})
                    preds = {r: oof[f"{target}|{r}|{tier}|{TN_PRED_SEED}"]
                             for r in res["gap"]}
                    sd_t = target_noise_sd(y_reps[target], preds, res["r_ceiling"])
                    r3 = r_star_target(res["gap"], sd_t)
                    rows.append({"network": tag, "m": m, "target": target, "tier": tier,
                                 "rule": "target_noise_paired_2sd", "eps": None,
                                 "r_star": r3, "agree": None,
                                 "r_ceiling": res["r_ceiling"], "ceiling": res["ceiling"]})
                    if target == "spread_mean" and tier == PRIMARY_TIER:
                        primary[m] = res["r_star"]
                        primary_target_rule[m] = r3
                    for eps in RELATIVE_EPS:
                        rel = r_star_relative(sweep, target, tier, eps)
                        rows.append({"network": tag, "m": m, "target": target, "tier": tier,
                                     "rule": "relative_modal", "eps": eps,
                                     "r_star": rel["r_star"], "agree": rel["agree"],
                                     "r_ceiling": None, "ceiling": None})
        verdicts[tag] = {"primary_network": tag in PRIMARY_NETWORKS,
                         "r_star_noise_spread_mean": {str(m): primary.get(m)
                                                      for m in SWEEP_MULTIPLES},
                         # Rule 3, reported only (prereg 12:31): it feeds the
                         # robustness label, never the verdict itself.
                         "r_star_target_spread_mean": {str(m): primary_target_rule.get(m)
                                                       for m in SWEEP_MULTIPLES},
                         "m_star_chi": locator["m_star_chi"],
                         **verdict(primary, locator)}
        v3 = verdict(primary_target_rule, locator)
        verdicts[tag]["rule3_verdict"] = v3
        verdicts[tag]["robust_label"] = robust_label(verdicts[tag], v3)
    if not rows:
        print("nothing to score yet")
        return 0
    write_atomic(OUT / "rstar.csv", pd.DataFrame(rows).to_csv(index=False, lineterminator="\n"))
    write_atomic(OUT / "verdict.json", json.dumps(
        {"registered_in": "prereg addendum 2026-10-12 12:15 IST, parts C-D",
         "target_noise_rule": "reported only (prereg addendum 2026-10-12 12:31)",
         "networks": verdicts}, indent=2) + "\n")
    for tag, v in verdicts.items():
        print(f"{tag:20s} {v.get('status'):10s} m_peak={v.get('m_peak')} "
              f"m_loc={v.get('m_loc')} H1={v.get('h1_stands')} label={v.get('robust_label')}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    lo = sub.add_parser("locator", help="record the fine-grid locator (no fits)")
    lo.add_argument("--nets", nargs="+", default=list(NETWORKS))
    lo.add_argument("--force", action="store_true")
    sub.add_parser("score", help="score the per-multiple sweeps")
    args = ap.parse_args(argv)
    if args.cmd == "locator":
        for tag in args.nets:
            s = run_locator(tag, force=args.force)
            print(f"{tag:20s} m*_chi={s['m_star_chi']:.2f} determined={s['determined']} "
                  f"m_loc={s['m_loc']} boot95=[{s['bootstrap']['q025']:.2f}, "
                  f"{s['bootstrap']['q975']:.2f}] E3={s['e3_root_identity']['pass']} "
                  f"({s['seconds']} s)", flush=True)
        return 0
    return run_score()


if __name__ == "__main__":
    sys.exit(main())

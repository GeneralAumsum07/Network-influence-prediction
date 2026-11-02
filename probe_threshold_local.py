"""L5 exact r-local probe (0 fits), registered 2026-11-02 16:59 IST.

docs/prereg/prereg_phase6_5_lanes.md, "L5 exact r-local probe". For each
network that passed the L5 gate, at its passing theta:
  trunc_r(i)   ball-truncated cascade size (influence/threshold_local.py)
  tau_r        Kendall tau-b(trunc_r, spread_theta), all n nodes, exact
  tau_r_ign    tau-b(trunc_r, ignites_theta)
  certified_r  fraction of igniters with trunc_r > 0.05 n (proven from radius r)
  coverage_r   mean and median |B_r(i)| / n
for r = 1..3 (scored) and 4..5 (convergence only), then part D's rule:
  r*_exact     smallest r in {1,2,3} with tau_r >= 0.95, else "> 3"
  r*_exact_ign smallest r in {1,2,3} with tau_r_ign >= 0.95 * tau-b(spread, ignites)
  counter      supported iff r* <= 2; flagged "ball near-global" when the
               mean coverage at the reported r* is >= 0.5.
Not part of the L5 lane verdict; each network is reported on its own.

Reads only gate.json and sizes_<tag>.npz (the gate's own numbers). It reads
no stage-2 output, so it may run while the L5 fits are in progress.

Run from the repo root: python probe_threshold_local.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.stats import kendalltau

from analyse_beta_sweep import load_network
from influence.threshold_local import truncated_threshold_sizes
from probe_threshold_arm import IGNITION_FRAC, OUT, passing_plan, sha256, write_atomic

RADII = (1, 2, 3, 4, 5)
SCORED = (1, 2, 3)
TAU_BAR = 0.95            # relative eps = 0.05 against a ceiling of exactly 1
COVERAGE_FLAG = 0.5


def ball_sizes(net, radii, batch_size: int = 256) -> dict[int, np.ndarray]:
    """{r: |B_r(i)|} for every node, by the same incremental ball growth the
    module uses. Kept here rather than exported from the module because only
    the report needs it; the cascade never uses the sizes, only the masks."""
    a = sp.csr_matrix(net.adj, dtype=np.int64)
    n = a.shape[0]
    out = {r: np.empty(n, dtype=np.int64) for r in radii}
    for start in range(0, n, batch_size):
        stop = min(n, start + batch_size)
        ball = np.zeros((n, stop - start), dtype=bool)
        ball[np.arange(start, stop), np.arange(stop - start)] = True
        reached = 0
        for r in sorted(radii):
            for _ in range(r - reached):
                ball = ball | ((a @ ball.astype(np.int64)) > 0)
            reached = r
            out[r][start:stop] = ball.sum(axis=0)
    return out


def tau_b(x, y) -> float:
    # scipy's default variant is tau-b, the one stage 2 reports. A constant
    # input (trunc_r for a regular graph, say) gives nan, kept as None.
    t = kendalltau(x, y).statistic
    return None if np.isnan(t) else float(t)


def first_reaching(values: dict[int, float | None], bar: float):
    hits = [r for r in SCORED if values[r] is not None and values[r] >= bar]
    return min(hits) if hits else "> 3"


def probe_one(tag: str, theta: str) -> dict:
    net, _, path = load_network(tag)
    with np.load(OUT / f"sizes_{tag}.npz") as z:
        node, spread = z["node"], z[f"theta{theta}"]
    # Same node order as the gate's arrays, or the comparison is meaningless.
    if not np.array_equal(node, np.arange(net.n)):
        raise SystemExit(f"{tag}: sizes_{tag}.npz is not in loader order")
    n = net.n
    ignites = (spread > IGNITION_FRAC * n).astype(np.int64)

    t0 = time.perf_counter()
    trunc = truncated_threshold_sizes(net, float(theta), RADII)
    balls = ball_sizes(net, RADII)
    secs = time.perf_counter() - t0
    # The registered properties, checked again on the real network: a lower
    # bound that never shrinks with r, and degree + 1 at r = 1.
    deg = np.asarray(net.adj.sum(axis=1)).ravel()
    assert (trunc[1] == deg + 1).all(), tag
    for r in RADII:
        assert (trunc[r] <= spread).all(), (tag, r)
        if r > RADII[0]:
            assert (trunc[r] >= trunc[r - 1]).all(), (tag, r)

    ceiling_ign = tau_b(spread, ignites)
    per_r = {}
    for r in RADII:
        cov = balls[r] / n
        per_r[r] = {"tau": tau_b(trunc[r], spread),
                    "tau_ign": tau_b(trunc[r], ignites),
                    "certified": float((trunc[r][ignites == 1] > IGNITION_FRAC * n).mean()),
                    "exact_fraction": float((trunc[r] == spread).mean()),
                    "coverage_mean": float(cov.mean()),
                    "coverage_median": float(np.median(cov)),
                    "scored": r in SCORED}

    def verdict(r_star):
        if r_star == "> 3":
            return {"r_star": r_star, "counter": "not supported", "ball_near_global": None}
        flag = per_r[r_star]["coverage_mean"] >= COVERAGE_FLAG
        return {"r_star": r_star,
                "counter": "supported" if r_star <= 2 else "not supported",
                "ball_near_global": bool(flag)}

    return {"theta": float(theta), "n": n, "edge_list_sha256": sha256(path),
            "seconds": round(secs, 2), "ceiling_ign": ceiling_ign,
            "per_radius": {str(r): v for r, v in per_r.items()},
            "spread": verdict(first_reaching({r: per_r[r]["tau"] for r in SCORED}, TAU_BAR)),
            "ignites": verdict(first_reaching({r: per_r[r]["tau_ign"] for r in SCORED},
                                              TAU_BAR * ceiling_ign))}


def main() -> int:
    plan = passing_plan()
    result = {"registered_in": "prereg addendum 2026-11-02 16:59 IST, L5 exact r-local probe",
              "rule": {"tau_bar": TAU_BAR, "coverage_flag": COVERAGE_FLAG,
                       "scored_radii": list(SCORED), "radii": list(RADII)},
              "sources": {p: sha256(Path(p)) for p in
                          ("probe_threshold_local.py", "influence/threshold_local.py",
                           "influence/threshold_dynamics.py", "probe_threshold_arm.py",
                           "analyse_beta_sweep.py")},
              "networks": {}}
    for tag, thetas in plan.items():
        for theta in thetas:
            res = probe_one(tag, theta)
            result["networks"][f"{tag}@{theta}"] = res
            taus = "  ".join(f"r{r} {res['per_radius'][str(r)]['tau']:.3f}" for r in RADII)
            print(f"{tag}@{theta}: {taus}  -> r*={res['spread']['r_star']} "
                  f"({res['spread']['counter']}), {res['seconds']:.0f} s", flush=True)
    write_atomic(OUT / "local_exact.json", json.dumps(result, indent=2) + "\n")
    print("wrote", OUT / "local_exact.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

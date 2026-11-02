"""L5 complex-contagion arm: the ignition gate (0 fits).

Registered in docs/prereg/prereg_phase6_5_lanes.md, "L5 execution definitions"
(2026-11-02 10:55), part C. Per (network, theta):
  spread_theta(i) = final size of the fractional-threshold cascade seeded on N[i]
  ignites(i)      = spread_theta(i) > 0.05 * n   (strict, as production's
                    CascadeResults.ignition_probability(0.05))
  gate passes     = mean ignites in [0.1, 0.9], inclusive.

Everything is written under results/phase7_threshold/, never the repo root:
  sizes_<tag>.npz  per-node sizes at every theta, with node order and original
                   ids, so the pilot builds its targets from these exact numbers
                   rather than re-running the cascade
  gate.json        the verdict per (network, theta), with source hashes

Run from the repo root: python probe_threshold_arm.py gate
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

from analyse_beta_sweep import NETWORKS, load_network
from influence.threshold_dynamics import exact_theta, threshold_cascade_sizes

THETAS = (0.1, 0.2)
IGNITION_FRAC = 0.05          # strict ">", the production spread_ignition cut
GATE_BAND = (0.1, 0.9)        # inclusive
OUT = Path("results/phase7_threshold")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, text: str) -> None:
    # Write-then-rename, so a host reset mid-write can never leave a truncated
    # gate.json that reads as a valid (and wrong) verdict.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def gate_one(sizes: np.ndarray, n: int) -> dict:
    """Gate verdict for one (network, theta) from its per-node sizes."""
    ignites = sizes > IGNITION_FRAC * n
    frac = float(ignites.mean())
    q = np.quantile(sizes, [0, .1, .25, .5, .75, .9, 1])
    return {"ignition_fraction": frac,
            "passes": bool(GATE_BAND[0] <= frac <= GATE_BAND[1]),
            "n_ignite": int(ignites.sum()),
            "size_quantiles": dict(zip(["min", "q10", "q25", "median", "q75", "q90", "max"],
                                       [float(x) for x in q])),
            # Distinct sizes: a target with very few distinct values ranks
            # mostly by ties, which matters for reading tau later.
            "n_distinct_sizes": int(np.unique(sizes).size)}


def run_gate() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {p: sha256(Path(p)) for p in
               ("probe_threshold_arm.py", "influence/threshold_dynamics.py",
                "analyse_beta_sweep.py")}
    result = {"registered_in": "prereg addendum 2026-11-02 10:55 IST, part C",
              "ignition": f"size > {IGNITION_FRAC} * n", "band": list(GATE_BAND),
              "thetas": list(THETAS), "sources": sources, "networks": {}}
    for tag in NETWORKS:
        net, meta, path = load_network(tag)
        per = {"n": net.n, "m": net.m, "edge_list_sha256": sha256(path)}
        arrays = {"node": np.arange(net.n), "original_id": np.asarray(net.original_ids)}
        for theta in THETAS:
            t0 = time.perf_counter()
            sizes = threshold_cascade_sizes(net, theta)
            secs = time.perf_counter() - t0
            g = gate_one(sizes, net.n)
            g["seconds"] = round(secs, 2)
            per[f"theta{theta}"] = g
            arrays[f"theta{theta}"] = sizes
            print(f"{tag:18s} theta={theta}: ignition {g['ignition_fraction']:.3f} "
                  f"({'PASS' if g['passes'] else 'fail'}), median size "
                  f"{g['size_quantiles']['median']:.0f} of n={net.n}, {secs:.1f} s", flush=True)
        np.savez(OUT / f"sizes_{tag}.npz", **arrays)
        result["networks"][tag] = per
    passing = [(t, th) for t in NETWORKS for th in THETAS
               if result["networks"][t][f"theta{th}"]["passes"]]
    result["passing"] = [f"{t}@{th}" for t, th in passing]
    result["verdict"] = ("gate passes on some pairs: fits run on those only" if passing
                         else "gate fails everywhere: report the gate, no fits (prereg section 3)")
    write_atomic(OUT / "gate.json", json.dumps(result, indent=2) + "\n")
    print(f"passing: {result['passing'] or 'none'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["gate"])
    args = ap.parse_args(argv)
    # Validate the registered thetas once, up front, rather than mid-run.
    for theta in THETAS:
        exact_theta(theta)
    return run_gate()


if __name__ == "__main__":
    sys.exit(main())

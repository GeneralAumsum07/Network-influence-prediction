"""
Stage 1: everything expensive and deterministic, saved to disk.

Split out from the sweep so that a slow model fit can never cost us the
simulation and feature work again.

Usage:
    python stage1_prepare.py <edgelist> [n_sims] [beta_c multiple] [convention]

The third argument is the important one. We do NOT fix p at an absolute
number - that would put different networks in different dynamical regimes and
make any cross-network comparison meaningless. Instead we compute each
network's own epidemic threshold beta_c and work at a fixed multiple of it,
so `1.5` means the same regime everywhere.

KEEP THE MULTIPLE THE SAME ACROSS NETWORKS YOU INTEND TO COMPARE. The pilot
corpus was originally built with ca-GrQc and p2p-Gnutella08 at 1.5x but
email-Eu-core at 1.2x, which quietly reintroduced exactly the confound the
beta_c normalisation exists to remove - and it mattered, because the sign of
the degree/volatility relationship differs between those networks.
"""
import sys, json, time, platform
import numpy as np
import pandas as pd

from influence.preprocessing import load_edgelist, describe
from influence.criticality import (
    threshold_report, epidemic_threshold, transmission_from_threshold,
)
from influence.dynamics import simulate_ic_percolation
from influence.features import extract_features
from influence.targets import build_targets

path = sys.argv[1]
n_sims = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
mult = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
convention = sys.argv[4] if len(sys.argv) > 4 else "uniform"

MAX_HOP = 3
SIM_SEED = 0

net = load_edgelist(path)
print(describe(net), flush=True)

print("\n[1] threshold", flush=True)
print(threshold_report(net), flush=True)
bc = epidemic_threshold(net)
# Validate before the first simulator or cache write.  Passing the beta_c we
# have just computed preserves one authoritative metadata value and avoids a
# second sparse non-backtracking eigensolve solely for probability validation.
p = transmission_from_threshold(net, mult, threshold=bc)
print(f"  p = {mult} x beta_c = {p:.5f}", flush=True)

print(f"\n[2] cascades ({n_sims} runs, convention={convention})", flush=True)
t0 = time.time()
cas = simulate_ic_percolation(net, p=p, n_sims=n_sims, convention=convention,
                              seed=SIM_SEED, verbose=False)
cascade_seconds = time.time() - t0
print(f"  {cascade_seconds:.1f}s", flush=True)
print(cas.noise_report(), flush=True)

print("\n[3] features", flush=True)
t0 = time.time()
X, reg, timings = extract_features(net, max_hop=MAX_HOP, verbose=True,
                                   p_transmission=p)
feature_seconds = time.time() - t0
print(f"  total {feature_seconds:.2f}s", flush=True)

print("\n[4] targets", flush=True)
t0 = time.time()
Y = build_targets(net, cas, include_betweenness=True, verbose=True)
target_seconds = time.time() - t0
print(f"  {target_seconds:.1f}s", flush=True)

tag = net.name
X.to_csv(f"cache_features_{tag}.csv", index=False)
Y.to_csv(f"cache_targets_{tag}.csv", index=False)
reg.to_csv(f"cache_registry_{tag}.csv", index=False)
np.save(f"cache_cascades_{tag}.npy", cas.sizes)

# Provenance. Everything here is something a result might later need to be
# explained by. The convention, max_hop and seed were previously NOT recorded,
# which meant a cache could not be distinguished from one built under
# different simulation settings - the exact ambiguity the manifest checksums
# exist to prevent on the data side.
def _versions() -> dict:
    import numpy, scipy, sklearn, pandas as pdmod
    out = {"python": platform.python_version(),
           "numpy": numpy.__version__, "scipy": scipy.__version__,
           "scikit-learn": sklearn.__version__, "pandas": pdmod.__version__}
    try:
        import igraph
        out["python-igraph"] = igraph.__version__
    except ImportError:
        out["python-igraph"] = None
    return out


json.dump({"timings": timings, "beta_c": bc, "p": p, "multiple": mult,
           "n_sims": n_sims, "convention": convention,
           "simulation_seed": SIM_SEED, "max_hop": MAX_HOP,
           "n": int(net.n), "m": int(net.m),
           "mean_degree": float(net.mean_degree),
           "stage_seconds": {"cascades": cascade_seconds,
                             "features": feature_seconds,
                             "targets": target_seconds},
           "versions": _versions(),
           "provenance": net.provenance},
          open(f"cache_meta_{tag}.json", "w"), indent=2)
print(f"\nCHECKPOINTED {tag}: {X.shape[1]-2} features, {Y.shape[1]-1} targets",
      flush=True)

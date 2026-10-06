"""
stage0_generate.py
==================
Build the synthetic families for the structural sweep.

WHAT THIS PRODUCES
------------------
Edge lists in data/synthetic/, one file per graph, plus a manifest recording
each graph's generator settings and measured structural profile.

Writing plain edge lists rather than passing objects in memory is deliberate:
stage1_prepare.py then runs on a synthetic graph with NO code change and NO
special case. Synthetic and real networks go down exactly the same path,
which is the only way their r* values are comparable.

THE FOUR FAMILIES
-----------------
Each sweeps ONE structural parameter with everything else held as fixed as
the generator allows.

  gamma       Chung-Lu, mean degree fixed at 6. Degree tail heaviness.
  clustering  Holme-Kim, m fixed at 3. Triangle density at a fixed tail.
  assortativity  Xulvi-Brunet-Sokolov rewiring of one BA graph. Degree
                 sequence held EXACTLY fixed - only the wiring changes.
  community   LFR, mu sweep. How porous the community walls are.

Plus controls: ER (no tail, no clustering), BA (tail, no clustering),
WS (clustering, no tail).

A NOTE ON gamma AS AN AXIS - READ BEFORE PLOTTING
--------------------------------------------------
We measured how precisely gamma can be estimated at these network sizes
(gamma_uncertainty.py). The answer is: not very. At n = 6,300 the bootstrap
standard deviation is 0.10 to 0.38 depending on the true value, and at
n = 1,000 with a steep tail the estimator fails outright.

So the gamma family is plotted against the generator's TARGET gamma, which
is known by construction and has no measurement error, not against the
fitted gamma. The fitted value is still recorded in the manifest, with its
error bar and reliability flag, because the honest version of this result
has to show how noisy the measurement is - and because the real networks
have no target gamma, only a fitted one.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp

from influence import generators as gen
from influence import structure as st
from influence.preprocessing import Network

N_DEFAULT = 5000
MEAN_DEGREE = 6.0


def write_edgelist(net: Network, path: Path) -> None:
    """Dump a Network back out as a plain two-column edge list."""
    c = sp.triu(net.adj, k=1).tocoo()
    with open(path, "w") as fh:
        fh.write(f"# {net.name}\n")
        fh.write(f"# generator={net.provenance.get('generator')}\n")
        fh.write(f"# params={json.dumps(net.provenance.get('generator_params', {}))}\n")
        for u, v in zip(c.row, c.col):
            fh.write(f"{u}\t{v}\n")


def build_families(n: int, seed: int, families: set[str]) -> list[Network]:
    """Construct every requested family. Returns a flat list of Networks."""
    nets = []

    if "gamma" in families:
        print("\n[gamma] Chung-Lu, tail exponent sweep at fixed mean degree")
        for g in [2.1, 2.3, 2.5, 2.8, 3.0, 3.3, 3.6, 4.0]:
            net = gen.chung_lu(n, g, mean_degree=MEAN_DEGREE, seed=seed)
            nets.append(net)
            print(f"   gamma_target={g:.1f}  n={net.n:,}  <k>={net.mean_degree:.2f}  "
                  f"k_max={int(net.degree.max())}")

    if "clustering" in families:
        print("\n[clustering] Holme-Kim, triangle density sweep at fixed tail")
        for p in [0.0, 0.15, 0.3, 0.45, 0.6, 0.8, 1.0]:
            net = gen.holme_kim(n, 3, p, seed=seed)
            nets.append(net)
            c = st.clustering_measures(net)
            print(f"   p_triad={p:.2f}  n={net.n:,}  avg_clustering={c['average_clustering']:.4f}")

    if "assortativity" in families:
        print("\n[assortativity] Xulvi-Brunet-Sokolov, degree sequence held EXACTLY fixed")
        base = gen.barabasi_albert(n, 3, seed=seed)
        print(f"   base BA: n={base.n:,}  assortativity={st.degree_assortativity(base):+.4f}")
        for target in [-0.35, -0.2, -0.1, 0.0, 0.1, 0.25, 0.4]:
            net = gen.rewire_to_assortativity(base, target,
                                              n_steps=40 * base.m, seed=seed)
            nets.append(net)
            got = st.degree_assortativity(net)
            same = np.array_equal(np.sort(base.degree), np.sort(net.degree))
            print(f"   target={target:+.2f}  achieved={got:+.4f}  degrees_preserved={same}")

    if "community" in families:
        print("\n[community] LFR, mixing parameter sweep")
        for mu in [0.05, 0.1, 0.2, 0.3, 0.45, 0.6]:
            try:
                net = gen.lfr(n, mu=mu, mean_degree=MEAN_DEGREE, seed=seed)
                nets.append(net)
                print(f"   mu={mu:.2f}  n={net.n:,}  <k>={net.mean_degree:.2f}")
            except Exception as e:
                # LFR genuinely fails to converge for some parameter sets.
                # Report and move on rather than silently substituting
                # different settings, which would corrupt the sweep.
                print(f"   mu={mu:.2f}  FAILED to converge: {e}")

    if "controls" in families:
        print("\n[controls] the three corner cases")
        for net in [gen.erdos_renyi(n, MEAN_DEGREE, seed=seed),
                    gen.barabasi_albert(n, 3, seed=seed),
                    gen.watts_strogatz(n, 6, 0.1, seed=seed)]:
            nets.append(net)
            print(f"   {net.name}: n={net.n:,}  <k>={net.mean_degree:.2f}")

    return nets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N_DEFAULT)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/synthetic")
    ap.add_argument("--bootstrap", type=int, default=200,
                    help="bootstrap replicates for the gamma error bar; 0 to skip")
    ap.add_argument("--families", default="gamma,clustering,assortativity,community,controls")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    families = set(args.families.split(","))

    nets = build_families(args.n, args.seed, families)

    print(f"\n[profile] measuring structure for {len(nets)} graphs "
          f"(bootstrap={args.bootstrap})")
    manifest = []
    for net in nets:
        path = out / f"{net.name}.txt"
        write_edgelist(net, path)

        prof = st.structural_profile(net, n_bootstrap=args.bootstrap,
                                     seed=args.seed)
        prof["path"] = str(path)
        prof["generator"] = net.provenance.get("generator")
        prof["generator_params"] = net.provenance.get("generator_params", {})
        manifest.append(prof)

        flag = "" if prof.get("gamma_reliable") else "  [gamma unreliable]"
        print(f"   {net.name:34s} gamma={prof['gamma']:.2f}"
              f"+/-{prof.get('gamma_std', float('nan')):.2f} "
              f"assort={prof['assortativity']:+.3f} "
              f"C={prof['average_clustering']:.3f}{flag}")

    mpath = out / "manifest.json"
    json.dump(manifest, open(mpath, "w"), indent=2, default=str)
    print(f"\nwrote {len(manifest)} edge lists + {mpath}")
    print("\nNext, for each graph:")
    print("   python stage1_prepare.py <path> 2000 1.5")
    print("   python stage2_sweep.py <tag> spread_mean,spread_cv,betweenness 3")


if __name__ == "__main__":
    main()

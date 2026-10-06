"""
Why does tau(b_k, b) DIP from k=2 to k=3 on ca-HepTh and p2p-Gnutella08?

THE FACT THAT REFRAMES THE QUESTION, AND IT IS A PROOF NOT A MEASUREMENT
------------------------------------------------------------------------
Raw b_k(v) is monotone NON-DECREASING in k, for every node, by construction:

    b_k(v) = sum over pairs (s,t) with d(s,t) <= k of sigma_st(v)/sigma_st

Each pair either has d(s,t) <= k - in which case it contributes a fixed,
non-negative share that does not depend on k - or it does not, and contributes
zero. Raising k can only move pairs from the second category to the first. No
term can shrink. Therefore **no node's score goes down.**

So the dip is NOT a value decreasing, and it is not an implementation bug -
that possibility is excluded by the definition rather than by re-auditing the
code. It is a RANK REVERSAL: different nodes approach their ceiling at
different RATES in k, so agreement with the true ranking can move
non-monotonically while every underlying value climbs.

(The monotonicity is asserted against the actual arrays below anyway. The proof
says what must be true of `truncated_betweenness`; the assertion says the code
implements the thing the proof is about. Those are different claims and this
project has been bitten by conflating them before.)

THE HYPOTHESIS UNDER TEST
-------------------------
Hubs and bridges converge at different rates.

  - A LOCAL HUB's betweenness is dominated by short-range pairs. It saturates
    early - most of its final value is already present at k=2.
  - A genuine LONG-RANGE BRIDGE only accrues importance from far-apart pairs.
    Its value is invisible at k=2 and only starts appearing once k is large
    enough to count those paths.

If so, hubs win the ranking at k=2, get partially displaced as bridges start
contributing at k=3, and the resort has not finished - producing exactly a dip.
The prediction is directional and therefore falsifiable: **the nodes driving
the drop should skew to ABOVE-average degree** (hubs losing ground they held on
a technicality), and the networks showing the dip should have a sharper
hub/bridge split than the ones that do not.

HOW "THE NODES DRIVING THE DROP" IS DEFINED
-------------------------------------------
tau is a pairwise statistic, so attributing it to nodes needs care. We use the
exact decomposition: for node v under predictor p,

    c_p(v) = sum over u != v of sign(b(v) - b(u)) * sign(p(v) - p(u))

which counts v's concordant pairs minus its discordant ones (ties contribute
zero, exactly as tau-b's numerator treats them). Summing c_p over v gives
2*(C - D), so this is a genuine partition of the statistic and not a heuristic
proxy. A node's contribution to the DIP is then

    Delta(v) = c_3(v) - c_2(v)

and sum(Delta) = 2 * (change in C - D). Negative Delta means v is ranked worse
at k=3 than at k=2.

Usage:
    python probe_betweenness_k_dip.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import hypergeom, kendalltau, mannwhitneyu

from analyse_betweenness_k import manifest_paths
from influence.preprocessing import load_edgelist
from influence.targets import truncated_betweenness

KMAX = 4
CHUNK = 512


def pair_contributions(true: np.ndarray, pred: np.ndarray) -> np.ndarray:
    """
    Per-node concordant-minus-discordant counts, exactly.

    Chunked over rows because the full sign matrix is n^2 doubles - 600 MB on
    ca-HepTh - and there is no need to hold it. Chunking is arithmetic-identical
    to the whole-matrix version, not an approximation.
    """
    n = len(true)
    out = np.zeros(n, dtype=np.float64)
    for i in range(0, n, CHUNK):
        j = min(i + CHUNK, n)
        st = np.sign(true[i:j, None] - true[None, :])
        sp = np.sign(pred[i:j, None] - pred[None, :])
        out[i:j] = (st * sp).sum(axis=1)
    return out


def main() -> int:
    paths = manifest_paths()
    # allow_pickle is required because the atlas is a nested dict of arrays,
    # not a rectangular array. It is safe here for a specific reason, not by
    # assumption: this file is written by THIS repo's analyse_failures.py:468
    # into the repo root, is never fetched or received from anywhere, and is
    # read the same way by the existing make_fig2.py. Do not extend this
    # pattern to any .npy that arrives from outside the project.
    atlas_path = "cache_failure_atlas.npy"
    atlas = (np.load(atlas_path, allow_pickle=True).item()
             if os.path.exists(atlas_path) else {})

    summary = []
    for tag, path in paths.items():
        print(f"\n{'=' * 74}\n{tag}\n{'=' * 74}")
        net = load_edgelist(path, name=tag)
        bc = pd.read_csv(f"cache_targets_{tag}.csv")["betweenness"].to_numpy(float)
        deg = net.degree.astype(float)

        bk = {k: truncated_betweenness(net, k) for k in range(2, KMAX + 1)}

        # --- the monotonicity assertion (see the module docstring) ----------
        viol = [(k, int(np.sum(bk[k + 1] < bk[k] - 1e-9)))
                for k in range(2, KMAX)]
        bad = [f"k={k}->{k+1}: {c}" for k, c in viol if c]
        print(f"  monotone in k, per node: "
              f"{'OK (0 violations)' if not bad else 'VIOLATED ' + '; '.join(bad)}")
        if bad:
            raise AssertionError(
                f"{tag}: b_k decreased for some node as k grew. That "
                f"contradicts the definition, so truncated_betweenness is "
                f"wrong - the dip investigation is moot until this is fixed.")

        taus = {k: kendalltau(bc, bk[k]).statistic for k in bk}
        dip = taus[3] - taus[2]
        print(f"  tau: k=2 {taus[2]:.4f}   k=3 {taus[3]:.4f}   "
              f"k=4 {taus[4]:.4f}   (k2->k3 change {dip:+.4f})")

        # --- CHECK 1: who drives the change, and are they hubs? -------------
        c2 = pair_contributions(bc, bk[2])
        c3 = pair_contributions(bc, bk[3])
        delta = c3 - c2

        # "Driving" = the nodes that got worse, weighted by how much. A fixed
        # top-N would compare different fractions across networks of different
        # size, so use the nodes carrying the first half of the total loss -
        # a definition that adapts to how concentrated the effect is.
        loss = np.where(delta < 0, -delta, 0.0)
        order = np.argsort(loss)[::-1]
        cum = np.cumsum(loss[order])
        half = int(np.searchsorted(cum, 0.5 * loss.sum())) + 1
        drivers = order[:half]

        # Nodes that gained, for the mirror comparison. The hypothesis is
        # DIRECTIONAL - hubs lose, bridges gain - so testing only the losers
        # would leave the other half of the prediction unexamined.
        gain = np.where(delta > 0, delta, 0.0)
        gorder = np.argsort(gain)[::-1]
        gcum = np.cumsum(gain[gorder])
        ghalf = int(np.searchsorted(gcum, 0.5 * gain.sum())) + 1
        gainers = gorder[:ghalf]

        # THE REFERENCE POPULATION IS THE NONZERO SET, NOT THE WHOLE GRAPH,
        # and getting this wrong would have manufactured the result.
        #
        # Roughly half of every network in this corpus is simplicial (b = 0,
        # §24.1) and those nodes have b_k = 0 at EVERY k, so they can never
        # appear in `drivers` or `gainers`. Comparing the movers' degree
        # against the whole graph's median therefore compares "nodes that can
        # move" against "nodes that mostly cannot" - and since simplicial nodes
        # are overwhelmingly low-degree, that test comes out significant no
        # matter what the hub/bridge story is. Against the nonzero set the
        # comparison is between nodes that were all eligible to move.
        nzmask = bc > 0
        ref = deg[nzmask]
        med_all, med_nz = float(np.median(deg)), float(np.median(ref))
        u_lose = mannwhitneyu(deg[drivers], ref, alternative="two-sided")
        u_gain = mannwhitneyu(deg[gainers], ref, alternative="two-sided")
        print(f"  reference population : {int(nzmask.sum()):,} nodes with b>0 "
              f"(median deg {med_nz:.1f}; whole-graph median {med_all:.1f})")
        print(f"  nodes carrying half the LOSS : {len(drivers):5d} "
              f"({100*len(drivers)/nzmask.sum():.1f}% of b>0)  median deg "
              f"{np.median(deg[drivers]):6.1f} vs {med_nz:.1f} "
              f"(p={u_lose.pvalue:.2e})")
        print(f"  nodes carrying half the GAIN : {len(gainers):5d} "
              f"({100*len(gainers)/nzmask.sum():.1f}% of b>0)  median deg "
              f"{np.median(deg[gainers]):6.1f} vs {med_nz:.1f} "
              f"(p={u_gain.pvalue:.2e})")

        # --- CHECK 1b: the mechanism stated directly ------------------------
        # The hypothesis is about CONVERGENCE RATE: hubs are dominated by
        # short-range pairs and are already near their ceiling at k=2; bridges
        # accrue their value late. That is measurable without reference to the
        # ranking at all - just b_2(v)/b(v) against degree, on the nonzero set.
        # If the mechanism is right this correlation is POSITIVE, and it should
        # be positive on every network whether or not that network dips.
        with np.errstate(divide="ignore", invalid="ignore"):
            frac2 = np.where(nzmask, bk[2] / np.maximum(bc, 1e-300), np.nan)
            frac3 = np.where(nzmask, bk[3] / np.maximum(bc, 1e-300), np.nan)
        r2 = kendalltau(deg[nzmask], frac2[nzmask]).statistic
        r3 = kendalltau(deg[nzmask], frac3[nzmask]).statistic
        print(f"  saturation vs degree (b>0 nodes): tau(deg, b_2/b)={r2:+.4f}   "
              f"tau(deg, b_3/b)={r3:+.4f}")
        print(f"  median b_2/b = {np.nanmedian(frac2):.4f}   "
              f"median b_3/b = {np.nanmedian(frac3):.4f}")

        # --- CHECK 2: do the losers overlap Finding 8's failure atlas? ------
        # The atlas holds the LEARNED model's rank residuals at r=3. If the
        # untrained formula stumbles at k=3 on the nodes the trained model
        # also misplaces, two unrelated methods are failing on the same
        # structure, which is stronger evidence for a structural cause than
        # either alone.
        A = atlas.get(tag, {}).get("betweenness")
        enrich = {}
        if A is not None and len(A["delta"]) == net.n:
            # THE SAME CONFOUND AS ABOVE, AND IT IS NOT HYPOTHETICAL: the
            # atlas's `under` tail is 100% nonzero-betweenness nodes on all
            # five networks (checked). Dividing by n rather than by |b>0| would
            # roughly double every enrichment figure below - on ca-HepTh it
            # turns a 3.1x into a 5.9x. The base rate must be measured in the
            # population the movers are drawn from.
            n_nz = int(nzmask.sum())
            for tail in ("under", "over"):
                idx = A[tail]
                tail_nz = set(idx[nzmask[idx]].tolist())
                base = len(tail_nz) / n_nz
                for label, grp in (("drivers", drivers), ("gainers", gainers)):
                    hit = len(set(grp.tolist()) & tail_nz)
                    frac = hit / max(1, len(grp))
                    # Hypergeometric tail: is this more overlap than drawing
                    # |grp| nodes at random from the nonzero set would give?
                    p = hypergeom.sf(hit - 1, n_nz, len(tail_nz), len(grp))
                    enrich[f"{label}_{tail}"] = (hit, frac, base,
                                                 frac / base if base else np.nan, p)
        for key, (hit, frac, base, x, p) in enrich.items():
            print(f"  atlas {key:16s}: {hit:4d} hits  {frac:.3f} vs base "
                  f"{base:.3f}  = {x:5.2f}x  (hypergeom p={p:.1e})")
        if not enrich:
            print("  atlas cross-ref:     no betweenness arm for this network")

        # --- CHECK 3: is the hub/bridge split unusual here? -----------------
        # lambda_NB = 1/beta_c is already on disk (the non-backtracking leading
        # eigenvalue that set p). kappa = <k^2>/<k> - 1 is the excess-degree
        # branching factor a locally tree-like graph would have. Their RATIO is
        # the diagnostic: lambda_NB tracks kappa closely when branching is
        # homogeneous, and departs from it when a few structures carry the
        # branching.
        meta = json.load(open(f"cache_meta_{tag}.json"))
        lam_nb = 1.0 / float(meta["beta_c"])
        kappa = float((deg ** 2).mean() / deg.mean() - 1.0)
        summary.append({
            "network": tag, "n": net.n, "mean_deg": float(deg.mean()),
            "tau_k2": taus[2], "tau_k3": taus[3], "tau_k4": taus[4],
            "dip": dip, "lambda_nb": lam_nb, "kappa_excess": kappa,
            "lam_over_kappa": lam_nb / kappa,
            "driver_med_deg": float(np.median(deg[drivers])),
            "nonzero_med_deg": med_nz,
            "overall_med_deg": med_all,
            "driver_deg_p": float(u_lose.pvalue),
            "gainer_med_deg": float(np.median(deg[gainers])),
            "gainer_deg_p": float(u_gain.pvalue),
            "tau_deg_sat2": float(r2), "tau_deg_sat3": float(r3),
            "med_sat2": float(np.nanmedian(frac2)),
            "med_sat3": float(np.nanmedian(frac3)),
        })
        print(f"  lambda_NB={lam_nb:7.2f}  kappa=<k^2>/<k>-1={kappa:7.2f}  "
              f"ratio={lam_nb/kappa:.3f}")

    S = pd.DataFrame(summary).sort_values("dip")
    S.to_csv("results_betweenness_k_dip.csv", index=False)
    print(f"\n{'=' * 74}\nSUMMARY (sorted by k2->k3 change)\n{'=' * 74}")
    print(S[["network", "dip", "driver_med_deg", "gainer_med_deg",
             "nonzero_med_deg", "tau_deg_sat2", "med_sat2",
             "lambda_nb", "kappa_excess", "lam_over_kappa"]]
          .round(3).to_string(index=False))
    print("\nWrote results_betweenness_k_dip.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())

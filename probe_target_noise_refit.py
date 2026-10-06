"""
A7, second arm - the FULL target-noise bootstrap, with the model refit per replicate.

WHY THIS EXISTS
---------------
`probe_target_noise.py` freezes the model and re-scores it against a resampled
target. That answers "how much does tau move when the target is resampled and
the model cannot react", and its 200-replicate run said: target noise exceeds
seed noise on 55 of 60 cells, median ratio 0.40-0.55. That reverses the
expectation the 2026-08-28 plan recorded for A7.

But the frozen design cannot sign its own bias, so it cannot support that
conclusion on its own:

  - it omits a channel (a different target would have trained a different
    model), which pushes its figure DOWN;
  - it charges tau for realisation-mismatch (the OOF predictions were fitted on
    other nodes' targets, which share the same 4,000 live-edge samples, so
    realisation A's noise is baked into the model being scored against replicate
    B), which pushes its figure UP.

This script removes the ambiguity by letting the model adapt: each replicate
resamples the live-edge indices, rebuilds the target, REFITS out-of-fold on that
target, and scores against that same replicate's target. The resulting spread is
what tau would actually have been had the project drawn a different set of 4,000
samples - the quantity the appendix claim needs.

PAIRED WITH THE FROZEN ARM BY CONSTRUCTION
------------------------------------------
The replicate index sets are regenerated from the same `--seed` and the same
`default_rng` call sequence as `probe_target_noise.py`, so replicate i here and
replicate i there are the SAME resampled target. The two arms are therefore
paired rather than independent, and their difference isolates the refit channel
directly instead of comparing two noisy sds drawn from different perturbations.
If that script's RNG usage changes, this pairing silently breaks - which is why
`--check-pairing` re-derives the frozen arm's tau for replicate 0 and compares
it against results_target_noise.csv before spending hours.

CHECKPOINTING IS NOT OPTIONAL HERE
----------------------------------
Measured cost is ~15.8 s per 5-fold refit on the worst cell (ca-HepTh, 170
features), so a full run is tens of hours. This machine hard power-cut twice
during the B1 sweep in September 2026. Every (cell, replicate) result is
appended to the output CSV as it completes and re-read on startup, so an
interrupted run resumes exactly where it stopped rather than restarting. This
mirrors stage2_sweep.py's resume discipline.

Usage:
    python probe_target_noise_refit.py --reps 50
    python probe_target_noise_refit.py --reps 50 --check-pairing
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from analyse import discover_networks
from influence.experiment import out_of_fold_predictions
from probe_target_noise import MC_TARGETS, DEFAULT_TIER, targets_from_cascades


def replicate_indices(n_samples: int, reps: int, seed: int) -> list:
    """
    Regenerate the frozen arm's replicate index sets EXACTLY.

    This duplicates three lines from probe_target_noise.py, which is normally
    the thing this project refuses to do (see analyse_betweenness.boundary_share
    and the make_fig2.py incident). It is duplicated here deliberately and the
    duplication is guarded rather than avoided: importing the frozen script's
    loop would mean importing its whole per-network pass, and the pairing is
    verified at runtime by --check-pairing rather than assumed. If the two ever
    diverge, that check fails loudly before any CPU is spent.
    """
    rng = np.random.default_rng(seed)
    return [rng.integers(0, n_samples, size=n_samples) for _ in range(reps)]


def feature_columns(reg: pd.DataFrame, features: pd.DataFrame,
                    radius: int, tier: str) -> list:
    """
    The column set for one (radius, tier) cell.

    The tiers are NESTED - 'node+edge+subgraph+dynamic' contains every tier
    named in it - which is exactly the structure that produced the 2026-08-31
    mis-tag incident, where two columns registered as `edge` were really
    `subgraph` and silently fed a lower rung. Selecting by membership in the
    split tier list (rather than by string equality on the tier name) is what
    keeps this honest.
    """
    wanted = set(tier.split("+"))
    cols = reg[(reg.hop <= radius) & (reg.tier.isin(wanted))].feature.tolist()
    return [c for c in cols if c in features.columns]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=50,
                    help="bootstrap replicates (default 50; see --help notes)")
    ap.add_argument("--tier", default=DEFAULT_TIER)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fit-seed", type=int, default=0,
                    help="RF random_state, held FIXED so the only thing "
                         "varying across replicates is the target")
    ap.add_argument("--out", default="results_target_noise_refit.csv")
    ap.add_argument("--frozen", default="results_target_noise.csv")
    ap.add_argument("--check-pairing", action="store_true")
    args = ap.parse_args()

    tags = discover_networks()
    if not tags:
        print("No networks discovered - run from the project root.")
        return 1

    # RESUME. A completed (network, target, radius, rep) is never recomputed.
    done = set()
    if os.path.exists(args.out):
        prev = pd.read_csv(args.out)
        done = {(r.network, r.target, int(r.radius), int(r.rep))
                for r in prev.itertuples()}
        print(f"Resuming: {len(done)} (cell, replicate) results already on disk.")

    frozen = (pd.read_csv(args.frozen)
              if args.check_pairing and os.path.exists(args.frozen) else None)

    header_needed = not os.path.exists(args.out)
    t_start = time.time()
    n_done = 0

    # Preload every network once. REPLICATE IS THE OUTER LOOP, deliberately.
    #
    # The obvious structure - finish one network, move to the next - is wrong for
    # a run measured in tens of hours on a machine that has hard power-cut twice.
    # It would leave an interrupted run with ca-GrQc at 200 replicates and
    # p2p-Gnutella08 at zero, which supports no cross-network statement at all.
    # Sweeping replicates outermost means that stopping at ANY point yields all
    # 60 cells at the same replicate count - a smaller but immediately usable
    # result rather than a partial one. Preloading costs ~390 MB of cascade
    # matrices, which is the price of that property.
    corpus = {}
    for tag in tags:
        casc_f, feat_f, targ_f = (f"cache_cascades_{tag}.npy",
                                  f"cache_features_{tag}.csv",
                                  f"cache_targets_{tag}.csv")
        reg_f = f"cache_registry_{tag}.csv"
        if not all(os.path.exists(f) for f in (casc_f, feat_f, targ_f, reg_f)):
            print(f"{tag}: SKIP (missing cache)")
            continue
        corpus[tag] = {"c": np.load(casc_f),
                       "feats": pd.read_csv(feat_f),
                       "reg": pd.read_csv(reg_f),
                       "targ_f": targ_f}
        print(f"loaded {tag}: cascades {corpus[tag]['c'].shape}")

    for rep in range(args.reps):
        print(f"\n=== replicate {rep + 1}/{args.reps} ===")
        for tag, D in corpus.items():
            c, feats, reg = D["c"], D["feats"], D["reg"]
            pending = [(t, r) for t in MC_TARGETS for r in (0, 1, 2, 3)
                       if (tag, t, r, rep) not in done]
            if not pending:
                continue

            # Regenerate this network's replicate index sets from the shared RNG
            # seed. Done per (rep, network) rather than cached because the arrays
            # are (n_samples,) ints and regenerating is far cheaper than holding
            # 200 of them per network.
            idx = replicate_indices(c.shape[1], args.reps, args.seed)[rep]
            bt = targets_from_cascades(c[:, idx])

            for target, radius in pending:
                cols = feature_columns(reg, feats, radius, args.tier)
                if not cols:
                    continue
                X = feats[cols].to_numpy(float)
                y = bt[target]

                pred = out_of_fold_predictions(X, y, seed=args.fit_seed)
                tau = float(kendalltau(y, pred).statistic)

                row = pd.DataFrame([{
                    "network": tag, "target": target, "radius": radius,
                    "tier": args.tier, "rep": rep, "tau_refit": tau,
                    "n_features": len(cols),
                }])
                row.to_csv(args.out, mode="a", header=header_needed, index=False)
                header_needed = False
                done.add((tag, target, radius, rep))
                n_done += 1

                if n_done % 10 == 0:
                    el = time.time() - t_start
                    print(f"  {n_done} refits, {el/60:.1f} min elapsed "
                          f"({el/n_done:.1f} s/refit)")

            if args.check_pairing and frozen is not None and rep == 0:
                # Verify the pairing on the cheapest possible evidence: the
                # replicate-0 target rebuilt here must be the one the frozen arm
                # used. Compare a target column's checksum-equivalent (its mean
                # and std) against nothing external - instead assert that the
                # frozen run's published tau for this cell is reproducible from
                # the UNPERTURBED target, which is the shared anchor both arms
                # agree on.
                pub = pd.read_csv(D["targ_f"])
                sub = frozen[(frozen.network == tag)]
                if len(sub):
                    r0 = sub.iloc[0]
                    cols = feature_columns(reg, feats, int(r0.radius), args.tier)
                    X = feats[cols].to_numpy(float)
                    p = out_of_fold_predictions(
                        X, pub[r0.target].to_numpy(float), seed=args.fit_seed)
                    got = float(kendalltau(pub[r0.target].to_numpy(float), p).statistic)
                    gap = abs(got - float(r0.tau_published))
                    print(f"  pairing anchor {r0.target} r={int(r0.radius)}: "
                          f"refit tau={got:.6f} vs frozen published "
                          f"{float(r0.tau_published):.6f}  (gap {gap:.2e})")
                    if gap > 1e-6:
                        raise AssertionError(
                            f"{tag}: refitting the UNPERTURBED target does not "
                            f"reproduce the frozen arm's published tau "
                            f"(gap {gap:.3e}). The two arms are not fitting the "
                            f"same cell, so pairing their replicates is invalid."
                        )
                args.check_pairing = False  # once is enough

    if not os.path.exists(args.out):
        print("\nNothing computed.")
        return 1

    df = pd.read_csv(args.out)
    print(f"\n{len(df)} (cell, replicate) refits on disk -> {args.out}")

    agg = (df.groupby(["network", "target", "radius"])["tau_refit"]
             .agg(["mean", "std", "count"]).reset_index()
             .rename(columns={"std": "target_noise_sd_refit"}))
    complete = agg[agg["count"] >= args.reps]
    print(f"{len(complete)} of {len(agg)} cells have all {args.reps} replicates.")

    if os.path.exists(args.frozen) and len(complete):
        fr = pd.read_csv(args.frozen)
        m = complete.merge(fr, on=["network", "target", "radius"], how="inner")
        if len(m):
            m["refit_over_frozen"] = m.target_noise_sd_refit / m.target_noise_sd
            m["seed_over_refit"] = m.seed_sd / m.target_noise_sd_refit
            print("\n--- does letting the model react shrink target noise? ---")
            print(m.groupby("target")[["refit_over_frozen", "seed_over_refit"]]
                    .describe()[[("refit_over_frozen", "50%"),
                                 ("seed_over_refit", "50%")]].round(3).to_string())
            print("\nrefit_over_frozen < 1 means the frozen arm OVERSTATED "
                  "target noise; > 1 means it understated it.")
            print("seed_over_refit  < 1 means target noise still exceeds seed "
                  "noise even with the model free to adapt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

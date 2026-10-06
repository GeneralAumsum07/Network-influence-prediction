"""
A7 arm 2 scoring: P1-P4 from `docs/prereg_A7_target_noise.md`, against
`results_target_noise_refit.csv`.

WHAT THE TWO ARMS ARE
---------------------
Both bootstrap the TARGET over live-edge sample indices, 200 replicates, on the
same 60 cells (5 networks x 3 Monte Carlo targets x 4 radii, richest tier).
`betweenness` is excluded from both: it is computed exactly by Brandes, carries
no Monte Carlo noise, and a row of zeros would read as a bug rather than a fact.

  arm 1 (frozen)  - the model is NOT refitted; the cached OOF predictions are
                    scored against each resampled target. Cheap, but it charges
                    tau for realisation mismatch (the predictions were fitted on
                    other nodes' targets from the ORIGINAL realisation) while
                    omitting the training channel entirely.
  arm 2 (refit)   - out-of-fold refit per replicate, so the model can adapt.

Arm 1 cannot sign its own bias, which is exactly why arm 2 was run. The two
channels push in opposite directions and the prereg named both in advance.

THE RATIOS
----------
  refit_over_frozen = sd(tau | refit) / sd(tau | frozen)
      < 1  the frozen arm OVERSTATED target noise (P1)
      > 1  the training channel dominates instead (P2)
  seed_over_refit   = seed_sd / sd(tau | refit)
      < 1  target noise still exceeds seed noise even with the model free (P3)

Usage:
    python score_a7_arm2.py
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

EXPECTED_REPS = 200


def main() -> int:
    refit = pd.read_csv("results_target_noise_refit.csv")
    frozen = pd.read_csv("results_target_noise.csv")

    key = ["network", "target", "radius"]

    # Guard: an interrupted run would leave short cells, and a cell scored on 40
    # replicates instead of 200 has a visibly noisier sd that would silently
    # distort every ratio below. The run checkpoints and resumes, so a short cell
    # means "not finished", not "finished differently".
    counts = refit.groupby(key).rep.nunique()
    short = counts[counts != EXPECTED_REPS]
    if len(short):
        print(f"REFUSING TO SCORE: {len(short)} cells have != {EXPECTED_REPS} "
              f"replicates:\n{short.to_string()}")
        return 1

    # Bootstrap sd is the ddof=1 sd over replicates - the same estimator arm 1
    # used, so the ratio compares like with like.
    A2 = (refit.groupby(key).tau_refit
          .agg(sd_refit=lambda v: v.std(ddof=1), tau_refit_mean="mean")
          .reset_index())
    df = frozen.merge(A2, on=key, how="inner", validate="one_to_one")
    assert len(df) == 60, f"expected 60 cells, joined {len(df)}"

    df["refit_over_frozen"] = df.sd_refit / df.target_noise_sd
    df["seed_over_refit"] = df.seed_sd / df.sd_refit

    print(f"{len(df)} cells, {EXPECTED_REPS} replicates each.\n")
    print("=" * 74)
    print("P1 - the frozen arm OVERSTATED target noise: refit/frozen < 1 on a "
          "majority")
    print("=" * 74)
    n_lt = int((df.refit_over_frozen < 1).sum())
    print(f"  refit_over_frozen < 1 on {n_lt} of {len(df)} cells")
    print(f"  median {df.refit_over_frozen.median():.3f}   "
          f"range {df.refit_over_frozen.min():.3f} - "
          f"{df.refit_over_frozen.max():.3f}")
    print(f"  by target:\n"
          + df.groupby("target").refit_over_frozen
          .agg(median="median", n_lt_1=lambda v: int((v < 1).sum()),
               n="size").to_string())
    print(f"  VERDICT P1: {'SUPPORTED' if n_lt > len(df) / 2 else 'FALSIFIED'}")
    print(f"  VERDICT P2 (training channel dominates, refit/frozen > 1): "
          f"{'SUPPORTED' if n_lt < len(df) / 2 else 'not the case'}")

    print("\n" + "=" * 74)
    print("P3 - target noise still exceeds seed noise: seed_over_refit < 1 on a")
    print("     majority, but by a SMALLER margin than arm 1's 0.40-0.55 medians")
    print("=" * 74)
    n_lt3 = int((df.seed_over_refit < 1).sum())
    print(f"  seed_over_refit < 1 on {n_lt3} of {len(df)} cells")
    cmp = pd.DataFrame({
        "arm1_median": df.groupby("target").ratio_seed_over_target.median(),
        "arm2_median": df.groupby("target").seed_over_refit.median(),
    })
    cmp["margin_shrank"] = cmp.arm2_median > cmp.arm1_median
    print(cmp.round(3).to_string())
    half = n_lt3 > len(df) / 2
    smaller = bool((cmp.arm2_median > cmp.arm1_median).all())
    print(f"  majority clause: {'SUPPORTED' if half else 'FALSIFIED'}")
    print(f"  smaller-margin clause: "
          f"{'SUPPORTED' if smaller else 'FALSIFIED'} "
          f"(arm-2 ratio closer to 1 on all three targets = smaller margin)")

    print("\n" + "=" * 74)
    print("P4 - ordering by target preserved: spread_resid worst-affected, "
          "spread_mean least")
    print("=" * 74)
    # "Worst-affected" = smallest seed/target ratio, i.e. target noise most
    # dominant relative to seed noise. Same reading as arm 1's headline table.
    #
    # P4 bundles TWO claims and they score differently, so they are scored
    # separately rather than collapsed into one verdict:
    #   (i)  the ordering is PRESERVED between arms;
    #   (ii) that ordering is spread_resid worst, spread_mean least.
    # Clause (ii) turns out to be wrong about ARM 1's OWN numbers, not about
    # arm 2 - which makes it an error in the pre-registration rather than a
    # falsified prediction about the refit. Reporting a bare "FALSIFIED" would
    # attribute the miss to the wrong arm.
    order1 = df.groupby("target").ratio_seed_over_target.median().sort_values()
    order2 = df.groupby("target").seed_over_refit.median().sort_values()
    print(f"  arm 1 order (worst first): {list(order1.index)}")
    print(f"  arm 2 order (worst first): {list(order2.index)}")
    preserved = list(order1.index) == list(order2.index)
    named = (order2.index[0] == "spread_resid"
             and order2.index[-1] == "spread_mean")
    print(f"  clause (i)  ordering preserved between arms: "
          f"{'SUPPORTED' if preserved else 'FALSIFIED'}")
    print(f"  clause (ii) spread_resid worst / spread_mean least: "
          f"{'SUPPORTED' if named else 'FALSIFIED'}")
    if preserved and not named:
        print(f"    NOTE: clause (ii) is false of ARM 1 as well "
              f"(arm-1 worst was {order1.index[0]}, "
              f"median {order1.iloc[0]:.3f}). The pre-registration misstated "
              f"its own already-published arm-1 result; arm 2 reproduced arm "
              f"1's ordering exactly.")

    print("\n" + "=" * 74)
    print("Per-cell table (median over radii)")
    print("=" * 74)
    print(df.groupby(["network", "target"])[
        ["refit_over_frozen", "seed_over_refit", "ratio_seed_over_target"]]
        .median().round(3).to_string())

    df.to_csv("results_target_noise_scored.csv", index=False)
    print("\nWrote results_target_noise_scored.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())

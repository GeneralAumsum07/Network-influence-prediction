"""
The betweenness target, examined honestly.

WHY THIS SCRIPT EXISTS
----------------------
Betweenness is the target with the largest r0 -> r1 jump in the whole project
(+0.37 on ca-GrQc), and it is the basis of the claim that betweenness saturates
at radius 1. That number needs a caveat stated up front rather than discovered
by a reviewer.

A large share of nodes have betweenness EXACTLY zero - 55% on ca-GrQc. Kendall
tau-b excludes pairs tied in the truth, but it still scores every zero-vs-
nonzero pair, and on ca-GrQc those are 71% of everything it scores. So most of
the "prediction problem" is one binary question: is this node's betweenness
zero or not?

That question has an exact local answer, and as of 2026-08-28 it is stated as a
THEOREM rather than an empirical regularity (study doc section 24.1):

    betweenness(v) == 0  <=>  ego_betweenness(v) == 0  <=>  v is simplicial
                                                (N(v) induces a clique)

Proof. (<=) If every two neighbours of v are adjacent, any path s..a v b..t
through v can be shortcut by replacing 'a v b' with the edge ab, strictly
shortening it; so no geodesic has v as an interior vertex, and the same holds
inside the ego graph. (=>) If some u,w in N(v) are non-adjacent then d(u,w) = 2
and u-v-w is a geodesic, so sigma_uw(v) >= 1 and betweenness(v) > 0; that same
pair witnesses ego_betweenness(v) > 0, since u, w and their common neighbours
all lie in the ego graph. Nodes of degree < 2 are simplicial vacuously. QED

Note clustering_coefficient == 1 is NOT equivalent: it misses degree-1 nodes,
whose clustering is defined here as 0 while their betweenness is 0 too. That is
exactly the vacuous-simpliciality case the proposition handles explicitly.

WHAT THE EQUIVALENCE CHECK IS FOR, NOW THAT IT IS A THEOREM
----------------------------------------------------------
It is a CANARY, not evidence. The mathematics establishes the equivalence; a
measurement cannot add to that. What the check still does - and this is worth
keeping - is guard the IMPLEMENTATION. If `exact_betweenness` or
`ego_betweenness` is ever broken by a refactor, the two will stop agreeing and
this prints a nonzero mismatch count. That is precisely the class of error this
project has been bitten by twice (the ORCA paw-orbit numbering, the H-index
convergence direction), and both times only an independent cross-check caught
it.

So this script reports three things per network:
  1. the zero fraction, and what share of tau-b's scoreable pairs it drives
  2. the equivalence canary described above
  3. tau measured on the NONZERO subset only - the ranking quality among the
     nodes where betweenness actually varies

Point 3 is the number that survives the caveat. Report both.

WHY THIS READS CACHED PREDICTIONS RATHER THAN REFITTING (changed 2026-08-28)
---------------------------------------------------------------------------
This script used to refit every cell itself: 4 radii x 10 seeds x 5 networks =
200 forests, several minutes, for numbers the sweep had ALREADY computed and
stored in `cache_oof_<tag>.npz` under exactly the key this script needs
(`betweenness|<radius>|node+edge+subgraph|<seed>`).

Refitting was worse than slow, it was less correct. An independent refit is a
second measurement that can silently drift from the sweep it is supposed to be
annotating - different sklearn version, a changed default, an edited model
config - and then the nonzero-subset column in the study doc would no longer
describe the same models as the full-tau column beside it. Reading the stored
predictions makes the two columns the same experiment by construction.

It also takes this analysis off the training gate entirely: with the cache
present it performs no fits at all. Pass --refit to force the old behaviour if
the prediction store is missing or you are deliberately re-deriving it.

OBJECTIVE ARM (added 2026-09-11, Claude Opus 5, Task 6 audit finding P2-03)
The reported betweenness model is the log1p-objective forest whose predictions
live in estimators/cache_oof_<tag>__rf_log1p.npz; the top-level archive is the
historical squared-error arm. This script now reads the reported arm by default
and prints which arm every table came from. `--arm=raw` reproduces the
historical (Finding 8-era) table, labelled.
"""
import glob
import sys
import os
import re

import numpy as np
import pandas as pd

from influence.estimators import get_estimator
from influence.experiment import out_of_fold_predictions, TIER_LADDER
from influence.features import select_features
from influence.oof_arms import arm_label, load_oof as load_oof_arm
from influence.targets import assert_no_leakage

from scipy.stats import kendalltau

N_SEEDS = 10
FULL_TIERS = TIER_LADDER["node+edge+subgraph"]
# The richness rung whose predictions we read back. Must match the string the
# sweep writes into its key, not just be equivalent to it.
FULL_RICHNESS = "node+edge+subgraph"
# Set from the command line in main(); module-level so the helpers can see it.
FORCE_REFIT = False
# Which betweenness objective arm to read. None = the arm the study reports
# (log1p; see influence/oof_arms.py). Until 2026-09-11 this script silently
# read the raw squared-error archive while analyse_moran_correlogram read the
# log1p one (Task 6 audit finding P2-03, fixed by Claude Opus 5). `--arm=raw`
# reproduces the historical table and labels it as such.
OOF_ARM: str | None = None
# Must match the sweep's max_hop, or this script reports radii the sweep never
# ran and for which no stored prediction exists.
MAX_HOP = 3


def boundary_share(bc: np.ndarray) -> dict:
    """
    The zero-inflation decomposition of Kendall tau-b's scored pairs.

    Single source of truth for study_doc_v2.md 24.4-24.5 and for the D2
    scoring critique. It lives in a function rather than inline in main()
    because verify_pipeline.py checks the identity too, and the one thing this
    project must not do is keep two copies of a formula in two files - that is
    precisely the make_fig2.py failure, where the figure and the tables drifted
    apart because each carried its own copy of a rule.

    Returns, for a betweenness vector:

      z         zero fraction |Z|/n
      w_exact   share of tau-b's SCORED pairs that are zero-vs-nonzero, as an
                identity with the pair counts: 2*nz*nn / [n(n-1) - nz(nz-1)]
      w_asym    its large-n limit 2z/(1+z), which depends on z ALONE - the m's
                cancel, so the boundary share is independent of graph size,
                density and degree distribution
      w_counted the same quantity assembled from the counts separately, so the
                caller can assert two routes agree
      gap       |w_exact - w_counted|

    tau-b excludes pairs tied in the truth, so the zero-zero pairs drop out of
    the denominator entirely; that exclusion is the whole reason w is as large
    as it is on the sparse collaboration graphs.
    """
    n = int(len(bc))
    zero = bc == 0
    nz, nn = int(zero.sum()), int((~zero).sum())

    total = n * (n - 1) / 2
    tied_y = nz * (nz - 1) / 2          # zero-zero: tied in truth, not scored
    scoreable = total - tied_y
    cross = nz * nn                     # the boundary pairs

    z = nz / n
    w_exact = 2.0 * nz * nn / (n * (n - 1) - nz * (nz - 1))
    w_counted = cross / scoreable

    # THE TAU FLOOR - and note it is NOT w. This was wrong in study_doc_v2.md
    # 24.5 until 2026-09-05, and the error was systematic, not a rounding slip.
    #
    # 24.5 argued: a method that decides the zero set exactly and ranks the
    # nonzero set at chance scores every boundary pair and nothing else, so
    #     tau_floor ~= w*1 + (1-w)*0 = w.
    # That treats tau as a weighted average OVER SCORED PAIRS. It would be right
    # for (C-D)/scoreable. But scipy's kendalltau - which is what this pipeline
    # reports, and what the literature reports - is tau-b:
    #     tau_b = (C - D) / sqrt((n0 - n1)(n0 - n2))
    # with n1 the pairs tied in truth and n2 those tied in the prediction. A
    # regressor's output is continuous, so n2 = 0 and the denominator is
    #     sqrt(scoreable * total),
    # the GEOMETRIC MEAN of the untied and the full pair counts - not scoreable.
    # Since scoreable < total, dividing by scoreable OVERSTATES the floor, and
    # it overstates it most where z is largest, which is exactly the sparse
    # collaboration graphs the whole argument is about. On ca-GrQc the published
    # floor was 0.710; the true one is 0.593.
    #
    # The corrected floor has an equally clean closed form,
    #     tau_floor = cross / sqrt(scoreable * total) = w * sqrt(scoreable/total)
    #               ~= w * sqrt(1 - z^2)            (scoreable/total = 1 - nz(nz-1)/(n(n-1))
    #                                                -> 1 - z^2 only as n -> inf;
    #                                                gap 2.5e-5 on ca-GrQc)
    #               -> 2z * sqrt((1-z)/(1+z))  asymptotically,
    # (The "= w*sqrt(1-z^2)" that stood here until 2026-09-12 was the
    # asymptotic form written with an equals sign; analyse_c3_benchmarks.shares
    # had implemented that form as if it were exact - Task 6 finding P3-02,
    # Claude Opus 5. The code below was always the exact expression.)
    # verified against 200 simulated draws of the exact hypothetical method on
    # all five networks: max |closed form - simulated| = 5.1e-4, against a
    # simulation standard error of ~3e-4. See docs/priority_search_D2.md.
    #
    # w itself is untouched and still correct AS the share of scored pairs that
    # are boundary pairs. What was wrong was the step from that share to a tau.
    tau_floor = cross / np.sqrt(scoreable * total)
    tau_floor_asym = 2 * z * np.sqrt((1 - z) / (1 + z)) if z < 1 else 0.0

    return {"n": n, "nz": nz, "nn": nn, "zero": zero,
            "tau_floor": tau_floor, "tau_floor_asym": tau_floor_asym,
            "total": total, "scoreable": scoreable, "cross": cross,
            "z": z, "w_exact": w_exact, "w_asym": 2 * z / (1 + z),
            "w_counted": w_counted, "gap": abs(w_exact - w_counted)}


def load_oof(tag: str) -> dict | None:
    """
    The sweep's stored out-of-fold predictions, or None if absent.

    Keys are `target|radius|richness|seed`, written by stage2_sweep.py. Loaded
    lazily into a plain dict because npz members are decompressed on access and
    we touch each one exactly once.
    """
    store, arm = load_oof_arm(tag, "betweenness", OOF_ARM)
    print(f"  {arm_label('betweenness', arm)}")
    return store


def predictions_for(oof: dict | None, Xm: np.ndarray, bc: np.ndarray,
                    r: int, seed: int) -> tuple[np.ndarray, bool]:
    """
    Predictions for one (radius, seed) cell: from cache if present, else refit.

    Returns (preds, came_from_cache) so the caller can say which it used -
    a number whose provenance is ambiguous is a number this project does not
    want to print.
    """
    if oof is not None:
        key = f"betweenness|{r}|{FULL_RICHNESS}|{seed}"
        if key in oof:
            return oof[key], True
    # A refit must use the SAME objective as the arm being read, or a "refit"
    # row would be a different model from its "cache" neighbours. The raw arm
    # is the estimator=None baseline; log1p is the registered rf_log1p factory.
    arm = OOF_ARM or "log1p"
    est = None if arm == "raw" else get_estimator("rf_log1p")
    return out_of_fold_predictions(Xm, bc, n_splits=5, seed=seed, estimator=est), False


def networks_with_betweenness() -> list[str]:
    tags = []
    for path in sorted(glob.glob("cache_targets_*.csv")):
        tag = re.match(r"cache_targets_(.+)\.csv$", os.path.basename(path)).group(1)
        if "betweenness" in pd.read_csv(path, nrows=1).columns:
            tags.append(tag)
    return tags


def main() -> None:
    # Optional tag arguments restrict the run; with none, every cached network
    # that has a betweenness column is analysed. `--refit` forces fresh fits
    # instead of reading the sweep's stored predictions.
    global FORCE_REFIT, OOF_ARM
    args = sys.argv[1:]
    FORCE_REFIT = "--refit" in args
    for a in args:
        if a.startswith("--arm="):
            OOF_ARM = a.split("=", 1)[1]        # "raw" or "log1p"
    wanted = [a for a in args if not a.startswith("--")]
    if FORCE_REFIT:
        print("  [--refit] ignoring cache_oof_*.npz; fitting every cell fresh")
    tags = networks_with_betweenness()
    if wanted:
        tags = [t for t in tags if t in wanted]
        missing = sorted(set(wanted) - set(tags))
        if missing:
            print(f"  [skip] no cached betweenness for: {', '.join(missing)}")

    for tag in tags:
        X = pd.read_csv(f"cache_features_{tag}.csv")
        Y = pd.read_csv(f"cache_targets_{tag}.csv")
        reg = pd.read_csv(f"cache_registry_{tag}.csv")

        bc = Y["betweenness"].to_numpy(dtype=np.float64)
        egob = X["ego_betweenness"].to_numpy(dtype=np.float64)
        B = boundary_share(bc)
        n, nz, nn = B["n"], B["nz"], B["nn"]
        zero, total, scoreable, cross = (B["zero"], B["total"],
                                         B["scoreable"], B["cross"])

        print("\n" + "=" * 74)
        print(f"{tag}   n={n:,}")
        print("=" * 74)
        print(f"  betweenness == 0            : {nz:,} ({100*nz/n:.1f}%)")
        print(f"  pairs scored by tau-b       : {scoreable:,.0f} of {total:,.0f}")
        print(f"  of those, zero-vs-nonzero   : {100*cross/scoreable:.1f}%")

        # The boundary share has a closed form. Two of them, and the difference
        # between them is a finite-size correction worth being precise about.
        #
        # EXACT, at finite n - just the pair counts written out:
        #
        #     w_exact = 2*nz*nn / [ n(n-1) - nz(nz-1) ]
        #
        # ASYMPTOTIC, treating z = nz/n as continuous and dropping the -1s.
        # Writing m = 1 - z, the boundary pairs are z*m and the nonzero-nonzero
        # pairs m^2/2, so
        #
        #     w = zm / (zm + m^2/2) = z / (z + m/2) = 2z / (1 + z)
        #
        # The m's cancel: w depends on NOTHING about the graph except its zero
        # fraction. That is what makes it useful beyond this corpus - w can be
        # computed for any benchmark graph without running anyone's model,
        # which is the basis of the scoring critique in study doc 24.4-24.5.
        #
        # The exact form is what gets ASSERTED, because it is an identity with
        # the counts above and must hold to machine precision. The asymptotic
        # form is reported beside it with its error, because it is the version
        # worth quoting in prose and a reader should be able to see what the
        # convenience costs. (At n=986 it costs ~0.05 percentage points; the
        # first version of this check asserted the asymptotic form at 1e-9 and
        # failed on all five networks, which is how the distinction got found.)
        z, w_exact = B["z"], B["w_exact"]
        w_asym, w_measured, gap = B["w_asym"], B["w_counted"], B["gap"]
        # RAISE, do not print. Until 2026-09-04 this printed the string
        # "MISMATCH" and carried on to the next network - so a broken identity
        # would have scrolled past inside 200 lines of output that otherwise
        # looks like a clean run, and the exit code would still have been 0.
        # Meanwhile study_doc_v2.md 24.4 states in prose that "the exact form
        # is the one asserted". It was not; it was the one printed. That gap
        # between a documented guarantee and an enforced one is the same shape
        # as the make_fig2.py incident, and w_exact is load-bearing: 24.5's tau
        # floor, the ordering reversal, and the whole D2 scoring critique are
        # computed from it. If it ever stops matching the counted value the
        # correct response is to stop, not to report a floor derived from an
        # identity that no longer holds.
        if gap >= 1e-12:
            raise AssertionError(
                f"{tag}: closed form disagrees with the counted boundary "
                f"share by {gap:.3e} (w_exact={w_exact!r}, "
                f"counted={w_measured!r}). These are two routes to the same "
                f"quantity and must agree to machine precision; a real gap "
                f"means the pair accounting in study_doc_v2.md 24.4 is wrong."
            )
        print(f"  CHECK  w exact vs counted   : {100*w_exact:.4f}% vs "
              f"{100*w_measured:.4f}%  (agree)")
        print(f"         w ~ 2z/(1+z)         : {100*w_asym:.4f}%  "
              f"(asymptotic, error {100*(w_asym-w_exact):+.4f} pp)")

        # A method that answers only the zero/nonzero question - which the
        # Proposition says is exactly decidable at radius 1 - and ranks the
        # rest at chance already scores about w. Report the margin, because
        # the raw tau alone makes the most inflated networks look best.
        print(f"  tau floor from zero set     : {w_exact:.4f} "
              f"(any tau below this is worse than a radius-1 certificate)")

        # Also raised rather than printed, for a different reason. 24.1 PROVES
        # bc(v)==0 <=> ego_bet(v)==0, so this is no longer evidence for the
        # claim - 24.2 relabels it a canary on the implementation. But a canary
        # that only whispers is not a canary. A nonzero count here cannot mean
        # the theorem is false; it means betweenness or ego_betweenness is
        # being computed wrongly (endpoint convention, normalisation, a stale
        # cache), which would silently corrupt z, w, the floor, and every
        # nonzero-subset tau below.
        mismatches = int((zero != (egob == 0)).sum())
        if mismatches:
            raise AssertionError(
                f"{tag}: bc==0 <=> ego_betweenness==0 fails on {mismatches} "
                f"of {n} nodes. The equivalence is a theorem (study_doc_v2.md "
                f"24.1), so this is an implementation fault in one of the two "
                f"columns, not a counterexample."
            )
        print(f"  CHECK  bc==0 <=> ego_bet==0 : 0 mismatches (exact)")

        # clustering==1 is the tempting but wrong version - show why
        if "clustering_coefficient" in X.columns:
            clus = X["clustering_coefficient"].to_numpy(dtype=np.float64)
            mm = int((zero != (clus == 1.0)).sum())
            print(f"         bc==0 <=> clustering==1 : {mm} mismatches "
                  f"(misses degree-1 nodes, as expected)")

        if nn < 20:
            print("  too few nonzero nodes to rank; skipping subset tau")
            continue

        oof = None if FORCE_REFIT else load_oof(tag)
        if oof is None and not FORCE_REFIT:
            print("  NOTE: no cache_oof_%s.npz - refitting (this is slow, and "
                  "the numbers will be an independent measurement rather than "
                  "the sweep's own)" % tag)

        # Capped at MAX_HOP deliberately. The registry contains one subgraph
        # feature tagged hop 4, so iterating over every hop present would emit
        # an r=4 row - a radius the sweep never runs (max_hop=3) and which the
        # rest of the project explicitly excludes. Worse, there is no cached
        # prediction for it, so that row would silently refit and sit in the
        # table beside cached rows as if it were the same experiment.
        print(f"\n  {'r':>2} {'tau (all nodes)':>22} {'tau (nonzero only)':>22}  src")
        for r in sorted(h for h in reg["hop"].unique() if h <= MAX_HOP):
            cols = select_features(X, reg, max_hop=int(r), tiers=FULL_TIERS)
            if not cols:
                continue
            assert_no_leakage(cols)
            Xm = X[cols].to_numpy(dtype=np.float64)

            full_t, sub_t, cached = [], [], []
            for seed in range(N_SEEDS):
                pred, from_cache = predictions_for(oof, Xm, bc, int(r), seed)
                cached.append(from_cache)
                full_t.append(kendalltau(bc, pred).statistic)
                # Same model, evaluated only where the target actually varies.
                sub_t.append(kendalltau(bc[~zero], pred[~zero]).statistic)

            # Mixed provenance within one row would mean some seeds came from
            # the sweep and some from a fresh fit - averaging those together
            # would quietly blend two experiments, so say so rather than hide it.
            src = ("cache" if all(cached)
                   else "refit" if not any(cached)
                   else f"MIXED {sum(cached)}/{len(cached)}")
            print(f"  {int(r):>2} {np.mean(full_t):>13.4f} +/-{np.std(full_t, ddof=1):.4f}"
                  f" {np.mean(sub_t):>13.4f} +/-{np.std(sub_t, ddof=1):.4f}  {src}")


if __name__ == "__main__":
    main()

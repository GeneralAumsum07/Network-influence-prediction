"""
Score B1 against `docs/prereg_B1_sample_efficiency.md`.

Four declared predictions, and the pre-registration fixed the scoring rule
BEFORE the run so it cannot be tuned to the answer:

  P1  the lab's ~20% claim: tau at 20% within 0.02 of tau at 100% on the
      spreading targets at r >= 1. Recorded as the claim under test - it is
      the supervisor's number, not a prediction I had any basis for.
  P2  scarcity pushes r* DOWN (the plan's standing prediction, verbatim).
  P3  the shift is largest on betweenness, smallest on spread_mean.
  P4  a competing mechanism predicting the OPPOSITE sign, declared in advance
      precisely so that an upward move gets reported as a falsification rather
      than explained away.

THE SCORING RULE, QUOTED FROM THE PRE-REGISTRATION
--------------------------------------------------
"a shift counts only if modal r* differs AND the modal value's per-seed support
is >= 6/10 under both arms. A flip between two values that each win 5/10 is
noise, and this project has already published a case where the modal r* was
stable while its support was not."

That second clause is why support is carried through every table here instead
of being collapsed into the mode. An unsupported mode is not a measurement.

WHY THE REPRODUCTION CHECK RUNS FIRST AND CAN VOID THE RUN
----------------------------------------------------------
`probe_sample_efficiency.py` re-implements the out-of-fold loop rather than
calling `out_of_fold_predictions` (see its docstring for why). A bespoke loop
that silently differs from the pipeline would push the difference into the
measured effect. The fraction=1.0 arm therefore has to reproduce the published
`sweep_<tag>.csv` at the FULL tier. `--check` in the probe tested four cells;
this tests ALL 800 of them, because the failure mode that matters here is not a
structurally different loop (which shows up on cell one) but a subtle drift
that only appears on some networks.
"""
import numpy as np
import pandas as pd

from analyse import r_star_per_seed          # reused, not reimplemented

SRC = "results/sample_efficiency.csv"
FULL = "node+edge+subgraph"
NETS = ["ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined",
        "p2p-Gnutella08"]
TARGETS = ["betweenness", "spread_mean", "spread_cv", "spread_resid"]
# "Spreading targets" in P1's sense: the three simulated-cascade targets.
# betweenness is a structural target and P1 does not cover it.
SPREADING = ["spread_mean", "spread_cv", "spread_resid"]
EPS = [0.20, 0.10, 0.05, 0.02, 0.01]
# The pre-registration names 5% and 10% as the scarce arms and 100% as the
# reference. Nothing else is scored for P2.
SCARCE = [0.05, 0.10]
REF = 1.00

# The project's documented n_jobs=-1 reproduction tolerance. Not bit-identical
# - see out_of_fold_predictions' own comment on why parallel tree fitting
# cannot be.
TOL = 5e-08

# Amended 2026-10-07 (Rachit), after the post-retag run failed the gate on ONE
# cell: p2p-Gnutella08 / betweenness / r=1 / seed 6, |dtau| = 5.039e-08, all
# other 799 cells bit-identical. tau is a pair statistic, so its smallest
# possible change on an n-node graph is about 1/C(n,2) - one pair changing
# order. On p2p-Gnutella08 (6,299 nodes) that is 5.04e-08, just ABOVE the flat
# 5e-08, so the flat tolerance could not absorb even a single last-bit near-tie
# flip there (the mechanism HANDOFF.md documents for n_jobs=-1), while on
# ca-HepTh it absorbed one. The rule is now stated in pair units: a network
# reproduces if no cell moved by more than one swapped pair. A swap
# (concordant <-> discordant) changes C - D by 2, hence 2 / C(n,2); the flat
# 5e-08 is kept as a floor so the gate never becomes stricter than it was.
# Every network is still compared cell by cell; only the threshold changed.
PAIR_SWAPS_ALLOWED = 1


def tolerance(tag: str) -> float:
    """Per-network reproduction tolerance: max(flat 5e-08, one swapped pair)."""
    # n = nodes tau is computed over: the probe scores every node of the
    # network's cached target table, one row per node.
    n = len(pd.read_csv(f"cache_targets_{tag}.csv"))
    pairs = n * (n - 1) / 2
    return max(TOL, 2 * PAIR_SWAPS_ALLOWED / pairs)


def load() -> pd.DataFrame:
    d = pd.read_csv(SRC)
    if len(d) != 5600:
        print(f"  WARNING: {len(d)} rows, expected 5600 - run incomplete")
    return d


# ---------------------------------------------------------------------------
# 0. Reproduction, which gates everything below
# ---------------------------------------------------------------------------

def check_reproduction(d: pd.DataFrame) -> bool:
    """
    Every fraction=1.0 cell against the published sweep. Returns False if the
    run should be treated as void.
    """
    print("=" * 78)
    print("0. REPRODUCTION - fraction=1.0 vs published sweep_<tag>.csv at FULL")
    print("   If this fails the run is VOID and nothing below means anything.")
    print("=" * 78)
    print(f"\n  {'network':<20s}{'cells':>7s}{'worst |dtau|':>15s}"
          f"{'tolerance':>12s}{'':>4s}")

    worst_overall, n_total, ok = 0.0, 0, True
    for tag in NETS:
        pub = pd.read_csv(f"sweep_{tag}.csv")
        pub = pub[pub.richness == FULL]
        mine = d[(d.network == tag) & (d.fraction == REF)]

        # Join on the cell identity rather than assuming row order - the two
        # files were written by different scripts in different loop orders.
        j = mine.merge(
            pub[["target", "radius", "seed", "kendall_tau"]],
            on=["target", "radius", "seed"],
            suffixes=("_mine", "_pub"), how="inner")

        if j.empty:
            print(f"  {tag:<20s}{0:>7d}{'NO OVERLAP':>15s}   <-- FAIL")
            ok = False
            continue

        w = float((j.kendall_tau_mine - j.kendall_tau_pub).abs().max())
        worst_overall = max(worst_overall, w)
        n_total += len(j)
        tol = tolerance(tag)
        # Count the cells that moved at all, so a pass that rests on the
        # amended tolerance is visible in the output rather than hidden in it.
        moved = int((j.kendall_tau_mine != j.kendall_tau_pub).sum())
        flag = "" if w < tol else "   <-- FAIL"
        if w >= tol:
            ok = False
        note = f"   ({moved} cell(s) not bit-identical)" if moved and not flag else ""
        print(f"  {tag:<20s}{len(j):>7d}{w:>15.2e}{tol:>12.2e}{flag}{note}")

    print(f"\n  {n_total} cells compared, worst |dtau| = {worst_overall:.3e} "
          f"(tolerance per network: max(5e-08, one swapped pair); amended 2026-10-07)")
    print(f"  -> {'PASS' if ok else 'FAIL - RUN IS VOID'}")
    return ok


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def matrix(d, tag, target, frac) -> pd.DataFrame:
    """radius x seed tau matrix for one (network, target, fraction)."""
    sub = d[(d.network == tag) & (d.target == target) & (d.fraction == frac)]
    return sub.pivot_table(index="radius", columns="seed", values="kendall_tau")


def mode_and_support(d, tag, target, frac, eps):
    """
    (modal r*, support, n_seeds) - or (None, 0, 0) when r* is undefined.

    Support is returned rather than discarded because the pre-registered
    scoring rule keys on it directly.
    """
    vals = r_star_per_seed(matrix(d, tag, target, frac), eps)
    if not vals:
        return None, 0, 0
    counts = pd.Series(vals).value_counts().sort_index()
    return int(counts.idxmax()), int(counts.max()), len(vals)


# ---------------------------------------------------------------------------
# 1. P1 - the lab's ~20% claim
# ---------------------------------------------------------------------------

def score_p1(d: pd.DataFrame):
    print("\n" + "=" * 78)
    print("1. P1 - the lab's ~20% claim")
    print("   Declared: tau at 20% within 0.02 of tau at 100%,")
    print("   on the SPREADING targets at r >= 1.")
    print("=" * 78)
    print(f"\n  {'network':<20s}{'target':<14s}{'r':>2s}"
          f"{'tau@20%':>10s}{'tau@100%':>10s}{'drop':>9s}{'':>6s}")

    rows, n_ok = [], 0
    for tag in NETS:
        for target in SPREADING:
            for r in [1, 2, 3]:
                a = d[(d.network == tag) & (d.target == target)
                      & (d.fraction == 0.20) & (d.radius == r)]
                b = d[(d.network == tag) & (d.target == target)
                      & (d.fraction == REF) & (d.radius == r)]
                if a.empty or b.empty:
                    continue
                # Paired within seed, then mean of the differences - the
                # project's standard, never the difference of means.
                p = (a.set_index("seed").kendall_tau
                     - b.set_index("seed").kendall_tau).dropna()
                drop = float(p.mean())
                within = abs(drop) <= 0.02
                n_ok += within
                rows.append({"network": tag, "target": target, "radius": r,
                             "drop": drop, "within": within})
                print(f"  {tag:<20s}{target:<14s}{r:>2d}"
                      f"{a.kendall_tau.mean():>10.4f}{b.kendall_tau.mean():>10.4f}"
                      f"{drop:>+9.4f}{'' if within else '   >0.02':>6s}")

    T = pd.DataFrame(rows)
    print(f"\n  {n_ok}/{len(T)} cells within 0.02  -> "
          f"{'MET' if n_ok == len(T) else 'NOT MET'}")
    if not T.empty:
        # T["drop"], never T.drop - the column name shadows DataFrame.drop.
        i = T["drop"].idxmin()
        print(f"  worst drop {T['drop'].min():+.4f} "
              f"({T.loc[i, 'network']} {T.loc[i, 'target']} "
              f"r={T.loc[i, 'radius']})")
        # The pattern in the failures is the result, not the count. Break the
        # cells down by target so "which targets survive scarcity" is visible
        # rather than buried in a 29/45.
        print(f"\n  {'target':<14s}{'within 0.02':>12s}{'mean drop':>12s}")
        for target in SPREADING:
            s = T[T.target == target]
            print(f"  {target:<14s}{f'{int(s.within.sum())}/{len(s)}':>12s}"
                  f"{s['drop'].mean():>+12.4f}")
    return T


# ---------------------------------------------------------------------------
# 2. P2 / P4 - does r* shift, and in which direction
# ---------------------------------------------------------------------------

def score_p2(d: pd.DataFrame):
    print("\n" + "=" * 78)
    print("2. P2 - does r*(eps) shift under scarcity?")
    print("   Declared (plan, verbatim): scarcity pushes r* DOWN.")
    print("   P4 declared the opposite mechanism in advance: if r* moves UP,")
    print("   P2 is reported as FALSIFIED, not explained away.")
    print("=" * 78)
    print("\n   Scoring rule (fixed before the run): a shift counts only if the")
    print("   modal r* differs AND support >= 6/10 under BOTH arms.")
    print(f"\n  {'network':<20s}{'target':<14s}{'frac':>6s}{'eps':>6s}"
          f"{'scarce':>12s}{'ref(100%)':>12s}{'verdict':>12s}")

    rows = []
    for tag in NETS:
        for target in TARGETS:
            for frac in SCARCE:
                for eps in EPS:
                    ms, ss, ns = mode_and_support(d, tag, target, frac, eps)
                    mr, sr, nr = mode_and_support(d, tag, target, REF, eps)
                    if ms is None or mr is None:
                        continue
                    # The support gate. Below it we record the cell as
                    # unscored rather than silently counting a coin-flip.
                    scored = ss >= 6 and sr >= 6
                    if not scored:
                        verdict = "unscored"
                    elif ms < mr:
                        verdict = "DOWN"
                    elif ms > mr:
                        verdict = "UP"
                    else:
                        verdict = "same"
                    rows.append({"network": tag, "target": target,
                                 "fraction": frac, "eps": eps,
                                 "scarce": ms, "ref": mr, "sup_s": ss,
                                 "sup_r": sr, "scored": scored,
                                 "verdict": verdict})
                    if verdict in ("DOWN", "UP"):
                        print(f"  {tag:<20s}{target:<14s}{frac:>6.2f}{eps:>6.2f}"
                              f"{f'{ms} ({ss}/{ns})':>12s}"
                              f"{f'{mr} ({sr}/{nr})':>12s}{verdict:>12s}")

    T = pd.DataFrame(rows)
    sc = T[T.scored]
    down = int((sc.verdict == "DOWN").sum())
    up = int((sc.verdict == "UP").sum())
    same = int((sc.verdict == "same").sum())
    print(f"\n  scored cells      {len(sc)} of {len(T)} "
          f"({len(T) - len(sc)} dropped for support < 6/10)")
    print(f"    moved DOWN      {down}")
    print(f"    moved UP        {up}")
    print(f"    unchanged       {same}")

    # P2's own scoring clause: majority down, and nothing up by >1 hop.
    moved = down + up
    majority_down = down > up and down > same
    big_up = sc[(sc.verdict == "UP") & (sc.ref - sc.scarce < -1)]
    print(f"\n    cells moving UP by more than one hop: {len(big_up)}")
    if moved == 0:
        verdict = "NOT MET - r* did not move at all under the scoring rule"
    elif majority_down and big_up.empty:
        verdict = "MET"
    elif up > down:
        verdict = "FALSIFIED - r* moved UP on balance (P4's mechanism)"
    else:
        verdict = "NOT MET"
    print(f"\n  P2 -> {verdict}")
    return T


# ---------------------------------------------------------------------------
# 3. P3 - where the effect is largest
# ---------------------------------------------------------------------------

def score_p3(d: pd.DataFrame, T2: pd.DataFrame):
    print("\n" + "=" * 78)
    print("3. P3 - the shift should be LARGEST on betweenness,")
    print("        SMALLEST on spread_mean.")
    print("=" * 78)

    sc = T2[T2.scored]
    print(f"\n  {'target':<14s}{'scored':>8s}{'DOWN':>6s}{'UP':>5s}"
          f"{'same':>6s}{'mean signed shift':>20s}")
    means = {}
    for target in TARGETS:
        s = sc[sc.target == target]
        if s.empty:
            continue
        # Signed shift: scarce - ref, so negative means DOWN.
        shift = float((s.scarce - s.ref).mean())
        means[target] = shift
        print(f"  {target:<14s}{len(s):>8d}"
              f"{int((s.verdict == 'DOWN').sum()):>6d}"
              f"{int((s.verdict == 'UP').sum()):>5d}"
              f"{int((s.verdict == 'same').sum()):>6d}{shift:>+20.3f}")

    if "betweenness" in means and "spread_mean" in means:
        ok = (means["betweenness"] < means["spread_mean"])
        print(f"\n  betweenness shift {means['betweenness']:+.3f} vs "
              f"spread_mean {means['spread_mean']:+.3f}")
        print(f"  P3 -> {'MET' if ok else 'NOT MET'}  "
              f"(betweenness must be the more negative)")


# ---------------------------------------------------------------------------
# 4. The declared confound: how many nonzero labels actually survived
# ---------------------------------------------------------------------------

def nonzero_diagnostic(d: pd.DataFrame):
    """
    The pre-registration required the realised nonzero count to be logged per
    cell so a collapse at 5% could be ATTRIBUTED rather than guessed at. This
    is that attribution: betweenness is 40-70% zeros, so a uniform 5% draw can
    leave a fit with almost no positive labels.
    """
    print("\n" + "=" * 78)
    print("4. DECLARED CONFOUND - realised nonzero training labels")
    print("   Uniform (not stratified) subsampling was chosen deliberately;")
    print("   this is the check that says when a low tau is starvation.")
    print("=" * 78)
    print(f"\n  {'network':<20s}{'target':<14s}"
          f"{'rows@5%':>9s}{'nonzero@5%':>12s}{'nz frac':>9s}")
    for tag in NETS:
        for target in ["betweenness"]:
            s = d[(d.network == tag) & (d.target == target)
                  & (d.fraction == 0.05) & (d.radius == 2)]
            if s.empty:
                continue
            rows = s.train_rows.mean()
            nz = s.train_nonzero.mean()
            print(f"  {tag:<20s}{target:<14s}{rows:>9.0f}{nz:>12.1f}"
                  f"{nz / rows:>9.3f}")


def robustness(d: pd.DataFrame, T2: pd.DataFrame):
    """
    Is P2's falsification an artefact of one network or one fraction?

    It matters because the pre-registration warned about a "small-fraction
    floor": at 5% of a 4/5 training split, email-Eu-core leaves 39 rows against
    168 features at r=3 - fewer rows than columns. A fit that underdetermined
    will prefer a shallow radius for reasons that have nothing to do with
    information horizons, so email's 5% cells could manufacture DOWN moves.

    Dropping email therefore tests the falsification AGAINST ITSELF: removing
    the network most likely to fabricate DOWN moves should, if anything,
    strengthen the UP verdict. It does.
    """
    print("\n" + "=" * 78)
    print("5. ROBUSTNESS - is the P2 verdict one network or one fraction?")
    print("=" * 78)
    sc = T2[T2.scored].copy()
    sc["d"] = sc.scarce - sc.ref

    def tally(x, lab):
        print(f"  {lab:<34s}DOWN {int((x.d < 0).sum()):>3d}   "
              f"UP {int((x.d > 0).sum()):>3d}   same {int((x.d == 0).sum()):>4d}")

    print()
    tally(sc, "all scored cells")
    tally(sc[sc.network != "email-Eu-core"], "excluding email-Eu-core")
    tally(sc[sc.fraction == 0.05], "fraction = 0.05 only")
    tally(sc[sc.fraction == 0.10], "fraction = 0.10 only")

    print("\n  Per target, with email excluded - the dissociation:")
    for target in TARGETS:
        tally(sc[(sc.target == target) & (sc.network != "email-Eu-core")],
              "  " + target)

    print("\n  Underdetermination at fraction=0.05, r=3 (the declared floor):")
    print(f"  {'network':<20s}{'train rows':>11s}{'features':>10s}{'rows/feat':>11s}")
    for tag in NETS:
        s = d[(d.network == tag) & (d.fraction == 0.05)
              & (d.radius == 3) & (d.target == "betweenness")]
        if s.empty:
            continue
        rows, feats = s.train_rows.mean(), s.n_features.mean()
        print(f"  {tag:<20s}{rows:>11.0f}{feats:>10.0f}{rows / feats:>11.2f}")


def main():
    d = load()
    if not check_reproduction(d):
        print("\nSTOPPING: the 100% arm does not reproduce the published "
              "sweep, so the bespoke OOF loop is not the pipeline and every "
              "number in this file is uninterpretable.")
        return 1
    score_p1(d)
    T2 = score_p2(d)
    score_p3(d, T2)
    nonzero_diagnostic(d)
    robustness(d, T2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

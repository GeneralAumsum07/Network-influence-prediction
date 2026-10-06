"""
Analyse the sweep results.

WHAT CHANGED, AND WHY IT MATTERS
--------------------------------
Every cell is now run at several seeds, so every number here carries a spread.
That is not decoration. The conclusions this project draws rest on differences
of 0.001 to 0.02 in Kendall tau, and at one seed there was no way to tell any
of them from noise. A claim that "betweenness saturates at r=1" is only
meaningful if the r1->r2 gain is small COMPARED TO SOMETHING, and the seed
spread is that something.

Marginal gains are computed PAIRED - the same seed's r and r+1 curves are
differenced before averaging. Radii sharing a seed share their fold split, so
the paired difference cancels most of the shared noise and is a far sharper
test than comparing two independent means.

Sections:
  1. Locality budget curves P(r), with seed spread.
  2. r*(eps) across tolerances, and how stable it is across seeds.
  3. Marginal value of each hop, paired, against the noise floor.
  4. Depth vs richness - PER TARGET, because it does not behave the same way
     for a structural target as for a dynamical one.
  5. Cost vs quality, on the repaired cost model.
"""
import glob
import json
import os
import re

import numpy as np
import pandas as pd

pd.set_option("display.width", 220)

# The reference configuration for every P(r) curve is the richest STRUCTURAL
# tier, deliberately not the richest tier overall. The `dynamic` rung assumes
# the observer knows the transmission probability p, and the headline locality
# result must not quietly depend on that. The dynamic tier appears in the
# depth-vs-richness table (section 4), where it can be read as what it is.
FULL = "node+edge+subgraph"
TIER_ORDER = ["node", "node+edge", "node+edge+subgraph",
              "node+edge+subgraph+dynamic"]

# ---------------------------------------------------------------------------
# THE REPORTED OBJECTIVE (decided by Rachit, 2026-09-04)
# ---------------------------------------------------------------------------
# `betweenness` is REPORTED from the log1p-objective arm, not from the raw
# squared-error arm that `sweep_<tag>.csv` holds.
#
# WHY. Betweenness skew runs 4.77 (p2p) to 28.88 (facebook). A model minimising
# squared error on that raw target is dominated by a handful of huge-betweenness
# nodes, which is not what a rank metric rewards. Kendall tau is invariant to
# monotone transforms of the GROUND TRUTH, so training on log1p(y) and scoring
# tau against the untransformed y changes what the model optimises and not what
# it is judged against. It is a correction, not a relaxation. Finding 11 in
# HANDOFF.md documents the mis-specification; Finding 10's carrying rung was
# inflated roughly 3x by it (+0.1291 -> +0.0436, reproduced by three
# independent routes).
#
# SCOPE - BETWEENNESS ONLY. The other three targets are ineligible on
# arithmetic, not stylistic, grounds: `spread_resid` is NEGATIVE on all five
# networks (min -0.9364), so log1p is undefined; `spread_cv` is LEFT-skewed on
# p2p (-0.96), so the transform worsens conditioning; `spread_mean` has low skew
# and the probe's control arm measured a gain of +0.0005. Applying a transform
# where it is not indicated is an intervention, not a correction.
#
# WHAT IS AND IS NOT ON DISK. `sweep_<tag>.csv` is NOT rewritten. The raw
# squared-error corpus stays exactly where it was and stays inspectable - the
# project's record of what it used to believe is not something a later decision
# gets to delete. This function assembles the reported corpus at read time.
#
# IF YOU ARE COMPARING THE TWO OBJECTIVES, pass raw=True (or read
# `sweep_<tag>.csv` directly, as `analyse_objective_resweep.py` does). Calling
# the default here and comparing it to the log1p file compares log1p to itself
# and will show a difference of exactly zero, which is a very convincing wrong
# answer.
REPORTED_BETWEENNESS = os.path.join("estimators", "sweep_{tag}__rf_log1p.csv")


def discover_networks() -> list[str]:
    """
    Every tag with a sweep on disk.

    Globbed rather than hard-coded: the synthetic corpus in stage0_generate.py
    produces around thirty graphs, and a hand-maintained NETS list would be
    wrong the first time anyone used it.
    """
    tags = []
    for path in sorted(glob.glob("sweep_*.csv")):
        m = re.match(r"sweep_(.+)\.csv$", os.path.basename(path))
        if m:
            tags.append(m.group(1))
    return tags


def load(tag: str, path: str | None = None, raw: bool = False) -> pd.DataFrame:
    """
    One network's sweep, de-duplicated, as the project REPORTS it.

    By default the `betweenness` rows are taken from the log1p-objective arm -
    see THE REPORTED OBJECTIVE above for why, and for why it is betweenness
    only. The other three targets come from `sweep_<tag>.csv` unchanged.

    `raw=True` returns the untouched squared-error corpus. Use it only when the
    point is to COMPARE the objectives; using it by accident silently reverts a
    published correction.

    `path` overrides the filename so the alternative-estimator sweeps in
    `estimators/` can reuse this loader rather than re-implementing the
    de-duplication rule below - two copies of that rule is how the two files
    eventually disagree. It is NOT a hook for putting other estimators'
    output beside the baseline: `discover_networks` globs `sweep_*.csv` and
    would read `sweep_ca-GrQc__ridge.csv` as a network called
    `ca-GrQc__ridge`. An explicit `path` implies raw - the caller has already
    said exactly which file it wants.
    """
    d = _read_dedup(path if path is not None else f"sweep_{tag}.csv")
    if raw or path is not None:
        return d
    return _splice_reported_betweenness(d, tag)


def _read_dedup(path: str) -> pd.DataFrame:
    d = pd.read_csv(path)
    if "seed" not in d.columns:
        d["seed"] = 0
    # Keep the last write of any (target, radius, richness, seed) cell - a
    # resumed run can legitimately append the same cell twice.
    return d.drop_duplicates(subset=["target", "radius", "richness", "seed"],
                             keep="last")


def _splice_reported_betweenness(d: pd.DataFrame, tag: str) -> pd.DataFrame:
    """
    Replace the raw betweenness rows with the log1p-objective ones.

    THIS FAILS LOUDLY RATHER THAN FALLING BACK. A silent fallback to the raw
    arm would be the worst available outcome: some sessions would report
    corrected betweenness and some would report the squared-error numbers, both
    without saying which, and the difference (up to 0.086 tau on the facebook
    r=2 subgraph rung) is far larger than the effects this project reports. An
    incomplete corpus is a bug to fix, not a condition to tolerate.
    """
    src = REPORTED_BETWEENNESS.format(tag=tag)
    if not os.path.exists(src):
        raise FileNotFoundError(
            f"{src} is missing, but betweenness is reported from the log1p "
            f"objective (see THE REPORTED OBJECTIVE in analyse.py). Reproduce "
            f"it with:  python stage2_sweep.py {tag} betweenness 3 10 rf_log1p"
            f"\nPass raw=True only if you deliberately want the superseded "
            f"squared-error numbers.")

    lg = _read_dedup(src)
    # Scope enforcement added 2026-09-11 (Claude Opus 5, Task 6 finding P2-05):
    # the log1p arm is betweenness-only by design. A file carrying any other
    # target was produced by something other than the documented command and
    # must not be spliced, however its betweenness rows look.
    extra = sorted(set(lg.target.unique()) - {"betweenness"})
    if extra:
        raise ValueError(
            f"{src} carries targets {extra} besides betweenness; the rf_log1p "
            f"arm is defined for betweenness only and this file is not it.")
    keep = d[d.target != "betweenness"]

    # The two arms must cover the SAME cells - not merely the same NUMBER of
    # cells. Until 2026-09-11 this was a count check (Task 6 finding P2-06): a
    # missing cell plus a spurious extra key still balanced. Key-set equality
    # on (radius, richness, seed) is the check the rest of the project applies.
    raw_keys = {(int(r.radius), r.richness, int(r.seed))
                for r in d[d.target == "betweenness"].itertuples()}
    lg_keys = {(int(r.radius), r.richness, int(r.seed)) for r in lg.itertuples()}
    if raw_keys != lg_keys:
        missing = sorted(raw_keys - lg_keys)[:5]
        spurious = sorted(lg_keys - raw_keys)[:5]
        raise ValueError(
            f"{tag}: log1p betweenness cells != raw betweenness cells "
            f"({len(lg_keys)} vs {len(raw_keys)}). The reported corpus must be "
            f"a cell-for-cell replacement. Missing from log1p: {missing}; "
            f"not in raw: {spurious}.")

    return pd.concat([keep, lg], ignore_index=True)


def curve(d: pd.DataFrame, target: str, richness: str = FULL) -> pd.DataFrame:
    """Mean and spread of tau per radius, plus the per-seed matrix."""
    sub = d[(d.target == target) & (d.richness == richness)]
    g = sub.groupby("radius")["kendall_tau"]
    return pd.DataFrame({"tau_mean": g.mean(), "tau_sd": g.std(ddof=1),
                         "n_seeds": g.size()}).sort_index()


def seed_matrix(d: pd.DataFrame, target: str, richness: str = FULL) -> pd.DataFrame:
    """radius x seed table of tau, for paired comparisons."""
    sub = d[(d.target == target) & (d.richness == richness)]
    return sub.pivot_table(index="radius", columns="seed", values="kendall_tau")


# ---------------------------------------------------------------------------
# r*(eps)
# ---------------------------------------------------------------------------

def r_star_per_seed(mat: pd.DataFrame, eps: float) -> list[int]:
    """
    r*(eps) computed independently within each seed.

    Each seed is a complete, self-consistent experiment: its own fold split,
    its own forest, its own P(r) curve. Computing r* inside a seed and then
    looking at the spread of answers tells us something averaging the curves
    first would hide - namely how often the reported radius would have come
    out differently had we simply picked another random split.

    That instability IS a result for this project. A field that reports a
    single ad hoc radius is implicitly claiming the number is stable; if ours
    moves across seeds, saying so is the honest version of the criticism.
    """
    out = []
    for seed in mat.columns:
        col = mat[seed].dropna().sort_index()
        if col.empty:
            continue
        ceiling = col.max()
        ok = col[col >= (1 - eps) * ceiling]
        if len(ok):
            out.append(int(ok.index.min()))
    return out


def r_star_summary(mat: pd.DataFrame, eps: float) -> str:
    """
    One cell of the r*(eps) table: the modal radius, and how often it wins.

    We report the mode with its support rather than a mean, because r* is an
    ordinal count of hops - "1.4 hops" is not a thing an observer can do.
    """
    vals = r_star_per_seed(mat, eps)
    if not vals:
        return "-"
    counts = pd.Series(vals).value_counts().sort_index()
    mode = int(counts.idxmax())
    return f"{mode} ({counts.max()}/{len(vals)})"


def main() -> None:
    nets = discover_networks()
    if not nets:
        raise SystemExit("no sweep_*.csv found - run stage2_sweep.py first")
    print(f"networks found: {', '.join(nets)}")

    # -- 1. locality budget curves -----------------------------------------
    print("\n" + "=" * 78)
    print("1. LOCALITY BUDGET CURVES   P(r) +/- seed sd, full feature richness")
    print("=" * 78)
    for tag in nets:
        d = load(tag)
        try:
            meta = json.load(open(f"cache_meta_{tag}.json"))
            hdr = (f"n={meta['n']}, <k>={meta['mean_degree']:.1f}, "
                   f"p={meta['multiple']}x beta_c={meta['p']:.4f}, "
                   f"{meta['n_sims']} sims, {meta.get('convention','?')}")
        except FileNotFoundError:
            hdr = "(no cache_meta)"
        print(f"\n{tag}  ({hdr})")
        # Build per-target Series indexed on radius and align them, rather than
        # assuming every target was swept to the same depth. A partially
        # finished run is the normal state of an interrupted sweep, and the
        # table should still print.
        cols = {}
        for target in sorted(d.target.unique()):
            c = curve(d, target)
            cols[target] = pd.Series(
                [f"{m:.4f} +/-{s:.4f}" if np.isfinite(s) else f"{m:.4f}"
                 for m, s in zip(c.tau_mean, c.tau_sd)],
                index=[f"r={r}" for r in c.index])
        table = pd.DataFrame(cols).fillna("-")
        print(table.to_string())

    # -- 2. r*(eps) ---------------------------------------------------------
    print("\n" + "=" * 78)
    print("2. r*(eps) ACROSS TOLERANCES, WITH SEED STABILITY")
    print("   cell = modal r* (how many seeds agreed)")
    print("=" * 78)
    rows = []
    for tag in nets:
        d = load(tag)
        for target in sorted(d.target.unique()):
            mat = seed_matrix(d, target)
            c = curve(d, target)
            row = {"network": tag, "target": target,
                   "ceiling_tau": f"{c.tau_mean.max():.4f}"}
            for eps in [0.20, 0.10, 0.05, 0.02, 0.01]:
                row[f"eps={eps:.2f}"] = r_star_summary(mat, eps)
            rows.append(row)
    print(pd.DataFrame(rows).to_string(index=False))

    # -- 3. marginal value of each hop, paired -----------------------------
    print("\n" + "=" * 78)
    print("3. MARGINAL VALUE OF EACH EXTRA HOP  (paired across seeds)")
    print("   'sig' = |mean gain| > 2 x sd of the paired per-seed gain")
    print("=" * 78)
    for tag in nets:
        d = load(tag)
        print(f"\n{tag}")
        for target in sorted(d.target.unique()):
            mat = seed_matrix(d, target)
            radii = sorted(mat.index)
            parts = []
            for a, b in zip(radii[:-1], radii[1:]):
                diff = (mat.loc[b] - mat.loc[a]).dropna()
                if diff.empty:
                    continue
                m, s = diff.mean(), diff.std(ddof=1)
                sig = "*" if abs(m) > 2 * s else " "
                parts.append(f"r{a}->r{b}: {m:+.4f}+/-{s:.4f}{sig}")
            base = mat.loc[radii[0]].mean()
            print(f"  {target:14s} base(r0)={base:.4f}   " + "  ".join(parts))

    # -- 4. depth vs richness, per target ----------------------------------
    print("\n" + "=" * 78)
    print("4. DEPTH vs RICHNESS   (gain from adding tiers, at fixed radius)")
    print("   Reported PER TARGET: it does not behave the same way for a")
    print("   structural target as for a dynamical one.")
    print("=" * 78)
    for tag in nets:
        d = load(tag)
        print(f"\n{tag}")
        for target in sorted(d.target.unique()):
            sub = d[d.target == target]
            piv = sub.pivot_table(index="radius", columns="richness",
                                  values="kendall_tau", aggfunc="mean")
            piv = piv[[c for c in TIER_ORDER if c in piv.columns]]
            piv["gain"] = piv[FULL] - piv["node"]
            # Noise floor. Until 2026-09-11 this was the UNPAIRED sd across
            # seeds of the richest configuration alone (Task 6 finding P2-06).
            # The seeds are shared between the two tiers - seed s draws the
            # same folds for `node` and for FULL - so the right yardstick is
            # the sd of the per-seed DIFFERENCE, which is what every paired
            # table elsewhere in the project uses. Both are printed: `seed_sd`
            # is kept for continuity with older RESULTS.txt captures, and
            # `beats_noise` now reads off the paired sd. (Claude Opus 5)
            full_s = (sub[sub.richness == FULL]
                      .pivot_table(index="radius", columns="seed", values="kendall_tau"))
            node_s = (sub[sub.richness == "node"]
                      .pivot_table(index="radius", columns="seed", values="kendall_tau"))
            common = [c for c in full_s.columns if c in node_s.columns]
            piv["seed_sd"] = full_s[common].std(axis=1, ddof=1)
            piv["paired_sd"] = (full_s[common] - node_s[common]).std(axis=1, ddof=1)
            piv["beats_noise"] = np.where(piv["gain"].abs() > 2 * piv["paired_sd"],
                                          "yes", "no")
            print(f"  target = {target}   (beats_noise: |gain| > 2 x paired_sd, "
                  f"paired over {len(common)} shared seeds)")
            print(piv.round(4).to_string().replace("\n", "\n  "))

    # -- 5. cost vs quality -------------------------------------------------
    print("\n" + "=" * 78)
    print("5. COST vs QUALITY   (Pareto frontier marked *)")
    print("   feature_seconds now reflects only the extraction groups a cell")
    print("   actually used - see feature_cost() in influence/experiment.py.")
    print("=" * 78)
    for tag in nets:
        d = load(tag)
        if "spread_mean" not in set(d.target):
            continue
        sub = (d[d.target == "spread_mean"]
               .groupby(["radius", "richness"], as_index=False)
               .agg(kendall_tau=("kendall_tau", "mean"),
                    feature_seconds=("feature_seconds", "mean"),
                    fit_seconds=("fit_seconds", "mean")))
        sub["total_seconds"] = sub.feature_seconds + sub.fit_seconds
        sub = sub.sort_values("total_seconds")
        best, front = -np.inf, []
        for _, r in sub.iterrows():
            on = r.kendall_tau > best
            best = max(best, r.kendall_tau)
            front.append(on)
        sub["on_frontier"] = front
        print(f"\n{tag}  (frontier marked *)")
        for _, r in sub.iterrows():
            print(f"  {'*' if r.on_frontier else ' '} r={int(r.radius)} "
                  f"{r.richness:20s} feat={r.feature_seconds:6.2f}s "
                  f"fit={r.fit_seconds:6.2f}s  tau={r.kendall_tau:.4f}")


if __name__ == "__main__":
    main()

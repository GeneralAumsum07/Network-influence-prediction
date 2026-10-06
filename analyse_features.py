"""
analyse_features.py - is the feature table as informative as it looks?

WHY THIS EXISTS
---------------
The feature set reached 43 columns before anyone asked how many *dimensions*
it held. The answer was about five. Worse, five of the six edge- and
subgraph-tier features turned out to be exact algebraic functions of node-tier
features:

    triangle_count     = clustering x k(k-1)/2
    ego_net_edges      = triangle_count + k
    edges_leaving_ego  = nbr_degree_sum - 2*triangle_count - k
    ego_net_density    = ego_net_edges / [(k+1)k/2]
    boundary_porosity  = edges_leaving_ego / (ego_net_edges + edges_leaving_ego)

That matters because the depth-versus-richness result compares tiers. If the
tiers do not differ in information, the comparison is not measuring what it
claims to, and "richness does not help" is a statement about the ladder rather
than about the world. The only genuinely independent non-node feature in the
original set was ego_betweenness - which is exactly why richness helped the
betweenness target and nothing else.

So this file checks, automatically and every time, the things that were
previously assumed:

  1. Which features are rank-identical to another (pure duplicates).
  2. How many dimensions the table really has.
  3. Which features are predictable from the others - "derived" columns that
     add a transform but no information.
  4. THE TIER TEST: can each tier's features be predicted from the tiers below
     it? If yes, that rung of the richness ladder is decorative.

Run:  python analyse_features.py [tag ...]
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split

TIER_ORDER = ["node", "edge", "subgraph", "dynamic"]
MAX_ROWS = 4000          # subsample for the regression probes
DERIVED_R2 = 0.999       # above this, a column carries no new information


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(((y_true - y_pred) ** 2).sum())
    ss_tot = float(((y_true - y_true.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0


def predictability(X: np.ndarray, y: np.ndarray, seed: int = 0) -> float:
    """
    How well can this column be reconstructed from those columns?

    A gradient-boosted tree rather than a linear fit, because the dependencies
    that matter here are products and ratios - `triangle_count` is clustering
    TIMES a function of degree, which no linear probe would flag.

    Scored on held-out rows. Training R^2 would approach 1 for anything given
    enough depth and would call every feature derived.
    """
    if X.shape[1] == 0 or np.ptp(y) == 0:
        return np.nan
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3,
                                          random_state=seed)
    m = HistGradientBoostingRegressor(max_iter=120, random_state=seed)
    m.fit(Xtr, ytr)
    return _r2(yte, m.predict(Xte))


def analyse(tag: str) -> None:
    X = pd.read_csv(f"cache_features_{tag}.csv")
    reg = pd.read_csv(f"cache_registry_{tag}.csv")
    cols = [c for c in reg.feature if c in X.columns]
    reg = reg[reg.feature.isin(cols)]
    M = X[cols].to_numpy(dtype=np.float64)

    rng = np.random.default_rng(0)
    idx = (rng.choice(len(M), MAX_ROWS, replace=False)
           if len(M) > MAX_ROWS else np.arange(len(M)))
    Ms = M[idx]

    print("\n" + "=" * 78)
    print(f"{tag}   n={len(M):,}   features={len(cols)}")
    print("=" * 78)

    # -- 0. exact closed-form identities ------------------------------------
    # The ML probe in section 3 UNDERSTATES derivedness for exact algebraic
    # relations: a tree approximates a product with axis-aligned splits and
    # never quite reaches R^2 = 1, so `triangle_count` scores 0.998 rather than
    # 1.0 and slips past any threshold. Identities we know in closed form are
    # therefore checked directly, to machine precision. This doubles as a
    # regression guard - if a future edit reintroduces a derived column, it
    # shows up here rather than inflating the feature count unnoticed.
    print("\n0. EXACT CLOSED-FORM IDENTITIES (checked to machine precision)")
    g = {c: X[c].to_numpy(dtype=np.float64) for c in cols}
    k = g.get("degree")
    identities = []
    if k is not None and "clustering_coefficient" in g:
        tri = g["clustering_coefficient"] * k * (k - 1) / 2.0
        identities.append(("triangle_count", tri,
                           "clustering x k(k-1)/2"))
        if "ego_net_edges" in g:
            identities.append(("ego_net_edges", tri + k,
                               "triangle_count + k"))
        if "edges_leaving_ego" in g and "nbr_degree_sum" in g:
            identities.append(("edges_leaving_ego",
                               g["nbr_degree_sum"] - 2 * tri - k,
                               "nbr_degree_sum - 2*triangle_count - k"))
        if "ego_net_density" in g:
            tot = (k + 1) * k / 2.0
            identities.append(("ego_net_density",
                               np.where(tot > 0, (tri + k) / tot, 0.0),
                               "ego_net_edges / [(k+1)k/2]"))
    if k is not None and "ego_net_size" in g:
        identities.append(("ego_net_size", k + 1.0, "degree + 1"))

    any_exact = False
    for nm, recon, formula in identities:
        if nm not in g:
            continue
        err = float(np.abs(recon - g[nm]).max())
        exact = err < 1e-8
        any_exact |= exact
        print(f"   {'EXACT  ' if exact else 'differs'}  {nm:20s} = {formula:42s}"
              f" max|err|={err:.1e}")
    if any_exact:
        print("   -> these columns carry a transform, not information. Any tier")
        print("      comparison that relies on them is not varying what it claims.")

    # -- 1. exact duplicates ------------------------------------------------
    rho = np.abs(spearmanr(M).statistic)
    np.fill_diagonal(rho, 0.0)
    print("\n1. RANK-IDENTICAL GROUPS (Spearman |rho| = 1: pure duplicates)")
    seen, found = set(), False
    for i, c in enumerate(cols):
        if c in seen:
            continue
        grp = [cols[j] for j in range(len(cols)) if rho[i, j] > 0.999999]
        if grp:
            found = True
            seen.update(grp + [c])
            print(f"   {' == '.join([c] + grp)}")
    if not found:
        print("   none")

    n95 = int((rho > 0.95).any(axis=1).sum())
    print(f"\n   features with |rho| > 0.95 to some other feature: "
          f"{n95}/{len(cols)}")

    # -- 2. effective dimensionality ---------------------------------------
    R = np.apply_along_axis(lambda v: pd.Series(v).rank().to_numpy(), 0, M)
    R = (R - R.mean(0)) / (R.std(0) + 1e-12)
    ev = np.linalg.svd(R, compute_uv=False) ** 2
    ev = ev / ev.sum()
    cum = np.cumsum(ev)
    print("\n2. EFFECTIVE DIMENSIONALITY (PCA on rank-standardised columns)")
    for thr in (0.90, 0.95, 0.99):
        print(f"   components for {int(thr * 100)}% of rank variance: "
              f"{int(np.searchsorted(cum, thr) + 1):3d}  of {len(cols)}")

    # -- 3. derived columns -------------------------------------------------
    print(f"\n3. DERIVED COLUMNS (held-out R^2 predicting each from all others)")
    print(f"   listed when R^2 > {DERIVED_R2}: carries a transform, not information")
    rows = []
    for j, c in enumerate(cols):
        others = np.delete(Ms, j, axis=1)
        rows.append((c, predictability(others, Ms[:, j])))
    derived = [(c, r) for c, r in rows if np.isfinite(r) and r > DERIVED_R2]
    if derived:
        for c, r in sorted(derived, key=lambda t: -t[1]):
            print(f"   R^2={r:.5f}  {c}")
    else:
        print("   none")
    print(f"   ({len(derived)}/{len(cols)} derived)")

    # -- 4. the tier test ---------------------------------------------------
    print("\n4. TIER TEST - does each rung of the richness ladder add anything?")
    print("   For every feature, R^2 predicting it from ALL LOWER-TIER features")
    print("   at the same radius or below. High R^2 = that rung is decorative.")
    for t_i, tier in enumerate(TIER_ORDER[1:], start=1):
        sub = reg[reg.tier == tier]
        if sub.empty:
            continue
        lower = TIER_ORDER[:t_i]
        print(f"\n   tier '{tier}' vs {lower}")
        worst, best = [], []
        for _, r in sub.iterrows():
            base = [c for c in cols
                    if reg.loc[reg.feature == c, "tier"].iloc[0] in lower
                    and reg.loc[reg.feature == c, "hop"].iloc[0] <= r.hop]
            if not base:
                continue
            bi = [cols.index(c) for c in base]
            score = predictability(Ms[:, bi], Ms[:, cols.index(r.feature)])
            (worst if score > DERIVED_R2 else best).append((r.feature, score))
        for nm, sc in sorted(worst, key=lambda t: -t[1]):
            print(f"      DERIVED   R^2={sc:.5f}  {nm}")
        for nm, sc in sorted(best, key=lambda t: t[1]):
            print(f"      new info  R^2={sc:.5f}  {nm}")
        if worst:
            print(f"      -> {len(worst)}/{len(worst)+len(best)} of this tier "
                  f"is recoverable from the tiers below it")


def discover() -> list[str]:
    return [re.match(r"cache_features_(.+)\.csv$", os.path.basename(p)).group(1)
            for p in sorted(glob.glob("cache_features_*.csv"))]


if __name__ == "__main__":
    tags = sys.argv[1:] or discover()
    if not tags:
        raise SystemExit("no cache_features_*.csv found - run stage1_prepare.py")
    for t in tags:
        analyse(t)

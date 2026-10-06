"""
targets.py
==========
Ground truth (the things we predict) and the leakage guard.

TARGETS vs FEATURES
-------------------
Targets are computed with FULL knowledge of the graph. That is fine - they are
the answer key. What must never happen is a target, or anything equivalent to
one, ending up in the feature matrix. That would hand the model the answer and
silently void every result.

The guard at the bottom of this file is not decoration. Run it before every
model fit.

WHAT WE COMPUTE
---------------
  spread_mean : expected cascade size. The primary target.
  spread_cv   : coefficient of variation of cascade size (volatility).
  spread_resid: volatility with the mean's contribution regressed out - see
                the long comment on that function for why the raw variance is
                misleading.
  betweenness : exact betweenness centrality. A structural target, and a
                validation check (a pipeline that cannot recover betweenness
                from local features has a bug).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from .preprocessing import Network
from .dynamics import CascadeResults


# ----------------------------------------------------------------------------
# Global structural targets
# ----------------------------------------------------------------------------

def exact_betweenness(net: Network, fast: bool = True) -> np.ndarray:
    """
    Exact betweenness centrality.

    Two paths, both computing the SAME quantity:

      fast=True  - igraph's C implementation. Used for anything above a few
                   thousand nodes, where pure Python is impractical.
      fast=False - our own Brandes implementation below.

    We wrote ours first and verified the two agree to floating-point precision
    (see tests). Using the C version afterwards is an engineering choice about
    speed, not an inherited result - the algorithm is a specification and we
    have checked our reading of it.
    """
    if fast:
        try:
            import igraph as ig
            coo = sp.triu(net.adj, k=1).tocoo()
            g = ig.Graph(n=net.n,
                         edges=list(zip(coo.row.tolist(), coo.col.tolist())),
                         directed=False)
            return np.asarray(g.betweenness(), dtype=np.float64)
        except ImportError:
            pass  # fall through to the pure-Python version

    return _brandes_betweenness(net)


def _brandes_betweenness(net: Network) -> np.ndarray:
    """
    Exact betweenness centrality via Brandes' algorithm, written out in full.

    This is unambiguously GLOBAL - it needs shortest paths between every pair
    in the network. Kept as the reference implementation that the fast path is
    validated against.
    """
    n = net.n
    bc = np.zeros(n, dtype=np.float64)
    indptr, indices = net.adj.indptr, net.adj.indices

    for s in range(n):
        # --- single-source shortest paths (BFS, unweighted) ---
        stack = []
        preds = [[] for _ in range(n)]
        sigma = np.zeros(n, dtype=np.float64)   # number of shortest paths
        dist = np.full(n, -1, dtype=np.int64)
        sigma[s] = 1.0
        dist[s] = 0
        queue = [s]
        qi = 0
        while qi < len(queue):
            v = queue[qi]; qi += 1
            stack.append(v)
            for w in indices[indptr[v]:indptr[v + 1]]:
                w = int(w)
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    preds[w].append(v)

        # --- accumulation, walking back from the furthest nodes ---
        delta = np.zeros(n, dtype=np.float64)
        while stack:
            w = stack.pop()
            for v in preds[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                bc[w] += delta[w]

    # Each undirected pair is counted from both endpoints.
    return bc / 2.0


# ----------------------------------------------------------------------------
# betweenness_k - the truncated, and therefore LOCAL, betweenness (C5)
# ----------------------------------------------------------------------------

def truncated_betweenness(net: Network, k: int,
                          batch: int = 128) -> np.ndarray:
    """
    `betweenness_k`: ordinary betweenness restricted to source-target pairs at
    graph distance <= k.

    ```math
    b_k(v) = \\sum_{\\substack{i \\ne v \\ne j \\\\ d(i,j) \\le k}}
             \\frac{\\sigma_{ij}(v)}{\\sigma_{ij}}
    ```

    Defined in Appendix A.4 of arXiv 2601.16236 (Exarchakos, van der Hofstad,
    Nagy, Pandey, "Bringing order to network centrality measures", Jan 2026),
    which demonstrates betweenness6 / betweenness10 against full betweenness on
    a 3.7M-vertex citation network. This is OUR implementation of THEIR
    definition; nothing here is inherited from their code.

    WHY THIS FUNCTION BELONGS TO THIS PROJECT AND NOT MERELY TO ITS BIBLIOGRAPHY
    ---------------------------------------------------------------------------
    b_k is a RADIUS-k LOCAL RULE BY CONSTRUCTION, so it drops straight into the
    project's radius protocol at matched r and is a closed-form, ZERO-TRAINING
    competitor to the 171-feature model at its own game.

    Proof, because the loose version of it is easy to get wrong. Take any pair
    (i, j) contributing a nonzero term, so d(i,j) <= k and v lies on at least
    one shortest i-j path; hence d(v,i) + d(v,j) = d(i,j). Let u be any node on
    ANY shortest i-j path - including the paths that avoid v, which matter
    because sigma_ij counts them. Then

        d(v,u) <= d(v,i) + d(i,u)     and     d(v,u) <= d(v,j) + d(j,u)

    and the two right-hand sides sum to [d(v,i) + d(v,j)] + [d(i,u) + d(u,j)]
    = d(i,j) + d(i,j) <= 2k. A minimum is at most the mean of the two, so
    d(v,u) <= k. Every geodesic that enters b_k(v) - numerator and denominator
    alike - therefore lies inside the k-ball around v. QED.

    The naive version of this argument ("d(i,j) <= k and v on the path implies
    d(i,v) <= k") establishes only which PAIRS matter, not that sigma_ij is
    computable locally, and sigma_ij is exactly the part that could have
    reached outside. It does not, but that needed showing.

    b_1 IS IDENTICALLY ZERO, and that is a fact about the definition rather
    than a bug: a geodesic between adjacent nodes is the edge itself and has no
    interior vertex. The k=1 row exists in the output tables to make that
    visible instead of quietly starting the sweep at k=2.

    HOW IT IS COMPUTED
    ------------------
    Brandes with the BFS stopped at depth k and the dependency accumulation
    started from depth k rather than from the eccentricity. The truncation is
    exactly the standard recursion with the target indicator switched off past
    depth k:

        delta_s^k(v) = sum_{w in Succ(v)} (sigma_v / sigma_w)
                       * ( [d(s,w) <= k] + delta_s^k(w) )

    so initialising delta = 0 at depth k and never visiting deeper IS the
    restriction - no separate bookkeeping is needed. sigma is exact for every
    node at depth <= k because all shortest paths to a depth-d node pass only
    through nodes at depth < d.

    The loop is VECTORISED OVER A BATCH OF SOURCES rather than written as the
    textbook per-source scalar loop, and that is not premature optimisation:
    `_brandes_betweenness` above is pure Python and takes hours on
    facebook_combined, whose average distance (3.7) means a depth-3 BFS is most
    of the graph. Each level becomes one sparse-dense product:

        forward   sigma_{d}  = (A @ sigma_{d-1}) masked to the unvisited
        backward  delta_{d-1} = sigma_{d-1} * (A @ [(1 + delta_d) / sigma_d])

    which is the same recursion, one level at a time, for `batch` sources at
    once. Cost is O(k * nnz * n / batch) products of shape (n, batch).

    Correctness is not argued from the algebra alone - `analyse_betweenness_k.py`
    checks that b_k at k >= diameter reproduces the cached exact betweenness
    column, which is the strongest available end-to-end test and also catches
    node-ordering drift between the rebuilt graph and the cache.

    Returns an array of length net.n, on the same scale as `exact_betweenness`
    (endpoints excluded, each undirected pair counted once).
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    n = net.n
    A = net.adj.astype(np.float64)
    bc = np.zeros(n, dtype=np.float64)

    for start in range(0, n, batch):
        srcs = np.arange(start, min(start + batch, n))
        b = len(srcs)
        rows = np.arange(b)

        # --- forward pass: shortest-path counts, level by level -------------
        # sigma_lv[d][v, j] = number of shortest paths from source srcs[j] to v,
        # nonzero only where d(srcs[j], v) == d. masks[d] is that level's
        # membership, kept separately because sigma can legitimately be large
        # and we never want to test it for exact zero after arithmetic.
        sigma0 = np.zeros((n, b), dtype=np.float64)
        sigma0[srcs, rows] = 1.0
        mask0 = np.zeros((n, b), dtype=bool)
        mask0[srcs, rows] = True

        sigma_lv, masks = [sigma0], [mask0]
        visited = mask0.copy()

        for _ in range(k):
            cand = A @ sigma_lv[-1]
            new = (cand > 0) & ~visited
            sigma_lv.append(np.where(new, cand, 0.0))
            masks.append(new)
            visited |= new

        # --- backward pass: dependency accumulation -------------------------
        # delta starts at zero, which IS the truncation: nodes at depth k are
        # given no successors, so no target beyond distance k contributes.
        delta = np.zeros((n, b), dtype=np.float64)
        for d in range(k, 0, -1):
            sig_d = sigma_lv[d]
            # The (1 + delta) numerator: the 1 counts w itself as a target,
            # which is legitimate precisely because d(s,w) = d <= k.
            coef = np.divide(1.0 + delta, sig_d,
                             out=np.zeros_like(delta), where=masks[d])
            contrib = A @ coef
            # A node at level d-1 has all its DAG-successors at level d, so
            # this ASSIGNS its delta rather than accumulating into it.
            delta = np.where(masks[d - 1], sigma_lv[d - 1] * contrib, delta)

        # Brandes' "if w != s" - a source is not a target of its own pairs.
        delta[srcs, rows] = 0.0
        bc += delta.sum(axis=1)

    # Each undirected pair is reached from both of its endpoints.
    return bc / 2.0


# ----------------------------------------------------------------------------
# Volatility with the mean decoupled
# ----------------------------------------------------------------------------

def variance_residual(mean: np.ndarray, std: np.ndarray,
                      n_bins: int = 30) -> np.ndarray:
    """
    Volatility with the mean's mechanical contribution removed.

    THE TRAP THIS AVOIDS
    --------------------
    Cascade-size variance is strongly coupled to cascade-size mean: a seed
    that reaches 500 nodes on average has far more room to vary than one that
    reaches 3. So a model that "predicts variance" well may simply be
    predicting the mean a second time, dressed up as a new result.

    The fix: work out how much spread you would EXPECT from a node's mean
    alone, and predict only what is left over.

    We fit the expected relationship non-parametrically, by binning nodes on
    their mean and taking the median std within each bin. That avoids assuming
    any particular functional form (sqrt, linear, whatever) - the data tells
    us the shape.

    Returns the residual in log space, so it is a multiplicative deviation:
    positive means "more volatile than nodes of similar reach", negative means
    less.
    """
    lm = np.log10(np.maximum(mean, 1e-9))
    ls = np.log10(np.maximum(std, 1e-9))

    # Bin by mean, using quantiles so every bin holds a similar node count.
    edges = np.quantile(lm, np.linspace(0, 1, n_bins + 1))
    edges = np.unique(edges)
    if len(edges) < 3:
        return ls - ls.mean()

    idx = np.clip(np.searchsorted(edges, lm, side="right") - 1,
                  0, len(edges) - 2)

    expected = np.zeros_like(ls)
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() > 0:
            expected[m] = np.median(ls[m])

    return ls - expected


# ----------------------------------------------------------------------------
# Assembling the target table
# ----------------------------------------------------------------------------

def build_targets(net: Network, cascade: CascadeResults,
                  include_betweenness: bool = True,
                  verbose: bool = True) -> pd.DataFrame:
    """Assemble every target into one table, one row per node."""
    out = {"node": np.arange(net.n)}

    mean = cascade.mean
    std = cascade.std
    out["spread_mean"] = mean
    out["spread_std"] = std
    out["spread_cv"] = cascade.cv
    out["spread_resid"] = variance_residual(mean, std)
    out["spread_ignition"] = cascade.ignition_probability(0.05)

    if include_betweenness:
        if verbose:
            print("  computing exact betweenness (global, O(nm))...")
        out["betweenness"] = exact_betweenness(net)

    return pd.DataFrame(out)


# ----------------------------------------------------------------------------
# THE LEAKAGE GUARD
# ----------------------------------------------------------------------------

# Any feature name containing one of these is a global quantity that must
# never be used as an input. Matching is on substrings so that variants
# ('betweenness_norm', 'log_pagerank') are caught too.
FORBIDDEN_IN_FEATURES = (
    "betweenness",      # unless prefixed 'ego_' - handled below
    "closeness",
    "pagerank",
    "eigenvector",
    "katz",
    "harmonic",
    "eccentricity",
    "coreness",
    "core_number",
    "k_shell",
    "spread_",          # any target column
    "influence_true",
)

# Explicitly allowed exceptions: these ARE local despite matching above.
ALLOWED_EXCEPTIONS = (
    "ego_betweenness",           # computed inside the ego network only
    "collective_influence_1",    # CI is a local shell score, not a target
    "collective_influence_2",
    "collective_influence_3",
)


def assert_no_leakage(feature_names: list[str]) -> None:
    """
    Raise if any global quantity has crept into the feature set.

    Call this immediately before every model fit. It costs microseconds and it
    is the only thing standing between a working experiment and a beautiful,
    meaningless result.
    """
    offenders = []
    for name in feature_names:
        lower = name.lower()
        if lower in (e.lower() for e in ALLOWED_EXCEPTIONS):
            continue
        for bad in FORBIDDEN_IN_FEATURES:
            if bad in lower:
                offenders.append(name)
                break

    if offenders:
        raise ValueError(
            "LEAKAGE DETECTED - global quantities found in the feature set:\n"
            + "\n".join(f"    - {o}" for o in offenders)
            + "\n  These are targets or global measures. They may be predicted "
              "or used as rival baselines, never as model inputs."
        )

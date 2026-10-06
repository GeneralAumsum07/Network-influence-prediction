"""
structure.py
============
Structural measurements of a whole network - the axes r* gets plotted against.

WHAT THIS IS FOR
----------------
The locality sweep answers "how far must you look on THIS network." That is
one number per network. To turn a pile of such numbers into a result we need
to say what property of the network the number depends on.

This module computes those properties: the degree tail exponent, the
assortativity, the clustering, and the localization diagnostic. Every one is
a GLOBAL measurement of the graph.

IMPORTANT - THIS IS NOT A FEATURE MODULE
-----------------------------------------
Nothing in here may ever enter the feature matrix. Most of it is per-NETWORK
descriptors used to organise results across networks, not per-NODE inputs to
a model. The distinction is easy to blur and the leakage guard will not
catch the per-network ones, because those quantities never become columns in
the feature table. Keeping them in a separate module from features.py is the
structural defence against that mistake.

The second half of this file holds PER-NODE GLOBAL quantities - coreness,
distance to the nearest hub. Those are one number per node and therefore look
exactly like features, which makes them the more dangerous half. They exist
for one purpose: the failure atlas needs to describe what local prediction is
blind to, and it can only do that using information the model was denied. They
are computed from the whole graph and are legitimate as PROFILING axes and as
rival baselines, never as inputs.

The leakage guard is the backstop here rather than the first line: 'coreness'
and 'k_shell' are both in FORBIDDEN_IN_FEATURES, so a column of these reaching
the feature matrix aborts the run.
"""

from __future__ import annotations

import heapq

import numpy as np
import scipy.sparse as sp
from scipy.special import zeta

from .preprocessing import Network


# ----------------------------------------------------------------------------
# Degree tail exponent - Clauset, Shalizi & Newman (2009)
# ----------------------------------------------------------------------------

def _fit_alpha(x: np.ndarray, xmin: int) -> float:
    """
    MLE for alpha at a fixed xmin, by direct search.

    THE MODEL. A DISCRETE power law above xmin:

        p(x) = x^-alpha / zeta(alpha, xmin)

    with zeta the Hurwitz zeta function. Degrees are integers, so the discrete
    form is the correct one; the continuous formula most papers use is an
    approximation that is measurably biased for small xmin, which is exactly
    the regime degree data lives in.

    (This log-likelihood previously also existed as a standalone
    `_discrete_powerlaw_loglik` helper that nothing ever called - the scan
    below has always evaluated its own vectorised copy. The unused version was
    deleted rather than wired in, because two spellings of one likelihood is
    precisely how a formula and its implementation drift apart.)

    There is no closed form in the discrete case, so we scan rather than call
    an optimizer. The likelihood is smooth and unimodal in alpha, the range of
    interest is narrow, and a scan cannot fail to converge or land in a local
    optimum.

    The scan is VECTORISED over the alpha grid. That is not a micro-
    optimisation: this function runs once per candidate xmin, and the
    bootstrap runs the whole xmin loop hundreds of times over. The naive
    Python loop made the bootstrap too slow to run at all, which in practice
    meant the uncertainty simply would not get reported.

    The trick is that the log-likelihood

        ll(alpha) = -n * log(zeta(alpha, xmin)) - alpha * sum(log x)

    depends on the data only through n and sum(log x), both scalars. So the
    entire grid evaluates as one vectorised zeta call.
    """
    n = len(x)
    slogx = np.log(x).sum()

    def ll_grid(alphas):
        return -n * np.log(zeta(alphas, xmin)) - alphas * slogx

    coarse = np.arange(1.01, 6.0, 0.01)
    best = float(coarse[np.argmax(ll_grid(coarse))])

    fine = np.arange(max(1.005, best - 0.01), best + 0.01, 0.0005)
    return float(fine[np.argmax(ll_grid(fine))])


def fit_power_law_tail(degrees: np.ndarray,
                       xmin_max: int = 50,
                       n_bootstrap: int = 0,
                       seed: int = 0) -> dict:
    """
    Fit a power-law tail to a degree sequence the Clauset-Shalizi-Newman way.

    THE METHOD, AND WHY NOT THE OBVIOUS ONE
    ---------------------------------------
    The common approach - histogram the degrees, take logs, fit a straight
    line - is badly biased. Log-binning distorts the tail, the fitted line is
    dominated by the many low-degree nodes rather than the few that define
    the tail, and it gives no way to decide where the tail even starts.

    CSN's method instead:
      1. For each candidate xmin, fit alpha by maximum likelihood on the data
         above xmin only.
      2. Measure the Kolmogorov-Smirnov distance between the empirical CDF
         above xmin and the fitted power law's CDF.
      3. Pick the xmin that MINIMISES that distance.

    So xmin is chosen by goodness of fit rather than by eye, which is the
    whole point - "where the power law starts" stops being a judgement call.

    WHAT THIS DOES NOT DO
    ---------------------
    It does not test whether a power law is a good model at all. CSN's full
    procedure includes a bootstrapped p-value and comparison against
    lognormal alternatives. We report `ks_distance` so the quality of the fit
    is visible, but a small KS distance is not evidence that the degree
    distribution IS a power law. For our purposes alpha is a summary of tail
    heaviness used as a plotting axis, not a claim about the generating
    process, and it should be described that way in any writeup.

    WHY THE BOOTSTRAP IS NOT OPTIONAL HERE
    --------------------------------------
    We measured this estimator against synthetic data with a known exponent
    (see verify_generators.py). At a KNOWN xmin the MLE is essentially exact,
    error under 0.007. But once xmin is chosen by KS, the selected xmin sits
    far out in the tail and leaves only a few hundred points behind it, and
    the error grows to 0.1-0.3 at sample sizes comparable to our networks.

    In other words the uncertainty in gamma is dominated by xmin SELECTION,
    not by the MLE. On a 5,000-node network that uncertainty is large enough
    to matter for any claim of the form "r* varies with gamma" - if the error
    bar on gamma is +/-0.25, a gamma sweep has far fewer distinguishable
    points than it appears to.

    Set n_bootstrap > 0 to get `alpha_std` and a 95% interval by resampling
    the degree sequence with replacement and refitting end to end, xmin
    selection included. Report it. A gamma without an error bar is not usable
    as a regression axis.
    """
    x_all = np.asarray(degrees, dtype=np.int64)
    x_all = x_all[x_all > 0]
    if len(x_all) < 50:
        return {"alpha": np.nan, "xmin": np.nan, "n_tail": 0,
                "ks_distance": np.nan, "reliable": False,
                "tail_fraction": np.nan}

    candidates = np.unique(x_all)
    candidates = candidates[candidates <= xmin_max]

    best = {"alpha": np.nan, "xmin": np.nan, "n_tail": 0,
            "ks_distance": np.inf}

    for xmin in candidates:
        tail = x_all[x_all >= xmin]
        # Need enough tail data for the MLE to mean anything. CSN suggest
        # roughly 50 points as a floor.
        if len(tail) < 50:
            continue

        alpha = _fit_alpha(tail, int(xmin))

        # KS distance between empirical and fitted CDFs on the tail.
        vals = np.arange(int(xmin), int(tail.max()) + 1)
        # Theoretical CDF: 1 - zeta(alpha, k) / zeta(alpha, xmin)
        cdf_theory = 1.0 - zeta(alpha, vals) / zeta(alpha, int(xmin))
        # Empirical CDF evaluated at the same points.
        cdf_emp = np.searchsorted(np.sort(tail), vals, side="right") / len(tail)
        ks = float(np.abs(cdf_emp - cdf_theory).max())

        if ks < best["ks_distance"]:
            best = {"alpha": float(alpha), "xmin": int(xmin),
                    "n_tail": int(len(tail)), "ks_distance": ks}

    # --- reliability flag -------------------------------------------------
    # FAILURE MODE THIS CATCHES (found by testing, not by reasoning):
    # when the true tail is steep and n is small, there are not 50 points
    # above any genuinely tail-like xmin. KS selection then falls back to a
    # low xmin and happily fits the BULK of the distribution instead of the
    # tail, returning a confident-looking number that is simply wrong. On a
    # 1,000-node Chung-Lu graph built with gamma = 3.4 this returned 1.81
    # with n_tail = 954 out of 1,000 nodes.
    #
    # A fit that keeps most of the data is not a tail fit. We say so rather
    # than returning a plausible number.
    if np.isfinite(best["alpha"]):
        tail_fraction = best["n_tail"] / len(x_all)
        best["tail_fraction"] = float(tail_fraction)
        best["reliable"] = bool(tail_fraction < 0.5 and best["n_tail"] >= 50)
    else:
        best["tail_fraction"] = np.nan
        best["reliable"] = False

    # --- uncertainty, by resampling the WHOLE procedure -------------------
    # Note we refit xmin inside every bootstrap replicate rather than
    # holding it at the point estimate. Holding xmin fixed would report only
    # the MLE's variance and would badly understate the true uncertainty,
    # since xmin selection is the dominant source.
    if n_bootstrap > 0 and np.isfinite(best["alpha"]):
        rng = np.random.default_rng(seed)
        draws = []
        for _ in range(n_bootstrap):
            resample = rng.choice(x_all, size=len(x_all), replace=True)
            b = fit_power_law_tail(resample, xmin_max=xmin_max, n_bootstrap=0)
            if np.isfinite(b["alpha"]):
                draws.append(b["alpha"])
        if draws:
            draws = np.asarray(draws)
            best["alpha_std"] = float(draws.std(ddof=1))
            best["alpha_ci_lo"] = float(np.percentile(draws, 2.5))
            best["alpha_ci_hi"] = float(np.percentile(draws, 97.5))
            best["n_bootstrap"] = len(draws)

    return best


# ----------------------------------------------------------------------------
# Newman (2002) degree assortativity
# ----------------------------------------------------------------------------

def degree_assortativity(net: Network) -> float:
    """
    Pearson correlation between the degrees at the two ends of an edge.

    Positive means hubs attach to hubs (social networks typically);
    negative means hubs attach to leaves (technological networks typically).

    We compute it directly from the edge list rather than from Newman's
    e_jk matrix formulation. The two are algebraically identical - the
    matrix form is just this correlation written out in terms of the joint
    degree distribution - and the direct form avoids building an n x n
    object.

    Each undirected edge is entered in BOTH orientations. This is not
    optional bookkeeping: without it the correlation depends on which
    endpoint you happened to list first, which is arbitrary.
    """
    c = sp.triu(net.adj, k=1).tocoo()
    if c.nnz == 0:
        return np.nan

    ku = net.degree[c.row].astype(np.float64)
    kv = net.degree[c.col].astype(np.float64)

    a = np.concatenate([ku, kv])
    b = np.concatenate([kv, ku])

    sa, sb = a.std(), b.std()
    if sa == 0 or sb == 0:
        return np.nan          # regular graph: correlation undefined
    return float(np.mean((a - a.mean()) * (b - b.mean())) / (sa * sb))


# ----------------------------------------------------------------------------
# Clustering
# ----------------------------------------------------------------------------

def clustering_measures(net: Network) -> dict:
    """
    Both clustering conventions, because they answer different questions and
    the literature switches between them without saying so.

      transitivity      = 3 * triangles / connected triples, computed over the
                          WHOLE graph. Dominated by high-degree nodes.
      average_clustering = mean over nodes of the per-node clustering
                          coefficient. Dominated by low-degree nodes, since
                          most nodes have low degree.

    On a hub-heavy network these two can differ by an order of magnitude. We
    report both and always name which one a figure uses.
    """
    A = net.adj.astype(np.float64)
    # Triangles through each node = diagonal of A^3, halved.
    A3_diag = np.asarray((A @ A).multiply(A).sum(axis=1)).ravel()
    tri_per_node = A3_diag / 2.0

    k = net.degree.astype(np.float64)
    pairs = k * (k - 1) / 2.0

    total_triangles = tri_per_node.sum() / 3.0
    total_triples = pairs.sum()

    with np.errstate(divide="ignore", invalid="ignore"):
        per_node = np.where(pairs > 0, tri_per_node / pairs, 0.0)

    return {
        "transitivity": float(3 * total_triangles / total_triples)
                        if total_triples > 0 else 0.0,
        "average_clustering": float(per_node.mean()),
        "n_triangles": int(round(total_triangles)),
    }


# ----------------------------------------------------------------------------
# The localization duel - Chung, Lu & Vu (2003)
# ----------------------------------------------------------------------------

def localization_duel(net: Network) -> dict:
    """
    Which term controls the leading adjacency eigenvalue:

        lambda_1  ~  max( sqrt(k_max),  <k^2> / <k> )

    The two terms correspond to two different mechanisms:

      sqrt(k_max) winning  -> the eigenvector LOCALIZES on the single largest
                              hub. The spectral threshold is then set by one
                              node, and a local view centred anywhere else
                              has little chance of seeing what drives
                              spreading.

      <k^2>/<k> winning    -> the eigenvector is DELOCALIZED across the whole
                              degree distribution. Spreading is a collective
                              property of the tail, which a local view has a
                              much better chance of sampling.

    That is a direct, testable prediction about the locality horizon: r*
    should behave differently on either side of this crossover. It is the
    first component of what the reading list calls the certificate.

    We return both terms, which wins, and the ratio, so the crossover can be
    used as a continuous axis rather than a binary label.
    """
    k = net.degree.astype(np.float64)
    k_max = float(k.max())
    ratio_term = float((k ** 2).mean() / k.mean())
    sqrt_term = float(np.sqrt(k_max))

    return {
        "k_max": k_max,
        "sqrt_k_max": sqrt_term,
        "k2_over_k1": ratio_term,
        "localized": bool(sqrt_term > ratio_term),
        "duel_ratio": float(sqrt_term / ratio_term) if ratio_term > 0 else np.inf,
    }


# ----------------------------------------------------------------------------
# One call for everything
# ----------------------------------------------------------------------------

def structural_profile(net: Network, n_bootstrap: int = 0,
                       seed: int = 0) -> dict:
    """
    Every whole-network descriptor in one dict, ready to become a row in the
    cross-network results table.

    This is what gets joined against r* to produce the r*(structure) plots.
    """
    prof = {
        "network": net.name,
        "n": net.n,
        "m": net.m,
        "mean_degree": net.mean_degree,
        "assortativity": degree_assortativity(net),
    }
    prof.update(clustering_measures(net))
    prof.update(localization_duel(net))

    tail = fit_power_law_tail(net.degree, n_bootstrap=n_bootstrap, seed=seed)
    prof.update({"gamma": tail["alpha"], "gamma_xmin": tail["xmin"],
                 "gamma_ks": tail["ks_distance"], "gamma_n_tail": tail["n_tail"],
                 "gamma_reliable": tail.get("reliable", False),
                 "gamma_tail_fraction": tail.get("tail_fraction", np.nan),
                 "gamma_std": tail.get("alpha_std", np.nan),
                 "gamma_ci_lo": tail.get("alpha_ci_lo", np.nan),
                 "gamma_ci_hi": tail.get("alpha_ci_hi", np.nan)})
    return prof


# ----------------------------------------------------------------------------
# PER-NODE GLOBAL QUANTITIES - PROFILING AXES, NEVER FEATURES
# ----------------------------------------------------------------------------

def core_numbers(net: Network) -> np.ndarray:
    """
    k-core number of every node, by peeling.

    The k-core is the maximal subgraph in which every node has degree at least
    k; a node's core number is the largest k whose core contains it. The
    algorithm is the obvious one: repeatedly remove the lowest-degree node,
    recording the running maximum of the degree at removal.

    THIS IS GLOBAL. Peeling cannot stop at any radius - removing a node
    anywhere can cascade to a node arbitrarily far away, which is exactly why
    coreness is a target-side quantity here and not a feature. Its local
    counterpart is the H-index ladder in features.py, which converges toward
    coreness as the order grows without ever leaving a bounded neighbourhood.
    The gap between the two is one of the more informative columns in the
    failure atlas: it measures how badly the local proxy under-reads the
    global core for a given node.

    Implemented here rather than taken from igraph so that the comparison
    against the H-ladder is between two things we wrote. verify_pipeline.py
    checks it against igraph's coreness.
    """
    n = net.n
    deg = net.degree.astype(np.int64).copy()
    core = np.zeros(n, dtype=np.int64)
    removed = np.zeros(n, dtype=bool)

    # Min-heap with lazy deletion: when a node's degree drops we push the new
    # value rather than trying to find and update the old entry, and discard
    # any popped entry that no longer matches the node's current degree. That
    # keeps the whole thing O(m log n) with no bookkeeping structure beyond the
    # heap itself - the naive "rescan for the minimum each round" version is
    # O(n^2) and visibly slow by a few thousand nodes.
    heap = [(int(deg[i]), i) for i in range(n)]
    heapq.heapify(heap)

    k = 0
    while heap:
        d, i = heapq.heappop(heap)
        if removed[i] or d != deg[i]:
            continue                  # stale entry, superseded by a later push
        k = max(k, d)
        core[i] = k
        removed[i] = True
        for j in net.nbrs[i]:
            if not removed[j]:
                deg[j] -= 1
                heapq.heappush(heap, (int(deg[j]), int(j)))
    return core


def distance_to_hubs(net: Network, top_fraction: float = 0.01) -> np.ndarray:
    """
    Hop distance from every node to the nearest node in the top `top_fraction`
    by degree.

    Multi-source BFS seeded from all hubs at once, which gives every node its
    distance to the closest of them in one sweep.

    Why the atlas wants this: a node whose own neighbourhood looks unremarkable
    can still sit one step from a structure that carries an entire cascade. A
    bounded local view cannot tell "unremarkable and isolated" from
    "unremarkable but adjacent to the core", and that is precisely the kind of
    blind spot the atlas exists to name. Hub proximity is global information -
    it requires knowing who the hubs are, which requires the whole degree
    sequence.
    """
    n = net.n
    k = max(1, int(round(top_fraction * n)))
    hubs = np.argsort(net.degree)[::-1][:k]

    dist = np.full(n, -1, dtype=np.int64)
    dist[hubs] = 0
    frontier = np.asarray(hubs, dtype=np.int64)
    d = 0
    while len(frontier):
        d += 1
        nxt = np.unique(np.concatenate([net.nbrs[u] for u in frontier])) \
            if len(frontier) else np.empty(0, dtype=np.int64)
        nxt = nxt[dist[nxt] < 0]
        dist[nxt] = d
        frontier = nxt
    # Disconnected nodes cannot occur inside the LCC, but be explicit.
    dist[dist < 0] = n
    return dist


def structural_report(net: Network, n_bootstrap: int = 0) -> str:
    """Human-readable version. Print alongside describe() for every network."""
    p = structural_profile(net, n_bootstrap=n_bootstrap)
    return "\n".join([
        f"Structure: {net.name}",
        f"  n / m                  : {p['n']:,} / {p['m']:,}",
        f"  mean degree            : {p['mean_degree']:.3f}",
        f"  degree tail gamma      : {p['gamma']:.3f}"
        + (f" +/- {p['gamma_std']:.3f}" if np.isfinite(p.get('gamma_std', np.nan)) else "")
        + f"  (xmin={p['gamma_xmin']}, n_tail={p['gamma_n_tail']}, KS={p['gamma_ks']:.4f})"
        + ("" if p.get('gamma_reliable') else "   <- UNRELIABLE, tail too thin"),
        f"  assortativity          : {p['assortativity']:+.4f}",
        f"  transitivity           : {p['transitivity']:.4f}",
        f"  average clustering     : {p['average_clustering']:.4f}",
        f"  sqrt(k_max)            : {p['sqrt_k_max']:.3f}",
        f"  <k^2>/<k>              : {p['k2_over_k1']:.3f}",
        f"  regime                 : {'LOCALIZED (hub-dominated)' if p['localized'] else 'DELOCALIZED (tail-dominated)'}",
    ])

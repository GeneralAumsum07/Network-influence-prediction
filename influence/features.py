"""
features.py
===========
Strictly-local feature extraction.

THE ONE RULE
------------
Every feature in this file must be computable from a BOUNDED neighbourhood
around a node. Nothing here may look at the whole graph.

That is not a stylistic preference - it is the entire experiment. If a global
quantity (betweenness, closeness, PageRank) ever leaks into this file, the
model is being handed the answer key and every downstream result is void.
There is an automated check for this in targets.py; keep it passing.

HOP TAGGING
-----------
Every feature is registered with the radius it needs:

    hop 0 : the node's own edges only
    hop 1 : the node + its neighbours + edges among them (the ego network)
    hop 2 : adds friends-of-friends
    hop 3 : adds one ring further

This tagging is what makes the radius sweep a one-line filter instead of a
rewrite. `features_up_to(df, r)` gives you exactly the columns a radius-r
observer could have computed.

TIER TAGGING
------------
Independently of radius, features are tagged by what OBJECT they describe:

    node     : properties of the node itself
    edge     : properties of its incident edges, aggregated
    subgraph : counts of small structures it participates in

Radius and tier are two separate axes. That is deliberate - it lets us ask
whether it is better to look FURTHER (more hops) or look RICHER (more tiers)
for the same compute budget.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .preprocessing import Network


# ----------------------------------------------------------------------------
# Feature registry
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class FeatureSpec:
    """Metadata for one feature column."""
    name: str
    hop: int          # smallest radius that can compute it
    tier: str         # 'node' | 'edge' | 'subgraph'
    description: str
    group: str        # extraction group whose timer paid for this feature


class FeatureRegistry:
    """Collects specs as features are computed, so metadata never drifts."""

    def __init__(self):
        self._specs: dict[str, FeatureSpec] = {}

    def add(self, name, hop, tier, description, group):
        """
        Register one feature.

        `group` names the timed extraction block that produced it. Carrying it
        here rather than reconstructing it downstream is what makes the cost
        model correct by construction. experiment.py used to infer the mapping
        from hop and tier, and inferred it wrongly in both directions: it
        charged r=1 for the CI_2 and CI_3 work that r=1 cannot use, and
        charged nothing at all for the step from r=2 to r=3. A feature that
        forgets its group now shows up as a missing cost rather than as a
        silently mis-attributed one.
        """
        self._specs[name] = FeatureSpec(name, hop, tier, description, group)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [{"feature": s.name, "hop": s.hop, "tier": s.tier,
              "group": s.group, "description": s.description}
             for s in self._specs.values()]
        ).sort_values(["hop", "tier", "feature"]).reset_index(drop=True)


# ----------------------------------------------------------------------------
# Shared primitives
# ----------------------------------------------------------------------------

def bfs_shells(net: Network, source: int, max_hop: int) -> list[np.ndarray]:
    """
    Return the nodes at EXACTLY distance 1, 2, ..., max_hop from `source`.

    This is the workhorse for every multi-hop feature. We return shells rather
    than balls because shells are what the hop-tagging needs; a ball is just
    the concatenation of shells, which callers can do cheaply.

    Implemented with a visited bitmask rather than a set: for repeated calls
    across every node in the graph, the array version is substantially faster
    and allocates nothing per level beyond the frontier itself.
    """
    visited = np.zeros(net.n, dtype=bool)
    visited[source] = True

    shells = []
    frontier = net.nbrs[source]
    frontier = frontier[~visited[frontier]]
    visited[frontier] = True

    for _ in range(max_hop):
        shells.append(frontier)
        if len(frontier) == 0:
            # Neighbourhood exhausted; pad with empties so callers can index
            # shells[k] safely regardless of graph structure.
            frontier = np.empty(0, dtype=np.int64)
            continue
        # Next shell = neighbours of the frontier that we have not seen.
        nxt = np.concatenate([net.nbrs[u] for u in frontier])
        nxt = np.unique(nxt)
        nxt = nxt[~visited[nxt]]
        visited[nxt] = True
        frontier = nxt

    return shells


def _safe_div(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    """
    Elementwise num/den, zero where den is zero, without evaluating 0/0.

    `np.where(den > 0, num / den, 0.0)` gives the right ANSWER but computes the
    invalid division first and discards it, which raises a RuntimeWarning and
    briefly materialises NaN. That never surfaced while every graph was its own
    largest connected component and no node had degree 0. Angle 4 breaks that
    assumption on purpose - a damaged graph has isolated nodes, and their
    features must come out as clean zeros with no warning and no NaN in flight.
    """
    out = np.zeros_like(num, dtype=np.float64)
    return np.divide(num, den, out=out, where=den > 0)


_ALL_STATS = ("mean", "max", "min", "std", "sum")


def _stats(values: np.ndarray, prefix: str, out: dict,
           suffixes: tuple[str, ...] = _ALL_STATS) -> None:
    """
    Summarise a variable-length vector into fixed-width features.

    Every node has a different number of neighbours, but the model needs a
    fixed-width row. Summary statistics are how we standardise that - this is
    exactly the "min / max / std / count of my neighbours' degrees" construction.

    Empty input yields zeros rather than NaN, so downstream models never see
    missing values.

    `suffixes` exists so a caller can omit a statistic that would be an exact
    function of something already in the table. The sum of edge embeddedness
    over a node's incident edges, for instance, is precisely 2 x triangle_count
    - emitting it would add a column and no information.
    """
    fns = {"mean": np.mean, "max": np.max, "min": np.min,
           "std": np.std, "sum": np.sum}
    if len(values) == 0:
        for suffix in suffixes:
            out[f"{prefix}_{suffix}"] = 0.0
        return
    v = values.astype(np.float64)
    for suffix in suffixes:
        out[f"{prefix}_{suffix}"] = float(fns[suffix](v))


# ----------------------------------------------------------------------------
# The H-index ladder  (hop-parameterised, computed for the whole graph at once)
# ----------------------------------------------------------------------------

def h_operator(values: np.ndarray) -> int:
    """
    The H-operator: the largest h such that at least h of the values are >= h.

    This is the same operator as a researcher's h-index, applied to a node's
    neighbours instead of to paper citations.
    """
    if len(values) == 0:
        return 0
    v = np.sort(values)[::-1]          # descending
    # v[i] >= i+1 means "at least i+1 entries are >= i+1"
    idx = np.arange(1, len(v) + 1)
    ok = v >= idx
    return int(idx[ok].max()) if ok.any() else 0


def h_index_ladder(net: Network,
                   max_order: int) -> tuple[list[np.ndarray], list[float]]:
    """
    Compute h^(1), h^(2), ..., h^(max_order) for every node.

        h^(0)(i) = degree(i)
        h^(n+1)(i) = H({ h^(n)(j) : j a neighbour of i })

    This is a radius ladder in disguise: h^(n) depends on information exactly
    n hops away. So h^(1) is a hop-1 feature, h^(2) is a hop-2 feature, and so
    on - which is why it slots directly into the radius sweep.

    It is also our incumbent baseline: iterating this operator converges toward
    the k-core number, so the ladder interpolates between degree (purely local)
    and coreness (global). We compute it ourselves rather than taking anyone's
    reported behaviour on faith.

    Returns the ladder AND the wall-clock cost of each order separately.
    Per-order timing matters because order n is a hop-n feature: a radius-r
    observer pays for orders 1..r and nothing beyond. Timing the ladder as a
    single block would charge r=1 for work only r=3 uses, which is exactly the
    cost-attribution bug this project had to fix once already.
    """
    current = net.degree.astype(np.int64)
    ladder: list[np.ndarray] = []
    seconds: list[float] = []
    for _ in range(max_order):
        t0 = time.perf_counter()
        nxt = np.empty(net.n, dtype=np.int64)
        for i in range(net.n):
            nxt[i] = h_operator(current[net.nbrs[i]])
        seconds.append(time.perf_counter() - t0)
        ladder.append(nxt)
        current = nxt
    return ladder, seconds


# ----------------------------------------------------------------------------
# Collective Influence  (Morone & Makse form, radius-parameterised)
# ----------------------------------------------------------------------------

def collective_influence(net: Network, ell: int) -> np.ndarray:
    """
        CI_l(i) = (k_i - 1) * sum over j at EXACTLY distance l from i of (k_j - 1)

    Note the "exactly distance l" - it is the shell, not the ball. This is a
    genuinely local score with the radius as an explicit parameter, which makes
    it the natural classical competitor in the radius sweep.

    THIS IS NOW THE REFERENCE IMPLEMENTATION, NOT THE PRODUCTION PATH.
    `shell_and_ci_pass` below computes the same numbers far more cheaply by
    reusing one traversal. We keep this straightforward version because the
    fast path is verified against it - the same discipline applied to Brandes
    betweenness and the Ihara-Bass eigenvalue elsewhere in the project.
    """
    out = np.zeros(net.n, dtype=np.float64)
    km1 = (net.degree - 1).astype(np.float64)
    for i in range(net.n):
        shells = bfs_shells(net, i, ell)
        shell = shells[ell - 1]
        out[i] = km1[i] * km1[shell].sum() if len(shell) else 0.0
    return out


def neighbourhood_pass(net: Network, max_hop: int, p_transmission: float | None = None):
    """
    One BFS per node producing every radius-parameterised feature at once,
    with a per-hop cost breakdown.

    WHY EVERYTHING SHARES ONE TRAVERSAL
    -----------------------------------
    The obvious implementation walks each node's neighbourhood once per
    feature family: once for shell statistics, once per Collective Influence
    radius, again for anything else. Measured before these were merged, shells
    plus CI alone were 78-94% of feature-extraction time. Every quantity below
    is a different reading of the same walk, so it is taken during the walk.

    WHAT IT PRODUCES, AND WHAT IS ACTUALLY NEW
    ------------------------------------------
    shell counts / degree stats / CI
        As before.

    shell degree SUMS
        Needed for the gravity model. Not emitted as features - the sum is
        count x mean, which the table already holds.

    BALL-INTERNAL STRUCTURE (this is the real gap being closed)
        Every previous multi-hop feature was a count or a degree summary of a
        shell. None of them ever looked at the edges AMONG those nodes. So the
        feature set could see how many friends-of-friends a node had and how
        well connected they were, but nothing whatever about how they were
        wired to each other. `ball_internal_edges` and `ball_volume` give the
        2-ball's internal edge count and degree volume, from which density and
        conductance follow.

        Only the 2-ball is measured, deliberately. On a dense network the
        3-ball is most of the graph - on email-Eu-core the 2-ball already
        covers about 93% of nodes - so a 3-ball density stops being a local
        quantity in any useful sense while costing a great deal more. That the
        2-ball can already swallow a dense network is not a defect of the
        measurement; it is the reason locality saturates there, and it is worth
        being able to see.

    TRUNCATED PERCOLATION REACH (optional, needs p)
        The ground truth is bond percolation at probability p. This is the
        local estimate of that same quantity: propagate a reach probability
        outward along the BFS layers and sum it, stopping at radius r.

            q(i) = 1,   q(j) = 1 - prod over parents u of (1 - p * q(u))

        where a parent is a neighbour of j one layer closer to i. Summing q
        over the r-ball estimates the expected cascade size visible within r
        hops.

        This is an approximation and it is worth being precise about how. It
        treats the paths arriving at j as independent, which they are not when
        the neighbourhood contains cycles, so it over-estimates in clustered
        regions. It is the standard tree/independent-path approximation, and
        the point is not that it is exact but that it is MECHANISTIC - derived
        from the dynamics rather than from generic structure.

        It uses p, which is a parameter of the spreading process rather than
        anything about the graph. That is a real modelling assumption: the
        observer is assumed to know the transmission rate. It is not leakage -
        no global structure enters, and p is a known constant in the same sense
        n is - but any result using this feature has to state the assumption,
        so it is registered under its own tier and is easy to exclude.

    THE PER-HOP TIMER, AND WHERE TO CHARGE THE EXPANSION
    ----------------------------------------------------
    Expanding the frontier at level h is what PRODUCES level h+1, so its cost
    belongs to h+1. Charging it to the level that triggered it makes the
    deepest hop look nearly free and makes the cumulative cost of reaching
    radius r overstate by one expansion. We therefore charge each expansion
    forward to the level it creates, so sum(hop_seconds[:r]) is exactly the
    cost of seeing radius r.

    Clearing the visited buffer is deliberately left untimed: it is bookkeeping
    for the next source, not work any observer pays for.
    """
    n = net.n
    shell_counts = np.zeros((n, max_hop), dtype=np.float64)
    shell_deg_mean = np.zeros((n, max_hop), dtype=np.float64)
    shell_deg_max = np.zeros((n, max_hop), dtype=np.float64)
    shell_deg_sum = np.zeros((n, max_hop), dtype=np.float64)
    ci = np.zeros((n, max_hop), dtype=np.float64)
    ball2_edges = np.zeros(n, dtype=np.float64)
    ball2_volume = np.zeros(n, dtype=np.float64)
    perc = np.zeros((n, max_hop), dtype=np.float64)

    deg = net.degree.astype(np.float64)
    km1 = deg - 1.0
    hop_seconds = [0.0] * max_hop
    want_perc = p_transmission is not None

    # Reused scratch buffers. Clearing only the entries we touched keeps the
    # per-node cost proportional to the neighbourhood rather than to n.
    visited = np.zeros(n, dtype=bool)
    inball = np.zeros(n, dtype=bool)
    qbuf = np.zeros(n, dtype=np.float64)

    for i in range(n):
        t0 = time.perf_counter()

        visited[i] = True
        touched = [np.array([i], dtype=np.int64)]

        # Building shell 1 is hop-1 work.
        frontier = net.nbrs[i]
        frontier = frontier[~visited[frontier]]
        visited[frontier] = True
        if want_perc:
            qbuf[i] = 1.0
            # A direct neighbour is reached iff its single edge transmits.
            q_frontier = np.full(len(frontier), p_transmission, dtype=np.float64)
            qbuf[frontier] = q_frontier
            # The seed is always part of its own cascade, so reach starts at 1.
            reach = 1.0 + float(q_frontier.sum())
        t1 = time.perf_counter(); hop_seconds[0] += t1 - t0; t0 = t1

        for h in range(max_hop):
            if len(frontier):
                shell_counts[i, h] = len(frontier)
                d = deg[frontier]
                shell_deg_mean[i, h] = d.mean()
                shell_deg_max[i, h] = d.max()
                shell_deg_sum[i, h] = d.sum()
                # CI_(h+1) = (k_i - 1) * sum over this shell of (k_j - 1)
                ci[i, h] = km1[i] * km1[frontier].sum()
            touched.append(frontier)
            if want_perc:
                perc[i, h] = reach
            # Statistics on shell h+1 are hop-(h+1) work.
            t1 = time.perf_counter(); hop_seconds[h] += t1 - t0; t0 = t1

            # Expand only if a further level is still needed. The expansion
            # PRODUCES shell h+2, so it is charged forward to that level.
            if h + 1 < max_hop and len(frontier):
                counts = np.fromiter((len(net.nbrs[u]) for u in frontier),
                                     dtype=np.int64, count=len(frontier))
                dst = np.concatenate([net.nbrs[u] for u in frontier])
                fresh = ~visited[dst]
                nxt = np.unique(dst[fresh])
                if want_perc and len(nxt):
                    # One message per (parent -> child) arc that reaches a
                    # newly discovered node. Working in logs turns the product
                    # over parents into a bincount sum.
                    src = np.repeat(frontier, counts)[fresh]
                    child = dst[fresh]
                    contrib = np.log1p(-p_transmission * qbuf[src])
                    logprod = np.bincount(child, weights=contrib, minlength=n)
                    q_next = 1.0 - np.exp(logprod[nxt])
                    qbuf[nxt] = q_next
                    reach += float(q_next.sum())
                visited[nxt] = True
                t1 = time.perf_counter(); hop_seconds[h + 1] += t1 - t0; t0 = t1
            else:
                nxt = np.empty(0, dtype=np.int64)
                t0 = time.perf_counter()

            # --- 2-ball internal structure, once shell 2 exists -------------
            if h == 1:
                ball = np.concatenate(touched)
                if len(ball):
                    inball[ball] = True
                    nbr_cat = np.concatenate([net.nbrs[u] for u in ball])
                    # Each internal edge is seen from both endpoints.
                    ball2_edges[i] = float(inball[nbr_cat].sum()) / 2.0
                    ball2_volume[i] = float(deg[ball].sum())
                    inball[ball] = False
                t1 = time.perf_counter(); hop_seconds[1] += t1 - t0; t0 = t1

            frontier = nxt

        for arr in touched:
            visited[arr] = False
        if want_perc:
            for arr in touched:
                qbuf[arr] = 0.0

    return {"shell_counts": shell_counts, "shell_deg_mean": shell_deg_mean,
            "shell_deg_max": shell_deg_max, "shell_deg_sum": shell_deg_sum,
            "ci": ci, "ball2_edges": ball2_edges, "ball2_volume": ball2_volume,
            "perc": perc if want_perc else None, "hop_seconds": hop_seconds}


def shell_and_ci_pass(net: Network, max_hop: int):
    """
    Backwards-compatible view of `neighbourhood_pass`.

    Kept because verify_pipeline.py checks this signature's outputs against the
    separate reference implementations bit for bit, and that check is the thing
    standing between a refactor and a silently changed feature table.
    """
    r = neighbourhood_pass(net, max_hop)
    return (r["shell_counts"], r["shell_deg_mean"], r["shell_deg_max"],
            r["ci"], r["hop_seconds"])




# ----------------------------------------------------------------------------
# Ego-network betweenness  (Everett & Borgatti form)
# ----------------------------------------------------------------------------

def ego_betweenness(net: Network) -> np.ndarray:
    """
    Betweenness of the ego computed INSIDE its own ego network only.

    Derivation (why we can do this without running full betweenness):
    within an ego network, any two neighbours j,k of the ego are either
    directly connected - in which case the shortest path between them has
    length 1 and cannot pass through the ego - or they are not, in which case
    every shortest path has length 2 and runs through some common neighbour.
    The ego is always one such common neighbour.

    So for each non-adjacent pair (j,k):
        sigma_jk        = number of their common neighbours inside the ego net
        sigma_jk(ego)   = 1        (the ego itself)
        contribution    = 1 / sigma_jk

    Summing that over non-adjacent neighbour pairs gives the ego's betweenness
    within its ego network exactly - a purely local brokerage measure.

    TWO IMPLEMENTATIONS, AND WHY
    ----------------------------
    The set-based version below is the readable statement of the formula and is
    kept as the reference. It is also quadratic in the degree with Python-level
    set operations in the inner loop, which is fine on a sparse graph and not
    fine on a dense one: after the shell/CI traversal was merged, this function
    became 57% of all feature-extraction time on email-Eu-core (mean degree 33)
    while staying around 9% on the two sparse networks.

    The fast path builds the neighbour-adjacency matrix of the ego network once
    and gets every pairwise common-neighbour count from a single matrix
    product, which is where the work belongs. It is used when the degree is
    small enough that a k x k matrix is cheap; above that the dense matrix
    would cost more memory than it saves time, so we fall back.

    The two agree to floating-point tolerance rather than bit-for-bit, because
    they sum the same terms in a different order and floating-point addition is
    not associative. verify_pipeline.py checks that agreement.
    """
    out = np.zeros(net.n, dtype=np.float64)

    for i in range(net.n):
        nb = net.nbrs[i]
        k = len(nb)
        if k < 2:
            continue
        out[i] = (_ego_betweenness_dense(net, nb, k)
                  if k >= EGO_DENSE_MIN_DEGREE
                  else _ego_betweenness_sets(net, nb, k))

    return out


# The dense path is used only for HIGH-degree nodes. Getting this comparison
# the right way round matters, and it was measured rather than guessed:
#
#   using dense for every node          email 1.48x   ca-GrQc 0.29x   Gnutella 0.25x
#   using dense for small k as well     3-4x SLOWER on both sparse networks
#
# Building a k x k matrix and a matmul is pure overhead when k is 6, which is
# the mean degree on the sparse networks and therefore the common case there.
# It only starts paying at the hubs: email-Eu-core has mean degree 33 and a
# max of 345, and essentially all of its 1.48x came from that tail.
#
# At 128 no node in either sparse pilot network (max degree 81 and 97) takes
# the dense path at all, so this can only help and can never hurt. The gain is
# modest today - feature extraction is about a second, while the model fits are
# hundreds - but it grows with density, and denser corpora are on the roadmap.
EGO_DENSE_MIN_DEGREE = 128


def _ego_betweenness_dense(net: Network, nb: np.ndarray, k: int) -> float:
    """
    Fast path: one matrix product gives every pairwise common-neighbour count.

    M[a, b] is 1 when neighbours a and b of the ego are themselves adjacent.
    Then (M @ M.T)[a, b] counts their common neighbours INSIDE the ego network,
    which is exactly the sigma_jk the formula needs.

    net.adj.indices is sorted per row (preprocessing calls sort_indices), so
    membership tests are searchsorted rather than hashing.
    """
    M = np.zeros((k, k), dtype=np.int32)
    for a in range(k):
        un = net.nbrs[nb[a]]
        pos = np.searchsorted(nb, un)
        np.clip(pos, 0, k - 1, out=pos)
        M[a, pos[nb[pos] == un]] = 1

    shared = M @ M.T
    iu = np.triu_indices(k, 1)
    # Only NON-adjacent neighbour pairs route through the ego. The +1 is the
    # ego itself, always a common neighbour of any two of its neighbours.
    nonadj = M[iu] == 0
    return float((1.0 / (shared[iu][nonadj] + 1)).sum())


def _ego_betweenness_sets(net: Network, nb: np.ndarray, k: int) -> float:
    """Reference path: the formula written out directly with Python sets."""
    in_ego = set(nb.tolist())
    nb_sets = {u: (set(net.nbrs[u].tolist()) & in_ego) for u in nb.tolist()}

    total = 0.0
    nb_list = nb.tolist()
    for a in range(k):
        u = nb_list[a]
        su = nb_sets[u]
        for b in range(a + 1, k):
            v = nb_list[b]
            if v in su:
                continue  # directly connected -> ego is not on the path
            # Common neighbours of u,v inside the ego net, plus the ego.
            total += 1.0 / (len(su & nb_sets[v]) + 1)
    return total


# ----------------------------------------------------------------------------
# Main extractor
# ----------------------------------------------------------------------------

def extract_features(net: Network,
                     max_hop: int = 3,
                     verbose: bool = True,
                     p_transmission: float | None = None,
                     graphlet_size: int | None = 5,
                     edge_graphlet_size: int | None = 4
                     ) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Build the full local-feature table.

    `p_transmission` enables the `dynamic` tier - a local estimate of the
    cascade itself rather than a structural proxy for it. Leave it None and
    those columns are simply absent, which is the right default for any
    analysis that must not assume the observer knows the spreading rate.

    `graphlet_size` enables the node graphlet orbit columns (4 or 5); None
    disables them. `edge_graphlet_size` does the same for edge orbits, which
    are aggregated over each node's incident edges and land in the edge tier.
    Both are skipped automatically, with a message, if the ORCA binary is not
    built - the rest of the pipeline does not depend on either.

    The defaults are 5-node node orbits and 4-node edge orbits. 5-node EDGE
    orbits are supported by the counter but not defaulted on: 68 orbits times
    three summary statistics is 204 columns, which is disproportionate against
    everything measured so far about how little most orbit columns contribute,
    and would roughly triple sweep time.

    Returns
    -------
    features : DataFrame, one row per node, one column per feature
    registry : DataFrame of feature metadata (name, hop, tier, description)
    timings  : dict of wall-clock seconds per feature group

    The timings are not decoration. The whole point of the depth-vs-richness
    experiment is to compare accuracy against COST, so we have to measure cost
    while we compute - it cannot be reconstructed afterwards.
    """
    reg = FeatureRegistry()
    timings: dict[str, float] = {}
    cols: dict[str, np.ndarray] = {}

    def timed(group: str):
        """Small context-manager-ish helper for recording group cost."""
        class _T:
            def __enter__(self_):
                self_.t0 = time.perf_counter(); return self_
            def __exit__(self_, *a):
                timings[group] = time.perf_counter() - self_.t0
                if verbose:
                    print(f"    {group:24s} {timings[group]:7.2f}s")
        return _T()

    if verbose:
        print(f"  extracting features for {net.name} (n={net.n:,})")

    # ---------------- hop 0: the node itself ----------------------------
    with timed("hop0_node"):
        cols["degree"] = net.degree.astype(np.float64)
        reg.add("degree", 0, "node", "number of direct neighbours",
                "hop0_node")

        # Degree divided by (n-1). Note this uses n, which is a global constant
        # rather than global STRUCTURE - it is a rescaling, not information
        # about anyone else's connections. Kept because it makes the feature
        # comparable across networks of different sizes.
        cols["degree_normalized"] = net.degree / max(net.n - 1, 1)
        reg.add("degree_normalized", 0, "node", "degree / (n-1)", "hop0_node")

    # ---------------- hop 1: ego network ---------------------------------
    with timed("hop1_ego"):
        tri = np.zeros(net.n, dtype=np.float64)
        ego_edges = np.zeros(net.n, dtype=np.float64)
        ego_density = np.zeros(net.n, dtype=np.float64)
        clustering = np.zeros(net.n, dtype=np.float64)
        edges_out = np.zeros(net.n, dtype=np.float64)
        eff_size = np.zeros(net.n, dtype=np.float64)

        # Per-EDGE structure, kept rather than discarded. The intersection
        # below already computes the embeddedness of edge (i,u); the previous
        # version summed it into a triangle count and threw the distribution
        # away. That distribution is the only genuinely edge-level information
        # available at radius 1 - see the note on the edge tier below.
        emb_agg: dict[str, list] = {}
        ovl_agg: dict[str, list] = {}
        entropy = np.zeros(net.n, dtype=np.float64)
        entropy_norm = np.zeros(net.n, dtype=np.float64)

        for i in range(net.n):
            nb = net.nbrs[i]
            k = len(nb)
            if k == 0:
                for acc, pref in ((emb_agg, "edge_embeddedness"),
                                  (ovl_agg, "edge_overlap")):
                    row: dict[str, float] = {}
                    _stats(np.empty(0), pref, row, ("mean", "max", "min", "std"))
                    for kk, vv in row.items():
                        acc.setdefault(kk, []).append(vv)
                continue
            in_ego = set(nb.tolist())

            # Count edges among the neighbours. Each such edge is a triangle
            # through i, so triangles and ego-internal edges are the same
            # count - we keep both names because they are conventionally
            # reported differently.
            internal = 0
            outward = 0
            emb = np.empty(k, dtype=np.float64)
            for idx, u in enumerate(nb.tolist()):
                un = net.nbrs[u]
                shared = len(in_ego.intersection(un.tolist()))
                emb[idx] = shared
                internal += shared
                # Edges from u leaving the ego network entirely (excluding the
                # edge back to i itself).
                outward += len(un) - shared - 1
            internal //= 2  # each internal edge counted from both endpoints

            # Onnela neighbourhood overlap of each incident edge:
            #   O(i,u) = n_iu / ((k_i - 1) + (k_u - 1) - n_iu)
            # the fraction of the two endpoints' combined neighbourhood that
            # they share. Low overlap marks a bridge, high marks an embedded
            # tie - the strong/weak tie distinction, per edge.
            du = net.degree[nb].astype(np.float64)
            denom = (k - 1) + (du - 1) - emb
            ovl = _safe_div(emb, denom)

            # NOTE the deliberate omission of 'sum'. Summing embeddedness over
            # incident edges gives exactly 2 x triangle_count, which we already
            # have - it would be a derived column, and this feature set has
            # enough of those. The mean/max/min/std describe the SHAPE of the
            # distribution, which nothing else does.
            for acc, vals, pref in ((emb_agg, emb, "edge_embeddedness"),
                                    (ovl_agg, ovl, "edge_overlap")):
                row = {}
                _stats(vals, pref, row, ("mean", "max", "min", "std"))
                for kk, vv in row.items():
                    acc.setdefault(kk, []).append(vv)

            # Local structure entropy: Shannon entropy of the neighbour-degree
            # distribution. Captures the SHAPE of local heterogeneity, which a
            # standard deviation does not - one dominant neighbour among many
            # small ones reads very differently from an even spread, at equal
            # variance.
            tot = du.sum()
            if tot > 0:
                pk = du / tot
                nz = pk[pk > 0]
                h = float(-(nz * np.log(nz)).sum())
                entropy[i] = h
                # Raw entropy grows like log(k), which is degree information we
                # already hold. Dividing it out isolates the part that is about
                # shape alone.
                entropy_norm[i] = h / np.log(k) if k > 1 else 0.0

            tri[i] = internal
            ego_edges[i] = internal + k          # + the k spokes from ego
            possible = k * (k - 1) / 2
            clustering[i] = internal / possible if possible > 0 else 0.0
            # Density of the whole ego net including the ego and its spokes.
            tot_possible = (k + 1) * k / 2
            ego_density[i] = ego_edges[i] / tot_possible if tot_possible > 0 else 0.0
            edges_out[i] = outward
            # Burt's effective size: neighbours minus average redundancy.
            eff_size[i] = k - (2 * internal / k) if k > 0 else 0.0

        cols["triangle_count"] = tri
        reg.add("triangle_count", 1, "subgraph", "triangles through the node",
                "hop1_ego")
        cols["clustering_coefficient"] = clustering
        reg.add("clustering_coefficient", 1, "node",
                "fraction of neighbour pairs that are connected", "hop1_ego")
        cols["ego_net_size"] = net.degree + 1.0
        reg.add("ego_net_size", 1, "node", "nodes in the ego network",
                "hop1_ego")
        cols["ego_net_edges"] = ego_edges
        reg.add("ego_net_edges", 1, "edge", "edges inside the ego network",
                "hop1_ego")
        cols["ego_net_density"] = ego_density
        reg.add("ego_net_density", 1, "edge", "ego-net edges / possible edges",
                "hop1_ego")
        cols["edges_leaving_ego"] = edges_out
        reg.add("edges_leaving_ego", 1, "edge",
                "edges from neighbours to nodes outside the ego net",
                "hop1_ego")
        cols["effective_size"] = eff_size
        reg.add("effective_size", 1, "node",
                "Burt effective size: non-redundant contacts", "hop1_ego")
        # Boundary porosity: what fraction of the ego net's edge endpoints
        # point outward. This is the key self-assessment signal - a node cannot
        # see past its boundary but CAN see how leaky that boundary is.
        denom = ego_edges + edges_out
        cols["boundary_porosity"] = _safe_div(edges_out, denom)
        reg.add("boundary_porosity", 1, "edge",
                "outward edges / all ego-net edge endpoints", "hop1_ego")

        # --- a real edge tier ------------------------------------------------
        # Every edge feature above is an exact algebraic function of node-tier
        # features (see analyse_features.py, which checks this automatically):
        #   ego_net_edges     = clustering * k(k-1)/2 + k
        #   edges_leaving_ego = nbr_degree_sum - 2*triangle_count - k
        # and so on. They therefore add zero information over the node tier,
        # which is why the depth-vs-richness result showed no gain from the
        # edge tier - the axis was not actually varying.
        #
        # These two DO vary it. They describe the distribution of structure
        # across a node's incident edges rather than one aggregate over the
        # ego net, and no combination of node-level columns recovers a
        # distribution's shape from its total.
        for acc in (emb_agg, ovl_agg):
            for nm, vals in acc.items():
                cols[nm] = np.asarray(vals, dtype=np.float64)
                what = ("common neighbours on an incident edge"
                        if nm.startswith("edge_embeddedness")
                        else "Onnela neighbourhood overlap of an incident edge")
                reg.add(nm, 1, "edge", f"{what}, summarised over edges",
                        "hop1_ego")

        cols["local_entropy"] = entropy
        reg.add("local_entropy", 1, "node",
                "Shannon entropy of the neighbour-degree distribution",
                "hop1_ego")
        cols["local_entropy_norm"] = entropy_norm
        reg.add("local_entropy_norm", 1, "node",
                "local entropy divided by log(degree): heterogeneity shape "
                "with the degree scale removed", "hop1_ego")

    # ---------------- neighbour aggregates --------------------------------
    # These are summaries of a per-node quantity over a node's neighbours.
    # They are split into TWO groups because they do not all cost the same
    # radius, and they used to be tagged as though they did.
    #
    # WHAT THE HOP TAG MEANS HERE
    # ---------------------------
    # Our convention throughout is structural: at radius r you know which
    # nodes lie within r hops, the edges among them, and the degrees of the
    # nodes on the boundary. That is what makes h_index_1, CI_1 and
    # edges_leaving_ego legitimately hop 1 - each needs neighbours' degrees
    # and nothing more.
    #
    # Neighbour DEGREE aggregates fit that budget exactly: hop 1.
    #
    # Neighbour CLUSTERING and TRIANGLE aggregates do not. Clustering of a
    # neighbour j is decided by the edges among j's neighbours, and those
    # nodes sit at distance 2 from us. Edges *between* two distance-2 nodes
    # are simply not inside a 1-ball, so these are hop-2 features.
    #
    # They were previously tagged hop 1. That inflated P(1), depressed the
    # measured r1->r2 gain, and therefore biased r* downward - on the exact
    # column where the headline saturation claims live. The alternative
    # reading, "a neighbour can just tell us its clustering coefficient",
    # is one this project already rejects elsewhere: under it
    # shell_2_degree_mean would be hop 1 too, and it is tagged hop 2.
    def _aggregate(source: np.ndarray, prefix: str) -> dict[str, np.ndarray]:
        """Summarise a per-node quantity over each node's neighbours."""
        acc: dict[str, list] = {}
        for i in range(net.n):
            row: dict[str, float] = {}
            _stats(source[net.nbrs[i]], prefix, row)
            for kk, vv in row.items():
                acc.setdefault(kk, []).append(vv)
        return {kk: np.asarray(vv, dtype=np.float64) for kk, vv in acc.items()}

    with timed("hop1_neighbor_degree_agg"):
        for kk, vv in _aggregate(net.degree.astype(np.float64), "nbr_degree").items():
            cols[kk] = vv
            reg.add(kk, 1, "node", "nbr_degree summarised over neighbours",
                    "hop1_neighbor_degree_agg")

        # Do you connect "up" to more popular people, or "down"?
        cols["assortativity_local"] = (
            cols["nbr_degree_mean"] - cols["degree"]
        )
        reg.add("assortativity_local", 1, "node",
                "mean neighbour degree minus own degree",
                "hop1_neighbor_degree_agg")

    with timed("hop2_neighbor_structure_agg"):
        for src, prefix in ((clustering, "nbr_clustering"), (tri, "nbr_triangles")):
            for kk, vv in _aggregate(src, prefix).items():
                cols[kk] = vv
                reg.add(kk, 2, "node", f"{prefix} summarised over neighbours",
                        "hop2_neighbor_structure_agg")

    # ---------------- ego betweenness (hop 1, brokerage) ------------------
    with timed("hop1_ego_betweenness"):
        cols["ego_betweenness"] = ego_betweenness(net)
        reg.add("ego_betweenness", 1, "subgraph",
                "betweenness of the ego inside its own ego network",
                "hop1_ego_betweenness")

    # ---------------- H-index ladder --------------------------------------
    # Timed PER ORDER, because order n is a hop-n feature.
    ladder, ladder_seconds = h_index_ladder(net, max_order=max_hop)
    for order, vals in enumerate(ladder, start=1):
        nm = f"h_index_{order}"
        cols[nm] = vals.astype(np.float64)
        reg.add(nm, order, "node",
                f"order-{order} H-index (needs info {order} hops away)",
                f"h_index_order_{order}")
        timings[f"h_index_order_{order}"] = ladder_seconds[order - 1]
        if verbose:
            print(f"    {'h_index_order_' + str(order):24s} "
                  f"{ladder_seconds[order - 1]:7.2f}s")

    # ---------------- one traversal, every radius-parameterised feature ----
    # See neighbourhood_pass for why these used to be four separate walks over
    # every neighbourhood, and what that cost.
    P = neighbourhood_pass(net, max_hop, p_transmission=p_transmission)
    shell_counts = P["shell_counts"]
    shell_deg_mean = P["shell_deg_mean"]
    shell_deg_max = P["shell_deg_max"]
    shell_deg_sum = P["shell_deg_sum"]
    ci = P["ci"]
    shell_hop_seconds = P["hop_seconds"]

    for h in range(max_hop):
        timings[f"shells_ci_hop_{h + 1}"] = shell_hop_seconds[h]
        if verbose:
            print(f"    {'shells_ci_hop_' + str(h + 1):24s} "
                  f"{shell_hop_seconds[h]:7.2f}s")

    for h in range(1, max_hop):         # hop-1 count == degree, already have it
        hop = h + 1
        cols[f"shell_{hop}_count"] = shell_counts[:, h]
        reg.add(f"shell_{hop}_count", hop, "node",
                f"nodes at exactly {hop} hops", f"shells_ci_hop_{hop}")
        cols[f"shell_{hop}_degree_mean"] = shell_deg_mean[:, h]
        reg.add(f"shell_{hop}_degree_mean", hop, "node",
                f"mean degree at exactly {hop} hops",
                f"shells_ci_hop_{hop}")
        cols[f"shell_{hop}_degree_max"] = shell_deg_max[:, h]
        reg.add(f"shell_{hop}_degree_max", hop, "node",
                f"max degree at exactly {hop} hops",
                f"shells_ci_hop_{hop}")
        # Growth ratio: how fast the reachable set expands outward. This is
        # a strong spread signal and a boundary-porosity signal at once.
        prev = shell_counts[:, h - 1]
        cols[f"growth_ratio_{hop}"] = _safe_div(shell_counts[:, h], prev)
        reg.add(f"growth_ratio_{hop}", hop, "node",
                f"shell {hop} size / shell {hop-1} size",
                f"shells_ci_hop_{hop}")
        # Cumulative reach within this radius. shell_counts[:, 0] is shell 1,
        # so the sum runs over hops 1..hop and EXCLUDES the node itself; the
        # description used to say "total distinct nodes within {hop} hops",
        # which reads as including it (Task 6 finding P1-11, corrected
        # 2026-09-11 by Claude Opus 5; the computation is unchanged).
        cols[f"reach_within_{hop}"] = shell_counts[:, :h + 1].sum(axis=1)
        reg.add(f"reach_within_{hop}", hop, "node",
                f"distinct nodes at 1..{hop} hops (excludes the node itself)",
                f"shells_ci_hop_{hop}")

    # ---------------- Collective Influence --------------------------------
    # Already computed by the shell pass above - CI_l is just the (k-1)-weighted
    # sum over the shell at distance l, and that shell was in hand. Its cost is
    # therefore folded into shells_ci_hop_*, not charged again here.
    for ell in range(1, max_hop + 1):
        nm = f"collective_influence_{ell}"
        cols[nm] = ci[:, ell - 1]
        reg.add(nm, ell, "node",
                f"Morone-Makse CI at radius {ell}", f"shells_ci_hop_{ell}")

    # ---------------- 2-ball internal structure ---------------------------
    # THE GAP THIS CLOSES. Every other multi-hop feature is a count or a degree
    # summary of a shell; none of them ever looks at the edges AMONG those
    # nodes. So the table could say how many friends-of-friends a node had and
    # how well connected they were, and nothing at all about how they were
    # wired to one another. These do.
    if max_hop >= 2:
        b_edges = P["ball2_edges"]
        b_vol = P["ball2_volume"]
        b_size = 1.0 + shell_counts[:, 0] + shell_counts[:, 1]

        cols["ball2_edges"] = b_edges
        reg.add("ball2_edges", 2, "subgraph",
                "edges with both endpoints inside the 2-ball",
                "shells_ci_hop_2")

        # TIER: subgraph, NOT edge. Corrected 2026-08-31 after a full-project
        # audit; it was tagged `edge` from the day it was written.
        #
        # THE RULE THESE TWO BROKE. The edge tier is defined (study doc 6.4) as
        # "the distribution of structure across a node's INCIDENT edges" -
        # edge_embeddedness and edge_overlap, one value per edge touching the
        # node, summarised. `ball2_density` and `local_conductance_2` are not
        # that. They are single aggregates over the edges AMONG 2-ball members,
        # most of which the node does not touch. That is the subgraph tier's
        # definition, and `ball2_edges` - computed from the very same
        # P["ball2_edges"] array three lines up - was already tagged subgraph.
        # One array, two tiers, is not a defensible split.
        #
        # WHY IT MATTERED RATHER THAN BEING A LABELLING QUIBBLE. The richness
        # ladder is NESTED: node < node+edge < node+edge+subgraph. With these in
        # the edge tier, the `node+edge` rung at r>=2 could reconstruct
        # `ball2_edges` exactly - verified to 5e-12 on ca-GrQc, 3e-11 on email
        # and 3e-10 on facebook, by two independent routes:
        #     ball2_edges = ball2_density * b_size(b_size-1)/2
        #     ball2_edges = (b_vol - local_conductance_2 * b_vol) / 2
        # with b_size and b_vol both recoverable from node-tier columns. So the
        # rung that is supposed to be structure-blind was reading 2-ball
        # structure, which inflates the measured EDGE gain and deflates the
        # measured SUBGRAPH gain at every radius >= 2.
        #
        # This is the same class of defect as the hop-tagging bug that inflated
        # P(1): a feature credited to a budget that could not have computed it.
        possible = b_size * (b_size - 1) / 2.0
        cols["ball2_density"] = _safe_div(b_edges, possible)
        reg.add("ball2_density", 2, "subgraph",
                "2-ball edges / possible 2-ball edges", "shells_ci_hop_2")

        # Conductance of the 2-ball: what fraction of its edge endpoints point
        # out of it. The standard local approximation cut / vol(S), valid while
        # the ball is the smaller side - which it is except on dense graphs
        # where the 2-ball swallows most of the network, and that case is
        # itself informative.
        # TIER: subgraph, NOT edge - see the note on ball2_density above. This
        # is the column that made the mis-tagging consequential rather than
        # cosmetic: study doc 26a's Finding 10 was written as "the edge tier is
        # not a null" on the strength of +0.1478 tau on facebook betweenness,
        # and this feature carries nearly all of it. Refitting after the retag
        # (2026-08-31) splits that number across the two rungs: the edge tier
        # buys +0.0318 and the subgraph tier +0.1291. So the headline was an
        # artefact of the tag, not a property of the edge tier, and 26a now
        # says the subgraph tier carries it.
        #
        # The PREDICTION stands: a bridge detector really is worth +0.117 tau on
        # a union of ego networks. What does NOT stand is the orthogonality
        # sentence that used to sit here - "held-out R^2 = -0.88 against the
        # node tier". That does not reproduce; the measured value is about
        # +0.99, by two estimators and two CV protocols. This column is very
        # nearly reconstructible from the tiers below it and is still worth
        # +0.117 tau, because a forest fitting BETWEENNESS does not
        # spontaneously form the ratio cut/vol. Reconstructible is not the same
        # as accessible - do not restate the old number.
        cut = b_vol - 2.0 * b_edges
        cols["local_conductance_2"] = _safe_div(cut, b_vol)
        reg.add("local_conductance_2", 2, "subgraph",
                "2-ball cut size / 2-ball degree volume", "shells_ci_hop_2")

    # ---------------- Local Gravity Model ---------------------------------
    # LGM_R(i) = sum over j with 1 <= d(i,j) <= R of k_i * k_j / d(i,j)^2
    # A distance-WEIGHTED mass, where CI and the shell columns treat each shell
    # as an independent quantity. Registered honestly as a literature baseline:
    # it is a nonlinear recombination of columns already present, so it adds a
    # transform rather than information. Included so the claim can be tested
    # rather than assumed - see analyse_features.py.
    grav = np.zeros(net.n, dtype=np.float64)
    for ell in range(1, max_hop + 1):
        grav = grav + shell_deg_sum[:, ell - 1] / float(ell ** 2)
        nm = f"local_gravity_{ell}"
        cols[nm] = net.degree.astype(np.float64) * grav
        reg.add(nm, ell, "node",
                f"local gravity model truncated at radius {ell}",
                f"shells_ci_hop_{ell}")

    # ---------------- ClusterRank -----------------------------------------
    # Degree mass discounted by clustering: a node whose neighbours all know
    # each other reaches fewer distinct people per edge. Also a recombination
    # of existing columns, and also included to be tested rather than assumed.
    with timed("hop1_clusterrank"):
        cols["cluster_rank"] = (
            np.power(10.0, -cols["clustering_coefficient"])
            * (cols["nbr_degree_sum"] + net.degree))
        reg.add("cluster_rank", 1, "node",
                "Chen ClusterRank: 10^-C(i) * sum of (k_j + 1) over neighbours",
                "hop1_clusterrank")

    # ---------------- semi-local centrality -------------------------------
    # SLC(i) = sum over neighbours j of |2-ball(j)|. Genuinely hop 3: it needs
    # the 2-ball of a node one step away, which reaches distance 3. Nothing
    # else in the table aggregates REACH over neighbours - the neighbour
    # aggregates only ever summarised degree, clustering and triangles.
    if max_hop >= 3:
        with timed("hop3_semilocal"):
            reach2 = 1.0 + shell_counts[:, 0] + shell_counts[:, 1]
            slc = np.empty(net.n, dtype=np.float64)
            nbr_reach_mean = np.empty(net.n, dtype=np.float64)
            for i in range(net.n):
                nb = net.nbrs[i]
                if len(nb):
                    v = reach2[nb]
                    slc[i] = v.sum()
                    nbr_reach_mean[i] = v.mean()
                else:
                    slc[i] = 0.0
                    nbr_reach_mean[i] = 0.0
            cols["semilocal_centrality"] = slc
            reg.add("semilocal_centrality", 3, "node",
                    "Chen semi-local centrality: sum over neighbours of their "
                    "2-ball size", "hop3_semilocal")
            cols["nbr_reach2_mean"] = nbr_reach_mean
            reg.add("nbr_reach2_mean", 3, "node",
                    "mean 2-ball size over neighbours", "hop3_semilocal")

    # ---------------- truncated local percolation -------------------------
    # The one MECHANISTIC family: a local estimate of the very quantity being
    # predicted, rather than a generic structural proxy. See neighbourhood_pass
    # for the approximation and for why using p is a modelling assumption
    # rather than leakage.
    #
    # Its own tier, so it can be included or excluded as a block. Any result
    # that uses it assumes the observer knows the transmission rate, and that
    # assumption should never be buried inside a general "richness" claim.
    if P["perc"] is not None:
        # Starting at radius 2 deliberately. At radius 1 the estimate is
        # 1 + p*k, a linear function of degree and therefore rank-identical to
        # it - a pure duplicate column. The mechanistic estimate only starts
        # carrying anything of its own once a second layer exists for the
        # message passing to combine.
        for ell in range(2, max_hop + 1):
            nm = f"perc_reach_{ell}"
            cols[nm] = P["perc"][:, ell - 1]
            reg.add(nm, ell, "dynamic",
                    f"expected cascade size within {ell} hops under the "
                    f"independent-path approximation at p={p_transmission:g}",
                    f"shells_ci_hop_{ell}")

    # ---------------- graphlet orbits -------------------------------------
    # The fair test of the subgraph tier. Orbits are tagged with the radius
    # each genuinely needs - the eccentricity of the node within its graphlet -
    # so they distribute across the ladder instead of arriving as one block at
    # the deepest rung. See influence/graphlets.py for the derivation.
    #
    # COST DOES NOT DECOMPOSE BY RADIUS HERE, and that is worth being explicit
    # about. The BFS shells can be charged per level because each level is
    # produced by a separate expansion. ORCA solves one system of equations for
    # all fifteen orbits at once, so there is no cheaper run that returns only
    # the hop-1 orbits. Any cell using any orbit pays for all of them, which is
    # why they share a single cost group rather than one per hop.
    if graphlet_size:
        orbits = None
        try:
            from .graphlets import count_node_orbits, orbit_columns
            with timed("graphlet_orbits"):
                orbits = count_node_orbits(net, graphlet_size)
        except Exception as exc:                       # noqa: BLE001
            if verbose:
                print(f"    graphlet orbits skipped: {exc}")
            timings.pop("graphlet_orbits", None)
        if orbits is not None:
            for nm, vals, hop in orbit_columns(orbits):
                cols[nm] = vals
                reg.add(nm, hop, "subgraph",
                        f"graphlet orbit count ({nm.split('_', 2)[2]})",
                        "graphlet_orbits")
        elif verbose:
            print("    graphlet orbits skipped: no orca binary found")

    # ---------------- edge orbits -----------------------------------------
    # An edge orbit is a position an EDGE occupies in a graphlet - a different
    # decomposition from the node orbits and not recoverable from them. Summarised
    # over each node's incident edges they become node features, and they land in
    # the EDGE tier because that is the object they describe.
    #
    # `sum` is excluded from the summary: summing an edge-orbit count over a
    # node's incident edges counts each graphlet once per incident edge, which
    # for several orbits is an exact multiple of a node-orbit count already
    # present. Mean, max and spread describe the distribution across a node's
    # edges, which nothing else in the table does.
    if edge_graphlet_size:
        try:
            from .graphlets import (count_edge_orbits, edge_orbit_node_features,
                                    edge_orbit_columns)
            with timed("edge_orbits"):
                eu, ev, eorb = count_edge_orbits(net, edge_graphlet_size)
                per_stat = (edge_orbit_node_features(net, eu, ev, eorb)
                            if eorb is not None else None)
            if per_stat is not None:
                for nm, vals, hop in edge_orbit_columns(per_stat):
                    cols[nm] = vals
                    reg.add(nm, hop, "edge",
                            f"edge-orbit count summarised over incident edges "
                            f"({nm.split('_', 1)[1]})", "edge_orbits")
            else:
                timings.pop("edge_orbits", None)
                if verbose:
                    print("    edge orbits skipped: no orca binary found")
        except Exception as exc:                       # noqa: BLE001
            timings.pop("edge_orbits", None)
            if verbose:
                print(f"    edge orbits skipped: {exc}")

    features = pd.DataFrame(cols)
    features.insert(0, "node", np.arange(net.n))
    features.insert(1, "original_id", net.original_ids)

    return features, reg.to_frame(), timings


# ----------------------------------------------------------------------------
# Radius / tier filtering - the sweep is a filter, not a rewrite
# ----------------------------------------------------------------------------

def select_features(features: pd.DataFrame,
                    registry: pd.DataFrame,
                    max_hop: int | None = None,
                    tiers: tuple[str, ...] | None = None) -> list[str]:
    """
    Column names an observer restricted to `max_hop` and `tiers` could compute.

    This single function is what makes the two-dimensional locality budget
    experiment cheap: every cell of the (radius x richness) grid is one call
    to this, then one model fit.
    """
    sel = registry
    if max_hop is not None:
        sel = sel[sel["hop"] <= max_hop]
    if tiers is not None:
        sel = sel[sel["tier"].isin(tiers)]
    return [c for c in sel["feature"].tolist() if c in features.columns]

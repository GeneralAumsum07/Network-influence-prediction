"""
dynamics.py
===========
Spreading simulators. These produce the GROUND TRUTH the whole project is
graded against, so correctness matters more here than anywhere else.

WHAT WE COMPUTE
---------------
For every node i, the distribution of |R(i)| - the number of nodes eventually
reached when i alone is the seed. We keep the FULL distribution, not just the
mean, for two reasons:

  1. The mean is the standard influence target.
  2. The variance is its own target (some seeds are reliable, some are
     lottery tickets), and it cannot be recovered later if we throw the
     samples away. Re-running is expensive; storing is cheap.

THE PERCOLATION SHORTCUT
------------------------
Naively you simulate M cascades from each of n seeds: O(n*M) cascades.

But Independent Cascade with a fixed per-edge probability is EXACTLY bond
percolation. Each edge either transmits or does not, independently, and that
draw does not depend on who is seeding. So we can:

    - sample ONE live-edge subgraph
    - find its connected components
    - every node's reached set for that sample IS its component

which gives one sample for ALL n seeds simultaneously. M percolation runs
instead of n*M cascades - a speedup of roughly n.

This shortcut is exact for symmetric edge probabilities (uniform, trivalency).
It does NOT hold for the weighted-cascade convention, where the probability
depends on the receiving node's degree and the edge is therefore asymmetric.
We implement both paths and verify they agree where both are valid.

EDGE PROBABILITY CONVENTIONS
----------------------------
The convention silently changes the results, so it is an explicit parameter
and never a default buried in the code:

  'uniform'   : p on every edge. Simplest; inflates hub influence.
  'weighted'  : p_uv = 1/degree(v). Normalises each node's incoming pressure.
  'trivalency': p drawn per edge from {0.001, 0.01, 0.1}.

We report under at least two of these. SIR with a rate beta is a fourth
convention that does not map exactly onto any of them.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from .preprocessing import Network


# ----------------------------------------------------------------------------
# Result container
# ----------------------------------------------------------------------------

@dataclass
class CascadeResults:
    """
    Full simulation output.

    sizes : (n, M) int array. sizes[i, m] is the number of nodes reached in
            simulation m when i was the seed. This is the raw material for
            both the mean-influence target and the volatility target.

    n_nodes : size of the NETWORK, which is not the same thing as
            sizes.shape[0]. When seeds are subsampled - which the direct
            simulators support and which is the only practical option on a
            large graph - sizes has one row per sampled seed, not one per
            node. ignition_probability needs the network size to turn a
            fraction into a node count, and reading it off sizes.shape[0]
            silently rescaled the threshold to the sample. Storing it
            explicitly removes the trap.
    """
    sizes: np.ndarray
    model: str
    convention: str
    p: float
    n_sims: int
    n_nodes: int

    @property
    def mean(self) -> np.ndarray:
        """Expected spread - the standard influence target."""
        return self.sizes.mean(axis=1)

    @property
    def std(self) -> np.ndarray:
        return self.sizes.std(axis=1, ddof=1)

    @property
    def stderr(self) -> np.ndarray:
        """
        Standard error of the mean estimate: s / sqrt(M).

        This is how we decide whether M was large enough. The rule: the
        typical standard error must be well below the spread BETWEEN nodes,
        otherwise we are ranking simulation noise rather than real differences.
        """
        return self.std / np.sqrt(self.n_sims)

    @property
    def cv(self) -> np.ndarray:
        """
        Coefficient of variation = sd / mean.

        Scale-free measure of volatility. A steady broadcaster has low CV; a
        node that usually fizzles but occasionally ignites has high CV.
        """
        m = self.mean
        return np.where(m > 0, self.std / np.maximum(m, 1e-12), 0.0)

    def ignition_probability(self, threshold_frac: float = 0.05) -> np.ndarray:
        """
        Fraction of runs where the cascade exceeded threshold_frac * n.

        The threshold is a fraction of the NETWORK, so it uses n_nodes rather
        than the number of rows in `sizes` - see the note on n_nodes above.
        """
        thresh = threshold_frac * self.n_nodes
        return (self.sizes > thresh).mean(axis=1)

    def noise_report(self) -> str:
        """Is M large enough? Print this before trusting any result."""
        se = self.stderr
        between = self.mean.std()
        ratio = np.median(se) / between if between > 0 else np.inf
        verdict = "OK" if ratio < 0.1 else "TOO NOISY - raise M"
        return (f"  median standard error : {np.median(se):.3f}\n"
                f"  between-node spread   : {between:.3f}\n"
                f"  ratio (want << 1)     : {ratio:.4f}  [{verdict}]")


# ----------------------------------------------------------------------------
# Edge probability assignment
# ----------------------------------------------------------------------------

TRIVALENCY_CHOICES = np.array([0.001, 0.01, 0.1])


def symmetric_edge_probabilities(net: Network, convention: str, p: float,
                                 rng: np.random.Generator):
    """
    One probability per UNDIRECTED edge, plus the edge list it is aligned to.

    THE SINGLE SOURCE OF TRUTH FOR SYMMETRIC CONVENTIONS
    ----------------------------------------------------
    The percolation path and the direct path used to draw trivalency
    probabilities independently - the fast path drew once per upper-triangle
    edge, the slow path drew once per unique edge key and mirrored. Both were
    individually correct, but they consumed the random stream differently, so
    the same seed produced DIFFERENT graphs on the two paths. That quietly
    destroys the ability to verify one against the other under trivalency,
    which is the whole reason both paths exist.

    Everything symmetric now goes through here, so the two paths cannot
    disagree.

    Returns (eu, ev, per_edge_p) with eu < ev elementwise.
    """
    coo = sp.triu(net.adj, k=1).tocoo()
    eu, ev = coo.row, coo.col

    if convention == "uniform":
        return eu, ev, np.full(len(eu), p, dtype=np.float64)

    if convention == "trivalency":
        return eu, ev, rng.choice(TRIVALENCY_CHOICES, size=len(eu))

    raise ValueError(f"{convention} is not a symmetric convention")


def edge_probabilities(net: Network, convention: str, p: float,
                       rng: np.random.Generator) -> np.ndarray:
    """
    Probability for each directed arc, aligned with net.adj.indices.

    Returned array is parallel to the CSR structure: entry j corresponds to
    the arc from the row-owner to net.adj.indices[j]. For symmetric
    conventions the two directions of an edge carry the same value.
    """
    n_arcs = net.adj.nnz

    if convention == "uniform":
        return np.full(n_arcs, p, dtype=np.float64)

    if convention == "weighted":
        # p_uv = 1 / degree(v): the RECEIVER's degree. Each node's total
        # incoming pressure sums to about 1 regardless of how popular it is.
        return 1.0 / net.degree[net.adj.indices].astype(np.float64)

    if convention == "trivalency":
        # Draw once per undirected edge via the shared helper, then mirror onto
        # both arcs so the edge stays symmetric.
        eu, ev, per_edge = symmetric_edge_probabilities(net, convention, p, rng)
        edge_key = eu.astype(np.int64) * net.n + ev.astype(np.int64)
        order = np.argsort(edge_key)
        edge_key, per_edge = edge_key[order], per_edge[order]

        rows = np.repeat(np.arange(net.n), np.diff(net.adj.indptr))
        cols = net.adj.indices
        lo = np.minimum(rows, cols).astype(np.int64)
        hi = np.maximum(rows, cols).astype(np.int64)
        arc_key = lo * net.n + hi
        return per_edge[np.searchsorted(edge_key, arc_key)]

    raise ValueError(f"unknown convention: {convention}")


def is_symmetric_convention(convention: str) -> bool:
    """Can we use the fast percolation path?"""
    return convention in ("uniform", "trivalency")


# ----------------------------------------------------------------------------
# Fast path: bond percolation (all seeds at once)
# ----------------------------------------------------------------------------

def simulate_ic_percolation(net: Network, p: float = 0.05,
                            n_sims: int = 200,
                            convention: str = "uniform",
                            seed: int = 0,
                            verbose: bool = True) -> CascadeResults:
    """
    Independent Cascade via bond percolation.

    Each run: keep every edge independently with its probability, find the
    connected components of what survives, and record each node's component
    size as its reached-set size for that run.

    Exact for symmetric conventions. One run yields a sample for every seed.
    """
    if not is_symmetric_convention(convention):
        raise ValueError(f"{convention} is asymmetric; use simulate_ic_direct")

    rng = np.random.default_rng(seed)
    sizes = np.empty((net.n, n_sims), dtype=np.int32)

    # Upper-triangle edge list: each undirected edge appears exactly once, so
    # we make exactly one keep/drop decision per edge. The probabilities come
    # from the shared helper so this path and simulate_ic_direct cannot draw
    # different graphs from the same seed.
    eu, ev, edge_p = symmetric_edge_probabilities(net, convention, p, rng)
    n_edges = len(eu)

    for m in range(n_sims):
        live = rng.random(n_edges) < edge_p
        g = sp.csr_matrix(
            (np.ones(live.sum(), dtype=np.int8), (eu[live], ev[live])),
            shape=(net.n, net.n))
        n_comp, labels = sp.csgraph.connected_components(g, directed=False)
        comp_sizes = np.bincount(labels, minlength=n_comp)
        sizes[:, m] = comp_sizes[labels]

        if verbose and (m + 1) % max(1, n_sims // 5) == 0:
            print(f"    percolation run {m+1}/{n_sims}")

    return CascadeResults(sizes=sizes, model="IC", convention=convention,
                          p=p, n_sims=n_sims, n_nodes=net.n)


# ----------------------------------------------------------------------------
# General path: direct per-seed simulation
# ----------------------------------------------------------------------------

def _one_cascade(net: Network, seed_node: int, arc_p: np.ndarray,
                 rng: np.random.Generator) -> int:
    """
    One Independent Cascade run from a single seed. Returns nodes reached.

    Follows the IC rules exactly:
      - a node that becomes active gets ONE attempt on each inactive neighbour
      - the attempt succeeds with the arc's probability
      - success or failure, that attempt is never repeated
      - newly activated nodes act in the next round
    """
    active = np.zeros(net.n, dtype=bool)
    active[seed_node] = True
    frontier = np.array([seed_node], dtype=np.int64)
    total = 1

    indptr, indices = net.adj.indptr, net.adj.indices

    while len(frontier):
        # Gather every arc leaving the frontier in one shot.
        starts = indptr[frontier]
        ends = indptr[frontier + 1]
        counts = ends - starts
        if counts.sum() == 0:
            break
        arc_idx = np.concatenate(
            [np.arange(s, e) for s, e in zip(starts, ends)])
        targets = indices[arc_idx]

        # One coin flip per attempt.
        success = rng.random(len(arc_idx)) < arc_p[arc_idx]
        cand = targets[success]
        if len(cand) == 0:
            break
        cand = np.unique(cand)
        cand = cand[~active[cand]]
        if len(cand) == 0:
            break

        active[cand] = True
        total += len(cand)
        frontier = cand

    return total


def simulate_ic_direct(net: Network, p: float = 0.05, n_sims: int = 200,
                       convention: str = "uniform", seed: int = 0,
                       nodes: np.ndarray | None = None,
                       verbose: bool = True) -> CascadeResults:
    """
    Per-seed Independent Cascade. Works for ANY convention, including the
    asymmetric weighted-cascade rule. Slower than percolation by roughly a
    factor of n, so use it when the convention demands it or to verify the
    fast path.

    THE DEFAULT MATCHES simulate_ic_percolation DELIBERATELY.
    ---------------------------------------------------------
    This defaulted to 'weighted' while the percolation path defaulted to
    'uniform'. Both are documented as computing the same quantity, and the
    stated use for this function is "to verify the fast path" - so the one
    call it exists to serve was, by default, comparing two different models
    and would have reported a disagreement that was pure convention mismatch.
    Every caller in the repository passes `convention` explicitly, so nothing
    depended on the old default; it was a trap laid for the next caller rather
    than an active bug. Callers wanting the asymmetric rule must now ask for it
    by name, which is the right way round: the convention that cannot be run
    through percolation should be the one you have to type.
    """
    rng = np.random.default_rng(seed)
    arc_p = edge_probabilities(net, convention, p, rng)

    targets = np.arange(net.n) if nodes is None else np.asarray(nodes)
    sizes = np.empty((len(targets), n_sims), dtype=np.int32)

    for idx, i in enumerate(targets):
        for m in range(n_sims):
            sizes[idx, m] = _one_cascade(net, int(i), arc_p, rng)
        if verbose and (idx + 1) % max(1, len(targets) // 10) == 0:
            print(f"    seed {idx+1}/{len(targets)}")

    return CascadeResults(sizes=sizes, model="IC", convention=convention,
                          p=p, n_sims=n_sims, n_nodes=net.n)


# ----------------------------------------------------------------------------
# SIR
# ----------------------------------------------------------------------------

def _one_sir(net: Network, seed_node: int, beta: float, mu: float,
             rng: np.random.Generator) -> int:
    """
    One discrete-time SIR run. Returns the final recovered-set size.

    Each timestep: every infected node attempts to infect each susceptible
    neighbour with probability beta, then recovers with probability mu.

    Note mu = 1 makes SIR collapse exactly onto Independent Cascade - each
    node is infectious for exactly one step, so it gets exactly one attempt
    per neighbour. We use that equivalence as a correctness test.
    """
    SUSCEPTIBLE, INFECTED, RECOVERED = 0, 1, 2
    state = np.zeros(net.n, dtype=np.int8)
    state[seed_node] = INFECTED
    infected = [seed_node]
    total = 1

    while infected:
        new_infected = []
        for u in infected:
            nb = net.nbrs[u]
            sus = nb[state[nb] == SUSCEPTIBLE]
            if len(sus):
                hit = sus[rng.random(len(sus)) < beta]
                for v in hit:
                    if state[v] == SUSCEPTIBLE:
                        state[v] = INFECTED
                        new_infected.append(int(v))
                        total += 1
        # Recovery happens after transmission attempts for this step.
        for u in infected:
            if rng.random() < mu:
                state[u] = RECOVERED
        still = [u for u in infected if state[u] == INFECTED]
        infected = still + new_infected

    return total


def simulate_sir(net: Network, beta: float = 0.05, mu: float = 1.0,
                 n_sims: int = 200, seed: int = 0,
                 nodes: np.ndarray | None = None,
                 verbose: bool = True) -> CascadeResults:
    """
    SIR ground truth. beta is the per-contact transmission probability,
    mu the per-step recovery probability.
    """
    rng = np.random.default_rng(seed)
    targets = np.arange(net.n) if nodes is None else np.asarray(nodes)
    sizes = np.empty((len(targets), n_sims), dtype=np.int32)

    for idx, i in enumerate(targets):
        for m in range(n_sims):
            sizes[idx, m] = _one_sir(net, int(i), beta, mu, rng)
        if verbose and (idx + 1) % max(1, len(targets) // 10) == 0:
            print(f"    seed {idx+1}/{len(targets)}")

    return CascadeResults(sizes=sizes, model=f"SIR(mu={mu})",
                          convention="uniform", p=beta, n_sims=n_sims,
                          n_nodes=net.n)


# ----------------------------------------------------------------------------
# Choosing p - the tipping point sweep
# ----------------------------------------------------------------------------

def sweep_transmission(net: Network, p_values: np.ndarray,
                       n_sims: int = 60, convention: str = "uniform",
                       seed: int = 0) -> "pd.DataFrame":
    """
    Find the transmission probability that makes seeds most DISTINGUISHABLE.

    Why this matters: if p is too high, every seed reaches nearly everyone and
    all scores collapse together. If p is too low, nothing spreads and all
    scores are ~1. Either way there is nothing for a model to learn. We want
    the regime where seeds genuinely differ - which is near the critical
    tipping point.

    We pick p by MEASURING where the between-node spread of influence peaks,
    rather than assuming any particular value.
    """
    import pandas as pd

    rows = []
    for p in p_values:
        res = simulate_ic_percolation(net, p=p, n_sims=n_sims,
                                      convention=convention, seed=seed,
                                      verbose=False)
        mean = res.mean
        rows.append({
            "p": float(p),
            "mean_spread": float(mean.mean()),
            "mean_spread_frac": float(mean.mean() / net.n),
            # Dispersion across nodes: this is the quantity we maximise.
            "between_node_std": float(mean.std()),
            "between_node_cv": float(mean.std() / mean.mean()) if mean.mean() > 0 else 0.0,
            "median_stderr": float(np.median(res.stderr)),
        })
    return pd.DataFrame(rows)

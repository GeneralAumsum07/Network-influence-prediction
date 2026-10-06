"""
generators.py
=============
Synthetic network generators - the structural control arm.

WHY THIS MODULE EXISTS
----------------------
Everything measured so far comes from three real networks. That gives us
Finding 4 ("the locality horizon is a property of the network, not a
constant") as an OBSERVATION on three points, which is an anecdote, not a
result.

The problem with real networks is that you cannot turn one knob at a time.
ca-GrQc differs from email-Eu-core in density AND degree tail AND clustering
AND assortativity all at once, so when r* differs we cannot say which
property caused it.

Generators fix that. We build families where exactly one structural
parameter moves and everything else is held fixed, then measure r* across
the family. That converts "the horizon varies" into "the horizon varies
WITH gamma, like this."

THE ONE DISCIPLINE RULE HERE
----------------------------
Every generator returns a Network built through `build_network`, so the six
preprocessing decisions in preprocessing.py apply to synthetic graphs
EXACTLY as they apply to real ones. A synthetic graph that skipped the LCC
restriction, or kept its self-loops, would not be comparable to the real
corpus and would quietly poison any cross-family claim.

This is why no generator here returns a raw networkx object.

WHY networkx RATHER THAN OUR OWN IMPLEMENTATIONS
------------------------------------------------
Elsewhere in this project we implement algorithms ourselves and verify them,
because the algorithm IS the contribution. Generators are different: they
are inputs, not results. networkx's `powerlaw_cluster_graph` is literally
the Holme-Kim reference implementation and `double_edge_swap` is literally
Maslov-Sneppen. Reimplementing them would add risk without adding evidence.

What we DO verify (see verify_generators.py) is that each family actually
moves the parameter it claims to move - that Holme-Kim's p really raises
clustering, that Chung-Lu's gamma really lands where we asked. That is the
part that could silently be wrong, so that is the part we check.
"""

from __future__ import annotations

import numpy as np
import networkx as nx
import scipy.sparse as sp

from .preprocessing import Network, build_network


# ----------------------------------------------------------------------------
# The bridge: any networkx graph -> our Network container
# ----------------------------------------------------------------------------

def from_networkx(g: nx.Graph, name: str, params: dict | None = None) -> Network:
    """
    Convert a networkx graph into a Network via the standard protocol.

    Every generator in this file funnels through here. That guarantees a
    synthetic graph and a real graph have been through identical treatment,
    which is the only way a cross-family comparison means anything.

    The generator's parameters are stored in provenance alongside the
    cleaning log, so a result table can always be joined back to the exact
    settings that produced the graph.
    """
    edges = [(int(u), int(v)) for u, v in g.edges()]
    if not edges:
        raise ValueError(f"generator {name} produced an empty edge list")

    net = build_network(edges, name=name, source=f"synthetic:{name}")
    net.provenance["generator"] = name
    net.provenance["generator_params"] = params or {}
    return net


# ----------------------------------------------------------------------------
# Homogeneous / delocalized controls
# ----------------------------------------------------------------------------

def erdos_renyi(n: int, mean_degree: float, seed: int = 0) -> Network:
    """
    G(n, p) with p set so the expected mean degree is `mean_degree`.

    The degree distribution is Poisson - no hubs, no tail. This is the
    delocalized control: if the locality horizon depends on hub structure,
    ER is where that dependence should vanish.

    We parameterize by mean degree rather than p because mean degree is the
    quantity we hold fixed across families.
    """
    p = mean_degree / (n - 1)
    g = nx.fast_gnp_random_graph(n, p, seed=seed)
    return from_networkx(g, f"ER_n{n}_k{mean_degree:g}",
                         {"n": n, "mean_degree": mean_degree, "p": p, "seed": seed})


def watts_strogatz(n: int, k: int, beta: float, seed: int = 0) -> Network:
    """
    Watts-Strogatz small world: a ring lattice with a fraction beta of edges
    rewired at random.

    Every node has degree ~k by construction, so the degree distribution is
    almost a delta function. What beta tunes is the path length and the
    clustering, NOT the tail.

    That makes WS the clean test of a specific confound: if r* changes across
    a beta sweep, the horizon responds to path length / clustering
    independently of any degree heterogeneity, because there is none here.
    """
    g = nx.watts_strogatz_graph(n, k, beta, seed=seed)
    return from_networkx(g, f"WS_n{n}_k{k}_b{beta:g}",
                         {"n": n, "k": k, "beta": beta, "seed": seed})


# ----------------------------------------------------------------------------
# Heavy tails
# ----------------------------------------------------------------------------

def barabasi_albert(n: int, m: int, seed: int = 0) -> Network:
    """
    Preferential attachment. Degree exponent is fixed at gamma = 3 by the
    mechanism - you cannot dial it, which is precisely why Chung-Lu below is
    needed for the gamma sweep.

    Kept as the hub-dominated / localized control case. Note its clustering
    decays toward zero as n grows, so BA alone cannot exercise clustering and
    tail together (this is the gap the reading list flagged; holme_kim fixes it).
    """
    g = nx.barabasi_albert_graph(n, m, seed=seed)
    return from_networkx(g, f"BA_n{n}_m{m}", {"n": n, "m": m, "seed": seed})


def holme_kim(n: int, m: int, p_triad: float, seed: int = 0) -> Network:
    """
    Holme-Kim: preferential attachment plus a triad-formation step.

    THE MISSING GENERATOR. BA gives heavy tails but no clustering; WS gives
    clustering but no tail. Holme-Kim gives both, with clustering dialled by
    p_triad while the degree distribution stays essentially BA's.

    That independence is the whole point: it lets us ask whether the locality
    horizon responds to clustering at a FIXED tail, which no real-network
    comparison can isolate.

    p_triad is the probability that each new edge, after the first, closes a
    triangle instead of attaching preferentially. p_triad = 0 reduces exactly
    to BA.
    """
    g = nx.powerlaw_cluster_graph(n, m, p_triad, seed=seed)
    return from_networkx(g, f"HK_n{n}_m{m}_p{p_triad:g}",
                         {"n": n, "m": m, "p_triad": p_triad, "seed": seed})


def _powerlaw_weights(n: int, gamma: float, mean_degree: float,
                      k_min: int = 1, rng: np.random.Generator | None = None) -> np.ndarray:
    """
    Draw n expected-degree weights from a power law with exponent gamma.

    This is the piece we write ourselves, because it is what makes gamma a
    controllable knob rather than a property we inherit from a mechanism.

    Method: inverse transform sampling on the continuous power law with
    support [k_min, inf):

        P(w > x) = (x / k_min)^(1 - gamma)
        =>  w = k_min * u^(-1 / (gamma - 1))     for u uniform on (0, 1]

    Then we rescale the whole vector so its mean equals `mean_degree`.

    WHY THE RESCALE MATTERS: without it, changing gamma changes the mean
    degree too, and a "gamma sweep" would secretly be a density sweep as
    well. Holding mean degree fixed is what makes the sweep interpretable.

    Note the rescale slightly shifts the effective k_min but leaves the tail
    exponent untouched, which is the parameter we actually care about.
    """
    rng = rng or np.random.default_rng(0)
    if gamma <= 1.0:
        raise ValueError("gamma must exceed 1 for the power law to be normalizable")

    u = rng.random(n)
    u = np.maximum(u, 1e-12)                 # guard against u = 0
    w = k_min * u ** (-1.0 / (gamma - 1.0))

    # Cap at the structural maximum. A weight above sqrt(sum of weights)
    # cannot be realised by Chung-Lu anyway (the edge probability would
    # exceed 1), so leaving it uncapped would silently flatten the tail
    # during sampling instead of here where it is visible.
    w = np.minimum(w, np.sqrt(n * mean_degree))

    return w * (mean_degree / w.mean())


def chung_lu(n: int, gamma: float, mean_degree: float = 6.0,
             k_min: int = 1, seed: int = 0) -> Network:
    """
    Chung-Lu expected-degree model with a TUNABLE tail exponent.

    Edge probability p_ij = w_i * w_j / sum(w), where w is the expected
    degree sequence. Node i then has expected degree w_i.

    THIS IS THE CENTRAL GENERATOR FOR THIS PROJECT. gamma controls how
    hub-dominated the network is, and hub dominance is exactly what the
    non-backtracking threshold and the localization literature say should
    govern how far influence information travels. Sweeping gamma at fixed
    mean degree is the controlled version of Finding 4.

    BA cannot do this - its gamma is pinned at 3 by the mechanism.

    Range worth sweeping: gamma in [2.1, 4.0]. Below ~2 the second moment
    diverges and finite-size effects dominate; above ~4 the tail is
    effectively gone and it behaves like ER.
    """
    rng = np.random.default_rng(seed)
    w = _powerlaw_weights(n, gamma, mean_degree, k_min, rng)
    g = nx.expected_degree_graph(w, seed=seed, selfloops=False)
    return from_networkx(g, f"CL_n{n}_g{gamma:g}_k{mean_degree:g}",
                         {"n": n, "gamma_target": gamma,
                          "mean_degree": mean_degree, "k_min": k_min, "seed": seed})


# ----------------------------------------------------------------------------
# Nulls: hold the degree sequence, destroy everything else
# ----------------------------------------------------------------------------

def configuration_model(degree_sequence, name: str = "CM", seed: int = 0) -> Network:
    """
    Molloy-Reed configuration model: a random graph with a GIVEN degree
    sequence and no other structure.

    This is the primary null. Feed it a real network's degree sequence and
    you get "the same network with everything except degrees randomised."
    If r* is the same on both, the horizon is a degree-sequence phenomenon.
    If it moves, something beyond degrees is driving it.

    The raw model produces self-loops and multi-edges; build_network strips
    both (decisions 3 and 4), which is the standard and stated treatment.
    Note this slightly lowers the realised mean degree - the provenance log
    records exactly how much, so it is never silent.
    """
    seq = np.asarray(degree_sequence, dtype=int)
    if seq.sum() % 2:
        # A valid degree sequence needs an even stub count. Bump the single
        # largest entry rather than a random one, so the change is
        # deterministic and its effect on the tail is negligible.
        seq[seq.argmax()] += 1
    g = nx.configuration_model(seq.tolist(), seed=seed)
    return from_networkx(nx.Graph(g), f"{name}_config",
                         {"n": len(seq), "seed": seed, "null_of": name})


def configuration_null_of(net: Network, seed: int = 0) -> Network:
    """Convenience: the degree-preserving null of an existing Network."""
    return configuration_model(net.degree, name=net.name, seed=seed)


def rewire_preserving_degree(net: Network, n_swaps_per_edge: int = 10,
                             seed: int = 0) -> Network:
    """
    Maslov-Sneppen double-edge-swap randomization.

    Repeatedly pick two edges (a,b) and (c,d) and replace them with (a,d) and
    (c,b). Every node's degree is untouched by construction, but degree
    correlations, clustering and community structure are progressively
    destroyed.

    Differs from the configuration model in a way that matters: this starts
    from the REAL graph and walks away from it, so with few swaps you get a
    partially randomized graph. That makes it usable as a continuous dial
    rather than an all-or-nothing null.

    n_swaps_per_edge = 10 is the usual convention for "fully mixed".
    """
    g = nx.Graph()
    g.add_nodes_from(range(net.n))
    c = sp.triu(net.adj, k=1).tocoo()
    g.add_edges_from(zip(c.row.tolist(), c.col.tolist()))

    n_swaps = int(n_swaps_per_edge * g.number_of_edges())
    # max_tries guards against dense graphs where valid swaps are rare;
    # nx raises if it cannot hit the target, so we give it generous headroom.
    nx.double_edge_swap(g, nswap=n_swaps, max_tries=n_swaps * 20, seed=seed)

    return from_networkx(g, f"{net.name}_rewired",
                         {"source_network": net.name,
                          "swaps_per_edge": n_swaps_per_edge, "seed": seed})


def rewire_to_assortativity(net: Network, target: float,
                            n_steps: int = 200000, check_every: int = 200,
                            seed: int = 0) -> Network:
    """
    Xulvi-Brunet-Sokolov rewiring: tune degree assortativity while holding
    the degree sequence exactly fixed.

    Algorithm: pick two edges, rank their four endpoints by degree. With
    probability q, reconnect so the two highest-degree endpoints pair up and
    the two lowest pair up (this raises assortativity); otherwise rewire at
    random. Reverse the pairing to lower assortativity.

    WHY THIS IS HERE: assortativity is a known confound for spreading
    processes - assortative and disassortative networks localize
    differently. If we sweep gamma without controlling assortativity, a
    reviewer can reasonably say the gamma effect is an assortativity effect.
    This generator is the answer to that objection.

    We accept a swap only if it moves assortativity toward the target, which
    is a greedy scheme rather than the original's fixed-q scheme. Greedy
    converges faster and the endpoint - a graph at a specified assortativity
    with the original degree sequence - is what we need.

    STOPPING IS THE WHOLE TRICK (this was a bug, found by testing)
    -------------------------------------------------------------
    A purely greedy loop does not converge to the target, it converges to the
    SATURATION point: every accepted swap pushes assortativity further, so
    the loop drives it as far as the degree sequence allows and the target
    value is ignored entirely. The first version of this function did exactly
    that - targets of -0.35, -0.20 and -0.10 all returned -0.303, and targets
    of 0.00, +0.10, +0.25 and +0.40 all returned +0.269.

    So we recompute assortativity every `check_every` accepted swaps and stop
    the moment we reach or cross the target. Recomputation is O(m), and doing
    it every few hundred swaps costs a few percent of runtime.

    KNOWN SIDE EFFECT, NOT A BUG: this rewiring changes clustering as well.
    On a BA base, driving assortativity to +0.27 raised average clustering
    from 0.042 to 0.078, and driving it to -0.30 dropped it to 0.002. Degree
    sequence is held exactly; clustering is not. Any claim from the
    assortativity family has to control for that, which is what the Holme-Kim
    family is for.
    """
    rng = np.random.default_rng(seed)

    c = sp.triu(net.adj, k=1).tocoo()
    edges = list(zip(c.row.tolist(), c.col.tolist()))
    edge_set = {tuple(sorted(e)) for e in edges}
    deg = net.degree.copy()

    current = _assortativity_from_edges(edges, deg)
    want_assortative = target > current
    accepted = 0

    for _ in range(n_steps):
        i, j = rng.integers(0, len(edges), size=2)
        if i == j:
            continue
        (a, b), (c_, d) = edges[i], edges[j]
        nodes = [a, b, c_, d]
        if len(set(nodes)) < 4:
            continue        # shared endpoint: swapping would make a self-loop

        # Rank the four endpoints by degree, then pair them up.
        order = sorted(nodes, key=lambda x: deg[x])
        if want_assortative:
            # low-with-low, high-with-high
            e1, e2 = (order[0], order[1]), (order[2], order[3])
        else:
            # low-with-high, twice
            e1, e2 = (order[0], order[3]), (order[1], order[2])

        k1, k2 = tuple(sorted(e1)), tuple(sorted(e2))
        if k1 in edge_set or k2 in edge_set:
            continue        # would create a multi-edge

        edge_set.discard(tuple(sorted(edges[i])))
        edge_set.discard(tuple(sorted(edges[j])))
        edge_set.add(k1); edge_set.add(k2)
        edges[i], edges[j] = e1, e2
        accepted += 1

        # Stop as soon as we reach the target, rather than saturating.
        if accepted % check_every == 0:
            current = _assortativity_from_edges(edges, deg)
            if (want_assortative and current >= target) or \
               (not want_assortative and current <= target):
                break

    final = _assortativity_from_edges(edges, deg)
    g = nx.Graph()
    g.add_nodes_from(range(net.n))
    g.add_edges_from(edges)
    out = from_networkx(g, f"{net.name}_assort{target:+.2f}",
                        {"source_network": net.name,
                         "target_assortativity": target,
                         "achieved_assortativity": final,
                         "reached_target": bool(
                             (final >= target) if want_assortative else (final <= target)),
                         "accepted_swaps": accepted,
                         "n_steps": n_steps, "seed": seed})
    return out


def _assortativity_from_edges(edges, deg) -> float:
    """
    Newman's degree assortativity computed directly from an edge list.

    Kept private and separate from structure.py's version because this one
    runs inside a rewiring loop on a plain edge list, where converting to a
    Network every iteration would dominate the cost.
    """
    if not edges:
        return 0.0
    x = np.array([deg[u] for u, v in edges], dtype=float)
    y = np.array([deg[v] for u, v in edges], dtype=float)
    # Symmetrize: each undirected edge contributes in both orientations.
    a = np.concatenate([x, y]); b = np.concatenate([y, x])
    sa, sb = a.std(), b.std()
    return float(np.mean((a - a.mean()) * (b - b.mean())) / (sa * sb)) if sa and sb else 0.0


# ----------------------------------------------------------------------------
# Heavy tails AND communities
# ----------------------------------------------------------------------------

def lfr(n: int, tau1: float = 2.5, tau2: float = 1.5, mu: float = 0.1,
        mean_degree: float = 6.0, min_community: int = 20,
        seed: int = 0) -> Network:
    """
    Lancichinetti-Fortunato-Radicchi benchmark: power-law degrees AND
    power-law community sizes, with mu setting the fraction of each node's
    edges that leave its community.

    mu is the knob that matters for us. Low mu means tightly bounded
    communities, so a node's influence should be almost fully determined
    inside a small radius; high mu means the community walls are porous.
    If the locality horizon means anything, r* should track mu.

    LFR generation can fail to converge for awkward parameter combinations;
    we surface that as an error rather than silently retrying with different
    settings, because a silently altered mu would corrupt the sweep.
    """
    g = nx.LFR_benchmark_graph(
        n, tau1, tau2, mu, average_degree=mean_degree,
        min_community=min_community, seed=seed, max_iters=5000)
    g = nx.Graph(g)
    g.remove_edges_from(nx.selfloop_edges(g))
    return from_networkx(g, f"LFR_n{n}_mu{mu:g}",
                         {"n": n, "tau1": tau1, "tau2": tau2, "mu": mu,
                          "mean_degree": mean_degree, "seed": seed})

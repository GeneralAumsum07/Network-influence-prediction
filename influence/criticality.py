"""
criticality.py
==============
Each network's epidemic threshold, computed from its own structure.

WHY THIS MODULE IS NECESSARY
----------------------------
We need to pick a transmission probability p. The obvious approaches both
fail:

  - "Use p = 0.05 everywhere" - meaningless. On a dense network that is far
    above the tipping point (everything spreads to everyone); on a sparse one
    it is far below (nothing spreads at all). Comparing results across
    networks at fixed p compares different dynamical regimes.

  - "Pick p that maximises the spread of influence scores" - confounded with
    scale. Larger p means larger cascades means larger raw variance, so the
    criterion just chases the top of whatever range you searched.

The principled answer is to compute each network's OWN critical threshold
beta_c and then work at a fixed multiple of it. Then "p = 2 * beta_c" means
the same dynamical regime on every network, and cross-network comparison is
finally valid.

THE NON-BACKTRACKING (HASHIMOTO) OPERATOR
-----------------------------------------
The naive estimate beta_c = 1/lambda_1(A), using the adjacency matrix, is
known to be poor on networks with hubs, because the leading eigenvector
localises on the hub and the estimate is dragged around by a handful of nodes.

The better operator tracks walks that never immediately step back where they
came from. It is defined on DIRECTED edges:

    B[(i->j), (k->l)] = 1  if j == k and i != l,  else 0

and the threshold is

    beta_c = 1 / lambda_1(B)

B is 2m x 2m, which is large. The Ihara-Bass identity gives the same leading
eigenvalue from a 2n x 2n matrix instead:

    M = [[ A,      I - D ],
         [ I,      0     ]]

where A is adjacency and D is the degree diagonal. For our networks that is
several times smaller, so we use M and verify it against direct B on small
graphs.

We derive all of this ourselves and test it rather than taking any published
threshold value on faith.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .preprocessing import Network


# ----------------------------------------------------------------------------
# Building the operators
# ----------------------------------------------------------------------------

def build_nonbacktracking_direct(net: Network) -> sp.csr_matrix:
    """
    Build the full 2m x 2m non-backtracking matrix explicitly.

    Only used for verification on small graphs - it is memory-hungry. The
    Ihara-Bass form below is what we actually use in practice.
    """
    coo = sp.triu(net.adj, k=1).tocoo()
    # Each undirected edge becomes two directed arcs.
    arcs = [(int(u), int(v)) for u, v in zip(coo.row, coo.col)]
    arcs += [(v, u) for u, v in arcs]
    index = {a: i for i, a in enumerate(arcs)}
    n_arcs = len(arcs)

    rows, cols = [], []
    for (i, j) in arcs:
        src = index[(i, j)]
        # An arc (i->j) can be followed by (j->l) for any neighbour l of j,
        # except l == i, which would be backtracking.
        for l in net.nbrs[j]:
            l = int(l)
            if l == i:
                continue
            rows.append(src)
            cols.append(index[(j, l)])

    return sp.csr_matrix(
        (np.ones(len(rows), dtype=np.float64), (rows, cols)),
        shape=(n_arcs, n_arcs))


def build_ihara_bass(net: Network) -> sp.csr_matrix:
    """
    The 2n x 2n matrix whose leading eigenvalue equals that of B.

        M = [[ A,   I - D ],
             [ I,   0     ]]
    """
    n = net.n
    A = net.adj.astype(np.float64)
    I = sp.identity(n, format="csr", dtype=np.float64)
    D = sp.diags(net.degree.astype(np.float64), format="csr")
    Z = sp.csr_matrix((n, n), dtype=np.float64)

    top = sp.hstack([A, I - D], format="csr")
    bottom = sp.hstack([I, Z], format="csr")
    return sp.vstack([top, bottom], format="csr")


# ----------------------------------------------------------------------------
# The threshold
# ----------------------------------------------------------------------------

# Largest operator dimension for which the dense eigvals fallback in
# leading_eigenvalue is used when Arnoldi fails. 4000 x 4000 complex eigvals
# takes seconds; the registered networks' operators are 10^4-10^5 wide.
DENSE_FALLBACK_MAX_DIM = 4000


def leading_eigenvalue(M: sp.spmatrix, tol: float = 1e-8) -> float:
    """
    Spectral radius via sparse Arnoldi iteration.

    M is not necessarily symmetric.  `which="LM"` can legitimately return
    the negative member of a bipartite +/- extremal pair, so taking its real
    part made a positive threshold depend on the Arnoldi start vector.  The
    threshold is defined by the spectral radius, which is nonnegative.

    This helper deliberately says nothing about whether an Ihara--Bass root
    represents a real non-backtracking transition.  Trees need that separate
    structural check in ``epidemic_threshold`` because their reduced matrix
    has algebraic +/-1 roots although B is nilpotent.
    """
    if M.shape[0] == 0:
        return 0.0
    if M.shape[0] <= 2:
        return float(np.max(np.abs(np.linalg.eigvals(M.toarray()))))
    try:
        vals = spla.eigs(M, k=1, which="LM", return_eigenvectors=False, tol=tol)
    except spla.ArpackNoConvergence:
        # Added 2026-09-11 by Claude Opus 5 (Task 6 audit finding P1-05).
        # Arnoldi fails to converge on small multicyclic graphs whose
        # non-backtracking spectrum crowds the unit circle - a theta graph
        # with three paths of eleven or more edges is enough (rho(B) =
        # 2^(1/11) ~ 1.065, with dozens of eigenvalues of modulus ~1). The
        # failure is loud, never a wrong value; the dense spectrum is exact
        # and cheap at this size, so use it. Above the cap a dense solve
        # would be the wrong tool, so name the graph and re-raise instead of
        # silently spending minutes - none of the five registered networks
        # (all >> 4000 arcs) has ever reached this branch, and their cached
        # beta_c values are unchanged by it.
        if M.shape[0] <= DENSE_FALLBACK_MAX_DIM:
            return float(np.max(np.abs(np.linalg.eigvals(M.toarray()))))
        raise ValueError(
            f"leading_eigenvalue: Arnoldi did not converge on a "
            f"{M.shape[0]}x{M.shape[1]} operator and it is too large for the "
            f"dense fallback ({DENSE_FALLBACK_MAX_DIM}); the spectral radius "
            f"could not be established") from None
    return float(np.abs(vals[0]))


def _component_cyclomatic_excess(net: Network) -> np.ndarray:
    """Return ``edges - vertices + 1`` for each undirected component.

    A component with excess zero is a tree, while a unicyclic component has
    excess one.  This structural classification is exact and avoids asking
    Arnoldi to resolve the non-normal Ihara--Bass roots created by long trees
    attached to an otherwise simple cycle.
    """
    n_components, labels = sp.csgraph.connected_components(
        net.adj, directed=False, return_labels=True
    )
    if n_components == 0:
        return np.empty(0, dtype=np.int64)

    vertices = np.bincount(labels, minlength=n_components)
    upper = sp.triu(net.adj, k=1).tocoo()
    edges = np.bincount(labels[upper.row], minlength=n_components)
    return edges - vertices + 1


def epidemic_threshold(net: Network, method: str = "nonbacktracking") -> float:
    """
    beta_c for this network.

    method:
      'nonbacktracking' - 1 / lambda_1(B) via Ihara-Bass. The accurate one.
      'adjacency'       - 1 / lambda_1(A). The naive one; kept so we can
                          MEASURE how much they differ rather than assert it.
      'meanfield'       - <k> / (<k^2> - <k>). The classical heterogeneous
                          mean-field estimate.
    """
    if method == "nonbacktracking":
        excess = _component_cyclomatic_excess(net)
        # Trees have no recurrent NB walk, so direct B is nilpotent and no
        # finite critical point exists.  The Ihara--Bass +/-1 roots are only
        # cancellation artefacts in this case.
        if len(excess) == 0 or np.all(excess == 0):
            return np.inf

        # Every unicyclic component has one directed cycle as its recurrent
        # NB class; attached trees are transient.  Its spectral radius is
        # exactly one.  Treating every component separately matters for
        # explicit disconnected inputs: a forest beside a cycle must not
        # erase the cycle's finite threshold.
        if np.all(excess <= 1):
            return 1.0

        # A component with two or more independent cycles has no comparable
        # closed-form radius, so retain the reduced sparse solve for the real
        # graphs and multicyclic test cases.
        lam = leading_eigenvalue(build_ihara_bass(net))
        return float(1.0 / lam) if lam > 0 else np.inf

    if method == "adjacency":
        # eigs cannot operate on a 0x0 matrix, and an edgeless graph has
        # adjacency spectral radius zero by definition.
        if net.n == 0 or net.adj.nnz == 0:
            return np.inf
        lam = leading_eigenvalue(net.adj.astype(np.float64))
        return float(1.0 / lam) if lam > 0 else np.inf

    if method == "meanfield":
        k = net.degree.astype(np.float64)
        if len(k) == 0:
            return np.inf
        k1, k2 = k.mean(), (k ** 2).mean()
        denom = k2 - k1
        return float(k1 / denom) if denom > 0 else np.inf

    raise ValueError(f"unknown method: {method}")


def threshold_report(net: Network) -> str:
    """
    Compare all three estimates. Print this per network - the gap between the
    naive and non-backtracking values is itself informative about how
    hub-dominated the network is.
    """
    nb = epidemic_threshold(net, "nonbacktracking")
    ad = epidemic_threshold(net, "adjacency")
    mf = epidemic_threshold(net, "meanfield")
    return (f"  beta_c (non-backtracking) : {nb:.5f}   <- we use this\n"
            f"  beta_c (adjacency)        : {ad:.5f}\n"
            f"  beta_c (mean-field)       : {mf:.5f}\n"
            f"  NB / adjacency ratio      : {nb/ad:.3f}")


def transmission_probability(threshold: float, multiple: float) -> float:
    """Turn an already-computed critical point into a valid IC probability.

    ``multiple`` is a positive regime multiplier, rather than a raw IC
    probability.  IC itself permits p=0, but a zero multiplier is not a
    multiple *above* a critical point and would conceal an input error.
    Keeping this validation separate lets stage1 reuse its recorded beta_c
    without paying for a second sparse eigensolve.
    """
    if not np.isfinite(multiple) or multiple <= 0:
        raise ValueError("critical-threshold multiple must be finite and positive")
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError(
            "no finite non-backtracking critical point exists for this graph; "
            "a transmission probability cannot be derived from its threshold"
        )

    probability = float(multiple * threshold)
    if not np.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError(
            f"critical-threshold multiple produces p={probability!r}, outside [0, 1]"
        )
    return probability


def transmission_from_threshold(net: Network, multiple: float = 2.0,
                                threshold: float | None = None) -> float:
    """
    Set p as a fixed multiple of this network's own critical threshold.

    This is what makes cross-network comparison valid: `multiple=2.0` puts
    every network in the same dynamical regime (twice critical) regardless of
    its density or degree distribution.  Pass ``threshold`` only when the
    caller has already computed this network's non-backtracking threshold and
    needs the cache metadata and validated p to use the identical value.
    """
    beta_c = (epidemic_threshold(net, "nonbacktracking")
              if threshold is None else float(threshold))
    return transmission_probability(beta_c, multiple)

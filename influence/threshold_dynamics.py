"""Deterministic fractional-threshold cascades for the complex-contagion lane.

Lives in its own module, not in local_dynamics.py: that file's hash is part of
the local-IC lane's recorded identity, and editing it would make the local-IC lane's sidecars look stale.

Model, as registered (complex-contagion prereg, 2026-09-12: fixed fractional theta,
N[i] seeding):
  - seed the closed neighbourhood N[i] = {i} + neighbours of i;
  - an inactive node j activates once (active neighbours of j) / k_j >= theta;
  - activation is permanent, iterate to the fixed point.
Seeding N[i] rather than {i} alone sidesteps a known degeneracy: a
lone seed activates neighbour j only when 1/k_j >= theta, so with theta = 0.1
nothing of degree > 10 could ever be reached from a single node.

The dynamics are deterministic: one cascade per seed node, no draws. So the
target has no sampling noise, and only fold/seed noise enters r*.
"""
from fractions import Fraction

import numpy as np
import scipy.sparse as sp


def exact_theta(theta) -> Fraction:
    """theta as an exact fraction in (0, 1].

    The activation test sits exactly on the boundary whenever theta * k is
    an integer (a degree-30 node at theta = 0.1 activates at exactly 3
    active neighbours), so it is done in integers: den * c >= num * k.
    Converting through str() turns the float 0.1 into 1/10, not the binary
    value 3602879701896397/36028797018963968.

    This is defensive, not a fix for an observed failure: for the registered
    theta in {0.1, 0.2}, the float tests c >= theta * k and c / k >= theta
    agree with the exact one at every boundary up to degree 200,000 (checked
    2026-11-02). The integer form keeps that true for any theta a later
    addendum registers, without re-checking.
    """
    if isinstance(theta, bool):
        raise ValueError("theta must be a number in (0, 1]")
    frac = theta if isinstance(theta, Fraction) else Fraction(str(theta))
    if not 0 < frac <= 1:
        raise ValueError(f"theta must lie in (0, 1], got {theta!r}")
    return frac


def threshold_cascade_sizes(net, theta, batch_size: int = 256) -> np.ndarray:
    """Final cascade size per seed node i, seeding N[i]; int64 [n].

    Vectorised over a batch of seeds: S is an (n x batch) boolean matrix, one
    column per seed, and each round applies S <- S | (den * (A @ S) >= num * k)
    to every column at once. Synchronous rounds reach the same final set as
    any one-at-a-time order, because activation only ever adds nodes and the
    rule is monotone: the result is the unique smallest closed set containing
    N[i]. The verifier checks this against a sequential queue implementation.
    """
    frac = exact_theta(theta)
    if not isinstance(batch_size, (int, np.integer)) or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    a = sp.csr_matrix(net.adj, dtype=np.int64)
    n = a.shape[0]
    if a.shape != (n, n) or n < 1 or (a != a.T).nnz or a.diagonal().any():
        raise ValueError("requires a nonempty symmetric loop-free graph")
    k = np.asarray(a.sum(axis=1)).ravel()
    # Integer form of c / k >= theta. An isolated node (k = 0) would pass
    # 0 >= 0 and activate spontaneously, so it is excluded explicitly; the
    # project's networks are connected, but the function must not depend on it.
    need = (frac.numerator * k)[:, None]
    can = (k > 0)[:, None]
    den = frac.denominator

    sizes = np.empty(n, dtype=np.int64)
    for start in range(0, n, batch_size):
        stop = min(n, start + batch_size)
        cols = np.arange(start, stop)
        # Column b is N[start + b]: the seed's adjacency column plus itself.
        s = a[:, cols].toarray().astype(bool)
        s[cols, np.arange(stop - start)] = True
        while True:
            c = a @ s.astype(np.int64)            # active-neighbour counts
            new = s | ((den * c >= need) & can)
            if np.array_equal(new, s):
                break
            s = new
        sizes[start:stop] = s.sum(axis=0)
    return sizes

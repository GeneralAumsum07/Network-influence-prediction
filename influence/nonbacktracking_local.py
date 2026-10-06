"""Bounded, exact non-backtracking walk counts for one undirected network.

The Phase 6.5 L2 baseline only registers lengths one through three.  Keeping
that boundary in the public API is deliberate: longer NB walks can grow beyond
fixed-width integers and would invite an expensive operator construction that
is neither needed nor part of the registered comparison.
"""
from __future__ import annotations

import numbers

import numpy as np

from .preprocessing import Network


_MAX_LENGTH = 3
_INT64_MAX = np.iinfo(np.int64).max


def _checked_int64(values: list[int], length: int) -> np.ndarray:
    """Publish exact counts or fail loudly before a narrowing conversion wraps."""
    if any(value < 0 or value > _INT64_MAX for value in values):
        raise OverflowError(
            f"non-backtracking walk count at length {length} exceeds int64; "
            "the bounded L2 API refuses a lossy result"
        )
    return np.asarray(values, dtype=np.int64)


def nb_walk_counts(net: Network, length: int) -> np.ndarray:
    """Return each node's number of non-backtracking walks of ``length`` edges.

    The recurrence is over implicit directed arcs ``u -> v``.  An arc's value
    is the number of permitted suffixes after entering ``v``; its successor
    sum excludes only ``u``, which is precisely the immediate-backtrack rule.
    No degree-squared Hashimoto matrix is materialised.  Length one is degree,
    while length three uses only the root's two-hop information.
    """
    if isinstance(length, bool) or not isinstance(length, numbers.Integral) or not 1 <= length <= _MAX_LENGTH:
        raise ValueError(f"length must be an integer in 1..{_MAX_LENGTH}")
    length = int(length)
    if len(net.nbrs) != net.n or len(net.degree) != net.n:
        raise ValueError("network neighbour and degree arrays must match adjacency order")

    degree = [int(value) for value in net.degree]
    if any(value < 0 for value in degree):
        raise ValueError("network degrees must be nonnegative")
    if length == 1:
        return _checked_int64(degree, length)

    # One record per directed arc is O(m), unlike the O(sum degree^2) explicit
    # non-backtracking matrix.  Python integers make intermediate additions
    # exact; _checked_int64 supplies the stable numeric result at the boundary.
    arcs = [(u, int(v)) for u, neighbours in enumerate(net.nbrs) for v in neighbours]
    arc_index = {arc: index for index, arc in enumerate(arcs)}
    if len(arc_index) != len(arcs):
        raise ValueError("network neighbour arrays must not contain duplicate arcs")
    if any((v, u) not in arc_index for u, v in arcs):
        raise ValueError("network neighbour arrays must describe an undirected graph")
    suffix = [1] * len(arcs)
    by_source: list[int] = [u for u, _ in arcs]
    for _step in range(1, length):
        # Group each old suffix once.  Subtracting the one reverse arc then
        # gives every legal successor sum in O(m+n), rather than re-summing a
        # high-degree neighbour list for every incoming arc (O(sum degree^2)).
        outgoing_total = [0] * net.n
        for source, value in zip(by_source, suffix):
            outgoing_total[source] += value
        next_suffix = [0] * len(arcs)
        for index, (u, v) in enumerate(arcs):
            next_suffix[index] = outgoing_total[v] - suffix[arc_index[(v, u)]]
        suffix = next_suffix

    result = [0] * net.n
    for source, value in zip(by_source, suffix):
        result[source] += value
    return _checked_int64(result, length)

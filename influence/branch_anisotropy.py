"""Order-invariant hop-two branch anisotropy features for Phase 6.5 L7."""
from __future__ import annotations

import numpy as np

from .preprocessing import Network


def branch_anisotropy(net: Network) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return maximum branch share, natural-log entropy, and empty-shell flags.

    For a root, every exact-distance-two node contributes mass one, divided
    equally between *all* adjacent first-hop parents.  This makes diamonds
    fractional rather than accidentally assigning them to whichever BFS parent
    happened to be visited first.  The implementation stores only one local
    parent map per root; it never builds an n-by-n or n-cubed tensor.
    """
    if len(net.nbrs) != net.n:
        raise ValueError("neighbour arrays must match graph order")
    maximum = np.zeros(net.n, dtype=np.float64)
    entropy = np.zeros(net.n, dtype=np.float64)
    empty = np.zeros(net.n, dtype=bool)
    for root in range(net.n):
        parents = [int(v) for v in net.nbrs[root]]
        direct = set(parents)
        # child -> every root-neighbour through which it is reached.  Set use
        # guards malformed duplicate neighbour arrays without choosing an order.
        child_parents: dict[int, set[int]] = {}
        for parent in parents:
            for child_value in net.nbrs[parent]:
                child = int(child_value)
                if child != root and child not in direct:
                    child_parents.setdefault(child, set()).add(parent)
        shell_size = len(child_parents)
        if shell_size == 0:
            empty[root] = True
            continue
        mass = {parent: 0.0 for parent in parents}
        for tied_parents in child_parents.values():
            share = 1.0 / len(tied_parents)
            for parent in tied_parents:
                mass[parent] += share
        shares = np.fromiter((mass[parent] / shell_size for parent in parents), dtype=np.float64)
        # Floating addition is deterministic because parents and neighbours are
        # canonical graph arrays; the values themselves are independent of BFS.
        maximum[root] = float(shares.max(initial=0.0))
        positive = shares[shares > 0.0]
        entropy[root] = float(-(positive * np.log(positive)).sum())
    return maximum, entropy, empty

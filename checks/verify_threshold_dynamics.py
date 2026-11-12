"""Independent fixtures for the complex-contagion fractional-threshold cascade.

Every check compares threshold_cascade_sizes against something it does not
share code with: hand-computed answers on tiny graphs, and a sequential
queue implementation written the obvious way.
"""
import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import unittest
from collections import deque
from fractions import Fraction

import numpy as np
import scipy.sparse as sp

from influence.preprocessing import Network
from influence.threshold_dynamics import exact_theta, threshold_cascade_sizes


def fixture(n, edges):
    a = np.zeros((n, n), dtype=bool)
    for u, v in edges:
        a[u, v] = a[v, u] = True
    return Network('fixture', sp.csr_matrix(a), [np.flatnonzero(r) for r in a],
                   a.sum(1), np.arange(n))


def reference_size(net, i, theta):
    """Sequential cascade from N[i], one node at a time, exact fractions."""
    theta = Fraction(str(theta))
    active = {i, *net.nbrs[i].tolist()}
    queue = deque(active)
    while queue:
        u = queue.popleft()
        for j in net.nbrs[u].tolist():
            if j in active:
                continue
            k = len(net.nbrs[j])
            if Fraction(sum(v in active for v in net.nbrs[j].tolist()), k) >= theta:
                active.add(j)
                queue.append(j)
    return len(active)


def random_graph(rng, n, p):
    edges = [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p]
    return fixture(n, edges)


class ThresholdCascadeTests(unittest.TestCase):
    def test_path_by_hand(self):
        # Path 0-1-2-3-4. Seed N[0] = {0, 1}. Node 2 sees 1 of 2 neighbours.
        net = fixture(5, [(0, 1), (1, 2), (2, 3), (3, 4)])
        self.assertEqual(threshold_cascade_sizes(net, 0.5)[0], 5)   # 1/2 >= .5
        self.assertEqual(threshold_cascade_sizes(net, 0.6)[0], 2)   # 1/2 < .6
        # The middle seed N[2] = {1, 2, 3} reaches both ends at any theta <= 1.
        self.assertEqual(threshold_cascade_sizes(net, 1.0)[2], 5)

    def test_activation_exactly_on_the_boundary(self):
        # Hub 0 has degree 30. Seed node 31 touches hub neighbours 1..m, so
        # N[31] gives the hub exactly m/30 active. "Greater or equal" means
        # m = 3 (exactly 0.1) activates the hub and m = 2 does not.
        # m = 3: hub fires, then every degree-1 leaf sees 1/1 -> all 32 nodes.
        # m = 2: N[31] = {31, 1, 2} and nothing else can move -> 3 nodes.
        for m, want in ((3, 32), (2, 3)):
            edges = [(0, j) for j in range(1, 31)] + [(31, j) for j in range(1, m + 1)]
            net = fixture(32, edges)
            self.assertEqual(threshold_cascade_sizes(net, 0.1)[31], want, f"m = {m}")

    def test_matches_sequential_reference(self):
        rng = np.random.default_rng(0)
        for trial in range(30):
            net = random_graph(rng, int(rng.integers(5, 40)), float(rng.uniform(.05, .3)))
            for theta in (0.1, 0.2, 0.35, 0.5, 1.0):
                got = threshold_cascade_sizes(net, theta, batch_size=7)
                want = [reference_size(net, i, theta) for i in range(net.adj.shape[0])]
                self.assertEqual(got.tolist(), want, f"trial {trial} theta {theta}")

    def test_batch_size_invariant(self):
        net = random_graph(np.random.default_rng(1), 60, .08)
        base = threshold_cascade_sizes(net, 0.2, batch_size=1)
        for b in (2, 13, 60, 1000):
            np.testing.assert_array_equal(threshold_cascade_sizes(net, 0.2, batch_size=b), base)

    def test_monotone_in_theta(self):
        net = random_graph(np.random.default_rng(2), 80, .06)
        lo, hi = threshold_cascade_sizes(net, 0.1), threshold_cascade_sizes(net, 0.2)
        self.assertTrue((lo >= hi).all())

    def test_isolated_node_never_activates_spontaneously(self):
        # Node 3 is isolated: 0 active of 0 neighbours must not count as >= theta.
        net = fixture(4, [(0, 1), (1, 2)])
        sizes = threshold_cascade_sizes(net, 0.1)
        self.assertEqual(sizes.tolist(), [3, 3, 3, 1])

    def test_lower_bound_is_closed_neighbourhood(self):
        net = random_graph(np.random.default_rng(3), 50, .1)
        deg = np.asarray(net.adj.sum(1)).ravel()
        self.assertTrue((threshold_cascade_sizes(net, 1.0) >= deg + 1).all())

    def test_theta_validation(self):
        self.assertEqual(exact_theta(0.1), Fraction(1, 10))
        self.assertEqual(exact_theta('0.2'), Fraction(1, 5))
        for bad in (0, -0.1, 1.5, True):
            with self.assertRaises(ValueError):
                exact_theta(bad)
        net = fixture(3, [(0, 1), (1, 2)])
        with self.assertRaises(ValueError):
            threshold_cascade_sizes(net, 0.1, batch_size=0)


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Independent fixtures for the exact r-local threshold probe.

Checks truncated_threshold_sizes against hand-computed graphs, against a
sequential implementation that computes the ball by plain BFS, and against
the four properties the 2026-11-02 16:59 registration lists.
"""
import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import unittest
from collections import deque
from fractions import Fraction

import numpy as np

from influence.threshold_dynamics import threshold_cascade_sizes
from influence.threshold_local import truncated_threshold_sizes
from verify_threshold_dynamics import fixture, random_graph


def bfs_ball(net, i, r):
    dist = {i: 0}
    queue = deque([i])
    while queue:
        u = queue.popleft()
        if dist[u] == r:
            continue
        for v in net.nbrs[u].tolist():
            if v not in dist:
                dist[v] = dist[u] + 1
                queue.append(v)
    return set(dist)


def reference_size(net, i, theta, r):
    return len(active_set(net, i, theta, r))


def active_set(net, i, theta, r):
    """Sequential cascade from N[i], activation allowed only inside the BFS ball."""
    theta = Fraction(str(theta))
    ball = bfs_ball(net, i, r)
    active = {i, *net.nbrs[i].tolist()}
    queue = deque(active)
    while queue:
        u = queue.popleft()
        for j in net.nbrs[u].tolist():
            if j in active or j not in ball:
                continue
            k = len(net.nbrs[j])
            if Fraction(sum(v in active for v in net.nbrs[j].tolist()), k) >= theta:
                active.add(j)
                queue.append(j)
    return active


class TruncatedCascadeTests(unittest.TestCase):
    def test_path_by_hand(self):
        # Path 0-1-2-3-4 at theta 0.5. From N[0] = {0, 1} the full cascade
        # takes the whole path, one node per radius beyond 1.
        net = fixture(5, [(0, 1), (1, 2), (2, 3), (3, 4)])
        got = truncated_threshold_sizes(net, 0.5, range(0, 6))
        self.assertEqual([got[r][0] for r in range(6)], [2, 2, 3, 4, 5, 5])

    def test_matches_sequential_reference(self):
        rng = np.random.default_rng(10)
        for trial in range(25):
            net = random_graph(rng, int(rng.integers(5, 35)), float(rng.uniform(.05, .3)))
            for theta in (0.1, 0.2, 0.5):
                got = truncated_threshold_sizes(net, theta, (0, 1, 2, 3, 4), batch_size=6)
                for r, sizes in got.items():
                    want = [reference_size(net, i, theta, r) for i in range(net.adj.shape[0])]
                    self.assertEqual(sizes.tolist(), want, f"trial {trial} theta {theta} r {r}")

    def test_registered_properties(self):
        net = random_graph(np.random.default_rng(11), 70, .06)
        n = net.adj.shape[0]
        full = threshold_cascade_sizes(net, 0.2)
        deg = np.asarray(net.adj.sum(1)).ravel()
        got = truncated_threshold_sizes(net, 0.2, range(0, n))
        # Lower bound, monotone in r, k + 1 at r <= 1, exact at r >= n - 1
        # (no shortest path is longer than n - 1).
        for r in range(n):
            self.assertTrue((got[r] <= full).all(), f"r {r}")
            if r:
                self.assertTrue((got[r] >= got[r - 1]).all(), f"r {r}")
        np.testing.assert_array_equal(got[0], deg + 1)
        np.testing.assert_array_equal(got[1], deg + 1)
        np.testing.assert_array_equal(got[n - 1], full)

    def test_radius_order_and_batch_invariant(self):
        net = random_graph(np.random.default_rng(12), 50, .08)
        base = truncated_threshold_sizes(net, 0.2, (1, 2, 3), batch_size=1)
        for b in (3, 17, 1000):
            other = truncated_threshold_sizes(net, 0.2, (3, 2, 1, 2), batch_size=b)
            for r in (1, 2, 3):
                np.testing.assert_array_equal(other[r], base[r])

    def test_containment_matches_reference_and_is_exact(self):
        # Containment (registered 17:15, part A): no active node at distance
        # exactly r. Checked two ways: against BFS distances computed here
        # independently, and against the claim it exists for, that a
        # contained cascade has already reached its full size.
        rng = np.random.default_rng(13)
        for trial in range(20):
            net = random_graph(rng, int(rng.integers(5, 35)), float(rng.uniform(.05, .3)))
            full = threshold_cascade_sizes(net, 0.2)
            sizes, cont = truncated_threshold_sizes(net, 0.2, (0, 1, 2, 3, 4),
                                                    batch_size=5, with_contained=True)
            plain = truncated_threshold_sizes(net, 0.2, (0, 1, 2, 3, 4), batch_size=5)
            for r in (0, 1, 2, 3, 4):
                np.testing.assert_array_equal(sizes[r], plain[r])   # flag changes nothing else
                for i in range(net.adj.shape[0]):
                    ball, inner = bfs_ball(net, i, r), (bfs_ball(net, i, r - 1) if r else set())
                    active = active_set(net, i, 0.2, r)
                    want = not (active & (ball - inner))
                    self.assertEqual(bool(cont[r][i]), want, f"trial {trial} r {r} node {i}")
                    if r >= 1 and cont[r][i]:
                        self.assertEqual(sizes[r][i], full[i], f"trial {trial} r {r} node {i}")
            # r = 1: every distance-1 node is a seed, so only isolated nodes
            # could be contained, and random_graph may make some.
            deg = np.asarray(net.adj.sum(1)).ravel()
            np.testing.assert_array_equal(cont[1], deg == 0)

    def test_input_validation(self):
        net = fixture(3, [(0, 1), (1, 2)])
        for bad in ((), (-1,)):
            with self.assertRaises(ValueError):
                truncated_threshold_sizes(net, 0.2, bad)
        with self.assertRaises(ValueError):
            truncated_threshold_sizes(net, 0.2, (1,), batch_size=0)
        with self.assertRaises(ValueError):
            truncated_threshold_sizes(net, 0, (1,))


if __name__ == '__main__':
    unittest.main(verbosity=2)

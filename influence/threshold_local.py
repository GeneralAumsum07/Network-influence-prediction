"""Exact r-local threshold cascades: the L5 probe registered 2026-11-02 16:59.

The threshold model is deterministic, so what an observer limited to radius r
around node i can know about i's cascade is computable exactly: run the
cascade but let only nodes inside the ball B_r(i) activate. Every node still
uses its FULL degree k_j as the denominator, so a neighbour outside the ball
counts as inactive. That keeps radius r's information budget the same as the
feature tiers': deciding j needs k_j, just as degree is a hop-0 fact about i.

Consequences the verifier checks:
  - trunc_r(i) <= spread_theta(i): the ball can only withhold activations;
  - trunc_r(i) does not decrease in r: a bigger ball allows more;
  - trunc_r(i) = spread_theta(i) once the ball is the whole graph;
  - for r <= 1 the ball is inside the seed N[i], so trunc_r(i) = k_i + 1.

A separate module, not an addition to threshold_dynamics.py: that file's hash
is pinned in results/phase7_threshold/sources.json while the L5 fits run, and
editing it would stop them. This module imports from it and changes nothing.
"""
import numpy as np
import scipy.sparse as sp

from influence.threshold_dynamics import exact_theta


def truncated_threshold_sizes(net, theta, radii, batch_size: int = 256,
                              with_contained: bool = False):
    """{r: int64 [n]} of ball-truncated cascade sizes, seeding N[i].

    All radii are computed in one pass per batch. The balls are grown
    incrementally (B_{r+1} = B_r plus its neighbours), so asking for r = 1..5
    costs one ball expansion per extra radius rather than a fresh BFS each.

    with_contained=True also returns {r: bool [n]}: True where no node at
    distance exactly r is active at the fixed point (registered 2026-11-02
    17:15, part A). Such a cascade is provably complete: every node outside
    the ball has neighbours only at distance >= r, none of them active, so
    nothing outside can ever activate and trunc_r(i) equals the full cascade.
    The observer can test this from the ball alone, which is what lets radius
    r PROVE a fizzle without the ball holding 5% of n. Returned as a pair
    (sizes, contained) so the default call keeps its 16:59 return type.
    """
    frac = exact_theta(theta)
    radii = sorted({int(r) for r in radii})
    if not radii or radii[0] < 0:
        raise ValueError("radii must be a nonempty set of non-negative integers")
    if not isinstance(batch_size, (int, np.integer)) or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    a = sp.csr_matrix(net.adj, dtype=np.int64)
    n = a.shape[0]
    if a.shape != (n, n) or n < 1 or (a != a.T).nnz or a.diagonal().any():
        raise ValueError("requires a nonempty symmetric loop-free graph")
    k = np.asarray(a.sum(axis=1)).ravel()
    # Same integer test and isolated-node guard as threshold_cascade_sizes.
    need = (frac.numerator * k)[:, None]
    can = (k > 0)[:, None]
    den = frac.denominator

    out = {r: np.empty(n, dtype=np.int64) for r in radii}
    contained = {r: np.empty(n, dtype=bool) for r in radii}
    for start in range(0, n, batch_size):
        stop = min(n, start + batch_size)
        cols = np.arange(start, stop)
        diag = (cols, np.arange(stop - start))
        seed = a[:, cols].toarray().astype(bool)
        seed[diag] = True                              # column b is N[start + b]
        ball = np.zeros_like(seed)
        ball[diag] = True                              # B_0 = {i}
        reached = 0
        prev_ball = ball.copy()                        # B_{r-1}, for the distance-r shell
        for r in radii:
            # Grow the ball from radius `reached` to radius r, keeping the
            # radius r - 1 ball: the shell at distance exactly r is the
            # difference. At r = 0 the "shell" is {i} itself.
            for step in range(r - reached):
                if step == r - reached - 1:
                    prev_ball = ball.copy()
                ball = ball | ((a @ ball.astype(np.int64)) > 0)
            if r == 0:
                prev_ball = np.zeros_like(ball)
            reached = r
            # The cascade restarts from the seed at every radius rather than
            # continuing from the previous radius's fixed point. Continuing
            # would give the same answer (the process is monotone), but a
            # fresh start keeps each radius an independent computation that
            # the verifier can compare against the reference one at a time.
            s = seed.copy()
            while True:
                c = a @ s.astype(np.int64)
                new = s | ((den * c >= need) & can & ball)
                if np.array_equal(new, s):
                    break
                s = new
            out[r][start:stop] = s.sum(axis=0)
            shell = ball & ~prev_ball
            contained[r][start:stop] = ~(s & shell).any(axis=0)
    return (out, contained) if with_contained else out

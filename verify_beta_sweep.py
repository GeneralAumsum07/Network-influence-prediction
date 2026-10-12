"""
Pre-launch checks for Phase 6.5 L1 (prereg addendum 2026-10-12 12:15 IST, part E).

    python verify_beta_sweep.py

E1  S1/S2 recovered from a component-size matrix equal a direct
    connected_components count, including a tie for the largest component,
    a single spanning component, and all-singleton draws; a matrix that is
    not a percolation output is rejected.
E2  With a common seed, every node's cluster at a larger m contains its
    cluster at a smaller m, so S1 never shrinks draw by draw (the coupling the
    fine grid relies on).
E4  The r* rules and the verdict on synthetic sweep frames: a tie at the
    ceiling, sd = 0 with a positive gap, a flat series, a peak at an end
    multiple, an undetermined locator, the cv/resid exclusion below 1.25.
Plus the fail-closed guards: the locator refuses to overwrite itself, and
scoring refuses a network without a recorded locator.

E3 (cache bit-identity) needs the real caches and runs inside
`analyse_beta_sweep.py locator`, which refuses to record a locator if it fails.
E5 is the four project gates, run separately.

No fits, no network data; seconds to run.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components

import analyse_beta_sweep as ab
from influence.dynamics import simulate_ic_percolation
from influence.preprocessing import Network

FAIL: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label:62s} {detail}")
    if not ok:
        FAIL.append(label)


def graph(n: int, edges) -> Network:
    """A small undirected Network built the way preprocessing builds one."""
    r = [a for a, b in edges] + [b for a, b in edges]
    c = [b for a, b in edges] + [a for a, b in edges]
    a = sp.csr_matrix((np.ones(len(r)), (r, c)), shape=(n, n))
    a.sort_indices()
    nbrs = [a.indices[a.indptr[i]:a.indptr[i + 1]] for i in range(n)]
    return Network("fixture", a, nbrs, np.diff(a.indptr), np.arange(n))


def sizes_from_components(n: int, edges) -> np.ndarray:
    """One column exactly as simulate_ic_percolation writes it."""
    g = graph(n, edges).adj
    _, labels = connected_components(g, directed=False)
    return np.bincount(labels)[labels]


def e1() -> None:
    print("\n[E1] S1/S2 recovery from component sizes")
    cases = {
        # (n, live edges) -> expected (S1, S2)
        "tie for largest (3, 3, 1)": ((7, [(0, 1), (1, 2), (3, 4), (4, 5)]), (3, 3)),
        "distinct (4, 2, 1)": ((7, [(0, 1), (1, 2), (2, 3), (4, 5)]), (4, 2)),
        "one spanning component": ((5, [(0, 1), (1, 2), (2, 3), (3, 4)]), (5, 0)),
        "all singletons": ((4, []), (1, 1)),
    }
    cols = []
    for label, ((n, edges), want) in cases.items():
        col = sizes_from_components(n, edges)
        s1, s2 = ab.largest_two(col[:, None])
        check(f"E1 {label}", (int(s1[0]), int(s2[0])) == want, f"got {(int(s1[0]), int(s2[0]))}")
        cols.append(col)

    # Random graphs against a direct count of sorted component sizes.
    rng = np.random.default_rng(7)
    ok = True
    for _ in range(50):
        n = int(rng.integers(5, 40))
        edges = [(int(a), int(b)) for a, b in rng.integers(0, n, size=(n, 2)) if a != b]
        col = sizes_from_components(n, edges)
        _, labels = connected_components(graph(n, edges).adj, directed=False)
        comp = np.sort(np.bincount(labels))[::-1]
        want = (comp[0], comp[1] if len(comp) > 1 else 0)
        s1, s2 = ab.largest_two(col[:, None])
        ok &= (int(s1[0]), int(s2[0])) == (int(want[0]), int(want[1]))
    check("E1 50 random graphs match a direct component count", ok)

    # A column that cannot come from percolation (three nodes claiming size 2).
    try:
        ab.largest_two(np.array([[2], [2], [2]]))
        check("E1 non-percolation column rejected", False)
    except ValueError:
        check("E1 non-percolation column rejected", True)


def e2() -> None:
    print("\n[E2] coupling across m under a common seed")
    rng = np.random.default_rng(11)
    n = 60
    edges = list({(int(min(a, b)), int(max(a, b)))
                  for a, b in rng.integers(0, n, size=(150, 2)) if a != b})
    net = graph(n, edges)
    ps = (0.05, 0.12, 0.30, 0.55)
    runs = [simulate_ic_percolation(net, p=p, n_sims=200, convention="uniform",
                                    seed=0, verbose=False).sizes for p in ps]
    nested = all(np.all(b >= a) for a, b in zip(runs, runs[1:]))
    check("E2 every node's cluster is non-decreasing in p, draw by draw", nested)
    s1 = np.vstack([ab.largest_two(s)[0] for s in runs])
    check("E2 S1 non-decreasing in p for all 200 draws", bool(np.all(np.diff(s1, axis=0) >= 0)))
    # Control: different seeds are NOT coupled, so the test above can fail.
    other = simulate_ic_percolation(net, p=ps[1], n_sims=200, convention="uniform",
                                    seed=1, verbose=False).sizes
    check("E2 control: a different seed breaks the nesting", not np.all(other >= runs[0]))


def frame(taus: dict, target="spread_mean", tier=ab.PRIMARY_TIER) -> pd.DataFrame:
    """Synthetic sweep rows from {radius: [tau per seed]}."""
    rows = [{"target": target, "richness": tier, "radius": r, "seed": s, "kendall_tau": t}
            for r, ts in taus.items() for s, t in enumerate(ts)]
    return pd.DataFrame(rows)


def e4() -> None:
    print("\n[E4] r* rules and verdict on synthetic frames")
    noise = np.array([0.000, 0.004, -0.003, 0.002, -0.001, 0.003, -0.004, 0.001, 0.000, -0.002])

    # Clear horizon: r=0 and r=1 far below, r=2 within noise of r=3.
    f = frame({0: 0.50 + noise, 1: 0.70 + noise, 2: 0.899 + noise[::-1], 3: 0.900 + noise})
    res = ab.r_star_noise(ab.tau_table(f, "spread_mean", ab.PRIMARY_TIER))
    check("E4 horizon found inside the paired noise", res["r_star"] == 2 and res["r_ceiling"] == 3,
          f"r*={res['r_star']} r_c={res['r_ceiling']}")

    # Tie at the ceiling: r=2 and r=3 identical means -> r_c is the smaller.
    f = frame({0: 0.5 + noise, 1: 0.6 + noise, 2: 0.9 + noise, 3: 0.9 + noise})
    res = ab.r_star_noise(ab.tau_table(f, "spread_mean", ab.PRIMARY_TIER))
    check("E4 tie at the ceiling resolves to the smaller radius", res["r_ceiling"] == 2)

    # sd = 0 with a positive gap: r=2 is exactly 0.01 below r=3 on every seed,
    # so the gap is real and must NOT pass, even though "2 x 0" is the bar.
    f = frame({0: 0.5 + noise, 1: 0.6 + noise, 2: 0.89 + noise, 3: 0.90 + noise})
    res = ab.r_star_noise(ab.tau_table(f, "spread_mean", ab.PRIMARY_TIER))
    check("E4 sd = 0 with a positive gap does not qualify", res["r_star"] == 3,
          f"r*={res['r_star']}")

    # Paired vs unpaired: large common seed swings, tiny consistent gap. The
    # unpaired SD would pass r=2; the paired SD (0) must not.
    swing = np.linspace(-0.05, 0.05, 10)
    f = frame({0: 0.5 + swing, 1: 0.6 + swing, 2: 0.895 + swing, 3: 0.900 + swing})
    res = ab.r_star_noise(ab.tau_table(f, "spread_mean", ab.PRIMARY_TIER))
    check("E4 rule is paired (common seed swings do not hide a gap)", res["r_star"] == 3)

    # One seed only -> error, not a silent r*.
    try:
        ab.r_star_noise(ab.tau_table(frame({0: [0.5], 1: [0.6]}), "spread_mean", ab.PRIMARY_TIER))
        check("E4 fewer than 2 seeds rejected", False)
    except ValueError:
        check("E4 fewer than 2 seeds rejected", True)

    loc = {"determined": True, "m_loc": 1.25}
    v = ab.verdict({0.8: 2, 1.0: 2, 1.25: 2, 2.0: 2, 3.0: 2}, loc)
    check("E4 flat series -> flat, H1 not standing", v["flat"] and v["h1_stands"] is False)
    v = ab.verdict({0.8: 1, 1.0: 3, 1.25: 3, 2.0: 2, 3.0: 1}, loc)
    check("E4 plateau peak -> m_peak is its lowest multiple", v["m_peak"] == 1.0
          and v["prediction_met"] and v["h1_stands"] is True)
    v = ab.verdict({0.8: 1, 1.0: 1, 1.25: 2, 2.0: 2, 3.0: 3}, loc)
    check("E4 peak at the end multiple -> prediction not met, H1 not standing",
          v["m_peak"] == 3.0 and not v["prediction_met"] and v["h1_stands"] is False)
    v = ab.verdict({0.8: 1, 1.0: 3, 1.25: 2, 2.0: 2, 3.0: 1}, {"determined": False, "m_loc": None})
    check("E4 undetermined locator -> H1 not scored", v["h1_stands"] is None)
    v = ab.verdict({0.8: 1, 1.0: 3, 1.25: 2, 2.0: 2}, loc)
    check("E4 missing multiple -> no verdict", v["status"] == "incomplete")

    check("E4 locator boundary detection",
          ab.is_boundary(0.50) and ab.is_boundary(3.00) and not ab.is_boundary(1.05))
    check("E4 locator bin is the smallest sweep multiple at or above m*",
          ab.locator_bin(1.05) == 1.25 and ab.locator_bin(1.0) == 1.0 and ab.locator_bin(2.05) == 3.0)
    check("E4 tie rule for argmax takes the smaller m",
          ab.first_argmax([1, 3, 3, 2], [0.5, 0.55, 0.6, 0.65]) == 0.55)
    check("E4 cv/resid excluded below m = 1.25",
          ab.targets_for(1.0, {"spread_mean", "spread_cv", "spread_resid"}) == ["spread_mean"]
          and len(ab.targets_for(1.25, {"spread_mean", "spread_cv", "spread_resid"})) == 3)
    check("E4 fine grid: 51 points, exact 1.5, all sweep multiples on it",
          len(ab.FINE_GRID) == 51 and 1.5 in ab.FINE_GRID
          and all(m in ab.FINE_GRID for m in ab.SWEEP_MULTIPLES))
    check("E4 directory names", ab.mult_dir(1.0).name == "m1.00" and ab.mult_dir(1.25).name == "m1.25")


def guards() -> None:
    print("\n[guards] fail-closed behaviour")
    saved_out, saved_loc = ab.OUT, ab.LOCATOR_DIR
    with tempfile.TemporaryDirectory() as d:
        ab.OUT = Path(d)
        ab.LOCATOR_DIR = Path(d) / "locator"
        try:
            ab.LOCATOR_DIR.mkdir()
            (ab.LOCATOR_DIR / "ca-GrQc.json").write_text("{}")
            try:
                ab.run_locator("ca-GrQc")
                check("guard: locator refuses to overwrite a recorded one", False)
            except FileExistsError:
                check("guard: locator refuses to overwrite a recorded one", True)
            (ab.LOCATOR_DIR / "ca-GrQc.json").unlink()
            # No locator anywhere -> scoring writes nothing.
            ab.run_score()
            check("guard: scoring without a locator writes nothing",
                  not (Path(d) / "verdict.json").exists())
        finally:
            ab.OUT, ab.LOCATOR_DIR = saved_out, saved_loc


def main() -> int:
    print("=" * 78)
    print("verify_beta_sweep - Phase 6.5 L1 pre-launch checks (prereg part E)")
    print("=" * 78)
    e1(); e2(); e4(); guards()
    print()
    if FAIL:
        print(f"FAILURES ({len(FAIL)}):")
        for f in FAIL:
            print(f"   - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

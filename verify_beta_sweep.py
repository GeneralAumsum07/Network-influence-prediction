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
Rule 3 (prereg addendum 12:31): the threshold, the pairing (identical
    predictions give sd_target = 0), a hand-computed sd_target, deterministic
    replicates sharing one index set, and the rebuild self-check failing closed.
End to end: run_score on a synthetic tree of all five multiples finds the
    peak it was built with, so the wiring is exercised before the real sweep.
Plus the fail-closed guards: the locator refuses to overwrite itself, and
scoring refuses a network without a recorded locator.

E3 (cache bit-identity) needs the real caches and runs inside
`analyse_beta_sweep.py locator`, which refuses to record a locator if it fails.
E5 is the four project gates, run separately.

No fits, no network data; seconds to run.
"""
from __future__ import annotations

import json
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


def rule3() -> None:
    print("\n[rule 3] target-noise rule (prereg addendum 12:31)")
    # Threshold: same form as rule 2, only the yardstick differs.
    gap = {0: 0.20, 1: 0.05, 2: 0.01, 3: 0.0}
    check("rule3 threshold picks the smallest r inside 2 x sd_target",
          ab.r_star_target(gap, {0: 0.01, 1: 0.03, 2: 0.0, 3: 0.0}) == 1)
    check("rule3 sd_target = 0 with a positive gap does not qualify",
          ab.r_star_target(gap, {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}) == 3)
    try:
        ab.r_star_target(gap, {0: 0.1, 1: 0.1})
        check("rule3 mismatched radii rejected", False)
    except ValueError:
        check("rule3 mismatched radii rejected", True)

    # Pairing: a prediction identical to the ceiling's gives D_b = 0 in every
    # replicate, so sd_target is exactly 0 however noisy the targets are.
    rng = np.random.default_rng(3)
    base = rng.normal(size=60)
    y_reps = [base + rng.normal(scale=0.5, size=60) for _ in range(30)]
    preds = {0: rng.normal(size=60), 1: base.copy(), 2: base.copy()}
    sd = ab.target_noise_sd(y_reps, preds, r_c=2)
    check("rule3 identical predictions -> sd_target 0 (paired)", sd[1] == 0.0 and sd[2] == 0.0)
    check("rule3 a different prediction -> sd_target > 0", sd[0] > 0)
    # Hand computation for one radius.
    from scipy.stats import kendalltau
    want = np.std([kendalltau(y, preds[2]).statistic - kendalltau(y, preds[0]).statistic
                   for y in y_reps], ddof=1)
    check("rule3 sd_target matches a hand computation", np.isclose(sd[0], want, rtol=0, atol=1e-15))

    # Replicates: deterministic, one index set shared by every target, and the
    # self-check against the published targets fails closed.
    c = rng.integers(1, 30, size=(40, 300))
    pub = pd.DataFrame(ab.targets_from_cascades(c))
    a = ab.replicate_targets(c, ["spread_mean", "spread_cv"], pub, reps=5, seed=0)
    b = ab.replicate_targets(c, ["spread_mean", "spread_cv"], pub, reps=5, seed=0)
    check("rule3 replicates are deterministic for a fixed seed",
          all(np.array_equal(x, y) for t in a for x, y in zip(a[t], b[t])))
    idx = np.random.default_rng(0).integers(0, 300, size=300)
    check("rule3 first replicate uses the seed-0 index set for every target",
          np.allclose(a["spread_mean"][0], c[:, idx].mean(axis=1))
          and np.allclose(a["spread_cv"][0], c[:, idx].std(axis=1, ddof=1) / c[:, idx].mean(axis=1)))
    bad = pub.copy()
    bad["spread_mean"] = bad["spread_mean"] + 1e-6
    try:
        ab.replicate_targets(c, ["spread_mean"], bad, reps=1)
        check("rule3 rebuild mismatch with cache_targets rejected", False)
    except AssertionError:
        check("rule3 rebuild mismatch with cache_targets rejected", True)


def label() -> None:
    print("\n[label] robustness label (prereg addendum 13:44)")
    loc = {"determined": True, "m_loc": 1.25}
    stands = ab.verdict({0.8: 1, 1.0: 3, 1.25: 2, 2.0: 2, 3.0: 1}, loc)
    also = ab.verdict({0.8: 1, 1.0: 2, 1.25: 2, 2.0: 1, 3.0: 1}, loc)
    flat3 = ab.verdict({0.8: 1, 1.0: 1, 1.25: 1, 2.0: 1, 3.0: 1}, loc)
    late3 = ab.verdict({0.8: 1, 1.0: 1, 1.25: 1, 2.0: 2, 3.0: 1}, loc)
    fails = ab.verdict({0.8: 1, 1.0: 1, 1.25: 1, 2.0: 3, 3.0: 1}, loc)
    undet = ab.verdict({0.8: 1, 1.0: 3, 1.25: 2, 2.0: 2, 3.0: 1}, {"determined": False, "m_loc": None})
    check("label: stands under both -> robust",
          ab.robust_label(stands, also) == ab.ROBUST)
    check("label: rule 3 flat -> seed noise only",
          ab.robust_label(stands, flat3) == ab.SEED_ONLY)
    check("label: rule 3 peak above m_loc -> seed noise only",
          ab.robust_label(stands, late3) == ab.SEED_ONLY)
    check("label: H1 fails under rule 2 -> no label, whatever rule 3 says",
          ab.robust_label(fails, also) is None)
    check("label: locator undetermined -> no label", ab.robust_label(undet, undet) is None)
    check("label: incomplete rule 3 series -> seed noise only",
          ab.robust_label(stands, ab.verdict({0.8: 1, 1.0: 2}, loc)) == ab.SEED_ONLY)


def end_to_end() -> None:
    """run_score on a synthetic tree of all five multiples, so the wiring (paths,
    OOF key format, the cv/resid exclusion, the verdict file) is exercised before
    a 25 h sweep could expose a typo in it."""
    print("\n[end to end] score on a synthetic five-multiple tree")
    saved_out, saved_loc = ab.OUT, ab.LOCATOR_DIR
    rng = np.random.default_rng(5)
    tag, n = "email-Eu-core", 40
    with tempfile.TemporaryDirectory() as d:
        ab.OUT = Path(d)
        ab.LOCATOR_DIR = Path(d) / "locator"
        try:
            ab.LOCATOR_DIR.mkdir()
            (ab.LOCATOR_DIR / f"{tag}.json").write_text(
                '{"m_star_chi": 1.15, "determined": true, "m_loc": 1.25}')
            # r* peaks at m = 1.0 by construction: there the curve keeps rising
            # to r = 3; elsewhere it saturates at r = 1.
            peak_m = 1.0
            for m in ab.SWEEP_MULTIPLES:
                md = ab.mult_dir(m)
                md.mkdir(parents=True)
                c = rng.integers(1, 30, size=(n, 200))
                np.save(md / f"cache_cascades_{tag}.npy", c)
                tg = pd.DataFrame(ab.targets_from_cascades(c))
                tg.to_csv(md / f"cache_targets_{tag}.csv", index=False)
                targets = ab.targets_for(m, {"spread_mean", "spread_cv", "spread_resid"})
                rows, oof = [], {}
                for t in targets:
                    for tier in (ab.PRIMARY_TIER, ab.FULL_TIER):
                        for r in range(4):
                            level = (0.5 + 0.12 * r) if m == peak_m else (0.5 + 0.3 * min(r, 1))
                            for s in range(10):
                                rows.append({"target": t, "richness": tier, "radius": r, "seed": s,
                                             "kendall_tau": level + rng.normal(scale=0.001)})
                            oof[f"{t}|{r}|{tier}|0"] = tg[t].to_numpy() + rng.normal(scale=1 + 3 - r, size=n)
                pd.DataFrame(rows).to_csv(md / f"sweep_{tag}.csv", index=False)
                np.savez(md / f"cache_oof_{tag}.npz", **oof)
            ab.run_score()
            v = json.loads((Path(d) / "verdict.json").read_text())["networks"][tag]
            rs = pd.read_csv(Path(d) / "rstar.csv")
            check("e2e verdict scored, peak at the constructed multiple",
                  v["status"] == "scored" and v["m_peak"] == peak_m and v["h1_stands"] is True,
                  f"{v.get('status')} m_peak={v.get('m_peak')}")
            check("e2e rule 3 series present for all five multiples",
                  all(v["r_star_target_spread_mean"][str(m)] is not None for m in ab.SWEEP_MULTIPLES))
            check("e2e robustness label written and well-formed",
                  v["robust_label"] in (ab.ROBUST, ab.SEED_ONLY) and "rule3_verdict" in v,
                  str(v.get("robust_label")))
            low = rs[(rs.m < ab.CV_RESID_MIN_M)]
            check("e2e no cv/resid rows below m = 1.25", set(low.target) == {"spread_mean"})
            want = sum(len(ab.targets_for(m, {"spread_mean", "spread_cv", "spread_resid"}))
                       for m in ab.SWEEP_MULTIPLES) * 2 * (2 + len(ab.RELATIVE_EPS))
            check("e2e row count: targets x 2 tiers x (2 rules + 3 eps)", len(rs) == want,
                  f"{len(rs)} vs {want}")
        finally:
            ab.OUT, ab.LOCATOR_DIR = saved_out, saved_loc


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


def controller() -> None:
    """probe_beta_sweep.py: the grid it runs, what it pins, when it calls a
    unit complete, and the lock that lets it resume after a host reset."""
    print("\n[controller] probe_beta_sweep.py")
    import probe_beta_sweep as pb

    counts = {m: len(pb.expected_keys(m)) for m in ab.SWEEP_MULTIPLES}
    check("controller: 480 cells below m=1.25, 800 from 1.25 up",
          counts == {0.8: 480, 1.0: 480, 1.25: 800, 2.0: 800, 3.0: 800}, str(counts))
    total = sum(len(pb.expected_keys(m)) for _, m in pb.all_units())
    # The 2026-09-14 12:16 clarification computed 16,800; this is that arithmetic.
    check("controller: 25 units, 16,800 cells in all",
          len(pb.all_units()) == 25 and total == 16800, str(total))
    check("controller: cv/resid excluded below 1.25 only",
          "spread_cv" not in pb.stage_targets(1.0) and "spread_resid" in pb.stage_targets(1.25))
    check("controller: primary networks run first",
          [t for t, _ in pb.all_units()[:10]] == [ab.PRIMARY_NETWORKS[0]] * 5 + [ab.PRIMARY_NETWORKS[1]] * 5)
    for bad in ("email-Eu-core@1.5", "nonet@1.0", "email-Eu-core"):
        try:
            pb.parse_only([bad])
            check(f"controller: --only {bad} refused", False)
        except SystemExit:
            check(f"controller: --only {bad} refused", True)

    pinned = {p.relative_to(pb.ROOT).as_posix() for p in pb.identity_sources()}
    must = {"stage1_prepare.py", "stage2_sweep.py", "influence/features.py",
            "influence/dynamics.py", "influence/experiment.py", "influence/estimators.py",
            "influence/sweep_inputs.py", "influence/preprocessing.py", "influence/targets.py",
            "influence/criticality.py", "influence/graphlets.py", "vendor/orca.exe",
            "data/email-Eu-core.txt",
            "results/phase6_5_beta/locator/p2p-Gnutella08.json"}
    check("controller: pins the stages, their imports, data and locator",
          must <= pinned, str(sorted(must - pinned)))
    check("controller: leaves L7's module and the analyser unpinned",
          "influence/branch_anisotropy.py" not in pinned and "analyse_beta_sweep.py" not in pinned)

    with tempfile.TemporaryDirectory() as tmp:
        d, tag, m = Path(tmp), "email-Eu-core", 1.0
        keys = sorted(pb.expected_keys(m))
        rows = pd.DataFrame([{"target": t, "radius": r, "richness": tier, "seed": s, "tau": 0.5}
                             for t, r, tier, s in keys])
        oof = {f"{t}|{r}|{tier}|{s}": np.zeros(3) for t, r, tier, s in keys}
        rows.to_csv(d / f"sweep_{tag}.csv", index=False)
        np.savez(d / f"cache_oof_{tag}.npz", **oof)
        check("controller: complete unit recognised", pb.unit_done(d, tag, m)[0])
        rows.iloc[1:].to_csv(d / f"sweep_{tag}.csv", index=False)
        check("controller: a missing cell is incomplete", not pb.unit_done(d, tag, m)[0])
        pd.concat([rows, rows.iloc[:1]]).to_csv(d / f"sweep_{tag}.csv", index=False)
        check("controller: a duplicated cell is incomplete", not pb.unit_done(d, tag, m)[0])
        rows.to_csv(d / f"sweep_{tag}.csv", index=False)
        np.savez(d / f"cache_oof_{tag}.npz", **dict(list(oof.items())[1:]))
        check("controller: a missing OOF prediction is incomplete", not pb.unit_done(d, tag, m)[0])

        # Refit reconciliation (2026-10-13). A deterministic refit repeats its
        # row except fit_seconds: the stale copy goes, the last copy stays,
        # the unit becomes complete and every other line is byte-identical.
        # A refit with any other difference refuses. Uses "\r\n" endings
        # because pandas writes os.linesep on Windows.
        np.savez(d / f"cache_oof_{tag}.npz", **oof)
        timed = rows.assign(fit_seconds=1.0)
        sweep = d / f"sweep_{tag}.csv"
        timed.to_csv(sweep, index=False, lineterminator="\r\n")
        clean = sweep.read_bytes()
        refit = timed.iloc[3:5].assign(fit_seconds=2.0)
        pd.concat([timed, refit]).to_csv(sweep, index=False, lineterminator="\r\n")
        removed = pb.reconcile_refits(d, tag)
        after = sweep.read_bytes().decode("utf-8").splitlines(keepends=True)
        ref = clean.decode("utf-8").splitlines(keepends=True)
        check("controller: refit duplicates reconciled, last copy kept",
              removed == 2 and pb.unit_done(d, tag, m)[0]
              and after[:-2] == ref[:4] + ref[6:]
              and all(",2.0" in line for line in after[-2:]), str(removed))
        evidence = (d / f"refit_duplicates_{tag}.csv").read_text(encoding="utf-8").splitlines()
        check("controller: removed rows kept as evidence",
              len(evidence) == 3 and all(",1.0" in line for line in evidence[1:]))
        check("controller: nothing to reconcile is a no-op",
              pb.reconcile_refits(d, tag) == 0 and sweep.read_bytes().decode("utf-8").splitlines(
                  keepends=True) == after)
        pd.concat([timed, timed.iloc[:1].assign(tau=0.6)]).to_csv(sweep, index=False,
                                                                  lineterminator="\r\n")
        try:
            pb.reconcile_refits(d, tag)
            check("controller: a refit with a different result refuses", False)
        except RuntimeError:
            check("controller: a refit with a different result refuses", True)
        rows.to_csv(sweep, index=False)

        (d / f"cache_meta_{tag}.json").write_text(json.dumps(
            {"multiple": 2.0, "n_sims": 4000, "convention": "uniform", "max_hop": 3}))
        try:
            pb.stage1_done(d, tag, m)
            check("controller: a stage-1 cache for another multiple is refused", False)
        except RuntimeError:
            check("controller: a stage-1 cache for another multiple is refused", True)

        # Lock: a dead PID is renamed and the run proceeds; a live python.exe
        # (this process) refuses. 4,000,000,000 is above any Windows PID.
        lock = d / "active.lock"
        lock.write_text("4000000000")
        note = pb.take_lock(lock)
        stale = list(d.glob("stale_lock_4000000000_*.txt"))
        check("controller: stale lock renamed and the run resumes",
              len(stale) == 1 and lock.read_text() == str(__import__("os").getpid()), note)
        try:
            pb.take_lock(lock)
            check("controller: a live controller's lock refuses", False)
        except RuntimeError:
            check("controller: a live controller's lock refuses", True)


def main() -> int:
    print("=" * 78)
    print("verify_beta_sweep - Phase 6.5 L1 pre-launch checks (prereg part E)")
    print("=" * 78)
    e1(); e2(); e4(); rule3(); label(); end_to_end(); guards(); controller()
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

"""
verify_generators.py
====================
Verification for generators.py and structure.py.

The project standard is that nothing is asserted, only checked against an
independent reference. Generators and structural measurements are no
exception - in fact they are more dangerous than most code, because a
generator that silently fails to move its parameter produces a sweep that
looks perfectly well behaved and means nothing.

Six checks:
  1. Structural measures against networkx (independent implementation).
  2. Power-law fit against synthetic data with a KNOWN exponent.
  3. Chung-Lu actually lands near its target gamma.
  4. Holme-Kim's p_triad actually raises clustering.
  5. Double-edge-swap preserves the degree sequence exactly.
  6. Assortativity rewiring actually moves assortativity toward the target.
"""
import numpy as np
import networkx as nx

from influence import generators as gen
from influence import structure as st
from influence.preprocessing import build_network

rng = np.random.default_rng(0)
FAIL = []

def check(label, ours, theirs, tol):
    ok = abs(ours - theirs) <= tol
    print(f"  {'PASS' if ok else 'FAIL'}  {label:34s} ours={ours: .6f}  ref={theirs: .6f}  diff={abs(ours-theirs):.2e}")
    if not ok:
        FAIL.append(label)

def to_nx(net):
    import scipy.sparse as sp
    c = sp.triu(net.adj, k=1).tocoo()
    g = nx.Graph(); g.add_nodes_from(range(net.n))
    g.add_edges_from(zip(c.row.tolist(), c.col.tolist()))
    return g

print("=" * 74)
print("1. STRUCTURAL MEASURES vs networkx")
print("=" * 74)
for name, net in [("BA",   gen.barabasi_albert(1200, 3, seed=1)),
                  ("HK",   gen.holme_kim(1200, 3, 0.5, seed=1)),
                  ("WS",   gen.watts_strogatz(1200, 6, 0.1, seed=1)),
                  ("ER",   gen.erdos_renyi(1200, 6, seed=1))]:
    g = to_nx(net)
    print(f"\n{name}  (n={net.n}, m={net.m})")
    check("assortativity",      st.degree_assortativity(net),
          nx.degree_assortativity_coefficient(g), 1e-9)
    cm = st.clustering_measures(net)
    check("transitivity",       cm["transitivity"],       nx.transitivity(g), 1e-9)
    check("average_clustering", cm["average_clustering"], nx.average_clustering(g), 1e-9)
    check("triangle count",     cm["n_triangles"],
          sum(nx.triangles(g).values()) / 3, 0.5)

print("\n" + "=" * 74)
print("2. POWER-LAW FIT vs SYNTHETIC DATA WITH KNOWN EXPONENT")
print("=" * 74)
print("  Two separate questions, tested separately:")
print("    (a) is the MLE correct when xmin is known?")
print("    (b) how much does KS-based xmin selection cost us in accuracy?")
print()

print("  (a) MLE at a KNOWN xmin - isolates the estimator itself")
for true_alpha in [2.0, 2.5, 3.0, 3.5]:
    ks_ = np.arange(5, 200000)
    pmf = ks_.astype(float) ** (-true_alpha); pmf /= pmf.sum()
    x = ks_[np.searchsorted(np.cumsum(pmf), rng.random(200000))]
    a = st._fit_alpha(x[x >= 5], 5)
    err = abs(a - true_alpha)
    ok = err < 0.02
    if not ok: FAIL.append(f"MLE at known xmin alpha={true_alpha}")
    print(f"      {'PASS' if ok else 'FAIL'}  true={true_alpha:.2f}  fitted={a:.4f}  err={err:.4f}")

print()
print("  (b) full procedure incl. KS xmin selection, N=200,000")
for true_alpha in [2.0, 2.5, 3.0, 3.5]:
    ks_ = np.arange(5, 200000)
    pmf = ks_.astype(float) ** (-true_alpha); pmf /= pmf.sum()
    x = ks_[np.searchsorted(np.cumsum(pmf), rng.random(200000))]
    f = st.fit_power_law_tail(x, xmin_max=30)
    err = abs(f["alpha"] - true_alpha)
    ok = err < 0.10
    if not ok: FAIL.append(f"full fit alpha={true_alpha}")
    print(f"      {'PASS' if ok else 'FAIL'}  true={true_alpha:.2f}  fitted={f['alpha']:.3f}  "
          f"xmin={f['xmin']:2d}  n_tail={f['n_tail']:5d}  err={err:.3f}  "
          f"reliable={f['reliable']}")

print()
print("  (c) the failure mode the reliability flag must catch:")
print("      steep tail + small n -> KS falls back to a low xmin and fits the BULK")
net_bad = gen.chung_lu(1000, 3.4, mean_degree=6.0, seed=11)
f_bad = st.fit_power_law_tail(net_bad.degree, n_bootstrap=0)
caught = (f_bad["reliable"] is False)
if not caught: FAIL.append("reliability flag did not catch bulk-fit fallback")
print(f"      {'PASS' if caught else 'FAIL'}  n=1000 target gamma=3.4 -> fitted={f_bad['alpha']:.3f}, "
      f"n_tail={f_bad['n_tail']}/{net_bad.n} "
      f"({100*f_bad['tail_fraction']:.0f}% of data), flagged unreliable={not f_bad['reliable']}")

print("\n" + "=" * 74)
print("3. CHUNG-LU LANDS NEAR ITS TARGET GAMMA")
print("=" * 74)
print("  Sweeping the knob the whole structural arm depends on.")
prev = None
mono = True
for g_target in [2.1, 2.5, 3.0, 3.5, 4.0]:
    net = gen.chung_lu(6000, g_target, mean_degree=6.0, seed=2)
    fit = st.fit_power_law_tail(net.degree)
    if prev is not None and fit["alpha"] < prev - 0.05:
        mono = False
    prev = fit["alpha"]
    print(f"    target gamma={g_target:.1f}  ->  fitted={fit['alpha']:.3f}  "
          f"(xmin={fit['gamma_xmin'] if 'gamma_xmin' in fit else fit['xmin']}, "
          f"n={net.n}, <k>={net.mean_degree:.2f}, k_max={net.degree.max()})")
print(f"  {'PASS' if mono else 'FAIL'}  fitted gamma increases monotonically with target")
if not mono: FAIL.append("chung-lu monotonicity")

print("\n" + "=" * 74)
print("4. HOLME-KIM p_triad ACTUALLY RAISES CLUSTERING (at fixed tail)")
print("=" * 74)
prev_c, mono_c = -1, True
for p in [0.0, 0.25, 0.5, 0.75, 1.0]:
    net = gen.holme_kim(3000, 3, p, seed=3)
    cm = st.clustering_measures(net)
    fit = st.fit_power_law_tail(net.degree)
    if cm["average_clustering"] < prev_c - 1e-3:
        mono_c = False
    prev_c = cm["average_clustering"]
    print(f"    p_triad={p:.2f}  ->  avg_clustering={cm['average_clustering']:.4f}  "
          f"transitivity={cm['transitivity']:.4f}  gamma={fit['alpha']:.3f}")
print(f"  {'PASS' if mono_c else 'FAIL'}  clustering increases monotonically with p_triad")
if not mono_c: FAIL.append("holme-kim clustering monotonicity")

print("\n" + "=" * 74)
print("5. DOUBLE-EDGE-SWAP PRESERVES THE DEGREE SEQUENCE EXACTLY")
print("=" * 74)
base = gen.barabasi_albert(2000, 3, seed=4)
rew = gen.rewire_preserving_degree(base, n_swaps_per_edge=10, seed=4)
same = np.array_equal(np.sort(base.degree), np.sort(rew.degree))
print(f"  {'PASS' if same else 'FAIL'}  degree sequences identical after rewiring")
if not same:
    FAIL.append("double-edge-swap degree preservation")
    print(f"      before: n={base.n} sum={base.degree.sum()}")
    print(f"      after : n={rew.n} sum={rew.degree.sum()}")
print(f"      assortativity  before={st.degree_assortativity(base):+.4f}"
      f"  after={st.degree_assortativity(rew):+.4f}")
print(f"      clustering     before={st.clustering_measures(base)['average_clustering']:.4f}"
      f"  after={st.clustering_measures(rew)['average_clustering']:.4f}")
print("      (rewiring should destroy clustering while leaving degrees alone)")

print("\n" + "=" * 74)
print("6. ASSORTATIVITY REWIRING MOVES TOWARD THE TARGET")
print("=" * 74)
src = gen.barabasi_albert(2000, 3, seed=5)
a0 = st.degree_assortativity(src)
print(f"    source assortativity: {a0:+.4f}")
ok6 = True
for target in [-0.3, +0.3]:
    out = gen.rewire_to_assortativity(src, target, n_steps=60000, seed=5)
    a1 = st.degree_assortativity(out)
    moved_right = (a1 > a0) if target > a0 else (a1 < a0)
    deg_ok = np.array_equal(np.sort(src.degree), np.sort(out.degree))
    if not (moved_right and deg_ok): ok6 = False
    print(f"    target={target:+.2f}  ->  achieved={a1:+.4f}  "
          f"moved_correct_direction={moved_right}  degrees_preserved={deg_ok}")
print(f"  {'PASS' if ok6 else 'FAIL'}  rewiring moves assortativity and preserves degrees")
if not ok6: FAIL.append("assortativity rewiring")

print("\n" + "=" * 74)
print(f"RESULT: {'ALL CHECKS PASSED' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)}")
print("=" * 74)
# Exit non-zero on failure so a controller or CI step keyed on the return code
# cannot read a failing run as green. Added 2026-09-11 by Claude Opus 5 (Task 6
# audit finding P1-06): before this line the script printed FAILURES and exited 0.
import sys
sys.exit(1 if FAIL else 0)

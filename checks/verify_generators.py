"""
checks/verify_generators.py
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
  3. Chung-Lu: (a) its weights carry the target gamma, by exact MLE;
     (b) pooled fitted gamma of the graphs rises across the sweep.
  4. Holme-Kim's p_triad raises clustering by a minimum size, not just sign.
  5. Double-edge-swap preserves the degree sequence exactly.
  6. Assortativity rewiring actually moves assortativity toward the target.
"""
import _bootstrap  # noqa: F401 - repo root and script folders onto sys.path
import numpy as np
import networkx as nx
import scipy.sparse as sp

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

# ---------------------------------------------------------------------------
# Sections 3 and 4 were rewritten for D-11 (2026-11-16). Before, both asserted
# only tolerant monotonicity (a step down of up to 0.05 in gamma, 1e-3 in
# clustering, was allowed), so a generator that IGNORED its parameter - a
# constant series - passed both. Section 3 also ran on a single seed (2) that
# turned out to be one of the well-behaved draws: over seeds 0-7 the same
# single-graph fit missed the target by up to 1.8, twice because the tail fit
# fell back to the bulk (xmin=3, flagged reliable=False, flag never read here)
# and otherwise because ~60-120 tail nodes at n=6000 cannot pin gamma to
# better than a few tenths. So the knob and the graph are now tested apart:
#   3a  the knob itself: the weights are a Pareto draw times one constant, so
#       their exponent has a closed-form MLE with no fitter in the way;
#   3b  the graph: degrees pooled over four generator seeds, one CSN fit,
#       which must be reliable, rise strictly and span the sweep.
# Calibration (2026-11-16, recorded in the D-closure sidecar): 3a's worst
# |error| over seeds 0-7 at n=200,000 was 0.011; 3b's pooled fits over seeds
# 0-3 and 4-7 were all reliable and strictly rising, spans 1.87 and 2.31.
# ---------------------------------------------------------------------------
GAMMAS = [2.1, 2.5, 3.0, 3.5, 4.0]

print("\n" + "=" * 74)
print("3a. CHUNG-LU WEIGHTS CARRY THE TARGET GAMMA (exact MLE, no fitter)")
print("=" * 74)
# w = c * k_min * u^(-1/(gamma-1)), so w / min(w) is Pareto on [1, inf) and
# alpha_hat = 1 + m / sum(log(w / min(w))), standard error (alpha-1)/sqrt(m),
# about 0.007 at gamma 4 and m = 200,000. Weights clipped at the structural
# cap are censored, not Pareto draws, so they are left out (about 100 at
# gamma 2.1, none above 3.0). The band, 0.05, is ~5x the worst error seen
# over eight seeds; a generator that ignores gamma misses by 0.4 or more.
N_W, TOL_W = 200_000, 0.05
for g_target in GAMMAS:
    w = gen._powerlaw_weights(N_W, g_target, 6.0, 1, np.random.default_rng(5))
    capped = w == w.max()
    if capped.sum() == 1:                    # a single maximum is a draw, not the cap
        capped[:] = False
    x = w[~capped] / w.min()
    alpha = 1 + len(x) / np.log(x).sum()
    ok = abs(alpha - g_target) <= TOL_W
    print(f"  {'PASS' if ok else 'FAIL'}  target gamma={g_target:.1f}  weights MLE={alpha:.4f}  "
          f"|err|={abs(alpha - g_target):.4f}  (bar {TOL_W}, {int(capped.sum())} capped)")
    if not ok:
        FAIL.append(f"chung-lu weights exponent at gamma={g_target}")

print("\n" + "=" * 74)
print("3b. CHUNG-LU GRAPHS: POOLED FITTED GAMMA RISES ACROSS THE SWEEP")
print("=" * 74)
# Realised degrees, not weights: this catches a fault between the weights and
# the graph (e.g. chung_lu passing the wrong gamma on, or the edge sampler
# flattening the tail). No accuracy band: at n=6000 even the pooled fit sits
# up to ~0.5 from target (seeds 4-7 gave 4.47 at 4.0), and accuracy is 3a's
# job. What must hold: every pooled fit reliable, a strict rise at every step,
# and a span from the first to the last target of at least 1.0 (a constant
# series has span ~0; measured 1.87 here).
POOL_SEEDS, MIN_SPAN = (0, 1, 2, 3), 1.0
fits = []
for g_target in GAMMAS:
    nets = [gen.chung_lu(6000, g_target, mean_degree=6.0, seed=s) for s in POOL_SEEDS]
    fit = st.fit_power_law_tail(np.concatenate([net.degree for net in nets]))
    fits.append(fit)
    print(f"    target gamma={g_target:.1f}  ->  pooled fitted={fit['alpha']:.3f}  "
          f"(xmin={fit['xmin']}, n_tail={fit['n_tail']}, reliable={fit['reliable']}, "
          f"mean <k>={np.mean([net.mean_degree for net in nets]):.2f})")
alphas = [f["alpha"] for f in fits]
all_reliable = all(f["reliable"] for f in fits)
rising = all(b > a for a, b in zip(alphas, alphas[1:]))
span = alphas[-1] - alphas[0]
print(f"  {'PASS' if all_reliable else 'FAIL'}  every pooled fit is reliable")
print(f"  {'PASS' if rising else 'FAIL'}  pooled fitted gamma rises strictly at every step")
print(f"  {'PASS' if span >= MIN_SPAN else 'FAIL'}  span {span:.3f} >= {MIN_SPAN} from gamma {GAMMAS[0]} to {GAMMAS[-1]}")
if not all_reliable: FAIL.append("chung-lu pooled fit unreliable")
if not rising: FAIL.append("chung-lu pooled gamma not strictly rising")
if span < MIN_SPAN: FAIL.append("chung-lu pooled gamma span")

print("\n" + "=" * 74)
print("4. HOLME-KIM p_triad ACTUALLY RAISES CLUSTERING")
print("=" * 74)
# Clustering is tight across generator seeds (seeds 0-7, 2026-11-16: total
# rise 0.568 or more, every 0.25 step 0.120 or more), so one seed is enough,
# but the bars are now on SIZE, not just sign: a total rise of at least 0.4
# and every step at least 0.05. The old heading said "at fixed tail"; the
# tail is not fixed at n=3000 (fitted gamma varied by 0.09-0.51 across p_triad
# within a seed), so gamma is printed for information and not asserted.
MIN_RISE, MIN_STEP = 0.4, 0.05
cs = []
for p in [0.0, 0.25, 0.5, 0.75, 1.0]:
    net = gen.holme_kim(3000, 3, p, seed=3)
    cm = st.clustering_measures(net)
    fit = st.fit_power_law_tail(net.degree)
    cs.append(cm["average_clustering"])
    print(f"    p_triad={p:.2f}  ->  avg_clustering={cm['average_clustering']:.4f}  "
          f"transitivity={cm['transitivity']:.4f}  gamma={fit['alpha']:.3f} (not asserted)")
steps = np.diff(cs)
rise_ok = cs[-1] - cs[0] >= MIN_RISE
step_ok = bool((steps >= MIN_STEP).all())
print(f"  {'PASS' if rise_ok else 'FAIL'}  clustering rises {cs[-1] - cs[0]:.3f} >= {MIN_RISE} from p_triad 0 to 1")
print(f"  {'PASS' if step_ok else 'FAIL'}  every step rises >= {MIN_STEP} (smallest {steps.min():.3f})")
if not rise_ok: FAIL.append("holme-kim clustering rise")
if not step_ok: FAIL.append("holme-kim clustering step")

print("\n" + "=" * 74)
print("5. DOUBLE-EDGE-SWAP PRESERVES THE DEGREE SEQUENCE EXACTLY")
print("=" * 74)
base = gen.barabasi_albert(2000, 3, seed=4)
rew = gen.rewire_preserving_degree(base, n_swaps_per_edge=10, seed=4)
# NODE-WISE, not sorted (2026-11-15). A swap (a,b),(c,d) -> (a,d),(c,b) keeps
# each node's own degree, which is the stronger property the heading claims;
# comparing sorted arrays only checked the multiset, so a rewire that moved
# degree between nodes (or relabelled them) passed.
same = rew.n == base.n and np.array_equal(base.degree, rew.degree)
print(f"  {'PASS' if same else 'FAIL'}  every node's degree identical after rewiring")
if not same:
    FAIL.append("double-edge-swap degree preservation")
    print(f"      before: n={base.n} sum={base.degree.sum()}")
    print(f"      after : n={rew.n} sum={rew.degree.sum()}")
# ...and the rewire must have DONE something. Before 2026-11-15 this section
# only printed; a no-op "rewire" returning its input passed it.
edges = lambda net: set(zip(*np.nonzero(sp.triu(net.adj, k=1))))
kept = len(edges(base) & edges(rew)) / max(1, len(edges(base)))
c_before = st.clustering_measures(base)['average_clustering']
c_after = st.clustering_measures(rew)['average_clustering']
# 10 swaps per edge leaves ~e^-20 of edges by chance; 0.5 is a loose bound
# that only a broken or near-no-op swap can exceed. Clustering is printed but
# NOT asserted: a BA graph starts near random-graph clustering (~0.016 here),
# so "it fell" is a coin-flip under another seed, not a property of the swap.
changed = kept < 0.5
print(f"  {'PASS' if changed else 'FAIL'}  rewiring changed the graph "
      f"({kept:.1%} of edges kept; clustering {c_before:.4f} -> {c_after:.4f})")
if not changed:
    FAIL.append("double-edge-swap did not rewire")
print(f"      assortativity  before={st.degree_assortativity(base):+.4f}"
      f"  after={st.degree_assortativity(rew):+.4f}")

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
# cannot read a failing run as green. Added (Task 6
# audit finding P1-06): before this line the script printed FAILURES and exited 0.
import sys
sys.exit(1 if FAIL else 0)

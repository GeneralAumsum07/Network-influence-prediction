# Pre-registration — B1, sample efficiency

**Written 2026-09-03, before the run.** Append-only. Scored in a dated addendum
below, never by editing this section.

Supervisor directive 5, outstanding since July 2026. Un-gated 2026-08-28.

## The design

For each (network, target, radius, fraction, seed): 5-fold out-of-fold
predictions where the **test fold is always complete** and only the *training*
portion is subsampled to `fraction` of its rows.

    fractions   {0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00}
    networks    all five
    targets     all four
    radii       0,1,2,3
    richness    node+edge+subgraph (FULL) only
    seeds       10
    = 5,600 cells

**Why the test fold stays whole.** Shrinking it too would change the estimand:
τ would be computed over a different, smaller node set at each fraction and the
curve would confound "less training data" with "noisier measurement". Holding
the test fold fixed makes every fraction's τ an estimate of the same quantity,
so the differences are paired and interpretable.

**Why FULL only.** r\*(ε) is read off the richest structural tier, so that is
the tier the second question needs. Sweeping all four rungs would quadruple the
grid to answer a question nobody asked.

**Why the 100% arm is not wasted compute.** It must reproduce the published
`sweep_<tag>.csv` betweenness/spreading cells at FULL to within the documented
`n_jobs=-1` tolerance (~5e-08 in τ). A bespoke OOF loop that silently differs
from `out_of_fold_predictions` would put the difference into the measured
effect, which is the exact error `probe_objective_horizon.py` was written to
avoid. **If the 100% arm does not reproduce, the run is void.**

## Predictions

### P1 — the lab's ~20% claim
The lab's working assumption is that ~20% of labels recovers most of the
performance. Predicted: **τ at 20% is within 0.02 of τ at 100%** on the
spreading targets at r ≥ 1. Recorded as the claim under test; I have no
independent basis for it and it is the supervisor's number, not mine.

### P2 — the sharper, on-thesis question: does r\*(ε) shift?
From the plan (Rachit, 2026-08-28), recorded verbatim as the standing
prediction:

> scarcity pushes effective r\* *down* — deeper radii add features whose
> marginal signal is small relative to their added variance (ca-GrQc at 20%
> labels ≈ 665 training rows against 145 features at r=2).

Scored as: **modal r\*(ε) at 5% and 10% is ≤ modal r\*(ε) at 100%, in a
majority of (network, target, ε) cells, with no cell moving up by more than
one hop.**

### P3 — where the effect should be largest
Predicted: the downward shift is **largest on `betweenness` and smallest on
`spread_mean`**, because betweenness at deep radii is carried by a few
high-variance columns (Finding 10's conductance rung) whose estimates degrade
fastest as rows are removed.

### P4 — a stated risk to P2, declared now so it cannot be explained away later
There is a competing mechanism that predicts the **opposite** sign. Scarcity
raises variance everywhere, which lowers τ at *every* radius; if it lowers the
shallow radii proportionally more (they have fewer, cruder features and less
redundancy to average over), the *relative* ranking could favour deeper radii
and push r\* **up**. I do not know which dominates. **If r\* moves up, P2 is
falsified and gets reported as falsified** — the plan's prediction is a
hypothesis, not a conclusion, and this project's own record shows a headline
mechanism claim can be backwards (Finding 11's handicap direction, corrected
2026-09-03).

## Confounds to hold fixed

- **Fraction is applied to the training fold only**, after the KFold split, so
  the same seed still means one coherent draw (fold assignment + model
  randomness + subsample choice, all from the same integer).
- **The subsample is drawn uniformly at random, not stratified.** Betweenness
  is ~40–70% zeros on these networks, so a uniform 5% draw may contain very few
  nonzero nodes. That is a real property of label scarcity and stratifying it
  away would answer an easier question — but the **realised nonzero count must
  be logged per cell** so a collapse can be attributed rather than guessed at.
- **Small-fraction floor.** At 5% of a 4/5 training split, ca-GrQc gives ~166
  rows against 145 features at r=2. That is a genuinely underdetermined fit and
  its τ should be read as such, not as evidence about locality.

## Scoring rule

Fixed now: a shift counts only if modal r\* differs **and** the modal value's
per-seed support is ≥ 6/10 under both arms. A flip between two values that each
win 5/10 is noise, and this project has already published a case where the
modal r\* was stable while its support was not (ca-GrQc betweenness ε=0.01,
10/10 → 5/10 under log1p).

---

# ADDENDUM — scored outcome (2026-09-04)

Run complete: **5,600 / 5,600 cells**, 0 duplicates, 0 NaN, 4.38 CPU-hours of
fitting. Scored by `analyse_sample_efficiency.py` against the section above.

## Validity gate

The pre-registration said the run is **void** if the 100% arm does not
reproduce the published sweep. All **800** fraction=1.0 cells were compared
against `sweep_<tag>.csv` at FULL, on all five networks:

    worst |dtau| = 0.000e+00   (tolerance 5e-08)

Bit-identical, not merely within tolerance. The bespoke OOF loop **is** the
pipeline. The run stands.

## Verdicts

| # | prediction | verdict |
|---|---|---|
| P1 | tau at 20% within 0.02 of 100%, spreading targets, r ≥ 1 | **NOT MET — 29/45** |
| P2 | scarcity pushes r\* **down** | **FALSIFIED — moved UP on balance (20 vs 15)** |
| P3 | shift largest on betweenness, smallest on `spread_mean` | **MET** |
| P4 | competing mechanism, opposite sign, declared in advance | **P4's mechanism is the one that won on 2 of 4 targets** |

## P1 — the lab's ~20% claim is target-dependent, not simply wrong

| target | within 0.02 | mean drop at 20% |
|---|---|---|
| `spread_mean` | **15/15** | −0.0097 |
| `spread_cv` | 11/15 | −0.0157 |
| `spread_resid` | **3/15** | −0.0285 |

The supervisor's ~20% rule **holds cleanly for `spread_mean`** — every cell,
every network, every radius ≥ 1, at a cost under 0.01 τ. It degrades on
`spread_cv` and **fails on `spread_resid`** (worst cell −0.0441, email-Eu-core
r=2). So the honest answer to directive 5 is not "yes" or "no": the fraction of
labels you can drop depends on how hard the target is, and the claim was formed
on the easy one.

## P2 — falsified, and the aggregate verdict hides the real finding

20 cells moved UP against 15 DOWN, so the plan's standing prediction is
**falsified as stated**. P4 was declared precisely so this would be reported
rather than explained away, and this is that report.

But the aggregate is the wrong summary. Split by target, with email-Eu-core
excluded (see the floor caveat below), the separation is **total**:

| target | DOWN | UP | same |
|---|---|---|---|
| `betweenness` | **9** | **0** | 30 |
| `spread_mean` | 1 | 0 | 38 |
| `spread_cv` | 0 | **9** | 31 |
| `spread_resid` | 0 | **6** | 32 |

**Zero counterexamples in either direction.** `betweenness` and `spread_mean`
never move up; `spread_cv` and `spread_resid` never move down. Both declared
mechanisms are real and each owns a set of targets:

- **The plan's mechanism (P2) governs `betweenness`.** Deep radii there are
  carried by a few high-variance columns — Finding 10's conductance rung — whose
  estimates degrade fastest as rows are removed, so the deep advantage
  evaporates first and r\* falls. Predicted for exactly this reason, and
  confirmed on exactly the target it was reasoned about.
- **P4's mechanism governs `spread_cv` and `spread_resid`.** These are the hard
  targets (τ from 0.05 to 0.83). Scarcity lowers τ everywhere, but it lowers the
  shallow radii proportionally more — they have fewer, cruder features and less
  redundancy to average over — so the *relative* ranking tips toward the deeper
  radii and r\* rises.

**The direction of the sample-efficiency effect is a property of the target,
not of scarcity.** That is a better result than either prediction alone and it
was only visible because P4 forced the opposite sign to be scoreable.

Robustness — the verdict is not one network or one fraction:

    all scored cells          DOWN 15   UP 20   same 150
    excluding email-Eu-core   DOWN 10   UP 15   same 131
    fraction = 0.05 only      DOWN  9   UP 11   same  71
    fraction = 0.10 only      DOWN  6   UP  9   same  79

15 of 200 cells were dropped for support < 6/10 under the pre-registered rule.
No cell moved UP by more than one hop.

## P3 — MET, but read the mechanism, not the ranking

Mean signed shift (negative = downward): `betweenness` **−0.208**,
`spread_mean` −0.020, `spread_resid` +0.158, `spread_cv` +0.200. Betweenness is
the most negative and `spread_mean` is near zero, so P3 is met as written.

It is met for a partly different reason than imagined, and that should be said:
P3 assumed the shift was downward everywhere and asked only where it was
*largest*. In fact **betweenness is the only target that moves down at all**.

## The declared floor — a real limit on the 5% arm

The pre-registration warned that 5% of a 4/5 split is an underdetermined fit.
Measured, at r=3:

| network | train rows | features | rows/feature |
|---|---|---|---|
| ca-HepTh | 346 | 168 | 2.06 |
| p2p-Gnutella08 | 252 | 168 | 1.50 |
| ca-GrQc | 166 | 168 | **0.99** |
| facebook_combined | 162 | 168 | **0.96** |
| email-Eu-core | **39** | 168 | **0.23** |

Three of five networks have **no more rows than columns** at 5% and r=3;
email-Eu-core has four times as many columns as rows. Those fits are
underdetermined and will prefer a shallow radius for reasons unrelated to any
information horizon — which is why the robustness pass drops email, the network
most able to manufacture DOWN moves. Removing it *strengthens* the UP verdict,
so the falsification does not rest on it.

Realised nonzero betweenness labels at 5% (the non-stratified-sampling
confound, logged per cell as required): 32.9 of 39 rows on email-Eu-core, 74.5
of 166 on ca-GrQc. Label starvation is not what drives these cells — the
positive fraction survives subsampling roughly in proportion.

## What this does NOT license

The 5% arm is reported with the underdetermination caveat attached and should
not be quoted as a locality result on its own. The 10% and 20% arms carry the
weight. **Directive 5 is discharged**; the answer is target-dependent and the
supervisor's number is right only for `spread_mean`.

## Amendment 2026-10-07 — reproduction tolerance stated in pair units (post hoc)

Decided by Rachit after the post-orbit5-retag run failed the gate above. This is
a **post-hoc** change to a declared gate, recorded here so it is not mistaken for
the original declaration.

**What failed.** 799 of the 800 fraction=1.0 cells reproduced the published
sweeps bit-for-bit. One did not: p2p-Gnutella08 / betweenness / r=1 / seed 6,
|Δτ| = 5.039e-08 against the declared 5e-08.

**Why the declared number could not hold.** τ is a pair statistic; its smallest
possible change on an n-node graph is about 1/C(n,2). On p2p-Gnutella08
(6,299 nodes) that is 5.04e-08, already above 5e-08, so the flat tolerance
rejected even a single one-pair change there (1/C(n,2), which is exactly what was
observed; a pair moving between tied and ordered) — the `n_jobs=-1` effect the
"~5e-08" wording above was written to allow — while on ca-HepTh (2.7e-08 per
pair) it absorbed one. On the other three networks one pair exceeds 5e-08, so the
flat number silently meant "bit-identical".

**New rule.** Per network, tolerance = max(5e-08, 2 / C(n,2)): no fraction=1.0
cell may move by more than one swapped pair (a concordant↔discordant swap moves
C − D by 2). The flat 5e-08 stays as a floor, so no network is judged more
strictly than before. Implemented in `analyse_sample_efficiency.py`
(`tolerance()`), which now also prints how many cells are not bit-identical.
Result: PASS, with exactly the one p2p-Gnutella08 cell not bit-identical.

**Rejected alternatives.** Re-running the cell until it matched (re-rolling a
gate proves nothing); declaring the run void (discarding 5,600 sound cells over
one pair).

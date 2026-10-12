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

## Addendum 2026-10-12 — re-scored on the post-retag re-run

The scored outcome above (2026-09-04) was fitted before the 2026-09-11 orbit-radius
retag, which moved six 5-node node orbits and nine 5-node edge orbits from hop 1 to
hop 2. That changed the r=1 column set. The full 5,600-cell sweep was re-run on the
retagged registry and completed 2026-10-07. It passes the validity gate under the
amendment above: 799 of 800 fraction=1.0 cells are bit-identical, and one differs by
one pair-step. `analyse_sample_efficiency.py` re-scored it into
`results/RESULTS_sample_efficiency.txt`. The sections above are left as written; this
addendum supersedes their numbers, not their predictions.

| # | 2026-09-04 | re-run (2026-10-07) | verdict |
|---|---|---|---|
| P1 | 29/45 within 0.02 | **30/45** | NOT MET (unchanged) |
| P2 | 20 UP vs 15 DOWN | **21 UP vs 17 DOWN** | FALSIFIED (unchanged) |
| P3 | betweenness −0.208, `spread_mean` −0.020 | **−0.245, +0.040** | MET (unchanged) |

**P1 by target** (within 0.02 / mean drop at 20%): `spread_mean` **14/15**, −0.0109
(was 15/15, −0.0097); `spread_cv` 13/15, −0.0150 (was 11/15, −0.0157); `spread_resid`
3/15, −0.0288 (was 3/15, −0.0285). The one `spread_mean` miss is facebook_combined at
r=1 (−0.0347). The worst cell is now facebook_combined `spread_resid` at r=1 (−0.0720),
not email-Eu-core `spread_resid` at r=2 (now −0.0441, the second worst). "Holds cleanly
for `spread_mean` — every cell" no longer holds. The rule holds on 14 of 15 cells, and
the target-dependence verdict is unchanged.

**P2 split by target, email-Eu-core excluded** (DOWN / UP / same):

| target | 2026-09-04 | re-run |
|---|---|---|
| `betweenness` | 9 / 0 / 30 | **11 / 0 / 28** |
| `spread_mean` | 1 / 0 / 38 | **1 / 4 / 35** |
| `spread_cv` | 0 / 9 / 31 | 0 / 9 / 29 |
| `spread_resid` | 0 / 6 / 32 | 0 / 6 / 34 |

"Zero counterexamples in either direction" no longer holds for `spread_mean`. All four
of its UP moves are on facebook_combined, at fractions 0.05 and 0.10 and ε 0.05 and
0.02, each from a reference r\*=1 to a scarce r\*=2. Whether they come from the r=1
column change alone was not separately tested (TBC). The dissociation the addendum above
reports still holds on the three targets that move: `betweenness` never moves up, and
`spread_cv` and `spread_resid` never move down.

**Robustness** (DOWN / UP / same): all scored cells 17 / 21 / 148 (was 15 / 20 / 150);
email excluded 12 / 19 / 126 (was 10 / 15 / 131); fraction 0.05 only 10 / 12 / 71 (was
9 / 11 / 71); fraction 0.10 only 7 / 9 / 77 (was 6 / 9 / 79). 14 of 200 cells were
dropped for support < 6/10 (was 15). No cell moved UP by more than one hop. UP still
exceeds DOWN in every row.

**P3 mean signed shift:** `betweenness` −0.245, `spread_mean` +0.040, `spread_cv`
+0.170, `spread_resid` +0.150 (was −0.208, −0.020, +0.200, +0.158). Betweenness is
still the most negative, so P3 is met as written.

**Unchanged:** the declared-floor table (rows per feature at 5%, r=3) and the realised
nonzero betweenness labels at 5%. Both depend on row counts, not on columns.

The betweenness arm is still fitted with `make_rf` (raw squared error), not the
reported `rf_log1p` objective. Re-basing it would need a separate run (study §26d).

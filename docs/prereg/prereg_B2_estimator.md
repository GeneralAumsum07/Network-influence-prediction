# Pre-registration — B2, estimator invariance

**Written 2026-09-01, before any estimator sweep was run.**
**Author:** Rachit (with Claude)
**Answers review objection:** M4 (every number comes from one learner)
**Scripts that will test it:** `stage2_sweep.py <tag> <targets> 3 10 {ridge,hgb}`,
then `analyse_estimators.py` (not yet written at time of writing)

---

## Disclosure — what was already seen before this was written

The pre-registration discipline is worthless if the author has quietly seen the answer,
so: while smoke-testing that the new estimator factories run at all, **one cell was
scored**. ca-GrQc, betweenness, r=2, `node+edge+subgraph`, seed 0:

| estimator | τ | fit time |
|---|---|---|
| rf | 0.9220 | 7.6 s |
| ridge | 0.6389 | 1.1 s |
| hgb | 0.7213 | 8.7 s |

That is one cell, on one network, at one radius, on one seed. It fixes nothing about the
predictions below, all of which are about **differences** — between radii, between
richness rungs, and between networks — rather than about levels. But it does tell me in
advance that ridge is much weaker in level on ca-GrQc, and P3 is written knowing that.
No facebook cell, no r\*(ε), and no richness gain has been computed under any estimator
other than the random forest.

---

## Why this is pre-registered, and why it moved to the front of the queue

r\*(ε) is the project's headline quantity and it is claimed to be a property of the
**(network, target) pair**. Every number establishing it came from one random forest with
one set of hyperparameters. If the horizon moves when the learner changes, the thesis
sentence has to change with it.

The 2026-08-31 audit turned this from a completeness gap into a live threat to a specific
published finding. Finding 10's carrying feature, `local_conductance_2`, is **~99%
reconstructible** from columns already in the table (held-out R² ≈ +0.99 by two
protocols), and is nonetheless worth **+0.117 τ**. So what it buys is *accessibility, not
information*: a forest splitting on axis-aligned thresholds cannot form the ratio
cut/vol out of a dozen shell columns, and being handed the ratio directly is worth a
third of a hop.

An accessibility gain is exactly what a different inductive bias erases. A linear model
computes ratios for free in the space where they matter. Finding 10 is therefore the one
result in this project that has a **named, mechanistic reason to be estimator-specific**,
which is why it gets its own prediction below rather than being folded into a general
invariance check.

---

## What will be computed

Two additional full sweeps over all five networks, all four targets, 4 radii × 4 richness
rungs × 10 seeds, identical in every respect except the learner:

- **`ridge`** — `StandardScaler` → `RidgeCV(alphas=logspace(-3, 6, 40))`, the scaler
  fitted inside each fold. The scaler is not optional: the table spans four orders of
  magnitude and an unscaled ridge would measure our preprocessing rather than its
  inductive bias.
- **`hgb`** — `HistGradientBoostingRegressor(random_state=seed)`. A *second* non-linear
  learner, included so that a ridge-only failure can be attributed to non-linearity as
  such rather than to axis-aligned ensembling specifically.

Output goes to `estimators/sweep_<tag>__<est>.csv`, deliberately **not** beside the
baseline sweeps — `analyse.py::discover_networks` globs `sweep_*.csv` and would otherwise
discover `ca-GrQc__ridge` as a network.

r\*(ε) is computed **relative to each estimator's own ceiling**. A weaker learner is not
thereby a shorter-sighted one, and comparing a weak learner's absolute τ against a strong
learner's threshold would guarantee a spurious disagreement.

---

## Predictions

Numbered so they can be scored individually. Each states what would falsify it.

**P1 — Finding 10's subgraph rung largely disappears under ridge.**
On facebook_combined, betweenness, r=2, the paired gain from `node+edge` to
`node+edge+subgraph` is **+0.1291 ± 0.0043** under the random forest. Under ridge it will
be **below +0.040** — less than a third of the forest's value.
*Falsified by:* a ridge gain ≥ +0.040.
*Why:* if the gain is accessibility rather than information, the learner that can already
form ratios has nothing to gain from being handed one.

**P2 — but the rung does not go to zero, and may go negative.**
Ridge's gain will be small in magnitude (|gain| < 0.040 by P1) and its **sign is not
predicted**. Adding 64 columns to a penalised linear model on ~4,000 rows can cost
accuracy outright.
*Recorded so it cannot be spun:* a *negative* ridge gain is **P1-confirming**, not a
separate discovery, and must be reported as such.

**P3 — hgb sides with rf, not with ridge, on the same cell.**
The facebook subgraph gain under `hgb` will be **≥ +0.040**, i.e. it will land on the
forest's side of P1's threshold.
*Falsified by:* hgb below +0.040.
*Why it matters:* this is what separates "the gain requires non-linearity" (P3 confirmed)
from "the gain is specific to axis-aligned forests" (P3 falsified). Those are different
sentences in the write-up and I do not currently know which is true. **P3 is the
prediction I hold most weakly.**

**P4 — r\*(ε) agrees across estimators on the spreading targets.**
For `spread_mean` and `spread_cv`, at ε = 0.05, the modal r\*(ε) will agree between `rf`
and `hgb` on **at least 4 of the 5 networks each**, and between `rf` and `ridge` on at
least 3 of 5 each.
*Falsified by:* fewer agreements than that.
*Why the weaker bar for ridge:* ridge's P(r) curve may be flat enough that r\* is decided
by noise, which is itself a reportable outcome and is why per-seed stability is reported
beside every cell.

**P5 — betweenness is where invariance is most at risk.**
Any r\*(ε) disagreement will concentrate on `betweenness` rather than the spreading
targets. Concretely: the count of (network, estimator-pair) disagreements will be
**strictly higher for betweenness than for `spread_mean`**.
*Falsified by:* betweenness disagreeing no more often than `spread_mean`.
*Why:* betweenness is the target where the r=1→r=2 jump is largest and where the
zero-inflation structure (Finding 7) makes the ranking problem qualitatively unlike the
spreading targets.

**P6 — the shape of P(r) is far more invariant than its level.**
Spearman correlation between the `rf` and `hgb` P(r) curves (4 points, per network ×
target) will have **median ≥ 0.90** across the 20 pairs, despite large level differences.
For `rf` vs `ridge`, median ≥ 0.80.
*Falsified by:* medians below those bars.
*Why it matters:* P(r) shape is what r\*(ε) is read off. If shape is invariant while level
is not, "the horizon is a property of the pair, the achievable quality is a property of
the learner" is the honest and rather clean statement of the result.

---

## What each global outcome means

Written now so neither result can be spun later.

- **P1 confirmed, P4 and P6 confirmed:** the best available outcome and the one I expect.
  Finding 10 must be rewritten as an explicitly estimator-relative claim — "worth +0.117 τ
  *to a random forest*" — while r\*(ε) survives as an estimator-invariant quantity and the
  invariance figure becomes the paper's licence for the word *measured*. Note that this
  requires **editing a published finding**, and P1 being expected is not a reason to
  soften that edit.
- **P1 falsified (ridge also gains ≥ +0.040):** more interesting than it looks. It would
  mean the +0.117 is *not* pure accessibility, which contradicts the R² ≈ +0.99 result and
  demands an explanation neither the audit nor this document currently has. Do not paper
  over it; it would mean one of the two measurements is wrong.
- **P4 or P6 falsified:** the thesis sentence changes. r\*(ε) becomes "the horizon of *this
  estimator* on this pair", and the paper becomes an argument that radius must be reported
  jointly with the learner — publishable, but a different paper, and one that should be
  recognised early rather than at review.
- **Everything agrees perfectly, including ridge:** treat with suspicion before
  celebration. Check first that the ridge sweep is not silently degenerate (near-constant
  predictions make τ ≈ 0 at every radius, which would make r\* trivially 0 everywhere and
  look like agreement). The scored outcome must state the ridge ceiling per cell.

**No outcome licenses dropping the estimator axis.** Whichever way it falls, every future
r\*(ε) claim states which learner produced it.

---

## Recorded constraints

- The baseline `rf` sweep is **not re-run**. It is the existing `sweep_<tag>.csv`, which
  was repaired on 2026-09-01 (see `repair_column_order.py`) — 800 cells at r=2,3 in the
  two richest rungs had stale column ordering and were refitted. Any comparison below is
  against the repaired file, not the pre-repair one.
- Gains are **paired within seed**, as everywhere else in this project: the same seed's
  baseline and variant share a fold split. An unpaired comparison of a +0.03 effect is
  unreadable.
- `ridge`'s scaler is fitted inside each CV fold. Scaling the whole matrix once before
  splitting would leak the test fold's mean and variance, and this project does not get to
  publish a leakage critique and then commit one.
- The seed is passed to the estimator factory, so one `seed` continues to mean one
  coherent draw of variability — fold assignment *and* model randomness together — which
  is what the reported error bars are supposed to measure.
- P1's +0.040 threshold and P6's 0.90/0.80 bars were chosen **before** any relevant number
  was computed and **will not be moved** after the fact. The A2 pre-registration's P3 was
  scored as failed on a threshold its author judged badly chosen; the same rule applies
  here.

---

# ADDENDUM — scored outcome (append-only, 2026-09-01)

**Nothing above this line has been edited.** The predictions, thresholds and the
"what each global outcome means" section are exactly as written before the sweeps ran.
This addendum records what happened.

## Verdicts

| | verdict | measured |
|---|---|---|
| **P1** — subgraph rung largely disappears under ridge | CONFIRMED | −0.0016 ± 0.0066 |
| **P2** — rung does not go to zero, may go negative | CONFIRMED | as above |
| **P3** — `hgb` sides with `rf` | **FALSIFIED** | −0.0016 ± 0.0141 |
| **P4** — r\*(ε) agrees across estimators on spreading targets | CONFIRMED | on the bar, not above it |
| **P5** — betweenness is where invariance is most at risk | CONFIRMED | |
| **P6** — P(r) shape more invariant than level | CONFIRMED | median ρ hides a sign flip |

## The degeneracy check this document required

§"What each global outcome means" required that *"the scored outcome must state the ridge
ceiling per cell"*, because a near-constant ridge would make τ ≈ 0 at every radius and
produce fake agreement. **Ridge is not degenerate.** Ceiling (max τ over radii, richest
structural tier), against `rf` for reference:

| network | ridge btwn | rf btwn | ridge spread_mean | rf spread_mean |
|---|---|---|---|---|
| ca-GrQc | 0.6437 | 0.9241 | 0.9363 | 0.9448 |
| ca-HepTh | 0.7329 | 0.9168 | 0.9498 | 0.9511 |
| email-Eu-core | 0.7927 | 0.9079 | 0.9754 | 0.9692 |
| facebook_combined | 0.5735 | 0.8558 | 0.9201 | 0.9590 |
| p2p-Gnutella08 | 0.8601 | 0.9374 | 0.9030 | 0.9163 |

Ridge is a working learner everywhere — it *beats* `rf` on two spread_mean cells. The
suspicion case this document raised is ruled out.

## Three caveats that weaken the verdicts

**1. P3 was falsified on a confound.** The sweep compared `rf` at `min_samples_leaf=2`
against `hgb` at sklearn's default of **20**. That one parameter accounts for 68% of the
gap. **P3 stays falsified** — a post-hoc rerun does not un-falsify a pre-registered
prediction — but it did not measure inductive bias. The separately-declared follow-up is
`docs/archive/phase6_record.md#rec-posthoc_B2_hgb_capacity`. Note this is the same error this document explicitly
caught for ridge's scaler and then committed for hgb, because it hid inside a default.

**2. P1 is confirmed in outcome and wrong in mechanism.** This document reasoned that
ridge would lose the rung *because a linear model computes ratios for free*. Ridge does
lose it — but the ridge ceiling table above shows it is a working learner in general,
while at the facebook betweenness cell specifically it scores 0.0971 and **decays with
radius** (0.5445 → 0.1866 → 0.0956 → 0.1107). That is not "ratios for free"; it is the
loss/metric mismatch documented as Finding 11. The verdict stands; the stated mechanism
does not, and should not be repeated.

**3. P4 and P5 land exactly on their bars.** Neither has margin; either would flip on one
cell. Report as "consistent with", not "established".

## What was established

r\*(ε) agreement between `hgb` and `rf` is **17/20 cells**, and the horizon claim on the
**spreading targets** is estimator-stable within the pre-registered tolerance. That is the
licence this sweep was run to obtain, and for the spreading targets it was obtained. For
betweenness it was not.

## Open, and deliberately not guessed at

Whether r\*(ε) for betweenness moves under a **corrected training objective** is being
measured separately (`probe_objective_horizon.py`). Until that lands, no claim either way.

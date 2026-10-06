# A7 / N6 — target-noise bootstrap: record and pre-registration

**Written 2026-09-05.** Two arms, and they are recorded differently on purpose:
the first had already run when this file was created, the second had not.

---

## Arm 1 — frozen model. **Ran unregistered. Recorded honestly rather than backdated.**

**This arm has no dated pre-registration, because none was written before it ran.**
The project's convention is that a prediction is registered, dated, in the repo
*before* the corresponding run. That did not happen here, and this file does not
pretend otherwise.

What stands in for it is the plan's own stated expectation, written 2026-08-28,
long before the run — the 2026-08-28 work programme, item A7:

> "Bootstrap over live-edge sample indices (cascade arrays are cached), propagate
> to tau, and quote target-noise CIs **once** in an appendix to show seed noise
> dominates. **It probably does — show it rather than assert it.**"

That is a directional prediction with a date attached, and it is the closest
thing to a pre-registration this arm has. Treat it as weaker evidence than a real
one: it was written as an aside in a plan, not as a falsifiable declaration, and
it was not scored in advance.

### Result: **FALSIFIED.**

`probe_target_noise.py --reps 200`, richest tier, five networks × three Monte
Carlo targets × four radii = 60 cells. Output `results_target_noise.csv`.

| target | min ratio | median | max |
|---|---|---|---|
| `spread_cv` | 0.19 | **0.40** | 2.28 |
| `spread_mean` | 0.24 | **0.55** | 1.49 |
| `spread_resid` | 0.11 | **0.46** | 0.73 |

where ratio = seed sd ÷ target-noise sd. **Target noise exceeds seed noise on 55
of 60 cells.** The five exceptions are all at r=0, the shallowest and weakest
cells, where the model is poor enough that refit variability is comparatively
large.

Seed noise does **not** dominate. It is typically **half** the target noise, and
on `spread_resid` as little as a ninth.

### What this arm does NOT establish, and why arm 2 exists

The frozen design cannot sign its own bias. Two channels push in opposite
directions and it measures neither cleanly:

- **It omits the training channel** (a different target column would have trained
  a different model) — pushes its figure **down**.
- **It charges tau for realisation-mismatch.** The predictions are out-of-fold,
  so no node's own target leaked into its own prediction — but every *other*
  node's target did, and all of them share the same 4,000 live-edge samples. So
  realisation A's noise is baked into the fitted model, and re-scoring it against
  replicate B penalises tau for a mismatch that is not target noise as such —
  pushes its figure **up**.

An earlier draft of `probe_target_noise.py` called the frozen figure a lower
bound. That was wrong and has been corrected in the file. The honest description
is *"the movement in tau when the target is resampled and the model is not
allowed to react"* — a well-defined quantity, but not a bound in either
direction.

---

## Arm 2 — refit model. **Pre-registered 2026-09-05, before the run.**

**Scope decided by Rachit, 2026-09-05:** full refit across all cells, not a
single-cell spot-check.

**Design.** `probe_target_noise_refit.py`. Each replicate resamples the 4,000
live-edge sample indices, rebuilds the target, **refits** out-of-fold on that
target, and scores against that same replicate's target. The RF seed is held
fixed so the only thing varying is the target. Replicate index sets are
regenerated from the same RNG seed and call sequence as arm 1, so replicate *i*
is the **same resampled target** in both arms — the arms are paired, and their
difference isolates the refit channel rather than comparing two independently
noisy sds.

**Measured cost:** 15.8 s per 5-fold OOF refit on the worst cell (ca-HepTh,
n=8,638, 170 features). All 60 cells × 200 replicates would be ≈53 h. The run
checkpoints every (cell, replicate) to CSV and resumes, because this machine hard
power-cut twice during the B1 sweep.

### The predictions, stated before the run

**P1 — the frozen arm OVERSTATED target noise: `refit_over_frozen` < 1 on a
majority of cells.** Reasoning: the realisation-mismatch channel is real and
should be the larger of the two. The model is fitted against a target whose
noise is shared across all nodes; letting it re-fit to each replicate removes a
penalty that is an artefact of freezing, not a property of the target.

**P2 — the competing mechanism, declared in advance so an increase is reportable
rather than explained after the fact.** The training channel could dominate
instead: a random forest fitted to a noisier target realisation may make
genuinely worse splits, and that degradation would *not* appear in the frozen
arm at all. If `refit_over_frozen` > 1, P1 is wrong and this is why.

**P3 — the headline survives: target noise still exceeds seed noise
(`seed_over_refit` < 1) on a majority of cells, but by a smaller margin than arm
1's 0.40–0.55.** This is the prediction that matters for the appendix. If it
fails — if seed noise dominates once the model is free to adapt — then arm 1's
reversal was a frozen-design artefact and the plan's original expectation was
right after all.

**P4 — ordering by target is preserved: `spread_resid` remains the worst-affected
and `spread_mean` the least.** `spread_resid` is a residual of a residual and its
bin structure is recomputed per replicate, so it should stay the most sensitive.

### Scoring

Score P1–P4 against `results_target_noise_refit.csv` and append the outcome
below, dated, whatever it says. **Betweenness is excluded from both arms** — it
is computed exactly by Brandes and carries no Monte Carlo noise, so a bootstrap
over cascade samples cannot move it. Reporting a row of zeros for it would read
as a bug rather than as a fact about the estimator.

---

## Consequence for the write-up, independent of arm 2's outcome

The plan's phrasing — *"quote target-noise CIs once in an appendix to show seed
noise dominates"* — is no longer available. Arm 1 has already shown that on the
frozen design it does not, and arm 2 can only change the size of the effect or
its direction, not restore the original claim unexamined. Every existing error
bar in this project is a seed sd, and the corpus now has at least one measured
noise source that is larger. Where that changes a starred result, it has to be
said. **Which starred results it touches has not yet been checked** — that is the
next question after arm 2 scores, and it is a real one, not a formality.

---

## SCORED — 2026-09-06

Run complete: **60 cells × 200 replicates = 12,000 out-of-fold refits**, all cells
at full depth (the scorer refuses to run on a short cell, because a bootstrap sd
from 40 replicates instead of 200 would distort every ratio below while looking
perfectly plausible). Scoring script `score_a7_arm2.py`; per-cell output
`results_target_noise_scored.csv`.

| prediction | verdict |
|---|---|
| **P1** — frozen arm overstated target noise (`refit/frozen < 1` on a majority) | **FALSIFIED**, decisively — true on **2 of 60** cells |
| **P2** — the training channel dominates instead (`refit/frozen > 1`) | **SUPPORTED** |
| **P3a** — target noise still exceeds seed noise (`seed/refit < 1` on a majority) | **SUPPORTED** — 56 of 60 |
| **P3b** — …but by a *smaller* margin than arm 1 | **FALSIFIED** — the margin got **larger** on all three targets |
| **P4a** — the target ordering is preserved between arms | **SUPPORTED** — identical |
| **P4b** — that ordering is `spread_resid` worst, `spread_mean` least | **FALSIFIED**, and see the note below |

### P1 falsified, P2 confirmed: freezing the model *understated* target noise

`refit_over_frozen` has median **1.220** and range **0.973–2.344**; only two cells
(both `spread_cv`, one of them email at 0.993, i.e. a tie) fall below 1. By
target: `spread_cv` 1.299, `spread_resid` 1.252, `spread_mean` 1.165.

So the reasoning behind P1 was wrong about which channel is bigger. The
realisation-mismatch penalty is real, but **the training channel is larger**: a
random forest fitted to a noisier target realisation makes genuinely worse
splits, and that degradation is invisible to the frozen design because the
frozen design never refits. P2 named this mechanism in advance for exactly this
outcome, which is the only reason it can be reported as a result rather than as
a post-hoc explanation.

**Consequence: arm 1 was a lower bound after all** — but for the opposite reason
to the one originally written down, and the earlier draft that called it a lower
bound was right by accident, not by argument. The honest statement is that arm 1
could not sign its own bias, arm 2 signs it, and the sign is positive.

### P3: the headline strengthens rather than softens

`seed_over_refit < 1` on **56 of 60** cells. Median by target, arm 1 → arm 2:

| target | arm 1 (frozen) | arm 2 (refit) |
|---|---|---|
| `spread_cv` | 0.401 | **0.307** |
| `spread_resid` | 0.463 | **0.344** |
| `spread_mean` | 0.554 | **0.441** |

P3's majority clause holds. Its "smaller margin" clause fails in the opposite
direction: seed noise is now typically **a quarter to a half** of target noise
rather than a half. On `facebook_combined` `spread_cv` the ratio is 0.239 and on
`ca-HepTh` `spread_resid` 0.240 — seed noise there is roughly a **quarter** of
the noise in the target the model is being scored against.

### P4: the ordering is preserved, but the pre-registration misstated it

Both arms order the targets identically, worst-affected first:
`spread_cv` → `spread_resid` → `spread_mean`. Clause (i) is supported.

Clause (ii) named `spread_resid` as worst-affected. **That was already false of
arm 1**, whose published medians are `spread_cv` 0.401 < `spread_resid` 0.463 <
`spread_mean` 0.554. This is an error in the pre-registration — it misdescribed
an already-published result of its own — and not a falsified prediction about the
refit. Recording it as a bare "P4 FALSIFIED" would attribute the miss to arm 2,
which reproduced arm 1's ordering exactly.

The reasoning attached to clause (ii) (`spread_resid` is a residual of a residual
with a per-replicate bin structure, so it should be most sensitive) is a real
mechanism that is simply outranked: `spread_cv` is a ratio of two noisy
quantities, and dividing by an estimated mean is the more violent operation.

### What this settles, and what it does not

**Settled.** Every error bar in this project is a seed sd. The corpus now has a
measured noise source that is larger on 56 of 60 cells — by more, not less, once
the model is free to adapt. The bootstrap perturbs the column the sweep actually
trained against (the target columns are rebuilt from `cache_cascades_*.npy` and
the run **raises** unless all three reproduce `cache_targets_*.csv` exactly), so
this is not an artefact of a mismatched target.

**NOT settled, and still the next question.** *Which starred results this
touches has not been checked.* It is a real question, not a formality: stars are
awarded at "beats 2× paired seed sd", and a noise source larger than the seed sd
does not automatically invalidate a star — the two noises enter a comparison
differently, and target noise is **shared** across the radii being compared
within a cell, so much of it may cancel in a paired difference. Whether it does
is a measurement, and it has not been made. Nothing in `HANDOFF.md` §10 has been
downgraded on the strength of this run.

**`betweenness` remains excluded from both arms**, as pre-registered — exact by
Brandes, no Monte Carlo noise, and a row of zeros would read as a bug rather than
as a fact about the estimator.

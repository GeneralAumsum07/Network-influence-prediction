# Declaration — betweenness re-sweep under a corrected training objective

**Written 2026-09-03, before the run.** Append-only, per project convention.
Authorised by Rachit 2026-09-03 ("go ahead and re-sweep"), discharging the open
decision recorded in `HANDOFF.md` §14 and in the vault's `brain/Key Decisions.md`
(which currently reads "deferred" and must be amended once this lands).

## What is being run

`estimators/sweep_<tag>__rf_log1p.csv` for all five networks: **betweenness
only**, 4 radii × 4 richness rungs × 10 seeds = 160 cells per network, 800
total. Estimator `rf_log1p` = the pinned forest wrapped in
`TransformedTargetRegressor(func=log1p, inverse_func=expm1)`.

Tau is scored against the **untransformed** betweenness throughout. Kendall tau
is invariant to monotone transforms of the ground truth, so this changes what
the model optimises and not what it is judged against. It is a correction, not
a relaxation.

## Why betweenness only

Not a stylistic restriction — the other three targets are ineligible:

| target | obstacle | measured |
|---|---|---|
| `spread_resid` | **negative on all five networks**; log1p undefined/wrong | min −0.9364 (facebook) |
| `spread_cv` | **left**-skewed on p2p; log1p worsens conditioning | skew −0.96 |
| `spread_mean` | skew is low and the probe's control showed no effect | mean gain +0.0005 |

Applying a transform where it is not indicated is an intervention, not a
correction, and it would re-base 2,400 cells for no measured gain.

## What is ALREADY MEASURED — not to be re-presented as a prediction

`probe_objective_horizon.py` (2026-09-03) already ran both objectives at the
**FULL structural tier** (`node+edge+subgraph`), 5 networks × 4 radii × 10 seeds.
So the following are known facts going in, and the re-sweep must reproduce them:

- **Horizons.** r\*(ε) is read off FULL, so the horizon question is already
  answered: **3 of 50 (network × target × ε) cells moved — all betweenness, all
  facebook, all downward.** The re-sweep is not expected to add anything here.
- **The level effect is essentially a facebook effect.** Gains at FULL:

  | network | skew | r=0 | r=1 | r=2 | r=3 |
  |---|---|---|---|---|---|
  | facebook_combined | 28.88 | **+0.2906** | **+0.1870** | **+0.0983** | **+0.0793** |
  | email-Eu-core | 9.73 | +0.0402 | +0.0094 | +0.0084 | +0.0097 |
  | ca-GrQc | 6.15 | +0.0138 | +0.0020 | +0.0074 | +0.0070 |
  | ca-HepTh | 6.95 | −0.0000 | +0.0046 | +0.0040 | +0.0038 |
  | p2p-Gnutella08 | 4.77 | −0.0005 | +0.0007 | +0.0019 | +0.0020 |

  **State this limitation wherever the +0.18 headline is quoted.** The effect
  tracks skew, but the *magnitude* rests on the single extreme-skew network in
  the corpus. Four of five networks gain ≤ 0.04 anywhere and ≤ 0.01 at r ≥ 1.
  This is n=1 for the large effect and the project has already been burned once
  by reading a corpus-wide law off a facebook-only pattern (Finding 9's ego-net
  hypothesis) and once by an n=5 correlation (Finding 8).

- **One rung.** The facebook r=2 subgraph rung under a corrected objective was
  measured directly at **+0.0436** (vs +0.1291 published raw).

## What is genuinely new, and the predictions

Only the three richness rungs below FULL, and the top-k columns, are unmeasured.
Predictions, recorded before the run:

1. **The richness ladder compresses.** Because the handicap is largest where
   features are poorest (+0.2906 at r=0 → +0.0793 at r=3 on facebook), correcting
   the objective raises the poor rungs more than the rich ones. Predicted:
   **every facebook betweenness rung gain shrinks**, and the subgraph rung at
   r=2 lands near the +0.0436 already measured, not near +0.1291.
2. **The other four networks barely move.** Predicted: no rung gain on
   ca-GrQc, ca-HepTh, email-Eu-core or p2p changes by more than 0.02.
3. **Top-k is the open one — no prediction offered.** `precision_at_1pct` and
   `precision_at_5pct` have never been measured under a corrected objective, and
   I have no basis to guess the sign. Squared error over-weights exactly the
   huge-betweenness nodes that the top-k metric cares about, so it is entirely
   possible that **the correction helps bulk tau and hurts precision@1%**. If
   that happens it is a result, not a failure, and it must be reported rather
   than buried: it would mean the "corrected objective" is correct *for the
   metric this project reports* and wrong for the applied top-k question.

## Correctness checks

- **Harness, run before launch and PASSED.** `rf_log1p` through the registry
  reproduces the probe's log1p arm at FULL to `max|Δτ| = 1.11e-16` on four cells
  (ca-GrQc r1s0, facebook r2s0, facebook r2s3, p2p r3s1). If the two disagreed,
  the estimator would not be the thing the probe measured.
- **Output goes to `estimators/`**, never the repo root, or
  `analyse.py::discover_networks` discovers `ca-GrQc__rf_log1p` as a *network*
  and corrupts five consumers.
- **`sweep_<tag>.csv` is not touched.** The published raw-objective corpus stays
  on disk and stays inspectable, as the `hgb` files did.
- `verify_pipeline.py`, `verify_generators.py`, `verify_docs.py` must still pass
  afterwards — `verify_docs.py` specifically, as the check that the subdirectory
  discipline was honoured.

## What this does NOT license

The published corpus is **not** re-based by this run. `sweep_*.csv` remains the
project's primary result and every betweenness τ in it remains a
squared-error-objective number. Whether `rf_log1p` becomes the reported default
is a separate decision, and it is Rachit's; this run produces the evidence for
it. Until that decision is taken, the qualifier recorded in §14 stands: **every
published betweenness τ is quoted "under a squared-error objective."**

---

# ADDENDUM — scored outcome (2026-09-04)

Run complete: 800/800 cells, 0 duplicates, 0 NaN, five files in `estimators/`.
Scored by `analyse_objective_resweep.py` against the declaration above.

## Verdicts

| # | prediction | verdict |
|---|---|---|
| P1 | every facebook rung gain shrinks | **NOT MET — 6/8 shrank, 2 grew** |
| P1b | facebook r=2 subgraph rung lands near +0.0436 | **MET exactly (+0.0436, agreement 0.0000)** |
| P2 | other four networks move < 0.02 | **MET — 0 of 32 rungs exceed it** |
| P3 | top-k: no prediction offered | **RESOLVED — no measurable harm** |

## P1b — the headline, triangulated

    facebook betweenness r=2, subgraph rung
      published (squared-error objective)   +0.1291
      corrected (log1p objective)           +0.0436

This reproduces the independently measured +0.0436 to four decimals, from a
different code path (full sweep vs single-cell probe). Together with the
capacity-matched HGB arm's +0.0555 — a correction of an unrelated kind — three
routes now put the honest rung near **+0.05, not +0.13**.

## P1 — where it failed, and why that matters

Two facebook rungs GREW under the correction, both at r=1:

    r=1 edge       -0.0097*  ->  +0.0158*     sign flip, both starred
    r=1 subgraph   +0.0000   ->  +0.0074*     null -> starred

The first is the substantive one. Under the published objective the edge tier at
r=1 on facebook **significantly hurt** — adding edge features made the ranking
worse. Under a correctly-conditioned objective it significantly helps. So that
negative rung was an artefact of the training objective, not a property of the
features, and any reading of it as "edge features are harmful at short radius on
dense graphs" is withdrawn.

This falsifies the compression story as stated. The handicap does shrink with
feature richness on average, but "every rung shrinks" was too strong: where the
raw objective produced a *negative* gain, correcting it moves the rung UP. The
mechanism is about the sign of the handicap's effect on each tier, not a uniform
contraction, and the declaration's P1 overreached.

## P3 — the open question, resolved: no measurable top-k harm

The declaration flagged that the correction might help bulk τ and hurt
`precision_at_1pct`, and refused to guess. Measured, paired within seed at the
richest tier, against the project's |mean| > 2·sd bar:

    significant tau changes                                 18/20
    significant p@1 changes                                  1/20  (positive)
    cells with tau significantly UP and p@1 significantly DOWN   0/20

Five cells show the pattern in the raw means (ca-GrQc r=2/r=3, ca-HepTh
r=1/r=3, facebook r=2), but none survives the error bars: p@1 seed-to-seed sd
runs 0.01–0.07, an order of magnitude above the shifts. `precision_at_1pct` is
also coarse by construction — 1% of ca-GrQc's ~4,158 nodes is ~41 nodes, so one
node is ~0.024, larger than every apparent decline.

**Conclusion: the objective correction does not measurably damage top-k.** The
concern was real enough to declare and is not supported by the data. Stated as a
null with its power caveat: this rules out an effect of the size the means
suggested, not an effect of any size.

## Scope limitation, restated

The corpus-wide picture is unchanged by the re-sweep and must travel with every
quotation of the headline: **the objective correction is essentially a facebook
effect.** 0 of 32 rungs on the other four networks moved by more than 0.02. The
+0.18 τ headline rests on the single extreme-skew network (28.88 vs 4.77–9.73).

## Status of the published corpus

`sweep_*.csv` is **not** re-based. Every betweenness τ in it remains a
squared-error-objective number and the §14 qualifier still stands. Whether
`rf_log1p` becomes the reported default is Rachit's decision; this run is the
evidence for it, not the execution of it.

---

# ADDENDUM 2 — the open decision was taken (2026-09-04)

The section "What this does NOT license" above, and the closing "Status of the
published corpus", both recorded that the corpus was **not** re-based and that
adoption was Rachit's separate decision. **That decision was taken on
2026-09-04: adopt, for betweenness only.** Both paragraphs are superseded; they
are left in place because this file is append-only and because what the project
believed before a decision is part of the record.

**Implementation.** `sweep_<tag>.csv` is still not rewritten. `analyse.load()`
splices the `estimators/sweep_<tag>__rf_log1p.csv` betweenness rows in at read
time; `load(tag, raw=True)` returns the superseded arm for comparison work.
`analyse_estimators.py` is pinned to `raw=True` — `ridge` and `hgb` were fitted
under squared error, so the default there would confound estimator with
objective.

**Guarded, not asserted.** `verify_pipeline.py` section N9 checks on every run
that the log1p file exists for all five networks, that the spreading targets
pass through at `|dτ| = 0.000e+00`, that betweenness actually moves (so a
missing file cannot silently revert the correction), and that the estimator
comparison stays in the raw arm.

**Effect, measured through the spliced loader.** The FULL-tier gains reproduce
this declaration's own pre-run table exactly, now from a third code path. The
horizon moves in **3 of 25** betweenness r\*(ε) cells — all facebook_combined,
all downward — matching `probe_objective_horizon.py`.

**The n=1 scope limitation is NOT discharged by adoption** and still travels
with every quotation of the headline magnitude.

# C4 — two-number reporting protocol for learned betweenness

*Draft protocol. Started 2026-09-07; bounded steps (1)-(3) delivered the same day. See
**Status** below for exactly what is and is not claimed.*

This follows the scored C3 result in [study §26i](../study_doc_v2.md#26i-c3--external-benchmark-levels-and-the-two-tie-regimes-2026-09-06)
and the [binding C3 registration](../prereg/prereg_C3_benchmark_inflation.md). C3 is scored;
this draft introduces no replacement test or retrospective threshold change.

**Credit.** BRAVA-GNN already computes and ships nonzero-subset Kendall τ. Its
implementation makes C3 possible and demonstrates the practical availability of the
second number. The proposal is to report both tasks explicitly, with enough metadata
to interpret them, rather than introduce a supposedly new filtered metric.

## What this protocol is for

**The problem.** A learned betweenness estimator is doing two different jobs at once, and
the field reports them as one number. The first job is deciding which nodes have zero
betweenness — on the graphs in C3's corpus that is between 4% and 96% of all nodes, and it
is exactly solvable from each node's radius-1 neighbourhood without learning anything. The
second job is ranking the nodes that remain, which is the hard one. A single all-node
Kendall τ mixes them, and the mixing weight is a property of the graph rather than of the
method: C3 measured the per-graph median **drop** `τ_all − τ_filtered` correlating with
the zero fraction `z` across 14 graphs at Spearman ρ = 0.890. This measures the association
of filtering's effect with support, not the correlation of all-node τ itself with `z`.

**The proposal.** Report the two jobs separately, with enough metadata to interpret each.
Nothing here is a new metric. The nonzero-subset τ is already computed and shipped by
BRAVA-GNN; a method that produces zero scores can explicitly declare how those scores
become a zero decision, but the numerical scores alone do not establish that declaration.
The proposal is to publish both, and to declare the zero decision rather than leave it
implicit in a score array.

**Who this is for.** Authors releasing a betweenness-estimation benchmark or method, and
reviewers deciding what a reported τ establishes. It is written against a concrete corpus:
every claim about what is and is not currently reported is a measurement on BRAVA-GNN's
released artefacts, recorded in Finding C4-1 below.

**What it is not.** It is not a claim that any published method is bad, and not a claim
that method rankings change under it. C3 checked that: configuration ordering largely
survives filtering (τ 0.87–0.999 between all-node and filtered orderings). The claim is
about what a published *level* means, not about who wins.

## The two primary numbers

Use the same held-out nodes and predictions for both measurements. Write reference
betweenness as y, predicted score as s and the declared predicted-zero decision as Ẑ.
Do not retrain a model or select a cutoff on the test set to produce this report.

| Number | Definition | What it answers |
|---|---|---|
| Zero-set classification accuracy | `mean(Ẑ == (y == 0))` over all evaluated nodes | Does the declared predictor identify the solved zero-set subproblem? |
| Nonzero-subset Kendall τ-b | `kendalltau(s[y > 0], y[y > 0], variant='b')` | How well are genuinely positive reference nodes ranked? |

The second number filters by **reference truth only**, never by predicted positivity
or by the intersection of correct predictions. A positive node assigned a zero score
stays in this ranking test. Otherwise classification mistakes would disappear from
both measurements and reward a method for omitting difficult nodes.

Accuracy alone is prevalence-sensitive. Accompany it with the zero and positive
class counts and the full 2×2 confusion counts, with the zero class explicitly labelled.
Report false-zero and missed-zero rates where denominators are nonzero; use NA when
a class is absent. These are required audit metadata, not a substitute third headline.
Keep all-node τ-b as a supplementary continuity measure so older reports remain readable.

## Declare how a continuous score becomes a zero decision

The local certificate identifies zero betweenness exactly for the simple, unweighted,
endpoint-excluding graph conventions used here. For undirected graphs this is the
simplicial-neighbourhood rule; for directed graphs it is the predecessor/successor
shortcut rule registered in C3. Its graph regime and available radius-1 information
must match the evaluation task.

An estimator may report either an explicitly implemented certificate/mask or a score
cutoff chosen before test evaluation. Record which it uses. If a cutoff is calibrated,
record the validation split and selection rule; the test labels cannot select it.
This draft does not prescribe a universal numeric cutoff for arbitrary score scales.

Do not label an auxiliary exact certificate as the learned predictor's accuracy.
If the predictor exposes no zero decision and no predeclared cutoff exists, its first
number is **not reported**, with that reason. An auxiliary certificate may be shown
separately, clearly named. This prevents an automatic 1.0 from concealing mistakes in
the scores actually evaluated. Adding a mask changes the evaluated method and must
be declared as such.

## Support, tie and provenance metadata

Every report row should carry the following fields beside the two numbers:

| Field | Required content |
|---|---|
| Evaluation identity | Graph/version, regime, node set, preprocessing, component policy, method/configuration and seed or source-row occurrence |
| Target convention | Directed/undirected, weighted/unweighted, endpoints, normalisation, exact/sampled/quantised target, source and checksum |
| Support | n, number of reference zeros and positives, reference zero fraction z; structural zero count separately if available |
| Zero decision | Certificate or predeclared cutoff, provenance of cutoff selection, confusion counts |
| Primary metrics | Zero-set accuracy and reference-positive-only τ-b; NA reason if unavailable/undefined |
| Tie evidence | Number of prediction-tied pairs within reference zeros, within positives and across the boundary; reference positive-block ties |
| Supplementary metrics | All-node τ-b, all-minus-nonzero drop; any zero-skill reference labelled by its assumptions |
| Uncertainty | Per-run values and declared aggregation; seed variability labelled as seed variability, not total uncertainty |

Use the **shipped reference support** when reproducing an existing benchmark's filter.
If structural zeros disagree, publish both counts and explain the direction of the
discrepancies. For C3's cit-Patents and com-lj, the shipped zero counts are 709,724 and
1,151,702, whereas the structural counts are 709,062 and 1,150,616. A replication
using structural support would measure a different positive-only column. Do not round
tiny positive values into zeros during reporting or silently equate quantised targets
with exact betweenness.

If only aggregate τ columns are available, do not infer classification accuracy or
prediction ties from their values. BRAVA's paired CSV supports C3's second metric and
its level comparison; it does not alone supply a complete two-number report.

## A reference depends on prediction ties

With perfect zero/positive separation and no additional positive-block ties, the
zero-within-positive-skill reference is w for predictions tied on the zero block,
and `w sqrt(S/T)` for continuous predictions, where `T = C(n,2)` and
`S = T − C(n_z,2)`. The familiar `w sqrt(1−z²)` is the large-n geometric expression.
Real positive-block ties or boundary errors require the actual pair accounting.

Call this a **zero-skill reference**, not a universal lower bound. A method can rank
positives negatively and fall below it. Neither an algorithm-name prefix nor a good
median mixture fit establishes every row's tie regime. C3's `baseline_random_*`
exceptions are a concrete reason to require this metadata.

## Degenerate cases and aggregation

If fewer than two reference-positive nodes remain, or either positive-only vector is
constant, report τ-b as NA with its reason. Do not convert undefined τ to zero or omit
the row from the support table. Record finite-row counts when aggregating.

Report per-graph values before any across-graph summary. Repeated seeds and repeated
source labels need stable identifiers; do not collapse distinct observations merely
because their displayed names match. If a graph-level median is used, state which
observations enter it. The C3 corpus has 395 names but 404 paired row occurrences.

Where uncertainty is estimated, keep the sources distinct: model-seed variation,
target approximation/noise, and sampling of evaluation nodes. A node bootstrap does
not automatically provide an independence-valid interval on a network. The project's
A7 result already shows why seed error bars cannot stand for every uncertainty source.

## Finding C4-1 — the metadata this protocol requires is absent from every method in a full published benchmark

*Established 2026-09-07 by inventory of the cloned BRAVA-GNN repository and the downloaded
14-graph corpus. Numbered within this document; `docs/study_doc_v2.md` runs its own Finding
sequence to 13, and folding this in there is a separate edit, not implied by this label.*

This document argues in §"Declare how a continuous score becomes a zero decision" and
§"A reference depends on prediction ties" that an aggregate Kendall τ column cannot supply
either a zero decision or tie evidence. The inventory tests that argument against the **released artefacts of** a complete
published benchmark and finds the metadata missing for **every method, on every graph**. The
claim is scoped to what was inspected: these files do not carry it. That is not proof no such
arrays exist anywhere, only that none were published.

| Artefact | Contents | Zero decision? | Tie evidence? |
|---|---|---|---|
| `results/betweenness/all_results.csv` | **846 × 15** (algorithm column + 14 graphs), **one aggregate τ per cell** | No | No |
| `all_results_topk / flops / wallclock / training_time.csv` | aggregate; **939×15, 405×15, 472×15, 412×2** — *not* the same shape as each other (corrected 2026-09-07) | No | No |
| ABCDE `<graph>-score.txt` (5 graphs) | per-node **ground-truth** BC | For the target only, for no method | No |
| `baselines/abcde/*.ckpt`, `drbc.ckpt`, `seeds/best_S*.ckpt` | model weights | Only by executing the model | Only by executing the model |

The scope of the gap is worth stating precisely, because it includes the one repository that
made C3 possible at all. **BRAVA-GNN computes and ships the nonzero-subset τ** — the metric whose
availability is the entire reason the C3 re-analysis could be done without retraining anything —
and it still ships no per-node predictions, no declared zero decision and no tie evidence. If the
most transparent release in the corpus does not carry this metadata, no third party can
reconstruct the two primary numbers for any published method after the fact.

**This is a release-discipline gap, not a feasibility limit, and the distinction is the finding.**
The capability is already implemented in the codebase: `betweenness.py:17 _dump_predictions`
writes per-node `pred_bc` and `true_bc` arrays (alongside in- and out-degree) to a compressed
`.npz`. It is gated behind an opt-in `--dump_predictions` flag at inference time, and that flag
was not exercised for the shipped release. **The mechanism exists; the artefact was not
published.** Nothing about betweenness estimation, graph scale, or the metric makes this
information expensive to emit — one array per method per graph, written by code that is already
in the repository. What is missing is the convention of emitting it.

**Recommendation for future benchmark releases.** Ship per-node prediction arrays and a declared
zero decision by default, alongside the aggregate table. Both are cheap next to the compute
already spent producing the scores, and together they are what allows a published number to be
audited, decomposed, or reused by anyone who did not run the experiment. The nonzero-subset τ
that BRAVA-GNN already ships is precisely the kind of low-cost addition that made an external
re-analysis possible; per-node arrays and a stated zero decision would extend that same courtesy
to the questions this protocol raises.

---

## Status

Delivered 2026-09-07, each under its own name and with its own evidential weight:

| Piece | Where it lives | What it establishes |
|---|---|---|
| Support and zero-count reconciliation audit | `audit_c4_support.py`, `results_c4_support_audit.csv`, and **Support and zero-count reconciliation audit** below | The protocol's support and identifier machinery exercised against real external artefacts |
| Reporting implementation | `c4_two_numbers.py`, pinned by `verify_pipeline.py` **N12**, and **Implementation and internal code-correctness check** below | That the protocol is implementable and the implementation is correct |
| Cutoff predeclaration contract | **Cutoff predeclaration contract** below | What a cutoff-based method must declare, and what a third party can then verify |

**No external two-number pilot was run, and none is possible from the released artefacts.**
That is Finding C4-1, not an omission. The internal run on this project's own cached
predictions is a code-correctness check and is labelled as one everywhere it appears; it
cannot be pilot evidence, because this project's own zero decision was supplied
retrospectively for that run rather than predeclared.

**Open:** the paper-stage argument — positioning against the evaluation-methodology
literature, and the choice of venue — is not written. The protocol itself is complete
enough to be applied.

## Next bounded steps — three separable pieces

The original bounded scope is retained here as a completion index. These deliverables
have distinct evidential weight and must not be grouped as a two-number pilot.

### (1) Support and zero-count reconciliation audit — the reportable external work

Delivered in **Support and zero-count reconciliation audit** below, with the named script,
CSV and text report. It computes neither primary number for a published method.

### (2) Internal smoke-test on this project's own OOF cache — code correctness only

Delivered in **Implementation and internal code-correctness check** below, with the reusable
reporter, N12 checks and 800 cached rows. This is not pilot evidence.

### (3) Predeclaration for cutoff-based methods

Delivered in **Cutoff predeclaration contract** below for fixed, top-k and adaptive rules.

## Support and zero-count reconciliation audit

`audit_c4_support.py` writes `results_c4_support_audit.csv` and
`results/RESULTS_c4_support_audit.txt`. This is reportable external support/identifier work,
not a two-number pilot. Structural counts and directional mismatch evidence reuse C3;
printed decimal targets and source-row pairing are checked directly, with input hashes.
No graph traversal, external prediction reconstruction or fitting occurs.

**Support substitution is a different evaluation population.** Shipped zeros exceed
structural zeros by 662 on cit-Patents and 1,086 on com-lj. The existing C3 gate records
zero discrepancies in the opposite direction (`rule = 0 & shipped > 0`). Metadata naming
the scored target, its checksum and both supports would prevent silent substitution.

| Graph | Structural → shipped zeros | z, structural → shipped | w, structural → shipped | Registered geometric reference, structural → shipped |
|---|---:|---:|---:|---:|
| cit-Patents | 709,062 → 709,724 | 0.188374060 → 0.188549931 | 0.317028296 → 0.317277328 | 0.311352651 → 0.311586516 |
| com-lj | 1,150,616 → 1,151,702 | 0.287800634 → 0.288072273 | 0.446964666 → 0.447292182 | 0.428053745 → 0.428330872 |

The respective reference increases are **0.000233865** and **0.000277127**; the maximum
geometric mixture-prediction shifts over shipped cells are **0.000192224** and
**0.000213260** (tied-mixture shifts **0.000210282** and **0.000269218**).
These are small but measurable support effects. Both global P1 medians remain exactly
unchanged at the computed precision: absolute **0.078564179078**, signed **−0.076970069043**.
The two graphs retain **12** and **9** floor+0.05 hits under this support sensitivity.
The audit uses C3's registered geometric expression `w*sqrt(1-z*z)` here, keeping it
distinct from the exact finite-n untied reference `w*sqrt(S/T)` in the reporter.
Published tau columns and their observed drops change by **0** because the supplied cells
are fixed. The *actual* tau after replacing the shipped positive filter by structural
support is **TBD: what would it be with the unavailable aligned per-node predictions?**
Conditional mixture shifts cannot answer that question.

**Quantised support is not exact target precision.** Streaming `Decimal` checks find
**15,043,174 values**, every one an exact multiple of 1e-14, with zero exceptions. The
first positive grid point occurs **1,679** and **3,802** times in the two affected files,
and zero times in the other three. This corrects the brief and C3 third amendment's
**14,943,174** total, which is 100,000 too small. The existing P4 denominators already
sum to the measured total (7,281,095 + 7,762,079); no threshold, conditional or scored
verdict changes. The locked registration is retained, with this contradiction disclosed.

The metadata remedy is to declare decimal precision, rounding rule and target provenance
before treating zeros as exact. Under nearest rounding, positive values strictly below
half a step (5e-15) reach zero; equality depends on the tie rule. **Inference, not measured
exact magnitudes:** these discrepancies are consistent with that mechanism. Grid membership
alone does not establish nearest rounding, nor the missing pre-rounding values. Calling
the first positive grid point a hard clamp is too strong; it is a quantisation grid. The
quantisation/support effect on references is quantified above; its effect on an exact-target
method tau is unavailable. All five files are quantised, even though only two lose support.

**Repeated labels are an identity defect.** There are 395 distinct paired names but 404
paired occurrences and 5,608 finite observations. Six names recur (three appear three times,
three twice). The audit preserves zero-based source-row IDs and occurrence indices assigned
*before* finite filtering, then independently matches the existing C3 values. Source order
is the reproducible pairing convention; absent unique run IDs, the table cannot independently
prove that nth plain and nth filtered rows originated from the same underlying run.

Name-only first/last deduplication each drops **126 observations**, yielding **5,482**.
Across graphs and these two policies, maximum absolute changes are **0.0004** in median
all-node tau, **0.00095** in median filtered tau and **0.0009** in median drop (the latter
on soc-Slashdot0902). Spearman rho becomes **0.907692**, versus the retained occurrence
analysis's **0.890110**; P3 per-graph hit counts remain unchanged. These small table changes
do not justify discarding rows. Explicit run/configuration/source occurrence IDs and a
declared aggregation population would prevent both accidental deletion and many-to-many
join multiplication. These are sensitivity policies, not replacement C3 analyses.

## Implementation and internal code-correctness check

`c4_two_numbers.py::report` implements both primary metrics, the zero-labelled confusion
counts, class-conditional rates, all-node tau, exact-equality prediction tie counts within
zeros/positives/across the boundary, reference positive ties and the actual tau-b denominator.
The zero decision and its provenance are explicit arguments; `None` leaves accuracy and
confusion counts unavailable. Negative/nonfinite reference values, nonfinite scores and
misaligned or non-Boolean decisions are rejected rather than silently filtered.

**Resolution of unspecified cases:** empty evaluation gives NA accuracy; absent classes give
NA for their class-conditional rates. Positive tau reasons distinguish fewer than two
positives, constant reference and constant scores (in that order if several apply).
Prediction ties mean exact stored-value equality, without rounding. The simplified mixture
is labelled only when separation is strict, both blocks have at least two nodes, positive
reference and score blocks have no ties, and the zero-score block is either wholly tied or
wholly untied. Otherwise it reports `general_pair_accounting` and leaves the simplified
reference unavailable. It reuses the two C3/N11 mixture functions; no third mixture is fitted.
When fewer than two zeros exist, the distinction between those zero-block regimes is vacuous;
the conservative general label avoids presenting it as measured evidence for either regime.

**Internal code-correctness check, not pilot evidence.**
`results/results_c4_internal_smoke.csv` retains all 800 betweenness vectors (160 per graph),
with `results/RESULTS_c4_internal_smoke.txt` and `results/c4_internal_provenance.json` recording
the summary, source hashes and conventions. Each row spans all nodes in a full 5-fold OOF
vector. Contrary to the handoff's key description, the writer `stage2_sweep.py` uses
`target|radius|richness|seed`, not `target|seed|tier|fold`.

The cache has no declared Boolean zero decision. For this code-correctness check only, the
runner explicitly supplies **`cached score == 0`**, declared retrospectively here without
calibration or an auxiliary certificate. The original estimator did not publish a predeclared
cutoff; these accuracies must not be described as prospective evidence for that rule. The
handoff's claim that the project's zero-decision logic was already fully known was too strong:
the writer establishes score generation, not a pre-existing classification declaration.

| Graph | Rows / finite positive taus | Median zero accuracy | Median positive tau-b |
|---|---:|---:|---:|
| ca-GrQc | 160 / 160 | 0.991101 | 0.723900 |
| ca-HepTh | 160 / 160 | 0.995948 | 0.714781 |
| email-Eu-core | 160 / 160 | 0.965517 | 0.876114 |
| facebook_combined | 160 / 160 | 0.963605 | 0.645960 |
| p2p-Gnutella08 | 160 / 160 | 0.998412 | 0.872212 |

These descriptive medians pool all radius/richness/seed configurations per graph, not a
selected operating point and not an uncertainty interval. All 800 rows need general pair
accounting. No forest is classified as continuously untied merely because it outputs floats.
All-node taus reproduce the matching stored sweep cells to maximum absolute error
**2.220e-16**. NPZ vectors have no embedded node identifiers: alignment follows the current
writer's target-CSV order, checked for unique sequential IDs, equal shapes and agreement
with the separately stored sweep metric. This is strong consistency evidence, not proof of
the historical cache-generation process or of held-outness from the arrays alone.

`verify_pipeline.py` **N12** independently pins accuracy 3/5 and positive tau 1/3 on a
five-node example; tied and untied all-node taus 7/9 and 7/sqrt(90); confusion rates,
boundary ties, reference ties, unavailable decisions, invalid inputs and all named
degenerate cases. Existing N11 retains both mixture checks.

## A minimal complete report — one worked row

Every field the protocol requires, instantiated once, so "report the metadata" has a
concrete referent. This row is a **code-correctness check, not evidence about the method**:
the zero decision was supplied retrospectively, and the configuration is one arbitrary cell
of 800, not a selected operating point.

| Field | Value |
|---|---|
| Evaluation identity | ca-GrQc, undirected simple graph, all 4,158 nodes, 5-fold out-of-fold predictions, cache key `betweenness\|0\|node+edge+subgraph+dynamic\|0` (radius 0, richest tier, seed 0) |
| Target convention | Undirected, unweighted, endpoint-excluding Brandes betweenness, exact; source and checksum in `results/c4_internal_provenance.json` |
| Support | n = 4,158; reference zeros 2,288; reference positives 1,870; z = 0.550265 |
| Zero decision | `predicted_zero = (cached score == 0)`, **declared retrospectively for this check only**, no calibration and no auxiliary certificate |
| Confusion counts | true-zero 675, missed-zero 1,613, false-zero 0, true-positive 1,870 |
| **Number 1** — zero-set accuracy | **0.612073** (false-zero rate 0.000000; missed-zero rate 0.704983) |
| **Number 2** — reference-positive-only τ-b | **0.429094** |
| Tie evidence | 201 distinct predictions overall, 98 within the zero set, 193 within positives; prediction-tied pairs 298,939 within zeros, 25,940 within positives, 47,093 across the boundary; reference positive-block ties 7,563 |
| Pair accounting | total pairs 8,642,403; reference-tied pairs 2,623,891; prediction-tied pairs 371,972; τ-b denominator 7,055,188.744369 |
| Regime | `perfect_score_separation` false; zero-tie regime `partially_tied`; mixture regime `general_pair_accounting` — the simplified mixtures do **not** apply, so no zero-skill reference is reported |
| Supplementary | all-node τ-b 0.544282; drop 0.115189 |

Three things this row demonstrates that an aggregate τ column cannot.

**The row checks three distinct calculations.** All-node τ is 0.544282,
reference-positive-only τ is 0.429094, and the retrospectively declared rule's accuracy
is 0.612073. The majority-class accuracy is 0.550265 (declare every node zero), giving
an arithmetic difference of 0.061808. These values illustrate the fields and prevalence
calculation in the implementation; this arbitrary cached configuration supplies no pilot
evidence or judgement about method quality. All-node tau is not an arithmetic average of
accuracy and positive-only tau, especially with the general tie accounting required here.

**The asymmetry is visible only in the confusion counts.** False-zero is 0 and missed-zero
is 1,613: this rule never calls a positive node zero, it just fails to find most of the
zeros. Accuracy alone hides which direction the errors run, and the two directions have
completely different consequences for a downstream user.

**The tie evidence refuses the shortcut.** The predictions are `partially_tied` on the zero
set — neither of C3's two clean regimes — so neither simplified mixture applies and the
zero-skill reference is withheld rather than approximated. A report that assumed continuity
from "the model outputs floats" would have quoted a reference that does not hold here. This
is the case the metadata exists to catch, and it is the *typical* case: all 800 rows in the
internal run require general pair accounting.

## Cutoff predeclaration contract

A reconstructible zero decision is a deterministic mapping from released inputs to an
aligned Boolean vector. Specify score orientation/units, transforms (including clipping and
rounding), comparison operator, treatment of equality and nonfinite values, eligible node
set, node IDs/order, and whether the decision changes scores before either tau is measured.
Ship the scores actually evaluated, target convention/checksum, decision vector, rule/code
version and selection provenance. Hash the graph, arrays and rule, and preserve a dated
declaration in a versioned public record or independently timestamped archive. A hash made
after evaluation proves content identity, not predeclaration. Report the raw scorer and any
mask-augmented method as distinct configurations.

| Rule | Declare before evaluation-graph access | Instantiate after graph access, before test-label access | What a third party can verify |
|---|---|---|---|
| Fixed threshold | Numerical threshold, score scale/transforms, `s <= t` versus `s < t`, and all tie/invalid policies. If calibrated, freeze the validation graph/node split, candidate set, objective, tie-break and selected threshold before evaluating the test graph. | Apply the frozen threshold; release the resulting decision vector and evaluated scores. | Recompute every decision and both numbers from arrays. Reproduce calibration only if validation inputs/results are released. A retrospective threshold is auditable arithmetic but cannot substantiate a predeclared selection claim. |
| Top-k | Say whether top-k are predicted **positive** (others zero) or the reverse. Fix k, or a formula such as `ceil(q*n)` with q, eligible-node definition and rounding rule; specify deterministic boundary-tie handling using stable IDs, or all-ties inclusion (which can exceed k). | Compute n, realised k and boundary score under the frozen rule; release the ordered IDs, tie outcomes and decision vector. | Check membership/counts exactly; a top-k-positive rule reports retrieval membership as a zero classification decision, not a claim that all remaining scores are numerically zero. A graph-specific k picked after seeing scores is adaptive, not a fixed predeclaration. |
| Data-dependent cutoff | Freeze the complete algorithm and allowed inputs: graph statistics, unlabelled score distribution, or an independent calibration split; include constants, random seed, tie/degenerate fallbacks and stopping/selection rules. Predeclare the evaluation protocol as transductive when test-graph structure or scores are used. | Log allowed input statistics, realised threshold, algorithm trace/version and decision vector. No evaluation labels may select the threshold. | Recompute the threshold if every allowed input and code path is released. An opaque human choice or private calibration dataset leaves selection unauditable; released decisions still permit metric recomputation, but cannot establish how the cutoff was chosen. |

For every rule, distinguish three timestamps: freezing the selection procedure, obtaining
the evaluation graph/scores, and revealing evaluation labels. A method whose threshold is
set after inspecting the evaluation graph must say so; only an already frozen adaptive rule
supports the corresponding predeclaration claim. If the benchmark's labels were already
public and seen, a later declaration cannot erase that exposure. Disclose it, and use a
new hidden evaluation set for a prospective claim. A timestamp alone cannot prove labels
were never viewed; independently controlled access records can strengthen that evidence.

Do not tune on the two reported test metrics. If there is neither a decision vector nor a
reproducible declared rule, the first number remains unavailable. Released scores and
reference truth can still supply the positive-only tau, with its support and tie metadata.
No procedure can reconstruct an undocumented historical human cutoff or prove a private
selection history from aggregate tau columns alone.

---

## What this protocol does not do

Collected here rather than left implicit, because a protocol that oversells itself is worse
than none.

- **It does not make an old published number recoverable.** Where per-node arrays were not
  released, the two numbers cannot be reconstructed after the fact by any means short of
  re-running the method. Finding C4-1 is the measurement of how often that is the case in
  one complete benchmark: always.
- **It does not validate a zero decision that was never declared.** Supplying one
  retrospectively — as the internal check here does — produces auditable arithmetic, not
  evidence that the method committed to that rule. The distinction is recorded in every
  place this project does it.
- **It does not settle uncertainty.** It requires that seed variation, target
  approximation and evaluation-node sampling be reported separately, and says a node
  bootstrap is not automatically independence-valid on a network. It does not supply a
  correct interval; that is open.
- **It does not supply a universal cutoff.** For arbitrary score scales no numeric
  threshold is prescribed, and the predeclaration contract is explicit that an opaque human
  choice or a private calibration set leaves *selection* unauditable even when the
  resulting metrics recompute exactly.
- **It does not establish exactness of anyone's reference targets.** C3's quantisation
  finding narrows to this: grid membership shows a release is rounded, not that a
  particular value was clamped, and not what the pre-rounding magnitudes were.
- **It changes no C3 verdict.** P1 remains falsified on both registered clauses, P2 and P3
  supported, P4 passed under its recorded conditional. Nothing in this document rescores
  anything.

## Adoption path for a benchmark reporting aggregate τ today

The cost is small and it decomposes, so none of it has to happen at once.

1. **Ship the per-node prediction arrays** you already computed, alongside the aggregate
   table. This is the one step that makes everything else reconstructible by third parties,
   and in BRAVA-GNN's case the code to do it is already written and merely unexercised
   (`betweenness.py:17 _dump_predictions`, behind `--dump_predictions`).
2. **State the target convention and its precision** — directed/undirected, endpoint
   handling, normalisation, exact or sampled or quantised, with a checksum. C3 lost two
   graphs to consistency-only status for want of this one line.
3. **Declare the zero decision**, or state that the method has none. Either is fine; only
   silence is not.
4. **Report the two numbers**, keeping all-node τ as a supplementary continuity column so
   older tables stay readable.
5. **Publish the support and tie counts** from the table above.

Steps 1 and 2 are the ones that matter most, because they let someone else compute the rest
without your cooperation.

## The boundary on per-node arrays is hard, and is not a problem to be solved here

The inspected BRAVA-GNN release does not provide per-node prediction arrays; its documented
dump option creates them on model execution. The C3 pre-registration excludes that in §4 ("No re-running of anyone's
model"), and this project's CPU/no-PyTorch stance blocks it independently. **This is recorded as
the finding above, not carried as an open task**, and no workaround should be attempted: any
route that reconstructs per-node scores from aggregate columns would be inventing the very
metadata whose absence is the result.

If a stronger version of C4 is wanted later, the honest next move is to **ask the authors for a
`--dump_predictions` run** — the flag already exists; its runtime cost has not been measured here. Logged as
future work, not attempted now.

**Bounded implementation complete:** the three pieces listed under **Status** each have
their own deliverable and are not to be reported under a single name. An external
two-number pilot remains unavailable under Finding C4-1. C3's registered verdicts remain
P1 falsified, P2/P3 supported and P4 passed under its recorded conditional.

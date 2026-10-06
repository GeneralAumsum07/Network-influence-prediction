# What an Aggregate Betweenness Score Cannot Reconstruct

## A release audit and reporting contract for zero-inflated centrality evaluation

### Abstract

Betweenness benchmarks often publish one all-node Kendall tau-b per method and graph. In zero-inflated targets, that score mixes identifying reference-zero nodes and ranking reference-positive nodes. We audit the released aggregate artefacts of the 14-graph BRAVA-GNN benchmark and re-score a pre-registered comparison using its all-node and reference-positive-only columns. The aggregate release supports a comparison of reported levels, but it does not preserve aligned zero decisions, per-node scores, target/support provenance, or tie accounting. It therefore cannot reconstruct a joint two-task report.

The C3 analysis finds that the graph-level median all-node minus positive-only drop tracks reference zero fraction (Spearman rho = 0.890, 14 graphs). Its registered continuous-score mixture is falsified (median absolute error 0.0786), while the registered near-floor condition holds on 12 of 14 graphs. We supply an executable reporting contract: declared zero-set accuracy, positive-only tau-b, all-node tau-b, support, confusion counts, and tie metadata. A cache-only test validates its arithmetic on 800 held-out vectors; it is not an external pilot. This is a reproducibility and support audit, not a new metric.

## 1. The reporting problem

Let y_i >= 0 be reference betweenness, s_i a predicted score, and Zhat_i a declared zero decision. All-node tau-b(s,y) remains useful for continuity but does not say whether agreement arises from zero/positive separation, positive-node ranking, or ties. A report needs both:

1. **Zero-set classification:** mean(Zhat_i = (y_i = 0)).
2. **Positive-node ranking:** tau-b(s[y > 0], y[y > 0]), filtering solely by reference truth. A positive node predicted zero remains in this test.

If no aligned decision vector or complete declared reproducible rule exists, the first number is unavailable and must be reported as NA with a reason. It must not be filled by an auxiliary exact certificate. Accuracy also needs support counts, the four zero-labelled confusion cells, false-zero rate, and missed-zero rate. The ranking number needs actual prediction and reference-tie evidence. All-node tau-b is supplementary continuity evidence.

Perrone, van den Heuvel, and Zhan (2023) provide prior work on zero/nonzero components and a tie-corrected component in a population association estimator for bivariate zero-inflated counts. The finite benchmark pair accounting here is a different object; the one-sided specialization and denominator are not attributed to that paper. GNN-Bet includes zero-betweenness preprocessing. BRAVA-GNN computes and ships a reference-positive-only statistic. This paper adds an aggregate-release audit and a reconstructible reporting contract; it does not claim to introduce filtered evaluation.

## 2. Audit evidence

The released BRAVA-GNN table is paired in source-row occurrence order: 5,608 finite plain/filtered graph-method cells, 404 paired row occurrences, 395 names, and 14 graphs. Repeated labels remain observations. Structural zero support is checked against graph regime. Two shipped targets have different printed zero counts, so support provenance is recorded rather than silently substituted.

An aggregate tau-b table, even with a positive-only column, cannot recover zero-set accuracy without an aligned decision. It cannot recompute either rank statistic or tie accounting without per-node vectors. It cannot establish target support or convention without metadata. This is an audit finding for the inspected release and corpus, not a prevalence claim.

| Test | Result | Meaning |
|---|---:|---|
| P1: registered mixture predicts all-node tau-b | **Falsified**; median absolute error 0.0786, signed -0.0770 | The specified mixture does not reproduce reported levels. |
| P2: median drop tracks zero fraction | **Supported**; rho = 0.890 | Support is associated with filtering's observed effect. |
| P3: graphs within 0.05 of registered free floor | **Supported**; 12/14 | Conditional comparator result, not a ranking claim. |
| P4: structural-rule gate | **Passed under registered conditional** | Permits reporting P1-P3 under the recorded convention. |

> Regenerated 2026-09-12 by Claude Opus 5 after three scorer fixes from the Task 6 audit (exact floor, ABCDE gate detail, per-cell registered floor): all four rows above are unchanged to the digit; see `docs/archive/phase6_record.md#rec-C3_C4_REGENERATION_NOTE_20260912`. The A7 paired follow-through quoted in §4 (38 of 41) is being re-measured on the refit corpus and is the pre-refit record until then.

The C4 audit preserves repeated source occurrences; name-only first/last policies each drop 126 observations. It finds all 15,043,174 inspected printed target values lie on a 1e-14 grid. Cit-Patents and com-lj have 662 and 1,086 more shipped zeros than structural zeros. This requires declared support and precision; it does not establish unavailable pre-rounding values.

> Added 2026-09-11 by Claude Opus 5. An exact rational local witness was subsequently run on all five ABCDE graphs. On cit-Patents and com-lj it certifies positive lower bounds for those 662 and 1,086 nodes, but **no pair qualifies at either reporting threshold**, so the witness does not contradict the shipped zeros and the sentence above is unchanged. On the three graphs without support loss it selects **zero** structurally-positive printed zeros among 3,030,420 printed zeros: every printed-zero node there has a clique neighbourhood, so none is structurally impossible. Because the selection predicate is structural rather than precision-based, the separation is informative, but it remains a null and does not establish that those three files are unquantised — all five lie on the 1e-14 grid. See docs/archive/phase6_record.md#rec-phase6_external_precision_followup.

The inspected release has no aligned method-prediction arrays, declared zero decisions, or tie arrays for external two-number reconstruction. BRAVA-GNN has a prediction-dump option, but using it executes the method and was not authorised. The cache-only reporter check uses 800 saved OOF vectors, requires general pair accounting in all rows, and agrees with stored all-node tau within 2.22e-16. Its retrospective score == 0 rule is code-correctness evidence, not evidence about any external method or predeclared decision.

## 3. Reporting contract

| Component | Required record |
|---|---|
| Identity | Graph/version, node population, preprocessing, method/configuration, seed/source occurrence |
| Target/support | Convention, exact or quantised source/checksum, n, zero and positive counts |
| Zero decision | Aligned Boolean vector or complete predeclared rule, selection provenance, confusion counts |
| Primary metrics | Zero-set accuracy and positive-only tau-b, each with an NA reason where needed |
| Ties | Prediction ties within/between support blocks, reference-positive ties, actual tau-b denominator |
| Continuity/uncertainty | All-node tau-b, drop, and separately labelled seed, target, or sampling variation |

Rules must declare score orientation, transformations, comparison operator, equality/nonfinite policy, eligible IDs/order, and whether scores change before ranking. A fixed threshold records validation selection; top-k records orientation, k, and boundary ties; a data-dependent rule records allowed inputs, constants, seed, fallbacks, and trace. Released arrays permit metric reconstruction; a retrospective cutoff does not prove predeclared selection.

## 4. Scope, limits, and claim map

This paper audits one release with a targeted literature review. It does not establish field-wide release practice, a method-ranking reversal, a prospective external evaluation, a universal cutoff, or an independence-valid network interval. A node bootstrap is not automatically a network interval.

| Claim | Evidence | Limit |
|---|---|---|
| Aggregate levels mix support-sensitive tasks | results/RESULTS_c3_benchmarks.txt; results/c3_scored_summary.json | 14 graphs; P2 is association only. |
| Registered mixture fails | Same C3 outputs | No replacement mixture follows. |
| Support and source provenance matter | results/RESULTS_c4_support_audit.txt | No recomputed external method scores. |
| The report is implementable | c4_two_numbers.py; results/RESULTS_c4_internal_smoke.txt | Internal cache-only check. |
| Reconstruction is blocked for this release | C4 protocol, Finding C4-1 | Does not describe uninspected releases. |
| Paired target variation can alter dynamic-tier flags | results/results_paired_target_noise.csv | 45 contrasts; no headline-star or total-uncertainty claim. |

The paired A7 follow-through retains 38 of 41 seed heuristic flags and loses three under target resampling. It is conditional context: it neither changes C3/C4 verdicts nor reaches headline structural-tier comparisons.

## References

- Perrone, E., van den Heuvel, E., and Zhan, Z. (2023). Kendall's tau estimator for bivariate zero-inflated count data. Statistics & Probability Letters 199, 109858. [DOI](https://doi.org/10.1016/j.spl.2023.109858).
- Maurya, S. K., Liu, X., and Murata, T. (2021). Graph Neural Networks for Fast Node Ranking Approximation. ACM TKDD 15(5), Art. 78. [DOI](https://doi.org/10.1145/3446217).
- Dachille et al. (2026). Degree-Mass Message Passing for Betweenness Ranking in Directed and Undirected Networks. [arXiv:2602.09716v2](https://arxiv.org/abs/2602.09716v2).

See docs/reference/prior_work.md for source boundaries and fuller positioning.

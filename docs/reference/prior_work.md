# Prior work — literature positioning for Phases 6 and 6.5

Merged 2026-09-12 by Claude Opus 5 from two files that were both citation lists, formerly
`phase6_literature_review` (2026-09-07, Part A) and `phase7_prior_work_20260912`
(2026-09-12, Astra's primary-source check, Part B; its "Phase 7" heading reads
"Phase 6.5" per the naming ruling in `docs/ROADMAP.md`).
Bodies are verbatim; only the two top headings were demoted to `##`. Pre-merge hashes
are in `results/phase6_doc_moves_20260912.json`.

---

## Part A — Phase 6 literature review: zero-inflated betweenness evaluation and release audit

**Status:** evidence-limited positioning for the Phase 6 paper package, completed
2026-09-07. This is a targeted verification of the closest sources, not a systematic
review and not a claim that no other relevant work exists.

## The defensible paper claim

The paper can make a concrete, bounded contribution: it audits a released
betweenness-ranking benchmark at the aggregate-table level, distinguishes the all-node
and reference-positive-only ranking questions, and supplies an executable reporting
contract for making both questions reconstructible. The release audit is central: an
aggregate Kendall column alone does not preserve the per-node scores, target convention,
support, tie evidence, or a declared mapping from scores to a zero decision that are
needed to recompute the two quantities.

It should **not** present a new filtered metric, a new zero-set certificate, or a new
general theory of zero-inflated concordance. BRAVA-GNN already computes and releases a
reference-positive-only Kendall statistic in its result tables; GNN-Bet and BRAVA-GNN
also provide the shortest-path preprocessing antecedent. The contribution is the
external audit, the separation of evaluation tasks, and the reproducibility contract.
The contract is a proposal backed by one inspected released benchmark and this project's
internal code-correctness check; it is not a claim about the prevalence of release
practices across the field.

## Resolved C0 question: Perrone, van den Heuvel and Zhan (2023)

The direct, CC-BY publisher version resolves the outstanding source question in
`../study_doc_v2.md` §24.6.

- Perrone et al. define population Kendall association through concordance and
  discordance probabilities, then distinguish a conventional sample estimator formed
  from sample pair frequencies.
- For ties they introduce the tie-corrected estimator `tau_b`. Their proposed estimator
  `hat(tau_A)` substitutes sample relative frequencies into their population association
  formula and uses `tau_b` for the positive-positive component `tau_11`.
- The article formulates the general two-margin zero-inflated count setting with `p1` and
  `p2`. It does **not** state the project's one-sided `p2 = 0` specialization. That
  specialization is valid algebra applied to its displayed general formula, not a
  result attributed to the paper.
- Their target is a population association measure and a consistent sample estimator for
  it. It is not the finite-vector `tau_b` reporting calculation audited here, and the
  article does not give the project's scored-pair-share `w` or its `sqrt(scoreable *
  total)` denominator decomposition.

Thus Perrone et al. are direct prior art for separating zero and nonzero parts and for
using a tie-corrected component in a zero-inflated-count estimator. Cite them for that
architecture. The distinction in object remains important: the Phase 6 calculation
accounts for a particular finite benchmark score's pairs and denominator, whereas their
work estimates an association parameter of a bivariate distribution. This is a scope
distinction, not a priority or absence claim.

## Closest benchmark and learned-centrality sources

| Source | Directly established from the source | Position in this paper |
|---|---|---|
| Maurya, Liu and Murata, GNN-Bet (2021) | The method identifies nodes with no shortest paths through them and zeroes their adjacency rows for betweenness message passing. Its evaluation section calls its metric Kendall tau, with the ordinary concordant-minus-discordant pair-count expression. | Cite for the preprocessing antecedent. Do not use it as evidence that it reports a positive-only statistic or as a claim about all modern benchmark releases. |
| Dachille et al., BRAVA-GNN (2026) | The paper evaluates all-node ranking with `tau_b`, explicitly motivates it by ties in betweenness, and attributes its undirected preprocessing heuristic to Maurya et al. The linked public implementation's `ranking_correlation(..., compute_filtered=True)` also computes `kendalltau` after `true_arr > 0`; its test path enables this and its writer emits a `_filtered` result row. The README documents `--dump_predictions`, but predictions are only created on execution. | This is the closest practical precedent. Credit it for computing and shipping the second ranking statistic. The Phase 6 audit asks for a declared two-task report and the artefacts needed to reconstruct it without executing the method; it does not claim BRAVA failed to calculate the filtered number. |
| AlGhamdi et al., BeBeCA (2017) | The public repository supplies exact-score inputs and an evaluation script that reports average error, maximum error, top-1% hit, and Kendall-tau distance. | Cite as a dedicated BC-approximation evaluation framework with a prescribed script. Its public README was inspected; the paper full text was not obtained here, so do not make stronger paper-content claims. It motivates a release/reconstruction discussion without asserting a missing-zero-treatment finding. |
| Arends et al. (2025) | The arXiv abstract and HTML identify zero-inflated continuous distributions and develop Gini's gamma and Spearman's footrule, with representations, estimators and bounds. | Adjacent statistical work on zero inflation and concordance. It is not evidence about Kendall `tau_b` benchmark reporting. |

The literature positioning should therefore say that the protocol builds on known
zero-inflated-concordance ideas and on an existing filtered evaluation implementation,
then state precisely what it adds: an audit of released aggregate artefacts and an
executable, predeclarable record of the separate zero decision and positive-only ranking
task. It should avoid phrases such as “first,” “nobody,” “unoccupied,” or “the only
benchmark,” which this targeted check cannot support.

## Release-audit argument, narrowed to observed evidence

The C3/C4 inspection establishes one concrete constraint on the BRAVA-GNN benchmark
release: paired all-node and filtered aggregate results can support a level comparison,
but they do not reconstruct a two-number evaluation. Computing zero-set accuracy needs
an aligned decision vector or a complete declared rule; recomputing either rank statistic
and its tie accounting needs aligned per-node scores and targets. The public source code
contains a prediction-dump option, but using it would require a model run, which Phase 6
does not authorise. The paper should call this an **audit finding for the inspected
release/corpus**, rather than a field-wide conclusion.

The resulting contract is useful even where a method has no zero-decision stage: it
requires authors to say that fact, release the scores and targets actually evaluated,
identify the evaluation population and target convention, and report support/tie
metadata alongside all-node and positive-only rank statistics. A decision-bearing method
also releases the deterministic decision vector or the fully declared rule and its
selection provenance. These are executable reporting requirements, not a new score.

## Conditional venue fit

The strongest topical fit is a **future KDD Datasets and Benchmarks Track**, conditional
on turning the present protocol and audit into an accessible, documented evaluation tool
with reusable inputs and outputs. The current official track scope explicitly includes
benchmarking tools, evaluation methodologies, and frameworks; its criteria emphasize
accessibility, documentation, impact and reproducibility. The paper's release contract
and executable reporter align with that scope.

The fit weakens if the submission remains only a retrospective analysis of one released
table: a stronger benchmark/tool package would need a public, well-documented runner and
artefacts that let another group apply the contract to another method without executing
hidden checkpoints. In that narrower state, a data-mining research-track submission is
plausible only if the paper leads with a substantive, bounded empirical evaluation result
and uses the contract as the reproducibility consequence. This is a scope assessment,
not a venue decision or a statement about eligibility, deadlines, or acceptance prospects.

## Evidence record and public source archive

The following sources were actually opened/read at the stated level. Downloads and raw
source snapshots are under `results/phase6_sources/`; their hashes identify the local
copies rather than asserting permanent availability at a remote URL.

| Source | Read level | Stable public location | Local evidence |
|---|---|---|---|
| Perrone, van den Heuvel and Zhan (2023), *Kendall's tau estimator for bivariate zero-inflated count data*, *Statistics & Probability Letters* 199, 109858 | Full publisher PDF/text, including §§2–4 and conclusion | [DOI](https://doi.org/10.1016/j.spl.2023.109858), [TU/e CC-BY record](https://pure.tue.nl/ws/portalfiles/portal/299446753/1_s2.0_S0167715223000822_main.pdf) | `perrone2023_published.pdf`, SHA-256 `B44CD75E3EA725239AC79619ED10C4162B0AE5298F0B8A5E6D8A18A8014DED72` |
| Maurya, Liu and Murata (2021), *Graph Neural Networks for Fast Node Ranking Approximation*, *ACM TKDD* 15(5), Art. 78 | Full publisher PDF/text; preprocessing and evaluation sections inspected | [DOI](https://doi.org/10.1145/3446217) | `maurya2021_gnn_bet.pdf`, SHA-256 `82F614BD43558568667AFCEA50DEF9D6F14BCB77223F492EC1FEF9CB0B8B180C` |
| Dachille et al. (2026), *Degree-Mass Message Passing for Betweenness Ranking in Directed and Undirected Networks* | Official arXiv v2 HTML, including preprocessing and metric sections; public implementation source inspected without execution | [arXiv v2](https://arxiv.org/abs/2602.09716v2), [paper HTML](https://arxiv.org/html/2602.09716v2), [implementation](https://github.com/justindachille/BRAVA-GNN) | `brava_gnn_2026_v2.pdf` `B670C0BA67ADB23B23178F791B72F45BB893637222592BF0A3137C530E7D64F1`; raw `brava_utils.py` `C1B040C50842CC4E718580E5AFCF01203AAF7AE197A21CE0A1A9D63AE7ACACA5`, `brava_betweenness.py` `C7BB0F44ABE1175BD0B23FB70C4D7F3AE703F13FD030AEC0BFAB14B51211994D`, `brava_results.py` `3389B7023B49EA7189FD6199999BDB446E0477B41A8B1C3CE16D8369555644F2` |
| AlGhamdi, Jamour, Skiadopoulos and Kalnis (2017), *A Benchmark for Betweenness Centrality Approximation Algorithms on Large Graphs* | Public framework README inspected; paper full text not obtained | [DOI](https://doi.org/10.1145/3085504.3085510), [public framework](https://github.com/ecrc/BeBeCA) | No local paper download; claim restricted to repository README |
| Arends et al. (2025), *Rank-based concordance for zero-inflated data* | Official arXiv abstract/HTML sections inspected | [arXiv](https://arxiv.org/abs/2510.16504), [HTML](https://arxiv.org/html/2510.16504v1) | `arends2025_rank_concordance.pdf`, SHA-256 `F5E5A78024B1E52D6A061F74F45BF805E2021FE6DD79CF70870337CEA97ABC4A` |
| KDD 2026 Datasets and Benchmarks Track | Official scope and evaluation criteria inspected | [official call](https://kdd2026.kdd.org/datasets-and-benchmarks-track-call-for-papers/) | Web source only; used only for conditional scope fit |

## Remaining limits

- This was a narrow primary-source check, not a systematic review, citation-graph sweep
  or a search of paywalled full text. It cannot establish global priority or absence.
- BeBeCA's paper itself was not read; its release README is enough only for the reported
  evaluation-script facts.
- The exact commits of external GitHub repositories can change after this snapshot.
  The saved raw files and hashes support the stated code observations, not a claim about
  later versions.
- No method was executed, no checkpoint was loaded, and no new external two-number pilot
  was produced. The audit's limit on unreleased per-node predictions remains a result,
  rather than a gap this phase attempted to bypass.
- Venue selection and any submission decision remain with Rachit. A future venue needs
  its then-current call, scope, policy and schedule checked afresh.


---

## Part B — Phase 6.5 positioning — primary-source check, 2026-09-12

## Zhang: correction to the attached plan

Zhang, Hanjalic and Wang, *Predicting nodal influence via local iterative metrics*,
Scientific Reports 14, 4929 (2024), already studies increasing local-information
order. The final published paper tests infection-rate multiples 0.5, 1, 1.5 and 2,
locates the epidemic threshold empirically by variability, and reports a qualitative
ridge comparison alongside random forests. Therefore the plan's “Zhang fixed
dynamics” and categorical absence of an estimator comparison are incorrect.
Source: [final paper, printed pages 3–5](https://pure.tudelft.nl/ws/portalfiles/portal/180892512/s41598-024-55547-y.pdf).

Its NWC counts ordinary adjacency walks; the proposed non-backtracking counts are
a related comparator, not a reproduction. Its first H-index order is degree;
this repository starts degree at order zero, so `h_index_r` corresponds to its
order r+1. The recursion agrees. The paper reports saturation near order four,
with infrastructure-network exceptions. Source: same paper, printed pages 1–4.

**Project implication (inference):** L1 remains a missing within-project robustness
test, but neither varying infection rate nor comparing learner families is a new
idea here. The contribution must be assessed through explicit tolerance rules,
radius conventions, multiple targets and uncertainty controls. This targeted
reading does not establish global novelty for that combination.

## Other required citations

- [Lü, Zhou, Zhang and Stanley (2016), *The H-index of a network node and its
  relation to degree and coreness*](https://www.nature.com/articles/ncomms10168):
  the iterative H-operator connects degree, intermediate H-indices and coreness.
  The existing `influence/features.py::h_index_ladder` implements that recursion.
- [Kitsak et al. (2010), *Identification of influential spreaders in complex
  networks*](https://www.nature.com/articles/nphys1746): k-shell location and the
  separation of simultaneous seeds matter for spreading. This is relevant prior
  work for both the core features and L4's overlap control.
- [Guilbeault and Centola (2021), *Topological measures for identifying and
  predicting the spread of complex contagions*](https://www.nature.com/articles/s41467-021-24704-6):
  reinforcement changes which paths and seeds support spread. L5's deterministic
  fractional-threshold arm tests a different process from the existing IC arm;
  it must retain its ignition gate and state the N[i] seeding convention.

## Estimator-family ceiling

The usable-information perspective of Xu et al., *A Theory of Usable Information
under Computational Constraints* (ICLR 2020), makes predictive accessibility
relative to a model family. See the [paper](https://openreview.net/attachment?id=r1eBeyHFDH&name=original_pdf).
Here this is a conceptual connection: empirical Kendall-tau P(r) is not a measured
V-information quantity. Maximising over a finite fitted family cannot certify the
best possible r-local predictor; finite-sample scores are not rigorous population
lower bounds either. L3 adds an estimator to the comparison, not an information
ceiling. A GNN would add another tested family and would still not prove that ceiling.

## Locality convention

The repo's radius-r observation includes the induced ball **and boundary-node
degrees**, as documented in `features.py`. Thus the plan's “exact r-ball guard”
must be read with that qualification. L3 needs only the induced ball and known p.
Compare computational/local-information assumptions explicitly, not just radius
integers across papers with different indexing or boundary conventions.

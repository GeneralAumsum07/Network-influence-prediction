# Phase 6 record — superseded working documents, preserved verbatim

Built 2026-09-12 by Claude Opus 5 (documentation reorganisation, plan Part B; Rachit's decision
that the old files are folded into one record and deleted rather than kept as a folder).

**What this file is.** Every brief, report, review, design note, status ledger and worklog
that the project produced up to 2026-09-12 and no longer needs as a separate file. Each one
sits between a `<!-- BEGIN <old path> sha256=… -->` and `<!-- END <old path> -->` marker
with its **original bytes untouched**, so the SHA-256 in the marker still verifies (the Task 6
coverage ledger, `results/phase6_task6_coverage_ledger_20260911.json`, binds
`docs/phase6_buffered_cv_execution_status.md` by hash; the path→anchor map is in
`results/phase6_doc_moves_20260912.json`). `verify_docs.py` re-extracts and re-hashes every
block on every run, so an edit inside a block fails the gate.

**Rules.** Never edit inside a block. Relative links inside blocks point where they pointed
on 2026-09-12 and are not maintained. To retire a future file, append a new block the same way
and add a row to the table. Living status is in `docs/ROADMAP.md`; the session record is
`docs/LOG.md`; new preregistrations go in `docs/prereg/`.

**Author column.** What the file itself says. "unsigned" means the file names no author;
the Phase 6 expanded-scope files (2026-09-08 to 09-10) were produced under the scope the
worklog attributes to Astra (GPT-6), with dated addenda by Claude Opus 5 where marked.

## Contents

| # | Original path | Date | Author | What it is | Superseded by |
|---|---|---|---|---|---|
| 1 | [`docs/networkinfluencetechnicalreview.md`](#rec-networkinfluencetechnicalreview) | 2026-08-27 | unsigned (referee report v2) | Technical referee report v2 against the 2026-08-27 HANDOFF/README | v3 below; the Phase 6 lanes it triggered (study PART VII) |
| 2 | [`docs/posthoc_B2_hgb_capacity.md`](#rec-posthoc_B2_hgb_capacity) | 2026-09-01 | Rachit (with Claude) | Declared post-hoc B2 arm: capacity-matched hgb | docs/prereg/prereg_B2_estimator.md scored addendum; HANDOFF Finding 11 |
| 3 | [`docs/priority_search_D2.md`](#rec-priority_search_D2) | 2026-09-05 | unsigned | Literature priority search for the D2 zero-inflation critique (Firecrawl + arXiv) | docs/reference/prior_work.md; study section 26 |
| 4 | [`docs/networkinfluencetechnicalreview_v3.md`](#rec-networkinfluencetechnicalreview_v3) | 2026-09-05 | unsigned (referee report v3) | Technical referee report v3: what changed 2026-08-27 to 09-05, four new directions | the Phase 6 lanes (study PART VII); ROADMAP D-closure rows |
| 5 | [`docs/HANDOFF_C3_astra.md`](#rec-HANDOFF_C3_astra) | 2026-09-06 | Claude (Opus 5) | End-of-window hand-off for the C3 external-benchmark lane, written for Astra | study 26i; docs/prereg/prereg_C3_benchmark_inflation.md scored addendum |
| 6 | [`docs/phase6_plan_row6_pending.md`](#rec-phase6_plan_row6_pending) | 2026-09-07 | Claude | Staged (then applied) update to sequencing row 6 of the external plan | applied 2026-09-07; ROADMAP |
| 7 | [`docs/phase6_paired_noise_analysis.md`](#rec-phase6_paired_noise_analysis) | 2026-09-07 | unsigned | Post-hoc analysis rules for the paired radius-gain target-noise contrasts | results/RESULTS_paired_target_noise*.txt; study 26 |
| 8 | [`docs/phase6_completion_checklist.md`](#rec-phase6_completion_checklist) | 2026-09-07 | unsigned (status corrections by Claude Opus 5, 2026-09-12) | Phase 6 completion ledger: the no-fit closure and its 2026-09-08 supersession | docs/ROADMAP.md |
| 9 | [`docs/phase6_extension_20260908.md`](#rec-phase6_extension_20260908) | 2026-09-08 | unsigned; the expanded-scope timeline the worklog attributes to Astra (GPT-6) | Phase 6 evidence extension and full-audit authorisation ledger | docs/ROADMAP.md; docs/LOG.md |
| 10 | [`docs/phase6_requirements_inventory.md`](#rec-phase6_requirements_inventory) | 2026-09-08 | unsigned | Read-only requirements assessment for the 2026-09-08 extension | docs/ROADMAP.md |
| 11 | [`docs/phase6_buffered_cv_design.md`](#rec-phase6_buffered_cv_design) | 2026-09-08 | unsigned | Design of the buffered graph-CV follow-up arm | study 26 (buffered CV); results/RESULTS_buffered_cv*.txt |
| 12 | [`docs/phase6_buffered_implementation_brief.md`](#rec-phase6_buffered_implementation_brief) | 2026-09-08 | unsigned | Implementation brief for probe_buffered_cv.py | probe_buffered_cv.py docstring; verify_buffered_cv.py |
| 13 | [`docs/phase6_criticality_repair_brief.md`](#rec-phase6_criticality_repair_brief) | 2026-09-08 | unsigned | Brief for the criticality (beta_c) repair | verify_criticality.py; influence/criticality.py |
| 14 | [`docs/phase6_criticality_repair_report.md`](#rec-phase6_criticality_repair_report) | 2026-09-08 | unsigned | Report on the criticality repair | verify_criticality.py |
| 15 | [`docs/phase6_criticality_review.md`](#rec-phase6_criticality_review) | 2026-09-08 | unsigned (review role) | Review of the criticality repair | verify_criticality.py |
| 16 | [`docs/phase6_external_precision_followup.md`](#rec-phase6_external_precision_followup) | 2026-09-08 | unsigned; executed-result section by Claude Opus 5 (2026-09-10) | External precision and prediction-feasibility follow-up, with its executed result | study 26; results/phase6_claude_witness_run_20260910.log |
| 17 | [`docs/phase6_precision_witness_design.md`](#rec-phase6_precision_witness_design) | 2026-09-08 | unsigned; amendments by Claude Opus 5 (2026-09-10) | Targeted external-precision witness design (lower bound later withdrawn) | precision_witness.py; study 26 |
| 18 | [`docs/phase6_r1_ablation_design.md`](#rec-phase6_r1_ablation_design) | 2026-09-08 | unsigned | Radius-one subgraph attribution follow-up design | results/phase6_r1_ablation/; study 16 |
| 19 | [`docs/phase6_r1_ablation_implementation_brief.md`](#rec-phase6_r1_ablation_implementation_brief) | 2026-09-08 | unsigned; P1-01 update by Claude Opus 5 (2026-09-12) | R1 ablation implementation plan | probe_r1_ablation.py docstring; influence/r1_ablation.py |
| 20 | [`docs/phase6_structural_target_noise_design.md`](#rec-phase6_structural_target_noise_design) | 2026-09-08 | unsigned | Structural-tier paired target-uncertainty design | results/RESULTS_paired_target_noise_structural.txt |
| 21 | [`docs/phase6_task1_review.md`](#rec-phase6_task1_review) | 2026-09-08 | unsigned (review role) | Pre-run review of Task 1 (structural-tier pilot) | the run |
| 22 | [`docs/phase6_buffered_cv_review.md`](#rec-phase6_buffered_cv_review) | 2026-09-09 | unsigned (review role) | Scoped review of the buffered-CV harness; launch gate | the run (results/phase6_buffered_controller_20260910.log) |
| 23 | [`docs/phase6_structural_task_report.md`](#rec-phase6_structural_task_report) | 2026-09-09 | unsigned; results section by Claude Opus 5 (2026-09-10) | Task 1 structural-tier report, pilot and full-run results | results/RESULTS_paired_target_noise_structural.txt; study 26 |
| 24 | [`docs/phase6_parallel_warning_diagnosis.md`](#rec-phase6_parallel_warning_diagnosis) | 2026-09-09 | unsigned | Diagnosis of the scikit-learn parallel warning in the structural run | HANDOFF section 12 |
| 25 | [`docs/phase6_buffered_cv_execution_status.md`](#rec-phase6_buffered_cv_execution_status) | 2026-09-10 | Astra (GPT-6), per its 2026-09-10 addendum by Claude Opus 5 | Buffered-CV execution status record (Task 6 ledger path) | docs/ROADMAP.md; docs/LOG.md |
| 26 | [`docs/phase6_r1_ablation_readiness_addendum.md`](#rec-phase6_r1_ablation_readiness_addendum) | 2026-09-10 | unsigned | R1 ablation readiness addendum (cache/estimator inspection) | results/phase6_r1_ablation/ |
| 27 | [`docs/phase6_claude_worklog_20260910.md`](#rec-phase6_claude_worklog_20260910) | 2026-09-10 | Claude Opus 5 | Worklog for the lanes completing the Phase 6 expanded scope, 2026-09-10 to 09-12 | docs/LOG.md (starts clean; this is its predecessor) |
| 28 | [`results/REGENERATION_NOTE_20260912.md`](#rec-REGENERATION_NOTE_20260912) | 2026-09-12 | Claude Opus 5 | Regeneration of the reported analyses on the post-refit corpus (Task 6 run C6) | docs/LOG.md |
| 29 | [`results/C3_C4_REGENERATION_NOTE_20260912.md`](#rec-C3_C4_REGENERATION_NOTE_20260912) | 2026-09-12 | Claude Opus 5 | C3/C4 regeneration on the post-audit code (Task 6 run C7) | docs/LOG.md |
| 30 | [`docs/phase7_continuation_20260912.md`](#rec-phase7_continuation_20260912) | 2026-09-12 | Astra (GPT-6), per Rachit 2026-09-12 | Continuation ledger and implementation rulings for the lane plan (filed as 'Phase 7', now Phase 6.5) | docs/ROADMAP.md; docs/LOG.md entry 1 |
| 31 | [`docs/phase7_l3_implementation_brief.md`](#rec-phase7_l3_implementation_brief) | 2026-09-12 | Astra (GPT-6), per Rachit 2026-09-12 | L3 implementation requirements | influence/local_dynamics.py; probe_local_predictors.py |
| 32 | [`docs/phase7_l3_implementation_report.md`](#rec-phase7_l3_implementation_report) | 2026-09-12 | Astra (GPT-6), per Rachit 2026-09-12 | L3 implementation report: files, API, red/green evidence, pilots, runtime estimate | docs/LOG.md entry 1 |
| 33 | [`docs/phase7_l4_implementation_brief.md`](#rec-phase7_l4_implementation_brief) | 2026-09-12 | Astra (GPT-6), per Rachit 2026-09-12 | L4 seed-set quality requirements | docs/ROADMAP.md L4 row |
| 34 | [`HANDOFF.md#13`](#rec-handoff-13) | 2026-09-12 | many hands, 2026-08-27 to 2026-09-12 | HANDOFF section 13 'what to do next' as it stood when status moved to ROADMAP | docs/ROADMAP.md |
| 35 | [`docs/phase6_buffered_cv_implementation_report.md`](#rec-phase6_buffered_cv_implementation_report) | undated | unsigned | Implementation report for the buffered-CV harness | docs/phase6_buffered_cv_review.md (below); the run itself |


---

## <a id="rec-networkinfluencetechnicalreview"></a>`docs/networkinfluencetechnicalreview.md`

<!-- BEGIN docs/networkinfluencetechnicalreview.md sha256=46ae37587d8eb8c443165e23fb8af4c747e986b88f85041c69bdad47a699fbe3 date=2026-08-27 author=unsigned (referee report v2) -->
# Local Network-Based Influence Prediction — Technical Referee Report (v2)

**Scope:** deep-technical review of the project described in `HANDOFF.md` and `README.md` (2026-08-27 versions), written against the standard of an A\* conference submission.
**What changed from v1:** every load-bearing claim was re-verified against primary sources (verification log in §10, including two refinements and one correction to v1); the mathematics behind the main objections is now worked out explicitly; each proposed experiment is specified concretely enough to run.

---

## 0. Verdict

The engineering discipline — independent-reference verification, an enforced leakage guard, paired-seed uncertainty on every number, public revision of findings — is above the norm of the published literature this project sits in. That is a real asset and none of it should change.

But the project in its current state is **not an A\* paper, and the reasons are structural**:

1. The stated motivation (global computation is infeasible) is contradicted by the algorithmic literature and by the project's own experiments (§2, M1).
2. The central object — r\*(ε), the locality horizon — is currently defined only relative to one estimator (RandomForest) and one feature vocabulary; nothing establishes that it is a property of the *(network, target)* pair, which is what the thesis asserts (M4).
3. Hop-radius is treated as a cross-network currency, but a hop buys wildly different fractions of different graphs. On email-Eu-core the r = 3 "local" view is, to numerical accuracy, the whole graph (M3 — this is quantified below, and it plausibly explains both places where email is the corpus outlier).
4. Zero published methods have been run as baselines, in a field that has produced at least six directly comparable systems since 2019 (M2).
5. Every across-network claim rests on n = 5 observational points, several of which generated the hypotheses they now support, with no multiplicity control over a 3,200-cell grid (M5).

Each is fixable. §5 gives the priority order. §6 gives directions that could produce an A\* paper; two of them (D1, D2) are, as far as an August-2026 literature check can establish, unoccupied.

One result in the project deserves to be pulled out and stated now because it anchors the strongest direction: **the zero-inflation decomposition of Kendall's tau for betweenness has a closed form, it exactly reproduces the handoff's measured "share of scored pairs" numbers on all five networks, and it applies to every published paper in the learned-betweenness literature** (§4). That is the fastest credible route to a top venue this project owns.

---

## 1. Strengths (unchanged from v1, condensed)

- **Verification culture.** Everything checked against an independent implementation; two real bugs (ORCA paw-orbit numbering, H-index convergence direction) caught only because of it. The `make_fig2.py` post-mortem — figure wrong, text dumps right, figure is what gets read — is a publishable lesson in itself.
- **Statistical instincts.** Paired-within-seed differencing; r\*(ε) reported with seed stability; refusal to report a single r\* at an arbitrary ε; shrinkage and heteroscedasticity removed from the failure atlas before reading it.
- **Finding 7 and Finding 10** are the two most publishable results (see §4 and D1/D2).
- **The β_c normalization** (per-network non-backtracking threshold, work at a fixed multiple) is the right construction, and the internal numbers are consistent: for ca-GrQc, 1/λ₁(A) = 0.02192 < 1/λ₁(B) = 0.02250 < HMF 0.0589 — exactly the ordering theory predicts for a sparse graph with degree fluctuations (Karrer–Newman bond-percolation threshold via the Hashimoto matrix; the 2n×2n form used is the Ihara–Bass reduction).

---

## 2. Major objections, with the technical detail worked out

### M1 — The motivation is contradicted by the algorithmic state of the art

The claim "real networks are too large to process globally, yet influence is defined globally" fails quantitatively for every target in the project:

| Target | Global cost, exact | Best known approximation |
|---|---|---|
| PageRank / eigenvector / Katz | O(m) per power iteration; routinely run at 10⁹–10¹¹ edges | — (exact is already near-linear) |
| coreness | O(m) (Batagelj–Zaveršnik) | — |
| closeness | O(nm) exact | pivot/sampling schemes, Õ(m) per node-set |
| betweenness | O(nm) (Brandes) | Riondato–Kornaropoulos (VC-dimension sampling, ε-approx of all scores) and KADABRA (adaptive sampling, near-linear in practice) |
| IC spread (all seeds) | #P-hard exact; Monte Carlo | RIS / reverse-reachable-set sketches (Borgs et al.; TIM/IMM/SSA) with (1−1/e−ε) guarantees at billion-edge scale |

A KDD/WWW reviewer will know this table by heart. The paper's defense ("controlled proof of concept") concedes the point rather than answering it.

**The correct motivation is partial observability, and it is strictly stronger.** A crawler behind an API rate limit, a node in a decentralized protocol, a platform under privacy constraints, an analyst with a sampled subgraph — none of these can see the whole graph *at any compute budget*. Under that framing:

- "how far must you see" is the natural scientific question, and the radius-as-measurement thesis is the centerpiece rather than an apology;
- the small exactly-solvable corpus is the correct instrument (you need exact global ground truth to grade local views against);
- Angle 4 (damage) becomes the same question under a noisy observation channel rather than a bolted-on robustness study, and connects cleanly to the measurement-error literature (N1).

This is a two-paragraph rewrite with paper-fate consequences. Do it before anything else, because it re-ranks which experiments matter.

### M2 — Zero external baselines, and exactly how to fix it cheaply

The comparable-systems list, all verified to exist and be on-topic (August 2026):

- **1D-CGS** (verified via arXiv 2507.19702): inputs are *degree and average neighbor degree only*, 1D-CNN + GraphSAGE, SIR ground truth on Barabási–Albert synthetics, evaluated with Kendall tau. Two input features. Reimplementation is an afternoon; it is also the paper the handoff itself names as the crowded-naive-version evidence, which makes not comparing against it conspicuous.
- **DrBC** (arXiv 1905.10418, CIKM'19): encoder-decoder GNN, pairwise ranking loss, trained on small synthetic scale-free graphs, transfers to real graphs orders of magnitude larger; reports top-N% and Kendall tau. Public code.
- **ABCDE** (2021): successor with progressive DropEdge; same evaluation protocol.
- **BRAVA-GNN / degree-mass message passing** (arXiv 2602.09716, 2026): current betweenness-ranking line.
- **Transferable centrality GNNs** (arXiv 2607.09372, 2026).
- **MONSTOR / MONSTOR+** (verified via DAMI 2025 paper): GNN trained on Monte-Carlo-simulated IC *and* LT ground truth, predicts incremental infection-probability vectors step-by-step (stacked at test time), transfers inductively to unseen networks; ≥0.955 Spearman vs ground truth on unseen graphs; empirically preserves submodularity of the estimated spread function, which is what lets it drive greedy IM.

The cheap, thesis-aligned way to discharge the baseline burden: **run every baseline inside the radius-sweep protocol.** A message-passing GNN with r layers has a receptive field of exactly the r-ball, so the sweep applies unchanged: train DrBC-with-r-layers for r = 0..3 and plot its P(r) next to yours. This converts "no baselines" from a fatal reviewer objection into a new contribution — *the first measurement of the locality horizon of the published methods themselves* — and simultaneously tests M4's estimator-invariance for free.

One methodological caution when doing this (it matters): deep full-graph GNNs degrade with depth for reasons unrelated to information content (over-smoothing, over-squashing), which would bias the measured horizon downward at large r. The clean protocol is **ball extraction**: materialize each node's r-ball as a separate subgraph and train a subgraph regressor (e.g., GIN + readout) on it. Receptive field is then exactly r *by construction*, and model pathology cannot masquerade as an information horizon.

### M3 — Hop-radius is not a cross-network currency; the ball-coverage confound, quantified

The number of nodes within r hops grows initially like k·b^(r−1), where k = mean degree and b = mean excess degree = ⟨k²⟩/⟨k⟩ − 1 (branching heuristic, before clustering and finite-size corrections). Hop-for-hop comparability across networks therefore fails by construction. The corpus's own public statistics make this concrete (verified against SNAP dataset pages):

| Network | n | 90-percentile effective diameter (SNAP) | What r = 3 means there |
|---|---|---|---|
| email-Eu-core | 1,005 | **2.9** | 90% of node pairs are within ~3 hops: the r = 3 "local" view is essentially the whole graph |
| facebook_combined | 4,039 | 4.7 | r = 3 is a large fraction of the graph |
| ca-GrQc / ca-HepTh | 5,242 / 9,877 | ~7–8 | r = 3 is genuinely local |
| p2p-Gnutella08 | 6,301 | ~5.5 | intermediate |

(The SNAP figures are for the raw graphs — email's is measured on the directed graph, so the symmetrized LCC used in the project is even *more* compact.)

Consequences, in increasing order of severity:

1. Every cross-network statement of the form "network X saturates at r = 2, network Y at r = 3" is comparing different fractions of graph seen. Finding 4's headline ("the horizon is a property of the network, not its density") is confounded: coverage-per-hop is itself a function of n, k, and the degree tail jointly.
2. **email-Eu-core is the corpus outlier in exactly two findings (6 and the subgraph-tier-peaks-at-r3 anomaly), and it is exactly the network where r = 3 ≈ whole graph.** "Predictable from r = 3 local information" on email means "predictable from global information" — the locality claim is nominal there. The handoff's own unresolved question ("is email's null structural or small-n?") has a third candidate answer that is computable today: it is a *coverage* artifact.
3. The r\* integer is not the right x-axis for cross-network synthesis at all.

**The fix costs nothing and is not gated on the GPU move.** The BFS shells are already cached per node. Compute, per network: the distribution of |B_r(v)|/n over v for r = 0..3, and the mean edges-examined per node (the cost model already has this). Then (a) publish the coverage table alongside every cross-network figure; (b) re-plot P(·) against median coverage and against edges-examined; (c) re-state Findings 4, 6, 8 against the coverage axis. Pre-registerable prediction: email's two anomalies shrink or vanish on the coverage axis; the collaboration-graph replication (Finding 4) survives. Either outcome is a better paper.

### M4 — r\* is currently a property of the estimator, not of the network

The thesis says "the neighbourhood radius is a measured quantity." A measurement must be instrument-independent within stated tolerance. Currently the instrument is: RandomForest(n_estimators=120, min_samples_leaf=2) over 171 hand-designed features. Two distinct gaps:

- **Model-class dependence.** If ridge regression, HistGradientBoosting, and a ball-extracted GNN produce different P(r) curves and different r\*(ε), then r\* is an artifact of the estimator's inductive bias, and the paper's central object is ill-defined. Nothing currently rules this out; the README even documents the two-line model swap that was never run.
- **Feature-vocabulary dependence.** What the sweep measures is a *lower bound* on the information in the r-ball: I(ball_r; target) ≥ what RF extracts from these 171 features. Finding 3's own history proves the point internally — the measured "richness gain" changed twice as the vocabulary improved (algebraically-derived features → 4-node orbits → 5-node orbits). The same logic applies to the depth axis: the horizon at radius r can only be trusted as far as the vocabulary at radius r is expressive. The ball-extracted GNN (M2) is the capacity probe that bounds this from above: if GNN(r) ≈ RF(r) everywhere, the feature set is near-sufficient and the horizon is real; if GNN(r) ≫ RF(r) at some r, published horizons are vocabulary artifacts at that radius.

**Protocol:** rerun the existing grid with {ridge, HistGradientBoosting} (CPU-cheap; ridge fits in milliseconds), plus ball-GNN at whatever subset is affordable. Report (i) rank correlation of P(r) curves across estimators per (network, target); (ii) agreement matrix of r\*(ε) with seed stability. If invariance holds, that figure *is* the paper's license to say "measured." If it fails, the paper becomes "the horizon depends on the estimator," which is publishable but is a different paper — better to know now.

### M5 — n = 5, hypothesis-generating points, and uncontrolled multiplicity

Three separate problems, each with a concrete fix:

**(a) The unit-of-analysis problem.** Ten seeds control run-to-run noise *within* a network. The headline claims are *across* networks (Findings 4, 8, 10), where the sample size is 5, not 3,200. For Finding 8's ρ = 0.900, p = 0.037: the exact permutation distribution of Spearman's ρ on n = 5 has 5! = 120 orderings, so the two-sided p-value floor is ≈ 0.017 — the result sits near the floor of what n = 5 can ever show, *and* three of the five points generated the hypothesis. The honest confirmatory sample is the two held-out networks, which cannot reach significance at any effect size. The handoff's own caveat ("one swap drops ρ to 0.7") is correct and fatal at this n.

**(b) Multiplicity.** Stars are awarded at "beats 2× paired seed sd" ≈ α = 0.046 two-sided. Under a global null, the 3,200-cell grid would produce ≈ 147 false stars; even a single analysis family (5 networks × 4 targets × 3 hop-gains = 60 comparisons) expects ~3. Fix: Benjamini–Hochberg within each analysis family, report q-values next to the stars, and — better — fit one hierarchical model (tau ~ target × radius, with network as a random effect and seed as the residual level) so partial pooling replaces per-cell testing. This is a day of work with `statsmodels`/`lme4` and removes an entire class of review objections.

**(c) The path to real n.** Two arms, both already planned or possible:
  - *Synthetic corpus* (`stage0_generate.py`, never swept — correctly the top scientific priority). Pre-register the three predictions already implicit in the handoff, in the repo, dated, before the sweep: (1) Finding 8's saturation–blind-spot law holds on families where structure moves one knob; (2) Finding 9's transfer-gap grows with clustering coefficient at fixed n, ⟨k⟩; (3) email's residual null is reproduced by (small n, high coverage), not by density per se — LFR/Chung–Lu at n ∈ {1k, 4k, 8k} × ⟨k⟩ ∈ {6, 16, 32} disentangles what the real corpus cannot.
  - *Real-corpus scale-out*: Netzschleuder / CommunityFitNet host hundreds of cleaned networks in the 10³–10⁴ range. A reduced confirmatory grid — richest tier only, 4 radii, 3 seeds, spread_mean + betweenness — is ~10–15 CPU-minutes per network with the existing pipeline. Fifty networks in a weekend turns Findings 4/8/10 from anecdotes into regressions with confidence bands, and it is the training set D1 needs.

### M6 — Directionality, weights, and the project's own unexamined hyperparameter

**Directionality.** email-Eu-core and p2p-Gnutella08 are directed (verified; email is explicitly "sent at least one email to"). Symmetrization (cleaning decision 1) lets cascades traverse one-way edges backward; the resulting spread and betweenness are properties of a graph on which no real process runs. Weights get a stated defense in the README; direction gets none anywhere. For spreading dynamics direction is the more consequential of the two. Either (a) restrict claims to genuinely undirected systems and add more of them, or (b) run a directed arm — the directed non-backtracking operator and directed IC are both standard, and the in/out horizon asymmetry it would expose is unstudied (D8).

**Weighted cascade and the percolation shortcut.** The handoff correctly notes WC breaks the shortcut. The technical reason is worth writing down: under WC, p(u→v) = 1/deg(v) ≠ p(v→u), so the live-edge sample is a *directed* graph and "spread of v" is v's forward-reachable set, not its undirected component — one BFS per seed per sample. The efficient fix is not to abandon the shortcut but to switch machinery: **reverse-reachable (RIS) sketches estimate all-seeds influence under any triggering model** (WC included) with the same all-nodes-per-sample economics the percolation trick gives for uniform IC. Implementing RR-set estimation would let WC be headlined (it is the more defensible convention for social graphs, as the open-decisions list already says) without giving up the ~900× win.

**The p-multiple.** The project's founding critique is that prior work buries an unexamined hyperparameter (the radius). p = 1.5×β_c is this project's unexamined hyperparameter. Finding 5 (discriminability peaks near criticality) is measured on one network and is, additionally, established physics — near-threshold, ranking is governed by non-backtracking/localization structure rather than degree (Karrer–Newman; Martin–Zhang–Newman localization; Radicchi–Castellano). The archived 1.2× email cache proves multiples matter operationally. Run the multiple ∈ {1.1, 1.25, 1.5, 2, 3} on two structurally unlike networks and annotate every finding as regime-stable or regime-specific. Until then, every claim should carry "at 1.5×β_c" explicitly.

### M7 — The evaluation never reaches the task the field cares about

Kendall tau over all pairs is dominated by the bulk. For influence specifically, the applied question is top-k, and for the influence-maximization audience the object is the *seed set*, whose value is submodular, not additive (Kempe–Kleinberg–Tardos): ranking nodes well and selecting sets well are different problems because top-k-by-individual-influence over-counts overlapping cascades.

Two cheap additions:

1. **Top-k arm**: precision@5% is already computed per cell — plot P(r) with precision@k as the y-axis and check whether r\*(ε) shifts. Plausible new finding either way: if the top of the ranking saturates earlier than the bulk (hubs are locally obvious), the practical horizon is shorter than the reported one; if later (top-k errors are exactly the escaping-cascade nodes of Finding 8), that is a sharper version of the blind-spot result.
2. **One seed-set experiment**: select k seeds by (i) greedy/CELF on true simulations (reference), (ii) top-k by local model at each radius, (iii) degree-discount. Simulate the *set* spread of each on the true graph. This connects the paper to the IM literature's currency and preempts the "ranking ≠ selection" objection with one figure.

Terminology note: betweenness is a brokerage/routing quantity, not "influence" under any spreading model. Call the target family *global structural importance*; it costs one sentence and saves a review point.

---

## 3. Moderate objections

**N1 — Angle 4 partially reinvents the measurement-error literature.** Robustness of centrality to missing/erroneous edges is a 20-year literature: Costenbader–Valente (2003), Borgatti–Carley–Krackhardt (2006), Frantz–Cataldo–Carley, Martin–Niemeyer (Network Science 2019, and the 2021 size/degree follow-up). Angle 4's genuinely new elements — a *learned local model's* transfer under damage, and the damage-training control that separates distribution shift from fragility — survive contact with that literature, but must be positioned inside it. Additionally, uniform edge deletion is the gentlest error model; degree-biased deletion and node removal are the realistic ones, and one extra damage model would show whether "distribution shift, not fragility" is a law of the mechanism or a fact about uniform deletion.

**N2 — Finding 5 is one network and known physics.** Keep it as a *confirmation* with citations (it strengthens credibility as a calibration check); as a claimed discovery it invites a "known since ~2014" annotation.

**N3 — facebook_combined is a sampling artifact.** Verified: the SNAP ego-Facebook graph is the union of 10 survey-collected ego networks (plus ego edges), clustering coefficient 0.6055. Its "dense communities + bridges" morphology is partly an artifact of the collection frame, and Finding 10's mechanism story (conductance detects bridges between sampled ego-nets) may be a story about the frame. The controlled test is a stochastic-block-model / LFR arm with bridge density as the knob; until then the caveat belongs in the finding's headline, not its limits list.

**N4 — The iff-claim is a theorem; prove it, keep the empirical check as a canary.**

> **Proposition.** Let G be a finite connected simple graph, v a vertex, and let betweenness exclude endpoints. Then betweenness(v) = 0 ⟺ ego_betweenness(v) = 0 ⟺ N(v) induces a clique (v is simplicial).
>
> *Proof.* (⇐) If every two neighbours of v are adjacent, then any path s…a v b…t through v can be shortcut via the edge ab, so no geodesic has v as an interior vertex; hence betweenness(v) = 0, and likewise inside the ego graph. (⇒) If some u, w ∈ N(v) are non-adjacent, then d(u, w) = 2 and u–v–w is a geodesic, so σ_uw(v) ≥ 1 and betweenness(v) ≥ σ_uw(v)/σ_uw > 0; the same pair witnesses ego_betweenness(v) > 0 since u, w, and their common neighbours all lie in the ego graph. ∎

Three sentences replace an 11,443-node empirical check, and the proposition powers the tau decomposition in §4 (the zero set is *locally decidable at radius 1*). Note the pipeline check is still worth keeping — it guards the implementation, not the mathematics.

**N5 — The GPU gate blocks the wrong things.** The handoff's own recorded pushback is correct on the merits (6,400 small fits; per-call host-device overhead; half the wall-clock is traversal cuML never touches; every historical win here was algorithmic — 900× percolation, 4–8× merged traversal). What the gate actually blocks: sample efficiency (supervisor directive 5, never started, overnight-CPU-sized), ridge/GBM invariance sweeps (M4, hours), coverage curves (M3, minutes, no fits at all), and the reduced-grid scale-out (M5). Do the prescribed one-hour timing comparison; if cuML does not win decisively, un-gate CPU work the same day. On sm_120/Blackwell, also verify the RAPIDS build ships kernels for it before treating the install as a working environment — this machine has been burned by exactly that once.

**N6 — Correlated Monte Carlo noise in the targets is unmodeled.** The percolation shortcut evaluates all seeds on the *same* 4,000 live-edge samples; in any given sample, every node in the same percolation component receives the identical spread value. Node-level spread estimates therefore have strongly positive covariance. Two consequences: (i) pairwise ranking noise between nodes sharing components is smaller than independent-sampling intuition suggests (helpful, but should be stated); (ii) the "noise report" (a per-node marginal ratio) does not characterize the joint error, and corpus-level statements about small tau differences inherit an effective-sample-size ≪ 4,000. Honest fix: bootstrap over live-edge samples (resample the 4,000 sample indices, recompute targets, propagate to tau) — the cascade arrays are cached, so this is cheap — and quote target-noise-propagated CIs once, in the appendix, to show seed noise dominates (it probably does; show it).

**N7 — The promised target set skips the theoretically interesting targets.** §3 of the handoff names betweenness, closeness, PageRank, eigenvector, Katz, coreness as what the project predicts; results exist for betweenness plus three spreading statistics. PageRank and closeness matter for a specific reason: **PageRank provably converges under local weak convergence** — Garavaglia–van der Hofstad–Litvak, Theorem 2.1 (verified): for directed random graphs converging locally weakly, the PageRank of a uniform vertex converges in distribution to the PageRank of the root of the local limit. PageRank is, in the limit, a bounded-neighbourhood quantity. No analogous local-limit result exists for betweenness or closeness, which are functionals of global geodesic structure. (Phrase it exactly this way — as an existing theorem for PageRank and an absence of one for geodesic measures — not as a proven non-convergence for betweenness; v1 of this review was loose on that point.) Adding PageRank and closeness as targets is exact and cheap at these sizes, and Finding 1's multi-target horizon contrast then has a theoretical spine: short-horizon targets are the provably-local ones. This is also the concrete bridge to the teammate's theory track (D5).

**N8 — (new) The ORCA orbit accounting has an unexplained gap.** ORCA counts 15 node orbits for graphlets on ≤4 nodes (0–14) and 73 for ≤5 nodes (0–72); edge orbits number 12 (≤4-node) and 68 (≤5-node). The project's numbers check out almost everywhere: "all 15 orbits exactly identical" (verification), "12 ORCA edge orbits × 3 statistics" = 36 columns, and the 5-node edge-orbit radius calibration 16+39+12+1 = 68 ✓. But the subgraph tier claims **71** "ORCA 5-node node orbits" — ORCA yields 73. Two orbits are unaccounted for. Probably orbit 0 (= degree, already in the node tier) plus one other was deliberately dropped — but no document says which two or why, and after the paw-orbit incident this project of all projects should have that written down. Ten-minute fix; the kind of loose end referees pull on.

---

## 4. The zero-inflation decomposition, formalized (this is D2's engine)

Let b(v) be true betweenness, Z = {v : b(v) = 0}, z = |Z|/n, m = 1 − z. Partition the n(n−1)/2 node pairs:

- **zero–zero pairs** (fraction ∝ z²/2): ties in the truth; excluded from tau-b's concordant/discordant count (they enter only the tie correction);
- **zero–nonzero "boundary" pairs** (∝ z·m): their true order is entirely determined by membership in Z;
- **nonzero–nonzero pairs** (∝ m²/2): the actual ranking problem.

So the share of tau-b's *scored* pairs that are boundary pairs is

    w = z·m / (z·m + m²/2)

**This closed form exactly reproduces the handoff's measured column on all five networks** (measured values in parentheses): ca-GrQc z = 0.550 → w = 0.710 (71.0%); ca-HepTh z = 0.485 → 0.653 (65.4%); p2p-Gnutella08 z = 0.278 → 0.435 (43.5%); email z = 0.151 → 0.262 (26.3%); facebook z = 0.085 → 0.157 (15.6%). The pipeline's numbers are internally consistent to three decimals — and the formula means the inflation of any published result can be computed from a single scalar, z, which is itself computable for any benchmark graph without running anyone's model.

By the Proposition in N4, membership in Z is decidable *exactly* from the radius-1 ego graph. Therefore a method that solves only the locally-trivial boundary question and ranks the nonzero set at chance scores approximately tau ≈ w·1 + (1−w)·0 = w. On ca-GrQc that floor is **0.71** — against which the project's full-ranking 0.92, and the literature's routinely reported ~0.9 taus on similar sparse graphs, must be read. The corrected protocol: report (i) zero-set classification accuracy (should be ~1.0 for everyone; it is a solved subproblem), and (ii) tau on the nonzero–nonzero pairs only, which is where methods actually differ (the project's own drop: 0.92 → 0.73 on ca-GrQc).

**The paper this implies (D2):** formalize the decomposition; prove the proposition; compute z and w for every benchmark graph used by DrBC, ABCDE, BRAVA-GNN and successors; re-score the public implementations on the nonzero subset; show where the method ranking flips; propose the two-number protocol. Searches found no prior statement of this critique. It is modest-compute, mostly-existing-tooling, and A\*-shaped (KDD research or NeurIPS datasets-and-benchmarks track, where evaluation-pitfall papers with actionable protocols have a track record).

---

## 5. Documentation inconsistencies (unchanged list, one addition)

The 2026-08-27 "documentation correctness pass" reported five stale claims found and fixed; at least four remain in the documents as provided:

| Where | Says | Reality per the same documents |
|---|---|---|
| README §5 | "feature table is **77 columns** … 45/14/16/2", "5 orbits at hop 1, 7 at hop 2, one at hop 3" | 171 (45/50/74/2) everywhere else; the paragraph describes the pre-ORCA-5 era |
| HANDOFF §10 intro | "**Three networks**, all cleaned…" | Five-network table directly beneath it |
| HANDOFF Finding 3 | "on **all three networks**" (twice) | Five-network era |
| HANDOFF §9 | β_c table has 3 rows; "**All three networks** now run at 1.5×" | ca-HepTh and facebook thresholds absent — the doc cannot demonstrate the two new networks are in the regime it mandates |
| README intro | "**two to five minutes** end to end" | README §11 itself: 931 s sweep on 16 cores; HANDOFF: ~70 min/network |
| README §6 vs §2 | model table `n_jobs=1` ("change to -1") | §2: "n_jobs is now -1" |
| **N8, new** | "**71** ORCA 5-node node orbits" | ORCA has 73; the two exclusions are undocumented |

Mechanical fix in the project's own idiom: `verify_docs.py` — grep the prose for the numeric claims that have already burned you (network counts, feature counts, orbit counts, β_c rows vs corpus manifest, timing claims) and fail on disagreement with the manifests. The project checks everything except its own sentences.

---

## 6. Prioritized plan (effort-annotated)

1. **Rewrite motivation around partial observability** (M1) — hours; do first, it re-ranks everything else.
2. **Ball-coverage curves from cached shells** (M3) — minutes of compute, no fits, not GPU-gated; directly tests whether email's two anomalies are coverage artifacts.
3. **Un-gate CPU work; run sample efficiency** (N5, supervisor directive 5) — overnight. Sharp on-thesis question: does r\*(ε) shift when labels are scarce? Pre-register the prediction: scarcity pushes effective r\* *down* (deeper radii add features whose marginal signal is small relative to added variance — e.g., ca-GrQc at 20% labels ≈ 665 training rows vs 145 features at r = 2).
4. **Estimator-invariance sweep: ridge + HistGradientBoosting** (M4) — hours on CPU; the invariance figure is the license for the word "measured."
5. **Synthetic corpus with pre-registered predictions** (M5) — the existing top priority; write the three dated predictions first.
6. **Baselines inside the radius protocol: 1D-CGS, DrBC-at-depth-r, one MONSTOR-style estimator** (M2) — days; converts the biggest gap into a contribution.
7. **Netzschleuder scale-out, reduced grid, 50+ networks** (M5→D1) — a weekend of CPU.
8. **PageRank + closeness targets; connect Finding 1 to the LWC theorem with the teammate** (N7, D5) — cheap compute, high leverage.
9. **Top-k arm + one CELF seed-set experiment** (M7); **p-multiple sweep on two networks; LT arm via RIS sketches** (M6); **degree-biased damage model** (N1).
10. **Prove the proposition (N4), fix §5's table, add `verify_docs.py`, document the 73→71 orbit exclusions (N8), bootstrap-over-samples appendix (N6).**

---

## 7. Novel directions (positioning re-verified August 2026)

**D1 — The horizon predictor.** Meta-model: predict r\*(ε) (and the full P(r) curve shape) for a *(network, target)* pair from cheap whole-network descriptors (n, degree moments, clustering, assortativity, modularity, spectral gap, coverage-per-hop — all in `structure.py`). Training data: synthetic corpus (causal knobs) + Netzschleuder scale-out (realism). Deliverable: a practitioner sketches their graph in seconds and learns how deep to look *before* extracting features. Closest existing work is adaptive-depth GNNs (ADGAT; KDD'23 receptive-field search), which *search* depth per task — i.e., treat it as the hyperparameter your thesis says it shouldn't be. Unoccupied as far as searches show, and it upgrades the project from measurement study to predictive theory.

**D2 — The evaluation-pitfalls paper** (§4). Fastest credible A\* shot; the engine is already built and its arithmetic already validates against your own corpus.

**D3 — Anytime local ranking with a learned stopping rule.** Angle 5's open half becomes an algorithm: per node, expand the ball hop-by-hop; a stopping model trained on the locality-gap signal (boundary_porosity, shell growth ratios — existing features) decides when the ranking marginal gain is exhausted; objective = ranking accuracy under a global edges-examined budget; baselines = fixed-r at matched budget. Prediction worth registering: adaptive allocation beats fixed-r most on the networks with the largest directional blind spots (Gnutella), because that is where depth is unevenly valuable. Algorithmic contribution — the shape A\* applied venues reward most.

**D4 — The locality of complex contagion.** Add a threshold/fractional-threshold simulator (LT is already an open decision) and measure the horizon under complex contagion. Guilbeault–Centola (Nat. Comm. 2021, verified) established that classical centralities misidentify complex-contagion spreaders and that *wide bridges* — a radius-1/2 quantity — govern transmission; the natural, unstudied hypothesis is that complex contagion has a *qualitatively shorter* locality horizon than simple contagion, and that the feature groups that matter flip toward exactly the redundancy/bridge-width features the project already computes. New axis for the multi-target contrast; direct bridge to the ICWSM/WWW social-science audience.

**D5 — The theory bridge.** PageRank has a local-weak-convergence limit theorem (Garavaglia–van der Hofstad–Litvak, verified); geodesic-based targets have no such result; spreading targets sit in between (percolation on the local limit governs them near β_c — the teammate's non-backtracking/locality-horizon track is exactly adjacent). The merged paper — theory classifies targets by whether a bounded-neighbourhood limit exists; the empirical protocol measures the finite-size horizons and their corrections — is the strongest version of this project. Requires N7's targets and an actual working session between the two halves of the team, which the July meeting pattern suggests has not happened.

**D6 — Adversarial locality.** Budgeted rewiring inside a node's own r-ball to move its *predicted* rank; defense value of deeper horizons. Caution flag verified: WWW 2026 already has "Sybil Attacks on Centrality Measures" (abstract paywalled; by definition sybil attacks are fake-identity *injection* against the true measures) — the learned-local-estimator attack surface via rewiring appears distinct, but read that paper before investing; the differentiation must be argued, not assumed.

**D7 — Conformal rank intervals from local features.** CF-GNN (NeurIPS'23) and GraphLCP (2026) do conformal prediction on graphs for classification/regression, not for centrality/influence *ranking*; per-node calibrated rank intervals would make the failure atlas actionable ("this node's rank is [12%, 60%] — spend budget here") and compose with D3 (interval width as the stopping signal). Real exchangeability subtleties on a single graph (features are cross-node dependent); tractable but nontrivial — that is the research content.

**D8 — Directed and temporal horizons.** Directed: two horizons per node (downstream influence vs upstream vulnerability) — the corpus already contains two directed graphs currently being flattened (M6). Temporal: budget becomes (hops × history window). Both are thesis-consistent but bigger lifts; park unless a thesis-length runway opens.

**Recommendation unchanged from v1:** for one submission this academic year, D2 is the fastest credible A\* shot and D1 is the best paper; D5 is the best science conditional on the collaboration actually starting. Do not attempt more than two.

---

## 8. Venue calibration

- **As-is + fixes 1–5:** strong at Complex Networks, Applied Network Science, Network Science, PLOS-tier — a respectable first paper for a second-year student, and nothing to be ashamed of.
- **+ baselines, scale-out, D2:** competitive at CIKM, WSDM, ICWSM, ECML-PKDD; D2 alone, executed sharply, is a plausible KDD / NeurIPS-D&B submission.
- **+ D1 or D5 delivered:** genuine A\* research-track candidate — because there is then a predictive claim or a mechanism, not only measurements.

And the strategic point, stated once more because it was asked for: the 2026-08-27 log shows enormous competent effort spent refining what exists (corpus doubling, three finding revisions, a figure-bug hunt, a doc audit, an environment migration decision) while the supervisor's one explicit request — sample efficiency — remains untouched and is an overnight CPU job. The discipline is world-class; the allocation is not. Fix the allocation.

---

## 9. Threats to the review's own validity

Symmetric honesty: (i) this review had access to HANDOFF.md and README.md only — not the code, the study doc, or the figures; claims about what the code does are trusted from the documents, and any doc-vs-code drift (which this project has demonstrably had) would also mislead this review. (ii) The literature check is search-based as of August 2026; absence of evidence for D1/D2 priority is not proof of absence — run your own search before committing a semester. (iii) The SNAP effective-diameter figures used in M3 are for the raw graphs, not the project's symmetrized LCCs; the direction of the correction (symmetrization compacts the graph further) strengthens M3, but the project should compute its own coverage numbers, which is precisely the recommendation.

---

## 10. Verification log

| # | Claim in this review | Status | Source |
|---|---|---|---|
| 1 | 1D-CGS uses only degree + average neighbour degree; 1D-CNN + GraphSAGE; SIR ground truth on BA synthetics; Kendall-tau evaluation | **Verified** | arXiv 2507.19702 (fetched) |
| 2 | PageRank converges under local weak convergence (Thm 2.1; limit = PageRank of root of local limit) | **Verified** | Garavaglia–van der Hofstad–Litvak, arXiv 1803.06146 (fetched) |
| 3 | "Betweenness is not local-limit continuous" (v1 wording) | **Refined** — no such published theorem; correct statement is the *absence* of any local-limit result for geodesic measures vs an existing theorem for PageRank | v1 correction, this doc N7 |
| 4 | DrBC: encoder-decoder, pairwise ranking loss, trained on small synthetic graphs, transfers to much larger real graphs | **Verified** | arXiv 1905.10418 abstract (fetched); tau/top-N% metrics per the paper's standard protocol |
| 5 | MONSTOR/MONSTOR+: GNN on simulated IC **and LT** ground truth; inductive transfer; ≥0.955 correlation on unseen networks; empirically submodular estimates | **Verified**; v1's "submodularity-based normalization trick" **corrected** to: predicts incremental infection-probability vectors; submodularity is an emergent, measured property | DAMI 2025 paper (fetched via Springer) |
| 6 | Guilbeault–Centola: complex path length / complex centrality; classical centralities misidentify complex-contagion spreaders; wide bridges govern spread | **Verified** | Nat. Comm. 12, 4430 (2021) (fetched) |
| 7 | email-Eu-core: n = 1,005, directed, 90-pct effective diameter **2.9**, clustering 0.399 | **Verified** | SNAP dataset page (fetched) |
| 8 | facebook_combined: 4,039 / 88,234, undirected, union of **10** ego networks, eff. diameter 4.7, clustering 0.6055 | **Verified** | SNAP dataset page (fetched) |
| 9 | Sybil-attacks-on-centrality paper exists at WWW 2026 | **Verified (existence only)** — abstract paywalled; characterization as node-injection follows from the definition of sybil attacks, not from reading the paper | ACM DL listing |
| 10 | Betweenness approximation: Riondato–Kornaropoulos VC-sampling; KADABRA adaptive sampling; RIS/IMM for spread | **Verified** (well-established literature) | standard references |
| 11 | tau-b boundary-pair share formula w = zm/(zm + m²/2) reproduces the handoff's measured column on all five networks | **Verified by direct computation** (0.710, 0.653, 0.435, 0.262, 0.157 vs reported 71.0/65.4/43.5/26.3/15.6%) | this doc §4 |
| 12 | Proposition: betweenness(v)=0 ⟺ v simplicial ⟺ ego_betweenness(v)=0 (connected simple graph, endpoints excluded) | **Proved** | this doc N4 |
| 13 | ORCA orbit counts: 15 node (≤4), 73 node (≤5), 12 edge (≤4), 68 edge (≤5); project's "71" node orbits leaves 2 undocumented; its 16+39+12+1 = 68 edge calibration is consistent | **Verified arithmetic; discrepancy flagged** | ORCA (Hočevar–Demšar); HANDOFF §7.3/§14 |
| 14 | n = 5 Spearman permutation floor ≈ 0.017 two-sided; ~147 expected false stars at 2σ over 3,200 cells | **Computed** | this doc M5 |
| 15 | Threshold ordering 1/λ₁(A) < 1/λ₁(B) < HMF on sparse graphs matches the project's ca-GrQc row | **Verified against the handoff's own table** | HANDOFF §9; Karrer–Newman |
| 16 | Measurement-error centrality literature (Costenbader–Valente 2003; Borgatti et al. 2006; Martin–Niemeyer 2019+) | **Verified** | search results, journal pages |
| 17 | CF-GNN (NeurIPS'23) / GraphLCP (2026): conformal on graphs exists for classification/regression, not ranking | **Verified** | fetched search results |
| 18 | BRAVA-GNN (2026), transferable-centrality GNNs (2026), ABCDE (2021) exist and are on-topic | **Verified (existence/abstracts)** | arXiv listings |

---

*Prepared 2026-08-27 from HANDOFF.md and README.md plus primary-source verification as logged above. Companion styled version: the "Network Influence Referee Report" artifact from this session (v1 — this document supersedes it on technical detail).*

<!-- END docs/networkinfluencetechnicalreview.md -->

---

## <a id="rec-posthoc_B2_hgb_capacity"></a>`docs/posthoc_B2_hgb_capacity.md`

<!-- BEGIN docs/posthoc_B2_hgb_capacity.md sha256=5c0ff4af519e27a304d0d7d051bcc5711bb730986e390463974bf423881659b0 date=2026-09-01 author=Rachit (with Claude) -->
# Post-hoc follow-up — B2, capacity-matched `hgb`

**Written 2026-09-01, AFTER the pre-registered B2 arms were scored and BEFORE this run.**
**Status: POST-HOC. This is not a pre-registration and must never be cited as one.**
**Author:** Rachit (with Claude)
**Supersedes nothing.** `docs/prereg_B2_estimator.md` stands exactly as written, including
its scored verdicts. This document adds a follow-up; it does not amend a prediction.

---

## Why this exists

P3 in `docs/prereg_B2_estimator.md` predicted that `hgb` would land on the forest's side of
the +0.040 threshold for the facebook betweenness r=2 subgraph rung. It did not:

| estimator | node+edge | +subgraph | gain | sd | verdict |
|---|---|---|---|---|---|
| rf | 0.6959 | 0.8250 | **+0.1291** | 0.0043 | — |
| hgb | 0.1940 | 0.1924 | −0.0016 | 0.0141 | **P3 FALSIFIED** |
| ridge | 0.0971 | 0.0956 | −0.0016 | 0.0066 | P1 CONFIRMED |

**That verdict stands and is not being re-run.** P3 is falsified, it is recorded as
falsified, and the threshold has not moved.

But the comparison that produced it was confounded, and the confound was found by
diagnosis rather than by wishing. Isolating one hyperparameter at a time on that cell
(seed 0, `node+edge+subgraph`, facebook betweenness r=2):

| configuration | τ |
|---|---|
| `hgb` as swept (`min_samples_leaf=20`, 100 iters, 31 leaves) | 0.2076 |
| **only** `min_samples_leaf=2` | **0.6286** |
| only `max_iter=1000` | 0.1303 |
| only `max_leaf_nodes=255` | 0.2024 |
| only `max_bins=32` | 0.1413 |
| `rf` as swept (120 trees, `min_samples_leaf=2`) | 0.8231 |

One parameter, changed alone, moves τ from 0.21 to 0.63 — **68% of the entire rf–hgb gap**.
More iterations made it *worse*; more leaf nodes did nothing.

The B2 sweep compared `rf` at a leaf floor of **2**, pinned deliberately by this project,
against `hgb` at a leaf floor of **20**, which is sklearn's default and was never chosen by
anyone. That is not a comparison of inductive biases. It is a comparison of leaf floors.

This is the identical error the pre-registration caught for ridge and then committed for hgb:

> *"An unscaled ridge would be crippled by feature scaling rather than by inductive bias,
> and would produce a false 'invariance fails' verdict."*

Same reasoning, different hyperparameter, missed because it was hiding inside a default.

---

## What will be run

One additional sweep, `hgb_matched`, identical to the `hgb` arm in every respect except
`min_samples_leaf=2`, matching `rf`. All five networks, four targets, 4 radii × 4 richness
rungs × 10 seeds. Output to `estimators/sweep_<tag>__hgb_matched.csv`, following the same
subdirectory rule, for the same reason.

`min_samples_leaf` is the **only** change. `max_iter` and `max_leaf_nodes` stay at their
defaults despite being obvious knobs, because the isolation above shows neither helps and
because changing three things at once is what created this problem.

---

## What this run can and cannot establish

**It can** answer one question: *does the facebook betweenness subgraph rung survive under a
capacity-matched non-linear learner?* That is the question P3 was meant to answer and could
not.

**It cannot** rescue P3. P3 is falsified. A post-hoc run that produces a nicer number does
not un-falsify a pre-registered prediction, and this document exists partly to make that
impossible to forget later.

**It cannot** be reported as though it had been pre-registered. Any write-up must state that
the capacity match was chosen after seeing that the original comparison was confounded.

---

## Declared expectations, recorded before the run

Stated so that the outcome cannot be narrated after the fact. These are **expectations, not
pre-registered predictions**, and they carry less evidential weight precisely because the
confound is already known.

**E1 — `hgb_matched` will beat `hgb` substantially on facebook betweenness.**
Expected τ around 0.60–0.75 at `node+edge+subgraph` r=2, against `hgb`'s 0.1924.
*Basis:* the single-seed isolation gave 0.6286 for `min_samples_leaf=2` alone.
*If it does not:* the isolation did not generalise across seeds and the whole capacity story
is wrong, which would need saying loudly.

**E2 — the subgraph rung gain will remain well below rf's +0.1291.**
*Basis:* stated as a genuine uncertainty rather than a prediction. If the gain appears at
close to rf's size, then the rung is about non-linearity and P3's *intent* was right even
though P3's *test* was broken. If it stays near zero on a now-competent learner, that is far
stronger evidence for the accessibility story than the original P3 could ever have provided,
because it would come from a learner that is demonstrably working.

**E3 — nothing outside betweenness will move.**
The corpus survey showed the rf advantage at `node+edge` is confined to betweenness
(mean +0.1429) and is absent on all three spreading targets (−0.0014 to +0.0012). So
`hgb_matched` should be near-identical to `hgb` on the spreading targets.
*If spreading targets move materially:* the leaf floor was affecting far more than the
diagnosis suggested, and the B2 r\*(ε) agreement counts (hgb 17/20) need re-reading too.

---

## Recorded constraints

- The `rf` baseline is not re-run. Comparisons are against the repaired `sweep_<tag>.csv`.
- Gains are paired within seed, as everywhere else in this project.
- The pre-registered `hgb` arm's files are **kept**, not overwritten. Both live side by side
  so the confound remains inspectable rather than being tidied away.
- Whatever this produces, `docs/prereg_B2_estimator.md` is not edited. If an addendum is
  wanted there it must be append-only and dated.

<!-- END docs/posthoc_B2_hgb_capacity.md -->

---

## <a id="rec-priority_search_D2"></a>`docs/priority_search_D2.md`

<!-- BEGIN docs/priority_search_D2.md sha256=dc8bddb0b31e4111c39c819bba52430e5a6f513a234b697bebf109dcec0a5207 date=2026-09-05 author=unsigned -->
# Priority search — D2 (the zero-inflation scoring critique)

**First pass:** 2026-09-04 (Firecrawl research index only)
**Deep dive:** 2026-09-05 — arXiv via `MCP_DOCKER`, the DrBC forward-citation graph,
ACM DL, and general web. This revision supersedes the first pass.

**Why:** the plan (Part C) makes this a gate, not a formality — *"Before committing a
semester: run an independent priority search. This is the one place where being second
is fatal."*

---

## Verdict

**The evaluation critique is NOT occupied. One of its three components is, and that
component was being carried as if it were ours.**

| Component | Status |
|---|---|
| **(1)** The closed form `w = 2z/(1+z)` for the boundary share of τ-b's scored pairs | **Not found anywhere.** No conflict. |
| **(2)** The τ floor, and the claim that reported τ is not comparable across graphs unless `z` is | **Not found anywhere.** No conflict. This is the core of D2. |
| **(3)** The proposition that betweenness-zero ⟺ simplicial, decidable at radius 1 | **PRIOR ART. Known, published, and in production use as a speedup.** Corrected in `study_doc_v2.md` §24.1 on 2026-09-05. |

The finding on (3) is the one that matters, and it cuts in D2's favour — see below.

---

## The material finding: the premise is already field practice

**Maurya et al., GNN-Bet** (CIKM 2019; *ACM TKDD* 15(5), 2021) prunes from the adjacency
matrix "those nodes that lie on no shortest path". **BRAVA-GNN** (arXiv:2602.09716,
CIKM '26 — the paper the plan already names) states the rule outright as preprocessing:

> *"(1) **Isolated or Leaf Nodes:** Any node with fewer than two neighbors has zero
> centrality... (2) **Clique Neighborhoods:** If a node's neighbors form a clique, any
> shortest path between them will favor the direct edge (length 1) over a path through
> the node (length 2)."*

That is the (⇐) direction of §24.1's proposition, verbatim, in someone else's paper.
Two consequences, and they point in opposite directions:

- **Against us:** §24.1 must cite Maurya et al. and stop reading as an original result.
  Done. The proof is kept — the project still needs the statement, and the ⇔ with
  `ego_betweenness` is the form the pipeline actually asserts — but relabelled.
- **For us, and this is the larger effect:** the field accepts the premise firmly enough
  to *build preprocessing on it*, and then **still reports τ over all nodes**. Everyone
  uses the zero set to go faster; nobody subtracts it from the score. D2's gap is not
  the fact — it is the evaluation consequence of a fact the field already relies on.

That is a much stronger motivating paragraph than "we noticed something." It is also a
harder one to wave away at review: the reviewer most likely to say "this is obvious" is
the one whose own preprocessing step proves the premise is uncontroversial.

**BRAVA-GNN also reasons about τ-b and ties explicitly** — *"the τ_b variant accounts for
ties in the rankings, which is particularly relevant for betweenness centrality, where
large subsets of nodes (e.g., peripheral nodes or symmetric structures) often share
identical scores."* This is the closest anyone comes to D2's claim, and it stops exactly
where D2 starts: it justifies *choosing* τ-b because of the ties, and never asks how much
of the resulting score the ties hand over for free.

---

## The other gap the first pass flagged, now closed

**The DrBC forward-citation sweep.** The 2026-09-04 pass named this as the single most
likely place for the claim to already exist. Run 2026-09-05 over arXiv:1905.10418's
citing set (26 papers evaluated), ranked for evaluation-critique intent.

**Result: negative.** Every citing paper is a new model, a new architecture, or an
application (BRAVA-GNN, inductive-GNN centrality, hypergraph BC, ESN pruning, dismantling,
contact tracing, PathSim, …). Not one is an evaluation-methodology paper. The literature
citing DrBC competes on the metric; it does not examine it.

---

## The ACM DL find, and what it shows

**BeBeCA — *A Benchmark for Betweenness Centrality Approximation Algorithms on Large
Graphs*** (AlGhamdi, Jamour, Skiadopoulos, Kalnis; SSDBM '17;
[10.1145/3085504.3085510](https://dl.acm.org/doi/10.1145/3085504.3085510); code at
`github.com/ecrc/BeBeCA`). This is the field's **one dedicated evaluation-methodology
paper** for BC approximation — a golden standard computed with Brandes on 96,000 CPU
cores, plus a prescribed evaluation script.

Its four metrics are: **average error, maximum error, top-1% hit, Kendall-tau distance.**

**It never mentions the zero set, ties, or stratification.** The one artefact in this
literature whose entire purpose is to say how BC approximation should be scored ships a
Kendall-tau metric with no treatment of the mass of exact zeros that dominates it. If D2
needs a single sentence establishing that the gap is real rather than merely unfashionable,
this is it.

(Scope note: BeBeCA targets *sampling* approximation, not learned models. That widens
D2's relevance rather than narrowing it — the same metric, the same blind spot, in the
neighbouring subfield.)

---

## Adjacent work — cite, none conflicting

| Paper | What it has | Why it is not D2 |
|---|---|---|
| **Maurya et al., GNN-Bet** (TKDD 2021) | The zero-set identification, as a pruning heuristic | **Prior art for §24.1.** Uses it to compute faster; evaluates on the metric unchanged. |
| **arXiv:2602.09716** BRAVA-GNN (CIKM '26) | The pruning rule restated; explicit τ-b/ties reasoning | Chooses τ-b *because* of ties; never quantifies what the ties concede. Closest neighbour. |
| **arXiv:2506.14122** CLGNN | *"imbalance leads learning-based models to overfit to zero-centrality nodes"* | Treats the zero mass as a **training** problem; changes the model, evaluates on all nodes with Spearman + HitsIn@k. |
| **arXiv:2510.16504** Rank-based concordance for zero-inflated data | The statistical machinery for concordance under a mass at zero | Statistics, not benchmarks. Better *estimators*; no claim about published results. **Cite for (1)'s grounding.** |
| **arXiv:2608.09692** Evaluating generative time-series models on data with point masses | The same argument shape in another domain; reversed the authors' own conclusion | **Precedent that this genre publishes**, and a template for the reversal. |
| **arXiv:1404.3325** A weighted correlation index for rankings with ties | τ under ties; notes most alternatives assume no ties | Proposes a different *metric*; does not measure what the ties give away. |
| **arXiv:2408.01157** Computing BC from the 2-core | Degree-one nodes are zero; effect of removing them | Aimed at **estimation cost**. Adjacent to the proposition, not to the scoring claim. |
| **arXiv:2404.00766** SoK: The faults in our graph benchmarks | Graph evaluations ignore datasets' statistical idiosyncrasies | Systems benchmarks. **Framing precedent**, no content overlap. |
| DrBC, ABCDE, 2403.04977, 2607.09372 | The methods D2 would re-score | All report all-pairs rank correlation. **None reports `z`.** Their silence is the evidence. |

---

## Open question — specific, checkable, and it matters

**Does BRAVA-GNN (or GNN-Bet) compute its reported τ-b over *all* nodes, or only over the
nodes surviving the zero-set pruning?**

The paper defines the scoring function over all of V and reports τ-b improvements of up to
24.6%, which reads as all-nodes scoring — but the text does not state the evaluation node
set explicitly, and the pruning section discusses only the effect on message passing. This
is not something to assume in either direction:

- If they score **all** nodes, the inflation applies in full and they are a clean example.
- If they score only **retained** nodes, they have partially implemented D2's protocol by
  accident, without naming it — which would be a significant finding, and would have to be
  credited prominently rather than discovered by a reviewer.

**How to settle it:** read the evaluation code (BRAVA-GNN and GNN-Bet both have public
implementations) rather than the prose. Do this before C3, not before submission — it
changes how C3's re-scoring is framed.

> **SETTLED 2026-09-05 by reading the code, and the answer is neither of the two options
> above.** `utils.py::ranking_correlation` in `github.com/justindachille/BRAVA-GNN` takes a
> `compute_filtered` flag and, when set, computes a **second** Kendall τ over `keep =
> true_arr > 0` — exactly D2's nonzero-subset τ. `betweenness.py:196` passes it
> unconditionally at test time. So they compute the metric, **report only the all-node τ in
> the paper** (v2, 21 Aug 2026, grepped for `filter` / `non-?zero` / `restricted to`: zero
> hits), and **ship the filtered numbers in the repo** — 5,309 of 5,482 algorithm × network
> cells drop, by 5.3% (wiki-topcats) to 66.3% (web-Google) of τ. Full accounting in the plan
> file, §C3a. The gap D2 fills therefore narrows from "nobody computes this" to **"the one
> group that computes it does not report it, and the field has no protocol requiring them
> to"** — which is what C4 proposes. BRAVA-GNN must be credited prominently.

---

## C0 — the zero-inflated rank-correlation prior-art check (2026-09-05)

**Direct-source correction, 2026-09-07.** The published Perrone/van den Heuvel/Zhan
paper (2023, S&PL 199, 109858) has now been read. It explicitly uses tau-b for the
positive-positive component in its proposed sample estimator. The earlier claims
“no counterpart,” “not on arXiv,” and “not obtained” are superseded. A preprint is
arXiv:2208.03155. It does not explicitly state the one-sided p2=0 specialization or
the finite-vector denominator/pair-share w audited here. This is a scope distinction,
not proof of novelty.

Study §24.6 and [the Phase 6 source review](phase6_literature_review.md) replace the
provisional C0 positioning. The old algebra exercise still explains how §24.5's
untied-prediction floor error was found; tied and untied regimes must remain conditional.
The paper leads with a released-corpus support audit and reproducible reporting contract,
credits BRAVA's filtered evaluation, and makes no field-wide absence or priority claim.

## O4 — ADMP-GNN, verified (2026-09-05)

Review v3 cited an ACM DL listing it did not check. Verified against arXiv directly:

- **arXiv 2509.01170v1**, *Adaptive Depth Message Passing GNN* (submitted 2025-09-01).
- **Venue unconfirmed.** The arXiv metadata carries no journal reference; v3's CIKM
  attribution is **not verified here** and must not be asserted in a write-up until it is.
- **What it does:** clusters nodes by centrality (degree, k-core, PageRank, Walk Count ℓ=2)
  and assigns each cluster a common exit layer, so different nodes are read out at different
  message-passing depths. Task is **node classification**.
- **How it relates to this project — near-inverse, and that is the interesting part.** ADMP
  uses centrality as an *input* to choose a per-node depth. This project measures the depth
  required to *compute* centrality. The two are complementary rather than competing, and the
  citation belongs in D1/D3 positioning as evidence that per-node depth adaptivity is live
  in the field — **not** as a baseline, since it neither predicts centrality nor reports τ.

---

## What this search still does NOT establish

- **Google Scholar was not searched directly** — no tool here reaches it, and the ACM DL
  abstract page returns 403 to automated fetches (BeBeCA's methodology was recovered from
  its public repository instead). Coverage of ACM/IEEE venues is therefore via web search
  and repository READMEs, not full text.
- **Semantic search finds papers that *argue* the thing.** A paper quietly reporting a
  nonzero-subset τ in a results table, without prose, would not surface. Spot-check the
  result tables of DrBC, ABCDE, BRAVA-GNN and GNN-Bet manually before submission.
- **The arXiv MCP server appears to ignore its `categories` filter** — a query containing
  "zero central" returned `math.RA` ring theory under `categories: ["cs.SI","cs.LG"]`.
  Its relevance ranking also degrades sharply after ~2 results. Treat its recall as
  weaker than the Firecrawl index's, and do not read a thin arXiv result as absence.

**Recommendation (not a decision — Rachit's to make): proceed to C3.** Components (1) and
(2) are unoccupied across four search surfaces including the citation graph that was the
main risk. Component (3) is prior art, is now cited, and its being prior art strengthens
the motivation rather than weakening the contribution. Settle the BRAVA-GNN evaluation-set
question first — it is an hour of reading someone's code, and it determines whether C3
opens with a clean example or with a credit.

<!-- END docs/priority_search_D2.md -->

---

## <a id="rec-networkinfluencetechnicalreview_v3"></a>`docs/networkinfluencetechnicalreview_v3.md`

<!-- BEGIN docs/networkinfluencetechnicalreview_v3.md sha256=608278bec8a5f64eef8ca4241da6c5074aca8edbe391e1146c9d09e4584a901c date=2026-09-05 author=unsigned (referee report v3) -->
# Local Network-Based Influence Prediction — Technical Referee Report (v3)

**Scope:** this note does not re-litigate v2. Between 2026-08-27 and 2026-09-05 the project
answered nearly all of v2's structural objections (M1, M3, M4, M5b, M7, N4, N5, N8, and the
documentation list are all discharged with measured results — see `HANDOFF.md` and the
2026-08-28 plan for the full accounting). What follows is new: (i) two recent papers that close
gaps v2 flagged as open, (ii) one prior-art risk that needs resolving before the project's
best-positioned direction goes further, (iii) four validity gaps that neither v2 nor the
project's own 2026-08-31/09-05 audits caught, and (iv) four new research directions, numbered
D9–D12 to sit alongside v2's D1–D8, grounded in literature current to September 2026.

**Verdict, updated.** The project has closed the gap between "solid engineering" and "solid
engineering with the statistics to back it up." It has not yet closed the gap between that and
A\*. The two objections that still gate A\* are the same two v2 named — M2 (baselines) and M5a
(n=5) — and this note does not pretend otherwise. But it also finds that the project is one
citation check away from a real risk (§2), sitting on a live, uncited theoretical opening from
the same research group whose theorem it already relies on (§1), and one afternoon of scripting
away from closing part of M2 for free (§4, D11).

---

## 1. Two things v2 said were missing that a January 2026 paper now supplies

### 1.1 A theory paper that states the project's exact open question — and a free baseline inside it

Exarchakos, van der Hofstad, Nagy and Pandey (arXiv 2601.16236, Jan 2026 — same van der Hofstad
whose PageRank local-weak-convergence theorem the project already cites for N7/D5) introduce the
Centrality Comparison Curve (CCC): a rank-agreement curve between any two centrality measures
that is invariant to monotone transforms, converges under local weak convergence for pairs of
local measures, and reduces to a clean closed form (x² for independent rankings, the identity for
identical ones) that gives it interpretable reference lines Kendall τ does not have.

Three things in this paper matter directly:

- **It states, as an explicit open problem, the exact question this project is measuring
  empirically.** Section 4.3 of the paper says plainly that whether distance-based global
  centralities (closeness, betweenness, load) can be well approximated by local quantities on
  appropriate graph sequences is a real and unresolved difficulty, left for future work. This
  project's entire locality-budget programme — P(r), r\*(ε), the five-network corpus — is an
  empirical attack on precisely that sentence. That is a much stronger D5 hook than "our
  teammate does theory and we should talk to them": it is a citable, dated, from-the-source
  statement that the question is open, from the group that proved the one positive result
  (PageRank) the project already leans on.
- **It computes exactly the cheap non-ML baseline M2 asked for.** The paper's own experiments
  include betweenness*k* — betweenness restricted to shortest paths of length ≤ k, computed by
  aborting Brandes'/Dijkstra's algorithm early — compared against full betweenness via CCC, on a
  citation network of several million edges. This is a closed-form, zero-training, radius-*k*
  local approximation to global betweenness that the project has never run against its own
  171-feature ML model. (The same restricted-path idea, attributed to Borgatti and Everett 2006,
  is worked out in isolation in a separate 2021 paper on urban network analysis, arXiv 2103.11437,
  which gives the exact early-termination recipe: run Brandes' algorithm and stop accumulating
  once the current path length exceeds the radius.)
- **CCC is a fourth evaluation metric, and a theoretically cleaner one than precision@k for the
  exact worry M7 raised.** Unlike `precision_at_kpct`, which has no natural null-model reference
  point, CCC has one built in (the x² curve) and a documented convergence story under exactly the
  local-limit machinery the project's `criticality.py` module already touches. It also comes with
  a principled tie-breaking rule (rank first by the primary measure, break ties with the
  secondary measure, break remaining ties uniformly at random) that is worth reading before
  extending the project's own zero-inflation work (§2 below) — it is solving an adjacent problem
  (rank comparison in the presence of structurally forced ties) with a different, more general
  tool.

**Recommended action, cheap:** implement `betweenness_k` for k ∈ {1,2,3} via early-terminated
Brandes — a few hours, no new theory, reuses the BFS machinery `features.py` already has — and
report it alongside the ML model's r\*(ε) on the same axis. Two honest outcomes: if the 171-feature
model beats the trivial truncation by a wide margin at matched radius, that is the cleanest "value
of learning over a naive local rule" result in the project. If it doesn't, that is exactly the
kind of finding this project's own culture says to report rather than bury. Either way it is a
real, citable, near-zero-cost external comparison point — the single cheapest partial answer to
M2 available. See §4, D11, for the fuller CCC-as-metric proposal.

### 1.2 A conformal-ranking method that removes v2's stated reason not to attempt D7

v2's D7 (conformal rank intervals) was flagged as real research content partly because the
existing conformal-on-graphs literature (CF-GNN, GraphLCP) only covers classification and
regression, not ranking. That is no longer accurate as stated. "Distribution-informed Efficient
Conformal Prediction for Full Ranking" (arXiv 2601.23128, Jan 2026) derives the exact distribution
of non-conformity scores for full-ranking conformal prediction — the absolute ranks of calibration
items follow a Negative Hypergeometric distribution conditional on their relative ranks — which
gives materially tighter prediction sets than the conservative bounds prior full-ranking methods
relied on.

This does not make D7 free, but it changes its risk profile: instead of building full-ranking
conformal machinery from nothing, the project would be adapting a named, dated, off-the-shelf
method to per-node rank intervals from local features, which is a smaller and more clearly-scoped
piece of work, and a natural companion to D3's stopping rule (interval width is exactly the kind
of signal a stopping rule would consume). Worth a line in the D7 write-up either way: the "doesn't
exist yet" framing needs updating regardless of whether the project pursues it this cycle.

---

## 2. A prior-art risk in D2 that should be checked before the direction goes further

This is the most important item in this document, because it is the one place where not checking
could cost the project's best-positioned result at review time rather than merely leave value on
the table.

D2's engine is the closed-form decomposition of Kendall's tau-b under zero-inflated betweenness:
partition scored pairs into a "boundary" class (one node zero, one nonzero — order fully
determined by membership in the zero set) and a "nonzero–nonzero" class (the real ranking
problem), giving the boundary-pair share w = zm/(zm + m²/2). The project's own priority search
(`docs/priority_search_D2.md`, 2026-09-05) checked arXiv, a research-index crawler, the DrBC
forward-citation graph, and ACM DL — all network-science- and ML-facing surfaces — and concluded
the closed form was unoccupied.

**There is a parallel statistics literature the search would not have surfaced, because it is
indexed under different keywords in a different community (biostatistics / actuarial science, not
network science).** A specific, cited thread — Pimentel et al. (2015), Denuit and Mesfioui
(2017), Perrone et al. (2023, explicitly on **zero-inflated count data and Kendall's tau**),
Arends et al. (2025), and a March 2026 extension (Arends, Lyu, Mesfioui, Perrone and Trufin,
arXiv 2503.13148, revised through March 2026) — has spent a decade deriving exactly this class of
object: rank-correlation measures decomposed into a zero/nonzero structural component and a
"genuine association" component on the strictly-positive subset, with closed forms and attainable
bounds, motivated by insurance-claim and health-count data where zero-inflation is the norm.

Two things keep this from being a flat "D2 is scooped," and one thing means it needs checking
regardless:

- The statistics literature's setup is **bivariate** zero-inflation — both the true value and the
  predicted value carry their own point mass at zero (their p₁, p₂). The project's setup is
  **one-sided**: true betweenness has structural zeros, but a regression's continuous output
  essentially never lands exactly on zero. Whether the general bivariate formulas collapse to
  something bit-for-bit identical to w = zm/(zm + m²/2) under p₂ = 0, or whether the project's
  simpler derivation is a genuinely distinct (if easier) special case, is an algebra check that
  has not been done.
- Even if the core identity turns out to be the same formula in different notation, **the
  project's actual contribution does not evaporate**: (a) N4's proposition — that the zero set is
  exactly decidable from the radius-1 ego graph — has no analogue in the statistics thread, which
  treats z as an unknown parameter to be estimated, not a locally-computable structural fact; (b)
  the application to the network-centrality-benchmark literature (C3/C4 — computing z and w for
  DrBC, BRAVA-GNN and successors' benchmark graphs, and re-scoring published methods on the
  nonzero subset) is still new regardless of who first wrote the decomposition down; (c) the
  "two-number protocol" proposal (report zero-set accuracy plus nonzero-subset τ) is a methodology
  recommendation for a field, not a formula.
- What must change either way: **the write-up needs to cite this thread if the formulas match,
  and needs to explicitly rule it out if they don't.** A KDD or NeurIPS-D&B reviewer with a
  statistics background — plausible for an evaluation-methodology submission — is exactly the
  kind of reviewer who would know the Perrone et al. line and read an uncited match as a serious
  omission. This is a half-day of algebra and reading, and it should happen before any more time
  goes into C3/C4.

**Recommended action:** read Perrone et al. (2023) directly (it is the one paper in the thread
specifically about Kendall's tau, matching the project's own metric, rather than Spearman's rho),
derive its formula for the one-sided case, and diff it symbolically against w = zm/(zm + m²/2).
Write the outcome into `docs/study_doc_v2.md` §24 either way, in the project's existing "revised
because—" idiom.

---

## 3. Validity gaps neither v2 nor the project's own audits caught

### O1 — Prediction residuals are almost certainly network-autocorrelated, and this has never been checked

Every uncertainty figure in this project (seed sd, paired differencing, the multiplicity
correction) quantifies **model-fitting** variability — the randomness from tree construction and
fold assignment. None of it addresses a different, well-known source of non-independence: nodes
that are close together in the graph tend to have **correlated prediction errors**, because they
share overlapping local neighbourhoods and therefore overlapping features. This is not the same
issue as N6 (correlated Monte Carlo noise in the *targets*, from reusing one set of cascade
samples) — it is correlation in the **residuals of a fitted model**, and it would exist even with
noise-free ground truth.

This is a well-established diagnostic in an adjacent field. Spatial statistics has spent decades
on exactly this problem for geographic data: Moran's I, computed on regression or random-forest
residuals against a spatial weights matrix, is the standard test for whether residual
autocorrelation remains after fitting, and a positive result is read as "the effective sample size
for inference is smaller than the number of observations, and standard cross-validation is
optimistically biased" (this is precisely the finding of the "spatial cross-validation" literature
— e.g. the 2025 *Cartography and Geographic Information Science* study on optimistic bias in
general CV under spatial autocorrelation, and the broader spatial-ML toolchain built around
Moran's-I diagnostics on residuals). The natural graph analogue is immediate: replace the
geographic weights matrix with the network's own adjacency (or a k-hop-decayed version of it), and
compute Moran's I on the out-of-fold residuals already sitting in `cache_oof_<tag>.npz`.

**Concretely:** for each (network, target, radius, seed), compute network Moran's I on the OOF
residual vector using the adjacency matrix (or ego-network overlap) as the weights. If I is
reliably positive and significant, two things follow: (a) the project's own 5-fold CV is *also*
subject to the "optimistic bias" this literature documents for spatial data, meaning within-network
accuracy figures may be mildly inflated beyond what seed variance alone reveals; (b) a **block/
spatial CV** variant — folds defined by graph distance rather than by random assignment, so a
test node's neighbours are never in the training fold — is worth running once as a robustness
check, exactly analogous to the spatial-CV-vs-random-CV comparisons in that literature. This is
zero new fits for the diagnostic itself (Moran's I on existing residuals) and one re-sweep for the
robustness check. It is the kind of thing a referee versed in relational learning or spatial
statistics would ask about, and right now there is no answer in any document.

### O2 — The n=5 problem has a sharper statistical answer already flagged as unbuilt, before the synthetic corpus lands

`docs/study_doc_v2.md` §19b explicitly records that the plan's stronger option — a partial-pooling
model (`tau ~ target * radius + (1 | network)`, with seed as the residual level) — was never
built; Benjamini–Hochberg was used as "the cheap correct answer" while conceding partial pooling
would be "the better one." This is worth treating as more than a nice-to-have. The n=5 problem
(M5a) is currently being addressed by two things: (i) BH correction within families, which
controls false-positive rate but does not borrow strength across networks, and (ii) waiting for
the synthetic corpus, which is the right long-run fix but is not yet run and is a much bigger
piece of work.

There is a middle option that uses only data already in hand: recast r\*(ε) determination as a
**discrete-time hazard model** rather than a per-cell threshold crossing. At each radius r, a
(network, target, ε) cell either has "reached the ceiling" or has not — a binary sequence over
r = 0,1,2,3 that is exactly the shape of grouped survival data. Fitting a discrete hazard model
(complementary log-log or logistic link, standard in biostatistics and econometric duration
analysis — this needs no new machinery beyond what `statsmodels` already provides, which the
project already uses for the BH correction) with structural covariates (coverage-per-hop from
§17a, mean degree, gamma, clustering) as predictors of the hazard of saturating at each radius
gives a **model-based, shrinkage-regularised r\*(network, target)**, rather than five independent
point estimates read off five separate curves. This directly answers the review's complaint that
n=5 cannot support the current per-network comparisons: a hazard model pools information across
networks and radii simultaneously, the same way partial pooling would, and it can be fit and
reported *before* the synthetic corpus sweep, then re-fit *on* the synthetic corpus once it exists
as a second, larger validation. It is a data-analysis exercise on numbers already in
`sweep_*.csv`, not a new experiment — on the order of a day, not a phase.

### O3 — Finding 10's "accessibility, not information" mechanism was diagnosed once and never generalised

The 2026-08-31 audit's most important discovery was that `local_conductance_2` is ~99%
reconstructible from existing columns (held-out R² ≈ 0.99) yet still worth +0.117 τ, because a
random forest cannot form the ratio cut/volume from its constituent shell counts using
axis-aligned splits — the information was always there, the *learner* just couldn't reach it
without help. This is currently reported as a fact about one feature on one network. It is very
unlikely to be the only one.

Axis-aligned trees are well documented to require many splits to approximate a decision boundary
that depends on a ratio or linear combination of features — this is the entire motivating
observation behind oblique decision forests (Menze et al. 2011's original oblique-forest paper;
Tomita et al.'s Sparse Projection Oblique Randomer Forests, which show consistent gains
specifically on tasks with strong feature interactions; and a December 2026 preprint, Jacobian
Aligned Random Forests, which fits an axis-aligned forest first, estimates the gradient of its own
predictions with respect to each input, and uses that to build a single global rotation that
recovers much of oblique forests' accuracy at axis-aligned cost). Any of these — or more simply, a
GAM with explicit pairwise-ratio interaction terms among the shell-count features already in the
table — can serve as a cheap **upper-bound probe**: refit every (radius, tier) cell with an
oblique or ratio-aware learner and ask how many of the corpus's currently-null or negligible
richness effects become significant.

This turns a one-off anecdote into a general, corpus-wide methodological finding with its own
headline number ("X of Y null richness cells become significant under a ratio-aware learner"),
and it interacts directly with M4: it is a *third* class of estimator (distinct from ridge and
HGB) that is specifically diagnostic for the failure mode Finding 10 discovered, rather than a
generic robustness check. Cost is comparable to the existing ridge/HGB sweep — SPORF has an
available implementation, and the GAM-with-interactions variant is a `pygam` or `statsmodels` call
away.

### O4 — The adaptive-depth GNN landscape has moved since 2026-08-27, and D1/D3's positioning needs a one-paragraph update

v2 named ADGAT (KDD'23) as the closest existing work to D1's horizon predictor, on the grounds
that it *searches* depth per task rather than measuring it as a property of the data. Since then,
ADMP-GNN (CIKM, 2025/2026) has published an adaptive-depth message-passing GNN that assigns
per-node layer depth using centrality-based heuristics to cluster structurally similar nodes — a
closer relative than ADGAT, because it is explicitly about *which nodes need more hops*, the same
question Angle 5 and D3 ask. It still differs from this project's framing in the direction that
matters: ADMP-GNN allocates depth to optimise a GNN's own accuracy, using centrality computed
*during* training, whereas D1 predicts the radius **before** any feature extraction happens, from
whole-network descriptors alone, and treats r\*(ε) as a property to be measured rather than a
hyperparameter to be searched. That distinction still holds and is still worth making explicitly,
but the citation needs updating — citing only ADGAT now reads as dated to anyone who has followed
the adaptive-GNN-depth line since 2025, and not citing ADMP-GNN in the eventual D1/D3 write-up
would look like a missed neighbour rather than a considered one.

---

## 4. New research directions (D9–D12)

These sit alongside v2's D1–D8, which are unchanged except where §1 and §3.O4 update their
positioning.

**D9 — Angle 5, made into a live per-node instrument rather than a post-hoc diagnostic.** The
failure atlas (Finding 8) currently answers "which nodes did locality get wrong, after the fact."
Angle 5's declared open half — can a node predict its own gap from local features alone — has a
concrete architecture: train a second, cheap model whose target is not the influence value itself
but the node's own expected rank residual (or a calibrated version of it), using only features the
first model also had. If this "confidence" model is any good, the project gets something
genuinely new and practically shippable: a per-node "trust this" / "look deeper here" flag,
computable at the same radius as the main prediction, with no access to global information. This
is distinct from D3 (a corpus-level budget-allocation stopping rule) and from D7 (calibrated
interval width) — it is a supervised meta-model of exactly the pattern Finding 8 already
documented, turned into something a practitioner could deploy rather than something a researcher
reads off a post-hoc table. Natural evaluation: does flagging the bottom-decile-confidence nodes
for a deeper look recover more of the missed ranking accuracy per edge examined than expanding
every node's radius uniformly? That is a fair, cheap comparison against the project's own existing
cost-model machinery, and it is a genuinely new empirical question, not a rerun of Finding 8.

**D10 — A zero-cost theory-empirics bridge for Finding 4, using data the project has already
computed.** The non-backtracking matrix's leading eigenvalue — which the project already computes
for every network to get β꜀ — is exactly the mean offspring number of the excess-degree branching
process that governs local neighbourhood growth in the configuration-model universality class (a
classical heuristic, now given a rigorous concentration proof for bounded-degree configuration
models by Louvaris, Wise and Yehuda, arXiv 2404.07321). This means the project can, at zero
additional computation, plot the *theoretical* branching-process prediction for |B_r(v)| growth
against the *empirical* BFS-ball coverage curve it already built for §17a, on every network, using
a number it already has in `cache_meta_<tag>.json`. The gap between theory and data at each radius
is a direct, mechanistic measurement of how much clustering and finite-size structure slow ball
growth below the tree approximation — and it is a natural candidate explanatory variable for
Finding 4 ("the horizon is a property of the network") that is stronger than a correlational
observation across five points: it proposes a specific mechanism (deviation from the branching
approximation) and predicts its direction (more clustering → slower-than-predicted growth →
longer horizon), which is falsifiable on the synthetic corpus's clustering-controlled family
(Holme–Kim) without waiting for the rest of D3 (the synthetic sweep) to land. This is the single
cheapest way to convert "the horizon depends on the network, empirically, across five points" into
"the horizon depends on the network *because of a measurable, theory-predicted quantity*," which
is exactly the difference between an observation and a mechanism.

**D11 — CCC and betweenness_k as a fourth metric and a zero-training baseline (expanded from §1.1).**
Beyond the immediate baseline win, CCC's convergence properties under local weak convergence give
the project a metric that is native to exactly the theoretical framework D5 wants to invoke,
rather than borrowed from information retrieval (Kendall τ) or recommender systems
(precision@k). Reporting r\*(ε) under CCC alongside τ and precision@5% (which §19a of the study
doc already shows agree 74% of the time with each other) would let the project make a claim no
version of this document currently supports: that the measured horizon is stable across three
metrics with different theoretical motivations, one of which has a proven large-graph limit for
local measures. That is a stronger form of "measured" than the estimator-invariance work (M4)
alone delivers, because it varies the *evaluation criterion* rather than the *model class*.

**D12 — Generalising D2 from a fact about betweenness into a general degeneracy taxonomy across
centrality measures.** The zero-inflation decomposition is a special case of a broader
phenomenon: any global centrality measure with a large structurally-determined tied or
degenerate subset will have its rank-correlation score inflated by that subset, regardless of
whether the degeneracy takes the form of exact zeros. Eigenvector centrality assigns
near-identical scores to symmetric pendant leaves attached to the same parent; coreness is
constant within a k-shell by construction; PageRank on trees with repeated symmetric subtrees
produces large tied blocks. A field-facing information-retrieval literature already treats ties
in ranked lists as a first-class evaluation problem (McSherry and Najork's tie-aware metric
corrections, and a 2022 JCDL paper extending tie-awareness to Hit@k) — worth reading before
building the taxonomy, since some of the mechanics (how to redistribute credit across a tied
block) are already worked out there and need not be re-derived. Generalising D2 this way turns it
from "a correction that matters for betweenness" into "a general reason every learned-centrality
paper should report a degeneracy-adjusted score for whichever measure it targets" — a
substantially larger claim, and one that would make the two-number protocol (C4) a genuinely
general recommendation rather than a betweenness-specific fix. This is a natural extension of C1–C4
once the prior-art check in §2 is resolved, not a replacement for that check.

---

## 5. Updated priority order

Numbers carry over from v2 where unchanged; new items are lettered.

1. **(a) Resolve the D2 prior-art check (§2).** Half a day. Gates further investment in C3/C4.
2. **(b) Implement `betweenness_k` and report it against the existing r\*(ε) figures (§1.1, D11).**
   A few hours, no new theory, the cheapest real partial answer to M2 available.
3. **(c) Network Moran's I on existing OOF residuals (§O1).** An afternoon; uses data already on
   disk; either clears a real validity concern or surfaces one worth fixing with block CV.
4. Synthetic corpus (v2's M5a/M5c, unchanged priority) — still the load-bearing fix for n=5, and
   now has three sharper, falsifiable predictions waiting on it: Finding 8's saturation law,
   Finding 9's clustering-vs-transfer-gap hypothesis, and D10's branching-process-deviation
   mechanism for Finding 4.
5. **(d) The hazard-model treatment of r\*(ε) (§O2).** A day of analysis on existing data; narrows
   the gap between "BH controls false positives" and "partial pooling is the better answer,"
   before the synthetic corpus makes the pooling model's payoff larger.
6. Baselines inside the radius protocol (v2's M2/D1 main programme, unchanged) — still the biggest
   remaining lift, still the thing that most determines whether this clears the A\* bar.
7. **(e) The oblique/ratio-aware accessibility audit (§O3).** Comparable cost to the existing
   estimator sweep; generalises the project's single most striking 2026-08-31 finding.
8. Everything else v2 already prioritised (B3–B5, D3–D8, N1–N3, N6) at its existing priority,
   updated per §3.O4 where it touches adaptive-depth GNN positioning.

---

## 6. Verification log (new items only)

| # | Claim in this document | Status | Source |
|---|---|---|---|
| 1 | CCC (Centrality Comparison Curve): rank-agreement curve, invariant to monotone transforms, converges under local weak convergence for pairs of local measures; explicitly leaves open whether global distance-based centralities can be well approximated by local quantities | **Verified** | Exarchakos, van der Hofstad, Nagy, Pandey, arXiv 2601.16236 (fetched in full) |
| 2 | betweenness*k* (path-length-restricted betweenness via early-terminated Brandes/Dijkstra) is a known, cheap local approximation to betweenness, attributed to Borgatti and Everett (2006) | **Verified** | arXiv 2601.16236 (fetched); arXiv 2103.11437 (fetched) |
| 3 | Distribution-informed Conformal Ranking (DCR): exact Negative-Hypergeometric distribution of non-conformity scores for full-ranking conformal prediction, tighter than prior conservative bounds | **Verified (abstract)** | arXiv 2601.23128 |
| 4 | Non-backtracking matrix leading eigenvalue of the configuration model concentrates around the mean offspring number of the excess-degree branching process; rigorous concentration result under bounded degrees | **Verified** | Louvaris, Wise, Yehuda, arXiv 2404.07321 (fetched) |
| 5 | Zero-inflated Kendall's tau / Spearman's rho decomposition thread: Pimentel et al. (2015), Denuit and Mesfioui (2017), Perrone et al. (2023, Kendall's tau on zero-inflated count data), Arends et al. (2025), Arends/Lyu/Mesfioui/Perrone/Trufin (2026) | **Verified (existence, abstracts, and partial formula detail)** | arXiv 2503.13148 v2/v3 (fetched), citing Perrone et al. 2023 directly |
| 6 | Oblique random forests (Menze et al. 2011) and Sparse Projection Oblique Randomer Forests improve accuracy specifically on tasks with strong feature interactions, at the cost of per-node optimisation complexity | **Verified** | arXiv 1506.03410 (fetched); ar5iv mirror |
| 7 | Jacobian Aligned Random Forests: fits an axis-aligned forest, uses its own prediction gradients to build a single global rotation, recovers much of oblique-forest accuracy at axis-aligned cost | **Verified (abstract, fetched)** | arXiv 2512.08306 |
| 8 | Moran's I and spatial cross-validation are the standard diagnostics for residual spatial autocorrelation and its effect on CV bias in geospatial ML | **Verified (multiple independent sources)** | EGU26-11342 (Nowosad, Meyer, Schmidinger); *Cartography and GIS Science* 52(5), 2025 (optimistic-bias study); general spatial-ML tooling documentation |
| 9 | ADMP-GNN: adaptive-depth message-passing GNN assigning per-node layer depth via centrality-based clustering heuristics | **Verified (existence, venue, mechanism description)** | ACM DL listing, CIKM proceedings |
| 10 | Tie-aware rank evaluation metrics exist as a distinct IR sub-literature (McSherry and Najork correction; tie-aware Hit@k) | **Verified (existence, abstracts)** | JCDL 2022 short paper (fetched) |

---

## 7. Threats to this document's own validity

Symmetric with v2's own §9: (i) the D2 prior-art risk in §2 is flagged from abstracts and one
fully-fetched paper in the zero-inflated-concordance thread, not from a term-by-term algebraic
comparison against the project's own derivation — the recommended action is exactly that
comparison, and it is possible it comes back clean. (ii) The literature check here is
search-based, run in September 2026; the same caveat v2 raised about absence-of-evidence applies.
(iii) O1's Moran's I proposal assumes network adjacency is the right weights matrix for a
"network Moran's I" analogue of the spatial case; a k-hop-decayed weighting may be more
appropriate given the project's own radius-based framing, and that choice should be made
deliberately rather than defaulted.

---

*Prepared 2026-09-05, building on `networkinfluencetechnicalreview.md` (v2, 2026-08-27),
`HANDOFF.md`, `README.md`, `docs/study_doc_v2.md`, and the 2026-08-28 work-programme plan, plus
primary-source verification logged in §6.*

<!-- END docs/networkinfluencetechnicalreview_v3.md -->

---

## <a id="rec-HANDOFF_C3_astra"></a>`docs/HANDOFF_C3_astra.md`

<!-- BEGIN docs/HANDOFF_C3_astra.md sha256=23712c3f2a0a1f2cbc13ba434b9403791e607cd07c7cc0a30b241ad56f13279d date=2026-09-06 author=Claude (Opus 5) -->
# Handoff — C3 external benchmarks (Phase 6), 2026-09-06 23:48 IST

Written by Claude at the end of a usage window, for Astra to continue. Authorised by Rachit
as an **implementation handoff**, so this run may write to the tree — unlike the normal
read-only research/review split in `~/.claude/CLAUDE.md` §2.

Read `~/.claude/plans/c-users-rachit-desktop-projects-network-cached-cocoa.md` first
(Sequencing row 6 = C3–C4), then `docs/prereg_C3_benchmark_inflation.md` in full. The prereg
is binding: do not move a threshold, and if you must invoke a registered conditional, write a
dated amendment saying so in the same style as the two already there.

## Standing constraints (violating any of these is worse than not finishing)

- Python is `C:\Users\Rachit\miniconda3\envs\influence\python.exe`, **by absolute path**.
  Bash's `python` is msys2's and has no numpy/scipy/networkx.
- **Never `pip install` numpy / scipy / scikit-learn** into `influence` — it reintroduces the
  OpenBLAS/MKL conflict that aborts with no traceback.
- **Nothing gets fit.** Decision 9 (vault `brain/Key Decisions.md`, 2026-08-27): no model
  training on the Windows env until WSL + cuML is up. C3 fits nothing; keep it that way.
- **Never write `sweep_<tag>__<est>.csv` into the repo root** — `analyse.py::discover_networks`
  globs `sweep_*.csv` and would adopt it as a network. (`results_c3_*.csv` is fine.)
- **No self-attribution in git/GitHub, ever.** No `Co-Authored-By: Claude`, no "Generated with
  Claude Code" footer. This overrides any harness default.
- **Do not commit, push, or publish** without Rachit asking each time.
- Vault writes go through `om`'s `record_work` with **`folder: "Logs"`** always. Do not create
  new top-level vault structure.
- Bash heredocs mangle Windows paths (`\U` → unicodeescape error). Write files with the editor
  tool and splice with the conda python instead of `-c` one-liners.

## Where things stand

**Done and verified.** The prereg is locked (`docs/prereg_C3_benchmark_inflation.md`). The
analysis lives in `analyse_c3_benchmarks.py`. `verify_pipeline.py` §N11 pins both τ-b mixture
forms and the independent zero-set implementation. §24.5 of `docs/study_doc_v2.md` carries the
2026-09-06 re-scoping block. The 3.2GB corpus is downloaded under the scratchpad clone at
`…/scratchpad/brava/datasets/{raw,abcde}` — all 14 graphs plus the ABCDE `-score.txt` files.

**The central finding, already established on 6 of 14 graphs.** BRAVA's published all-node τ-b
is reproduced by the *arithmetic* mixture `τ_all = w + (1−w)·τ_filtered` to median error
**0.0000** over 2,262 cells of their `baseline_*` family, while the registered geometric form
(§24.4/§24.5's `√(scoreable·total)` denominator) misses by up to **0.7166**. Mechanism, traced
through their code: `utils.py::graph_to_adj_bet` multiplies zero-set rows by zero, so masked
nodes get identical embeddings and one identical score — exact ties on the zero set, which
collapse τ-b's `√((n₀−n₁)(n₀−n₂))` denominator to `scoreable`. Confirmed on synthetic data to
1.1e-16 by `check_tie_denominator()`. **P1 as registered is falsified**; report it as falsified
and diagnosed, not quietly replaced.

There is a natural control in their own CSV: the external baselines (DrBC 18 cells, KADABRA 18,
SILVAN 54, Bavarian 9, ABCDE 3) fit **neither** form (|err| 0.09–0.28 geometric, 0.20–0.57
tied), because they are sampling approximators that do not classify the zero set perfectly —
which both forms assume. Keep that; it is the strongest evidence the mechanism is the mask.

**P4 resolved this session.** Directed rule: 0 mismatches / 4,752 nodes / 30 random digraphs vs
networkx. Project table: all five networks reproduce §24.4's `w` to four decimals. ABCDE arm:
0 mismatches on amazon (2,146,057), com-youtube (1,134,890), dblp (4,000,148); cit-Patents and
com-lj fail *only* because their shipped scores are clamped at exactly `1.0e-14` (1,679 and
3,802 nodes sitting on the clamp; the three clean graphs have none). **All 1,748 discrepancies
are `rule > 0 & truth = 0`; `rule = 0 & truth > 0` occurs 0 times in 7,762,079 nodes.** The
gate now tests only that falsifying direction on files detected as clamped — see the second
amendment in the prereg and the docstring of `gate_undirected_abcde`.

## The run has since finished — do not re-run it

**Update appended 2026-09-06 23:51, after the handoff above was written.** Background task
`bj0k0000p` completed, exit code 0. The results are on disk:
`results/RESULTS_c3_benchmarks.txt`, `results_c3_structure.csv`, `results_c3_cells.csv`.
Read those rather than spending four minutes reproducing them. soc-LiveJournal1 was not a
problem in the end (65.8s).

**VERDICT: P1 FAIL | P2 PASS | P3 PASS | P4 PASS (gate).**

- **P4 PASSED** under the clamp-aware criterion — 0 rule failures on every graph; amazon,
  com-youtube and dblp exact with no clamp; cit-Patents and com-lj consistency-only.
- **P1 FALSIFIED**, and on both registered criteria: median |error| **0.0786** against the 0.05
  threshold, and median signed error **−0.0770** where the registration required ≥ 0. The sign
  failure is the substantive one — the geometric form *under*-predicts, and the per-graph error
  tracks `z` nearly monotonically, from −0.0005 at wiki-topcats (z=0.0401) to −0.7166 at
  email-EuAll (z=0.9609) and −0.7106 at wiki-Talk (z=0.9588). The post-hoc tie-matched form
  `w + (1−w)·τ_f` fits to median **0.0000** over 5,608 paired cells (max |error| 1.1034).
- **P2 SUPPORTED**, and much stronger on the full corpus than on the 6-graph subset:
  Spearman **ρ = 0.890** over 14 graphs against a ≥ 0.5 threshold (it was 0.657 on 6).
- **P3 SUPPORTED: 12 of 14** graphs against a ≥ 7 threshold. Only p2p-Gnutella31 and
  wiki-topcats carry no configuration within 0.05 of the registered floor `w√(1−z²)`.
- Pairing: 442 plain rows, 404 filtered, 395 configurations with both, 5,608 paired cells.
- `z` spans 0.0401 (wiki-topcats) to 0.9609 (email-EuAll), which is why P2 resolves so sharply.

**Two things to state plainly in the SCORED block rather than smooth over.**

1. On email-EuAll the minimum published all-node τ is **−0.1176** — below zero. So "within 0.05
   of the floor" on that graph is partly a statement about configurations that failed outright,
   not only about the floor being high. Do not let that number do rhetorical work it cannot bear.
2. Against the **post-hoc** tied floor `w`, P3 is 13/14, and on email-EuAll and wiki-Talk *every*
   published configuration (401/401 and 398/398) sits under `w + 0.05`. That is the most striking
   number in the whole analysis and it is **not** the registered one. Label it post-hoc every
   time it appears.

## What to do, in order

1. **Score P2 and P3 on all 14 graphs.** P2 (Spearman ρ ≥ 0.5 between `z` and median drop) was
   ρ = 0.657 on the 6 measured graphs. P3 (≥ 7 of 14 graphs carrying a published τ within 0.05
   of `τ_floor`) stood at 5/6 and is genuinely undecided — do not pre-announce it either way.
   Note `τ_floor` must be the tied-regime floor `w` for BRAVA's own masked family and the
   geometric `w√(1−z²)` for anything continuous; §24.5 now says which applies when.
2. **One correction I flagged but did not apply.** For cit-Patents and com-lj, BRAVA's
   `keep = true_arr > 0` filter ran against the *clamped* score column, so the zero set their
   `_filtered` τ was computed on is theirs (709,724 / 1,151,702), not the true one
   (709,062 / 1,150,616). The effect on `w` is ~2e-4 — far below P1's 0.05 threshold and it
   will not change a verdict — but the SCORED block must say the `z` predicting their number on
   those two graphs is theirs, not the true one. Do not silently conflate them.
3. **Append the `## SCORED` verdict table** to the prereg: P1 falsified (with the diagnosis and
   the arithmetic form's fit), P2 and P3 as they land, P4 passed under the registered
   conditional with the directional criterion spelled out.
4. **Write §26i in `docs/study_doc_v2.md`.** §24.5's new block already forward-references it, so
   it is currently a dangling reference. It should carry the external-corpus numbers, the
   two-mixture-form distinction, the mask mechanism, and the sampling-baseline control.
5. **Re-run all three verifiers to `ALL CHECKS PASSED`:** `verify_pipeline.py`,
   `verify_generators.py`, `verify_docs.py`. `verify_docs.py` will likely complain about §26i
   until step 4 is done.
6. **Update the vault** (`record_work`, `folder: "Logs"`) and the plan file's Sequencing row 6.
7. **C4** (the two-number reporting protocol) has not been started.

## Framing that must not drift

- This is **not** a claim that any method is bad or that rankings flip. BRAVA's own data shows
  configuration ordering largely survives filtering (τ 0.87–0.999). The 2026-09-05 reframing to
  the *level* claim stands; any sentence implying a ranking flip is out of scope and wrong.
- BRAVA-GNN **computes and ships** the nonzero-subset τ. They are the evidence the metric is
  cheap to produce, and must be credited prominently, not framed as a gotcha.
- Neither mixture form is "the" formula. Which denominator τ-b uses depends on whether the
  scored predictions tie on the zero set. N11 asserts both so neither gets promoted again.

<!-- END docs/HANDOFF_C3_astra.md -->

---

## <a id="rec-phase6_plan_row6_pending"></a>`docs/phase6_plan_row6_pending.md`

<!-- BEGIN docs/phase6_plan_row6_pending.md sha256=c632cad79d12424e4efb6c0808cef55e9ea48a18bacee2bd8c5b2d257c79fe57 date=2026-09-07 author=Claude -->
# ~~Pending~~ APPLIED update to the external plan — Sequencing row 6

> **APPLIED 2026-09-07 by Claude.** The staged row below was spliced into line 957 of
> `~/.claude/plans/c-users-rachit-desktop-projects-network-cached-cocoa.md`, replacing the
> 2026-09-05 re-scoping row. This file is now a record, not a pending action. Astra could not
> reach the plan because it sits outside the repo; Rachit has since widened that access, so a
> future handoff should edit the plan directly rather than staging it here.

**Historical staging text — superseded by the directly edited plan and
`phase6_completion_checklist.md`.** The account and row below describe an earlier
handoff, not current permissions or completion. C4's internal run is now explicitly
a code-correctness check, not pilot evidence; the Phase 6 package is recorded in the
current plan.

**Prepared earlier on 2026-09-07.** The external plan update was rejected because the plan is
outside this session's writable project. The original plan has not been changed.
The replacement below is ready to apply to its existing row 6; do not treat this
staged text as evidence that the external update succeeded.

| Phase | Work | Rough scale | Gated? |
|---|---|---|---|
| 6 | **C3 COMPLETE AND SCORED 2026-09-06.** All 14 graphs, 5,608 paired observations across 395 names (404 source-row occurrences). **P1 FALSIFIED**: median absolute error 0.078564, signed error −0.076970. **P2 SUPPORTED**: Spearman rho 0.890110. **P3 SUPPORTED AS REGISTERED**: 12/14 against geometric floor + 0.05; tied-floor diagnostics stay post-hoc. **P4 PASSED under the registered conditional**: cit-Patents/com-lj provide directional consistency only; structural and shipped zeros remain distinct. Tied formula median error 0.000039 on 5,278 baseline_* observations, with large exceptions retained. SCORED table and study §26i written; all three verifiers ALL CHECKS PASSED; vault log filed. **C4 STARTED 2026-09-07**: `docs/C4_two_number_reporting_protocol.md` defines the two primary metrics, reference-only filtering, zero-decision provenance, clamped support and tie metadata; no-fit cached-prediction pilot remains open. No fits or threshold changes. | ~1 week | ~~C0~~ **unblocked 2026-09-05** |

<!-- END docs/phase6_plan_row6_pending.md -->

---

## <a id="rec-phase6_paired_noise_analysis"></a>`docs/phase6_paired_noise_analysis.md`

<!-- BEGIN docs/phase6_paired_noise_analysis.md sha256=8479f3be252eb3f68a84e174ddd95b34bb40b08c0b9b7a6be6f54f53a42868d8 date=2026-09-07 author=unsigned -->
# Phase 6: paired radius-gain target noise

**2026-09-07. Post-hoc analysis rules, written before calculating the paired
outcomes below.** The A7 arms have already been scored. This is a descriptive
follow-through, not a new pre-registration or a revision of A7's verdicts.

## Fixed scope and reporting rules

Use only the saved `results_target_noise_refit.csv` and current
`sweep_<network>.csv` files. No target recomputation, fitting, or new simulation.
Require exactly the five existing networks, three Monte Carlo targets, four
radii (0–3), richest tier `node+edge+subgraph+dynamic`, and 200 complete,
unique replicate indices (0–199) per cell. Reject missing, duplicate, extra,
or nonfinite data. Read the current sweep's matching tier/targets and require
ten paired seeds (0–9); use the established keep-last sweep resume convention.

For all 45 network × target × adjacent-radius comparisons, calculate
`tau(r+1, rep) - tau(r, rep)` using identical replicate keys. Independently
calculate the matching ten within-seed sweep differences. Report both vectors'
means, sample SDs (`ddof=1`), positive/zero/negative counts, and linearly
interpolated 2.5/97.5 percentiles. Percentile spans describe the observed
bootstrap/seed distributions; they are not confidence intervals for a mean,
p-values, or multiplicity-adjusted tests. Report target/seed paired SD ratios
and the radius-wise covariance identity as a diagnostic of cancellation.
Zero SD denominators yield missing ratios, never silently infinite evidence.

Reproduce the existing adjacent-hop heuristic exactly:
`abs(mean gain) > 2 * SD(paired gain)` (`analyse.py`, section 3).
Report its result for the seed distribution and, separately, for the paired
target-bootstrap distribution with the same algebra. Count retained/lost/new
flags. This substitution compares two conditional distributions: it is not an
updated significance test or a combined uncertainty estimate. Do not combine
SDs in quadrature, assume independence, or claim a total uncertainty floor.

## Pairing evidence and limits established before outcomes

In `probe_target_noise_refit.py`, the loop over `(rep, network)` builds
`idx = replicate_indices(...)[rep]` and `bt = targets_from_cascades(c[:, idx])`
once, before the loop over `(target, radius)`. Every radius for a target receives
that same `bt[target]`; the RF/fold seed is fixed (default 0).
`replicate_indices` uses one `default_rng(seed)` and one draw per replicate,
matching the source of `probe_target_noise.py`. The frozen script also builds
one target set per replicate and shares it across radii. Thus within-network,
within-target, within-replicate radius pairing is justified by the recorded
design and the source. We do not pair observations across networks.

The CSV does not store index hashes, RNG seed, or fit seed. It cannot independently
prove that every historical resumed invocation used the same arguments.
The scripts' `--check-pairing` anchor reproduces an unperturbed score; that is
not a verification of resampled index hashes. No cross-arm per-replicate score
difference is attempted because the frozen output contains summaries only.

The saved refits contain **only the richest dynamic tier**. The headline
adjacent-radius tables use `analyse.FULL = node+edge+subgraph`, the richest
structural tier. Structural-tier stars, feature-tier/richness comparisons,
betweenness, and all-star/multiplicity claims remain outside this analysis.
The target bootstrap is conditional on a single fit seed and the cached
live-edge samples; the seed sweep is conditional on the original target.
Their interaction is not observed by this design. No joint uncertainty claim
or general claim about all starred findings follows.

## Outcomes

**Calculated 2026-09-07 from the complete saved corpus, without refitting or
re-simulating.** `analyse_paired_target_noise.py` accepted exactly 12,000 refit
rows (5 networks × 3 targets × 4 radii × 200 unique replicate indices) and the
matching dynamic-tier sweep cells after applying the existing keep-last resume
convention (10 unique seeds 0–9 per cell). The full, machine-readable table is
`results/results_paired_target_noise.csv`; the companion text report is
`results/RESULTS_paired_target_noise.txt`.

Across the 45 fixed adjacent-radius contrasts, the existing seed rule flags
**41/45** and the paired target-bootstrap distribution flags **38/45**. Of the
seed flags, **38 are retained and 3 are lost; no new flag appears**. Four
contrasts meet neither conditional rule. The lost dynamic-tier comparisons are
`email-Eu-core/spread_resid` r1→r2 (seed gain +0.0300 ± 0.00959; target gain
−0.00519 ± 0.02166), `facebook_combined/spread_cv` r1→r2 (+0.00283 ± 0.000956;
+0.00202 ± 0.00166), and `facebook_combined/spread_resid` r1→r2 (+0.00677 ±
0.00193; +0.00462 ± 0.00246). Here and in the CSV, ± is the sample SD of the
paired gain, rather than an error bar on its mean.

The paired target-gain SD is larger than the paired seed-gain SD in most cells:
the target/seed SD ratio has median **1.733** and range **0.700–3.984**. This
does not mean the target variation failed to cancel. The lower/upper target-tau
covariance is positive in all 45 comparisons; the paired SD is a median **0.529**
of the SD obtained by ignoring that covariance and adding the two radius
variances. The CSV records each covariance and confirms the identity
`var(gain) = var(lower) + var(upper) − 2 cov(lower, upper)` (maximum numerical
residual 8.5e-17).

## Confirmed limits after calculation

These are conditional descriptive substitutions into the existing heuristic,
not revised significance tests. The bootstrap distribution conditions on the
cached live-edge samples' resampling and fixed fit seed; the ten-seed sweep
conditions on the original target. Their SDs must not be combined as a total
uncertainty measure. The 2.5/97.5 percentile spans in the CSV are observed
distribution percentiles, not confidence intervals, p-values, or
multiplicity-adjusted tests.

Most importantly, the refit corpus is available only for
`node+edge+subgraph+dynamic`, while the headline adjacent-radius table uses
`node+edge+subgraph`. These 45 results therefore do **not** downgrade or
otherwise alter headline structural-tier stars, all-star counts, feature-tier
comparisons, or claims about total uncertainty. They establish the paired
target-noise behaviour only in the stated dynamic-tier follow-through scope.

<!-- END docs/phase6_paired_noise_analysis.md -->

---

## <a id="rec-phase6_completion_checklist"></a>`docs/phase6_completion_checklist.md`

<!-- BEGIN docs/phase6_completion_checklist.md sha256=fc4dc49732ba8588f7cd932d5a5cdec51ad073650be8c309edff63a89c1cab6b date=2026-09-07 author=unsigned (status corrections by Claude Opus 5, 2026-09-12) -->
# Phase 6 completion ledger

**Current status, 2026-09-12:** initial Task 6 review complete (87 paths), root
integration and final-hash re-review pending. Structural/buffered and later
follow-up reruns are not complete. The historical September 11 "audit not
started" passage below is superseded. Phase 6 remains open; the approved
seven-lane continuation is separately registered in `prereg_phase7_lanes.md`.

**Scope extended 2026-09-08:** the historical no-fit closure below is superseded for
remaining evidence work by the user's new training authorisation. See
`phase6_extension_20260908.md`; structural-tier uncertainty, buffered CV and the full
codebase audit are being completed there. This record retains what was verified on
2026-09-07 and does not claim the expanded work is already complete.

Authorised 2026-09-07: complete work through Phase 6; Phase 7 comes later.
Plan: the existing post-review work programme, Sequencing rows 1–6.

## Scope rulings

- Ruling: finish evidence enforcement, C4 reporting/release usability and paper positioning
  from existing results; no Phase 7 synthetic or scale-out runs. The completed phases are
  not instructions to repeat expensive historical experiments.
- Ruling: preserve all registered verdicts and thresholds. If new evidence contradicts a
  verdict, stop that dependent work and disclose it rather than revise the registration.
- Ruling: no fits, external checkpoint execution, environment changes, author contact,
  commits or publishing. A draft and a venue recommendation are deliverables; submission
  and the final venue choice remain separate user decisions.
- Ruling: existing A7 paired-radius analysis is eligible only from stored, demonstrably
  paired replicates. It must be labelled post-hoc and cannot claim all tiers or total
  uncertainty. Blocked-CV refitting stays outside this no-fit closure.
- Ruling: the workspace is not a Git checkout; changes remain in the authorised directory,
  with artefact hashes and verification logs rather than invented commit/worktree evidence.
- Ruling: use one combined final review for the Phase 6 changes, consistent with the
  project's one-review-pass rule. No CodeRabbit or Claude-dependent filing helpers.

## Work and interfaces

| Task | Produces | Consumer / shared interface | Status |
|---|---|---|---|
| Nodewise fallback enforcement | `verify_c3_fallback.py`, aligned count/hash evidence | Root integrates into final checks; no independent edits to C3/scorer/main verifier | Complete |
| Direct-source literature and venue fit | `phase6_literature_review.md`, public sources | Root paper draft and claim matrix; no model-quality/novelty inference from absent sources | Complete |
| Existing A7 paired-radius analysis | Declared post-hoc design, script, results, limitations | Root appendix/status; no changes to A7 SCORED verdicts | Complete |
| C3 provenance/reporting hardening | Correct structural sensitivity and stable source identity | Existing scorers and audit must keep identical headline values | Complete |
| Phase 6 paper/release package | Paper draft, evidence map, reconstruction instructions | Uses only completed evidence; missing external arrays stay a result | Complete |
| Final verification and combined review | Logs, resolved findings, final phase status | All code/docs lanes above; no Phase 7 work | Complete |

The literature task consumes the old search as leads, not verified facts. Its categorical
absence/novelty language and the cached clamp-heuristic memory are superseded where primary
evidence disagrees. Paper statements will track what was actually obtained and read.

## Closure evidence — 2026-09-07

Phase 6 is complete within the authorised no-fit scope. The manuscript is a draft,
not a submitted or publication-ready claim of global novelty. Start with
`D2_phase6_paper_draft.md`, `phase6_literature_review.md`, and `phase6_reproduction.md`.
The external work plan was edited directly, including Sequencing row 6; the study's
inventory, §24.6 and §26h–§26j now distinguish delivered work from unavailable evidence.

- `results/VERIFY_phase6_pipeline.txt`: ALL CHECKS PASSED, including the new fallback,
  source-pairing/support regression and independent C4 arithmetic checks.
- `results/VERIFY_phase6_generators.txt`, `results/VERIFY_phase6_docs.txt`, and
  `results/VERIFY_phase6_c3_scoring.txt`: ALL CHECKS PASSED.
- Fallback self-tests: 10/10; paired target-noise tests: 6/6. Both reporter examples
  in the reproduction guide were executed successfully.
- Fallback evidence: five required graphs, 24,120 aligned nodes, zero mismatches.
  Paired evidence: 45 contrasts; 38 retained / 3 lost / 0 new / 4 neither heuristic
  flags, with input/source/output hashes in the report.
- Refreshed C4 support audit passes: 15,043,174 decimal values, no off-grid values;
  5,608 finite paired observations. Registered C3 summary remains P1 FALSIFIED
  (absolute 0.07856417907755398, signed -0.07697006904311415), P2 SUPPORTED
  (rho 0.8901098901098902), P3 SUPPORTED 12/14, P4 PASSED UNDER REGISTERED CONDITIONAL.

One combined final review found and resolved a standalone project gate that skipped
missing graphs, missing paired-analysis hash bindings, historical staging-text ambiguity,
and incomplete reproduction inventory. The missing-graph regression failed before the
fix and passed afterward; the full pipeline then passed again. No second broad review
or external review service was run.

## Evidence that remains unavailable

- External per-node method scores/declared decisions: no external two-number pilot.
- Exact positive magnitudes and rounding mode: zero-support enforcement does not
  promote P4's two quantised graphs from consistency to exact verification.
- Historical traversal chronology: current hashes cannot prove past execution order.
- Headline structural-tier paired uncertainty and blocked CV: the saved dynamic-tier
  analysis cannot answer these, and the required new fits were not authorised here.
- Phase 7 controlled synthetic confirmation and later scale-out remain unrun; no new
  D3 registration, fits, installations, checkpoints, contacts, commits or publication.

---

## Expanded-scope evidence lanes, 2026-09-11 (Claude Opus 5)

> Added 2026-09-11 by Claude Opus 5. The checklist above is Astra's and is unchanged.
> **This is not a closure claim.** `docs/phase6_final_audit_protocol.md` makes closure
> conditional on the full Phase 0–6 source audit (Task 6), which Rachit has deferred and
> which has not started. Status: **evidence lanes complete; final audit outstanding.**

### The four gates, re-run 2026-09-11

All four print `ALL CHECKS PASSED`, logged as
`results/VERIFY_phase6_claude_lane5_verify_{pipeline,generators,docs,c3_scoring}_20260911.txt`.
Registered C3 verdicts are unchanged: P1 FALSIFIED (0.07856417907755398), P2 SUPPORTED
(rho 0.8901098901098902), P3 SUPPORTED 12/14, P4 PASSED UNDER REGISTERED CONDITIONAL.
`verify_docs.py` globs `sweep_*.csv`, so its pass is also the check that nothing leaked to
the repository root; no `sweep_<tag>__<est>.csv` exists.

### What the lanes measured

| Lane | Outcome |
| --- | --- |
| Structural paired target uncertainty | 12,000 cells, 45 contrasts: **38 retained / 3 lost / 4 neither / 0 new**. Reproduces A7's dynamic tier exactly — but the two tiers **share their resamples by design**, so this is not independent replication. Study §26k.1. |
| Buffered CV | 25/25 fixtures; all 20,000 logical fold rows accounted for. **~94% of the b=1 buffered tau drop is geometric**, isolated by the size-matched control. 29 of 80 decisions stay unresolved. Study §26k.2. |
| External precision witness | All **five** ABCDE graphs. Clamped pair: 662 / 1,086 targets, **zero qualifying pairs at either threshold** (a null). Unclamped three: **zero structurally-positive printed zeros** among 3,030,420. Study §26i. |
| r=1 attribution | 800 fresh cells, 60 contrasts, 19 flagged. The 5-node orbit step carries the effect (17/20); the 4-node step carries **none** (0/20). Qualified by graph. Study §26k.3. |

> **Updated 2026-09-12 by Claude Opus 5 (Task 6 root integration).** Two rows of the table
> above are no longer current. **r=1 attribution:** the 17/20 for the 5-node step was measured
> with six hop-2 orbits tagged hop 1; rerun on the corrected registries it is **0/20** — the
> r=1 subgraph tier contributes nothing on any target (study §26k.3 superseding block,
> `results/subgraph_gain_pre_post_retag_20260912.txt`). **Structural paired target
> uncertainty** and **buffered CV** are being re-run on the refit corpus
> (`results/phase6_root_integration_controller_20260912.log`); the 38 / 3 / 4 / 0 and 480
> figures are the pre-retag record until that controller writes its terminal line. The
> witness row is unaffected (no fits). The Task 6 audit itself is recorded in
> `results/phase6_task6_coverage_ledger_20260911.json`; closure of Phase 6 still waits on
> its D-stage re-review at final hashes.

### Defects found and fixed while executing

1. A pinned com-lj score SHA-256 was **61 characters**, not 64 — and the same truncated string
   sat in both the spec and the preflight, so every existing check compared it against itself.
   Corrected in both, with a well-formedness assertion added that needs no second copy.
2. The witness's pinned degree range `[3, 18]` was wrong at **both** ends and unsupported by any
   artifact. Replaced: floor 2 (the structural minimum), and the ceiling replaced by a cumulative
   pair-scan budget, which is the quantity the design's resource claim was actually about.
   Approved by Rachit on 2026-09-10.
3. The selector could not express a **zero-target** run, which is the expected outcome on the
   three unclamped graphs; it raised `TypeError` on `int(None)`. Fixed under TDD.

### Additions to the unavailable-evidence list

- The three newly pinned witness graphs were **measured in order to be pinned**, so those pins
  cannot falsify the runs that produced them. Independent support is limited to two agreeing
  topology constructions and two per-graph row-count identities.
- The sklearn config-propagation warnings remain an **open limitation**; the live callsite is
  still unknown and they are not asserted to be harmless.
- Nothing above establishes independent graph generalisation, total uncertainty, or an external
  two-number pilot. Phase 7 remains deferred.

<!-- END docs/phase6_completion_checklist.md -->

---

## <a id="rec-phase6_extension_20260908"></a>`docs/phase6_extension_20260908.md`

<!-- BEGIN docs/phase6_extension_20260908.md sha256=59c6ea15a6dc31d278d7db7f327c703198987196e4aa58f5c841a4058773747b date=2026-09-08 author=unsigned; the expanded-scope timeline the worklog attributes to Astra (GPT-6) -->
# Phase 6 evidence extension and full audit

**Status correction, 2026-09-12:** Task 6 initial review has covered all 87 ledger
paths. Root integration has applied fixes, including the orbit-radius retag and
r=1 refit; long follow-up reruns and final-hash re-review are outstanding.
`phase6_claude_worklog_20260910.md` contains the dated implementation evidence.
Historical "audit not started" entries below are superseded by that record.
The new seven-lane continuation is tracked in `phase7_continuation_20260912.md`;
it does not claim closure of Phase 6.

Authorisation: 2026-09-08, training sweeps necessary to address the remaining evidence
gaps are now authorised. This supersedes the prior no-fit closure; Phase 7 remains later.

## Standing constraints and rulings

- CPU and existing conda influence environment; no PyTorch/GPU or numerical-library installs.
- Preserve registered C3/A7/B1/B2 outcomes as historical results. New evidence is separately
  labelled; report contradictions rather than silently rewriting scored registrations.
- No contacts, commits, pushes or publishing. No estimator sweeps at repository root.
- Ruling: use the existing non-Git workspace and file/hash evidence, not imaginary commits
  or worktree history. No skill cleanup may delete this workspace.
- Ruling: training permission authorises project CPU sweeps, not a silent PyTorch migration
  to execute external GNN checkpoints. Investigate public arrays and source precision first.
- Ruling: write follow-up design before results; exploratory designs informed by earlier
  results are labelled follow-ups, not retroactive preregistration.

## Task 1 — Structural-tier paired target uncertainty

Read probe_target_noise_refit.py, probe_target_noise.py, analyse.py and the Phase 6 paired
noise note. Implement a robust, resumable CPU runner for all five current networks, three
Monte Carlo targets, radii 0–3, richest structural tier (analyse.FULL), 200 shared target
bootstrap replicates at fixed fit seed 0. Use separate results/ outputs. Preserve old A7
results. Record input/source/configuration hashes and resample identity. Validate tier,
seed, graph IDs and cache alignment on resume; reject partial incompatible provenance.
Predeclare the 45 adjacent-radius contrasts and the same descriptive paired SD heuristic,
not a p-value. Compare against matching structural seed sweeps, report covariance and
which matching headline radius flags persist. Bound CPU workers to avoid oversubscription.
Measure a small pilot before full execution; report timing and launch the complete run
when valid. Test invariants and interruption/resume. Own new runner/test/design/results
files only; coordinate required shared edits with root. Report paths and commands, status,
and limitations in docs/phase6_structural_task_report.md. No child agents.

## Task 2 — Requirements inventory (read-only assessment)

Read the full existing external plan and project study/HANDOFF, enumerate every requirement
through Phase 6 and its actual code, results and validation evidence. Identify false done
claims, missing components, stale statuses and necessary reruns. Separate Phase 7/8 and
optional branches. Inspect all project Python file names for audit coverage categories.
Do not edit source or run training. Write docs/phase6_requirements_inventory.md and return
concrete missing work ordered by dependency. This is preparation, not the final audit.
No child agents.

## Task 3 — External precision and prediction feasibility

Inspect current C3/C4 corpus paths/source snapshots and public release documentation.
Seek publicly released per-node predictions without contacting authors or executing GNNs.
Trace ABCDE score generation/printing to establish what can actually be proved about
rounding and positive magnitudes. Design targeted independent CPU checks if useful,
without full all-source exact betweenness on million-node graphs. Record primary sources,
hashes and limits. Existing grid evidence alone is not proof of a rounding mode.
Write docs/phase6_external_precision_followup.md. No source edits/training or child agents.

## Subsequent tasks

4. Based on inventory, implement missing Phase 0–6 work, including defensible buffered/
   blocked CV follow-up and any necessary training; predeclare design and feasibility.
5. Run required checks and reconcile plan/study/paper with measured results.
   Also close the documented r=1 subgraph ablation scope gap: fresh matched current
   feature sets on all five graphs (old three-graph outputs came from an earlier feature
   table), four nested sets (node+edge, plus non-orbit subgraph, plus node orbits with
   index <15, plus remaining node orbits), r=1, ten paired seeds and four reported
   targets. Keep edge orbits in the common baseline; betweenness uses the reported
   log1p objective. Save separate provenance-bound cell and paired-gain results; qualify
   findings by graph rather than perpetuate universal expressive-power language.
6. Full codebase audit across core computation, features/targets, training/leakage/resume,
   statistics/scorers, generators, reporting/documentation and utility scripts. Record file
   coverage and findings; fix actionable defects and rerun affected checks. One final
   broad review campaign, no CodeRabbit. Terra subagents; one implementation lane at a time.

## Progress

- 2026-09-10 19:30 (Claude Opus 5, Lane 0): **both long runs are complete.** The structural
  bootstrap wrote all 12,000 cells and its paired analysis (`Structural follow-up complete`,
  14:11:17, elapsed 442.9 min); the buffered corpus completed 13,971 newly fitted canonical
  folds and its analysis (`Buffered follow-up complete`, 17:12:11). No writer process for
  either run survives. This supersedes the "active"/"Pending" wording in the entries below
  and in `docs/phase6_buffered_cv_execution_status.md`. Identity and accounting validated:
  12,000 structural rows, all tau finite, a single `configuration_sha256`, and **all 42
  provenance `input_sha256` entries rebind to the current files with 0 mismatches**; all
  20,000 buffered logical fold rows accounted (15,472 complete / 2,900 unresolved / 814
  `infeasible_lt30` / 814 `source_infeasible`), 4,000 cells, 480 contrasts (330 scored, 150
  retained as unscored; of the 330 scored, 45 are alias repeats of a b1 row where the
  measured buffer was 1, so 285 are distinct - note added 2026-09-12 by Claude Opus 5,
  P3-08), and cells/folds/OOF/preflight/identity hashes all bind. **These are
  identity and accounting checks only; no scientific result is claimed from them.** Full
  record and remaining lanes: `docs/phase6_claude_worklog_20260910.md`. Task 6 (final
  codebase audit) is deferred by Rachit and remains outstanding, so Phase 6 is **not**
  closed.

- 2026-09-10 07:02: structural Moran completed and authenticated all 5,600 rows.
  Measured buffers resolve 51/80 decisions, leaving 29 explicitly unresolved;
  45/80 decisions have a later significant lag. Buffered preflight accounts for
  all 20,000 logical fold rows: 15,472 ready (including 1,500 aliases), 814
  infeasible, 814 source-infeasible controls and 2,900 unresolved rows. Its 13,972
  canonical fits use pilot-selected four-worker forests. Maximum pilot prediction
  gap is 3.55e-15, tau gap zero. Controlled one-fit stop/resume passed and the
  full run is active. See `docs/phase6_buffered_cv_execution_status.md`; its
  single-fold timing extrapolation is not a full-corpus ETA.

- 2026-09-10 06:56: final buffered review approved the frozen producer, runner,
  analyzer and verifier after all 25 fixtures passed. Consumer validation now binds
  all authoritative permutation settings (199 permutations, batch 512, seed 0).
  Hidden controller PID23948 launched with logs
  `results/phase6_buffered_controller_20260910.log` and `.err.log`; structural
  Moran is running before preflight, worker pilot, controlled stop/resume and
  complete analysis. No buffered result is claimed yet. The structural bootstrap
  remains active under PID31528 and passed 9,463/12,000 cells. The next code lane
  is the bounded external-precision witness implementation; full raw execution
  will follow its scoped review.

- 2026-09-10 morning resume: the earlier controller stopped at 9,433/12,000
  structural cells (last output 02:24 local), with no surviving training writer
  and no recorded exception in the log tail. Controller PID31528 revalidated all
  120 pilot cells and all 9,433 full-run checkpoints, then continued. New logs:
  `results/phase6_structural_controller_resume_20260910.log` and `.err.log`.
  Buffered harness has 24 passing fixtures and cleared producer/controller checks;
  an exact 199/512/0 Moran configuration guard is the remaining scoped review fix.
  `results/phase6_buffered_controller.ps1` is prepared and syntax-valid, not launched.

- 2026-09-09 afternoon C3 scoring check passed again. The 5,608-cell/14-graph
  corpus retains P1 FALSIFIED (MAE 0.07856417907755398; signed error
  -0.07697006904311415), P2 SUPPORTED (rho 0.8901098901098902), P3 SUPPORTED
  (12/14) and P4 PASSED UNDER REGISTERED CONDITIONAL. No registration changed.
  Log: `results/VERIFY_phase6_extension_c3_scoring.txt`.

- 2026-09-09 15:25 local continuation: the same bootstrap PID14396 remains active
  and reached 4,598/12,000 cells. Buffered-CV fixes resumed after another usage pause;
  the five scoped review findings are not yet cleared. No duplicate training writer
  or buffered corpus execution was launched. The original controller remains PID26376.

- 2026-09-09 regression follow-through: refreshed C3 fallback evidence after the
  stage-1 source change, preserving zero mismatches over all 24,120 nodes and
  binding the current stage-1 hash. Pipeline, generator and documentation checks
  all passed. Logs: `results/VERIFY_phase6_criticality_fallback_refresh.txt`,
  `results/VERIFY_phase6_criticality_pipeline.txt`,
  `results/VERIFY_phase6_criticality_generators.txt` and
  `results/VERIFY_phase6_extension_progress_docs.txt`.
  The warning diagnosis now independently reproduces the same sklearn message
  with matching Parallel/delayed and complete configuration when warning filters
  are empty; it does not establish configuration loss in the live run. See
  `docs/phase6_parallel_warning_diagnosis.md`; live callsite remains unknown.

- 2026-09-09 morning continuation: bootstrap PID14396 survived the usage pause and
  passed 2,595/12,000 cells. Repeated scikit-learn configuration-propagation warnings
  are under read-only diagnosis; no frozen source or environment change was made.
  Buffered harness now has 13 passing fixtures and is under scoped review, including
  the required benchmark launch gate. External input preflight verified all four
  pinned hashes and exact raw row counts; see
  `results/phase6_precision_input_preflight.json`. Precision execution remains pending.

- 2026-09-09: criticality repair passed scoped re-review, including exact tree/
  unicyclic handling and the five cached-network comparisons. Buffered-CV harness
  implementation is active. Plan, study and HANDOFF now mark the expanded Phase 6
  as incomplete; `python verify_docs.py` passed after these status updates.

- 2026-09-09 resume: the two-replicate pilot completed all 120 cells. The first
  full-run process stopped after 15/12,000 cells with no recorded Python error;
  no training process survived. Controller PID26376 resumed with separate
  `results/phase6_structural_controller_resume_20260909.*.log` logs, revalidated
  the pilot and accepted all 15 full-run checkpoints before continuing.
  This is progress, not completion of the structural uncertainty result.

- 2026-09-08 resume: controlled pilot stopped correctly at12rows; resumed as PID3088.
  Hidden sequential controller PID10424 waits for it, validates/completes120pilot rows,
  then runs all12000structural cells and the paired analyzer. Controller:
  results/phase6_structural_controller.ps1; stdout/err logs use the same basename.
  Before any restart inspect live processes and those logs; never launch a second
  writer on the same checkpoint. Controller is ordinary finite job sequencing, not
  a scheduler or recurring automation. Source dependencies must stay fixed during it.

- Initial scope and historical evidence reviewed; tasks 1–3 dispatched after this record.
- Requirements inventory completed; scoped Task1 harness review underway before full run.
- Ruling: serialization-only checkpoint fixes do not require another three-setting RF
  timing benchmark. Retain its actual source hash, record the reviewed code delta and
  require current-code prediction equivalence plus real high-precision resume tests.
  Cost if wrong: performance estimates may be stale; correctness still gates on the
  current runner and pilot. Do not relabel the old benchmark as a new-source execution.
- Four missing threshold values measured without fits; results/phase6_threshold_comparison.json.
- Implementation preflight found criticality bug: on a path with four nodes,
  repeated adjacency thresholds flip sign (+/-0.618033988749894) and non-backtracking
  thresholds return +/-1. The LM eigensolver can select the negative bipartite eigenvalue;
  the Ihara-Bass reduction also has extraneous unit roots on trees. Add independent
  path/cycle/complete/tiny-graph tests and repair without regenerating existing caches.
  Validate that the five actual cached graph thresholds remain within tolerance.
- Ruling: the r=1 ablation scope gap is part of this full Phase0–6 repair, although it
  does not block structural bootstrap. Cost if unnecessary: a modest additional matched
  radius-one experiment; avoids retaining an untested five-network interpretation.
- Full completion requires actual sweep results and the final codebase audit; the earlier
  no-fit Phase 6 ledger does not certify this expanded task.

### Progress — 2026-09-11 (Claude Opus 5)

All four evidence lanes executed. Details in `docs/phase6_claude_worklog_20260910.md`; this is
the timeline entry only, so Astra's ledger stays the single record of sequence.

- **Structural bootstrap (Task 1) complete.** 12,000 cells validated, 45 contrasts scored:
  38 retained / 3 lost / 4 neither / 0 new. Study §26k.1.
- **Buffered CV (Task 4) complete.** 25/25 fixtures, all 20,000 logical fold rows accounted
  for; ~94% of the b=1 tau drop isolated as geometric by the size-matched control. Study §26k.2.
- **Precision witness (Task 3) executed on all five ABCDE graphs**, per Rachit's ruling rather
  than the two clamped ones. Clamped pair: 662 / 1,086 targets, zero qualifying pairs (a null).
  Unclamped three: zero structurally-positive printed zeros among 3,030,420. Study §26i.
- **r=1 ablation (Task 5) built and run.** Four new files, TDD, 26-test verifier; 800 fresh
  cells, 60 contrasts, 19 flagged. The 5-node orbit step carries the effect; the 4-node step
  carries none. Study §26k.3. This closes the scope gap HANDOFF flagged on 2026-08-28.
- **Three defects found and fixed:** a 61-character pinned SHA-256 duplicated into both records
  that compared it; a pinned witness degree range wrong at both ends; and a selector that
  crashed rather than publishing a legitimate zero-target run.
- All four gates re-run green, logged under `results/VERIFY_phase6_claude_lane5_*_20260911.txt`.

**Task 6, the full Phase 0–6 codebase audit, has not started** — Rachit deferred it. Phase 6 is
therefore **not** closed: `docs/phase6_final_audit_protocol.md` makes closure conditional on it.

<!-- END docs/phase6_extension_20260908.md -->

---

## <a id="rec-phase6_requirements_inventory"></a>`docs/phase6_requirements_inventory.md`

<!-- BEGIN docs/phase6_requirements_inventory.md sha256=e3ec942d1528fcbac20d74e4cf35809fa6d4b56e7dfebb20d38c8395da95231c date=2026-09-08 author=unsigned -->
# Phase 6 requirements inventory — 2026-09-08

**Purpose.** This is a read-only requirements assessment for the 2026-09-08
evidence extension. It inventories work through Phase 6, distinguishes evidence
actually on disk from historical status prose, and defines the coverage boundary for
the later full codebase audit. It is not a new preregistration, a final audit, or an
authorisation to run work beyond the extension.

**Precedence.** `docs/phase6_extension_20260908.md` supersedes the 2026-09-07
no-fit closure where they conflict. The 2026-09-07 closure remains accurate for its
own authorised scope: it did not establish the two evidence gaps that the extension
now authorises. The study document and scored/preregistered artefacts control factual
claims; a result-file name alone is not treated as proof of a completed requirement.

## Standing constraints for every remaining Phase 0–6 task

- Use the existing CPU `influence` Conda environment. Do not install numerical
  libraries, use GPU/PyTorch, or execute an external GNN checkpoint.
- Preserve registered C3, A7, B1 and B2 verdicts as history. New follow-up results
  must be dated and cannot silently replace scored registrations.
- Use the current non-Git workspace and content hashes as provenance. Do not commit,
  push, publish, contact authors, or create estimator sweep files in the repository
  root.
- Write the design before observing each new follow-up result. A design informed by
  current results is a labelled follow-up, not a retroactive preregistration.
- A completed report must say whether it applies to the richest **structural** tier,
  the distinct dynamic tier, or another explicitly named population. The existing
  dynamic-tier A7 follow-through cannot answer structural-tier questions.

## Evidence ledger through Phase 6

| Requirement | Status and actual evidence | Remaining interpretation limit |
|---|---|---|
| 0.1–0.6: correct the review's factual premises | **Complete.** The five-network corpus, 171-feature ladder, beta-c metadata, objective splice and document guards are recorded in `verify_docs.py`, `verify_pipeline.py`, `repair_column_order.py`, the study §§5–6 and §26b–d. Phase 6 verification logs end in `ALL CHECKS PASSED`. | The comparison table in `HANDOFF.md` still leaves adjacency and mean-field thresholds for ca-HepTh/facebook as explicit TBD values; calculate or remove that comparative claim before treating it as five-network evidence. |
| A1: partial-observability framing | **Complete as documentation.** Study §1 and README/HANDOFF framing describe an information constraint rather than a compute-cost claim. | This is positioning, not an empirical transfer result. |
| A2: coverage control | **Complete and preregistered.** `analyse_coverage.py`, `results/coverage.csv`, `results/RESULTS_coverage.txt`, and `docs/prereg_A2_coverage.md`; study §17a scores the stated prediction. | Coverage is a descriptive control over five networks, not a new independent corpus. |
| A3: top-k arm | **Complete.** `analyse_topk.py`, `results/topk_rstar.csv`, `results/RESULTS_topk.txt`; study §19a. | Precision@1% is coarse and does not become a second independent horizon test. |
| A4: multiplicity | **Complete for the specified BH/BY family analyses.** `analyse_multiplicity.py`, `results/multiplicity.csv`, `results/RESULTS_multiplicity.txt`; study §19b. | The proposed hierarchical model is explicitly not built. It is optional analysis, not a substitute for more networks. |
| A5: document correctness and verification | **Complete.** `verify_docs.py` validates corpus, feature, ladder, beta-c, result and C3 prose consistency; `results/VERIFY_phase6_docs.txt` passes. | Re-run after any result/prose reconciliation in the extension. |
| A6 / N4: zero-set proposition | **Complete as a pipeline proposition/canary.** `analyse_betweenness.py`, `verify_pipeline.py` N10/N11, study §24.1–24.4. Literature correction credits GNN-Bet/BRAVA-GNN. | It is prior art, not a novelty claim; its use cannot establish external score precision. |
| A7 Arm 1 and Arm 2 target noise | **Complete and scored.** `probe_target_noise.py`, `probe_target_noise_refit.py`, `score_a7_arm2.py`, `results_target_noise*.csv`, and `docs/prereg_A7_target_noise.md`; 12,000 refits, with refit target variation larger than seed variation on 56/60 cells. | These are per-cell target-noise measures. They do not yield total uncertainty or a structural-tier paired radius conclusion by themselves. |
| A7 Phase 6 paired follow-through | **Complete only for the dynamic tier.** `analyse_paired_target_noise.py`, `verify_paired_target_noise.py`, `results/results_paired_target_noise.csv`, and `docs/phase6_paired_noise_analysis.md`: 45 contrasts, 38 retained / 3 lost / 0 new. | **Insufficient for headline radius stars.** The study correctly says the structural tier and blocked CV remain unmeasured. This is reopened as extension Task 1. |
| B1: sample efficiency | **Complete and scored.** `probe_sample_efficiency.py`, `analyse_sample_efficiency.py`, `results/sample_efficiency.csv`, and `docs/prereg_B1_sample_efficiency.md`; 100% reproduction gate passed. | The 5% arm has the recorded rows-versus-features caveat. It does not establish cross-network transfer. |
| B2: estimator invariance | **Complete for registered ridge/HGB comparison, plus declared post-hoc capacity match.** `influence/estimators.py`, `stage2_sweep.py`, `analyse_estimators.py`, `estimators/` artifacts, `docs/prereg_B2_estimator.md`, and `docs/posthoc_B2_hgb_capacity.md`; study §26c. | Spreading horizons are estimator-stable only within the stated tolerance. Betweenness is not established as estimator-invariant. The post-hoc HGB result cannot rescue the preregistered falsified P3. |
| Objective correction (Finding 11) | **Complete, adopted for betweenness only.** `probe_objective_horizon.py`, `estimators/*__rf_log1p.*`, `docs/decl_objective_resweep.md`, and `analyse.load()` splice guard in `verify_pipeline.py` N9. | It covers betweenness; it does not rebase three spreading targets or settle transfer validity. |
| C0: prior-art and tau-b correction | **Complete within a targeted direct-source review.** `docs/phase6_literature_review.md`, local source hashes, study §24.6. | No global novelty or absence claim is justified. |
| C1/C2: zero-inflation pair accounting and floor | **Complete.** `analyse_betweenness.py`, `analyse_c3_benchmarks.py::shares`, `verify_pipeline.py` N10/N11, study §24.4–24.5. | Continuous and zero-block-tied formulas are conditional regimes, not universal identities. |
| C3/P4: external benchmark audit | **Complete at the recorded conditional level.** `analyse_c3_benchmarks.py`, `score_c3_results.py`, `verify_c3_scoring.py`, `verify_c3_fallback.py`, C3 structure/scored tables, and `results/RESULTS_c3_fallback.txt`. The five local fallback graphs pass nodewise, both directions, over 24,120 aligned nodes. | P4 remains conditional on the two quantised ABCDE files. Exact positive magnitudes and the release rounding mode are not known. Extension Task 3 owns the feasibility/precision follow-up. |
| C4: two-number reporting | **Bounded implementation complete.** `c4_two_numbers.py`, `audit_c4_support.py`, `results_c4_support_audit.csv`, cache-only smoke report, protocol, and N12 in `verify_pipeline.py`. | No external per-node predictions or declared decisions were released; therefore there is no external two-number pilot. Do not turn the internal cache check into one. |
| C5: matched-radius `betweenness_k` comparison | **Complete.** `analyse_betweenness_k.py`, `probe_betweenness_k_dip.py`, result tables, study §26f. | It is a zero-training local comparator, not a learned published-method baseline. |
| C6/O1: residual autocorrelation | **Complete as diagnosis.** `analyse_moran_correlogram.py`, `probe_moran_zeroset.py`, `results_moran_*.csv`, study §26g. | It supplies measured buffer radii but **not** a blocked-CV effect size. The blocked re-sweep is required follow-up work, not a conclusion already earned. |
| D2 paper/release package | **Complete as a draft and evidence package.** `docs/D2_phase6_paper_draft.md`, literature review, C4 protocol and reproduction guide. | It is neither submitted nor a claim of global novelty, prevalence, external pilot, or venue acceptance. |

## Required work reopened by the extension

These are the dependency-ordered requirements for Phase 0–6 closure under the new
authorisation. They are not Phase 7 replacements.

1. **Structural-tier paired target uncertainty — active extension Task 1.**
   First write the follow-up design, then implement and validate a resumable 200-replicate
   fixed-seed runner over five networks, three Monte Carlo targets, four radii and
   `analyse.FULL`. It must bind input/source/config hashes and bootstrap identities;
   fail on incompatible resume state; use bounded CPU workers; make a small pilot before
   launch; and test pairing and interruption/resume. The result must predeclare all 45
   adjacent-radius contrasts, report covariance and the existing descriptive paired-SD
   rule, and compare only against matching structural seed sweeps. It must not revise
   historical A7 verdicts or label its rule a p-value.

2. **C3 precision and prediction feasibility — active extension Task 3.**
   Inspect the saved BRAVA source/data paths and public release documentation without
   running checkpoints or contacting authors. Determine whether public per-node predictions
   exist and trace ABCDE target generation/printing. Record source hashes and distinguish
   proven printing precision from unproven rounding mode and exact positive values. Any
   proposed CPU check must avoid million-node all-source exact recomputation. This task is
   needed before strengthening, weakening, or otherwise rewording P4.

3. **Blocked-CV follow-up design and feasibility — extension Task 4.**
   Build from the O1 per-cell buffers, rather than inventing one global distance. Before
   fitting, define eligible cells, fold/block construction, exclusion/coverage handling,
   estimator/objective, outputs, comparison to ordinary OOF CV, and stopping conditions.
   The structural paired uncertainty result is informative input to the interpretation but
   does not mechanically determine the blocked-CV design. The output must report a
   robustness result, not silently replace historical five-fold numbers.

4. **Execute only the approved follow-up designs, then reconcile evidence.**
   Run the structural bootstrap and any feasible blocked-CV sweep under the extension's
   CPU/no-install rules. Validate every new output, retain historical scores, update
   the study/paper/plan with the scope distinction, and rerun affected verifiers.

5. **Full codebase audit — extension Task 6.**
   Audit the coverage categories below after the active implementation lanes finish.
   Record each file inspected, defects, fixes, and affected regression commands. This is
   the one final broad review campaign; do not duplicate it with CodeRabbit.

## Deferred, optional, and later-phase branches

**Phase boundary.** The 2026-09-08 extension explicitly keeps Phase 7 later but
does not define a canonical Phase 8 work package. For this inventory, the unrun Part D
program is classified as Phase 7/later. Review ideas beyond it (adaptive stopping,
conformal intervals, directed/temporal horizons) are unscoped later research, not an
invented Phase 8 commitment. They require their own design and authorisation.

| Branch | Classification | Why it is not a prerequisite for the extension closure |
|---|---|---|
| B3 p-multiple sweep | Deferred robustness branch | It tests regime sensitivity at 1.5 beta-c but does not answer structural paired noise or blocked CV. |
| B4 directed arm | Deferred decision/experiment | The current pipeline explicitly symmetrises; a directed model is a separate methods lift. |
| B5 degree-biased damage/node removal | Deferred robustness branch | Existing robustness results are for uniform deletion. |
| r=1 subgraph ablation on ca-HepTh/facebook | Open control for Finding 3 | Needed to generalise the 4-to-5-node claim from three to five networks; it is not a blocker for Tasks 1–3. |
| missing adjacency/mean-field beta-c values | Small documentation/evidence repair | Needed if the five-network threshold-comparison prose is retained; it is a seconds-scale calculation, not a training sweep. |
| D1 published learned baselines | Phase 7/later | Requires a separate method/environment scope; extension forbids a silent PyTorch migration. |
| D2 real-corpus scale-out and cross-network transfer | Phase 7/later | Requires a confirmatory design and new corpus execution. The 14-graph C3 aggregate audit is not substitute evidence. |
| D3 synthetic corpus | Phase 7/later and currently unregistered | Generators exist, but predictions, scoring and stop rules must be written before any sweep. |
| Angle 5 adaptive stopping / cross-network transfer | Later research branch | Neither is supplied by a five-network within-graph CV result. |
| GPU timing/port | Rejected/non-blocking | The measured GPU gate lost; the extension authorises existing CPU work only. |
| neural comparisons | Later and separately authorised | Require a separate environment and remain outside the extension. |

## Stale or potentially misleading status statements

1. **The 2026-09-07 completion ledger is scope-complete, not current full completion.**
   `docs/phase6_completion_checklist.md` says Phase 6 is complete within the no-fit scope,
   while `docs/phase6_extension_20260908.md` explicitly supersedes that scope and says full
   completion requires the new sweeps and audit. Keep the old ledger as history, but add a
   prominent supersession link/status during reconciliation so a reader cannot treat it as
   closure of the expanded Phase 6.
2. **The study's “remain unrun under the no-fit constraint” wording is stale once a new
   follow-up begins.** Study §§26h/26j correctly describe the 2026-09-07 state. After the
   extension work produces evidence, replace only the present-tense status with a dated
   follow-up account; do not rewrite the original limitation.
3. **`HANDOFF.md` is a mixed historical/current document.** Its “What to do next” still
   prioritises the synthetic corpus and lists cross-network transfer, while the extension
   prioritises structural uncertainty, precision and blocked CV. Preserve historical
   rationale, but add a current-pointer section when results are reconciled.
4. **The explicit beta-c TBD cells are unresolved.** `HANDOFF.md` records ca-HepTh and
   facebook adjacency/mean-field values as missing even though the plan made filling them
   a zero-fit requirement. Either calculate them with `influence.criticality` and document
   provenance or remove the unsupported five-network comparison.

## Later codebase-audit coverage map

The repository currently has 61 Python files visible to `rg --files`: 12 core
`influence/` modules and 49 project scripts. The later audit must cover each group;
external source snapshots under `results/phase6_sources/`, cached data, archives and
compiled files are inputs rather than project implementation targets.

| Coverage category | Files to inspect in the later audit | Principal audit questions |
|---|---|---|
| Core graph/target computation | `influence/preprocessing.py`, `criticality.py`, `dynamics.py`, `features.py`, `graphlets.py`, `targets.py`, `structure.py`, `robustness.py` | Parsing/LCC semantics, sparse/dense correctness, numerical invariants, target definitions, feature provenance/tiering, leakage and damage semantics. |
| Learning and metrics | `influence/experiment.py`, `estimators.py`; `stage2_sweep.py`, `run_experiment.py`, `probe_sample_efficiency.py`, `probe_target_noise_refit.py`, `probe_structural_target_noise_refit.py` | Fold isolation, estimator factory/defaults, target transforms, seed/restart semantics, prediction-store alignment, bounded parallelism and resume integrity. |
| Data production and acquisition | `stage0_generate.py`, `stage1_prepare.py`, `fetch_data.py`, `repair_column_order.py`, `_calib.py`, `_calib_edge.py`, `gamma_uncertainty.py` | Synthetic parameter coverage, cache overwrite hazards, hashes/manifests, column-order repair, calibration assumptions and documented warnings. |
| Primary analyses | `analyse.py`, `analyse_coverage.py`, `analyse_topk.py`, `analyse_multiplicity.py`, `analyse_estimators.py`, `analyse_objective_horizon.py`, `analyse_objective_resweep.py`, `analyse_sample_efficiency.py`, `analyse_edge_tier.py`, `analyse_edge5.py`, `analyse_features.py`, `analyse_failures.py`, `analyse_robustness.py`, `analyse_betweenness.py`, `analyse_betweenness_k.py`, `analyse_moran_correlogram.py`, `analyse_paired_target_noise.py` | Selection population, paired calculations, raw-versus-spliced objective handling, multiple-testing claims, missing/duplicate rejection and scope labels. |
| Probes and scorers | `probe_target_noise.py`, `probe_betweenness_k_dip.py`, `probe_moran_zeroset.py`, `probe_objective_horizon.py`, `score_a7_arm2.py` | Exact cache reconstruction, bootstrap identity, numerical stability, scoring thresholds and reporting of post-hoc versus registered results. |
| C3/C4 reporting and external audit | `analyse_c3_benchmarks.py`, `score_c3_results.py`, `verify_c3_scoring.py`, `verify_c3_fallback.py`, `audit_c4_support.py`, `c4_two_numbers.py` | Fail-closed inputs, source occurrence identity, precision claims, conditional P4 direction, portable hashes, decision provenance and tau-b pair arithmetic. |
| Verification suite | `verify_pipeline.py`, `verify_docs.py`, `verify_generators.py`, `verify_paired_target_noise.py` | Independent oracles, adversarial fixtures, missing-input failure, current documentation assertions and regression reach. |
| Presentation/build utilities | `make_fig1.py`, `make_fig2.py`, `make_fig3.py`, `make_fig5.py`, `make_fig6.py`, `docs/build_study.py` | Correct source populations, output naming, stale labels, figure/data correspondence and reproducible document build. |

## Inventory conclusion

The original Phase 6 implementation/reporting package is complete at its stated
no-fit boundary. The expanded closure has three material evidence gaps: structural-tier
paired target uncertainty, a design then execution of buffered/blocked CV, and C3 external
precision/prediction feasibility. The active extension Tasks 1 and 3 address the first and
third. The blocked-CV design is the next dependency after their bounded results. Synthetic
scale-out, learned baselines, GPU work and neural comparisons are later branches and must
not be used to delay the focused Phase 0–6 follow-up or to overstate its outcome.

<!-- END docs/phase6_requirements_inventory.md -->

---

## <a id="rec-phase6_buffered_cv_design"></a>`docs/phase6_buffered_cv_design.md`

<!-- BEGIN docs/phase6_buffered_cv_design.md sha256=0e0ee7b32529ad3627a0ebe8b613721bb7c78139206c68d2234956f03ed256a4 date=2026-09-08 author=unsigned -->
# Phase 6 buffered graph CV follow-up design

Design written 2026-09-08 before fitting the new validation arm. This is a robustness
follow-up informed by the existing C6 residual diagnostics, not a new independent
confirmation or a replacement for the old random-CV results.

## Question and evidence boundary

Measure how ranking quality changes when the training labels are separated from a
held-out graph region, and separate this from the effect of having fewer training labels.
Graph topology and cached structural features remain transductive: the full graph is
available, so this does not establish cross-network transfer or complete independence.
Residual autocorrelation alone does not prove a numerical amount of CV optimism.
Structured validation also changes the prediction task; see Roberts et al. (2017),
[Cross-validation strategies](https://doi.org/10.1111/ecog.02881).

## Inputs and matched analysis

- All five existing project networks, four reported targets, radii 0–3, richest
  structural tier, ten seeds 0–9. Use the reported log1p forest for betweenness only;
  the other three targets retain the pinned raw-target forest.
- Existing C6 CSV uses the dynamic tier. Do not relabel its buffers structural.
  First reproduce the rank-residual correlogram for the matching structural OOF
  vectors, preserving the old output separately. Include graph/cache/registry hashes.
- Use its common lag range 1–7, seed-wise first non-significant testable lag, then
  ceiling of the median across all ten seeds per network/target/radius. A cell with
  any unresolved seed has no fully established buffer: report unresolved rather
  than silently discard it. A sensitivity at fixed b=1 can still be reported.
- For every selected cutoff, flag whether later testable lags remain significant;
  release the entire lag curve. The cutoff is a diagnostic-derived sensitivity,
  not a claim that all dependence disappears there. Do not introduce a post-results
  effect-size cutoff to improve feasibility.
- Preserve the old alpha/d decision rule only for comparability and name it explicitly.
  It is not a general family-wise-error guarantee. A seven-lag Bonferroni sensitivity
  uses alpha/7; neither non-significance rule proves independence.

## Splits, buffers and controls

Construct five deterministic, graph-only regions per seed. Use a seeded breadth-first
ordering on the connected graph and divide that ordering into five near-equal contiguous
segments; record membership and acknowledge that segments need not induce connected
subgraphs. This avoids outcome-dependent grouping and preserves every node exactly once
as a test node. Do not call the segments balanced connected communities.

Precisely: `default_rng(seed).integers(n)` selects the root; FIFO BFS explores sorted
ascending cached neighbour IDs, marking a node visited on enqueue. The graph is the
validated connected LCC, so the ordering must cover all n IDs exactly once. Divide it
with `np.array_split(order, 5)`. Bind the membership to graph hash, seed and construction
version and save explicit test/train node IDs, not just counts.

For each held-out region, exclude all candidate training nodes whose shortest graph
distance to ANY test node is <= b. Verify that every retained training node is farther
than b using an independent check on constructed graphs. Each cell has these arms:

1. Region holdout, no buffer: all other nodes train.
2. Region holdout, b=1 fixed sensitivity.
3. Region holdout, measured buffer where defined.
4. Size-matched control for each buffered arm: sample the same number of training
    nodes uniformly from the unbuffered candidates with a declared deterministic seed.

Control RNG seed: first eight bytes (little endian unsigned integer) of SHA256 of the
UTF-8 string `network|target|radius|seed|fold|arm|phase6-buffer-v1`. Sort selected IDs
after sampling without replacement. Record them and assert exact buffered/control
training-count equality. Near-test nodes are allowed in controls by design.

At least 30 training rows are required per fold. This threshold is a feasibility guard,
not a statistical adequacy claim. When buffering leaves fewer, retain the fold status
and counts; do not shrink b or substitute an unbuffered fit. Report a full-population
OOF tau only if all five folds succeed. Partial vectors, if released, carry NA and an
explicit subset label; do not compare their tau with a full-population reference.

Use identical estimator hyperparameters, fold partitions and model seeds in the paired
arms. Compare with the existing random-fold reported results separately: the split
geometry differs, so it is not a pure sample-size contrast. Training-size controls share
the region's test nodes and isolate sample count conditional on this test population.
Monte Carlo targets still share the same 4,000 live-edge samples and graph-wide residual
construction. Removing neighbouring training labels does not remove that dependence.

## Outputs, execution and verification

Write new scripts/tests and results/ files; preserve every previous sweep. Save nodewise
OOF predictions, fold identities, training/exclusion counts, failure reasons, provenance
and per-cell timings. Resume must validate configuration, input/source hashes and the
exact output key set; completed rows cannot cross configurations.

Start with split/buffer feasibility on all cells before any fit, then a timed small fit.
Use bounded CPU workers and memory-mapped inputs where useful. Report per-network/target
curves, paired differences and descriptive seed spreads; no new formal significance
claim or old-star replacement follows from a changed evaluation task. If most measured
buffers exhaust the training data, that is the result, not permission to weaken them.
The upper-bound workload is 20,000 forest fits (4,000 five-fold cell/arm evaluations); report
the feasible count and pilot-derived time estimate before launch. Freeze job counts,
output keys and resource settings before checkpointing. Reuse identical b=1/measured
arms when their buffer is identical, with explicit alias metadata rather than duplicate
fits. No reduced-scope result may be labelled the complete design.

Tests must independently check BFS determinism and complete fold coverage, path/cycle
buffer distances, complete-graph exhaustion, matching control counts, no test labels in
training, log1p only on betweenness, and interrupted/incompatible resume rejection.

<!-- END docs/phase6_buffered_cv_design.md -->

---

## <a id="rec-phase6_buffered_implementation_brief"></a>`docs/phase6_buffered_implementation_brief.md`

<!-- BEGIN docs/phase6_buffered_implementation_brief.md sha256=7f4a060c5afdc0db7949c823c311688c82675c85b203b4b08b760e14c5010056 date=2026-09-08 author=unsigned -->
# Phase 6 buffered-CV implementation brief

Prepared 2026-09-08 before implementation or fitting. This specifies a separate
robustness follow-up. It does not alter the random-fold sweeps, the dynamic-tier
C6 CSV, or any registered result.

## Fixed scope and input contract

Run the five networks in `data/manifest.json` (`ca-GrQc`, `ca-HepTh`,
`email-Eu-core`, `facebook_combined`, and `p2p-Gnutella08`), all four reported
targets, radii `0..3`, ten seeds `0..9`, and `analyse.FULL`
(`node+edge+subgraph`). That tier excludes `dynamic`; the existing C6 artifact
`results_moran_correlogram.csv` remains the historical dynamic-tier result and
must retain that description.

Use the existing preprocessed LCC from
`influence.preprocessing.load_edgelist(raw_path, name=network)`. It supplies a
sorted CSR adjacency: `Network.nbrs[v]` is the cached ascending-neighbour-ID
slice after `adj.sort_indices()`. Before any result checkpoint, require:

* raw graph, `cache_features_<network>.csv`, `cache_targets_<network>.csv`,
  `cache_registry_<network>.csv`, `cache_meta_<network>.json`,
  `sweep_<network>.csv`, and the appropriate reported OOF store;
* cache row identity: `node == arange(n)` in features and targets, and
  `features.original_id == network.original_ids` as in
  `probe_structural_target_noise_refit.validate_alignment`;
* registry selection through
  `probe_structural_target_noise_refit.structural_features(registry, features,
  radius)`, including its dynamic-tier assertion and the matching structural
  sweep feature count;
* SHA-256 hashes for every input above, the manifest, new runner/analyser,
  `analyse.py`, `analyse_moran_correlogram.py`, `influence/experiment.py`,
  `influence/preprocessing.py`, `probe_structural_target_noise_refit.py`, and
  the new split-construction version string.

Targets come from `cache_targets_<network>.csv`. For `betweenness` only, train
each forest on `log1p(y_train)`, convert predictions back with `expm1`, and
score Kendall tau against the original `y_test`. The other three targets train
and predict on their raw scale. This is the current reported-objective rule in
`analyse.py`; no blanket transform is allowed.

## Structural Moran prerequisite

Add `analyse_structural_moran_correlogram.py`; do not change or overwrite
`analyse_moran_correlogram.py` or `results_moran_correlogram.csv`. It may reuse
the latter's pure `rank_pct`, `shell_masks`, and `morans_i` functions, but it
must load structural OOF keys
`<target>|<radius>|node+edge+subgraph|<seed>`.

For spreading targets read `cache_oof_<network>.npz`; for betweenness read
`estimators/cache_oof_<network>__rf_log1p.npz`. This mirrors
`analyse_moran_correlogram.oof_store`'s reported-log1p special case, with the
structural key rather than its module-local dynamic `FULL` constant.

Write `results/phase6_structural_moran_correlogram.csv` and
`results/phase6_structural_moran_correlogram_provenance.json`. The CSV keeps
the established rank residual, lags `1..7`, empirical permutation p-value,
`alpha_d = 0.05 / lag`, `sig`, `n_used`, `testable`, and complete lag curve.
It also adds `tier=node+edge+subgraph`, `source_oof_path`, graph/cache/registry
hashes, and a Boolean `later_testable_sig` for each candidate cutoff. The
existing testable threshold is 30 sources. Keep the current `alpha/d` label as
`progressive_bonferroni`; it is a comparability rule, not a family-wise claim.
Also calculate a seven-lag sensitivity with `p_perm < 0.05 / 7`, separately
labelled and never substituted for the primary rule.

For each `(network, target, radius, seed)`, define `first_nonsig` as the first
testable lag whose primary `sig` is false. Its absence is the explicit status
`unresolved_no_testable_nonsig`; do not coerce it to 7. A cell's measured buffer
is available only when all ten seeds have finite `first_nonsig`; then it is
`ceil(median(first_nonsig))`. Otherwise its measured arms receive
`unresolved_seedwise_buffer` and are not fitted. Every resolved cutoff carries
the later-significance flag from the full testable lag curve. This is a
diagnostic-derived sensitivity, not evidence of independence.

## New runner and exact interfaces

Add `probe_buffered_cv.py` with protocol string `phase6-buffer-v1`. Do not
extend `influence.experiment.out_of_fold_predictions`: it owns shuffled KFold
construction at lines 94--170 and changing its signature risks the historical
sweeps. The new runner owns custom graph splits.

Required pure functions (and their contracts) are:

```python
def bfs_order(nbrs: list[np.ndarray], seed: int) -> tuple[np.ndarray, int]:
    # root = default_rng(seed).integers(len(nbrs)); FIFO queue; mark on enqueue.
    # Visit sorted ascending neighbour IDs. Raise unless result is a permutation
    # of arange(n), since the validated LCC must be connected.

def region_folds(nbrs: list[np.ndarray], seed: int) -> list[np.ndarray]:
    # np.array_split(bfs_order(...)[0], 5); five nonempty test-ID arrays.

def exclusion_mask(adj: scipy.sparse.csr_matrix, test_ids: np.ndarray,
                   buffer: int) -> np.ndarray:
    # Multi-source graph-distance traversal; True exactly where distance <= buffer.

def control_seed(network: str, target: str, radius: int, seed: int,
                 fold: int, arm: str) -> int:
    # first 8 bytes little-endian unsigned of SHA256(UTF-8
    # f"{network}|{target}|{radius}|{seed}|{fold}|{arm}|phase6-buffer-v1").

def fit_region_fold(X: np.ndarray, y: np.ndarray, train_ids: np.ndarray,
                    test_ids: np.ndarray, model_seed: int, rf_jobs: int,
                    target: str) -> np.ndarray:
    # RandomForestRegressor(120, min_samples_leaf=2, random_state=model_seed,
    # n_jobs=rf_jobs); log1p/expm1 only for target == "betweenness".
```

`bfs_order` must call `np.random.default_rng(seed).integers(n)` exactly once.
It must never use unordered Python sets for traversal. Fold membership is
graph-only, independent of targets, features, residuals, buffer outcomes, and
model fitting. The five contiguous `array_split` segments are region labels,
not claimed to be connected or balanced communities.

For each fold, `unbuffered_candidates = setdiff1d(arange(n), test_ids)`.
`region` uses all candidates. `buffer_b1` excludes candidates with distance
`<= 1`; `buffer_measured` does the same at the resolved cell buffer. A buffered
fold with fewer than 30 retained rows gets `infeasible_lt30` (with its counts),
not a shrunken buffer or fallback fit. The corresponding control is sampled
without replacement only from `unbuffered_candidates`, sorted before fitting,
and must have exactly the buffered arm's retained count. Controls are allowed
to include near-test nodes.

There are five logical arms: `region`, `buffer_b1`, `control_b1`,
`buffer_measured`, and `control_measured`. Only a complete five-fold arm gets
a full-population OOF vector and tau. An infeasible fold gives its logical arm
`infeasible_lt30`; an unresolved measured cell gives both measured logical arms
`unresolved_seedwise_buffer`; its OOF key is absent rather than a partial vector.
If partial predictions are retained for diagnosis, write `NaN` outside successful
test folds and label `subset_only`, with no tau comparison to a full vector.

When `measured_buffer == 1`, canonicalise `buffer_measured` to `buffer_b1` and
`control_measured` to `control_b1` before deriving the control seed. Fit each
canonical arm once, then write the two measured rows as aliases with
`alias_of`, identical split/train-ID digest, and identical prediction digest.
This is the only permitted fit de-duplication: targets and radii have different
`X` or `y`, and the declared control seed contains both, so they cannot share
fits. The region arm is likewise intentionally separate from random-CV because
the test geometry differs.

## Result, provenance, and resume layout

Keep every new artifact under `results/`:

* `phase6_buffered_cv_preflight.json`: all cells and folds, status/counts,
  selected measured buffer or unresolved status, split hashes, and projected
  canonical fit count before training;
* `phase6_buffered_cv_provenance.json`: fixed configuration, runtime versions,
  hashes, resource policy, expected logical and canonical output-key sets, and
  Moran artifact hash;
* `phase6_buffered_cv_assignments/<cell-sha256>.npz`: one immutable,
  provenance-indexed archive per `(network, target, radius, seed)` cell. Each
  archive contains its complete explicit `test_ids`, `train_ids`, and
  `excluded_ids` key set for all five folds and five logical arms, including
  aliases and infeasible/unresolved empty-ID records. `preflight.json` records
  the readable cell key, archive path, and SHA-256; readers reject an archive
  whose hash or exact expected key set differs. This replaces the originally
  proposed monolithic assignment archive so preflight never accumulates the
  corpus's arrays in memory;
* `phase6_buffered_cv_folds.csv`: one logical-arm/fold row with counts,
  status, buffer, distance verification, split/train/exclusion digests,
  canonical arm, timing, and failure reason;
* `phase6_buffered_cv_cells.csv`: one logical-arm/cell row with complete-fold
  status, tau only when five folds succeeded, feature count, OOF digest, and
  provenance/configuration digest;
* `phase6_buffered_cv_oof/<network>.npz`: canonical full OOF vectors keyed
  `network|target|radius|seed|canonical_arm`, plus
  `phase6_buffered_cv_oof_manifest.json` listing each per-network archive,
  its hash, and exact key set. Per-network packaging prevents a final
  whole-corpus compressed-archive load; and
* `phase6_buffered_cv_pilot.json`: representative timing, memory snapshots,
  and extrapolation from the preflight canonical fit count.

`np.savez_compressed` is appropriate for one immutable cell transaction and
one final network archive, but its members are not memory-mapped. A cell
transaction writes its complete generation under a unique directory, hashes
every artifact, and atomically replaces only the `current.json` pointer after
all files exist. Resume accepts solely that indexed generation; unindexed
partial generations are ignored and a pointer/hash mismatch is rejected.
During a network's run, hold only one network's feature matrix, target vectors,
CSR graph, and active cell output vectors; release them and collect before the
next network. Use
`np.load(cache_cascades_<network>.npy, mmap_mode="r")` in cache-alignment
preflight if target reconstruction is performed, never materialise all five
cascade matrices, and do not claim that `mmap_mode` memory-maps `.npz` members.
The feature CSVs are at most 10.2 MiB on this corpus, so one-network loading is
the bounded-memory choice without an unnecessary format migration.

Use atomic CSV/JSON replacement following
`probe_structural_target_noise_refit.atomic_csv` and `atomic_json`. On resume,
require CSV/provenance co-presence; exact stable-digest equivalence of the
configuration/input/source/provenance; no duplicate logical or canonical keys;
completed keys a subset of the preflight expected set; existing assignment and
OOF key sets exactly consistent with completed canonical successes; valid row
digests; and matching saved ID digests. Reject an interrupted or edited output
that violates any condition rather than filling its gaps from another run.

## Execution order and launch commands

Freeze outer workers at one. Reuse the measured CPU policy from the structural
pilot: benchmark `rf_jobs` in `{1,4,8}`, select one before fitting, and never
run an outer process pool alongside forests. The buffered preflight makes zero
fits; only after it and the structural Moran artifact pass should the runner
permit a pilot. The nominal maximum is 20,000 fits (5 networks x 4 targets x
4 radii x 10 seeds x 5 folds x 5 arms), reduced only by explicit aliases and
infeasible/unresolved statuses reported by preflight.

```powershell
conda run -n influence python analyse_structural_moran_correlogram.py `
  --perms 199 --batch 512 `
  --out results/phase6_structural_moran_correlogram.csv

conda run -n influence python probe_buffered_cv.py --preflight-only

conda run -n influence python probe_buffered_cv.py --benchmark-only --rf-jobs 1

conda run -n influence python probe_buffered_cv.py --rf-jobs <chosen-1-or-4-or-8> `
  --stop-after-canonical-fits 1

conda run -n influence python probe_buffered_cv.py --rf-jobs <chosen-1-or-4-or-8>

conda run -n influence python analyse_buffered_cv.py
conda run -n influence python -m unittest -v verify_buffered_cv.py
```

The controlled stop and subsequent identical resume are a launch gate. The
analysis must reject incomplete/duplicate seed-arm cells, compare only paired
within-seed values, report covariance and descriptive seed spread, and make no
new p-value, headline-star replacement, or claim that the buffer made targets
independent. Buffered labels remove local training labels only; cached
structural features remain transductive and train/test Monte Carlo targets
share the same 4,000 live-edge simulations.

## Required tests

`verify_buffered_cv.py` must cover:

1. deterministic root/order, permutation coverage, and five-fold exact test
   coverage on a graph whose adjacency order is intentionally scrambled;
2. exact buffer masks on a path and a cycle, independently checking every
   retained train node has shortest distance greater than the requested buffer;
3. complete-graph exhaustion and the explicit `<30` status, with no fallback
   prediction or altered buffer;
4. no test ID in any train ID; control IDs drawn only from unbuffered
   candidates; exact count matching; sorted deterministic control IDs; and
   alias identity when measured buffer equals one;
5. `log1p`/`expm1` only for betweenness, raw fit targets for all three spreading
   targets, and tau evaluated against original targets;
6. structural OOF source selection, including log1p betweenness path, and a
   dynamic C6 source/key rejected for the structural prerequisite;
7. unresolved seedwise Moran buffer produces recorded measured-arm statuses
   rather than a substituted fit, and later significant testable lags are
   retained/flagged; and
8. atomic interruption/resume succeeds with identical provenance and rejects a
   changed hash/configuration, altered row digest, missing assignment, duplicate
   key, missing OOF vector, and incompatible expected-key set.

## Readiness and remaining design questions

The design is implementation-ready for the fixed protocol: split construction,
buffer status semantics, control randomness, aliasing, source paths, output
identities, resource policy, and tests are specified. Two choices remain
deliberately deferred until preflight evidence exists: the bounded `rf_jobs`
value (selected from the fresh buffered pilot) and the launch estimate (derived
from the measured representative cell and actual canonical feasible-fit count).
Neither changes the scientific design. A high infeasibility rate or unresolved
measured buffer is itself an output condition, not authority to reduce scope.

## Review fix round: artifact identity and bounded export

The executable contract now separates immutable scientific/preflight identity from benchmark-selected execution identity. Structural Moran is accepted only with its structural sidecar and live source hashes; the preflight binds input hashes, assignment-index hash, exact logical/canonical folds, and cell keys. The pilot records all 1/4/8 observations before selecting the fastest valid setting under the memory guard. Checkpoints bind both identities.

The final folds CSV is streamed and contains archive locators plus ID digests, never expanded ID lists. Cells and OOF packages are authenticated by a final results manifest. CSV readers use `float_precision="round_trip"`; the row digest canonicalizes missing fields (`None`, `NaN`, and empty CSV values) and nullable integer formatting so high-precision tau values retain their exact round trip. The random-CV readout is a separate labelled reference, sourced from the root reported sweeps for spreading and the reported log1p sweep for betweenness; it is not a seventh paired contrast.

## Structural-Moran launch resource bound

The new structural Moran calculation must enter `threadpool_limits(limits=4, user_api="blas")` only for the dense BLAS calculation and record `blas_threads: 4` in its provenance. Free the residual `columns` list after `np.column_stack` and do not call the redundant float64 `astype` copy. Buffered preflight rejects a Moran sidecar without that recorded cap. This applies only to the new structural artifact, preserving the historical dynamic-tier runner and its results.

## Structural-Moran producer validity and shared-null disclosure

Before computing rank residuals, the producer verifies target node order, feature node/original-ID order, every OOF key's shape, and finite OOF values. Its sidecar hashes the producer modules and the buffered reader recomputes those hashes before accepting the CSV. A non-finite observed statistic or permutation tail area is `testable=False`, so it cannot yield a measured buffer.

The approved null construction remains unchanged: permutations use the fit-seed-0 residual for each target/radius and are reused across the other fit seeds. Rows and the sidecar must carry `null_reference_seed: 0` and an explicit description that nonzero-seed `p_perm` values are seed-0-reference tail areas, not independently generated seed-specific permutation tests.

## Pilot numerical-equivalence gate

Before worker timing selects an execution count, the one-fit `rf_jobs` 4 and 8 predictions must be compared with the `rf_jobs` 1 reference. Record maximum absolute difference, maximum difference divided by `max(1, max(abs(reference_prediction)))`, and the Kendall-tau difference. The fixed validity threshold is `absolute <= 1e-10 + 1e-12 * scale` and `tau difference <= 1e-12`; an otherwise fast setting failing either threshold is invalid. These tolerances are stored in the pilot before selection, along with the memory guard and elapsed time.

## Authoritative structural-Moran settings

The buffered consumer accepts only the structural sidecar configuration `perms: 199`, `batch: 512`, and `random_seed: 0`, in addition to the structural tier, source, BLAS, and shared-null bindings. Alternative producer diagnostics must be kept separate and cannot determine a buffered-CV measured radius.


<!-- END docs/phase6_buffered_implementation_brief.md -->

---

## <a id="rec-phase6_criticality_repair_brief"></a>`docs/phase6_criticality_repair_brief.md`

<!-- BEGIN docs/phase6_criticality_repair_brief.md sha256=3331f2147352100ed6a255f7e16ee812b67a5dce3d524d4f3e98c733a92cadc9 date=2026-09-08 author=unsigned -->
# Criticality repair brief

Preflight reproduced 2026-09-08, existing environment. On path edges (0,1),(1,2),(2,3),
five repeated adjacency thresholds yielded negative/positive 0.618033988749894; three
non-backtracking thresholds yielded -1, +1, +1. No source edit preceded the reproduction.

Independent dense eigendecomposition confirms adjacency has opposite-sign extremal
eigenvalues. Direct non-backtracking B has six zero eigenvalues and B^3=0. Ihara-Bass M
has extraneous +/-1 roots. Therefore merely taking absolute value of the current result
does not repair the tree case. Investigate small/empty/cycle graphs and probability-range
handling as well as the bipartite sign. Use the systematic-debugging and TDD process.

Scope: influence/criticality.py and an independent regression verifier; minimal necessary
call-site validation if transmission_from_threshold can otherwise emit invalid probability.
CPU/no-install. Preserve all current caches and registered results. Baseline source hash
is in results/phase6_extension_initial_source_hashes.json.

Required tests: path/tree NB spectral radius0 gives infinite threshold, adjacency path
threshold known exactly; cycle NB threshold1; complete graph NB threshold1/(n-2); direct
B versus reduced computation on constructed cyclic/bipartite graphs; deterministic
nonnegative results and explicit tiny-input handling. Record no-transition semantics,
not a fabricated finite critical point. Invalid probability multiples should fail with
a clear explanation at their boundary instead of being silently clipped.

Before reporting repaired: recompute NB for the five real graphs and compare to the
existing cache_meta values using the numerical tolerance warranted by the eigensolver.
If any moves materially, report and assess affected caches before training changes.
Preserve analytical arguments, tests, commands and outcomes in the repair report.

<!-- END docs/phase6_criticality_repair_brief.md -->

---

## <a id="rec-phase6_criticality_repair_report"></a>`docs/phase6_criticality_repair_report.md`

<!-- BEGIN docs/phase6_criticality_repair_report.md sha256=fa6f5c5ddc45efd44fa033d157d83684b304af621deef8d7cc8f4729f3fb3dde date=2026-09-08 author=unsigned -->
# Phase 6 criticality repair report

Date: 2026-09-08  
Scope: `influence/criticality.py`, the stage-1 probability boundary, and
`verify_criticality.py`. No registered cache, score, sweep, target, feature,
or structural-bootstrap source file was rewritten.

## Root cause and observed failure

The preflight reproduction was confirmed before the repair by running the new
analytical verifier against the original source. It failed on the four-node
path because `epidemic_threshold(path4, "nonbacktracking")` returned a finite
value instead of infinity.

There were two separate numerical/algebraic defects.

1. `leading_eigenvalue` asked ARPACK for a largest-magnitude root, then used
   its signed real part. For a bipartite adjacency matrix, both signs have the
   same magnitude. ARPACK may select either member, so the reported adjacency
   threshold could change sign between calls.
2. The Ihara--Bass reduced matrix is not itself the non-backtracking operator
   on a forest. For path P4, direct B has `B^3 = 0`, hence spectral radius zero
   and no finite non-backtracking critical point. The reduced matrix has
   algebraic `+/-1` roots from the tree cancellation, which must not be used as
   a transmission threshold.

`stage1_prepare.py` also calculated `p = multiple * beta_c` directly, so the
then-unused `transmission_from_threshold` function could not protect the
actual cache-writing boundary.

## Repair

- `leading_eigenvalue` now returns the nonnegative spectral radius. This keeps
  the existing sparse Arnoldi method and removes only the sign dependence.
- `epidemic_threshold(..., "nonbacktracking")` classifies every connected
  component by cyclomatic excess (`edges - vertices + 1`) before a reduced
  solve. All-tree inputs return `inf`; when every component is at most
  unicyclic and at least one is unicyclic, the exact threshold is `1.0`; a
  component with excess at least two uses the existing Ihara--Bass sparse
  solve. This prevents long pendant trees from turning an exact unicyclic
  threshold into an ARPACK convergence artifact.
- Empty and edgeless adjacency inputs return `inf` without asking ARPACK to
  solve a zero-dimensional problem.
- `transmission_probability` validates a finite positive regime multiplier,
  a finite positive threshold, and final `p` in `[0, 1]`. Raw IC permits
  `p=0`, but zero is rejected as a threshold *multiplier* because it does not
  select a regime above criticality. Forest inputs explain that no finite
  non-backtracking critical point exists; oversize multiples identify the
  invalid derived probability.
- Stage 1 calls the validation boundary before simulations or cache writes,
  passing its already-computed `beta_c` so the metadata and `p` use the same
  value and no second non-backtracking eigensolve is introduced.

## Independent regression verifier

[`verify_criticality.py`](../verify_criticality.py) derives expected values
from hand-checkable graph structure rather than from the production helpers.
It checks:

- P4 adjacency threshold `2 / (1 + sqrt(5))`; P4 non-backtracking threshold
  is infinite.
- C4 non-backtracking threshold is 1, exercising the bipartite case.
- K4 non-backtracking threshold is `1 / (4 - 2) = 0.5`.
- Direct Hashimoto B and Ihara--Bass agree on C4 and K4, cyclic fixtures where
  the tree-only cancellation does not apply.
- C8 with a 64-edge pendant tail returns exactly 1.0 on repeated calls, with
  direct B independently confirming spectral radius 1; a disconnected C4 plus
  a tree also returns 1.0, proving component-wise rather than global handling.
- Repeated adjacency and non-backtracking calls stay nonnegative and agree
  within `1e-7`, rather than assuming bitwise equality from ARPACK.
- Empty and one-node edgeless inputs have infinite adjacency and
  non-backtracking thresholds.
- Forest, zero-multiplier, and `p > 1` boundaries raise explanatory errors.
- The real stage-1 CLI rejects a temporary tree input before any cache output
  is created.
- All five current cache metadata thresholds match a fresh source/data
  calculation under `rtol=1e-7`, without writing the caches.

The `1e-7` comparison tolerance is conservative relative to ARPACK's
`tol=1e-8`. Repeated C4 sparse solves varied by at most about `2e-8`; the
largest observed registered-cache relative difference was `4.69e-11`.

## Registered cache comparison

| Network | Cached beta_c | Current beta_c | Absolute difference | Relative difference |
|---|---:|---:|---:|---:|
| ca-GrQc | 0.02250307170411322 | 0.022503071704151653 | 3.84e-14 | 1.71e-12 |
| ca-HepTh | 0.033326089293547044 | 0.033326089291985161 | 1.56e-12 | 4.69e-11 |
| email-Eu-core | 0.01337856605222597 | 0.01337856605222559 | 3.80e-16 | 2.84e-14 |
| facebook_combined | 0.006200284107725097 | 0.006200284107725297 | 2.00e-16 | 3.22e-14 |
| p2p-Gnutella08 | 0.03772097825111152 | 0.037720978251131645 | 2.01e-14 | 5.34e-13 |

All five values pass. The five `cache_meta_*.json` files remain present and no
temporary tree cache output remains. The historical email 1.2x archive was
not changed.

## Commands and environment

```powershell
C:/Users/Rachit/miniconda3/envs/influence/python.exe verify_criticality.py
C:/Users/Rachit/miniconda3/envs/influence/python.exe -m compileall -q influence/criticality.py stage1_prepare.py verify_criticality.py
```

Both succeeded in the CPU-only `influence` environment:
Python 3.12.14, NumPy 2.5.2, SciPy 1.18.0. No package installation, GPU, or
training run occurred.

## Source evidence

Initial extension inventory records `stage1_prepare.py` as
`2F89076F23376A935DDA92182833D4D4251D62FAAEE266F0D5D8670150F4121D`.
It also records the pre-repair `influence/criticality.py` as
`7780D6F73059349F189FC2DE6782741E760A8AE0F5980F3BBDF95A368687D05B`.
The current hash below is the documented repair delta from that baseline.

Current hashes:

| File | SHA-256 |
|---|---|
| `influence/criticality.py` | `457973DE8C7F2E140B10066C6244E02F59A185DC0DF4749C4AD4B17BB76BED9B` |
| `stage1_prepare.py` | `5408279966404890DF4C2B28581033E9BAE650B1B65A265CAF1E127FDEEF9C7C` |
| `verify_criticality.py` | `05F89BD398FD9784C69B1B2ECBD8640C897D18025D4A484381C542A9F57F90FA` |

The stage-1 delta is intentionally limited to importing and calling the
validated threshold conversion. The criticality module has the analytical
repair and boundary handling described above.

## Scoped review follow-up

The review correctly identified a remaining boundary: C8 with a 64-edge
pendant tail is connected and unicyclic, but reduced-matrix Arnoldi produced
thresholds from `0.999991135194145` to `0.999999999241431` across the review's
eight repetitions. The exact non-backtracking spectral radius is 1 because
the cycle is the only recurrent non-backtracking class and the tail is
transient. The verifier uses the same C8-plus-64-edge-tail construction
(`n=m=72`; adding a 64-edge tail to C8 adds 64 nodes), and it failed before
the structural repair with values as low as `0.9999967514902595`.

The component cyclomatic branch resolves this without changing the
multicyclic solver used by the five cached networks. It also fixes the
disconnected-input case: global `m < n` cannot identify a forest when one
component is cyclic and another is a tree. The updated verifier exercises that
case, five exact repeated unicyclic calls, direct B on the long-tail fixture,
the existing analytical checks, stage-1 boundary, and all five cache
comparisons. All checks pass after the repair.

<!-- END docs/phase6_criticality_repair_report.md -->

---

## <a id="rec-phase6_criticality_review"></a>`docs/phase6_criticality_review.md`

<!-- BEGIN docs/phase6_criticality_review.md sha256=cfb041b02caea7362292305d015486c54a2d30a338007318373955424ab761b0 date=2026-09-08 author=unsigned (review role) -->
# Phase 6 criticality repair review

**Date:** 2026-09-08  
**Scope:** read-only review of `docs/phase6_criticality_repair_brief.md`,
`influence/criticality.py`, `stage1_prepare.py`, `verify_criticality.py`,
the draft repair report, cache metadata, and the initial source-hash manifest.
No source, cache, result, or test file was changed by this review.

## Disposition: changes required before declaring the repair green

The forest, bipartite-sign, empty-input, probability-boundary, and cache
preservation repairs are well scoped and largely correct. The five cache values
remain within the report's stated tolerance; the largest reported relative
difference is `4.28e-12` for ca-HepTh. The stage-1 validation now occurs before
simulation or cache output, which closes the previously bypassed probability
boundary.

One required mathematical boundary remains unhandled: a unicyclic component
with attached trees. It is neither a forest nor a case in which sparse Arnoldi
on the Ihara--Bass reduction is numerically reliable enough to represent the
known exact non-backtracking radius.

### P1 — unicyclic graphs need an exact branch

**Evidence.** In the CPU-only `influence` environment, I constructed C8 with a
64-edge tail attached at one cycle vertex. It has `n = 73`, `m = 73`, hence is
connected and unicyclic. Direct Hashimoto B returned a spectral radius of 1 to
approximately `1e-9`. The current reduced-matrix route was run eight times:

```
min beta_c = 0.999991135194145
max beta_c = 0.999999999241431
spread      = 8.86404728584e-06
```

The exact result is `rho(B) = 1` and `beta_c = 1`: the sole cycle supplies the
only recurrent non-backtracking class, while every attached tree contributes
only transient paths. The observed spread is about two orders of magnitude
larger than the verifier's `1e-7` repeated-solve tolerance. A bare C4 fixture
does not expose this non-normal/Jordan boundary.

**Required resolution.** Classify component cyclomatic excess before invoking
the reduced eigensolver. For a simple undirected component,
`excess = edges - vertices + 1`.

- all components with `excess == 0`: `rho(B) = 0`, so return `beta_c = inf`;
- every component has `excess <= 1` and at least one has `excess == 1`:
  `rho(B) = 1`, so return `beta_c = 1.0` exactly;
- any component has `excess >= 2`: use the existing Ihara--Bass sparse solve.

This component-wise formulation also handles disconnected test inputs with two
separate unicyclic components correctly. Add the C8-plus-tail fixture as an
analytical `beta_c == 1.0` regression and retain a small direct-B comparison as
supporting evidence. Repeat the value several times only to prove the
structural fast path is deterministic; no broad benchmark replay is needed.

### P2 — correct the draft report's source-manifest statement

The draft report says that
`results/phase6_extension_initial_source_hashes.json` did not include
`influence/criticality.py`. It does include it, with baseline SHA-256:

```
7780D6F73059349F189FC2DE6782741E760A8AE0F5980F3BBDF95A368687D05B
```

The current SHA-256 is
`749B1392AD247E7DD709BC9E7283FA1135EB7ACE4BE0746F97F5CDCF94B06E81`.
The report should state this actual baseline-to-current delta rather than say
that no baseline hash exists.

## Reviewed requirements that are satisfied after P1 is resolved

- `leading_eigenvalue` uses magnitude, eliminating the negative threshold from
  a bipartite adjacency extremal pair.
- Forests and empty/edgeless inputs return `inf`, expressing no finite
  non-backtracking transition instead of fabricating a critical point.
- `transmission_probability` rejects non-positive/non-finite multiples,
  non-finite thresholds, and derived probabilities outside `[0, 1]`; `p = 1`
  remains valid.
- The verifier covers P4 adjacency, C4, K4, direct-B/reduced agreement on
  cyclic fixtures, empty graphs, invalid multipliers, invalid derived `p`,
  stage-1 failure before cache output, and all five existing cache metadata
  values.
- The change surface is confined to the repair scope plus its verifier and
  report. No cache or registered-result file was rewritten.

Until P1 and P2 are addressed, the repair report's claim that the verifier
fully covers the required unicyclic boundary is not supported.

## Follow-up disposition — 2026-09-09

**P1 resolved.** `influence/criticality.py` now computes cyclomatic excess per
connected component. It returns `inf` when all components are trees, returns
exactly `1.0` when each component is a tree or unicyclic and at least one is
unicyclic, and reserves the Ihara--Bass solve for a component with excess at
least two. This is the required classification: a unicyclic component has one
recurrent directed non-backtracking cycle and attached trees are transient.
The disconnected cycle-plus-tree case is explicitly retained by the
component-wise check.

`verify_criticality.py` now covers C8 with a 64-edge pendant tail (`n=m=72`),
asserts five exact `1.0` results, and independently checks direct Hashimoto B.
It also tests a disconnected C4-plus-tree input. I ran the focused verifier
with `C:/Users/Rachit/miniconda3/envs/influence/python.exe
verify_criticality.py`; it completed with `ALL CHECKS PASSED`.

**P2 resolved.** The repair report now identifies the actual baseline
`influence/criticality.py` SHA-256 from the initial manifest
(`7780D6F73059349F189FC2DE6782741E760A8AE0F5980F3BBDF95A368687D05B`) and
records the current repaired hash
(`457973DE8C7F2E140B10066C6244E02F59A185DC0DF4749C4AD4B17BB76BED9B`).

**Disposition: approved for the next implementation lane.** The two findings
from this review are addressed. This approval covers only the scoped
criticality repair and its report; it does not authorize cache replacement or
training.

<!-- END docs/phase6_criticality_review.md -->

---

## <a id="rec-phase6_external_precision_followup"></a>`docs/phase6_external_precision_followup.md`

<!-- BEGIN docs/phase6_external_precision_followup.md sha256=c4b96ff14010611a8f733e407a678f6e76cbc5e8165f6b96296c313ceca75b04 date=2026-09-08 author=unsigned; executed-result section by Claude Opus 5 (2026-09-10) -->
# Phase 6 external precision and prediction feasibility follow-up

**Date:** 2026-09-08  
**Status:** read-only source and corpus investigation. No source edits, model execution,
checkpoint use, PyTorch import, or training were performed. This is a follow-up design,
not a retroactive registration or a replacement for the registered C3/C4 outcomes.

## Answer supported by the inspected evidence

The released ABCDE material establishes a fixed, precomputed text corpus, but the inspected
public repositories do not expose the program invocation, score normalisation, unrounded
values, or text formatter that produced the five real `*-score.txt` files. The C4 result
that every printed value is on a `1e-14` grid therefore establishes a serialisation grid;
it does **not** establish nearest rounding, truncation, a tie rule, clamping, or the exact
positive values that appear as zero in the text files.

No published BRAVA per-node prediction array was located in the inspected current public
repository tree or its matching local results directory. BRAVA has a runtime
`--dump_predictions` facility, but that is code capable of producing an artefact after an
experiment, not a released artefact. This investigation did not run it.

An independent, targeted CPU check can prove a lower bound for selected positive nodes under
explicit graph and normalisation assumptions. It cannot recover an exact betweenness value or
identify the release's rounding rule without producer provenance or a full matched-convention
exact computation.

## Corpus and release trail

The evidence trail that was actually read is:

```
ABCDE v1.0.0 real.zip (five graph/score text pairs)
  -> BRAVA datasets/download.py fetch_abcde()
  -> local datasets/abcde/<graph>{,-score}.txt
  -> BRAVA datasets/import_abcde_datasets.py np.loadtxt(..., dtype=float32)
  -> imported labels for BRAVA evaluation
```

[MartinXPN/abcde's v1.0.0 release](https://github.com/MartinXPN/abcde/releases/tag/v1.0.0)
lists `real.zip` as a release asset (published 2021-04-07). Its
[download script](https://github.com/MartinXPN/abcde/blob/main/datasets/download.sh) downloads
that asset; the repository tree contains no versioned real score files, score exporter, or
real-data generation script. Its vendored data code only generates synthetic graphs, so it
does not establish how the real release was scored or printed.

BRAVA's [download code](https://github.com/justindachille/BRAVA-GNN/blob/main/datasets/download.py)
sets `ABCDE_ZIP` to that `real.zip` release and copies the five graph and score text files.
Its [ABCDE importer](https://github.com/justindachille/BRAVA-GNN/blob/main/datasets/import_abcde_datasets.py)
reads the supplied score text with `np.loadtxt(..., dtype=np.float32)`. That later conversion
does not evidence the precision or formatter used to create the release text. The vendored
[predict entry point](https://github.com/justindachille/BRAVA-GNN/blob/main/baselines/abcde/predict.py)
reads labels for evaluation; it does not write released real scores or prediction arrays.

The inspected BRAVA checkout is commit `84119a1f0246dd0e6ea717533c1bf6fc4cfad4b6`. Its relevant
source snapshots have these SHA-256 values:

| Snapshot | SHA-256 |
| --- | --- |
| `datasets/download.py` | `e531f1ac1c6aeef6bd90ecc17dadae4d0c43df5701f37248a7ab997d160c782be` |
| `datasets/import_abcde_datasets.py` | `f4931f14f8189da61c3bac55745a8e056f3a3203aa44fbd7f088c913191432d9` |
| `baselines/abcde/predict.py` | `952b7e3b600c3a078057ef19009b252d5a39c563bf0d0a9099bc0fd2f59ce142` |
| `baselines/abcde/abcde/data.py` | `950454caf2fde31468a5b714c05eb650755888c2ed0bd044eeeb71a50edbf16` |

The local target files agree with the C4 audit's hashes:

| Graph | score-file SHA-256 | graph-file SHA-256 |
| --- | --- | --- |
| amazon | `3a89a0714033591105d0070b9228cfe0763e8a0b2ca8487ca54e800a27c040c4` | `43f7a104f3ec6c2c2d7bcd947a71fe5ceb2f16db3060200e907e9f9dc0dca00f` |
| cit-Patents | `48f352137529955aed7faf1fd06be1ded7fe77708ca0989683ef984733ab71a6` | `f8797f004315acf99faaee62b08ce093109968ba82bb52d55c7bc8b92e4918b9` |
| com-lj | `78a77750ac83057a6c62e5cef3ef34c74c50a8c6fc7603d0b460eb91a0d480d4` | `835d5175a7309fedd782fc505407a5d140587540b27d4eab64df9f3f3eba2add` |
| com-youtube | `b9f3aa834eb638ca7db74b61f5515298eb41cfcf9efdf0ce95f81e3dd8d675b3` | `b9dad0cdd621f9b0c8f9a333a9783776b6af1624ca0f908158d6af3e0a5acaec` |
| dblp | `4236b420a8ef0303120735eca6dfe787a8a4526e94a8d285e24af23789cb7c47` | `5641215f2373210340309553a26c2517a8379f81b8a93490bab80b05eeaff52b` |

## What the current C3/C4 corpus proves

`results/RESULTS_c4_support_audit.txt` audited all 15,043,174 score text values exactly as
decimals. It found no value off the `1e-14` grid. The two C3 structural-versus-shipped support
mismatches are one-directional: a structurally positive node is printed as zero; no printed
positive is structurally zero.

| Graph | nodes | structural zeroes | printed zeroes | structural-positive/printed-zero count | smallest printed positive |
| --- | ---: | ---: | ---: | ---: | ---: |
| cit-Patents | 3,764,117 | 709,062 | 709,724 | 662 | `1.00e-14` |
| com-lj | 3,997,962 | 1,150,616 | 1,151,702 | 1,086 | `1.00e-14` |

The scored C3 provenance is recorded in `results/c3_scored_provenance.json`: structure CSV
`1ceb3d435947e7078a7091f86227dfb140d114969b30e29c59d808ca47bb98c6`, cells CSV
`218a1357b8d34b52c0b28e4b0e9a83b421048879a5f8eb67e25f065ad2e1c788`, and the C3 benchmark
report `5485da23286fb3cfd13f64c4f526eb28a4479bd4d191d98e1f48093272cb1523`.

These observations do not answer any of the following: whether formatting used nearest
rounding or truncation; the half-step tie rule; whether a value was computed in binary or
decimal floating point; the original score normalisation; or the unprinted magnitude of a
structurally positive printed zero. The existing historical C3/C4 outcome, including P4's
registered conditional wording, remains unchanged.

## Per-node external prediction release check

The public BRAVA tree at the cited commit and its local `results/betweenness/` directory contain
aggregate CSV results but no tracked `.npy`, `.npz`, or prediction directory. The current source
has `_dump_predictions` behind `--dump_predictions`; this is an available runtime export path,
not evidence of a public prediction release. The inspected ABCDE release likewise distributes
labels and checkpoints rather than a per-node BRAVA prediction file. No checkpoint was opened or
executed.

This is a bounded search result for the stated release and repository surfaces. It is not a
claim that no such array exists anywhere else or has never been released.

## Targeted lower-bound follow-up design

The following independent CPU check is feasible without model execution or an all-source
Brandes computation. It would be new evidence and must write separate provenance/results if it
is ever implemented.

1. Pin the two graph and score hashes above, the C3 node-index mapping, and the exact list of
   662/1,086 structural-positive/printed-zero rows. Reject a mismatch before calculation.
2. For each selected node `v`, find a pair of distinct, non-adjacent neighbours `u,w` and count
   `c = |N(u) intersection N(w)|` with sorted adjacency intersections. In a simple, unweighted,
   undirected graph, `u-v-w` is then a shortest path, and `v` contributes `1/c` to the
   unnormalised betweenness from that pair. Thus the node's total unnormalised betweenness is at
   least `1/c`.
3. Only if the original release used the usual endpoint-excluding undirected normalisation
   `2 / ((n-1)(n-2))`, report the corresponding lower bound
   `2 / (c (n-1)(n-2))`. Do not assume that normalisation merely because the score values are
   small; the public producer source has not established it.
4. Under a further *nearest-to-14-decimal* hypothesis, a bound strictly above `5e-15` rules out
   nearest rounding as the explanation for that node printing zero. It does not identify the
   actual rounding rule or exact score.

For reference, the sufficient common-neighbour thresholds under that conditional normalisation
are:

| Graph | `(n-1)(n-2)` | need for lower bound `> 5e-15` | sufficient integer test |
| --- | ---: | ---: | ---: |
| cit-Patents | 14,168,565,497,340 | `c < 28.2315101042` | `c <= 28` |
| com-lj | 15,983,688,159,560 | `c < 25.0255132612` | `c <= 25` |

The check needs one adjacency construction per affected graph, then only the affected rows and
local set intersections. It does not calculate all-source centrality, train a model, import
PyTorch, or use any checkpoint. Its interpretable outcomes are limited:

- a qualifying witness gives a conditional lower bound and rejects the nearest-rounding
  explanation for that row under the stated graph/normalisation assumptions;
- no qualifying witness is inconclusive, because other source-target pairs may still raise the
  exact score; and
- even a qualifying witness cannot recover the exact positive magnitude, prove the original
  graph interpretation, or distinguish truncation, formatting, clamping, and other release
  pipelines.

Exact raw magnitudes or an exact rounding-mode proof require either the original producer and
its conventions, or an exact all-source recomputation that demonstrably matches those
conventions. Neither is supplied by the public material inspected here. Accordingly, this
targeted check is suitable only as a bounded falsification test, not as an upgrade of P4 from
conditional consistency to exact target verification.

---

## Executed result, 2026-09-10 (Claude Opus 5)

> Added 2026-09-10 by Claude Opus 5. The design above was written as a proposal ("if it is ever
> implemented"). It has now been executed on both pinned graphs. This section reports what the
> run measured; it does not restate the design's intent as an outcome.

Command, once per graph, serially, `--workers 1`:
`probe_c3_precision_witness.py --graph <g> --brava data/brava --workers 1`.
Log: `results/phase6_claude_witness_run_20260910.log`.
Artifacts: `results/phase6_precision_witness/<graph>_{summary.json,targets.csv,witnesses.csv}`.

### Measured

| Graph | Selected targets | Pinned | Usable pairs | Degree range | Pair scan | Pairs `> 5e-15` | Pairs `> 1e-14` |
| --- | ---: | ---: | ---: | :--: | ---: | ---: | ---: |
| cit-Patents | 662 | 662 | 727 | `[2, 6]` | 1,459 | **0** | **0** |
| com-lj | 1,086 | 1,086 | 1,588 | `[2, 111]` | 293,013 | **0** | **0** |

Both pinned selected-target counts reproduced **exactly**, as did both printed-zero counts
(709,724 and 1,151,702). The witness therefore selected precisely the rows this document's
table above describes.

### The headline result is a null, and is reported as one

**No pair on either graph qualifies at either threshold.** Under the design's own reading, that
means the one-pair witness class does not reject the nearest-rounding explanation for any of the
1,748 rows. It is explicitly *not* evidence that the values are exactly zero: as stated above, a
non-qualifying result is inconclusive because other source-target pairs may still raise the exact
score, and this class cannot upper-bound `BC(v)` at all.

### The margin is one common neighbour, on both graphs

| Graph | Qualifying boundary | Smallest observed `c` | Margin |
| --- | :--: | ---: | ---: |
| cit-Patents | `c <= 28` | 29 | **+1** |
| com-lj | `c <= 25` | 26 | **+1** |

Observed `c` ranges up to 297 and 707 respectively, so the minimum landing exactly one above the
boundary on both graphs is worth recording rather than rounding off as "no result".

**Reading, labelled inferred.** This is what *consistency* looks like rather than a coincidence.
A row survives selection only if its printed score is zero while its structure is positive. If
the producer's rounding is honest, the true value must lie below the printing threshold, which
forces the certified lower bound `2 / ((n-1)(n-2)c)` below that same threshold — that is, forces
`c` above the qualifying boundary. A qualifying pair would have been a detected *contradiction*.
Finding none, with the data sitting immediately against the boundary the clamp implies, is
consistent with genuine sub-grid values.

This is an inference about consistency, not an established mechanism. Per the standing traps it
is labelled as such: quantisation mechanisms remain **inferred**; a repeated minimum is not proof
of clamping and its absence is not proof of exactness; and the directional test still cannot
catch false-nonzero rule errors hidden among shipped zeros. **No registered C3 verdict changes.**
P4 stays at its registered conditional wording, and this run does not upgrade it.

### Two defects found in the unrun implementation

The witness had never completed a run before today, so its preflight predictions had never been
testable. Two failed on first contact with real data; details, evidence and the corrections are
in `docs/phase6_claude_worklog_20260910.md` (Lane 3b) and in dated superseding notes in
`docs/phase6_precision_witness_design.md`.

1. **A 61-character SHA-256** for the com-lj score file, transcribed identically into both the
   spec and the preflight, so the check that compares them agreed with itself.
2. **The pinned degree range `[3,18]` was wrong at both ends on both graphs.** Measured `[2,6]`
   and `[2,111]`. Degree 2 is the structural minimum, not an anomaly; the ceiling was a second
   consequence of the same claim and is replaced by a cumulative pair-scan budget, which guards
   the quantity the design's resource argument was actually about. The measured scans, 1,459 and
   293,013, total 294,472 against the design's quoted 267,444 — a ~10% overrun of streaming,
   constant-extra-memory work, not an envelope breach.

Because all four pinned **counts** reproduced exactly while the degree prediction failed, the
inputs were never in doubt; only the inherited prediction was wrong.

### Scope still outstanding

`SPECS` implements two graphs. Under Rachit's 2026-09-10 ruling the witness is to cover all five
ABCDE graphs; amazon, dblp and com-youtube require new pinned specs whose `nodes`/`arcs`/
`selected_targets` counts can only come from a construction pass. Those three are the clean,
unclamped graphs, so a null there is a **control result** and will be reported as one, not as a
weak positive.

---

## The three unclamped graphs: a control that came out sharper than expected, 2026-09-11 (Claude Opus 5)

> Added 2026-09-11 by Claude Opus 5. Extends the witness from the two clamped graphs to all
> five ABCDE graphs on Rachit's instruction. `verify_c3_precision_witness.py` **13/13**.

### Measured, all five graphs

| Graph | Clamped ground truth | Printed zeros | Structurally-positive targets | Degree range | Pair scan |
| --- | --- | ---: | ---: | --- | ---: |
| cit-Patents | yes | 709,724 | **662** | 2–6 | 1,459 |
| com-lj | yes | — | **1,086** | 2–111 | 293,013 |
| amazon | no | 701,532 | **0** | — | 0 |
| dblp | no | 1,678,358 | **0** | — | 0 |
| com-youtube | no | 650,530 | **0** | — | 0 |

**Zero structurally-positive printed zeros across all three unclamped graphs, among 3,030,420
printed zeros between them.** Every printed-zero node on those graphs has a neighbourhood that
induces a clique, so no nonadjacent neighbour pair exists, so no printed zero contradicts a true
zero. The plan called this a control result and predicted it would "yield nothing"; it yields
nothing in the strongest available sense — not a small count, but exactly none.

### Why this is worth more than the usual null

The witness's selection predicate is *not* a property of clamping. It asks a purely structural
question: does this node have two nonadjacent neighbours? If it does, it lies on a shortest path
between them and its betweenness is strictly positive, so a printed zero is impossible. The
predicate would fire on a mis-shipped zero regardless of the mechanism that produced it.

So the separation is informative: the two graphs independently flagged as clamped at 1.0e-14 are
exactly the two carrying structurally impossible zeros, and the three clean graphs carry none.
**This is a directional consistency result across the corpus, and it is what the design asked
the three clean graphs to provide.**

### What it does not establish, stated because the temptation is real

- It does **not** prove amazon, dblp and com-youtube are unclamped. It shows their printed zeros
  carry no *detectable structural contradiction*. Absence of a detected contradiction is not
  proof of exactness — the standing trap in this document, and it binds here.
- The directional test still **cannot** catch false-**nonzero** rule errors hidden among the
  shipped zeros. Nothing here changes that.
- Quantisation mechanisms remain **inferred**, not established. Producer normalisation and
  rounding provenance remain unknown.
- On the two clamped graphs, the qualifying-pair counts remain **0** at both thresholds. The
  null reported previously stands unchanged; nothing here converts it into a positive.

### Provenance, and one honest weakness in it

`precision_witness.SPECS` pins identity, topology and selector outcome as hard gates. For
cit-Patents and com-lj those came from the 2026-09-09 read-only preflight, which predates the
witness. **No such record existed for the other three**, so every pinned field for them was
measured on 2026-09-11 in order to be pinned
(`results/phase6_precision_witness_discovery_20260911.json`; the preflight entries carry
`source: "discovery_2026-09-11"`).

A pin derived that way cannot falsify the run that produced it. It buys reproducibility and
detection of later corpus drift, and nothing more. This is labelled rather than left implicit
because the design's inherited `3--18` degree range was an unrecorded claim presented as a
prediction, and that cost a full cit-Patents run.

Three checks do carry independent weight:

1. **Two separate topology constructions agree.** The discovery pass counted nodes and canonical
   edges in memory; the production path re-derived both through the external-merge machinery.
   The resulting `topology_sha256` matches exactly on all three graphs.
2. Score non-blank rows equal the distinct edge-file node count, on all three.
3. Parsed edge rows minus self-loop rows equal canonical undirected edges (amazon 5,743,146 − 14
   = 5,743,132; dblp 8,649,011 − 10 = 8,649,001; com-youtube 2,987,624 − 0), so no duplicate
   rows are being silently absorbed.

### Defect found and fixed while extending

The production selector could not express a zero-target run: with nothing selected it reached
`int(min_degree)` with `min_degree` still `None` and raised `TypeError`. A source comment
asserted this was unreachable "since no pinned spec declares zero targets" — true only while the
two clamped graphs were the whole corpus. Fixed under TDD (failing test first:
`test_zero_selected_targets_is_a_completed_control_result`, a printed-zero triangle), with the
stale comment corrected in place rather than deleted. A null run now publishes a header-only
witness file and a summary saying zero, because a null result is a result and needs the same
artifact trail as a positive one.

<!-- END docs/phase6_external_precision_followup.md -->

---

## <a id="rec-phase6_precision_witness_design"></a>`docs/phase6_precision_witness_design.md`

<!-- BEGIN docs/phase6_precision_witness_design.md sha256=8edfe72b257845f260b4373b6e812976b071091fd04969755b56ff4c196332f5 date=2026-09-08 author=unsigned; amendments by Claude Opus 5 (2026-09-10) -->
# Phase 6 targeted external-precision witness design

**Status:** design only, 2026-09-08. This is new follow-up evidence and is
separate from the registered C3/P4 result. No exact all-source betweenness,
GNN, PyTorch, checkpoint, or training work is included.

## Scope

`cit-Patents-score.txt` and `com-lj-score.txt` contain respectively 662 and
1,086 rows where C3's local structural rule says the node has positive
betweenness while the printed score is zero. The text proves a `1e-14`
serialisation grid only. It does not prove score normalisation, rounding,
truncation, tie handling, or omitted positive magnitudes. The two C3 arms stay
**consistency only** and cannot become `SCORED` from this check.

The bounded question is whether an explicit source--target pair forces a lower
bound above `5e-15` or `1e-14` for each affected node. A passing witness is
conditional evidence against a stated zero-printing explanation; it never
recovers exact centrality or producer provenance.

## Pinned inputs and identity layout

A future command accepts `--brava <checkout>` and reads only the existing public
BRAVA ABCDE text files. It must not download data or substitute a cached pickle.

| Logical input | cit-Patents | com-lj | Purpose |
| --- | ---: | ---: | --- |
| `datasets/abcde/<graph>.txt` SHA-256 | `f8797f004315acf99faaee62b08ce093109968ba82bb52d55c7bc8b92e4918b9` | `835d5175a7309fedd782fc505407a5d140587540b27d4eab64df9f3f3eba2add` | Edge text |
| `datasets/abcde/<graph>-score.txt` SHA-256 | `48f352137529955aed7faf1fd06be1ded7fe77708ca0989683ef984733ab71a6` | `78a77750ac83057a6c62e5cef3ef34c50a8c6fc7603d0b460eb91a0d480d4` | Score text |
| Nodes / C3 undirected CSR arcs | 3,764,117 / 33,023,480 | 3,997,962 / 69,362,378 | Topology check |
| Expected selected rows | 662 | 1,086 | Fail-closed selector |

The edge text has two integer labels per non-comment line. The score text has
one scalar per nonblank line and has no node label. C3's `load_edges` applies
`np.unique`, giving compact id `i` to the `i`th sorted original label;
`build_csr(..., symmetrise=True)` drops loops, adds reverse arcs, collapses
duplicates, and sorts adjacency. BRAVA's importer independently sorts labels.
The required identity is therefore:

```
score row i  <->  C3 compact id i  <->  sorted original node label[i]
```

Read score lines as text, retain the literal, and decide zero with `Decimal`,
not a float. Assert one score per compact node and `score_row == compact_id`.
The selector writes a separate input-derived target artifact:

```
results/phase6_precision_witness_targets.csv
  graph,score_row,compact_id,original_node_id,printed_score_text,degree,
  edge_sha256,score_sha256
```

Its manifest records logical paths and hashes only, never the machine-specific
temporary checkout path.

## Bounded selection and witness

The target selector replays C3 local topology only:

1. Build one graph's C3-compatible sorted simple undirected CSR.
2. Run `zero_set(A, A, n)`, then select `score_is_zero & ~structural_zero`.
3. Require the pinned counts of 662 and 1,086; reject a changed hash, row count,
   topology, duplicate identity, or target count before any witness output.

This reconstructs the already reported target universe; it is not centrality
computation. The new calculation for each selected vertex `v` is independent:
enumerate unordered neighbour pairs `(a,b)` in lexicographic compact-id order.
Test that they are nonadjacent by binary search in the sorted CSR, then obtain
`c = |N(a) intersection N(b)|` by exact two-pointer intersection. It allocates
no neighbour-pair materialisation.

For a nonadjacent pair, `a-v-b` is a length-two shortest path. Its `c` common
neighbours each supply a length-two shortest route, so the pair's contribution
through `v` is `1/c`. Under the conventional unordered-pair unnormalised
undirected definition,

```
BC(v) >= 1/c.
```

Scan every usable pair and retain the minimum `c`, breaking ties by `(a,b)`.
Thus a row without a threshold witness has exhausted the entire one-pair witness
class; it remains inconclusive about all other source--target pairs and cannot
upper-bound `BC(v)`.

Affected nodes were previously reported as degree 3--18. Verify this as a
preflight condition; if any target lies outside `[3,18]`, stop rather than
silently changing the bounded search. Once verified, at most
`1,748 * C(18,2) = 267,444` pairs are examined.

> **Superseded 2026-09-10 by Claude Opus 5: the lower bound was wrong and is
> now 2.** The paragraph above is retained as the registered prediction. Its
> instruction was followed -- the first real execution of the witness stopped,
> on both pinned graphs, with `selected target degree 2 outside [3,18]` -- and
> the investigation that followed falsified the bound rather than the data.
>
> Two is the structural *minimum*, not an anomaly. A selected row is one whose
> printed score is zero and one pair of whose neighbours is nonadjacent. A
> degree-two node with two nonadjacent neighbours meets that, and is positive
> for the reason given above: `a-v-b` is a length-two shortest path, so
> `BC(v) >= 1/c > 0`. A floor of 3 is unsatisfiable in principle for a
> legitimate class of targets and silently discards them.
>
> The topology was never in doubt. A read-only instrumented replay of the same
> predicate on cit-Patents reproduced two *other* pinned quantities exactly --
> 709,724 printed zeros and **662** selected rows -- so only the degree
> prediction was wrong. Measured degree range there is **`[2,6]`**, and
> **424 of the 662 targets have degree two**:
>
> | Degree | 2 | 3 | 4 | 5 | 6 |
> |---|--:|--:|--:|--:|--:|
> | Targets | 424 | 178 | 26 | 33 | 1 |
>
> No artifact in this repository records the `3--18` measurement; `grep` finds
> the range only in this document. It was inherited from a prior report, and
> because the witness had never completed a run it had never been testable.
>
> **The upper bound was wrong too, and is replaced rather than raised.**
> cit-Patents passed with a measured maximum of 6, which made 18 look like a
> safe envelope. com-lj then failed with `degree 34 outside [2,18]`: its
> measured range is **`[2,111]`**, and **412 of its 1,086 targets exceed 18**.
> So the inherited range is wrong at *both* ends on *both* graphs -- while both
> pinned counts (662 and 1,086) and both printed-zero counts reproduced
> exactly, on com-lj as on cit-Patents.
>
> 18 was never an independent resource guard. It was a second consequence of
> the same wrong degree claim, used to state the `1,748 * C(18,2) = 267,444`
> budget above. The real cumulative scan is the sum of `C(degree,2)` over
> selected targets: **1,459** for cit-Patents and **293,013** for com-lj,
> **294,472** together -- about 10% over the quoted figure. This paragraph
> already states that the intersection scans are constant-extra-memory
> streaming work, so that count bounds *time*, not memory, and a 10% overrun of
> a few hundred thousand two-pointer intersections is not an envelope breach.
>
> Capping per-node degree is therefore the wrong instrument: it rejects lawful
> targets in order to limit the cumulative scan only indirectly. The gate now
> guards **the cumulative pair scan itself**
> (`precision_witness.MAX_TOTAL_PAIR_SCAN`, a declared budget set far above the
> measured 294,472 so it binds on a runaway rather than on real data), with
> per-node degree bounded only by the graph and floored at
> `MIN_TARGET_DEGREE = 2`. Every run records `minimum_degree`,
> `maximum_degree`, `total_pair_scan` and `total_pair_scan_budget` in its
> summary, so the resource claim is checkable from the artifact instead of
> resting on a predicted degree range.
>
> Regression tests: `verify_c3_precision_witness.py::
> test_degree_two_structurally_positive_node_is_a_valid_target` and
> `::test_pair_scan_budget_replaces_the_degree_ceiling` (which reproduces the
> degree-34 com-lj failure on a synthetic star).
>
> **This is a design amendment, not a silent edit**: the registered prediction
> above is retained verbatim, it was tested, and it failed. It was put to
> Rachit and **approved on 2026-09-10** ("the pair-scan replacement is fine"). The intersection scans are
constant-extra-memory streaming work.

## Exact conditional comparisons

The score producer's normalisation is unknown. Only if it used endpoint-
excluding normalised undirected betweenness may the result be reported as

```
BC_normalized(v) >= 2 / ((n - 1) * (n - 2) * c).
```

Let `D = (n-1)(n-2)`. Use strict positive-integer cross-products, never binary
floating point or a guessed rounding tie rule.

| Graph | `D` | `2/(D*c) > 5e-15` | largest passing `c` | `2/(D*c) > 1e-14` | largest passing `c` |
| --- | ---: | --- | ---: | --- | ---: |
| cit-Patents | 14,168,565,497,340 | `2*10^15 > 5*c*D` | 28 | `2*10^14 > c*D` | 14 |
| com-lj | 15,983,688,159,560 | `2*10^15 > 5*c*D` | 25 | `2*10^14 > c*D` | 12 |

Store `numerator=2`, `denominator=D*c`, and both decision cross-products. A
formatted decimal is display-only. Under the stated graph and normalisation
assumptions, a `>5e-15` witness rules out nearest-to-14-decimal printing zero;
a `>1e-14` witness also rules out ordinary nonnegative truncation to 14
decimals. Neither distinguishes clamping or another pipeline, nor establishes
the release graph/label convention or any exact score.

## Outputs and resource contract

Write only new artifacts below `results/phase6_precision_witness/` after all
preflight checks pass. Each row reports:

```
graph,score_row,compact_id,original_node_id,degree,
a_compact_id,b_compact_id,a_original_node_id,b_original_node_id,
common_neighbor_count,rational_numerator,rational_denominator,
gt_5e15,gt_1e14,qualifying_pair_count,edge_sha256,score_sha256
```

The JSON summary records target count, usable-pair count, both threshold totals,
maximum degree, all examined pairs, hashes, configuration, and source hashes.
No existing `results_c3_*`, C4, registration, or score input is edited.

Run one graph, process, and CPU worker at a time. The original C3 selector's
global int64 edge-key acceleration is multi-GiB on com-lj and is not an
implementation option on this machine. The bounded external-sort and memmapped
CSR contract in the addendum below supersedes the former free-RAM gate; its
fixed resource envelope, storage preflight, and clean-stop rules apply.

## Tests before a raw execution

1. **Identity and CSR semantics:** non-monotone labels prove sorted
   original-id/score-row mapping; loops and duplicate edges prove C3-compatible
   simple-undirected adjacency.
2. **Selector:** toy path/triangle score text proves exactly `printed zero AND
   non-simplicial`; bad hashes, row count, duplicate ids, and target counts fail.
3. **Witness:** a diamond `a-v-b` and `a-x-b` gives `c=2` and `1/2`; a clique
   yields no usable pair; multiple pairs choose the smallest `c` deterministically.
4. **Integer boundaries:** cit `28/29` at `5e-15`, `14/15` at `1e-14`; com-lj
   `25/26` and `12/13` respectively must pass/fail. Equality fails because the
   claim is strictly greater.
5. **Forbidden work:** monkeypatch exact-centrality entry points and assert no
   call; reject workers other than one and assert no model, checkpoint, or
   PyTorch import.
6. **Raw preflight:** all four hashes, score/node counts, 662/1,086 counts,
   structural-positive selection, degree bound, and output identities pass before
   any authoritative result. A failure emits no partial result.

Implementation awaits the structural lane freeze. Even then, its final prose
must retain the unknown-normalisation condition and must not change the C3 P4
status.

## Addendum — bounded-memory C3-topology construction (2026-09-08)

This addendum replaces the earlier operational `>= 5 GiB` free-memory gate.
That gate was a sensible warning about the existing all-in-memory C3 loader,
but it would turn a reproducible local check into an indefinitely blocked task
on this 16 GiB workstation, where the live snapshot had 3.46 GiB free. The
implementation must instead use the bounded construction below and reject only
an input-identity or construction-invariant failure. It must not use available
RAM as a proxy for correctness.

### Why the existing loader is unsuitable for the raw graphs

The relevant C3 path is `analyse_c3_benchmarks.py`:

```
load_edges: np.loadtxt(..., int64) -> np.unique(..., return_inverse=True)
build_csr:  concatenate both directions -> scipy CSR -> sum_duplicates
zero_set:   _edge_keys, including np.repeat(row owners), then a sorted int64 key array
```

For com-lj alone, the final C3 topology has 69,362,378 arcs. The final CSR
indices occupy about 265 MiB if `int32`, but `_edge_keys` needs about 529 MiB
and its temporary row-owner array needs another about 529 MiB. Before those,
the raw `int64` endpoint array, inverse labels, symmetric concatenations, and
SciPy construction temporaries coexist. Thus the existing loader is a useful
semantic reference and a small-fixture oracle, but it has no defensible
working-set bound below the current free memory. Do not attempt to make it safe
by choosing an arbitrary larger free-memory threshold.

The repository's ordinary `influence.preprocessing.load_edgelist` is also not
the implementation path: it collects Python `(u, v)` tuples and restricts to
the LCC. The witness graph must retain C3's whole sorted-label topology,
including every non-isolated label appearing in the raw edge text. The raw
inputs are outside this repository under the BRAVA checkout supplied as
`--brava`; the exact paths are:

```
<brava>/datasets/abcde/cit-Patents.txt
<brava>/datasets/abcde/cit-Patents-score.txt
<brava>/datasets/abcde/com-lj.txt
<brava>/datasets/abcde/com-lj-score.txt
```

### Disk-backed construction, one graph at a time

Use a per-run temporary directory under the new Phase 6 output directory. It
contains only derived, resumeless files and is removed after a successful
graph; an interrupted run leaves it in place for inspection and the next run
creates a new directory. No input, C3 artifact, or registered result is
modified.

1. Stream the raw graph bytes once through SHA-256 and a strict two-integer
   parser compatible with the known ABCDE edge text: blank lines and lines
   whose first non-whitespace character is `#` or `%` are skipped; the first
   two whitespace-separated fields are signed base-10 integers; every other
   data line is rejected rather than silently repaired. Count parsed rows.
   The SHA-256 must match the pinned graph hash before derived output is
   accepted.
2. Append the two original labels from each parsed row as `int64` values to
   fixed-size external-sort runs. Sort each run in place and k-way merge the
   runs while suppressing equal neighbours. The resulting `original_ids.i64`
   is the strictly increasing C3 map: compact id `i` means
   `original_ids[i]`. It is therefore the same sorted mapping that
   `np.unique(raw_endpoints, return_inverse=True)` gives, without retaining
   raw endpoints or an inverse array. Record its byte SHA-256 and assert its
   length is the pinned node count.
3. Stream the graph a second time. Map each endpoint chunk with
   `np.searchsorted(original_ids_memmap, endpoint)`, assert the returned label
   equals the original label, discard `u == v`, and write the canonical
   `uint64` key `min(u,v) * n + max(u,v)` to external-sort runs. Merge these
   sorted runs while suppressing equal keys. This is exactly C3's loop removal
   plus duplicate collapse after symmetrisation: one surviving key represents
   one simple undirected edge.
4. Stream every surviving canonical edge once and emit its two directed
   `uint64` arc keys, `u*n+v` and `v*n+u`, into another external sort. Merge
   the runs in ascending-key order. The decoded `(row, column)` sequence is
   row-major and each row's columns are already increasing. Allocate only
   memmapped `indptr` and `indices` files and fill them sequentially from that
   stream, inserting identical offsets for empty rows. Assert exactly the
   pinned 33,023,480 and 69,362,378 arcs, respectively, and that each row is
   strictly ascending. A materialised data vector is unnecessary because every
   value is semantically one; if a SciPy compatibility object is needed, write
   its `uint8` all-ones data array as a third memmap rather than allocating it
   in RAM.
5. Define the topology fingerprint as SHA-256 over a version tag, `n`, `nnz`,
   little-endian `uint32 indptr`, and little-endian `uint32 indices`. Record it
   together with the raw graph hash, score hash, parser row count,
   `original_ids` hash, and arc count in the Phase 6 manifest. `uint32` is
   valid for both graphs: `n < 2^32` and `nnz < 2^32`. The fixture tests below
   compare the generated `indptr` and `indices` byte-for-byte with C3's
   `load_edges`/`build_csr(..., symmetrise=True)` result, so this narrower
   representation cannot silently change C3 semantics.

The score text is read sequentially after topology construction. Each nonblank
line is retained as literal text and parsed with `Decimal`; row counter `i` is
the compact id. Assert score rows equal `n` and use
`original_ids_memmap[i]` for the emitted original id. This preserves the
required `score row == compact id == sorted original-id position` identity
without holding the score column in memory.

### Exact selector without the global arc-key index

Do not call C3's vectorised `zero_set` on these raw graphs: its global arc-key
array is an acceleration, not part of the zero-set definition. Instead, while
streaming literal score rows, inspect only rows whose printed score is exactly
zero. For candidate `v`, take sorted neighbour slices directly from the
memmapped CSR. `v` is structurally positive exactly when one pair of distinct
neighbours is nonadjacent. Test pairs in lexicographic compact-id order and
test adjacency by scalar binary search in the first neighbour's sorted CSR
row. Stop at the first missing edge. If no missing pair occurs, `v` is
structurally zero.

This is the same simplicial criterion used by C3, with a different traversal
order. It allocates no `n`-length Boolean mask, no `nnz`-length arc keys, no
row-owner array, and no neighbour-pair array. It also produces the first
nonadjacent pair for each selected row; that pair is already a valid witness
candidate, though the witness phase must still enumerate every local pair to
minimise `c` as specified above. Require the pinned selected counts (662 and
1,086) and the existing degree range [3,18] before emitting target or witness
artifacts.

> **Amended 2026-09-10 by Claude Opus 5.** The degree ceiling is withdrawn and
> replaced by a cumulative pair-scan budget, with a floor of 2; see
> the superseding note in "Exact conditional comparisons" for the measurement
> and the reasoning. The pinned **counts** are unchanged and were *confirmed*
> by the same investigation -- an instrumented replay selected exactly 662 rows
> on cit-Patents -- so the count gate stands as written.

### Hard resource envelope and preflight

The former fixed statement of a 1.3 GiB payload and a 2 GiB gate was
under-specified: it did not say whether an external merge materialises a full
merged arc file, nor when prior sort runs are removed. The bound below is the
required contract. It counts every derived file that is live at the same time;
it does not count the already-present BRAVA input text against scratch-space
free bytes. If input and scratch use the same volume, its existing input bytes
are already absent from that volume's reported free space.

Before any derived file is created, the hash pass must record both the input
file byte length `T` and exact parsed raw-row count `R`. These values are not
recoverable from the pinned node/arc counts: raw duplicate and loop rows are
deliberately removed later. The supplied hash-matching BRAVA text is therefore
the source of truth; do not substitute a SNAP catalogue count or an archive's
compressed size for `R` or `T`. The files are absent from this repository but
are available at `analyse_c3_benchmarks.DEFAULT_BRAVA` in the external BRAVA
checkout. The bounded read-only preflight in
`results/phase6_precision_input_preflight.json` measured them there.

| Graph | Edge bytes `T` | Parsed rows `R` | Score bytes | Score rows | Hash / row checks |
| --- | ---: | ---: | ---: | ---: | --- |
| cit-Patents | 256,154,375 | 16,511,741 | 71,518,223 | 3,764,117 | both pinned hashes match; every edge line is exactly two signed integers |
| com-lj | 502,171,107 | 34,681,189 | 75,961,278 | 3,997,962 | both pinned hashes match; every edge line is exactly two signed integers |

The score-row counts equal the pinned node counts. cit-Patents has one more
raw row than final canonical edges; com-lj has the same count. These are
observed input facts, not inferred graph semantics.

Let `n` be the pinned node count, `A` the pinned final CSR arc count, and
`E=A/2` the final canonical undirected-edge count. Every record below is a
binary integer record; text parsing and score rows are not retained.

| Live derived object | Record width | Count / upper bound | Bytes |
| --- | ---: | ---: | ---: |
| Label-sort runs | signed `int64` | `2R` labels | `16R` |
| Final `original_ids.i64` | signed `int64` | `n` | `8n` |
| Canonical-edge sort runs | `uint64` | at most `R` keys | `8R` |
| Final canonical-edge file | `uint64` | `E` keys | `8E` |
| Arc-sort runs | `uint64` | `A=2E` keys | `8A` |
| CSR `indices` | `uint32` | `A` | `4A` |
| Optional CSR all-ones `data` | `uint8` | `A` | `A` |
| CSR `indptr` | `uint32` | `n+1` | `4(n+1)` |

The lifetimes are mandatory. First merge label runs directly to
`original_ids.i64`, then delete every label run. Next merge canonical runs
directly to the deduplicated canonical-edge file, then delete every canonical
run. Finally retain only `original_ids.i64` and the canonical-edge file while
arc runs are merged **directly** into `indptr`, `indices`, and the reserved
optional `data` memmap. No `arcs.merged.i64`, full merged-run output, copied
CSR, Python edge list, row-owner array, or global arc-key array is permitted.
If an implementation materialises a merged arc file, it adds `8A` bytes and
must be rejected rather than treating this envelope as applicable.

With those deletion points and direct final merge, the preflight scratch bound
is:

```
D_label = 16R + 8n
D_canonical = 8R + 8E + 8n
D_arc = 8A + 8E + 4A + A + 4(n + 1) + 8n
D_peak = max(D_label, D_canonical, D_arc)
required_free_bytes = D_peak + 512 MiB
```

The `512 MiB` reserve covers filesystem allocation granularity, manifests,
logs, interrupted-close headroom, and a phase restart; it is not a hidden
data structure. The implementation must calculate and persist all four values
from observed `R`, `T`, `n`, and `A`, then require the selected scratch volume
to have at least `required_free_bytes` available. A fixed 2 GiB gate is not a
substitute for this calculation, although it is sufficient only when this
preflight says so.

The final-topology part of the peak is already known from the pinned C3
counts, including the optional data memmap. It is `606,568,568` bytes
(0.565 GiB) for cit-Patents and `1,227,135,974` bytes (1.143 GiB) for com-lj.
With the measured raw rows, cit-Patents peaks at 606,568,568 bytes (0.565 GiB)
and requires 1,143,439,480 bytes free (1.065 GiB) after reserve. com-lj peaks
at 1,227,135,974 bytes (1.143 GiB) and requires 1,764,006,886 bytes free
(1.643 GiB) after reserve. Therefore the former 2 GiB gate is sufficient for
these exact, already-existing inputs only under the mandated deletion schedule
and direct CSR merge. The explicit formulas remain the authority for any
changed hash, row count, parser result, or implementation that changes file
lifetimes.

Set the external-sort payload cap to 192 MiB, use an 8 MiB text buffer, at
most 40 MiB of fixed numeric parser/mapping chunks, and at most 8 MiB total
merge buffers. In-place numeric quicksort is sufficient because stability has
no semantic role. These application-owned numeric allocations total at most
248 MiB during a run-sort phase; Python/runtime and operating-system working
sets are observed and reported, not claimed to be part of that array bound.
The final com-lj CSR maps occupy at most 363 MB decimal including optional
data. Selector and witness code must hold only scalar counters and memmap
views of rows, never copied rows or Python lists of edges or pairs. At most
one graph, process, and CPU worker may run.

The implementation should obtain the current process working set and available
physical memory before each phase, report both in the manifest, and fail only
if its own caps cannot be configured or a requested memmap/scratch file cannot
be created. It must not require 5 or 6 GiB available RAM. If the operating
system reports pressure during a run, flush and close completed maps and stop
cleanly before any result publication; the input and topology checks will be
repeated on the next fresh run.

### Required implementation tests

In addition to the previously listed tests, add a small raw-text fixture with
comments, non-monotone signed labels, loops, repeated/reversed edges, and an
isolated-by-loop-only label. Compare the bounded constructor byte-for-byte to
the existing C3 `load_edges` plus `build_csr` arrays, including sorted original
ids, row offsets, and row indices. Check that the loop-only label is retained
in `original_ids` but has an empty CSR row, exactly as C3 does. A test with a
malformed data line must fail before any target output. Finally, run the
selector against the same fixtures and assert its structural-positive mask
equals C3 `zero_set`'s complement; this validates the no-global-key traversal
without turning the raw production run back into the memory-heavy loader.

<!-- END docs/phase6_precision_witness_design.md -->

---

## <a id="rec-phase6_r1_ablation_design"></a>`docs/phase6_r1_ablation_design.md`

<!-- BEGIN docs/phase6_r1_ablation_design.md sha256=9bf2c1dc0f224d7b504186782976728fa0280799a67eef3480f2ab557f7fd0c9 date=2026-09-08 author=unsigned -->
# Radius-one subgraph attribution follow-up

Written 2026-09-08 before new fits. The old three-network decomposition is kept as
history; this run closes its corpus gap under the current feature registry and objectives.

Scope: all five current graphs, four reported targets, radius1, seeds0–9, five folds,
pinned120-tree RF/minimum leaf2. Betweenness trains log1p and is scored in original target
units; the three spreading targets keep the raw objective. No other hyperparameter changes.

Feature sets, preserving the pipeline's declared column order:

1. node+edge at radius1 (38 columns in current caches).
2. Set1 plus eligible non-orbit subgraph features (ego_betweenness, triangle_count).
3. Set2 plus eligible node-orbit indices below15 (five columns).
4. Full radius1 structural set including remaining17 five-node node orbits (62 columns).

Edge-orbit columns stay in the common baseline. Select eligible columns using registry
hop/tier fields, distinguish `orbit_` from `eorbit_`, reject unknown/missing columns and
assert nestedness/full-set identity before fitting. These comparisons measure usefulness
for this learner and task, not universal expressive sufficiency of graphlets.

Retain all800 cell observations (5graphs x4targets x4sets x10seeds), with paired increments
for60 graph/target/step contrasts. Report mean, sample SD, sign counts and the descriptive
abs(mean)>2SD flag. No new formal significance or multiplicity claim is made. Preserve
old data, save separate source/config/input hashes, seed/fold identities and resumable
row integrity; no name-only join or partial-seed aggregation may silently pass.

Existing end-set OOF results may be reused ONLY if their exact current feature order,
objective, folds/seeds, targets and stored provenance are verified. Otherwise refit.
At least a representative end-set equivalence check is required before reuse. Any reuse
is explicitly labelled by source path/hash, not presented as a new fit. This can avoid
duplicating valid endpoint sweeps while measuring the two intermediate feature sets.

**Pre-fit provenance decision, 2026-09-09:** inspection found the existing OOF
archives lack the column, fold, objective, estimator and input provenance required
by this gate. All four sets will therefore be refitted. The five inspected registries
give exactly 38/40/45/62 ordered columns. The implementation contract is in
`docs/phase6_r1_ablation_implementation_brief.md`; the planned 800 cells and 60
paired contrasts are unchanged.

Tests: four-set membership with orbit2 vs orbit23 and edge-orbit names, nestedness,
missing-feature rejection, objective selection, wrong seed/config resume failure, and
independent paired-difference arithmetic. Reconcile HANDOFF Finding3 and study's radius-one
section using measured per-network outcomes; retain contradictory/null effects if found.

<!-- END docs/phase6_r1_ablation_design.md -->

---

## <a id="rec-phase6_r1_ablation_implementation_brief"></a>`docs/phase6_r1_ablation_implementation_brief.md`

<!-- BEGIN docs/phase6_r1_ablation_implementation_brief.md sha256=b21775f1d21f85183347a1c5ce598655eb67147d481792d7be40a3bbf3198341 date=2026-09-08 author=unsigned; P1-01 update by Claude Opus 5 (2026-09-12) -->
# R1 Ablation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a provenance-bound, resumable five-network radius-one ablation with four nested structural feature sets and paired-within-seed attribution results.

**Architecture:** A new helper owns feature-set construction, target-objective selection, cache fingerprints, fold digests, and immutable-cell validation. A new runner writes one atomically committed cell artifact for each fit; a separate analyzer verifies the complete cell universe before creating the sorted cell table, paired contrasts, and report. Existing sweeps and OOF stores remain read-only historical inputs.

**Tech Stack:** Python 3.12, the existing `influence` conda environment, NumPy, pandas, SciPy, scikit-learn `RandomForestRegressor` / `TransformedTargetRegressor`.

**Spec:** [phase6_r1_ablation_design.md](phase6_r1_ablation_design.md)

**Binding readiness amendment, 2026-09-10:** apply
[the readiness addendum](phase6_r1_ablation_readiness_addendum.md) wherever it
corrects the interfaces below. Keep the shared experiment/estimator modules
unchanged. The R1-only factory accepts a bounded inner-worker count; there is
always one outer fit process. Scientific/input identity is immutable before the
pilot, while the pilot-selected execution identity is frozen before the first
authoritative cell; bind both in every checkpoint to avoid a circular manifest
dependency. Use unique temporary files per write attempt and retain interrupted
temps as evidence. Validate raw graph/LCC/node identities, hash both rejected
OOF candidates, reject nonfinite predictions and metrics, and hash final products.

The representative pilot cell is ca-HepTh, spread_mean, full_r1_structural,
seed 0, all five folds, run at inner jobs 1/4/8. Record prediction absolute and
scale-relative gaps plus tau gaps against jobs 1; declare numerical tolerances
in code and tests before executing it. The 800-cell extrapolation is a rough
single-cell timing estimate, not a promised runtime. Check active process CPU
budgets before the pilot/full launch: the current bootstrap and buffered sweep
may together reserve all 16 logical workers. In that state queue the R1 pilot
until one finishes rather than adding another concurrent 8-worker fit. This is
an operational capacity gate, not a scientific dependency between the results.

## Global Constraints

- Use `C:/Users/Rachit/miniconda3/envs/influence/python.exe`; do not install packages, use GPU/PyTorch, or run more than one fit worker.
- Fit only the five current cache bundles, at radius 1, five KFold splits, seeds `0..9`, and the pinned 120-tree, `min_samples_leaf=2` forest.
- Train `betweenness` with `rf_log1p`, score against original target units; use raw `rf` for `spread_mean`, `spread_cv`, and `spread_resid`.
- Create only the new R1 helper, runner, analyzer, verifier, and `results/phase6_r1_ablation/` artifacts. Do not modify, replace, append to, or reuse a root `sweep_*.csv` or `cache_oof_*.npz`.
- A run is valid only with exactly 800 cells and exactly 60 paired adjacent-set contrasts. Duplicate, missing, mixed-provenance, invalid-seed, or partial cells are errors.
- Report paired mean gain, sample SD (`ddof=1`), positive/zero/negative counts, and the descriptive flag `abs(mean_gain) > 2 * paired_sd`. This is not a p-value, confidence interval, multiplicity procedure, or claim of universal graphlet sufficiency.
- No commit is part of this task.

---

## Inspected inputs and decision on endpoint reuse

The five current registries produce the same declared R1 ladder, in registry
row order:

| Set id | Definition | Columns |
|---|---|---:|
| `node_edge` | `hop <= 1`, tier `node` or `edge` | 38 |
| `plus_nonorbit_subgraph` | `node_edge` plus `ego_betweenness`, `triangle_count` | 40 |
| `plus_orbit_lt15` | preceding set plus `orbit_02_P3_centre`, `orbit_07_claw_centre`, `orbit_11_paw_hub`, `orbit_13_diamond_deg3`, `orbit_14_K4` | 45 |
| `full_r1_structural` | every `node`, `edge`, or `subgraph` feature at `hop <= 1` | 62 → **56** |

> **Updated 2026-09-12 by Claude Opus 5 (Task 6 finding P1-01).** The 62 was measured
> against the registries before six 5-node orbits (56, 57, 65, 66, 68, 70) were retagged
> from hop 1 to hop 2 on 2026-09-11. The corrected registries give 56; `verify_r1_ablation.py`
> pins `(38, 40, 45, 56)`. The 800-cell run made against the 62-column set is archived at
> `results/phase6_r1_ablation_pre_orbit5_retag_20260910/` and a fresh run on the corrected
> ladder replaces it under `results/phase6_r1_ablation/`.

The 17 final additions are `orbit_23_g5`, `orbit_33_g5`, `orbit_42_g5`,
`orbit_44_g5`, `orbit_55_g5`, `orbit_56_g5`, `orbit_57_g5`, `orbit_58_g5`,
`orbit_61_g5`, `orbit_65_g5`, `orbit_66_g5`, `orbit_67_g5`, `orbit_68_g5`,
`orbit_69_g5`, `orbit_70_g5`, `orbit_71_g5`, and `orbit_72_g5`.
`eorbit_` names are edge-tier members of the common baseline and must never be
classified as node orbits.

| Network | Nodes | Edges | Expected cells |
|---|---:|---:|---:|
| ca-GrQc | 4,158 | 13,422 | 160 |
| ca-HepTh | 8,638 | 24,806 | 160 |
| email-Eu-core | 986 | 16,064 | 160 |
| facebook_combined | 4,039 | 88,234 | 160 |
| p2p-Gnutella08 | 6,299 | 20,776 | 160 |

The 160 cells per graph are `4 targets * 4 sets * 10 seeds`; the corpus has
800. The fixed target order is `spread_mean`, `spread_cv`, `spread_resid`,
`betweenness`.

**Refit decision: refit all four sets and all targets.** Each current
`cache_oof_<network>.npz` has exactly 640 arrays with names in the form
`target|radius|richness|seed`; it has no embedded manifest, selected-column
list/hash, cache input hash, target-objective identifier, fold digest, or
estimator source/configuration hash. Its existing `betweenness` endpoint also
belongs to the raw objective, whereas this design requires `rf_log1p`.
Names and a matching column count are not provenance. The runner records the
candidate OOF path and hash as a rejected reuse candidate, then performs a
fresh, single provenance-bound fit for every cell.

## Files and output contract

| File | Responsibility |
|---|---|
| Create `influence/r1_ablation.py` | Pure feature selection, objective routing, hashing, fold digesting, expected-key construction, and artifact validation. |
| Create `probe_r1_ablation.py` | Single-process CLI runner and atomic checkpoint writer. |
| Create `analyse_r1_ablation.py` | Strict reader, paired contrast calculator, and final result writer. |
| Create `verify_r1_ablation.py` | Deterministic unit/integration verifier with temporary artifacts; never fits the five-network corpus. |
| Create `results/phase6_r1_ablation/manifest.json` | Immutable launch configuration and source/cache/rejected-OOF hashes. |
| Create `results/phase6_r1_ablation/cells/*.json` | One committed, self-validating record per completed cell. |
| Create `results/phase6_r1_ablation/cells.csv` | Sorted materialisation of all 800 verified cell records. |
| Create `results/phase6_r1_ablation/paired.csv` | The 60 verified paired contrasts. |
| Create `results/phase6_r1_ablation/RESULTS_r1_ablation.txt` | Human-readable report with scope and descriptive limits. |

`manifest.json` is created once with exclusive creation. Its canonical JSON
SHA-256 is `run_id`; every cell records it. It contains the fixed target/set
orders, seeds, folds, estimator definitions, Python/library versions, hashes
of the five feature/target/registry/meta files, hashes of the helper/runner/
analyzer/estimator/experiment/feature/target source files, and the rejected
candidate OOF paths and hashes. On resume, recompute every hash and canonical
configuration byte-for-byte; a mismatch stops before loading an existing cell.

A cell is written only to `cells/<network>__<target>__<set>__s<seed>.tmp`,
flushed and `fsync`ed, then atomically renamed to `.json`. The JSON includes
all key fields, `run_id`, `fold_digest`, ordered-column SHA-256, target-column
SHA-256, estimator/objective ids, metrics, fit seconds, and a content SHA-256
over the same canonical record excluding that checksum. A pre-existing final
cell may be skipped only after verifying all of those values, its checksum,
and its key; otherwise stop. The final CSVs are derived from verified final
cells and written by the same temporary-file/atomic-rename procedure. No CSV
is a resume source of truth.

### Task 1: Build the pure R1 contract helper

**Files:**

- Create: `influence/r1_ablation.py`
- Test: `verify_r1_ablation.py`

**Interfaces:**

```python
TARGETS = ("spread_mean", "spread_cv", "spread_resid", "betweenness")
SET_IDS = ("node_edge", "plus_nonorbit_subgraph", "plus_orbit_lt15", "full_r1_structural")
SEEDS = tuple(range(10))
NETWORKS = ("ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined", "p2p-Gnutella08")

def select_r1_sets(features: pd.DataFrame, registry: pd.DataFrame) -> dict[str, list[str]]: ...
def objective_for(target: str) -> tuple[str, Callable[[int], Regressor]]: ...
def fold_digest(n_rows: int, seed: int, n_splits: int = 5) -> str: ...
def expected_keys(tags: tuple[str, ...] = NETWORKS) -> set[tuple[str, str, str, int]]: ...
def canonical_sha256(value: dict | list) -> str: ...
```

- [ ] Write verifier cases that construct a registry containing `orbit_02`,
  `orbit_23`, and `eorbit_02`, then assert the four ordered set lengths are
  `38, 40, 45, 62` (56 after the 2026-09-11 retag, see the table note), `orbit_02` enters only Set 3, `orbit_23` enters only Set
  4, and `eorbit_02` remains in Set 1.
- [ ] Implement `select_r1_sets` by filtering registry rows in file order,
  requiring every selected feature to occur once in `features.columns`, and
  parsing node-orbit indices only from `^orbit_(\d+)_`. Reject a malformed
  `orbit_` name, an unknown tier, a duplicate feature, a missing selected
  feature, a non-nested set, or a Set-4 list that differs from
  `select_features(features, registry, max_hop=1, tiers=("node", "edge", "subgraph"))`.
- [ ] Implement `objective_for`: return `("log1p", make_rf_log1p)` for
  `betweenness`; return `("raw", make_rf)` for the three spreading targets;
  reject every other name. The runner will pass the returned factory to
  `out_of_fold_predictions`, so the existing pinned 120-tree/leaf-2 RF stays
  the single model definition.
- [ ] Implement `fold_digest` by creating
  `KFold(n_splits=5, shuffle=True, random_state=seed)`, filling an `int8`
  fold-owner vector indexed by test rows, and hashing `n_rows`, `n_splits`,
  `seed`, and the vector's little-endian bytes. This binds the fold allocation
  rather than merely recording a seed label.
- [ ] Run `C:/Users/Rachit/miniconda3/envs/influence/python.exe verify_r1_ablation.py`
  and require the membership, objective, digest-repeatability, and expected
  800-key checks to pass.

### Task 2: Implement the provenance-bound runner and resume protocol

**Files:**

- Create: `probe_r1_ablation.py`
- Modify: `influence/r1_ablation.py`
- Test: `verify_r1_ablation.py`

**Interfaces:**

```python
def build_manifest(root: Path, tags: tuple[str, ...]) -> dict: ...
def validate_manifest(root: Path, manifest: dict) -> None: ...
def read_verified_cell(path: Path, run_id: str) -> dict: ...
def write_atomic_json(path: Path, record: dict) -> None: ...
def run_cell(features: pd.DataFrame, targets: pd.DataFrame, columns: list[str],
             target: str, seed: int) -> dict: ...
```

- [ ] Give the CLI defaults `--out results/phase6_r1_ablation`, all five tags,
  and seeds `0..9`; reject an alternate tag, target, set, seed, radius, fold
  count, or worker count rather than creating a subset under the authoritative
  output path. Print each completed canonical key and the remaining count.
- [ ] At launch, hash every cache bundle (`cache_features_*`, `cache_targets_*`,
  `cache_registry_*`, `cache_meta_*`) and the required source files. Inspect,
  but do not load as fit input, `cache_oof_*`; record the rejected-reuse reason
  and hash. Create or validate the immutable manifest before any model fit.
- [ ] For each expected key, reconstruct the exact R1 columns, call
  `assert_no_leakage(columns)`, select the objective factory, invoke
  `out_of_fold_predictions(X[columns].to_numpy(float64), y, n_splits=5,
  seed=seed, estimator=factory)`, then call `evaluate(y, predictions)` against
  the original `y`. Store the metrics and all binding identities in one atomic
  cell record.
- [ ] Make resume scan only final `cells/*.json`, reject an unexpected filename
  or key, validate every existing record, and run only absent expected keys.
  Leave `.tmp` files untouched as evidence of interruption but never count
  them; an existing final output with fewer than 800 cells is incomplete, not
  an analyzable result.
- [ ] Test temporary output cases: a valid completed cell resumes without a
  fit; a changed seed/config/hash, a malformed checksum, an unexpected cell,
  a duplicate key, and a partial final corpus all fail before result creation.

### Task 3: Implement the paired analyzer and final artifacts

**Files:**

- Create: `analyse_r1_ablation.py`
- Modify: `influence/r1_ablation.py`
- Test: `verify_r1_ablation.py`

**Interfaces:**

```python
CONTRASTS = (
    ("add_nonorbit_subgraph", "node_edge", "plus_nonorbit_subgraph"),
    ("add_orbit_lt15", "plus_nonorbit_subgraph", "plus_orbit_lt15"),
    ("add_remaining_g5_orbits", "plus_orbit_lt15", "full_r1_structural"),
)

def load_complete_cells(root: Path) -> pd.DataFrame: ...
def paired_contrasts(cells: pd.DataFrame) -> pd.DataFrame: ...
def write_final_artifacts(root: Path, cells: pd.DataFrame, pairs: pd.DataFrame) -> None: ...
```

- [ ] Require every cell to validate against the immutable manifest, then sort
  the exact 800 keys by network order, target order, set order, and seed. Do
  not use `pivot_table`, because it averages duplicate rows; first reject
  duplicates, absent keys, missing seeds, differing `run_id`, differing
  objective, differing feature hash, or differing fold digest.
- [ ] For each of five networks, four targets, and three consecutive set
  contrasts, align exactly the ten same-seed `kendall_tau` values and calculate
  `gain = tau_high - tau_low`. Emit mean, `std(ddof=1)`, positive/zero/negative
  counts, `n_pairs=10`, and `heuristic_star = abs(mean_gain) > 2 * paired_sd`.
  This produces exactly `5 * 4 * 3 = 60` rows.
- [ ] Write `cells.csv`, `paired.csv`, and `RESULTS_r1_ablation.txt` atomically.
  The report must call the stars descriptive, identify the fully refit
  provenance, state that only R1/radius-one results are covered, and retain
  null or contradictory per-network effects. It must not alter Finding 3 or
  study prose; reconciliation happens only after the measured artifacts exist.
- [ ] Test paired arithmetic independently with fixed lower/upper seed vectors
  whose gains include negative, zero, and positive values. Assert exact counts,
  sample SD, strict greater-than boundary behavior, and rejection when either
  endpoint lacks one of the ten seeds.

### Task 4: Verify the real cache contract without fitting

**Files:**

- Modify: `verify_r1_ablation.py`
- Modify: `docs/phase6_r1_ablation_implementation_brief.md` only if the
  inspected cache contract changes before implementation starts.

- [ ] Load the five real cache feature/registry/target files read-only and
  assert the exact set sizes `38, 40, 45, 62` (now `56`, repinned 2026-09-12), target availability, nesting,
  Set-4 identity, and the expected 800-key universe.
- [ ] Inspect each legacy OOF archive's central directory and assert that it
  contains the historical 640 bare prediction keys but no provenance manifest
  member. Assert `betweenness|1|node+edge|0` and
  `betweenness|1|node+edge+subgraph|0` are therefore ineligible for reuse,
  regardless of their presence.
- [ ] Run only `verify_r1_ablation.py` before the fitting lane. It must not
  call `out_of_fold_predictions`, `RandomForestRegressor.fit`, cache writers,
  or any training script.

## Self-review

- The design’s five graphs, four targets, radius 1, ten seeds, five folds,
  feature membership, pinned learner/objective, paired arithmetic, input/source
  hashes, and resumable integrity each map to Tasks 1–4.
- The implementation has no endpoint reuse path because the inspected OOF
  archives cannot prove the required provenance; every endpoint is measured in
  the same new run as the two intermediate sets.
- The expected totals are explicit: 800 cells, 160 per graph, 60 paired
  contrasts, and 10 seed pairs per contrast.
- The plan contains no fit command. Execution requires scoped harness review and
  a measured resource preflight. Root ruling, 2026-09-09: completion of the full
  bootstrap is not a scientific dependency of this ablation. A bounded concurrent
  run may proceed if its pilot establishes acceptable memory and CPU use; otherwise
  queue it. Keep one outer worker, record explicit within-forest `n_jobs`, bind that
  setting in the manifest and test prediction equivalence to the pinned default.
  The workstation has eight physical cores/sixteen logical threads; account for
  the existing bootstrap's eight forest threads when selecting the new setting.

---

## Execution and results, 2026-09-10 (Claude Opus 5)

> Added 2026-09-10 by Claude Opus 5. The brief above is the design and is unchanged. This
> section records that the design was built and run, and what it measured.

### Built

Four files, TDD, verifier before the fitting lane, exactly as specified:
`influence/r1_ablation.py` (pure), `probe_r1_ablation.py` (single-process runner, atomic
checkpoints), `analyse_r1_ablation.py` (strict reader + paired contrasts),
`verify_r1_ablation.py` (**26 tests, all passing**; it never fits the corpus, enforced by an
AST check on calls, not imports). Outputs live only under `results/phase6_r1_ablation/`;
nothing was written to a root `sweep_*.csv` or `cache_oof_*.npz`.

The determinism pilot gate passed before the main run: the `ca-GrQc / spread_mean /
full_r1_structural / seed 0` cell was refit at 1, 4 and 8 jobs and the Kendall tau agreed to
the last bit.

### Run

800 cells, `run_id afadc675f345d0dc1d626b4293cb1452fa6836e82bf02cad7c4fb26b4ae04441`,
completed exit 0. 60 paired contrasts, **19 flagged**.

| Contrast | Flagged |
| --- | ---: |
| `add_nonorbit_subgraph` | 2 of 20 |
| `add_orbit_lt15` | **0 of 20** |
| `add_remaining_g5_orbits` | 17 of 20 |

**The remaining 5-node orbits carry the r=1 effect and the 4-node-and-smaller orbits carry
none of it.** Peak gain +0.03515 tau (ca-GrQc/`spread_cv`); the `add_orbit_lt15` step never
exceeds 2.5e-4 in absolute mean on any of the twenty cells.

### The exceptions, kept as exceptions

Three cells do not flag on the 5-node step: ca-GrQc/`betweenness` (+0.00045, sd 0.00081),
email-Eu-core/`spread_resid` (+0.01163, sd 0.00855) and email-Eu-core/`betweenness`, which is
**negative** — −0.00049 with nine of ten seeds worse. The last is a small consistent harm
pointing opposite to every other network, and is reported rather than folded into a positive
summary. The two `add_nonorbit_subgraph` flags are both `betweenness`, so that step is
target-specific rather than tier-wide.

### What this does not license

The stars are the descriptive `|mean| > 2*sd` heuristic: no null distribution, no multiplicity
correction over 60 contrasts, ten seeds on one graph are not ten graphs. **Radius one only.**
The brief's standing requirement holds: findings are stated per graph, and the universal
expressive-power language elsewhere in the study is reconciled against these artifacts in a
separate step, never restated from them.

<!-- END docs/phase6_r1_ablation_implementation_brief.md -->

---

## <a id="rec-phase6_structural_target_noise_design"></a>`docs/phase6_structural_target_noise_design.md`

<!-- BEGIN docs/phase6_structural_target_noise_design.md sha256=bbec5aa3b25291d21071abce92fff099e2d82a84715060ab8823380b686177b4 date=2026-09-08 author=unsigned -->
# Phase 6 follow-up: structural-tier paired target uncertainty

**Written 2026-09-08 before the pilot produces results.** This is a new follow-up made possible by the extension's explicit training authorisation. It does not revise, replace, or append to the historical A7 dynamic-tier arm.

## Question and fixed scope

The existing target-refit results cover node+edge+subgraph+dynamic, while headline locality comparisons use analyse.FULL = node+edge+subgraph. This follow-up measures paired target-bootstrap movement in the latter structural tier only.

The runner will evaluate exactly five current networks (ca-GrQc, ca-HepTh, email-Eu-core, facebook_combined, and p2p-Gnutella08), the three Monte Carlo targets (spread_mean, spread_cv, spread_resid), radii 0--3, and 200 bootstrap replicates. Betweenness remains outside scope because it is exact rather than a live-edge Monte Carlo target.

Each replicate samples the 4,000 live-edge indices with replacement at resample seed 0. Within a network and replicate, that identical index vector rebuilds every target once and is reused for all four radii. Each refit has fixed fit seed 0. The runner records a SHA-256 identity for every resample vector, plus input/source/configuration hashes. It rejects a resumed CSV unless its provenance, tier, cell keys, target values, graph/cache node order, feature registry, and resample identities all match.

## Planned analysis

For all 45 network x target x adjacent-radius comparisons, compute tau(r+1, rep) - tau(r, rep) after aligning replicate IDs. Compare these 200 paired target-bootstrap gains with the ten paired structural-tier seed gains from the current keep-last sweeps. Report means, sample SDs, signs, linear 2.5/97.5 percentiles, covariance, and the variance identity.

The descriptive heuristic is copied unchanged from analyse.py: abs(mean paired gain) > 2 * SD(paired gain). It is reported separately for the target-bootstrap and seed distributions, as retained/lost/new/neither matching structural-tier flags. It is not a p-value, confidence interval, multiplicity adjustment, total uncertainty estimate, or retrospective alteration of an A7/C3 registration.

## CPU and interruption plan

Only one outer refit runs at a time. Cascades are memory-mapped and only one network's arrays/tables are loaded in the execution loop. Before the all-cell pilot, the cache-heavy ca-HepTh/spread_mean/r3 cell is timed with in-forest n_jobs 1, 4, and 8, using the published 120 trees, minimum leaf size 2, and fit seed 0. The selected bounded setting must agree with the historical default OOF construction within recorded prediction and tau tolerances. A two-replicate pilot then uses a controlled stop after one newly processed replicate and resumes from the same provenance. The full 200-replicate run uses a separate output/provenance pair, so a pilot cannot be mistaken for the final corpus.

## Pre-results limits

The bootstrap conditions on cached live-edge samples and fixed forest randomness. It observes the target-resampling channel and paired cancellation, not blocked-CV error, cross-network transfer, or their interaction. Even if target-bootstrap flags differ, the result is a structural-tier follow-up under this stated design; it does not silently rewrite earlier dynamic-tier A7 outputs.

<!-- END docs/phase6_structural_target_noise_design.md -->

---

## <a id="rec-phase6_task1_review"></a>`docs/phase6_task1_review.md`

<!-- BEGIN docs/phase6_task1_review.md sha256=e8095e8b82699289bd09b8a61555fd0dd77593479812ca3edca3bef9597b0f57 date=2026-09-08 author=unsigned (review role) -->
# Phase 6 Task 1 pre-run review

Reviewed 2026-09-08 before the structural-tier pilot. Scope was limited to the
Task 1 design, runner, tests, benchmark artifact, and the proposed buffered-CV
follow-up. This is not the later whole-codebase audit.

## Decision

**The scoped Task 1 runner is green for the controlled two-replicate pilot.**
The no-fit fixture, checkpoint corruption checks, real CSV scalar handling, and
high-precision tau round trip have been repaired and independently rerun. The
benchmark has also completed. The pilot must still prove an actual interrupted
checkpoint resumes, which is an execution gate rather than an unreviewed code
blocker.

## What is sound in the current Task 1 design and runner

- The follow-up is clearly separated from the historical dynamic-tier A7 arm.
  It fixes the five networks, three Monte Carlo targets, radii 0--3, 200
  replicates, fit seed 0, and excludes exact betweenness for the stated reason.
- A resample vector is constructed once per network/replicate and is reused
  across all targets and radii. The runner records a digest that includes its
  dtype and shape. This supplies the required within-replicate pairing for the
  45 adjacent-radius contrasts.
- `preflight` rebuilds the targets from the cached cascades, checks their
  agreement with the cached targets, checks graph/cache node order and original
  IDs, validates the structural registry at every radius, and checks the
  matching structural sweeps contain exactly the expected ten seeds. The tier
  selector uses only `analyse.FULL` and rejects a dynamic-tier feature.
- Inputs include each raw graph, cache, metadata file, sweep and manifest. The
  current runner also hashes its direct semantic dependencies: `analyse.py`,
  `probe_target_noise.py`, `influence/experiment.py`,
  `influence/targets.py`, and `influence/preprocessing.py`. Runtime package
  versions are recorded. These cover the direct code paths for feature-tier
  choice, target reconstruction, OOF fitting, and graph reconstruction.
- OOF prediction is used for every refit. Feature selection is registry-based,
  excludes the dynamic tier, and cannot select an unregistered target column.
  This is adequate for the stated target-resampling experiment; it does not
  turn the transductive graph setting into independent graph-level validation.
- The execution loop holds one network at a time, memory-maps cascades, fixes
  outer workers at one, and allows only 1, 4, or 8 in-forest workers. CSV and
  JSON replacement is atomic.

## Initial blockers and re-review status

1. **No-fit suite — addressed.** The original fixture omitted `n_features`,
   although `validate_sweep` correctly requires it. The repaired fixture now
   supplies it, separately tests its absence, and exercises the incomplete
   ten-seed case. In the `influence` environment, the current command
   `python -m unittest -v verify_structural_target_noise.py` passes all seven
   present tests.

2. **Resume corruption checks — partially addressed, with a new launch
   blocker.** Each completed CSV row now carries
   a SHA-256 over its identity, tau, feature count, configuration hash, and
   resample digest. On resume, the runner recomputes that value and checks
   `n_features` against the preflight structural count for the network/radius.
   The new tests reject changed tau and changed feature count; the suite also
   covers changed provenance, duplicate composite keys, one-file-only
   checkpoint states, and JSON tuple round-tripping. This SHA is an accidental
   corruption/edit detector for a local resumable checkpoint, not an adversary-
   resistant authentication mechanism: a deliberate editor who changes both a
   row and its digest can recompute it. The composite
   `(network, target, radius, rep)` is the row identity and `load_resume`
   requires each component as a CSV column; an explicit missing-`rep`
   regression test would be worthwhile but the code already rejects it.

   A direct write/read/resume check using the realistic tau
   `0.9334276102646076` exposed a further defect: values obtained from pandas
   `itertuples` are NumPy scalars, and `result_row_digest` passes them to
   `json.dumps`, which raised `TypeError: Object of type int64 is not JSON
   serializable`. **This is now addressed:** `result_row_digest` normalizes
   NumPy scalars to native JSON values, and `load_resume` uses
   `float_precision="round_trip"`. The new high-precision-tau test goes through
   `atomic_csv`, `pd.read_csv`, and `load_resume`; the full current no-fit suite
   passes 8/8 in the `influence` environment.

3. **Benchmark provenance — addressed with a documented serialization-only
   source boundary.** The old artifact is superseded by
   `results/structural_target_noise_pilot_benchmark_rerun.json`, whose
   provenance hashes all direct semantic inputs and records runner SHA
   `3c83c9a8...`. It reports ca-HepTh/spread_mean/r3 timings of 151.73 s
   (`n_jobs=1`), 44.05 s (4), and 24.30 s (8); tau and the recorded comparison
   gaps are identical at the displayed precision. The final reviewed runner is
   SHA `eb12c1de...` because it adds only CSV digest scalar normalization and
   round-trip parsing after the benchmark. That delta does not touch model
   construction, OOF splitting, data loading, or scheduling. Consequently the
   benchmark is valid evidence for the selected bounded scheduling, while the
   pilot’s existing one-cell equivalence check and actual interruption/resume
   proof must bind the final source hash. Do not describe the artifact as a new
   timing measurement of `eb12c1de...`.

## Benchmark evidence, pending refresh

The refreshed representative ca-HepTh / spread_mean / r=3 measurement supports
`n_jobs=8`: 24.30 s versus 44.05 s (4) and 151.73 s (1), with no observed tau
gap and zero displayed prediction gap against 1. The available-memory snapshots
are not peak-RSS measurements, but one outer worker, sequential network loading,
and memory mapping remain a reasonable safe-CPU policy for this workstation.
The pilot must still record the controlled stop/resume proof before the
200-replicate corpus.

## Required analysis guard after the corpus exists

The design correctly requires replicate-ID alignment before differencing,
paired seed comparisons from the matching structural sweep, covariance, and
the variance identity. The final analyzer must refuse an incomplete or
duplicate 200-replicate cell rather than silently computing a contrast on an
intersection. It should preserve the declared descriptive `abs(mean) > 2 SD`
rule as a heuristic only, never re-label it as a p-value or total uncertainty.

## Buffered-CV design critique for the next lane

The proposal properly labels itself a follow-up, preserves the dynamic C6
record, uses structural features, keeps test regions graph-only, defines
size-matched controls, reports failed folds, and states the remaining
transductive limitation. It needs these refinements before implementation:

1. **Specify the split generator exactly.** "Seeded BFS ordering" needs a
   deterministic root-selection rule, a deterministic neighbour order, seed
   derivation, and a recorded membership hash. Otherwise different adjacency
   iteration orders can change the five regions. Record every test and train
   node ID, not only fold counts.

2. **Do not interpret the first non-significant correlogram lag as evidence of
   independence.** Residual dependence can be non-monotone and power varies by
   cell. At minimum, report all lags 1--7, flag later significant lags after
   the selected cutoff, and label the measured buffer as a diagnostic-derived
   sensitivity. A conservative rule based on the furthest observed material
   dependence (with an explicit effect threshold) is more defensible than the
   first failure to reject alone.

3. **State the target-dependence limit separately.** Buffers remove nearby
   *training labels*, but train and test Monte Carlo targets still share the
   same 4,000 live-edge samples and graph-wide target construction. Thus this
   is a local-label-separation robustness check, not an independence-valid CV
   estimate. The report should say this alongside the existing transductive
   feature caveat.

4. **Make control sampling reproducible and complete.** Define the control RNG
   from network/target/radius/seed/fold/arm, sample only the unbuffered
   non-test candidates, record selected IDs, and assert its training count is
   exactly the corresponding buffered count. A control deliberately may retain
   near-test nodes; that is what identifies separation conditional on size.

5. **Preflight cost and feasibility before fits.** The nominal design can reach
   five networks × four targets × four radii × ten seeds × five folds × up to
   five arms: about 20,000 forest fits. Run graph/split/buffer feasibility first,
   then one timed representative cell to estimate full cost. Freeze an explicit
   inner `n_jobs`, outer-worker count, memory policy, and a rule for cells whose
   measured buffer is unresolved or leaves fewer than 30 training rows. Do not
   calculate or compare a partial-vector tau as though it covered all nodes.

6. **Keep comparisons within their evaluands.** Region holdout and random-fold
   OOF evaluate different test geometries. Report their paired differences as
   descriptive robustness results, and use the size-matched arm only to
   separate retained-label count from spatial separation for the same region.
   Do not treat ten BFS seeds as independent networks or convert the existing
   star heuristic into formal inference.

## Handoff

The Task 1 blockers were sent to the structural-run lane and root during this
review. The scoped re-review is green for the two-replicate interruption/resume
pilot. The pilot is the remaining required operational proof before the full
200-replicate corpus.

<!-- END docs/phase6_task1_review.md -->

---

## <a id="rec-phase6_buffered_cv_review"></a>`docs/phase6_buffered_cv_review.md`

<!-- BEGIN docs/phase6_buffered_cv_review.md sha256=57384ab6598533ec4d7a125870e454aaa64f7ebaec24db1d774f3be20c51ed45 date=2026-09-09 author=unsigned (review role) -->
# Phase 6 buffered-CV harness scoped review

Reviewed 2026-09-09 against `phase6_buffered_cv_design.md`,
`phase6_buffered_implementation_brief.md`, and
`phase6_buffered_cv_implementation_report.md`. This was a source and fixture
review only: no corpus Moran run, preflight, pilot, or forest fitting was
started.

## Reviewed source identities

- `probe_buffered_cv.py`: `677ABF6B0478D6223893BBC33A805D47AE2430E426C461145BDCB0380925EBA9`
- `analyse_structural_moran_correlogram.py`: `DAD7BFDA4BA8D610BEAA7474B897EF6BAE4115DC4BEC40480483DF8D1000ACA4`
- `analyse_buffered_cv.py`: `44D7286F7AB645BDE33867A707B099C0C9B8430403C1B4D83C5DE93D669984BF`
- `verify_buffered_cv.py`: `9E14B36D2F40E7CD0C69A834F08D025027331F7973BA1384F35D6C2B3FDE920A`
## Verification completed

`C:\Users\Rachit\miniconda3\envs\influence\python.exe -m unittest -v
verify_buffered_cv.py` passed all 13 fixtures in 2.718 seconds. The fixtures
give useful coverage for seeded BFS, path/cycle distance masks, infeasible
buffer semantics, matched controls and b=1 aliases, target transforms,
basic checkpoint interruption, assignment-key completeness, and paired
analysis. The statistical calculation itself is correctly within-seed,
descriptive only, and suppresses a pair unless both ten-seed arms are complete
(`analyse_buffered_cv.py:40-73`).

## Findings

### P1 — The required benchmark/pilot launch gate is absent

`probe_buffered_cv.py:775-790` exposes only `--moran`, `--preflight-only`,
`--rf-jobs`, and `--stop-after-canonical-fits`. It has no `--benchmark-only`
mode, does not run the required `rf_jobs` 1/4/8 measurements, and never writes
`results/phase6_buffered_cv_pilot.json` with timing, memory snapshots, and the
preflight-based extrapolation. The execution brief makes that artifact a
required gate before choosing the worker count and launching the controlled
stop/resume or full sweep.

Independent reproduction, with no graph work or fits: `python
probe_buffered_cv.py --benchmark-only --rf-jobs 1` exits 2 with `unrecognized
arguments: --benchmark-only`; `-h` lists no such mode.

Add a benchmark-only path that requires an already validated preflight, runs a
representative bounded pilot at each of 1, 4, and 8 jobs (one at a time),
records elapsed time and process-memory snapshots, derives the full-run
estimate from `canonical_fit_count`, and atomically writes the pilot artifact.
The normal execution path should require the recorded chosen job count and
pilot/provenance identity before it writes a checkpoint.

### P1 — Structural-Moran and resume provenance are not validated or bound strongly enough

The runner hashes whatever CSV is supplied at `probe_buffered_cv.py:402-409`,
but `_measured_buffer_map` at lines 369-382 checks only the derived
network/target/radius key set. It neither reads the paired structural-Moran
provenance JSON nor requires `phase6-structural-moran-v1`, the structural tier,
the expected source OOF paths/hashes, or the CSV's recorded output digest.
Thus a historical dynamic-tier C6-shaped CSV can be accepted if it has the
expected dimensions, contrary to the design's explicit source boundary.

The same weakness exists on resume. `load_checkpoint` compares only
`configuration_sha256` (`probe_buffered_cv.py:331-355`); `_load_preflight`
checks that configuration and assignment-file hashes agree, but does not
recompute the recorded raw/cache/source hashes (`489-506`).
`assignment_sha256` is created in `plan_row` (`295-304`) but never validated in
`_validate_resumed_rows` (`561-574`). This does not meet the required
input/source/provenance equivalence and valid-row-digest checks.

Independent reproductions, both using temporary files and no real fit:

- A synthetic 80-cell, 10-seed, rank-only CSV with no `protocol`, `tier`,
  `source_oof_path`, or provenance file was accepted by `_measured_buffer_map`
  as 80 resolved buffer decisions.
- A checkpoint written with `input_sha256={'cache':'old'}` was accepted by
  `load_checkpoint` when read with the same configuration hash but
  `input_sha256={'cache':'changed'}`.
- The one-cell fixture setup still completed its mocked first fit after every
  preflight row's `assignment_sha256` was replaced with
  `corrupted-but-unchecked`.

Require the structural-Moran sidecar and verify its protocol, complete
configuration, CSV output hash, expected full structural source paths/key
space, and OOF input hashes before preflight. Bind a digest of the complete
preflight/provenance input identity and expected logical/canonical key sets to
each checkpoint manifest; recompute current source hashes before resume. For
each restored row, verify an immutable preflight-row digest and the exact ID
array digests. Add fixtures for dynamic-C6 rejection, changed input-source
hash rejection, and altered-row-digest rejection.

### P1 — Final materialization breaks the stated bounded-memory contract

Although assignment archives and checkpoints are per cell, `_materialize_final`
loads every cell and retains its full `test_ids`, `train_ids`, and
`excluded_ids` Python lists in the process-wide `folds` list
(`probe_buffered_cv.py:699-714`). It does this for all 800 cells before writing
`phase6_buffered_cv_folds.csv` at lines 736-743. The largest graph has 8,638
nodes; expanded JSON lists across five logical arms, five folds, 160 cells per
network, and all networks can exceed the available ~1.1 GiB physical headroom.
This is precisely the aggregate-ID accumulation the per-cell archive amendment
was intended to avoid.

The failure is structural and independent of corpus fitting: the loop extends
`folds` before releasing each cell state, and `atomic_csv` constructs one
DataFrame from the entire aggregate. The final OOF archives are correctly
network-scoped, but the fold CSV is not.

Keep IDs solely in their immutable per-cell archive. Emit a compact fold record
with the archive path/hash and per-field ID digests instead of materialized ID
lists, and stream it to a temporary CSV (or bounded per-network shards followed
by a streamed merge). Materialize and release one network's OOF vectors and
fold rows before proceeding to the next. Add a fixture that asserts the final
fold rows do not contain ID arrays and a resource test/instrumented assertion
that aggregation never retains more than one network's cell states.

### P2 — The analyzer can pair cells from different configurations

The final cell rows contain `configuration_sha256` and `row_sha256`
(`probe_buffered_cv.py:688-695`), but `analyse_buffered_cv.validate_cells`
requires neither and validates no sidecar manifest (`analyse_buffered_cv.py:25-37`).
Any complete, unique set of static logical keys is accepted, so a CSV assembled
from different preflight/provenance identities can produce apparently valid
paired contrasts. This violates the design requirement that completed rows
cannot cross configurations.

Independent reproduction is direct: the analyzer's required-column set is
only `network,target,radius,seed,logical_arm,status,kendall_tau`; adding a
different `configuration_sha256` to one otherwise valid complete row leaves
validation unchanged and the contrast is scored.

Require one configuration/provenance digest across all cells, validate each
row digest, and verify the cells CSV/OOF manifest against the recorded expected
logical and canonical key sets before descriptive pairing. Add a mixed-config
fixture.

### P2 — No separate readout against the reported random-CV corpus is implemented

The design requires the graph-region results to be compared separately with the
existing reported random-fold results while explicitly retaining the different
split geometry (`phase6_buffered_cv_design.md:72-75`).
`analyse_buffered_cv.py` accepts only the new buffered cells CSV and defines
six contrasts exclusively among its five new arms (`16-22`, `76-85`). It never
loads the reported `analyse.load(network)` corpus, its structural-tier rows, or
its reported log1p-betweenness replacement. No other reviewed file produces
that separate comparison.

This is reproducible by the public command interface: `python
analyse_buffered_cv.py -h` exposes only `--cells` and `--out`; neither is an
existing random-CV input. The current output has no random-CV metric, source,
or geometry label.

Add a separately labelled baseline readout using `analyse.load(network)` and
`analyse.FULL`, with its reported betweenness splice, grouped by the same
network/target/radius keys. It must be descriptive and explicitly mark the
random-fold versus BFS-region geometry, rather than treat the difference as a
paired sample-size effect or add a new significance claim. Cover source
selection and the geometry label in a fixture.
## Disposition

The split, control, alias, incomplete-arm, and paired-descriptive core is a
sound start, but the five findings are launch blockers. Resolve them and extend
the focused fixtures before running structural Moran, corpus preflight, the
worker benchmark, or any buffered fits.



## Fix-round re-review — 2026-09-09

The scoped fixture suite passed: `C:\Users\Rachit\miniconda3\envs\influence\python.exe -m unittest -v verify_buffered_cv.py` ran 21 tests in 3.050 seconds. The revised harness resolves the benchmark CLI/pilot artifact, input/preflight/checkpoint identity checks, compact streamed fold export, cells/OOF manifest validation with CSV round-trip handling, and separately labelled reported random-CV reference. The old four findings are therefore cleared in this reviewed revision, subject to the new producer blockers below.

### P1 — Structural-Moran producer cannot execute its claimed BLAS-capped path

At this reviewed revision, `analyse_structural_moran_correlogram.py:147` calls `threadpool_limits(limits=BLAS_THREADS, user_api="blas")` and line 208 records `BLAS_THREADS`, but neither symbol is imported or defined anywhere in that file. The 21 constructed fixtures and `py_compile` do not exercise `_rows_for_network`, so they do not detect this runtime `NameError`. This blocks the first required structural-Moran launch.

Add `from threadpoolctl import threadpool_limits` and a module-level `BLAS_THREADS = 4`, then add a tiny mocked producer-path fixture which calls `_rows_for_network` through the dense-Moran boundary and asserts the configured cap is recorded. Re-review must execute that path, not only CLI help or pure read-off helpers.

### P1 — Undefined Moran statistics are incorrectly converted into a resolved buffer

`analyse_structural_moran_correlogram.py:156-165` sets `p_perm` to `NaN` when no finite permutation statistics exist, but still calls the lag `testable` whenever `n_used >= 30`; `sig` then becomes `False`. `first_nonsig` (`62-68`) treats that as a valid first non-significant lag. A ten-seed constructed fixture with `testable=True`, `p_perm=NaN`, and `sig=False` returned `status='resolved'` and `measured_buffer=1` for every seed. A zero-variance rank residual or non-finite source can therefore establish a measured buffer without a test statistic.

Require finite observed I and at least one finite permutation statistic before marking a lag testable or eligible for `first_nonsig`; otherwise preserve the explicit unresolved status. Validate finite target and OOF-prediction values before rank residual construction. Add this exact NaN/constant-residual fixture.

### P1 — The structural-Moran artifact is still not bound to the producer source revision

The sidecar emitted at `analyse_structural_moran_correlogram.py:206-211` records configuration, data/OOF hashes, output hash, and runtime versions, but no hashes for the producer or the imported Moran/ranking implementation. `probe_buffered_cv.validate_structural_moran` (`456-516`) validates only those recorded data identities; later preflight hashes the *current* producer script, which cannot establish that an existing CSV/sidecar was generated under that same source revision. A stale artifact made by older Moran code with unchanged data and configuration can therefore pass.

Independent reproduction used a temporary complete 5,600-row structural CSV and sidecar containing every required data/OOF hash field but no producer-source identity. With file-hash reads mocked to the declared value, `validate_structural_moran` accepted it (`accepted_sidecar_without_producer_source_identity=5600`).

Write a canonical source-hash map into the structural sidecar for this producer and its semantically imported Moran/ranking dependencies, then require equality with the current files in `validate_structural_moran`. Also require the full fixed Moran configuration, including permutation count and RNG seed if they remain protocol parameters. Add a stale-source-sidecar rejection fixture.

### P1 — The producer does not verify node ordering or finite OOF inputs before residual ranking

`_rows_for_network` reads `cache_targets_<network>.csv` and ranks its target column (`99-125`) without verifying `node == arange(n)`, original-ID alignment, or finite targets/predictions. It only validates OOF shape. A reordered target cache with the correct length silently pairs labels with the wrong OOF nodes; a non-finite OOF/target contributes to the undefined-statistic path above. Buffered preflight's later cache-alignment check cannot repair an already produced Moran cutoff.

Use the same LCC/cache identity checks in the producer before residual construction, and reject non-finite target/OOF vectors. Add tiny reordered-node and non-finite-vector producer fixtures.

### Source identities at the time these findings were observed

- `probe_buffered_cv.py`: `A62AA884D939BA0DF43F09EAC30920B522651A07E593F807D00C5280B1DB3A43`
- `analyse_structural_moran_correlogram.py`: `B4D2DE5A1887D59457D24338479DC015BF90089CCA995ECB91E00B323C6A82EE`
- `analyse_buffered_cv.py`: `B441EC1807B33E457938B4E5BCE44D2F1BB99BAB5570265A24BFCD96171AE57B`
- `verify_buffered_cv.py`: `ED1298E94A30EAF398EBD5D2DE2DECEA5103750A5A7A995EB1631D7A8C2C9BF6`

The source files changed concurrently after these observations. These hashes identify the reviewed revision; they are not a disposition of later edits. The next review requires a frozen source set and fresh hashes.
## Re-review disposition

Do not launch structural Moran, preflight, pilot, or fits from the reviewed revision. The buffered runner/analyzer fixes are materially improved and their 21 fixtures pass, but the four producer-path P1 findings block the prerequisite artifact. After a source freeze, rerun this scoped review with the tiny real producer execution and the added undefined/alignment/source-binding fixtures.


## Frozen fix-round-2 re-review — 2026-09-10

The files were declared frozen when this pass began. `C:\Users\Rachit\miniconda3\envs\influence\python.exe -m unittest -v verify_buffered_cv.py` passed all 24 fixtures in 4.492 seconds. The tiny CLI producer fixture executed the actual structural-Moran producer through its dense calculation and wrote 1,120 rows plus a sidecar, using only its temporary constructed graph and mocked cache files.

### Cleared producer findings

The four previously recorded producer P1 findings are resolved in this frozen revision:

- `threadpoolctl.threadpool_limits` is imported, `BLAS_THREADS = 4` is defined, the cap scopes only the dense Moran calculation, and its value is recorded in the sidecar.
- Non-finite observed statistics or null tail areas make a lag untestable. The former undefined-statistic reproduction now returns `unresolved_no_testable_nonsig` with no measured buffer.
- The producer verifies target node order, feature node/original-ID order, OOF shape, and finite OOF values before ranking. The tiny CLI fixture exercises alignment and non-finite OOF rejection.
- The sidecar records producer-source hashes and the buffered consumer compares them to the current semantic producer sources. The altered-source-binding fixture passes.

The new pilot numerical-equivalence gate also passes review. It fits the same canonical fold at jobs 1/4/8, records finite predictions, scale-aware absolute/relative prediction deltas, and Kendall-tau deltas against jobs=1. Both selection and execution require all three settings to satisfy the declared tolerances; the fixture rejects both prediction and tau drift without any corpus fit.

`results/phase6_buffered_controller.ps1` parses successfully. Its sequence matches the runner: structural Moran, paired zero-fit preflight, 1/4/8 pilot, pilot-selected one-fit interruption, identical-job resume, then analysis. It validates the parsed job is in `{1,4,8}`; the runner independently validates the pilot digest, selected setting, equivalence rows, and preflight identity before any checkpoint. The controller relies on the producer's default `--seed 0` rather than spelling it out.

### P1 — Consumer accepts structural-Moran sidecars with non-protocol permutation configuration

`probe_buffered_cv.validate_structural_moran` validates tier, key space, BLAS cap, and shared-null disclosure (`477-544`), but its expected configuration at lines `492-498` omits `perms`, `batch`, and `random_seed`. Those values are emitted by the producer and alter the empirical permutation tail areas on which the measured buffer is based. The required launch contract is `--perms 199 --batch 512 --seed 0`; a same-data, same-source sidecar from another permutation count or RNG seed can currently pass.

Independent reproduction used a complete temporary 5,600-row structural CSV and a valid current producer-source map, while file hashes were mocked to their declared values. `validate_structural_moran` accepted a sidecar declaring `perms=1`, `batch=1`, and `random_seed=99` (`accepted_nonprotocol_perms_batch_seed=5600 1 1 99`).

Require `perms: 199`, `batch: 512`, and `random_seed: 0` in the consumer's expected configuration, and add the exact altered-configuration rejection fixture. The controller should pass `--seed 0` explicitly for audit clarity.

### Source identities at the time this frozen review began

- `probe_buffered_cv.py`: `57B4AFBB5C33A0714931924995C18EB52BDA97980918CD1FE6148C0F71442B4D`
- `analyse_structural_moran_correlogram.py`: `8F8D0B7AFB252FCFDBAAE2BB93ED2EFBB7E713E32A72D1BACABDF1D64FC5066E`
- `analyse_buffered_cv.py`: `755D8F1538B320F2C82B1EE58572B42696FAA63EB600C3963C3770154049F147`
- `verify_buffered_cv.py`: `48B6CD5D365A87BE743F10E261955F2625A64A4F0355880FE64297C7ACC66AF4`

The producer/runner files changed after the complete-configuration finding was routed. These hashes identify the reviewed source set; the next narrow re-review must hash and inspect the final three-field fix.
## Disposition

The buffered harness, producer validity repairs, benchmark equivalence gate, and controller sequencing are otherwise ready. Do not launch the controller or any corpus step until the remaining complete-configuration P1 is fixed and its focused regression passes; only that three-field configuration check then needs re-review.


## Final narrow configuration re-review — 2026-09-10

The final routed P1 is cleared. `probe_buffered_cv.validate_structural_moran` now requires `perms: 199`, `batch: 512`, and `random_seed: 0` alongside the previously bound structural configuration (`probe_buffered_cv.py:492-499`). `test_structural_moran_consumer_rejects_non_authoritative_permutation_config` independently alters each field and passes by observing rejection.

Validation completed on the refrozen source set:

- `python -m py_compile probe_buffered_cv.py analyse_structural_moran_correlogram.py analyse_buffered_cv.py verify_buffered_cv.py` passed.
- `python -m unittest -v verify_buffered_cv.py` passed all 25 tests in 6.615 seconds, including the temporary tiny producer CLI execution.

The controller sequence remains consistent with this contract: it supplies `--perms 199 --batch 512`; the producer's default seed is 0 and the consumer rejects any resulting sidecar that records another seed. Supplying `--seed 0` explicitly would improve audit readability but is not needed for correctness under the bound consumer guard.

### Final frozen source identities

- `probe_buffered_cv.py`: `B32AA481BC1D2F350C2403C39B2E4EE47CE5345F9BABCAA7C602CADAE628CC1A`
- `analyse_structural_moran_correlogram.py`: `8F8D0B7AFB252FCFDBAAE2BB93ED2EFBB7E713E32A72D1BACABDF1D64FC5066E`
- `analyse_buffered_cv.py`: `755D8F1538B320F2C82B1EE58572B42696FAA63EB600C3963C3770154049F147`
- `verify_buffered_cv.py`: `73D74DB28B8A641020597FB3040408F03D566B4166CF773EF81FF4E271B2A422`

## Final disposition

Approved for the finite controller sequence. All scoped buffered-CV and structural-Moran launch blockers recorded in this review are resolved on the listed frozen source set.

<!-- END docs/phase6_buffered_cv_review.md -->

---

## <a id="rec-phase6_structural_task_report"></a>`docs/phase6_structural_task_report.md`

<!-- BEGIN docs/phase6_structural_task_report.md sha256=4d07013d184af891fdc8d744fecfe24a79fc193e3100405ecf05f24707905172 date=2026-09-09 author=unsigned; results section by Claude Opus 5 (2026-09-10) -->
# Phase 6 Task 1: structural-tier paired target uncertainty

## Status

**Pilot complete; full run resumed 2026-09-09.** All 120 two-replicate pilot cells
completed after the controlled 12-cell interruption. The original controller stopped
after 15/12,000 full-run cells with no recorded Python error. Controller PID 26376
revalidated the complete pilot and accepted those 15 checkpoints before resuming.
Current logs are `results/phase6_structural_controller_resume_20260909.log` and
`.err.log`. Check live processes before restarting to prevent concurrent writers.
This report preserves historical A7 dynamic-tier results and writes separate paths.

## Deliverables

- Runner: probe_structural_target_noise_refit.py
- Tests: verify_structural_target_noise.py
- Pre-results design: docs/phase6_structural_target_noise_design.md
- Pilot output/provenance: results/results_target_noise_refit_structural_pilot.csv and results/provenance_target_noise_refit_structural_pilot.json
- Full output/provenance: results/results_target_noise_refit_structural.csv and results/provenance_target_noise_refit_structural.json
- Final paired comparison: pending the complete 200-replicate corpus.

## Resource and launch policy

At launch preparation, Windows reported roughly 2.14 GiB free physical memory. The runner therefore memory-maps cascades, discards preflight tables per network, loads one network at a time during refitting, and permits exactly one outer worker. The current-code representative ca-HepTh/spread_mean/r3 benchmark is recorded separately in `results/structural_target_noise_pilot_benchmark_rerun.json` so the earlier timing record remains intact: n_jobs 1/4/8 took 151.7/44.0/24.3 seconds, respectively, with identical Kendall tau and at most 3.553e-15 OOF-prediction difference from n_jobs 1. The run selects bounded in-forest n_jobs=8. The review-era changes only strengthen checkpoint provenance and CSV resume validation; they do not alter model fitting or job scheduling. The checkpointed runner also performs its one-cell bounded/default OOF equivalence before writing pilot results.

## Commands

Use the existing environment only:

```powershell
conda run -n influence python -m unittest -v verify_structural_target_noise.py
# representative cell speed/memory comparison; no result CSV
conda run -n influence python probe_structural_target_noise_refit.py --benchmark-only
# controlled interruption/resume pilot (substitute measured setting, e.g. 4)
conda run -n influence python probe_structural_target_noise_refit.py --reps 2 --rf-jobs 8 --stop-after-reps 1 --out results/results_target_noise_refit_structural_pilot.csv --provenance results/provenance_target_noise_refit_structural_pilot.json
conda run -n influence python probe_structural_target_noise_refit.py --reps 2 --rf-jobs 8 --out results/results_target_noise_refit_structural_pilot.csv --provenance results/provenance_target_noise_refit_structural_pilot.json
# full run, launched only after the pilot passes
conda run -n influence python probe_structural_target_noise_refit.py --reps 200 --rf-jobs 8
```

## Pre-launch verification

- `python -m unittest -v verify_structural_target_noise.py verify_structural_target_noise_analysis.py`: 11 checks passed. They cover structural feature selection, exact ten-seed sweep scope, two-file checkpoint presence, duplicate and provenance rejection, tuple-safe JSON resume, high-precision tau round-trip, feature-count binding, accidental row-corruption detection, and structural paired-analysis corpus identity.
- The paired analyzer is `analyse_structural_target_noise.py`. After the complete corpus it writes `results/results_paired_target_noise_structural.csv` and `results/RESULTS_paired_target_noise_structural.txt`, with all 45 adjacent-radius contrasts, paired SDs, covariance, variance identity, observed linear percentiles, signs, and retained/lost/new/neither descriptive flags.

## Limits

Results are pending. The intended 45 contrasts concern the richest structural tier and matching ten-seed structural sweeps; they are not a total uncertainty analysis, p-value family, or a change to registered C3/A7 findings. No GPU, PyTorch, external checkpoint, or numerical-library installation is used.

---

## Results, 2026-09-10 (Claude Opus 5)

> Added 2026-09-10 by Claude Opus 5 (Lane 1). The section above says "Results are pending"; they
> are no longer pending. That sentence is retained as the record of what was planned, and this
> section reports what the completed run measured.

**Corpus.** `results/results_target_noise_refit_structural.csv`, exactly 12,000 cells
(5 networks x 3 Monte-Carlo targets x 4 radii x 200 replicates), all `tau_refit` finite, one
distinct `configuration_sha256` across both resumes, and all 42 `input_sha256` entries in
`results/provenance_target_noise_refit_structural.json` recomputed against the current files
with 0 mismatches. That last check matters because the stage-1 source changed on 2026-09-09,
mid-run; it binds, so no incompatible checkpoint was accepted.

`verify_structural_target_noise.py` passes **8/8** and
`verify_structural_target_noise_analysis.py` **3/3**. Both are fixture-based, so they establish
the machinery's semantics, not the corpus — the corpus evidence is the paragraph above.

### The 45 predeclared adjacent-radius contrasts

| Outcome | Count |
| --- | ---: |
| `retained` (starred under both resamplings) | **38** |
| `lost` (starred under seed-only, not under target noise) | **3** |
| `neither` | **4** |
| **`new`** (starred only under target noise) | **0** |

The three lost flags, all at radius 1 -> 2:

| Network | Target | Mean gain | Paired SD |
| --- | --- | ---: | ---: |
| email-Eu-core | spread_resid | −0.005752 | 0.021810 |
| facebook_combined | spread_cv | +0.002007 | 0.001674 |
| facebook_combined | spread_resid | +0.004565 | 0.002437 |

### Comparison with A7's dynamic tier

The structural tier reproduces A7's saved dynamic-tier analysis **exactly**: not merely the same
counts (38 / 3 / 4 / 0) but the **same three contrasts**, on the same networks, targets and
radius step. Verified by direct comparison of `results/results_paired_target_noise.csv` against
`results/results_paired_target_noise_structural.csv`.

**This agreement is weaker evidence than it looks, and is qualified accordingly.** The two
analyses **share their target-noise resamples by design** — that identity is deterministic and
is asserted by `verify_structural_target_noise.py::
test_resample_identity_is_deterministic_and_shared_by_design`. So the two tiers see the *same*
perturbed targets, and this is **not** an independent replication. What it does show is that the
fragility of those three flags is driven by the target noise itself rather than by which feature
tier is used to fit them — which is the question the structural follow-up was posed to answer.

**No headline structural-tier star failed that A7 retained**, and no flag was gained. Had one
failed, that would have been the finding and would be reported here as such.

### The quantitative point: seed-only resampling understates uncertainty

`target_over_seed_sd` is the ratio of the target-noise paired SD to the seed-only paired SD.

| Statistic | Value |
| --- | ---: |
| Median | **1.700** |
| Fraction > 1 | **91.1%** (41 of 45) |
| Range | 0.700 – 3.984 |

In roughly nine contrasts out of ten the target-noise resampling produces a **larger** paired SD
than resampling seeds alone, by a median factor of 1.7. Ten-seed intervals are therefore
optimistic as a description of total uncertainty in this design. That is the substantive result,
and it is the reason three flags do not survive.

### Limits

Descriptive **predeclared** paired-SD heuristics throughout: no p-values, no null distribution
and no multiplicity correction across 45 contrasts, so individual flags carry much less weight
than the aggregate pattern. This is not a total uncertainty analysis — it varies target noise and
seeds, not the graph sample, the cascade model, or the estimator. **No registered C3 or A7
outcome changes.** The sklearn config-propagation warnings
(`docs/phase6_parallel_warning_diagnosis.md`) remain an open limitation and are not asserted to
be harmless.

<!-- END docs/phase6_structural_task_report.md -->

---

## <a id="rec-phase6_parallel_warning_diagnosis"></a>`docs/phase6_parallel_warning_diagnosis.md`

<!-- BEGIN docs/phase6_parallel_warning_diagnosis.md sha256=3e291c32fa6b6718df609b5ddecb78599144cdcbf1daba39c6d94231264930d9 date=2026-09-09 author=unsigned -->
# Phase 6 structural run: scikit-learn parallel warning diagnosis

**Observation date:** 2026-09-09 (India Standard Time).  This is a bounded,
read-only diagnosis of the active structural refit.  It does not change the
runner, environment, process, caches, or logging.

## Measured evidence

At the observation snapshot, the active process was:

```text
PID:      14396
Command:  C:\\Users\\Rachit\\miniconda3\\envs\\influence\\python.exe
          probe_structural_target_noise_refit.py --reps 200 --rf-jobs 8
Started:  2026-09-09 00:08:05 IST
```

`results/phase6_structural_controller_resume_20260909.err.log` then measured
18,431,182 bytes and contained exactly 57,778 lines matching
`sklearn/utils/parallel.py:144`.  Each warning occupies two lines in this
log, so that is 28,889 warning events.  Searches found zero `Traceback` and
zero `Error` lines.  The results log had reached cell 2,611 of 12,000; the
process was responsive.  C: had 532,122,714,112 bytes free.

The repeated message is:

```text
sklearn.utils.parallel.delayed should be used with
sklearn.utils.parallel.Parallel to make it possible to propagate the
scikit-learn configuration of the current thread to the joblib workers.
```

The frozen provenance records the installed runtime as scikit-learn 1.9.0,
NumPy 2.5.2, pandas 3.0.5, SciPy 1.18.0, and Python 3.12.14.  The installed
joblib version is 1.5.3.

Installed `sklearn.utils.parallel._FuncWrapper.__call__` emits this message
when either its propagated scikit-learn configuration or propagated warning
filters are empty.  Therefore the message is evidence of failed configuration
or warning-filter propagation for that invocation.  It is not an exception
and does not itself state that an estimator parameter changed.

## Frozen-source evidence

The active runner calls an explicit, bounded random forest:

```python
RandomForestRegressor(
    n_estimators=120, n_jobs=rf_jobs, random_state=seed,
    min_samples_leaf=2,
)
```

The launcher supplies `--rf-jobs 8`; it sets no `SKLEARN_*` environment
variables.  The runner and its frozen dependencies contain no direct joblib,
`Parallel`, `delayed`, `set_config`, or `config_context` use.  The installed
`sklearn.ensemble._forest` imports `Parallel` and `delayed` from
`sklearn.utils.parallel`, and identity checks confirmed both are the
scikit-learn implementations rather than the joblib implementations.

The runner performed and saved a one-cell default-versus-bounded OOF check
before the full refits:

```text
max_abs_prediction_gap = 7.105427357601002e-15  (limit 1e-10)
abs_tau_gap            = 0.0                    (limit 1e-6)
```

This verifies the selected `n_jobs=8` factory agrees with the established
default construction for that preflight cell.  It does not independently
prove every later cell had no configuration-propagation issue.

## In-memory probes

All probes ran with the pinned interpreter and used synthetic arrays only;
they read no experiment data and wrote no files.

```powershell
& 'C:/Users/Rachit/miniconda3/envs/influence/python.exe' -c "..."
```

Within that interpreter:

| Probe | Result |
|---|---:|
| `sklearn.utils.parallel.Parallel` paired with its `delayed` | 0 warnings |
| Deliberate `joblib.Parallel` paired with `sklearn.utils.parallel.delayed` | 2 warnings, exactly the logged message |
| Matching sklearn pair after `warnings.resetwarnings()` | 1 exact warning despite a nonempty propagated worker configuration |
| One-tree `RandomForestRegressor(n_jobs=2)` | 0 warnings |
| Five sequential synthetic `RandomForestRegressor(n_estimators=120, n_jobs=8)` fits and predictions | 0 warnings |

The current default sklearn configuration in a fresh pinned-interpreter
process was nonempty, including `assume_finite=False`,
`working_memory=1024`, `transform_output='default'`,
`enable_metadata_routing=False`, and `skip_parameter_validation=False`.

The third probe isolates the two sides of sklearn's warning guard.  In a fresh
process, `warnings.resetwarnings()` reduced the caller's warning-filter list
to zero.  A matching `sklearn.utils.parallel.Parallel` plus its own `delayed`
then emitted the exact warning once.  The worker nevertheless received the
complete nonempty default sklearn configuration shown above, while its
warning-filter list was empty.  Thus empty warning filters alone are enough to
trigger the message.

## Interpretation and limitation

**Evidence supports:** a runtime parallel invocation in the active process
entered sklearn's delayed wrapper with either empty configuration metadata or
empty warning-filter metadata.  The warning alone cannot distinguish those
cases: the controlled matching-pair probe proves that empty warning filters
can produce it while configuration propagation succeeds.  The warning does
not reproduce from the frozen RandomForest path in isolation, and the forest's
explicit hyperparameters have not been shown to change.

**Not established:** the exact live invocation that emits the warnings.
The log carries no Python stack trace, and intrusive tracing or modification of
the active frozen process was intentionally not performed.  It remains
possible that the warning-filter half of sklearn's condition, rather than the
estimator configuration half, is what is empty; the controlled probe makes
that possibility concrete.  No live worker configuration was captured.

**Operational conclusion:** the warning alone is insufficient to stop or
invalidate the active run.  Preserve the run and its logs unchanged.  The
final audit should retain this note, check process completion and CSV/provenance
integrity, and treat the unknown warning callsite as an explicit limitation.

<!-- END docs/phase6_parallel_warning_diagnosis.md -->

---

## <a id="rec-phase6_buffered_cv_execution_status"></a>`docs/phase6_buffered_cv_execution_status.md`

<!-- BEGIN docs/phase6_buffered_cv_execution_status.md sha256=0306d2cd8159b644bc8114c8f882cf34749e5b778c9ca28dd68b6b662f1c2faa date=2026-09-10 author=Astra (GPT-6), per its 2026-09-10 addendum by Claude Opus 5 -->
# Phase 6 buffered-CV execution status

Observed 2026-09-10 (Asia/Kolkata). This record is evidence from completed artifacts and the active controller state. It makes no new statistical claim and does not replace the historical random-CV results.

## Structural Moran prerequisite: complete and authenticated

`results/phase6_structural_moran_correlogram.csv` contains the exact expected 5,600 rows: 5 networks × 4 targets × 4 radii × 10 fit seeds × 7 lags. All rows are `tier=node+edge+subgraph` and `residual=rank`; all Moran-I and permutation-tail values are finite. The paired provenance sidecar records the required fixed settings: 199 permutations, batch 512, random seed 0, local BLAS cap 4, and the shared seed-0 null-reference description.

The following artifact checks passed against the current files:

- CSV SHA-256 equals the sidecar `output_sha256`.
- The sidecar's producer-source hash map equals the current producer-source hashes.
- `probe_buffered_cv.validate_structural_moran(...)` accepted all 5,600 rows, including current graph/cache/OOF source hashes and exact source paths.
- Recomputing the 80 measured-buffer records from the CSV reproduced the sidecar's `measured_buffers` exactly.

The primary progressive-lag significance field has 3,809 significant rows among 5,440 testable rows; the fixed-seven-lag Bonferroni field has 3,640 among the same 5,440 testable rows. There are 160 untestable rows (40 per target), although their stored numerical statistics are finite; untestability is retained rather than treated as non-significance.

| Target | Resolved `(network, radius)` decisions | Unresolved decisions | Resolved buffer min / median / max | Decisions with a later testable significant lag |
|---|---:|---:|---:|---:|
| betweenness | 17 | 3 | 2 / 4 / 7 | 13 |
| spread_cv | 12 | 8 | 1 / 2 / 7 | 13 |
| spread_mean | 10 | 10 | 1 / 3.5 / 5 | 6 |
| spread_resid | 12 | 8 | 1 / 1 / 4 | 13 |
| **All targets** | **51** | **29** | — | **45** |

Across the 800 `(network, target, radius, fit-seed)` curves, 329 carry `later_testable_sig=True`. The decision-level `later_testable_sig` flag is present for 45 of 80 decisions. It is an audit warning that a first non-significant lag did not make the rest of the curve uniformly non-significant; it does not change the predeclared first-testable-non-significant read-off or license a different buffer choice.

The shared-null construction also limits interpretation: permutations use the fit-seed-0 residual for each target/radius and the resulting tail area is reused for other fit seeds. Thus nonzero fit-seed `p_perm` values are seed-0-reference tail areas, not independently generated seed-specific permutation tests. Moran results set a graph-distance label-exclusion rule; they do not establish independent targets or remove transductive feature/Monte-Carlo dependence.

## Buffered preflight: complete

`results/phase6_buffered_cv_preflight.json` and `results/phase6_buffered_cv_provenance.json` were published together at 07:01:56. Their configuration hashes and scientific/input identities agree. The preflight contains 800 immutable per-cell assignment archives, 20,000 exact logical fold keys, and 4,000 logical cell keys.

| Preflight outcome | Logical fold rows |
|---|---:|
| ready | 15,472 |
| `infeasible_lt30` | 814 |
| `source_infeasible` | 814 |
| `unresolved_seedwise_buffer` | 2,900 |
| **Total** | **20,000** |

There are 13,972 ready canonical fits. The 1,500 aliases consist of 750 `buffer_measured → buffer_b1` and 750 `control_measured → control_b1` rows, so they do not add duplicate fits. By arm, all 4,000 region, b=1-buffer, and b=1-control rows are ready; measured-buffer arms account for the infeasible, source-infeasible, and unresolved statuses shown above.

## Pilot and current execution state

The authenticated pilot binds to the preflight configuration and identity and selected `rf_jobs=4`. Its representative work item is `ca-GrQc / spread_mean / radius 0 / seed 0 / fold 0 / region`.

| `rf_jobs` | Elapsed seconds | Kendall tau | Tau difference from 1 job | Max absolute prediction difference from 1 job | Valid |
|---:|---:|---:|---:|---:|---|
| 1 | 0.308128 | 0.8423172485988824 | 0 | 0 | yes |
| 4 | 0.231674 | 0.8423172485988824 | 0 | 3.552713678800501e-15 | yes |
| 8 | 0.234799 | 0.8423172485988824 | 0 | 3.552713678800501e-15 | yes |

All pilot memory guards passed. The declared tolerance is absolute `1e-10` plus relative `1e-12 × scale`, with Kendall-tau tolerance `1e-12`; the selected four-job pilot is within both. The pilot's 3,236.95-second estimate is a multiplication from this single ca-GrQc/spread_mean/radius-0/fold-0 measurement. It is a launch-planning extrapolation, **not** a reliable full-corpus ETA because fit cost and feasibility vary across networks, targets, radii, and arms.

The controller reports that the controlled one-fit stop and identical resume passed. The full buffered run is now active. This status task did not start, stop, or modify that run.

## Pending

> **Updated 2026-09-10 19:30 by Claude Opus 5:** the first two items below are now done —
> the run completed at 17:12:11 (`Buffered follow-up complete`) and its manifests validate.
> The section is retained as Astra's original record; the measured state follows it.
> Only the interpretation item remains, and it is Lane 2 of
> `docs/phase6_claude_worklog_20260910.md`.

- Complete the active full buffered-CV run and validate its final compact fold/cell/OOF manifests.
- Run the authenticated buffered descriptive analysis and separately labelled reported random-CV reference.
- Interpret results as descriptive within-seed buffered comparisons and distinct random-KFold versus BFS-region geometry reference values.

## Completed run — measured state, 2026-09-10 (Claude Opus 5)

The controller logged `Complete buffered corpus after 13971 newly fitted canonical folds.`
and, after the analyser, `Buffered follow-up complete` at 2026-09-10T17:12:11+05:30
(`results/phase6_buffered_controller_20260910.log`). No writer process survives.

**All 20,000 logical fold rows are accounted for, exactly as the preflight predicted:**

| Fold status | Rows |
|---|---:|
| `complete` | 15,472 |
| `unresolved_seedwise_buffer` | 2,900 |
| `infeasible_lt30` | 814 |
| `source_infeasible` | 814 |
| **Total** | **20,000** |

Cell level (4,000 logical cells): 3,012 `complete`, 580 `unresolved_seedwise_buffer`, 290
`infeasible_lt30`, 118 `incomplete`. The `region`, `buffer_b1` and `control_b1` arms are each
complete at 800/800; every infeasible and unresolved status falls on the two measured-buffer
arms. `results/phase6_buffered_cv_analysis.csv` holds 480 contrasts over six arm pairs, split
330 `scored` and 150 `unscored_incomplete_or_infeasible`. **The unscored contrasts are
retained and reported, not dropped.**

> **Alias note, added 2026-09-12 by Claude Opus 5 (Task 6 finding P3-08 / P2-10(a)).**
> 480 is the number of *rows*, not of independent measurements. In 15 of the 80
> (network, target, radius) cells the measured buffer resolved to 1, so the
> `buffer_measured` and `control_measured` arms are aliases of `buffer_b1` and
> `control_b1` (same folds, same predictions, copied digest; `canonical_arm` differs from
> `logical_arm` in the cells CSV). Each such cell contributes three contrast rows that
> repeat a b1 row number for number: `buffer_measured|region` = `buffer_b1|region`,
> `control_measured|region` = `control_b1|region`, `buffer_measured|control_measured` =
> `buffer_b1|control_b1`. That is **45 alias rows, all `scored`**, so the 330 scored
> contrasts are **285 distinct measurements plus 45 repeats**; the 150 unscored rows are
> all distinct. The rows are kept because the table is predeclared as one row per
> (cell, pair); since 2026-09-11 `analyse_buffered_cv.descriptive_contrasts` flags them
> (`is_alias`, `alias_of_pair`) and the analysis CSV carries those columns from its next
> regeneration. The 15 cells: ca-GrQc spread_cv r3, spread_resid r3; email-Eu-core
> spread_cv r2-r3, spread_resid r0-r3; facebook_combined spread_mean r3, spread_cv r1,
> spread_resid r2-r3; p2p-Gnutella08 spread_cv r2-r3, spread_resid r2. Any count of
> contrasts that beat 2 sd must be quoted over the 285, not the 330.

Identity checks passed: `cells_sha256`, `folds_sha256` and `oof_manifest_sha256` match the
current files; `preflight_sha256` matches `probe_buffered_cv.stable_digest(preflight)` — note
this is a canonical digest of the *parsed document*, so a raw-file SHA-256 comparison is the
wrong test and fails misleadingly; `preflight_identity_sha256` agrees across provenance,
cells and OOF manifest. 5 OOF archives, 2,712 completed OOF keys.

This is identity and accounting evidence only. The interpretation, with the declared limits
(within-seed descriptive comparisons; the random-KFold reference being a distinct geometry
rather than a matched control; nonzero-seed `p_perm` values being seed-0-reference tail
areas; a measured buffer being a diagnostic label-exclusion radius and not proof of
independence; 29 of 80 decisions unresolved and staying unresolved), is Lane 2 and is not
claimed here.

---

## Interpretation within the declared limits, 2026-09-10 (Claude Opus 5)

> Added 2026-09-10 by Claude Opus 5 (Lane 2). `verify_buffered_cv.py` passes **25/25** against
> the completed corpus. Everything below is read from
> `results/phase6_buffered_cv_analysis.csv`; the accounting is in the section above.

### What the design permits me to say

The comparison that carries weight here is **buffer vs control**, because those two arms are
size-matched: the control removes the same number of training rows as the buffer but chooses
them without regard to geometry. `region` is the un-thinned BFS-region arm. All three share one
geometry, so differences among them are interpretable.

The random-KFold file (`..._reported_random_reference.csv`) is **not** in this table and is not
used as a comparator. It is a *distinct geometry*, not a matched control, and treating it as one
would convert a geometry difference into a spurious "optimism" number.

All 330 scored contrasts carry the full 10 seeds. `descriptive_abs_mean_gt_2sd` is the
predeclared paired-SD heuristic — **descriptive, not a p-value**.

### Measured, mean paired difference (left − right), Kendall tau

| Contrast | n | Mean difference | Flagged |
| --- | ---: | ---: | ---: |
| `control_b1` − `region` | 80 | **−0.00513** | 23 |
| `buffer_b1` − `region` | 80 | **−0.09195** | 54 |
| `buffer_b1` − `control_b1` | 80 | **−0.08681** | 47 |
| `control_measured` − `region` | 30 | **−0.02660** | 13 |
| `buffer_measured` − `region` | 30 | **−0.18206** | 24 |
| `buffer_measured` − `control_measured` | 30 | **−0.15546** | 22 |

> **Split added 2026-09-12 by Claude Opus 5 (P3-08).** The three `*_measured` rows above
> average 15 genuine measured-buffer cells with the 15 alias cells whose measured buffer
> is 1 (see the alias note under the accounting). Separated:
>
> | Contrast | genuine (b > 1) n | mean | flagged | alias (b = 1) n | mean | flagged |
> | --- | ---: | ---: | ---: | ---: | ---: | ---: |
> | `control_measured` − `region` | 15 | −0.04626 | 11 | 15 | −0.00694 | 2 |
> | `buffer_measured` − `region` | 15 | −0.23089 | 15 | 15 | −0.13323 | 9 |
> | `buffer_measured` − `control_measured` | 15 | −0.18463 | 15 | 15 | −0.12628 | 7 |
>
> The alias half is the b=1 result restated for those 15 cells. Computed from
> `results/phase6_buffered_cv_cells.csv` via `analyse_buffered_cv.descriptive_contrasts`.

### The one substantive reading these numbers support

**The buffered drop is almost entirely geometric, not a training-set-size effect.** Removing the
same number of rows *without* regard to geometry costs −0.005 tau at b=1; removing them *by
proximity* costs −0.092. The size-matched contrast isolates the remainder at −0.087, i.e. about
94% of the b=1 drop is attributable to excluding spatially proximate labels rather than to
having less training data. At the measured radii the same decomposition gives −0.027 versus
−0.182, leaving −0.155, about 85% — *but those 30 cells include the 15 alias cells; over
the 15 cells whose measured buffer is genuinely above 1 it is −0.046 versus −0.231, leaving
−0.185, about 80% (added 2026-09-12, Claude Opus 5, P3-08)*.

This is the comparison buffered CV exists to make, and the control arm is what makes it
legitimate: without it, the entire drop could have been dismissed as smaller training sets.

Flag density rises monotonically with radius — r=0: 31/63, r=1: 29/72, r=2: 53/90, r=3: 70/105 —
which is the direction a proximity effect predicts, and is reported as a description of the
table rather than as a dose-response claim.

### Limits, restated because they bind on the paragraph above

- These are **descriptive within-seed** comparisons. There is no null distribution and no
  multiplicity correction across 330 contrasts; at a 2-SD heuristic some flags are expected by
  chance alone, so individual flags carry far less weight than the consistent sign and magnitude
  of the arm-level means.
- `p_perm` for nonzero fit seeds are **seed-0-reference tail areas**, not independent permutation
  tests, and are not used above.
- A measured buffer is a **diagnostic label-exclusion radius, not a proof of independence**.
  Nothing here establishes that buffered folds are independent — only that excluding nearby
  labels changes the score, and by how much.
- **29 of 80 decisions are unresolved and stay unresolved.** All 150 unscored contrasts fall
  entirely on the two measured-buffer arms (50 in each of the three pairs), so the
  `*_measured` rows above rest on 30 of 80 decisions — of which only 15 have a measured buffer
  above 1; the other 15 are b=1 aliases — and are correspondingly weaker than the
  b=1 rows. They are retained and reported, never dropped.
- **45 of 80 decisions carry `later_testable_sig=True`.** That is an audit warning, and it does
  **not** license departing from the predeclared first-testable-non-significant read-off. No
  buffer choice in this document was made by inspecting these results.

### Not claimed

No statement about the random-KFold geometry, no independence claim, no p-value, and no change
to any registered B1/B2 outcome. The sklearn config-propagation warnings
(`docs/phase6_parallel_warning_diagnosis.md`) remain an **open limitation**; I do not assert they
are harmless.

<!-- END docs/phase6_buffered_cv_execution_status.md -->

---

## <a id="rec-phase6_r1_ablation_readiness_addendum"></a>`docs/phase6_r1_ablation_readiness_addendum.md`

<!-- BEGIN docs/phase6_r1_ablation_readiness_addendum.md sha256=69f3f24c3fa3710094a5fdcefa73e12d14ae54d3819a4aaf5914b6ec462d93c8 date=2026-09-10 author=unsigned -->
# R1 ablation implementation readiness addendum

Prepared 2026-09-10 by read-only inspection of the current cache and estimator
contracts. This supplements the implementation brief before any R1 source is
created or fit is launched.

## Required decisions before implementation

1. **Make the inner-worker contract explicit.**
   `influence.experiment.out_of_fold_predictions` has no `n_jobs` parameter,
   while `influence.estimators.make_rf` and `make_rf_log1p` hard-code
   `n_jobs=-1`. The brief cannot pass those factories unchanged and also select
   bounded inner jobs in a 1/4/8 pilot. Define a new R1-only factory builder,
   for example `objective_for(target, rf_n_jobs)`, which constructs the same
   120-tree, leaf-2 RF with the supplied inner `n_jobs`, and wraps only
   betweenness in `TransformedTargetRegressor(log1p, expm1)`. Keep one outer
   process. The manifest, pilot, and every cell must bind `rf_n_jobs` and the
   objective identifier. Do not change existing estimator factories or the
   published experiment path.

2. **Specify the pilot as an artifact and equivalence gate.**
   The current brief says to measure resources but does not define the artifact,
   selection rule, or comparison. Add an atomic `pilot.json`, tied to the
   immutable manifest, that runs the same representative five-fold OOF cell at
   jobs 1, 4, and 8 sequentially with no cell checkpoint. It must record memory
   before/after, elapsed time, finite predictions, full OOF prediction deltas,
   tau deltas, fixed absolute/relative/tau tolerances, selected fastest valid
   job count, and an 800-cell time extrapolation. Execution must reject an
   absent, mismatched, incomplete, or non-equivalent pilot. These pilot fits are
   separate from the 800 authoritative cells.

3. **Bind and validate the complete cache identity.**
   The manifest list in the brief omits `data/manifest.json`, each raw graph,
   and `cache_cascades_<network>.npy`. At minimum bind the data manifest and
   raw graph hashes, rebuild each LCC, require `features.node` and
   `targets.node == arange(n)`, require `features.original_id` to match the
   rebuilt LCC, and require finite target vectors before any fit. If target
   reconstruction is used, include the cascades hash and use read-only mmap
   one network at a time. `cache_meta` alone cannot establish node identity.

4. **Record both rejected historical endpoint candidates.**
   For each network, the runner should hash and name both the root raw-objective
   `cache_oof_<network>.npz` and the reported betweenness
   `estimators/cache_oof_<network>__rf_log1p.npz` (plus their corresponding
   sweeps where used as provenance evidence). Root archives contain 640 bare
   keys and the log1p files exist separately. Neither can be reused, but
   recording only the root archive leaves the relevant reported betweenness
   endpoint unaccounted for.

5. **Resolve temporary-file recovery.**
   A deterministic `<cell>.tmp` cannot both remain untouched as interruption
   evidence and be reused for the missing cell on the next invocation. Use a
   unique temporary name per write attempt, `fsync`, and atomically replace the
   final `<cell>.json`; ignore old uniquely named temps. Alternatively reject a
   pre-existing deterministic temp and require explicit cleanup. State one
   policy and test it.

6. **Make nonfinite results a hard failure and bind final products.**
   `experiment.evaluate` returns NaN metrics when inputs or rank statistics are
   undefined; it does not reject them. The R1 runner must reject nonfinite y,
   predictions, and every stored metric before writing a cell, and the analyzer
   must recheck them. Add an atomic final-results manifest containing `run_id`
   and hashes of `cells.csv`, `paired.csv`, and the report, so final artifacts
   remain verifiably derived from the 800 immutable cells rather than merely
   atomically written.

The inspected R1 feature counts and the decision to refit all four sets remain
consistent with the current caches: 800 cells, 60 paired contrasts, and the
reported `rf_log1p` objective only for betweenness.

<!-- END docs/phase6_r1_ablation_readiness_addendum.md -->

---

## <a id="rec-phase6_claude_worklog_20260910"></a>`docs/phase6_claude_worklog_20260910.md`

<!-- BEGIN docs/phase6_claude_worklog_20260910.md sha256=2a6a94f9bb71b38aa2ce386980d525e098f0aaa1aee982914cad4b9401f06a2f date=2026-09-10 author=Claude Opus 5 -->
# Phase 6 expanded scope — Claude Opus 5 worklog

Running record for the lanes completing Astra's (GPT-6) Phase 6 expanded scope. Astra's own
timeline stays in `docs/phase6_extension_20260908.md`; this file does not replace it and
adds a per-lane entry there as each lane closes.

Plan of record: `C:\Users\Rachit\.claude\plans\so-gpt-6-astra-has-fluffy-marble.md`
(written 2026-09-10 by Claude Opus 5, approved by Rachit the same day).

Scope rulings taken by Rachit, 2026-09-10:

1. Stabilise the BRAVA/ABCDE corpus into the project before running the precision witness.
2. Run the precision witness on all five ABCDE graphs.
3. **Task 6, the full Phase 0–6 codebase audit, is deferred.** It is not started here, and
   no Phase 6 closure is claimed without it (`docs/phase6_final_audit_protocol.md`).

Every entry below is evidence from artifacts, not restated intent.

---

## 2026-09-10 19:30 IST — Claude Opus 5 — Lane 0: both long runs are complete; status record corrected

**Finding.** Both Phase 6 CPU sweeps finished earlier today, after the last documentation
pass. Every status document in the project still described them as active. No writer process
for either run survives (`Get-Process python` shows only unrelated PIDs).

Terminal controller evidence:

| Run | Terminal log line | Time |
|---|---|---|
| Structural bootstrap | `Complete: 12000 cells written to results\results_target_noise_refit_structural.csv; elapsed 442.9 min.` then `Structural follow-up complete` | 2026-09-10T14:11:17+05:30 |
| Buffered CV | `Complete buffered corpus after 13971 newly fitted canonical folds.` then `Buffered follow-up complete` | 2026-09-10T17:12:11+05:30 |

Sources: `results/phase6_structural_controller_resume_20260910.log`,
`results/phase6_buffered_controller_20260910.log`.

**Artifact validation performed (Lane 0 scope: identity and accounting only — no scientific
claim is made here, and row counts are not results).**

Structural bootstrap:

- `results/results_target_noise_refit_structural.csv` — exactly 12,000 rows; all `tau_refit`
  finite; grid is 5 networks × 3 Monte-Carlo targets × 4 radii × 200 replicates; `rep` spans
  0–199; single `tier` value `node+edge+subgraph`; **exactly one distinct
  `configuration_sha256`**, so no incompatible checkpoint was accepted across the run's two
  resumes.
- `results/results_paired_target_noise_structural.csv` — exactly 45 predeclared
  adjacent-radius contrasts.
- `results/provenance_target_noise_refit_structural.json` — **all 42 `input_sha256` entries
  recomputed against the current files: 0 mismatches, 0 missing.** This is the check that
  clears the plan's Risk 2 for this run (the stage-1 source changed on 2026-09-09, mid-run).
- Recorded bounded/default OOF equivalence check: `abs_tau_gap` 0.0, `max_abs_prediction_gap`
  7.105427357601002e-15 against a 1e-10 prediction tolerance.

Buffered CV — **all 20,000 logical fold rows accounted for**, matching the preflight's
predicted split exactly:

| Fold status | Rows |
|---|---:|
| `complete` | 15,472 |
| `unresolved_seedwise_buffer` | 2,900 |
| `infeasible_lt30` | 814 |
| `source_infeasible` | 814 |
| **Total** | **20,000** |

At cell level, 4,000 logical cells: 3,012 `complete`, 580 `unresolved_seedwise_buffer`, 290
`infeasible_lt30`, 118 `incomplete`. The `region`, `buffer_b1` and `control_b1` arms are each
complete at 800/800; the infeasible and unresolved statuses fall entirely on the two
measured-buffer arms. The 480 descriptive contrasts split 330 `scored` / 150
`unscored_incomplete_or_infeasible`; the unscored ones are retained and reported, never
dropped.

Hash bindings verified: `cells_sha256`, `folds_sha256` and `oof_manifest_sha256` all match
the current files; `preflight_sha256` matches `probe_buffered_cv.stable_digest(preflight)`
(a canonical digest of the parsed document, not a raw file hash — a raw-file comparison is
the wrong test and fails misleadingly); `preflight_identity_sha256` agrees across the
provenance, cells and OOF manifest. 5 OOF archives, 2,712 completed OOF keys.

**Documents corrected**, each with a dated attribution line:
`docs/phase6_extension_20260908.md` (new Progress entry),
`docs/phase6_buffered_cv_execution_status.md` (Pending → measured), and the external plan's
Sequencing row "6 — expanded scope".

**Still outstanding after this lane** (unchanged by it): the two write-up lanes, the
precision witness execution, the r=1 ablation build, evidence reconciliation, and the
deferred Task 6 audit.

---

## 2026-09-10 19:45 IST — Claude Opus 5 — Lane 3a: corpus stabilised; a truncated hash found and corrected

### The corpus is no longer volatile (plan Risk 1 closed)

Copied the BRAVA/ABCDE corpus from the dead session scratchpad
`%TEMP%\claude\C--Users-...\cf707b16-...\scratchpad\brava` to `data/brava/`
(185 files, 3.154 GB, robocopy reported 0 failed; its exit code 1 means "files copied",
not failure). Added `data/brava/` to `.gitignore` — it is ~3 GB of public, re-downloadable
third-party data, not ours to vendor.

`analyse_c3_benchmarks.DEFAULT_BRAVA` repointed from the temp path to
`Path(__file__).resolve().parent / "data" / "brava"`, with a dated comment giving the reason.

New `verify_brava_corpus_identity.py` + `results/phase6_brava_corpus_identity_20260910.json`
record hash, byte size and non-blank row count for **all ten files of all five graphs**.
This was necessary because **the historical preflight pins only two graphs** (cit-Patents and
com-lj); amazon, dblp and com-youtube had no recorded identity at all.

### Defect found: a 61-character SHA-256

`results/phase6_precision_input_preflight.json` recorded the `com-lj` score hash as **61
characters, not 64** — the three characters `74c` had been dropped after `...f3ef34c`. The
*same* truncated string had been transcribed into `precision_witness.SPECS`.

Why every existing check missed it: `validate_preflight_spec` asserts that the spec and the
preflight **agree with each other**, and both carried the identical defect. Agreement between
two copies of one error proves nothing. But `precision_witness.py` hashes the *real* score
file against that value, so a com-lj witness run would have failed — after building its
entire 3,997,962-node / 69,362,378-arc topology.

**The file did not change; the record was wrong.** Evidence, from two independent quantities
the same preflight recorded and which both still match exactly: 75,961,278 bytes and
3,997,962 non-blank rows. The malformed string is also a *subsequence* of the true digest,
which is what dropped-character transcription looks like and what a different file does not.

Corrected in both places under Rachit's 2026-09-10 ruling, documented at each site, with the
original preserved:

- `precision_witness.py` — true digest plus a comment recording the defect and the evidence.
- `results/phase6_precision_input_preflight.json` — `sha256` corrected; original retained as
  `sha256_original_malformed` with a `sha256_correction` block; whole prior file kept at
  `results/phase6_precision_input_preflight.json.pretruncationfix_20260910`.
- New `precision_witness.assert_pinned_hashes_wellformed()` and verifier test
  `test_every_pinned_hash_is_a_wellformed_sha256`. This check needs no second copy to compare
  against, which is precisely why it catches a defect transcribed into both records.

`verify_c3_precision_witness.py` now passes **10/10** (was 9).

### Scope correction, ruled by Rachit

The witness implements only two graphs. `SPECS` covers cit-Patents and com-lj — the two
clamped graphs — and the three clean graphs were scoped out by Astra because they have no
clamp to witness. Rachit's ruling stands: **extend to all five.** The two implemented graphs
are running now; the three additions require new pinned specs whose `nodes`/`arcs`/
`selected_targets` counts can only come from a construction pass, and are the next step.

---

## 2026-09-10 20:10 IST — Claude Opus 5 — Lane 3b: the witness's pinned degree range was wrong; counts were right

### What happened

The first real execution of the precision witness stopped on **both** pinned graphs with
the identical error:

```
probe_c3_precision_witness.py: error: selected target degree 2 outside [3,18]
```

cit-Patents at 19:37, com-lj at 19:42. An identical failure on two independent graphs is not
a data anomaly.

Astra's design anticipated this exact situation and said what to do
(`docs/phase6_precision_witness_design.md`, "Exact conditional comparisons"): *"if any target
lies outside `[3,18]`, stop rather than silently changing the bounded search."* The code did
stop, before writing any artifact. **That instruction was followed, and the investigation it
demanded then falsified the bound rather than the data.**

### Evidence

The failed cit-Patents run left its memmapped topology on disk, so the truth could be measured
without a rebuild. A read-only instrumented replay of the *same* selection predicate — recording
the degree histogram instead of raising — produced:

| Quantity | Pinned prediction | Measured | |
|---|---|---|---|
| Printed-zero rows | 709,724 | **709,724** | match |
| Selected structurally-positive rows | 662 | **662** | match |
| Target degree range | `[3,18]` | **`[2,6]`** | **falsified** |

Degree histogram of the 662 selected targets:

| Degree | 2 | 3 | 4 | 5 | 6 |
|---|--:|--:|--:|--:|--:|
| Targets | 424 | 178 | 26 | 33 | 1 |

**424 of 662 targets — the majority — have degree 2.** The gate was rejecting most of its own
valid target set.

### Root cause

Two is the structural **minimum**, not an anomaly. The selector admits a row when its printed
score is zero and one pair of its neighbours is nonadjacent. A degree-two node with two
nonadjacent neighbours satisfies that, and is structurally positive for the same reason every
other selected node is: `a-v-b` is a length-two shortest path, so `BC(v) >= 1/c > 0`. A floor
of 3 is therefore not a data guard — it is **unsatisfiable in principle** for a legitimate
class of targets.

Because the two *other* pinned quantities reproduced exactly, the topology is unambiguously
the intended graph; only the degree prediction was wrong.

Where the number came from: `grep` finds `3--18` in exactly one place in the whole repository —
the design sentence saying it was *"previously reported"*. **No artifact records that
measurement.** It was inherited, and since the witness had never completed a run, nothing had
ever been able to test it. This run was the first thing that could, and it did.

### Changes made

Fixed under TDD — the failing test was written and confirmed failing with the production error
on a three-node fixture (path `10-20-30`, node 20 scored zero) *before* any production edit.

- `precision_witness.py` — the floor became the named constant `MIN_TARGET_DEGREE = 2`, with a
  comment recording the defect, the measurement and the reasoning. **At this point I judged the
  ceiling of 18 to be a genuine resource guard and left it alone. The com-lj run then falsified
  that too — see "Second failure" below.**
- `precision_witness.py` — `_select_targets` now also returns the observed minimum, and the
  summary records `minimum_degree` beside the existing `maximum_degree`. Previously only the
  maximum was persisted, so a completed run could not report the very quantity whose inherited
  prediction it had falsified. **The range is now a measured output, not an inherited claim.**
- `verify_c3_precision_witness.py` — new
  `test_degree_two_structurally_positive_node_is_a_valid_target`. Verifier now passes
  **11/11** (was 10); all nine pre-existing tests still pass, including the diamond fixture
  that was written around the old floor.
- `docs/phase6_precision_witness_design.md` — both pinned-range sites carry a dated
  superseding note. Astra's original prose is retained, not deleted: it was a correctly
  registered prediction, and the record should show it was tested and failed.

### What did NOT change, and why it matters

The **pinned counts 662 and 1,086 stand**, and the same investigation *confirmed* 662 by direct
measurement. Only the degree gate moved. No recorded hash was rewritten and no resume guard was
bypassed.

### Outcome: both graphs ran to completion

After the second correction below, both pinned graphs completed **exit 0** (23:24 and 23:36).
Full write-up appended to `docs/phase6_external_precision_followup.md`.

| Graph | Targets | Pinned | Usable pairs | Degree range | Pair scan | `> 5e-15` | `> 1e-14` |
|---|---:|---:|---:|:--:|---:|---:|---:|
| cit-Patents | 662 | 662 | 727 | `[2, 6]` | 1,459 | **0** | **0** |
| com-lj | 1,086 | 1,086 | 1,588 | `[2, 111]` | 293,013 | **0** | **0** |

Both measured pair scans match the figures my read-only instrumentation predicted before the
runs, which is an independent check on the accounting.

The scientific result is a **null**: no pair qualifies at either threshold on either graph, so
the one-pair witness class does not reject the nearest-rounding explanation for any of the 1,748
rows. Reported as a null, not as weak evidence either way.

**The margin is one common neighbour, on both graphs** — boundary `c <= 28` versus observed
minimum 29 on cit-Patents, and `c <= 25` versus 26 on com-lj, with observed `c` ranging to 297
and 707. I checked the arithmetic before reporting it rather than assuming a defect: first
cit-Patents row has `c = 48`, cross-products `2.0e15` vs `3.4e15`, correctly `False`.

My reading, **labelled inferred** in the write-up: this is what consistency looks like. A row is
selected only if it prints zero while being structurally positive; if the rounding is honest the
true value lies below the printing threshold, which forces the certified bound below it too, and
so forces `c` above the boundary. A qualifying pair would have been a *detected contradiction*.
None was found, and the data sits immediately against the boundary the clamp implies. That is an
inference about consistency, not an established mechanism, and **no registered C3 verdict
changes** — P4 keeps its registered conditional wording.

### Second failure: the ceiling was wrong too

With the floor fixed, `com-lj` failed at the other end at 23:16:

```
probe_c3_precision_witness.py: error: selected target degree 34 outside [2,18]
```

Same instrumented replay, on the topology that run left behind:

| Quantity | Pinned prediction | Measured | |
|---|---|---|---|
| Printed-zero rows | 1,151,702 | **1,151,702** | match |
| Selected structurally-positive rows | 1,086 | **1,086** | match |
| Target degree range | `[3,18]` | **`[2,111]`** | **falsified at both ends** |

107 targets below 3, and **412 of 1,086 above 18**. So the inherited range is wrong at both
ends on both graphs, while all four pinned *counts* reproduced exactly.

**Why the ceiling was replaced rather than raised.** 18 was not an independent resource guard;
it was a second consequence of the same wrong degree claim, used to state the design's pair
budget `1,748 * C(18,2) = 267,444`. The real cumulative scan is `sum C(degree,2)` over selected
targets: **1,459** (cit-Patents) + **293,013** (com-lj) = **294,472**, about 10% over the quoted
figure. The design itself states these intersection scans are constant-extra-memory streaming
work, so that count bounds **time, not memory** — a 10% overrun of a few hundred thousand
two-pointer intersections is not an envelope breach.

Capping per-node degree is therefore the wrong instrument: it rejects lawful targets to limit
the cumulative scan only indirectly. The gate now guards the cumulative scan itself
(`MAX_TOTAL_PAIR_SCAN`, set far above the measured 294,472 so it binds on a runaway, not on real
data), and each run records `total_pair_scan` and `total_pair_scan_budget` beside the measured
degree range — so the resource claim is checkable from the artifact rather than resting on a
predicted degree range.

New test `test_pair_scan_budget_replaces_the_degree_ceiling` reproduces the degree-34 failure on
a synthetic 35-node star and asserts the budget accounting. Verifier now **12/12**.

The cit-Patents artifacts produced under the intermediate (floor-only) build were archived to
`results/phase6_precision_witness_superseded_20260910/` and both graphs re-run, so the published
outputs share one provenance rather than two.

**This is a design amendment, put to Rachit and approved on 2026-09-10** ("the pair-scan
replacement is fine"). Astra's registered prediction is retained verbatim in the design doc;
it was tested, and it failed.

### Note on the class of defect

This is the second inherited-and-never-verified value found in this lane, after the
61-character SHA-256. Both share a shape: a quantity copied from a prior report into a gate,
never independently measured, and structurally impossible for the existing checks to catch.
The mitigation in both cases was the same — a check that does not depend on a second copy of
the same claim.


---

## 2026-09-10 23:45 IST — Claude Opus 5 — Lane 2: buffered CV interpreted within its declared limits

`verify_buffered_cv.py` passes **25/25** against the completed corpus. Interpretation appended to
`docs/phase6_buffered_cv_execution_status.md`; the Lane 0 accounting above is unchanged.

**The one substantive result.** The buffered drop is almost entirely *geometric*, not a
training-set-size effect. The size-matched control arm is what makes this sayable:

| Contrast | n | Mean paired difference (tau) |
|---|---:|---:|
| `control_b1` − `region` (size only) | 80 | −0.00513 |
| `buffer_b1` − `region` (size + geometry) | 80 | −0.09195 |
| `buffer_b1` − `control_b1` (geometry, size-matched) | 80 | **−0.08681** |

So ~94% of the b=1 drop comes from excluding spatially proximate labels rather than from having
less training data (~85% at the measured radii). Without the control arm the whole drop could
have been dismissed as smaller training sets.

**Limits enforced in the prose, not just noted.** The random-KFold reference is deliberately
*not* used as a comparator — it is a distinct geometry, and treating it as a matched control
would manufacture an "optimism" number. Descriptive within-seed only, no p-values, no
multiplicity correction over 330 contrasts. A measured buffer remains a diagnostic
label-exclusion radius, **not** proof of independence. All 150 unscored contrasts fall entirely
on the two measured-buffer arms, so those rows rest on 30 of 80 decisions and are weaker; they
are retained, not dropped. The 45 `later_testable_sig=True` decisions are an audit warning and
did **not** license any departure from the predeclared read-off.

---

## 2026-09-10 23:45 IST — Claude Opus 5 — Lane 4: r=1 ablation built and running

Tasks 2–4 of `docs/phase6_r1_ablation_implementation_brief.md` are complete; the 800-cell run is
in progress.

**Created** `probe_r1_ablation.py` (runner, atomic checkpoints, pilot gate) and
`analyse_r1_ablation.py` (paired contrasts, final artifacts). **Extended**
`verify_r1_ablation.py` from 14 to **26 tests, all passing**, adding the paired arithmetic on
fixed vectors (mixed-sign counts, ddof=1 sample SD, strict `>` boundary, missing-endpoint
rejection) and the cell-record integrity cases (tampered metric, foreign `run_id`, filename/key
mismatch, changed fold count, unique-temp atomic write).

Addendum items honoured: the R1-only bounded-worker factory (item 1); `pilot.json` as an
artifact and gate (2); full cache identity including a rebuilt LCC and `original_id` match (3);
**both** rejected OOF candidates hashed and named, root raw-objective and reported log1p (4);
unique temp name per write attempt, stale temps left as interruption evidence (5); nonfinite
results rejected at the boundary since `evaluate` returns NaN rather than refusing it (6).

**Pilot gate passed** — the point of it being that `make_rf` hardcodes `n_jobs=-1` and could not
be asked for this comparison, so having introduced a private factory the burden was to show it
is the same model:

| jobs | seconds | max abs prediction gap | abs tau gap |
|---:|---:|---:|---:|
| 1 | 32.1 | 0.0 | 0.0 |
| 4 | 6.7 | 7.11e-15 | 0.0 |
| 8 | 4.9 | 1.07e-14 | 0.0 |

Equivalent against a 1e-10 tolerance; tau identical to the last bit; 8 jobs selected. The 4-job
gap matches the structural run's own recorded equivalence figure exactly.

**Two corrections to my own earlier work, recorded rather than quietly fixed.**

1. My `test_verifier_does_not_train` banned *importing* `probe_r1_ablation` and
   `analyse_r1_ablation`. That was an over-broad proxy: the brief forbids **calling** fitting
   entry points, importing a module fits nothing, and Task 3 explicitly requires testing the
   analyzer's arithmetic — which the ban made impossible. Narrowed to the calls, and widened to
   cover `run_cell` / `run_pilot` / `load_or_create_pilot`.
2. I initially added `main` to that call ban and it caught this file's own `unittest.main()`. A
   name-based AST check cannot distinguish them, so `main` was removed from the set.

**Reporting requirement carried into the analyzer itself**, not left to prose discipline:
`RESULTS_r1_ablation.txt` prints results per network, lists both flagged *and* unflagged
(network, target) cells for every contrast, and states in its own text that the stars are
descriptive and that effects are qualified **by graph** — so a reader who quotes the table
cannot lose the qualification.

Run log: `results/phase6_claude_r1_ablation_run_20260910.log`;
`run_id afadc675f345d0dc1d626b4293cb1452fa6836e82bf02cad7c4fb26b4ae04441`.

---

## 2026-09-11 00:05 IST — Claude Opus 5 — Lane 1: structural bootstrap scored; A7's pattern reproduced exactly

`verify_structural_target_noise.py` **8/8**, `verify_structural_target_noise_analysis.py` **3/3**
(both fixture-based, so they establish semantics, not the corpus — the corpus evidence is Lane 0's
12,000-row / 42-hash validation). Write-up appended to `docs/phase6_structural_task_report.md`,
whose "Results are pending" line is retained as the record of what was planned.

**The 45 predeclared contrasts: 38 retained / 3 lost / 4 neither / 0 new.** This matches A7's
saved dynamic-tier analysis not only in counts but in the **identical three contrasts** —
email-Eu-core/spread_resid, facebook_combined/spread_cv, facebook_combined/spread_resid, all at
radius 1→2 — confirmed by direct comparison of the two CSVs.

**I have qualified this rather than reporting it as replication.** The two tiers **share their
target-noise resamples by design** (asserted by the verifier's own
`test_resample_identity_is_deterministic_and_shared_by_design`), so they see the same perturbed
targets and this is *not* independent evidence. What it does establish is that those three flags'
fragility is driven by the target noise itself, not by the feature tier — which is the question
the structural follow-up existed to answer.

**No headline structural-tier star failed that A7 retained, and none was gained.** Had one
failed, that would have been the finding.

**The quantitative result:** `target_over_seed_sd` has median **1.700**, is `>1` in **41 of 45**
contrasts (91.1%), range 0.700–3.984. Target-noise resampling yields a larger paired SD than
seed-only resampling in roughly nine contrasts out of ten, so ten-seed intervals understate total
uncertainty — which is *why* three flags do not survive.

No registered C3/A7 outcome changes.

---

## 2026-09-11 04:05 IST — Claude Opus 5 — Lane 4 complete: the r=1 effect is the 5-node orbits, and nothing else

800 cells, exit 0, `run_id afadc675f345d0dc1d626b4293cb1452fa6836e82bf02cad7c4fb26b4ae04441`.
`analyse_r1_ablation.py` wrote `cells.csv`, `paired.csv`, `RESULTS_r1_ablation.txt`.
60 contrasts, **19 flagged**: `add_nonorbit_subgraph` 2/20, `add_orbit_lt15` **0/20**,
`add_remaining_g5_orbits` 17/20.

**The clean part of the result:** adding the 4-node-and-smaller node orbits changes nothing
anywhere — zero of twenty cells, absolute mean gain never above 2.5e-4. The remaining 5-node
orbits then give up to +0.035 tau. The rung is identified, not just the tier.

**The part I am not smoothing over:** email-Eu-core/`betweenness` has a *negative* 5-node mean
(−0.00049, sd 0.00037, nine of ten seeds worse). It is below the flag threshold, but it points
opposite to every other network and is written up as such. Two other cells fail to flag
(ca-GrQc/`betweenness`, email-Eu-core/`spread_resid` — the latter a large mean with larger seed
variance). The two `add_nonorbit_subgraph` flags are both `betweenness`, i.e. target-specific.

Written up in `docs/phase6_r1_ablation_implementation_brief.md` (dated section) and study
**§26k.3**. Lanes 1 and 2 also now have study subsections **§26k.1** and **§26k.2**; the planned
"Still required" table in §26k is retained above them as the record of what was planned.

Reconciling the study's broader expressive-power language against these artifacts is Lane 5, and
is deliberately not done here.

---

## 2026-09-11 04:20 IST — Claude Opus 5 — Lane 3 complete: all five ABCDE graphs, and the clean three came out at exactly zero

Extended `precision_witness.SPECS` from two graphs to five. `verify_c3_precision_witness.py`
**13/13**. All five production runs exit 0.

**The result:** amazon, dblp and com-youtube select **zero** structurally-positive printed zeros
among **3,030,420** printed zeros between them (701,532 / 1,678,358 / 650,530). The two clamped
graphs select 662 and 1,086. The selection predicate is purely structural — two nonadjacent
neighbours force strictly positive betweenness — so it is not a clamping detector, which is why
the separation means something: the two graphs independently flagged as clamped are exactly the
two carrying structurally impossible zeros.

It is still a null and is written up as one. It does **not** prove the three graphs are unclamped,
only that their printed zeros carry no detectable structural contradiction. The false-nonzero
blind spot and the inferred status of the quantisation mechanism both stand.

**Provenance weakness I am flagging myself.** No pre-existing record pinned these three graphs, so
every pinned field was measured in order to be pinned
(`results/phase6_precision_witness_discovery_20260911.json`; preflight entries tagged
`source: "discovery_2026-09-11"`, original backed up). Such a pin cannot falsify its own run. Three
checks do carry weight: the in-memory discovery and the external-merge production path produce
**identical `topology_sha256`** on all three; score rows equal node count; and parsed rows minus
self-loops equal canonical edges.

**Defect found and fixed (TDD, failing test first).** The selector could not express a zero-target
run — it fell through to `int(None)` and raised `TypeError`. The source comment asserting this was
unreachable was correct only while the clamped pair was the whole corpus; it is corrected in place,
not deleted. A null now publishes a header-only witness file and a summary saying zero.

Written up in `docs/phase6_external_precision_followup.md`. Study **§26i** reconciliation and the
four gates are Lane 5, next.

---

## 2026-09-11 04:19 IST — Claude Opus 5 — Lane 5: four gates green, evidence lanes closed, audit outstanding

`verify_pipeline.py`, `verify_generators.py`, `verify_docs.py`, `verify_c3_scoring.py` all pass;
logs at `results/VERIFY_phase6_claude_lane5_verify_<gate>_20260911.txt`. C3 registered verdicts
unchanged (P1 FALSIFIED MAE 0.07856…, P2 SUPPORTED ρ 0.8901…, P3 SUPPORTED 12/14, P4 PASSED under
the registered conditional). `docs/phase6_completion_checklist.md` reads "evidence lanes complete;
final audit outstanding". No closure claimed. *(Entry written retrospectively at 14:15 IST; the
gate logs carry the actual timestamps.)*

---

## 2026-09-11 14:15 IST — Claude Opus 5 — Task 6 audit: all 87 paths reviewed; root integration awaits Rachit's decisions

Rachit called the audit ("go ahead and start the Task 6 audit") and, with Astra's Codex quota
exhausted until 2026-09-15, chose "Raise effort, I review". Every review below is mine and is bound
to the file's SHA-256 in `results/phase6_task6_coverage_ledger_20260911.json`; the recorder refuses
a review whose disk hash differs from the enumerated hash, and no recorded hash was rewritten.

**Coverage.** 87 paths: Partition 1 (21), Partition 2 (44), Partition 3 (19), Partition 0 (3
third-party BRAVA snapshot files, interface-only). Ledger status is now
`reviews_complete_pending_root_integration`. Dispositions: 32 clean, 37 clean with notes, 14 with
defects, 4 interface/build.

**Findings: 30 total** — 2 MAJOR, 15 MINOR, 11 INFORMATIONAL, 3 LIMITATION (P1-08, P2-09, P0-01)
plus P3-06 recorded as a limitation. Nothing reverses a registered outcome. The ones that need a
decision rather than a mechanical fix:

- **P1-01 (MAJOR)** — six hop-1 5-node orbit columns are tagged one rung too shallow because
  `_calib.py` does not take the max-over-families radius `graphlets.py` says it does. The fix is a
  retag **and a refit** of every cell that includes those columns (RF splits by column index — a
  retag alone changes nothing fitted). That is a training run and needs authorisation under the
  2026-08-27 decision as amended 2026-09-08.
- **P1-02 (MAJOR)** — no content hash binds cached stage-1/2 results to their edge list. Code fix
  is small; the question is whether to also pin expected download hashes in `fetch_data`.
- **P2-02 (MINOR)** — two provenance files key their hash maps on local absolute paths. Code fix
  is clear; the artifacts must **not** be rewritten (identity_sha256 folds the keys in), so the
  choice is a compatibility shim that maps old keys, or leaving the two files as recorded
  limitations.
- **P2-03 / P2-11 / P3-08** — the raw-vs-log1p betweenness arm split. Fix is an explicit arm
  selector plus regeneration of `cache_failure_atlas.npy`, `RESULTS_failures.txt`,
  `RESULTS_betweenness.txt`, fig2 (no fits), and labels on the historical raw-arm artifacts.
- **P3-01 + P3-07 (MINOR)** — §19b's "α ≈ 0.046 / 147 stars" is wrong (the 2-sd rule is
  |t| > 6.32, α ≈ 1.4×10⁻⁴; "zero stars withdrawn by BH" is forced by that, not found), and §19b's
  table, `RESULTS_multiplicity.txt` and `multiplicity.csv` are three inconsistent snapshots
  (edge tier starred/BH/BY: 29/44/43 vs 28/43/38 vs 29/44/39; dynamic tier 4/6/4 vs 4/6/4 vs 5/5/5). Fix is a rerun of `analyse_multiplicity.py` (no
  fits), a rewrite of the §19b objection paragraph and dynamic-tier paragraph, and a
  `verify_docs` pin. The 31 under-claimed effects — the actual finding — survive every snapshot.
- **P3-02** — C3's floor uses the asymptotic tau-b form (differences ≤ 1.5×10⁻⁶, minimum P3
  margin 1.7×10⁻⁴; no verdict moves). One-line fix; regenerating the cells CSV to match would need
  the full external traversal, which is not authorised.

Everything else (P1-03..07, P1-09..11, P2-01, P2-04..08, P2-10, P3-03..06) is mechanical and
numbers-neutral, and I will apply it in root integration once the decisions above are taken,
re-reviewing each changed file at its new hash and re-running the four gates.

**What this audit did not do.** It did not run `analyse_c3_benchmarks.py` (external traversal not
authorised), did not fit anything, and did not resolve any defect yet — the protocol's closure
contract (resolve, re-review at new hash, re-run gates, reconcile plan/study/HANDOFF/paper/
reproduction/ledger, retain limitations) is still entirely ahead. Phase 6 remains **not closed**.

## 2026-09-12 10:50 IST — Claude Opus 5 — Task 6 root integration: what has landed, what is running

Rachit's decisions (2026-09-11): P1-01 "retag + refit now"; P2-02 compatibility shim; P2-03 /
P3-08 regenerate on log1p; everything else "apply all proposed fixes for all review parts,
free to re-download or re-sweep, no compromises". Numbered runs below follow the ledger
(`results/phase6_task6_coverage_ledger_20260911.json`). Every archived pre-fix artefact is a
byte copy with a dated `ARCHIVED_*.md`; nothing recorded was edited in place.

**Landed (2026-09-11 → 2026-09-12 morning).**

- **P1-01 retag + refit.** `_calib.derive_node_radius` (exact eccentricity) now gates the
  calibrator (`verify_pipeline.py` 2c-5); six 5-node node orbits 56/57/65/66/68/70 and nine
  5-node edge orbits 49/50/51/59/60/61/63/64/65 moved hop 1 → hop 2. r=1 structural set
  62 → 56 columns; ladder 2/56/145/170. Every r=1 subgraph-tier cell in `sweep_*.csv`,
  `estimators/sweep_*__*.csv` and the `cache_oof_*` archives was refit
  (`results/RESULTS_orbit5_refit_20260911.txt`). r=0/2/3 cells are column-identical.
- **Run C2 — r=1 ablation re-run, headline reversal.** Fresh 800 cells
  (`results/phase6_r1_ablation/`, run_id c66485a6…; pre-retag run moved to
  `results/phase6_r1_ablation_pre_orbit5_retag_20260910/`). `add_remaining_g5_orbits`
  **17/20 → 0/20** flagged cells (largest |mean| 0.00054 τ; sum of means +0.187 → +0.0004).
  `add_nonorbit_subgraph` 2/20 and `add_orbit_lt15` 0/20 unchanged. "5-node beats 4-node at
  r=1" was a radius effect labelled as a graphlet-size effect — the Finding 10 class of
  error. Evidence: `results/phase6_r1_ablation_retag_delta_20260912.txt`. Study §16 and
  §26k.3 carry dated reversal blocks; HANDOFF Finding 3 "REVERSED"; the "5-node graphlets
  justify their cost" open decision is re-opened. `verify_r1_ablation.py` expected sizes
  re-pinned (38, 40, 45, **56**) with a dated comment, not bypassed.
- **Run C6 — reported analyses regenerated** on the refit corpus and the spliced log1p
  betweenness arm (`analyse.load`): `RESULTS.txt`, `RESULTS_betweenness.txt`,
  `RESULTS_failures.txt`, `RESULTS_topk.txt`, `topk_rstar.csv`, `estimator_*.csv`, figs
  1/2/2-tail5/5/6. Previous versions kept as `*_pre_orbit5_refit_<date>.txt` and
  `results/pre_orbit5_refit_20260911/`. B2 agreement unchanged 17/20 (hgb, hgb_matched),
  11/20 ridge; `rf_log1p` no longer listed as an estimator (P2-01). Top-k agreement
  74.0 → 72.0%. Betweenness moves at every radius because of the objective splice, not
  the refit — `results/REGENERATION_NOTE_20260912.md` says which is which.
- **Multiplicity (P3-01/P3-07).** Star rule |t| > 6.32, α = 1.37×10⁻⁴; families 54/29/25/5
  after the refit; `RESULTS_multiplicity.txt` regenerated, previous kept.
- **Run C7 — C3/C4 regenerated from the raw corpus** (`data/brava/`, P3-02/03/04 code).
  Registered verdicts unchanged to the digit (MAE 0.07856417907755398, ρ 0.8901098901098902,
  P3 12/14, P4 passed; `c3_scored_summary.json` byte-identical); no P3 hit flips under the
  exact floor (max gap 1.54×10⁻⁶). Structure/cells now carry the ABCDE shipped-support
  columns for cit-Patents and com-lj (previously `n_zero_shipped == n_zero`). C4 smoke rows
  moved ≤ 2×10⁻³ on the refit r=1 archives. `verify_c3_fallback.py`, `verify_c3_scoring.py`
  green. Details: `results/C3_C4_REGENERATION_NOTE_20260912.md`; pre-copies in
  `results/c3_c4_pre_task6_20260909/`.
- **Run C8 — historical r=1 / raw-arm lanes** decided per file in
  `results/HISTORICAL_LANES_NOTE_20260912.md`: `RESULTS_r1_subgraph_ablation.txt`
  superseded (reversal); `RESULTS_orbit04_ablation.txt` valid (r=3); `RESULTS_edge5.txt`
  re-run scheduled (both retags hit its r=1 rows); `RESULTS_edge_tier*.txt` valid at r=2,
  facebook log1p addendum scheduled (P2-11); robustness not re-run (retag-independent),
  fig3 regenerated with the objective label. `analyse_edge_tier.py` and `analyse_edge5.py`
  gained `--objective raw|reported` (default `raw` reproduces the historical files);
  `analyse_robustness.py` prints the arm.
- **P1-08** study scope subsection on what is and is not independently established about
  the 5-node orbit counts; verification-table row added.
- Gate/verifier logs from this lane: `results/VERIFY_phase6_claude_*_20260912.txt`
  (pipeline 95 PASS incl. 2c-5; r1_ablation 26 OK; buffered_cv 26 OK; docs; c3_scoring).

**Running (serial, one fitting lane at a time, all detached with dated controller logs).**

| Stage | Lanes | Started | Estimate | Log |
| --- | --- | --- | --- | --- |
| 1 | C3 structural bootstrap (12,000 cells, ~10.4 s/cell) then C4 buffered CV | 10:04 IST (pilot 120/120 passed 10:25) | ~35 h + ~10 h | `results/phase6_root_integration_controller_20260912.log`; per-lane `phase6_{structural,buffered}_controller_20260912.log` (UTF-16, read via `iconv -f UTF-16LE`) |
| 2 | C5: B1 sample efficiency (5,600 cells) → objective-horizon probe (800 fits) → A7 frozen arm, refit arm (200 reps, 12,000 fits, `--check-pairing`), arm-2 scoring, paired analysis | parked, starts when stage 1 prints a terminal line | ~5 h + ~2 h + ~33 h | `results/phase6_root_integration_stage2_20260912.log` |
| 3 | C8: `analyse_edge5.py` (five networks, raw; betweenness log1p), `analyse_edge_tier.py facebook_combined --objective reported` (edge, subgraph) | parked behind stage 2 | ~3 h | `results/phase6_root_integration_stage3_20260912.log` |

Pre-refit copies for stage 2 are in `results/phase6_c5_pre_orbit5_refit_20260906/`; the
stage-2 script removes the live originals only after a SHA-256 match against the archive,
and each probe's self-check runs before its fits. Total ≈ 87 h serial, all authorised under
"no compromises"; Rachit can trim any lane by stopping its controller — nothing downstream
splices a partial run.

**Still owed (D closure).** Lane write-ups when stages finish (structural task report,
buffered status, study §26k; C5 reconciliation of README "How many labels", "3 of 50 r*
cells moved", HANDOFF, study §24/§26; C8 edge5 table in study §"The edge axis"); re-review
of every changed file at its new hash; four gates + lane verifiers once more; study §26k.2,
§24.x, §26i, §20 table (ca-GrQc +0.0354 ✱ is stale); HANDOFF, paper draft, reproduction,
completion checklist, plan Sequencing; vault `record_work` (Logs) and a Gotchas entry on
the empirical radius calibrator.

## 2026-09-12 15:30 IST — Claude Opus 5 — Task 6 root integration: study/HANDOFF reconciliation of the regenerated outputs

Continuation of the 10:50 entry. All edits are dated blocks; no historical prose deleted.
`verify_docs.py` re-run after the last edit: `results/VERIFY_phase6_claude_docs_c7c8_20260912.txt`,
ALL CHECKS PASSED.

**docs/study_doc_v2.md**

- New §24.3a (before §24.4): the all/nonzero τ table re-read on the reported log1p arm
  from `results/RESULTS_betweenness.txt`. The facebook sign inversion of §24.3 (nonzero τ
  above full τ at r=2/3) does **not** survive the objective: on the reported arm the gap is
  +0.0137 / +0.0116 in the ordinary direction, and the r=3 full-minus-nonzero drop is
  monotone in the zero fraction on all five networks (0.152 / 0.144 / 0.047 / 0.027 /
  0.012). Finding 7's ca-GrQc saturation on the nonzero subset survives
  (0.7365 → 0.7754 → 0.7765). The §24.3 sentence "on four of five full τ flatters the
  model; on the fifth it understates it" is superseded to "on all five, by an amount
  that tracks z". §24.4's direction argument never depended on the inversion.
- §26c: dated subsection "Re-read on the refit registries" — B2 licence unchanged
  (17/20 hgb, 17/20 hgb_matched, 11/20 ridge); `rf_log1p` removed from
  `estimator_horizons.csv` as a non-learner (P2-01).
- §26i: dated subsection "Regenerated after the Task 6 fixes" — C7 verdicts unchanged
  to the digit; bookkeeping differences enumerated with a pointer to
  `results/C3_C4_REGENERATION_NOTE_20260912.md`.

**HANDOFF.md §10** — one dated block before "The corpus": (1) every betweenness τ in §10
is the retired raw arm; reported-arm r=0→r=3 endpoints for all five networks; facebook
r\*(ε=0.02) for betweenness is 2 not 3, so the Finding 6 matched-dense-pair argument
survives with a smaller gap; (2) the r=1 refit moved Finding 1's r0→r1 / r1→r2 marginals
on every target — regenerated ca-GrQc table given inline (spread targets lost 0.013–0.035
at hop 1 and gained it back at hop 2). Finding 2's r\*(ε) ladder for ca-GrQc spread mean
unchanged.

**Controllers at 15:28 IST** (evidence: lane logs, `Get-Process python`):

| stage | state | evidence |
|---|---|---|
| 1 structural (pid 25956) | 2489/12000 cells, 7.3 s/cell steady since 10:25:51 | `phase6_structural_controller_20260912.log` (UTF-16LE) |
| 1 buffered | queued behind structural | master log `BEGIN structural` is the last line |
| 2 (pid 17016) | parked, polling for stage-1 terminal line | `..._stage2_20260912.log` |
| 3 (pid 8944) | parked, polling for stage-2 terminal line | `..._stage3_20260912.log` |

Projection at 7.3 s/cell: structural finishes ≈ 10:45 IST 2026-09-13; buffered ≈ +10 h;
stage 2 (B1 ≈ 5 h, objective horizon ≈ 2 h, A7 refit 200 reps ≈ 33 h) ≈ +40 h; stage 3
≈ +3 h. Serial total ≈ 87 h from 10:04 IST today, i.e. through 2026-09-16 morning. Every
stage is stoppable independently by killing its controller; the parked stages do nothing
until their predecessor writes a terminal line.

**Still owed (D closure, unchanged from the 10:50 entry):** stage-1/2/3 completion
write-ups; re-review of the 42 ledger paths that changed since enumeration (at final
hash); the four gates plus lane verifiers; paper draft / reproduction / checklist
reconciliation; vault `record_work` (Logs) and the Gotchas entry.

<!-- END docs/phase6_claude_worklog_20260910.md -->

---

## <a id="rec-REGENERATION_NOTE_20260912"></a>`results/REGENERATION_NOTE_20260912.md`

<!-- BEGIN results/REGENERATION_NOTE_20260912.md sha256=684362572af433db464b1c5af974dca60f7e1d97ab4276cd67cb7b3fbe121a22 date=2026-09-12 author=Claude Opus 5 -->
# Regeneration of the reported analyses on the post-refit corpus

Written 2026-09-12 by Claude Opus 5 (Task 6 root integration, run C6).

## Why anything was regenerated

Two changes to the corpus since these files were last produced, both from the Task 6 audit:

1. **P1-01 / orbit-5 retag and refit (2026-09-11).** Six 5-node orbits (56, 57, 65, 66,
   68, 70) were retagged from hop 1 to hop 2 and every r=1 subgraph-tier cell in
   `sweep_*.csv`, `estimators/sweep_*__*.csv` and the matching `cache_oof_*` archives was
   refit (`results/RESULTS_orbit5_refit_20260911.txt`). r=0, r=2 and r=3 cells are
   column-identical to before; only r=1 moved.
2. **P2-03 / betweenness objective splice.** `analyse.load` now splices the reported
   `rf_log1p` betweenness arm into the loaded frame, so every betweenness number below is on
   the reported objective. The 2026-08/09 versions of `RESULTS.txt`, `RESULTS_failures.txt`
   and the figures carried the *raw*-objective betweenness column. **This is why betweenness
   changes at every radius, not just r=1, in the diffs** (e.g. facebook_combined r=0
   0.3038 → 0.5944 is the objective, not the refit).

Nothing else changed: same networks, seeds, folds, estimators and scripts' logic, except the
dated edits recorded in each script's docstring.

## What was regenerated, and from what

| Output | Producer (captured stdout unless noted) | Previous version kept as |
| --- | --- | --- |
| `RESULTS.txt` | `analyse.py` | `RESULTS_pre_orbit5_refit_20260901.txt` |
| `RESULTS_betweenness.txt` | `analyse_betweenness.py` (cached OOF, reported arm) | `RESULTS_betweenness_pre_orbit5_refit_20260828.txt` |
| `RESULTS_failures.txt` | `analyse_failures.py --arm reported` | `RESULTS_failures_pre_orbit5_refit_20260827.txt` |
| `RESULTS_topk.txt`, `topk_rstar.csv` | `analyse_topk.py` | `RESULTS_topk_pre_orbit5_refit_20260901.txt`, `pre_orbit5_refit_20260911/topk_rstar.csv` |
| `estimator_horizons.csv`, `estimator_shape.csv` | `analyse_estimators.py` (log: `estimators_analyse_20260912.log`) | `pre_orbit5_refit_20260911/` |
| `RESULTS_multiplicity.txt`, `multiplicity.csv` | `analyse_multiplicity.py` (done earlier this lane) | `RESULTS_multiplicity_pre_orbit5_refit_20260901.txt` |
| `fig1_locality_budget.png` | `make_fig1.py` | `pre_orbit5_refit_20260911/` |
| `fig2_failure_atlas.png` | `make_fig2.py` | `pre_orbit5_refit_20260911/` |
| `fig2_failure_atlas_betweenness_tail5.png` | `make_fig2.py --target betweenness --tail 0.05` | `pre_orbit5_refit_20260911/` |
| `fig5_coverage_confound.png` | `make_fig5.py` (`coverage.csv` itself is graph-only and unchanged) | `pre_orbit5_refit_20260911/` |
| `fig6_multiplicity_landscape.png` | `make_fig6.py` | `pre_orbit5_refit_20260911/` |

Not regenerated, because their inputs did not change: `RESULTS_features*.txt`
(`analyse_features.py`, reads the feature table, not the sweep), `RESULTS_coverage.txt`,
`coverage.csv`, `RESULTS_robustness*.txt` / `fig3` (their own historical fits — see run C8),
`RESULTS_edge*.txt`, `RESULTS_orbit04_ablation.txt`, `RESULTS_r1_subgraph_ablation.txt`
(historical three-network lanes; superseded in substance by `phase6_r1_ablation/`).

## Headline checks after regeneration

- **B2 estimator agreement is unchanged: r\* agrees with `rf` in 17/20 cells under `hgb`
  and 17/20 under `hgb_matched`** (11/20 under ridge). `estimator_horizons.csv` no longer
  lists an `rf_log1p` estimator row — it is an objective arm, not a learner, and was
  excluded on 2026-09-11 (P2-01); the 2026-09-04 file recorded 15 nonexistent cells per
  network for it.
- **A3 top-k:** overall r\*(ε) agreement between precision@k and Kendall τ moves 74.0% →
  72.0%; per target betweenness 84 → 76%, spread_cv 68 → 72%, spread_mean 68 → 60%,
  spread_resid 76 → 80%. The r=1 refit and the betweenness objective both feed this; the
  study's §24 wording is reconciled separately.
- `RESULTS.txt` P(r) tables: spread-target changes are confined to r=1 (e.g. ca-GrQc
  spread_cv 0.7074 → 0.6720, the six orbits leaving the r=1 set); betweenness changes at all
  radii for the objective reason above.

## Open item

`RESULTS_r1_subgraph_ablation.txt` (three networks, 2026-08) is superseded by the five-network
`phase6_r1_ablation/` run and its reversal (`phase6_r1_ablation_retag_delta_20260912.txt`);
it is retained as history and is not re-run.

<!-- END results/REGENERATION_NOTE_20260912.md -->

---

## <a id="rec-C3_C4_REGENERATION_NOTE_20260912"></a>`results/C3_C4_REGENERATION_NOTE_20260912.md`

<!-- BEGIN results/C3_C4_REGENERATION_NOTE_20260912.md sha256=7c55128873314b69745a524af42ddb48fd7db0777977bd4fc0e60e350c4f97ea date=2026-09-12 author=Claude Opus 5 -->
# C3 / C4 regeneration on the post-audit code (Task 6 run C7)

Written 2026-09-12 by Claude Opus 5. Pre-regeneration copies of every file named below
are in `results/c3_c4_pre_task6_20260909/` (byte-for-byte, dated 2026-09-07..09).

## Why

Task 6 findings P3-02 (`tau_floor` was the `w*sqrt(1-z^2)` approximation, not the exact
pipeline floor `cross/sqrt(S*T)`), P3-03 and P3-04 (gate-failure transcript sidecar; CSVs
written to the repo root by a relative path) changed `analyse_c3_benchmarks.py`, so its
outputs had to be re-traversed from the raw BRAVA corpus in `data/brava/` rather than
edited. `c4_two_numbers.py` reads the r=1 `cache_oof_*.npz` archives that were refit after
the orbit-5 retag (P1-01), so its smoke rows moved too.

## What ran (serial, 2026-09-12 10:22-10:38 IST)

| Step | Command | Log | Output |
| --- | --- | --- | --- |
| traversal | `analyse_c3_benchmarks.py` | `results/c3_traversal_20260912.log` | `results/RESULTS_c3_benchmarks.txt`, `results_c3_structure.csv`, `results_c3_cells.csv` (exit 0, GATE PASSED, no `GATE_FAILED` sidecar) |
| scoring | `score_c3_results.py` | `results/c7_scoring_20260912.log` | `results_c3_scored_cells.csv`, `results_c3_scored_graphs.csv`, `results/c3_scored_summary.json`, `results/c3_scored_provenance.json` |
| C4 smoke | `c4_two_numbers.py` | same log | `results/RESULTS_c4_internal_smoke.txt`, `results/results_c4_internal_smoke.csv`, `results/c4_internal_provenance.json` |
| C4 support audit | `audit_c4_support.py` | same log | `results/RESULTS_c4_support_audit.txt`, `results_c4_support_audit.csv` |
| fallback verifier | `verify_c3_fallback.py` | `results/c7_verify_c3_fallback_20260912.log` | `results/RESULTS_c3_fallback.txt`, `results/c3_fallback_nodes.csv` |
| scoring gate | `verify_c3_scoring.py` | `results/VERIFY_phase6_claude_c3_scoring_20260912.txt` | ALL CHECKS PASSED |

## Registered verdicts: unchanged, to the digit

`results/c3_scored_summary.json` is byte-identical to the 2026-09-09 copy:
P1 FALSIFIED (MAE 0.07856417907755398), P2 SUPPORTED (rho 0.8901098901098902),
P3 SUPPORTED (12/14), P4 PASSED UNDER REGISTERED CONDITIONAL. The transcript's new line
"registered floor w*sqrt(1-z^2) vs exact cross/sqrt(S*T): max gap 1.54e-06; per-graph hit
counts under the exact floor identical" is the P3-02 check: **no P3 hit flips under the
exact floor.**

## What did change, and by how much

| File | Change | Size |
| --- | --- | --- |
| `results_c3_structure.csv` | two new columns `cross_pairs`, `tau_floor_wz_approx` (P3-02); `tau_floor` now exact | max 1.5e-06 |
| same | `n_zero_shipped`, `z_shipped`, `w_shipped`, `tau_floor_shipped`, `clamped` now carry the ABCDE gate's shipped-support detail for cit-Patents (709,062 -> 709,724 zeros) and com-lj (1,150,616 -> 1,151,702); the 2026-09-07 file had `n_zero_shipped == n_zero` and `clamped=False` for both | w moves by 2.5e-04 / 3.3e-04 |
| `results_c3_cells.csv` | new column `tau_floor_registered`; shipped-support columns as above | max 2.7e-04 on `tau_all_pred_tied`/`err_tied` |
| `results/RESULTS_c3_benchmarks.txt` | timings (the traversal shared the CPU with the structural lane); the two `[support]` lines; P1 residual line for cit-Patents -0.0130 -> -0.0129, tied -0.0000 -> +0.0001 | |
| `results/RESULTS_c4_internal_smoke.txt` | r=1 betweenness smoke columns on the refit `cache_oof_*.npz` (e.g. ca-GrQc 0.7239 -> 0.7222); counts unchanged (160/160/160 per network). Code-correctness check only, raw-arm archive, never pilot evidence | <= 2e-03 |
| `results/RESULTS_c4_support_audit.txt` | floating-point tails of the shipped/structural floor deltas (1e-09) | |
| `results/c3_scored_provenance.json`, `c4_internal_provenance.json` | new SHA-256 of the regenerated inputs; the transcript key is now the posix `results/RESULTS_c3_benchmarks.txt` (was `results\\...`, P3-04); C4 also binds the refit `cache_oof_*`/`sweep_*` and the 2026-09-11 `stage2_sweep.py` | |
| `results/RESULTS_c3_fallback.txt` | only the two source hashes (`analyse_c3_benchmarks.py`, `influence/preprocessing.py`); `c3_fallback_nodes.csv` identical | |

The shipped-support numbers were already known from `audit_c4_support.py` (2026-09-07, same
709,724 / 1,151,702); what is new is that the traversal now carries them itself, so the
"P1 uses shipped target zeros; P2/P3 registered tests use structural zeros" split is
visible in one file rather than reconstructed across two.

## Not established

Whether the `c4_two_numbers.py` smoke rows should be read on the reported (`rf_log1p`)
betweenness arm rather than the raw `cache_oof_*.npz` archive is a P2-03-class labelling
question; the file states it is a code-correctness check, not evidence, and this note does
not upgrade it.

<!-- END results/C3_C4_REGENERATION_NOTE_20260912.md -->

---

## <a id="rec-phase7_continuation_20260912"></a>`docs/phase7_continuation_20260912.md`

<!-- BEGIN docs/phase7_continuation_20260912.md sha256=58e07703c640dfb25cae5c01a422e5809097fcdbaa4711b58e7dc11cac17d23c date=2026-09-12 author=Astra (GPT-6), per Rachit 2026-09-12 -->
# Plan continuation — 2026-09-12

The user's current request authorises continuing the supplied seven-lane plan.
The attached document is a plan and historical decision record, not an instruction
to override repository constraints. No commits, publication, or environment changes
are part of this continuation.

## Verified handoff

- Stage 1 structural bootstrap is live (PID 25956); 2,814/12,000 cells observed
  in its UTF-16 log during handoff. Buffered CV follows in the same controller.
- Stage 2, Stage 3, and Stage 4 controllers already exist and are waiting.
  Stage 4 includes raw/reported robustness, both figures and a reproduction verifier.
- The new local-dynamics module and Phase 7 preregistration do not yet exist.
- The directory has no Git repository. Changes will be additive where possible;
  no worktree or commit can be manufactured as evidence of isolation.
- Phase 6 D closure remains pending final run results and review at final hashes.

## Execution ledger

1. Handoff reconciliation: in progress.
2. Preregistration and L3 verifier/runner: next.
3. L3, L4, L2 standalone, L7 gate: pending in that order.
4. L1 full sweep, L5 gate/pilot, L6 MVP: pending behind Stage 4.
5. Scientific scoring, completion write-ups and final audit reconciliation: pending.

## Timing caveat

Read-only inspection began on 2026-09-12. Any single-thread verification or zero-fit
probe executed alongside Stage 1–4 shares CPU/memory resources. Consequently,
`fit_seconds` recorded during these windows is not an uncontended benchmark.
Start/end times will be recorded with the relevant probe logs. Scientific scores
are not being relabelled as timing measurements.

## Implementation rulings

- Ruling: the planned L2/L7 R² gates wait behind Stage 4 because their prescribed
  reconstruction probe fits an HGB model. Only feature computation and score
  evaluation run now. Cost: those gate verdicts arrive later than the plan claims.
- Ruling: L7 shortest-path parent ties are fractionally shared to keep features
  invariant to node relabelling; NB walk length is reported separately from the
  repo's information radius. Cost: these explicit conventions may differ from
  an unstated interpretation in the supplied plan, and are registered before data.

- Ruling: subsequent seed-set and threshold helpers will use separate modules,
  not mutate L3's source-bound local_dynamics module after its run. This preserves
  executable provenance as lanes are implemented. Cost: filenames differ from
  the plan; imports and reproduction instructions must state the actual locations.
- Ruling: Zhang positioning is corrected before execution after checking the
  published paper; the plan's fixed-dynamics and no-learner-comparison premises
  were false. The numerical hypotheses remain unchanged. Cost: a narrower novelty
  claim, accurately reflecting prior work.

- Ruling: use new files without editing hash-bound production modules while the
  queue is running. There is no Git checkout to isolate. Cost if wrong: a missed
  dependency would require a separately reviewed change and compatible rerun.
- Ruling: distinguish cached-RF historical-target scores from a fair held-out-draw
  comparison. L3's predictor uses draws 0–1999 and its target uses 2000–3999;
  existing RF predictions were trained using the full 4,000-draw targets. Their
  comparison is descriptive, not independent target-noise evidence. Cost if
  ignored: overstating the L3 gate as a clean estimator-only intervention.

<!-- END docs/phase7_continuation_20260912.md -->

---

## <a id="rec-phase7_l3_implementation_brief"></a>`docs/phase7_l3_implementation_brief.md`

<!-- BEGIN docs/phase7_l3_implementation_brief.md sha256=35be30f225e8de7d45b1b73e7a54c740b01d4b20aecf53918f6c10c0de2c5b8b date=2026-09-12 author=Astra (GPT-6), per Rachit 2026-09-12 -->
# L3 implementation requirements

Read `docs/prereg_phase7_lanes.md` L3, verification section, and preregistration
clarifications first. This task implements L3 only; no L4/L2/L7/L1/L5/L6 code yet.

Create `influence/local_dynamics.py`, `verify_local_dynamics.py`,
`probe_local_predictors.py`, `analyse_local_predictors.py`. Do not edit existing
production files: running experiments hash them. No installs, commits, subagents,
or new fitting jobs. Interpreter: C:/Users/Rachit/miniconda3/envs/influence/python.exe.
Set OMP/MKL/OPENBLAS/NUMEXPR threads to 1 for all verification/probe processes.

Tests first, with independently enumerated live-edge shortest-path fixtures for
paths, cycles, stars and disconnected draws; labels reproduce production cascades
exactly, including trivalency RNG consumption. Verify r>=diameter equals full
size, isolated seeds count one, all radii nested, p=0/1, and reject invalid inputs.
Use bounded memory and efficient sparse boolean reachability for all seeds;
avoid n-by-n-by-M storage. APIs should support label-based L4 later. Expose
percolation_labels and truncated_cascade_sizes with documented array axes.

Production runner: all five root networks using actual metadata and source paths,
assert node identity against caches and all 4000 full cascade sizes bit-identical
before accepting each network. E(r) averages draws 0..1999, test target uses
2000..3999. r=0..3. Score available perc_reach_2/3 separately. Read existing
RF cells through analyse.load(), use analyse.FULL as structural full. Do not imply
the old RF scores share the independent target protocol. Save predictor vectors
and held-out targets for L4, plus hashes of source/input files, config, timestamps,
split declaration, per-network status, and resumable outputs only under
results/phase7_local/. Resume must fail on mismatched identities. Atomic publication
where practical; reject partial/nonfinite/duplicate input records.

Analysis scores every L3 prediction/counter explicitly, preserves network-level
results and coverage side-by-side (inspect actual coverage schema). Do not write
a claim before observing it. Null/tied tau is unscored. Analysis outputs must not
silently classify missing networks as negative results.

Run the verifier, then only a bounded pilot with at most 20 draws (separate output
directory marked pilot) to measure runtime/memory; do not launch the full corpus.
The parent will review and start it. Provide a report at
docs/phase7_l3_implementation_report.md recording files, API, red/green test
commands/results, pilot timing, estimated full runtime, limitations. Return a
short status, test summary and concerns.

<!-- END docs/phase7_l3_implementation_brief.md -->

---

## <a id="rec-phase7_l3_implementation_report"></a>`docs/phase7_l3_implementation_report.md`

<!-- BEGIN docs/phase7_l3_implementation_report.md sha256=acc02ff7b7320220828670d4a86b894eadc50ad0b4cff69ead41bc69254d1c86 date=2026-09-12 author=Astra (GPT-6), per Rachit 2026-09-12 -->
# L3 implementation report — 2026-09-12

Status: DONE_WITH_CONCERNS. Implementation and bounded pilots passed; full-corpus
verification and scientific scoring remain for the parent after review.

## Files and API

- `influence/local_dynamics.py`: `live_edge_draws` yields one symmetric boolean
  sparse live graph and its component labels at a time. `percolation_labels`
  returns `[node, draw]` labels, suitable for subsequent L4 union-of-components
  queries. `truncated_cascade_sizes` returns `[node, draw, radius]` counts.
  `truncated_draw_sizes` uses batches of 256 seeds and boolean sparse products,
  avoiding integer walk-count overflow and any node-by-node-by-draw allocation.
- `verify_local_dynamics.py`: independent set/BFS fixtures for paths, cycles,
  stars, disconnected graphs and one isolated node; both symmetric conventions;
  p=0/.37/1; exact production full sizes and trivalency RNG consumption; nesting,
  radius-zero identity, sufficiently large radius, invalid inputs. Additional
  verdict tests cover missing networks, ties and inclusive counter comparisons.
- `probe_local_predictors.py`: five actual root networks, metadata source paths,
  cache node/original-ID checks, complete/nonfinite/duplicate validation, one
  exact cache comparison for every regenerated draw. Production requires 4000
  draws, seed zero, splits 0:2000 and 2000:4000, and refuses a completed network
  on any mismatch. Writes node IDs, E(0..3), held-out target and available
  perc_reach_2/3 vectors to per-network NPZ files. JSON sidecars bind inputs,
  code, split, configuration, timestamps, output hashes and status. Publication
  is atomic per file, with completed status published last. Resume checks
  identity and output hashes; an interrupted network restarts that network.
- `analyse_local_predictors.py`: explicitly scores all L3 predictions and the
  counter, retaining each network and unscored missing/tied cases. Joins the
  actual coverage median/q25/q75/share_over_half/median_ball schema by network
  and radius. Uses `analyse.load()` and `analyse.FULL`; RF reference uses the
  existing full-draw target protocol, clearly labelled descriptive. Rejects
  duplicate RF spread cells and partially populated ten-seed reference cells.

No existing production modules, environment, controllers or historical scores
were changed. No model fitting or full-corpus execution was started.

## Test-first evidence

Interpreter: `C:/Users/Rachit/miniconda3/envs/influence/python.exe`.
Before each process, OMP_NUM_THREADS, MKL_NUM_THREADS, OPENBLAS_NUM_THREADS and
NUMEXPR_NUM_THREADS were set to 1. The runner and analyser also set these before
numerical imports.

1. `python verify_local_dynamics.py`: RED with missing
   `influence.local_dynamics`, before implementation.
2. Same command after local dynamics implementation: GREEN, 2 test methods,
   0.452 seconds (30 graph/convention/probability combinations, eight draws each).
3. Added verdict tests before analysis implementation: RED with missing
   `analyse_local_predictors` (the other tests remained green).
4. Final same command: GREEN, 3 methods, 2.234 seconds including imports.

## Bounded pilots and memory

`python probe_local_predictors.py --pilot-draws 20` completed on all five
networks. Outputs are under `results/phase7_local/pilot_20/`, marked pilot.
Only the first 20 production draws were checked; these pilots do not establish
all-4000-draw identity and cannot score the preregistered claims.

| Network | 20-draw elapsed seconds |
|---|---:|
| ca-GrQc | 0.420 |
| ca-HepTh | 0.571 |
| p2p-Gnutella08 | 0.366 |
| email-Eu-core | 0.131 |
| facebook_combined | 0.443 |

Native process peak-working-set instrumentation was then added to the runner.
A separate `--pilot-draws 2` pass, under `results/phase7_local/pilot_2/`, checked
that instrumentation and the current runner. Its cumulative lifetime peak was
133.89 MiB (107.69 MiB after the first network). This includes native sparse
allocations, cache reads, imports and allocator retention; it is not per-network
incremental memory. Both pilot executions were bounded to at most 20 draws each.

The 20-draw pilot preceded the memory instrumentation edit, so its stored runner
hash differs from current source. That pilot is retained as historical timing
evidence; attempting to resume it now correctly fails identity validation. The
2-draw pilot binds the current implementation.

## Estimated runtime and remaining limits

Multiplying the 20-draw aggregate (1.931 s) by 4000/20 gives approximately
386 seconds (6.4 minutes) for the full five-network corpus, excluding outer
process startup/hash overhead. This is an inference from a very small pilot,
dominated by fixed CSV loading and compression costs; actual full execution
may differ substantially. Small pilots cannot establish the peak native memory
of the full cached target scan, although algorithmic reachability storage stays
bounded by the same batch size regardless of draw count.

Parent review and full execution remain necessary. The analyser's scientific
output has intentionally not been generated from pilot data. Analysis requires
complete applicable RF reference cells; a still-running sweep may prevent
publication until those cells are present. Existing RF targets are not the
independent half-draw target used for E(r); this comparability limitation is
explicit in the output and is not corrected by a new fit here.

Full cache reproduction is enforced by the production runner, rather than being
silently performed by the small fixture verifier. L4/L5 APIs beyond reusable
component labels and live graphs are deliberately outside this L3 task.

<!-- END docs/phase7_l3_implementation_report.md -->

---

## <a id="rec-phase7_l4_implementation_brief"></a>`docs/phase7_l4_implementation_brief.md`

<!-- BEGIN docs/phase7_l4_implementation_brief.md sha256=e7be5d66e3af90865bf621e1daa0686e4439f27d094be8dbdeb7a8ea4adaebb8 date=2026-09-12 author=Astra (GPT-6), per Rachit 2026-09-12 -->
# L4 seed-set quality requirements

Read prereg_phase7_lanes.md L4 and sequence before work. Implement after L3 review
and full run, using the local_dynamics API. No new model fits, installs, commits,
or subagents. One-thread environment and absolute influence interpreter.

Own only new influence/seed_sets.py and verify_seed_sets.py,
probe_seed_sets.py, analyse_seed_sets.py, and this task's implementation report.
Keep local_dynamics.py and verify_local_dynamics.py unchanged: L3 binds their
source identity. This is a file-placement deviation, not a scientific change.

Implement greedy_seed_set and set_spread from per-draw component labels. Training
draws 0..1999 select seeds, 2000..3999 evaluate unions. k=50. Greedy marginal gain
is expected previously uncovered component size; exact lazy greedy is acceptable,
with deterministic tie breaking by node index, and diminishing gains verified.
Don't materialise n*n*draw tensors. Greedy and oracle-top-k must both select using
the training-half draws. 'True sigma' is Monte Carlo training mean, not exact sigma
and not the evaluation half. Report this explicitly.

Compare greedy, top-k training sigma (overlap control), IC degree-discount, degree,
RF OOF spread_mean per radius and seed, and L3 E(r) rankings (always report them,
required if the L3 counter fires). RF includes node and structural-full tiers;
ten seeds separately, summarised descriptively. Existing RF training targets used
both halves, so cached RF policy evaluation is not free of target-noise reuse;
state it. Preserve the original reported metric and no claims of greedy optimality.

Outputs only results/phase7_seed_sets: seed vectors, paired per-draw set spreads,
summary and input/source/config hashes. Cache/source/node alignment fail-closed;
refuse incompatible resume and changed inputs; verify all regenerated component
sizes match existing cascade caches. Consume L3 vectors only if output hashes
validate, and record their historical source identity rather than demanding a
later helper still match its old hash. Missing networks = unscored.

Tests first: brute-force component-union oracle; exact greedy vs exhaustive greedy
on tiny fixtures, deterministic tie and k edge cases, nonincreasing gains; split
selection/evaluation independence; malformed/missing/duplicate OOF keys reject;
scoring boundaries and missing corpus. Production tests must not fit models.

Score prereg predictions: facebook oracle-top-k/greedy <.95, p2p >.98; RF reaches
.98 of r3 set spread at r<=1 everywhere. Use per-seed ratios and report the mean
curve rule, all ten seed outcomes, and disagreement. Stop branch if all five
oracle ratios >=.98: one table and no further seed-policy expansion.

Run verifier and <=20-draw pilot only. Write docs/phase7_l4_implementation_report.md
with changes, red/green command evidence, interfaces, timing/memory estimate,
scientific limitations and any deviations. Return concise status and report path.

<!-- END docs/phase7_l4_implementation_brief.md -->

---

## <a id="rec-handoff-13"></a>`HANDOFF.md#13`

<!-- BEGIN HANDOFF.md#13 sha256=9da374fbe6422cebe5b0019c47dabe224fff696d60074fb623695fc9d5bdfa3a date=2026-09-12 author=many hands, 2026-08-27 to 2026-09-12 -->
## 13. WHAT TO DO NEXT (in priority order)

> **~~Every item below requires fitting a model, and training is gated on the WSL +
> cuML move.~~ NO LONGER TRUE (2026-09-01).** The gate was measured and the GPU lost
> (section 11); fitting on the Windows `influence` env is the supported path and is
> what the B2 sweeps ran on. **The claim that "the analysis-only backlog is empty"
> was also false** when it was written - a large tranche of zero-fit work existed and
> has since been done (coverage curves, top-k arm, multiplicity control, the zero-set
> proposition). Do not trust either statement; both are kept struck through because
> the project's habit is to show corrections rather than delete them.

> ~~**NEW TOP PRIORITY, ahead of everything below (2026-09-01).** Finding 11 means every
> betweenness number in the corpus was produced under a mis-specified objective. Decide
> whether to re-sweep betweenness on a `log1p` training target - and until that is
> decided, **every betweenness τ quoted anywhere must carry "under a squared-error
> objective"**. This is a ~6 h corpus sweep and it is Rachit's call, not an agent's.
> The specific open question: **does r\*(ε) for betweenness move under a corrected
> objective?** Nobody knows. Do not guess it in a write-up.~~
>
> **DISCHARGED 2026-09-04.** Both halves are now answered and the block above is kept
> struck through rather than deleted, per the project's habit.
>
> - **The horizon question.** `probe_objective_horizon.py` measured it: **3 of 50
>   (network × target × ε) cells moved — all betweenness, all facebook, all downward**;
>   0 of 25 spreading control cells moved. It is no longer a TBC and may be quoted.
> - **The re-sweep.** Authorised by Rachit 2026-09-03 and run: 800 cells, betweenness
>   only, `estimators/sweep_<tag>__rf_log1p.csv`. Declaration and scored addendum in
>   `docs/decl_objective_resweep.md`.
> - **The cost estimate above was wrong by 4×.** "~6 h corpus sweep" assumed all four
>   targets. Only betweenness is eligible — `spread_resid` is negative on all five
>   networks and `spread_cv` is left-skewed on p2p, so `log1p` does not apply to them —
>   which makes it 800 cells and ~1.5 h.
> - ~~**THE QUALIFIER STILL STANDS.** The re-sweep produced the evidence; it did **not**
>   re-base the corpus.~~ **SUPERSEDED 2026-09-04 — the qualifier is RETIRED.** Rachit
>   adopted `rf_log1p` as the reported objective for betweenness. `sweep_*.csv` is
>   still untouched on disk, but `analyse.load()` now splices the log1p betweenness
>   rows at read time, so every betweenness number the documents quote is a
>   corrected-objective number and needs no qualifier. See section 14.

1. ~~**Expand the corpus.**~~ **DONE 2026-08-27.** `ca-HepTh` and `facebook_combined` are fully run and verified. It revised Findings 3, 4, 6 and 7 and produced Finding 10. Cost was ~70 min sweep per network (not 40), and facebook's stage-1 feature extraction is 242 s because ORCA 5-node orbits on a dense graph take 232 s of it - the one place graphlet cost really bites.

   **The obvious next corpus step, given what the additions bought:** a second *modular* network to test Finding 10's ego-network mechanism, and a second *communication* network of comparable size to email to settle whether its null residual (Finding 6) is structural or small-n. Both are now specific, motivated questions rather than "more data".

2. **Run the synthetic corpus.** `stage0_generate.py` builds it and it has never been swept. This is what turns "the horizon varies between networks" (Finding 4) and "the blind spot tracks saturation" (Finding 8) from suggestive five-point correspondences into measured relationships, by moving one structural parameter at a time. Read the gamma-uncertainty warning first (`gamma_uncertainty.py`).

   **This is now the top scientific priority, and the reason sharpened on 2026-08-27.** Finding 8 is at rho=0.900 (p=0.037) on five points, of which three generated the hypothesis - it needs points that were not used to build it. Separately, email-Eu-core is now the outlier in *two* independent places (no volatility residual - its `spread_resid` ceiling is 0.098 against 0.44-0.74 everywhere else - and it is the only network where the subgraph tier's gain peaks at r=3 rather than r=1). It is both the smallest (n=986) and the densest (<k>=32.6) network in the corpus, and five observational networks cannot separate those two explanations. The synthetic corpus can, because n and <k> move independently there. That is a specific question the generated arm answers and nothing else does.

   **A third question was added the same day, from Finding 9.** facebook_combined is the only network where the clean-trained model fails to transfer to a damaged graph for `spread_mean`, and the only explanation on offer - that dense overlapping ego-nets make uniform deletion *restructure* the triangle/conductance features rather than rescale them - is fitted to that one network. It makes a falsifiable prediction: on a generated corpus with clustering swept at fixed n and <k>, the clean-trained minus damage-trained gap should grow with the clustering coefficient. Three findings now hang on the same unrun arm.

2a. ~~**Estimator invariance (M4 / plan B2).**~~ **DONE 2026-09-01.** `ridge` and `hgb` swept across the full corpus, plus a declared post-hoc `hgb_matched` arm. Verdicts and their three caveats are in section 10. Headline: the horizon claim is estimator-stable on the **spreading** targets (17/20 cells agree), and is **not** established on betweenness - where Finding 11 explains most of the disagreement.

3. ~~**Sample efficiency (supervisor directive 5).**~~ **DONE 2026-09-04.** 5,600 cells, 4.38 CPU-hours, scored against `docs/prereg_B1_sample_efficiency.md`. The 100% arm reproduces the published sweep **bit-identically** across all 800 comparable cells, so the bespoke OOF loop is the pipeline. Headline: **the direction of the sample-efficiency effect is a property of the target, not of scarcity** - r\* falls on `betweenness` (9 DOWN / 0 UP) and rises on `spread_cv` and `spread_resid` (0 DOWN / 15 UP), with zero counterexamples either way. The plan's standing prediction is **falsified as stated**; the competing mechanism declared as P4 governs two of four targets. See section 10, Finding 12.

4. **Cross-network transfer.** Train on some networks, test on entirely separate ones. The clean answer to the known limitation that single-graph CV is not honest transfer.

5. **Angle 5 proper.** The atlas answered "how much influence lies beyond r hops". The other half - *can a node predict its own gap from local features?* - is untouched, and `boundary_porosity` and the growth ratios exist for exactly this.

6. ~~**The betweenness failure atlas.**~~ **DONE 2026-08-27.** Written up in study doc section 25 across all five networks, after fixing a `make_fig2.py` bug that had been hiding the directional variables entirely (see Finding 8). Headline: betweenness carries a much larger directional blind spot than spread_mean on four of five networks, the leading variable is usually `ego_betweenness` - a local feature the model already had - and its sign is not stable across networks. What remains open is *why* the sign flips on ca-GrQc while its same-family twin ca-HepTh goes the other way.

7. **Neural comparison.** Last, per supervision. Separate environment.

---


<!-- END HANDOFF.md#13 -->

---

## <a id="rec-phase6_buffered_cv_implementation_report"></a>`docs/phase6_buffered_cv_implementation_report.md`

<!-- BEGIN docs/phase6_buffered_cv_implementation_report.md sha256=236b27156adbacd78fc09b2e51d1304ab58f29e24a97c16a2043fffeb350900b date=undated author=unsigned -->
# Phase 6 buffered-CV harness implementation report

Status: **ready for scoped re-review** (fix round 2). No structural Moran run, corpus preflight, worker benchmark, checkpointed fit, or buffered corpus result has been launched.

## Review findings resolved

1. `probe_buffered_cv.py --benchmark-only` now first validates the immutable scientific/preflight identity, then performs one representative **non-checkpointed** canonical fit at each `rf_jobs` 1, 4, and 8. `results/phase6_buffered_cv_pilot.json` records elapsed seconds, Windows available-memory snapshots, finite-prediction checks, max absolute/scale-relative prediction and Kendall-tau differences from `rf_jobs=1`, declared equivalence tolerances, the fixed selection rule, the selected count, and the `canonical_fit_count` extrapolation. Normal execution accepts only the selected setting from a valid, hash-bound pilot. A setting is valid only when it is finite, clears the memory guard, and is numerically equivalent to `rf_jobs=1` under the predeclared `1e-10 + 1e-12 × max(1, |prediction|)` prediction bound and `1e-12` Kendall-tau bound. The scientific/preflight identity is immutable before the pilot; the selected worker setting is a distinct execution identity bound to every checkpoint.

2. The buffered preflight requires the paired structural-Moran sidecar. It rejects dynamic C6 lookalikes and verifies the structural protocol, `analyse.FULL` tier, rank residuals, lag/key space, CSV output hash, source OOF paths/hashes, and current graph/cache hashes. Preflight binds raw/cache/source hashes, immutable assignment index, and exact logical/canonical key sets into its identity. Resume recomputes every input hash, validates preflight/assignment digests, validates each plan's assignment and ID digests, and binds checkpoint generations to both preflight and execution identities.

3. Final materialization streams compact fold rows to an atomic temporary CSV. It never aggregates `test_ids`, `train_ids`, or `excluded_ids`; those remain only in the per-cell immutable archive. It reloads one cell transaction at a time and packages OOF vectors one network at a time. The final results manifest hashes the cells/folds/OOF artifacts and records exact expected cell and completed-OOF keys.

4. `analyse_buffered_cv.py` reads cells with `float_precision="round_trip"`, requires one configuration and preflight identity, validates each canonicalized row digest, and authenticates the final results and OOF manifests before producing paired descriptive contrasts. Digest canonicalization treats `None`, CSV `NaN`, and an empty CSV field as one missing value and normalizes nullable integral floats while retaining high-precision statistics.

5. The analyzer writes a distinct `phase6_buffered_cv_reported_random_reference.csv`. It loads `analyse.load(network)` at the structural tier and exact radius/seed keys, labels the result as a random-KFold versus BFS-region geometry reference, and does not add it as a paired contrast. Its provenance is the root `sweep_<network>.csv` for spreading targets and `estimators/sweep_<network>__rf_log1p.csv` for betweenness, both hashed.

## Structural-Moran resource bound

`analyse_structural_moran_correlogram.py` imports and uses `threadpoolctl.threadpool_limits(limits=4, user_api="blas")` only around its dense Moran calculation. The cap is recorded as `blas_threads: 4` in structural provenance and required by buffered preflight validation. The runner releases the residual-column list immediately after `np.column_stack`, avoiding the former redundant float64 copy before the approximately 231 MiB largest-network residual matrix calculation. This leaves the historical Moran script and global environment unchanged.

The producer now checks targets' contiguous node order, features' node order and original-ID mapping, OOF vector shape, and finite values before rank residuals are built. Its sidecar records SHA-256 hashes of each producer source module, and buffered preflight recomputes them. A non-finite observed Moran statistic or null tail area is untestable rather than a false non-significant lag.

The buffered consumer accepts only the authoritative structural-Moran settings `perms=199`, `batch=512`, and `random_seed=0`; alternate producer runs may exist but cannot drive this fixed buffered design. Regression fixtures reject a changed value for each setting.

The approved shared-null design is explicit: for each target/radius, permutations are generated from the fit-seed-0 residual vector and reused across the ten fit seeds. Every row and sidecar records `null_reference_seed: 0` and the interpretation that nonzero-fit-seed `p_perm` values are seed-0-reference tail areas; they are not separate seed-specific permutation tests.

## Validation

Executed only against constructed graphs, temporary archives, mocks, and CSV fixtures in the existing CPU `influence` environment:

```powershell
conda run -n influence python -m py_compile probe_buffered_cv.py `
  analyse_structural_moran_correlogram.py analyse_buffered_cv.py verify_buffered_cv.py
conda run -n influence python -m unittest -v verify_buffered_cv.py
```

Both commands passed. The suite has 25 tests covering deterministic BFS folds; graph buffers; infeasible/unresolved arms; matched controls and aliases; betweenness transforms; structural-sidecar rejection; checkpoint/input/assignment tamper rejection; stop/resume; streamed compact export; pilot selection; analyzer/config/digest rejection; a `0.9334276102646076` tau round-trip together with `None`/`NaN`/empty/boolean fields; and the separately labelled log1p random-CV reference.

## Required launch order after re-review

```powershell
conda run -n influence python analyse_structural_moran_correlogram.py `
  --perms 199 --batch 512 `
  --out results/phase6_structural_moran_correlogram.csv

conda run -n influence python probe_buffered_cv.py --preflight-only `
  --moran results/phase6_structural_moran_correlogram.csv `
  --moran-provenance results/phase6_structural_moran_correlogram_provenance.json

conda run -n influence python probe_buffered_cv.py --benchmark-only

conda run -n influence python probe_buffered_cv.py --rf-jobs <pilot-selected-1-or-4-or-8> `
  --stop-after-canonical-fits 1

conda run -n influence python probe_buffered_cv.py --rf-jobs <pilot-selected-1-or-4-or-8>
conda run -n influence python analyse_buffered_cv.py
```

The controlled stop/resume is still a launch gate. No action is authorized before scoped re-review accepts this round.

<!-- END docs/phase6_buffered_cv_implementation_report.md -->

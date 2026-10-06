# PROJECT HANDOFF - Local Network-Based Influence Prediction

**Status lives elsewhere since 2026-09-12.** This document is the project's knowledge:
what it is, the binding rules, the findings register (section 10), the gotchas (section
12) and the open decisions (section 14). What is running, queued, blocked or next is in
[`docs/ROADMAP.md`](docs/ROADMAP.md); what each session did is in
[`docs/LOG.md`](docs/LOG.md). Every dated "current status" paragraph below is historical
and is kept because the project shows its corrections rather than deleting them.

**Current continuation, 2026-09-12:** Task 6 source review covered all 87 ledger
paths; root integration, reruns and final-hash re-review remain incomplete.
Stage 1 structural bootstrap is running, with buffered CV next; Stages 2–4 are
queued. The five-network precision witness and corrected r=1 ablation are complete.
The supplied seven-lane plan is now being continued under
`docs/prereg/prereg_phase6_5_lanes.md` as **Phase 6.5** (naming settled 2026-09-12; the
lanes were briefly filed as "Phase 7", which keeps its plan-of-record meaning — see the
ROADMAP): zero-fit lanes may run single-threaded beside the
queue, while new fitting lanes wait for Stage 4 success. Astra's continuation ledger is
preserved at `docs/archive/phase6_record.md#rec-phase7_continuation_20260912`. The September 10 status below is historical.

Prior-work correction: see [the verified positioning note](docs/reference/prior_work.md)
before claiming novelty against Zhang (2024). The new plan's original comparison
overstated what that paper left untested.

**Current work, 2026-09-10:** complete the authorised Phase 6 evidence extension
before Phase 7. The structural bootstrap pilot passed all 120 cells; the full
12,000-cell run is underway. Buffered CV passed scoped review and 25 tests; its
finite controller is running. Its results, external precision witnesses, the
five-network radius-one ablation and a full codebase audit are still outstanding.
Follow [the extension ledger](docs/archive/phase6_record.md#rec-phase6_extension_20260908) for current status;
older completion and next-step annotations below retain their historical scope.

> **Stale artefact, 2026-09-12 (Claude Opus 5, Task 6 finding P3-03):**
> `docs/study_document.pdf` was built on 2026-08-18 and has not been rebuilt since. It
> predates sections 24.x and 26a–26k of `docs/study_doc_v2.md`, the 19b revision and every
> Phase 6 lane. **The markdown is the document of record; do not cite the PDF.**
> `docs/build_study.py` now resolves its paths relative to itself, but `weasyprint` is not
> in the `influence` environment (by design — see the script's docstring), so the PDF is
> rebuilt only on request, in a separate environment.

**Purpose of this document:** to bring a new assistant fully up to speed on an in-progress research project. Read it start to finish before doing anything. It covers what the project is, what has been built and verified, what has been measured, the decisions already made and why, and what comes next.

**Status as of handoff:** mature, verified pipeline. **Five** real networks, 171 local features across four tiers, **3,200** swept grid cells with error bars on every number, **eleven** findings, five of the six research angles delivered. Two further corpus-wide sweeps (`ridge`, `hgb`) exist under `estimators/` as the B2 estimator-invariance arm, added 2026-09-01.

**Corpus expanded 2026-08-27** — `ca-HepTh` and `facebook_combined` are now fully run (stage 1, 640-cell sweep each, all verification checks passing). This was the previous handoff's priority 1, and it did what corpus expansion is supposed to do: it **revised three existing findings and produced a new one**. Read section 10 before relying on any number from the three-network era.

**Documentation and figure correctness pass, same day.** After the corpus work, `README.md` and the study doc were checked line by line against the current code and results. Five stale claims were found in the README, one of which had silently gone from true to false when the orbit features landed (it said the richness columns were identical to four decimal places; they are not any more). More seriously, **`make_fig2.py` had a variable-selection bug that made two panels print "no directional blind spot" when their own data contradicted it** - see Finding 8. The lesson is recorded there because it generalises: the text dumps were correct the whole time and only the figure was wrong, and the figure is the artefact people actually read.

**Angle 4 re-run at five networks, same day.** `analyse_robustness.py` was run over the full 5-network corpus (2 targets x 6 damage levels x 3 draws x 4 methods) and `fig3_robustness.png` regenerated. **Finding 9 changed materially** and is rewritten below: the spreading-parity claim is now four-of-five with `facebook_combined` the exception, the degree baseline turns out to overtake the local model on *every* network rather than some, and - the strongest new result - a damage-trained model reaches parity with recomputation on the nonzero-betweenness subset on four of five. Pre-expansion outputs are archived under `results/archive_3net/`.

**This document now lives in the repository** (`HANDOFF.md`, repo root, moved out of
`~/Downloads` on 2026-08-27). Keep it there and keep it current: it is versioned
alongside the code it describes, so a claim in here and the code that contradicts it
are now visible in the same place.

**~~TRAINING IS GATED AS OF 2026-08-27.~~ UN-GATED 2026-09-01 — the gate was measured
and the GPU lost.** The 2026-08-27 decision was that nothing gets fit on the Windows
`influence` env again until the project moved to WSL + cuML on the RTX 5060. That gate
was tested rather than assumed on 2026-09-01, and the GPU came out **slower** than a
correctly-scheduled CPU run on this exact workload. Section 11 has the measurements.
Fitting on the Windows env is the supported path again, and it is what the B2 sweeps
below actually ran on.

**Three things changed on 2026-09-01 and each one invalidates something you might
otherwise quote from this document:**

1. **The GPU is rejected on measured grounds** (section 11). Not deferred, not
   pending - measured, at 0.65x the best CPU arm.
2. **B2 estimator invariance was run** - ridge and HGB across the whole corpus. Its
   verdicts are in section 10 (Finding 11) and `docs/prereg/prereg_B2_estimator.md`.
3. **The project has been optimising the wrong objective the whole time**, and the
   size of Finding 10 depends on it. See **Finding 11**. This is the largest
   correction since the tier mis-tag and it touches every betweenness number in the
   corpus. Read it before quoting any betweenness τ.

**Supersedes the previous handoff.** Where this document and the old one disagree, this one is right - several headline numbers changed after a correctness pass, and two of them changed because the earlier result was measuring the wrong thing.

---

## 1. WHO AND WHAT

**Rachit** - second-year CSE student at Mahindra University, Hyderabad. This is his first ML project. He is competent and asks sharp questions, but is new to ML specifically, so explanations should build from the ground up rather than assume familiarity with standard terminology.

**Preferences that matter:**
- Casual, direct communication. Hyphens rather than em-dashes.
- **Heavily commented code** - this is important to him and the existing codebase follows it closely. Maintain that standard. The comments explain *why*, not *what*, and several record failures that were found by testing.
- Iterative development; clarifying questions before building anything ambiguous.
- **He explicitly wants pushback when he is wrong.** Do not soften genuine technical disagreement.

**Environment:** Windows 11, miniconda. **Read section 12 before running anything** - the environment has one failure mode that costs hours if you meet it cold.

**Team structure:** Rachit works with a teammate on a heavily theoretical track (locality horizons, non-backtracking operators, targeting physics journals). Rachit owns the **empirical half**: the pipeline, the features, the targets, the experiments, the evaluation. His work produces the figures.

**Supervision:** a professor and a second faculty member. One supervision meeting (July 2026); the teammate presented and Rachit did not speak.

---

## 2. THE RESEARCH QUESTION

> Can we predict how influential a node is in an **entire** network, using only information visible in its **local neighbourhood** - its neighbours, neighbours-of-neighbours, and perhaps one hop further?

**Why the constraint matters: partial observability, NOT compute cost.** (Rewritten 2026-08-28 - the previous framing was wrong and is preserved at the bottom of this section so the change is visible.)

Influence is defined globally. The question is what happens to an observer who cannot see globally. The reason such an observer exists is **not** that the global computation is expensive:

| Target | Global cost, exact | Best known approximation |
|---|---|---|
| PageRank / eigenvector / Katz | O(m) per power iteration; routine at 10^9-10^11 edges | exact is already near-linear |
| coreness | O(m) (Batagelj-Zaversnik) | - |
| closeness | O(nm) exact | pivot / sampling schemes |
| betweenness | O(nm) (Brandes) | Riondato-Kornaropoulos (VC-dimension sampling); KADABRA (adaptive) |
| IC spread, all seeds | #P-hard exact; Monte Carlo | RIS / reverse-reachable sketches (Borgs et al.; TIM/IMM/SSA), (1-1/e-eps) guarantees at billion-edge scale |

A KDD or WWW reviewer knows this table by heart. Any framing that rests on "too big to compute" is refuted by it in one sentence, and the old defence ("controlled proof of concept") conceded the point instead of answering it.

**The obstacle that does not dissolve is not being able to see the graph.** A crawler behind an API rate limit; a node inside a decentralised protocol that knows only its own peers; a platform barred by privacy constraints from joining user data; an analyst holding a sampled subgraph with no route to the rest. **None of these can see the whole network at any compute budget.** For them "how far must I look?" is the entire question, and no amount of hardware answers it.

**Why the datasets are small on purpose - and this is now a strength, not a hedge.** We work at a scale where the true global influence is still exactly computable, because that exact value is the ground truth our local predictions are graded against. Under the partial-observability framing the small exactly-solvable corpus is the *correct instrument*: a larger corpus would remove the grader. It is not a concession that we could have gone bigger.

**Consequences that re-rank the work:**
- Radius-as-measurement becomes the centrepiece rather than a defence.
- Angle 4 (damage) is no longer a bolted-on robustness study - it is the same question under a noisy observation channel, which places it inside the measurement-error literature on centrality (Costenbader-Valente 2003; Borgatti-Carley-Krackhardt 2006; Martin-Niemeyer 2019) rather than leaving it free-floating.
- Every "we cannot compute this globally" sentence anywhere in the docs is now a bug. Grep for them.

> **Superseded framing, kept deliberately.** The previous text read: *"Real networks are too large to process globally, yet influence is defined globally. If a bounded local view recovers global importance, the method scales to networks where the global computation is impossible."* It is recorded here rather than deleted because this project's convention is that revisions stay visible - and because anyone who read the old README will otherwise wonder whether the change was noticed or merely forgotten.

---

## 3. THE NON-NEGOTIABLE RULE

**A global measurement may never appear as an input feature.**

Global quantities (betweenness, closeness, PageRank, eigenvector, Katz, coreness) are what we **predict** and what we **compare against**. They must never be model inputs.

Enforced in code, not by discipline: `assert_no_leakage()` in `influence/targets.py` runs on **every grid cell**. Current allowed exceptions: `ego_betweenness` (computed only inside the ego network), `collective_influence_1/2/3`.

**Two structural defences beyond the guard:**
- `influence/structure.py` holds global quantities and must never feed the feature matrix. Its second half (`core_numbers`, `distance_to_hubs`) is *per-node* global and therefore looks exactly like a feature - it exists only so the failure atlas can describe what locality is blind to using information the model was denied.
- The `dynamic` feature tier assumes the observer knows the transmission probability p. That is a modelling assumption, not leakage, but it sits on its own tier so no general claim can depend on it silently.

---

## 4. SUPERVISOR DIRECTIVES (binding constraints)

From the July 2026 meeting:

1. **Non-neural first.** Classical models before any deep learning. *(Held - zero PyTorch.)*
2. **Do not pay for GPU resources.** *(Held. The 2026-08-27 move to WSL + cuML uses the **local** RTX 5060, which costs nothing, so the directive is not breached - but it was written when the project was CPU-only, and a supervisor who reads "GPU" in a methods section will ask. Have the answer ready: local hardware, zero spend, and the non-neural constraint in directive 1 is untouched - cuML's RandomForest is the same family of model, not a neural one. See section 11.)*
3. **Do not trust published baselines.** Reproduce or reimplement. *(Held - see section 8.)*
4. **Add edge-level and subgraph-level features.** *(Now genuinely done: 50 edge, 74 subgraph. It was NOT done before - see section 10, Finding 3.)*
5. **Test sample efficiency** - the lab claims ~20% of nodes may suffice. *(**DONE 2026-09-04.** 5,600 cells. The answer is **target-dependent**: the ~20% claim holds cleanly for `spread_mean` (15/15 cells within 0.02 tau) and **fails for `spread_resid`** (3/15). See section 10, Finding 12.)*
6. **Feature-extraction compute is the main bottleneck.** *(Addressed: merged traversal gave 4-8x, verified bit-identical.)*

The professor also described the locality-budget experiment and said *"you have one result already with you."* That plot exists and is now `results/fig1_locality_budget.png`, with error bars.

---

## 5. NOVELTY POSITIONING

"Local features + GNN + spreading ground truth" is a crowded, five-year-old setup. A 2025 paper (1D-CGS) does almost exactly the naive version.

**What survives:** across that literature the radius is chosen ad hoc and justified after the fact. **Nobody sweeps the radius as a controlled variable, measures where it saturates, or asks whether different influence definitions need different radii.**

**Framing discipline:** never say "we use local features to predict influence." Say **"we treat the neighbourhood radius as a measured quantity rather than a hyperparameter."**

**Honest claim set:**
- We do NOT claim to have invented local influence prediction.
- We DO claim: radius as a measured object, with uncertainty; a characterisation of the blind spots; the observation that **graphlet orbits carry different radii** and should not be added as one block; replication discipline.

---

## 6. THE SIX RESEARCH ANGLES

| Angle | Status |
|---|---|
| 1 - Locality budget: how far must you look? | **Done.** P(r), r*(eps) with seed stability, paired marginal gains |
| 2 - Multi-target contrast | **Done.** Four targets; they have genuinely different horizons |
| 3 - Failure atlas: what is locality blind to? | **Done.** Section 25 of the study doc |
| 4 - Robustness under damage | **Done**, including the train-on-damaged control |
| 5 - Locality gap | **Partly** - answered as a by-product of Angle 3; the "can a node predict its own gap" half is open |
| 6 - Spread volatility | **Done.** Both `spread_cv` and the variance residual |

---

## 7. WHAT HAS BEEN BUILT

A Python package `influence/` of ten modules and 19 runner/analysis scripts, all heavily commented. Zero PyTorch.

| Module | Responsibility |
|---|---|
| `preprocessing.py` | Loading + the six-decision cleaning protocol; the `Network` container |
| `features.py` | **171 features**, hop/tier/cost-group tagged, one shared traversal |
| `dynamics.py` | IC and SIR simulators, three edge-probability conventions, full distributions |
| `criticality.py` | Non-backtracking operator, Ihara-Bass form, beta_c |
| `targets.py` | Ground truth, variance residual, the leakage guard |
| `experiment.py` | Metrics, out-of-fold prediction, the sweep, the cost model |
| `generators.py` | Synthetic networks - the structural control arm |
| `structure.py` | Whole-network descriptors **and** per-node globals for the atlas |
| `graphlets.py` | ORCA orbit counts, their **measured** radius tags, brute-force reference |
| `robustness.py` | Damaged views for Angle 4 - the only place LCC restriction is skipped |

**Runners, in order:** `fetch_data.py` -> `stage0_generate.py` -> `stage1_prepare.py` -> `stage2_sweep.py` -> `analyse.py` / `make_fig1.py` -> `analyse_failures.py` / `make_fig2.py` -> `analyse_robustness.py` / `make_fig3.py`.

**Standalone analyses:** `analyse_features.py` (feature-table audit), `analyse_betweenness.py` (the tie-block), `analyse_edge5.py` (the 5-node edge orbit test), **`analyse_edge_tier.py --tier {edge,subgraph}` (which cost-group inside a given rung carries the gain, per network - the Finding 10 tool; run BOTH rungs)**, `gamma_uncertainty.py`. `_calib.py` and `_calib_edge.py` re-derive the orbit radius tables.

**Outputs:** `results/` holds `RESULTS*.txt` for each analysis plus three figures - `fig1_locality_budget.png`, `fig2_failure_atlas.png`, `fig3_robustness.png`.

**Verification:** `verify_pipeline.py` (43 checks) and `verify_generators.py` (6 checks). Both must print `ALL CHECKS PASSED`.

### 7.1 The cleaning protocol (six decisions, applied identically)

1. Symmetrize (stated, not silent)
2. Restrict to largest connected component
3. Remove self-loops
4. Collapse multi-edges
5. **Discard weights entirely**
6. Reindex to 0..n-1, keeping the mapping

Every step logged into a provenance dict. `robustness.py` deliberately skips step 2 - see section 12.

### 7.2 The two tagging axes

Every feature carries **hop** (smallest radius that can compute it) and **tier** (`node` / `edge` / `subgraph` / `dynamic`), plus a **cost group** naming the timed block that produced it. The radius sweep is a one-line filter.

**Any new feature must be registered with all three or it silently vanishes.**

### 7.3 The 171 features (170 reachable)

| Tier | Count | What |
|---|---|---|
| node | 45 | degree, clustering, ego structure, neighbour aggregates, H-index ladder, Collective Influence, shells, local gravity, entropy, ClusterRank, semi-local centrality |
| edge | 48 | embeddedness and overlap distributions, **12 ORCA edge orbits x 3 statistics** |
| subgraph | 76 | ego-betweenness, ball-internal edges, 2-ball density and conductance, **71 ORCA 5-node node orbits** |
| dynamic | 2 | truncated local percolation estimate (assumes knowledge of p) |

Cumulative by radius: 2 at r=0, **56** at r=1, **145** at r=2, **170** at r=3. One feature sits at hop 4 and is never selectable at `max_hop=3`. *(r=1 was 62 until 2026-09-11, when six 5-node orbits were retagged from hop 1 to hop 2 and the r=1 subgraph-tier cells refitted - Claude Opus 5, Task 6 finding P1-01, study §26k.3.)*

**Tier correction, 2026-08-31.** The edge/subgraph split was 50/74 until a project-wide code audit moved `ball2_density` and `local_conductance_2` into the subgraph tier. They aggregate the edges **among** 2-ball members, not the node's own incident edges - and §6.4 defines the edge tier as "the distribution of structure across a node's incident edges". `ball2_edges`, computed from the *identical* array, was already tagged subgraph; one array in two tiers was not defensible.

It was not cosmetic. The richness ladder is nested, so with those two in the edge tier the `node+edge` rung at r>=2 could reconstruct `ball2_edges` exactly (verified to 5e-12 / 3e-11 / 3e-10 on ca-GrQc / email / facebook, by two independent algebraic routes). The structure-blind rung was reading 2-ball structure. 400 of the 3,200 sweep cells - `node+edge` at r=2 and r=3 - were refitted; the other 2,800 are bit-identical and untouched. **Finding 10 (§26a) is the claim this rewrites** - see that section.

Orbit columns by hop, measured by `_calib.py` / `_calib_edge.py`:

| | hop 1 | hop 2 | hop 3 | hop 4 | total |
|---|---|---|---|---|---|
| node orbits (5-node ORCA) | 22 | 37 | 11 | 1 | **71** |
| edge orbit columns (12 orbits x 3 stats) | 9 | 24 | 3 | - | **36** |

**Why 71 node orbits and not 73 - the answer, since the docs did not previously carry it.** ORCA emits **73** node orbits for graphlets on up to 5 nodes (0-72). Two are excluded deliberately because they are *exactly* columns the table already has:

- **orbit 0 == degree**
- **orbit 3 == triangle_count**

Including them would put duplicate columns in the table and inflate the subgraph tier with nothing. Enforced by `REDUNDANT_ORBITS = (0, 3)` in `influence/graphlets.py` (the reasoning has always been in that file's comments - it was only the handoff and README that were silent). Additionally, any orbit identically zero on a given graph is skipped, since a constant column carries no information and inflates the count.

**The complete chain, so no step is left implicit** (measured across all five networks, 2026-08-31):

| step | count | why |
|---|---|---|
| ORCA 5-node node orbits | **73** | orbits 0-72, ORCA's full output |
| less redundant | −2 | orbit 0 = `degree`, orbit 3 = `triangle_count` |
| less all-zero on this graph | −0 | the zero-skip rule exists, but **fires on none of the five networks** - every one of the 71 is non-constant everywhere |
| **registered in the table** | **71** | what the subgraph tier claims |
| less above `MAX_HOP` | −1 | orbit 15, the induced-P5 endpoint, has eccentricity 4 |
| **selectable in any sweep cell** | **70** | what a model can actually be given |

The 71 → 70 step is the one nobody had written down. Orbit 15 is registered rather than deleted on purpose: deleting it would quietly convert "we measured this orbit's radius and it fell out of range" into "this orbit does not exist", and raising `MAX_HOP` to 4 would bring it in with no other change. `verify_docs.py` asserts both that exactly one feature sits above `MAX_HOP` and that the zero-skip fired zero times, so if either ever changes the documents fail rather than drift.

*An external review flagged the unexplained 73 -> 71 gap as exactly the kind of loose end a referee pulls on - and it was right that the documents could not answer it, even though the code could. After the ORCA paw-orbit incident, orbit accounting is the last place this project should be taking anything on trust.*

**Optional:** `edge_graphlet_size=5` adds 5-node edge orbits, taking the table to 339 columns. Off by default - see section 14. Its radius calibration is 16 at r1, 39 at r2, 12 at r3, 1 at r4 = **68**, which is ORCA's full 5-node edge-orbit count (no exclusions there, since no edge orbit duplicates an existing column).

### 7.4 The percolation shortcut

Independent Cascade with fixed per-edge probability **is** bond percolation. One live-edge sample gives a sample for **all n seeds simultaneously**. Measured ~900x. Exact for symmetric conventions (uniform, trivalency); does NOT hold for weighted cascade. Both paths implemented and verified to agree.

### 7.5 The merged traversal

Shell statistics, Collective Influence, gravity, ball-internal structure and the percolation estimate all come from **one BFS per node**. Previously four separate walks - 78-94% of feature-extraction time. Verified **bit-identical** against the separate reference implementations, which are retained precisely so the check can be repeated.

---

## 8. VERIFICATION

Nothing is asserted, only checked against an independent reference.

| Implementation | Checked against | Result |
|---|---|---|
| degree, clustering, triangles | networkx | exact |
| ego-betweenness | brute-force betweenness on ego subgraphs | 2e-11 |
| ego-betweenness fast path | the set-based reference | 1.7e-14 relative |
| Ihara-Bass eigenvalue | direct 2m x 2m non-backtracking matrix | 1e-9 |
| Brandes betweenness | networkx | 1e-14 |
| percolation shortcut | direct per-seed IC | r = 0.9993 |
| SIR with mu=1 | Independent Cascade | 0.4% |
| merged traversal | separate reference implementations | **bit-identical** |
| **graphlet orbits (ORCA)** | **our own induced-subgraph enumeration, four graph families** | **all 15 orbits exactly identical** |
| core_numbers | igraph coreness | exact |
| trivalency probabilities | percolation path vs direct path, same seed | identical |
| leakage guard | deliberate injection of forbidden names | all caught |
| structural measures, power-law MLE, generators | networkx / known-exponent synthetic data | 1e-14 or better |

**Two errors were caught this way, and both would have been invisible otherwise:**
- ORCA numbers the **paw** graphlet opposite to the obvious guess (degree-2 triangle nodes are orbit 10, the degree-3 hub is orbit 11). The brute-force check disagreed on exactly those two orbits and nothing else. Two orbits would have carried the wrong radius tag.
- The H-index ladder converges to coreness **from above**, not below. A verification check written with the inequality the wrong way round failed and exposed it.

---

## 9. CHOOSING THE TRANSMISSION PROBABILITY (solved - do not relitigate)

Fixing p at an absolute value compares different dynamical regimes. Picking the p that maximises score spread is confounded with scale.

**In use:** compute each network's own epidemic threshold beta_c from the **non-backtracking operator** (Ihara-Bass 2n x 2n form), then work at a fixed *multiple* of it.

| Network | beta_c (non-backtracking) | beta_c (adjacency) | beta_c (mean-field) |
|---|---|---|---|
| ca-GrQc | 0.02250 | 0.02192 | 0.05889 |
| **ca-HepTh** | **0.03333** | **0.03222** | **0.08341** |
| email-Eu-core | 0.01338 | 0.01311 | 0.01358 |
| **facebook_combined** | **0.00620** | **0.00616** | **0.00947** |
| p2p-Gnutella08 | 0.03772 | 0.03524 | 0.06004 |

Mean-field is wrong by 2.6x on the sparse networks - concrete evidence the non-backtracking operator is necessary.

**The two new rows were added 2026-08-28**, read from `cache_meta_ca-HepTh.json` and `cache_meta_facebook_combined.json` (exact values 0.033326089293547044 and 0.006200284107725097). Until then this table had three rows while the corpus had five, so the document **could not demonstrate that the two new networks were in the regime it mandates** - the single most load-bearing methodological claim in the project, undocumented for the two networks that revised four findings.

**Completed 2026-09-08:** the four missing adjacency/mean-field thresholds were computed
with `influence.criticality.epidemic_threshold` on the normal preprocessed edge lists.
Exact outputs are in `results/phase6_threshold_comparison.json`. No training or target
cache changed. For these two graphs the adjacency estimate is close to the
non-backtracking estimate; the mean-field estimate is higher, especially on ca-HepTh.

**All five networks run at p = 1.5 x beta_c, 4,000 sims, uniform convention** - verified 2026-08-28 by reading `multiple`, `n_sims` and `convention` from all five `cache_meta_*.json`, not from memory. They did not always: email-Eu-core was at 1.2x, which reintroduced exactly the confound the normalisation exists to remove. That cache is kept in `cache_archive/` because the two runs together start a p-multiple sweep worth doing properly.

---

## 10. RESULTS SO FAR

**Five** networks, all cleaned by our own pipeline, all at identical dynamical settings. **Every cell is run at 10 seeds**; every number below carries a spread. Marginal gains are computed **paired within seed**.

> **Read the per-finding scope line before quoting any number in this section.** The corpus is five, but not every experiment has been re-run at five - the sweep, the failure atlas and Angle 4 have; the r=1 subgraph ablation behind Finding 3 has not. Findings now carry an explicit "measured on" line so the two cannot be confused.

> **Numbers in this section: which are still current (2026-09-12, Claude Opus 5, Task 6
> root integration).** Two changes since these tables were written on 2026-08-28:
>
> 1. **Betweenness is now reported on the `log1p` objective** (study §26b/§26d, adopted
>    2026-09-04; Task 6 finding P2-03 made the analysis scripts read that arm by default).
>    Every betweenness τ below is the retired raw-squared-error arm, on which the forest
>    was badly mis-specified on the dense networks. Reported-arm endpoints, richest tier,
>    r=0 → r=3: ca-GrQc 0.5560 → 0.9283, ca-HepTh 0.6611 → 0.9199, email 0.7831 → 0.9134,
>    facebook **0.5944 → 0.9303**, Gnutella 0.8848 → 0.9387. The facebook r=0 baseline of
>    0.3038 quoted twice below is the raw-arm number; the degree baseline is still the
>    weakest of the five, but by 0.19 rather than 0.44. Facebook's r\*(ε=0.02) for
>    betweenness is now **2**, not 3 (email stays 1), so the matched-dense-pair argument
>    under Finding 6 survives with a smaller gap: the denser network still has the longer
>    horizon and the weaker baseline.
> 2. **Every r=1 cell of the subgraph-inclusive tiers was refit on 2026-09-11** after six
>    5-node orbits were retagged hop 1 → hop 2 (finding P1-01). r=0, r=2 and r=3 cells are
>    untouched, so every r=3 number below for the spread targets is still exact; the r=1
>    numbers and the two marginals that touch r=1 are not. Finding 1's ca-GrQc table,
>    regenerated from `results/RESULTS.txt`:
>
> | Target | base | r0->r1 | r1->r2 | r2->r3 |
> |---|---|---|---|---|
> | betweenness (log1p arm) | 0.5560 | +0.3638 * | +0.0091 * | −0.0005 |
> | spread mean | 0.7807 | +0.1266 * | +0.0343 * | +0.0025 * |
> | volatility | 0.4598 | +0.2122 * | +0.1325 * | +0.0159 * |
> | volatility residual | 0.2240 | +0.2745 * | +0.1537 * | +0.0194 * |
>
> The r=1 hop lost 0.013–0.035 τ on the spread targets and the r=2 hop gained the same
> amount — the six orbits were hop-2 quantities doing hop-2 work under a hop-1 label.
> Betweenness is still the one target whose last hop buys nothing. Finding 2's r\*(ε)
> ladder for ca-GrQc spread mean (0 / 1 / 2 at ε = 0.20 / 0.10 / 0.02) is unchanged.
> `results/RESULTS.txt` is authoritative; the 2026-08-28 file is kept as
> `results/RESULTS_pre_orbit5_refit_20260901.txt`, and `docs/archive/phase6_record.md#rec-REGENERATION_NOTE_20260912`
> lists every regenerated artefact with its archived predecessor.

**The corpus:**

| Network | n | m | mean degree | character |
|---|---|---|---|---|
| ca-GrQc | 4,158 | 13,422 | 6.46 | sparse collaboration |
| **ca-HepTh** | **8,638** | **24,806** | **5.74** | **sparse collaboration (same-family replicate of ca-GrQc)** |
| email-Eu-core | 986 | 16,064 | 32.58 | dense communication |
| **facebook_combined** | **4,039** | **88,234** | **43.69** | **dense social, union of ego networks** |
| p2p-Gnutella08 | 6,299 | 20,776 | 6.60 | sparse peer-to-peer |

The two additions were chosen to be a **matched pair on each arm**, not just more data. ca-HepTh is the same generative process as ca-GrQc at near-identical density, so it tests replication. facebook_combined is a second dense network to set against email-Eu-core, so it tests whether "dense" was ever the operative variable. Both tests returned informative answers - see Findings 4 and 6.

**Locality budget, richest structural tier, Kendall tau:**

| | ca-GrQc | ca-HepTh | email-Eu-core | facebook_combined | p2p-Gnutella08 |
|---|---|---|---|---|---|
| spread mean r=0 -> r=3 | 0.7807 -> 0.9441 | 0.7228 -> 0.9508 | 0.8619 -> 0.9687 | 0.6705 -> 0.9586 | 0.6705 -> 0.9159 |
| betweenness r=0 -> r=3 | 0.5422 -> 0.9216 | 0.6611 -> 0.9162 | 0.7429 -> 0.9030 | **0.3038 -> 0.8514** | 0.8853 -> 0.9367 |
| volatility r=0 -> r=3 | 0.4598 -> 0.8206 | 0.3282 -> 0.8220 | 0.8563 -> 0.9629 | 0.1438 -> 0.8360 | 0.4560 -> 0.7793 |
| volatility residual r=3 | 0.6715 | 0.7191 | 0.0802 | **0.7378** | 0.4375 |

### Finding 1 - different targets have different horizons (THE HEADLINE)

Marginal gain per hop, ca-GrQc, paired, starred where it beats twice the seed sd:

| Target | base | r0->r1 | r1->r2 | r2->r3 |
|---|---|---|---|---|
| betweenness | 0.5422 | +0.3759 * | +0.0034 * | +0.0000 |
| spread mean | 0.7807 | +0.1400 * | +0.0209 * | +0.0025 * |
| volatility | 0.4598 | +0.2475 * | +0.0972 * | +0.0160 * |
| volatility residual | 0.2240 | +0.3060 * | +0.1223 * | +0.0193 * |

Betweenness is the only target whose final hop buys nothing measurable. On Gnutella **every** gain at **every** radius is still significant at r=3.

**The error bars sharpen this rather than softening it** - at one seed, "+0.0025" and "+0.0000" would be indistinguishable claims.

### Finding 2 - r* depends on the tolerance, and sometimes on the seed

r*(eps) for ca-GrQc spread mean: **0** at eps=0.20, **1** at 0.10, **2** at 0.02. And r* is now reported with **seed stability** - where signal is strong it is 10/10, where weak (email's volatility residual) it drops to 7/10, meaning the reported radius is close to a coin flip. **Always report the full P(r) curve, the marginal-gain table, and r*(eps) with its stability.**

### Finding 3 - depth beats richness, but richness is not nothing (REVISED TWICE)

**The original version of this finding was vacuous.** Five of the six edge/subgraph features were exact algebraic functions of node-tier features - `triangle_count = clustering x k(k-1)/2`, `ego_net_edges = triangle_count + k`, and so on. `node -> node+edge` **could not** have shown a gain. The measured zero was a property of the ladder, not the world.

**Measured on: ca-GrQc, email-Eu-core, p2p-Gnutella08 (three of five).** The r=1 subgraph decomposition behind this finding predates the corpus expansion and has **not** been re-run on ca-HepTh or facebook_combined - see the scope note at the end of this finding.

With a ladder that genuinely varies, subgraph structure **does** help the dynamical targets on all three networks it was run on - and mostly at **radius 1**:

| Network | target | subgraph gain at r=1 |
|---|---|---|
| ca-GrQc | volatility | **+0.0354** * |
| ca-GrQc | spread mean | **+0.0134** * |
| p2p-Gnutella08 | spread mean | **+0.0093** * |
| email-Eu-core | volatility | **+0.0044** * |

**And it is the 4-node to 5-node step, nothing else.** Ablating at r=1, ten seeds, on those same three networks (`results/RESULTS_r1_subgraph_ablation.txt`): the pre-ORCA subgraph features contribute ~0.0000, the five 4-node hop-1 orbits contribute ~0.0000, and the seventeen extra **5-node** hop-1 orbits contribute the entire effect. **Four-node graphlets are not expressive enough to describe an ego network.**

> **SCOPE GAP, flagged 2026-08-28 - do not quietly upgrade this to "five networks".** An external review listed this finding's "all three networks" as a stale doc claim to be corrected to five. It is **not** stale: the ablation genuinely covers three, and `results/RESULTS_r1_subgraph_ablation.txt` contains exactly three blocks (Gnutella, email, ca-GrQc). Rewriting the number would have converted an honest statement into a false one.
>
> That said, the gap is real and it matters more than it looks. **Finding 10 established that feature-group value is a property of the network, not the feature group** - the subgraph tier is worth +0.1291 on facebook and +0.0014 on Gnutella. There is therefore no basis for assuming the 4-node-to-5-node result generalises to the two unrun networks, and facebook is exactly the network where a subgraph result would be most likely to behave differently, since it is the one built of overlapping dense ego-nets. **Re-running this ablation on ca-HepTh and facebook_combined is cheap** (r=1 only, ten seeds, four feature sets) and it is the missing control for the project's second-most-cited finding.

> **SCOPE GAP CLOSED, 2026-09-11 by Claude Opus 5.** The missing control was run: 800 fresh
> out-of-fold cells, **five** networks x four targets x four nested feature sets x ten paired
> seeds, r=1, betweenness on the reported `rf_log1p` objective. Artifacts in
> `results/phase6_r1_ablation/`, `run_id afadc675...4441`; write-up in study §26k.3 and
> `docs/archive/phase6_record.md#rec-phase6_r1_ablation_implementation_brief`. No historical `cache_oof` endpoint was
> reused - they carry no manifest, column list, fold digest or objective id.
>
> **The note above was right to refuse the upgrade, and right about facebook being the network
> to watch - but the surprise landed on email, not facebook.** The 4-node-to-5-node result does
> generalise: `add_orbit_lt15` flags 0 of 20 cells and `add_remaining_g5_orbits` 17 of 20,
> facebook_combined included (spread_mean +0.01036, spread_cv +0.00607, spread_resid +0.01200,
> betweenness +0.00377, all flagged). Two things the three-network run could not see:
>
> - "the pre-ORCA subgraph features contribute ~0.0000" is **too strong**. That step flags on
>   two cells and both are `betweenness` - email-Eu-core +0.00254 and facebook_combined
>   +0.00349 - a target the original three-network tables did not contain.
> - On **email-Eu-core/`betweenness` the 5-node step is negative**: -0.00049, sd 0.00037, nine
>   of ten seeds worse. Below the flag threshold, but opposite in sign to every other network,
>   and kept as an exception rather than folded into the positive summary.
>
> Radius one only. The stars are the descriptive |mean| > 2*sd heuristic over ten seeds: no
> null distribution, no multiplicity correction over 60 contrasts, and ten seeds on one graph
> are not ten graphs.

> **REVERSED, 2026-09-12 by Claude Opus 5 (Task 6 finding P1-01, run C2).** The run above
> and the three-network table above it were fitted with six 5-node orbits (56, 57, 65, 66,
> 68, 70) tagged hop 1 although they reach two hops. Rerun on the corrected registries
> (`results/phase6_r1_ablation/`, `run_id c66485a6...299f`; pre-retag run archived at
> `results/phase6_r1_ablation_pre_orbit5_retag_20260910/`; diff in
> `results/phase6_r1_ablation_retag_delta_20260912.txt`):
>
> - `add_remaining_g5_orbits`: **17 of 20 -> 0 of 20**. Largest |mean| now 0.00054 tau; the
>   sum of the twenty means falls from +0.187 to +0.0004. **"Four-node graphlets are not
>   expressive enough to describe an ego network" is withdrawn at radius one.** The gain was
>   a radius effect mislabelled as a graphlet-size effect - the same failure class as
>   Finding 10's "+0.148 edge tier".
> - `add_nonorbit_subgraph` 2 of 20 and `add_orbit_lt15` 0 of 20: **unchanged**, means equal
>   to ~1e-7 (those columns did not move; this is the control on the rerun).
>
> The subgraph-gain table at the top of this finding (+0.0354 ca-GrQc volatility etc.) is a
> whole-tier r=1 number from the same shallow tag. Recomputed on the refit sweep
> (`results/subgraph_gain_pre_post_retag_20260912.txt`, same paired construction): every
> r=1 spread-target gain is within +/-0.0008 of zero and none clears 2 sd - **ten for ten
> becomes zero for ten** - while the r=2/r=3 columns are unchanged to the last digit. The
> subgraph tier's surviving gains are +0.001 to +0.006 at r >= 2 on the spread targets and
> the facebook betweenness rung at r=2 (Finding 10). Study §20 and §26k.3 carry the full
> statement.

**Depth still wins by roughly an order of magnitude** - +0.376 for one hop against +0.035 max richness. *(2026-09-12: the +0.035 was the shallow-tag r=1 subgraph gain; see the reversal above.)* But "richness is worthless" was an artefact of asking with too poor a vocabulary, twice.

> **REVISED A THIRD TIME (2026-08-27).** That order-of-magnitude ratio is not a constant - it is a property of the network. On facebook_combined betweenness the comparison is +0.197 (one hop) against **+0.160** (richness at fixed radius): the same order of magnitude. Depth still wins on average and wins outright on every sparse network, but the claim must be stated per-network. See Finding 10.

### Finding 4 - the horizon is a property of the network, NOT of its density (STRENGTHENED)

The old version rested on one coincidence: ca-GrQc and Gnutella have the same mean degree and behave differently. The two new networks were chosen to break that argument if it was wrong. It held, and got much stronger.

**The same-family replicate.** ca-HepTh and ca-GrQc are both arXiv collaboration graphs (mean degree 5.7 vs 6.5). Their r*(eps=0.02) profiles agree on **three of four targets exactly**, and differ by one hop on the fourth - which is the one cell where ca-GrQc's own seed stability was weakest (7/10, a near coin-flip). Both curves have the same shape and the same longest-horizon target. **This is the project's first genuine replication.**

**The matched dense pair, where the density hypothesis dies.** facebook_combined (43.7) is *denser* than email (32.6). On betweenness it behaves in the opposite direction:

| | email-Eu-core | facebook_combined |
|---|---|---|
| betweenness tau at r=0 | 0.7429 | **0.3038** |
| r1->r2 marginal gain | +0.0056 | **+0.1970** |
| r*(eps=0.02) | 1 | **3** |

The denser network has the **longer** horizon and the far weaker degree baseline. Density cannot be the explanatory variable. Structural reason: facebook_combined is a union of ego networks, so betweenness is about the bridges between friend groups, and degree measures how big your friend group is - which says nothing about whether you are a bridge.

**Still cannot claim** that *family* is causal - five observational networks cannot separate family from modularity, clustering and degree-tail shape, which all co-vary with it. The synthetic corpus remains the instrument for that.

### Finding 5 - discriminability peaks near criticality

Degree-vs-spread correlation on email dips to a **minimum near criticality** (0.860 at 1.0x beta_c, rising to 0.960 at 5x) - exactly the regime where looking beyond degree pays most.

### Finding 6 - volatility beyond the mean: email is the exception, and it is NOT a density effect (REVISED)

`spread_resid` (volatility with the mean regressed out) at r=3, all five networks:

| facebook_combined | ca-HepTh | ca-GrQc | p2p-Gnutella08 | email-Eu-core |
|---|---|---|---|---|
| **0.7378** | 0.7191 | 0.6715 | 0.4375 | **0.0802** |

The old version said the objection "is correct for the dense network and wrong for the sparse ones", generalising from one dense network to density as such. **facebook_combined falsifies that directly**: it is the densest graph in the corpus and has the *largest* residual signal of all five - an order of magnitude above email, in the direction opposite to what density predicts.

Correct statement is the narrow one: **email-Eu-core is the network where volatility is the mean in disguise**, and density does not explain it. Four of five retain a large predictable residual.

**Explicitly unresolved:** email is also by far the smallest graph (n=986 vs 4,039-8,638) and has the largest seed spread in the table (+/-0.0137, ~8x ca-HepTh's). A residual that is mostly noise cannot be predicted by anything, so a near-zero tau is exactly what small-n would look like. Whether email's null is structural or an artefact of 986 nodes **is not resolved by this corpus** - do not assert either way until a second communication network of comparable size is run.

### Finding 7 - the betweenness result needs a stated caveat

`betweenness(v) = 0` **if and only if** `ego_betweenness(v) = 0`, verified on all 11,443 nodes with zero mismatches. **Report tau on the nonzero subset too** - on ca-GrQc it drops 0.92 -> 0.73.

**The five-network corpus sharpens this a lot.** The zero-inflation is not a fixed nuisance - it ranges from 71% of scored pairs down to 16%, and it varies *inversely* with how hard betweenness actually is:

| network | betweenness = 0 | share of tau-b's scored pairs that are zero-vs-nonzero |
|---|---|---|
| ca-GrQc | 55.0% | 71.0% |
| ca-HepTh | 48.5% | 65.4% |
| p2p-Gnutella08 | 27.8% | 43.5% |
| email-Eu-core | 15.1% | 26.3% |
| **facebook_combined** | **8.5%** | **15.6%** |

The two collaboration graphs, where tau looks best (0.92 at r=3), are exactly the two where two thirds of the score is the zero/nonzero question - which has an **exact local answer**. facebook_combined, at 16%, is the cleanest betweenness measurement in the corpus, and it is also where locality does **worst**: 0.30 on degree alone, only 0.85 at r=3, r*=3.

So the ordering reverses. **The corpus-wide impression that "betweenness saturates early" is substantially an artefact of which networks were in the corpus** - it does not hold on the one graph where the metric is not doing the work for us.

### Finding 8 - the blind spot appears where the horizon has not been reached

Failure atlas (`analyse_failures.py`). The **directional** blind spot - what decides whether a node is under- or over-predicted - tracks saturation:

Re-measured on all five, target `spread_mean`, 171 features (2026-08-27):

| Network | final hop still buys | max Cliff's d, directional |
|---|---|---|
| facebook_combined | +0.0012 | **0.146** (none) |
| ca-GrQc | +0.0025 | **0.122** (none) |
| ca-HepTh | +0.0047 | **0.185** (weak) |
| email-Eu-core | +0.0049 | **0.319** (medium) |
| p2p-Gnutella08 | +0.0292 | **0.403** (medium) |

**Spearman rho = 0.900, p = 0.037, n = 5.** The correspondence survived both the corpus doubling and the feature set going 64 -> 171.

Do not over-read that. Three of those five points *generated* the hypothesis and cannot also test it. Out-of-sample it is one clean hit (ca-HepTh, predicted mid, measured mid) and one near miss (facebook, predicted smallest, measured second smallest). The single inversion in the table is exactly that facebook/ca-GrQc pair, and their gains differ by 0.0013. At n=5 one swap drops rho to 0.7.

On Gnutella the driving variable is **spread / visible ball** - the under-predicted nodes are exactly those whose cascade escapes everything they can see. That is the Angle 5 locality gap, measured directly, falling out of the failure analysis rather than being assumed. The same variable leads on ca-HepTh and facebook too.

**Betweenness behaves differently and it matters.** Directional d is far larger on betweenness than on spread_mean on four of five networks (ca-GrQc 0.334, ca-HepTh 0.421, email 0.911, facebook 0.735; Gnutella reverses at 0.286 vs 0.403). The leading variable is usually `ego_betweenness` - a local feature the model HAD. So on the spreading targets the blind spot is explained by information the model was denied, and on betweenness by information it already had and is not using at the tails.

The sign is NOT stable: on ca-GrQc the locally-bridge-like nodes are the ones the model over-rates; on ca-HepTh, email and facebook they are the ones it under-rates. ca-HepTh is the same family as ca-GrQc and goes the other way, which kills the easiest explanation. Do not write "high local bridging => under-ranked" as a law.

**A bug was hiding all of the above until 2026-08-27.** `make_fig2.py` drew its directional row using the variable set ranked by the row above it (a different contrast over a different node set). A variable that separates the two tails from each other can be flat against the middle, because it pushes the tails in opposite directions and they cancel - so the selection systematically hid precisely the strongest directional effects. The panel's headline `max |d|` was computed over that borrowed subset, and **two panels printed "no directional blind spot" when their own data said otherwise** (ca-HepTh spread_mean, true 0.185; Gnutella betweenness, true 0.286). The text dump in `results/RESULTS_failures.txt` was correct throughout - only the figure was wrong, which is the artefact most likely to be read and least likely to be checked. Fixed: each row now takes its own top-7 from its own table, and the verdict is computed over the whole directional table.

Two artefacts had to be removed first, and the second nearly produced a spurious result: shrinkage (any regression pulls toward the middle) and **heteroscedasticity** (residual variance is far from constant, so tails fill with the periphery regardless of structure - the symptom was that *both tails profiled identically*).

### Finding 9 - Angle 4: what survives damage depends on the target (REVISED at five networks, 2026-08-27)

Delete a fraction rho of edges; rank nodes by their **clean** influence given only the damaged graph. Re-run on all five networks, 3 damage draws per cell, paired within draw.

- **Spreading:** local reaches **parity** with recomputation at rho = 0.05-0.10 and holds it - **on four of five**. `facebook_combined` never crosses and the gap *widens* (-0.013 -> -0.086). Margins elsewhere are a few thousandths: parity, not a rout.
- **facebook's failure is transfer, not locality.** Retraining on the damage regime turns it from worst to best: damaged-trained minus recompute goes **+0.014 -> +0.154** across rho, the largest margin any method achieves over recomputation anywhere in the arm. On the other four, damage-training moves `spread_mean` by <=0.010 - there is no shift to fix. Hypothesis for why (fitted to one network, **untested**): facebook is the one corpus network built of overlapping dense ego-nets, so uniform deletion shreds the triangle/conductance features rather than merely rescaling them.
- **Betweenness:** recomputation wins on **all five**, widening with damage, no exceptions. **Hypothesis rejected**, now on a corpus with a same-family replicate and a structurally unlike dense network. facebook is extreme: clean-trained local goes from tau 0.851 undamaged to **-0.111** at rho=0.5 - anti-correlated, not merely degraded.
- **Skew control still cuts the other way, and further than before.** On the nonzero subset *with* damage-training, local reaches parity or better with recomputation on **four of five** by rho=0.5 (ca-GrQc +0.002, Gnutella +0.001, facebook +0.020, ca-HepTh -0.015); only email holds a stable -0.056. So "recomputation wins for betweenness" is precisely: *on the full ranking, with a clean-trained model.* Drop either qualifier and it stops being true.
- **The collapse was distribution shift, not fragility.** Damage-training recovers up to **+0.509 tau** (facebook, rho=0.5; Gnutella +0.454). The recovery is largest exactly where the collapse was largest - which distribution shift predicts and fragility-of-locality does not.
- **Degree on the damaged graph overtakes the 171-feature clean-trained model on EVERY network** for betweenness; only the onset differs: rho=0.05 (facebook, Gnutella), 0.30 (ca-HepTh, email), 0.50 (ca-GrQc). At three networks this read as a high-damage embarrassment; at five it is a rule with a network-dependent onset. Even damage-trained, degree is beaten on ca-GrQc alone.
- **Caveat on quoting facebook:** its *full-tau* damaged-trained betweenness numbers carry paired sds of 0.10-0.18 and are **not** significant at 2 sd. Quote the nonzero-subset column there, not the point estimates.

### Finding 10 - one rung of the ladder is not a null; it is network-dependent, and ONE feature carries it (NEW)

This finding did not exist before facebook_combined was run, and it **revises Finding 3's headline**.

**Rewritten 2026-08-31.** The first version said "the **edge** tier is not a null" and put the whole +0.1478 there. That was an artefact of the tier mis-tag in section 7.3: the two columns carrying the effect were tagged `edge` and belong to `subgraph`. After the retag and the 400-cell refit, the effect splits across the two rungs and lands almost entirely on `subgraph`. The measurement was right; the attribution was not.

On facebook_combined, betweenness at radius 2, ten seeds paired:

| feature set | features | tau |
|---|---|---|
| node only | 35 | 0.6641 +/- 0.0048 |
| node + edge | 80 | 0.6959 +/- 0.0036 |
| node + edge + subgraph | 144 | **0.8239 +/- 0.0054** |

| rung | paired gain |
|---|---|
| node -> node+edge | +0.0318 +/- 0.0064 * |
| node+edge -> +subgraph | **+0.1291 +/- 0.0043 *** |

The **subgraph** tier is worth +0.129 - about 30 sd, and roughly **four times larger than any richness effect previously measured anywhere in this project**. The edge tier's +0.032 is real and is the largest edge-tier effect in the corpus, but it is a fifth of the whole.

Isolated with `analyse_edge_tier.py --tier subgraph`, adding each subgraph cost-group to the node+edge baseline separately:

| added group | features | gain vs node+edge |
|---|---|---|
| `shells_ci_hop_2` | **3** | **+0.1234 +/- 0.0042 *** |
| `graphlet_orbits` | 59 | +0.0134 +/- 0.0051 * |
| `hop1_ego_betweenness` | 1 | +0.0024 +/- 0.0035 |
| `hop1_ego` | 1 | -0.0004 +/- 0.0018 |

Splitting those three: **`local_conductance_2` alone is worth +0.1171**. One feature. `ball2_density` is worth +0.0469 on its own and **nothing** once conductance is present (the pair scores the same as conductance alone to five decimals); `ball2_edges` is +0.0042, not significant. And the cost contrast is the sharpest part: `shells_ci_hop_2` costs **1.55 s** on this graph for +0.123, while `graphlet_orbits` costs **231.6 s** - 150x more - for +0.013.

**Why:** conductance of the 2-ball is the fraction of the ball's edge volume that leaves it - a bridge detector by construction. facebook_combined is a union of ego networks where betweenness is almost entirely about the bridges, and that is invisible to every node-tier feature.

**The redundancy check has been WITHDRAWN.** This section used to certify the feature as orthogonal on a held-out R^2 of **-0.88** predicting `local_conductance_2` from the node tier. **That number does not reproduce.** Measured two ways on the current table - the project's own probe in `analyse_features.py`, and a RandomForest under 5-fold CV - it is **+0.99**, from the node tier and from node+edge alike (`ball2_edges` +0.999, `ball2_density` +0.992, `local_conductance_2` +0.992). The column is very nearly a deterministic function of the shell counts already present. It is still worth +0.117, because **a forest fitting betweenness does not spontaneously form the ratio cut/vol** - reconstructible is not accessible. That is a better result than the one it replaces, but it is a *different* one: do not repeat the orthogonality claim.

**Replication across all five, betweenness at r=2 - the composition differs, not just the magnitude:**

| network | edge rung | subgraph rung | `shells_ci_hop_2` | `graphlet_orbits` |
|---|---|---|---|---|
| facebook_combined | +0.0318 * | **+0.1291 *** | **+0.1234 *** | +0.0134 * |
| ca-HepTh | +0.0105 * | +0.0050 * | +0.0004 | **+0.0043 *** |
| ca-GrQc | +0.0082 * | +0.0014 | +0.0005 | +0.0006 |
| email-Eu-core | +0.0023 | +0.0045 | +0.0003 | +0.0017 |
| p2p-Gnutella08 | +0.0009 * | +0.0014 * | +0.0010 * | +0.0006 * |

Three regimes: boundary geometry dominates on facebook; **orbits** carry what little there is on both collaboration graphs (which agree with each other again); null on email and Gnutella.

**What it changes:** "Depth beats richness by an order of magnitude" was +0.376 vs +0.035. On facebook betweenness it is +0.197 (the r1->r2 hop) vs +0.160 (richness at fixed r=2) - **same order of magnitude**. Both of those are untouched by the retag, since the node tier and the richest tier are the same column sets as before; only the rung between them moved. Depth still wins on average and wins outright on the sparse networks, but the ratio is a property of the network, not a constant.

**The practical rule:** feature-group value is not a property of the feature group. A corpus average of "+0.003 for the subgraph tier" would have buried a +0.129 effect and told a practitioner to drop the single most valuable feature on the one network where anything mattered. **Per-network ablation is not optional.**

**The second rule, from the correction itself:** a tier label is an input to every richness comparison, not documentation. Because the ladder is nested, a column tagged one rung too low is fed to every model at that rung and above - so a mis-tag yields a *plausible* number attributed to the wrong cause, not a missing one. `verify_pipeline.py` now enforces that the three columns computed from one array share one tier.

**Limits:** one network drives it; the ego-network mechanism is a post-hoc structural reading, not a prediction; it is specific to betweenness (facebook's spreading targets see at most +0.012, and at r=2 at most +0.002); all three driving features are hop-2, so a radius-1 observer cannot use them - ~~at r=1 the facebook edge tier is *negative* (0.6366 -> 0.6268) and subgraph then adds +0.0001.~~

**CORRECTION 2026-09-04 to the struck clause above.** That negative r=1 edge rung was an artefact of the squared-error objective, not a property of the features. Under the `log1p` re-sweep the same rung is **+0.0158**, starred, having been **−0.0097**, starred - it changes sign - and the r=1 subgraph rung goes from a null +0.0000 to a starred +0.0074. Any reading of "the columns dilute before they help" is **withdrawn**. What survives is the first clause: the three driving columns are hop-2 and remain unavailable to a radius-1 observer.

**REVISED DOWNWARD 2026-09-01 - the +0.1291 is inflated roughly threefold.** Two
independent corrections, made for unrelated reasons, both cut this rung to about a
third of its published size:

| how the rung is measured | gain | sd |
|---|---|---|
| **as published** (rf, squared-error on raw betweenness) | **+0.1291** | 0.0043 * |
| rf, trained on `log1p(y)` - τ still scored against the original y | **+0.0436** | 0.0011 * |
| `hgb_matched` - a capacity-matched second non-linear learner | **+0.0555** | 0.0128 * |

The rung is **real** - starred under every one of the three, and with *tighter* error
bars under the corrected objective than the published version has. But the honest
size is ≈ **+0.05, not +0.13**, and the two corrections agreeing to within 0.012 from
completely different directions is what makes that conclusion stick rather than one
number replacing another. See **Finding 11** for why the objective was wrong, and
`docs/archive/phase6_record.md#rec-posthoc_B2_hgb_capacity` for the capacity-matched arm, which was declared
before it was run.

**And the effect is no longer a random-forest artefact, which is the one thing the
estimator sweep was run to find out.** `hgb_matched` is a different non-linear learner
and it reproduces the rung at +0.0555. Ridge and the un-matched `hgb` do not, but
neither of those is a working learner on this cell - see Finding 11. So: *"worth about
+0.05 to a competent non-linear learner"* is now supported; *"worth +0.117"* is not.

---

### Finding 11 - the project has been optimising the wrong objective, and it cost more than any feature ever added (NEW, 2026-09-01)

**This is the largest correction since the tier mis-tag, and unlike that one it is not
a bug. Nothing was implemented wrongly. The default was wrong.**

Every fit in this project minimises **squared error**. Every fit is scored by
**Kendall τ**. Those are not the same objective, and on a target with skew **28.88**
they are barely related: squared loss spends the model on the handful of nodes with
enormous betweenness, while τ only cares about ordering the bulk.

The fix is one line and it is free. Kendall τ is invariant to monotone transforms of
the *ground truth*, so training on `log1p(y)` while still scoring τ against the
**original** `y` changes what the model optimises and not what it is judged against.
That is a better-conditioned objective, **not a relaxed metric** - the distinction is
the whole reason this is reportable.

On facebook_combined betweenness at r=2, `node+edge`, 10 seeds:

| what the model trains on | τ (scored against original y) |
|---|---|
| `y` (as every published number was produced) | 0.6959 |
| `log1p(y)` | **0.8797** |

**+0.1838 τ, for free.** For scale: that is larger than the entire subgraph tier was
worth under the raw objective (+0.1291), larger than any hop in the project on this
cell, and it costs no extra traversal, no extra hop and no extra column.

**Why it contaminates the richness ladder specifically.** The handicap is **not constant
along the ladder**, so it is confounded with the axis §26a measures. Measured across the
corpus (`probe_objective_horizon.py`, 800 cells), the correction is **largest where the
feature set is poorest** and shrinks as features are added - on facebook betweenness,
+0.2906 at r=0, +0.1870 at r=1, +0.0983 at r=2, +0.0793 at r=3. Richer features
**partially substitute for a correct objective**. So a rung measured under the bad
objective flatters the richer arm, because the poorer arm was penalised harder. Correct
the objective and the subgraph rung falls from +0.1291 to +0.0436 - 66% of the published
effect was the poorer rung's handicap, not the richer rung's information.

> **Correction, 2026-09-01 (same day).** The first version of this paragraph said the
> handicap *grows* with feature count, reasoning that more features let the model chase
> the tail harder. **That is backwards for `rf` and it was generalised from a single
> cell.** The corpus probe shows the opposite direction. The *conclusion* - the rung gain
> is inflated ~3x - is unaffected and was always measured directly; only the stated
> mechanism was wrong. Note the direction is **learner-specific**: `ridge` on facebook
> betweenness does decay with radius (0.5445 -> 0.1107), which is what made the wrong
> reading plausible. The safe general claim is that the handicap **varies along the
> richness ladder**, not which way.

**How it was found, which matters because it was nearly missed.** It came out of asking
why `ridge` and `hgb` both collapsed on this cell. Two hypotheses were tested and
**both were falsified and discarded**: feature skew (log1p on the *features* rescued
nobody and actively hurt ridge, with rf's invariance to monotone transforms of
individual features used as the control) and discretisation (`max_bins=32` hurt, but
was not the cause). The objective was the third hypothesis.

**Who it hits, and how hard:**

| learner | why it is or is not protected |
|---|---|
| `ridge` | **worst**. It cannot escape the loss at all - it *is* the loss. Its collapse on facebook betweenness is this artefact, not inductive bias. |
| `hgb` | badly, and compounded by a separate leaf-floor confound (below). |
| `rf` | **partially, not fully.** Splits are order-based, but the split criterion and the leaf values are not. It still gains +0.18. |

**Does the horizon move? MEASURED 2026-09-01 - yes, on one network, and it moves DOWN.**
`probe_objective_horizon.py` recomputes r\*(ε) under both objectives across all five
networks, both `betweenness` and `spread_mean`, 4 radii × 10 seeds, using the project's
own `r_star_per_seed`. The raw arm reproduces the published sweep to **1e-16**, so the
only thing differing between arms is the transform.

**3 of 50 (network × target × ε) horizon cells moved. All three are betweenness. All
three are facebook_combined. 0 of 25 spreading cells moved.**

| network | target | ε | raw | log1p |
|---|---|---|---|---|
| facebook_combined | betweenness | 0.20 | 2 | **1** |
| facebook_combined | betweenness | 0.02 | 3 | **2** |
| facebook_combined | betweenness | 0.01 | 3 | **2** |

**The horizon gets SHORTER, and that is the interesting direction.** Part of the apparent
need for a third hop on facebook betweenness was the model **buying with features what a
correct objective would have given it for free**. Under a properly-conditioned objective,
r\*=2 suffices where r\*=3 was published. This strengthens the project's central claim -
locality is *more* sufficient than reported - while correcting a published number.

**The control worked.** Mean correction gain is **+0.0385 on betweenness** (mean skew
11.29) against **+0.0005 on spread_mean** (mean skew 4.12) - a 77× difference tracking
skew, with spread_mean's largest movement anywhere being +0.0047. So this is an artefact
of the objective/skew interaction, not of the transform perturbing r\* in general.

**One honest wrinkle:** ca-GrQc betweenness at ε=0.01 loses seed stability under the
corrected objective (modal support 10/10 → 5/10) without changing its modal r\*. Every
other cell holds at 9/10 or 10/10 under both. Worth a sentence; not worth a claim.

**What this does NOT do:** it does not invalidate any *comparison* made at a fixed
objective. Every rung gain, hop gain and horizon in this document was computed with
both arms under the same handicap, so the comparisons are internally consistent. What
moves is the *magnitude* of anything involving betweenness, and the ranking of feature
groups where the handicap grows along the axis being compared - which is exactly the
richness ladder.

**The generalisable lesson, recorded in the vault:** before comparing feature sets on a
rank metric, check the target's skew and refit once on a monotone transform of it. If
that single change moves the metric by more than your effect size, fix the objective
before reporting the ablation.

---

### The B2 estimator-invariance verdicts (2026-09-01)

Run per `docs/prereg/prereg_B2_estimator.md`, written and dated before the sweeps. Two full
corpus sweeps (`ridge`, `hgb`), plus one declared post-hoc arm (`hgb_matched`). All
output under `estimators/`, 640 rows and 640 OOF vectors per network per arm, 0
duplicates and 0 NaNs across all fifteen files.

| | verdict | note |
|---|---|---|
| P1 - rung largely disappears under ridge | **CONFIRMED** | but see the caveat below; it disappears for the wrong reason |
| P2 - rung does not go to zero, may go negative | CONFIRMED | −0.0016 ± 0.0066 |
| P3 - `hgb` sides with rf | **FALSIFIED** | and the test was **confounded** - see below |
| P4 - r\*(ε) agrees on spreading targets | CONFIRMED | lands **exactly on** the threshold bar; would flip on one cell |
| P5 - betweenness is where invariance is most at risk | CONFIRMED | |
| P6 - P(r) shape more invariant than its level | CONFIRMED | median ρ masks a **sign flip** on betweenness under ridge |

**Three caveats, all of which weaken the verdicts rather than the sweep:**

1. **P3 was falsified on a confound, and the confound is the same class of error the
   pre-registration congratulated itself for avoiding on ridge's scaler.** The sweep
   compared `rf` at `min_samples_leaf=2` - pinned deliberately by this project -
   against `hgb` at **20**, which is sklearn's default and was never chosen by anyone.
   Isolating one hyperparameter at a time, that single parameter moves τ from 0.2076 to
   0.6286, **68% of the entire gap**; `max_iter` made it *worse* and `max_leaf_nodes`
   did nothing. **P3 stays falsified** - a post-hoc rerun does not un-falsify a
   pre-registered prediction - but it did not measure inductive bias. The declared
   follow-up `hgb_matched` (`docs/archive/phase6_record.md#rec-posthoc_B2_hgb_capacity`, written before it ran)
   met its expectations: τ 0.6300 against a declared 0.60-0.75 band, spreading targets
   unmoved (≤ 0.0034), betweenness the only thing that moved.
2. **P1 is confirmed but its stated *mechanism* is not.** The pre-registration reasoned
   that ridge would lose the rung because a linear model computes ratios for free.
   Ridge does lose the rung - but it loses it while scoring 0.0971, i.e. while not
   working at all, and Finding 11 shows why. A prediction can be right about the
   outcome and wrong about the cause, and this one is.
3. **P4 and P5 both land exactly on their threshold bars.** Neither is a comfortable
   margin; both would flip on a single cell. Report them as "consistent with", not as
   established.

**What survives cleanly:** r\*(ε) agreement is **17/20 cells** for `hgb` against `rf`,
and the horizon claim on the spreading targets is estimator-stable within the stated
tolerance. That is the licence the sweep was run to obtain, and it was obtained - for
the spreading targets. For betweenness it was not, and Finding 11 explains most of why.

---

### Item 3 - the stale-cell analyses, re-established on repaired data (2026-09-01)

The 2026-08-31 audit reported "every locality horizon is unchanged" and "eight
richness-gain cells flipped significance". Both were computed **before** the
800-cell column-order repair, i.e. on data that was later fixed. Re-run against the
repaired sweeps:

- **r\*(ε): 0 of 100 (network × target × ε) horizon cells moved.** The audit's claim
  holds on the repaired data.
- **Significance stars: 2 borderline flips**, both at magnitudes below 0.004.
- **Quoted richest-tier τ at r=2 and r=3: max delta +0.0011**, nothing above the 0.002
  reporting threshold.

The claim was true. It is now *checked*, which it was not before - this project does
not get to leave a verification claim resting on data it subsequently repaired.

### Finding 12 - the sample-efficiency effect changes SIGN by target (NEW, 2026-09-04)

Supervisor directive 5, outstanding since July 2026, discharged. 5,600 cells:
5 networks x 4 targets x 4 radii x 7 training fractions x 10 seeds, FULL tier,
test fold always whole and only the *training* portion subsampled. Pre-registered in
`docs/prereg/prereg_B1_sample_efficiency.md`, scored by `analyse_sample_efficiency.py`.

**Validity first.** The fraction=1.0 arm reproduces `sweep_<tag>.csv` at FULL to
`max|dtau| = 0.000e+00` across all **800** comparable cells - bit-identical, against a
declared 5e-08 tolerance. The bespoke OOF loop in `probe_sample_efficiency.py` is the
pipeline, so the measured effect is the effect and not an artefact of the duplication.

**1. The lab's ~20% claim is target-dependent.** τ at 20% labels vs 100%, r ≥ 1:

| target | cells within 0.02 | mean drop |
|---|---|---|
| `spread_mean` | **15/15** | −0.0097 |
| `spread_cv` | 11/15 | −0.0157 |
| `spread_resid` | **3/15** | −0.0285 |

The rule is right for the easy target and wrong for the hard one. Quote it with the
target attached, never bare.

**2. The headline: r\*(ε) moves in OPPOSITE directions depending on the target.**
Scored under the pre-registered rule (modal r\* must differ *and* support ≥ 6/10 under
both arms), with email-Eu-core excluded as underdetermined:

| target | DOWN | UP | same |
|---|---|---|---|
| `betweenness` | **9** | **0** | 30 |
| `spread_mean` | 1 | 0 | 38 |
| `spread_cv` | 0 | **9** | 31 |
| `spread_resid` | 0 | **6** | 32 |

**Zero counterexamples in either direction.** Two mechanisms, each owning a set of
targets: on `betweenness` the deep radii are carried by a few high-variance columns
(Finding 10's conductance rung) that degrade fastest as rows are removed, so the deep
advantage goes first and r\* falls. On the hard targets scarcity hurts the *shallow*
radii proportionally more - fewer, cruder features, less redundancy to average over -
so the relative ranking tips deeper and r\* rises.

**The plan's standing prediction ("scarcity pushes r\* down") is FALSIFIED as stated**
- 20 UP against 15 DOWN overall. It was declared alongside its own competing mechanism
(P4) precisely so an upward move would be reportable rather than explainable, and P4
is what governs two of the four targets.

**3. The 5% arm is underdetermined and must carry the caveat.** At r=3, three of five
networks have no more training rows than columns (ca-GrQc 0.99, facebook 0.96,
email-Eu-core **0.23** rows per feature). Such a fit prefers a shallow radius for
reasons unrelated to any information horizon. Dropping email - the network most able to
manufacture DOWN moves - *strengthens* the UP verdict, so the falsification does not
rest on it. **The 10% and 20% arms carry the weight; do not quote the 5% arm alone.**

Label starvation is *not* the driver: realised nonzero betweenness labels survive
subsampling roughly in proportion (32.9 of 39 rows on email, 74.5 of 166 on ca-GrQc).

---

## 11. ~~WHY NO GPU WAS NEEDED - and why that changed on 2026-08-27~~ GPU MEASURED AND REJECTED (2026-09-01)

**The gate was run. The GPU lost. This section is now a measurement, not an argument.**

The 2026-08-27 decision to move to WSL + cuML and fit nothing further on CPU was
overruled on 2026-09-01 **by its own timing gate**, which is how it was always meant to
be settled. The original technical argument below turned out to be right, but for a
sharper reason than it gave.

### The decisive measurement

Three arms, identical work, same library, same data, same folds - so exactly one
variable moves between the arms that matter:

| arm | s / seed-cell |
|---|---|
| XGBoost **CPU**, tasks sequential, `n_jobs=16` | 6.77 |
| XGBoost **CPU**, 16 tasks in parallel, `n_jobs=1` | **3.90** |
| XGBoost **CUDA**, tasks sequential | 6.01 |

**GPU vs the best CPU arm: 0.65x. It is 1.54x SLOWER.** The pre-committed adoption
threshold was **≥ 2x**. Not close. Agreement was never the issue: `max|dτ|` was
0.00e+00 between the CPU arms and 6.24e-06 CPU-vs-CUDA.

The GPU genuinely executed - verified three independent ways, because a silent CPU
fallback would have produced exactly this shape of result for the wrong reason:
unfiltered warnings, `save_config()["learner"]["generic_param"]["device"]` reading
`'cuda:0'`, and `nvidia-smi` sampled from a background thread mid-fit showing 642 MiB
resident.

### Why - and this is the part worth carrying to other projects

**There are two parallelism axes, and GPUs only compete on one of them.** *Within-fit*
parallelism (across trees and features) is what a GPU accelerates. *Across-fit*
parallelism (independent seeds, folds, cells) is what this workload actually has, and
it is **6,400 wide per network**. Handing 16 CPU cores the outer axis instead of the
inner one beat the GPU outright. A workload made of many small independent fits loses
on a GPU **regardless of how fast the device is**, because the device is competing on
the wrong axis.

That reasoning applies to cuML exactly as it applies to XGBoost. **Recommendation:
do not build the WSL + RAPIDS environment for the sweep.** It faces the identical
constraint and would cost a second environment, a second set of numbers and a looser
reproducibility claim to lose the same race.

### The free 1.23x that was found on the way, and NOT applied

Restructuring the existing sklearn sweep from inner (`n_jobs=-1`) to outer parallelism
measured **1.23x** on matched cores, with `max|dτ| = 0.00e+00` - i.e. **more** exactly
reproducible than the current path, which drifts ~5e-08. Inner threading is only 53.5%
efficient on 16 cores against 61% for outer; the ceiling is memory bandwidth, which is
why the win is 1.23x and not 4x.

**This has deliberately NOT been applied.** It touches the code path that produced
every existing number, and 1.23x is not obviously worth that on its own. **Rachit's
call** - it is listed in section 14.

### What the GPU is still for

Part D1's GNN baselines, in a separate PyTorch environment. That is genuinely
GPU-shaped work - large dense tensor arithmetic, one model, many epochs - and none of
the reasoning above argues against it.

*(Retained because it remains true and cost time once: the RTX 5060 is Blackwell,
sm_120. An install succeeding is not evidence the kernels exist; a missing-arch build
fails at runtime, not at install.)*

### The original argument, retained - it was right

- Random forests are branching comparisons and sorting, not bulk matrix arithmetic.
- The data is tiny (~6,000 rows x 171 columns).
- The real bottlenecks are feature extraction and simulation - graph traversals with irregular memory access, the least GPU-friendly workload there is.
- Algorithmic wins dominate: the percolation shortcut gave ~900x, the merged traversal a further 4-8x. Neither required hardware.

Stage 1 is ~4 seconds per sparse network. The sweeps are the cost: 640 cells x 10 seeds x 5 networks is roughly 6 hours on 16 cores (~70 min per network; facebook's stage 1 alone is 242 s, 232 of which is ORCA 5-node orbits on a dense graph).

PyTorch appears only if the optional GNN comparison happens (last phase), in a **separate environment**.

<details>
<summary><b>Superseded: the 2026-08-27 decision and the pushback, kept for the record</b></summary>

*Kept because the reasoning is worth reading even though the conclusion was
settled empirically. Nothing below is current guidance.*

### The decision (2026-08-27)

Rachit has decided to move to **WSL + cuML on the RTX 5060** and to run nothing
further on CPU. His call, and the motivation is sound at the level that matters:
sweep cost is now the binding limit on what can be *asked*, and the three biggest
open items - the synthetic corpus, sample efficiency, cross-network transfer - each
multiply the current 6-hour corpus sweep several times over. A free local GPU is a
reasonable thing to reach for.

### The pushback, given and recorded

This is the least GPU-favourable workload in machine learning, and it should be
measured before the whole plan is built on it:

- The sweep is **6,400 small fits per network**, not one large one. Each cell is
  ~5,000 rows x <=171 columns. cuML's RandomForest carries real per-call overhead
  (host-to-device transfer, kernel launch, model materialisation) that a 0.6-second
  sklearn fit does not amortise. It is entirely possible for the GPU sweep to come
  out **slower** than 16-core sklearn.
- The **other** half of the runtime is feature extraction and cascade simulation -
  irregular graph traversal, which cuML does not touch at all. Even a perfect
  speedup on the fit leaves that untouched.
- Historically on this project the wins came from algorithms, not hardware: the
  percolation shortcut ~900x, the merged traversal a further 4-8x.

**None of that is a reason not to try it** - it is a reason to spend the first hour
in the new environment on a *timing comparison*, not a full sweep. Fit one network's
worth of cells both ways and look at the wall clock. If cuML is not clearly ahead,
the honest conclusion is that the sweep stays on CPU and the GPU is reserved for the
optional GNN phase, which genuinely is GPU-shaped work.

*(Note: the RTX 5060 is Blackwell, sm_120. Support for it has already been the gating
problem once on this machine, in an unrelated tool. Check that the RAPIDS build you
install actually has sm_120 kernels before assuming an install means a working GPU.)*

**How this turned out:** the timing comparison recommended here is exactly what was
run on 2026-09-01, and it came out against the GPU by a wide margin. The pushback was
overruled by a decision and then vindicated by a measurement.

</details>

---

## 12. GOTCHAS AND TRAPS

**THE BLAS WILL KILL YOU SILENTLY.** An unpinned solve produced numpy linked against MKL alongside a **pip-installed** scipy carrying its own OpenBLAS. Result: a hard native abort, **exit code 127, no Python traceback**, on any dense matmul - which kills `beta_c` at the first eigenvalue call. `environment.yml` now pins `libblas=*=*openblas` and exact versions. **Never `pip install` numpy/scipy/scikit-learn into this env.** After any environment change:

```bash
python -c "import numpy as np; A=np.random.rand(300,300); print((A@A).sum())"
```

If that aborts instead of printing, fix the BLAS before debugging anything else.

**The WSL environment does not inherit any of that.** `environment.yml`'s pin protects
the Windows env only. Two things must pass in the new env before a single number out
of it is trusted:

1. **The BLAS check above**, re-run in WSL. A fresh conda solve there can reintroduce
   exactly the same MKL/OpenBLAS collision, with the same silent exit-127 signature.
2. **A cuML-vs-sklearn agreement check.** Fit the same cell both ways on the same
   seed and compare tau. cuML's RandomForest is **not** a reimplementation of
   sklearn's - different split-finding, different histogram binning - so it will not
   agree bit for bit and should not be expected to. What you need to establish is
   that the *conclusions* survive: the ranking of radii, the sign and rough size of
   the tier gains. If they do not, the GPU results are a different experiment, not a
   faster version of this one.

**This bites the reproducibility wording, and the docs will need editing, not
copying.** The study doc currently states reproducibility as a *measured tolerance*
(`max|dtau| = 5.08e-08` for `n_jobs=-1`), which was itself a correction of an earlier
"bit-identical" claim that turned out to be false. A cuML number will be orders of
magnitude looser than 5.08e-08. Re-measure it and rewrite the sentence; do not carry
the old figure across.

**`python` on the Bash tool's PATH is msys2's**, which has none of the dependencies. Always call `<conda-root>\envs\influence\python.exe` by absolute path.

**`n_jobs=-1` costs bit-exact reproducibility.** Two identical runs differ by 5.7e-14 in predictions, which amplifies to ~5e-08 in tau because tau is a rank statistic and a last-bit difference can flip a near-tie. That is five orders of magnitude below the seed spread we report. Set `n_jobs=1` for a bit-exact audit and accept ~10x slowdown.

**The leakage guard will abort runs.** That is intentional. Its exception list matches **exact names only** - `collective_influence_4` would trip it if you raise `max_hop`.

**THE TRAINING OBJECTIVE IS NOT THE SCORING METRIC, AND THE GAP IS BIGGER THAN ANY
FEATURE.** Every estimator here minimises squared error; everything is scored by
Kendall τ. On betweenness (skew 28.88) that costs **+0.18 τ** - more than the whole
subgraph tier. Training on `log1p(y)` while scoring τ against the **original** `y`
recovers it and is legitimate, because τ is invariant to monotone transforms of the
truth. Worse, the handicap **grows with feature count**, so it inflates every richness
comparison. See Finding 11. Before comparing feature groups on a rank metric, check
the target's skew and refit once on a transformed target.

**Match capacity hyperparameters before calling anything an inductive-bias result.**
`RandomForestRegressor` defaults to `min_samples_leaf=1` and this project pins it to
**2**; `HistGradientBoostingRegressor` defaults to **20**. B2 compared those two
directly and attributed the resulting 0.5 τ gap to inductive bias. It was the leaf
floor - 68% of it, from that one parameter. A hyperparameter nobody chose is not a
property of the learner.

**Alternative-estimator sweeps MUST go in `estimators/`, never the repo root.**
`analyse.py::discover_networks` globs `sweep_*.csv` and regexes `sweep_(.+)\.csv`, so
a file named `sweep_ca-GrQc__ridge.csv` beside the others is silently discovered as a
**network** - corrupting `analyse.py`, `analyse_topk.py`, `analyse_multiplicity.py`,
`make_fig1.py` and `verify_docs.py`, all of which share that glob. The globs are
non-recursive, which is what makes the subdirectory safe. Do not "just add an
`estimator` column" either; that breaks `load()` and every consumer of it.

**`stage2_sweep.py` calls `out_of_fold_predictions` directly**, not through
`locality_sweep`. It is a third call site and the easiest one to miss when threading
anything through the estimator path.

**Feature count is not information.** Run `analyse_features.py` before any result that compares feature groups. It checks closed-form identities to machine precision, effective dimensionality, and whether each tier is predictable from the tiers below. **An ML probe understates derivedness for exact identities** - a tree approximates a product with axis-aligned splits and scores 0.998, slipping past any threshold.

**But high correlation is NOT redundancy.** `orbit_04` is 0.99 rank-correlated with existing columns and still gave a ten-sigma gain. Effective dimensionality measures *monotone* redundancy only.

**`robustness.py` deliberately skips the LCC restriction.** Deleting edges fragments the graph; taking the LCC would drop nodes and break correspondence with the clean ground truth - and the dropped nodes would be exactly the ones the damage hurt most.

**Graphlet orbit cost does not decompose by radius** unlike everything else - ORCA solves all orbits in one pass, so a cell using any orbit pays for all of them.

**`stage2_sweep.py` resumes on both the CSV and the prediction store.** A cell counts as done only if *both* survived; an interruption can otherwise leave cells scored but unusable for the atlas.

**Re-running `stage1_prepare.py` overwrites the cache** including cascades. Deterministic given the seed, so it reproduces - but it is the expensive step.

**Cascade arrays (~50-75 MB) and prediction stores (~20 MB) are gitignored.** Cascades regenerate in seconds; predictions require a full re-sweep.

**Windows:** `curl` in PowerShell is an alias - use `curl.exe`, or just `fetch_data.py`.

**THE HOST HARD-CUTS UNDER SUSTAINED LOAD. Design every long run to be resumable.**
Measured 2026-09-04 from the Windows event log: **8 unexpected shutdowns between
2026-08-24 and 2026-09-04**, all with `BugcheckCode = 0`, `PowerButtonTimestamp = 0`,
and **no crash dump** - despite minidump collection being enabled and demonstrably
working (5 dumps exist from Apr-Aug). No WHEA events either. That signature means the
CPU stopped executing instantly: power removal or a firmware-level trip, both of which
happen below Windows and leave nothing behind. It is *not* a software crash, so no
amount of Python defensiveness prevents it.

Machine: ASUS ROG Zephyrus G14 GA403UM, Ryzen 9 270 (8C/16T), 16 GB, on the ASUS
"Turbo" power plan (CPU max state 100%). Ruled out so far: overheating as the direct
mechanism (AMD throttles at Tjmax rather than cutting), charger (bundled barrel
adapter in use), airflow (hard desk), battery wear (90.4% health - 66,003 of 73,001
mWh design). Remaining candidates are a power-delivery transient, a firmware bug (BIOS
GA403UM.310, 2025), or a VRM fault.

**HWiNFO64 caught one (2026-09-04, `Documents/CheckingStuff.csv`, 2 s interval).** The
log runs continuously 08:49:55 -> 10:36:40 with no gap anywhere; `LastBootUpTime` is
10:36:50. So the cut happened at ~10:36:4x and the final 25 samples are *unremarkable*:
34-37 W package, 95.2 C steady, `PROCHOT = No`, fans steady at 5,900 / 8,900 RPM, no
ramp in anything. **That rules out a slow thermal or power ramp** - whatever kills the
machine is faster than a 2-second sample. Next run should log at 200-500 ms.

> **Timestamp trap, and it nearly cost a diagnosis.** Windows Event 6008 reported the
> "previous system shutdown at 10:23:43", but the machine was demonstrably alive and
> logging until 10:36:40. Event 6008's time is a *periodically flushed checkpoint*, not
> the instant of power loss - here it was 13 minutes stale. Searching the telemetry at
> the event-log time finds a perfectly healthy machine and yields the false conclusion
> that the logging missed the crash. **Always cross-check 6008 against `LastBootUpTime`
> and the telemetry's own last row.**

The predicted decisive row - **charge rate going negative on AC** - did *not* happen,
and the actual reading is more interesting: the battery hit 100% at 09:17:49, charge
rate settled to **0.000 W** from 09:23 onward, and the cut came 79 minutes later. Both
2026-09-04 crashes were on AC with a full pack. *(Inferred, n=1, mechanism unconfirmed -
many laptops do keep a full battery available to supply peak current.)* The cheap
reversible test is **Armoury Crate -> Battery Health Charging -> 80%**, which keeps the
pack in the current path. Also noted: the 10:36:30 and 10:36:32 samples are
byte-identical across all 356 sensors, i.e. HWiNFO stalled one poll ~10 s before the
cut. Possibly noise; only finer sampling will say.

**The practical consequence for this repo:** `stage2_sweep.py` appends each cell the
moment it completes and resumes on both the CSV and the prediction store;
`probe_sample_efficiency.py` resumes on the cell tuple and, **since 2026-09-04, writes
after every (target, radius) block rather than every network** - the per-network cadence
would have discarded all 1,120 cells of `facebook_combined` if a cut landed near its
end, which is hours. Per-block bounds the loss to 70 cells. That is why *both*
2026-09-04 cuts cost **zero** finished cells. Do not "optimise" those
incremental writes away, and do not add a long-running script that only writes at the
end. This is also the strongest argument against adopting outer parallelism (section
14).

---

## 13. WHAT TO DO NEXT

Status and sequencing live in one place since 2026-09-12: [`docs/ROADMAP.md`](docs/ROADMAP.md),
with the session-by-session record in [`docs/LOG.md`](docs/LOG.md). The priority list this
section carried until then, struck-through history included, is preserved verbatim in
[the Phase 6 record](docs/archive/phase6_record.md#rec-handoff-13).

## 14. OPEN DECISIONS

**Added 2026-09-01, all three are Rachit's call and none should be inferred:**

- **~~Whether to re-sweep betweenness under a `log1p` training objective.~~ DECIDED
  2026-09-03 (Rachit): re-sweep. RUN 2026-09-04.** 800 cells in
  `estimators/sweep_<tag>__rf_log1p.csv`; declaration + scored addendum in
  `docs/reference/decl_objective_resweep.md`. What it established:
  - The facebook r=2 subgraph rung is **+0.0436**, not the published +0.1291 —
    reproducing an independent single-cell measurement to four decimals. With the
    capacity-matched HGB arm's +0.0555 from an unrelated correction, **three routes
    put the honest rung near +0.05, not +0.13.**
  - **It is essentially a facebook effect.** 0 of 32 rungs on the other four networks
    moved by more than 0.02. The +0.18 τ headline rests on the one extreme-skew
    network (28.88 vs 4.77–9.73) — **n=1, and it must be said so.**
  - **A published negative rung was an objective artefact.** facebook r=1 edge tier
    goes from a *significant* −0.0097 to a *significant* +0.0158. Any reading of that
    as "edge features hurt at short radius on dense graphs" is withdrawn.
  - **Top-k is unharmed.** The correction was suspected of helping bulk τ while hurting
    `precision_at_1pct`; measured, 1 of 20 p@1 changes clears 2·sd and it is positive,
    and 0 cells show τ significantly up with p@1 significantly down.

- ~~**NEW, and the successor to the above: whether `rf_log1p` becomes the reported
  default.**~~ **DECIDED 2026-09-04 by Rachit: ADOPT, for betweenness only.**

  **How it is implemented.** `sweep_<tag>.csv` is *not* rewritten - the record of what
  the project used to believe is not something a later decision gets to delete.
  Instead `analyse.load()` splices the log1p betweenness rows in at read time and
  returns everything else unchanged. `load(tag, raw=True)` returns the superseded
  squared-error corpus, and the scripts whose job is to COMPARE objectives keep
  reading `sweep_<tag>.csv` directly. **`analyse_estimators.py` is pinned to `raw=True`**
  because `ridge` and `hgb` were fitted under squared error - taking the default there
  would compare rf(log1p) against ridge(squared) and report the objective effect under
  an estimator's name.

  **What it changed, measured.** Betweenness τ at FULL rises everywhere; the spreading
  targets are bit-identical (`worst |dτ| = 0.000e+00`, asserted every run by
  `verify_pipeline.py` N9). The horizon barely moves: **3 of 25** betweenness r\*(ε)
  cells shifted, all `facebook_combined`, all **downward** — reproducing the
  pre-registered probe from a third code path.

  | network | r=0 | r=1 | r=2 | r=3 |
  |---|---|---|---|---|
  | facebook_combined | **+0.2906** | **+0.1870** | **+0.0983** | **+0.0793** |
  | email-Eu-core | +0.0402 | +0.0094 | +0.0084 | +0.0097 |
  | ca-GrQc | +0.0138 | +0.0020 | +0.0074 | +0.0070 |
  | ca-HepTh | −0.0000 | +0.0046 | +0.0040 | +0.0038 |
  | p2p-Gnutella08 | −0.0005 | +0.0007 | +0.0019 | +0.0020 |

  **The scope limitation travels with it.** The large effect is a `facebook_combined`
  effect and that is n=1 — four of five networks gain ≤ 0.04 anywhere and ≤ 0.01 at
  r ≥ 1. Adoption fixes a real mis-specification; it does not make the magnitude
  generalise.

  **What is now on the OLD objective and is not re-based:** B2's estimator-invariance
  sweep (ridge/hgb) and B1's betweenness arm (Finding 12). Both were fitted with
  `make_rf`. Re-basing either means re-running it, which is a separate decision.
- **Whether to adopt outer parallelism in the sweep.** A measured **1.23x** with
  `max|dτ| = 0.00e+00` - strictly more reproducible than the current `n_jobs=-1` path.
  ~~Against: it touches the code path that produced every existing number, for 1.23x.~~

  **Reasoning strengthened 2026-09-04, because the original objection was weak.** With
  `dτ` measured at *exactly* zero, the parallelism provably does not change answers, so
  "it touches the published path" only guards against the refactor introducing a bug -
  a real but modest risk, and a testable one (re-run one network, diff the CSV). Three
  concrete costs, two of them measured for the first time here:

  1. **Memory: ~2.2 GB at 16 workers.** Separate processes each carry their own
     interpreter and numpy. Measured: a fitted forest is only 6.5 MB (90,204 tree
     nodes) and the feature matrices are 5-12 MB, so the cost is almost entirely
     per-process overhead (~130 MB each): ~1.1 GB at 8 workers, ~2.2 GB at 16. This
     machine has 16 GB and runs at ~3.7 GB free during a sweep, so that is
     substantially all the remaining headroom.
  2. **It forfeits per-cell durability, which is the expensive part on THIS machine.**
     `stage2_sweep.py` appends each cell the instant it finishes ("never lose a
     finished cell"); outer parallelism returns results in batches. The host has
     suffered **8 hard power-cuts in 12 days** (see the gotcha in section 12), and that
     append is what limited the 2026-09-04 crash to zero lost cells. Recoverable with
     `Parallel(return_as="generator")` streaming results back to a serialised writer,
     but that is engineering, not a flag.
  3. **Oversubscription footgun.** Requires `n_jobs=1` on the estimator AND
     `OMP_NUM_THREADS=1`; otherwise 16 processes x N BLAS threads thrash 8 cores.

  Note also the scope: the 1.23x applies to **fitting only**. Stage 1 is graph
  traversal and is untouched (facebook: 242 s, of which 232 s is ORCA). Net saving is
  ~17 min on a betweenness re-sweep, ~70 min on a full corpus run.

  **Standing recommendation: keep declined until the host is stable AND a genuine
  full-corpus re-run is needed** - then the durability loss is worth engineering around
  and the 70 minutes is worth having. Still Rachit's call.
- **Whether to build WSL + RAPIDS at all.** Recommendation on the measured evidence is
  **no** for the sweep (section 11) and **yes, eventually** for Part D1's GNN
  baselines, which are a different shape of work in a separate environment.

- **Which edge-probability convention to headline.** Weighted cascade is most defensible for social networks; uniform is what the fast percolation path supports. Currently uniform, and it is recorded in `cache_meta`.
- **Whether to add a threshold model (Linear Threshold)** as a second dynamics arm.
- **~~Whether 5-node graphlets justify their cost over 4-node.~~ ANSWERED: yes, decisively, and specifically at radius 1.** See Finding 3.
- **~~Whether 5-node EDGE orbits justify 204 more columns.~~ ANSWERED: no.** Implemented and radius-calibrated (16 at r1, 39 at r2, 12 at r3, 1 at r4), then tested directly with `analyse_edge5.py` on two networks, three targets, ten seeds paired. The largest gain anywhere is **+0.0020** (ca-GrQc volatility at r=1, for 39 extra columns) and several are **significantly negative** (email spread mean at r=2 and r=3, -0.0007 and -0.0006, both beyond 2 sd) - the extra 132-165 columns dilute rather than help. They stay **off by default**; `edge_graphlet_size=5` turns them on if anyone wants to re-check.

  Note the contrast with 5-node NODE orbits, which were a decisive win at r=1. Expanding the *node* orbit vocabulary mattered; expanding the *edge* one did not. That asymmetry is worth a sentence in any writeup.
- **Whether to keep the `dynamic` tier.** It works, it is cleanly isolated, and it contributes ~0 everywhere (max +0.0008). Keeping it costs 25% of sweep time for a citable null. Worth keeping until the corpus is larger.
- **When to report the p-multiple sweep.** The 1.2x email cache in `cache_archive/` is the start of one.

---

## 15. TONE AND WORKING STYLE NOTES

- Rachit has been anxious about novelty and about a harsh AI-generated meta-review. That review applied a top-tier-conference rubric to an undergraduate proof of concept. The fair reading is that this is solid student research with a genuine angle - and it is now considerably stronger than when that review was written. Be honest about limitations without being deflating.
- He gets nervous presenting. Scripts and cheat-sheets have been useful. Write speaking material the way people talk.
- **When a result contradicts something previously claimed, say so explicitly and write it up as a revision.** This has now happened repeatedly - Finding 3 has been revised twice, Angle 4's headline was overturned by its own control, and a reproducibility claim written into the docs was falsified within the hour and corrected. That honesty is the project's main asset.
- **Verify rather than assert.** Every implementation is checked against an independent reference. Two real errors were caught that way and both would otherwise have been invisible.
- The most useful habit established: when a result looks good, ask *"compared to what, exactly?"* and *"what would make this artefactual?"* Both tails profiling identically, an edge tier that was algebraically derived, and a model collapsing from distribution shift rather than fragility were all found that way.

---

*End of handoff.*

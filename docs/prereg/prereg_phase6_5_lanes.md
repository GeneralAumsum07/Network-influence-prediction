# Phase 6.5 lanes — preregistration, 2026-09-12

**Naming addendum, 2026-09-12 21:30 IST (Claude Opus 5; Rachit's instruction "settle it"):**
this file was registered as "Phase 7 lanes" and lived at the docs root as `prereg_phase7_lanes` (`.md`). The
seven deck-derived lanes are **Phase 6.5**; Phase 7 keeps its plan-of-record meaning (D3
synthetic confirmation, then real-corpus scale-out) and Phase 8 stays the learned baselines.
"Phase 7" in the body below means Phase 6.5 wherever it names these lanes, and means the
GNN/D3 phase where it says so (rows 9, 10, 14 and the "Not lanes" list). Output
directories registered as `results/phase7_<lane>/` are `results/phase6_5_<lane>/`
(`results/phase7_local` was renamed with its pilots re-run; nothing else had been written).
No prediction, scoring rule or clarification changes. Rationale in `docs/ROADMAP.md`.

**Pre-execution literature correction, 2026-09-12:** the copied plan's claim that
Zhang fixed the dynamics is false; the paper varies four infection rates, uses
an empirical threshold locator and includes a ridge comparison. Its HI indexing
also starts degree at order 1, whereas this repository uses order 0. See
`../reference/prior_work.md`. The planned L1 experiments remain project
robustness tests; their predictions and numerical scoring rules are unchanged.
No estimator, including a GNN, is asserted to establish the true information ceiling.

**Pre-execution implementation clarifications, 2026-09-12:**

- L4 RF .98-radius rule uses the mean set-spread curve over ten fit seeds;
  individual seed ratios/radii and disagreements are retained. The top-sigma
  overlap control selects on the training half only, so it is a Monte Carlo
  oracle rather than exact expected influence.
- L2/L7 reconstruction R² requires fitting: `analyse_features.predictability`
  trains a histogram gradient booster. Therefore only raw feature extraction,
  standalone tau and residual effect sizes run beside the queue; the R² gates
  wait until Stage 4 succeeds. Calling these “zero-fit R² gates” was incorrect.
  R² uses that existing held-out protocol, including max 4000 rows and seed 0.
- L7 shares each shell-2 node equally across all its first-hop shortest-path
  parents, then normalises branch mass by shell-2 size. This avoids dependence
  on arbitrary node ordering. Empty shell 2 gives max share=entropy=0 and is
  flagged; entropy uses natural logs. Compare against the prescribed residual
  groups without using target residuals to define the features.
- NB walk-length L has information radius L-1 under this repo's boundary-degree
  convention (length 1 is degree at radius 0). Report both quantities. Use an
  implicit arc recurrence on production graphs to avoid a degree-squared
  explicit matrix; verify against `build_nonbacktracking_direct` on fixtures.

Status: registered before any Phase 7 probe execution. The seven-lane plan below is preserved as the specification; section 5 supersedes the earlier MVP-only L1 schedule. Results will be appended separately, never inserted into predictions. Phase 6 historical results remain unchanged.

Clarifications registered before execution: RF full means analyse.FULL (the richest structural tier). The dynamic tier is separately labelled. RF scores from existing sweeps use full-draw targets; comparison with E(r) on independent half-draw targets is descriptive and will expose this mismatch. For L3 monotonic means nondecreasing tau at radii 1,2,3 (no tolerance beyond 1e-12); each network is scored separately. Sparse networks means ca-GrQc, ca-HepTh, p2p-Gnutella08. L3 counter fires at >=4 networks under the stated >= comparison. Radius zero is a tied baseline, reported unscored for tau. No new predictive-model fits start before Stage 4 succeeds.

---

# Plan — The teammate's two decks, audited against the repo, and what to do with them

**Author:** Claude Opus 5 · **Written:** 2026-09-12 16:30 IST · **Owner of record:** Rachit
**Supersedes** the 2026-09-10 "Finish Astra's Phase 6" plan in this file, which is complete
except the items carried over in §0.

## Context

Two decks by a teammate, `1_primer.pptx` (51 slides, concept primer) and
`2_consolidation.pptx` (22 slides, "consolidation briefing for my advisor"), both dated
2026-07-22, lay out a research programme for the locality horizon. Rachit asked: which of
those ideas are actually good, which are novel, which the project has already implemented
or tested, and what a plan to pursue the good ones looks like. Both decks were read slide
by slide (text, tables, notes); the repo, docs and vault were searched for each idea; the
one prior-work claim the decks hinge on (Zhang et al. 2024) was verified on the web.

Also carried in from the previous turn: **queue the Angle 4 robustness re-run** (Rachit's
instruction, 15:51 IST). That is §0, first action after approval.

## 0. Carry-over from the Phase 6 root integration (do first)

1. **Queue Angle 4.** Append to `results/phase6_root_integration_stage3_20260912.ps1`'s
   successor — a new `stage4` controller that waits for `STAGE 3 LANES COMPLETE`, then runs
   `analyse_robustness.py` (raw arm, historical) **and** a log1p arm (needs the same
   `--objective reported` switch already added to `analyse_edge5.py`; add it to
   `analyse_robustness.py` with a dated docstring note), then `make_fig3.py`. Pre-C8 copies
   of `RESULTS_robustness*.txt` / `robustness.csv` go to `results/c8_historical_pre_20260912/`.
   Update `results/HISTORICAL_LANES_NOTE_20260912.md` ("not re-run" → "re-run queued, stage 4").
   ~1 h of compute, after stage 3 (≈ 2026-09-16 morning).
2. Stage 1/2/3 completion write-ups and the D-closure ledger re-review stay as listed in
   `docs/archive/phase6_record.md#rec-phase6_claude_worklog_20260910` (15:30 entry). Nothing in §2 below starts a
   multi-core fit before that queue drains (~2026-09-16); zero-fit lanes may run now,
   single-threaded, with a dated note that `fit_seconds` in the running lanes is
   contaminated during that window.

## 1. The audit: every idea in the decks, graded

Legend: **DONE** = implemented and measured · **PART** = partly · **DEFER** = explicitly
deferred by a standing ruling · **NEW** = never touched. Novelty is my assessment of the
idea against the literature the project has on file plus the Zhang check; "good" means
worth compute on *this* project's evidence base.

| # | Deck idea (slide) | Repo status | Good? | Novel? | Verdict |
|---|---|---|---|---|---|
| 1 | r\*(ε) as a first-class object; ε relative to ceiling (P 33, C 4) | **DONE** — `experiment.py::locality_horizon`, relative `(1-ε)·ceiling`, five tolerances, seed stability, 3,200 cells | — | Claimed novel vs Zhang; plausible | Already the project |
| 2 | P(r) measured over a finite family is a lower bound on the true ceiling (P 32, C 10 #3) | **PART** — B2 estimator invariance (ridge/hgb/hgb_matched, 17/20 agreement); referee M4 names it | yes | framing only | One paragraph in study (V-information name); no code |
| 3 | Kendall τ + top-5% + seed-set quality (P 34) | **PART** — τ, Spearman, p@1%/5%, `RESULTS_topk.txt`; **seed-set quality never done** (referee M7) | yes | no | **L4** |
| 4 | **H1: r\* non-monotone in β, peak at β_c** (P 35, C 8, C 21) | **NEW** — everything at 1.5×β_c; only τ(degree, spread) at 6 multiples on one network (Finding 5); referee M6 "the unexamined hyperparameter"; `sweep_transmission()` exists uncalled; 1.2× email cache archived | **yes — the most important robustness check the project has not run** | partly (Zhang fixed dynamics) | **L1** |
| 5 | β_c from the non-backtracking operator (P 17) | **DONE** — `criticality.py`, Ihara–Bass, verified vs direct 2m×2m to 1e-9; mean-field wrong by 2.6× | — | no | nothing to do |
| 6 | Percolation shortcut: one cut reveals every seed (P 13) | **DONE** — `simulate_ic_percolation`, production path, 4000 draws < 1 s | — | no | nothing to do |
| 7 | Simple vs complex contagion; LT arm; single-seed degeneracy (P 14–15, C 10 #2, C 20) | **DEFER** — HANDOFF §14 open decision; referee D4; no code | yes, with a correction (§L5) | moderately | **L5** (gated pilot) |
| 8 | Truncated DMP as a zero-training r-local predictor (P 38) | **PART** — the `dynamic` tier's `perc_reach_2/3` is the independent-path approximation used as a *feature* (null: max +0.0008); **never scored standalone**; DMP proper absent | yes | no | **L3** |
| 9 | Loop-corrected MP (Cantwell–Newman) as the information ceiling I(r) (P 40, C 11) | **NEW** | weak as posed — it is an IC-specific estimator, not a ceiling for betweenness/volatility; the honest ceiling probe is the GNN (Phase 7) | no | Replace with L3's exact object; no loop-corrected MP |
| 10 | The gap G(r) = I(r) − E(r) (P 48, C 11, C 13) | **PART** — "reconstructible ≠ accessible" (+0.117 τ at R²≈0.99) and B2 are the accessibility half; the ceiling half is referee M4 (GNN, Phase 7) | yes as an *estimator ladder*; not measurable as a true gap until Phase 7 | the framing is the decks' best idea | L3 builds the hand-derived rung; the ladder table becomes a study section |
| 11 | Directional horizon / per-branch signal / NB backbone (P 49, C 12) | **NEW** — all multi-hop features are shell aggregates; bridges caught isotropically (`edge_overlap_*`, `boundary_porosity`, `local_conductance_2`); NB used only for β_c | yes, cheaply testable | moderately | **L7** |
| 12 | Certificate: predict r\* from hub-vs-bulk ratio, γ, NB spectral gap (P 50, C 15) | **PART** — `structure.py` has the localisation duel, γ (CSN + bootstrap), assortativity, clustering; NB gap absent; **never joined against r\***; Finding 4/§17a show five real networks cannot separate n, ⟨k⟩, coverage | yes, but only on the synthetic corpus | moderately | **L6** (= D3, already the top scientific priority) |
| 13 | Synthetic ensembles: configuration model across γ, tunable clustering (C 16) | **DEFER** — `generators.py` + `stage0_generate.py` verified, 31 graphs designed, `data/synthetic/` empty, D3 unregistered | yes | no | folded into **L6** |
| 14 | GNN depth = radius (P 41–42, C 5) | **DEFER** — standing rule, Phase 7, separate env | later | no (Xu et al.) | out of scope |
| 15 | T1 correlation-decay upper bound, T2 Le Cam lower bound (P 44–45, C 14) | **NEW** | no — the decks concede bounds live on ensembles; the relevant literature is local weak convergence (referee D5) | no | Cite, do not prove |
| 16 | H-index ladder, CI_ℓ, k-shell, localisation duel (P 25–28) | **DONE** as features / global axes | — | no | Add citations (Lü 2016, Kitsak 2010 absent) |
| 17 | Zhang, Hanjalic & Wang 2024 collision (C 7–8) | **NEW — not cited anywhere in the repo.** Verified real: [Sci Rep 14:4929](https://www.nature.com/articles/s41598-024-55547-y), iterative NWC / visiting-probability / H-index over order-K neighbourhoods, saturation ≈ K 4 | mandatory | — | **L2** |
| 18 | Venue: journal not ML conference (C 18) | — | Rachit's call | — | no action |

**What the decks get wrong, for the record.** (i) "Nobody set the radius as the variable"
was already false in July — the repo had. (ii) Loop-corrected MP is not an information
ceiling; it is one more r-local estimator, and for IC the exact r-local object is simpler
(L3). (iii) The certificate cannot be fitted on five observational networks — the project
proved that to itself in §17a. (iv) "Zhang has no ε-formalism / no estimator-independence"
is true, but the repo already has both, so the surviving-gap list is shorter than the deck
says: what is genuinely open is **criticality (L1), complex contagion (L5), the ceiling
(Phase 7 GNN), and the certificate on synthetic graphs (L6)**.

## 2. Lanes, in the order to run them

All lanes: pre-register prediction **and** the opposite-sign mechanism in one dated file
`docs/prereg/prereg_phase6_5_lanes.md` before any run (vault lesson 2026-09-04); outputs under
`results/phase7_<lane>/` only; verifier before runner; nothing written to the repo root;
every historical number preserved. Interpreter by absolute path; no pip installs.

### L3 — zero-training r-local dynamics predictors (≈ 1.5 h, 0 fits, can run now)
- **Object:** IC **truncated at r rounds on the actual percolation draws** — cascade size
  reachable within r live steps from seed i. Strictly r-local by construction; equals σ_i as
  r → ∞; the spread-target twin of `betweenness_k`. `perc_reach_r` standalone is a free
  extra column. DMP at depth r optional, only if cost forces it.
- **Confounds handled:** score E(r) on draws 0–1999, target on 2000–3999 (else inflated);
  report beside `results/coverage.csv` (on email/facebook the 3-ball ≈ the graph).
- **Prediction:** E(r) τ rises monotonically; E(1) beats the RF node tier at r=1 on the
  three sparse networks; RF full beats E(r) at r≥2 by ≥0.03 everywhere.
  **Counter:** E(3) ≥ RF full at r=3 on ≥4/5 networks → the RF has been under-extracting the
  ball and reported horizons are a vocabulary artefact (this cancels L2/L7 fits).
- Files: `influence/local_dynamics.py` (`truncated_cascade_sizes`, `percolation_labels`
  reusing `symmetric_edge_probabilities` and the exact draw order of
  `simulate_ic_percolation`, `SIM_SEED=0`), `verify_local_dynamics.py` (labels reproduce
  `cache_cascades_<tag>.npy` bit-for-bit; size at r ≥ diameter == full size),
  `probe_local_predictors.py`, `analyse_local_predictors.py` (matched RF cells via
  `analyse.load()`).

### L4 — seed-set quality (≈ 30 min, 0 fits, can run now)
- Greedy on draws 0–1999 vs top-k by RF at each radius vs degree-discount vs **top-k by
  true σ_i (the overlap-blindness control)**; set spread on draws 2000–3999; k = 50.
- **Prediction:** oracle-top-k/greedy < 0.95 on facebook (overlapping ego-nets), > 0.98 on
  p2p; RF-top-k set spread reaches 0.98 of its r=3 value at r ≤ 1 everywhere.
  **Counter/stop:** ratio ≥ 0.98 on all five → one table, lane collapses into
  `RESULTS_topk.txt`.
- Files: `probe_seed_sets.py`, `analyse_seed_sets.py` (reads `cache_oof_<tag>.npz`);
  `greedy_seed_set`, `set_spread` in `local_dynamics.py`.

### L2 — Zhang 2024 positioning + NB walk counts (minutes now; fits only if gated in)
- Study section + README/HANDOFF prior-work rows: `h_index_1..3` **is** Zhang's iterative
  H-index; what the repo adds (exact r-ball guard, ε with seed stability, four targets,
  estimator invariance, zero-training baselines, buffered CV, target-noise bootstrap).
  Add missing citations: Kitsak 2010, Lü 2016, Guilbeault–Centola.
- `nb_walk_counts(net, r)` via `build_nonbacktracking_direct` — the r-truncated analogue of
  NB centrality and of Zhang's NWC; nb_walks_1 = degree, nb_walks_2 ≈ CI_1, so register
  from r=2 and gate on `analyse_features.py`'s new-information R² before any fit.
- **Prediction:** nb_walks_3 standalone within 0.02 τ of h_index_3, below RF node tier.
  **Counter:** beats the RF node tier at r=2 on ca-GrQc/p2p. Add-one fits ≈ 49 min, after
  the queue and only if the R² gate passes and L3's counter did not fire.

### L7 — anisotropy features vs bridge residuals (seconds now; ≈ 24 min of fits if gated in)
- At the hop-1→2 expansion of `neighbourhood_pass`, bincount shell-2 parents by first-hop
  neighbour → max branch share, branch entropy (hop 2, node tier). **New module, do not edit
  `features.py`** (hash-bound caches).
- Gate: new-information R² vs `ego_betweenness`/`edge_overlap_*` < 0.95; test |Cliff's d|
  against the Finding 8 directional residual (0 fits, reads `cache_oof_*`).
- **Prediction:** |d| > 0.2 on ≥3/5; add-one gain at r=2 < 0.005. **Counter:** R² > 0.95 → drop.

### L1 — β/β_c sweep, H1 (MVP ≈ 45 min after the queue; full ≈ 25 h)
- Run the **unmodified** `stage1_prepare.py` / `stage2_sweep.py` with
  `cwd=results/phase7_beta/m<mult>/` and `PYTHONPATH=<repo>` (both scripts resolve caches
  and `sweep_<tag>.csv` relative to cwd; `sweep_inputs` takes `root="."`) — root caches
  untouched, nothing at repo root. Betweenness is p-independent: spread targets only; the
  `dynamic` tier is p-dependent so stage 1 re-runs per multiple.
- **Empirical criticality locator, pre-registered:** β_c from the NB operator is an
  infinite-size threshold; on 1–8k nodes "m = 1.0" is not demonstrably critical. Locate the
  peak of between-node CV / second-largest-cluster size from the same draws (zero cost) and
  plot r\* against both m and the locator.
- **Three r\* rules, pre-registered:** relative ε (repo default); noise-normalised (smallest
  r within 2·sd_seed of the ceiling, `analyse_topk.py` §4 rule); target-noise-normalised via
  the frozen arm of `probe_target_noise.py` (split-half draws, 0 fits). The relative rule
  alone "confirms" H1 by ceiling collapse near m = 1.
- **Prediction (H1):** r\*(0.05, spread_mean) peaks at m ∈ [1.0, 1.25] on both MVP networks
  under the noise-normalised rule. **Counter:** near threshold cascades stay inside the 1–2
  ball so r\* is *smallest* at m ≈ 1 and rises with m until σ_i ≈ P(giant) is
  degree-dominated at m ≥ 3 — a peak at intermediate m > 1 misread as "at criticality".
  H1 stands only if the peak sits at or below the empirical locator.
- MVP: email-Eu-core + p2p-Gnutella08, m ∈ {0.8, 1.0, 2.0, 3.0}, spread_mean, tiers
  {node+edge+subgraph, full}, 5 seeds: 40 cells × 7.3 s ≈ 5 min per (net, m). spread_cv /
  spread_resid excluded below m = 1.25 (ill-defined when mean ≈ 1).
  **Stop rule:** r\* unchanged across m under the noise-normalised rule on both → H1 dropped,
  L6 runs at 1.5× only. Non-monotone on ≥1 → full sweep (5 multiples × 5 nets × 480 cells
  ≈ 25 h) before L6.
- Files: `probe_beta_sweep.py` (controller shelling out to stage1/stage2 per cwd; resume is
  stage2's), `analyse_beta_sweep.py` (reuses `locality_horizon` + the two noise rules).

### L5 — complex-contagion arm (gate 0 fits; pilot ≈ 30 min; full ≈ 2.4 h)
- **Correction to the deck:** Kempe-style LT with uniform random thresholds *does* have a
  live-edge shortcut (each node keeps ≤ 1 incoming arc; sizes are subtree sizes) and its
  single-seed marginal is the weighted-cascade convention — it is submodular and not
  complex contagion in the Centola sense. The genuine arm is **fixed fractional θ** or
  bootstrap percolation with absolute threshold 2, seeding the closed neighbourhood N[i] to
  sidestep the 1/k_j < θ degeneracy the deck flags.
- Vectorised deterministic cascades `S ← S | ((S@A)/k ≥ θ)` over a (batch × n) bool matrix;
  minutes per (network, θ). **Gate first:** ignition fraction must lie in [0.1, 0.9] at
  θ ∈ {0.1, 0.2}; expect ≤ 2/5 networks to pass. Fits only where it does: 3 tiers (drop the
  IC-specific dynamic tier) × 4 r × 10 seeds = 120 cells ≈ 15 min per (net, θ).
- **Prediction:** where ignition is intermediate, r\*(spread_θ) ≥ r\*(spread_mean) + 1
  (wide bridges, not hubs). **Counter:** ignition is decided by whether N[i] touches a
  vulnerable pair → r\* ≤ 2.
- Files: `threshold_cascade_sizes` in `local_dynamics.py`; `probe_threshold_arm.py` (gate +
  `cache_targets_<tag>__theta<x>.csv` under `results/phase7_threshold/`, stage2 with cwd
  there); `analyse_threshold_arm.py`.

### L6 — certificate on the synthetic corpus (= D3; MVP ≈ 3.2 h; full ≈ 16.5 h)
- After L1 decides the multiple. `stage0_generate.py --n 5000 --families gamma,controls`
  (11 graphs) → `verify_generators.py` → cwd-isolated stage1/stage2 under
  `results/phase7_certificate/`, reduced protocol (spread_mean + betweenness, 3 tiers,
  5 seeds); add `nb_spectral_gap` (`eigs(k=2)` on the Ihara–Bass form, seconds).
- **What it can and cannot be:** per-axis trends, not a certificate — within the γ family at
  fixed n, ⟨k⟩ the duel ratio and γ are collinear (8 points) and r\* takes ≤ 4 integer
  values. Primary statistic pre-registered as the continuous τ₁/τ₃ (or hop-gain area);
  r\* secondary. Say so in the prereg.
- **Prediction:** τ₁/τ₃ for spread_mean decreases with γ; NB gap adds nothing once the duel
  ratio is controlled. **Counter:** τ₁/τ₃ increases with γ. Full 31-graph corpus only if the
  γ family shows a monotone trend outside seed sd.
- Files: `analyse_certificate.py` (reuses `structure.localization_duel`,
  `structural_profile`).

### Not lanes
- GNN depth = radius: Phase 7 / separate env (standing rule) — it is the only honest
  ceiling probe for the gap; note in the study, do not start.
- Theorems: cite local-weak-convergence work (referee D5); no proofs.
- V-information: one paragraph naming what P(r) over family V is.

## 3. Sequence and stop rules

```
now (single-thread, 0 fits)  L3 → L4 → L2 standalone / L7 gate
after queue (~2026-09-16)    §0 Angle 4 → L1 MVP → [L1 full] → L5 gate/pilot → L6 MVP → [L6 full]
```
- L3 counter fires → cancel L2/L7 fits; L4 uses E(r) rankings beside RF.
- L4 ratio ≥ 0.98 everywhere → one table, stop.
- L1 flat under the noise rule on both MVP networks → drop H1, L6 at 1.5× only.
- L5 gate fails on all five → report the gate, no fits.
- Any lane > 3 h of fits is justified in the prereg against the 33 h A7-refit precedent.

## 4. Verification
- `verify_local_dynamics.py` (labels bit-identical to `cache_cascades_*`; truncated size at
  r ≥ diameter equals full; nb_walks_1 == degree; branch shares sum to 1; greedy gains
  non-increasing; LT on a hand-built 6-node graph) — green before any probe.
- The four gates (`verify_pipeline.py`, `verify_generators.py`, `verify_docs.py`,
  `verify_c3_scoring.py`) green after every doc/code change; `verify_docs.py`'s
  `sweep_*.csv` glob is the root-leak check.
- Every lane: scored addendum appended to `docs/prereg/prereg_phase6_5_lanes.md` with verdicts per
  prediction/counter; dated worklog entry; `record_work` (folder Logs).
- Registered C3/A7/B1/B2/C6 numbers untouched; new results compared side by side.

## 5. Decisions Rachit made (2026-09-12 16:40 IST)

| Decision | Rachit's answer | Consequence for the plan |
|---|---|---|
| Lanes | **All seven, in the plan's order** | §2 and §3 stand as written |
| Zero-fit lanes beside the queue | **Yes, run now** | L3/L4/L2-standalone/L7-gate start after §0 at `OMP_NUM_THREADS=1`; dated `fit_seconds` contamination note goes into the stage 1–3 write-ups |
| L5 model | **Fixed fractional θ, N[i] seeding** | θ ∈ {0.1, 0.2}; bootstrap variant not built |
| L1 scale | **Full sweep upfront** | Replace the MVP: 5 multiples m ∈ {0.8, 1.0, 1.25, 2.0, 3.0} × 5 networks × all spread targets (spread_cv/spread_resid still excluded below m = 1.25 as ill-defined) ≈ 25 h, queued behind §0; the pre-registered predictions, the empirical criticality locator and the three r\* rules are unchanged; the "flat → drop H1" stop rule now decides only whether L6 uses one multiple or a scan |

Revised sequence:

```
now (single-thread, 0 fits)  §0 queue Angle 4 → prereg + verifier → L3 → L4 → L2 standalone → L7 gate
after queue (~2026-09-16)    Angle 4 (1 h) → L1 full (25 h, resumable per (net, m)) → L5 gate/pilot → L6 MVP → [L6 full]
```

---

## L3 scored addendum — 2026-09-13 12:46 IST — Astra

Full run: all five networks, 4,000 draws each, with every full cascade-size
column exactly equal to the corresponding cache. Predictor draws 0–1999 and
held-out target draws 2000–3999; no fits. Radius zero has undefined tau and is
unscored. Source/configuration/input/output hashes are in the network sidecars.
Evidence: `results/phase6_5_local/analysis.json` and `scores.csv` (the latter
includes the registered coverage comparison).

| Network | E(1) tau | E(2) tau | E(3) tau | RF structural r=3 tau |
|---|---:|---:|---:|---:|
| ca-GrQc | 0.773899 | 0.853790 | 0.878247 | 0.944106 |
| ca-HepTh | 0.717487 | 0.830311 | 0.875394 | 0.950793 |
| p2p-Gnutella08 | 0.665509 | 0.755800 | 0.792533 | 0.915965 |
| email-Eu-core | 0.868768 | 0.933350 | 0.948937 | 0.968655 |
| facebook_combined | 0.684290 | 0.756728 | 0.793972 | 0.958623 |

- Monotonic tau at radii 1–3: **SUPPORTED, 5/5**.
- E(1) beats RF node r=1 on the three sparse networks: **FALSIFIED, 0/3**.
- RF structural exceeds E(r) by at least 0.03 at both r=2 and r=3 everywhere:
  **FALSIFIED as universal, 4/5**. Email r=3 gap is 0.019719; its r=2 gap is
  0.030381. All other networks satisfy both margins.
- Counter E(3) >= RF structural r=3 on at least four networks: **NOT SUPPORTED,
  0/5**. L2/L7 are not cancelled by this gate; their reconstruction gates remain.

Limits registered before execution still apply: cached RF scores use full-draw
training/evaluation targets, whereas E(r) uses independent halves. These are
therefore descriptive estimator comparisons with unequal target-noise protocols,
not a pure estimator-only intervention. Increasing expected reachable size does
not mathematically guarantee increasing rank correlation; the observed monotonic
result is empirical. No population information ceiling is established.

Measured network work totals 104.93 seconds (12:43:50–12:45:35), process-lifetime
peak working set 232.78 MiB. Analysis completed 12:46. The concurrent Stage 1
fit_seconds window is contaminated by this single-thread computation.
## L2 execution definitions — 2026-09-13 18:11 IST — before standalone extraction

The standalone target is the existing full-draw `spread_mean` cache, matching
both cached H-index and RF comparisons. For each network, report Kendall tau-b
for NB walk lengths 1–3 and H-index order 3. The registered length-3 comparison
uses absolute tau difference <= 0.02; the RF comparison uses the mean of all ten
node-tier radius-2 seeds. Report each network separately and the universal
five-network prediction. The counter requires strict improvement over that RF
reference on both ca-GrQc and p2p-Gnutella08. Missing/undefined cells are unscored.

Walk length 3 uses information radius 2, while cached H-index order 3 uses
radius 3; the registered H-index comparison is therefore a descriptive benchmark
across unequal observation radii. Report that difference beside the scores.
NB length 2 is sum(degree(v) - 1) over neighbors v, and is related to, but is
not generally equal to, collective influence CI_1.

The later reconstruction gate inherits `analyse_features.py`'s DERIVED_R2=0.999:
R2 >= 0.999 marks a candidate reconstructible; undefined R2 cannot pass. Its
predictors are existing node-tier features available at the candidate's declared
information radius; the candidate itself is excluded. Use the already registered
4,000-row maximum, seed 0, 30% held-out HGB protocol only after Stage 4 succeeds.
This gate is not part of the zero-fit standalone execution.
## L4 scored addendum — 2026-09-13 18:14 IST — Astra

Full run 18:12:01–18:13:31, 89.14 s summed network work, no fits. All five
networks matched all 4,000 cached cascade-size columns exactly. Each of 88
policies selected 50 nodes, with greedy and individual Monte Carlo influence
using draws 0–1999 and all policies evaluated on the same draws 2000–3999.
Evidence: `results/phase6_5_seed_sets/analysis.json`, `scores.csv`, and per-network
NPZ/JSON files containing seed vectors, paired draw spreads and provenance.

| Network | Greedy mean spread | Individual top-sigma / greedy | Degree-discount / greedy | RF .98 radius, node / structural |
|---|---:|---:|---:|---:|
| ca-GrQc | 176.0135 | 0.498013 | 0.961619 | 0 / 0 |
| ca-HepTh | 276.4475 | 0.538616 | 0.991841 | 0 / 0 |
| p2p-Gnutella08 | 404.6200 | 0.795685 | 0.867640 | 0 / 0 |
| email-Eu-core | 271.5060 | 0.898849 | 0.954299 | 0 / 0 |
| facebook_combined | 390.9005 | 0.493705 | 0.930468 | 0 / 0 |

- Facebook individual-top-sigma/greedy < 0.95: **SUPPORTED**.
- P2p individual-top-sigma/greedy > 0.98: **FALSIFIED**.
- RF set-spread reaches 0.98 of its own radius-3 value at radius <=1 everywhere:
  **SUPPORTED for both tiers**, already at radius0 on all five. All ten seeds
  agree with their mean-curve radius in every network/tier.
- Counter/stop, individual-top-sigma/greedy >=0.98 on all five: **NOT SUPPORTED**;
  no network reaches the threshold. Do not collapse this lane to a null result.

A small relative RF radius does not imply near-greedy policy quality: its
reference is the RF radius-3 policy, not greedy. The individual-top-sigma
control uses training-half Monte Carlo means, not exact expected influence.
Greedy optimises the sampled training objective and is not a proven optimal
set. RF training labels include the evaluation draws, so its policy comparison
retains target-noise reuse. Degree-discount and E results are descriptive
comparators, not additional registered predictions. The concurrent Stage1
fit_seconds interval is resource-contaminated by this single-thread run.
## L7 execution definitions — 2026-09-13 18:17 IST — before feature extraction

Ruling: use reported-arm betweenness at structural radius3 for the primary
bridge-residual comparison, because Finding8's local-bridge sign discussion
concerns that target. Report spread_mean and historical raw betweenness as
separately labelled sensitivity checks, not substitute primaries. Changing this
choice would change the interpretation of the cross-network prediction, so all
three contrasts are retained. Reported betweenness uses rf_log1p OOF; no silent
fallback to the raw archive. The current cache/source hashes identify the exact
snapshot; this is a new comparison, not a claim to reproduce the old table.

Use all ten seeds and the existing `analyse_failures.mean_delta`, percentile
ranking and `standardise_residual` definitions. Compare the largest and smallest
5% of adjusted residuals, k=max(10, round(0.05*n)), matching that module's default.
Break exact adjusted-residual ties by smallest node index; report the tie rule.
Positive d means larger feature values among under-predicted nodes. No universal
sign is predicted. Features do not use residuals or targets for their definition.

Score the two registered features separately (maximum branch share and natural-log
branch entropy). For the lane's |d|>0.2 prediction, a network qualifies if either
feature exceeds 0.2 in absolute directional Cliff's d; success requires >=3/5 on
the primary contrast. This is a predeclared maximum across two features, not two
independent confirmations. Retain both effect sizes, group sizes and empty-shell
flags; missing/invalid primary inputs remain unscored. Sensitivity contrasts do
not rescue a failed primary prediction. An empty shell2 gives zero for both
features as already registered; it is not silently excluded from the contrast.

The reconstruction gate remains deferred until Stage4. Predictors are the cached
ego_betweenness and all edge_overlap_* features available by radius2; reconstruct
each candidate separately under the registered HGB protocol. R2<0.95 passes,
R2>=0.95 fails (boundary ruling), undefined R2 remains unscored. Residual association
alone does not establish new information or authorise an add-one fit.
## L2 standalone scored addendum — 2026-09-14 12:13 IST — Astra

Full zero-fit execution completed12:13:03, exit0, all five validated networks.
Evidence: `results/phase6_5_nonbacktracking/analysis.json`, per-network arrays
and provenance, and `results/logs/l2_full_20260914.txt`. Summary independently
rechecked current input/source identities and recomputed counts and scores.

| Network | NB length3 tau | H-index3 tau | RF node radius2 mean tau |
|---|---:|---:|---:|
| ca-GrQc | 0.747899 | 0.770837 | 0.942144 |
| ca-HepTh | 0.820623 | 0.760281 | 0.945688 |
| p2p-Gnutella08 | 0.876171 | 0.763015 | 0.885393 |
| email-Eu-core | 0.959704 | 0.902486 | 0.959346 |
| facebook_combined | 0.862449 | 0.726746 | 0.955370 |

- NB3 within0.02 tau of H-index3 everywhere: **FALSIFIED, 0/5**. NB3 is above
  H-index3 on four networks and below it on ca-GrQc.
- NB3 below RF node radius2 everywhere: **FALSIFIED as universal, 4/5**.
  Email's NB advantage is only0.0003584; the strict registered sign rule fails,
  but this small difference is not evidence of statistical superiority.
- Counter, NB3 strictly beats RF node radius2 on both ca-GrQc and p2p:
  **NOT SUPPORTED, 0/2**.

All predictors use the same full-draw spread_mean target. NB length3 has
information radius2, H-index3 radius3; the H-index contrast is explicitly
unequal-radius and descriptive. R2 reconstruction and any add-one fits are
**UNSCORED / DEFERRED** until genuine Stage4 completion. L3's cancellation
counter did not fire, but the standalone result alone does not pass that gate.
The execution used one thread beside buffered CV; concurrent fit_seconds
is resource-contaminated. Source-scoped review approved the three files and
the fixture/input/resume verifier passed before this full run.
## L1 controller scope clarification — 2026-09-14 12:16 IST — before preparation or fits

The approved full-sweep instruction says all spread targets. The explicit cache
columns are spread_mean, spread_std, spread_cv, spread_resid and spread_ignition;
exclude spread_cv/spread_resid below multiple1.25 as registered. The primary H1
claim remains spread_mean on the originally named email/p2p pair; the other
networks/targets are retained and labelled, not substituted for a failed primary.
Five multiples (0.8,1.0,1.25,2.0,3.0), five networks, four tiers, radii0..3 and ten
seeds imply16,800 cells: 480 at each of the two lower multiples and800 at each
of the three higher multiples per network. Thus25h is an earlier rough estimate,
not a measured duration or permission to silently omit auxiliary spread columns.

Controller preparation and no-fit fixture tests may proceed now. No stage1
preparation or stage2 fitting for this lane runs before the recovery controller's
genuine ALL STAGES COMPLETE terminal state, with no active recovery owner.
Old September13 Stage2–4 completion strings are specifically insufficient.
The beta directories are `results/phase6_5_beta/m<multiple>/`; production entry
points stay unmodified and all scientific outputs stay inside those directories.
A prepared controller does not score the still-unimplemented empirical locator
or noise-normalised horizon analyses. Their precise execution definitions and
verification must be completed before this lane's full run is launched.

## L1 execution definitions — 2026-10-12 12:15 IST — before any L1 preparation or fits

Written by Claude Opus 5.5. Rachit decided the locator choice in chat (12:14): "χ primary
with the fine grid". Nothing in this section has been computed. No L1 controller,
analyser or cache exists yet. This addendum supplies the "precise execution definitions"
that the 2026-09-14 12:16 clarification requires before the full run. It changes no
prediction, counter or stop rule above.

### A. Gate status

The 2026-09-14 clarification gates L1 preparation and fits on the recovery controller's
"genuine ALL STAGES COMPLETE terminal state, with no active recovery owner". That literal
state was never reached.

- `results/recovery_20261007/controller.log` ends with `FAILED stage4 exited 1`
  (2026-10-12 05:57:30).
- Every stage 4 fit finished (05:57:27). The only failing step is the verifier's
  CHECK 1, which missed its 1e-6 bar on model rows (max |Δτ| 0.012). The miss is traced
  to registry column order, and its prescribed action, re-quoting Angle 4, is done.
- Rachit declared stage 4 COMPLETE at 11:35 on 2026-10-12 ("mark stage 4 complete";
  LOG 2026-10-12 11:41). The `FAILED` line is kept as evidence.
- No recovery lock is active; only two renamed stale locks remain.

**The gate is therefore treated as met by Rachit's ruling, not by the controller's
terminal string.** This is recorded here so that L1 does not launch on a gate that its
own record shows as failed.

### B. Empirical criticality locator

**Primary: percolation susceptibility.** For a network at multiple m, draw J
bond-percolation realisations. S₁ⱼ is the number of nodes in the largest connected
component of draw j. Then

  χ(m) = Var_j(S₁) / Mean_j(S₁)      (sample variance, ddof = 1)

and **m\*_χ = argmax of χ over the fine grid below.** Ties go to the smallest m.

**Secondary, reported and labelled, never substituted for the primary:**

- the argmax of the mean second-largest component size ⟨S₂⟩;
- the argmax of the between-node CV, sd_i(σ̄_i) / mean_i(σ̄_i), where σ̄_i is node i's
  mean reached-set size over the draws.

If the three disagree, every one of them is reported; the verdict uses χ only.

**Why χ and not the CV.** The CV is computed from the per-node spreads, which are the
target whose locality r\* measures. χ and ⟨S₂⟩ depend only on the percolation, so they
can falsify the counter-prediction ("a peak at intermediate m > 1 misread as at
criticality") without sharing a quantity with the outcome. Radicchi (2015,
arXiv:1412.3678) reports that 1/λ₁ of the non-backtracking matrix, the β_c used here,
is often a tight lower bound on the true threshold of real networks. So m = 1.0 is not
assumed to be critical.

**Recovering S₁ and S₂ from a cascade cache needs no new draws.**
`simulate_ic_percolation` stores, for every node and draw, the size of the node's
component (`sizes[i, j] = comp_sizes[labels][i]`). A component of size s therefore
contributes exactly s entries equal to s, and:

- S₁ⱼ = max_i sizes[i, j];
- the number of components of size s in draw j is #{i : sizes[i, j] = s} / s, which
  gives S₂ⱼ, with S₂ⱼ = S₁ⱼ when two components tie for largest.

**Fine grid.**

- m ∈ {0.50, 0.55, …, 3.00}, 51 points. It contains all five sweep multiples
  (0.8, 1.0, 1.25, 2.0, 3.0) and the historical 1.5.
- J = 500 draws per point.
- p = `transmission_probability(β_c, m)`, with β_c the value recorded in the network's
  `cache_meta_<tag>.json`, which is the value stage 1 recomputes.
- `simulate_ic_percolation(net, p, n_sims=500, convention="uniform", seed=0)` at every
  point. Under `uniform` the generator is used only for the live-edge uniforms, so a
  common seed couples the draws across m. That reduces argmax noise; the fixture test
  in D checks it.
- No fits.
- Output: `results/phase6_5_beta/locator/<tag>.csv`, one row per m, with χ, ⟨S₂⟩, CV,
  p and β_c.

**The locator is computed and recorded before any L1 stage 1 or stage 2 cell runs**, so
m\*_χ is fixed before any r\* exists.

**Uncertainty.** A 200-replicate bootstrap over the 500 draws gives the spread of the
argmax. It is reported and not used in the verdict.

**Boundary.** If m\*_χ falls at 0.50 or 3.00, the locator is undetermined for that
network. This is reported, and H1 is not scored there.

**Locator bin.** m_loc = the smallest sweep multiple ≥ m\*_χ.

### C. r\* rules

The three rules registered above are kept. For each one, r\* is computed per
(network, m, target, tier) from the 10 seeds × radii 0–3 of `sweep_<tag>.csv` in
`results/phase6_5_beta/m<m>/`.

**Primary tier: `node+edge+subgraph`.** This is `analyse.FULL`, the default of
`locality_horizon`, and the tier every existing r\* in the project uses. The `full` tier
(with `dynamic`) is reported beside it.

1. **Relative rule.** `locality_horizon(sweep, epsilon)` as implemented, at
   ε ∈ {0.10, 0.05, 0.02}. Reported. The registered text warns that it can "confirm" H1
   by ceiling collapse.

2. **Noise-normalised rule (primary for H1).** The ceiling radius r_c is the argmax of
   the mean τ over seeds; ties go to the smaller r. For each r, take the paired per-seed
   differences dₛ(r) = τₛ(r_c) − τₛ(r). Then

     r\*_noise = the smallest r with mean_s dₛ(r) ≤ 2 · sd_s(dₛ(r))   (ddof = 1).

   r_c always qualifies. The rule is paired because every seed draws the same folds for
   every radius. A7 found all 45 covariances positive, with the paired SD about 0.58 of
   the unpaired one, so an unpaired SD would be too lenient and would bias r\* low.
   `analyse.py`'s `beats_noise` uses the same yardstick, 2 × the SD of per-seed
   differences.

   **Correction to the registered wording.** The rule was cited above as "`analyse_topk.py`
   §4 rule: smallest r within 2·sd_seed of the ceiling". `analyse_topk.py` §4 is a sign
   test on p@1% vs τ horizon shifts and contains no such rule, so this definition
   replaces the citation.

3. **Target-noise rule.** Its input is executable without fits: stage 2 writes
   `cache_oof_<tag>.npz` into each m directory, and `probe_target_noise.py` reads its
   cwd caches. **TBD.** Two things are not yet defined:
   - the threshold;
   - whether "split-half draws", as registered above, or the column bootstrap that
     `probe_target_noise.py` implements is the resampling unit.

   This rule is reported only. It must be defined in a further dated addendum before the
   full run launches. It does not block the primary verdict.

### D. Verdict

For each network, take the primary series r\*_noise(m) for `spread_mean` and tier
`node+edge+subgraph` over the five multiples.

- **Flat:** r\*_noise is equal at all five. Under decision 5 this sends L6 to one
  multiple rather than a scan.
- Otherwise, P is the set of multiples where r\*_noise is largest, and m_peak = min(P).
- **The prediction**, a peak at m ∈ [1.0, 1.25], is scored as written above, on m_peak.
- **H1 stands** on a network only if it is not flat, its locator is determined, and
  m_peak ≤ m_loc ("H1 stands only if the peak sits at or below the empirical locator").
- **Primary claim:** email-Eu-core and p2p-Gnutella08, as registered. The other three
  networks and the other targets are reported and labelled, and are not substituted for
  a failed primary.

### E. Verification before the full run

1. **Fixture test.** On hand-built graphs with known components, the S₁/S₂ recovery
   from a `sizes` matrix equals a direct `connected_components` count. This includes a
   tie for the largest component.
2. **Coupling test.** With seed 0, the live-edge set at a larger m is a superset of the
   set at a smaller m. So S₁ⱼ is non-decreasing in m, draw by draw.
3. **Cache agreement, now, with no new fits.** χ from the existing root 1.5× caches
   (4,000 draws) agrees with the fine-grid point m = 1.50 within 3 bootstrap SE. The
   same check is repeated against each m directory's 4,000-draw cache once stage 1 has
   written it.
4. **Rule tests.** The r\* functions are tested on synthetic sweep frames covering:
   - a tie at the ceiling;
   - sd = 0 with a positive mean gap;
   - a flat series;
   - a peak at an end multiple.
5. **The four gates** stay green after every change, as section 4 requires.

## L1 target-noise rule — 2026-10-12 12:31 IST — before any L1 sweep data

Written by Claude Opus 5.5. Rachit agreed it in chat at 12:28 ("agree with 1-4"). It
closes the TBD left in part C, rule 3, of the 12:15 addendum. No L1 sweep cell exists.
The locator was recorded at about 12:29 (`results/phase6_5_beta/locator/`), and no
r\* has been computed. Nothing above is changed. **Whether a "robust" label is
registered is still open.** It is not decided here.

**Rule 3, target-noise-normalised r\*.** It is computed per (network, m, target, tier)
in `results/phase6_5_beta/m<m>/` and runs no fits.

1. **Resampling unit: the column bootstrap, not split-half.** The registered L1 text
   says "split-half draws". This replaces that.
   - The bootstrap resamples the 4,000 live-edge draws with replacement. It rebuilds
     every target column from the resampled draws with `targets_from_cascades`
     (`probe_target_noise.py`), which is what A7 implemented and validated.
   - It reproduces the full-size sampling process and keeps the cross-node covariance.
     A split-half target is built from 2,000 draws, so its noise has to be rescaled, and
     the rescaling assumes the halves are independent.
   - The rebuild must first reproduce the m directory's `cache_targets_<tag>.csv` to
     1e-9 for every scored target, or the rule raises.
2. **Frozen model.** The out-of-fold predictions of sweep seed 0 are frozen, A7's
   default, and nothing is refit.
   - A7's refit arm found refit noise a median of 1.24× the frozen noise (range
     0.97–2.33, at 1.5×), so this rule understates target noise.
   - That ratio is reported as context. It is not applied as a correction, because it
     was measured at a different multiple.
3. **Paired across radii.** B = 200 replicates, with seed 0 for the resampling. Each
   replicate's index set is shared across targets, radii and tiers. For replicate b:

     D_b(r) = τ(y_b, ŷ_{r_c}) − τ(y_b, ŷ_r),   sd_target(r) = SD_b(D_b(r))   (ddof = 1)

   Here r_c is rule 2's ceiling radius (the best seed-mean τ), and ŷ_r is the frozen
   seed-0 prediction at radius r.
4. **Threshold, the same form as rule 2:**

     r\*_target = the smallest r with mean_s dₛ(r) ≤ 2 · sd_target(r)

   The left side is rule 2's paired seed-mean gap. Rules 2 and 3 differ only in which
   noise source the yardstick measures, so a disagreement between them is attributable
   to that source alone.

**Status: reported only.** Rule 3 does not change the H1 verdict, the stop rule or
L6's multiple. They stay on rule 2.

## L1 robustness label — 2026-10-12 13:44 IST — before any L1 sweep data

Written by Claude Opus 5.5. Rachit decided it in chat at 13:44 ("register the robust
label"). It closes the question left open at 12:31. No L1 sweep cell exists, and no
r\* has been computed. The locator was recorded at 12:29. Nothing above is changed.

**The label is a qualifier on the wording of the H1 claim, per network.** It is not a
second verdict. Let V₂ be the part D verdict computed on rule 2's r\*_noise series, and
V₃ the same verdict logic, with the same recorded locator, applied to rule 3's
r\*_target series for `spread_mean`, tier `node+edge+subgraph`.

- **"robust to target noise"**: H1 stands under V₂ **and** under V₃.
- **"stands under seed noise; not resolved against target noise"**: H1 stands under V₂
  but not under V₃. This includes a V₃ series that is flat, or whose peak lies above
  m_loc.
- **No label**: H1 does not stand under V₂, or H1 is not scored there (locator
  undetermined, or the series incomplete).

**What the label does not change:** the H1 verdict, the part D prediction, the stop rule
and L6's multiple. All of them stay on rule 2 alone.

**Why "stands under both" rather than "same m_peak".** r\* takes only the values
0–3. A one-step move in m_peak that leaves the conclusion unchanged is not fragility, and
the label asks whether the conclusion survives, not where exactly the peak sits.

**Caveat carried in the label's definition.** Rule 3 uses a frozen model. A7's refit arm
put refit target noise at a median of 1.24× the frozen figure (range 0.97–2.33, at 1.5×).
So "robust to target noise" is easier to earn than it would be under refit noise, and any
text using the label states this.

**Where it applies.** The label is attached wherever H1 is scored. The primary claim
remains email-Eu-core and p2p-Gnutella08. On the recorded locator, ca-GrQc and
facebook_combined are undetermined, so they get no label.

## L7 run status — 2026-10-13 01:56 IST — before the full extraction and the R² gate

Written by Claude Opus 5.5. Rachit's instruction (chat, 01:54): "start L7". No full
L7 output exists. This section records how the registered definitions (2026-09-12
clarification, 2026-09-13 18:17 execution definitions) are executed. It changes no
definition, prediction or threshold above.

**A. Gate status.** The R² reconstruction gate was "deferred until Stage4". Stage 4 is
treated as complete by Rachit's ruling of 2026-10-12 11:35, on the same evidence and
with the same caveat as part A of the L1 execution definitions (2026-10-12 12:15).
So the gate runs now. It uses `analyse_features.predictability` exactly:
- HistGradientBoostingRegressor, max_iter 120, 70/30 split, seed 0;
- at most 4,000 rows, drawn with `default_rng(0)` as `analyse_features.analyse` does;
- predictors: the cached `ego_betweenness`, `edge_overlap_max`, `edge_overlap_mean`,
  `edge_overlap_min` and `edge_overlap_std` (registry hop 1, all within radius 2);
- each candidate is reconstructed separately.
R² < 0.95 passes, R² ≥ 0.95 fails, and undefined R² is unscored, as registered.

**B. Add-one fits are not run.** The registered prediction "add-one gain at r=2 <
0.005" has no protocol: no target, tier, seed count or pairing is written down. No
add-one fit runs until a further dated addendum defines one. A gate pass only makes
a network eligible.

**C. Tie rule, as implemented.** `probe_branch_anisotropy.tails` orders nodes by
`np.lexsort((node, adjusted))`, ascending. The over-predicted tail is the first k
nodes and the under-predicted tail the last k. Among exact ties at a tail boundary,
the over-predicted tail therefore takes the smaller node indices and the
under-predicted tail the larger ones. This is the reading of "break ties by smallest
node index" that the reviewed code applies. Boundary ties are counted and reported
with the scores.

**D. Prior pilot, disclosed.** `results/phase6_5_anisotropy/pilot/ca-GrQc.json`
(2026-09-14, Astra) holds unscored ca-GrQc effect sizes computed on that day's caches.
The full run recomputes every network on the current caches, and the pilot is not
used in scoring. Whether its numbers were read before this section is not recorded.

**E. Run.** `python probe_branch_anisotropy.py` (all five networks, one thread, zero
fits), then the gate. Outputs go to `results/phase6_5_anisotropy/`. The scored
addendum follows the results.

## L7 scored addendum — 2026-10-13 01:59 IST — Claude Opus 5.5

Full zero-fit extraction: 2026-10-13 01:57:05–01:57:14, exit 0, all five networks.
R² gate: 10 HGB fits, run immediately after. Evidence:
`results/phase6_5_anisotropy/analysis.json`, `gate.json`, `<tag>.json`, `<tag>.npz`.
Definitions as registered on 2026-09-12 and 2026-09-13, executed as the 01:56 run
status says.

**Disclosed fix before scoring.** The first full run (01:56:30) extracted all five
networks, then `summary()` raised a TypeError: it took `abs()` of each effect's dict
rather than its d value, so no verdict was written. The rule moved into
`qualifies()` unchanged and now has a verifier case. That changed the probe's hash,
which is part of every network's recorded identity, so the five unread outputs were
deleted and recomputed (01:57). No definition or threshold changed.

Primary contrast: reported (rf_log1p) betweenness, radius 3, `node+edge+subgraph`,
ten seeds, the top and bottom 5% of adjusted residuals. d is Cliff's delta, under-
minus over-predicted. Empty shell 2: 0 nodes on every network. Boundary ties in the
primary arm: 0.

| network | k | d max share | d entropy | qualifies | R² max share | R² entropy |
|---|---:|---:|---:|---|---:|---:|
| ca-GrQc | 208 | +0.150 | **−0.205** | yes | 0.825 pass | 0.879 pass |
| ca-HepTh | 432 | −0.099 | +0.129 | no | 0.838 pass | 0.897 pass |
| p2p-Gnutella08 | 315 | +0.013 | −0.044 | no | 0.928 pass | **0.977 fail** |
| email-Eu-core | 49 | −0.090 | +0.080 | no | 0.908 pass | **0.966 fail** |
| facebook_combined | 202 | −0.140 | +0.070 | no | 0.628 pass | 0.780 pass |

- **Prediction, |d| > 0.2 on ≥ 3/5 (primary): NOT SUPPORTED, 1/5.** The one
  qualifier, ca-GrQc, clears by 0.005, through entropy, the larger of the two
  features. That maximum was predeclared.
- **Counter, R² ≥ 0.95 → drop: fires for branch entropy on p2p-Gnutella08 and
  email-Eu-core only.** Maximum branch share passes on all five networks
  (R² 0.628–0.928), and entropy on the other three. Per the registered caveat, a
  pass only makes a network eligible for an add-one fit; it is not evidence the
  feature helps.
- **Prediction, add-one gain at r = 2 < 0.005: UNSCORED.** No add-one protocol is
  registered (run status, part B), and none was run.

**Sensitivities (reported; they do not rescue the primary).** Maximum |d| over the
two features:

| arm | GrQc | HepTh | p2p | email | facebook | > 0.2 |
|---|---:|---:|---:|---:|---:|---:|
| raw betweenness | 0.234 | 0.283 | 0.020 | 0.793 | 0.491 | 4/5 |
| spread_mean | 0.055 | 0.039 | 0.066 | 0.232 | 0.021 | 1/5 |

One exact tie decided tail membership, at the over-predicted boundary of
p2p-Gnutella08's spread_mean arm.

**Reading (inference, not tested).**
- The association is large under the raw objective and mostly vanishes under
  log1p, on the same target, nodes and tails. The project has already measured
  that squared error on heavy-tailed betweenness distorts the ranking it is scored
  on (study §26). The likeliest reading is that the raw arm's residual tails track
  that distortion, which correlates with branching structure, rather than
  information that anisotropy adds. That is why the registered primary uses the
  reported arm.
- Where an effect is non-negligible on HepTh, email and facebook, the
  under-predicted nodes have the lower maximum share and the higher entropy: their
  shell 2 is spread more evenly across first-hop branches. ca-GrQc's primary
  effect has the same direction for entropy but the opposite sign for maximum
  share. No sign was predicted.

**Lane status.** The standalone and the gate are scored. The add-one fit waits for a
protocol addendum and Rachit's decision whether to run it at all.

## L1 scored addendum — 2026-11-02 04:05 IST — Claude Opus 5.5

**DRAFT. The claim wording (the paragraph marked "Claim") is Rachit's to set.**
Everything else reports what the registered rules output.

Full sweep: 25 units (5 networks × m ∈ {0.8, 1.0, 1.25, 2.0, 3.0}), all complete
2026-11-02 01:29 IST. Scored 02:29 by `analyse_beta_sweep.py score`. Evidence:
`results/phase6_5_beta/rstar.csv` and `verdict.json` (commit 1bd2924), the per-unit
`m<m>/sweep_<tag>.csv`, and the locator in `locator/` (recorded 2026-10-12 12:29,
before any sweep cell). `verify_beta_sweep.py` passes 72/72. It is a synthetic
self-test of the rules and the controller's guards, not a re-check of the sweep data.
Definitions are as registered on 2026-09-12, 2026-09-14 and 2026-10-12 (12:15, 12:31,
13:44).

**Disclosed changes during the run.** No prediction, rule, threshold or target changed.
All three changes are in the unpinned controller `probe_beta_sweep.py`. Each one
stopped the run, and each loosening was Rachit's decision.

1. **β_c identity tolerance (d63b870, 2026-10-15).**
   - E3 compared stage 1's recomputed β_c with the root cache's to a hand-set relative
     1e-12. That value was chosen from a single 1.7e-14 observation.
   - ca-GrQc@1.25 came in at 1.37e-12 and the sweep stopped. Its draws were
     bit-identical and χ was 0.008 SE away.
   - The bound is now the eigensolve's own tol, 1e-8. Draw bit-identity and the
     registered 3-SE test are unchanged.
2. **Refit duplicates (85067cd, 2026-10-13).**
   - A host reset inside a stage 2 grid row leaves cells with a CSV row but no stored
     prediction. On resume they are refitted, which appends a second row.
   - The controller now drops the stale copy, provided the duplicate qualifies under
     item 3, and records the dropped copy in `refit_duplicates_<tag>.csv`.
   - This happened in three units: facebook_combined@1.25, p2p-Gnutella08@2.0 and
     ca-HepTh@3.0.
3. **Refit score tolerance (e5a1c11, a0c69ac, 2026-11-01).**
   - Identity and input columns are compared byte for byte.
   - The five score columns are compared within an absolute 1e-6, because the n_jobs=-1
     forest is reproducible only to its last bits (about 5e-8 in τ, documented in
     `influence/experiment.py`).
   - The largest accepted difference was 1.1e-16 (facebook_combined@1.25, rmse).
   - e5a1c11 shipped with three faults that the verifier caught, and a0c69ac fixed
     them. They affected no scored number.

**Locator (recorded before the sweep).**

| network | m\*_χ | m_loc |
|---|---:|---|
| email-Eu-core | 1.15 | 1.25 |
| p2p-Gnutella08 | 1.20 | 1.25 |
| ca-HepTh | 2.35 | 3.0 |
| ca-GrQc | 3.00 | undetermined (at the grid edge) |
| facebook_combined | 3.00 | undetermined (at the grid edge) |

**Primary series.** This is r\*_noise (rule 2) for `spread_mean`, tier
`node+edge+subgraph`, ten seeds, over m = 0.8 / 1.0 / 1.25 / 2.0 / 3.0. The ceiling
radius is r_c = 3 in all 25 cells.

| network | r\*_noise | part D verdict | rule 3 (r\*_target) | label |
|---|---|---|---|---|
| **email-Eu-core** (primary) | 3 3 3 3 3 | flat → **H1 does not stand** | 3 3 3 3 3, flat | none |
| **p2p-Gnutella08** (primary) | 3 3 3 3 3 | flat → **H1 does not stand** | 3 3 3 3 3, flat | none |
| ca-HepTh | 3 3 3 3 3 | flat → H1 does not stand | 3 3 3 3 3, flat | none |
| ca-GrQc | 2 3 3 3 3 | m_peak 1.0, in [1.0, 1.25]; **H1 not scored** (locator undetermined) | 2 3 3 3 3 | none |
| facebook_combined | 2 2 3 3 3 | m_peak 1.25, in [1.0, 1.25]; **H1 not scored** (locator undetermined) | 2 3 3 3 3 (m_peak 1.0) | none |

- **Prediction (r\* peaks at m ∈ [1.0, 1.25] on both primary networks, rule 2): NOT
  SUPPORTED.** Both primary series are flat, so there is no peak.
- **Stop rule (r\* unchanged across m on both primary networks): FIRES.** H1 is
  dropped. Under §5 (the L1 scale decision), L6 runs at one multiple, 1.5×, and not as
  a scan.
- **Counter (r\* smallest near m ≈ 1 and rising with m): NOT SUPPORTED on the primary
  networks**, where r\* does not move. ca-GrQc and facebook_combined have the counter's
  rise-then-plateau shape, but on non-primary networks with an undetermined locator.
  See the reading below.
- **Robustness label:** none anywhere, because H1 is not standing under rule 2 on any
  network. Rule 3 agrees with rule 2 on every flat series.
- `analyser` writes `prediction_met: true` for ca-GrQc and facebook_combined. That flag
  only tests whether min(P) falls in [1.0, 1.25]. Each of these series is a single step
  up to a plateau at 3, so min(P) is just the first multiple of the plateau. Neither
  network carries an H1 verdict.

**Reported beside the primary (not scored).**
- **Full tier** (`node+edge+subgraph+dynamic`): the r\*_noise series match the primary
  tier on four networks. ca-GrQc reads 2 2 3 3 3 rather than 2 3 3 3 3; it is still not
  flat and its locator is still undetermined.
- **Rule 1** (relative ε, which the registration warns can "confirm" H1 through ceiling
  collapse), spread_mean, primary tier:

  | network | ε = 0.10 | ε = 0.05 | ε = 0.02 |
  |---|---|---|---|
  | email-Eu-core | 0 1 1 0 0 | 1 1 1 1 1 | 1 1 1 1 1 |
  | p2p-Gnutella08 | 1 1 2 2 1 | 1 2 2 2 2 | 2 2 3 3 2 |
  | ca-HepTh | 1 1 1 2 2 | 1 1 1 2 2 | 1 1 2 3 3 |
  | ca-GrQc | 0 1 1 1 2 | 1 1 1 2 2 | 1 1 1 2 3 |
  | facebook_combined | 0 1 1 1 1 | 1 1 1 1 1 | 1 1 1 1 2 |

- **spread_cv and spread_resid** are scored at m ≥ 1.25 only, as registered. Rule 2
  puts them at r\* = 3 everywhere, with these exceptions:
  - email-Eu-core spread_cv: 2 3 3;
  - facebook_combined spread_cv: 2 3 3;
  - email-Eu-core spread_resid: 2 0 0. Its ceiling falls to r_c = 0 at m = 2.0 and
    r_c = 1 at m = 3.0;
  - facebook_combined spread_resid: 2 2 3;
  - p2p-Gnutella08 spread_resid: 3 3 2.
- **spread_std and spread_ignition** are in every sweep CSV. Per the 2026-09-14
  clarification, they were fitted and not dropped. The analyser scores neither.
  spread_ignition's τ is undefined in 2,240 of its 4,000 rows. Those are the 14 units
  where the ignition column has no rank variation: GrQc and HepTh below 3.0, and
  facebook and p2p below 2.0. email-Eu-core is defined everywhere. **No rule was
  registered for either target, so neither carries a verdict.**

**Reading (inference, not tested).**
1. **"Flat" means r\* sits at the edge of the radius grid. It does not mean r\* is
   invariant to β.**
   - r_c = 3, the largest radius fitted, in every primary cell. So these data show
     r\* ≥ 3 at every multiple and cannot place a peak above 3.
   - The paired yardstick is very tight. On the primary networks, 2·sd at r = 2 is
     0.0004–0.0011 τ. That makes
     r\*_noise "the smallest radius statistically indistinguishable from the ceiling",
     and any real gain from r = 2 to r = 3 puts it at 3.
   - The gains are real but small:

     | network | m = 0.8 | 1.0 | 1.25 | 2.0 | 3.0 |
     |---|---:|---:|---:|---:|---:|
     | email-Eu-core | 0.0019 | 0.0034 | 0.0050 | 0.0048 | 0.0021 |
     | p2p-Gnutella08 | 0.0015 | 0.0051 | 0.0196 | 0.0314 | 0.0120 |

     These are the paired mean τ gaps from r = 2 to r = 3. Each is 2.0–39.5 times its
     2·sd threshold. The smallest margin is email@3.0, at 2.0 times.
   - The size of that gain does vary with m, and on both networks it is largest at
     m ≥ 1.25. That is a continuous quantity, like the τ₁/τ₃ statistic registered for
     L6. **It was not registered for L1 and is not scored here.**
2. **ca-GrQc and facebook_combined do not partly support H1.** Each is one step up to a
   plateau. That shape matches the registered counter, whose "smallest near m ≈ 1,
   rising with m" describes it, more than it matches a peak.
3. **The locator does not settle criticality on the larger networks.** It puts the χ
   peak at 3.0 on GrQc and facebook, and at 2.35 on HepTh, against the NB β_c's
   m = 1.0. On these graph sizes the NB threshold is not the effective critical point.
   The registration anticipated this ("on 1–8k nodes 'm = 1.0' is not demonstrably
   critical").

**Claim (Rachit's wording; the line below is a placeholder, not a claim).**
> TBD: one or two sentences stating what L1 shows about H1. Constraint from the
> evidence: the claim can say H1 is not supported at r ≤ 3. It cannot say r\* is
> invariant to β, because of reading 1.

**Lane status.** L1 is scored. H1 is dropped on the primary networks by the registered
stop rule. L6 runs at 1.5× only. No further L1 fits are planned. A radius-4 extension
would be a new registration, not part of this lane.

## L5 execution definitions — 2026-11-02 10:55 IST — before any L5 cascade on a real network

Written by Claude Opus 5.5.
- **Decided by Rachit in chat (asked 04:12, answered about 10:54):** "Relative ε=0.05 primary" and "> 5% of n".
- **Agent definitions, open to Rachit's veto before the gate runs:** the lane-level
  aggregation in part D and the overlap rule.

No threshold cascade has been run on any of the five networks. The only code is
`influence/threshold_dynamics.py`, with `verify_threshold_dynamics.py` at 8/8 on
fixtures. The prediction, the counter, θ ∈ {0.1, 0.2}, N[i] seeding, the gate band
and the stop rule above are unchanged.

### A. Why the r\* rule has to be named

- The L5 text writes "r\*" and names no rule.
- Under rule 2 of the L1 definitions (paired noise), r\*(spread_mean) at the root
  1.5× is 3 on all five networks. That is r_c, the largest radius fitted. The
  number was computed 2026-11-02 from the existing root `sweep_<tag>.csv`, which
  holds no L5 data.
- So "r\*(spread_θ) ≥ r\*(spread_mean) + 1" would need r\* = 4, and radii are 0–3.
  Under rule 2 the prediction could never be supported.

### B. Model and target

- **Model:** `threshold_cascade_sizes(net, θ)`. Seed N[i]. A node j activates once
  (active neighbours) / k_j ≥ θ, with ≥ tested exactly in integers. Iterate to the
  fixed point.
- **Determinism:** the model is deterministic, so there is one cascade per node and
  no draws. Rule 3 (target noise) does not apply.
- **spread_θ** is node i's final cascade size, N[i] included. This is the same
  convention as spread_mean, which includes the seed.
  - **Caveat (inference):** a cascade that fizzles has size ≥ k_i + 1. Where most
    nodes fizzle, degree alone ranks much of spread_θ, which favours a small r\*.
    That leans toward the counter, and the scored text must say so.
- **Networks:** the five project networks, loaded exactly as stage 1 loads them,
  with n and m checked against `cache_meta_<tag>.json`.

### C. Gate (0 fits)

- **Ignition:** node i ignites at θ if spread_θ(i) > 0.05 · n. This is strictly
  greater, as in production `CascadeResults.ignition_probability(0.05)`.
- **Ignition fraction:** the mean of that indicator over all n nodes.
- **Pass:** the ignition fraction lies in [0.1, 0.9], inclusive, per (network, θ).
- **Output:** `results/phase7_threshold/gate.json` holds, per (network, θ):
  - the fraction;
  - pass or fail;
  - n;
  - the size quantiles;
  - the source hashes.
- If no (network, θ) passes, the gate is reported and no fits run (§3).

### D. Fits and r\*

Fits run only for passing (network, θ) pairs.

**Protocol.**
- Unmodified stage 2 with `cwd=results/phase7_threshold/`.
- spread_θ is added as a target column named `spread_theta<θ>`.
- Tiers: `node`, `node+edge`, `node+edge+subgraph`. The `dynamic` tier is dropped
  as registered, because it is IC-specific.
- Radii 0–3, ten seeds: 120 cells per pair.
- **How stage 2 is fed** (cache layout, feature reuse from the root caches) is
  defined in a run-status addendum before the pilot.

**Primary rule: relative ε = 0.05.**
- Per seed, `locality_horizon(sweep, epsilon=0.05, richness="node+edge+subgraph")`.
- r\* is the modal value across the ten seeds, with ties going to the smaller r.
  This is `analyse_beta_sweep.r_star_relative`, unchanged.
- **The comparison value r\*(spread_mean)** is the same function on the root 1.5×
  `sweep_<tag>.csv`. For reference, at 1.5× that value is:

  | network | r\*(spread_mean), ε = 0.05 |
  |---|---:|
  | ca-GrQc | 1 |
  | ca-HepTh | 2 |
  | email-Eu-core | 1 |
  | facebook_combined | 1 |
  | p2p-Gnutella08 | 2 |

  It was computed from data that predates L5.
- **Reported beside the primary:** ε = 0.10 and ε = 0.02, and rule 2 (paired noise)
  for both targets. The rule 2 r\*(spread_mean) is 3 everywhere, as part A says.

**Scoring, per passing pair.**
- **Prediction holds:** r\*(spread_θ) ≥ r\*(spread_mean) + 1.
- **Counter holds:** r\*(spread_θ) ≤ 2.
- Both can hold at once, for example r\*(spread_mean) = 1 and r\*(spread_θ) = 2. Such
  a pair is reported as **"both"** and counts for neither.

**Lane level.** Over the passing pairs whose outcome is not "both":
- **SUPPORTED:** the prediction holds on all of them.
- **NOT SUPPORTED:** it holds on none of them.
- **MIXED:** anything in between.

The counter is aggregated the same way. If every passing pair is "both", the lane
is **UNDECIDED**.

**Ceiling-collapse caveat.** The L1 text warns that the relative rule can "confirm"
H1 through ceiling collapse near m = 1. Here both targets are compared at the same
1.5×, so that mechanism does not apply directly. A low ceiling τ can still compress
r\* under the relative rule (inference). Each pair's ceiling τ is therefore
reported, and a pair whose spread_θ ceiling τ is ≤ 0 is unscored, because
`locality_horizon` raises on it.

### E. Verification before any real-network run

1. `verify_threshold_dynamics.py` is green. It covers:
   - hand-computed paths;
   - the exact boundary at k = 30;
   - 30 random graphs × 5 θ against a sequential queue implementation;
   - batch-size invariance;
   - monotonicity in θ;
   - the isolated-node guard;
   - the N[i] lower bound.
2. The four gates stay green after every change (§4).

## L5 run status — 2026-11-02 16:09 IST — before any L5 fit

Written by Claude Opus 5.5.
- **Decided by Rachit in chat (16:04):** keep spread_θ as the primary target and add
  the ignition indicator as a secondary target, disclosed as added after the gate.
- **Agent definitions:** how stage 2 is fed (part B), which the 10:55 definitions
  deferred to this addendum.

The gate ran at 10:56 (`results/phase7_threshold/gate.json`, committed in fd225f1).
Three pairs pass, all at θ = 0.2: ca-GrQc, ca-HepTh and email-Eu-core. No model has
been fitted on any L5 target.

### A. Secondary target, added after the gate

- **Definition:** ignites_θ(i) = 1 if spread_θ(i) > 0.05 · n, else 0. This is the
  gate's own per-node indicator. Column name `ignites_theta0.2`.
- **Why it was added.** The gate showed spread_θ to be close to binary on the passing
  pairs. Measured 2026-11-02 from `sizes_<tag>.npz`, before any fit:

  | network | untied pairs ignite vs fizzle | both fizzle | both ignite | τ(spread_θ, degree), fizzlers only |
  |---|---:|---:|---:|---:|
  | ca-GrQc | 0.72 | 0.20 | 0.08 | 0.36 |
  | ca-HepTh | 0.73 | 0.25 | 0.02 | 0.33 |
  | email-Eu-core | 0.67 | 0.16 | 0.17 | 0.74 |

  So most of spread_θ's rankable pairs are already the ignition question. The
  both-fizzle pairs are ranked largely by degree, and degree leans toward a small r\*
  (caveat B of the 10:55 definitions). ignites_θ drops those pairs.
- **Status.** It was chosen after seeing the target's distribution and before any
  fit. It is scored per pair by the part D rule and reported beside spread_θ. **It
  does not enter the lane verdict,** which stays on spread_θ alone.
- **If the two targets give different r\*,** that difference is reported as a
  finding. It is not reconciled or averaged.

### B. How stage 2 is fed

**Directory.** cwd is `results/phase7_threshold/` for every passing network.

**Files, per network.**
- **Copied byte for byte from the repo root:** `cache_features_<tag>.csv`,
  `cache_registry_<tag>.csv`, `cache_meta_<tag>.json`.
  - Each copy is checked by SHA-256 against its root original.
  - The features' `node` and `original_id` columns are checked against the same
    columns in `sizes_<tag>.npz`.
  - Any mismatch refuses before a fit.
- **Also copied byte for byte:** `cache_provenance_audit_20260911.json`.
  - With it, stage 2's source-identity line finds the recorded edge-list hash.
  - Stage 2 resolves the meta's relative edge-list path against its cwd, where the
    file does not exist. It reports this and carries on (non-fatal, by its design).
    The controller therefore hashes each edge list itself against the audit record
    before any fit.
- **New:** `cache_targets_<tag>.csv`, with the columns `node`, `spread_theta0.2` and
  `ignites_theta0.2`.
  - It is built from `sizes_<tag>.npz`. These are the gate's own numbers, not a
    re-run of the cascade.

**Command.** Unmodified: `stage2_sweep.py <tag> spread_theta0.2,ignites_theta0.2 3 10`.

**Dynamic tier: a disclosed deviation from part D.** Part D drops the `dynamic`
tier. But stage 2 has no tier argument and fits every rung of `TIER_LADDER`. The
options were:
1. edit stage 2, which part D registers as unmodified;
2. strip the two dynamic columns, which makes rung 4 an exact duplicate of rung 3:
   40 identical fits per target, filed under a "dynamic" label;
3. fit the dynamic rung and never score it.

The choice is (3).
- Rung 4 carries the root cache's two IC-derived dynamic columns. They were
  computed at 1.5×, not for the threshold model.
- It is reported, labelled unscored. r\* uses `node+edge+subgraph`, as part D says.
- **Cost (inference):** about 20 of roughly 90 minutes, estimated from the root
  sweep's spread_mean fit times on these three networks.

**Cells.** 2 targets × 4 radii × 4 rungs × 10 seeds = 320 per network, 960 in all.

**Pinning and resume.**
- `results/phase7_threshold/sources.json` records SHA-256 for:
  - `stage2_sweep.py` and every repo module it imports;
  - the root caches that were copied;
  - the three edge lists;
  - `influence/threshold_dynamics.py`.
- The controller checks it before each network, and a mismatch stops the run. The
  recorded hashes are never rewritten to pass.
- The lock, the stage runner and the refit reconciliation are imported from
  `probe_beta_sweep.py`, not reimplemented. The L1 sweep exercised them through
  three host resets.

**Order.** Smallest network first: email-Eu-core, ca-GrQc, ca-HepTh.
- The prereg's pilot/full split assumed 2 of 10 pairs for the pilot. Only three pairs
  pass, so all three are fitted in this one run.
- Each network is logged COMPLETE once exactly its 320 cells and their OOF
  predictions are present.

### C. Scoring

`analyse_threshold_arm.py` applies part D of the 10:55 definitions to both targets:
- the relative ε = 0.05 rule, unchanged;
- ε = 0.10 and ε = 0.02 reported beside it;
- the paired-noise rule (rule 2) reported beside it, not scored.

The lane verdict is computed on spread_θ only, as part A says.

## L5 exact r-local probe — 2026-11-02 16:59 IST — before any computation and before L5 scoring

Written by Claude Opus 5.5.
- **Decided by Rachit in chat (16:58):** "go ahead" on building the threshold model's
  own r-local estimate, as a zero-training probe beside L5. It is not a stage-2 tier.
- **Agent definitions, open to Rachit's veto:** the rule and flags below.

**State when this was written.**
- No L5 r\* has been computed.
- The fit logs print mean τ per grid row. I have seen two of them while checking
  progress:
  - email-Eu-core, spread_θ, r=0 node: τ 0.689;
  - ca-GrQc, r=3 node+edge and node+edge+subgraph: 0.592 and 0.595.
- No truncated cascade has been run on any real network.

### A. Why

L5's fitted tiers are structural. IC also has a dynamic rung (`perc_reach_*`), but
the threshold model had no estimate of its own. Unlike IC, the threshold model is
deterministic. So what a radius-r observer can know about the cascade is exactly
computable: run the cascade inside the radius-r ball. That tests the counter-
hypothesis ("ignition is decided by whether N[i] touches a vulnerable pair → r\* ≤
2") with no learner in between. It is the threshold model's analogue of L3.

### B. Definition

For seed node i, radius r and θ = 0.2, let B_r(i) be the set of nodes within
shortest-path distance r of i.
- **Start:** A ← N[i].
- **Activation:** an inactive j activates iff j ∈ B_r(i) and |N(j) ∩ A| / k_j ≥ θ.
  - k_j is j's full degree, so a neighbour outside the ball counts as inactive.
  - The test is exact, in integers, exactly as in `threshold_cascade_sizes`.
- **Iterate to the fixed point.** trunc_r(i) = |A|.

**Properties, each checked by the verifier.**
- trunc_r ≤ spread_θ.
- trunc_r does not decrease as r grows.
- trunc_r = spread_θ once B_r(i) is the whole graph.
- For r ≤ 1, B_r(i) ⊆ N[i], so trunc_r = k_i + 1. That is degree, and r = 0 adds
  nothing over r = 1.

**Radius convention.** Deciding j's activation needs k_j. That is the same convention
as degree being a hop-0 feature of i, so radius r uses only what the hop-r feature
tiers may use.

**Code.**
- New module `influence/threshold_local.py`, with `verify_threshold_local.py`.
- New script `probe_threshold_local.py`, writing
  `results/phase7_threshold/local_exact.json`.
- No pinned file is touched. `influence/threshold_dynamics.py` is imported, not
  edited.

### C. What is computed

On the three passing networks at θ = 0.2, for r = 1, 2, 3 (scored) and r = 4, 5 (for
convergence only):
- **τ_r:** Kendall τ-b(trunc_r, spread_θ) over all n nodes. There are no seeds; the
  value is exact.
- **τ_r^ign:** τ-b(trunc_r, ignites_θ).
- **certified_r:** the fraction of igniting nodes with trunc_r > 0.05 · n. Because
  trunc_r is a lower bound, these nodes are proven to ignite from radius-r
  information alone.
- **coverage_r:** the mean and median of |B_r(i)| / n.

### D. Rule

**spread_θ.**
- r\*_exact is the smallest r ∈ {1, 2, 3} with τ_r ≥ 0.95. Otherwise it is "> 3".
- The ceiling is exactly 1, reached at the graph's eccentricity, so 0.95 is the
  relative ε = 0.05 rule against a known ceiling.

**ignites_θ.**
- ceiling^ign = τ-b(spread_θ, ignites_θ). This is below 1, because the indicator ties
  what spread_θ ranks.
- r\*_exact^ign is the smallest r ∈ {1, 2, 3} with τ_r^ign ≥ 0.95 · ceiling^ign.

**Reading against the counter, per network.**
- r\*_exact ≤ 2 → the probe supports the counter.
- r\*_exact = 3 or > 3 → it does not.

**Coverage flag.** If coverage_r (mean) ≥ 0.5 at the r\*_exact that is reported, the
result is flagged **"ball near-global"**. Support from a ball that holds half the
graph is not evidence of locality, and the scored text must say so.

### E. Status

- The probe is reported beside L5. **It does not enter the L5 lane verdict.**
- It aggregates nothing across networks; each network is reported separately.
- It runs after `verify_threshold_local.py` passes. It reads no fit output, so it can
  run while the stage-2 fits are in progress. Its CPU load slows them but cannot
  change their results.

## L5 post-hoc measures — 2026-11-02 17:15 IST — after the 16:59 probe results, before any of the below is computed

Written by Claude Opus 5.5.
- **Decided by Rachit in chat (17:13):** register and run both of the following, and
  use Somers' D for the sensitivity check in part B.
- **Agent definitions:** the precise rules below.

**Added after seeing results.**
- **Part A** exists because of the 16:59 probe's results
  (`results/phase7_threshold/local_exact.json`, committed in 59d24a9).
- **Part B** follows from the same diagnosis.

Neither part replaces or reinterprets a registered result:
- The 16:59 rule's outcome stands as registered. On all three networks r\*_exact is
  "> 3", so the counter is not supported by the probe.
- The L5 lane verdict stays part D of the 10:55 definitions, scored with Kendall τ-b.

**State at writing.**
- The L5 fits for email-Eu-core and ca-GrQc are complete; ca-HepTh is running.
- No L5 r\* has been computed, and no Somers' D or censored value has been computed.
- Seen so far: the fit-log τ rows named in the 16:59 addendum, and the 16:59 probe
  output.

**The diagnosis (inference, from `local_exact.json`).**
1. **τ-b penalises tie-breaking.** The ignite block of spread_θ is largely tied at one
   global size. A predictor that orders the nodes inside that block loses τ-b, even
   when the ordering is harmless.
   - Example: on email-Eu-core at r = 3, 99.8% of igniters are certified to ignite,
     yet τ_3 = 0.818.
2. **certified_r is capped by ball size.** It needs the ball to hold more than 5% of
   n. The mean coverage at r = 3 is 4.1% (ca-GrQc) and 3.5% (ca-HepTh), so most
   nodes cannot be certified there whatever their dynamics.

### A. Censored r-local predictor (fixes both, zero training)

**Containment.**
- For r ≥ 1, node i is **contained at r** if no node at distance exactly r from i is
  active in the truncated cascade's fixed point.
- **Claim:** if i is contained at r, then trunc_r(i) = spread_θ(i) exactly.
- **Proof.** Every node at distance > r has its neighbours at distance ≥ r. None of
  those is active: those at distance r by containment, and those beyond r because
  activation is confined to the ball. So no node outside the ball can activate. The
  truncated fixed point is therefore closed under the full rule, and it contains
  N[i]. The full cascade is the smallest such set, so the two are equal.
- At r = 1 no node with k ≥ 1 is contained, because every distance-1 node is a seed.
- Containment uses only the ball, so it is radius-r information.

**Predictor.** x_r(i) = trunc_r(i) if i is contained at r; otherwise one shared value,
n + 1, placed above every contained node.

**Computed** for r = 1–5 on the three passing networks at θ = 0.2.
- **τ_cens_r:** τ-b(x_r, spread_θ).
  - At r = 1, x_r is constant, so this is undefined and reported as such.
- **τ_cens_r^ign:** τ-b(x_r, ignites_θ).
- **contained share of fizzlers:** the fraction of fizzlers that are contained at r.
  Their final size is proven from radius r.
- **contained share of igniters**, reported alongside.
- **P(ignites | escaped at r)** and **P(escaped at r)**.

**Rule.** The 16:59 form, with x_r in place of trunc_r.
- r\*_cens is the smallest r ∈ {1, 2, 3} with τ_cens_r ≥ 0.95. Otherwise "> 3".
- r\*_cens^ign is the smallest r with τ_cens_r^ign ≥ 0.95 · ceiling^ign. ceiling^ign is
  τ-b(spread_θ, ignites_θ) as before.
- Counter reading: r\* ≤ 2 supports it.
- The coverage flag stays at mean coverage ≥ 0.5.
- **Descriptive, not scored:** P(ignites | escaped at r = 2). This is the
  counter-hypothesis in its own terms.

**Code.**
- `threshold_local.py` gains containment output. Its earlier version is committed in
  59d24a9 together with the 16:59 output it produced.
- `verify_threshold_local.py` gains the check that contained ⇒ trunc_r = the full
  cascade.
- Output goes to `results/phase7_threshold/local_censored.json`. `local_exact.json` is
  not rewritten.

### B. Somers' D sensitivity for the L5 fits

**Definition.** D = (C − D_pairs) / (pairs untied in the target).
- C and D_pairs count the concordant and discordant pairs between prediction and
  target.
- A pair tied in the prediction but not in the target counts in the denominator only.
- A pair tied in the target is excluded.
- So breaking the target's ties costs nothing, while failing to separate what the
  target separates still costs.
- **Computation:** from τ-b's numerator, S = τ_b · √((n0 − n1)(n0 − n2)), then D = S /
  (n0 − n2), where n1 and n2 are the tied-pair counts in the prediction and the target.

**Data.**
- The stored out-of-fold predictions: `results/phase7_threshold/cache_oof_<tag>.npz`
  for spread_θ and ignites_θ, and the root `cache_oof_<tag>.npz` for spread_mean at
  1.5×.
- The `node+edge+subgraph` rung, every radius and seed.
- No model is refitted.

**Consistency check.** For every cell, τ-b recomputed from the stored predictions must
equal the sweep CSV's `kendall_tau` within 1e-9. Any mismatch refuses the whole
analysis: it would mean the predictions are not the ones that were scored.

**Rule.** Part D exactly, with Somers' D in place of τ-b:
- r\* is the per-seed `locality_horizon` at ε = 0.05 on the `somers_d` metric, then the
  modal value across seeds, ties to the smaller r;
- r\*(spread_mean) is recomputed the same way, from the root predictions;
- the same per-pair outcomes and the same lane aggregation.

**Status.** Reported beside the τ-b verdict, labelled as a sensitivity check.
- **If it agrees,** the verdict did not depend on tie-breaking.
- **If it disagrees,** both are reported. The τ-b verdict remains the registered one,
  and the disagreement is stated as a limitation of it.

## L5 scored addendum — 2026-11-02 17:44 IST — Claude Opus 5.5

Scored by `analyse_threshold_arm.py` on 2026-11-02 at 17:42. Its outputs are in
`results/phase7_threshold/`:
- `rstar.csv`, `curves.csv` and `somers.csv`;
- `verdict.json`, which records the sha256 of the scorer and of its imports.

The fits finished at 17:41 and `controller.log` reads "ALL NETWORKS COMPLETE (3)":

| network | cells | stage-2 time |
|---|---:|---:|
| email-Eu-core | 320 | 348 s |
| ca-GrQc | 320 | 3018 s |
| ca-HepTh | 320 | 2063 s |

**What governs this addendum.** The rules are part D of the 10:55 definitions and parts
A and C of the 16:09 run status; nothing here changes a rule.
- The verdict and the per-pair outcomes are registered results.
- The section "Reading the verdict against the r-local probes" is inference and is
  labelled as such.
- The wording of any claim is Rachit's.

### Verdict (registered, part D, Kendall τ-b)

**Lane: prediction NOT SUPPORTED, counter SUPPORTED.**

Primary target spread_θ, θ = 0.2, tier `node+edge+subgraph`, relative ε = 0.05:

| network | ceiling τ | r\*(spread_θ) | seeds agreeing | r\*(spread_mean) | outcome |
|---|---:|---:|---:|---:|---|
| email-Eu-core | 0.764 | 1 | 10/10 | 1 | counter |
| ca-GrQc | 0.595 | 2 | 10/10 | 1 | both |
| ca-HepTh | 0.620 | 2 | 10/10 | 2 | counter |

**How the outcomes combine.**
- ca-GrQc is "both": 2 ≥ 1 + 1 and 2 ≤ 2. It counts for neither.
- Over the two remaining pairs, the prediction holds on none and the counter holds on
  both.
- r\*(spread_mean) equals the registered root values (1 / 2 / 1). The scorer checks
  this and refuses to run otherwise.
- Every ceiling τ is positive, so every pair is scored.

**Seed-mean τ by radius, `node+edge+subgraph`, spread_θ:**

| network | r = 0 | r = 1 | r = 2 | r = 3 |
|---|---:|---:|---:|---:|
| email-Eu-core | 0.689 | 0.757 | 0.764 | 0.764 |
| ca-GrQc | 0.308 | 0.504 | 0.586 | 0.595 |
| ca-HepTh | 0.405 | 0.517 | 0.613 | 0.620 |

### Reported beside the primary (not scored)

**ε = 0.10 and ε = 0.02.** The ε = 0.02 values do not change any outcome.

| network | r\* at ε = 0.10 | r\* at ε = 0.02 |
|---|---|---|
| email-Eu-core | 0 (5/10 seeds) | 1 (10/10) |
| ca-GrQc | 2 (10/10) | 2 (8/10) |
| ca-HepTh | 2 (10/10) | 2 (10/10) |

**Rule 2 (paired noise).**
- r\*(spread_θ) is 2 / 3 / 3 (email, GrQc, HepTh), and r\*(spread_mean) is 3 on all
  three.
- As part A of 10:55 said, the prediction cannot hold under rule 2 when radii stop at
  3.

**ignites_θ, the post-gate secondary (16:09 part A), outside the lane verdict.**
- Ceiling τ: 0.756 / 0.629 / 0.621.
- r\*: 0 / 2 / 2.
- Outcomes: counter / both / counter. These match the primary pair for pair.

**The dynamic rung (16:09 part B deviation), descriptive only.**
- `node+edge+subgraph+dynamic` equals `node+edge+subgraph` to three decimals at every
  radius on all three networks.
- The IC-specific dynamic features add nothing to either threshold target.

### Somers' D sensitivity (17:15 part B, not the verdict)

**Consistency check.** τ-b recomputed from the stored out-of-fold predictions matched
the sweep CSVs' `kendall_tau` within 1e-9 on every cell. The scorer refuses to run on
any mismatch.

| network | target | ceiling D | r\*(θ), agreement | r\*(spread_mean) under D | outcome |
|---|---|---:|---|---:|---|
| email-Eu-core | spread_θ | 0.890 | 1, 10/10 | 1 | counter |
| ca-GrQc | spread_θ | 0.738 | 2, 10/10 | 1 | both |
| ca-HepTh | spread_θ | 0.754 | 2, 10/10 | 2 | counter |

**Lane under Somers' D:** prediction NOT SUPPORTED, counter SUPPORTED. The ignites
outcomes are counter / both / counter.

**The two statistics agree on every pair,** so the verdict did not depend on τ-b's
penalty for breaking the target's ties.
- That penalty is large in level. D is 0.13–0.14 above τ-b on spread_θ, and 0.22–0.29
  above it on ignites_θ.
- It does not change where the curves flatten.

### Reading the verdict against the r-local probes (inference)

**The verdict measures where the learned curve flattens.** The 16:59 and 17:15 probes
measure what exact radius-r information is worth. The two disagree, and the
disagreement is the main qualification on this lane:

| network | learned, r = 2 → 3 | exact trunc_r, r = 2 → 3 → 5 | censored, r = 3 → 4 |
|---|---|---|---|
| email-Eu-core | 0.764 → 0.764 | 0.802 → 0.818 → 0.998 | 0.710 → 0.969 |
| ca-GrQc | 0.586 → 0.595 | 0.533 → 0.622 → 0.705 | 0.570 → 0.718 |
| ca-HepTh | 0.613 → 0.620 | 0.613 → 0.696 → 0.774 | 0.550 → 0.702 |

1. **At r = 3 the learned model is below the single exact r-local scalar on all three
   networks**: by 0.054, 0.027 and 0.076 τ (email, GrQc, HepTh).
   - trunc_3 uses only radius-3 information.
   - So at least that much rank information is available within 3 hops but is not
     captured by the feature tiers as fitted.
   - The comparison is between a trained regressor's out-of-fold τ and an untrained
     scalar's in-sample τ. The scalar has no parameters, so overfitting cannot account
     for the gap.
2. **From r = 2 to r = 3 the learned curve gains 0.000 / 0.009 / 0.007,** while the
   exact scalar gains 0.016 / 0.089 / 0.083.
   - The flattening that puts r\* at ≤ 2 is a property of the feature tiers, not of the
     threshold dynamics.
   - On the two collaboration networks the exact information keeps rising through
     r = 5.
3. **What the lane result supports, then:**
   - **Supported:** "with the project's radius-r feature tiers, threshold spread is no
     less local than mean IC spread".
   - **Not supported:** "threshold influence is decided within 2 hops". Both probes
     reject that on all three networks.
4. **Bias toward the counter.** The 10:55 caveat (part B) said fizzles of size
   k_i + 1 favour a small r\*, and it applies here.
   - At r = 0, where the features are degree and other node-level facts, τ is already
     0.689 on email-Eu-core. That is 90% of its ceiling, and it is why email's r\* is 1.
   - The fizzle mass is 33% / 37% / 42% (email, GrQc, HepTh): the shares of nodes that
     do not ignite at the gate.

**Probe caveats (from the 17:15 work, repeated here so they travel with the result).**
- The censored predictor discards the ordering among escaped nodes.
- On email-Eu-core at r ≥ 4 it re-breaks the target's ties: contained igniters get
  their exact size and escaped nodes get n + 1. That is why τ_cens falls from 0.969
  at r = 4 to 0.885 at r = 5.
- At the scored radii, contained igniters are ≤ 0.3% on email-Eu-core and 0 on the
  collaboration networks.

### Not done here

- No refit.
- No change to any registered rule.
- No new probe.
- L6 is the next lane.

## L6 execution definitions — 2026-11-02 19:53 IST — before any L6 graph is generated

Written by Claude Opus 5.5.
- **Decided by Rachit:**
  - 19:49: start L6, after L5.
  - Earlier: the multiple is 1.5×, by L1's stop rule (L1 scored addendum, "Lane status").
- **Agent definitions, open to Rachit's veto before the first stage-2 fit:**
  - the trend rule in part C;
  - the betweenness arm in part B;
  - the seed count;
  - everything marked "agent".

**State at writing.**
- No synthetic graph has been generated: `data/synthetic/` does not exist.
- `nb_spectral_gap` does not exist.
- No L6 cascade, feature or fit exists.
- The lane text (§2 "L6") stands. This addendum names the rules that text leaves open.
- **Discharges Phase 7's D3 prerequisite** (ROADMAP Phase 7 row). It is logged as
  "Phase 6.5 L6".

### A. Corpus

**Generation.** `python stage0_generate.py --n 5000 --families gamma,controls --seed 0
--bootstrap 200`, unmodified. It produces 11 graphs:
- **Chung-Lu, ⟨k⟩ = 6:** γ_target ∈ {2.1, 2.3, 2.5, 2.8, 3.0, 3.3, 3.6, 4.0}. This is the
  **γ family**.
- **Controls:** ER (⟨k⟩ = 6), BA (m = 3) and WS (k = 6, p = 0.1).

**Verification before use.** `verify_generators.py` must be green.

**Recorded once, in `results/phase7_certificate/corpus.json`:**
- the sha256 of each edge list;
- stage 0's manifest: γ fit with its bootstrap sd, duel ratio, clustering and
  assortativity.

`data/synthetic/` is git-ignored, so the hashes plus the seed are the record.

**Known confound, to be measured and disclosed (inference until then).**
- stage 1 restricts each graph to its largest component.
- The weight rescale that fixes ⟨k⟩ = 6 pushes many low-γ weights below 1.
- So n and ⟨k⟩ after the LCC step will vary along the γ family.
- These per-graph values are reported beside every result. The trend in part C is not
  adjusted for them: 8 points cannot carry an adjustment.

### B. Pipeline (reduced protocol, as the lane text says)

**Layout.** Unmodified `stage1_prepare.py` and `stage2_sweep.py`, run with
`cwd=results/phase7_certificate/`, so no cache is written to the repo root.
- stage 1 is given the edge list by a path relative to that cwd. stage 2's source
  guard then rehashes it.

**stage 1.** `<edgelist> 4000 1.5 uniform`, the root's settings:
- 4000 cascades;
- 1.5× the NB β_c;
- the uniform convention;
- MAX_HOP = 3.

**stage 2, primary target.** `spread_mean` with the default `rf` estimator.
- radii 0–3, all four TIER_LADDER rungs, **5 seeds** (the lane text's reduced protocol).
- 80 cells per graph.
- The `dynamic` rung is legitimate here: it is IC-specific and the target is IC.
- The primary tier is `node+edge+subgraph`, as in L1 and L5, so that L6 is comparable
  to them.

**stage 2, betweenness (agent).** `betweenness` with `rf_log1p`, the project's
reported betweenness arm.
- Under plain `rf` the squared-error objective handicaps the poorer tiers, and so
  distorts the hop curve (vault memory 2026-09-03).
- 5 seeds, 80 cells per graph, written to `estimators/` as stage 2 does.
- A structural control, reported only.

**Totals.** 160 cells per graph, 1,760 cells overall.

**Controller.** `probe_certificate.py`, with subcommands `generate`, `prepare` and
`fit`. It reuses L1's lock, stage runner and refit reconciliation, as L5 did.
- It pins `stage2_sweep.py` and its imports, `stage1_prepare.py` and its imports, and
  every edge list.
- It checks those pins before every graph.
- It writes only under `results/phase7_certificate/` and `data/synthetic/`.
- Graphs run in γ order, then the controls.

### C. Primary statistic and trend rule (agent rule)

**Statistic.** ρ_g = τ₁/τ₃ for `spread_mean`, tier `node+edge+subgraph`.
- It is formed per seed, which is paired: the same seed gives the same folds at
  r = 1 and r = 3.
- Then ρ̄_g (seed mean) and sd_g (seed sd, ddof = 1) are taken.
- A graph whose seed-mean τ₃ is ≤ 0 is unscored.

**Trend statistic.** T = Kendall τ-b between γ_target and ρ̄_g over the scored γ-family
graphs.
- The γ_targets are fixed by construction and have no measurement error.
- The fitted γ is reported, not used (stage 0's docstring).

**Magnitude condition.** |ρ̄(2.1) − ρ̄(4.0)| > 2·sd_pool, where sd_pool =
√(mean over the scored γ graphs of sd_g²).
- This is the lane text's "outside seed sd".
- It is applied end to end because the lane predicts a direction, not a shape.

**Outcomes.**
- **PREDICTION SUPPORTED:** T ≤ −0.571 and the magnitude condition holds.
  - −0.571 is C − D ≤ −16 of 28 pairs: the exact one-sided null p = 0.031 at n = 8
    with no ties (computed 19:50).
- **COUNTER SUPPORTED:** T ≥ +0.571 and the magnitude condition holds.
- **FLAT:** anything else.
- **UNDECIDED:** fewer than 6 γ graphs are scored. The threshold then stays at the
  one-sided p ≤ 0.05 point for that n, which is recomputed and stated.

**Stop rule (lane text).** The full 31-graph corpus is fitted only if the outcome is
PREDICTION or COUNTER SUPPORTED. FLAT or UNDECIDED ends L6 at the MVP.

### D. Reported beside the primary (not scored)

- **r\* per graph:** relative ε = 0.05, the modal value across seeds
  (`analyse_beta_sweep.r_star_relative`), with seed agreement shown.
- **Hop-gain area:** the sum over r = 1–3 of (τ_r − τ₀)/(τ₃ − τ₀).
- **The same ρ̄ and T for betweenness** (`rf_log1p`).
- **ρ̄ for the three controls:**
  - ER, as a no-tail reference beside γ = 4.0;
  - BA, as a γ ≈ 3 point by a different mechanism;
  - WS, as a clustered, tail-free point.
- **Structure per graph:**
  - n and ⟨k⟩ after the LCC step;
  - the fitted γ with its bootstrap sd and reliability flag;
  - the duel ratio;
  - `nb_spectral_gap`;
  - average clustering;
  - assortativity.
- **NB gap versus the duel ratio.**
  - The lane predicts that the NB gap adds nothing once the duel ratio is controlled.
    With 8 collinear points that is **not testable**, as the lane text warns.
  - Reported only: Kendall τ of the NB gap and of the duel ratio with γ_target, and
    with each other.
  - No partial or conditional test is computed.

### E. `nb_spectral_gap` (agent definition)

**Definition.**
- λ₁ = the spectral radius of the Ihara–Bass matrix M = [[A, I − D], [I, 0]] of the
  LCC, as stage 1 loads it.
- λ₂ = the second-largest modulus in M's spectrum.
- gap = 1 − |λ₂|/λ₁.
- M's spectrum is B's spectrum without the (m − n)-fold ±1 roots. When |λ₂| < 1 that
  difference matters, and the code records which case held.

**Computation.**
- `scipy.sparse.linalg.eigs` on M.
- In a new module, `influence/nb_spectrum.py`. `influence/criticality.py` is imported,
  not edited.

**Verification before use.**
- On 20 random small graphs, the result against `numpy.linalg.eigvals` of the dense M,
  within 1e-8 relative.
- On one L6 graph, against the dense spectrum, which is affordable at 2n = 10⁴.
- λ₁ must equal 1/β_c from `epidemic_threshold` within 1e-8 relative.

## L6 scored addendum — 2026-11-02 21:25 IST — Claude Opus 5.5

**Run.** `python probe_certificate.py fit`, 19:59:09 → 21:19:10 (80 min, against a
projected ≈ 21:25). All 11 graphs × 2 arms complete at 80 cells each, with no
refit reconciliation needed. The outputs are `results/phase7_certificate/ratios.csv` and
`verdict.json`.

**One edit after the fit, before any number was read.** `analyse_certificate.py`
crashed after writing `ratios.csv` and before printing. The cause was that the
provenance block passed a `str` to `sha256`, which takes a `Path`. The fix wraps the
argument in `Path`. It changes no computation. The rerun rewrote `ratios.csv` from
the same sweeps.

### Verdict (registered, part C)

| γ_target | 2.1 | 2.3 | 2.5 | 2.8 | 3.0 | 3.3 | 3.6 | 4.0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| τ₁ | .927 | .924 | .918 | .899 | .887 | .889 | .907 | .919 |
| τ₃ | .937 | .942 | .943 | .944 | .946 | .941 | .943 | .946 |
| ρ̄ = τ₁/τ₃ | .989 | .981 | .973 | .952 | .938 | .945 | .962 | .972 |
| sd (seed) | .0005 | .0005 | .0003 | .0004 | .0003 | .0006 | .0004 | .0006 |
| r\* (ε = .05) | 1 | 1 | 1 | 1 | 2 | 2 | 1 | 1 |

- All 8 are scored, since every τ₃ > 0.
- T = Kendall τ-b(γ_target, ρ̄) = **−0.429**. t_crit = 0.571 at n = 8.
- ρ̄(2.1) − ρ̄(4.0) = 0.0176 and 2·sd_pool = 0.0010, so the magnitude condition holds.
- **Outcome: FLAT.** T falls short of the threshold.
- **Stop rule:** L6 ends at the MVP. The 31-graph corpus is not fitted.
- r\* agreement is 5/5 seeds on every graph.

### Reported beside the primary (not scored)

**Controls (spread_mean):**

| graph | ρ̄ | τ₃ | r\* |
|---|---:|---:|---:|
| ER | .972 | .962 | 1 |
| BA | .932 | .927 | 2 |
| WS (p = .1) | .724 | .781 | 3 |

WS is the only graph in the corpus where radius 3 is needed. It also has the
smallest NB gap by far (.046, against .59–.82 elsewhere).

**Betweenness (`rf_log1p`):**
- T = **+0.571**, exactly at t_crit.
- ρ̄(2.1) − ρ̄(4.0) = −0.014, against 2·sd_pool = 0.0018.
- By the part C rule applied to it, that reads COUNTER. It is a reported control,
  not the lane verdict.
- It sits on the boundary: one swapped pair would make it FLAT.
- ρ̄ runs .972 → .956 (minimum at γ = 2.5) → .986. Every r\* is 1.

**Structure along the γ family (Kendall τ):**
- NB gap vs γ: −0.929;
- duel ratio vs γ: +0.929;
- NB gap vs duel ratio: −0.857.

As registered, the two are near-collinear on this family, so the claim that the NB
gap adds nothing once the duel ratio is controlled cannot be tested here.

### Reading (inference, not registered)

- **The spread ratio is U-shaped, not monotone.** ρ̄ falls from .989 at γ = 2.1 to a
  minimum of .938 at γ = 3.0, then rises to .972 at γ = 4.0. Kendall's T is built
  to detect a monotone trend and cannot see that shape. This is one realisation
  per γ, and the shape was not registered, so it is a description, not a finding.
- **The magnitude condition is weaker than its numbers look.** sd_g is the spread
  across fitting seeds on one fixed graph and one fixed set of cascades. It
  measures fold and forest noise only. It does not measure graph-realisation
  noise: there is one graph per γ, seed 0.
  - The end-to-end gap clears 2·sd_pool by 18×. That says the gap is not fitting
    noise. It does not say the gap is a γ effect.
  - This does not change FLAT. It does mean the betweenness "COUNTER" and any
    future use of this condition need a between-realisation yardstick, i.e.
    several generator seeds per γ.
- **On every Chung-Lu graph, radius 1 already reaches 94–99% of radius 3.** The
  locality question on this family is about the last 1–6% of τ.
- **The part A confounds are still present.** Along γ, LCC n rises 4303 → 4965 and
  ⟨k⟩ falls 6.82 → 6.05. Fitted γ is unreliable at γ_target 4.0 (2.21 ± 0.79).
  Neither is adjusted for.

### Not done here

- No 31-graph corpus (stop rule).
- No multi-seed generator replicate.
- No test of the U-shape.
- No regression of ρ̄ on the NB gap across all 11 graphs. Each would need its own
  registration.

## L6 realisation-noise calibration — execution definitions — 2026-11-02 23:30 IST — before any replicate graph is generated

### A. Why, and what this cannot do

- **The gap it closes.** The L6 scored addendum found that sd_g measures fitting
  noise on one graph per γ, not graph-realisation noise.
- **Who chose it.** Rachit, 23:29: a small calibration run, not a test of the U-shape.
- **What it is.** A **calibration**. It has no verdict and scores nothing.
- **What it cannot change.** L6 stays FLAT by its registered stop rule, whatever
  this run shows.
- **What it is for.** The realisation sd it measures is an input to Rachit's
  decision on how later synthetic trend tests set their noise yardstick.

### B. Corpus

- **Command.** For k ∈ {1, 2, 3}:
  `python stage0_generate.py --n 5000 --families gamma --seed k --bootstrap 200 --out data/synthetic/s<k>`.
- **What is fitted.** Stage 0 cannot select γ, so all 8 Chung-Lu graphs are
  generated. Only γ_target ∈ {2.1, 3.0, 4.0} are fitted, which is 9 graphs. The
  other 15 are not fitted or inspected.
- **Realisations per γ.** With L6's seed-0 graph, there are 4 realisations of each
  of the three γ. `data/synthetic/` is git-ignored, so the record is the seeds plus
  the sha256 of each list, kept in `results/phase7_certificate/realisations/corpus.json`.
- **Disclosure.** Within one generator seed, `chung_lu` uses the same seed for every
  γ. Realisations are therefore independent across k, not across γ within a k.

### C. Pipeline

The pipeline is identical to L6's primary arm:
- stage 1: `<edgelist> 4000 1.5 uniform`, with MAX_HOP 3;
- stage 2: `spread_mean 3 5 rf`, giving radii 0–3, all four rungs and 5 fitting seeds.

The working directory is `results/phase7_certificate/realisations/s<k>/`, one per k.
The tags match L6's, and each k has its own directory, so nothing collides with
L6's caches. The controller is `probe_realisation.py`, which uses the same lock,
stage runner, refit reconciliation and source pinning as `probe_certificate.py`.

### D. Computed (all reported, none scored)

Notation:
- ρ̄_{γ,k} is the seed-mean of τ₁/τ₃, defined exactly as in L6 part C, on tier
  node+edge+subgraph, for realisation k = 0..3 (k = 0 is L6's graph).
- m_γ is the mean of ρ̄_{γ,k} over k.

1. **Realisation sd.**
   - Per γ: s_γ = sd over k = 0..3 of ρ̄_{γ,k}, with ddof = 1.
   - Pooled: sd_real = √(mean_γ s_γ²).
   - Reported next to sd_fit, the pooled fitting-seed sd over the same 12 graphs,
     and next to L6's sd_pool. The headline is the ratio sd_real / sd_fit.
2. **L6's end-to-end gap re-expressed.** Δ̄ = m(2.1) − m(4.0), compared with
   2·sd_real. It is also reported with seed 0 excluded.
3. **The dip, on seeds 1–3 only.** Seed 0 is excluded because it is where the shape
   was first seen.
   - D = mean_k ρ̄(3.0, k) − ½[mean_k ρ̄(2.1, k) + mean_k ρ̄(4.0, k)], with k = 1..3.
   - SE = √(s₃²/3 + (s₂.₁² + s₄.₀²)/12), with each s taken over k = 1..3.
   - Reported as D and D/SE.
   - With 3 realisations per point, this describes the dip. It is not a test, and
     no threshold is attached.
4. **Structure per realisation:** LCC n, ⟨k⟩ and nb_spectral_gap. The question is
   whether the part A drift (n up and ⟨k⟩ down along γ) replicates, and how large
   its realisation sd is.

### E. Stop and cost

- The run is one pass of 9 graphs. There is no follow-on rule.
- **Projected time (inference):** about 4 min of stage 2 per graph, from L6's
  measured 214–249 s, plus under 40 s of stage 1, giving ≈ 40 min.

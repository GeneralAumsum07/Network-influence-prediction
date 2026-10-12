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
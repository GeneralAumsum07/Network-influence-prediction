# Historical r=1 / raw-objective lanes: what is stale, what is re-run, what is only labelled

Written 2026-09-12 by Claude Opus 5 (Task 6 root integration, run C8; findings P1-01,
P2-11, P3-08). Two corpus changes since these files were produced decide each file's fate:

- **Retag (P1-01, 2026-09-11):** six 5-node NODE orbits (56, 57, 65, 66, 68, 70) and nine
  5-node EDGE orbits (49, 50, 51, 59, 60, 61, 63, 64, 65) moved from hop 1 to hop 2. Only
  the **r=1** column set changed; the cumulative r=2 and r=3 sets contain both hops either
  way and are column-identical to before.
- **Objective (P2-11, decided 2026-09-04):** the study reports betweenness from the
  `rf_log1p` arm. Every file below fitted betweenness under the raw squared-error arm.

| File | Radius | Retag-affected? | Objective | Decision |
| --- | --- | --- | --- | --- |
| `RESULTS_r1_subgraph_ablation.txt` (2026-08-26, three networks; producer script no longer in the tree) | r=1 | **yes** - its "+ 5-node hop-1 orbits" step contained the six retagged orbits | raw (spread targets only, so raw == reported) | **Historical, superseded.** Replaced in substance by the five-network `phase6_r1_ablation/` run and its reversal (`phase6_r1_ablation_retag_delta_20260912.txt`: 17/20 -> 0/20). Not re-run; study §16 and HANDOFF Finding 3 carry the dated reversal. |
| `RESULTS_orbit04_ablation.txt` (2026-08-26, three networks; producer no longer in the tree) | r=3 | no | raw (spread targets only) | Historical, still valid for what it measures. Labelled only. |
| `RESULTS_edge5.txt` (2026-08-26, two networks) | r=1,2,3 | **yes** - r=1 rows used columns a radius-1 observer cannot compute (both retags apply: the edge-orbit-5 table is this lane's whole subject) | raw, incl. betweenness | **Re-run** by `phase6_root_integration_stage3_20260912.ps1` on all five networks, raw arm (historical form) plus a betweenness-only reported-arm run (`RESULTS_edge5_betweenness_log1p_20260912.txt`). Pre-C8 file kept at `c8_historical_pre_20260912/RESULTS_edge5.txt`. `analyse_edge5.py` gained `--objective` (2026-09-12) and prints the arm in its header. |
| `RESULTS_edge_tier.txt`, `_others.txt`, `_subgraph.txt` (2026-09-01) | r=2 | no | raw betweenness | Valid for what they are; header printed before the arm label existed. **Dated addendum** (P2-11's proposed fix) runs the facebook cell under the reported arm for both rungs: `RESULTS_edge_tier_log1p_facebook_20260912.txt`, `RESULTS_edge_tier_subgraph_log1p_facebook_20260912.txt` (stage 3). `analyse_edge_tier.py` gained `--objective` (2026-09-12); `raw` reproduces the 2026-09-01 files byte for byte. |
| `RESULTS_robustness.txt`, `RESULTS_robustness_trainmode.txt`, `robustness.csv` (2026-08-27) | max_hop 3 (full ladder) | no | raw betweenness | *Original decision (morning):* not re-run: identical seeds and columns would reproduce identical numbers. `fig3_robustness.png` regenerated 2026-09-12 from the unchanged `robustness.csv` with the objective label in its subtitle (P3-08); the pre-label figure is at `c8_historical_pre_20260912/fig3_robustness.png`. **Overruled by Rachit 2026-09-12 15:51 IST ("queue the angle 4 re-run"):** re-run queued as stage 4 (`phase6_root_integration_stage4_20260912.ps1`, launched 16:32 IST, waits for stage 3). Raw arm re-run to its existing paths after the 2026-08-27 `RESULTS_robustness.txt` / `robustness.csv` are copied to `c8_historical_pre_20260912/`; the "identical numbers" inference is then *measured* by `verify_robustness_rerun.py` (bar 1e-06). A **log1p arm** (`--objective reported --targets betweenness`, added to `analyse_robustness.py` the same day) writes `robustness_log1p.csv`, `RESULTS_robustness_log1p_20260912.txt` and `fig3_robustness_log1p.png` beside the raw files; `make_fig3.py --objective reported` labels its arm. `RESULTS_robustness_trainmode.txt` (three networks, four rho) is a subset of the same protocol and is not re-run separately. |

## How to quote these files

- Any betweenness number from `RESULTS_edge*.txt` or `RESULTS_robustness*.txt` is a
  **raw-arm** number. The study's horizon tables report log1p; the two arms differ by up to
  +0.1291 vs +0.0436 on the facebook r=2 subgraph rung (P2-11), so they are not
  interchangeable.
- Any r=1 number produced before 2026-09-11 that includes 5-node orbits used the wrong
  column set. The three-network "5-node beats 4-node at r=1" attribution is reversed, not
  merely stale.

## Compute decision, stated so it can be overruled

`analyse_robustness.py` is the one lane here that was *not* re-run. It is retag-independent
(fits at max_hop 3) and its numbers are deterministic given seeds, so a re-run buys only a
header line at the cost of ~2-3 h of fits. `analyse_robustness.py` now prints that
header (objective label added 2026-09-12), so if Rachit wants the label inside the text
files rather than in this note and in fig3, `python analyse_robustness.py` regenerates
them at their existing paths.

**Overruled the same afternoon.** Rachit asked for the re-run at 15:51 IST; it is queued
as stage 4 (see the table row above). Two things the re-run buys that the paragraph above
undersold: (i) the "identical numbers" claim becomes a measurement rather than an
inference - `verify_robustness_rerun.py` aligns all 640 rows against the archive; (ii) the
Angle 4 comparison exists on the arm the study actually reports, which the raw-arm files
could not give. A one-network smoke test (email-Eu-core, betweenness, rho 0 / 0.1) already
shows the arm is not cosmetic here: the clean-trained local model gains +0.009 tau at
rho = 0 and +0.017 at rho = 0.1 under log1p (seed 0). Whether that holds across networks,
damage levels and the nonzero subset is what stage 4 measures (inferred from one cell:
the raw-arm numbers may understate the reported arm's; not yet established).

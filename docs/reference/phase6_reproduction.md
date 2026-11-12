# Reproduction guide

This guide reproduces completed analyses from saved files. Its commands neither fit a model nor rerun graph traversal across the external corpus. They regenerate scored summaries, audits, or cache-only reports. Run them from the repository root with the pinned environment:

Activate the existing `influence` Conda environment first; do not install packages. Then resolve its interpreter instead of relying on a machine-specific path:

```powershell
conda activate influence
$py = Join-Path $env:CONDA_PREFIX 'python.exe'
```

The expected evidence package is results/RESULTS_c3_benchmarks.txt, results/c3_scored_summary.json, results/RESULTS_c4_support_audit.txt, results/RESULTS_c4_internal_smoke.txt, results/RESULTS_paired_target_noise.txt, results/c3_fallback_nodes.csv, and results/RESULTS_c3_fallback.txt. The detailed protocol and limits are in docs/reference/C4_two_number_reporting_protocol.md.

## Fast verification

These checks use saved local evidence. They do not train, bootstrap, or traverse the full external edge-list corpus.

```powershell
& $py checks/verify_paired_target_noise.py
& $py checks/verify_generators.py
& $py checks/verify_c3_fallback.py --self-test
& $py checks/verify_pipeline.py
& $py checks/verify_docs.py
```

checks/verify_pipeline.py includes C3 synthetic denominator checks, project fallback nodewise agreement, C3 scored provenance checks, and C4 reporter tests. It may need cached project data and the configured BRAVA source location. A successful run ends with ALL CHECKS PASSED.

## Regenerate the C3 fallback evidence

```powershell
& $py checks/verify_c3_fallback.py --self-test
& $py checks/verify_c3_fallback.py --record
```

The self-test uses hand-derived fixtures. The evidence command verifies the five
project zero masks with raw IDs and cached ordering, then writes
results/c3_fallback_nodes.csv and results/RESULTS_c3_fallback.txt. It computes
no positive betweenness magnitudes, fits no models, and does not traverse the
external corpus.

## Recreate the scored C3 summaries

```powershell
& $py analysis/score_c3_results.py
```

This reads results/results_c3_structure.csv, results/results_c3_cells.csv, the saved C3 transcript, and BRAVA-GNN's released aggregate all_results.csv. It writes results/results_c3_scored_cells.csv, results/results_c3_scored_graphs.csv, results/results_c3_controls.csv, results/c3_scored_summary.json, and results/c3_scored_provenance.json. It does not reconstruct predictions, load a checkpoint, fit a model, or recompute structural zero sets. Expected verdicts are P1 **FALSIFIED**, P2 **SUPPORTED**, P3 **SUPPORTED** (12/14 graphs), and P4 **PASSED UNDER REGISTERED CONDITIONAL**.

## Recreate the C4 support and identifier audit

```powershell
& $py analysis/audit_c4_support.py
```

This streams released decimal target files and reads the released aggregate table. It writes results/results_c4_support_audit.csv and results/RESULTS_c4_support_audit.txt. It performs no graph traversal, model execution, prediction reconstruction, or external two-number pilot. The output should report 15,043,174 printed values on the 1e-14 grid and retain 5,608 paired cells, 404 row occurrences, and 395 names.

## Recreate the cache-only C4 code-correctness report

```powershell
& $py analysis/c4_two_numbers.py
```

This reads existing project target, OOF-cache, and sweep files and writes results/results_c4_internal_smoke.csv, results/RESULTS_c4_internal_smoke.txt, and results/c4_internal_provenance.json. It evaluates 800 saved full OOF vectors; no forest is fitted. The decision score == 0 is supplied retrospectively for this code check. Treat it as validation of arithmetic and output schema, never as an external-method result or predeclared zero-decision test.

## Recreate the paired target-noise table

```powershell
& $py analysis/analyse_paired_target_noise.py
```

The script reads the complete 12,000-row results/results_target_noise_refit.csv and the five current sweeps using the keep-last resume convention. It writes results/results_paired_target_noise.csv and results/RESULTS_paired_target_noise.txt. It requires exactly 200 unique replicates per refit cell and ten seeds per selected sweep cell, rejecting missing, duplicate, extra, or nonfinite observations. No target is rebuilt and no model is refit.

The scope is 45 adjacent-radius contrasts in the richest dynamic tier only. The saved result has 41 seed heuristic flags and 38 paired target-bootstrap flags: 38 retained, 3 lost, 0 new, and 4 neither. It does not amend headline structural-tier stars or make a total-uncertainty claim.

## Minimal reporter API

c4_two_numbers.report is a pure function over aligned finite vectors. It does not fit, calibrate, or infer a zero decision. Supply a Boolean decision when one was actually declared; otherwise pass None and say why in the provenance string.

```python
import numpy as np
from c4_two_numbers import report

y = np.asarray([0.0, 0.0, 1.0, 3.0])
scores = np.asarray([0.0, 0.2, 0.4, 0.8])
decision = np.asarray([True, False, False, False], dtype=bool)

row = report(
    y, scores,
    predicted_zero=decision,
    decision_provenance='fixed threshold documented before evaluation',
)
print(row['zero_accuracy'], row['tau_positive'], row['tau_all'])
print(row['prediction_ties_zero'], row['prediction_ties_positive'])
```

The reporter filters tau_positive solely by y > 0; it does not remove positive nodes predicted zero. It returns labelled true_zero, missed_zero, false_zero, and true_positive counts, support, error rates, all-node tau, tie counts, denominator, mixture regime, and NA-reason fields. It rejects nonfinite or misaligned input, negative reference values, a non-Boolean decision vector, and empty decision provenance.

For a method with no decision, do not substitute an exact auxiliary mask:

```python
row = report(
    y, scores,
    predicted_zero=None,
    decision_provenance='method releases scores but no zero decision',
)
assert row['zero_accuracy_na_reason'] == 'no_declared_zero_decision'
```

The release package must add node IDs/order, graph and target checksums, evaluation support, target convention, rule-selection provenance, and raw arrays to this in-memory row. The reporter cannot reconstruct those facts from an aggregate Kendall column.

## What this guide does not reproduce

Do not invoke analysis/analyse_c3_benchmarks.py unless a separate full external traversal is authorised. Do not execute BRAVA checkpoints to create a retrospective external two-number pilot. Do not rerun probes/probe_target_noise_refit.py; its 12,000 refits are an input to the study, not a reproduction prerequisite. The study's claims are limited to the existing audit, cache-only correctness check, reporting contract, and paired dynamic-tier follow-through.

## Reproducing the expanded-scope lanes

> The paragraph above still holds for everything it names. These four lanes were authorised
> separately by the 2026-09-08 training authorisation and each has its own runner and verifier.
> Run the verifier before the runner in every case; the verifiers use temporary fixtures and
> never touch the corpus.

Interpreter is the conda env `influence`, by absolute path
(`<conda-root>\envs\influence\python.exe`). **Never `pip install` numpy, scipy or
scikit-learn into it** — a pip wheel reintroduces the OpenBLAS/MKL abort that dies with no
traceback. CPU only.

```
# r=1 ablation: verifier, determinism pilot, 800 cells, analysis (~5 h)
python checks/verify_r1_ablation.py
python probes/probe_r1_ablation.py            # runs the pilot gate first, then the grid; resumable
python analysis/analyse_r1_ablation.py          # -> results/phase6_r1_ablation/{cells,paired}.csv, RESULTS_*.txt

# Precision witness: one graph at a time, serial by design (--workers must be 1)
python checks/verify_c3_precision_witness.py
python probes/probe_c3_precision_witness.py --graph com-youtube --brava data/brava --workers 1
#   ... repeat for amazon, dblp, cit-Patents, com-lj. Peak scratch ~1.14 GB for cit-Patents.

# Structural target-noise bootstrap and buffered CV: validation only, the corpora exist
python checks/verify_structural_target_noise.py
python checks/verify_structural_target_noise_analysis.py
python checks/verify_buffered_cv.py
```

The BRAVA/ABCDE corpus now lives at `data/brava/` (gitignored) rather than in a temporary
directory that any cleanup would delete. Its four pinned identities re-verify there.

**Do not** re-run `probes/probe_structural_target_noise_refit.py` or the buffered controller to
reproduce a claim: like `probes/probe_target_noise_refit.py` above, those completed corpora are inputs
to the study, not reproduction prerequisites. **Do not** rewrite a recorded source hash to get past
a resume guard — if a hash does not bind, the affected evidence is rerun, not rationalised.

`checks/verify_robustness_rerun.py` exits 1 by design of its bar: CHECK 1 misses 1e-6 (max |Δτ| 0.012,
model rows only), traced to registry column order; CHECK 2 passes. `checks/verify_c3_fallback.py` and
`checks/verify_brava_corpus_identity.py` only verify; each writes under `results/` only when given `--record`.

## Root integration — what changed under the commands above

> The two "do not re-run" paragraphs above describe the *reproduction* posture and still
> do. Separately, on 2026-09-11 the author authorised a one-time root integration of the Task 6
> audit findings ("apply all proposed fixes … free to run any re-downloads or re-sweeps, no
> compromises"), and several of those re-runs are exactly the ones the paragraphs say not to
> repeat for reproduction. This section records what that changes for anyone following
> this guide.

**Corpus.** Six 5-node orbits (56, 57, 65, 66, 68, 70) were retagged hop 1 → hop 2 after
the exact eccentricity derivation contradicted the empirical calibrator (finding P1-01;
`checks/verify_pipeline.py` 2c-5 now gates it). Every r=1 cell of the subgraph-inclusive tiers in
`sweep_*.csv`, `estimators/sweep_*__*.csv` and their `cache_oof_*` archives was refit on
2026-09-11; r=0/2/3 cells are byte-identical to before. Pre-refit copies carry a
`.preorbit5` suffix; the root-level ones live under `data/cache_archive/pre_orbit5_20260911/`
since the 2026-09-13 tidy-up, the `estimators/` ones beside their files. A hash recorded in a `cache_meta_*.json` was never edited
to get past a resume guard.

**Scripts whose default output changed.**

| Script | Change | Reproduce the old table with |
|---|---|---|
| `analysis/analyse_betweenness.py` | reads the reported `log1p` arm (finding P2-03); prints the arm | `--arm=raw` |
| `analysis/analyse_edge5.py`, `analysis/analyse_edge_tier.py` | new `--objective {raw,reported}` (default `raw`, the historical arm); header prints the objective | default |
| `analysis/analyse_c3_benchmarks.py` | exact `tau_floor` beside the approximation, ABCDE gate detail in the structure rows, `tau_floor_registered` per cell (P3-02/03/04) | no flag; the deltas are bookkeeping only (study §26i) |
| `analysis/analyse_robustness.py`, `figures/make_fig3.py` | header states the betweenness objective (raw, historical); both later gained `--objective {raw,reported}` (log1p for betweenness, same forest, same folds); the reported arm writes `robustness_log1p.csv` / `fig3_robustness_log1p.png` and can never overwrite the raw files; `checks/verify_robustness_rerun.py` compares the raw re-run to `c8_historical_pre_20260912/robustness.csv` | default (raw) |

**Registered numbers that were re-measured, and where the historical ones live.**
The root-integration controllers `results/phase6_root_integration_{controller,stage2,stage3,stage4}_20260912.ps1`
re-ran the lanes below (logs beside them). The archives hold the complete historical outputs:

| Lane | Historical numbers quoted above | Archive of the historical output |
|---|---|---|
| A7 refit arm (`probes/probe_target_noise_refit.py --reps 200 --check-pairing`) and `analysis/analyse_paired_target_noise.py` | 41 seed flags, 38 retained / 3 lost / 0 new / 4 neither | `results/phase6_c5_pre_orbit5_refit_20260906/` |
| Structural bootstrap and buffered CV | 12,000 cells / 45 contrasts; 480 contrasts | `results/phase6_structural_pre_orbit5_retag_20260910/`, `results/phase6_buffered_pre_orbit5_retag_20260910/` |
| B1 sample efficiency, objective-horizon probe | §26e/§26h of the study | same C5 archive |
| edge5 and facebook edge-tier addenda (stage 3) | study §"The edge axis" table | `results/c8_historical_pre_20260912/` |
| Angle 4 robustness, raw arm re-run + new log1p arm (stage 4) | study §"Angle 4" / Finding 9 tables, `fig3_robustness.png` | `results/c8_historical_pre_20260912/` (`RESULTS_robustness.txt`, `robustness.csv` copied there by the controller before the re-run) |

C3/C4 were regenerated first and are **already final**: `analysis/score_c3_results.py` reproduces
the four registered verdicts to the digit on the regenerated cells
(`results/VERIFY_phase6_c3_scoring_20260912.txt`). The command list above for C3/C4
is therefore unchanged.

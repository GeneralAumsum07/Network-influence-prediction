# Phase 0–6 final audit protocol

**Status correction, 2026-09-12:** the initial source review is complete over 87
paths, recorded in `results/phase6_task6_coverage_ledger_20260911.json` with status
`reviews_complete_pending_root_integration`. Reruns, changed-file review at final
hashes and evidence reconciliation remain pending. The "not started" statement
below records the protocol's preparation date, not its current execution state.

Prepared 2026-09-09. **Status: not started.** This defines the final review campaign;
the requirements inventory and scoped implementation reviews do not substitute for it.
Run after the remaining implementation lanes are complete. The long sweeps may still
be running during source review, but final evidence reconciliation requires their
complete, validated outputs.

## Coverage and ownership

Enumerate every project Python file with `rg --files -g '*.py'`, excluding external
source snapshots and generated environments. Record the exact reviewed SHA-256 for
each file, reviewer, disposition, findings and regression evidence. Include new
follow-up scripts even when they are absent from the September 8 inventory.

The coverage is broader than Python: include vendored `vendor/orca.cpp` and its
build/call boundary, environment specifications, graph manifests, and executable
controllers under `results/` (including the structural controller PowerShell script).
Generated result data are checked as evidence, not excluded merely because their
directory also contains scripts. Treat external downloaded source snapshots as
third-party inputs and validate the specific interfaces actually used.

Use one broad review campaign with these nonoverlapping partitions:

1. Core graph computation and data production: `influence/` except learning modules,
   stage 0/1, acquisition, calibration, cache repair, generators and their verifier;
   vendored ORCA and the environment/data contracts.
2. Learning and statistical analysis: learning modules, stage 2, experiment runner,
   all non-C3/C4 analyses and probes, A7 scorer and associated verifiers; finite
   training controllers and their checkpoint/exit semantics.
3. External audit and reporting: C3/C4 scripts and tests, figure/build utilities,
   documentation assertions and the evidence/prose reconciliation.

Root integrates partition findings, checks cross-module contracts and assigns every
new file exactly once. GPT 5.6 Terra performs subagent reviews. No CodeRabbit,
commits, publishing or new research outside Phase 6.

## Review questions

- Can input identities, graph cleaning, target conventions or feature order change
  without invalidating cached or resumed results?
- Do global target quantities appear in local features, feature selection or held-out
  preprocessing? Are shared simulations and transductive topology stated accurately?
- Are folds, seeds, transforms and comparisons paired as claimed? Do missing,
  duplicated, nonfinite or interrupted observations fail explicitly?
- Do thresholds, sparse numerical methods and degenerate graph cases agree with
  independent analytical or reference calculations?
- Are statistical families, effect sizes, uncertainty components and conditional
  claims correctly named? Does any prose turn an approximate threshold into proof
  of comparable dynamics or a diagnostic buffer into independence?
- Do plots and documents use the actual reported objective, tier and corpus? Are
  historical registered verdicts preserved alongside contradictory follow-ups?
- Do utility commands risk overwriting inputs, reusing an incompatible checkpoint,
  launching overlapping writers or exceeding the declared memory/CPU envelope?

## Closure evidence

Record findings with severity, affected paths, concrete trigger, consequence, fix
and verification. Resolve actionable defects, then re-review changed files in the
same campaign. Do not count a file as reviewed solely because a test imported it.
Keep limitations separate from defects and state what evidence would resolve them.

If a repair changes a source dependency of an active or completed sweep, assess
whether it changes data, model fits, selection or scoring before resuming. Never
rewrite recorded source hashes merely to bypass a resume guard. Stop affected
writers, preserve old artifacts and rerun affected evidence when necessary. A
source freeze protects consistency during a run; it does not excuse a confirmed
correctness defect or certify the old results after an incompatible repair.

Run the existing pipeline, generator, documentation and C3/C4 checks plus relevant
new verifiers. Refresh provenance-bearing reports affected by source changes, with
dated records explaining why they were regenerated. A passing command is evidence
only for its actual assertions; it is not universal scientific validation.

Finally require complete structural bootstrap contrasts, complete buffered logical
cell accounting (including infeasible/unresolved cases), all precision-witness input
and identity checks, and all radius-one ablation comparisons. Reconcile the plan,
study, HANDOFF, paper, reproduction guide and completion ledger against those files.
Explicitly retain unavailable external predictions, unknown producer conventions
and Phase 7 deferrals. Claim closure only after this contract is met.

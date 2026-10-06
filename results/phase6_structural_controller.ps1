# Keep the authorised pilot -> full-run sequence alive across an interrupted UI
# session. Python owns data validation and checkpointing; this wrapper only orders
# processes and checks exit codes. It never changes source or cache files.
# NOTE (2026-09-11, Claude Opus 5, Task 6 finding P2-10(d)): --rf-jobs 8 is hard-coded
# for this 16-core machine. The runner's parallel-equivalence check bounds the numerical
# effect of the thread count (documented tolerance in the runner), so a different value
# is a portability choice, not a correctness one. Left as-is on purpose.
param([int]$PilotProcessId = 0)
$ErrorActionPreference = 'Stop'
$phase6Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$phase6Python = Join-Path $env:USERPROFILE 'miniconda3/envs/influence/python.exe'
Set-Location -LiteralPath $phase6Root
try {
    if ($PilotProcessId -gt 0) {
        $pilotProcess = Get-Process -Id $PilotProcessId -ErrorAction SilentlyContinue
        if ($null -ne $pilotProcess) { $pilotProcess.WaitForExit() }
    }
    # An idempotent pilot resume checks all rows, hashes and configuration even
    # if the previous process finished while this wrapper was being launched.
    Write-Output "$(Get-Date -Format o) Validate/finish two-replicate pilot"
    & $phase6Python probe_structural_target_noise_refit.py --reps 2 --rf-jobs 8 --out results/results_target_noise_refit_structural_pilot.csv --provenance results/provenance_target_noise_refit_structural_pilot.json
    if ($LASTEXITCODE -ne 0) { throw "Pilot validation failed with exit $LASTEXITCODE" }
    $pilotRows = @(Import-Csv -LiteralPath 'results/results_target_noise_refit_structural_pilot.csv')
    if ($pilotRows.Count -ne 120) { throw "Pilot has $($pilotRows.Count) rows; expected120" }
    Write-Output "$(Get-Date -Format o) Pilot passed; starting complete200-replicate run"
    & $phase6Python probe_structural_target_noise_refit.py --reps 200 --rf-jobs 8
    if ($LASTEXITCODE -ne 0) { throw "Full run failed with exit $LASTEXITCODE" }
    Write-Output "$(Get-Date -Format o) Full run complete; paired analysis"
    & $phase6Python analyse_structural_target_noise.py
    if ($LASTEXITCODE -ne 0) { throw "Paired analysis failed with exit $LASTEXITCODE" }
    Write-Output "$(Get-Date -Format o) Structural follow-up complete"
} catch {
    Write-Error $_
    exit 1
}

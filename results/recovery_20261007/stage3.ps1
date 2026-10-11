# Stage 3 of the post-retag re-runs, second recovery (2026-10-07): the historical
# r=1 / raw-objective lanes Task 6 run C8 chose to re-run (findings P1-01, P2-11,
# P3-08). Same four steps, same arguments and same output files as
# results/recovery_20260914/stage3.ps1; that file's header explains why each runs.
#
# Differences: no wait loop (that copy polled results/phase6_root_integration_stage2_20260912.log,
# whose terminal line is an old FAILED, so it would have started at once and logged
# that stale line as stage 2's outcome); this folder's run.py starts stage 3 only
# after stage 2 exits 0. Python stderr goes to this folder, not the run C8 log.
#
# Resumable since 2026-10-11 (after the 2026-10-10 19:34 self-reset): every step
# passes --checkpoint, so each fold-seed tau is recorded as it lands under
# checkpoints\ and a relaunch refits only what it never reached. Finished steps
# replay in seconds and rewrite their RESULTS file byte-identically, so after a
# reset the whole stage is simply run again. A checkpoint recorded under different
# code, inputs or arguments refuses (the step FAILs) rather than mixing answers;
# see influence/checkpoint.py. The checkpoints are run state, not results: they
# can be deleted once the stage is COMPLETE, and are never edited.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root
$py = Join-Path $env:USERPROFILE 'miniconda3/envs/influence/python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$here = 'results\recovery_20261007'
$ck = "$here\checkpoints"

function Log([string]$Msg) { Write-Output "$(Get-Date -Format o) $Msg" }

function Invoke-Step([string]$Name, [string[]]$StepArguments, [string]$Stdout) {
    Log "BEGIN $Name"
    # Redirect through cmd.exe so the captured file holds Python's own UTF-8 bytes;
    # PowerShell 5.1's '>' re-encodes native output as UTF-16.
    $quoted = ($StepArguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
    & cmd.exe /c "`"$py`" $quoted > `"$Stdout`" 2>> $here\stage3.python.err.log"
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit $LASTEXITCODE" }
    Log "END $Name"
}

try {
    $live = @(Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
        Where-Object { $_.CommandLine -match 'probe_structural_target_noise_refit|probe_buffered_cv|probe_sample_efficiency|probe_objective_horizon|probe_target_noise' })
    if ($live.Count -gt 0) { throw 'A fitting lane is still running.' }

    Invoke-Step 'edge5 raw arm, five networks' @('analyse_edge5.py', '--checkpoint', "$ck\edge5_raw.jsonl") 'results/RESULTS_edge5.txt'
    Invoke-Step 'edge5 reported arm, betweenness only' @('analyse_edge5.py', '--objective', 'reported', '--targets', 'betweenness', '--checkpoint', "$ck\edge5_reported_betweenness.jsonl") 'results/RESULTS_edge5_betweenness_log1p_20260912.txt'
    Invoke-Step 'edge tier on facebook, reported arm' @('analyse_edge_tier.py', 'facebook_combined', '--objective', 'reported', '--checkpoint', "$ck\edge_tier_facebook_reported.jsonl") 'results/RESULTS_edge_tier_log1p_facebook_20260912.txt'
    Invoke-Step 'subgraph tier on facebook, reported arm' @('analyse_edge_tier.py', 'facebook_combined', '--tier', 'subgraph', '--objective', 'reported', '--checkpoint', "$ck\subgraph_tier_facebook_reported.jsonl") 'results/RESULTS_edge_tier_subgraph_log1p_facebook_20260912.txt'

    Log 'STAGE 3 LANES COMPLETE'
} catch {
    Log "FAILED: $_"
    exit 1
}

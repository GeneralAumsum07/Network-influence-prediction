# Stage 3 of the post-retag re-runs, second recovery (2026-10-07): the historical
# r=1 / raw-objective lanes Task 6 run C8 chose to re-run (findings P1-01, P2-11,
# P3-08). Same four steps, same arguments and same output files as
# results/recovery_20260914/stage3.ps1; that file's header explains why each runs.
#
# Differences: no wait loop (that copy polled results/phase6_root_integration_stage2_20260912.log,
# whose terminal line is an old FAILED, so it would have started at once and logged
# that stale line as stage 2's outcome); this folder's run.py starts stage 3 only
# after stage 2 exits 0. Python stderr goes to this folder, not the run C8 log.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root
$py = Join-Path $env:USERPROFILE 'miniconda3/envs/influence/python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$here = 'results\recovery_20261007'

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

    Invoke-Step 'edge5 raw arm, five networks' @('analyse_edge5.py') 'results/RESULTS_edge5.txt'
    Invoke-Step 'edge5 reported arm, betweenness only' @('analyse_edge5.py', '--objective', 'reported', '--targets', 'betweenness') 'results/RESULTS_edge5_betweenness_log1p_20260912.txt'
    Invoke-Step 'edge tier on facebook, reported arm' @('analyse_edge_tier.py', 'facebook_combined', '--objective', 'reported') 'results/RESULTS_edge_tier_log1p_facebook_20260912.txt'
    Invoke-Step 'subgraph tier on facebook, reported arm' @('analyse_edge_tier.py', 'facebook_combined', '--tier', 'subgraph', '--objective', 'reported') 'results/RESULTS_edge_tier_subgraph_log1p_facebook_20260912.txt'

    Log 'STAGE 3 LANES COMPLETE'
} catch {
    Log "FAILED: $_"
    exit 1
}

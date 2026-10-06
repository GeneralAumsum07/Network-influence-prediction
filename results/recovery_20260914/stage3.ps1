# Stage 3 of the post-retag re-runs: the historical r=1 / raw-objective lanes that
# Task 6 run C8 decided to re-run rather than merely label (findings P1-01, P2-11,
# P3-08). Written 2026-09-12 by Claude Opus 5 (Task 6 root integration, run C8).
#
# Waits for stage 2 (phase6_root_integration_stage2_20260912.ps1: B1, objective
# horizon, A7) to reach a terminal line, so no two fitting lanes share the machine.
#
# What runs and why:
#   analyse_edge5.py (raw arm, all five networks) - the 2026-08-26 file covered two
#     networks and predates BOTH radius corrections of 2026-09-11 (six 5-node node
#     orbits and nine 5-node edge orbits moved hop 1 -> hop 2), so its r=1 rows used
#     columns a radius-1 observer cannot compute. The old file is kept at
#     results/c8_historical_pre_20260912/RESULTS_edge5.txt.
#   analyse_edge5.py --objective reported --targets betweenness - the same
#     comparison on the reported log1p arm, betweenness only (the spread targets'
#     reported arm IS the raw arm, so re-fitting them would only reproduce rows).
#   analyse_edge_tier.py facebook_combined --objective reported (edge, then
#     subgraph rung) - P2-11's proposed dated addendum: does the group that carries
#     Finding 10 change when the rung is isolated under the objective the study
#     reports? r=2 column sets are unchanged by the retag, so the historical raw-arm
#     files stay valid for what they are and are NOT regenerated.
# Not re-run (retag-independent at max_hop 3, raw objective already labelled in
# fig3 and prose): analyse_robustness.py. See results/HISTORICAL_LANES_NOTE_20260912.md.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root
$py = Join-Path $env:USERPROFILE 'miniconda3/envs/influence/python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$stage2Log = 'results/phase6_root_integration_stage2_20260912.log'

function Log([string]$Msg) { Write-Output "$(Get-Date -Format o) $Msg" }

function Invoke-Step([string]$Name, [string[]]$StepArguments, [string]$Stdout) {
    Log "BEGIN $Name"
    # Redirect through cmd.exe so the captured file holds Python's own UTF-8 bytes;
    # PowerShell 5.1's '>' re-encodes native output as UTF-16.
    $quoted = ($StepArguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
    & cmd.exe /c "`"$py`" $quoted > `"$Stdout`" 2>> results\phase6_c8_controller_20260912.err.log"
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit $LASTEXITCODE" }
    Log "END $Name"
}

try {
    Log 'Waiting for stage 2 to reach a terminal line'
    while ($true) {
        $done = $false
        if (Test-Path -LiteralPath $stage2Log) {
            $text = Get-Content -LiteralPath $stage2Log -Raw -ErrorAction SilentlyContinue
            if ($text -match 'STAGE 2 LANES COMPLETE|FAILED') { $done = $true }
        }
        if ($done) { break }
        Start-Sleep -Seconds 300
    }
    Log "Stage 2 terminal: $((Get-Content -LiteralPath $stage2Log | Select-Object -Last 1))"

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

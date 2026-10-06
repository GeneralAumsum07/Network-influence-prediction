# Stage 4 of the post-retag re-runs: Angle 4 (analyse_robustness.py), the one
# historical lane stage 3 chose NOT to re-run. Written 2026-09-12 by Claude Opus 5
# on Rachit's instruction ("queue the angle 4 re-run", 15:51 IST; plan §0 of
# ~/.claude/plans/so-gpt-6-astra-has-fluffy-marble.md).
#
# Waits for stage 3 (phase6_root_integration_stage3_20260912.ps1: edge5 + facebook
# edge-tier addenda) to reach a terminal line, so no two fitting lanes share the
# machine.
#
# What runs and why:
#   1. Archive the 2026-08-27 outputs before anything overwrites them:
#      RESULTS_robustness.txt and robustness.csv -> c8_historical_pre_20260912/.
#      (fig3_robustness.png was archived there on 2026-09-12 already, pre-label.)
#   2. analyse_robustness.py, default (raw) arm, full protocol: 5 networks x
#      2 targets x 6 rho x 3 draws x 4 methods = 640 rows. HISTORICAL_LANES_NOTE
#      said this "would reproduce identical numbers"; that was an inference.
#      verify_robustness_rerun.py (step 5) measures it against the archive.
#   3. make_fig3.py (raw arm) - regenerates fig3_robustness.png from the new CSV.
#   4. analyse_robustness.py --objective reported --targets betweenness ->
#      results/robustness_log1p.csv + RESULTS_robustness_log1p_20260912.txt.
#      Betweenness only: the spread targets' reported arm IS the raw arm, so
#      re-fitting them would reproduce rows (same rule stage 3 applied to edge5).
#      Then make_fig3.py --objective reported -> fig3_robustness_log1p.png.
#   5. verify_robustness_rerun.py -> VERIFY_robustness_rerun_20260912.txt:
#      raw re-run vs archive (bar 1e-06), and log1p vs raw invariant rows.
# Fit budget: HISTORICAL_LANES_NOTE estimated 2-3 h for the raw arm; the log1p
# arm is roughly half (one target). Nothing here is resumable, so a FAILED line
# means re-run the step by hand, not the whole stage.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root
$py = Join-Path $env:USERPROFILE 'miniconda3/envs/influence/python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$stage3Log = 'results/phase6_root_integration_stage3_20260912.log'
$archive = 'results/c8_historical_pre_20260912'

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
    Log 'Waiting for stage 3 to reach a terminal line'
    while ($true) {
        $done = $false
        if (Test-Path -LiteralPath $stage3Log) {
            $text = Get-Content -LiteralPath $stage3Log -Raw -ErrorAction SilentlyContinue
            if ($text -match 'STAGE 3 LANES COMPLETE|FAILED') { $done = $true }
        }
        if ($done) { break }
        Start-Sleep -Seconds 300
    }
    Log "Stage 3 terminal: $((Get-Content -LiteralPath $stage3Log | Select-Object -Last 1))"

    $live = @(Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
        Where-Object { $_.CommandLine -match 'probe_structural_target_noise_refit|probe_buffered_cv|probe_sample_efficiency|probe_objective_horizon|probe_target_noise|analyse_edge5|analyse_edge_tier' })
    if ($live.Count -gt 0) { throw 'A fitting lane is still running.' }

    # Step 1: archive. Copy, never move - the study quotes these paths until the
    # re-run lands, and a failed step 2 must leave them readable.
    foreach ($f in @('RESULTS_robustness.txt', 'robustness.csv')) {
        $src = Join-Path 'results' $f
        $dst = Join-Path $archive $f
        if (Test-Path -LiteralPath $dst) { Log "Preserving existing pre-rerun archive $dst"; continue }
        Copy-Item -LiteralPath $src -Destination $dst
        Log "archived $src -> $dst"
    }

    Invoke-Step 'robustness raw arm, five networks' @('analyse_robustness.py') 'results/RESULTS_robustness.txt'
    Invoke-Step 'fig3 raw arm' @('make_fig3.py') 'results/make_fig3_raw_20260912.log'
    Invoke-Step 'robustness reported arm, betweenness only' @('analyse_robustness.py', '--objective', 'reported', '--targets', 'betweenness') 'results/RESULTS_robustness_log1p_20260912.txt'
    Invoke-Step 'fig3 reported arm' @('make_fig3.py', '--objective', 'reported') 'results/make_fig3_log1p_20260912.log'
    Invoke-Step 'verify raw re-run and log1p arm' @('verify_robustness_rerun.py') 'results/VERIFY_robustness_rerun_20260912.txt'

    Log 'STAGE 4 LANES COMPLETE'
} catch {
    Log "FAILED: $_"
    exit 1
}

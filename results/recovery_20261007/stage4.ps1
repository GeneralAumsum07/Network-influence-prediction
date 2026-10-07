# Stage 4 of the post-retag re-runs, second recovery (2026-10-07): Angle 4
# (analyse_robustness.py, raw and reported arms), fig3, and the re-run verifier.
# Same five steps, same arguments and same output files as
# results/recovery_20260914/stage4.ps1; that file's header explains each step.
#
# Differences: no wait loop (that copy polled results/phase6_root_integration_stage3_20260912.log,
# whose terminal line is an old FAILED); this folder's run.py starts stage 4 only after
# stage 3 exits 0. Python stderr goes to this folder, not the run C8 log.
#
# The step 1 archive is already in place (results/c8_historical_pre_20260912 holds
# RESULTS_robustness.txt and robustness.csv), so step 1 logs "Preserving existing" and
# copies nothing. Nothing in this stage is resumable: a FAILED line means re-run the
# failed step by hand, not the whole stage.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root
$py = Join-Path $env:USERPROFILE 'miniconda3/envs/influence/python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$archive = 'results/c8_historical_pre_20260912'
$here = 'results\recovery_20261007'

function Log([string]$Msg) { Write-Output "$(Get-Date -Format o) $Msg" }

function Invoke-Step([string]$Name, [string[]]$StepArguments, [string]$Stdout) {
    Log "BEGIN $Name"
    # Redirect through cmd.exe so the captured file holds Python's own UTF-8 bytes;
    # PowerShell 5.1's '>' re-encodes native output as UTF-16.
    $quoted = ($StepArguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
    & cmd.exe /c "`"$py`" $quoted > `"$Stdout`" 2>> $here\stage4.python.err.log"
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit $LASTEXITCODE" }
    Log "END $Name"
}

try {
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

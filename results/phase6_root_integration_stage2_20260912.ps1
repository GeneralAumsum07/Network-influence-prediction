# Stage 2 of the post-retag re-runs: the three fitting lanes that verify themselves
# against sweep_*.csv (B1 sample efficiency, objective-horizon probe, A7 target-noise
# frozen + refit arms) and their analysers.
# Written 2026-09-12 by Claude Opus 5 (Task 6 root integration, run C5).
#
# Waits for stage 1 (phase6_root_integration_controller_20260912.ps1: structural
# bootstrap, then buffered CV) to reach a terminal line before starting, so no two
# fitting lanes ever share the machine. Stage 1's outcome does not gate stage 2 -
# these lanes read only the sweep corpus - but it is logged either way.
#
# Each probe re-reads its own output CSV on start-up and resumes cell by cell, so the
# pre-refit files are MOVED OUT (already copied to results/phase6_c5_pre_orbit5_refit_20260906/)
# before the probe starts; leaving them in place would resume 62-column r=1 cells
# under a 56-column registry, which is exactly the splice the resume guards exist
# to prevent. Every probe's self-check (--check / --check-pairing / raw-arm
# reproduction) runs first and a failure stops the lane.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
$py = Join-Path $env:USERPROFILE 'miniconda3/envs/influence/python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$stage1Log = 'results/phase6_root_integration_controller_20260912.log'
$archive = 'results/phase6_c5_pre_orbit5_refit_20260906'

function Log([string]$Msg) { Write-Output "$(Get-Date -Format o) $Msg" }

function Invoke-Step([string]$Name, [string[]]$Args, [string]$Stdout) {
    Log "BEGIN $Name"
    # Redirect through cmd.exe so the captured file holds Python's own UTF-8 bytes;
    # PowerShell 5.1's '>' re-encodes native output as UTF-16, which the doc
    # verifier and grep cannot read as text.
    $quoted = ($Args | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $target = if ($Stdout) { '"' + $Stdout + '"' } else { '"results/phase6_c5_controller_20260912.out.log"' }
    $op = if ($Stdout) { '>' } else { '>>' }
    & cmd.exe /c "`"$py`" $quoted $op $target 2>> results\phase6_c5_controller_20260912.err.log"
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit $LASTEXITCODE" }
    Log "END $Name"
}

function Remove-PreRefit([string]$Path) {
    # Refuse to delete anything that is not already safely archived byte-for-byte.
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $copy = Join-Path $archive (Split-Path -Leaf $Path)
    if (-not (Test-Path -LiteralPath $copy)) { throw "$Path has no archived copy at $copy" }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash) {
        throw "$Path differs from its archived copy; not removing"
    }
    Remove-Item -LiteralPath $Path -Force
    Log "removed pre-refit $Path (archived at $copy)"
}

try {
    Log 'Waiting for stage 1 to reach a terminal line'
    while ($true) {
        $done = $false
        if (Test-Path -LiteralPath $stage1Log) {
            $text = Get-Content -LiteralPath $stage1Log -Raw -ErrorAction SilentlyContinue
            if ($text -match 'ROOT INTEGRATION LANES COMPLETE|FAILED') { $done = $true }
        }
        if ($done) { break }
        Start-Sleep -Seconds 300
    }
    Log "Stage 1 terminal: $((Get-Content -LiteralPath $stage1Log | Select-Object -Last 1))"

    $live = @(Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
        Where-Object { $_.CommandLine -match 'probe_structural_target_noise_refit|probe_buffered_cv|probe_sample_efficiency|probe_objective_horizon|probe_target_noise' })
    if ($live.Count -gt 0) { throw 'A fitting lane is still running.' }

    # --- B1 sample efficiency ------------------------------------------------
    Remove-PreRefit 'results/sample_efficiency.csv'
    Invoke-Step 'B1 harness check' @('probe_sample_efficiency.py', '--check') $null
    Invoke-Step 'B1 sweep (5,600 cells)' @('probe_sample_efficiency.py') $null
    Invoke-Step 'B1 analysis' @('analyse_sample_efficiency.py') 'results/RESULTS_sample_efficiency.txt'

    # --- objective horizon ----------------------------------------------------
    Remove-PreRefit 'results/objective_horizon_probe.csv'
    Invoke-Step 'objective-horizon probe (800 fits)' @('probe_objective_horizon.py') $null
    Invoke-Step 'objective-horizon analysis' @('analyse_objective_horizon.py') 'results/RESULTS_objective_horizon.txt'

    # --- A7 target noise: frozen arm, refit arm, scoring, paired analysis ---------
    Remove-PreRefit 'results_target_noise.csv'
    Remove-PreRefit 'results_target_noise_refit.csv'
    Remove-PreRefit 'results_target_noise_scored.csv'
    Remove-PreRefit 'results/results_paired_target_noise.csv'
    Remove-PreRefit 'results/RESULTS_paired_target_noise.txt'
    Invoke-Step 'A7 frozen arm (200 reps, no fits)' @('probe_target_noise.py', '--reps', '200') $null
    # --check-pairing re-derives the frozen arm's replicate-0 tau before any fit and
    # then continues into the full run, so one invocation covers both.
    Invoke-Step 'A7 refit arm (200 reps, 12,000 fits, pairing checked first)' @('probe_target_noise_refit.py', '--reps', '200', '--check-pairing') $null
    Invoke-Step 'A7 arm-2 scoring' @('score_a7_arm2.py') 'results/RESULTS_a7_arm2_scoring.txt'
    Invoke-Step 'A7 paired analysis' @('analyse_paired_target_noise.py') $null

    Log 'STAGE 2 LANES COMPLETE'
} catch {
    Log "FAILED: $_"
    exit 1
}

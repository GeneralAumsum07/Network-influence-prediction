# Stage 2 of the post-retag re-runs, second recovery (2026-10-07): B1 sample
# efficiency, objective-horizon probe, A7 target-noise frozen + refit arms, and
# their analysers. Same steps, same order and same arguments as
# results/recovery_20260914/stage2.ps1. Differences:
#
#   * No wait loop. That copy polled results/phase6_root_integration_controller_20260912.log,
#     whose terminal line is the old, invalid FAILED, so it "waited" for nothing.
#     This folder's run.py starts a stage only after the previous one exits 0, and it
#     checks stage 1's real completion (recovery_20260914/controller.log) first.
#   * B1: check_b1_resume.py replaces Remove-PreRefit for results/sample_efficiency.csv.
#     The pre-refit file was already moved out on 2026-09-13 20:26; what is on disk now
#     is the killed run's own partial output (1,540 of 5,600 cells), which the probe
#     resumes on. Remove-PreRefit would refuse it ("differs from its archived copy").
#   * Objective horizon: check_objective_horizon_resume.py replaces Remove-PreRefit for
#     results/objective_horizon_probe.csv (amended 2026-10-07 ~10:00). The probe was
#     lost twice that day because it wrote only at the end; it now checkpoints per
#     (target, radius) block and resumes by key, so a partial file is expected after
#     an interruption and Remove-PreRefit would refuse it. The pre-refit copy is
#     already archived and absent from results/ (removed 2026-09-13 20:26).
#   * The other Remove-PreRefit calls stay as guards. On 2026-10-07 all their targets
#     are absent (removed 2026-09-13 20:26), so each returns without doing anything;
#     they would only act if a stale pre-refit file had somehow reappeared.
#   * Python stdout/stderr go to this folder, not to the 2026-09-12 run C5 logs.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root
$py = Join-Path $env:USERPROFILE 'miniconda3/envs/influence/python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$archive = 'results/phase6_c5_pre_orbit5_refit_20260906'
$here = 'results\recovery_20261007'

function Log([string]$Msg) { Write-Output "$(Get-Date -Format o) $Msg" }

function Invoke-Step([string]$Name, [string[]]$StepArguments, [string]$Stdout) {
    Log "BEGIN $Name"
    # Redirect through cmd.exe so the captured file holds Python's own UTF-8 bytes;
    # PowerShell 5.1's '>' re-encodes native output as UTF-16, which the doc
    # verifier and grep cannot read as text.
    $quoted = ($StepArguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $target = if ($Stdout) { '"' + $Stdout + '"' } else { "`"$here\stage2.python.out.log`"" }
    $op = if ($Stdout) { '>' } else { '>>' }
    & cmd.exe /c "`"$py`" $quoted $op $target 2>> $here\stage2.python.err.log"
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
    $live = @(Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
        Where-Object { $_.CommandLine -match 'probe_structural_target_noise_refit|probe_buffered_cv|probe_sample_efficiency|probe_objective_horizon|probe_target_noise' })
    if ($live.Count -gt 0) { throw 'A fitting lane is still running.' }

    # --- B1 sample efficiency ------------------------------------------------
    Invoke-Step 'B1 resume gate' @("$here\check_b1_resume.py") $null
    Invoke-Step 'B1 harness check' @('probe_sample_efficiency.py', '--check') $null
    Invoke-Step 'B1 sweep (resume; 4,060 of 5,600 cells left at 2026-10-07)' @('probe_sample_efficiency.py') $null
    Invoke-Step 'B1 analysis' @('analyse_sample_efficiency.py') 'results/RESULTS_sample_efficiency.txt'

    # --- objective horizon ----------------------------------------------------
    Invoke-Step 'objective-horizon resume gate' @("$here\check_objective_horizon_resume.py") $null
    Invoke-Step 'objective-horizon probe (800 fits, resumes by key)' @('probe_objective_horizon.py') $null
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

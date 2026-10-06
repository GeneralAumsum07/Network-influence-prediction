# Serial re-run of the two registry-bound Phase 6 lanes after the orbit-5 retag.
# Written 2026-09-12 by Claude Opus 5 (Task 6 root integration, runs C3 and C4).
#
# Order is structural first, then buffered, because the buffered lane's measured
# buffers come from the structural Moran correlogram and both lanes want the
# whole machine (--rf-jobs 8 inside each controller). Nothing runs concurrently.
# Each inner controller owns its own validation; this wrapper only sequences
# them and stops at the first non-zero exit so a failed lane is never followed
# by a lane that would silently consume its partial output.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root

function Invoke-Lane([string]$Name, [string]$Script) {
    Write-Output "$(Get-Date -Format o) BEGIN $Name"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Script `
        1>> "results/phase6_${Name}_controller_20260912.log" `
        2>> "results/phase6_${Name}_controller_20260912.err.log"
    if ($LASTEXITCODE -ne 0) { throw "$Name lane failed with exit $LASTEXITCODE" }
    Write-Output "$(Get-Date -Format o) END $Name"
}

try {
    # Refuse to start over a live writer for either lane.
    $live = @(Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
        Where-Object { $_.CommandLine -match 'probe_structural_target_noise_refit|probe_buffered_cv|analyse_structural_moran_correlogram|probe_r1_ablation' })
    if ($live.Count -gt 0) { throw 'A Phase 6 lane writer is already running.' }

    Invoke-Lane 'structural' 'results/phase6_structural_controller.ps1'
    Invoke-Lane 'buffered' 'results/phase6_buffered_controller.ps1'
    Write-Output "$(Get-Date -Format o) ROOT INTEGRATION LANES COMPLETE"
} catch {
    Write-Output "$(Get-Date -Format o) FAILED: $_"
    exit 1
}

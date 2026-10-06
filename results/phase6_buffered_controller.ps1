# Finite Phase 6 sequence. Launch only after the scoped harness review passes.
# Python owns provenance and checkpoint validation; this wrapper never repairs
# or rewrites a partial input pair to bypass those checks.
# NOTE (2026-09-11, Claude Opus 5, Task 6 finding P2-10(d)): --rf-jobs 8 is hard-coded
# for this 16-core machine. The runner's parallel-equivalence check bounds the numerical
# effect of the thread count (documented tolerance in the runner), so a different value
# is a portability choice, not a correctness one. Left as-is on purpose.
$ErrorActionPreference = 'Stop'
$bufferedRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$bufferedPython = Join-Path $env:USERPROFILE 'miniconda3/envs/influence/python.exe'
Set-Location -LiteralPath $bufferedRoot

function Test-CompletePair([string]$First, [string]$Second) {
    $firstPresent = Test-Path -LiteralPath $First
    $secondPresent = Test-Path -LiteralPath $Second
    if ($firstPresent -ne $secondPresent) {
        throw "Partial artifact pair: $First / $Second. Inspect before resuming."
    }
    return $firstPresent
}

try {
    # Reject a visible competing invocation before any artifact is produced.
    # The operator must also inspect live processes before starting this wrapper.
    $competingRuns = @(Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
        Where-Object { $_.CommandLine -match '(?:^|[ /\\"])(?:probe_buffered_cv|analyse_structural_moran_correlogram)\.py(?:[" ]|$)' })
    if ($competingRuns.Count -gt 0) {
        throw 'An existing buffered/Moran Python invocation is still running.'
    }

    $moranReady = Test-CompletePair 'results/phase6_structural_moran_correlogram.csv' 'results/phase6_structural_moran_correlogram_provenance.json'
    if (-not $moranReady) {
        Write-Output "$(Get-Date -Format o) Structural Moran prerequisite"
        & $bufferedPython analyse_structural_moran_correlogram.py --perms 199 --batch 512
        if ($LASTEXITCODE -ne 0) { throw "Moran failed with exit $LASTEXITCODE" }
    }

    $preflightReady = Test-CompletePair 'results/phase6_buffered_cv_preflight.json' 'results/phase6_buffered_cv_provenance.json'
    if (-not $preflightReady) {
        Write-Output "$(Get-Date -Format o) Zero-fit buffered preflight"
        & $bufferedPython probe_buffered_cv.py --preflight-only
        if ($LASTEXITCODE -ne 0) { throw "Preflight failed with exit $LASTEXITCODE" }
    }

    # Both benchmark and execution validate the saved preflight against current
    # inputs. Presence here is only sequencing, never proof of compatibility.
    if (-not (Test-Path -LiteralPath 'results/phase6_buffered_cv_pilot.json')) {
        Write-Output "$(Get-Date -Format o) Worker timing and memory pilot"
        & $bufferedPython probe_buffered_cv.py --benchmark-only
        if ($LASTEXITCODE -ne 0) { throw "Benchmark failed with exit $LASTEXITCODE" }
    }
    $bufferedPilot = Get-Content -LiteralPath 'results/phase6_buffered_cv_pilot.json' -Raw | ConvertFrom-Json
    $bufferedJobs = $bufferedPilot.selected_rf_jobs
    if ($bufferedJobs -notin @(1, 4, 8)) { throw 'Invalid pilot-selected worker count.' }

    Write-Output "$(Get-Date -Format o) Controlled one-fit stop with rf_jobs=$bufferedJobs"
    & $bufferedPython probe_buffered_cv.py --rf-jobs $bufferedJobs --stop-after-canonical-fits 1
    if ($LASTEXITCODE -ne 0) { throw "Controlled stop failed with exit $LASTEXITCODE" }
    Write-Output "$(Get-Date -Format o) Resume complete buffered corpus"
    & $bufferedPython probe_buffered_cv.py --rf-jobs $bufferedJobs
    if ($LASTEXITCODE -ne 0) { throw "Buffered sweep failed with exit $LASTEXITCODE" }

    Write-Output "$(Get-Date -Format o) Validate and analyse complete buffered results"
    & $bufferedPython analyse_buffered_cv.py
    if ($LASTEXITCODE -ne 0) { throw "Buffered analysis failed with exit $LASTEXITCODE" }
    Write-Output "$(Get-Date -Format o) Buffered follow-up complete"
} catch {
    Write-Error $_
    exit 1
}

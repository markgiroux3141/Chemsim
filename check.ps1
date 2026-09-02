<#
.SYNOPSIS
    The check to run after every change. Fast by default.

.DESCRIPTION
    Four steps: lint, the documentation caps, the catalog's structural
    validation, and a smoke subset of the test suite.

    The smoke subset is a hand-named list because the suite has no markers yet.
    T0.4 in BACKLOG.md replaces it with `pytest -m "not slow"`; when that lands,
    delete $SmokeTests and use the marker.

    The full suite is about 30 minutes on the user's own machine. It is not run
    here, and it is not run without asking.

.PARAMETER Full
    Also run the two report generators with --check, so a stale committed report
    fails. Adds about two minutes.
#>
param([switch]$Full)

$ErrorActionPreference = 'Continue'
$failures = @()

$SmokeTests = @(
    'tests/test_conservation.py',
    'tests/test_ui.py',
    'tests/test_threads.py'
)

function Step {
    param([string]$Name, [scriptblock]$Body)
    Write-Host ''
    Write-Host "=== $Name" -ForegroundColor Cyan
    & $Body
    if ($LASTEXITCODE -ne 0) {
        $script:failures += $Name
        Write-Host "--- $Name FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    }
}

Step 'ruff' { ruff check src tests tools validation examples }
Step 'docs' { python tools/check_docs.py }
Step 'catalog' { python tools/catalog.py }
Step 'smoke tests' { python -m pytest -q @SmokeTests }

if ($Full) {
    # These regenerate committed reports; --check makes a stale one fail rather
    # than rewriting it. Both flags are T0.5 in BACKLOG.md and may not exist yet.
    Step 'coverage report' { python validation/catalog_coverage.py --check }
    Step 'playable report' { python tools/build_playable.py --check }
}

Write-Host ''
if ($failures.Count -gt 0) {
    Write-Host ("FAILED: " + ($failures -join ', ')) -ForegroundColor Red
    exit 1
}
Write-Host 'all checks passed' -ForegroundColor Green
exit 0

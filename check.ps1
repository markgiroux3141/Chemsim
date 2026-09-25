<#
.SYNOPSIS
    The check to run after every change. Fast by default.

.DESCRIPTION
    Nine steps: lint, the documentation caps, the catalog's structural
    validation, the extracted half of the template table against the catalog
    steps it was written from, the whole table against the constructors it
    copies, each template row against the catalog step it claims, the
    held-out reaction benchmark, the classification of the templates the
    shelf cannot reach, and a smoke subset of the test suite.

    The smoke subset is a hand-named list because the suite has no markers yet.
    T0.4 in BACKLOG.md replaces it with `pytest -m "not slow"`; when that lands,
    delete $SmokeTests and use the marker.

    The full suite is about 30 minutes on the user's own machine. It is not run
    here: it runs in GitHub Actions on every push (.github/workflows/ci.yml),
    and `python tools/ci_status.py` reads the result. What IS printed here is
    the ledger, `data/checks/cadence.psv`, which says what is owed and where
    the fix goes if one comes back red.

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
    'tests/test_threads.py',
    # Under a second between them, and both guard a committed artefact against
    # the code that writes it rather than against a hand-typed number.
    'tests/test_reachable.py',
    'tests/test_cadence.py',
    # One second, and it guards the network builder's newest claim: a template
    # run backwards finds species and never a rate.
    'tests/test_reverse_discovery.py',
    # Three seconds. The tool step below pins the artefact; these pin what the
    # artefact MEANS -- no row dies in its own rewrite, the five demonstrated
    # chains still make what their step declares, and the medium pool is three
    # species that report themselves.
    'tests/test_template_table.py'
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
# T2, ~2 s. `literal.psv` is generated from the catalog steps, so a corpus edit
# that changes what an extracted row rewrites fails here instead of leaving the
# table describing a step that no longer exists. `needs_review.psv` is checked
# with it, because the refusals are the other half of the same measurement.
Step 'extracted templates' { python tools/extract_templates.py --check }
# Fast (~5 s) and it guards a transcription: --check refuses a stale
# template_data.py AND any row that has drifted from the constructor it copies.
Step 'templates' { python tools/build_templates.py --check }
# T1b, ~2 s. The column set and the construction sites say nothing about
# chemistry: this fires every row over the catalog steps its class claims and
# compares the product set. --check refuses a stale artefact, so a SMARTS edit
# that changes which species a row makes fails here rather than drifting.
Step 'template products' { python tools/check_template_products.py --check }
# ~3 s. The coverage metric that rewards generality: every row fired at
# textbook substrates it was never written from. --check refuses a stale
# scores.psv and any case that does not parse, balance or stay held out.
Step 'benchmark' { python tools/benchmark.py --check }
# T6's classifier over T4's silent list. ~23 s, and it re-derives rather than
# re-reading: a template that stops being silent, or a shelf row that changes
# what the closure can make, fails here instead of drifting in a committed file.
# Most of the 23 s is T9's second pool tier -- each of the 13 natural rows too
# big for the closure, expanded one generation against it, because the closure
# alone said the shelf could not make an aromatic aldehyde it makes in one step.
Step 'silent templates' { python tools/classify_silent.py --check }
Step 'smoke tests' { python -m pytest -q @SmokeTests }

if ($Full) {
    # These regenerate committed reports; --check makes a stale one fail rather
    # than rewriting it. The playable report is regenerated FIRST when both are
    # stale: the coverage report quotes its footer, so a fresh PLAYABLE.md is an
    # input to a fresh COVERAGE_REPORT.md.
    Step 'playable report' { python tools/build_playable.py --check }
    Step 'coverage report' { python validation/catalog_coverage.py --check }
}

# Not a step: it runs nothing and it cannot fail the check. It is the standing
# answer to "how long has it been since the suite?", which used to be nobody's
# job. `tools/cadence.py` derives what it can from the artefacts and stamps only
# what leaves no trace.
Write-Host ''
Write-Host '=== expensive checks' -ForegroundColor Cyan
python tools/cadence.py --due
$LASTEXITCODE = 0

Write-Host ''
if ($failures.Count -gt 0) {
    Write-Host ("FAILED: " + ($failures -join ', ')) -ForegroundColor Red
    # In Actions, name the failing steps as an annotation: the public API serves
    # annotations without a token, which is how tools/ci_status.py reads them.
    if ($env:GITHUB_ACTIONS) { Write-Host ("::error title=check.ps1::FAILED: " + ($failures -join ', ')) }
    exit 1
}
Write-Host 'all checks passed' -ForegroundColor Green
exit 0

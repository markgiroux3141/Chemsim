<#
.SYNOPSIS
    Run /session over and over, each in its own fresh context, until a goal is
    met or a stop condition fires.

.DESCRIPTION
    The unit of work is one `/session` invocation: take task 1, do it to its
    done-when, close out through `handoff`, push main. This script does nothing
    clever with that unit. It starts a NEW `claude -p` process each time, so
    every iteration begins with an empty context and reads its state back out of
    the repo -- CLAUDE.md, NEXT.md, BACKLOG.md, the git log. The handoff is the
    only channel between iterations, which is what it was designed to be.

    The loop stops on the first of:
      * tools/loop/STOP exists. A session writes it when it meets the goal, runs
        out of work it may do unattended, or hits the same failure twice. It is
        also the operator's brake: create it mid-run and the loop halts after
        the session now running finishes.
      * -MaxSessions reached, or -MaxHours elapsed.
      * claude exited non-zero, or its result event reported an error.
      * two sessions in a row left HEAD where they found it.
      * a session left the tree dirty, or left HEAD not level with origin/main.
        Either means `handoff` did not complete, and stacking another session on
        a broken close-out is how a loop destroys a week of work.

.PARAMETER MaxSessions
    Hard cap on iterations. Default 8.

.PARAMETER MaxHours
    Wall-clock deadline. The loop will not START a session past it. 0 = none.

.PARAMETER BudgetPerSession
    Passed to `claude --max-budget-usd`, so a runaway session dies on its own.
    0 = unset.

.PARAMETER PermissionMode
    `acceptEdits` (default) pairs with an allowlist in .claude/settings.json:
    edits are automatic, listed commands are automatic, anything else is DENIED
    rather than prompted, because nobody is watching. Safe, occasionally lossy.
    `bypassPermissions` runs with no permission checks at all. That is what a
    genuinely unattended overnight run wants, and it means a model deciding on
    its own to run any command in this repo. Choose deliberately.

.PARAMETER Goal
    One line of steering for this run, overriding tools/loop/GOAL.md. Per the
    session skill's step 0 it outranks NEXT.md's ordering.

.PARAMETER ShowPrompt
    Print the prompt that would be sent, and exit.

.EXAMPLE
    .\tools\loop\run-loop.ps1 -MaxSessions 3

.EXAMPLE
    .\tools\loop\run-loop.ps1 -MaxHours 8 -MaxSessions 12 -PermissionMode bypassPermissions
#>
param(
    [int]$MaxSessions = 8,
    [double]$MaxHours = 0,
    [double]$BudgetPerSession = 0,
    [string]$Model = '',
    [ValidateSet('acceptEdits', 'bypassPermissions', 'dontAsk', 'auto')]
    [string]$PermissionMode = 'acceptEdits',
    [string]$Goal = '',
    [switch]$ShowPrompt
)

$ErrorActionPreference = 'Continue'

$LoopDir  = $PSScriptRoot
$Root     = (Resolve-Path (Join-Path $LoopDir '..\..')).Path
$StateDir = Join-Path $LoopDir 'state'
$StopFile = Join-Path $LoopDir 'STOP'
$GoalFile = Join-Path $LoopDir 'GOAL.md'
$Ledger   = Join-Path $StateDir 'ledger.md'

Set-Location $Root
if (-not (Test-Path $StateDir)) { New-Item -ItemType Directory -Force $StateDir | Out-Null }

function Get-Head { (& git rev-parse HEAD 2>$null | Out-String).Trim() }
function Get-OriginHead { (& git rev-parse origin/main 2>$null | Out-String).Trim() }
function Test-Dirty { [bool]((& git status --porcelain 2>$null | Out-String).Trim()) }

function Format-Snip {
    param([string]$Text, [int]$Width)
    if ([string]::IsNullOrWhiteSpace($Text)) { return '' }
    $s = ($Text -replace '\s+', ' ').Trim()
    if ($s.Length -le $Width) { return $s }
    return $s.Substring(0, $Width) + '...'
}

# Prints one stream-json event; returns the final result event, or $null.
function Show-Event {
    param([string]$Line)
    if ([string]::IsNullOrWhiteSpace($Line)) { return $null }
    try { $e = $Line | ConvertFrom-Json }
    catch {
        Write-Host ('  ! ' + (Format-Snip $Line 150)) -ForegroundColor DarkYellow
        return $null
    }
    if ($e.type -eq 'assistant') {
        foreach ($b in $e.message.content) {
            if ($b.type -eq 'text') {
                $t = Format-Snip $b.text 150
                if ($t) { Write-Host ('  ' + $t) -ForegroundColor Gray }
            }
            elseif ($b.type -eq 'tool_use') {
                $arg = ''
                foreach ($k in 'command', 'file_path', 'pattern', 'skill', 'description') {
                    $v = $b.input.$k
                    if ($v) { $arg = [string]$v; break }
                }
                Write-Host ('  > {0}  {1}' -f $b.name, (Format-Snip $arg 100)) -ForegroundColor DarkCyan
            }
        }
    }
    elseif ($e.type -eq 'result') { return $e }
    return $null
}

# --- the prompt every session gets -----------------------------------------

if (-not $Goal -and (Test-Path $GoalFile)) {
    $parts = (Get-Content $GoalFile -Raw) -split '(?m)^##\s+Goal\s*$'
    $Goal = ($parts[-1] -replace '(?m)^#.*$', '').Trim()
}

function New-Prompt {
    param([int]$Index, [int]$Total)
    $lines = @(
        '/session',
        '',
        "You are session $Index of up to $Total in an unattended loop. Nobody is",
        'watching and there is nobody to answer a question. Read',
        'tools/loop/PROTOCOL.md before you choose the task: it says what an',
        'unattended session may and may not do, and how to stop the loop.',
        ''
    )
    if ($Goal) {
        $lines += 'The standing goal for this run, which outranks the ordering in NEXT.md:'
        $lines += ''
        $lines += $Goal
    }
    else {
        $lines += 'There is no standing goal. Task 1 in NEXT.md is the task.'
    }
    return ($lines -join "`n")
}

if ($ShowPrompt) { New-Prompt 1 $MaxSessions; exit 0 }

# --- preflight -------------------------------------------------------------

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host 'claude is not on PATH.' -ForegroundColor Red
    exit 1
}
if (Test-Path $StopFile) {
    Write-Host 'A STOP file from an earlier run is present:' -ForegroundColor Yellow
    Get-Content $StopFile | ForEach-Object { Write-Host "  $_" }
    Write-Host 'Delete tools/loop/STOP to start a new run.' -ForegroundColor Yellow
    exit 1
}
if (Test-Dirty) {
    Write-Host 'The tree is dirty. A loop starts from a clean tree, so that every' -ForegroundColor Red
    Write-Host 'change it makes is one of its own commits.' -ForegroundColor Red
    exit 1
}

$deadline = $null
if ($MaxHours -gt 0) { $deadline = (Get-Date).AddHours($MaxHours) }

Write-Host ''
Write-Host "loop: up to $MaxSessions sessions, permission mode $PermissionMode" -ForegroundColor Cyan
if ($deadline) { Write-Host ('      deadline ' + $deadline.ToString('HH:mm')) -ForegroundColor Cyan }
if ($Goal) { Write-Host ('      goal: ' + (Format-Snip $Goal 100)) -ForegroundColor Cyan }

# --- the loop --------------------------------------------------------------

$noProgress = 0
$stopReason = "reached the $MaxSessions session cap"
$landed = @()

for ($i = 1; $i -le $MaxSessions; $i++) {

    if ($deadline -and (Get-Date) -ge $deadline) { $stopReason = 'wall-clock deadline'; break }

    $stamp   = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $raw     = Join-Path $StateDir ('{0:d3}.jsonl' -f $i)
    $before  = Get-Head
    $started = Get-Date

    Write-Host ''
    Write-Host ("=== session $i/$MaxSessions  $stamp  @ " + $before.Substring(0, 7)) -ForegroundColor Cyan

    $claudeArgs = @(
        '-p', (New-Prompt $i $MaxSessions),
        '--output-format', 'stream-json',
        '--verbose',
        '--permission-mode', $PermissionMode
    )
    if ($Model) { $claudeArgs += @('--model', $Model) }
    if ($BudgetPerSession -gt 0) { $claudeArgs += @('--max-budget-usd', "$BudgetPerSession") }

    $script:resultEvent = $null
    & claude @claudeArgs 2>&1 | ForEach-Object {
        $line = [string]$_
        Add-Content -Path $raw -Value $line -Encoding utf8
        $r = Show-Event $line
        if ($r) { $script:resultEvent = $r }
    }
    $exit = $LASTEXITCODE
    $mins = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)

    $after = Get-Head
    $cost  = 0.0
    $turns = 0
    if ($script:resultEvent) {
        if ($script:resultEvent.total_cost_usd) { $cost = [double]$script:resultEvent.total_cost_usd }
        if ($script:resultEvent.num_turns) { $turns = [int]$script:resultEvent.num_turns }
    }
    $cost = [math]::Round($cost, 2)

    $moved   = ($after -ne $before)
    $subject = ''
    if ($moved) {
        $subject = (& git log -1 --format=%s | Out-String).Trim()
        $landed += $subject
    }

    $cell = 'nothing landed'
    if ($moved) { $cell = $after.Substring(0, 7) + ' ' + $subject }
    Add-Content -Path $Ledger -Encoding utf8 -Value "| $stamp | $i | $mins min | $turns turns | $cost | $cell |"

    Write-Host ''
    Write-Host "--- session ${i}: $mins min, $turns turns, USD $cost" -ForegroundColor DarkGray
    if ($moved) { Write-Host ('    landed: ' + $subject) -ForegroundColor Green }
    else { Write-Host '    nothing landed' -ForegroundColor Yellow }

    # stop conditions, in the order that matters
    if (Test-Path $StopFile) {
        $stopReason = 'a session wrote STOP: ' + ((Get-Content $StopFile -Raw).Trim())
        break
    }
    if ($exit -ne 0) { $stopReason = "claude exited $exit"; break }
    if ($script:resultEvent -and $script:resultEvent.is_error) {
        $stopReason = 'the session reported an error result'
        break
    }
    if (Test-Dirty) {
        $stopReason = 'the session left the tree dirty; handoff did not complete'
        break
    }
    $origin = Get-OriginHead
    if ($origin -and $after -ne $origin) {
        $stopReason = 'HEAD is not level with origin/main; the push did not land'
        break
    }
    if (-not $moved) {
        $noProgress++
        if ($noProgress -ge 2) { $stopReason = 'two sessions in a row landed nothing'; break }
    }
    else { $noProgress = 0 }
}

Write-Host ''
Write-Host ('=== loop stopped: ' + $stopReason) -ForegroundColor Cyan
Write-Host "    $($landed.Count) commit(s) landed" -ForegroundColor Cyan
foreach ($s in $landed) { Write-Host ('      ' + $s) -ForegroundColor DarkGray }
Write-Host '    transcripts in tools/loop/state/, ledger in state/ledger.md' -ForegroundColor DarkGray
Write-Host ''

---
name: session
description: Run one complete chemsim work session end to end — take task 1 from NEXT.md (or the user's steering), do it to its done-when, then close out through the handoff skill and push main. Use when the user invokes /session, says "do the next piece of work", or wants the box advanced without driving it. Not for closing out work already done; that is /handoff on its own.
user-invocable: true
---

# Work session

One invocation is one unit of work: pick the task, do it, record it, push it.
The user is not a chemist and will not be watching. Nothing in this skill
relaxes the ten rules in `CLAUDE.md` or the caps that `handoff` enforces.

## Step 0 — Steering

Anything the user typed after the invocation outranks `NEXT.md`'s ordering.
If it names a task, that is the task. If it names a constraint ("no engine
work", "only docs"), filter the list by it and take the first survivor. If it
is empty, task 1 in `NEXT.md` is the task, subject to Step 0b.

A request to "increase coverage", "get more routes", "add breadth" or anything
else aimed at the 173 is NOT a free choice of task. It resolves to the standing
priority below, because that priority IS the measured answer to it.

## Step 0b — The standing priority: coverage of chemistry, measured by the benchmark

Decided 2026-09-24 in a retro, and not relitigated inside a session.

**Two scoreboards, two questions.** `data/benchmark/` (scored by
`tools/benchmark.py`) fires every template row at held-out textbook substrates
and is the measure of how much chemistry the engine covers. Its headline is
`classes_general`: classes whose `family` rows pass every case. The 173-route
catalog measures the game's progression and its ceiling is ~66 runnable
(`docs/design/route-coverage-ceiling.md`); it is not the coverage target.

When the choice is yours, rank the open work this way:

1. **Work that moves the benchmark** -- a family row that makes a class general,
   an extractor change that writes rows for a whole refusal category, a priced
   species that turns `unpriced` into `runs`. A family row must pass its class's
   held-out cases; a class with none gets cases first (they are data rows in
   `data/benchmark/reactions.psv`, checked for balance and held-out-ness).
2. **Work that unblocks a named route or template**, where the item says which.
3. **A measurement that could cancel expensive work**, as before.
4. **Scoreboard or instrument work** -- at most one session in four, unless a
   check is red. Look at the last three CHANGELOG entries: if two of them were
   instrument work and nothing is red, the session moves a content number.
5. **Queue-grinding curation** -- one sourced pKa row at a time -- last.

If `NEXT.md`'s task 1 ranks below an open item from tier 1, take the tier-1 item
and say so in one line of the report. That is the one case where you may
reorder `NEXT.md` without being told to.

## Step 1 — Take the task

Read `CLAUDE.md` and `NEXT.md`. Nothing else yet. Then `python
tools/ci_status.py`: CI runs the full suite on every push and the tolerance
audit and shelf sweep when a push could move them. A red job on HEAD outranks
task 1 -- it is the previous session's defect, and its failing test ids are
printed. `python tools/ci_status.py --record` stamps the ledger from a finished
run. Take the chosen task and read only the files it names; grep for the rest.

Commit to one task, sized as an arc: finish the whole of what it names, not a
first slice of it. Do not take a second task afterwards; it belongs to the
next invocation with a fresh context.

Then run `python tools/cadence.py`. A due row CI covers is answered by CI, not
by running it here; a due row under two minutes is run now; running a long one
on the user's machine is still their call.

## Step 2 — Do it

Work to the task's done-when, not to your own sense of finished. After every
change, `./check.ps1` — its last section prints what the ledger says is owed.
Regenerate any generated file you touched and run its `--check`. A number you
write down comes from a command you ran today.

If you ran a slow check, record it (`python tools/cadence.py --record <check>
--result pass|fail --note "..."`) in the same breath, pass or fail. A result
that is not recorded did not happen as far as the next session can tell.

A change that moves template rows re-runs `tools/benchmark.py` and quotes its
headline beside the catalog's, so every session's effect on coverage of
chemistry is in its CHANGELOG entry.

When a task turns out to be wrong as written — the measurement it asked for
cannot be made, the file it names has moved, its premise is false — do not
quietly substitute a different task. Do the part that stands, record the
finding as the result, and let `handoff` rewrite the backlog item as the
decision with its reasoning.

If you are stuck for real, stop at a clean point: no half-edited generated
file, `./check.ps1` green. An honest "stopped here, because" in `NEXT.md` is
a valid outcome. A task silently narrowed to look finished is not.

## Step 3 — Close out

Invoke the `handoff` skill (`.claude/skills/handoff/`). It owns the numbers,
`BACKLOG.md`, `CHANGELOG.md`, the whole-file rewrite of `NEXT.md`, memory, the
caps, the commit and the push. Do not reproduce its steps here and do not skip
it because the task was small. Its `NEXT.md` must leave task 1 startable by a
successor who reads nothing else.

## Step 4 — Confirm the push

`handoff` pushes; you confirm it. `git status -sb` must show the branch level
with `origin/main` and a clean tree. If the push was rejected because the
remote moved, `git pull --rebase origin main`, rerun `./check.ps1`, and push
again. Never force, never amend.

## Step 5 — Report

`handoff`'s four paragraphs, plus one line at the top naming the task taken and
whether its done-when passed.

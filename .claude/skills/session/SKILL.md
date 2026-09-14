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

## Step 0b — The standing priority: change the rate, do not grind the queue

Decided 2026-09-13 from `docs/design/route-coverage-ceiling.md`, which carries
the derivation and the script. Do not re-derive it and do not relitigate it
inside a session; if a measurement contradicts it, that is a finding for the
report and the backlog.

**173 is not reachable and is not the target.** 7 routes name a species with no
molecular graph, 14 reaction classes are credited to integrator terms where no
SMARTS can exist, and the rest of the gap is steps that will not balance. If
every extractable step in the corpus became a template the ceiling is **110
template-ready and about 66 runnable**. The box stands at 46 / 47. The gap is
roughly twenty routes, it is bounded, and it is worth finishing.

So when the choice is yours, rank the open work this way:

1. **Work that changes the rate** at which content arrives — T2's extractor
   above all, then T3. One extractor writes ~132 classes mechanically; the
   historical hand-written rate is three to five a session, which is thirty
   sessions for the same content.
2. **Work that unblocks a named route or template**, where the item says which.
3. **A measurement that could cancel expensive work**, as before.
4. **Queue-grinding curation** — the per-row pKa work of T23 and T26, one
   sourced paper at a time — comes LAST while T2 is open. It is not worthless:
   T18's rule took stearic acid from 4 reactions to 21. It is mis-scored, and
   it must not be task 1. T23 and T27 each spent a whole session and wrote
   "coverage does not move" as their own result, with 444 ions still queued at
   two to four a session.

If `NEXT.md`'s task 1 is queue-grinding curation while a rate-changing item is
open, take the rate-changing item instead and say so in one line of the report.
That is the one case where you may reorder `NEXT.md` without being told to.

## Step 1 — Take the task

Read `CLAUDE.md` and `NEXT.md`. Nothing else yet. Take the chosen task and
read only the files it names; grep for anything else. If task 1's done-when
requires the full suite (~30 min) or `validation/tolerance_audit.py` (~10 min),
you may not run them unasked: leave that task where it is, take the next one
that does not need them, and say why in the report.

Commit to one task. Do not take a second one afterwards, however short it
looks; the user asked for a predictable unit, and the second task belongs to
the next invocation with a fresh context.

Then run `python tools/cadence.py` and read what it says before you start. It
names the expensive checks that are owed, how long it has been in commits, and
where the fix goes if one comes back red. A due row under two minutes is run
now; a due row over ten is the user's call, and the answer to "is this task
safe without it" belongs in the report either way.

## Step 2 — Do it

Work to the task's done-when, not to your own sense of finished. After every
change, `./check.ps1` — its last section prints what the ledger says is owed.
Regenerate any generated file you touched and run its `--check`. A number you
write down comes from a command you ran today.

If you ran a slow check, record it (`python tools/cadence.py --record <check>
--result pass|fail --note "..."`) in the same breath, pass or fail. A result
that is not recorded did not happen as far as the next session can tell.

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

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
is empty, task 1 in `NEXT.md` is the task.

## Step 1 — Take the task

Read `CLAUDE.md` and `NEXT.md`. Nothing else yet. Take the chosen task and
read only the files it names; grep for anything else. If task 1's done-when
requires the full suite (~30 min) or `validation/tolerance_audit.py` (~10 min),
you may not run them unasked: leave that task where it is, take the next one
that does not need them, and say why in the report.

Commit to one task. Do not take a second one afterwards, however short it
looks; the user asked for a predictable unit, and the second task belongs to
the next invocation with a fresh context.

## Step 2 — Do it

Work to the task's done-when, not to your own sense of finished. After every
change, `./check.ps1`. Regenerate any generated file you touched and run its
`--check`. A number you write down comes from a command you ran today.

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

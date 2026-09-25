# Unattended loop protocol

`tools/loop/run-loop.ps1` starts a new `claude -p "/session"` process per
iteration. You are one of those. Nothing here relaxes the ten rules in
`CLAUDE.md` or the caps that `handoff` enforces. It says only what changes when
nobody is watching.

## What is different

1. **Your context does not survive.** The next iteration is a new process that
   has read `CLAUDE.md` and `NEXT.md` and nothing else. Anything you learned
   that is worth keeping reaches `NEXT.md`, `CHANGELOG.md`, `BACKLOG.md` or
   memory before you exit, or it is gone.
2. **There is nobody to ask.** A question you would have asked goes under
   `NEXT.md`'s open questions, and you take work that does not depend on the
   answer. Stalling on a question is the one failure mode that wastes a whole
   iteration.
3. **The slow checks are CI's.** The full suite, the tolerance audit and the
   shelf sweep run in GitHub Actions on the push your `handoff` makes; the next
   iteration reads them with `python tools/ci_status.py` before taking a task,
   and a red job there is its task. Never run them locally unattended -- the
   machine is the user's.
4. **Still exactly one task.** The loop is what makes the work continue, not
   you. A second task taken here is a task done with a full context instead of
   an empty one, which is the thing the loop exists to avoid.

## The goal

The runner passes the `## Goal` section of `tools/loop/GOAL.md` into your
prompt. Per the session skill's step 0 it outranks `NEXT.md`'s ordering: take
the first task that advances it. When it is empty, task 1 is the task.

## Leave the tree the way the runner expects

The runner reads the repo, not your report. After you exit it checks that the
tree is clean and `HEAD` is level with `origin/main`, and stops the loop if
either fails, because a second session stacked on a broken close-out is how a
loop destroys a week of work. It also stops after two iterations in a row that
leave `HEAD` where they found it.

So finish through `handoff`, or stop at a clean point and say so in `NEXT.md`.
A half-regenerated report committed to `main` is worse than an honest stop.

## Stopping the loop

Write one line of reason to `tools/loop/STOP` and the loop halts once you exit.
Do it when any of these is true:

- The goal is met. Name the command that shows it.
- Every remaining task needs the user's decision, or needs a command that may
  not run unattended.
- You hit the same failure a second time. Two identical failures across two
  fresh contexts is not bad luck, and a third costs the same and learns
  nothing new.
- The repo is in a state you would not hand to a colleague.

Write `STOP` before `handoff` runs, so the reason is on disk even if the push
fails. It is not committed; it is a signal to the runner, and the durable record
of why is the `CHANGELOG` entry and `NEXT.md`.

## Never

- Never `git push --force`, never amend a commit, never raise a cap in
  `tools/check_docs.py` so that text fits.
- Never start the runner from inside a session.
- Never hand-edit a generated file. `--check` catches it, and the loop then
  stops on a dirty tree with the work half done.

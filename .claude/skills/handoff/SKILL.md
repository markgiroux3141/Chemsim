---
name: handoff
description: Close out a chemsim session — verify the numbers, prune BACKLOG.md, write the CHANGELOG entry, rewrite NEXT.md whole, save any transferable lesson to memory, hold the doc caps, commit and push main. Use when the user says they are wrapping up, invokes /handoff, or when context is running short mid-task. Not for starting or running a session; that is the session skill.
user-invocable: true
---

# Session handoff

The user does not drive the chemistry — you do. So the handoff is not a status
report to them, it is a **work order to your successor**, who will have none of
your context and should need nothing but `CLAUDE.md` and `NEXT.md` to start.

Write it for a model that knows this repo's rules and nothing about today.

If the user typed anything after the invocation, that is their steering: fold it
into the backlog and into `NEXT.md`'s next-task choice before you decide
anything yourself. Their input outranks your judgement about priority; it does
not relax the caps or the honesty rules below.

---

## Step 1 — Get the numbers from commands, never from prose

Nothing goes into a doc that you cannot regenerate. Run what the session
touched; re-use a number already measured *this* session rather than re-running.

| number | command |
|---|---|
| tests | `python -m pytest --co -q` |
| templates | `grep -c 'ReactionTemplate(' src/chemsim/reactions/*.py src/chemsim/properties/electrolyte.py` |
| catalog shape | `python tools/catalog.py` |
| readiness columns | `data/catalog/COVERAGE_REPORT.md` (regenerate with `python validation/catalog_coverage.py`) |
| playable routes | `data/catalog/PLAYABLE.md` (regenerate with `python tools/build_playable.py`, ~50 s) |
| save format | `src/chemsim/engine/world.py` `SAVE_VERSION` |

If a number did not move, say so and quote it anyway. A `NEXT.md` whose state
table is stale is worse than no table.

## Step 2 — Run the checks and say what happened

`./check.ps1` always. Regenerate any generated file the session touched and
commit input and output together — `*_data.py`, `COVERAGE_REPORT.md`,
`PLAYABLE.md`, `ROUTE_INDEX.md` are never hand-edited.

**Ask before** the full suite (~30 min on the user's own machine) or
`validation/tolerance_audit.py` (~10 min). The audit is owed when a trajectory
could have moved — anything in `numerics/`, `vessel/` or `network/`.

Report failures plainly, in the CHANGELOG entry as well as to the user. A
handoff that hides a red check hands over a trap.

## Step 3 — `BACKLOG.md`: delete what is done, record what was decided

- A finished item is **deleted**. No tick, no post-mortem paragraph. Its record
  is the CHANGELOG entry and the commit.
- Every item has a **done-when** that a successor can check without asking.
- When the session **decided** something that had been open, keep the item and
  rewrite it as the decision **with its reasoning**, so nobody relitigates it.
  This is the single highest-value thing in the file.
- New work discovered mid-session goes in at the right tier, not at the top.
- Measurement before build: if an item rests on an unverified estimate, put a
  small measuring item in front of it and make the big item depend on it.
- Cap 300 lines. If it does not fit, the file is carrying done work — cut that,
  do not raise the cap.

## Step 4 — `CHANGELOG.md`: one entry, twelve body lines at most

Newest first, under the existing header. What changed, which numbers moved
(with the command), what is next in one clause. No narrative, no lessons — a
lesson is a memory note or a `docs/design/` paragraph.

## Step 5 — `NEXT.md`: rewrite it whole

**Overwrite, never edit.** Anything still true gets re-typed; anything not
re-typed is gone. That is the pruning mechanism — if you edit in place, this
file becomes the next monolith. Cap 120 lines.

```
# NEXT — overwritten YYYY-MM-DD      (today's date; check_docs compares it to the last commit)

## State of the box          every number with the command that produced it
## Last session, in five lines
## Do this now               at most THREE tasks, each with a done-when, ordered
## Decisions already taken — do not reopen
## Open questions for the user
## Do not                    three or four lines
```

**Choosing the three tasks**, in this order of preference:

1. A measurement that could cancel expensive work beats the expensive work.
2. Finish the tier that is open. Do not start engine work with a Tier 0 item live.
3. Prefer the item that unblocks others over the item that is most interesting.
4. Something the user must decide is not a task — it goes under open questions,
   and you queue work that does not depend on the answer.

Task one should be startable with no reading beyond the files it names.

## Step 6 — Memory: transferable lessons only

Write a note only for something that would change how the *next* session works
and is not derivable from the code, the commit or the backlog: a trap that bit,
a constraint discovered, a measurement that overturned an assumption. One fact
per file, with the `why` and the `how to apply`, a line in `MEMORY.md`, and
`[[links]]` to the related notes.

Task state is `NEXT.md`. History is `CHANGELOG.md`. Numbers are generated files.
None of those belong in memory.

Also **correct any memory note this session falsified** — a note naming a plan
of record, a live arc or a file that moved is now lying to every future session.

## Step 7 — Hold the caps

`python tools/check_docs.py` must pass. It enforces absolute caps on
`CLAUDE.md` (150), `NEXT.md` (120), `BACKLOG.md` (300) and a CHANGELOG entry
(12), and it **ratchets** the existing debt — README lines, warning-glyph counts
per tree — failing when a count moves in *either* direction.

- Over a cap: cut content or move it (`docs/design/` for rationale,
  `docs/manual/chapters/` for physics). Never raise a cap to fit the text.
- Debt paid down: `python tools/check_docs.py --fix-budgets`, and say in the
  CHANGELOG what moved.
- Debt grown: that is the check working. Undo the growth.

Never append to anything in `docs/history/`. It is frozen.

## Step 8 — Commit and push

Invoking this skill authorises the commit and the push. Stage everything the
session touched, including generated outputs and the doc updates. One commit
unless the session did genuinely separate things.

Message: a subject line that states what changed and the number that moved, then
a short body with the same facts as the CHANGELOG entry. End with the
`Co-Authored-By:` trailer. Do not amend an earlier commit.

Then `git push origin main`. Fast-forward only: if the remote has moved,
`git pull --rebase origin main`, rerun `./check.ps1`, and push again. Never
`--force`. If the session did something risky enough that you would not want
it on `main` unreviewed, push a branch instead and say so in the report; that
is the one case where `main` is not the destination.

## Step 9 — Report

Four short paragraphs at most: what landed, what the checks said (including
failures), what task one is for the next session, and anything that needs the
user's decision. Link files as `[NEXT.md](NEXT.md)`.

---

## Traps this repo has actually hit

- **Line endings are mixed.** `README.md`, `GAME_DESIGN.md` and everything in
  `docs/history/` are CRLF; most source is LF. A whole-file rewrite with the
  wrong terminator turns a one-line edit into a 600-line diff. Prefer `Edit`;
  for a repo-wide substitution, read and write **bytes** so the endings survive.
- **A blanket path rewrite eats the file that narrates the rewrite.** The
  CHANGELOG entry describing a move names the old paths on purpose. Exclude it.
- **A checker must not contain the token it counts.** `check_docs.py` builds the
  warning glyph with `chr(0x26A0)` for exactly this reason.
- **A number copied between two files drifts.** It lives in one generated file
  and is quoted with its command. Re-narration is how the old docs reached five
  conflicting accounts of one event.
- **A scoreboard you can charge the target with credits everything.** Be
  suspicious of any metric the project both writes and scores itself against.
- **Silence about an approximation is an argument.** Any bound that drops
  species, truncates a network or holds a coefficient ideal reports itself
  through `notices`.

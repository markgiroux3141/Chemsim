# Session handoff: why the monoliths exist, what they cost, and the replacement

## 1. The cost, in tokens

A model reads roughly one token per four bytes of English. The files a new
session is currently told to read first:

| file | bytes | approx. tokens | share of a 200k context |
|---|---:|---:|---:|
| `NEXT_PROMPT.md` | 129,003 | 32,000 | 16% |
| `MILESTONES.md` ("read it first, it is the authority") | 462,476 | 115,000 | 58% |
| `HANDOFF.md` | 573,910 | 143,000 | 72% |
| `NEXT_SESSION.md` (superseded, still reads as current) | 213,932 | 53,000 | 27% |

`NEXT_PROMPT.md` opens with "The plan is `MILESTONES.md`. Read it first." A session
that obeys has spent 74% of its context before opening a source file, on prose in
which the same event is narrated three to five times with different numbers, and
in which 1,100 warning glyphs make every sentence look equally urgent. It then
reads the code with what is left. That is the mechanism of "getting lost": not
confusion, but a context that is full of history and empty of the task.

## 2. Why this happened

The four files are doing four jobs that need four different lifecycles, and an
append-only file can only do one of them.

| job | needs | what the monoliths did instead |
|---|---|---|
| **history** (what happened, when, why) | append-only, never read whole, grep-only | append-only, but also designated as the thing to read first |
| **backlog** (what is left to do) | edited in place; a finished item is deleted | finished items kept with ✅ and a paragraph of post-mortem, forever |
| **bootstrap** (what to do this session) | overwritten every session; tiny | prepended to, so the top is fresh and the bottom is three weeks stale |
| **rationale** (why the design is what it is) | stable, one topic per file | inlined into every other job and into source comments |

A model with no memory between sessions over-documents defensively. It is also
rewarded here for "never being silent about an approximation", which is the right
rule for the engine and the wrong rule for a handoff file. Every session added a
record of itself to the top of the bootstrap and to the end of the history, and
nothing ever removed anything. Growth without pruning is the whole story.

## 3. The replacement: five files, each with a size cap and a lifecycle

```
CLAUDE.md          auto-loaded. <= 150 lines. Stable. What this is, how to run, where things are, the rules.
NEXT.md            the ONLY bootstrap. <= 120 lines. OVERWRITTEN each session, never appended.
BACKLOG.md         the plan. <= 300 lines. Edited in place. A done item is DELETED, not ticked.
CHANGELOG.md       the diary outlet. Append-only, newest first, <= 12 lines per entry.
                   When it passes 400 lines, the older half rolls into docs/history/changelog-YYYY-MM.md.
docs/design/*.md   rationale, one topic per file, <= 300 lines each. Edited rarely.
docs/history/      the frozen monoliths and rolled-over changelogs. Grep-only. Never read whole.
```

Plus the two that already exist and are right: the memory notes (cross-session
lessons, one fact per file) and `docs/manual/chapters/` (the physics textbook).

### `NEXT.md` layout (the file you point a session at)

```
# NEXT — overwritten 2026-09-01

## State of the box            (every number from a command run today; name the command)
tests 1264 (pytest --co -q) | templates 57 | routes both 38/173 | playable 21 | suite ~30 min

## Last session, in five lines
...

## Do this now                  (at most three tasks, from BACKLOG.md, with done-when)
1. T0.4 fast test subset — done when `pytest -m "not slow"` < 3 min and green.
2. ...

## Open questions for the user  (things a session must not decide alone)
- ...

## Do not                       (three lines at most)
```

That is 60 to 120 lines, roughly 2,000 tokens. With `CLAUDE.md` it is under 5,000.
The session prompt becomes one sentence: *"Read CLAUDE.md and NEXT.md, then do
task 1."*

### The pruning rules, stated so a model can follow them

1. **A finished task leaves `BACKLOG.md`.** Its record is the `CHANGELOG.md` entry
   and the commit. No ✅, no post-mortem paragraph. If the post-mortem taught a
   transferable lesson, it becomes a memory note or a `docs/design/` paragraph.
2. **`NEXT.md` is rewritten, not edited.** At the end of a session, write the
   whole file fresh from `BACKLOG.md` and today's numbers. Anything from the old
   `NEXT.md` that is still true is re-typed; anything not re-typed is gone.
3. **Nothing is copied between files.** A number lives in one generated file and
   is quoted with its command. A rationale lives in one `docs/design/` file and is
   linked. Re-narration is how the monoliths reached five conflicting accounts of
   the same event.
4. **No `⚠`, no ALL-CAPS emphasis outside `docs/history/`.** Emphasis that is
   everywhere is nowhere.
5. **Caps are mechanical.** `tools/check_docs.py` fails `check.ps1` when a cap is
   exceeded, when a `⚠` appears outside `docs/history/`, or when `NEXT.md` has a
   `## Last session` older than the latest commit date. Models blow through soft
   caps; a failing check is the only cap that holds.

## 4. Migrating what exists

Do not try to summarise `MILESTONES.md` into `BACKLOG.md`. Almost all of it is
done work, already in git. One session, in this order:

1. `git mv` the seven root monoliths to `docs/history/` (T0.2). Fix links.
2. Split `MILESTONES.md` on its `## ` headings into `docs/history/milestones/NN-<slug>.md`
   with a generated index, so a grep hit lands in a 5 KB file rather than a 462 KB
   one. `HANDOFF.md` has no headings and cannot be split; leave it whole. It is the
   one file that should never be opened again except by grep.
3. Extract only the **open** items from `MILESTONES.md` and `NEXT_PROMPT.md`
   into `BACKLOG.md`: today that is R4 (rate-aware pruning) and R6 (lattice to
   ions), plus whatever `06-WORK-ORDER.md` adds. Everything marked done is not
   carried.
4. Write `NEXT.md` from `06-WORK-ORDER.md` Tier 0.
5. Move the design rationale that is still load-bearing (the "stock is a
   composition" argument, the "gate is a mechanism" argument, the lattice-vs-ions
   argument, the R-series measurement) from `GAME_DESIGN.md` into
   `docs/design/`, one file each, stripped of the narrative. `GAME_DESIGN.md`
   then becomes a 100-line index or is deleted.
6. Add `tools/check_docs.py` and wire it into `check.ps1`.

## 5. What the memory system is for, and what it is not

The memory notes already do the job the monoliths were failing at: one
transferable lesson per file, with a one-line index that is loaded every
session. Keep using them for "the trap that bit and would bite again." Do not use
them for task state (that is `NEXT.md`), for history (`CHANGELOG.md`), or for
numbers (generated files). A memory note over 40 lines is a design doc in the
wrong place.

## 6. The test of whether this worked

Three sessions from now, a new session should be able to answer these from
`CLAUDE.md` + `NEXT.md` alone, in under 5,000 tokens, with no grep:
what is this project, how do I run it, what do I do today, how will I know it
is done, and what must I not touch. If any answer requires opening
`docs/history/`, the handoff files have started growing again.

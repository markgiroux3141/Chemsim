# Frozen history

Everything in this directory is a record of work already done. It is here to be
**grepped and cited, never read whole and never appended to**. A session that
opens one of these files top to bottom spends its context on narrative and
arrives at the code with nothing left.

| file | what it was | how to use it |
|---|---|---|
| `MILESTONES.md` | the plan, 462 KB, 7,810 lines | now an **index**. The 79 sections live in `milestones/`. |
| `milestones/NN-*.md` | those sections, unedited | `grep -rn 'S9' docs/history/milestones/` lands in a file under 25 KB |
| `HANDOFF.md` | 574 KB, 8,637 lines, **zero headings** | grep only. It cannot be split and should not be opened. |
| `NEXT_SESSION.md` | a superseded bootstrap | superseded by `NEXT.md` at the root |
| `NEXT_PROMPT.md` | the previous bootstrap | superseded by `NEXT.md` at the root |
| `ASSESSMENT.md` | the 2026-08-17 self-assessment | its conclusion is in `fable analysis/01-CRITIQUE.md` |
| `EQUIPMENT_PLAN.md`, `EQUIPMENT_CATALOG.md` | the equipment design | design rationale still live moves to `docs/design/` when a task needs it |

## Why they are frozen

The four bootstrap files above totalled 1.4 MB and a session was told to read
`MILESTONES.md` "first, it is the authority". Reading the set costs about 74% of
a 200k context before a source file is opened. The four files were also doing
four jobs with four different lifecycles — history, backlog, bootstrap and
rationale — and an append-only file can only do one of them.

The replacement is five files with size caps, enforced by `tools/check_docs.py`:

| file | cap | lifecycle |
|---|---|---|
| `CLAUDE.md` | 150 lines | stable; auto-loaded |
| `NEXT.md` | 120 lines | **overwritten** every session, never appended |
| `BACKLOG.md` | 300 lines | edited in place; a done item is **deleted** |
| `CHANGELOG.md` | 12 lines per entry | append-only, newest first |
| `docs/design/*.md` | 300 lines each | one topic per file, edited rarely |

A finished task's record is its `CHANGELOG.md` entry and its commit. If it taught
a transferable lesson, that lesson is a memory note or a `docs/design/` paragraph
— not a post-mortem paragraph kept forever in a backlog.

The full argument is in `fable analysis/08-SESSION-HANDOFF.md`.

## Citing history

A milestone tag in a source comment (`S9`, `M6`, `C4`, `R3`) resolves through
`MILESTONES.md`'s index. Prefer not to add new ones: write what the code does,
and put the argument in `docs/design/` or `docs/manual/chapters/`.

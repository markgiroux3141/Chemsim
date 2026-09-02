# Operating rules for working in this repo

Ten rules. Each exists because the opposite was measured to cost something.

## 1. Start from `CLAUDE.md` and this folder, not from the diaries
`HANDOFF.md` has 8,637 lines and no headings. Loading it costs your whole
context and answers nothing a task needs. Grep it for a specific term if a task
sends you there; never read it top to bottom.

## 2. A session's record is a `CHANGELOG.md` entry and a commit message
Five to ten lines: what changed, which numbers moved (from the generated files),
what is next. Never append to `HANDOFF.md`, `MILESTONES.md`, `NEXT_*.md` or
`README.md`'s narrative. If a finding is worth more than ten lines, it is a
chapter in `docs/manual/chapters/` or a memory note, not a root markdown file.

## 3. No `⚠`, no ALL-CAPS emphasis, no milestone tags in code or docs
The repo has 1,600 warning glyphs in docs and 851 in source; they carry no
signal. Use `NOTE:` or `WARNING:` at most once per file. A comment explains the
code in front of it. A measurement, a history, or an argument goes in `docs/`
with a one-line pointer from the code. Never write "S9 changed this because"
in a source file; write what the code does and why, without the tag.

## 4. Numbers come from a command, on the day, or they are not written down
Every count quoted anywhere (tests, templates, routes, species) must be copied
from the output of a named command run in the same session. The README was
quoting 275 tests against 1,264 and a 25-second suite against 30 minutes. If a
doc has a number you cannot regenerate, delete the number.

## 5. Generated files are regenerated, never edited
`*_data.py`, `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`, and after
T1 `template_data.py`. Each has a `tools/` or `validation/` script that writes it.
Run the script; commit the input and the output together; run `--check` in
`check.ps1`.

## 6. Preserve each file's own line endings
The repo is mixed CRLF and LF. `README.md` and `MILESTONES.md` are CRLF; most
source is LF. A whole-file rewrite with the wrong terminator makes a 600-line
diff out of a one-line edit. Use `Edit` for partial changes. If you must rewrite
a whole file, check `file <path>` first and match it.

## 7. Run the fast checks always, the slow suite only when asked
`check.ps1` (ruff, `pytest -m "not slow"`, catalog structure) after every change.
The full suite is ~30 minutes on the user's own machine; run it only when a
change touches `numerics/`, `vessel/` or `network/`, and ask first.
`validation/tolerance_audit.py` (~10 min) is owed when a trajectory could move.
State plainly which checks you ran and their results, including failures.

## 8. A template is a row; a class is a mechanism; kinetics come from the policy table
After T1, a new template is a line in `data/templates/templates.psv`. Its class
names a mechanism, not an outcome ("fermentation" and "pyrolysis" are outcomes
and were correctly refused). Its `A` and `Ea` come from
`kinetics_policy.psv` unless a cited measurement overrides them. Do not write
a paragraph arguing a barrier; put the source id in the `source` column.

## 9. Never declare what detailed balance derives
No reverse rate, no equilibrium constant, no boiling point, no melting point, no
pKa as a rate parameter. If a reaction runs to the wrong equilibrium, the
formation data or the standard state is wrong; fix that. A declared `orders=`
forbids `reversible=True` and the constructor enforces it.

## 10. Report coverage limits, never hide them
The engine reports a species cap, a molar-mass drop, an unpriceable product, an
unexpanded frontier, a held-ideal γ, and a refused estimator domain. Any new
bound must report itself through the same `notices` path to `Snapshot.notices`.
An approximation that touches matter (drops a species, truncates a network) is
allowed only if the player can see that it happened.

---

## Session template

```
1. Read CLAUDE.md, fable analysis/06-WORK-ORDER.md. Pick the top open task.
2. Read only the files the task names. grep for anything else.
3. Do the task. Run check.ps1. Run the task's own "done when" check.
4. Regenerate any generated file the task touched. Run --check.
5. CHANGELOG.md: one entry. Commit with a message that states the numbers.
6. If you learned something that would change how the NEXT session works,
   write a memory note (feedback or project type) and link it from MEMORY.md.
```

## Things that will tempt you and are wrong

- Fixing the scoreboard rules again. Four corrections are in; it is accurate enough.
- Writing a bespoke test file for one template. Use the table-driven test.
- Adding a physics module because the chemistry for it is interesting. The
  engine is a decade ahead of its content. Add content.
- Reading `MILESTONES.md` to find out what is next. This folder is what is next.
- Explaining a decision in a 40-line comment at the call site. One line and a
  pointer to `docs/manual/chapters/`.

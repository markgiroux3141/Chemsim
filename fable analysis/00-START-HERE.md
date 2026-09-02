# fable analysis — start here

Written 2026-09-01 by Claude Fable 5.1 after a full read of the repository, four
targeted audits (documentation, coverage pipeline, engine code, tests), and the
project's own memory notes. This folder is for the model that continues the work.
It is deliberately short, flat, and free of the repo's warning-glyph style.

## Read in this order

| # | file | read it when |
|---|---|---|
| 1 | `01-CRITIQUE.md` | first. What works, what does not, and why coverage grows slowly. |
| 2 | `02-CODEBASE-MAP.md` | before touching code. The 30 files that matter, with line refs. |
| 3 | `05-COVERAGE-STRATEGY.md` | before adding chemistry. How to change the slope, not just the count. |
| 4 | `06-WORK-ORDER.md` | to pick a task. Prioritised, sized, with acceptance criteria. |
| 5 | `03-HOW-TO-ADD-A-TEMPLATE.md` | when a task says "add a template". |
| 6 | `04-HOW-TO-ADD-A-SPECIES.md` | when a task says "price a species". |
| 7 | `07-OPERATING-RULES.md` | always. How to work here without making the repo worse. |
| 8 | `08-SESSION-HANDOFF.md` | before the first Tier 0 task. Why the monolithic docs cost 74% of a context, and the five-file replacement with size caps. |

Total reading time for all seven: under an hour. You do not need `HANDOFF.md`
(574 KB, no headings), `MILESTONES.md` (462 KB) or `NEXT_SESSION.md` (superseded)
to start. Grep them only when a specific question sends you there.

## The project in one paragraph

`chemsim` is a Python chemistry simulator. Molecules are RDKit graphs, reactions
are SMARTS graph-rewrite templates with forward Arrhenius kinetics, reverse rates
are derived from thermochemistry by detailed balance, and a flask is integrated
as one stiff ODE system over `[n_liquid | n_liquid2 | n_gas | n_solid | T]` with
UNIFAC activity, Henry's law, solubility products, an energy balance and
multi-vessel rigs. A Tkinter window sits on a worker thread over a `World` that
records a replayable script. Coverage is measured against a hand-typed catalog of
1,583 compounds and 173 named industrial routes. Today 57 templates exist, 46 of
173 routes are template-ready, 38 also price every species, and 21 are reachable
from natural materials. The engine is strong. The content pipeline is the
problem, and the process around it has become the second problem.

## The state of the box (verified 2026-09-01)

| fact | value |
|---|---|
| source lines (`src/chemsim`) | 61,839 total; 27,203 excluding 8 generated data modules |
| tests | 1,264 collected, 63 files, 23,563 lines, zero skips, zero xfails |
| full suite wall time | about 30 minutes (no markers, no fast subset, no CI) |
| templates | 57 `ReactionTemplate(...)` constructions (38 synthesis, 9 library, 6 electrolyte, 4 electrochemistry) |
| catalog | 1,583 compounds, 173 routes, 377 steps, 240 reaction classes |
| classes with a template | 59 of 240 |
| routes template-ready / species-ready / both / playable | 46 / 85 / 38 / 21 |
| root-level prose | 1.6 MB, 23,456 lines, of which 84% is append-only diary |
| `SAVE_VERSION` | 9 (`src/chemsim/engine/world.py:122`) |
| line endings | mixed. Preserve each file's own. |

## What this folder is not

It is not a replacement for the code's own docstrings on physics. Where the
engine's reasoning is sound, the comments say so at the call site and these docs
point at them. It does not re-derive the thermodynamics. It tells you where the
project is, why it is there, and what to do differently.

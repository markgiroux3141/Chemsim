# chemsim

A Python chemistry simulator built for **emergence**. Molecules are RDKit graphs;
reactions are SMARTS graph-rewrite templates carrying forward Arrhenius kinetics
only; reverse rates are derived from thermochemistry by detailed balance; a flask
is one stiff ODE over `[n_liquid | n_liquid2 | n_gas | n_solid | T]` with UNIFAC
activity, Henry's law, solubility products, an energy balance and multi-vessel
rigs. Boiling points, equilibria and pH are *consequences*, never lookups. A
Tkinter window sits on a worker thread over a `World` that records a replayable
script. Coverage is scored against a hand-typed catalog of 1,583 compounds and
173 named industrial routes.

## Where to start

1. This file.
2. `NEXT.md` — the only bootstrap. What to do today.
3. `fable analysis/` — the 2026-09-01 external critique and the work order it
   produced. `02-CODEBASE-MAP.md` before touching code, `03-HOW-TO-ADD-A-TEMPLATE.md`
   and `04-HOW-TO-ADD-A-SPECIES.md` when a task says to.
4. `docs/history/` is frozen. Grep it; never read it whole. See its `README.md`.

## Run

```
python -m pip install -e ".[dev,viz]"
python -m chemsim.ui                            # the window
./check.ps1                                     # ruff + fast tests + catalog structure
python -m pytest -q                             # full suite, ~30 min, ASK FIRST
ruff check src tests tools validation
python tools/catalog.py                         # structural validation of the PSVs
python validation/catalog_coverage.py           # regenerates data/catalog/COVERAGE_REPORT.md
python tools/build_playable.py                  # regenerates data/catalog/PLAYABLE.md (~50 s)
python tools/build_route_index.py               # regenerates data/catalog/ROUTE_INDEX.md
python examples/named_routes.py                 # 17 routes end to end (~30 s)
```

## Layers (strict downward imports)

```
ui/         Tkinter window + worker thread + Session (the testable half)
engine/     World (clock, events, script, save/load v9), Scenario, Stock, shelf_data
vessel/     Vessel (3 phases + energy), Rig (edges), conditions (wait_until roots)
discovery/  refine_network -- DORMANT: zero callers, zero tests. Not "done".
numerics/   integrators + RHS + UNIFAC/LLE evaluation. Arrays only, no molecules.
network/    build_network: templates x species -> ConcreteReaction -> KineticArrays
reactions/  ReactionTemplate, template libraries, detailed balance, Hammett, electrodes
properties/ thermochemistry (curated > Benson > Joback), volatility, condensed, minerals, ions
matter/     Molecule (canonical SMILES identity). Where RDKit is *supposed* to live.
```

Two known breaches, both real: `properties/electrolyte.py:406` lazily imports
`reactions.ReactionTemplate` upward; `reactions/template.py:25`,
`reactions/hammett.py:182` and `properties/fragmentation.py` import rdkit
directly, so the README's "nothing above Layer 0 imports rdkit" is false today.

## The ten rules

1. **Start from `CLAUDE.md` and `NEXT.md`.** Not from `docs/history/`. Grep it for
   a term when a task sends you there; never read a diary top to bottom.
2. **A session's record is a `CHANGELOG.md` entry and a commit message.** Five to
   ten lines: what changed, which numbers moved, what is next. Nothing is
   appended to `docs/history/` ever again.
3. **No warning glyphs, no ALL-CAPS emphasis, no milestone tags in new text.**
   The repo has ~1,600 of them in docs and ~1,050 in source; a marker used 1,600
   times carries no signal. `NOTE:` or `WARNING:` at most once per file. An argument goes in
   `docs/design/` or `docs/manual/chapters/` with a one-line pointer from the code.
4. **A number comes from a command run today, or it is not written down.** The
   README quoted 275 tests against 1,264 and a 25-second suite against 30 minutes.
   If you cannot regenerate a number, delete it.
5. **Generated files are regenerated, never edited.** `*_data.py`,
   `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`. Commit input and output
   together.
6. **Preserve each file's own line endings.** The repo is mixed: `README.md`,
   `GAME_DESIGN.md` and the history files are CRLF, most source is LF. A
   whole-file rewrite with the wrong terminator turns a one-line edit into a
   600-line diff. Prefer `Edit`; check before rewriting.
7. **Fast checks always, the slow suite only when asked.** `./check.ps1` after
   every change. The full suite is ~30 minutes on the user's own machine — ask.
   `validation/tolerance_audit.py` (~10 min) is owed when a trajectory could move.
   State which checks you ran, including the failures.
8. **A class names a mechanism, not an outcome.** "fermentation" and "pyrolysis"
   are outcomes and were correctly refused. Every `A` is an order-of-magnitude
   choice for the molecularity and every `Ea` a band midpoint; say so once,
   in the source column, not in a paragraph per template.
9. **Never declare what detailed balance derives.** No reverse rate, no
   equilibrium constant, no boiling point, no melting point, no pKa as a rate
   parameter. If a reaction runs to the wrong equilibrium the formation data or
   the standard state is wrong — fix that. A declared `orders=` forbids
   `reversible=True`, and the constructor enforces it.
10. **Report coverage limits, never hide them.** The engine reports a species cap,
    a molar-mass drop, an unpriceable product, an unexpanded frontier, a held-ideal
    γ and a refused estimator domain. Any new bound reports itself through the
    same `notices` path to `Snapshot.notices`. An approximation that touches
    matter is allowed only if the player can see that it happened.

## Session shape

```
1. Read CLAUDE.md and NEXT.md. Take task 1.
2. Read only the files that task names. Grep for anything else.
3. Do it. Run ./check.ps1 and the task's own done-when check.
4. Regenerate any generated file touched; run its --check.
5. Close with the `handoff` skill (.claude/skills/handoff/), which prunes
   BACKLOG.md, writes the CHANGELOG entry, rewrites NEXT.md whole, saves any
   transferable lesson to memory, holds the caps, commits and pushes main.
```

The `session` skill (.claude/skills/session/) runs all five steps as one unit:
one task, done to its done-when, closed out and pushed. `/session` is how the
user advances the box; `/handoff` alone is for closing out work already done.

The user is not a chemist and does not drive the work. Decide, act, and write
the decision down with its reasoning so it is not relitigated; take their
steering when they give it, and put anything only they can settle under
`NEXT.md`'s open questions rather than stalling on it.

## Things that will tempt you and are wrong

- Adding a physics module because the chemistry is interesting. The engine is an
  order of magnitude ahead of its content. Add content.
- Correcting the coverage scoreboard again. Four corrections are in; it is
  accurate enough.
- Writing a bespoke 400-line test file for one template.
- Reading `docs/history/MILESTONES.md` to find out what is next. `NEXT.md` is.
- Explaining a decision in a 40-line comment at the call site.

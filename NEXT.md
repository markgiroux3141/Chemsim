# NEXT — overwritten 2026-09-12

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-12. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,278 collected | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~70 s, green | ruff + docs + catalog + templates + 39 smoke tests |
| full check | `./check.ps1 -Full`, ~2.5 min, green | adds both report `--check` ratchets |
| full suite | ~30 min, no markers yet | ask before running |
| templates | 57 rows, all `tier=family`, covering 46 catalog classes | `python tools/build_templates.py --check` |
| where a template comes from | `data/templates/templates.psv` only: 5 `ReactionTemplate(` sites in `src/chemsim`, all loaders | same command |
| the bench's library | all 57, and it reports its tier | `ui.examples.full_library()` |
| catalog | 1,583 compounds, 173 routes, 377 steps, 240 classes | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 85 / 38 | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 21, three tiers deep; 44 runnable, 22 fed but unrunnable | `data/catalog/PLAYABLE.md` footer |
| rows extractable and uncovered | 174 of 377, in 132 classes (102 single-row) | `python validation/extraction_yield.py` |
| upper bound if all 174 became templates | template-ready 110, intersection 66 | same command, last two panels |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs and the generated `*_data.py` are CRLF; most source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

T1c is done, and T2a with it. `full_library()` is `load_templates(tier="family")`
-- the module sweep it replaced gathered 50 of 57 and the 50 were not a subset.
The blocker was `inventory.needs_electrolyte` reading the CHARGE only; it reads
the LIBRARY too now, through `ReactionTemplate.touches_ions`. The default bench
went 26 species / 19 reactions to 35 / 24, and sulfur + air + water + NO2 now
takes five generations to exhaust where it took three.

## Do this now

1. **T4 -- reactions reachable from the shelf.** Spec in `BACKLOG.md`. This is the
   headline metric that replaces the organic-family checklist, and the bench
   library is finally the whole table so the count will not have to be redone.
   Read `tools/build_playable.py` for how a report is generated and `--check`ed,
   `engine/inventory.py` for the natural tier, and `network/builder.py` for
   `build_network`'s bounds. Measure ONE pair and multiply before launching the
   sweep: 45 natural rows is ~1,000 pairs.
   *Done when:* the reachable-reaction count prints in `COVERAGE_REPORT.md`
   beside the intersection, with the command that produced it, and its `--check`
   ratchet passes.

2. **T1d -- `examples/named_routes.py` dies on route 2.** Spec in `BACKLOG.md`.
   The traceback is `cannot derive reverse kinetics for reversible template
   'phenol_dissociation'` on salicyl alcohol: no electrolyte provider and no
   `_PAIRS` entry for that anion. T1c's `touches_ions` is the near half of the
   fix -- the example builds its own `Scenario`s and can ask the same question --
   but the missing `_PAIRS` entry is a data question of its own.
   *Done when:* the example runs to the end, its route count is quoted from its
   own output, and `CLAUDE.md`'s run list matches.

3. **R4/E3 -- delete `discovery/refine.py`.** Decided; the argument is in
   `BACKLOG.md`. Half an hour, and it only removes code.
   *Done when:* the module, `discovery/__init__.py`, the README layer row and the
   `chemsim/__init__.py` mention are gone and `./check.ps1` is green.

T0.4 and T1b's second half (retiring the per-template test files) both need a
full-suite run, so they go to whichever session is asked to run the suite.

## Decisions already taken — do not reopen

- **A library's chemistry is part of the electrolyte question.** `needs_electrolyte`
  takes the charge AND the templates: a template that makes an ion needs the
  overlay whether or not anyone poured one, and the overlay is a superset of the
  plain provider so it changes no neutral price. The test is net formal charge
  per SMARTS SLOT, not per atom -- `[N+](=O)[O-]`, `[C-]#[O+]`.
- **A sweep over modules is not a library.** Two shipped, both wrong: by naming
  convention (44) and by result type (50 of 57, not a subset).
- **A PSV row is the template built with its constructor's DEFAULT arguments,**
  every field of it: where a default catalyst is on the row carries the
  already-catalysed SMARTS and the already-rescaled `A`, and
  `library._catalysed_row`/`_surface_row` undo whichever the row carries and
  apply the caller's. An empty optional cell means the `ReactionTemplate`
  default, read off the dataclass and spelled `None` in a signature.
- **The constructors stay.** They are the public API and carry the keyword
  arguments a row cannot -- `catalyst=`, `eta_a=`, `A=`, `rho=`. Not data.
- **`Ea_J` is the only barrier column.** An electrode template's declared
  quantity is a voltage (`Ea = n F eta_a`), and that goes in `source`.
- **What holds "a template is a row" is `CONSTRUCTION_SITES`** -- the set of
  `ReactionTemplate(` sites under `src/chemsim` is exactly the five loaders.
- **`TEMPLATE_CLASSES` is derived.** 14 integrator-TERM entries stay hand-typed
  in `validation/catalog_coverage.py`; the other 46 come from the `class` column.
- **`PLAYABLE.md`'s last line is a contract.** `catalog_coverage._PLAYABLE_FOOTER`
  parses it; change its shape and update the regex in the same commit.
- **Regeneration order is playable, then coverage.** `check.ps1 -Full` runs them
  in that order.
- **T2 and T3 go ahead.** 174 extractable-and-uncovered rows, +28 on the
  intersection at the ceiling, and a ceiling is a ceiling: the LP passes rows
  atom-mapping will refuse.
- **`discovery/refine.py` is deleted, not wired.** A fixpoint is cheap for the
  chemistry that matters, the species cap bounds the expensive case and reports
  itself, and silent pruning breaks rule 10.
- **The organic-family checklist is not a headline metric.** The headline is
  reactions reachable from the shelf (T4), which is computed.
- **The README stays at 561 lines** until C1 moves the physics prose into
  `docs/manual/chapters/`. The budget is 400.

## Open questions for the user

- **`rxnmapper` as a curation-time dependency** for T2. Same standing as
  `chemicals` and RMG-database: used to build data, never imported at runtime.
  Without it T2 needs an RDKit-only mapper, which is a session of its own.
- **Species work is half of T2's payoff.** 36 of the 64 routes extraction would
  make template-ready are held by an unpriceable species; hydrogen-cyanide and
  vanadium-pentoxide each hold three.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md` or `template_data.py`;
  `--check` will fail. A template is edited in `data/templates/templates.psv`.
- Do not read `docs/history/` top to bottom. Grep it.
- Do not add a physics module; the engine is well ahead of the content.
- Do not run the full suite without asking; it is 30 minutes on the user's own
  machine.

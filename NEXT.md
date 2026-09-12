# NEXT — overwritten 2026-09-12

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-12. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,284 collected | `python -m pytest --co -q` |
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
| named routes end to end | 17 routes in 32.4 s | `python examples/named_routes.py` |
| templates a natural pair can reach | 25 of 57; 32 silent and named | `data/catalog/derived/reachable.psv` |
| distinct reactions from the shelf | 24,828, but 98% is four templates | same file, `tools/build_reachable.py` (~35 min) |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs and the generated `*_data.py` are CRLF; most source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

T4 is in: the first number that scores the ENGINE rather than the corpus.
Every pair of the 36 natural shelf rows, to a fixpoint, with all 57 templates
-- 24,828 distinct reactions, 98% of it four templates over a sugar frontier,
and **only 25 of 57 fire at all**. The 32 silent ones are T6. The sweep also
found a hole in T1d, and segfaults at random, so it checkpoints.

## Do this now

1. **T6 -- classify the 32 templates the shelf cannot reach.** Spec in
   `BACKLOG.md`. T4's output turned into work, and a measurement before a
   build: the 32 split into substrate-not-on-the-shelf, needs-a-third-reagent
   (a pair sweep cannot see it), and cannot-fire-at-all -- a bug, and the most
   valuable of the three. Read the `silent_templates` line of
   `data/catalog/derived/reachable.psv`, then each one's SMARTS in
   `data/templates/templates.psv`.
   *Done when:* all 32 carry a label with its evidence and the third group is
   filed as bugs.

2. **T5 -- measure what the 30-row pKa table bounds.** Spec in `BACKLOG.md`.
   T1d made "no pKa for this ion" a reported limit: five turned up in one
   session and T4's sweep reported nineteen in a single flask. Sweep the priced
   corpus against the dissociation templates and group the misses by the acid
   class that would fix them, before writing any pKa.
   *Done when:* the count and its top acid classes are in this table with the
   command, and a follow-up item names the fix the number argues for.

3. **R4/E3 -- delete `discovery/refine.py`.** Decided in `BACKLOG.md`; half an
   hour, and it only removes code.
   *Done when:* the module, `discovery/__init__.py`, the README layer row and the
   `chemsim/__init__.py` mention are gone and `./check.ps1` is green.

T0.4 and T1b's second half need a full-suite run: they go to a session asked
for one.

## Decisions already taken — do not reopen

- **The headline is templates fired, not reactions reached.** A reaction total
  is whatever the most promiscuous template does over a sugar frontier: 98% of
  T4's 24,828 is four of them. What a shelf can DO is the count that fire at all
  and the names of the ones that do not -- computed, never declared.
- **A long sweep checkpoints and names the unit it is on.** `build_reachable`
  segfaults out of RDKit at a different pair each run, with no traceback. A
  35-minute job that cannot say where it died cannot be finished.
- **An ion refusal is two different claims and the overlay tells them apart.**
  Overlay off, a charged species means the PROVIDER is wrong and the builder
  passes it through. Overlay ON and the ion not in its 30-row table, nothing in
  this project prices it: `UnpricedIon`, a coverage limit. It drops the rewrite
  only for a template that NEEDS the price -- an irreversible one still carries
  the ion, which keeps `saponification` working on tristearin.
- **A library's chemistry is part of the electrolyte question.** `needs_electrolyte`
  takes the charge AND the templates, and the test is net charge per SMARTS
  SLOT, not per atom (`[N+](=O)[O-]`). The overlay is a superset, so turning it
  on changes no neutral price. And a sweep over MODULES is not a library.
- **A PSV row is the template with its constructor's DEFAULT arguments,** every
  field: the row carries the already-catalysed SMARTS and rescaled `A`, and
  `library._catalysed_row`/`_surface_row` undo whichever it carries and apply the
  caller's. An empty optional cell means the dataclass default. The constructors
  stay as the public API for `catalyst=`, `eta_a=`, `A=`, `rho=`, and `Ea_J` is
  the only barrier column.
- **What holds "a template is a row" is `CONSTRUCTION_SITES`** -- the
  `ReactionTemplate(` sites under `src/chemsim` are exactly the five loaders.
  `TEMPLATE_CLASSES` is derived: 14 integrator-TERM entries, 46 from `class`.
- **`PLAYABLE.md`'s last line is a contract** parsed by
  `catalog_coverage._PLAYABLE_FOOTER`; change its shape and the regex together.
  Regeneration order is playable, then coverage, as `check.ps1 -Full` runs it.
- **T2 and T3 go ahead.** 174 extractable-and-uncovered rows, +28 on the
  intersection at the ceiling -- and the LP passes rows atom-mapping will refuse.
- **`discovery/refine.py` is deleted, not wired.** A fixpoint is cheap where it
  matters, the species cap bounds the rest, and silent pruning breaks rule 10.
- **The organic-family checklist is not a headline.** T4 is, and it is computed.
  **The README stays at 561 lines** until C1 moves the physics prose out.

## Open questions for the user

- **`rxnmapper` as a curation-time dependency** for T2, same standing as
  `chemicals`: build-time only. Without it T2 needs an RDKit-only mapper.
- **Species work is half of T2's payoff.** 36 of the 64 routes extraction would
  make template-ready are held by an unpriceable species.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md` or `template_data.py`;
  `--check` will fail. A template is edited in `data/templates/templates.psv`.
- Do not read `docs/history/` top to bottom. Grep it.
- Do not add a physics module; the engine is well ahead of the content.
- Do not run the full suite without asking; it is 30 minutes on the user's machine.

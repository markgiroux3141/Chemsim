# NEXT — overwritten 2026-09-02

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-02. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,264 collected, 0 skips, 0 xfails | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~60 s, green | ruff + docs + catalog + 39 smoke tests |
| full suite | ~30 min, no markers yet | ask before running |
| templates | 57: 38 `synthesis.py`, 9 `library.py`, 6 `electrolyte.py`, 4 `electrochemistry.py` | `grep -c 'ReactionTemplate(' src/chemsim/reactions/*.py src/chemsim/properties/electrolyte.py` |
| catalog | 1,583 compounds, 173 routes, 377 steps, 240 classes | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 85 / 38 | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 21, three tiers deep | `data/catalog/PLAYABLE.md` |
| rows extractable and uncovered | 174 of 377, in 132 classes (102 single-row) | `python validation/extraction_yield.py` |
| upper bound if all 174 became templates | template-ready 110, intersection 66 | same command, last two panels |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md` are CRLF; source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

T1.0 measured the gate on the Tier 1 plan. `validation/extraction_yield.py`
cross-tabulates the 377 steps by resolves / balances / class-uncovered: 174 are
extractable and uncovered, which is inside the critique's estimate, and the
intersection could reach 66 from 38. T1 and T2 survive; T3 shrank to 6 families.
`corpus_balance.coefficients()` returns the LP vector, which is fractional where
the nullspace is 2-D, so the extractor needs an integer step. Argument in
`docs/design/extraction-yield.md`.

## Do this now

1. **T0.5 — the two generators disagree.** `data/catalog/COVERAGE_REPORT.md`
   hard-codes a template count (47 against 57 today) and cross-quotes
   `PLAYABLE.md` with numbers `PLAYABLE.md` does not say. Make
   `validation/catalog_coverage.py` count templates and either read
   `tools/build_playable.py`'s output or drop the cross-quote; give both
   generators a `--check` flag that exits non-zero when the committed file
   differs from a fresh run. `check.ps1 -Full` already calls both flags.
   *Done when:* the two files agree, `./check.ps1 -Full` is green, and both
   regenerated reports are committed with the code.

2. **T1 — templates become data.** Spec in `BACKLOG.md` under T1. Read
   `reactions/synthesis.py`, `library.py`, `electrochemistry.py`,
   `properties/electrolyte.py` for the 57 constructors, `tools/build_ion_data.py`
   for the generator pattern, and `validation/catalog_coverage.py:433` for the
   class map the `class` column replaces. Two sessions: first the PSV and the
   generator with a field-equality assertion against every constructor, then the
   table-driven test and the switch-over.
   *Done when:* `examples/named_routes.py`, the bench and the coverage report run
   from the PSV with identical output, and adding a template is one row.

3. **R4/E3 — delete `discovery/refine.py`.** Decided; the argument is in
   `BACKLOG.md`. Half an hour. Take it only after T0.5, because it is Tier 2.
   *Done when:* the module, `discovery/__init__.py`, the README layer row and the
   `chemsim/__init__.py` mention are gone and `./check.ps1` is green.

T0.4 (the fast test subset) needs a full-suite run and is bundled with whichever
session is asked to run the suite anyway.

## Decisions already taken — do not reopen

- **T1 and T2 go ahead.** 174 extractable-and-uncovered rows, +28 on the
  intersection at the ceiling, and they do not concentrate in covered classes.
  The ceiling is a ceiling: the LP passes rows atom-mapping will refuse
  (`vanillin-lignin` 1, `abe-fermentation` 1).
- **T3 is bounded, not repeating.** Only 6 uncovered classes have three or more
  extractable rows.
- **`discovery/refine.py` is deleted, not wired.** A fixpoint is cheap for the
  chemistry that matters, the species cap already bounds the expensive case and
  reports itself, and silent pruning breaks rule 10.
- **The organic-family checklist is not a headline metric.** The headline is
  reactions reachable from the shelf (T4), which is computed. The 173-route
  intersection stays.
- **The README stays at 561 lines** until C1 moves the physics prose into
  `docs/manual/chapters/`. The budget is 400.

## Open questions for the user

- **`rxnmapper` as a curation-time dependency** for T2. T1.0 cleared the gate.
  Same standing as `chemicals` and RMG-database: used to build data, never
  imported at runtime. Without it T2 needs an RDKit-only mapper, which is a
  session of its own.
- **Species work is half of T2's payoff.** 36 of the 64 routes extraction would
  make template-ready are held by an unpriceable species; hydrogen-cyanide and
  vanadium-pentoxide each hold three. No decision needed, but it is where the
  species sessions should aim.

## Do not

- Do not read `docs/history/` top to bottom. Grep it.
- Do not start T2 before T1 is in; T2 writes rows into T1's table.
- Do not add a physics module. The engine is an order of magnitude ahead of the
  content.
- Do not run the full suite without asking; it is 30 minutes on the user's own
  machine.

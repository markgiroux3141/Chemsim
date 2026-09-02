# NEXT — overwritten 2026-09-02

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-02. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,264 collected, 0 skips, 0 xfails | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~60 s, green | ruff + docs + catalog + 39 smoke tests |
| full check | `./check.ps1 -Full`, ~2.5 min, green | adds both report `--check` ratchets |
| full suite | ~30 min, no markers yet | ask before running |
| templates | 57: 38 `synthesis.py`, 9 `library.py`, 6 `electrolyte.py`, 4 `electrochemistry.py` | counted by `catalog_coverage.template_counts()` |
| catalog | 1,583 compounds, 173 routes, 377 steps, 240 classes | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 85 / 38 | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 21, three tiers deep; 44 runnable, 22 fed but unrunnable | `data/catalog/PLAYABLE.md` footer |
| rows extractable and uncovered | 174 of 377, in 132 classes (102 single-row) | `python validation/extraction_yield.py` |
| upper bound if all 174 became templates | template-ready 110, intersection 66 | same command, last two panels |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md` are CRLF; source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

T0.5 stopped the coverage report asserting numbers it could count. Five
hand-maintained `N_*_TEMPLATES` constants summed to 47 against 57 in the tree;
`template_counts()` walks the source with `ast` instead. The `PLAYABLE.md`
cross-quote (36 runnable / 12 playable) is now parsed from that file's footer,
which gained the fed-but-unrunnable count and is a declared contract. New
`catalog.emit()` gives both generators `--check`, so a stale committed report
fails `./check.ps1 -Full` instead of being silently rewritten.

## Do this now

1. **T1 — templates become data.** Spec in `BACKLOG.md` under T1. Read
   `reactions/synthesis.py`, `library.py`, `electrochemistry.py`,
   `properties/electrolyte.py` for the 57 constructors, `tools/build_ion_data.py`
   for the generator pattern, and `validation/catalog_coverage.py` for
   `TEMPLATE_CLASSES` (the class map the `class` column replaces) and
   `template_counts()` (which counts `ReactionTemplate(` construction sites and
   must still say 57 after the switch-over, or be changed deliberately). Two
   sessions: first the PSV and the generator with a field-equality assertion
   against every constructor, then the table-driven test and the switch-over.
   *Done when:* `examples/named_routes.py`, the bench and the coverage report run
   from the PSV with identical output, `./check.ps1 -Full` is green, and adding a
   template is one row.

2. **R4/E3 — delete `discovery/refine.py`.** Decided; the argument is in
   `BACKLOG.md`. Half an hour, and it is the only Tier 2 item worth taking before
   T1 lands because it only removes code.
   *Done when:* the module, `discovery/__init__.py`, the README layer row and the
   `chemsim/__init__.py` mention are gone and `./check.ps1` is green.

3. **T4 — reactions reachable from the shelf.** Spec in `BACKLOG.md`. Take this
   only if T1 is in; it is the headline metric that replaces the organic-family
   checklist, and it reads the template table T1 creates.
   *Done when:* one command prints the count and `NEXT.md`'s state table quotes it.

T0.4 (the fast test subset) needs a full-suite run and is bundled with whichever
session is asked to run the suite anyway.

## Decisions already taken — do not reopen

- **A generated report counts, it does not assert.** The template count is an
  `ast` walk, not a constant. It counts CONSTRUCTION SITES, so the integrator
  TERMS (precipitation, calcination, roasting, surface) stay covered classes with
  no template behind them — that distinction is the reason M3 and M6 declined to
  increment the old constants, and it now holds itself.
- **`PLAYABLE.md`'s last line is a contract.** `catalog_coverage._PLAYABLE_FOOTER`
  parses it; change its shape and update the regex in the same commit. It refuses
  loudly rather than falling back to a hand-typed number.
- **Regeneration order is playable, then coverage.** The coverage report reads
  the playable footer, so a fresh `PLAYABLE.md` is an input to a fresh
  `COVERAGE_REPORT.md`. `check.ps1 -Full` runs them in that order.
- **T1 and T2 go ahead.** 174 extractable-and-uncovered rows, +28 on the
  intersection at the ceiling, and they do not concentrate in covered classes.
  The ceiling is a ceiling: the LP passes rows atom-mapping will refuse.
- **T3 is bounded, not repeating.** Only 6 uncovered classes have three or more
  extractable rows.
- **`discovery/refine.py` is deleted, not wired.** A fixpoint is cheap for the
  chemistry that matters, the species cap already bounds the expensive case and
  reports itself, and silent pruning breaks rule 10.
- **The organic-family checklist is not a headline metric.** The headline is
  reactions reachable from the shelf (T4), which is computed.
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

- Do not hand-edit `COVERAGE_REPORT.md` or `PLAYABLE.md`; `--check` will fail.
- Do not read `docs/history/` top to bottom. Grep it.
- Do not add a physics module. The engine is an order of magnitude ahead of the
  content.
- Do not run the full suite without asking; it is 30 minutes on the user's own
  machine.

# NEXT — overwritten 2026-09-08

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-08. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,275 collected | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~70 s, green | ruff + docs + catalog + templates + 39 smoke tests |
| full check | `./check.ps1 -Full`, ~2.5 min, green | adds both report `--check` ratchets |
| full suite | ~30 min, no markers yet | ask before running |
| templates | 57: 38 `synthesis.py`, 9 `library.py`, 6 `electrolyte.py`, 4 `electrochemistry.py` | `catalog_coverage.template_counts()` |
| template rows | 57 rows, all `tier=family`, covering 46 catalog classes | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps, 240 classes | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 85 / 38 | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 21, three tiers deep; 44 runnable, 22 fed but unrunnable | `data/catalog/PLAYABLE.md` footer |
| rows extractable and uncovered | 174 of 377, in 132 classes (102 single-row) | `python validation/extraction_yield.py` |
| upper bound if all 174 became templates | template-ready 110, intersection 66 | same command, last two panels |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs and the generated `*_data.py` are CRLF; most source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

The first half of T1 landed. All 57 templates are now rows in
`data/templates/templates.psv`, `tools/build_templates.py` emits
`src/chemsim/reactions/template_data.py`, and `--check` (in `check.ps1`) refuses
both a stale module and any row that has drifted from the constructor it copies.
Nothing imports the module yet — the engine still builds templates from the
constructors, which is exactly what makes the equality check mean something. No
chemistry moved and no coverage number moved.

## Do this now

1. **T1 — the switch-over.** Spec in `BACKLOG.md` under T1, which now lists the
   four moving parts. Read `data/templates/templates.psv`'s header and
   `tools/build_templates.py` first; then `reactions/library.py` lines 130-200
   (`CATALYST_REFERENCE`, `_maybe_catalyse`, `_kinetics`, `_surface_kinetics` —
   the transform a row does not carry, and the reason a constructor keeps its
   keyword arguments) and `validation/catalog_coverage.py`'s `TEMPLATE_CLASSES`
   and `template_counts()`.
   *Done when:* `examples/named_routes.py`, the bench and the coverage report run
   from the PSV with identical output, `./check.ps1 -Full` is green, and adding
   a template is one row.

2. **R4/E3 — delete `discovery/refine.py`.** Decided; the argument is in
   `BACKLOG.md`. Half an hour, and it only removes code.
   *Done when:* the module, `discovery/__init__.py`, the README layer row and the
   `chemsim/__init__.py` mention are gone and `./check.ps1` is green.

3. **T4 — reactions reachable from the shelf.** Spec in `BACKLOG.md`. Take this
   only after T1 lands; it is the headline metric that replaces the
   organic-family checklist, and it reads the template table.
   *Done when:* one command prints the count and `NEXT.md`'s state table quotes it.

T0.4 (the fast test subset) needs a full-suite run and is bundled with whichever
session is asked to run the suite anyway.

## Decisions already taken — do not reopen

- **A PSV row is the template built with its constructor's DEFAULT arguments,
  and every field of it.** Not the constructor's parameters: where a default
  catalyst is on (`skraup_cyclisation`, `alkene_isomerisation`, `wacker_oxidation`,
  the four solid-catalyst gas routes) the row carries the already-catalysed
  SMARTS and the already-rescaled `A`. The keyword arguments stay in Python.
- **An empty optional cell means the `ReactionTemplate` default**, read off the
  dataclass by the generator, so a default lives in exactly one place.
- **`Ea_J` is the only barrier column.** An electrode template's declared
  quantity is really a voltage (`Ea = n F eta_a`), and that is recorded in the
  `source` cell rather than in a second column: two numbers in one file that
  must agree is the drift T0.5 spent a session removing.
- **A generated report counts, it does not assert.** `template_counts()` is an
  `ast` walk over `ReactionTemplate(` CONSTRUCTION SITES, which is why the
  integrator TERMS (precipitation, calcination, roasting, surface) stay covered
  classes with no template behind them. `_NOT_A_TEMPLATE_SOURCE` keeps the
  generated loader out of that count and is deleted by the switch-over.
- **13 of `TEMPLATE_CLASSES`' 59 keys can never have a row.** They are
  integrator terms, and a lattice is not a graph. The `class` column carries the
  other 46.
- **`PLAYABLE.md`'s last line is a contract.** `catalog_coverage._PLAYABLE_FOOTER`
  parses it; change its shape and update the regex in the same commit.
- **Regeneration order is playable, then coverage.** The coverage report reads
  the playable footer. `check.ps1 -Full` runs them in that order.
- **T1 and T2 go ahead.** 174 extractable-and-uncovered rows, +28 on the
  intersection at the ceiling. The ceiling is a ceiling: the LP passes rows
  atom-mapping will refuse.
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

- **`rxnmapper` as a curation-time dependency** for T2. Same standing as
  `chemicals` and RMG-database: used to build data, never imported at runtime.
  Without it T2 needs an RDKit-only mapper, which is a session of its own.
- **Species work is half of T2's payoff.** 36 of the 64 routes extraction would
  make template-ready are held by an unpriceable species; hydrogen-cyanide and
  vanadium-pentoxide each hold three.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md` or `template_data.py`;
  `--check` will fail.
- Do not read `docs/history/` top to bottom. Grep it.
- Do not add a physics module. The engine is an order of magnitude ahead of the
  content.
- Do not run the full suite without asking; it is 30 minutes on the user's own
  machine.

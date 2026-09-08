# NEXT — overwritten 2026-09-08

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-08. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,276 collected | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~70 s, green | ruff + docs + catalog + templates + 39 smoke tests |
| full check | `./check.ps1 -Full`, ~2.5 min, green | adds both report `--check` ratchets |
| full suite | ~30 min, no markers yet | ask before running |
| templates | 57 rows, all `tier=family`, covering 46 catalog classes | `python tools/build_templates.py --check` |
| where a template comes from | `data/templates/templates.psv` only: 5 `ReactionTemplate(` sites in `src/chemsim`, all loaders | same command |
| catalog | 1,583 compounds, 173 routes, 377 steps, 240 classes | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 85 / 38 | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 21, three tiers deep; 44 runnable, 22 fed but unrunnable | `data/catalog/PLAYABLE.md` footer |
| rows extractable and uncovered | 174 of 377, in 132 classes (102 single-row) | `python validation/extraction_yield.py` |
| upper bound if all 174 became templates | template-ready 110, intersection 66 | same command, last two panels |
| the bench's library | 50 of 57 templates, and not a subset — see T1c | `ui.examples.full_library()` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs and the generated `*_data.py` are CRLF; most source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

T1 is done. The 57 constructors in `reactions/{library,synthesis,electrochemistry}`
and `properties/electrolyte` are wrappers over `load_templates()`; they keep their
keyword arguments and hold no data. Proven by snapshotting every
template-producing callable over a keyword grid before and after: 577 variants
across 69 callables, byte-identical. Adding a template is one row, measured. Two
pre-existing breaks surfaced and were filed rather than fixed: T1c and T1d.

## Do this now

1. **T1c — the bench's library is 50 of 57 templates.** Spec in `BACKLOG.md`,
   which carries the three separate causes and the measured blocker. Read
   `src/chemsim/ui/examples.py` (`full_library`, `bench`), then
   `engine/inventory.py`'s `scenario_for`. The fix is
   `load_templates(tier="family")`, and it refuses at build time until
   `scenario_for` turns `electrolyte` on for a LIBRARY that makes ions rather
   than only for a CHARGE that contains one.
   *Done when:* `full_library()` returns 57 and reports its tier, the bench
   builds, and `./check.ps1` is green.

2. **T4 — reactions reachable from the shelf.** Spec in `BACKLOG.md`. This is
   the headline metric that replaces the organic-family checklist, and it reads
   the template table, which now exists. Take it after T1c: a reachability count
   computed off a 50-template library would be the wrong number.
   *Done when:* the count prints in `COVERAGE_REPORT.md` beside the
   intersection, with the command that produced it.

3. **R4/E3 — delete `discovery/refine.py`.** Decided; the argument is in
   `BACKLOG.md`. Half an hour, and it only removes code.
   *Done when:* the module, `discovery/__init__.py`, the README layer row and the
   `chemsim/__init__.py` mention are gone and `./check.ps1` is green.

T0.4 and T1b's second half (retiring the per-template test files) both need a
full-suite run, so they go to whichever session is asked to run the suite.

## Decisions already taken — do not reopen

- **A PSV row is the template built with its constructor's DEFAULT arguments,
  and every field of it.** Where a default catalyst is on, the row carries the
  already-catalysed SMARTS and the already-rescaled `A`;
  `library._catalysed_row` and `_surface_row` undo whichever the row carries and
  apply the caller's, so `A` is always on the uncatalysed basis exactly as
  `_kinetics` always saw it. Every pre-exponential in the table round-trips
  through `CATALYST_REFERENCE` to the last bit — checked, not assumed.
- **An empty optional cell means the `ReactionTemplate` default**, read off the
  dataclass, so a default lives in one place; in a constructor's signature that
  default is now spelled `None`.
- **The constructors stay.** They are the public API and carry the keyword
  arguments a row cannot — `catalyst=`, `eta_a=`, `A=`, `rho=`. Not data.
- **`Ea_J` is the only barrier column.** An electrode template's declared
  quantity is a voltage (`Ea = n F eta_a`, `n` the row's own `electrons`), and
  that goes in `source`, not in a second column.
- **The row-vs-constructor check is replaced by `CONSTRUCTION_SITES`.** With the
  constructors reading their rows, comparing the two compares the table with
  itself. What holds "a template is a row" is the inverse claim: the set of
  `ReactionTemplate(` sites under `src/chemsim` is exactly the five loaders, and
  a new site has to be argued for in `tools/build_templates.py`.
- **`TEMPLATE_CLASSES` is derived.** 14 integrator-TERM entries stay hand-typed
  in `validation/catalog_coverage.py` — a lattice is not a graph and can have no
  row — and the other 46 come from the `class` column.
  `acid-displacement-precipitating` is carried by both, and the merge says so.
- **`PLAYABLE.md`'s last line is a contract.** `catalog_coverage._PLAYABLE_FOOTER`
  parses it; change its shape and update the regex in the same commit.
- **Regeneration order is playable, then coverage.** The coverage report reads
  the playable footer. `check.ps1 -Full` runs them in that order.
- **T2 and T3 go ahead.** 174 extractable-and-uncovered rows, +28 on the
  intersection at the ceiling — and a ceiling is a ceiling, since the LP passes
  rows atom-mapping will refuse. T3 is bounded: 6 classes have 3+ such rows.
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

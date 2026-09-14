# NEXT — overwritten 2026-09-14

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-14. The command is named.

| fact | value | command |
|---|---|---|
| **route coverage ceiling** | **110 template-ready, ~66 intersection. 173 is NOT the target** | the script in `docs/design/route-coverage-ceiling.md` |
| routes template-ready / species-ready / both | 49 / 90 / 41 | `data/catalog/COVERAGE_REPORT.md` |
| routes runnable / playable | 49 / 23 | `data/catalog/PLAYABLE.md` footer |
| templates | 67 rows, all `tier=family`, 50 catalog classes | `python tools/build_templates.py --check` |
| template rows against their catalog step | 67 rows / 208 steps: 38 pass, 15 partial, 9 wrong-product, 3 no-substrate, 2 no-class | `python tools/check_template_products.py` (2.4 s) |
| why the 29 non-passing rows miss | 9 salt, 5 stereo, 10 other | same, or the `#!` keys in `derived/template_products.psv` |
| tests | 1,353 collected | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~90 s, green | ruff + docs + catalog + templates + template products + silent + 83 smoke |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| why templates are silent | 15 no-substrate, 9 needs-more-than-a-pair, 0 cannot-fire; `pool_species` 325, shelf closure 50 | `classify_silent.py --check`, current |
| pKa table / corpus ions | 41 `AcidPair` rows; the rows reach 1,078 ions over the corpus and 1,022 are unpriceable, from 388 compounds | `python validation/pka_domains.py` panels 0 and 1 |
| the shelf | 71 rows | `data/catalog/shelf.psv` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| expensive checks owed | `suite` DUE (4 commits), `reachable` DUE (12 commits, last 2026-09-12) | `python tools/cadence.py` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, `CLAUDE.md`, the PSVs, `catalog_coverage.py` and `electrolyte.py` are CRLF; `check.ps1`, `docs/design/`, `tools/` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T3 wrote eight family rows by hand over four of its six classes — two
ammoxidations, two nucleophilic substitutions, three nucleophilic additions, one
intramolecular Williamson. `template-ready` 46 -> 49, BOTH 40 -> 41, runnable 47
-> 49, `pass` 31 -> 38, shelf closure 48 -> 50. The other two classes are
refused with their measurement in `docs/design/two-refused-template-classes.md`:
air oxidation needs three O2 slots in one rewrite, and nitration's declared
polynitrate is unreachable in any run because `build_network` cannot price the
mononitrate the path goes through. Six of the eight rows build reactions in a
network; the two that do not are blocked on HCN having no thermochemistry, and
they say so in their own `notes` cell.

## Do this now

1. **T2 — the extractor, on the RDKit-only path.** Spec in `BACKLOG.md`. This is
   the rate-changing item and T3 is out of the way. Do not wait on the
   `rxnmapper` question below: T3's eight rows are all one-bond-context rewrites
   that RDKit's own `ReactionFromSmarts` round-trips, so an RDKit-only mapper is
   enough to start and `rxnmapper` is an optimisation, not a gate. Two walls are
   counted and must be decided BEFORE writing it, not after: the catalog spells
   a precipitated salt as one species where the engine holds its ions (9 rows),
   and declares a stereoisomer where a template emits the flat species (5). The
   corpus carries no stoichiometric coefficients, so `corpus_balance.
   coefficients()` needs a smallest-integer step after it.
   *Done when:* extracted rows reach `pass` in `template_products.psv`, the
   report separates template-ready-via-family from via-literal, `./check.ps1`
   green.

2. **Two formation entries light three rows already written.** T28 in
   `BACKLOG.md`. `methane_ammoxidation` and `cyanide_imine_addition` both reach
   `pass` against their catalog steps and build ZERO reactions, because HCN has
   no curated entry and neither Joback nor Benson will price it. An alkyl
   nitrate is the same shape and is what `esterification-nitration` is refused
   on. Source both the way `docs/design/` records it, never from recall.
   *Done when:* `build_network(['CC=N','C#N'], ...)` returns a reaction, and
   the two rows stop appearing in `unpriced`.

3. **Two expensive checks are due and both are the user's call.** `suite` is 30
   minutes at 4 commits; `reachable` is 35 minutes at 12 and nothing has
   re-derived `derived/reachable.psv` since 2026-09-12. T3 added eight templates,
   so `reachable`'s fired count and reaction total will both move and that is the
   measurement. `python -m pytest -q`; `python tools/build_reachable.py`; then
   `python tools/cadence.py --record <check> --result pass|fail --note "..."`.
   *Done when:* both ledger rows are recorded with what they said.

## Decisions already taken — do not reopen

- **173 is not the target and never was reachable.** Ceiling 110 template-ready
  / ~66 intersection against 49 / 41 today. `docs/design/route-coverage-ceiling.md`.
  Quote 66, not 173.
- **Change the rate, do not grind the queue.** The session skill's Step 0b.
  Per-row pKa curation is real playability work and is NOT task 1 while T2 is
  open.
- **`catalytic-air-oxidation` and `esterification-nitration` are refused as
  template work** (`docs/design/two-refused-template-classes.md`). What is left
  of them is a class split and a formation value, both in T28.
- **A judge that iterates a row over its own products would have been wrong.**
  It was the obvious fix for nitration's `partial` and it would have credited a
  class whose intermediate has no standard state. The instrument fires once on
  purpose.
- **A pinned count is not a guard.** Two tests in `test_template_table.py`
  asserted 46 classes and a constructor per row; both failed on a new row and
  neither was about anything. They derive the split now.
- **The per-template test files are not retired**; **no species `build_network`
  registers may be unpriceable**; **a declared order may never be reversible**;
  **backwards is retrosynthesis**; **the expensive checks are clocked in
  commits**; **a class names a mechanism, never an outcome**.

## Open questions for the user

- **`suite` and `reachable` are 65 minutes between them and both are due.**
  Task 3. Say whether to spend it.
- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is. Task 1 no longer waits on this; the answer would make its
  mapper better, not possible.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure and a pyrrhotite flask both make it, and no catalog route does.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `*_data.py`, `reachable.psv`, `species_roles.psv`, `silent_templates.psv` or
  `template_products.psv`.
- Do not chase 173, re-derive the ceiling, make per-row pKa curation task 1,
  write a pKa you cannot source, or reopen the phenol or the T3 refusals.
- Do not read `docs/history/` whole (grep it), add a physics module, stamp a
  cadence row you did not run, or rewrite a mixed-ending file whole — a block
  inserted with LF into a CRLF file is how BACKLOG.md went mixed this session.

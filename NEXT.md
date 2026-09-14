# NEXT — overwritten 2026-09-14

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-14. The command is named.

| fact | value | command |
|---|---|---|
| **route coverage ceiling** | **110 template-ready, ~66 intersection. 173 is NOT the target** | the script in `docs/design/route-coverage-ceiling.md` |
| routes template-ready / species-ready / both | 65 / 95 / 53, and **49 / 95 / 43 on hand-typed rows alone** | `data/catalog/COVERAGE_REPORT.md` |
| routes runnable / playable | 50 / 23 -- `PLAYABLE.md` scores the `family` tier ALONE, on purpose | `data/catalog/PLAYABLE.md` footer |
| the same two granting the extracted rows | 60 / 25 | same file, the note under §1 |
| corpus species no provider prices | 401 of 1,583 (was 408 before T28) | `python validation/catalog_coverage.py` |
| templates | 125 rows: 67 `family` hand-typed, 58 `literal` extracted; 102 catalog classes | `python tools/build_templates.py --check` |
| reaction classes with a template | 115 of 240, 63 of them a family row | `python validation/catalog_coverage.py` |
| template rows against their catalog step | 96 pass, 15 partial, 9 wrong-product, 3 no-substrate, 2 no-class over 279 steps | `python tools/check_template_products.py` (3.8 s) |
| steps the extractor refused | 178 of 236: 75 salt, 35 stoichiometry, 24 stereo, 22 coefficients, 10 no-graph, 5 closed-cycle, 4 centre, 3 duplicate | `data/templates/needs_review.psv` footer |
| tests | 1,360 collected; **1,353 pass and 7 FAIL** -- all 7 pre-existing, see T31 | `python -m pytest -q` (29m48s) |
| fast check | `./check.ps1`, ~95 s, green, 88 smoke tests | ruff + docs + catalog + extracted + templates + template products + silent + smoke |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| why templates are silent | 30: 20 no-substrate, 10 needs-more-than-a-pair, 0 cannot-fire; `pool_species` 325, shelf closure 50 at frontier 0 | `python tools/classify_silent.py` |
| the shelf sweep | 666 pairs, 23,140 distinct reactions, **37 of 67 templates fire**, 0 crashed, 1,254 s | `data/catalog/derived/reachable.psv` footer |
| pKa table / ions derived | 41 `AcidPair` rows; **43** ions priced (cyanide is new, off a row that already existed) | `python validation/pka_domains.py` |
| the shelf | 71 rows | `data/catalog/shelf.psv` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| expensive checks | all four clocked rows recorded today; `suite` and `tolerance` recorded RED with their reasons | `python tools/cadence.py` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, `CLAUDE.md`, `thermochemistry.py`, the catalog PSVs and `physical_data.py` are CRLF; `check.ps1`, `tools/`, `tests/` and `formation_data.py` are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T28 priced hydrogen cyanide and the alkyl nitrates, and every step of it found a
second wall behind the first. HCN's entry is in `_CURATED_RAW` and not in
`formation_data.PHYSICAL_PROPERTIES`, because that tier's members are ordinary
condensable organics while HCN's Antoine residual (1.99%) and Hvap gap (12.6%)
put it with HF and water. Benson's missing nitrate group was a missing KEY, not
a missing number. The mononitrates then needed a PHYSICAL half nobody had looked
up, because `physical_data.py` is generated from the corpus and a catalog step
names its endpoints. Net: 7 fewer refused species, +5 species-ready routes, +1
runnable route (`andrussow`), and `esterification-nitration` went from worth
nothing to worth a route.

## Do this now

1. **T30 — write the nitration template; its blocker is gone and it is worth a
   route.** Spec in `BACKLOG.md`; the SMARTS is written out and already run in
   `docs/design/two-refused-template-classes.md`. T3 refused this class because
   nitroglycerin was unreachable, and it is not any more: glycerol + nitric acid
   now builds 7 species and 4 reactions and makes the trinitrate. Expect
   `partial` on its three steps -- each declares an exhaustively nitrated
   polyol, so one rewrite cannot reach it -- and record that as the step being a
   lump rather than the row being wrong.
   *Done when:* the row is in `templates.psv` at `tier=family`, `guncotton` is
   runnable, and `PLAYABLE.md` moves with it.

2. **T31 — six red scoreboard pins, none of them from T28.** `test_fermentation`,
   `test_vanillin` and `test_vitriol` fail two apiece on a CLEAN tree; measured
   by stashing and re-running at `e5dc47d`. They pin §8b counts that T3 and T2
   moved. Cheap, and it is what makes the next suite run mean something.
   *Done when:* each is green or re-pinned with the reason its number moved.

3. **T2c — promote one literal row to `family`.** Unchanged and still the cheap
   playable route; granting all 58 extracted rows would take runnable 50 -> 60.
   T2d gates it: the gate compares canonical SMILES, so it cannot see a mapping
   that is wrong on a symmetric product. Check the mapping by hand, argue the
   barrier, move the row.
   *Done when:* one class moves tier and `PLAYABLE.md`'s headline moves with it.

## Decisions already taken — do not reopen

- **A curated record's TIER is decided by a measurement, not by its
  description.** HCN fits `PHYSICAL_PROPERTIES`'s stated rule and fails that
  tier's measured band, so it lives in `_CURATED_RAW`. The argument is in the
  entry's own comment.
- **`catalytic-air-oxidation` does not become four `pass` rows**, on arithmetic:
  `judge` scores ONE application of ONE row. See T28 in `BACKLOG.md`.
- **The extractor's two walls are refusals** (75 salt, 24 stereo), argued in
  `tools/extract_templates.py`'s docstring.
- **`PLAYABLE.md` scores the `family` tier and `COVERAGE_REPORT.md` every tier.**
  Both print the split.
- **A literal row is irreversible and declares no orders, no alpha, no rho.**
- **173 is not the target.** Quote 66. **Change the rate, not the queue** --
  per-row pKa curation is real work and is not task 1.
- **A pinned count is not a guard**; **no species `build_network` registers may
  be unpriceable**; **backwards is retrosynthesis**; **a class names a
  mechanism, never an outcome**.

## Open questions for the user

- **The suite has been red for three commits and nobody was told.** Seven tests,
  all scoreboard pins, none in the smoke set. T31 fixes six and T29 the seventh;
  both are cheap. Worth deciding whether `test_playable.py` joins `check.ps1`
  at +47 s, which would have caught all of them.
- **`shelf.psv` is hand-maintained game design** (T29). The audit now asks for
  `ammonia` and `platinum`; giving a player either is a design call.
- **`docs/design/two-refused-template-classes.md` names one thing worth building
  for the bench and nothing for the scoreboard**: a `family` `autoxidation` row
  for a primary benzylic methyl, so a player can oxidise a xylene.

## Do not

- Do not hand-edit `literal.psv`, `needs_review.psv`, `COVERAGE_REPORT.md`,
  `PLAYABLE.md`, `ROUTE_INDEX.md`, `*_data.py`, `reachable.psv`,
  `species_roles.psv`, `silent_templates.psv` or `template_products.psv`.
- Do not chase 173, re-derive the ceiling, make per-row pKa curation task 1,
  write a pKa you cannot source, or reopen the T2, T3 or T28c refusals.
- Do not put a `literal` row in `templates.psv` or a `family` row in
  `literal.psv` -- the tier and the file are the same fact twice.
- Do not read `docs/history/` whole (grep it), add a physics module, stamp a
  cadence row you did not run, or rewrite a mixed-ending file whole.

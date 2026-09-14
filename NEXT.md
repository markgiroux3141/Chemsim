# NEXT — overwritten 2026-09-14

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-14. The command is named.

| fact | value | command |
|---|---|---|
| **route coverage ceiling** | **110 template-ready, ~66 intersection. 173 is NOT the target** | the script in `docs/design/route-coverage-ceiling.md` |
| routes template-ready / species-ready / both | 66 / 95 / 53, and **50 / 95 / 43 on hand-typed rows alone** | `python validation/catalog_coverage.py` |
| routes runnable / playable | **51** / 23 -- `PLAYABLE.md` scores the `family` tier ALONE, on purpose | `data/catalog/PLAYABLE.md` footer |
| the same two granting the extracted rows | 61 / 25 | same file, the note under §1 |
| corpus species no provider prices | 401 of 1,583 | `python validation/catalog_coverage.py` |
| templates | 126 rows: 68 `family` hand-typed, 58 `literal` extracted; 103 catalog classes | `python tools/build_templates.py --check` |
| reaction classes with a template | 116 of 240, 64 of them a family row | `python validation/catalog_coverage.py` |
| template rows against their catalog step | 96 pass, 16 partial, 9 wrong-product, 3 no-substrate, 2 no-class over 282 steps | `python tools/check_template_products.py` (4 s) |
| steps the extractor refused | 175 of 233: 75 salt, 35 stoichiometry, 23 stereo, 20 coefficients, 10 no-graph, 5 closed-cycle, 4 centre, 3 duplicate | `data/templates/needs_review.psv` footer |
| tests | 1,360 collected; **7 FAIL, all 7 pre-existing and unchanged by T30** -- see T31, T29 | `python -m pytest -q` on the four pin files (133 s) |
| fast check | `./check.ps1`, ~95 s, green, 88 smoke tests | ruff + docs + catalog + extracted + templates + template products + silent + smoke |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| why templates are silent | 30: 20 no-substrate, 10 needs-more-than-a-pair, 0 cannot-fire; `pool_species` 325, shelf closure 50 at frontier 0 | `python tools/classify_silent.py` (2 s) |
| the shelf sweep | 666 pairs, 23,140 distinct reactions, 37 of 67 templates fire, 0 crashed, 1,254 s | `data/catalog/derived/reachable.psv` footer (NOT re-run today) |
| pKa table / ions derived | 41 `AcidPair` rows, 43 ions priced | unchanged since T28 |
| the shelf | **72 rows**: 43 natural, 25 intermediate, 4 bottle (yesterday's NEXT said 71; it was wrong) | `python -c "from chemsim.engine.shelf_data import SHELF; print(len(SHELF))"` |
| the rate ceiling | clean at 298 K; coldest crossing still 417 K; T30's new bench crosses at 1895 K | `python validation/rate_ceiling.py` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| expensive checks | 0 of 5 due; `suite` and `tolerance` still stand RED from T28 with their reasons | `python tools/cadence.py` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, `CLAUDE.md`, `rate_ceiling.py`, the catalog PSVs and `physical_data.py` are CRLF; `check.ps1`, `tools/`, `tests/`, `docs/design/` are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T30 wrote the nitration row and the interesting part was the scoring. ONE class
grant moved two scoreboards by one, on two DIFFERENT routes, and neither route
moved on both: `COVERAGE_REPORT.md` counts every ROW, so `guncotton` went
template-ready; `PLAYABLE.md` walks a DAG to the TARGET, so
`nitroglycerin-route` went runnable off step 1 alone and never needed its
uncovered `formulation` step. The class had been priced +1 (§8, on the wrong
route), +0 (§8b, correctly) and +2 (the greedy queue, conditional on its own
row 8 granting `formulation` first). `guncotton` is now blocked only on
`nitrocellulose-unit`'s price, which is a species job. Argued with its numbers
in `docs/design/two-refused-template-classes.md`.

## Do this now

1. **T31 — six red scoreboard pins, and they gate every suite run.**
   `test_fermentation`, `test_vanillin` and `test_vitriol` fail two apiece, on a
   clean tree, unchanged by T30 (re-measured today: the same 7 as HEAD, with
   `test_playable_levers` the seventh). They pin §8b counts that T3 and T2 moved.
   `test_playable`'s three were T30's and are re-pinned already, so these six are
   all that is left of the scoreboard debt.
   *Done when:* each is green or re-pinned with the reason its number moved.
   Confirming needs the full suite (~30 min) -- **ask the user first**; the four
   pin files alone take 133 s and are enough to do the work.

2. **T32 — `needs()` hands a route its own TARGET as a starting charge.** Spec in
   `BACKLOG.md`, found by T30. `test_playable_levers` now asks for
   `nitroglycerin` on the shelf, and it must not be given: the catalyst union
   reads a no-op formulation step. The candidate rule and its two documented
   counterexamples are written out. Do this BEFORE T29, which is the same test.
   *Done when:* `nitroglycerin` leaves that work order without a shelf row, and
   every pin the change moves is re-pinned with its reason.

3. **T2c — promote one literal row to `family`.** Unchanged and still the cheap
   playable route; granting all 58 extracted rows would take runnable 51 -> 61.
   T2d gates it: the gate compares canonical SMILES, so it cannot see a mapping
   that is wrong on a symmetric product. Check the mapping by hand, argue the
   barrier, move the row.
   *Done when:* one class moves tier and `PLAYABLE.md`'s headline moves with it.

## Decisions already taken — do not reopen

- **A class grant is priced differently by each scoreboard, and both are right.**
  The row scorer wants every ROW covered; `route_reachable` wants one DAG path to
  the TARGET. Quote whichever answers the question you are asking, and never
  average them.
- **A greedy set-cover queue's per-row gain is conditional on every row above
  it.** `COVERAGE_REPORT.md`'s +2 for `esterification-nitration` needed its own
  row 8 first. Reading one row as what a session buys double-counts.
- **`nitroglycerin` does not go on the shelf.** It is the route's own target; the
  bug is in `needs()`. That is T32.
- **A literal row is irreversible and declares no orders, no alpha, no rho.**
- **`PLAYABLE.md` scores the `family` tier and `COVERAGE_REPORT.md` every tier.**
  Both print the split.
- **173 is not the target.** Quote 66. **Change the rate, not the queue** --
  per-row pKa curation is real work and is not task 1.
- **A pinned count is not a guard**; **no species `build_network` registers may
  be unpriceable**; **backwards is retrosynthesis**; **a class names a
  mechanism, never an outcome**; **never declare what detailed balance derives**.

## Open questions for the user

- **The suite has been red for four commits now.** Seven tests, all scoreboard
  pins, none in the smoke set. T31 fixes six and T29/T32 the seventh. Still
  worth deciding whether `test_playable.py` joins `check.ps1` at +47 s, which
  would have caught every one of them -- and would have caught T30's three the
  moment they broke rather than because it went looking.
- **`shelf.psv` is hand-maintained game design** (T29). The audit asks for
  `ammonia` and `platinum`; giving a player either is a design call.
- **`CHANGELOG.md` is past the 400 lines its own header rolls at** (T33). Nothing
  enforces it, so it is a convention going stale rather than a red check.

## Do not

- Do not hand-edit `literal.psv`, `needs_review.psv`, `COVERAGE_REPORT.md`,
  `PLAYABLE.md`, `ROUTE_INDEX.md`, `*_data.py`, `reachable.psv`,
  `species_roles.psv`, `silent_templates.psv` or `template_products.psv`.
- Do not chase 173, re-derive the ceiling, make per-row pKa curation task 1,
  write a pKa you cannot source, or reopen the T2, T3, T28c or T30 decisions.
- Do not put a `literal` row in `templates.psv` or a `family` row in
  `literal.psv` -- the tier and the file are the same fact twice.
- Do not read `docs/history/` whole (grep it), add a physics module, stamp a
  cadence row you did not run, or rewrite a mixed-ending file whole.

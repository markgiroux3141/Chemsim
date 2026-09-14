# NEXT — overwritten 2026-09-14

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-14. The command is named. T31
touched only `tests/` and one glyph budget, so every chemistry number below is
last session's, re-typed with its command rather than re-measured.

| fact | value | command |
|---|---|---|
| **route coverage ceiling** | **110 template-ready, ~66 intersection. 173 is NOT the target** | the script in `docs/design/route-coverage-ceiling.md` |
| routes template-ready / species-ready / both | 66 / 95 / 53, and 50 / 95 / 43 on hand-typed rows alone | `python validation/catalog_coverage.py` |
| routes runnable / playable | **51** / 23 -- `PLAYABLE.md` scores the `family` tier ALONE, on purpose | `data/catalog/PLAYABLE.md` footer |
| the same two granting the extracted rows | 61 / 25 | same file, the note under §1 |
| corpus species no provider prices | 401 of 1,583 | `python validation/catalog_coverage.py` |
| templates | 126 rows: 68 `family` hand-typed, 58 `literal` extracted; 103 catalog classes | `python tools/build_templates.py --check` |
| reaction classes with a template | 116 of 240, 64 of them a family row | `python validation/catalog_coverage.py` |
| template rows against their catalog step | 96 pass, 16 partial, 9 wrong-product, 3 no-substrate, 2 no-class over 282 steps | `python tools/check_template_products.py` (4 s) |
| steps the extractor refused | 175 of 233: 75 salt, 35 stoichiometry, 23 stereo, 20 coefficients, 10 no-graph, 5 closed-cycle, 4 centre, 3 duplicate | `data/templates/needs_review.psv` footer |
| tests | 1,360 collected; **the five scoreboard pin files are 1 FAIL / 104 pass** (135 s), down from 7 FAIL. The survivor is `test_playable_levers`, which is T32 | `python -m pytest -q` on the five pin files |
| the full suite | **not run since T28 (2 commits), where it was 7 FAIL / 1,353 pass in 29m48s.** Six of those 7 are fixed; nothing re-measured the other 1,353 | `python -m pytest -q`, ~30 min, ASK FIRST |
| fast check | `./check.ps1`, ~95 s, green, 88 smoke tests | ruff + docs + catalog + extracted + templates + template products + silent + smoke |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| why templates are silent | 30: 20 no-substrate, 10 needs-more-than-a-pair, 0 cannot-fire; `pool_species` 325, shelf closure 50 at frontier 0 | `python tools/classify_silent.py` (2 s) |
| the shelf sweep | 666 pairs, 23,140 distinct reactions, 37 of 67 templates fire, 0 crashed, 1,254 s | `data/catalog/derived/reachable.psv` footer (NOT re-run today) |
| pKa table / ions derived | 41 `AcidPair` rows, 43 ions priced | unchanged since T28 |
| the shelf | 72 rows: 43 natural, 25 intermediate, 4 bottle | `python -c "from chemsim.engine.shelf_data import SHELF; print(len(SHELF))"` |
| the rate ceiling | clean at 298 K; coldest crossing still 417 K; T30's bench crosses at 1895 K | `python validation/rate_ceiling.py` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| expensive checks | 0 of 5 due; `suite` and `tolerance` still stand RED from T28 with their reasons | `python tools/cadence.py` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, `CLAUDE.md`, `tools/check_docs.py`, `rate_ceiling.py`, the catalog PSVs and `physical_data.py` are CRLF; `check.ps1`, `tests/`, `docs/design/` are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T31 made the six red pins green and four of them turned out to be ONE defect,
not four drifts. T2 split `cc.TEMPLATE_CLASSES` into an every-tier dict and
`FAMILY_TEMPLATE_CLASSES`; four test helpers kept the all-tier one while the
`bp.RUNNABLE` and `bp.PLAYABLE` they compared against are family, so each was
reading a LEVEL on one measurement path (25) against a SET on the other (23).
Every difference those tests pin is identical on both paths, which is why only
the levels broke. The two real moves are re-pinned with their reasons: T3's
`ketene_acid_addition` left `pyrolysis-dehydration` as
`acetic-anhydride-ketene`'s only gap, so §8b is 8 at +1; and T2's extractor
wrote an `oleum-hydrolysis` row, so 2 of the 8 hydrolysis classes are covered.

## Do this now

1. **T32 — `needs()` hands a route its own TARGET as a starting charge.** Spec
   in `BACKLOG.md`, found by T30. `test_playable_levers` asks for
   `nitroglycerin` on the shelf and must not be given it: `route_roles` calls a
   species on both sides of a step a catalyst, so the no-op kieselguhr step asks
   for the thing the route exists to make. The candidate rule
   (`first_made < first_used` is not a charge) and its two counterexamples are
   written out. This is also the last of the seven suite failures, so it is what
   makes a full suite green again.
   *Done when:* `nitroglycerin` leaves that work order without a shelf row, and
   every pin the change moves is re-pinned with its reason.

2. **T2c — promote one literal row to `family`.** Still the cheap playable
   route: granting all 58 extracted rows would take runnable 51 -> 61, so each
   promotion is a route rather than a template written from nothing. T2d gates
   it -- the gate compares canonical SMILES, so it cannot see a mapping that is
   wrong on a symmetric product. Check the mapping by hand, argue the barrier,
   move the row.
   *Done when:* one class moves tier and `PLAYABLE.md`'s headline moves with it.

3. **T33 — `CHANGELOG.md` is 428 lines, past the 400 its own header rolls at.**
   Nothing enforces it (`check_docs.py` caps an ENTRY, not the file). A
   whole-file move, CRLF, older half into `docs/history/changelog-2026-09.md`.
   *Done when:* under 400 lines and `./check.ps1` green.

## Decisions already taken — do not reopen

- **`bp.RUNNABLE`/`bp.PLAYABLE` are the `family` path and `COVERAGE_REPORT.md`
  is every tier.** A test comparing a level against either of them must use
  `cc.FAMILY_TEMPLATE_CLASSES`. The two dicts were equal before T2, so any
  helper written before it is suspect by default.
- **A test that pins a claim about a difference must assert the difference.**
  Every level in the vanillin and fermentation pair tests moved; not one
  difference did.
- **A class grant is priced differently by each scoreboard, and both are right.**
  The row scorer wants every ROW covered; `route_reachable` wants one DAG path
  to the TARGET. Never average them.
- **A greedy queue's per-row gain is conditional on every row above it**, which
  is also how a session can re-price a class it never touched.
- **`nitroglycerin` does not go on the shelf.** That is T32.
- **A literal row is irreversible and declares no orders, no alpha, no rho.**
- **173 is not the target.** Quote 66. **Change the rate, not the queue** --
  per-row pKa curation is real work and is not task 1.
- **A pinned count is not a guard**; **no species `build_network` registers may
  be unpriceable**; **backwards is retrosynthesis**; **a class names a
  mechanism, never an outcome**; **never declare what detailed balance derives**.

## Open questions for the user

- **The full suite has not run since T28 and six of its seven failures are now
  fixed, unverified.** T32 fixes the seventh. Worth one ~30 min run after T32
  lands, and worth deciding whether `test_playable.py` joins `check.ps1` at
  +47 s -- it would have caught all seven the commit they broke.
- **`shelf.psv` is hand-maintained game design** (T29). The audit asks for
  `ammonia` and `platinum`; giving a player either is a design call.

## Do not

- Do not hand-edit `literal.psv`, `needs_review.psv`, `COVERAGE_REPORT.md`,
  `PLAYABLE.md`, `ROUTE_INDEX.md`, `*_data.py`, `reachable.psv`,
  `species_roles.psv`, `silent_templates.psv` or `template_products.psv`.
- Do not chase 173, re-derive the ceiling, make per-row pKa curation task 1,
  write a pKa you cannot source, or reopen the T2, T3, T28c, T30 or T31
  decisions.
- Do not put a `literal` row in `templates.psv` or a `family` row in
  `literal.psv` -- the tier and the file are the same fact twice.
- Do not read `docs/history/` whole (grep it), add a physics module, stamp a
  cadence row you did not run, or rewrite a mixed-ending file whole.

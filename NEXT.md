# NEXT — overwritten 2026-09-15

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-15 unless the row says
otherwise. T32 touched only the two catalog scorers, one shelf row and six
pins, so every chemistry number is last session's, re-typed with its command.

| fact | value | command |
|---|---|---|
| **route coverage ceiling** | **110 template-ready, ~66 intersection. 173 is NOT the target** | the script in `docs/design/route-coverage-ceiling.md` |
| routes template-ready / species-ready / both | 66 / 95 / 53, and 50 / 95 / 43 on hand-typed rows alone | `python validation/catalog_coverage.py` |
| routes runnable / playable | **51** / 23 -- `PLAYABLE.md` scores the `family` tier ALONE, on purpose | `data/catalog/PLAYABLE.md` footer |
| fed but unrunnable / the ceiling it implies | **24 / 52**, both moved by T32 and by no chemistry | same file, §8 and its last section |
| corpus species no provider prices | 401 of 1,583 | `python validation/catalog_coverage.py` |
| templates | 126 rows: 68 `family` hand-typed, 58 `literal` extracted; 103 catalog classes | `python tools/build_templates.py --check` |
| reaction classes with a template | 116 of 240, 64 of them a family row | `python validation/catalog_coverage.py` |
| template rows against their catalog step | 96 pass, 16 partial, 9 wrong-product, 3 no-substrate, 2 no-class over 282 steps | `python tools/check_template_products.py` (4 s) |
| tests | **1,361 collected; the full suite is 1 FAIL / 1,360 pass in 29m51s**, from T28's 7 / 1,353. The survivor is T29 | `python -m pytest -q`, ~30 min, ASK FIRST |
| fast check | `./check.ps1`, ~95 s, green, 88 smoke tests | ruff + docs + catalog + extracted + templates + template products + silent + smoke |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| why templates are silent | 30: 20 no-substrate, 10 needs-more-than-a-pair, 0 cannot-fire; `pool_species` 325, shelf closure 50 at frontier 0 | `python tools/classify_silent.py` (2 s) |
| the shelf sweep | 666 pairs, 23,140 distinct reactions, 37 of 67 templates fire, 0 crashed, 1,254 s | `data/catalog/derived/reachable.psv` footer (NOT re-run today) |
| pKa table / ions derived | 41 `AcidPair` rows, 43 ions priced | unchanged since T28 |
| the shelf | **71 rows: 43 natural, 24 intermediate, 4 bottle** (T32 deleted `sodium-stearate`) | `python tools/build_shelf.py`, or `len(SHELF)` from `chemsim.engine.shelf_data` |
| the rate ceiling | clean at 298 K; coldest crossing still 417 K | `python validation/rate_ceiling.py` (NOT re-run today) |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| expensive checks | **0 of 5 due.** `suite` recorded RED today with its reason (it is T29); `tolerance` still stands RED from T28 | `python tools/cadence.py` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, `CLAUDE.md`, `tests/test_shelf.py`, the catalog PSVs and `physical_data.py` are CRLF; `check.ps1`, most of `tests/`, `tools/`, `docs/design/` are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T32: `needs()` unioned `route_roles().catalysts` in, and a catalyst is derived
by IDENTITY not order, so four routes making their target in one row and eating
it in the next asked the player to hold it -- which `route_reachable` forbids
one layer down, so the two instruments contradicted each other. `route_reachable`
then proved to have the mirror defect: `made_by` let a no-op row make its own
input, scoring `dissolution` +3 atop the C-series ranking on a row that moves no
atoms. Both fixed, no verdict moved, and the work order grew instead: 23 -> 24
fed, ceiling 50 -> 52. A three-session finding flipped with it -- `nickel` is now
both the most frequent blocker and the most valuable grant (+3), because
hardening fat feeds soap feeds the glycerol that nitrates.

## Do this now

1. **T29 -- `ammonia` and `platinum`, the last red test, and it is a design
   call.** Spec in `BACKLOG.md`; the ONLY failure in the suite. T32 closed the
   scorer half, so what remains is real: `andrussow`'s platinum and
   `tollens-test`'s ammonia are same-step catalysts nothing in the corpus makes.
   `shelf.psv` is hand-maintained game design; its header already argues seven
   unpriceable natural rows into staying, and `build_playable`'s
   `NOT_NATURAL_NOTES` calls the catalyst metals the rule that decides the third
   tier. Argue it either way IN THE FILE.
   *Done when:* each species is a shelf row with a note or is argued down in
   `shelf.psv`'s header, and `pytest tests/test_playable_levers.py` is green.

2. **T2c -- promote one literal row to `family`.** Still the cheap playable
   route: granting all 58 extracted rows would take runnable 51 -> 61, so each
   promotion is a route rather than a template written from nothing. T2d gates
   it -- the gate compares canonical SMILES, so it cannot see a mapping that is
   wrong on a symmetric product. Check the mapping by hand, argue the barrier,
   move the row.
   *Done when:* one class moves tier and `PLAYABLE.md`'s headline moves with it.

3. **T33 -- `CHANGELOG.md` is past the 400 lines its own header rolls at.**
   Nothing enforces it (`check_docs.py` caps an ENTRY, not the file). A
   whole-file move, CRLF, older half into `docs/history/changelog-2026-09.md`.
   *Done when:* under 400 lines and `./check.ps1` green.

## Decisions already taken — do not reopen

- **A route may never be charged with its own target, and the rule is ORDER.**
  `bayer-process` and `contact-process` ARE primed with theirs, correctly: both
  want it before anything makes it, like `lead-chamber`'s NO2. The four T32
  closed made theirs first. `test_no_route_is_charged_with_its_own_target` pins
  it over all 173 routes, not the four that showed it.
- **A no-op row does not make its own input.** `made_by` skips a step carrying
  the species on both sides: costs nothing today, stops a formulation row
  fabricating a target.
- **A generated file must COMPUTE a comparison, not hard-code which way it came
  out.** §7's "the frequent blocker is not the most valuable" was prose with the
  numbers filled in, and went stale behind its own table.
- **`bp.RUNNABLE`/`bp.PLAYABLE` are the `family` path and `COVERAGE_REPORT.md`
  is every tier.** A test comparing a level against either must use
  `cc.FAMILY_TEMPLATE_CLASSES`.
- **A test that pins a claim about a difference must assert the difference.**
- **A class grant is priced differently by each scoreboard, both right; never
  average them.** A greedy queue's per-row gain is conditional on the rows above.
- **A literal row is irreversible and declares no orders, no alpha, no rho.**
- **173 is not the target.** Quote 66. **Change the rate, not the queue** --
  per-row pKa curation is real work and is not task 1.
- **A pinned count is not a guard**; **no species `build_network` registers may
  be unpriceable**; **backwards is retrosynthesis**; **a class names a
  mechanism, never an outcome**; **never declare what detailed balance derives**.

## Open questions for the user

- **T29 is a game-design call and it is task 1**, bending the rule that a user
  decision is not a task: either answer is defensible and writing the argument
  down IS the work. Take the steer if one is offered, otherwise decide and
  record the reasoning in `shelf.psv`.
- **`validation/tolerance_audit.py` has stood RED since T28**, same three
  pre-existing findings. Nothing since touched `numerics/`, `vessel/` or
  `network/`, so it is not owed -- but it has never been green.
- **Should `test_playable.py` join `check.ps1` at +47 s?** It would have caught
  all seven of T28's failures, and T32's bug, the commit they broke.

## Do not

- Do not hand-edit `literal.psv`, `needs_review.psv`, `COVERAGE_REPORT.md`,
  `PLAYABLE.md`, `ROUTE_INDEX.md`, `*_data.py`, `reachable.psv`,
  `species_roles.psv`, `silent_templates.psv` or `template_products.psv`.
- Do not chase 173, re-derive the ceiling, make per-row pKa curation task 1,
  write a pKa you cannot source, or reopen T2, T3, T28c, T30, T31 or T32.
- Do not put a `literal` row in `templates.psv` or a `family` row in
  `literal.psv` -- the tier and the file are the same fact twice.
- Do not read `docs/history/` whole (grep it), add a physics module, stamp a
  cadence row you did not run, or rewrite a mixed-ending file whole.

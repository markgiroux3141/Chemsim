# NEXT — overwritten 2026-09-16

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-16. T33 moved only documents
and three generated artefacts; no template, price, species or trajectory moved.

| fact | value | command |
|---|---|---|
| **route coverage ceiling** | **110 template-ready, ~66 intersection. 173 is not the target** | the script in `docs/design/route-coverage-ceiling.md` |
| routes template-ready / species-ready / both | 66 / 95 / 53, and 50 / 95 / 43 on hand-typed rows alone | `python validation/catalog_coverage.py` |
| routes runnable / playable | 51 / 23 -- `PLAYABLE.md` scores the `family` tier alone, on purpose | `data/catalog/PLAYABLE.md` footer |
| fed but unrunnable / the ceiling it implies | 24 / 52 | same file, section 8 and its last section |
| granting the whole shelf work order | 23 -> 51 playable, which is every runnable route | `tests/test_playable_levers.py` |
| **granting all 58 extracted rows** | **runnable 51 -> 61, playable 23 -> 25** -- this is T2c's lever | `bp.RUNNABLE_WITH_LITERAL`, measured today |
| corpus species no provider prices | 401 of 1,583 | `python validation/catalog_coverage.py` |
| templates | 126 rows: 68 `family` hand-typed, 58 `literal` extracted; 103 catalog classes | `python tools/build_templates.py --check` |
| reaction classes with a template | 116 of 240, 64 of them a family row | `python validation/catalog_coverage.py` |
| template rows against their catalog step | 96 pass, 16 partial, 9 wrong-product, 3 no-substrate, 2 no-class over 282 steps | `python tools/check_template_products.py` (4 s) |
| **tests** | **1,361 collected, 1,361 passed, 0 failed in 33m00s. The first wholly green full run on record** | `python -m pytest -q`, ~33 min, ASK FIRST |
| fast check | `./check.ps1`, ~95 s, green, 88 smoke tests | ruff + docs + catalog + extracted + templates + template products + silent + smoke |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| why templates are silent | 31: 21 no-substrate, 10 needs-more-than-a-pair, 0 cannot-fire | `python tools/classify_silent.py` (2 s) |
| the shelf sweep | 666 pairs, 23,140 reactions, 37 of 68 templates fire, 1,242 s. Fresh today | `derived/reachable.psv` footer |
| pKa table / ions derived | 41 `AcidPair` rows, 43 ions priced | unchanged since T28 |
| the shelf | 75 rows: 43 natural, 21 intermediate, 11 bottle | `python tools/build_shelf.py`, or `len(SHELF)` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| expensive checks | **0 of 5 due, and 3 of 5 ran today.** `suite` is green, `reachable` is fresh, `tolerance` stands red on the same three findings for a fourth run | `python tools/cadence.py` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, `CLAUDE.md`, `tools/check_docs.py`, `tests/test_shelf.py`, the catalog PSVs and `physical_data.py` are CRLF; `check.ps1`, most of `tests/`, `tools/`, `docs/design/` are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T33 rolled `CHANGELOG.md` 458 -> 253 lines, 14 entries into
`docs/history/changelog-2026-09.md`, and turned its 400 from a sentence in its
own header into a cap in `check_docs.py`. Then all three slow checks at the
user's ask. The suite is wholly green for the first time. The tolerance audit is
identical to T28 to the digit, so nothing in T29-T32 moved a trajectory. The
sweep found every pair unchanged -- T29's four new shelf rows are `bottle` tier
and the sweep charges only the 37 natural ones -- but regenerating it exposed
two artefacts wrong since T30: `silent_templates.psv` said 30 silent templates
against 31 and `COVERAGE_REPORT.md` said 67 templates against 68. Both derive
those numbers, so both followed the sweep. The finding is T34.

## Do this now

1. **T2d -- the promotion gate cannot see a wrong mapping.** Gates T2c, so it
   comes first. Verification compares canonical SMILES, the engine's own
   identity, so a symmetric product hides a mis-mapping: the Diels-Alder row
   joins the ring at the wrong carbons and still writes cyclohexene, and the
   Lebedev row joins its two ethanols at a pair the mechanism does not. Re-run
   each row on one substituted analogue and report where it lands.
   *Done when:* the count of rows their own step does not constrain is
   measured, or the idea is refused in writing.

2. **T2c -- promote one literal row to `family`.** Still the cheap playable
   route, and the lever is now measured rather than quoted: granting all 58
   extracted rows takes runnable 51 -> 61 and playable 23 -> 25. Check the
   mapping by hand (T2d), argue the barrier, move the row into `templates.psv`.
   *Done when:* one class moves tier and `PLAYABLE.md`'s headline moves with it.

3. **T34 -- nitric acid is the only substrate blocking two templates.** Found
   today. `[OX2H1][N+](=[O])[O-]` reads `2 blocked, 2 alone` at the top of
   `silent_templates.psv`'s work order, where every other row is 1 and 1, and
   T30's `nitrate_esterification` has never fired from the shelf. The corpus
   makes nitric acid, so the question is the tier, not the price.
   *Done when:* the slot is off the work order and `classify_silent.py` reports
   29 silent, or the tier argument is refused in writing.

## Decisions already taken — do not reopen

- **`CHANGELOG.md` has a 400-line cap in `check_docs.py`, and it bites.**
  At the cap, roll whole entries into `docs/history/changelog-YYYY-MM.md`,
  CRLF both sides. The `handoff` skill names the procedure in its Step 7.
- **A generated artefact that derives its numbers repairs itself; one that
  declares them does not.** A stale sweep made two files lie and a current one
  fixed both with no edit. Rule 5: commit input and output together.
- **The sweep charges natural shelf rows only.** Adding a `bottle` or
  `intermediate` row cannot move it, so the shelf growing is not, by itself,
  a reason to spend 35 minutes re-running it.
- **A species the corpus writes on both sides of a step is not made by it.**
  In all three instruments. A catalyst is bought, never earned.
- **The four catalyst metals are `bottle` rows.** `nickel`, `cobalt`,
  `palladium`, `platinum`. `test_shelf.py` pins the four by name.
- **A shelf tier is a question about a species, not its route.**
- **A route may never be charged with its own target, and the rule is order.**
- **`bp.RUNNABLE`/`bp.PLAYABLE` are the `family` path and `COVERAGE_REPORT.md`
  is every tier.** A test comparing a level must use `cc.FAMILY_TEMPLATE_CLASSES`.
- **A test that pins a level gets re-numbered; pin the relation too.**
- **A literal row is irreversible and declares no orders, no alpha, no rho.**
- **173 is not the target.** Quote 66. **Change the rate, not the queue** --
  per-row pKa curation is real work and is not task 1.
- **A pinned count is not a guard**; **no species `build_network` registers may
  be unpriceable**; **backwards is retrosynthesis**; **a class names a
  mechanism, never an outcome**; **never declare what detailed balance derives**.

## Open questions for the user

- **T0.4 is one flag away from free.** It needs per-test timings, which means a
  30-minute suite run, and today's was made without `--durations=0`. Add that
  flag to the next full suite and T0.4 costs nothing extra.
- **The tolerance audit has now stood red for four runs with identical digits**
  (activity 0.1277%, multistep_prep 0.1073%, named_routes raises at rtol 1e-8).
  It is stable pre-existing debt, T10 owns the fix, and it has never once been
  green. Worth deciding whether T10 is ever going to be done.
- **Nothing is due:** four more commits owe the suite, ten owe the sweep.

## Do not

- Do not hand-edit `literal.psv`, `needs_review.psv`, `COVERAGE_REPORT.md`,
  `PLAYABLE.md`, `ROUTE_INDEX.md`, `*_data.py`, `reachable.psv`,
  `species_roles.psv`, `silent_templates.psv` or `template_products.psv`.
- Do not chase 173, re-derive the ceiling, make per-row pKa curation task 1,
  write a pKa you cannot source, or reopen T2, T3, T28c, T29, T30, T31 or T33.
- Do not put a `literal` row in `templates.psv` or a `family` row in
  `literal.psv`, and do not edit `shelf.psv` against the playable audit -- the
  test prints the work order and the file follows it.
- Do not read `docs/history/` whole (grep it), append to anything in it, add a
  physics module, stamp a cadence row you did not run, or rewrite a mixed file.

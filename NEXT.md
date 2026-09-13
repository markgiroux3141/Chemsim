# NEXT — overwritten 2026-09-13

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-13. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,329 collected, unmoved -- T17 re-measured nine pins and added none. No red test known today | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~85 s, green | ruff + docs + catalog + templates + silent + 62 smoke tests |
| expensive checks owed | `suite` DUE at 9 commits, NOT run; `tolerance` DUE at 9, NOT run. `playable` re-derives from this commit, `routes` ok at 3, `reachable` ok at 5 | `python tools/cadence.py` |
| templates | 59 rows, all `tier=family`, covering 46 catalog classes -- unmoved | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps -- unmoved | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 89 / 40 -- unmoved | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 23, three tiers deep (10 / 12 / 1); 46 runnable, 23 fed but unrunnable, ceiling 50 | `data/catalog/PLAYABLE.md` footer |
| the shelf | 70 rows, 43 natural / 23 intermediate / 4 bottle | `data/catalog/shelf.psv`, `python tools/build_shelf.py` |
| pKa table | 33 `AcidPair` rows -- unmoved | `len(electrolyte.known_pairs())` |
| carboxylic pairs the table is short of | 624 distinct, 12 priced. 270 inside the plateau domain, 243 of them oligomers of one acid; 342 need their own measurement | `python validation/fatty_acid_pka.py` (118 s) |
| the plateau itself, from C3 up | 4.87 to 5.02, derived from `_PAIRS` and not asserted | the same command, panel 0 |
| why templates are silent | 16 no-substrate, 8 needs-more-than-a-pair, 0 cannot-fire -- unmoved | `python tools/classify_silent.py` (31 s) |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs, `shelf_data.py`, `inventory.py`, `validation/catalog_coverage.py` are CRLF; `tools/build_playable.py` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T17 found the playability scorer crediting a route with its *declared* output.
`needs` has read step order since G4, but `shelves` read `route_roles.products`,
which drops whatever a route makes and later consumes -- so `lime-cycle` could be
run without holding slaked lime and earn no credit for the slaked lime row 2
makes, leaving `bleaching-powder` chain-blocked behind a test red for three
sessions. Every step product is credited now: playable 22 -> 23, ceiling 46 -> 50,
`copper-ii-oxide` earned off the roaster and its shelf row deleted. Nothing was
built and nine pinned scoreboards moved: that is what an instrument fix costs.

## Do this now

1. **T18 - write the carboxylic plateau as a rule.** Spec in `BACKLOG.md`, shape
   decided by T14. Move `validation/fatty_acid_pka.py:domain` under
   `properties/` and give `ion_thermochemistry` a fallback consulted after
   `_PAIRS` misses, at 4.87 to 5.02. It must report itself through `notices`: a
   derived pKa is not a measured one and rule 10 says the player has to see
   which they got. This continues the route-unblocking arc of T8/T12/T14 -- an
   unpriced acid is what stops a species-ready route running.
   *Done when:* a stearate prices with no hand-typed row, the notice names the
   rule and its domain, and the audit reports the plateau bucket as covered.

2. **T13 - an unpriced ion in the flask still stops `to_arrays`.** Spec in
   `BACKLOG.md`. T8 guarded the builder, so `build_network` reports and carries
   on; `to_arrays` still raises on the same flask, so a network can be built,
   reported and un-runnable, and the player hears one call later than the
   notice. Decide which half moves -- drop the species at registration and say
   the flask lost matter, or refuse the way the builder reports -- not by taste.
   *Done when:* a network holding an unpriced ion either integrates or refuses
   with a notice naming the species, and one test pins whichever was chosen.

3. **T16 - the other loose sulfur-dioxide slot.** Spec in `BACKLOG.md`.
   `sulfur_dioxide_oxidation_by_nitrogen_dioxide` still writes SO2 as
   `[O:1]=[S:2]=[O:3]`, which matches a sulfate, and two shelf rows are sulfates.
   Three slots rather than eight, so it is wasted work per flask and not the
   16-minute bomb T12 defused. It is chain 2's carrier step, so the tolerance
   audit is owed with it and the Ea/A must not move.
   *Done when:* the slot matches one shelf species and
   `tests/test_lead_chamber.py` is green with the same numbers.

The suite (~29 min) and the tolerance audit (~11 min) are owed and were not run
here. T17 changed no rate and no thermochemistry -- the deep chain's digits are
byte-identical -- but it deleted a shelf row, so the untested remainder is
bounded by the six files importing the scorer plus `test_shelf`,
`test_template_table`, `test_protocol`, `test_dropping_funnel` and
`test_wait_until`, all green today. `reachable.psv` is stale by input (57
templates over 36 natural rows; now 59 and 37), so `templates_fired = 33` is a
floor.

## Decisions already taken — do not reopen

- **A route is credited with every step product, never with `route_roles`.** A
  step boundary is where a player can stop: the corpus's steps carry their own
  conditions and vessel, so a step's products are real material whether or not a
  later step eats them. `needs` and `shelves` are mirrors; both read step order.
- **An `intermediate` shelf row is deleted the day a reachable route makes it**,
  which is what lets the shelf shrink. The scoreboard decides it, not taste.
- **A ratio pinned in a test is a guard rail, not a finding.** P0's "templates
  alone are under half the ceiling" is 14 of 26 since the shelf rule was
  corrected; the finding is super-additivity, and it widened.
- **The carboxylic plateau is a rule, not rows,** and the pool is the argument:
  243 of the 270 pairs in its domain are oligomers of one self-esterifying acid.
- **A pKa domain is local and its exclusions are chemistry**: a basic nitrogen
  anywhere makes the molecule a zwitterion and a different acid. **A carboxylate
  salt is priced as its ion**, **a proton-transfer row is written
  protonation-first**, and **no pKa is in `chemicals`**.
- **A rock's Ksp decides whether its shelf row is matter or scenery**, and acid
  shifts that equilibrium, never the rate. **A disputed constant is a subtraction
  when two rows of one table bracket it.**
- **Backwards is retrosynthesis and must be forbidden to build up.**
- **The expensive checks are clocked in commits.** **The headline is templates
  fired, not reactions reached.** **`discovery/refine.py` is deleted, not
  wired**; **the README stays at 561 lines** until C1.

## Open questions for the user

- **The suite, the audit and a fresh `reachable.psv`** cost ~75 minutes, and six
  sessions have deferred the first two. T17 is the evidence of the cost: a red
  test lived through three of them, being none of the 62 smoke tests.
- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is. Without it T2 needs an RDKit-only mapper.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure and a pyrrhotite flask both make it -- but no catalog route does, and
  the tier's rule reads routes.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `*_data.py`, `reachable.psv`, `species_roles.psv` or `silent_templates.psv`.
- Do not write a reactant slot more than twice without checking what else it
  matches on the shelf; `tests/test_template_table.py` fails you for it.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, and do not clear a red one.
- Do not rewrite a mixed-ending file whole; read and write bytes.

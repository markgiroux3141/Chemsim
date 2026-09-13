# NEXT — overwritten 2026-09-13

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-13. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,338 collected, unmoved -- T13 restated two rather than adding any | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~85 s, green | ruff + docs + catalog + templates + silent + 62 smoke tests |
| expensive checks owed | `suite` and `tolerance` both DUE at 10 commits when measured, 11 after this one, neither run; `routes` re-run today and recorded pass; `playable` and `reachable` ok | `python tools/cadence.py` |
| templates | 59 rows, all `tier=family`, covering 46 catalog classes -- unmoved | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps -- unmoved | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 90 / 40 -- unmoved, and the report regenerates byte-identical | `python validation/catalog_coverage.py` |
| routes runnable / playable | 47 runnable, 23 playable, three tiers deep (10 / 12 / 1); 23 fed but unrunnable, ceiling 50 -- regenerates byte-identical | `python tools/build_playable.py` (44 s) |
| the shelf | 72 rows, 43 natural / 25 intermediate / 4 bottle | `data/catalog/shelf.psv` |
| pKa table | 33 `AcidPair` rows -- unmoved | `len(electrolyte.known_pairs())` |
| why templates are silent | 16 no-substrate, 8 needs-more-than-a-pair, 0 cannot-fire -- unmoved. `pool_unpriceable` 41 -> 0 and `step_frontier` 306 -> 265, which is T13 | `python tools/classify_silent.py` (31 s) |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs, `builder.py` and `tests/test_robustness.py` are CRLF; `carboxylic_pka.py`, `validation/` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T13 closed the gap between a network that reports and a network that runs.
`vessel.build_phase_arrays` prices every species for heat capacity and molar
volume before a reaction is looked at, so an unpriceable species makes a flask
un-integrable whatever its reactions are: `_unpriceable` now drops one
unconditionally (T1d's `uses_thermochemistry` condition asked the templates, the
wrong half of the engine) and `_refuse_unpriceable_feed` refuses a CHARGED one at
`build_network`'s door. No route pays -- playable, coverage and the 17 named
routes all regenerate byte-identical.

## Do this now

1. **Ask the user to run the suite, then run it.** `python -m pytest -q`, ~29
   min on their own machine, 11 commits owed, and T13 is exactly the change that
   makes it worth it: it REVERSED a decision two tests pinned, and one of those
   two had been red since T18 with `./check.ps1` green over it. 14 modules were
   run green by hand (371 tests) -- robustness, furans, born, fatty_acid_pka,
   gas_processes, protonation, solid_state, vanillin, shelf, playable,
   named_routes, detailed_balance, solids_and_ions, granularity -- so the risk
   is a module none names. If the user is not there to ask, skip to 2.
   *Done when:* the run is recorded with `python tools/cadence.py --record suite`,
   pass or fail, and a failure names its module in `NEXT.md`.

2. **T5 - measure what the 33-row pKa table still bounds.** Spec in `BACKLOG.md`.
   T13 raised its value: an unpriceable ion used to ride along in a network and
   now takes its rewrite with it, so the pKa table gates what the engine can
   BUILD and not only what it can integrate -- 41 species and 41 frontier entries
   went with it today. The phenoxide is candidate and warning both: `_PAIRS`
   carries two phenols at 9.95 and 10.19, against the carboxylic plateau's
   measured 0.15-unit spread. Copy `validation/fatty_acid_pka.py`'s shape; do not
   write a pKa first.
   *Done when:* the count and its top classes are in this table with the command,
   and a follow-up names the fix the number argues for, refusal included.

3. **T16 - the other loose sulfur-dioxide slot.** Spec in `BACKLOG.md`.
   `sulfur_dioxide_oxidation_by_nitrogen_dioxide` still writes SO2 as
   `[O:1]=[S:2]=[O:3]`, which matches a sulfate, and two shelf rows are sulfates.
   Three slots rather than eight, so it is wasted work per flask and not the
   16-minute bomb T12 defused. Tighten it to `[OX1]=[SX2]=[OX1]` as T12 did for
   the Claus row. Chain 2's carrier step, so the audit is owed and Ea/A must not
   move.
   *Done when:* the slot matches one shelf species and
   `tests/test_lead_chamber.py` is green with the same numbers.

The tolerance audit (~11 min) is owed and was not run. T13 cannot move a
trajectory, measured rather than argued: every flask it changes is one that
raised at `to_arrays` before, so no flask that ran runs differently -- the 17
named routes print byte-identical output on pre-T13 and post-T13 source once the
stamps are stripped. `reachable.psv` is stale and `templates_fired = 33` a floor.

## Decisions already taken — do not reopen

- **No species `build_network` registers may be unpriceable**, and the two halves
  of that are opposite on purpose: what the TEMPLATES make is dropped with a
  notice naming it, what the CALLER charges is a refusal naming it. Dropping a
  charged species would delete matter the player put in the flask; keeping an
  unpriceable one builds a flask no integrator can accept. **The half of the
  engine to ask was the vessel, not the templates** -- `build_phase_arrays` needs
  a heat capacity and a molar volume for every species, which is why
  `tmpl.uses_thermochemistry` was the wrong question.
- **A pKa the engine derived is not a pKa it measured, and the player sees which**
  (`electrolyte.PLATEAU_RULE`); **the rule is consulted AFTER the curated table
  and BEFORE the refusal**; **the plateau value is derived from `_PAIRS`, never
  typed**; **a graph edit belongs to `matter`**.
- **A route is credited with every step product, never with `route_roles`**, and
  **an `intermediate` shelf row is deleted the day a reachable route makes it**
  and ADDED the day a route becomes runnable with nothing to feed it. **A ratio
  pinned in a test is a guard rail, not a finding**, and **the plateau is a rule,
  not rows**.
- **A pKa domain is local and its exclusions are chemistry**; **a carboxylate
  salt is priced as its ion**; **no pKa is in `chemicals`**; **a rock's Ksp
  decides whether its shelf row is matter or scenery**, acid shifting that
  equilibrium and never the rate; **backwards is retrosynthesis**.
- **The expensive checks are clocked in commits**, **the headline is templates
  fired, not reactions reached**, **`discovery/refine.py` is deleted, not wired**
  and **the README stays at 561 lines** until C1.

## Open questions for the user

- **The suite, the audit and a fresh `reachable.psv`** cost ~75 minutes, and
  eight sessions have now deferred the first two. T17 and T18 are both evidence:
  each left a red test that lived through the next session's green `./check.ps1`.
- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is; without it T2 needs an RDKit-only mapper.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure and a pyrrhotite flask both make it, and no catalog route does.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `*_data.py`, `reachable.psv`, `species_roles.psv` or `silent_templates.psv`.
- Do not write a reactant slot more than twice without checking what else it
  matches on the shelf; `test_template_table.py` fails you for it.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, clear a red one, or rewrite a
  mixed-ending file whole -- read and write bytes.

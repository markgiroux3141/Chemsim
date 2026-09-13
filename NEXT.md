# NEXT — overwritten 2026-09-13

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-13. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,342 collected, 1,338 -> 1,342: T5's four | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~85 s, green | ruff + docs + catalog + templates + silent + 62 smoke tests |
| expensive checks owed | `suite` and `tolerance` both DUE, 12 commits after this one, neither run; `routes`, `playable`, `reachable` ok | `python tools/cadence.py` |
| templates | 59 rows, all `tier=family`, covering 46 catalog classes -- unmoved | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps -- unmoved | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 90 / 40 -- unmoved, nothing under `src/` changed today | `data/catalog/COVERAGE_REPORT.md` |
| routes runnable / playable | 47 runnable, 23 playable, ceiling 50 -- unmoved for the same reason | `data/catalog/PLAYABLE.md` |
| the shelf | 72 rows, 43 natural / 25 intermediate / 4 bottle | `data/catalog/shelf.psv` |
| pKa table | 33 `AcidPair` rows over 8 classes, 3 of them reachable by no template row | `python validation/pka_domains.py` panel 0 |
| ions the six ion rows reach from the corpus | 1,078, of which 1,030 unpriceable over 395 compounds; 451 want a pKa, 579 have no priceable parent | `python validation/pka_domains.py` (5 s) |
| the same sweep over the shelf | 46 ions, 39 unpriceable, and they come from FOUR compounds (35 are tannic acid) | same command, panel 2 |
| why templates are silent | 16 no-substrate, 8 needs-more-than-a-pair, 0 cannot-fire -- unmoved | `python tools/classify_silent.py` (31 s) |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs and `builder.py` are CRLF; `validation/` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T5 counted the pKa wall before writing a single pKa, the way T14 did for one
class. `validation/pka_domains.py` fires the six ion-producing template rows
themselves -- so the classes are the engine's rows, not a re-typed list of
functional groups -- and drives the corpus and the shelf to a fixpoint. The
count that matters is not 1,030 missing ions but the 451 whose neutral parent
the engine can already price; the other 579 would be skipped by
`ion_thermochemistry` the day a row was written. A phenol plateau rule is
refused, measured twice over, and the shelf half is three curated pairs.

## Do this now

1. **T23's shelf half -- the three pairs a player can actually reach.** Spec in
   `BACKLOG.md`. `python validation/pka_domains.py` panel 2 lists them: malonic
   acid (2.83 / 5.69), 4-nitrophenol (7.15) and coniferyl alcohol's phenol,
   whose value must be sourced or the row refused with its reason, never
   estimated. Tannic acid's 35 are a powerset over unpriced parents and are NOT
   three more rows -- write that half down as a bound. Curation rules are in the
   comments around `_PAIRS`: never mix two compilations inside one trend.
   *Done when:* panel 2's missing count is 35 or lower, `tools/build_playable.py`
   is regenerated and any move is in the CHANGELOG, and `./check.ps1` is green.

2. **Ask the user to run the suite, then run it.** `python -m pytest -q`, ~29
   min on their own machine, 12 commits owed and deferred nine sessions running.
   T17 and T18 each left a red test that lived through the next session's green
   `./check.ps1`, so the risk is a module no fast check names. Today's change
   cannot be the cause -- it adds a validation script and a test file and
   touches nothing under `src/` -- which makes this a good session to spend the
   half hour on the backlog rather than on a suspicion.
   *Done when:* the run is recorded with `python tools/cadence.py --record suite`,
   pass or fail, and a failure names its module here.

3. **T16 - the other loose sulfur-dioxide slot.** Spec in `BACKLOG.md`.
   `sulfur_dioxide_oxidation_by_nitrogen_dioxide` still writes SO2 as
   `[O:1]=[S:2]=[O:3]`, which matches a sulfate, and two shelf rows are
   sulfates. Three slots rather than eight, so it is wasted work per flask and
   not the 16-minute bomb T12 defused. Tighten it to `[OX1]=[SX2]=[OX1]` as T12
   did for the Claus row. Chain 2's carrier step, so the tolerance audit is owed
   and Ea/A must not move.
   *Done when:* the slot matches one shelf species and
   `tests/test_lead_chamber.py` is green with the same numbers.

The tolerance audit (~11 min) is owed and was not run. Nothing this session can
move a trajectory: the only files added are `validation/pka_domains.py` and
`tests/test_pka_domains.py`, and no file under `src/` was touched.

## Decisions already taken — do not reopen

- **A class-wide pKa rule for phenols is refused, and the measurement is why.**
  Both curated phenols are electron-rich; 39 of 79 gap phenols sit outside their
  substituent range (picric acid at sigma_sum +1.102 against phenol's -0.920);
  and phenol and salicylate's second proton SHARE a sigma_sum while sitting 3.45
  pKa units apart, so no substituent sum on the scale `hammett` carries can
  separate them. Sigma-minus, the scale a phenol pKa is fitted on, is not in
  that module. The amine class is refused more simply: three rows spanning 6.04
  units, its one plausible domain holding a single row against the two
  `carboxylic_pka.plateau` requires.
- **A missing ion has two gaps and only one is a pKa.** An ion whose neutral
  parent has no thermochemistry is not unblocked by curating an acidity; that is
  the whole mineral-oxyacid class (89 ions, 0 wanting a pKa) and it is T25.
- **No species `build_network` registers may be unpriceable**: what the TEMPLATES
  make is dropped with a notice, what the CALLER charges is a refusal. The half
  of the engine to ask was the vessel, not the templates.
- **A pKa the engine derived is not one it measured, and the player sees which**;
  **the rule is consulted AFTER the curated table and BEFORE the refusal**; **the
  plateau value is derived from `_PAIRS`, never typed**; **a graph edit belongs
  to `matter`**; **a pKa domain is local and its exclusions are chemistry**.
- **A route is credited with every step product, never with `route_roles`**; **an
  `intermediate` shelf row is deleted the day a reachable route makes it**; **a
  ratio pinned in a test is a guard rail, not a finding**; **backwards is
  retrosynthesis**; **the expensive checks are clocked in commits**; **the
  headline is templates fired, not reactions reached**.

## Open questions for the user

- **The suite and the audit** cost ~40 minutes together and nine sessions have
  now deferred the first. Task 2 is the ask.
- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is; without it T2 needs an RDKit-only mapper.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure and a pyrrhotite flask both make it, and no catalog route does.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `*_data.py`, `reachable.psv`, `species_roles.psv` or `silent_templates.psv`.
- Do not write a pKa you cannot source, and do not put an estimator in front of
  one: `pka_domains.py` panel 0 is where a rule has to earn its domain first.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, clear a red one, or rewrite a
  mixed-ending file whole -- read and write bytes.

# NEXT — overwritten 2026-09-13

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-13. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,329 collected, up 20 for the new pKa domain file. 1 RED and it is task 1, not this session's. Last full run 1,301 passed in 28m51s, eight commits ago | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~85 s, green | ruff + docs + catalog + templates + silent + 62 smoke tests |
| expensive checks owed | `suite` DUE at 7 commits, NOT run; `tolerance` at 7 of 6, NOT run. Neither is owed BY this session: it changed no `src/` file at all | `python tools/cadence.py` |
| templates | 59 rows, all `tier=family`, covering 46 catalog classes -- unmoved | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps -- unmoved | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 89 / 40 -- unmoved | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 22, three tiers deep; 46 runnable, 21 fed but unrunnable -- unmoved | `data/catalog/PLAYABLE.md` footer |
| pKa table | 33 `AcidPair` rows -- unmoved | `len(electrolyte.known_pairs())` |
| carboxylic pairs the table is short of | 624 distinct, 12 priced. 270 inside the plateau domain, 243 of them oligomers of one acid; 342 need their own measurement (230 polyprotic, 42 zwitterion) | `python validation/fatty_acid_pka.py` (118 s) |
| the plateau itself, from C3 up | 4.87 to 5.02, 0.15 units wide, derived from `_PAIRS` and not asserted | the same command, panel 0 |
| corpus and pool overlap | the corpus has 182 carboxylic pairs, a pool of 36 oleic flasks has 446, and they share 4 | the same command, panel 3 |
| why templates are silent | 16 no-substrate, 8 needs-more-than-a-pair, 0 cannot-fire -- unmoved | `python tools/classify_silent.py` (31 s) |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs, `properties/electrolyte.py` are CRLF; `validation/*.py` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T14 counted the carboxylic pKa wall instead of guessing at it, and the count
changed the answer. The corpus half is 19 missing pairs inside the plateau
domain -- typable by hand. The POOL half is not: one flask of oleic acid against
one other natural row reaches 249 more, and 243 of them are the same acid
esterified onto itself over and over, a series whose only end was the 400-species
cap. A table closes a list and that is not a list, so the fix is a rule with a
stated domain. That domain now exists as `validation/fatty_acid_pka.py:domain`,
pinned by 20 tests, and two false starts are recorded in it: GABA sat on the
plateau until a basic nitrogen four bonds out was excluded, and every carboxylate
salt read as unpriced until the counter-ion was dropped from the key.

## Do this now

1. **T17 - a test has been red for three sessions now.** Spec in `BACKLOG.md`.
   `tests/test_playable_levers.py::test_the_shelf_file_holds_exactly_what_this_audit_measured`
   fails on `calcium-hydroxide`: `build_playable`'s deep chain calls it
   CHAIN-blocked and `shelf.psv` has no `intermediate` row for it. Confirmed
   still red today (46 s, one test). Bisected on 2026-09-13 -- green at 77c6bd1,
   red from 188f22a, so it is T8's pKa cascade one scoreboard further out. It
   survives because it is not one of the 62 smoke tests. Decide which side is
   wrong before editing either: the test's message says ADD the row, and the
   chain arguably SHOULD reach slaked lime, `lime-cycle` being playable.
   *Done when:* the test is green and `PLAYABLE.md` is regenerated, or the
   backlog item is rewritten as the decision that the audit is the wrong half.

2. **T18 - write the plateau as a rule.** Spec in `BACKLOG.md`, and T14 decided
   its shape. Move `validation/fatty_acid_pka.py:domain` under `properties/` and
   give `ion_thermochemistry` a fallback consulted after `_PAIRS` misses, at
   4.87 to 5.02. It must report itself through `notices`: a derived pKa is not a
   measured one and rule 10 says the player has to be able to see which they got.
   *Done when:* a stearate prices with no hand-typed row, the notice names the
   rule and its domain, and the audit reports the plateau bucket as covered.

3. **T16 - the other loose sulfur-dioxide slot.** Spec in `BACKLOG.md`.
   `sulfur_dioxide_oxidation_by_nitrogen_dioxide` still writes SO2 as
   `[O:1]=[S:2]=[O:3]`, which matches a sulfate, and two shelf rows are
   sulfates. Three slots rather than eight, so it is wasted work per flask and
   not the 16-minute bomb T12 defused. It is chain 2's carrier step, so the
   tolerance audit is owed with it and the Ea/A must not move.
   *Done when:* the slot matches one shelf species and
   `tests/test_lead_chamber.py` is green with the same numbers.

The suite (~29 min) and the tolerance audit (~11 min) are owed from T8 and were
not run here; this session changed no `src/` file, so nothing it did can have
moved a trajectory. `reachable.psv` is stale by input (57 templates over 36
natural rows; there are now 59 and 37), so `templates_fired = 33` is a floor.

## Decisions already taken — do not reopen

- **The carboxylic plateau is a rule, not rows,** and the pool is the argument.
  243 of the 270 pairs inside its domain are oligomers of one self-esterifying
  acid, so the set has no last member and no table can close it.
- **A pKa domain is LOCAL and its exclusions are chemistry, not tidiness.** A
  basic nitrogen anywhere makes the molecule a zwitterion and a different acid
  (GABA 4.03, not 4.87). A substituent is named by the carbon it hangs off, not
  by its own bond depth, or lactic acid reports a beta hydroxyl.
- **A carboxylate salt is priced as its ION, never as the salt.**
  `thermochemistry` refuses `CC(=O)[O-].[Na+]` whole, so a pair's key is the
  fragment's -- and this is not S7's neutral mixture, since the two halves of a
  conjugate pair differ by one proton on one fragment.
- **A rock's Ksp decides whether its shelf row is matter or scenery**, and a
  sparingly soluble lattice dissolves at a rate its own Ksp bounds -- acid shifts
  the equilibrium and never the rate. **A disputed constant is a subtraction when
  two rows of one table bracket it.** **A proton-transfer row is written
  protonation-first**; **an ion's pKa is the molecular constant**; **no pKa is in
  `chemicals`**.
- **Backwards is retrosynthesis and must be forbidden to build up.**
- **The expensive checks are clocked in commits**, and an artefact-backed check
  derives its own last run from git. **The headline is templates fired, not
  reactions reached.** **T2 and T3 go ahead**; **`discovery/refine.py` is
  deleted, not wired**; **the README stays at 561 lines** until C1.

## Open questions for the user

- **The suite, the audit and a fresh `reachable.psv`** cost ~75 minutes, and
  five sessions have now deferred the first two. T17 is direct evidence of the
  cost: a red test has lived through three of them.
- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is. Without it T2 needs an RDKit-only mapper.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure and a pyrrhotite flask both make it. That tier's rule deletes a row
  when a ROUTE makes it, and no catalog route does.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `*_data.py`, `reachable.psv`, `species_roles.psv` or `silent_templates.psv`.
- Do not write a reactant slot more than twice without checking what else it
  matches on the shelf; `tests/test_template_table.py` fails you for it.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, and do not clear a red one.
- Do not rewrite a mixed-ending file whole; read and write bytes.

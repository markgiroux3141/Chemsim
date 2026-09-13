# NEXT — overwritten 2026-09-13

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-13. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,338 collected, +9 from T18's pins. No red test known today | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~85 s, green | ruff + docs + catalog + templates + silent + 62 smoke tests |
| expensive checks owed | `suite` DUE at 10 commits and `tolerance` DUE at 10, neither run; `routes` re-run today and recorded pass; `playable` re-derives from this commit; `reachable` ok at 6 | `python tools/cadence.py` |
| templates | 59 rows, all `tier=family`, covering 46 catalog classes -- unmoved | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps -- unmoved | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 90 / 40 (species-ready +1: `soap-saponification`) | `data/catalog/COVERAGE_REPORT.md` |
| routes runnable / playable | 47 runnable (+1), 23 playable, three tiers deep (10 / 12 / 1); 23 fed but unrunnable, ceiling 50 | `data/catalog/PLAYABLE.md` footer |
| the shelf | 72 rows, 43 natural / 25 intermediate / 4 bottle | `data/catalog/shelf.psv`, `python tools/build_shelf.py` |
| pKa table | 33 `AcidPair` rows -- unmoved, and T18's point is that it need not grow | `len(electrolyte.known_pairs())` |
| the plateau the rule quotes | 4.95, the mean of the two in-domain `_PAIRS` rows from C3 up, which span 4.87 to 5.02 | `carboxylic_pka.plateau(known_pairs())` |
| corpus carboxyl pairs priced | 32 of 182 (14 by a curated row, 18 by the rule); 0 left inside the domain | `python validation/fatty_acid_pka.py --corpus-only` (9 s) |
| why templates are silent | 16 no-substrate, 8 needs-more-than-a-pair, 0 cannot-fire -- unmoved | `python tools/classify_silent.py` (31 s) |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs, `shelf_data.py`, `inventory.py`, `electrolyte.py`, `builder.py` are CRLF; `carboxylic_pka.py`, `validation/` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T18 made the carboxylic plateau a rule. `properties/carboxylic_pka.py` carries
T14's domain predicate (against `Molecule`, so no new RDKit edge) and derives its
value from `_PAIRS`; `ThermochemistryProvider` gained an `ion_fallback` consulted
after the curated table misses and before the refusal, so no measurement is
overridden, and `build_network` reports every ion the rule priced. A stearate
prices with no hand-typed row: stearic acid in water goes from 12 species and 4
reactions to 21 and 21, `soap-saponification` runs, its two feeds are stranded.

## Do this now

1. **T16 - the other loose sulfur-dioxide slot.** Spec in `BACKLOG.md`.
   `sulfur_dioxide_oxidation_by_nitrogen_dioxide` still writes SO2 as
   `[O:1]=[S:2]=[O:3]`, which matches a sulfate, and two shelf rows are sulfates.
   Three slots rather than eight, so it is wasted work per flask and not the
   16-minute bomb T12 defused. Tighten it to `[OX1]=[SX2]=[OX1]` as T12 did for
   the Claus row. Chain 2's carrier step, so the audit is owed and Ea/A must not
   move.
   *Done when:* the slot matches one shelf species and
   `tests/test_lead_chamber.py` is green with the same numbers.

2. **T13 - an unpriced ion in the flask still stops `to_arrays`.** Spec in
   `BACKLOG.md`. T8 guarded the builder, so `build_network` reports and carries
   on; `to_arrays` still raises on the same flask, so a network can be built,
   reported and un-runnable, and the player hears one call later than the notice.
   T18 priced the stearate, so the witness is now the PHENOXIDE -- saligenol,
   saligenolate and water builds 7 reactions and refuses. Decide which half moves
   -- drop the species at registration and say the flask lost matter, or refuse
   the way the builder reports -- not by taste.
   *Done when:* a network holding an unpriced ion either integrates or refuses
   with a notice naming the species, and one test pins whichever was chosen.

3. **T5 - measure what the 33-row pKa table still bounds.** Spec in `BACKLOG.md`;
   T18 is why it is cheap now, the hook existing with one caller, so a second
   rule is a domain and a spread rather than plumbing. The phenoxide is candidate
   and warning both -- `_PAIRS` carries two phenols, 9.95 and 10.19, against the
   carboxylic plateau's measured 0.15-unit spread. Copy
   `validation/fatty_acid_pka.py`'s shape; do not write a pKa first.
   *Done when:* the count and its top classes are in this table with the command,
   and a follow-up names the fix the number argues for, refusal included.

The suite (~29 min) and the tolerance audit (~11 min) are owed and were not run
here. T18 declared no rate and no thermochemistry: it prices ions that were
previously REFUSED, so a flask that ran before runs the same way -- measured, by
diffing `examples/named_routes.py` on pre-T18 and post-T18 source, byte-identical
once clock stamps are stripped (in the `routes` cadence note). Untested is a
flask holding a plateau carboxylate: new chemistry, not a moved trajectory.
`reachable.psv` is stale by input (now 59 templates, 37 natural rows, 72 shelf
rows), so `templates_fired = 33` is a floor.

## Decisions already taken — do not reopen

- **A pKa the engine derived is not a pKa it measured, and the player sees which.**
  The rule stamps its own `source` and `build_network` routes that to `notices`;
  the marker is the constant `electrolyte.PLATEAU_RULE`, never a sentence.
- **The rule is consulted AFTER the curated table and BEFORE the refusal**, so a
  curated measurement is the last word and a species outside the domain still
  raises `UnpricedIon` rather than being given a plausible number.
- **The plateau value is derived from `_PAIRS`, never typed** (T0.5's reason);
  **a graph edit belongs to `matter`** (`Molecule.reprotonated`).
- **A route is credited with every step product, never with `route_roles`**, and
  **an `intermediate` shelf row is deleted the day a reachable route makes it**
  and ADDED the day a route becomes runnable with nothing to feed it. The
  scoreboard decides both, not taste. **A ratio pinned in a test is a guard rail,
  not a finding**, and **the plateau is a rule, not rows** -- the pool is why.
- **A pKa domain is local and its exclusions are chemistry**: a basic nitrogen
  anywhere makes the molecule a zwitterion and a different acid. **A carboxylate
  salt is priced as its ion**; **no pKa is in `chemicals`**; **a rock's Ksp
  decides whether its shelf row is matter or scenery**, acid shifting that
  equilibrium and never the rate; **backwards is retrosynthesis and must be
  forbidden to build up**.
- **The expensive checks are clocked in commits**, **the headline is templates
  fired, not reactions reached**, **`discovery/refine.py` is deleted, not wired**,
  and **the README stays at 561 lines** until C1.

## Open questions for the user

- **The suite, the audit and a fresh `reachable.psv`** cost ~75 minutes, and seven
  sessions have deferred the first two. T17 is the evidence: a red test lived
  through three of them, being none of the 62 smoke tests.
- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is; without it T2 needs an RDKit-only mapper.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure and a pyrrhotite flask both make it, and no catalog route does.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `*_data.py`, `reachable.psv`, `species_roles.psv` or `silent_templates.psv`.
- Do not write a reactant slot more than twice without checking what else it
  matches on the shelf; `tests/test_template_table.py` fails you for it.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, clear a red one, or rewrite a
  mixed-ending file whole -- read and write bytes.

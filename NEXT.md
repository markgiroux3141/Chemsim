# NEXT — overwritten 2026-09-13

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-13. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,309 collected. 31 files run today, 1 RED and it is not this session's -- see task 1. Last full run 1,301 passed in 28m51s, seven commits ago | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~85 s, green | ruff + docs + catalog + templates + silent + 62 smoke tests |
| expensive checks owed | `suite` DUE at 7 commits, NOT run; `tolerance` at 7 of 6, NOT run; `routes` recorded pass today (149 tests, 223 s). `reachable` reads ok at 3 commits and is stale by input | `python tools/cadence.py` |
| templates | 59 rows, all `tier=family`, covering 46 catalog classes | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 89 / 40 -- unmoved | `data/catalog/COVERAGE_REPORT.md` |
| corpus species refused a price | 409 of 1,583; chargeable 1,174 | same file |
| routes playable from natural materials | 22, three tiers deep; 46 runnable, 21 fed but unrunnable -- regenerated today byte-identical | `data/catalog/PLAYABLE.md` footer |
| mineral lattices | 50, 21 of them reacting as a crystal; 29 have a Ksp AND can be put in a flask, 2 blocked (both on a cation) | `tools/build_shelf.py`, `tests/test_phosphate.py` |
| natural shelf rows that can be charged | 37 of 43 | `chemsim.engine.inventory.shelf(("natural",))` |
| pKa table | 33 `AcidPair` rows; the provider prices 34 ions, 5 of them cations | `len(electrolyte._PAIRS)` |
| why templates are silent | 16 no-substrate, 8 needs-more-than-a-pair, 0 cannot-fire; work order 19 substrates, 14 of them alone | `python tools/classify_silent.py` (31 s) |
| the small-molecule closure | 24 rows, 48 species, frontier 0 -- still a fixpoint | the same file's `#!` block |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs, `properties/electrolyte.py`, `tests/test_shelf.py`, `mineral_data.py` and `template_data.py` are CRLF; `tests/test_phosphate.py`, `tools/build_shelf.py` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T15 made T12's sulfide real in a flask. `troilite` is now a `mineral_data` row,
so `iron-ii-sulfide` has a Ksp and its ions no longer sit in the solid block for
ever: pKsp 18.775 derived, the flask saturates at sqrt(Ksp) = 4.10e-10 M and
holds femtomoles of H2S with nothing declared anywhere in the chain. Acid keeps
the dissolution going and CANNOT accelerate it, the drive being capped at
`k_diss*V*Ksproot`. Pyrite's corpus SMILES was FeS3 and is now FeS2 -- a formula
fix for `corpus_balance`, not a price, since the disulfide has no pKa pair. And
it found a test that has been red since T8 and that nobody has looked at.

## Do this now

1. **T17 - a test has been red for two sessions.** Spec in `BACKLOG.md`.
   `tests/test_playable_levers.py::test_the_shelf_file_holds_exactly_what_this_audit_measured`
   fails on `calcium-hydroxide`: `build_playable`'s deep chain calls it
   CHAIN-blocked and `shelf.psv` has no `intermediate` row for it. Bisected
   today -- green at 77c6bd1, red from 188f22a, so it is T8's pKa cascade one
   scoreboard further out than that session looked. It survived because it is
   not one of the 62 smoke tests. Decide which side is wrong before editing
   either: the test's message says ADD the row, and the chain arguably SHOULD
   reach slaked lime, `lime-cycle` being playable.
   *Done when:* the test is green and `PLAYABLE.md` is regenerated, or the
   backlog item is rewritten as the decision that the audit is the wrong half.

2. **T14 - count the fatty-acid pKa wall before writing any of it.** Spec in
   `BACKLOG.md`; a measurement, and it sits in front of T5 for the reason T5
   sits in front of any pKa work. T8's cascade named four unpriced carboxylates
   in one flask and every one sits on the same 4.9 plateau, so the question is
   whether the fix is rows or a rule with a domain. T12 is the counter-example
   worth carrying: a number that looks like a judgement can be a subtraction.
   *Done when:* the count and its split are in this table with the command.

3. **T16 - the other loose sulfur-dioxide slot.** Spec in `BACKLOG.md`.
   `sulfur_dioxide_oxidation_by_nitrogen_dioxide` still writes SO2 as
   `[O:1]=[S:2]=[O:3]`, which matches a sulfate, and two shelf rows are
   sulfates. Three slots rather than eight, so it is wasted work per flask and
   not the 16-minute bomb T12 defused. It is chain 2's carrier step, so the
   tolerance audit is owed and the Ea/A must not move.
   *Done when:* the slot matches one shelf species and
   `tests/test_lead_chamber.py` is green with the same numbers.

The suite (~29 min) and the tolerance audit (~11 min) are owed from T8 and were
not run here either; T15 touched no integrator code and `examples/named_routes.py`
came back green with 149 route tests. `reachable.psv` is stale by input -- it
swept 57 templates over 36 natural rows and there are now 59 and 37 -- so
`templates_fired = 33` is a lower bound; re-running is 35 minutes, ask first.

## Decisions already taken — do not reopen

- **A rock's Ksp decides whether its shelf row is matter or scenery.** Nothing
  in this engine converts a lattice charge into its ions, so a mineral with no
  `mineral_data` row and a `solid` declaration is inert by construction.
  `build_shelf` prints those rows by name; that print is the work queue.
- **A sparingly soluble lattice dissolves at a rate its own Ksp bounds.** The
  drive is `k_diss*V*(Qroot - Ksproot)`, so acid shifts the equilibrium and
  never the rate. Real acid attack on a sulfide is surface chemistry with no
  term here. The EQUILIBRIUM is derived; the RATE is the vessel's one knob.
- **A disputed constant is a subtraction when two rows of one table bracket it.**
  HS- to S2- is quoted 12.9 to 19; `ion_data` makes it 12.91 on one basis.
- **A proton-transfer row is written protonation-first**, `_expand_reverse`
  refusing a proposal heavier than the flask it came from.
- **An ion's pKa is the molecular constant**, and **no pKa is in `chemicals`**.
- **Backwards is retrosynthesis and must be forbidden to build up.**
- **The expensive checks are clocked in commits**, and an artefact-backed check
  derives its own last run from git.
- **The headline is templates fired, not reactions reached.**
- **T2 and T3 go ahead**; **`discovery/refine.py` is deleted, not wired**; **the
  README stays at 561 lines** until C1.

## Open questions for the user

- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is. Without it T2 needs an RDKit-only mapper.
- **The suite, the audit and a fresh `reachable.psv`** cost ~75 minutes, and
  four sessions have now deferred the first two. T17 is direct evidence of what
  that costs: a red test lived through two of them.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure makes it from natural rows and a flask now makes it from pyrrhotite.
  That tier's rule deletes a row when a ROUTE makes it, and no catalog route
  does: `sulfide-carbonation` needs the carbonic anchor `electrolyte` refuses.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `template_data.py`, `mineral_data.py`, `shelf_data.py`, `reachable.psv`,
  `species_roles.psv` or `silent_templates.psv`; `--check` fails. A mineral is
  edited in `tools/build_mineral_data.py`, a template in `templates.psv`.
- Do not write a reactant slot more than twice without checking what else it
  matches on the shelf; `tests/test_template_table.py` now fails you for it.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, and do not clear a red one.
- Do not rewrite a mixed-ending file whole; read and write bytes.

# NEXT — overwritten 2026-09-13

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-13. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,307 collected; 24 of the 66 files run today, all green, 4 restated. Last full run 1,301 passed in 28m51s, six commits ago | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~86 s, green | ruff + docs + catalog + templates + silent + 62 smoke tests |
| expensive checks owed | `suite` DUE at 5 commits, NOT run; `tolerance` at 5 of 6, NOT run; `routes` recorded pass today. `reachable` reads ok at 1 commit and is stale by input -- see below | `python tools/cadence.py` |
| templates | 59 rows, all `tier=family`, covering 46 catalog classes | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| pKa table | 33 `AcidPair` rows; the provider prices 34 ions, 5 of them cations | `len(electrolyte._PAIRS)`, `len(ion_thermochemistry(ThermochemistryProvider()))` |
| routes template-ready / species-ready / both | 46 / 89 / 40 | `data/catalog/COVERAGE_REPORT.md` |
| corpus species refused a price | 409 of 1,583; chargeable 1,174 | same file |
| routes playable from natural materials | 22, three tiers deep; 46 runnable, 21 fed but unrunnable -- regenerated today byte-identical | `data/catalog/PLAYABLE.md` footer |
| natural shelf rows that can be charged | 37 of 43; pyrrhotite joined | `chemsim.engine.inventory.shelf(("natural",))` |
| why templates are silent | 16 no-substrate, 8 needs-more-than-a-pair, 0 cannot-fire; work order 19 substrates, 14 of them alone, head `[C;H4]` | `python tools/classify_silent.py` (31 s) |
| the small-molecule closure | 24 rows, 48 species, frontier 0 -- still a fixpoint, reached in 4 generations | the same file's `#!` block |
| lattices with a Ksp that cannot be put in a flask | 2 of 30, both blocked on a cation | `tests/test_phosphate.py`, `validation/phosphate_rock.py` panel 3 |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs, `properties/electrolyte.py`, `tests/test_shelf.py`, `tests/test_solubility_product.py` and `template_data.py` are CRLF; `tools/build_shelf.py`, `validation/phosphate_rock.py` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T12 priced the sulfide ion and the head of the work order left it. The pKa C2
refused to choose between (12.9 to 19 across compilations) was never a choice:
`ion_data` carries [SH-] and [S-2] on one CRC basis, so the pKa is their
difference, 12.91, and any other value prices [S-2] twice over. Two protonation
rows carry it into the network, the closure now makes H2S, and both Claus
templates fire. It also found a bomb: the Claus SO2 slot was `[O]=[S]=[O]`,
which matches a sulfate, and eight such slots over three species is 6561
rewrites of a 24-molecule template -- the four-second closure took 16 minutes
the first time H2S existed in it. A test now fails any repeated slot like it.

## Do this now

1. **T15 - the sulfide half of the shelf is half-represented.** Spec in
   `BACKLOG.md`; small, and it makes T12's work true in a flask rather than only
   in discovery. `iron-ii-sulfide` is chargeable now and its ions sit in the
   solid block for ever, troilite having no `mineral_data` row and so no Ksp;
   `tools/build_shelf.py` prints exactly that, by name. `chemicals` has FeS under
   CAS 1317-37-9 (Hfs -100.0, S0s 60.3). The second half is pyrite, whose corpus
   SMILES `[Fe+2].[S-]S[S-]` is FeS3.
   *Done when:* pyrrhotite and water make H2S in the integrator, or the shelf
   row says `liquid` and says why; and pyrite's formula is FeS2.

2. **T14 - count the fatty-acid pKa wall before writing any of it.** Spec in
   `BACKLOG.md`; a measurement, and it sits in front of T5 for the reason T5
   sits in front of any pKa work. T8's cascade named four unpriced carboxylates
   in one flask and every one sits on the same 4.9 plateau, so the question is
   whether the fix is rows or a rule with a domain. T12 is the counter-example
   worth carrying: a number that looks like a judgement can be a subtraction.
   *Done when:* the count and its split are in this table with the command.

3. **T13 - an unpriced ion in the flask still stops `to_arrays`.** Spec in
   `BACKLOG.md`. `build_network` no longer raises on one, both asking sites being
   guarded, but `ReactionNetwork.to_arrays` does: measured on saligenol plus water
   plus saligenolate, 7 reactions then a refusal. `network/` work, and it owes
   the suite and the audit.
   *Done when:* such a network integrates or refuses with a notice, and a test
   pins whichever was chosen.

`reachable.psv` is stale by input and the ledger cannot see it: it swept 57
templates over 36 natural rows and there are now 59 and 37, so `templates_fired
= 33` and its silent list are lower bounds. Re-running is 35 minutes over 666
pairs, was 630 -- ask first, and prefer it after T15, which moves the same
inputs again. The suite (~29 min) and the tolerance audit (~11 min) are owed
from T8 and were not run here either; T12 touched no integrator code, and
`examples/named_routes.py` came back in 35.8 s with 119 route tests green.

## Decisions already taken — do not reopen

- **A disputed constant is a subtraction when two rows of one table already
  bracket it.** HS- to S2- is quoted from 12.9 to 19; `ion_data`'s own [SH-] and
  [S-2] differ by 73.7 kJ/mol on one basis, which is pKa 12.91. A modern 17-19
  would contradict the five sulfide Ksp computed from that same Gf([S-2]) -- one
  species with two standard states. C2's phosphoric-third rule, one level down.
- **A proton-transfer row is written protonation-first.** `_expand_reverse`
  refuses a proposal heavier than the flask it came from and a proton is heavier,
  so a dissociation-direction row never protonates the base. Same as
  `amine_protonation`.
- **An ion's pKa is the molecular constant, never the aggregate's.**
- **A pKa is not in `chemicals`.** The table uses PubChem's `iupacpka`
  collection (`sdqagent.cgi`), named papers, and now `ion_data` subtraction.
- **The closure is the small-molecule half and stays a fixpoint** (24 rows, 48
  species). A witness is ranked by cost and `UnpricedIon` gates the pool.
- **Backwards is retrosynthesis and must be forbidden to build up.**
- **The expensive checks are clocked in commits**, and an artefact-backed check
  derives its own last run from git. T11 (a run that confirms no change) is open.
- **The headline is templates fired, not reactions reached.**
- **T2 and T3 go ahead**; **`discovery/refine.py` is deleted, not wired** (R4/E3); **the README stays at 561 lines** until C1.

## Open questions for the user

- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is. Without it T2 needs an RDKit-only mapper.
- **The suite, the audit and a fresh `reachable.psv`** cost ~75 minutes, and
  three sessions have now deferred the first two.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure now makes it from natural rows. That tier's own rule deletes a row
  when a route makes it, and no catalog route does: `sulfide-carbonation` is
  uncovered and needs the carbonic-acid anchor `electrolyte` refuses.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `template_data.py`, `shelf_data.py`, `reachable.psv`, `species_roles.psv` or
  `silent_templates.psv`; `--check` fails. A template is edited in
  `data/templates/templates.psv`.
- Do not write a reactant slot more than twice without checking what else it
  matches on the shelf; `tests/test_template_table.py` now fails you for it.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, and do not clear a red one.
- Do not rewrite a mixed-ending file whole: `tests/test_reachable.py` holds both
  CRLF and LF lines, and `read_text` then `write_text` flattens it.

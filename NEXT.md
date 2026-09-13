# NEXT — overwritten 2026-09-12

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-12. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,304 collected; 34 of the 66 test files run today, all green. Last full run 1,301 passed in 28m51s, four commits ago | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~105 s, green | ruff + docs + catalog + templates + silent + 62 smoke tests |
| expensive checks owed | `suite` is DUE at 4 commits and was NOT run; `tolerance` is at 4 of 6. Both are owed by T8, which changed `network/builder.py`. `playable` and `reachable` cleared on this commit | `python tools/cadence.py` |
| tolerance audit | recorded FAIL three commits ago, 11m12s, 3 findings all pre-existing (T10) | `python validation/tolerance_audit.py` |
| templates | 57 rows, all `tier=family`, covering 46 catalog classes | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| pKa pairs | 33, of which 5 are cations | `properties/electrolyte._PAIRS` |
| routes template-ready / species-ready / both | 46 / 88 / 40 | `data/catalog/COVERAGE_REPORT.md` |
| corpus species refused a price | 412 of 1,583 | same file |
| routes playable from natural materials | 22, three tiers deep; 46 runnable, 21 fed but unrunnable | `data/catalog/PLAYABLE.md` footer |
| templates a natural PAIR can reach | 33 of 57; 24 silent and named | `data/catalog/derived/reachable.psv` |
| why the 24 are silent | 18 no-substrate, 6 needs-more-than-a-pair, 0 cannot-fire | `python tools/classify_silent.py` |
| the work order | 20 blocking substrates, 16 of which block one template and nothing else; head is `[S;H2]` at 2 | `derived/silent_templates.psv`, THE WORK ORDER block |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs, `tools/classify_silent.py`, `properties/electrolyte.py`, `network/builder.py` and `tests/test_robustness.py` are CRLF; most other source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

T8 sourced three pKa values and every scoreboard in the repo moved. The oleate,
the eugenolate and hypochlorite were switching four templates off in flasks of
natural shelf rows; `cannot-fire` is now zero, templates fired 29 -> 33, playable
21 -> 22, intersection 38 -> 40. It also broke something: pricing the oleate let
the fatty-acid cascade run one step further, to a stearate the table does not
carry, and the 35-minute sweep died out of the Evans-Polanyi barrier. The builder
now drops that reaction with a notice, the shape T1d gave the reverse-rate end.
Six test files had pinned the old numbers and were restated.

## Do this now

1. **T12 — hydrogen sulfide, still the head of the work order.** Spec in
   `BACKLOG.md`; small, and the only substrate in the file worth two templates
   (`claus_comproportionation`, `hydrogen_sulfide_combustion`), neither short of
   anything else. H2S is a shelf row at tier `intermediate`; the sweep is over
   `natural`, and pyrite, galena and pyrrhotite are natural rows the closure
   makes no H2S from. Find the missing template between a metal sulfide and an
   acid, or record that the gap is the shelf tier and not the chemistry.
   *Done when:* `[S;H2]` has left the work order, or `BACKLOG.md` says which
   template would put it there and at what cost.

2. **T14 — count the fatty-acid pKa wall before writing any of it.** Spec in
   `BACKLOG.md`; a measurement, and it sits in front of T5 for the reason T5
   sits in front of any pKa work. T8's cascade named four unpriced carboxylates
   in one flask and every one sits on the same 4.9 plateau, so the question is
   whether the fix is rows or a rule with a domain.
   *Done when:* the count and its split are in this table with the command.

3. **T13 — an unpriced ion in the flask still stops `to_arrays`.** Spec in
   `BACKLOG.md`. `build_network` no longer raises on one, both asking sites
   being guarded, but `ReactionNetwork.to_arrays` does: measured today on
   saligenol + water + saligenolate, which builds 7 reactions and then refuses.
   A network that is built, reported and un-runnable is R1's boundary landing
   one call too late. This is `network/` work and owes the suite and the audit.
   *Done when:* such a network integrates or refuses with a notice, and a test
   pins whichever was chosen.

T8 changed `network/builder.py`, so the suite (~29 min) and the tolerance audit
(~11 min) are both owed and **neither was run** — ask before taking either. The
guard only converts a raise into a dropped reaction, so no trajectory that ran
before can have moved; the three new pKa rows can move any flask holding oleic
acid, eugenol or HOCl, and `examples/named_routes.py` came back clean in 33.7 s
(recorded pass) with `tests/test_named_routes.py` green.

## Decisions already taken — do not reopen

- **An ion's pKa is the molecular constant, never the aggregate's.** Oleic acid
  is 5.02 because that is what an unbranched carboxyl is; the 8-10 the
  fatty-acid literature reports is the acidity of a micelle or bilayer surface,
  whose own charge shifts the next proton. This engine has no aggregate phase,
  and a table of molecular constants is the wrong place to smuggle one in.
- **A pKa is not in `chemicals`.** Checked today, no pKa dataset in the package.
  What this table uses is PubChem's IUPAC dissociation-constant collection
  (queryable: `sdqagent.cgi`, collection `iupacpka`) and named primary papers.
- **`to_arrays` refusing an unpriced ion is pre-existing**, measured today on a
  charged saligenolate. T8 neither caused it nor fixed it. T13.
- **The closure is the small-molecule half and stays a fixpoint**, a witness is
  ranked by cost, a template is charged to every missing slot, and `UnpricedIon`
  rather than `OutsideEstimatorDomain` gates the pool. All four still hold.
- **Backwards is retrosynthesis and must be forbidden to build up.**
- **The expensive checks are clocked in COMMITS**, and a check writing a
  committed artefact derives its own last run from git rather than a stamp.
  `playable` and `reachable` both clear on this commit because their artefacts
  moved; T11 (a run that confirms no change) is still open and still right.
- **The headline is templates fired, not reactions reached.** 98% of the 24,825
  is four templates over a sugar frontier.
- **T2 and T3 go ahead** (174 extractable-and-uncovered rows, +28 at the
  ceiling). **`discovery/refine.py` is deleted, not wired** (R4/E3, still open),
  and **the README stays at 561 lines** until C1.

## Open questions for the user

- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is. Without it T2 needs an RDKit-only mapper.
- **Species work is half of T2's payoff**: 36 of the 64 routes extraction would
  make template-ready are held by an unpriceable species.
- **The suite and the tolerance audit are owed** and cost ~40 minutes together.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `template_data.py`, `reachable.psv`, `species_roles.psv` or
  `silent_templates.psv`; `--check` fails. A template is edited in
  `data/templates/templates.psv`.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, and do not clear a red one.
- Do not rewrite a mixed-ending file whole: `tests/test_reachable.py` holds both
  CRLF and LF lines, and `read_text` then `write_text` flattens it.

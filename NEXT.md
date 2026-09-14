# NEXT — overwritten 2026-09-13

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-13. The command is named.

| fact | value | command |
|---|---|---|
| **route coverage ceiling** | **110 template-ready, ~66 intersection. 173 is NOT the target** | the script in `docs/design/route-coverage-ceiling.md` |
| routes template-ready / species-ready / both | 46 / 90 / 40; template-ready has not moved in 43 commits | `data/catalog/COVERAGE_REPORT.md` |
| routes runnable / playable | 47 / 23 | `data/catalog/PLAYABLE.md` footer |
| uncovered extractable steps / classes | 174 steps over 132 classes; 102 singletons, 6 with three or more | same script |
| tests | 1,353 collected | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~85 s, green | ruff + docs + catalog + templates + template products + silent + 83 smoke |
| template rows against their catalog step | 59 rows / 191 steps: 31 pass, 14 partial, 9 wrong-product, 3 no-substrate, 0 no-fire, 2 no-class | `python tools/check_template_products.py` (2.2 s) |
| why the 23 non-passing rows miss | 8 salt, 5 stereo, 10 other | same, or the `#!` keys in `derived/template_products.psv` |
| templates | 59 rows, all `tier=family`, 46 catalog classes | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| why templates are silent | 16 no-substrate, 8 needs-more-than-a-pair, 0 cannot-fire; `pool_species` 290 | `classify_silent.py --check`, current |
| pKa table / corpus ions still wanting one | 41 `AcidPair` rows; 444 ions over 48 routes | `python validation/pka_domains.py` panels 0 and 3 |
| the shelf | 72 rows, 43 natural / 25 intermediate / 4 bottle | `data/catalog/shelf.psv` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| expensive checks owed | `reachable` is DUE, 11 of 10 commits, last 2026-09-12 | `python tools/cadence.py` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, `CLAUDE.md`, the PSVs and `electrolyte.py` are CRLF; `check.ps1`, `docs/design/`, `tools/` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T1b built `tools/check_template_products.py`: every template row fired over the
catalog steps its class claims, product sets compared, 2.2 s, committed artefact
with a `--check` step in `check.ps1` and eight tests folded into
`test_template_table.py`. Its third clause is refused, not deferred — 132 of the
208 tests in the fourteen per-template files build a network or run a vessel.
Then the ceiling was derived for the first time: 110 template-ready, ~66
intersection, so the gap is twenty routes and not a hundred and twenty-six. The
session skill now carries the standing priority that came out of it — change the
rate, do not grind the queue.

## Do this now

1. **T3's six family candidates, hand-written. No extractor needed.** The one
   piece of T2's payload that is writable today, and the cheapest thing on the
   board: six uncovered classes hold three or more extractable steps each, so
   six rows cover 24 steps over 21 routes. `nucleophilic-substitution` (6 steps,
   6 routes), `nucleophilic-addition` (4/4), `catalytic-air-oxidation` (4/3),
   `ammoxidation` (4/2), `esterification-nitration` (3/3),
   `intramolecular-williamson` (3/3). Read
   `fable analysis/03-HOW-TO-ADD-A-TEMPLATE.md`, then add rows to
   `data/templates/templates.psv` — a template is a row now. Take them one at a
   time and let `check_template_products.py` judge each against its own steps;
   a class that will not generalise is refused with its reason, not forced.
   This also de-risks T2: you learn what these SMARTS look like before
   automating 132 of them.
   *Done when:* each of the six is a row reaching `pass`, or refused in writing;
   `template-ready` in `COVERAGE_REPORT.md` has moved off 46; `./check.ps1` green.

2. **T2 — the extractor.** Spec in `BACKLOG.md`. 132 classes, 102 of them
   singletons, at a hand-written rate of three to five a session — the extractor
   is the only thing that changes that. Decide its two walls first, both counted
   by T1b: the catalog spells a precipitated salt as one species where the engine
   holds its ions (8 rows), and declares a stereoisomer where a template emits
   the flat species (5 rows). The corpus carries no stoichiometric coefficients,
   so `corpus_balance.coefficients()` needs a smallest-integer step after it.
   *Done when:* extracted rows reach `pass` in `template_products.psv`, the
   report separates template-ready-via-family from via-literal, `./check.ps1` green.

3. **`reachable` is due and it is the user's call.** 35 minutes, 11 of 10
   commits, nothing has re-derived `derived/reachable.psv` since 2026-09-12.
   `python tools/build_reachable.py`, then `python tools/cadence.py --record
   reachable --result pass|fail --note "..."`. Task 1 adds templates, so the
   fired count will move and this is how it is measured.
   *Done when:* `reachable.psv` is regenerated and the ledger row is recorded.

## Decisions already taken — do not reopen

- **173 is not the target and never was reachable.** 7 routes name a species
  with no molecular graph, 14 classes are credited to integrator terms where no
  SMARTS can exist, the rest have a step that will not balance. Ceiling 110
  template-ready / ~66 intersection against 46 / 40 today. Derivation and the
  script: `docs/design/route-coverage-ceiling.md`. Quote 66, not 173.
- **Change the rate, do not grind the queue.** The session skill's Step 0b is
  the standing priority. Per-row pKa curation (T23, T26) is real playability
  work — T18's rule took stearic acid from 4 reactions to 21 — and it is NOT
  task 1 while T2 or T3 is open. T23 and T27 each spent a session and wrote
  "coverage does not move" as their own result.
- **The per-template test files are not retired and the file count is not a
  target**; 132 of their 208 tests build a network or run a vessel
  (`docs/design/per-template-tests-not-retired.md`).
- **A step lists neither its solvent nor the ions the pot carries**, so
  `check_template_products.py` offers a slot water, hydronium and hydroxide and
  nothing else, and names the four rows that needed it.
- **A class-wide phenol pKa rule is refused**
  (`docs/design/phenol-pka-rule-refused.md`); **the top of the pKa ranking is
  refused, not pending**; **both protons of a diacid come from one
  determination**; **a curated pKa moves the shelf and corpus ion instruments,
  never `COVERAGE_REPORT.md`**.
- **No species `build_network` registers may be unpriceable**; **a declared
  order may never be reversible**; **backwards is retrosynthesis**; **the
  expensive checks are clocked in commits**; **a class names a mechanism, never
  an outcome**.

## Open questions for the user

- **`reachable` is 35 minutes and it is due.** Task 3. Say whether to spend it.
- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is; without it T2 needs an RDKit-only atom mapper. Task 2 needs
  this answered or it needs the RDKit-only path. Task 1 does not.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure and a pyrrhotite flask both make it, and no catalog route does.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `*_data.py`, `reachable.psv`, `species_roles.psv`, `silent_templates.psv` or
  `template_products.psv`.
- Do not chase 173, re-derive the ceiling, make per-row pKa curation task 1,
  write a pKa you cannot source, or re-open the phenol refusal.
- Do not read `docs/history/` whole (grep it), add a physics module, stamp a
  cadence row you did not run, or rewrite a mixed-ending file whole.

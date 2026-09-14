# NEXT — overwritten 2026-09-14

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-14. The command is named.

| fact | value | command |
|---|---|---|
| **route coverage ceiling** | **110 template-ready, ~66 intersection. 173 is NOT the target** | the script in `docs/design/route-coverage-ceiling.md` |
| routes template-ready / species-ready / both | 65 / 90 / 51, and **49 / 90 / 41 on hand-typed rows alone** | `data/catalog/COVERAGE_REPORT.md` |
| routes runnable / playable | 49 / 23 -- `PLAYABLE.md` scores the `family` tier ALONE, on purpose | `data/catalog/PLAYABLE.md` footer |
| the same two granting the extracted rows | 59 / 25 | same file, the note under §1 |
| templates | 125 rows: 67 `family` hand-typed, 58 `literal` extracted; 102 catalog classes | `python tools/build_templates.py --check` |
| reaction classes with a template | 115 of 240, 63 of them a family row | `python validation/catalog_coverage.py` |
| template rows against their catalog step | 96 pass, 15 partial, 9 wrong-product, 3 no-substrate, 2 no-class over 279 steps | `python tools/check_template_products.py` (3.8 s) |
| why the 24 non-passing rows miss | 9 salt, 5 stereo, 10 other -- all of them `family` rows | same, or the `#!` keys in `derived/template_products.psv` |
| steps the extractor refused | 178 of 236: 75 salt, 35 stoichiometry, 24 stereo, 22 coefficients, 10 no-graph, 5 closed-cycle, 4 centre, 3 duplicate | `data/templates/needs_review.psv` footer |
| tests | 1,357 collected | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~95 s, green | ruff + docs + catalog + extracted + templates + template products + silent + 87 smoke |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| why templates are silent | 15 no-substrate, 9 needs-more-than-a-pair, 0 cannot-fire; `pool_species` 325, shelf closure 50 | `classify_silent.py --check`, current |
| pKa table / corpus ions | 41 `AcidPair` rows; 444 corpus ions still want one | `python validation/pka_domains.py` panel 3 |
| the shelf | 71 rows | `data/catalog/shelf.psv` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| expensive checks owed | `suite` DUE (5 commits), `reachable` DUE (13), both before this commit; `routes` recorded pass today | `python tools/cadence.py` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, `CLAUDE.md`, the catalog PSVs, `catalog_coverage.py` and `electrolyte.py` are CRLF; `check.ps1`, `tools/`, `data/templates/literal.psv` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T2 landed: `tools/extract_templates.py` turns a catalog step into a template row
in 1.8 s for the whole corpus. It balances the step (refusing a 2-D nullspace
rather than picking one of two balances), maps atoms by iterated MCS, writes a
SMARTS with one bond of context, and **runs it against the step before keeping
it** -- which is what lets an approximate mapper be safe. 58 rows, 52 classes,
all 96-pass and all building a reaction in `build_network`. Two bugs it wrote
and this session caught: a product context atom written tight makes hydrogen out
of nothing, and gating on `TEMPLATE_CLASSES` makes the second run read its own
output as coverage. `PLAYABLE.md` deliberately still scores `family` alone.

## Do this now

1. **T28 — two formation entries light three rows already written.** Spec in
   `BACKLOG.md`. `methane_ammoxidation` and `cyanide_imine_addition` reach
   `pass` against their catalog steps and build ZERO reactions, because HCN has
   no curated entry and neither Joback nor Benson prices it. An alkyl nitrate is
   the same shape and is what `esterification-nitration` was refused on. Source
   both the way `docs/design/` records it, never from recall.
   *Done when:* `build_network(['CC=N','C#N'], ...)` returns a reaction and the
   two rows stop appearing in `unpriced`.

2. **T2c — promote one literal row to `family`, which is the cheap playable
   route.** `PLAYABLE.md` §8b marks the four work-order classes that already
   have an extracted row: `pyrolysis`, `pyrolysis-dehydration`,
   `carbonyl-hydration`, `thermal-fixation`. A promotion is not a copy -- T2d
   says why: the gate compares canonical SMILES, so it cannot see a mapping that
   is wrong on a symmetric product. Check the mapping by hand, argue the
   barrier, move the row into `templates.psv`.
   *Done when:* one class moves tier and `PLAYABLE.md`'s headline moves with it.

3. **Two expensive checks are due and both are the user's call.** `suite` is 30
   minutes and `reachable` 35; `python tools/cadence.py` says how overdue. Neither could have been broken
   by this session -- every engine path goes through `ui.examples.full_library()`,
   which loads `family`, so the library `build_reachable` sweeps is the same 67
   rows as on 2026-09-12. `python -m pytest -q`; `python tools/build_reachable.py`;
   then `python tools/cadence.py --record <check> --result pass|fail --note "..."`.
   *Done when:* both ledger rows are recorded with what they said.

## Decisions already taken — do not reopen

- **The extractor's two walls are refusals, not gaps.** 75 salt steps and 24
  stereo steps, argued in `tools/extract_templates.py`'s docstring and T2 in
  `BACKLOG.md`. Do not make the extractor split a salt into ions.
- **`PLAYABLE.md` scores the `family` tier and `COVERAGE_REPORT.md` scores every
  tier.** One measures the game, the other the corpus. Both print the split.
- **The extractor gates on `FAMILY_TEMPLATE_CLASSES`.** Reading the whole map
  makes the second run refuse everything the first wrote, and the first run of a
  fresh checkout is correct either way. `test_the_extractor_does_not_read_its_own_output_as_coverage`.
- **A literal row is irreversible, declares no orders, no alpha, no rho.** A
  policy cannot argue for any of them; that is what `tier=family` is for.
- **173 is not the target.** Quote 66. **Change the rate, not the queue** --
  per-row pKa curation is real work and is not task 1.
- **A pinned count is not a guard**; **no species `build_network` registers may
  be unpriceable**; **backwards is retrosynthesis**; **a class names a
  mechanism, never an outcome**.

## Open questions for the user

- **`suite` and `reachable` are 65 minutes between them and both are due.** Task
  3. Say whether to spend it.
- **Five species are newly stranded and `shelf.psv` is hand-maintained** (T29,
  a red test since T3): `ammonia`, `benzene`, `bisphenol-a`, `ethylene-oxide`,
  `hydrogen-iodide`. Giving a player benzene is a game-design call, not a
  regeneration.
- **`tests/test_playable.py` is not in the smoke set**, which is why T3's
  scoreboard drift went five commits unseen. Adding it costs `./check.ps1`
  another 47 s.

## Do not

- Do not hand-edit `literal.psv`, `needs_review.psv`, `COVERAGE_REPORT.md`,
  `PLAYABLE.md`, `ROUTE_INDEX.md`, `*_data.py`, `reachable.psv`,
  `species_roles.psv`, `silent_templates.psv` or `template_products.psv`.
- Do not chase 173, re-derive the ceiling, make per-row pKa curation task 1,
  write a pKa you cannot source, or reopen the T2 or T3 refusals.
- Do not put a `literal` row in `templates.psv` or a `family` row in
  `literal.psv` -- the tier and the file are the same fact twice.
- Do not read `docs/history/` whole (grep it), add a physics module, stamp a
  cadence row you did not run, or rewrite a mixed-ending file whole.

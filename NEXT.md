# NEXT — overwritten 2026-09-13

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-13. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,353 collected, 1,345 -> 1,353 (T1b's eight) | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~85 s, green | ruff + docs + catalog + templates + template products + silent + 83 smoke tests |
| template rows against their catalog step | 59 rows / 191 steps: 31 pass, 14 partial, 9 wrong-product, 3 no-substrate, 0 no-fire, 2 no-class | `python tools/check_template_products.py` (2.2 s) |
| why the 23 non-passing rows miss | 8 salt, 5 stereo, 10 other | same command, or the `#!` keys in `derived/template_products.psv` |
| rows reaching their verdict through the medium | 4 of 59 | same command |
| templates | 59 rows, all `tier=family`, 46 catalog classes -- unmoved | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps -- unmoved | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 90 / 40 -- unmoved | `data/catalog/COVERAGE_REPORT.md` |
| routes runnable / playable | 47 / 23 -- unmoved | `data/catalog/PLAYABLE.md` footer |
| why templates are silent | 16 no-substrate, 8 needs-more-than-a-pair, 0 cannot-fire; `pool_species` 290 | `classify_silent.py --check`, current |
| pKa table | 41 `AcidPair` rows over 8 classes | `python validation/pka_domains.py` panel 0 |
| corpus ions wanting a pKa | 444: 207 amine / 136 carboxylic / 101 phenoxide, over 48 routes | same command, panel 3 |
| the shelf | 72 rows, 43 natural / 25 intermediate / 4 bottle | `data/catalog/shelf.psv` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| expensive checks owed | `reachable` is DUE, 10 of 10 commits, last 2026-09-12 | `python tools/cadence.py` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, `CLAUDE.md`, the PSVs and `electrolyte.py` are CRLF; `check.ps1`, `docs/design/`, `tools/` and most tests are LF | `git ls-files --eol <file>` |

## Last session, in five lines

T1b built `tools/check_template_products.py`: every template row fired over the
catalog steps its class claims, product sets compared, 2.2 s, committed artefact
with a `--check` step in `check.ps1` and eight tests folded into
`test_template_table.py`. Its first version refused two rows that work — a
catalyst spelled `[OH3+:99]` and a fermentation whose step does not list water —
so a slot may now draw on a declared three-species medium and says when it did.
T1b's third clause is refused, not deferred: 132 of the 208 tests in the
fourteen per-template files build a network or run a vessel, so a product-set
check replaces none of them (`docs/design/per-template-tests-not-retired.md`).
No chemistry moved and no slow check was owed or run.

## Do this now

1. **T2 — extract literal templates from the catalog.** Spec in `BACKLOG.md`,
   now unblocked in full: T1b's check is what an extracted row must pass, and it
   already counted the two walls T2 will hit on the same corpus. Read
   `fable analysis/03-HOW-TO-ADD-A-TEMPLATE.md` and `docs/design/extraction-yield.md`
   first. Decide the two walls before writing the extractor, not after: the
   catalog spells a precipitated salt as one species where the engine holds its
   ions (8 rows), and declares a stereoisomer where a template emits the flat
   species (5 rows). T1.0's ceiling if every extractable row became a template
   is intersection 40 -> 66. Note the corpus carries no stoichiometric
   coefficients, so `corpus_balance.coefficients()` needs a smallest-integer
   step after it.
   *Done when:* extracted rows reach `pass` in `template_products.psv`, the
   report separates template-ready-via-family from via-literal, and
   `./check.ps1` is green.

2. **`reachable` is due and it is the user's call.** 35 minutes, 10 of 10
   commits, nothing has re-derived `derived/reachable.psv` since 2026-09-12.
   `python tools/build_reachable.py`, then `python tools/cadence.py --record
   reachable --result pass|fail --note "..."`. T27's four ions can be registered
   by the network now, so the pool may have moved; `classify_silent.py`
   regenerating byte-identical is no evidence, because it reads the stale
   artefact.
   *Done when:* `reachable.psv` is regenerated and the ledger row is recorded.

3. **T26 — a `dH_diss` of 0.0 cannot say "unmeasured", and it blocks two rows.**
   Spec in `BACKLOG.md`. Phenol and eugenol carry a default zero against
   4-nitrophenol's +19.8; methylammonium and anilinium against ammonium's +52.2
   and dimethylammonium's +50.0. Salicylaldehyde (8.37) and n,n-dimethylaniline
   (5.15) are sourced and waiting on it, 2 routes each.
   *Done when:* no `dH_diss` of 0.0 stands for an unmeasured quantity, those two
   rows are in, and the tolerance audit is re-run.

## Decisions already taken — do not reopen

- **The per-template test files are not retired and the file count is not a
  target.** 132 of their 208 tests build a network or run a vessel and assert a
  selectivity, a declared order, a standard state or a trajectory; the product
  check replaces at most one assertion in each. Argument and the per-file counts
  are in `docs/design/per-template-tests-not-retired.md`.
- **A step lists neither its solvent nor the ions the pot carries**, so
  `check_template_products.py` offers a slot water, hydronium and hydroxide and
  nothing else, and reports the four rows that needed it. An instrument that
  narrows its own pool reports the narrowing as a fact about the rows.
- **`salt` and `stereo` are rules over the missing SMILES, not lists of names**,
  so a new row lands in the right bucket with nobody editing anything.
- **The top of the pKa ranking is refused, not pending** (salicylic acid wants a
  microspecies, gallic acid spans 1.3 units, four have no rows); **both protons
  of a diacid come from one determination**; **a class-wide phenol pKa rule is
  refused** (`docs/design/phenol-pka-rule-refused.md`); **tannic acid's 35 shelf
  ions are a bound, not rows**; **a curated pKa moves the shelf and corpus ion
  instruments, never `COVERAGE_REPORT.md`**.
- **No species `build_network` registers may be unpriceable**; **a declared
  order may never be reversible**; **backwards is retrosynthesis**; **the
  expensive checks are clocked in commits**; **the headline is templates fired**.

## Open questions for the user

- **`reachable` is 35 minutes and it is due.** Task 2. Say whether to spend it,
  or it goes on being deferred.
- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is; without it T2 needs an RDKit-only atom mapper. Task 1 needs
  this answered or it needs the RDKit-only path.
- **`hydrogen-sulfide` is still a shelf row at tier `intermediate`** while the
  closure and a pyrrhotite flask both make it, and no catalog route does.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `*_data.py`, `reachable.psv`, `species_roles.psv`, `silent_templates.psv` or
  `template_products.psv`.
- Do not write a pKa you cannot source, put an estimator in front of one, or
  re-open the phenol refusal, the tannic acid bound or T23's refusal list.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, clear a red one, or rewrite a
  mixed-ending file whole — read and write bytes.

# NEXT — overwritten 2026-09-12

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-12. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,297 collected | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~75 s, green | ruff + docs + catalog + templates + silent + 56 smoke tests |
| full check | `./check.ps1 -Full`, ~2.5 min, green | adds both report `--check` ratchets |
| expensive checks owed | 2 of 5: the suite and the tolerance audit, neither ever recorded | `python tools/cadence.py` |
| templates | 57 rows, all `tier=family`, covering 46 catalog classes | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps, 240 classes | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 85 / 38 | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 21, three tiers deep; 44 runnable, 22 fed but unrunnable | `data/catalog/PLAYABLE.md` footer |
| rows extractable and uncovered | 174 of 377, in 132 classes (102 single-row) | `python validation/extraction_yield.py` |
| upper bound if all 174 became templates | template-ready 110, intersection 66 | same command, last two panels |
| named routes end to end | 17 routes in 32.6 s | `python examples/named_routes.py` |
| templates a natural pair can reach | 25 of 57; 32 silent and named | `data/catalog/derived/reachable.psv` |
| why the 32 are silent | 29 no-substrate, 1 needs-more-than-a-pair, 2 cannot-fire | `python tools/classify_silent.py` |
| what the small-molecule shelf can make | 41 species from 23 rows, frontier 0 — a closure, not a cap | `data/catalog/derived/silent_templates.psv` |
| missing substrates behind the 29 | 23, the largest being `[C-]#[O+]` at four templates | same file, THE WORK ORDER block |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs and the generated `*_data.py` are CRLF; most source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

T6 is in, and it cost 2 seconds rather than 35 minutes: the small-molecule half
of the shelf expands to a TRUE fixpoint, so every "the shelf cannot make this"
rests on a closure instead of a cap. The 32 silent templates group into 23
missing substrates; carbon monoxide alone holds four, and the shelf has its
ingredients but not the DIRECTION. The two `cannot-fire` rows turned out not to
be bugs. A cadence ledger now says which slow checks are owed.

## Do this now

1. **T7 — carbon monoxide, and the four templates waiting for it.** Spec in
   `BACKLOG.md`; the biggest single lever T6 found. The closure holds `O=C=O`
   and `[H][H]`, `water_gas_shift` is written CO + H2O to CO2 + H2 with
   `reversible=yes`, and discovery runs templates FORWARD ONLY, so the reaction
   that makes CO is derived and never found. Do not just flip the row — a CO
   and water flask would then discover nothing. Decide between a mirror row, a
   reverse-aware discovery pass, and a solid-carbon term, and write the reason
   down. Read `data/catalog/derived/silent_templates.psv`, then
   `amine_protonation`'s `notes` cell in `data/templates/templates.psv`.
   *Done when:* `[C-]#[O+]` is in the closure, `templates_fired` is re-measured,
   and the four rows have left `silent_templates.psv` or it says why not.

2. **T8 — the two templates a missing pKa switches off.** Spec in `BACKLOG.md`;
   small, and it is T5's question already answered for the shelf.
   `carboxylic_acid_dissociation` on `oleic-acid+water` and `phenol_dissociation`
   on `tannic-acid-core+water` both apply and lose the rewrite to an unpriceable
   ion. Source the oleate, the tannate phenoxide and hypochlorite, or record a
   refusal with its reason.
   *Done when:* `python tools/classify_silent.py` re-derives with those rows gone.

3. **R4/E3 — delete `discovery/refine.py`.** Decided in `BACKLOG.md`; half an
   hour, and it only removes code.
   *Done when:* the module, `discovery/__init__.py`, the README layer row and the
   `chemsim/__init__.py` mention are gone and `./check.ps1` is green.

The suite and `validation/tolerance_audit.py` are both DUE and neither has ever
been recorded. Ask the user, run them, and record the result either way with
`python tools/cadence.py --record <check> --result pass|fail --note "..."`.
T0.4 and T1b's second half need the suite and belong to that session.

## Decisions already taken — do not reopen

- **A closure beats a cap, and the shelf has one.** 23 of the 36 natural rows
  are at most 8 heavy atoms and expand to a fixpoint in under a second; the
  sugars and fats are what made a whole-shelf flask cap in its first round. Any
  threshold in (8, 10) picks the same 23 rows, so the constant is not a knob.
- **A slot match is a candidate, never a verdict.** Nitrate matches `[N;H0]=[O]`
  and is not nitric oxide; the rewrite that follows makes a five-valent nitrogen.
  Every witness is BUILT, and the network is the arbiter.
- **A template that applies and loses its rewrite is not a bug.** Both
  `cannot-fire` rows are the 30-row pKa table refusing to price a product ion,
  which is a reported coverage limit doing its job. The fix is a pKa, not code.
- **The expensive checks are clocked in COMMITS, not days.** A check that writes
  a committed artefact derives its own last run from `git log -1 -- <artefact>`
  and is never stamped by hand; one that leaves no trace carries a stamp, and
  `never` is DUE rather than clean. Every row names where the fix goes before a
  red result arrives, because that is the worst moment to be deciding it.
- **The headline is templates fired, not reactions reached.** 98% of T4's 24,828
  is four templates over a sugar frontier. What a shelf can DO is the count that
  fire at all and the names of the ones that do not.
- **A long sweep checkpoints and names the unit it is on.** `build_reachable`
  segfaults out of RDKit at a different pair each run, with no traceback.
- **An ion refusal is two claims and the overlay tells them apart.** Off,
  a charged species means the PROVIDER is wrong. Overlay ON and the ion not in
  its 30-row table, nothing prices it: `UnpricedIon`, a coverage limit. It drops
  the rewrite only for a template that NEEDS the price.
- **A PSV row is the template with its constructor's DEFAULT arguments.** The row
  carries the already-catalysed SMARTS and rescaled `A`; the constructors stay
  the public API for `catalyst=`, `eta_a=`, `A=`, `rho=`. All 57 rows are
  `liquid` or `gas` — a solid-phase reaction is an integrator TERM, not a row.
- **T2 and T3 go ahead.** 174 extractable-and-uncovered rows, +28 on the
  intersection at the ceiling. **`discovery/refine.py` is deleted, not wired.**
  **The README stays at 561 lines** until C1 moves the physics prose out.

## Open questions for the user

- **The suite has never been recorded as run.** 30 minutes on their own machine,
  and the ledger says DUE until somebody runs it once.
- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is. Without it T2 needs an RDKit-only mapper.
- **Species work is half of T2's payoff.** 36 of the 64 routes extraction would
  make template-ready are held by an unpriceable species.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `template_data.py` or
  `silent_templates.psv`; `--check` will fail. A template is edited in
  `data/templates/templates.psv`.
- Do not read `docs/history/` whole (grep it) and do not add a physics module;
  the engine is well ahead of the content. Do not stamp a row you did not run.

# NEXT — overwritten 2026-09-12

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-12. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,301 collected, 1,301 passed in 28m51s | `python -m pytest -q` |
| fast check | `./check.ps1`, ~80 s, green | ruff + docs + catalog + templates + silent + 60 smoke tests |
| full check | `./check.ps1 -Full`, ~2.5 min, green | adds both report `--check` ratchets |
| expensive checks owed | 0 of 5; all five recorded today | `python tools/cadence.py` |
| tolerance audit | recorded FAIL, 11m12s, 3 findings all pre-existing | `python validation/tolerance_audit.py` |
| templates | 57 rows, all `tier=family`, covering 46 catalog classes | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 85 / 38 — unmoved by T7 | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 21, three tiers deep; 44 runnable, 22 fed but unrunnable | `data/catalog/PLAYABLE.md` footer |
| templates a natural PAIR can reach | 29 of 57, up from 25; 28 silent and named | `data/catalog/derived/reachable.psv` |
| distinct reactions from 630 pairs | 24,836; 264 pairs capped, 320 inert, 0 crashed | same file |
| why the 28 are silent | 25 no-substrate, 1 needs-more-than-a-pair, 2 cannot-fire | `python tools/classify_silent.py` |
| what the small-molecule shelf can make | 43 species from 23 rows, frontier 0 — a closure, not a cap | `data/catalog/derived/silent_templates.psv` |
| missing substrates behind the 25 | 21, the largest being `[c][CX3H1]=[OX1]` at three templates | same file, THE WORK ORDER block |
| named routes end to end | 17 routes in 35.6 s, every yield bit-identical to pre-T7 | `python examples/named_routes.py` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs and the generated `*_data.py` are CRLF; most source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

T7 is in, and it was a defect rather than a missing row: discovery matched
REACTANT patterns only, so an equilibrium could be approached solely from the
side its SMARTS was typed on, and carbon dioxide plus hydrogen made nothing
while detailed balance held the reverse shift rate all along. `_expand_reverse`
now searches from the product side, the forward rewrite arbitrates every
proposal, and no rate is declared anywhere. `templates_fired` 25 -> 29 of 57.
All five expensive checks ran and are recorded, two of them for the first time.

## Do this now

1. **T9 — an aromatic aldehyde, the substrate three templates wait on.** Spec in
   `BACKLOG.md`; the top of the work order now that carbon monoxide is off it.
   `[c][CX3H1]=[OX1]` holds `cannizzaro_disproportionation`,
   `knoevenagel_doebner_condensation` and `perkin_condensation`; `[CX3H2]=[CX3]`,
   a terminal alkene, holds both hydroformylations, which T7 moved here from
   carbon monoxide. The shelf has eugenol and coniferyl alcohol and
   `vanillin_chemistry` cleaves them: read the WORK ORDER block of
   `data/catalog/derived/silent_templates.psv` and find out whether the closure
   reaches an aldehyde, and which template or shelf row is missing.
   *Done when:* either substrate is in the closure and those rows have left
   `silent_templates.psv`, or the file says which shelf row would put it there.

2. **T8 — the two templates a missing pKa switches off.** Spec in `BACKLOG.md`;
   small, and unchanged by T7. `carboxylic_acid_dissociation` on
   `oleic-acid+water` and `phenol_dissociation` on `tannic-acid-core+water` both
   apply and lose the rewrite to an unpriceable ion. Source the oleate, the
   tannate phenoxide and hypochlorite, or record a refusal with its reason.
   *Done when:* `python tools/classify_silent.py` re-derives with those rows gone.

3. **T10 — two examples print a digit that depends on the solver.** Spec in
   `BACKLOG.md`; the tolerance audit's own prescription, and the only red row in
   the ledger. `activity` moves 0.128% and `multistep_prep` 0.107% between the
   default tolerance and rtol 1e-8, and `named_routes` raises at 1e-8. All three
   are pre-existing, measured: both print byte-identical output on pre-T7 and
   post-T7 source. Give each its own tight tolerance, as `lime_cycle.py` does.
   *Done when:* the audit exits 0, or the ledger note says which is a refusal.

Nothing is due. A session that changes `network/` should ask about the suite
(~29 min) and the tolerance audit (~11 min) before closing.

## Decisions already taken — do not reopen

- **Backwards is retrosynthesis, and it must be forbidden to build up.** Forward
  expansion is bounded by what a flask can become; running a template backwards
  asks what could have made this, and every acid and alcohol is a candidate
  precursor of an absent ester. Aspirin and water reached the species cap up a
  polyester ladder. A reverse proposal is refused when it introduces a species
  heavier than what it came from — a comparison, not a threshold — and the
  refusals report through `notices`. What it gives up -- a reverse step that
  genuinely builds up -- is a coverage limit, and it says so.
- **The reverse rewrite proposes; the forward rewrite decides.** A reversed
  SMARTS is a textual swap and can propose what the forward rule would never
  make. Every candidate is re-run forward and kept only if it reproduces the
  products it came from, then built in the template's own orientation, so the
  reaction is the one forward discovery would have built — measured identical on
  key, `A` and `Ea`. A mirror row with kinetics of its own was refused on rule 9.
- **`amine_protonation` and `ester_hydrolysis` stay as written.** The direction
  they were forced into is now a choice; re-typing a row buys only risk.
- **A closure beats a cap, and the shelf has one.** 23 natural rows at most 8
  heavy atoms reach a fixpoint in under a second; any threshold in (8, 10) picks
  the same rows, so the constant is not a knob.
- **A template that applies and loses its rewrite is not a bug.** Both
  `cannot-fire` rows are the 30-row pKa table refusing to price a product ion.
  The fix is a pKa, not code.
- **The expensive checks are clocked in COMMITS**, and a check writing a
  committed artefact derives its own last run from git rather than a stamp.
- **The headline is templates fired, not reactions reached.** 98% of the 24,836
  is four templates over a sugar frontier.
- **A long sweep checkpoints and names the unit it is on.** `build_reachable`
  segfaults out of RDKit at a different pair each run -- it resumed twice today,
  then finished clean. Re-run it until it exits 0.
- **T2 and T3 go ahead** (174 extractable-and-uncovered rows, +28 at the
  ceiling). **`discovery/refine.py` is deleted, not wired** (R4/E3, still open),
  and **the README stays at 561 lines** until C1.

## Open questions for the user

- **`rxnmapper` as a curation-time dependency** for T2, build-time only as
  `chemicals` is. Without it T2 needs an RDKit-only mapper.
- **Species work is half of T2's payoff**: 36 of the 64 routes extraction would
  make template-ready are held by an unpriceable species.

## Do not

- Do not hand-edit `COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md`,
  `template_data.py`, `reachable.psv` or `silent_templates.psv`; `--check` fails.
  A template is edited in `data/templates/templates.psv`.
- Do not read `docs/history/` whole (grep it) and do not add a physics module.
- Do not stamp a cadence row you did not run, and do not clear a red one.

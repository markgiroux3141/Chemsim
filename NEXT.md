# NEXT — overwritten 2026-09-12

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-12. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,303 collected; last full run 1,301 passed in 28m51s (two commits ago) | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~105 s, green | ruff + docs + catalog + templates + silent + 62 smoke tests |
| expensive checks owed | `playable` DUE at 9 commits and cannot clear — re-run green today at 48 s, byte-identical output, so no commit touches it (T11) | `python tools/cadence.py` |
| tolerance audit | recorded FAIL two commits ago, 11m12s, 3 findings all pre-existing (T10) | `python validation/tolerance_audit.py` |
| templates | 57 rows, all `tier=family`, covering 46 catalog classes | `python tools/build_templates.py --check` |
| catalog | 1,583 compounds, 173 routes, 377 steps | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 85 / 38 — unmoved by T9 | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 21, three tiers deep; 44 runnable, 22 fed but unrunnable | `data/catalog/PLAYABLE.md` footer |
| templates a natural PAIR can reach | 29 of 57; 28 silent and named | `data/catalog/derived/reachable.psv` |
| why the 28 are silent | 20 no-substrate, 6 needs-more-than-a-pair, 2 cannot-fire | `python tools/classify_silent.py` |
| what the shelf's pool holds | 282 species: 43 from the closure (frontier 0) plus 13 one-generation tiers (frontier 304); 42 more discovered and refused a price | `data/catalog/derived/silent_templates.psv` |
| the work order | 22 blocking substrates, 18 of which block one template and nothing else; head is `[S;H2]` at 2 | same file, THE WORK ORDER block |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed: `BACKLOG.md`, `NEXT.md`, `CHANGELOG.md`, the PSVs and `tools/classify_silent.py` are CRLF, `tests/test_reachable.py` is BOTH, most source is LF | `git ls-files --eol <file>` |

## Last session, in five lines

T9 was filed as "source an aromatic aldehyde" and turned out to be three defects
in the instrument that asked for it. Coniferyl alcohol plus air makes vanillin in
one generation with a template already in the 57, but the classifier's pool was
shelf species plus the small-molecule closure, and coniferyl is too big for it.
The pool now has a bounded second tier, the witness search minimises cost rather
than set size, and a template is charged to every missing slot rather than the
first. no-substrate 25 -> 20. No engine code was touched.

## Do this now

1. **T8 — the templates a missing pKa switches off.** Spec in `BACKLOG.md`;
   small. `carboxylic_acid_dissociation` on `gypsum+oleic-acid` and
   `phenol_dissociation` on `eugenol+gypsum` both apply and lose the rewrite to
   an ion `properties/electrolyte._PAIRS` cannot price; `halogen_disproportionation`
   is the same refusal on the closure. Source the oleate, the eugenolate and
   hypochlorite, or record a refusal with its reason. Note T9 renamed both
   witnesses — gypsum is a dissolved row, so it carries the water the old
   witnesses named; the ions are unchanged.
   *Done when:* `python tools/classify_silent.py` re-derives with those rows gone.

2. **T12 — hydrogen sulfide, the new head of the work order.** Spec in
   `BACKLOG.md`. `[S;H2]` blocks `claus_comproportionation` and
   `hydrogen_sulfide_combustion` and neither is short of anything else, so it is
   the only substrate in the file worth two templates. Hydrogen sulfide is a
   shelf row already, at tier `intermediate`; the sweep is over `natural`, and
   pyrite, galena and pyrrhotite are all natural rows the closure makes no H2S
   from. Find the missing template between a metal sulfide and an acid, or
   record that the gap is the shelf tier and not the chemistry.
   *Done when:* `[S;H2]` has left the work order, or `BACKLOG.md` says which
   template would put it there.

3. **T10 — two examples print a digit that depends on the solver.** Spec in
   `BACKLOG.md`; the tolerance audit's own prescription and the only red row in
   the ledger. `activity` moves 0.128% and `multistep_prep` 0.107% between the
   default tolerance and rtol 1e-8, and `named_routes` raises at 1e-8. All three
   are pre-existing and measured. Give each its own tight tolerance, as
   `lime_cycle.py` does. Costs a ~11 min audit run — ask before taking it.
   *Done when:* the audit exits 0, or the ledger note says which is a refusal.

`playable` is due and cannot clear until T11 lands; it was re-run green today.
A session that changes `network/`, `numerics/` or `vessel/` should ask about the
suite (~29 min) and the tolerance audit (~11 min) before closing.

## Decisions already taken — do not reopen

- **The closure is the small-molecule half and stays a fixpoint.** 23 natural
  rows at most 8 heavy atoms reach it in under a second; any threshold in (8, 10)
  picks the same rows. The whole shelf cannot be closed — the sugars cap a flask
  in the first round — so reaching past the closure is a BOUNDED tier that
  reports its frontier, never a wider closure that pretends to be one.
- **A witness is ranked by cost, and a plain shelf row outranks a tier.** A
  witness of shelf rows is a flask the pair sweep actually held, so what happens
  in it is a measurement; one reaching through the closure is an argument about
  what the shelf could become. Same cost, weaker evidence loses.
- **A template is charged to every missing slot.** Charging it to the first is
  what put an aromatic aldehyde at the head of a work order on three templates,
  exactly one of which it would have unblocked. `blocked` and `alone` are both
  printed and `alone` is the queue's sort key.
- **`UnpricedIon`, not `OutsideEstimatorDomain`, gates the pool.** A lattice and
  a bare element are refused by the same `get` and are neither missing nor
  unusable — calcite and iron are shelf rows. Filtering on the parent threw 15
  of the closure's 43 species away and called them missing measurements.
- **Backwards is retrosynthesis and must be forbidden to build up.** A reverse
  proposal is refused when it introduces a species heavier than what it came
  from, and the refusals report through `notices`. The reverse rewrite proposes;
  the forward rewrite decides.
- **A template that applies and loses its rewrite is not a bug.** Both
  `cannot-fire` rows are the 30-row pKa table refusing a product ion. T8.
- **The expensive checks are clocked in COMMITS**, and a check writing a
  committed artefact derives its own last run from git rather than a stamp.
- **The headline is templates fired, not reactions reached.** 98% of the 24,836
  is four templates over a sugar frontier.
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
- Do not rewrite a mixed-ending file whole: `tests/test_reachable.py` holds 93
  CRLF lines and 109 LF ones, and `read_text` then `write_text` flattens it.

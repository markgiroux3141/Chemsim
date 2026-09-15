# Backlog

Open work only. A finished item is **deleted** — its record is the
`CHANGELOG.md` entry and the commit. No ticks, no post-mortems. S = under two
hours, M = a session, L = two. Order is priority order: do not start a Tier 2
item while a Tier 0 item is open.

---

## Tier 0 — make the repo cheap to enter

### T0.4 — a fast test subset (S)
No pytest markers exist, so running less than the 30-minute suite means naming
files. `pytest --durations=0 -q` once (ask first), mark everything over 2 s
`slow`, register the marker, put `pytest -m "not slow"` in `check.ps1`.
**Done when:** `pytest -m "not slow"` is green in under three minutes.

---

## Tier 1 — change the slope of coverage

240 reaction classes over 377 catalog steps, 169 used by exactly one step; 116
have a template, 64 of them hand-typed. Ceiling 110 template-ready / ~66
runnable. What is left of the slope is promoting rows (T2c). Argued in
`docs/design/route-coverage-ceiling.md`, `docs/design/extraction-yield.md` and
`fable analysis/05-COVERAGE-STRATEGY.md`.

### DECIDED and closed — the argument is in the file named, do not reopen
- **T30, the nitration row** (`docs/design/two-refused-template-classes.md`).
  In at `tier=family`. One class grant moved two scoreboards by one on two
  DIFFERENT routes: template-ready 65 → 66 on `guncotton`, runnable 50 → 51 on
  `nitroglycerin-route`.
- **T28, the air-oxidation split** (same file). Refused on arithmetic: `judge`
  scores ONE application of ONE row and three of the four stages already have
  templates. Still worth a bench: a `family` `autoxidation` row for a primary
  benzylic methyl, worth nothing to the scoreboard.
- **T2, the extractor's two walls** (`tools/extract_templates.py` docstring).
  `salt` (75 steps, a claim about the MEDIUM the corpus never makes) and
  `stereo` (24, a configuration the mechanism does not fix) are refusals, each
  wanting the per-class judgement a `family` row IS.
- **T31, the six scoreboard pins.** Green. Four were one defect: T2 split
  `cc.TEMPLATE_CLASSES` into every-tier and `FAMILY_`, the helpers kept the
  all-tier dict, and `bp.RUNNABLE`/`bp.PLAYABLE` are family — a level on one
  measurement path against a set on the other, and every DIFFERENCE they pin
  held on both. Two were real moves, re-pinned with their reasons in the tests.
  A green `pytest -q` was the half owed; T32 ran it.
- **T32, a route charged with its own target.** Closed. `needs` unioned
  `route_roles().catalysts` in and a catalyst is derived by IDENTITY, so four
  routes making their target in one row and consuming it in the next demanded
  it as a charge. Dropping the union IS `first_made < first_used`, provably: a
  catalyst's own step makes and uses it, so the ORDER rule had it already.
  `route_reachable` had the mirror defect. Reasoning in both docstrings.
- **The furfural false credit cannot pay, for a structural reason** — 29b's
  spelling makes xylose chargeable, so the class need never be covered for the
  route to reach its target. Argued in `test_vitriol.py`'s pentosan test.

### T33 — `CHANGELOG.md` is past the 400 lines its own header rolls at (S, from T30)
Nothing enforces it (`check_docs.py` caps an ENTRY, not the file), so it is a
convention going stale rather than a red check. A whole-file move, CRLF.
**Done when:** under 400 lines, the rolled half one new `docs/history/` file.

### T2c — promote a literal row, the cheap way to buy a playable route (M)
`PLAYABLE.md` scores the `family` tier alone, because that is what
`load_templates` loads. Granting the extracted rows takes runnable 50 -> 60 and
playable 23 -> 25 (`acetic-anhydride-ketene`, `wood-distillation`); §8b marks
the work-order classes that already have a row. A promotion is not a copy:
check the atom mapping by hand (T2d), argue a barrier, move the row into
`templates.psv` at `tier=family`.
**Done when:** one class moves tier and `PLAYABLE.md`'s headline moves with it.

### T2d — the gate cannot see a wrong mapping that makes the right species (S)
Verification compares canonical SMILES, the engine's own identity, so a
symmetric product hides a mis-mapping: the Diels-Alder row joins the ring at the
wrong pair of carbons and still writes cyclohexene, and the Lebedev row joins its
two ethanols at a pair the mechanism does not. Both are right on their own step,
which is all a `literal` row claims, and both would misplace a substituent -- so
this gates T2c. Re-run each row on ONE substituted analogue and report where
the substituent lands.
**Done when:** the count of rows whose mapping their own step does not constrain
is measured, or the idea is refused in writing.

### T29 — `ammonia` and `platinum`: the last red test, and it is a design call (S)
`test_playable_levers.py::test_the_shelf_file_holds_exactly_what_this_audit_measured`
is the ONLY failure in the suite (T32's run, 1 failed / 1360 passed). Its two
halves were independent and T32 closed the scorer half, so what is left is
genuine: `andrussow`'s platinum and `tollens-test`'s ammonia are real same-step
catalysts nothing in the corpus makes, and the audit is right to demand them.
`shelf.psv` is hand-maintained game design, so a row is a decision about what a
player is GIVEN -- and the file's own header already argues SEVEN unpriceable
natural rows into staying. Either is defensible; giving a player platinum is
the larger claim, and `shelf.psv`'s NOT_NATURAL_NOTES calls the catalyst metals
the rule that decides the third tier. READ THE FAILURE, NOT THIS ITEM: the set
moves with every template session.
**Done when:** each species the test names is a shelf row with a note, or is
argued down in `shelf.psv`'s header, and the test is green.

### T23 — the corpus half of the pKa gap, one row at a time (M, running)
`validation/pka_domains.py` prints the queue and the route-demand ranking; take
it from there rather than from a count typed here. Method: query PubChem
`iupacpka` by CID, prefer a determination carrying a temperature series so one
paper gives both the pKa and a van't Hoff `dH_diss`, both protons of a diacid.
**The top of the ranking is decided, not pending:** salicylic acid (4 routes)
wants the phenol-first MICROSPECIES and CID 338 has no microscopic constant;
both macroscopic ones are in. Gallic acid (2) spans 3.13 to 4.46 on pKa1 at the
SAME ionic strength, so report the spread. Salicylaldehyde and
n,n-dimethylaniline wait on T26.
**Done when:** each new row is in `_PAIRS` with a named source, panel 3's count
has moved, and `test_protonation.py`'s `len(ions)` prompt is answered with a
re-measured number, not only bumped.

### T26 — a `dH_diss` of 0.0 cannot say "unmeasured", and it is blocking rows (S)
`AcidPair.dH_diss` defaults to 0.0, indistinguishable in that field from a
measured zero — a claim the dissociation is athermal. Nearly true for a
carboxylic acid, badly false for a phenol or an amine: phenol and eugenol carry
a default zero against 4-nitrophenol's +19.8 and coniferyl alcohol's +24.4,
methylammonium and anilinium against ammonium's +52.2. Give `AcidPair` a way to
say the enthalpy is unknown and the providers a way to report it — a coverage
limit, so rule 10 applies.
**It blocks two ready rows**, both worth 2 routes and both next in T23's ranking:
salicylaldehyde 8.37 (Green and Alexander, Aust. J. Chem. 18 (1965) 329; their
pK = 8.37 − 0.78 sqrt(I) is the I = 0 value) and n,n-dimethylaniline 5.15
(Bacarella, Grunwald, Marshall and Purlee, J. Org. Chem. 20 (1955) 747, I = 0).
Neither has a temperature series, so writing them mints two false zeros.
**Done when:** no row in `_PAIRS` carries a `dH_diss` of 0.0 that stands for an
unmeasured quantity, those two rows are in, and the tolerance audit is re-run
because equilibria above 298 K move.

### T25 — the mineral-oxyacid gap is not a pKa gap (S, found in T5)
89 missing ions in that class and ZERO want a pKa: every one has a parent the
engine cannot price, so an `AcidPair` would be skipped by `ion_thermochemistry`
the day it was written. `ThermochemistryProvider` refuses benzenesulfonic,
p-toluenesulfonic and sulfanilic acid and eleven routes name one; the fix is
neutral thermochemistry for them, curated or the estimator group.
**Done when:** those sulfonic acids price as neutrals, or the missing estimator
group is named in a refusal, and the audit's mineral-oxyacid row leaves zero.

### T11 — an artefact-backed check that changes nothing can never clear (S)
Found 2026-09-12 and seen again in T23: `playable` re-ran with BYTE-IDENTICAL
output, so no commit touches `PLAYABLE.md` to derive a last-run from, and
`--record` refuses an artefact-backed row by design. The row reads DUE until the
artefact's CONTENT moves, which is the one thing a passing check does not do.
The fix is a third state — a run confirming no change. Unchanged by T28 or T30,
each of which happened to move the content it re-ran.
**Done when:** re-running an artefact-backed check whose output is unchanged
clears its DUE, and `python tools/cadence.py` explains which of the two happened.

### T10 — two examples print a digit that depends on the solver (S)
`validation/tolerance_audit.py` is red on `activity` and `multistep_prep`: a
quotable digit moves between the default tolerance and rtol 1e-8, and
`named_routes` raises there. Pre-existing, and reproduced to the same digits on
three runs now (T23, T27, T28), so the debt is stable and a run that MOVES is a
real finding -- `python tools/cadence.py` prints the digits. The fix the audit
prescribes is a tight per-example tolerance, as `lime_cycle.py` has.
**Done when:** `python validation/tolerance_audit.py` exits 0, or the ledger
note says which of the three is a standing refusal and why.

### T21 — the manual quotes the scoreboard by hand and nothing checks it (S, found in T17)
`docs/manual/chapters/30-playable.md` carried "21 of 173 playable" against
`PLAYABLE.md`'s 22 — stale by a session, and nothing failed. The chapter stays
prose, so the fix is a check rather than a generator: parse what it states
against `PLAYABLE.md`'s footer and §1 table. Chapters 29 and 30 quote counts.
**Done when:** a command in `check.ps1` fails on a manual chapter whose quoted
playable counts do not match the artefact, and it is green today.

### T22 — two guards T13 made unreachable, and an instrument that now reports 0 (S, found in T13)
T13's invariant -- no species `build_network` registers is unpriceable -- makes
the two `UnpricedIon` catches in `_concrete_reactions` (Evans-Polanyi, T8, and
detailed balance, T1d) unreachable through it, and T13 deleted the tests
that pinned them. Same shape in `classify_silent.py`: its `priceable()` filter
dropped 41 species and now drops 0. Neither is wrong; both are untested claims
about a path nobody takes. Delete, or keep as defence against a hand-built
`ReactionNetwork` with one line saying the builder is what makes it dead.
**Done when:** each site is deleted or carries that line, and no test pins a
branch `build_network` cannot reach.

### T19 — the diacid is the bigger half (S, both ends now measured)
230 of the 342 pairs needing their own measurement are polyprotic, and a diacid
is not the plateau twice. Both ends are in `_PAIRS`: malonic 2.85 / 5.70 (one
CH2, 2.85 units apart) and adipic 4.42 / 5.41 (four CH2, 0.99).
`carboxylic_pka.domain` rightly refuses both. Where it flattens between them is
the open question, and succinic or glutaric -- one paper for both protons --
settles it.
**Done when:** a second domain or a refusal with its reasoning is written down.

### T20 — one template makes an unbounded oligoester series (S, found in T14)
Not a pKa item. Oleic acid hydrates and esterifies onto itself: T14's sweep
reached 243 oligoesters six condensations deep and 11 of 36 flasks hit the cap.
A bound question -- molar mass, condensation depth, or the cap naming it.
**Done when:** most of the 36 flasks reach a fixpoint, or `Snapshot.notices`
names the template filling the cap.

### T16 — the other loose sulfur-dioxide slot (S, found in T12)
`sulfur_dioxide_oxidation_by_nitrogen_dioxide` still writes SO2 as
`[O:1]=[S:2]=[O:3]`, the pattern that made `claus_comproportionation` take
sixteen minutes once H2S existed. It matches a SULFATE, and two shelf rows are
sulfates -- three slots not eight, so not a bomb, but every flask holding a
vitriol does work it throws away on a five-bonded sulfur. Tighten to
`[OX1]=[SX2]=[OX1]` as T12 did. Chain 2's carrier step, so the tolerance audit
is owed and Ea/A must not move.
**Done when:** the slot matches one shelf species, and
`tests/test_lead_chamber.py` is green with the same numbers.

---

## Tier 2 — engine work that moves playability

### R6 / E1 — a lattice becomes its ions (M)
A term consuming a `mineral_data` lattice and producing its ions in the solid
block, priced from the same Ksp `PrecipitationArrays` already uses, so a rock
dissolves. The design is argued in `docs/history/milestones/` — grep `R6`. This
is the one engine item that unblocks the "rock into water" half of the shelf, and
it converges the two representations of a rock that today have disjoint
mechanics.
**Done when:** 0.5 mol NaCl lattice into 30 mol water reaches the same end state
as 0.5 mol of its ions, and the six shelf rows that had to pick a representation
regain the other mechanic.

### R4 / E3 — delete `discovery/refine.py` (S, decided)
Decision 2026-09-01: delete it, and with it the `[done]` on Layer 4.5 in the
README's layer table and the `discovery` layer in `chemsim/__init__.py`. The
reasoning, so it is not relitigated: rate-aware pruning exists to make a network
tractable, the R-series measured a fixpoint as free for the chemistry that
matters, the species cap already bounds the rest and reports itself, and pruning
would drop species silently where rule 10 forbids it. The module is a sketch --
zero callers, zero tests, a duplicated `build_network`, a `_rates_of` judging
species on forward kinetics alone -- and T2's rows are not in the default
library, so nothing here has changed.
**Done when:** the module, its `__init__.py`, the layer row and the README
claim are gone, and `./check.ps1` is green.

### E2 — "react until done" as the default (S)
The R-series measured a fixpoint as free for the whole inorganic half of the
shelf (sulfur/air/water/NO₂ closes at 14 species in 1.5 s). `generations=None`
does it today and is not the default. In `ui/examples.py:bench()`, default to
`None` unless a loaded template is self-feeding (a product matching one of its
own reactant slots, computed at load), else `generations=1` with a visible
notice. A player never sees the word "generation".
**Done when:** sulfur + air + water reaches sulfuric acid with no button press
and glucose + water still terminates.

### E4 — decompose `make_rhs` (L)
`numerics/vessel_integrator.py:1781` is 673 lines wrapping a 506-line closure
with ~40 captured locals; nothing inside is testable alone, though it visually
contains its phase blocks already (volumes, Born transfer, per-layer reaction,
surface, solid-state, transport). Extract them as module-level functions over
arrays, and define the `Protocol` in `numerics/integrator.py` that
`VesselIntegrator` and `RigIntegrator` both satisfy -- eleven identically named
methods and no base class.
**Done when:** no function in `numerics/` exceeds 120 lines of code, and
`validation/tolerance_audit.py` before and after shows no trajectory change
beyond solver tolerance, with the difference reported.

### E5 — the RDKit boundary claim (S)
`README.md:40` and `chemsim/__init__.py:14` say nothing above Layer 0 imports
rdkit. `reactions/template.py:25-26`, `reactions/hammett.py:182` and
`properties/fragmentation.py` do — and `fragmentation.py:58` carries a comment
saying "No rdkit here". Either move `ReactionFromSmarts`/`RunReactants` behind a
`matter/rewrite.py`, route `hammett.survey` through `Molecule`, and add a test
that greps `src/chemsim` outside `matter/` for `rdkit`; or delete the claim.
**Done when:** the claim and the code agree.

---

## Tier 3 — cleanup, only once Tier 1 has landed

### C1 — move the essays out of the source (M, repeating)
First target is `validation/catalog_coverage.py`: T1 left **656 lines of taxonomy
prose around a 14-entry dict**, and that prose is the record of why `combustion`,
`deprotonation`, `acid-base` and `redox` were split — worth keeping, in
`docs/design/`, with a pointer. `ReactionTemplate`'s class docstring is 200
lines; `_dryout_gates` is 158 lines around 3 of code; the `rhs` closure is 56%
comments. The physics is good and the file is wrong.
**Done when:** `python tools/check_docs.py` shows the `src/chemsim` glyph budget
under 50 and no comment carries a milestone tag.

### C2 — `validation/` becomes tests or checks (M)
41 scripts, 3,285 prints, 9 asserts, no runner and no exit codes: a lab notebook
labelled a validation harness. Each script either gains asserts and moves to
`tests/` under `slow`, or exits non-zero on a regression and joins `check.ps1
--full`.
**Done when:** every file in `validation/` fails loudly when its own claim breaks.

### C3 — extract the live design rationale from `GAME_DESIGN.md` (S)
It is 58 KB and quotes `SAVE_VERSION` as 4 in one place and 7 in another; it is
9. Each load-bearing argument -- a stock is a composition not (name, purity), a
gate must be a mechanism, lattice versus ions -- becomes one `docs/design/`
file; the rest is an index or `docs/history/`.
**Done when:** no root markdown quotes a `SAVE_VERSION`, each argument once.

---

## Not doing, and why

| not doing | because |
|---|---|
| a Debye–Hückel / electrolyte activity model | γ for ions blocks no route |
| LHHW or Michaelis–Menten rate laws | no playable route needs one |
| a Rust kernel | the RHS is 231 µs; the cost is numpy dispatch, not arithmetic |
| another coverage-scoreboard correction | four are in; the instrument is fine |

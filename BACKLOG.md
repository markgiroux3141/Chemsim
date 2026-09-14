# Backlog

Open work only. A finished item is **deleted** from this file — its record is the
`CHANGELOG.md` entry and the commit. No ticks, no post-mortems.

Sizing: S = under two hours, M = a session, L = two sessions.
Order is priority order. Do not start a Tier 2 item while a Tier 0 item is open.

---

## Tier 0 — make the repo cheap to enter

### T0.4 — a fast test subset (S)
There are no pytest markers at all, so the only way to run less than the
30-minute suite is to name files. Run `python -m pytest --durations=0 -q` once
(ask first), mark everything over 2 s `@pytest.mark.slow`, register the marker in
`pyproject.toml`, and put `pytest -m "not slow"` into `check.ps1`.
**Done when:** `pytest -m "not slow"` is green in under three minutes.

---

## Tier 1 — change the slope of coverage

The measurement behind this tier: 240 reaction classes over 377 catalog steps,
169 used by exactly one step, and the bottleneck is that a template is a
hand-written Python function. T1.0 measured the gate on 2026-09-02: 174 of 377
rows resolve, balance and sit in an uncovered class, over 132 classes of which
102 hold one row; ceiling if all became templates is intersection 38 -> 66. The
argument is `docs/design/extraction-yield.md` and
`fable analysis/05-COVERAGE-STRATEGY.md`; do not re-narrate it here.

### T2 — extract literal templates from the catalog (L, unblocked: T1.0 and T1 are in)
`tools/extract_templates.py`: resolve each step's reactants and products to
SMILES, infer stoichiometry, atom-map, extract a reaction SMARTS with one bond of
context, verify it regenerates the products, assign kinetics from a class policy
table, write the row with `tier=literal`. Note what the analysis missed: the
corpus carries no stoichiometric coefficients at all, so balancing is an
inference and not a check, and the LP that does it returns a vector that is not
unique when the element matrix has a 2-D nullspace (`phthalic-anhydride-route`
step 2 comes back fractional) — so a smallest-integer-vector step is needed after
`corpus_balance.coefficients()`. Rows that fail go to `needs_stoichiometry.psv`
or `needs_review.psv`, never silently.
`tools/check_template_products.py` is the check the rows must pass (T1b, in),
and its 2026-09-13 run over the 59 family rows names the two walls an extractor
meets on this same corpus: **8 of the 23 non-passing rows are missing only a
salt** the catalog spells as one species where the engine holds its ions, and
**5 are missing only a stereoisomer** a template emits flat. Decide both before
writing an extractor, not after; the counts are the `#!` keys at the foot of
`data/catalog/derived/template_products.psv`.
**Done when:** the extracted rows reach `pass` in `template_products.psv` and
the report distinguishes template-ready-via-family from via-literal.

### T3 — generalise the literal rows that cluster (M, bounded)
Cluster literal rows by reacting centre; where three or more share one, write a
family row, confirm it covers every member, retire the members. T1.0 found only
6 uncovered classes with three or more extractable rows (24 rows in all), so this
is one or two sessions, not a repeating one.
**Done when:** the 6 families are written or refused with a reason, and the
retired row count is in `CHANGELOG.md`.

### T23 — the corpus half of the pKa gap, one row at a time (M, running)
T27 wrote four rows in route-demand order and `validation/pka_domains.py` panel
3 now reads 444 corpus ions wanting a pKa (207 amine / 136 carboxylic / 101
phenoxide) over 27 / 17 / 19 routes. Keep going down it: query PubChem
`iupacpka` by CID, prefer a determination carrying a temperature series so one
paper gives both the pKa and a van't Hoff `dH_diss`, and take both protons of a
diacid from one.
**The top of the ranking is decided, not pending:** salicylic acid (4 routes)
wants the phenol-first MICROSPECIES, and CID 338 has pKa1, pKa2 and a Hammett
pKaH but nothing microscopic; both macroscopic constants are already in. Gallic
acid (2) spans 3.13 to 4.46 on pKa1 at the SAME ionic strength, so report the
spread. Indigo (3), bisphenol-a (2), hydroxylamine (2) and indoxyl (2, CID
50591) have no rows; salicylaldehyde and n,n-dimethylaniline wait on T26.
**Done when:** each new row is in `_PAIRS` with a named source, panel 3's count
has moved, and the `len(ions)` prompt in `tests/test_protonation.py` is answered
with a re-measured coverage number, not only bumped.

### T26 — a `dH_diss` of 0.0 cannot say "unmeasured", and it is blocking rows (S)
`AcidPair.dH_diss` defaults to 0.0, which in that field is indistinguishable
from a measured zero — a claim the dissociation is athermal. For a carboxylic
acid that is nearly true and the module docstring says so; for a phenol or an
amine it is badly false. Phenol and eugenol carry a default zero against
4-nitrophenol's +19.8 and coniferyl alcohol's +24.4; methylammonium and
anilinium carry one against ammonium's +52.2 and T27's dimethylammonium at
+50.0. Give `AcidPair` a way to say the enthalpy is unknown, then the providers
a way to report it — a coverage limit, so rule 10 applies.
**It blocks two ready rows**, both worth 2 routes and both next in T23's
ranking: salicylaldehyde 8.37 (Green and Alexander, Aust. J. Chem. 18 (1965)
329, whose pK = 8.37 − 0.78 sqrt(I) makes it the I = 0 value) and
n,n-dimethylaniline 5.15 (Bacarella, Grunwald, Marshall and Purlee, J. Org.
Chem. 20 (1955) 747, extrapolated to I = 0). Neither carries a temperature
series, so writing them today mints two new false zeros.
**Done when:** no row in `_PAIRS` carries a `dH_diss` of 0.0 that stands for an
unmeasured quantity, those two rows are in, and the tolerance audit is re-run
because equilibria above 298 K move.

### T25 — the mineral-oxyacid gap is not a pKa gap (S, found in T5)
89 missing ions in that class and ZERO want a pKa: every one has a parent the
engine cannot price at all, so an `AcidPair` would be skipped by
`ion_thermochemistry` the day it was written. `ThermochemistryProvider` refuses
benzenesulfonic, p-toluenesulfonic and sulfanilic acid and eleven routes name
one; the fix is neutral thermochemistry for the aryl sulfonic acids, curated or
the estimator group it lacks.
**Done when:** the sulfonic acids a catalog route names price as neutrals, or
the missing estimator group is named in a refusal, and the audit's
mineral-oxyacid row moves off zero.

### T11 — an artefact-backed check that changes nothing can never clear (S)
Found 2026-09-12 while closing T7 and seen again in T23: `playable` re-ran in
45 s and produced BYTE-IDENTICAL output, so there is no commit touching
`data/catalog/PLAYABLE.md` to derive a last-run from, and `--record` refuses an
artefact-backed row by design. The row reads DUE until the artefact's CONTENT
happens to move, which is the one thing a passing check does not do. Deriving
the date from git is still right — it stops a row being stamped by hand — so the
fix is a third state: a run confirming no change, distinct from a stamp and from
a commit. The same trap waits for `reachable`.
**Done when:** re-running an artefact-backed check whose output is unchanged
clears its DUE, and `python tools/cadence.py` explains which of the two happened.

### T10 — two examples print a digit that depends on the solver (S)
`validation/tolerance_audit.py` comes back red on `activity` (worst 0.1277%)
and `multistep_prep` (0.1073%): a quotable digit moves between the default
tolerance and rtol 1e-8. Measured PRE-EXISTING -- both print byte-identical
output on pre-T7 and post-T7 source -- so this is debt the audit found rather
than damage. `named_routes` additionally raises at rtol 1e-8, which the audit
diagnoses in-run as older than S13. Two runs on 2026-09-13, either side of
T23's ion rows, reproduced all three to those digits: the debt is stable, so a
future run that moves is a real finding. The fix the audit prescribes is to
give each example its own tight tolerance, as `lime_cycle.py` and
`roasting_and_the_catalyst_gate.py` already do.
**Done when:** `python validation/tolerance_audit.py` exits 0, or the ledger
note says which of the three is a standing refusal and why.

### T21 — the manual quotes the scoreboard by hand and nothing checks it (S, found in T17)
`docs/manual/chapters/30-playable.md` carried "21 of 173 playable" against
`PLAYABLE.md`'s 22 — stale by a session, and nothing failed. T17 re-typed six
numbers there by hand, the same debt one session older. The chapter is prose and
should stay prose, so the fix is a check, not a generator: parse the numbers the
chapter states against `PLAYABLE.md`'s footer and §1 table and fail when they
disagree. Chapters 29 and 30 are the two that quote generated counts.
**Done when:** a command in `check.ps1` fails on a manual chapter whose quoted
playable counts do not match the artefact, and it is green today.

### T22 — two guards T13 made unreachable, and an instrument that now reports 0 (S, found in T13)
T13's invariant is that no species `build_network` registers is unpriceable, so
the two `UnpricedIon` catches inside `_concrete_reactions` — the Evans-Polanyi
barrier (T8) and detailed balance (T1d) — are unreachable through
`build_network`, and T13 deleted the two tests that pinned them. Same shape in
`tools/classify_silent.py`: its `priceable()` post-filter dropped 41 species and
now drops 0 every time. Neither is wrong; both are untested claims about a path
nobody takes. Decide per site: delete, or keep as defence against a hand-built
`ReactionNetwork` with one line saying the builder is what makes it dead.
**Done when:** each of the three sites is deleted or carries the one line, and
no test pins a branch `build_network` cannot reach.

### T19 — the diacid is the bigger half (S, both ends now measured)
230 of the 342 pairs needing their own measurement are polyprotic, and a diacid
is not the plateau twice. Both ends of the curve are now in `_PAIRS`, each from
one determination: malonic 2.85 / 5.70, one CH2 and 2.85 units of separation
(T23); adipic 4.42 / 5.41, four CH2 and 0.99 (T27). `carboxylic_pka.domain`
rightly refuses both. Where it flattens between them is the open question and
succinic or glutaric, one paper for both protons, settles it.
**Done when:** a second domain or a refusal with its reasoning is written down.

### T20 — one template makes an unbounded oligoester series (S, found in T14)
Not a pKa item. Oleic acid hydrates and esterifies onto itself: T14's sweep
reached 243 distinct oligoesters six condensations deep and 11 of its 36 flasks
hit the cap — P0's "31500 reactions per 9 credited steps" again. This is a bound
question: molar mass, condensation depth, or the cap naming the template.
**Done when:** most of the 36 flasks reach a fixpoint, or `Snapshot.notices`
names the template filling the cap.

### T16 — the other loose sulfur-dioxide slot (S, found in T12)
`sulfur_dioxide_oxidation_by_nitrogen_dioxide` still writes SO2 as
`[O:1]=[S:2]=[O:3]`, the pattern that made `claus_comproportionation` take
sixteen minutes once H2S existed. It matches a SULFATE too, and two shelf rows
are sulfates. Not a bomb -- three slots, not eight -- but the rewrite it then
attempts makes a five-bonded sulfur that sanitisation throws away, so it does
work it cannot use on every flask holding a vitriol. Tighten it to
`[OX1]=[SX2]=[OX1]` as T12 did for the Claus row. Chain 2's carrier step, so the
tolerance audit is owed and the Ea/A must not move.
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
would drop species silently where rule 10 forbids it. The module is a sketch:
zero callers, zero tests, a duplicated `build_network`, and a `_rates_of` that
judges species on forward kinetics with no derived reverse, no declared orders,
no Hammett and no electrode work. If T1/T2 make networks explode, rebuild it
where the charge is known and make it report what it dropped.
**Done when:** the module, its `discovery/__init__.py`, the layer row and the
README claim are gone, and `./check.ps1` is green.

### E2 — "react until done" as the default (S)
The R-series measured a fixpoint as free for the whole inorganic half of the
shelf (sulfur/air/water/NO₂ closes at 14 species in 1.5 s). `generations=None`
does it today and is not the default. In `ui/examples.py:bench()`, default to
`None` unless a template in the loaded library is self-feeding (a product
matching one of its own reactant slots — compute once at load), and fall back to
`generations=1` with a visible notice when one is. A player should never see the
word "generation".
**Done when:** sulfur + air + water reaches sulfuric acid with no button press
and glucose + water still terminates.

### E4 — decompose `make_rhs` (L)
`numerics/vessel_integrator.py:1781` is 673 lines wrapping a 506-line closure
with ~40 captured locals; nothing inside is independently testable or
profilable, though it visually contains its phase blocks already (volumes, Born
transfer, per-layer reaction, surface, solid-state, transport). Extract them as
module-level functions over arrays. Define the `Protocol` in
`numerics/integrator.py` that `VesselIntegrator` and `RigIntegrator` both
satisfy — they share eleven identically named methods and no base class.
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
The warning glyph appears ~1,040 times in non-generated source and milestone tags ~300 times.
First target is now `validation/catalog_coverage.py`: T1 deleted the 46
template-backed entries of `TEMPLATE_CLASSES` and derives them from the table,
which left **656 lines of taxonomy prose around a 14-entry dict**. The prose is
the record of why `combustion`, `deprotonation`, `acid-base` and `redox` were
split, and it is worth keeping — in `docs/design/`, with a pointer.
`ReactionTemplate`'s class docstring is 200 lines; `_dryout_gates` is 158 lines
around 3 lines of code; the `rhs` closure is 56% comments, many of them
changelog entries. The physics in them is good and the file is wrong. Move it to
`docs/manual/chapters/`, leave a one-line pointer.
**Done when:** `python tools/check_docs.py` shows the `src/chemsim` glyph budget
under 50 and no comment carries a milestone tag.

### C2 — `validation/` becomes tests or checks (M)
41 scripts, 3,285 `print` calls, 9 `assert`s, no runner and no exit codes: a lab
notebook labelled a validation harness. Each script either gains asserts and
moves to `tests/` under `slow`, or exits non-zero on a regression and joins
`check.ps1 --full`.
**Done when:** every file in `validation/` fails loudly when its own claim breaks.

### C3 — extract the live design rationale from `GAME_DESIGN.md` (S)
It is 58 KB and quotes `SAVE_VERSION` as 4 in one place and 7 in another; it is
9. The load-bearing arguments — "a stock is a composition, not (name, purity)",
"a gate must be a mechanism", lattice versus ions — become one `docs/design/`
file each, stripped of narrative. What is left becomes an index or goes to
`docs/history/`.
**Done when:** no root markdown file quotes a `SAVE_VERSION` and each argument
lives in exactly one place.

---

## Not doing, and why

| not doing | because |
|---|---|
| a Debye–Hückel / electrolyte activity model | γ for ions blocks no route |
| LHHW or Michaelis–Menten rate laws | no playable route needs one |
| a Rust kernel | the RHS is 231 µs; the cost is numpy dispatch, not arithmetic |
| another coverage-scoreboard correction | four are in; the instrument is fine |
| appending to anything in `docs/history/` | frozen |
| a markdown file over 300 lines | nobody reads it |

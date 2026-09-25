# Backlog

Open work only. A finished item is **deleted** — its record is the
`CHANGELOG.md` entry and the commit. No ticks, no post-mortems. S = under two
hours, M = a session, L = two. Order is priority order: do not start a Tier 2
item while a Tier 0 item is open.

---

## Tier 0 — make the repo cheap to enter

### T0.4 — a fast test subset (S)
No pytest markers exist, so running less than the 30-minute suite means naming
files. CI now publishes the ten slowest modules as notices on every run
(`python tools/ci_status.py --slowest`), which is the measurement this item
was waiting on: mark those `slow`, register the marker, put `pytest -m "not
slow"` in `check.ps1` in place of the hand-named `$SmokeTests`.
**Done when:** `pytest -m "not slow"` is green in under three minutes.

---

## Tier 1 — coverage of chemistry, measured by the benchmark

`data/benchmark/reactions.psv` is the coverage metric (216 held-out textbook
cases over 63 classes, scored by `tools/benchmark.py`); the 173-route catalog is
the game's progression metric, ceiling ~66 runnable
(`docs/design/route-coverage-ceiling.md`). The session skill's Step 0b ranks
the work.

### DECIDED and closed — the argument is in the file named, do not reopen
- **The benchmark, 2026-09-24** (`tools/benchmark.py` docstring). A family row
  is a claim about a mechanism and must pass its class's held-out cases; a
  `wrong-product` there is how a mis-mapped row shows itself. It cannot say
  which product wins -- that is B4.
- **Extractor v2's two walls** (`tools/extract_templates.py` docstring). An
  aqueous salt is read as its net ionic equation and a furnace's stays refused
  as a lattice (E1); a stereo step is extracted flat. The checker judges in the
  same engine reading, so the two instruments cannot disagree.
- **A literal row that cannot be priced is still written.** Pricing is the
  species-ready axis; refusing the row would count the gap twice. The table's
  footer counts it instead.
- **T30** (nitration row, `docs/design/two-refused-template-classes.md`), **T28**
  (air-oxidation split refused, same file), **T31/T32** (scoreboard pins, a
  route charged with its own target: reasoning in the test and `needs`
  docstrings), **the furfural false credit** (`test_vitriol.py`).
- **Left out on purpose, with the reason in the row's note:** halide as an SN2
  nucleophile (halide exchange through one irreversible row reaches a ratio
  nothing chose), radical halogenation (discovery is rate-blind and the row
  matches every C-H), secondary alcohols in the acyclic acetal (two slots over
  a sugar multiply by every hydroxyl).

### B1 — price what the new rows are waiting on (M, repeating)
The benchmark's `family_unpriced` cases and `literal.psv`'s `#! unpriced`
footer are the work order: the rewrite is right and a species it makes or
takes has no thermochemistry. Phenyl isocyanate blocks three literal rows;
triphenylphosphine oxide, the Grignard reagents, the diazonium ions and the
enolates (ions, so a pKa) block benchmark classes. Source every value; never
recall one (memory: formation-data-sourcing).
**Done when:** `family_runs` in `data/benchmark/scores.psv` has moved, each new
entry names its source, and `./check.ps1` is green.

### B2 — ethylene is the +4 grant (S)
`PLAYABLE.md`: ethylene blocks four runnable routes and granting it is worth
+4, the largest single grant on the board. The corpus makes it (ethanol
dehydration, the cracker), so the question is why that route is not playable,
not a purchase. Read `bp.needs` for the routes that make it.
**Done when:** playable moves, or the blocker upstream of ethylene is named in
`NEXT.md` as the next task.

### B3 — the benchmark's remaining family failures (S each)
From `data/benchmark/scores.psv`: aliphatic Knoevenagel, a Perkin anhydride
with a CH2, a non-aryl alkene isomerisation, formaldehyde Cannizzaro -- four
existing rows narrower than their mechanism, and widening one moves pins in
its own test file; Finkelstein (needs a reversible halide-exchange row);
radical halogenation (needs a gate, see DECIDED); alkane dehydrogenation.
Also `check_template_products.cause` files a row under `other` when the stereo
sits on the step's REACTANT (the camphor Markovnikov row).
**Done when:** each is a passing class or a one-line refusal in its row.

### B4 — which product wins is not measured (M)
Every new row offers each regiochemistry at one rate: Diels-Alder orientation,
Zaitsev, epoxide opening, and ortho/meta/para on the EAS rows, which carry no
Hammett rho (only nitration has one, sourced). A benchmark `pass` means the
product is among the outcomes. Add a verdict that runs the case in a `Vessel`
and asks whether the expected product is the MAJOR one, and source rho values
for halogenation, sulfonation and Friedel-Crafts before writing them.
**Done when:** the benchmark reports a `major` verdict for the EAS and
Markovnikov classes, and each rho written names its source.

### B5 — grow the benchmark (S, repeating)
Classes a chemist would expect that the catalog does not name -- Grignard
addition to a carbonyl, reductive amination, Baeyer-Villiger, the Mannich --
get cases first and rows second. Inorganic one-offs stay out: a class that
exists for one furnace step has no held-out substrate. An external set
(USPTO-50k, open, coarse class labels) is an option that needs a download.
**Done when:** each new class has 3+ cases that parse, balance and are held
out, and its row count is in the CHANGELOG entry.

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
A re-run with byte-identical output touches no file, so `cadence.py` derives no
new last-run and `--record` refuses an artefact-backed row by design: it reads
DUE until the content moves. It needs a third state, a run confirming no change.
**Done when:** such a re-run clears its DUE and `cadence.py` says which happened.

### T10 — two examples print a digit that depends on the solver (S)
`validation/tolerance_audit.py` is red on `activity` and `multistep_prep`: a
quotable digit moves between the default tolerance and rtol 1e-8, and
`named_routes` raises there. Pre-existing, and reproduced to the same digits on
four runs now (T23, T27, T28, T33), so the debt is stable and a run that MOVES is a
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

### T22 — two guards T13 made unreachable (S, found in T13)
No species `build_network` registers is unpriceable, so the two `UnpricedIon`
catches in `_concrete_reactions` and `classify_silent.priceable()` (now drops 0)
guard a path nobody takes. Delete each, or keep it with one line saying the
builder is what makes it dead.
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

### T34 — nitric acid is the only substrate blocking two templates (S, found in T33)
T33's sweep regeneration put T30's `nitrate_esterification` on the silent list,
and it wants the same slot `aromatic_nitration` does. So
`[OX2H1][N+](=[O])[O-]` now reads `2 blocked, 2 alone` at the top of
`silent_templates.psv`'s work order, where every other row is 1 and 1: one
species unblocks two templates, and T30's row has never fired from the shelf.
The open question is the tier -- the corpus makes nitric acid, so this is a
`shelf.psv` argument, not a purchase, and it belongs with the playable audit
rather than against it.
**Done when:** the nitric acid slot is off `silent_templates.psv`'s work order
and its two templates leave the silent list, or the tier argument is refused.

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
Decided 2026-09-01: delete the module, its `__init__.py`, the `[done]` on Layer
4.5 in the README and the `discovery` layer in `chemsim/__init__.py`. Pruning
would drop species silently where rule 10 forbids it, the species cap already
bounds a network and reports itself, and the module has zero callers and tests.
**Done when:** all four are gone and `./check.ps1` is green.

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
| scoreboard work while no check is red | at most one session in four; the session skill counts |

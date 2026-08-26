We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M8, M12, S1–S6 are DONE.**

# ⚠⚠ START WITH: RUN THE FULL SUITE. IT IS THE FIRST THING, NOT THE LAST.

```bash
python -m pytest -q                          # ~12.5 min. DO THIS FIRST.
```

**M8 changed five files under `src/` and DID NOT re-run the suite** — the session
ended on the user's instruction to hand the run forward rather than keep the
machine busy. So the baseline is genuinely unverified, and unlike S6's deliberate
skip there is no by-construction argument available: `reactions/thermo.py`,
`reactions/template.py`, `reactions/reaction.py`, `network/builder.py` and
`constants.py` were all touched.

What M8 *did* verify, so you know what a failure would mean:

* **all 14 pre-M8 examples byte-identical** (`esterification`, `thermochemistry`,
  `competing_pathways`, `vessel`, `activity`, `extraction`, `multistep_prep`,
  `wait_until`, `workshop`, `lime_cycle`, `mercury_retort`,
  `roasting_and_the_catalyst_gate`, `named_routes`, `oil_of_vitriol`), captured
  by stashing `src/` and running both ways — apart from RDKit log timestamps and
  two wall-clock readings;
* **99 targeted tests green**: `test_reaction_thermo`, `test_detailed_balance`,
  `test_evans_polanyi`, `test_engine`, `test_competing_templates`,
  `test_catalysis`, `test_electrochemistry`;
* **76 more green** on the ion side (`test_born`, `test_solids_and_ions`,
  `test_precipitation`, `test_solubility_product`), because M8's brief predicted
  it would break the five pH values and it did not;
* `ruff` clean across `src tests examples validation tools`.

**Baseline at the end of S5: 826 passed in 12:32.** Expect 826 + 21 = **847**.
⚠ If it is green, say so and move on — do not re-verify what is already listed
above. If it is RED, that is the session's first job and the list above tells you
where NOT to look.

Then, and only then:

```bash
python validation/cell_potentials.py         # M8's standing audit, seconds
python examples/electrolysis_cell.py         # M8, five panels, ~2 min
python validation/catalog_coverage.py        # ⚠ READ THE 'BOTH' LINE: 20/173, ~10 s
python tools/build_route_index.py            # ⚠ the artefact nothing reads
python validation/jacobian_bound.py          # ⚠ S5's standing audit, ~1 min
python validation/rate_ceiling.py            # M12's standing audit, seconds
python validation/tolerance_audit.py         # S2's standing audit, ~8 min
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE AND THE TOLERANCE AUDIT ARE MINUTES OF SATURATED CPU ON THE USER'S
OWN MACHINE.** Say what a long run will cost before starting one. The tolerance
audit is another ~8 minutes and **`examples/plate_column.py` alone is 12.**

---

# ⚠⚠ THEN: KEEP TAKING CONTENT. M8 IS THE FIRST SESSION IN SEVEN TO MOVE THE NUMBER.

Template-ready went **25 at M5 → 28 through six engine sessions → 31 now**, and
the intersection — the only column a route can be judged on — went **17 → 20**.
M8 is +3 on both, which is more than S1+S3+S4+S5 combined. **The lesson held:
`MILESTONES.md`'s own instruction is that M5 onward is CONTENT.**

⚠ **AND READ §M8 §2 BEFORE TRUSTING ANY UNLOCK NUMBER IN THE QUEUE BELOW.** M8
took the greedy curve's **top row since M1** — `electrolysis`, +3 routes — and
M1's own row check cut it to **+1**: its four rows are three mechanisms, split at
the cathode. The `RUNNABLE` column was right (+3, predicted exactly) while the
`ALONE` column was not (+3, not +5). **Two milestones running, the intersection
is the trustworthy column and the unlock count is the one that lies.**

The queue, re-measured after M8 and ranked by RUNNABLE:

1. **⚠⚠ `isomerisation` — +3 unlocked / +2 RUNNABLE, AND IT IS A SPLIT JOB, NOT A
   TEMPLATE JOB.** Top of the table, and **M5 explicitly REFUSED it**: its three
   rows are *"a cis/trans isomerisation on a nickel surface, an aldose-ketose
   interconversion, and Wohler's ammonium cyanate rearrangement"* — three
   mechanisms under one label, the `deprotonation` mistake waiting to happen.
   That refusal still stands and it is now the *reason to take it*, on M8's own
   precedent: **split first, then credit what is built.** Predict the split
   before running it. ⚠ And read `hydrogenation-margarine` step 2 closely —
   `oleic-acid + hydrogen + nickel -> elaidic-acid + nickel` **does not balance**
   (an H2 goes in and nothing comes out), which is S3's *which one is WRONG*
   question arriving before you write a line.
2. **⚠ `crosslinking` — +2 / +2, AND MEASURE WHETHER IT IS CREDITABLE AT ALL
   BEFORE COSTING IT.** Second on the table, and **both its rows produce
   MARKERS**: `polyisoprene-unit + S8 + ZnO -> vulcanised-rubber-marker` and
   `gallic-acid + collagen-marker -> tanned-leather-marker + water`. A marker has
   no molecular graph. M5 refused `separation` for exactly this — *"crediting it
   would have moved the headline number by one while making zero routes
   runnable"* — and `pyrolysis` for half of it. **This may be two routes' worth
   of headline for zero runnable chemistry, which is the trade M1 exists to
   refuse.** It is a cheap thing to measure and an expensive thing to assume.
3. **⚠ THE BARE-ELEMENT GAP — 15 ROUTES, STILL THE CHEAPEST ITEM HERE, AND
   UNTOUCHED SINCE S6 NAMED IT.** 45 compounds are refused as *a bare element
   symbol*, correctly — the ideal-gas value for `[C]` is the ATOM at Gf +671
   kJ/mol while the charcoal in the flask is 0. Leverage: `cobalt` **+3**, then
   `carbon-graphite` / `platinum` / `silver` at **+2** each. The generated table
   is in `data/catalog/COVERAGE_REPORT.md` under *"The next one along"*.
   ⚠⚠ **AND IT LANDS ON THE SAME COLUMN A TEMPLATE DOES** — S6 moved no
   template-ready route and moved the INTERSECTION 12 → 17.
   ⚠ **IT HAS A LAYERING QUESTION IN FRONT OF IT, SO IT IS NOT A LOOKUP.**
   `element_data.REFERENCE_STATES` already carries S0 and the reference state for
   Zn(s), Ag(s), C(graphite) — but with `smiles=None`, because a SOLID reference
   state had nowhere to live until the solid block existed. Mercury resolves
   today precisely because its standard state is a LIQUID and so it got a SMILES.
   Missing is that binding plus the `Cp_solid`/`Vm_solid` pair `priced_solid`
   demands. **Whether that belongs in `element_data` or `mineral_data` is a real
   decision — a metal is not a mineral** — and it owes a predict-then-measure pass.
   ⚠ It also unblocks two of M8's own leftovers: `downs-cell` and `hall-heroult`
   are blocked on `sodium` / `aluminium` / `carbon-graphite` **as well as** on
   `molten-salt-electrolysis`.
4. **⚠ THE CURRENT BUDGET — M8's OWN NAMED GAP, AND IT IS A LAYER 4 TERM.** Two
   electrode reactions in one cell divide nothing here, so both run at full rate
   and activation selectivity washes out as the barrier floors at zero:
   k(brine)/k(water) is **4.76e+17 at 2.5 V, 5.94 at 3.0, 1.00 at 4.0**. The
   selective window in this engine is ~2.2–2.7 V where a real chloralkali cell
   holds 99% at 3 V and above. ⚠ It is worth **ZERO new routes** — chloralkali
   already runs — so take it for the mechanic, not the scoreboard, and say which
   you are doing. ⚠ `test_the_activation_selectivity_washes_out_at_high_voltage`
   pins the gap; if you close it, that test SHOULD fail and be rewritten.
5. **⚠ S5's SIXTH INSTRUMENT FAULT, STILL OPEN AND STILL CHEAP.**
   `tolerance_audit.py` reports `QUOTABLE DIGITS MOVE, worst 99.85%` on
   `oil_of_vitriol`, and **that headline is wrong**: four of its five moved lines
   are the CREATED-MATTER residual and every one gets SMALLER, on rows
   `NEXT_SESSION.md` already carries as "NOT AN INVARIANT". **A
   relative-difference test is meaningless on a column whose converged value is
   zero.** `REPORT_ABS` exists for this and 2.9e-05 clears it. Reported, not
   fixed — raising it blunts the test for genuine quantities, so picking the
   number owes its own predict-then-measure pass.
6. **Pyrite** — one mineral entry from `pyrite-roasting` running. Blocked on the
   same-database rule (`Hfs` in WEBBOOK, `S0s` in nothing), which is a rule worth
   keeping, so this needs a SOURCE and not a workaround. ⚠ It is one of the
   **11 template-ready routes that cannot run**, so closing it is +1 on the
   intersection for one curated entry.
7. **⚠⚠ THE BURNER — THE LIVE FRAGILITY, STILL DEMOTED AND STILL NOT DISMISSED.**
   **53 s at rtol 1e-8 against 0.8 s at the default.** S5 bounded the CRASH and
   explicitly did not bound the THRASHING. BDF is struggling with a liquid layer
   holding **1e-29 mol**, which `LAYER_REABSORB` drains toward zero without ever
   reaching it. **The question nobody has asked is whether a layer below
   `LAYER_EPS` should be *merged discretely* at a step boundary rather than
   drained continuously forever.** ⚠ `merge_phases` already does exactly that at
   the `run` boundary — so this may be a matter of WHEN IT IS CALLED, not of a
   new mechanic. **Measure the layer-2 inventory over the failing run before
   designing anything.** It fires only at rtol 1e-8, so nothing a player does
   reaches it.
8. **⚠ `hydrolysis` — AND READ S3's LANDMINE FIRST.** It unlocks **exactly ONE
   route alone, `vitriol-distillation`**, and that route's step 1 reads
   `-> iron-ii-OXIDE` while the engine makes HEMATITE. The whole standalone
   payoff is a route carrying a step whose product the engine does not make.
   ⚠ S3 and S4 disagree about what to do with such a row — read §S3's "which one
   is WRONG" check before deciding.
9. **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
   re-scope before scheduling)**, **M9 (polymers, 12 routes)**, **M10 (the site
   balance S1 did not build, 8 routes)**, and **`molten-salt-electrolysis`**
   (a MELT is not a phase this project has — M8's other leftover, and it needs
   item 3 as well before either route could run).
10. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
    the *deposition-needs-a-seed* half into a real bound in
    `SolidStateArrays.units`, which is why the mercury retort does not re-form
    its oxide when cooled 289 K below the oxide's threshold. What is still not
    expressible is a solid appearing from NO solid — `hydride-thermal-deposition`
    (`arsine -> arsenic + hydrogen`) is still a mechanism gap for that reason.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§M8, §S1, §S3, §S4, §S5 and §S6 are the ones to
  read**: M8's brief predicted the wrong failure AND named a class that split
  under its own row check, S1's brief asked for one mechanism and the arithmetic
  said two, S3 found the instrument's own OUTPUT was not diffable, S4's brief
  said to reverse a re-label and the arithmetic said keep, **S5's brief named the
  wrong LAYER**, and **S6's brief handed it a number that was wrong.**
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1, 86 is S2, 87 is
  S3, 88 is S4, 89 is S5, 90 is S6, 91 is M8.**
NEXT_SESSION.md — the invariants table at the bottom is the contract, and M8
  added seven rows to it. ⚠ Read the two warnings above it before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **M8's split of
  `electrolysis`**, **S3's split of `thermal-decomposition`** and **S4's decision
  NOT to un-split `roasting-to-metal`**, and `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-electrochemistry,
  chemsim-species-ready-minerals, chemsim-jacobian-bound,
  chemsim-zero-jacobian-column (⚠ its diagnosis was CORRECTED by S5),
  chemsim-element-floor, chemsim-mercury-retort and chemsim-generated-artefacts.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 38 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, a catalyst you have to actually put in
the flask, a route that nothing declares, a Jacobian that cannot be probed outside
its own state, and **a dial that decomposes things in the order their chemistry
says they should**. `SAVE_VERSION` is **5**.
Coverage: **38/220 classes**, **38 templates**, **31/173 template-ready**,
**65/173 species-ready** — and ⚠⚠ **20/173 BOTH, which is the only one of the
three a route can be judged on.**

---

# ⚠⚠ WHAT M8 TURNED OUT TO BE: THE MECHANIC WAS FREE AND THE CLASS WAS NOT

**+2 classes (36 → 38 of 220), +3 template-ready (28 → 31), +3 RUNNABLE
(17 → 20).** Four templates, one field on `ReactionTemplate`, one field on
`ConcreteReaction`, one `if` in `reaction_deltas`, one keyword on
`build_network`. **No new term in Layer 4, no new phase, no new gate.**

A cell does electrical work `w = n F E`. `electrons` says how many cross the
external circuit, `cell_potential` says what the supply is set to, and
`reaction_deltas` subtracts their product from **both** dH and dG. A reaction
whose chemistry costs less than the cell supplies runs, and the crossing is
`E_dec = dG_chem / (n F)` — every number in an electrochemical series.

| what | measured |
|---|---|
| water splitting `E_dec` | **1.441 V** (book 1.229) |
| brine `E_dec` | **2.362 V** (book 2.186) |
| bromide `E_dec` | **2.061 V** (book 1.894) |
| brine cell, 1 h, 2.5 V | **0.0177 mol Cl2**, 8.9e-19 mol O2 |
| brine cell, 1 h, 4.0 V | 0.0169 mol Cl2, **0.53 mol O2** |
| adiponitrile at 3 V | **65.6% conversion**; nothing at 2 V |

## ⚠ 1. THE SHIFT GOES ON dH AS WELL AS dG

E is held fixed by the supply, so `w` does not vary with T, and a T-independent
shift is an ENTHALPY shift. In dG alone, `reaction_entropy` (`dS = (dH-dG)/T`)
books the whole cell voltage as reaction entropy and K drifts as `exp(w/RT)`.
Shifting both leaves dS exactly the chemistry's — **and the energy balance comes
out right for free**, since `to_arrays` reads the same dH: heat to the flask is
`w - dH_chem`, zero at the thermoneutral voltage, which is what a real cell does.

## ⚠⚠ 2. EVANS-POLANYI ON AN ELECTRODE REACTION *IS* BUTLER-VOLMER

An identity, not a resemblance. With the work in dH,
`Ea + alpha(dH_chem - nFE)` is `Ea - alpha nF eta` up to the entropy term — the
Tafel slope, with `alpha` at its conventional 0.5. So **`Ea` on an electrode
template is the ACTIVATION OVERPOTENTIAL in energy units, `n F eta_a`**, and the
kinetics needed no new field either. Oxygen evolution 0.80 V, chlorine 0.40 V,
Kolbe 1.20 V — measured quantities with a century of Tafel data behind them, and
**that gap is why a brine cell makes chlorine rather than the oxygen its
thermodynamics prefers.**

## ⚠⚠ 3. THE BRIEF PREDICTED THE WRONG FAILURE

M8's brief budgeted for re-deriving the five pH values: *"a half-cell potential
is not consumed as a number: it puts the ion back into an equilibrium the kernel
evaluates."* **Measured: unmoved, 76 tests.** There is no half-cell potential.
Every template is a WHOLE CELL — electrons cancelled, charge balanced — because a
half reaction does not conserve charge and `_element_charge_balance` rejects it,
and because that is what the catalog rows already say. **So no electrode
potential was ever curated**: dG of a half reaction needs a reference electrode,
dG of a cell does not.
⚠ And the brief's `done when` asked that "the current is the control". It is not
— the VOLTAGE is. See queue item 4.

## ⚠⚠ 4. THE NEW AUDIT FOUND A PRE-EXISTING ERROR ON ITS FIRST RUN

`validation/cell_potentials.py` panel 2: the brine cell's dS is out by
**−591 J/(mol K)** and bromide's by −738, which REVERSES the sign of dE/dT —
every cell here wants more voltage when heated and every real one wants less.
This project's ions are derived from measured pKa against its OWN water, and its
own water is priced on the **ideal-gas** basis (Hf −241.8, not the aqueous
−285.8). For a reaction that conserves water the offset cancels and nothing has
noticed since the electrolyte model was built; **every cell reaction consumes
water and makes hydroxide**, so it does not. **dG survives it and dS does not.**
Quote E_dec at 298 K; do NOT quote its temperature derivative, and do NOT read a
cell's HEAT.

## ⚠⚠ 5. THE SOLVER SAID THE PRE-EXPONENTIAL WAS THE WRONG KIND OF NUMBER

At `A = 1e10` — an order under `COLLISION_LIMIT`, which is how every other
pre-exponential here is bounded — a cell at 3.0 V ate 0.2 mol of chloride inside
a nanosecond and `Vessel.run` died with *required step size is less than spacing
between numbers* after **4.2e-09 s of 3600 s**. The rate cap had been firing at
the low end too. Same wrong ceiling from two ends. **An electrode reaction is not
two molecules meeting** — it happens on a SURFACE, its rate scales with electrode
AREA and not volume, and 1e10 asserts every chloride is touching the anode. The
right units are a current density over an area, `5e-8 = j0 * a / (n F)` =
`1e-3 * 10 / (2*96485)`, and the check that makes it defensible is that **it
comes back out as an ampere**.

## ⚠ 6. THE ADIPONITRILE ROW IS NOT AN ELECTRODE REACTION

The row reads `AN + water -> ADN + oxygen`, so a fourth electron-carrying
template was the expected shape. Measured: the CELL is uphill at **+212.7
kJ/mol** but `2 AN + H2 -> ADN` is **downhill at −171.7**. The voltage buys the
HYDROGEN, not the carbon–carbon bond. So the route is `water_electrolysis` +
`alkene_hydrodimerisation` (`electrons=0`) and the row's stoichiometry — oxygen
included — EMERGES. ⚠ Cost stated: routing electrons through free H2 puts the
threshold at water's 1.441 V instead of its own 0.551 V, **0.89 V too high**.
⚠ The lump alternative was measured and refused — 6 slots, FOURTH order in the
limiting reagent, `sulfur_combustion`'s stall in the case not forgiven.

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ THE BURNER IS STILL 53 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT.** The
crash is bounded; the thrashing is not. **Queue item 7, not the next job.** It
fires only at rtol 1e-8, so nothing a player does reaches it.

**2. ⚠⚠ NEW IN M8: NO CURRENT BUDGET.** Two electrode reactions in one cell
divide nothing, so every reaction the cell clears runs at its own full rate at
once. Selectivity washes out above ~2.7 V. Measured, pinned by a test as a LIMIT,
queue item 4.

**3. ⚠⚠ NEW IN M8, AND PRE-EXISTING: THE ION TABLE'S MIXED BASIS.** dG survives
it, dS does not. See §4 above. **The first mechanism to depend on it is M8**, and
it will bite anything else that writes a reaction consuming water and making
hydroxide.

**4. ⚠ A SOLID DECOMPOSITION'S FORWARD CONSTANT CROSSES THE UNIMOLECULAR CEILING
AT 3710 K**, inside the RHS's 5000 K clamp. New in S4, reported by
`validation/rate_ceiling.py`'s fourth panel. Not guarded, on the stated policy:
`A0` divides out of `flux = 0` and moves a CLOCK, not an equilibrium.

**5. ⚠ `detailed_balance`'s RATE CAP COMPARES A CATALYSED PRE-EXPONENTIAL AGAINST
A LIMIT NOT IN ITS UNITS**, so it would fire 10x too eagerly. It does not fire on
any of the five catalysed templates, pinned by a test.

**6. THE DEFAULT TOLERANCE, BOUNDED RATHER THAN OPEN.** ⚠ `tolerance_audit.py` is
a STANDING audit: run it after touching the RHS. Its three self-check examples
must come out OUTPUT IDENTICAL. ⚠ Its `QUOTABLE DIGITS MOVE` headline on
`oil_of_vitriol` is WRONG — queue item 5.

**7. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever. M10.

**8. ⚠ NUCLEATION, HALF modelled.** A solid can only grow where one already is.
What is still not expressible is a solid appearing from NO solid.

**9. ⚠ LIQUID MERCURY IS 99.85% HELD IDEAL.** Named and bounded, not hidden.

**10. ⚠ THE FLAT COLUMN IS STILL FLAT, AND THAT IS CORRECT.** A species genuinely
absent from a sealed flask has an identically zero Jacobian column, and **zero is
its derivative.**

**11. ⚠ 45 COMPOUNDS ARE STILL REFUSED AS A BARE ELEMENT, BLOCKING 15 ROUTES.**
Queue item 3.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's clamp is
`T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Nineteen times now. ⚠ **AND M8 ADDS A COROLLARY: THE SOLVER IS PART
OF THE ARITHMETIC.** M8's dG bound was right and its `A` was three orders wrong,
and nothing caught that until a vessel actually ran. **An arithmetic bound tells
you whether a mechanism CAN go; only running it tells you whether it can be
INTEGRATED.**
⚠⚠ **A CONSTANT'S UNITS ARE WHAT MAKE ITS VALUE DEFENSIBLE, AND "the units every
other constant here uses" IS NOT AUTOMATICALLY THE RIGHT UNIT.** Every
pre-exponential in this project is bounded by a collision frequency; an electrode
reaction is not a collision, and reusing that ceiling cost a dead solver.
⚠⚠ **A RECORDED MEASUREMENT IS A CLAIM ABOUT A PAST STATE OF THE CODE, AND IT CAN
BE WRONG ABOUT ITS OWN SUBJECT.** S5: four of five recorded triggers had stopped
firing. S6: a measured number and a list of ids, both wrong. **M8: the greedy
curve's TOP ROW, unchallenged since M1, was worth a third of what it claimed.**
⚠⚠ **A CLASS IS A MECHANISM CLAIM — AND THE ROW CHECK IS WORTH MOST EXACTLY WHERE
THE UNLOCK COUNT IS HIGHEST.** It is cheap to apply to a class worth +1. Applied
to the one at the top of the queue it cost two thirds of the headline, which is
when it was doing its job.
⚠⚠ **TWO COLUMNS THAT ANSWER INDEPENDENT QUESTIONS DO NOT BOUND EACH OTHER —
COMPUTE THE INTERSECTION.** And note which column survived M8's split: RUNNABLE
was right, ALONE was not, because the rows the split lost were blocked on a
species anyway.
⚠ **A BRIEF'S EXPECTED OUTCOME IS A HYPOTHESIS.** S4's said a re-label would be
reversed; running it both ways said keep. S1's asked for one mechanism and got
two. S5's named a layer and the measurement named another. S6's named a size.
**M8's named a FAILURE — the five pH values — that never came, and the reason it
never came (there is no half-cell potential) is the milestone's best finding.**
**Run the number for the option you are not taking.**
⚠ **PREDICT THE NUMBER BEFORE YOU MEASURE IT.** S3 predicted +2/+0; S4 +1/+1;
S6 predicted 14 and measured 16. **M8 predicted 38/220 classes, 31 template-ready
and 20 BOTH, and all three came out exactly** — which is what makes the ONE
prediction it got wrong (the selectivity window) worth reading.
⚠ **VERIFY A CREDIT BY RUNNING IT, NOT BY READING THE CODE THAT WOULD RUN IT.**
M8 charged every cell into a real `Vessel`; that is how the dead solver was
found, and `pyrite-roasting` is what the check exists to prevent.
⚠ **AND VERIFY A BIT-IDENTICAL CLAIM AGAINST THE EXAMPLE SET, NOT AN ARGUMENT.**
M8's "no supply is exactly the old engine" is true by construction AND was
checked by stashing `src/` and running all 14 examples both ways. S5's lesson:
a four-run sweep is not the example set.
⚠ **AN `inf` IS USUALLY THE WRONG BOUND, NOT A BOUND NEEDING SOFTENING.**
⚠ **A RELATIVE-DIFFERENCE TEST IS MEANINGLESS ON A COLUMN WHOSE CONVERGED VALUE
IS ZERO.**
⚠ **A NEW CREDIT MUST BE A FALLBACK BEFORE IT IS AN OVERRIDE.**
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS.** S2's harness invented a finding;
S1's coverage audit credited a route that cannot run; S3's report could not be
diffed; S4's rate-ceiling audit made a claim about a table it does not read;
S6's target column had been understating itself since M3. **M8's new audit found
a pre-existing error in the ion table on its first run** — which is what a
standing audit is for.
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS.
⚠ **A GENERATED FILE NOTHING READS IS THE ONE THAT ROTS.** Regenerate all three
catalog artefacts. ⚠ The root `README.md`'s coverage table is NOT generated —
S4 corrected it once, S6 again, M8 again.
⚠ **A PHASE LABEL CARRIES A STANDARD STATE.** So does a BASIS.
⚠ **BDF IGNORES `jac_sparsity` THE MOMENT `jac` IS CALLABLE.**
⚠ Windows console is cp1252: **a warning glyph inside a `print()` kills a
script.** Docstrings fine, printed text ASCII. (TWENTY-TWO sessions running —
M8 hit it too, in `validation/cell_potentials.py`, on the first run.)
⚠⚠ **`sed -i` REWRITES EVERY LINE ENDING IN A CRLF FILE.** This repo is MIXED:
markdown and `.psv` are CRLF, `element_data.py` / `solid_state.py` /
`volatility.py` / `catalog_coverage.py` / `template.py` / `reaction.py` /
`synthesis.py` are CRLF while `vessel.py` / `surface.py` / `thermo.py` /
`builder.py` / `constants.py` / `jacobian.py` are LF. **Read binary, detect
`\r\n`, restore it on write. Check `git diff --stat` after the first edit to any
file** — a whole-file rewrite shows up instantly as a huge insertion count.
⚠ **HEREDOCS EAT ESCAPES**, and M8 also found they choke outright on a large
block containing quotes. Write the payload to a file with the Write tool and
splice it with a tiny script.
⚠ **A GENERATOR CAN LEAK A `numpy` REPR INTO ITS OUTPUT.** Cast to `float`.
⚠ An em dash in a markdown anchor will not match a `--` you typed.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u`.

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays; RDKit stays in matter.
NO silent approximations. REFUSE loudly rather than return a confident wrong
number — and a LATENT fragility is a third case: report it, do not refuse it.
⚠ **AND REFUSING TO *DISSOLVE* A SPECIES IS NOT REFUSING TO *PRICE* IT.**
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?" **M8's answer was "none — it collapses to
different numbers in the arrays that already exist", which is why it cost no
Layer 4 code.**
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; `solid_state=False`
exactly no crystal reacting; `surface=False` exactly no gas attacking one; an
all-zero `order_solid` exactly the old kinetics kernel; **`cell_potential=0.0`
exactly the pre-M8 engine, bit for bit, verified on all 14 examples**;
**`BoundedJacobian` with its bound lifted exactly BDF's own differencing**; the
Born term exactly zero in PURE water; the five pH values (**M8 predicted to break
them and did not**); SAVE_VERSION stores the CONDITION, never the instant; every
gaseous element reference state Hf = Gf = 0 EXACTLY; **a CONDENSED reference
state's ideal-gas record is a MEASUREMENT and must not be zero**; every METAL
Hf = Gf = 0 EXACTLY on the solid basis; a reference state its own database does
not price at Hf = 0 is REFUSED; no mineral pricing differently under the two
providers; `ion_data` and `electrolyte` never subtracted from each other; **a
declared rate order may never be reversible, and an `electrons` count may never
carry declared orders**; **an electrode template is a WHOLE CELL, charge balanced
on both sides — a half reaction is refused by the builder and must stay so**;
**the reverse of an electrode reaction carries MINUS the work, so `dH_rev ==
-dH_fwd` exactly**; a surface row whose `ln K` is under +20 is REFUSED; **a
solid-state row with no crystal on EITHER side is REFUSED**; **the four pre-S4
solid-state rows take the raw `units` minimum, bit for bit**; **an element's
`Hvap` is Clausius-Clapeyron on the vapour-pressure curve `volatility` actually
evaluates**; the reflux ratio is the ratio of two drain conductances out of one
condenser; the fragmentation SEARCH runs only after the greedy pass has been
REFUSED; an ion is never counted in the held-ideal flag; a rate CAP scales BOTH
pre-exponentials by one factor; a template that moves a hydrogen ATOM must
collapse explicit Hs; a declared catalyst is a CONSTANT OF THE MOTION; the
tolerance audit's THREE self-check examples come out byte-identical;
**`COVERAGE_REPORT.md` and both `derived/*.psv` come out byte-identical across
`PYTHONHASHSEED` values**; **the `mineral` tier is a FALLBACK consulted only after
all three providers refuse**; **`validation/jacobian_bound.py` panel 3 reads 0
clamped columns on every single vessel**; **a lattice may REACT and may never
DISSOLVE — the fusion law is still 407x wrong in both directions, and neither M6
nor S1–S6 nor M8 softened that by one digit.**

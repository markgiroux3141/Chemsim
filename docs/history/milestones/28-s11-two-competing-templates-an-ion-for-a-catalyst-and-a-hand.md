## S11 — Two competing templates, an ion for a catalyst, and a hand-typed list  ✅ **DONE 2026-08-26 — the coverage queue's two best rows, plus the discovery that a species is estimated because nobody typed its name**

**+2 classes, +2 template-ready, +0 species-ready, +2 RUNNABLE — all four
predicted before the audit ran, and all four came out.** Two content classes off
the queue, one instrument fault CLOSED (engine queue item 6), and one new
honesty item that is larger than either of them.

| | before | after |
|---|---:|---:|
| classes with a template | 48 / 229 | **50 / 229** |
| routes template-ready | 38 / 173 | **40 / 173** |
| routes species-ready | 77 / 173 | 77 / 173 |
| ⚠⚠ **routes BOTH — the one to quote** | **28** | **30** |
| templates | 43 | **45** |

⚠ **NO ENGINE CODE CHANGED AGAIN.** Not one line of `numerics/` or `vessel/`,
for the second milestone running. Everything below is declarations, data, and
one instrument.

### ⚠⚠ 1. THE OXO PROCESS — TWO TEMPLATES THAT RACE, AND THE THERMODYNAMICS POINT THE WRONG WAY

`hydroformylation` is the first class here whose two catalog rows are ONE
reaction with TWO regiochemistries — `butyraldehyde` and `isobutyraldehyde` from
the same reactants, the second row's own condition column reading "same reactor,
n:iso selectivity". One template cannot cover it, and the pair is the mechanic.

⚠⚠ **AND THE INTERESTING PART IS THAT THE ENGINE'S OWN TABLES SAY THE BRANCHED
PRODUCT SHOULD WIN.**

    propene + CO + H2 -> butanal            dH -113.73   dG298 -38.72   K(420) 10.08
    propene + CO + H2 -> 2-methylpropanal   dH -123.08   dG298 -43.54   K(420) 23.52

The branched aldehyde is **9.35 kJ/mol more exothermic** and takes 2.33 of every
3.33 molecules at equilibrium. The real reactor makes the LINEAR one, four to
one. **The oxo process is under kinetic control and running against its own
thermodynamics**, which is why the aldehyde industry wants has to be taken out of
a reactor rather than waited for.

⚠⚠ **SO EVANS-POLANYI HAD TO BE SWITCHED OFF, AND THAT IS A DECLARATION.** `alpha`
scales the barrier with dH, so **any** transfer coefficient above zero hands the
more exothermic branched route the lower barrier and names the wrong major
product with confidence. `alpha=0.0` on both, and a test asserts it.

**ONE NUMBER IS FITTED**: a 4.8 kJ/mol barrier difference, chosen so
`exp(dEa/RT)` is 4.0 at the catalog row's own 420 K. Everything else is a
consequence, and the consequences were measured:

| what | measured |
|---|---|
| the reactor, 1 L at 200 bar / 420 K / 0.1 mol cobalt / 1 h | **94.3% converted**, n:iso **3.952** |
| n:iso against `exp(dEa/RT)` at 380 / 400 / 420 / 450 K | 4.569 / 4.234 / 3.952 / 3.543 against 4.569 / 4.235 / 3.953 / **3.607** |
| ⚠ and at 480 / 520 K | **1.867 / 0.760** against a pure kinetic 3.329 / 3.035 |
| the cobalt gate | 0 mol -> **exactly zero**, and 0.001 / 0.01 / 0.1 / 0.5 mol are a first-order knob |

⚠⚠ **NOBODY DECLARED A MAXIMUM OPERATING TEMPERATURE AND THE FLASK HAS ONE.** Up
to ~450 K the selectivity IS the exponential, to three figures. Above it the two
REVERSE reactions get inside the reactor's own hour and the stable branched
product starts winning; the conversion turns over in the same place. **A real
cobalt oxo reactor sits at 410-450 K.**

### ⚠⚠ 2. REVERSIBLE, AND THE ALTERNATIVE WAS MEASURED RATHER THAN ARGUED

Three moles of gas become one, so this equilibrium turns over on heating: ln K is
+2.31 at 420 K and **-7.46 at 600**. `alkene_hydrogenation` argues that
irreversibility is "a claim about temperature rather than about thermodynamics",
and that argument does not transfer here — retro-hydroformylation is real and
industrial. Measured, one hour, each temperature's own charge:

| | 1 bar, reversible | 1 bar, IRREVERSIBLE | 200 bar, reversible |
|---|---:|---:|---:|
| 420 K | 0.469% | 0.470% | 93.1% |
| 500 K | 1.475% | 20.202% | 91.0% |
| **600 K** | **0.013%** | **77.933%** | 53.3% |

**A factor of ~6000 at 600 K and 1 bar, on a flask a player can build.** And the
200 bar column is the process: pressure buys back what heat costs, because three
moles become one.

### ⚠⚠ 3. AND THE PAIR CROSSES FROM KINETIC TO THERMODYNAMIC CONTROL ON ITS OWN

Nothing declares a crossover. The two templates share a reactant, detailed
balance supplies both reverses at `Ea - dH` (209.7 and 223.9 kJ/mol, nobody typed
either), so the kinetic product is eaten by the stable one through propene:

    t          1 h     10 h    4 days   6 weeks   1 year   11 years   settled
    n:iso     3.952   3.944    3.863     3.204     1.188     0.513     0.513
    GAS       3.304   3.296    3.229     2.678     0.993     0.4286    0.4283

⚠⚠ **AND THE LAST TWO ROWS DISAGREE, WHICH IS ALSO CORRECT AND ALSO UNDECLARED.**
`K(n)/K(iso)` is **0.4283** and the HEADSPACE lands on it to four figures. The
flask's INVENTORY ratio settles at **0.513**, because at 200 bar and 420 K this
reactor holds ~1.7 mol of LIQUID product and butanal (Tb 347.95 K) is the less
volatile of the two, so it hides in the layer. **A real cobalt oxo reactor is a
liquid-phase process for exactly this reason, and nothing asked for a two-phase
reactor — it is what a 200-bar charge of those five species IS.**
⚠ **AN EQUILIBRIUM CONSTANT IS A STATEMENT ABOUT PARTIAL PRESSURES. Read it
against the headspace, never against the inventory.**

### ⚠⚠ 4. THE WACKER PROCESS — THE FIRST TEMPLATE WHOSE CATALYST IS AN ION

`wacker-process` writes `copper-ii-ion` on both sides of its only row, which is
`library._maybe_catalyse`'s own case — except that `[Cu+2]` is priced from
`ion_data` and `thermochemistry` refuses a charged species by name. **So the gate
this template carries is not "did you add the catalyst" but "is there a SOLVENT
for it to be an ion in."** A flask built without `electrolyte_provider()`
REFUSES; it does not run slowly.

⚠ **AND IT REFUSES AT THE VESSEL, NOT AT THE NETWORK.** `build_network` succeeds
and names `[Cu+2]` as a species, because a network is a GRAPH question; pricing
happens one layer down in `build_phase_arrays`. That is the layering working, and
the message names the ion and says what to do.

Measured: 1 L of water, 0.02 mol Cu(II) as the chloride, 0.20 mol each of
ethylene and oxygen above it, 400 K — **40.1% converted in one minute, 98.2% in
ten**, against a real one-stage Wacker's 30-40% per pass on minutes of residence.
Copper out = copper in, to 1e-12. Carbon closure exact.

⚠ **AND THE COPPER LOADING IS A FIRST-ORDER KNOB THAT IS ACTUALLY RIGHT.** The
site balance M10 is missing is a statement about a SURFACE; there are no sites to
saturate in a chloride liquor. This is the one place the project's catalysis is
on firmer ground than its heterogeneous templates.

### ⚠⚠ 5. ONE THING IN THE WACKER TEMPLATE IS DELIBERATELY WRONG, AND IT IS MEASURED

The real Wacker rate law is first order in the alkene, first order in palladium
and **ZERO order in oxygen** — the O2 only reoxidises the copper(I) and never
appears in the rate-determining hydroxypalladation. This template declares FIRST
order in oxygen. **The reason is mechanical rather than chemical**: the kinetics
kernel has no availability gate (`_avail` serves the solid block only), so a
reactant at order zero keeps reacting after it runs out and is driven negative.
`hydrogen_sulfide_combustion` keeps one O2 slot at order 1 for the same reason.

The cost, measured rather than described — acetaldehyde in 60 s against O2
charged: **0.05 -> 1.00x, 0.10 -> 1.92x, 0.20 -> 3.53x, 0.40 -> 5.85x.** A real
reactor would give 1.00 throughout. Right at LOW oxygen, wrong at high, same
shape as the missing site balance.

⚠ What IS declared correctly is the alkene order: the SMARTS consumes two
ethylenes to balance one O2, so mass action would make it SECOND order in the
alkene. `orders=(1.0, 0.0, 1.0, 1.0)` puts it back to first, which is the
measured law. A declared order may never be reversible, and here that costs
nothing: ln K is +129 at 400 K.

### ⚠⚠ 6. **A SPECIES IS ESTIMATED BECAUSE NOBODY TYPED ITS NAME — 310 OF THEM**

The biggest thing in this milestone, and it was found by a failing reactor rather
than by an audit. `physical_data.py` is GENERATED, and what it is generated FROM
is `CANDIDATES` in `tools/build_physical_data.py` — **a hand-typed list of 33
names.** Everything not on it falls to Joback, whether or not a measurement
exists.

Propene was not on it. So the oxo reactor's own feedstock read **Tb 264.92 K
against a measured 225.53 and Tc 427.64 against 364.21**, both ~17% high — and
`chemicals` holds five independent experimental sources for that boiling point
(HEOS, CRC_ORG, COMMON_CHEMISTRY, WEBBOOK, YAWS, agreeing inside 0.5 K).

⚠⚠ **AND THE Tc ERROR WAS NOT COSMETIC.** An oxo reactor sits at 420 K, which is
55 K ABOVE propene's real critical temperature and 8 K BELOW Joback's — so the
engine condensed **0.91 mol of "liquid propene" into a supercritical flask**, the
reactor read 167 bar where it was charged to 200, and the extra stiff phase left
**2.8e-24 mol of butanal in a species with no source at all**. One line in a
candidate list removed all three: 200.00 bar exactly, no liquid, and the
zero-cobalt gate reads exactly 0.0.

**THE GENERAL CASE, MEASURED OVER THE WHOLE CATALOG:**

| | |
|---|---:|
| catalog species with a graph | 1539 |
| in `physical_data.MEASURED_PHYSICAL` | **33** |
| no CAS resolvable | 1070 |
| CAS but genuinely no experimental Tb | 126 |
| ⚠⚠ **experimental Tb available and NOT in the table** | **310** |
| ...of those, PRICE a Tb in this engine today | **229** |
| mean / median / worst \|error\| against the measurement | **5.81% / 2.94% / 84.89%** |
| over 2% / 5% / 10% / 20% | 138 / 70 / 34 / 11 |

The worst: arachidonic acid 819.35 against 443.15, dinitrogen tetroxide 503.28
against 294.30, linolenic acid 769.43 against 504.15, **ethylene 234.56 against
169.38**.

⚠⚠ **AND THE INSTRUMENT THAT MEASURED IT WAS WRONG FIRST, AS USUAL.** The first
run said 360 and listed *borane* boiling at 2823 K and *methane* at 4273. Cause:
`chemicals.CAS_from_any("C")` reads a bare SMILES as a FORMULA, so `C` resolved
to carbon and `B` to boron. `CAS_from_any("smiles=C")` gives methane, and the
count fell to 310. **A single-letter SMILES is also an element symbol.**

### ⚠⚠ 7. FOUR RECORDS WERE OVERRIDDEN AND A GUARD HAD TO BE REWRITTEN TO ALLOW IT

`test_the_measured_table_never_overrides_a_working_joback_record` failed, and it
was RIGHT to: propene, ethylene, butanal and 2-methylpropanal all resolve fully
through Joback. But that rule was a SCOPING decision, not a physics claim — the
milestone that wrote it was closing a coverage gap and deliberately did not
relitigate accuracy on species that already worked. Its own stated reason ("the
moment it stops being true the azeotrope, the boiling points and the crop sizes
all move at once") **is a call for measurement, not a reason never to do it.**

So the guard now names WHICH records were overridden, and still refuses any it
does not name — `DELIBERATE_OVERRIDES`, with a second test asserting no stale
entries. **The cost was measured example by example before any entry was kept:**
propene, butanal and 2-methylpropanal appear in NO example and move nothing;
ethylene appears in two, and `competing_pathways`'s worst moved number is
0.20380 -> 0.20485 (**0.5%**) with `named_routes` reporting ethanol-hydration at
**2.7% instead of 2.9%**.

⚠⚠ **AND THE PREDICTION ETHYLENE'S ENTRY WAS MADE ON WAS WRONG.** The brief was:
a Wacker flask dissolves 83% of its ethylene charge, the whole process is that a
gas must dissolve before meeting the copper, so a measured boiling point should
move it. **Measured after: 0.16588 -> 0.16596. Four significant figures
unchanged** — because ethylene's vapour pressure comes from
`volatility._CURATED_ANTOINE` and **Tb does not feed that curve at all.** What
the entry corrects is Tc, Tm and Hvap.

⚠⚠ **AND THE 83% IS REAL AND IS A SEPARATE FAULT, REPORTED NOT FIXED.** Ethylene
is a CONDENSABLE species here, so its solubility is Raoult's law against
Psat = **219.9 bar** — a curated Antoine evaluated at 400 K, which is **118 K
above ethylene's critical temperature of 282.35 K.** Oxygen beside it is a
Henry's-law solute and behaves. **NOTHING IN `build_phase_arrays` COMPARES T TO
Tc.** It makes the Wacker liquor richer in alkene than a real one, by roughly
40x. New engine-queue item.

### ⚠⚠ 8. ENGINE QUEUE ITEM 6 IS CLOSED, AND **NOT** BY RAISING `REPORT_ABS`

`tolerance_audit.py` has reported `QUOTABLE DIGITS MOVE, worst 99.85%` on
`oil_of_vitriol` since S5, and that headline was wrong: four of its five moved
lines are the created-matter residual and **every one gets smaller** at the tight
tolerance. The obvious fix — raise `REPORT_ABS` above 2.9e-05 — is the wrong one.
`REPORT_ABS` is SYMMETRIC, so raising it would blind the audit to a small
quantity GROWING as well as shrinking, and **a residual growing under refinement
is the defect the whole file exists to catch.**

The fix is a SECOND floor, `CONVERGING_ABS`, applied only when the tight run's
value is SMALLER than the loose one's. **Direction is the information the old
test threw away.** And the number came out of a measurement this project already
had rather than out of the audit: `NEXT_SESSION.md` records that same column
swinging **2.5e-09 to 4.5e-04 under an INERT 0.5% N2 nudge** — a perturbation
that cannot change the answer. 5e-04 is the top of that swing.

⚠ **AND THE SUPPRESSION IS NEVER SILENT**: a line whose only moves are converging
tokens is still printed, under its own heading, with its values.

**PREDICTED BEFORE THE 19-MINUTE RUN, AND ALL FOUR CAME OUT:** 5 moved lines ->
**1**; worst 0.9985 -> **6.60e-05**; the headline flips from QUOTABLE DIGITS MOVE
to **(below 0.1%)**; and no other example changes — `CONVERGING_ABS` fires on
**zero tokens across all twelve cheap examples**, which is the safety measurement
that mattered.

### ⚠ 9. THE OXO REVERSE IS THE ONE ROW WHOSE CROSSING TEMPERATURE IS A REAL STATEMENT

`rate_ceiling.py` gained an oxo panel, on M12's standing instruction to check the
reverse a template IMPLIES. Every other reverse it flags is high-order, so its
pre-exponential is in `L^n/(mol^n s)` and comparing it to a collision limit is
M8's unit error — the column is only good for RANKING.
`hydroformylation_linear_rev` is `butanal -> propene + CO + H2`, **one molecule
falling apart**, so its `A` really is in 1/s and `UNIMOLECULAR_LIMIT` really is
its yardstick.

It is **2.0e26 and 1.2e27 1/s**, and that is the third appearance of a thing this
project has now named twice: an **entropy of gas-making in a pre-exponential**.
One mole becomes three, dS_rev = +251.6 J/(mol K), and `exp(dS/R)` is 1.4e13 by
itself. Detailed balance is not free to shrink it without breaking `k_f/k_r = K`.
⚠ It crosses at **969.4 K** (branched 966.8), 550 K above the reactor. ⚠ The
brief predicted ~824 K off a 1e13 ceiling and the audit's own constant put it
145 K higher; **the measured number stands.**

### 10. AND TWO REFUSALS WERE RE-MEASURED AND BOTH STAND

Engine queue items 3 and 7 were both priced as "one source away". Re-queried
against `chemicals` 1.5.2 this session:

* **`pyrite`** — `Hfs` in WEBBOOK, `S0s` in **nothing**. Blocked, and the
  same-database rule is worth keeping. **Unchanged.**
* **`iron-ii-oxide`** — `Hfs` in CRC and WEBBOOK, `S0s` in WEBBOOK, so the
  same-database rule COULD be met from WEBBOOK. But its CRC standard row has
  `Cps = NaN`, and a species in the solid block has to say how much heat it
  holds. **Still blocked, on the recorded reason.**
* ⚠⚠ **AND ITEM 3 WAS PRICED WRONG.** `slagging` was listed as needing
  "`silicon-dioxide` and `calcium-silicate` in `mineral_data`", i.e. two curated
  entries and one declaration. Silica is fully available (CRC: Hfs -910700,
  Gfs -856300, S0s 41.5, Cps 44.4). **Calcium silicate has NO data in
  `chemicals` under any of its three CAS numbers** — 10101-39-0, 1344-95-2,
  13983-17-0 — so it is not a curation job at all. `slagging` is blocked, and
  `blast-furnace` is blocked twice over.

### ⚠⚠ 12. AND A THIRD CLASS WAS ATTEMPTED AND REFUSED — BECAUSE THE BALANCE AUDIT'S TEST IS WEAK

`oxidative-cleavage` was the queue's next row after the two above, worth +1 and
listed as clean: every species resolves, and `corpus_balance` passes its only
step. **It cannot be built, and finding out why is a finding about the
instrument.**

The row is `coniferyl alcohol + oxygen -> vanillin + water`. Coniferyl alcohol is
**C10H12O3** and vanillin is **C8H8O3**: a C10 monolignol makes ONE C8 vanillin
and a C2 fragment the row does not name. `corpus_balance` passes it anyway,
because its test is *does ANY positive coefficient vector conserve every element*,
and there is one:

    8 C10H12O3 + 7 O2  ->  10 C8H8O3 + 8 H2O

**EIGHT AROMATIC RINGS IN AND TEN OUT.** Element conservation does not forbid
rearranging carbon skeletons, so a row can PASS this audit and still not be the
reaction it is written as. ⚠ **A pass there is not permission to write a SMARTS**,
and the audit says so in a new last panel now.

Naming the missing C2 product would be inventing chemistry inside the corpus,
which is the `diels-alder-route` precedent this project already follows. **So the
class is REFUSED, measured, and the measurement is printed rather than remembered.**

⚠⚠ **AND THE ROW NEXT TO IT ON THE SAME QUEUE IS THE CONVERSE, WHICH IS WHY BOTH
WERE CHECKED.** `skraup-route` step 2 reads with **aniline on BOTH sides**, which
looks exactly like the `spurious` pattern the audit exists to catch — and is not:
the nitrobenzene oxidant is REDUCED to aniline. It balances at

    3 aniline + 3 acrolein + 1 nitrobenzene -> 3 quinoline + 1 aniline + 5 water

with **four aromatic rings in and four out**. That is the real Skraup
stoichiometry, and it is now the coverage queue's best row — 7 reactant slots and
9 product slots, which the Claus template's 24 proves is reachable.
**Two rows, one passing audit each, and only one of them is real.**

### 13. THE SMALL THINGS

* **`species_roles.psv` upgrades four provenance tiers** — ethylene `joback -> measured`,
  and propylene, butanal and 2-methylpropanal `joback -> benson` (a measured Tb lets Benson's formation half assemble where
  Joback's was standing in). An upgrade in the audit's own terms, and it is what
  a coverage report CAN see about this work — the 310 it cannot see are engine
  queue item 1.
* `validation/hydroformylation.py` and `validation/wacker.py` are new standing
  audits. Every class S11 credits went into a real `Vessel`; the coverage table
  credited nothing on a lookup.
* ⚠ Panel 3 of the oxo audit prints the KINETIC ratio beside the actual one,
  because the first version printed only the actual one and read as if the
  Arrhenius ratio had collapsed. **A column that answers one question cannot
  answer the next one**, again.
* ⚠ The oxo audit's own prose rotted twice inside this session — once when
  reversibility changed the 480/520 K numbers, once when propene's boiling point
  changed the conversion. **Third session running.**

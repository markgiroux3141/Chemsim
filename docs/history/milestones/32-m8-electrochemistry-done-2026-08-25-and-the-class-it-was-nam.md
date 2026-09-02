## M8 — Electrochemistry  ✅ **DONE 2026-08-25 — and the class it was named for did not survive its own row check**

**+2 classes (36 → 38 of 220), +3 template-ready (28 → 31), +3 RUNNABLE
(17 → 20).** Four templates, one field, one `if`. No new term in Layer 4, no new
phase, no new gate, and the pre-M8 example set is byte-identical.

### 1. THE MECHANIC, AND WHY IT NEEDED NO ENGINE

An electrolysis cell does electrical work `w = n F E` on the reaction.
`ReactionTemplate.electrons` says how many electrons cross the external circuit;
`build_network(cell_potential=...)` says what the supply is set to; their product
lands on `ConcreteReaction.electrical_work` and `reaction_deltas` subtracts it
from **both** dH and dG. A reaction whose chemistry costs less than the cell
supplies then runs, and the voltage where the two balance is the

    E_dec = dG_chem / (n F)

of every electrochemical series ever printed. **The gate is a comparison of two
energies this project already computed**, which is why nothing had to be
invented to hold it.

⚠ **THE SHIFT GOES ON dH AS WELL AS dG, AND THAT IS THE ONE PIECE OF ALGEBRA
WORTH CHECKING.** The supply holds E fixed, so `w` does not vary with
temperature, and a T-independent shift is an ENTHALPY shift. Put it in dG alone
and `reaction_entropy` — which reads `dS = (dH - dG)/T` — books the whole cell
voltage as reaction entropy, and K then drifts as `exp(w/RT)`. Shifting both
leaves dS exactly the chemistry's. **And the energy balance comes out right for
free**: `to_arrays` takes its dH from the same function, so the heat the flask
sees is `w - dH_chem`, zero at the thermoneutral voltage. A real cell does that.

⚠⚠ **EVANS-POLANYI ON AN ELECTRODE REACTION IS THE BUTLER-VOLMER EQUATION, AND
`alpha` IS THE TRANSFER COEFFICIENT.** An identity, not a resemblance: with the
work inside dH, `Ea_i = Ea + alpha (dH_chem - n F E)` is `Ea - alpha n F eta` up
to the entropy term — the Tafel slope, with alpha at its conventional 0.5. So
**`Ea` on an electrode template is the ACTIVATION OVERPOTENTIAL in energy units,
`n F eta_a`**, and the kinetics needed no new field either.

### 2. ⚠⚠ THE BRIEF NAMED THE TOP OF THE GREEDY CURVE, AND THE ROW CHECK TOOK TWO THIRDS OF IT

`electrolysis` has been the set-cover curve's **first row at +3 routes** since
M1. Its four rows are THREE mechanisms, distinguished at the CATHODE:

| became | rows | covered? |
|---|---|---|
| `aqueous-electrolysis` | `chloralkali` | ✔ the cathode reduces WATER |
| `molten-salt-electrolysis` | `downs-cell`, `hall-heroult` | ✘ a MELT is not a phase here |
| `amalgam-electrolysis` | `castner-kellner` | ✘ a mercury cathode reduces the SODIUM; the product is a marker |

**So the curve's top row is worth +1, not +3.** Chloralkali and Castner-Kellner
take the same feed and give the same chlorine; one makes caustic soda and the
other makes sodium metal, and the reason is which species the cathode reduces.
Crediting them together would have claimed a route to sodium metal this engine
cannot make — `roasting-to-metal`'s false credit in a new costume. ⚠ The two melt
rows cost nothing today: both are blocked on a bare element as well (`sodium`,
`aluminium`, `carbon-graphite`), so neither was ever one class away from running.

The other +2 came from `electro-organic-coupling`, which was NOT split — its two
rows are two mechanisms and **both are built**, which is the `ester-hydrolysis`
precedent and exactly when a multi-mechanism class may be credited.

### 3. ⚠⚠ THE BRIEF SAID THIS WOULD BREAK THE SPECTATOR ZEROS. IT DID NOT, AND THE REASON IS THE FINDING

The brief: *"a half-cell potential is not consumed as a number: it puts the ion
back into an equilibrium the kernel evaluates. Budget for re-deriving the five pH
values."* **Measured: they did not move, and no half-cell potential exists.**

Every template here is a WHOLE CELL — anode plus cathode, electrons cancelled,
charge balanced. That is not a convenience: a half reaction does not conserve
charge, and `builder._element_charge_balance` rejects a rewrite that does not. It
is also what the catalog rows already say — `sodium-chloride + water ->
sodium-hydroxide + chlorine + hydrogen` is the cell, not the anode. And it means
**no electrode potential was ever curated**: dG of a half reaction needs a
reference electrode, dG of a cell does not, so the driving force comes out of the
same dGf table that fixes every other equilibrium in the project. Nothing new
entered the ion equilibria, so nothing moved. `test_born.py`,
`test_solids_and_ions.py`, `test_precipitation.py`, `test_solubility_product.py`:
76 passed.

⚠ **AND THE "done when" WAS MET IN THE OTHER VARIABLE.** The brief asked that
"the current is the control". It is not — the VOLTAGE is, and see §6. Voltage is
what makes the gate thermodynamic and therefore derivable; a current budget is a
Layer 4 term and would have been a second milestone.

### 4. ⚠ THE NUMBER IS DERIVED, AND `validation/cell_potentials.py` AUDITS IT

| cell | E_dec derived | electrochemical series |
|---|---:|---:|
| `2 H2O -> 2 H2 + O2` | **1.441 V** | 1.229 |
| `2 Cl- + 2 H2O -> Cl2 + H2 + 2 OH-` | **2.362 V** | 2.186 |
| `2 Br- + 2 H2O -> Br2 + H2 + 2 OH-` | **2.061 V** | 1.894 |

Within a quarter of a volt, from formation data, with no electrode potential in
`src/`. ⚠ **The book column is an INDEPENDENT CHECK and must never become a
target** — nothing in it feeds anything in `src/`.

⚠⚠ **AND THE AUDIT FOUND A PRE-EXISTING ERROR ON ITS FIRST RUN: dG SURVIVES THE
ION TABLE'S MIXED BASIS AND dS DOES NOT.** The brine cell's dS is out by
**−591 J/(mol K)** and the bromide cell's by −738, which REVERSES the sign of
dE/dT: every cell here needs more voltage when heated, every real one needs less.
The cause is that this project's ions are derived from measured pKa against its
OWN water reference, and its own water is priced on the **ideal-gas** basis
(Hf −241.8, not the aqueous −285.8). For a reaction that conserves water the
offset cancels and nothing has noticed since the electrolyte model was built;
**every cell reaction consumes water and makes hydroxide**, so it does not.
**Quote E_dec at 298 K. Do not quote how it moves with temperature, and do not
read a cell's HEAT** — `to_arrays` takes its enthalpy from the same dH.

### 5. ⚠⚠ THE SOLVER SAID THE PRE-EXPONENTIAL WAS THE WRONG KIND OF NUMBER

Declared at `A = 1e10` — an order under the collision limit, which is how every
other pre-exponential in this project is bounded — a cell at 3.0 V consumed
0.2 mol of chloride inside a nanosecond and `Vessel.run` died with *required step
size is less than spacing between numbers* after **4.2e-09 s of a 3600 s
interval**. The rate cap had been firing at the low-voltage end too, scaling a
pair by 4.031e-14. Both are the same wrong ceiling seen from two ends.

**An electrode reaction is not two molecules meeting.** It happens on a SURFACE;
its rate is proportional to electrode AREA, not to volume; the molecules in the
bulk are not at the electrode at all. `A = 1e10` asserts that every chloride in
the flask is touching the anode. The right units are a current density over an
area:

    rate [mol/(L s)] = j0 [A/cm2] * a [cm2/L] / (n F)
    5e-8             = 1e-3       * 10        / (2 * 96485)

and the check that makes it defensible is that **it comes back out as an
ampere**: 5e-8 mol/(L s) at unit concentrations is 1e-2 A, and the cells below
run between a milliamp and a couple of amps. A bench power supply has those.

### 6. WHAT IS NOT MODELLED, MEASURED RATHER THAN ASSERTED: THERE IS NO CURRENT BUDGET

A real supply delivers a fixed number of electrons per second and the electrode
reactions divide them. Here they divide nothing, so **every reaction the cell
clears runs at its own full rate, simultaneously**. The measured consequence is
that activation selectivity washes out as the barriers reach `barrier`'s floor at
zero:

| E (V) | k(brine) / k(water) | one flask of brine, one hour |
|---:|---:|---|
| 2.5 | **4.76e+17** | 0.0177 mol Cl2, 8.9e-19 mol O2 |
| 3.0 | 5.94 | 0.0176 mol Cl2, 0.091 mol O2 |
| 4.0 | 1.00 | 0.0169 mol Cl2, 0.53 mol O2 |

**The usable window for a selective brine cell in this engine is roughly
2.2–2.7 V**, where a real one holds 99% selectivity at 3 V and above. Same shape
as the site balance: right at low loading, wrong at high. ⚠ Pinned by a test as
a LIMIT — if a later milestone makes the ratio hold at 4 V, that test should fail
and be rewritten, not deleted.

⚠ The chlorine PLATEAUS across 2.5–4.0 V and the oxygen does not, which is the
whole mechanic in one column: above 2.5 V the halide barrier is already floored
so more volts buy it nothing, while oxygen's is still coming down. The chloride
is a charge that runs out; the water is the solvent and does not.

### 7. ⚠ THE ADIPONITRILE ROW IS NOT AN ELECTRODE REACTION, AND THAT IS ARITHMETIC

The row reads `acrylonitrile + water -> adiponitrile + oxygen`, so the expected
shape was a fourth `electrons`-carrying template. Running the numbers first said
otherwise:

* the CELL `4 AN + 2 H2O -> 2 ADN + O2` costs **+212.7 kJ/mol** — genuinely
  uphill, genuinely needs 0.551 V;
* but `2 AN + H2 -> ADN` is **−171.7 kJ/mol**, downhill on its own. **The voltage
  does not pay for the carbon–carbon bond.** It pays for tearing hydrogen out of
  water, which is `water_electrolysis` and is in every aqueous cell already.

So the route is two steps whose overall stoichiometry — the oxygen included —
EMERGES. Measured end to end: 65.6% conversion at 3 V, nothing at 2 V.
⚠ **The cost is stated rather than hidden:** routing the electrons through free
H2 puts the route's threshold at water's 1.441 V instead of its own 0.551 V,
**0.89 V too high**. Baizer's cell runs near 4 V so nothing about whether it RUNS
turns on it, but the threshold this engine reports is the wrong one.
⚠ The alternative was measured and refused: written as the one 6-slot lump the
row implies, the rate law is FOURTH ORDER in acrylonitrile, the limiting
reagent — `sulfur_combustion`'s stall in the case its own note says is NOT
forgiven, where the yield stops being chemistry and becomes a reading of `A`.

### 8. WHAT IS EMERGENT

* Kolbe generalises with nothing enumerated: acetate + propanoate gives ethane,
  propane **and** butane, because the two reactant slots fill independently.
  ⚠ Read the 1.49 : 0.98 : 0.57 ratio as the three rate constants Evans-Polanyi
  set from three slightly different dH — the STATISTICAL factor of 2 on the cross
  is not in it, which is this engine's mass-action convention everywhere.
* One halide template covers Cl, Br and I, and bromide goes at a lower voltage
  because its chemistry costs less. Nothing was told that.
* Kolbe needs the CARBOXYLATE: a flask of glacial acetic acid does not
  electrolyse, and the template says so by matching `[O-]`.

**Files:** `reactions/electrochemistry.py` (new, 4 templates),
`reactions/template.py` (`electrons` + two refusals),
`reactions/reaction.py` (`electrical_work`), `reactions/thermo.py` (the
subtraction + `decomposition_potential`), `network/builder.py`
(`cell_potential`), `constants.py` (`FARADAY`),
`validation/cell_potentials.py` (new, standing audit),
`examples/electrolysis_cell.py` (new, 5 panels),
`tests/test_electrochemistry.py` (new, 21 tests).

---

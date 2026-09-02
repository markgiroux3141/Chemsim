## S9 — The reversible solid-gas term, and the smelter  ✅ **DONE 2026-08-26 — the queue's only +2 was one algebraic rearrangement, and the reason recorded beside the refusal was about a form the term never used**

**+5 classes (43 → 48, of 229 after two splits), +4 template-ready (34 → 38), +4 RUNNABLE
(24 → 28)** — tying S7 for the largest single-session move the intersection has
had. Six declarations, ~15 lines of engine, no new term, no new phase, and the
five pre-S9 solid-state rows are BIT-IDENTICAL.

⚠ **All four coverage numbers were PREDICTED before the audit was run and all
four came out exactly**: 48 classes, 38, 28, and species-ready holding at 77.
⚠ The class DENOMINATOR moved 224 → 229 because S9 made TWO splits, and only
one of them was planned — see §8 and §9 below.

| | before | after |
|---|---:|---:|
| classes with a template | 43 / 224 | **48 / 229** |
| routes template-ready | 34 / 173 | **38 / 173** |
| routes species-ready | 77 / 173 | 77 / 173 |
| ⚠⚠ **routes BOTH — the one to quote** | **24** | **28** |

The four: `copper-smelting`, `lead-smelting`, `zinc-smelting`, `thermite`. **All
three smelting routes at once**, which `catalog_coverage.py` has carried a
comment about since S1 — *"all three smelting routes are still blocked at
`carbothermic-reduction` / `gas-solid-reduction`"*.

### ⚠⚠ 1. THE ENGINE GAP WAS ONE ALGEBRAIC REARRANGEMENT, AND HALF THE REASON BESIDE IT WAS ABOUT A DIFFERENT FORM

S8 named "a REVERSIBLE solid-gas term" as **the most valuable engine item in the
plan that nobody had scoped**. `SolidStateArrays` already integrates the affinity
form and already reaches `Q = K`; what it refused was a gas REACTANT, on two
recorded grounds:

1. *its pressure sits in the DENOMINATOR of `Q = prod(p ** nu_gas)`, so an
   atmosphere depleted of it drives the reverse flux to 2.6e15 formula units per
   second* — **true, and cured by not writing a quotient.**

       net = k_f * prod(p ** consumed_gas)  -  k_r * prod(p ** formed_gas)

   is `P_react (k_f - k_r Q)` algebraically — **the same root, so the same
   equilibrium** — and at `p_react = 0` it is the finite `-k_r P_prod`. Measured
   on the copper row at 1400 K: the old branch reads 1.50e-8, 1.50e-2, 1.50e+4,
   1.50e+22, `inf` as p_CO falls 1 → 1e-3 → 1e-6 → 1e-30 → 0; the new one is
   bounded by `k_r` at 1.4973e-08 the whole way.

2. *mass action written on a solid AMOUNT settles at `p/K = n_A/n_B`* — M6's
   measurement, true, and **not about this term.** The affinity form takes ONE
   `units` for both directions, chosen by the sign of the affinity, so it is a
   common factor that divides out of `net = 0`. That was already the case when
   the refusal was written. Measured across a **50x charge range**: Q/K =
   1.0000, 1.0000, 1.0000.

⚠⚠ **SO M6 DREW THE LINE IN THE WRONG PLACE, AND THE RIGHT LINE IS ALREADY ONE
OF THIS PROJECT'S INVARIANTS.** The dichotomy was recorded as *inside a crystal /
at its surface*, and S4 had already broken that by turning a crystal entirely
into gas. The line that actually holds is **reversible or not**: an affinity form
cannot carry DECLARED rate orders, because detailed balance fixes its exponents
at the stoichiometric coefficients or the equilibrium is wrong. That is verbatim
*"a declared rate order may NEVER be reversible"*, which has been in the
invariants table since M8's rate work, arriving in a new place. So roasting stays
in `SurfaceArrays` — `3 O2` as mass action stalls asymptotically, which is what
`SurfaceReaction.orders` exists to declare away — and it stays there **for the
order and not for the denominator**.

### ⚠⚠ 2. THE SECOND CHANGE: `Ea = max(dH, 0)` IS A DERIVATION ABOUT A DECOMPOSITION, AND ON AN EXOTHERMIC ROW IT RETURNS ZERO

M6 derives the barrier rather than declaring it, correctly: an endothermic
decomposition whose reverse is a gas landing on a crystal has no reverse barrier,
so `Ea = dH`, and calcite comes out at 179.2 kJ/mol against a measured 170–200.
Write an EXOTHERMIC row and the same line gives **zero**.

| row | dH/kJ | derived A | what that IS |
|---|---:|---:|---|
| `metallothermic-reduction` | −851.50 | 4.15e-6 1/s | a 2.8-**day** thermite, at every temperature |
| `tenorite-carbon-monoxide-reduction` | −125.68 | 9.70e-4 1/(bar s) | 17 minutes at 298 K as well as at 1500 |

⚠ **The finding is not the size of the numbers, it is that the temperature has
left the rate law.** With `Ea = 0` there is no exponential. Thermite's entire
mechanic is that it sits in a jar until something lights it; a smelter's is that
it needs a furnace. So an exothermic row DECLARES its forward pair and still gets
its reverse by detailed balance — the direction every `ReactionTemplate` here
declares in — and `price` refuses the derivation for such a row by name.

⚠ **AND A DECLARED `Ea` BELOW `dH` IS REFUSED, WHICH IS NOT A CONVENIENCE.**
`Ea_rev = max(Ea - dH, 0)` clips, and the clip would leave `k_f/k_r` no longer
equal to `K` — the equilibrium would silently stop being the thermodynamics. The
`max` is provably inert for the derived pair (`max(dH,0) - dH >= 0` always), so
the guard only bites on a declaration. It is also `detailed_balance`'s own floor
everywhere else in this project.

### 3. THE SIX DECLARATIONS, AND THE THREE THAT NEEDED NOTHING NEW

| row | module | dH/kJ | kinetics | what it is |
|---|---|---:|---|---|
| `tenorite-carbon-monoxide-reduction` | `solid_state` | −125.68 | declared | `copper-smelting` 2 |
| `litharge-carbon-monoxide-reduction` | `solid_state` | −63.98 | declared | `lead-smelting` 2 |
| `metallothermic-reduction` | `solid_state` | −851.50 | declared | `thermite`, the whole route |
| `zincite-carbothermic-reduction` | `solid_state` | +239.97 | **derived** | `zinc-smelting` 2 |
| `boudouard-gasification` | `solid_state` | +172.45 | **derived** | `blast-furnace` 2 |
| `carbon-combustion` | `surface` | −393.51 | declared | `blast-furnace` 1, the tuyere |

⚠⚠ **`carbothermic-reduction` NEEDED NO ENGINE WORK AT ALL, AND THE QUEUE HAD
PRICED THE WRONG REACTION.** `NEXT_PROMPT` warned that `ZnO + CO -> Zn + CO2` is
**uphill at +63.3 kJ/mol** and might be `gas-solid-reduction`'s problem in a
second costume. The catalog's own row is not that reaction: it reads
`zinc-oxide + carbon-graphite -> zinc + carbon-monoxide`, and with graphite the
entropy of making a mole of CO carries it — **dG = 0 at 1264.3 K** against a real
Belgian retort's 1200–1300. Two solid reactants and one gas PRODUCT is an
ordinary row of M6's table that nobody had written. **S8 measured a row the
catalog does not contain and concluded the class was blocked.**

⚠ **AND THE SAME IS TRUE OF BOUDOUARD, WHICH IS THE ONLY DERIVED ROW WITH A GAS
REACTANT.** It is endothermic, so `Ea = max(dH,0)` is right for it and its
reverse — 2 CO laying down soot on carbon — really is the barrierless event
`RECOMBINATION_A` was calibrated as. **The gas-reactant fix and the declared-pair
fix are independent, and Boudouard needs only the first.**

### ⚠⚠ 4. THE ROUTE NOBODY DECLARES: ORE + COKE + AIR → METAL

Four declarations in two modules, none of which mentions another. They share a
solid block and a headspace:

    surface.py       CuS + O2  -> CuO + SO2     a gas at a crystal (S1)
    surface.py       C   + O2  -> CO2           the tuyere         (S9)
    solid_state.py   C   + CO2 -> 2 CO          Boudouard, reversible
    solid_state.py   CuO + CO  -> Cu + CO2      the reduction, reversible
    ------------------------------------------------------------------
    the catalog route  CuS + O2 -> CuO + SO2, then CuO + CO -> Cu + CO2

Measured on a sealed 10 L flask holding 0.04 mol of covellite and 0.20 mol of
graphite at 1500 K, with air and nothing else: **0.040000 mol of copper,
0.040000 mol of SO2, no ore and no coke left, `conservation_report` empty.** The
same for galena at 1400 K and for sphalerite at 1400 K.

⚠ **THE AIR IS THE CONTROL, WHICH IS WHAT A SMELTER ACTUALLY ADJUSTS.** On the
copper flask: 0.02 mol O2 → 29.01%, 0.06 → 80.41%, 0.10 → 99.89%, 0.20 →
100.00%. Nothing declares that curve; it is the roast running out of oxidant.

⚠⚠ **AND THE ZINC FLASK GOES *DOWN* AT 0.20 mol OF OXYGEN, WHICH NOBODY DECLARED
EITHER.** 0.032476 mol of metal at 0.06 and **0.025515 at 0.20**, with 0.014485
mol of zincite left and the coke completely gone. The reason is that
`zincite-carbothermic-reduction` and `carbon-combustion` **compete for the same
carbon**, and a blast rich enough to burn all of it leaves nothing to reduce the
oxide with. The copper and lead flasks do not do this, because their reductant is
the CO the carbon made and Boudouard keeps handing it back. **Overblowing a zinc
retort really does waste the charge, and no line in this project says so.**

⚠⚠ **S10 WITHDREW THIS PARAGRAPH'S CONCLUSION.** The competition is real, but which side won was decided by two DERIVED pre-exponentials — and making the zinc a VAPOUR moved one by 24x (`tau` 256.9 s → 10.9 s), so the reduction now takes the zincite before the blast can burn the coke. The yield is **monotone and saturating**: .0117 / .0229 / .0328 / .0400, flat to 0.50 mol O2. ⚠⚠ **THE SIGN OF THE EFFECT DEPENDED ON A CLOCK**, and it was written up here as physics. A real furnace does waste an overblown charge, for transport reasons this engine does not model. **Thermodynamic conclusions here survive a phase change in a product; kinetic ones need not.** See §S10.

### ⚠⚠ 5. THE CARRIER IS THE MECHANIC, AND IT IS THE LEAD CHAMBER'S FAILURE MODE THAT DIDN'T HAPPEN

A flask of ore and coke with **no gas in it at all** is **exactly inert** — 0.0
copper, 0.0 CO, 0.0 CO2, at the default rung, rtol 1e-6, rtol 1e-8 and rtol
1e-10. Both reactions that would run need a carbon oxide and there is none.

⚠⚠ **THAT IS THE QUESTION `chemsim-solid-gate-fix` EXISTS TO ASK.** A cycle with
gain on its own carrier is precisely the shape that let round-off seed the lead
chamber to an 89% yield on 1.2e-4 mol of phantom NOx. The reason it cannot happen
here is the FORM and not a guard: the arriving gas enters as `p ** 1` with no
denominator, so zero in is zero out with a bounded slope. A smoothstep with a
constant scale is what failed in the chamber, and there is none in this term.

⚠ **AND ONCE SEEDED THE CARRIER MULTIPLIES, WHICH IS REAL CHEMISTRY.** 1e-12 mol
of CO2 — **one part in 1e11 of the charge** — reduces the whole 0.10 mol of
oxide. Boudouard makes 2 CO out of 1 CO2 and the reduction hands one CO2 back, so
the cycle gains a carrier per turn; a blast furnace's gas volume really does grow
that way. **The carbon is the reagent and the carbon oxide is only the vehicle**,
which is why a furnace is charged with coke.

### 6. THERMITE — THE ONLY ROW IN EITHER SOLID TABLE WITH NO GAS AT ALL

Four crystals, no gas, so both one-sided pressure products are empty (exactly
1.0) and the affinity collapses to `k_f - k_r`, a constant. That is correct: with
no gas there is no quotient to move, so at ln K +29.5 the row is effectively
irreversible and runs to completion. One pin, on the reported 1200 K ignition
temperature, buys a column nothing was fitted to:

| T / K | conversion in 600 s |
|---:|---:|
| 298.15 | **0.0000%** — exactly zero |
| 600 | 0.0000% (3.1e-10 mol) |
| 800 | 0.2171% |
| **933** | **36.95%** — ⚠ **and this is where ALUMINIUM MELTS** |
| 1000 | 98.16% |
| 1200 | 100.00% |

⚠ 933 K is the trigger every account of thermite names, and nothing in this
engine knows it: the column is one Arrhenius pair.

⚠ **AND AN INSULATED FLASK IGNITES ITSELF.** The energy balance was already
there; 851.5 kJ/mol into a few J/K is a runaway nobody declared. Cold and
insulated it stays at 298.15 K to six figures and makes nothing; lit at 1000 K
it goes to 100% and the rise is the arithmetic — **+322.45 K** measured against
+323.86 predicted on a 50 J/K flask, +33.87 against +33.88 on a 500 J/K one.

⚠ **STATED LIMITATION: NOTHING CAPS THE TEMPERATURE.** A real thermite stops near
3135 K because the IRON BOILS, and a lattice in this engine may react and may
never boil. A 1 J/K flask reports 5469 K — above the RHS's own `T_MAX` clamp of
5000, which bounds RATE evaluation and not the state. **It is the same statement
the zinc retort makes** (below), and it is the honest cost of the one-boolean
lattice.

### ⚠ 7. THE ZINC RETORT KEEPS ITS THERMODYNAMICS AND LOSES ITS DISTILLATION

`mineral_data` holds zinc as a lattice, `thermo.get("[Zn]")` refuses the
monatomic vapour as a bare element, and a lattice here may react and may never
boil. So the row makes **solid** zinc, and the product removal that pulls a real
retort over is not expressible.
⚠⚠ **S10 CLOSED THIS, AND THE SENTENCE ABOVE IS WHY IT LOOKED HARD: it is about the `mineral_data` ENTRY, not about zinc.** `[Zn]` passes every test S4 admitted mercury on, so it moved to `element_data`, the row evolves a VAPOUR, and the threshold came DOWN to 1197.8 K — **with no engine change at all.** See §S10. ⚠ **The row does not need it**: ln K is already
+2.21 at the catalog's own 1400 K. Vented, the threshold is measured where the
thermodynamics put it — 3.61% at 1100 K, 29.44% at 1200, **87.05% at 1264**,
99.96% at 1300, 100% at 1400.

### ⚠⚠ 8. `carbothermic-reduction` WAS AN OUTCOME LABEL AND WAS SPLIT — AND THE ROW CHECK COST NOTHING THIS TIME

Five rows, **four mechanisms**, and only the oxide one is built. Crediting the
class on it would have claimed routes to calcium carbide and to white phosphorus
that this engine cannot make — `roasting-to-metal`'s false credit in a fourth
costume. See `data/catalog/README.md`. The split moves the denominator (224 →
227) and costs no route, because none of the other four was covered.

### ⚠ 9. AND THE INSTRUMENT AUDIT FOUND A FALSE CITATION FOUR MILESTONES OLD

`surface.ROASTING_A`'s pinning comment has ended *"validation/rate_ceiling.py
re-measures it"* since S1. **It did not.** `rate_ceiling` walks `net.reactions`,
and a `SurfaceReaction` never becomes a `Reaction`; S4 found the identical fault
about `SOLID_STATE_REACTIONS` and added a panel, and this table was left out —
with the sentence claiming otherwise sitting right beside the constant. S9
tripped over it while writing the same sentence for a new one.
`rate_ceiling.surface_panel` now reads it: every pre-exponential in the table is
**below the collision limit outright**, so no row can cross at any temperature.
⚠ And the units had to be the BIMOLECULAR ceiling, not the unimolecular one that
panel above it uses — a surface rate is order 1 in one gas, in L/(mol s). That is
M8's unit error, avoided by naming the order.

### 10. WHAT IS REFUSED, MEASURED RATHER THAN ASSUMED

* **`direct-combination`** (`vermilion-route`: `Hg + S8 -> HgS`) was on the queue
  as *"probably"* part of this work. It is not: mercury is a curated LIQUID
  element and S8 is a MOLECULAR solid, and `build_surface_arrays` refuses a
  non-lattice solid by name because `PhaseArrays.lattice` cannot answer "how much
  solid is there" for a species with a solid block AND a liquid block AND a
  headspace. Neither table's shape. **Still one class away and still not this.**
* **`blast-furnace`** gains three of its five classes and is still not
  template-ready: `slagging` has no template (and `silicon-dioxide` /
  `calcium-silicate` have no lattice), and both `gas-solid-reduction` rows in it
  need an `iron-ii-oxide` `mineral_data` refuses on the crystal Cp. **One class
  and one mineral away** — the closest any five-step route has been.
* **`carbon-combustion`'s ln K at 2200 K is +21.87 against a bar of +20**, the
  tightest row in `SURFACE_REACTIONS` by 46 nats. Not a marginal constant: above
  ~1000 K carbon dioxide over carbon is increasingly taken to CO, so this
  reaction's own product stops being the stable one. **The reversal is declared
  next door**, and nothing connects the two but a shared headspace.

**Files:** `src/chemsim/numerics/vessel_integrator.py` (the split, ~30 lines with
its argument), `src/chemsim/properties/solid_state.py` (+2 optional fields, two
guards, five rows, two constant blocks), `src/chemsim/properties/surface.py`
(+2 optional fields, one guard, one row, two constants, the false-citation note),
`src/chemsim/vessel/vessel.py` (the refusal lifted), `validation/smelting.py`
(new, 8 panels), `validation/rate_ceiling.py` (`surface_panel`),
`validation/catalog_coverage.py` (5 classes), `data/catalog/route_steps.psv`
(5 rows re-labelled), `tests/test_smelting.py` (new, 20 tests),
`tests/test_solid_state.py` (5 rewritten, 4 new), `tests/test_surface.py`
(2 rewritten), `data/catalog/README.md`, `README.md`, `COVERAGE_REPORT.md` and
both `derived/*.psv` (regenerated, byte-identical across `PYTHONHASHSEED`).

---

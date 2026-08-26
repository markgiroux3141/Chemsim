We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M8, M12, S1–S11 are DONE.**

# ⚠ THE BASELINE IS MEASURED. DO NOT START WITH THE SUITE.

**S11 RAN THE WHOLE SUITE AT THE END AND MEASURED 952 PASSED / 0 FAILED IN
13:15.** ⚠ It was run TWICE: the first run read 951/1 and the failure was a
standing test whose pinned number S11's own data change had moved
(`test_the_250_450_K_FIT_WINDOW_IS_STILL_THE_GENERAL_FAULT` — see engine queue
item 4). **952/0 would have been arithmetic, so it was re-run as one clean pass
rather than reported as a sum.** Take that number and spend the time on content. ⚠ **It was run AFTER
every `src/` edit, so it is a real baseline and not arithmetic** — the second
session running that is true. (932 at S10; +19 from `test_hydroformylation.py`
(11) and `test_wacker.py` (8), plus one added and one rewritten in
`test_critical.py` and one rewritten in `test_phase_properties.py`.)

⚠⚠ **S11 DID NOT TOUCH THE RHS EITHER** — not one line of `numerics/` or
`vessel/`, second milestone running. **But it DID change
`properties/physical_data.py`, and two examples moved because of it**, so
`validation/tolerance_audit.py` WAS re-run and its finding is:
*"NO example prints a quotable digit that moves"*, unchanged.
⚠⚠ **AND `oil_of_vitriol`'s WRONG HEADLINE IS FIXED — engine queue item 6 is
CLOSED**, at 1 moved line and worst 6.60e-05.

⚠ **THE TWO EXAMPLES THAT MOVED, AND THEY MOVED BECAUSE ETHYLENE GOT A MEASURED
BOILING POINT**: `competing_pathways`'s worst number goes 0.20380 → 0.20485
(0.5%) and `named_routes` reports ethanol-hydration at **2.7% instead of 2.9%**.
Both were measured before/after, example by example. **If you are comparing
against a pre-S11 number in either of those, this is why.**

⚠ **AND THE STANDING AUDITS ARE ALL CLEAN**, re-run at the end of S11.

```bash
python validation/smelting.py                 # ⚠⚠ S9's standing audit, ~1 min. RUN IT FIRST
python validation/hydroformylation.py         # ⚠ S11's, ~1 min. NEW
python validation/wacker.py                   # ⚠ S11's other one, ~1 min. NEW
python validation/gas_processes.py            # S7's, ~1 min
python validation/corpus_balance.py           # S7's other one, ~20 s. READ IT before picking
python validation/catalog_coverage.py         # ⚠ READ THE 'BOTH' LINE: 30/173, ~15 s
python validation/game_gates.py               # the element floor's cross-check, seconds
python tools/build_route_index.py             # the artefact nothing reads
python validation/cell_potentials.py          # M8's standing audit, seconds
python validation/rate_ceiling.py             # M12's, seconds. ⚠ S11 gave it a SIXTH panel
python validation/jacobian_bound.py           # S5's standing audit, ~1 min
python -m ruff check src tests examples validation tools
python -m pytest -q                           # ~13 min. ONLY after touching src/
python validation/tolerance_audit.py          # ~8 min. After touching the RHS **or any data table**
```

⚠ **THE SUITE AND THE TOLERANCE AUDIT ARE MINUTES OF SATURATED CPU ON THE USER'S
OWN MACHINE.** Say what a long run will cost before starting one, and ask.
`examples/plate_column.py` alone is 12 minutes, and
`tolerance_audit.py --only oil_of_vitriol` is 19.

---

# ⚠⚠ START HERE: THE ENGINE AND HONESTY QUEUE — IT STILL OUTRANKS THE TABLE BELOW

1. **⚠⚠⚠ 310 SPECIES ARE ESTIMATED BECAUSE NOBODY TYPED THEIR NAME. NEW IN S11,
   AND IT IS THE LARGEST HONESTY ITEM ON THIS LIST.**
   `properties/physical_data.py` is GENERATED, which reads as systematic. What it
   is generated FROM is `CANDIDATES` in `tools/build_physical_data.py` — **a
   hand-typed list of 37 names** (33 before S11). Anything not on it falls to
   Joback, whether or not `chemicals` holds five experimental sources for it.
   There is no refusal and no warning, and **the coverage audit cannot see it,
   because the record RESOLVES.**

   Measured over the whole catalog (1539 species with a graph):

       in physical_data.MEASURED_PHYSICAL            37
       no CAS resolvable                           1070
       CAS but genuinely no experimental Tb          126
       ⚠⚠ experimental Tb available, NOT in table    310
       ...of those, price a Tb in this engine today  229
       mean / median / worst |error|      5.81% / 2.94% / 84.89%
       over 2% / 5% / 10% / 20%              138 / 70 / 34 / 11

   Worst: arachidonic acid 819.35 against 443.15, dinitrogen tetroxide 503.28
   against 294.30, linolenic acid 769.43 against 504.15.

   ⚠⚠ **AND A BOILING POINT IS NOT A DECORATION IN AN ENGINE WITH A STILL IN
   IT.** Propene read Tb and Tc both ~17% high, which put Joback's Tc (427.64)
   ABOVE the oxo reactor's 420 K where the real one (364.21) is 55 K below — so
   the engine condensed **0.91 mol of "liquid propene" into a supercritical
   flask** and read 167 bar where it was charged to 200. One candidate line fixed
   it.

   ⚠ **THE COST OF DOING THIS AT SCALE IS STATED AND IT IS THE REASON IT IS NOT
   DONE**: it moves every example's volatility and energy balance and owes the
   tolerance audit plus a before/after on each example. **S11's four were done
   one at a time with the cost measured per example**, which is the pattern to
   follow. ⚠ `tests/test_critical.py::DELIBERATE_OVERRIDES` is the gate: an
   addition that changes a fifth working Joback record FAILS there until you
   write down what it cost.

   ⚠⚠ **AND THE INSTRUMENT WILL BE WRONG FIRST.** The first sweep counted 360 and
   listed borane boiling at 2823 K and methane at 4273, because
   `chemicals.CAS_from_any("C")` reads a bare SMILES as a FORMULA and returns
   CARBON. Use `CAS_from_any("smiles=" + smi)`. **A single-letter SMILES is also
   an element symbol.**

   ⚠ **M11 IS THE SAME MECHANISM FROM THE OTHER END.** Its own costed starting
   point is "10 species that need ONE measured boiling point each". They are on
   this list. **A session that builds the CANDIDATES list properly may close M11
   as a side effect** — worth checking before scheduling M11 separately.

2. **⚠⚠ NOTHING IN `build_phase_arrays` COMPARES T TO Tc. NEW IN S11.**
   A species is `condensable` or not, and that flag is a property of the SPECIES
   rather than of the state. So a CONDENSABLE species above its critical
   temperature still dissolves by Raoult's law against an Antoine curve
   extrapolated past its own domain.

   Measured: a Wacker flask at 400 K charged with 0.20 mol of ethylene over
   20 mol of water **dissolves 0.165958 of it — 83%, against a real ~2%**,
   because Psat reads **219.9 bar** off a curated Antoine **118 K above
   ethylene's critical temperature of 282.35 K.** Oxygen beside it is a
   Henry's-law solute and behaves perfectly.

   ⚠⚠ **AND A MEASURED BOILING POINT DOES NOT FIX IT — S11 PREDICTED IT WOULD AND
   MEASURED THAT IT DOES NOT.** 0.16588 → 0.16596, four figures unchanged,
   because ethylene's vapour pressure comes from `volatility._CURATED_ANTOINE`
   and **Tb does not feed that curve at all.** ⚠ **Ask which number the symptom
   actually depends on before curating the one that looks responsible.**

   ⚠ It makes the Wacker liquor ~40x richer in alkene than a real one, which is
   the only place it is currently reachable. Worth ZERO routes; take it for the
   honesty and say so. `validation/wacker.py` panel 4 is the measurement.

3. **⚠⚠ A METAL THAT BOILS OUT OF THE SOLID BLOCK — STILL OPEN, AND STILL THE
   BEST-SCOPED ENGINE ITEM.** Unchanged by S11; the S10 measurement stands and is
   reproduced here because it is what makes the item small.

   ⚠⚠ **MEASURED AFTER S10's COMMIT, BY PATCHING IRON'S VOLATILITY IN PLACE
   (Alcock's curve) AND RUNNING THERMITE INSULATED. IT WORKS:**

       vessel Cp    lattice iron    VOLATILE iron    where the iron went
          1 J/K       5469.43 K        3490.99 K     0.0192 gas / 0.0207 liquid
         10 J/K       2329.06 K        2284.28 K     0.0399 liquid (it MELTED)
         50 J/K       1322.45 K        1322.45 K     unchanged — never reaches Tm

   **The actual blocker is ONE BRANCH in `build_phase_arrays`** — the
   `if mineral is not None:` arm that pins `vol_A = NONVOLATILE_A`,
   `condensable = False` and `solidifies = False`. Letting a `MineralRecord`
   carry OPTIONAL volatility and having that branch consult it is a
   **setup-layer change with NO RHS edit**, so it carries no tolerance-audit
   exposure. ⚠ Iron must keep its `mineral_data` ENTRY (name resolution for
   `_catalyst_lattice` and thermite's `decl.solids`); it does not need `lattice`
   to stay True. The two hot-loop uses of `PhaseArrays.lattice` are in the
   SURFACE term only and iron is in no surface row, so `C_mix[Fe] ** 0 == 1.0`
   exactly.

   ⚠ **THE GENERAL FORM IS STILL WORTH FIXING**: `build_surface_arrays` already
   receives `decl.solids` and `decl.gases` separately and builds separate
   `order_solid`/`order_gas`, then collapses `nu` into ONE array and lets the RHS
   re-derive the split from `is_lattice`. **The information is present at setup
   and thrown away.** Build `nu_solid`/`nu_gas` there and split `C_mix` into two
   one-sided products — literally S9's move. Touches the RHS, so the five surface
   rows must come out bit-identical; ⚠ each row has exactly ONE solid and ONE gas
   factor today, so `a*b` vs `b*a` is the whole exposure and IEEE multiplication
   is commutative. S9's test is the template.

   ⚠⚠ **BUT THE DATA OBJECTIONS SURVIVE THE ENGINE FIX.** `[Fe]` still fails S4's
   DISAMBIGUATION test (three solid allotropes, two transitions inside thermite's
   own range) and Alcock tabulates **no sublimation curve** for iron, so zinc's
   best cross-check cannot be run at all — **ONE check, not four.** Deciding
   whether one is enough for a species with three allotropes is the real work and
   it is a judgement, not a measurement.

   ⚠ **WORTH ZERO ROUTES for iron.** ⚠⚠ **BUT MEASURE `direct-combination` FIRST:
   it is worth +1 AND it is refused by the SAME `build_surface_arrays`
   non-lattice check.** Hold that as a HYPOTHESIS — `Hg(l) + S8(s)` is not a gas
   attacking a crystal, so `SurfaceArrays`' form (extensive in the solid,
   INTENSIVE in the gas) may be wrong for it whatever the mask says.

4. **⚠⚠ THE 250–450 K FIT WINDOW — AND S11 MOVED A SPECIES FROM ONE BUCKET TO
   THE OTHER WITHOUT TOUCHING THE MECHANISM.** `CondensedProvider.get(mol,
   T_lo=250.0, T_hi=450.0)` is an organic-solvent window and **every caller in
   the repo takes the default.** Re-swept in S11 over each species' OWN Tm→Tb at
   21 points: **99 compounds return a negative liquid Cp inside their own liquid
   range** (worst carminic acid at **−21482 J/(mol K)**) and **38 more swing over
   5x**. ⚠ S10 recorded 103 and 41 with a script that was not preserved, so the
   difference of four may be METHOD rather than movement.

   ⚠⚠ **WHAT IS CERTAIN IS THAT ETHYLENE MOVED, AND IT MOVED THE WRONG WAY ON
   BETTER DATA.** It read **+1574 J/(mol K)** at its melting point before S11 and
   reads **−1782** after, because a MEASURED Tc changed the Rowlinson-Bondi fit.
   **A correlation extrapolated outside its domain does not get safer when its
   inputs get better.** `test_the_250_450_K_FIT_WINDOW_IS_STILL_THE_GENERAL_FAULT`
   pins both halves.

   * ⚠ **A negative Cp is not an accuracy problem: adding heat LOWERS the
     temperature.** S10 measured it reachable — 3.96 mol of liquid mercury gave a
     NEGATIVE TOTAL thermal mass.
   * ⚠⚠ **DO NOT JUST WIDEN THE WINDOW.** Most of the 99 have a JOBACK Tm/Tb that
     is itself meaningless (carminic acid "melts" at 1398 K and really
     decomposes). **Separate the wrong output from the wrong input first** —
     which is also **why item 1 above is upstream of this one.**
   ⚠ Worth ZERO routes. Measured inert on every example today.

5. **⚠ `slagging` — AND S11 RE-PRICED THIS ITEM AND IT WAS PRICED TOO CHEAPLY.**
   It was listed as "two curated minerals and one declaration". Re-queried against
   `chemicals` 1.5.2:
   * **`silicon-dioxide`** is fully available — CRC Hfs −910700, Gfs −856300,
     S0s 41.5, Cps 44.4. ✔
   * **`calcium-silicate` has NO thermochemical data under ANY of its three CAS
     numbers** (10101-39-0, 1344-95-2, 13983-17-0). ✘ **Not a curation job at
     all.**
   * **`iron-ii-oxide`**'s CRC standard row has **`Cps = NaN`**, confirming the
     recorded refusal. Its `Hfs` is in CRC and WEBBOOK and its `S0s` in WEBBOOK,
     so the same-database rule COULD be met — the crystal Cp is the blocker.
   **`blast-furnace` is blocked TWICE over, on SOURCES rather than on work.**

6. **⚠ THE CIS/TRANS BLIND SPOT — A REAL DATA JOB WITH A REAL TRAP.** Benson (the
   RMG group set) has no cis correction, so oleic and elaidic acid come back with
   IDENTICAL Hf and Gf and the engine reports a confident 50:50 for a real ~5:1.
   ⚠ **The data exists and is not usable as it stands:** WEBBOOK has both liquid
   enthalpies, −764.8 and −769.0 kJ/mol, and that 4.2 kJ/mol gap agrees with
   Benson's own historical cis NNI term of 4.18 to 0.4% — **two independent
   sources**. But neither has an S0, so no Gf can be derived, and grafting
   Benson's original correction onto RMG-fitted group values **mixes two bases**.
   ⚠ Worth ZERO routes today. `test_the_cis_trans_pair_prices_at_exactly_zero`
   pins the limit.

7. **⚠ THE CURRENT BUDGET — M8's OWN NAMED GAP, AND IT IS A LAYER 4 TERM.** Two
   electrode reactions in one cell divide nothing, so both run at full rate and
   activation selectivity washes out: k(brine)/k(water) is **4.76e+17 at 2.5 V,
   5.94 at 3.0, 1.00 at 4.0**. ⚠ Worth **ZERO new routes**.
   `test_the_activation_selectivity_washes_out_at_high_voltage` pins the gap.

8. **Pyrite** — one mineral entry from `pyrite-roasting` running, +1 on the
   intersection. ⚠ **RE-QUERIED IN S11 AND THE REFUSAL STANDS**: `Hfs` in
   WEBBOOK, `S0s` in **nothing**. This needs a SOURCE and not a workaround.

9. **⚠⚠ THE BURNER — THE LIVE FRAGILITY, STILL DEMOTED AND STILL NOT DISMISSED.**
   **~50 s at rtol 1e-8 against 0.8 s at the default.** S5 bounded the CRASH and
   explicitly did not bound the THRASHING. BDF is struggling with a liquid layer
   holding **1e-29 mol**, which `LAYER_REABSORB` drains toward zero without ever
   reaching it. **The question nobody has asked is whether a layer below
   `LAYER_EPS` should be *merged discretely* at a step boundary rather than
   drained continuously for ever.** ⚠ `merge_phases` already does exactly that at
   the `run` boundary. **Measure the layer-2 inventory over the failing run
   before designing anything.** It fires only at rtol 1e-8.

10. **THE CORPUS BALANCE BACKLOG — 75 ROWS, AND IT IS NOT A TO-DO LIST.** S7 built
    the check and deliberately fixed nothing, on the `diels-alder-route`
    precedent. ⚠ But **17 of the 75 are `spurious`** — a reagent written as
    consumed that is really a catalyst — and those are the cheapest and least
    inventive to correct. ⚠ `tools/catalog.py`'s `validate` still does NOT check
    balance, so the corpus can grow another one silently. ⚠ One BOTH-column route
    carries one: `perkin-route` step 1.

11. **⚠ `hydrolysis` — AND READ S3's LANDMINE FIRST.** It unlocks **exactly ONE
    route alone, `vitriol-distillation`**, and that route's step 1 reads
    `-> iron-ii-OXIDE` while the engine makes HEMATITE. ⚠ **That is item 5's
    mineral again, from the other side.**

12. **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
    re-scope before scheduling)**, **M9 (polymers, 12 routes)**, **M10 (the site
    balance S1 did not build, 8 routes)**, **M11 (the unpriceable families, 16
    routes — ⚠⚠ and see item 1: 10 of them need ONE boiling point each, which is
    the same mechanism)**.

13. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
    the *deposition-needs-a-seed* half into a real bound in
    `SolidStateArrays.units`. What is still not expressible is a solid appearing
    from NO solid — `hydride-thermal-deposition` is still a mechanism gap for
    that reason. ⚠ **S9 leaned on the modelled half deliberately.**

---

# THE COVERAGE QUEUE — **STILL ALL +1, AND THE TWO BEST ROWS ARE GONE**

S11 took `hydroformylation` and `wacker-oxidation`, which were the queue's top
two rows for mechanic value. What is left is thinner. **Pick for the MECHANIC,
and say which you are picking for.**

| class | its route | worth | what it is |
|---|---|---:|---|
| ⚠⚠ **`skraup-cyclisation`** | `skraup-route` | **+1, and it is now the queue's best row** | aniline + acrolein -> quinoline. ⚠ Step 1 (`dehydration`) is already covered, so this is genuinely the last class the route needs, and S11 CHECKED the row rather than leaving it as a warning. **Aniline on both sides is NOT the `spurious` pattern** — the nitrobenzene oxidant is REDUCED to aniline. **It balances at `3 aniline + 3 acrolein + 1 nitrobenzene -> 3 quinoline + 1 aniline + 5 water`, four aromatic rings in and four out.** That is the real Skraup stoichiometry and it is what the SMARTS has to carry: **7 reactant slots and 9 product slots** (Claus proves 24 works). ⚠ Every species resolves, and `sulfuric-acid` on both sides is `_maybe_catalyse`'s own case |
| ~~**`oxidative-cleavage`**~~ | `vanillin-lignin` | ⚠⚠ **S11 MEASURED IT AND REFUSED IT** | The row is `coniferyl alcohol + O2 -> vanillin + water` and **it cannot be that reaction**: a C10 monolignol makes one C8 vanillin and a C2 fragment the row does not name. `corpus_balance` passes it because it balances at **8 C10H12O3 + 7 O2 -> 10 C8H8O3 + 8 H2O** — eight aromatic rings in and TEN out. Naming the missing product would be inventing chemistry inside the corpus. ⚠ **Do not re-derive this**; the audit prints it now |
| `fischer-tropsch` | `fischer-tropsch` | +1 | `8 CO + 17 H2 -> octane + 8 H2O`, **25 slots**. The Claus template proves 24 works — but read M8 §6 on the lump that was refused |
| `molten-salt-electrolysis` | `downs-cell` | +1 | ⚠ **A MELT is not a phase this project has** — M8's own named leftover, and it is engine work |
| `catalytic-air-oxidation` | `p-xylene-oxidation` | +1 | ⚠⚠ **M5 REFUSED THIS CLASS** — its four rows are at least three mechanisms. **Split it before crediting it**, and only one of the four rows is runnable |
| `direct-combination` | `vermilion-route` | +1 | ⚠⚠ **S9 MEASURED AND REFUSED IT**, and engine queue item 3 is the only thing that could change that. **Do not re-derive this** |
| `fermentation` | `abe-fermentation`, `msg-route` | +1 | ⚠ **M5 REFUSED IT** as a metabolic NETWORK rather than a transformation. That refusal still stands |
| `separation` | `coal-tar-distillation` | +1 | ⚠ **M5 REFUSED IT**: a distillation is not a reaction class, and the feedstock has no graph |

⚠⚠ **AND READ `corpus_balance.py`'s LAST PANEL BEFORE PICKING ANY OF THEM.** S11
added it: **the balance audit's test is a WEAK one.** It asks whether ANY positive
coefficient vector conserves the elements, and element conservation does not
forbid rearranging carbon skeletons — so a row can PASS and still not be the
reaction it is written as. `vanillin-lignin` is the standing example and it cost
S11 a template. **A pass there is not permission to write a SMARTS.**

⚠⚠ **AND THE EIGHT THE REPORT STILL PROMISES THAT THE BALANCE AUDIT KILLS.** Do
not start any of these without reading `corpus_balance.py`'s output on it:

| class the report ranks | route | the step that cannot balance |
|---|---|---|
| **`isomerisation` (still the report's TOP ROW, at +2)** | `hydrogenation-margarine` | step 2 `spurious` — an H2 in and none out |
| " | `starch-hydrolysis` | step 1 `atoms` |
| `metal-ion-aldehyde-oxidation` | `tollens-test` | step 1 `atoms` |
| `pyrolysis` | `wood-distillation` | step 1 `atoms` |
| `biological-transformation` | `tyrian-purple-route` | step 1 `atoms` |
| `dissolving-metal-reduction` | `aniline-route` | step 1 `atoms` |
| `polycondensation` | `pet-route` | step 2 `atoms` |
| `thermal-cracking` | `steam-cracking` | step 1 `spurious` |

⚠ **`isomerisation` IS DEAD THREE TIMES OVER AND IS STILL THE TABLE'S TOP ROW.**
Besides the two balance failures: `oleic -> elaidic` prices at **dH = dG = 0.000
EXACTLY** and `glucose -> fructose` at **K = 4.8e-08** because the corpus spells
one as a pyranose and the other as a furanose. **Do not build it.**

---

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§S11, §S10, §S9, §S8, §S7, §M8, §S1, §S3, §S4, §S5 and
  §S6 are the ones to read**: **S11 found that a species is estimated because
  nobody typed its name — `physical_data.py` is generated from a hand-typed list
  of 33 — that a SELECTIVITY is a rate ratio between two templates racing for one
  substrate, that Evans-Polanyi names the WRONG major product when kinetics fight
  thermodynamics, and that its own instrument read methane's boiling point as
  carbon's**; S10 found that S9's top engine item was HALF A DATA JOB, that
  splitting it in two is what LOCATED the engine gap, and that a NEGATIVE liquid
  heat capacity had been in the engine since S4; S9 found that the engine gap S8
  called "the most valuable unscoped item in the plan" was ONE ALGEBRAIC
  REARRANGEMENT; S8 did a job this file called "cheapest" for two sessions and
  measured it at +0 on the number that counts; S7 measured the queue's top two
  rows at ZERO and split a class in a way that LOWERED the headline; M8's brief
  predicted the wrong failure; S1's brief asked for one mechanism and the
  arithmetic said two; S3 found the instrument's own OUTPUT was not diffable;
  S4's brief said to reverse a re-label and the arithmetic said keep; **S5's
  brief named the wrong LAYER**; and **S6's brief handed it a number that was
  wrong.**
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1, 86 is S2, 87 is
  S3, 88 is S4, 89 is S5, 90 is S6, 91 is M8, 92 is S7, 93 is S8, 94 is S9,
  95 is S10, 96 is S11.**
NEXT_SESSION.md — the invariants table at the bottom is the contract, and S7, S8,
  S9, S10 and S11 each added a block to it. ⚠⚠ **S10 WITHDREW a row** and S11
  added **two more LIMITS TO REMOVE rather than invariants to keep** (the
  Wacker's oxygen order; ethylene's solubility). ⚠ Read the two warnings above it
  before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including S9's two splits,
  S7's of `combustion`, M8's of `electrolysis`, S3's of `thermal-decomposition`
  and S4's decision NOT to un-split `roasting-to-metal`; plus
  `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-competing-templates,
  chemsim-physical-data-sourcing, chemsim-vaporising-metal,
  chemsim-declared-rate-orders, chemsim-catalysis-and-bounds,
  chemsim-coverage-catalog, chemsim-corpus-balance and
  chemsim-generated-artefacts.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 45 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, a catalyst you have to actually put in
the flask, a route that nothing declares, a Jacobian that cannot be probed outside
its own state, a dial that decomposes things in the order their chemistry says
they should, four inorganic gas processes whose whole behaviour is their
reversibility, three smelters that take ore, coke and air to metal, a retort that
DISTILS its metal off, **two templates that RACE for one alkene and hand back a
selectivity nobody typed**, and **a catalyst that only exists if there is water to
dissolve it in**. `SAVE_VERSION` is **5**.
Coverage: **50/229 classes**, **45 templates**, **40/173 template-ready**,
**77/173 species-ready** — and ⚠⚠ **30/173 BOTH, which is the only one of the
three a route can be judged on.**

---

# ⚠⚠ WHAT S11 TURNED OUT TO BE: +2 ON THE INTERSECTION, AND ONE FINDING BIGGER THAN BOTH

**+2 classes (48 → 50 of 229), +2 template-ready (38 → 40), +0 species-ready,
+2 RUNNABLE (28 → 30) — all four predicted before the audit ran and all four came
out.** ⚠ **NO ENGINE CODE CHANGED**: not one line of `numerics/` or `vessel/`,
second milestone running.

| | before | after |
|---|---:|---:|
| classes with a template | 48 / 229 | **50 / 229** |
| routes template-ready | 38 / 173 | **40 / 173** |
| routes species-ready | 77 / 173 | 77 / 173 |
| ⚠⚠ **routes BOTH — the one to quote** | **28** | **30** |
| templates | 43 | **45** |

## ⚠⚠ 1. A SELECTIVITY IS A RATE RATIO, AND THE THERMODYNAMICS POINT THE WRONG WAY

`hydroformylation`'s two catalog rows are ONE reaction with TWO regiochemistries.
Two SMARTS differing only in which alkene carbon takes the formyl group, racing
for one propene. **ONE number is fitted** — 4.8 kJ/mol of barrier difference, set
so `exp(dEa/RT)` = 4.0 at the row's own 420 K. Everything else is a prediction.

⚠⚠ **AND THE ENGINE'S OWN TABLES SAY THE BRANCHED PRODUCT SHOULD WIN**: it is
9.35 kJ/mol more exothermic and takes 2.33 of every 3.33 molecules at
equilibrium, while the real reactor makes the LINEAR one four to one. **So
Evans-Polanyi had to be switched OFF and that is a declaration, not an
omission** — any `alpha > 0` hands the more exothermic route the lower barrier
and names the wrong major product with confidence.

Measured, 1 L at 200 bar / 420 K / 0.1 mol cobalt / 1 h: **94.32% converted,
n:iso 3.9523**, conservation clean, carbon closure exact.

## ⚠⚠ 2. NOBODY DECLARED A MAXIMUM OPERATING TEMPERATURE AND THE FLASK HAS ONE

    T / K      380     400     420     450     480     520
    n:iso     4.569   4.234   3.952   3.543   1.867   0.760
    kinetic   4.569   4.235   3.953   3.607   3.329   3.035

Up to ~450 K the flask IS the exponential, to three figures. Above it the two
REVERSE reactions get inside the reactor's own hour and the stable branched
product starts winning; the conversion turns over in the same place. **A real
cobalt oxo reactor sits at 410–450 K.**

## ⚠⚠ 3. IRREVERSIBLE WOULD HAVE LIED BY A FACTOR OF 6000, AND IT WAS MEASURED

Three moles of gas become one, so ln K goes +2.31 at 420 K to **−7.46 at 600**.
One hour, each temperature's own charge:

| | 1 bar, reversible | 1 bar, IRREVERSIBLE | 200 bar, reversible |
|---|---:|---:|---:|
| 420 K | 0.469% | 0.470% | 93.1% |
| 500 K | 1.475% | 20.202% | 91.0% |
| **600 K** | **0.013%** | **77.933%** | 53.3% |

`alkene_hydrogenation`'s "irreversible is a claim about temperature" argument does
NOT transfer. **Count the moles of gas on each side before declaring
irreversible.**

## ⚠⚠ 4. AND THE PAIR CROSSES FROM KINETIC TO THERMODYNAMIC CONTROL UNAIDED

    t         1 h    10 h   4 days  6 weeks  1 year  11 years  settled
    n:iso    3.952  3.944   3.863    3.204    1.188    0.513    0.513
    GAS      3.304  3.296   3.229    2.678    0.993    0.4286   0.4283

`K(n)/K(iso)` is **0.4283** and the HEADSPACE lands on it to four figures, through
reverse barriers (`Ea - dH`) nobody typed. ⚠⚠ **The INVENTORY ratio settles at
0.513 instead**, because the reactor holds ~1.7 mol of LIQUID product and butanal
is the less volatile. **AN EQUILIBRIUM CONSTANT IS A STATEMENT ABOUT PARTIAL
PRESSURES: read it against the headspace, never against the total moles.**

## ⚠⚠ 5. THE WACKER — AND AN ION CATALYST GATES ON THE SOLVENT, NOT ON ITSELF

`[Cu+2]` is priced from `ion_data` and `thermochemistry` refuses a charged species
by name, so a flask without `electrolyte_provider()` **REFUSES** rather than
running slowly. ⚠ **And it refuses at the `Vessel`, not at `build_network`** —
a network is a GRAPH question and succeeds, naming the ion; pricing is one layer
down. Measured: **40.1% in one minute, 98.2% in ten** at 400 K over 0.02 mol of
Cu(II), against a real one-stage reactor's 30–40% per pass.
⚠ And its first-order copper loading is RIGHT rather than provisional: the
missing site balance is a statement about a SURFACE, and there are none in a
liquor.

## ⚠⚠ 6. ONE THING IN THAT TEMPLATE IS DELIBERATELY WRONG, WITH THE PRICE MEASURED

The real Wacker rate law is **ZERO order in oxygen**. It cannot be declared that
way: the kinetics kernel has **no availability gate** (`_avail` serves the solid
block only), so a reactant at order zero keeps reacting after it runs out and is
driven negative. Cost, measured: acetaldehyde in 60 s goes **1.00 / 1.92 / 3.53 /
5.85x** as the oxygen charge doubles, where a real reactor gives 1.00 throughout.
⚠ **NOT an invariant to preserve — a LIMIT to remove.**

## ⚠⚠⚠ 7. A SPECIES IS ESTIMATED BECAUSE NOBODY TYPED ITS NAME — 310 OF THEM

Engine queue item 1, and it was found by a failing reactor rather than by an
audit. See there for the table and the cost. The two things to carry:

* ⚠⚠ **A GENERATED FILE IS ONLY AS SYSTEMATIC AS ITS INPUT LIST.** This project
  already knows that a generated file NOTHING READS rots. This is the other half:
  a generated file whose SOURCE is hand-typed is not a survey, it is a
  transcription, and it looks identical from the outside.
* ⚠⚠ **AND THE SCOPING GUARD THAT BLOCKED THE FIX WAS RIGHT TO EXIST AND WRONG TO
  SAY "NEVER".** `test_the_measured_table_never_overrides_a_working_joback_record`
  failed and was RIGHT to; but its own stated reason — "the moment it stops being
  true the azeotrope, the boiling points and the crop sizes all move at once" —
  **is a call for measurement, not a reason never to do it.** It is now
  `DELIBERATE_OVERRIDES`, naming the four records replaced with what each cost,
  and still refusing anything unnamed.

## ⚠⚠ 8. ENGINE QUEUE ITEM 6 IS CLOSED, AND **NOT** BY RAISING `REPORT_ABS`

The obvious fix was to raise `REPORT_ABS` above 2.9e-05. It is the wrong one:
`REPORT_ABS` is SYMMETRIC, so raising it would blind the audit to a small quantity
**GROWING** as well as shrinking, and a residual growing under refinement is the
defect the whole file exists to catch. The fix is a SECOND floor,
`CONVERGING_ABS`, applied only when the tight run's value is SMALLER.
**Direction is the information the old test threw away.**

⚠ And the number came out of a measurement the project already had rather than
out of the audit: `NEXT_SESSION.md` records that same column swinging **2.5e-09
to 4.5e-04 under an INERT 0.5% N2 nudge.**

**PREDICTED BEFORE THE 19-MINUTE RUN AND ALL FOUR CAME OUT:** 5 moved lines → 1;
worst 0.9985 → **6.60e-05**; the headline flips to "(below 0.1%)"; and
`CONVERGING_ABS` fires on **ZERO tokens across all twelve cheap examples**, which
is the safety measurement that mattered.

## ⚠ 9. THE ONE `rate_ceiling` ROW WHOSE CROSSING TEMPERATURE IS A REAL STATEMENT

Every other reverse it flags is high-order, so the ceiling comparison is M8's unit
error and the column is only good for RANKING. `hydroformylation_linear_rev` is
`butanal -> propene + CO + H2`: **one molecule falling apart**, so its `A` really
is in 1/s. It is **2.0e26 and 1.2e27**, crossing at **969.4 / 966.8 K** — the
third appearance of an **entropy of gas-making in a pre-exponential**
(dS_rev = +251.6, so `exp(dS/R)` is 1.4e13 by itself). ⚠ The brief predicted
~824 K off a 1e13 ceiling and the audit's own constant put it 145 K higher; **the
measured number stands.**

## 10. THE SMALL THINGS

* ⚠ **A COLUMN THAT ANSWERS ONE QUESTION CANNOT ANSWER THE NEXT ONE**, again: the
  oxo audit's panel 3 printed only the actual n:iso at first and read as if the
  ARRHENIUS ratio had collapsed. It prints the kinetic column beside it now.
* ⚠ **The oxo audit's own prose rotted TWICE inside this session** — once when
  reversibility changed the 480/520 K numbers, once when propene's boiling point
  changed the conversion. **Third session running.**
* ⚠ A `⚠` inside a `print()` nearly shipped again. Docstrings fine, printed text
  ASCII. **TWENTY-FIVE sessions running.**

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ 310 SPECIES HAVE A MEASURED BOILING POINT THIS ENGINE IS NOT USING (S11).**
229 price a Tb today, mean error 5.81%, worst 84.89%. Engine queue item 1.

**2. ⚠⚠ NOTHING COMPARES T TO Tc (S11).** A condensable species above its critical
temperature still dissolves by Raoult's law against an extrapolated Antoine curve.
Ethylene is ~40x too soluble in the Wacker liquor. Engine queue item 2.
**A LIMIT to remove, not an invariant.**

**3. ⚠⚠ THE WACKER'S OXYGEN ORDER IS FIRST AND SHOULD BE ZERO (S11).** The kernel
has no availability gate. Measured at 1.00 / 1.92 / 3.53 / 5.85x.
**A LIMIT to remove, not an invariant.**

**4. ⚠⚠ A LATTICE MAY REACT AND MAY NEVER BOIL — HALF CLOSED BY S10.** What
remains is thermite: nothing caps the temperature, and iron cannot make zinc's
move. **Engine queue item 3**, worth ZERO routes.

**5. ⚠⚠ THE BURNER IS STILL ~50 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT.** The
crash is bounded; the thrashing is not. **Engine queue item 9.**

**6. ⚠⚠ NO CURRENT BUDGET (M8).** Selectivity washes out above ~2.7 V.

**7. ⚠⚠ THE ION TABLE'S MIXED BASIS (M8, pre-existing).** dG survives it, dS does
not. Quote E_dec at 298 K; do NOT quote its temperature derivative or a cell's
HEAT.

**8. ⚠⚠ 75 CATALOG ROWS CANNOT BE BALANCED (S7).** Reported, not fixed. One of
them (`perkin-route` step 1) is in the BOTH column and is inert.

**9. ⚠⚠ THE ESTIMATORS CANNOT TELL A CIS ALKENE FROM A TRANS ONE (S7).**

**10. ⚠ `deacon_oxidation_rev` CROSSES THE BIMOLECULAR CEILING AT 1141 K**, and a
solid decomposition's forward constant crosses the unimolecular one at 3710 K.
⚠ **S11 added two rows that cross at 967/969 K**, and they are the only ones whose
crossing is a physical statement rather than a ranking.

**11. ⚠ `detailed_balance`'s RATE CAP COMPARES A CATALYSED PRE-EXPONENTIAL AGAINST
A LIMIT NOT IN ITS UNITS.** It does not fire on any catalysed template.

**12. THE DEFAULT TOLERANCE, BOUNDED RATHER THAN OPEN.** ⚠ `tolerance_audit.py`
is a STANDING audit: run it after touching the RHS **or any data table**. Its
three self-check examples must come out OUTPUT IDENTICAL. ⚠ Its
`oil_of_vitriol` headline is FIXED as of S11.

**13. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever. M10.
⚠ **S11 measured the one case where that is CORRECT**: a homogeneous ion catalyst
has no sites to saturate.

**14. ⚠⚠ 99 CORPUS ROWS HAVE A NEGATIVE LIQUID HEAT CAPACITY (S10, re-swept S11).**
Plus 38 swinging over 5x. ⚠ **S11 moved ethylene from +1574 to −1782 by giving it
a MEASURED Tc** — better data, same window, worse number. **Engine queue item 4.**

**15. ⚠ NUCLEATION, HALF modelled.** A solid can only grow where one already is.

**16. ⚠ LIQUID MERCURY IS 99.85% HELD IDEAL.**

**17. ⚠ THE FLAT COLUMN IS STILL FLAT, AND THAT IS CORRECT.**

**18. ⚠ THE ELEMENT FLOOR'S SOLID HALF IS CURATED AND ITS GAS HALF IS STILL
REFUSED.** 33 compounds remain refused as bare elements and none blocks a route.

**19. ⚠ `iron-ii-oxide`, `pyrite` AND `calcium-silicate` ARE ALL SOURCE-BLOCKED,
RE-QUERIED IN S11.** FeO has no crystal Cp in CRC; pyrite has `Hfs` in WEBBOOK and
`S0s` in nothing; **calcium silicate has nothing at all under any of its three CAS
numbers.** All three refusals follow rules worth keeping.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K.** PRE-EXISTING, **measured
inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Twenty-two times now. ⚠ **AND THE SOLVER IS PART OF THE ARITHMETIC**
(M8).
⚠⚠ **A GENERATED FILE IS ONLY AS SYSTEMATIC AS ITS INPUT LIST.** S11: 310 species
are priced by Joback not because a measurement is missing but because
`tools/build_physical_data.py`'s `CANDIDATES` is 33 hand-typed names. **The file
looks generated from the outside and is a transcription on the inside.**
⚠⚠ **ASK WHICH NUMBER THE SYMPTOM ACTUALLY DEPENDS ON BEFORE CURATING THE ONE
THAT LOOKS RESPONSIBLE.** S11 curated ethylene's boiling point to fix a flask
dissolving 83% of its ethylene, and measured 0.16588 → 0.16596 — **four figures
unchanged**, because the vapour pressure comes from a CURATED ANTOINE that Tb does
not feed.
⚠⚠ **A CORRELATION EXTRAPOLATED OUTSIDE ITS DOMAIN DOES NOT GET SAFER WHEN ITS
INPUTS GET BETTER.** Ethylene's liquid Cp at its melting point went from +1574 to
−1782 when it gained a MEASURED critical temperature.
⚠⚠ **EVANS-POLANYI NAMES THE WRONG MAJOR PRODUCT WHEN KINETICS FIGHT
THERMODYNAMICS.** `alpha > 0` scales the barrier with dH, so it hands the more
exothermic route the lower barrier. Before declaring `alpha`, ask whether the real
selectivity agrees in SIGN with the enthalpy ordering.
⚠⚠ **AN EQUILIBRIUM CONSTANT IS A STATEMENT ABOUT PARTIAL PRESSURES.** The oxo
reactor's headspace settles on `K(n)/K(iso)` to four figures and its INVENTORY
settles 20% away, because it is two-phase. **Read K against the headspace.**
⚠⚠ **A DECLARED ORDER OF ZERO DRIVES ITS REACTANT NEGATIVE.** `_avail` serves the
solid block only. Every declared rate law must keep at least order 1 in each
species it consumes; where that makes the law wrong, MEASURE the cost and print
it.
⚠⚠ **COUNT THE MOLES OF GAS ON EACH SIDE BEFORE DECLARING IRREVERSIBLE.** If they
differ, the equilibrium turns over somewhere reachable — 6000x for the oxo pair at
600 K and 1 bar.
⚠⚠ **A SCOPING GUARD IS NOT A PHYSICS CLAIM, AND ITS OWN REASON MAY BE A CALL FOR
MEASUREMENT.** "Never overrides a working Joback record" became "overrides only
where DECLARED and MEASURED", and the guard is stronger for it.
⚠⚠ **A SINGLE-LETTER SMILES IS ALSO AN ELEMENT SYMBOL.**
`chemicals.CAS_from_any("C")` returns CARBON. Use `"smiles=" + smi`.
⚠⚠ **A REFUSAL'S SENTENCE IS A CLAIM ABOUT A NAMED THING — CHECK WHICH THING.**
⚠⚠ **AND TWO SYMPTOMS CITING ONE SENTENCE ARE NOT NECESSARILY ONE GAP.**
⚠⚠ **THERMODYNAMIC CONCLUSIONS SURVIVE A PHASE CHANGE IN A PRODUCT; KINETIC ONES
NEED NOT.**
⚠⚠ **ASK WHAT A FIT WAS ANCHORED ON, NOT WHETHER THE CHECK LOOKS FAMILIAR.**
⚠⚠ **A CORRELATION'S FIT WINDOW IS A DEFAULT ARGUMENT NOBODY OVERRIDES.**
⚠⚠ **A SHARED PROVENANCE STRING GOES SILENTLY WRONG ON THE NEXT ADDITION.**
⚠ **CHECK WHETHER A NEW WRONGNESS IS A NEW CLASS OR A NEW MEMBER.**
⚠⚠ **A RECORDED REFUSAL CAN BE RIGHT ABOUT ITS MEASUREMENT AND WRONG ABOUT ITS
SCOPE.**
⚠⚠ **READ THE CATALOG ROW, NOT THE CLASS NAME.** S11: `skraup-route` step 2 has
ANILINE ON BOTH SIDES, because the oxidant is reduced to it — and that row is
REAL. `vanillin-lignin`'s, next to it on the same queue, is not.
⚠⚠ **AND A BALANCE CHECK IS A NECESSARY CONDITION, NOT A SUFFICIENT ONE.**
`corpus_balance` asks whether ANY positive coefficient vector conserves the
elements. `vanillin-lignin` passes at **8 rings in and 10 out**. **Element
conservation does not forbid rearranging carbon skeletons**, and the audit now
says so in its own last panel.
⚠⚠ **A COLUMN THAT ANSWERS A QUESTION CANNOT ANSWER THE NEXT ONE.** `RUNNABLE`
cannot ask whether the number is RIGHT, whether the product is a GRAPH, or whether
the CREDIT under the ranking is real. **And S11 adds: a coverage table cannot ask
whether a class's SECOND product is made** — a template making only the linear
aldehyde reads identically there.
⚠⚠ **A CLASS IS A MECHANISM CLAIM, AND A SPLIT MAY LOWER THE HEADLINE.**
⚠⚠ **A SPECIES JOB SHOULD FOLLOW THE TEMPLATE IT ENABLES, NOT LEAD IT.** S11
followed it and it worked; the four species were curated for two templates that
already existed.
⚠ **A BRIEF'S EXPECTED OUTCOME IS A HYPOTHESIS.** **S11's said a measured boiling
point would fix a solubility and it did not.**
⚠ **PREDICT THE NUMBER BEFORE YOU MEASURE IT.** S3 +2/+0; S4 +1/+1; S6 predicted
14 and measured 16; M8 three for three; S7 five for five; S9 four for four; S10
four for four and all four ZERO; **S11 four for four.**
⚠ **VERIFY A CREDIT BY RUNNING IT, NOT BY READING THE CODE THAT WOULD RUN IT.**
⚠ **AND VERIFY A BIT-IDENTICAL CLAIM AGAINST THE EXAMPLE SET, NOT AN ARGUMENT.**
⚠ **A CONSTANT'S UNITS ARE WHAT MAKE ITS VALUE DEFENSIBLE.**
⚠ **AN ARRHENIUS PAIR IS NOT SEPARABLE.**
⚠ **AN `inf` IS USUALLY THE WRONG BOUND, NOT A BOUND NEEDING SOFTENING.**
⚠ **A RELATIVE-DIFFERENCE TEST IS MEANINGLESS ON A COLUMN WHOSE CONVERGED VALUE
IS ZERO — AND THE FIX IS DIRECTIONAL, NOT A BIGGER FLOOR.**
⚠ **A NEW CREDIT MUST BE A FALLBACK BEFORE IT IS AN OVERRIDE.**
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS.** S2's harness invented a finding;
S1's coverage audit credited a route that cannot run; S3's report could not be
diffed; S4's rate-ceiling audit made a claim about a table it does not read; S6's
target column had been understating itself since M3; M8's new audit found a
pre-existing ion-table error; S7 found the coverage audit pricing a species the
engine refuses; S9 found a source comment CITING an audit check that never
existed; S10's `game_gates` panel INVENTED a 90 kJ/mol error; **and S11's
boiling-point sweep read methane's boiling point as carbon's and counted 360 where
the answer is 310.**
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS.
⚠ **A GENERATED FILE NOTHING READS IS THE ONE THAT ROTS.** Regenerate all three
catalog artefacts and check them across `PYTHONHASHSEED`.
⚠⚠ **AND A GENERATED FILE'S PROSE ROTS EXACTLY LIKE A HAND-WRITTEN ONE.** ⚠ The
root `README.md`'s coverage table is NOT generated — S4 corrected it, S6 again, M8
again, S7 again, S9 again, S11 again.
⚠ **A PHASE LABEL CARRIES A STANDARD STATE.** So does a BASIS.
⚠ **BDF IGNORES `jac_sparsity` THE MOMENT `jac` IS CALLABLE.**
⚠ Windows console is cp1252: **a warning glyph inside a `print()` kills a
script.** Docstrings fine, printed text ASCII. (TWENTY-FIVE sessions running.)
⚠⚠ **`sed -i` REWRITES EVERY LINE ENDING IN A CRLF FILE, AND ON THIS MACHINE IT
ALSO FAILS OUTRIGHT IN THE SCRATCHPAD** ("invalid cross-device link"). This repo
is MIXED: markdown and `.psv` are CRLF, and so are `element_data.py`,
`solid_state.py`, `volatility.py`, `catalog_coverage.py`, `rate_ceiling.py`,
`gas_processes.py`, `template.py`, `reaction.py`, `synthesis.py`,
`thermochemistry.py`, `mineral_data.py`, `condensed.py`, `library.py`,
`test_solid_state.py`, `test_critical.py`, `test_phase_properties.py`,
`build_physical_data.py`, while `vessel.py`, `surface.py`, `thermo.py`,
`builder.py`, `constants.py`, `jacobian.py`, `test_surface.py`,
`tolerance_audit.py` and the newer `validation/*.py` are LF. **Read binary, detect
`\r\n`, restore it on write, and check `git diff --stat` after the first edit to
any file.** S7, S9 and S11 each used a short CRLF-preserving splice helper for
every edit; it is worth rebuilding.
⚠ **HEREDOCS EAT ESCAPES AND CHOKE ON A LARGE BLOCK CONTAINING QUOTES.** Write
the payload with the Write tool and splice it. S11 lost a command to exactly this.
⚠ **A GENERATOR CAN LEAK A `numpy` REPR INTO ITS OUTPUT.** Cast to `float`.
⚠ **DO NOT NAME A LOCAL `net` IN A SCRIPT THAT ALSO HAS A `net()` HELPER.**
⚠ An em dash in a markdown anchor will not match a `--` you typed.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u`.
⚠ **A CANONICAL SMILES IS NOT THE ONE YOU TYPED.** S11 lost a probe to
`st.total("CC=C")` returning 0.0 because the network holds `C=CC`.

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays; RDKit stays in matter.
NO silent approximations. REFUSE loudly rather than return a confident wrong
number — and a LATENT fragility is a third case: report it, do not refuse it.
⚠ **AND REFUSING TO *DISSOLVE* A SPECIES IS NOT REFUSING TO *PRICE* IT.**
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?"
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; `solid_state=False`
exactly no crystal reacting; `surface=False` exactly no gas attacking one; an
all-zero `order_solid` exactly the old kinetics kernel; `cell_potential=0.0`
exactly the pre-M8 engine, bit for bit; an all-positive `nu_gas` exactly the
pre-S9 solid-state term, bit for bit; `SolidStateReaction.Ea is None` exactly M6's
derived pair; `SurfaceReaction.A is None` exactly the shared sulfide clock;
`BoundedJacobian` with its bound lifted exactly BDF's own differencing; the Born
term exactly zero in PURE water; the five pH values; SAVE_VERSION stores the
CONDITION, never the instant; every gaseous element reference state Hf = Gf = 0
EXACTLY; a CONDENSED reference state's ideal-gas record is a MEASUREMENT and must
not be zero; every METAL Hf = Gf = 0 EXACTLY on the solid basis; a reference state
its own database does not price at Hf = 0 is REFUSED; no mineral pricing
differently under the two providers; `ion_data` and `electrolyte` never subtracted
from each other; **a declared rate order may NEVER be reversible**; an `electrons`
count may never carry declared orders; an electrode template is a WHOLE CELL,
charge balanced on both sides; the reverse of an electrode reaction carries MINUS
the work; an IRREVERSIBLE surface row whose `ln K` is under +20 is REFUSED; a
solid-state row with no crystal on EITHER side is REFUSED; an EXOTHERMIC
solid-state row with no declared kinetics is REFUSED, and a declared `Ea` below
`dH` is REFUSED; half an Arrhenius declaration is REFUSED in both solid tables;
the four pre-S4 solid-state rows take the raw `units` minimum, bit for bit; an
element's `Hvap` is Clausius-Clapeyron on the vapour-pressure curve `volatility`
actually evaluates; the reflux ratio is the ratio of two drain conductances out of
one condenser; the fragmentation SEARCH runs only after the greedy pass has been
REFUSED; an ion is never counted in the held-ideal flag; a rate CAP scales BOTH
pre-exponentials by one factor; a template that moves a hydrogen ATOM must
collapse explicit Hs; a declared catalyst is a CONSTANT OF THE MOTION; the
tolerance audit's THREE self-check examples come out byte-identical;
`COVERAGE_REPORT.md` and both `derived/*.psv` come out byte-identical across
`PYTHONHASHSEED` values; the `mineral` tier is a FALLBACK consulted only after all
three providers refuse; a dot-separated SMILES is a MIXTURE and is refused; a
lattice may REACT and may never DISSOLVE, BOIL or MELT (⚠ S10 moved ZINC out of
the lattice table, which is a statement about one ENTRY; the rule is untouched);
`_CURATED_SOURCE.get(smi, _NIST)` is exactly the old shared stamp for all nine
pre-S10 Antoine rows; a curated liquid Cp must be POSITIVE across the species'
whole liquid range; **the two hydroformylation templates share one `A`, so the
n:iso ratio IS `exp(dEa/RT)` and a test says so**; **`alpha` is 0.0 on both,
because Evans-Polanyi would name the wrong major product**; **`wacker_oxidation`
keeps order 1 in oxygen because the kernel has no availability gate**; and **the
measured physical table overrides a working Joback record ONLY where
`DELIBERATE_OVERRIDES` names it and says what it cost.**

We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M8, M12, S1–S13 are DONE.**

# ⚠ THE BASELINE IS MEASURED. DO NOT START WITH THE SUITE.

**S13 RAN THE WHOLE SUITE AT THE END AND MEASURED 965 PASSED / 0 FAILED IN 21:36.**
Take that number and spend the time on content. ⚠ **It was run AFTER every
`src/` edit** — fourth session running that is true. (961 at S12; the +4 are
S13's own new tests.) ⚠ The 21:36 against S12's 13:20 is CONTENTION, not the
suite getting slower: S13 ran examples in another process at the same time.

⚠⚠ **S13 REGENERATED A DATA TABLE — `physical_data.py` WENT FROM 37 SPECIES TO
1239 — SO `tolerance_audit.py` WAS RE-RUN AND ITS RESULT HAS CHANGED.** Read the
three warnings below before comparing any number to a pre-S13 one.

```bash
python validation/boiling_points.py            # ⚠⚠ S13's standing audit, 2 s. NEW, and READ PANEL 2
python validation/skraup.py                    # S12's, ~10 s
python validation/smelting.py                  # S9's, ~1 min
python validation/hydroformylation.py          # S11's, ~1 min
python validation/wacker.py                    # S11's other one, ~1 min
python validation/gas_processes.py             # S7's, ~1 min
python validation/corpus_balance.py            # S7's other one, ~20 s. READ IT before picking
python validation/catalog_coverage.py          # ⚠ READ THE 'BOTH' LINE: 31/173, ~15 s
python validation/physical_estimation.py       # ⚠ S13 took its panel 3 from n~20 to n=254
python validation/game_gates.py                # the element floor's cross-check, seconds
python tools/build_route_index.py              # the artefact nothing reads
python validation/cell_potentials.py           # M8's standing audit, seconds
python validation/rate_ceiling.py              # M12's, seconds
python validation/jacobian_bound.py            # S5's standing audit, ~1 min
python -m ruff check src tests examples validation tools
python -m pytest -q                            # ~14–21 min. ONLY after touching src/
python validation/tolerance_audit.py           # ~10 min. After touching the RHS **or any data table**
```

⚠ **THE SUITE AND THE TOLERANCE AUDIT ARE MINUTES OF SATURATED CPU ON THE USER'S
OWN MACHINE.** Say what a long run will cost before starting one, and ask.
`examples/plate_column.py` alone is 12 minutes.

---

# ⚠⚠⚠ THREE THINGS S13 CHANGED THAT INVALIDATE OLD NUMBERS

**1. EVERY EXAMPLE'S VOLATILITY MOVED.** The measured-physical table went from 37
species to 1239, so **any number you are comparing against a pre-S13 one is
stale unless S13 quoted it**. Five examples came out IDENTICAL (`esterification`,
`lime_cycle`, `roasting_and_the_catalyst_gate`, `mercury_retort`,
`oil_of_vitriol`); the rest moved and MILESTONES §S13 ¶7 has the table.
⚠ `plate_column`'s heart cut is **0.8548**, not 0.8544. M2's target still MET.

**2. THE COVERAGE REPORT'S TIER COUNTS ARE NOT COMPARABLE TO ANY PRE-S13 ONES.**
`catalog_coverage`'s two tier classifiers were matching substrings against a
COMPOSITE provenance string and both were wrong — one overstated measured
formation halves, the other invented a "Benson physical half" tier that does not
exist. Fixed, and it moved counts that S13 did not otherwise touch (measured
formation 144 → **135**, mineral 29 → **25**, ion 61 → **64**).

**3. `tolerance_audit.py` HAS A `KNOWN_REFUSAL` ENTRY AGAIN**, and two examples
now print a tolerance-dependent digit where S11 found none. All three are
diagnosed in the file. ⚠ **None of the three is a regression** — read the
diagnosis before acting on any of them.

---

# ⚠⚠ START HERE: THE ENGINE AND HONESTY QUEUE

⚠⚠ **S13 TOOK ITEM 1, WHICH HAD BEEN THE LIST'S LARGEST ITEM FOR THREE SESSIONS.**
What is below is renumbered. **Items 1 and 2 are the two it created.**

1. **⚠⚠ THE PSRK OVERFLOW IS NO LONGER "MEASURED INERT" — NEW IN S13, AND IT IS
   THE CHEAPEST REAL ITEM ON THIS LIST.**
   `activity.activity_coefficients` overflows `np.exp(-a / T)` for the PSRK
   quadratic **below 4.28 K**, and has been carried for several sessions as
   "PRE-EXISTING, measured inert". **`plate_column` now prints five
   `RuntimeWarning` lines where it printed none**, so something in that
   fourteen-vessel rig is evaluating an activity coefficient below 4.28 K.

   ⚠ **MEASURED HARMLESS WHERE IT FIRES**: heart 0.8548 against 0.8544, target
   met, replay determinism still exact at 0.000e+00 mol on all three receivers.
   **The word to change is "inert", not the number.**

   ⚠ **WHAT IS NOT KNOWN IS *WHERE*.** The overflow threshold was measured
   exactly (`max(-a/T) = 760` at T=4, `292` at T=10, so it fires below ~4.28 K
   and nowhere above), but nothing has found which call passes a T that low.
   **Find the call before designing anything** — a `np.errstate(over="raise")`
   context around the residual term, with the state printed, is the whole probe.
   Worth ZERO routes; take it for the honesty.

2. **⚠⚠ `multistep_prep` PRINTS `pH = inf`, AND IT IS PRE-EXISTING.**
   At the default tolerance the benzoate flask reports **`pH = inf`**; at rtol
   1e-8 it reports **11.65**. The `inf` is in the pre-S13 run too — what S13
   changed is that the tolerance audit can now SEE it, because the tight run
   resolves it.

   ⚠ **A READOUT THAT REPORTS INFINITY IS NOT AN ACCURACY PROBLEM**, and it is
   the same mechanism as the Skraup's "exactly zero": a hydronium column the
   loose solver clamps to a literal 0.0, and `-log10(0)` is `inf`. **S13 fixed
   the Skraup's claim and not this one.** The fix is probably a floor on the pH
   READOUT (the shape `is_boiling` just got), but **measure the hydronium
   trajectory first** — if the column is genuinely reaching zero from a state
   where it should not, that is a different bug.

3. **⚠⚠ NOTHING IN `build_phase_arrays` COMPARES T TO Tc. UNCHANGED BY S13, AND
   S13 MAKES IT MORE LIKELY TO BITE, NOT LESS.**
   A species is `condensable` or not, and that flag is a property of the SPECIES
   rather than of the state. A CONDENSABLE species above its critical temperature
   still dissolves by Raoult's law against an Antoine curve extrapolated past its
   own domain.

   Measured: a Wacker flask at 400 K charged with 0.20 mol of ethylene over
   20 mol of water **dissolves 0.165958 of it — 83%, against a real ~2%** —
   because Psat reads **219.9 bar** off a curated Antoine **118 K above
   ethylene's critical temperature of 282.35 K.**

   ⚠⚠ **A MEASURED BOILING POINT DOES NOT FIX IT** — S11 predicted it would and
   measured that it does not (0.16588 → 0.16596, four figures unchanged),
   because ethylene's vapour pressure comes from `volatility._CURATED_ANTOINE`
   and **Tb does not feed that curve at all**. ⚠ **S13 CONFIRMS THIS IS STILL
   TRUE** — `validation/wacker.py` panel 4 is unchanged after the sweep.

   ⚠ **BUT S13 PUT 869 MORE SPECIES ON A FITTED ANTOINE CURVE** (889 condensable records against 20), each with a
   fit window bracketing its own Tb, and nothing checks whether the flask is
   above Tc when it evaluates one. The exposure grew even though the measured
   example did not move. Worth ZERO routes; take it for the honesty.

4. **⚠⚠ A METAL THAT BOILS OUT OF THE SOLID BLOCK — STILL OPEN, AND STILL THE
   BEST-SCOPED ENGINE ITEM.** Unchanged by S11, S12 and S13.

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
   best cross-check cannot be run at all — **ONE check, not four.**

   ⚠ **WORTH ZERO ROUTES for iron.** ⚠⚠ **BUT MEASURE `direct-combination`
   FIRST: it is worth +1 AND it is refused by the SAME `build_surface_arrays`
   non-lattice check.** Hold that as a HYPOTHESIS — `Hg(l) + S8(s)` is not a gas
   attacking a crystal, so `SurfaceArrays`' form (extensive in the solid,
   INTENSIVE in the gas) may be wrong for it whatever the mask says.

5. **⚠⚠ THE 250–450 K FIT WINDOW — AND S13 DID NOT TOUCH IT, THOUGH IT LOOKS AS
   IF IT SHOULD HAVE.** `CondensedProvider.get(mol, T_lo=250.0, T_hi=450.0)` is
   an organic-solvent window and **every caller in the repo takes the default**.
   Swept in S11 over each species' OWN Tm→Tb at 21 points: **99 compounds return
   a negative liquid Cp inside their own liquid range** (worst carminic acid at
   **−21482 J/(mol K)**) and **38 more swing over 5x**.

   ⚠⚠ **AND S13 MAKES THIS ITEM MORE URGENT AND ALSO EASIER.** S11's finding was
   that ethylene moved from **+1574 to −1782 J/(mol K)** when it gained a
   MEASURED Tc — *a correlation extrapolated outside its domain does not get
   safer when its inputs get better*. **S13 just gave 876 more species measured
   Tb/Tc.** ⚠⚠ **NOBODY HAS RE-SWEPT THE 99 SINCE.** The count is a pre-S13
   number and **the first thing this item needs is to measure it again** — it
   could be smaller, and it could be larger, and S11's ethylene result says do
   not assume which.

   * ⚠ **A negative Cp is not an accuracy problem: adding heat LOWERS the
     temperature.** S10 measured it reachable — 3.96 mol of liquid mercury gave a
     NEGATIVE TOTAL thermal mass.
   * ⚠⚠ **DO NOT JUST WIDEN THE WINDOW.** Many of the 99 have a JOBACK Tm/Tb that
     is itself meaningless (carminic acid "melts" at 1398 K and really
     decomposes). **Separate the wrong output from the wrong input first** — and
     S13 has now fixed a large part of the wrong INPUT, which is exactly why the
     re-sweep comes first.
   ⚠ Worth ZERO routes. Measured inert on every example as of S11.

6. **⚠ `slagging` — RE-PRICED IN S11 AND IT WAS PRICED TOO CHEAPLY.**
   * **`silicon-dioxide`** is fully available — CRC Hfs −910700, Gfs −856300,
     S0s 41.5, Cps 44.4. ✔
   * **`calcium-silicate` has NO thermochemical data under ANY of its three CAS
     numbers** (10101-39-0, 1344-95-2, 13983-17-0). ✘ **Not a curation job.**
   * **`iron-ii-oxide`**'s CRC standard row has **`Cps = NaN`**.
   **`blast-furnace` is blocked TWICE over, on SOURCES rather than on work.**
   ⚠ **S13 DID NOT CHANGE THIS**: its sweep reads `chemicals`' Tb/Tm/Hfus/Tc/Pc
   tables, not the solid-basis thermochemistry `mineral_data` needs.

7. **⚠ THE CIS/TRANS BLIND SPOT — A REAL DATA JOB WITH A REAL TRAP.** Benson (the
   RMG group set) has no cis correction, so oleic and elaidic acid come back with
   IDENTICAL Hf and Gf and the engine reports a confident 50:50 for a real ~5:1.
   ⚠ **The data exists and is not usable as it stands:** WEBBOOK has both liquid
   enthalpies, −764.8 and −769.0 kJ/mol, and that 4.2 kJ/mol gap agrees with
   Benson's own historical cis NNI term of 4.18 to 0.4% — **two independent
   sources**. But neither has an S0, so no Gf can be derived, and grafting
   Benson's original correction onto RMG-fitted group values **mixes two bases**.
   ⚠ Worth ZERO routes today. `test_the_cis_trans_pair_prices_at_exactly_zero`
   pins the limit. ⚠ **S13 gave both acids a measured PHYSICAL half and changed
   nothing about this** — the blind spot is in the FORMATION half.

8. **⚠ THE CURRENT BUDGET — M8's OWN NAMED GAP, AND IT IS A LAYER 4 TERM.** Two
   electrode reactions in one cell divide nothing, so both run at full rate and
   activation selectivity washes out: k(brine)/k(water) is **4.76e+17 at 2.5 V,
   5.94 at 3.0, 1.00 at 4.0**. ⚠ Worth **ZERO new routes**.

9. **Pyrite** — one mineral entry from `pyrite-roasting` running, +1 on the
   intersection. ⚠ **RE-QUERIED IN S11 AND THE REFUSAL STANDS**: `Hfs` in
   WEBBOOK, `S0s` in **nothing**. This needs a SOURCE and not a workaround.

10. **⚠⚠ THE BURNER — ~50 s at rtol 1e-8 against 0.8 s at the default.** S5
    bounded the CRASH and explicitly did not bound the THRASHING. BDF is
    struggling with a liquid layer holding **1e-29 mol**, which `LAYER_REABSORB`
    drains toward zero without ever reaching it. **The question nobody has asked
    is whether a layer below `LAYER_EPS` should be *merged discretely* at a step
    boundary rather than drained continuously for ever.** ⚠ `merge_phases`
    already does exactly that at the `run` boundary. **Measure the layer-2
    inventory over the failing run before designing anything.**
    ⚠ **S13 measured `oil_of_vitriol` OUTPUT IDENTICAL across the sweep**, so
    nothing here moved.

11. **THE CORPUS BALANCE BACKLOG — 75 ROWS, AND IT IS NOT A TO-DO LIST.** S7 built
    the check and deliberately fixed nothing, on the `diels-alder-route`
    precedent. ⚠ But **17 of the 75 are `spurious`** and those are the cheapest
    to correct. ⚠ `tools/catalog.py`'s `validate` still does NOT check balance,
    so the corpus can grow another one silently.

12. **⚠ `hydrolysis`** — it unlocks **exactly ONE route alone,
    `vitriol-distillation`**, and that route's step 1 reads `-> iron-ii-OXIDE`
    while the engine makes HEMATITE. ⚠ **That is item 6's mineral again.**

13. **M7 (⚠ M12 took most of its case away; re-scope)**, **M9 (polymers, 12
    routes)**, **M10 (the site balance S1 did not build, 8 routes)**,
    **⚠⚠ M11 — RE-COST IT BEFORE SCHEDULING.** Its costed starting point was
    *"10 species that need ONE measured boiling point each"*; **S13 closed eight
    of them and the bucket now counts 2** (`performic-acid`, `phenyl-radical`,
    neither of which has a non-estimated Tb under either key). What is left of
    M11 is the FORMATION half — 267 species with no group value in any published
    tabulation — which is a different problem with a different answer.

14. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
    the *deposition-needs-a-seed* half into a real bound in
    `SolidStateArrays.units`. What is still not expressible is a solid appearing
    from NO solid — `hydride-thermal-deposition` is still a mechanism gap.

---

# THE COVERAGE QUEUE — **THE TOP THREE ROWS ARE GONE AND WHAT IS LEFT IS ALL REFUSALS OR ENGINE WORK**

S11 took `hydroformylation` and `wacker-oxidation`; **S12 took `skraup-cyclisation`,
which that table called the queue's best remaining row. S13 took nothing off this
table at all** — it went to the engine/honesty queue instead, and the queue above
is still where the value is. ⚠⚠ **What is left here is NOT a work queue.** Five of the seven rows below are recorded REFUSALS or engine
prerequisites, and the two that are neither are the hardest kind of content work.
**Read the row, not the rank, and say which mechanic you are picking for — or
pick off the ENGINE queue above instead, which is where the value now is.**

| class | its route | worth | what it is |
|---|---|---:|---|
| ~~**`skraup-cyclisation`**~~ | `skraup-route` | ✔ **DONE IN S12, +1** | 7 reactant slots and 9 product slots. See MILESTONES §S12 — and read its §2 before pricing ANY liquid-phase template by hand |
| `fischer-tropsch` | `fischer-tropsch` | +1 | `8 CO + 17 H2 -> octane + 8 H2O`, **25 slots**. Claus proves 24 works and Skraup proves the pattern generalises — but read M8 §6 on the lump that was refused. ⚠ **This is now the queue's best CONTENT row**, and its mechanic is chain growth as a lump, which is M9's problem wearing a template |
| `molten-salt-electrolysis` | `downs-cell` | +1 | ⚠ **A MELT is not a phase this project has** — M8's own named leftover, and it is ENGINE work, not content |
| `catalytic-air-oxidation` | `p-xylene-oxidation` | +1 | ⚠⚠ **M5 REFUSED THIS CLASS** — its four rows are at least three mechanisms. **Split it before crediting it**, and only one of the four rows is runnable |
| `direct-combination` | `vermilion-route` | +1 | ⚠⚠ **S9 MEASURED AND REFUSED IT**, and engine queue item 4 is the only thing that could change that. **Do not re-derive this** |
| ~~**`oxidative-cleavage`**~~ | `vanillin-lignin` | ⚠⚠ **S11 MEASURED IT AND REFUSED IT** | The row is `coniferyl alcohol + O2 -> vanillin + water` and **it cannot be that reaction**: a C10 monolignol makes one C8 vanillin and a C2 fragment the row does not name. It balances at **8 C10H12O3 + 7 O2 -> 10 C8H8O3 + 8 H2O** — eight aromatic rings in and TEN out. ⚠ **Do not re-derive this**; the audit prints it |
| `fermentation` | `abe-fermentation`, `msg-route` | +1 | ⚠ **M5 REFUSED IT** as a metabolic NETWORK rather than a transformation. That refusal still stands |
| `separation` | `coal-tar-distillation` | +1 | ⚠ **M5 REFUSED IT**: a distillation is not a reaction class, and the feedstock has no graph |

⚠⚠ **AND READ `corpus_balance.py`'s LAST PANEL BEFORE PICKING ANY OF THEM.** S11
added it: **the balance audit's test is a WEAK one.** It asks whether ANY positive
coefficient vector conserves the elements, and element conservation does not
forbid rearranging carbon skeletons — so a row can PASS and still not be the
reaction it is written as. `vanillin-lignin` is the standing example and it cost
S11 a template. **A pass there is not permission to write a SMARTS.**
⚠⚠ **AND S12 IS THE CONVERSE AND IS EQUALLY IMPORTANT**: `skraup-route` step 2
looked like the `spurious` pattern, passed the balance check, and was REAL. The
audit prints both rows side by side now. **The check cannot decide either way;
only reading the chemistry can.**

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

MILESTONES.md — the plan. ⚠ **§S12, §S11, §S10, §S9, §S8, §S7, §M8, §S1, §S3, §S4, §S5 and
  §S6 are the ones to read**: **S12 found that its own source comment had priced
  its own reaction on the WRONG STANDARD STATE — the same reaction is dS +36.65
  as an ideal gas and dS −329.08 as a liquid, and the argument built on the sign
  was about a basis the template does not use**; S11 found that a species is estimated because
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
  95 is S10, 96 is S11, 97 is S12, **98 is S13**.**
NEXT_SESSION.md — the invariants table at the bottom is the contract, and S7, S8,
  S9, S10, S11 and S12 each added a block to it. ⚠⚠ **S10 WITHDREW a row** and S11
  added **two more LIMITS TO REMOVE rather than invariants to keep** (the
  Wacker's oxygen order; ethylene's solubility). ⚠ Read the two warnings above it
  before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including S9's two splits,
  S7's of `combustion`, M8's of `electrolysis`, S3's of `thermal-decomposition`
  and S4's decision NOT to un-split `roasting-to-metal`; plus
  `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-skraup-standard-state,
  chemsim-competing-templates, chemsim-physical-data-sourcing,
  chemsim-vaporising-metal, chemsim-declared-rate-orders,
  chemsim-catalysis-and-bounds, chemsim-coverage-catalog, chemsim-corpus-balance
  and chemsim-generated-artefacts.

⚠⚠ **AND READ MILESTONES §S13 BEFORE QUOTING ANY NUMBER OUT OF AN EXAMPLE.**
S13 regenerated `physical_data.py` from 37 hand-typed species to 1239 generated
ones, so every example's volatility and energy balance moved. Five came out
IDENTICAL and §S13 ¶7 has the table for the rest.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 46 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, a catalyst you have to actually put in
the flask, a route that nothing declares, a Jacobian that cannot be probed outside
its own state, a dial that decomposes things in the order their chemistry says
they should, four inorganic gas processes whose whole behaviour is their
reversibility, three smelters that take ore, coke and air to metal, a retort that
DISTILS its metal off, **two templates that RACE for one alkene and hand back a
selectivity nobody typed**, **a catalyst that only exists if there is water to
dissolve it in**, and **a ring closure whose OXIDANT turns into one of its own
reagents and goes round again**. `SAVE_VERSION` is **5**.
Coverage: **51/229 classes**, **46 templates**, **41/173 template-ready**,
**80/173 species-ready** — and ⚠⚠ **31/173 BOTH, which is the only one of the
three a route can be judged on.**
⚠ The corpus's **PHYSICAL half is measured for 652/1583 (41.2%)** as of S13,
against 40 (2.5%) before; Joback fell from 964 (61%) to 333 (21%).

---

# ⚠⚠ WHAT S13 TURNED OUT TO BE: 37 HAND-TYPED SPECIES BECAME 1239 GENERATED ONES, AND THE INSTRUMENT WAS WRONG FIRST

**+0 class, +0 template-ready, +3 species-ready, +0 RUNNABLE — all four
predicted before the audit ran.** A DATA milestone cannot add a template, so it
cannot add a class or move the BOTH column. What it moves is whether the numbers
the engine already reports are RIGHT.

| | before | after |
|---|---:|---:|
| species in `MEASURED_PHYSICAL` | 37 | **1239** |
| ...with a measured boiling point | 20 | **896** |
| corpus PHYSICAL half measured | 40 / 1583 (2.5%) | **652 / 1583 (41.2%)** |
| corpus physical half Joback | 964 (60.9%) | **333 (21.0%)** |
| routes species-ready | 77 / 173 | **80 / 173** |
| ⚠⚠ **routes BOTH — the one to quote** | **31** | **31** |

## ⚠⚠⚠ 1. THE LARGEST FINDING IS ABOUT S13's OWN INSTRUMENT, AND IT USED S11's FIX AS THE REASON

S11 recorded a trap: `CAS_from_any("C")` returns **CARBON**, because a bare
SMILES is read as a FORMULA. Its recorded fix was **"always use `smiles=`"**.

S13 built `validation/boiling_points.py` on exactly that fix, measured the gap at
**322 species**, wrote the number into a commit message, and generated a table.
**The table had no aniline in it. No nitrobenzene, no quinoline.**

    CAS_from_any("smiles=Nc1ccccc1")  -> "recognized, but it is not in the database."
    CAS_from_any("aniline")           -> 62-53-3, Tb 457.15 K

Measured: of **1069** corpus species with no graph-resolved CAS, **874 resolve by
NAME with a matching formula and 508 of those carry a measured boiling point.**
The gap is **830, not 322** — the instrument undercounted by 60%, and it did so by
faithfully applying the previous session's fix.

⚠⚠ **THE FIX FOR ONE TRAP BECAME THE NEXT TRAP.** Both keys now, graph first,
formula cross-check as arbiter — and it earns its place: **it refuses 72 name
matches outright**.

## ⚠⚠ 2. THE GAP WAS NOT EXOTIC. IT WAS THE SOLVENT IN THE FLASK

All priced by JOBACK, in a project whose flagship rig is a distillation column:
**acetylene 216.60 against 189.00 (+14.60%), methanol 314.66 against 337.63
(−6.80%, 23 K), ethanol 337.54 against 351.57 (−3.99%, 14 K)**, diethyl ether,
n-hexane. Over the whole table **881 estimates replaced, mean 6.10%, worst
110.94%, 437 over 2% and 68 over 20%.** ⚠ The error was UNSIGNED and UNBOUNDED —
nothing knew which was the 3% one and which the 85% one, **because all of them
RESOLVED**.

## ⚠⚠ 3. A COUNT OF ABSENT SPECIES IS NOT A COUNT OF WRONG ONES

322 were absent from `MEASURED_PHYSICAL`; only **213** would have changed the
resolved record. Water, O2 and HCl are all "absent" and all irrelevant —
`_CURATED_RAW` short-circuits them. `boiling_points.would_move` resolves every
candidate **twice, through two providers**, rather than arguing about tiers.

## ⚠⚠ 4. THE COVERAGE AUDIT WAS READING A TIER OUT OF PROSE, AND `thermochemistry` HAD ALREADY SAID WHY THAT FAILS

Its `physical_source` field carries: *"deducing it by matching on the prefix of a
composite string is the kind of guess that goes quietly wrong the first time the
wording changes."* `_thermo_tier` was handed the WHOLE `source`, which names both
halves, and said `measured` if "experimental" appeared anywhere — **669 measured
FORMATION halves where the answer is 135**, from a change that touched no
formation data. Its twin's bare `return "benson"` default reported **659 Benson
PHYSICAL halves**, of which there is no such thing.

⚠ **A DEFAULT AT THE BOTTOM OF A MATCHER IS A GUESS.** Both split on structure
now, take `physical_source` as the FIELD it is, and **raise** on an unrecognised
provenance. ⚠ The fix found a pre-existing overcount (144 → 135) and needed a
new `compilation` tier for 47 YAWS/WIKIDATA values.

## ⚠⚠ 5. A FIT WINDOW THAT COULD EXCLUDE THE BOILING POINT IT WAS BRACKETING

`volatility.py` fitted over `max(0.30*Tc, Tb-120, 150.0)`, so methane's window
opened **38 K ABOVE its own Tb**: **+16.50%** at the normal boiling point, nitric
oxide **+14.53%**. ⚠ **PRE-EXISTING AND INVISIBLE** — the check that exists for
exactly this walked `MEASURED_PHYSICAL` and both are in `_CURATED_RAW`. One line.

## ⚠ 6. WHAT IT COST, MEASURED BY RUNNING ALL FIFTEEN EXAMPLES

`esterification`, `lime_cycle`, `roasting_and_the_catalyst_gate`,
`mercury_retort`, `oil_of_vitriol` **IDENTICAL**. Worst movers: `multistep_prep`
yield **84.0% → 82.7%**, `fractional_distillation` 11.8%, `workshop` 8.7%,
`wait_until` **the boil at 1353 s → 1418 s**, `vessel` structurally (still
boiling where it had gone dry). ⚠⚠ **`plate_column`'s HEART is 0.8548 against
0.8544 — M2's target still MET**, replay determinism still exact.

⚠⚠ **`named_routes` LOST FOUR `MIXES STANDARD STATES` WARNINGS AND GAINED A
BARRIER GUARD.** The engine had been saying *"do not read this reaction's
equilibrium constant"* about DDT isomers, dinitrotoluenes and the stearic/oleic
pair; they have a liquid standard-state shift now. And `ester_hydrolysis`'s
declared Ea of 70 kJ/mol is below aspirin hydrolysis's dH of 75.6, so a guard
that was already there raised it — `aspirin-impurity` reports **59.2% where it
reported 99.8%**. Nobody changed a barrier.

## ⚠⚠ 7. AND THE TOLERANCE AUDIT'S "CANNOT BE SWEPT" WAS NOT A REGRESSION

`named_routes` raises at rtol 1e-8 now. Measured on both data bases:

    basis            default (1e-6)   rtol 1e-7   rtol 1e-8
    pre-S13 Joback   1.000000 mol     RAISES      1.000000 mol
    S13 measured     1.000000 mol     RAISES      RAISES

⚠⚠ **A ONE-POINT TOLERANCE SWEEP CANNOT TELL "NEWLY BROKEN" FROM "ALREADY BROKEN
AT A POINT IT DOES NOT SAMPLE."** The fragility was one decade CLOSER to the
default than this audit tests, before S13. In `KNOWN_REFUSAL` with the numbers.

## ⚠ 8. FIVE TESTS MOVED AND EACH ONE WAS A FINDING

* S12's *"a flask with no acid makes exactly zero"* was **one word too strong**.
  Water autoprotolyses; the flask holds ~4e-29 mol of hydronium and makes
  ~2.4e-25 mol of quinoline in ten hours, flat thereafter. The literal `0.0` was
  the solver clamping a column that never left the floor.
* A documented `temperature_steady` trap **went below the default tolerance**.
  Ethanol's Joback Tb made the flask ~2x too volatile at 298 K, so the opening
  swing was **−24 K/s**; it is **−1.42 K/s** now, and BDF at the default no
  longer resolves it. ⚠ `max_step` does NOT recover it; **rtol 1e-9 does**.
* `is_boiling` read a flask integrated to its own boiling point as **NOT
  boiling** — **−1.110e-15 bar** below ambient. A root is zero to solver
  precision. The readout gained a 1e-12 relative floor.
* The provenance test's own illustration turned inside out: **no catalog species
  has a measured formation half on a Joback physical one any more.**
* Benzoic acid's molar volume got **worse** — 96 → 87.4 mL/mol against a real
  ~96.5 — because a measured Tb brings a FEDORS Vc (326.43) where Joback's
  (343.50) was closer to the literature's ~341. **Taken anyway and written
  down**: a record may not mix two group-contribution methods.

## 9. THE SMALL THINGS

* `validation/boiling_points.py` is a new standing audit, **2 seconds**, written
  to stay useful once the gap is closed: panel 2 measures what the CORRECTION was
  worth through `ThermochemistryProvider(measured_physical=False)`.
* `physical_estimation.py` panel 3 — the one INDEPENDENT check in the chain —
  went from n≈20 to **n=254**, and the design held: measured Tc/Pc mean
  |Δω| **0.029**, Wilson-Jasperson **0.121**.
* **It closed eight tenths of M11 as a side effect**: the "needs only a boiling
  point" bucket went **10 → 2**. ⚠⚠ RE-COST M11 before scheduling it.
* `COVERAGE_REPORT.md` and both `derived/*.psv` byte-identical across
  `PYTHONHASHSEED`. `critical_data.py` byte-identical.
* ⚠ **A `⚠` inside a `print()` DID ship** in the first draft and was caught
  before the first run. Twenty-seven sessions.

---

# ⚠ THE FRAGILITIES

**1. ✔✔ CLOSED IN S13 — THE HAND-TYPED LIST.** `MEASURED_PHYSICAL` is generated
from `data/catalog` now: 37 species → **1239**, 20 measured boiling points →
**896**, corpus physical half measured 2.5% → **41.2%**. ⚠ What replaced it as a
fragility is item 15 below, and it is smaller.

**2. ⚠⚠ NOTHING COMPARES T TO Tc (S11).** A condensable species above its critical
temperature still dissolves by Raoult's law against an extrapolated Antoine curve.
Ethylene is ~40x too soluble in the Wacker liquor. Engine queue item 3.
**A LIMIT to remove, not an invariant.** ⚠ **S13 put 869 more species on a fitted
Antoine curve and did NOT add a Tc check**, so the exposure grew even though the
measured example did not move.

**3. ⚠⚠ THE WACKER'S OXYGEN ORDER IS FIRST AND SHOULD BE ZERO (S11).** The kernel
has no availability gate. Measured at 1.00 / 1.92 / 3.53 / 5.85x.
**A LIMIT to remove, not an invariant.**

**4. ⚠⚠ A LATTICE MAY REACT AND MAY NEVER BOIL — HALF CLOSED BY S10.** What
remains is thermite: nothing caps the temperature, and iron cannot make zinc's
move. **Engine queue item 4**, worth ZERO routes.

**5. ⚠⚠ THE BURNER IS STILL ~50 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT.** The
crash is bounded; the thrashing is not. **Engine queue item 10.** ⚠ S13 measured
`oil_of_vitriol` OUTPUT IDENTICAL across its whole sweep, so nothing here moved.

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
a MEASURED Tc** — better data, same window, worse number. **Engine queue item 5.**

**15. ⚠ NUCLEATION, HALF modelled.** A solid can only grow where one already is.

**16. ⚠⚠ THERE IS NO REFLUX HEAD (S12).** Nothing returns a vapour to the pot,
so a reaction at reflux must be modelled as a SEALED flask -- and that buys a
real pressure (13.7 bar for the Skraup at 450 K). ⚠ Measured cost of getting it
wrong: an OPEN Skraup flask loses **98% of its yield** because acrolein boils at
314 K. **Reported, and the audit prints the pressure rather than hiding it.**

**17. ⚠ LIQUID MERCURY IS 99.85% HELD IDEAL.**

**18. ⚠ THE FLAT COLUMN IS STILL FLAT, AND THAT IS CORRECT.**

**19. ⚠ THE ELEMENT FLOOR'S SOLID HALF IS CURATED AND ITS GAS HALF IS STILL
REFUSED.** 33 compounds remain refused as bare elements and none blocks a route.

**20. ⚠ `iron-ii-oxide`, `pyrite` AND `calcium-silicate` ARE ALL SOURCE-BLOCKED,
RE-QUERIED IN S11.** FeO has no crystal Cp in CRC; pyrite has `Hfs` in WEBBOOK and
`S0s` in nothing; **calcium silicate has nothing at all under any of its three CAS
numbers.** All three refusals follow rules worth keeping.

**21. ⚠⚠ THE PSRK OVERFLOW IS NO LONGER "MEASURED INERT" (S13).**
`psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows below
**4.28 K** (measured exactly: `max(-a/T)` is 760 at T=4 and 292 at T=10).
`plate_column` now prints **five `RuntimeWarning` lines where it printed none**.
⚠ **Measured HARMLESS where it fires** — heart 0.8548 vs 0.8544, target met,
replay exact. **The word to change is "inert", not the number.** Nothing has yet
found WHICH call passes a T that low. **Engine queue item 1.**

**22. ⚠⚠ `multistep_prep` PRINTS `pH = inf` (pre-existing, newly VISIBLE in S13).**
At the default tolerance the benzoate flask reports `pH = inf`; at rtol 1e-8,
11.65. Same mechanism as the Skraup's "exactly zero": a hydronium column the
loose solver clamps to a literal 0.0. **Engine queue item 2.**

**23. ⚠ `named_routes` CANNOT BE SWEPT at rtol 1e-8 (S13) — AND IT IS NOT NEW.**
The PRE-S13 data raises too, at **rtol 1e-7**, one decade closer to the default
than the audit samples. Diagnosed in `KNOWN_REFUSAL`; the default-tolerance
answer is confirmed on both bases.

**24. ⚠ THE 31 SPECIES THAT MISS THE BOILS-AT-1-ATM BAR (S13).** 858 of 889 clear
1.5%; the 31 that do not are NAMED in `BOILS_LOOSELY` with their residuals, and
**eight are pre-existing** — water +2.57%, SO2, SO3, HF, formaldehyde, nitric
acid, the nitrite pair, and zinc. Nearly all are polar or associating and boil
between 250 and 375 K. ⚠⚠ **Zinc is S10's own −0.96% in TEMPERATURE read as
+12.61% in PRESSURE**; a bar in one is not a bar in the other.

**25. ⚠ BENZOIC ACID'S MOLAR VOLUME GOT WORSE IN S13** — 96 → 87.4 mL/mol against
a real ~96.5 — because a measured Tb brings a FEDORS Vc (326.43) where Joback's
(343.50) was closer to the literature's ~341. Taken deliberately: a record may not
mix two group-contribution methods, and Fedors' 7.7% mean error is MEASURED.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Twenty-two times now. ⚠ **AND THE SOLVER IS PART OF THE ARITHMETIC**
(M8).
⚠⚠ **A GENERATED FILE IS ONLY AS SYSTEMATIC AS ITS INPUT LIST.** S11 found it,
S13 closed it: `physical_data.py` was generated from 37 hand-typed names, so 830
corpus species with a measured boiling point fell to Joback. **The file looked
generated from the outside and was a transcription on the inside**, and nothing
could see the difference **because a Joback record RESOLVES** — it answers every
question put to it, confidently, in the wrong place.
⚠⚠⚠ **AND THE FIX FOR ONE TRAP CAN BE THE NEXT TRAP. S13's OWN INSTRUMENT WAS
WRONG FIRST, AND IT WAS WRONG BY OBEYING S11.** S11 recorded "a bare SMILES is
read as a FORMULA — always use `smiles=`". S13 did, and generated a table with no
aniline, no nitrobenzene and no quinoline in it: **`chemicals`' SMILES index does
not contain them**, while `CAS_from_any("aniline")` answers instantly. It reported
the gap as 322 where it is 830. **NEITHER KEY ALONE IS ENOUGH** — graph first,
then the NAME, with the formula cross-check as the arbiter (it refuses 72).
⚠⚠ **A COUNT OF THINGS THAT ARE MISSING IS NOT A COUNT OF THINGS THAT ARE WRONG.**
322 species were absent from the measured table and only **213** would have
changed a resolved record; water, oxygen and hydrogen chloride are "absent" and
irrelevant, because a higher tier short-circuits them. **Resolve it twice through
two providers rather than arguing about tiers.**
⚠⚠ **A TIER READ OUT OF PROSE GOES WRONG THE MOMENT THE WORDING CHANGES — AND
THE FIELD THAT EXISTS TO PREVENT THAT MAY ALREADY SAY SO.**
`catalog_coverage._thermo_tier` matched substrings against a COMPOSITE provenance
string naming both halves of a record, and after S13's sweep reported **669
measured FORMATION halves where the answer is 135**, from a change that touched no
formation data. `ThermoData.physical_source` had carried a comment predicting
exactly this since the day it was added. ⚠ **AND A DEFAULT AT THE BOTTOM OF A
MATCHER IS A GUESS**: its twin's bare `return "benson"` invented 659 "Benson
physical halves", a tier this engine does not have.
⚠⚠ **A BAR MEASURED OVER NINE SPECIES IS A BAR MEASURED OVER NINE SPECIES.** The
boils-at-1-atm check held 20 records to 1.5%; pointed at all three tables that
carry a Tb it holds **889**, and 8 of the 31 that miss are PRE-EXISTING and were
invisible because the check walked the wrong list.
⚠⚠ **A BAR IN TEMPERATURE AND A BAR IN PRESSURE ARE NOT THE SAME BAR.** Zinc's
curated curve is **−0.96% in T** (S10's own recorded number) and **+12.61% in P**
at the same point. Quoting one against the other manufactures a regression.
⚠⚠ **A ONE-POINT TOLERANCE SWEEP CANNOT TELL "NEWLY BROKEN" FROM "ALREADY BROKEN
AT A POINT IT DOES NOT SAMPLE."** `named_routes` went from "2 lines moved" to
"CANNOT BE SWEPT" after S13 — and the PRE-S13 data raises too, at rtol 1e-7, one
decade CLOSER to the default. **Rebuild the same state on BOTH data bases before
calling a tolerance result new.**
⚠⚠ **A DOCUMENTED BEHAVIOUR CAN BE RESTING ON A WRONG NUMBER MAKING IT BIG ENOUGH
TO SEE.** The hotplate's opening evaporative swing was −24 K/s on Joback's ethanol
and is −1.42 K/s on the measured one, and `temperature_steady` no longer fires on
it at the default tolerance. ⚠ `max_step` does NOT recover it — the loose error
control smooths the spike OUT of the computed solution — but **rtol 1e-9 does**.
⚠ **A ROOT IS ZERO TO SOLVER PRECISION, AND THE LAST BIT IS NOT PHYSICS.** A
readout compared with `>=` against the same expression a terminal event roots on
will disagree with it about half the time. `is_boiling` read **−1.110e-15 bar**
and said "not boiling".
⚠ **A BETTER RECORD CAN MAKE ONE NUMBER WORSE, AND THE ANSWER IS TO WRITE IT
DOWN.** Benzoic acid's measured Tb brings a Fedors Vc; Joback's was closer to the
literature. Taken anyway, because a record may not mix two group-contribution
methods and Fedors' error is MEASURED.
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
⚠⚠ **READ THE CATALOG ROW, NOT THE CLASS NAME.** S11 flagged `skraup-route` step
2 for having ANILINE ON BOTH SIDES; **S12 built it and the row is REAL** — the
oxidant is reduced to it. `vanillin-lignin`'s, next to it on the same queue, is
not. ⚠⚠ **THE SAME SURFACE FEATURE MEANT OPPOSITE THINGS ON TWO ADJACENT ROWS,
AND NEITHER THE CLASS NAME NOR THE BALANCE CHECK COULD TELL THEM APART.**
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
four for four and all four ZERO; **S11 four for four; S12 four for four; S13 four
for four — +0 class, +0 template-ready, +3 species-ready, +0 BOTH.**
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
existed; S10's `game_gates` panel INVENTED a 90 kJ/mol error; **S11's
boiling-point sweep read methane's boiling point as carbon's and counted 360 where
the answer is 310; and S13's own sweep, built on the fix for that, counted 322
where the answer is 830 and generated a table with no aniline in it.**
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS.
⚠ **A GENERATED FILE NOTHING READS IS THE ONE THAT ROTS.** Regenerate all three
catalog artefacts and check them across `PYTHONHASHSEED`.
⚠⚠ **AND A GENERATED FILE'S PROSE ROTS EXACTLY LIKE A HAND-WRITTEN ONE.** ⚠ The
root `README.md`'s coverage table is NOT generated — S4 corrected it, S6 again, M8
again, S7 again, S9 again, S11 again.
⚠⚠ **A PHASE LABEL CARRIES A STANDARD STATE — AND SO DOES A SENTENCE.** S12: the
same reaction is **dS +36.65** as an ideal gas and **dS −329.08** as a liquid,
163.53 kJ/mol apart in dH, because `phase="liquid"` condenses NINE products
against SEVEN reactants. *"Seven molecules become nine, so dS is positive"* is
an ideal-gas sentence that reads like a physical fact. **Price a template with
`reaction_deltas`, never by summing `Hf` and `Gf` by hand.** So does a BASIS.
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
`DELIBERATE_OVERRIDES` names it and says what it cost**; the Skraup's three amine
slots may be three DIFFERENT molecules, so a substituted aniline makes the parent
quinoline too; **`skraup_cyclisation` keeps order 1 in its oxidant, and its dS is
pinned on BOTH standard states because the comment got the sign wrong once**; and
**a template that is not in `validation/rate_ceiling.py` is not audited**;
**`MEASURED_PHYSICAL` is generated from `data/catalog` and never hand-edited**;
**a corpus CAS is resolved by GRAPH first and then by NAME, and a name match must
pass the formula cross-check**; **`CORPUS_SWEEP` and `DELIBERATE_OVERRIDES` are
DISJOINT**, so a hand addition can never hide inside the batch; **an Antoine fit
window must BRACKET its own boiling point**; and **a species that leaves
`BOILS_LOOSELY` must be removed from it rather than left as a stale excuse**.

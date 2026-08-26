We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M8, M12, S1–S10 are DONE.**

# ⚠ THE BASELINE IS MEASURED. DO NOT START WITH THE SUITE.

**S10 RAN THE WHOLE SUITE AT THE END AND MEASURED 932 PASSED / 0 FAILED IN
13:20.** Take that number and spend the time on content. ⚠ **It was run AFTER
every `src/` edit, so it is a real baseline and not arithmetic** — the first time
in four sessions that is true. (928 at S9, net +4: eight tests added across
`test_smelting.py`, `test_element_data.py` and `test_phase_properties.py`, four
absorbed into rewrites of tests that pinned limitations S10 removed.)

⚠ **S10 DID NOT TOUCH THE RHS**, so `validation/tolerance_audit.py` was NOT
re-run and its last reading still stands from S9: *"NO example prints a quotable
digit that moves."* ⚠ What S10 did change is `properties/condensed.py`, which
feeds every example's energy balance — and the one example that could move was
measured directly instead: **`examples/mercury_retort.py` shifts by ONE DIGIT IN
THE NINTH DECIMAL** (0.012636665 → 0.012636666, 1 part in 1e8). Nothing else in
the example set holds liquid mercury or zinc. ⚠ `oil_of_vitriol`'s wrong headline
is UNCHANGED and still open — engine queue item 6.

⚠ **AND THE STANDING AUDITS ARE ALL CLEAN**, re-run this session:
`smelting.py`, `game_gates.py` (fixed — see below), `catalog_coverage.py`,
`corpus_balance.py` (292 balance / 75 cannot, unchanged), `rate_ceiling.py`,
`cell_potentials.py`, `gas_processes.py`, `jacobian_bound.py`, and all three
catalog artefacts byte-identical across `PYTHONHASHSEED` 0 / 1 / 12345.

```bash
python validation/smelting.py                 # ⚠⚠ S9's standing audit, ~1 min. RUN IT FIRST
python validation/gas_processes.py            # S7's, ~1 min
python validation/corpus_balance.py           # S7's other one, ~20 s. READ IT before picking
python validation/catalog_coverage.py         # ⚠ READ THE 'BOTH' LINE: 28/173, ~15 s
python validation/game_gates.py               # the element floor's cross-check, seconds
python tools/build_route_index.py             # the artefact nothing reads
python validation/cell_potentials.py          # M8's standing audit, seconds
python validation/rate_ceiling.py             # M12's, seconds. ⚠ S9 gave it a FIFTH panel
python validation/jacobian_bound.py           # S5's standing audit, ~1 min
python -m ruff check src tests examples validation tools
python -m pytest -q                           # ~13 min. ONLY after touching src/
python validation/tolerance_audit.py          # ~8 min. ONLY after touching the RHS
```

⚠ **THE SUITE AND THE TOLERANCE AUDIT ARE MINUTES OF SATURATED CPU ON THE USER'S
OWN MACHINE.** Say what a long run will cost before starting one, and ask.
`examples/plate_column.py` alone is 12 minutes.

---

# ⚠⚠ START HERE: THE WORK QUEUE, AND **THE +2 IS GONE**

S8 handed forward one +2 (`gas-solid-reduction`) and a table of +1s. S9 built the
+2 — and everything left on the coverage queue is now **+1**, with the single
nominal +2 (`isomerisation`) dead three times over. ⚠⚠ **So the coverage queue is
no longer where the value is. Read the ENGINE queue below it before choosing.**

Every class in this table is one class away from a route that is species-ready,
produces no marker, and can be balanced. **Pick for the MECHANIC, and say which
you are picking for.**

| class | its route | worth | what it is |
|---|---|---:|---|
| ⚠⚠ **`hydroformylation`** | `oxo-process` | **+1, and the best mechanic here** | `propene + CO + H2 -> butanal` over cobalt — and the class's **TWO rows are the SAME reaction with DIFFERENT REGIOCHEMISTRY** (`butyraldehyde` and `isobutyraldehyde`, "same reactor, n:iso selectivity"). That is a **competing-template SELECTIVITY** mechanic and this project already has `test_competing_templates.py`. `cobalt` is in `mineral_data` (S8) so `steam_reforming`'s declared-solid-catalyst shape applies directly. ⚠ Read `chemsim-catalysis-and-bounds` first: a declared catalyst's folded concentration must be DECLARED |
| **`wacker-oxidation`** | `wacker-process` | +1 | `2 C2H4 + O2 -> 2 acetaldehyde`, with `copper-ii-ion` written on BOTH sides — a homogeneous catalyst, which is `library._maybe_catalyse`'s own case. Needs the electrolyte templates beside it for `[Cu+2]` to exist |
| **`skraup-cyclisation`** | `skraup-route` | +1 | aniline + acrolein -> quinoline. ⚠ Nitrobenzene is the oxidant AND is regenerated, and step 1 (`dehydration`) is already covered, so this is genuinely the last class the route needs |
| **`oxidative-cleavage`** | `vanillin-lignin` | +1 | a C=C cleaved by an oxidant; NaOH on both sides |
| `fischer-tropsch` | `fischer-tropsch` | +1 | `8 CO + 17 H2 -> octane + 8 H2O`, **25 slots**. The Claus template proves 24 works — but read M8 §6 on the lump that was refused |
| `molten-salt-electrolysis` | `downs-cell` | +1 | ⚠ **A MELT is not a phase this project has** — M8's own named leftover, and it is engine work |
| `catalytic-air-oxidation` | `p-xylene-oxidation` | +1 | ⚠⚠ **M5 REFUSED THIS CLASS** — its four rows are at least three mechanisms (liquid-phase radical autoxidation, Mars-van Krevelen over V2O5, an oxidative ring cleavage). **Split it before crediting it**, and only one of the four rows is runnable |
| `direct-combination` | `vermilion-route` | +1 | ⚠⚠ **S9 MEASURED AND REFUSED IT.** `Hg + S8 -> HgS` is a curated LIQUID element plus a MOLECULAR solid, and `build_surface_arrays` refuses a non-lattice solid by name: `PhaseArrays.lattice` cannot answer "how much solid is there" for a species with a solid block AND a liquid block AND a headspace. **Do not re-derive this.** Neither table's shape |
| `fermentation` | `abe-fermentation`, `msg-route` | +1 | ⚠ **M5 REFUSED IT** as a metabolic NETWORK rather than a transformation. That refusal still stands |
| `separation` | `coal-tar-distillation` | +1 | ⚠ **M5 REFUSED IT**: a distillation is not a reaction class, and the feedstock has no graph |

⚠⚠ **AND THE EIGHT THE REPORT STILL PROMISES THAT THE BALANCE AUDIT KILLS.** Do
not start any of these without reading `corpus_balance.py`'s output on it:

| class the report ranks | route | the step that cannot balance |
|---|---|---|
| **`isomerisation` (still the report's TOP ROW, at +2)** | `hydrogenation-margarine` | step 2 `spurious` — an H2 in and none out |
| " | `starch-hydrolysis` | step 1 `atoms` |
| `metal-ion-aldehyde-oxidation` | `tollens-test` | step 1 `atoms` |
| `pyrolysis` | `wood-distillation` | step 1 `atoms` |
| `biological-transformation` | `tyrian-purple-route` | step 1 `atoms` — the product has two BROMINES and there is none on the left |
| `dissolving-metal-reduction` | `aniline-route` | step 1 `atoms` — the chloride has nowhere to go |
| `polycondensation` | `pet-route` | step 2 `atoms` |
| `thermal-cracking` | `steam-cracking` | step 1 `spurious` |

⚠ **`isomerisation` IS DEAD THREE TIMES OVER AND IS STILL THE TABLE'S TOP ROW.**
Besides the two balance failures: `oleic -> elaidic` prices at **dH = dG = 0.000
EXACTLY** (no estimator here tells a cis alkene from a trans one), and
`glucose -> fructose` at **K = 4.8e-08** because the corpus spells one as a
pyranose and the other as a furanose. **Do not build it.** Read §S7 before
arguing with that.

⚠⚠ **AND `ostwald-process` HAS JUST LEFT THIS TABLE, WHICH IS THE POINT OF THE
SECOND HALF OF S9.** It was listed as one class away (`disproportionation-
hydrolysis`) for two sessions on a credit it never had: its step 1 was under
`catalytic-gas-oxidation`, a class whose three rows are three different reactions
and whose only implemented one is Deacon's. Split, and the route is **two**
classes away — it needs an ammonia oxidation nothing here makes. **A ranking is
only as good as the credits under it, and this is the second class to come apart
under that check rather than under a build.**

---

# ⚠⚠ THE ENGINE AND HONESTY QUEUE — AND IT NOW OUTRANKS THE TABLE ABOVE

1. **⚠⚠ A METAL THAT BOILS OUT OF THE SOLID BLOCK — STILL OPEN, AND S10's OWN
   WRITE-UP OVERSTATED WHAT IT COSTS. THE MEASUREMENT IS BELOW; TRUST IT OVER THE
   PROSE IN §S10 §8.** S9 filed one gap with two symptoms, on the shared sentence
   *"a lattice may react and may never boil"*. **The zinc half was a DATA job and
   is CLOSED** (the retort distils, no engine code changed — §S10). The iron half
   is open, and it is **much cheaper than §S10 says**.

   ⚠⚠ **IT WAS MEASURED AFTER THE COMMIT, BY PATCHING IRON'S VOLATILITY IN PLACE
   (Alcock's curve) AND RUNNING THERMITE INSULATED. IT WORKS:**

       vessel Cp    lattice iron    VOLATILE iron    where the iron went
          1 J/K       5469.43 K        3490.99 K     0.0192 gas / 0.0207 liquid
         10 J/K       2329.06 K        2284.28 K     0.0399 liquid (it MELTED)
         50 J/K       1322.45 K        1322.45 K     unchanged — never reaches Tm

   The runaway CAPS, `conservation_report` stays empty, and the 50 J/K flask is
   **identical** because its temperature never reaches the melting point. ⚠ 3491 K
   rather than a real ~3135 K is not error: a sealed 1 L flask pressurises, so the
   iron boils above 1 atm. A vented one would sit nearer 3135. ⚠ The melt at
   1811 K appears too, which §S10's audit records as something the engine could
   not see.

   ⚠⚠ **THREE CORRECTIONS TO §S10 §8, ALL OF WHICH MAKE THIS SMALLER:**
   * **The two hot-loop uses of `PhaseArrays.lattice` are in the SURFACE term
     ONLY, and iron is in no surface row** — so its `order` column is all zeros
     and `C_mix[Fe] ** 0 == 1.0` exactly. Inert, by the same `p ** 0` invariant S9
     already pinned. `SolidStateArrays` (thermite's term) takes explicit
     `nu_solid`/`nu_gas` from the DECLARATION and never consults the boolean.
   * **The Haber catalyst never depended on the flag.** It reads `order_solid` and
     `nS` (`vessel_integrator.py` ~1780, ~1886). What needs `MINERALS["iron"]` is
     *name resolution* in the network builder — `_catalyst_lattice`, plus
     thermite's `decl.solids` — and that is separable from volatility. **Iron must
     keep its `mineral_data` ENTRY; it does not need `lattice` to stay True.**
   * **So the actual blocker is ONE BRANCH in `build_phase_arrays`** — the
     `if mineral is not None:` arm that pins `vol_A = NONVOLATILE_A`,
     `condensable = False` and `solidifies = False`. Letting a `MineralRecord`
     carry OPTIONAL volatility and having that branch consult it is a
     **setup-layer change with NO RHS edit**, so it carries no tolerance-audit
     exposure. That is not what §S10 §8 implies.

   ⚠ **THE GENERAL FORM IS STILL WORTH FIXING, and it is already patterned twice
   in this codebase.** One boolean answering two questions will bite the moment a
   volatile lattice appears in a SURFACE reaction. Note that
   `build_surface_arrays` already receives `decl.solids` and `decl.gases`
   separately and already builds separate `order_solid`/`order_gas` matrices — it
   then collapses `nu` into ONE array and lets the RHS re-derive the split from
   `is_lattice`. **The information is present at setup and thrown away.** So:
   build `nu_solid`/`nu_gas` there (copies `build_solid_state_arrays`), and split
   `C_mix` into two one-sided products (**literally S9's move**). Both touch the
   RHS, so the five existing surface rows must come out bit-identical — the same
   `p ** 0 == 1.0` argument, and S9's test is the template.

   ⚠⚠ **BUT THE DATA OBJECTIONS SURVIVE THE ENGINE FIX, AND THAT IS THE POINT TO
   SCOPE ON.** The probe above patches ARRAYS; it does not curate a record, so a
   green result there does **not** license admitting `[Fe]`. `[Fe]` still fails
   S4's DISAMBIGUATION test (three solid allotropes, two transitions inside
   thermite's own range, against zinc's single condensed form) and Alcock
   tabulates **no sublimation curve** for iron, so the 298 K reference-state
   identity zinc closed at −0.184 kJ/mol cannot be evaluated at all — **ONE
   cross-check, not four.** Deciding whether one check is enough for a species
   with three allotropes is the real work here, and it is a judgement, not a
   measurement. The mechanism and most of the data are adequate: Alcock's iron
   equation converts to Antoine by exact algebra (A = 6.352717, B = 19574, C = 0),
   unanchored Tb 3083.98 K against 3134.15 (**−1.60%**), and boiling thermite's
   2 mol of iron absorbs **749.5 of the 851.5 kJ it releases, 88.0%**.

   ⚠ **WORTH ZERO ROUTES for iron** — take it for the mechanic and say so.
   ⚠⚠ **BUT MEASURE `direct-combination` FIRST: it is worth +1 AND it is refused
   by the SAME `build_surface_arrays` non-lattice check.** `vermilion-route`'s
   `Hg + S8 -> HgS` is refused because a SOLID participant must be a
   `mineral_data` lattice and S8 is a molecular solid. If the general fix above
   reaches it, this item stops being worth zero. ⚠ **Hold that as a HYPOTHESIS,
   not a finding** — `Hg(l) + S8(s)` is not a gas attacking a crystal, so
   `SurfaceArrays`' form (extensive in the solid, INTENSIVE in the gas) may be
   wrong for it whatever the mask says. **Measure it before scoping either.**

   `test_thermite_runs_away_on_its_own_enthalpy_and_nothing_caps_it` pins the
   limit and names the counts; if you close it, that test SHOULD change. ⚠ Its
   docstring carries the same overstatement as §S10 §8 and has a correction note
   pointing here.

2. **⚠⚠ THE 250–450 K FIT WINDOW — 103 CORPUS ROWS WITH A NEGATIVE LIQUID HEAT
   CAPACITY, AND S10 FIXED TWO OF THEM BY HAND.** New, and the largest single
   honesty item on this list. `CondensedProvider.get(mol, T_lo=250.0, T_hi=450.0)`
   is an organic-solvent window and **every caller in the repo takes the default**,
   so Rowlinson-Bondi is fitted where a species may not be liquid and then
   extrapolated into the range where it is. Measured over `data/catalog`:
   **103 compounds return a NEGATIVE liquid Cp somewhere inside their own liquid
   range** (worst carminic acid at **−21482 J/(mol K)**) and 41 more swing over 5x.
   ⚠ **It bites at BOTH ends** — ethylene reads ~1574 J/(mol K) at its 113.9 K
   melting point, and ethylene is a curated-Antoine species and a real reagent.
   * ⚠ **A negative Cp is not an accuracy problem: adding heat LOWERS the
     temperature.** S10 measured it reachable — with 50 J/K glassware a flask
     holding over **3.96 mol of liquid mercury (795 g, 59 mL) had a NEGATIVE TOTAL
     thermal mass**, −12.808 J/K at 5 mol — and mercury had carried it since S4.
   * ⚠⚠ **BUT DO NOT JUST WIDEN THE WINDOW.** Most of the 103 have a JOBACK
     Tm/Tb that is itself meaningless (carminic acid "melts" at 1398 K and really
     decomposes), so there the bad Cp is downstream of a bad transition
     temperature and fitting over it would be fitting to nonsense. **Separate the
     wrong output from the wrong input first.** The two metals were the clean
     cases precisely because their Tm/Tb are MEASURED and the Cp was still wrong.
   * ⚠ Fitting over each species' OWN liquid range is the obvious fix and it moves
     **every** example's energy balance, so it needs the tolerance audit and a
     stated cost. `test_the_250_450_K_FIT_WINDOW_IS_STILL_THE_GENERAL_FAULT` pins
     the gap as it stands.
   ⚠ Worth ZERO routes. Measured inert on every example today — a LATENT
   fragility, reported and not refused.

3. **⚠ `slagging` + ONE MINERAL WOULD MAKE `blast-furnace` RUN — THE CLOSEST ANY
   FIVE-STEP ROUTE HAS BEEN.** S9 gave it three of its five classes
   (`carbon-combustion`, `boudouard`, `gas-solid-reduction` ×2). What is left:
   * **`slagging`** (`CaO + SiO2 -> CaSiO3`) — one row, one class, and it is a
     `SOLID_STATE_REACTIONS` row with NO GAS AT ALL, exactly `thermite`'s new
     shape. ⚠ Needs `silicon-dioxide` and `calcium-silicate` in `mineral_data`.
   * **`iron-ii-oxide`**, which `mineral_data` refuses because CRC does not
     tabulate its crystal Cp (recorded there since M6). **This needs a SOURCE,
     not a workaround.**
   ⚠ Worth **+1** and it is a five-step ore-to-metal chain with a real slag. Two
   curated minerals and one declaration if the FeO Cp can be sourced honestly.

4. **⚠ THE CIS/TRANS BLIND SPOT — A REAL DATA JOB WITH A REAL TRAP.** Benson (the
   RMG group set) has no cis correction, so oleic and elaidic acid come back with
   IDENTICAL Hf and Gf and the engine reports a confident 50:50 for a real ~5:1.
   ⚠ **The data exists and is not usable as it stands:** WEBBOOK has both liquid
   enthalpies, −764.8 and −769.0 kJ/mol, and that 4.2 kJ/mol gap agrees with
   Benson's own historical cis NNI term of 4.18 to 0.4% — **two independent
   sources**. But neither has an S0, so no Gf can be derived, and grafting
   Benson's original correction onto RMG-fitted group values **mixes two bases**,
   which is the trap `chemsim-benson-status` exists to name. ⚠ Worth ZERO routes
   today (the margarine row cannot balance either) — take it for the honesty.
   `test_the_cis_trans_pair_prices_at_exactly_zero` pins the limit.

5. **⚠ THE CURRENT BUDGET — M8's OWN NAMED GAP, AND IT IS A LAYER 4 TERM.** Two
   electrode reactions in one cell divide nothing, so both run at full rate and
   activation selectivity washes out as the barrier floors at zero:
   k(brine)/k(water) is **4.76e+17 at 2.5 V, 5.94 at 3.0, 1.00 at 4.0**. The
   selective window here is ~2.2–2.7 V where a real chloralkali cell holds 99% at
   3 V and above. ⚠ Worth **ZERO new routes** — chloralkali already runs — so
   take it for the mechanic and say so.
   `test_the_activation_selectivity_washes_out_at_high_voltage` pins the gap.

6. **⚠ S5's SIXTH INSTRUMENT FAULT, STILL OPEN AND STILL CHEAP.**
   `tolerance_audit.py` reports `QUOTABLE DIGITS MOVE, worst 99.85%` on
   `oil_of_vitriol`, and **that headline is wrong**: four of its five moved lines
   are the CREATED-MATTER residual and every one gets SMALLER, on rows
   `NEXT_SESSION.md` already carries as "NOT AN INVARIANT". **A
   relative-difference test is meaningless on a column whose converged value is
   zero.** `REPORT_ABS` exists for this and 2.9e-05 clears it. Picking the number
   owes its own predict-then-measure pass.

7. **Pyrite** — one mineral entry from `pyrite-roasting` running, and it is one of
   the **10 template-ready routes that cannot run**, so it is +1 on the
   intersection for one curated entry. Blocked on the same-database rule (`Hfs`
   in WEBBOOK, `S0s` in nothing), which is a rule worth keeping, so this needs a
   SOURCE and not a workaround. ⚠ **Same shape as item 2's FeO** — a session that
   finds one source may find both.

8. **⚠⚠ THE BURNER — THE LIVE FRAGILITY, STILL DEMOTED AND STILL NOT DISMISSED.**
   **~50 s at rtol 1e-8 against 0.8 s at the default.** S5 bounded the CRASH and
   explicitly did not bound the THRASHING. BDF is struggling with a liquid layer
   holding **1e-29 mol**, which `LAYER_REABSORB` drains toward zero without ever
   reaching it. **The question nobody has asked is whether a layer below
   `LAYER_EPS` should be *merged discretely* at a step boundary rather than
   drained continuously for ever.** ⚠ `merge_phases` already does exactly that at
   the `run` boundary — so this may be a matter of WHEN IT IS CALLED, not of a
   new mechanic. **Measure the layer-2 inventory over the failing run before
   designing anything.** It fires only at rtol 1e-8, so nothing a player does
   reaches it.

9. **THE CORPUS BALANCE BACKLOG — 75 ROWS, AND IT IS NOT A TO-DO LIST.** S7 built
   the check and deliberately fixed nothing, on the `diels-alder-route`
   precedent: inventing chemistry inside an audit corpus is not allowed. ⚠ But
   **17 of the 75 are `spurious`** — a reagent written as consumed that is
   really a catalyst — and those are the cheapest and least inventive to correct,
   because the fix is to put the species on both sides of the row it is already
   on one side of. ⚠ `tools/catalog.py`'s `validate` still does NOT check
   balance, so the corpus can grow another one silently.

10. **⚠ `hydrolysis` — AND READ S3's LANDMINE FIRST.** It unlocks **exactly ONE
   route alone, `vitriol-distillation`**, and that route's step 1 reads
   `-> iron-ii-OXIDE` while the engine makes HEMATITE. ⚠ **That is item 2's
   mineral again, from the other side.** S3 and S4 disagree about what to do with
   such a row — read §S3's "which one is WRONG" check before deciding.

11. **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
    re-scope before scheduling)**, **M9 (polymers, 12 routes)**, **M10 (the site
    balance S1 did not build, 8 routes)**, **M11 (the unpriceable families, 16
    routes, and 10 of them need ONE boiling point each)**.

12. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
    the *deposition-needs-a-seed* half into a real bound in
    `SolidStateArrays.units`. What is still not expressible is a solid appearing
    from NO solid — `hydride-thermal-deposition` (`arsine -> arsenic + hydrogen`)
    is still a mechanism gap for that reason. ⚠ **S9 leaned on the modelled half
    deliberately** (an exhausted furnace stops in both directions), so read
    `units`' docstring before touching it.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§S10, §S9, §S8, §S7, §M8, §S1, §S3, §S4, §S5 and §S6 are
  the ones to read**: **S10 found that S9's top engine item was HALF A DATA JOB —
  the sentence it rested on was about a `mineral_data` ENTRY, not about the metal —
  that splitting it in two is what LOCATED the engine gap, that a NEGATIVE liquid
  heat capacity had been in the engine since S4 with 103 corpus rows still carrying
  one, and that S9's own overblowing finding was a RATE ARTEFACT written up as
  physics**; S9 found that the engine gap S8 called "the most valuable
  unscoped item in the plan" was ONE ALGEBRAIC REARRANGEMENT, that half the
  reason recorded beside the refusal was about a form the term never used, and
  that S8's own zinc measurement had priced a reaction the catalog does not
  contain**; S8 did a job this file called "cheapest" for two sessions and
  measured it at +0 on the number that counts; S7 measured the queue's top two
  rows at ZERO and split a class in a way that LOWERED the headline; M8's brief
  predicted the wrong failure AND named a class that split under its own row
  check; S1's brief asked for one mechanism and the arithmetic said two; S3 found
  the instrument's own OUTPUT was not diffable; S4's brief said to reverse a
  re-label and the arithmetic said keep; **S5's brief named the wrong LAYER**;
  and **S6's brief handed it a number that was wrong.**
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1, 86 is S2, 87 is
  S3, 88 is S4, 89 is S5, 90 is S6, 91 is M8, 92 is S7, 93 is S8, 94 is S9,
  95 is S10.**
NEXT_SESSION.md — the invariants table at the bottom is the contract, and S7, S8,
  S9 and S10 each added a block to it. ⚠⚠ **S10 also WITHDREW a row** (the zinc
  flask going down at 0.20 mol O2) and MOVED another (the retort's threshold, 1264.2
  → 1197.8 K) — the first withdrawal that table has had. ⚠ Read the two warnings above it before
  trusting any row, and note that TWO rows are LIMITS to remove rather than
  invariants to keep.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **S9's two splits
  (`carbothermic-reduction` and `catalytic-gas-oxidation`)**, S7's of
  `combustion`, M8's of `electrolysis`, S3's of `thermal-decomposition` and S4's
  decision NOT to un-split `roasting-to-metal`; plus
  `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-vaporising-metal,
  chemsim-physical-data-sourcing, chemsim-reversible-solid-gas,
  chemsim-solid-state-reactions, chemsim-surface-reactions,
  chemsim-solid-gate-fix, chemsim-element-solids, chemsim-coverage-catalog,
  chemsim-corpus-balance and chemsim-generated-artefacts.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 43 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, a catalyst you have to actually put in
the flask, a route that nothing declares, a Jacobian that cannot be probed outside
its own state, a dial that decomposes things in the order their chemistry says
they should, four inorganic gas processes whose whole behaviour is their
reversibility, three smelters that take ore, coke and air to metal through
four declarations that do not know about each other, and **a retort that DISTILS
its metal off and condenses it in a cool receiver, at a boiling point nothing
typed**. `SAVE_VERSION` is **5**.
Coverage: **48/229 classes**, **43 templates**, **38/173 template-ready**,
**77/173 species-ready** — and ⚠⚠ **28/173 BOTH, which is the only one of the
three a route can be judged on.**

---

# ⚠⚠ WHAT S10 TURNED OUT TO BE: +0 ROUTES, AND THAT WAS THE PREDICTION

**+0 classes, +0 template-ready, +0 species-ready, +0 RUNNABLE — all four
predicted before the audit ran and all four came out.** An honesty and mechanic
milestone, taken as one and said so up front. ⚠ **NO ENGINE CODE CHANGED**: not
one line of `numerics/` or `vessel/`. Coverage stays **48/229 classes, 38/173
template-ready, 77/173 species-ready, 28/173 BOTH**.

## ⚠⚠ 1. S9's TOP ENGINE ITEM WAS HALF A DATA JOB, AND SPLITTING IT LOCATED THE REST

S9 handed forward ONE gap with two symptoms — the zinc retort makes solid zinc,
nothing caps thermite's temperature — both citing *"a lattice may react and may
never dissolve, boil or melt"*. **They are not one gap, and the pairing is what
hid the real one.** That sentence is true of `PhaseArrays.lattice`; what put zinc
under it was a `mineral_data` ROW. Against S4's own three tests for admitting
mercury, zinc passes all three — a monatomic vapour at 1180.15 K (group 12, no Zn2
to be wrong about), ONE condensed form, and an expressible reference state.
⚠ Mercury passed the third on the LIQUID block; **zinc passes it on the SOLID
block, which the table already relied on twice for I2 and S8.**

So `[Zn]` moved into `element_data` and out of `mineral_data`, and the row became
`ZnO + C -> Zn(g) + CO`. **One edit to a tuple.**

## ⚠⚠ 2. THE VAPOUR PRESSURE IS ALGEBRA, AND AN UNANCHORED FIT MAKES Tb A REAL CHECK

Lee-Kesler has no domain over a liquid metal (S4 measured it 3.8x high for
mercury), so zinc needed a curated Antoine for mercury's reason. Alcock, Itkin &
Horrigan (1984) publish the liquid range as **two constants**,
`log10(p/atm) = 5.378 - 6286/T`, and with C = D = 0 that IS Antoine with C = 0 —
a change of base and of pressure unit, **nothing fitted**, agreeing to 4e-15 over
700–3000 K, and the round trip reproduces Alcock's published numbers to four
figures.

⚠⚠ **`chemsim-physical-data-sourcing` says boils-at-1-atm is NOT independent,
because Lee-Kesler's ω is inverted at Tb to make it pass. THE CONVERSE IS WORTH AS
MUCH.** Alcock's fit was made over 692.7–750 K and never saw Tb, so where it lands
the boiling point is real evidence. **Ask what a fit was ANCHORED ON.** Four
checks, and CRC never meets Alcock in any:

| check | result |
|---|---|
| `Gf(g) + RT ln(Psub/P0) = 0`, sublimation curve at 298 K | **−0.184 kJ/mol** (Br2 −0.053, Hg +0.012, I2 +0.139, S8 +3.052) |
| that curve's SLOPE vs CRC's Hf(g) = 130.400 | **130.674, +0.21%** |
| the unanchored boiling point | **1168.84 K vs 1180.15, −0.96%** |
| sublimation and liquid fits at the triple point | **+0.103%** |

⚠ `chemicals` ships Alcock for the metals and no accessor advertises it usefully —
`thermo.VaporPressure` reports `T_limits=(692.677, 750.0)` for zinc, which is the
TABLE's window and not a hole in the data. Raw files:
`chemicals/Vapor Pressure/Alcock_Itkin_Horrigan_metalic_elements{,_sublimation}.tsv`.
⚠ Tc/Pc/Vc are YAWS only (**compilation** tier) and stamped as such.
⚠ And the price of deriving Hvap from the curve the engine evaluates is that
Alcock's fit measures the latent heat near the MELTING point: **120.344 against
CRC's 115.3 at Tb, +4.4%.** Taking CRC's would mix two tabulations. Stated.

## ⚠⚠ 3. THE THRESHOLD MOVED 66 K TOWARD THE LITERATURE, AND THE ROW GOT FASTER

    Zn(s) product, S9    dH +240.0 kJ/mol   dS +189.8   dG = 0 at 1264.2 K
    Zn(g) product, S10   dH +370.4 kJ/mol   dS +309.2   dG = 0 at 1197.8 K

against a real Belgian retort's 1200–1300 and a literature ~1200 K. ⚠ The barrier
rose by the same 130.4 kJ/mol (`Ea = max(dH,0)`) — inside the 300–400 kJ/mol range
reported for carbothermic zinc, so it is defensible rather than merely arithmetic.
⚠⚠ **AND THE ROW IS 24x FASTER ANYWAY**, because an Arrhenius pair is not
separable: the derived `A` carries `exp(dS/R)`, and at 1400 K `exp(119.4/R)` =
1.7e6 beats `exp(−130400/RT)` = 1.4e-5. **tau 256.9 s → 10.9 s**, equilibrium
untouched, still under the collision ceiling.

## ⚠⚠ 4. THE DISTILLATION, AND TWO MECHANICS NOBODY DECLARED

Sealed 1 L at 1400 K: **0.040000 mol of zinc, every atom in the headspace.** Cool
the receiver and it comes back — 0.028404 liquid at 1180 K, 0.039665 at 900 K,
**0.040000 SOLID at 600 K.** ⚠ **Tb = 1180.15 and Tm = 692.68 appear in no
declaration and in no script.**

⚠⚠ **THE VENT DOES NOTHING UNTIL THE RETORT BEATS THE ROOM.**
`solid_state_report` DERIVES 1156 K for the row's two evolved gases to reach one
bar between them. Measured: **12.29% sealed / 12.29% vented at 1150 K** (0.9325
bar) against **13.52% / 18.63% at 1156 K** (1.0312 bar), rising to 25.67% / 99.84%
at 1198 K. A van 't Hoff number and a flask that was actually run, agreeing to the
degree.

⚠⚠ **AND A VENTED RETORT BLOWS ITS PRODUCT UP THE CHIMNEY.** Ore consumed
99.91% → 100% while metal KEPT falls **51.04% → 46.93% → 43.53%** at
1200/1300/1400 K, because the vent is indifferent to which gas it vents. **That is
why a real Belgian retort has a condenser on it**, and why the threshold panel is
run SEALED. ⚠ `conservation_report` is silent throughout, correctly.

## ⚠⚠ 5. AND S9's OVERBLOWING FINDING IS WITHDRAWN — A RATE ARTEFACT WRITTEN UP AS PHYSICS

S9 measured the zinc smelter's yield going DOWN at 0.20 mol O2 and concluded
*"Overblowing a zinc retort really does waste the charge."* The competition is
real. **But which side won was decided by two DERIVED pre-exponentials**, and §3
moved one by 24x: the reduction now takes the zincite before the blast can burn
the coke, and the yield is monotone and saturating (.0117 / .0229 / .0328 / .0400,
flat to 0.50 mol O2).

⚠⚠ **THE SIGN OF THE EFFECT DEPENDED ON A CLOCK.** A real furnace does waste an
overblown charge, for transport reasons this engine does not model. **Thermodynamic
conclusions here survive a phase change in a product; kinetic ones need not.** New
rule, and the sharpest thing in the session.

## ⚠⚠ 6. A NEGATIVE HEAT CAPACITY HAD BEEN IN THE ENGINE SINCE S4, AND 103 ROWS STILL HAVE ONE

`CondensedProvider.get` fits Rowlinson-Bondi over a **hardcoded 250–450 K** and
every caller takes the default. For a metal that is a LIQUID correlation evaluated
where there is no liquid, then extrapolated in: **mercury −25.26 at Tm, −12.62 at
298 K** against a real 27.98; **zinc +462.51 at Tb** against 31.38.

⚠⚠ **AND IT WAS REACHABLE**: with 50 J/K glassware, a flask holding over
**3.96 mol of liquid mercury (795 g, 59 mL) had a NEGATIVE TOTAL thermal mass** —
−12.808 J/K at 5 mol, i.e. heating it cooled it. Both curated from measurement
(mercury CRC 28.000 / VDI 28.031 / Fit-2023 27.976, three sources inside 0.2%;
zinc from the WebBook Shomate curve over its OWN 692.73–1180.17 K window, flat at
31.380). Cost on the pinned example: **one digit in the ninth decimal.**

⚠⚠ **THE GENERAL FAULT IS ENGINE QUEUE ITEM 2 AND IT IS LARGE: 103 corpus rows,
worst −21482, plus 41 swinging over 5x, and it bites at BOTH ends** (ethylene
~1574 at its 113.9 K melting point). ⚠ Mostly on Joback Tm/Tb that is itself
meaningless — **separate the wrong output from the wrong input before fixing it.**

## ⚠⚠ 7. TWO INSTRUMENTS WERE WRONG AND ONE INVENTED A 90 kJ/mol FINDING

* **`validation/game_gates.py` printed a residual whether or not the shift it
  differences had been APPLIED.** `standard_state.shift` correctly refuses one
  whose 298 K vapour pressure is under `PSAT_FLOOR_BAR` = 1e-12 and returns 0.0
  with a reason; differencing that zero read **"zinc, residual +90.78 kJ/mol"**
  for a formation pair that is fine. **Every other row has an applied shift, so
  the hole was unreachable until a solid with a 2e-16 bar vapour pressure
  arrived.** The panel says REFUSED with the reason now, and gives zinc the check
  it CAN have.
* **`volatility._CURATED_ANTOINE` stamped every entry `NIST WebBook`** — true of
  all nine and false the moment a tenth came from Alcock. ⚠⚠ **That is exactly the
  shape S9's false citation had: correct when written, silently wrong after the
  next addition.** Per-entry overrides in `volatility` and in `condensed`, whose
  strings claimed "at 298 K" for a zinc liquid volume taken at 700 K.

## 8. IRON IS REFUSED, MEASURED RATHER THAN ASSUMED — AND IT IS ENGINE QUEUE ITEM 1

The mechanism would work (88.0% of thermite's enthalpy could go into boiling the
iron) and the curve converts exactly (−1.60% on an unanchored Tb). Three counts
against: **iron cannot leave `mineral_data`** (a declared `solid_catalyst` via
`ammonia_synthesis` AND thermite's solid product, so it must be BOTH a lattice and
a gas); `[Fe]` fails S4's disambiguation test (three solid allotropes, two
transitions inside thermite's own range); and **no sublimation curve exists**, so
zinc's best check cannot be run at all.

## 9. THE PRE-EXISTING THING ZINC JOINED RATHER THAN CREATED

`solidifies = True` exposes zinc to the ideal fusion law and zinc has no UNIFAC
groups, so x_sat = **0.197** at 298 K, 89 g/100 mL against a real ~1e-8. ⚠
**Measured before accepting it:** iodine is over by **1.5e4x** and sulfur by
**1.1e8x** on the same law, and zinc's mole fraction is SMALLER than iodine's
(0.238), sulfur's (0.275) or naphthalene's (0.302). Reachable only by putting
metal in water, which no route does. **Check whether a new wrongness is a new
CLASS or a new member before pricing it.**

## 10. THE SMALL THINGS

* `species_roles.psv` moves zinc from the `mineral` provenance tier to
  **`measured`** — an upgrade in the audit's own terms.
* ⚠ **Three pieces of prose rotted inside this session's own edits**: the audit's
  overblowing paragraph, its "a lattice against three curated gases" (two of each
  now), and its "the same statement the zinc retort makes". **An audit's prose
  rots exactly like a generated file's.**
* ⚠ `validation/smelting.py` is **CRLF**, contrary to the note that the newer
  `validation/*.py` are LF. Check, do not assume.

---

# WHAT S9 TURNED OUT TO BE: +4 ON THE INTERSECTION FOR ~15 LINES OF ENGINE
*(kept for the record. ⚠ Its §4 overblowing paragraph is WITHDRAWN and its §7
zinc-retort limitation is CLOSED — see S10 above.)*

**+5 classes (43 → 48 of 229 after two splits), +4 template-ready (34 → 38), +4
RUNNABLE (24 → 28)** — tying S7's record. Six declarations, no new term, no new
phase, and the five pre-S9 solid-state rows BIT-IDENTICAL. ⚠ **All four coverage
numbers were predicted before the audit ran and all four came out exactly.**

| | before | after |
|---|---:|---:|
| classes with a template | 43 / 224 | **48 / 229** |
| routes template-ready | 34 / 173 | **38 / 173** |
| routes species-ready | 77 / 173 | 77 / 173 |
| ⚠⚠ **routes BOTH — the one to quote** | **24** | **28** |

The four: `copper-smelting`, `lead-smelting`, `zinc-smelting`, `thermite`.

## ⚠⚠ 1. "THE MOST VALUABLE ENGINE ITEM NOBODY HAS SCOPED" WAS ONE LINE OF ALGEBRA

`SolidStateArrays` already integrated the affinity form and already reached
`Q = K`. What it refused was a gas REACTANT, whose negative exponent in
`Q = prod(p ** nu_gas)` puts a pressure in a DENOMINATOR — M6 measured 2.6e15
formula units per second as the gas ran out. Written as the two ONE-SIDED
products,

    net = k_f * prod(p ** consumed_gas)  -  k_r * prod(p ** formed_gas)

nothing is divided. It is `P_react (k_f - k_r Q)` algebraically — **the same
root, so the same equilibrium** — and at `p_react = 0` it is the finite
`-k_r P_prod`. At 1400 K, as p_CO falls 1 → 1e-6 → 1e-30 → 0, the old branch
reads 1.5e-8, 1.5e-2, 1.5e+22, `inf`; the new one is bounded by `k_r` at
**1.4973e-08** the whole way.

⚠⚠ **AND THE OTHER RECORDED REASON WAS ABOUT A FORM THIS TERM NEVER USED.** It
cited M6's `p/K = n_A/n_B` — true of MASS ACTION on a solid amount, and
irrelevant here, because the affinity form takes ONE `units` for both directions
chosen by the sign of the affinity, so it is a common factor that divides out of
`net = 0`. **That was already true when the refusal was written.** Q/K = 1.0000
over a 50x charge range.

⚠⚠ **SO M6 DREW THE LINE IN THE WRONG PLACE.** The dichotomy was recorded as
*inside a crystal / at its surface*, and S4 had already broken it. The line that
holds is **reversible or not**: an affinity form cannot carry DECLARED rate
orders, because detailed balance fixes its exponents at the stoichiometric
coefficients. That is this project's own standing invariant — *a declared rate
order may NEVER be reversible* — arriving in a new place. Roasting stays in
`SurfaceArrays` **for the order, not for the denominator.**

## ⚠⚠ 2. `Ea = max(dH, 0)` RETURNS ZERO ON AN EXOTHERMIC ROW, AND THE TEMPERATURE LEAVES THE RATE LAW

M6 derives the barrier, correctly for an endothermic decomposition whose reverse
is barrierless. On an exothermic row it is **zero**: thermite comes out at
`A = 4.15e-6 1/s`, a 2.8-DAY reaction, and a CO reduction at 9.70e-4 1/(bar s).
⚠ **The finding is not the size — it is that with `Ea = 0` there is no
exponential**, so thermite goes exactly as fast in a cold jar as in a furnace and
a smelter's heat does nothing. An exothermic row now declares its forward pair
(both halves or neither) and still gets its reverse by detailed balance. ⚠ A
declared `Ea` under `dH` is refused because `Ea_rev = max(Ea - dH, 0)` would CLIP
and leave `k_f/k_r != K` silently.

## ⚠⚠ 3. THE QUEUE HAD PRICED THE WRONG REACTION FOR `carbothermic-reduction`

S8 measured `ZnO + CO -> Zn + CO2` uphill at +63.3 kJ/mol and concluded the class
needed engine work. **The catalog's row is the CARBON one**, `ZnO + C -> Zn + CO`,
where the entropy of making a mole of CO carries it: dG = 0 at **1264.3 K**
against a real Belgian retort's 1200–1300, and two solid reactants with one gas
PRODUCT is an ordinary row of M6's table nobody had written. **It needed no engine
work at all.** Same for Boudouard, which is endothermic and needs only the
gas-reactant fix. **Read the row, not the class name.**

## ⚠⚠ 4. ORE + COKE + AIR → METAL, AND NOTHING DECLARES THE ROUTE

    surface.py       CuS + O2  -> CuO + SO2     a gas at a crystal (S1)
    surface.py       C   + O2  -> CO2           the tuyere         (S9)
    solid_state.py   C   + CO2 -> 2 CO          Boudouard, reversible
    solid_state.py   CuO + CO  -> Cu + CO2      the reduction, reversible

0.04 mol covellite + 0.20 mol graphite + air, sealed at 1500 K: **0.040000 mol
copper, 0.040000 mol SO2, no ore and no coke left**, conservation clean. Same for
galena at 1400 K and sphalerite at 1400 K. ⚠ **The AIR is the control**, which is
what a smelter actually adjusts: on the copper flask 0.02 mol O2 → 29.01%, 0.06 →
80.41%, 0.10 → 99.89%, 0.20 → 100.00%.

⚠⚠ **AND THE ZINC FLASK GOES *DOWN* AT 0.20 mol OF OXYGEN, WHICH NOBODY DECLARED
EITHER.** 0.032476 mol of metal at 0.06 against **0.025515 at 0.20**, with
0.014485 mol of zincite left and the coke completely gone.
`zincite-carbothermic-reduction` and `carbon-combustion` **compete for the same
carbon**, and a blast rich enough to burn all of it leaves nothing to reduce the
oxide with. Copper and lead do not do this — their reductant is the CO the carbon
made and Boudouard keeps handing it back. **Overblowing a zinc retort really does
waste the charge.**

## ⚠⚠ 5. THE CARRIER-FREE FURNACE IS EXACTLY INERT — THE LEAD CHAMBER'S FAILURE MODE NOT HAPPENING

Ore + coke with **no gas at all**: 0.0 copper, 0.0 CO, 0.0 CO2 at the default
rung, rtol 1e-6, 1e-8 and 1e-10. A cycle with gain on its own carrier is exactly
the shape that let round-off seed the lead chamber to 89% yield; the reason it
cannot happen here is the FORM and not a guard — the arriving gas enters as
`p ** 1` with no denominator, so zero in is zero out with a bounded slope.
⚠ **Once SEEDED it multiplies, which is real chemistry:** 1e-12 mol of CO2, one
part in 1e11 of the charge, reduces the whole 0.10 mol of oxide. Boudouard makes
2 CO from 1 CO2 and the reduction hands one back. **The carbon is the reagent; the
carbon oxide is only the vehicle**, which is why a furnace is charged with coke.

## 6. THERMITE — A ROW WITH NO GAS, AND ONE PIN BUYS A COLUMN

Four crystals, no gas, so both one-sided products are empty (exactly 1.0) and the
affinity collapses to `k_f - k_r`. One pin on the reported 1200 K ignition
temperature: 0.0000% at 298.15 K, 3.1e-10 mol at 600, 0.2171% at 800, **36.95% at
933 — where ALUMINIUM MELTS**, which nothing in this engine knows — 98.16% at
1000, 100% at 1200. ⚠ An insulated flask **ignites itself** and the rise is the
arithmetic (+322.45 K measured, +323.86 predicted, 50 J/K flask).

## ⚠ 7. AND THE INSTRUMENT AUDIT FOUND A FALSE CITATION FOUR MILESTONES OLD

`surface.ROASTING_A`'s pinning comment has ended *"validation/rate_ceiling.py
re-measures it"* since S1. **It did not** — `rate_ceiling` walks `net.reactions`
and a `SurfaceReaction` never becomes one. S4 found the identical fault about
`SOLID_STATE_REACTIONS` and added a panel; this table was left out, **and the
sentence claiming the check existed is why nobody looked.**
`rate_ceiling.surface_panel` reads it now, against the BIMOLECULAR ceiling (order
1 in one gas — M8's unit error avoided). Every pre-exponential there is below the
collision limit outright.

## 8. TWO SPLITS, AND ONLY ONE OF THEM WAS PLANNED

* **`carbothermic-reduction`** — five rows, four mechanisms (oxide reduction;
  carbide formation, where the carbon ends up IN the product; a phosphate needing
  a slag former; a sulfate whose sulfur is reduced rather than removed). Costs no
  route because none of the other four was credited.
* **`catalytic-gas-oxidation`** — found while RANKING, not while building. Three
  rows, three reactions, and only Deacon's is implemented. ⚠ **The near-miss:
  `sulfur_dioxide_oxidation` looks like it covers the contact-process row and does
  not — that template is the lead chamber's `SO2 + NO2 + H2O`. A template's NAME
  is not its SMARTS.** Zero headline effect and it removes a RANKING error:
  `ostwald-process` was two classes away, not one.

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ A LATTICE MAY REACT AND MAY NEVER BOIL — HALF CLOSED BY S10, AND THE
HALF LEFT IS NOW ONE SENTENCE.** S9 recorded this as one gap with two symptoms.
**The zinc retort DISTILS now** (0.040000 mol of vapour at 1400 K, condensing to
liquid at 1180.15 K and freezing at 692.68 K, neither temperature written
anywhere) because the sentence was about a `mineral_data` ENTRY, not about the
metal — and no engine code changed. What remains is thermite: **nothing caps the
temperature** (a 1 J/K flask reports 5469 K, above `T_MAX` = 5000, which bounds
RATE evaluation and not the state), and iron cannot make zinc's move because it is
a declared `solid_catalyst` AND thermite's solid product, so it would have to be
BOTH a lattice and a gas. **Engine queue item 1**, and it is worth ZERO routes.

**2. ⚠⚠ THE BURNER IS STILL ~50 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT.** The
crash is bounded; the thrashing is not. **Engine queue item 8.** It fires only at
rtol 1e-8, so nothing a player does reaches it.

**3. ⚠⚠ NO CURRENT BUDGET (M8).** Two electrode reactions in one cell divide
nothing. Selectivity washes out above ~2.7 V. Measured, pinned as a LIMIT.

**4. ⚠⚠ THE ION TABLE'S MIXED BASIS (M8, pre-existing).** dG survives it, dS does
not. Quote E_dec at 298 K; do NOT quote its temperature derivative and do NOT
read a cell's HEAT.

**5. ⚠⚠ 75 CATALOG ROWS CANNOT BE BALANCED (S7).** Reported, not fixed. One of
them is in the BOTH column and is inert. `tools/catalog.py`'s `validate` still
does not check it, so the corpus can grow another silently.

**6. ⚠⚠ THE ESTIMATORS CANNOT TELL A CIS ALKENE FROM A TRANS ONE (S7).**
dH = dG = 0.000 exactly for oleic/elaidic. Pinned by a test as a LIMIT.

**7. ⚠ `deacon_oxidation_rev` CROSSES THE BIMOLECULAR CEILING AT 1141 K**, the
coldest such row. Reported on the stated policy: it moves a CLOCK.

**8. ⚠ A SOLID DECOMPOSITION'S FORWARD CONSTANT CROSSES THE UNIMOLECULAR CEILING
AT 3710 K**, inside the RHS's 5000 K clamp. New in S4. ⚠ **S9 added five rows and
none of them crosses at any temperature** — `rate_ceiling` says so.

**9. ⚠ `detailed_balance`'s RATE CAP COMPARES A CATALYSED PRE-EXPONENTIAL AGAINST
A LIMIT NOT IN ITS UNITS**, so it would fire 10x too eagerly. It does not fire on
any catalysed template, pinned by a test.

**10. THE DEFAULT TOLERANCE, BOUNDED RATHER THAN OPEN.** ⚠ `tolerance_audit.py`
is a STANDING audit: run it after touching the RHS. Its three self-check examples
must come out OUTPUT IDENTICAL. ⚠ Its `QUOTABLE DIGITS MOVE` headline on
`oil_of_vitriol` is WRONG — engine queue item 6.

**11. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever. M10.

**11b. ⚠⚠ 103 CORPUS ROWS HAVE A NEGATIVE LIQUID HEAT CAPACITY (S10).** The
`CondensedProvider` fit window is a hardcoded 250–450 K and every caller takes
the default, so a species whose liquid range falls outside it is extrapolated —
worst carminic acid at **−21482 J/(mol K)**, plus 41 more swinging over 5x, and
it bites at BOTH ends (ethylene ~1574 at its 113.9 K melting point). ⚠ **A
negative Cp means heating the liquid COOLS it**, and S10 measured it reachable:
over 3.96 mol of liquid mercury gave a NEGATIVE TOTAL thermal mass, and mercury
had carried it since S4. **Two species curated by hand; the mechanism is
UNFIXED.** Measured inert on every example today. **Engine queue item 2.**

**12. ⚠ NUCLEATION, HALF modelled.** A solid can only grow where one already is.
⚠ **S9 leaned on the modelled half deliberately**: an exhausted furnace stops in
both directions, which is that gap stated rather than worked around.

**13. ⚠ LIQUID MERCURY IS 99.85% HELD IDEAL.** Named and bounded, not hidden.

**14. ⚠ THE FLAT COLUMN IS STILL FLAT, AND THAT IS CORRECT.** A species genuinely
absent from a sealed flask has an identically zero Jacobian column.

**15. ⚠ THE ELEMENT FLOOR'S SOLID HALF IS CURATED AND ITS GAS HALF IS STILL
REFUSED, WHICH IS THE SAME STATEMENT TWICE.** 33 compounds remain refused as bare
elements and none of them blocks a route on its own. ⚠ The one row the report
still lists (`gunpowder`) is there because `gunpowder-marker` is a four-fragment
COMPOSITION whose `[C]` fragment refuses — the `mineral` fallback is consulted per
whole species and not per fragment. A real inconsistency, and inert.

**16. ⚠ `iron-ii-oxide` AND `pyrite` ARE BOTH ONE SOURCE AWAY, AND EACH IS WORTH
+1.** FeO has no crystal Cp in CRC; pyrite has `Hfs` in WEBBOOK and `S0s` in
nothing. Both refusals follow rules worth keeping. Engine queue items 3 and 7.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's clamp is
`T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Twenty-one times now. ⚠ **AND THE SOLVER IS PART OF THE ARITHMETIC**
(M8): an arithmetic bound tells you whether a mechanism CAN go; only running it
tells you whether it can be INTEGRATED.
⚠⚠ **A REFUSAL'S SENTENCE IS A CLAIM ABOUT A NAMED THING — CHECK WHICH THING.**
S10's whole zinc half is one sentence, *a lattice may react and may never boil*,
turning out to be about a `mineral_data` ROW rather than about a metal. Two
sessions read it as physics. **This is the trap below, one level down.**
⚠⚠ **AND TWO SYMPTOMS CITING ONE SENTENCE ARE NOT NECESSARILY ONE GAP.** S9
paired the zinc retort with thermite's missing temperature cap. Splitting them cost
nothing and LOCATED the engine gap; keeping them together had hidden it for a
session, because the pair looked too big to scope.
⚠⚠ **THERMODYNAMIC CONCLUSIONS SURVIVE A PHASE CHANGE IN A PRODUCT; KINETIC ONES
NEED NOT.** S9's overblowing finding was written up as physics and was two derived
pre-exponentials racing; making the product a vapour moved one by 24x and the
effect reversed. **Ask what a claim rests on before quoting it as behaviour.**
⚠⚠ **ASK WHAT A FIT WAS ANCHORED ON, NOT WHETHER THE CHECK LOOKS FAMILIAR.**
"Boils at 1 atm" is NOT independent for Lee-Kesler, because omega is inverted at Tb
to make it pass — and IS independent for Alcock, whose fit was made 430 K below Tb
and never saw it. The same check, worthless one way and load-bearing the other.
⚠⚠ **A CORRELATION'S FIT WINDOW IS A DEFAULT ARGUMENT NOBODY OVERRIDES.**
`CondensedProvider.get(mol, T_lo=250.0, T_hi=450.0)` — and a LIQUID correlation
evaluated where there is no liquid returned a NEGATIVE heat capacity for four
sessions. ⚠ **But separate the wrong OUTPUT from the wrong INPUT before fixing
it**: 103 rows are negative and most of them have a Joback Tm/Tb that is itself
meaningless.
⚠⚠ **A SHARED PROVENANCE STRING GOES SILENTLY WRONG ON THE NEXT ADDITION.** Nine
curated Antoine rows stamped `NIST WebBook`; correct until a tenth came from
Alcock. **Same shape as S9's false citation**, and the fix is a per-entry override
with the default retained.
⚠ **CHECK WHETHER A NEW WRONGNESS IS A NEW CLASS OR A NEW MEMBER.** Zinc's
20 mol% aqueous solubility looks alarming until iodine (1.5e4x over) and sulfur
(1.1e8x) are measured on the same law. It JOINED a reported fragility.
⚠⚠ **A RECORDED REFUSAL CAN BE RIGHT ABOUT ITS MEASUREMENT AND WRONG ABOUT ITS
SCOPE.** S9's whole engine change is one rearrangement of an expression a refusal
had been standing in front of for five milestones — and half the reason recorded
beside that refusal was about a DIFFERENT algebraic form, which was already not
in use when it was written. **Read a refusal as two separate claims: the number,
and what the number is about.**
⚠⚠ **READ THE CATALOG ROW, NOT THE CLASS NAME.** S8 priced `ZnO + CO` and
declared the class blocked; the corpus row is `ZnO + C`, which is downhill above
1264 K and needed no engine work. And S9's own second split turned on
`sulfur_dioxide_oxidation` NOT being the reaction its name suggests. **A name is
not a mechanism, on either side of the audit.**
⚠⚠ **A COLUMN THAT ANSWERS A QUESTION CANNOT ANSWER THE NEXT ONE.** `ALONE`
could not ask whether the species price. `RUNNABLE` cannot ask whether the number
is RIGHT or whether the product is a GRAPH. **And neither can ask whether the
CREDIT under the ranking is real** — S9 found `ostwald-process` ranked one class
away on a credit it never had.
⚠⚠ **A CLASS IS A MECHANISM CLAIM, AND A SPLIT MAY LOWER THE HEADLINE.** S7's
split of `combustion` cost a template-ready route; S9's two cost nothing. Both
are correct; the difference is only whether the old credit was live.
⚠⚠ **A SPECIES JOB SHOULD FOLLOW THE TEMPLATE IT ENABLES, NOT LEAD IT.** S8
curated nine element solids for +14 species-ready and +0 on the intersection; S9
cashed five of the nine opportunities that created. The curation was right and
the ORDER cost a session.
⚠ **A BRIEF'S EXPECTED OUTCOME IS A HYPOTHESIS.** S4's said a re-label would be
reversed; running it both ways said keep. S1's asked for one mechanism and got
two. S5's named a layer and the measurement named another. S6's named a size.
M8's named a FAILURE that never came. S7's said the bare-element gap was the
cheapest item on the queue. **S9's brief said the reversible solid-gas term was
the plan's most valuable unscoped item and might be worth +4 — the +4 was right
and "unscoped" was worth about fifteen lines.**
⚠ **PREDICT THE NUMBER BEFORE YOU MEASURE IT.** S3 +2/+0; S4 +1/+1; S6 predicted
14 and measured 16; M8 three for three; S7 five for five; S9 four for four;
**S10 four for four, and all four were ZERO — which is the harder prediction to
make and the one worth making out loud.**
⚠ **VERIFY A CREDIT BY RUNNING IT, NOT BY READING THE CODE THAT WOULD RUN IT.**
Every S9 class went into a real `Vessel`; `pyrite-roasting` is what the check
exists to prevent.
⚠ **AND VERIFY A BIT-IDENTICAL CLAIM AGAINST THE EXAMPLE SET, NOT AN ARGUMENT.**
S9 claimed the five pre-S9 rows were untouched and then diffed
`examples/lime_cycle.py` and `examples/mercury_retort.py` byte for byte.
⚠ **A CONSTANT'S UNITS ARE WHAT MAKE ITS VALUE DEFENSIBLE.** S9's `REDUCTION_A`
is bounded by the HERTZ-KNUDSEN arrival rate at a crystal face, not by a
collision frequency in solution — and `mineral_data`'s `Vm_solid` is in **L/mol**,
which is a factor of 1000 in that check.
⚠ **AN ARRHENIUS PAIR IS NOT SEPARABLE.** Half a kinetic declaration is refused
in both tables now, because the defensible statement is always a TIME CONSTANT AT
A TEMPERATURE and never `A` or `Ea` alone.
⚠ **AN `inf` IS USUALLY THE WRONG BOUND, NOT A BOUND NEEDING SOFTENING.**
⚠ **A RELATIVE-DIFFERENCE TEST IS MEANINGLESS ON A COLUMN WHOSE CONVERGED VALUE
IS ZERO.**
⚠ **A NEW CREDIT MUST BE A FALLBACK BEFORE IT IS AN OVERRIDE.**
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS.** S2's harness invented a finding;
S1's coverage audit credited a route that cannot run; S3's report could not be
diffed; S4's rate-ceiling audit made a claim about a table it does not read; S6's
target column had been understating itself since M3; M8's new audit found a
pre-existing ion-table error; S7 found the coverage audit pricing a species the
engine refuses. S9 found a source comment CITING an audit check that had never
existed, and the citation is why nobody looked; **and S10's `game_gates` panel
INVENTED a 90 kJ/mol error by differencing a shift the engine had correctly
REFUSED, which no row before zinc could trigger.**
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS.
⚠ **A GENERATED FILE NOTHING READS IS THE ONE THAT ROTS.** Regenerate all three
catalog artefacts and check them across `PYTHONHASHSEED`.
⚠⚠ **AND A GENERATED FILE'S PROSE ROTS EXACTLY LIKE A HAND-WRITTEN ONE.** S8 was
caught by it; S9 found `catalog_coverage.py` still asserting in a comment that
"all three smelting routes are still blocked", which it had said since S1 and
which the same session's own work refuted. **Read the generated prose after
regenerating, not just the generated numbers.** ⚠ The root `README.md`'s coverage
table is NOT generated — S4 corrected it, S6 again, M8 again, S7 again, S9 again.
⚠ **A PHASE LABEL CARRIES A STANDARD STATE.** So does a BASIS.
⚠ **BDF IGNORES `jac_sparsity` THE MOMENT `jac` IS CALLABLE.**
⚠ Windows console is cp1252: **a warning glyph inside a `print()` kills a
script.** Docstrings fine, printed text ASCII. (TWENTY-FOUR sessions running —
S9 hit it in a scratch script and caught it before `validation/smelting.py`.)
⚠⚠ **`sed -i` REWRITES EVERY LINE ENDING IN A CRLF FILE, AND ON THIS MACHINE IT
ALSO FAILS OUTRIGHT IN THE SCRATCHPAD** ("invalid cross-device link"). This repo
is MIXED: markdown and `.psv` are CRLF, and so are `element_data.py`,
`solid_state.py`, `volatility.py`, `catalog_coverage.py`, `rate_ceiling.py`,
`gas_processes.py`, `template.py`, `reaction.py`, `synthesis.py`,
`thermochemistry.py`, `test_solid_state.py`, while `vessel.py`, `surface.py`,
`thermo.py`, `builder.py`, `constants.py`, `jacobian.py`, `test_surface.py` and
the newer `validation/*.py` are LF. **Read binary, detect `\r\n`, restore it on
write, and check `git diff --stat` after the first edit to any file** — a
whole-file rewrite shows up instantly as a huge insertion count. S7 and S9 each
used a ~40-line CRLF-preserving splice helper for every edit; it is worth
rebuilding.
⚠ **HEREDOCS EAT ESCAPES AND CHOKE ON A LARGE BLOCK CONTAINING QUOTES.** Write
the payload with the Write tool and splice it. ⚠ S9 also hit a Python one-liner
whose embedded Windows path ended in a backslash-quote.
⚠ **A GENERATOR CAN LEAK A `numpy` REPR INTO ITS OUTPUT.** Cast to `float`.
⚠ **DO NOT NAME A LOCAL `net` IN A SCRIPT THAT ALSO HAS A `net()` HELPER.** S9
shadowed it with an ndarray four panels in.
⚠ An em dash in a markdown anchor will not match a `--` you typed.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u`.

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
exactly the pre-M8 engine, bit for bit; **an all-positive `nu_gas` exactly the
pre-S9 solid-state term, bit for bit — `p ** 0` is exactly 1.0 including at
p = 0**; `SolidStateReaction.Ea is None` exactly M6's derived pair;
`SurfaceReaction.A is None` exactly the shared sulfide clock;
`BoundedJacobian` with its bound lifted exactly BDF's own differencing; the Born
term exactly zero in PURE water; the five pH values; SAVE_VERSION stores the
CONDITION, never the instant; every gaseous element reference state Hf = Gf = 0
EXACTLY; **a CONDENSED reference state's ideal-gas record is a MEASUREMENT and
must not be zero**; every METAL Hf = Gf = 0 EXACTLY on the solid basis; a
reference state its own database does not price at Hf = 0 is REFUSED; no mineral
pricing differently under the two providers; `ion_data` and `electrolyte` never
subtracted from each other; **a declared rate order may NEVER be reversible, and
that is now also why a REVERSIBLE solid-gas row's exponents are its
stoichiometry**; an `electrons` count may never carry declared orders; an
electrode template is a WHOLE CELL, charge balanced on both sides; the reverse of
an electrode reaction carries MINUS the work, so `dH_rev == -dH_fwd` exactly; an
IRREVERSIBLE surface row whose `ln K` is under +20 is REFUSED; a solid-state row
with no crystal on EITHER side is REFUSED; **an EXOTHERMIC solid-state row with
no declared kinetics is REFUSED, and a declared `Ea` below `dH` is REFUSED
because `max(Ea - dH, 0)` would break `k_f/k_r = K`**; **half an Arrhenius
declaration is REFUSED in both solid tables**; the four pre-S4 solid-state rows
take the raw `units` minimum, bit for bit; an element's `Hvap` is
Clausius-Clapeyron on the vapour-pressure curve `volatility` actually evaluates;
the reflux ratio is the ratio of two drain conductances out of one condenser; the
fragmentation SEARCH runs only after the greedy pass has been REFUSED; an ion is
never counted in the held-ideal flag; a rate CAP scales BOTH pre-exponentials by
one factor; a template that moves a hydrogen ATOM must collapse explicit Hs; a
declared catalyst is a CONSTANT OF THE MOTION; the tolerance audit's THREE
self-check examples come out byte-identical; **`COVERAGE_REPORT.md` and both
`derived/*.psv` come out byte-identical across `PYTHONHASHSEED` values**; the
`mineral` tier is a FALLBACK consulted only after all three providers refuse; a
dot-separated SMILES is a MIXTURE and is refused whether or not a fragment is
charged; `validation/jacobian_bound.py` panel 3 reads 0 clamped columns on every
vessel; **a lattice may REACT and may never DISSOLVE, BOIL or MELT — the fusion
law is still 407x wrong in both directions, and neither M6 nor S1–S10 nor M8
softened that by one digit** (⚠⚠ S10 did NOT weaken this: it moved ZINC out of the
lattice table, which is a statement about one entry. The rule over lattices is
untouched, and iron is the case that would need it changed — engine queue item 1);
`_CURATED_SOURCE.get(smi, _NIST)` is exactly the old shared stamp for all nine
pre-S10 Antoine rows; zinc's Antoine pair reproduces **Alcock's own published
log10 coefficients to four figures**, which is what says the conversion is
algebra; and **a curated liquid Cp must be POSITIVE across the species' whole
liquid range** — the check that had never been made.

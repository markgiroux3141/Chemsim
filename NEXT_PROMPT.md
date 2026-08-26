We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M8, M12, S1–S8 are DONE.**

# ⚠ THE BASELINE IS VERIFIED. DO NOT START WITH THE SUITE.

The last session ran the full suite THREE times. At the top, to clear M8's
unverified changes: **847 passed in 12:20**, exactly the 826 + 21 M8 predicted.
After S7: **866 passed in 12:46** (847 + S7's 19). After S8: **904 passed in 13:02** (866 + S8's 38).
⚠ **Two sessions running that hand forward a suite number they actually
measured.** Take it and spend the time on content.

```bash
python validation/gas_processes.py            # ⚠ S7's standing audit, ~1 min
python validation/corpus_balance.py           # ⚠ S7's other one, ~20 s. READ IT FIRST -- see below
python validation/catalog_coverage.py         # ⚠ READ THE 'BOTH' LINE: 24/173, ~15 s
python validation/game_gates.py               # ⚠ the element floor's own cross-check, seconds
python tools/build_route_index.py             # the artefact nothing reads
python validation/cell_potentials.py          # M8's standing audit, seconds
python validation/rate_ceiling.py             # M12's standing audit, seconds
python validation/jacobian_bound.py           # S5's standing audit, ~1 min
python -m ruff check src tests examples validation tools
python -m pytest -q                           # ~12.5 min. ONLY after touching src/
python validation/tolerance_audit.py          # ~8 min. ONLY after touching the RHS
```

⚠ **THE SUITE AND THE TOLERANCE AUDIT ARE MINUTES OF SATURATED CPU ON THE USER'S
OWN MACHINE.** Say what a long run will cost before starting one.
`examples/plate_column.py` alone is 12 minutes.

---

# ⚠⚠ START HERE: THE WORK QUEUE, RANKED AGAINST THREE BARS INSTEAD OF ONE

**S7's finding, and it still decides the session: `catalog_coverage`'s RUNNABLE
column has the same shape of fault the `ALONE` column had.** RUNNABLE asks
whether every species RESOLVES. It cannot ask two more questions, and both kill
entries at the top of its own table:

1. **is the row's PRODUCT a graph at all?** ⚠ Mechanised by S7 — a marker on the
   product side now excludes a route from RUNNABLE. `crosslinking` went +2 → +0.
2. **is the row BALANCEABLE?** ⚠ **NOT in the report at all** — it is in
   `validation/corpus_balance.py`. **75 of 367 testable rows cannot be balanced
   by any positive coefficient vector**, and EIGHT of them are on
   one-class-away routes the report still lists as runnable.
3. **is the NUMBER that comes back right?** Not mechanisable, and it is what took
   `isomerisation` — the report's top row — to zero.

**Here is the queue with all three bars applied.** Every class below is one class
away from a route that is species-ready, produces no marker, and can be balanced.
⚠ Nothing here is worth more than +1 except the one item that is blocked on
engine work, so **pick for the MECHANIC, and say which you are picking for.**

| class | its route | worth | what it is |
|---|---|---:|---|
| ⚠⚠ **`gas-solid-reduction`** | `copper-smelting`, `lead-smelting` | **+2** | **BLOCKED: an engine gap, measured by S8.** `MO(s) + CO(g) -> M(s) + CO2(g)` looks like four rows of `SURFACE_REACTIONS` and no code, and all four fail `LN_K_IRREVERSIBLE` — ln K 10.90 / 7.24 / 4.20 / −4.10 against a bar of 20. **The bound is not the problem**: a blast furnace's top gas contains CO because the reaction really is reversible. It needs a REVERSIBLE solid-gas term, which is M6's `p/K = n_A/n_B` measurement. ⚠ **Do not close it by lowering the bar.** See MILESTONES §S8 and `properties/surface.py`'s docstring |
| **`wacker-oxidation`** | `wacker-process` | +1 | `2 C2H4 + O2 -> 2 acetaldehyde`, and the copper(II) ion is written on BOTH sides of the row — a homogeneous catalyst, which is `library._maybe_catalyse`'s own case. Needs the electrolyte templates beside it for `[Cu+2]` to exist |
| **`metallothermic-reduction`** | `thermite` | +1 | `2 Al + Fe2O3 -> Al2O3 + 2 Fe`. ⚠⚠ **A NEW OPPORTUNITY S8 CREATED** and probably the best mechanic in the table: solid + solid -> solid + solid with no gas at all, so it is `solid_state.py`'s shape rather than `surface.py`'s, and dG is about −851 kJ/mol. **First measure whether `SolidStateArrays` accepts a row with ZERO gases** — every existing row evolves one, and the affinity quotient may need one |
| **`hydroformylation`** | `oxo-process` | +1 | `propene + CO + H2 -> butanal` over cobalt. ⚠ A NEW OPPORTUNITY S8 CREATED (it needed `cobalt`). A gas-phase template with a declared solid catalyst — `steam_reforming`'s exact shape |
| **`disproportionation-hydrolysis`** | `ostwald-process` | +1 | `3 NO2 + H2O -> 2 HNO3 + NO`. ⚠ A NEW OPPORTUNITY S8 CREATED (it needed `platinum`). **And the lead chamber already has both halves of the nitrogen cycle**, so this one lands next to chain 2 rather than on its own |
| **`carbothermic-reduction`** | `zinc-smelting` | +1 | `ZnO + C -> Zn + CO`. ⚠ A NEW OPPORTUNITY S8 CREATED. **⚠⚠ READ S8's zinc measurement first**: `ZnO + CO -> Zn + CO2` is UPHILL at +63.3 kJ/mol, and a real retort works because the zinc BOILS OFF at 1180 K. `mineral_data` holds zinc as a lattice with no vapour pressure, so the escape that makes the process work is not expressible — this may be `gas-solid-reduction`'s problem in a second costume |
| **`catalytic-air-oxidation`** | `p-xylene-oxidation` | +1 | ⚠ A NEW OPPORTUNITY S8 CREATED (it needed `cobalt`). ⚠⚠ **M5 REFUSED THIS CLASS** — its four rows are at least three mechanisms (liquid-phase radical autoxidation, Mars-van Krevelen over V2O5, an oxidative ring cleavage). **Split it before crediting it**, and only one of the four rows is runnable |
| **`molten-salt-electrolysis`** | `downs-cell` | +1 | ⚠ A NEW OPPORTUNITY S8 CREATED (it needed `sodium`). **A MELT is not a phase this project has** — M8's own named leftover, and it is engine work |
| **`oxidative-cleavage`** | `vanillin-lignin` | +1 | a C=C cleaved by an oxidant |
| **`skraup-cyclisation`** | `skraup-route` | +1 | aniline + acrolein -> quinoline; nitrobenzene is the oxidant AND is regenerated |
| **`direct-combination`** | `vermilion-route` | +1 | `Hg + S8 -> HgS`. ⚠ A LIQUID metal and a SOLID reagent making a LATTICE — neither `surface.py`'s shape (no gas) nor a template's (a lattice is not a graph) |
| `fischer-tropsch` | `fischer-tropsch` | +1 | `8 CO + 17 H2 -> octane + 8 H2O`, 25 slots. The Claus template proves 24 works — but read M8 §6 on the lump that was refused |
| `fermentation` | `abe-fermentation` | +1 | ⚠ **M5 REFUSED IT** as a metabolic NETWORK rather than a transformation. That refusal still stands |
| `separation` | `coal-tar-distillation` | +1 | ⚠ **M5 REFUSED IT**: a distillation is not a reaction class, and the feedstock has no graph |

⚠⚠ **AND THE EIGHT THE REPORT STILL PROMISES THAT THE BALANCE AUDIT KILLS.** Do
not start any of these without reading `corpus_balance.py`'s output on it:

| class the report ranks | route | the step that cannot balance |
|---|---|---|
| **`isomerisation` (still the report's TOP ROW)** | `hydrogenation-margarine` | step 2 `spurious` — an H2 in and none out |
| " | `starch-hydrolysis` | step 1 `atoms` |
| `metal-ion-aldehyde-oxidation` | `tollens-test` | step 1 `atoms` — ⚠ an S8 "opportunity" that the balance bar takes straight back |
| `pyrolysis` | `wood-distillation` | step 1 `atoms` — ⚠ likewise |
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

---

# THE REST OF THE QUEUE — THE ENGINE AND HONESTY ITEMS, RANKED

1. **⚠⚠ A REVERSIBLE SOLID-GAS TERM — S8's NAMED GAP, AND THE MOST VALUABLE
   ENGINE ITEM NOBODY HAS SCOPED.** `gas-solid-reduction` is the queue's only +2
   and it is blocked on this: `SurfaceArrays` is integrated FORWARD ONLY, and
   `surface.LN_K_IRREVERSIBLE` refuses all four of its rows at ln K 10.90 / 7.24
   / 4.20 / −4.10. ⚠ The obstacle is M6's measurement, not a missing feature:
   **mass action written on a solid AMOUNT settles at `p/K = n_A/n_B` rather
   than at unit activity**, so a reversible declaration on the existing term
   reaches a wrong equilibrium while looking like one that does not. What is
   needed is a term whose reverse uses the crystal's ACTIVITY (which is 1 for a
   pure solid) rather than its amount. ⚠⚠ **That is also `carbothermic-reduction`
   and probably `direct-combination`, so it is worth up to +4 rather than +2 —
   measure that before scoping it.** Read `properties/surface.py`'s closing
   section and `properties/solid_state.py`'s docstring together; they are the two
   halves of the argument.
   ⚠ **The bare-element gap that used to be item 1 here is DONE (S8)** — nine
   element solids curated, species-ready 63 → 77, intersection +0 exactly as
   predicted. What is left of it is 33 compounds still refused as bare elements,
   none of which blocks a route on its own.

2. **⚠ THE CIS/TRANS BLIND SPOT — A REAL DATA JOB WITH A REAL TRAP.** Benson (the
   RMG group set) has no cis correction, so oleic and elaidic acid come back with
   IDENTICAL Hf and Gf and the engine reports a confident 50:50 for a real ~5:1.
   ⚠ **The data exists and is not usable as it stands:** WEBBOOK has both liquid
   enthalpies, −764.8 and −769.0 kJ/mol, and that 4.2 kJ/mol gap agrees with
   Benson's own historical cis NNI term of 4.18 to 0.4% — **two independent
   sources**. But neither has an S0, so no Gf can be derived, and grafting
   Benson's original correction onto RMG-fitted group values **mixes two bases**,
   which is the trap `chemsim-benson-status` exists to name. ⚠ Worth ZERO routes
   today (the margarine row cannot balance either) — take it for the honesty, and
   say which you are doing. `test_the_cis_trans_pair_prices_at_exactly_zero`
   pins the limit; if you close it, that test SHOULD fail and be rewritten.

3. **⚠ THE CURRENT BUDGET — M8's OWN NAMED GAP, AND IT IS A LAYER 4 TERM.** Two
   electrode reactions in one cell divide nothing, so both run at full rate and
   activation selectivity washes out as the barrier floors at zero:
   k(brine)/k(water) is **4.76e+17 at 2.5 V, 5.94 at 3.0, 1.00 at 4.0**. The
   selective window here is ~2.2–2.7 V where a real chloralkali cell holds 99% at
   3 V and above. ⚠ Worth **ZERO new routes** — chloralkali already runs — so
   take it for the mechanic and say so.
   `test_the_activation_selectivity_washes_out_at_high_voltage` pins the gap; if
   you close it, that test SHOULD fail and be rewritten.

4. **⚠ S5's SIXTH INSTRUMENT FAULT, STILL OPEN AND STILL CHEAP.**
   `tolerance_audit.py` reports `QUOTABLE DIGITS MOVE, worst 99.85%` on
   `oil_of_vitriol`, and **that headline is wrong**: four of its five moved lines
   are the CREATED-MATTER residual and every one gets SMALLER, on rows
   `NEXT_SESSION.md` already carries as "NOT AN INVARIANT". **A
   relative-difference test is meaningless on a column whose converged value is
   zero.** `REPORT_ABS` exists for this and 2.9e-05 clears it. Picking the number
   owes its own predict-then-measure pass.

5. **Pyrite** — one mineral entry from `pyrite-roasting` running, and it is one of
   the **10 template-ready routes that cannot run**, so it is +1 on the
   intersection for one curated entry. Blocked on the same-database rule (`Hfs`
   in WEBBOOK, `S0s` in nothing), which is a rule worth keeping, so this needs a
   SOURCE and not a workaround.

6. **⚠⚠ THE BURNER — THE LIVE FRAGILITY, STILL DEMOTED AND STILL NOT DISMISSED.**
   **53 s at rtol 1e-8 against 0.8 s at the default.** S5 bounded the CRASH and
   explicitly did not bound the THRASHING. BDF is struggling with a liquid layer
   holding **1e-29 mol**, which `LAYER_REABSORB` drains toward zero without ever
   reaching it. **The question nobody has asked is whether a layer below
   `LAYER_EPS` should be *merged discretely* at a step boundary rather than
   drained continuously for ever.** ⚠ `merge_phases` already does exactly that at
   the `run` boundary — so this may be a matter of WHEN IT IS CALLED, not of a
   new mechanic. **Measure the layer-2 inventory over the failing run before
   designing anything.** It fires only at rtol 1e-8, so nothing a player does
   reaches it.

7. **THE CORPUS BALANCE BACKLOG — 75 ROWS, AND IT IS NOT A TO-DO LIST.** S7 built
   the check and deliberately fixed nothing, on the `diels-alder-route`
   precedent: inventing chemistry inside an audit corpus is not allowed. ⚠ But
   **17 of the 75 are `spurious`** — a reagent written as consumed that is
   really a catalyst — and those are the cheapest and least inventive to correct,
   because the fix is to put the species on both sides of the row it is already
   on one side of. ⚠ Read `corpus_balance.py`'s classification before touching
   any of them, and note that `tools/catalog.py`'s `validate` still does NOT
   check balance, so the corpus can grow another one silently.

8. **⚠ `hydrolysis` — AND READ S3's LANDMINE FIRST.** It unlocks **exactly ONE
   route alone, `vitriol-distillation`**, and that route's step 1 reads
   `-> iron-ii-OXIDE` while the engine makes HEMATITE. The whole standalone
   payoff is a route carrying a step whose product the engine does not make.
   ⚠ S3 and S4 disagree about what to do with such a row — read §S3's "which one
   is WRONG" check before deciding.

9. **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
   re-scope before scheduling)**, **M9 (polymers, 12 routes)**, **M10 (the site
   balance S1 did not build, 8 routes)**, **M11 (the unpriceable families, 16
   routes, and 10 of them need ONE boiling point each)**, and
   **`molten-salt-electrolysis`** (a MELT is not a phase this project has).

10. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
    the *deposition-needs-a-seed* half into a real bound in
    `SolidStateArrays.units`. What is still not expressible is a solid appearing
    from NO solid — `hydride-thermal-deposition` (`arsine -> arsenic + hydrogen`)
    is still a mechanism gap for that reason.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§S8, §S7, §M8, §S1, §S3, §S4, §S5 and §S6 are
  the ones to read**: S8 did a job this file had called "cheapest" for two
  sessions and measured it at +0 on the number that counts, then had the +2 it was
  for refused by the engine's own bound, S7 measured the queue's top two rows at
  ZERO and split a class in a way that LOWERED the headline, M8's brief predicted the wrong failure AND named
  a class that split under its own row check, S1's brief asked for one mechanism
  and the arithmetic said two, S3 found the instrument's own OUTPUT was not
  diffable, S4's brief said to reverse a re-label and the arithmetic said keep,
  **S5's brief named the wrong LAYER**, and **S6's brief handed it a number that
  was wrong.**
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1, 86 is S2, 87 is
  S3, 88 is S4, 89 is S5, 90 is S6, 91 is M8, 92 is S7, 93 is S8.**
NEXT_SESSION.md — the invariants table at the bottom is the contract, and S7
  and S8 each added a block to it. ⚠ Read the two warnings above it before
  trusting any row, and note that one S7 row is a LIMIT to remove rather than an
  invariant to keep.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **S7's split of
  `combustion`**, M8's of `electrolysis`, S3's of `thermal-decomposition` and
  S4's decision NOT to un-split `roasting-to-metal`; plus
  `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-gas-processes,
  chemsim-corpus-balance, chemsim-element-solids, chemsim-electrochemistry,
  chemsim-species-ready-minerals, chemsim-coverage-catalog,
  chemsim-element-floor and chemsim-generated-artefacts.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 43 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, a catalyst you have to actually put in
the flask, a route that nothing declares, a Jacobian that cannot be probed outside
its own state, a dial that decomposes things in the order their chemistry says
they should, and **four inorganic gas processes whose whole behaviour is their
reversibility**. `SAVE_VERSION` is **5**.
Coverage: **43/224 classes**, **43 templates**, **34/173 template-ready**,
**77/173 species-ready** — and ⚠⚠ **24/173 BOTH, which is the only one of the
three a route can be judged on.**

---

# ⚠⚠ WHAT S8 TURNED OUT TO BE: +14 SPECIES-READY, +0 ON THE NUMBER THAT COUNTS

**Both halves were predicted before the work was done, and both came out.**
Nine element solids curated, two reference entropies added to `element_data`, no
new templates, and the +2 the curation was FOR turned out to be an engine gap.

| | before | after |
|---|---:|---:|
| routes species-ready | 63 / 173 | **77 / 173** |
| ... of them carried by a lattice | 14 | **28** |
| compounds refused | 455 | **444** |
| ⚠⚠ **routes BOTH — the one to quote** | **24** | **24** |

## ⚠⚠ 1. "THE CHEAPEST ITEM ON THE QUEUE" WAS WORTH ZERO, AND S7 SAID SO FIRST

This file called the bare-element gap the cheapest item available for two
sessions. S7 predicted +0 on the intersection by reading two of the report's own
lists against each other; **S8 did the work and measured +0.** None of the 15
routes blocked only by a bare element is template-ready.

⚠ What it buys is a MULTIPLIER, and the queue is where it shows:
`gas-solid-reduction` went 1 → 2 runnable; `catalytic-air-oxidation`,
`carbothermic-reduction`, `metal-ion-aldehyde-oxidation`,
`molten-salt-electrolysis` and `pyrolysis` each went 0 → 1; and
`disproportionation-hydrolysis`, `hydroformylation` and
`metallothermic-reduction` appeared in the table for the first time. **Nine new
entries, of which seven survive the balance bar** — `tollens-test` and
`wood-distillation` are both taken straight back by it.

**The ordering lesson: species work should FOLLOW the template it enables, not
lead it.**

## 2. THE CURATION, AND THE LAYERING QUESTION S6 LEFT OPEN

`cobalt`, `silver`, `platinum`, `palladium`, `lead`, `aluminium`, `sodium`,
`zinc`, `carbon-graphite` — in `mineral_data`, SOLID basis, `ions=()`,
`Hf = Gf = 0` by definition. **No new machinery**: S1 had built the shape for
iron, nickel and copper.

⚠ **THE ANSWER IS IN THE TYPE, NOT THE MODULE NAME.** `element_data`'s record is
on the IDEAL-GAS basis and the ideal-gas record for `[Fe]` is the ATOM at +416
kJ/mol, so a solid-basis zero belongs in the solid-basis module.
`element_data.REFERENCE_STATES` still carries the S0 the Gf derivation consumes —
and **two were missing, Pt and Pd**, so that file had to be touched anyway. Both
regenerations are purely additive.

⚠ **THE LIST WAS CALLED `METALS` AND THE NAME WAS WRONG BY ONE ROW.**
`carbon-graphite` is a COVALENT lattice. Renamed `ELEMENT_SOLIDS`, because an
exception was the only alternative and every property the entry needs is about
the REPRESENTATION rather than the bonding.
⚠ And the definitional-zero check FIRED: **tin is absent** because CRC's row for
7440-31-5 is GREY tin at Hfs = −2.1 kJ/mol against a white-tin reference state.

⚠ **VERIFIED BY RUNNING** — all nine charged into a real `Vessel` at 800 K under
air, held to twelve figures over 600 s, `conservation_report` empty. And the
ideal-gas refusal is not softened by one digit.

## ⚠⚠ 3. `gas-solid-reduction` IS REFUSED, AND THE REFUSAL IS THE CHEMISTRY

The only +2 on the queue. `MO(s) + CO(g) -> M(s) + CO2(g)` is the same shape as a
roast, so it looked like four rows of `SURFACE_REACTIONS` and no code. **All four
fail `LN_K_IRREVERSIBLE`**, priced off this project's own tables at each row's own
furnace temperature:

    tenorite + CO  -> copper  + CO2    dG -127.72 kJ/mol   ln K  10.90 @ 1500 K
    litharge + CO  -> lead    + CO2    dG  -68.31          ln K   7.24 @ 1400 K
    hematite + 3CO -> 2 iron  + 3CO2   dG  -29.48          ln K   4.20 @ 1300 K
    zincite  + CO  -> zinc    + CO2    dG  +63.31          ln K  -4.10 @ 1400 K

⚠⚠ **THE BOUND IS NOT THE PROBLEM.** A blast furnace's top gas still contains CO
because these reductions really are reversible — the CO/CO2 ratio over an oxide
is the equilibrium a furnace is designed around. The zinc row is not even
downhill; a real retort works because the zinc **boils off at 1180 K**, which is
product removal, and `mineral_data` holds zinc as a lattice with no vapour
pressure so that escape is not expressible either.

⚠ For contrast, every declared roasting row sits **above ln K 60** at its own
temperature. The bar is not unreachable, which is what makes these four a
statement about chemistry rather than about a constant.

## ⚠ 4. NO TEMPLATE WAS WRITTEN, AND THAT WAS THE RIGHT ANSWER

The queue's only +2 needs engine work and every alternative is +1. S7's lesson is
that the ranking lies, so the session spent itself measuring which +1s are real
rather than taking one at random. **The queue at the top of this file is now
ranked against three bars instead of one; the next session picks off it.**

---

# ⚠⚠ WHAT S7 TURNED OUT TO BE: +4 ON THE INTERSECTION, AND TWO NEW INSTRUMENTS

**+5 classes (38 → 43 of 224), +3 template-ready (31 → 34), +4 RUNNABLE
(20 → 24)** — the largest single-session move the intersection has had, against
M8's +3. Five templates, three bundles, **no Layer 3 or Layer 4 code**, one
refusal widened in Layer 1.

⚠ **All five coverage numbers were PREDICTED before the audit was run and all
five came out exactly** (43/224, 43, 34, 24, and species-ready holding at 65
before the refusal was widened; the refusal's cost was predicted at "≤4 routes
and 0 in the BOTH column" and measured at 2 and 0).

| what | measured |
|---|---|
| water-gas shift, 1 h | 10.4% at 500 K, **81.3% at 620 K**, 73.3% at 700, 55.6% at 900 |
| steam reforming, 1 h | 0.01% at 700 K, **36.1% at 1300 K** |
| ... same 1100 K flask, thinned | **18.6% at 54 bar → 73.5% at 0.63 bar** |
| Deacon, 10 s / 1 h | 14.8/70.7% at 400 K, **90.6/91.2% at 600**, 84.6/84.6% at 700 |
| Claus, 0.20 mol H2S | 50.0% at 0.05 mol O2, **100.0% at 0.10**, 93.7% at 0.30 |

## ⚠⚠ 1. THREE OF THE FOUR ARE INTERESTING ONLY BECAUSE THEY ARE REVERSIBLE

Every equilibrium came out at its textbook value off this project's own tables
BEFORE a template existed — dH −41.15 against a book −41.2 for the shift, +206.2
against +206 for the reformer, −114.4 against −114.5 for Deacon. What the
templates buy is behaviour NOBODY DECLARED: the shift gets worse when heated (two
reactors, hot then cold); the reformer is impossible until ~900 K and is the one
gas equilibrium here that PRESSURE HURTS (two moles in, four out); Deacon's
ceiling and rate move in opposite directions with T and cross between 600 and
700 K, which is the entire industrial history of the process.

⚠ And the Claus flask recovers **100.0%** at exactly the stoichiometric air rate
and less on either side, because burning one third of the H2S is what leaves the
2:1 ratio the second template wants. **Neither Claus template knows the other
exists.**

## ⚠⚠ 2. THE QUEUE'S TOP TWO ROWS WERE MEASURED AT ZERO BEFORE BEING COSTED

See the top of this file. `isomerisation` (+3/+2) is three rows and three
mechanisms, each failing its own way; `crosslinking` (+2/+2) has two products
with no chemistry behind them, one of them spelled `CC(C)=CC.S1SSSSSSS1` — **its
own two reactants written side by side.** That last measurement is what closed a
Layer 1 hole (§4).

## ⚠⚠ 3. `combustion` WAS AN OUTCOME LABEL — AND THE SPLIT LOWERED THE HEADLINE

Six rows, **five mechanisms**, credited to `sulfur_combustion` since M1 while
that template's SMARTS (`S8 + 8 O2 -> 8 SO2`) fires on two of them. The match-head
row is not combustion at all: a solid oxidiser hands its oxygen to a solid fuel
on friction, with no air and no flame until after it goes.
⚠⚠ **`match-chemistry` loses template-ready for it — the first split in this
project whose measured headline effect is NEGATIVE.** It was never species-ready,
so the intersection is untouched, and **a split whose effect is negative is a
split doing its job.**

## ⚠⚠ 4. A NEUTRAL MULTI-FRAGMENT SMILES WAS PRICED, AND THE RECORDED REASON WAS FALSE

`thermochemistry` refused a dot-separated SMILES only when a fragment carried
CHARGE, on the recorded grounds that *"nothing in this project produces one, so
refusing it would widen the blast radius for no measured gain."* The catalog
carries **eleven**, and Joback prices `CC(C)=CC.S1SSSSSSS1` at **+273.70 against
the +51.59 its own two parts sum to.** ⚠ **In an ideal gas that sum is an
IDENTITY, not an estimate** — there are no intermolecular interactions. Benson
honours it (three of five at +0.00); Joback has a constant term and does not.
⚠ And `catalog_coverage` was disagreeing with the provider it audits: it treated
any dot as ionic and priced fragment-by-fragment, so all nine kept resolving
after the engine stopped. Right for a salt, wrong for a neutral mixture.

## ⚠⚠ 5. NOTHING HAD EVER CHECKED THAT A CATALOG ROW BALANCES

`validation/corpus_balance.py`, and the question is not "does it balance as
written" — the corpus carries no coefficients on purpose — but **does a strictly
POSITIVE coefficient vector exist**, an LP over the element-and-charge matrix.
**75 of 367 testable rows do not:** 17 `spurious`, 1 `charge`, 57 `atoms`. ⚠ It
touches the headline exactly once — `perkin-route` step 1, INERT because
`perkin_condensation`'s SMARTS never mentions the base it consumes on paper.

## ⚠ 6. AND THE RATE-CEILING AUDIT FOUND A ROW ON ITS FIRST RUN

`deacon_oxidation_rev` crosses the bimolecular ceiling at **1141 K**, the coldest
of the high-order reverse rows. Reported, not guarded, on the policy ammonia's
1335 K row already sits under: the cap scales both pre-exponentials, so it moves
a CLOCK and not an equilibrium. ⚠ And the crossing temperature is not a physical
statement for such a row — a FOURTH-order constant in L^3/(mol^3 s) against a
ceiling in L/(mol s) is M8's unit error.

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ THE BURNER IS STILL 53 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT.** The
crash is bounded; the thrashing is not. **Queue item 6.** It fires only at rtol
1e-8, so nothing a player does reaches it.

**2. ⚠⚠ NO CURRENT BUDGET (M8).** Two electrode reactions in one cell divide
nothing, so every reaction the cell clears runs at its own full rate at once.
Selectivity washes out above ~2.7 V. Measured, pinned by a test as a LIMIT.

**3. ⚠⚠ THE ION TABLE'S MIXED BASIS (M8, pre-existing).** dG survives it, dS does
not. Quote E_dec at 298 K; do NOT quote its temperature derivative and do NOT
read a cell's HEAT.

**4. ⚠⚠ NEW IN S7: 75 CATALOG ROWS CANNOT BE BALANCED.** Reported, not fixed.
One of them is in the BOTH column and is inert. `tools/catalog.py`'s `validate`
still does not check it, so the corpus can grow another silently.

**5. ⚠⚠ NEW IN S7: THE ESTIMATORS CANNOT TELL A CIS ALKENE FROM A TRANS ONE.**
dH = dG = 0.000 exactly for oleic/elaidic. Any future template on a
double-bond geometry reports a confident 50:50. Pinned by a test as a LIMIT.

**6. ⚠ `deacon_oxidation_rev` CROSSES THE BIMOLECULAR CEILING AT 1141 K**, the
coldest such row. Reported on the stated policy: it moves a CLOCK.

**7. ⚠ A SOLID DECOMPOSITION'S FORWARD CONSTANT CROSSES THE UNIMOLECULAR CEILING
AT 3710 K**, inside the RHS's 5000 K clamp. New in S4.

**8. ⚠ `detailed_balance`'s RATE CAP COMPARES A CATALYSED PRE-EXPONENTIAL AGAINST
A LIMIT NOT IN ITS UNITS**, so it would fire 10x too eagerly. It does not fire on
any catalysed template, pinned by a test.

**9. THE DEFAULT TOLERANCE, BOUNDED RATHER THAN OPEN.** ⚠ `tolerance_audit.py` is
a STANDING audit: run it after touching the RHS. Its three self-check examples
must come out OUTPUT IDENTICAL. ⚠ Its `QUOTABLE DIGITS MOVE` headline on
`oil_of_vitriol` is WRONG — queue item 4.

**10. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever. M10.

**11. ⚠ NUCLEATION, HALF modelled.** A solid can only grow where one already is.

**12. ⚠ LIQUID MERCURY IS 99.85% HELD IDEAL.** Named and bounded, not hidden.

**13. ⚠ THE FLAT COLUMN IS STILL FLAT, AND THAT IS CORRECT.** A species genuinely
absent from a sealed flask has an identically zero Jacobian column.

**14. ⚠ THE ELEMENT FLOOR'S SOLID HALF IS CURATED AND ITS GAS HALF IS STILL
REFUSED, WHICH IS THE SAME STATEMENT TWICE.** S8 curated nine element solids into
`mineral_data`; `thermo.get("[C]")` still refuses, because the ideal-gas record
for `[C]` is the carbon ATOM at Gf +671 kJ/mol. 33 compounds remain refused as
bare elements and none of them blocks a route on its own. ⚠ The one row the
report still lists (`gunpowder`) is there because `gunpowder-marker` is a
four-fragment COMPOSITION whose `[C]` fragment refuses — the `mineral` fallback
is consulted per whole species and not per fragment. A real inconsistency, and
inert, because that route's step 2 cannot be balanced either.

**15. ⚠⚠ NEW IN S8: `gas-solid-reduction` CANNOT BE EXPRESSED.** Two
species-ready routes (`copper-smelting`, `lead-smelting`) wait on a REVERSIBLE
solid-gas term. Measured, refused, and the four ln K values are pinned by a
test so the refusal cannot quietly become an acceptance. Queue item 1.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's clamp is
`T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Twenty times now. ⚠ **AND THE SOLVER IS PART OF THE ARITHMETIC**
(M8): an arithmetic bound tells you whether a mechanism CAN go; only running it
tells you whether it can be INTEGRATED.
⚠⚠ **A COLUMN THAT ANSWERS A QUESTION CANNOT ANSWER THE NEXT ONE.** `ALONE`
could not ask whether the species price. `RUNNABLE` cannot ask whether the number
is RIGHT or whether the product is a GRAPH. **S7's two top-of-queue rows failed
on exactly those, and neither failure was visible in the report.** Every column
this project adds should be read as "and what can it still not see?"
⚠⚠ **A RECORDED MEASUREMENT IS A CLAIM ABOUT A PAST STATE OF THE CODE, AND IT
CAN BE WRONG ABOUT ITS OWN SUBJECT.** S5: four of five recorded triggers had
stopped firing. S6: a measured number and a list of ids, both wrong. M8: the
greedy curve's top row was worth a third of its claim. **S7: a docstring's stated
reason for a carve-out ("nothing in this project produces one") was false about
its own corpus by eleven, and a bundle's docstring still described behaviour S1
had removed.** Read the claim, then check it.
⚠⚠ **A CLASS IS A MECHANISM CLAIM, AND A SPLIT MAY LOWER THE HEADLINE.** S7's
split of `combustion` cost a template-ready route. That is what a correct split
looks like when the old credit was false.
⚠⚠ **A SPECIES JOB SHOULD FOLLOW THE TEMPLATE IT ENABLES, NOT LEAD IT.** S8
curated nine element solids for +14 species-ready and +0 on the intersection, and
the +2 it was for turned out to need engine work. The curation was still right —
it created nine new entries in the queue — but done in the other order it would
have been +2 on the day.
⚠ **A BRIEF'S EXPECTED OUTCOME IS A HYPOTHESIS.** S4's said a re-label would be
reversed; running it both ways said keep. S1's asked for one mechanism and got
two. S5's named a layer and the measurement named another. S6's named a size.
M8's named a FAILURE that never came. **S7's said the bare-element gap was the
cheapest item on the queue, and the measurement said it is worth zero alone.**
**Run the number for the option you are not taking.**
⚠ **PREDICT THE NUMBER BEFORE YOU MEASURE IT.** S3 +2/+0; S4 +1/+1; S6 predicted
14 and measured 16; M8 predicted three numbers and got three. **S7 predicted five
and got five, which is what makes the sixth — the Deacon timescale, predicted at
minutes and measured at ten seconds — worth reading.**
⚠ **VERIFY A CREDIT BY RUNNING IT, NOT BY READING THE CODE THAT WOULD RUN IT.**
Every S7 class went into a real `Vessel`; `pyrite-roasting` is what the check
exists to prevent.
⚠ **AND VERIFY A BIT-IDENTICAL CLAIM AGAINST THE EXAMPLE SET, NOT AN ARGUMENT.**
⚠ **READ THE PRODUCT SMILES OF A NEW TEMPLATE.** S7's water-gas shift first came
out as `O=C=[O+]`, because the CO's `[O+]` was never neutralised. Second time
that has been the catch (see `sulfur_dioxide_oxidation`).
⚠ **A CONSTANT'S UNITS ARE WHAT MAKE ITS VALUE DEFENSIBLE.** A fifth-order
pre-exponential is not a collision frequency, and neither is a fourth-order rate
constant comparable to a bimolecular ceiling.
⚠ **AN `inf` IS USUALLY THE WRONG BOUND, NOT A BOUND NEEDING SOFTENING.**
⚠ **A RELATIVE-DIFFERENCE TEST IS MEANINGLESS ON A COLUMN WHOSE CONVERGED VALUE
IS ZERO.**
⚠ **A NEW CREDIT MUST BE A FALLBACK BEFORE IT IS AN OVERRIDE.**
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS.** S2's harness invented a finding;
S1's coverage audit credited a route that cannot run; S3's report could not be
diffed; S4's rate-ceiling audit made a claim about a table it does not read;
S6's target column had been understating itself since M3; M8's new audit found a
pre-existing ion-table error. **S7 found the coverage audit pricing a species the
engine refuses, and the corpus validator never checking that a row balances.**
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS.
⚠ **A GENERATED FILE NOTHING READS IS THE ONE THAT ROTS.** Regenerate all three
catalog artefacts and check them across `PYTHONHASHSEED`.
⚠⚠ **AND A GENERATED FILE'S PROSE ROTS EXACTLY LIKE A HAND-WRITTEN ONE.** S8
closed the bare-element gap and `COVERAGE_REPORT.md` then read "33 compounds are
still refused ... **it is not closed**" over a table with ONE row in it, still
naming Zn(s), Ag(s) and C(graphite) as the examples of what was missing — all
three curated an hour earlier. The NUMBER regenerated; the sentence around it was
hardcoded in `catalog_coverage.py`. **Read the generated prose after
regenerating, not just the generated numbers.** ⚠ The root `README.md`'s
coverage table is NOT generated — S4 corrected it, S6 again, M8 again, S7 again.
⚠ **A PHASE LABEL CARRIES A STANDARD STATE.** So does a BASIS.
⚠ **BDF IGNORES `jac_sparsity` THE MOMENT `jac` IS CALLABLE.**
⚠ Windows console is cp1252: **a warning glyph inside a `print()` kills a
script.** Docstrings fine, printed text ASCII. (TWENTY-THREE sessions running —
S7 caught one in `validation/gas_processes.py` before the first run.)
⚠⚠ **`sed -i` REWRITES EVERY LINE ENDING IN A CRLF FILE, AND ON THIS MACHINE IT
ALSO FAILS OUTRIGHT IN THE SCRATCHPAD** ("invalid cross-device link"). This repo
is MIXED: markdown and `.psv` are CRLF, and so are `element_data.py`,
`solid_state.py`, `volatility.py`, `catalog_coverage.py`, `template.py`,
`reaction.py`, `synthesis.py`, `thermochemistry.py`, `rate_ceiling.py`, while
`vessel.py`, `surface.py`, `thermo.py`, `builder.py`, `constants.py`,
`jacobian.py` and the newer `validation/*.py` are LF. **Read binary, detect
`\r\n`, restore it on write, and check `git diff --stat` after the first edit to
any file** — a whole-file rewrite shows up instantly as a huge insertion count.
S7 used a 40-line CRLF-preserving splice helper for every edit and it is worth
rebuilding.
⚠ **HEREDOCS EAT ESCAPES AND CHOKE ON A LARGE BLOCK CONTAINING QUOTES.** S7 hit
both: a `\\` in a SMILES became `\` (SyntaxWarning), and a 100-line block with
apostrophes killed the shell outright. Write the payload with the Write tool and
splice it.
⚠ **A GENERATOR CAN LEAK A `numpy` REPR INTO ITS OUTPUT.** Cast to `float`.
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
exactly the pre-M8 engine, bit for bit; `BoundedJacobian` with its bound lifted
exactly BDF's own differencing; the Born term exactly zero in PURE water; the
five pH values; SAVE_VERSION stores the CONDITION, never the instant; every
gaseous element reference state Hf = Gf = 0 EXACTLY; **a CONDENSED reference
state's ideal-gas record is a MEASUREMENT and must not be zero**; every METAL
Hf = Gf = 0 EXACTLY on the solid basis; a reference state its own database does
not price at Hf = 0 is REFUSED; no mineral pricing differently under the two
providers; `ion_data` and `electrolyte` never subtracted from each other; **a
declared rate order may NEVER be reversible, and that holds at twenty-four slots
as well as at nine**; an `electrons` count may never carry declared orders; an
electrode template is a WHOLE CELL, charge balanced on both sides; the reverse of
an electrode reaction carries MINUS the work, so `dH_rev == -dH_fwd` exactly; a
surface row whose `ln K` is under +20 is REFUSED; a solid-state row with no
crystal on EITHER side is REFUSED; the four pre-S4 solid-state rows take the raw
`units` minimum, bit for bit; an element's `Hvap` is Clausius-Clapeyron on the
vapour-pressure curve `volatility` actually evaluates; the reflux ratio is the
ratio of two drain conductances out of one condenser; the fragmentation SEARCH
runs only after the greedy pass has been REFUSED; an ion is never counted in the
held-ideal flag; a rate CAP scales BOTH pre-exponentials by one factor; a
template that moves a hydrogen ATOM must collapse explicit Hs; a declared
catalyst is a CONSTANT OF THE MOTION; the tolerance audit's THREE self-check
examples come out byte-identical; **`COVERAGE_REPORT.md` and both `derived/*.psv`
come out byte-identical across `PYTHONHASHSEED` values**; the `mineral` tier is a
FALLBACK consulted only after all three providers refuse; **a dot-separated
SMILES is a MIXTURE and is refused whether or not a fragment is charged — the
ideal-gas record for one IS the sum of its fragments', which is an identity**;
`validation/jacobian_bound.py` panel 3 reads 0 clamped columns on every vessel;
**a lattice may REACT and may never DISSOLVE — the fusion law is still 407x wrong
in both directions, and neither M6 nor S1–S7 nor M8 softened that by one digit.**

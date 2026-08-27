We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M8, M12, S1–S13, G1 and G2 are DONE.**

⚠⚠⚠ **THE PLAN CHANGED ON 2026-08-27 AND THE ARC IS THE G-SERIES.** The catalog
is a measuring instrument and was being read as a specification; the goal is a
connected tech tree a player can walk from natural materials. **Read MILESTONES
§ THE G-SERIES.** Coverage is DEFERRED to a C-series, not cancelled.

# ⚠ THE BASELINE IS MEASURED. DO NOT START WITH THE SUITE.

**G2 RAN THE WHOLE SUITE AT THE END AND MEASURED 995 PASSED / 0 FAILED IN
22:06.** Take that number and spend the time on content. ⚠ It was run AFTER
every `src/` edit — fifth session running that is true. (965 at S13; the +30 are
G1's 9 and G2's 21.)

⚠⚠⚠ **AND IT CORRECTS S13's OWN EXPLANATION OF THE CLOCK. THE SUITE REALLY IS
~8 MINUTES SLOWER THAN IT WAS AT S12, AND IT IS NOT CONTENTION.** S13 measured
21:36 against S12's 13:20 and wrote *"the 21:36 against S12's 13:20 is
CONTENTION, not the suite getting slower: S13 ran examples in another process at
the same time."* **This run had NOTHING else on the CPU and came out at 22:06** —
within 30 seconds of S13's supposedly-contended figure. And the 30 tests this
session added are measured separately at **47 s combined**
(`test_dropping_funnel` 35.1 s, `test_ring_deactivation` 12.4 s), so they account
for about one of the eight minutes.

⚠ **THE CAUSE IS NOT MEASURED AND SHOULD NOT BE ASSERTED.** The likeliest
candidate is the only large thing that changed between S12 and S13 — the
measured-physical table going from 37 species to 1239, which moved every
example's volatility and therefore every trajectory's stiffness — but **nobody
has bisected it**, and a plausible cause is not a measured one. ⚠⚠ **A ONE-POINT
WALL-CLOCK ATTRIBUTION IS NOT A MEASUREMENT**: the honest correction is that the
contention explanation is REFUTED, not that the data table is convicted. If the
suite's cost matters to a future session, `pytest --durations=25` is the probe
and it has never been run here.

⚠ **NEITHER G1 NOR G2 TOUCHED THE RHS OR A DATA TABLE**, so `tolerance_audit.py`
was not owed and was NOT re-run. Its last measured state is S13's and every
warning in §S13 about it still stands.

```bash
python validation/dropwise.py                  # ⚠ G1's, 78 s. NEW -- read panels 1-3 and 5
python validation/ring_deactivation.py         # ⚠ G2's, ~25 s. NEW -- read panel 3
python validation/boiling_points.py            # S13's, 2 s. READ PANEL 2
python validation/skraup.py                    # S12's, ~10 s
python validation/smelting.py                  # S9's, ~1 min
python validation/hydroformylation.py          # S11's, ~1 min
python validation/wacker.py                    # S11's other one, ~1 min
python validation/gas_processes.py             # S7's, ~1 min
python validation/corpus_balance.py            # S7's other one, ~20 s. READ IT before picking
python validation/catalog_coverage.py          # ⚠ READ THE 'BOTH' LINE: 31/173, ~15 s
python validation/physical_estimation.py       # S13 took its panel 3 to n=254
python validation/game_gates.py                # the element floor's cross-check, seconds
python tools/build_route_index.py              # the artefact nothing reads
python validation/cell_potentials.py           # M8's standing audit, seconds
python validation/rate_ceiling.py              # ⚠ G2 added TWO NETWORKS to it
python validation/jacobian_bound.py            # S5's standing audit, ~1 min
python -m ruff check src tests examples validation tools
python -m pytest -q                            # ~14–25 min. ONLY after touching src/
python validation/tolerance_audit.py           # ~10 min. After touching the RHS **or any data table**
```

⚠ **THE SUITE AND THE TOLERANCE AUDIT ARE MINUTES OF SATURATED CPU ON THE USER'S
OWN MACHINE.** Say what a long run will cost before starting one, and ask.
`examples/plate_column.py` alone is 12 minutes.

---

# ⚠⚠⚠ WHAT G1 AND G2 TURNED OUT TO BE

**+0 classes, +0 templates, +0 species-ready, +0 on the BOTH column — all four
predicted before measuring, twice over.** A Layer 6 VERB is not a template and
neither is a barrier. What moved is whether the engine can express the thing the
game is about, and whether the numbers it already reported are right.

## ⚠⚠⚠ 1. G1's BRIEF NAMED THE WRONG GAP, AND THE MECHANIC WAS ALREADY BUILT

G1 was scoped as engine work: a `feed` vector on `VesselConditions`, a `feed_T`
beside it (*"THIS TERM IS THE WHOLE POINT"*), a `SET_FEED` event, and a funnel
whose reservoir is a DERIVED DURATION. **All four already existed as the rig's
`meter` edge, which `rig_integrator` documents as "a dropping funnel or a syringe
pump".** Measured, panels 1–2 of `validation/dropwise.py`:

* it delivers its set rate (pinned since Layer 5);
* it **carries the donor's sensible heat** — a 270 K funnel leaves the pot at
  **298.13 K** where a 370 K one leaves it at **364.12 K**, same moles;
* its reservoir **runs out exactly** — 0.001 to **10 mol/s**, funnel lands on
  0.0, the pair conserved to **1e-12**;
* and `SET_EDGE` already opens and shuts it inside a saveable `Scenario`.

⚠ **A `feed` VECTOR WAS REFUSED as a second home for all of it**, with a `feed_T`
that is a DECLARED CONSTANT where a funnel **vessel's** temperature is a solved
one you can put in an ice bath with a thermal edge.

## ⚠⚠⚠ 2. AND THE ONE THING THE BRIEF SAID CAME FOR FREE IS WHAT HAD TO BE BUILT

*"It composes with `wait_until` for free — 'drip until the pot reaches 340 K,
then stop' needs no new machinery."* **False**, for exactly the reason
`collect_fraction` exists. An `Event` carries an absolute `t`:

    the free way:  340 K discovered at t = 20.348728 s
                   recipe records set_edge at t = 20.348728
      replay at 1x: ran
      replay at 2x: REFUSED -- cannot schedule 'set_edge' at t=20.348728...
                    the world is already at t=31.513289

⚠ **THE REFUSAL IS THE GOOD CASE.** A crossing landing a hair EARLIER stays in
the future and the tap shuts at an instant the run never found, silently.
`World.add_dropwise(edge, rate, watch, until, timeout, close=True)` stores the
CONDITION. **SAVE_VERSION 5 → 6** — for a reason the brief did not have: an
unknown SCRIPT VERB is discovered part-way through `run_script`, so a v5 reader
executes every entry before it and stops holding a world that looks finished.

## ⚠⚠ 3. SENSIBLE HEAT ALONE CANNOT PRODUCE THE VIGNETTE

The same moles carry the same joules however fast they arrive, so an INSULATED
pot lands in the same place: **338.422 / 338.480 / 338.567 K** across a 25x rate
change. **A rate only matters against another rate.** The playground is therefore
a nitration (−141.2 kJ/mol) against a bath, not an esterification (−3.2), and
peak pot temperature runs **382 K → 283 K** on nothing but the tap setting.

## ⚠⚠ 4. G2 STAGED THE NITRATION, AND A rho IS MEANINGLESS WITHOUT ITS SIGMA SCALE

    rho = 0     T/K   t/s  toluene   mono     di     tri
                300    10   0.0045 0.0303 0.0745  0.2422
                380  1000   0.0045 0.0303 0.0745  0.2422   <- identical

    rho = -6.5  300    10   0.0000 0.6339 0.3661  0.0000
                300   100   0.0000 0.0721 0.9278  0.0001
                340    10   0.0000 0.0015 0.9971  0.0014
                380  1000   0.0000 0.0000 0.1241  0.8756

Three barriers **25.0 kJ/mol** apart, and nobody typed 25: it is
`-ln(10)*R*298.15*rho*sigma+_meta(NO2)`.

⚠⚠ **THE TABLE IS SIGMA-PLUS (Brown & Okamoto 1958), NOT AQUEOUS SIGMA** —
S12's standard-state finding in another suit. Electrophilic substitution builds
positive charge on the ring, so methoxy is **−0.27 on σ and −0.778 on σ⁺** and
amino **−0.66 and −1.30**. A σ⁺-fitted rho on σ constants multiplies two bases.

⚠ **NOT `alpha`, and the refusal is measured**: benzene → nitrobenzene is −141.2
kJ/mol and nitrobenzene → dinitrobenzene is **−268.1**, so any positive alpha
makes the DEACTIVATED ring react FASTER. `ReactionTemplate` refuses both.

⚠ **It lives at SETUP** — `build_network` bakes the shifted `Ea` into the
kinetics array. No RHS edit, therefore no tolerance-audit exposure.

## ⚠ 5. WHAT G2 COST THE CORPUS, AND TWO OF FOUR ARE IMPROVEMENTS

| route | before | after | |
|---|---:|---:|---|
| `tnt-route` | 0.1528 | **0.0662** mol | worse and RIGHTER — real TNT needs ~380 K |
| `benzene-nitration` | 0.1762 | **0.8000** mol | a mononitration can STOP now |
| `picric-acid-route` | 0.0481 | **0.1208** mol | phenol activated, dinitrophenol not |
| `ddt-route` | 0.1667 | 0.1667 | unchanged — it does not nitrate |

---

# ⚠⚠⚠ START HERE: THE G-SERIES IS THE WORK ORDER

⚠⚠ **READ `MILESTONES.md` § THE G-SERIES.** G1 and G2 are marked done there with
what they actually turned out to be. What is left, in order:

## ⚠⚠ THE BEST-SCOPED NEW ITEM: **COUPLE PROTONATION INTO A BARRIER**

G2 created this and it is the clearest next step on the aromatic branch.

**The gap, measured.** `hammett` prices an amine as a FREE BASE. Aniline comes
out **2.8e8 times more reactive than benzene**, where the real thing in mixed
acid is an **anilinium ion** — meta-directing and *slower* than benzene. That is
wrong by eight orders of magnitude **and in the wrong direction**. 4-aminophenol
(Σσ⁺ = −2.220, a **−82.4 kJ/mol** shift against a declared 60) drives the barrier
straight through zero; `hammett.clamp_barrier` floors it and `build_network`
emits a NOTICE naming the missing physics rather than hiding it.

⚠ **THE MACHINERY IS HALF PRESENT AND NOTHING JOINS IT.** M3 gave the project ion
tables and a pKa; `electrolyte_provider()` prices charged species; the Skraup's
gate is already a hydronium concentration. What does not exist is anything that
lets the FRACTION PROTONATED enter a rate. Design questions, in the order they
will bite:

1. **Is it a barrier shift or a species split?** The honest answer may be that
   an anilinium is a DIFFERENT SPECIES with its own σ⁺ row (−NH3+ is a known,
   tabulated substituent), in which case `dissociation_templates()` already makes
   it and the fix is a table row plus a network that carries the acid. **Measure
   that before designing a coupling** — it would be a data job, not an engine one.
2. **If it is a coupling, what array form does it collapse to?** A barrier that
   depends on the flask's acidity is no longer a setup constant, and that is an
   RHS edit with the tolerance audit attached. The setup/hot-loop split is the
   project's first question and the answer here is not obvious.
3. **What does it cost the four nitration routes?** `picric-acid-route` runs on a
   phenol, which protonates too.

## ⚠ G3 — `PLAYABLE.md`, the scoreboard the goal needs

A generated standing audit answering *what can a player make, starting from
what?* `ROUTE_INDEX.md` knows feedstocks but not what runs; `COVERAGE_REPORT.md`
knows what runs but never asks whether a feedstock is obtainable.

⚠ The classification is already written and measured (7 from-the-ground / 6
one-step-up / 14 blocked on an unmakeable intermediate / 4 from a reagent
bottle). ⚠ **The one hand judgement in it — which compounds count as NATURAL —
must be PRINTED, not hidden**, so it can be argued with.

⚠⚠ **AND G1 GAVE IT A SECOND QUESTION TO ANSWER**: `benzene-nitration` went from
0.1762 to 0.8000 mol on a change that touched no species and no template, so
"what a player can make" is not a property of the corpus alone. **A PLAYABLE
scoreboard has to RUN things**, which is what makes it different from the two
artefacts above and also what makes it expensive.

## ⚠ G4 — the granularity audit *(possibly free routes)*

How many routes are, like `benzene-nitration`, chemically runnable but scored as
blocked because the catalog spells a mechanism out in steps the engine does in
one? **Nobody has counted.** Until someone does, the BOTH column is an unknown
amount too low.

## The C-series — coverage, deliberately deferred

Where *"grind out the remaining classes, including the boring ones"* lives. The
greedy curve in MILESTONES PART 2 is its work order, subject to the RUNNABLE
warning printed beneath it. ⚠ Nothing in the G-series blocks it and every
G-series template counts toward it.

---

# ⚠ THE ENGINE AND HONESTY QUEUE — **REFERENCE, NOT THE WORK ORDER**

⚠⚠ **THE G-SERIES ABOVE IS THE WORK ORDER.** This queue is kept because every row
is a measured, live finding — but **do not start here**, and do not treat a row's
age as a reason to take it.

1. **⚠⚠ NO PROTONATION IN A BARRIER — NEW IN G2, AND IT IS PROMOTED TO THE
   G-SERIES ABOVE.** See that section; it is not repeated here.

2. **⚠ NO REGIOSELECTIVITY IN THE SUBSTITUENT MODEL — ALSO NEW IN G2, AND IT IS A
   BUILDER CHANGE RATHER THAN A DATA ONE.** `hammett.survey` sums over the
   substrate's ring as a whole, so all three dinitrobenzenes from nitrobenzene
   get the same barrier and are made at the same rate. Doing better needs the
   barrier to know WHICH ring carbon was attacked, and a `ConcreteReaction` is a
   pair of SMILES tuples — the site is discarded by the time
   `_concrete_in_phase` computes the barrier.
   ⚠ **The information EXISTS at the moment the rewrite runs** (`tmpl.run` has
   the RDKit match) and is thrown away, which is S9's shape exactly. What it
   would buy is real: nitration of toluene is ~60% ortho / 37% para / 3% meta and
   the engine currently says a third each. ⚠ **Price it against G4 first** — a
   regioselective nitration may or may not move any catalog row.

3. **⚠⚠ THE PSRK OVERFLOW IS NO LONGER "MEASURED INERT" (S13), AND IT IS STILL
   THE CHEAPEST REAL ITEM.** `activity.activity_coefficients` overflows
   `np.exp(-a / T)` below **4.28 K** (measured exactly: `max(-a/T)` is 760 at
   T=4 and 292 at T=10). `plate_column` prints **five `RuntimeWarning` lines
   where it printed none**. ⚠ **MEASURED HARMLESS WHERE IT FIRES** — heart 0.8548
   against 0.8544, target met, replay exact. **The word to change is "inert", not
   the number.** ⚠ **WHAT IS NOT KNOWN IS *WHERE*** — nothing has found which
   call passes a T that low. A `np.errstate(over="raise")` context around the
   residual term, with the state printed, is the whole probe. Worth ZERO routes.

4. **⚠⚠ `multistep_prep` PRINTS `pH = inf`, AND IT IS PRE-EXISTING.** At the
   default tolerance the benzoate flask reports `inf`; at rtol 1e-8, **11.65**.
   ⚠ **A READOUT THAT REPORTS INFINITY IS NOT AN ACCURACY PROBLEM** — same
   mechanism as the Skraup's "exactly zero": a hydronium column the loose solver
   clamps to a literal 0.0, and `-log10(0)` is `inf`. The fix is probably a floor
   on the pH READOUT (the shape `is_boiling` got), but **measure the hydronium
   trajectory first**.

5. **⚠⚠ NOTHING IN `build_phase_arrays` COMPARES T TO Tc.** A CONDENSABLE species
   above its critical temperature still dissolves by Raoult's law against an
   Antoine curve extrapolated past its own domain. Measured: a Wacker flask at
   400 K dissolves **0.165958 of 0.20 mol of ethylene over 20 mol of water —
   83%, against a real ~2%** — because Psat reads **219.9 bar** off a curated
   Antoine **118 K above ethylene's Tc of 282.35 K**.
   ⚠⚠ **A MEASURED BOILING POINT DOES NOT FIX IT** — S11 predicted it would and
   measured that it does not (0.16588 → 0.16596), because the vapour pressure
   comes from `volatility._CURATED_ANTOINE` and Tb does not feed that curve.
   ⚠ **S13 PUT 869 MORE SPECIES ON A FITTED ANTOINE CURVE** and added no Tc
   check, so the exposure grew even though the measured example did not move.

6. **⚠⚠ A METAL THAT BOILS OUT OF THE SOLID BLOCK — STILL THE BEST-SCOPED PURE
   ENGINE ITEM.** Measured after S10's commit by patching iron's volatility in
   place (Alcock's curve) and running thermite insulated:

       vessel Cp    lattice iron    VOLATILE iron    where the iron went
          1 J/K       5469.43 K        3490.99 K     0.0192 gas / 0.0207 liquid
         10 J/K       2329.06 K        2284.28 K     0.0399 liquid (it MELTED)
         50 J/K       1322.45 K        1322.45 K     unchanged

   **The blocker is ONE BRANCH in `build_phase_arrays`** — the
   `if mineral is not None:` arm pinning `vol_A = NONVOLATILE_A`,
   `condensable = False`, `solidifies = False`. Letting a `MineralRecord` carry
   OPTIONAL volatility is a **setup-layer change with NO RHS edit**.
   ⚠ **BUT THE DATA OBJECTIONS SURVIVE THE ENGINE FIX**: `[Fe]` fails S4's
   disambiguation test (three solid allotropes, two transitions inside thermite's
   range) and Alcock tabulates **no sublimation curve** for iron, so zinc's best
   cross-check cannot be run — **ONE check, not four.** ⚠ Worth ZERO routes for
   iron; ⚠⚠ **MEASURE `direct-combination` FIRST** — worth +1 and refused by the
   same `build_surface_arrays` non-lattice check, but `Hg(l) + S8(s)` is not a
   gas attacking a crystal, so `SurfaceArrays`' form may be wrong for it.

7. **⚠⚠ THE 250–450 K FIT WINDOW.** `CondensedProvider.get(mol, T_lo=250.0,
   T_hi=450.0)` is an organic-solvent window and **every caller takes the
   default**. Swept in S11 over each species' OWN Tm→Tb: **99 compounds return a
   NEGATIVE liquid Cp inside their own liquid range** (worst carminic acid at
   **−21482 J/(mol K)**) and 38 more swing over 5x.
   ⚠⚠ **NOBODY HAS RE-SWEPT THE 99 SINCE S13 GAVE 876 SPECIES MEASURED Tb/Tc.**
   The count is a pre-S13 number and **the first thing this item needs is to
   measure it again** — S11 moved ethylene from **+1574 to −1782** by giving it a
   measured Tc, so better inputs do not make an extrapolation safer.
   ⚠ A negative Cp is not an accuracy problem: **adding heat LOWERS the
   temperature**, and S10 measured it reachable (3.96 mol of liquid mercury gave
   a NEGATIVE total thermal mass). ⚠⚠ **DO NOT JUST WIDEN THE WINDOW** — many of
   the 99 have a Joback Tm/Tb that is itself meaningless.

8. **⚠ `slagging` — RE-PRICED IN S11 AND IT WAS PRICED TOO CHEAPLY.**
   `silicon-dioxide` ✔ fully available; **`calcium-silicate` has NO
   thermochemical data under ANY of its three CAS numbers** ✘ (not a curation
   job); `iron-ii-oxide`'s CRC standard row has **`Cps = NaN`**.
   **`blast-furnace` is blocked TWICE over, on SOURCES rather than on work.**

9. **⚠ THE CIS/TRANS BLIND SPOT.** Benson (the RMG group set) has no cis
   correction, so oleic and elaidic acid come back with IDENTICAL Hf and Gf and
   the engine reports a confident 50:50 for a real ~5:1. ⚠ **The data exists and
   is not usable as it stands**: WEBBOOK has both liquid enthalpies (−764.8 and
   −769.0 kJ/mol) and that 4.2 kJ/mol gap agrees with Benson's own historical cis
   NNI term to 0.4% — **two independent sources** — but neither has an S0, so no
   Gf can be derived, and grafting Benson's original correction onto RMG-fitted
   group values **mixes two bases**.

10. **⚠ THE CURRENT BUDGET — M8's OWN NAMED GAP, AND IT IS A LAYER 4 TERM.** Two
    electrode reactions in one cell divide nothing, so both run at full rate:
    k(brine)/k(water) is **4.76e+17 at 2.5 V, 5.94 at 3.0, 1.00 at 4.0**.
    ⚠ Worth **ZERO new routes**.

11. **Pyrite** — one mineral entry, +1 on the intersection. ⚠ **RE-QUERIED IN S11
    AND THE REFUSAL STANDS**: `Hfs` in WEBBOOK, `S0s` in **nothing**.

12. **⚠⚠ THE BURNER — ~50 s at rtol 1e-8 against 0.8 s at the default.** S5
    bounded the CRASH and explicitly did not bound the THRASHING. BDF is
    struggling with a liquid layer holding **1e-29 mol**, which `LAYER_REABSORB`
    drains toward zero without ever reaching it. **The question nobody has asked
    is whether a layer below `LAYER_EPS` should be *merged discretely* at a step
    boundary rather than drained continuously for ever** — `merge_phases` already
    does exactly that at the `run` boundary. **Measure the layer-2 inventory over
    the failing run before designing anything.**

13. **THE CORPUS BALANCE BACKLOG — 75 ROWS, AND IT IS NOT A TO-DO LIST.** S7
    built the check and deliberately fixed nothing, on the `diels-alder-route`
    precedent. ⚠ But **17 of the 75 are `spurious`** and those are the cheapest to
    correct. ⚠ `tools/catalog.py`'s `validate` still does NOT check balance, so
    the corpus can grow another one silently.

14. **⚠ `hydrolysis`** — it unlocks **exactly ONE route alone,
    `vitriol-distillation`**, and that route's step 1 reads `-> iron-ii-OXIDE`
    while the engine makes HEMATITE. ⚠ **That is item 8's mineral again.**

15. **M7 (⚠ M12 took most of its case away; re-scope)**, **M9 (polymers, 12
    routes)**, **M10 (the site balance S1 did not build, 8 routes)**,
    **⚠⚠ M11 — RE-COST IT BEFORE SCHEDULING.** Its costed starting point was
    *"10 species that need ONE measured boiling point each"*; **S13 closed eight
    and the bucket counts 2**. What is left is the FORMATION half — 267 species
    with no group value in any published tabulation.

16. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
    the *deposition-needs-a-seed* half into a real bound in
    `SolidStateArrays.units`. What is still not expressible is a solid appearing
    from NO solid — `hydride-thermal-deposition` is still a mechanism gap.

---

# THE COVERAGE QUEUE — **DEFERRED TO THE C-SERIES; WHAT IS LEFT IS REFUSALS OR ENGINE WORK**

⚠⚠ **What is left here is NOT a work queue.** Five of the seven rows are recorded
REFUSALS or engine prerequisites, and the two that are neither are the hardest
kind of content work. **Read the row, not the rank.**

| class | its route | worth | what it is |
|---|---|---:|---|
| `fischer-tropsch` | `fischer-tropsch` | +1 | `8 CO + 17 H2 -> octane + 8 H2O`, **25 slots**. Claus proves 24 works and Skraup proves the pattern generalises — but read M8 §6 on the lump that was refused. ⚠ **The queue's best CONTENT row**, and its mechanic is chain growth as a lump, which is M9's problem wearing a template |
| `molten-salt-electrolysis` | `downs-cell` | +1 | ⚠ **A MELT is not a phase this project has** — M8's own leftover, ENGINE work |
| `catalytic-air-oxidation` | `p-xylene-oxidation` | +1 | ⚠⚠ **M5 REFUSED THIS CLASS** — its four rows are at least three mechanisms. **Split it before crediting it**; only one of the four is runnable |
| `direct-combination` | `vermilion-route` | +1 | ⚠⚠ **S9 MEASURED AND REFUSED IT**; engine queue item 6 is the only thing that could change that. **Do not re-derive this** |
| ~~`oxidative-cleavage`~~ | `vanillin-lignin` | ⚠⚠ **S11 REFUSED IT** | It cannot be the reaction the row is written as: it balances at **8 C10H12O3 + 7 O2 -> 10 C8H8O3 + 8 H2O** — eight aromatic rings in and TEN out. **Do not re-derive this** |
| `fermentation` | `abe-fermentation`, `msg-route` | +1 | ⚠ **M5 REFUSED IT** as a metabolic NETWORK rather than a transformation |
| `separation` | `coal-tar-distillation` | +1 | ⚠ **M5 REFUSED IT**: a distillation is not a reaction class, and the feedstock has no graph |

⚠⚠ **AND READ `corpus_balance.py`'s LAST PANEL BEFORE PICKING ANY OF THEM.** The
balance audit's test is a WEAK one: it asks whether ANY positive coefficient
vector conserves the elements, and element conservation does not forbid
rearranging carbon skeletons. `vanillin-lignin` PASSES at eight rings in and ten
out. ⚠⚠ **AND S12 IS THE CONVERSE**: `skraup-route` step 2 looked like the
`spurious` pattern, passed, and was REAL. **The check cannot decide either way;
only reading the chemistry can.**

⚠ **`isomerisation` IS DEAD THREE TIMES OVER AND IS STILL THE REPORT'S TOP ROW.**
Two balance failures, plus `oleic -> elaidic` prices at **dH = dG = 0.000
EXACTLY** and `glucose -> fructose` at **K = 4.8e-08** because the corpus spells
one as a pyranose and the other as a furanose. **Do not build it.** The other
seven the report promises and the balance audit kills are tabulated in
`corpus_balance.py`'s own output.

---

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan, and **§ THE G-SERIES first**. ⚠ **§G1 and §G2 are
  marked DONE with what they turned out to be, and G1's original brief is kept
  underneath because the measurement that overturned it only means something
  against it.** Then §S13, §S12, §S11, §S10, §S9, §S8, §S7, §M8, §S1, §S3, §S4,
  §S5, §S6.
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1 … 98 is S13,
  99 is G1, 100 is G2.**
NEXT_SESSION.md — the invariants table at the bottom is the contract, and **G1
  and G2 each added a block**. ⚠ Read the two warnings above it before trusting
  any row, and note that G2's protonation row and G1's still-cost row are
  **LIMITS TO REMOVE**, not invariants to keep.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy; plus
  `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially **chemsim-dropping-funnel** and
  **chemsim-ring-deactivation**, then chemsim-skraup-standard-state,
  chemsim-competing-templates, chemsim-physical-data-sourcing,
  chemsim-measured-physical-table, chemsim-coverage-catalog and
  chemsim-generated-artefacts.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a
plate column that reaches its purity target, an ionic lattice that can leave
solution, an energy balance it can report the way it reports a mass one, 46
templates, a reaction that happens INSIDE a crystal, a gas that ATTACKS a
crystal, a catalyst you have to actually put in the flask, a Jacobian that cannot
be probed outside its own state, four inorganic gas processes, three smelters, a
retort that DISTILS its metal off, two templates that RACE for one alkene, a ring
closure whose OXIDANT turns into one of its own reagents, **a dropping funnel
whose addition is a CONDITION and not a duration**, and **an aromatic ring that
knows what is already on it**. `SAVE_VERSION` is **6**.
Coverage: **51/229 classes**, **46 templates**, **41/173 template-ready**,
**80/173 species-ready** — and ⚠⚠ **31/173 BOTH, which is the only one of the
three a route can be judged on.** ⚠ G1 and G2 moved none of them, as predicted.
⚠ The corpus's **PHYSICAL half is measured for 652/1583 (41.2%)** as of S13.

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ NO PROTONATION IN A SUBSTITUENT BARRIER (G2).** Aniline is priced as a
free base at **2.8e8 × benzene**; the real anilinium ion is meta-directing and
SLOWER than benzene. 4-aminophenol drives the barrier through zero and is
CLAMPED with a NOTICE. **A LIMIT to remove**, and the best-scoped new item.

**2. ⚠ NO REGIOSELECTIVITY IN A SUBSTITUENT BARRIER (G2).** All three
dinitrobenzenes are made at one rate. The site exists at rewrite time and is
discarded. **A LIMIT to remove.** Engine queue item 2.

**3. ⚠ A STILL AND A DRIP BENCH CANNOT BE ONE APPARATUS IN AN EXAMPLE'S BUDGET
(G1).** The same 20 s addition costs **3.9 s of wall clock on two vessels and
220 s with a head and receiver attached — 56x.** Not a bug: a rig integrates
every vessel as one stiff system. **Reported in `examples/dropping_funnel.py`.**

**4. ⚠⚠ NOTHING COMPARES T TO Tc (S11).** Ethylene is ~40x too soluble in the
Wacker liquor. Engine queue item 5. **A LIMIT to remove.** ⚠ S13 put 869 more
species on a fitted Antoine curve and did NOT add a Tc check.

**5. ⚠⚠ THE WACKER'S OXYGEN ORDER IS FIRST AND SHOULD BE ZERO (S11).** Measured
at 1.00 / 1.92 / 3.53 / 5.85x. **A LIMIT to remove.**

**6. ⚠⚠ A LATTICE MAY REACT AND MAY NEVER BOIL — HALF CLOSED BY S10.** What
remains is thermite. **Engine queue item 6**, worth ZERO routes.

**7. ⚠⚠ THE BURNER IS STILL ~50 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT.**
**Engine queue item 12.**

**8. ⚠⚠ NO CURRENT BUDGET (M8).** Selectivity washes out above ~2.7 V.

**9. ⚠⚠ THE ION TABLE'S MIXED BASIS (M8, pre-existing).** dG survives it, dS does
not. Quote E_dec at 298 K; do NOT quote its temperature derivative or a cell's
HEAT.

**10. ⚠⚠ 75 CATALOG ROWS CANNOT BE BALANCED (S7).** Reported, not fixed.

**11. ⚠⚠ THE ESTIMATORS CANNOT TELL A CIS ALKENE FROM A TRANS ONE (S7).**

**12. ⚠ `deacon_oxidation_rev` CROSSES THE BIMOLECULAR CEILING AT 1141 K**, and a
solid decomposition's forward constant crosses the unimolecular one at 3710 K.
⚠ S11 added two rows that cross at 967/969 K, the only ones whose crossing is a
physical statement rather than a ranking.

**13. ⚠ `detailed_balance`'s RATE CAP COMPARES A CATALYSED PRE-EXPONENTIAL
AGAINST A LIMIT NOT IN ITS UNITS.** It does not fire on any catalysed template.

**14. THE DEFAULT TOLERANCE, BOUNDED RATHER THAN OPEN.** ⚠ `tolerance_audit.py`
is a STANDING audit: run it after touching the RHS **or any data table**. ⚠
**NEITHER G1 NOR G2 DID EITHER**, so its last measured state is S13's.

**15. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever. M10.

**16. ⚠⚠ 99 CORPUS ROWS HAVE A NEGATIVE LIQUID HEAT CAPACITY (S10, re-swept
S11).** ⚠ **The count is PRE-S13 and nobody has re-swept it.** Engine item 7.

**17. ⚠ NUCLEATION, HALF modelled.** A solid can only grow where one already is.

**18. ⚠⚠ THERE IS NO REFLUX HEAD (S12).** A reaction at reflux must be modelled
as a SEALED flask, which buys a real pressure (13.7 bar for the Skraup at 450 K).
⚠ An OPEN Skraup loses **98% of its yield**.

**19. ⚠ LIQUID MERCURY IS 99.85% HELD IDEAL.**

**20. ⚠ THE ELEMENT FLOOR'S SOLID HALF IS CURATED AND ITS GAS HALF IS REFUSED.**
33 compounds remain refused as bare elements and none blocks a route.

**21. ⚠ `iron-ii-oxide`, `pyrite` AND `calcium-silicate` ARE ALL SOURCE-BLOCKED.**

**22. ⚠⚠ THE PSRK OVERFLOW IS NO LONGER "MEASURED INERT" (S13).** Overflows below
**4.28 K**; `plate_column` prints five `RuntimeWarning` lines. ⚠ Measured
HARMLESS where it fires. Nothing has found WHICH call passes a T that low.
**Engine queue item 3.**

**23. ⚠⚠ `multistep_prep` PRINTS `pH = inf` (pre-existing, visible since S13).**
**Engine queue item 4.**

**24. ⚠ `named_routes` CANNOT BE SWEPT at rtol 1e-8 (S13) — AND IT IS NOT NEW.**
The PRE-S13 data raises too, at **rtol 1e-7**, one decade closer to the default
than the audit samples.

**25. ⚠ THE 31 SPECIES THAT MISS THE BOILS-AT-1-ATM BAR (S13).** 858 of 889 clear
1.5%; the 31 are NAMED in `BOILS_LOOSELY` and **eight are pre-existing**.

**26. ⚠ BENZOIC ACID'S MOLAR VOLUME GOT WORSE IN S13** — 96 → 87.4 mL/mol against
a real ~96.5. Taken deliberately: a record may not mix two group-contribution
methods.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠⚠⚠ **SEARCH FOR THE MECHANIC BEFORE BUILDING IT, AND SEARCH THE OTHER LAYER.**
G1's brief said a dropping funnel was MISSING and listed four things to build.
All four already existed as `Rig`'s `meter` edge, whose own docstring says *"a
dropping funnel or a syringe pump"* — sensible heat and all. The brief had
measured the vignette against `Vessel` and never looked at Layer 4's edges.
**Twenty-eight sessions of audit-the-instrument, and this is the first time the
instrument was the BRIEF.**
⚠⚠⚠ **AND THE HALF A BRIEF CALLS FREE IS THE HALF TO MEASURE.** *"It composes
with `wait_until` for free"* was the only sentence in G1's build list that was
not an instruction, and it was the only thing that had to be built.
⚠⚠ **A rho IS MEANINGLESS WITHOUT ITS SIGMA SCALE**, exactly as a dH is
meaningless without its standard state. σ⁺ and σ differ by up to 0.6 for
resonance donors (methoxy −0.778 against −0.27) and agree within 0.05 for
acceptors. **Ask which scale a fitted reaction constant was measured against
before multiplying it by anything.**
⚠⚠ **TWO NUMBERS THAT EACH CARRY THEIR OWN ERROR TERM CANNOT BE SUBTRACTED TO
DECIDE A THIRD.** `ran_dry` was first written as `delivered < rate*elapsed` and a
funnel with a headspace delivers 0.40799 against a nominal 0.40702 — MORE, not
less. Measure the thing the question is about (what is left in the funnel).
⚠⚠ **A DERIVED DURATION IS WRONG TWICE: IT IS DERIVED DATA, AND THE ARITHMETIC
MAY NOT BE THE ARITHMETIC YOU THINK.** `total / rate` for a dropping funnel is
20 s where the answer is 30, because a meter moves the donor's SOLUTION and not
its reagent. It caught its own author, in a test written to make a different point.
⚠⚠ **A RATE ONLY MATTERS AGAINST ANOTHER RATE.** The same moles carry the same
joules however fast they arrive; an insulated pot moved 0.15 K across a 25x
addition-rate change. "Add it too fast and it runs away" needs an EXOTHERM racing
a COOLING CONDUCTANCE, which is why the playground is a nitration and not an
esterification.
⚠⚠ **A BIT-IDENTITY CLAIM HAS TO BE ABOUT THE THING IT IS A CLAIM ABOUT.** The
first draft of G2's collapse check built a 5-species network, which lets one
dinitrobenzene in, and reported "not identical" while printing two numbers that
both read 60000.000000. The disagreeing entry was the second reaction, on a ring
that is no longer unsubstituted.
⚠ **AN UNSOURCED VALUE IS REPORTED, NOT PRICED AT ZERO IN SILENCE.** Aspirin's
acetoxy oxygen has no σ⁺ this table can source, so it is excluded from the
`alkoxy` pattern and comes back in `unknown` with a NOTICE. Pricing it as a
methoxy would have made aspirin's ring more reactive than anisole's.
⚠ **A CHEMICAL RULE'S EXCEPTIONS ARE DATA, NOT A DERIVATION.** "Meta-directing
iff σ_para > 0" is wrong for all four halogens, which deactivate and yet direct
ortho/para. `meta_directing` is a declared field.
⚠ **A CLAMP IS NOT A FIX, AND IT SHOULD SAY SO.** `clamp_barrier` floors a
negative activation energy at zero and `build_network` emits a NOTICE naming the
missing physics (protonation) rather than letting the floor read as the answer.
⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Twenty-four times now. ⚠ **AND THE SOLVER IS PART OF THE ARITHMETIC**
(M8).
⚠⚠ **A GENERATED FILE IS ONLY AS SYSTEMATIC AS ITS INPUT LIST.** S13 closed it
for `physical_data.py`: the file looked generated from the outside and was a
transcription on the inside, and nothing could see the difference **because a
Joback record RESOLVES**.
⚠⚠⚠ **AND THE FIX FOR ONE TRAP CAN BE THE NEXT TRAP.** S11 recorded "a bare
SMILES is read as a FORMULA — always use `smiles=`"; S13 did, and generated a
table with no aniline in it. **NEITHER KEY ALONE IS ENOUGH** — graph first, then
the NAME, with the formula cross-check as the arbiter.
⚠⚠ **A COUNT OF THINGS THAT ARE MISSING IS NOT A COUNT OF THINGS THAT ARE WRONG.**
⚠⚠ **A TIER READ OUT OF PROSE GOES WRONG THE MOMENT THE WORDING CHANGES**, and
**A DEFAULT AT THE BOTTOM OF A MATCHER IS A GUESS.**
⚠⚠ **A BAR MEASURED OVER NINE SPECIES IS A BAR MEASURED OVER NINE SPECIES**, and
**A BAR IN TEMPERATURE AND A BAR IN PRESSURE ARE NOT THE SAME BAR.**
⚠⚠ **A ONE-POINT TOLERANCE SWEEP CANNOT TELL "NEWLY BROKEN" FROM "ALREADY BROKEN
AT A POINT IT DOES NOT SAMPLE."**
⚠⚠ **A DOCUMENTED BEHAVIOUR CAN BE RESTING ON A WRONG NUMBER MAKING IT BIG ENOUGH
TO SEE.**
⚠ **A ROOT IS ZERO TO SOLVER PRECISION, AND THE LAST BIT IS NOT PHYSICS.**
⚠ **A BETTER RECORD CAN MAKE ONE NUMBER WORSE, AND THE ANSWER IS TO WRITE IT
DOWN.**
⚠⚠ **ASK WHICH NUMBER THE SYMPTOM ACTUALLY DEPENDS ON BEFORE CURATING THE ONE
THAT LOOKS RESPONSIBLE.**
⚠⚠ **A CORRELATION EXTRAPOLATED OUTSIDE ITS DOMAIN DOES NOT GET SAFER WHEN ITS
INPUTS GET BETTER.**
⚠⚠ **EVANS-POLANYI NAMES THE WRONG MAJOR PRODUCT WHEN KINETICS FIGHT
THERMODYNAMICS**, and G2 adds the measurement that makes it concrete on a ring:
the DEACTIVATED substrate's step is the MORE exothermic one.
⚠⚠ **AN EQUILIBRIUM CONSTANT IS A STATEMENT ABOUT PARTIAL PRESSURES.**
⚠⚠ **A DECLARED ORDER OF ZERO DRIVES ITS REACTANT NEGATIVE.**
⚠⚠ **COUNT THE MOLES OF GAS ON EACH SIDE BEFORE DECLARING IRREVERSIBLE.**
⚠⚠ **A SCOPING GUARD IS NOT A PHYSICS CLAIM.**
⚠⚠ **A SINGLE-LETTER SMILES IS ALSO AN ELEMENT SYMBOL.**
⚠⚠ **A REFUSAL'S SENTENCE IS A CLAIM ABOUT A NAMED THING — CHECK WHICH THING**,
and **TWO SYMPTOMS CITING ONE SENTENCE ARE NOT NECESSARILY ONE GAP.**
⚠⚠ **THERMODYNAMIC CONCLUSIONS SURVIVE A PHASE CHANGE IN A PRODUCT; KINETIC ONES
NEED NOT.**
⚠⚠ **ASK WHAT A FIT WAS ANCHORED ON, NOT WHETHER THE CHECK LOOKS FAMILIAR.**
G2's answer is 298.15 K and deliberately NOT the network's `T_ref`.
⚠⚠ **A CORRELATION'S FIT WINDOW IS A DEFAULT ARGUMENT NOBODY OVERRIDES.**
⚠⚠ **READ THE CATALOG ROW, NOT THE CLASS NAME**, and **A BALANCE CHECK IS A
NECESSARY CONDITION, NOT A SUFFICIENT ONE.**
⚠⚠ **A COLUMN THAT ANSWERS A QUESTION CANNOT ANSWER THE NEXT ONE.**
⚠⚠ **A CLASS IS A MECHANISM CLAIM, AND A SPLIT MAY LOWER THE HEADLINE.**
⚠⚠ **A SPECIES JOB SHOULD FOLLOW THE TEMPLATE IT ENABLES, NOT LEAD IT.**
⚠ **A BRIEF'S EXPECTED OUTCOME IS A HYPOTHESIS.** ⚠⚠ **AND G1 IS THE STRONGEST
CASE OF IT YET: THE BRIEF'S ENTIRE BUILD LIST WAS ALREADY BUILT.**
⚠ **PREDICT THE NUMBER BEFORE YOU MEASURE IT.** S3 +2/+0; S4 +1/+1; S6 predicted
14 and measured 16; M8 three for three; S7 five for five; S9 four for four; S10
four for four and all four ZERO; S11 four for four; S12 four for four; S13 four
for four; **G1 four for four and G2 four for four — all eight ZERO, because
neither a Layer 6 verb nor a barrier is a template.**
⚠ **VERIFY A CREDIT BY RUNNING IT, NOT BY READING THE CODE THAT WOULD RUN IT.**
⚠ **AND VERIFY A BIT-IDENTICAL CLAIM AGAINST THE EXAMPLE SET, NOT AN ARGUMENT.**
⚠ **A CONSTANT'S UNITS ARE WHAT MAKE ITS VALUE DEFENSIBLE.** G1 uses it as a
REFUSAL: `add_dropwise` rejects a drain edge, because a drain's `k` is a
reciprocal residence time and a meter's is mol/s.
⚠ **AN ARRHENIUS PAIR IS NOT SEPARABLE.**
⚠ **AN `inf` IS USUALLY THE WRONG BOUND, NOT A BOUND NEEDING SOFTENING.**
⚠ **A RELATIVE-DIFFERENCE TEST IS MEANINGLESS ON A COLUMN WHOSE CONVERGED VALUE
IS ZERO.**
⚠ **A NEW CREDIT MUST BE A FALLBACK BEFORE IT IS AN OVERRIDE.**
⚠⚠ **A ONE-POINT WALL-CLOCK ATTRIBUTION IS NOT A MEASUREMENT.** S13 explained a
suite that had gone from 13:20 to 21:36 as CONTENTION, from one run with other
work on the machine. G2's uncontended run is **22:06** — the explanation is
refuted, and the cause is still not measured. ⚠ **Note which half of that
sentence is the finding**: "not contention" is established; "therefore the data
table" is not, and `pytest --durations=25` has never been run here.
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS.** S2's harness invented a finding;
S1's coverage audit credited a route that cannot run; S3's report could not be
diffed; S4's rate-ceiling audit made a claim about a table it does not read; S6's
target column had been understating itself since M3; M8's new audit found a
pre-existing ion-table error; S7 found the coverage audit pricing a species the
engine refuses; S9 found a source comment CITING an audit check that never
existed; S10's `game_gates` panel INVENTED a 90 kJ/mol error; S11's sweep read
methane's boiling point as carbon's; S13's counted 322 where the answer is 830;
**and G1's brief listed four things to build that were already built.**
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS.
⚠ **A GENERATED FILE NOTHING READS IS THE ONE THAT ROTS.** Regenerate all three
catalog artefacts and check them across `PYTHONHASHSEED`.
⚠⚠ **AND A GENERATED FILE'S PROSE ROTS EXACTLY LIKE A HAND-WRITTEN ONE.** ⚠ The
root `README.md`'s coverage table is NOT generated — S4 corrected it, S6 again,
M8 again, S7 again, S9 again, S11 again. ⚠ G1 and G2 moved no coverage number,
so it is correct as it stands.
⚠⚠ **A PHASE LABEL CARRIES A STANDARD STATE — AND SO DOES A SENTENCE.**
⚠ **BDF IGNORES `jac_sparsity` THE MOMENT `jac` IS CALLABLE.**
⚠ Windows console is cp1252: **a warning glyph inside a `print()` kills a
script.** Docstrings fine, printed text ASCII. **(TWENTY-SIX sessions running —
G1 shipped one into `examples/dropping_funnel.py` and it died on the first run.)**
⚠⚠ **`sed -i` REWRITES EVERY LINE ENDING IN A CRLF FILE, AND ON THIS MACHINE IT
ALSO FAILS OUTRIGHT IN THE SCRATCHPAD.** This repo is MIXED: markdown and `.psv`
are CRLF, and so are `element_data.py`, `solid_state.py`, `volatility.py`,
`catalog_coverage.py`, `rate_ceiling.py`, `gas_processes.py`, `template.py`,
`reaction.py`, `synthesis.py`, `thermochemistry.py`, `mineral_data.py`,
`condensed.py`, `library.py`, `test_solid_state.py`, `test_critical.py`,
`test_phase_properties.py`, `test_protocol.py`, `test_still.py`,
`test_wait_until.py`, `build_physical_data.py`, while `vessel.py`, `surface.py`,
`thermo.py`, `builder.py`, `world.py`, `constants.py`, `jacobian.py`,
`tolerance_audit.py`, `hammett.py` and the newer `validation/*.py` are LF.
**Read binary, detect `\r\n`, restore it on write, and check `git diff --stat`
after the first edit to any file.**
⚠ **HEREDOCS EAT ESCAPES AND CHOKE ON A LARGE BLOCK CONTAINING QUOTES.** Write
the payload with the Write tool and splice it.
⚠ **A GENERATOR CAN LEAK A `numpy` REPR INTO ITS OUTPUT.** Cast to `float`.
⚠ **DO NOT NAME A LOCAL `net` IN A SCRIPT THAT ALSO HAS A `net()` HELPER.**
⚠ An em dash in a markdown anchor will not match a `--` you typed.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u`.
⚠ **A CANONICAL SMILES IS NOT THE ONE YOU TYPED.**

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays. NO silent
approximations. REFUSE loudly rather than return a confident wrong number — and a
LATENT fragility is a third case: report it, do not refuse it.
⚠ **AND REFUSING TO *DISSOLVE* A SPECIES IS NOT REFUSING TO *PRICE* IT.**
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?" ⚠ **G2's answer was "one that already
exists"**, which is why it cost no RHS edit.
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; `solid_state=False`
exactly no crystal reacting; `surface=False` exactly no gas attacking one; an
all-zero `order_solid` exactly the old kinetics kernel; `cell_potential=0.0`
exactly the pre-M8 engine, bit for bit; an all-positive `nu_gas` exactly the
pre-S9 solid-state term; `SolidStateReaction.Ea is None` exactly M6's derived
pair; `SurfaceReaction.A is None` exactly the shared sulfide clock;
`BoundedJacobian` with its bound lifted exactly BDF's own differencing; the Born
term exactly zero in PURE water; **`hammett_rho = 0.0` exactly the pre-G2
barrier, bit for bit, and `barrier_shift` returns a LITERAL `0.0` so it is exact
rather than nearly so**; the five pH values; SAVE_VERSION stores the CONDITION,
never the instant; every gaseous element reference state Hf = Gf = 0 EXACTLY; a
CONDENSED reference state's ideal-gas record is a MEASUREMENT and must not be
zero; every METAL Hf = Gf = 0 EXACTLY on the solid basis; a reference state its
own database does not price at Hf = 0 is REFUSED; no mineral pricing differently
under the two providers; `ion_data` and `electrolyte` never subtracted from each
other; a declared rate order may NEVER be reversible; an `electrons` count may
never carry declared orders; an electrode template is a WHOLE CELL, charge
balanced on both sides; the reverse of an electrode reaction carries MINUS the
work; an IRREVERSIBLE surface row whose `ln K` is under +20 is REFUSED; a
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
lattice may REACT and may never DISSOLVE, BOIL or MELT; `_CURATED_SOURCE.get(smi,
_NIST)` is exactly the old shared stamp for all nine pre-S10 Antoine rows; a
curated liquid Cp must be POSITIVE across the species' whole liquid range; the
two hydroformylation templates share one `A`, so the n:iso ratio IS `exp(dEa/RT)`;
**`alpha` is 0.0 on both, because Evans-Polanyi would name the wrong major
product**; `wacker_oxidation` keeps order 1 in oxygen because the kernel has no
availability gate; the measured physical table overrides a working Joback record
ONLY where `DELIBERATE_OVERRIDES` names it and says what it cost; the Skraup's
three amine slots may be three DIFFERENT molecules; `skraup_cyclisation` keeps
order 1 in its oxidant, and its dS is pinned on BOTH standard states; a template
that is not in `validation/rate_ceiling.py` is not audited; `MEASURED_PHYSICAL` is
generated from `data/catalog` and never hand-edited; a corpus CAS is resolved by
GRAPH first and then by NAME, and a name match must pass the formula cross-check;
`CORPUS_SWEEP` and `DELIBERATE_OVERRIDES` are DISJOINT; an Antoine fit window must
BRACKET its own boiling point; a species that leaves `BOILS_LOOSELY` must be
removed from it; **`add_dropwise` stores the CONDITION and never the instant, and
turns its taps through `_set_edge` rather than the event queue**; **a dropwise
addition refuses a non-METER edge, because a drain's `k` is not in mol/s**;
**`ran_dry` is read off what is LEFT IN THE FUNNEL and never off a delivery
shortfall**; **the Hammett table is on the SIGMA-PLUS scale, its two PROXY rows
are both electron ACCEPTORS and are labelled, and `meta_directing` is DECLARED
rather than derived from the sign of sigma**; **the Hammett conversion is
anchored at 298.15 K and NOT at the network's `T_ref`**; and **`hammett_rho` and
`alpha` may not be declared on the same template.**

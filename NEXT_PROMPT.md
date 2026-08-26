We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M12, S1–S6 are DONE.**

**START WITH: ⚠⚠ CONTENT, NOT THE ENGINE — AND THE REASON IS MEASURED.**
Template-ready routes went **25 at M5 → 28 now**: S1 +1, S3 +0, S4 +1, S5 +0,
S6 +0. **Six consecutive sessions produced +3 routes.** Every one found something
real, and the aggregate is still a project spending its measurement discipline on
the ENGINE while its own plan says the constraint is CONTENT. `MILESTONES.md`'s
own instruction — *"M5 onward is content and new physics, and should be run
against a target rather than against completeness"* — has not been followed since
M5. **Take a template milestone this session. The burner is item 5 and it will
keep.**

⚠⚠ **AND READ §S6's INTERSECTION FINDING BEFORE PICKING ONE, BECAUSE IT CHANGES
THE WORK QUEUE.** The three readiness columns answer INDEPENDENT questions and the
smallest does not bound the others: **species-ready 65, template-ready 28, BOTH
17.** Eleven template-ready routes have a refused species and cannot run. The
greedy curve and the one-class-away table were BOTH ranked on the overstated
column; both now carry a generated `RUNNABLE` column, and the top changes hands:

    class                       unlocks ALONE   of those RUNNABLE
    isomerisation                     3                2
    crosslinking                      2                2
    electro-organic-coupling          2                2
    electrolysis  (= M8)              3                1
    catalytic-air-oxidation           3                0     <-- greedy row 3

⚠ **`catalytic-air-oxidation` is the third row of the greedy curve and is worth
ZERO runnable routes.** Read the RUNNABLE column, not the ALONE column.

⚠ **ONE SCOPING QUESTION TO ANSWER FIRST, NOT ASSUME.** `electro-organic-coupling`
(`kolbe-electrolysis`, `adiponitrile-route`) is electrochemistry too, and M8's
brief names only `electrolysis`. **If one milestone covers both it is +5 unlocked
/ +3 runnable and goes back to the top of the queue.** Measure whether one
mechanism covers both rows before choosing between M8 and `isomerisation`.
⚠ And M8 is the only planned item that WILL break the spectator zeros — budget for
re-deriving the five pH values, do not budget for them being unmoved.

⚠⚠ **S6 IS THE PRECEDENT TO READ BEFORE ANY INSTRUMENT JOB, AND S5 BEFORE ANY
FRAGILITY JOB.** S6's brief handed it a number (14 routes) and a list; the number
was wrong (16), the list was missing two, and the list contradicted the prose
beside it. It only came out because the standing predict-then-measure check was
run on a number that looked already-measured. **A recorded measurement is a claim
about a past state of the code, and it can be wrong about its own subject.**

The queue, re-ordered by what it is measured to be WORTH:

1. **⚠⚠ THE TEMPLATE MILESTONE — SEE START WITH.** `isomerisation` (+3 / **2
   runnable**), `crosslinking` (+2 / **2**) and `electro-organic-coupling` (+2 /
   **2**) are the three worth most. **M8 = `electrolysis` is +3 / 1 alone but +5 /
   3 if its scope also covers `electro-organic-coupling`** — measure that first.
   ⚠ Do NOT take `catalytic-air-oxidation` because the greedy curve ranks it
   third: it is worth **zero** runnable routes.
2. **⚠ THE BARE-ELEMENT GAP — S6 MEASURED IT AT 15 ROUTES AND IT IS THE CHEAPEST
   ITEM HERE.** 45 compounds are refused as *a bare element symbol*, correctly —
   the ideal-gas value for `[C]` is the ATOM at Gf +671 kJ/mol while the charcoal
   in the flask is 0. `iron`, `copper` and `nickel` escaped only because S1 needed
   them as solid catalysts. **15 routes are blocked by nothing else**; leverage
   `cobalt` **+3**, then `carbon-graphite` / `platinum` / `silver` at **+2** each.
   The generated table is in `data/catalog/COVERAGE_REPORT.md` under *"The next
   one along"*.
   ⚠⚠ **AND IT IS NOT SECOND-CLASS WORK ON THE COLUMN THAT MATTERS.** S6 moved no
   template-ready route and moved the INTERSECTION **12 → 17**. Curating a species
   and writing a template land on the SAME number there.
   ⚠ **IT HAS A LAYERING QUESTION IN FRONT OF IT, SO IT IS NOT A LOOKUP.**
   `element_data.REFERENCE_STATES` **already carries S0 and the reference state**
   for Zn(s), Ag(s), C(graphite) — but with **`smiles=None`**, because a SOLID
   reference state had nowhere to live until the solid block existed. Mercury
   resolves today precisely because its standard state is a LIQUID and so it got
   a SMILES. Missing is that binding plus the `Cp_solid`/`Vm_solid` pair
   `priced_solid` demands. **Whether that belongs in `element_data` or in
   `mineral_data` is a real decision — a metal is not a mineral** — and it owes
   its own predict-then-measure pass.
3. **⚠ S5's SIXTH INSTRUMENT FAULT, STILL OPEN AND STILL CHEAP.**
   `tolerance_audit.py` reports `QUOTABLE DIGITS MOVE, worst 99.85%` on
   `oil_of_vitriol`, and **that headline is wrong**: four of its five moved lines
   are the CREATED-MATTER residual and every one gets SMALLER, on rows
   `NEXT_SESSION.md` already carries as "NOT AN INVARIANT". **A
   relative-difference test is meaningless on a column whose converged value is
   zero.** `REPORT_ABS` exists for this and 2.9e-05 clears it. Reported, not
   fixed — raising it blunts the test for genuine quantities, so picking the
   number owes its own predict-then-measure pass.
4. **Pyrite** — one mineral entry from `pyrite-roasting` running. Blocked on the
   same-database rule (`Hfs` in WEBBOOK, `S0s` in nothing), which is a rule worth
   keeping, so this needs a SOURCE and not a workaround. ⚠ It is also one of the
   **11 template-ready routes that cannot run**, so closing it is +1 on the
   intersection for one curated entry.
5. **⚠⚠ THE BURNER — THE LIVE FRAGILITY, DEMOTED NOT DISMISSED.** **53 s at rtol
   1e-8 against 0.8 s at the default.** S5 bounded the CRASH and explicitly did
   not bound the THRASHING. BDF is struggling with a liquid layer holding
   **1e-29 mol**, which `LAYER_REABSORB` drains toward zero without ever reaching
   it. **The question nobody has asked is whether a layer below `LAYER_EPS`
   should be *merged discretely* at a step boundary rather than drained
   continuously forever.** ⚠ `merge_phases` already does exactly that at the
   `run` boundary — so this may be a matter of WHEN IT IS CALLED, not of a new
   mechanic. **Measure the layer-2 inventory over the failing run before
   designing anything.** It is at rtol 1e-8, not the default, so nothing a player
   does reaches it.
6. **⚠ `hydrolysis` — AND READ S3's LANDMINE FIRST.** Measured: it unlocks
   **exactly ONE route alone, `vitriol-distillation`**, and that route's step 1
   reads `-> iron-ii-OXIDE` while the engine makes HEMATITE. The whole standalone
   payoff is a route carrying a step whose product the engine does not make.
   ⚠ S3 and S4 disagree about what to do with such a row — S3's was the MECHANISM
   right and the ROW wrong, S4's was the ROW right and the mechanism short. Read
   §S3's "which one is WRONG" check before deciding.
7. **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
   re-scope before scheduling)**, **M9 (polymers, 12 routes)** and **M10 (the
   site balance S1 did not build, 8 routes)**.
8. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
   the *deposition-needs-a-seed* half into a real bound in
   `SolidStateArrays.units`, which is why the mercury retort does not re-form its
   oxide when cooled 289 K below the oxide's threshold. What is still not
   expressible is a solid appearing from NO solid — `hydride-thermal-deposition`
   (`arsine -> arsenic + hydrogen`) is still a mechanism gap for that reason.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§S1, §S3, §S4, §S5 and §S6 are the ones to read**:
  S1's brief asked for one mechanism and the arithmetic said two, S3 found the
  instrument's own OUTPUT was not diffable, S4's brief said to reverse a re-label
  and the arithmetic said keep it, **S5's brief named the wrong LAYER**, and
  **S6's brief handed it a number that was wrong.**
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1, 86 is S2, 87 is
  S3, 88 is S4, 89 is S5, 90 is S6.**
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **S3's split of
  `thermal-decomposition`** and **S4's decision NOT to un-split
  `roasting-to-metal`**, and `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-species-ready-minerals,
  chemsim-jacobian-bound, chemsim-zero-jacobian-column (⚠ its diagnosis was
  CORRECTED by S5), chemsim-element-floor, chemsim-mercury-retort and
  chemsim-generated-artefacts.

```bash
python validation/catalog_coverage.py        # ⚠ READ THE 'BOTH' LINE: 17/173, ~10 s
python tools/build_route_index.py            # ⚠ RUN THIS TOO -- it is the artefact nothing reads
python validation/jacobian_bound.py          # ⚠ S5's standing audit, ~1 min
python examples/mercury_retort.py            # S4, six panels, ~4 s
python examples/roasting_and_the_catalyst_gate.py   # S1, five panels, ~11 s
python examples/lime_cycle.py                # M6, eight panels, ~18 s
python examples/named_routes.py              # M5's 17 routes, ~24 s
python validation/rate_ceiling.py            # M12's standing audit + S4's 4th panel, seconds
python validation/tolerance_audit.py         # S2's standing audit, ~8 min
python -m pytest -q tests/test_jacobian.py   # S5's 11 tests, ~55 s
python -m pytest -q tests/test_mercury_retort.py   # S4's 14 tests, ~4 s
python -m pytest -q tests/test_surface.py        # S1's 38 tests, ~12 s
python -m pytest -q                          # the whole suite
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE IS MINUTES OF SATURATED CPU ON THE USER'S OWN MACHINE.** Run it to
establish a baseline and to verify at the end, not after each change. Say what a
long run will cost before starting one. The tolerance audit is another ~8 minutes
and **`examples/plate_column.py` alone is 12 minutes.**

✔ **THE SUITE WAS GREEN AND MEASURED AT 826 passed in 12:32 at the end of S5.**
⚠ **S6 DID NOT RE-RUN IT, DELIBERATELY AND WITH THE REASON STATED: it changed no
file under `src/` or `tests/`, and nothing under either imports
`validation/catalog_coverage.py`.** The suite is unaffected by construction, not
by assumption — but that is an argument, and the next session should re-establish
the baseline for itself before touching the RHS.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 34 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, a catalyst you have to actually put in
the flask, a route that nothing declares, and a Jacobian that cannot be probed
outside its own state. `SAVE_VERSION` is **5**.
Coverage: **36/218 classes**, **34 templates**, **28/173 template-ready**,
**65/173 species-ready** (was 49) — and ⚠⚠ **17/173 BOTH, which is the only one
of the three a route can be judged on.** S6 moved that one **12 → 17** while
moving no template-ready route at all.

---

# ⚠⚠ WHAT S6 TURNED OUT TO BE: THE BRIEF HANDED IT A NUMBER, AND THE NUMBER WAS WRONG

The brief: `species-ready` asks the plain `ThermochemistryProvider`, which refuses
an ionic lattice by name, while `mineral_data` has priced lattices on the solid
basis since M3. S4 recorded the gap as **14 routes, 49 → at most 63**.

What shipped: `_mineral_fallback` and a `mineral` tier in
`validation/catalog_coverage.py`. **19 compounds move refused → `mineral`;
species-ready 49 → 65; fully-sourced 5 → 14. No `src/` file was touched and no
chemistry moved.**

| column | before | after |
|---|---:|---:|
| routes species-ready | 49 (28.3%) | **65 (37.6%)** |
| routes fully sourced | 5 (2.9%) | **14 (8.1%)** |
| compounds resolving | 1118 (70.6%) | **1137 (71.8%)** |
| formation measured/Benson | 716 (45.2%) | **735 (46.4%)** |
| refused | 465 (29.4%) | **446 (28.2%)** |
| UNIFAC-decomposable | 836 | 836 — **unchanged, by design** |
| routes template-ready | 28/173 | **28/173 — unchanged** |

## ⚠⚠ 1. THE PREDICTION WAS 14 AND THE ANSWER IS 16

The recorded 14 was measured with a **RAW string comparison** of the catalog's
SMILES against the `by_lattice` key, and the catalog spells its salts in a
different fragment order than the canonical table:

    catalog   [Ca+2].[O-]C([O-])=O          [Zn+2].[O-2]
    table     O=C([O-])[O-].[Ca+2]          [O-2].[Zn+2]

| matching rule | routes moved |
|---|---:|
| raw lattice string | 14 ← **the recorded estimate** |
| raw, or the sorted dissolved-ion tuple | 15 |
| **canonical lattice — what the engine itself does** | **16** |

The two missed are `vulcanisation` and **`lime-cycle`** — and `lime-cycle` is the
route S4's own note names *in prose* as the headline case while its list of
fourteen ids omits it. **The number, the list and the prose disagreed with each
other.** Same lesson as S5's four dead triggers in a different costume.

## ⚠⚠ 2. THE RULE HAD TO BE A FALLBACK, NEVER AN OVERRIDE

The obvious implementation — *is this compound a mineral?* — is measurably wrong.
36 catalog compounds sit on a mineral lattice but **17 already resolve as `ion`**:
`sodium-chloride`'s ions are priced, it genuinely dissolves, and it can also
precipitate. Labelling it `mineral` would **downgrade a species the engine handles
in two phases to one it handles in one**, and would have silently cut the
published UNIFAC count. So the fallback fires only where all three providers have
already refused — the engine's own precedence, not a new one. Because every
rescued species was already refused, **UNIFAC does not move by one**, which is the
honest answer: a lattice cannot enter a liquid mixture, by the same verdict that
sent it down the branch.

## ⚠ 3. THE CANONICAL CLAIM WAS VERIFIED, NOT INFERRED

`vessel.py` does a RAW dict lookup on `by_lattice()`, so crediting a spelling the
engine would refuse is the `pyrite-roasting` failure in reverse. What bridges it
is `network/builder.py` line 320, which rebuilds every input SMILES through
`Molecule.from_smiles` before the species list exists. **All 19 rescued minerals
were charged into a real `Vessel` solid block: 19 of 19 at their full 0.02 mol.**

## ⚠⚠ 4. THE COLUMN NOBODY WAS COMPUTING: THE INTERSECTION IS 17, NOT 28

Asked afterwards what the coverage actually IS, S6 measured the one thing none of
the three readiness columns says. **They answer INDEPENDENT questions and the
smallest does not bound the others.**

    species-ready   65        template-ready  28        BOTH   17

**11 of the 28 template-ready routes have a refused species and cannot run** —
`pyrite-roasting`, `tnt-route`, `superphosphate`, `chrome-yellow-route`,
`biodiesel-route` and six more. **This project has quoted 28 as "what could run"
since S4, and it overstates by a factor of 1.6.**

⚠ **AND IT CHANGES WHAT S6 IS WORTH.** Measured both ways: the intersection
without the `mineral` tier is **12**, with it **17**. The milestone that "moved no
template-ready route" moved the runnable count **+5**, more than the last three
content milestones combined. **Curating a species and writing a template are the
SAME axis on this column**, which neither published column can show.

⚠⚠ **AND THE WORK QUEUE WAS RANKED ON THE OVERSTATED COLUMN.** Both the greedy
curve and the one-class-away table counted template unlocks alone; both now carry
a generated RUNNABLE column. `catalytic-air-oxidation` is greedy row 3 and is
worth **zero** runnable routes. See START WITH for the re-ranked queue.

⚠ 17 is an **upper bound on what runs**, not a measured count: a class is credited
when a template would fire on the right substrate at all, and `pyrite-roasting` is
the standing proof that this is not the same as running.

## ⚠ 5. WHAT `species-ready` DOES NOT CLAIM FOR THESE

A mineral resolves **as a crystal**. It can be charged, held and reacted; it still
cannot dissolve, so a step needing one in solution is still not expressible.
**None of the 16 becomes template-ready, and 28/173 is still the honest headline
of this project's coverage.**

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ THE BURNER IS STILL 53 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT.** The
crash is bounded; the thrashing is not. **Still the live one — but it is QUEUE
ITEM 5, not the next job.** It fires only at rtol 1e-8, so nothing a player does
reaches it, and six sessions of engine work against +3 routes is why it waits.

**2. ⚠ A SOLID DECOMPOSITION'S FORWARD CONSTANT CROSSES THE UNIMOLECULAR CEILING
AT 3710 K, INSIDE THE RHS's 5000 K CLAMP.** New in S4, reported by
`validation/rate_ceiling.py`'s fourth panel. Not guarded, on the stated policy:
`A0` multiplies both directions of an affinity flux, so it divides out of
`flux = 0` and moves a CLOCK, not an equilibrium. The retort runs 2810 K below it.

**3. ⚠ `detailed_balance`'s RATE CAP COMPARES A CATALYSED PRE-EXPONENTIAL AGAINST
A LIMIT THAT IS NOT IN ITS UNITS**, so it would fire 10x too eagerly. Bounded in
the class this project forgives, and **it does not fire on any of the five
catalysed templates**, pinned by a test. `validation/rate_ceiling.apparent_A`
undoes the units and the audit is at baseline (`ammonia_synthesis_rev` crosses at
**1335.1 K**; raw it reads 1178.1 K, which is the units error).

**4. THE DEFAULT TOLERANCE, BOUNDED RATHER THAN OPEN.** S2 swept it, S4 re-ran it
after the engine change, and S5 moved `fractional_distillation`'s cuts by ≤ 1e-6
relative — three decades under the audit's own reporting band.
⚠ `validation/tolerance_audit.py` is a STANDING audit: run it after touching the
RHS. It has THREE self-check examples (`lime_cycle`,
`roasting_and_the_catalyst_gate`, `mercury_retort`) which must come out OUTPUT
IDENTICAL, and **`oil_of_vitriol` is sweepable for the first time.** ⚠ Its
`QUOTABLE DIGITS MOVE` headline on `oil_of_vitriol` is WRONG — see item 2 of the
task list.

**5. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever, so
ten times the iron is ten times the rate. Right at low coverage, wrong at high.
M10.

**6. ⚠ NUCLEATION, HALF modelled.** A solid can only grow where one already is —
S4 made that a real bound and the mercury retort demonstrates it. What is still
not expressible is a solid appearing from NO solid: `SurfaceArrays` is first order
and EXTENSIVE in the solid amount, and irreversible by construction.
`hydride-thermal-deposition` is still a mechanism gap for that reason.

**7. ⚠ LIQUID MERCURY IS 99.85% HELD IDEAL**, and the visible cost is that O2 and
SO2 dissolve in the pool on Henry constants **measured in water** transferred
through a ratio of activity coefficients that is 1: **0.14% of the SO2**. Named
and bounded, not hidden — which is exactly what M4 built that flag for.

**8. ⚠ THE FLAT COLUMN IS STILL FLAT, AND THAT IS CORRECT.** A species genuinely
absent from a sealed flask has an identically zero Jacobian column, and **zero is
its derivative.** What S5 changed is that `num_jac` stops reading "I measured
zero" as "I failed to measure". `fragilities`' `kla=0` entry is KEPT rather than
deleted, because the CONFIGURATION still produces flat columns.

**9. ⚠ 45 COMPOUNDS ARE STILL REFUSED AS A BARE ELEMENT, BLOCKING 15 ROUTES.**
New in S6, generated into `COVERAGE_REPORT.md` so it cannot rot. See task 1 — it
is a curation job with a layering decision in front of it.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's clamp is
`T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Eighteen times now.
⚠⚠ **A RECORDED MEASUREMENT IS A CLAIM ABOUT A PAST STATE OF THE CODE, AND IT CAN
BE WRONG ABOUT ITS OWN SUBJECT.** S5 found four of five recorded triggers had
stopped firing. **S6 was handed a measured number and a list of ids: the number
was wrong, the list was short by two, and the list contradicted the prose beside
it.** Re-measure even what looks already-measured.
⚠⚠ **WHEN A NOTE HANDS YOU A NUMBER *AND* A LIST, CHECK THEY AGREE.** The
disagreement is the finding.
⚠⚠ **A NEW CREDIT MUST BE A FALLBACK BEFORE IT IS AN OVERRIDE.** S6's rescue
would have DOWNGRADED 17 species that already resolved better, and silently cut a
published column, if it had asked "is this a mineral" instead of "did everything
else refuse".
⚠⚠ **INSTRUMENT WHICH COLUMN/ROW/SPECIES ACTUALLY FAILS.** S2's diagnosis named
"a species absent from a sealed flask" and the column was liquid layer 2's SO2,
frozen rather than flat.
⚠⚠ **A FOUR-RUN SWEEP IS NOT THE EXAMPLE SET.** S5's first bound was bit-identical
on four runs and moved eight of sixteen examples. For anything in the hot loop,
diff the WHOLE example set.
⚠⚠ **WHEN A NUMERICS CHANGE MOVES A NUMBER, DO NOT COMPARE IT TO THE PREVIOUS
DEFAULT RUN — COMPARE BOTH TO A CONVERGED ONE.**
⚠ **A BRIEF'S EXPECTED OUTCOME IS A HYPOTHESIS.** S4's said a re-label would be
reversed; running it both ways said keep. S1's asked for one mechanism and got
two. S5's named a layer and the measurement named another. S6's named a size and
the measurement named another. **Run the number for the option you are not
taking.**
⚠ **PREDICT THE NUMBER BEFORE YOU MEASURE IT.** S3 predicted +2 classes and +0
routes; S4 predicted +1 class and +1 route. Both came out exactly. ⚠ S5 predicted
"every example byte-identical" and was wrong, twice. ⚠ **S6 predicted 14 and
measured 16** — which is exactly why the prediction is worth writing down.
⚠ **VERIFY A CREDIT BY RUNNING IT, NOT BY READING THE CODE THAT WOULD RUN IT.**
S6 charged all 19 rescued minerals into a real `Vessel` rather than arguing from
`builder.py` line 320. `pyrite-roasting` is what that check exists to prevent.
⚠ **AN `inf` IS USUALLY THE WRONG BOUND, NOT A BOUND NEEDING SOFTENING.** Twice:
S4's seed crystal, S5's state extent.
⚠ **A RELATIVE-DIFFERENCE TEST IS MEANINGLESS ON A COLUMN WHOSE CONVERGED VALUE
IS ZERO.** `0.000e+00 -> 2.728e-07` reads as "99% moved" and means "a residual got
smaller".
⚠⚠ **TWO COLUMNS THAT ANSWER INDEPENDENT QUESTIONS DO NOT BOUND EACH OTHER —
COMPUTE THE INTERSECTION.** template-ready 28 and species-ready 65 were both
published for four milestones while the number that decides whether a route runs,
17, was computed by nothing. **A work queue ranked on either one alone sends
effort at routes that cannot run** — measured: `catalytic-air-oxidation` unlocks
3 routes and 0 runnable ones.
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS — AND THEN AUDIT ITS OUTPUT AND ITS
COVERAGE.** S2's harness invented a finding; S1's coverage audit credited a route
that cannot run; S3's report could not be diffed; S4's rate-ceiling audit made a
claim about a table it does not read; S5's own first audit asserted "every clamped
must read 0" and a rig refuted it; **S6's target column had been understating
itself since M3 and the note recording that was wrong too.**
⚠ **WHEN YOU OVERRIDE THE SOURCE OF A DERIVED QUANTITY, FIND WHAT ELSE WAS
DERIVED FROM THE OLD ONE.** The curated Antoine would silently have orphaned
`Hvap`. ⚠ Same shape in an instrument: S6 added a tier and had to route THREE
hard-coded `measured + benson + ion` sums through one `SOURCED_TIERS` constant, or
the headline would have silently under-counted.
⚠ **A GENERATED FILE NOTHING READS IS THE ONE THAT ROTS.** Regenerate all three
catalog artefacts. ⚠ The root `README.md`'s coverage table is NOT generated —
S4 corrected it once and S6 again.
⚠ **A PHASE LABEL CARRIES A STANDARD STATE.** Adding one is a thermodynamic
change, not a naming change. ⚠ So is a BASIS: a solid-basis Hf is not an
ideal-gas Hf, which is why S6's `mineral` is its own tier and not part of
`measured`.
⚠ A CLASS IS A MECHANISM CLAIM. Read the rows, not the name — and check which
ROUTES a credit moves. When a mechanism does not make a row's product, ask which
of the two is WRONG before deciding the verdict.
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS, and neither is a
converged-looking number at the default tolerance. Re-measure before quoting.
⚠ **BDF IGNORES `jac_sparsity` THE MOMENT `jac` IS CALLABLE.** `BoundedJacobian`
CONSUMES the pattern; handing scipy both would silently drop the column groups
`useful_sparsity` computes.
⚠ Windows console is cp1252: a warning glyph inside a `print()` kills a script.
Docstrings fine, printed text ASCII. (TWENTY-ONE sessions running.)
⚠⚠ **`sed -i` REWRITES EVERY LINE ENDING IN A CRLF FILE.** S3 lost a file to it on
its first edit. This repo is MIXED: markdown and `.psv` are CRLF,
`element_data.py`/`solid_state.py`/`volatility.py`/`catalog_coverage.py` are CRLF
while `vessel.py`/`surface.py`/`vessel_integrator.py`/`jacobian.py` are LF. Use a
binary-mode anchored patcher that reads anchor and replacement without decoding.
**Check `git diff --stat` after the first edit to any file.**
⚠ **HEREDOCS EAT ESCAPES:** `\\n` written into a `python - <<'PY'` heredoc arrives
as `\n` and becomes a real newline inside a Python string. Use the Write/Edit
tools for anything containing a backslash.
⚠ **A GENERATOR CAN LEAK A `numpy` REPR INTO ITS OUTPUT.** `np.float64(59.444)`
went into `element_data.py` and made the module unimportable. Cast to `float` at
the boundary.
⚠ An em dash in a markdown anchor will not match a `--` you typed. MILESTONES.md
uses both.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u`.

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays; RDKit stays in matter.
NO silent approximations. REFUSE loudly rather than return a confident wrong
number — and a LATENT fragility is a third case: report it, do not refuse it.
⚠ **AND REFUSING TO *DISSOLVE* A SPECIES IS NOT REFUSING TO *PRICE* IT.** S6's
whole finding was a column that conflated the two for three milestones.
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?"
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; `solid_state=False`
exactly no crystal reacting; `surface=False` exactly no gas attacking one, and an
all-zero `order_solid` exactly the old kinetics kernel; **`BoundedJacobian` with
its bound lifted exactly BDF's own differencing, bit for bit**; the Born term
exactly zero in PURE water; the five pH values; SAVE_VERSION stores the CONDITION,
never the instant; every gaseous element reference state Hf = Gf = 0 EXACTLY; **a
CONDENSED reference state's ideal-gas record is a MEASUREMENT and must not be
zero**; every METAL Hf = Gf = 0 EXACTLY on the solid basis, and a non-zero result
REFUSED as an allotrope mismatch; a reference state its own database does not
price at Hf = 0 is REFUSED; no mineral pricing differently under the two
providers; `ion_data` and `electrolyte` never subtracted from each other; a
declared rate order may never be reversible; a surface row whose `ln K` is under
+20 is REFUSED; **a solid-state row with no crystal on EITHER side is REFUSED, and
one with no crystal on ONE side falls back to the other — a deposition needs a
seed**; **the four pre-S4 solid-state rows take the raw `units` minimum, bit for
bit**; **an element's `Hvap` is Clausius-Clapeyron on the vapour-pressure curve
`volatility` actually evaluates**; the reflux ratio is the ratio of two drain
conductances out of one condenser, declared rather than inferred; the
fragmentation SEARCH runs only after the greedy pass has been REFUSED; an ion is
never counted in the held-ideal flag; a rate CAP scales BOTH pre-exponentials by
one factor; a template that moves a hydrogen ATOM must collapse explicit Hs; a
declared catalyst is a CONSTANT OF THE MOTION — bit for bit, at every charge; the
tolerance audit's THREE self-check examples come out byte-identical;
**`COVERAGE_REPORT.md` and both `derived/*.psv` come out byte-identical across
`PYTHONHASHSEED` values**; **the `mineral` tier is a FALLBACK consulted only after
all three providers refuse, so no species that resolves today is ever re-labelled
by it**; **`validation/jacobian_bound.py` panel 3 reads 0 clamped columns on every
single vessel**; **a lattice may REACT and may never DISSOLVE — the fusion law is
still 407x wrong in both directions, and neither M6 nor S1 nor S3 nor S4 nor S5
nor S6 softened that by one digit.**

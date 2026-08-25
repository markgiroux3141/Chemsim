We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M12, S1, S2, S3 and S4 are DONE.**

**START WITH: the `LAYER_REABSORB`-style honest diagonal on the gas block.** It
is the oldest live engine fragility and S4 just gave it a second confirmed
trigger and a fix precedent. The trap is *a species in the network but absent
from a sealed flask*: the Jacobian column is identically zero, `num_jac`'s
perturbation factor inflates to inf, BDF gets a NaN Jacobian. S2 found that a
TIGHT TOLERANCE on a flask holding a trace does it too — `oil_of_vitriol` cannot
be run at rtol 1e-8 at all. Hot loop, moves invariants, wants a session of its
own.

⚠ **S4 IS THE PRECEDENT TO READ BEFORE TOUCHING IT.** S4 hit an unbounded
Jacobian from the other direction — an `inf` in `units_rev`, not in `num_jac` —
and the fix was NOT a clip: it was noticing that infinity was the wrong BOUND
and asking what the finite one means physically. That question is available here
too and nobody has asked it yet.

After that, in order:

1. **⚠⚠ TEACH `species-ready` ABOUT `mineral_data`** — cheap, and it is a
   PUBLISHED number that has been understating itself since M3 by **14 routes**
   (49 → at most 63 of 173). See finding 3 below. ⚠ It redefines a column, so run
   the standing check first: **predict which routes move, then measure**, and do
   not credit anything until the prediction has come out right.
2. **Pyrite** — one mineral entry from `pyrite-roasting` running. Blocked on the
   same-database rule (`Hfs` in WEBBOOK, `S0s` in nothing), which is a rule worth
   keeping, so this needs a SOURCE and not a workaround.
3. **⚠ `hydrolysis` IS GREEDY RANK 4 — AND READ S3's LANDMINE FIRST.** Measured:
   it unlocks **exactly ONE route alone, `vitriol-distillation`**, and that
   route's step 1 reads `-> iron-ii-OXIDE` while the engine makes HEMATITE. The
   whole standalone payoff of the 4th-ranked template is a route carrying a step
   whose product the engine does not make. ⚠ S3 and S4 disagree about what to do
   with such a row — S3's is the MECHANISM being right and the ROW wrong, S4's
   was the ROW right and the mechanism short. Read §S3's "which one is WRONG"
   check before deciding.
4. **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
   re-scope before scheduling)**, then **M8+ (electrochemistry — ⚠ that one WILL
   break the spectator zeros)** and **M10 (the site balance S1 did not build)**.
5. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
   the *deposition-needs-a-seed* half into a real bound in
   `SolidStateArrays.units`, which is why the mercury retort does not re-form its
   oxide when cooled 289 K below the oxide's threshold. What is still not
   expressible is a solid appearing from NO solid — `hydride-thermal-deposition`
   (`arsine -> arsenic + hydrogen`) is still a mechanism gap for that reason.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§S1, §S3 and §S4 are the ones to read**: S1's brief
  asked for one mechanism and the arithmetic said two, S3 found the instrument's
  own OUTPUT was not diffable, and S4's brief said to reverse a re-label and the
  arithmetic said keep it.
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1, 86 is S2, 87 is
  S3, 88 is S4.**
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **S3's split of
  `thermal-decomposition`** and **S4's decision NOT to un-split
  `roasting-to-metal`**, and `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-mercury-retort,
  chemsim-surface-reactions, chemsim-solid-state-reactions,
  chemsim-zero-jacobian-column, chemsim-element-floor and
  chemsim-generated-artefacts.

```bash
python examples/mercury_retort.py            # S4, six panels, ~4 s
python examples/roasting_and_the_catalyst_gate.py   # S1, five panels, ~11 s
python examples/lime_cycle.py                # M6, eight panels, ~17 s
python examples/named_routes.py              # M5's 17 routes, ~24 s
python validation/rate_ceiling.py            # M12's standing audit + S4's 4th panel, seconds
python validation/catalog_coverage.py        # 36/218, 28/173, ~10 s
python tools/build_route_index.py            # ⚠ RUN THIS TOO -- it is the artefact nothing reads
python validation/tolerance_audit.py         # S2's standing audit, ~8 min
python -m pytest -q tests/test_mercury_retort.py   # S4's 14 tests, ~4 s
python -m pytest -q tests/test_surface.py        # S1's 38 tests, ~12 s
python -m pytest -q tests/test_solid_state.py    # M6's 31 tests, ~24 s
python -m pytest -q                          # the whole suite
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE IS MINUTES OF SATURATED CPU ON THE USER'S OWN MACHINE.** Run it to
establish a baseline and to verify at the end, not after each change. Say what a
long run will cost before starting one. The tolerance audit is another ~8 minutes.

✔ **THE SUITE IS GREEN AND THE NUMBER IS MEASURED: 815 passed in 11:50**, at the
end of S4. That is the first measured green number since S1 — S2 and S3 both
handed over "796 passed / 1 failed, the failure is fixed but the green number is
not measured". It is measured now.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 34 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, a catalyst you have to actually put in
the flask, and **a route that nothing declares**. `SAVE_VERSION` is **5**.
Coverage: **28/173 template-ready routes**, **36/218 classes**, **34 templates**.

---

# ⚠⚠ WHAT S4 TURNED OUT TO BE: THE ROUTE WAS THE CHEAP HALF

The brief was "curate mercury, declare `2 HgO -> 2 Hg + O2`, and the route
becomes emergent". All of that is true and the route is exact —
**0.020000000000 mol of mercury and 0.020000000000 mol of SO2 from 0.02 mol of
cinnabar, on 0.020000 mol of oxygen** — which is `mercury-from-cinnabar` step 1
coefficient for coefficient, out of a 2:3:2:2 and a 2:2:1 that do not mention
each other.

**Four findings are bigger than the route.**

## ⚠⚠ 1. THE BRIEF SAID TO REVERSE S1's RE-LABEL. MEASURED BOTH WAYS, IT WAS KEPT

| | classes | template-ready routes |
|---|---|---|
| keep `roasting-to-metal` | **36/218** | 28/173 |
| fold back into `roasting` | 35/217 | 28/173 |

**The routes are identical**, so the choice is only about what the class column
SAYS — and `roasting-to-metal` records a MECHANISM difference rather than an
outcome: this ore's oxide does not survive the furnace that makes it, which is
why one row needs two mechanisms where the other four need one.
`solid-carbonation` is the precedent, an emergent pair under a name of its own.
Folding back would delete the distinction S1 paid to find, for a smaller
denominator. ⚠ **A brief's expected outcome is a hypothesis, and the arithmetic
is what settles it — run BOTH numbers, not just the one you expect.**

## ⚠⚠ 2. THE FIRST ROW WHOSE PRODUCTS ARE ALL GAS, AND INFINITY WAS THE WRONG BOUND

`SolidStateArrays.units_rev` is a minimum over the solids FORMED. This is the
first row that forms none, and the minimum of an empty set is `+inf`, which the
RHS multiplies by a negative affinity. Measured before it was fixed: **a sealed
1 L retort holding 0.5 mol of montroydite at 900 K raised `array must not
contain infs or NaNs`** once `Q` crossed `K` — `ln K` is only +9.2 there.

⚠ **AND THE FAILURE HAD A CHARGE THRESHOLD AS WELL AS A TEMPERATURE ONE.** At
0.05 mol in the same flask `Q` never reaches `K` and the run is clean. **The
small charge is the one an example would have been written with**, so the bug
would have shipped.

**The fix was not a clip.** The four existing rows already say what the right
bound is: calcination's reverse is bounded by `n(CaO)` — the SEED the carbonate
grows on — and not by the CO2 pressure, which lives in `Q`. This engine cannot
nucleate a solid from nothing, so a row with no solid product deposits onto its
own REACTANT crystal. `units` therefore stays a COMMON FACTOR (the 0.5 mol run
now stalls at 71.8% with Q = K to 0.05%), and an exhausted charge stops the
reaction in BOTH directions. **The nucleation gap became a modelled bound rather
than a workaround**, and the four pre-S4 rows are bit-for-bit unmoved.

## ⚠⚠ 3. TWO INSTRUMENTS WERE WRONG, AND THE NEW ROW IS WHAT FOUND THEM

* **`CURATED_FORMATION` falsely refused CRC's own measurement.** It is a PREFIX
  MATCH ON A PROVENANCE STRING, so what it tests is how a sentence begins. A
  GASEOUS element reference state says "element reference state (gaseous)" and
  passes; a CONDENSED one says "Hf and S0 both from CRC …" and was read as an
  ESTIMATE. **It would have refused a row evolving Br2, I2 or S8 identically.**
  Widened by one prefix — the weakness is the mechanism, and moving the tier into
  `ThermoData` reaches every Layer-1 provider, so it is stated rather than done.
* **`validation/rate_ceiling.py` could not see the table it needed to.** Its
  summary claims "nothing approaches the unimolecular ceiling" — a claim about
  every rate constant in the project — while its panels walk `net.reactions`,
  which `SOLID_STATE_REACTIONS` never becomes. **A fourth panel now reads it.**
  The claim holds at 298 K by 26 decades. The hot half does not: S4's row is
  **1.93e18 1/s and crosses 1e14 at 3710 K, INSIDE the RHS's own 5000 K clamp** —
  the first row in the project to do so — and `sulfate-thermal-decomposition`
  crosses at 7543 K and had never been measured either. Reported, not guarded.

* **⚠⚠ AND A THIRD, FROM RECONCILING THE REPORT DIFF LINE BY LINE:
  `species-ready` IS BLIND TO `mineral_data`.** It asks the plain
  `ThermochemistryProvider`, which REFUSES A LATTICE BY NAME — correctly, the
  fusion law being 407x wrong for one. But a lattice has had a home since M3, and
  it is what precipitation, `SolidStateArrays` and `SurfaceArrays` all price
  from. **Measured: 14 routes read species-UNREADY while every refused species is
  a mineral this project prices — 49 of 173, where the honest number is at most
  63.** Among them `lime-cycle`, which M6 declared complete end to end from
  limestone and which its own example runs, and `haber-bosch` and
  `methanol-synthesis`, whose only "refused" species is **the solid CATALYST S1
  curated so it could be put in the flask**.

  ⚠⚠ **It is the exact OPPOSITE shape to `pyrite-roasting`** — that reads
  template-ready and does NOT run; this reads species-unready and DOES. Two
  columns, two directions of error, neither a bug in the engine.

  ⚠ **NOT FIXED, DELIBERATELY, AND THIS IS THE NEXT SESSION'S INSTRUMENT JOB.**
  It redefines a PUBLISHED column, so it owes the standing "which routes does it
  move" check (predicted before measured) and a full verification pass. Recorded
  at the line that computes it, in `validation/catalog_coverage.py`.

**Four sessions running, the instrument was part of the story — and this one had
THREE.**

## ⚠⚠ 4. "BOILS AT 1 ATM IS NOT AN INDEPENDENT CHECK" ARRIVED WITH A PRICE TAG

Mercury's vapour pressure comes from Lee-Kesler like every other element's. Over
a liquid METAL that reads **38.3 kPa at 523 K against CRC's 10.0 — 3.8x — while
agreeing at the boiling point to five figures, because it is ANCHORED there.**
The condenser panel would have been wrong by that factor and nothing would have
said so. The condensed-reference-state cross-check is what caught it: **+2.808
kJ/mol with the estimate, +0.012 with a curated NIST Antoine.**

⚠ And dropping the curated curve in would have BROKEN a stated invariant.
`build_element_data` differentiates `Hvap` out of the Lee-Kesler curve precisely
so the latent heat cannot disagree with the vapour pressure — but `volatility`
prefers a curated Antoine, so that is no longer the curve the engine evaluates.
The generator now takes Clausius-Clapeyron on the CURATED curve: **59.444 kJ/mol
against Lee-Kesler's 57.344 and CRC's measured 59.11.** *When you override the
source of a derived quantity, find what else was derived from the old one.*

---

# ⚠⚠ THE MECHANICS NOBODY WROTE, WHICH IS WHAT THIS PROJECT IS FOR

| | measured |
|---|---|
| the intermediate is INVISIBLE | montroydite's inventory is the roast's rate times its own clock: **8e-7 mol at the start, 3.4e-8 by 20 ks.** Its clock at 900 K is 0.2405 s against the roast's 5,918 s |
| **the two clocks CROSS** | 304.4 kJ/mol DERIVED against 150 DECLARED, so cooling slows the decomposition far faster — equal at **611.7 K**. The oxide's share of the mercury released: **2.0e-6 / 4.3e-4 / 1.9e-2 / 0.341 / 0.913** at 900 / 773 / 700 / 650 / 600 K. **Nothing gates on temperature anywhere** |
| a retort CONDENSES | cool the same flask to 400 K and **97.9%** of the metal is a liquid pool |
| the oxide CANNOT come back | at 400 K, **289 K below its own threshold**, in a flask full of Hg vapour and O2 |

---

# ⚠ MERCURY, AND WHY IT WAS REFUSED TWICE OVER

`[Hg]` was in `LATTICE_ELEMENTS` as "a metallic lattice" AND in the monatomic
refusal list as "the ideal-gas record is the ATOM, not the substance". Both are
true of the bonding and false of the REPRESENTATION:

* **its reference state is a LIQUID with a boiling point**, which this engine's
  liquid block holds — so it belongs with Br2 in `REFERENCE_SMILES`;
* **its vapour IS the atom** — it boils monatomic at 629.8 K — so `[Hg]`'s
  ideal-gas record is exactly what is in the retort. That is what fails for
  `[C]`, `[S]` and `[Fe]`, and mercury has one condensed form.

Hf **+61.40**, Gf **+31.853** kJ/mol. Pinning a condensed reference state to zero
is the I2 bug. **Two free exact checks came with it**: Cp = 5R/2 = 20.786
J/(mol K) EXACTLY at every temperature (the only non-fitted Cp in that table
besides the gaseous zeros), and the reference-state identity closing to
**+0.012 kJ/mol** — the tightest of the four (Br2 −0.053, I2 +0.139, S8 +3.052).

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ THE ZERO-JACOBIAN-COLUMN TRAP HAS TWO TRIGGERS, AND ONE MAKES AN EXAMPLE
UNRUNNABLE.** *A species in the network but absent from a sealed flask*: the
column is identically zero, `num_jac`'s perturbation factor inflates to inf, BDF
gets a NaN Jacobian. S2 found the second: **a TIGHT TOLERANCE on a flask holding
a trace.** `oil_of_vitriol` RAISES at rtol 1e-8 in `burn(690 K, s8=0.002,
o2=0.10)` — `lu_factor` gets `array must not contain infs or NaNs` after 50.7 s
of thrashing. ⚠ Its numbers are CONFIRMED, not suspect: SO2 = 0.016000 at the
default and 0.016000 at rtol 1e-8 with a 1e-9 mol trace charged. **The fix is
item 1 on the list above.** ⚠ A declared solid CATALYST does not trip it — its
column is populated even at zero amount and what is zero is its ROW.

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

**4. THE DEFAULT TOLERANCE, BOUNDED RATHER THAN OPEN.** S2 swept it and S4
re-ran it after the engine change: **ZERO examples print a quotable digit that
moves**, 5 move below 0.1% (S2's exact list), 7 are byte-identical.
⚠ `validation/tolerance_audit.py` is a STANDING audit: run it after touching the
RHS. It has THREE self-check examples now (`lime_cycle`,
`roasting_and_the_catalyst_gate`, `mercury_retort`) and all three came out
OUTPUT IDENTICAL at 1.00 / 0.99 / 1.00. ⚠ Its "tight is faster in N of M"
counter reads 1 of 12 against S2's 2 of 11 — that is WALL-CLOCK JITTER on a
self-check example whose output is identical by construction, not a regression.

**5. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever, so
ten times the iron is ten times the rate. Right at low coverage, wrong at high.
M10.

**6. ⚠ NUCLEATION, now HALF modelled.** A solid can only grow where one already
is — S4 made that a real bound and the mercury retort demonstrates it. What is
still not expressible is a solid appearing from NO solid: `SurfaceArrays` is
first order and EXTENSIVE in the solid amount, and irreversible by construction.
`hydride-thermal-deposition` is still a mechanism gap for that reason.

**7. ⚠ LIQUID MERCURY IS 99.85% HELD IDEAL**, and the visible cost is that O2 and
SO2 dissolve in the pool on Henry constants **measured in water** transferred
through a ratio of activity coefficients that is 1: **0.14% of the SO2**. Named
and bounded, not hidden — which is exactly what M4 built that flag for.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's clamp is
`T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Sixteen times now.
⚠ **A BRIEF'S EXPECTED OUTCOME IS A HYPOTHESIS.** S4's said the re-label would be
reversed; running the arithmetic BOTH ways said keep it. S1's asked for one
mechanism and got two. **Run the number for the option you are not taking.**
⚠ **PREDICT THE NUMBER BEFORE YOU MEASURE IT.** S3 predicted +2 classes and +0
routes; S4 predicted +1 class and +1 route on a one-step route. Both came out
exactly, and the prediction is what makes the measurement evidence.
⚠ **AN `inf` IS USUALLY THE WRONG BOUND, NOT A BOUND NEEDING SOFTENING.** Ask
what the finite one MEANS physically before reaching for a clip.
⚠ **A FAILURE CAN HAVE A CHARGE THRESHOLD AS WELL AS A TEMPERATURE ONE**, and the
small charge is the one an example gets written with.
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS — AND THEN AUDIT ITS OUTPUT AND ITS
COVERAGE.** S2's harness invented a finding; S1's coverage audit credited a route
that cannot run; S3's report could not be diffed; S4's rate-ceiling audit made a
claim about a table it does not read, and a curated-source guard refused CRC's
own row for the shape of a sentence.
⚠ **WHEN YOU OVERRIDE THE SOURCE OF A DERIVED QUANTITY, FIND WHAT ELSE WAS
DERIVED FROM THE OLD ONE.** The curated Antoine would silently have orphaned
`Hvap`.
⚠ **A GENERATED FILE NOTHING READS IS THE ONE THAT ROTS.** Regenerate all three
catalog artefacts, not just the one whose numbers you are quoting. ⚠ The root
`README.md`'s coverage table had rotted since M5 and S4 corrected it — that one
is not generated at all, which is worse.
⚠ **A PHASE LABEL CARRIES A STANDARD STATE.** Adding one is a thermodynamic
change, not a naming change.
⚠ A CLASS IS A MECHANISM CLAIM. Read the rows, not the name — and check which
ROUTES a credit moves. When a mechanism does not make a row's product, ask which
of the two is WRONG before deciding the verdict.
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS, and neither is a
converged-looking number at the default tolerance. Re-measure before quoting.
⚠ Windows console is cp1252: a warning glyph inside a `print()` kills a script.
Docstrings fine, printed text ASCII. (NINETEEN sessions running.)
⚠⚠ **`sed -i` REWRITES EVERY LINE ENDING IN A CRLF FILE.** S3 lost a file to it on
its first edit — 826/826 on a one-line change. This repo is MIXED: markdown and
`.psv` are CRLF, `element_data.py`/`solid_state.py`/`volatility.py` are CRLF while
`vessel.py`/`surface.py`/`vessel_integrator.py` are LF. Use a binary-mode anchored
patcher that reads the anchor and replacement from FILES (so no shell or heredoc
can eat a backslash) and never decodes. **Check `git diff --stat` after the first
edit to any file.**
⚠ **HEREDOCS EAT ESCAPES:** `\\n` written into a `python - <<'PY'` heredoc arrives
as `\n` and becomes a real newline inside a Python string, so an anchored patch
silently matches nothing. Use the Write tool for anything containing a backslash.
⚠ **A GENERATOR CAN LEAK A `numpy` REPR INTO ITS OUTPUT.** `np.float64(59.444)`
went into `element_data.py` and made the module unimportable — which then broke
the generator, because it imports what it writes. Cast to `float` at the boundary.
⚠ An em dash in a markdown anchor will not match a `--` you typed. MILESTONES.md
uses both.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u`.

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays; RDKit stays in matter.
NO silent approximations. REFUSE loudly rather than return a confident wrong
number — and a LATENT fragility is a third case: report it, do not refuse it.
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?"
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; `solid_state=False`
exactly no crystal reacting; `surface=False` exactly no gas attacking one, and an
all-zero `order_solid` exactly the old kinetics kernel; the Born term exactly
zero in PURE water; the five pH values; SAVE_VERSION stores the CONDITION, never
the instant; every gaseous element reference state Hf = Gf = 0 EXACTLY; **a
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
**`COVERAGE_REPORT.md` comes out byte-identical across `PYTHONHASHSEED` values**;
**a lattice may REACT and may never DISSOLVE — the fusion law is still 407x wrong
in both directions, and neither M6 nor S1 nor S3 nor S4 softened that by one
digit.**

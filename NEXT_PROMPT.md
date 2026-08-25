We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M12, S1, S2, S3, S4 and S5 are DONE.**

**START WITH: ⚠⚠ TEACH `species-ready` ABOUT `mineral_data`.** Cheap, and it is a
PUBLISHED number that has been understating itself since M3 by **14 routes**
(49 → at most 63 of 173). `species-ready` asks the plain
`ThermochemistryProvider`, which REFUSES A LATTICE BY NAME — correctly, the
fusion law being 407x wrong for one — but a lattice has had a home since M3, and
it is what precipitation, `SolidStateArrays` and `SurfaceArrays` all price from.
Among the 14 are `lime-cycle`, which M6 declared complete end to end and whose
own example runs, and `haber-bosch`/`methanol-synthesis`, whose only "refused"
species is **the solid CATALYST S1 curated so it could be put in the flask.**
It is recorded at the line that computes it, in `validation/catalog_coverage.py`.

⚠ **IT REDEFINES A PUBLISHED COLUMN**, so run the standing check first: **predict
which routes move, then measure**, and do not credit anything until the
prediction has come out right. ⚠ It is the exact OPPOSITE shape to
`pyrite-roasting` — that reads template-ready and does NOT run; these read
species-unready and DO. Two columns, two directions of error, neither an engine
bug.

⚠⚠ **S5 IS THE PRECEDENT TO READ BEFORE ANY INSTRUMENT JOB.** S5's brief named a
fix (an honest diagonal on the gas block) and the arithmetic named a different
one, in a different layer — because the FIRST thing it did was re-run all five
recorded triggers, and four of them no longer reproduce. **A recorded fragility
is a claim about a past state of the code.** Then its first bound looked safe on
a four-run sweep and moved eight of the sixteen examples. Both halves apply here.

After that, in order:

1. **Pyrite** — one mineral entry from `pyrite-roasting` running. Blocked on the
   same-database rule (`Hfs` in WEBBOOK, `S0s` in nothing), which is a rule worth
   keeping, so this needs a SOURCE and not a workaround.
2. **⚠ `hydrolysis` IS GREEDY RANK 4 — AND READ S3's LANDMINE FIRST.** Measured:
   it unlocks **exactly ONE route alone, `vitriol-distillation`**, and that
   route's step 1 reads `-> iron-ii-OXIDE` while the engine makes HEMATITE. The
   whole standalone payoff of the 4th-ranked template is a route carrying a step
   whose product the engine does not make. ⚠ S3 and S4 disagree about what to do
   with such a row — S3's was the MECHANISM right and the ROW wrong, S4's was the
   ROW right and the mechanism short. Read §S3's "which one is WRONG" check
   before deciding.
3. **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
   re-scope before scheduling)**, then **M8+ (electrochemistry — ⚠ that one WILL
   break the spectator zeros)** and **M10 (the site balance S1 did not build)**.
4. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
   the *deposition-needs-a-seed* half into a real bound in
   `SolidStateArrays.units`, which is why the mercury retort does not re-form its
   oxide when cooled 289 K below the oxide's threshold. What is still not
   expressible is a solid appearing from NO solid — `hydride-thermal-deposition`
   (`arsine -> arsenic + hydrogen`) is still a mechanism gap for that reason.
5. **⚠ THE BURNER IS STILL 53 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT.** S5
   bounded the crash, not the thrashing: BDF is genuinely struggling with a
   liquid layer holding **1e-29 mol**, which `LAYER_REABSORB` drains toward zero
   without ever reaching it. The question nobody has asked is whether a layer
   below `LAYER_EPS` should be *merged discretely* at a step boundary rather than
   drained continuously forever. ⚠ `merge_phases` already does exactly that at
   the `run` boundary — so this may be a matter of when it is called, not of a
   new mechanic. **Measure the layer-2 inventory over the failing run before
   designing anything.**

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§S1, §S3, §S4 and §S5 are the ones to read**: S1's
  brief asked for one mechanism and the arithmetic said two, S3 found the
  instrument's own OUTPUT was not diffable, S4's brief said to reverse a re-label
  and the arithmetic said keep it, and **S5's brief named the wrong LAYER.**
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1, 86 is S2, 87 is
  S3, 88 is S4, 89 is S5.**
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **S3's split of
  `thermal-decomposition`** and **S4's decision NOT to un-split
  `roasting-to-metal`**, and `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-jacobian-bound,
  chemsim-zero-jacobian-column (⚠ its diagnosis was CORRECTED by S5),
  chemsim-mercury-retort, chemsim-surface-reactions,
  chemsim-solid-state-reactions and chemsim-generated-artefacts.

```bash
python validation/jacobian_bound.py          # ⚠ S5's standing audit, ~1 min
python examples/mercury_retort.py            # S4, six panels, ~4 s
python examples/roasting_and_the_catalyst_gate.py   # S1, five panels, ~11 s
python examples/lime_cycle.py                # M6, eight panels, ~18 s
python examples/named_routes.py              # M5's 17 routes, ~24 s
python validation/rate_ceiling.py            # M12's standing audit + S4's 4th panel, seconds
python validation/catalog_coverage.py        # 36/218, 28/173, ~10 s
python tools/build_route_index.py            # ⚠ RUN THIS TOO -- it is the artefact nothing reads
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

✔ **THE SUITE IS GREEN AND THE NUMBER IS MEASURED: 826 passed in 12:32**, at
the end of S5.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 34 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, a catalyst you have to actually put in
the flask, a route that nothing declares, and **a Jacobian that cannot be probed
outside its own state.** `SAVE_VERSION` is **5**.
Coverage: **28/173 template-ready routes**, **36/218 classes**, **34 templates**
(unchanged — S5 moved no chemistry).

---

# ⚠⚠ WHAT S5 TURNED OUT TO BE: THE FIX WAS SCHEDULED FOR THE WRONG LAYER

The brief: a `LAYER_REABSORB`-style honest diagonal on the GAS block, to close the
trap *a species in the network but absent from a sealed flask has an identically
zero Jacobian column*. What shipped: `src/chemsim/numerics/jacobian.py`, a bound
on BDF's differencing STEP, at all three `solve_ivp` sites. **The gas block was
never touched and no chemistry moved.**

## ⚠⚠ 1. FOUR OF THE FIVE RECORDED TRIGGERS DO NOT REPRODUCE

| trigger | on record | measured now |
|---|---|---|
| M6's sealed kiln, 0.05 mol, N2/O2 absent | RAISED, CO2 hit −2.572 mol | clean, `p/K − 1 = −1.56e−04` |
| ... at 0.1 / 0.4 / 1.0 mol | clean | clean |
| `fragilities`' `kla=0`, empty headspace | named | never made to fire, then or now |
| a vessel at rest | short-circuited | short-circuited |
| **S2's `oil_of_vitriol` at rtol 1e-8** | RAISES after 50.7 s | **RAISES after 52.7 s ✔** |

⚠ The kiln stopped failing because **S4 changed `SolidStateArrays.units`**, not
because anything was fixed. **A fragility that no longer fires is not one that was
closed, and the difference is only visible if you re-run it.**

## ⚠⚠ 2. THE ONE THAT FIRES IS IN LIQUID LAYER 2, AND `LAYER_REABSORB` IS THE CAUSE

Of 4322 `num_jac` calls in the failing run, **exactly ONE column reaches `inf`**:
liquid layer 2's SO2, holding **8.21e-29 mol**. Every other column tops out at
1.49e+3. It is not absent and not flat — it is FROZEN. `LAYER_REABSORB` drains an
empty layer 2 at `−1.0·drain2·nL2`, **strictly negative**, so `num_jac` takes
`f_sign = −1` and steps DOWNWARD into the RHS's own `np.maximum(y, 0.0)`:

    h            -2.2e-24  -2.2e-19  -2.2e-14  -2.2e-09  -2.2e-04  -2.2e+06
    max |diff|    8.84e-29  8.84e-29  8.84e-29  8.84e-29  8.84e-29  8.84e-29

**Constant over thirty decades of step size**, against a `scale` of 8.37e-14 taken
from a different species' row. Twenty-eight consecutive calls at one unchanged
state climb a decade each; two hundred later the factor reads **2.220e+307**.

⚠⚠ **The term the brief named as the PRECEDENT to copy is what points the probe at
the clamp**, and a diagonal on the gas block could not have reached that column.

## ⚠⚠ 3. THE FIRST BOUND LOOKED SAFE ON FOUR RUNS AND MOVED EIGHT OF SIXTEEN

`h = factor · max(atol, |y_j|)`, so the obvious bound is "`factor = 1` moves the
variable by all of itself". **False where it matters**: when `|y_j| ≤ atol` the
fraction is of ATOL, so `factor = 149` on an absent species is a 1.5e-7 mol probe
of a 0.1 mol flask. Swept on four runs: all bit-identical. Run over all sixteen
examples: **8 moved**, six in a real digit — `roasting` SO2 **0.000201 → 0.000197
mol**, `fractional_distillation` tail **0.0702 → 0.0711** and **+59% wall clock**,
`multistep_prep` closure 100.0127% → 100.0017%.

**The bound that survived is the STATE'S OWN EXTENT and has no constant in it:**

    |h_j| <= max_i |y_i|    i.e.   factor_j <= max_i |y_i| / max(atol, |y_j|)

*A difference quotient is a derivative of THIS system only while the probe stays
inside it.* Every finite ceiling from 1e2 to 1e14 fixes the crash, so what matters
is finiteness and the value is free to mean something.

## ⚠⚠ 4. IT BINDS ON A RIG, AND ONLY A CONVERGED RUN CAN JUDGE THAT

`fractional_distillation` wants **3.252e+12** and is clamped in **232 of 1833**
Jacobians.

| | converged rtol 1e-8 | default UNBOUND | default BOUND |
|---|---|---|---|
| forerun | 0.43671495 | 0.43671550 | 0.43671561 |
| heart | 0.55620830 | 0.55620760 | 0.55620765 |
| tail | 0.07016219 | 0.07016210 | 0.07016229 |
| pot T / K | 408.20578700 | 408.20567700 | 408.20573700 |

⚠ At rtol 1e-8 the heart and tail are **BIT-IDENTICAL** bounded and unbounded, so
the two converge to the same answer. At the default neither is systematically
nearer, and every difference is **≤ 1e-6 relative, three decades under the 1e-3
band `tolerance_audit.py` itself calls a quotable digit.** ⚠ And 3.25e+12 against
`atol = 1e-9` is a **3250-unit probe** on a species holding nothing, in a rig
whose whole contents are a few mol: the seventh-figure move is the difference
between two fictions. ⚠ The rig runs ~122 Jacobians per solve against the ~316 an
overflow needs — **one longer run away from the same crash.**

## ⚠⚠ 5. S2's COVERAGE GAP IS CLOSED — AND THE SWEEP EXPOSED A SIXTH INSTRUMENT FAULT

`KNOWN_REFUSAL` is empty and `oil_of_vitriol` is in `EXPENSIVE`. ⚠ S2's diagnosis
was **right about the answer and wrong about the column**.

`--only oil_of_vitriol` now **completes in 1061 s tight against 57 s loose
(18.5x)** — and reports `QUOTABLE DIGITS MOVE, worst 99.85%`. ⚠⚠ **That headline
is wrong.** Four of its five moved lines are the CREATED-MATTER residual and
every one gets SMALLER (900 K 4.038e-08 → 6.166e-11; 690 K 2.935e-05 →
2.728e-07): a residual converging toward zero, and exactly the rows
`NEXT_SESSION.md` already carries as **"NOT AN INVARIANT"**. The one physical
number among the five moves **1.5154e-03 → 1.5155e-03, rel 6.6e-05 — three
decades under the audit's own 1e-3 band.**

⚠⚠ **A RELATIVE-DIFFERENCE TEST IS MEANINGLESS ON A COLUMN WHOSE CONVERGED VALUE
IS ZERO.** `0.000e+00 → 2.728e-07` reads as "99% moved" and means "a residual got
smaller". `REPORT_ABS` exists for this and 2.9e-05 clears it. **Reported, not
fixed** — raising it blunts the test for genuine quantities, and picking the
number owes its own predict-then-measure pass. **This is a good cheap first job
if the `species-ready` work stalls.**

---

# ⚠ THE FRAGILITIES

**1. ⚠ THE BURNER IS STILL 53 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT.** The
crash is bounded; the thrashing is not. See item 5 above — this is the live one.

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
IDENTICAL, and **`oil_of_vitriol` is sweepable for the first time.**

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
its derivative.** S5 did not change that and should not have: what it changed is
that `num_jac` stops reading "I measured zero" as "I failed to measure".
`fragilities`' `kla=0` entry is KEPT rather than deleted, because the
CONFIGURATION still produces flat columns and the bound was measured on the
trigger that FIRED rather than on that one.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's clamp is
`T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Seventeen times now.
⚠⚠ **A RECORDED FRAGILITY IS A CLAIM ABOUT A PAST STATE OF THE CODE.** Re-run
every trigger before designing the fix — S5 found four of five had stopped firing,
one of them because a DIFFERENT session changed a bound.
⚠⚠ **INSTRUMENT WHICH COLUMN/ROW/SPECIES ACTUALLY FAILS.** S2's diagnosis named
"a species absent from a sealed flask" and the column was liquid layer 2's SO2,
frozen rather than flat. The diagnosis was right about the ANSWER and wrong about
the CAUSE, which is the combination that survives review.
⚠⚠ **A FOUR-RUN SWEEP IS NOT THE EXAMPLE SET.** S5's first bound was bit-identical
on four runs and moved eight of sixteen examples. For anything in the hot loop,
diff the WHOLE example set.
⚠⚠ **WHEN A NUMERICS CHANGE MOVES A NUMBER, DO NOT COMPARE IT TO THE PREVIOUS
DEFAULT RUN — COMPARE BOTH TO A CONVERGED ONE.** That is what turned
`fractional_distillation`'s seventh figure from a regression into solver noise.
⚠ **A BRIEF'S EXPECTED OUTCOME IS A HYPOTHESIS.** S4's said a re-label would be
reversed; running it both ways said keep. S1's asked for one mechanism and got
two. S5's named a layer and the measurement named another. **Run the number for
the option you are not taking.**
⚠ **PREDICT THE NUMBER BEFORE YOU MEASURE IT.** S3 predicted +2 classes and +0
routes; S4 predicted +1 class and +1 route. Both came out exactly. ⚠ S5 predicted
"every example byte-identical" and **was wrong, twice** — which is exactly why the
prediction is worth writing down.
⚠ **AN `inf` IS USUALLY THE WRONG BOUND, NOT A BOUND NEEDING SOFTENING.** Ask what
the finite one MEANS physically before reaching for a clip. Twice now: S4's seed
crystal, S5's state extent.
⚠ **A FAILURE CAN HAVE A CHARGE THRESHOLD AS WELL AS A TEMPERATURE ONE**, and the
small charge is the one an example gets written with.
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS — AND THEN AUDIT ITS OUTPUT AND ITS
COVERAGE.** S2's harness invented a finding; S1's coverage audit credited a route
that cannot run; S3's report could not be diffed; S4's rate-ceiling audit made a
claim about a table it does not read; **S5's own first audit asserted "every
clamped must read 0" and a rig refuted it.**
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
⚠ **BDF IGNORES `jac_sparsity` THE MOMENT `jac` IS CALLABLE.** `BoundedJacobian`
CONSUMES the pattern; handing scipy both would silently drop the column groups
`useful_sparsity` computes.
⚠ Windows console is cp1252: a warning glyph inside a `print()` kills a script.
Docstrings fine, printed text ASCII. (TWENTY sessions running.)
⚠⚠ **`sed -i` REWRITES EVERY LINE ENDING IN A CRLF FILE.** S3 lost a file to it on
its first edit — 826/826 on a one-line change. This repo is MIXED: markdown and
`.psv` are CRLF, `element_data.py`/`solid_state.py`/`volatility.py` are CRLF while
`vessel.py`/`surface.py`/`vessel_integrator.py`/`jacobian.py` are LF. Use a
binary-mode anchored patcher that reads the anchor and replacement from FILES and
never decodes. **Check `git diff --stat` after the first edit to any file.**
⚠ **HEREDOCS EAT ESCAPES:** `\\n` written into a `python - <<'PY'` heredoc arrives
as `\n` and becomes a real newline inside a Python string. S5 hit this again and
broke a file's syntax. Use the Write/Edit tools for anything containing a
backslash.
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
**`COVERAGE_REPORT.md` comes out byte-identical across `PYTHONHASHSEED` values**;
**`validation/jacobian_bound.py` panel 3 reads 0 clamped columns on every single
vessel**; **a lattice may REACT and may never DISSOLVE — the fusion law is still
407x wrong in both directions, and neither M6 nor S1 nor S3 nor S4 nor S5 softened
that by one digit.**

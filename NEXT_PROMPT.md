We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M12 and S1 are DONE.**

**START WITH THE TOLERANCE AUDIT: re-run every example at rtol 1e-8 / atol 1e-11
and diff.** It is cheap, it is the highest-value thing left, and **two
milestones running have now found a quoted number that was wrong at the default
tolerance.** M6 found a swept-kiln conversion 2.6x off; S1 found a sealed roast's
sulfur closure 1.3e-6 off — and in BOTH cases the tight run was several times
FASTER (3.67 s against 19.94 s). Nobody has swept the other examples. See THE
TWO FRAGILITIES.

After that, the honest coverage job M6 named and nobody has done:
**`thermal-decomposition`'s four rows are four mechanisms** and the class has not
been split. M1's standard says that makes it an outcome label. Two of the four
are already covered by M6's term, so the split is +2 classes for four rows
re-labelled, and it is the cheapest coverage left in the corpus.

Then **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
re-scope before scheduling)** and **M8+ (electrochemistry — ⚠ that one WILL break
the spectator zeros)**.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§S1 is the one to read**: its brief asked for one
  mechanism and the arithmetic said two, and the *phase label* turned out to
  carry a standard state.
HANDOFF.md — what exists, and the ethos to preserve. **Item 85 is S1.**
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **S1's re-label
  of `mercury-from-cinnabar`**, and `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-solid-state-reactions,
  chemsim-zero-jacobian-column, chemsim-catalysis-and-bounds and
  chemsim-template-library.

```bash
python examples/roasting_and_the_catalyst_gate.py   # S1, five panels, ~12 s
python examples/lime_cycle.py                # M6, eight panels, ~18 s
python examples/named_routes.py              # M5's 17 routes, ~25 s
python validation/rate_ceiling.py            # M12's standing audit, seconds
python validation/catalog_coverage.py         # 33/215, 27/173, ~3 min
python -m pytest -q tests/test_surface.py        # S1's 38 tests, ~12 s
python -m pytest -q tests/test_solid_state.py    # M6's 31 tests, ~24 s
python -m pytest -q                          # the whole suite, 797 tests, ~11:50
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE IS MINUTES OF SATURATED CPU ON THE USER'S OWN MACHINE.** Run it to
establish a baseline and to verify at the end, not after each change. Say what a
long run will cost before starting one.

⚠⚠ **AND THE FULL SUITE HAS NOT BEEN RE-RUN SINCE S1's LAST FIX.** It ran
**796 passed / 1 failed in 11:50**; the failure was real and is fixed, and the
fixed file passes in a targeted run -- but the green number is not measured.
Re-run it before quoting one. (What it caught:
`test_every_mineral_records_the_ions_it_dissolves_into` asserted that EVERY
mineral has ions, and a metal has none. See the note under WHAT S1 LEFT.)

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 34 templates, a reaction that happens INSIDE
a crystal, and — new — **a gas that ATTACKS a crystal, and a catalyst you have to
actually put in the flask.** `SAVE_VERSION` is **5** (unchanged: the save stores
the recipe, not the per-term booleans).
Coverage: **27/173 template-ready routes** (was 26), **33/215 classes** (was
32/214), **34 templates UNCHANGED** — five gained a declared catalyst.

---

# ⚠⚠ WHAT S1 TURNED OUT TO BE, BECAUSE THE LESSON IS THE SHAPE OF THE ANSWER

S1's brief said: add `PHASE_INDEX["solid"] = 2`, and treat a solid catalyst and a
roasting sulfide as ONE mechanism, because "both are `nu` on the solid block".
**Both halves are refuted, and the arithmetic that refuted them was done before
any code was written.**

**A CATALYST'S STOICHIOMETRY IS ZERO ON BOTH SIDES.** So its `delta` never leaves
the gas block; only its EXPONENT reaches the solid one. That is one extra `(r, n)`
matrix — `KineticArrays.order_solid` — and nothing else.

⚠⚠ **AND THE PHASE LABEL IS NOT A NAME, IT IS A CHOICE OF THERMODYNAMICS.**
`reaction_deltas` applies the pure-liquid standard-state shift to any phase that
is not `"gas"`. Measured on `N2 + 3 H2 -> 2 NH3`:

| | dH / kJ/mol | dG / kJ/mol | K(500 K) |
|---|---:|---:|---:|
| `phase="gas"` | -91.880 | -32.820 | 2.683e+03 |
| `phase="solid"` | -114.769 | -132.542 | 7.019e+13 |
| shift | **-22.889** | **-99.722** | **x 2.616e+10** |

**That is verbatim the failure the `PHASE_INDEX` comment was written to prevent**
— `phase="any"` was validated, documented, and silently meant liquid — arriving
at the line that comment is written on. A solid-catalysed gas reaction IS a
gas-phase reaction: every participant that has an activity is a gas, and a pure
solid's activity is 1.

And roasting cannot take the label either, for an independent reason:
`thermochemistry` REFUSES a lattice SMILES by name, so a roasting row cannot be
priced on the ideal-gas basis the kernel's reverse derivation lives on. It needs
`mineral_data` against a curated gas — so it is a curated table, like M6's.

⚠⚠ **THE ONE-SENTENCE LESSON: `PHASE_INDEX` HAS TWO ENTRIES AFTER TWO MILESTONES
THAT EACH EXPECTED TO ADD A THIRD, AND THE REASONS ARE DIFFERENT.** M6's was *the
kernel cannot express this rate law*. S1's is *the label would change the
thermodynamics*. Read `network/builder.PHASE_INDEX`'s comment: it now carries both.

**Five mechanics nobody wrote:** a sealed roast STALLS (1.53% in 20 ks — a litre
of air holds 2.296 mmol of O2 and 0.1 mol of ore needs 150), a blown one goes
(78.26%), **autothermal roasting** (insulated, 100% while heating itself 1100 →
1908.6 K, and the VENT is what stops the runaway), two ores sharing one blast
(0.039131 mol each, both closures exact to 1e-12), and a clock that ignores the
charge (first order in the solid, so `tau = 1/(k C_gas)`).

---

# ⚠⚠ AND THREE THINGS S1's FIRST GUESS GOT WRONG. READ THIS.

**1. THE REFERENCE-CHARGE INVARIANT IS NOT BIT-EXACT, AND A VENTED COMPARISON IS
NOT A COMPARISON.** `A_cat * SOLID_CATALYST_REFERENCE == A_folded` exactly, so the
catalysed and folded templates should agree. In a VENTED flask they differ by
**+0.086%** — and the first explanation offered (displaced volume) was tested by
enlarging the flask and **made it worse**, because the two runs vent differently.
SEALED, with the flask enlarged by the 0.0007096 L that 0.1 mol of iron occupies:
**-4.6e-11 mol**, solver tolerance. The residual IS displaced volume; the vent was
hiding it. **Lesson: an invariant measured across a boundary flux is not an
invariant.**

**2. "TEN TIMES THE CATALYST IS TEN TIMES THE RATE" READS 9.75, NOT 10.** Measured
as a yield after a 1 s run. That 2.5% is DEPLETION — a run long enough to
integrate is long enough to move down its own curve — and the claim is about an
INITIAL rate. Off the RHS via `energy_terms` it is 10.0 to 1e-9. **Lesson: a rate
claim measured as a yield is measuring two things.**

**3. ⚠⚠ CREDITING A CLASS PRODUCED A FALSE CREDIT, AND THE AUDIT COULD NOT SEE
IT.** Crediting `roasting` as M6 labelled it moved `mercury-from-cinnabar` into
the template-ready list — and that row reads `mercury-sulfide + oxygen -> mercury
+ sulfur-dioxide` while the term makes the OXIDE. HgO decomposes at roasting heat,
which is exactly why the row is written that way. **M6 had already recorded the
reading** ("one template will not cover that row honestly") and not acted on it.
Re-labelled `roasting-to-metal`. **Lesson: a coverage number moving is not
evidence that the engine moved — check WHICH routes the +N is.**

⚠ And the number that remains needs the same care: **the one route S1 adds to the
template-ready list is `pyrite-roasting`, which does not run** (pyrite has `Hfs`
in WEBBOOK and `S0s` in nothing, so `mineral_data` refuses it). That is not a
broken number, it is what template-readiness MEANS. **Honest summary: +1 class,
+1 template-ready route, ZERO new routes that run end to end.**

---

# ⚠ TWO FRAGILITIES, PLUS ONE LATENT UNITS ISSUE S1 ADDED AND REPORTED

**1. THE DEFAULT SOLVER TOLERANCE IS NOT CONVERGED FOR A FLASK ON A VENT, AND
THAT IS NOW TWO MILESTONES DEEP.** M6 measured 39.04% against 13.97% on a swept
kiln — 2.6x. S1 measured a sealed roast's sulfur closing to 1.3e-6 at the default
and 9.4e-11 at rtol 1e-8, with the tight run **5.4x faster** (3.67 s vs 19.94 s).
Cause: `k_vent` is 1e3 mol/(bar s), so the gas balance is far stiffer than the
chemistry feeding it. **Any slow source feeding this vent is exposed to it, and
nobody has swept the other examples.** That is the task at the top of this file.

**2. A SPECIES IN THE NETWORK BUT ABSENT FROM A SEALED FLASK HAS AN IDENTICALLY
ZERO JACOBIAN COLUMN** — the `num_jac` trap `LAYER_REABSORB` documents: the
perturbation factor inflates to inf and BDF gets a NaN Jacobian. PRE-EXISTING; M6
made it reachable. ⚠ **A declared catalyst does NOT trip it, and that is measured
rather than hoped:** its column is populated even at zero amount (the gas rates
depend on it with slope `k prod(C**order)`), and what IS zero is its ROW — which
is exactly what a catalyst should be. The fix for the general case is still a
`LAYER_REABSORB`-style honest diagonal on the gas block: hot loop, moves
invariants, wants a session of its own.

**3. ⚠ NEW AND REPORTED RATHER THAN FIXED: `detailed_balance`'s RATE CAP COMPARES
A CATALYSED PRE-EXPONENTIAL AGAINST A LIMIT THAT IS NOT IN ITS UNITS.** A declared
`solid_catalyst` puts an order-1 factor in MOL into the rate law, so `A` carries an
extra `mol^-1` and 1e11 L/(mol s) is not a bound on it.
`validation/rate_ceiling.apparent_A` multiplies by `SOLID_CATALYST_REFERENCE` to
undo exactly that, and the audit is restored to its baseline
(`ammonia_synthesis_rev` crosses at **1335.1 K**, unmoved — raw it reads 1178.1 K,
which is the units error). `detailed_balance` does not, so it would fire **10x too
eagerly**. Bounded in the class this project forgives: the cap scales BOTH
pre-exponentials, so K is invariant and the whole cost is a clock at most 10x
slow. **It does not fire on any of the five catalysed templates today** and
`tests/test_surface.py` pins that so it cannot start silently. The proper fix wants
the reference charge as an ARGUMENT, not a Layer-2 import cycle.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's own clamp
is `T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

# WHAT S1 LEFT ON THE TABLE, IN THE ORDER IT IS WORTH DOING

1. **The tolerance sweep** (above). Cheap, and two milestones running have found
   a wrong quoted number.
2. **Split `thermal-decomposition`** (above). +2 classes, four rows re-labelled,
   no engine work.
3. **`mercury-from-cinnabar`'s second step.** `cinnabar-roasting` gives
   montroydite; the metal needs **mercury as a species** and a decomposition row.
   ⚠ That would be a genuinely EMERGENT two-step, the way M6's carbonation was:
   roast to the oxide, and the oxide falls apart at the same heat. Mercury is a
   LIQUID at room temperature and a gas in a retort, so its ideal-gas record is a
   real vaporisation number — this is curation, not research.
4. **Pyrite.** One mineral entry away from `pyrite-roasting` running. Blocked on
   the same-database rule (`Hfs` in WEBBOOK, `S0s` in nothing), which is a rule
   worth keeping — so this needs a source, not a workaround.
5. **⚠ RE-RUN THE SUITE.** 796/1 at S1's close, fix applied, not re-measured.
   ⚠ What the failure was is worth carrying: `test_element_data` asserted
   `rec.ions` for every mineral row, and S1's METALS have none on purpose --
   iron does not dissolve to Fe atoms. The narrowing does NOT just permit an
   empty tuple, because an empty tuple is also what a typo looks like: it
   exempts only a ONE-ELEMENT row priced at `Hf = Gf = 0`, i.e. an element in
   its own reference state. Verified by simulating three mistakes (a salt with
   its ions emptied, a metal with a non-zero Hf, a two-element row with no
   ions) -- **all three CAUGHT**. A name list would have gone stale and caught
   none of them.
6. **The SITE BALANCE, which is M10 and is what S1 did NOT do.** A real surface
   saturates; this one is first order in the catalyst FOR EVER, so ten times the
   iron is ten times the rate at any loading. Right at low coverage, wrong at
   high, stated rather than approximated. M10 owns it and it blocks 8 routes.

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Fourteen times now — and S1 is the first time the arithmetic
overturned the brief's own design decision rather than confirming it.
⚠ **A PHASE LABEL CARRIES A STANDARD STATE.** Adding one is a thermodynamic
change, not a naming change.
⚠ **A CONSTANT SHARED BETWEEN ROWS IS A CLAIM THAT THEY ARE THE SAME EVENT** —
and S1's is partly refuted and says so: one clock makes cinnabar 31x slower at its
own retort's temperature, and Evans-Polanyi would get the ordering BACKWARDS
because sphalerite is the most exothermic row and needs the hottest furnace.
⚠ A CLASS IS A MECHANISM CLAIM. Read the rows, not the name — and check which
ROUTES a credit moves, because S1's first attempt credited a route on a mechanism
that does not make its product.
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal the
flask first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS, and neither is a
converged-looking number at the default tolerance. Re-measure before quoting.
⚠ **A COMMITTED GENERATED REPORT IS NOT A BASELINE.** Regenerate at HEAD.
⚠ Windows console is cp1252: a warning glyph inside a `print()` kills a script.
Docstrings fine, printed text ASCII. (SIXTEEN sessions running.)
⚠⚠ **HEREDOCS ATE AN ESCAPE AGAIN, AND IT WAS WORSE THAN LAST TIME:** `\\n`
written into a `python - <<'PY'` heredoc arrived as `\n` and became a real newline
inside a Python string, so an anchored patch silently matched nothing. Use the
Write tool for anything containing a backslash, and run it as a file.
⚠ **AND WRITING A FILE THROUGH PYTHON'S TEXT MODE ON WINDOWS EMITS CRLF.** This
repo is MIXED — markdown and `.psv` are CRLF, most Python is LF, and
`tools/build_mineral_data.py` is CRLF while `src/chemsim/vessel/vessel.py` is LF.
S1 used a binary-mode anchored patch helper that detects and preserves each file's
own endings; check `git diff --stat` before committing and normalise if a file you
barely touched shows as rewritten.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u` — and
do not pipe a long run through `tail`, which holds everything until EOF.

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays; RDKit stays in matter.
NO silent approximations. REFUSE loudly rather than return a confident wrong
number — and a LATENT fragility is a third case: report it, do not refuse it.
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?" (S1's two declared exponent matrices collapse
to ONE in `SurfaceArrays.__post_init__`, and the halves survive only as the
declaration a builder can refuse.)
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; `solid_state=False`
exactly no crystal reacting; **`surface=False` exactly no gas attacking one, and
an all-zero `order_solid` exactly the old kinetics kernel**; the Born term exactly
zero in PURE water; the five pH values; SAVE_VERSION stores the CONDITION, never
the instant; every gaseous element reference state Hf = Gf = 0 EXACTLY; **every
METAL Hf = Gf = 0 EXACTLY on the solid basis, and a non-zero result REFUSED as an
allotrope mismatch**; a reference state its own database does not price at Hf = 0
is REFUSED; no mineral pricing differently under the two providers; `ion_data` and
`electrolyte` never subtracted from each other; a declared rate order may never be
reversible; **a surface row whose `ln K` is under +20 is REFUSED, because mass
action on a solid AMOUNT reaches the wrong equilibrium**; the reflux ratio is the
ratio of two drain conductances out of one condenser, declared rather than
inferred; the fragmentation SEARCH runs only after the greedy pass has been
REFUSED; an ion is never counted in the held-ideal flag; a rate CAP scales BOTH
pre-exponentials by one factor; a template that moves a hydrogen ATOM must collapse
explicit Hs; **a declared catalyst is a CONSTANT OF THE MOTION — bit for bit, at
every charge — which is what makes it unable to seed itself**;
**a lattice may REACT and may never DISSOLVE — the fusion law is still 407x wrong
in both directions, and neither M6 nor S1 softened that by one digit.**

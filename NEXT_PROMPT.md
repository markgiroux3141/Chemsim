We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M4 are DONE.**

⚠⚠ **BUT DO NOT START WITH M5.** A measured WRONG ANSWER landed on 2026-08-24
and this project's own ordering puts those first — M0 was exactly that case.
**Start with M12, the adiabatic energy leak** (HANDOFF 81, and the section below).
It has a 0.2-second reproduction, the diagnosis is already narrowed to one
window, and it is the kind of defect the whole project exists to refuse: a flask
that conserves every atom while destroying half a kilojoule.

**M5 — templates to a target of twenty playable routes** is the next CONTENT
milestone and is what to do once M12 is closed.

Start by reading, in order:

MILESTONES.md — the plan. M0–M4 done; **M5 has the greedy set-cover order and
  the warning that several of its entries are not template work at all.**
HANDOFF.md — what exists, and the ethos to preserve. **Items 80 and 81 are the
  last session** — 80 is M4 (both halves, plus two measurements that corrected
  each other); **81 is the energy leak, and it is the one to read.**
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy M1 settled, and
  `data/catalog/COVERAGE_REPORT.md` for the greedy order M5 works down.
the memory files (auto-loaded), especially chemsim-template-library,
  chemsim-coverage-catalog, chemsim-declared-rate-orders and
  chemsim-unifac-gap.

```bash
python validation/unifac_gap.py              # M4's measurement AND verification, ~1 min
python validation/catalog_coverage.py        # where coverage stands
python -m pytest -q tests/test_activity.py tests/test_lle.py
python -m pytest -q                          # 679 tests, ~15 min
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE IS 15 MINUTES OF SATURATED CPU ON THE USER'S OWN MACHINE.** Run it
to establish a baseline and to verify at the end, not after each change. Say what
a long run will cost before starting one, and **ask first.**

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral/ion floor, a still that is a saveable protocol, a
plate column that reaches its purity target, an ionic lattice that can leave
solution, and **a solvent mixture that says when it was never modelled.**
`SAVE_VERSION` is **5**. Coverage: **41/377 steps, 7/173 template-ready routes.**
UNIFAC organic coverage **66.1%** (764/1155). **679 tests green, lint clean, as
of 2026-08-24.**

---

# ⚠⚠ FOUR RULES FROM LAST SESSION, EACH BOUGHT WITH REAL TIME

**1. SILENCE IS NOT A NEUTRAL DEFAULT WHEN THE MISSING MODEL HAS A DIRECTION.**
`numerics/lle.py` says as a VIRTUE that *an ideal liquid never splits* — with no
group parameters the tangent-plane test returns "stable" for free. Put that beside
*a neutral species with no decomposition is held at γ = 1* and the omission stops
being noise around the right answer: **everything held ideal argues for one
phase, which is exactly the answer `lle_report()` used to return as the empty
string.** A foregone conclusion wearing the clothes of a finding.

⚠ **Checkable form: before treating an unmodelled term as "it adds uncertainty",
ask which way it points. If the model's default output and the omission's bias
are the same answer, silence is an argument for that answer.** Look for the next
place where a report is empty because a term was never computed.

**2. A CEILING MEASURED OFF ANOTHER IMPLEMENTATION IS A MEASUREMENT OF THAT
IMPLEMENTATION, NOT A TARGET.** M4 was planned against 66.4%, being what
`thermo`'s backtracking matcher reaches on our identical patterns. We reach 66.1%
and **refuse the last three on purpose** — they are three thermo gets by counting
hydrogens off the MOLECULE instead of off the GROUP, so a group's R and Q land
outside the structure they were fitted to (`CF2` onto a CHF₂ carbon, the
whole-molecule `FURFURAL` group onto a substituted furan, the ether group `CH3O`
onto a methoxy RADICAL). Reaching the "ceiling" meant adopting three wrong
answers.

**3. HOLD THE CODE FIXED AND CHANGE ONLY THE CHEMISTRY.** Giving acetaldehyde a
real γ made the benzoic-acid prep **23 s → 41 s** and produced a run of
`RuntimeWarning: overflow encountered in exp` in the activity kernel. Clipping
that exponent changed **nothing** — same wall time, same answer to six digits,
same residual. So 100% of the slowdown is the CHEMISTRY getting stiffer and 0% is
the NaN, and the NaN is inert: it lands only in BDF steps that were going to be
rejected. ⚠ **"My change made X appear" and "X is what made it slower" look like
one claim and are two.**

**4. ⚠⚠ COMPARE CONVERGED VALUES, NEVER ONE RUNG AGAINST ANOTHER RUNG — AND THIS
ONE BIT IN BOTH DIRECTIONS IN THE SAME HOUR.** A tolerance ladder was run on that
prep, `run(7200)`, both before and after M4:

| rtol / atol | BEFORE worst residual | AFTER worst residual |
|---|---|---|
| 1e-6 / 1e-9  | `HSO4-` 5.49e-05 | `[OH3+]` **1.88e-03** |
| 1e-7 / 1e-10 | **FAILED: infs or NaNs** | `[OH3+]` **6.41e-02** |
| 1e-8 / 1e-11 | `HSO4-` 1.31e-08 | `HSO4-` 1.48e-07 |
| 1e-9 / 1e-12 | `[OH3+]` 4.24e-08 | `[OH3+]` 1.39e-07 |

* The residual **converges**, so it is a tolerance artefact and not a defect —
  but it is **NOT MONOTONE**, and the 1e-7 rung is 34× worse than 1e-6. A
  projection residual on a species held near zero is luck-of-the-step, so
  **"the round-off grew 34×", read off the two default-tolerance numbers, was
  signal invented out of scatter.**
* ⚠ **And then the opposite mistake on the answer itself.** Reading across rungs
  suggested the acetic acid was moving inside the solver's scatter. It is not:
  each state agrees with ITSELF between 1e-8 and 1e-9 to ~5e-09, and the two
  CONVERGED answers are 0.006671076715 and 0.006669628012 — a difference of
  **0.0217%, which is 282× the convergence noise.** Acetaldehyde's γ really does
  move this prep; it just cannot be seen without converging first.
* ⚠ Note which way the failure points: **the state that fails at rtol 1e-7 is the
  OLD one.** This pot's tight-tolerance delicacy pre-dates M4.

---

# ⚠⚠ THE THING TO READ FIRST: THERE IS A MEASURED WRONG ANSWER, AND IT IS M12

**An insulated flask destroys 495 J after a precipitation event.** HANDOFF 81,
MILESTONES M12. This was carried for two sessions as a hypothesis — *"probably a
generic integration weakness, probably pre-dates the precipitation term"* —
because the control that would have tested it was recorded as too slow to run.
**The control takes 0.2 seconds.** It refutes the hypothesis outright.

    t=600s   dT = +0.15774 K    <- the prediction from the two tables
    t=1200s  dT = +0.15751 K    <- still right (this is why the 1200 s test passes)
    t=3600s  dT = +0.03782 K    <- and the chemistry stopped at t=1200

Between 1200 s and 3600 s the largest mole change in ANY block is **1.332e-07
mol** — 0.0087 J at 65 kJ/mol — against **495.6 J** of heat. UA = 0, the gas
block holds no water, the solid is flat. **No sink exists.**

⚠ **AND `conservation_report` CANNOT SEE IT: it audits MATTER, not energy.** A
flask can conserve every element to 1e-12 while destroying half a kilojoule. An
energy audit is part of M12, not a nicety — without one the next leak is invisible
too.

⚠ **The transferable lesson is about the RECORD, not the physics.** The
hypothesis was written down honestly, marked as unmeasured, and cited three
times — in a test docstring, in HANDOFF and in NEXT_SESSION — until it started
reading like a finding. *A hypothesis that survives long enough begins to be
quoted as a measurement.* The thing that saved the number was the standing rule
that the test asserts CONVERGENCE and not a default-tolerance value.

---

# ⚠ ONE LATENT FRAGILITY, REPORTED RATHER THAN FIXED

**`psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows for the
PSRK quadratic `H2O <-> N2` pair at every T below 4.28 K** — and the RHS's own
temperature clamp is `T_MIN = 1.0`, which sits inside that band. So whenever
`num_jac` probes the temperature column hard and the group basis holds both water
and nitrogen, the psi matrix goes to `inf` and then `NaN` through three matmuls.

* **PRE-EXISTING**: the offending pair is `H2O <-> N2` and the a_mn extremes are
  byte-identical before and after M4, which only made a standing test reach it.
* **MEASURED INERT** (rule 3): clipping the exponent changes no number.
* **The precedent for the fix is in the same file** — `gamma_ref_range` clamps T
  for the reference-state term precisely because PSRK's quadratic gas parameters
  go wrong quickly outside their window; the a_mn matrix has the same problem and
  no such clamp. ⚠ NOT bundled into M4: the activity kernel is the hottest code
  in the project and a change there is a deliberate decision with the full suite
  behind it, not a side effect of a fragmentation change.

It is open by choice rather than by running out of time. The suite is green with
it in place and its warnings are confined to `tests/test_prep_side_products.py`.

⚠ **AND A BLOCK-ORDER TRAP THAT COST ME A WRONG READING:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**
An audit that assumes (liquid, gas, solid, liquid2) silently reads the gas block
as the solid. Take a bound across ALL blocks first; that bound is
label-independent and it is what survived the mistake.

---

# M5 — TEMPLATES TO A TARGET OF TWENTY ROUTES

MILESTONES §M5 has the detail. In brief: not "full coverage" — pick **twenty
playable routes** and build only what they need, in the greedy set-cover order M1
established: `catalytic-air-oxidation`, `acid-displacement`, `electrolysis`,
`redox`, `disproportionation`, `pyrolysis`, `glycoside-hydrolysis`,
`catalytic-gas-synthesis`, `ammoxidation`, `roasting`, …

⚠ **CHECK THE MECHANISM BEFORE SCHEDULING THE TEMPLATE.** Several entries on that
list are not template work at all: `electrolysis` needs M8 (electrochemistry),
`roasting` needs M6 (solid-phase reactions). A class is a MECHANISM claim, which
is the standard M1 exists to enforce — `deprotonation` was refused credit because
five of its six rows were carbanion generation wearing the wrong label.

⚠ **BOUND EACH TEMPLATE'S A AND Ea AGAINST A STATED OBSERVABLE, or declare them
hand-authored and say what bounds them.** The sulfur burner is the worked
example: A pinned to the collision limit, and the soft threshold that fell out
asserted rather than tuned away.

⚠ **AND EXPECT NEW SPECIES TO REACH THE ACTIVITY MODEL.** M4 is why this is now
worth saying: a template that introduces an anhydride, an acid chloride, a urea
or a nitrate ester introduces a species with **no UNIFAC decomposition**, which
`Vessel.lle_report()` will now flag rather than silently hold ideal. That is the
system working — but if a new route's flask reports a large held-ideal fraction,
that route's phase behaviour is soft and saying so is part of shipping it.

**Done when:** 20+ routes are template-ready end to end and each has an example
that runs.

---

# AFTER M5

M6 (solid-phase reactions — ⚠ M3 added 15 element reference states, so the floor
is wider than when M6 was written), M7 (dissociation as an equilibrium, stiffness
7.05e21), M8+ (electrochemistry — ⚠ **that one WILL break the spectator zeros**).

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Ten times now, most recently by finding that the honest threshold
for M4's flag is a REPORTING decision with no dead zone under it — the error is
linear in the ideal mole fraction all the way down, so there is no fraction at
which the model becomes correct, only one at which it becomes visible.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS. The tests pin those
rows far looser than the digits quoted. Re-measure before quoting.
⚠ A RESIDUAL WHOSE VALUE MOVES WHEN YOU NUDGE AN INERT SPECIES IS NOT A NUMBER TO
ASSERT. Assert convergence, or exactness with nothing driven to zero. **And a
residual that is not MONOTONE in tolerance is not a number to compare, either.**
⚠ Windows console is cp1252: a warning glyph inside a print() kills a validation
script. Docstrings fine, printed text ASCII. (TWELVE sessions running; use `!!`
in printed panels.)
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it, so a probe that is
still working looks identical to one that has hung. Use `python -u`.

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays; RDKit stays in matter.
NO silent approximations. REFUSE loudly rather than return a confident wrong
number — and a LATENT fragility is a third case: report it, do not refuse it.
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?"
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; the Born term exactly
zero in PURE water; the five pH values; SAVE_VERSION stores the CONDITION, never
the instant; every gaseous element reference state Hf = Gf = 0 EXACTLY; a
reference state that its own database does not price at Hf = 0 is REFUSED; no
mineral pricing differently under the two providers; `ion_data` and `electrolyte`
never subtracted from each other; a declared rate order may never be reversible;
the reflux ratio is the ratio of two drain conductances out of one condenser,
declared rather than inferred; **the fragmentation SEARCH runs only after the
greedy pass has been REFUSED** (that ordering is what keeps Joback unmoved at
1057 species with zero changed); and **an ion is never counted in the held-ideal
flag** (γ = 1 there is a policy with the Born term behind it, not a gap).

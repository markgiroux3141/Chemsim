We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M4 and M12 are DONE.**

**START WITH M5 — templates to a target of twenty playable routes.** It is the
next CONTENT milestone and there is no measured wrong answer ahead of it any
more: M12, the adiabatic energy leak, was closed on 2026-08-24 (HANDOFF 82).

The project is under **git** as of 2026-08-24 — one initial commit plus M12.
There is no remote. ⚠ The committer identity is the machine's global
`innovationlabOBS <innovationlab@obsglobal.com>`; set a repo-local
`user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. M0–M4 and M12 done; **M5 has the greedy set-cover
  order and the warning that several of its entries are not template work at
  all.** ⚠ **M7 has been RE-SCOPED by M12 and is no longer "the largest single
  engine job" — read its section before quoting its stiffness number.**
HANDOFF.md — what exists, and the ethos to preserve. **Item 82 is M12 and is the
  one to read**; 80 is M4, 81 is the measurement that turned M12 from a
  hypothesis into a defect.
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy M1 settled, and
  `data/catalog/COVERAGE_REPORT.md` for the greedy order M5 works down.
the memory files (auto-loaded), especially chemsim-template-library,
  chemsim-coverage-catalog, chemsim-declared-rate-orders and
  chemsim-rate-ceiling.

```bash
python validation/rate_ceiling.py            # M12's standing audit, seconds
python validation/adiabatic_tail.py          # M12's reproduction, ~4 s
python validation/unifac_gap.py              # M4's measurement, ~1 min
python validation/catalog_coverage.py        # where coverage stands
python -m pytest -q tests/test_energy_balance.py tests/test_precipitation.py
python -m pytest -q                          # 689 tests
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE IS MINUTES OF SATURATED CPU ON THE USER'S OWN MACHINE.** Run it to
establish a baseline and to verify at the end, not after each change. Say what a
long run will cost before starting one, and **ask first.** ⚠ It should now be
materially faster than the 15 minutes previously quoted — M12 made the benzoic
acid prep **6.6× faster** — but the quoted figure has not been re-measured.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral/ion floor, a still that is a saveable protocol, a
plate column that reaches its purity target, an ionic lattice that can leave
solution, a solvent mixture that says when it was never modelled, and **an
energy balance it can report the way it reports a mass one.** `SAVE_VERSION` is
**5**. Coverage: **41/377 steps, 7/173 template-ready routes.** UNIFAC organic
coverage **66.1%** (764/1155). **689 tests green, lint clean, 2026-08-24.**

---

# ⚠⚠ WHAT M12 TURNED OUT TO BE, BECAUSE THE LESSON IS NOT ABOUT ENERGY

An insulated flask destroyed 495 J while conserving every atom to 1e-12. Four
plausible causes were measured and refuted before the real one was found, and
**each of the four is a fix someone will propose again:**

| proposed cause | how it died |
|---|---|
| the precipitation term | term ON vs OFF agree to 5 decimals with nothing supersaturated |
| the energy equation's algebra | `q_rxn / (−dH·dn) = 1.000000` **pointwise** — the heat already WAS the price of the extent |
| the tolerance | tightening the temperature's own budget made it **worse**: 31,324 steps and +2.0e-2 K |
| the integrator | Radau −5.5e-5 K and LSODA +8.8e-5 K both beat BDF's −1.2e-1 — but Radau can't finish the prep in 8 min and LSODA fails it at t=0.013 s |

**The cause was in Layer 2.** `dissociation_templates` sets `Ea = 60 kJ/mol` for
water autoionization so the elementary-barrier clamp misses water's 55.8 kJ/mol
dissociation enthalpy. Detailed balance then hands the REVERSE a 4.2 kJ/mol
barrier and **9.4e18 L/(mol s) — 9.4e7× the collision limit**, for a
recombination measured at 1.4e11.

⚠⚠ **THE ONE-SENTENCE LESSON, AND IT GENERALISES FAR BEYOND THIS FLASK: THIS
PROJECT HAS ALWAYS REFUSED AN IMPOSSIBLE HAND-AUTHORED PRE-EXPONENTIAL AND NEVER
CHECKED THE ONES IT DERIVES.** `reactions/library.py` argues at length about not
buying a prettier threshold with A = 1e14. Nothing applied that standard to
`detailed_balance`, which derives a rate constant for every reversible template
in the project. **Look for the next quantity that is derived rather than
declared and therefore never bounded.**

⚠ **The second lesson is about the instrument.** The leak was localised by a
PER-STEP energy budget, not by a better hypothesis: three consecutive BDF steps
of exactly 167.63 s, at −253.4, −145.2 and −69.0 J, with `dn(H3O+)` ~1e-10.
*Energy leaving with no matter moving, at a fixed step size.* That shape named
the mode. `Vessel.energy_report()` exists now and prints the **GROSS** reaction
heat beside the net — because a net of 1e-3 W looks identical whether a flask is
at rest or whether two 5.2e9 W terms are cancelling to twelve digits.

⚠ **A trap the instrument itself set:** `energy_terms` must be given the state
the RUN started from (`boundary=`). The RHS freezes each layer's permittivity at
its integration boundary, and re-freezing at a later state moves the
Bronsted-Bjerrum factor in the fifth digit — worth 1e5 W out of that
cancellation. The same state read **−4.69e6 W** frozen at itself and **−5e-3 W**
frozen at the run's own boundary.

---

# ⚠ THREE THINGS M12 LEFT OPEN, EACH REPORTED RATHER THAN FIXED

**1. THE CEILING IS ENFORCED AT 298 K ONLY.** A barrier climbs with temperature
faster than a collision frequency does.
`carboxylic_acid_dissociation_rev` **crosses the ceiling at 416.6 K** and is
1.16e3× over it at 700 K. Nothing runs a carboxylic acid that hot today, so it
is latent — but a reflux reaches 416 K. `validation/rate_ceiling.py` prints
every crossing; read it before scheduling a hot route with an acid in it.

**2. `born_A` IS ZERO FOR `[Ag+]`**, while Cl⁻, Na⁺, NO₃⁻, H₃O⁺ and OH⁻ all have
one. `born_A` is also the ion mask, so **silver is carried as a NEUTRAL by the
ion-transfer term.** Exactly zero cost in a single aqueous phase, where the Born
term vanishes anyway; it is an EXTRACTION of a silver salt that would be quietly
wrong. Found in passing by the M12 audit and not chased.

**3. THE DEFAULT RUNG'S PROJECTION RESIDUAL MOVED SPECIES AND GOT WORSE IN KIND.**
The prep now creates **2.53e-05 mol of benzoyl** at rtol 1e-6 where it used to
create 3.5e-12 — the standing *"a stiff reactant driven to exactly zero
overshoots at the 1e-4 level"* item, made visible because fewer, larger steps
cover the same span. ⚠ It **converges** (2.53e-05 → −1.70e-13 → −4.41e-15) and
`conservation_report` says so unprompted. Note what it replaced: the old default
created **1.88e-03 mol of `[OH3+]`**, 76× larger. It belongs to M7.

⚠ **AND THE OLD DEFAULT ANSWER WAS THE WRONG ONE, WHICH IS THE POINT.** Rule 4
applied to the prep: the two CONVERGED benzoate values agree to nine figures
(0.199993746), so M12 changed no chemistry. What changed is that the default rung
now lands ON the converged answer instead of 3.1e-5 away from it, and converging
costs **10.7 s instead of 156.7 s**. The old ladder had not converged in
temperature at all (352.9823 / 353.0001 / 353.0024); it is now 353.0012 at every
rung.

---

# ⚠ ONE LATENT FRAGILITY, STILL OPEN AND UNCHANGED BY M12

**`psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows for the
PSRK quadratic `H2O <-> N2` pair at every T below 4.28 K** — and the RHS's own
temperature clamp is `T_MIN = 1.0`, which sits inside that band. PRE-EXISTING,
**measured inert** (clipping the exponent changes no number, no timing, no
residual), so it is reported rather than refused. The precedent for the fix is
`gamma_ref_range` in the same file; the activity kernel is the hottest code in
the project and a change there wants the full suite behind it.

⚠ **AND A BLOCK-ORDER TRAP:** the state vector is
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

⚠⚠ **BOUND EACH TEMPLATE'S A AND Ea AGAINST A STATED OBSERVABLE — AND NOW CHECK
THE REVERSE THE TEMPLATE IMPLIES, NOT ONLY THE FORWARD YOU TYPED.** That is M12's
bequest to this milestone and it costs one command:
`python validation/rate_ceiling.py` after adding a reversible template. The
sulfur burner is still the worked example for the forward half: A pinned to the
collision limit, and the soft threshold that fell out asserted rather than tuned
away.

⚠ **AND EXPECT NEW SPECIES TO REACH THE ACTIVITY MODEL.** A template that
introduces an anhydride, an acid chloride, a urea or a nitrate ester introduces a
species with **no UNIFAC decomposition**, which `Vessel.lle_report()` will now
flag rather than silently hold ideal. That is the system working — but if a new
route's flask reports a large held-ideal fraction, that route's phase behaviour
is soft and saying so is part of shipping it.

**Done when:** 20+ routes are template-ready end to end and each has an example
that runs.

---

# AFTER M5

M6 (solid-phase reactions — ⚠ M3 added 15 element reference states, so the floor
is wider than when M6 was written), **M7 (dissociation as an equilibrium — ⚠ M12
took most of its case away; re-scope before scheduling)**, M8+ (electrochemistry
— ⚠ **that one WILL break the spectator zeros**).

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Eleven times now, most recently by finding that the energy
equation's algebra was already exact pointwise — which killed a rewrite of
`q_rxn` that had been designed and was about to be built.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS. The tests pin those
rows far looser than the digits quoted. Re-measure before quoting.
⚠ A RESIDUAL WHOSE VALUE MOVES WHEN YOU NUDGE AN INERT SPECIES IS NOT A NUMBER TO
ASSERT. Assert convergence, or exactness with nothing driven to zero. **And a
residual that is not MONOTONE in tolerance is not a number to compare, either.**
⚠ Windows console is cp1252: a warning glyph inside a print() kills a validation
script. Docstrings fine, printed text ASCII. (THIRTEEN sessions running, and it
bit twice more this session inside `python - <<'PY'` heredocs — a `\n` written
through two layers of quoting became a real newline and broke the file. Prefer
the Write/Edit tools for anything containing an escape.)
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
declared rather than inferred; the fragmentation SEARCH runs only after the
greedy pass has been REFUSED; an ion is never counted in the held-ideal flag;
**and a rate CAP scales BOTH pre-exponentials by one factor, because
`K = k_f/k_r` is the invariant it may not move** (measured: Kw stays 1.0022e-14
across eight orders of A).

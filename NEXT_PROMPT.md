We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6 and M12 are DONE.**

**START WITH THE THIRD `PHASE_INDEX` ENTRY: a gas-CONSUMING surface reaction.**
It is not a numbered milestone; it is what M6 measured its way to, and it is the
highest-value engine work available because it fixes a *gameplay-visible wrong
answer* rather than adding coverage. **A flask with no iron in it makes ammonia.**
Five of M5's twenty templates (`alkene_hydrogenation`, `nitro_hydrogenation`,
`ammonia_synthesis`, both methanol rows) fold their catalyst into an apparent
barrier, so "you need a catalyst" cannot be a gate. `roasting`'s five rows want
the same feature. M6 established exactly what it is and exactly what it is NOT —
read the section below before touching anything.

There is **one measured wrong answer** ahead of it, and it is small and
pre-existing: see THE TWO FRAGILITIES.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. M0–M6 and M12 done. ⚠ **§M6 is the one to read**: it
  records that its own brief posed a true dichotomy, that the answer was measured
  rather than argued, and — in its SECOND PUSH section — that the pre-exponential
  had to be declared at the opposite end of the reaction from everywhere else in
  this project.
HANDOFF.md — what exists, and the ethos to preserve. **Item 84 is M6.**
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row. ⚠⚠ **AND M6 CORRECTED ONE OF ITS
  OWN ROWS SIX HOURS AFTER WRITING IT** — the swept-kiln conversions were measured
  at the default solver tolerance and were 2.6x wrong. The row now says so.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **M6's five
  re-labelled rows**, and `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-solid-state-reactions,
  chemsim-zero-jacobian-column, chemsim-catalysis-and-bounds and
  chemsim-template-library.

```bash
python examples/lime_cycle.py                # M6, eight panels, ~17 s
python examples/named_routes.py              # M5's 17 routes, ~24 s
python validation/rate_ceiling.py            # M12's standing audit, seconds
python validation/catalog_coverage.py         # 26/173, 32/214, ~3 min
python -m pytest -q tests/test_solid_state.py    # M6's 31 tests, ~23 s
python -m pytest -q                          # the whole suite, 759 tests, ~11:21
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE IS MINUTES OF SATURATED CPU ON THE USER'S OWN MACHINE.** Run it to
establish a baseline and to verify at the end, not after each change. Say what a
long run will cost before starting one.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, **34 templates, and — new — a reaction that
happens INSIDE A CRYSTAL.** `SAVE_VERSION` is **5**.
Coverage: **26/173 template-ready routes** (was 25), **32/214 classes** (was 29),
**34 templates UNCHANGED** — M6 covered three classes with a TERM.
**759 tests green in 11:21, lint clean, 2026-08-25.**

---

# ⚠⚠ WHAT M6 TURNED OUT TO BE, BECAUSE THE LESSON IS THE SHAPE OF THE ANSWER

M6's brief asked one question: **is a solid-phase reaction a third `PHASE_INDEX`
entry, or a second term next to precipitation?** That was a real dichotomy and the
answer was decided by building the wrong one first.

**A pure solid has UNIT ACTIVITY.** So a pair of crystals fixes the gas pressure
above them at `K(T)` no matter how much of each is present. Mass action on the
solid amounts cannot say that — it says `p/K = n_A/n_B` — and **that form was
built and measured settling at exactly that: 3.0863 against 3.0863 at 1100 K,
1.2139 against 1.2139 at 1200 K. Five figures on both.**

⚠ **And dropping the reverse is not a way out.** Sealed 1 L, 0.1 mol of calcite:
equilibrium conversion is 0.12 / 1.23 / 7.95 / 37.3% at 900 / 1000 / 1100 / 1200 K,
where forward-only reads 100% at all four. **The kiln's whole mechanic is the part
forward-only deletes.**

⚠⚠ **THE ONE-SENTENCE LESSON: THE ARGUMENT WAS ALREADY WRITTEN DOWN BEFORE THE
CODE, AND WRITING THE CODE ANYWAY IS WHAT TURNED IT FROM AN ARGUMENT INTO A
MEASUREMENT.** The prediction and the observation agreed to five figures. That is
worth more than either alone, and it is why the wrong version's failure is
preserved in `SolidStateArrays`, in `builder.PHASE_INDEX`'s comment, and in a test.

**Four mechanics nobody wrote:** a kiln temperature (the threshold is where `K(T)`
crosses ambient, 1119 K, out of the CRC formation pair), a sealed tube that stalls,
**slaking** (the dehydration row run backwards), and **carbonation** (not any
single row's reverse — the dehydration row forwards and the decarbonation row
backwards, sharing the quicklime in the solid block). `solid-carbonation` is the
first class in the corpus credited to a mechanism that EMERGED.

---

# ⚠⚠ AND M6 GOT ONE THING WRONG AND FIXED IT IN THE SAME SESSION. READ THIS.

**The pre-exponential was declared at the wrong end of the reaction, and a second
row is what proved it.** M6 shipped `DECOMPOSITION_A = 1e5 1/s` as a FORWARD
constant, calibrated on the lime kiln. Adding chain 2's seed broke it completely:

| row | dH / kJ | with A declared forward |
|---|---:|---|
| `calcite -> quicklime + CO2` | 179.2 | 630 s at 1200 K — a real kiln |
| **`2 FeSO4 -> Fe2O3 + SO2 + SO3`** | **340.0** | **1.7e-13 1/s; 0.00% in 20 ks at EVERY temperature its thermodynamics allow** |

**Thirteen decades of clock error on a row whose thermodynamics were exactly
right.** The missing physics is the **ENTROPY OF MAKING GAS**. With the transition
state taken to resemble the products — the same late-TS assumption that makes the
reverse barrierless and fixes `Ea = dH` — the forward pre-exponential is
`A0 exp(dS/R)`, and what is left over is

    k_rev = A_fwd exp(-(Ea - dH)/RT) exp(-dS/R) = A0     exactly, at every T

**so `A0` is the REVERSE constant** — the pre-exponential of ONE elementary event,
a gas molecule arriving at a crystal surface with no barrier to climb. *That* event
is the same for calcite, green vitriol and baking soda, which is why one number can
cover rows that make different amounts of gas.

`RECOMBINATION_A = 4.259e-4 1/(bar s)`, unchanged in value from the original
calibration, so calcination's forward constant comes back as **100000.34 against
the 1e5 it was declared at — 3 ppm, and every lime number is provably unmoved.**
Then, with nothing else calibrated:

| row | tau | at | against |
|---|---:|---:|---|
| calcination-decarbonation | 631 s | 1200 K | a lime kiln, tens of minutes |
| calcination-dehydration | 146 s | 900 K | — |
| sulfate-thermal-decomposition | 25 s | 1000 K | a red-hot retort |
| bicarbonate-thermal-decomposition | 44 s | 450 K | the catalog's own `calciner, 450 K` |

⚠⚠ **THE LESSON TO CARRY: A CONSTANT SHARED BETWEEN ROWS IS A CLAIM THAT THEY ARE
THE SAME EVENT. IF THEY ARE NOT, THE CONSTANT IS HIDING THE DIFFERENCE.** Here the
difference was an entropy, it was already in the data, and finding it needed a
second row rather than more thought about the first.

---

# ⚠ TWO FRAGILITIES, ONE NEW-BUT-PRE-EXISTING AND ONE UNCHANGED

**1. A SPECIES IN THE NETWORK BUT ABSENT FROM A SEALED FLASK HAS AN IDENTICALLY
ZERO JACOBIAN COLUMN.** Verbatim the `num_jac` trap `LAYER_REABSORB` documents:
the perturbation factor inflates without bound, overflows to inf, and BDF gets a
NaN Jacobian. Measured, sealed at 1100 K, with and without N2/O2 in the species
list:

| charge / mol | lean network | N2/O2 present but absent |
|---:|---:|---|
| 0.05 | `p/K - 1` = -1.7e-07 | **RAISED**: CO2 reached -2.572 mol |
| 0.1 | +3.5e-09 | -2.6e-11 |
| 0.4 | -5.4e-13 | +1.6e-07 |
| 1.0 | +2.6e-08 | +1.9e-11 |

The hair trigger on the charge is a NaN Jacobian, not an instability. **It refuses
loudly rather than lying** (`check_raw_solution`: "a failed integration wearing a
success flag"), so it is a latent fragility. PRE-EXISTING; M6 made it reachable.
⚠ Note what it is NOT: the lean column is exact at `units_f/units_r` up to 129.5,
so the solid-state term's own sign switch handles a 130x derivative jump at its
operating point without trouble. The fix is a `LAYER_REABSORB`-style honest
diagonal on the gas block — hot loop, moves invariants, wants a session of its own.

**2. ⚠⚠ THE DEFAULT SOLVER TOLERANCE IS NOT CONVERGED FOR A VENTED KILN — 2.6x IN
THE ANSWER, AND IT CORRECTED A ROW THIS PROJECT HAD ALREADY WRITTEN DOWN.**

| rtol / atol | converted at 1100 K | p(CO2) / bar |
|---|---:|---:|
| 1e-6 / 1e-9 (**the default**) | 39.04% | 0.0000 |
| 1e-8 / 1e-11 | **13.97%** | **0.7275** = K(1100 K) exactly |
| 1e-10 / 1e-13 | 13.97% | 0.7275 |

It CONVERGES, so the loose reading is an artefact. **The tight runs are also
FASTER** (1.4–3.3 s against 5–13 s) — the loose solver was thrashing. Cause: the
vent. `k_vent` is 1e3 mol/(bar s), so the gas balance is far stiffer than the
chemistry feeding it. ⚠ **Not M6's term** — it reproduces with the solid-state
term as the network's only reaction. **Any slow source feeding this vent is
exposed to it, which means other examples in this repo may be quoting
tolerance-limited numbers.** Nobody has swept them. That is a cheap, high-value
audit: re-run each example at rtol 1e-8/atol 1e-11 and diff.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's own clamp
is `T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

# THE NEXT TASK — A GAS-CONSUMING SURFACE REACTION, i.e. `PHASE_INDEX["solid"]`

## Why this and not a numbered milestone

It fixes a wrong answer a player can see. `ammonia_synthesis` runs in a flask with
no iron in it, because the catalyst is folded into the barrier. That is the licence
`sulfur_dioxide_oxidation` already takes, and M5 reported it rather than fixing it.

## ⚠ What M6 established about it, so this does not get re-derived

**It IS mass action, and M6's term is measurably NOT a rate law for it.** A gas
REACTANT's pressure sits in the DENOMINATOR of `Q`, so an atmosphere depleted of it
drives the affinity form's reverse flux to **2.6e15 formula units per second**.
`build_solid_state_arrays` REFUSES a declaration with a gas reactant, naming that.
So the two mechanisms are deliberately kept apart:

| | M6's term (`SolidStateArrays`) | what you are building |
|---|---|---|
| example | `CaCO3(s) -> CaO(s) + CO2(g)` | `ZnS(s) + O2(g) -> ZnO(s) + SO2(g)`; `N2 + 3 H2 -> 2 NH3` **over iron** |
| control | thermodynamic — stops at `Q = K` | kinetic — `dG` is hugely negative, it runs |
| rate law | affinity, `(k_f - k_r Q) * units` | **mass action**: first order in a gas pressure, gated on a solid being present |
| home | a term | **a third `PHASE_INDEX` entry** |

## What it needs, in the order the constraints bite

1. **`PHASE_INDEX = {"liquid": 0, "gas": 1, "solid": 2}`**, and a block in the
   vessel RHS for it. Read the comment on that line first — it now carries the
   whole argument for why M6 did NOT add the entry, and it names this case as the
   one that should.
2. **A way for a template to declare a SOLID participant.** A catalyst is neither
   consumed nor produced but must be PRESENT; a roasting sulfide is consumed. Both
   are `nu` on the solid block, so this may be one mechanism.
   ⚠ `ReactionTemplate` matches SMARTS on a molecular graph and **a lattice is not
   a graph** — `[Ca+2].[O-2]` has no bonds to rewrite. So the solid participant
   has to be DECLARED on the template rather than discovered, the way
   `SOLID_STATE_REACTIONS` is a curated table. Do not try to make SMARTS reach it.
3. **The rate law's basis.** M6's term is on mol (solid) and bar (gas); the kernel
   is on mol/L. ⚠ **Decide this by arithmetic before writing code** — a solid's
   "concentration" in the block is meaningless (the block is mol and `V_S` is
   nominal), so a heterogeneous rate written on `nS/V` is a number with no
   referent. First order in `nS` (mol) is the constant-particle-count idealisation
   and is what M6 uses; `nS^(2/3)` (shrinking core) is physically better and has
   INFINITE slope at zero, which `SOLID_GATE_TIME` refuses for a measured reason.
4. **The data is already there.** `mineral_data` has 37 entries as of M6,
   including **all five roasting oxides and all five sulfides** — so `roasting`'s
   DATA refusal is closed and it is waiting on exactly this feature.
   ⚠ `mercury-from-cinnabar` will still need its own template: HgO decomposes at
   roasting temperature and that row gives the METAL.
5. **A catalyst must not be able to seed itself.** See
   `chemsim-solid-gate-fix` — a cycle's gain on its catalyst is unbounded, and the
   round-off-seeded lead chamber reached 89% yield on 1.2e-4 mol of phantom NOx.
   A solid catalyst gated on `nS` has exactly that exposure.

**Done when:** a flask with no iron in it makes NO ammonia, one with iron does, and
a roasting row runs and conserves matter.

## AFTER THAT

**M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away; re-scope
before scheduling)**, M8+ (electrochemistry — ⚠ **that one WILL break the spectator
zeros**). And the cheap audit named above: **re-run every example at rtol 1e-8 and
diff**, because M6 found one quoted number that was 2.6x wrong and nobody has
checked the others.

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Thirteen times now — and M6 is the first time the arithmetic was
done, the wrong thing was built anyway, and building it was WORTH IT because the
prediction and the measurement then agreed to five figures.
⚠ A CLASS IS A MECHANISM CLAIM. Read the rows, not the name. M6 read four classes
and split two of them; `thermal-decomposition`'s four rows are four mechanisms and
have NOT been split yet — that is a small, honest coverage job.
⚠ **A CONSTANT SHARED BETWEEN ROWS IS A CLAIM THAT THEY ARE THE SAME EVENT.**
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS — and now neither is a
converged-looking number at the default tolerance. Re-measure before quoting.
⚠ **A COMMITTED GENERATED REPORT IS NOT A BASELINE.** Regenerate at HEAD.
⚠ Windows console is cp1252: a warning glyph inside a `print()` kills a script.
Docstrings fine, printed text ASCII. (FIFTEEN sessions running — M6 hit it too.)
⚠ **`python - <<'PY'` HEREDOCS BIT AGAIN.** Use the Write tool for anything with
an escape, a quote or a markdown table, and run it as a file.
⚠ **AND WRITING A FILE THROUGH PYTHON'S TEXT MODE ON WINDOWS EMITS CRLF**, which
turned a 25-line edit into a whole-file diff twice this session. This repo is
MIXED: markdown and `.psv` are CRLF, most Python is LF. Check `git diff --stat`
before committing and normalise if a file you barely touched shows as rewritten.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u` — and
do not pipe a long run through `tail`, which holds everything until EOF.

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays; RDKit stays in matter.
NO silent approximations. REFUSE loudly rather than return a confident wrong
number — and a LATENT fragility is a third case: report it, do not refuse it.
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?"
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; **`solid_state=False`
exactly no crystal reacting**; the Born term exactly zero in PURE water; the five
pH values; SAVE_VERSION stores the CONDITION, never the instant; every gaseous
element reference state Hf = Gf = 0 EXACTLY; a reference state its own database
does not price at Hf = 0 is REFUSED; no mineral pricing differently under the two
providers; `ion_data` and `electrolyte` never subtracted from each other; a
declared rate order may never be reversible; the reflux ratio is the ratio of two
drain conductances out of one condenser, declared rather than inferred; the
fragmentation SEARCH runs only after the greedy pass has been REFUSED; an ion is
never counted in the held-ideal flag; a rate CAP scales BOTH pre-exponentials by
one factor; a template that moves a hydrogen ATOM must collapse explicit Hs;
**a lattice may REACT and may never DISSOLVE — the fusion law is still 407x wrong
in both directions, and M6 did not soften that by one digit.**

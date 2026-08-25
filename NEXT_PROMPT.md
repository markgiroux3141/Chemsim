We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M5 and M12 are DONE.**

**START WITH M6 — solid-phase reactions, and aim it at the LIME CYCLE
(`CaCO3 -> CaO + CO2`) rather than at the green-vitriol seed MILESTONES names.**
Both of the lime cycle's solids are already curated with measured CRC data,
whereas Fe2O3 has no entry and zero of the five `roasting` rows are fully priced
— so the lime cycle is the one where a failure is unambiguously the ENGINE's and
not the data's. That was measured at the end of M5; the table is in the M6
section below and MILESTONES §M6 has been corrected.

M5 also gave M6 a second reason to exist: five of M5's twenty templates are
HETEROGENEOUS and are written homogeneous with the catalyst folded into the
barrier, so **a flask with no iron in it makes ammonia** and "you need a
catalyst" cannot be a gate until a reaction can consume a solid.

There is **no measured wrong answer** ahead of it. M5 left three things
REPORTED rather than fixed and none of them is a defect in a running number —
read the M5 section below before deciding they are.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. M0–M5 and M12 done. ⚠ **M5's section records which six
  classes were REFUSED and why**, and **§M6 has been corrected**: its claim that
  the solid formation data is "curated and waiting" holds for the green-vitriol
  reactant and not for its product. M6's own two classes have already been read
  against M5's standard — `roasting` is one mechanism, `calcination` is two — so
  that work is done rather than pending.
HANDOFF.md — what exists, and the ethos to preserve. **Item 83 is M5 and is the
  one to read**; 82 is M12.
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row. M5's rows are at the end.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, **including M5's 11
  re-labelled rows**, and `data/catalog/COVERAGE_REPORT.md` for where coverage
  now stands.
the memory files (auto-loaded), especially chemsim-m5-named-routes,
  chemsim-coverage-catalog, chemsim-template-library and chemsim-rate-ceiling.

```bash
python examples/named_routes.py              # M5's 17 routes, ~24 s
python validation/rate_ceiling.py            # M12's standing audit, seconds
python validation/catalog_coverage.py        # where coverage stands, ~3 min
python -m pytest -q tests/test_named_routes.py   # M5's 38 tests, ~5 s
python -m pytest -q                          # the whole suite, 727 tests, ~11:34
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE IS MINUTES OF SATURATED CPU ON THE USER'S OWN MACHINE.** Run it to
establish a baseline and to verify at the end, not after each change. Say what a
long run will cost before starting one, and **ask first.**

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral/ion floor, a still that is a saveable protocol, a
plate column that reaches its purity target, an ionic lattice that can leave
solution, a solvent mixture that says when it was never modelled, an energy
balance it can report the way it reports a mass one, and **34 templates covering
29 of the catalog's 212 reaction classes.** `SAVE_VERSION` is **5**.
Coverage: **25/173 template-ready routes** (was 7), **29/212 classes** (was 12).
**727 tests green in 11:34, lint clean, 2026-08-24.**

---

# ⚠⚠ WHAT M5 TURNED OUT TO BE, BECAUSE THE LESSON IS NOT ABOUT TEMPLATES

M5's brief was "twenty playable routes, in the greedy set-cover order M1
established". **The greedy order did not survive M1's own standard.** Six of its
top ten classes have no template, and only ONE of the six is a difficulty
problem:

| refused | routes it would have paid | why |
|---|---:|---|
| `catalytic-air-oxidation` | 3 | its four rows are three mechanisms |
| `fermentation` | 2 | a metabolic NETWORK, not a transformation |
| `pyrolysis` | 2 | two of three rows read `coal-marker -> coal-tar-marker` |
| `isomerisation` | 2 | three mechanisms under one label |
| `thermal-cracking` | 1 | a lumped product slate from a radical chain |
| `separation` | 1 | ⚠ the ENGINE fractionates — but a distillation is not a reaction class, and that route's feedstock is a marker |

⚠⚠ **THE ONE-SENTENCE LESSON: M1 BUILT A STANDARD AND M5 IS THE FIRST MILESTONE
THAT HAD TO SPEND IT — AND SPENDING IT COST SIX ROUTES OFF THE TOP OF THE QUEUE.
A PLAN WRITTEN BEFORE A STANDARD DOES NOT AUTOMATICALLY SATISFY IT.** M6 inherits
exactly this: `roasting` and `calcination` are in the plan as classes, and
whether either is one mechanism is an open question until someone reads the rows.

⚠ **AND ONE CLASS WAS SPLIT RATHER THAN REFUSED, WHICH IS THE HARDER CALL.**
`catalytic-hydrogenation` is the most-used uncovered class in the corpus (10
steps) and its rows are FIVE mechanisms — but unlike `fermentation`, every one of
them *is* a clean mechanism. Refusing it would have been wrong in the other
direction. 11 rows were re-labelled; two of the five are built.

---

# ⚠ THREE THINGS M5 LEFT OPEN, EACH REPORTED RATHER THAN FIXED

**1. A REVERSIBLE TEMPLATE IS DISCOVERED IN THE FORWARD DIRECTION ONLY.**
Measured, and invisible from reading either layer:

    build_network(["CCOC(C)=O", "O"], [esterification()])  ->  0 reactions
    build_network(["CC(=O)O", "CCO"], [esterification()])  ->  2 reactions

`_expand_once` matches REACTANT patterns, so **an ester and water in a flask are
inert** however reversible the template is. This is general to every reversible
template in the project. The fix expands on reverse patterns too and roughly
doubles every build's match cost; M5 wrote `ester_hydrolysis` from the ester side
instead. ⚠ It is a gameplay problem as much as an engine one — a player who puts
two products together and expects the reverse gets nothing.

**2. `halogen_disproportionation` IS CORRECT AND CANNOT RUN.** HOCl has no
measured boiling point in any source — the same standing refusal `electrolyte.py`
records for carbonic acid — so `[O-]Cl` has no ion entry and `build_network`
refuses it by name. ⚠ **Curating it is a trap:** ATCT gives HOCl
`Hf = -76.8 kJ/mol` where **Joback gives -211.3, a 134.5 kJ/mol silent error**.
Adding the formation half alone pairs a measured equilibrium with an invented
standard-state shift, in a LIQUID-phase reaction where the shift decides the
answer. A test pins the refusal so whoever adds the pair is told the route opened.

**3. FIVE TEMPLATES ARE HETEROGENEOUS AND WRITTEN HOMOGENEOUS.**
`alkene_hydrogenation`, `nitro_hydrogenation`, `ammonia_synthesis` and both
methanol templates fold the catalyst into an apparent barrier — the licence
`sulfur_dioxide_oxidation` already takes. **The catalyst is therefore not a
species.** This is M6's second reason to exist.

---

# ⚠ TWO LATENT FRAGILITIES, ONE NEW AND ONE UNCHANGED

**NEW: `alkene_hydration` and `library.alkene_dehydration` are the same
interconversion with different barriers**, one reversible and one not (80 vs 160
kJ/mol). Both readings are defensible at their own end of the temperature range,
so a network holding BOTH has two channels between one pair of species and its
steady state is not its equilibrium. Bounded — the barriers differ by 80 kJ/mol,
so one channel is ~1e7x the other at any temperature — and the bundles keep them
apart, but nothing enforces it.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair at every T below 4.28 K**, and the RHS's
own clamp is `T_MIN = 1.0`, which sits inside that band. PRE-EXISTING, **measured
inert**. The precedent for the fix is `gamma_ref_range` in the same file; the
activity kernel is the hottest code in the project and a change there wants the
full suite behind it.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**
Take a bound across ALL blocks first; that bound is label-independent.

---

# M6 — SOLID-PHASE REACTIONS

MILESTONES §M6 has the detail. **⚠ Two of its premises were checked at the end of
M5 and one of them is half wrong — read this section before following that one.**

## THE ENGINE SIDE: there is no solid phase for a reaction to write

`PHASE_INDEX` in `network/builder.py` is `{"liquid": 0, "gas": 1}` and RAISES on
anything else — deliberately, and its comment names a solid-phase reaction as the
next case it would otherwise have swallowed silently. **That is where M6 starts.**
Note that the solid BLOCK already exists in the state vector (M3 put it there for
precipitation) and is written by a TERM, `vessel_integrator.PrecipitationArrays`,
not by any reaction. So the first question M6 has to answer is whether a
solid-phase reaction is a third `PHASE_INDEX` entry or a second term, and the
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` order is the constraint.

## ⚠ THE DATA SIDE, MEASURED 2026-08-24 — AND IT REORDERS THE MILESTONE

MILESTONES §M6 says the green-vitriol seed's "solid-basis formation data is
curated and waiting". **That is true of the REACTANT and false of the PRODUCT.**
`mineral_data.MINERALS` has 25 entries; here is what M6's own rows need:

| target | reactant priced? | product priced? | verdict |
|---|---|---|---|
| `FeSO4 -> Fe2O3 + SO3` (the seed) | yes, `green vitriol` | **no Fe2O3 entry** | needs one mineral |
| `calcination`: `CaCO3 -> CaO + CO2` | yes, `calcite` | yes, `quicklime` | **RUNNABLE TODAY** |
| `calcination`: `Al(OH)3 -> Al2O3 + H2O` | no | no | needs two |
| `roasting` (all five rows) | only `sphalerite` (ZnS) | **no ZnO entry** | **zero rows complete** |

⚠⚠ **SO START WITH THE LIME CYCLE, NOT THE GREEN-VITRIOL SEED.** `lime-cycle` and
`solvay-process` step 5 are the same reaction, and both of its solids are already
curated with measured CRC data — so the FIRST solid-phase reaction can be built
against species that already price, which means a failure is unambiguously the
engine's and not the data's. The seed and the roasting rows each want one or two
`mineral_data` entries first, and that is a separate, well-understood job with a
build script (`tools/build_mineral_data.py`) already written for it.

## ⚠ AND M5's STANDARD APPLIES TO M6's TWO CLASSES. THE ROWS ARE ALREADY READ:

* **`roasting` IS one mechanism** — all five rows are `metal sulfide + O2 -> metal
  oxide + SO2`. ⚠ With one wrinkle: `mercury-from-cinnabar` gives the METAL, not
  the oxide, because HgO decomposes at roasting temperature. One template will not
  cover that row honestly.
* **`calcination` is TWO mechanisms** — two rows are decarbonation
  (`carbonate -> oxide + CO2`) and one is dehydration (`hydroxide -> oxide +
  H2O`). Crediting the class on one of them would be the `deprotonation` mistake
  again. Split it, or build both.

⚠ M3 added 15 element reference states, so the floor is wider than when M6 was
written.

**Done when:** a solid-phase reaction runs, conserves matter, and has an example.
Aim it at the lime cycle first.

---

# AFTER M6

**M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
re-scope before scheduling)**, M8+ (electrochemistry — ⚠ **that one WILL break
the spectator zeros**).

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Twelve times now, most recently by measuring that an ester and
water find zero reactions — which turned "ester-hydrolysis is already covered by
the reversible esterification" from an argument into a refuted one.
⚠ A CLASS IS A MECHANISM CLAIM. Read the rows, not the name. Six refusals and one
split in M5 alone.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS. The tests pin those
rows far looser than the digits quoted. Re-measure before quoting.
⚠ **AND A COMMITTED GENERATED REPORT IS NOT A BASELINE.** `COVERAGE_REPORT.md`
was stale by 39 species when M5 started. Regenerate at HEAD — a `git worktree` of
HEAD costs one command and no risk to the working tree.
⚠ Windows console is cp1252: a warning glyph inside a print() kills a validation
script. Docstrings fine, printed text ASCII. (FOURTEEN sessions running.)
⚠ **`python - <<'PY'` HEREDOCS BIT AGAIN THIS SESSION.** Use the Write tool for
anything containing an escape, a quote or a markdown table, and run it as a file.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u`.

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
a rate CAP scales BOTH pre-exponentials by one factor, because `K = k_f/k_r` is
the invariant it may not move; **and a template that moves a hydrogen ATOM must
collapse explicit Hs, or it forks the species list while conserving every atom.**

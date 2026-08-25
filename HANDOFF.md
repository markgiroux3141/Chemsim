We're building `chemsim`, an emergent chemistry simulator (game inspired by Nile
Red), in `d:\Claude Code Projects\Chemistry Simulator`. Start by reading MEMORY.md
(auto-loaded) plus README.md and the memory files (chemsim-architecture,
chemsim-status, chemsim-coverage-audit, chemsim-ion-transfer) -- they have the full
design, decisions, current state, and an empirical capability audit. Then read
src/chemsim/ to reload the code.

CURRENT STATE: Layers 0-7 complete plus filtration, coupled RIGS, a second
thermochemistry estimator (Benson), a consolidation pass, the property-coverage
fix, TWO process losses (film holdup and the adhering crystal crust), LIQUID-LIQUID
EQUILIBRIUM, a PROTOCOL LAYER, a Layer 7 USER INTERFACE, the CURATED TEMPLATE
LIBRARY, ION TRANSFER BETWEEN PHASES, EXPLICIT ACID CATALYSIS, "WAIT UNTIL" AS A
SOLVER ROOT, a systematic ROBUSTNESS pass, the vent conservation fix, and --
2026-08-20 -- **THE ELEMENT AND MINERAL FLOOR, AND CHAIN 2 STANDING ON IT**.
**679 tests, lint clean, suite ~15 min** (2026-08-24).

**THE FLOOR EXISTS: `properties/element_data.py` and `properties/mineral_data.py`.**
An estimator applied outside its domain returns a well-formed number that means
nothing, and four instances were live -- F2 at Gf -440.5 and S8 at +275.96 where a
reference state is 0 by definition, ozone 716 kJ/mol out, and chloride 101 kJ/mol
apart depending on which provider built the network. `thermochemistry.get` now
REFUSES an element or an ion by name rather than estimating one, which closes the
class instead of one member of it. ⚠ And the previous species-by-species fix had
itself pinned **Br2 and I2 to zero on the ideal-gas basis**, where zero belongs to
the liquid and the solid: their real records are Gf +3.08 and +19.29. See items
56-60.

**CHAIN 2 IS BUILT AND FOUND A REAL BUG.** `examples/oil_of_vitriol.py` -- the
lead chamber is a genuine catalytic CYCLE (80 turnovers on a 0.5 mmol carrier
charge, 100% yield sealed, 22-42% vented) with an emergent temperature ceiling at
~600 K that nobody declared. ⚠⚠ **And a chamber charged with NO carrier at all
still reaches 89% yield**, because the non-negative projection creates 1.4e-7 mol
of round-off and a catalytic cycle has unbounded gain on its catalyst -- 296x,
measured. **The cause is LOCATED: the solid `avail` gate is an un-fixed twin of
`_layer_gates`**, with a 1e9 knee slope giving an empty solid block a Jacobian
diagonal of 3.6e7. Not shipped, because the precedent fix has a documented second
trap. Items 63-64, and it is the top item of NEXT_SESSION.md.

**THE ENGINE HAS A FACE: `python -m chemsim.ui`.** Four worked starting points, a
worker thread so an operation renders as IN PROGRESS rather than blocking, a live
cost meter because cost is concentrated in stiff transients rather than in elapsed
simulated time, and the engine's own reports as a first-class panel. See items
46-55. **The last conservation failure is gone**: the bulk vent destroyed ~100x an
open flask's air and now the worst raw excursion is 4.8e-11 mol, with all four
boiling invariants re-measured and unmoved. `validation/robustness.py` reads
**15 OK, 6 REFUSED, 0 WRONG** against 14 / 5 / 2.

**THE ENGINE WAS READY FOR AN INTERFACE, and neither of the last two sessions was
chemistry.**
A duration can now be a CONDITION rather than a guessed number of seconds, a run is
a pure function of (scenario, SCRIPT) with the condition stored and never the
instant it resolved to, and every abusive state a player can reach has been walked
and classified. Three real pre-existing bugs fell out of doing it: dissolved air
made every open flask report itself boiling, `Vessel.reset` left the previous
attempt's losses on display, and -- the sharp one -- **a refluxing rig destroys
about 0.34 mol of its air**, reported all along on a channel nothing was reading.
That last one is unfixed and is the top item of NEXT_SESSION.md.

**The headline: an acidified aqueous workup is expressible.** A liquid carrying
dissolved salt used to be REFUSED a liquid-liquid split outright, because ions had
no activity model and would otherwise have partitioned to equal mole fraction
between water and toluene. A Born transfer term prices that charge transfer now, so
brine and toluene separate with the salt staying in the water to one part in
162,000 -- and the five pH invariants come back BIT-IDENTICAL, because the term is
referenced to water and is exactly zero there.

Molecules-as-graphs (RDKit hidden in `matter`) → SMARTS reaction templates →
discovered reaction network → Arrhenius/mass-action BDF integrator → 3-phase
NON-IDEAL vessel with energy balance → headless deterministic engine with
save/load.

Reverse rates are DERIVED by detailed balance (templates declare forward kinetics
only). The vessel solves `y = [n_liquid | n_gas | n_solid | T]` as one stiff
system, so boiling point, melting point, boil-off rate, crystallisation and pH
all emerge rather than being looked up. Acid/base works with no pH solver:
dissociation is entered as ordinary reversible reactions. Verified: pure water
pH 7.00, half-neutralised acetic acid pH 4.76 (= pKa exactly), ethanol pins at
351.46 K under a hotplate.

ENVIRONMENT: Windows, PowerShell. System `python` has numpy/scipy/rdkit/thermo/
matplotlib. Install: `python -m pip install -e ".[dev,viz]"`. Test: `python -m
pytest -q` (~25 s). Lint: `python -m ruff check src tests examples`. Ignore IDE
"package not installed" hints — the editor points at a different interpreter than
the one running tests. Examples: esterification, thermochemistry, vessel, workshop.

DESIGN ETHOS TO PRESERVE:
- Strict downward layering: matter(0) → properties(1) → reactions(2) →
  network(3) → numerics(4) → discovery(4.5) → vessel(5) → engine(6).
- `numerics` sees ONLY numpy arrays (the Rust/PyO3 seam — no domain types).
  RDKit stays hidden in `matter`.
- **The setup/hot-loop split is the load-bearing idea.** Antoine, Lee-Kesler,
  Rackett, Rowlinson-Bondi, van 't Hoff and detailed balance are all evaluated
  and collapsed to plain polynomial/Arrhenius coefficients at SETUP time, so the
  kernel evaluates one polynomial form and `A·exp(−Ea/RT)` and has never heard of
  any correlation by name. When adding a physical model, first ask "what uniform
  array form does this collapse to?"
- Own the chemistry behind clean interfaces (deps are swappable). Curated
  experimental data overrides estimates, with provenance on every value.
- Conservation (element/charge, across all three phases) enforced by tests.
- NO silent coverage caps or silent approximations — everything dropped or
  clamped is logged/reported.

DONE (2026-08-16): activity coefficients via UNIFAC. Both target gaps closed.
  * Ethanol/water azeotrope emerges at x = 0.888 / 95.3 wt%, boiling at 351.17 K
    (experiment 0.894 / 95.6 wt%, 351.3 K) — below BOTH pure components. There is
    no azeotrope table; it is just where y = x.
  * Benzoic acid in water at 298 K: 3.26 g/L vs 3.44 measured. The ideal law gave
    1128 g/L. Residual gap: UNIFAC understates the TEMPERATURE slope for an
    associating solute (0.95× at 298 K, 0.48× at 333 K).

How it is built, and what to preserve:
  * `properties/fragmentation.py` — the greedy priority-ordered SMARTS matcher
    with formula verification, extracted from `joback.py`. ONE algorithm, two
    group tables. Joback now delegates to it.
  * `matter.Molecule.substructure_matches()` — added so Layer 1 no longer imports
    rdkit at all. Boundary 1 is now genuinely sealed (it wasn't before).
  * `properties/unifac_data.py` — 113 subgroups + 1270 interaction pairs, all
    cross-checked against the `thermo` oracle in tests. It carries an explicit
    `_SMARTS_CORRECTIONS` block: the conventional ether/ester patterns are
    written as `...[O]` and so match a HYDROXYL, making ethanol fragment as
    CH3 + CH2O and acetic acid as CH3COO. Every one of those was caught by the
    formula check, which is exactly what it is for. `_PRIORITY_CORRECTIONS`
    fixes THF, whose pattern is a subset of CH2O at equal priority (same formula,
    so only the ordering can catch it).
  * `numerics/activity.py` — the kernel. The combinatorial part is written with
    J = Φ/x and L = θ/x so x cancels ANALYTICALLY; a species at zero
    concentration therefore has a finite γ instead of a 0/0, which matters
    because most species in a network are at zero for part of the run.
  * `INTERACTIONS` is sparse on purpose (~half the pairs were never regressed).
    Missing pairs and unmodelled species are REPORTED via
    `vessel.activity_model.report()`, never silently treated as ideal.

ALSO DONE: the UNSYMMETRIC CONVENTION for Henry's-law solutes, which closed the
aqueous-Henry gap at the same time.
  * Standard UNIFAC has no group for a permanent gas, so `properties/psrk_data.py`
    adds PSRK's. It is an EXTENSION, not a replacement: only main groups UNIFAC
    lacks, so no existing parameter is overwritten and the azeotrope/solubility
    results above are bit-identical afterwards. Sound because PSRK's organic
    backbone IS UNIFAC's (1124/1174 pairs identical). Ids offset by 1000 —
    PSRK subgroups 118/119 collide with UNIFAC's sulfone groups.
  * `a_mn` is now (g, g, 3): a_mn(T) = a + bT + cT². 78 gas pairs genuinely need
    it; UNIFAC's own parameters are the b=c=0 case, so one array covers both.
  * p_i = x_i · [γ_i(x)/γ_i^∞(ref solvent)] · H_i(ref). The pure-liquid fugacity
    cancels from the ratio, so H(S)/H(ref) = γ^∞(S)/γ^∞(ref) — the transfer is
    exact in principle, and in water the correction is 1 by construction so the
    calibrated constant is reproduced untouched (γ* = 1.0001).
  * **The reference divisor is T-only, so it collapses to 4 numbers at setup** —
    the project's signature move, preserved. Fitted in 1/T (van 't Hoff), NOT in
    T: it is a ratio of Boltzmann factors, and the inverse basis fits ~10× better
    (N2: 0.15% vs 2.5%). Hence `_poly_inv` alongside `_poly`, and
    `fit_inverse_cubic` alongside `fit_cubic`.
  * Fit residual is MEASURED and reported per species (`reference_fits`), and T is
    clamped to the fitted window (`gamma_ref_range`) so PSRK's quadratics cannot
    extrapolate. CO fits badly (3.6%) and says so.
  * O2 under air at 298 K: water 0.27 mM (measured 0.27, exact by construction),
    methanol 1.55 (2.10), ethanol 1.57 (2.10), benzene 1.44 (1.80), hexane 2.41
    (3.10). Acetone is the bad case at 2.6× high. Every one of these previously
    returned water's 0.27 mM.
  * **Trap worth remembering:** PSRK's published H2 pattern is `[HH]`, and RDKit
    reads a bracketed H as the hydrogen-COUNT primitive — so it matches ANY atom
    with one H, at priority 1e9. It silently ate every hydroxyl and aromatic CH.
    Corrected to `[#1][#1]` in `psrk_data._SMARTS_CORRECTIONS`.

BENCHMARK (the Rust question, answered): RHS goes 140 µs → 231 µs (1.7×) for a
4-species vessel. But the γ kernel is FLAT from 4 species to 25 (78 → 87 µs) —
at these sizes everything is numpy dispatch overhead on small arrays, not
arithmetic. So UNIFAC does NOT justify the Rust seam by itself; the case rests on
fixed per-call overhead that was already there, and Rust would collapse it for
the whole RHS rather than just this part.

ALSO FIXED, and worth knowing about: a **pre-existing** BDF hang. A vessel at
rest (poured out, in equilibrium with its own headspace) has an identically zero
derivative. `num_jac` finds every finite difference below its "too small"
threshold, inflates the perturbation factor unboundedly until it overflows to
inf, and then rejects every step forever. Confirmed present with γ disabled — the
activity work only shifted the trajectory onto it. `VesselIntegrator.run` now
short-circuits: the RHS is autonomous, so a zero derivative means the constant
trajectory is the EXACT solution. Idle vessels are the common case in a game.

ALSO DONE: the three TIER-0 corrections -- systematic errors in things the
simulator already claimed to compute. Everything below is a fix, not a feature.

1. **LIQUID STANDARD STATE** (`properties/standard_state.py`). Formation data is
   ideal-gas; nearly every reaction runs in solution. Per species:
       dGf(liquid) = dGf(gas) + R T ln(Psat/P_std)
       dHf(liquid) = dHf(gas) - dHvap
   dHvap comes from the SAME Antoine curve by Clausius-Clapeyron, so both halves
   share one correlation and the derived entropy is real (water 44.1 vs 44.0
   measured, ethanol 42.7 vs 42.3, acetone 31.6 vs 31.0). **Fischer esterification
   K(298) goes 19.4 -> 8.1 against a measured ~4.** A dissolved gas uses the same
   expression with its Henry constant. Applied to liquid-phase reactions only --
   a gas-phase reaction keeps the ideal-gas basis, dispatched on `reaction.phase`.
   * **The trap: pH.** Ion data is back-derived from measured pKa AGAINST the
     acid, so the anchor must be taken in the same standard state. Miss that and
     every pKa moves ~3 units (acetic acid and water are ~9 kJ/mol each and both
     sit on the same side). `ion_thermochemistry` now takes a volatility provider
     and anchors on shifted values; pH 7.00 / 2.89 / 4.76 / 8.88 all unchanged.
   * Species below a 1e-12 bar vapour-pressure floor are REFUSED and reported --
     a discovered polyester oligomer extrapolates to 1e-20 bar, which would price
     its formation at -114 kJ/mol and overflow the equilibrium.
   * `build_network(..., liquid_standard_state=False)` reproduces the old basis,
     kept so the difference can be measured rather than only described.

2. **MODIFIED ARRHENIUS** `k = A * T**n * exp(-Ea/RT)`. The activity->molarity
   conversion carries a factor T**delta_n which is not Arrhenius; it used to be
   folded into A_rev at T_ref, leaving K drifting as (T/T_ref)**delta_n. It now
   lives in the exponent: `n_rev = n_fwd + delta_n`, exact at every temperature.
   `n` is zero for every DECLARED rate -- detailed balance is the only thing that
   sets it -- so the common case stays pure Arrhenius and the kernel skips the
   `T**n` array op entirely when nothing needs it.

3. **EVANS-POLANYI BARRIERS** -- `ReactionTemplate(..., alpha=0.5)`. Rates were
   the last hand-authored thing: one template gave every substrate the same
   barrier, so selectivity within a family was an author's choice. Now
   `Ea_i = Ea + alpha*dH_i`, so a more exothermic member is faster (three alcohols
   on one esterification template: 44532 / 45018 / 45655 J/mol, ordered by dH).
   alpha defaults to 0 = exactly the old behaviour. The reverse needs nothing:
   detailed balance yields `Ea - (1-alpha)*dH`, which IS the reverse
   Evans-Polanyi relation with transfer coefficient (1-alpha).

DONE (2026-08-16): CURATED FORMATION DATA, in both standard states --
`properties/formation_data.py`, 82 ideal-gas and 58 liquid entries. This was the
previous session's top recommendation and it closed the per-species error from
up to 17 kJ/mol to under 0.5.
  * dGf is DERIVED from dHf and S0 against the CODATA element reference states
    rather than transcribed, so both halves of an entry are consistent with each
    other by construction and the entropy a caller derives from the pair is real.
  * Every entry had to survive two cross-checks against correlations that never
    touched the formation tables: `dHf(g)-dHf(l) == dHvap(298)` and
    `dGf(l)-dGf(g) == R T ln(Psat)`. 102 candidates -> 82 gas, 58 liquid at a
    3 kJ/mol tolerance. Exclusions are LISTED with their residuals at the bottom
    of the module. The checks caught two tabulated gas entropies ~100 J/(mol K)
    below additivity (DMSO, morpholine) = ~30 kJ/mol of silent error.
  * **Do not mix sources within an entry.** Taking dHf from ATCT (better) and S0
    from CRC put a 0.6-0.9 kJ/mol inconsistency INSIDE each entry, which does not
    cancel across a reaction -- it moved esterification K by nearly 2x. Both
    halves of a basis are now pinned to CRC where CRC has both.
  * The liquid table exists for one species class in particular: a carboxylic
    acid's vapour is ~95% dimer, so `R T ln(Psat)` prices the wrong molecule.
    The size of that error is visible in the data itself -- acetic acid's
    dHf(g)-dHf(l) is 51.4 against a measured dHvap of 23.4, the missing 28 being
    the dimerisation enthalpy. A measured liquid entry sidesteps it entirely.
  * Formation data is an OVERLAY on a Joback record (like `_CURATED_FUSION`), so
    a species Joback cannot fragment has nothing to overlay onto -- its entry
    would sit INERT. `formation_data.PHYSICAL_PROPERTIES` supplies the missing
    half (Tb/Tc/Pc/Vc/Tm/Hfus + an ideal-gas Cp polynomial) for the nine species
    in that state: formic acid, benzaldehyde, furfural, DMSO, CS2, methyl
    formate, DMF, formamide, propionic anhydride. `thermochemistry` composes the
    two tables into ordinary fully-curated entries, so there is no new
    resolution tier and Hf/Gf still have ONE home. **Formic acid was the sharp
    case** -- a bench reagent, in the pKa table, with no thermochemistry at all;
    0.1 M now reads pH 2.39 against Henderson-Hasselbalch's 2.38.
    - **Cp is FITTED, not transcribed** -- the tabulated correlation is sampled
      over 273-600 K and least-squares fitted to the a+bT+cT^2+dT^3 form the
      kernel uses, the same move as fitting Lee-Kesler to Antoine. Residuals are
      all under 0.15% and each is recorded next to its entry.
    - Independent check, and a sharp one: Tb/Tc/Pc go in, and the acentric
      factor + Lee-Kesler + the Antoine fit must come back out agreeing the
      species boils at 1 atm where it is measured to. All nine within 1.4%, and
      CS2 pins at 319.5 K in a real vessel against a measured 319.4.
    - This fixes nine NAMED species, not the classes they belong to. Benson is
      still the general fix for aryl aldehydes/formamides/sulfoxides at large.
  * Consequences worth knowing: Fischer esterification's LIQUID dH is -3.2
    kJ/mol (measured), not the -18.4 Joback gave it on the ideal-gas basis it
    never left -- so an insulated flask warms ~8 K, not 20, and that test's
    threshold moved. And the standard-state correction now reads 333 -> 8.66
    rather than 19.4 -> 8.1: the correction was always that big, it just looked
    small because Joback put the gas-phase constant 17x too low.

DONE (2026-08-17): SOLID ISOLATION and COUPLED RIGS -- the two equipment items.

FILTRATION (`Vessel.filter_into`, Layer 5; `FILTER` event, Layer 6). Precipitation
already worked; what was missing was any way to COLLECT a crop. This is the ONLY
new primitive solid isolation needed -- decant is `pour_into(phase="liquid")` and
already existed, wash is charge-solvent-then-filter, and dry is evaporation the
vessel already does.
  * Two physical parameters, not tuning knobs. `retention` is the mother liquor
    held in the cake by capillarity -- and DISSOLVED SPECIES TRAVEL WITH IT, which
    is the whole reason washing exists; setting it to zero would make filtration a
    perfect purification. `passthrough` is fines through the paper, zero by
    default because it is a defect not a mechanism, but present so a low yield can
    have an honest cause.
  * **The purity/yield trade-off is emergent.** Recrystallise benzoic acid from
    water with an NaCl tracer: cooling drops 88% of it out, filtering leaves the
    cake at 80.5% purity, and one cold wash takes Na+ from 10 mmol to 1.0 and
    purity to 97.3% -- at the cost of 2.5% of the product. Nothing scripted it;
    it is the solubility law running forward.

RIGS (`numerics/rig_integrator.py` Layer 4, `vessel/rig.py` Layer 5). Coupled
vessels as ONE stiff system, `y = [vessel_0 (3n+1) | vessel_1 | ...]`.
  * **No refactor was needed.** `VesselIntegrator.make_rhs` already closes over a
    whole 3n+1 state, so the rig calls it on a SLICE for the diagonal blocks and
    adds edge terms. There is no second copy of the vessel RHS.
  * Four edges: VAPOUR (bidirectional, pressure-driven, smooth tanh upwinding),
    DRAIN (one-way liquid, first order in holdup -- a drain, NOT level-driven; no
    geometry is modelled), THERMAL (UA between vessels), METER (dropping funnel at
    a set mol/s; the rate is a parameter an EVENT sets, deliberately not a time
    window inside the RHS, which would be a mid-solve discontinuity).
  * Enthalpy travels with material or hot vapour entering a cold condenser is a
    free lunch. `jac_sparsity` is passed from the start (BDF's dense num_jac is
    ~245 RHS calls per Jacobian for a 4-vessel rig).
  * **A one-vessel rig is BIT-IDENTICAL to a lone vessel** with `jac_sparsity=None`
    -- the cheapest guard against regressing all of Layer 5. With sparsity on it
    agrees to solver tolerance; that difference is num_jac's grouping, not physics.
  * **Reflux and distillation needed no new physics.** Vapour arriving in a cold
    vessel finds p > p_eq, the existing evaporation term runs backwards, latent
    heat comes back out, a thermal edge carries it away. Reflux pins a 50/50
    ethanol/water pot at 352.9 K (real ~353) at exactly 1.013 bar, indefinitely.
  * **THE DEMO: a still finds the azeotrope by itself.** Enrichment falls
    monotonically and crosses ZERO at x = 0.894 -- below it the distillate is
    richer in ethanol, above it distilling enriches WATER -- and the pot
    temperature is at its minimum, 351.18 K, exactly there. There is no azeotrope
    table in this codebase.

  * **A PRE-EXISTING BUG the rig exposed: the vent was one-way.** A vessel could
    never draw air back in. For a lone flask that is nearly invisible; couple two
    and boiling sweeps the air out through the condenser, after which the whole
    rig settles at the cold end's vapour pressure (0.05 bar) and "boiling point"
    stops meaning anything. Now bulk bidirectional, carrying the donor's
    composition -- i.e. the room is just a fixed far end of a vapour edge.
    - **It is ALL-OR-NOTHING on the atmosphere, and must be.** Bulk flow carries
      composition, so a network with O2 but no N2 would inhale PURE OXYGEN up to
      1 bar, quintupling dissolved O2. Renormalising causes that; refusing to
      renormalise leaves it unable to repressurise. There is no honest partial
      credit, so a vessel that cannot represent ~all of the room keeps the old
      outward-only vent and `Vessel.atmosphere_report` says so. Put N2/O2 in the
      network for any rig that boils.
    - Two failed attempts worth not repeating: a per-species partial-pressure
      inflow CHATTERS against the bulk outflow at k_vent=1e3 (the suite hung);
      and a softplus gate is 0.69*scale at zero, which times k_vent is a
      permanent 0.07 mol/s leak that stopped solvents pinning at their boiling
      points. The bulk form is exactly zero at the crossing because of its
      leading dP factor.
    - COST: the suite went from ~45 s to ~95 s (plus 74 s of new rig tests).

DONE (2026-08-17): BENSON GROUP ADDITIVITY, the second estimator.
`properties/benson.py` + `benson_data.py`. Sits BELOW curated data, ABOVE Joback.
  * **Values come from MIT's RMG-database** (`input/thermo/groups/group.py` and
    `ring.py`), the open machine-readable form of Benson's tabulation plus later
    revisions. Cloned and parsed; every entry keeps its RMG node label and source
    note, so a straight-from-Benson value is distinguishable from a CBS-QB3
    refit. 758 groups + 12 ring corrections.
  * **THE TRAP, and it is silent: RMG MIXES kcal AND kJ WITHIN ONE FILE.**
    Benson-sourced entries are kcal/mol and cal/(mol K); later revisions are
    kJ/mol and J/(mol K). `Cs-CsHHH` reads -10.2 and `Cs-OsHHH` reads -42.9 --
    the same quantity to within a revision, printed 4.184 apart. Assuming either
    unit throughout makes every oxygen group 4x wrong, which **validates fine on
    alkanes** and then destroys anything with a functional group. The parser
    reads the declared unit per entry and raises on an unrecognised one.
  * **Benson is NOT a SMARTS table**, deliberately. Its groups are local topology
    (a polyvalent atom plus the TYPES of its ligands), so every polyvalent heavy
    atom contributes exactly one group and there is nothing to arbitrate -- unlike
    Joback/UNIFAC, which need `properties.fragmentation`'s priority-ordered
    matcher because their groups are overlapping patterns. New Layer 0 primitives
    `Molecule.topology()` -> `AtomView`, `ring_sizes()`, `ring_atom_indices()`,
    `graph_automorphism_count()`. Plain data, RDKit stays sealed.
  * **Symmetry is NOT optional.** Group values are INTRINSIC entropies, so the
    caller owes `-R ln(sigma)`. Omit it and alkanes look fine while every
    symmetric molecule is wrong -- benzene by R ln 12 = 20.7 J/(mol K) = 6 kJ/mol
    in dGf. sigma_ext comes from the HEAVY-ATOM graph automorphism count
    (hydrogens excluded on purpose: with them a methyl contributes 3! where only
    3 rotations are physical, making ethane 72 instead of 18), times terminal
    rotors. Verified: ethane 18, ethanol 3, benzene 12, toluene 6, acetone 18.
  * **It improves ACCURACY, not coverage.** Group additivity says nothing about
    Tb/Tc/Pc, so those stay Joback's and a species Joback cannot fragment is
    still refused. Measured on the 82 curated ideal-gas species: **median dGf
    error 1.6 kJ/mol vs Joback's 2.8**, refusing ~12% which keep Joback. Gains
    concentrate where Joback is weakest -- acetanilide 4.7 vs 89.4, a branched
    octane 7.7 vs 30.6. Benzene comes out at 82.84 kJ/mol against 82.9 measured,
    with a ring correction of exactly zero (the Cb group already carries the
    resonance) -- the cleanest confirmation the tables are on the same footing.
  * `ThermochemistryProvider(benson=False)` reproduces the Joback-only basis, so
    the difference can be measured rather than only described.
  * **A REGRESSION APPROACH WAS TRIED FIRST AND FAILS -- do not retry it.** 247
    unique structures, ridge-regularised, 5-fold cross-validated: the groups are
    heavily collinear because the ones that matter only co-occur (`CO-(C)(O)` and
    `O-(C)(CO)` appear in esters and nowhere else, so ~5 species must determine
    both). CV error 35-38 kJ/mol vs Joback's 33-42, with methyl acetate 187
    kJ/mol out. Published parameters carry decades of fitting; a few hundred
    noisy rows cannot reconstruct them.
  * (All four "STILL MISSING" items here were addressed by the 2026-08-17
    consolidation above -- see items 3-6. The gauche corrections are adopted, the
    ring table went 12 -> 44, nitriles and sulfoxide carbons are mapped, and the
    aromatic interactions were measured and deliberately rejected. Nitroaromatics
    and pyridine turned out not to exist in the source at all.)
  * NOTE the harness homologue panel is UNCHANGED at 4.5 kJ/mol, and correctly
    so: all five alcohols and their esters have CURATED data, which outranks
    Benson. That panel cannot test Benson; the 82-species comparison above does.

DONE (2026-08-17): CONSOLIDATION. All of NEXT_SESSION.md's Tier 1, plus Tier 2's
Benson correction item. Every change below is a fix or a measurement, not a
feature, and `validation/benson_accuracy.py` is the new harness that judges the
Benson half of it.

1. **`phase="any"` now means what it says.** It validated, was documented, and did
   nothing: `builder.to_arrays` mapped anything that wasn't "gas" to the liquid
   index. `ReactionTemplate.phases` resolves it into concrete phases and the
   builder instantiates ONE FORWARD/REVERSE PAIR PER PHASE.
   * **They cannot be collapsed into one flagged reaction**, which is why two
     reactions rather than a flag: a liquid-phase reaction is moved into the
     pure-liquid standard state and a gas-phase one keeps the ideal-gas basis, so
     detailed balance derives genuinely different reverses (A_rev 4.2e5 vs 5.1e6,
     Ea_rev 53200 vs 68430 J/mol on the same esterification).
   * `builder.PHASE_INDEX` is now explicit and total — an unknown phase RAISES.
     That was the point of fixing this line first: a default-to-liquid mapping
     cannot fail loudly, so the next phase added would have been swallowed too.

2. **The RHS clamp no longer creates matter, and the measurement is the story.**
   `np.maximum(y, 0)` on the final state was the entire cause. Measured over a
   600 s two-vessel run: **the trajectory conserves ethanol to 4e-15 and water to
   2e-21** — the RHS's fluxes are all antisymmetric, so the ODE was never at
   fault. Water finished with its solid block at −1.26e-6 mol and its liquid at
   +1.02e-6, a **cancelling numerical dipole**; clamping the negative half alone
   kept the positive half and invented 1.26e-6 mol of water in a vessel that
   never held any.
   * `numerics.project_non_negative` zeroes the negative entries and takes the
     same amount back out of the phases holding the other half, largest first, so
     every species' TOTAL is exactly preserved and the redistribution is bounded
     by the solver's own tolerance. Water's drift went 1.26e-6 → 2.4e-21.
   * **The rig projects across ALL vessels at once**, and must: the dipole does
     not respect vessel boundaries (the hot vessel was 2.4e-7 short and the cold
     one 2.4e-7 long), so a per-vessel projection would have created exactly what
     the other vessel was holding.
   * A species whose TOTAL went negative has nothing to settle against; that
     residual is genuinely created, is round-off sized, and is reported by
     `Vessel.conservation_report()` rather than swallowed.
   * `test_rig.py` asserted `abs=1e-5` to bound this; it now asserts `abs=1e-12`.

3. **Benson: three silent wrong numbers in the data pipeline**, all found by the
   new harness's fat tail, all caused by RMG's tree collapsing onto our
   first-order keys with FILE ORDER deciding the winner. `tools/build_benson_data.py`
   now ranks candidates by specificity (fewest generic alternatives, then least
   depth) and PRINTS every collision with its spread.
   * A generic nitrogen node beat the concrete amine one — propylamine was
     15.8 kJ/mol too negative, triethylamine 54.
   * A generic sulfur node whose thermo ALIAS points at the S(IV) value beat the
     divalent one — **every vinyl thioether and every thiophene carbon was priced
     as a sulfoxide.**
   * The oxo fold was keyed on ATOM TYPE (`Od`) where RMG sometimes writes a plain
     `O` with a double bond, so acetyl chloride's carbonyl oxygen became an
     ordinary ligand and `CO-(C)(Cl)` did not exist at all. It is keyed on
     ELEMENT + BOND ORDER now, which is what `benson._is_terminal_oxo` already did.
   * **Genericity outranks depth, and that order is measured.** All three
     mis-picks were a generic node beating a concrete one, including the
     vinyl-ester carbonyl where the generic entry would win by 84 kJ/mol in the
     wrong direction. Depth is often RMG restating what an atom type implies.
   * Result on the 82 curated ideal-gas species: **paired median dGf error 1.60 →
     1.56 kJ/mol, but the MEAN 6.41 → 2.94 and the WORST 71.8 → 17.1** (Joback
     2.82 / 6.54 / 66.7). The median was never the problem; the tail was.

4. **A fourth tabulation-mixing trap, and it is the session's main lesson.** RMG
   carries Benson's aryl-ester carbonyl next to Paraskevas's CBS-QB3 ester oxygen.
   Their SUMS agree to 3 kJ/mol; their SPLITS differ by 78. Mixing them put methyl
   benzoate +70 kJ/mol out — worse than the estimator Benson is meant to improve
   on. `INCOMPATIBLE_SPLIT` drops the key and aromatic esters keep Joback.
   **A group value is only meaningful against the group basis it was fitted with**,
   and this session hit that rule three separate times (see 6).

5. **Benson reaches heteroaromatics, and 44 rings instead of 12.**
   * The blocker was a CONVENTION SPLIT nobody had spotted: benzene rings are
     priced with delocalised `Cb` groups and a ring correction of exactly zero,
     while every other aromatic ring is priced on its **Kekulé structure** with
     localised groups plus a large correction. RMG has no aromatic-heteroatom
     group values at all — so furan refused for want of `Ob-(Cb)2` while its
     −26.4 kJ/mol ring correction sat in the table unused, i.e. the furan entry
     was dead code. New `Molecule.kekulized_topology()`; `benson.benson_views`
     mixes the two views atom by atom. **Furan comes out −34.7 against a measured
     −34.8.** Furfural and thiophene are priced now too.
   * Rings are named by a **canonical cyclic signature** — the element sequence
     round the ring with bond orders, minimised over rotations and both
     directions — instead of (size, element tally, double-bond count). The tally
     cannot tell 1,3-dioxane from 1,4-dioxane, whose corrections differ by
     6.4 kJ/mol, so it had to refuse both or silently pick one. The table is
     specified by **one exemplar SMILES per ring**, so it is readable chemistry
     that cannot drift out of step with the algorithm, and duplicate signatures
     raise at import.
   * Fused aromatic carbons became their own `Cbf` type, because naphthalene
     otherwise regressed. **Their NEIGHBOURS still name them `Cb`** — Benson's own
     convention and RMG's, and departing from it asks for `Cb-(Cb)(Cbf)(H)` keys
     no tabulation has.
   * **Pyridine and nitrobenzene still refuse, and that is the honest answer, not
     a gap to close**: `ring.py` contains no pyridine correction and `group.py`
     no aromatic-nitrogen or nitroaromatic group. The brief expected these to be
     fixable; they are not, from this source.

6. **Non-nearest-neighbour corrections: one family adopted, one rejected, both
   measured.** `benson_data.CORRECTIONS` + `benson.corrections()`.
   * **RMG no longer ships `gauche.py`.** The gauche/branching corrections are the
     `CsCs-ST`.. family in `longDistanceInteraction_noncyclic.py`. Label grammar
     reverse-engineered: rank = count of SINGLE-BONDED heavy neighbours (2/3/4 =
     S/T/Q), which is what makes `CdCs-ST` consistent.
   * **ADOPTED — branching.** Benson's own values on the same alkane groups we
     use. Mean |Hf| error over five branched alkanes **11.61 → 2.25 kJ/mol**:
     2,2,3,3-tetramethylbutane 25.9 → 5.8, 2,2,3-trimethylbutane 14.8 → 1.5,
     isooctane 16.2 → 0.1.
   * **REJECTED — aromatic ortho/meta/para** (Ince & Reyniers 2015), who regressed
     their terms together with their own group values. Over eleven disubstituted
     benzenes the mean |Hf| error goes **6.66 → 9.75 kJ/mol**, salicylaldehyde
     6.0 → 33.4 because the −27.4 kJ/mol ortho OH/CHO term double-counts a
     hydrogen bond the `Cb` values already partly carry. Kept in
     `AROMATIC_INTERACTIONS`, recognised but not priced, and **re-measured every
     run** so the rejection is a standing check rather than a deleted branch.
   * **THE HALVING TRAP.** RMG's matcher tries both assignments of its two
     labelled atoms, so it stores symmetric entries at HALF value — announced only
     in prose. We count each unordered pair once, so those 15 entries are DOUBLED.
     Miss it and every symmetric case is exactly half-corrected, which looks like
     ordinary scatter.
   * **A missing correction is ZERO, not a refusal** — the opposite of the rule for
     groups and rings, because a correction refines a complete estimate rather
     than completing it. m-xylene has no meta CH3/CH3 value and must still price.
   * **The 82-species set cannot see this family at all.** Measured: NONE of the 82
     has two adjacent branched sp3 centres and none has two halogens on adjacent
     carbons, so the panels use a second set chosen to exercise the corrections,
     with references pulled from `chemicals` at run time.
   * Still unread: the halogen 1,3 family (up to 42 kJ/mol, no curated species
     exercises it), the mixed `OsCs-`/`CdCs-` variants, `radical.py`,
     `polycyclic.py`. `other.py` turned out to be ketene corrections only, ≤6.7
     kJ/mol — not the gauche terms the brief expected there.

Nine systematic residuals were left in place deliberately, the largest being
**primary alcohols ~7 kJ/mol too negative**: RMG pairs Paraskevas's CBS-QB3
alcohol groups with Benson's alkane groups, and there is no alternative entry in
the clone. It is an inconsistency in the source, reported by the harness rather
than patched with a number from outside it.

TWO ARTIFACTS ADDED 2026-08-17, both re-runnable and both quoted by NEXT_SESSION.md:
  * `validation/coverage.py` — the audit, re-measurable instead of quoted. **63/70
    resolve** on a reconstructed target list (categories match the 2026-08-16 run,
    the list does not, so treat the trend against 46/70 → 51/70 as indicative).
    **All 7 failures share one cause**: Joback cannot fragment them and Benson
    supplies no Tb/Tc/Pc. Benson prices acetic anhydride at −576.2 kJ/mol against
    a measured −572.5 and the provider still refuses it, because Benson is only
    consulted after Joback succeeds. That is the architectural hole.
  * `examples/multistep_prep.py` — benzoic acid from ethyl benzoate: saponify,
    acidify, crystallise, filter, wash twice. **100.0001% mass closure.**
    - **The saponification has no template.** The only ester reaction is the
      reversible Fischer esterification; hydrolysis runs to completion because
      hydroxide removes the benzoic acid as fast as the reverse makes it. Le
      Chatelier out of the acid/base equilibrium.
    - Dissolved benzoic acid at 275 K is 1.62 g/L against ~1.7 measured, which is
      what makes the crop size trustworthy rather than decorative.
    - **It reports 93.2% yield at ~100% purity, which is a CEILING, not a result.**
      No transfer losses exist, nothing traps impurity where washing cannot reach,
      and there is exactly one template so there is nothing to be impure with.
      Workstream B of NEXT_SESSION.md is about that.

DONE (2026-08-17, later): THE PROPERTY-COVERAGE GAP CLOSED, and FILM HOLDUP as the
first honest process loss. 412 tests pass, lint clean. Coverage 63/70 -> 66/70.

WORKSTREAM A -- the architectural hole was the whole story, and the brief's
diagnosis was right about the cause and wrong about two of its numbers.

1. **A record is now assembled from two INDEPENDENTLY resolved halves.**
   `ThermochemistryProvider.get` used to consult Benson only inside the `else`
   branch after Joback had already succeeded, and `_assembled_entries` required
   curated formation data before a `PHYSICAL_PROPERTIES` entry counted. So a
   physical half could never pair with a Benson formation half -- Benson priced
   acetic anhydride to within 3.7 kJ/mol of measurement and the provider refused
   the species outright. The order is now, per half:
       FORMATION  curated measured > Benson > Joback
       PHYSICAL   curated measured > measured Tb + Wilson-Jasperson/Fedors > Joback
       Cp         curated physical > Benson > Joback   (its OWN chain)
   * **Cp needs its own chain and that is not cosmetic.** It is emitted by the
     formation ESTIMATORS but tabulated with the physical half, so tying it to
     whichever formation tier won would silently drop Benson's Cp for every
     species that also has a curated Hf.
   * `ThermoData.physical_source` is a field now. `volatility` used to infer the
     origin of Tb/Tc/Pc by testing `source.startswith("experimental")`, which a
     composite string breaks.

2. **`properties/critical.py` + `critical_data.py`** -- Wilson-Jasperson (Tc, Pc
   from a known Tb) and Fedors (Vc), extracted from `thermo` 0.6.1 (MIT, verified)
   at build time by `tools/build_physical_data.py`. **Bit-identical to the oracle
   across 24 species** covering rings, amines, halides, sulfur, nitro and fused
   rings. `thermo` stays a test-only oracle; nothing new at runtime.
   * The Lee-Kesler shape functions MOVED here from `volatility`, to break a
     cycle: `volatility` imports `thermochemistry`, and `thermochemistry` now
     needs an Hvap derived from the Lee-Kesler curve. Re-exported so callers are
     unaffected; `VolatilityError` is a subclass of `CriticalPropertyError`.
   * **Hvap is DIFFERENTIATED out of the Lee-Kesler curve analytically**, not
     taken from Riedel/Chen/Vetere. No new correlation enters, so the latent heat
     and the vapour pressure cannot disagree -- a flask must not boil at the right
     temperature and the wrong rate. With MEASURED Tc/Pc the residual is +1.4% to
     +5.8% (median +4.1%), which is exactly the `dz = 1` ideal-vapour assumption.

3. **`properties/physical_data.py`** -- 33 species of measured Tb/Tm/Hfus/Tc/Pc/Vc
   from `chemicals` 1.5.2, each value carrying its database AND a tier.
   * ⚠ **THE TRAP, and it nearly closed a gap with our own estimate.**
     `chemicals` serves JOBACK predictions through the same accessor as its
     measured compilations. For metformin the only Tb source it offers is
     `['JOBACK']`, returning 609.52 K -- bit-identical to what our Joback computes
     from the same groups. Its `Hfg` is the same story. The builder excludes every
     estimated method and refuses the species instead.
   * A second tier was needed on top of that. `YAWS` ("no data points are
     sourced"), `PSRK` ("experimental *and estimated*") and `PINAMARTINES` are
     published but not auditable to a measurement. The decisive check is
     empirical: **PINAMARTINES gives saccharin a critical temperature of 968 K,
     and saccharin decomposes near 500 K without ever boiling.** Tc/Pc/Vc are
     taken from the EXPERIMENTAL tier only -- Wilson-Jasperson's error is *known*,
     which beats a number that may itself be an estimate from a method we cannot
     see. Tb has no such choice (nothing here estimates a boiling point), so a
     compilation Tb is accepted and stamped. MDI is the case that matters.
   * **Tc and Pc are taken as a PAIR or not at all**, because they combine into
     the acentric factor. This caught formic acid, which has a measured Tc and no
     measured Pc.

4. **The brief understated Wilson-Jasperson's Pc badly, and the check it proposed
   cannot see it.** Measured over the nine curated species: Tc mean 1.9%, Vc 7.7%,
   **Pc mean 27.9% and worst 68.5%** -- not the 12% the brief quoted from acetic
   anhydride alone.
   * ⚠ **"Boils at 1 atm" is NOT an independent check.** omega is *derived* by
     inverting Lee-Kesler at Tb precisely so the curve passes through (Tb, 1 atm),
     so no error in Tc or Pc can appear there. It measures the Antoine FIT
     residual (all 17 within 1.4%) and nothing else. The independent check is the
     ACENTRIC FACTOR against tabulation, and it bites: |d omega| is 0.047 mean
     from measured Tc/Pc against **0.152 from Wilson-Jasperson's**.
   * The consequence is bounded and specific: a species still BOILS at the right
     temperature because omega absorbs the Pc error. What a bad Pc corrupts is the
     SLOPE -- the latent heat, and the vapour pressure away from Tb.

5. **A silent wrong answer that the restructure INTRODUCED, and the guard for it.**
   With halves independent, a Benson formation half alone produced a record with
   no Tb/Tc/Pc, and `volatility` labels such a record "decomposes before it
   boils". Correct for a sugar; a confident lie for acetic anhydride, which boils
   at 412 K. An empty physical half now REFUSES and names the fix. A measured Tm
   is enough to pass, because that means the species was looked up and nothing
   boils it -- a finding about the species, not a hole in our data.

6. **66/70, and the four remainders are data-source limits, not gaps.** The
   corrected baseline is 64/70 (63 was a harness artefact: `[Na+].[OH-]` is not a
   molecule and now resolves ion by ion through `electrolyte_provider`). Eight
   species newly resolve, not just the two on the audit list -- acetic anhydride,
   vanillin, maleic and succinic anhydride, dimethyl sulfone, p-anisaldehyde,
   salicylaldehyde, N-methylformamide.
   * **metformin and MDI: Joback's `-N= (nonring)` group has a dHf contribution
     and NO dGf contribution.** Verified against the oracle -- `thermo` has the
     identical single gap, 1 group of 41. Benson has no guanidine carbon and no
     isocyanate carbonyl. MDI's three `chemicals` Hf sources span 245 kJ/mol.
   * **saccharin**: no aryl-amide carbonyl in Benson, and no Tb in any source.
   * **glyphosate**: phosphorus, absent from Joback, Benson AND Fedors.
   * `validation/coverage.py` now names WHICH HALF failed and reports each tier's
     contribution; `validation/physical_estimation.py` is the four-panel harness.

WORKSTREAM B -- film holdup built, measured, and it does NOT explain the prep's
gap. That last part is the result.

7. **`vessel.TransferLosses`**, applied in `pour_into` and `filter_into`.
   MECHANISM: gravity drainage, `delta = sqrt(nu / (g t))` -- the film is DERIVED
   from a transport property and a drain time, not assigned. 319 um after 1 s,
   143 um after 5 s, 29 um after 120 s.
   SCALE: wetted area = `4.836 * V^(2/3)` (a sphere, i.e. the minimum-area case,
   so every number is a lower bound). **Measured absolute holdup ratio 0.2154x per
   decade against a predicted 0.2154x** -- so relative loss grows 2.154x as the
   batch shrinks tenfold. Nothing was told to do that; it is the test a yield
   multiplier cannot pass.
   COUNTERMEASURES: run it bigger, drain longer (`t^(-1/2)`), and **rinse and
   combine -- which needed no code at all**, because the film is LEFT IN THE
   SOURCE VESSEL rather than deleted. On a solution transfer: 2.88% lost from
   54 mL at a 2 s pour, 0.74% at 30 s, 0.00% after two rinses.
   * **Conservation is bit-exact (drift 0.0)** for exactly that reason: the
     operation only ever FAILS TO MOVE material. `losses=None` is the default and
     is exactly lossless.
   * Nothing stochastic, nothing in the RHS -- computed once per transfer at an
     event boundary, the same reasoning as the METER edge's rate.
8. ⚠ **AND IT CHANGES THE PREP'S YIELD BY NOTHING. 93.25% before and after.**
   The reason is worth more than a number would have been: **every transfer in
   that prep moves WASTE, not product.** The product travels as a solid in the
   cake, so the film left on the pot wall is mother liquor that was already being
   discarded. Film holdup is a correct mechanic aimed at the wrong loss for a
   crystallisation route. **The B1-first ranking should change: what that route
   needs is MECHANICAL SOLID LOSS on collection (B2).** Nothing was tuned to hide
   this -- a `drain_time` chosen to move the yield would have had to act on a
   stream that does not contain the product.
   * A caution from the harness itself: omitting the intermediate wash cakes from
     the balance made closure read 99.97%, which looked like the loss destroying
     matter when it was the harness failing to look where the matter went.

DONE (2026-08-17, last): THE TEMPLATE LIBRARY, which closes the founding claim.
432 tests pass, lint clean.

9. **`reactions/library.py`** -- the first curated template collection, with the
   same provenance discipline every other parameter table in this project has.
   Templates used to live inline in whichever example needed one, and the cost was
   not tidiness: **a network with ONE template cannot produce a side product**, so
   purity was ~100% by construction and two thirds of the project's founding claim
   (that yields, side products AND sensitivity emerge) had never been tested in the
   real code. `spike/spike_reactor.py` demonstrated it in Phase 0 with hand-written
   stoichiometry; `examples/competing_pathways.py` now does it from templates.
   * Five templates: Fischer esterification (reversible), ether condensation,
     alkene dehydration, aerobic oxidation, peroxide over-oxidation.
   * **Each parameter is labelled by how honest it is.** SMARTS = real. Ea =
     sourced, with its literature band. alpha = derived (Evans-Polanyi). Reverse
     rates = derived by detailed balance, never typed. **A = the remaining
     hand-authored parameter**, an order-of-magnitude choice, and the module says
     so: do not read a simulated reaction TIME as a prediction.

10. **The barrier ORDERING is the load-bearing chemistry, and it emerges.** Ethanol
    over sulfuric acid gives diethyl ether at ~140 C and ethylene at ~180 C,
    because the alkene route has the higher barrier (160 vs 125 kJ/mol, both from
    their literature bands). Measured: the **ether/ethylene ratio falls
    monotonically from 5660 at 340 K to 11 at 510 K** -- two orders of magnitude,
    with no selectivity table anywhere. Get the two barriers the wrong way round
    and the test fails while the yields still look perfectly plausible, which is
    why that test exists.

11. **THE PURITY CEILING IS BROKEN. Selectivity spans 100.00% -> 6.18%.** Ester
    3.59 mol at 340 K falling to 0.17 at 510 K as the alcohol is diverted. The
    clean case is clean now because the conditions are good, not because the model
    cannot express anything else.

12. **The oxidation had to be rewritten, and the balanced form is better
    chemistry.** The spike wrote `EtOH + 1/2 O2 -> AcH + H2O`; a graph rewrite
    cannot express half-stoichiometry and `build_network` refuses an unbalanced
    reaction. Written as `alcohol + O2 -> carbonyl + H2O2`, the peroxide is real,
    already curated -- and it then **over-oxidises the aldehyde to the acid**. So
    one air leak makes an aldehyde AND extra acetic acid, and that acid re-enters
    the esterification. **Measured: acetic acid RISES 1.44 -> 2.37 mol with the
    leak** even though it is a starting material being consumed. Three templates
    meeting; none mentions the others.

13. **Selectivity IS SMARTS specificity, now demonstrated rather than asserted.**
    `[CX4;!H0:1][OX2H1:2]` -- a carbinol carbon with a hydrogen to lose -- is the
    entire selectivity model for the oxidation family: methanol -> formaldehyde,
    ethanol -> acetaldehyde, **isopropanol -> acetone unasked** (it never said how
    many hydrogens), **tert-butanol REFUSED** (none to lose), and **glycerol gives
    BOTH its primary and secondary products from one template**. Over-oxidation is
    restricted to `[CX3H1:1]=[OX1:2]`, so isopropanol under air stops cleanly at
    acetone while ethanol runs on to acetic acid. Nobody declared that difference.

14. **The explosion risk did not materialise, and understanding why is the useful
    part: 10 species, 6 reactions, under 0.01 s.** Network explosion comes from a
    template that REGENERATES its own matched group -- polyesterification reached
    80 species from ONE template because its ester bears another acid and another
    alcohol. These five terminate: an ether, an alkene and a ketone have no
    hydroxyl left to attack. **Adding templates is not what blows up a network;
    adding a self-feeding one is.** The bound is asserted in the tests so a future
    self-feeding template shows up as a jump in that number.

DONE (2026-08-17, last of the day): THE PREP'S YIELD IS HONEST END TO END.
451 tests pass, lint clean. The arc was five steps; three landed, one was killed
by its own measurement, and the fifth was not reached.

15. **B2 -- THE ADHERING CRYSTAL CRUST (`TransferLosses.crystal_size`), and it IS
    the yield.** Applied in `filter_into` and in `pour_into(phase="solid")`.
    **93.25% -> 83.64% at a 50 um crop, 77.91% at 80 um**, with the bench's ~80%
    landing at a ~70 um crop -- an ordinary recrystallised one.
    * MECHANISM: an adhering layer ONE PARTICLE DIAMETER thick over the surface
      the slurry wetted. Areal density = `crystal_size * packing_fraction` of
      solid, converted to moles by **the vessel's OWN Rackett molar volume** --
      so a denser solid leaves more mass behind, a mixed crop is left behind in
      the proportion it was present, and no species needs a parameter. 50 um at
      0.6 packing = a 30 um packed layer = 1.45 mL of crystals off a 1 L slurry.
    * SCALE: the SAME `V^(2/3)` wetted area film holdup uses -- they share
      `shape_factor`, because they rest on the same premise about geometrically
      similar glassware. Measured 0.2150x / 0.2144x / 0.2131x per decade against
      a predicted 0.2154x. **This IS the "small fraction plus an absolute floor"
      the brief asked for, except the floor is not a second parameter -- it is
      the geometry.** Yield across four decades of scale: 88.77 / 83.64 / 72.65 /
      49.35%. A tenth-scale prep is punished and nothing told it to be.
    * COUNTERMEASURE: rinse it through and re-filter, free again because the
      crystals stay in the vessel they failed to leave. **And the rinse liquid is
      a real decision**: fresh solvent recovers them but dissolves some, the
      MOTHER LIQUOR is already saturated and dissolves none. Nothing scripts
      that; it is the solubility law, and it is asserted in `test_solid_losses.py`.
    * Kept distinct from `passthrough` (fines *through* the paper -- a filter
      defect, cured by a better filter) and from the film. Merging any two would
      make a low yield unattributable. `FiltrationResult.retained_solid` is a new
      field and `recovered` counts all three fates.
    * **Closure stays 100.0000% with both losses on, at every scale**, for the
      same reason as film holdup: the operation only ever FAILS TO MOVE material.
      `losses=None` is still exactly lossless, and `crystal_size=0` isolates the
      film from the crust.
    * ⚠ The one prediction not to lean on: the model says a COARSER crop leaves
      more mass per unit area. That is a monolayer argument, and real fine powders
      coat more completely and adhere in multilayers. `crystal_size` is a
      calibration with a band, not a lever, and the module says so.

16. **THE PREP HAS A COMPETING PATHWAY, and the route makes its own contaminant.**
    `examples/multistep_prep.py` now runs on four library templates plus the
    dissociation set. Saponification liberates ETHANOL; headspace O2 oxidises it
    to acetaldehyde + H2O2; the peroxide over-oxidises that to acetic acid; the
    acid re-esterifies. **Open flask, 2 h at 80 C: 6.7 mmol acetic acid,
    0.17 mmol ethyl acetate, 0.11 mmol each of acetaldehyde and peroxide.**
    Sealed, all of it goes to zero. Nobody charged any of it.
    * The oxygen budget is the headspace, so "stopper it" is a real lever and
      four times the cook time gives nowhere near four times the acid. Asserted
      in `tests/test_prep_side_products.py`.
    * Network still bounded: **18 species, 15 reactions, 0.04 s**. Still no
      self-feeding template.
    * ⚠ **AND THE WASHED PURITY BARELY MOVES.** Every product of that cascade is
      small, polar and water-soluble, so washing removes it exactly as it removes
      the salts. Necessary but not sufficient -- a one-template network's purity
      was true by construction, and now it is merely *washable*.

17. ⚠ **B3 (CRYSTAL OCCLUSION) WAS MEASURED BEFORE BEING BUILT, AND THE
    ARITHMETIC KILLED IT. It is NOT built, and the state-vector change it needs
    was NOT spent.** The bound is computed from the simulated liquor in
    `validation/process_losses.py`, not assumed:

        crop           0.1865 mol = 22.77 g = 18.90 mL of crystal
        mother liquor  1021 mL carrying 44.8 g/L of dissolved NON-WATER
                       -- i.e. the liquor is only 4.5% dry solids by mass

    So an occluded volume fraction phi carries `phi * 18.9 mL * 44.8 g/L` of DRY
    impurity: at a realistic phi = 0.01-0.05 that is 0.008-0.042 g on a 22.8 g
    crop, a purity ceiling of **99.96%-99.81%**. Reaching the bench's 97.5% needs
    **phi = 0.69** -- 13 mL of liquor inside 18.9 mL of crystal. That is not a
    crystal with inclusions, it is a slush.
    * **Two small numbers multiplied cannot make a big one**: a few percent of
      crystal volume times a few percent dry solids. And a dried crop's purity
      does not count water, which is 95.5% of what is trapped.
    * This is the same shape of finding as film holdup's, obtained an order of
      magnitude more cheaply. **The general lesson, now paid for twice: bound a
      mechanism arithmetically against the actual simulated state BEFORE writing
      the code.**
    * Where occlusion WOULD earn its cost: a liquor whose impurity is concentrated
      and non-volatile -- a recrystallisation carrying a coloured organic
      byproduct, tens of percent dry solids rather than 4.5%.

18. **WHICH MECHANISM ACCOUNTS FOR WHAT, which was the point of the arc:**

        yield 93.25% -> ~80%     THE CRUST, essentially all of it. Film holdup
                                 contributes 0.00 points on this route because it
                                 only ever acts on waste streams (reproduced).
        purity ~100% -> 97-98%   NOT ACCOUNTED FOR -- and now known not to be a
                                 loss parameter, by the bound above.

    ⚠ **THE REMAINING PURITY GAP IS A NAMED TEMPLATE-LIBRARY GAP: nothing in the
    library makes a BENZOYL side product.** Everything it produces from this
    route attacks the ethanol, so every impurity is small, polar and washable.
    What a bench crop of benzoic acid actually carries is something that
    CO-CRYSTALLISES with it -- an aromatic of similar solubility. **That is a
    template to write, not a fraction to tune**, and it is exactly the trap the
    brief warned about: if a purity number looks wrong, ask what side reactions
    the network is missing before reaching for a loss parameter.

    NOT REACHED: step 5, explicit acid catalysis in `reactions/library.py`.

DONE (2026-08-17, later still): LIQUID-LIQUID EQUILIBRIUM, and the structural gap
that gated a user interface. Lint clean. `validation/liquid_liquid.py` is the new
harness; `examples/extraction.py` is the new demo and is driven ENTIRELY by events.

19. **THE STATE VECTOR GREW A FOURTH BLOCK: `y = [nL1 | nL2 | nG | nS | T]`,
    4n+1.** Everything that touches a liquid now happens twice -- reactions run
    in both layers, both evaporate into the shared headspace, a solid dissolves
    into both -- and a species crosses between them until its ACTIVITY is equal
    on the two sides, which is the same equality the vapour and the solid
    already used.
    * ⚠ **With the second block empty the RHS reduces EXACTLY, term by term**:
      `wet2` is zero, layer 2's volume is below `V_LIQUID_MIN` so no reaction
      runs in it, its dissolution pool is zero, and the liquid-liquid flux
      carries the product of both wet factors. **Verified bit-identical against
      `lle=False` on a full boil-dry-and-superheat trajectory.** That is what
      lets every number this project has measured survive a state-vector change,
      and it means a moved invariant is a real phase split and never an
      accounting artefact.
    * The LLE flux is ANTISYMMETRIC (so conservation is untouched) and
      SELF-LIMITING at zero: a species absent from layer 2 has `a2 = 0`, so the
      flux can only be *into* layer 2. Neither layer can be driven negative,
      which is the property the evaporation term already had.

20. **`numerics/lle.py` -- the one decision that could not be a rate.** The
    equilibrium condition `gamma_i(x^I) x_i^I == gamma_i(x^II) x_i^II` has the
    same shape as every other equilibrium here, **and it is also satisfied by the
    two phases being IDENTICAL.** A single phase is a fixed point of its own
    splitting dynamics, so no amount of integrating will leave it; deciding
    whether that fixed point is a minimum or a saddle is a GLOBAL question about
    the Gibbs surface. So: Michelsen's tangent-plane test at EVENT BOUNDARIES
    (the METER precedent), smooth relaxation in the RHS.
    * Splitting is decided on the way IN to an integration and merging on the way
      OUT, deliberately: a split costs a tangent-plane iteration and is worth
      doing once per call, a merge is a comparison of two compositions and is
      worth doing the moment it is true. Without the merge, a system made
      miscible mid-run carries a phantom layer that a separatory funnel drains.
    * It does not FLASH. It reports "unstable, and here is a better composition",
      the caller seeds 1% of the liquid there, and the ODE finds the tie line --
      which also makes mass transfer between layers a RATE, as it is in practice.

21. **What it gets right, measured in `validation/liquid_liquid.py`:**
    * **13/14 miscibility pairs correct** from the sign of a tangent-plane
      distance alone -- water/ethanol, /acetone, /methanol, /THF mix;
      water/benzene, /toluene, /hexane, /DCM, /ether, /octanol split;
      benzene/toluene, hexane/toluene, ethanol/hexane mix.
    * **Layer densities within 0.7%** (toluene 0.861 vs 0.867, chloroform 1.480
      vs 1.489) and **every layer on the correct side**, from molar masses and
      the Rackett molar volume the RHS already integrates. So
      `pour_into(phase="lower")` means the aqueous layer with toluene and the
      ORGANIC one with dichloromethane, with nothing relabelled.
    * **STEAM DISTILLATION EMERGES: water + toluene co-distils at 358.3 K
      against a measured 357.3, and water + benzene at 345.5 against 342.4** --
      both below either component. Nothing was told what a co-distillation is;
      it is two layers driving one headspace.
    * **Extraction: 1 x 85 mL recovers 92.4%, 3 x 28 mL recovers 99.2%**, and
      the curve tracks the n-stage formula it was never given.
    * Solvent choice is a real lever with emergent consequences: K(org/aq) is
      2.7 for hexane, 12.0 toluene, 56.3 ether, 65.5 DCM -- and DCM's layer is
      on the bottom.

22. ⚠ **AN ELECTROLYTE IS REFUSED, NOT APPROXIMATED**, and it is the same
    judgement the atmosphere exchange makes about a room the network cannot
    represent. Ions have no activity model (UNIFAC is non-electrolyte), so they
    sit at gamma = 1. Inside one liquid that is a bounded error. Across an
    interface it is not: equality of activity with gamma = 1 on both sides means
    an ion partitions to **equal mole fraction** between water and toluene, where
    the Born energy puts the real coefficient past 1e7 -- so a split would invent
    a strongly ionic organic phase and run aqueous-anchored dissociation inside
    it. Above an ionic mole fraction of 1e-6 the split is refused and
    `Vessel.lle_report()` says exactly why.
    * **This is what saved the benzoic-acid prep.** It genuinely wants to split
      (ethyl benzoate is barely water-soluble), and letting it produced 0.19 mol
      of hydroxide coexisting with 0.085 mol of free benzoic acid in different
      layers, plus protons in the organic phase. Held as one phase, every
      previous number returns exactly.
    * ⚠ **THE CONSEQUENCE IS SPECIFIC: an acidified aqueous workup -- the most
      common workup there is -- cannot be two layers until this project has an
      electrolyte activity model.** That is now the highest-value item in the
      properties layer, ahead of everything else on the list.

23. ⚠ **THE HEADLINE ACCURACY LIMIT: our UNIFAC parameters are the VLE-regressed
    set.** Fredenslund's group published a separate UNIFAC-LLE table precisely
    because the VLE set underpredicts miscibility gaps. The one miss above
    (water/n-butanol reads miscible; it is ~7 wt%) is that, and so is hexane
    reading far more water-soluble than it is. **It errs toward MISCIBILITY,
    which is the safe direction** -- it fails to separate rather than separating
    something it should not. The fix is a parameter table, not a change of model.

24. ⚠ **`k_lle` IS NOT A CLEAN "HOW HARD DID YOU SHAKE IT" KNOB, and the module
    says so.** One coefficient carries both the separation of the bulk layers
    (gravity, fast) and the equilibration of a solute across them (interfacial
    area, what shaking is for). Turning it down far enough does not model a
    badly-shaken funnel, it models two liquids that never separated -- which is
    not a state a bench produces. Splitting them needs a settling model
    (drop size, coalescence) this project does not have, so the knob is not
    offered as one.

25. ⚠ **THREE NUMERICAL TRAPS AN EMPTY SECOND LAYER CREATES.** These cost more
    of the session than the physics did, and the first two are exact opposites --
    which is the lesson.
    * **An empty layer sits at the knee of `N/(N+eps)`, whose slope there is
      1/eps.** Differencing the Jacobian across it gave entries of **4e6 to 1.4e8
      for a layer holding NOTHING**, against 61 for the real one. Cost: a **10x
      slowdown of the whole suite** and reflux failing outright. Fixed with a
      SMOOTHSTEP (`LAYER_EPS`), zero *and flat* at zero. This project had already
      paid for a non-smooth switch twice (`DRYOUT_MOLES`, `MELT_BLEND`) -- but
      those needed continuity and this one needed a continuous DERIVATIVE.
    * **...and a perfectly flat column is just as bad.** `num_jac` finds every
      finite difference in it below its "too small" threshold, inflates that
      column's perturbation factor on every call without bound, overflows to inf
      and hands BDF a NaN Jacobian: `RuntimeError: Factor is exactly singular`.
      **That is the SAME pathology already documented for a vessel at rest**,
      arriving by a new route. Fixed with `LAYER_REABSORB` -- material below the
      phase scale flows back into layer 1, which is the continuous form of the
      discrete merge AND puts an honest small `-k` on the diagonal.
    * **...and then those two fixes FOUGHT EACH OTHER.** The liquid-liquid flux
      pumped material into a layer too small to be one while the reabsorption
      pushed it back, and the balance point sat exactly where `a2` is steepest
      in `N2`. **The benzoic-acid acidification became unsolvable** -- and the
      signature was diagnostic: turning off EITHER term alone fixed it, which is
      what two opposed terms look like rather than one bad one. Fixed by making
      the gates strictly DISJOINT (`_layer_gates`): `drain` acts only below
      `LAYER_EPS`, `grow` only above it, both C1 and flat where they meet. Their
      thresholds must match the MERGE floor too -- a layer between
      `DRYOUT_MOLES` and `LAYER_EPS` survived the merge AND sat in the
      transition band.
      **General rule: a state block that can sit at exactly zero needs a
      derivative there that is neither enormous nor exactly zero -- and only ONE
      term may govern it near zero.**
    * ⚠ **`Vessel.run` was SWALLOWING a failed solve.** `sol.y[:, -1]` is the
      last point the solver reached, so a run that gave up after 4 s of a 3600 s
      interval returned quietly with a plausible-looking state -- the prep
      reported 0% yield with the pot still at 353 K and no error anywhere.
      `step` had always checked; `run` never did. It raises now, and that is how
      the fight above was found at all.
    * ⚠ **THE TANGENT-PLANE TEST CANNOT TELL A SECOND LIQUID FROM A CRYSTAL.** It
      compares liquid Gibbs energies, so a solution holding more of a
      sparingly-soluble solid than it can dissolve is correctly reported
      unstable -- **but the resolution is CRYSTALLISATION, not a second layer**.
      Benzoic acid in cold water found it: the test proposed a "liquid" 99%
      benzoic acid at 275 K, twenty degrees below its melting point, and a
      fictitious layer then fought the real solid phase over the same material.
      **One test took 2043 seconds**; after the fix its whole file runs in 107 s
      and `test_lle.py` went 220 s -> 14 s. `lle._is_a_liquid` rejects a trial
      supersaturated in any crystallising species, using the same `a_sat` the
      dissolution term already uses. Conservative: a genuinely liquid
      solid-former near its melting point (phenol/water) is marginal and may be
      refused -- erring toward miscibility, as everything else here does.

26. **THE STRUCTURAL GAP CLOSED: the replayable path and the honest path were
    disjoint sets.** Events were always the only thing that could mutate a
    vessel, and a run was always a pure function of (scenario, event list) -- but
    **no real prep went through it**, because the things that make a prep honest
    were unreachable from a `VesselSpec`. A user interface is nothing but an
    event producer, so it could only have driven the half that was not honest.
    * `VesselSpec` now carries `drain_time`/`kinematic_viscosity`/`crystal_size`/
      `packing_fraction` (transfer losses), `k_lle` and `lle`. Losses used to be
      constructible only by calling `Vessel` directly.
    * `Scenario.electrolyte` -- without it a scenario could not price an ion, so
      no pH, no acidified workup, no salting anything out. The entire aqueous
      half of preparative chemistry was unreachable from the replayable path.
    * **`TemplateSpec` was silently dropping `alpha`**, so a saved run came back
      with every homologue in a family on the same barrier and diverged from the
      original for no visible reason. Fixed.
    * Two new verbs: `SET_SHAKING` (distinct from stirring -- a flask can be
      stirred hard under a condenser without two layers ever meeting) and
      `FILL_HEADSPACE` (a verb rather than a CHARGE because "open it to the
      room" means different moles once there is liquid in it; takes a
      composition, so an inert atmosphere is one payload away).
    * `TRANSFER` needed nothing: it already took a `phase`, so `phase="lower"`
      is a separatory funnel for free.
    * **SAVE_VERSION 3.** The second liquid layer is saved as its own block
      rather than re-derived, so a reload cannot depend on the stability test
      agreeing with itself and a funnel never comes back remixed.
    * `tests/test_protocol.py` pins the join: an extraction run as events and as
      direct calls agrees to 1e-9, and a run continued from a mid-extraction save
      matches one that never stopped **exactly**.

DONE (2026-08-18): ION TRANSFER BETWEEN PHASES, and the second half of the same
problem that nobody had foreseen. 499 tests pass, lint clean.
`validation/ion_partition.py` is the new harness; `tests/test_born.py` and
`tests/test_catalysis.py` are the new test files.

27. **THE FRAMING FIRST, because the brief for this session conflated two things
    and the distinction is load-bearing.** There are TWO ionic gaps:
      (a) ionic strength WITHIN one phase -- Debye-Huckel/Davies, which is what
          salting-out is. STILL ABSENT, deliberately, and see item 32;
      (b) ion transfer BETWEEN phases -- BORN,
          `dG ∝ (z²/r)(1/eps_org − 1/eps_water)`. **Only (b) lifts the refusal**,
          and it is what was built.
    Conflating them wastes the work: Debye-Huckel would not have unblocked a
    single workup.

28. **`properties/dielectric.py` + `dielectric_data.py`.** Two curated inputs, both
    with provenance per value, both in the shape this project already uses.
    * **Permittivity per liquid from the CRC compilation** in `chemicals` 1.5.2, 62
      of 65 candidates, and it arrives as `eps(T) = a + bT + cT² + dT³` -- which is
      bit-for-bit the polynomial basis `_poly` already evaluates for molar volume
      and Cp. **Nothing was fitted or refitted.** Each entry carries its own
      validity window and T is clamped to it: toluene's is quoted over 207-316 K
      and a cubic run far past its data goes negative, which would flip the sign of
      an ion's transfer energy. A third of the table is a single measurement with
      no correlation (acetaldehyde), stored as a CONSTANT and stamped `single
      point`, because a constant permittivity is wrong in a KNOWN direction and
      saying so is cheaper than inventing a slope.
    * **Ionic radius in two tiers**: Shannon (1976) six-coordinate radii for the
      monatomic set plus hydroxide, and otherwise the sphere of equal additive van
      der Waals volume from element radii. ⚠ **The curated table is small on
      purpose.** There is no ionic-radius table in `chemicals` or in anything else
      this project depends on, so every curated value is hand-entered -- and the
      rule here is that a value with no auditable source does not get written down.
      Benzoate, acetate and sulfate fall to the derived tier rather than acquiring
      a number of uncertain provenance.
    * `z` comes off the MOLECULAR GRAPH, so sulfate is four times as strongly held
      as chloride with no new datum at all.

29. **What it collapses to, which is the project's standard question: an (n, 4)
    block that is a function of TEMPERATURE ALONE** --
    `[A | eps_pure(T) | v_mol(T) | eps_water(T)]`, assembled once per RHS call by
    `PhaseArrays.born_block` and shared by both liquid layers and by every
    tangent-plane trial. A Born term cannot collapse *outright* like Antoine,
    because `eps_phase` is a MIXTURE property, so the mixing rule is what stays in
    the hot loop -- three array operations. `None` when the network has no ions,
    which is what keeps a non-electrolyte vessel bit-identical.
    * The mixing rule is **Oster's (1946)**, Onsager applied to a mixture, over
      VOLUME fractions. Its inverse is a quadratic and so closed-form, which
      matters: an iterative solve here would be finite-differenced by `num_jac` on
      every Jacobian column.
    * It is the same UNSYMMETRIC CONVENTION the Henry solutes use -- `ln_gamma_ref`
      divides gamma by its value at a reference state -- and that is exactly why
      the pH trap did not bite.

30. ⚠ **THE PH TRAP, AND WHY IT DID NOT BITE -- but "exactly" took two fixes.**
    Every ion here is priced from a measured AQUEOUS pKa at gamma = 1, so
    introducing gamma for ions would normally mean RE-DERIVING every anchor. It
    does not, because the term is a TRANSFER referenced to water and is identically
    zero there. **Measured, not argued: all five pH values come back with a delta
    of exactly 0.00e+00.** Getting *exactly* rather than *nearly* needed:
    * the REFERENCE permittivity put through the mixing rule as well, because
      water's value straight off the polynomial and a mixture value through Oster's
      inversion differ in their last few bits -- nothing as a permittivity, and the
      entire claim as a cancellation;
    * and the mixing rule NORMALISING before contracting, because `x/x` is exactly
      1.0 in IEEE arithmetic while `(w·f)/w` is only `f` to within rounding.

31. ⚠ **AN UNCLIPPED BORN TERM RETURNS A SILENT WRONG ANSWER, one projection away,
    and this is the session's sharpest lesson.** Sodium into toluene is ln gamma
    112, i.e. gamma 5e21, which in a flux of the form `k(a1 − a2)` gives that block
    a Jacobian diagonal of −7.5e22 and a relaxation timescale of 1e-23 s for a
    quantity whose equilibrium value is 1e-24 mol. **BDF did not fail. It reported
    SUCCESS** and returned chloride at +3.07e9 mol in one layer and −3.07e9 in the
    other -- a cancelling dipole fourteen orders of magnitude larger than the
    material present -- and `project_non_negative` then tidied it into a
    plausible-looking state.
    * `LN_GAMMA_BORN_MAX = 12` is therefore a RESOLUTION limit and is argued for
      in the code and SWEPT over four decades in the harness. The binding
      constraint is not the chemistry: it is that the equilibrium amount stay
      ABOVE the solver's own 1e-9 atol so the quantity is integrated rather than
      lost in round-off. At 12 the partition coefficient is 6e-6 -- a part per
      million, invisible in any assay -- and the equilibrium amount is a
      micromole. At 18 it lands ON the tolerance, at 30 it costs 4x the solver
      work, at 50 it breaks.
    * Every ion reported at the ceiling is NAMED as such by
      `Vessel.electrolyte_report`, with the value it was cut from, so a capped
      number can never be mistaken for a computed one. Same precedent as
      `detailed_balance`'s reverse-barrier floor: correct what cannot be
      integrated, keep the equilibrium that matters, and flag it.

32. ⚠ **AN AQUEOUS pKa DOES NOT APPLY IN AN OIL -- the half nobody had foreseen,
    and the old refusal had been hiding it too.** Getting the ions to stay in the
    water does nothing about the reactions that MAKE ions: every pKa here is
    anchored to water, so run unchanged inside an organic layer it leaves benzoic
    acid as dissociated in toluene as in water, which is the exact opposite of what
    an acid/base extraction relies on. It is also what made the two-phase
    saponification unsolvable -- the aqueous recombination rate constant acting on
    an ion pool it had no business creating.
    * Fixed in `_phase_rates` by the activity-basis correction over the ions a
      reaction MAKES, `K_c = K_a / Π gamma^nu`, placed ENTIRELY on the direction
      that CREATES them. That placement is Bronsted-Bjerrum with the transition
      state taken as ionic as the products -- conventional for a heterolysis -- and
      it is also the only placement that is numerically survivable: put it on the
      reverse and the recombination constant is multiplied by e^24 while the ion
      pool is unchanged, giving the same equilibrium, a Jacobian entry of 1e27 and
      an unsolvable flask. On the forward direction the disfavoured species is
      simply never made, so the fast mode has nothing to act on.
    * **In water the factor is exp(0) = 1.0 exactly**, which is the whole reason
      this was safe: it carries the BORN term only, never a UNIFAC gamma. Measured
      Ka factor: 1.000 in water, 0.203 in 90:10 water/toluene, 3.8e-11 in toluene.
    * It needed NO new Layer 3 array -- the product side is `max(delta, 0)` and the
      charge is a mask Layer 5 already supplied.
    * ⚠ **A wide-reaching consequence, and it is real chemistry**: acetic acid in a
      NEAT acid/alcohol mixture (permittivity ~12) is roughly a million times less
      dissociated than in water, so its own autocatalysis all but stops. That is
      why a bench Fischer esterification uses added sulfuric acid -- glacial acetic
      acid is a poor conductor -- and it is why `test_catalysis` demonstrates the
      catalysed route in an aqueous system.
    * **Debye-Huckel would still change nothing measurable**, and now for a
      sharper reason: an ion's gamma reaches only phase equilibria and this
      correction, and both are dominated by a factor of e^12. Salting-out needs the
      activity basis for NEUTRAL species first.

33. ⚠ **"NO MEASURED VALUE" AND "NOT PART OF THE MEDIUM" ARE DIFFERENT CLAIMS**,
    and conflating them was a real bug with a real symptom.
    * An unpriced NEUTRAL is medium of unknown polarity and contributes
      `f(eps) = 0`. That is a BOUND, not a guess: `f` is monotone with `f(1) = 0`,
      so it returns the LOWEST permittivity the layer could have, and erring low
      errs toward the ion staying in the water.
    * An ION is not medium at all and is excluded entirely. Left in, a molar brine
      reads eps 75 instead of 78 -- and with the WRONG SIGN for the
      low-concentration behaviour Debye-Huckel describes, since it would have ion
      activity rising where Debye-Huckel has it falling. The dielectric decrement a
      real salt causes belongs with (a), not here.
    * **Benzoic acid settled it.** It is a solid with no measured liquid
      permittivity in any source here, and as the prep's organic layer filled with
      it, renormalising over the priced remainder read that layer's polarity off
      the 32% that was water and ethanol, called it eps = 50, and let the ions in.
      The bound reads eps = 15 and keeps them out.

34. **THE REFUSAL NARROWED RATHER THAN VANISHING.** `IONIC_SPLIT_LIMIT` is a
    threshold for when the ion model has to be CHECKED, not a refusal. What can
    still refuse: an ion whose Born coefficient cannot be resolved (no radius, no
    transfer energy, so it would move freely) -- per species, and named. Layer
    permittivity COVERAGE is reported rather than refused, because the `f = 0`
    bound already errs safe. Nothing in ordinary chemistry hits either.

35. **THE PREP: measured, and it did NOT move -- for an identifiable reason.**
    Yield 83.6%, purity 100.0%, **closure 100.0001%** (it was 100.0010% -- the
    drift the last handoff flagged has gone back to its pre-liquid-liquid value),
    side products 6.675 mmol acetic acid. Every number preserved.
    * **And the pot genuinely goes two-phase and back**: it splits into a layer
      99.4% ethyl benzoate (tangent-plane distance −9.83), the ester hydrolyses,
      and the layers merge once it is gone.
    * ⚠ **The brief expected SLOWER hydrolysis and that is not what happens**, and
      the reason is `k_lle`: at 5 mol/s a 30 mL organic layer empties in 40 ms, so
      the reaction is not transfer-limited on a two-hour timescale at all.
      Measured insensitive over a decade (0.5 and 0.05 mol/s give the same
      benzoate to five decimal places), which is what makes it reportable rather
      than a fudge. **`k_lle` is what decides whether a two-phase reaction is
      transfer-limited, and its default is far too fast for the question to be
      asked.**
    * ⚠ **The pot is run at `k_lle = 0.5` rather than the default 5.0, and at the
      default it does not integrate.** Said plainly in the example.

36. ⚠ **THE ACIDIFICATION IS 3.2x SLOWER, and the fix is named but deliberately
    NOT SHIPPED.** Measured on a 10 s step: 33.0 s with everything on, 15.5 s with
    the ionic rate correction off, 10.4 s with Born off entirely, and 33.2 s with
    `lle=False` -- so it is not the phase split, the crop is 0.0261 mol in every
    row, and 2.1x of it is the rate correction making every rate constant a
    function of the layer's permittivity and therefore of every liquid amount.
    That turns a sparse Jacobian coupling into an all-to-all one.
    * **The fix is to freeze the layer permittivity at the integration boundary**,
      which is the bargain this project already accepts twice (the METER edge's
      rate, and the phase decision itself). Not shipped because it arrived with no
      time to re-validate a full suite -- the same call that kept
      `LAYER_REABSORB = 0.1` out. It is item 1 of NEXT_SESSION.md.
    * **THE SUITE IS 29 MIN, AGAINST ~20 BEFORE**, and the previous brief had asked
      for that to come DOWN. About 2.5 min of the increase is genuinely new tests
      (`test_catalysis`, `test_born`) and the rest is the prep tests carrying the
      3.2x. ⚠ **The rig tests are still 75% of the suite and are untouched by any of
      this** -- they carry no ions, so the two levers named last time
      (`LAYER_REABSORB = 0.1`, and the rig's `jac_sparsity` marking each vessel's
      whole block dense) are STILL the levers and are still unmeasured. That part of
      the brief was not delivered.

36b. **AND A REFRAMING OF THE WHOLE PERFORMANCE QUESTION:
    `validation/wall_clock.py`.** Wall-clock cost is NOT proportional to simulated
    duration -- an idle flask does an hour in 0.00 s (no solver at all), a boiling
    plateau does 1200 s in 0.73 s, a two-hour two-phase saponification does 7200 s
    in 27 s, and **ten seconds of the acid quench costs 40 s -- 4.1x SLOWER than
    real time, and eight times what four hours of crystal growth costs.**
    * ⚠ **THE EXPENSIVE MOMENTS ARE EXACTLY THE ONES A PLAYER IS WATCHING**, so a
      frontend cannot assume a short action is a cheap one: it has to show an
      operation IN PROGRESS rather than block on it. The engine is already stepped
      rather than run, so that is a frontend concern.
    * And **"wait until" is a responsiveness feature as much as an expressiveness
      one** -- 497 s of wall time went on the *remainder* of the quench hour, almost
      all of which resolves nothing.

37. **EXPLICIT ACID CATALYSIS, and the honest part was not the mechanism.** The
    mechanism needed NO engine work, exactly as the audit predicted: a species on
    BOTH sides of a reaction SMARTS already gets `order += 1` as a reactant and
    cancels out of `delta`, so it has rate-law exponent 1 and net stoichiometry 0.
    * The honest part was `CATALYST_REFERENCE = 0.1` mol/L -- **the catalyst
      concentration the apparent pre-exponentials had been standing in for, now
      declared.** So the catalysed and folded forms are the SAME RATE at that
      loading (asserted), and away from it "add more acid" is a real lever with the
      right first-order slope. Without declaring it, making the catalysis explicit
      would silently have slowed every esterification in the project tenfold.
    * ⚠ **The REVERSE is catalysed too and must be** -- detailed balance gives it
      the same exponent so the catalyst cancels out of K exactly, which is the
      definition of a catalyst. Forward-only would have made "add acid" move the
      equilibrium, and the error would have looked like a plausible rate effect.
    * ⚠ **A catalysed template in a network with no catalyst is INERT**, and
      `build_network` cannot warn: "matched nothing" is indistinguishable from a
      template that legitimately does not apply. So `catalyst` is opt-in per
      template and `alcohol_chemistry()` is untouched.
    * Still missing: the UNcatalysed pathway alongside the catalysed one. `Ea` is
      still the *catalysed* apparent barrier, so an uncatalysed flask is dead
      rather than slow. That needs a second literature band -- a data job.

38. **THE BENZOYL SIDE PRODUCT: TWO OF THREE CANDIDATES KILLED BY ARITHMETIC,
    before a template was written.** New panel in `validation/process_losses.py`.
    A candidate is only a purity mechanic if it CO-CRYSTALLISES, i.e. if the route
    can make more of it than 1 L of cold liquor holds; the peroxide budget bounds
    that at ~7 mmol.
    * **perbenzoic acid -- 0.30 mol/L at 275 K, forty times too soluble. DO NOT
      BUILD IT.** It was the obvious reach (the route already makes hydrogen
      peroxide from its own liberated ethanol, and `R-COOH + H2O2` is the real
      named equilibrium behind peracetic acid manufacture) and it would have
      washed out exactly as the acetic acid does.
    * peracetic acid is miscible -- the useful contrast: one template on two
      substrates, and only the aromatic product could ever have been a problem.
    * benzoic anhydride is REFUSED outright: Joback cannot fragment it.
    * **benzoyl peroxide works decisively -- 10 umol/L, gamma in water 1.5e5**, so
      anything above ten micromoles crops with the product and cannot be washed
      off it. But the route must reach it through TWO successive condensations,
      both unfavourable in water. ⚠ **Being unfavourable is not an objection here,
      it is the mechanism**: the threshold is a trace, so the impurity only has to
      be a trace. That is the OPPOSITE of the occlusion case, where two small
      numbers multiplied could not make a big one.
    * Same discipline as occlusion, an order of magnitude cheaper than building it:
      bound the mechanism against the actual simulated state FIRST.

DONE (2026-08-18, later): THE ENGINE IS READY FOR AN INTERFACE. Four items, none of
them chemistry: the acidification regression, "WAIT UNTIL" as a solver root, a
systematic ROBUSTNESS pass, and three GUI-facing fixes. New harnesses:
`validation/permittivity_freeze.py`, `validation/wait_conditions.py`,
`validation/robustness.py`. New tests: `test_wait_until.py`, `test_robustness.py`.
New example: `examples/wait_until.py`. New module: `chemsim/recipes.py`.

39. **THE PERMITTIVITY IS FROZEN AT THE INTEGRATION BOUNDARY, and the bargain is
    measured rather than conceded.** `FREEZE_LAYER_PERMITTIVITY` in
    `numerics/vessel_integrator.py`; `make_rhs` now takes the boundary state and
    `RigIntegrator.make_rhs` threads it down per slice.
    * ⚠ **WHICH HALF IS FROZEN IS LOAD-BEARING.** The volume WEIGHTS Oster's rule
      contracts are frozen; the per-species permittivities are NOT, so `eps` still
      follows temperature. Freezing the resulting permittivity outright would leave
      a pure-water layer comparing `eps(T0)` against `eps_ref(T)`, and the Born
      term would stop being exactly zero in water -- which is the one thing every
      water-anchored pKa in this project rests on. With only the weights frozen a
      single-species layer still normalises to exactly 1.0 and the cancellation is
      still bit-exact at any temperature.
    * ⚠ **AN EMPTY LAYER IS LEFT LIVE rather than frozen at nothing.** A flask dry
      at the boundary that fills during the call -- a solid melting, vapour
      condensing into a cold receiver -- would otherwise carry weights summing to
      zero, which reads as "no medium" and would put its ions back at gamma = 1.
    * COST, and it is the documented price: the answer now depends on the caller's
      step size, because a layer whose polarity changes DURING a call does not
      notice until the next one. Same bargain the METER edge's rate and the phase
      decision itself already accept.

40. **"WAIT UNTIL", and the fork was the work.** `vessel/conditions.py` (Layer 5
    vocabulary), `VesselIntegrator.step_until` + `RootStop` (Layer 4),
    `Vessel.wait_until` + `WaitOutcome`, `World.wait_until` + `World.script` +
    `World.replay`. **SAVE_VERSION 4.**
    * ⚠ **THE FORK, DECIDED DELIBERATELY: the SCRIPT records the CONDITION and
      never the instant it resolved to.** A run used to be a pure function of
      (scenario, event list). Once a duration can be DISCOVERED that needs mending,
      and there were exactly two ways: record the discovered INSTANT (replay is
      exact, and the artifact is a TRANSCRIPT -- run it against a different charge
      and it waits the wrong number of seconds, which is precisely the failure that
      made fixed durations the wrong shape), or record the CONDITION (it stays a
      recipe, and replay is only as reproducible as the root solve).
      **The deciding argument is that this project already made the same call once**:
      a `Scenario` stores templates rather than the network they generate, because
      derived data stored beside its source is how the two drift apart. A
      discovered instant is derived data of exactly that kind. So a run is now a
      pure function of **(scenario, script)**, and the instant is REPORTED -- in
      `transfer_log` and in the vessel clocks -- as the outcome it is.
    * `script` records `step` intervals too, not only waits. Not redundancy: item
      39 made the caller's `dt` weakly load-bearing, so "how it was stepped" is
      part of the recipe now and pretending otherwise would be a silent
      approximation.
    * **THE SIGN CONVENTION IS THE CONTRACT: `f < 0` not yet, `f >= 0` satisfied**,
      upward crossings only. With a direction flag per condition there are two ways
      to write each one and one of them is silently backwards, and "is it already
      true?" stops being a single comparison.
    * Eleven conditions: `reaches` / `cools_to` / `temperature_steady` / `boils` /
      `crystals` / `dissolves` / `consumed` / `accumulates` / `acidic_to` /
      `basic_to` / `pressure_above`.
    * ⚠ **THREE OF THEM HAD TO BE WRITTEN DIFFERENTLY THAN THEY READ**, and
      `validation/wait_conditions.py` samples each candidate along a REAL trajectory
      before it was implemented -- the discipline that killed occlusion:
      - **a derivative approaching zero is NOT a root.** dT/dt gets to zero
        asymptotically, so `dT/dt == 0` waits forever. A TOLERANCE on it is a root,
        and "the thermometer has stopped moving" is what a chemist means anyway;
      - **an amount that starts at exactly zero needs a threshold ABOVE the
        solver's own atol.** nS LEAVES zero rather than crossing it, and at 1e-9
        the crossing is inside the tolerance. `SOLID_VISIBLE = 1e-6` is a
        RESOLUTION limit, three decades clear of atol and far below what a bench
        could see -- the same argument the Born ceiling rests on;
      - **a condition already true is not a root either**, because scipy locates
        sign changes. Checked before integrating and reported as `already`, so
        "wait until it is above 300 K" asked of a flask at 340 K returns at once
        instead of hanging.
    * ⚠ **AND A FOURTH, WHICH THE PROBE WAS TOO COARSE TO SEE AND A TEST CAUGHT: A
      RATE TOLERANCE FIRES ON THE FIRST TRANSIENT, NOT ON THE PLATEAU.** A flask
      whose headspace has just been filled with air evaporates hard for a moment,
      so its dT/dt starts at **-24 K/s**, crosses zero within one second, and only
      then climbs to the steady +0.096 K/s that carries it to the boil. Bare
      `temperature_steady(0.01)` therefore fires at 297.8 K and is right to. Pinned
      as behaviour, not filed as a bug: the fix is to name the regime first
      (`boils()`, then `temperature_steady()`), which is what a chemist does.
    * ⚠ **THE CLOCK MOVES BY WHAT HAPPENED.** A terminal event returns the state AT
      the event, so `sol.t[-1] < dt` and every clock above the solver must advance
      by `outcome.elapsed`. That is why `RootStop`/`WaitOutcome` exist rather than a
      bare state vector: `World.wait_until` runs the OWNING vessel first to learn
      the instant, then brings every other vessel to the same clock exactly (sound
      because vessels in a `World` are uncoupled -- coupling is what a `Rig` is
      for). Pending events still fire at their own instants inside a wait, and the
      wait resumes with what is left of its timeout.
    * The timeout is REQUIRED and has no default. A condition that never comes true
      is an ordinary thing to ask for by mistake, and an unbounded wait is a hang.

41. **A PRE-EXISTING CONFIDENT WRONG NUMBER, found by building `boils()`: DISSOLVED
    AIR MADE EVERY OPEN FLASK BOIL.** `is_boiling` and `bubble_point` summed ALL of
    `equilibrium_pressures`, which includes the Henry back-pressure of every
    dissolved gas -- and a liquid in equilibrium with air holds exactly enough N2
    and O2 to return that air's own partial pressures. So the sum reached ambient at
    **every** temperature: a 50/50 ethanol/water flask at 297.8 K reported
    `is_boiling = True` and a **bubble point of 297.82 K instead of 352.89**.
    * Fixed with `VesselIntegrator.volatile_pressure` -- CONDENSABLE species only.
      A dissolved gas at equilibrium exerts no net driving force and so cannot
      displace the atmosphere, which is what boiling is; a beaker of air-saturated
      water at room temperature is not boiling. (Effervescence -- a gas
      SUPERSATURATED against its headspace -- is real, is already in the RHS per
      species, and is not boiling.)
    * ⚠ **IT SURVIVED BECAUSE THE TESTS THAT USE THOSE READOUTS HAVE NO
      NON-CONDENSABLE IN THEIR NETWORKS.** With no dissolved gas the old expression
      and the new one agree exactly, which is now asserted in both directions.

42. **THE ROBUSTNESS PASS, and the rule is the deliverable: every state a player
    can reach must WORK or REFUSE CLEANLY WITH A REASON.** `validation/robustness.py`
    walks abusive setups and classifies each as OK / REFUSED / UNCLEAR / WRONG;
    `tests/test_robustness.py` (16 tests) pins the promises.
    * ⚠ **THE HARNESS WAS WRITTEN AND NOT RUN** -- the session ran out of budget.
      The guards and the tests are in and green; the sweep is not. One row is
      PREDICTED to come back WRONG (an overfilled flask clamps its gas volume to
      `V_GAS_MIN` and then inhales air into a microlitre headspace), and that
      prediction is deliberately left in the harness rather than pre-emptively
      fixed, because measuring before changing is the rule.
    * ⚠ **`sol.success` IS NECESSARY AND NOWHERE NEAR SUFFICIENT, and
      `check_raw_solution` is what says so.** Called on the solver's own final point
      BEFORE `project_non_negative` sees it, because the projection's whole job is
      to settle a cancelling pair -- so by the time anything downstream looks, a
      catastrophic dipole has become a plausible state. Wired into
      `VesselIntegrator.step`/`step_until`, `Vessel.run`, `Rig.run` and
      `RigIntegrator.step` (per vessel, since the rig projects across all of them at
      once and a straddling dipole would be gone).
    * ⚠ **AND THE BOUND MUST USE THE SIGNED TOTAL, WHICH IS THE BUG MY FIRST
      VERSION HAD.** Summing |value| per phase gives a dipole a bound twice its own
      size, so the check passed on exactly the case it exists for -- caught by the
      test that reproduces the 3.07e9 mol dipole. What the bound has to mean is "the
      amount of this species that EXISTS": `max(signed total, EXCURSION_FLOOR)`,
      with a 1e-3 mol floor for species legitimately at zero. Dimensional rather
      than tuned -- a round-off dipole is bounded by the solver's own tolerance
      (measured worst case 1.26e-6 mol) while a failed integration is off by orders
      of magnitude.
    * `check_state` REFUSES a non-finite state and a temperature outside
      `[T_MIN, T_MAX]`, before the stability test can evaluate activity
      coefficients on it.
    * `VesselIntegrator.diagnose` attaches plausible causes to every failed solve,
      most likely first, and every entry is a state this project has actually failed
      on rather than a guess -- two layers at a default `k_lle`, a layer in the
      `DRYOUT_MOLES..LAYER_EPS` band, a dry superheated flask, `kla=0` with an empty
      headspace, an absurd ionic fraction, solid with no solvent. A crash with no
      diagnosis is not a clean refusal.
    * ⚠ **THE SEALED FLASK IS A REPORTED FRAGILITY, NOT A REFUSAL, and getting that
      the wrong way round was the temptation.** `kla=0` with an empty headspace
      leaves the gas block identically zero AND flat, which `num_jac` cannot
      difference: it multiplies that column's perturbation factor by ten on EVERY
      Jacobian (scipy clamps the factor from below and not from above) until it
      overflows to inf. **But it is PER-SOLVE** -- each `run` builds a fresh BDF and
      the factor resets -- so it needs a few hundred Jacobians in ONE call, and
      **sixty-odd setups in this repo sit there quite happily.** Refusing them would
      have been as wrong as crashing. `Vessel.integrability_report()` names it and
      names the fix (a nitrogen blanket).

43. **THE THREE GUI-FACING FIXES.**
    * `Vessel.reset()` now clears `_holdup_moles`/`_holdup_volume`/`_crust_moles`/
      `_crust_volume`, `integrator.created`, and the stability verdict and refusal.
      None of it is in the state vector, which is exactly why emptying the four
      amount blocks looked complete -- and a player retrying an experiment was
      shown the PREVIOUS attempt's losses.
    * ⚠ **`retention` WAS THE WRONG SHAPE AND IS NOW `porosity`.** It retained a
      fraction of the LIQUOR where retention is a property of the CAKE: 5% of a
      1021 mL liquor left 50 mL on 17 mL of crystals, a cake three quarters liquor
      by volume. Worse, it scaled with the wrong quantity -- filter the same crop
      out of twice the solvent and the crude came out twice as dirty, where a real
      cake holds what its own voids hold. Now
      `porosity * V_solid / (1 - porosity)`, capped at the liquor present, computed
      with the vessel's own Rackett molar volume so a denser crop retains
      proportionally less. Default 0.4 (a well-pulled Buchner), and **the parameter
      was RENAMED rather than reinterpreted** so every call site had to be looked
      at; the `FILTER` event refuses a `retention` key loudly.
      - **RE-MEASURED, and it moved the number that mattered.** The prep now reports
        **84.0% yield at 99.6% purity with 100.0000% closure**, and the CRUDE cake as
        filtered is **97.5% pure against 80.5% before** -- because the cake now holds
        a few mL of mother liquor instead of 50. The yield barely moved (83.6 ->
        84.0), which is right: the crust is what sets it, and 0.0147 mol = 1.79 g =
        7.9% of the crop stays stuck to the pot.
      - ⚠ **AND THAT MAKES THE SIMULATION CLEANER THAN THE BENCH (99.6% against
        97-98%), which is a finding rather than a win.** The remaining discrepancy is
        the same NAMED template-library gap: nothing in the library makes a benzoyl
        side product, so every impurity this route produces is small, polar and
        washable. Still a template to write rather than a fraction to tune -- and the
        occlusion arithmetic should be redone against the new liquor volume before
        anyone reaches for that again.
    * **`chemsim/recipes.py` -- ONE HOME FOR THE PREP.** It existed in three copies
      (`examples/multistep_prep.py`, `validation/process_losses.py`,
      `tests/test_prep_side_products.py`) whose conditions had to be kept in step by
      hand, and one of those conditions is counter-intuitive and load-bearing
      (`k_lle = 0.5`, not the default 5.0, or it does not integrate). All three now
      import `BENZOIC_ACID_PREP`. It holds numbers and hands back a `Vessel`; the
      three readers keep their own narratives and assertions, which are genuinely
      different jobs.

44. ⚠ **THE RIG'S `jac_sparsity` WAS COSTING 10x, NOT SAVING ANYTHING -- the
    lever was real and pointed the other way.** `test_rig.py` was 75% of a 29-minute
    suite; it now runs in **113 s, all 20 tests passing**. The azeotrope boiling-point
    test went **673 s -> 39 s**, reflux **243 s -> 18 s**, distillation[0.95]
    **139 s -> 38 s**. Cleanly attributed: those rigs carry no ions, so the frozen
    permittivity is inert in them and this is the sparsity change alone.
    * `jac_sparsity` buys exactly one thing -- column GROUPS in `num_jac`, which
      perturbs together any columns sharing no non-zero row. Measured with the same
      `group_columns` BDF's sparse path uses, the old pattern (each connected pair's
      WHOLE off-diagonal block) gave **162 groups out of 162 columns** on a
      two-vessel twenty-species rig and **324 of 324** on a four-vessel one. So it
      was doing the dense number of RHS evaluations per Jacobian **and** paying
      sparse `num_jac` and a sparse LU of a 29%-dense matrix on top. That factor of
      ten is the sparse LU.
    * **The culprit was not the empty second liquid layer, which is what the brief
      expected.** Nor the diagonal blocks -- those are honestly dense, since
      perturbing any amount moves the liquid volume, hence the gas volume, hence
      every partial pressure, hence every row. **It was the TEMPERATURE ROW**:
      marking vessel a's `dT` against the whole of vessel b's block means every
      column of b touches a's T row, so nothing can group whatever else is marked.
    * The pattern is now per edge kind, read off what each branch of the RHS writes
      (THERMAL: two T rows. VAPOUR: the donor's whole block, but only against the
      receiver's GAS rows and T row, because a pressure divides by the gas VOLUME.
      DRAIN/METER: the donor's two liquid blocks and its T, one direction only,
      since the flux is `k * nL_a` and so non-negative).
    * ⚠ **AND EVEN REFINED IT BUYS NOTHING ON A VAPOUR-COUPLED PAIR, WHICH IS EVERY
      SLOW TEST IN `test_rig.py`.** A pressure difference reaches every amount in the
      donor through `V_G`, so the receiver's gas rows depend on all of it. **Two
      vapour-coupled vessels are an honestly dense Jacobian.** A four-vessel still
      with a thermal-only leg does group -- 52 of 68 -- because a thermal edge
      touches two temperature rows and nothing else.
    * So `RigIntegrator.useful_sparsity()` passes the pattern when it groups
      anything and SKIPS it when it would only add sparse overhead to a dense amount
      of work. A one-vessel rig is therefore bit-identical to a lone vessel by
      default now, with no `jac_sparsity=None` needed.
    * ⚠ **UNDER-MARKING IS SILENTLY WRONG ANSWERS**, so the refinement is not
      trusted to the reasoning that produced it: `test_rig` differences the real
      Jacobian on a live, boiling, draining, heat-exchanging rig and asserts every
      non-negligible entry is marked. That test is what makes it safe.

45. ⚠⚠ **AND THE RAW-OUTPUT GUARD IMMEDIATELY FOUND A REAL, PRE-EXISTING
    CONSERVATION FAILURE IN THE RIG, WHICH IS NOT FIXED. This is the top item for
    next session.** It is exactly what item 42's instruction was for.
    * ⚠ **AND IT IS NOT A RIG BUG. THE BULK VENT DESTROYS GAS IN ANY OPEN FLASK,
      AND IT SCALES WITH `k_vent`.** The rig is only where the guard surfaced it
      first. Measured on a single, uncoupled, ORDINARY esterification -- 3 mol acetic
      acid + 3 mol ethanol at 350 K, air-filled, one hour:

          k_vent = 1e3 (THE DEFAULT)   -2.3025 mol N2 against 0.0227 charged   101.5x
          k_vent = 10                  -0.3081 mol                              13.6x
          k_vent = 0 (sealed)          +0.0039 mol                              none

      It vanishes when the vent is shut, which attributes it to that term and nothing
      else. ⚠ **SO IT BLOCKS AN INTERFACE**: an open flask is the commonest thing a
      player will do, `k_vent = 1e3` is its default, and dissolved O2 budgets the
      oxidation cascade that makes a prep's side products -- so the state a player
      lives in has a gas balance wrong by 100x, and it would arrive as "why did
      nothing oxidise" rather than as a conservation error.
    * **The refluxing rig is the same defect through the vapour edge.** After 3000 s
      its TOTAL nitrogen is **-0.336 mol** and its oxygen **-0.312 mol** against the
      ~0.06 mol charged. Not a dipole -- the totals themselves are negative, so the
      projection has to CREATE matter to bring them to zero.
    * **THE MECHANISM IS A CLAMPED COMPOSITION IN A BULK FLOW TERM.** Both the vent
      and the vapour edge take the donor's composition (and the rig its pressure)
      from `np.maximum(nG, 0)`, so once a gas
      component drifts below zero the flux cannot see it --
      and the edge keeps removing gas from an already-negative block. There is no
      restoring term, which is the same shape as the note in
      `project_non_negative`'s docstring ("the derivative is identically zero once a
      component drifts below zero, so a solver excursion into the negative is never
      pulled back") except that here it is actively driven further down. Boiling
      sweeps the pot's air out through the condenser, the condenser vents it, and the
      sealed pot goes negative without bound.
    * **IT WAS REPORTED ON A CHANNEL NOTHING WAS READING.**
      `project_non_negative` returns exactly this residual and
      `Vessel.conservation_report` surfaces it, and no rig test called it. Its
      docstring says such a residual "is bounded by round-off", and for a lone
      vessel it is -- 1.26e-6 mol measured over 600 s. For a rig it is five orders
      of magnitude larger. **New `Rig.conservation_report()`**, and the reflux test
      now asserts the leak is REPORTED so it cannot go quiet again.
    * The physics results survive it -- the azeotrope still lands at x = 0.894 and
      351.2 K, reflux still pins at 352.9 K -- because the projection conserves
      everything it can and the air is not what those tests measure. That is why it
      hid, and it is not a reason to leave it.
    * ⚠ **THE GUARD'S THRESHOLD IS A RATIO, NOT AN ABSOLUTE, AND THAT MATTERS.** The
      three cases are separated by nine orders of magnitude -- a round-off dipole is
      6e-8 of the material present, a rig sweeping its air is 6x, and the unclipped
      Born term was 3e9x -- so `EXCURSION_RATIO = 1e3` refuses the third and reports
      the second, and there is no threshold in between that could be accused of
      being chosen to make tests pass. **My first version got this wrong in a way
      worth recording**: it bounded against the sum of ABSOLUTE per-phase values,
      which hands a cancelling dipole a bound twice its own size, so the check passed
      on precisely the case it exists for. The test that reproduces the 3.07e9 mol
      dipole is what caught it.

DONE (2026-08-19): THE VENT LEAK IS FIXED AND THE ENGINE HAS A FACE. 560 tests
pass, lint clean. New module: `chemsim/ui/` (Layer 7 -- `session.py`, `app.py`,
`examples.py`). New test file: `tests/test_ui.py`. `validation/vent_leak.py` is
rewritten and now runs BOTH forms, so the before-and-after is measured rather than
quoted. Nothing in this session was chemistry.

46. ⚠⚠ **THE BULK VENT DESTROYED GAS, AND THE DIAGNOSIS IN THE LAST HANDOFF WAS
    HALF OF IT.** The clamped composition was real and was the reason nothing
    RESTORED a component that had gone negative. It is not what DROVE it there.
    * **The driver was a MIXED-SIGN PRODUCT.** The vent blended the two donor
      compositions across the crossing:
      `vent = k_vent * dP * (w*x_out + (1-w)*x_ambient)`, `w = sigma(dP/scale)`.
      At a small POSITIVE dP the flow is outward, but `1-w` is still ~0.5 -- so
      **half of an OUTflow left carrying the ROOM's composition.** The room is 79%
      nitrogen, so the flask exported nitrogen at a rate that did not depend on how
      much nitrogen it had, and once `x_out` clamped to zero that term carried on
      alone. Measured along the real trajectory: after t = 1 s the entire removal
      is that branch, at `1-w = 0.485`.
    * ⚠ **AND IT WAS NOT A CORNER OF THE BAND, IT WAS THE OPERATING POINT.** An
      open flask settles where `k_vent*dP` matches its boil-off, which at the
      default conductance is **dP ~ 3e-6 bar against a 1e-4 smoothing scale**. So
      the blend never resolved the direction of flow at all. **That also explains
      the "it scales with k_vent" attribution that the last session took as
      decisive**: a smaller conductance needs a bigger dP to pass the same flux,
      which pushes the operating point OUT of the band. The band was the problem,
      not the conductance -- and an attribution by scaling identified the right
      TERM and the wrong PARAMETER inside it.
    * **THE FIX -- `numerics.vessel_integrator.backflow_part`.** Write the flow as
      a full stream of the donor's composition plus a correction that can only ever
      be an INFLOW:
      `vent = k_vent * (dP*x_out + backflow(dP)*(x_ambient - x_out))` with
      `backflow <= 0` everywhere. Three properties, and they are the reasons:
      - **it sums to `k_vent*dP` EXACTLY at every dP**, because both compositions
        are normalised and their difference sums to zero. The pressure relaxation
        every boiling plateau rests on is untouched bit for bit, whatever the
        smoothing does -- which is why the invariants survived a change to this
        term;
      - **every OUTWARD contribution is proportional to `x_out`**, hence to the
        donor's own `nG`. That is the self-limiting property the evaporation and
        liquid-liquid fluxes already had;
      - **a species absent from the donor can only be GAINED.**
    * The rig's VAPOUR EDGE had the identical defect and takes the identical form.
      Same function, imported.
    * **MEASURED: -2.3019 mol N2 becomes -4.76e-11 at the default k_vent**, and the
      refluxing rig goes from creating 0.4765 mol of N2 + 0.0721 of O2 to
      `conservation clean`.

47. ⚠ **THE SMOOTHING SCALE IS NOW ZERO -- THE EXACT SWITCH -- AND THAT IS A
    MEASUREMENT.** `DP_VENT_SMOOTH` and `DP_SMOOTH` were 1e-4; both are 0.0.
    * **NO NON-ZERO SCALE IS FREE, and this is worth carrying forward as a general
      result.** `backflow_part` must be <= 0 with a zero at the origin, so the
      origin is a MAXIMUM, so the function is quadratic there -- and that quadratic
      is a counter-current against the bulk flow, sized by a numerical constant
      rather than by any physics. It is not removable: an exact positive/negative
      split that is also C1 at zero **does not exist**, because `pos >= max(x,0)`
      with equality at 0 forces the kink back.
    * Swept on the observable it corrupts (an open flask's oxidation cascade, which
      is budgeted by headspace O2): **acetaldehyde after an hour reads 2.97 / 3.01 /
      3.19 / 3.76 / 4.17 mmol at scale 1e-4 / 1e-5 / 1e-6 / 1e-7 / 0.** Monotone,
      so it is the residue and not scatter, and 1e-6 is still 24% low.
    * ⚠ **A NARROW BAND IS WORSE THAN NO BAND, MEASURED.** At 1e-8 the vapour-edge
      conservation test takes **3507 solver steps against 224 at zero**: BDF must
      resolve a real derivative of order 1/scale, where a kink has nothing to
      resolve and costs a few rejected steps at the crossing. **The "smooth it"
      reflex this codebase learned from `DRYOUT_MOLES` and `MELT_BLEND` INVERTS
      here**, because those were value discontinuities and this is only a kink.
    * COST, stated: `tests/test_rig.py` goes 113 s -> 185 s, of which ~45 s is the
      rig legitimately keeping air it used to destroy (1e-6 also retains it and
      costs 140 s) and the rest is the kink. **The whole suite is unchanged at
      ~11 min.**

48. **THE CHECK THE BRIEF ASKED FOR, ANSWERED: `k_vent = 1e3` IS NOT TOO STIFF, AND
    A SMALLER DEFAULT IS NOT THE CHEAP FIX.** Ethanol under a hotplate pins at
    **351.466 / 351.472 / 351.531 K at k_vent = 1e3 / 10 / 1**, and at k_vent = 1
    the flask sits **0.26% over ambient** because the vent is then SLOWER than
    `kla = 5` and cannot carry the boil-off away. It also only suppressed the leak
    by luck, by moving dP out of the band -- not a property anyone could rely on at
    a different scale or boil rate.

49. **THE SHARPER TEST, AND THE ANSWER IS YES: THE OXIDATION CASCADE MOVES.** The
    brief asked for this explicitly and for it to be reported either way. An open
    flask held BELOW its bubble point (the panel-1 flask boils dry, so all of its
    air leaves legitimately and the residue is invisible there) makes **4.17 mmol
    of acetaldehyde against the old form's 3.68**, and the whole sweep above is the
    same measurement. So the gas balance being wrong by 100x was observable in a
    prep's side products, not only in a conservation channel.

50. **THE FOUR INVARIANTS ARE UNMOVED**, re-measured rather than re-typed:
    ethanol under a hotplate **351.466 K**; a 50/50 pot's bubble point **352.887 K**;
    reflux holds it at **352.892 K / 1.01336 bar indefinitely, boiling=True**; the
    still's enrichment still crosses zero at x = 0.894 with the pot minimum at
    351.2 K (`test_rig.py`, all 20 passing).

51. **ROBUSTNESS: 15 OK, 6 REFUSED, 0 UNCLEAR, 0 WRONG** (was 14 / 5 / 0 / 2).
    * `an ordinary esterification, open` and `pull a vacuum on a volatile` were the
      two REFUSED rows the brief said must become OK. **Both are OK.**
    * The two WRONG rows were both `pressure` returning `inf`. **Both are REFUSED,
      with the overflow named.**
    * ⚠ `add 0.5 mol H2SO4 to 0.5 mol NaOH` REFUSES with a diagnosis attached, and
      **it refuses identically under the OLD vent form** (measured by substituting
      it back). It is pre-existing, not a regression, and a clean refusal is what
      the harness's rule asks for -- but it is the row to look at next if the acid
      quench matters. Its setup is `kla = 0` with a gas headspace, which is the
      documented flat-column cliff.

52. **`VesselIntegrator.check_capacity` -- ONE RULE FOR BOTH `inf` PRESSURES, and
    the boundary was the decision.** **Exactly full is legitimate; over-full is not
    a state.** A flask brim-full of ice is somewhere a player arrives on purpose
    (30 mol of water is 0.54 L in a 1 L flask). A vessel holding MORE condensed
    matter than it has room for is not a flask under any pressure. Called from
    `check_state` (on the way in) AND `check_raw_solution` (on the way out, because
    an overfill can GROW during a solve).
    * ⚠ **`CAPACITY_SLACK` IS 10%, AND MY FIRST VERSION AT 0.1% WAS WRONG -- TWELVE
      TESTS SAID SO.** A vessel's volume here is NOMINAL, the way a 1 L flask's is:
      "one litre of 1 M acetic acid" is 55.4 mol of water plus a mole of acid and
      comes to **1.006 L** by Rackett molar volumes, which is a flask filled to its
      neck rather than a mistake. What the check has to separate is a full flask
      from an arithmetic result nobody can be shown, and the real cases are nowhere
      near each other -- **legitimate at 1.006x, an overfilled flask at 3.6x, a
      vessel dissolving the room at 116x.** Nothing lives between 1.1 and 3.6, so
      it is not a threshold chosen to make anything pass. (Same shape of argument as
      `EXCURSION_RATIO`, and the same mistake avoided by measuring.)
    * ⚠ **AND THE FROZEN FLASK IS NOT WHAT THE BRIEF PREDICTED.** "It freezes solid
      and fills the flask" is wrong twice: **SEALED, it freezes cleanly** (0.542 L
      of solid, air conserved), and at T_env = 250 K open it also freezes cleanly.
      What fails is the OPEN flask at 100 K, and the cause is **Henry's law
      extrapolated 170 K below its window making water a bottomless sink for
      nitrogen**: it inhales **3382 mol of air** from a room it is connected to and
      reports **116 L of liquid in a 1 L flask**. The overflow is the symptom that
      can be checked cheaply and exactly; the extrapolation is the cause, and the
      refusal message names it.
    * `Vessel.pressure` returns **P_ambient** when the vessel is exactly full rather
      than `inf`. A flask with no headspace is not a flask at infinite pressure --
      it has nowhere for a gas to be, so its pressure is what presses on it.

53. ⚠ **A PROTOCOL-LAYER GAP FOUND BY BUILDING THE INTERFACE: `k_diss` WAS NOT
    REACHABLE FROM A `VesselSpec`.** It sets how fast a solid dissolves or
    crystallises, and `recipes.BENZOIC_ACID_PREP` runs its pot at **0.05 against
    the 1e-2 default** -- so the prep expressed as a scenario crystallised five
    times too slowly and the example a frontend loads was not the example the
    harness measured. Exactly the same class of gap as transfer losses, `k_lle` and
    `Scenario.electrolyte`, and missed when those were closed. Fixed, and pinned by
    a test that compares the example against `recipes` field by field.

54. **TWO SMALL ENGINE ADDITIONS THE INTERFACE NEEDED, both trajectory-neutral.**
    * `World.flush()` -- apply events already due, without integrating. ⚠ It exists
      for a LOOK and not for physics: `now()` schedules for the current instant and
      events fire between integrations, so a frontend that charges a reagent and
      renders the flask shows one without the reagent in it, which reads as a lost
      click. Sound because `_step` applies a same-instant event with no intervening
      `_advance`, so these fire in this order with this state either way, and
      nothing is added to the script.
    * `World.run_script(entries)` -- the script walk, extracted out of `replay` so
      that a caller holding a script and a world does not reimplement it. A second
      copy is a second thing to keep in step with the script format.

54b. **THE PERMITTIVITY-FREEZE DEBT IS PART-CLEARED, AND IT IS NOT CHEAP DEBT.**
    `validation/permittivity_freeze.py` ran further than it ever has. Panels 1-3
    produced numbers and the headline it exists for is among them: over the first
    600 s of the acid quench, **frozen costs 275.1 / 240.0 / 123.5 s of wall time
    against live's 576.5 / 490.5 s at 1 / 5 / 20 calls, about 2.1x**, while the crop
    is 0.183570 mol and the benzoyl balance 0.200000 mol in EVERY row and the layer
    permittivity agrees to four decimals. **So the step-size dependence the freeze
    traded away is real and lives in the fifth decimal of a crop.**
    * ⚠ Two things still owed. The `False / 20` row printed a wall time of 25221.1 s,
      which CANNOT be one for a process that lived under an hour -- treat that cell
      as suspect rather than as a measurement. And **panel 4 aborted** on the
      too-tight `CAPACITY_SLACK` described above, then did not finish inside ten
      minutes on its own afterwards, because it runs ten 2000 s solves at `kla = 0`.
    * The brief called this "measurement debt, cheap and worth clearing early". It is
      not cheap, and calling it cheap is why it has been carried for two sessions.

55. **THE INTERFACE -- `chemsim/ui/`, and the split is the design.** `python -m
    chemsim.ui [flask|boil|ester|prep]`. Tkinter, because it is in the standard
    library and this project adds no dependency it does not have to.
    * **`session.py` is the half that can be WRONG, and it has no widgets in it.**
      What is hard about a frontend for this engine is not layout: it is that
      **cost is concentrated in stiff transients**, so an operation must render as
      IN PROGRESS rather than block. One worker thread owns the `World` and nothing
      else ever touches it -- every command, including instantaneous ones, goes
      through one queue in submission order, so there is no lock around the engine
      at all and the only shared object is an immutable `Snapshot` published by a
      single assignment. All 19 tests in `tests/test_ui.py` drive that half; none
      opens a window.
    * ⚠ **CHUNKING IS PART OF THE RECIPE, NOT A RENDERING TRICK.** A long step is
      run as a sequence of short ones so a thermometer climbs rather than teleports
      -- and because freezing the layer permittivity made the caller's `dt` weakly
      load-bearing, that changes the answer slightly. It is therefore RECORDED:
      `World.script` gets the chunks that were run, and a replay of what the player
      did reproduces what the player saw (pinned to 1e-9). The chunk is a visible
      setting for that reason -- a knob on the recipe, not on the graphics.
    * ⚠ **A CHOPPED WAIT IS STILL A ROOT, WHICH IS THE WHOLE VALUE OF THE VERB.**
      Each chunk is a real `wait_until` with a short timeout, so the instant is
      located by scipy inside whichever chunk straddles it -- not the end of that
      chunk. Pinned against a single unchopped wait: same discovered instant to
      1e-3. Chopping a wait costs resolution nowhere.
    * ⚠ **CHUNKING BOUNDS THE UPDATE INTERVAL IN SIMULATED TIME, WHICH IS NOT WALL
      TIME**, and nothing can make it so. Thirty simulated seconds of crystal growth
      is instant; thirty of the acid quench is two minutes. So `stop()` takes effect
      at the next CHUNK BOUNDARY and says `stopping` while it waits -- a scipy solve
      cannot be interrupted from outside, and a cancel that does not cancel is worse
      than an honest one that arrives late.
    * **The cost meter is on screen, live**: wall seconds per simulated second.
      That is this project's sharpest performance finding rendered as a gauge, and
      without it a player reads a slow moment as a hung program.
    * **The reports panel is a first-class column**, not an error dialog:
      `conservation_report`, `integrability_report`, `atmosphere_report`,
      `lle_report`, `electrolyte_report`, `holdup_report`, `crust_report`. The rule
      that nothing is silently approximated is worth nothing if nobody is shown
      what it said -- **the rig destroyed 0.34 mol of its air for months on a
      channel that was reported all along and that nothing read.**
    * **A refusal is content.** Engine messages name a cause and a fix, several of
      them across multiple lines, so they are carried verbatim on the snapshot and
      rendered. The worker survives one and carries on, which is pinned.
    * **`chemsim/ui/examples.py`** -- four starting points as `Scenario` + opening
      script, including the benzoic-acid prep. ⚠ Every number comes from
      `recipes.BENZOIC_ACID_PREP`, so there is still ONE home for a recipe and the
      "load an example" button cannot drift away from the harness.

DESIGN (2026-08-20, no code): **`GAME_DESIGN.md`** settles what sits on top of the
engine. An inventory item is a COMPOSITION and never a `(name, purity)` pair, so
purity is derived, impurities are traceable, and **shelf life is emergent** -- wet
aspirin hydrolyses in the bottle for free. A purity gate must be a MECHANISM and
never a threshold, and six already work (the dilution gate measures 20.9 -> 48.8 ->
74.1% conversion on water content alone). The approximation to reach for is on TIME,
never on MATTER: rate errors are forgiven by attractors, composition errors
propagate linearly, and **the only error that can make step 12 unrecognisable is one
bad thermodynamic number** -- of which S8 at Gf = +276 kJ/mol is a live example.

DONE (2026-08-20): **THE FLOOR, AND A CHAIN STANDING ON IT.** 616 tests pass,
lint clean, suite ~12 min. New modules: `properties/element_data.py`,
`properties/mineral_data.py` (both GENERATED). New tools:
`tools/build_element_data.py`, `tools/build_mineral_data.py`. New harness:
`validation/game_gates.py`. New example: `examples/oil_of_vitriol.py`. New tests:
`tests/test_element_data.py` (41), `tests/test_lead_chamber.py` (15). Nothing in
this session was engine work, and two pieces of engine work are now NAMED with
the measurements that justify them.

56. ⚠⚠ **THE CLASS OF BUG WAS BIGGER THAN THE BRIEF SAID, AND THE HARNESS FOUND
    THE REST OF IT BEFORE ANY CODE CHANGED.** The brief named S8 at Gf +276.0
    where a reference state is 0 by definition. `validation/game_gates.py` panel
    4, written first and run before the fix, found three more live members:

        Cl2    Joback Hf -74.81  vs 0 exact   fixed 2026-08-16, species by species
        F2     Joback Gf -440.5  vs 0 exact   STILL LIVE -- the lesson had not generalised
        S8     Joback Gf +275.96 vs +48.68    e^91 in any K
        ozone  Joback Gf -552.8  vs +163.24   716 kJ/mol out; elemental, not a reference state
        [Cl-]  Joback Gf -10.43  vs -111.73   101 kJ/mol, and TWO ANSWERS for one species

    * ⚠ **THE UNIFYING STATEMENT IS ABOUT THE ESTIMATORS' DOMAIN, NOT ABOUT
      ELEMENTS.** Joback and Benson are fitted to NEUTRAL, MULTI-ELEMENT
      molecules; applied outside that domain they do not fail, they return a
      well-formed sum that means nothing. `thermochemistry.get` now refuses an
      element or an ion outright -- curated table or REFUSED BY NAME, with the
      refusal saying which table to add it to or which representation to use.
      **That is why it generalises where fixing Cl2 did not.**
    * **The halide ions were the whole of the ion half**, because they are the
      only ions Joback's group table can fragment: chloride 101.3 kJ/mol apart
      between providers, bromide 101.0, fluoride 53.5. ⚠ **And IODIDE was priced
      by Joback in BOTH providers**, because HI is not in the pKa table -- so it
      had no second opinion at all and nothing could have noticed.
    * ⚠ **NET CHARGE IS NOT ENOUGH, and that hole is real.** `[Na+].[Cl-]` sums
      to zero. Caught by a separate FRAGMENT test: a dot-separated SMILES with a
      charged fragment is a mixture of ions, not a molecule. A neutral
      multi-fragment SMILES is deliberately left alone -- nothing here produces
      one. And the test must be on NET charge, not on the presence of formal
      charges, or nitrobenzene (`O=[N+]([O-])c1ccccc1`) stops pricing.

57. ⚠⚠ **AND THE Cl2 FIX HAD ITSELF INTRODUCED THE SAME BUG ONE LEVEL UP.** A
    `ThermoData` is on the IDEAL-GAS basis, so only a species whose reference
    state IS the gas is exactly zero. **Br2 is a LIQUID and I2 is a SOLID, and
    both were pinned at 0.0** where their ideal-gas records are Gf +3.08 and
    +19.29, Hf +30.90 and +62.40. Fixing chlorine species-by-species took a
    75 kJ/mol error out of one halogen and put a 62 kJ/mol error into another.
    * **The independent cross-check is that shifting the ideal-gas value back
      down into its own phase must return zero**, and no term in it touches the
      formation table -- Psat comes from Tb/Tc/Pc through Lee-Kesler and Hfus/Tm
      are separate measurements:
      `Gf(g) + RT ln(Psat/P_std) - Hfus(1 - T/Tm) == 0`.
      **Measured: Br2 -0.05, I2 +0.14 kJ/mol. With the old zeros: -3.14 and
      -19.15.** So the check can reject, and a test asserts that it would have.
    * ⚠ **SULFUR IS THE WEAK ROW AND THE HARNESS SAYS SO: +3.05 kJ/mol.**
      Lee-Kesler extrapolated from Tb = 717.8 K down to Tr = 0.23, and liquid
      sulfur's vapour is not S8 but a shifting S8/S6/S2 equilibrium. That row is
      a SANITY BOUND, not a confirmation, and **S8's vapour-pressure curve is the
      weakest number in chain 2.** Pinned as a band rather than a value.
    * A GASEOUS reference state gets no cross-check and needs none: it is exactly
      zero, and above Tc the "Psat" is a supercritical extrapolation.

58. **`properties/element_data.py` -- 9 elemental species, GENERATED.** Gf DERIVED
    against the CRC element reference states, never transcribed; Hf and S0 for a
    species from the SAME database or the entry is refused; every estimated
    method excluded explicitly; ideal-gas Cp sampled from `thermo` and FITTED to
    the kernel's cubic, residuals under 0.15%.
    * ⚠ **`atoms_per_unit` IS LOAD-BEARING AND EASY TO GET WRONG.** `chemicals`
      tabulates sulfur under formula "S", so its S0 of 32.1 is PER GRAM-ATOM,
      while bromine is "Br2" and its 152.2 is per mole of Br2. Divide by the
      wrong one and every sulfur compound's entropy of formation is out by 8x.
    * ⚠ **THE `chemicals` JOBACK TRAP, again and worse.**
      `Hfg('7782-44-7', 'JOBACK')` is **-426930 J/mol for OXYGEN**, and
      `Hfg('10544-50-0', 'JOBACK')` is 381090 -- bit-identical to our own
      Joback. S8's Tb, Tm AND Hfus under its own CAS are ALL Joback-only; the
      measured values live under CAS 7704-34-9 with per-gram-atom molar
      quantities.
    * ⚠ **A CROWD-SOURCED MELTING POINT CAN BE 100 K WRONG.** `OPEN_NTBKM` is in
      the experimental tier and comes FIRST in `chemicals`' preference order for
      sulfur, where it returns **286.4 K against CRC's 388.4** -- sulfur melts at
      115 C, not 13. The builders take an explicit preference order with CRC
      first and PRINT the full spread per entry so a disagreement is visible
      rather than arbitrated silently.
    * ⚠ **`CRC_INORG` IS NOT AN ESTIMATION METHOD, and `build_physical_data.py`
      says it is.** Harmless there -- every candidate in that script is organic --
      and it would have refused the ENTIRE floor here, because CRC_INORG is the
      only source of a melting point for sulfur, iodine and every mineral. **A
      misclassification is latent only until the first caller from a different
      domain.**
    * **The five gas elements' PHYSICAL halves are carried forward VERBATIM**,
      stated as a decision: they are the atmosphere and the dissolved-gas set,
      their Tc/Pc/Vc feed the PSRK Henry extension and Rackett, and re-basing
      them from a different compilation would move invariants that have nothing
      to do with the formation bug. The builder PRINTS the comparison against
      `chemicals` (pinned Cp within 2% of the live fits) so the difference is
      visible rather than hidden.
    * **REFUSED, with the reason, and correctly**: graphite and every metal (the
      reference state is a LATTICE and this engine's species are molecules -- the
      ideal-gas record for `[C]` is the carbon ATOM at Gf +671, which is not
      charcoal); a bare monatomic symbol (the most ambiguous way to name an
      allotrope; the refusal names the reference-state SMILES instead); S2 (no
      measured Tb/Tc/Pc anywhere); P4 (whose tetrahedral SMILES canonicalises
      through RDKit to AROMATIC phosphorus).

59. **`properties/mineral_data.py` -- 13 minerals, and the LATTICE question
    answered by measurement rather than argument.** The brief asked whether a
    lattice needs its own entry or whether ion-by-ion plus a lattice energy is
    the honest form. **It is neither on its own.** The engine's only route from a
    solid into solution is the ideal-solubility fusion law, and against tabulated
    solubility at 298 K:

        NaCl     0.015 mol/L vs 6.15     0.0025x   407x too INSOLUBLE
        K2CO3    0.014       vs 8.03     0.0017x   585x too insoluble
        Na2CO3   0.008       vs 2.06     0.0040x   251x too insoluble
        KNO3     8.96        vs 3.51     2.55x       2.6x too SOLUBLE
        CaCO3    0.0015      vs 0.00014 11.0x       11x too soluble

    **6,445x of spread and the sign FLIPS.** Not a bias a factor could absorb --
    the wrong law. Tm and Hfus describe lattice -> MELT; dissolution is lattice
    -> HYDRATED IONS, and the hydration energy appears in neither.
    * So the lattice **does** get an entry, on the solid basis, because a
      solubility product or a calcination (`CaCO3 -> CaO + CO2`) would be
      computed from it -- **but it is REFERENCE DATA, not a provider tier**, and
      `thermochemistry` refuses the lattice SMILES by name and points at the
      ion-by-ion route: *"that is calcite, an ionic lattice... charge its ions
      instead"*.
    * **Sanity anchors: derived Gf(s) agrees with CRC's own tabulated Gf(s) to
      0.03-0.25 kJ/mol on five of six.** ⚠ K2CO3 is 1.8 out, and that is a
      finding about the source: **CRC's own K2CO3 entry is not internally
      consistent between its Hf, S0 and Gf.** Exactly what deriving rather than
      transcribing exposes.
    * ⚠ The same-database rule bites: **FeSO4's S0s is 107.5 J/(mol K) from CRC
      and 120.93 from WEBBOOK**, 13.4 apart and worth 4 kJ/mol in Gf. And
      **pyrite is REFUSED outright** -- WEBBOOK has its enthalpy, nothing has its
      entropy, so its Gf cannot be derived and mixing two tabulations is
      forbidden. A source limit, not an oversight.
    * **Spectator cations extended to Ca2+/Mg2+/Fe2+/Cu2+/Zn2+**, on exactly the
      Na+/K+ argument -- a species participating in no reaction can take any
      consistent value because it cancels -- **and with the two mechanics that
      would end that licence named on the entry**: a solubility product (calcium
      and carbonate would then be on opposite sides of a real equilibrium) and
      electrochemistry (a redox couple whose two members are both zero has no
      potential).

60. ⚠ **A 101 kJ/mol CORRECTION MOVED NO INVARIANT, AND THAT IS INFORMATION.**
    The chloride refusal broke 26 tests that used NaCl as a liquor tracer with a
    plain provider. Repointing them at `electrolyte_provider()` -- which is what
    the refusal message tells the caller to do -- brought **all 26 back with every
    asserted value UNCHANGED**, and `K(Na+) organic/aqueous` is still 6.155e-6.
    Two reasons, both worth carrying: a spectator's formation energy reaches
    nothing, and the Born term is a TRANSFER referenced to water that never reads
    `Gf` at all. **The correction was still right to make** -- a network that
    answers differently depending on how it was built is the shape of thing that
    goes quietly wrong later -- but it is a good example of a real error with no
    observable consequence in the cases that existed.
    * `Scenario(electrolyte=True)` was needed for the replayable path's version
      of the same fixture, which is the reason that flag exists.

61. **CHAIN 2 IS BUILT, AND THE CHAMBER IS A REAL CATALYTIC CYCLE.**
    `reactions.lead_chamber()` -- two templates, 7 species, 4 reactions (two
    forward, two derived reverses). **100.0% yield sealed; 80.3 turnovers on a
    0.5 mmol carrier charge; 22-42% if you vent it.** Cost: ONE data entry (S8)
    and no engine work.
    * ⚠ **THE CYCLE MUST NOT BE FOLDED, AND `CATALYST_REFERENCE` DOES NOT APPLY.**
      The acid catalysis in `library` is a FOLDED catalyst -- hydronium on both
      sides of one SMARTS, exponent 1, net stoichiometry 0, one reaction, no
      cycle. Here NO2 is genuinely consumed and NO genuinely regenerated, so the
      carrier has an integrated concentration that rises and falls. **The
      turnover count is what separates the two**, and a folded catalyst cannot
      produce one.
    * **A TEMPERATURE CEILING AT ~600 K, DERIVED AND NOT DECLARED.** The
      regeneration is written reversible, so `2 NO2 -> 2 NO + O2` takes over when
      it becomes favourable: at 650 K the NO/NO2 ratio has FLIPPED by 100x and
      the carrier sits as NO, which cannot oxidise SO2. Yield 94.1%. There is no
      maximum operating temperature anywhere in this project -- detailed balance
      derived one from the formation data, and it is why a real lead chamber is a
      big cool room rather than a furnace.
    * **A NEGATIVE ACTIVATION ENERGY THAT IS REAL, AND THE ONLY TEMPLATE WHOSE
      `A` IS NOT HAND-AUTHORED.** `2 NO + O2 -> 2 NO2` is genuinely termolecular,
      so its measured k = 1.2e-31 exp(+530/T) cm^6 molecule^-2 s^-1 converts
      straight into A = 4.35e10 L^2 mol^-2 s^-1 and Ea = -4.4 kJ/mol. It runs
      through an ONOONO dimer and goes FASTER as it gets colder. So "run it cool"
      is right for two independent reasons and neither was written down.
    * ⚠ **THE VENTING LOSS IS NOT MONOTONE IN `k_vent`** (22.4 / 23.4 / 41.7% at
      1 / 10 / 1e3), and the reason is the bulk-flow vent: a LARGE conductance
      holds the chamber at ambient pressure so little net volume crosses, while a
      small one needs a real pressure difference to pass the same flux. The loss
      is set by how much gas crosses the boundary, not by the conductance.
    * ⚠ **TWO ATOM-LEVEL TRAPS IN ONE SMARTS, both of which SANITISED HAPPILY.**
      The oxygen transferred from NO2 arrives carrying its formal -1, so the
      product was BISULFATE; neutralising the charge without also declaring the
      hydrogen count left an oxygen RADICAL on the sulfur. Neither raised
      anything. **Read the product SMILES.**
    * ⚠ **A SPECIES KEY MUST BE CANONICAL, and the failure mode is a SILENT
      ZERO.** `VesselState.total` is a dict lookup, so asking it for
      `"OS(=O)(=O)O"` when the network stored `"O=S(=O)(O)O"` returns 0.0 --
      which reads exactly like a reaction that did not happen. The chamber
      appeared to destroy all of its sulfur.

62. **THE NITRATE-LIBERATION TEMPLATE DOES NOT EXIST AND DOES NOT NEED TO.** The
    brief asked for one. It is a proton transfer the engine already does:
    `NO3- + H2SO4 <=> HNO3 + HSO4-`, with both pKa values already in
    `electrolyte._PAIRS` (-3.0 and -1.4), the existing
    `mineral_oxyacid_dissociation` template, and detailed balance. Sulfuric acid
    is stronger by 1.6 pKa units so it protonates nitrate; nitric acid boils at
    356 K and bisulfate does not, so distillation takes it away.
    * ⚠ **AND IT EXPOSED A TRAP: DO NOT SUBTRACT PROVIDER `Gf` VALUES BY HAND.**
      The ions are anchored on the acid in its LIQUID standard state (see
      `electrolyte`) while the neutrals are ideal-gas, so a naive difference reads
      **dG = -46.2 kJ where the pKa gap says -9.1**.
      `standard_state.reaction_shift` gets it right; a script doing its own
      arithmetic on provider output does not. That error was made writing the
      example.

63. ⚠⚠ **THE BURNER IS A WALL, MEASURED IN FOUR NUMBERS, AND IT IS NOT SHIPPED.**
    `S8 + 8 O2 -> 8 SO2` was written, built and measured FIRST -- same discipline
    that killed crystal occlusion and perbenzoic acid. The SMARTS is fine (4
    species, 1 reaction, 0.45 s, no explosion) and the thermochemistry is
    excellent (dG -2449.7 kJ, ln K = 988, a hard ATTRACTOR). **What fails is the
    RATE LAW**, because the kernel takes mass-action exponents from stoichiometry,
    so a global stoichiometry written as one elementary step is **NINTH ORDER,
    eighth in O2**:
    1. it cannot run with a physical pre-exponential -- [O2]^8 = 2.9e-20 at 700 K
       and atmospheric oxygen, so it needs **A = 7e24 (L/mol)^8/s**, four orders
       past anything defensible and in units a pre-exponential does not have;
    2. where O2 is in EXCESS the attractor holds and the wrong form is
       **FORGIVEN** -- 100.0% at 550 / 700 / 900 K and at A = 1e20 and 1e24 alike,
       exactly as GAME_DESIGN section 3(a) predicts;
    3. ⚠ **where O2 is LIMITING it is NOT, and that is disqualifying** -- 86.5 /
       92.8% at A = 1e20 against 96.4 / 98.0% at 1e24. The answer depends on a
       hand-authored A, because [O2]^8 stalls asymptotically and the last oxygen
       never burns. **So it corrupts the HEADSPACE-BUDGET gate**, one of the six
       purity gates that already work;
    4. forced to A = 1e26 the projection CREATES MATTER -- 334.8% yield, with
       `conservation_report` naming 0.136 mol O2 and 0.047 mol S8 created. A 2.35x
       excursion sits under `EXCURSION_RATIO`, so it is REPORTED rather than
       refused, which is the designed behaviour and is how it was caught.
    * **THE FIX IS ENGINE WORK AND IT IS NAMED: rate laws whose exponents are
      DECLARED independently of stoichiometry.** Already on the backlog as
      "non-mass-action rate laws (LHHW, Michaelis-Menten)", and this is a much
      cheaper first case than either -- a global reaction with a declared apparent
      order, no site balance and no saturation term.
    * ⚠ **AND THE OBVIOUS WORKAROUND IS BLOCKED BY THE ELEMENT TABLE,
      CORRECTLY.** Crack the ring first (`S8 <=> 4 S2`, real -- it is why hot
      sulfur vapour is S2) then burn `S2 + 2 O2 -> 2 SO2`, which is third order
      and perfectly well posed. It needs S2, whose formation half is measured and
      good (Hf +128.60, Gf +79.70, both CRC) and which has **no measured Tb, Tc or
      Pc in any source**, because a diatomic that never condenses as itself has no
      boiling point. Inventing two critical constants to get past that is exactly
      the confident estimate of an unmeasured quantity `element_data` exists to
      prevent. **The wall stays a wall and is reported as one.**

64. ⚠⚠ **AND THE CHAIN FOUND A REAL BUG: A CATALYTIC CYCLE SEEDS ITSELF FROM
    ROUND-OFF. This is the top item for next session.** A chamber charged with
    SO2, water and air and **no carrier at all** -- the carrier species in the
    network but at exactly zero -- reaches **89% yield**:

        t = 1 s      NOx 1.40e-07 mol    H2SO4 3.27e-06
        t = 100 s    NOx 3.22e-05        H2SO4 5.34e-04
        t = 3600 s   NOx 1.21e-04        H2SO4 3.58e-02   (89% of charge)

    Two halves, each individually correct:
    * **THE SEED IS THE PROJECTION.** `2 NO2 -> 2 NO + O2`, the derived reverse of
      the regeneration, runs at A = 2.4e19. Every rate term here is self-limiting
      at zero -- proportional to the species' own amount, the property this
      codebase deliberately engineered -- but a stiff reaction whose reactant sits
      at EXACTLY zero still lets BDF's stages overshoot negative, and
      `project_non_negative` zeroes that entry. With no positive holding to settle
      against it CREATES the amount, and reports it on every single run. 1.4e-7
      mol is genuinely round-off, exactly as that function's docstring promises.
    * **THE AMPLIFICATION IS THE CHEMISTRY AND IT HAS NO BOUND.** A catalytic
      cycle has no fixed gain on its catalyst -- 80 turnovers, measured -- so a
      round-off-sized catalyst charge produces a MACROSCOPIC amount of product.
      **296x**: 1.2e-4 mol of created carrier against 3.6e-2 mol of acid.
    * ⚠⚠ **THE CAUSE IS LOCATED, AND IT IS AN UN-FIXED TWIN OF A GATE THIS
      CODEBASE ALREADY FIXED.** Not the cycle, and not the reverse reaction's
      magnitude. The crystallisation term gates dissolution with

          avail   = nS / (nS + SOLID_EPS)        SOLID_EPS = 1e-9
          excess1 = x_sat * N1 - nL1             room to dissolve
          solute  = k_diss * excess1 * avail

      `avail` is zero at nS = 0 but its SLOPE there is `1/SOLID_EPS` = 1e9, so
      the Jacobian diagonal of an EMPTY solid block is `k_diss * excess1 / eps`
      -- measured on the chamber flask as **3.6e7 for NO and 4.0e7 for NO2 and
      H2SO4**. That is squarely inside the **4e6 to 1.4e8** band ITEM 25 above
      recorded for the second liquid layer's IDENTICAL `N/(N+eps)` knee, which
      was fixed with a SMOOTHSTEP -- zero *and flat* at zero (`_layer_gates`).
      **The solid twin never got the same treatment.**
    * **Two independent confirmations.** (a) The entry scales with `excess1`,
      i.e. with UNDERSATURATION, so the most DILUTE species gets the largest
      entry for a block holding nothing -- and that is exactly the measured
      ordering: NO -1.21e-4, NO2 -1.95e-5, H2SO4 -3.10e-6, and water, nearly
      pure and barely undersaturated, **-2.36e-16**. (b) Widening SOLID_EPS one
      decade to 1e-8 drops NO's drift to **-2.39e-9** and the phantom acid to
      **8.6e-6**; at 1e-6 created NOx is 2.0e-11; and `atol` 1e-14 makes it
      **exactly zero at no wall-clock cost**. (⚠ The sweep is non-monotone in the
      middle -- 1e-7 reads worse than 1e-8 -- which is solver-path noise at these
      magnitudes rather than a second effect.)
    * ⚠ **`ph.solidifies` IS NOT AT FAULT and works perfectly**: O2 and N2, which
      never crystallise, stay at exactly 0.0. NO has real fusion data (Tm
      109.5 K) and is simply far above it -- the ordinary case for most species
      in most flasks. **So this is not a NOx quirk: EVERY undersaturated species'
      solid block is drifting, and a catalytic cycle is merely the first thing
      with enough gain to make it visible.**
    * ⚠ **THE FIX HAS A DOCUMENTED SECOND TRAP, which is why it was not applied
      here.** `_layer_gates`' own docstring records that a smoothstep alone made
      the layer's Jacobian column perfectly FLAT at zero -- fixing the 1e8
      entries and walking straight into `num_jac`'s other pathology, an
      undifferentiable column whose perturbation factor inflates without bound.
      It needed a companion term (`LAYER_REABSORB`) and strictly disjoint gates
      to settle. The solid gate will want the same care and a full suite behind
      it, not the end of a data-curation session. `SOLID_VISIBLE` is 1e-6, so the
      knee has three decades of headroom below the smallest crop anything
      reports.
    * A MASKING approach was also checked and would be CORRECT on this network --
      every reaction that could make NO or NO2 also consumes one of them, which
      is what a catalytic cycle IS -- but it is state-dependent where the gate fix
      is not.
    * ⚠ **NO LOCAL GUARD CAN CATCH IT, AND THAT IS STRUCTURAL.**
      `check_raw_solution` bounds an excursion as a RATIO against the amount
      present, with a 1e-3 mol floor for a species legitimately at zero -- so
      1.4e-7 is four orders under `EXCURSION_RATIO` and is correctly REPORTED
      rather than refused. Nothing looking at one integration step can see that a
      round-off residual is about to be multiplied 300x downstream.
    * ⚠ **AND THE AMOUNT CREATED DEPENDS ON CHUNKING** -- 1.2e-4 mol in one solve
      against 8.3e-6 over sixty -- because each `run` builds a fresh BDF and the
      overshoot is per-solve. `World.script` recording the chunks is now
      load-bearing for a second and worse reason than the permittivity freeze.
    * **Attribution is clean**: an irreversible core step changes nothing (296x
      either way); an irreversible regeneration drops the created NOx tenfold to
      1.1e-5 and the acid to 6.0e-3. So the stiff derived reverse is the dominant
      seed and the remainder is the forward regeneration's own stiffness at zero.
    * ⚠ **GAME_DESIGN SECTION 3(d) GAINED ITS CONVERSE.** It said "no game
      mechanic may depend on a quantity the solver cannot carry". The other half:
      **NO CATALYTIC CYCLE MAY START FROM ZERO CATALYST**, because the cycle's
      gain on its catalyst is unbounded and the solver's own round-off is a
      sufficient seed. Pinned as CURRENT behaviour in `test_lead_chamber.py` so
      fixing it breaks a test that says what changed.

65. **`validation/game_gates.py` -- the measurement debt is cleared.** All four
    probes behind `GAME_DESIGN.md` sections 2, 4, 5 and 6, plus the
    reference-state cross-check as panel 4b.
    * ⚠ **THE DILUTION GATE MOVED ON BEING HARNESSED: 21.6 / 49.9 / 74.7%
      against the quoted 20.9 / 48.8 / 74.1.** The inline probe's flask geometry
      was never recorded, so the harness now DEFINES the measurement rather than
      reproducing it. That is the whole argument for harnesses in one line.
    * The stiffness table came back IDENTICAL (ratio 7.05e21, water recombination
      9.431e18, esterification 1.157e-2), which is what a stable measurement
      looks like.
    * **Salicylate's pKa (2.97) landed** and the ion prices at Gf -410.3.
      ⚠ **The CARBONATE lines did NOT, and the brief was wrong to call them a
      data job.** `ion_thermochemistry` skips a pair whose ACID cannot be priced,
      and carbonic acid cannot: Benson prices its formation half well (Gf -559.1)
      but no source has a boiling point (it decomposes) and the only melting
      point anywhere is **484.65 K from a crowd-sourced compilation, for a species
      never isolated as a bulk solid** -- taking it would be the exact failure
      this session closed. The honest anchor is dissolved CO2, and
      `CO2 + 2 H2O <=> HCO3- + H3O+` consumes TWO waters with delta_n = -1, which
      breaks the delta_n = 0 convention the whole ion table rests on. Bounded
      work, engine-adjacent, and both pairs sit in `_PAIRS` recognised and
      unpriced with the reason on them.

66. ⚠ Windows console is cp1252: a warning glyph inside a `print()` kills a
    script. **Recorded six sessions running, and it bit again in
    `examples/oil_of_vitriol.py` -- immediately after the brief warned about it.**
    Docstrings fine, printed text ASCII.

67. ⚠⚠ **THE ROUND-OFF-SEEDED CATALYST IS FIXED, AND THE FIX IS NOT THE ONE
    THE PRECEDENT SUGGESTED.** Item 64's carrier-free lead chamber reached 89%
    yield on 1.2e-4 mol of NOx that nothing had put there. Cause confirmed by
    direct measurement of the Jacobian: the solid dissolution gate
    ``avail = nS/(nS + SOLID_EPS)`` is zero at nS = 0 but has slope 1e9 there,
    so an EMPTY solid block carried a diagonal of ``k_diss * excess / eps`` --
    **-3.61e7 for NO, -3.95e7 for NO2 and H2SO4, -1.83e6 for water**, the exact
    values the diagnosis predicted.

    ⚠ **AND THE SMOOTHSTEP THAT FIXED THE LIQUID TWIN WOULD HAVE BEEN WRONG
    HERE.** A smoothstep is zero AND FLAT at zero, which is why ``_layer_gates``
    needed ``LAYER_REABSORB`` as a companion with strictly disjoint gates. A
    companion for the SOLID gate would have had to sit opposite the
    PRECIPITATION branch -- which is ungated by design, because anything can
    nucleate -- i.e. exactly the overlapping-gate arrangement that made the
    benzoic-acid acidification unsolvable. The rule item 25 produced says only
    ONE term may govern the block near zero, so the gate itself had to carry a
    bounded, non-zero slope.

    ``SOLID_GATE_TIME`` does that by making the gate's scale THE DRIVING FORCE
    rather than a constant: ``eps = tau * k_diss * excess``. The identity is
    ``1/rate = 1/(k_diss*excess) + tau/nS`` -- two resistances in series, a
    thermodynamic one and an availability one -- and the empty-block slope
    collapses to exactly ``1/tau`` for EVERY species. **That independence is the
    property.** The old knee got WORSE the more dilute a species was, which is
    precisely why the most dilute one seeded the cycle.

    ⚠ **THE VALUE IS A MEASUREMENT.** Swept on the chamber, the solid columns'
    largest entry reads 1.41e6 / 1.36e5 / 1.29e4 / 1.49e4 at tau = 1e-4 / 1e-3 /
    1e-2 / 1e-1 -- **it stops shrinking at 1e-2, and 1e-1 is slightly worse**. So
    1e-2 is the smallest tau, i.e. the least distortion of real dissolution, at
    which this gate has stopped being the stiffest thing in the block.

    **Results.** Carrier-free chamber: created NOx **1.21e-4 -> 1.55e-20**,
    phantom acid **3.58e-2 -> 1.55e-20**, yield **89% -> 0.00%**, and
    ``conservation_report`` is now EMPTY rather than reporting on every run. The
    chunking dependence went with it. ⚠ **And it closed a second row nobody had
    connected to it**: the chamber's carrier nitrogen used to close ~0.5% out at
    a charge four orders LARGER, which had been written up as a residual worth
    naming rather than a defect. It now closes to 1e-6 with nothing in that
    panel touched, which is the cleanest available confirmation that the two
    were one defect.

    **It moved no solubility**, because ``excess -> 0`` drives the scale to zero
    and the gate to 1: benzoic acid dissolves 0.026826 mol at every tau in the
    sweep, identical to six decimals, and a 1e-5 mol crop now dissolves to
    EXACTLY 0.0 where the constant knee left -9.4e-10 behind.

68. **THE CLASS WAS CHECKED BY MEASUREMENT, AND IT WAS NOT CLOSED.** Item 67's
    brief said to ask what else shares ``avail``'s shape. Both named candidates
    were measured:

    * **MELT_BLEND is NOT a member** -- it is a clip with slope 10, not a knee.
    * **DRYOUT_MOLES IS the same shape**, and on the first probe looked LATENT: a
      dry flask at 400 K carried a 4.6e5 wet-ramp entry but conserved matter to
      3.5e-18 mol and reported clean, because a species with no LIQUID still has
      a GAS holding for the projection to settle against. **That probe was too
      gentle, and item 70 is what a hot flask does with the same gate.**
    * a dry flask's LARGEST entry is not a gate at all: ``d(T)/d(liquid)`` at
      -2.2e6, which is an empty flask having no thermal mass. That is the
      superheated-flask fragility ``diagnose`` already names.

69. **DECLARED RATE ORDERS, AND THE KERNEL NEEDED NO HOT-LOOP WORK AT ALL.**
    ``builder.to_arrays`` has always emitted ``order`` as a matrix separate from
    ``delta``; it simply never had anything to put in it. So wall 2 was one
    field: ``ReactionTemplate.orders``, one exponent per SMARTS reactant SLOT,
    summed into the same matrix the multiset would have built.

    ⚠ **A DECLARED ORDER MAY NOT BE REVERSIBLE, and it is REFUSED at template
    construction.** ``detailed_balance`` derives the reverse from
    ``k_f/k_r = K(T)``, and that identity holds ONLY because the forward and
    reverse exponents ARE the stoichiometric coefficients -- it is what makes the
    ratio of the two rate laws equal the mass-action quotient. With an apparent
    order it is not, so a derived "reverse" would reach the WRONG equilibrium
    while looking exactly like one that does. The honest reading is simpler: an
    apparent order says the reaction is not an elementary step, and a
    non-elementary step has no reverse to derive. Negative orders are refused
    too -- inhibition is a saturation term, not a bare negative exponent.

    ⚠ **AND AN ORDER BELOW 1 IS A KNEE AT ZERO CONCENTRATION**, reported rather
    than refused: ``C**0.5`` has infinite slope at C = 0, the same shape as
    item 67. Half-order rate laws are real, so it is allowed and documented.

    **THE BURNER SHIPS.** ``reactions.sulfur_combustion()``, declaring
    ``(1, 1, 0, 0, 0, 0, 0, 0, 0)``: eight oxygens CONSUMED, one in the rate law.
    With O2 limiting the yield is **100.000% at A = 1e8, 1e9, 1e10 and 1e11** --
    the disqualifying A-dependence (86.5% vs 96.4%) is gone. ⚠ The failure mode
    at the slow end CHANGED, which is the real result: the old form STALLED
    ([O2]^8 never finished however long you waited), while this one is merely
    slow and FINISHES given ten times as long.

    ⚠ **BOTH PARAMETERS ARE HAND-AUTHORED and the rate law is APPARENT.** They
    are BOUNDED rather than fitted: ``A = 1e10 L/(mol s)`` is pinned to the order
    of the gas-kinetic COLLISION LIMIT so it cannot be dialled to taste, leaving
    ``Ea = 100 kJ`` as the only freedom. **The cost is a soft ignition threshold
    -- 68% at 500 K, more than real sulfur does below its ~523 K ignition point
    -- and that is asserted rather than tuned away.** A sharper knee needs
    A = 1e14, a thousand times the collision limit; buying a prettier threshold
    with an impossible pre-exponential is the wrong trade.

    The S2 workaround is still blocked by the element table, correctly, and the
    test is kept as the record of a road not taken.

70. ✔ **A DRYOUT BAND, and the burner walked into it. CLOSED by item 72 --
    read that one for the fix, and this one for what the bug was.** Sulfur
    boils at 717.8 K, so a burn run near that holds only a TRACE of condensate.
    If the trace lands inside ``DRYOUT_MOLES`` (1e-6 mol), THREE terms overlap:
    layer 1's evaporation is gated by ``wet``, the dry-flask branch by
    ``1 - wet``, and the mole fractions are floored on the same scale -- **so
    inside the band they sum to LESS THAN ONE and every activity is
    understated.** Measured, O2 limiting, A = 1e10:

    | T / K | liquid held | created O, relative | |
    |---|---|---|---|
    | 550 | 6.85e-03 mol | 1.8e-12 | |
    | 650 | 1.52e-03 | 1.1e-09 | |
    | **675** | **8.29e-07** | **2.3e-03** | IN BAND |
    | **690** | **5.43e-07** | **1.1e-01** | **reads 111% yield** |
    | 730 | 3.81e-07 | 2.0e-09 | |
    | 900 | 6.86e-08 | 1.7e-08 | |

    **It is a BAND, not a threshold** -- clean on both sides, wrong only inside --
    which is the signature of two gates meeting rather than of one bad one.

    ⚠ **AND THE DIAGNOSTIC THAT SEPARATES IT FROM ORDINARY ROUND-OFF IS WORTH
    MORE THAN THE MEASUREMENT.** The same burner shows a 1.7e-4 residual at
    600 K, nowhere near the band, and in a single run the two are
    indistinguishable. **They are told apart by REFINING:**

        600 K, round-off  atol 1e-9 1.70e-04 -> 1e-11 6.9e-12 -> 1e-14 -5.5e-14
                          60 chunks 4.79e-10
        690 K, the BAND   atol 1e-9 1.10e-01 -> 1e-11 5.0e-09 -> 1e-14  7.4e-04
                          60 chunks 5.25e-02

    **A ROUND-OFF RESIDUAL CONVERGES UNDER REFINEMENT; A STRUCTURAL DEFECT DOES
    NOT.** The band is non-monotone in ``atol`` and untouched by chunking.

    Same CLASS as item 67, **NOT the same fix**: lowering the mole-fraction floor
    MOVES the band to 730-900 K instead of removing it -- tried and measured, and
    it is the same three-attempt story item 25 records. It was REPORTED rather
    than patched for one session, on ``fragilities`` and not only ``diagnose``,
    because **the solve SUCCEEDS** -- ``diagnose`` runs only on failure and would
    never have been consulted.

    ⚠ **AND THE "LATENT" VERDICT THIS GATE CARRIED BEFORE THAT WAS ONLY AS GOOD
    AS ITS PROBE, which is the transferable part.** Item 68 checked DRYOUT_MOLES
    for membership in item 67's class, measured a dry flask at 400 K holding
    0.8 bar, found it conserved matter to 3.5e-18, and pronounced it latent. The
    SAME gate at 690 K with 7 bar and a CONDENSING species created 11% of its
    oxygen. **A gate's damage scales with what multiplies it**, so a latency
    verdict has to name the conditions it was taken under.

71. ⚠ **A TEST THAT ASSERTED A LUCKY SOLVER PATH, found by item 67 moving it.**
    `test_a_vapour_edge_conserves_matter` bounded ethanol's closure at 1e-12
    relative and its docstring claimed "machine precision", on the strength of a
    run that happened to close to **-4.3e-15**. The solid-gate fix moved the
    solver's path and it came back **-4.5e-11**, which looked like a regression.

    **The convergence diagnostic from item 70 settles it:**

        gate    atol 1e-9     atol 1e-11    atol 1e-13
        OLD     -4.293e-15     2.555e-11     3.494e-11
        NEW     -4.512e-11     2.556e-11     3.494e-11

    **The two gates agree to four significant figures once refined.** ~3e-11 is
    the CONVERGED error of that configuration and -4.3e-15 was a coincidence at
    the default tolerance. The new value is also insensitive to the gate's own
    constant across four decades (-4.512e-11 at tau = 1e-3 through 1.0), so the
    residual is the VAPOUR EDGE and not the gate at all.

    Bound is now `rel=1e-9`, with `abs=1e-12` KEPT alongside it: the absolute one
    is what catches created matter in a vessel holding nothing (water's 1.26e-6,
    which is what the test was written for), and `approx` takes the larger of the
    two -- so it reads 1e-12 for a species at zero and 3e-9 for one holding
    3 mol, which is what each is actually being asked.

    ⚠ **The rule: a tolerance tight enough to be luck is worse than no
    tolerance.** It fails on unrelated changes and says nothing when it passes.
    Suite at the time: **618 tests, all passing.** (Now **629**, after M0's two
    structural tests and M2's nine.)

72. ✔✔ **THE DRYOUT BAND IS CLOSED, AND THE FIX WAS THE CLAMP RATHER THAN THE
    GATES. Item 70 is down.** 690 K went **1.1e-01 -> 1.9e-11** created oxygen.
    Two changes, and the second one is the interesting one:

    **(a) THE 0/0 CLAMP WAS THE BUG.** ``x1 = nL1 / max(N1, DRYOUT_MOLES)`` put
    the mole-fraction floor on the SAME scale as the gate that multiplied it, so
    a flask holding less than DRYOUT_MOLES had x summing to **0.57** and every
    activity understated by that factor while both evaporation branches were live.
    It is now ``max(N1, MOLE_FRACTION_DENOM)`` with **MOLE_FRACTION_DENOM = 1e-30
    mol -- 24 decades below the gate and 21 below the solver's own atol**, so it
    can never be in contention and the mole fractions sum to 1 at every reachable
    holding. **A clamp that exists to avoid 0/0 must not double as a gate**, and
    the checkable form of that rule is: *the mole fractions of any layer that
    something is gated ON must sum to one.*

    ⚠ Layer 2 already satisfied it, by accident of SHAPE rather than of scale --
    its floor IS ``LAYER_EPS``, but its gate is a smoothstep at the same scale, so
    ``gate2`` is identically zero wherever the floor binds. Layer 1's gate was a
    RAMP at the same scale, so it was not. That is the whole difference.

    **(b) ⚠⚠ AND MAKING THE GATES DISJOINT -- WHICH IS WHAT THE WORK ORDER ASKED
    FOR, AND WHAT FIXED ITEM 25 -- IS WRONG HERE. MEASURED.** It closes the band
    (690 K -> 1.6e-13) and it breaks a condenser, because **disjointness leaves a
    DEAD ZONE where both halves are zero**, and for the flask's own liquid that
    pair is the ONLY phase-change channel. A condenser is precisely the thing that
    comes to rest at the scale:

        head charge stalled at 9.998e-07 mol   (a working charge is 1e-4)
        the pot lost its latent-heat sink
        THE REFLUX PLATEAU WENT 352.89 -> 370.39 K

    Same relocate-the-fight signature as the ramp, one vessel over. So the pair
    stayed COMPLEMENTARY -- one ``_smoothstep`` on two arguments, ``wet`` on N1
    because Raoult needs layer 1 to have a composition and ``dry`` on N1+N2
    because a flask holding all its liquid in layer 2 is not dry. Single liquid:
    ``wet + dry == 1`` exactly, so no dead zone and no double count. Two layers:
    ``dry <= 1 - wet``, so it can only ever under-count.

    ⚠ **THE RULE, AND IT IS NEW: WHETHER A GATE PAIR SHOULD BE DISJOINT OR
    COMPLEMENTARY DEPENDS ON WHETHER ITS DEAD ZONE IS SURVIVABLE.** Item 25's
    layer pair must be disjoint because its two halves OPPOSE each other, and its
    dead zone is harmless -- a trace layer with nothing acting on it just sits,
    and layer 1 carries the flask. This pair must be complementary because its two
    halves are ONE FLUX WRITTEN TWO WAYS -- ``a1*psat - p`` and
    ``min(psat - p, 0)`` cannot even have opposite signs, since the second needs
    ``p > psat`` and ``a1 <= 1`` then forces the first negative too -- and its
    dead zone stops the flask changing phase at all. **Both docstrings now carry
    the other's counter-example.**

    The ramp still had to go, for the reason LAYER_EPS and item 67 each record: its
    slope at zero is 1/DRYOUT_MOLES = 1e6, so an EMPTY flask carried a fictional
    -1e6 Jacobian entry on the dry branch. A smoothstep is zero AND FLAT at zero.

    **What it cost in hot-loop work: nothing.** Two expressions, same shape, same
    array form -- the third wall running for which asking "what uniform array form
    does this collapse to?" first meant there was no hot-loop work to do.

73. ⚠⚠ **WHAT IS LEFT AT 690 K IS THE DEPLETED REACTANT, AND ITS VALUE AT DEFAULT
    TOLERANCE IS LUCK -- INCLUDING THE OLD VALUES ITEM 70 TABULATED.** This is
    item 71's rule biting a second time, and it is why one invariant row moved.

    With O2 limiting the burner still reads ~1e-5 at 690 K. That is **not** the
    band. Three measurements:

    | | 690 K | 730 K |
    |---|---|---|
    | O2 limiting (ends at exactly 0.0) | 2.94e-05 | 5.23e-06 |
    | O2 in EXCESS (ends holding 8.4e-02) | **1.85e-11** | **1.12e-12** |
    | O2 limiting, atol 1e-12 | 6.04e-10 | 1.10e-10 |

    So it is the ordinary **stiff-reactant-at-zero** residual this project reports
    everywhere and which **M7 owns**; it CONVERGES under refinement where the band
    did not; and the evaporation path on its own is clean to 1.9e-11.

    ⚠ **AND NO SINGLE VALUE OF IT IS AN INVARIANT.** Nudge the charge of
    NITROGEN, which takes no part in the burn and cannot move a real conservation
    property -- only the solver's step selection:

        n(N2)     730 K dO     690 K dO
        0.0200     5.23e-06     2.94e-05
        0.0201     2.73e-04     3.46e-06
        0.0202     5.31e-06     1.22e-05
        0.0205     4.47e-04     1.00e-05
        0.0210     2.55e-09     9.76e-06

    **Five orders of magnitude from an inert species.** So item 70's "730 K
    2.0e-09, clean" was where the solver happened to land, and the row is
    **reported as a finding rather than retyped**. The burner test now asserts the
    two things that ARE stable -- exactness with nothing driven to zero, and
    convergence under refinement -- and asserts no tolerance on the rest.

74. ⚠⚠ **A GREEN SUITE IS NOT EVIDENCE THAT THE INVARIANTS TABLE STILL HOLDS,
    and `examples/wait_until.py` had been wrong by 60% for at least a session
    with its test passing throughout.** Found while checking M0's blast radius.

    | instant | table said | actually reads |
    |---|---|---|
    | until it passes 340 K | 564.18 s | **576.31 s** |
    | until it boils | 829.77 s | **1353.13 s** |
    | until the temperature steadies | 829.91 s | **1353.13 s** |

    The tests pin these at tolerances far looser than the digits the table quotes
    -- the reflux plateau is asserted at `abs=2.0` K against a value written to
    three decimals -- so the suite cannot catch a row drifting inside its own
    tolerance. **Re-measure a row before quoting it; do not infer it from green.**

    ⚠ **AND THE CHEAP WAY TO TELL "I MOVED THIS" FROM "THIS WAS ALREADY STALE",
    which is the transferable part.** The RHS resolves `_dryout_gates` and
    `MOLE_FRACTION_DENOM` from MODULE GLOBALS at call time, so the previous
    behaviour can be **monkeypatched back at runtime** and the same script run
    twice in one process. No file edit, so no risk of a half-reverted state, and
    the answer is a measured difference rather than a recollection. Here it read
    576.31 / 1353.14 under the OLD ramp and floor -- **0.00 s and 0.01 s from the
    new values**, the latter being the root solve's own tolerance. So the rows
    were stale BEFORE this session and are corrected rather than blamed.

    This is the third form of the same lesson: item 71 (a tolerance tight enough
    to be luck), item 73 (a residual whose value is set by where the solver lands)
    and now a row that drifted inside a loose assertion. **A number in that table
    is only as good as the last time it was actually run.**

75. ✔✔ **M1: THE COVERAGE INSTRUMENT WAS WRONG IN THREE WAYS, AND THE ONE THAT
    MATTERED WAS THE TAXONOMY.** Corrected baseline: **33/377 steps (8.8%) and
    4/173 routes template-ready**, from **14 templates** (8 in `library.py`, 6 in
    `electrolyte.py` — it knew only the first file, and said "10").

    ⚠ **THE HEADLINE: A REACTION CLASS MUST NAME A MECHANISM, BECAUSE A TEMPLATE
    IS SMARTS ON A MECHANISM.** `acid-base`, `redox`, `oxidation` and
    `deprotonation` were OUTCOME labels spanning several mechanisms each, so
    "does a template cover this class" had no answer. **32 rows of
    `route_steps.psv` re-labelled**; decision table in `data/catalog/README.md`.

    ⚠ **AND CREDITING THE SIX ELECTROLYTE TEMPLATES WAS NOT THE ONE-LINE EDIT IT
    WAS BILLED AS.** The predicted 21 → 46 steps needed `deprotonation` to be
    proton transfer. Five of its six rows are malonate/acetoacetate carbanions, a
    Wittig ylide and two enolates — the carbanion-generation capability that has
    NO template. **Crediting it would have made the instrument less trustworthy,
    which is the exact failure the milestone existed to prevent.** Measured 33,
    not 46, and the difference is real rather than pessimism.

    Two rules, both now in the catalog README:
    * **The class is the MECHANISM; whether a reagent is PRICED is a species
      question**, and the audit already counts those separately. Kjeldahl's
      boric-acid titration is `proton-transfer` even though boron has no oxyacid
      template — putting it in the class name would count one gap twice.
    * **A step's NAME can lie; its reactants cannot.** `williamson-ether` step 1
      is called "alkoxide formation" and reads `phenol + NaOH -> phenoxide`. It is
      a PHENOXIDE, so `phenol_dissociation` covers it.

    It also reconciled a contradiction in `MILESTONES.md`: `acid-displacement`
    was listed as covered AND as a top missing class. Both were right about
    different rows — 1 of 4 steps is proton transfer, 3 need a gypsum
    precipitation, i.e. **M3**.

    **The marginal-unlock table and greedy set-cover curve are now in
    `COVERAGE_REPORT.md`, and they revise the plan's own numbers**: 64 routes are
    one class away (was estimated 61) from **50 different classes** (46), the best
    single template unlocks **3** routes (6), twelve reach **30/173** (31) and
    twenty reach 43/173. ⚠ Splitting outcome classes into mechanisms necessarily
    LOWERS per-class unlock, so this was expected — the conclusion is unchanged
    and now measured: **there is no lever; plan for a target.**

    ⚠ **The curve's tie-break is load-bearing.** "Routes unlocked outright" hits
    zero after ~15 classes because every remaining route needs two or more, and a
    loop that stops there reports a curve that flattened because it gave up. When
    nothing unlocks a route alone, take the class appearing in the most remaining
    routes; those rows show `+0` honestly.

    Also fixed: a variable-shadowing bug in the summary print that reported
    **"20 compounds"** and coverage of **5520%**.

76. ✔✔ **M2: A STILL IS A PROTOCOL NOW. `SAVE_VERSION` 4 -> 5.** "Collect the
    fraction boiling between 351 and 355 K" was **unsayable**, not merely
    unimplemented: `World` -- the layer that saves, scripts and replays -- had no
    rig at all, so every coupled apparatus in this repo was assembled by hand in
    an example. Four parts, and MILESTONES was right that most of it is plumbing.

    * **`Scenario.edges`** (`EdgeSpec(kind, a, b, k)`, kinds `vapour` / `drain` /
      `thermal` / `meter`). The apparatus is saved DATA. `World._build_rig`
      resolves it; edge names are plain strings so a scenario stays readable JSON,
      the rule `TemplateSpec` and the event kinds already follow.
    * **`SWAP_RECEIVER`** -- re-point ONE END of an edge at another declared
      vessel. ⚠ It does not CREATE a vessel, deliberately: a world is (scenario,
      events, script), and a verb that conjured glassware would put part of the
      apparatus outside the scenario, which is the thing M2 set out to fix.
      Declare `receiver_1..n` on the bench and swap between them, which is also
      what a chemist does.
    * **`SET_EDGE`** -- open or close a tap. A dropping funnel is throttled, not
      moved, so it is a separate verb.
    * **`collect_fraction(vessel, edge, into, enter, leave, timeout, park)`** --
      wait for the band, swap in, wait, swap out.

    ⚠ **NONE IS A REAL STATE FOR `World.rig`.** With no edges the world keeps its
    ORIGINAL per-vessel stepping path exactly, so every number measured before
    rigs existed is bit-identical -- the guarantee `lle=False` and `losses=None`
    carry. A rig integrates every vessel as ONE stiff system: right for connected
    glassware, a needless expense for a bench of separate flasks. **Edges are the
    signal that the glassware is actually connected**, and the apparatus verbs
    REFUSE on a world without them rather than silently doing nothing.

    ## ⚠⚠ THE TWO THINGS THAT WERE NOT PLUMBING

    **(a) A CONDITION AND THE TRAJECTORY IT IS LOCATED ON ARE DIFFERENT THINGS,
    and this was a live wrong answer waiting to happen.** `World._wait_until`
    satisfied a wait by integrating the OWNER vessel ALONE and then advancing the
    others by however long that took. Exactly right for separate flasks; wrong for
    glassware, because **nearly all of a still head's heat arrives through the
    vapour edge**. MEASURED, same charge both ways: the coupled head crosses
    330 K, and the uncoupled head **never reaches it at all** -- it sits at its
    surroundings, 298.15 K, and times out. Every cut is called off that number, so
    a decoupled root would have quietly collected everything in the first
    receiver. Fixed with `RigIntegrator.step_until` (same contract and sign
    convention as the vessel's) plus `Rig.wait_until`, which compiles the
    condition against the named vessel and **lifts the root onto the rig's state
    vector by that vessel's slice**. Pinned in
    `tests/test_still.py::test_a_condition_on_the_HEAD_is_located_on_the_COUPLED_trajectory`.

    **(b) THE HEAD IS NOT THE CONDENSER, and conflating them is a silent
    failure.** A still head is the UNCOOLED junction where the thermometer sits;
    its temperature is set by the latent heat of vapour passing through, which is
    why "the head is at 351 K" says what is coming over. Put the thermometer in
    the condenser instead -- cold, UA=40 against a 288 K bath -- and it reads the
    COOLANT: it sat near 290 K for the whole run whatever was distilling, **every
    cut band missed, and the first receiver quietly collected the lot**. The rig
    is pot -> head -> condenser -> receiver, four stages, and the middle one
    exists only to be measured. ⚠ **The bands must be read off the head's own
    trace, not off a table of pure boiling points**: a three-component charge
    boils at its BUBBLE POINT, which climbs continuously as the pot depletes.

    ⚠ **AND A RECEIVER NEEDS `kla > 0`, which is worse in a rig than in a flask.**
    A receiver with `kla=0` leaves its gas block identically flat -- the fragility
    `check_state` already names -- and the receivers NOT currently connected are
    isolated blocks inside one coupled Jacobian. BDF's LU factorisation of it was
    **singular outright**, in `splu`. Same latent defect, promoted to fatal by
    being one block of a larger matrix.

    ⚠ **THE TRAP MILESTONES NAMED, AND IT DECIDED THE DESIGN: a cut is a
    DISCOVERED INSTANT, so the recipe stores the CONDITION and never the
    timestamp.** That is why `collect_fraction` is a scripted verb of its own
    rather than sugar over a scheduled SWAP_RECEIVER: an `Event` carries an
    absolute `t`, so building the swap from one would bake THIS run's crossing
    into the recipe, and a replay whose root landed elsewhere would either refuse
    to schedule in the past or -- worse -- swap at an instant it did not itself
    find. The swaps go through `World._swap`, which applies an Event WITHOUT
    queueing it. **A replayed distillation locates its own cut points**, and a
    test asserts no discovered time appears anywhere in the script entry.

    ⚠ A cut that never opens is a RESULT (`entered: False`), not an error -- a
    band above everything in the pot is an ordinary thing for a player to ask.
    And the tail cut is closed by its TIMEOUT rather than by a temperature,
    because once the pot runs down the head FALLS rather than climbing: `left:
    False` is the truthful report.

    ## ⚠ WHAT M2 DID NOT DELIVER, MEASURED

    **The heart cut is 0.523 mole fraction against a target of 0.85**, and it is
    an APPARATUS limit rather than a protocol one. The example is a simple still
    -- pot, one head, condenser -- i.e. about ONE theoretical plate, and one plate
    cannot reach 0.85 wherever the bands are put; moving them trades yield against
    purity along a curve that tops out below it. Purity comes from PLATES, and a
    plate here is just another vessel with a vapour edge up and a drain back
    down: **no engine work, only more edges.**

    ⚠ **AND THE FIRST COLUMN ATTEMPT FAILED, so do not assume it is a quick
    edit.** 3 and 5 plates chained vapour-up / drain-down: the head **never
    entered the band** (`entered: False`) and UNIFAC threw `overflow encountered
    in exp`, i.e. a plate's temperature left the range its correlations cover.
    Diagnosis: **column STARTUP.** A real column is flooded and brought to steady
    reflux before any take-off, and this one took off immediately, so the plates
    never established a liquid holdup or warmed into the band. Try flooding first
    (`SET_EDGE` the take-off to 0, run to steady reflux, then open it) -- which is
    exactly what the new verbs are for, and is itself a decent test of them.

    Also: the 0.85 figure in MILESTONES refers to a **50/50 ethanol/water** charge
    (a single receiver manages 0.655 there), not to the three-component example.
    ⚠ That pair AZEOTROPES at x = 0.888, so the target is tight by design.

77. ✔✔ **M2 IS FINISHED: A PLATE COLUMN REACHES 0.8544 MOLE FRACTION ETHANOL FROM
    A 50/50 CHARGE, 8 PLATES AT REFLUX RATIO 5, AND IT REPLAYS TO 0.000e+00.**
    `examples/plate_column.py`. MILESTONES was right that this needed no new
    physics -- a plate is a `VesselSpec` with a vapour edge up and a drain back
    down, and the ladder it makes is monotone and very nearly a theoretical stage
    per plate:

    | stage | pot | p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | head | cond |
    |---|---|---|---|---|---|---|---|---|---|---|---|
    | x(EtOH) | 0.492 | 0.562 | 0.611 | 0.652 | 0.687 | 0.719 | 0.747 | 0.772 | 0.794 | 0.812 | **0.828** |

    Cut: 0.2987 mol at **x = 0.8544**, containing 0.2552 mol of ethanol = 12.8% of
    the 2 mol charged. The purity is a **PLATEAU, not a peak** -- 0.845 in the
    first 50 s of take-off, 0.8538 after 2000 s -- so the band trades YIELD and
    not purity: a longer cut reaches **46.5% recovery at 0.8535**, measured. The
    azeotrope at x = 0.888 is what it cannot trade for.

    ⚠⚠ **BUT THE HEADLINE IS THAT THE FIRST COLUMN ATTEMPT'S PUBLISHED DIAGNOSIS
    WAS WRONG, AND THE SHIPPED M2 EXAMPLE WAS DISTILLING AT 3.09 BAR.** Item 76
    recorded the failure as column STARTUP -- plates never warmed into the band,
    fix by flooding at total reflux first. Flooding IS necessary and is done. It
    was not the bug.

    **The bug is that a still assembled in this project has NO OPEN END.** Every
    vessel is declared `k_vent=0` -- a pot must not boil its charge into the room
    -- and a receiver is reached only by a DRAIN, which moves liquid. So the gas
    phase of pot + plates + head + condenser is one sealed volume and heating it
    is heating a bomb. Measured, same 250 W and same charge:

    | | sealed | open (`k_vent=1` on the condenser) |
    |---|---|---|
    | `fractional_distillation.py`, t=100 s | **3.09 bar, pot 370.75 K** | 1.014 bar, pot 341.6 K |
    | ... and once the pot ran dry | **pot 548.15 K** | (run now ends before dryout) |
    | the column, 2 plates, t=300 s | **3.343 bar, pot 385.86 K, plates 384.8 K** | 1.014 bar, pot 352.97 K |
    | the column, 8 plates, t=300 s | **3.770 bar, pot 389.61 K** | 1.015 bar, pot 353.02 K |

    ⚠ **TALLER IS HOTTER, and that is why adding plates made the first attempt
    worse rather than better** -- 8 plates seal 2.40 L against 2 plates' 1.80 L
    and settle 4 K higher. That is what pushed a plate outside the range UNIFAC's
    correlations cover (the reported `overflow encountered in exp`) and put every
    stage ~30 K above a band chosen from a table of atmospheric boiling points, so
    `entered: False` was the only possible answer.

    ⚠ **The shipped example's published cuts were therefore taken on a pressurised
    trace**: bands `300-366 / 366-374 / 374-500` K are not the boiling points of
    anything in that flask. Vented, the head climbs 336 -> 341 -> 346 -> 352 ->
    366 K and then falls as the pot runs down, so the bands came down to
    `300-342 / 342-356 / 356-500` and the cuts moved: **0.4367 / 0.5562 / 0.0702
    mol, heart 0.459 ethanol** (was 0.060/0.287/0.580 and heart 0.523). Replay
    still 0.000e+00. Its timeouts were also cut so the run ends BEFORE the pot
    boils dry -- 250 W empties that 1.2 mol charge at ~280 s and the empty flask
    then runs to 548 K, which is the `diagnose`-named dry-superheat fragility.

    ⚠ **The transferable form is a DEFAULT that points the wrong way for
    glassware.** `VesselSpec.k_vent` is 1e3, so a *bench flask* is open and a
    *hand-assembled still* is not: its author has to turn exactly one vent back
    on, and nothing in the API says so. Checkable form: **a rig's gas phase needs
    somewhere to go, and a DRAIN is not it.** Pinned in
    `tests/test_still.py::test_a_still_with_no_open_end_is_a_SEALED_PRESSURE_VESSEL`.

    ## ⚠ THE ONE ENGINE FIX, AND IT IS ITEM 76(a) ONE LEVEL DEEPER

    **`temperature_steady` on a rig vessel was being answered by that vessel's OWN
    uncoupled derivative.** Every other condition in the vocabulary reads the
    STATE -- a temperature, a pressure, an amount -- so `Rig.wait_until` lifting
    the root onto the rig's vector by the owner's slice answers it exactly. This
    one reads the DERIVATIVE, and `compile_condition` builds it from
    `integ.make_rhs()` on the owner alone, which for a still head is the cooling
    rate of a small flask of hot ethanol standing in a cold room.

    MEASURED: a column at steady total reflux, head pinned at **351.22 K and
    unmoving to two decimals for 1200 s**, gives `temperature_steady(0.005)` a
    **TIMEOUT** on the lifted root and fires it in **0.0 s** on the coupled one. A
    protocol that floods a column and waits for it to settle -- exactly what the
    first attempt was missing -- could not be written. `Rig.wait_until` now builds
    this one kind against the rig's own RHS at the owner's temperature row.

    ⚠ **The rule, and it is the transferable part: it is not only WHEN a condition
    is located that belongs to the coupled trajectory, it is WHAT THE CONDITION
    COMPUTES.** Item 76(a) fixed the first half. A vocabulary of conditions is
    safe to lift onto a bigger state vector only while every member of it reads
    the state; the moment one reads a derivative, lifting silently changes the
    question. Both halves are asserted at one state in
    `test_temperature_steady_on_a_RIG_vessel_is_the_COUPLED_derivative`.

    ## ⚠ TWO MORE MEASUREMENTS, EACH OF WHICH KILLED AN OBVIOUS IDEA

    **(a) BOILUP IS A PLATE-EFFICIENCY KNOB, NOT A CLOCK.** Take-off rate is
    `boilup/(R+1)`, so turning the mantle up should be a free speed-up. It is not,
    twice over: the same 8 plates at the same R=5 plateau at **0.8538 at 250 W,
    0.8486 at 500 W** -- 500 W misses the target 250 W meets -- and the two runs
    cost the **same wall clock anyway (403 s vs 409 s)**, the faster take-off
    being paid for in stiffness. A plate here is a KINETIC stage, so more vapour
    through the same `kla` and the same holdup gets less time to equilibrate.
    Which is a real column's behaviour, and it means **this example cannot be made
    cheaper by pushing harder.**

    **(b) IN A GOOD COLUMN THE HEAD DOES NOT MOVE, SO THE HEAD IS THE WRONG
    INSTRUMENT FOR CLOSING THE CUT.** Across the entire ethanol take-off the head
    sits at **351.186 -> 351.188 K**. That flatness is what good rectification IS,
    and it means there is no signal there to cut on -- the earlier 4-plate attempt
    at a head band ran to its 3000 s timeout and collected 1.88 mol. The signal is
    the POT, whose bubble point climbs as it is stripped (353.08 -> 354.28 K), and
    `wait_until` works on any vessel in the rig, so the band goes there. ⚠ This
    does NOT weaken item 76(b): the head is still where the thermometer goes, and
    a *simple* still's head does move. It is the flip side -- **the better the
    column, the less the head has to say.**

    ## WHAT IT COST, AND WHAT WAS TRIED AND ABANDONED

    * ⚠ **`examples/plate_column.py` is ~13 minutes of saturated CPU** on 14
      coupled vessels and 21 edges, and **half of it is panel 4's replay**, which
      re-runs the whole protocol by construction. The **cold-start FLOOD dominates
      rather than the distillation**: ~155 s of wall clock for 135 s of simulated
      time, against ~0.12 s per simulated second once the column is running.
    * **Declaring the plates already warm (T=345 K) changes the flood by 1 s.**
      The transient is the PHASE CHANGE, not the heat-up, so there is no cheap
      version -- and no temptation to fudge the initial condition.
    * ⚠ **Sparsity DOES pay on a column, unlike the two-vessel rigs where
      `useful_sparsity` measured it as pure overhead.** A chain of vapour edges is
      banded, so `group_columns` finds **60 groups in a 238-column** Jacobian (8
      plates); 52 of 136 at 2 plates, 56 of 170 at 4. It grows ~4 groups per two
      plates while the state grows 34, so the Jacobian cost is nearly flat in
      column height. Nothing was changed to get this -- `useful_sparsity` already
      decides per rig, and this is the topology it was waiting for.
    * `tests/test_still.py` is 9 -> **13 tests, 2 min -> 4.4 min.** The extra
      four pin the mechanism at **0 and 2 plates**, deliberately: pressurisation
      needs no plates, a ladder needs two, and a flood is what costs wall clock.
      The 8-plate headline lives in the example.

    ⚠ **THE REFLUX RATIO IS TWO DRAINS OUT OF ONE CONDENSER, and that is why it is
    a declared number rather than an inferred one.** Both are first order in the
    same holdup, so they divide it exactly in the ratio of their conductances
    whatever the holdup settles at: `R = k_reflux / k_takeoff`. Total reflux is
    `k = 0` on one of them, which makes `SET_EDGE` the verb for opening the tap
    after flooding -- and the flooding protocol is the one M2's new verbs were
    asked for. No new edge kind was needed.

78. ⚠⚠ **M3 IS A DATA GAP, NOT A MODEL GAP, AND MILESTONES SAID THE OPPOSITE. A
    NAIVE Ksp ON TODAY'S TABLES RETURNS A NUMBER FOR 9 OF 13 MINERALS AND IT IS
    25-29 DECADES OUT WITH THE SIGN FLIPPING.** MILESTONES M3: "a lattice entry
    already exists... the data is largely there and this is a model gap." Measured
    before writing a line of the precipitation term -- which is the whole reason
    the rule *bound a mechanism arithmetically against the actual simulated state
    BEFORE writing code* exists, now paid for an eighth time:

    | mineral | dG_diss / kJ | Ksp | s pred / M | s meas / M | ratio |
    |---|---:|---:|---:|---:|---:|
    | rock salt | +272.4 | 1.9e-48 | **1.4e-24** | 6.15 | 2.2e-25 |
    | saltpetre | +315.4 | 5.6e-56 | **2.4e-28** | 3.51 | 6.8e-29 |
    | caustic soda | +242.3 | 3.5e-43 | 6.0e-22 | -- | -- |
    | slaked lime | +622.9 | 7.5e-110 | 2.7e-37 | -- | -- |
    | blue vitriol | **-21.5** | 5.8e+03 | **76.2** | -- | **sign flipped** |

    Blue vitriol's "solubility" is 76 mol/L, denser than the crystal it is
    dissolving from. **A zero reference does not BIAS a solubility product, it
    destroys it** -- nothing absorbs a sign flip, so there is no factor to
    calibrate and the data has to be fixed instead. This is the same shape as the
    fusion-law verdict `mineral_data` already records (407x too insoluble for
    NaCl, 11x too soluble for CaCO3, 6,445x of spread) but **twenty decades
    worse**, and unlike the fusion law it arrives with no warning attached.

    **The LATTICE half is sound and that is worth saying plainly**, because it is
    the half MILESTONES was right about: 13 minerals, solid-basis Hf/S0 from CRC,
    Gf DERIVED against the same element reference states, both halves of an entry
    from one database or no entry. Nothing there needs redoing.

    ## ⚠⚠ (1) A SPECTATOR CANCELS ONLY WHEN IT APPEARS ON BOTH SIDES

    `thermochemistry` prices `[Na+]`, `[K+]`, `[Ca+2]`, `[Mg+2]`, `[Fe+2]`,
    `[Cu+2]`, `[Zn+2]` as `ThermoData(0.0, 0.0, "spectator ion (zero reference;
    cancels from every equilibrium)")`. **For acid/base that is exact, and it is
    why the five pH invariants hold**: the cation appears unchanged on both sides
    of every proton transfer and drops out of the quotient. **A solubility product
    is the one consumer where it appears ONCE**, so the entire hydration Gibbs
    energy the zero stands in for lands directly in `dG_diss`. Conventionally
    ~262 kJ/mol for Na+, ~554 for Ca2+ -- **46 and 97 decades of Ksp**.

    ⚠ The transferable form, and it generalises past this milestone: **a
    convention chosen because a quantity cancels is only safe while every consumer
    cancels it.** The source string on those entries says "cancels from every
    equilibrium", which was true when it was written and became false the moment a
    Ksp was contemplated. A zero is not data; it is an assertion about the
    consumers.

    ## ⚠ (2) THE ANION HALF IS NOT AN AQUEOUS FORMATION VALUE EITHER

    `electrolyte`'s own docstring says it: every anion is back-calculated from a
    measured pKa against *this project's* water, `Gf(H3O+) = Gf(H2O)`, and "the
    resulting numbers are not literature aqueous values and are not labelled as
    such". They reproduce measured acidity exactly, which is what they are for.
    But the anchor is the acid in a hypothetical pure LIQUID standard state rather
    than in water, so **chloride reads -111.73 against a conventional aqueous
    -131.2**: 19.5 kJ/mol, **3.4 decades** -- on the half that is *not* the main
    problem. A Ksp is the one place the pKa basis and the CRC solid basis have to
    be subtracted from each other, and they cannot be.

    ## ⚠⚠ AND THE DATA CANNOT BE AUTOMATED OUT OF `chemicals`: IT RETURNS THE
    ## GAS-PHASE ION

    This project's rule is to source a number from `chemicals` and never from
    recall, so the obvious next move is a `tools/build_ion_data.py`. Measured,
    `chemicals` 1.5.2 for Na+ (CAS 17341-25-2): **`Hfs` None, `S0s` None, `Hfl`
    None -- and `Hfg` = +609343 J/mol.** That is the *gaseous* sodium cation with
    the ionisation energy in it, against an aqueous value near -240 kJ/mol.
    **850 kJ/mol of wrong, arriving as a float from a call that SUCCEEDS.** Ag+
    and Ba2+ return None everywhere, so a script that fell back to `Hfg` would
    price exactly the alkali metals -- the ones a chain uses -- and refuse the
    rest. Same trap as `chemicals` handing back this project's own Joback estimate
    as "data" and as an estimator used outside its domain: **the call succeeds, so
    only knowing what the number MEANS catches it.**

    ## WHAT LANDED, AND WHAT DELIBERATELY DID NOT

    * **`properties/solubility_product.py`** -- `Ksp` from a lattice Gf against an
      ion table, and it **REFUSES BY NAME on all 13 minerals**, naming the ion,
      which basis it is on, that the lattice half is sound (with its Gf and
      provenance, so nobody re-does that work), and the `chemicals` trap that is
      next in line. `lattice_verdicts()` returns the verdict as DATA so a test and
      a validation script pin it rather than prose doing.
    * The arithmetic is **written and tested** -- `dG = sum(ions) - lattice`,
      van't Hoff from the 298 K pair (`dCp = 0`, stated not hidden), and the
      stoichiometric root `s = (Ksp / prod nu^nu)^(1/sum nu)`. ⚠ Tested against a
      **synthetic** basis-consistent provider, deliberately: asserting against a
      remembered literature Ksp would put an unsourced number in a test and call
      it verified. So the test asserts the CODE and `validation/` will assert the
      PHYSICS when there is data to assert it against.
    * **`validation/solubility_product.py`**, four panels, seconds to run.
      `tests/test_solubility_product.py`, 7 tests, **0.32 s** -- no integration.
    * ⚠ **THE PRECIPITATION TERM WAS NOT WRITTEN, ON PURPOSE.** It is small and
      well-shaped: a stoichiometry matrix over ion indices plus a driving force in
      `(Q, Ksp)`, the same array form `KineticArrays` already has, writing the
      SOLID block and gated on the solid being present the way `_avail` already
      gates dissolution. ⚠ It cannot be a template -- a template's `phase` is
      liquid or gas and no reaction writes the solid block -- so it is a new term.
      Writing it now would have wired a 25-decade number into the RHS on 9 of 13
      minerals, silently.

    **So M3's order is now: (1) a curated aqueous-basis ion table, cations AND
    anions, one compilation, provenance per value, kept separate from the
    pKa-derived entries so nothing mixes them; (2) the term; (3) the three
    `acid-displacement-precipitating` steps M1 re-labelled become template-ready.**
    One of the four "done when" clauses -- an unpriced lattice refuses by name --
    is done.

79. ✔✔ **M3 IS DONE, AND THE BLOCKER ITEM 78 CALLED A HAND-CURATION JOB TOOK
    TWENTY MINUTES BECAUSE THE DATA WAS ALREADY INSTALLED. A METATHESIS
    PRECIPITATES: 0.01 mol of AgCl out of AgNO3 + NaCl, 1:1, conservation report
    empty, supernatant at sqrt(Ksp).**

    ## ⚠⚠ THE HEADLINE, AND IT IS A CORRECTION TO ITEM 78

    Item 78, MILESTONES M3, `chemsim-solubility-product` and this repo's own
    `validation/solubility_product.py` all recorded the same thing: *the ion
    table cannot be automated out of `chemicals`, which has no aqueous ion values
    and hands back the GAS-PHASE ion (`Hfg(Na+)` = +609343 J/mol against an
    aqueous −240 kJ/mol), so M3's next step is hand-curation.*

    **That was true of the FUNCTIONS and false of the PACKAGE.** `chemicals`
    1.5.2 ships, and no accessor function reads:

        chemicals/Electrolytes/CRC Thermodynamic Properties of Aqueous Ions.tsv

    173 ions, CAS-keyed, `Hf(aq)` / `Gf(aq)` / `S(aq)` / `Cp(aq)`, ONE
    compilation, with the `H+` row carrying **0 / 0 / 0 / 0** — i.e. the
    conventional `Gf(H+,aq) = 0` scale, stated by the table rather than assumed.
    Exactly the "curated aqueous-basis ion table, cations AND anions, from one
    compilation" that item 78 specified, sitting inside the package this project
    already depends on.

    ⚠ **THE TRANSFERABLE FORM: A REFUSAL FROM AN API IS NOT EVIDENCE THAT THE
    DATA IS ABSENT.** This project has a hard-won rule that a *successful* call
    can be a wrong answer — `chemicals` handing back a Joback estimate as "data",
    an estimator used outside its domain. This is its **mirror image** and it had
    no rule: item 78 asked the accessors, got `None`, and believed it. Both are
    fixed the same way — look at what the source actually CONTAINS, not at what
    its interface says. The cost was a milestone re-planned around work that did
    not need doing.

    ## THE ION TABLE, AND A CROSS-CHECK THAT PROVES THE BASIS RATHER THAN THE SUM

    `properties/ion_data.py`, generated by `tools/build_ion_data.py`: **58 ions**,
    58 of 59 candidates. Two independent checks, both refusals rather than
    warnings:

    * **IDENTITY.** The SMILES is the only hand-written half of an entry, so
      RDKit's element counts and formal charge must equal the ones parsed out of
      the CRC formula string. **It caught a typo immediately** — nitrite written
      `[O-][N+]=O`, which is a neutral N-oxide, not NO2⁻.
    * **VALUE.** `Gf` is re-derived from that same row's `Hf` and `S(aq)` against
      the element reference entropies in `element_data` — the basis
      `mineral_data` derives a lattice `Gf` against:

          ion of charge z:  elements + z H+(aq) -> ion + (z/2) H2(g)
          dS_f = S(ion,aq) + (z/2) S0(H2) − sum_el nu_el S0(el, ref state)

      ⚠ **The `(z/2) S0(H2)` term is what makes this a check on the BASIS and not
      on arithmetic.** It exists only because the convention settles the electron
      against half a hydrogen molecule and sets `S(H+,aq) = 0`. Drop it and a
      singly charged ion misses by **T·S0(H2)/2 = 19.48 kJ/mol exactly** — a
      quantity no slip produces. Keep it and **every accepted entry closes to
      within 0.85 kJ/mol, worst case Sr2+**, against a 1.0 tolerance that is five
      times the tabulation's own rounding floor (Hf/Gf to 100 J/mol, S to 0.1
      J/(mol K)). An entry passing has been *shown* to be on the conventional
      aqueous scale.

    ⚠ **KEPT STRUCTURALLY SEPARATE FROM `electrolyte`, AND A TEST ENFORCES IT.**
    Chloride is −131.20 here and −111.73 there; neither is wrong and subtracting
    one from the other is 3.4 decades of Ksp. Neither module imports the other,
    `solubility_product` takes a `Mapping[str, AqueousIon]` and **refuses a
    `ThermochemistryProvider` by name** — which matters because that provider
    would have *answered*.

    ## WHAT IT PRODUCES, AGAINST SOLUBILITIES THAT WERE ALREADY IN THE REPO

    `mineral_data.fusion_law_bound` carries a measured 298 K solubility for five
    salts, entered long ago to CONDEMN the fusion law and untouched since. Two
    tables subtracted, the stoichiometric root taken, IDEAL activities, nothing
    fitted anywhere:

    | mineral | log10 Ksp | s pred / M | s meas / M | ratio |
    |---|---:|---:|---:|---:|
    | rock salt | +1.57 | 6.093 | 6.15 | **0.99** |
    | potash | +5.10 | 31.48 | 8.03 | 3.92 |
    | soda ash | +0.83 | 1.187 | 2.06 | 0.58 |
    | saltpetre | −0.01 | 0.988 | 3.51 | 0.28 |
    | calcite | −8.35 | 6.67e−05 | 1.40e−04 | 0.48 |

    **Every one inside a factor of 4, across 4.4e4× of measured solubility** —
    against item 78's 25–29 decades. That is M3's "at least three salts within a
    stated factor" and **the stated factor is 4**.

    ⚠ **THE RESIDUAL FACTOR HAS A NAME AND IT IS NOT TUNING: gamma.** These are
    infinite-dilution values and `solubility()` assumes activity coefficients of
    1. The reductio is in the same table's tail: **caustic potash comes out at
    2.2e5 mol/L**, which is the ideal law extrapolated ten decades past where it
    means anything. So `Ksp` is the product and **`solubility()` is a SCALE** —
    `SolubilityProduct.dilute` reports which side of `DILUTE_LIMIT` a result is
    on, and the engine term consumes `Ksp` and never `solubility()`.

    ## THE TERM: WHAT SHAPE IT TOOK, AND THE ONE LIMIT IT CREATES

    `PrecipitationArrays` in `vessel_integrator`, built by
    `vessel.build_precipitation_arrays`. Item 78 predicted the shape correctly:
    a stoichiometry matrix over ion indices plus a `(Q, Ksp)` driving force, and
    it cannot be a template because a template's `phase` is liquid or gas and no
    reaction writes the solid block.

    ⚠⚠ **THE SOLID BLOCK HOLDS THE IONS, NOT A LATTICE SPECIES.** AgCl(s) is one
    mole of `[Ag+]` and one of `[Cl-]` in the solid block. That buys three things
    for nothing: conservation is exact by construction (matter only moves between
    blocks — the report is empty and every total holds to 1e-12), no new species
    enters the network, and the existing dissolution law never touches them
    because `solidifies` is False for every ion.

    ⚠ **AND IT MEANS THE SOLID BLOCK IS AN ION INVENTORY RATHER THAN A SET OF
    DISTINCT CRYSTALS** — where two lattices share an ion, solid chloride cannot
    be attributed between them. The bound that follows is `units = min_i
    nS_i/nu_i`: **a lattice can only dissolve while EVERY one of its ions is in
    the solid**, so a lattice that never precipitated can never dissolve (tested:
    solid Na+ under water with no solid Cl− is inert). What is NOT bounded is how
    much two coexisting solid lattices sharing an ion may each claim. **Reported
    as a latent fragility, not refused** — reaching it needs two sparingly
    soluble lattices with a common ion crystalline at once.

    **The form, and why the root is taken.** `Q = prod c_i^nu_i` spans decades
    faster than a concentration does (c³ for a 2:1 salt), so the driving force is
    written on the root: `drive = k_diss * V_liquid * (Q^(1/N) − Ksp^(1/N))`,
    both terms concentrations in mol/L. Same shape as the dissolution term one
    block up. ⚠ **`k_diss` is REUSED rather than a new constant invented** —
    crystal growth and dissolution are the same interfacial process, the vessel
    already declares that knob, and a second one would need a bound this project
    has no data to give it.

    **The gate question was asked before the code was written** (HANDOFF 72).
    Precipitation ungated, matching the molecular-solid branch's stated design
    ("anything can nucleate"); dissolution `_avail`-gated. So it is the
    SOLID_GATE_TIME arrangement and **not** the disjoint `_layer_gates` one, and
    there is no dead zone: with no solid and an undersaturated solution the flux
    is zero because there is nothing to dissolve, which is exact rather than
    gated.

    ⚠ **LAYER 1 ONLY, and that is not laziness** — `split_phases` refuses to put
    an electrolyte in two layers, so every ion is in layer 1 by construction.

    ## ⚠ THE PREDICTION IN `thermochemistry` DID NOT COME TRUE, AND WHY MATTERS

    The spectator-cation block carried a standing warning: *"a SOLUBILITY PRODUCT
    would end it — calcium and carbonate would appear on opposite sides of a real
    equilibrium, so their zeros would stop cancelling."* **M3 landed and the five
    pH invariants are unmoved.** The prediction assumed the Ksp would be computed
    from that table; item 78 measured that it CANNOT be, so the term is built on
    `ion_data` − `mineral_data` and consumes the Ksp as a NUMBER, never reading a
    Gf from the provider. The cation still appears in no equilibrium the kernel
    evaluates.

    ⚠ **So the licence is SHARPER now, not weaker: a zero is safe while no
    consumer reads it ONCE.** Electrochemistry still would break it. And the
    accident is worth naming — *the failed first attempt is what forced the
    separation of bases that saved the invariants.* Three cations were added on
    the same argument (`[Ag+]`, `[Ba+2]`, `[Pb+2]`) so a metathesis has something
    to drop.

    ## AN ELEMENT-FLOOR BUG THE NEW WORK FLUSHED OUT, ON THE DEFINITIONAL ZERO

    The ion cross-check needs the entropy of the metal an ion forms FROM, so
    `REFERENCE_STATES` gained sixteen elements (Mg Al Mn Ag Ba Pb Li Rb Cs Sr Cr
    Co Ni Cd Tl, and Sn). ⚠ **Tin is REFUSED, and the check that caught it is
    free and exact.** CRC's row for 7440-31-5 carries `S0s = 44.1` with **`Hfs =
    −2100 J/mol`** — that is GREY tin; the reference state is WHITE tin at
    `S0 = 51.18`, which WEBBOOK has under the same CAS. Taking the CRC entropy
    would have put 7 J/(mol K) — 2 kJ/mol of Gf — into every tin derivation,
    silently.

    `reference_entropies()` now refuses any reference state whose own database
    does not price it at **Hf = 0 exactly**, which is that module's whole thesis
    used as a detector. Same class as Br2 and I2 being pinned to 0.0 before
    `element_data` existed: **an allotrope mismatch that only the definitional
    zero can see.** 32 reference states established, 1 refused by name.

    ## COVERAGE: 4 → 7 TEMPLATE-READY ROUTES, 33 → 41 STEPS

    `precipitation-metathesis` and `acid-displacement-precipitating` are credited
    in `validation/catalog_coverage.py`, **to a TERM rather than a template** —
    `N_TEMPLATES` is deliberately not incremented.

    ⚠ **The M1 standard was applied before crediting them**, because that is the
    failure that instrument exists to prevent. `deprotonation` was refused credit
    for the dissociation templates because five of its six rows are carbanion
    generation wearing the wrong label — one class, several mechanisms. These two
    are not like that: every row is a double displacement dropping an insoluble
    salt, which is one mechanism and exactly what the term does.

    ⚠ **And a class being covered is a MECHANISM claim.** Of the five
    `precipitation-metathesis` rows, AgI and AgCl price today; **sodium
    bicarbonate and Prussian blue have no lattice entry, and chrome yellow
    (PbCrO4) is REFUSED by `mineral_data`** for want of an S0s in any database
    shared with its Hfs. First time a named target has been lost on the LATTICE
    half rather than the ion half. `mineral_data` went 13 → 25 entries (AgCl,
    AgBr, AgI, AgNO3, BaSO4, BaCl2, CaSO4-as-anhydrite, PbSO4, PbI2, CaF2, ZnS,
    Mg(OH)2), and quicklime now refuses on `[O-2]` — **which is chemistry, not a
    gap: CaO does not dissolve to Ca2+ + O2−, it hydrates to Ca(OH)2.**

    ⚠ Note the name: **anhydrite, NOT gypsum.** M1's three
    `acid-displacement-precipitating` steps want the DIHYDRATE; this is the
    anhydrous lattice, which is what CRC prices and what an anhydrous engine can
    model.

    ## TWO NUMBERS MEASURED RATHER THAN ASSUMED

    * ⚠ **"Precipitation made it 2× slower" is true and misleading.** On the
      metathesis flask, yes. Hold the chemistry fixed — same flask, nothing
      supersaturated — and the term costs **11% (0.134 s vs 0.121 s)**. The rest
      is AgCl actually crashing out, which is stiff work the flask was not doing
      before and which no array-code tightening removes.
    * ⚠ **DO NOT READ THE TEMPERATURE RISE OFF A LONG SINGLE CALL.** The
      insulated metathesis warms **0.1578 K against 0.1577 K predicted** from the
      two tables at t = 1200 s, and converges (rtol 1e−9 moves it 0.0001 K). The
      SAME flask taken to 3600 s in ONE call reads **0.038 K — with the extent
      unmoved at 0.0099866 mol**, so it is not the chemistry. Chunking the run
      recovers it exactly, so does rtol 1e-9, and an undisturbed adiabatic flask
      holds its temperature to 1e-4 K over the same span — so it is the
      integration of the TAIL. ⚠ **Whether that tail behaviour PREDATES this term
      was NOT established, and is recorded as a hypothesis rather than claimed.**
      The plausible mechanism is generic (an insulated flask 0.16 K above an open
      room loses the excess to evaporation, and BDF weights T against
      `rtol * 298`), but the control — a flask STARTED 0.16 K warm with no
      precipitation — did not finish inside two minutes, because the gradient
      itself makes it stiff. **`Chunking is part of the recipe`, one level deeper
      than the UI found it**, holds either way.

    ## WHAT M3 DELIBERATELY DID NOT DO

    ⚠ **No nucleation barrier / metastable zone**, which M3 offered to bundle so
    seeding becomes a mechanic. The code is three lines — hold the flux at zero
    until the saturation ratio passes S_crit — and **S_crit is a measured,
    substance-specific width this project has no source for.** Inventing it would
    be exactly the hand-tuned constant the sulfur burner's collision-limit A
    exists as the counter-example to. Refused, not forgotten.

    **Files:** `properties/ion_data.py` (new, generated), `tools/build_ion_data.py`
    (new), `properties/solubility_product.py` (rewritten), `mineral_data.py` +
    `element_data.py` (regenerated), `thermochemistry.py` (+3 spectators, the
    prediction corrected), `numerics/vessel_integrator.py` (`PrecipitationArrays`,
    the RHS term, `CONC_FLOOR`), `vessel/vessel.py` (`build_precipitation_arrays`,
    `Vessel.precipitation`), `validation/solubility_product.py` (rewritten, 5
    panels, seconds), `validation/catalog_coverage.py`,
    `tests/test_precipitation.py` (new, 14 tests, 3.7 s),
    `tests/test_solubility_product.py` (rewritten, 18 tests, 0.6 s).

80. ✔✔ **M4 IS DONE, IN THE ORDER THE MEASUREMENT PUT IT: THE FLAG FIRST, THE
    MATCHER SECOND. A FLASK CAN NO LONGER BE TOLD IT IS ONE STABLE PHASE ON THE
    STRENGTH OF A GAMMA THAT WAS NEVER COMPUTED, AND ORGANIC COVERAGE IS
    730 -> 764 OF 1155 (63.2% -> 66.1%).**

    ## ⚠⚠ THE HEADLINE: SILENCE WAS NOT A NEUTRAL DEFAULT, IT WAS AN ARGUMENT

    A neutral species with no UNIFAC decomposition is held at gamma = 1. The
    framing everywhere in this project was that this is a *silent* error, and
    that undersells it. `numerics/lle.py` has always said, as a virtue, that **an
    ideal liquid never splits** -- the tangent-plane test returns "stable" for
    free with no group parameters. Put the two together and the omission is not
    noise around the right answer: **everything held ideal argues for one phase,
    and the answer it argues for is exactly the one that used to be returned as
    the empty string.** `Vessel.lle_report()` returning "" was a foregone
    conclusion wearing the clothes of a finding.

    It now says so. `Vessel.held_ideal(layer)` is the quantity; `lle_report()`
    carries it in all three branches, including -- and this is the one that
    mattered -- the stable-single-phase branch that used to return "".

        this liquid is stable as one phase -- but 14.3% is NEUTRAL species with
        no UNIFAC decomposition, held at gamma = 1 rather than computed
        (O=S(=O)(O)O 0.143). An ideal liquid never splits, so that verdict is
        the one the missing model was always going to give

    ⚠ **AND THE TWO-LAYER CASE PRINTS THE SIGNATURE OF THE LIE NEXT TO THE
    WARNING.** Water/toluene/sulfuric acid comes out with H2SO4 at **0.058 mole
    fraction in BOTH layers**, because equality of activity with gamma = 1 on
    both sides of an interface is equality of MOLE FRACTION. That is the same
    failure the Born term was built to fix for ions (item 28), still running for
    neutrals, and it is now visible rather than inferable.

    ## THE THRESHOLD WAS BOUNDED ARITHMETICALLY, AND THE BOUND SAID SOMETHING

    Water/toluene 3:1 at 298.15 K and at the 358.31 K of the steam distillation,
    a third component added at mole fraction `f`, the tangent-plane test run
    twice -- once with that component modelled, once with it forced ideal -- and
    the displacement of the converged trial composition measured. Fifteen third
    components.

    ⚠ **THE SLOPES DO NOT SCATTER, THEY SPLIT IN TWO, AND THE BOUNDARY IS WHICH
    LAYER THE SPECIES BELONGS IN.**

    | held ideal | d(displacement)/df | |
    |---|---:|---|
    | acetone, ethers, esters, alcohols, DMSO | **0.03 - 0.25** | belongs in the MAJOR layer |
    | DCM, chloroform, benzene, hexane, cyclohexane, heptane | **0.99 - 3.46** | belongs in the MINOR layer |

    The mechanism is specific and is not "it gets the wrong gamma". Look at
    `activity_coefficients`: `xs = np.where(active, x, 0.0)` and then
    renormalise. **A species held ideal is DROPPED OUT OF THE GROUP COMPOSITION
    every other species' gamma is computed against.** For a cosolvent sitting in
    the bulk aqueous layer that is a perturbation. For a hydrocarbon that ought
    to DEFINE the organic layer, it is kept out of the layer it defines, and the
    tie line moves by 2-3.5x its own mole fraction.

    ⚠ **AND THERE IS NO DEAD ZONE. The displacement is LINEAR in `f` down to the
    smallest `f` measured (0.0005), so there is no fraction below which the model
    becomes correct -- only one below which the error is too small to print.**
    That is what makes this threshold a REPORTING decision, and it is the honest
    way to state it. `lle_report` prints layer mole fractions to three decimals,
    so:

        IDEAL_TIE_LINE_SENSITIVITY = 3.46      worst measured (heptane, 298 K)
        IDEAL_FRACTION_REPORT      = 0.003     = 0.01 / 3.46

    i.e. the flag fires exactly where the lie can move a printed digit. For scale
    at the other end: sweeping to `f = 0.6`, the stable/unstable **verdict** never
    flipped below an ideal mole fraction of **0.44**. So 0.003-0.44 is "these
    numbers are soft" and past 0.44 would be "this answer may be wrong".

    ⚠ **IONS ARE NOT COUNTED, AND `ActivityArrays.report()` NOW LISTS THEM
    SEPARATELY TOO.** An ion at gamma = 1 is a stated policy with the Born term
    doing the part that decides partitioning; a neutral at gamma = 1 is a gap.
    Running them together in one list made the gap look like the policy, and
    counting ions in the flag would have fired it on every electrolyte in the
    project and buried the case it exists for. The mask is `~gamma_active &
    ~ionic`.

    ## THE MATCHER HALF: TWO FIXES, AND THE SECOND ONE'S SAFETY IS AN ORDERING

    * **(a) THE KETONE SMARTS, +14.** `CH3CO`/`CH2CO` are ketone subgroups whose
      conventional patterns leave the carbonyl carbon unconstrained, so
      `[CX4;H3][CX3](=O)` matched ethanal's CH3-CHO, won the greedy pass by being
      the larger match, and stranded the aldehyde hydrogen. It cost the entire
      aliphatic aldehyde series, ethanal through dodecanal. Two `;H0`, added to
      the existing `_SMARTS_CORRECTIONS` mechanism, ketones verified unmoved.
      ⚠ The module docstring's claim that our patterns *are* thermo's is now
      corrected -- there are ten documented divergences (nine SMARTS, one priority) and
      `test_only_the_documented_patterns_differ_from_the_oracle` enumerates them.

    * **(b) A BACKTRACKING FALLBACK, +20.** Priority says which group is
      PREFERRED, not which is POSSIBLE, so greedy can eat an atom the only
      workable cover needed elsewhere. `fragmentation._search` is a depth-first
      search over covers -- settle the lowest unclaimed atom, try every match
      covering it in priority order -- with the running atom tally bounded by the
      formula at every node.

    ⚠⚠ **WHAT MAKES (b) SAFE IN A MATCHER JOBACK ALSO USES IS NOT WHAT IT FINDS,
    IT IS WHEN IT RUNS: only after the greedy pass has been REFUSED.** For any
    molecule that fragments today the search is unreachable, so it can turn a
    refusal into an answer and can never turn one answer into another. Measured
    over the whole catalog: **Joback unmoved at 1057 species, zero gained and
    zero changed**; Benson does not use this matcher at all. That is what let a
    new search algorithm go into a shared code path without re-validating the
    project around it.

    ⚠ **AND A SEARCH THAT RUNS OUT OF BUDGET REFUSES WITH A DIFFERENT MESSAGE.**
    "I did not find a cover" is not "there is no cover"; conflating them would be
    this project telling itself the published table is smaller than it is.
    Measured, nothing comes close: 517 searches over the catalog, deepest
    SUCCESS 18 nodes, most expensive REFUSAL 718, budget 20 000, total search
    time 0.01 s of the 0.70 s the catalog takes to fragment.

    ## ⚠ THE CEILING WAS A MEASUREMENT OF `thermo`, AND WE STOP THREE SHORT ON PURPOSE

    The planned ceiling was 767 (66.4%), being what thermo's backtracking matcher
    reaches on the identical patterns. We reach **764**, and the three species we
    still refuse are three species thermo gets **by counting hydrogens off the
    MOLECULE instead of off the GROUP** -- so a group's R and Q get applied
    outside the structure they were fitted to:

    | species | thermo says | why we refuse |
    |---|---|---|
    | PTFE repeat unit `FC(F)C(F)F` | `CF2 x2` | those carbons each carry an H |
    | 5-HMF `O=Cc1ccc(CO)o1` | `FURFURAL + CH2O` | FURFURAL is the WHOLE furfural molecule; this ring carbon has lost its H |
    | methoxy radical `C[O]` | `CH3O` | a radical oxygen is not an ether oxygen -- caught by one of our own documented pattern corrections |

    **A refusal is the right answer three times, so 764 is our ceiling and not a
    shortfall against 767.** The transferable form: *a number measured off
    another implementation is a measurement of that implementation, not a target.*

    ## WHAT IS STILL MISSING, NAMED BY ATOM ENVIRONMENT

    391 of 1155 organics still have no decomposition and
    `validation/unifac_gap.py` PANEL 2 names them by unassigned atom
    environment: 171 carbonyl oxygens outside the ketone/aldehyde/ester/acid/
    amide set (anhydrides, acid chlorides, ureas, carbonates), 75 sulfonyl
    oxygens, 91 aromatic nitrogens outside a pyridine RING, nitrate esters,
    phosphates. **None of that is an oversight -- it is the edge of a 1975 table,
    and going past it means a different model (Dortmund, NIST-UNIFAC) with its
    own combinatorial term, which is the basis error M3 exists as the warning
    about.**

    ## ⚠ A LATENT FRAGILITY THIS EXPOSED, REPORTED RATHER THAN BUNDLED

    Giving acetaldehyde a decomposition puts the `CHO` subgroup into the
    benzoic-acid prep's group basis, and the prep's tests started emitting
    `RuntimeWarning: overflow encountered in exp` from
    `activity.activity_coefficients`, followed by NaN through three matmuls.

    **The offending pair is not the new one.** `psi = np.exp(-a / T)` overflows
    for the PSRK quadratic pair **`H2O <-> N2`** (a = -3123.4 + 20.683 T -
    0.019561 T²) at **every T below 4.28 K** -- and the RHS's own temperature
    clamp is **`T_MIN = 1.0`**, which sits inside that band. So it fires whenever
    `num_jac` probes the temperature column hard and the basis holds both water
    and nitrogen, which is most aqueous flasks open to air. The a_mn extremes are
    byte-identical before and after M4; the change only made a standing test
    reach the probe.

    ⚠ **AND IT IS MEASURED INERT, WHICH IS A DIFFERENT CLAIM FROM "IT LOOKS
    HARMLESS".** Clipping the exponent to ±700 changes **nothing**: the prep
    returns the same acetic acid to six digits (0.00666923), the same wall time
    (43 s against 40 s, noise) and the same conservation residual. The NaN lands
    only in BDF steps that were going to be rejected.

    ⚠ **So the slowdown is NOT the NaN.** The same prep went **22.7 s -> 40.3 s**,
    and holding the code fixed while changing only the chemistry attributes 100%
    of that to acetaldehyde having a real gamma -- the flask got stiffer, the
    code did not get slower. Last session's rule 3 running in the other
    direction, and the trap is that *"my change made X appear" and "X is what
    made it slower" look like one claim.*

    ## A ROUND-OFF THAT LOOKED LIKE A REGRESSION, AND THE LADDER THAT SAID NO

    At DEFAULT tolerance the same prep's `conservation_report` went from three
    species of projection round-off (worst `HSO4-` 5.49e-05 mol) to one
    (`[OH3+]` **1.88e-03 mol**) -- a worst case 34x larger, which reads as a
    regression. It is not. Both states were run down a tolerance ladder,
    `run(7200)` on `BENZOIC_ACID_PREP.pot(net, air=True, lossless=True)`:

    | rtol / atol | BEFORE worst residual | AFTER worst residual |
    |---|---|---|
    | 1e-6 / 1e-9  | `HSO4-` 5.49e-05 | `[OH3+]` **1.88e-03** |
    | 1e-7 / 1e-10 | **FAILED: infs or NaNs** | `[OH3+]` **6.41e-02** |
    | 1e-8 / 1e-11 | `HSO4-` 1.31e-08 | `HSO4-` 1.48e-07 |
    | 1e-9 / 1e-12 | `[OH3+]` 4.24e-08 | `[OH3+]` 1.39e-07 |

    ⚠⚠ **IT CONVERGES -- SO IT IS A TOLERANCE ARTEFACT, NOT A DEFECT -- BUT IT IS
    NOT MONOTONE, AND THAT IS THE PART WORTH KEEPING.** The 1e-7 rung is
    **34x WORSE than the 1e-6 rung** in the AFTER state and OUTRIGHT FAILS in the
    BEFORE one. A projection residual on a species held near zero is
    luck-of-the-step, so **two default-tolerance residuals are not a like-for-like
    comparison and the "34x" framing was reading signal into scatter.** By 1e-8
    both states are at 1e-7--1e-8 and the difference between them is nothing.
    ⚠ Note also which way that table points: the state that fails at 1e-7 is the
    OLD one. This pot's delicacy at tight tolerance pre-dates M4.

    ⚠ **AND THE OPPOSITE CORRECTION ON THE ANSWER ITSELF.** Comparing across
    RUNGS suggested the acetic acid was moving inside the solver's own scatter.
    Comparing CONVERGED values does not: each state agrees with itself between
    1e-8 and 1e-9 to ~5e-09 absolute, and the two converged answers are

        BEFORE 0.006671076715      AFTER 0.006669628012

    -- a difference of 1.449e-06, **0.0217%, which is 282x the convergence
    noise.** So acetaldehyde gaining a real gamma DOES move this prep, by a fifth
    of a tenth of a percent, and it is resolved rather than inferred.
    ⚠ *Compare converged values, never one rung against another rung.*

    **Not fixed here.** The precedent for the fix is already in the same file --
    `gamma_ref_range` clamps T for the reference-state term precisely because
    PSRK's quadratic gas parameters go wrong quickly outside their window, and
    the a_mn matrix has the same problem with no such clamp -- but the activity
    kernel is the hottest code in the project and touching it needs the full
    suite behind it as a deliberate decision, not as a side effect of a
    fragmentation change.

    **Files:** `properties/unifac_data.py` (2 SMARTS corrections, docstring claim
    corrected), `properties/fragmentation.py` (the search; greedy pass unchanged
    and now shares its candidate list), `properties/unifac.py`
    (`ActivityArrays.report` splits ions from neutrals), `numerics/lle.py`
    (`held_ideal_fraction`, `IDEAL_FRACTION_REPORT`,
    `IDEAL_TIE_LINE_SENSITIVITY`), `vessel/vessel.py` (`Vessel.held_ideal`,
    `_ideal_caveat`, `lle_report` in all branches),
    `validation/unifac_gap.py` (rewritten, 5 panels, ~1 min),
    `tests/test_activity.py` (+6, now 83), `tests/test_lle.py` (+8, now 22).

    **679 tests pass in 14:42, lint clean.** The suite's only warnings are the
    `H2O <-> N2` overflow above, confined to `test_prep_side_products`.

81. ⚠⚠ **HANDOFF 79's OPEN HYPOTHESIS IS SETTLED, AND IT IS REFUTED. THE
    ADIABATIC TAIL IS NOT A GENERIC INTEGRATION WEAKNESS — IT IS AN ENERGY LEAK
    THAT NEEDS A PRECIPITATION EVENT, AND IT COSTS 495 J AGAINST A 0.0087 J
    CHEMICAL BUDGET.**

    Item 79 recorded, as a HYPOTHESIS rather than a measurement, that the
    insulated metathesis reading 0.038 K at 3600 s instead of 0.158 was probably
    generic and pre-dated the precipitation term: *"an insulated flask 0.16 K
    above an open room loses the excess to evaporation, and BDF weights T against
    rtol * 298."* The control that would have tested it — a flask STARTED 0.16 K
    warm with no precipitation — "did not finish inside two minutes".

    ⚠ **IT FINISHES IN 0.2 SECONDS.** Whatever was slow in that session, it was
    not this flask. Four controls, all insulated (UA = 0, heat_capacity = 0), all
    3600 s in ONE call:

    | control | dT after 3600 s |
    |---|---:|
    | D  ions, no precipitation, started AT ambient | **−0.00008 K** |
    | C  water only, no ions, started 0.16 K WARM | **+0.15991 K** |
    | C  ... same at rtol 1e-9 | **+0.15991 K** |
    | B  the metathesis flask, precipitation OFF, started WARM | **+0.15992 K** |
    | B  ... same at rtol 1e-9 | **+0.15992 K** |

    **A warm insulated flask holds its heat to five decimals in a single 3600 s
    call.** There is no generic evaporative loss and no generic BDF weighting
    problem. The proposed mechanism does not exist.

    ## WHICH HALF: THE TERM'S CODE, OR THE EVENT?

    Rule 3 applied literally — hold the code fixed and change the chemistry, then
    the reverse. Same flask, 3600 s, one call, started 0.16 K warm:

    | | dT |
    |---|---:|
    | term ON, charged 10x BELOW saturation (no event) | +0.15991 K |
    | term OFF, same dilute charge | +0.15991 K |
    | term OFF, fully charged 0.01 mol | +0.15992 K |
    | **term ON, fully charged (the event happens)** | **+0.10930 K** |

    ⚠ **The term's mere presence in the RHS is free** — with nothing
    supersaturated it agrees with the term switched off to five decimals. **The
    EVENT is what costs.**

    ## THE TRAJECTORY, AND WHY THE 1200 s TEST PASSES

    `Vessel.run` returns the scipy solution, so the single call's own trajectory
    needs no extra integration:

    | t / s | dT / K | solid AgCl / mol |
    |---:|---:|---:|
    | 600 | **+0.15774** | 0.0099619 |
    | 900 | +0.15811 | 0.0099854 |
    | 1200 | **+0.15751** | 0.0099866 |
    | 1800 | +0.15520 | 0.0099866 |
    | 2400 | +0.09586 | 0.0099867 |
    | 3000 | +0.03553 | 0.0099867 |
    | 3600 | **+0.03782** | 0.0099867 |

    It reaches the enthalpy prediction (0.1577 from the two tables), holds it
    through 1200 s — **which is why `test_it_warms_the_flask_by_the_dissolution_
    enthalpy` passes and is not wrong to** — and then decays **after the
    chemistry has stopped.** Both endpoints are real solver points, not dense
    output: the 1200 s run ends at +0.15751 and the 3600 s run ends at +0.03782.

    ## THE ARITHMETIC THAT MAKES IT A DEFECT RATHER THAN PHYSICS

    Between t = 1200 s and t = 3600 s, with everything audited block by block:

        temperature       −0.119682 K  on ~4141 J/K   =   −495.6 J
        largest mole change ANYWHERE (all four blocks)  =  1.332e−07 mol
        that, priced at 65 kJ/mol                       =  0.0087 J

    **Five orders of magnitude.** UA = 0, so nothing leaves to the room; the gas
    block holds no water at all, so there is no latent heat; the solid is flat to
    1e-10 mol, so it is not re-dissolution. ⚠ **No sink exists, and
    `conservation_report` cannot see it because it audits MATTER, not energy.**

    ## AND ONCE THE ENERGY IS GONE THE FLASK IS STABLE AT THE WRONG TEMPERATURE

    A matched pair, each SETTLED first and then given another idle 3600 s call:

    | | settled | after another 3600 s idle |
    |---|---|---:|
    | AgCl, the precipitation TERM | 298.1878 K, 0.0099867 mol | **+0.00001 K** |
    | benzoic acid, the DISSOLUTION law | 275.9236 K, 0.1773486 mol | **+0.00000 K** |

    ⚠ **A solid phase sitting at rest does NOT leak** — neither kind. So this is
    not "the solid block in the energy equation" either. The loss happens in the
    window where the event has finished but the solver is still expanding its
    step, and once lost it stays lost: 298.1878 K is +0.0378, i.e. the flask
    settles at the depleted value and holds it.

    **What this changes:** item 79's "chunking is part of the recipe, one level
    deeper" reading was the right ADVICE for the wrong REASON. Chunking does not
    compensate for a generic solver weakness; it avoids a window in which energy
    is actually destroyed. ⚠ **This is a measured wrong answer of the same class
    as M0's dryout band**, and it is now `MILESTONES.md` M12.

    ⚠ **A TRAP THIS COST ME, WORTH WRITING DOWN:** the state vector is
    `pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not
    last.** An audit that assumes (liquid, gas, solid, liquid2) reads the gas
    block as the solid and vice versa. The conclusion above survived it only
    because the bound taken was the largest change across ALL blocks, which is
    label-independent. Take that bound first.

    **Files:** `validation/adiabatic_tail.py` (NEW — every control above, runs in
    about 7 seconds, and it is the reproduction M12 works against);
    `tests/test_precipitation.py` (docstring corrected to stop stating the
    refuted hypothesis — the test itself is unchanged and still right).

82. ✔✔ **M12 IS CLOSED, AND THE CAUSE WAS IN LAYER 2 RATHER THAN IN THE SOLVER,
    THE ENERGY EQUATION OR THE PRECIPITATION TERM. A DERIVED RATE CONSTANT WAS
    9.4e7 TIMES THE COLLISION LIMIT, AND ITS TWO HEAT TERMS WERE ±5.2e9 W EITHER
    SIDE OF A NET OF A FRACTION OF A WATT.**

    The insulated metathesis reads **+0.15759 K at 3600 s in one call** (was
    +0.03782 against a prediction of ~0.1577), agrees with itself at **every**
    tolerance rung from 1e-6 to 1e-9, and the per-step energy budget over the
    post-event window is **+0.005 J** where it was **−495.843 J**.

    ## THE CAUSE, AND IT IS A ONE-LINE CONSEQUENCE OF AVOIDING ANOTHER CLAMP

    `dissociation_templates` declares `Ea = 60 kJ/mol` for water autoionization,
    chosen — the comment says so — to sit just above water's dissociation
    enthalpy of 55.8 so `detailed_balance`'s elementary-barrier clamp does not
    fire. Detailed balance then gives the REVERSE `Ea_rev = 60000 − 55800 =
    4200 J/mol` and, with `A_rev = 5.13e19`, a rate constant of

        k_rev(298) = 9.43e18 L/(mol s)      vs 1.4e11 measured (Eigen)

    ⚠ **The very choice that avoids one clamp puts the derived reverse eight
    orders past what a collision can deliver.** Every other pair in the project
    has `dH ≈ 0`, hence `Ea_rev = 60000`, hence a perfectly ordinary rate — which
    is why water was the *only* offender out of 29 bimolecular reactions across
    three real networks.

    A pair running 1e8× too fast turns over 9.4e4 mol/s in a 1 L flask, so its
    two heat terms are ±5.2e9 W around a net of a fraction of a watt: **a
    twelve-order cancellation in the temperature equation, on the stiffest mode
    in the vessel, invisible to a solver whose error control is denominated in
    kelvin and in moles and never in joules.**

    ## THE FIX: A CEILING THE PROJECT ALREADY APPLIED TO THE OTHER HALF

    `reactions/library.py` has always refused a hand-authored A above the
    collision limit — *"buying a prettier threshold with an impossible
    pre-exponential is the wrong trade"*, written about a burner that wanted
    1e14. ⚠ **Nothing applied that standard to the rate constants this project
    DERIVES**, and it derives one for every reversible template there is. That
    asymmetry is the whole defect in one sentence.

    `reactions.thermo.COLLISION_LIMIT = 1.0e11 L/(mol s)`: if either direction's
    rate constant at 298 K exceeds it, **both** pre-exponentials are scaled by
    the same factor and `DetailedBalance.rate_capped` reports it (surfaced by
    `build_network` as a NOTICE, exactly like `barrier_raised`).

    ⚠ **Scaling BOTH is what keeps this a correction to a rate rather than a
    change of chemistry: K = k_f/k_r is invariant under it exactly.** Measured —
    Kw stays **1.0022e-14** across eight orders of A. No pKa, no pH, no
    equilibrium can move. Water now equilibrates in ~0.3 ms instead of ~0.5 ps,
    which is still instant against anything here.

    ⚠ **THE CEILING IS ON k(298), NOT ON A.** Every acid dissociation carries
    `Ea = 60 kJ/mol` with a pre-exponential many orders above 1e11 and a rate
    constant 1e-4 of the limit or below — the barrier is what makes them
    physical. Capping A instead would have slowed every acid/base equilibration
    in the project by 1e7 and would have been measuring the wrong quantity.

    ## FOUR THINGS THAT WERE REFUTED BEFORE THE RIGHT ONE WAS FOUND

    Each cost real time and each is a fix someone will propose again:

    * **The precipitation term.** Controlled for in the last session; with
      nothing supersaturated, term ON and OFF agree to five decimals.
    * **The energy equation's algebra.** ⚠ Measured pointwise:
      `q_rxn / (−dH·dn_rxn[H3O+]) = 1.000000` at every solver point. The heat IS
      exactly the price of the extent it drives — so rewriting `q_rxn` as
      `−Hf·dn` (which was designed and nearly built) would have changed nothing.
    * **TOLERANCE, IN BOTH DIRECTIONS.** Tightening `atol` alone recovered it
      (−1.2e-1 → −1.5e-4 K) even though `atol` never reaches T, whose scale is
      `rtol·298 K`. And integrating `(T − T0)` — which tightens the temperature's
      own budget by three orders — made it **worse**: +2.0e-2 K at default and
      **31,324 steps / 265 s** at rtol 1e-8. ⚠ *The obvious fix, aimed at the
      variable the error appeared in, was measurably the wrong one.*
    * **THE INTEGRATOR.** Same RHS, same tolerances: **Radau −5.5e-5 K, LSODA
      +8.8e-5 K, BDF −1.2e-1 K.** So BDF specifically mishandled it — but
      neither alternative survives the project's real work: **Radau does not
      finish the benzoic-acid prep in 8 minutes where BDF takes 39 s, and LSODA
      fails it outright at t = 0.013 s.** "Use a better solver" was measured and
      unavailable.

    ⚠ **The transferable shape: the leak was localised by a PER-STEP energy
    budget, not by a better hypothesis.** Three consecutive BDF steps of exactly
    167.63 s, at −253.4, −145.2 and −69.0 J, with `dn(H3O+)` of order 1e-10.
    *Energy leaving with no matter moving*, three times, at a fixed step size —
    that shape named the mode. It is in `validation/adiabatic_tail.py` now.

    ## THE COST WENT DOWN, AND THE CONVERGED CHEMISTRY DID NOT MOVE

    The stiffest mode in every aqueous flask got 6.7e7× slower, so the prep got
    **6.6× faster (39.4 s → 6.0 s)**. Rule 4 applied to the answer itself — the
    prep's benzoate on a tolerance ladder:

    | rtol | BEFORE benzoate | BEFORE s | AFTER benzoate | AFTER s |
    |---|---|---:|---|---:|
    | 1e-6 | 0.199999990 | 39.8 | 0.200025315 | 6.1 |
    | 1e-7 | 0.199999991 | 88.0 | **0.199993746** | 10.7 |
    | 1e-8 | **0.199993746** | 156.7 | **0.199993745** | 9.3 |

    ⚠ **The two CONVERGED answers are identical to nine figures**, which is what
    Kw's invariance predicts and is the claim worth making. What changed is that
    the default rung now lands on the converged answer instead of 3.1e-5 away
    from it, and converging costs 10.7 s instead of 156.7 s. `T_final` is
    353.0012 K at all three rungs after, against 352.9823 / 353.0001 / 353.0024
    before — ⚠ the old default was **0.019 K** off and the old ladder had not
    converged in temperature at all.

    ## ⚠ ONE HONEST REGRESSION AT THE DEFAULT RUNG, AND IT IS THE OLD ONE

    At rtol 1e-6 the prep now creates **2.53e-05 mol of benzoyl** where it used
    to create 3.5e-12 — the projection cannot settle ethyl benzoate, which is
    driven to exactly zero. That is the standing *"a stiff reactant driven to
    EXACTLY zero still overshoots, at the 1e-4 level"* item, made visible because
    fewer, larger steps now cover the same span. It **converges**: 2.53e-05 →
    −1.70e-13 → −4.41e-15. And `conservation_report` says so unprompted, which is
    the honest path working rather than failing. ⚠ Note what it replaced: the old
    default's projection created **1.88e-03 mol of `[OH3+]`** — 76× larger, and
    already sitting in the invariants table as a tolerance artefact.

    ## THE OTHER HALF OF THE MILESTONE: AN ENERGY AUDIT

    `conservation_report` audits MATTER; a flask held every element to 1e-12
    while destroying half a kilojoule. New:

    * `VesselIntegrator.energy_terms(y, boundary=None)` — every watt the
      temperature equation saw, term by term, plus the per-reaction heats.
      Implemented as an optional `probe` dict on `make_rhs`: one `is not None`
      test per evaluation, against a call that does dozens of matmuls.
    * `Vessel.energy_report()` — the balance, **and the GROSS reaction heat
      beside the net**. ⚠ That column is the point: a net of 1e-3 W looks the
      same whether the flask is at rest or whether two 5.2e9 W terms are
      cancelling to twelve digits, and it was the second. It flags any
      cancellation above 1e6×; the metathesis now reads **2.26e3×**.
    * `validation/rate_ceiling.py` — the standing audit of every derived rate
      constant against the ceiling, cold and hot.
    * `tests/test_energy_balance.py` — 10 tests, asserting **convergence and
      physics**, never a default-tolerance value.

    ⚠ **A TRAP THE INSTRUMENT ITSELF SET, AND IT COST A WHOLE WRONG READING.**
    `energy_terms` must be given the state the RUN started from, because the RHS
    freezes each layer's permittivity at its integration boundary. Re-freezing at
    a later state perturbs the Bronsted-Bjerrum factor in the fifth digit — which
    is 1e5 W out of a twelve-order cancellation. The same state at t = 1183 s
    reads **q_rxn = −4.69e6 W** frozen at itself and **−5e-3 W** frozen at the
    run's own boundary. Hence the `boundary=` argument, and a test for it.

    ## ⚠ WHAT IS STILL OPEN, REPORTED RATHER THAN FIXED

    **The guard is evaluated at 298.15 K only, and a barrier climbs with
    temperature faster than a collision frequency does.**
    `validation/rate_ceiling.py` prints the crossings:
    `carboxylic_acid_dissociation_rev` **crosses the ceiling at 416.6 K** and is
    1.16e3× over it at 700 K. Nothing runs a carboxylic acid that hot today, so
    it is latent — but a reflux reaches 416 K, and a route that wants to must
    read that panel first. Water's own pair is *pinned at* the ceiling at 298 K,
    so it is nominally 2.6× over at 700 K — against 9.4e7× before, and the real
    ceiling rises with temperature while a fixed 1e11 does not.

    ⚠ **AND A SECOND THING THE AUDIT FOUND IN PASSING, NOT YET CHASED:
    `born_A` is ZERO for `[Ag+]`** while every other ion in the flask has one
    (Cl⁻ 3.84e5, Na⁺ 6.81e5, NO₃⁻ 2.86e5, H₃O⁺ 3.55e5, OH⁻ 5.07e5 J/mol). Since
    `born_A` is also the ion mask, silver is being carried as a NEUTRAL by the
    transfer term. Harmless in a single aqueous phase, where the Born term is
    exactly zero anyway; it is an extraction of a silver salt that would be
    wrong, and nothing says so.

    **Files:** `src/chemsim/reactions/thermo.py` (COLLISION_LIMIT, correction 3,
    `rate_capped`); `src/chemsim/network/builder.py` (the NOTICE);
    `src/chemsim/numerics/vessel_integrator.py` (`probe`, `energy_terms`);
    `src/chemsim/vessel/vessel.py` (`energy_report`);
    `validation/rate_ceiling.py` (NEW); `tests/test_energy_balance.py` (NEW);
    `validation/adiabatic_tail.py` (now the verification, with the step budget).

83. ✔✔ **M5 IS DONE AT 25 TEMPLATE-READY ROUTES OF 173 (WAS 7), FROM TWENTY NEW
    TEMPLATES — AND THE MILESTONE'S REAL FINDING IS THAT THE WORK QUEUE M1 LEFT
    BEHIND WAS MOSTLY OUTCOME LABELS. SIX OF THE TOP TEN CLASSES WERE REFUSED,
    AND ONLY ONE OF THE SIX FOR DIFFICULTY.**

    Measured against the previous commit, regenerated in a worktree rather than
    read off the committed report (which predated M4 and was stale):

    | | before | after |
    |---|---:|---:|
    | routes template-ready | 7 / 173 | **25 / 173** |
    | reaction classes covered | 12 / 206 | **29 / 212** |
    | templates in the project | 14 | **34** |
    | species refused | 472 | 466 |
    | UNIFAC-decomposable | 830 | 836 |

    `examples/named_routes.py` runs **17 routes end to end in 24 s**.
    `tests/test_named_routes.py` is 38 tests.

    ## ⚠⚠ M1 BUILT THE STANDARD; THIS IS THE FIRST MILESTONE THAT HAD TO SPEND IT

    M1 settled that *a reaction class is a MECHANISM claim, not an outcome*, and
    handed forward a greedy set-cover order. **That order does not survive its own
    standard.** Refused, with what each would have paid:

    | refused | routes | why |
    |---|---:|---|
    | `catalytic-air-oxidation` | 3 | three mechanisms: liquid-phase radical autoxidation (Amoco), Mars–van Krevelen over V2O5, and an oxidative ring cleavage losing 2 C as CO2 |
    | `fermentation` | 2 | `glucose -> acetone + butanol + ethanol + CO2 + H2` **by Clostridium**. A metabolic network. |
    | `pyrolysis` | 2 | two of three rows are `coal-marker -> coal-tar-marker` |
    | `isomerisation` | 2 | cis/trans on nickel, aldose-ketose, and Wöhler's cyanate rearrangement |
    | `thermal-cracking` | 1 | a lumped product slate from a radical chain |
    | `separation` | 1 | ⚠ refused in the OTHER direction — the engine genuinely fractionates (M2's plate column), but a distillation is not a reaction class and that route's feedstock is a marker. Crediting it moves the headline by one and makes zero routes runnable. |

    **What replaced them is a long tail, and M5 barely shortened it.** Measured
    before and after: **63 routes one class away from 50 distinct classes ->
    56 from 43.** So M5 was 20 templates for 18 routes, not 5 for 18, and the next
    18 will cost about the same. There is no lever, and that was M1's own
    conclusion arriving in the work.

    ⚠ **ONE CLASS WAS SPLIT RATHER THAN REFUSED, AND THE DISTINCTION IS THE WHOLE
    JUDGEMENT.** `catalytic-hydrogenation` is the most-used class with no template
    in the corpus (10 steps) and its rows are five mechanisms — but unlike
    `fermentation`, **every one of them IS a clean mechanism**. So the rows were
    re-labelled on M1's precedent (11 rows, with `picric-acid-route`'s ipso
    nitration) and two of the five built: `nitro-hydrogenation` and
    `alkene-hydrogenation`. The other three are named gaps in
    `data/catalog/README.md`.

    ## ⚠⚠ FOUR THINGS FOUND ON THE WAY, THREE OF THEM SILENT BEFORE

    **1. A REVERSIBLE TEMPLATE IS DISCOVERED IN THE FORWARD DIRECTION ONLY.**
    Measured, and it is not visible from reading either layer:

        build_network(["CCOC(C)=O", "O"], [esterification()])  ->  0 reactions
        build_network(["CC(=O)O", "CCO"], [esterification()])  ->  2 reactions

    `_expand_once` matches the template's REACTANT patterns, and an ester is
    neither an acid nor an alcohol. So **an ester and water in a flask are inert**,
    however reversible the esterification is; the derived reverse exists only as
    the mirror of a forward reaction the expansion already found. ⚠ This is
    GENERAL to every reversible template in the project and it is **NOT FIXED** —
    fixing it means expanding on reverse patterns too, roughly doubling every
    build's match cost. M5 wrote `ester_hydrolysis` from the ester side instead,
    and it is the reason `ester-hydrolysis` needed two templates rather than being
    credited to the esterification that "already covers it".

    **2. A NEUTRAL SPECIES WITH NO VAPOUR-PRESSURE CURVE MIXES STANDARD STATES,
    AND IT WAS WORTH +323 kJ/mol.** `standard_state.reaction_shift` skips a
    species for two reasons and its docstring justified only one. For a derived
    ION, skipping is correct — the value was anchored on the already-shifted
    conjugate acid, so the conventions agree. **That argument says nothing about a
    NEUTRAL whose Psat is under `PSAT_FLOOR_BAR`.** On the biodiesel network:
    monoolein stays on the ideal-gas basis while methyl oleate, glycerol and
    methanol move to the liquid one, and `methyl oleate + glycerol -> monoolein +
    methanol` reports **dH = +330 kJ/mol** for a reaction that is thermoneutral to
    a few kJ. Nothing was wrong except that two of four species were priced in
    different currencies. `standard_state.mixed_basis` now names them and
    `build_network` prints a NOTICE per reaction.

    **3. AN ESTIMATOR OUTSIDE ITS DOMAIN ARRIVED AS A SCIPY TRACEBACK.** Joback
    gives triolein **Tb = 1690 K and Tc = 4020 K**, from which `acentric_factor`
    derives **omega = -0.64**. A negative acentric factor belongs to a quantum
    fluid (H2 -0.22, He -0.39); for anything else it INVERTS the Lee-Kesler slope,
    so the sampled saturation pressure falls as the sample heats, the Antoine fit
    wants a negative B, and scipy says *"Initial guess is outside of provided
    bounds"* — naming neither triolein nor Joback. Now
    `volatility._refuse_inverted_slope` refuses with the species, the two
    temperatures and the acentric factor in the message. **Same shape as the class
    bug `element_data` was written for.**

    **4. THE AUDIT WAS CALLING NINE NEUTRAL SPECIES "ion".**
    `_volatility_tier` mapped `kind == "nonvolatile"` to the `ion` tier, which the
    report describes as *"correct, and not an estimate at all"*. Phosphoric acid,
    guanidine, arginine, creatine, cyanic acid and two triglycerides are neutral,
    and "does not enter the vapour" is a different claim for them than for an ion —
    it is also a MISSING vapour-pressure curve, which is exactly what finding 2 is
    about. `nonvolatile` is now its own tier, ranked below `ion`.

    ## THE ONE ENGINE CHANGE THE TEMPLATES NEEDED

    `ReactionTemplate.run` now calls `Chem.RemoveHs`. Any template consuming H2
    must write hydrogen as an ATOM (`[H][H]` has no heavy atom to hang an implicit
    count on), and without the collapse the ammonia the Haber template makes
    canonicalises as `[H]N([H])[H]` — **a different state-vector entry from the
    `N` a player charges, with no reaction connecting them and every atom still
    accounted for.** ⚠ `RemoveHs` correctly leaves H2 itself alone; neither of its
    atoms has a heavy neighbour to fold into. Both halves are pinned by tests.

    ## FOUR RESULTS THE NETWORK PRODUCES RATHER THAN IS TOLD

    * **Cannizzaro** gives benzyl alcohol and benzoate EQUAL and each ~47% of the
      aldehyde, not ~94%. Two aldehyde slots, so two molecules per turn. Nobody
      wrote the 2:1.
    * **DDT is one sixth of the chloral charged.** `[cH]` matches chlorobenzene's
      ortho, meta and para independently, so six isomers form and share it. The
      historical insecticide was a mixture, and this is why — a pattern, not a
      purity model.
    * **Haber-Bosch stops at 76% of theoretical at 700 K** and makes LESS at 800 K.
      No maximum temperature is declared anywhere; detailed balance derived it.
    * **Ethylene hydration converts 2.9% per pass in the vapour** (a real plant
      gets ~5%) and **99.7% in the liquid**, same template, same charge, same
      temperature. The standard state is the entire difference — which is why
      `alkene_hydration` takes a `phase` argument instead of declaring `"any"`:
      `"any"` would put both channels in one network and the liquid one would run
      the flask to completion off a trace of condensate, destroying the number
      that is the whole point of the process.

    ## ⚠ WHAT M5 LEFT OPEN, REPORTED RATHER THAN FIXED

    * **`halogen_disproportionation` is written, correct, and CANNOT RUN.** HOCl
      has no measured boiling point in any source — the same standing refusal
      `electrolyte.py` records for carbonic acid — so `[O-]Cl` has no ion entry
      and `build_network` refuses by name. ⚠ **And curating it is a trap worth
      recording:** ATCT gives HOCl `Hf = -76.8 kJ/mol` where **Joback gives
      -211.3, a 134.5 kJ/mol error** that would have been silent. Adding the
      formation half without a physical half would leave a species whose
      equilibrium is measured and whose standard-state shift is invented, in a
      LIQUID-phase reaction where the shift decides the answer. A test pins the
      refusal so the day someone adds the pair, they are told the route opened.
    * **`nitro-partial-hydrogenation`, `arene-hydrogenation` and
      `carbonyl-hydrogenation`** are named gaps from the split above. The first is
      the whole difficulty of the paracetamol route.
    * **The catalyst is never a species** for `alkene_hydrogenation`,
      `nitro_hydrogenation`, `ammonia_synthesis` or either methanol template. All
      are heterogeneous and all are written homogeneous with an apparent barrier —
      the licence `sulfur_dioxide_oxidation` already takes. A flask with no iron in
      it makes ammonia, and "you need a catalyst" cannot be a gate until M6 gives
      a solid-phase reactant. Four routes read as species-short for exactly this
      reason (iron, copper, nickel, mercury(II)) and are runnable in practice.
    * **`alkene_hydration` and `library.alkene_dehydration` are the same
      interconversion with different barriers**, one reversible and one not. Both
      readings are defensible at their own end of the temperature range (80 vs 160
      kJ/mol), so a network holding both has two channels between one pair of
      species and its steady state is not its equilibrium. The bound is that the
      barriers differ by 80 kJ/mol, so one channel is ~1e7x the other at any given
      temperature. The bundles keep them apart; nothing enforces it.
    * **`diels-alder-route` step 3 is unbalanced in the catalog** — it loses a
      whole anhydride. Labelled, not corrected: inventing the missing products
      would be authoring chemistry inside an audit corpus.
    * **Nitration feeds itself.** A nitroarene still has aromatic C-H, so toluene ->
      mono -> di -> tri is not scripted — and neither is anything stopping it. 18
      species / 29 reactions at `generations=3`. Cap the expansion.

    **Files:** `src/chemsim/reactions/synthesis.py` (NEW, 20 templates);
    `src/chemsim/reactions/template.py` (RemoveHs);
    `src/chemsim/properties/volatility.py` (`_refuse_inverted_slope`);
    `src/chemsim/properties/standard_state.py` (`mixed_basis`);
    `src/chemsim/network/builder.py` (the mixed-basis NOTICE);
    `src/chemsim/properties/electrolyte.py` (hydroiodic acid);
    `validation/catalog_coverage.py` (17 classes, the `nonvolatile` tier);
    `validation/rate_ceiling.py` (four M5 networks);
    `data/catalog/route_steps.psv` (11 re-labelled rows);
    `examples/named_routes.py` (NEW); `tests/test_named_routes.py` (NEW).

84. ✔✔ **M6 IS DONE: A REACTION NOW HAPPENS INSIDE A CRYSTAL, AND THE MILESTONE'S
    REAL FINDING IS THAT ITS OWN BRIEF POSED A TRUE DICHOTOMY AND THE ANSWER WAS
    THE ONE THAT LOOKED LIKE MORE WORK. `PHASE_INDEX` STILL HAS TWO ENTRIES.**

    `CaCO3(s) -> CaO(s) + CO2(g)` runs, conserves every atom, carries its own
    endothermic load into the energy balance, and has an example. **Two
    declarations cover three catalog steps.** New: `properties/solid_state.py`,
    `numerics.vessel_integrator.SolidStateArrays`,
    `vessel.build_solid_state_arrays`, `Vessel.solid_state` /
    `Vessel.solid_state_report`, `examples/lime_cycle.py`,
    `tests/test_solid_state.py` (31 tests, 23 s). `mineral_data` regenerated with
    three new fields.

    ## ⚠⚠ THE FIRST IMPLEMENTATION WAS MASS ACTION AND IT WAS MEASURED WRONG

    M6's brief asked: a third `PHASE_INDEX` entry, or a second term next to
    precipitation? The arithmetic was done first, as the arc's rule requires, and
    it predicted that mass action on the solid amounts would give

        p / K  =  n(calcite) / n(quicklime)

    because a pure solid has UNIT ACTIVITY and mass action cannot say so. It was
    then BUILT that way anyway — and the prediction landed to five figures:
    **3.0863 against 3.0863 at 1100 K, 1.2139 against 1.2139 at 1200 K.** That
    turned the argument into a measurement, which is why it is worth keeping.

    ⚠ **AND DROPPING THE REVERSE IS NOT A WAY OUT.** Sealed 1 L, 0.1 mol charged:

    | T / K | equilibrium conversion | forward-only |
    |---:|---:|---:|
    | 900 | 0.12% | 100% |
    | 1000 | 1.23% | 100% |
    | 1100 | 7.95% | 100% |
    | 1200 | 37.3% | 100% |

    Under 1 bar of air, the equilibrium says calcite does not calcine below
    ~1150 K at all. **The kiln's whole mechanic is the part forward-only
    deletes.**

    The form that works is `flux = (k_f - k_r Q) * units` with **ONE `units`,
    chosen by the sign of the affinity** rather than one per direction. It is a
    common factor, so it divides out of `flux = 0` — amount-independent
    equilibrium — while an exhausted side still stops the reaction. That sign
    switch is a kink at the exact operating point, and it was measured: a vessel
    parked at equilibrium for **2,000,000 s costs 0.2 s of wall clock and lands
    on K to 4e-13**, at `units_f/units_r` up to 129.5.

    ## ⚠ THE REPRESENTATION WAS FORCED, AND IT IS THE SECOND MEASUREMENT

    **The lattice had to become a species, and item 78's representation could not
    do it.** The solid block holds IONS — that is what makes precipitation
    conserve matter by construction. Quicklime ion-by-ion is `[Ca+2].[O-2]`, and
    **the oxide ion is in no aqueous table anywhere**, because CaO does not
    dissolve to Ca2+ + O2-, it hydrates. `thermochemistry` refuses `[O-2]` on net
    charge; `solubility_product` had already refused quicklime for exactly this
    reason. So there was no ionic route to the product of calcining limestone,
    and both halves of that refusal are now pinned by a test — so a future
    curation of `[O-2]` is told what it opens.

    `mineral_data` gained `lattice` (canonical one-species SMILES), `Cp_solid`
    and `Vm_solid`. Both new numbers are measured CRC, `Cps` from the SAME ROW as
    the `Hfs`/`S0s` pair; 23 of 25 minerals carry all three, and a mineral
    missing either is refused loudly when charged rather than borrowing an ion's
    placeholder.

    ⚠ **NOTHING ABOUT THE FUSION-LAW VERDICT IS SOFTENED.** A crystal may now
    REACT while staying a crystal, and it still may not DISSOLVE — 407x wrong in
    both directions is still 407x wrong. `solidifies` is False for every lattice,
    its vapour pressure is 1e-30 bar, and a test integrates limestone under water
    for 1000 s to show it does nothing. The two questions never touch.

    ## ⚠ Ea IS DERIVED, WHICH IS WHAT MAKES THE REVERSE SURVIVABLE

    An endothermic decomposition whose reverse is a gas landing on an oxide
    surface has no reverse barrier, so `Ea = dH` — the same floor
    `detailed_balance` enforces everywhere else here. Two consequences:

    * calcite's barrier comes out at **179.2 kJ/mol** against experimental
      calcination activation energies quoted at 170–200. Nothing was fitted.
    * the reverse rate constant becomes `A exp(-dS/R)`, **temperature-
      independent** (4.26e-4 1/(bar s)). ⚠ And the cancellation is done in
      CLOSED FORM at setup rather than as `k_f / K`: at 300 K those two
      exponentials are 1e-32 and 1e+21 and their product is an ordinary 4e-4.
      Written as a ratio it would be a division of two near-overflow numbers in
      the hot loop.

    `DECOMPOSITION_A = 1e5 1/s` is the only free number, and it is a CLOCK:
    it multiplies the whole flux so it divides out of the equilibrium. Measured
    over two decades — the same sealed pressure to **seven figures**. One
    constant covers both rows because no source would distinguish them.

    ## FOUR MECHANICS NOBODY WROTE

    * **A kiln temperature.** 14% conversion at 1100 K under air, 99.8% at
      1150 K. The threshold is where `K(T)` crosses ambient;
      `solid_state_report` BISECTS for it rather than printing a stored number.
    * **A sealed tube that stalls** — the table above.
    * **Slaking** (`lime-cycle` step 2): the dehydration row run backwards.
      ⚠ Priced against water VAPOUR, so slaking with liquid water gets the
      condensation enthalpy from the vessel's own evaporation term. The two must
      not both carry it.
    * **Carbonation** (`lime-cycle` step 3), and this one is not any single row's
      reverse: it is the dehydration row forwards and the decarbonation row
      backwards, **sharing the quicklime in the solid block**. 0.02 mol of slaked
      lime under CO2 at 700 K yields limestone through a quicklime intermediate
      neither declaration names in that role, calcium exact to 1e-9.

    ## ⚠⚠ SECOND PUSH, SAME SESSION: THE CONSTANT WAS DECLARED AT THE WRONG END, AND
    ## A SECOND ROW IS WHAT PROVED IT

    M6 shipped with `DECOMPOSITION_A = 1e5 1/s` as a declared FORWARD pre-exponential,
    calibrated on the lime kiln. Adding chain 2's seed broke it immediately and
    completely:

    | row | dH / kJ | forward, A declared | measured |
    |---|---:|---|---|
    | calcite -> quicklime + CO2 | 179.2 | 630 s at 1200 K | a real kiln |
    | **2 FeSO4 -> Fe2O3 + SO2 + SO3** | **340.0** | **1.7e-13 1/s at 1000 K** | **0.00% in 20,000 s at every temperature its thermodynamics allow** |

    **Thirteen decades of clock error on a row whose thermodynamics were exactly
    right.** With `Ea = dH`, a barrier nearly double calcite's is unreachable.

    ⚠ **THE MISSING PHYSICS IS THE ENTROPY OF MAKING GAS, AND FOLDING IT INTO A
    CONSTANT IS THE MISTAKE.** With the transition state taken to resemble the
    products — the same late-TS assumption that makes the reverse barrierless and
    fixes `Ea = dH` — the forward pre-exponential is `A0 exp(dS/R)`, and what is left
    over is

        k_rev = A_fwd exp(-(Ea - dH)/RT) exp(-dS/R) = A0      exactly, at every T

    **so `A0` is the REVERSE constant** — the pre-exponential of ONE elementary event,
    a gas molecule arriving at a crystal surface with no barrier to climb. That event
    is the same event for calcite, green vitriol and baking soda, which is why one
    number can cover rows that make different amounts of gas. The forward direction
    is not one event: it is that one run backwards against a different amount of
    gas-making entropy each time.

    `RECOMBINATION_A = 4.259e-4 1/(bar s)`, unchanged in value from the first
    version's calibration, so **calcination's forward constant comes back as
    100000.34 against the 1e5 it was declared at — 3 ppm, and every lime number is
    provably unmoved.** The four rows then land at:

    | row | dH | dS | tau | at |
    |---|---:|---:|---:|---:|
    | calcination-decarbonation | 179.2 | 160.3 | 631 s | 1200 K |
    | calcination-dehydration | 108.5 | 143.6 | 146 s | 900 K |
    | sulfate-thermal-decomposition | 340.0 | 377.6 | 25 s | 1000 K |
    | bicarbonate-thermal-decomposition | 135.6 | 334.4 | 44 s | 450 K |

    **Three of those four are timescales nothing was calibrated against** — a red-hot
    retort of green vitriol in half a minute, and baking soda in the catalog's own
    `calciner, 450 K` in under a minute. They came out right because the entropy
    stopped hiding in the constant. ⚠ The one number that DID move is the
    dehydration row's clock, 7.4x slower; its equilibrium is untouched.

    ## ⚠ TWELVE MINERALS, AND CHAIN 2's SEED WAS NEVER AN ENGINE PROBLEM

    `mineral_data` is now **37 entries**. Every candidate tried priced on the existing
    rule except one, and the two new rows are:

    * **`2 FeSO4(s) -> Fe2O3(s) + SO2(g) + SO3(g)`** — chain 2's seed, recorded as
      blocked on the engine since M6 was written. **It was blocked on ONE MINERAL.**
      Goes to completion at 1000 K in ~300 s, ending at `p(SO2) = p(SO3) = 0.5066 bar`
      — the two gases sharing the ambient total exactly.
    * **`2 NaHCO3(s) -> Na2CO3(s) + CO2(g) + H2O(g)`** — `solvay-process` step 3, and
      why a cake rises.

    ⚠ **AND THE CATALOG'S OWN ROW NAMES A PRODUCT THAT IS NOT THE REACTION.**
    `vitriol-distillation` step 1 reads `iron-ii-sulfate -> iron-ii-OXIDE +
    sulfur-trioxide`, which balances and is not what happens: FeO does not survive red
    heat. The declaration is the chemistry (hematite, with half the sulfur reduced) and
    the row is recorded as a simplification. ⚠ **FeO is refused by the curation rule
    anyway, on the half nobody would guess** — its formation pair shares WEBBOOK, and
    **CRC tabulates no crystal heat capacity for it at all**, so the refusal that stops
    the wrong reaction being built is the BOOKKEEPING one. The five roasting oxides and
    four more sulfides are curated too, which closes the DATA half of `roasting`'s
    refusal and leaves it waiting on one clearly-named engine feature.

    ## ⚠ A TWO-GAS ROW CHANGES WHAT "HOT ENOUGH" MEANS

    A row evolving `n` moles of gas has `K` in `bar^n`, so comparing it against a
    pressure is a units error the moment `n > 1`.
    `SolidStateArrays.threshold_temperature` solves `K(T) = (P_ambient / n)^n` instead
    — the reference state where the evolved gases are the whole atmosphere and share
    the ambient total. **For `n = 1` that is exactly `K = P_ambient`, so no lime number
    moves**; for green vitriol it is 874 K against the 918 K where `K` reaches
    1 bar^2, because two gases sharing one bar is 0.25 bar^2 and not 1.

    ## ⚠⚠ AND THE DEFAULT SOLVER TOLERANCE IS NOT CONVERGED FOR A VENTED KILN

    Found while re-measuring the gate, and it corrects a row this session had already
    written down. On the 1100 K swept kiln:

    | rtol / atol | converted | p(CO2) / bar |
    |---|---:|---:|
    | 1e-6 / 1e-9 (**the default**) | 39.04% | 0.0000 |
    | 1e-8 / 1e-11 | **13.97%** | **0.7275** = K(1100 K) exactly |
    | 1e-10 / 1e-13 | 13.97% | 0.7275 |

    It CONVERGES, which is what says the loose reading is an artefact and not a
    different physical answer, and **the tight runs are also FASTER** (1.4–3.3 s
    against 5–13 s) because the loose solver was thrashing. The cause is the vent:
    `k_vent` is 1e3 mol/(bar s), so the gas balance is far stiffer than the chemistry
    feeding it. ⚠ **It is not this milestone's term** — the same 36% appears with the
    solid-state term as the network's only reaction, and converges to the same 13.97%.
    Any slow source feeding this vent is exposed to it.

    The corrected gate, converged:

    | T / K | K(T) / bar | vs 1.013 | converted | p(CO2) |
    |---:|---:|---|---:|---:|
    | 1000 | 0.1026 | below | 1.30% | 0.1026 |
    | 1073 | 0.4444 | below | 6.54% | 0.4443 |
    | 1100 | 0.7275 | below | 13.97% | 0.7275 |
    | **1119** | **1.0146** | **the threshold** | 43.53% | 0.9949 |
    | 1150 | 1.7052 | ABOVE | 99.75% | 1.0132 |
    | 1200 | 3.7231 | ABOVE | 100.00% | 1.0132 |

    ⚠ **AND IT SHARPENS WHAT THE GATE IS.** Below the threshold an open flask's CO2
    sits at **exactly K(T)** — it is not swept anywhere, because a vent only pushes
    gas out when the TOTAL exceeds ambient and the air makes up the rest. **"Sweep the
    kiln" needs a carrier FLOW (`Vessel.ingress`), not an open door.** Above it, CO2
    alone would exceed ambient, so it pushes the air out and the reaction runs to
    completion. One comparison, `K(T)` against `P_ambient`, and both branches fall out
    of it.

    ## ⚠ THE COVERAGE ACCOUNTING COST TWO MORE SPLITS, AND BOUGHT A ROUTE

    Regenerated at HEAD: **26 / 173 routes template-ready** (was 25) and
    **32 / 214 classes** (was 29 / 212). `lime-cycle` is COMPLETE end to end from
    limestone and is the first entry in the report's list.

    M5's standard had to be spent twice more, and both times the answer was
    SPLIT rather than refuse, on the `catalytic-hydrogenation` precedent:

    | was | rows | became | why |
    |---|---:|---|---|
    | `hydration` | 3 | `lime-slaking` (2) + `carbonyl-hydration` (1) | two are `CaO + H2O -> Ca(OH)2`; the third is CHLORAL HYDRATE, a gem-diol on a carbonyl |
    | `carbonation` | 2 | `solid-carbonation` (1) + `basic-carbonate-precipitation` (1) | setting mortar is a solid-state reaction; the white-lead stack is a metathesis in solution |

    ⚠⚠ **AND THIS IS THE FIRST TIME A CLASS HAS BEEN CREDITED TO A MECHANISM
    THAT EMERGED RATHER THAN BEING WRITTEN.** `lime-slaking` is the dehydration
    row run backwards; `solid-carbonation` is not any single row's reverse.
    **Two declarations, three credited mechanisms.** `calcination` is credited
    the way `precipitation-metathesis` is -- to a TERM, with `N_TEMPLATES`
    deliberately not incremented.

    ## ⚠ M5's STANDARD, SPENT AGAIN — AND THIS TIME IT COST A CATALOG ROW

    `calcination` is TWO mechanisms and both are built. ⚠ **But the dehydration
    built is not the catalog's own row.** Bayer's `Al(OH)3 -> Al2O3 + H2O` needs
    two minerals `mineral_data` does not have; `Ca(OH)2 -> CaO + H2O` is the same
    mechanism on species that already price. **The mechanism is covered and the
    row is NOT claimed** — `data/catalog` still scores it uncovered. That is the
    standard costing something in the honest direction for once.

    ## ⚠⚠ AND THE THIRD `PHASE_INDEX` ENTRY IS STILL WANTED — BY A DIFFERENT
    MECHANISM

    `roasting` is refused twice over, and the second half is new and is the
    useful part:

    * **data** — all five rows are `metal sulfide + O2 -> metal oxide + SO2`; of
      the five sulfides only ZnS prices and **none of the five oxides does**.
    * **⚠ mechanism** — roasting CONSUMES a gas, and the affinity form is
      measurably not a rate law for that. A gas reactant's pressure sits in the
      DENOMINATOR of Q, so `p_O2 -> 0` drives the reverse flux to **2.6e15
      formula units per second**. A gas reactant is REFUSED where the arrays are
      built, naming that.

    A gas-consuming surface reaction IS mass action — first order in a gas
    pressure, gated on a solid being present — so it is exactly what the third
    `PHASE_INDEX` entry is for. **That is also the shape of the five
    heterogeneous templates** (`alkene_hydrogenation`, `nitro_hydrogenation`,
    `ammonia_synthesis`, both methanol rows), so **item 83's "a flask with no
    iron in it makes ammonia" is NOT fixed by M6** — but it now has a definite
    shape rather than being a gap.

    ## ⚠ dCp = 0 — AND THE CORRECTION WAS BUILT AND REJECTED BY MEASUREMENT

    Same discipline as `PrecipitationArrays.ln_Ksp`, and the cost is stated: the
    1 bar decomposition temperature is 1118.2 K for calcite (literature ~1170)
    and 755.2 K for slaked lime (~785), so kilns run 30–50 K cool. A `dCp(T)`
    correction from the new `Cps` values moves calcite to 1107.7 K (**worse by
    10 K**) and slaked lime to 774.9 K (better by 20). **One improves and one
    degrades**, which is the signature of a half-applied correction rather than
    of missing physics — a mineral's `Cp_solid` is a 298 K constant while a gas
    `Cp` here is a real cubic. A half-correction that helps one row and hurts
    another is worse than a stated omission, so the omission stays. The
    generating script records the measurement so it is not re-attempted blind.

    ## ⚠ ONE LATENT FRAGILITY FOUND — PRE-EXISTING, MADE REACHABLE, NOT FIXED

    A species that is in the network but **absent from a flask with no vent, no
    liquid and no reaction** has an identically ZERO Jacobian column — verbatim
    the `num_jac` trap `LAYER_REABSORB` documents. Sealed at 1100 K, with and
    without N2/O2 in the species list:

    | charge / mol | lean network | N2/O2 present but absent |
    |---:|---:|---|
    | 0.05 | `p/K - 1` = -1.7e-07 | **RAISED**: CO2 reached -2.572 mol |
    | 0.1 | +3.5e-09 | -2.6e-11 |
    | 0.4 | -5.4e-13 | +1.6e-07 |
    | 1.0 | +2.6e-08 | +1.9e-11 |

    The hair trigger on the charge is a NaN Jacobian, not a physical
    instability. **It does not return a wrong number** — `check_raw_solution`
    raises "a failed integration wearing a success flag" — so it is reported, not
    refused and not silently fixed. The second route in is the same one:
    a flask at EXACTLY zero pressure with `k_vent = 1e3` inhales 1013 mol/s at
    t = 0; 0.01 bar of nitrogen in the headspace removes the overflow entirely.
    Both are modelling errors in the caller (a sealed tube contains no air; an
    open flask contains air), and the example and tests model them correctly.

    The reason NOT to fix it tonight: the fix is a `LAYER_REABSORB`-style honest
    diagonal on the gas block, which is a change in the hot loop of every vessel
    in the project and would move invariants. It wants the full suite behind it
    and a session of its own.

85. ✔✔ **A GAS NOW ATTACKS A CRYSTAL, AND `PHASE_INDEX` STILL HAS TWO
    ENTRIES -- FOR THE SECOND MILESTONE RUNNING AND FOR A DIFFERENT REASON.**

    The wrong answer this fixes is one a player could see: **a flask with no iron
    in it made ammonia.** Five templates folded a heterogeneous catalyst into an
    apparent barrier, so "you need a catalyst" could not be a gate. It is one now:
    a bare flask of N2 and H2 at 700 K makes **exactly 0.0** mol of ammonia, and
    the same flask with 0.1 mol of iron makes 31.7% of theoretical in 600 s.
    `sphalerite-roasting` runs to **78.26%** in 1800 s of blown air, conserving
    zinc to 1e-12.

    New: `properties/surface.py`, `numerics.vessel_integrator.SurfaceArrays`,
    `vessel.build_surface_arrays`, `Vessel.surface` / `Vessel.surface_report`,
    `PhaseArrays.lattice`, `KineticArrays.order_solid`,
    `ReactionTemplate.solid_catalyst`, `library.SOLID_CATALYST_REFERENCE`,
    `examples/roasting_and_the_catalyst_gate.py` (5 panels, 12 s),
    `tests/test_surface.py` (38 tests, 12 s). `mineral_data` regenerated with
    three METALS (40 entries).

    ## ⚠⚠ THE BRIEF ASKED FOR ONE MECHANISM AND THE ARITHMETIC SAYS TWO

    The brief said to add `PHASE_INDEX["solid"] = 2` and let one mechanism cover
    both a solid catalyst and a roasting sulfide ("both are `nu` on the solid
    block, so this may be one mechanism"). Both halves are refuted:

      * a **catalyst's stoichiometry is zero on both sides**, so its `delta`
        never leaves the gas block -- only `order` reaches the solid one;
      * and **roasting cannot be priced on the ideal-gas basis at all**, because
        `thermochemistry` refuses a lattice SMILES by name. It needs `mineral_data`
        against a curated gas, which makes it a curated table like M6's.

    ⚠ **AND THE PHASE LABEL IS NOT A NAME, IT IS A CHOICE OF THERMODYNAMICS.**
    `reaction_deltas` applies the pure-liquid shift to anything that is not
    `"gas"`, so labelling `N2 + 3 H2 -> 2 NH3` a "solid"-phase reaction moves dG by
    **-99.7 kJ/mol** and K at 500 K by **2.6e10**. That is verbatim the failure the
    `PHASE_INDEX` comment was written to prevent -- `phase="any"` validated,
    documented and silently meaning liquid -- arriving at the line that comment is
    written on. A solid-catalysed gas reaction IS a gas-phase reaction: every
    participant that has an activity is a gas, and a pure solid's is 1.

    ## THE MIXED BASIS, WHICH IS THE ONE THING THE TERM HAD TO GET RIGHT

        rate = k(T) * prod(nS ** order_solid) * prod(C_gas ** order_gas)    mol/s

    NOT scaled by a volume, unlike every other rate law here. A solid's
    *concentration* has no referent -- the block is an inventory in mol and `V_S`
    is nominal -- and a gas's *amount* is not what a surface sees, because arrival
    goes with the collision rate and compressing the flask must speed the reaction
    up. So the rate is EXTENSIVE in the solid and INTENSIVE in the gas.

    One boolean does both jobs: `PhaseArrays.lattice` chooses each species' basis
    AND which block its stoichiometry lands in, because a lattice is the only
    species here whose block is unambiguous (it may react and may never dissolve,
    boil or melt). A non-lattice solid participant is REFUSED by name.

    ## FIVE MECHANICS NOBODY WROTE

    | | measured |
    |---|---|
    | a sealed roast STALLS | **1.53%** in 20 ks -- a litre of air holds 2.296 mmol of O2 and 0.1 mol of ore needs 150. Same shape as M6's kiln needing its CO2 swept: an open end, not a temperature |
    | a blown roast GOES | **78.26%** in 1800 s at 1100 K |
    | **autothermal roasting** | insulated, the same flask reaches **100%** while heating itself 1100 -> **1908.6 K**. A real zinc roaster burns no fuel. The VENT is what stops the runaway |
    | two ores share one blast | ZnS + PbS -> **0.039131 mol each**, both closures exact to 1e-12 |
    | the clock ignores the charge | first order in the solid, so `tau = 1/(k C_gas)` |

    ## ⚠ THREE THINGS THE FIRST GUESS GOT WRONG, MEASURED

      * **the reference-charge invariant is not bit-exact, and the reason is not a
        modelling difference.** `A_cat * SOLID_CATALYST_REFERENCE == A_folded`
        exactly, but a VENTED flask shows +0.086% ammonia -- and a vented
        comparison is not a comparison, because the two runs vent differently.
        Sealed, with the flask enlarged by the 0.0007096 L that 0.1 mol of iron
        occupies, they agree to **-4.6e-11 mol**. The residual is a crystal
        displacing gas, which a fourth-order rate law notices. Real, and bounded.
      * **the "no site balance" claim reads 9.75 as a yield ratio**, not 10. That
        2.5% is DEPLETION -- a run long enough to integrate is long enough to move
        down its own curve. Measured as an initial rate off the RHS it is 10.0 to
        1e-9.
      * **crediting `roasting` as M6 labelled it produced a FALSE CREDIT.**
        `mercury-from-cinnabar` reads `mercury-sulfide + oxygen -> mercury +
        sulfur-dioxide` and this term makes the OXIDE, so the route moved into the
        template-ready list on a mechanism that does not make its product -- the
        `deprotonation` mistake M1 named, from the other direction. Re-labelled
        `roasting-to-metal`. M6 had recorded the reading and not acted on it.

    ## COVERAGE: 33/215 classes, 27/173 routes, and be careful with that number (S3: now 35/218 and 27/173 -- item 87)

    Was 32/214 and 26/173. ⚠ **The one route added is `pyrite-roasting`, which
    does not run** -- pyrite has `Hfs` in WEBBOOK and `S0s` in nothing, so
    `mineral_data` refuses it. That is not a broken number, it is what
    template-readiness MEANS. **Honest summary: +1 class, +1 template-ready route,
    ZERO new routes that run end to end**, because all three smelting routes are
    still blocked at `carbothermic-reduction` / `gas-solid-reduction`.

    ## ⚠ THE SHARED CLOCK IS A PARTLY-REFUTED CLAIM, STATED

    `ROASTING_A` = 3.21e6 L/(mol s) (3.2e-5 of the collision limit) and
    `ROASTING_EA` = 150 kJ/mol are shared across all four rows -- M6's lesson says
    that claims they are the same event. Structurally they are; on temperature they
    are not. The catalog's own equipment column puts cinnabar in a **900 K** retort
    and sphalerite in an **1100 K** roaster, and one clock makes cinnabar **31x
    slower** at its own temperature. ⚠⚠ And the one available fix is measured
    getting the ordering BACKWARDS: Evans-Polanyi would rank by enthalpy
    (sphalerite -882.7 the most exothermic, cinnabar -658.9 the least), so it puts
    sphalerite first where the furnaces put it last. The overall enthalpy is not the
    barrier of the rate-determining step. `alpha` is zero and the ordering is not
    claimed.

    ## THE DATA: three metals, and a free exact check on each

    Iron, nickel and copper. A metal is a lattice with NO DISSOLVED FORM, so
    `ions` is empty and that emptiness is the claim --
    `build_precipitation_arrays` now skips an ion-less record, because "every ion
    is present" is VACUOUSLY TRUE of an empty tuple and iron filings would
    otherwise be offered to `solubility_product` as a lattice whose only ion is
    itself. ⚠ **All three price at `Hf = Gf = 0.0` EXACTLY**, which is a CHECK
    rather than a datum: the same free, exact check `element_data` is built on,
    arriving on the solid basis, and the generator REFUSES a non-zero result as an
    allotrope mismatch (CRC's grey tin).

    ## ⚠ ONE LATENT UNITS ISSUE, REPORTED NOT FIXED

    `detailed_balance`'s rate cap compares a CATALYSED pre-exponential against a
    limit that is not in its units -- an order-1 factor in mol gives `A` an extra
    `mol^-1`, so 1e11 L/(mol s) is not a bound on it.
    `validation/rate_ceiling.apparent_A` multiplies by `SOLID_CATALYST_REFERENCE`
    to undo exactly that and the audit is restored to its baseline
    (`ammonia_synthesis_rev` crosses at **1335.1 K**, unmoved); `detailed_balance`
    does not, so it would fire **10x too eagerly**. Bounded in the class this
    project forgives -- the cap scales BOTH pre-exponentials so K is invariant, and
    the cost is a clock at most 10x slow -- and **it does not fire on any of the
    five catalysed templates today**, which a test pins so it cannot start
    silently. The proper fix wants the reference charge as an argument rather than
    a Layer-2 import cycle.

    **Also not modelled:** the SITE BALANCE. Ten times the catalyst is ten times
    the rate, for ever. Right at low coverage, wrong at high, stated rather than
    approximated. That is still M10.

86. ✔✔ **THE TOLERANCE AUDIT: EVERY EXAMPLE SWEPT, AND THE INSTRUMENT HAD TO
    BE AUDITED BEFORE ITS FINDINGS COULD BE TRUSTED.**

    `validation/tolerance_audit.py` re-runs every example at rtol 1e-8 / atol
    1e-11 and diffs, token by token. It patches the two `run` DEFAULTS rather
    than editing examples, so anything already passing its own tolerance is
    untouched -- which is the self-check: `lime_cycle` and
    `roasting_and_the_catalyst_gate` come out byte-identical at speedup 1.00.

    **11 examples swept; after one fix ZERO print a quotable digit that moves.**
    5 move below 0.1%, 6 are identical.

    ## ⚠ THE ONE REAL MOVE WAS IN THE PANEL THAT EXISTS TO SHOW IT

    `workshop` Part 2, melting a dry solid. At t = 800 s the default reads
    **T 389.50 K / solid 2.0000** and converged reads **388.38 K / 1.9656** --
    so the default says melting has not begun when 1.7% of the charge is gone
    and the flask is 1.1 K cooler from latent heat. The loose run overshoots the
    temperature by delaying the onset of the plateau the panel is about.

    ⚠ Fixing it cost **one second**: Part 2 alone tightened takes the example
    from 8.1 s to 9.1 s, not to 58.9 s. The 7.2x belonged to the other panels,
    which move by 4e-4 and are left alone.

    ## ⚠⚠ `oil_of_vitriol` CANNOT BE SWEPT, AND ITS NUMBERS ARE STILL RIGHT

    It RAISES at rtol 1e-8 in `burn(690 K, s8=0.002, o2=0.10)` -- `lu_factor`
    gets `array must not contain infs or NaNs` on `I - c J`, a NaN Jacobian,
    after 50.7 s of thrashing. But the panel's answer is confirmed: SO2 =
    **0.016000** at the default, **0.016000** at rtol 1e-8 with a 1e-9 mol trace
    of SO2 charged, 0.016001 with 1e-6 mol, **0.016000** at rtol 1e-7. A trace of
    the absent species removes the failure and the answer does not move -- the
    same diagnostic that identified this trap originally.

    ⚠⚠ **SO THE ZERO-JACOBIAN-COLUMN TRAP HAS A SECOND TRIGGER.** Not only "a
    species in the network but absent from a sealed flask" but "a TIGHT TOLERANCE
    on a flask holding a trace". Same NaN, same fix. That widens the case for the
    `LAYER_REABSORB`-style honest diagonal on the gas block.

    ⚠ And "it moved" and "it refused" are different findings. The audit keeps
    them in different rows and names the un-swept example in its summary whether
    or not it ran, because a coverage limit here is never silent.

    ## ⚠⚠ IT REFUTED A CLAIM THIS PROJECT HAD STARTED TO GENERALISE

    M6 measured its kiln FASTER tight (1.4-3.3 s against 5-13 s); S1 measured the
    same on a roast (3.67 against 19.94 s). Swept: **faster in 2 of 11, slower in
    9, worst 7.2x.** Each local measurement was right and the pattern is not
    there. The speedup belongs to a stiff vent fed by slow chemistry.

    ## ⚠⚠ AND THE FIRST VERSION OF THE AUDIT INVENTED A FINDING

    It reported `wait_until` moving **12.5%**, and that was `0.07 s of wall`
    against `0.08 s of wall`; the real worst move is **1.04e-4**. Wall clocks are
    now excised as TOKENS rather than by dropping the line, because this project
    prints physics and timing together (`t = 1353.13 s ... (0.89 s of wall)`) --
    dropping the line hides the move in `t`. And keying on the word "wall" would
    have been actively wrong: `lime_cycle` prints `±14.374 W wall`, a heat flux.
    **An instrument that cannot tell a clock from a result manufactures
    findings** -- the same shape as a coverage number counting a route that
    cannot run.

87. ✔✔ **`thermal-decomposition` SPLIT INTO FOUR MECHANISMS, ZERO ENGINE WORK --
    AND THE INSTRUMENT NEEDED FIXING BEFORE THE FINDING COULD BE READ.**

    M6 read this class against M1's standard, recorded "four rows and they are
    four mechanisms", and ran out of session rather than acting. The reading
    held. Four rows re-labelled in `route_steps.psv`:

    | route | became | covered? |
    |---|---|---|
    | `vitriol-distillation` 1 | `sulfate-thermal-decomposition` | ✔ built by M6, RUNS |
    | `solvay-process` 3 | `bicarbonate-thermal-decomposition` | ✔ built by M6, RUNS |
    | `melamine-route` 1 | `urea-deammoniation` | ✘ template only |
    | `marsh-test` 2 | `hydride-thermal-deposition` | ✘ nucleation + species |

    **Both covering mechanisms were already DECLARED, under exactly these two
    names**, in `properties/solid_state.py`, and both are pinned by
    `tests/test_solid_state.py` at 25.4 s at 1000 K and 43.7 s at 450 K. So
    unlike S1, the two credited rows are rows that RUN.

    ## ⚠⚠ THE INSTRUMENT FIRST: THE COVERAGE REPORT WAS NOT BYTE-STABLE

    Regenerating `COVERAGE_REPORT.md` at HEAD -- the project's own rule, because
    a committed generated report is not a baseline -- produced a **17-line diff
    with every number identical**. `sorted(covered, key=lambda x:
    -step_classes[x])` sorts a **SET** with no tie-break, so classes with equal
    step counts came out in `PYTHONHASHSEED` order. The `missing` table eight
    lines below it already had the `(-count, name)` tie-break; this one had been
    missed.

    ⚠ **A REPORT YOU CANNOT DIFF IS A WEAK INSTRUMENT.** 17 lines of pure noise
    per regeneration is enough to hide a real one-line change in review, which
    is precisely what this file is regenerated *for*. Fixed (one line), and
    verified the way S2 verified its harness: **byte-identical across
    `PYTHONHASHSEED=0` and `=1`.** The greedy `max` at line 446 already carried a
    `c` tie-break, and the dict-item sorts are insertion-ordered, so this was the
    only unstable site.

    ## ⚠⚠ AND THE OTHER GENERATED FILE WAS STALE BY THREE MILESTONES

    `ROUTE_INDEX.md` had **not been regenerated since the initial commit**, while
    `route_steps.psv` was re-labelled by M5, M6 and S1. Regenerating it moved
    **21 class labels: 11 from M5, 5 from M6, 1 from S1 and 4 from S3.**

    ⚠ **It is the one generated file no audit reads** -- `catalog_coverage.py`
    parses `route_steps.psv` directly -- so a stale index changes no measured
    number, fails no test, and warns nobody. Anyone who read the index to find a
    step's class between M5 and S3 got a pre-M5 answer. The project's rule was
    already "a committed generated report is not a baseline"; what this adds is
    that the rule has to cover the artefact NOTHING checks, because that is the
    one that rots silently. `data/catalog/README.md`'s regenerate block now says
    so.

    ## ⚠⚠ WHICH ROUTES IT MOVED: ZERO -- PREDICTED, THEN MEASURED

    S1's third mistake is now a standing check, and this is the first time it was
    run *before* crediting rather than after. All four affected routes are
    blocked on a SECOND uncovered class -- `hydrolysis`,
    `carbonate-equilibrium`, `trimerisation`, `dissolving-metal-reduction` -- so
    no route could move. Measured: **33/215 classes -> 35/218, covered steps
    95 -> 97, template-ready routes 27 -> 27.**

    ⚠ **AND THE GREEDY CURVE'S "+1 route" FOR THIS CLASS WAS NEVER A STANDALONE
    UNLOCK** -- it sat at rank 14, i.e. after `hydrolysis` was added at rank 6.
    Read as a promise it would have delivered a route it cannot. The standalone
    table is the one that answers that question and it never listed the class.
    Same misreading as S1's, from a different table.

    **What DID move is the shape of the remaining work, and that is the part
    worth acting on:** `solvay-process` and `vitriol-distillation` both went from
    two classes away to ONE, so routes-one-class-away went 58 -> 60 from 44 -> 46
    distinct classes, and **`hydrolysis` jumped to greedy rank 4 (+2 routes)**.

    ## ⚠⚠ ONE CREDIT IS A LATENT FALSE CREDIT, AND THE SPLIT MADE IT NEARER

    `vitriol-distillation` step 1 reads `iron-ii-sulfate -> iron-ii-OXIDE +
    sulfur-trioxide`; the declaration makes HEMATITE, `2 FeSO4 -> Fe2O3 + SO2 +
    SO3`. The credit is honest for the **opposite** reason to cinnabar's, and
    being able to tell the two apart is the whole value of the check:

      * **cinnabar** -- the ROW is right and the mechanism stops short of it, so
        the row needs a second reaction nobody built. Not covered; re-labelled.
      * **green vitriol** -- the MECHANISM is right and the ROW is wrong. FeO does
        not survive red heat and `mineral_data` refuses it anyway (no crystal Cp
        in CRC). Nothing further is needed to reach the real products.

    ⚠ **THE LANDMINE:** the class is credited and the row still names a product
    this engine never makes. Inert today, because step 2 is uncovered. **The day
    `hydrolysis` is credited, `vitriol-distillation` goes template-ready on a
    step whose stated product does not exist in the run** -- and this split just
    made `hydrolysis` the 4th-best template to build. Not corrected in the
    corpus, on the `diels-alder-route` precedent; correcting it means
    re-balancing to 2 FeSO4 and adding an SO2 nobody wrote.

    ⚠⚠ **MEASURED, AND SHARPER THAN "SOMEDAY": `hydrolysis` unlocks exactly ONE
    route on its own, and it is `vitriol-distillation`.** The entire standalone
    payoff of the 4th-ranked template is the one route carrying a step whose
    product the engine does not make.

    ## THE TWO GAPS COST DIFFERENT AMOUNTS, WHICH IS WHY THEY ARE TWO CLASSES

      * **`urea-deammoniation` is blocked on a TEMPLATE ONLY.** All three species
        resolve and the kernel can already express a unimolecular decomposition
        in a liquid -- urea melts at 406 K and the row runs at 620 K, so it is a
        liquid-phase graph rewrite, not a lattice. ⚠ Caveat that is a physical
        fact, not a gap: cyanic acid is one of the nine neutral species with no
        boiling point in ANY source, so it is `nonvolatile` and cannot enter the
        gas block -- the HNCO would come off into the liquid.
      * **`hydride-thermal-deposition` is blocked on BOTH, and its mechanism gap
        has a name: NUCLEATION.** `SurfaceArrays` is first order and EXTENSIVE in
        the solid amount, so a solid at zero mol has zero rate for ever -- and the
        term is irreversible by construction, so no roasting row can be run
        backwards to deposit one. Depositing a solid from no solid is not
        expressible here at all. `arsine` and `arsenic` are both refused outright,
        independently.

88. ✔✔ **A ROUTE EMERGED. `mercury-from-cinnabar` RUNS, OUT OF TWO DECLARATIONS
    THAT DO NOT MENTION EACH OTHER — AND THE RE-LABEL S1 MADE WAS *NOT*
    REVERSED.**

    S1 credited `roasting`, found it had claimed a route whose product its term
    does not make, split the row out as `roasting-to-metal` and named what was
    missing: "a second reaction nobody built". It is three lines:

        properties/surface.py      2 HgS + 3 O2 -> 2 HgO + 2 SO2   SurfaceArrays
        properties/solid_state.py  2 HgO        -> 2 Hg  +   O2    SolidStateArrays
        --------------------------------------------------------------------
        what a retort does           HgS +   O2 ->   Hg  +   SO2   NOBODY WROTE IT

    Sealed 10 L retort, pure oxygen, 0.02 mol of cinnabar, 900 K:
    **0.020000000000 mol of mercury and 0.020000000000 mol of SO2 on 0.020000
    mol of oxygen consumed.** The catalog row, coefficient for coefficient.
    **35/218 → 36/218 classes, 97 → 98 steps, 27 → 28 template-ready routes**,
    and unlike S1's `pyrite-roasting` this one RUNS end to end.

    ## ⚠⚠ THE BRIEF SAID TO REVERSE THE RE-LABEL. BOTH WAYS WERE MEASURED

    |  | classes | routes |
    |---|---|---|
    | keep `roasting-to-metal` | **36/218** | 28/173 |
    | fold back into `roasting` | 35/217 | 28/173 |

    **The routes are identical, so the choice is only about what the class column
    says.** `roasting-to-metal` records a MECHANISM difference and not an
    outcome: this ore's oxide does not survive the furnace that makes it, which
    is why one row needs two mechanisms where the other four need one.
    `solid-carbonation` is the precedent. Folding back would delete the
    distinction S1 paid to find, for a smaller denominator.

    ## ⚠⚠ THE FIRST ROW WHOSE PRODUCTS ARE ALL GAS, AND IT BROKE A BOUND

    `units_rev` is a minimum over the solids FORMED, and over an empty set that
    is `+inf`. **Measured before it was fixed: a sealed 1 L retort holding 0.5
    mol of montroydite at 900 K raised `array must not contain infs or NaNs`**
    the instant `Q` crossed `K` — which it does at that charge, `ln K` being only
    +9.2 there. ⚠ **At 0.05 mol in the same flask it never crosses and the run is
    clean, so the failure had a CHARGE threshold as well as a temperature one —
    and the small charge is the one an example would have been written with.**

    **Infinity was the wrong bound, not a bound needing softening.** The four
    existing rows say what the right one is: calcination's reverse is bounded by
    `n(CaO)`, the SEED, not by the CO2 pressure, which is in `Q`. This engine
    cannot nucleate a solid from nothing (S3 named that), so a row with no solid
    product deposits onto its own REACTANT crystal. `units` therefore stays a
    COMMON FACTOR — the sealed 0.5 mol run stalls at 71.8% with Q and K agreeing
    to 0.05% — and an exhausted charge stops it in BOTH directions, which is the
    nucleation gap stated rather than worked around. **The four pre-S4 rows are
    bit-for-bit unmoved**, pinned.

    ## ⚠⚠ MERCURY IS IN `element_data`, AND BOTH REFUSALS WERE ABOUT REPRESENTATION

    `[Hg]` was refused as "a metallic lattice" and as a bare monatomic symbol
    whose "ideal-gas record is the ATOM, not the substance". Both true of the
    bonding, false of the representation: **its reference state is a LIQUID with
    a boiling point**, which the liquid block holds, and **its vapour IS the
    atom** — it boils monatomic at 629.8 K. Hf +61.40, Gf +31.853 kJ/mol, a
    condensed reference state like bromine's. Pinning it to zero would be the I2
    bug again.

    **Two free exact checks came with it, one new to that table:**

      * **Cp = 5R/2 = 20.786 J/(mol K) EXACTLY at every temperature.** Every
        other Cp there is a fit with a residual; this one is an answer.
      * **the condensed-reference-state identity closes to +0.012 kJ/mol** — the
        tightest of the four (Br2 −0.053, I2 +0.139, S8 +3.052).

    ⚠⚠ **AND THAT SECOND CHECK IS WHAT CAUGHT LEE-KESLER.** Over a liquid METAL
    the estimated vapour pressure reads **38.3 kPa at 523 K against CRC's 10.0 —
    3.8x — while agreeing at the boiling point to five figures, because it is
    ANCHORED there.** "Boils at 1 atm is not an independent check", arriving with
    a real cost: the condenser panel would have been wrong by that factor. A
    curated NIST Antoine (within 2% of CRC over five decades) takes the residual
    from +2.808 to +0.012.

    ⚠ **And dropping it in would have BROKEN a stated invariant.**
    `build_element_data` differentiates `Hvap` out of the Lee-Kesler curve so the
    latent heat cannot disagree with the vapour pressure — but `volatility`
    prefers a curated Antoine, so that is no longer the curve the engine
    evaluates. The generator now takes Clausius-Clapeyron on the CURATED curve:
    **59.444 kJ/mol against Lee-Kesler's 57.344 and CRC's measured 59.11.**

    ## ⚠⚠ TWO INSTRUMENTS WERE WRONG, AND BOTH WERE FOUND BY THE NEW ROW

      * **the curated-source guard falsely refused CRC's own measurement.**
        `CURATED_FORMATION` is a PREFIX MATCH ON A PROVENANCE STRING, so it tests
        how a sentence begins. A gaseous reference state says "element reference
        state (gaseous)" and passes; a CONDENSED one says "Hf and S0 both from
        CRC …" and was read as an estimate. **It would have refused a row
        evolving Br2, I2 or S8 identically.** Widened by one prefix; the weakness
        is the mechanism, and moving the tier into `ThermoData` reaches every
        Layer-1 provider, so it is stated rather than done.
      * **`validation/rate_ceiling.py` could not see the table it needed to.** It
        claims "nothing approaches the unimolecular ceiling" — a claim about
        every rate constant in the project — while its panels walk
        `net.reactions`, which `SOLID_STATE_REACTIONS` never becomes. A fourth
        panel now reads it. The claim holds at 298 K by 26 decades. The hot half
        does not: **S4's row is 1.93e18 1/s and crosses 1e14 at 3710 K, inside
        the RHS's own 5000 K clamp**, the first row in the project to do so, and
        `sulfate-thermal-decomposition` crosses at 7543 K and had never been
        measured either. Reported, not guarded — the constant multiplies both
        directions of an affinity flux, so it moves a CLOCK and not an
        equilibrium.

    ## FOUR MECHANICS NOBODY WROTE

    | | measured |
    |---|---|
    | the intermediate is INVISIBLE | montroydite's inventory is the roast's rate times its own clock: **8e-7 mol at the start, 3.4e-8 by 20 ks.** Its clock at 900 K is 0.24 s against the roast's 5,918 s |
    | **the two clocks CROSS** | 304.4 kJ/mol DERIVED against 150 DECLARED, so cooling slows the first far faster — equal at **611.7 K**. The oxide's share of the mercury released: 2.0e-6 at 900 K, 4.3e-4 at 773, 1.9e-2 at 700, 0.341 at 650, **0.913 at 600**. Nothing gates on temperature |
    | a retort CONDENSES | cool the same flask to 400 K and **97.9%** of the metal is in the liquid block |
    | the oxide CANNOT come back | at 400 K, **289 K below its own threshold**, in a flask full of mercury vapour and oxygen — no oxide forms, because there is none left to grow on |

    `examples/mercury_retort.py`, six panels, 4 s. 14 tests, 4 s.

    ⚠ **THE TOLERANCE AUDIT WAS RE-RUN AND S2's FINDING IS UNMOVED:** across 12
    examples **no example prints a quotable digit that moves**; 5 move below
    0.1% (S2's exact list) and 7 are byte-identical, `mercury_retort` joining
    them. It is the audit's THIRD self-check example — `lime_cycle` 1.00,
    `roasting_and_the_catalyst_gate` 0.99, `mercury_retort` 1.00, all three
    OUTPUT IDENTICAL, which is what says the harness's default-rebinding still
    cannot touch an example that passes its own rtol. ⚠ One counter moved and it
    is JITTER, not a regression: "tight is faster in 1 of 12" against S2's "2 of
    11", and the example that left that column is a self-check one landing at
    0.99 rather than 1.00 with output identical by construction.
    ⚠ **The whole suite: 815 passed in 11:50** — the first measured green number
    since S1's last fix, which left it at 796 passed / 1 failed and was never
    re-run. `COVERAGE_REPORT.md` re-verified byte-identical across
    `PYTHONHASHSEED` 0, 1 and unseeded.

    ⚠ **NOT MODELLED, STATED:** liquid mercury is **99.85% HELD IDEAL** (a metal
    has no UNIFAC groups, so γ is DECLARED 1 — what M4 built that flag for), and
    the visible cost is O2 and SO2 dissolving in the pool on Henry constants
    measured IN WATER: **0.14% of the SO2**, named and bounded.

    ## ⚠⚠ AND A FIFTH INSTRUMENT FINDING, FROM RECONCILING THE REPORT DIFF

    Every changed line in `COVERAGE_REPORT.md` is a real consequence — S3's
    byte-stability fix held. Reconciling them turned up a column that has been
    understating itself since M3.

    **`species-ready` is blind to `mineral_data`.** It asks whether every species
    resolves under the plain `ThermochemistryProvider`, which REFUSES A LATTICE
    BY NAME — correctly, the fusion law being 407x wrong for one. But a lattice
    has had a home since M3, on the solid basis, and it is what precipitation,
    `SolidStateArrays` and `SurfaceArrays` all price from.

    **Measured: 14 routes read species-UNREADY while every refused species is a
    mineral this project prices** — 49 of 173 where the honest number is at most
    63. Among them: `lime-cycle`, which M6 declared complete end to end from
    limestone and which `examples/lime_cycle.py` runs; and `haber-bosch` and
    `methanol-synthesis`, where the only "refused" species is **the solid
    CATALYST S1 curated so it could be put in the flask.**

    ⚠⚠ **It is the exact OPPOSITE shape to `pyrite-roasting`** — that reads
    template-ready and does NOT run; this reads species-unready and DOES. Two
    columns, two directions of error, neither a bug in the engine, and having
    both is what makes the pair informative.

    ⚠ **NOT FIXED, DELIBERATELY** — it changes a published column's definition,
    so it owes the standing "which routes does it move" check and a verification
    pass. Recorded at the line that computes it. Next session's instrument job.

    ⚠ One more thing the diff paid for: **`castner-kellner` became species-ready
    AND fully sourced** (48 → 49, 4 → 5). Curating one element paid somewhere
    nobody was looking.

89. ✔✔ **THE OLDEST LIVE FRAGILITY IS BOUNDED — AND THE FIX WAS SCHEDULED FOR
    THE WRONG LAYER, WHICH ONE MEASUREMENT SAID.**

    The brief was a `LAYER_REABSORB`-style honest diagonal on the GAS block. What
    shipped is `src/chemsim/numerics/jacobian.py`: a bound on BDF's differencing
    STEP, at all three `solve_ivp` sites. **No chemistry moved and the gas block
    was not touched.**

    ⚠⚠ **FOUR OF THE FIVE RECORDED TRIGGERS DO NOT REPRODUCE.** Every one was
    re-run first. M6's sealed lime kiln at 0.05 mol with N2/O2 absent — the row
    that read "RAISED: CO2 reached −2.572 mol" — now runs clean at
    `p/K − 1 = −1.56e−04`, because S4 changed `SolidStateArrays.units`, not
    because anything was fixed. `fragilities`' `kla=0` case has never been made
    to fire at all. **A fragility that no longer fires is not one that was
    closed, and the difference is only visible if you re-run it.**

    ⚠⚠ **THE FIFTH FIRES, AND IT IS NOT IN THE GAS BLOCK.** `oil_of_vitriol` at
    rtol 1e-8 still raises after 52.7 s. Instrumented: of 4322 `num_jac` calls,
    exactly ONE column reaches `inf`, and it is **liquid layer 2's SO2 holding
    8.21e-29 mol**. Every other column tops out at 1.49e+3. It is not absent and
    not flat — it is FROZEN: `LAYER_REABSORB` drains an empty layer 2 at
    `−1.0·drain2·nL2`, strictly negative, so `num_jac` takes `f_sign = −1` and
    steps DOWNWARD into the RHS's own `np.maximum(y, 0.0)`.

        h            -2.2e-24   -2.2e-19   -2.2e-14   -2.2e-09   -2.2e-04   -2.2e+06
        max |diff|    8.84e-29   8.84e-29   8.84e-29   8.84e-29   8.84e-29   8.84e-29

    Constant over **thirty decades of step size**, against a `scale` of 8.37e-14
    from a different species' row. Twenty-eight consecutive calls at one unchanged
    state climb a decade each; two hundred later the factor reads **2.220e+307**.
    ⚠⚠ **The term the brief named as the precedent to copy is what points the
    probe at the clamp**, and a diagonal on the gas block could not have reached
    that column.

    ## ⚠⚠ THE FIRST BOUND WAS WRONG AND THE EXAMPLE SET IS WHAT SAID SO

    `h = factor · max(atol, |y_j|)`, so the obvious bound is "`factor = 1` moves
    the variable by all of itself". Implemented, swept on four runs, all four
    bit-identical — **and wrong**, because where `|y_j| ≤ atol` the fraction is of
    ATOL: `factor = 149` on an absent species is a 1.5e-7 mol probe of a 0.1 mol
    flask. Run across all sixteen examples, **8 of 16 moved**, six of them in a
    real digit: `roasting` SO2 0.000201 → 0.000197 mol, `fractional_distillation`
    tail 0.0702 → 0.0711 mol and +59% wall clock, `multistep_prep` closure
    100.0127% → 100.0017%.

    ⚠ **A FOUR-RUN SWEEP IS NOT THE EXAMPLE SET.** That is what
    `validation/jacobian_bound.py` exists to catch, and panel 3 is the check that
    would have rejected the 1.0 ceiling before it shipped.

    ## THE BOUND THAT SURVIVED

        |h_j| <= max_i |y_i|    i.e.   factor_j <= max_i |y_i| / max(atol, |y_j|)

    *A difference quotient is a derivative of THIS system only while the probe
    stays inside it.* Per column, per call, from the state, **no constant in it.**
    On a single vessel it never binds — the busiest asks for 1.490e+09
    (`extraction`) against a bound of order 1e11–1e12. On the failing column it
    lands at 6.9e13, finite, which is all the crash needed: swept, **every finite
    ceiling from 1e2 to 1e14 turns the raise into 0.0160000000**.

    ⚠⚠ **IT DOES BIND ON A RIG.** `fractional_distillation` wants 3.252e+12 and is
    clamped in 232 of its 1833 Jacobians, moving its three cuts in the SEVENTH
    significant figure. Measured against a converged rtol 1e-8 run: at the tight
    tolerance the heart and tail are **bit-identical** bounded and unbounded, so
    the two converge to the same answer; at the default neither is systematically
    nearer, and every difference is **≤ 1e-6 relative, three decades under the
    1e-3 band `tolerance_audit.py` itself calls a quotable digit.** ⚠ And what the
    rig wanted is worth looking at before mourning it: 3.25e+12 against
    `atol = 1e-9` is a probe of **3250 units** on a species holding nothing. The
    seventh-figure move is the difference between two fictions.

    ⚠ The rig runs ~122 Jacobians per solve against the ~316 an overflow needs.
    **It is one longer run away from the same crash.**

    ## WHAT IT DOES NOT FIX, STATED

    The burner still takes ~53 s at rtol 1e-8 against 0.8 s at the default. BDF is
    genuinely struggling with a layer holding 1e-29 mol; the bound stops that
    ending in a NaN and does not stop the struggle. **The 1.0 ceiling ran it in
    2.6 s — a faster wrong number is not a better one.** Nor does it make a flat
    column non-flat: an absent species still has an identically zero column, and
    **zero is the correct derivative for it**. What changes is that `num_jac`
    stops treating "I measured zero" as "I failed to measure".

    ## S2's ONE COVERAGE GAP IS CLOSED

    `KNOWN_REFUSAL` is empty; `oil_of_vitriol` is in `EXPENSIVE` and completes.
    ⚠ S2's diagnosis was **right about the answer and wrong about the column** —
    it read "a species absent from a sealed flask", and it is layer 2's SO2,
    frozen rather than flat.

    ⚠ `jac_sparsity` is **consumed** by `BoundedJacobian`, not passed alongside:
    BDF ignores `jac_sparsity` the moment `jac` is callable, so a rig handing over
    both would silently lose the column groups `useful_sparsity` computes — the
    10x it exists to avoid paying. Pinned by a test.

IMMEDIATE NEXT TASK: see **`MILESTONES.md`**, which is the plan of record as of
2026-08-22 and supersedes the ordering below. It is derived from `data/catalog`
(1,583 compounds, 173 routes) plus four measured capability probes, and it
promotes three things this list had low or missing: **rigs and fraction cuts in
`World`** (a still works; a CUT cannot be expressed), **a solubility product**
(no ion can precipitate at all -- there is no Ksp anywhere), and **the UNIFAC
gap** (silent, unlike a missing template). The list below is still accurate as
the ENGINE backlog; MILESTONES.md is what to do in what order.

Superseded ordering, kept for the record: see **NEXT_SESSION.md**. Both of last session's walls are
down; the one below is what closing them found. In order:

1. ⚠⚠ **THE DRYOUT BAND** (item 70). A measured wrong answer -- 111% yield --
   with a reproduction that runs in seconds, a convergence diagnostic that
   proves it structural, and three overlapping gates already located. It is the
   last member of the ``N/(N+eps)`` class still live, and it bounds where any
   chain may be run near a boiling point.
2. **CHAIN 1, aspirin from wintergreen.** Steps 1-3 are the flagship prep with
   different species. Salicylate's pKa is in; still needs two anhydride
   templates. ⚠ The carbonate lines are NOT a data job -- item 65.
3. **A curated overlay for aspirin and salicylic acid**, whose formation halves
   are both Joback -- named by `validation/game_gates.py` panel 3, and the
   acetylation K is chain 1's weakest number.
4. ~~SOLID-PHASE REACTIONS~~ -- **DONE, item 84**, and the gas-CONSUMING half is
   **DONE, item 85.** ⚠ But NOT for the
   green-vitriol seed: `FeSO4 -> Fe2O3 + SO3` needs an Fe2O3 mineral entry that
   does not exist, and the claim that the seed's data "is curated and waiting"
   was checked and is half wrong -- true of the reactant, false of the product.
   The engine half is built; that row is a curation job.
5. **THEN dissociation as an equilibrium.** Stiffness ratio 7.05e21. Deliberately
   after there are chains to measure it against, and there are now two.

FURTHER OUT: ⚠ **THIS LIST IS SUPERSEDED BY `MILESTONES.md` M8-M11, WHICH NOW
OWN ALL THREE ITEMS PLUS TWO THE LIST DID NOT HAVE.** Kept for the reasoning:
1. Non-mass-action rate laws (Langmuir-Hinshelwood, Michaelis-Menten) so
   heterogeneous catalysis and enzymes have somewhere to live. Requires the
   numerics kernel to admit rate forms beyond A*exp(-Ea/RT) -- a surface has a site
   balance, which is why HOMOGENEOUS catalysis was free (item 37) and this is not.
   **Now M10.** ⚠ Measured 2026-08-24: it blocks 8 routes and one of them is
   `ethanol by fermentation` -- brewing, the oldest applied chemistry in the
   catalog. It was the largest UNOWNED wall in the project.
2. Electrochemistry (electrode potentials, Faraday's law) -- gates chlorine and
   NaOH (chlor-alkali), PEDOT, polyaniline. **Now M8.**
3. Polymers as chain-length distributions (population balance / method of
   moments). Note this is the SAME problem as the network explosion, seen twice:
   species enumeration is the wrong representation for a polymer. **Now M9**, and
   it is 12 routes -- Bakelite, nylon 66, PET, polyethylene, PVC, PTFE.
4. **NEW, and it had no owner: the UNPRICEABLE FAMILIES (M11).** 16 routes touch
   a compound class nothing here can price -- isocyanates, sulfonic acids,
   organometallics (Grignard, Wittig), azo dyes, pigments, sulfonamides. ⚠ The
   costed starting point has been sitting idle: **10 species need exactly ONE
   measured boiling point each**, named in `data/catalog/COVERAGE_REPORT.md`.
5. **NEW, and stated as NON-GOALS rather than work**: photochemistry (costs ONE
   catalog step), stereochemistry control (costs ZERO), and absolute reaction
   TIME (permanent -- A-factors cannot be derived, only bounded or declared).
   See MILESTONES' "STATED NON-GOALS" section for why each is written down.

KNOWN ISSUES worth fixing opportunistically:
- ⚠ **`exp(-a_mn/T)` OVERFLOWS BELOW 4.28 K FOR THE PSRK `H2O <-> N2` PAIR, AND
  THE RHS CLAMP `T_MIN` IS 1.0** -- i.e. the clamp that protects the correlations
  lands inside the band that breaks this one. Reachable whenever `num_jac` probes
  the temperature column and the basis holds water and nitrogen. **Measured
  inert** (clipping the exponent changes no number, no timing, no residual), so
  it is reported rather than refused; item 80 has the reproduction. The fix has a
  precedent in the same file (`gamma_ref_range`) and needs the full suite behind
  it.
- ⚠⚠ **THE DRYOUT BAND** -- item 70, and not opportunistic: it is the top of the
  list. Three overlapping gates make mole fractions sum to 0.57 and a sulfur burn
  at 690 K report 111% yield. Last live member of the `N/(N+eps)` class.
- **A stiff reactant driven to EXACTLY zero still overshoots**, at the 1e-4 level.
  Reported, and it CONVERGES under refinement (which is how it was told apart
  from item 70). Belongs with dissociation-as-an-equilibrium, which now has a
  convergence test to measure a fix against.
- ~~A catalytic cycle seeds itself from round-off~~ -- **FIXED, item 67.**
- ~~The kernel cannot express a declared rate order~~ -- **FIXED, item 69**, and
  it did NOT close the LHHW/Michaelis-Menten item below: still no site balance
  and no saturation term.
- ~~NO SOLID-PHASE REACTIONS~~ -- **BUILT, item 84**, as a TERM rather than a
  third `PHASE_INDEX` entry, and the choice was measured. What is still missing
  is the OTHER solid mechanism: a gas-CONSUMING surface reaction (`roasting`, and
  the five heterogeneous templates that fold a catalyst into an apparent
  barrier). That one IS mass action and it IS the third `PHASE_INDEX` entry.
  ⚠ The green-vitriol seed `FeSO4 -> Fe2O3 + SO3` is now blocked on DATA alone:
  there is no Fe2O3 entry in `mineral_data`, and item 84's term would run the row
  unchanged the day there is one. Item 84 corrects the sentence this bullet used
  to end with: the seed's solid-basis data is curated for the REACTANT and not
  for the product.
- **`tools/build_physical_data.py` CLASSIFIES `CRC_INORG` AS ESTIMATED**, which
  it is not -- harmless there because every candidate in that script is organic,
  and it would have refused the entire mineral floor. Worth correcting if that
  script ever gains an inorganic candidate.
- **Primary alcohols read ~7 kJ/mol too negative under Benson.** RMG pairs
  Paraskevas's CBS-QB3 alcohol groups with Benson's alkane groups and has no
  alternative entry, so this is an inconsistency in the source. Reported by
  `validation/benson_accuracy.py`; do not "fix" it with a transcribed number.
- **Benson refuses pyridine, nitrobenzene and aromatic esters, permanently from
  this source.** RMG has no aromatic-nitrogen groups, no nitroaromatic groups and
  no pyridine ring correction; the aryl-ester carbonyl is on an incompatible
  tabulation split. They keep Joback and say so.
- **No IONIC-STRENGTH model (Debye–Hückel / Davies) -- but this is no longer the
  blocker it was.** Ion TRANSFER between phases is modelled now (Born, item 28),
  which is what lifted the electrolyte refusal. What remains is ionic strength
  WITHIN one phase, and adding it would presently change nothing measurable: an
  ion's γ reaches only phase equilibria and the ionic rate correction, and both are
  dominated by a factor of e^12. **Salting-out needs the activity basis for
  NEUTRAL species first**, not an ionic-strength term for the ions.
- **A dielectric decrement for ions.** A real salt lowers water's permittivity
  substantially (~-11 per mol/L for NaCl); ions are deliberately excluded from the
  medium entirely, because putting them in gets the low-concentration sign wrong.
  It belongs with Debye–Hückel.
- Gas solubility outside water is PREDICTED, not measured — it runs ~25% low for
  common organics and 2.6× high for acetone. Only the aqueous constants are
  experimental.
- The gas extension joins two regressions (UNIFAC organic + PSRK gas). Defensible
  because the backbones agree, but it is not one self-consistent fit.
- **Inconsistency BETWEEN tabulated formation values is now the dominant error
  in K**, having overtaken Joback. Acetic acid + five alcohols spans 4.5 kJ/mol
  of gas-phase dG_rxn where the chemistry says it should be flat to ~1, methanol
  being the outlier. That is in the sources, not in anything we do to them. See
  the homologue panel in the harness.
- **Curated formation data reaches species Joback can fragment, plus nine named
  exceptions.** It is an overlay on his record, so the general gap the coverage
  audit found (aryl aldehydes, formamides, sulfoxides, anhydrides as CLASSES)
  still needs Benson. Nine specific species now have full assembled records.
- **Equilibrium is still on a CONCENTRATION basis, not an activity basis.** gamma
  corrects phase equilibria and solubility but not the reaction quotient. Fixing
  it means rate laws on activities (use gamma*c in `_phase_rates`), which is a
  one-line kernel change but redefines every A and would need the electrolyte
  work re-calibrated. **Still measure before doing it, but the reason has
  changed**: it is no longer that gamma clearly makes things worse (with curated
  data it now helps on one case and hurts on the other), it is that the two
  cases disagree by 4.9 kJ/mol and that disagreement IS the homologue spread
  above. Calibrating now would fit the activity model to a bad methyl acetate.
- UNIFAC understates the temperature slope of an associating solute's solubility
  (benzoic acid 0.95× at 298 K but 0.48× at 333 K). Absolute scale good, slope not.
- Joback's Tm is its weakest output (benzoic acid 355.7 K vs 395.6 K real) and
  drives solubility exponentially. `thermochemistry._CURATED_FUSION` now overlays
  measured Tm/Hfus for benzoic acid, naphthalene, urea and salicylic acid; it is
  an overlay, not a full curated entry, because Joback's OTHER outputs for those
  species are fine. Extend it as more solids matter.

RESOLVED since the last handoff:
- Ideal solubility used to cover both melting and dissolution. They are now
  separate: `saturation_activity(T)` is the composition-independent fusion law
  (still exactly 1 at Tm, so melting is untouched) and `solubility(T, gamma)`
  divides by γ. Melting must not care how badly a solvent dissolves the solid.

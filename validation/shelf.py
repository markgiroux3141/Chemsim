"""P3/P4's standing audit, and the R-series' opening measurement.

The shelf, the two forms of a rock, the burner, and what a FIXPOINT costs.

Run: ``python validation/shelf.py``   (~5 min, no scorer import)
     ``python validation/shelf.py --mass-cap`` adds panel 5F's live sweep,
     which is ~6.5 minutes on its own and is RECORDED rather than re-run
     by default. It is the only sub-panel here that is not measured live.

Five panels, and each one exists because a decision was made from it.

**PANEL 1 -- THE SHELF IS DATA AND ITS SHAPE IS MEASURED.** 71 rows in three
tiers, 7 of them refused a price and kept anyway, 1167 priced species on the
cheat axis, 416 that may never be charged. The tier column is what lets the
shelf shrink: an ``intermediate`` row is deleted the day its stranded route
becomes reachable.

**PANEL 2 -- ⚠⚠⚠ A ROCK HAS TWO REPRESENTATIONS AND THEY ARE NOT
INTERCHANGEABLE.** The obvious resolution rule -- charge a mineral as its
``mineral_data`` lattice -- puts five shelf rows into the flask as matter no
mechanic in this engine can touch. Rock salt as ions in the solid block
dissolves; the same rock salt as its lattice sits there for ever. Measured in a
flask, both ways, because nothing static says so.

**PANEL 3 -- ⚠⚠⚠ AND SIX TEMPLATE FIELDS WERE NOT REACHING THE ENGINE.**
``TemplateSpec`` -- the only way a frontend can describe chemistry to a
``Scenario`` -- was dropping ``orders``, ``solid_catalyst``, ``electrons`` and
the three ``hammett_*`` fields. So the shelf's own sulfur would not burn: the
burner declares first order in oxygen and the network ran the SMARTS' own
ninth-body mass action. **This was found by PLAYING the game.** The panel
measures the burner both ways.

**PANEL 4 -- THE PLAYED SESSION.** Sulfur, air, water and a trace of NO2 off the
shelf, at one generation and then two: SO2 first, then sulfuric acid. The
game's own chain 2, out of the picker, in two presses of a button.

**PANEL 5 -- REACT UNTIL DONE, AND WHAT IT COSTS.** ⚠⚠⚠ The
generation bound is an OBJECTION before it is a design: *in the real world
these materials would continue to react until everything was done -- it
would not stop artificially at sulfur dioxide and need a deliberate
trigger.* That is correct, and section 8.2 concedes it. So this panel
measures whether the bound can simply be dropped. **It can, for the whole
inorganic half of the shelf** -- panel 4's own pick closes at 14 species
with an empty frontier in a couple of seconds. It cannot for sugars, and
the reason is not discovery cost: a fixpoint is ~150x more expensive to
**INTEGRATE**, because the solver evaluates 644 reactions -- nearly all of
them kinetically dead at 298 K -- on every right-hand-side call. Sub-panel
D settles what the extra 624 buy at 300 s and 297 K, which is *nothing as
big as a micromole*; sub-panel E is the crash that has to be closed before
anything explores deeper; sub-panel F is the refutation of a molar-mass
cap, which made the network BIGGER.

⚠ **AND F's OWN BASELINE IS A CORRECTION.** The first write-up of that
sweep recorded the uncapped build at 10.9 s, which made the 250 g/mol run a
35x slowdown. Sub-panel B builds the identical network live and has now
measured it three times at 19.8 / 20.1 / 20.2 s, so the figure is **19x**
and the 10.9 s should not be quoted again. *Two numbers for the same build
sitting in one panel is exactly why the expensive half is recorded WITH the
cheap half that contradicts it, rather than on its own.*

EVERY PRINTED LINE HERE IS ASCII. The console is cp1252 and a warning glyph in a
``print`` kills the script mid-panel. Glyphs belong in docstrings and comments.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from chemsim.engine import inventory as inv  # noqa: E402
from chemsim.engine.scenario import TemplateSpec  # noqa: E402
from chemsim.engine.world import World  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.properties.mineral_data import MINERALS  # noqa: E402
from chemsim.properties.solubility_product import (  # noqa: E402
    UnpricedLattice,
    solubility_product,
)
from chemsim.reactions import ReactionTemplate  # noqa: E402
from chemsim.ui.examples import bench, full_library  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402

QUIET = io.StringIO()
S8, O2, N2, WATER, NO2 = "S1SSSSSSS1", "O=O", "N#N", "O", "O=[N+][O-]"
SO2, VITRIOL = "O=S=O", "O=S(=O)(O)O"


def rule(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


def _dissolves(rec):
    """Can ``PrecipitationArrays`` move this lattice between solid and solution?

    The same predicate ``tools/build_shelf.py`` resolves rows with. A metal's
    ``ions`` is empty on purpose, and quicklime has no aqueous Ksp because CaO
    hydrates rather than dissolving -- both refusals are chemistry.
    """
    if not rec.ions:
        return False
    try:
        solubility_product(rec)
    except UnpricedLattice:
        return False
    return True


def total(state, smiles):
    return (state.n_liquid.get(smiles, 0.0) + state.n_liquid2.get(smiles, 0.0)
            + state.n_gas.get(smiles, 0.0) + state.n_solid.get(smiles, 0.0))


# ---------------------------------------------------------------------------
def panel1():
    rule("PANEL 1 -- THE SHELF, AS DATA, IN THREE TIERS")
    got = inv.counts()
    print(f"  shelf rows                                       {got['rows']:5d}")
    for tier in inv.TIERS:
        print(f"     {tier:<12}                                {got[tier]:5d}")
    print(f"  ... REFUSED a price and kept anyway              "
          f"{got['shelf refused']:5d}")
    print()
    print(f"  corpus species                                   {got['corpus']:5d}")
    print(f"  ... chargeable  (the cheat axis)                 {got['priced']:5d}")
    print(f"  ... refused, shown greyed WITH THE REASON        {got['refused']:5d}")
    print()
    forms: dict[str, int] = {}
    for item in inv.shelf():
        forms[item.form] = forms.get(item.form, 0) + 1
    print(f"  how a row is CHARGED: {forms}")
    print()
    print("  The tier is the whole design argument: an `intermediate` row is")
    print("  deleted the day its stranded route becomes reachable, and the")
    print("  player earns it instead. A flat list of names cannot say that.")
    print()
    print("  The 7 refused rows, with the engine's own reason:")
    for item in inv.shelf():
        if not item.chargeable:
            print(f"     {item.id:<20} {item.refusal.splitlines()[0][:64]}")


# ---------------------------------------------------------------------------
def panel2():
    rule("PANEL 2 -- A ROCK HAS TWO FORMS, AND FIVE SHELF ROWS TURN ON WHICH")
    rec = MINERALS["rock salt"]
    lattice = Molecule.from_smiles(rec.lattice).smiles
    na, cl = rec.ions
    print(f"  rock salt: lattice {lattice!r}   ions {rec.ions}")
    print()
    print("  0.5 mol into 30 mol of water at 298 K for 600 s, k_diss = 1.0:")
    print()
    print(f"     {'charged as':<26} {'dissolved / mol':>16} {'solid left / mol':>17}")
    thermo = electrolyte_provider()
    for label, feed, charge in (
        ("ions in the solid block", [WATER, na, cl], {na: 0.5, cl: 0.5}),
        ("the LATTICE, one species", [WATER, na, cl, lattice], {lattice: 0.5}),
    ):
        with contextlib.redirect_stdout(QUIET):
            net = build_network(feed, list(dissociation_templates()),
                               thermo=thermo, max_species=40)
            v = Vessel(net, volume=1.0, thermo=thermo, T=298.15, T_env=298.15,
                       k_diss=1.0)
            v.charge(charge, phase="solid")
            v.charge({WATER: 30.0})
            v.run(600.0, rtol=1.0e-8, atol=1.0e-11)
        st = v.state()
        print(f"     {label:<26} {st.n_liquid.get(na, 0.0):16.6f} "
              f"{sum(st.n_solid.values()):17.6f}")
    print()
    print("  THE LATTICE IS INERT TO WATER AND IT ALWAYS WAS.")
    print("  `PrecipitationArrays` says it in a comment -- 'the lattice is not a")
    print("  species and never becomes one, the SOLID BLOCK HOLDS THE IONS' --")
    print("  while `solid_state` and `surface` say the opposite, because for a")
    print("  calcination or a roast the lattice IS the species. Two")
    print("  representations, disjoint mechanics, and NOTHING CONVERTS BETWEEN")
    print("  THEM. So the shelf's rule is mechanism-driven:")
    print()
    print("     1. reacts as a crystal        -> the LATTICE")
    print("     2. else has a priceable Ksp   -> its IONS in the solid block")
    print("     3. else charged fragments     -> its ions, dissolved")
    print("     4. else                       -> the molecule")
    print()
    only_dissolve = [i for i in inv.shelf()
                     if i.form == "ions" and i.lattice]
    # The collision is a priceable Ksp and NOT merely having ions: hematite,
    # corundum and tenorite have ions and no aqueous Ksp, so they could not
    # dissolve in either representation and are not a choice. Counting them made
    # this list read 9 where the generator's reads 6, which is the instrument
    # disagreeing with the rule it is auditing.
    collide = [i for i in inv.shelf() if i.form == "lattice" and i.lattice
               and _dissolves(MINERALS[i.lattice])]
    print(f"  rows the OBVIOUS rule would have stranded ({len(only_dissolve)}):")
    for item in only_dissolve:
        print(f"     {item.id:<22} {item.lattice:<16} dissolving is all it does")
    print()
    print(f"  rows where the two rules COLLIDE and rule 1 wins ({len(collide)}):")
    for item in collide:
        print(f"     {item.id:<22} {item.lattice:<16} can be roasted, cannot dissolve")
    print()
    print("  THAT SECOND LIST IS A NAMED ENGINE GAP, not a preference: limestone")
    print("  in acid does nothing. The way out is a mechanic that turns a lattice")
    print("  charge into its ions, and until there is one the shelf has to pick.")


# ---------------------------------------------------------------------------
def panel3():
    rule("PANEL 3 -- SIX TEMPLATE FIELDS WERE NOT REACHING THE ENGINE")
    spec_names = {f.name for f in dataclasses.fields(TemplateSpec)}
    tmpl_names = {f.name for f in dataclasses.fields(ReactionTemplate)
                  if not f.name.startswith("_")}
    print(f"  ReactionTemplate fields  {len(tmpl_names):3d}")
    print(f"  TemplateSpec fields      {len(spec_names):3d}")
    print(f"  carried by neither       {sorted(tmpl_names - spec_names)}")
    print()
    print("  The six that were being dropped, and what each one is worth:")
    for name, what in (
        ("orders", "a DECLARED RATE LAW (S11) -- the burner, below"),
        ("solid_catalyst", "a CRYSTAL GATE (S1) -- 11 templates declare one, and"),
        ("", "   dropped, the reaction runs with NO catalyst at all"),
        ("electrons", "an ELECTRODE REACTION's driving force (M8) -- dropped,"),
        ("", "   n F E is zero and the electrolysis stops"),
        ("hammett_rho", "RING DEACTIVATION (G2). aromatic_nitration ships with"),
        ("", "   -6.5, so this was the DEFAULT being lost"),
        ("hammett_slot", "which reactant slot the sigma-plus is read on"),
        ("hammett_saturation", "the encounter plateau in decades (G6)"),
    ):
        print(f"     {name:<20} {what}")
    print()
    print("  THE BURNER, BOTH WAYS. 0.02 mol S8 in a sealed litre at 700 K for")
    print("  an hour, with 0.5 mol of water and 0.02 mol of NO2 present:")
    print()
    print(f"     {'O2 / mol':>9} {'declared 1st order':>20} "
          f"{'mass action (9 bodies)':>24}")
    lib = full_library()
    burner = next(t for t in lib if t.name == "sulfur_combustion")
    assert burner.orders is not None
    stripped = dataclasses.replace(burner, orders=None)
    items = [inv.find(x) for x in
             ("sulfur-s8", "oxygen", "nitrogen", "water", "nitrogen-dioxide")]
    for o2 in (0.05, 0.20, 0.50):
        row = []
        for tmpl in (burner, stripped):
            others = [t for t in lib if t.name != "sulfur_combustion"]
            with contextlib.redirect_stdout(QUIET):
                sc = inv.scenario_for(items, templates=[tmpl, *others],
                                      generations=3, max_species=400,
                                      T=700.0, UA=1.0e4, k_vent=0.0, kla=5.0)
                w = World(sc)
                w.now("charge", "flask", amounts={S8: 0.02}, phase="solid")
                w.now("charge", "flask", amounts={WATER: 0.5}, phase="liquid")
                w.now("charge", "flask",
                      amounts={O2: o2, N2: 0.05, NO2: 0.02}, phase="gas")
                w.flush()
                w.step(3600.0)
            st = w.vessels["flask"].state()
            row.append(100.0 * (0.02 - total(st, S8)) / 0.02)
        print(f"     {o2:9.2f} {row[0]:19.4f}% {row[1]:23.4f}%")
    print()
    print("  A THRESHOLD WHERE THE DECLARED LAW IS A LINE, and that is what an")
    print("  exponent of 8 on oxygen looks like. The right-hand column is what")
    print("  every scenario-built network ran before P4, so the shelf's own")
    print("  oxygen bottle could not light the shelf's own sulfur.")
    print()
    print("  WHAT FOUND IT: playing the game. Not a test -- the suite was green,")
    print("  because every harness in the repo hands templates to build_network")
    print("  DIRECTLY and only a frontend goes through a Scenario. The three")
    print("  hammett_* fields were then found by a test asserting the SET of")
    print("  fields rather than the three the play had reached.")


# ---------------------------------------------------------------------------
def panel4():
    rule("PANEL 4 -- THE PLAYED SESSION: VITRIOL, OUT OF THE PICKER")
    pick = ("sulfur-s8", "oxygen", "nitrogen", "water", "nitrogen-dioxide")
    print(f"  taken off the shelf: {', '.join(pick)}")
    print(f"  {'gens':>5} {'species':>8} {'frontier':>9}  what is in the network")
    for gens in (1, 2, 3):
        with contextlib.redirect_stdout(QUIET):
            ex = bench([inv.find(i) for i in pick], generations=gens, T=700.0)
            w = World(ex.scenario)
        new = [s for s in w.network.species
               if s not in {S8, O2, N2, WATER, NO2}]
        print(f"  {gens:>5} {len(w.network.species):>8} "
              f"{len(w.network.unexpanded):>9}  {new}")
    print()
    print("  SO2 at one generation, SULFURIC ACID at two, and an empty frontier")
    print("  at three -- the network is complete and the engine says so. That is")
    print("  the game's own chain 2, from four natural rows and one intermediate,")
    print("  in two presses of REACT FURTHER.")
    print()
    print("  THE SIX LATTICES NOBODY CHARGED ARE P4's OWN FIX SHOWING. Restoring")
    print("  `solid_catalyst` means every gated template's crystal is a SPECIES")
    print("  again -- nickel, iron, copper, cobalt, tenorite, hematite -- because")
    print("  a gate the kernel cannot see is not a gate. They sit at zero moles,")
    print("  which is the zero-Jacobian-column case S5 bounded, and the flask")
    print("  does none of their chemistry until one is actually poured in.")
    print()
    print("  AND THE NO2 IS WHY THE INTERMEDIATE TIER EXISTS. There is no")
    print("  template for SO2 + O2 -> SO3 without a carrier: the corpus has the")
    print("  LEAD CHAMBER (a NOx cycle) and the contact process (a solid")
    print("  catalyst). Sulfur, air and water alone stop at SO2 with an empty")
    print("  frontier, which is the engine correctly reporting that it knows no")
    print("  further chemistry rather than declining to look.")
    print()
    with contextlib.redirect_stdout(QUIET):
        ex = bench([inv.find(i) for i in pick], generations=3, T=700.0)
        w = World(ex.scenario)
        for item in [inv.find(i) for i in pick]:
            w.now("charge", "flask", amounts=item.amounts(), phase=item.phase)
        w.flush()
        t0 = time.time()
        w.step(3600.0)
        wall = time.time() - t0
    v = w.vessels["flask"]
    st = v.state()
    print(f"  ONE HOUR IN THE SHELF'S OWN AMOUNTS, open flask, 700 K "
          f"({wall:.1f} s wall):")
    print(f"     T {v.T:.1f} K   P {v.pressure:.4f} bar")
    print(f"     S8 left  {total(st, S8):.6f} of 0.2      "
          f"SO2 {total(st, SO2):.6f}      vitriol {total(st, VITRIOL):.6f}")
    print()
    print("  THE OPEN FLASK IS PART OF IT AND IS S12's LESSON AGAIN: the bench's")
    print("  default vessel vents (k_vent = 1e3), so the steam and the oxygen")
    print("  leave through the top. But SEALING IT IS NOT THE FIX, and assuming")
    print("  it was is a claim this panel had to withdraw.")
    print()
    print("  THE WATER IS THE LEVER, AND NOBODY DECLARED THAT. A gas-phase")
    print("  combustion is first order in GASEOUS S8, and 5 mol of water (90 mL)")
    print("  holds the sulfur in the liquid. Sealed, 700 K, one hour, 0.05 mol of")
    print("  oxygen throughout:")
    print()
    print(f"     {'S8 / mol':>9} {'water / mol':>12} {'S8 in the gas':>14} "
          f"{'burnt':>10}")
    for s8, water in ((0.2, 5.0), (0.2, 0.5), (0.02, 5.0), (0.02, 0.5)):
        with contextlib.redirect_stdout(QUIET):
            sc = inv.scenario_for(
                [inv.find(i) for i in pick], templates=full_library(),
                generations=3, max_species=400, T=700.0, UA=1.0e4,
                k_vent=0.0, kla=5.0)
            w = World(sc)
            w.now("charge", "flask", amounts={S8: s8}, phase="solid")
            w.now("charge", "flask", amounts={WATER: water}, phase="liquid")
            w.now("charge", "flask",
                  amounts={O2: 0.05, N2: 0.2, NO2: 0.02}, phase="gas")
            w.flush()
            w.step(3600.0)
        st = w.vessels["flask"].state()
        print(f"     {s8:9.2f} {water:12.1f} {st.n_gas.get(S8, 0.0):14.3e} "
              f"{100.0 * (s8 - total(st, S8)) / s8:9.4f}%")
    print()
    print("  A TENTH OF THE WATER IS 7.7x THE SULFUR IN THE VAPOUR AND FOUR")
    print("  ORDERS OF MAGNITUDE OF CONVERSION. Nothing declares it: the phase")
    print("  model partitions S8 into whichever liquid is there. You do not burn")
    print("  sulfur in a wet flask, and the engine says so without being told.")
    print("  The shelf's water bottle is 5.0 mol, so the shelf's own charge does")
    print("  NOT burn -- pour less water in.")


# ---------------------------------------------------------------------------
def _charge_and_step(w, items, sim):
    """Charge the shelf rows into a freshly-built world and step it once."""
    with contextlib.redirect_stdout(QUIET):
        for it in items:
            w.now("charge", "flask", amounts=it.amounts(), phase=it.phase)
        w.flush()
        t0 = time.time()
        w.step(sim)
    return time.time() - t0


def _totals(w):
    st = w.vessels["flask"].state()
    out: dict[str, float] = {}
    for blk in (st.n_liquid, st.n_liquid2, st.n_gas, st.n_solid):
        for s, n in blk.items():
            out[s] = out.get(s, 0.0) + n
    return out


def panel5(mass_cap: bool = False):
    """REACT UNTIL DONE -- what a fixpoint costs, measured six ways.

    ⚠⚠⚠ THIS PANEL EXISTS BECAUSE THE GENERATION BOUND IS AN OBJECTION, NOT A
    DESIGN. *"In the real world these materials would continue to react until
    everything was done -- it would not stop artificially at sulfur dioxide and
    need a deliberate trigger."* That is correct, and ``GAME_DESIGN.md`` 8.2
    already concedes it: one generation is an approximation that TOUCHES MATTER,
    admissible only because it is never silent. So the question is whether the
    engine can simply be run to a fixpoint instead, and the answer is measured
    here rather than assumed.

    ⚠ Sub-panel C is ~2.5 minutes on its own, and that IS the finding: the
    fixpoint it times is 400 species and 644 reactions and the solver evaluates
    every one of them on every right-hand-side call.
    """
    rule("PANEL 5 -- REACT UNTIL DONE: WHAT A FIXPOINT ACTUALLY COSTS")
    print("  The generation bound is an approximation that touches matter, so")
    print("  'why not just react until nothing is left to react' is the right")
    print("  question. Six measurements, and only ONE of them is about the")
    print("  cost of DISCOVERY.")

    # -- A ------------------------------------------------------------------
    print()
    print("  A. A FIXPOINT IS FREE FOR NON-POLYMERISING CHEMISTRY.")
    print(f"     {'picked off the shelf':30s} {'species':>8} {'rxn':>6} "
          f"{'frontier':>9} {'build':>8}")
    for label, pick in (
        ("sulfur, air, water, NO2", ("sulfur-s8", "oxygen", "nitrogen",
                                     "water", "nitrogen-dioxide")),
        ("limestone + water", ("calcium-carbonate", "water")),
        ("brine", ("sodium-chloride", "water")),
    ):
        t0 = time.time()
        with contextlib.redirect_stdout(QUIET):
            w = World(bench([inv.find(i) for i in pick],
                            generations=None, max_species=400).scenario)
        print(f"     {label:30s} {len(w.network.species):8d} "
              f"{len(w.network.reactions):6d} {len(w.network.unexpanded):9d} "
              f"{time.time() - t0:7.2f}s")
    print()
    print("     FRONTIER ZERO IN EVERY ROW. 'React until done' is available")
    print("     TODAY for the whole inorganic half of the shelf -- the chain-2")
    print("     pick closes on its own in a couple of seconds, and PANEL 4's SO2")
    print("     stop is not a bound biting at all. Set generations=None and that")
    print("     flask runs to completion with no trigger and no button.")

    # -- B ------------------------------------------------------------------
    print()
    print("  B. SUGARS AND ORGANICS EXPLODE, AND IT IS NOT A TUNING PROBLEM.")
    sugar = [inv.find(i) for i in ("glucose", "water", "oxygen", "nitrogen")]
    t0 = time.time()
    with contextlib.redirect_stdout(QUIET):
        wf = World(bench(sugar, generations=None, max_species=400).scenario)
    build_fix = time.time() - t0
    print(f"     glucose + water + air at a fixpoint: {len(wf.network.species)} species, "
          f"{len(wf.network.reactions)} reactions,")
    print(f"     frontier {len(wf.network.unexpanded)}, build {build_fix:.1f} s "
          f"-- so it hit the 400 cap and is NOT a fixpoint.")
    print()
    print("     THE CAUSE IS THAT TWO TEMPLATES BUILD. esterification and")
    print("     ether_condensation take an acid or an alcohol and hand back a")
    print("     bigger molecule that is a VALID REACTANT FOR THE SAME RULE, and")
    print("     a sugar is a polyol, so the product set feeds itself. There is")
    print("     no fixpoint for this chemistry at all -- only a size bound or a")
    print("     count bound -- and that is a property of the TEMPLATE SET, not a")
    print("     parameter anybody can raise.")

    # -- C ------------------------------------------------------------------
    print()
    print("  C. THE DECIDING NUMBER, AND IT IS NOT DISCOVERY COST.")
    t0 = time.time()
    with contextlib.redirect_stdout(QUIET):
        w1 = World(bench(sugar, generations=1, max_species=400).scenario)
    build_1 = time.time() - t0
    step_1 = _charge_and_step(w1, sugar, 3600.0)
    step_f = _charge_and_step(wf, sugar, 300.0)
    print(f"     {'':10s} {'species':>8} {'rxn':>6} {'build':>8} {'step':>9} "
          f"{'sim s':>7} {'wall s / sim s':>15}")
    for label, w, build, step, sim in (("gens=1", w1, build_1, step_1, 3600.0),
                                       ("fixpoint", wf, build_fix, step_f, 300.0)):
        print(f"     {label:10s} {len(w.network.species):8d} "
              f"{len(w.network.reactions):6d} {build:7.2f}s {step:8.2f}s "
              f"{sim:7.0f} {step / sim:15.4f}")
    ratio = (step_f / 300.0) / (step_1 / 3600.0)
    print()
    print(f"     A FIXPOINT IS {ratio:.0f}x MORE EXPENSIVE TO *INTEGRATE*, and the")
    print(f"     same simulated hour is {step_1:.0f} s against "
          f"{step_f * 12.0 / 60.0:.0f} minutes. The extra")
    print("     20 s of BUILD is nothing; the solver evaluating 644 reactions on")
    print("     every right-hand-side call is everything. So what stops 'react")
    print("     until done' is the INTEGRATOR and not the discovery, and THAT IS")
    print("     THE CASE FOR RATE PRUNING: nearly all 644 are kinetically dead at")
    print("     298 K and the solver pays full price for them regardless.")

    # -- D ------------------------------------------------------------------
    print()
    print("  D. AND AT THE SAME CLOCK THE FLASK IS BARELY DIFFERENT.")
    with contextlib.redirect_stdout(QUIET):
        w1b = World(bench(sugar, generations=1, max_species=400).scenario)
    _charge_and_step(w1b, sugar, 300.0)
    a, b = _totals(w1b), _totals(wf)
    keys = sorted(set(a) | set(b), key=lambda s: -abs(b.get(s, 0.0) - a.get(s, 0.0)))
    worst = keys[0]
    appeared = [s for s in keys if a.get(s, 0.0) <= 1e-12 < b.get(s, 0.0)]
    print("     glucose + water + air, both stepped 300 s from the same charge:")
    print(f"     {'':46s} {'gens=1':>13s} {'fixpoint':>13s}")
    for s in keys[:5]:
        print(f"     {s[:46]:46s} {a.get(s, 0.0):13.6e} {b.get(s, 0.0):13.6e}")
    print(f"     species present {sum(1 for v in a.values() if v > 1e-12):>4d} "
          f"vs {sum(1 for v in b.values() if v > 1e-12):<4d}"
          f"  new in the fixpoint: {len(appeared)}")
    print(f"     largest move on anything: "
          f"{abs(b.get(worst, 0.0) - a.get(worst, 0.0)):.2e} mol, on a 0.5 mol charge")
    print(f"     T {w1b.vessels['flask'].T:.4f} K vs {wf.vessels['flask'].T:.4f} K")
    print()
    print("     THIS WAS THE OPEN QUESTION AND IT SETTLES IN THE CHEAP")
    print("     DIRECTION. The two runs DO give different flasks -- the extra")
    print("     species are real, and the bound touches matter exactly as")
    print("     GAME_DESIGN.md 8.2 says it does -- but at 297 K over five")
    print("     minutes the 624 extra reactions move nothing by as much as a")
    print("     MICROMOLE.")
    print("     SCOPE IT HONESTLY: one system, one temperature, one clock. The")
    print("     species that appear are lactate ESTERS, and esters BUILD, so a")
    print("     hot flask or a long run is a different measurement and it has")
    print("     not been made. This is evidence the bound is cheap HERE, not a")
    print("     proof that it is cheap.")

    # -- E ------------------------------------------------------------------
    print()
    print("  E. AND DEEPER EXPLORATION CRASHES RATHER THAN DEGRADING.")
    pick = [inv.find("5-hydroxymethylfurfural"), inv.find("oxygen")]
    try:
        with contextlib.redirect_stdout(QUIET):
            World(bench(pick, generations=1, max_species=400).scenario)
        print("     it no longer raises. If this line prints, R1 is done and")
        print("     this sub-panel must be rewritten to assert the NOTICE.")
    except ValueError as exc:
        print(f"     picker rows '5-HMF' + 'oxygen' at generations=1 -> "
              f"{type(exc).__name__}")
        print(f"     {str(exc).split(' -- ')[0]}")
    print()
    print("     BOTH ROWS ARE OFFERED UNGREYED BY THE PICKER, AND THIS IS ONE")
    print("     GENERATION, not a deep exploration. 5-HMF is priced; the species")
    print("     it makes, 2,5-diformylfuran, has a formation half from Benson and")
    print("     NO physical half -- no measured Tb anywhere, so no")
    print("     vapour-pressure curve can be built -- and thermochemistry refuses")
    print("     rather than pretend it is non-volatile. That refusal is RIGHT in")
    print("     isolation and wrong here: max_species, max_molar_mass and")
    print("     generations all DROP, NOTICE and carry on, while this one")
    print("     propagates out of build_network as a bare ValueError and the")
    print("     player gets a traceback. It has to become the fourth REPORTED")
    print("     coverage limit before anything is allowed to explore deeper.")

    # -- F ------------------------------------------------------------------
    print()
    print("  F. A MOLAR-MASS CAP IS DEAD AS AN IDEA -- MEASURED AND REFUTED.")
    if mass_cap:
        print(f"     {'max_molar_mass':>16s} {'species':>8} {'rxn':>6} "
              f"{'frontier':>9} {'build':>9}")
        with contextlib.redirect_stdout(QUIET):
            sc = inv.scenario_for(sugar, templates=full_library(),
                                  generations=None, max_species=400)
            feed = list(sc.feed_species)
            tmpls = [t.build() for t in sc.templates]
        for cap in (None, 500.0, 400.0, 250.0):
            label = "none" if cap is None else f"{cap:.0f}"
            t0 = time.time()
            try:
                with contextlib.redirect_stdout(QUIET):
                    net = build_network(feed, tmpls, max_species=400,
                                        thermo=ThermochemistryProvider(),
                                        generations=None, max_molar_mass=cap)
                print(f"     {label:>16s} {len(net.species):8d} "
                      f"{len(net.reactions):6d} {len(net.unexpanded):9d} "
                      f"{time.time() - t0:8.1f}s")
            except ValueError as exc:
                print(f"     {label:>16s}   CRASHED after {time.time() - t0:.1f}s: "
                      f"{str(exc)[:44]}")
    else:
        print("     RECORDED, NOT RE-RUN -- this sweep is ~6.5 minutes on its own.")
        print("     `python validation/shelf.py --mass-cap` measures it live.")
        print()
        print(f"     {'max_molar_mass':>16s} {'rxn':>6} {'build':>9}   outcome")
        print(f"     {'none':>16s} {644:6d} {'~20.2s':>9}   hit the 400-species cap")
        print(f"     {'250 g/mol':>16s} {842:6d} {'388s':>9}   hit it too -- and is BIGGER")
        print()
        print("     THE UNCAPPED BASELINE IS CORRECTED HERE AND THE CORRECTION")
        print("     COSTS THE HEADLINE HALF ITS SIZE. The measurement was first")
        print("     written up as 10.9 s uncapped, which made 388 s a 35x")
        print("     slowdown; sub-panel B builds that same network live and has")
        print("     measured 19.8, 20.1 and 20.2 s. So it is 19x, not 35x. The")
        print("     10.9 s does not reproduce and nothing should be quoted from")
        print("     it. What survives the correction is the part that was never")
        print("     about the clock:")
    print()
    print("     IT NEVER CLOSES THE FIXPOINT, IT IS ~19x SLOWER, AND IT TURNS")
    print("     TWO PICKS INTO CRASHES. The reason is the part worth")
    print("     keeping: BOUNDING SIZE DOES NOT SHRINK THE SEARCH, IT REDIRECTS")
    print("     IT INTO A DENSER REGION. 842 reactions at 250 g/mol against 644")
    print("     uncapped -- THE TIGHTER BOUND PRODUCED THE BIGGER NETWORK,")
    print("     because refusing the heavy products leaves the light ones to")
    print("     recombine with each other instead. Rate is the axis to prune on.")
    print("     Mass is not, and this is what refuted it.")


def main() -> None:
    panel1()
    panel2()
    panel3()
    panel4()
    panel5(mass_cap="--mass-cap" in sys.argv)
    print()


if __name__ == "__main__":
    main()

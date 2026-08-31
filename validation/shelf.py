"""P3/P4's standing audit: the shelf, the two forms of a rock, and the burner.

Run: ``python validation/shelf.py``   (~2 min, no scorer import)

Four panels, and each one exists because a decision was made from it.

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


def main() -> None:
    panel1()
    panel2()
    panel3()
    panel4()
    print()


if __name__ == "__main__":
    main()

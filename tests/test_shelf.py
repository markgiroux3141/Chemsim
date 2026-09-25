"""P3 -- the shelf as data: the file, the resolution rule, and the two forms.

⚠⚠ **THE TEST THIS FILE EXISTS FOR IS `test_a_lattice_charge_cannot_dissolve`**,
because that is the one that would have caught P3's first resolution rule. The
obvious rule -- *a mineral is charged as its `mineral_data` lattice* -- reads
correctly, generates a clean report, and puts rock salt, fluorite, saltpetre,
phosphate rock and anhydrite into the flask as matter no mechanic in this engine
can touch. Nothing static says so. A flask does, in ten seconds.

The rest pins the classification, because a generated artefact with no assertion
behind it is a snapshot of whenever somebody last ran the generator --
`ROUTE_INDEX.md` rotted for three milestones on exactly that.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("src", "tools"):
    _full = os.path.join(_ROOT, _p)
    if _full not in sys.path:
        sys.path.insert(0, _full)

from chemsim.engine import inventory as inv                     # noqa: E402
from chemsim.engine.shelf_data import ROSTER, SHELF             # noqa: E402
from chemsim.engine.world import World                          # noqa: E402
from chemsim.matter import Molecule                             # noqa: E402
from chemsim.network import build_network                       # noqa: E402
from chemsim.properties import (                                # noqa: E402
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.properties.mineral_data import MINERALS            # noqa: E402
from chemsim.vessel import Vessel                               # noqa: E402

SHELF_PSV = os.path.join(_ROOT, "data", "catalog", "shelf.psv")


# ---------------------------------------------------------------------------
# 1. THE FILE, AND THAT THE GENERATED MODULE STILL MATCHES IT
# ---------------------------------------------------------------------------


def test_the_psv_and_the_generated_module_say_the_same_thing():
    """``shelf_data.SHELF`` is ``shelf.psv``, or the generator was not re-run."""
    import build_shelf

    rows = build_shelf.read_shelf(SHELF_PSV)
    assert len(rows) == len(SHELF), (
        f"shelf.psv has {len(rows)} rows and shelf_data.SHELF has {len(SHELF)}. "
        f"Run `python tools/build_shelf.py`."
    )
    for (cid, tier, amount, phase, note), entry in zip(rows, SHELF, strict=True):
        assert (cid, tier, amount, phase, note) == tuple(entry), (
            f"{cid}: the file and the module disagree. Regenerate."
        )


def test_the_three_tiers_are_the_measured_ones():
    """43 / 21 / 11, and the relation rather than the level is what is pinned.

    ⚠ C4's rule: a test that pins a LEVEL gets re-numbered by the next session
    that moves it and the claim quietly becomes someone else's arithmetic. So the
    numbers are here, but the ASSERTIONS are about what has to stay true -- three
    tiers and nothing else, naturals the biggest block, and the intermediate
    block non-empty because it is the one that is supposed to shrink.
    """
    got = inv.counts()
    assert set(inv.TIERS) == {"natural", "intermediate", "bottle"}
    assert got["rows"] == got["natural"] + got["intermediate"] + got["bottle"]
    assert got["natural"] == 43
    # T18 ADDED TWO, which is the tier moving in the direction it is not
    # supposed to. It is the rule working: `soap-saponification` became
    # RUNNABLE when the plateau rule priced its stearate, so the two species it
    # is short of -- tristearin and the stearate itself -- are newly STRANDED
    # rather than newly unreachable. `tests/test_playable_levers.py` is what
    # reported it, and a route that cannot run at all strands nothing.
    #
    # T32 TOOK ONE OF THOSE TWO BACK OFF, and it should never have been on:
    # `soap-saponification` MAKES sodium stearate, and the only reason the
    # audit called it short of it was `needs` unioning the route's derived
    # catalysts in -- which made a route that makes its target in row 1 and
    # consumes it in row 2 ask the player to already hold it. Nothing became
    # reachable to earn this deletion. A demand was withdrawn.
    #
    # T29 MOVED FIVE MORE OUT OF IT AND INTO `bottle`, and again no route
    # became reachable: `build_playable.MADE_SOMEWHERE` was crediting a step
    # that carries a species on BOTH sides with making it, so the corpus read
    # as smelting its own catalysts. A catalyst is not earnable, so the tier
    # that is supposed to shrink shrinks and the one that never shrinks grows.
    # 24 -> 21 and 4 -> 11, net +4 rows, two of which (`ammonia` and
    # `acetic-anhydride`) were owed and unrecorded.
    #
    # 2026-09-24 ADDED FIVE AND TWO, and it is T18's shape: the textbook family
    # rows made five routes runnable, and the species they are short of are
    # newly stranded (`intermediate`) or newly wanted and made nowhere (`bottle`).
    assert got["intermediate"] == 26
    assert "sodium-stearate" not in {e.id for e in SHELF}, (
        "T32: soap-saponification makes it; it is earnable and not a gift"
    )
    assert got["bottle"] == 13
    # THE RELATION, not the level: a catalyst metal is bought, for ever. If
    # one of these is ever `intermediate` again, something is crediting a
    # no-op row with making it -- see `catalog.made_by` and T29.
    tiers = {e.id: e.tier for e in SHELF}
    for metal in ("nickel", "cobalt", "palladium", "platinum"):
        assert tiers.get(metal) == "bottle", (
            f"{metal} is {tiers.get(metal)}: nothing in the corpus smelts it"
        )
    assert got["intermediate"] > 0, (
        "an empty intermediate tier means every stranded route became "
        "reachable, which is the goal -- update this test and delete the rows"
    )


def test_every_shelf_row_is_a_real_corpus_species():
    """A shelf entry that is not a `VesselState` is forbidden (8.6), and the
    first way to fail that is to name something with no molecular graph."""
    for entry in SHELF:
        assert entry.id in ROSTER, f"{entry.id} is not a corpus compound"
        rec = ROSTER[entry.id]
        assert rec.smiles, f"{entry.id} has no SMILES"
        assert rec.charge, f"{entry.id} resolves to no charge at all"
        Molecule.from_smiles(rec.smiles)          # parses, or this raises


def test_the_two_markers_are_absent_and_that_is_the_reason():
    """⚠ 45 natural species, 43 rows, and the gap is exactly the markers.

    `coal-marker` and `collagen-marker` are declared natural by
    `tools/build_playable.py` and cannot be shelf rows: a marker is a rock, a
    mixture or a protein carried so the catalog's routes stay balanced, and it
    has no compound entry and no graph. Pinned as an EQUALITY so that a third
    marker cannot be dropped silently, and so that a session which gives coal a
    graph finds this test rather than discovering the absence later.
    """
    assert "coal-marker" not in ROSTER
    assert "collagen-marker" not in ROSTER
    assert {e.id for e in SHELF if e.tier == "natural"} <= set(ROSTER)


# ---------------------------------------------------------------------------
# 2. THE RESOLUTION RULE -- A ROCK HAS TWO FORMS AND THEY ARE NOT EQUIVALENT
# ---------------------------------------------------------------------------


def test_a_lattice_charge_cannot_dissolve():
    """⚠⚠⚠ THE FINDING. Rock salt as ions dissolves; as a lattice it is inert.

    ``PrecipitationArrays`` says it in a comment -- *the lattice is not a species
    and never becomes one, the SOLID BLOCK HOLDS THE IONS* -- and this is that
    sentence as a measurement. 0.5 mol into 30 mol of water at 298 K for 600 s.

    It is the reason ``build_shelf``'s rule is mechanism-driven. Charging every
    mineral as its lattice, which is the obvious rule and was the first one,
    strands five shelf rows including the chlor-alkali feedstock and the whole
    subject of C2.
    """
    rec = MINERALS["rock salt"]
    lattice = Molecule.from_smiles(rec.lattice).smiles
    na, cl = rec.ions
    thermo = electrolyte_provider()
    out = {}
    for label, feed, charge in (
        ("ions", ["O", na, cl], {na: 0.5, cl: 0.5}),
        ("lattice", ["O", na, cl, lattice], {lattice: 0.5}),
    ):
        net = build_network(feed, list(dissociation_templates()), thermo=thermo,
                            max_species=40)
        v = Vessel(net, volume=1.0, thermo=thermo, T=298.15, T_env=298.15,
                   k_diss=1.0)
        v.charge(charge, phase="solid")
        v.charge({"O": 30.0})
        v.run(600.0, rtol=1.0e-8, atol=1.0e-11)
        out[label] = v.state()

    assert out["ions"].n_liquid.get(na, 0.0) > 0.4, (
        "rock salt charged as ions in the solid block did NOT dissolve; the Ksp "
        "path is what makes a rock on the shelf mean anything"
    )
    assert sum(out["ions"].n_solid.values()) < 1.0e-6
    assert out["lattice"].n_solid.get(lattice, 0.0) == pytest.approx(0.5), (
        "the lattice charge moved. If a mechanic now converts a lattice into "
        "its ions, THAT IS THE GAP CLOSING -- rewrite build_shelf's rule 1/2 "
        "collision note and this test, do not delete the assertion."
    )
    assert not out["lattice"].n_liquid.get(na, 0.0)


def test_the_dissolution_only_minerals_are_charged_as_ions():
    """The five rows the first rule would have stranded, by name.

    Every one of them has a Ksp and NO solid-state or surface reaction, so ions
    in the solid block is the only representation that does anything at all.
    """
    for cid in ("sodium-chloride", "calcium-fluoride", "potassium-nitrate",
                "calcium-phosphate", "calcium-sulfate"):
        item = inv.find(cid)
        assert item.form == "ions", f"{cid} is charged as {item.form}"
        assert item.lattice, f"{cid} lost its mineral record"
        assert len(item.charge) > 1 or cid == "copper-ii-ion"
        assert item.electrolyte, f"{cid} charges ions and must set electrolyte"


def test_phosphate_rock_is_charged_the_way_c2_measured_it():
    """``validation/phosphate_rock.py`` charges ``{Ca2+: 3, PO4(3-): 2}`` solid.

    The one row in this file whose representation was measured by an earlier
    session, in a flask, with the alternative measured beside it at 0.0000%
    conversion. If this ever changes, C2's audit is the thing to re-read.
    """
    item = inv.find("calcium-phosphate")
    assert dict(item.charge) == {"[Ca+2]": 3.0, "O=P([O-])([O-])[O-]": 2.0}
    assert item.phase == "solid"
    assert item.amounts(1.0) == {"[Ca+2]": 1.5, "O=P([O-])([O-])[O-]": 1.0}


def test_the_six_colliding_rows_keep_the_lattice_and_lose_the_solution():
    """A NAMED GAP, asserted so it cannot be forgotten rather than fixed.

    Calcite, covellite, galena, sphalerite, cinnabar and green vitriol both
    react as a crystal and have a priceable Ksp. Rule 1 wins because a
    solid-state mechanic is reachable no other way -- so limestone in acid does
    nothing, and that is a limitation of the engine and not of the shelf.
    """
    for cid in ("calcium-carbonate", "copper-sulfide", "lead-sulfide",
                "zinc-sulfide", "mercury-sulfide", "iron-ii-sulfate"):
        item = inv.find(cid)
        assert item.form == "lattice", f"{cid} is charged as {item.form}"
        assert len(item.charge) == 1
        assert item.charge[0][0] == ROSTER[cid].smiles
        assert not item.electrolyte


def test_a_metal_is_a_lattice_and_not_a_molecule():
    """Nickel has no ions on purpose, so the lattice is its only form.

    Its charge string and a nickel atom's SMILES are the same characters, which
    is exactly why ``form`` has to say which one it is.
    """
    for cid in ("nickel", "palladium", "silver", "cobalt", "iron", "aluminium"):
        item = inv.find(cid)
        assert item.form == "lattice", f"{cid} is charged as {item.form}"
        assert item.phase == "solid"
        assert not MINERALS[item.lattice].ions


def test_a_formula_unit_carries_its_own_stoichiometry():
    """Fluorite is 1:2 and gypsum brings its water into the flask.

    The dot-separated SMILES is the only place a salt's stoichiometry is written
    down in this corpus, so reading it is not a convenience.
    """
    assert dict(inv.find("calcium-fluoride").charge) == {"[Ca+2]": 1.0, "[F-]": 2.0}
    gyp = dict(inv.find("gypsum").charge)
    assert gyp["O"] == 2.0, "gypsum's two waters of crystallisation are matter"
    assert gyp["[Ca+2]"] == 1.0


# ---------------------------------------------------------------------------
# 3. A ROW BECOMES A REAL BOTTLE, AND A REFUSED ROW REFUSES
# ---------------------------------------------------------------------------


def test_every_chargeable_row_makes_a_real_vessel_state():
    """8.6: no shelf entry that is not a real ``VesselState``. All 64 of them."""
    for item in inv.shelf():
        if not item.chargeable:
            continue
        state = item.state()
        assert state.T == pytest.approx(inv.T_SHELF)
        block = getattr(state, "n_" + item.phase)
        assert block, f"{item.id} put nothing in the {item.phase} block"
        assert sum(block.values()) == pytest.approx(
            sum(n * item.amount for _s, n in item.charge)
        )
        # and every other block is empty: a bottle is in ONE phase
        others = sum(
            sum(getattr(state, name).values())
            for name in ("n_liquid", "n_liquid2", "n_gas", "n_solid")
            if name != "n_" + item.phase
        )
        assert others == 0.0, f"{item.id} spread across phases"


def test_a_refused_row_is_visible_carries_its_reason_and_refuses_to_pour():
    """⚠ 8.3: greyed WITH THE REASON, never absent and never failing late.

    Six shelf rows and 409 corpus species. The refusal is the element floor
    working: an estimator outside its domain answers confidently and wrongly.

    T12 took one row OFF this list -- pyrrhotite, once the second sulfide pKa
    priced the [S-2] it is written as. Pyrite stays. T15 repaired its SMILES
    from [S-]S[S-], a TRIsulfide, to [S-][S-] -- which is a formula fix for
    `corpus_balance` and not a price: `_PAIRS` reaches S2- and HS- and has no
    row for the disulfide, whose acid is HS-SH.
    """
    refused = [i for i in inv.shelf() if not i.chargeable]
    assert {i.id for i in refused} == {
        "gold", "silicon-dioxide", "cryolite", "iron-disulfide",
        "manganese-dioxide", "borax",
    }
    for item in refused:
        assert item.refusal.strip(), f"{item.id} is refused and says nothing"
        with pytest.raises(ValueError, match="may not be charged"):
            item.state()
        # ...and the charge is still resolved, so pricing it later needs no edit
        assert item.charge, f"{item.id} should still know what it would be"


def test_the_roster_holds_the_refused_ones_and_the_cheat_axis_does_not():
    got = inv.counts()
    assert len(inv.roster()) == got["corpus"]
    assert len(inv.roster(refused=False)) == got["priced"]
    assert len(inv.all_priced()) == got["priced"]
    assert all(i.chargeable for i in inv.all_priced())
    assert got["priced"] + got["refused"] == got["corpus"]
    # ⚠ NOT A FOURTH TIER, and the tier name says so
    assert all(i.tier == inv.CHEAT_TIER for i in inv.all_priced())
    assert inv.CHEAT_TIER not in inv.TIERS


def test_the_declared_phase_beats_the_engines_estimate_for_olive_oil():
    """⚠ Joback puts triolein's Tm at 828.9 K. Olive oil is a liquid.

    The measurement that makes the phase column a declaration rather than a
    derivation: a phase read off the estimator would put a bottle of oil in the
    solid block, and no run would ever have said why. Same class of failure as
    the element floor, one rung further out -- a C57 triglyceride is nowhere near
    the domain Joback's groups were fitted over.
    """
    item = inv.find("triolein")
    assert item.phase == "liquid", "the shelf declares olive oil a liquid"
    assert ROSTER["triolein"].phase == "solid", (
        "the engine's own estimate has changed; if triolein now gets a measured "
        "Tm, this test is where to record it"
    )
    assert "828" in ROSTER["triolein"].phase_why


# ---------------------------------------------------------------------------
# 4. A SELECTION BECOMES A WORLD -- P2's HANDOFF
# ---------------------------------------------------------------------------


def test_a_scenario_carries_every_species_the_selection_would_charge():
    """P2's finding: ``charge_state`` refuses a species the network lacks, and a
    network is derived from its FEED. So the picker is a builder."""
    pick = [inv.find("water"), inv.find("sodium-chloride"),
            inv.find("calcium-carbonate"), inv.find("oxygen")]
    sc = inv.scenario_for(pick)
    for item in pick:
        for smiles in item.species:
            assert smiles in sc.feed_species, f"{smiles} missing from the feed"
    assert sc.electrolyte, "rock salt charges ions and needs the overlay"
    assert sc.generations == 1, "a step is ONE generation (8.2)"
    assert len(sc.feed_species) == len(set(sc.feed_species))


def _neutral_pick():
    return ([inv.find("water"), inv.find("ethanol")] if "ethanol" in ROSTER
            else [inv.find("water"), inv.find("benzaldehyde")])


def test_a_selection_with_no_ions_does_not_turn_the_overlay_on():
    """The flag is derived, not defaulted: an overlay nothing needs is cost."""
    sc = inv.scenario_for(_neutral_pick())
    assert not sc.electrolyte


def test_a_library_that_makes_an_ion_turns_the_overlay_on_by_itself():
    """T1c. The guarantee used to read the CHARGE only.

    Nothing in the bench's default items is an ion -- water, glucose, oxygen,
    nitrogen -- so loading the whole template table refused at build time:
    ``cannot derive reverse kinetics for reversible template
    'water_autoionization'``. Water dissociating is the library's chemistry, not
    the player's selection, so the question is the union of the two.
    """
    from chemsim.reactions.template_data import load_templates

    neutral = _neutral_pick()
    ionic = [t for t in load_templates(tier="family") if t.touches_ions]
    assert ionic, "the table carries ionic templates; the gate has nothing to do"
    assert inv.scenario_for(neutral, templates=ionic).electrolyte
    quiet = [t for t in load_templates(tier="family")
             if t.name in ("fischer_esterification", "sulfur_combustion")]
    assert len(quiet) == 2
    assert not inv.scenario_for(neutral, templates=quiet).electrolyte


def test_a_neutral_molecule_with_charged_atoms_is_not_an_ionic_template():
    """A nitro group is ``[N+](=O)[O-]`` and carbon monoxide is ``[C-]#[O+]``.

    Summing formal charge over ATOMS rather than over SLOTS calls fifteen
    ordinary organic templates ionic, aromatic nitration among them.
    """
    from chemsim.reactions.template_data import load_templates

    by_name = {t.name: t for t in load_templates(tier="family")}
    assert not by_name["aromatic_nitration"].touches_ions
    assert not by_name["water_gas_shift"].touches_ions
    assert by_name["water_autoionization"].touches_ions
    assert by_name["saponification"].touches_ions


def test_the_whole_loop_runs_and_the_players_shelf_is_depleted():
    """Take a bottle off the shelf, pour it in, and the bottle is gone.

    ⚠ ``Shelf.take`` is the verb ``World.shelf`` deliberately never sees. This is
    the one test that exercises the difference: the player's shelf is depleted by
    a pour and the run's own shelf stays empty, because no event consumes from it.
    """
    from chemsim.engine.stock import state_to_dict

    pick = [inv.find("water"), inv.find("sodium-chloride")]
    world = World(inv.scenario_for(pick, k_diss=1.0))
    book = inv.open_shelf(pick)
    assert len(book) == 2
    for item in pick:
        stock = book.take(item.name)
        world.now("charge_stock", "flask", label=stock.name,
                  state=state_to_dict(stock.state), fraction=1.0)
    world.flush()
    assert len(book) == 0, "a poured bottle is an empty bottle"
    assert len(world.shelf) == 0, "nothing bottles itself"

    world.step(600.0)
    state = world.vessels["flask"].state()
    dissolved = state.n_liquid.get("[Na+]", 0.0)
    left = state.n_solid.get("[Na+]", 0.0)
    assert dissolved > 0.1 and left > 0.0, (
        f"1 mol of rock salt in 90 mL of water should give a SATURATED brine "
        f"with a crop left over; got {dissolved:.4g} dissolved, {left:.4g} solid"
    )
    assert dissolved + left == pytest.approx(1.0, rel=1e-9)


def test_a_refused_row_is_skipped_by_open_shelf_rather_than_raising():
    book = inv.open_shelf(inv.shelf(("natural",)))
    assert len(book) == 43 - 6


# ---------------------------------------------------------------------------
# 6. T15 -- THE SULFIDE HALF OF THE SHELF
# ---------------------------------------------------------------------------


def test_pyrrhotite_saturates_its_own_solution_and_makes_hydrogen_sulfide():
    """T15. The row used to be matter no mechanic could move, and now it is not.

    `iron-ii-sulfide` declares `solid` and resolves to its ions, so before
    troilite was in `mineral_data` there was no Ksp behind it: the ions sat in
    the solid block for ever while DISCOVERY happily reacted them, which is the
    score and the chemistry coming out of different tables, arriving from the
    shelf side.

    What it does now is the chain with nothing declared anywhere in it --
    FeS(s) -> Fe2+ + S2- on a derived Ksp, then S2- + H2O -> HS- + OH- and
    HS- + H2O -> H2S + OH- on the two `_PAIRS` rows T12 wrote. A flask of
    pyrrhotite and water therefore holds hydrogen sulfide, and holds
    femtomoles of it, because pKsp 18.8 and pKa 12.91 say so together.

    The bound worth knowing is in the numbers rather than in a notice: the
    dissolution drive is `k_diss * V * (Qroot - Ksproot)`, so an empty solution
    dissolves at most `k_diss * V * Ksp**(1/N)` mol/s, and that root is
    4.1e-10 mol/L. Acid pulls the sulfide out and keeps it going, and CANNOT
    make it faster, which is why the same flask with HCl in it reaches
    nanomoles in an hour rather than dissolving. A real acid attack on a
    sulfide is surface chemistry this engine has no term for; the
    EQUILIBRIUM is derived and the RATE is the vessel's one knob.
    """
    import math

    from chemsim.properties.solubility_product import solubility_product

    rec = MINERALS["troilite"]
    fe, s = rec.ions
    assert (fe, s) == ("[Fe+2]", "[S-2]")
    thermo = electrolyte_provider()
    net = build_network(["O", fe, s], list(dissociation_templates()),
                        thermo=thermo, max_species=40)
    v = Vessel(net, volume=1.0, thermo=thermo, T=298.15, T_env=298.15,
               k_diss=1.0)
    v.charge({fe: 0.5, s: 0.5}, phase="solid")
    v.charge({"O": 30.0})
    v.run(600.0, rtol=1.0e-8, atol=1.0e-14)
    st = v.state()

    dissolved = st.n_liquid.get(fe, 0.0)
    assert dissolved > 0.0, (
        "the pyrrhotite row is stranded matter again -- either troilite lost "
        "its mineral_data entry or its Ksp stopped pricing"
    )
    root = math.exp(solubility_product(rec).ln_Ksp / 2.0)
    assert dissolved / v.liquid_volume == pytest.approx(root, rel=1.0e-3), (
        "a saturated solution of a 1:1 lattice is sqrt(Ksp) molar in each ion"
    )
    assert st.n_liquid.get(s, 0.0) == pytest.approx(dissolved, rel=1.0e-2), (
        "both ions leave the lattice together: nu is (1, 1)"
    )
    h2s = st.n_liquid.get("S", 0.0) + st.n_gas.get("S", 0.0)
    assert h2s > 0.0, "the two sulfide pKa rows are what carry S2- to H2S"
    assert h2s < 1.0e-12, (
        "H2S at more than a picomole from water alone would mean the Ksp or "
        "one of the two sulfide pKa rows moved; check which, do not retune this"
    )


def test_pyrite_is_a_disulfide_and_troilite_is_not():
    """T15. `iron-disulfide` was written `[Fe+2].[S-]S[S-]`, which is FeS3.

    The corpus carries no formulas, so `corpus_balance` counts atoms off the
    SMILES and a third sulfur is a silent wrong answer for `pyrite-roasting`.
    Fixing it does not make the row chargeable and is not meant to: the
    disulfide ion has no pKa pair, and `pyrite` itself is refused a lattice
    entry for want of an S0s in the database that holds its Hfs.
    """
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors

    def formula(smiles):
        return rdMolDescriptors.CalcMolFormula(Chem.MolFromSmiles(smiles))

    assert formula(ROSTER["iron-disulfide"].smiles) == "FeS2"
    assert formula(ROSTER["iron-ii-sulfide"].smiles) == "FeS"
    assert "pyrite" not in MINERALS, (
        "pyrite has an Hfs in WEBBOOK and an S0s in nothing; if it prices now, "
        "`pyrite-roasting` is unblocked and PLAYABLE.md has a row to lose"
    )
    assert not inv.find("iron-disulfide").chargeable

"""A prep as DATA: the event layer has to be able to express a real one.

The engine has always guaranteed that a run is a pure function of (scenario,
event list) -- events are the only thing that may mutate a vessel, and they fire
strictly between integrations. The gap was that **no real prep went through it**.
The flagship examples called ``pour_into`` and ``filter_into`` directly, and the
things that make a prep honest were not reachable from a ``VesselSpec`` at all:
transfer losses could only be given to a ``Vessel`` constructor, ion
thermochemistry could only be given to ``build_network``, and a template's
``alpha`` was dropped on the way through ``TemplateSpec``.

So the replayable path and the honest path were disjoint sets, and a user
interface -- which is nothing but an event producer -- could only have driven the
half that was not honest.

These tests pin the join: the same preparation, run both ways, has to agree.
"""

import pytest

from chemsim.engine import Scenario, VesselSpec, World
from chemsim.engine.events import (
    CHARGE,
    FILL_HEADSPACE,
    FILTER,
    SET_ENVIRONMENT,
    SET_SHAKING,
    TRANSFER,
)
from chemsim.engine.scenario import TemplateSpec
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import (
    ThermochemistryProvider,
    dissociation_templates,
)
from chemsim.reactions.library import esterification
from chemsim.vessel import Vessel

WATER, ETOH = "O", "CCO"
TOLUENE = Molecule.from_smiles("Cc1ccccc1").smiles
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
ACETIC = "CC(=O)O"
N2, O2 = "N#N", "O=O"


# ---------------------------------------------------------------------------
# the two paths must be one simulation
# ---------------------------------------------------------------------------


def test_an_extraction_runs_the_same_through_events_as_through_calls():
    """The headline. Same charge, same contact, same draw -- one done by
    scheduling events against a World, one by calling the vessel directly."""
    spec = VesselSpec(volume=3.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)
    scenario = Scenario(
        feed_species=[WATER, TOLUENE, BENZOIC], templates=[],
        vessels={"funnel": spec, "organic": spec}, max_species=20,
    )
    w = World(scenario)
    w.schedule(0.0, CHARGE, "funnel",
               amounts={WATER: 27.7, TOLUENE: 4.7, BENZOIC: 0.02})
    w.schedule(1200.0, TRANSFER, "funnel", to="organic", phase="upper")
    w.run(duration=1800.0, dt=600.0)

    net = build_network(
        [WATER, TOLUENE, BENZOIC], [], thermo=ThermochemistryProvider(),
        max_species=20,
    )

    def flask():
        return Vessel(net, volume=3.0, T=298.15, T_env=298.15, UA=50.0,
                      kla=0.0, k_diss=0.0)

    funnel, organic = flask(), flask()
    funnel.charge({WATER: 27.7, TOLUENE: 4.7, BENZOIC: 0.02})
    for _ in range(2):
        funnel.step(600.0)
    funnel.pour_into(organic, phase="upper")
    funnel.step(600.0)

    assert w.vessels["organic"].state().total(BENZOIC) == pytest.approx(
        organic.state().total(BENZOIC), rel=1e-9
    )
    assert w.vessels["funnel"].state().total(WATER) == pytest.approx(
        funnel.state().total(WATER), rel=1e-9
    )


def test_transfer_losses_are_reachable_from_a_scenario():
    """They used to be constructible only by calling ``Vessel`` directly, so the
    one path a save could replay was the one path that could not lose
    anything."""
    lossy = VesselSpec(volume=1.0, T=275.0, T_env=275.0, UA=5.0, kla=0.0,
                       drain_time=5.0, crystal_size=50.0e-6)
    ideal = VesselSpec(volume=1.0, T=275.0, T_env=275.0, UA=5.0, kla=0.0)
    scenario = Scenario(
        feed_species=[WATER, BENZOIC], templates=[],
        vessels={"pot": lossy, "cake": lossy, "clean": ideal, "waste": ideal},
        max_species=20,
    )
    w = World(scenario)
    assert w.vessels["pot"].losses is not None
    assert w.vessels["clean"].losses is None
    assert w.vessels["pot"].losses.crystal_size == pytest.approx(50.0e-6)

    w.vessels["pot"].charge({WATER: 27.7})
    w.vessels["pot"].charge({BENZOIC: 0.05}, phase="solid")
    w.now(FILTER, "pot", filtrate="waste", cake="cake", porosity=0.4)
    w.run(duration=10.0, dt=10.0)

    # The crust stayed in the pot, and it is reported rather than differenced.
    assert w.vessels["pot"].state().total(BENZOIC) > 0.0
    assert "crystals left adhering" in w.vessels["pot"].crust_report()


def test_a_scenario_can_express_acid_base_chemistry():
    """Without ``electrolyte``, a scenario could not price an ion, so no pH, no
    acidified workup, no salting anything out -- the whole aqueous half of
    preparative chemistry was unreachable from the replayable path."""
    spec = VesselSpec(volume=1.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)
    scenario = Scenario(
        feed_species=[WATER, BENZOIC, "[Na+]", "[OH-]"],
        templates=[TemplateSpec.of(t) for t in dissociation_templates()],
        vessels={"flask": spec}, max_species=40, electrolyte=True,
    )
    w = World(scenario)
    w.vessels["flask"].charge({WATER: 55.3, BENZOIC: 0.01})
    w.run(duration=60.0, dt=60.0)

    # 0.01 M benzoic acid, pKa 4.20 -> pH ~= (4.20 - log10(0.01)) / 2 = 3.10
    assert w.vessels["flask"].pH == pytest.approx(3.10, abs=0.15)


def test_a_template_keeps_its_evans_polanyi_coefficient_through_a_scenario():
    """``alpha`` used to be dropped silently, so a saved run came back with
    every homologue on the same barrier and diverged from the original for no
    visible reason."""
    tmpl = esterification(alpha=0.3)
    spec = TemplateSpec.of(tmpl)
    assert spec.alpha == pytest.approx(0.3)
    assert spec.build().alpha == pytest.approx(0.3)

    round_tripped = Scenario.from_dict(
        Scenario(templates=[spec]).to_dict()
    ).templates[0]
    assert round_tripped.alpha == pytest.approx(0.3)


def test_every_template_field_survives_a_scenario_and_three_did_not():
    """⚠⚠⚠ P4: ``orders``, ``solid_catalyst`` and ``electrons`` were dropped too.

    The test above was written when ``alpha`` was found missing, and it pinned
    ``alpha``. Three fields were added to ``ReactionTemplate`` after it -- a
    declared rate law (S11), a heterogeneous catalyst gate (S1) and an electrode
    reaction's electron count (M8) -- and every one of them was dropped by
    ``TemplateSpec`` in exactly the same way, silently, for three milestones.

    **It was found by playing the game, not by a test.** Sulfur, air, water and a
    trace of NO2 taken off the shelf would not make vitriol at one atmosphere,
    because ``sulfur_combustion`` declares first order in oxygen and the network
    built from the scenario ran the SMARTS' own ninth-body mass action instead:
    0.02 mol of S8 under 0.05 mol of O2 burnt 0.0000% in an hour, under 0.50 mol
    it burnt 77.85%, which is a threshold where the declared law is a line.

    So this test asserts the GENERAL property rather than three more particulars:
    every field of a ``ReactionTemplate`` that a spec can carry, carries. A field
    added to the template and not to the spec is a field the game does not have,
    because a frontend can only reach the engine through a ``Scenario``.
    """
    import dataclasses

    from chemsim.reactions.library import sulfur_combustion

    tmpl = sulfur_combustion()
    assert tmpl.orders is not None, "the burner declares its own rate law"

    spec = TemplateSpec.of(tmpl)
    rebuilt = Scenario.from_dict(Scenario(templates=[spec]).to_dict()).templates[0]
    for field in dataclasses.fields(TemplateSpec):
        assert getattr(rebuilt, field.name) == getattr(spec, field.name), (
            f"{field.name} did not survive to_dict/from_dict"
        )
    # ⚠ AND BACK OUT THE OTHER SIDE AS A TEMPLATE, which is the half that
    # actually reaches ``build_network``. A list from JSON is not a tuple.
    got = rebuilt.build()
    assert got.orders == tmpl.orders
    assert isinstance(got.orders, tuple)
    assert got.solid_catalyst == tmpl.solid_catalyst
    assert got.electrons == tmpl.electrons

    # every field the TEMPLATE has, the SPEC has -- the rule the three misses broke
    spec_names = {f.name for f in dataclasses.fields(TemplateSpec)}
    # ⚠ Private fields are excluded and only those: ``_rxn`` is a parsed-SMARTS
    # cache, derived from ``smarts`` and rebuilt on demand, so carrying it would
    # be putting an RDKit object in a save file. Everything without a leading
    # underscore is state a template was CONSTRUCTED with and has to survive.
    tmpl_names = {f.name for f in dataclasses.fields(type(tmpl))
                  if not f.name.startswith("_")}
    assert tmpl_names <= spec_names, (
        f"ReactionTemplate has field(s) TemplateSpec cannot carry: "
        f"{sorted(tmpl_names - spec_names)}. A field that does not round-trip is "
        f"a field a saved run loses and a frontend cannot set."
    )


def test_a_solid_catalyst_gate_is_not_lost_on_the_way_to_a_network():
    """The same drop, in the direction that is WORSE than losing a rate law.

    A ``solid_catalyst`` is a GATE: without the crystal the reaction does not go
    at all. Dropped, the reaction goes with no catalyst -- so the flask that was
    supposed to need nickel reacts without it, which is the opposite of what the
    mechanic means. Eleven templates in the library declare one.

    Asserted through a BUILT NETWORK rather than on the spec, because the spec
    being right is not the claim: the gate has to reach ``KineticArrays``.
    """
    from chemsim.engine.world import World
    from chemsim.reactions.synthesis import ammonia_synthesis

    tmpl = ammonia_synthesis()
    assert tmpl.solid_catalyst == "iron"
    scenario = Scenario(
        templates=[TemplateSpec.of(tmpl)],
        feed_species=["N#N", "[H][H]"],
        vessels={"flask": VesselSpec(volume=1.0, T=700.0, T_env=700.0)},
        max_species=12,
    )
    world = World(Scenario.from_dict(scenario.to_dict()))
    made = [r for r in world.network.reactions if r.name.startswith(tmpl.name)]
    assert made, "the template made no reaction at all"
    # ⚠ The concrete reaction carries the LATTICE SMILES, not the mineral name --
    # ``build_network`` resolves it, because Layer 4 gets numbers and species and
    # never a name. Asserting the name here would have failed on a working gate.
    assert all(r.solid_catalyst == "[Fe]" for r in made), (
        f"the network's reactions lost their catalyst gate "
        f"({[r.solid_catalyst for r in made]}), so ammonia synthesis will run "
        f"in a flask with no iron in it"
    )
    # and BOTH directions are gated, which is what keeps detailed balance legal
    assert len(made) == 2, "ammonia synthesis is reversible; both halves gate"


def test_a_hammett_rho_reaches_the_network_and_not_only_the_spec():
    """G2's ring deactivation, through a ``Scenario``. ⚠ IT IS A DEFAULT.

    ``aromatic_nitration()`` ships with ``hammett_rho = -6.5``, so this was not
    an option nobody set -- it was the shipped behaviour being lost every time a
    frontend or a save went through ``TemplateSpec``, which is what ``examples``
    and ``tests/test_dropping_funnel.py`` have both done since G1. Nitration
    staged correctly in the harness and did not stage at all in the game.

    The observable is the BARRIER SPREAD: with rho in force, nitrating a
    deactivated ring costs more than nitrating benzene, so the reactions the
    network builds do not all share one Ea. Dropped, they do.
    """
    from chemsim.engine.world import World
    from chemsim.reactions.synthesis import aromatic_nitration

    tmpl = aromatic_nitration()
    assert tmpl.hammett_rho == pytest.approx(-6.5)
    scenario = Scenario(
        templates=[TemplateSpec.of(tmpl)],
        feed_species=[Molecule.from_smiles("c1ccccc1").smiles,
                      Molecule.from_smiles("O=[N+]([O-])O").smiles, WATER],
        vessels={"flask": VesselSpec(volume=1.0, T=320.0, T_env=320.0)},
        max_species=40,
    )
    world = World(Scenario.from_dict(scenario.to_dict()))
    nitrations = [r for r in world.network.reactions if r.name == tmpl.name]
    assert len(nitrations) >= 2, "need at least two rings to compare barriers"
    barriers = {round(r.Ea, 6) for r in nitrations}
    assert len(barriers) > 1, (
        f"every nitration in the network got the same barrier "
        f"({barriers}), so hammett_rho did not survive the scenario and a "
        f"deactivated ring nitrates as fast as benzene"
    )


# ---------------------------------------------------------------------------
# the verbs a real prep needs
# ---------------------------------------------------------------------------


def test_filling_the_headspace_is_a_verb_because_the_amount_depends_on_state():
    """"Open the flask to the room" means different moles once there is liquid
    in it, so a fixed CHARGE cannot express it."""
    spec = VesselSpec(volume=2.0, T=298.15, T_env=298.15, UA=5.0, kla=0.0)
    scenario = Scenario(
        feed_species=[WATER, ETOH, N2, O2], templates=[],
        vessels={"empty": spec, "full": spec},
    )
    w = World(scenario)
    w.vessels["full"].charge({WATER: 55.0})          # ~1 L of the 2 L
    w.now(FILL_HEADSPACE, "empty")
    w.now(FILL_HEADSPACE, "full")
    w.run(duration=1.0, dt=1.0)

    empty = sum(w.vessels["empty"].state().n_gas.values())
    full = sum(w.vessels["full"].state().n_gas.values())
    assert empty > full, "less headspace holds less air"
    assert full == pytest.approx(empty / 2.0, rel=0.1)

    # ... and it takes a composition, so an inert atmosphere is one payload away
    w2 = World(scenario)
    w2.now(FILL_HEADSPACE, "empty", composition={N2: 1.0})
    w2.run(duration=1.0, dt=1.0)
    assert w2.vessels["empty"].state().n_gas[O2] == 0.0


def test_shaking_is_its_own_verb_and_survives_a_save():
    """Distinct from stirring: a flask can be stirred hard under a condenser
    without two layers ever being brought into contact."""
    spec = VesselSpec(volume=3.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)
    scenario = Scenario(
        feed_species=[WATER, TOLUENE], templates=[],
        vessels={"funnel": spec}, max_species=20,
    )
    w = World(scenario)
    w.now(SET_SHAKING, "funnel", k_lle=0.25)
    w.run(duration=1.0, dt=1.0)
    assert w.vessels["funnel"].k_lle == pytest.approx(0.25)
    assert w.vessels["funnel"].conditions.k_lle == pytest.approx(0.25)

    assert World.load(w.save()).vessels["funnel"].k_lle == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# a save has to carry the second liquid layer
# ---------------------------------------------------------------------------


def test_a_two_layer_flask_survives_a_save_without_remixing():
    """The layers are state, not a derived quantity. Re-deriving them on load
    would make a reload depend on the stability test agreeing with itself, and
    a funnel that came back remixed would silently undo a separation."""
    spec = VesselSpec(volume=3.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)
    scenario = Scenario(
        feed_species=[WATER, TOLUENE, BENZOIC], templates=[],
        vessels={"funnel": spec, "organic": spec}, max_species=20,
    )
    w = World(scenario)
    w.vessels["funnel"].charge({WATER: 27.7, TOLUENE: 4.7, BENZOIC: 0.02})
    w.run(duration=1200.0, dt=600.0)
    assert w.vessels["funnel"].two_phase

    before = w.vessels["funnel"].state()
    reloaded = World.load(w.save())
    after = reloaded.vessels["funnel"].state()

    assert after.two_phase
    for s in (WATER, TOLUENE, BENZOIC):
        assert after.n_liquid[s] == pytest.approx(before.n_liquid[s], rel=1e-12)
        assert after.n_liquid2[s] == pytest.approx(before.n_liquid2[s], rel=1e-12)


def test_a_run_continued_from_a_save_matches_one_that_never_stopped():
    """The property the whole event layer exists for, now exercised through a
    phase separation and a pending transfer rather than a bare integration."""
    spec = VesselSpec(volume=3.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)
    scenario = Scenario(
        feed_species=[WATER, TOLUENE, BENZOIC], templates=[],
        vessels={"funnel": spec, "organic": spec}, max_species=20,
    )

    def build():
        w = World(scenario)
        w.schedule(0.0, CHARGE, "funnel",
                   amounts={WATER: 27.7, TOLUENE: 4.7, BENZOIC: 0.02})
        w.schedule(1800.0, TRANSFER, "funnel", to="organic", phase="upper")
        return w

    straight = build()
    straight.run(duration=2400.0, dt=600.0)

    interrupted = build()
    interrupted.run(duration=1200.0, dt=600.0)       # stop before the draw
    resumed = World.load(interrupted.save())
    resumed.run(duration=1200.0, dt=600.0)

    assert resumed.vessels["organic"].state().total(BENZOIC) == pytest.approx(
        straight.vessels["organic"].state().total(BENZOIC), rel=1e-9
    )
    assert resumed.t == pytest.approx(straight.t)


def test_the_save_version_refuses_an_older_layout():
    """The state vector grew a liquid layer at v3, v4 added the SCRIPT, and v5
    added the APPARATUS.

    v4's script is the record of everything asked of the world, which is what a
    run became a pure function of once a duration could be DISCOVERED rather than
    declared. v5 is ``Scenario.edges`` plus the SWAP_RECEIVER and SET_EDGE verbs:
    a rig used to exist only in Python, so a still could not be saved at all.
    v6 is ``add_dropwise``. v7 is the SHELF -- ``World.shelf`` plus the BOTTLE
    and CHARGE_STOCK verbs -- and ``Scenario.generations``, which until P2 could
    not be requested through a scenario at all, so a world always built its
    network to a fixpoint.

    ⚠ **A v4 save would LOAD CLEANLY and mean something different** -- it has no
    edges, so it would replay as an uncoupled bench, which is a different
    experiment rather than a missing field. That is exactly the case a version
    number exists for, and it is why this bumped instead of defaulting."""
    from chemsim.engine import SAVE_VERSION

    spec = VesselSpec(volume=1.0)
    w = World(Scenario(feed_species=[WATER], templates=[],
                       vessels={"flask": spec}))
    blob = w.save()
    assert blob["version"] == SAVE_VERSION == 9
    assert "script" in blob
    # the apparatus travels with the scenario, empty or not
    assert blob["scenario"]["edges"] == []
    # ⚠ R3: the scenario's key SET is pinned, the same discipline P4 imposed on
    # ``TemplateSpec``'s fields, from the opposite direction. ``prune_threshold``
    # sat in this dict for three milestones reaching nothing -- a field a
    # frontend can set that the engine never reads is a lie in the format, and
    # the way it survived is that no test looked at the SET. Growing this set
    # is fine; growing it means editing this line, which is the point.
    assert set(blob["scenario"]) == {
        "templates", "feed_species", "vessels", "edges", "max_species",
        "generations", "T_build", "electrolyte",
    }
    for older in (3, 4, 5, 6, 8):
        stale = dict(blob, version=older)
        with pytest.raises(ValueError, match="save format version"):
            World.load(stale)


# ---------------------------------------------------------------------------
# and the whole thing at once
# ---------------------------------------------------------------------------


def test_a_workup_is_expressible_end_to_end_as_an_event_list():
    """React, then extract, then wash -- as data, with losses on and ions
    priced. This is the shape a user interface would emit."""
    pot = VesselSpec(volume=3.0, T=330.0, T_env=330.0, UA=20.0, kla=0.0,
                     drain_time=5.0, crystal_size=50.0e-6)
    plain = VesselSpec(volume=3.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)
    scenario = Scenario(
        feed_species=[WATER, ETOH, ACETIC, TOLUENE], templates=[],
        vessels={"pot": pot, "organic": plain, "aqueous": plain},
        max_species=30,
    )
    w = World(scenario)
    w.schedule(0.0, CHARGE, "pot", amounts={WATER: 27.7, ACETIC: 0.05})
    w.schedule(600.0, SET_ENVIRONMENT, "pot", T_env=298.15)
    w.schedule(600.0, CHARGE, "pot", amounts={TOLUENE: 4.7})
    w.schedule(1200.0, TRANSFER, "pot", to="organic", phase="upper")
    w.schedule(1800.0, TRANSFER, "pot", to="aqueous", phase="liquid")
    w.run(duration=2400.0, dt=300.0)

    charged = 0.05
    recovered = sum(
        w.vessels[v].state().total(ACETIC)
        for v in ("pot", "organic", "aqueous")
    )
    assert recovered == pytest.approx(charged, rel=1e-9), "nothing may be lost"
    assert w.vessels["organic"].state().total(ACETIC) > 0.0
    assert any("transfer" in line for line in w.transfer_log)

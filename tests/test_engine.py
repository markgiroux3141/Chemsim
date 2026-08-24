"""Layer 6 -- engine: determinism, events, and save/load.

The engine has almost no chemistry in it, so these tests are about the three
guarantees it exists to provide: that events are the only thing that can mutate a
vessel, that a run is reproducible from (scenario, events), and that a save
round-trips without the network having to be serialized.
"""

import json

import pytest

from chemsim.engine import Scenario, TemplateSpec, VesselSpec, World
from chemsim.engine.events import (
    CHARGE,
    SET_ENVIRONMENT,
    SET_HEAT,
    SET_VENT,
    TRANSFER,
)

ACID, ETHANOL, WATER, ESTER = "CC(=O)O", "CCO", "O", "CCOC(C)=O"

FISCHER = TemplateSpec(
    name="fischer",
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000, reversible=True,
)


def make_scenario(**vessels):
    return Scenario(
        templates=[FISCHER],
        feed_species=[ACID, ETHANOL, WATER],
        vessels=vessels or {"flask": VesselSpec(volume=1.0, T=298.15, UA=0.5)},
    )


@pytest.fixture
def world():
    w = World(scenario=make_scenario(), seed=7)
    w.schedule(0.0, CHARGE, "flask", amounts={ACID: 3.0, ETHANOL: 3.0})
    return w


# --------------------------------------------------------------------------
# events
# --------------------------------------------------------------------------


def test_events_fire_at_their_scheduled_time(world):
    world.schedule(600.0, SET_HEAT, "flask", watts=50.0)

    world.run(300.0, dt=100.0)
    assert world.vessels["flask"].Q_input == 0.0, "fired early"

    world.run(600.0, dt=100.0)
    assert world.vessels["flask"].Q_input == 50.0, "never fired"


def test_an_event_mid_step_takes_effect_at_its_own_instant():
    """Stepping once by 600 s and six times by 100 s must agree: the interval is
    split at the event time, so the result cannot depend on the caller's dt."""
    results = []
    for dt in (600.0, 100.0):
        w = World(scenario=make_scenario(), seed=1)
        w.schedule(0.0, CHARGE, "flask", amounts={ACID: 2.0, ETHANOL: 2.0})
        w.schedule(250.0, SET_HEAT, "flask", watts=30.0)
        w.run(600.0, dt=dt)
        results.append(w.vessels["flask"].T)
    assert results[0] == pytest.approx(results[1], rel=1e-3)


def test_same_instant_events_apply_in_submission_order():
    """Ties must break on submission order, never on dict or set iteration --
    otherwise replay stops being reproducible."""
    w = World(scenario=make_scenario(), seed=1)
    w.schedule(0.0, SET_HEAT, "flask", watts=10.0)
    w.schedule(0.0, SET_HEAT, "flask", watts=99.0)
    w.run(10.0, dt=10.0)
    assert w.vessels["flask"].Q_input == 99.0


def test_scheduling_in_the_past_is_rejected(world):
    world.run(100.0, dt=100.0)
    with pytest.raises(ValueError, match="already at"):
        world.schedule(50.0, SET_HEAT, "flask", watts=10.0)


def test_unknown_event_kinds_and_vessels_are_rejected(world):
    with pytest.raises(ValueError, match="unknown event kind"):
        world.schedule(10.0, "explode", "flask")
    with pytest.raises(KeyError, match="no vessel"):
        world.schedule(10.0, SET_HEAT, "beaker", watts=1.0)


def test_every_control_event_reaches_the_vessel(world):
    world.schedule(1.0, SET_HEAT, "flask", watts=12.0)
    world.schedule(2.0, SET_ENVIRONMENT, "flask", T_env=273.0)
    world.schedule(3.0, SET_VENT, "flask", k_vent=0.0)
    world.run(10.0, dt=10.0)

    v = world.vessels["flask"]
    assert (v.Q_input, v.T_env, v.k_vent) == (12.0, 273.0, 0.0)
    # and the integrator must see them, not just the wrapper
    assert v.conditions.Q_input == 12.0
    assert v.conditions.T_env == 273.0
    assert v.conditions.k_vent == 0.0


# --------------------------------------------------------------------------
# transfers
# --------------------------------------------------------------------------


def test_pouring_moves_matter_and_conserves_it():
    w = World(
        scenario=make_scenario(
            a=VesselSpec(volume=1.0), b=VesselSpec(volume=1.0)
        ),
        seed=1,
    )
    w.schedule(0.0, CHARGE, "a", amounts={ETHANOL: 2.0})
    w.schedule(1.0, TRANSFER, "a", to="b", fraction=0.25)
    w.run(10.0, dt=10.0)

    a, b = w.vessels["a"].state(), w.vessels["b"].state()
    # Conservation is exact -- a transfer must not create or destroy anything.
    assert a.total(ETHANOL) + b.total(ETHANOL) == pytest.approx(2.0, rel=1e-6)
    # The fraction is of the LIQUID, and a little has already evaporated in the
    # second before the pour, so the amount moved is slightly under a quarter.
    assert b.total(ETHANOL) == pytest.approx(0.5, rel=0.02)
    assert b.total(ETHANOL) < 0.5


def test_pouring_carries_enthalpy():
    """Hot into cold must warm the cold one -- a transfer that only moved moles
    would silently discard the energy."""
    w = World(
        scenario=make_scenario(
            hot=VesselSpec(volume=1.0, T=360.0, UA=0.0),
            cold=VesselSpec(volume=1.0, T=280.0, UA=0.0),
        ),
        seed=1,
    )
    w.schedule(0.0, CHARGE, "hot", amounts={ETHANOL: 2.0})
    w.schedule(0.0, CHARGE, "cold", amounts={ETHANOL: 2.0})
    w.schedule(1.0, TRANSFER, "hot", to="cold", fraction=1.0)
    w.run(5.0, dt=5.0)

    T = w.vessels["cold"].T
    assert 280.0 < T < 360.0, f"cold vessel ended at {T}"


def test_pouring_between_incompatible_vessels_is_rejected():
    w1 = World(scenario=make_scenario(), seed=1)
    other = Scenario(templates=[], feed_species=[WATER],
                     vessels={"flask": VesselSpec(volume=1.0)})
    w2 = World(scenario=other, seed=1)
    with pytest.raises(ValueError, match="different networks"):
        w1.vessels["flask"].pour_into(w2.vessels["flask"])


# --------------------------------------------------------------------------
# determinism
# --------------------------------------------------------------------------


def test_a_run_is_reproducible_from_scenario_and_events():
    def run():
        w = World(scenario=make_scenario(), seed=42)
        w.schedule(0.0, CHARGE, "flask", amounts={ACID: 3.0, ETHANOL: 3.0})
        w.schedule(60.0, SET_HEAT, "flask", watts=40.0)
        w.run(1200.0, dt=200.0)
        return w.vessels["flask"].state()

    a, b = run(), run()
    assert a.T == b.T
    assert a.n_liquid == b.n_liquid
    assert a.n_gas == b.n_gas


def test_species_ordering_is_stable_across_rebuilds():
    """Indices come from dict insertion order; if that ever became set-ordered,
    saves would silently load into the wrong species."""
    a = World(scenario=make_scenario(), seed=1)
    b = World(scenario=make_scenario(), seed=1)
    assert a.vessels["flask"].species == b.vessels["flask"].species


# --------------------------------------------------------------------------
# save / load
# --------------------------------------------------------------------------


def test_save_is_json_serializable_and_holds_no_network(world):
    world.run(300.0, dt=300.0)
    blob = json.dumps(world.save())      # would raise on numpy or Molecule
    data = json.loads(blob)

    assert set(data) >= {"version", "t", "seed", "scenario", "vessels", "events"}
    # The scenario carries templates as SMARTS text; no discovered reaction list.
    assert data["scenario"]["templates"][0]["smarts"] == FISCHER.smarts
    assert "reactions" not in data


def test_save_load_round_trips_exactly(world):
    world.schedule(100.0, SET_HEAT, "flask", watts=25.0)
    world.run(900.0, dt=300.0)

    restored = World.load(json.loads(json.dumps(world.save())))
    before, after = world.vessels["flask"].state(), restored.vessels["flask"].state()

    assert restored.t == world.t
    assert after.T == before.T
    assert after.n_liquid == before.n_liquid
    assert after.n_solid == before.n_solid
    assert restored.vessels["flask"].Q_input == 25.0


def test_a_reloaded_world_continues_identically(world):
    world.run(600.0, dt=300.0)
    restored = World.load(json.loads(json.dumps(world.save())))

    world.run(600.0, dt=300.0)
    restored.run(600.0, dt=300.0)

    assert restored.vessels["flask"].state().n_liquid == pytest.approx(
        world.vessels["flask"].state().n_liquid, rel=1e-9
    )


def test_pending_events_survive_a_save(world):
    world.schedule(5000.0, SET_HEAT, "flask", watts=80.0)
    restored = World.load(json.loads(json.dumps(world.save())))
    assert len(restored.pending_events) == len(world.pending_events)

    restored.run(6000.0, dt=1000.0)
    assert restored.vessels["flask"].Q_input == 80.0


def test_an_incompatible_save_version_is_refused(world):
    data = world.save()
    data["version"] = 1
    with pytest.raises(ValueError, match="save format version"):
        World.load(data)

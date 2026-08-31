""""Wait until": the instant DISCOVERED rather than declared.

Every duration in this project used to be a number of seconds, so "reflux until
the head stabilises" and "cool until crystals appear" were inexpressible, and a
frontend built against fixed durations would have encoded the wrong shape into
every screen.

These tests pin four separate things, and they are separate on purpose:

  * **the mechanism** -- a scipy terminal root lands ON the condition, to solver
    tolerance, and does not overshoot it;
  * **the clock** -- a terminal event returns the state AT the event, so the span
    that HAPPENED is shorter than the span that was asked for, and every clock
    above the solver has to move by the actual figure. This is the bug the shape
    of the API is designed to prevent;
  * **the three non-answers** -- already true, timed out, and never true are
    different outcomes and a player is owed the difference;
  * **the recipe** -- a run stays replayable, from the CONDITION and not from the
    instant it resolved to. See ``World.script``.
"""

import pytest

from chemsim.engine import SAVE_VERSION, Scenario, VesselSpec, World
from chemsim.engine.events import CHARGE, SET_ENVIRONMENT
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.vessel import (
    Condition,
    Vessel,
    acidic_to,
    boils,
    cools_to,
    crystals,
    dissolves,
    reaches,
    temperature_steady,
)

ETOH, WATER, N2, O2 = "CCO", "O", "N#N", "O=O"
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
NA = "[Na+]"


@pytest.fixture(scope="module")
def solvent_net(thermo_module):
    return build_network([ETOH, WATER, N2, O2], [], thermo=thermo_module,
                         max_species=20)


@pytest.fixture
def hotplate(solvent_net):
    """50/50 ethanol/water over a 60 W hotplate, open to the room."""
    v = Vessel(solvent_net, volume=2.0, T=298.15, T_env=298.15, UA=0.5,
               Q_input=60.0, kla=5.0)
    v.charge({ETOH: 3.0, WATER: 3.0})
    v.fill_headspace_with_air()
    return v


# ---------------------------------------------------------------------------
# the mechanism: it lands ON the condition
# ---------------------------------------------------------------------------


def test_a_wait_lands_exactly_on_its_condition(hotplate):
    """The headline. A fixed duration forces a choice between overshooting the
    interesting instant and paying for steps that resolve nothing; a root does
    neither."""
    out = hotplate.wait_until(reaches(340.0), 3600.0)

    assert not out.timed_out and not out.already
    assert hotplate.T == pytest.approx(340.0, abs=1e-6)
    assert 0.0 < out.elapsed < 3600.0


def test_the_discovered_instant_does_not_depend_on_the_timeout_given(solvent_net):
    """The determinism claim, at the level it can be tested. If the instant moved
    with the bound the caller happened to choose, "discovered" would be a
    euphemism for "wherever the solver stopped"."""
    def when(timeout):
        v = Vessel(solvent_net, volume=2.0, T=298.15, T_env=298.15, UA=0.5,
                   Q_input=60.0, kla=5.0)
        v.charge({ETOH: 3.0, WATER: 3.0})
        v.fill_headspace_with_air()
        return v.wait_until(reaches(340.0), timeout).elapsed

    assert when(900.0) == pytest.approx(when(3600.0), rel=1e-6)


def test_the_clock_advances_by_what_HAPPENED_not_by_what_was_asked(hotplate):
    """⚠ The trap this API exists to close. ``sol.t[-1]`` is less than the
    requested span when a terminal event fires, so a caller that advanced its own
    clock by the timeout would silently drift out of step with the vessel."""
    out = hotplate.wait_until(reaches(340.0), 3600.0)
    assert hotplate.t == pytest.approx(out.elapsed)
    assert hotplate.t < 3600.0


def test_waiting_for_a_boil_agrees_with_the_boiling_readout(hotplate):
    """The condition and the readout must be the same physics, or a player is told
    two different things about one flask."""
    assert not hotplate.is_boiling
    out = hotplate.wait_until(boils(), 7200.0)
    assert not out.timed_out
    assert hotplate.is_boiling
    assert hotplate.T == pytest.approx(hotplate.bubble_point(), abs=0.5)


# ---------------------------------------------------------------------------
# ⚠ the pre-existing bug this uncovered
# ---------------------------------------------------------------------------


def test_dissolved_air_does_not_make_a_cold_flask_boil(solvent_net):
    """⚠ A CONFIDENT WRONG NUMBER, PRE-EXISTING, found by building ``boils()``.

    A liquid in equilibrium with a headspace of air holds exactly enough
    dissolved N2 and O2 to return that air's own partial pressures by Henry's
    law. Summing ALL the equilibrium pressures therefore reaches ambient at every
    temperature -- so a 50/50 ethanol/water flask at 298 K reported ``is_boiling``
    and a bubble point of 297.8 K rather than 352.9.

    A dissolved gas at equilibrium exerts no net driving force, so it cannot
    displace the atmosphere, which is what boiling is. Condensables only.
    """
    v = Vessel(solvent_net, volume=2.0, T=298.15, T_env=298.15, UA=0.5, kla=5.0)
    v.charge({ETOH: 3.0, WATER: 3.0})
    v.fill_headspace_with_air()
    v.run(60.0)

    assert not v.is_boiling, "a room-temperature flask is not boiling"
    assert v.bubble_point() > 340.0
    # ... and the whole sum really is at ambient, which is why this bit.
    p = v.integrator.equilibrium_pressures(v._nL, v.T, v._nL2)
    assert float(p.sum()) == pytest.approx(v.P_ambient, rel=1e-3)
    assert v.integrator.volatile_pressure(v._nL, v.T, v._nL2) < 0.2


def test_the_same_flask_without_air_was_always_right(thermo_module):
    """The other half of the bug: with no non-condensable in the network the old
    expression and the new one agree exactly, which is why this survived."""
    net = build_network([ETOH, WATER], [], thermo=thermo_module, max_species=10)
    v = Vessel(net, volume=2.0, T=298.15, T_env=298.15, UA=0.5, kla=5.0)
    v.charge({ETOH: 3.0, WATER: 3.0})
    v.run(60.0)
    p = v.integrator.equilibrium_pressures(v._nL, v.T, v._nL2)
    assert v.integrator.volatile_pressure(v._nL, v.T, v._nL2) == pytest.approx(
        float(p.sum())
    )


# ---------------------------------------------------------------------------
# the three non-answers
# ---------------------------------------------------------------------------


def test_a_condition_already_true_returns_at_once_and_says_so(hotplate):
    """scipy locates sign CHANGES, so a satisfied condition is not a root and the
    solve would run the whole span and report nothing. "It is already above 300 K"
    is an answer, not a failure, and not the same answer as "it got there"."""
    out = hotplate.wait_until(reaches(200.0), 3600.0)
    assert out.already and not out.timed_out
    assert out.elapsed == 0.0
    assert hotplate.t == 0.0


def test_a_condition_that_never_comes_true_times_out_cleanly(hotplate):
    """An unbounded wait is a hang, so the timeout is required and reaching it is
    reported rather than raised."""
    out = hotplate.wait_until(cools_to(200.0), 30.0)
    assert out.timed_out and not out.already
    assert out.fired is None
    assert out.elapsed == pytest.approx(30.0)
    assert hotplate.t == pytest.approx(30.0)


def test_several_conditions_race_and_the_winner_is_named(hotplate):
    """"Heat until it boils, but stop at 345 K" -- the lower one has to win, and
    the caller has to be told which."""
    out = hotplate.wait_until([boils(), reaches(345.0)], 7200.0)
    assert out.fired == reaches(345.0)
    assert hotplate.T == pytest.approx(345.0, abs=1e-6)


def test_a_wait_needs_a_bound_and_a_condition(hotplate):
    with pytest.raises(ValueError, match="at least one condition"):
        hotplate.wait_until([], 100.0)
    with pytest.raises(ValueError, match="timeout must be positive"):
        hotplate.wait_until(reaches(340.0), 0.0)


def test_a_zero_rate_is_refused_because_it_is_not_a_root():
    """⚠ dT/dt approaches zero ASYMPTOTICALLY. Offering "wait until the
    temperature stops changing" as an equality would be offering a hang, so the
    verb takes a tolerance and refuses zero with the reason."""
    with pytest.raises(ValueError, match="POSITIVE rate tolerance"):
        temperature_steady(0.0)
    with pytest.raises(ValueError, match="POSITIVE rate tolerance"):
        Condition("temperature_steady", -1.0)


def test_temperature_steady_fires_on_the_plateau(hotplate):
    """And the tolerance form DOES fire, where the equality never would: the flask
    stops warming when the latent heat starts absorbing the hotplate.

    ⚠ Reached via ``boils()`` first, and that is not tidiness -- see the test below.
    """
    hotplate.wait_until(boils(), 7200.0)
    out = hotplate.wait_until(temperature_steady(0.01), 3600.0)
    assert not out.timed_out
    assert hotplate.T == pytest.approx(hotplate.bubble_point(), abs=1.0)


def test_a_rate_tolerance_fires_on_the_FIRST_transient_not_the_plateau(hotplate):
    """⚠ THE TRAP THIS ARC'S OWN PROBE WAS TOO COARSE TO SEE, caught here instead.

    A flask whose headspace has just been filled with air evaporates hard for a
    moment, so its dT/dt starts negative, crosses zero within a second, and only
    then climbs to the steady +0.096 K/s that carries it to the boil. A bare
    ``temperature_steady`` therefore fires in that first second at 298 K -- and
    reports, correctly, that the temperature was momentarily steady.

    Pinned as behaviour rather than filed as a bug, because it IS what the condition
    says. The lesson is that "until it stabilises" needs the regime named first, and
    that is already expressible.

    ⚠⚠ S13: THE TRAP DID NOT GO AWAY, IT WENT BELOW THE DEFAULT TOLERANCE, AND
    WHAT MOVED IT WAS A BOILING POINT. Ethanol was priced by Joback at 337.54 K
    against a measured 351.57, so the flask was roughly twice as volatile at
    298 K as it should have been and the opening swing was **-24 K/s**. With the
    measured record it is **-1.42 K/s** at 0.25 s, still crossing zero inside
    half a second -- but BDF at the default tolerance does not resolve a spike
    that brief, so no sign change appears at any accepted step and the condition
    runs on to the plateau instead.

    ⚠ The trap is still THERE, and the companion test below reaches it by
    tightening the tolerance rather than by shrinking the step. ``max_step``
    does NOT recover it (0.1 and 0.01 both still land at 966.9 s), because the
    loose error control has smoothed the spike out of the computed solution
    rather than merely stepping over it. **THE SOLVER IS PART OF THE
    ARITHMETIC**, and a behaviour this project had written down was resting on a
    wrong boiling point making a transient big enough to see.
    """
    out = hotplate.wait_until(temperature_steady(0.01), 7200.0)
    assert not out.timed_out
    assert out.elapsed == pytest.approx(966.9, abs=5.0), (
        "at the default tolerance the opening swing is not resolved, so this "
        "reaches the boiling plateau"
    )
    assert hotplate.T == pytest.approx(352.0, abs=1.0)


def test_the_opening_swing_is_still_there_at_a_tighter_TOLERANCE(hotplate):
    """The other half of the finding above: it is a resolution limit, not a fact.

    ⚠ A behaviour that disappears when the tolerance is loosened has not
    stopped happening. At rtol 1e-9 the same flask, unchanged in every other
    respect, fires at **0.08 s and 297.78 K** -- on the evaporative swing
    through zero, exactly where the original version of this test said it would.
    """
    out = hotplate.wait_until(
        temperature_steady(0.01), 7200.0, rtol=1.0e-9, atol=1.0e-12
    )
    assert not out.timed_out
    assert out.elapsed < 5.0, "it fires on the initial swing through zero"
    assert hotplate.T < 300.0, "nowhere near the boiling plateau"


# ---------------------------------------------------------------------------
# a condition about matter, not about temperature
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def crystal_net():
    return build_network([WATER, BENZOIC, NA], dissociation_templates(),
                         thermo=electrolyte_provider(), max_species=60)


def test_waiting_for_a_crop_to_appear(crystal_net):
    """"Cool until crystals appear". nS starts at EXACTLY zero, which is the state
    this project has twice paid for putting a switch at -- so the threshold sits
    three decades above the solver's own atol rather than at zero."""
    # 0.02 mol in ~0.5 L is 4.9 g/L, comfortably under the ~10 g/L benzoic acid
    # dissolves at 340 K and comfortably over the 1.62 g/L it holds at 275. The
    # margins matter: the test is about the ROOT, not about a marginal solubility.
    v = Vessel(crystal_net, volume=1.0, T=340.0, T_env=275.0, UA=5.0, kla=0.0,
               k_diss=0.05)
    v.charge({WATER: 27.7, BENZOIC: 0.02})
    v.run(30.0)                                   # dissolve it warm
    assert v.state().n_solid[BENZOIC] < 1e-9

    out = v.wait_until(crystals(BENZOIC), 7200.0)
    assert not out.timed_out, "cooling a saturated solution must crop something"
    assert v.state().n_solid[BENZOIC] == pytest.approx(1.0e-6, rel=1e-3)
    assert v.T < 340.0


def test_waiting_for_a_solid_to_dissolve(crystal_net):
    """The mirror image, and the one that says "stir until it all goes in"."""
    v = Vessel(crystal_net, volume=1.0, T=275.0, T_env=340.0, UA=20.0, kla=0.0,
               k_diss=0.05)
    v.charge({WATER: 27.7})
    v.charge({BENZOIC: 0.002}, phase="solid")
    out = v.wait_until(dissolves(BENZOIC), 7200.0)
    assert not out.timed_out
    assert v.state().n_solid[BENZOIC] <= 1.0e-6 * (1.0 + 1e-6)


def test_waiting_on_a_pH(crystal_net):
    """"Acidify until pH 2" -- and the root is read off the state vector the
    solver is trying, never off the vessel's own attributes."""
    v = Vessel(crystal_net, volume=1.0, T=298.15, T_env=298.15, UA=50.0,
               kla=0.0, k_diss=0.0)
    v.charge({WATER: 27.7, BENZOIC: 0.02})
    out = v.wait_until(acidic_to(4.0), 3600.0)
    assert not out.timed_out
    assert v.pH == pytest.approx(4.0, abs=0.05)


# ---------------------------------------------------------------------------
# Layer 6: the world, and the recipe
# ---------------------------------------------------------------------------


def _boil_world():
    spec = VesselSpec(volume=2.0, T=298.15, T_env=298.15, UA=0.5, Q_input=60.0,
                      kla=5.0)
    cold = VesselSpec(volume=1.0, T=298.15, T_env=298.15, UA=0.5, kla=0.0)
    scenario = Scenario(
        feed_species=[ETOH, WATER, N2, O2], templates=[],
        vessels={"pot": spec, "receiver": cold}, max_species=20,
    )
    w = World(scenario)
    w.now(CHARGE, "pot", amounts={ETOH: 3.0, WATER: 3.0})
    return w


def test_every_vessel_advances_by_the_discovered_time():
    """A wait is about one flask but it moves the whole world, and it has to move
    all of it by the SAME amount or the vessels' clocks disagree."""
    w = _boil_world()
    w.step(1.0)                                   # let the charge land
    out = w.wait_until("pot", reaches(340.0), 3600.0)

    assert not out.timed_out
    assert w.t == pytest.approx(1.0 + out.elapsed)
    for v in w.vessels.values():
        assert v.t == pytest.approx(w.t)


def test_a_pending_event_still_fires_on_time_inside_a_wait():
    """A wait must not swallow an action scheduled in the middle of it -- a
    dropwise addition due at t=60 has to happen at t=60 even if the wait was told
    to run for an hour."""
    w = _boil_world()
    w.step(1.0)
    w.schedule(60.0, SET_ENVIRONMENT, "pot", T_env=350.0)
    out = w.wait_until("pot", reaches(340.0), 3600.0)

    assert not out.timed_out
    assert w.vessels["pot"].T_env == pytest.approx(350.0), (
        "the scheduled event was skipped by the wait"
    )
    assert w.t > 60.0


def test_the_script_records_the_condition_and_not_the_instant():
    """⚠ THE FORK, pinned. Recording the discovered instant would make the saved
    artifact a transcript rather than a recipe -- fixed durations wearing a
    condition's name. The condition is what is stored; the instant is reported as
    the outcome it is."""
    w = _boil_world()
    w.step(1.0)
    out = w.wait_until("pot", reaches(340.0), 3600.0)

    waits = [e for e in w.script if e["do"] == "wait_until"]
    assert len(waits) == 1
    assert waits[0]["conditions"] == [reaches(340.0).to_dict()]
    assert waits[0]["timeout"] == pytest.approx(3600.0)
    assert "elapsed" not in waits[0], "the instant is derived data, not recipe"
    # ... and it is still reported, in the log, as what happened.
    assert any("wait pot" in line for line in w.transfer_log)
    assert out.elapsed > 0.0


def test_a_run_that_waited_replays_from_its_recipe():
    """The whole point of storing the condition: the recipe is complete, so a
    fresh world driven by the script alone reaches the same place. The instant is
    RE-DISCOVERED, which is why this is a tolerance and not an equality."""
    w = _boil_world()
    w.step(1.0)
    w.wait_until("pot", reaches(340.0), 3600.0)
    w.step(30.0)
    saved = w.save()

    again = World.replay(saved)
    assert again.t == pytest.approx(w.t, rel=1e-6)
    assert again.vessels["pot"].T == pytest.approx(w.vessels["pot"].T, rel=1e-6)
    assert again.vessels["pot"].state().n_liquid[ETOH] == pytest.approx(
        w.vessels["pot"].state().n_liquid[ETOH], rel=1e-6
    )


def test_the_save_format_had_to_move_and_says_so():
    """A save from before the script exists cannot be replayed, and must fail
    loudly rather than replay a run whose durations it does not know.

    ⚠ It has moved again since, to 5, for the APPARATUS -- ``Scenario.edges``.
    Same reasoning one layer out: a v4 save has no edges and would replay as an
    uncoupled bench, i.e. a different experiment, so it is refused rather than
    defaulted. And again to 6 for ``add_dropwise``, where the failure is worse:
    an unknown SCRIPT VERB is only discovered part-way through the walk, so a
    v5 reader would run every entry before it and stop half-way through the
    recipe with a world that looks finished.

    ⚠ And again to 7 for the SHELF and ``Scenario.generations`` -- see P2. A
    ``bottle`` is a trailing event, so a v6 reader would fail on it after
    executing the whole recipe."""
    assert SAVE_VERSION == 7
    w = _boil_world()
    w.step(1.0)
    saved = w.save()
    assert "script" in saved

    stale = dict(saved, version=3)
    with pytest.raises(ValueError, match="version 3"):
        World.replay(stale)
    with pytest.raises(ValueError, match="save format version 3"):
        World.load(stale)


def test_load_carries_the_script_without_re_running_it():
    """``load`` restores the state and carries the history; ``replay`` re-derives
    it. Confusing the two would double every event."""
    w = _boil_world()
    w.step(1.0)
    w.wait_until("pot", reaches(340.0), 3600.0)
    saved = w.save()

    back = World.load(saved)
    assert back.t == pytest.approx(w.t)
    assert back.script == w.script
    assert back.vessels["pot"].T == pytest.approx(w.vessels["pot"].T)

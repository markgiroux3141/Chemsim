"""G1 -- the dropping funnel, and the one thing about it that was missing.

⚠⚠ **THE PLUMBING WAS NOT THE GAP, AND THE BRIEF SAID IT WAS.** G1 was scoped as
"add a feed term to ``VesselConditions``, plus a ``feed_T``, plus a ``SET_FEED``
event". Measured against the engine first, all four halves of that already
existed as the rig's ``meter`` edge:

  * it delivers its set rate (``test_rig`` has pinned that since Layer 5);
  * it carries the donor's SENSIBLE HEAT -- a funnel at 270 K leaves the pot at
    298.13 K where one at 370 K leaves it at 364.12 K, same moles either way;
  * its reservoir RUNS OUT, and exactly: at rates from 0.001 to 10 mol/s the
    funnel lands on 0.0 and the pair conserves 0.5 mol to 1e-12;
  * and ``SET_EDGE`` already opens and shuts it inside a saveable scenario.

⚠ A ``feed`` vector would have been a second home for all of that, with a
``feed_T`` that is a DECLARED CONSTANT where a funnel vessel's temperature is a
solved one you can put in an ice bath. The measurements are in
``validation/dropwise.py`` and the refusal is argued in MILESTONES §G1.

**What was genuinely missing is one layer up, and it is the same gap
``collect_fraction`` was built to close**: a dropwise addition that STOPS ON A
CONDITION could not be written as a recipe. ``wait_until`` then
``now(SET_EDGE)`` bakes this run's discovered instant into the script, and the
tests below measure both halves of what that costs.
"""

from __future__ import annotations

import pytest

from chemsim.engine import SAVE_VERSION, EdgeSpec, Scenario, VesselSpec, World
from chemsim.engine.events import SET_EDGE
from chemsim.engine.scenario import TemplateSpec
from chemsim.matter import Molecule
from chemsim.reactions.synthesis import aromatic_nitration
from chemsim.vessel import Condition, consumed, reaches


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


BENZENE, NITRIC, WATER = c("c1ccccc1"), c("O[N+](=O)[O-]"), c("O")
NITROBENZENE = c("O=[N+]([O-])c1ccccc1")


def _scenario(funnel_volume: float = 2.0) -> Scenario:
    """A cooled pot, a cold funnel over it, and a tap between them.

    The nitration is here because it is the only exotherm in reach that is big
    enough for a drip rate to matter: -141 kJ/mol for the first substitution,
    against an esterification's -3.2. See ``validation/dropwise.py``.
    """
    return Scenario(
        feed_species=[BENZENE, NITRIC, WATER],
        templates=[TemplateSpec.of(aromatic_nitration())],
        max_species=60,
        vessels={
            "funnel": VesselSpec(volume=funnel_volume, T=280.0, T_env=280.0,
                                 UA=1.0e6, kla=0.0, k_vent=0.0, k_diss=0.0,
                                 lle=False, heat_capacity=200.0),
            "pot": VesselSpec(volume=2.0, T=280.0, T_env=280.0, UA=5.0,
                              kla=1.0, k_vent=0.0, k_diss=0.0, lle=False,
                              heat_capacity=50.0),
        },
        edges=[EdgeSpec(kind="meter", a="funnel", b="pot", k=0.0)],
    )


def _charged(scale: float = 1.0, acid: float = 1.0,
             funnel_volume: float = 2.0) -> World:
    w = World(_scenario(funnel_volume))
    w.vessels["funnel"].charge({NITRIC: acid * scale, WATER: 0.1 * scale})
    w.vessels["pot"].charge({BENZENE: 1.0 * scale})
    return w


# ---------------------------------------------------------------------------
# the gap, stated as the two tests that measure it
# ---------------------------------------------------------------------------


def test_stopping_a_drip_with_an_event_bakes_this_runs_instant_into_the_recipe():
    """⚠⚠ THE BRIEF SAID THIS COMPOSES "FOR FREE" AND IT DOES NOT.

    G1's plan read: *it composes with ``wait_until`` for free -- "drip until the
    pot reaches 340 K, then stop" needs no new machinery.* Measured, it needs
    exactly the machinery ``collect_fraction`` needed, and for the same reason:
    an ``Event`` carries an absolute ``t``.

    The recipe below is written the free way. It replays at the scale it was
    recorded at and REFUSES at twice that scale, because a bigger charge takes
    longer to reach 340 K and the recorded timestamp is then in the past.

    ⚠ The refusal is the GOOD case. A crossing that landed a hair earlier would
    leave the event in the future and the tap would shut at an instant this run
    never found -- silently. See ``World.add_dropwise``.
    """
    w = _charged()
    w.now(SET_EDGE, edge=0, k=0.02)
    w.step(1.0)
    w.wait_until("pot", reaches(340.0), timeout=200.0)
    w.now(SET_EDGE, edge=0, k=0.0)          # <- the discovered instant, recorded
    w.step(10.0)
    script = w.save()["script"]

    stamped = [e for e in script
               if e["do"] == "schedule" and e["event"]["kind"] == SET_EDGE]
    assert len(stamped) == 2
    closing = stamped[-1]["event"]["t"]
    assert closing > 0.0, "the tap-close carries this run's own crossing time"

    same = _charged()
    same.run_script(script)                  # same scale: it happens to line up

    with pytest.raises(ValueError, match="already at t="):
        _charged(scale=2.0).run_script(script)


def test_add_dropwise_stores_the_condition_so_the_recipe_survives_a_rescale():
    """The same protocol, said as a verb -- and now the 2x replay runs.

    ⚠ It does not reproduce the 1x run's numbers at 2x, and it must not: the
    point of storing a condition is that the recipe MEANS the same thing at a
    different scale, which is a different trajectory. What is pinned here is
    that it runs at all, and that the tap shut at a crossing THIS run found.
    """
    w = _charged()
    out = w.add_dropwise(edge=0, rate=0.02, watch="pot",
                         until=reaches(340.0), timeout=200.0)
    w.step(10.0)
    assert not out["timed_out"]
    assert out["fired"] == Condition("temperature_above", 340.0)
    script = w.save()["script"]
    assert [e["do"] for e in script] == ["add_dropwise", "step"]
    assert "t" not in script[0], "a recipe may not carry a discovered instant"

    big = _charged(scale=2.0)
    big.run_script(script)                    # the case that refused above
    assert big.t > w.t, "twice the charge takes longer to reach 340 K"
    assert big.vessels["pot"].T > 300.0

    # and the tap is shut in both, at the end
    assert w.rig.connections[0].k == 0.0
    assert big.rig.connections[0].k == 0.0


def test_a_dropwise_recipe_replays_exactly_at_the_scale_it_was_written_at():
    """The determinism guarantee ``script`` rests on, for the new verb.

    ⚠ EXACT rather than close, because nothing here is scale-dependent: the
    replay re-solves the same root on the same trajectory. A discovered instant
    may legitimately move by about the root solve's tolerance across a rescale
    or a tolerance change -- not across a re-run of the same recipe.
    """
    w = _charged()
    w.add_dropwise(0, 0.02, "pot", reaches(340.0), 200.0)
    w.step(20.0)
    script = w.save()["script"]

    again = _charged()
    again.run_script(script)
    assert again.t == pytest.approx(w.t, abs=1.0e-12)
    assert again.vessels["pot"].T == pytest.approx(w.vessels["pot"].T, abs=1e-12)
    for vid in ("funnel", "pot"):
        for s in (BENZENE, NITRIC, NITROBENZENE, WATER):
            assert again.vessels[vid].state().total(s) == pytest.approx(
                w.vessels[vid].state().total(s), abs=1.0e-12
            ), f"{vid} {s}"


# ---------------------------------------------------------------------------
# what the verb reports, and the thing the first draft of it got wrong
# ---------------------------------------------------------------------------


def test_a_funnel_that_empties_early_is_reported_rather_than_hidden():
    """A dropping funnel running out before the condition fires is an ordinary
    bench event, so it is a RESULT and not an error.

    ⚠⚠ AND ``ran_dry`` IS READ OFF WHAT IS LEFT IN THE FUNNEL, NOT OFF A
    SHORTFALL IN THE DELIVERY. The obvious test -- ``delivered < rate*elapsed``
    -- does not survive a real funnel: measured on a funnel with a LIVE
    HEADSPACE (``kla = 1.0``) the donor's liquid inventory falls FASTER than the
    tap takes it, so ``delivered`` came out 0.40799 mol against a nominal
    0.40702. Two numbers that each carry their own error term cannot be
    subtracted to decide a third thing.

    ⚠ The funnel in THIS test is sealed (``kla = 0``), where the two figures do
    agree -- which is the point: the bad test would have passed here.
    """
    w = _charged(acid=0.05, funnel_volume=0.2)
    out = w.add_dropwise(0, 0.02, "pot", reaches(340.0), timeout=200.0)

    assert out["ran_dry"], "0.05 mol at 0.02 mol/s is gone in 2.5 s"
    assert out["timed_out"], "and the pot therefore never reaches 340 K"
    assert out["donor_left"] == pytest.approx(0.0, abs=1.0e-9)
    assert out["delivered"] < out["nominal"]
    assert w.vessels["pot"].T < 300.0

    # the other side of the same flag: enough acid, condition fires, funnel full
    ok = _charged(funnel_volume=0.2).add_dropwise(
        0, 0.02, "pot", reaches(340.0), timeout=200.0
    )
    assert not ok["ran_dry"] and not ok["timed_out"]
    assert ok["donor_left"] > 0.5


def test_the_funnel_itself_can_be_what_is_watched():
    """"Add all of it" is a CONDITION on the funnel, not a duration.

    The brief proposed deriving the addition time as ``total / rate``. That is
    the same category error as recording a discovered instant: it is derived
    data, and it stops being true the moment the funnel holds something else.
    ``consumed`` on the donor says what was meant, and the root finds the time.

    ⚠⚠ AND THIS TEST IS THE PROOF THAT ``total / rate`` IS WRONG, BECAUSE IT
    CAUGHT THE AUTHOR OF IT. The funnel holds 0.2 mol of nitric acid and the tap
    is set to 0.01 mol/s, so ``total / rate`` says 20 s. It is **30 s**: a meter
    edge moves the donor's SOLUTION at that rate, not the reagent, and this
    funnel is 0.2 mol of acid in 0.1 mol of water. The acid therefore leaves at
    ``0.01 * 2/3`` mol/s. A derived duration would have shut the tap with a
    third of the charge still in the funnel and reported success.
    """
    w = _charged(acid=0.2, funnel_volume=0.2)
    out = w.add_dropwise(0, 0.01, "funnel",
                         until=consumed(NITRIC, 1.0e-4), timeout=200.0)
    assert not out["timed_out"]
    assert out["elapsed"] == pytest.approx(30.0, rel=0.02), (
        "0.2 mol of acid in 0.3 mol of solution, drained at 0.01 mol/s"
    )
    assert out["elapsed"] > 25.0, "and NOT the 20 s that total/rate predicts"
    assert w.vessels["funnel"].state().total(NITRIC) < 1.0e-4


def test_leaving_the_tap_open_is_sayable_so_a_staged_addition_is_too():
    """``close=False`` is how "drip fast until it warms, then drip slowly" is
    written -- two additions, one continuous stream, no gap in between."""
    w = _charged()
    first = w.add_dropwise(0, 0.05, "pot", reaches(320.0), 200.0, close=False)
    assert not first["timed_out"]
    assert w.rig.connections[0].k == 0.05, "the tap is still running"
    second = w.add_dropwise(0, 0.005, "pot", reaches(340.0), 400.0)
    assert w.rig.connections[0].k == 0.0
    assert second["was"] == 0.05, "and it reports what it took over from"


# ---------------------------------------------------------------------------
# refusals
# ---------------------------------------------------------------------------


def test_a_dropwise_addition_refuses_an_edge_that_is_not_a_meter():
    """⚠ A CONSTANT'S UNITS ARE WHAT MAKE ITS VALUE DEFENSIBLE. A meter's k is
    mol/s, a drain's is a reciprocal residence time and a vapour edge's is
    mol/(bar s). Opening any of the others "at 0.01 mol/s" would be a number in
    the wrong units wearing the right name -- and ``SET_EDGE`` cannot catch it,
    because setting a conductance is exactly what SET_EDGE is for."""
    w = World(Scenario(
        feed_species=[WATER], templates=[],
        vessels={"a": VesselSpec(volume=1.0), "b": VesselSpec(volume=1.0)},
        edges=[EdgeSpec("drain", "a", "b", k=1.0),
               EdgeSpec("meter", "a", "b", k=0.0)],
    ))
    with pytest.raises(ValueError, match="needs a METER edge"):
        w.add_dropwise(0, 0.01, "a", reaches(300.0), 10.0)
    w.add_dropwise(1, 0.01, "a", reaches(300.0), 1.0)      # the meter is fine


def test_a_dropwise_addition_refuses_the_ways_of_asking_that_cannot_mean_anything():
    w = _charged()
    with pytest.raises(ValueError, match="positive rate"):
        w.add_dropwise(0, 0.0, "pot", reaches(340.0), 10.0)
    with pytest.raises(ValueError, match="timeout must be positive"):
        w.add_dropwise(0, 0.01, "pot", reaches(340.0), 0.0)
    with pytest.raises(ValueError, match="at least one condition"):
        w.add_dropwise(0, 0.01, "pot", [], 10.0)
    with pytest.raises(KeyError):
        w.add_dropwise(0, 0.01, "nowhere", reaches(340.0), 10.0)
    with pytest.raises(IndexError):
        w.add_dropwise(7, 0.01, "pot", reaches(340.0), 10.0)

    bench = World(Scenario(feed_species=[WATER], templates=[],
                           vessels={"flask": VesselSpec(volume=1.0)}))
    with pytest.raises(ValueError, match="no apparatus"):
        bench.add_dropwise(0, 0.01, "flask", reaches(300.0), 10.0)


def test_the_save_format_moved_because_an_unknown_verb_fails_too_late():
    """⚠ A version-5 reader handed this script executes every entry BEFORE the
    unknown one and only then raises, leaving a half-run world that looks like a
    finished one. That is the failure a version number exists to prevent, and it
    is why a new VERB bumps the format the way a new FIELD does."""
    assert SAVE_VERSION == 6
    w = _charged()
    w.add_dropwise(0, 0.02, "pot", reaches(340.0), 200.0)
    blob = w.save()
    assert blob["version"] == 6
    for older in (4, 5):
        with pytest.raises(ValueError, match="version"):
            World.load(dict(blob, version=older))
        with pytest.raises(ValueError, match="version"):
            World.replay(dict(blob, version=older))

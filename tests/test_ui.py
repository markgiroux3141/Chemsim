"""Layer 7 -- the session, which is the half of a frontend that can be wrong.

⚠ NONE OF THIS OPENS A WINDOW, and that is the point of the split. What is hard
about a user interface for this engine is not the layout: it is that cost is
concentrated in stiff transients, so an operation has to render as IN PROGRESS
rather than block, which means a worker thread, chunking, and a cancel that
arrives at a chunk boundary. Every one of those is testable and none of them is
testable through Tk.
"""

from __future__ import annotations

import threading
import time

import pytest

from chemsim.engine.scenario import Scenario, TemplateSpec, VesselSpec
from chemsim.ui.examples import catalogue, load, titles
from chemsim.ui.session import Load, Reset, Session
from chemsim.vessel import conditions as cond

WATER, ETOH, N2, O2 = "O", "CCO", "N#N", "O=O"


def tiny() -> Scenario:
    """One flask, four species, no templates -- the cheapest real world there is."""
    return Scenario(
        feed_species=[WATER, ETOH, N2, O2],
        vessels={"flask": VesselSpec(volume=1.0, T=298.15, T_env=298.15,
                                     UA=2.0, kla=5.0, Q_input=200.0)},
        max_species=20,
    )


@pytest.fixture
def session():
    s = Session(tiny())
    yield s
    s.close()


def drive(s: Session, timeout: float = 300.0) -> None:
    assert s.wait_idle(timeout), "the worker never went idle"
    assert not s.snapshot().error, s.snapshot().error


# -- the contract a view relies on ------------------------------------------


def test_submitting_does_not_block_the_caller(session):
    """The whole reason this layer exists.

    Ten minutes of simulated boiling is submitted and the caller is back
    immediately -- if it were not, a window would freeze exactly when the
    chemistry got interesting.
    """
    session.do("charge", "flask", amounts={ETOH: 4.0, WATER: 4.0})
    started = time.perf_counter()
    session.step(600.0, chunk=30.0)
    assert time.perf_counter() - started < 0.05
    drive(session)
    assert session.snapshot().t == pytest.approx(600.0)


def test_the_snapshot_advances_while_an_operation_runs(session):
    """A thermometer has to climb rather than teleport."""
    session.do("charge", "flask", amounts={ETOH: 4.0, WATER: 4.0})
    session.wait_idle(60.0)
    session.step(300.0, chunk=20.0)
    seen = set()
    deadline = time.perf_counter() + 120.0
    while time.perf_counter() < deadline:
        snap = session.snapshot()
        seen.add(round(snap.t, 6))
        if not snap.busy and snap.t >= 300.0:
            break
        time.sleep(0.01)
    drive(session)
    # More than the two endpoints, i.e. the view genuinely had something to draw.
    assert len(seen) > 3, seen


def test_an_operation_reports_itself_in_progress(session):
    session.do("charge", "flask", amounts={ETOH: 4.0, WATER: 4.0})
    session.wait_idle(60.0)
    session.step(600.0, chunk=15.0)
    deadline = time.perf_counter() + 30.0
    activity = ""
    while time.perf_counter() < deadline and not activity:
        snap = session.snapshot()
        if snap.busy:
            activity = snap.activity
        time.sleep(0.005)
    assert "step" in activity, activity
    drive(session)
    assert session.snapshot().busy is False


def test_the_cost_meter_is_wall_over_simulated(session):
    """The measurement the brief says must shape the first screen.

    Cost has nothing to do with elapsed simulated time, so a frontend has to be
    able to show what an operation actually cost rather than how long it
    represented.
    """
    session.do("charge", "flask", amounts={ETOH: 4.0, WATER: 4.0})
    session.step(120.0, chunk=40.0)
    drive(session)
    snap = session.snapshot()
    assert snap.sim == pytest.approx(120.0)
    assert snap.wall > 0.0
    assert snap.cost_ratio == pytest.approx(snap.wall / snap.sim)


# -- chunking, which changes the recipe and therefore has to record itself ---


def test_chunking_records_itself_in_the_script(session):
    """⚠ A chunk boundary is an integration boundary, so it is part of the recipe.

    Freezing the layer permittivity made the caller's dt weakly load-bearing,
    which is why ``World.script`` records stepped intervals at all. A view that
    chunked for smoothness and did not record it would be making a silent
    approximation -- so the script has to show the chunks that were run.
    """
    session.do("charge", "flask", amounts={ETOH: 4.0, WATER: 4.0})
    session.step(100.0, chunk=30.0)
    drive(session)
    steps = [e for e in session.world.script if e["do"] == "step"]
    assert [e["dt"] for e in steps] == pytest.approx([30.0, 30.0, 40.0])
    assert sum(e["dt"] for e in steps) == pytest.approx(100.0)


def test_the_remainder_joins_the_last_chunk_rather_than_trailing(session):
    """No nanosecond stub steps: every boundary re-takes the phase decision."""
    session.do("charge", "flask", amounts={WATER: 4.0})
    session.step(61.0, chunk=30.0)
    drive(session)
    dts = [e["dt"] for e in session.world.script if e["do"] == "step"]
    assert min(dts) > 1.0, dts
    assert sum(dts) == pytest.approx(61.0)


def test_a_chunked_run_replays_to_the_same_place(session):
    """A run is a pure function of (scenario, script), chunks and all."""
    session.do("charge", "flask", amounts={ETOH: 4.0, WATER: 4.0})
    session.step(120.0, chunk=25.0)
    drive(session)
    was = session.snapshot().vessel("flask")
    script = tuple(session.world.script)

    session.submit(Load(tiny(), script, "replay"))
    drive(session)
    now = session.snapshot().vessel("flask")
    assert now.T == pytest.approx(was.T, abs=1e-9)
    assert now.liquid[ETOH] == pytest.approx(was.liquid[ETOH], rel=1e-9)


# -- waiting -----------------------------------------------------------------


def test_a_chopped_wait_still_finds_the_crossing(session):
    """⚠ Each chunk is a real ``wait_until``, so the instant is a scipy ROOT.

    That is the difference between chopping a wait and polling one: the answer is
    the crossing itself, located inside whichever chunk straddles it, not the end
    of that chunk. Measured against a single unchopped wait.
    """
    session.do("charge", "flask", amounts={ETOH: 4.0, WATER: 4.0})
    session.wait_until("flask", cond.reaches(340.0), 3600.0, chunk=1.0e9)
    drive(session)
    whole = session.snapshot()
    assert whole.vessel("flask").T == pytest.approx(340.0, abs=1e-3)

    session.submit(Reset())
    session.do("charge", "flask", amounts={ETOH: 4.0, WATER: 4.0})
    session.wait_until("flask", cond.reaches(340.0), 3600.0, chunk=50.0)
    drive(session)
    chopped = session.snapshot()
    assert chopped.vessel("flask").T == pytest.approx(340.0, abs=1e-3)
    # Not merely both-near-340: the discovered INSTANT has to agree too.
    assert chopped.t == pytest.approx(whole.t, rel=1e-3)


def test_a_wait_that_never_fires_times_out_and_says_so(session):
    session.do("charge", "flask", amounts={WATER: 1.0})
    session.wait_until("flask", cond.reaches(4000.0), 20.0, chunk=10.0)
    drive(session)
    assert "TIMED OUT" in session.snapshot().outcome


def test_a_condition_already_true_returns_at_once(session):
    session.do("charge", "flask", amounts={WATER: 1.0})
    session.wait_until("flask", cond.reaches(250.0), 3600.0)
    drive(session)
    snap = session.snapshot()
    assert snap.t == pytest.approx(0.0)
    assert "already" in snap.outcome


# -- what the engine said while building --------------------------------------


def noisy() -> Scenario:
    """One flask and one template that cannot possibly have the barrier it
    declares, so ``build_network`` has something to say about it.

    The ester hydrolysis below is endothermic by more than its declared Ea, which
    detailed balance refuses -- a barrier under the reaction enthalpy makes the
    REVERSE barrier negative. The builder raises it and says so. That notice is a
    real one, it fires deterministically, and before P1 the only place it went
    was stdout.
    """
    return Scenario(
        feed_species=["CCOC(C)=O", WATER],
        templates=[TemplateSpec(
            name="impossible_hydrolysis",
            smarts="[CX3:1](=[O:2])[OX2:3][CX4:4].[OX2H2:5]"
                   ">>[CX3:1](=[O:2])[OX2H1:5].[O:3][C:4]",
            A=1.0e6, Ea=1_000.0, reversible=True,
        )],
        vessels={"flask": VesselSpec(volume=1.0, T=298.15, T_env=298.15)},
        max_species=20,
    )


def test_the_builder_s_notices_reach_the_snapshot(capsys):
    """⚠ STDOUT IS NOT A PLACE A PLAYER LOOKS, AND A WINDOWED APPLICATION DOES
    NOT HAVE ONE.

    The engine's rule is that nothing is silently approximated, and the reports
    panel exists because that rule is worth nothing if nobody is shown what it
    said -- ``app.py``'s own docstring records the refluxing rig destroying
    0.34 mol of its air on a channel that was reported all along and that nothing
    read. ``build_network`` was on exactly such a channel: a mix-anything game
    generates hundreds of these notices per step, 397 for five reagents two
    generations deep, into a console nobody is watching.

    ⚠ CARRIED, NOT MOVED. The print stays -- a harness and a validation script
    both read it -- so this asserts the two channels say the SAME thing.
    """
    with Session(noisy()) as s:
        printed = capsys.readouterr().out
        snap = s.snapshot()
        assert snap.notices, "the clamp notice fired and nothing carried it"
        assert any("raised to" in n for n in snap.notices)
        assert all(n in printed for n in snap.notices)
        assert snap.notices == tuple(s.world.network.notices)


def test_a_quiet_network_carries_no_notices(session):
    """Empty is a positive statement here. ``tiny()`` has no templates at all, so
    nothing was clamped, dropped or left unexpanded, and the panel's fallback
    text -- "nothing to report" -- has to be true when it is shown."""
    assert session.snapshot().notices == ()
    assert session.snapshot().unexpanded == ()


# -- refusing ----------------------------------------------------------------


def test_a_refusal_is_carried_verbatim_rather_than_reduced(session):
    """The engine's messages name a cause and a fix; that is the product.

    ⚠ And the worker must SURVIVE one. A frontend whose engine thread dies on the
    first mistake is worse than one that never had a thread.
    """
    session.do("charge", "flask", amounts={WATER: 500.0})     # ~9 L into 1 L
    session.step(10.0)
    assert session.wait_idle(120.0)
    error = session.snapshot().error
    assert "condensed phases occupy" in error, error
    assert "L in a vessel of" in error

    session.submit(Reset())
    session.do("charge", "flask", amounts={WATER: 1.0})
    session.step(10.0)
    drive(session)
    assert session.snapshot().t == pytest.approx(10.0)


def test_an_unknown_event_kind_is_refused_before_it_is_queued(session):
    with pytest.raises(ValueError, match="unknown event kind"):
        session.do("explode", "flask")


# -- cancelling --------------------------------------------------------------


def test_stop_ends_the_operation_at_a_chunk_boundary(session):
    """⚠ At a boundary, not immediately, because a scipy solve cannot be
    interrupted from outside. What is asserted is that it stops EARLY and that
    the clock reflects what actually ran -- not that it stops instantly."""
    session.do("charge", "flask", amounts={ETOH: 4.0, WATER: 4.0})
    session.wait_idle(60.0)
    session.step(100_000.0, chunk=5.0)
    while not session.snapshot().busy:
        time.sleep(0.005)
    time.sleep(0.2)
    session.stop()
    assert session.wait_idle(180.0)
    snap = session.snapshot()
    assert 0.0 < snap.t < 100_000.0
    assert snap.t == pytest.approx(sum(
        e["dt"] for e in session.world.script if e["do"] == "step"))


# -- the engine is only ever touched by one thread ---------------------------


def test_commands_run_in_submission_order_from_any_thread(session):
    """"charge then step" and "step then charge" are different experiments, so
    ordering is a guarantee rather than a convenience."""
    def add(species, mol):
        session.do("charge", "flask", amounts={species: mol})

    threads = [threading.Thread(target=add, args=(WATER, 1.0)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    drive(session)
    assert session.snapshot().vessel("flask").liquid[WATER] == pytest.approx(8.0)


def test_a_view_never_sees_a_half_applied_state(session):
    """The snapshot is immutable and published by one assignment, so a reader
    cannot catch the world mid-event."""
    session.do("charge", "flask", amounts={WATER: 10.0})
    session.step(60.0, chunk=20.0)
    seen = []
    while len(seen) < 50 and (session.snapshot().busy or not seen):
        snap = session.snapshot()
        view = snap.vessel("flask")
        if view is not None:
            seen.append((snap.t, view.t))
    drive(session)
    # Every pair came off one object, so the world clock and the vessel clock
    # can never disagree.
    for world_t, vessel_t in seen:
        assert world_t == pytest.approx(vessel_t, abs=1e-9)


# -- the examples a frontend offers ------------------------------------------


def test_every_example_builds_and_opens():
    for example in catalogue():
        assert example.scenario.vessels
        assert example.blurb
        with Session(example.scenario) as s:
            s.submit(Load(example.scenario, example.opening, example.title))
            assert s.wait_idle(300.0)
            assert not s.snapshot().error, (example.key, s.snapshot().error)
            assert s.snapshot().vessels


def test_the_example_titles_match_what_is_built():
    assert [(e.key, e.title) for e in catalogue()] == titles()


def test_the_prep_example_carries_the_recipe_s_own_numbers():
    """⚠ ONE HOME FOR A RECIPE. The example a frontend loads must be the prep the
    harness measured, including the two counter-intuitive constants: ``k_lle =
    0.5`` or the two-phase pot does not integrate, and ``k_diss = 0.05``, which a
    ``VesselSpec`` could not express at all until this session."""
    from chemsim.recipes import BENZOIC_ACID_PREP as prep

    pot = load("prep").scenario.vessels["pot"]
    assert pot.k_lle == prep.k_lle
    assert pot.k_diss == prep.k_diss
    assert pot.volume == pytest.approx(prep.pot_volume * prep.scale)
    assert pot.T == pytest.approx(prep.cook_T)
    assert pot.k_vent == 0.0
    assert pot.drain_time == prep.drain_time
    assert pot.crystal_size == prep.crystal_size


def test_a_do_command_is_ordered_against_driving_calls(session):
    """Charging mid-run has to land where it was asked for, not at the end."""
    session.do("charge", "flask", amounts={WATER: 4.0})
    session.step(30.0, chunk=30.0)
    session.do("charge", "flask", amounts={ETOH: 1.0})
    session.step(30.0, chunk=30.0)
    drive(session)
    kinds = [
        e["event"]["kind"] if e["do"] == "schedule" else e["do"]
        for e in session.world.script
    ]
    assert kinds == ["charge", "step", "charge", "step"]

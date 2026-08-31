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


# -- the shelf: the two verbs, from the view's side ---------------------------


def test_a_bottle_reaches_the_view_without_the_view_touching_the_engine(session):
    """P2. The whole loop through Layer 7: charge, bottle, read the shelf off a
    ``Snapshot``, charge that stock back into the flask.

    ⚠ ``Snapshot.shelf`` carries ``Stock`` objects and that is safe for the same
    reason everything else on a snapshot is: a ``Stock`` is frozen and copies its
    mole dicts on construction, so nothing on it aliases a live vessel. The view
    gets no return value from ``bottle`` -- it reads the next snapshot, which is
    the only channel there is.
    """
    session.do("charge", "flask", amounts={WATER: 2.0, ETOH: 0.5})
    session.bottle("flask", "first crop")
    drive(session)

    shelf = session.snapshot().shelf
    assert [s.name for s in shelf] == ["first crop"]
    stock = shelf[0]
    assert stock.total == pytest.approx(2.5)
    assert stock.major("mass") == WATER
    assert 0.0 < stock.purity("mass") < 1.0
    # the flask is empty and its species are still known to the network
    view = session.snapshot().vessel("flask")
    assert sum(view.liquid.values()) == pytest.approx(0.0, abs=1e-12)

    session.charge_stock("flask", stock, 0.4)
    drive(session)
    view = session.snapshot().vessel("flask")
    assert sum(view.liquid.values()) == pytest.approx(1.0, rel=1e-9)


def test_the_recipe_records_a_bottling_and_a_pour_from_a_stock(session):
    """⚠ The recipe records the stock's COMPOSITION and not its label, because
    two bottles labelled the same are not the same bottle -- see
    ``events.CHARGE_STOCK``. The label rides along for a reader."""
    from chemsim.ui.app import _recipe_lines

    session.do("charge", "flask", amounts={WATER: 1.0})
    session.bottle("flask", "some water")
    drive(session)
    session.charge_stock("flask", session.snapshot().shelf[0], 0.5)
    drive(session)

    script = session.snapshot().script
    kinds = [e["event"]["kind"] for e in script if e["do"] == "schedule"]
    assert kinds == ["charge", "bottle", "charge_stock"]
    payload = script[-1]["event"]["payload"]
    assert payload["state"]["n_liquid"] == {WATER: pytest.approx(1.0)}
    assert payload["label"] == "some water"

    rendered = _recipe_lines(script)
    assert "bottle flask as some water" in rendered
    assert "0.5 of the stock some water into flask" in rendered


def test_one_generation_play_reaches_the_snapshot(fischer_template):
    """⚠⚠ WHAT P1 HANDED TO P2, CLOSED. ``Snapshot.unexpanded`` was correct and
    permanently empty because ``World`` passed no ``generations`` to
    ``build_network``, so nothing could ask for one-generation play through the
    UI at all -- and the "react further" control P4 builds had no state to offer.

    With the bound set, the frontier the builder declined to expand arrives on
    the snapshot as data, which is what the reports panel puts in its heading.
    """
    from chemsim.engine.scenario import TemplateSpec

    scenario = Scenario(
        feed_species=[WATER, ETOH, "CC(=O)O"],
        templates=[TemplateSpec.of(fischer_template)],
        vessels={"flask": VesselSpec(volume=1.0)},
        max_species=12,
        generations=1,
    )
    with Session(scenario) as s:
        drive(s)
        snap = s.snapshot()
        assert snap.unexpanded, "one generation must leave a frontier"
        assert any("generation" in n for n in snap.notices)


# ---------------------------------------------------------------------------
# P4 -- the bench, and the control that raises the bound
# ---------------------------------------------------------------------------


def test_the_bench_is_built_from_shelf_rows_and_carries_every_species():
    """⚠ P2's handoff: the SELECTION IS THE SCENARIO.

    ``Vessel.charge_state`` refuses a species the network does not carry and a
    network is derived from its feed, so picking shelf rows is not filling a
    list -- and the opening script has to charge each row into its DECLARED
    phase, because the shelf declares that rather than deriving it.
    """
    from chemsim.engine import inventory as inv
    from chemsim.ui.examples import bench

    items = [inv.find(i) for i in ("water", "sodium-chloride", "oxygen")]
    ex = bench(items, generations=1)
    assert ex.key == "bench"
    for item in items:
        for smiles in item.species:
            assert smiles in ex.scenario.feed_species
    assert ex.scenario.electrolyte, "rock salt charges ions"
    assert ex.scenario.generations == 1
    phases = {e["event"]["payload"]["phase"] for e in ex.opening}
    assert phases == {"liquid", "solid", "gas"}
    # every opening event is a charge into the one flask
    assert all(e["event"]["vessel"] == "flask" for e in ex.opening)


def test_a_refused_shelf_row_never_reaches_the_flask():
    """8.3 again, at the other end: greyed in the picker AND skipped here.

    A bench built from a selection containing gold has to come out without it
    rather than raising, because the picker is what tells the player why.
    """
    from chemsim.engine import inventory as inv
    from chemsim.ui.examples import bench

    gold = inv.find("gold")
    assert not gold.chargeable
    ex = bench([inv.find("water"), gold])
    assert ex.scenario.feed_species == ["O"]
    assert len(ex.opening) == 1


def test_the_bench_library_holds_the_templates_a_name_rule_missed():
    """⚠⚠ The bench claims *every template in the project*, and the first
    version of that claim was false by more than half.

    Collecting only ``*_chemistry`` bundles -- the rule
    ``validation/playable_levers.py`` uses -- silently skips every template
    exported as a function of its own. **Playing it is what found that**: sulfur,
    air and water off the shelf gave four species, no reactions and an empty
    frontier, which is the engine correctly reporting a library with no sulfur
    chemistry in it.
    """
    from chemsim.ui.examples import full_library

    names = {t.name for t in full_library()}
    for wanted in ("sulfur_combustion", "sulfur_trioxide_hydration",
                   "fischer_esterification", "cannizzaro_disproportionation"):
        assert wanted in names, f"{wanted} is missing from the bench library"
    assert len(names) >= 50


def test_the_burner_declares_first_order_in_oxygen_through_a_scenario():
    """⚠⚠⚠ THE PLAY FINDING, as the smallest thing that shows it.

    ``sulfur_combustion`` declares ``orders=(1, 1, 0...)``; ``TemplateSpec`` used
    to drop it, so a scenario-built network ran the SMARTS' ninth-body mass
    action and the shelf's own oxygen bottle could not light the shelf's own
    sulfur. The full measurement is ``validation/shelf.py`` panel 3.
    """
    from chemsim.engine.world import World
    from chemsim.ui.examples import bench
    from chemsim.engine import inventory as inv

    ex = bench([inv.find(i) for i in ("sulfur-s8", "oxygen", "nitrogen")],
               generations=1)
    world = World(ex.scenario)
    burners = [r for r in world.network.reactions
               if r.name.startswith("sulfur_combustion")]
    assert burners, "the burner template made no reaction"
    assert all(r.orders is not None for r in burners), (
        "the network's burner lost its declared rate law, so it is eighth order "
        "in oxygen and will not light at one atmosphere"
    )
    assert burners[0].orders[:2] == (1.0, 1.0)


def test_react_further_raises_the_bound_and_leaves_the_recipe_alone():
    """The control, as ``examples.rebuilt``: the BOUND moves, nothing else does."""
    from chemsim.engine import inventory as inv
    from chemsim.ui.examples import bench, rebuilt

    ex = bench([inv.find(i) for i in ("water", "glucose")], generations=1,
               max_species=400)
    deeper = rebuilt(ex, generations=2, max_species=700)
    assert deeper.scenario.generations == 2
    assert deeper.scenario.max_species == 700
    assert ex.scenario.generations == 1, "the original must not be mutated"
    assert deeper.scenario.feed_species == ex.scenario.feed_species
    assert deeper.opening == ex.opening
    assert len(deeper.scenario.templates) == len(ex.scenario.templates)


def test_one_more_generation_actually_finds_more_chemistry():
    """The bound is real: raise it and the network grows.

    ⚠ And the frontier is what says whether there is more to ask for. An empty
    one at a raised bound means the chemistry is exhausted rather than the budget
    -- which is what the control has to be able to tell a player apart.
    """
    from chemsim.engine.world import World
    from chemsim.ui.examples import bench, rebuilt
    from chemsim.engine import inventory as inv

    ex = bench([inv.find(i) for i in
                ("sulfur-s8", "oxygen", "nitrogen", "water", "nitrogen-dioxide")],
               generations=1)
    first = World(ex.scenario).network
    assert first.unexpanded, "one generation must leave a frontier here"
    second = World(rebuilt(ex, generations=2).scenario).network
    assert len(second.species) > len(first.species)
    assert "O=S(=O)(O)O" in second.species, (
        "the lead chamber makes sulfuric acid in the second generation; if it "
        "no longer does, the play in validation/shelf.py panel 4 is stale"
    )
    third = World(rebuilt(ex, generations=3).scenario).network
    assert not third.unexpanded, (
        "the third generation should exhaust this network, so the control can "
        "say 'the chemistry is finished' rather than 'the budget ran out'"
    )


def test_a_saved_recipe_carries_the_whole_scenario_not_only_its_key():
    """⚠ P4 had to fix the save format before either control could ship.

    The file used to be ``{"example": key, "script": [...]}``, which is enough
    only while every world is one of four hard-coded ones. A bench world is a
    shelf selection and has no key; a REACTED-FURTHER world differs from its
    key's scenario by exactly the bound that was raised. Both reloaded as
    something else, silently.
    """
    from chemsim.engine import inventory as inv
    from chemsim.engine.scenario import Scenario
    from chemsim.ui.examples import bench, rebuilt

    ex = rebuilt(bench([inv.find("water"), inv.find("sodium-chloride")],
                       generations=1), generations=3, max_species=650)
    blob = ex.scenario.to_dict()
    back = Scenario.from_dict(blob)
    assert back.generations == 3
    assert back.max_species == 650
    assert back.feed_species == ex.scenario.feed_species
    assert back.electrolyte == ex.scenario.electrolyte
    assert len(back.templates) == len(ex.scenario.templates)
    # and the fields P4 found missing survive it, template by template
    for before, after in zip(ex.scenario.templates, back.templates, strict=True):
        assert before == after

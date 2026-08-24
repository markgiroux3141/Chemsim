"""M2 -- the still as a PROTOCOL: an apparatus in the scenario, and a CUT.

The physics was never the gap. A pot, a vapour edge and a cold receiver have
been a working still since Layer 5. What could not be *said* was the one
operation that makes fractional distillation fractional: stop, and change the
receiver. So these tests are about vocabulary and determinism, not about
thermodynamics -- except for the one in the middle, which is about the
difference between a condition and the trajectory it is located on.
"""

from __future__ import annotations

import pytest

from chemsim.engine import SAVE_VERSION, EdgeSpec, Scenario, VesselSpec, World
from chemsim.matter import Molecule
from chemsim.vessel import Condition


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


ACETONE, ETHANOL, WATER = c("CC(C)=O"), c("CCO"), c("O")
AIR = ["N#N", "O=O"]
RECEIVERS = ("forerun", "heart")
DRAIN = 2


def _still(edges: bool = True) -> World:
    pot = VesselSpec(volume=1.0, T=298.15, T_env=298.15, UA=1.0,
                     Q_input=120.0, kla=5.0, k_vent=0.0, lle=False)
    head = VesselSpec(volume=0.10, T=298.15, T_env=298.15, UA=0.3, kla=5.0,
                      k_vent=0.0, heat_capacity=5.0, lle=False)
    cond = VesselSpec(volume=0.5, T=288.0, T_env=288.0, UA=40.0, kla=5.0,
                      k_vent=0.0, heat_capacity=20.0, lle=False)
    jar = VesselSpec(volume=0.5, T=288.0, T_env=288.0, UA=5.0, kla=5.0,
                     k_vent=10.0, lle=False)
    return World(Scenario(
        feed_species=[ACETONE, ETHANOL, WATER, *AIR],
        templates=[], max_species=30,
        vessels={"pot": pot, "head": head, "condenser": cond,
                 **{r: jar for r in RECEIVERS}},
        edges=[
            EdgeSpec("vapour", "pot", "head", k=20.0),
            EdgeSpec("vapour", "head", "condenser", k=20.0),
            EdgeSpec("drain", "condenser", "forerun", k=0.5),
        ] if edges else [],
    ))


def _charge(w: World) -> None:
    w.now("charge", "pot", amounts={ACETONE: 0.5, ETHANOL: 0.5, WATER: 0.5})
    for v in w.vessels:
        w.now("fill_headspace", v)
    w.flush()


def _held(w: World, vid: str) -> float:
    st = w.vessels[vid].state()
    return sum(st.n_liquid.values()) + sum(st.n_liquid2.values())


# ---------------------------------------------------------------------------
# the apparatus is DATA
# ---------------------------------------------------------------------------
def test_the_apparatus_survives_a_save_because_it_is_part_of_the_scenario():
    """⚠ THIS IS WHAT MADE A STILL UNSAYABLE, and it was plumbing rather than
    science. ``Rig`` has had vapour, drain, thermal and metered edges since
    Layer 5 -- but only in Python. ``World``, the layer that can be saved,
    scripted and replayed, had no rig at all, so every coupled apparatus in this
    repo was assembled by hand in an example and could not be saved."""
    w = _still()
    blob = w.save()
    assert blob["version"] == SAVE_VERSION == 5
    assert [e["kind"] for e in blob["scenario"]["edges"]] == [
        "vapour", "vapour", "drain"
    ]
    back = World.load(blob)
    assert back.rig is not None
    assert [con.describe() for con in back.rig.connections] == [
        con.describe() for con in w.rig.connections
    ]


def test_a_world_with_NO_edges_keeps_the_uncoupled_path_exactly():
    """⚠ NONE IS A REAL STATE, NOT A DEGENERATE ONE -- the same guarantee
    ``lle=False`` and ``losses=None`` carry.

    A rig integrates every vessel as ONE stiff system. That is the right answer
    for connected glassware and a needless expense for a bench of separate
    flasks, so edges are the SIGNAL that they are connected. Without them the
    world keeps its original per-vessel stepping, which is what makes every
    number measured before rigs existed still reachable."""
    w = _still(edges=False)
    assert w.rig is None
    _charge(w)
    w.step(50.0)
    assert w.vessels["pot"].T > 298.15         # it heated
    assert _held(w, "forerun") == 0.0          # ...and nothing could travel

    # and the apparatus verbs REFUSE rather than silently doing nothing
    with pytest.raises(ValueError, match="no apparatus"):
        w.now("swap_receiver", edge=0, to="heart")
        w.flush()
    with pytest.raises(ValueError, match="collect_fraction needs an apparatus"):
        w.collect_fraction("head", 0, "heart", 300.0, 350.0, 10.0)


# ---------------------------------------------------------------------------
# the verb
# ---------------------------------------------------------------------------
def test_swap_receiver_repoints_an_edge_and_refuses_the_nonsense():
    w = _still()
    assert w.rig.connections[DRAIN].b == "forerun"
    w.now("swap_receiver", edge=DRAIN, to="heart")
    w.flush()
    assert w.rig.connections[DRAIN].b == "heart"
    assert any("swap_receiver" in line for line in w.transfer_log)

    with pytest.raises(KeyError, match="no such vessel"):
        w.now("swap_receiver", edge=DRAIN, to="beaker")
        w.flush()
    with pytest.raises(IndexError, match="edge 9 does not exist"):
        w.now("swap_receiver", edge=9, to="heart")
        w.flush()
    # the drain runs condenser -> heart, so swapping its SOURCE to heart too
    # would connect a vessel to itself
    with pytest.raises(ValueError, match="itself"):
        w.now("swap_receiver", edge=DRAIN, to="heart", end="a")
        w.flush()


def test_set_edge_opens_and_closes_a_tap():
    w = _still()
    w.now("set_edge", edge=DRAIN, k=0.0)
    w.flush()
    assert w.rig.connections[DRAIN].k == 0.0
    with pytest.raises(ValueError, match="non-negative"):
        w.now("set_edge", edge=DRAIN, k=-1.0)
        w.flush()


# ---------------------------------------------------------------------------
# ⚠ the one that is about physics: WHERE the root is located
# ---------------------------------------------------------------------------
def test_a_condition_on_the_HEAD_is_located_on_the_COUPLED_trajectory():
    """⚠⚠ THE ENGINE CHANGE M2 ACTUALLY NEEDED, and the reason a cut could not
    simply reuse ``wait_until``.

    ``World`` used to satisfy a wait by integrating the OWNER vessel ALONE and
    then advancing the others by however long that took. For a bench of separate
    flasks that is exactly right. For glassware it is not: **nearly all of a
    still head's heat arrives through the vapour edge**, so a head integrated by
    itself just sits near its surroundings and never crosses the band at all --
    while the real, coupled head sails through it.

    Every cut in a fractional distillation is called off that number, so this is
    the difference between a protocol that works and one that silently collects
    everything in the first receiver. ``RigIntegrator.step_until`` lifts the
    condition onto the rig's own state vector; ``Rig.wait_until`` is the seam.
    """
    want = Condition("temperature_above", 330.0)

    # coupled: the pot boils, vapour reaches the head, the head crosses
    w = _still()
    _charge(w)
    got = w.wait_until("head", want, timeout=1500.0)
    assert not got.timed_out, "the coupled head never reached 330 K"
    assert w.vessels["head"].T == pytest.approx(330.0, abs=1.0)
    coupled_at = got.elapsed
    assert coupled_at > 0.0

    # the SAME head, alone, with the same charge in a pot it cannot see
    alone = _still(edges=False)
    _charge(alone)
    solo = alone.wait_until("head", want, timeout=coupled_at * 3.0)
    assert solo.timed_out, (
        "an UNCOUPLED head reached 330 K, which would mean this test no longer "
        "demonstrates anything -- the whole point is that its heat comes from "
        "the pot through the vapour edge"
    )
    assert alone.vessels["head"].T == pytest.approx(298.15, abs=1.0)


# ---------------------------------------------------------------------------
# the cut, and the trap
# ---------------------------------------------------------------------------
def test_a_cut_stores_the_CONDITION_and_never_the_INSTANT():
    """⚠⚠ A CUT IS A DISCOVERED INSTANT, so the recipe records the band.

    This is why ``collect_fraction`` is a scripted verb of its own rather than
    sugar over a scheduled SWAP_RECEIVER: an ``Event`` carries an absolute ``t``,
    so building the swap out of one would bake THIS run's crossing into the
    recipe. A replay whose root landed a picosecond elsewhere would then either
    refuse to schedule in the past or -- far worse -- swap at an instant it did
    not itself find. **A replayed distillation has to locate its own cut
    points**, which is the rule ``wait_until`` already followed and the reason
    SAVE_VERSION reached 4."""
    w = _still()
    _charge(w)
    out = w.collect_fraction("head", DRAIN, "heart", 330.0, 350.0, 1500.0,
                            park="forerun")
    assert out["entered"], out

    entries = [e for e in w.script if e.get("do") == "collect_fraction"]
    assert len(entries) == 1
    e = entries[0]
    assert (e["enter"], e["leave"], e["into"]) == (330.0, 350.0, "heart")
    # the whole point: no discovered time anywhere in it
    assert "t" not in e and "at" not in e
    assert all(not isinstance(v, float) or v in (330.0, 350.0, 1500.0)
               for v in e.values() if isinstance(v, float))

    # ...and no SWAP_RECEIVER was scheduled as a timed event either
    assert not any(
        s.get("do") == "schedule" and s["event"]["kind"] == "swap_receiver"
        for s in w.script
    )


def test_a_band_the_head_never_enters_is_a_RESULT_not_an_error():
    """A cut that never starts is an ordinary thing to ask for. The honest
    answer is "nothing came over", not an exception."""
    w = _still()
    _charge(w)
    out = w.collect_fraction("head", DRAIN, "heart", 900.0, 1000.0, 30.0)
    assert out == {"entered": False, "left": False, "into": "heart",
                   "wait": pytest.approx(30.0), "collected": 0.0}
    assert _held(w, "heart") == 0.0
    # the receiver was never swapped in, so the drain is where it started
    assert w.rig.connections[DRAIN].b == "forerun"


def test_a_band_must_rise_because_that_is_what_taking_a_cut_is():
    w = _still()
    with pytest.raises(ValueError, match="band must rise"):
        w.collect_fraction("head", DRAIN, "heart", 360.0, 330.0, 10.0)


def test_a_distillation_replays_from_its_script():
    """The determinism guarantee, on the verb that discovers its own timings."""
    w = _still()
    _charge(w)
    w.collect_fraction("head", DRAIN, "heart", 330.0, 355.0, 1500.0,
                       park="forerun")
    saved = w.save()

    back = World.replay(saved)
    for vid in ("pot", "head", "condenser", *RECEIVERS):
        assert _held(back, vid) == pytest.approx(_held(w, vid), abs=1e-9), vid
        assert back.vessels[vid].T == pytest.approx(w.vessels[vid].T, abs=1e-9)
    # and the apparatus came back pointing where the run left it
    assert back.rig.connections[DRAIN].b == w.rig.connections[DRAIN].b


# ---------------------------------------------------------------------------
# ⚠⚠ THE COLUMN, AND THE TWO THINGS BUILDING ONE FOUND
#
# M2's remaining task was a plate column reaching 0.85 mole fraction from a
# 50/50 ethanol/water charge, and the first attempt at one was recorded as
# having failed on column STARTUP. It had not. It had failed because the
# apparatus was SEALED, and the tests below pin both halves of that: what a
# still with no open end actually does, and that a plate enriches once it has
# one. ⚠ The 0.85 headline itself is measured by ``examples/plate_column.py``
# and not here -- eight plates is thirteen coupled vessels and about eight
# minutes of wall clock, which does not belong in a suite. What belongs here is
# the mechanism, at a plate count that is cheap.
# ---------------------------------------------------------------------------
def _column(plates: int, *, sealed: bool = False, takeoff: bool = False):
    """The same apparatus ``examples/plate_column.py`` builds, sized down."""
    pot = VesselSpec(volume=1.0, T=298.15, T_env=298.15, UA=1.0,
                     Q_input=250.0, kla=5.0, k_vent=0.0, lle=False)
    plate = VesselSpec(volume=0.10, T=298.15, T_env=298.15, UA=0.1, kla=5.0,
                       k_vent=0.0, heat_capacity=5.0, lle=False)
    head = VesselSpec(volume=0.10, T=298.15, T_env=298.15, UA=0.3, kla=5.0,
                      k_vent=0.0, heat_capacity=5.0, lle=False)
    cond = VesselSpec(volume=0.5, T=288.0, T_env=288.0, UA=40.0, kla=5.0,
                      k_vent=0.0 if sealed else 1.0, heat_capacity=20.0,
                      lle=False)
    jar = VesselSpec(volume=0.5, T=288.0, T_env=288.0, UA=5.0, kla=5.0,
                     k_vent=10.0, lle=False)
    names = [f"plate{i + 1}" for i in range(plates)]
    stack = ["pot", *names, "head", "condenser"]
    vessels = {"pot": pot, **{n: plate for n in names}, "head": head,
               "condenser": cond, "forerun": jar, "tail": jar}
    edges = [EdgeSpec("vapour", a, b, k=20.0) for a, b in zip(stack, stack[1:])]
    down = list(reversed(stack[:-1]))
    edges += [EdgeSpec("drain", a, b, k=0.5) for a, b in zip(down, down[1:])]
    edges.append(EdgeSpec("drain", "condenser", "head", k=0.5))
    if takeoff:
        edges.append(EdgeSpec("drain", "condenser", "forerun", k=0.0))
    w = World(Scenario(
        feed_species=[ETHANOL, WATER, *AIR], templates=[], max_species=20,
        vessels=vessels, edges=edges,
    ))
    w.now("charge", "pot", amounts={ETHANOL: 2.0, WATER: 2.0})
    for v in w.vessels:
        w.now("fill_headspace", v)
    w.flush()
    return w, stack


def _x_ethanol(w: World, vid: str) -> float:
    n = w.vessels[vid].state().n_liquid
    total = sum(n.values())
    return n.get(ETHANOL, 0.0) / total if total > 1.0e-12 else 0.0


def test_a_still_with_no_open_end_is_a_SEALED_PRESSURE_VESSEL():
    """⚠⚠ THE REAL REASON THE FIRST COLUMN ATTEMPT FAILED, and the published
    diagnosis (column startup) was wrong.

    Every vessel in a still is declared with ``k_vent=0`` -- the pot must not
    boil its charge out into the room -- and a receiver is reached only by a
    DRAIN, which moves liquid. So the gas phase of pot + plates + head +
    condenser has nowhere to go, and heating it is heating a bomb. That is why
    adding plates made the first column WORSE, and that is MEASURED rather than
    reasoned: eight plates seal 2.40 L against two plates' 1.80 L and settle at
    **3.770 bar / 389.6 K against 3.343 bar / 385.9 K.** Taller is hotter, the
    plates leave the range UNIFAC's correlations cover (the reported "overflow
    encountered in exp"), and a band chosen from atmospheric boiling points is
    30 K below anything the head ever reaches.

    ⚠ Asserted here with NO plates at all, because pressurisation needs none and
    a flood is what costs wall clock. The plate count only makes it worse.

    ⚠ The transferable form is a DEFAULT that points the wrong way for glassware:
    ``VesselSpec.k_vent`` is 1e3, so a bench flask is open and a hand-assembled
    still is not -- its author has to turn exactly one vent back on, and nothing
    says so.
    """
    sealed, _ = _column(0, sealed=True)
    sealed.step(120.0)
    assert sealed.vessels["pot"].pressure > 1.6   # 1.70 bar at 120 s, 3.34 by 300
    assert sealed.vessels["pot"].T > 353.0        # 355.8 K at 120 s, 385.9 by 300

    opened, _ = _column(0)
    opened.step(150.0)
    assert opened.vessels["pot"].pressure == pytest.approx(1.014, abs=0.02)
    # the reflux plateau, which is what a distillation is supposed to sit on
    assert opened.vessels["pot"].T == pytest.approx(353.0, abs=1.5)


def test_temperature_steady_on_a_RIG_vessel_is_the_COUPLED_derivative():
    """⚠⚠ THE ONE CONDITION LIFTING IS NOT ENOUGH FOR, and it is the one a column
    protocol needs.

    Every other condition in the vocabulary reads the STATE, so evaluating it on
    the owner's slice of the rig vector answers it exactly. ``temperature_steady``
    reads the DERIVATIVE, and ``compile_condition`` builds that from the owner
    vessel's OWN rhs -- which for a still head is the cooling rate of a small
    flask of hot ethanol standing in a cold room. A column at steady total reflux
    therefore TIMED OUT on it while its head sat unmoving to two decimals.

    Both halves are asserted at ONE state, so this costs one flood: the coupled
    root says steady, the lifted root says the opposite. Same lesson as
    ``step_until``'s, one level deeper -- it is not only WHEN a condition is
    located that belongs to the coupled trajectory, it is what it computes.
    """
    from chemsim.vessel.conditions import compile_condition

    w, stack = _column(2)
    w.wait_until("head", Condition("temperature_above", 349.0), timeout=1200.0)
    settled = w.wait_until("head", Condition("temperature_steady", 0.005),
                           timeout=900.0)
    assert not settled.timed_out          # the coupled derivative DOES settle

    head = w.vessels["head"]
    local = compile_condition(Condition("temperature_steady", 0.005), head)
    y = head.integrator.pack(head._nL, head._nL2, head._nG, head._nS, head.T)
    # f >= 0 means satisfied. The uncoupled head, at the very state the coupled
    # run just declared steady, is nowhere near it -- and by a wide margin, not
    # by a tolerance.
    assert local(0.0, y) < -0.05

    # ⚠ AND THE LADDER, ASSERTED OFF THE SAME FLOOD because a flood is the
    # expensive thing here. A plate is a vessel with a vapour edge UP and a drain
    # back DOWN, and it behaves as a theoretical stage because the existing
    # physics makes it one: arriving vapour finds ``p > p_eq`` in a slightly
    # cooler vessel and partly condenses, the plate's own liquid evaporates, and
    # what leaves is in equilibrium with what is held. The MONOTONE composition
    # ladder is the whole mechanism the 0.85 heart rests on, and nothing in the
    # engine knows the word "plate".
    ladder = [_x_ethanol(w, v) for v in stack]
    assert ladder == sorted(ladder), ladder
    assert ladder[0] == pytest.approx(0.49, abs=0.02)      # the pot, ~as charged
    assert ladder[-1] > 0.77                               # two plates' worth
    for v in stack[1:]:
        assert sum(w.vessels[v].state().n_liquid.values()) > 1.0e-4


def test_the_reflux_ratio_is_the_ratio_of_two_drain_conductances():
    """⚠ WHY THE SPLIT IS TWO DRAINS AND NOT A NEW EDGE KIND. Both are first
    order in the SAME condenser holdup, so they divide it exactly in the ratio of
    their conductances whatever the holdup settles at -- the reflux ratio is
    declared rather than inferred, and total reflux is ``k = 0`` on one of them.
    Which also makes ``SET_EDGE`` the verb for opening the tap after flooding.
    """
    w, _ = _column(0, takeoff=True)
    reflux, takeoff = w.rig.connections[-2], w.rig.connections[-1]
    assert (reflux.a, reflux.b, reflux.k) == ("condenser", "head", 0.5)
    assert (takeoff.a, takeoff.b, takeoff.k) == ("condenser", "forerun", 0.0)
    w.now("set_edge", edge=len(w.rig.connections) - 1, k=0.1)
    w.flush()
    assert reflux.k / takeoff.k == pytest.approx(5.0)


def test_a_column_cut_on_the_POT_replays_from_its_script():
    """⚠ IN A GOOD COLUMN THE HEAD DOES NOT MOVE, so the head is the wrong
    instrument for closing this cut -- 0.002 K across an entire ethanol take-off
    is what good rectification IS. The signal is the POT's rising bubble point,
    and ``wait_until`` works on any vessel in the rig, so the band goes there.
    That does not weaken item 76(b): the head is still where the thermometer
    goes, it is just flat when the column is working.

    No plates, so this is cheap -- a pot, a head and a condenser still enrich,
    and the point being pinned is the PROTOCOL: a cut located on a different
    vessel is still a CONDITION and still replays to its own crossing. The eight
    plates the 0.85 heart needs are in ``examples/plate_column.py``, which
    measured 0.8544 and replayed to 0.000e+00.
    """
    w, _ = _column(0, takeoff=True)
    edge = len(w.rig.connections) - 1
    w.wait_until("head", Condition("temperature_above", 349.0), timeout=1200.0)
    w.now("set_edge", edge=edge, k=0.1)
    w.flush()
    cut = w.collect_fraction("pot", edge, "tail", 353.05, 353.10, 600.0,
                             park="forerun")
    assert cut["entered"]
    saved = w.save()
    back = World.replay(saved)
    for vid in w.vessels:
        assert _held(back, vid) == pytest.approx(_held(w, vid), abs=1e-9), vid
    entry = [e for e in w.script if e.get("do") == "collect_fraction"]
    assert entry == [{
        "do": "collect_fraction", "vessel": "pot", "edge": edge,
        "into": "tail", "enter": 353.05, "leave": 353.10,
        "timeout": 600.0, "park": "forerun",
    }]

"""P2 -- the two verbs that close the loop: BOTTLE and CHARGE from a stock.

⚠ **EVERY TEST HERE IS ABOUT ONE DESIGN DECISION**: a stock is a
``VesselState``, never ``(name, purity)`` -- ``GAME_DESIGN.md`` section 1. That
decision is cheap to state and easy to lose, because a purity scalar is the
obvious representation and it destroys every gate in the design the moment it
exists. So the first test is the decision itself, measured: two bottles carrying
the same label do different chemistry.

The rest are the plumbing that makes it real -- matter conserved through a
bottling, the film left on the glass, the temperature carried, a save that
round-trips and a replay that rebuilds the shelf from the script -- plus the
``Scenario.generations`` field P1 found missing, which is what lets the game ask
for one-generation play at all.
"""

from __future__ import annotations

import pytest

from chemsim.engine import SAVE_VERSION, Scenario, Shelf, Stock, VesselSpec, World
from chemsim.engine.scenario import TemplateSpec
from chemsim.engine.stock import state_to_dict
from chemsim.vessel import VesselState

WATER, ETOH, ACETIC, ESTER = "O", "CCO", "CC(=O)O", "CCOC(C)=O"
BENZOIC = "O=C(O)c1ccccc1"

FISCHER = TemplateSpec(
    name="fischer_esterification",
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000.0, reversible=True,
)


def _bench(**kw) -> Scenario:
    """One warm sealed flask on the esterification network."""
    spec = VesselSpec(volume=1.0, T=353.0, T_env=353.0, UA=20.0, kla=0.0, **kw)
    return Scenario(
        feed_species=[WATER, ETOH, ACETIC],
        templates=[FISCHER],
        vessels={"flask": spec},
        max_species=12,
    )


def _stock(name: str, **amounts: float) -> Stock:
    """A bottle made by hand, at bench temperature, all of it liquid."""
    return Stock(name=name,
                 state=VesselState(n_liquid=dict(amounts), n_gas={}, T=298.15))


# ---------------------------------------------------------------------------
# the decision itself
# ---------------------------------------------------------------------------


def test_two_bottles_with_the_same_label_do_different_chemistry():
    """⚠⚠ **THE WHOLE OF SECTION 1, AS A MEASUREMENT.** Two bottles, both
    honestly labelled "90 mol% ethanol". One's 10% is water and the other's is
    acetic acid. Charged into identical flasks and left for two hours at 353 K,
    one of them makes ethyl acetate and the other cannot.

    A ``(name, purity)`` inventory cannot tell these apart -- they are the same
    pair of values -- so every gate that reads a composition becomes decoration
    the moment purity becomes state. This is also why ``purity`` here is a
    method and not a field.
    """
    wet = _stock("ethanol, 90%", **{ETOH: 0.9, WATER: 0.1})
    sour = _stock("ethanol, 90%", **{ETOH: 0.9, ACETIC: 0.1})
    assert wet.purity("mole") == pytest.approx(0.9)
    assert sour.purity("mole") == pytest.approx(0.9)

    made = {}
    for label, stock in (("wet", wet), ("sour", sour)):
        w = World(_bench())
        w.charge_stock("flask", stock)
        w.flush()
        w.step(7200.0)
        made[label] = w.vessels["flask"].state().total(ESTER)

    assert made["sour"] > 1.0e-4
    # ⚠ ZERO TO THE SOLVER'S OWN PRECISION, NOT ZERO. The wet flask holds no
    # acid at all, so the rate is exactly zero and what comes back is 3.8e-11
    # mol -- below the integrator's per-component atol of 1e-9, and six orders
    # under the sour flask. Asserting an exact 0.0 here would be asserting
    # something about the solver rather than about the chemistry.
    assert made["wet"] < 1.0e-9
    assert made["sour"] > 1.0e6 * made["wet"]
    # And the derived labels differ on a mass basis, which is the figure a bench
    # would quote: the same mole fraction is not the same purity.
    assert wet.purity("mass") != pytest.approx(sour.purity("mass"), rel=1e-3)


def test_purity_is_derived_and_has_to_say_which_basis_it_is_on():
    """⚠ A wet crop is 50 mol% and 13 wt% water, and a bare percentage on a
    shelf row would be the one number that means neither.

    0.05 mol of benzoic acid (122.12 g/mol) wet with 0.05 mol of water
    (18.02 g/mol): half the molecules are water and an eighth of the mass is.
    Nothing here is stored -- both figures come out of the same mole vector.
    """
    crop = Stock(name="crude benzoic acid", state=VesselState(
        n_liquid={WATER: 0.05}, n_gas={}, n_solid={BENZOIC: 0.05}, T=298.15,
    ))
    # ⚠⚠ AND THIS IS WHY ``major`` TAKES THE BASIS TOO. The biggest component of
    # this bottle is WATER by mole and BENZOIC ACID by mass, so a ``major`` fixed
    # on moles printed beside a purity quoted by mass would read "water at
    # 87 wt%" -- two true numbers making one false statement.
    assert crop.major("mole") == WATER
    assert crop.major("mass") == BENZOIC
    assert crop.purity("mole") == pytest.approx(0.5)
    assert crop.purity("mass") == pytest.approx(122.12 / (122.12 + 18.02), rel=1e-3)
    assert "87." in crop.describe() and BENZOIC in crop.describe()
    with pytest.raises(ValueError, match="basis must be"):
        crop.purity("volume")


def test_two_bottles_under_one_name_are_never_merged():
    """A player who runs the same prep twice and calls both "crude aspirin" has
    TWO bottles, and section 1 is the reason: one may carry unreacted salicylic
    acid and the other acetic acid. Adding their mole vectors would invent a
    bottle nobody made, at a temperature nothing was ever at."""
    shelf = Shelf()
    first = shelf.put(_stock("crude", **{ETOH: 1.0}))
    second = shelf.put(_stock("crude", **{WATER: 2.0}))
    third = shelf.put(_stock("crude", **{ACETIC: 3.0}))
    assert [first.name, second.name, third.name] == [
        "crude", "crude (2)", "crude (3)"
    ]
    assert [round(s.total, 6) for s in shelf] == [1.0, 2.0, 3.0]


def test_taking_a_share_depletes_the_bottle_and_an_empty_one_leaves_the_shelf():
    """``Shelf.take`` is the PLAYER's shelf verb -- the one ``World.shelf``
    deliberately never sees, because a run must not depend on an inventory that
    lives outside (scenario, script). A bottle with nothing left in it is not a
    thing on a shelf, so it is removed rather than kept as a zero."""
    shelf = Shelf()
    shelf.put(_stock("ethanol", **{ETOH: 2.0}))
    got = shelf.take("ethanol", 0.25)
    assert got.total == pytest.approx(0.5)
    assert shelf.get("ethanol").total == pytest.approx(1.5)
    rest = shelf.take("ethanol", 1.0)
    assert rest.total == pytest.approx(1.5)
    assert "ethanol" not in shelf
    with pytest.raises(KeyError, match="no stock named"):
        shelf.take("ethanol")


# ---------------------------------------------------------------------------
# BOTTLE: matter, and the glass it wets
# ---------------------------------------------------------------------------


def test_bottling_conserves_matter_and_leaves_the_film_on_the_glass():
    """⚠ **BOTTLING IS A POUR AND SUFFERS A POUR'S LOSSES.** Had ``withdraw``
    moved matter perfectly, BOTTLE would have been a loss-free transfer sitting
    beside a lossy one -- and bottle-and-recharge would have been the cheapest
    route around holdup in the whole game.

    What is withheld is not destroyed: it stays on the wall of the flask it was
    poured from, which is where it physically is, so the total is exact.
    """
    w = World(_bench(drain_time=5.0, crystal_size=50.0e-6))
    w.now("charge", "flask", amounts={ETOH: 1.0, ACETIC: 0.2}, phase="liquid")
    w.flush()
    before = sum(w.vessels["flask"].state().n_liquid.values())

    stock = w.bottle("flask", "crude ester")
    left = sum(w.vessels["flask"].state().n_liquid.values())

    assert stock.total + left == pytest.approx(before, rel=1e-12)
    assert left > 0.0, "a real pour wets the glass"
    assert w.vessels["flask"].holdup_report()


def test_all_means_the_contents_of_the_flask_and_not_its_air():
    """⚠ A PHYSICAL CLAIM RATHER THAN AN OMISSION: tipping a flask into a bottle
    leaves the headspace behind and the bottle brings its own air. So ``"all"``
    takes both liquid layers and the solid heap, and a gas moves only when it is
    asked for by name.

    ⚠ ``"all"`` has been offered by the Transfer tab's phase list since the
    first commit and was never implemented -- clicking Pour with it selected
    raised. Found building BOTTLE, which needs the same word.
    """
    w = World(_bench())
    v = w.vessels["flask"]
    v.charge({ETOH: 1.0}, phase="liquid")
    v.charge({BENZOIC if False else ACETIC: 0.1}, phase="solid")
    v.fill_headspace({"O": 1.0})
    gas_before = sum(v.state().n_gas.values())
    assert gas_before > 0.0

    stock = w.bottle("flask", "the lot")
    assert sum(stock.state.n_gas.values()) == 0.0
    assert stock.state.n_liquid[ETOH] == pytest.approx(1.0)
    assert stock.state.n_solid[ACETIC] == pytest.approx(0.1)
    assert sum(v.state().n_gas.values()) == pytest.approx(gas_before)


def test_a_bottle_poured_in_behaves_exactly_like_a_flask_poured_in():
    """The cross-check that says ``charge_state`` is a transfer and not a new
    physics: bottle a hot flask and charge the stock into a cold one, or pour the
    hot flask straight into the cold one. Same moles, same final temperature.

    ⚠ Which is the point of ``charge_state`` existing at all. Plain CHARGE adds
    moles and says nothing about heat -- right for "add 2 mol of acetic acid",
    wrong for a bottle that came off a hot plate. A stock is a STATE.
    """
    def two_flasks() -> Scenario:
        sc = _bench()
        sc.vessels = {
            "hot": VesselSpec(volume=1.0, T=353.0, T_env=353.0, UA=0.0, kla=0.0),
            "cold": VesselSpec(volume=1.0, T=290.0, T_env=290.0, UA=0.0, kla=0.0),
        }
        return sc

    poured = World(two_flasks())
    poured.vessels["hot"].charge({ETOH: 1.0, WATER: 0.5}, phase="liquid")
    poured.now("transfer", "hot", to="cold", fraction=1.0, phase="all")
    poured.flush()

    bottled = World(two_flasks())
    bottled.vessels["hot"].charge({ETOH: 1.0, WATER: 0.5}, phase="liquid")
    stock = bottled.bottle("hot", "hot ethanol")
    bottled.charge_stock("cold", stock)
    bottled.flush()

    assert bottled.vessels["cold"].T == pytest.approx(
        poured.vessels["cold"].T, rel=1e-12
    )
    assert bottled.vessels["cold"].state().n_liquid == pytest.approx(
        poured.vessels["cold"].state().n_liquid
    )
    assert bottled.vessels["cold"].T > 300.0, "the cold flask was warmed"


def test_a_separated_bottle_keeps_its_layers_and_mixes_when_it_is_poured():
    """⚠ Two decisions that pull in opposite directions, and both are right.

    A bottle is not a vessel: it takes no stability decision, so ``withdraw``
    keeps the two liquid layers apart rather than throwing the split away -- a
    separated bottle is a real thing on a shelf. Charging it back lands both in
    the destination's PRIMARY layer, because that is what every transfer in
    ``vessel.py`` does and what pouring a separated bottle into a flask
    physically is. The receiving flask re-decides for itself at the next
    integration.
    """
    stock = Stock(name="two layers", state=VesselState(
        n_liquid={WATER: 1.0}, n_liquid2={ETOH: 0.5}, n_gas={}, T=298.15,
    ))
    assert stock.state.two_phase
    assert stock.total == pytest.approx(1.5)

    w = World(_bench())
    w.charge_stock("flask", stock)
    w.flush()
    st = w.vessels["flask"].state()
    assert st.n_liquid[WATER] == pytest.approx(1.0)
    assert st.n_liquid[ETOH] == pytest.approx(0.5)
    assert sum(st.n_liquid2.values()) == 0.0


def test_a_stock_the_network_does_not_know_is_refused_loudly():
    """⚠ THE SHAPE OF A REAL CONSTRAINT RATHER THAN A BUG. A network is derived
    from its feed, so a stock bottled in one world can only be charged into a
    world whose network knows its species -- which means a picker over the shelf
    has to put the chosen stocks' species into ``Scenario.feed_species``. Better
    said at the pour than discovered as a missing product later."""
    w = World(_bench())
    with pytest.raises(KeyError, match="not a species in this network"):
        w.charge_stock("flask", _stock("toluene", **{"Cc1ccccc1": 1.0}))
        w.flush()


def test_a_bottle_cannot_pour_more_than_it_holds():
    w = World(_bench())
    with pytest.raises(ValueError, match="at most 1.0"):
        w.charge_stock("flask", _stock("ethanol", **{ETOH: 1.0}), fraction=2.0)
        w.flush()


# ---------------------------------------------------------------------------
# the loop: an impurity introduced in step 1 is still there in step 3
# ---------------------------------------------------------------------------


def test_an_impurity_charged_in_the_first_step_survives_into_the_third():
    """⚠ **THE WHOLE POINT OF THE LOOP**, and it needs no bookkeeping because
    impurities are not tracked -- they are simply IN the mole vector.

    Water goes in with the first charge, the flask is bottled, the bottle is
    charged into a second flask, that is bottled in turn. The water is still
    there in the third bottle, in the amount arithmetic says it should be, and
    the player can see which step it came from because the stock carries the
    script that made it.
    """
    w = World(_bench())
    w.now("charge", "flask", amounts={ETOH: 1.0, WATER: 0.02}, phase="liquid")
    w.flush()

    first = w.bottle("flask", "step 1")
    w.charge_stock("flask", first, 0.5)
    w.flush()
    second = w.bottle("flask", "step 2")
    w.charge_stock("flask", second, 0.5)
    w.flush()
    third = w.bottle("flask", "step 3")

    assert third.amounts()[WATER] == pytest.approx(0.02 * 0.25)
    assert third.purity("mole") == pytest.approx(1.0 / 1.02, rel=1e-9)
    # ⚠ and the provenance grows, so "where did this water come from" is a
    # question the bottle itself answers.
    assert len(third.script) > len(second.script) > len(first.script)
    assert any(e.get("do") == "schedule"
               and e["event"]["kind"] == "charge_stock" for e in third.script)


def test_the_provenance_is_a_recipe_that_re_runs_to_the_same_bottle():
    """⚠ "How did I make this" is answerable AND re-runnable, which is the
    reason the script stores conditions rather than instants.

    A stock's ``script`` is replayed against the same scenario from nothing, and
    the shelf that comes out holds a bottle identical to the original -- same
    name, same mole vector, same temperature.
    """
    w = World(_bench())
    w.now("charge", "flask", amounts={ETOH: 1.0, ACETIC: 0.5}, phase="liquid")
    w.flush()
    w.step(600.0)
    stock = w.bottle("flask", "the product")

    again = World.replay({
        "version": SAVE_VERSION,
        "scenario": _bench().to_dict(),
        "seed": 0,
        "script": list(stock.script),
    })
    assert list(again.shelf.stocks) == ["the product"]
    assert again.shelf.get("the product").to_dict() == stock.to_dict()


def test_the_provenance_stops_at_the_bottling_and_not_wherever_the_queue_got_to():
    """⚠⚠ **THE SCRIPT RUNS AHEAD OF THE EVENT QUEUE**, and reading "the script
    as it stands" made a stock's recipe depend on when the queue was flushed.

    Entries are appended when an action is SCHEDULED and events are applied at
    step boundaries. So a run that bottles and then charges the bottle somewhere
    else, saved and replayed, produced two stocks with identical compositions to
    every digit and DIFFERENT provenances -- the replayed one carrying the
    ``charge_stock`` that happened afterwards. A recipe that includes what
    happened to a bottle after it was filled is not that bottle's recipe.
    """
    def run() -> World:
        w = World(_bench())
        w.now("charge", "flask", amounts={ETOH: 1.0}, phase="liquid")
        w.flush()
        w.step(10.0)
        stock = w.bottle("flask", "bottled")
        w.charge_stock("flask", stock, 0.5)
        w.flush()
        return w

    w = run()
    stock = w.shelf.get("bottled")
    assert not any(e.get("do") == "schedule"
                   and e["event"]["kind"] == "charge_stock"
                   for e in stock.script)
    replayed = World.replay(w.save())
    assert replayed.shelf.to_dict() == w.shelf.to_dict()


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------


def test_the_shelf_is_carried_by_a_save_and_rebuilt_by_a_replay():
    """Two doors, and they have to agree. ``load`` restores the shelf as the
    state it is; ``replay`` never restores it at all -- the bottle events are in
    the script, so re-running them fills it. That the two agree is the check
    that BOTTLE is a real event and not a side effect."""
    w = World(_bench())
    w.now("charge", "flask", amounts={ETOH: 1.0, ACETIC: 0.5}, phase="liquid")
    w.flush()
    w.step(300.0)
    w.bottle("flask", "half of it", fraction=0.5)
    w.step(300.0)
    w.bottle("flask", "the rest")

    blob = w.save()
    assert set(blob["shelf"]) == {"half of it", "the rest"}
    assert World.load(blob).shelf.to_dict() == w.shelf.to_dict()
    assert World.replay(blob).shelf.to_dict() == w.shelf.to_dict()


def test_a_replay_applies_a_trailing_event_and_used_not_to():
    """⚠ PRE-EXISTING, found by P2, and BOTTLE is exactly the event it bites.

    ``now`` schedules for the current instant and events fire between
    integrations, so an action taken after the last step -- which the original
    run applied with ``flush`` -- was left sitting in the replayed world's
    queue. Measured on a two-event script: ``set_heat`` 50 W gave the original
    ``Q_input = 50.0`` and the replay ``0.0``, with one event still pending. It
    stayed invisible because only a TRAILING event can be affected; anything
    with a ``step`` after it is applied by that step. "Bottle it and stop" is a
    trailing event, so P2 would have shipped a replay with an empty shelf.
    """
    w = World(_bench())
    w.now("charge", "flask", amounts={ETOH: 1.0}, phase="liquid")
    w.flush()
    w.step(10.0)
    w.now("set_heat", "flask", watts=50.0)
    w.flush()

    back = World.replay(w.save())
    assert back.vessels["flask"].Q_input == pytest.approx(50.0)
    assert back.pending_events == []


def test_the_save_format_moved_to_seven_for_the_shelf_and_the_bound():
    """⚠ Two changes, one version, and either would have earned a bump.

    A v6 reader handed a v7 save is the ``add_dropwise`` failure again: an
    unknown script entry is discovered part-way through the walk, so it executes
    everything before the first ``bottle`` and stops holding a world that looks
    finished. And a v7 save read as a v6 one would drop ``generations`` and
    rebuild the network to a FIXPOINT -- a flask with products in it that the
    saved run never had. Both are a different experiment wearing the right name.

    ⚠⚠ **AT 8 SINCE P4, AND THE BARE ``7`` ON THE LINE BELOW IS WHY THIS
    DOCSTRING NOW SAYS SO.** P4 bumped the version, updated every
    ``SAVE_VERSION == 7`` in the suite, and MISSED this one because it compares
    the blob to a literal instead of to the constant — so it survived a grep for
    the constant and only the full run found it. The comparison is against
    ``SAVE_VERSION`` now: a test that pins a version to a hand-typed integer has
    to be edited in two places by every session that moves it, and the second
    place is the one that gets forgotten. Version 8 carries the six
    ``ReactionTemplate`` fields ``TemplateSpec`` had been dropping — the same
    bytes mean something different, so a pre-8 save cannot be replayed to the
    trajectory it recorded. Version 9 (R3) is the opposite case and the only
    one: it REMOVES ``prune_threshold``, a field that reached nothing, so a v8
    save would replay identically — the refusal is for the format's contract,
    not the bytes.
    """
    assert SAVE_VERSION == 9
    w = World(_bench())
    w.now("charge", "flask", amounts={ETOH: 1.0}, phase="liquid")
    w.flush()
    w.bottle("flask", "a bottle")
    blob = w.save()
    assert blob["version"] == SAVE_VERSION
    assert "shelf" in blob
    assert blob["scenario"]["generations"] is None
    for older in (3, 4, 5, 6, 7, 8):
        with pytest.raises(ValueError, match="version"):
            World.load(dict(blob, version=older))
        with pytest.raises(ValueError, match="version"):
            World.replay(dict(blob, version=older))


def test_a_stock_round_trips_through_plain_data():
    """It has to be JSON: a shelf is going to be a PSV in ``data/catalog`` and a
    save is a dict with no numpy and no molecules in it."""
    import json

    stock = Stock(name="crude", state=VesselState(
        n_liquid={ETOH: 1.0}, n_liquid2={WATER: 0.5}, n_gas={"N#N": 0.01},
        n_solid={ACETIC: 0.2}, T=310.0, t=42.0,
    ), script=({"do": "step", "dt": 1.0},), source="flask", note="tier: bottle")
    blob = json.loads(json.dumps(stock.to_dict()))
    back = Stock.from_dict(blob)
    assert back.to_dict() == stock.to_dict()
    assert back.state.T == 310.0 and back.state.t == 42.0
    assert back.note == "tier: bottle"


def test_a_stock_cannot_alias_the_vessel_it_came_from():
    """A ``Stock`` is published to a view thread on a ``Snapshot``. One that
    aliased a live vessel's arrays would be a mutable object read from the wrong
    thread, which is the one thing Layer 7 exists to prevent."""
    state = VesselState(n_liquid={ETOH: 1.0}, n_gas={}, T=298.15)
    stock = Stock(name="x", state=state)
    state.n_liquid[ETOH] = 99.0
    assert stock.state.n_liquid[ETOH] == 1.0
    assert stock.total == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# what P1 handed to P2: generations was not a Scenario field
# ---------------------------------------------------------------------------


def test_generations_is_a_scenario_field_and_the_frontier_is_reported():
    """⚠⚠ **P1's HANDOFF, AND IT IS WHAT MAKES ONE-GENERATION PLAY SAYABLE.**
    ``World.__post_init__`` called ``build_network`` with no ``generations``, so
    a world always built to a fixpoint: ``Snapshot.unexpanded`` was correct and
    permanently empty, and nothing could request the mechanic
    ``GAME_DESIGN.md`` section 8.2 is written around.

    One generation is "what can the things in this flask do, once". It is an
    approximation that touches MATTER, so it may not be silent -- and it is not:
    the unexpanded frontier is a notice and a structured list.
    """
    sc = _bench()
    sc.generations = 1
    one = World(sc)
    assert one.network.unexpanded, "one generation leaves a frontier"
    assert any("generation" in n for n in one.network.notices)
    assert ESTER in one.network.unexpanded

    fixpoint = World(_bench())
    assert fixpoint.network.unexpanded == ()
    assert len(fixpoint.network.species) >= len(one.network.species)


def test_the_generation_bound_survives_a_save_and_none_stays_none():
    """⚠ ``int(d.get("generations"))`` would turn "build to a fixpoint" into a
    TypeError and a default of 0 would turn it into "apply no templates at all"
    -- a saved scenario that quietly built an empty network."""
    sc = _bench()
    sc.generations = 1
    blob = sc.to_dict()
    assert blob["generations"] == 1
    assert Scenario.from_dict(blob).generations == 1

    plain = Scenario.from_dict(_bench().to_dict())
    assert plain.generations is None
    assert Scenario.from_dict({}).generations is None


def test_state_to_dict_drops_the_zeros_but_never_a_number():
    """A vessel's ``state()`` names every species in the network, most of them
    at zero. A bottle carries what is in it."""
    w = World(_bench())
    w.vessels["flask"].charge({ETOH: 1.0}, phase="liquid")
    blob = state_to_dict(w.vessels["flask"].state())
    assert blob["n_liquid"] == {ETOH: 1.0}
    assert blob["n_gas"] == {}


def test_bottling_one_layer_of_a_funnel_gives_a_bottle_with_one_liquid():
    """⚠ "The second layer" is a fact about the FLASK, and means nothing about a
    bottle.

    ``withdraw`` keeps the split when both layers are taken -- a separated flask
    emptied into a jar gives a separated jar. Taking ONE layer is a separatory
    funnel, and the bottle it fills holds one liquid, so it lands in the primary
    block whichever vessel block it came out of. Otherwise a jar of ether drawn
    off the top would carry a shelf row reading "[2nd layer]", which describes
    the funnel it came from rather than the bottle it is.
    """
    sc = _bench()
    sc.feed_species = [WATER, ETOH, ACETIC, "Cc1ccccc1"]
    w = World(sc)
    v = w.vessels["flask"]
    v.charge({WATER: 3.0}, phase="liquid")
    v.charge({"Cc1ccccc1": 2.0}, phase="liquid2")

    upper = v.withdraw(1.0, phase="upper")
    assert sum(upper.n_liquid2.values()) == 0.0
    assert not upper.two_phase
    # toluene floats on water, so "upper" is the layer2 block -- and it still
    # arrives as the bottle's one liquid.
    assert upper.n_liquid["Cc1ccccc1"] == pytest.approx(2.0)
    assert Stock(name="off the top", state=upper).total == pytest.approx(2.0)

    both = v.withdraw(1.0, phase="all")
    assert Stock(name="the rest", state=both).total == pytest.approx(3.0)
    assert sum(v.state().n_liquid.values()) == pytest.approx(0.0, abs=1e-12)

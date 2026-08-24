"""Layer 5/6 -- isolating a solid, which is where a yield becomes a number.

Precipitation already worked: a solid crystallises out when the liquid can no
longer hold it, and redissolves when it can. What was missing was any way to
*collect* it -- you could grow a crop and never weigh it. ``filter_into`` is the
one primitive that needed adding; decant, wash and dry are all expressible
without it (see its docstring), and the headline test at the bottom is that the
purity-versus-yield trade-off then emerges rather than being scripted.
"""

import pytest

from chemsim.engine import Scenario, VesselSpec, World
from chemsim.engine.events import FILTER, Event
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties.electrolyte import electrolyte_provider
from chemsim.vessel import Vessel

BZ = Molecule.from_smiles("OC(=O)c1ccccc1").smiles      # benzoic acid, the product
WATER = "O"
NA, CL = "[Na+]", "[Cl-]"        # a soluble, non-crystallising tracer for liquor


@pytest.fixture(scope="module")
def net():
    # ⚠ THE ELECTROLYTE PROVIDER, and it is not optional. The tracer is
    # [Na+]/[Cl-], and the plain provider REFUSES a chloride ion -- deliberately,
    # because Joback prices it at Gf -10.43 kJ/mol against the ion table's
    # -111.73, so a plain network silently disagreed with an electrolyte one by
    # 101 kJ/mol for the same species. Chloride is the conjugate base of an acid
    # in the pKa table, so the ion table is where its value comes from.
    return build_network(
        [WATER, BZ, NA, CL], [], thermo=electrolyte_provider(), max_species=40
    )


def _flask(net, T=298.15):
    return Vessel(net, volume=1.0, T=T, T_env=T, UA=50.0, kla=0.0)


def _slurry(net, T=298.15):
    """A vessel holding solid, liquor and a dissolved tracer."""
    v = _flask(net, T)
    v.charge({WATER: 55.3, NA: 0.10, CL: 0.10})
    v.charge({BZ: 0.10}, phase="solid")
    return v


# ---------------------------------------------------------------------------
# what a filtration moves
# ---------------------------------------------------------------------------


def test_filtration_conserves_every_species(net):
    """The guardrail. A phase partition is bookkeeping, so nothing may be
    created or lost -- and it is easy to lose a stream when a destination is
    absent, which is why the discard case is checked separately below."""
    src = _slurry(net)
    before = {s: src.state().total(s) for s in net.species}

    cake, filtrate = _flask(net), _flask(net)
    src.filter_into(filtrate, cake, porosity=0.4)

    for s in net.species:
        after = src.state().total(s) + cake.state().total(s) + filtrate.state().total(s)
        assert after == pytest.approx(before[s], abs=1e-12), s


def test_the_cake_holds_back_mother_liquor_and_everything_dissolved_in_it(net):
    """The whole reason washing exists. A wet cake retains liquid, and the liquid
    is a solution -- so it carries that same share of every impurity. A filtration
    that left the solute behind would be a perfect purification, which no
    filtration is.

    ⚠ HOW MUCH it retains is a property of the CAKE and is checked against the
    mechanism rather than against a remembered number: the liquor held is what fits
    in the voids between the crystals, ``porosity * V_solid / (1 - porosity)``.
    """
    src = _slurry(net)
    V_solid = src.volume_of(src._nS)
    V_liquor = src.volume_of(src._nL)
    cake, filtrate = _flask(net), _flask(net)
    got = src.filter_into(filtrate, cake, porosity=0.4)

    held = 0.4 * V_solid / 0.6
    assert cake.volume_of(cake._nL) == pytest.approx(held, rel=1e-6)
    # ... and the tracer travels with it, in exactly that proportion.
    share = held / V_liquor
    assert cake.state().n_liquid[NA] == pytest.approx(0.10 * share, rel=1e-6)
    assert filtrate.state().n_liquid[NA] == pytest.approx(
        0.10 * (1.0 - share), rel=1e-6
    )
    assert got.cake_liquid > 0.0


def test_holdup_is_a_property_of_the_CAKE_not_of_the_liquor_it_came_from(net):
    """⚠ THE FIX THAT MOVED EVERY CRUDE-PURITY NUMBER IN THE PROJECT. Retention
    used to be a fraction of the liquor, so filtering one crop out of twice the
    solvent left twice as much mother liquor on it and the crude came out twice as
    dirty. A real cake holds what its own voids hold and no more, so the SAME crop
    from a bigger liquor is CLEANER, not dirtier -- which is also why a
    recrystallisation is done from plenty of solvent."""
    def crude_purity(water):
        src = _flask(net)
        src.charge({WATER: water, NA: 0.10, CL: 0.10})
        src.charge({BZ: 0.10}, phase="solid")
        cake = _flask(net)
        src.filter_into(None, cake, porosity=0.4)
        return cake.state().n_liquid[NA]

    small, large = crude_purity(27.7), crude_purity(55.4)
    # Twice the liquor, the same cake: the same VOLUME of liquor is held, so it
    # carries half the concentration-weighted tracer... which for a fixed total
    # tracer means half the moles.
    assert large == pytest.approx(0.5 * small, rel=0.02)
    # The old shape would have given exactly the same number for both.
    assert large < 0.9 * small


def test_a_cake_cannot_hold_more_liquor_than_was_poured_on_it(net):
    """The cap, and it is not decoration: a big crop in a little solvent has voids
    that could hold more than is there, and the arithmetic would otherwise hand the
    cake a negative filtrate."""
    src = _flask(net)
    src.charge({WATER: 0.05, NA: 0.001})
    src.charge({BZ: 0.30}, phase="solid")
    cake, filtrate = _flask(net), _flask(net)
    got = src.filter_into(filtrate, cake, porosity=0.6)

    assert got.filtrate_liquid == pytest.approx(0.0, abs=1e-12)
    assert cake.state().n_liquid[WATER] == pytest.approx(0.05, rel=1e-9)
    assert filtrate.state().n_liquid[NA] == pytest.approx(0.0, abs=1e-15)


def test_the_solid_goes_to_the_cake_and_the_source_is_emptied(net):
    src = _slurry(net)
    cake, filtrate = _flask(net), _flask(net)
    got = src.filter_into(filtrate, cake, porosity=0.4)

    assert got.cake_solid == pytest.approx(0.10)
    assert got.recovered == pytest.approx(1.0)
    assert filtrate.state().n_solid[BZ] == pytest.approx(0.0)
    assert sum(src.state().n_liquid.values()) == pytest.approx(0.0)
    assert sum(src.state().n_solid.values()) == pytest.approx(0.0)


def test_fines_through_the_paper_are_a_yield_loss_you_can_account_for(net):
    """``passthrough`` is a defect rather than a mechanism, hence zero by
    default -- but it is here so that a low yield can have an honest cause."""
    src = _slurry(net)
    cake, filtrate = _flask(net), _flask(net)
    got = src.filter_into(filtrate, cake, porosity=0.4, passthrough=0.15)

    assert got.filtrate_solid == pytest.approx(0.015)
    assert got.cake_solid == pytest.approx(0.085)
    assert got.recovered == pytest.approx(0.85)


def test_a_missing_destination_discards_that_stream(net):
    """"Filter it off and bin the filtrate" has to be sayable. Discarding is a
    real action, distinct from forgetting -- so the solid must survive intact
    while the liquor genuinely leaves the simulation."""
    src = _slurry(net)
    cake = _flask(net)
    src.filter_into(None, cake, porosity=0.4)

    assert cake.state().n_solid[BZ] == pytest.approx(0.10)
    # A wet cake, carrying its share of the tracer -- discarding the filtrate is
    # not the same as squeezing the cake dry.
    assert 0.0 < cake.state().n_liquid[NA] < 0.10
    # ... and the rest of the liquor is gone, not hiding in the source.
    assert sum(src.state().n_liquid.values()) == pytest.approx(0.0)


def test_the_headspace_does_not_pour_through_a_filter(net):
    src = _slurry(net)
    src.fill_headspace_with_air()
    gas_before = sum(src.state().n_gas.values())

    cake, filtrate = _flask(net), _flask(net)
    src.filter_into(filtrate, cake)

    assert sum(src.state().n_gas.values()) == pytest.approx(gas_before)
    assert sum(cake.state().n_gas.values()) == pytest.approx(0.0)


def test_a_hot_filtration_warms_what_it_lands_in(net):
    """Transfers carry enthalpy, so a hot filtrate heats a cold receiver. The
    same rule ``pour_into`` already obeys -- filtration must not be the one
    transfer where energy appears from nowhere."""
    src = _slurry(net, T=350.0)
    cake, filtrate = _flask(net, T=280.0), _flask(net, T=280.0)
    src.filter_into(filtrate, cake, porosity=0.4)

    assert 280.0 < filtrate.T < 350.0
    assert filtrate.T > 340.0, "the filtrate is nearly all of the hot liquor"


def test_rejects_a_nonsensical_porosity(net):
    src = _slurry(net)
    with pytest.raises(ValueError, match="void fraction"):
        src.filter_into(_flask(net), _flask(net), porosity=1.5)
    with pytest.raises(ValueError, match="void fraction"):
        src.filter_into(_flask(net), _flask(net), porosity=1.0)
    with pytest.raises(ValueError, match="passthrough"):
        src.filter_into(_flask(net), _flask(net), passthrough=-0.1)


# ---------------------------------------------------------------------------
# the headline
# ---------------------------------------------------------------------------


def test_washing_a_cake_trades_yield_for_purity(net):
    """Recrystallise, filter, wash -- and the trade-off is not scripted anywhere.

    Hot water dissolves the whole charge; cooling drops most of it back out, but
    not all, because the cold solubility is not zero. Filtering leaves the crop
    wet with mother liquor, so it carries impurity in proportion to how wet it
    is. Washing with cold solvent rinses that away -- and dissolves some of the
    product too, because the crystals do not know the difference between wash
    solvent and mother liquor.

    Every one of those steps is the solubility law running forward. The only
    thing this test adds is a filter.
    """
    hot = _slurry(net, T=350.0)
    hot.run(3000.0)
    assert hot.state().n_solid[BZ] == pytest.approx(0.0, abs=1e-4), "should dissolve hot"

    hot.set_environment(275.0)
    hot.run(6000.0)
    crop = hot.state().n_solid[BZ]
    assert 0.05 < crop < 0.095, f"cooling must drop most but not all: {crop}"

    cake, liquor = _flask(net, 275.0), _flask(net, 275.0)
    first = hot.filter_into(liquor, cake, porosity=0.4)

    def purity(v):
        s = v.state()
        impurity = s.n_liquid[NA] + s.n_liquid[CL] + s.n_liquid[BZ]
        return s.n_solid[BZ] / (s.n_solid[BZ] + impurity)

    dirty, dirty_mass = purity(cake), first.cake_solid
    cake_snapshot = _flask(net, 275.0)
    cake_snapshot.charge(cake.state().n_liquid)
    cake_snapshot.charge(cake.state().n_solid, phase="solid")

    cake.charge({WATER: 10.0})       # a cold wash
    cake.run(3000.0)
    washed, waste = _flask(net, 275.0), _flask(net, 275.0)
    second = cake.filter_into(waste, washed, porosity=0.4)

    # ⚠ THE ASSERTION IS ON THE IMPURITY, NOT ON THE PURITY, and it had to move
    # when retention became a cake property: a crop that leaves the funnel holding
    # 6 mL of liquor rather than 50 is already ~99% pure, so there is no room left
    # for a ten-point gain. What a wash still does -- and what a purification is
    # actually judged on -- is cut what impurity there IS by a large factor.
    def impurity(v):
        s = v.state()
        return s.n_liquid[NA] + s.n_liquid[CL] + s.n_liquid[BZ]

    before, after = impurity(cake_snapshot), impurity(washed)
    assert after < 0.5 * before, "washing must cut the impurity materially"
    assert purity(washed) > dirty, "and purity must rise"
    assert second.cake_solid < dirty_mass, "and it must cost some product"
    assert second.cake_solid > 0.9 * dirty_mass, "but a cold wash is not ruinous"


# ---------------------------------------------------------------------------
# Layer 6: it has to be an event, or it is not replayable
# ---------------------------------------------------------------------------


def test_filtration_is_a_replayable_event():
    """Only events may mutate a vessel -- that rule is what makes a run
    reproducible from (scenario, event list) alone. A filtration performed by
    calling the method directly would be invisible to a save file."""
    spec = VesselSpec(volume=1.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)
    scenario = Scenario(
        feed_species=[WATER, BZ, NA, CL],
        templates=[],
        vessels={"flask": spec, "cake": spec, "filtrate": spec},
        # ⚠ Required, not decorative: a scenario without it cannot price an ion,
        # and the tracer here is [Na+]/[Cl-]. This is the replayable path's own
        # version of the fixture note above -- and it is the reason
        # Scenario.electrolyte exists at all.
        electrolyte=True,
    )
    w = World(scenario)
    w.vessels["flask"].charge({WATER: 55.3, NA: 0.1, CL: 0.1})
    w.vessels["flask"].charge({BZ: 0.1}, phase="solid")

    w.schedule(10.0, FILTER, "flask",
               filtrate="filtrate", cake="cake", porosity=0.4)
    w.run(duration=30.0, dt=10.0)

    # Not all 0.1 mol is still solid: the world ran for 10 s first, and some
    # dissolved toward saturation on the way. That is the point of routing it
    # through the engine rather than calling the method -- the filtration sees
    # the state the chemistry actually left, not the state that was charged.
    cake, filtrate = w.vessels["cake"].state(), w.vessels["filtrate"].state()
    assert 0.09 < cake.n_solid[BZ] < 0.1
    assert cake.total(BZ) + filtrate.total(BZ) == pytest.approx(0.1, abs=1e-9)
    # Nearly all of the tracer leaves with the filtrate: the cake's own voids hold
    # only a few mL of the litre of liquor. That figure MOVED when retention became
    # a property of the cake instead of a fraction of the liquor -- it used to be
    # 0.09 -- which is exactly the change the fix was made for.
    assert filtrate.n_liquid[NA] == pytest.approx(0.0993, rel=1e-2)
    assert cake.n_liquid[NA] + filtrate.n_liquid[NA] == pytest.approx(0.1, rel=1e-9)
    assert any("filter" in line for line in w.transfer_log)


def test_a_filter_event_survives_a_round_trip_through_json():
    ev = Event(t=5.0, seq=2, kind=FILTER, vessel="flask",
               payload={"filtrate": "f", "cake": "c", "porosity": 0.4})
    assert Event.from_dict(ev.to_dict()) == ev
    assert Event.from_dict(ev.to_dict()).payload == ev.payload

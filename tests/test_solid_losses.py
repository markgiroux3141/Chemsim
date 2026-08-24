"""Mechanical solid loss on collection: the crop that never leaves the flask.

Film holdup (``test_transfer_losses.py``) is a correct mechanic that changed the
benzoic-acid prep's yield by **nothing**, because every transfer in that prep
moves waste: the product travels as a solid in the cake, so the film left on the
pot wall is mother liquor that was already being discarded. This is the loss that
actually stands between a simulated crystallisation and a bench one.

It is held to exactly the same three requirements, because they are what
distinguish a mechanic from a tax:

  * MECHANISM      -- an adhering crystal layer one particle diameter thick,
                      converted to moles through the vessel's own molar volume;
  * SCALE          -- the same V^(2/3) wetted area, which is where the "absolute
                      floor" that ruins a small prep comes from;
  * COUNTERMEASURE -- rinse it through and re-filter, and the choice of rinse
                      liquid is a real trade-off.

plus the two hard constraints: conservation survives, and ``losses=None`` stays
exactly lossless.
"""

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties.electrolyte import electrolyte_provider
from chemsim.vessel import SPHERE_SHAPE_FACTOR, TransferLosses, Vessel

BZ = Molecule.from_smiles("OC(=O)c1ccccc1").smiles     # benzoic acid, the crop
WATER = "O"
NA, CL = "[Na+]", "[Cl-]"                              # a liquor tracer


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


def flask(net, T=275.0, volume=1.0, k_diss=0.0, **kw):
    return Vessel(net, volume=volume, T=T, T_env=T, UA=0.0, kla=0.0,
                  k_diss=k_diss, **kw)


def slurry(net, losses=None, scale=1.0, solid=0.10, **kw):
    """A crop of crystals under mother liquor. Everything scales together, so the
    glassware stays geometrically similar -- the premise the V^(2/3) area law
    rests on, and it has to be honoured or the scale test measures the wrong
    thing."""
    v = flask(net, losses=losses, volume=1.0 * scale, **kw)
    v.charge({WATER: 55.3 * scale, NA: 0.10 * scale, CL: 0.10 * scale})
    v.charge({BZ: solid}, phase="solid")
    return v


# ---------------------------------------------------------------------------
# the mechanism
# ---------------------------------------------------------------------------


def test_the_crust_is_a_particle_layer_not_a_fraction_of_the_crop(net):
    """Areal density = crystal_size * packing_fraction, converted to moles by the
    vessel's OWN molar volume.

    The distinction that matters: it is an ABSOLUTE amount set by the geometry,
    so doubling the crop in the same flask leaves the same crust behind rather
    than twice as much. A fraction cannot do that, and it is what makes the loss
    hurt a small prep and not a large one.
    """
    losses = TransferLosses(crystal_size=50e-6, packing_fraction=0.6)
    assert losses.crust_thickness == pytest.approx(30e-6)

    lost = []
    for crop in (0.05, 0.10, 0.20):
        src = slurry(net, losses=losses, solid=crop)
        cake = flask(net)
        got = src.filter_into(filtrate=None, cake=cake, porosity=0.4)
        lost.append(got.retained_solid)

    # Same flask and the same litre of liquor, so very nearly the same wetted
    # area and very nearly the same absolute crust: a FOURFOLD change in the crop
    # moves it by a few percent, and only because the crystals themselves are
    # part of what wets the glass.
    assert lost[2] / lost[0] < 1.05
    # ... which means the RELATIVE loss falls almost in proportion to the crop.
    assert lost[0] / 0.05 > 3.5 * (lost[2] / 0.20)


def test_the_crust_volume_is_the_wetted_area_times_one_particle_layer(net):
    """The arithmetic, against the geometry rather than against itself."""
    losses = TransferLosses(crystal_size=80e-6, packing_fraction=0.5)
    src = slurry(net, losses=losses)
    wetted = src.wetted_volume

    area = SPHERE_SHAPE_FACTOR * (wetted * 1e-3) ** (2 / 3)          # m^2
    expected_litres = area * 80e-6 * 0.5 * 1e3
    assert losses.crust_litres(wetted) == pytest.approx(expected_litres)

    cake = flask(net)
    got = src.filter_into(filtrate=None, cake=cake, porosity=0.4)
    # The crystals left behind occupy exactly that volume ...
    assert src.volume_of(src._nS) == pytest.approx(expected_litres, rel=1e-9)
    # ... and the MOLES follow from the molar volume the vessel already uses for
    # its own solid inventory, so there is no second density estimate anywhere
    # that could disagree with the one the RHS integrates.
    molar_volume = src.solid_volume / got.retained_solid          # L/mol
    assert got.retained_solid * molar_volume == pytest.approx(expected_litres)
    assert 0.09 < molar_volume < 0.11, "benzoic acid is ~96 mL/mol"


def test_a_denser_solid_leaves_more_mass_behind_with_no_per_species_parameter(net):
    """The crust is a VOLUME, so which species it costs you follows from the
    molar volumes the vessel already has. Two solids in one crop are left behind
    in the proportion they were present -- the same rule the film obeys for
    dissolved species, and the reason neither needs a table."""
    losses = TransferLosses(crystal_size=50e-6)
    src = flask(net, losses=losses)
    src.charge({WATER: 55.3})
    src.charge({BZ: 0.10, NA: 0.02}, phase="solid")
    cake = flask(net)
    src.filter_into(filtrate=None, cake=cake, porosity=0.4)

    left = src.crust
    assert left[BZ] > 0.0 and left[NA] > 0.0
    assert left[NA] / left[BZ] == pytest.approx(0.02 / 0.10, rel=1e-9)


def test_a_negative_crystal_size_is_refused_and_zero_is_allowed():
    """Zero is meaningful -- it isolates the film from the crust, which is how
    the two are measured apart in ``validation/process_losses.py``. Negative is
    not, and silently clamping it would hide a caller's mistake."""
    assert TransferLosses(crystal_size=0.0).crust_litres(1.0) == 0.0
    with pytest.raises(ValueError, match="crystal_size must be >= 0"):
        TransferLosses(crystal_size=-1e-6)
    with pytest.raises(ValueError, match="packing_fraction"):
        TransferLosses(packing_fraction=1.5)


# ---------------------------------------------------------------------------
# the scale law -- the property a fudge factor cannot have
# ---------------------------------------------------------------------------


def test_the_absolute_floor_is_the_geometry_not_an_asserted_constant(net):
    """The brief's "a small fraction plus an absolute floor" -- except the floor
    is not a second parameter, it is the V^(2/3) area law.

    Crust goes as V^(2/3) while the crop goes as V, so a tenfold smaller batch
    keeps 10^(2/3) = 0.2154x as much in absolute terms and therefore loses
    10^(1/3) = 2.154x as much proportionally. Nothing was told to do that, and it
    is the same signature film holdup carries -- which is the point: both rest on
    the same premise about geometrically similar glassware.
    """
    losses = TransferLosses(crystal_size=50e-6)
    absolute = []
    for scale in (10.0, 1.0, 0.1, 0.01):
        src = slurry(net, losses=losses, scale=scale, solid=0.10 * scale)
        got = src.filter_into(filtrate=None, cake=flask(net), porosity=0.4)
        absolute.append(got.retained_solid)

    for coarse, fine in zip(absolute, absolute[1:]):
        assert fine / coarse == pytest.approx(10.0 ** (-2 / 3), rel=1e-6)


def test_a_small_prep_can_lose_most_of_its_crop(net):
    """The consequence that makes it a mechanic: at milligram scale the crust is
    a large share of the crop, and the cap means it can be all of it. That is the
    honest end of the law, not an edge case to be smoothed away."""
    losses = TransferLosses(crystal_size=50e-6)
    tiny = slurry(net, losses=losses, scale=0.01, solid=1e-4)
    got = tiny.filter_into(filtrate=None, cake=flask(net), porosity=0.4)
    assert got.recovered < 0.5
    assert got.cake_solid >= 0.0                       # never negative


# ---------------------------------------------------------------------------
# the countermeasures
# ---------------------------------------------------------------------------


def test_rinsing_the_flask_through_recovers_the_crust(net):
    """The countermeasure that needed no code, for the same reason film holdup's
    did: the crystals are left where they physically are, so charging solvent and
    filtering again just works. Had the crust been deleted this would have been
    unimplementable and the loss would have been a tax."""
    losses = TransferLosses(crystal_size=50e-6)
    src = slurry(net, losses=losses)
    cake = flask(net)
    first = src.filter_into(filtrate=None, cake=cake, porosity=0.4)
    assert first.retained_solid > 0.0

    src.charge({WATER: 5.0})                           # rinse the flask out
    src.filter_into(filtrate=None, cake=cake, porosity=0.4)
    assert cake.state().total(BZ) > first.cake_solid


def test_rinsing_with_mother_liquor_costs_no_product_and_fresh_solvent_does(net):
    """A real bench decision with a real trade-off, and nothing scripts it.

    Fresh cold solvent recovers the crystals off the wall but dissolves some of
    them on the way; the mother liquor is already saturated and dissolves none.
    That difference is the solubility law running forward -- the only thing this
    test adds is a rinse.
    """
    losses = TransferLosses(crystal_size=50e-6)
    rinse_moles = 3.0                                  # ~54 mL, either way

    def rinse(with_liquor: bool) -> float:
        # k_diss > 0 so the liquor genuinely saturates against its own crop --
        # otherwise "mother liquor" would be pure water wearing the name, and
        # the test would be comparing two fresh rinses.
        src = slurry(net, losses=losses, k_diss=1e-2)
        src.run(600.0)
        cake, filtrate = flask(net), flask(net, k_diss=1e-2)
        src.filter_into(filtrate=filtrate, cake=cake, porosity=0.4)

        if with_liquor:
            filtrate.pour_into(src, fraction=rinse_moles / filtrate._nL.sum())
        else:
            src.charge({WATER: rinse_moles})           # fresh, and hungry
        src.run(600.0)
        src.filter_into(filtrate=filtrate, cake=cake, porosity=0.4)
        return cake.state().total(BZ)

    saturated, fresh = rinse(True), rinse(False)
    assert saturated > fresh
    # Both rinses recover crystals; the fresh one hands some of them back to the
    # filtrate as solute, which is the cost the choice is about.
    assert fresh > 0.0


def test_running_it_bigger_is_a_strategy(net):
    """The scale law, stated as the thing a player would actually do."""
    losses = TransferLosses(crystal_size=50e-6)
    recovered = []
    for scale in (0.1, 1.0, 10.0, 100.0):
        src = slurry(net, losses=losses, scale=scale, solid=0.10 * scale)
        got = src.filter_into(filtrate=None, cake=flask(net), porosity=0.4)
        recovered.append(got.recovered)
    assert recovered[0] < recovered[1] < recovered[2] < recovered[3]
    assert recovered[0] < 0.75, "a tenth-scale prep is punished"
    assert recovered[3] > 0.96, "and a hundredfold one barely notices"


# ---------------------------------------------------------------------------
# the two hard constraints
# ---------------------------------------------------------------------------


def test_the_crust_is_material_going_somewhere_not_disappearing(net):
    """Conservation is an invariant, not a nicety. The crystals stay in the
    vessel that was filtered, so the operation only ever FAILS TO MOVE
    material."""
    losses = TransferLosses(drain_time=2.0, crystal_size=50e-6)
    src = slurry(net, losses=losses)
    cake, filtrate = flask(net), flask(net)
    src.filter_into(filtrate=filtrate, cake=cake, porosity=0.4)

    for species, charged in ((BZ, 0.10), (WATER, 55.3), (NA, 0.10)):
        total = (
            src.state().total(species)
            + cake.state().total(species)
            + filtrate.state().total(species)
        )
        assert total == pytest.approx(charged, abs=1e-12), species
    assert src.state().total(BZ) > 0.0, "the crust should be left behind here"


def test_ideal_mode_is_exactly_lossless(net):
    """``losses=None`` is the default and must stay bit-exact -- it is how you
    tell a loss from a bug, and an invariant must not move because a default
    did."""
    src = slurry(net)
    assert src.losses is None
    cake, filtrate = flask(net), flask(net)
    got = src.filter_into(filtrate=filtrate, cake=cake, porosity=0.4)

    assert got.retained_solid == 0.0
    assert got.recovered == 1.0
    assert cake.state().total(BZ) == 0.10
    assert sum(src.state().n_solid.values()) == 0.0
    assert src.crust_report() == ""


def test_nothing_stochastic_and_nothing_in_the_rhs(net):
    """Repeating the same filtration must give bit-identical results: the crust
    is computed once, at an event boundary, from the state."""
    results = []
    for _ in range(3):
        src = slurry(net, losses=TransferLosses(crystal_size=50e-6))
        got = src.filter_into(filtrate=None, cake=flask(net), porosity=0.4)
        results.append((got.cake_solid, got.retained_solid))
    assert results[0] == results[1] == results[2]


# ---------------------------------------------------------------------------
# it says what it did, and it does not merge with the other losses
# ---------------------------------------------------------------------------


def test_the_crust_is_reported_and_is_not_folded_into_passthrough(net):
    """``passthrough`` is fines going THROUGH the paper -- a defect of the
    filter, cured by a better filter. The crust is crystals that never left the
    flask -- cured by a rinse. Merging them would make a low yield
    unattributable, so they are reported as separate lines and the recovery
    figure accounts for both."""
    src = slurry(net, losses=TransferLosses(crystal_size=50e-6))
    got = src.filter_into(
        filtrate=flask(net), cake=flask(net), porosity=0.4, passthrough=0.10
    )

    assert got.filtrate_solid == pytest.approx(0.010)          # fines
    assert got.retained_solid > 0.0                            # crust
    assert got.cake_solid + got.filtrate_solid + got.retained_solid == pytest.approx(
        0.10, abs=1e-12
    )
    assert got.recovered == pytest.approx(got.cake_solid / 0.10)

    report = src.crust_report()
    assert "crystals left adhering" in report
    assert "30 um packed layer" in report                      # the derived depth
    assert "50 um crop" in report
    assert "re-filter" in report                               # names the cure
    assert src.holdup_report() == "" or "film holdup" in src.holdup_report()


def test_the_fines_are_not_charged_the_crust_as_well(net):
    """A crystal that went through the paper was never on the wall. Charging it
    both would price one crystal twice, which is the arithmetic version of
    merging two mechanisms."""
    losses = TransferLosses(crystal_size=50e-6)
    plain = slurry(net, losses=losses).filter_into(
        filtrate=flask(net), cake=flask(net), porosity=0.4
    )
    with_fines = slurry(net, losses=losses).filter_into(
        filtrate=flask(net), cake=flask(net), porosity=0.4, passthrough=0.50
    )
    # Half the crop bypassed the wall, so the crust it could be charged is capped
    # by what remained -- never more than the plain case.
    assert with_fines.retained_solid <= plain.retained_solid + 1e-15

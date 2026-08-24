"""Film holdup: is it a mechanic, or a tax wearing a lab coat?

The rule this feature had to satisfy is that a loss the player can FIGHT is a
mechanic, and a loss they cannot fight is a tax. ``yield *= 0.9`` is a tax: a
silent approximation with no scale dependence and no countermeasure. So the tests
here are not only "does it subtract something" -- they check the three properties
that distinguish the two, plus the two hard constraints (conservation survives,
ideal mode stays exact).
"""

import pytest

from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.vessel import SPHERE_SHAPE_FACTOR, TransferLosses, Vessel

ETOH, WATER = "CCO", "O"


@pytest.fixture(scope="module")
def net():
    return build_network(
        [ETOH, WATER, "N#N"], templates=[], thermo=ThermochemistryProvider()
    )


def flask(net, **kw):
    return Vessel(net, volume=40.0, T=298.15, UA=0.0, kla=0.0, k_diss=0.0, **kw)


# ---------------------------------------------------------------------------
# the mechanism
# ---------------------------------------------------------------------------


def test_the_film_comes_from_the_drainage_law_not_a_constant():
    """delta = sqrt(nu / (g t)). The t^(-1/2) response is what makes "let it
    drain" a real decision rather than a flavour note, and it is the reason the
    parameter is a TIME rather than a thickness someone chose."""
    thin = TransferLosses(drain_time=30.0)
    thick = TransferLosses(drain_time=2.0)

    # Quadrupling the drain time halves the film, exactly.
    assert TransferLosses(drain_time=8.0).film_thickness == pytest.approx(
        TransferLosses(drain_time=2.0).film_thickness / 2.0
    )
    # Order of magnitude: tens to hundreds of microns for water.
    assert 2.0e-5 < thin.film_thickness < 1.0e-4
    assert 1.0e-4 < thick.film_thickness < 5.0e-4

    # A more viscous liquid holds a thicker film -- glycerol against water.
    assert (
        TransferLosses(kinematic_viscosity=7.0e-4).film_thickness
        > 20.0 * TransferLosses(kinematic_viscosity=1.0e-6).film_thickness
    )


def test_zero_drain_time_is_refused_rather_than_clamped():
    """The drainage law is singular at t = 0 (an undrained wall holds an unbounded
    film). Refusing beats silently substituting a number."""
    with pytest.raises(ValueError, match="drain_time must be positive"):
        TransferLosses(drain_time=0.0)


def test_holdup_is_capped_at_what_was_actually_there():
    """A film cannot hold back more than the volume present. Matters at the very
    small scales where the relative loss is heading for 100%."""
    losses = TransferLosses(drain_time=1.0)
    assert losses.holdup_litres(0.0) == 0.0
    tiny = 1.0e-9
    assert losses.holdup_litres(tiny) == pytest.approx(tiny)


# ---------------------------------------------------------------------------
# the scale law -- the property a fudge factor cannot have
# ---------------------------------------------------------------------------


def test_relative_loss_grows_as_the_batch_shrinks(net):
    """Wetted area goes as V^(2/3), so holdup is nearly constant in ABSOLUTE
    volume and the RELATIVE loss grows as V^(-1/3): a tenfold smaller batch loses
    10^(1/3) = 2.154x as much, proportionally.

    Nothing was told to do this -- it falls out of the geometry. It is also the
    entire reason "run it on a bigger scale" is a strategy, and the sharpest
    single check that this is a mechanism rather than a multiplier, because a
    multiplier is scale-free by construction.
    """
    losses = TransferLosses(drain_time=5.0)
    relative = []
    for moles in (100.0, 10.0, 1.0):
        src, dst = flask(net, losses=losses), flask(net)
        src.charge({ETOH: moles})
        before = src.liquid_volume
        src.pour_into(dst)
        relative.append(src.liquid_volume / before)

    for coarse, fine in zip(relative, relative[1:]):
        assert fine / coarse == pytest.approx(10.0 ** (1 / 3), rel=1e-3)


def test_the_area_law_is_the_sphere_it_claims_to_be():
    """A sphere is the minimum-area shape for a volume, so the default is an
    optimistic lower bound on holdup -- worth asserting, because a caller reading
    a small number should know which way it errs."""
    losses = TransferLosses(drain_time=5.0, shape_factor=SPHERE_SHAPE_FACTOR)
    v_litres = 1.0
    area = SPHERE_SHAPE_FACTOR * (v_litres * 1e-3) ** (2 / 3)   # m^2
    assert losses.holdup_litres(v_litres) == pytest.approx(
        area * losses.film_thickness * 1e3
    )
    # A narrower vessel wets more wall per unit volume and must lose more.
    narrow = TransferLosses(drain_time=5.0, shape_factor=2.0 * SPHERE_SHAPE_FACTOR)
    assert narrow.holdup_litres(v_litres) > losses.holdup_litres(v_litres)


# ---------------------------------------------------------------------------
# the countermeasures
# ---------------------------------------------------------------------------


def test_draining_longer_recovers_product(net):
    losses = [TransferLosses(drain_time=t) for t in (2.0, 5.0, 30.0)]
    lost = []
    for loss in losses:
        src, dst = flask(net, losses=loss), flask(net)
        src.charge({ETOH: 10.0})
        src.pour_into(dst)
        lost.append(10.0 - dst.state().total(ETOH))
    assert lost[0] > lost[1] > lost[2] > 0.0


def test_rinsing_recovers_the_film_and_needs_no_code_of_its_own(net):
    """The countermeasure that proves the design decision was right.

    The film is left in the SOURCE vessel rather than deleted, so charging fresh
    solvent and pouring again just works -- which is what a chemist actually does,
    and it needed no new verb. Had the loss been modelled as material
    disappearing, this would have been unimplementable and the loss would have
    been a tax.
    """
    src, dst = flask(net, losses=TransferLosses(drain_time=5.0)), flask(net)
    src.charge({ETOH: 10.0})
    src.pour_into(dst)
    after_one_pour = dst.state().total(ETOH)
    assert after_one_pour < 10.0                       # something was held back

    for _ in range(2):
        src.charge({WATER: 2.0})
        src.pour_into(dst)
    assert dst.state().total(ETOH) > after_one_pour
    assert dst.state().total(ETOH) == pytest.approx(10.0, rel=2e-3)


# ---------------------------------------------------------------------------
# the two hard constraints
# ---------------------------------------------------------------------------


def test_the_loss_is_material_going_somewhere_not_disappearing(net):
    """Conservation is an invariant, not a nicety.

    The film is not destroyed and not sent to a sink -- it stays on the wall of
    the vessel that was poured from, so this operation only ever FAILS TO MOVE
    material. Any loss modelled as matter vanishing would have destroyed the
    property ``numerics.project_non_negative`` was written to establish.
    """
    src, dst = flask(net, losses=TransferLosses(drain_time=2.0)), flask(net)
    src.charge({ETOH: 10.0, WATER: 4.0})
    src.pour_into(dst)

    for species, charged in ((ETOH, 10.0), (WATER, 4.0)):
        total = src.state().total(species) + dst.state().total(species)
        assert total == pytest.approx(charged, abs=1e-12)


def test_filtration_conserves_with_losses_on(net):
    """Same guarantee through the other transfer path. The withheld film stays in
    the vessel being filtered FROM, which is why a chemist rinses the reaction
    flask into the funnel."""
    src = flask(net, losses=TransferLosses(drain_time=2.0))
    cake, filtrate = flask(net), flask(net)
    src.charge({ETOH: 6.0, WATER: 20.0})
    src.filter_into(filtrate=filtrate, cake=cake, porosity=0.4)

    for species, charged in ((ETOH, 6.0), (WATER, 20.0)):
        total = (
            src.state().total(species)
            + cake.state().total(species)
            + filtrate.state().total(species)
        )
        assert total == pytest.approx(charged, abs=1e-12)
    assert src.state().total(ETOH) > 0.0, "the film should be left behind here"


def test_ideal_mode_is_exactly_lossless(net):
    """``losses=None`` must stay bit-exact, because that is what the conservation
    and mass-closure invariants check and it is how you tell a loss from a bug.
    It is also the default: an invariant should not move because a default did."""
    src, dst = flask(net), flask(net)
    assert src.losses is None
    src.charge({ETOH: 10.0})
    src.pour_into(dst)

    assert src.liquid_volume == 0.0
    assert dst.state().total(ETOH) == 10.0
    assert src.holdup_report() == ""
    assert sum(src.holdup.values()) == 0.0

    # Both mechanisms, or "ideal mode" stops being a single switch you can trust.
    solid_src, solid_dst = flask(net), flask(net)
    solid_src.charge({ETOH: 10.0}, phase="solid")
    assert solid_src.pour_into(solid_dst, phase="solid") == 10.0
    assert solid_src.crust_report() == ""
    assert sum(solid_src.crust.values()) == 0.0


def test_nothing_stochastic_and_nothing_in_the_rhs(net):
    """Repeating the same transfer must give bit-identical results.

    A random term inside the RHS would break BDF outright, and Layer 6's saves
    have to reproduce exactly -- so the holdup is computed once per transfer at an
    event boundary, from the state. Same reasoning that put the METER edge's rate
    in a parameter rather than a time window inside the ODE.
    """
    results = []
    for _ in range(3):
        src, dst = flask(net, losses=TransferLosses(drain_time=3.0)), flask(net)
        src.charge({ETOH: 7.0, WATER: 3.0})
        src.pour_into(dst)
        results.append((dst.state().total(ETOH), src.state().total(ETOH)))
    assert results[0] == results[1] == results[2]


# ---------------------------------------------------------------------------
# it says what it did
# ---------------------------------------------------------------------------


def test_the_holdup_is_reported_not_left_to_be_differenced(net):
    """A loss the player cannot see is indistinguishable from a bug."""
    src, dst = flask(net, losses=TransferLosses(drain_time=5.0)), flask(net)
    src.charge({ETOH: 10.0})
    src.pour_into(dst)

    report = src.holdup_report()
    assert "film holdup" in report
    assert "143 um" in report                          # the derived thickness
    assert "5 s draining" in report
    assert "rinse and pour again" in report            # names the countermeasure
    assert src.holdup[ETOH] == pytest.approx(10.0 - dst.state().total(ETOH))


def test_a_solid_transfer_does_not_borrow_the_liquid_film_law(net):
    """A film is a LIQUID on a wall, and a headspace transfer has no wall at all.

    A poured solid's losses are MECHANICAL -- crystals adhering to glass, and what
    a spatula cannot lift -- which is a different mechanism with a different scale
    law and a different cure. It exists now (see ``test_solid_losses.py``), and
    the point of this test is that the two do not bleed into one another: a solid
    transfer must be charged the CRUST and never the film, or a yield loss stops
    being attributable to a mechanism.
    """
    src, dst = flask(net, losses=TransferLosses(drain_time=1.0)), flask(net)
    src.charge({ETOH: 5.0})
    src._nS = src._nS + src._nL                    # pretend it all crystallised
    src._nL = src._nL * 0.0

    moved = src.pour_into(dst, phase="solid")
    assert moved < 5.0                             # the crust stayed behind
    assert sum(src.holdup.values()) == 0.0, "no liquid moved, so no film"
    assert src.holdup_report() == ""
    assert src.crust[ETOH] == pytest.approx(5.0 - moved)

    # ... and a gas transfer is charged neither.
    other, sink = flask(net, losses=TransferLosses(drain_time=1.0)), flask(net)
    other.charge({ETOH: 5.0}, phase="gas")
    assert other.pour_into(sink, phase="gas") == pytest.approx(5.0)
    assert sum(other.holdup.values()) == 0.0
    assert sum(other.crust.values()) == 0.0

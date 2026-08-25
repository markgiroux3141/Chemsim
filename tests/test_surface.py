"""A gas ARRIVING at a crystal: roasting an ore, and the gate a catalyst is.

The other half of M6's dichotomy. M6 built the reaction that happens INSIDE a
crystal and evolves a gas; this is the crystal a gas attacks, and the two are
different mechanisms with a refusal pointing each way.

Grouped by the claim each set pins:

  * **the wrong answer this fixes** -- a flask with no iron in it made ammonia
    for several sessions, because the catalysis was folded into an apparent
    barrier. It now makes EXACTLY zero, and the reference-charge run reproduces
    every number the folded version measured.
  * **why it is not a third ``PHASE_INDEX`` entry**, which is the design question
    the brief posed and which is settled here by arithmetic rather than by
    preference: labelling a solid-catalysed gas reaction "solid" moves it onto
    the pure-liquid standard state and multiplies K by 2.6e10 at 500 K.
  * **why roasting is a TERM** -- its reactant is a lattice, and
    ``thermochemistry`` refuses a lattice by name, so it cannot be priced on the
    ideal-gas basis the kernel's reverse derivation lives on at all.
  * **forward only, and that is two measurements** -- M6's ``p/K = n_A/n_B`` and
    an ``ln K`` of +67.6 to +78.8. The bar is enforced at pricing time, and the
    tightest row clears it by 20.7 decades.
  * **a catalyst cannot seed itself**, which is the exposure
    ``chemsim-solid-gate-fix`` records at 89% yield on 1.2e-4 mol of phantom NOx.
    Here the mechanism is absent rather than guarded, and the measurement is that
    the catalyst amount does not move by one bit.
  * **the contract** -- ``surface=False`` is EXACTLY the old vessel, and a
    network with no declared catalyst is bit-identical to one built before
    ``order_solid`` existed.
  * **what is NOT modelled** -- the site balance, and the rate cap's units.
"""

import dataclasses
import math

import numpy as np
import pytest

from chemsim.constants import R, R_L_BAR
from chemsim.network import build_network
from chemsim.network.builder import PHASE_INDEX
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties import surface as sf
from chemsim.properties.mineral_data import MINERALS
from chemsim.reactions import ReactionTemplate
from chemsim.reactions.library import SOLID_CATALYST_REFERENCE
from chemsim.reactions.synthesis import (
    alkene_hydrogenation,
    ammonia_synthesis,
    methanol_from_carbon_dioxide,
    methanol_from_carbon_monoxide,
    nitro_hydrogenation,
)
from chemsim.reactions.thermo import COLLISION_LIMIT, T_REF, reaction_deltas
from chemsim.vessel import Vessel
from chemsim.vessel.vessel import build_solid_state_arrays, build_surface_arrays

IRON = MINERALS["iron"]
SPHALERITE = MINERALS["sphalerite"].lattice
ZINCITE = MINERALS["zincite"].lattice
GALENA = MINERALS["galena"].lattice
LITHARGE = MINERALS["litharge"].lattice
O2 = "O=O"
SO2 = "O=S=O"
N2 = "N#N"
H2 = "[H][H]"
AMMONIA = "N"

# Tight tolerances everywhere a number is quoted. The default is NOT converged
# for a vented flask -- M6 measured 2.6x in a kiln's conversion and the tight run
# was FASTER -- and this term is fed by the same vent.
TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)


@pytest.fixture(scope="module")
def providers():
    thermo = ThermochemistryProvider()
    return thermo, VolatilityProvider(thermo)


def haber_net(providers, template):
    thermo, vol = providers
    return build_network([N2, H2], [template], thermo=thermo, volatility=vol)


def roast_net(providers, extra=()):
    thermo, vol = providers
    return build_network(
        [SPHALERITE, ZINCITE, O2, SO2, N2, *extra], [],
        thermo=thermo, volatility=vol,
    )


# ---------------------------------------------------------------------------
# THE WRONG ANSWER THIS FIXES
# ---------------------------------------------------------------------------


def test_a_flask_with_no_iron_in_it_makes_no_ammonia(providers):
    """The headline, and it is a wrong answer a player could see.

    ``ammonia_synthesis`` folded promoted iron into an apparent barrier, so a
    bare flask of nitrogen and hydrogen made ammonia and "you need a catalyst"
    could not be a gate. Zero here is EXACT, not small: the rate law carries
    ``nS(iron) ** 1`` and the flask holds none.
    """
    net = haber_net(providers, ammonia_synthesis())
    assert IRON.lattice in net.species, "the catalyst must be IN the network"

    v = Vessel(net, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4, k_vent=0.0)
    v.charge({N2: 0.25, H2: 0.75}, phase="gas")
    v.run(600.0, **TIGHT)
    assert v.state().total(AMMONIA) == 0.0


def test_the_same_flask_with_iron_in_it_does(providers):
    net = haber_net(providers, ammonia_synthesis())
    v = Vessel(net, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4, k_vent=0.0)
    v.charge({N2: 0.25, H2: 0.75}, phase="gas")
    v.charge({IRON.lattice: SOLID_CATALYST_REFERENCE}, phase="solid")
    v.run(600.0, **TIGHT)
    assert v.state().total(AMMONIA) > 0.1


def test_more_iron_is_faster_and_the_gate_is_smooth(providers):
    """First order in the catalyst, so the gate is a slope and not a switch.

    Which is also the shape that keeps it numerically safe: the rate is zero at
    an empty solid block with a BOUNDED slope, so there is nothing to
    regularise -- the same argument M6 makes for having no ``_avail`` gate.
    """
    net = haber_net(providers, ammonia_synthesis())
    got = []
    for iron in (0.0, 1.0e-6, 1.0e-3, 0.1):
        v = Vessel(net, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4, k_vent=0.0)
        v.charge({N2: 0.25, H2: 0.75}, phase="gas")
        if iron:
            v.charge({IRON.lattice: iron}, phase="solid")
        v.run(60.0, **TIGHT)
        got.append(v.state().total(AMMONIA))
    assert got[0] == 0.0
    assert got[1] < got[2] < got[3]


def test_the_reference_charge_reproduces_the_folded_pre_exponential_exactly():
    """Arithmetic, not a run: ``A_catalysed * SOLID_CATALYST_REFERENCE == A_folded``.

    This is the whole content of naming a reference loading. Without it, making
    the catalysis explicit would silently slow every reaction that gained one --
    and it would do it while looking like physics.
    """
    for factory in (ammonia_synthesis, methanol_from_carbon_monoxide,
                    methanol_from_carbon_dioxide, alkene_hydrogenation,
                    nitro_hydrogenation):
        cat, folded = factory(), factory(catalyst=None)
        assert cat.solid_catalyst is not None
        assert folded.solid_catalyst is None
        assert cat.A * SOLID_CATALYST_REFERENCE == folded.A


def test_at_the_reference_charge_the_only_difference_is_displaced_volume(providers):
    """And it is measured, because the first guess about it was WRONG.

    A vented flask makes the two forms differ by 0.086%, which looks like a
    modelling difference and is not -- a vented comparison is not a comparison at
    all, because the two runs vent different amounts. SEALED, and with the flask
    enlarged by exactly the volume 0.1 mol of iron occupies, the two agree to
    5e-11 mol: solver tolerance.

    So the residual is a crystal displacing gas, which raises every concentration
    and which a fourth-order rate law and a mole-losing equilibrium both notice.
    Real, small, and not an artefact.
    """
    charge = {N2: 0.25, H2: 0.75}

    def run(template, iron, volume):
        net = haber_net(providers, template)
        v = Vessel(net, volume=volume, T=700.0, T_env=700.0, UA=1.0e4,
                   k_vent=0.0)
        v.charge(dict(charge), phase="gas")
        if iron:
            v.charge({IRON.lattice: iron}, phase="solid")
        v.run(600.0, **TIGHT)
        return v.state().total(AMMONIA)

    base = run(ammonia_synthesis(catalyst=None), 0.0, 1.0)
    displaced = SOLID_CATALYST_REFERENCE * IRON.Vm_solid
    same_flask = run(ammonia_synthesis(), SOLID_CATALYST_REFERENCE, 1.0)
    same_gas = run(ammonia_synthesis(), SOLID_CATALYST_REFERENCE,
                   1.0 + displaced)

    assert same_gas == pytest.approx(base, abs=1.0e-9)
    # and the un-corrected flask differs in the direction Le Chatelier says:
    # less room for a reaction that loses moles means MORE product.
    assert same_flask > base
    assert (same_flask - base) / base == pytest.approx(3.7e-4, rel=0.5)


def test_the_catalyst_does_not_move_the_equilibrium(providers):
    """It cannot: its exponent is identical on both arrows, so it divides out of
    ``k_f/k_r``. Ten times the iron reaches the SAME place, sooner."""
    net = haber_net(providers, ammonia_synthesis())
    got = []
    for iron in (0.1, 1.0):
        v = Vessel(net, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4, k_vent=0.0)
        v.charge({N2: 0.25, H2: 0.75}, phase="gas")
        v.charge({IRON.lattice: iron}, phase="solid")
        v.run(20_000.0, **TIGHT)
        got.append(v.state().total(AMMONIA))
    # Both at equilibrium; the small gap left is the volume the extra iron
    # displaces, which is a real effect and is bounded by it.
    assert got[1] == pytest.approx(got[0], rel=5.0e-3)


def test_the_derived_reverse_carries_the_catalyst_too(providers):
    """If it did not, adding iron would MOVE the equilibrium -- the failure
    ``library.esterification`` records for putting an acid on one arrow only."""
    net = haber_net(providers, ammonia_synthesis())
    arr = net.to_arrays()
    col = arr.order_solid[:, net.species.index(IRON.lattice)]
    assert len(col) == 2, "forward and derived reverse"
    assert np.all(col == 1.0)


# ---------------------------------------------------------------------------
# A CATALYST CANNOT SEED ITSELF -- the exposure, absent rather than guarded
# ---------------------------------------------------------------------------


def test_the_catalyst_amount_is_a_constant_of_the_motion(providers):
    """Not "conserved to 1e-12" -- UNCHANGED, bit for bit, at every charge.

    ``chemsim-solid-gate-fix`` records a round-off-seeded lead chamber reaching
    89% yield on 1.2e-4 mol of phantom NOx, and the shape of that failure is a
    CYCLE with gain on its own catalyst. A declared solid catalyst has zero
    stoichiometry on both sides, so its row of the state derivative is
    identically zero and there is no gain to have. The exposure is absent, not
    regularised.
    """
    net = haber_net(providers, ammonia_synthesis())
    arr = net.to_arrays()
    i = net.species.index(IRON.lattice)
    assert np.all(arr.delta[:, i] == 0.0), "a catalyst is in no stoichiometry"

    for iron in (1.0e-12, 0.1, 1.0):
        v = Vessel(net, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4, k_vent=0.0)
        v.charge({N2: 0.25, H2: 0.75}, phase="gas")
        v.charge({IRON.lattice: iron}, phase="solid")
        v.run(600.0, **TIGHT)
        assert v.state().total(IRON.lattice) == iron


def test_a_catalyst_in_the_network_but_absent_does_not_trip_num_jac(providers):
    """The documented fragility this walks into and does NOT trip.

    A species in the network but absent from a sealed flask has an identically
    zero Jacobian COLUMN, which ``num_jac``'s perturbation factor inflates to
    inf -- ``chemsim-zero-jacobian-column``. A catalyst's column is not zero: the
    gas block's rates depend on its amount with slope ``k prod(C**order)`` even
    at zero. What IS zero is its row, which is what a catalyst should be.
    """
    net = haber_net(providers, ammonia_synthesis())
    v = Vessel(net, volume=1.0, T=1100.0, T_env=1100.0, UA=1.0e4, k_vent=0.0)
    v.charge({N2: 0.25, H2: 0.75}, phase="gas")      # no iron at all
    v.run(600.0, **TIGHT)                            # must not raise
    assert v.state().total(AMMONIA) == 0.0


# ---------------------------------------------------------------------------
# WHY THIS IS NOT A THIRD ``PHASE_INDEX`` ENTRY -- measured, not preferred
# ---------------------------------------------------------------------------


def test_phase_index_still_has_two_entries():
    """For the SECOND time, and for a different reason than M6's.

    M6's reason was that the kernel cannot express its rate law. This one is
    that the label would put the reaction on the wrong standard state -- see the
    test below, which is the measurement.
    """
    assert set(PHASE_INDEX) == {"liquid", "gas"}


def test_calling_a_catalysed_gas_reaction_solid_phase_would_cost_2e10_in_K(
    providers,
):
    """THE MEASUREMENT THAT SETTLED THE DESIGN.

    ``reaction_deltas`` applies the pure-liquid standard-state shift to any phase
    that is not ``"gas"``. So a ``phase="solid"`` label on ``N2 + 3 H2 -> 2 NH3``
    is not a naming choice, it is a change of thermodynamics -- and it is exactly
    the failure the ``PHASE_INDEX`` comment was written to prevent ("phase='any'
    silently became liquid"), arriving at the line that comment sits on.

    A solid-catalysed gas reaction IS a gas-phase reaction: every participant
    that has an activity is a gas, and a pure solid's activity is 1.
    """
    thermo, vol = providers
    net = haber_net(providers, ammonia_synthesis())
    fwd = next(r for r in net.reactions if r.name == "ammonia_synthesis")
    assert fwd.phase == "gas"

    dH_gas, dG_gas = reaction_deltas(fwd, thermo, vol)
    mislabelled = dataclasses.replace(fwd, phase="solid")
    dH_bad, dG_bad = reaction_deltas(mislabelled, thermo, vol)

    assert dG_bad - dG_gas == pytest.approx(-99.7, abs=1.0)
    assert dH_bad - dH_gas == pytest.approx(-22.9, abs=1.0)
    ratio = math.exp(-(dG_bad - dG_gas) * 1000.0 / (R * 500.0))
    assert ratio == pytest.approx(2.6e10, rel=0.1)


def test_an_uncatalysed_network_is_bit_identical(providers):
    """``order_solid`` all-zero is EXACTLY the old kernel, the way
    ``solid_state=None`` and ``losses=None`` are."""
    net = haber_net(providers, ammonia_synthesis(catalyst=None))
    arr = net.to_arrays()
    assert arr.order_solid.shape == (arr.n_reactions, arr.n_species)
    assert not np.any(arr.order_solid)
    assert IRON.lattice not in net.species


# ---------------------------------------------------------------------------
# THE DATA FLOOR: a metal is a lattice with no dissolved form
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("metal", ["iron", "nickel", "copper"])
def test_a_metal_prices_at_exactly_zero_on_the_solid_basis(metal):
    """FREE AND EXACT, and therefore a check rather than a datum.

    An element in its reference state is ``Hf = Gf = 0`` by definition on the
    basis that reference state lives on. For these three that basis is the SOLID
    one, and both halves are derived by the same arithmetic every mineral row
    uses -- CRC's ``Hfs``, and ``Gf`` from an entropy subtraction which for a
    metal subtracts the row's own entropy from itself. A non-zero result would
    prove the CAS names a different allotrope, which is the failure CRC's
    grey-tin row is refused for.
    """
    rec = MINERALS[metal]
    assert rec.Hf_solid == 0.0
    assert rec.Gf_solid == 0.0
    assert rec.S0_solid > 0.0
    # and the half a catalyst is actually needed for
    assert rec.Cp_solid is not None and rec.Vm_solid is not None


@pytest.mark.parametrize("metal", ["iron", "nickel", "copper"])
def test_a_metal_has_no_ions_and_is_not_a_precipitation_candidate(metal):
    """The emptiness is the claim. Iron does not dissolve to Fe atoms, and
    ``ions=('[Fe]',)`` would say that it does -- and would then offer iron
    filings to ``solubility_product`` as a lattice whose only ion is itself.
    """
    from chemsim.vessel.vessel import build_precipitation_arrays

    rec = MINERALS[metal]
    assert rec.ions == ()
    arr, report = build_precipitation_arrays([rec.lattice, "O"])
    assert metal not in arr.names
    assert not any(metal in line for line in report), (
        "nothing was refused -- there is nothing here to dissolve"
    )


def test_a_metal_lattice_is_still_refused_by_the_gas_providers():
    """M6's bargain, unsoftened. ``mineral_data`` holding ``[Fe]`` does not make
    ``[Fe]`` priceable on the ideal-gas basis: that value is the iron ATOM."""
    thermo = ThermochemistryProvider()
    with pytest.raises(ValueError, match="bare element symbol"):
        thermo.get("[Fe]")


def test_a_declared_catalyst_must_be_a_priced_mineral():
    with pytest.raises(ValueError, match="not a name in mineral_data"):
        ReactionTemplate(
            name="nonsense", smarts="[C:1]=[C:2]>>[C:1][C:2]",
            A=1.0, Ea=1.0, solid_catalyst="unobtainium",
        )


def test_the_lattice_mask_is_true_exactly_for_a_mineral(providers):
    net = roast_net(providers)
    v = Vessel(net, volume=1.0, T=1100.0)
    mask = v.phases.lattice
    for i, smi in enumerate(net.species):
        assert bool(mask[i]) == (smi in (SPHALERITE, ZINCITE)), smi


# ---------------------------------------------------------------------------
# ROASTING: the declarations, and the bar they clear
# ---------------------------------------------------------------------------


def test_every_declared_row_prices_and_the_reverse_is_29_decades_down(providers):
    """``ln K`` at each row's own run temperature, against a bar of 20.

    That bar is what makes "forward only" a measurement rather than a
    simplification. It is checked at ``T_run`` because K moves with temperature
    and a row that is irreversible in a roaster need not be at room temperature.
    """
    thermo, _ = providers
    assert len(sf.SURFACE_REACTIONS) == 4
    for decl in sf.SURFACE_REACTIONS:
        priced = sf.price(decl, thermo)
        assert priced.dH < -600_000.0, "roasting is hugely exothermic"
        assert priced.ln_K_run > sf.LN_K_IRREVERSIBLE + 20 * math.log(10.0)
        assert priced.Ea == sf.ROASTING_EA
        assert priced.A == sf.ROASTING_A


def test_a_row_whose_reverse_is_real_is_refused_by_name(providers):
    """The refusal is the boundary between this term and M6's, from this side.

    M6's term refuses a gas REACTANT because an affinity quotient puts its
    pressure in a denominator. This term refuses a row with a live equilibrium,
    because mass action on a solid AMOUNT settles at ``p/K = n_A/n_B`` -- M6's
    own measurement, at 3.0863 against 3.0863.
    """
    thermo, _ = providers
    # calcite -> quicklime + CO2 as though it were a surface reaction: real
    # equilibrium, so it must be refused rather than run forward-only.
    decl = sf.SurfaceReaction(
        name="calcination-as-a-surface-reaction",
        solids=(("calcite", -1, 1.0), ("quicklime", +1, 0.0)),
        gases=(("O=C=O", +1, 0.0),),
        mechanism="decarbonation", T_run=1100.0, note="not a roast",
    )
    with pytest.raises(sf.UnpricedSurfaceReaction, match="ln K"):
        sf.price(decl, thermo)


def test_an_estimated_gas_is_refused(providers):
    """Same guard ``solid_state`` carries, and for the same reason: the answer IS
    the difference between a solid-basis number and a gas one."""
    thermo, _ = providers
    decl = sf.SurfaceReaction(
        name="made-up", solids=(("sphalerite", -2, 1.0), ("zincite", +2, 0.0)),
        gases=(("O=O", -3, 1.0), ("CCCCCCCCCCCCCCCC", +2, 0.0)),
        mechanism="roasting", T_run=1100.0, note="",
    )
    with pytest.raises(sf.UnpricedSurfaceReaction, match="ESTIMATE"):
        sf.price(decl, thermo)


def test_a_lattice_declared_as_a_gas_is_refused_by_name(providers):
    """``PhaseArrays.lattice`` is what chooses a species' basis, so a participant
    on the wrong side of the split would silently read the wrong block -- an error
    no measurement downstream could tell from a wrong rate constant.

    Iron on the GAS side is the reachable half of that mistake, and the refusal
    has to come BEFORE pricing: priced first, ``thermochemistry`` raises on the
    lattice SMILES and the report blames the formation data instead.
    """
    decl = sf.SurfaceReaction(
        name="iron-as-a-gas",
        solids=(("sphalerite", -2, 1.0), ("zincite", +2, 0.0)),
        gases=((IRON.lattice, -3, 1.0), (SO2, +2, 0.0)),
        mechanism="roasting", T_run=1100.0, note="",
    )
    original = sf.SURFACE_REACTIONS
    sf.SURFACE_REACTIONS = (decl,)
    try:
        arr, report = build_surface_arrays(
            [SPHALERITE, ZINCITE, IRON.lattice, SO2]
        )
    finally:
        sf.SURFACE_REACTIONS = original
    assert arr.m == 0
    assert len(report) == 1
    assert "wrong side of the solid/gas split" in report[0]
    assert IRON.lattice in report[0]

    # and the well-formed declaration builds, with no report at all
    arr, report = build_surface_arrays([SPHALERITE, ZINCITE, O2, SO2])
    assert arr.m == 1 and not report


def test_the_orders_are_first_order_in_each_and_not_the_stoichiometry():
    """``3 O2`` taken as mass action is third order in oxygen, which stalls
    asymptotically and makes the conversion a reading of ``ROASTING_A``. Same
    declaration ``library.sulfur_combustion`` makes, for the same reason."""
    arr, _ = build_surface_arrays([SPHALERITE, ZINCITE, O2, SO2])
    assert np.all(arr.n_solid_order == 1.0)
    assert np.all(arr.n_gas_order == 1.0)
    # and the stoichiometry is NOT the rate law
    j = arr.names.index("sphalerite-roasting")
    assert arr.nu[j].sum() == -1.0        # 2 + 3 in, 2 + 2 out
    assert arr.order[j].sum() == 2.0


def test_evans_polanyi_would_get_the_roasting_order_backwards(providers):
    """WHY ``alpha`` IS ZERO, measured rather than asserted.

    This project has one mechanism for making rates differ inside a family, and
    applied here it is wrong in a direction the catalog itself can check:
    cinnabar roasts in a 900 K retort and sphalerite needs an 1100 K roaster, but
    sphalerite is the MORE exothermic of the two. The overall enthalpy is not the
    barrier of the rate-determining step -- what orders these rows is the
    metal-sulfur bond, and this project has no table for that.
    """
    thermo, _ = providers
    by_name = {d.name: sf.price(d, thermo) for d in sf.SURFACE_REACTIONS}
    zn = by_name["sphalerite-roasting"]
    hg = by_name["cinnabar-roasting"]
    assert zn.dH < hg.dH, "sphalerite is the more exothermic"
    assert zn.decl.T_run > hg.decl.T_run, "and it needs the HOTTER furnace"
    # so a positive alpha would rank them the wrong way round; alpha is 0 here,
    # which is visible as one shared barrier.
    assert zn.Ea == hg.Ea == sf.ROASTING_EA


def test_the_clock_does_not_depend_on_the_charge(providers):
    """First order in the solid, so ``tau = 1/(k C_gas)``. A bigger bed is more
    throughput, not a longer roast -- which is what a roaster is."""
    thermo, _ = providers
    priced = sf.price(sf.SURFACE_REACTIONS[0], thermo)
    C = 0.21 / (R_L_BAR * 1100.0)
    tau = sf.time_constant(priced, 1100.0, C)
    assert tau == pytest.approx(1800.0, rel=0.02)
    assert sf.rate_constant(priced, 1100.0) == pytest.approx(0.242, rel=0.02)


def test_the_pre_exponential_is_below_the_collision_limit():
    """The one property that makes ``ROASTING_A`` a rate rather than a knob."""
    assert sf.ROASTING_A / COLLISION_LIMIT == pytest.approx(3.2e-5, rel=0.1)
    assert sf.ROASTING_A < COLLISION_LIMIT


# ---------------------------------------------------------------------------
# ROASTING: what a vessel does with it
# ---------------------------------------------------------------------------


def test_a_roast_runs_and_conserves_its_metal_exactly(providers):
    net = roast_net(providers)
    T = 1100.0
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e4)
    v.charge({SPHALERITE: 0.1}, phase="solid")
    v.charge({O2: 0.21 / (R_L_BAR * T), N2: 0.79 / (R_L_BAR * T)}, phase="gas")
    v.run(1800.0, **TIGHT)
    st = v.state()
    assert st.total(ZINCITE) > 0.0
    assert st.total(SPHALERITE) + st.total(ZINCITE) == pytest.approx(
        0.1, abs=1.0e-11
    )
    assert not v.conservation_report()


def test_a_sealed_roast_is_oxygen_limited_and_that_is_the_mechanic(providers):
    """A litre of air at 1100 K holds 2.3 mmol of oxygen, and 0.1 mol of ore
    needs 150. So a closed flask stalls at a couple of percent -- which is why a
    real roaster BLOWS AIR, and is the same shape as M6's kiln needing its CO2
    swept away."""
    net = roast_net(providers)
    T = 1100.0
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e4)
    v.set_vent(0.0)
    v.charge({SPHALERITE: 0.1}, phase="solid")
    v.charge({O2: 0.21 / (R_L_BAR * T), N2: 0.79 / (R_L_BAR * T)}, phase="gas")
    v.run(20_000.0, **TIGHT)
    st = v.state()
    conv = st.total(ZINCITE) / 0.1
    assert 0.005 < conv < 0.05, conv
    assert st.total(O2) == pytest.approx(0.0, abs=1.0e-6)


def test_a_blown_roast_goes_and_an_insulated_one_is_autothermal(providers):
    """NOBODY DECLARES THIS. A zinc roaster needs no fuel, and here that is what
    -883 kJ/mol of reaction enthalpy does to a flask with no wall losses."""
    net = roast_net(providers)
    T = 1100.0
    air = {O2: 0.45 / 1800.0, N2: 0.45 * (79.0 / 21.0) / 1800.0}
    out = {}
    for label, UA in (("walled", 1.0e4), ("insulated", 0.0)):
        v = Vessel(net, volume=1.0, T=T, T_env=T, UA=UA, ingress=dict(air))
        v.charge({SPHALERITE: 0.1}, phase="solid")
        v.charge({O2: 0.21 / (R_L_BAR * T), N2: 0.79 / (R_L_BAR * T)},
                 phase="gas")
        v.run(1800.0, **TIGHT)
        st = v.state()
        out[label] = (st.total(ZINCITE) / 0.1, st.T)
        assert st.total(SPHALERITE) + st.total(ZINCITE) == pytest.approx(
            0.1, abs=1.0e-11
        )
    assert out["walled"][0] > 0.7
    assert out["walled"][1] == pytest.approx(T, abs=0.5)
    # the insulated bed heats itself by hundreds of kelvin and finishes
    assert out["insulated"][0] > out["walled"][0]
    assert out["insulated"][1] > T + 500.0


def test_surface_false_is_exactly_no_roasting(providers):
    """The same contract ``precipitation=False``, ``losses=None`` and
    ``solid_state=False`` keep -- and the report still answers the question."""
    net = roast_net(providers)
    T = 1100.0
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e4, surface=False)
    v.charge({SPHALERITE: 0.1}, phase="solid")
    v.charge({O2: 0.21 / (R_L_BAR * T)}, phase="gas")
    v.run(1800.0, **TIGHT)
    assert v.state().total(ZINCITE) == 0.0
    report = v.surface_report()
    assert "sphalerite-roasting" in report
    assert "surface=False" in report


def test_the_report_says_why_a_flask_can_do_nothing(providers):
    """"The ore just sat there" must not be indistinguishable from a bug."""
    thermo, vol = providers
    # oxygen and a crystal, but not a crystal any declared row names.
    net = build_network([O2, N2, "O", MINERALS["calcite"].lattice], [],
                       thermo=thermo, volatility=vol)
    v = Vessel(net, volume=1.0, T=1100.0)
    assert "no surface reaction is available" in v.surface_report()
    assert "not its ions" in v.surface_report()


def test_two_ores_in_one_flask_share_the_oxygen(providers):
    """Both rows run off the same headspace, so they compete -- and the solid
    block is an inventory, which is the limit this term shares with M6's."""
    thermo, vol = providers
    net = build_network(
        [SPHALERITE, ZINCITE, GALENA, LITHARGE, O2, SO2, N2], [],
        thermo=thermo, volatility=vol,
    )
    arr, _ = build_surface_arrays(net.species)
    assert set(arr.names) == {"sphalerite-roasting", "galena-roasting"}
    T = 1100.0
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e4,
               ingress={O2: 0.45 / 1800.0})
    v.charge({SPHALERITE: 0.05, GALENA: 0.05}, phase="solid")
    v.charge({O2: 0.21 / (R_L_BAR * T), N2: 0.79 / (R_L_BAR * T)}, phase="gas")
    v.run(1800.0, **TIGHT)
    st = v.state()
    assert st.total(ZINCITE) > 0.0 and st.total(LITHARGE) > 0.0
    assert st.total(SPHALERITE) + st.total(ZINCITE) == pytest.approx(
        0.05, abs=1.0e-11
    )
    assert st.total(GALENA) + st.total(LITHARGE) == pytest.approx(
        0.05, abs=1.0e-11
    )


# ---------------------------------------------------------------------------
# THE BOUNDARY WITH M6 HOLDS FROM BOTH SIDES
# ---------------------------------------------------------------------------


def test_m6s_term_still_refuses_a_gas_consuming_declaration():
    """The refusal that pointed here must keep pointing here. M6 measured an
    affinity form's reverse flux at 2.6e15 formula units per second as the gas
    reactant ran out; that is not a clipping problem, it is the form saying it is
    not a rate law for this."""
    from chemsim.properties import solid_state as ss

    decl = ss.SolidStateReaction(
        name="roasting-as-a-solid-state-reaction",
        solids=(("sphalerite", -2), ("zincite", +2)),
        gases=(("O=O", -3), ("O=S=O", +2)),
        mechanism="roasting", note="",
    )
    original = ss.SOLID_STATE_REACTIONS
    ss.SOLID_STATE_REACTIONS = original + (decl,)
    try:
        _, report = build_solid_state_arrays([SPHALERITE, ZINCITE, O2, SO2])
    finally:
        ss.SOLID_STATE_REACTIONS = original
    assert any("REFUSED" in line and "denominator" in line for line in report)
    assert any("PHASE_INDEX" in line for line in report)


# ---------------------------------------------------------------------------
# WHAT IS NOT MODELLED, PINNED SO IT CANNOT DRIFT
# ---------------------------------------------------------------------------


def test_the_rate_cap_does_not_currently_fire_on_a_catalysed_template(providers):
    """REPORTED, NOT FIXED -- ``detailed_balance``'s cap compares a catalysed
    pre-exponential against a limit that is not in its units, so it would fire
    ``1/SOLID_CATALYST_REFERENCE`` = 10x too eagerly. It does not fire today, and
    this test is what stops that starting silently. The cost if it did is a clock
    at most 10x slow, because the cap scales BOTH pre-exponentials and K is
    invariant under it."""
    for factory in (ammonia_synthesis, methanol_from_carbon_monoxide,
                    methanol_from_carbon_dioxide):
        net = build_network(
            [N2, H2, "[C-]#[O+]", "O=C=O"], [factory()],
            thermo=providers[0], volatility=providers[1], max_species=20,
        )
        for r in net.reactions:
            k = r.A * math.exp(-r.Ea / (R * T_REF)) * T_REF ** r.n_exp
            apparent = k * SOLID_CATALYST_REFERENCE
            assert apparent <= COLLISION_LIMIT, (r.name, apparent)


def test_there_is_no_site_balance_and_the_rate_is_first_order_for_ever(providers):
    """A real surface saturates; this one does not, and it is stated rather than
    approximated. Ten times the catalyst is ten times the rate at any loading.

    Measured as an INITIAL RATE off the RHS rather than as a yield after a finite
    run, and the difference matters: a run long enough to integrate is long enough
    to deplete, so the ten-times-faster flask has already moved further down its
    own curve and the yield ratio reads 9.75. That 2.5% is depletion, not
    saturation -- there is no saturation here to find. The flask is also enlarged
    by the metal's own volume so the gas concentrations are identical across the
    three states.
    """
    net = haber_net(providers, ammonia_synthesis())
    i = net.species.index(AMMONIA)
    rates = []
    for iron in (0.01, 0.1, 1.0):
        v = Vessel(net, volume=1.0 + iron * IRON.Vm_solid, T=700.0,
                   T_env=700.0, UA=1.0e4, k_vent=0.0)
        v.charge({N2: 0.25, H2: 0.75}, phase="gas")
        v.charge({IRON.lattice: iron}, phase="solid")
        terms = v.integrator.energy_terms(
            v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
        )
        rates.append(float(terms["dn_gas_rxn"][i]))
    assert rates[0] > 0.0
    assert rates[1] / rates[0] == pytest.approx(10.0, rel=1.0e-9)
    assert rates[2] / rates[1] == pytest.approx(10.0, rel=1.0e-9)

"""M6 -- a reaction that happens inside a crystal, and the lime cycle.

Grouped by the claim each set pins, because each claim was measured before the
code was written and one of them overturned the first implementation:

  * **the representation** -- the lattice has to be a SPECIES, because the
    ion-by-ion form of quicklime needs the oxide ion and no aqueous table
    anywhere prices it. Both halves of that refusal are pinned here, so an
    honest-looking future curation of ``[O-2]`` is told what it opens.
  * **the form** -- a pure solid has unit activity, so the equilibrium gas
    pressure above a pair of crystals must NOT depend on how much of each is
    there. The first implementation was mass action on the solid amounts and it
    settled at ``p/K = n_A/n_B`` to five figures. The test that would have caught
    it is ``test_the_equilibrium_pressure_does_not_depend_on_the_charge``.
  * **the derivation** -- ``Ea`` is not declared. It is the reaction enthalpy,
    which makes the reverse barrierless and its rate constant temperature-
    independent. That is what keeps a cold flask full of CO2 numerically sane.
  * **the mechanic** -- a kiln has a temperature below which nothing happens,
    and nobody typed it. It is where ``K(T)`` crosses what the room pushes back
    with.
  * **the contract** -- ``solid_state=False`` is EXACTLY the old vessel, the way
    ``precipitation=False`` and ``losses=None`` are.
"""


import math

import numpy as np
import pytest

from chemsim.constants import R
from chemsim.network import build_network
from chemsim.properties import solid_state as ss
from chemsim.properties.mineral_data import MINERALS
from chemsim.vessel import Vessel
from chemsim.vessel.vessel import build_solid_state_arrays

CALCITE = MINERALS["calcite"].lattice
QUICKLIME = MINERALS["quicklime"].lattice
PORTLANDITE = MINERALS["slaked lime"].lattice
CO2 = "O=C=O"
WATER = "O"

# ⚠ TWO NETWORKS, AND THE DIFFERENCE IS A PRE-EXISTING FRAGILITY THIS
# MILESTONE MADE REACHABLE RATHER THAN ONE IT INTRODUCED.
#
# A sealed tube is modelled with NO nitrogen or oxygen in the species list,
# because there is none in the tube. Carrying them anyway gives each an
# identically ZERO Jacobian column -- nothing acts on a species that is absent
# from a flask with no vent, no liquid to dissolve into and no reaction -- and
# that is verbatim the failure mode ``LAYER_REABSORB``'s comment records:
# ``num_jac`` finds every difference in the column below its threshold, inflates
# the perturbation factor without bound, overflows to inf, and hands BDF a NaN
# Jacobian.
#
# MEASURED, sealed at 1100 K, four charges, with and without the two spectator
# gases in the species list:
#
#     charge / mol    lean network            with N2/O2 present but absent
#       0.05          p/K - 1 = -1.7e-07      RAISED: CO2 reached -2.572 mol
#       0.1                    +3.5e-09       p/K - 1 = -2.6e-11
#       0.4                    -5.4e-13                +1.6e-07
#       1.0                    +2.6e-08                +1.9e-11
#
# The hair trigger on the charge is the signature of a NaN Jacobian rather than
# of a physical instability, and note what it is NOT: the lean column is exact
# at ``units_f / units_r`` up to 129.5, so the sign switch in the solid-state
# term handles a 130x derivative jump at its own operating point without
# trouble. It also does not return a wrong number -- ``check_raw_solution``
# raises "a failed integration wearing a success flag" -- so this is a latent
# fragility to report, not a silent error. See NEXT_SESSION.
LIME_SPECIES = [CALCITE, QUICKLIME, PORTLANDITE, CO2, WATER]
LIME_SPECIES_AIR = [*LIME_SPECIES, "N#N", "O=O"]


@pytest.fixture(scope="module")
def lime_network(thermo_module):
    """A sealed tube: only what is actually in it."""
    return build_network(LIME_SPECIES, [], thermo=thermo_module)


@pytest.fixture(scope="module")
def lime_network_air(thermo_module):
    """An open kiln, which needs the room's atmosphere to be representable."""
    return build_network(LIME_SPECIES_AIR, [], thermo=thermo_module)


def held(vessel, smiles: str) -> float:
    """mol of ``smiles`` in the solid heap. ``solids()`` omits a species the
    flask is not holding, and "none of it" is the answer half of these tests
    are checking for."""
    return vessel.solids().get(smiles, 0.0)


# ⚠⚠ THE DEFAULT SOLVER TOLERANCE IS NOT CONVERGED FOR A VENTED KILN, AND THE
# ERROR IS A FACTOR OF 2.6 IN THE ANSWER. Measured on the 1100 K swept kiln,
# where the converged answer is a flask sitting exactly at ``p_CO2 = K(T)``:
#
#     rtol / atol        converted   p(CO2) / bar
#     1e-6 / 1e-9  (the default)  39.04%      0.0000     <- lets CO2 escape
#     1e-8 / 1e-11                13.97%      0.7275     = K(1100 K) exactly
#     1e-10 / 1e-13               13.97%      0.7275
#
# So it CONVERGES, which is what says the loose reading is an artefact and not a
# different physical answer. The cause is the vent: ``k_vent`` is 1e3 mol/(bar s),
# so the gas balance is far stiffer than the chemistry feeding it, and at loose
# tolerance the solver under-resolves it and lets CO2 leak past a vent that
# should be holding it at ambient. ⚠ The tight runs are also FASTER (1.4-3.3 s
# against 5-13 s), because the loose solver was thrashing.
#
# ⚠ AND IT IS NOT THIS MILESTONE'S TERM. The same 36% appears with the
# solid-state term as the network's ONLY reaction and no extra rows, and it
# converges to the same 13.97%. Any slow source feeding this vent is exposed to
# it; reported in NEXT_SESSION.
CONVERGED = dict(rtol=1.0e-8, atol=1.0e-11)


def kiln(net, T, seconds, charge, volume=1.0, k_vent=1.0e3, sealed=False,
         tol=None, **kw):
    """A vessel at T holding ``charge`` in its solid heap. Sealed or swept.

    ⚠ The headspace is FILLED unless the vessel is sealed. A flask at exactly
    zero pressure with a 1e3 mol/(bar s) vent inhales 1013 mol/s at t = 0, and
    that transient -- not anything in this milestone -- is the OTHER way into
    the ``num_jac`` overflow above. Measured: 0.01 bar of nitrogen in the
    headspace removes the warning entirely.

    ⚠ ``tol`` defaults to the solver's own default, which a SEALED run is fine
    at. A VENTED one is not -- see ``CONVERGED``.
    """
    v = Vessel(
        net, volume=volume, T=T, T_env=T, UA=1.0e4,
        k_vent=0.0 if sealed else k_vent,
        atmosphere={} if sealed else {"N#N": 0.79, "O=O": 0.21},
        **kw,
    )
    v.charge(charge, phase="solid")
    if not sealed:
        v.fill_headspace()
    if seconds:
        v.run(seconds, **(tol or {}))
    return v


# ==========================================================================
# the representation: why the lattice has to be a species
# ==========================================================================

def test_the_ion_by_ion_route_to_quicklime_is_closed(thermo):
    """⚠ THE MEASUREMENT THAT FORCED A LATTICE TO BECOME A SPECIES.

    Every other solid in this project is held in the solid block ion by ion --
    that is what makes precipitation conserve matter by construction. Quicklime
    ion by ion is ``[Ca+2]`` and ``[O-2]``, and the oxide ion is in NO aqueous
    table because it does not exist in water: CaO does not dissolve to Ca2+ plus
    O2-, it hydrates. So there was no ionic route to the product of calcining
    limestone, and the choice was the lattice or nothing.

    Both halves of the refusal are pinned. If someone curates an oxide ion, this
    test is where they are told the ionic route just opened.
    """
    with pytest.raises(ValueError, match="net charge"):
        thermo.get("[O-2]")

    from chemsim.properties.solubility_product import (
        UnpricedLattice,
        solubility_product,
    )

    with pytest.raises(UnpricedLattice):
        solubility_product(MINERALS["quicklime"])


def test_a_lattice_species_is_still_refused_on_the_ideal_gas_basis(thermo):
    """M6 does not soften ``mineral_data``'s verdict; it works beside it.

    The lattice SMILES must still raise from the thermochemistry provider,
    because a solid-basis formation value wearing a ``ThermoData`` would be
    shifted by ``standard_state`` and dissolved by the fusion law. Layer 5
    resolves a mineral from ``mineral_data`` directly instead.
    """
    with pytest.raises(ValueError, match="ionic LATTICE"):
        thermo.get(CALCITE)


def test_a_lattice_never_dissolves_and_never_boils(lime_network):
    """``solidifies`` is False and the vapour pressure is 1e-30 bar.

    The entire bargain of M6: a crystal may now REACT while staying a crystal,
    and it still may not dissolve, because the fusion law is still measured
    wrong for a lattice by up to 407x in both directions.
    """
    v = Vessel(lime_network, volume=1.0, T=298.15)
    idx = {s: i for i, s in enumerate(v.species)}
    for lattice in (CALCITE, QUICKLIME, PORTLANDITE):
        i = idx[lattice]
        assert not v.phases.solidifies[i]
        assert not v.phases.condensable[i]
        assert v.integrator.saturation_coefficients(1200.0)[i] < 1.0e-25
        assert v.phases.Hfus[i] == 0.0
        assert v.phases.Tm[i] == 0.0
        assert not v.phases.ionic[i]         # a crystal is neutral overall


def test_a_lattice_in_water_stays_a_lattice(lime_network):
    """The other half of the same claim, integrated rather than inspected."""
    v = Vessel(lime_network, volume=1.0, T=298.15, k_vent=0.0, atmosphere={})
    v.charge({CALCITE: 0.01}, phase="solid")
    v.charge({WATER: 5.0})
    v.run(1000.0)
    assert held(v, CALCITE) == pytest.approx(0.01, rel=1e-9)
    assert v.state().n_liquid[CALCITE] == pytest.approx(0.0, abs=1e-12)


def test_the_crystal_carries_its_own_measured_volume_and_heat_capacity(
    lime_network,
):
    """A species in the solid block has to say how much room it takes and how
    much heat it holds, and a mineral's answers are CRC's rather than an ion's
    placeholder. Same row as its ``Hf_solid``."""
    v = Vessel(lime_network, volume=1.0, T=298.15)
    idx = {s: i for i, s in enumerate(v.species)}
    for lattice, name in ((CALCITE, "calcite"), (QUICKLIME, "quicklime")):
        rec = MINERALS[name]
        i = idx[lattice]
        assert v.phases.v_liq[i][0] == pytest.approx(rec.Vm_solid)
        assert v.phases.v_liq[i][1:] == pytest.approx([0.0, 0.0, 0.0])
        assert v.phases.Cp_liq[i][0] == pytest.approx(rec.Cp_solid)
    # And the values are the measured ones, not estimates.
    assert MINERALS["calcite"].Cp_solid == pytest.approx(83.5)
    assert MINERALS["calcite"].Vm_solid == pytest.approx(0.036932, abs=1e-6)
    assert MINERALS["quicklime"].Cp_solid == pytest.approx(42.0)


def test_a_mineral_with_no_crystal_bookkeeping_is_refused_loudly(thermo):
    """Two of the 25 minerals have a formation pair and no CRC ``Cps``. Charging
    one into a flask must say so rather than borrow a placeholder."""
    unpriced = [
        r for r in MINERALS.values()
        if r.Cp_solid is None or r.Vm_solid is None
    ]
    assert unpriced, "the guard is untested if every mineral prices"
    net = build_network([unpriced[0].lattice], [], thermo=thermo)
    with pytest.raises(ValueError, match="crystal Cp or molar volume"):
        Vessel(net, volume=1.0, T=298.15)


# ==========================================================================
# the pricing, and what is derived rather than declared
# ==========================================================================

def test_both_calcination_mechanisms_price_from_the_solid_basis(thermo):
    """⚠ M5's STANDARD APPLIED: the catalog calls both of these ``calcination``
    and they are TWO MECHANISMS. Decarbonation and dehydration are both built,
    because crediting the class on one would be M1's ``deprotonation`` mistake.
    """
    priced = {d.name: ss.price(d, thermo) for d in ss.SOLID_STATE_REACTIONS}
    assert {"decarbonation", "dehydration"} <= {
        p.decl.mechanism for p in priced.values()
    }

    # CaCO3(s) -> CaO(s) + CO2(g), straight off the two tables.
    dec = priced["calcination-decarbonation"]
    expect = (
        MINERALS["quicklime"].Hf_solid + thermo.get(CO2).Hf
        - MINERALS["calcite"].Hf_solid
    ) * 1000.0
    assert dec.dH == pytest.approx(expect)
    assert dec.dH / 1000.0 == pytest.approx(179.19, abs=0.01)
    assert dec.dS == pytest.approx(160.25, abs=0.01)

    deh = priced["calcination-dehydration"]
    assert deh.dH / 1000.0 == pytest.approx(108.47, abs=0.01)
    assert deh.dS == pytest.approx(143.62, abs=0.01)


def test_the_barrier_is_the_reaction_enthalpy_and_the_reverse_has_none(thermo):
    """⚠ ``Ea`` IS DERIVED. An endothermic decomposition whose reverse is a gas
    landing on an oxide surface has no reverse barrier, which fixes the forward
    barrier at ``dH`` -- the same floor ``detailed_balance`` enforces everywhere
    else here. Calcite comes out at 179.2 kJ/mol against experimental
    activation energies quoted at 170-200; nothing was fitted.
    """
    # ⚠ S9 -- OVER THE **DERIVED** ROWS ONLY, which is the whole of what this
    # derivation was ever about: an ENDOTHERMIC decomposition. An exothermic row
    # would get Ea = max(dH, 0) = 0 -- a barrierless reaction with no
    # temperature dependence -- so it declares its own forward pair, and
    # ``price`` refuses the derivation for it by name. See
    # ``test_an_exothermic_row_may_not_take_the_derived_pair``.
    derived = [d for d in ss.SOLID_STATE_REACTIONS if d.Ea is None]
    assert len(derived) == 7
    for decl in derived:
        p = ss.price(decl, thermo)
        assert p.Ea == pytest.approx(p.dH)
        assert p.dH > 0.0

    arr, _ = build_solid_state_arrays(LIME_SPECIES)
    assert arr.Ea_rev == pytest.approx(np.zeros(arr.m))
    # ...so the reverse rate constant does not depend on temperature at all.
    # That is what stops a cold flask full of CO2 acquiring an exploding
    # recombination rate from two exponentials that fail to cancel.
    assert arr.A_rev[0] == pytest.approx(ss.RECOMBINATION_A, rel=1e-9)


def test_the_declared_constant_is_the_REVERSE_one_and_it_is_shared(thermo):
    """⚠⚠ THE CORRECTION A SECOND ROW FORCED, AND THE TEST THAT PINS IT.

    Declared as a FORWARD constant, one number makes a lime kiln work and leaves
    green vitriol **thirteen decades too slow** -- measured, 0.00% conversion in
    20,000 s at every temperature its thermodynamics allow, because its ``dH`` is
    340 kJ/mol against calcite's 179 and ``Ea = dH``.

    The missing physics is the ENTROPY OF MAKING GAS. With the transition state
    taken to resemble the products -- the same late-TS assumption that makes the
    reverse barrierless -- the forward pre-exponential is ``A0 exp(dS/R)`` and
    ``A0`` is the reverse constant. So ``A0`` is the pre-exponential of ONE
    elementary event (a gas molecule reacting at a crystal surface, with no
    barrier), which is the same event for every row -- and that is why one number
    can cover four rows that make different amounts of gas.
    """
    # ⚠ S9 -- THE DERIVED ROWS ONLY. A row that declares its own forward pair
    # has its own elementary event, so its reverse constant is NOT this one; the
    # claim being pinned is that ONE number covers every row whose reverse IS
    # "a gas molecule reacting at a crystal surface with no barrier to climb".
    derived = [d for d in ss.SOLID_STATE_REACTIONS if d.Ea is None]
    for decl in derived:
        p = ss.price(decl, thermo)
        # every derived row's reverse constant is the SAME number, exactly
        assert p.A * math.exp(-p.dS / R) == pytest.approx(
            ss.RECOMBINATION_A, rel=1e-12
        )
    # ...and the forward constants are NOT the same number: the two-gas rows are
    # eleven decades above the one-gas rows, which is the entropy that used to be
    # hidden in a shared constant.
    forward = {d.name: ss.price(d, thermo).A for d in derived}
    assert max(forward.values()) / min(forward.values()) > 1.0e11

    # ⚠ AND CALCINATION'S FORWARD CONSTANT IS UNCHANGED TO EVERY DIGIT, which is
    # what makes every lime number in this file provably unmoved by the
    # correction: the calibration was always the calcination clock, and this only
    # changed which end of the reaction it is declared at.
    # (to 3 ppm -- RECOMBINATION_A is written to four figures, so the forward
    # constant it reproduces is 100000.34 rather than 100000 exactly.)
    assert forward["calcination-decarbonation"] == pytest.approx(1.0e5, rel=1e-5)


def test_the_four_rows_land_on_four_real_timescales(thermo):
    """⚠ FOUR OF THESE FIVE ARE TIMESCALES NOTHING WAS CALIBRATED AGAINST.

    ``RECOMBINATION_A`` is pinned by the lime kiln alone. The other rows then
    come out at the temperature their own chemistry is run at, and they land on
    the right order -- a red-hot retort of green vitriol in half a minute,
    baking soda in the catalog's own 450 K calciner in under a minute, and S4's
    montroydite gone in a quarter of a second in a 900 K mercury retort, which
    is why that retort never accumulates the oxide it makes. That is what says
    the entropy belonged in the pre-exponential rather than in the constant.
    """
    expect = {
        "calcination-decarbonation": (1200.0, 631.0),
        "calcination-dehydration": (900.0, 146.0),
        "sulfate-thermal-decomposition": (1000.0, 25.4),
        "bicarbonate-thermal-decomposition": (450.0, 43.7),
        "oxide-thermal-decomposition": (900.0, 0.2405),
        # ⚠⚠ S9 -- AND FIVE MORE, of which THREE are again timescales nothing
        # was calibrated against. The two CO reductions are pinned (600 s at
        # 1400 K is what fixes ``REDUCTION_A``) and so is thermite (1 s at its
        # 1200 K ignition temperature). The zinc retort at 257 s and the
        # Boudouard reaction at 13 s come out of ``RECOMBINATION_A`` -- a
        # constant pinned on a LIME KILN -- and land on a Belgian retort's own
        # few minutes and on a gasifier's own seconds.
        "tenorite-carbon-monoxide-reduction": (1400.0, 600.1),
        "litharge-carbon-monoxide-reduction": (1400.0, 600.1),
        "zincite-carbothermic-reduction": (1400.0, 256.9),
        "boudouard-gasification": (1300.0, 13.28),
        "metallothermic-reduction": (1200.0, 1.000),
    }
    for decl in ss.SOLID_STATE_REACTIONS:
        T, tau = expect[decl.name]
        p = ss.price(decl, thermo)
        k = p.A * math.exp(-p.Ea / (R * T))
        assert 1.0 / k == pytest.approx(tau, rel=0.02), decl.name


def test_a_gas_reactant_is_BOUNDED_now_and_the_old_refusal_measured_why():
    """⚠⚠ S9 -- THE REFUSAL THIS TEST USED TO PIN IS GONE, AND THE MEASUREMENT
    BEHIND IT IS REPRODUCED HERE AS THE CONTRAST.

    What was refused was an algebraic FORM, not a mechanism. Taken as one
    quotient, ``Q = prod(p ** nu_gas)`` gives a gas REACTANT a negative exponent
    -- its pressure in a denominator -- so an atmosphere depleted of it drove the
    reverse flux without bound. Split into the two one-sided products,

        net = k_f * prod(p ** consumed)  -  k_r * prod(p ** formed)

    nothing is divided at all, and the bound is ``k_r`` times a pressure. This
    test measures both numbers on the same declaration.
    """
    bogus = ss.SolidStateReaction(
        name="bogus-reduction",
        solids=(("tenorite", -1), ("copper", +1)),
        gases=(("[C-]#[O+]", -1), ("O=C=O", +1)),
        mechanism="gas-solid-reduction",
        note="a gas on the reactant side",
        Ea=ss.REDUCTION_EA,
        A=ss.REDUCTION_A,
    )
    original = ss.SOLID_STATE_REACTIONS
    ss.SOLID_STATE_REACTIONS = (bogus,)
    try:
        arr, report = build_solid_state_arrays(
            [MINERALS["tenorite"].lattice, MINERALS["copper"].lattice,
             "[C-]#[O+]", "O=C=O"]
        )
    finally:
        ss.SOLID_STATE_REACTIONS = original
    # it BUILDS now, and nothing is reported against it
    assert arr.m == 1
    assert not [line for line in report if "bogus-reduction" in line]
    assert (arr.nu_gas < 0.0).any()          # a gas really is on the left

    # the two one-sided products, and the quotient that used to be taken
    p = np.zeros(4)
    p[2] = 1.0e-12          # CO all but gone
    p[3] = 1.0               # CO2 at a bar
    T = 1400.0
    k_f = arr.A_fwd * np.exp(-arr.Ea_fwd / (R * T))
    k_r = arr.A_rev * np.exp(-arr.Ea_rev / (R * T))

    # ⚠ WHAT THE OLD FORM WOULD HAVE DONE. Q = p_CO2 / p_CO = 1e+12, so the
    # reverse branch is k_r Q -- twelve decades of it, and unbounded as p_CO
    # falls further. This is M6's 2.6e15 in this row's own units.
    Q = np.prod(p[None, :] ** arr.nu_gas, axis=1)
    assert Q[0] == pytest.approx(1.0e12, rel=1e-9)
    assert (k_r * Q)[0] > 1.0e4

    # ⚠ AND WHAT THE SPLIT FORM DOES: the reverse is k_r * p_CO2, full stop.
    P_react = np.prod(p[None, :] ** arr.gas_consumed, axis=1)
    P_prod = np.prod(p[None, :] ** arr.gas_formed, axis=1)
    net = k_f * P_react - k_r * P_prod
    assert net[0] == pytest.approx(-k_r[0] * 1.0, rel=1e-9)
    assert abs(net[0]) < 1.0e-5

    # ...and at p_CO exactly ZERO it is still finite, which is the whole claim.
    p[2] = 0.0
    P_react = np.prod(p[None, :] ** arr.gas_consumed, axis=1)
    assert P_react[0] == 0.0
    assert np.isfinite(k_f * P_react - k_r * P_prod).all()


def test_the_split_form_has_the_same_zero_as_the_quotient_form():
    """⚠⚠ ``net = k_f P_react - k_r P_prod`` IS ``P_react (k_f - k_r Q)``, so it
    has the SAME root: the equilibrium is still ``Q = K`` exactly and not
    ``Q = K n_A/n_B``. That is the property the affinity form exists to have, and
    the reason a gas reactant never threatened it.
    """
    original = ss.SOLID_STATE_REACTIONS
    ss.SOLID_STATE_REACTIONS = tuple(
        d for d in original if d.name == "boudouard-gasification"
    )
    try:
        arr, _ = build_solid_state_arrays(
            [MINERALS["carbon-graphite"].lattice, "O=C=O", "[C-]#[O+]"]
        )
    finally:
        ss.SOLID_STATE_REACTIONS = original
    assert arr.m == 1

    T = 1300.0
    K = float(arr.equilibrium_pressure(T)[0])       # bar^(+1), sum nu = +1
    k_f = arr.A_fwd * np.exp(-arr.Ea_fwd / (R * T))
    k_r = arr.A_rev * np.exp(-arr.Ea_rev / (R * T))
    # k_f / k_r IS K, in closed form and never by dividing two exponentials
    assert (k_f / k_r)[0] == pytest.approx(K, rel=1e-9)

    # put the gases at a quotient of exactly K and the flux is zero -- for ANY
    # solid charge, which is the unit-activity claim
    p_CO2 = 0.5
    p_CO = math.sqrt(K * p_CO2)                     # Q = p_CO^2 / p_CO2 = K
    p = np.array([0.0, p_CO2, p_CO])
    P_react = np.prod(p[None, :] ** arr.gas_consumed, axis=1)
    P_prod = np.prod(p[None, :] ** arr.gas_formed, axis=1)
    net = k_f * P_react - k_r * P_prod
    assert abs(net[0]) < 1.0e-12 * k_f[0]
    for charge in (1.0e-6, 1.0, 1.0e3):
        nS = np.array([charge, 0.0, 0.0])
        units_f, units_r = arr.units(nS)
        flux = net * np.where(net > 0.0, units_f, units_r)
        assert abs(flux[0]) < 1.0e-9 * charge


def test_an_exothermic_row_may_not_take_the_derived_pair(thermo):
    """⚠⚠ ``Ea = max(dH, 0)`` IS A DERIVATION ABOUT A DECOMPOSITION, and on an
    exothermic row it silently returns ZERO -- a barrierless reaction with no
    temperature dependence at all. Measured on thermite: 4.15e-6 1/s, a 2.8-day
    reaction that runs just as fast in a cold jar as in a furnace, which deletes
    the only mechanic thermite has. Refused at the declaration.
    """
    bogus = ss.SolidStateReaction(
        name="bogus-thermite-derived",
        solids=(("hematite", -1), ("aluminium", -2),
                ("iron", +2), ("corundum", +1)),
        gases=(),
        mechanism="metallothermic-reduction",
        note="no declared kinetics on an exothermic row",
    )
    with pytest.raises(ss.UnpricedSolidReaction, match="EXOTHERMIC"):
        ss.price(bogus, thermo)

    # ...and the number the refusal exists to prevent, so it is not an assertion
    real = [d for d in ss.SOLID_STATE_REACTIONS
            if d.name == "metallothermic-reduction"][0]
    p = ss.price(real, thermo)
    A_derived = ss.RECOMBINATION_A * math.exp(p.dS / R)
    assert A_derived == pytest.approx(4.15e-6, rel=0.02)
    assert max(p.dH, 0.0) == 0.0                     # the barrier that vanishes
    assert 1.0 / A_derived / 86400.0 == pytest.approx(2.79, rel=0.02)   # days


def test_half_a_kinetic_declaration_is_refused(thermo):
    """``A`` without ``Ea`` is a pre-exponential for a barrier nobody wrote
    down; ``Ea`` without ``A`` takes a constant calibrated as the reverse of a
    decomposition. Both or neither."""
    base = dict(
        solids=(("calcite", -1), ("quicklime", +1)),
        gases=(("O=C=O", +1),),
        mechanism="decarbonation",
        note="",
    )
    with pytest.raises(ss.UnpricedSolidReaction, match="declares Ea and not A"):
        ss.price(ss.SolidStateReaction(name="half-a", Ea=1.0e5, **base), thermo)
    with pytest.raises(ss.UnpricedSolidReaction, match="declares A and not Ea"):
        ss.price(ss.SolidStateReaction(name="half-b", A=1.0e5, **base), thermo)


def test_a_declared_barrier_below_dH_is_refused_because_it_would_break_K(thermo):
    """⚠ ``Ea_rev = max(Ea - dH, 0)`` CLIPS, and the clip is not a safety net --
    it would leave ``k_f/k_r`` no longer equal to ``K``, so the equilibrium would
    stop being the thermodynamics. It is also ``detailed_balance``'s own floor
    everywhere else in this project.
    """
    bogus = ss.SolidStateReaction(
        name="bogus-low-barrier",
        solids=(("calcite", -1), ("quicklime", +1)),
        gases=(("O=C=O", +1),),
        mechanism="decarbonation",
        note="",
        Ea=50_000.0,                  # dH is +179.2 kJ/mol
        A=1.0e5,
    )
    with pytest.raises(ss.UnpricedSolidReaction, match="below dH"):
        ss.price(bogus, thermo)

    # and every declared row in the table clears its own floor
    for decl in ss.SOLID_STATE_REACTIONS:
        if decl.Ea is None:
            continue
        p = ss.price(decl, thermo)
        assert p.Ea >= max(p.dH, 0.0)
        arr_Ea_rev = max(p.Ea - p.dH, 0.0)
        assert arr_Ea_rev == pytest.approx(p.Ea - p.dH)      # no clipping


def test_an_estimated_gas_is_refused_on_one_side_of_a_lattice(thermo):
    """A lattice subtraction is a difference of two formation values, so a
    group-contribution number on one side of it is the failure
    ``solubility_product`` measured at 25-29 decades."""
    bogus = ss.SolidStateReaction(
        name="bogus-estimated",
        solids=(("calcite", -1), ("quicklime", +1)),
        gases=(("CC(=O)OCC", +1),),      # priced by Joback, not curated
        mechanism="nonsense",
        note="",
    )
    with pytest.raises(ss.UnpricedSolidReaction, match="ESTIMATE"):
        ss.price(bogus, thermo)


# ==========================================================================
# the form: unit activity, and the mass-action failure it rules out
# ==========================================================================

def test_the_equilibrium_pressure_does_not_depend_on_the_charge(lime_network):
    """⚠⚠ THE TEST THAT WOULD HAVE CAUGHT THE FIRST IMPLEMENTATION.

    A pure solid has unit activity, so a pair of crystals fixes the gas pressure
    above them at ``K(T)`` no matter how much of each is present. The first
    version of this term was mass action on the solid amounts,
    ``k_f units_f - k_r Q units_r``, and it settled at

        p / K  =  n(calcite) / n(quicklime)

    exactly: 3.0863 against 3.0863 at 1100 K, 1.2139 against 1.2139 at 1200 K.
    Five figures on both, which is why the argument is a measurement.

    Three charges spanning 8x, one temperature, one volume: the SAME pressure,
    reached at different conversions.
    """
    T = 1100.0
    seen = []
    for charge in (0.05, 0.1, 0.4):
        v = kiln(lime_network, T, 40_000.0, {CALCITE: charge}, sealed=True)
        K = float(v.solid_state_arrays.equilibrium_pressure(T)[0])
        p = v.partial_pressures()[CO2]
        seen.append((charge, p, held(v, CALCITE), held(v, QUICKLIME)))
        assert p == pytest.approx(K, rel=1e-4)

    pressures = [p for _, p, _, _ in seen]
    assert max(pressures) == pytest.approx(min(pressures), rel=1e-4)
    # ...and the conversions genuinely differ, so this is not three copies of
    # one state. The mass-action form would have given three DIFFERENT
    # pressures in exactly this ratio.
    ratios = [a / b for _, _, a, b in seen]
    assert max(ratios) / min(ratios) > 3.0


def test_the_sealed_kiln_stalls_where_van_t_hoff_says_it_should(lime_network):
    """The extent forward-only would get wrong, at four temperatures."""
    for T, expected_conversion in (
        (900.0, 0.0012), (1000.0, 0.0123), (1100.0, 0.0793), (1200.0, 0.372)
    ):
        v = kiln(lime_network, T, 60_000.0, {CALCITE: 0.1}, sealed=True)
        converted = (0.1 - held(v, CALCITE)) / 0.1
        assert converted == pytest.approx(expected_conversion, rel=0.05)
        # Forward-only would read 100% at every one of these.
        assert converted < 0.5


def test_an_exhausted_crystal_stops_the_reaction(lime_network_air):
    """The other stopping condition, and the reason ``units`` cannot be dropped
    even though it divides out of the equilibrium: a swept kiln runs to
    completion and then holds, rather than driving the solid negative."""
    v = kiln(lime_network_air, 1250.0, 20_000.0, {CALCITE: 0.02})
    assert held(v, CALCITE) == pytest.approx(0.0, abs=1e-9)
    assert held(v, QUICKLIME) == pytest.approx(0.02, rel=1e-6)
    assert held(v, CALCITE) >= 0.0




def test_the_pre_exponential_is_a_clock_and_not_a_thermodynamic_quantity(
    lime_network,
):
    """``RECOMBINATION_A`` is the only free number in the module, and it
    multiplies the whole flux -- forward and reverse alike -- so it divides out
    of ``flux = 0``. A wrong ``A0`` moves the clock and nothing else.

    Measured over two decades: the same sealed pressure to seven figures.
    """
    base = ss.RECOMBINATION_A
    got = []
    try:
        for factor in (0.1, 1.0, 10.0):
            ss.RECOMBINATION_A = base * factor
            v = kiln(lime_network, 1200.0, 200_000.0, {CALCITE: 0.1},
                     sealed=True)
            got.append(v.partial_pressures()[CO2])
    finally:
        ss.RECOMBINATION_A = base
    assert got[0] == pytest.approx(got[1], rel=1e-6)
    assert got[2] == pytest.approx(got[1], rel=1e-6)


# ==========================================================================
# the mechanic: a kiln temperature nobody typed
# ==========================================================================

def test_the_kiln_gate_is_where_K_crosses_the_room(lime_network_air):
    """⚠ THE MECHANIC THE FORWARD-ONLY FORM WOULD HAVE DELETED.

    Under a bar of air, calcite calcines only once its own decomposition
    pressure exceeds what the room is pushing back with. Nothing declares a
    temperature: the threshold falls out of the CRC formation pair, and it lands
    between 1100 K (K = 0.73 bar, stalls at 13%) and 1150 K (K = 1.71 bar, runs
    to completion).
    """
    stalled = kiln(lime_network_air, 1100.0, 20_000.0, {CALCITE: 0.1},
                   tol=CONVERGED)
    ran = kiln(lime_network_air, 1150.0, 20_000.0, {CALCITE: 0.1},
               tol=CONVERGED)

    K_lo = float(stalled.solid_state_arrays.equilibrium_pressure(1100.0)[0])
    K_hi = float(ran.solid_state_arrays.equilibrium_pressure(1150.0)[0])
    assert K_lo < stalled.P_ambient < K_hi          # the gate, in one line

    # ⚠ BELOW THE GATE THE OPEN FLASK SITS AT EXACTLY K, WHICH IS THE WHOLE
    # MECHANISM. A vent only pushes gas out when the TOTAL exceeds ambient, so
    # CO2 below its own equilibrium pressure is not swept anywhere -- it fills
    # the headspace to K and the air makes up the rest. "Sweep the kiln" needs a
    # carrier FLOW (``Vessel.ingress``), not an open door.
    assert stalled.partial_pressures()[CO2] == pytest.approx(K_lo, rel=1e-3)
    assert (0.1 - held(stalled, CALCITE)) / 0.1 == pytest.approx(0.1397,
                                                                rel=0.02)
    # Above it, CO2 alone would exceed ambient, so it pushes the air out and
    # goes to completion.
    assert (0.1 - held(ran, CALCITE)) / 0.1 > 0.99
    assert ran.partial_pressures()[CO2] == pytest.approx(ran.P_ambient,
                                                         rel=1e-2)


def test_the_report_derives_the_kiln_temperature_rather_than_printing_one(
    lime_network,
):
    """``solid_state_report`` solves ``K(T) = P_ambient``. 1119 K for the
    decarbonation against a literature ~1170 K, and 756 K for the dehydration
    against ~785 K -- both about 30-50 K cool, which is what ``dCp = 0`` costs
    and is stated in ``solid_state.py`` rather than hidden."""
    v = Vessel(lime_network, volume=1.0, T=1200.0)
    report = v.solid_state_report()
    assert "1119 K to beat the room" in report
    assert "756 K to beat the room" in report
    assert "calcination-decarbonation" in report
    assert "calcination-dehydration" in report


def test_the_report_answers_the_same_question_with_the_term_off(lime_network):
    """The ``lle_report``/``precipitation_report`` contract: turning a term off
    must not be able to hide the question it answers."""
    v = Vessel(lime_network, volume=1.0, T=1200.0, solid_state=False)
    report = v.solid_state_report()
    assert "calcination-decarbonation" in report
    assert "solid_state=False" in report and "term is OFF" in report


# ==========================================================================
# the lime cycle: two declarations, three steps
# ==========================================================================

def test_slaking_is_the_dehydration_row_run_backwards(lime_network):
    """⚠ NOTHING DECLARES SLAKING. ``lime-cycle`` step 2 is
    ``CaO + H2O -> Ca(OH)2``, and it is this milestone's dehydration row in
    reverse -- which is only available because the term is reversible.

    ⚠ It is priced against water VAPOUR. Slaking with liquid water gets the
    condensation enthalpy from the vessel's own evaporation term instead, which
    is why the two must not both carry it.
    """
    v = Vessel(lime_network, volume=1.0, T=400.0, T_env=400.0, UA=1.0e4,
               k_vent=0.0, atmosphere={})
    v.charge({QUICKLIME: 0.05}, phase="solid")
    v.charge({WATER: 0.05}, phase="gas")
    # ⚠ 20 ks, not 1 ks. This row's forward constant is 1.35e4 1/s and not 1e5:
    # once the entropy of making gas moved into the pre-exponential, a row that
    # releases ONE mole of gas got slower relative to the shared constant. The
    # EQUILIBRIUM did not move at all -- only the clock.
    v.run(20_000.0, **CONVERGED)
    assert held(v, PORTLANDITE) > 0.04
    assert held(v, QUICKLIME) < 0.01
    # Calcium is conserved between the two lattices, exactly.
    assert (held(v, QUICKLIME) + held(v, PORTLANDITE)
            == pytest.approx(0.05, rel=1e-9))


def test_carbonation_is_emergent_from_the_two_rows(lime_network):
    """⚠ THE THIRD STEP OF THE LIME CYCLE IS NOT DECLARED ANYWHERE.

    ``Ca(OH)2 + CO2 -> CaCO3 + H2O`` is the dehydration row forwards and the
    decarbonation row backwards, sharing the quicklime in the solid block. Two
    declarations, three catalog steps -- which is the shape this project wants a
    mechanism to have.
    """
    v = Vessel(lime_network, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4,
               k_vent=0.0, atmosphere={})
    v.charge({PORTLANDITE: 0.02}, phase="solid")
    v.charge({CO2: 0.02}, phase="gas")
    v.run(50_000.0)
    assert held(v, CALCITE) > 1.0e-3        # limestone, nothing declared it
    assert v.partial_pressures()[WATER] > 0.1  # and the water it released
    total_ca = (held(v, CALCITE) + held(v, QUICKLIME)
                + held(v, PORTLANDITE))
    assert total_ca == pytest.approx(0.02, rel=1e-9)


# ==========================================================================
# the contract: conservation, energy, and the off switch
# ==========================================================================

def test_a_calcination_conserves_every_atom(lime_network):
    """Matter is exact everywhere in this project, and a reaction that writes
    two blocks at once is the newest way to break that."""
    from chemsim.matter import Molecule

    v = kiln(lime_network, 1200.0, None, {CALCITE: 0.1}, sealed=True)
    counts = [Molecule.from_smiles(s).element_counts() for s in v.species]
    # ⚠ CONVERGED, and what the default costs is worth naming: at rtol 1e-6 the
    # projection reports creating 8.6e-9 mol of PORTLANDITE, a species this
    # flask never holds any of. That is the known "a stiff reactant driven to
    # EXACTLY zero still overshoots" case (HANDOFF's own bullet, quoted there at
    # the 1e-4 level), reached here through the dehydration row's forward branch
    # draining a block with nothing in it. It CONVERGES away, which is what says
    # it is that and not a leak in the term.

    def elements(vessel):
        y = vessel.integrator.pack(vessel._nL, vessel._nL2, vessel._nG,
                                   vessel._nS, vessel.T)
        n = vessel.integrator.n
        total = (y[:n] + y[n:2 * n] + y[2 * n:3 * n] + y[3 * n:4 * n])
        out: dict[str, float] = {}
        for amount, c in zip(total, counts, strict=True):
            for el, k in c.items():
                out[el] = out.get(el, 0.0) + amount * k
        return out

    before = elements(v)
    v.run(20_000.0, **CONVERGED)
    after = elements(v)
    # A SEALED flask exports nothing, so every element is exact -- Ca and C move
    # between the solid and gas blocks and nothing leaves.
    assert set(before) == set(after)
    for el, amount in before.items():
        # ⚠ THE TOLERANCE IS THE SOLVER'S, NOT THE TERM'S, and naming which is
        # the whole point. ``run`` integrates at atol = 1e-9 per component, and
        # oxygen is counted three times over in every mole of CO2 across four
        # blocks, so a few times 1e-9 mol of drift on 0.3 mol is integration
        # error and not a leak. Measured at 6.1e-9 absolute; the term itself
        # writes ``nu_solid`` and ``nu_gas`` from one signed ``flux``, so what
        # it takes out of one block it puts into the other by construction.
        # ⚠ ``abs`` covers HYDROGEN, which starts at exactly zero here (nothing
        # charged holds any) and ends at 1.7e-8 mol. A tolerance quoted only as
        # ``rel`` cannot express "zero, to within what the solver can see".
        assert after[el] == pytest.approx(amount, rel=1e-7, abs=1e-7)
    # And the projection had nothing to tidy: no matter was created.
    assert v.conservation_report() == ""


def test_the_endothermic_load_appears_in_the_energy_report(lime_network_air):
    """A running kiln absorbs its own reaction enthalpy and the wall has to
    supply it. M12's instrument has to be able to see this term, or the balance
    it reports is not the one the temperature equation solved."""
    v = kiln(lime_network_air, 1200.0, 300.0, {CALCITE: 0.1})
    probe = v.integrator.energy_terms(
        v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    )
    assert "q_solid" in probe
    assert probe["q_solid"] < -1.0                 # endothermic: it cools
    assert probe["q_sum"] == pytest.approx(
        probe["q_rxn"] + probe["q_vap"] + probe["q_fus"] + probe["q_solid"]
        + probe["q_loss"] + probe["q_vent"] + probe["Q_input"]
    )
    assert "solid-state" in v.energy_report()


def test_solid_state_false_is_exactly_the_old_vessel(lime_network_air):
    """The same contract ``losses=None``, ``World.rig is None`` and
    ``precipitation=False`` keep: the term is identically zero, not small."""
    off = kiln(lime_network_air, 1200.0, 20_000.0, {CALCITE: 0.1},
               solid_state=False)
    assert held(off, CALCITE) == pytest.approx(0.1, rel=1e-12)
    assert held(off, QUICKLIME) == pytest.approx(0.0, abs=1e-15)
    assert off.partial_pressures()[CO2] == pytest.approx(0.0, abs=1e-15)
    assert off.integrator.solid is None


def test_the_kinetics_kernel_still_has_only_two_phases():
    """⚠ ``PHASE_INDEX`` DID NOT GAIN AN ENTRY, AND THAT IS THE MILESTONE'S
    ANSWER RATHER THAN AN OMISSION.

    M6's brief asked whether a solid-phase reaction is a third ``PHASE_INDEX``
    entry or a second term. It is a term, because mass action on the solid
    amounts cannot express unit activity -- see
    ``test_the_equilibrium_pressure_does_not_depend_on_the_charge``, which is
    the measurement. A gas-CONSUMING surface reaction (roasting, a solid
    catalyst) is the case that still wants the third entry.
    """
    from chemsim.network.builder import PHASE_INDEX

    assert set(PHASE_INDEX) == {"liquid", "gas"}


# ==========================================================================
# the two-gas rows: chain 2's seed, and the reason a cake rises
# ==========================================================================

GREEN_VITRIOL = MINERALS["green vitriol"].lattice
HEMATITE = MINERALS["hematite"].lattice
NAHCOLITE = MINERALS["nahcolite"].lattice
SODA_ASH = MINERALS["soda ash"].lattice
SO2, SO3 = "O=S=O", "O=S(=O)=O"


@pytest.fixture(scope="module")
def vitriol_network(thermo_module):
    return build_network([GREEN_VITRIOL, HEMATITE, SO2, SO3], [],
                         thermo=thermo_module)


@pytest.fixture(scope="module")
def soda_network(thermo_module):
    return build_network([NAHCOLITE, SODA_ASH, CO2, WATER], [],
                         thermo=thermo_module)


def test_the_catalog_row_names_a_product_that_is_not_the_reaction():
    """⚠ `vitriol-distillation` step 1 reads `iron-ii-sulfate -> iron-ii-OXIDE +
    sulfur-trioxide`, which balances and is not what happens. FeO does not
    survive red heat; anhydrous green vitriol gives HEMATITE with half its
    sulfur reduced to SO2. So the declaration is the chemistry and not the row.

    ⚠ AND FeO IS REFUSED BY THE CURATION RULE ANYWAY, on the half nobody would
    have guessed: its formation pair shares WEBBOOK, and CRC tabulates no
    crystal heat capacity for it at all. The refusal that stops the wrong
    reaction being built is the BOOKKEEPING one, not the thermochemical one.
    """
    assert "wustite" not in MINERALS
    assert "hematite" in MINERALS
    decl = next(d for d in ss.SOLID_STATE_REACTIONS
                if d.name == "sulfate-thermal-decomposition")
    assert dict(decl.solids) == {"green vitriol": -2, "hematite": +1}
    assert dict(decl.gases) == {SO2: +1, SO3: +1}


def test_chain_2s_seed_runs_and_makes_both_gases(vitriol_network):
    """⚠ THE ROW THAT WAS RECORDED AS BLOCKED ON THE ENGINE AND WAS BLOCKED ON
    DATA. `2 FeSO4(s) -> Fe2O3(s) + SO2(g) + SO3(g)` -- oil of vitriol's
    ancestor, and the SO3 half is what a receiver of water turns into sulfuric
    acid.
    """
    v = Vessel(vitriol_network, volume=1.0, T=1000.0, T_env=1000.0, UA=1.0e4,
               k_vent=1.0e3, atmosphere={})
    v.charge({GREEN_VITRIOL: 0.1}, phase="solid")
    v.run(2000.0, **CONVERGED)
    assert held(v, HEMATITE) > 0.045                 # of a possible 0.05
    assert held(v, GREEN_VITRIOL) < 0.01
    # one SO2 and one SO3 per formula unit of hematite, exactly
    made = held(v, HEMATITE)
    assert v.state().n_gas[SO2] + v.state().n_gas[SO3] > 0.0
    assert (v.state().n_gas[SO2] == pytest.approx(v.state().n_gas[SO3],
                                                  rel=1e-6))
    # iron is conserved between the two lattices
    assert 2 * held(v, HEMATITE) + held(v, GREEN_VITRIOL) == pytest.approx(
        0.1, rel=1e-6
    )
    assert made > 0.0


def test_a_two_gas_row_stalls_on_the_PRODUCT_of_both(vitriol_network):
    """Sealed, the driving force is ``Q = p(SO2) p(SO3)`` and ``K`` is in bar^2.
    That is what makes the threshold temperature not ``K = P_ambient``."""
    v = Vessel(vitriol_network, volume=1.0, T=900.0, T_env=900.0, UA=1.0e4,
               k_vent=0.0, atmosphere={})
    v.charge({GREEN_VITRIOL: 0.1}, phase="solid")
    v.run(200_000.0, **CONVERGED)
    pp = v.partial_pressures()
    Q = pp[SO2] * pp[SO3]
    K = float(v.solid_state_arrays.equilibrium_pressure(900.0)[0])
    assert Q == pytest.approx(K, rel=1e-3)
    assert 0.0 < held(v, HEMATITE) < 0.05            # stalled, not exhausted


def test_the_threshold_temperature_is_not_K_equals_ambient(vitriol_network):
    """⚠ A ROW EVOLVING n MOLES OF GAS HAS K IN bar^n, so comparing it against a
    pressure is a units error the moment ``n > 1``. The reference state that
    means something is the evolved gases being the whole atmosphere and sharing
    the ambient total, i.e. ``K(T) = (P/n)^n`` -- which for ``n = 1`` is exactly
    ``K = P``, so no lime number moves.
    """
    arr = Vessel(vitriol_network, volume=1.0, T=1000.0).solid_state_arrays
    assert int(arr.total_nu_gas[0]) == 2
    T_threshold = float(arr.threshold_temperature(1.01325)[0])
    assert T_threshold == pytest.approx(874.0, abs=3.0)
    # ...and it is BELOW the temperature at which K reaches 1 bar^2, because two
    # gases sharing one bar is 0.25 bar^2 and not 1.
    T_one_bar = 700.0
    while float(arr.equilibrium_pressure(T_one_bar)[0]) < 1.0:
        T_one_bar += 0.5
    assert T_threshold < T_one_bar
    assert T_one_bar == pytest.approx(900.5, abs=2.0)


def test_solvay_step_3_goes_in_its_own_calciner(soda_network):
    """`2 NaHCO3(s) -> Na2CO3(s) + CO2(g) + H2O(g)`, and the catalog's own
    condition for it is `calciner, 450 K`. The threshold this table derives is
    392 K, which is the closest agreement of any row here -- and it is why a
    cake rises."""
    arr = Vessel(soda_network, volume=1.0, T=450.0).solid_state_arrays
    assert float(arr.threshold_temperature(1.01325)[0]) == pytest.approx(
        392.0, abs=3.0
    )
    v = Vessel(soda_network, volume=1.0, T=450.0, T_env=450.0, UA=1.0e4,
               k_vent=1.0e3, atmosphere={})
    v.charge({NAHCOLITE: 0.1}, phase="solid")
    v.run(2000.0, **CONVERGED)
    assert held(v, SODA_ASH) > 0.045                 # of a possible 0.05
    assert held(v, NAHCOLITE) < 0.01
    assert v.state().n_gas[CO2] == pytest.approx(v.state().n_gas[WATER],
                                                 rel=1e-3)


def test_every_declared_row_prices_and_carries_its_own_kinetics(thermo):
    """The guards, over the whole table rather than one row: every mineral can
    sit in a solid block, and every row's barrier clears its own enthalpy.

    ⚠ S9 -- WHAT THIS TEST USED TO ASSERT AND NO LONGER CAN: ``all(nu > 0)`` on
    the gases, i.e. that no row consumes one. Three rows now do, and the bound
    that made that assertion necessary is in
    ``test_a_gas_reactant_is_BOUNDED_now_and_the_old_refusal_measured_why``.
    """
    exothermic = 0
    for decl in ss.SOLID_STATE_REACTIONS:
        priced = ss.price(decl, thermo)                    # raises if unpriced
        # ⚠ the barrier clears the enthalpy on EVERY row, derived or declared --
        # otherwise the reverse barrier clips and K stops being K
        assert priced.Ea >= max(priced.dH, 0.0)
        if priced.dH < 0.0:
            exothermic += 1
            assert decl.Ea is not None and decl.A is not None
        for name, _ in decl.solids:
            rec = MINERALS[name]
            assert rec.Cp_solid is not None and rec.Vm_solid is not None
    # three exothermic rows, all of them S9's, all of them declaring
    assert exothermic == 3

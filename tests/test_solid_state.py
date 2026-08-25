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


import numpy as np
import pytest

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


def kiln(net, T, seconds, charge, volume=1.0, k_vent=1.0e3, sealed=False,
         **kw):
    """A vessel at T holding ``charge`` in its solid heap. Sealed or swept.

    ⚠ The headspace is FILLED unless the vessel is sealed. A flask at exactly
    zero pressure with a 1e3 mol/(bar s) vent inhales 1013 mol/s at t = 0, and
    that transient -- not anything in this milestone -- is the OTHER way into
    the ``num_jac`` overflow above. Measured: 0.01 bar of nitrogen in the
    headspace removes the warning entirely.
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
        v.run(seconds)
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
    assert {p.decl.mechanism for p in priced.values()} == {
        "decarbonation", "dehydration"
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
    for decl in ss.SOLID_STATE_REACTIONS:
        p = ss.price(decl, thermo)
        assert p.Ea == pytest.approx(p.dH)
        assert p.A == ss.DECOMPOSITION_A

    arr, _ = build_solid_state_arrays(LIME_SPECIES)
    assert arr.Ea_rev == pytest.approx(np.zeros(arr.m))
    # ...so the reverse rate constant does not depend on temperature at all.
    # That is what stops a cold flask full of CO2 acquiring an exploding
    # recombination rate from two exponentials that fail to cancel.
    assert arr.A_rev[0] == pytest.approx(4.259e-4, rel=1e-3)


def test_a_gas_reactant_is_refused_rather_than_clipped():
    """⚠ THE AFFINITY FORM IS NOT A RATE LAW FOR A GAS-CONSUMING SURFACE
    REACTION. A gas reactant's pressure sits in the denominator of Q, so an
    atmosphere depleted of it drives the reverse flux without bound. Roasting
    and the five heterogeneous templates that fold a catalyst into a barrier are
    a DIFFERENT mechanism, and they want the mass-action kernel.
    """
    bogus = ss.SolidStateReaction(
        name="bogus-roasting",
        solids=(("sphalerite", -1), ("calcite", +1)),
        gases=(("O=O", -1),),
        mechanism="roasting",
        note="a gas on the reactant side",
    )
    original = ss.SOLID_STATE_REACTIONS
    ss.SOLID_STATE_REACTIONS = (bogus,)
    try:
        arr, report = build_solid_state_arrays(
            [MINERALS["sphalerite"].lattice, CALCITE, "O=O"]
        )
    finally:
        ss.SOLID_STATE_REACTIONS = original
    assert arr.m == 0
    assert any("REFUSED" in line and "reactant side" in line
               for line in report)


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
    """``DECOMPOSITION_A`` is the only free number in the module, and it
    multiplies the whole flux -- forward and reverse alike -- so it divides out
    of ``flux = 0``. A wrong ``A`` moves the clock and nothing else.

    Measured over two decades: the same sealed pressure to seven figures.
    """
    base = ss.DECOMPOSITION_A
    got = []
    try:
        for factor in (0.1, 1.0, 10.0):
            ss.DECOMPOSITION_A = base * factor
            v = kiln(lime_network, 1200.0, 200_000.0, {CALCITE: 0.1},
                     sealed=True)
            got.append(v.partial_pressures()[CO2])
    finally:
        ss.DECOMPOSITION_A = base
    assert got[0] == pytest.approx(got[1], rel=1e-7)
    assert got[2] == pytest.approx(got[1], rel=1e-7)


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
    stalled = kiln(lime_network_air, 1100.0, 20_000.0, {CALCITE: 0.1})
    ran = kiln(lime_network_air, 1150.0, 20_000.0, {CALCITE: 0.1})

    K_lo = float(stalled.solid_state_arrays.equilibrium_pressure(1100.0)[0])
    K_hi = float(ran.solid_state_arrays.equilibrium_pressure(1150.0)[0])
    assert K_lo < stalled.P_ambient < K_hi          # the gate, in one line

    assert 0.10 < (0.1 - held(stalled, CALCITE)) / 0.1 < 0.20
    assert (0.1 - held(ran, CALCITE)) / 0.1 > 0.99


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
    v.run(1000.0)
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
    v.run(20_000.0)
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
        assert after[el] == pytest.approx(amount, rel=1e-7, abs=1e-8)
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

"""Layer 5 -- vessel: phases, energy balance, and what emerges from coupling them.

The tests are in three groups:

  * **laws** -- at rest the vessel must satisfy Raoult and Henry exactly. These
    catch a sign or unit error in the phase model.
  * **conservation** -- a sealed vessel conserves every element across BOTH
    phases. Same guardrail as Layer 3, now with matter moving between phases.
  * **emergence** -- the behaviours nothing in the code states directly: a
    boiling point, a latent-heat plateau, a flask boiling dry, and an exotherm
    that heats itself out of its own equilibrium.
"""

import numpy as np
import pytest

from chemsim.network import build_network
from chemsim.numerics.vessel_integrator import PhaseArrays, VesselIntegrator
from chemsim.vessel import Vessel

ETHANOL, WATER, ACID, ESTER, O2 = "CCO", "O", "CC(=O)O", "CCOC(C)=O", "O=O"


@pytest.fixture
def ester_network(fischer_template, thermo):
    return build_network([ACID, ETHANOL, WATER], [fischer_template], thermo=thermo)


@pytest.fixture
def inert_network(thermo):
    """Water + O2, no templates at all -- pure phase behaviour, nothing reacting."""
    return build_network([WATER, O2], [], thermo=thermo)


@pytest.fixture
def mixture_network(thermo):
    """Ethanol + water, nothing reacting -- for vapour-liquid equilibrium alone."""
    return build_network([ETHANOL, WATER], [], thermo=thermo)


# --------------------------------------------------------------------------
# the laws hold at equilibrium
# --------------------------------------------------------------------------


def test_raoult_holds_at_equilibrium(inert_network):
    v = Vessel(inert_network, volume=1.0, T=298.15, UA=5.0, kla=2.0)
    v.charge({WATER: 5.0})
    v.run(20_000.0)

    p = v.partial_pressures()[WATER]
    x = v.mole_fractions()[WATER]
    psat = v.volatility.get(WATER).coefficient(v.T)
    assert p == pytest.approx(x * psat, rel=1e-4)


def test_henry_holds_at_equilibrium(inert_network):
    """A permanent gas partitions by Henry's law -- same code path as Raoult.

    The measured constant is aqueous, and a dissolved gas now carries an
    activity coefficient in the unsymmetric convention, whose reference state is
    infinite dilution in exactly that solvent. So in water the correction must be
    1 to within the reference fit, and p = x * gamma* * H recovers the tabulated
    constant. In another solvent it deliberately would not -- see test_activity.
    """
    v = Vessel(inert_network, volume=1.0, T=298.15, UA=5.0, kla=2.0)
    v.charge({WATER: 5.0})
    v.charge({O2: 0.008}, phase="gas")
    v.run(20_000.0)

    p = v.partial_pressures()[O2]
    x = v.mole_fractions()[O2]
    gamma = v.activity_coefficients()[O2]
    H = v.volatility.get(O2).coefficient(v.T)

    assert gamma == pytest.approx(1.0, abs=1e-3), "water is the reference solvent"
    assert p / (x * gamma) == pytest.approx(H, rel=1e-4)


def test_dissolved_oxygen_is_physically_right(inert_network):
    """Air-saturated water holds ~0.25-0.28 mM O2 at 298 K. This is the number
    that decides whether an open flask oxidizes, so it has to be real."""
    v = Vessel(inert_network, volume=1.0, T=298.15, UA=5.0, kla=2.0)
    v.charge({WATER: 5.0})
    v.charge({O2: 0.008}, phase="gas")   # ~0.21 bar in the headspace
    v.run(20_000.0)

    assert 0.15e-3 < v.concentrations()[O2] < 0.45e-3


def test_gas_solubility_falls_with_temperature(inert_network):
    """Warm water holds less oxygen -- van 't Hoff, via the Henry coefficient."""
    dissolved = []
    for T in (288.15, 328.15):
        v = Vessel(inert_network, volume=1.0, T=T, T_env=T, UA=50.0, kla=2.0)
        v.charge({WATER: 5.0})
        v.charge({O2: 0.008}, phase="gas")
        v.run(20_000.0)
        dissolved.append(v.concentrations()[O2])
    assert dissolved[0] > dissolved[1]


# --------------------------------------------------------------------------
# conservation
# --------------------------------------------------------------------------


def test_sealed_vessel_conserves_every_element(ester_network):
    """Reaction plus evaporation plus condensation, across two phases, must not
    create or destroy atoms."""
    v = Vessel(
        ester_network, volume=2.0, T=330.0, T_env=330.0, UA=1.0,
        kla=2.0, k_vent=0.0,          # sealed: nothing may leave
    )
    v.charge({ACID: 2.0, ETHANOL: 2.0})

    def totals(state):
        out = {}
        for smi in v.species:
            n = state.total(smi)
            for el, k in ester_network.molecules[smi].element_counts().items():
                out[el] = out.get(el, 0.0) + k * n
        return out

    start = totals(v.state())
    v.run(5_000.0)
    end = totals(v.state())

    for el in start:
        assert np.isclose(start[el], end[el], rtol=1e-5), f"{el}: {start[el]} -> {end[el]}"


def test_venting_removes_matter_only_above_ambient(ester_network):
    """A vessel below ambient pressure must not leak; that would be a mass sink."""
    v = Vessel(
        ester_network, volume=2.0, T=300.0, T_env=300.0, UA=5.0, kla=2.0
    )
    v.charge({ETHANOL: 1.0})
    before = sum(v.state().n_liquid.values()) + sum(v.state().n_gas.values())
    v.run(3_000.0)
    after = sum(v.state().n_liquid.values()) + sum(v.state().n_gas.values())

    assert v.pressure < v.P_ambient
    assert after == pytest.approx(before, rel=1e-6)


# --------------------------------------------------------------------------
# emergence: none of the following is stated anywhere in the code
# --------------------------------------------------------------------------


def test_a_heated_solvent_pins_at_its_own_boiling_point(ester_network):
    """Ethanol boils at 351.4 K. Nothing in the integrator knows that: the
    temperature stalls because evaporation runs away once the vapour pressure
    reaches ambient, and the latent heat absorbs the hotplate."""
    v = Vessel(ester_network, volume=0.5, T=298.15, UA=0.5, Q_input=60.0, kla=5.0)
    v.charge({ETHANOL: 3.0})
    v.run(1_200.0)

    assert v.is_boiling
    assert v.T == pytest.approx(351.4, abs=1.5)


def test_the_plateau_agrees_with_the_predicted_bubble_point(ester_network):
    """The dynamics and the static prediction must be the same physics."""
    v = Vessel(ester_network, volume=0.5, T=298.15, UA=0.5, Q_input=60.0, kla=5.0)
    v.charge({ETHANOL: 3.0})
    predicted = v.bubble_point()
    v.run(1_200.0)
    assert v.T == pytest.approx(predicted, abs=0.5)


def test_a_mixture_boils_below_its_less_volatile_component(ester_network):
    """Raoult again, but as a statement about the mixture: adding volatile
    ethanol to acetic acid (Tb 391 K) must drag the bubble point down."""
    pure_acid = Vessel(ester_network, volume=0.5, T=298.15)
    pure_acid.charge({ACID: 3.0})

    mixture = Vessel(ester_network, volume=0.5, T=298.15)
    mixture.charge({ACID: 1.5, ETHANOL: 1.5})

    assert mixture.bubble_point() < pure_acid.bubble_point()


def test_the_vapour_is_enriched_in_the_volatile_component(mixture_network):
    """Distillation, for free. A 50/50 ethanol/water liquid stands in equilibrium
    with a vapour that is ~70% ethanol -- which is the entire reason distillation
    works, and it falls out of the phase model with no separation model anywhere.

    The enrichment is now larger than ideal Raoult alone would give, because
    ethanol and water dislike each other: the activity coefficients push both
    components into the vapour. Where that stops -- the azeotrope -- is in
    test_activity.py; here we only assert that the vapour is richer, which was
    true before activity coefficients and is still true after.
    """
    v = Vessel(mixture_network, volume=1.0, T=298.15, T_env=298.15, UA=5.0, kla=2.0)
    v.charge({ETHANOL: 2.0, WATER: 2.0})
    v.run(20_000.0)

    x = v.mole_fractions()
    p = v.partial_pressures()
    y_ethanol = p[ETHANOL] / sum(p.values())

    assert x[ETHANOL] == pytest.approx(0.5, abs=0.01)
    assert y_ethanol > 0.65, "vapour must be richer in ethanol than the liquid"

    alpha = (p[ETHANOL] / p[WATER]) / (x[ETHANOL] / x[WATER])
    assert 1.5 < alpha < 6.0

    # The signature of a positive-deviation mixture: BOTH components are pushed
    # out of the liquid, so the total pressure exceeds what ideal Raoult would
    # predict. Note this does not raise the relative volatility -- water's gamma
    # is the larger of the two here, so alpha actually falls below the
    # vapour-pressure ratio. That is why the azeotrope is where it is.
    gamma = v.activity_coefficients()
    assert gamma[ETHANOL] > 1.0 and gamma[WATER] > 1.0
    ideal_total = sum(
        x[s] * v.volatility.get(s).coefficient(v.T) for s in (ETHANOL, WATER)
    )
    assert sum(p.values()) > ideal_total


def test_boil_off_rate_matches_the_latent_heat_balance(ester_network):
    """At the plateau every net watt goes into vaporization: the measured
    boil-off rate must equal (Q_in - losses) / Hvap(T)."""
    Q, UA, T_env = 60.0, 0.5, 298.15
    v = Vessel(ester_network, volume=0.5, T=298.15, T_env=T_env, UA=UA,
               Q_input=Q, kla=5.0)
    v.charge({ETHANOL: 3.0})
    v.run(900.0)                       # get onto the plateau
    assert v.is_boiling

    n0 = v.state().n_liquid[ETHANOL]
    v.run(300.0)
    measured = (n0 - v.state().n_liquid[ETHANOL]) / 300.0   # mol/s

    i = v.species.index(ETHANOL)
    Hvap = v.integrator.latent_heat(v.T)[i]
    expected = (Q - UA * (v.T - T_env)) / Hvap
    assert measured == pytest.approx(expected, rel=0.1)


def test_a_flask_boiled_dry_superheats(ester_network):
    """The plateau is not a temperature cap -- it lasts exactly as long as there
    is liquid to absorb the heat, and not one second longer."""
    v = Vessel(ester_network, volume=0.5, T=340.0, UA=0.2, Q_input=80.0, kla=5.0)
    v.charge({ETHANOL: 0.3})

    v.run(150.0)
    assert v.is_boiling
    assert v.T == pytest.approx(351.4, abs=1.5)

    v.run(200.0)
    assert not v.is_boiling
    assert sum(v.state().n_liquid.values()) < 1e-6
    assert v.T > 380.0, "a dry flask on a hotplate must keep heating"


def test_an_insulated_exotherm_heats_itself_and_loses_yield(ester_network, thermo):
    """The coupling that makes this worth building: the same charge, in a vessel
    that cannot shed heat, reaches a HIGHER temperature and a LOWER conversion --
    because the reaction's own heat pushes its equilibrium constant down.
    Le Chatelier, arrived at from a hotplate and a heat-transfer coefficient.

    The effect is DELIBERATELY small here, and the size is itself the check.
    Fischer esterification in the liquid is nearly thermoneutral -- measured
    dH = -3.2 kJ/mol, since all four species are stabilised by condensing and
    the two sides very nearly cancel -- so 4 mol releases only ~13 kJ and the
    flask warms about 8 K. This test used to demand 20 K, which it got from
    Joback pricing the reaction at -18.4 kJ/mol, the ideal-gas value. Curated
    liquid formation data removed that, so the threshold moved to what the
    chemistry actually does. If it ever needs a big exotherm again, use a
    reaction that has one rather than restoring the number."""
    results = {}
    for label, UA in (("cooled", 2.0), ("insulated", 0.02)):
        v = Vessel(ester_network, volume=1.0, T=298.15, T_env=298.15, UA=UA, kla=2.0)
        v.charge({ACID: 4.0, ETHANOL: 4.0})
        v.run(7_200.0)
        results[label] = (v.T, v.state().n_liquid[ESTER])

    assert results["insulated"][0] > results["cooled"][0] + 5.0
    assert results["insulated"][1] < results["cooled"][1]


def test_temperature_relaxes_to_the_room_at_the_right_rate(inert_network):
    """No reaction, no phase change: pure Newton cooling. Checks the energy
    balance's denominator (the heat capacity) as well as its numerator."""
    v = Vessel(
        inert_network, volume=1.0, T=350.0, T_env=300.0, UA=2.0,
        kla=0.0,                       # freeze the phase model out of it
        heat_capacity=0.0,             # contents only, so tau is predictable
    )
    v.charge({WATER: 5.0})

    Cp = 5.0 * v.condensed.get(WATER).Cp(350.0)     # J/K
    tau = Cp / 2.0
    v.run(tau)

    expected = 300.0 + 50.0 * np.exp(-1.0)
    assert v.T == pytest.approx(expected, rel=0.02)


def test_a_hotplate_below_boiling_reaches_a_steady_state(inert_network):
    """Q_input = UA*(T - T_env) once the transient dies."""
    v = Vessel(inert_network, volume=1.0, T=298.15, T_env=298.15, UA=4.0,
               Q_input=40.0, kla=0.0)
    v.charge({WATER: 5.0})
    v.run(5_000.0)
    assert v.T == pytest.approx(298.15 + 40.0 / 4.0, rel=0.01)


# --------------------------------------------------------------------------
# contracts
# --------------------------------------------------------------------------


def test_energy_balance_refuses_a_network_with_no_enthalpies(ester_network):
    """Without reaction enthalpies the vessel would run adiabatically and silently
    report no exotherm at all. That must be an error, not a quiet zero.

    An irreversible template needs no thermochemistry to build, so its network
    genuinely has none to hand on -- exactly the case that must be caught.
    """
    from chemsim.reactions import ReactionTemplate

    bare = build_network(
        [ETHANOL],
        [ReactionTemplate(
            name="dehydration",
            smarts="[CX4:1][CX4:2][OX2H1:3]>>[C:1]=[C:2].[OH2:3]",
            A=1.0e8, Ea=90_000,
        )],
    )
    kin = bare.to_arrays()
    assert np.isnan(kin.dH).all(), "no provider anywhere -> enthalpies unknown"

    v = Vessel(ester_network, volume=1.0)
    with pytest.raises(ValueError, match="reaction enthalpies"):
        VesselIntegrator(kin, v.phases, v.conditions)


def test_phase_arrays_carry_no_chemistry(ester_network):
    """The Layer 5 -> 4 contract: numpy only, no molecules, no SMILES."""
    v = Vessel(ester_network, volume=1.0)
    for name, value in vars(v.phases).items():
        assert isinstance(value, np.ndarray), f"{name} is {type(value)}"
    assert isinstance(v.phases, PhaseArrays)


def test_charging_an_unknown_species_is_rejected(ester_network):
    v = Vessel(ester_network, volume=1.0)
    with pytest.raises(KeyError, match="not a species in this network"):
        v.charge({"c1ccccc1": 1.0})

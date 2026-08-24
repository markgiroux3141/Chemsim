"""The ideal-gas -> liquid standard-state correction.

Group-contribution thermochemistry is ideal-gas data. Nearly every reaction here
runs in a liquid. Using the gas numbers unmodified asserts that solvation is free,
which is the same class of error ideal Raoult made about vapour pressure.

Three things need guarding:

  * the correction is right in magnitude and sign, and its enthalpy half comes
    from the same vapour-pressure curve as its Gibbs half, so the entropy derived
    from the pair is real;
  * it is applied to liquid-phase reactions and NOT to gas-phase ones;
  * it does not move pH. Ion formation data is back-derived from measured pKa
    against the acid, so the anchor has to be taken in the same standard state --
    get that wrong and every pKa shifts by about three units.
"""

import math

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties import standard_state as ss
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.reactions import ReactionTemplate, equilibrium_constant
from chemsim.vessel import Vessel

WATER, ETHANOL, ACID, ESTER = "O", "CCO", "CC(=O)O", "CCOC(C)=O"


@pytest.fixture(scope="module")
def volatility():
    return VolatilityProvider(ThermochemistryProvider())


# --------------------------------------------------------------------------
# the per-species shift
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "smiles,measured",
    [("O", 44.0), ("CCO", 42.3), ("CCOC(C)=O", 35.1), ("CO", 37.4), ("CC(C)=O", 31.0)],
)
def test_vaporization_enthalpy_comes_from_the_vapour_pressure_curve(
    volatility, smiles, measured
):
    """Clausius-Clapeyron on our own Antoine coefficients, not a second
    correlation. Using one curve for both halves of the shift is what makes the
    entropy that falls out of them meaningful."""
    dHvap = ss.enthalpy_of_vaporization(volatility.get(smiles), 298.15)
    assert dHvap == pytest.approx(measured, rel=0.08)


def test_the_gibbs_shift_is_negative_for_anything_that_boils(volatility):
    """Psat < 1 bar at room temperature, so R T ln(Psat) < 0: a molecule is
    cheaper to make as a liquid than as an isolated gas. Anything else would mean
    the species boils spontaneously."""
    for smiles in (WATER, ETHANOL, ACID, ESTER, "CC(C)=O"):
        s = ss.shift(smiles, volatility)
        assert s.applied
        assert s.dGf < 0.0
        assert s.dHf < 0.0, "condensing releases heat"


def test_an_involatile_species_is_refused_and_says_why(volatility):
    """A = -30 gives Psat = 1e-30 bar, so R T ln(Psat) would read -171 kJ/mol and
    wreck every equilibrium it touched. Ions and decomposing solids keep whatever
    basis their data was derived on."""
    s = ss.shift("[OH-]", volatility)
    assert not s.applied
    assert "no volatility model" in s.reason


def test_a_species_below_the_vapour_pressure_floor_is_refused(volatility):
    """A discovered polyester oligomer extrapolates to ~1e-20 bar, which is a
    correlation far past its data rather than a measurement. Left alone, and
    named."""
    oligomer = "O=C(O)CCC(=O)OCCOC(=O)CCC(=O)OCCOC(=O)CCC(=O)O"
    s = ss.shift(oligomer, volatility)
    assert not s.applied
    assert "below the" in s.reason and "floor" in s.reason

    # ... while benzoic acid, the least volatile species anyone would defend a
    # shift for, is six orders of magnitude clear of that floor.
    benzoic = ss.shift(Molecule.from_smiles("OC(=O)c1ccccc1").smiles, volatility)
    assert benzoic.applied
    assert benzoic.dGf < -20.0


def test_a_dissolved_gas_shifts_the_other_way(volatility):
    """Its Antoine coefficients hold a Henry constant, which is much LARGER than
    1 bar, so the shift is positive: a gas is expensive to dissolve. Same
    expression, opposite sign, no special case."""
    s = ss.shift("O=O", volatility)
    assert s.applied
    assert s.dGf > 0.0


# --------------------------------------------------------------------------
# the reaction-level shift
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def thermo_mod():
    return ThermochemistryProvider()


FISCHER = ReactionTemplate(
    name="fischer",
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000, reversible=True,
)


def _fischer_K(thermo, T, liquid):
    net = build_network(
        [ACID, ETHANOL, WATER], [FISCHER], thermo=thermo,
        liquid_standard_state=liquid,
    )
    fwd = next(r for r in net.reactions if r.name == "fischer")
    return equilibrium_constant(fwd, thermo, T, net.volatility)


def test_esterification_K_moves_toward_the_measured_value(thermo_mod):
    """The headline. Esterification in the VAPOUR is strongly favoured -- K ~ 330
    on measured ideal-gas data -- and in the liquid it is not, because all four
    species are stabilised by condensing and the two sides do not cancel. The
    standard-state correction is the whole of that factor of ~38, and it lands
    within a factor of 2 of the ~4-8 measured in the liquid.

    These numbers used to read 19.4 -> 8.1, which looked like a much smaller
    correction only because Joback put the gas-phase constant 17x too low."""
    ideal_gas = _fischer_K(thermo_mod, 298.15, liquid=False)
    liquid = _fischer_K(thermo_mod, 298.15, liquid=True)

    assert ideal_gas == pytest.approx(333.0, rel=0.05)
    assert liquid == pytest.approx(8.66, rel=0.05)
    assert abs(liquid - 4.0) < abs(ideal_gas - 4.0), "must move toward experiment"


def test_the_correction_is_a_real_shift_not_a_rescaling(thermo_mod):
    """It changes enthalpy and Gibbs energy separately, so the reaction entropy
    changes too. A pure K rescaling would leave dH untouched and would be a fudge
    factor rather than a change of standard state."""
    from chemsim.reactions.thermo import reaction_deltas

    net = build_network([ACID, ETHANOL, WATER], [FISCHER], thermo=thermo_mod)
    fwd = next(r for r in net.reactions if r.name == "fischer")

    dH_gas, dG_gas = reaction_deltas(fwd, thermo_mod, None)
    dH_liq, dG_liq = reaction_deltas(fwd, thermo_mod, net.volatility)
    assert dH_liq != pytest.approx(dH_gas, rel=1e-6)
    assert dG_liq != pytest.approx(dG_gas, rel=1e-6)


def test_a_gas_phase_reaction_keeps_the_ideal_gas_basis(thermo_mod):
    """For a reaction that genuinely runs in the vapour, the ideal-gas standard
    state is the correct one and must be left alone."""
    from chemsim.reactions.thermo import reaction_deltas

    gas_template = ReactionTemplate(
        name="gas_fischer", smarts=FISCHER.smarts,
        A=1.0e6, Ea=50_000, reversible=True, phase="gas",
    )
    net = build_network([ACID, ETHANOL, WATER], [gas_template], thermo=thermo_mod)
    fwd = next(r for r in net.reactions if r.name == "gas_fischer")

    assert reaction_deltas(fwd, thermo_mod, net.volatility) == reaction_deltas(
        fwd, thermo_mod, None
    )


# --------------------------------------------------------------------------
# the thing that must NOT move
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def acid_thermo():
    return electrolyte_provider()


def _pH(thermo, species, charge):
    net = build_network(species, dissociation_templates(), thermo=thermo,
                        max_species=60)
    v = Vessel(net, volume=1.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)
    v.charge(charge)
    v.run(4_000.0)
    return v.pH


def test_pH_survives_the_correction(acid_thermo):
    """The load-bearing test for the whole change. Ion formation data is
    back-derived from measured pKa against the acid's value, so if the acid moves
    into the liquid standard state and the anchor does not follow it, every pKa
    shifts by ~3 units -- acetic acid and water are each worth ~9 kJ/mol of
    vaporization Gibbs energy and both sit on the same side of the reaction."""
    assert _pH(acid_thermo, [WATER], {WATER: 55.3}) == pytest.approx(7.00, abs=0.05)
    assert _pH(
        acid_thermo, [WATER, ACID], {WATER: 55.3, ACID: 0.1}
    ) == pytest.approx(2.88, abs=0.05)


def test_a_half_neutralised_acid_still_sits_exactly_at_its_pKa(acid_thermo):
    """The sharpest of the pH checks, because it has no concentration dependence
    to hide behind: at half neutralisation pH = pKa identically."""
    pH = _pH(
        acid_thermo,
        [WATER, ACID, "[OH-]", "[Na+]"],
        {WATER: 55.3, ACID: 0.1, "[OH-]": 0.05, "[Na+]": 0.05},
    )
    assert pH == pytest.approx(4.76, abs=0.05)


def test_the_ion_anchor_is_taken_in_the_liquid_standard_state():
    """Directly, rather than through a simulation. Acetate is anchored on acetic
    acid, so moving the acid into the liquid standard state must move acetate by
    exactly the acid's own shift -- that displacement is what keeps the
    dissociation Gibbs energy, and hence the pKa, invariant."""
    from chemsim.properties.electrolyte import _NO_SHIFT_VOLATILITY, ion_thermochemistry

    base = ThermochemistryProvider()
    vol = VolatilityProvider(base)
    acetate = Molecule.from_smiles("CC(=O)[O-]").smiles

    shifted = ion_thermochemistry(base, volatility=vol)[acetate]
    unshifted = ion_thermochemistry(base, volatility=_NO_SHIFT_VOLATILITY)[acetate]

    acid_shift = ss.shift(ACID, vol)
    assert acid_shift.applied and acid_shift.dGf < -5.0
    assert shifted.Gf - unshifted.Gf == pytest.approx(acid_shift.dGf, rel=1e-9)
    assert shifted.Hf - unshifted.Hf == pytest.approx(acid_shift.dHf, rel=1e-9)


def test_water_autoionization_still_gives_pKw_14(acid_thermo):
    """Kw is derived, not stored, so it is a check on the whole chain."""
    from chemsim.reactions.thermo import equilibrium_constant_c

    net = build_network([WATER], dissociation_templates(), thermo=acid_thermo,
                        max_species=60)
    fwd = next(r for r in net.reactions if r.name == "water_autoionization")
    K = equilibrium_constant_c(fwd, acid_thermo, 298.15, net.volatility)
    # K is written with two waters on the left, so Kw = K * [H2O]^2.
    C_water = 1.0 / 0.01807
    assert -math.log10(K * C_water * C_water) == pytest.approx(14.0, abs=0.1)

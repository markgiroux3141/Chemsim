"""The element and mineral floor: the class fix, and the guard that keeps it.

The point of these tests is not that S8 has a particular number. It is that
**no estimator can ever price an element or an ion again**, which is what
distinguishes a class fix from the species-by-species one it replaced.
"""

from __future__ import annotations

import math

import pytest

from chemsim.constants import P_STD_BAR, R
from chemsim.matter import Molecule
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties import standard_state
from chemsim.properties.benson import BensonError
from chemsim.properties.benson import estimate as benson_estimate
from chemsim.properties.electrolyte import electrolyte_provider
from chemsim.properties.element_data import (
    ELEMENTAL,
    REFERENCE_STATES,
    element_of,
    is_monatomic,
)
from chemsim.properties.joback import JobackError
from chemsim.properties.joback import estimate as joback_estimate
from chemsim.properties.mineral_data import MINERALS

T_REF = 298.15


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def volatility(thermo):
    return VolatilityProvider(thermo)


# ---------------------------------------------------------------------------
# the detector
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("smiles,expected", [
    ("[H][H]", "H"),
    ("O=O", "O"),
    ("S1SSSSSSS1", "S"),
    ("[C]", "C"),
    ("[O-][O+]=O", "O"),          # ozone: elemental, not a reference state
    ("C", None),                  # methane is C1H4, not elemental carbon
    ("c1ccccc1", None),           # benzene is C6H6
    ("[Cl-]", None),              # charged -- the ion guard's business
    ("O=[N+]([O-])c1ccccc1", None),   # formal charges, net neutral, a molecule
])
def test_element_of_identifies_only_single_element_neutrals(smiles, expected):
    assert element_of(Molecule.from_smiles(smiles)) == expected


def test_monatomic_is_distinguished_from_polyatomic():
    assert is_monatomic(Molecule.from_smiles("[S]"))
    assert not is_monatomic(Molecule.from_smiles("S1SSSSSSS1"))


# ---------------------------------------------------------------------------
# THE CLASS FIX: an estimator may never price an element
# ---------------------------------------------------------------------------
def test_every_gaseous_reference_state_is_exactly_zero(thermo):
    """FREE AND EXACT -- so this asserts equality, not approximate equality."""
    for smi, rec in ELEMENTAL.items():
        if not (rec.reference_state and rec.reference_phase == "g"):
            continue
        data = thermo.get(smi)
        assert data.Hf == 0.0, f"{rec.name} Hf"
        assert data.Gf == 0.0, f"{rec.name} Gf"


def test_the_estimators_DISAGREE_with_every_pinned_reference_state():
    """The detection test, and the reason the class fix exists.

    An estimator returning a non-zero formation energy for a reference state is
    a DETECTABLE error rather than a judgement call. This test asserts the error
    is real and large -- so if a future estimator change made Joback agree with
    the definition, this test would fail and say so, which is information.
    """
    caught = {}
    for smi, rec in ELEMENTAL.items():
        if not (rec.reference_state and rec.reference_phase == "g"):
            continue
        try:
            est = joback_estimate(Molecule.from_smiles(smi))
        except JobackError:
            continue
        if est.Hf is None:
            continue
        caught[rec.name] = est.Hf
    # Joback prices exactly the halogens among the gaseous reference states, and
    # gets both of them wrong by enough to matter: -74.81 kJ/mol for Cl2 is a
    # factor of ~1e13 in any K.
    assert "chlorine" in caught and abs(caught["chlorine"]) > 50.0
    assert "fluorine" in caught and abs(caught["fluorine"]) > 50.0


def test_joback_still_misprices_S8_and_the_provider_no_longer_asks_it():
    """The headline: the estimate is still there, and nothing consults it."""
    est = joback_estimate(Molecule.from_smiles("S1SSSSSSS1"))
    assert est.Gf == pytest.approx(275.96, abs=0.1)      # the old, wrong answer
    data = ThermochemistryProvider().get("S1SSSSSSS1")
    assert data.Gf == pytest.approx(48.68, abs=0.1)      # gaseous S8, JANAF
    assert "JANAF" in data.source
    assert "Joback" not in data.source


@pytest.mark.parametrize("smiles", ["[S]", "[C]", "[Hg]", "[Fe]", "S=S"])
def test_an_uncurated_elemental_species_refuses_by_name(smiles):
    provider = ThermochemistryProvider()
    with pytest.raises(ValueError) as exc:
        provider.get(smiles)
    message = str(exc.value)
    assert "refusing to price" in message
    # A refusal must be actionable: it names either the reference state to
    # charge instead or the table to add the species to.
    assert "element_data" in message or "standard state is" in message


def test_a_monatomic_refusal_names_the_reference_state_to_charge_instead():
    provider = ThermochemistryProvider()
    with pytest.raises(ValueError, match="S1SSSSSSS1"):
        provider.get("[S]")


# ---------------------------------------------------------------------------
# THE CLASS FIX, second half: an estimator may never price an ion
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("smiles", ["[Cl-]", "[Br-]", "[F-]", "[I-]"])
def test_the_halide_ions_refuse_under_the_plain_provider(smiles):
    """These four were the whole of the ion mispricing, and they were silent.

    Joback fragments a halide ion happily and returns a number: chloride at
    Gf -10.43 against the ion table's -111.73. So a network built WITHOUT
    electrolyte support disagreed with one built with it by 101 kJ/mol for the
    same species -- and iodide was priced by Joback in BOTH, because HI is not
    in the pKa table, so it had no second opinion at all.
    """
    assert joback_estimate(Molecule.from_smiles(smiles)).Gf is not None
    with pytest.raises(ValueError, match="net charge"):
        ThermochemistryProvider().get(smiles)


def test_a_charged_species_still_prices_when_the_ion_table_supplies_it():
    ions = electrolyte_provider()
    assert ions.get("[Cl-]").Gf == pytest.approx(-111.7, abs=0.5)
    assert ions.get("[OH-]").Gf == pytest.approx(-137.3, abs=0.5)


def test_a_net_neutral_molecule_with_formal_charges_is_untouched(thermo):
    """Nitrobenzene must keep pricing -- the guard is on NET charge."""
    data = thermo.get("O=[N+]([O-])c1ccccc1")
    assert data.Gf is not None


def test_a_salt_pair_sums_to_zero_charge_and_is_caught_anyway(thermo):
    """The hole net charge alone leaves: [Na+].[Cl-] is neutral overall."""
    with pytest.raises(ValueError) as exc:
        thermo.get("[Na+].[Cl-]")
    assert "rock salt" in str(exc.value)
    assert "ions" in str(exc.value)


# ---------------------------------------------------------------------------
# THE INDEPENDENT CROSS-CHECK on a condensed reference state
# ---------------------------------------------------------------------------
def _reference_residual(smi, rec, thermo, volatility):
    """Gf(g) + RT ln(Psat/P0) - dGfus, which must be 0 for a reference state."""
    data = thermo.get(smi)
    shift = standard_state.shift(smi, volatility, T_REF)
    assert shift.applied, f"{rec.name}: no standard-state shift available"
    dgfus = 0.0
    if rec.reference_phase == "s" and rec.Hfus and rec.Tm:
        dgfus = rec.Hfus * max(0.0, 1.0 - T_REF / rec.Tm)
    return data.Gf + shift.dGf - dgfus


def test_bromine_and_iodine_close_their_own_cross_check(thermo, volatility):
    """The check that would have caught the values this repo used to carry.

    With the OLD pinned Gf(g) = 0.0 the residuals are -3.14 and -19.15 kJ/mol.
    """
    for smi, tol in (("BrBr", 0.5), ("II", 0.5)):
        rec = ELEMENTAL[smi]
        assert abs(_reference_residual(smi, rec, thermo, volatility)) < tol, rec.name


def test_the_check_would_have_FAILED_on_the_old_pinned_zeros(volatility):
    """Not a tautology: the cross-check has to be able to reject."""
    for smi, expected in (("BrBr", -3.14), ("II", -19.15)):
        rec = ELEMENTAL[smi]
        shift = standard_state.shift(smi, volatility, T_REF)
        dgfus = 0.0
        if rec.reference_phase == "s" and rec.Hfus and rec.Tm:
            dgfus = rec.Hfus * max(0.0, 1.0 - T_REF / rec.Tm)
        old = 0.0 + shift.dGf - dgfus
        assert old == pytest.approx(expected, abs=0.5)
        assert abs(old) > 3.0


def test_sulfurs_cross_check_is_a_BOUND_and_is_reported_as_one(thermo, volatility):
    """S8's residual is ~3 kJ/mol, and the reason is worth pinning.

    Lee-Kesler is being extrapolated from Tb = 717.8 K down to Tr = 0.23, and
    liquid sulfur's vapour is not S8 -- it is an S8/S6/S2 equilibrium. So this
    row is a sanity bound rather than a confirmation, and S8's vapour-pressure
    curve is the weakest number in chain 2. Pinned so that "weakest" stays a
    measured claim.
    """
    residual = _reference_residual("S1SSSSSSS1", ELEMENTAL["S1SSSSSSS1"],
                                   thermo, volatility)
    assert 1.0 < abs(residual) < 8.0


def test_a_gaseous_reference_state_has_no_cross_check_and_needs_none(volatility):
    """Above Tc the 'Psat' is a supercritical extrapolation, so the identity
    does not apply -- and it does not need to, because the value is exact."""
    shift = standard_state.shift("N#N", volatility, T_REF)
    assert shift.applied
    assert shift.dGf > 20.0            # nonsense as a vaporisation energy
    assert ThermochemistryProvider().get("N#N").Gf == 0.0   # still exact


# ---------------------------------------------------------------------------
# derivation consistency
# ---------------------------------------------------------------------------
def test_every_derived_Gf_is_consistent_with_its_own_Hf_and_S0():
    """Gf must be recoverable from Hf and the reference entropies.

    This is what "DERIVED, not transcribed" buys: the two halves of an entry
    cannot drift apart, because one is computed from the other.
    """
    for smi, rec in ELEMENTAL.items():
        if rec.reference_state and rec.reference_phase == "g":
            continue                            # exactly zero, nothing to derive
        # dS_rxn implied by the stored pair
        implied = (rec.Hf - rec.Gf) * 1000.0 / T_REF
        # dS_rxn from the reference states, if the species' own S0 is recovered
        ref = REFERENCE_STATES[rec.element]
        own_S0 = implied + (rec.n_atoms / ref.atoms_per_unit) * ref.S0
        # Absolute entropies are positive and, for these species, in a sane band.
        assert 100.0 < own_S0 < 500.0, f"{rec.name}: implied S0 = {own_S0}"


def test_the_element_table_is_the_only_home_for_an_element(thermo):
    """No element may also sit in the hand-written curated table.

    Two homes is how Br2 came to be pinned at 0.0 while the measured ideal-gas
    value was +30.90: one table said 'element, therefore zero' and nothing
    checked which PHASE that zero belonged to.
    """
    for smi, rec in ELEMENTAL.items():
        data = thermo.get(smi)
        assert data.Hf == rec.Hf
        assert data.Gf == rec.Gf
        assert rec.name in data.source


# ---------------------------------------------------------------------------
# minerals: the lattice verdict
# ---------------------------------------------------------------------------
def test_the_fusion_law_is_wrong_for_a_lattice_in_BOTH_directions():
    """The measurement that decided a lattice does not enter the phase model.

    If this ever comes back within an order of magnitude, an ionic dissolution
    mechanic has become worth building and this verdict should be revisited.
    """
    ratios = [
        rec.fusion_law_bound[2] for rec in MINERALS.values()
        if rec.fusion_law_bound is not None
    ]
    assert len(ratios) >= 5
    assert min(ratios) < 0.01, "no salt is badly UNDER-dissolved any more"
    assert max(ratios) > 2.0, "no salt is badly OVER-dissolved any more"
    assert max(ratios) / min(ratios) > 1000.0


def test_every_mineral_records_the_ions_it_dissolves_into():
    for name, rec in MINERALS.items():
        assert rec.ions, name
        for ion in rec.ions:
            assert Molecule.from_smiles(ion).smiles == ion, f"{name}: {ion}"


def test_a_mineral_resolves_ION_BY_ION_under_the_electrolyte_provider():
    """The representation the refusal points at has to actually work."""
    ions = electrolyte_provider()
    for name in ("saltpetre", "rock salt", "potassium bisulfate"):
        for ion in MINERALS[name].ions:
            assert ions.get(ion).Gf is not None, f"{name}: {ion}"


def test_the_derived_solid_Gf_reproduces_the_tabulated_value():
    """Sanity anchors against CRC's own tabulated Gf(s), which was NOT used.

    Five land within 0.25 kJ/mol. K2CO3 is 1.8 out, and that is a finding about
    the source rather than about the derivation: CRC's own K2CO3 entry is not
    internally consistent between its Hf, S0 and Gf, which is exactly what
    deriving rather than transcribing exposes.
    """
    anchors = {
        "calcite": -1129.1, "quicklime": -603.3, "rock salt": -384.1,
        "saltpetre": -394.9, "caustic soda": -379.7,
    }
    for name, tabulated in anchors.items():
        assert MINERALS[name].Gf_solid == pytest.approx(tabulated, abs=0.3), name
    assert MINERALS["potash"].Gf_solid == pytest.approx(-1063.5, abs=2.0)


def test_pyrite_is_absent_and_that_is_a_source_limit(thermo):
    """FeS2 has a tabulated enthalpy and NO entropy in any source consulted, so
    its Gf cannot be derived and mixing two tabulations is forbidden."""
    assert "pyrite" not in MINERALS
    with pytest.raises(ValueError):
        thermo.get("[Fe+2].[S-][S-]")


# ---------------------------------------------------------------------------
# the elements still behave as species
# ---------------------------------------------------------------------------
def test_sulfur_melts_and_boils_where_it_is_measured_to(thermo, volatility):
    data = thermo.get("S1SSSSSSS1")
    assert data.Tm == pytest.approx(388.36, abs=0.5)     # 115.2 C
    assert data.Tb == pytest.approx(717.76, abs=0.5)     # 444.6 C
    assert data.Hfus is not None and data.Hfus > 0.0
    assert data.Hvap is not None and data.Hvap > 0.0
    # A latent heat of zero would let sulfur evaporate for free -- the vessel
    # reads ``(t.Hvap or 0.0)``, so a missing value is silent rather than loud.
    vol = volatility.get("S1SSSSSSS1")
    assert vol.volatile


def test_the_boiling_point_comes_back_out_of_the_fitted_curve(volatility):
    """Tb goes in; the Antoine fit must say the species boils at 1 atm there.

    Not an independent check on Tc or Pc -- omega is derived by inverting
    Lee-Kesler at Tb precisely so this holds -- but it does catch a fit that
    did not take, which for an extrapolation as long as sulfur's is worth
    having.
    """
    for smi, Tb in (("S1SSSSSSS1", 717.76), ("FF", 85.04),
                    ("O=[O+][O-]", 161.8)):
        p = volatility.get(smi).coefficient(Tb)
        assert p == pytest.approx(1.01325, rel=0.05), smi


def test_benson_refuses_every_element_and_says_why():
    """Benson's own guard is independent of ours, and both should hold."""
    for smi in ("S1SSSSSSS1", "ClCl", "[S]"):
        with pytest.raises((BensonError, ValueError)):
            benson_estimate(Molecule.from_smiles(smi))


def test_R_and_P_STD_are_the_ones_the_cross_check_used():
    """Guard against the check silently changing basis."""
    assert R == pytest.approx(8.314, abs=0.01)
    assert P_STD_BAR == pytest.approx(1.0, abs=0.02)
    assert math.isfinite(R)

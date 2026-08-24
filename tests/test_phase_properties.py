"""Layer 1 tests: volatility and condensed-phase estimation.

Same correctness strategy as the Joback tests: anchor values from the literature,
plus a cross-check of the new Joback outputs (Hvap, Tm) against the `thermo`
oracle so a transcription slip in the group table fails loudly.

The estimators here are *approximations with known failure modes*, so the
tolerances are deliberately not uniform -- they encode how much each correlation
should be trusted. A test that demanded 1% of Rowlinson-Bondi on ethanol would be
asserting something false about chemistry.
"""

import math

import pytest

from chemsim.matter import Molecule
from chemsim.properties import (
    CondensedProvider,
    ThermochemistryProvider,
    VolatilityError,
    VolatilityProvider,
    acentric_factor,
    estimate,
)
from chemsim.properties.critical import CriticalPropertyError
from chemsim.properties.condensed import (
    rackett_molar_volume,
    rowlinson_bondi_cp_excess,
)
from chemsim.properties.volatility import P_ATM_BAR, _henry_to_antoine

thermo_lib = pytest.importorskip("thermo", reason="thermo oracle not installed")
from thermo import Joback  # noqa: E402


@pytest.fixture
def vol():
    return VolatilityProvider()


@pytest.fixture
def cond():
    return CondensedProvider()


# --------------------------------------------------------------------------
# Joback's newly exposed outputs, against the oracle
# --------------------------------------------------------------------------

CROSS_CHECK = [
    "CCO", "CC(=O)O", "CCOC(C)=O", "CC(C)=O", "CO", "CCOCC", "CCCCC",
    "c1ccccc1", "Cc1ccccc1", "Oc1ccccc1", "CCN", "CC#N", "C1CCCCC1",
]


@pytest.mark.parametrize("smi", CROSS_CHECK)
def test_hvap_and_tm_match_thermo(smi):
    ours = estimate(Molecule.from_smiles(smi))
    ref = Joback(smi)
    assert ours.Hvap == pytest.approx(ref.Hvap(ref.counts) / 1000.0, rel=1e-6)
    assert ours.Tm == pytest.approx(ref.Tm(ref.counts), rel=1e-6)


def test_hvap_is_in_the_right_ballpark():
    """Joback Hvap is at the NORMAL BOILING POINT, not at 298 K."""
    assert estimate(Molecule.from_smiles("CCO")).Hvap == pytest.approx(38.6, abs=3.0)
    assert estimate(Molecule.from_smiles("c1ccccc1")).Hvap == pytest.approx(30.7, abs=3.0)


# --------------------------------------------------------------------------
# acentric factor: derived from the boiling point, not transcribed
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,Tb,Tc,Pc,literature",
    [
        ("water", 373.15, 647.14, 220.64, 0.344),
        ("ethanol", 351.44, 514.00, 61.37, 0.645),
        ("benzene", 353.24, 562.16, 48.95, 0.210),
        ("acetone", 329.22, 508.20, 47.01, 0.307),
        ("n-hexane", 341.88, 507.60, 30.25, 0.301),
    ],
)
def test_acentric_factor_matches_literature(name, Tb, Tc, Pc, literature):
    # Water is the outlier (associating); 0.03 absolute covers it.
    assert acentric_factor(Tb, Tc, Pc) == pytest.approx(literature, abs=0.03)


def test_acentric_factor_rejects_a_boiling_point_above_tc():
    # ``acentric_factor`` lives in ``properties.critical`` now -- it moved below
    # ``volatility`` so ``thermochemistry`` could derive an enthalpy of
    # vaporisation from the Lee-Kesler curve without importing back into a
    # provider. It therefore raises the BASE exception type. ``VolatilityError``
    # is a subclass, so a caller who wants either can still catch the base.
    with pytest.raises(CriticalPropertyError, match="not below Tc"):
        acentric_factor(700.0, 647.0, 220.0)
    assert issubclass(VolatilityError, CriticalPropertyError)


# --------------------------------------------------------------------------
# vapour pressure
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "smi,P298",
    [("O", 0.0317), ("CO", 0.169), ("CCO", 0.0790), ("CCOC(C)=O", 0.124)],
)
def test_curated_antoine_reproduces_known_vapour_pressures(vol, smi, P298):
    assert vol.get(smi).coefficient(298.15) == pytest.approx(P298, rel=0.05)


@pytest.mark.parametrize("smi,Tb", [("O", 373.15), ("CCO", 351.44), ("CO", 337.7)])
def test_vapour_pressure_is_one_atmosphere_at_the_boiling_point(vol, smi, Tb):
    assert vol.get(smi).coefficient(Tb) == pytest.approx(P_ATM_BAR, rel=0.05)


def test_estimated_curve_passes_through_the_boiling_point(vol):
    """The Lee-Kesler fit is anchored by construction: omega is chosen to make
    Psat(Tb) = 1 atm. An uncurated molecule must still honour that."""
    t = ThermochemistryProvider().get("CCCCO")   # n-butanol: not in the table
    v = vol.get("CCCCO")
    assert "Lee-Kesler" in v.source
    assert v.coefficient(t.Tb) == pytest.approx(P_ATM_BAR, rel=0.10)


def test_vapour_pressure_rises_with_temperature(vol):
    v = vol.get("CCO")
    assert v.coefficient(280.0) < v.coefficient(320.0) < v.coefficient(360.0)


# --------------------------------------------------------------------------
# Henry's law: the same functional form, exactly
# --------------------------------------------------------------------------


def test_henry_to_antoine_is_exact_not_fitted():
    """van 't Hoff is already Antoine-shaped with C = 0; the conversion is
    algebra, so it must reproduce the input to machine precision."""
    H_ref, C_vh = 4.26e4, 1700.0
    A, B, C = _henry_to_antoine(H_ref, C_vh)
    assert C == 0.0

    for T in (280.0, 298.15, 350.0):
        expected = H_ref * math.exp(-C_vh * (1.0 / T - 1.0 / 298.15))
        assert 10.0 ** (A - B / T) == pytest.approx(expected, rel=1e-12)


def test_permanent_gases_are_not_condensable(vol):
    for smi in ("O=O", "N#N", "[H][H]"):
        v = vol.get(smi)
        assert v.kind == "henry"
        assert not v.condensable
    assert vol.get("CCO").condensable


def test_henry_constant_rises_with_temperature(vol):
    """Higher H means less dissolved -- warm water holds less oxygen."""
    v = vol.get("O=O")
    assert v.coefficient(280.0) < v.coefficient(330.0)


# --------------------------------------------------------------------------
# condensed phase
# --------------------------------------------------------------------------


def test_rackett_reproduces_known_liquid_volumes():
    # benzene: Tc 562.2 K, Pc 48.95 bar, Vc 256 cm3/mol -> ~89 cm3/mol at 298 K
    v = rackett_molar_volume(298.15, 562.16, 48.95, 256.0)
    assert v == pytest.approx(89.4, rel=0.05)


def test_rowlinson_bondi_is_good_for_a_non_polar_liquid(cond):
    """Benzene: ideal-gas Cp 82.4 + excess should land near the real 135.7."""
    excess = rowlinson_bondi_cp_excess(298.15, 562.16, 0.210)
    assert 82.4 + excess == pytest.approx(135.7, rel=0.10)


@pytest.mark.parametrize(
    "smi,V,Cp",
    [("O", 0.01807, 75.3), ("CCO", 0.05868, 112.3), ("CC(=O)O", 0.05748, 123.1)],
)
def test_curated_liquids_are_exact(cond, smi, V, Cp):
    d = cond.get(smi)
    assert d.molar_volume(298.15) == pytest.approx(V, rel=1e-3)
    assert d.Cp(298.15) == pytest.approx(Cp, rel=1e-3)


@pytest.mark.parametrize(
    "smi,V,Cp", [("c1ccccc1", 0.0894, 135.7), ("CCCCCC", 0.1315, 195.0)]
)
def test_estimated_liquids_are_within_their_stated_accuracy(cond, smi, V, Cp):
    d = cond.get(smi)
    assert d.molar_volume(298.15) == pytest.approx(V, rel=0.08)
    assert d.Cp(298.15) == pytest.approx(Cp, rel=0.10)


def test_dissolved_gases_skip_the_liquid_correlations(cond):
    """O2 at 298 K is 1.9x above its critical temperature -- Rackett is off its
    domain and Rowlinson-Bondi diverges. It must take the solute path instead,
    and say so."""
    d = cond.get("O=O")
    assert "partial molar volume" in d.v_source
    assert "dissolved gas" in d.Cp_source
    assert d.Cp(298.15) == pytest.approx(29.4, rel=0.02)   # ideal-gas value
    assert 0.02 < d.molar_volume(298.15) < 0.05


def test_every_value_carries_provenance(vol, cond):
    for smi in ("O", "CCO", "c1ccccc1", "O=O"):
        assert vol.get(smi).source
        d = cond.get(smi)
        assert d.v_source and d.Cp_source

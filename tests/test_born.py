"""Ion transfer between phases -- the Born term, and what it replaced.

The thing under test is a JUDGEMENT as much as a model: an electrolyte used to be
refused a liquid-liquid split outright, because an ion held at gamma = 1 partitions
to equal mole fraction between water and toluene. These tests pin the replacement
and, just as importantly, pin the two narrow refusals that survive it -- a refusal
that quietly stopped refusing would be the worst outcome here.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.numerics.activity import (
    LN_GAMMA_BORN_MAX,
    born_ln_gamma,
    oster_permittivity as oster_mixture,
)
from chemsim.numerics.vessel_integrator import BORN_COVERAGE_MIN
from chemsim.properties import (
    BORN_PREFACTOR,
    DielectricProvider,
    born_coefficient,
    build_born_arrays,
    dissociation_templates,
    electrolyte_provider,
    ionic_radius,
)
from chemsim.vessel import Vessel

WATER = "O"
TOLUENE = Molecule.from_smiles("Cc1ccccc1").smiles
NA, CL = "[Na+]", "[Cl-]"


@pytest.fixture(scope="module")
def thermo():
    return electrolyte_provider()


@pytest.fixture(scope="module")
def brine_net(thermo):
    return build_network(
        [WATER, TOLUENE, NA, CL], [], thermo=thermo, max_species=20
    )


def funnel(net, **kw):
    conds = dict(volume=4.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0,
                 k_diss=0.0, k_vent=0.0)
    conds.update(kw)
    return Vessel(net, **conds)


# ---------------------------------------------------------------- Layer 1


def test_the_permittivity_table_reproduces_its_own_measurements():
    """A curated table has to be checked against the thing it was taken from.

    Each CRC entry carries a measurement at one temperature alongside the
    correlation, so evaluating the correlation there is an internal consistency
    check on the transcription -- it catches a shifted column, which is the way
    a generated table actually goes wrong.
    """
    provider = DielectricProvider()
    for smi, eps in (("O", 78.4), ("Cc1ccccc1", 2.38), ("c1ccccc1", 2.27),
                     ("CCCCCC", 1.88), ("CCO", 24.9), ("ClCCl", 8.9)):
        got = provider.get(smi).at(298.15)
        assert got == pytest.approx(eps, rel=0.03), smi


def test_water_is_the_reference_and_its_curve_is_sane():
    """Water's permittivity falls from 87 near freezing to 55 near boiling. Every
    ion's activity coefficient is measured against this curve, so a sign error in
    it would invert every partition in the project."""
    provider = DielectricProvider()
    water = provider.get(WATER)
    assert water.at(273.15) == pytest.approx(87.9, rel=0.02)
    assert water.at(298.15) == pytest.approx(78.4, rel=0.02)
    assert water.at(373.15) == pytest.approx(55.5, rel=0.03)
    # ... and it is clamped rather than extrapolated: the cubic is quoted to
    # 372 K and a cubic run far past its data is how a permittivity goes negative.
    assert water.at(1000.0) == water.at(water.T_range[1])
    assert water.at(1.0) == water.at(water.T_range[0])


def test_an_unpriced_liquid_says_so_instead_of_guessing():
    """Benzoic acid is a solid and has no measured liquid permittivity. The table
    must not invent one -- a guessed polarity decides which layer an ion lives in.
    """
    record = DielectricProvider().get("OC(=O)c1ccccc1")
    assert not record.known
    assert record.at(298.15) == 0.0        # the sentinel the mixing rule masks on


def test_the_ionic_radius_is_curated_where_it_can_be_and_derived_otherwise():
    curated = ionic_radius(NA)
    assert curated.value == pytest.approx(1.02e-10)
    assert "Shannon" in curated.source

    derived = ionic_radius("[O-]C(=O)c1ccccc1")     # benzoate: no crystal radius
    assert "derived" in derived.source
    # A benzoate ion is bigger than a sodium ion and smaller than a nanometre.
    assert 3.0e-10 < derived.value < 4.5e-10

    assert not ionic_radius(WATER).known            # a neutral has no Born term


def test_the_born_coefficient_is_the_textbook_expression():
    """694.7 kJ/mol for a unit charge on a 1 angstrom sphere, per unit (1/eps).
    Assembled from SI constants rather than transcribed, so this pins the
    assembly."""
    assert BORN_PREFACTOR / 1.0e-10 / 1000.0 == pytest.approx(694.7, abs=0.5)
    A_na, why = born_coefficient(NA)
    assert A_na == pytest.approx(BORN_PREFACTOR / 1.02e-10)
    assert "z = +1" in why

    # z SQUARED, and z comes from the graph rather than a table -- so a divalent
    # ion is four times as excluded with no extra data.
    A_sulfate, _ = born_coefficient("[O-]S(=O)(=O)[O-]")
    r = ionic_radius("[O-]S(=O)(=O)[O-]").value
    assert A_sulfate == pytest.approx(4.0 * BORN_PREFACTOR / r)


def test_osters_rule_is_exact_at_both_ends_and_monotone_between():
    eps = np.array([78.4, 2.38])
    assert oster_mixture(np.array([1.0, 0.0]), eps) == pytest.approx(78.4, rel=1e-9)
    assert oster_mixture(np.array([0.0, 1.0]), eps) == pytest.approx(2.38, rel=1e-9)
    mixed = [oster_mixture(np.array([f, 1.0 - f]), eps) for f in np.linspace(0, 1, 11)]
    assert all(b > a for a, b in zip(mixed, mixed[1:]))

    # ⚠ An unpriced NEUTRAL is medium of unknown polarity, so it contributes
    # f = 0 and still counts in the volume: the result is the LOWEST permittivity
    # the layer could have, which is a bound rather than a guess. Erring low errs
    # toward the ion staying in the water.
    bounded = oster_mixture(np.array([1.0, 0.0, 1.0]), np.array([78.4, 2.38, 0.0]))
    assert 1.0 < bounded < 78.4
    assert bounded == pytest.approx(
        oster_mixture(np.array([1.0, 1.0]), np.array([78.4, 1.0])), rel=1e-6
    ), "an unpriced species must behave as the least polarisable material there is"

    # ... and an ION is not medium at all, which is a different statement. Left in
    # it would give a molar brine a lower permittivity than water, with the wrong
    # sign for the ionic-strength behaviour Debye-Huckel describes.
    excluded = oster_mixture(
        np.array([1.0, 1.0]), np.array([78.4, 0.0]),
        medium=np.array([True, False]),
    )
    assert excluded == pytest.approx(78.4, rel=1e-9)


# ---------------------------------------------------------------- Layer 4


def test_the_born_term_is_exactly_zero_in_water_at_every_temperature(brine_net):
    """⚠ THE TRAP THIS ARC WAS WARNED ABOUT, and the reason it did not bite.

    Every ion in this project has its formation data BACK-DERIVED from a measured
    aqueous pKa at gamma = 1. Introducing gamma for ions would normally mean
    re-deriving all of those anchors. It does not here, because the term is a
    TRANSFER referenced to water: in water it is identically zero, so the anchors
    are still taken at the state they were derived in. Zero, not small.
    """
    v = funnel(brine_net)
    v.charge({WATER: 55.0})
    for T in (275.0, 298.15, 330.0, 373.0):
        born = v.phases.born_block(T)
        ln = born_ln_gamma(v._nL, born, T)
        assert np.all(ln == 0.0), f"{T} K: {ln}"


def test_an_ion_is_excluded_from_a_hydrocarbon_and_not_from_water(brine_net):
    v = funnel(brine_net)
    v.charge({WATER: 55.0, TOLUENE: 5.0, NA: 0.5, CL: 0.5})
    born = v.phases.born_block(298.15)
    i = v._idx[NA]

    aqueous = born_ln_gamma(np.array([55.0 if s == WATER else 0.0
                                      for s in v.species]), born, 298.15)
    organic = born_ln_gamma(np.array([5.0 if s == TOLUENE else 0.0
                                      for s in v.species]), born, 298.15)
    assert aqueous[i] == pytest.approx(0.0, abs=1e-12)
    assert organic[i] == pytest.approx(LN_GAMMA_BORN_MAX)   # at the ceiling

    # Neutral species are untouched by this term entirely.
    assert organic[v._idx[WATER]] == 0.0
    assert organic[v._idx[TOLUENE]] == 0.0


def test_the_term_is_bounded_and_the_bound_is_why_it_integrates():
    """The unclipped transfer energy for sodium into toluene is ln gamma 112. That
    is not a number BDF can carry in a flux of the form k (a1 - a2): it implies a
    relaxation timescale of 1e-23 s for a quantity whose equilibrium value is
    1e-24 mol. The ceiling is a resolution limit, argued for in
    ``activity.LN_GAMMA_BORN_MAX``, and this test pins that it is doing work.
    """
    A, _ = born_coefficient(NA)
    eps_toluene = DielectricProvider().get(TOLUENE).at(298.15)
    eps_water = DielectricProvider().get(WATER).at(298.15)
    raw = A / (8.31446 * 298.15) * (1.0 / eps_toluene - 1.0 / eps_water)
    assert raw > 100.0, "the physics really is this violent"
    assert LN_GAMMA_BORN_MAX < 0.2 * raw, "and the ceiling really is doing work"
    # ... and what the ceiling implies is still an invisible partition.
    assert math.exp(-LN_GAMMA_BORN_MAX) < 1.0e-4


# ---------------------------------------------------------------- Layer 5


def test_brine_and_toluene_now_separate_with_the_salt_in_the_water(brine_net):
    """The headline: the split this project used to refuse.

    Nothing about the SOLVENT pair changed -- water/toluene always separated. What
    changed is that the salt no longer has to be pretended away, and it ends up
    where a bench would find it.
    """
    v = funnel(brine_net)
    v.charge({WATER: 27.7, TOLUENE: 4.7, NA: 1.0, CL: 1.0})
    v.run(600.0)
    assert v.two_phase

    st = v.state()
    for ion in (NA, CL):
        aqueous, organic = st.n_liquid[ion], st.n_liquid2[ion]
        assert aqueous > 0.999, f"{ion} left the water"
        assert organic < 1.0e-5, f"{ion} got into the toluene: {organic}"

    # The two layers are what they should be, computed rather than labelled.
    assert v.layer_permittivity(1) == pytest.approx(78.3, rel=0.02)
    assert v.layer_permittivity(2) == pytest.approx(2.39, rel=0.05)
    assert not v.conservation_report()


def test_the_partition_coefficient_is_small_and_the_report_says_how(brine_net):
    v = funnel(brine_net)
    v.charge({WATER: 27.7, TOLUENE: 4.7, NA: 1.0, CL: 1.0})
    v.run(600.0)
    st = v.state()
    N1 = sum(st.n_liquid.values())
    N2 = sum(st.n_liquid2.values())
    K = (st.n_liquid2[NA] / N2) / (st.n_liquid[NA] / N1)
    assert K < 1.0e-4
    # It is the ceiling that sets it, so it must agree with the ceiling.
    assert K == pytest.approx(math.exp(-LN_GAMMA_BORN_MAX), rel=0.5)

    report = v.electrolyte_report()
    assert "Shannon" in report and "Born" in report
    assert "AT THE CEILING" in report, "a ceiled value must say so"


def test_a_divalent_ion_is_excluded_four_times_as_hard(thermo):
    """z^2, and z is read off the molecular graph. Sulfate needs no new datum to
    be more strongly held in the water than chloride is."""
    net = build_network(
        [WATER, TOLUENE, NA, CL, "[O-]S(=O)(=O)[O-]"], [],
        thermo=thermo, max_species=20,
    )
    v = funnel(net)
    v.charge({WATER: 55.0, TOLUENE: 5.0, NA: 0.1, CL: 0.05,
              "[O-]S(=O)(=O)[O-]": 0.025})
    born = v.phases.born_block(298.15)
    organic = born_ln_gamma(
        np.array([5.0 if s == TOLUENE else 0.0 for s in v.species]), born, 298.15
    )
    # Both are at the ceiling in toluene, so compare the coefficients instead --
    # that is where the z^2 lives, and the ceiling is downstream of it.
    A_cl, _ = born_coefficient(CL)
    A_so4, _ = born_coefficient("[O-]S(=O)(=O)[O-]")
    r_cl = ionic_radius(CL).value
    r_so4 = ionic_radius("[O-]S(=O)(=O)[O-]").value
    assert A_so4 / A_cl == pytest.approx(4.0 * r_cl / r_so4, rel=1e-9)
    assert organic[v._idx[CL]] > 0.0


def test_a_miscible_electrolyte_is_left_alone(thermo):
    """Salt water is one liquid, and adding an ion model must not make it two."""
    net = build_network(
        [WATER, NA, CL], [], thermo=thermo, max_species=20
    )
    v = funnel(net)
    v.charge({WATER: 55.0, NA: 1.0, CL: 1.0})
    v.run(600.0)
    assert not v.two_phase
    assert v.lle_report() == ""
    assert v.layer_permittivity(1) == pytest.approx(78.3, rel=0.02)


def test_a_layer_of_unknown_polarity_gets_a_BOUND_not_a_guess(thermo):
    """⚠ THE CASE THAT DECIDED THE MIXING RULE'S TREATMENT OF UNKNOWNS.

    The Born term needs a medium as well as a charge, and benzoic acid is the
    honest awkward case: a solid, with no measured LIQUID permittivity in any
    source this project has. So what should a layer made mostly of it be worth?

    Excluding it and renormalising over the priced remainder says it behaves like
    the average of what IS priced -- fine for a trace, and actively dangerous when
    the unknown dominates. It is what let the ions into the prep's organic layer:
    that layer's polarity got read off the 32% of it that was water and ethanol,
    came out at eps = 50, and stopped excluding anything.

    Contributing ``f(eps) = 0`` while still counting in the volume is a BOUND
    instead. ``f`` is monotone with ``f(1) = 0``, so it is the LOWEST permittivity
    the layer could possibly have -- and erring low errs toward the ion staying in
    the water, which is the safe direction here.
    """
    benzoic = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
    net = build_network([WATER, benzoic, NA, CL], [], thermo=thermo, max_species=20)
    v = funnel(net)

    # It is named as unpriced rather than silently defaulted.
    assert benzoic in v.born_model.unpriced
    assert "no relative permittivity" in v.born_model.unpriced[benzoic]
    assert benzoic in v.electrolyte_report()

    # A layer that is mostly the unpriced species reads LOW, not average.
    born = v.phases.born_block(298.15)
    amounts = np.array(
        [1.0 if s == WATER else (9.0 if s == benzoic else 0.0) for s in v.species]
    )
    v._nL = amounts
    eps = v.layer_permittivity(1)
    assert 1.0 < eps < 30.0, f"a mostly-unpriced layer read {eps}, not a bound"

    # ... and that is enough to keep the ions out of it, which is the whole point.
    ln = born_ln_gamma(amounts, born, 298.15)
    assert ln[v._idx[NA]] > 5.0, "an unpriced layer stopped excluding ions"

    # Coverage is REPORTED rather than refused, precisely because the bound above
    # already errs safe. The helper still has to measure it correctly.
    only_benzoic = np.array([1.0 if s == benzoic else 0.0 for s in v.species])
    assert v.integrator._permittivity_coverage(
        only_benzoic, np.ones(len(v.species))
    ) == 0.0
    only_water = np.array([1.0 if s == WATER else 0.0 for s in v.species])
    assert v.integrator._permittivity_coverage(
        only_water, np.ones(len(v.species))
    ) == 1.0
    assert BORN_COVERAGE_MIN == pytest.approx(0.9)


def test_an_ion_the_model_cannot_price_is_named_not_guessed(thermo):
    """The other surviving refusal, at the level it can be tested: an ion with no
    resolvable radius gets no coefficient and is REPORTED, rather than being left
    freely transferable in silence."""
    arrays = build_born_arrays([WATER, TOLUENE, NA, CL])
    assert not arrays.unpriced_ions, "these four are all priceable"
    assert arrays.any_ions
    assert TOLUENE not in arrays.unpriced and WATER not in arrays.unpriced

    # A species carrying an element with no van der Waals radius cannot be
    # priced, and says which element.
    A, why = born_coefficient("[Fe+3]")
    assert A == 0.0
    assert "Fe" in why


def test_pH_is_untouched_by_all_of_this(thermo):
    """⚠ Re-measured rather than argued: the anchors were derived at gamma = 1
    against water and the Born term is exactly zero there, so the five pH
    invariants must come back unchanged. This is the check the arc's brief asked
    for by name."""
    net = build_network(
        [WATER, "CC(=O)O", "[OH-]", NA], dissociation_templates(),
        thermo=thermo, max_species=60,
    )

    def pH(charge):
        v = Vessel(net, volume=1.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0,
                   k_diss=0.0)
        v.charge(charge)
        v.run(2000.0)
        return v.pH

    assert pH({WATER: 55.34}) == pytest.approx(7.00, abs=0.05)
    assert pH({WATER: 55.34, "CC(=O)O": 0.1}) == pytest.approx(2.89, abs=0.1)
    assert pH({WATER: 55.34, "CC(=O)O": 0.1, "[OH-]": 0.05, NA: 0.05}) == (
        pytest.approx(4.76, abs=0.05)
    )

"""M3, the ENGINE half -- an ionic lattice can leave solution.

``AgNO3 + NaCl -> AgCl(down)``. Before this, no ion could crystallise at all:
``solidifies`` is set only where Tm AND Hfus AND condensable are known, and an
ion has none of the three, so the whole "add A to B and it goes cloudy" class of
play was unreachable. The DATA half -- why a Ksp could not be priced until an
aqueous-basis ion table landed -- is in ``tests/test_solubility_product.py``.

⚠ These tests integrate, so they are slower than that file's. They are still
seconds rather than minutes: the flask is seven species and the interesting
transient is over in twenty minutes of simulated time.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from chemsim.network import build_network
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.properties.solubility_product import solubility_product
from chemsim.vessel import Vessel
from chemsim.vessel.vessel import build_precipitation_arrays

WATER = "O"
SILVER, CHLORIDE, SODIUM = "[Ag+]", "[Cl-]", "[Na+]"
NITRATE = "O=[N+]([O-])[O-]"


@pytest.fixture(scope="module")
def thermo():
    return electrolyte_provider()


@pytest.fixture(scope="module")
def net(thermo):
    return build_network(
        [WATER, SILVER, CHLORIDE, SODIUM, NITRATE],
        list(dissociation_templates()), thermo=thermo, max_species=40,
    )


def flask(net, thermo, **kw) -> Vessel:
    return Vessel(net, volume=1.0, thermo=thermo, **kw)


def metathesis(net, thermo, mol: float = 0.01, **kw) -> Vessel:
    """0.01 mol of silver nitrate meeting 0.01 mol of rock salt in 1 L."""
    v = flask(net, thermo, **kw)
    v.charge({WATER: 55.0, SILVER: mol, NITRATE: mol, SODIUM: mol, CHLORIDE: mol})
    return v


# ---------------------------------------------------------------------------
# the deliverable
# ---------------------------------------------------------------------------
def test_a_metathesis_precipitates(net, thermo):
    """⚠⚠ M3's first 'done when' clause, and the mechanic the design is named for.

    Nothing about this is declared. There is no AgCl species, no template and no
    recipe -- four ions are charged into water and the solubility product decides
    what happens.
    """
    v = metathesis(net, thermo)
    v.run(1200.0)
    st = v.state()

    assert st.n_solid[SILVER] > 0.99 * 0.01, "silver did not come out"
    assert st.n_liquid[SILVER] < 1.0e-4

    # ⚠ AND THE SPECTATOR STAYS IN SOLUTION, which is the other half of the
    # claim: sodium nitrate is soluble and no part of it drops.
    assert st.n_solid.get(SODIUM, 0.0) == pytest.approx(0.0, abs=1e-12)
    assert st.n_liquid[SODIUM] == pytest.approx(0.01, rel=1e-6)


def test_the_precipitate_comes_out_in_EXACT_lattice_stoichiometry(net, thermo):
    """1:1 for AgCl, to the last digit the solver carries. The solid block holds
    IONS rather than a lattice species, so nothing enforces the ratio except the
    stoichiometry row the term multiplies by -- which is the property worth
    pinning, because a bug there would look like a plausible precipitate."""
    v = metathesis(net, thermo)
    v.run(600.0)
    st = v.state()
    # rel 1e-6 rather than exact: the two blocks receive the SAME flux at every
    # RHS evaluation, so any difference is the solver's own error control and
    # not the stoichiometry. Measured, it is ~1e-9 relative.
    assert st.n_solid[SILVER] == pytest.approx(st.n_solid[CHLORIDE], rel=1e-6)
    assert st.n_solid[SILVER] > 1.0e-3


def test_the_supernatant_sits_at_the_square_root_of_Ksp(net, thermo):
    """The equilibrium the term is supposed to reach, checked against the number
    the property layer computes independently of the engine."""
    v = metathesis(net, thermo)
    v.run(1800.0)
    st = v.state()
    saturated = math.sqrt(solubility_product("chlorargyrite").Ksp)
    for ion in (SILVER, CHLORIDE):
        assert st.n_liquid[ion] / v.liquid_volume == pytest.approx(
            saturated, rel=0.05
        )


def test_matter_is_CONSERVED_across_the_precipitation(net, thermo):
    """Nothing here is new physics -- matter only moves between blocks -- so the
    conservation report has to stay empty and every element total unmoved."""
    v = metathesis(net, thermo)
    v.run(1200.0)
    assert v.conservation_report() == ""
    st = v.state()
    for ion, charged in ((SILVER, 0.01), (CHLORIDE, 0.01), (SODIUM, 0.01)):
        assert st.total(ion) == pytest.approx(charged, rel=1e-9), ion


def test_it_warms_the_flask_by_the_dissolution_enthalpy(net, thermo):
    """⚠ Precipitation is the REVERSE of dissolution, so it RELEASES dH_diss.

    AgCl dissolves endothermically, so a flask that drops 0.01 mol of it has to
    warm -- by an amount the two TABLES predict, not by an amount the run
    reports. Insulated, so the only place the energy can go is temperature.

    ⚠ CHECKED AT 1200 s AND FOR CONVERGENCE, NOT AT AN ARBITRARY LATE TIME.
    Measured, the same flask run in ONE call to 3600 s reads 0.038 K instead of
    0.158. What IS established about that: the extent is unmoved at 0.0099866 mol
    either way, so it is not the chemistry; chunking the identical run into ten
    calls recovers 0.1578 exactly; tightening rtol to 1e-9 recovers it in one
    call; and an undisturbed adiabatic flask at ambient holds its temperature to
    1e-4 K over the same span. So it is the integration of the TAIL, after the
    precipitation is over by ~600 s.

    ⚠⚠ SETTLED 2026-08-24, AND THE HYPOTHESIS THAT STOOD HERE WAS WRONG. This
    docstring used to say the tail was *probably* generic -- an insulated flask
    losing its excess to evaporation while BDF weighted T against ``rtol * 298``
    -- and recorded that as unmeasured because the control "did not finish inside
    two minutes". The control finishes in 0.2 s, and it REFUTES that: a warm
    insulated flask with no precipitation holds +0.15992 K to five decimals over
    the same single 3600 s call, at default tolerance and at rtol 1e-9.

    What the tail actually is: **an energy leak that requires the precipitation
    EVENT**, worth 495 J against a 0.0087 J chemical budget, occurring in the
    window after the chemistry has stopped. See HANDOFF 81 and MILESTONES M12.

    ⚠ THIS TEST IS STILL CORRECT AND STILL WORTH KEEPING. It measures at 1200 s,
    where the flask is at +0.15751 K against +0.1577 predicted, and it asserts
    CONVERGENCE rather than a default-tolerance value -- which is exactly the
    rule that kept it honest while the tail was misdiagnosed for two sessions.
    """
    ksp = solubility_product("chlorargyrite")
    Cp_water = 75.29                                  # J/(mol K), liquid water

    def rise(**kw) -> tuple[float, float]:
        v = metathesis(net, thermo, UA=0.0, heat_capacity=0.0, T_env=298.15)
        v.run(1200.0, **kw)
        dropped = v.state().n_solid[SILVER]
        return v.T - 298.15, dropped * ksp.dH_diss * 1000.0 / (55.0 * Cp_water)

    loose, expected = rise()
    tight, _ = rise(rtol=1.0e-9, atol=1.0e-12)
    assert loose > 0.0
    assert loose == pytest.approx(expected, rel=0.02)
    assert tight == pytest.approx(expected, rel=0.02)
    # ...and it is CONVERGED: tightening the solver by three decades moves it by
    # less than a tenth of the claim.
    assert abs(tight - loose) < 0.1 * expected


# ---------------------------------------------------------------------------
# the reverse direction, and the gate that guards it
# ---------------------------------------------------------------------------
def test_a_crop_of_solid_DISSOLVES_back_to_saturation(net, thermo):
    """The term is one flux written twice, so the undersaturated direction has to
    work too -- a crop under pure water dissolves until Q reaches Ksp and stops."""
    v = flask(net, thermo)
    v.charge({WATER: 55.0})
    v.charge({SILVER: 1.0e-4, CHLORIDE: 1.0e-4}, phase="solid")
    v.run(3000.0)
    st = v.state()
    saturated = math.sqrt(solubility_product("chlorargyrite").Ksp)
    assert st.n_liquid[SILVER] / v.liquid_volume == pytest.approx(
        saturated, rel=0.05
    )
    assert st.n_solid[SILVER] > 0.8 * 1.0e-4, "it must not all dissolve"


def test_a_lattice_that_never_precipitated_cannot_be_dissolved(net, thermo):
    """⚠ THE GATE, AND THE LIMIT IT COMPENSATES FOR.

    The solid block is an ION INVENTORY, not a set of distinct crystals -- there
    is no record of which lattice a solid chloride belongs to. What keeps that
    from letting rock salt dissolve out of a silver chloride crop is the ``units``
    bound: a lattice can only dissolve while EVERY one of its ions is present in
    the solid. Solid sodium with no solid chloride is therefore inert.
    """
    v = flask(net, thermo)
    v.charge({WATER: 55.0})
    v.charge({SODIUM: 1.0e-3}, phase="solid")
    v.run(600.0)
    st = v.state()
    assert st.n_solid[SODIUM] == pytest.approx(1.0e-3, rel=1e-6)
    assert st.n_liquid.get(SODIUM, 0.0) < 1.0e-12


def test_a_soluble_salt_does_not_drop_at_half_molar(net, thermo):
    """The other side of the mechanic: 0.5 M sodium chloride is a long way below
    saturation and nothing should happen to it. A term that precipitated here
    would be worse than no term."""
    v = flask(net, thermo)
    v.charge({WATER: 55.0, SODIUM: 0.5, CHLORIDE: 0.5})
    v.run(1200.0)
    st = v.state()
    assert st.n_solid.get(SODIUM, 0.0) == pytest.approx(0.0, abs=1e-12)
    assert st.n_liquid[SODIUM] == pytest.approx(0.5, rel=1e-6)


# ---------------------------------------------------------------------------
# the off switch, and what it is not allowed to hide
# ---------------------------------------------------------------------------
def test_precipitation_False_is_EXACTLY_the_old_behaviour(net, thermo):
    """Same contract ``losses=None`` and ``World.rig is None`` keep: the term is
    absent rather than small."""
    v = metathesis(net, thermo, precipitation=False)
    assert v.integrator.prec is None
    v.run(1200.0)
    st = v.state()
    assert st.n_liquid[SILVER] == pytest.approx(0.01, rel=1e-9)
    assert st.n_solid.get(SILVER, 0.0) < 1.0e-20


def test_switching_it_off_does_not_hide_the_QUESTION(net, thermo):
    """⚠ Same rule ``lle=False`` follows. The arrays are still built and still
    report which lattices this flask could have dropped, because a silently
    non-precipitating solution is exactly the confident wrong answer this project
    refuses to give."""
    v = metathesis(net, thermo, precipitation=False)
    assert "chlorargyrite" in v.precipitation_arrays.names


# ---------------------------------------------------------------------------
# the Layer 5 -> Layer 4 contract
# ---------------------------------------------------------------------------
def test_the_arrays_carry_no_chemistry(net, thermo):
    """Numerics sees only numpy arrays. ``names`` is the one exception and it is
    for reporting -- nothing in the RHS reads it."""
    prec, _ = build_precipitation_arrays(list(net.species))
    for field in ("nu", "total_nu", "ln_Ksp_ref", "dH_diss", "dS_diss"):
        assert isinstance(getattr(prec, field), np.ndarray), field
    assert prec.nu.shape == (prec.m, len(net.species))
    assert np.all(prec.total_nu == prec.nu.sum(axis=1))


def test_a_lattice_qualifies_on_its_IONS_being_present_not_the_lattice(net, thermo):
    """The lattice never becomes a species. What has to be in the vessel is
    ``[Ag+]`` and ``[Cl-]``, which a dissociating network already has."""
    prec, _ = build_precipitation_arrays([WATER, SILVER, CHLORIDE])
    assert "chlorargyrite" in prec.names
    assert "barite" not in prec.names            # no barium, no sulfate here
    empty, _ = build_precipitation_arrays([WATER, "CCO"])
    assert empty.m == 0


def test_the_vant_Hoff_lift_matches_the_property_layer(net, thermo):
    """The arrays carry ``dH``/``dS`` rather than a Ksp, so the RHS can move it
    with temperature. That lift has to agree with what ``solubility_product``
    computes directly, or the flask and the table would disagree when hot."""
    prec, _ = build_precipitation_arrays(list(net.species))
    j = prec.names.index("chlorargyrite")
    for T in (278.15, 298.15, 348.15):
        assert prec.ln_Ksp(T)[j] == pytest.approx(
            solubility_product("chlorargyrite", T=T).ln_Ksp, rel=1e-9
        )


def test_the_term_itself_is_cheap_and_the_CHEMISTRY_is_what_costs(net, thermo):
    """⚠ MEASURED, BECAUSE 'PRECIPITATION MADE IT 2x SLOWER' IS TRUE AND
    MISLEADING.

    On the metathesis flask the run really does take about twice as long with
    the term on. But hold the chemistry fixed -- charge a flask where nothing is
    supersaturated -- and the term costs about 10%. The rest is AgCl actually
    crashing out, which is stiff work the flask was not doing before, and no
    amount of tightening the array code would remove it.
    """
    import time

    def cost(precipitation: bool) -> float:
        v = flask(net, thermo, precipitation=precipitation)
        v.charge({WATER: 55.0, SODIUM: 0.01, CHLORIDE: 0.01})
        start = time.perf_counter()
        v.run(1200.0)
        return time.perf_counter() - start

    # Generous: the point is that it is not a multiple, and a shared CI box is
    # noisy enough that a tight bound here would be a flaky test rather than a
    # measurement.
    assert cost(True) < 1.8 * cost(False)

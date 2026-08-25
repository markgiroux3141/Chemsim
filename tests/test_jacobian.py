"""Layer 4 -- the bound on BDF's differencing step, and what it costs.

⚠ THE UNIT UNDER TEST IS ONE MISSING BOUND IN scipy, so most of this module is
deliberately NOT about chemistry. ``num_jac`` raises a column's perturbation
factor tenfold whenever the difference it got back looks too small next to the
rates elsewhere in the system, floors that factor and never ceilings it. Against
a column it cannot difference at ALL -- one that is identically flat, or one the
RHS's own ``np.maximum(y, 0.0)`` has frozen -- that loop does not terminate.

See ``numerics/jacobian.py``, where the bound is argued and where the sweep that
REJECTED the obvious version of it (a constant ceiling of 1.0) is recorded. The
chemistry tests at the bottom are the two ends of the measurement: the run that
could not be done before, and the runs that were already fine and have to stay
bit-identical.
"""

import numpy as np
import pytest
from scipy.integrate._ivp.common import EPS, num_jac

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.numerics.jacobian import BoundedJacobian, factor_bound
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.reactions import sulfur_combustion
from chemsim.vessel import Vessel


def canonical(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


S8 = canonical("S1SSSSSSS1")
O2 = canonical("O=O")
N2 = canonical("N#N")
SO2 = canonical("O=S=O")


# --- the mechanism, with no chemistry anywhere near it ---------------------
#
# Two states, one live and one that nothing acts on. The second column is
# identically flat, which is the CORRECT derivative for it and also the one
# ``num_jac`` refuses to accept.
def _toy(t, y):
    return np.array([-float(y[0]), 0.0])


def _toy_vectorized(t, y):
    y = np.asarray(y)
    if y.ndim == 1:
        return _toy(t, y)
    return np.stack([_toy(t, y[:, k]) for k in range(y.shape[1])], axis=1)


def _drive(rounds: int, bounded: bool, y=None, atol=1e-9):
    """Difference the same fixed state ``rounds`` times, as a long single run
    does, carrying the factor forward exactly as BDF does."""
    y = np.array([1.0, 0.0]) if y is None else np.asarray(y, float)
    f = _toy(0.0, y)
    factor = None
    for _ in range(rounds):
        J, factor = num_jac(_toy_vectorized, 0.0, y, f, atol, factor, None)
        if bounded:
            np.clip(factor, None, factor_bound(y, atol), out=factor)
    return J, factor


def test_the_bound_is_the_states_own_extent_and_not_a_constant():
    """``|h_j| = factor_j * max(atol, |y_j|)`` and the requirement is
    ``|h_j| <= max_i |y_i|``: a probe may not move one component further than
    the whole state extends. On a state holding 690 K and 0.1 mol with
    ``atol = 1e-11``, an absent species is bounded at 6.9e13 -- finite, and far
    above the 1.49e+9 the busiest example in this project ever asks for."""
    toy = factor_bound(np.array([1.0, 0.0]), 1e-9)
    assert toy[0] == pytest.approx(1.0)
    assert toy[1] == pytest.approx(1e9)
    bound = factor_bound(np.array([0.1, 0.0, 690.0]), 1e-11)
    assert bound[1] == pytest.approx(6.9e13)
    assert bound[2] == pytest.approx(1.0)


def test_the_floor_keeps_a_degenerate_state_differenceable():
    """``max|y| = 0`` would otherwise bound every factor at zero and stall the
    differencing outright. Nothing real reaches this -- ``run``'s at-rest
    short-circuit catches it first -- but a bound that can return 0 is a
    division waiting to happen."""
    assert np.all(factor_bound(np.zeros(3), 1e-9) == EPS ** 0.5)


def test_a_flat_column_runs_the_factor_to_infinity_unbounded():
    """scipy's own behaviour, pinned so this module keeps meaning something if
    scipy ever grows the bound itself."""
    _, factor = _drive(400, bounded=False)
    assert factor[0] == pytest.approx(EPS ** 0.5)      # the live column: untouched
    assert not np.isfinite(factor[1])                  # the flat one: inf


def test_the_bound_holds_it_finite_and_the_column_still_reads_zero():
    """⚠ THE POINT IS NOT THAT THE COLUMN BECOMES NON-ZERO. Zero IS the
    derivative of a state nothing acts on. What changes is that ``num_jac``
    stops treating "I measured zero" as "I failed to measure"."""
    J, factor = _drive(400, bounded=True)
    assert factor[1] == pytest.approx(1e9)             # max|y| / atol
    assert np.all(np.isfinite(J))
    assert np.all(J[:, 1] == 0.0)


def test_the_number_of_jacobians_it_takes_to_overflow():
    """A decade per Jacobian from ``EPS**0.5``, so ~316 of them in ONE run --
    which is why this is a long-run fragility and not a per-step one, and why
    ``fragilities`` reports it rather than refusing the configuration."""
    for rounds in (300, 320):
        _, factor = _drive(rounds, bounded=False)
        assert np.isfinite(factor[1]) == (rounds == 300)


# --- the wrapper is the default path until the clamp binds ------------------
def test_bounded_jacobian_is_bit_for_bit_scipys_own_path_when_unbounded():
    """The "inf" rows of the sweeps in ``jacobian.py`` were taken this way, so
    it has to be exactly the same arithmetic."""
    y = np.array([1.0, 0.0])
    jac = BoundedJacobian(_toy, 1e-9, bounded=False)
    factor = None
    for _ in range(12):
        mine = jac(0.0, y)
        theirs, factor = num_jac(
            _toy_vectorized, 0.0, y, _toy(0.0, y), 1e-9, factor, None
        )
        assert np.array_equal(mine, theirs, equal_nan=True)
        assert np.array_equal(jac.factor, factor, equal_nan=True)


def test_it_reports_the_factor_the_solver_wanted_before_the_clamp():
    """``peak_factor`` is taken BEFORE the clip, because how hard BDF wanted to
    push is the diagnostic and the clipped value cannot show it."""
    jac = BoundedJacobian(_toy, 1e-9)
    for _ in range(60):
        jac(0.0, np.array([1.0, 0.0]))
    # One decade ABOVE the bound, and that is the reporting working rather than
    # the bound leaking: num_jac multiplies by ten, ``peak_factor`` records what
    # it asked for, and only then is it clipped back.
    assert jac.peak_factor == pytest.approx(1e10)
    assert jac.clamped > 0
    assert np.all(np.isfinite(jac.factor))


def test_a_sparsity_pattern_is_consumed_rather_than_dropped():
    """⚠ BDF IGNORES ``jac_sparsity`` THE MOMENT ``jac`` IS CALLABLE. A rig that
    passed both to ``solve_ivp`` would silently lose its column groups, which is
    the entire 10x that ``useful_sparsity`` exists to avoid paying."""
    pattern = np.array([[1, 0], [0, 1]], dtype=bool)
    jac = BoundedJacobian(_toy, 1e-9, pattern)
    J = jac(0.0, np.array([1.0, 0.0]))
    assert hasattr(J, "toarray"), "a sparsity pattern must give a sparse J"
    assert J.toarray()[0, 0] == pytest.approx(-1.0)


# --- the two ends of the chemistry measurement -----------------------------
@pytest.fixture(scope="module")
def burn_net():
    return build_network(
        [S8, O2, N2], [sulfur_combustion()],
        thermo=ThermochemistryProvider(), volatility=VolatilityProvider(),
        max_species=40,
    )


def _burn(net, T, s8, o2, **kw):
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e4, kla=5.0, k_vent=0.0,
               k_diss=0.05, lle=False)
    v.charge({S8: s8, O2: o2, N2: 0.02})
    v.run(600.0, **kw)
    return v.state().total(SO2)


def test_the_burner_can_be_run_at_a_tight_tolerance_at_all(burn_net):
    """⚠ THE REGRESSION THIS MODULE EXISTS FOR, and it costs ~50 s. S2's
    tolerance audit could not sweep ``oil_of_vitriol`` because this run RAISED
    "array must not contain infs or NaNs" after ~51 s of thrashing. The column
    that overflowed is the SECOND LIQUID LAYER's SO2 at 8.21e-29 mol, whose
    ``LAYER_REABSORB`` drain makes ``f`` negative, so ``num_jac`` steps DOWNWARD
    into the RHS's own non-negativity clamp and gets the same frozen difference
    at every step size over thirty decades.

    ⚠ IT IS STILL SLOW, AND THAT IS REPORTED RATHER THAN HIDDEN. BDF is
    genuinely struggling with a liquid layer holding 1e-29 mol; the bound stops
    that struggle ending in a NaN and does not stop the struggle. ⚠ Note also
    where the column is: a diagonal on the GAS block -- the fix this was
    scheduled as -- could not have reached it."""
    assert _burn(burn_net, 690.0, 0.002, 0.10, rtol=1e-8, atol=1e-11) == (
        pytest.approx(0.016, rel=1e-6)
    )


def test_the_default_tolerance_answers_are_bit_identical_to_the_unbounded_ones(
    burn_net,
):
    """⚠ THE HALF THAT REJECTED THE FIRST BOUND. A constant ceiling of 1.0 moved
    the O2-rich burner and seven other examples; this one leaves both runs where
    they were, to every digit either prints."""
    assert _burn(burn_net, 690.0, 0.002, 0.10) == pytest.approx(
        0.0160000005, abs=5e-11
    )
    assert _burn(burn_net, 650.0, 0.02, 0.40) == pytest.approx(
        0.1600000374, abs=5e-11
    )


def test_the_bound_does_not_bind_on_a_single_vessel(burn_net):
    """⚠ ON A VESSEL. IT DOES BIND ON A RIG AND THAT IS NOT HIDDEN:
    ``fractional_distillation`` wants factor 3.252e+12 and is clamped in 232 of
    its 1833 Jacobians, which moves its three cuts in the SEVENTH significant
    figure. Measured against a converged rtol 1e-8 run, neither the bounded nor
    the unbounded default is systematically nearer -- and at rtol 1e-8 the heart
    and tail come out bit-identical either way, so the two converge to the same
    answer. See ``validation/jacobian_bound.py`` panel 3, which is the standing
    version of this check.

    If THIS test ever starts clamping, the burner numbers above are the thing to
    re-measure -- against a converged run, not against the previous default."""
    v = Vessel(burn_net, volume=1.0, T=650.0, T_env=650.0, UA=1.0e4, kla=5.0,
               k_vent=0.0, k_diss=0.05, lle=False)
    v.charge({S8: 0.02, O2: 0.40, N2: 0.02})
    y0 = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    rhs = v.integrator.make_rhs(y0)
    jac = BoundedJacobian(rhs, 1e-9)
    for _ in range(40):
        jac(0.0, y0)
    assert jac.clamped == 0

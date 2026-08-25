"""Layer 4 -- the numerical Jacobian BDF differences, with the bound scipy lacks.

⚠ THIS MODULE EXISTS BECAUSE OF ONE MISSING BOUND IN ``scipy.integrate``, and the
whole of it is that bound plus the argument for it. Nothing here is chemistry: it
sees a callable and two float arrays, like everything else in this layer.

``num_jac`` differences a column at ``h = factor * max(atol, |y_j|)``. When the
difference it gets back is small compared with the rates elsewhere in the system
it concludes it probed too gently and multiplies that column's ``factor`` by ten
-- on every Jacobian, for ever. scipy FLOORS ``factor`` at ``NUM_JAC_MIN_FACTOR``
and never CEILINGS it, so a column it cannot difference is probed harder without
bound until ``factor`` overflows to ``inf``, ``h`` becomes ``nan``, and BDF is
handed a NaN Jacobian. The LU then fails with "array must not contain infs or
NaNs", a raise several tens of seconds after the column first went quiet.

This project has met that overflow three times and named it three ways -- a
vessel at rest (``VesselIntegrator.run``'s short-circuit), an empty second liquid
layer (``LAYER_REABSORB``) and a sealed flask with no headspace (``fragilities``)
-- and worked around it three times, each time in the chemistry. The bound
belongs here instead.

## ⚠⚠ PROBING HARDER IS NOT ALWAYS A QUESTION THAT CAN BE ANSWERED

Measured on the sulfur burner at rtol 1e-8 -- ``burn(690 K, s8=0.002, o2=0.10)``,
the one run S2's tolerance audit could not sweep at all. The column that
overflows is the SECOND LIQUID LAYER's SO2, holding 8.21e-29 mol. Its ``f`` is
the ``LAYER_REABSORB`` drain, which is strictly NEGATIVE for any positive
holding, so ``num_jac`` takes ``f_sign = -1`` and steps DOWNWARD -- straight into
the RHS's own ``np.maximum(y, 0.0)``. Every downward step, at every size, lands
on the same clamped state:

    h            -2.2e-24   -2.2e-19   -2.2e-14   -2.2e-09   -2.2e-04   -2.2e+06
    max |diff|    8.84e-29   8.84e-29   8.84e-29   8.84e-29   8.84e-29   8.84e-29
                  ^ CONSTANT over thirty decades of step size

against a ``scale`` of 8.37e-14 taken from another species' row. So
``max_diff < NUM_JAC_DIFF_SMALL * scale`` is true no matter what, the factor
climbs a decade per Jacobian -- twenty-eight of those calls are at one unchanged
state, t = 1.08799 -- and about two hundred later it reads 2.220e+307.
**No step size can measure a derivative the model has deliberately projected
away.**

⚠ NOTE WHERE THAT COLUMN IS. This fix was scheduled as a ``LAYER_REABSORB``-style
honest diagonal on the GAS block. The gas block is a route in -- an absent
species there does have a flat column -- but it is not the one that fires: of the
five triggers this project has recorded, the only one that still reproduces
overflows in LIQUID LAYER 2, and a diagonal on the gas block could not have
reached it. Worse, ``LAYER_REABSORB`` -- the precedent the fix was to copy -- is
what makes ``f`` negative and so points the probe at the clamp in the first
place. The named precedent was the cause.

## ⚠⚠ THE BOUND IS THE STATE'S OWN EXTENT, AND IT IS NOT A CONSTANT

The first version of this module capped ``factor`` at 1.0, on the reading that
``factor`` is the step as a fraction of the variable's own scale, so ``factor =
1`` moves the variable by all of itself. **That reading is FALSE exactly where it
matters and the measurement said so.** ``y_scale`` is ``max(atol, |y_j|)``, so
for a species at or below ``atol`` the fraction is of ATOL, not of the variable:
``factor = 149`` on an absent species is a 1.5e-7 mol probe of a 0.1 mol flask,
which is a perfectly good probe. Measured, on ``roasting_and_the_catalyst_gate``:

    ceiling      SO2 in the flask       what the solver WANTED
    inf              0.000201 mol       1.490e+02
    1e+6             0.000201 mol       1.490e+02
    1e+2             0.000201 mol       1.490e+02
    1.0              0.000197 mol       clamped -- and the answer moved

⚠ **A ceiling of 1.0 moved a quotable digit in a healthy run**, and it was not
alone: eight of the sixteen examples moved under it. So the bound cannot be on
``factor``. It has to be on the STEP, and the honest statement is

    a difference quotient is a derivative of THIS system only while the probe
    stays inside it -- you cannot learn anything about a state by moving one of
    its components further than the whole state extends

i.e. ``|h_j| <= max_i |y_i|``, which is ``factor_j <= max_i |y_i| / max(atol,
|y_j|)``. It is a bound per column and per call, computed from the state, with no
constant in it at all.

On a single VESSEL it never binds: the largest ``factor`` any single-vessel
example asks for is 1.490e+09 (``extraction``) against a bound of order 1e11-1e12
for a state carrying a temperature at ``atol = 1e-9``. Where it binds by design is
the runaway itself -- the burner's frozen column reaches the bound at 6.9e13
(690 K over ``atol = 1e-11``) and stops there instead of at ``inf``. Swept on that
run, EVERY finite ceiling from 1e2 to 1e14 turns the raise into 0.0160000000, so
what fixes it is finiteness, and the value is free to be the one that means
something.

## ⚠⚠ IT DOES BIND ON A RIG, AND THAT IS MEASURED RATHER THAN CLAIMED AWAY

``examples/fractional_distillation.py`` -- fourteen coupled vessels -- wants
``factor`` **3.252e+12** and gets clamped in **232 of its 1833 Jacobians**. So the
honest statement is not "this is inert", it is "this is inert on a vessel and
CHANGES A RIG, by this much":

    quantity   converged (rtol 1e-8)   default UNBOUND     default BOUND
    forerun            0.43671495         0.43671550        0.43671561
    heart              0.55620830         0.55620760        0.55620765
    tail               0.07016219         0.07016210        0.07016229
    pot T / K        408.20578700       408.20567700      408.20573700

⚠ **AT THE TIGHT TOLERANCE THE BOUND IS INERT**: heart and tail come out
BIT-IDENTICAL bounded and unbounded, forerun differs by 1e-8 and the pot by 5e-6.
The two converge to the same answer. At the DEFAULT tolerance neither is
systematically nearer it -- bounded is closer on the heart and the pot, unbounded
on the forerun and the tail, and every difference is at or below 1e-6 relative,
**three decades below the 1e-3 band ``validation/tolerance_audit.py`` declares as
the point where a quotable digit moves.** So what moved is solver noise at the
default tolerance and not the answer.

⚠ AND WHAT THE RIG WANTED IS WORTH LOOKING AT BEFORE MOURNING IT. ``factor``
3.25e+12 against ``atol = 1e-9`` is a probe of **3250 units** on a species holding
nothing, in a rig whose whole contents are a few mol and whose temperatures are a
few hundred K. The RHS is being evaluated a thousand vessel-loads outside itself,
and whatever it returns there is fiction. The seventh-figure move is the
difference between two fictions, and the bound is what says so. ⚠ Note also that
the rig runs ~122 Jacobians per solve against the ~316 an overflow needs: it is
one longer run away from the same crash.

⚠ WHAT IT DOES NOT FIX, STATED. The burner still takes ~50 s at rtol 1e-8 where
it takes 0.8 s at the default. BDF is genuinely struggling with a liquid layer
holding 1e-29 mol, and the bound only stops that struggle from ending in a NaN.
The 1.0 ceiling ran it in 2.6 s -- which looked like a speedup and was a
different Jacobian that BDF happened to like, on a run whose answer it was
moving elsewhere. **A faster wrong number is not a better one.**

WHAT IT IS ALSO NOT. It does not make a flat column non-flat: a species genuinely
absent from a sealed flask still has an identically zero column, and zero is the
CORRECT derivative for it. What changes is that ``num_jac`` stops treating "I
measured zero" as "I failed to measure", and BDF gets the zero.
"""
from __future__ import annotations

import numpy as np
from scipy.integrate._ivp.common import EPS, num_jac
from scipy.optimize._numdiff import group_columns
from scipy.sparse import csc_matrix, issparse

# The smallest relative step the bound may ever impose. This is ``num_jac``'s own
# starting factor, so the bound can never make a probe FINER than scipy would
# have begun with -- which matters only for the degenerate all-zero state, where
# ``max|y|`` is 0 and the bound would otherwise be 0 and stall the differencing
# outright. Every non-degenerate state is bounded far above this.
FACTOR_FLOOR = EPS ** 0.5


def factor_bound(y: np.ndarray, threshold) -> np.ndarray:
    """Per-column ceiling on ``num_jac``'s ``factor``: the step may not exceed
    the largest component of the state it is probing.

    ``num_jac`` uses ``|h_j| = factor_j * max(threshold, |y_j|)``, so requiring
    ``|h_j| <= max_i |y_i|`` is a ceiling on ``factor_j`` directly.
    """
    y = np.abs(np.asarray(y, dtype=float))
    extent = float(y.max()) if y.size else 0.0
    return np.maximum(extent / np.maximum(threshold, y), FACTOR_FLOOR)


class BoundedJacobian:
    """BDF's own numerical Jacobian with ``factor_bound`` imposed on ``factor``.

    Pass an instance as ``solve_ivp(..., jac=)``. It replicates exactly what
    ``BDF._validate_jac`` does when ``jac is None`` -- one RHS call for ``f``,
    then ``num_jac`` over the columns, carrying ``factor`` between calls -- and
    then clamps. With the clamp lifted it is bit-for-bit the default path, which
    is how the "inf" rows of the sweeps above were taken.

    ⚠ ``jac_sparsity`` HAS TO BE CONSUMED HERE RATHER THAN PASSED ALONGSIDE.
    BDF ignores ``jac_sparsity`` entirely once ``jac`` is callable, so a rig that
    handed both to ``solve_ivp`` would silently lose its column groups -- the 10x
    that ``RigIntegrator.useful_sparsity`` exists to avoid paying.
    """

    def __init__(self, rhs, atol, sparsity=None, *, bounded: bool = True):
        self.rhs = rhs
        self.atol = atol
        self.bounded = bounded
        self.factor = None
        # The peak BEFORE the clamp, so an audit can see how hard the solver
        # wanted to push. Nothing else can see it once it has been clamped.
        self.peak_factor = 0.0
        self.clamped = 0
        self.njev = 0
        if sparsity is None:
            self.sparsity = None
        else:
            # ⚠ VERBATIM ``BDF._validate_jac``, INCLUDING NOT CONVERTING A DENSE
            # PATTERN. ``group_columns`` dispatches to ``group_dense`` or
            # ``group_sparse`` on the type it is handed, and the two do not have
            # to agree on which columns share a group. Converting first therefore
            # perturbs the rig's columns in different COMBINATIONS, which is a
            # different rounding of the same Jacobian: measured on
            # ``fractional_distillation``, the three cuts moved in the seventh
            # significant figure (0.43671550 -> 0.43671561) for no other reason.
            if issparse(sparsity):
                sparsity = csc_matrix(sparsity)
            self.sparsity = (sparsity, group_columns(sparsity))

    def _vectorized(self, t, y):
        """``num_jac`` wants a fun that takes a column stack; the RHS takes one
        state. This is verbatim what ``check_arguments`` builds for
        ``vectorized=False``."""
        y = np.asarray(y)
        if y.ndim == 1:
            return np.asarray(self.rhs(t, y), dtype=float)
        return np.stack(
            [np.asarray(self.rhs(t, y[:, k]), dtype=float)
             for k in range(y.shape[1])],
            axis=1,
        )

    def __call__(self, t, y):
        self.njev += 1
        y = np.asarray(y, dtype=float)
        f = np.asarray(self.rhs(t, y), dtype=float)
        J, factor = num_jac(
            self._vectorized, t, y, f, self.atol, self.factor, self.sparsity,
        )
        peak = np.nanmax(factor) if factor.size else 0.0
        if np.isfinite(peak):
            self.peak_factor = max(self.peak_factor, float(peak))
        if self.bounded:
            cap = factor_bound(y, self.atol)
            self.clamped += int(np.count_nonzero(~(factor <= cap)))
            np.clip(factor, None, cap, out=factor)
        self.factor = factor
        return J

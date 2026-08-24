"""Layer 4 -- does this liquid want to be two liquids?

Every other phase change in this project is a RATE toward an equilibrium the RHS
can evaluate pointwise: evaporation follows ``x*gamma*Psat - p``, crystallisation
follows ``x_sat - x``. Liquid-liquid equilibrium is the one that cannot be
written that way, and it is worth being precise about why, because the shape of
this module follows from it.

The equilibrium CONDITION is easy and has the same form as the others: two
liquid phases are at equilibrium when every species has the same activity in
both,

    gamma_i(x^I) x_i^I  ==  gamma_i(x^II) x_i^II

and ``vessel_integrator`` drives exactly that difference, so the dynamics need
nothing from this module. **The problem is that the condition is also satisfied
by the two phases being IDENTICAL.** That trivial solution always exists, it is
the one a relaxation started from a well-mixed flask sits on, and no amount of
integrating will leave it: a single phase is a fixed point of its own splitting
dynamics. Deciding whether that fixed point is a stable minimum or a saddle is a
GLOBAL question about the Gibbs surface, and answering it takes an iteration.

So the work is split the way this project splits everything discrete or
iterative -- the smooth relaxation lives in the RHS, and the decision lives at an
EVENT BOUNDARY, the same reasoning that put the METER edge's rate in a parameter
rather than a time window inside the ODE. This module is only ever called
between integrations.

## The test

Michelsen's tangent-plane criterion. A phase of composition ``z`` is stable if
and only if the Gibbs energy surface lies above its own tangent plane at ``z``
for every trial composition ``w``; equivalently, if the tangent plane distance

    tpd(w) = sum_i w_i [ ln w_i + ln gamma_i(w) - ln z_i - ln gamma_i(z) ]

is non-negative everywhere. Working with the unnormalised ``W_i`` makes the
stationary points of that surface the fixed points of a plain successive
substitution,

    W_i  <-  exp( d_i - ln gamma_i(w) ),     d_i = ln z_i + ln gamma_i(z)

and at any stationary point the modified distance

    tm = 1 + sum_i W_i ( ln W_i + ln gamma_i(w) - d_i - 1 )

is negative exactly when the trial phase is more stable than the feed -- i.e.
when the feed wants to split. Because ``tpd`` can have several minima, the
iteration is run from several starting points and the deepest one wins.

## What this does NOT do, deliberately

It does not FLASH. It reports "this liquid is unstable, and here is a
composition that is better", and the caller seeds a second phase with a little
material at that composition; the RHS relaxation then finds the tie line by
integrating, at a rate the caller controls. That is a real modelling choice with
a real consequence: **mass transfer between two layers is rate-limited in
practice, which is why a separatory funnel gets shaken**, and a flash would have
asserted instantaneous equilibrium instead. It also keeps the split independent
of the caller's step size, because the approach to equilibrium is an ODE rather
than a per-step correction.

⚠ **IONS ARE THE REASON THIS TEST GETS ELECTROLYTES RIGHT AT ALL**, and it took
a second activity convention to fix. Held at gamma = 1 -- which is what "no
UNIFAC decomposition" used to mean -- an ion is an ideal solute here: it
contributes mixing entropy that OPPOSES a split and then partitions evenly
between whatever phases do form, which is how a brine/toluene funnel came out
with a strongly ionic organic layer. The BORN term (``born``, see
``activity.py``) prices the charge transfer instead, so a trial phase made of
hydrocarbon converges with the ions expelled from it and the tie line lands where
a bench would put it.

⚠ **A NEUTRAL species with no UNIFAC decomposition is still held ideal**, and
that is unchanged and still reported upstream. So is the WITHIN-phase electrolyte
effect: nothing here knows that a concentrated brine is less ideal than a dilute
one, so salting-out still does not raise the driving force for a split. That errs
toward MISCIBILITY, which is the direction everything else in this module errs in.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from chemsim.numerics.activity import activity_coefficients

# Mole fraction below which a species is not worth starting a trial phase from.
# It can still ENTER one -- this only bounds how many iterations are run, and the
# cost of the test is one UNIFAC evaluation per iteration per trial.
TRIAL_THRESHOLD = 1.0e-3

# ln(0) guard. A species genuinely absent from the feed cannot appear in a trial
# phase, and is masked out rather than floored -- flooring it would let a species
# at exactly zero drive the split.
LN_FLOOR = 1.0e-300

# tm below this counts as unstable. Not zero: the trivial solution sits at
# tm == 0 exactly, so a tolerance is what distinguishes "a second phase" from
# "the same phase found again".
TM_UNSTABLE = -1.0e-6

# ... and the same tolerance in composition space. A trial phase this close to
# the feed IS the feed; accepting it would seed a second phase identical to the
# first, which is the trivial solution wearing a disguise.
TRIVIAL_DISTANCE = 1.0e-3

# Abandon a trial once it has landed this close to the feed, ten times tighter
# than the distance at which the result would be thrown away anyway.
#
# This is a pure speed fix and it matters more than it looks: the STABLE case is
# the common one -- almost every flask in almost every run holds one liquid --
# and on a stable feed every trial crawls toward the trivial solution and
# converges slowly, so the cheap answer ("no split") was costing ten times what
# the interesting one did. Measured on a five-species mixture: 22 ms for a
# stable feed against 1.8 ms for an unstable one, and the stable figure was paid
# at the start of every single integration. Cutting the trials off once they are
# demonstrably on their way to the feed itself does not change any verdict --
# that trial was going to be discarded either way.
TRIVIAL_EXIT = 1.0e-4

MAX_ITERATIONS = 40
CONVERGENCE = 1.0e-10


@dataclass(frozen=True)
class StabilityResult:
    """What the tangent-plane test found.

    ``unstable`` is the answer; ``composition`` is the trial phase that proved
    it, normalised, and is what a caller seeds a second liquid phase with;
    ``tm`` is how deep the tangent-plane violation was, which is reported rather
    than thresholded away so a marginal case is visible as marginal.
    """

    unstable: bool
    composition: np.ndarray
    tm: float
    trials: int


def stability_test(
    n_liquid: np.ndarray,
    nu: np.ndarray,
    R_k: np.ndarray,
    Q_k: np.ndarray,
    a_mn: np.ndarray,
    active: np.ndarray,
    T: float,
    ln_gamma_ref: np.ndarray | None = None,
    a_sat: np.ndarray | None = None,
    born: np.ndarray | None = None,
) -> StabilityResult:
    """Is a single liquid of this composition stable, or does it want to split?

    Takes amounts (they are normalised here) and the same UNIFAC parameter block
    the RHS uses, so the test and the dynamics cannot disagree about the
    thermodynamics -- there is one activity model in this project and both call
    it.

    ``a_sat`` is the per-species SATURATION ACTIVITY at this temperature (1.0
    for anything that does not crystallise) and it is not optional in practice
    -- see ``_is_a_liquid``. Without it a sparingly-soluble solid is reported as
    wanting a second LIQUID phase, which is the wrong resolution of a perfectly
    real instability.

    An ideal liquid never splits, and the test says so for free: with no group
    parameters every gamma is 1, ``tm`` is identically zero for every trial, and
    nothing is unstable. That is not a special case in the code, it is what the
    equations give.
    """
    n = n_liquid.shape[0]
    stable = StabilityResult(False, np.zeros(n), 0.0, 0)

    total = float(np.maximum(n_liquid, 0.0).sum())
    if total <= 0.0 or nu.shape[1] == 0:
        return stable
    z = np.maximum(n_liquid, 0.0) / total
    present = z > LN_FLOOR
    if int(present.sum()) < 2:
        return stable                      # one component cannot split

    gamma_z = activity_coefficients(
        z, nu, R_k, Q_k, a_mn, active, T, ln_gamma_ref, born
    )
    d = np.where(present, np.log(np.where(present, z, 1.0)) + np.log(gamma_z), 0.0)

    # Start a trial phase from each species that is actually there in quantity.
    # Michelsen's guidance is to use several starts because the tangent-plane
    # surface is multimodal; "nearly pure i" is the standard set for a liquid,
    # where the interesting minima sit near the corners of the simplex.
    # A species below its melting point cannot be the bulk of a LIQUID phase --
    # a trial made mostly of it is a crystal. Excluding such species as seeds is
    # most of the fix; ``_is_a_liquid`` checks the converged trial as well.
    seedable = present & (z > TRIAL_THRESHOLD)
    if a_sat is not None:
        seedable = seedable & (a_sat > 0.999)
    candidates = np.flatnonzero(seedable)
    best = stable

    for j in candidates:
        W = np.where(present, 1.0e-3, 0.0)
        W[j] = 1.0
        converged = False
        for _ in range(MAX_ITERATIONS):
            w_total = W.sum()
            if w_total <= 0.0:
                break
            w = W / w_total
            # Heading for the feed itself: that is the trivial stationary point,
            # this trial would be discarded below, and on a stable mixture EVERY
            # trial does this. See TRIVIAL_EXIT -- it is the difference between
            # the cheap answer costing 22 ms and costing 2.
            if float(np.abs(w - z).sum()) < TRIVIAL_EXIT:
                break
            gamma_w = activity_coefficients(
                w, nu, R_k, Q_k, a_mn, active, T, ln_gamma_ref, born
            )
            W_new = np.where(
                present, np.exp(np.clip(d - np.log(gamma_w), -500.0, 500.0)), 0.0
            )
            delta = float(np.abs(W_new - W).max())
            W = W_new
            if delta < CONVERGENCE:
                converged = True
                break
        if not converged:
            # A trial that did not settle is not evidence either way, and
            # treating it as evidence is how a stability test invents phases.
            continue

        w_total = W.sum()
        if w_total <= 0.0:
            continue
        w = W / w_total
        gamma_w = activity_coefficients(
            w, nu, R_k, Q_k, a_mn, active, T, ln_gamma_ref, born
        )
        with np.errstate(divide="ignore", invalid="ignore"):
            terms = np.where(
                W > 0.0,
                W * (np.log(np.where(W > 0.0, W, 1.0)) + np.log(gamma_w) - d - 1.0),
                0.0,
            )
        tm = 1.0 + float(terms.sum())

        # The feed found again is not a second phase.
        if float(np.abs(w - z).sum()) < TRIVIAL_DISTANCE:
            continue
        # ... and neither is a crystal.
        if not _is_a_liquid(w, gamma_w, a_sat):
            continue
        if tm < best.tm:
            best = StabilityResult(tm < TM_UNSTABLE, w, tm, len(candidates))

    if best.trials == 0:
        return StabilityResult(False, np.zeros(n), 0.0, len(candidates))
    return best


def _is_a_liquid(
    w: np.ndarray, gamma_w: np.ndarray, a_sat: np.ndarray | None
) -> bool:
    """Would this trial composition actually be a liquid, or is it a crystal?

    ⚠ THE TANGENT-PLANE TEST CANNOT TELL, and this is not a detail. It compares
    liquid Gibbs energies, so a solution holding more of a sparingly-soluble
    SOLID than it can dissolve is correctly reported as unstable -- but the
    resolution of that instability is CRYSTALLISATION, not a second liquid
    layer. Benzoic acid in cold water is the case that found this: the test
    proposed a "liquid" that was 99% benzoic acid at 275 K, twenty degrees below
    its melting point, and the vessel then had a fictitious liquid layer and a
    real solid phase fighting over the same material. One test took 34 minutes.

    The criterion is the one the vessel already uses for dissolution: a phase
    supersaturated in a crystallising species is not a stable liquid. ``a_sat``
    is 1.0 for anything that does not crystallise, so this is a no-op for a
    network of ordinary solvents.
    """
    if a_sat is None:
        return True
    return bool(np.all(w * gamma_w <= a_sat * (1.0 + 1.0e-6)))


def merge_threshold_reached(n_minor: float, n_total: float, floor: float) -> bool:
    """Has a second liquid phase shrunk back to nothing worth carrying?

    Split out so the rule is stated once and is the same in the vessel and the
    rig: a phase is dropped when it is below an absolute floor OR is a
    vanishing fraction of the liquid. Both are needed -- the absolute test
    catches a phase that never grew, the relative one catches a phase that was
    real and has since been extracted away.
    """
    if n_total <= 0.0:
        return True
    return n_minor <= floor or n_minor / n_total <= 1.0e-9


# ---------------------------------------------------------------------------
# What fraction of a liquid had no activity model at all
# ---------------------------------------------------------------------------
# A neutral species with no UNIFAC decomposition is held at gamma = 1, and that
# is the one error in this module nothing announced. It matters here more than
# anywhere else in the project for a reason the module docstring already states
# in the other direction: AN IDEAL LIQUID NEVER SPLITS. Every species held at
# gamma = 1 contributes mixing entropy and no unfavourable interaction at all,
# so the omission does not merely add noise -- it pushes the answer toward
# "one phase" and toward "these two layers are more alike than they are".
#
# ⚠ WEIGHTED BY AMOUNT, NEVER BY PRESENCE. gamma = 1 on 1e-9 mol changes
# nothing; on a third of the layer it decides the answer. The honest quantity is
# the MOLE FRACTION of the liquid held ideal.
#
# ⚠ AND IONS ARE NOT COUNTED. An ion at gamma = 1 is a stated policy -- there is
# no Debye-Huckel term in this project -- and it has the BORN term for the part
# that decides partitioning, so it is not silent. A neutral organic at gamma = 1
# is. Two different things wearing the same value.

# The worst measured sensitivity of a split to one species being held ideal, as
# the displacement of the converged trial composition per unit of ideal mole
# fraction. Measured, not chosen: water/toluene 3:1 at 298.15 K and 358.31 K --
# the standing steam-distillation example -- with each of eighteen third
# components added at mole fraction f and the test run twice, once with that
# component modelled and once with it forced ideal. The displacement is linear
# in f in the small-f limit, and the slope splits the components into two
# families rather than scattering:
#
#     belongs in the MAJOR (aqueous) layer   0.02 - 0.25   methanol .. DMSO
#     belongs in the MINOR (organic) layer   0.96 - 3.46   DCM .. heptane
#
# The second family is where the damage is, and the mechanism is specific: held
# ideal, a species is not merely given the wrong gamma, it is dropped from the
# group composition every OTHER species' gamma is computed against -- so a
# hydrocarbon that should dominate the organic layer is instead kept out of the
# layer it defines. 3.46 is heptane at 298.15 K.
IDEAL_TIE_LINE_SENSITIVITY = 3.46

# ... so this is the ideal mole fraction at which the worst measured case can
# move a layer mole fraction by 0.01 -- one unit in the last digit
# ``Vessel.lle_report`` prints. Below it the lie cannot change a printed digit;
# above it, it can. 0.01 / 3.46 = 0.0029.
#
# ⚠ IT IS NOT A THRESHOLD BELOW WHICH THE ANSWER IS RIGHT, and the measurement
# is what says so: the error is LINEAR in the ideal fraction with no dead zone
# near zero, so there is no fraction at which the model becomes correct, only
# one at which the error becomes visible. For scale at the other end, the
# stable/unstable VERDICT itself did not flip anywhere below an ideal mole
# fraction of 0.44.
IDEAL_FRACTION_REPORT = 0.003


def held_ideal_fraction(
    n_liquid: np.ndarray, gamma_active: np.ndarray, ionic: np.ndarray
) -> tuple[float, np.ndarray]:
    """How much of this liquid has no activity model, and which species.

    Returns the mole fraction of the liquid that is NEUTRAL and held at
    gamma = 1, and the per-species mole fractions making it up (zero everywhere
    else, so the caller can name the offenders in order of size).
    """
    n = np.maximum(np.asarray(n_liquid, dtype=float), 0.0)
    total = float(n.sum())
    if total <= 0.0:
        return 0.0, np.zeros_like(n)
    silent = (~np.asarray(gamma_active, dtype=bool)) & (
        ~np.asarray(ionic, dtype=bool)
    )
    x = np.where(silent, n / total, 0.0)
    return float(x.sum()), x

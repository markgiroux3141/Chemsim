"""Layer 4 -- the coupled vessel core: composition, three phases, and temperature.

``Integrator`` solves an isothermal reactor at fixed T. This solves the thing a
flask actually does: react in liquid or vapour, evaporate, dissolve, crystallise,
vent, lose heat, and change its own temperature while doing so -- all in ONE stiff
system, so the feedback loops are resolved by the solver rather than smeared
across an outer stepping loop.

Those loops are the whole point. An exothermic reaction heats the vessel; the
higher temperature accelerates it (Arrhenius) but also lowers its equilibrium
constant (detailed balance, Layer 3); heating raises the vapour pressure so the
solvent evaporates and latent heat pulls the temperature back down; it also raises
solubility, so a product that had crystallised redissolves. None of that is
scripted. In particular **neither the boiling point nor the melting point is
looked up**: a flask boils when its summed partial pressures reach ambient, and a
solid melts when the ideal-solubility limit reaches unity, which happens exactly
at Tm because that is what the equation says.

State vector, length 4n+1:

    y = [ n_liquid1 (n) | n_liquid2 (n) | n_gas (n) | n_solid (n) | T ]

Moles, not concentrations -- deliberately. Concentration needs a volume, and the
liquid volume is itself a state-dependent quantity that shrinks as things boil
off or crystallise out. Moles stay meaningful when the flask boils dry.

TWO LIQUID BLOCKS, because a flask can hold two layers. Everything that touches
a liquid now happens twice: reactions run in both, both evaporate into the shared
headspace, a solid dissolves into both, and a species crosses between them until
its ACTIVITY is equal on the two sides. ``lle.py`` holds the one piece that
cannot live in here -- the decision that a second phase should exist at all,
which is a global question about the Gibbs surface rather than a local rate.

⚠ **With the second block empty, every term below reduces EXACTLY to the
one-liquid RHS**, term by term and not merely closely: ``gate2`` is zero, phase
2's volume is below ``V_LIQUID_MIN`` so no reaction runs in it, its dissolution
pool is zero, and the liquid-liquid flux carries the product of both layer gates.
That is deliberate and it is load-bearing -- it is what lets a vessel that never
splits reproduce every number this project has measured, so a moved invariant
means a real phase split and never an accounting change.

⚠ And it is why ``_dryout_gates`` takes N1 + N2 for its dry half rather than N1:
with layer 2 empty the two arguments coincide, ``wet + dry`` is exactly 1, and the
pair is the same single expression the one-liquid RHS always had.

STILL PURE ARRAYS. This module knows nothing about molecules, SMILES, RDKit,
Antoine, Rackett, or Joback. Every property arrives as a numpy array of
polynomial coefficients, fitted upstream at setup time. That is what keeps this
the Rust/PyO3 seam.

One model does not fit that mould, and it is worth naming: activity coefficients
depend on composition, not just on temperature, so they cannot be collapsed to a
polynomial in advance. They arrive as a PARAMETER block instead (see
``activity.py``) and are evaluated in the RHS. The arrays got richer; the
contract did not change.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from chemsim.constants import R, R_L_BAR
from chemsim.network import KineticArrays
from chemsim.numerics.activity import (
    activity_coefficients,
    born_ln_gamma,
    oster_permittivity,
)
from chemsim.numerics.jacobian import BoundedJacobian
from chemsim.numerics.lle import (
    TRIVIAL_DISTANCE,
    StabilityResult,
    merge_threshold_reached,
    stability_test,
)

# Numerical floors. These keep the RHS finite in degenerate states (dry flask,
# flooded vessel) rather than letting the solver walk into a divide-by-zero.
V_LIQUID_MIN = 1.0e-12   # L
V_GAS_MIN = 1.0e-6       # L
# Fractional slack on a vessel's own volume before its contents are refused as not
# fitting. See ``VesselIntegrator.check_capacity``.
#
# ⚠ IT IS 10% AND NOT ROUND-OFF, AND THE FIRST VERSION AT 0.1% WAS WRONG -- twelve
# tests said so. A vessel's volume here is NOMINAL, the way a 1 L flask's is: "one
# litre of 1 M acetic acid" is 55.4 mol of water plus a mole of acid and comes to
# 1.006 L by Rackett molar volumes, which is a flask filled to its neck and not a
# mistake. Real glassware holds well over its graduation for exactly that reason.
#
# What this has to separate is a full flask from an arithmetic result nobody can be
# shown, and the real cases are nowhere near each other: the legitimate ones sit at
# 1.006x, an overfilled flask in ``validation/robustness.py`` at 3.6x, and a vessel
# dissolving the room at 116x. Nothing lives between 1.1 and 3.6, so this is not a
# threshold chosen to make anything pass.
CAPACITY_SLACK = 0.10
CP_MIN = 1.0e-6          # J/K
T_MIN, T_MAX = 1.0, 5000.0
# ⚠ THE SCALE, IN MOL, OVER WHICH "THIS FLASK HAS A LIQUID PHASE" TURNS OFF --
# AND THE TWO GATES BUILT ON IT MUST BE DISJOINT. 1e-6 mol of water is 18 ug, far
# below anything a bench would call a pool, and three decades above the solver's
# own 1e-9 atol, which is the gap that makes the transition resolvable at all.
#
# ⚠ IT USED TO BE THREE OVERLAPPING TERMS AND IT CREATED MATTER. Written as a
# RAMP, ``wet = N/(N + DRYOUT_MOLES)`` is non-zero for EVERY N > 0, so layer 1's
# evaporation at ``wet`` strength and the dry-flask branch at ``1 - wet`` were
# both live inside the band -- and the mole fractions were floored on the SAME
# scale, ``x = nL/max(N, DRYOUT_MOLES)``, so inside it they summed to LESS THAN
# ONE (0.57 at N = 5.7e-7) and every activity was understated as well. MEASURED on
# a sulfur burner, which walks into this because sulfur boils at 717.8 K and a
# burn run near that holds only a TRACE of condensate:
#
#     T / K   liquid held         created O, relative   after
#       550    6.85e-03 mol            1.8e-12          1.8e-12
#       650    1.52e-03                1.1e-09          1.1e-09
#       675    8.29e-07  IN BAND       2.3e-03          2.1e-13
#       690    5.43e-07  IN BAND       1.1e-01          8.3e-14   reads 111% yield
#       700    5.73e-07  IN BAND       2.9e-05          2.8e-14
#       730    3.81e-07                2.0e-09          8.3e-14
#       900    6.86e-08                1.7e-08          4.2e-14
#
# Clean on both sides and wrong only inside: the signature of two gates meeting
# rather than of one bad one.
#
# ⚠ AND LOWERING THE MOLE-FRACTION FLOOR ALONE ONLY MOVED IT, measured before the
# fix below: at a floor of 1e-9 the 690 K case went 1.1e-1 -> 1.4e-8 but 700 K got
# WORSE (2.9e-5 -> 3.0e-4), and at 1e-12 the trouble reappeared at 730 and 900 K.
# That is the relocate-the-fight signature ``_layer_gates`` already records across
# its three attempts, and it is what says the fix is DISJOINTNESS rather than a
# better constant.
#
# So the pair is built with ``_phase_gates`` -- the same construction LAYER_EPS
# uses -- and here disjointness is a THEOREM rather than a choice of numbers:
# ``grow`` is non-zero only ABOVE DRYOUT_MOLES and is evaluated on N1, ``drain``
# is non-zero only BELOW it and is evaluated on N1 + N2, and N1 <= N1 + N2. So no
# flask can have both, and they are flat where they meet.
#
# ⚠ WHY THE LAYER_EPS PRECEDENT AND NOT THE SOLID_GATE_TIME ONE, because the two
# disagree. SOLID_GATE_TIME refused a smoothstep: its companion is PRECIPITATION,
# which is ungated by design, so something had to carry a bounded non-zero slope
# at zero. Here the companion is the dry-flask branch, which is itself gated and
# is exactly 1 at N = 0, so IT holds the empty-flask diagonal and the smoothstep's
# flatness is a pure gain -- it removes the -1/DRYOUT_MOLES = -1e6 Jacobian entry
# that the old ``1 - wet`` form carried for a flask holding NO liquid at all.
#
# ⚠ WHAT IS GIVEN UP, STATED RATHER THAN HIDDEN. Below DRYOUT_MOLES layer 1 cannot
# EVAPORATE at all (it can still receive condensation), so a sub-microlitre film
# no longer pins its own vapour at psat. That is a RETENTION and not a creation --
# attenuating a flux cannot make matter -- and the trace is stranded, not lost.
DRYOUT_MOLES = 1.0e-6
# mol. NOT A SCALE: the smallest denominator a mole fraction may be divided by,
# whose only job is to keep 0/0 out of ``x = nL/N`` for an exactly empty layer.
#
# ⚠ THE UNITS SAY WHAT IT IS AND THE MAGNITUDE SAYS WHAT IT IS NOT. A clamp that
# exists to avoid 0/0 must not double as a second gate, which is exactly what went
# wrong while this WAS DRYOUT_MOLES -- the floor bit precisely where the gate was
# still open. 1e-30 mol is 24 decades below DRYOUT_MOLES and 21 below the solver's
# atol, so nothing an integration can reach puts it in contention; and because the
# RHS clamps ``nL`` non-negative before summing, x stays inside [0, 1] by
# construction rather than by this constant's value.
#
# THE PROPERTY TO PRESERVE, AND IT IS CHECKABLE: *the mole fractions of any layer
# something is gated ON must sum to 1.* Layer 2 already satisfied it by accident
# of shape -- its floor is LAYER_EPS and its gate is a smoothstep at the SAME
# scale, so ``gate2`` is identically zero wherever that floor binds. Layer 1's
# gate was a ramp at the same scale, so it was not.
MOLE_FRACTION_DENOM = 1.0e-30
# mol -- the FLOOR on the dissolution gate's scale, not the scale itself. See
# SOLID_GATE_TIME: the scale is normally set by the driving force, and this
# only stops it collapsing to zero at exact saturation. It used to BE the scale.
SOLID_EPS = 1.0e-9
# ⚠ THE SCALE OF THE DISSOLUTION GATE, SET BY THE DRIVING FORCE RATHER THAN BY A
# CONSTANT. Seconds -- the gate's scale is ``SOLID_GATE_TIME * k_diss * excess``,
# a driving force in mol/s times a time, so what this constant actually says is
# *no crop may dissolve faster than its own amount per SOLID_GATE_TIME*. This
# is the third `N/(N + eps)` knee this codebase has had to fix (DRYOUT_MOLES and
# LAYER_EPS were the first two) and the first one where a constant eps was
# actively WRONG rather than merely awkward.
#
# The gate answers "you cannot dissolve a solid that is not there". Written with a
# constant scale, ``avail = nS/(nS + 1e-9)``, it is zero at nS = 0 but its slope
# there is 1e9, so an EMPTY solid block carries a Jacobian diagonal of
# ``k_diss * excess / eps``. MEASURED on the lead chamber: **-3.61e7 for NO,
# -3.95e7 for NO2 and H2SO4, -1.83e6 for water** -- for blocks holding NOTHING.
# That is the same 4e6-to-1.4e8 band LAYER_EPS records for the second liquid
# layer's identical knee. BDF then overshoots those blocks negative,
# ``project_non_negative`` zeroes them, and a species with no positive holding to
# settle against has matter CREATED. Harmless in ordinary chemistry -- an
# esterification absorbs it silently -- and not harmless at all when the species
# is a CATALYST, because a cycle's gain on its catalyst is unbounded: the
# carrier-free lead chamber reached 89% yield on 1.2e-4 mol of phantom NOx.
#
# ⚠ THE FIX IS NOT THE SMOOTHSTEP LAYER_EPS USED, AND THAT IS DELIBERATE. A
# smoothstep is zero AND FLAT at zero, which is why it needed LAYER_REABSORB as a
# companion to keep ``num_jac`` from inflating its perturbation factor on an
# undifferentiable column. A companion term here would sit opposite the
# PRECIPITATION branch, which is ungated by design (anything can nucleate), so the
# two would meet in exactly the overlapping-gate arrangement that made the
# benzoic-acid acidification unsolvable. One term has to govern this block near
# zero, so the gate itself has to carry a bounded, non-zero slope.
#
# It does that by making the scale proportional to the driving force instead of
# constant. The result is a resistance-in-series form -- the identity is
# ``1/rate = 1/(k_diss*excess) + 1/(nS/tau)`` -- so dissolution is limited BOTH by
# how far from saturation the solution is AND by how much solid is there to
# dissolve from, and the empty-block slope collapses to exactly ``1/tau`` for
# EVERY species, independent of the undersaturation that was driving it to 4e7.
# That independence is the property: the old knee got WORSE the more dilute the
# species was, which is why the most dilute one seeded the cycle.
#
# ⚠ IT IS A REGULARISATION AND NOT A PHYSICAL MODEL, and saying otherwise would be
# the kind of dressing-up this project refuses. Real dissolution is area-limited,
# i.e. proportional to nS^(2/3), whose slope at zero is INFINITE -- worse than
# what is being fixed. So the value is chosen by MEASUREMENT of the Jacobian it
# produces, swept on the chamber (columns: the empty-block diagonal, the largest
# entry anywhere in the solid columns, and the phantom NOx the carrier-free
# chamber creates in an hour):
#
#     tau      diagonal    solid columns   NOx created   H2SO4 (of 0.04 charged)
#     1e-9      3.9e+07        --           1.21e-04       3.58e-02   (89% yield)
#     1e-4      1.0e+04       1.41e+06      2.32e-12       8.51e-11
#     1e-3      1.0e+03       1.36e+05      4.34e-12       2.72e-10
#     1e-2      1.0e+02       1.29e+04      1.55e-20       1.55e-20
#     1e-1      1.0e+01       1.49e+04      1.55e-20       1.55e-20
#     1e+0      1.0e+00       1.51e+04      1.55e-20       1.55e-20
#
# **The solid columns stop shrinking at 1e-2**: below it the gate is the stiffest
# thing in the block, at and above it something else is, and 1e-1 is very slightly
# WORSE. So 1e-2 is the smallest value -- i.e. the least distortion of real
# dissolution -- at which this gate has stopped dominating. That is a measurement
# rather than a preference, which is the whole reason for taking the sweep.
#
# 10 ms is also far faster than anything the chemistry resolves (``k_diss`` is
# 0.01-0.05 /s, so bulk dissolution runs on 20-100 s), so the cap never binds on a
# real crop. It only ever regularises the empty block.
#
# What it does NOT touch: the equilibrium. ``excess -> 0`` drives the scale to zero
# and the gate to 1, so every solubility this project has measured is unmoved.
# Benzoic acid under water dissolves 0.026826 mol on the sweep's flask at EVERY
# row above, identical to six decimals, and a 1e-5 mol crop dissolves to exactly
# 0.0 at every row -- where the old constant knee left -9.4e-10 behind.
SOLID_GATE_TIME = 1.0e-2
# Pressure scale, bar, over which the vent blends the donor's composition between
# the vessel's headspace and the room's. See ``backflow_part``, which is where the
# form is argued. ZERO -- the exact switch -- and that is a MEASUREMENT, not a
# default nobody chose.
#
# ⚠ IT USED TO BE 1e-4 AND THE BAND WAS HALF OF THE VENT BUG. An open flask settles
# where ``k_vent dP`` matches its boil-off, which at the default conductance is
# dP ~ 3e-6 bar -- INSIDE a 1e-4 band, so the blend never resolved the direction of
# flow at all and half the outflow permanently left on the room's composition. A
# refluxing rig runs at dP ~ 2e-4 and so sat right at the band's edge: with the
# corrected form but the old scale, enough of the condenser's air came back down
# the vapour edge to hold 7% of the pot's headspace, which DEPRESSED THE REFLUX
# PLATEAU 352.89 -> 351.10 K. The plateau is an invariant, so the band cannot be
# allowed to reach the operating point of any real apparatus.
#
# ⚠ AND NO NON-ZERO SCALE IS FREE, which is the part worth keeping. ``backflow_part``
# has to be <= 0 with a zero at the origin, so the origin is a maximum, so it is
# quadratic there -- a counter-current against the bulk flow, sized by a numerical
# constant rather than by any physics. Swept in ``validation/vent_leak.py`` on the
# observable it actually corrupts, an open flask's oxidation cascade: acetaldehyde
# after an hour reads 2.97 / 3.01 / 3.19 / 3.76 / 4.17 mmol at 1e-4 / 1e-5 / 1e-6 /
# 1e-7 / 0. It is monotone, so it is the residue and not scatter, and 1e-6 is still
# 24% low.
#
# ⚠ A NARROW BAND IS WORSE THAN NO BAND, MEASURED. At 1e-8 the vapour-edge test
# takes 3507 solver steps against 224 at zero: BDF has to resolve a real derivative
# of order 1/scale, where a kink has nothing to resolve and costs a few rejected
# steps at the crossing. So the usual "smooth it" reflex inverts here.
#
# COST, stated rather than hidden: ``tests/test_rig.py`` goes 113 s -> 185 s, of
# which ~45 s is the rig legitimately keeping air it used to destroy (1e-6 also
# retains it and costs 140 s) and the rest is the kink. The constant is kept as a
# knob so the sweep above stays re-runnable.
DP_VENT_SMOOTH = 0.0
# Saturation fraction at which a solid starts counting toward its own melt. Sets
# the width of the melting range: x_sat reaches 1 exactly at Tm, so melting runs
# from wherever x_sat crosses this value up to Tm.
MELT_BLEND = 0.90

# How much of the liquid is moved into a newly detected second layer. Only a
# nudge off the trivial solution -- the RHS relaxation carries it the rest of
# the way, so this sets how long the split takes to appear, not where it lands.
SPLIT_SEED_FRACTION = 0.01

# Moles below which a second liquid layer is not a layer, and the scale of the
# SMOOTHSTEP that switches it on. 1e-5 mol is ~0.2 uL -- far below anything a
# bench would call a phase, and far ABOVE the ~1e-8 perturbation ``num_jac``
# uses to difference the Jacobian. That gap is the whole point.
#
# ⚠ WHY A SMOOTHSTEP AND NOT A ``N/(N + eps)`` RAMP -- which is what every phase
# gate in here used to be, and none of them is any more. An empty second layer
# sits at exactly zero, which is that ramp's knee --
# whose slope there is 1/eps. Differencing the Jacobian across that knee gave
# entries of 4e6 to 1.4e8 for a layer holding NOTHING, against 61 for the real
# one: five orders of magnitude of pure fiction, which BDF then had to resolve.
# It cost a 10x slowdown of the whole test suite and broke reflux outright,
# because ``num_jac`` inflates its perturbation factor against a column like
# that until it overflows. A smoothstep is zero AND FLAT at zero, so an empty
# layer contributes an identically zero Jacobian column instead.
#
# This is the third time this codebase has paid for a switch that was not
# smooth -- see DRYOUT_MOLES and MELT_BLEND. MELT_BLEND only ever needed
# continuity; this one needed a continuous DERIVATIVE as well, and DRYOUT_MOLES
# turned out to need one too, for exactly the reason argued here.
LAYER_EPS = 1.0e-5

# 1/s, how fast material below that scale rejoins layer 1. This is the
# continuous form of the discrete merge ``merge_phases`` performs at a boundary,
# and it exists for TWO reasons, one physical and one numerical.
#
# Physically: a sub-microlitre "layer" is not a layer, and material stranded
# there should go back into the bulk rather than sit forever.
#
# ⚠ Numerically it is what keeps ``num_jac`` sane, and the mechanism is worth
# understanding because it is the second half of a trap this project has already
# documented once. Gating layer 2 with a smoothstep made its Jacobian column
# perfectly FLAT at zero -- which fixed the 1e8 entries but walked straight into
# the other failure mode: num_jac finds every finite difference in that column
# below its "too small" threshold, inflates the perturbation factor for it on
# every call without bound, overflows to inf, and hands BDF a NaN Jacobian. The
# LU then fails with "Factor is exactly singular". A column that is exactly zero
# is as bad as one that is enormous.
#
# This term puts a small, honest -k on the diagonal of every empty-layer column,
# so the difference is real, the factor never inflates, and the block is simply
# stiff-free rather than pathological.
LAYER_REABSORB = 1.0


def _smoothstep(u: float) -> float:
    """C1 ramp from 0 to 1 over u in [0, 1]: flat at both ends."""
    s = min(max(u, 0.0), 1.0)
    return s * s * (3.0 - 2.0 * s)


def backflow_part(dP: float, scale: float) -> float:
    """The INFLOW half of a bulk flow, as a smooth function that is never positive.

    ⚠ THIS IS WHAT MAKES A BULK FLOW SELF-LIMITING, and getting it wrong destroyed
    ~100x an open flask's own air for as long as the vent has existed. The bulk
    terms -- the vent here and the rig's vapour edge -- move gas along a total
    pressure difference and carry the DONOR's composition. Written the obvious way,

        vent = k dP (w x_out + (1 - w) x_ambient),   w = sigma(dP / scale)

    the second term is a mixed-sign product: at a small POSITIVE dP the flow is
    outward but ``1 - w`` is still ~0.5, so half of an OUTflow leaves carrying the
    ROOM's composition. The room is 79% nitrogen, so the vessel exports nitrogen at
    a rate that does not depend on how much nitrogen it has -- and once the block
    crosses zero, the honest ``x_out`` branch is exactly zero (``x_out`` is computed
    from a clamped ``nG``) while this one carries on. Nothing restores it.

    It is not a corner case: an open flask settles where ``k_vent dP`` matches its
    boil-off, and at ``k_vent = 1e3`` that is dP ~ 3e-6 bar, i.e. 0.03 of the
    smoothing scale. Measured there, ``1 - w = 0.485``: essentially half the vent
    permanently ran on the wrong composition. That also explains why the leak
    "scaled with k_vent" -- a smaller conductance needs a bigger dP to pass the same
    flux, which pushes the operating point out of the smoothing band. The band was
    the problem, not the conductance.

    The cure is to write the flow as a full stream of the donor's composition plus a
    CORRECTION that is only ever an inflow::

        flux = k [ dP x_out + backflow(dP) (x_ambient - x_out) ]

    with ``backflow <= 0`` everywhere. Three properties come out of that form, and
    they are the reasons for it:

    * **it sums to ``k dP`` exactly, at every dP**, because ``x_out`` and
      ``x_ambient`` are both normalised and their difference sums to zero. So the
      pressure relaxation -- which is what pins every boiling plateau in this
      project -- is untouched by the smoothing, bit for bit;
    * **every OUTWARD contribution is proportional to ``x_out``**, hence to the
      donor's own ``nG_i``. That is the self-limiting property the evaporation and
      liquid-liquid fluxes already have: a species that is not there cannot leave;
    * **a species absent from the donor can only be GAINED.** With ``x_out_i = 0``
      the whole flux is ``k backflow x_ambient,i <= 0``, i.e. inward.

    ⚠ NO SMOOTH FORM IS FREE HERE, and the residue is worth naming rather than
    hiding. ``backflow <= 0`` with ``backflow(0) = 0`` makes zero a maximum, so the
    function is quadratic there and a small counter-current survives on the outflow
    side: |backflow| peaks at ~0.088 ``scale``. That is a counter-diffusion against
    the bulk flow, which is real but is here sized by a numerical constant -- so
    ``scale`` is kept small and its effect is SWEPT in ``validation/vent_leak.py``
    rather than asserted. A softplus was tried and rejected for the opposite defect:
    it is 0.69 ``scale`` at zero, which is a permanent leak from a vessel at rest.

    At ``scale = 0`` this is exactly ``min(dP, 0)``, and the C1 blend is the only
    thing the scale buys.
    """
    if scale <= 0.0:
        return min(dP, 0.0)
    tau = np.tanh(dP / scale)
    return -0.5 * (1.0 - tau) * tau * dP


def _avail(n_solid: np.ndarray, drive: np.ndarray) -> np.ndarray:
    """Fraction of the dissolution driving force a crop of ``n_solid`` can supply.

    ``drive`` is ``k_diss * excess`` -- the rate dissolution would run at if the
    solid were unlimited, in mol/s. The gate returns ``nS / (nS + eps)`` with

        eps = max(SOLID_GATE_TIME * drive, SOLID_EPS)      mol

    so the product ``drive * _avail`` is the harmonic combination of ``drive`` and
    ``nS / SOLID_GATE_TIME``: two resistances in series, a thermodynamic one and
    an availability one.

    ⚠ THE ONE PROPERTY THIS EXISTS FOR is the slope at an EMPTY block, which is

        d(drive * avail)/d(nS) |_0  =  drive / eps  =  min(1 / tau, drive / SOLID_EPS)

    -- BOUNDED by ``1 / tau`` however undersaturated the solution is, where a
    constant ``eps`` made it grow WITH the undersaturation and reached 4e7. It is
    also non-zero wherever there is any driving force at all, which is what lets
    this be a single term rather than the smoothstep-plus-companion pair
    ``_layer_gates`` needed. See SOLID_GATE_TIME for the whole argument.

    ``drive`` may be negative (a supersaturated solution); the floor is what keeps
    the scale positive there, and the caller does not use this branch anyway --
    precipitation is ungated, because anything can nucleate.
    """
    eps = np.maximum(SOLID_GATE_TIME * drive, SOLID_EPS)
    return n_solid / (n_solid + eps)


def _layer_gates(n_total: float) -> tuple[float, float]:
    """(grow, drain) for a liquid layer holding ``n_total`` moles.

    ⚠ THESE MUST NOT OVERLAP, and that is the whole design. ``grow`` switches
    the layer's own physics on -- evaporation, reaction, dissolution and the
    liquid-liquid flux -- and ``drain`` returns sub-threshold material to layer
    1. When both were active in the same band they FOUGHT: the flux pumped
    material into a layer too small to be one while the reabsorption pushed it
    back, and the balance point between them was a spurious equilibrium sitting
    exactly where ``a2`` is steepest in ``N2``. It made the benzoic-acid
    acidification unsolvable, and turning off EITHER term alone fixed it --
    which is the signature of two opposed terms rather than one bad one.

    So they are made disjoint: ``drain`` acts only below ``LAYER_EPS`` and
    ``grow`` only above it. Both are C1, both are flat where they meet, and
    ``drain`` is 1 at zero -- which is also what keeps an empty layer's Jacobian
    diagonal honestly non-zero instead of exactly zero.

    ⚠ DISJOINT IS NOT THE RIGHT SHAPE FOR EVERY GATE PAIR, and ``_dryout_gates``
    is the counter-example -- measured, in the session that closed the dryout
    band. Disjointness leaves a DEAD ZONE where both halves are zero. Here that
    zone is harmless: a second layer sitting at LAYER_EPS with nothing acting on
    it just sits, and layer 1 carries the flask. Where the pair is the flask's
    ONLY phase-change channel, the same dead zone stops a condenser accumulating
    and superheats the pot it is refluxing. See ``_dryout_gates``.
    """
    grow = _smoothstep((n_total - LAYER_EPS) / LAYER_EPS)
    drain = 1.0 - _smoothstep(n_total / LAYER_EPS)
    return grow, drain


def _dryout_gates(n_layer1: float, n_liquid: float) -> tuple[float, float]:
    """(wet, dry) for layer 1's evaporation and the DRY-FLASK branch beside it.

    ⚠ THIS PAIR IS COMPLEMENTARY AND NOT DISJOINT, WHICH IS THE OPPOSITE OF
    ``_layer_gates``, AND BOTH SHAPES ARE MEASURED. The two branches are not
    rivals: they are ONE flux written two ways, and the crossover is the point at
    which "this flask has a liquid composition" stops being a meaningful
    statement. ``wet`` scales Raoult against the layer's own activity; ``dry``
    scales the pure-component statement that vapour over an empty flask does
    nothing unless it exceeds ``psat``. So they have to SUM TO ONE rather than
    exclude each other.

    Made disjoint instead -- ``grow`` above the scale, ``drain`` below it, the
    ``_layer_gates`` shape -- both halves are exactly zero AT the scale, and a
    condenser is precisely the thing that comes to rest there. MEASURED: the head
    stalled at 9.998e-07 mol against the 1e-4 a working charge needs, the pot lost
    its latent-heat sink, and the REFLUX PLATEAU went 352.89 -> 370.39 K. Same
    relocate-the-fight signature as the ramp, one vessel over.

    So: one ``_smoothstep``, two arguments. ``wet`` on layer 1 alone, because
    Raoult needs layer 1 to have a composition; ``dry`` on BOTH layers, because a
    flask holding all its liquid in layer 2 is not a dry flask. With a single
    liquid the two arguments coincide and ``wet + dry == 1`` EXACTLY, so there is
    neither a dead zone nor a double count. With two layers ``dry <= 1 - wet``, so
    the pair can only ever UNDER-count, and layer 2's own ``grow`` covers the
    remainder.

    ⚠ WHY A SMOOTHSTEP RATHER THAN THE RAMP ``N/(N + DRYOUT_MOLES)`` IT REPLACES.
    The ramp is complementary too, and by itself it was never the wrong answer --
    the mole-fraction FLOOR sharing its scale was, see MOLE_FRACTION_DENOM. But
    the ramp's slope at zero is 1/DRYOUT_MOLES = 1e6, so a flask holding NO liquid
    carried a fictional -1e6 Jacobian entry on the dry branch: the same knee
    LAYER_EPS and SOLID_GATE_TIME each had to remove. A smoothstep is zero AND
    FLAT at zero, so an empty flask's column is honestly zero.

    ⚠ THE ONE CASE WHERE THE OVERLAP COULD STILL OPPOSE, STATED RATHER THAN
    ASSUMED. ``a1 * psat - p`` and ``min(psat - p, 0)`` carry the SAME sign
    wherever the second is non-zero: that needs ``p > psat``, and ``a1 <= 1`` then
    forces the first negative too, so the two branches cannot fight. The argument
    leans on ``a1 <= 1``, which a species with gamma > 1 can break. It would take
    a supersaturated vapour over a sub-microlitre pool of a strongly non-ideal
    mixture, it is inherited unchanged from the ramp rather than introduced here,
    and it is written down so the next person finds it stated instead of assumed.
    """
    wet = _smoothstep(n_layer1 / DRYOUT_MOLES)
    dry = 1.0 - _smoothstep(n_liquid / DRYOUT_MOLES)
    return wet, dry

# Ionic mole fraction above which a liquid holds enough charge for the ion model
# to be load-bearing -- see ``VesselIntegrator.split_phases``. Set well above
# water's own autoionisation (~2e-9 mole fraction in pure water) and well below
# any real electrolyte, so "there is dissolved salt in this" and "this is
# nominally neutral water" are cleanly separated.
#
# ⚠ THIS USED TO BE A BLANKET REFUSAL and is not one any more. Ions had no activity
# model, so equality of activity across an interface put them at equal mole
# fraction in water and in toluene, and every electrolyte split was refused
# outright -- which took the most common workup in preparative chemistry with it.
# The BORN term prices that transfer now (``properties/dielectric.py``), so this
# threshold only decides when the ion model has to be CHECKED, and the two checks
# below are what can still refuse.
IONIC_SPLIT_LIMIT = 1.0e-6

# ... and the two things that can still refuse an electrolyte split, both of them
# narrow and both reported by name.
#
# BORN_COVERAGE_MIN: the fraction of a PROPOSED LAYER's volume that must have a
# known relative permittivity before that layer is allowed to exist. A layer whose
# polarity is unknown gives its ions no Born term at all -- i.e. gamma = 1, i.e.
# exactly the wrong answer this work replaced -- so it is refused instead. The
# test is applied to the tangent-plane test's TRIAL composition as well as to the
# feed, because it is the trial that says what the second layer would be made of,
# and a feed that is 95% water can still propose a layer that is 100% unpriced.
BORN_COVERAGE_MIN = 0.9

# Mole fraction below which a species is a trace and cannot be the bulk of
# anything. Used only to decide whether an unpriced ION is worth refusing over.
BORN_TRACE = 1.0e-6

# ⚠ HOW FAR NEGATIVE AN AMOUNT MAY GO BEFORE THE SOLVE IS CALLED A FAILURE
# RATHER THAN AN EXCURSION, and this exists because ``sol.success`` is NOT
# sufficient on its own.
#
# The case that proved it: an unclipped Born term gave brine/toluene chloride at
# +3.07e9 mol in one layer and -3.07e9 in the other -- a cancelling dipole
# fourteen orders of magnitude larger than the material present. BDF reported
# SUCCESS. ``project_non_negative`` then did exactly its job, cancelled the pair,
# and returned a state that looked perfectly plausible. **The silent wrong answer
# was one projection away, and nothing in the pipeline was in a position to notice
# it**, because everything downstream only ever sees the projected state.
#
# So the RAW solver output is checked before anything tidies it, and the question it
# asks is deliberately coarse: **is this a perturbation of a physical state at all,
# or is it fiction?** Not "is it clean" -- that is a different and much tighter
# question, and one this project currently FAILS on coupled rigs (see below).
#
# The bound is a RATIO against the material present rather than an absolute amount,
# because the two failure modes are separated by nine orders of magnitude and any
# threshold between them would otherwise be a number chosen to make tests pass:
#
#     a round-off dipole                 1.26e-6 mol against 20 mol   ratio 6e-8
#     a coupled rig sweeping its air     0.34 mol against 0.06 mol    ratio 6
#     the unclipped Born term            3.07e9 mol against 1 mol     ratio 3e9
#
# ⚠ **THE MIDDLE ROW IS A REAL, PRE-EXISTING, UNFIXED BUG that this guard is what
# found.** A refluxing rig drives its sealed pot's nitrogen and oxygen blocks
# NEGATIVE without bound -- the vapour edge computes its pressure from a CLAMPED gas
# block, so the derivative cannot see the negativity and nothing pulls it back --
# and after 3000 s the rig's TOTAL nitrogen is -0.34 mol against the 0.06 mol of air
# it started with. That is not a dipole; it is matter destroyed.
# ``project_non_negative`` reports it faithfully on ``created``, and nothing was
# reading that channel. It is written up as the top item of NEXT_SESSION.md.
#
# So this guard REFUSES the third row and REPORTS the second, and the ratio is set
# where a state stops being a perturbation of a physical one rather than where the
# tests are comfortable. ``Rig.conservation_report`` is the channel for the second.
EXCURSION_FLOOR = 1.0e-3     # mol, for species whose total is legitimately zero
EXCURSION_RATIO = 1.0e3      # times the material present

# Whether a liquid layer's POLARITY is held fixed for the duration of one
# integration, evaluated from the state the solver was handed rather than from
# the state it is currently trying.
#
# ⚠ THIS IS A BARGAIN AND IT HAS A PRICE. What it buys is the Jacobian structure
# everything else in this project was tuned for. The ionic rate correction in
# ``_phase_rates`` multiplies every ion-producing rate constant by a function of
# the layer's permittivity, and Oster's rule makes that a function of EVERY
# liquid amount -- so a coupling that was sparse (a reaction touches the species
# it names) became all-to-all (a reaction touches everything dissolved beside
# it). Measured on the prep's acid quench: 2.1x of a 3.2x slowdown, with the
# chemistry unchanged in every row.
#
# What it costs is that the answer now depends on the caller's step size, because
# a layer whose polarity changes DURING a call does not notice until the next one.
# That is the same bargain this project already accepts twice -- the METER edge's
# rate is a parameter an event sets, and the liquid-liquid phase decision is an
# event-boundary test -- and it rests on the same argument: a phase's polarity
# changes on the timescale of the whole operation, not of a proton transfer.
# ``validation/permittivity_freeze.py`` measures both halves of it: the speed
# recovered, and the drift over the longest span this project actually runs.
#
# What it does NOT touch, and this is why it is safe rather than merely cheap:
# the per-species permittivities still follow temperature (only the volume
# WEIGHTS are frozen -- see ``activity.born_ln_gamma``), so a PURE aqueous phase
# still returns a Born term of EXACTLY zero and the anchors keep the value they were
# derived with. ⚠ Be precise about the scope of that: a 0.1 M acetic acid solution is
# not a pure layer, so its permittivity is a shade below water's and its ions carry a
# small non-zero transfer term whether or not the weights are frozen. Freezing
# perturbs that term, not the anchor. Set False to measure what it is worth.
FREEZE_LAYER_PERMITTIVITY = True

WATSON_EXPONENT = 0.38

PHASE_LIQUID = 0
PHASE_GAS = 1


@dataclass
class PhaseArrays:
    """Per-species phase behaviour, as arrays. The Layer 5 -> Layer 4 contract.

    Every field is (n_species,) except the polynomial blocks, which are
    (n_species, 4) for a + bT + cT^2 + dT^3.
    """

    vol_A: np.ndarray        # Antoine A -- log10(P/bar) = A - B/(C+T)
    vol_B: np.ndarray        # Antoine B
    vol_C: np.ndarray        # Antoine C
    condensable: np.ndarray  # bool: True = Raoult (vapour pressure), False = Henry
    Hvap_Tb: np.ndarray      # J/mol, latent heat AT the normal boiling point
    Tb: np.ndarray           # K
    Tc: np.ndarray           # K
    v_liq: np.ndarray        # (n,4) L/mol   liquid molar volume polynomial
    Cp_liq: np.ndarray       # (n,4) J/(mol K) liquid heat capacity polynomial
    Cp_gas: np.ndarray       # (n,4) J/(mol K) ideal-gas heat capacity polynomial

    # solid phase
    Hfus: np.ndarray = None  # J/mol, enthalpy of fusion
    Tm: np.ndarray = None    # K, melting point
    solidifies: np.ndarray = None  # bool: False = never crystallises (gases, ions)
    # bool: this species carries a charge. Used by the liquid-liquid phase
    # decision, which REFUSES to split an electrolyte -- see ``split_phases``.
    ionic: np.ndarray = None
    # bool: this species is a CRYSTAL LATTICE and exists in no other block.
    #
    # ⚠ WHAT MAKES THIS A SPECIES PROPERTY RATHER THAN A PER-REACTION ONE, which
    # is the whole reason a surface reaction needs only one extra mask. A
    # lattice may REACT and may never DISSOLVE, never boil and never melt --
    # ``solidifies`` is held False for it and ``vol_A`` is 1e-30 bar -- so
    # "which block does this species live in" has a single answer for a lattice
    # and only for a lattice. Water is a liquid here and a gas there; calcite is
    # a crystal wherever it appears. That is what lets ``SurfaceArrays`` read a
    # mixed basis off one boolean instead of an (m, n) matrix per reaction.
    lattice: np.ndarray = None

    # Activity-coefficient parameters. Unlike everything above, these are not
    # evaluated properties -- they are the inputs to a model that must run in the
    # loop, because it depends on composition. Left empty, the liquid is ideal
    # and every gamma is 1, which is exactly what this vessel did before.
    nu: np.ndarray = None          # (n, g) group counts per species
    R_k: np.ndarray = None         # (g,) group volume parameters
    Q_k: np.ndarray = None         # (g,) group surface parameters
    a_mn: np.ndarray = None        # (g, g, 3) K, interactions, quadratic in T
    gamma_active: np.ndarray = None  # bool: False = held ideal (ions, unknowns)
    # (n, 4) ln of the reference-state activity coefficient, in the van 't Hoff
    # basis a + b/T + c/T^2 + d/T^3. Zero for a condensable species, whose
    # reference is its own pure liquid; non-zero for a Henry's-law solute, whose
    # reference is infinite dilution in the solvent its Henry constant was
    # measured in. See ``activity.py``.
    gamma_ref: np.ndarray = None
    # (2,) the temperature window that fit was made over. Evaluating outside it
    # is extrapolating a correlation past its data, which for PSRK's quadratic
    # gas parameters goes wrong quickly, so T is clamped to this range for this
    # term only -- a solvent is not liquid out there anyway.
    gamma_ref_range: np.ndarray = None

    # ---- the BORN block: what it costs an ion to leave the water ----------
    # An ion has no UNIFAC decomposition, so ``gamma_active`` is False for it and
    # everything above skips it -- which used to mean gamma = 1, i.e. an ion
    # partitioning to equal MOLE FRACTION between water and toluene. What it has
    # instead is the electrostatic transfer energy, referenced to water:
    #
    #     ln gamma_i = born_A_i / (R T) * (1/eps_layer - 1/eps_water(T))
    #
    # ``born_A`` is (n,) J/mol and is ZERO for every neutral species, so it is
    # also the ion mask and no extra flag is needed. The permittivities are
    # per-species cubics with per-species validity windows, because that is the
    # form CRC publishes and a cubic extrapolated past its data goes negative.
    # See ``properties/dielectric.py``; the mixing rule is Oster's and lives in
    # ``activity.born_ln_gamma`` because it needs the composition.
    born_A: np.ndarray = None        # (n,) J/mol
    eps_coeffs: np.ndarray = None    # (n,4) eps(T) = a + bT + cT^2 + dT^3
    eps_range: np.ndarray = None     # (n,2) K, per-species validity window
    eps_ref_coeffs: np.ndarray = None  # (4,) the reference solvent's own curve
    eps_ref_range: np.ndarray = None   # (2,)

    def __post_init__(self) -> None:
        n = self.vol_A.shape[0]
        if self.Hfus is None:
            self.Hfus = np.zeros(n)
        if self.Tm is None:
            self.Tm = np.zeros(n)
        if self.solidifies is None:
            self.solidifies = np.zeros(n, dtype=bool)
        if self.ionic is None:
            self.ionic = np.zeros(n, dtype=bool)
        if self.lattice is None:
            self.lattice = np.zeros(n, dtype=bool)
        if self.nu is None:
            self.nu = np.zeros((n, 0))
        g = self.nu.shape[1]
        if self.R_k is None:
            self.R_k = np.zeros(g)
        if self.Q_k is None:
            self.Q_k = np.zeros(g)
        if self.a_mn is None:
            self.a_mn = np.zeros((g, g, 3))
        if self.gamma_active is None:
            self.gamma_active = np.zeros(n, dtype=bool)
        if self.gamma_ref is None:
            self.gamma_ref = np.zeros((n, 4))
        if self.gamma_ref_range is None:
            self.gamma_ref_range = np.array([T_MIN, T_MAX])
        if self.born_A is None:
            self.born_A = np.zeros(n)
        if self.eps_coeffs is None:
            self.eps_coeffs = np.zeros((n, 4))
        if self.eps_range is None:
            self.eps_range = np.zeros((n, 2))
        if self.eps_ref_coeffs is None:
            self.eps_ref_coeffs = np.zeros(4)
        if self.eps_ref_range is None:
            self.eps_ref_range = np.zeros(2)

    @property
    def has_ions(self) -> bool:
        """Does anything here carry a Born transfer term?

        Derived from ``born_A`` rather than cached beside it, for two reasons. It
        keeps every ATTRIBUTE of this dataclass a numpy array, which is the Layer
        5 -> Layer 4 contract and is asserted by
        ``test_vessel.test_phase_arrays_carry_no_chemistry``. And it cannot go
        stale: zeroing ``born_A`` to measure what the Born term is worth -- which
        is exactly what the diagnostics do -- would otherwise leave a cached flag
        claiming ions that are no longer priced.
        """
        return bool(np.any(self.born_A > 0.0))

    def reference_correction(self, T: float) -> np.ndarray:
        """ln gamma at the reference state, at T clamped to the fitted window."""
        lo, hi = self.gamma_ref_range
        return _poly_inv(self.gamma_ref, min(max(T, lo), hi))

    def permittivity(self, T: float) -> np.ndarray:
        """Pure-component relative permittivity at T, (n,), 0 where unknown.

        Each species is clamped to ITS OWN published window: the tables are cubics
        fitted over as little as a hundred kelvin (toluene's is quoted 207-316 K)
        and a cubic extrapolated far past its data can go negative, which would
        flip the sign of an ion's transfer energy. A species with no entry has
        all-zero coefficients AND a zero window, so it comes out at exactly 0 --
        the "no data" sentinel the mixing rule masks on, since no real
        permittivity is below 1.
        """
        t = np.clip(T, self.eps_range[:, 0], self.eps_range[:, 1])
        c = self.eps_coeffs
        return c[:, 0] + t * (c[:, 1] + t * (c[:, 2] + t * c[:, 3]))

    def born_block(self, T: float) -> np.ndarray | None:
        """The (n, 4) ion-transfer block at T: ``[A | eps | v_mol | eps_ref]``.

        ⚠ THE ANSWER TO THIS PROJECT'S STANDARD QUESTION. A Born term depends on
        the LAYER's permittivity and therefore on composition, so unlike Antoine
        or Rackett it cannot collapse to setup-time coefficients outright. What it
        does collapse to is this: a block that is a function of TEMPERATURE ALONE,
        assembled once per RHS call and shared by both liquid layers and by every
        tangent-plane trial. Only the mixing rule is left in the hot loop, and
        that is three array operations.

        ``None`` when the network has no ions at all, which is what keeps a
        non-electrolyte vessel bit-identical to one built before any of this
        existed.

        Each permittivity is clamped to ITS OWN published window: the tables are
        cubics fitted over as little as a hundred kelvin (toluene's is quoted
        207-316 K) and a cubic extrapolated far past its data can go negative,
        which would flip the sign of an ion's transfer energy.
        """
        if not self.has_ions:
            return None
        eps = self.permittivity(T)
        lo, hi = self.eps_ref_range
        tr = min(max(T, lo), hi)
        r = self.eps_ref_coeffs
        # ⚠ THE REFERENCE GOES THROUGH THE MIXING RULE TOO, and it has to. The
        # claim this whole term rests on is that an ion's activity coefficient in
        # water is EXACTLY one, so that every water-anchored pKa in this project
        # keeps the value it was derived with. A reference taken straight off the
        # polynomial and a mixture value taken through Oster's inversion differ in
        # their last few bits, which is nothing as a permittivity and is not
        # nothing as "exactly". Putting both through the same round trip makes the
        # cancellation bit-exact rather than merely close.
        eps_ref = oster_permittivity(
            np.ones(1), np.array([r[0] + tr * (r[1] + tr * (r[2] + tr * r[3]))])
        )
        return np.column_stack([
            self.born_A,
            eps,
            np.maximum(_poly(self.v_liq, T), 0.0),
            np.full(self.born_A.shape[0], eps_ref),
        ])


# mol/L -- NOT A SCALE. The floor under a concentration before it is logged, so
# that an ion which is exactly absent gives ln c = -69 rather than -inf. Same
# discipline as MOLE_FRACTION_DENOM and for the same measured reason: *a clamp
# that exists to avoid a singularity must not double as a gate.* 1e-30 M is 21
# decades below the solver's atol and far below the smallest Ksp root in the
# table (sphalerite's, 5.5e-13 M), so nothing an integration can reach puts it
# in contention -- and because the reaction quotient it feeds is compared
# against Ksp, a floored ion makes Q collapse and the term reads DISSOLVING,
# which is the physically correct answer for an ion that is not there.
CONC_FLOOR = 1.0e-30

# The largest ln(Q/Ksp) the driving force is evaluated at before the exponential
# is capped. Not a gate either: 1e3 in the root of the saturation ratio is a
# driving force no chemistry reaches, and the cap exists so that a transient
# absurd state during a Jacobian perturbation cannot produce an inf.
#
# ⚠⚠⚠ AND C2 MEASURED THAT IT DID NOT ACHIEVE THAT, WHICH IS THE WHOLE POINT OF
# WRITING AN INTENT DOWN. The cap bounds a CONCENTRATION; the RHS returns a
# MOLAR FLOW, and the line that turns one into the other multiplies by the
# liquid volume -- which a Newton iterate does not bound. Measured, in a flask
# of phosphate rock and sulfuric acid: the BDF iteration proposed T = 1.0 K
# (the RHS's own ``T_MIN`` clamp, not a state the chemistry reached) with
# 5.0e10 mol in the liquid, so ``V_L1`` came to 9.2e8 L, every lattice's
# ``ln_Ksp/total_nu`` ran past the cap, and ``1e-2 * 9.2e8 * exp(700)``
# overflowed to ``inf`` -- and then to ``nan`` one line later, in the ``_avail``
# product. **exp() being finite is not the same claim as k*V*exp() being
# finite**, and the cap was written as though it were.
#
# ⚠⚠ THE HEADROOM IN THE RHS IS THEREFORE PART OF THIS CAP AND NOT A SECOND
# CLAMP. ``head`` subtracts the scale the result is about to be multiplied by,
# so the quantity actually bounded by ``LN_SATURATION_CAP`` is the DRIVE. It is
# BIT-IDENTICAL wherever ``k_diss * V_L1 <= 1`` -- which is every vessel in this
# repo, ``k_diss`` defaulting to 1e-2 and no flask here holding more than a few
# litres -- and elsewhere it binds only in states that were already past the
# cap. ⚠ It is still a CAP and not a fix for the Ksp: ``ln_Ksp(1 K)`` is a
# van 't Hoff extrapolation 297 K outside anything it means, and no bound makes
# that number mean something. What the cap buys is that the meaningless number
# stays FINITE, so BDF rejects the step on its merits rather than on a ``nan``.
#
# ⚠ AND THIS IS ENGINE QUEUE ITEM 6's OPEN QUESTION, ANSWERED FROM A DIFFERENT
# TERM. That row records a PSRK overflow below 4.28 K and says "nothing has
# found WHICH call passes a T that low". Nothing does: ``T_MIN`` manufactures
# it. A Newton iterate proposes a temperature below 1 K, the RHS's
# ``min(max(float(y[-1]), T_MIN), T_MAX)`` hands every term exactly 1.0, and
# each 1/T in the right-hand side is evaluated 297 K outside its domain at once.
LN_SATURATION_CAP = 700.0


@dataclass
class PrecipitationArrays:
    """Ionic lattices that can leave solution, as arrays. Layer 5 -> Layer 4.

    ## WHY THIS IS A TERM AND NOT A REACTION

    ⚠ **The kinetics kernel cannot express it.** A ``ReactionTemplate``'s phase is
    liquid or gas, ``KineticArrays`` writes only into those two blocks, and no
    reaction anywhere in this project writes the SOLID block. Precipitation is
    liquid -> solid, so it is a transport term next to evaporation and
    dissolution, not a reaction next to esterification. That was settled by
    measurement before any of this was written -- see
    ``properties/solubility_product.py``.

    ## HOW A LATTICE IS REPRESENTED, AND THE ONE LIMIT THAT CREATES

    **The solid block holds the IONS, not the lattice.** AgCl(s) is one mole of
    ``[Ag+]`` and one mole of ``[Cl-]`` sitting in the solid block. That choice
    buys three things for free: conservation is exact by construction (the same
    species vector, matter only moves between blocks), no new species enters the
    network, and the existing dissolution law never touches them because
    ``solidifies`` is False for every ion.

    ⚠ **AND IT MEANS THE SOLID BLOCK IS AN ION INVENTORY RATHER THAN A SET OF
    DISTINCT CRYSTALS.** Where two candidate lattices share an ion -- rock salt
    and chlorargyrite both claim ``[Cl-]`` -- solid chloride cannot be attributed
    between them. ``units`` below is the honest bound that follows: a lattice can
    only dissolve while EVERY one of its ions is present in the solid, so a
    lattice that never precipitated can never dissolve. What is not bounded is
    how much two coexisting solid lattices sharing an ion may each claim. This is
    reported as a LATENT fragility rather than refused, because reaching it needs
    two sparingly-soluble lattices with a common ion both crystalline at once,
    and the non-negative projection catches the overshoot if it ever happens.

    ## THE FORM, AND WHY THE ROOT IS TAKEN

    ``Q = prod c_i^nu_i`` spans decades faster than a concentration does -- for a
    2:1 salt it goes as c^3 -- so the driving force is written on the ROOT:

        Qroot = Q^(1/N),  Ksproot = Ksp^(1/N),   N = sum nu_i
        drive = k_diss * V_liquid * (Qroot - Ksproot)          mol/s, + = out

    Both roots are concentrations in mol/L, so ``drive`` is the same shape as the
    dissolution term one block up -- a rate constant times a volume times a
    concentration difference -- and it relaxes toward saturation on 1/k_diss.
    ⚠ ``k_diss`` is REUSED rather than a new constant being invented: crystal
    growth from a supersaturated solution and dissolution of a crop are the same
    interfacial process, the vessel already declares that knob, and a second one
    would need a bound this project has no data to give it.

    ## THE GATE, AND WHAT IS IN ITS DEAD ZONE

    Asked before it was written, which is HANDOFF 72's rule. Precipitation is
    UNGATED, matching the molecular-solid branch's stated design ("anything can
    nucleate"); dissolution is gated on the lattice being present by exactly the
    ``_avail`` used one block up, driving-force-scaled. So the pair is the
    SOLID_GATE_TIME arrangement and not the disjoint ``_layer_gates`` one, and
    there is no dead zone: with no solid and an undersaturated solution the flux
    is zero because there is nothing to dissolve, which is exact rather than
    gated.

    ⚠ **NO NUCLEATION BARRIER, AND THAT IS A REFUSAL RATHER THAN AN OVERSIGHT.**
    M3 offered to bundle a metastable zone so that seeding becomes a mechanic.
    The code for it is three lines -- hold the flux at zero until the saturation
    ratio passes some S_crit -- but S_crit is a measured, substance-specific
    width and this project has no source for one. Inventing it would be the
    hand-tuned constant the sulfur burner's A exists as the counter-example to.
    """

    # (m, n) -- ions per formula unit of each lattice, over the species vector.
    nu: np.ndarray
    total_nu: np.ndarray      # (m,) sum over species; the root exponent
    ln_Ksp_ref: np.ndarray    # (m,) at T_REF_KSP
    dH_diss: np.ndarray       # (m,) J/mol, lattice -> dissolved ions
    dS_diss: np.ndarray       # (m,) J/(mol K), from the 298 K pair, dCp = 0
    names: tuple = ()         # (m,) mineral names, for reporting only

    @property
    def m(self) -> int:
        return int(self.nu.shape[0])

    def ln_Ksp(self, T: float) -> np.ndarray:
        """van't Hoff from the 298 K pair. ``dCp = 0``, stated not hidden."""
        return -(self.dH_diss - T * self.dS_diss) / (R * T)


@dataclass
class SolidStateArrays:
    """A reaction that happens INSIDE a crystal, as arrays. Layer 5 -> Layer 4.

    M6. ``CaCO3(s) -> CaO(s) + CO2(g)``: matter changes identity while staying a
    solid, and the gas it evolves leaves through the headspace.

    ## WHY THIS IS A TERM AND NOT A THIRD ``PHASE_INDEX`` ENTRY

    ⚠ **The kinetics kernel cannot express it, and that was measured rather than
    assumed.** A pure solid has UNIT ACTIVITY, so a pair of crystals fixes the
    gas pressure above them at ``K(T)`` regardless of how much of each is there.
    Mass action on the solid amounts gives instead

        k_f n(CaCO3) = k_r n(CaO) p        ->      p_eq = (k_f/k_r) n_A / n_B

    which sweeps from infinity to zero as a charge converts. Real calcite either
    goes to completion (``p < K``) or does not start (``p > K``); the mass-action
    form always stops partway, so it is a different shape of answer and not a
    loose one. Dropping the reverse instead deletes the kiln mechanic outright:
    a sealed 1 L flask holding 0.1 mol of calcite equilibrates at **7.95%**
    conversion at 1100 K and at 0.12% at 900 K, where forward-only reads 100% at
    both. ``properties/solid_state.py`` carries that table.

    So ``PHASE_INDEX`` keeps its two entries and this sits beside
    ``PrecipitationArrays``, for the same reason and by the same precedent.

    ## THE FORM

        Q     = prod over gas participants of p_i^nu_i          bar^(sum nu)
        flux  = k_f(T) * units_fwd  -  k_r(T) * Q * units_rev   mol/s

    with ``units_fwd``/``units_rev`` the formula units of the reactant and
    product SOLID sides the block can supply -- the same ``units`` bound
    ``PrecipitationArrays`` uses, and the same limit: the solid block is an
    inventory, so two solid-state reactions sharing a mineral cannot attribute it
    between them.

    ⚠ **THERE IS NO ``_avail`` GATE HERE, AND ITS ABSENCE IS THE POINT.**
    Dissolution needed one because its driving force (undersaturation) is
    non-zero at an EMPTY block, so something had to stop a phantom crop
    dissolving -- and a constant-scale knee there put 4e7 on the Jacobian
    diagonal of blocks holding nothing. This term's driving force IS the amount
    present: it is exactly zero and its slope is ``k_f`` at an empty block, which
    is bounded by ``A`` (1e5 1/s in the limit, ~1e-3 at a kiln's 1200 K, 1.3e3 at
    the ``T_MAX`` clamp). Nothing to regularise, so nothing is regularised.

    ## ⚠ THE TWO RATE CONSTANTS ARE COMBINED ANALYTICALLY, NOT DIVIDED

    ``k_r`` is not ``k_f / K``. Written that way it is a ratio of two exponentials
    that are each enormous and nearly cancel -- at 300 K, ``exp(-Ea/RT)`` is
    1e-32 and ``exp(-lnK)`` is 1e+21, and their product is a perfectly ordinary
    4e-4. So the cancellation is done at SETUP, in closed form:

        k_r(T) = A exp(-dS/R) * exp(-(Ea - dH)/RT)

    and ``Ea - dH`` is exactly ZERO for an endothermic decomposition, because
    ``Ea`` is derived as ``max(dH, 0)`` -- see ``solid_state.py``. **The reverse
    of a calcination is barrierless and its rate constant is a temperature-
    independent 4.26e-4 1/(bar s).** No clip, no floor, and no exponential in
    this term can overflow.

    ## ⚠⚠ S9 -- A GAS REACTANT IS ALLOWED NOW, AND THE OLD REFUSAL IS WORTH READING

    This section used to say ``nu_gas`` is required positive, because a gas
    REACTANT puts its pressure in the DENOMINATOR of ``Q``, so an atmosphere with
    none of it left drives ``Q`` to infinity and the reverse flux with it --
    measured on a roasting declaration at 2.6e15 formula units per second as
    ``p_O2 -> 0``. **All of that is true of a QUOTIENT and none of it is true of
    the same expression written as its two one-sided halves:**

        net = k_f * prod(p ** gas_consumed)  -  k_r * prod(p ** gas_formed)

    which is ``P_react (k_f - k_r Q)`` algebraically -- the SAME root, hence the
    same equilibrium -- and which never divides anything at all. At
    ``p_react = 0`` it is the finite ``-k_r P_prod``. See ``__post_init__``.

    ⚠ **THE SECOND REASON THAT USED TO BE GIVEN WAS ABOUT A FORM THIS TERM NEVER
    USED.** It cited M6's ``p/K = n_A/n_B``, which is mass action on a solid
    AMOUNT -- and the block below already takes ONE ``units`` for both directions,
    chosen by the sign, so it is a common factor that divides out of ``net = 0``.
    That was already the case when the refusal was written. **Read a refusal as
    two separate claims: the number, and what the number is about.**

    ⚠ **AND ROASTING IS STILL A DIFFERENT MECHANISM, FOR THE REASON THAT
    SURVIVES: THE RATE ORDER.** An affinity form's exponents are fixed at the
    stoichiometric coefficients by detailed balance, or the equilibrium is wrong.
    ``3 O2`` taken third order stalls asymptotically as the atmosphere is
    consumed, which is exactly what ``SurfaceReaction.orders`` exists to declare
    away -- and this project's standing invariant is that **a declared rate order
    may never be reversible.** So a gas-consuming surface reaction whose reverse
    is unobservable (``ln K`` +67.6 to +78.8) still wants the mass-action kernel;
    one whose reverse is a real flux (``ln K`` +10.90 for a copper smelt) wants
    this one.

    ⚠ **IT WAS BUILT -- ``SurfaceArrays``, below -- AND IT TURNED OUT TO WANT A
    TERM OF ITS OWN RATHER THAN THE THIRD ``PHASE_INDEX`` ENTRY THIS DOCSTRING
    PREDICTED.** A roasting row's reactant is a lattice, which
    ``thermochemistry`` refuses by name, so it cannot be priced on the ideal-gas
    basis the kernel's reverse derivation lives on; and a solid CATALYST is a
    factor in a gas reaction's rate law, whose phase label carries a standard
    state worth 2.6e10 in K. Refusing here is still what keeps the two apart.
    """

    # (m, n) signed stoichiometry over the species vector. Solids live in the
    # SOLID block, gases in the GAS block; the split is why these are two arrays
    # and not one -- a single delta could not say which block to write.
    nu_solid: np.ndarray
    nu_gas: np.ndarray
    dH: np.ndarray            # (m,) J/mol at 298.15 K, + = endothermic
    dS: np.ndarray            # (m,) J/(mol K) at 298.15 K, dCp = 0
    A_fwd: np.ndarray         # (m,) 1/s
    Ea_fwd: np.ndarray        # (m,) J/mol -- DERIVED as max(dH, 0)
    names: tuple = ()

    def __post_init__(self) -> None:
        # The reverse pair, in closed form. See the docstring: this is the whole
        # reason nothing in the hot loop divides one exponential by another.
        self.A_rev = self.A_fwd * np.exp(-self.dS / R)
        self.Ea_rev = np.maximum(self.Ea_fwd - self.dH, 0.0)
        # Which species each side needs, as positive counts. Precomputed so the
        # RHS does two maxima fewer per call.
        self.consumed = np.maximum(-self.nu_solid, 0.0)
        self.formed = np.maximum(self.nu_solid, 0.0)
        # ⚠ S4 -- WHETHER EACH SIDE HAS ANY SOLID AT ALL. Every row until S4 had
        # a crystal on both sides, so ``units`` never met an empty one; see
        # ``units`` for what the empty minimum used to return and why the fix is
        # not a clip.
        self.has_consumed = (self.consumed > 0.0).any(axis=1)
        self.has_formed = (self.formed > 0.0).any(axis=1)
        # ⚠⚠ S9 -- THE TWO HALVES OF THE GAS SIDE, WHICH IS THE WHOLE OF THE
        # REVERSIBLE SOLID-GAS TERM. ``Q`` used to be taken as one product,
        # ``prod(p ** nu_gas)``, and a gas REACTANT was refused where these
        # arrays are built because its NEGATIVE exponent puts its pressure in
        # the DENOMINATOR: an atmosphere with none of it left drives the reverse
        # flux without bound (measured at 2.6e15 formula units per second on a
        # roasting declaration). Split into the two one-sided products
        #
        #     P_react = prod(p ** consumed_gas)      P_prod = prod(p ** formed_gas)
        #
        # nothing is ever divided, so nothing can blow up:
        #
        #     net = k_f P_react - k_r P_prod
        #
        # which is ALGEBRAICALLY ``P_react * (k_f - k_r Q)`` and therefore the
        # same equilibrium -- ``net = 0`` is still ``Q = K`` exactly -- while
        # ``p_react -> 0`` now gives the finite ``-k_r P_prod`` instead of an
        # infinity. **That is the entire engine gap S8 named**; see
        # ``properties/solid_state.py``'s docstring for why M6 drew the line in
        # the wrong place.
        #
        # ⚠ AND THE FIVE PRE-S9 ROWS ARE BIT-IDENTICAL, not merely close. Every
        # one of them has ``nu_gas >= 0``, so ``formed_gas`` IS ``nu_gas``
        # element for element and ``consumed_gas`` is all zeros -- and
        # ``p ** 0`` is exactly 1.0 for every finite p, including 0.0. A test
        # pins it.
        self.gas_consumed = np.maximum(-self.nu_gas, 0.0)
        self.gas_formed = np.maximum(self.nu_gas, 0.0)

    @property
    def m(self) -> int:
        return int(self.nu_solid.shape[0])

    def units(self, n_solid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(forward, reverse) formula units this solid block can supply, (m,).

        ⚠⚠ **A SIDE WITH NO SOLID ON IT FALLS BACK TO THE OTHER SIDE, AND THAT
        IS A NUCLEATION STATEMENT RATHER THAN A CLIP.** S4 added the first row
        here that turns a crystal ENTIRELY into gas -- ``2 HgO(s) -> 2 Hg(g) +
        O2(g)``, mercury being a gas at the 900 K its own retort runs at -- so
        the product side has no solid to take a minimum over. The minimum of an
        empty set is ``+inf``, and the RHS multiplies it by a negative affinity:
        measured, a sealed 1 L retort holding 0.5 mol of montroydite at 900 K
        raised ``array must not contain infs or NaNs`` the moment ``Q`` crossed
        ``K``, which it does at that charge because ``ln K`` is only +9.2 there.

        **Infinity is not a bound that needs softening; it is the wrong bound.**
        What ``units`` measures on the reverse side is the crystal the reaction
        has to run ON, and reading the existing rows that way they already say
        so: calcination's reverse is bounded by ``n(CaO)`` -- the SEED the
        carbonate grows on -- not by the CO2 pressure, which is in ``Q``. This
        engine cannot nucleate a solid out of nothing (S3 named that gap: a
        surface term is extensive in the solid, so zero solid is zero rate for
        ever). So for a row whose products are all gas, the seed the deposition
        lands on is the REACTANT crystal, and the reverse gets that bound.

        Two consequences, both wanted:

          * ``units`` stays a COMMON FACTOR of the two directions for such a
            row -- it is the same number either way -- so the equilibrium is
            still ``Q = K`` and not ``Q = K n_A/n_B``, which is the whole
            property this term exists to have;
          * and an EXHAUSTED charge stops the reaction in both directions. Once
            the last of the oxide is gone, mercury vapour and oxygen in the
            flask cannot make it again. That is the nucleation gap stated
            rather than worked around, and it is honest here: HgO really does
            need a surface.

        ⚠ The four rows that existed before S4 all carry a crystal on each side,
        so both fallbacks are inert for them -- bit for bit, which a test pins.
        """
        fwd = np.where(self.consumed > 0.0,
                       n_solid[None, :] / np.maximum(self.consumed, 1.0),
                       np.inf).min(axis=1)
        rev = np.where(self.formed > 0.0,
                       n_solid[None, :] / np.maximum(self.formed, 1.0),
                       np.inf).min(axis=1)
        return (np.where(self.has_consumed, fwd, rev),
                np.where(self.has_formed, rev, fwd))

    @property
    def total_nu_gas(self) -> np.ndarray:
        """(m,) how many moles of gas each row evolves. The exponent on K."""
        return self.nu_gas.sum(axis=1)

    def equilibrium_pressure(self, T: float) -> np.ndarray:
        """``K(T)``, (m,), in bar^(sum nu_gas). For reporting, not the RHS."""
        return np.exp(-(self.dH - T * self.dS) / (R * T))

    def threshold_temperature(
        self, P_ambient: float, lo: float = 200.0, hi: float = 3000.0
    ) -> np.ndarray:
        """(m,) K -- the temperature each row needs to run against the room.

        ⚠ THIS IS NOT ``K(T) = P_ambient``, AND FOR A ONE-GAS ROW IT REDUCES TO
        IT. A row evolving ``n`` moles of gas has ``K`` in units of ``bar^n``, so
        comparing it against a pressure is a units error the moment ``n > 1``.
        What the comparison has to be is the reaction QUOTIENT against ``K``, and
        the honest reference state for "in the open" is the one where the evolved
        gases are the whole atmosphere and share the ambient total:

            each gas at P/n   ->   Q = (P_ambient / n)^n   ->   solve K(T) = Q

        For ``n = 1`` that is exactly ``K = P_ambient``, so every lime number
        this project has measured is unmoved. For the two-gas rows it matters a
        lot: green vitriol's ``K`` reaches 1 bar^2 at 918 K and its threshold is
        874 K, because two gases sharing one bar is 0.25 bar^2 and not 1.

        ⚠ It is a REFERENCE STATE and not a prediction of what a real retort
        does. A retort full of air dilutes the products further (so it decomposes
        cooler) and a sealed one concentrates them (so it stalls). Both of those
        the RHS integrates; this is the one-number summary that goes in a report.
        """
        n = np.maximum(self.total_nu_gas, 1.0)
        target = (P_ambient / n) ** n
        a = np.full(self.m, lo)
        b = np.full(self.m, hi)
        for _ in range(80):
            mid = 0.5 * (a + b)
            below = self.equilibrium_pressure(mid) < target
            a = np.where(below, mid, a)
            b = np.where(below, b, mid)
        return 0.5 * (a + b)


@dataclass
class SurfaceArrays:
    """A crystal reacting with a gas that ARRIVES at it, as arrays. Layer 5 -> 4.

    ``2 ZnS(s) + 3 O2(g) -> 2 ZnO(s) + 2 SO2(g)`` is a roaster. This is the other
    half of M6's dichotomy and it is a different mechanism from
    ``SolidStateArrays``, not a variant of it -- see ``properties/surface.py``
    for the argument, which is measured in both directions.

    ## THE FORM, AND THE ONE THING IT MUST NOT GET WRONG

        rate = k(T) * prod(nS ** order_solid) * prod(C_gas ** order_gas)   mol/s
        k(T) = A exp(-Ea / R T)

    ⚠ **THE BASIS IS MIXED, SO THIS RATE IS NOT MULTIPLIED BY A VOLUME.** Every
    other rate law in this project comes out in mol/(L s) and is scaled by the
    phase's volume; this one is already in mol/s. Both halves are forced:

      * a solid's CONCENTRATION has no referent -- the solid block is an
        inventory in mol and ``V_S`` is nominal, because solids are given the
        liquid molar volume. ``nS/V`` divides a number by a convention;
      * a gas's AMOUNT is not what a surface sees -- the arrival rate at a
        crystal face goes with the collision rate, i.e. with concentration.
        Written on ``nG`` the reaction would not speed up under compression, and
        a roaster is a machine for blowing air through a bed.

    So the rate is EXTENSIVE in the solid and INTENSIVE in the gas, and one
    consequence is a mechanic: with order 1 in the solid, ``tau = 1/(k C_gas)``
    does not depend on the charge. A bigger bed is more throughput, not a longer
    roast.

    ## ⚠ ONE BOOLEAN SPLITS THE BASIS AND THE DESTINATION BOTH

    ``PhaseArrays.lattice`` says which species are crystals, and a lattice is
    the only species in this engine whose block is unambiguous -- it may react
    and may never dissolve, boil or melt. So the same mask that chooses each
    species' basis also chooses which block its stoichiometry lands in, and no
    per-reaction matrix is needed. Water is liquid here and vapour there; calcite
    is a crystal wherever it appears.

    ## ⚠⚠ FORWARD ONLY, AND THAT IS TWO MEASUREMENTS RATHER THAN A SIMPLIFICATION

      * **Mass action on a solid AMOUNT reaches the wrong equilibrium** -- M6's
        measurement, not re-derived here: a reversible pair written this way
        settles at ``p/K = n_A/n_B``, observed at 3.0863 against 3.0863 at
        1100 K. Any reversible row with a non-zero solid stoichiometry inherits
        that exactly, which is why ``properties/surface.price`` refuses one.
      * **And for the rows that exist the reverse is unobservable anyway.**
        ``ln K`` is +67.6 to +78.8 at each row's own run temperature;
        ``LN_K_IRREVERSIBLE`` requires +20 and the tightest row clears it by
        20.7 decades.

    ## ⚠ NOTHING IS GATED HERE, AND THAT IS THE SAME ARGUMENT M6 MADE

    ``_avail`` exists because dissolution's driving force is non-zero at an EMPTY
    block, so a phantom crop would dissolve. This term's driving force IS the
    amount present: at ``nS = 0`` the rate is exactly zero and its slope is
    ``k C_gas``, bounded by ``A`` (3.21e6 L/(mol s) in the limit, 0.24 at a
    roaster's 1100 K). The same holds for the arriving gas -- order 1, no
    denominator, so ``C_gas = 0`` is a zero with a bounded slope. Nothing to
    regularise.

    ⚠ **AND A CATALYST CANNOT SEED ITSELF, WHICH IS WHY THAT EXPOSURE IS ABSENT
    RATHER THAN GUARDED.** ``chemsim-solid-gate-fix`` records a round-off-seeded
    lead chamber reaching 89% yield on 1.2e-4 mol of phantom NOx, and the shape of
    that failure is a CYCLE with unbounded gain on its own catalyst. Here a
    catalyst's stoichiometry is identically zero -- it is in ``order_solid`` and
    absent from both ``nu`` arrays -- so its amount is a constant of the motion
    and a phantom mole stays a phantom mole. A consumed solid is bounded by matter
    the ordinary way: a spurious 1e-20 mol of sphalerite makes 1e-20 mol of
    zincite and stops.

    ⚠ **THE ``units`` BOUND THAT ``SolidStateArrays`` AND ``PrecipitationArrays``
    BOTH CARRY IS NOT HERE, AND IT IS NOT NEEDED.** Those two write a flux that
    can be large at a nearly-empty block, so they cap it by the formula units the
    block can supply. This rate is PROPORTIONAL to the amount present, so it
    self-limits: the solid decays exponentially and cannot cross zero, which the
    non-negative projection then never has to repair. The limit that remains is
    the shared one -- the solid block is an inventory, so two surface reactions
    consuming the same mineral cannot attribute it between them.
    """

    # (m, n) signed stoichiometry, split by ``PhaseArrays.lattice`` at use.
    # Kept as ONE array rather than the two ``SolidStateArrays`` needs, because
    # there the split is per-reaction and here it is per-species.
    nu: np.ndarray
    # (m, n) rate-law exponents. Two arrays and not one, because they are on
    # different bases -- ``order_solid`` on mol, ``order_gas`` on mol/L -- and a
    # single matrix could not say which. Both are DECLARED: the written
    # stoichiometry is a global one (three O2 do not meet one crystal), so taking
    # the coefficients for the rate law would make the conversion a reading of
    # ``A``. Same declaration ``library.sulfur_combustion`` makes.
    order_solid: np.ndarray
    order_gas: np.ndarray
    dH: np.ndarray            # (m,) J/mol at 298.15 K, + = endothermic
    A: np.ndarray             # (m,) L^g mol^(1-g-s) / s -- the mixed basis
    Ea: np.ndarray            # (m,) J/mol -- DECLARED, not derived; see below
    names: tuple = ()

    def __post_init__(self) -> None:
        # ⚠ THE TWO EXPONENT MATRICES COLLAPSE TO ONE, AND THAT IS THE ANSWER TO
        # "what uniform array form does this model reduce to?" -- the question
        # this project asks before adding any physical model. Since the BASIS is
        # chosen per species by ``PhaseArrays.lattice``, and a species appears in
        # exactly one of the two matrices, their sum indexes the mixed vector
        # correctly and the hot loop takes one product instead of two.
        #
        # They are kept as separate fields anyway, because the split is the
        # DECLARATION: it is what lets ``build_surface_arrays`` refuse a row that
        # puts a solid's exponent on a concentration, which is an error no
        # measurement downstream could distinguish from a wrong rate constant.
        self.order = self.order_solid + self.order_gas
        # How many moles of gas the rate law is order-``g`` in, and how many of
        # solid. Reported so that ``A``'s units can be written down beside its
        # value -- L^g mol^(1-g-s)/s -- rather than inferred.
        self.n_gas_order = self.order_gas.sum(axis=1)
        self.n_solid_order = self.order_solid.sum(axis=1)

    @property
    def m(self) -> int:
        return int(self.nu.shape[0])

    def rate_constants(self, T: float) -> np.ndarray:
        """(m,) ``k(T)``. Reported and used; no exponential here can overflow.

        ``Ea`` is positive and declared, so the exponent is negative and bounded
        by 1 -- unlike ``SolidStateArrays``, where the barrier is DERIVED as
        ``max(dH, 0)`` and the closed-form reverse exists to stop two enormous
        exponentials being divided. There is no reverse here to cancel against,
        which is also why the barrier could not be derived: ``max(dH, 0)`` is
        ZERO for a reaction this exothermic, i.e. a roast that goes as fast as
        oxygen can arrive, and that is not what a roaster is.
        """
        return self.A * np.exp(-self.Ea / (R * T))


@dataclass
class VesselConditions:
    """Scalar operating conditions and boundary fluxes."""

    volume: float                 # L, total internal volume of the vessel
    T_env: float = 298.15         # K, surroundings
    UA: float = 1.0               # W/K, overall heat-transfer coefficient
    Q_input: float = 0.0          # W, external heating (a hotplate)
    P_ambient: float = 1.01325    # bar
    kla: float = 1.0              # mol/(bar s), liquid<->vapour mass-transfer
    k_diss: float = 1.0e-2        # 1/s, liquid<->solid dissolution rate
    k_vent: float = 1.0e3         # mol/(bar s), how freely the vessel vents
    # mol/s, liquid<->liquid mass transfer between two layers -- how freely the
    # two liquids exchange across their interface. Nothing forces the phases to
    # be at equilibrium, so a funnel drained before it has equilibrated leaves
    # product behind.
    #
    # ⚠ ONE COEFFICIENT DOES TWO JOBS HERE, and it is worth knowing which.
    # Separating the bulk phases and equilibrating a solute between them are
    # physically different processes -- the first is gravity-driven and fast,
    # the second needs interfacial area and is what shaking is for -- but both
    # are carried by this single flux. So it is NOT a clean "how hard did you
    # shake it" knob: turning it down far enough does not model a badly-shaken
    # funnel, it models two liquids that never separated at all, which is not a
    # state a bench produces. Separating the two would need a settling model
    # (drop size, coalescence) that this project does not have.
    k_lle: float = 5.0
    # Whether a second liquid phase may form at all. False keeps the second
    # block identically zero, which reproduces the one-liquid vessel bit for
    # bit -- and `Vessel` still RUNS the stability test and reports a liquid
    # that wanted to split, rather than silently ignoring it.
    lle: bool = True
    ingress: np.ndarray = None    # (n,) mol/s into the headspace (e.g. air leak)
    # (n,) mole fractions of the room's atmosphere, i.e. what gets drawn back in
    # when the vessel is below ambient pressure. Layer 5 fills this with air; an
    # inert-atmosphere glovebox is the same field with a different composition.
    x_ambient: np.ndarray = None

    # Heat capacity of the vessel ITSELF, J/K -- the glass, not the contents.
    # This is not a numerical fudge: without it a flask boiled dry has literally
    # zero thermal mass, so dT/dt is singular and the integrator is right to give
    # up. Real glassware has tens of J/K (borosilicate is ~0.83 J/(g K), so a
    # 100 g flask is ~83 J/K), which is what makes a dry flask heat fast but
    # finitely. It also sets how sluggishly the vessel responds to the hotplate.
    heat_capacity: float = 50.0


def _poly(coeffs: np.ndarray, T: float) -> np.ndarray:
    """Evaluate (n,4) polynomial coefficients at scalar T -> (n,)."""
    return coeffs[:, 0] + T * (coeffs[:, 1] + T * (coeffs[:, 2] + T * coeffs[:, 3]))


def _poly_inv(coeffs: np.ndarray, T: float) -> np.ndarray:
    """Evaluate (n,4) coefficients of a + b/T + c/T^2 + d/T^3 -> (n,).

    The van 't Hoff basis. Quantities that are ratios of Boltzmann factors are
    near-linear in 1/T, so they need this rather than a polynomial in T; the same
    observation is why Henry constants collapse to Antoine form upstream.
    """
    u = 1.0 / T
    return coeffs[:, 0] + u * (coeffs[:, 1] + u * (coeffs[:, 2] + u * coeffs[:, 3]))


# Below this, a species' total is numerical noise rather than matter: the solver
# was asked for atol=1e-9 per component and a state vector has 3n+1 of them, so a
# total that lands this close to zero from the negative side is round-off, not a
# deficit worth reporting. Scaled by the number of blocks in ``project_non_negative``.
NEGLIGIBLE_TOTAL = 1.0e-9


def project_non_negative(
    blocks: list[np.ndarray],
) -> tuple[list[np.ndarray], np.ndarray]:
    """Make every per-species amount non-negative WITHOUT changing its total.

    ``blocks`` is the list of same-length amount vectors that hold one species set
    between them -- ``[n_liquid, n_gas, n_solid]`` for a vessel, and the same three
    per vessel for a rig. Returns the projected blocks and, per species, the amount
    that had to be created because the total was itself negative.

    **Why this exists, and what it replaces.** The RHS evaluates its fluxes at
    ``max(y, 0)``, which keeps it finite in degenerate states but also makes the
    derivative identically zero once a component drifts below zero -- so a solver
    excursion into the negative is never pulled back, it just sits there. Every
    flux in the RHS is antisymmetric between the phases it connects, so the
    trajectory still conserves each species exactly: measured over a 600 s
    two-vessel run, ethanol is conserved to 4e-15 and water to 2e-21.

    What did NOT conserve anything was the ``np.maximum(y, 0.0)`` that used to be
    applied to the final state. In that same run water finished with its solid
    block at -1.26e-6 mol and its liquid block at +1.02e-6 -- a cancelling pair
    that sums to nothing. Clamping the negative half alone destroyed the
    cancellation and CREATED 1.26e-6 mol of water out of a vessel that never held
    any. That is a fifteen-order-of-magnitude asymmetry between the species
    carrying real material and the ones sitting at zero, and it grew with run
    length.

    So the negative entry is not a deficit to be filled in, it is one half of a
    numerical dipole. Zero it and take the same amount back out of the phases
    holding the other half, largest first -- the total is then exactly preserved
    and the redistribution is bounded by the excursion, i.e. by the solver's own
    tolerance.

    A species whose total is *itself* negative has no other half to settle
    against; that residual is genuinely created, is bounded by round-off, and is
    RETURNED rather than swallowed so a caller can report it.
    """
    if not blocks:
        return blocks, np.zeros(0)

    out = [np.array(b, dtype=float, copy=True) for b in blocks]
    n = out[0].shape[0]
    created = np.zeros(n)
    floor = NEGLIGIBLE_TOTAL * len(out)

    for i in range(n):
        vals = np.array([b[i] for b in out])
        if (vals >= 0.0).all():
            continue
        total = float(vals.sum())
        if total <= 0.0:
            # Nothing positive to settle against. The whole (tiny) total is what
            # gets created; report anything above round-off.
            for b in out:
                b[i] = 0.0
            if total < -floor:
                created[i] = -total
            continue
        # Zero the negative entries and recover exactly that much from the
        # positive ones, biggest first, so the smallest holdings are disturbed
        # least and none can be driven back below zero.
        debt = -float(vals[vals < 0.0].sum())
        for k in np.flatnonzero(vals < 0.0):
            out[k][i] = 0.0
        for k in np.argsort(-vals):
            if debt <= 0.0:
                break
            take = min(debt, out[k][i])
            out[k][i] -= take
            debt -= take
    return out, created


@dataclass
class RootStop:
    """Where an integration stopped when it was told to watch for a condition.

    ``elapsed`` is the load-bearing field and the reason this is a dataclass
    rather than a bare state vector. A terminal event returns the state AT the
    event, so the span the caller asked for is NOT the span that happened, and a
    caller that advances its own clock by the requested duration silently drifts
    out of step with the vessel it is driving. Every clock above this one --
    ``Vessel.t``, ``World.t`` -- has to move by this number.

    ``already`` distinguishes "the condition became true during this span" from
    "it was already true when you asked", which are different answers to a
    player's question and must not be collapsed into one.
    """

    y: np.ndarray
    elapsed: float
    fired: int | None
    already: bool = False


@dataclass
class _Stationary:
    """The result of a solve that never had to run -- see ``VesselIntegrator.run``.

    Carries the same attributes callers read off a scipy solution, so a resting
    vessel is indistinguishable from an integrated one downstream.
    """

    t: np.ndarray
    y: np.ndarray
    success: bool = True
    status: int = 0
    message: str = "state is stationary within tolerance; no integration needed"
    nfev: int = 1
    njev: int = 0
    nlu: int = 0


class VesselIntegrator:
    """Integrates the coupled composition/phase/temperature system."""

    def __init__(
        self,
        kinetics: KineticArrays,
        phases: PhaseArrays,
        conditions: VesselConditions,
        precipitation: "PrecipitationArrays | None" = None,
        solid_state: "SolidStateArrays | None" = None,
        surface: "SurfaceArrays | None" = None,
    ):
        if np.isnan(kinetics.dH).any():
            raise ValueError(
                "an energy balance needs reaction enthalpies: build the network "
                "with a ThermochemistryProvider so KineticArrays.dH is populated"
            )
        self.kin = kinetics
        self.ph = phases
        self.cond = conditions
        # None means EXACTLY the old behaviour: no ionic lattice can leave
        # solution and the RHS adds an identically zero term. Same contract
        # ``losses=None`` and ``World.rig is None`` keep.
        self.prec = precipitation
        # M6. Same contract again: ``None`` is EXACTLY the old behaviour -- no
        # crystal can react, and the RHS adds an identically zero term.
        self.solid = solid_state
        # And again, for a crystal reacting with a gas that arrives at it:
        # ``None`` is EXACTLY no roasting. Kept separate from ``solid_state``
        # rather than folded into it because the two are different mechanisms
        # with different rate laws -- see ``SurfaceArrays``.
        self.surf = surface
        self.n = kinetics.n_species
        self._ingress = (
            np.zeros(self.n)
            if conditions.ingress is None
            else np.asarray(conditions.ingress, float)
        )
        # Split reactions by phase once, at setup, so the RHS never branches.
        rp = kinetics.phase
        self._liq = np.flatnonzero(rp == PHASE_LIQUID)
        self._gas = np.flatnonzero(rp == PHASE_GAS)
        # Per-species matter that the non-negative projection could not conserve.
        # Accumulated over the vessel's whole life so a long run cannot hide a
        # slow leak; ``Vessel.conservation_report`` is what surfaces it.
        self.created = np.zeros(self.n)
        # What the last tangent-plane test found, so Layer 5 can report a liquid
        # that WANTED to split even when the vessel was built with lle=False.
        # A stability result that is only acted on and never surfaced is the
        # silent kind of decision this project does not allow.
        self.last_stability: StabilityResult | None = None
        # ⚠ WHICH IONS EACH REACTION MAKES, as an (r, n) matrix of product
        # stoichiometries restricted to charged species. This is the whole input to
        # the ionic rate correction below, and it needs no new Layer 3 array: the
        # product side is ``max(delta, 0)`` and the charge is a mask Layer 5
        # already supplies.
        self._ion_products = np.where(
            phases.ionic[None, :], np.maximum(kinetics.delta, 0.0), 0.0
        )
        self._has_ionic_reactions = bool(
            phases.has_ions and np.any(self._ion_products > 0.0)
        )
        # Ionic mole fraction of a split this integrator declined to make, so
        # Layer 5 can say why a flask that should have two layers has one, plus
        # WHICH of the two narrow refusals fired and the coverage that triggered
        # it. A refusal that could not say which one it was would be untraceable.
        self.refused_split = 0.0
        self.refused_reason = ""
        self.refused_coverage = 1.0
        # ⚠ WHETHER THE LAST BOUNDARY DECISION NUDGED A NEW LAYER INTO EXISTENCE,
        # which is the one case a frozen polarity must not be applied to -- see
        # ``make_rhs`` and ``FREEZE_LAYER_PERMITTIVITY``. A seed is deliberately NOT
        # the tie line (see SPLIT_SEED_FRACTION): it is a nudge off the trivial
        # solution, and the RHS relaxation carries it the rest of the way.
        self.just_seeded = False

    # -- state vector helpers ------------------------------------------------

    def pack(self, n_liquid, n_liquid2, n_gas, n_solid, T: float) -> np.ndarray:
        return np.concatenate([n_liquid, n_liquid2, n_gas, n_solid, [T]])

    def unpack(
        self, y: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
        n = self.n
        return (
            y[:n], y[n : 2 * n], y[2 * n : 3 * n], y[3 * n : 4 * n], float(y[-1])
        )

    # -- physics -------------------------------------------------------------

    def latent_heat(self, T: float) -> np.ndarray:
        """Watson-scaled enthalpy of vaporization at T, J/mol.

            Hvap(T) = Hvap(Tb) * ((Tc - T)/(Tc - Tb)) ** 0.38

        Zero for non-condensable solutes (they have no latent heat to give) and
        clamped to zero above Tc, where there is no phase change left to make.
        """
        num = np.maximum(self.ph.Tc - T, 0.0)
        den = np.maximum(self.ph.Tc - self.ph.Tb, 1.0e-9)
        H = self.ph.Hvap_Tb * (num / den) ** WATSON_EXPONENT
        return np.where(self.ph.condensable, H, 0.0)

    def saturation_coefficients(self, T: float) -> np.ndarray:
        """The Antoine value per species at T, bar: Psat (Raoult) or H (Henry)."""
        denom = self.ph.vol_C + T
        safe = np.where(denom > 0.0, denom, 1.0)
        return np.where(denom > 0.0, 10.0 ** (self.ph.vol_A - self.ph.vol_B / safe), 0.0)

    def activity_coefficients(self, n_liquid: np.ndarray, T: float) -> np.ndarray:
        """Liquid-phase activity coefficients at the current composition.

        Ideal (all ones) when no group parameters were supplied. Amounts rather
        than mole fractions are fine -- the kernel normalises.
        """
        return activity_coefficients(
            n_liquid, self.ph.nu, self.ph.R_k, self.ph.Q_k,
            self.ph.a_mn, self.ph.gamma_active, T,
            self.ph.reference_correction(T),
            self.ph.born_block(T),
        )

    def saturation_activity(self, T: float) -> np.ndarray:
        """The ACTIVITY a solute reaches at saturation, from the fusion balance.

            ln(a_sat) = -(Hfus / R) * (1/T - 1/Tm)

        This is the composition-independent half of the solubility law, and
        writing it separately is what lets one equation keep covering both
        dissolution and melting. At T = Tm the right-hand side is zero, so
        a_sat = 1 and the solid is fully miscible with its own melt. Below Tm it
        falls off exponentially -- that is solubility. Above Tm it is clamped at
        1, meaning "cannot exist as a solid", which is exactly true.

        Species with no fusion data (dissolved gases, ions) never crystallise and
        get a_sat = 1.
        """
        Tm = np.maximum(self.ph.Tm, 1.0)
        a = np.exp(-(self.ph.Hfus / R) * (1.0 / max(T, T_MIN) - 1.0 / Tm))
        a = np.clip(a, 1.0e-12, 1.0)
        return np.where(self.ph.solidifies, a, 1.0)

    def solubility(self, T: float, gamma: np.ndarray | None = None) -> np.ndarray:
        """Saturation MOLE FRACTION: x_sat = a_sat / gamma, capped at 1.

            ln(x_sat * gamma) = -(Hfus / R) * (1/T - 1/Tm)

        The ideal law (gamma = 1) is right for melting and badly wrong for a
        solute in a dissimilar solvent -- it is the whole reason benzoic acid
        used to come out ~350x too soluble in water. Since gamma is evaluated at
        the CURRENT composition rather than at saturation, the instantaneous
        driving force is approximate, but the fixed point it relaxes to is not:
        the flux vanishes exactly where x_i * gamma_i(x) = a_sat, which is the
        true saturation condition.

        A gamma below 1 (a solvent that likes the solute more than the solute
        likes itself) can push x_sat above 1; the cap means "miscible".
        """
        a_sat = self.saturation_activity(T)
        if gamma is None:
            return a_sat
        return np.minimum(a_sat / np.maximum(gamma, 1.0e-30), 1.0)

    def equilibrium_pressures(
        self, n_liquid: np.ndarray, T: float, n_liquid2: np.ndarray | None = None
    ) -> np.ndarray:
        """p_eq,i = a_i * coefficient_i(T) -- Raoult or Henry, on the ACTIVITY.

        The activity coefficient is what makes an azeotrope possible: with
        gamma == 1 the vapour is always richer in the more volatile component, so
        distillation would run to a pure product every time. x_i is the true mole
        fraction over all species, while gamma comes from the non-electrolyte
        subsystem -- species with no group decomposition sit at gamma = 1 and are
        invisible to the model, which is stated upstream, not assumed here.

        With two liquid layers this is the WET-WEIGHTED mean of the two layers'
        activities, which is not a choice of estimator -- it is the fixed point
        of the RHS's own evaporation term, where each layer drives the shared
        headspace toward its own equilibrium with the same ``kla``:

            wet1 (a1 psat - p) + wet2 (a2 psat - p) = 0

        Using anything else here would make the readout disagree with the
        dynamics it is supposed to describe. At liquid-liquid equilibrium a
        species has the SAME activity in both layers, so the weighting stops
        mattering and this is exact. **That is why two immiscible liquids boil
        below either of them**: each layer is nearly pure in its own component,
        so each contributes nearly its own full vapour pressure and the total
        reaches ambient early. A single-phase call reduces to the old
        expression exactly.

        ⚠ It is still a FROZEN-COMPOSITION readout. Scanning temperature (as
        ``bubble_point`` does) recomputes gamma but not the tie line, so the two
        layers drift out of liquid-liquid equilibrium as the scan moves away
        from the current state and the answer reads high. Heating the flask for
        real does not have that problem, because then the layers re-equilibrate
        as they warm -- which is why the steam-distillation check is a HEATED
        one and not a call to ``bubble_point``.

        ⚠ **THE ``wet`` RAMP BELOW IS THE LAST ONE IN THIS FILE AND IT SURVIVES
        ON PURPOSE -- do not "fix" it to match ``_dryout_gates``.** Two reasons,
        and the second is the one that bites. (1) It is a NORMALISED mean: the
        weights divide out, so a single-layer call reduces to ``x * gamma * psat``
        for ANY positive weighting, and at liquid-liquid equilibrium the two
        activities are equal so the weighting stops mattering entirely. (2) A
        smoothstep is exactly ZERO below DRYOUT_MOLES, which would make this
        readout return **no vapour pressure at all** for a flask holding a trace
        of liquid -- and ``bubble_point``, ``volatile_pressure`` and
        ``Vessel.is_boiling`` are all built on it. The RHS wants a gate that shuts
        off; a readout of "what is this liquid's equilibrium pressure" must not.
        """
        n1 = np.maximum(n_liquid, 0.0)
        N1 = float(n1.sum())
        n2 = (
            np.zeros(self.n) if n_liquid2 is None else np.maximum(n_liquid2, 0.0)
        )
        N2 = float(n2.sum())
        if N1 + N2 <= 0.0:
            return np.zeros(self.n)
        wet1 = N1 / (N1 + DRYOUT_MOLES)
        wet2 = N2 / (N2 + DRYOUT_MOLES)
        a = np.zeros(self.n)
        if N1 > 0.0:
            a += wet1 * (n1 / N1) * self.activity_coefficients(n1, T)
        if N2 > 0.0:
            a += wet2 * (n2 / N2) * self.activity_coefficients(n2, T)
        return (a / max(wet1 + wet2, 1.0e-30)) * self.saturation_coefficients(T)

    def volatile_pressure(
        self, n_liquid: np.ndarray, T: float, n_liquid2: np.ndarray | None = None
    ) -> float:
        """Summed equilibrium partial pressure of the CONDENSABLE species, bar.

        ⚠ WHAT "BOILING" IS A STATEMENT ABOUT, and getting this wrong was a real
        pre-existing bug with a confident wrong number attached. Summing ALL of
        ``equilibrium_pressures`` includes the Henry back-pressure of every
        dissolved gas -- and a liquid in equilibrium with a headspace full of air
        holds exactly enough dissolved nitrogen and oxygen to return that air's own
        partial pressures. So the sum reaches ambient at EVERY temperature, and a
        50/50 ethanol/water flask at 298 K reported ``is_boiling`` and a bubble
        point of 297.8 K instead of 352.9.

        A dissolved gas at equilibrium with the headspace exerts no net driving
        force -- its partial pressure is already there -- so it cannot displace the
        atmosphere, which is what boiling is. A beaker of air-saturated water at
        room temperature is not boiling. The condensable species are the ones whose
        vapour has to be made, and they are what this sums.

        (Effervescence -- a dissolved gas SUPERSATURATED against its headspace --
        is a real and different phenomenon. The RHS already carries it, per
        species, in the evaporation term. It is not boiling and does not belong in
        a boiling-point readout.)
        """
        p = self.equilibrium_pressures(n_liquid, T, n_liquid2)
        return float(p[self.ph.condensable].sum())

    def make_rhs(self, y0: np.ndarray | None = None, probe: dict | None = None):
        """Compile dy/dt. Everything below is array arithmetic on plain floats.

        ``y0`` is the state at the INTEGRATION BOUNDARY, and the only thing it is
        used for is freezing each liquid layer's polarity -- see
        ``FREEZE_LAYER_PERMITTIVITY``. Passing ``None`` recomputes the mixture
        permittivity from the composition on every call, which is what this did
        before and is what the harness compares against.

        ``probe``, if given, is a dict the RHS overwrites with the energy balance
        it just evaluated -- every watt the temperature equation saw, term by
        term, plus the fluxes each was priced against. It exists because the
        temperature equation is the one place where a sum of nearly-cancelling
        terms cannot be checked against a conserved total: matter is audited by
        ``conservation_report`` and energy was audited by nothing (M12). One
        ``is not None`` test per evaluation, against a call that does dozens of
        matmuls; ``energy_terms`` is the supported way in.
        """
        kin, ph, cond = self.kin, self.ph, self.cond
        n = self.n
        order, delta, A, Ea, dH = kin.order, kin.delta, kin.A, kin.Ea, kin.dH
        n_exp = kin.n_exp
        # T**0 is a wasted array op on every RHS call, and delta_n is zero for
        # most networks, so the exponent is only evaluated where one is present.
        has_n_exp = bool(np.any(n_exp))
        # The heterogeneous-catalyst factor, and it is skipped entirely for a
        # network that declares none -- ``prod(nS ** 0)`` is a column of ones and
        # an array op nobody needs. So an uncatalysed network is bit-identical to
        # what it was before this existed.
        order_solid = kin.order_solid
        has_solid_catalyst = bool(np.any(order_solid))
        ingress = self._ingress
        liq_rxn, gas_rxn = self._liq, self._gas

        ion_products = self._ion_products
        has_ionic = self._has_ionic_reactions

        # The frozen volume weights, one set per liquid layer. Taken from the
        # boundary state and then left alone, so the mixing rule contracts a
        # constant and the ion terms stop coupling to every liquid amount.
        #
        # ⚠ An EMPTY layer is left live (``None``) rather than frozen at nothing.
        # A flask that is dry at the boundary and fills during the call -- a solid
        # melting, a vapour condensing into a cold receiver -- would otherwise
        # carry frozen weights that sum to zero, which reads as "no medium" and
        # would put its ions back at gamma = 1. There is nothing to couple to in
        # an empty layer, so this costs nothing and closes the case.
        frozen1 = frozen2 = None
        if y0 is not None:
            yb = np.asarray(y0, dtype=float)
            v_mol_0 = np.maximum(
                _poly(ph.v_liq, min(max(float(yb[-1]), T_MIN), T_MAX)), 0.0
            )
            b1 = np.maximum(yb[:n], 0.0) * v_mol_0
            b2 = np.maximum(yb[n : 2 * n], 0.0) * v_mol_0
            frozen1 = b1 if b1.sum() > 0.0 else None
            frozen2 = b2 if b2.sum() > 0.0 else None
            # ⚠ AND NEITHER LAYER IS FROZEN ON THE CALL A SPLIT APPEARS IN. This is
            # a real error the tests caught rather than a nicety, and it is the
            # freeze's worst case stated exactly: a layer whose composition changes
            # by a LOT during one call.
            #
            # ``split_phases`` nudges 1% of the liquid to the tangent-plane test's
            # TRIAL composition and lets the RHS relaxation find the tie line, so at
            # that boundary NEITHER layer is anywhere near where it converges to --
            # the new layer is a seed rather than a phase, and the old one still
            # holds all the material the new one is about to take. Measured on brine
            # against toluene, where layer 1 at that boundary is about half toluene
            # by volume: freezing it read the AQUEOUS layer's permittivity as ~15
            # instead of 78, which gives an ion in the water a large positive
            # transfer term instead of exactly zero and pushes it OUT. It let twenty
            # times as much sodium into the toluene -- 2.2e-5 mol against 9.8e-7.
            #
            # It costs only the call a split first appears in; by the next boundary
            # the layers are on their tie line and freezing is right again. And the
            # expensive integration this whole bargain was for -- the prep's acid
            # quench -- is single-phase, so it never pays this at all.
            if self.just_seeded:
                frozen1 = frozen2 = None

        def _phase_rates(idx, C, V, T, ln_gamma_ion=None, sink=None, nS=None):
            """Reaction source term (mol/s) and heat release (J/s) for one phase.

            ``ln_gamma_ion`` is the layer's BORN transfer term (see
            ``activity.born_ln_gamma``), and what it does here is the one place
            this project's rate laws are not purely on a concentration basis.

            ``nS`` is the solid block, and it is the SECOND such place: a
            template may declare a heterogeneous catalyst, whose exponent is on
            an AMOUNT in mol rather than on a concentration. See
            ``KineticArrays.order_solid``. The reaction itself is still a
            reaction of this phase -- the catalyst multiplies its rate and enters
            neither its stoichiometry nor its standard state.
            """
            if idx.size == 0 or V <= 0.0:
                return np.zeros(n), 0.0
            k = A[idx] * np.exp(-Ea[idx] / (R * T))
            if has_n_exp:
                k = k * T ** n_exp[idx]
            if has_ionic and ln_gamma_ion is not None:
                # ⚠ AN AQUEOUS pKa DOES NOT APPLY IN AN OIL, and this is what
                # stops it being applied there anyway.
                #
                # Every ion in this project is priced from a measured AQUEOUS pKa
                # (see ``properties/electrolyte``), so the equilibrium constant of
                # any ion-producing reaction is anchored to water. Run that
                # constant unchanged inside an organic layer and you get benzoic
                # acid as dissociated in toluene as in water -- which is the exact
                # opposite of what an acid/base extraction relies on, and was one
                # of the two reasons an electrolyte split used to be refused
                # outright. The Born term fixed the other one (ions staying in the
                # water); this fixes this one.
                #
                # The correction is the activity-basis one, ``K_c = K_a / prod
                # gamma^nu`` over the ions, and it is placed ENTIRELY on the
                # direction that CREATES them. That is a real modelling choice with
                # a name -- Bronsted-Bjerrum, with the transition state taken to be
                # as ionic as the products, which for a heterolysis is the
                # conventional assumption -- and it is also the only placement that
                # is numerically survivable. Put it on the reverse instead and the
                # recombination rate constant is multiplied by e^24 while the ion
                # pool it acts on is unchanged: same equilibrium, a Jacobian entry
                # of 1e27, and an unsolvable flask. Put it on the forward direction
                # and the disfavoured species is simply never made, so the fast
                # mode has nothing to act on.
                #
                # ⚠ IN WATER THIS FACTOR IS exp(0) = 1.0 EXACTLY, because the Born
                # term is exactly zero in the reference solvent. So every number
                # this project has ever measured in a single aqueous phase is
                # bit-identical, and the five pH invariants cannot move. That is
                # not a hope, it is the reason the correction is written against
                # the Born term rather than against a general activity model.
                k = k * np.exp(
                    np.clip(-(ion_products[idx] @ ln_gamma_ion), -50.0, 50.0)
                )
            rates = k * np.prod(C**order[idx], axis=1)      # mol/(L s)
            if has_solid_catalyst and nS is not None:
                # ⚠ THE ONE FACTOR THAT MAKES "YOU NEED A CATALYST" A GATE. An
                # absent catalyst is ``0 ** 1 = 0`` exactly, so the reaction does
                # not go at all -- and the slope in the catalyst's amount is
                # ``k prod(C**order)``, bounded, so an empty solid block
                # contributes a finite Jacobian column rather than a knee. This
                # is the same shape ``SurfaceArrays`` relies on and the reason
                # neither of them needs an ``_avail`` gate.
                rates = rates * np.prod(nS ** order_solid[idx], axis=1)
            if sink is not None:
                # Per-reaction watts, for the cancellation audit only. The NET is
                # what the temperature sees; the GROSS is what M12 turned out to
                # be about, and a report that shows only the net cannot tell a
                # quiet zero from two 5.2e9 W terms that happen to cancel.
                sink.append(-dH[idx] * rates * V)
            return delta[idx].T @ rates * V, -float(dH[idx] @ rates) * V

        prec = self.prec
        solid = self.solid
        surf = self.surf
        # Precomputed at SETUP, so the hot loop indexes rather than branches --
        # the same split ``self._liq``/``self._gas`` gets. ``is_lattice`` is what
        # makes one boolean serve as both the basis selector and the destination
        # selector; see ``SurfaceArrays``.
        is_lattice = ph.lattice
        if surf is not None and surf.m:
            surf_nu_solid = np.where(is_lattice[None, :], surf.nu, 0.0)
            surf_nu_gas = np.where(is_lattice[None, :], 0.0, surf.nu)
        else:
            surf_nu_solid = surf_nu_gas = None

        def rhs(t: float, y: np.ndarray) -> np.ndarray:
            nL1 = np.maximum(y[:n], 0.0)
            nL2 = np.maximum(y[n : 2 * n], 0.0)
            nG = np.maximum(y[2 * n : 3 * n], 0.0)
            nS = np.maximum(y[3 * n : 4 * n], 0.0)
            T = min(max(float(y[-1]), T_MIN), T_MAX)

            # --- volumes ------------------------------------------------
            v_mol = np.maximum(_poly(ph.v_liq, T), 0.0)
            V_L1 = float(nL1 @ v_mol)
            V_L2 = float(nL2 @ v_mol)
            V_S = float(nS @ v_mol)          # solids use the liquid molar volume
            V_G = max(cond.volume - V_L1 - V_L2 - V_S, V_GAS_MIN)

            # --- the ion-transfer term, needed by BOTH blocks below -----
            # Computed before the reactions because an ion-producing reaction's
            # equilibrium constant depends on the medium -- see ``_phase_rates``.
            # One block, both layers, a function of T alone: ``born_block``.
            born = ph.born_block(T)
            ln_ion1 = None if born is None else born_ln_gamma(
                nL1, born, T, phi=frozen1
            )
            ln_ion2 = None if born is None else born_ln_gamma(
                nL2, born, T, phi=frozen2
            )

            # --- reaction, per phase ------------------------------------
            # A liquid-phase reaction runs in BOTH layers, at each layer's own
            # concentrations. That is not bookkeeping: it is why an extraction
            # can quench a reaction (pull the substrate into a layer the
            # catalyst is not in) without anything saying so.
            dn_rxn1 = np.zeros(n)
            dn_rxn2 = np.zeros(n)
            q_rxn = 0.0
            q_rxn2 = 0.0
            sink = [] if probe is not None else None
            if V_L1 > V_LIQUID_MIN:
                d, q = _phase_rates(liq_rxn, nL1 / V_L1, V_L1, T, ln_ion1, sink,
                                    nS=nS)
                dn_rxn1 += d
                q_rxn += q
            if V_L2 > V_LIQUID_MIN:
                # Gated below, once ``gate2`` exists -- a perturbation of an
                # empty layer must not switch a whole reaction term on.
                dn_rxn2, q_rxn2 = _phase_rates(
                    liq_rxn, nL2 / V_L2, V_L2, T, ln_ion2, nS=nS
                )
            else:
                q_rxn2 = 0.0
            dn_gas_rxn, q_gas = _phase_rates(gas_rxn, nG / V_G, V_G, T, nS=nS)
            q_rxn += q_gas

            # --- activity coefficients ----------------------------------
            # The one property that cannot be precomputed, because it depends on
            # composition rather than on T alone. Evaluated once here and shared
            # by the vapour and solid equilibria below, which have to agree on
            # it: the same non-ideality that bends a boiling point is the one
            # that decides how much will dissolve.
            ln_ref = ph.reference_correction(T)
            # ``ln_ion1``/``ln_ion2`` were already evaluated above for the rate
            # correction, at exactly these compositions, so they are handed over
            # rather than recomputed.
            gamma1 = activity_coefficients(
                nL1, ph.nu, ph.R_k, ph.Q_k, ph.a_mn, ph.gamma_active, T, ln_ref,
                born, ln_ion1,
            )
            gamma2 = activity_coefficients(
                nL2, ph.nu, ph.R_k, ph.Q_k, ph.a_mn, ph.gamma_active, T, ln_ref,
                born, ln_ion2,
            )

            # Mole fractions and ACTIVITIES per layer. The activity is the
            # quantity every equilibrium below is written against -- vapour,
            # solid and the other layer all compare to a_i = x_i * gamma_i --
            # so computing it once here is what keeps the three of them from
            # disagreeing about what equilibrium means.
            N1 = float(nL1.sum())
            N2 = float(nL2.sum())
            # ⚠ THE GATE AND THE 0/0 GUARD ARE ON DIFFERENT SCALES, DELIBERATELY,
            # AND THEY USED TO BE ON THE SAME ONE -- which is what created matter.
            # ``MOLE_FRACTION_DENOM`` is 24 decades below the gate and is not a
            # gate at all, so **these mole fractions sum to 1 whenever any liquid
            # exists**. Floored on the gating scale instead they summed to 0.57
            # inside the band, every activity was understated by the same factor,
            # and a sulfur burner at 690 K created 11% of its oxygen. The gate
            # itself is paired with the dry-flask branch below and the two are
            # COMPLEMENTARY -- see ``_dryout_gates``, which is where making them
            # disjoint instead is measured and rejected.
            wet1, dry_all = _dryout_gates(N1, N1 + N2)
            x1 = nL1 / max(N1, MOLE_FRACTION_DENOM)
            a1 = x1 * gamma1
            # Layer 2 is gated by a DISJOINT pair (``_layer_gates``) where layer 1
            # above takes a COMPLEMENTARY one, and the difference is argued in
            # both docstrings. Its mole fractions ARE floored on its gating scale,
            # and that is safe only because ``gate2`` is identically zero wherever
            # the floor binds -- the property layer 1 lacked. At N2 = 0 the gate is
            # zero AND flat, so an absent layer contributes an identically zero
            # Jacobian column instead of one worth 1e8. See LAYER_EPS -- this cost
            # a 10x slowdown and broke reflux before it was found.
            gate1, _ = _layer_gates(N1)
            gate2, drain2 = _layer_gates(N2)
            x2 = nL2 / max(N2, LAYER_EPS)
            a2 = x2 * gamma2

            # --- liquid <-> vapour --------------------------------------
            # Raoult only has meaning while a liquid exists. As the last of it
            # boils off, blend to the dry-flask law: vapour above an empty flask
            # is superheated and does nothing unless it exceeds the pure-component
            # saturation pressure, in which case it condenses. Blending (rather
            # than switching on nL == 0) matters -- a hard switch here is a
            # discontinuity the stiff solver cannot step across. The dry-flask
            # branch needs no gamma: it is a pure-component statement, and a pure
            # component's activity coefficient is 1 by definition.
            #
            # BOTH LAYERS EVAPORATE INTO THE SAME HEADSPACE, each toward its own
            # equilibrium partial pressure, and that is the whole of steam
            # distillation: two nearly immiscible liquids each contribute close
            # to their PURE vapour pressure, so the total reaches ambient BELOW
            # either component's boiling point. Nothing here knows that; it is
            # what two independent driving forces against one shared ``p`` do.
            # ⚠ The interfacial area is not resolved -- each layer is taken to
            # be in contact with the headspace, which is true under agitation
            # and is the condition steam distillation is run under anyway.
            psat = self.saturation_coefficients(T)
            p = nG * R_L_BAR * T / V_G
            # The dry-flask branch: vapour above an empty flask is superheated
            # and does nothing unless it exceeds the pure-component saturation
            # pressure, in which case it condenses -- into layer 1, the same
            # convention the melt below uses. ``dry_all`` came from the same
            # ``_dryout_gates`` call as ``wet1`` and was evaluated on BOTH layers,
            # because a flask holding all its liquid in layer 2 is not dry.
            evap1 = cond.kla * wet1 * (a1 * psat - p)     # mol/s, + = evaporating
            evap2 = cond.kla * gate2 * (a2 * psat - p)
            evap_dry = cond.kla * dry_all * np.minimum(psat - p, 0.0)
            evap1 = np.where(nG <= 0.0, np.maximum(evap1, 0.0), evap1)
            evap2 = np.where(nG <= 0.0, np.maximum(evap2, 0.0), evap2)
            evap_dry = np.where(nG <= 0.0, np.maximum(evap_dry, 0.0), evap_dry)
            evap = evap1 + evap2 + evap_dry
            q_vap = -float(evap @ self.latent_heat(T))    # evaporation cools

            # --- solid <-> liquid ---------------------------------------
            # Equilibrium is x_i = x_sat,i, so the driving force in moles is
            # (x_sat * n_liquid_total - n_liquid_i). That alone cannot melt a dry
            # solid, though: with no solvent the total is zero and the force
            # vanishes, so a pure substance heated past its melting point would
            # just sit there. The fix is to let a solid count toward its OWN
            # solution as x_sat approaches 1 -- which happens exactly at Tm,
            # because that is what the solubility law says. MELT_BLEND sets how
            # sharply it takes over, i.e. the width of the melting range.
            #
            # Note which quantity gates melting: the saturation ACTIVITY, not the
            # saturation mole fraction. Melting is a pure-component event -- a
            # solid in equilibrium with its own melt, where gamma is 1 by
            # definition -- so it must not be affected by how badly some solvent
            # happens to dissolve it. Dissolution uses the gamma-corrected
            # x_sat; melting uses the raw a_sat, which still reaches 1 exactly
            # at Tm. The two uses of one equation finally part company here.
            #
            # A solid in a two-layer flask dissolves into BOTH, each to its own
            # saturation -- which is what makes "wash the organic layer" and
            # "the product crashed out of the aqueous side" different events.
            # ⚠ The self-melt term goes to layer 1 only. A melt is a new liquid
            # and there is no basis for splitting it across layers that already
            # exist; if it is immiscible with layer 2 the stability test will
            # say so at the next boundary. It also keeps the empty-layer-2 case
            # exactly equal to the old one-liquid expression, since layer 2's
            # pool is then identically zero.
            self_melt = np.clip(
                (self.saturation_activity(T) - MELT_BLEND) / (1.0 - MELT_BLEND),
                0.0,
                1.0,
            )
            # You cannot dissolve a solid that is not there; you can always
            # precipitate a solute that is. ``_avail`` is that gate, and its
            # scale is set by the DRIVING FORCE rather than by a constant --
            # see SOLID_GATE_TIME for why, and for what a fixed 1e-9 knee
            # cost. Each layer gets its own, because each has its own
            # undersaturation to be limited against.
            x_sat1 = self.solubility(T, gamma1)
            x_sat2 = self.solubility(T, gamma2)
            excess1 = x_sat1 * (max(N1, 0.0) + self_melt * nS) - nL1
            excess2 = x_sat2 * max(N2, 0.0) - nL2         # + = room to dissolve
            avail1 = _avail(nS, cond.k_diss * excess1)
            avail2 = _avail(nS, cond.k_diss * excess2)
            solute1 = cond.k_diss * np.where(excess1 > 0.0, excess1 * avail1, excess1)
            solute2 = cond.k_diss * gate2 * np.where(
                excess2 > 0.0, excess2 * avail2, excess2
            )
            solute1 = np.where(ph.solidifies, solute1, 0.0)  # mol/s, + = dissolving
            solute2 = np.where(ph.solidifies, solute2, 0.0)
            solute = solute1 + solute2
            q_fus = -float(solute @ ph.Hfus)               # dissolving/melting cools

            # --- ionic lattices: a SOLUBILITY PRODUCT --------------------
            # M3. The block above cannot do this: it works species by species
            # against a fusion law, and an ion has no Tm, no Hfus and no
            # ``solidifies``. A lattice leaves solution as a STOICHIOMETRIC
            # GROUP against Q/Ksp, so it needs its own term -- see
            # ``PrecipitationArrays`` for the form, the gate and what is in its
            # dead zone.
            #
            # ⚠ LAYER 1 ONLY, and that is not laziness. ``split_phases``
            # REFUSES to put an electrolyte into two layers (the Born term is
            # referenced to water and an ion at equal mole fraction in toluene
            # is what it exists to prevent), so every ion in this vessel is in
            # layer 1 by construction. Writing the term against layer 2 as well
            # would be modelling a state the phase decision does not allow.
            if prec is not None and prec.m and V_L1 > V_LIQUID_MIN:
                c = nL1 / V_L1                                   # mol/L
                ln_c = np.log(np.maximum(c, CONC_FLOOR))
                # Q^(1/N) and Ksp^(1/N), both concentrations in mol/L.
                ln_Qroot = (prec.nu @ ln_c) / prec.total_nu
                ln_Ksproot = prec.ln_Ksp(T) / prec.total_nu
                # ⚠ THE CAP CARRIES THE MULTIPLY'S HEADROOM -- see
                # LN_SATURATION_CAP, where the state that forced it is written
                # down. Bit-identical while ``k_diss * V_L1 <= 1``.
                #
                # ⚠⚠ ``log(max(scale, 1))`` AND **NOT** ``max(log(scale), 0)``.
                # Those two are the same function only where the log is DEFINED,
                # and ``scale`` is zero whenever a vessel declares
                # ``k_diss = 0.0`` -- which three examples do
                # (``workshop`` part 3, ``named_routes``, and ``recipes``'
                # crystallise stage, so ``multistep_prep`` as well). Written the
                # other way this line raised ``ValueError: math domain error``
                # in all three, and NOTHING IN THE TEST SUITE CAUGHT IT:
                # ``tolerance_audit.py`` did, which is what that audit is for.
                scale = cond.k_diss * V_L1
                head = LN_SATURATION_CAP - math.log(max(scale, 1.0))
                roots = np.exp(np.clip(
                    np.stack([ln_Qroot, ln_Ksproot]),
                    -LN_SATURATION_CAP, head,
                ))
                drive = scale * (roots[0] - roots[1])                # + = out
                # How many formula units of THIS lattice the solid block can
                # supply. A lattice missing any of its ions from the solid has
                # units = 0 and cannot dissolve, which is what keeps a lattice
                # that never precipitated from being dissolved out of another
                # one's crop. See the dataclass for the limit this leaves.
                ratio = np.where(prec.nu > 0.0,
                                 nS[None, :] / np.maximum(prec.nu, 1.0),
                                 np.inf)
                units = ratio.min(axis=1)
                # Ungated one way, ``_avail``-gated the other -- exactly the
                # arrangement the dissolution term above uses.
                flux = np.where(drive > 0.0, drive,
                                drive * _avail(units, -np.minimum(drive, 0.0)))
                precipitate = flux @ prec.nu                     # (n,) mol/s
                # Precipitation is the REVERSE of dissolution, so it releases
                # the dissolution enthalpy: + flux * dH_diss watts.
                q_fus += float(flux @ prec.dH_diss)
            else:
                precipitate = 0.0

            # --- a reaction INSIDE the crystal --------------------------
            # M6. Neither block above can write this: the reactant and the
            # product are both solids and the gas it evolves is a third place
            # again. See ``SolidStateArrays`` for why it is a term rather than a
            # third ``PHASE_INDEX`` entry -- a pure solid has unit activity, and
            # mass action on the solid amounts gives an equilibrium pressure
            # that depends on how much of the charge has converted.
            #
            # Nothing here is gated. This term's driving force IS the amount of
            # solid present, so it is exactly zero at an empty block with a
            # bounded slope, which is the property ``_avail`` had to manufacture
            # for dissolution.
            if solid is not None and solid.m:
                k_f = solid.A_fwd * np.exp(-solid.Ea_fwd / (R * T))
                k_r = solid.A_rev * np.exp(-solid.Ea_rev / (R * T))
                # ⚠⚠ S9 -- THE GAS SIDE AS TWO ONE-SIDED PRODUCTS RATHER THAN
                # ONE QUOTIENT, WHICH IS THE WHOLE REVERSIBLE SOLID-GAS TERM.
                # A crystal is at unit activity, so only the gases appear -- but
                # taken as a single ``Q = prod(p ** nu_gas)`` a gas REACTANT
                # carries a NEGATIVE exponent, i.e. its pressure sits in a
                # denominator, and an atmosphere depleted of it drove the
                # reverse flux to 2.6e15 formula units per second. That was
                # refused where these arrays are built for five milestones.
                # Written as the two one-sided products nothing is divided:
                #
                #     net = k_f P_react - k_r P_prod
                #
                # is ``P_react (k_f - k_r Q)`` algebraically -- SAME zero, so
                # still ``Q = K`` -- and at ``p_react = 0`` it is the finite
                # ``-k_r P_prod``. ⚠ The five pre-S9 rows have ``nu_gas >= 0``,
                # so ``P_react`` is an empty product of exactly 1.0 and
                # ``P_prod`` is the old ``Q`` element for element: bit-identical,
                # which a test pins against the recorded lime-kiln numbers.
                pp = np.maximum(p, 0.0)[None, :]
                P_react = np.prod(pp ** solid.gas_consumed, axis=1)
                P_prod = np.prod(pp ** solid.gas_formed, axis=1)
                units_f, units_r = solid.units(nS)
                # ⚠ ONE ``units`` FOR BOTH DIRECTIONS, CHOSEN BY THE SIGN OF THE
                # AFFINITY -- not one per direction. This is the whole
                # unit-activity claim in one line, and the version that got it
                # wrong was BUILT AND MEASURED first: with ``k_f units_f -
                # k_r Q units_r`` a sealed kiln settles at
                #
                #     p / K  =  n(calcite) / n(quicklime)
                #
                # exactly -- 3.0863 against 3.0863 at 1100 K and 1.2139 against
                # 1.2139 at 1200 K, five figures on both. That IS mass action on
                # the solid amounts, and it is the failure ``SolidStateArrays``
                # predicts from a pure solid having unit activity. Written this
                # way ``units`` is a common factor, so it divides out of
                # ``net = 0`` and the equilibrium is ``Q = K`` whatever the
                # crystals weigh -- while an EXHAUSTED side still stops the
                # reaction, because that direction's ``units`` is zero.
                net = k_f * P_react - k_r * P_prod      # 1/s x bar^n, signed
                s_flux = net * np.where(net > 0.0, units_f, units_r)   # mol/s
                dn_solid_rxn = s_flux @ solid.nu_solid
                dn_gas_srxn = s_flux @ solid.nu_gas
                # Endothermic forward, so a running kiln COOLS its own charge.
                q_solid = -float(s_flux @ solid.dH)
            else:
                dn_solid_rxn = 0.0
                dn_gas_srxn = 0.0
                q_solid = 0.0
                s_flux = None

            # --- a gas ARRIVING at a crystal ----------------------------
            # Roasting. Mass action, first order in the arriving gas and gated on
            # the solid being present. ⚠⚠ S9 -- THIS COMMENT USED TO SAY THE TERM
            # ABOVE "measurably is NOT a rate law for" a gas reactant, because
            # its pressure lands in the denominator of an affinity quotient.
            # That refusal is GONE: the quotient is written as two one-sided
            # products now and three rows up there consume a gas. **The reason
            # roasting is still HERE is the ORDER, not the denominator** -- an
            # affinity form's exponents are fixed at the stoichiometric
            # coefficients by detailed balance, and ``3 O2`` taken third order
            # stalls asymptotically as the atmosphere is consumed, which is
            # exactly what ``SurfaceReaction.orders`` exists to declare away.
            # See ``SurfaceArrays`` and ``properties/surface.py``.
            #
            # ⚠ THE MIXED BASIS IS THIS ONE LINE. A lattice enters on its AMOUNT
            # and everything else on its headspace CONCENTRATION, so the rate
            # comes out in mol/s and is NOT scaled by a volume the way every
            # other rate law here is. A solid's concentration would be an
            # inventory divided by a nominal molar volume; a gas's amount would
            # make the reaction indifferent to compression.
            if surf is not None and surf.m:
                C_mix = np.where(is_lattice, nS, nG / V_G)
                k_surf = surf.A * np.exp(-surf.Ea / (R * T))
                # ONE exponent matrix, because the basis is chosen per species
                # and each species sits in exactly one of the two declared
                # halves -- see ``SurfaceArrays.__post_init__``, where the sum is
                # taken and the reason the halves still exist is recorded.
                surf_rate = k_surf * np.prod(
                    C_mix[None, :] ** surf.order, axis=1
                )                                          # (m,) mol/s
                dn_solid_surf = surf_rate @ surf_nu_solid
                dn_gas_surf = surf_rate @ surf_nu_gas
                # Exothermic forward by hundreds of kJ, so a running roast heats
                # its own bed -- which is why a real roaster is autothermal.
                q_surf = -float(surf_rate @ surf.dH)
            else:
                dn_solid_surf = 0.0
                dn_gas_surf = 0.0
                q_surf = 0.0
                surf_rate = None

            # --- liquid <-> liquid --------------------------------------
            # Equality of ACTIVITY is the equilibrium, exactly as it is for the
            # vapour, so the driving force is the same subtraction. Two
            # properties of this form are worth stating because they are what
            # make it safe rather than merely plausible:
            #
            #   * it is ANTISYMMETRIC -- what leaves one layer enters the other,
            #     so conservation survives untouched;
            #   * it is SELF-LIMITING at zero. A species absent from layer 2 has
            #     a2 = 0, so the flux can only be INTO layer 2; a species absent
            #     from layer 1 likewise. Neither layer can be driven negative,
            #     which is the same property the evaporation term has.
            #
            # ``k_lle`` is agitation, not a numerical constant -- see
            # ``VesselConditions``. And the product of both wet factors is what
            # makes this vanish identically when there is only one layer.
            lle = cond.k_lle * gate1 * gate2 * (a1 - a2)   # + = layer 1 -> layer 2
            # ... plus the reabsorption of anything below the phase scale, which
            # is both the continuous form of the merge and what gives an empty
            # layer's Jacobian column a real diagonal. See LAYER_REABSORB.
            lle = lle - LAYER_REABSORB * drain2 * nL2

            # Layer 2's reaction term, gated on the same smoothstep so that a
            # differencing perturbation cannot light up a whole phase.
            dn_rxn2 = dn_rxn2 * gate2
            q_rxn += q_rxn2 * gate2

            # --- exchange with the room, in BOTH directions --------------
            # The room is just another headspace: a far end held at fixed
            # pressure and fixed composition. So this is the same law as a
            # vapour edge between two vessels, and the flow follows the
            # pressure difference either way.
            #
            # It used to vent outward only, which is wrong in a way that only
            # shows up once vessels are coupled: boiling sweeps the air out
            # through the condenser, and with no path back the whole rig settles
            # below atmospheric and "boiling point" stops meaning anything. A
            # flask open to the room cannot hold a vacuum.
            #
            # The donor composition is blended with a tanh rather than switched
            # on the sign of dP -- a hard switch is a discontinuity BDF cannot
            # step across, the same lesson as DRYOUT_MOLES and MELT_BLEND.
            # Bulk flow, driven by the total pressure difference and carrying
            # the composition of whichever side it left -- i.e. exactly the
            # vapour edge of a rig, with the room as a fixed far end.
            #
            # It used to flow OUTWARD only, which is wrong in a way that only
            # surfaces once vessels are coupled: boiling sweeps the air out
            # through the condenser, and with no path back the whole rig settles
            # at the cold end's vapour pressure -- 0.05 bar for a reflux -- where
            # "boiling point" stops meaning anything. A flask open to the room
            # cannot hold a vacuum.
            #
            # ``x_ambient`` is zero unless Layer 5 could account for essentially
            # all of the room's atmosphere (see ``Vessel``), so a network that
            # does not carry N2 keeps the old outward-only behaviour rather than
            # inhaling pure oxygen to make the pressure up.
            #
            # ⚠ THE DONOR SWITCH IS WRITTEN AS AN INFLOW-ONLY CORRECTION, not as
            # a blend of the two compositions, and the difference is a real
            # conservation bug this project shipped for several sessions: a
            # blended composition makes half of a small OUTflow leave carrying
            # the ROOM's composition, so an open flask exported nitrogen it did
            # not have until its gas block was ~100x negative. ``backflow_part``
            # is where that is argued, and it is what keeps every outward term
            # proportional to the vessel's own ``nG``. The leading ``dP`` still
            # makes this exactly zero at the crossing, so no residual flux leaks
            # through a vessel at rest, and it still sums to ``k_vent dP`` --
            # exactly, at any dP -- so the boiling plateau is untouched.
            P_total = float(p.sum())
            nG_total = nG.sum()
            dP_vent = P_total - cond.P_ambient
            x_out = nG / nG_total if nG_total > 0.0 else np.zeros(n)
            entering = backflow_part(dP_vent, DP_VENT_SMOOTH)
            vent = cond.k_vent * (
                dP_vent * x_out + entering * (cond.x_ambient - x_out)
            )                                            # + = leaving
            # Gas leaving at T costs no temperature change -- the shrinking heat
            # capacity accounts for it. Gas arriving from the room does: it
            # comes in at T_env and drags the vessel toward it.
            q_vent = -float(np.minimum(vent, 0.0) @ _poly(ph.Cp_gas, T)) * (
                cond.T_env - T
            )

            # --- energy -------------------------------------------------
            Cp_l = _poly(ph.Cp_liq, T)
            Cp_total = cond.heat_capacity + float(
                (nL1 + nL2 + nS) @ Cp_l + nG @ _poly(ph.Cp_gas, T)
            )
            q_loss = -cond.UA * (T - cond.T_env)
            # ⚠ Crossing between layers is ATHERMAL here. This project models no
            # excess enthalpy of mixing anywhere -- the energy balance is a sum
            # of pure-component heat capacities -- so charging a heat of mixing
            # to this one transfer would be the only place it existed, and would
            # disagree with the enthalpy every other transfer carries.
            dT = (
                q_rxn + q_vap + q_fus + q_solid + q_surf + q_loss + q_vent
                + cond.Q_input
            ) / max(Cp_total, CP_MIN)

            if probe is not None:
                probe.clear()
                probe.update(
                    T=T, Cp_total=Cp_total, dT=dT,
                    q_rxn=q_rxn, q_vap=q_vap, q_fus=q_fus, q_loss=q_loss,
                    q_vent=q_vent, Q_input=cond.Q_input, q_solid=q_solid,
                    q_surface=q_surf,
                    q_sum=q_rxn + q_vap + q_fus + q_solid + q_surf + q_loss
                    + q_vent + cond.Q_input,
                    evap=evap, solute=solute, vent=vent,
                    precipitate=precipitate if np.ndim(precipitate) else
                    np.zeros(n),
                    dn_rxn1=dn_rxn1, dn_rxn2=dn_rxn2, dn_gas_rxn=dn_gas_rxn,
                    lle=lle,
                    solid_flux=(
                        np.zeros(0) if s_flux is None else s_flux
                    ),
                    dn_solid_rxn=(
                        np.zeros(n) if s_flux is None else dn_solid_rxn
                    ),
                    surface_rate=(
                        np.zeros(0) if surf_rate is None else surf_rate
                    ),
                    dn_solid_surf=(
                        np.zeros(n) if surf_rate is None else dn_solid_surf
                    ),
                    dn_gas_surf=(
                        np.zeros(n) if surf_rate is None else dn_gas_surf
                    ),
                    q_rxn_terms=np.concatenate(sink) if sink else np.zeros(0),
                )

            return np.concatenate([
                dn_rxn1 - evap1 - evap_dry + solute1 - lle - precipitate,
                dn_rxn2 - evap2 + solute2 + lle,              # liquid layer 2
                dn_gas_rxn + dn_gas_srxn + dn_gas_surf + evap - vent
                + ingress,                                    # vapour
                -solute + precipitate + dn_solid_rxn + dn_solid_surf,  # solid
                [dT],
            ])

        return rhs

    # -- driving -------------------------------------------------------------

    # -- refusing cleanly, which is not the same as not crashing --------------

    def condensed_volume(self, y: np.ndarray) -> float:
        """L of liquid + solid in this state. Solids take the liquid molar volume."""
        n = self.n
        T = min(max(float(y[-1]), T_MIN), T_MAX)
        v_mol = np.maximum(_poly(self.ph.v_liq, T), 0.0)
        condensed = (
            np.maximum(y[:n], 0.0)
            + np.maximum(y[n : 2 * n], 0.0)
            + np.maximum(y[3 * n : 4 * n], 0.0)
        )
        return float(condensed @ v_mol)

    def check_capacity(self, y: np.ndarray) -> None:
        """Refuse a state whose condensed phases do not fit in the vessel. Raises.

        ⚠ EXACTLY FULL IS LEGITIMATE AND OVER-FULL IS NOT A STATE, and that
        boundary is the whole decision here. A flask brim-full of ice is somewhere
        a player arrives on purpose -- freeze 30 mol of water in a 1 L flask and
        0.54 L of it is solid, with a real headspace above. A flask holding MORE
        condensed matter than it has room for is not a flask under any pressure;
        it is an arithmetic result nobody can be shown.

        Without this the RHS clamps the gas volume to ``V_GAS_MIN`` and carries on,
        and every pressure downstream is that clamp: ``Vessel.pressure`` returned
        ``inf``, which is a wrong number wearing a confident face. Two rows of
        ``validation/robustness.py`` were exactly this and both are now refusals.

        ⚠ AND THE TWO ROWS DO NOT HAVE THE SAME CAUSE, which is why the message
        names the overflow rather than guessing at it. One is a player charging
        360 mL into a 100 mL flask -- unambiguous, and caught before it is ever
        integrated. The other is a vessel cooled to 100 K, where the brief expected
        a flask packed full of ice and the measurement says otherwise: the water
        freezes cleanly when the flask is SEALED, and it is the OPEN one that
        fails, because Henry's law extrapolated 170 K below its fitted window makes
        water a bottomless sink for nitrogen. It inhales 3382 mol of air from a
        room it is connected to and reports 116 L of liquid in a 1 L flask. The
        overflow is the symptom that can be checked cheaply and exactly; the
        extrapolation is the cause, and ``diagnose`` says so.

        The slack is RELATIVE and generous -- see ``CAPACITY_SLACK``. A vessel's
        volume here is NOMINAL, and "one litre of 1 M acetic acid" genuinely comes
        to 1.006 L of condensed phase.
        """
        V = float(self.cond.volume)
        V_C = self.condensed_volume(y)
        if V_C <= V * (1.0 + CAPACITY_SLACK):
            return
        raise ValueError(
            f"the condensed phases occupy {V_C:.4g} L in a vessel of {V:.4g} L -- "
            f"{V_C - V:.4g} L more than it holds, so there is no headspace for a "
            f"pressure to be defined in and every pressure downstream would be the "
            f"gas-volume floor rather than physics. Either less was meant to go in "
            f"(a 1 L flask holds ~55 mol of water and no more), or something has "
            f"dissolved without limit -- a gas whose Henry constant is being "
            f"evaluated far below the window it was fitted over will do that, and "
            f"an open vessel then draws the room in to feed it"
        )

    def check_state(self, y: np.ndarray) -> None:
        """Refuse a state the RHS cannot honestly be evaluated at. Raises.

        A player will reach every one of these. The rule is that a reachable state
        must either work or be refused WITH A REASON AND A FIX -- never a crash
        several layers down, and never a plausible-looking number.
        """
        y = np.asarray(y, dtype=float)
        if not np.all(np.isfinite(y)):
            bad = int(np.count_nonzero(~np.isfinite(y)))
            raise ValueError(
                f"{bad} of {y.size} state entries are not finite, so the vessel "
                "cannot be integrated from here. A non-finite state does not "
                "arise from chemistry -- look for a NaN charged into a vessel or "
                "a previous solve whose failure was swallowed"
            )
        T = float(y[-1])
        if not T_MIN <= T <= T_MAX:
            raise ValueError(
                f"temperature {T:.4g} K is outside the range this vessel's "
                f"correlations are evaluated over ({T_MIN:g}-{T_MAX:g} K). Every "
                "property here is a polynomial or an Antoine fit, and both return "
                "confident nonsense far outside their window"
            )
        self.check_capacity(y)

    def fragilities(self, y: np.ndarray) -> list[str]:
        """Latent numerical fragilities of this configuration -- warnings, not errors.

        ⚠ THE DISTINCTION FROM ``check_state`` IS THE WHOLE POINT, and getting it
        the wrong way round was a real temptation. A state that this project cannot
        evaluate has to be REFUSED; a configuration that merely sits near a known
        cliff has to be REPORTED, because refusing it would break the sixty-odd
        working setups in this repo that sit there quite happily.

        The sealed flask is the case that settled it. ``kla = 0`` with an empty
        headspace leaves the gas block identically zero AND its Jacobian columns
        identically flat, and a flat column is as bad as an enormous one:
        ``num_jac`` finds every difference in it below its "too small" threshold
        and multiplies that column's perturbation factor by ten on EVERY Jacobian
        until it overflows to inf and BDF gets a NaN Jacobian. Same pathology as a
        vessel at rest and as an empty second liquid layer, by a third route.

        But it is PER-SOLVE: each ``run`` builds a fresh BDF and the factor resets,
        so it takes a few hundred Jacobians in ONE call to overflow. A separatory
        funnel with ``kla = 0`` and no headspace is the commonest setup in this
        repo and never gets near that. So the honest report is "this is fragile
        under a long single run, and here is the fix", not a refusal -- and the
        fix, if a run does fail, is a nitrogen blanket rather than an absent
        atmosphere, which is also the more honest experiment.

        ⚠ THE OVERFLOW ITSELF IS NOW BOUNDED -- ``numerics/jacobian.py`` supplies
        the ceiling scipy does not have, so the factor stops at the state's own
        extent instead of at ``inf``. This entry is KEPT rather than deleted,
        deliberately and against the DRYOUT precedent below, because the
        CONFIGURATION is still the one that produces flat columns, and the bound
        was measured on the trigger that FIRED (liquid layer 2, at a tight
        tolerance) rather than on this one, which has never been made to fire at
        all. Reporting a configuration whose failure mode is bounded is a smaller
        error than dropping the report on the strength of a case nobody could
        reproduce.

        ⚠ AND EVERY ENTRY HERE IS ONCE AGAIN GENUINELY LATENT, which was not true
        for as long as the DRYOUT BAND was on this list. That one was a measured
        wrong answer rather than a nearby cliff, and it had to sit here rather
        than on ``diagnose`` precisely because the solve SUCCEEDED -- diagnose
        runs only on failure and would never have been consulted. It was removed
        together with the test that asserted it when the band was closed; see
        ``_dryout_gates``. If a live wrong answer ever has to be announced here
        again, say so as loudly as that one did, because it breaks this
        docstring's promise while it is here.
        """
        y = np.asarray(y, dtype=float)
        n = self.n
        nG = y[2 * n : 3 * n]
        liquid = float(
            np.maximum(y[:n], 0.0).sum() + np.maximum(y[n : 2 * n], 0.0).sum()
        )
        out: list[str] = []
        if self.cond.kla == 0.0 and float(nG.sum()) <= 0.0 and liquid > DRYOUT_MOLES:
            out.append(
                "kla=0 with an EMPTY HEADSPACE leaves the gas block identically "
                "zero and flat, which BDF's num_jac cannot difference: it inflates "
                "that column's perturbation tenfold per Jacobian until it "
                "overflows. Harmless in a short step and fatal in a long single "
                "run. If a solve fails here, 'sealed' should be a nitrogen "
                "blanket -- fill_headspace({'N#N': 1.0}) with kla left alone -- "
                "rather than an absent vapour phase"
            )
        N2_layer = float(np.maximum(y[n : 2 * n], 0.0).sum())
        if 0.0 < N2_layer <= LAYER_EPS * 10.0:
            out.append(
                f"the second liquid layer holds {N2_layer:.3e} mol, within a "
                f"decade of the {LAYER_EPS:g} mol scale at which it stops counting "
                f"as a layer -- the band where the growth and drain gates meet"
            )
        if self.cond.k_lle >= 5.0 and N2_layer > 0.0:
            out.append(
                f"two layers at k_lle={self.cond.k_lle:g} mol/s. The default is "
                f"fast enough that a 30 mL layer equilibrates in 40 ms, which is a "
                f"stiffer mode than most chemistry beside it; the prep's pot needs "
                f"0.5 to integrate at all, and the answer is insensitive to the "
                f"choice over a decade"
            )
        return out

    def check_raw_solution(self, y_raw: np.ndarray) -> None:
        """Refuse a solve whose RAW output is not a perturbation of a real state.

        ⚠ ``sol.success`` IS NECESSARY AND NOT SUFFICIENT, and this is the check
        that says so. Called on the solver's own final point BEFORE
        ``project_non_negative`` sees it, because the projection's whole job is to
        settle a cancelling pair -- so by the time anything downstream looks, a
        catastrophic dipole has become a plausible state. See ``EXCURSION_FLOOR``
        for the case that proved it.
        """
        y_raw = np.asarray(y_raw, dtype=float)
        if not np.all(np.isfinite(y_raw)):
            raise RuntimeError(
                "the solver reported success but returned a non-finite state; "
                "this is a failed integration wearing a success flag"
            )
        n = self.n
        blocks = [y_raw[:n], y_raw[n : 2 * n], y_raw[2 * n : 3 * n], y_raw[3 * n : 4 * n]]
        # ⚠ THE SIGNED TOTAL, not the sum of magnitudes. A cancelling dipole sums to
        # nothing, so summing |value| per phase would hand it a bound twice its own
        # size and the check would pass on exactly the case it exists for. What the
        # bound has to mean is "the amount of this species that EXISTS".
        totals = np.maximum(sum(blocks), 0.0)
        bound = EXCURSION_RATIO * np.maximum(totals, EXCURSION_FLOOR)
        worst = np.minimum.reduce([b for b in blocks])
        bad = np.flatnonzero(worst < -bound)
        if bad.size:
            i = int(bad[np.argmin(worst[bad])])
            raise RuntimeError(
                f"the solver reported success but species {i} reached "
                f"{worst[i]:.3e} mol in one phase against {totals[i]:.3e} mol "
                f"present in all of them -- more than {EXCURSION_RATIO:.0g} times "
                f"over, which is not a perturbation of any physical state. The "
                f"non-negative projection would have tidied this into a "
                f"plausible-looking answer, which is why it is checked on the RAW "
                f"solution. Suspect a term whose activity coefficient or rate "
                f"constant is orders of magnitude larger than the material it acts "
                f"on"
            )
        # ⚠ ON THE WAY OUT AS WELL AS THE WAY IN. An overfill is usually charged,
        # but it can also GROW during a solve -- a vessel cooled far enough
        # dissolves the room without limit -- and a state checked only on entry
        # would return that as a finished answer with an infinite pressure on it.
        self.check_capacity(y_raw)

    def run(self, y0, t_span, rtol: float = 1e-6, atol: float = 1e-9, **kw):
        # The phase decision is taken HERE, on the way in, rather than on the way
        # out. A flask charged with two immiscible liquids has to be two layers
        # for the whole of the integration that follows, not from the end of it;
        # and the merge cases are equally about the state the solver is handed.
        # ⚠ It is therefore an EVENT-BOUNDARY test, with the consequence that a
        # mixture which only becomes unstable part-way through one long ``run``
        # will not split until the next call. That is the METER edge's bargain
        # again -- the alternative is a discrete decision inside the RHS, which
        # BDF cannot step across.
        y0 = np.asarray(y0, dtype=float)
        # BEFORE the stability test, which evaluates activity coefficients and
        # would be the thing that actually broke on a non-finite state.
        self.check_state(y0)
        y0 = self.split_phases(y0)
        # ⚠ AFTER ``split_phases``, and it has to be: a layer seeded a line above
        # would otherwise be frozen at the composition it had before it existed.
        rhs = self.make_rhs(y0 if FREEZE_LAYER_PERMITTIVITY else None)
        t0, t1 = float(t_span[0]), float(t_span[1])

        # A vessel at rest gets no solver at all. This is not an optimization
        # dodge, it is a correctness fix: the RHS is autonomous (every flux is an
        # algebraic function of the state), so if the derivative is zero then the
        # constant trajectory is the exact solution. BDF cannot discover that on
        # its own -- with a uniformly vanishing derivative every finite difference
        # it tries comes back under its "difference too small" threshold, so it
        # keeps inflating the perturbation, overflows it to infinity, and then
        # rejects every step forever. A flask that has been poured out and is
        # sitting in equilibrium with its own headspace is exactly that state, and
        # an idle vessel is the common case in a game, not a corner case.
        #
        # The test is the solver's own local-error criterion: if a whole step
        # cannot move any component by more than its tolerance, there is nothing
        # for the integrator to resolve.
        dy = rhs(t0, y0)
        span = abs(t1 - t0)
        if np.all(np.abs(dy) * span <= atol + rtol * np.abs(y0)):
            return _Stationary(
                t=np.array([t0, t1]), y=np.column_stack([y0, y0])
            )

        # ⚠ THE JACOBIAN IS DIFFERENCED WITH A CEILING ON THE PERTURBATION
        # FACTOR, which BDF's own path does not have. The short-circuit above is
        # one instance of that missing bound; ``BoundedJacobian`` is the bound
        # itself, and it is what lets the sulfur burner be run at rtol 1e-8 at
        # all. It is bit-for-bit the default path until the clamp binds.
        if "jac" not in kw:
            kw["jac"] = BoundedJacobian(rhs, atol, kw.pop("jac_sparsity", None))
        return solve_ivp(
            rhs, t_span, y0, method="BDF", rtol=rtol, atol=atol, **kw,
        )

    def project(self, y: np.ndarray) -> np.ndarray:
        """Return ``y`` with every amount non-negative and every total unchanged.

        See ``project_non_negative``. Anything it could not settle is accumulated
        on ``self.created`` so Layer 5 can report it instead of it vanishing.
        """
        n = self.n
        out = np.array(y, dtype=float, copy=True)
        blocks, created = project_non_negative(
            [out[:n], out[n : 2 * n], out[2 * n : 3 * n], out[3 * n : 4 * n]]
        )
        out[: 4 * n] = np.concatenate(blocks)
        self.created += created
        return out

    # -- the energy balance, which nothing used to audit ---------------------

    def energy_terms(
        self, y: np.ndarray, boundary: np.ndarray | None = None
    ) -> dict:
        """Every watt the temperature equation sees at state ``y``, term by term.

        The mass balance can be audited against a conserved total; ``dT/dt``
        cannot, because it is a SUM and not a difference of two tallies. M12 is
        what that costs: an insulated flask destroyed 495 J while conserving
        every atom to 1e-12, and no report in the project could see it. This is
        the instrument. It evaluates the RHS once, with the probe attached, and
        hands back the terms rather than the derivative.

        ⚠ It is a snapshot of one state, not an accumulated balance -- a term
        that is small here may still be the one that integrates to a kilojoule,
        because the temperature equation has no restoring force to correct it.
        Read it alongside ``Vessel.energy_report``.

        ⚠⚠ ``boundary`` IS NOT OPTIONAL WHEN READING A TRAJECTORY, and getting it
        wrong is not a small error. The RHS a ``run`` used froze each layer's
        permittivity at the state it STARTED from (``FREEZE_LAYER_PERMITTIVITY``),
        and ``q_rxn`` for a fast reversible pair is a difference of two terms of
        order 5e9 W. Re-freezing at ``y`` instead perturbs the Bronsted-Bjerrum
        factor in the fifth digit, which is 1e5 W of a cancellation that nets a
        fraction of a watt: measured on M12's flask at t = 1183 s, the SAME state
        reads q_rxn = -4.69e6 W frozen at itself and -5e-3 W frozen at the run's
        own boundary. Pass the state the run began with, or read a number that is
        pure artefact.
        """
        y = np.asarray(y, dtype=float)
        if boundary is None:
            boundary = y
        probe: dict = {}
        rhs = self.make_rhs(
            np.asarray(boundary, dtype=float)
            if FREEZE_LAYER_PERMITTIVITY else None,
            probe=probe,
        )
        rhs(0.0, y)
        return dict(probe)

    # -- the one decision that cannot be a rate ------------------------------

    def stability_of(self, n_liquid: np.ndarray, T: float) -> StabilityResult:
        """Would a single liquid of this composition rather be two? See ``lle``.

        Public because it is also a READOUT. A vessel built with ``lle=False``
        never calls ``split_phases``, and a liquid that wanted to split would
        then be silently held as one phase -- which is exactly the class of
        quiet wrong answer this project forbids. Layer 5 calls this on demand to
        say so.
        """
        result = stability_test(
            n_liquid, self.ph.nu, self.ph.R_k, self.ph.Q_k, self.ph.a_mn,
            self.ph.gamma_active, T, self.ph.reference_correction(T),
            a_sat=self.saturation_activity(T),
            born=self.ph.born_block(T),
        )
        self.last_stability = result
        return result

    def _permittivity_coverage(
        self, n_liquid: np.ndarray, v_mol: np.ndarray
    ) -> float:
        """Fraction of this liquid's VOLUME whose relative permittivity is known.

        Volume rather than moles, because that is the weighting the mixing rule
        uses: a species excluded from Oster's rule is excluded in proportion to
        the volume it occupies, so this measures exactly how much of a layer's
        polarity is being inferred from the rest of it.
        """
        amounts = np.maximum(n_liquid, 0.0)
        volume = amounts * v_mol
        total = float(volume.sum())
        if total <= 0.0:
            return 1.0
        known = (self.ph.eps_coeffs != 0.0).any(axis=1)
        return float(volume[known].sum()) / total

    def merge_phases(self, y: np.ndarray) -> np.ndarray:
        """Collapse two liquid layers back into one when they are no longer two.

        The cheap half of the phase decision, and it runs on the way OUT of an
        integration where ``split_phases`` runs on the way in. The asymmetry is
        deliberate: deciding to SPLIT costs a tangent-plane iteration and is
        worth doing once per call, while deciding to MERGE is a comparison of
        two compositions and is worth doing as soon as it is true. Without it,
        a system made miscible part-way through a run would carry a phantom
        second layer until the next call -- and a separatory funnel would drain
        it.
        """
        n = self.n
        out = np.array(y, dtype=float, copy=True)
        nL1, nL2 = out[:n], out[n : 2 * n]
        N1, N2 = float(nL1.sum()), float(nL2.sum())
        if N2 <= 0.0:
            return out
        same = N1 <= 0.0 or float(
            np.abs(nL1 / max(N1, 1e-300) - nL2 / N2).sum()
        ) < TRIVIAL_DISTANCE
        # ⚠ The floor is LAYER_EPS, not DRYOUT_MOLES, and they must be the same
        # constant that the gate uses. A layer between the two survived the
        # merge AND sat inside the smoothstep's transition band -- the single
        # worst place for it -- and a solver excursion of 1e-5 mol was enough to
        # put it there. It then made the acidification unsolvable.
        if same or merge_threshold_reached(N2, N1 + N2, LAYER_EPS):
            nL1 += nL2
            nL2[:] = 0.0
        return out

    def split_phases(self, y: np.ndarray) -> np.ndarray:
        """Decide whether the liquid is one layer or two. Boundaries only.

        The RHS drives two layers toward equal activity, but it can never
        CREATE the second one: a single phase is a fixed point of its own
        splitting dynamics, and leaving that fixed point is a global question
        about the Gibbs surface rather than a local rate. So the test lives
        here, at an event boundary, and all this does is nudge the state off the
        trivial solution and let the ODE find the tie line -- see ``lle.py``.

        Three outcomes, and the two housekeeping ones matter as much as the
        interesting one:

        * one layer, and unstable -> seed a second with a little material at the
          composition that proved the instability;
        * two layers whose compositions have converged on each other -> they are
          one liquid wearing two labels, so MERGE them. Without this, adding
          enough co-solvent to make a system miscible would leave a phantom
          second layer that a separatory funnel would happily drain;
        * two layers, one of which has been emptied -> merge, so a phase that
          was extracted away does not linger as a rounding error.
        """
        self.just_seeded = False
        if not self.cond.lle:
            return y
        n = self.n
        out = np.array(y, dtype=float, copy=True)
        nL1, nL2 = out[:n], out[n : 2 * n]
        T = min(max(float(out[-1]), T_MIN), T_MAX)
        N1, N2 = float(nL1.sum()), float(nL2.sum())

        if N2 > 0.0:
            return self.merge_phases(out)

        if N1 <= DRYOUT_MOLES:
            return out
        result = self.stability_of(nL1, T)
        if not result.unstable:
            return out

        # ⚠ AN ELECTROLYTE USED TO BE REFUSED HERE OUTRIGHT. It is not any more,
        # and the difference is one term: ions had no activity model, so equality
        # of activity with gamma = 1 on both sides put an ion at EQUAL MOLE
        # FRACTION in water and in toluene, and splitting a brine invented a
        # strongly ionic organic phase with aqueous-anchored dissociation running
        # inside it. The Born transfer term prices that charge transfer now (see
        # ``properties/dielectric.py`` and ``PhaseArrays.born_block``), so a trial
        # phase made of hydrocarbon converges with its ions expelled from it.
        #
        # What survives is two NARROW refusals, because the replacement is only as
        # good as its two inputs -- a charge and a medium:
        #
        #   * an ion whose Born coefficient could not be resolved has no transfer
        #     energy, so it would move freely. That is the old failure, per
        #     species;
        #   * a proposed layer whose PERMITTIVITY is largely unknown has no
        #     polarity, so the ions in it get no Born term either -- the same
        #     failure, per phase. Checked on the TRIAL composition and not only on
        #     the feed: the trial is what says what the second layer would be made
        #     of, and a feed that is 95% water can still propose a layer that is
        #     100% unpriced.
        #
        # Both are reported by ``Vessel.lle_report`` and neither fires for
        # ordinary chemistry. This is a REPLACEMENT of one honest answer with a
        # better one, not permission to start guessing.
        ionic_fraction = float(nL1[self.ph.ionic].sum()) / N1
        if ionic_fraction > IONIC_SPLIT_LIMIT:
            unpriced = self.ph.ionic & (self.ph.born_A <= 0.0)
            if float(nL1[unpriced].sum()) / N1 > BORN_TRACE:
                self.refused_split = ionic_fraction
                self.refused_reason = "unpriced-ion"
                return out
            v_mol = np.maximum(_poly(self.ph.v_liq, T), 0.0)
            feed_cover = self._permittivity_coverage(nL1, v_mol)
            trial_cover = self._permittivity_coverage(result.composition, v_mol)
            if min(feed_cover, trial_cover) < BORN_COVERAGE_MIN:
                self.refused_split = ionic_fraction
                self.refused_reason = "unpriced-medium"
                self.refused_coverage = min(feed_cover, trial_cover)
                return out
        self.refused_split = 0.0
        self.refused_reason = ""
        # Seed, capped at what is actually present: the trial composition is a
        # direction, not an amount, and taking more of a species than the layer
        # holds would be creating matter to prove a point.
        take = np.minimum(SPLIT_SEED_FRACTION * N1 * result.composition, nL1)
        nL1 -= take
        nL2 += take
        self.just_seeded = True
        return out

    def diagnose(self, y: np.ndarray) -> list[str]:
        """Plausible causes for a failed solve from state ``y``, most likely first.

        A crash with no diagnosis is not a clean refusal. Every entry below is a
        state this project has actually failed on, so this is a record of what has
        gone wrong rather than a guess at what might. It never changes behaviour --
        it only turns "integration failed" into something a player can act on.
        """
        y = np.asarray(y, dtype=float)
        n = self.n
        nL1, nL2 = np.maximum(y[:n], 0.0), np.maximum(y[n : 2 * n], 0.0)
        nG, nS = np.maximum(y[2 * n : 3 * n], 0.0), np.maximum(y[3 * n : 4 * n], 0.0)
        N1, N2 = float(nL1.sum()), float(nL2.sum())
        T = float(y[-1])
        why: list[str] = []

        if N2 > 0.0 and self.cond.k_lle >= 1.0:
            why.append(
                f"this vessel holds TWO liquid layers and k_lle is "
                f"{self.cond.k_lle:g} mol/s. That is the most common cause of an "
                f"unsolvable two-phase flask: at the default of 5.0 a 30 mL layer "
                f"empties in 40 ms, which is a stiffer mode than the chemistry "
                f"beside it. Try SET_SHAKING at 0.5 -- and note the answer is "
                f"usually insensitive to it, so this is a numerical choice rather "
                f"than a physical one"
            )
        if N2 > 0.0 and merge_threshold_reached(N2, N1 + N2, LAYER_EPS * 10.0):
            why.append(
                f"the second liquid layer holds only {N2:.3e} mol, which is close "
                f"to the {LAYER_EPS:g} mol scale at which it stops being a layer. "
                f"A layer sitting inside that transition band is the worst place "
                f"for it -- the growth and drain gates meet there"
            )
        if DRYOUT_MOLES / 10.0 < N1 + N2 < DRYOUT_MOLES * 10.0:
            why.append(
                f"the flask holds {N1 + N2:.3e} mol of liquid, which is within a "
                f"decade of the {DRYOUT_MOLES:g} mol scale at which Raoult hands "
                f"over to the dry-flask law. Both halves of ``_dryout_gates`` are "
                f"partial there, and the liquid block is being driven by a "
                f"full-strength ``psat`` against a pool small enough that its own "
                f"emptying timescale is microseconds -- stiff, though no longer "
                f"wrong. ⚠ THIS USED TO BE A MEASURED WRONG ANSWER and is not one "
                f"any more: the gates were a ramp and its complement with the mole "
                f"fractions floored on the SAME scale, so inside the band they "
                f"summed to 0.57, every activity was understated, and a sulfur "
                f"burner at 690 K created 11% of its oxygen. It now closes to "
                f"1.9e-11 with nothing driven to zero beside it. If a solve still "
                f"fails here, move the temperature so the condensate is clearly "
                f"present or clearly gone rather than holding a vessel exactly at "
                f"its own boiling point with only a trace condensing"
            )
        if N1 + N2 <= DRYOUT_MOLES and T > 400.0:
            why.append(
                f"the flask is DRY ({N1 + N2:.3e} mol of liquid) and at {T:.0f} K, "
                f"so its only thermal mass is the glassware and its vapour "
                f"pressures are far off the end of their Antoine fits. A dry "
                f"superheated flask is a known-fragile state: stop a temperature "
                f"sweep at the boiling PLATEAU rather than driving through it"
            )
        if self.cond.kla == 0.0 and float(nG.sum()) <= 0.0:
            why.append(
                "kla=0 with an empty headspace leaves the gas block flat -- see "
                "check_state; 'sealed' has to be an inert atmosphere"
            )
        if self.ph.has_ions and N1 > 0.0:
            ionic = float(nL1[self.ph.ionic].sum()) / N1
            if ionic > 0.1:
                why.append(
                    f"layer 1 is {100 * ionic:.0f}% ions by mole fraction, which "
                    f"is far outside anything the Born term was checked over "
                    f"(there is no ionic-strength model here at all)"
                )
        if float(nS.sum()) > 0.0 and N1 + N2 <= DRYOUT_MOLES:
            why.append(
                f"there is {float(nS.sum()):.3e} mol of solid and no solvent to "
                f"dissolve it into, so the only route out of the solid block is "
                f"melting"
            )
        if not why:
            why.append(
                "no known-fragile state recognised. Re-run this step with "
                "FREEZE_LAYER_PERMITTIVITY off and with lle=False to bisect it, "
                "and check the RAW solver output rather than the projected state"
            )
        return why

    def _fail(self, y: np.ndarray, message: str) -> RuntimeError:
        bullet = "\n  - "
        return RuntimeError(message + bullet + bullet.join(self.diagnose(y)))

    def step(self, y: np.ndarray, dt: float, **kw) -> np.ndarray:
        """Advance the vessel by dt -- the call the Layer 6 stepper makes."""
        sol = self.run(y, (0.0, dt), **kw)
        if not sol.success:
            raise self._fail(y, f"vessel integration failed: {sol.message}")
        # ⚠ RAW FIRST, PROJECTED SECOND. The projection cancels a dipole, so it has
        # to be checked before it gets the chance -- see ``check_raw_solution``.
        self.check_raw_solution(sol.y[:, -1])
        return self.merge_phases(self.project(sol.y[:, -1]))

    def step_until(
        self,
        y: np.ndarray,
        dt: float,
        roots: list,
        **kw,
    ) -> RootStop:
        """Advance by at most ``dt``, stopping the instant a root is crossed.

        ``roots`` is a list of plain functions ``f(t, y) -> float`` over the state
        vector -- still numpy in, float out, so this stays the Rust seam. **The
        sign convention is uniform and is the whole contract: f < 0 means "not
        yet" and f >= 0 means "satisfied".** Every condition Layer 5 offers is
        written to that convention, so there is no direction flag to get backwards
        and "is it already true" is one comparison rather than a case analysis.

        Returns a ``RootStop``: the state reached, how long that ACTUALLY took,
        and which root stopped it (``None`` if the span simply expired).

        Three cases the naive version of this gets wrong, all of them handled here
        rather than by the caller:

        * **ALREADY TRUE.** scipy locates sign CHANGES, so a condition satisfied
          at t0 is not a root and the solve would run the whole span and report
          nothing. Checked before integrating, and reported as an event at zero
          elapsed time -- which is the truthful answer to "wait until it is above
          300 K" asked of a flask already at 340.
        * **A VESSEL AT REST.** The stationary short-circuit means no solver runs
          at all, and it is exactly right here: the RHS is autonomous, so a
          constant trajectory can never cross a root it is not already on. The
          span expires and nothing fires.
        * **A FAILED SOLVE.** ``sol.success`` is checked, because a terminal event
          and a failure both cut the span short and ``sol.y[:, -1]`` looks
          perfectly plausible either way. That distinction is the whole reason
          ``Vessel.run`` was made to raise.
        """
        y0 = np.asarray(y, dtype=float)
        for i, f in enumerate(roots):
            if float(f(0.0, y0)) >= 0.0:
                return RootStop(y=y0.copy(), elapsed=0.0, fired=i, already=True)

        events = []
        for f in roots:
            def event(t, yy, _f=f):
                return float(_f(t, yy))
            event.terminal = True
            # Upward only: the convention above makes "satisfied" the positive
            # side, so a downward crossing is a condition ceasing to hold, which
            # is not what was asked for.
            event.direction = 1.0
            events.append(event)

        sol = self.run(y0, (0.0, dt), events=events, **kw)
        if not sol.success:
            raise self._fail(
                y0,
                f"vessel integration failed after {float(sol.t[-1]):.4g} s of "
                f"{dt:.4g} s while waiting for a condition: {sol.message}",
            )
        self.check_raw_solution(sol.y[:, -1])
        fired = None
        for i, times in enumerate(getattr(sol, "t_events", None) or []):
            if times is not None and len(times):
                fired = i
                break
        elapsed = float(sol.t[-1]) if fired is not None else float(dt)
        return RootStop(
            y=self.merge_phases(self.project(sol.y[:, -1])),
            elapsed=elapsed,
            fired=fired,
            already=False,
        )

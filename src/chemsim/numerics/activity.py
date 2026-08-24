"""Layer 4 -- activity coefficients: the one model that would not collapse.

Every other property in this project is a function of temperature alone, so it
gets evaluated once at setup and handed down as polynomial coefficients; the
kernel has never heard of Antoine, Rackett or Lee-Kesler. An activity
coefficient cannot be treated that way, because it depends on COMPOSITION, and
composition is the state vector. Fitting it in advance would mean fitting a
function of the solution.

So the setup/hot-loop split moves instead of vanishing. What is precomputed is
the parameter block -- the group-count matrix ``nu``, the size and surface
parameters ``R_k``/``Q_k``, and the interaction matrix ``a_mn``, already expanded
from main groups to subgroups upstream. What runs here, per RHS call, is the
evaluation itself. The contract is unchanged: numpy in, numpy out, no domain
types, still the Rust/PyO3 seam. The arrays are simply bigger and the loop does
real work for the first time.

The functional form is UNIFAC (Fredenslund 1975): an entropic *combinatorial*
part from molecular size and shape, plus an enthalpic *residual* part from
group-group interactions.

    ln gamma_i = ln gamma_i(combinatorial) + ln gamma_i(residual)

Two implementation notes that are not cosmetic:

  * The combinatorial part is written with J_i = Phi_i/x_i and L_i = theta_i/x_i
    rather than with Phi_i and theta_i themselves. Algebraically identical, but
    the x_i cancels analytically instead of numerically -- so a species at zero
    concentration has a perfectly well-defined activity coefficient rather than a
    0/0. In a reaction network most species ARE at zero for part of the run.

  * ``active`` masks species with no UNIFAC decomposition -- ions, anything
    outside the table. They contribute nothing to the group sums. That is a
    deliberate statement of ignorance, made upstream and reported there; here it
    is just a mask. An unmodelled NEUTRAL species is then held at gamma = 1; an
    ION is not, because it has a Born term instead -- see below. "No UNIFAC
    decomposition" and "ideal" are two different claims and used to be conflated.

TWO CONVENTIONS, ONE EXPRESSION. A condensable species uses the symmetric
convention: gamma -> 1 as the liquid becomes pure in it. A Henry's-law solute
cannot, because it has no pure liquid state at these temperatures; its reference
is infinite dilution in a particular solvent, where gamma* -> 1 by definition.
The difference between the two is one division:

    gamma*_i = gamma_i(x) / gamma_i(infinite dilution in the reference solvent)

and the divisor depends only on temperature, so it collapses to a polynomial at
setup like every other property here. It arrives as ``ln_gamma_ref``, is zero for
symmetric species, and so costs one subtraction and no branch.

A THIRD CONVENTION, FOR IONS. UNIFAC has no ionic groups, so an ion has no
decomposition and is masked out of everything above -- but "no UNIFAC term" is not
the same as "gamma = 1", and treating it that way is what made an ion partition
to equal mole fraction between water and toluene. What an ion has instead is a
BORN term: the electrostatic cost of moving a charge between media of different
permittivity, referenced (like the Henry solutes above) to infinite dilution in
water.

    ln gamma_i = A_i / (R T) * ( 1/eps_mixture - 1/eps_water(T) )

It arrives as ``born``, an (n, 4) block ``[A | eps_pure | v_mol | eps_water]``
that is a function of TEMPERATURE ALONE -- so the parameters still collapse
upstream and the only thing left in here is the mixing rule. ``A`` is zero for
every neutral species, which makes ``A > 0`` the ion mask as well, so this costs
no branch either. See ``properties/dielectric.py`` for the model and for the two
things it deliberately omits.
"""

from __future__ import annotations

import numpy as np

from chemsim.constants import R

# Below this total liquid amount the composition is meaningless and every
# activity coefficient is reported as 1. Matches the vessel's dry-out scale.
_X_FLOOR = 1.0e-30

# UNIFAC's lattice coordination number, z = 10; the combinatorial term uses z/2.
_Z_HALF = 5.0

# ln gamma is clipped to +/- this before exponentiating: a pure overflow guard,
# and nothing in UNIFAC legitimately reaches it.
LN_GAMMA_CLIP = 50.0

# ⚠ AND A MUCH TIGHTER, SEPARATE CEILING ON THE BORN TERM, WHICH IS NOT AN
# OVERFLOW GUARD AND HAS TO BE ARGUED FOR.
#
# THE PHYSICS. A monovalent ion moving from water into a hydrocarbon costs
# ln gamma 63 (toluene) to 145 (hexane) -- the exclusion is genuinely that
# violent, which is why a salt is not extracted into toluene.
#
# THE PROBLEM, MEASURED RATHER THAN FEARED. The interphase flux is
# ``k_lle * (a1 - a2)`` with ``a2 = x2 gamma2``, so an unclipped gamma2 of 5e21
# gives that block a Jacobian diagonal of ``-k_lle gamma2 / N2`` = -7.5e22 and a
# relaxation timescale of 1e-23 s: a variable whose equilibrium value is 2e-24 mol
# relaxing to it infinitely fast. BDF does not merely slow down on that. On
# brine/toluene it reported SUCCESS and returned chloride at +3.07e9 mol in one
# layer and -3.07e9 in the other -- a cancelling dipole fourteen orders of
# magnitude larger than the material present, which ``project_non_negative`` then
# tidied into a plausible-looking answer. **The silent wrong answer was one
# projection away**, which is the whole reason there is a number here.
#
# WHY A CEILING IS HONEST, AND WHAT IT COSTS. The ceiling does not change any
# reportable quantity. At 12 the implied partition coefficient is 6e-6, which puts
# of order a MICROMOLE of ion in a typical organic layer against a mole in the
# aqueous one -- below any assay, invisible in a mass balance, and still safely
# ABOVE the solver's own 1e-9 atol so the quantity is resolved rather than lost in
# round-off. Both statements "the partition coefficient is 6e-6" and "... is
# 1e-63" say the same thing about the chemistry: free ions do not enter a
# low-dielectric phase. They say very different things about the Jacobian.
#
# So this is a RESOLUTION limit, not a thermodynamic claim, and it follows the
# precedent already set by ``detailed_balance``'s reverse-barrier floor: correct
# the number that cannot be integrated, keep the equilibrium that matters, and
# FLAG it. ``Vessel.electrolyte_report`` names every ion whose transfer energy is
# being reported at the ceiling and by how much it was cut, so a clipped value can
# never be mistaken for a computed one. The trade-off is measured across four
# decades of ceiling in ``validation/ion_partition.py``.
LN_GAMMA_BORN_MAX = 12.0


def oster_permittivity(
    phi: np.ndarray, eps: np.ndarray, medium: np.ndarray | None = None
) -> float:
    """Oster's rule: a mixture's relative permittivity from its volume fractions.

        f(eps) = sum_i phi_i f(eps_i),      f(e) = (e - 1)(2e + 1) / (9 e)

    ⚠ **A species with no measured permittivity (``eps <= 0``) contributes f = 0
    but still counts in the volume, and that is a BOUND rather than a guess.**
    ``f`` is monotone and ``f(1) = 0``, so f = 0 is the smallest value any real
    material can have -- this returns the LOWEST permittivity the layer could
    possibly have, never an invented one.

    The alternative -- excluding the unknown volume and renormalising over the rest
    -- says the unpriced species behaves like the average of the priced ones, and
    that is fine for a trace and actively dangerous when the unknown dominates. The
    benzoic-acid prep is the case that settled it: benzoic acid is a solid with no
    measured liquid permittivity, and as the organic layer filled with it the
    renormalising rule read that layer's polarity off the 32% of it that was water
    and ethanol, called it eps = 50, and let the ions in. The bound reads eps = 15
    and keeps them out. **Erring low errs toward the ion staying in the water**,
    which is the same safe direction everything else in this project errs in.

    ⚠ **``medium`` excludes species that are not part of the continuum at all, and
    that is a different thing from having no measured value.** An ION is not
    medium: the Born model puts a charge INSIDE a dielectric continuum, so it
    cannot also be the continuum, and the dielectric decrement a real salt does
    cause is an ionic-strength effect that belongs with Debye-Huckel rather than
    here. Left in, a molar brine would read eps = 75 instead of 78 -- and with the
    wrong sign for the low-concentration behaviour, since Debye-Huckel has ion
    activity FALLING at low ionic strength while this would have it rising.

    So the two cases are kept apart deliberately:
        an unpriced NEUTRAL   is medium of unknown polarity  -> f = 0, counts
        an ION                is not medium at all           -> excluded entirely

    Returns 0.0 only when there is no medium at all.

    The inversion is closed form: writing ``y`` for the right-hand side,
    ``(e - 1)(2e + 1) = 9 e y`` is ``2e^2 - (1 + 9y) e - 1 = 0``, so
    ``eps = [(1 + 9y) + sqrt((1 + 9y)^2 + 8)] / 4`` taking the positive root. That
    is not a convenience -- an iterative solve here would be finite-differenced by
    ``num_jac`` on every Jacobian column.

    ⚠ **A PURE LIQUID MUST COME BACK THROUGH THIS UNCHANGED TO THE LAST BIT**, and
    it does not come back unchanged if the caller compares against a permittivity
    that never went through it. That is why ``born_block`` puts the REFERENCE
    solvent's value through this same round trip: the difference between
    ``f^-1(f(eps))`` and ``eps`` is a few 1e-16, which is nothing as a
    permittivity and is not nothing when the claim being made is that an ion's
    activity coefficient in water is EXACTLY one.
    """
    known = eps > 0.0
    weight = np.maximum(phi, 0.0)
    if medium is not None:
        weight = np.where(medium, weight, 0.0)
    total = float(weight.sum())
    if total <= 0.0:
        return 0.0
    # ⚠ NORMALISE FIRST, THEN CONTRACT, and the order is not cosmetic. For a phase
    # holding one species, ``weight / total`` is exactly 1.0 in IEEE
    # arithmetic (x/x is exact) so the contraction returns that species' ``f``
    # bit-for-bit -- which is what makes a pure liquid come back through this
    # unchanged, and hence what makes an ion's activity coefficient in water
    # exactly one. Contracting first and dividing after gives ``(w f) / w``, which
    # is only equal to ``f`` to within rounding: about 1e-16, which is nothing as a
    # permittivity and is the difference between "exactly" and "nearly" in the one
    # claim this term has to make.
    phi_hat = weight / total
    safe = np.where(known, eps, 1.0)
    f = np.where(known, (safe - 1.0) * (2.0 * safe + 1.0) / (9.0 * safe), 0.0)
    u = 1.0 + 9.0 * float(phi_hat @ f)
    return 0.25 * (u + np.sqrt(u * u + 8.0))


def born_ln_gamma(
    x: np.ndarray,
    born: np.ndarray,
    T: float,
    clip: bool = True,
    phi: np.ndarray | None = None,
) -> np.ndarray:
    """The Born transfer term for the ions in a liquid of composition ``x``.

        ln gamma_i = A_i / (R T) * ( 1/eps_mixture - 1/eps_reference )

    ``born`` is the (n, 4) block ``[A | eps_pure | v_mol | eps_reference]``,
    already evaluated at T upstream (each permittivity clamped to its own
    published window). ``A`` is zero for every neutral species, so the returned
    array is zero there and the caller needs no mask.

    The mixture permittivity is Oster's rule -- ``oster_permittivity`` above.
    ``clip=False`` returns the UNCLIPPED value, which is what
    ``Vessel.electrolyte_report`` uses to say by how much a value was cut; nothing
    in the RHS ever asks for it.

    ``phi`` overrides the volume weights the mixing rule contracts, and it is how
    the vessel FREEZES a layer's polarity at an integration boundary -- see
    ``vessel_integrator.make_rhs``. Note what is frozen and what is not: the
    weights are, so the term stops depending on the amounts and the Jacobian
    coupling it created goes away; the per-species permittivities are NOT, so
    ``eps`` still follows temperature. That split is load-bearing rather than
    tidy. Freezing the resulting permittivity outright would leave a pure-water
    layer comparing a permittivity taken at one temperature against a reference
    taken at another, and the Born term would stop being exactly zero in water --
    which is the one thing every water-anchored pKa in this project rests on.
    With the WEIGHTS frozen, a single-species layer still normalises to exactly
    1.0 and the cancellation is still bit-exact at any temperature.

    ⚠ Returns zeros when there is no liquid to speak of, or when nothing in it
    has a known permittivity. Both matter for the same reason: an empty second
    layer must contribute an activity of exactly zero with a flat derivative, and
    a term that blew up as the layer emptied would be the third time this project
    paid for that.
    """
    n = x.shape[0]
    out = np.zeros(n)
    A = born[:, 0]
    if not np.any(A > 0.0):
        return out
    xs = np.maximum(x, 0.0)
    if xs.sum() <= _X_FLOOR:
        return out

    weights = xs * np.maximum(born[:, 2], 0.0) if phi is None else phi
    eps_mix = oster_permittivity(weights, born[:, 1], medium=A <= 0.0)
    if eps_mix <= 0.0:
        return out

    eps_ref = born[:, 3]
    inv_ref = np.where(eps_ref > 0.0, 1.0 / np.where(eps_ref > 0.0, eps_ref, 1.0), 0.0)
    raw = np.where(A > 0.0, A / (R * max(T, 1.0)) * (1.0 / eps_mix - inv_ref), 0.0)
    if not clip:
        return raw
    return np.clip(raw, -LN_GAMMA_BORN_MAX, LN_GAMMA_BORN_MAX)


def activity_coefficients(
    x: np.ndarray,
    nu: np.ndarray,
    R_k: np.ndarray,
    Q_k: np.ndarray,
    a_mn: np.ndarray,
    active: np.ndarray,
    T: float,
    ln_gamma_ref: np.ndarray | None = None,
    born: np.ndarray | None = None,
    ln_born: np.ndarray | None = None,
) -> np.ndarray:
    """Activity coefficients for a liquid of composition ``x`` at ``T``.

    ``x`` is (n,) mole fractions (need not be normalised); ``nu`` is (n, g);
    ``R_k``/``Q_k`` are (g,); ``a_mn`` is (g, g, 3), quadratic in T and in
    kelvin; ``active`` is an (n,) bool mask. ``ln_gamma_ref`` is an optional (n,)
    reference-state correction, already evaluated at T -- see the module
    docstring. ``born`` is the optional (n, 4) ion-transfer block, also evaluated
    at T. ``ln_born`` lets a caller that has ALREADY evaluated the Born term for
    this exact composition pass it in rather than have it recomputed -- the vessel
    RHS needs it for the ionic rate correction before it needs gamma, so without
    this it would be computed twice per layer per call for no reason. Returns (n,)
    activity coefficients, exactly 1 for a species that has neither a UNIFAC
    decomposition nor a charge.
    """
    n = x.shape[0]
    if ln_born is None:
        ln_born = np.zeros(n) if born is None else born_ln_gamma(x, born, T)

    def finish(ln_unifac: np.ndarray | None) -> np.ndarray:
        """Combine the two conventions. Neither one implies the other's mask."""
        ln_gamma = ln_born if ln_unifac is None else ln_unifac + ln_born
        return np.exp(np.clip(ln_gamma, -LN_GAMMA_CLIP, LN_GAMMA_CLIP))

    if nu.shape[1] == 0:
        return finish(None)

    xs = np.where(active, np.maximum(x, 0.0), 0.0)
    total = xs.sum()
    if total <= _X_FLOOR:
        return finish(None)
    xs = xs / total

    # ---- combinatorial: size and shape ---------------------------------
    r = nu @ R_k                      # (n,) van der Waals volume
    q = nu @ Q_k                      # (n,) van der Waals surface
    r_bar = float(xs @ r)
    q_bar = float(xs @ q)
    if r_bar <= 0.0 or q_bar <= 0.0:
        return finish(None)

    # J = Phi/x, L = theta/x. Both finite at x = 0, which is the point.
    J = r / r_bar
    L = np.where(q > 0.0, q / q_bar, 1.0)
    ratio = np.where(q > 0.0, J / L, 1.0)
    safe_J = np.where(J > 0.0, J, 1.0)
    ln_c = (
        1.0 - safe_J + np.log(safe_J)
        - _Z_HALF * q * (1.0 - ratio + np.log(ratio))
    )

    # ---- residual: group-group interaction -----------------------------
    a = a_mn[:, :, 0] + T * (a_mn[:, :, 1] + T * a_mn[:, :, 2])
    psi = np.exp(-a / T)              # (g, g)

    # Mixture: group mole fractions -> surface fractions.
    group_n = xs @ nu                 # (g,)
    group_total = group_n.sum()
    if group_total <= 0.0:
        return finish(None)
    theta = Q_k * group_n
    theta_sum = theta.sum()
    if theta_sum <= 0.0:
        return finish(None)
    theta = theta / theta_sum

    #   ln Gamma_k = Q_k [ 1 - ln(sum_m theta_m psi_mk)
    #                        - sum_m theta_m psi_km / sum_p theta_p psi_pm ]
    s = theta @ psi                                   # (g,)
    s = np.maximum(s, 1.0e-300)
    ln_Gamma = Q_k * (1.0 - np.log(s) - psi @ (theta / s))

    # Pure component i: the same expression over its own groups only. This is
    # the reference state that makes gamma -> 1 for a pure liquid.
    nu_total = nu.sum(axis=1, keepdims=True)          # (n,1)
    safe_total = np.where(nu_total > 0.0, nu_total, 1.0)
    theta_p = Q_k * (nu / safe_total)                 # (n,g)
    tp_sum = theta_p.sum(axis=1, keepdims=True)
    theta_p = theta_p / np.where(tp_sum > 0.0, tp_sum, 1.0)

    s_p = theta_p @ psi                               # (n,g)
    s_p = np.maximum(s_p, 1.0e-300)
    ln_Gamma_p = Q_k * (1.0 - np.log(s_p) - (theta_p / s_p) @ psi.T)

    ln_r = np.einsum("ik,ik->i", nu, ln_Gamma[None, :] - ln_Gamma_p)

    ln_gamma = ln_c + ln_r
    if ln_gamma_ref is not None:
        ln_gamma = ln_gamma - ln_gamma_ref
    return finish(np.where(active, ln_gamma, 0.0))

"""Layer 2 -- reaction thermodynamics.

Turns per-species formation data (from Layer 1) into reaction-level quantities:
the reaction enthalpy and Gibbs energy, hence the equilibrium constant, hence --
via ``detailed_balance`` -- the reverse reaction's Arrhenius parameters. Equilibrium
is thus *derived* from molecular structure instead of encoded by hand: a template
declares forward kinetics only, and K = k_forward / k_reverse fixes the rest.

Temperature dependence uses the standard approximation that Delta_H and Delta_S
are constant over the range of interest (equivalently, the van 't Hoff relation
with temperature-independent enthalpy):
    Delta_S(298) = (Delta_H - Delta_G(298)) / 298.15
    Delta_G(T)   = Delta_H - T * Delta_S(298)
    K(T)         = exp(-Delta_G(T) / (R T))
A future refinement integrates Cp(T) (Kirchhoff's law) for wide temperature spans.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from chemsim.constants import C_STD_M, P_STD_BAR, R, R_L_BAR
from chemsim.properties import ThermochemistryProvider
from chemsim.properties import standard_state
from chemsim.properties.volatility import VolatilityProvider
from chemsim.reactions.reaction import ConcreteReaction

T_REF = 298.15  # K

# ⚠ THE CEILING ON A DERIVED RATE CONSTANT, and it is the project's own number.
#
# ``reactions/library.py`` already refuses a hand-authored pre-exponential above
# the gas-kinetic collision limit -- "buying a prettier threshold with an
# impossible pre-exponential is the wrong trade", written there about a burner
# that wanted A = 1e14. Nothing applied the same standard to the rate constants
# this module DERIVES, and detailed balance derives one for every reversible
# template in the project.
#
# It should have: an elementary bimolecular step in solution cannot proceed
# faster than the reactants meet. In water that ceiling is Smoluchowski
# diffusion, ~1e10 L/(mol s) for ordinary small ions and 1.4e11 for H3O+ + OH-,
# which is the fastest bimolecular reaction known and is fast only because of
# Grotthuss proton hopping (Eigen). In the gas the ceiling is the collision
# frequency, the same 1e11 to an order of magnitude at ordinary temperatures.
# One number covers both to the accuracy anything here needs.
#
# ⚠ THE CEILING IS ON k(T_REF), NOT ON A. Every acid dissociation in this project
# carries Ea = 60 kJ/mol with a pre-exponential many orders above 1e11, and their
# rate constants are nonetheless 1e-4 of the limit or below -- the barrier is what
# makes them physical. Capping A instead of k would slow every acid/base
# equilibration in the project by 1e7 and would be measuring the wrong quantity.
#
# ⚠ MOLECULARITY: the ceiling applies to a step with TWO OR MORE reactants. A
# unimolecular step's ceiling is a bond vibration frequency, ~1e14 s^-1, which is
# a different quantity in different units; it is NOT guarded here, because
# nothing in this project approaches it (measured -- see
# ``validation/rate_ceiling.py``) and a guard with no case behind it is an
# invention rather than a bound.
COLLISION_LIMIT = 1.0e11  # L/(mol s), k of a bimolecular step at T_REF


def reaction_deltas(
    reaction: ConcreteReaction,
    provider: ThermochemistryProvider,
    volatility: VolatilityProvider | None = None,
) -> tuple[float, float]:
    """Return (Delta_H, Delta_G) of reaction at 298.15 K, in kJ/mol.

    With ``volatility`` supplied, a LIQUID-phase reaction is moved out of the
    ideal-gas standard state its formation data came in and into the pure-liquid
    one -- see ``properties.standard_state``. That is not a refinement, it is a
    correction: gas-phase formation data describes an isolated molecule, and
    applying it unmodified to a reaction in solution asserts that solvation costs
    nothing. A gas-phase reaction is left alone, because for it the ideal-gas
    basis is the right one.

    Omitting ``volatility`` reproduces the uncorrected ideal-gas result, which is
    what a network built without a volatility model gets.
    """
    dH = dG = 0.0
    for smi in reaction.products:
        t = provider.get(smi)
        dH += t.Hf
        dG += t.Gf
    for smi in reaction.reactants:
        t = provider.get(smi)
        dH -= t.Hf
        dG -= t.Gf

    if volatility is not None and reaction.phase != "gas":
        shift_H, shift_G, _ = standard_state.reaction_shift(
            reaction.reactants, reaction.products, volatility, T_REF
        )
        dH += shift_H
        dG += shift_G
    return dH, dG


def reaction_entropy(
    reaction: ConcreteReaction,
    provider: ThermochemistryProvider,
    volatility: VolatilityProvider | None = None,
) -> float:
    """Reaction entropy at 298.15 K in J/(mol K), from Delta_G = Delta_H - T Delta_S.

    Note the unit change: enthalpies/Gibbs energies are kJ/mol here, entropy is
    J/(mol K) -- the conventional pairing, and the one the Arrhenius algebra below
    needs so that Delta_S / R is dimensionless.
    """
    dH, dG_ref = reaction_deltas(reaction, provider, volatility)
    return (dH - dG_ref) * 1000.0 / T_REF


def delta_n(reaction: ConcreteReaction) -> int:
    """Change in mole count across the reaction (products minus reactants)."""
    return len(reaction.products) - len(reaction.reactants)


def gibbs_at(
    reaction: ConcreteReaction,
    provider: ThermochemistryProvider,
    T: float,
    volatility: VolatilityProvider | None = None,
) -> float:
    """Reaction Gibbs energy at temperature T, kJ/mol (constant dH/dS approx)."""
    dH, _ = reaction_deltas(reaction, provider, volatility)
    dS = reaction_entropy(reaction, provider, volatility) / 1000.0  # J -> kJ/(mol K)
    return dH - T * dS


def equilibrium_constant(
    reaction: ConcreteReaction,
    provider: ThermochemistryProvider,
    T: float,
    volatility: VolatilityProvider | None = None,
) -> float:
    """Activity-basis K(T) = exp(-Delta_G(T) / RT).

    The standard state is the ideal gas at 1 bar, or -- for a liquid-phase
    reaction with ``volatility`` supplied -- the pure liquid. For a rate law
    written in mol/L, see ``equilibrium_constant_c``.
    """
    dG_T = gibbs_at(reaction, provider, T, volatility) * 1000.0  # kJ/mol -> J/mol
    return math.exp(-dG_T / (R * T))


def equilibrium_constant_c(
    reaction: ConcreteReaction,
    provider: ThermochemistryProvider,
    T: float,
    volatility: VolatilityProvider | None = None,
) -> float:
    """Concentration-basis K_c(T), the ratio the mol/L rate law actually equilibrates to.

    The thermochemistry's standard state is an ideal gas at 1 bar; our state vector
    is mol/L. With a_i = c_i R T / P_std, the two bases differ by a factor per net
    mole change:

        K_c = K_a * (P_std / (R T c_std)) ** delta_n

    For delta_n = 0 (e.g. esterification) the factor is exactly 1 and the distinction
    is invisible -- but for delta_n = +-1 it is a factor of ~28 at 340 K, so it is
    not optional once the network contains additions or fragmentations.
    """
    K_a = equilibrium_constant(reaction, provider, T, volatility)
    dn = delta_n(reaction)
    if dn == 0:
        return K_a
    return K_a * (P_STD_BAR / (R_L_BAR * T * C_STD_M)) ** dn


def modified_arrhenius(A: float, n: float, Ea: float, T: float) -> float:
    """k = A * T**n * exp(-Ea / R T) -- the one rate form Layer 4 evaluates."""
    return A * T**n * math.exp(-Ea / (R * T))


@dataclass(frozen=True)
class DetailedBalance:
    """Forward + reverse Arrhenius parameters that are thermodynamically consistent.

    ``Ea_fwd`` may differ from the template's declared value -- see
    ``detailed_balance`` for the (logged) case where it must be raised.
    """

    A_fwd: float
    Ea_fwd: float
    A_rev: float
    Ea_rev: float
    dH: float          # J/mol, forward reaction enthalpy
    dS: float          # J/(mol K), forward reaction entropy
    barrier_raised: bool = False   # True if Ea_fwd was raised to stay physical
    n_fwd: float = 0.0             # modified-Arrhenius exponents, k = A T**n e^(-Ea/RT)
    n_rev: float = 0.0
    # The factor BOTH pre-exponentials were scaled by to keep the faster
    # direction at or below ``COLLISION_LIMIT``. 1.0 means the pair was already
    # physical. Scaling both preserves K(T) exactly -- see ``detailed_balance``.
    rate_capped: float = 1.0


def detailed_balance(
    reaction: ConcreteReaction,
    provider: ThermochemistryProvider,
    A_fwd: float,
    Ea_fwd: float,
    T_ref: float = T_REF,
    volatility: VolatilityProvider | None = None,
    n_fwd: float = 0.0,
) -> DetailedBalance:
    """Derive reverse Arrhenius parameters from forward kinetics + reaction thermo.

    A template declares FORWARD kinetics only; the reverse is not a free parameter
    once the thermochemistry is known. Requiring k_f / k_r = K(T) and substituting
    Arrhenius forms plus Delta_G = Delta_H - T Delta_S:

        k_r = k_f / K = A_f exp(-Ea_f/RT) * exp((Delta_H - T Delta_S)/RT)
            = [A_f exp(-Delta_S/R)] * exp(-[Ea_f - Delta_H]/RT)

    which is *itself* Arrhenius. That is the whole point: the reverse reaction enters
    the network as an ordinary reaction with its own (A, Ea), so Layer 4 stays a pure
    A exp(-Ea/RT) mass-action integrator with no notion of reversibility at all.

        A_rev  = A_fwd * exp(-Delta_S/R)
        Ea_rev = Ea_fwd - Delta_H

    Two corrections to that clean result:

    1. **Negative reverse barrier.** For an elementary step the forward barrier
       cannot be lower than the endothermicity (Ea_f >= Delta_H); if the declared
       Ea_f violates that, Ea_rev would come out negative. Rather than admit an
       unphysical barrier or silently break K, we raise the forward barrier to
       Delta_H (the thermodynamic floor), set Ea_rev = 0, and flag it. K(T) is still
       reproduced exactly -- only the declared forward rate is corrected, loudly.

    2. **Standard state.** K from formation data is activity-basis; the rate law is
       mol/L, and the conversion carries a factor ``(R T / P_std)**delta_n``. The
       ``T**delta_n`` part of that is not Arrhenius, so it goes into the
       temperature EXPONENT of the modified Arrhenius form rather than being
       folded into A at one reference temperature:

           k = A * T**n * exp(-Ea / R T),    n_rev = n_fwd + delta_n

       which reproduces K exactly at every temperature. It used to be absorbed
       into ``A_rev`` at ``T_ref``, which left K drifting as
       ``(T/T_ref)**delta_n`` -- about 1.3x per unit delta_n over a 100 K
       excursion. ``T_ref`` is therefore no longer used for anything and is
       retained only so existing callers keep working.

    3. **An impossible derived rate.** ⚠ This is the third correction and it was
       added by M12, because leaving it out cost a measured wrong answer rather
       than an untidy number. A template declares the FORWARD rate; detailed
       balance then hands the reverse whatever K demands, and nothing checked
       that the result was a rate matter can actually go at. Water
       autoionization is the case: ``Ea_fwd = 60 kJ/mol`` is chosen to sit just
       above water's dissociation enthalpy of 55.8 so correction 1 does not
       fire, which leaves the reverse a barrier of 4.2 kJ/mol and a rate
       constant of **9.4e18 L/(mol s) -- 9.4e7 times the collision limit**, for
       a recombination measured at 1.4e11. The very choice that avoids the
       barrier clamp is what puts the reverse eight orders past what a collision
       can deliver.

       That is not a cosmetic error. A pair running 1e8 times too fast turns
       over 9.4e4 mol/s in a 1 L flask, so its two heat terms are +-5.2e9 W
       either side of a net that is a fraction of a watt -- a twelve-order
       cancellation in the temperature equation, sitting on the stiffest mode in
       the vessel, and invisible to a solver whose error control is denominated
       in kelvin and moles rather than in joules. Three consecutive BDF steps of
       168 s then destroyed 467 J in an insulated flask whose composition did not
       move by a picomole. See ``validation/adiabatic_tail.py``.

       So: if either direction's rate constant at ``T_ref`` exceeds
       ``COLLISION_LIMIT``, BOTH pre-exponentials are scaled by the same factor
       and ``rate_capped`` reports it. ⚠ **Scaling both is what keeps this a
       correction rather than a change of chemistry: K = k_f/k_r is invariant
       under it, exactly**, so every equilibrium, every pKa and every pH is
       untouched -- measured, Kw stays 1.0022e-14 to five figures across eight
       orders of A. What changes is only how fast the equilibrium is REACHED,
       and water's still arrives in ~0.3 ms, which is instant against any
       chemistry in this project.

       ⚠ **REPORTED, NOT FIXED: THIS CAP COMPARES A HETEROGENEOUSLY CATALYSED
       PRE-EXPONENTIAL AGAINST A LIMIT THAT IS NOT IN ITS UNITS.** A reaction
       with a declared ``solid_catalyst`` carries an order-1 factor in MOL, so
       its ``A`` has an extra ``mol**-1`` and its rate constant is not in
       L/(mol s) at all -- ``validation/rate_ceiling.apparent_A`` multiplies by
       ``library.SOLID_CATALYST_REFERENCE`` to undo exactly that before auditing,
       and this function does not. So the cap here sees a number
       ``1/SOLID_CATALYST_REFERENCE`` = 10x too large and would fire 10x too
       eagerly.

       Bounded, and bounded in the class of error this project forgives: the cap
       scales BOTH pre-exponentials, so K is invariant under it and the whole cost
       is a clock at most 10x slow. And measured: it does NOT fire on any of the
       five catalysed templates -- the coldest ceiling crossing among them is
       1248 K against a cap applied at 298 K -- which is asserted in
       ``tests/test_surface.py`` so that it cannot start firing silently. Fixing
       it properly means this module knowing about a loading declared in
       ``reactions/library``, which is a Layer-2 import cycle; the honest place
       for the reference charge is an argument, and that is the change to make
       when a declaration actually needs it.
    """
    dH_kJ, _ = reaction_deltas(reaction, provider, volatility)
    dH = dH_kJ * 1000.0                              # J/mol
    dS = reaction_entropy(reaction, provider, volatility)   # J/(mol K)

    barrier_raised = Ea_fwd < dH
    Ea_fwd_out = max(Ea_fwd, dH)
    Ea_rev = Ea_fwd_out - dH                         # >= 0 by construction

    dn = delta_n(reaction)
    A_rev = A_fwd * math.exp(-dS / R)
    if dn != 0:
        A_rev *= (R_L_BAR * C_STD_M / P_STD_BAR) ** dn
    n_rev = n_fwd + dn

    # Correction 3: neither direction may go faster than the reactants meet.
    # Only a step of molecularity >= 2 has a collision limit to breach, and the
    # ceiling is on the rate CONSTANT rather than on A -- see COLLISION_LIMIT.
    rate_capped = 1.0
    for A, Ea, n, reactants in (
        (A_fwd, Ea_fwd_out, n_fwd, reaction.reactants),
        (A_rev, Ea_rev, n_rev, reaction.products),
    ):
        if len(reactants) < 2:
            continue
        k = A * T_ref**n * math.exp(-Ea / (R * T_ref))
        if k > COLLISION_LIMIT:
            rate_capped = min(rate_capped, COLLISION_LIMIT / k)
    if rate_capped < 1.0:
        # BOTH, by the same factor: K = k_f / k_r is what must not move.
        A_fwd *= rate_capped
        A_rev *= rate_capped

    return DetailedBalance(
        A_fwd=A_fwd,
        Ea_fwd=Ea_fwd_out,
        A_rev=A_rev,
        Ea_rev=Ea_rev,
        dH=dH,
        dS=dS,
        barrier_raised=barrier_raised,
        n_fwd=n_fwd,
        n_rev=n_rev,
        rate_capped=rate_capped,
    )

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

    return DetailedBalance(
        A_fwd=A_fwd,
        Ea_fwd=Ea_fwd_out,
        A_rev=A_rev,
        Ea_rev=Ea_rev,
        dH=dH,
        dS=dS,
        barrier_raised=barrier_raised,
        n_fwd=n_fwd,
        n_rev=n_fwd + dn,
    )

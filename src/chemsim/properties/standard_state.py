"""Layer 1 -- moving formation data out of the ideal gas and into the liquid.

Group-contribution thermochemistry (Joback, Benson, and the curated tables that
back them up) is **ideal-gas** data: formation enthalpies and Gibbs energies for
an isolated molecule at 1 bar. Almost every reaction this simulator runs happens
in a liquid. Using the gas numbers there is not a small approximation -- it is
the claim that a molecule costs the same to make whether or not it is surrounded
by solvent, which is the same claim ideal Raoult made about vapour pressure and
is wrong for the same reason.

The fix is a change of standard state. A pure liquid is in equilibrium with its
own vapour at ``Psat``, so their molar Gibbs energies are equal:

    mu(liquid) = mu(gas at Psat) = mu(gas at 1 bar) + R T ln(Psat / P_std)

Hence, per species,

    dGf(liquid) = dGf(gas) + R T ln(Psat / P_std)          <- always negative,
    dHf(liquid) = dHf(gas) - dHvap                            since Psat < 1 bar

and a reaction's shift is the stoichiometric sum of those. For esterification
that is a factor of ~2.4 in K at 298 K, in the direction of the measured value.

**dHvap comes from the vapour-pressure curve itself**, via Clausius-Clapeyron,
rather than from a second correlation:

    dHvap(T) = R T^2 * ln(10) * B / (C + T)^2      for log10 P = A - B/(C+T)

That is not a shortcut, it is the point: the enthalpy and Gibbs shifts then come
from one curve and satisfy Gibbs-Helmholtz between them, so the entropy the
caller derives from the pair is the real one. Checked against measured dHvap it
is good to a few percent (water 44.1 vs 44.0, ethanol 42.7 vs 42.3, acetone 31.6
vs 31.0 kJ/mol).

**A dissolved gas takes the same expression.** Its Antoine coefficients hold a
Henry constant rather than a vapour pressure, and ``R T ln(H / P_std)`` is
exactly the shift from the ideal gas to the solute's infinite-dilution reference
in that solvent. One formula, two standard states -- the same collapse that lets
Raoult and Henry share a line of code in Layer 4.

**Not everything can be shifted, and the ones that can't are refused loudly.**
A species with no volatility model (an ion; anything that decomposes before it
boils) has ``A = -30``, so ``R T ln(Psat)`` would read -171 kJ/mol and destroy
every equilibrium it touched. Those species keep whatever basis their data was
already on -- for the derived ions that is an aqueous basis by construction --
and ``shift`` reports that it declined rather than returning a quiet zero.

**And where the liquid has been measured, none of this is needed.** The route
above derives the liquid standard state; ``formation_data.LIQUID_FORMATION``
simply *contains* it, for 59 species, and a measurement beats a derivation. The
shift is then the difference of two measured values, with no correlation in it
at all -- and one species class needs exactly that, because for a carboxylic
acid the derivation is not merely imprecise but invalid: acetic acid vapour is
~95% dimer, so ``Psat`` is not the monomer's vapour pressure and ``R T ln(Psat)``
prices the wrong molecule. It misses by 4.9 kJ/mol on acetic acid, and routing
gas-phase data through that error predicts K = 149 for Fischer esterification
where the liquid data gives 8.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from chemsim.constants import P_STD_BAR, R
from chemsim.matter import Molecule
from chemsim.properties.formation_data import LIQUID_FORMATION
from chemsim.properties.volatility import Volatility, VolatilityProvider

LN10 = math.log(10.0)
T_REF = 298.15

# Below this vapour pressure (bar) the shift is refused rather than computed.
# Not a numerical guard dressed up as physics: R T ln(Psat) is only as good as
# Psat, and for a species this involatile the number is a correlation
# extrapolated tens of orders of magnitude past any data -- a discovered
# polyester oligomer comes out at 1e-20 bar, which would price its formation at
# -114 kJ/mol and hand the equilibrium an overflow. Benzoic acid, the least
# volatile species with a shift anyone would defend, sits at 2e-6 bar, so this
# floor is six orders of magnitude clear of the cases that matter.
PSAT_FLOOR_BAR = 1.0e-12


@dataclass(frozen=True)
class StandardStateShift:
    """What to add to a species' formation data to put it in the liquid basis."""

    dHf: float          # kJ/mol
    dGf: float          # kJ/mol
    applied: bool
    reason: str = ""

    @property
    def is_zero(self) -> bool:
        return not self.applied


NO_SHIFT = StandardStateShift(0.0, 0.0, False, "gas-phase reaction")


def enthalpy_of_vaporization(vol: Volatility, T: float) -> float:
    """dHvap(T) in kJ/mol, from the Antoine curve by Clausius-Clapeyron.

    For a Henry's-law entry this is the enthalpy of the dissolved -> gas
    transfer, which is the same derivative of the same functional form.
    """
    denom = vol.C + T
    if denom <= 0.0:
        return 0.0
    return R * T * T * LN10 * vol.B / (denom * denom) / 1000.0


_CURATED_LIQUID: dict[str, tuple[float, float]] = {
    Molecule.from_smiles(smi).smiles: v for smi, v in LIQUID_FORMATION.items()
}

_MEASURED = (
    "measured liquid formation data (CRC/NIST/ATCT); no vapour-pressure "
    "correlation involved"
)


def curated_liquid_species() -> tuple[str, ...]:
    """Species whose liquid standard state is measured rather than derived."""
    return tuple(sorted(_CURATED_LIQUID))


def shift(
    smiles: str, volatility: VolatilityProvider, T: float = T_REF
) -> StandardStateShift:
    """The ideal-gas -> liquid standard-state shift for one species.

    For a species with measured liquid formation data the shift is just the
    difference between the two measured bases. Note that it does not depend on
    ``T``: both tables are 298.15 K standard-state statements, which is the
    temperature every caller asks for -- reaction thermochemistry evaluates
    Delta_H and Delta_G at 298.15 K once and carries them to other temperatures
    through van 't Hoff, so this is where the whole chain is anchored. ``T``
    still selects the vapour pressure on the derived route below.
    """
    # The volatility model is consulted FIRST even when curated liquid data
    # exists, because "declines to give one" is how both an ion and a caller
    # asking for the uncorrected ideal-gas basis say so. Reading the curated
    # table ahead of it would make that switch unreachable. No curated species
    # is refused here in practice -- they are all ordinary liquids at 298 K, and
    # a test pins that.
    vol = volatility.get(smiles)
    if not vol.volatile:
        return StandardStateShift(
            0.0, 0.0, False,
            f"{smiles}: no volatility model (ion, or decomposes before boiling); "
            "its data is left on whatever basis it was derived on",
        )

    key = Molecule.from_smiles(smiles).smiles
    if key in _CURATED_LIQUID:
        gas = volatility.thermo.get(key)
        Hf_l, Gf_l = _CURATED_LIQUID[key]
        return StandardStateShift(Hf_l - gas.Hf, Gf_l - gas.Gf, True, _MEASURED)

    coefficient = vol.coefficient(T)
    if coefficient < PSAT_FLOOR_BAR:
        return StandardStateShift(
            0.0, 0.0, False,
            f"{smiles}: vapour pressure {coefficient:.2e} bar at {T:.1f} K is "
            f"below the {PSAT_FLOOR_BAR:.0e} bar floor, so the correlation is "
            "extrapolated far past its data; left on the ideal-gas basis",
        )
    return StandardStateShift(
        dHf=-enthalpy_of_vaporization(vol, T),
        dGf=R * T * math.log(coefficient / P_STD_BAR) / 1000.0,
        applied=True,
        reason=vol.source,
    )


def reaction_shift(
    reactants: tuple[str, ...],
    products: tuple[str, ...],
    volatility: VolatilityProvider,
    T: float = T_REF,
) -> tuple[float, float, tuple[str, ...]]:
    """Stoichiometric (dH, dG) shift for a reaction, plus the species it skipped.

    Species that cannot be shifted contribute nothing and are named. That is not
    a silent zero: for a derived ion it is the correct behaviour, because the
    value was anchored on the shifted acid in the first place (see
    ``electrolyte.ion_thermochemistry``), so the two conventions already agree.
    """
    dH = dG = 0.0
    skipped: list[str] = []
    for sign, species in ((1.0, products), (-1.0, reactants)):
        for smi in species:
            s = shift(smi, volatility, T)
            if not s.applied:
                skipped.append(smi)
                continue
            dH += sign * s.dHf
            dG += sign * s.dGf
    return dH, dG, tuple(dict.fromkeys(skipped))

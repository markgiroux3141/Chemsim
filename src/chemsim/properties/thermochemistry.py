"""Layer 1 -- thermochemistry provider.

Resolves a molecule to standard thermochemical data (ideal gas, 298.15 K),
preferring curated experimental values and falling back to Joback estimation.
Every result carries its ``source`` so downstream code (and the player) can tell
a measured number from an estimate.

Why curated overrides matter: small/inorganic species (water, O2, CO2, methane,
NH3) have no Joback group decomposition -- Joback would return the bare formula
intercepts, which are meaningless for them. These MUST come from a table. This is
the "measured vs. estimated, with provenance" discipline in practice.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from chemsim.matter import Molecule
from chemsim.properties.formation_data import (
    DERIVED_GAS_FORMATION,
    IDEAL_GAS_FORMATION,
    PHYSICAL_PROPERTIES,
)
from chemsim.properties.benson import BensonError
from chemsim.properties.benson import estimate as benson_estimate
from chemsim.properties.critical import CriticalPropertyError, estimate_physical
from chemsim.properties.element_data import (
    ELEMENTAL,
    LATTICE_ELEMENTS,
    REFERENCE_STATES,
    element_of,
    is_monatomic,
)
from chemsim.properties.joback import JobackError, estimate
from chemsim.properties.mineral_data import MINERALS
from chemsim.properties.physical_data import MEASURED_PHYSICAL
from chemsim.properties.stereo_keys import StereoFallback, fallback_note


@dataclass(frozen=True)
class ThermoData:
    Hf: float                       # kJ/mol, standard enthalpy of formation (ideal gas, 298.15 K)
    Gf: float                       # kJ/mol, standard Gibbs energy of formation
    source: str                     # provenance, e.g. "experimental" / "joback"
    Cp_coeffs: tuple | None = None  # J/(mol K) polynomial a,b,c,d
    Tb: float | None = None         # K, normal boiling point
    Tc: float | None = None         # K, critical temperature
    Pc: float | None = None         # bar, critical pressure
    Vc: float | None = None         # cm3/mol, critical volume
    Hvap: float | None = None       # kJ/mol, enthalpy of vaporization AT Tb
    Tm: float | None = None         # K, normal melting point
    Hfus: float | None = None       # kJ/mol, enthalpy of fusion at Tm
    # Provenance of the PHYSICAL half alone (Tb/Tc/Pc/Vc), separately from
    # ``source``, which describes the whole record. Kept as its own field
    # because a record is assembled from independently-resolved halves and
    # ``volatility`` builds a vapour-pressure curve out of the physical one --
    # it has to name what that curve rests on, and deducing it by matching on
    # the prefix of a composite string is the kind of guess that goes quietly
    # wrong the first time the wording changes.
    physical_source: str | None = None

    def Cp(self, T: float) -> float | None:
        if self.Cp_coeffs is None:
            return None
        a, b, c, d = self.Cp_coeffs
        return a + b * T + c * T**2 + d * T**3


# Curated experimental data (ideal gas, 298.15 K). kJ/mol.
# Sources: NIST-JANAF / CODATA reference values; ideal-gas Cp polynomials and
# critical constants from Poling, Prausnitz & O'Connell, "The Properties of Gases
# and Liquids" (5th ed), Appendix A. Cp is a + bT + cT^2 + dT^3 in J/(mol K) --
# the same functional form Joback emits, so downstream code needs no special case.
_EXPERIMENTAL = "experimental (NIST/CODATA, ideal gas 298 K)"
_ELEMENT = "element reference state"
_SPECTATOR = "spectator ion (zero reference; cancels from every equilibrium)"
_CURATED_RAW: dict[str, ThermoData] = {
    # water
    "O": ThermoData(-241.83, -228.59, _EXPERIMENTAL,
                    Cp_coeffs=(32.24, 1.924e-3, 1.055e-5, -3.596e-9),
                    Tb=373.15, Tc=647.14, Pc=220.64, Vc=55.95, Hvap=40.65, Tm=273.15, Hfus=6.01),
    # ⚠ THE ELEMENTS ARE NOT HERE. They live in ``element_data`` and are
    # composed in below by ``_element_entries()``. That is not tidying: their
    # formation values are exactly zero only for the species whose REFERENCE
    # STATE IS THE GAS, and hand-maintaining that distinction is what put Br2
    # and I2 in this table at 0.0 when their ideal-gas values are +30.90 and
    # +62.40 kJ/mol. One home, one rule, and a guard in ``get`` so no
    # estimator can ever price an element.
    # CO2 (sublimes at 1 atm; Tb is the sublimation point)
    "O=C=O": ThermoData(-393.51, -394.39, _EXPERIMENTAL,
                        Cp_coeffs=(19.80, 7.344e-2, -5.602e-5, 1.715e-8),
                        Tb=194.65, Tc=304.12, Pc=73.74, Vc=94.07, Hvap=17.16, Tm=216.59, Hfus=9.02),
    # CO
    "[C-]#[O+]": ThermoData(-110.53, -137.16, _EXPERIMENTAL,
                            Cp_coeffs=(30.87, -1.285e-2, 2.789e-5, -1.272e-8),
                            Tb=81.66, Tc=132.85, Pc=34.94, Vc=93.1, Hvap=6.04, Tm=68.13, Hfus=0.833),
    # methane
    "C": ThermoData(-74.87, -50.81, _EXPERIMENTAL,
                    Cp_coeffs=(19.25, 5.213e-2, 1.197e-5, -1.132e-8),
                    Tb=111.66, Tc=190.56, Pc=45.99, Vc=98.6, Hvap=8.19, Tm=90.69, Hfus=0.94),
    # ammonia
    "N": ThermoData(-45.94, -16.41, _EXPERIMENTAL,
                    Cp_coeffs=(27.31, 2.383e-2, 1.707e-5, -1.185e-8),
                    Tb=239.82, Tc=405.40, Pc=113.33, Vc=72.5, Hvap=23.33, Tm=195.42, Hfus=5.66),

    # ---------------------------------------------------------------------
    # Hydrogen halides. Joback has no group for them at all (the halogen group
    # covers the halogen but leaves the hydrogen unaccounted).
    "Cl": ThermoData(-92.31, -95.30, _EXPERIMENTAL,
                     Cp_coeffs=(30.67, -7.201e-3, 1.246e-5, -3.898e-9),
                     Tb=188.15, Tc=324.65, Pc=83.10, Vc=80.9, Hvap=16.15,
                     Tm=158.97, Hfus=1.99),
    "Br": ThermoData(-36.29, -53.36, _EXPERIMENTAL,
                     Cp_coeffs=(29.72, -4.100e-3, 8.500e-6, -2.700e-9),
                     Tb=206.45, Tc=363.15, Pc=85.50, Vc=100.0, Hvap=17.62,
                     Tm=186.30, Hfus=2.41),
    "F": ThermoData(-273.30, -275.40, _EXPERIMENTAL,
                    Cp_coeffs=(29.06, -6.200e-4, 1.300e-6, -1.500e-9),
                    Tb=292.69, Tc=461.00, Pc=64.80, Vc=69.0, Hvap=7.49,
                    Tm=189.79, Hfus=3.93),
    "I": ThermoData(26.50, 1.70, _EXPERIMENTAL,
                    Cp_coeffs=(29.20, -1.000e-3, 3.000e-6, -1.000e-9),
                    Tb=237.55, Tc=423.85, Pc=83.10, Vc=110.0, Hvap=19.76,
                    Tm=222.40, Hfus=2.87),

    # ---------------------------------------------------------------------
    # Mineral acids and oxides. Joback has no sulfonyl, no N-oxide and no P at
    # all, so every one of these fails there and MUST be curated. They are also
    # the highest-tonnage chemicals in the world, which is why they are here.
    # Cp is given as a constant where a reliable polynomial was not available --
    # a documented approximation, preferable to extrapolating a fitted curve.
    "OS(=O)(=O)O": ThermoData(-735.13, -653.37, _EXPERIMENTAL,
                              Cp_coeffs=(83.70, 0.0, 0.0, 0.0),
                              Tb=610.15, Tc=925.00, Pc=64.00, Vc=177.0, Hvap=50.00,
                              Tm=283.46, Hfus=10.71),
    "O[N+](=O)[O-]": ThermoData(-134.31, -73.94, _EXPERIMENTAL,
                                Cp_coeffs=(53.40, 0.0, 0.0, 0.0),
                                Tb=356.15, Tc=520.00, Pc=68.90, Vc=145.0, Hvap=39.10,
                                Tm=231.55, Hfus=10.48),
    "OP(=O)(O)O": ThermoData(-1279.00, -1119.10, _EXPERIMENTAL,
                             Cp_coeffs=(106.10, 0.0, 0.0, 0.0),
                             Tm=315.51, Hfus=13.40),
    "OO": ThermoData(-136.31, -105.60, _EXPERIMENTAL,
                     Cp_coeffs=(43.10, 0.0, 0.0, 0.0),
                     Tb=423.35, Tc=728.00, Pc=217.00, Vc=76.0, Hvap=51.60,
                     Tm=272.74, Hfus=12.50),
    "O=S=O": ThermoData(-296.84, -300.13, _EXPERIMENTAL,
                        Cp_coeffs=(39.87, 0.0, 0.0, 0.0),
                        Tb=263.13, Tc=430.75, Pc=78.84, Vc=122.0, Hvap=24.94,
                        Tm=197.67, Hfus=7.40),
    "O=S(=O)=O": ThermoData(-395.77, -371.02, _EXPERIMENTAL,
                            Cp_coeffs=(50.67, 0.0, 0.0, 0.0),
                            Tb=317.90, Tc=490.85, Pc=82.10, Vc=127.0, Hvap=40.70,
                            Tm=289.95, Hfus=8.60),
    "S": ThermoData(-20.60, -33.40, _EXPERIMENTAL,
                    Cp_coeffs=(34.19, 0.0, 0.0, 0.0),
                    Tb=212.84, Tc=373.40, Pc=89.63, Vc=98.5, Hvap=18.67,
                    Tm=187.68, Hfus=2.38),
    "[N]=O": ThermoData(90.29, 86.60, _EXPERIMENTAL,
                        Cp_coeffs=(29.86, 0.0, 0.0, 0.0),
                        Tb=121.38, Tc=180.00, Pc=64.80, Vc=58.0, Hvap=13.83,
                        Tm=109.50, Hfus=2.30),
    "[O-][N+]=O": ThermoData(33.10, 51.30, _EXPERIMENTAL,
                          Cp_coeffs=(36.97, 0.0, 0.0, 0.0),
                          Tb=294.30, Tc=431.35, Pc=101.33, Vc=82.0, Hvap=38.12,
                          Tm=261.90, Hfus=14.65),
    "[N-]=[N+]=O": ThermoData(82.05, 104.20, _EXPERIMENTAL,
                              Cp_coeffs=(38.62, 0.0, 0.0, 0.0),
                              Tb=184.67, Tc=309.57, Pc=72.55, Vc=97.0, Hvap=16.53,
                              Tm=182.30, Hfus=6.54),

    # ---------------------------------------------------------------------
    # Formaldehyde: Joback's aldehyde group needs a carbon to attach to, and
    # formaldehyde has none. Very common reagent, one-line fix.
    "C=O": ThermoData(-108.60, -102.53, _EXPERIMENTAL,
                      Cp_coeffs=(35.39, 0.0, 0.0, 0.0),
                      Tb=254.05, Tc=408.00, Pc=65.90, Vc=115.0, Hvap=23.32,
                      Tm=181.15, Hfus=7.50),

    # ---------------------------------------------------------------------
    # Spectator cations. A strong base in water simply IS its ions -- NaOH does
    # not exist as a molecule in solution -- so sodium is charged directly as
    # [Na+] alongside [OH-]. It participates in no reaction here, which is what
    # makes a zero reference legitimate rather than a guess: any consistent value
    # cancels out of every equilibrium it appears in.
    "[Na+]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(46.4, 0.0, 0.0, 0.0)),
    "[K+]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(21.8, 0.0, 0.0, 0.0)),
    # The mineral cations, on exactly the same argument and with exactly the
    # same limit. A mineral in a flask IS its ions (see ``mineral_data`` for why
    # the lattice cannot be), so a chain that digs up limestone or green vitriol
    # needs these; and each participates in no reaction this engine can express,
    # so any consistent value cancels.
    #
    # ⚠ WHAT WOULD BREAK IT, stated because a spectator's zero is a licence with
    # conditions rather than a datum. Two mechanics on the backlog would end it:
    # a SOLUBILITY PRODUCT (calcium and carbonate would then appear on opposite
    # sides of a real equilibrium, so their zeros would stop cancelling) and
    # ELECTROCHEMISTRY (Fe2+/Fe3+ is a redox couple, and a redox pair whose two
    # members are both zero has no potential). Adding either means giving every
    # entry below a real aqueous formation value, referenced the same way the
    # derived ions in ``electrolyte`` are.
    #
    # ⚠⚠ **M3 LANDED THE SOLUBILITY PRODUCT AND THE PREDICTION ABOVE DID NOT COME
    # TRUE. THE REASON IS WORTH KNOWING BECAUSE IT WAS AN ACCIDENT OF A FAILURE.**
    # The prediction assumed a Ksp would be computed from THIS table. Measured, it
    # cannot be -- a naive Ksp on these zeros lands 25-29 decades out with the
    # sign flipping -- so ``properties/solubility_product.py`` refuses this table
    # outright and prices Ksp from ``ion_data`` (conventional aqueous basis) minus
    # ``mineral_data`` (CRC solid basis), neither of which is a provider tier.
    # The engine's precipitation term consumes that Ksp as a NUMBER and never
    # reads a Gf from here, and the enthalpy it releases comes from the same
    # independent pair. So the cation still appears in no equilibrium the kernel
    # evaluates, and every zero below still cancels exactly.
    #
    # ⚠ The condition on the licence is therefore SHARPER than it was, not
    # weaker: *a zero is safe while no consumer reads it once.* What would break
    # it is a mechanic that puts these ions in a rate law or a detailed-balance
    # pair -- electrochemistry still would, and that half of the prediction
    # stands.
    "[Ca+2]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(30.0, 0.0, 0.0, 0.0)),
    "[Mg+2]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(30.0, 0.0, 0.0, 0.0)),
    "[Fe+2]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(30.0, 0.0, 0.0, 0.0)),
    "[Cu+2]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(30.0, 0.0, 0.0, 0.0)),
    "[Zn+2]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(30.0, 0.0, 0.0, 0.0)),
    # Added for M3, so a metathesis has cations to drop. Same argument, same
    # limit. ⚠ Silver's Cp is the CRC aqueous value (21.8 J/(mol K), the same
    # column [Na+]'s 46.4 and [K+]'s 21.8 come from); barium and lead have no
    # Cp(aq) in that tabulation, so they carry the 30.0 placeholder the mineral
    # cations above use and it is labelled here rather than looking sourced.
    "[Ag+]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(21.8, 0.0, 0.0, 0.0)),
    "[Ba+2]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(30.0, 0.0, 0.0, 0.0)),
    "[Pb+2]": ThermoData(0.0, 0.0, _SPECTATOR, Cp_coeffs=(30.0, 0.0, 0.0, 0.0)),
}


# ---------------------------------------------------------------------------
# Curated entries assembled from the two halves in ``formation_data``
# ---------------------------------------------------------------------------
# These are species Joback cannot fragment AT ALL -- aryl aldehydes, formamides,
# sulfoxides, anhydrides, formic acid -- so there is no estimated record to
# overlay measured formation data onto, and they previously had no
# thermochemistry whatsoever. Composing the formation table with the physical
# one gives a complete record, which makes them ordinary curated species with no
# new resolution tier: a full entry still outranks everything, exactly as before.
#
# Assembled rather than transcribed so Hf/Gf have ONE home. Duplicating them
# here would let the two copies drift, and a formation value that disagrees with
# itself depending on which table you read is precisely the class of error the
# cross-checks in ``formation_data`` exist to catch.
_ASSEMBLED = "experimental (CRC/NIST/ATCT); Joback has no groups for this species"


def _assembled_entries() -> dict[str, ThermoData]:
    out: dict[str, ThermoData] = {}
    formation = {**IDEAL_GAS_FORMATION, **DERIVED_GAS_FORMATION}
    for smi, physical in PHYSICAL_PROPERTIES.items():
        if smi not in formation:
            continue
        Hf, Gf = formation[smi]
        out[smi] = ThermoData(
            Hf=Hf, Gf=Gf, source=_ASSEMBLED,
            physical_source="curated measured (CRC/NIST) with a fitted Cp",
            **physical,
        )
    return out


_CURATED_RAW.update(_assembled_entries())


# ---------------------------------------------------------------------------
# The elements, composed in from their one home
# ---------------------------------------------------------------------------
# ``element_data`` is generated from ``chemicals``/``thermo`` with Gf DERIVED
# against the CRC element reference states, so the two halves of every entry
# agree with each other by construction. Composing rather than duplicating is
# the same rule ``_assembled_entries`` follows: a formation value that disagrees
# with itself depending on which table you read is the error the cross-checks
# exist to catch.
#
# The provenance string distinguishes the two cases, because they are not the
# same kind of statement. A gaseous reference state is EXACT and free; a
# condensed one's ideal-gas record is a MEASUREMENT of its sublimation energy.
def _element_entries() -> dict[str, ThermoData]:
    out: dict[str, ThermoData] = {}
    for smi, rec in ELEMENTAL.items():
        out[smi] = ThermoData(
            Hf=rec.Hf, Gf=rec.Gf,
            source=f"{rec.formation_source} [{rec.name}]",
            physical_source=rec.physical_source,
            Cp_coeffs=rec.Cp_coeffs,
            Tb=rec.Tb, Tc=rec.Tc, Pc=rec.Pc, Vc=rec.Vc,
            Hvap=rec.Hvap, Tm=rec.Tm, Hfus=rec.Hfus,
        )
    return out


_CURATED_RAW.update(_element_entries())


# ---------------------------------------------------------------------------
# Measured data overlaid on an otherwise estimated species
# ---------------------------------------------------------------------------
# An overlay substitutes only the properties it measured and leaves the rest of
# Joback's record alone. That is deliberate: replacing the whole record would
# discard good estimates to fix one bad one (Joback's Hfus for benzoic acid is
# 18.07 against a measured 18.02). The provenance string names which halves are
# measured, so a caller can still tell the two apart.
#
# **Melting** is Joback's weakest output by some margin -- benzoic acid 40 K
# low, urea 90 K low -- and the one that matters most, because Tm and Hfus drive
# the solubility law exponentially, so a 40 K miss is nearly a factor of 2 in
# how much dissolves.
#
# **Formation** is the other overlay, in ``formation_data``, which explains
# where its numbers come from and how each was cross-checked. Joback's Hf/Gf
# carry errors big enough to matter on their own (17 kJ/mol for methanol, a
# factor of a thousand in K), but the structural failure is worse: because group
# contributions are additive, the CH3 -> C2H5 difference cancels EXACTLY between
# an alcohol and the ester it makes, so Joback cannot tell homologues apart at
# all. Measured values can.
_CURATED_FUSION: dict[str, tuple[float, float]] = {
    # smiles: (Tm in K, Hfus in kJ/mol)
    "OC(=O)c1ccccc1":  (395.55, 18.02),   # benzoic acid  (Joback: 355.7 K)
    "c1ccc2ccccc2c1":  (353.35, 19.01),   # naphthalene
    "NC(N)=O":         (406.50, 13.90),   # urea          (Joback: 317 K)
    "OC(=O)c1ccccc1O": (432.15, 14.20),   # salicylic acid
}


# ---------------------------------------------------------------------------
# The two halves of a record
# ---------------------------------------------------------------------------
# A ThermoData is two independent things wearing one dataclass:
#
#   FORMATION   Hf, Gf  -- where the species sits on the energy scale
#   PHYSICAL    Tb, Tc, Pc, Vc, Hvap, Tm, Hfus -- how it behaves as a substance
#
# They come from different kinds of source and they used to be resolved as one
# unit, which was the architectural hole this module was restructured to close.
# The old ``get`` consulted Benson only INSIDE the ``else`` branch after Joback
# had already succeeded, and ``_assembled_entries`` required curated formation
# data before a curated PHYSICAL_PROPERTIES entry counted. So there was no path
# that paired a physical half from anywhere with a formation half from Benson --
# and Benson prices acetic anhydride's enthalpy of formation to within 3.7
# kJ/mol of measurement while the provider refused the species outright. The
# value was computed, correct and unreachable.
#
# Resolving the halves SEPARATELY, best source first, fixes that and is also
# just the honest structure -- nothing about a boiling point implies anything
# about an enthalpy of formation:
#
#   FORMATION   curated measured  >  Benson  >  Joback
#   PHYSICAL    curated measured  >  measured Tb + Wilson-Jasperson/Fedors
#                                 >  Joback
#   Cp          curated physical  >  Benson  >  Joback
#   Tm/Hfus     overlaid from _CURATED_FUSION / MEASURED_PHYSICAL on top
#
# Cp needs its own line because it is emitted by the formation ESTIMATORS but
# tabulated with the physical half, so tying it to whichever formation tier won
# would silently drop Benson's Cp for every species that also has a curated Hf.
#
# A fully curated entry in ``_CURATED_RAW`` still short-circuits all of this: it
# is one measured record and splitting it would only invite the two halves to
# drift apart.
_ASSEMBLED_PHYSICAL = "physical half: {}"
_ASSEMBLED_FORMATION = "formation half: {}"


@dataclass(frozen=True)
class _Physical:
    """A resolved physical half, and its provenance."""

    Tb: float | None = None
    Tc: float | None = None
    Pc: float | None = None
    Vc: float | None = None
    Hvap: float | None = None
    Tm: float | None = None
    Hfus: float | None = None
    Cp_coeffs: tuple | None = None
    source: str = ""

    @property
    def usable(self) -> bool:
        """Whether this half can drive a vapour-pressure curve.

        Tb/Tc/Pc are the three the Lee-Kesler chain needs. A half without them
        is not useless -- a species that decomposes before it boils is correctly
        non-volatile, and ``volatility`` handles that -- but it cannot be called
        complete, and the difference has to be visible rather than assumed.
        """
        return None not in (self.Tb, self.Tc, self.Pc)


class ThermochemistryProvider:
    """Resolves molecules to ThermoData, assembling the two halves separately.

    See the block comment above for the resolution order of each half and why
    they are resolved independently.
    """

    def __init__(
        self,
        extra_curated: dict[str, ThermoData] | None = None,
        benson: bool = True,
        measured_physical: bool = True,
        stereo_fallback: bool = True,
    ):
        # ``benson=False`` reproduces the Joback-only basis, kept so the
        # difference can be measured rather than only described -- the same
        # reason ``build_network(liquid_standard_state=False)`` exists.
        # ``measured_physical=False`` does the same for the Wilson-Jasperson /
        # Fedors / measured-Tb route, so the coverage this session added can be
        # switched off and the difference measured rather than asserted.
        # ``stereo_fallback=False`` reads every table on the EXACT canonical
        # spelling and nothing else, which is what this provider did before
        # ``stereo_keys`` existed. Same purpose as the two flags above: the
        # session that added a tier has to be able to measure what it bought.
        self._benson = benson
        self._measured_physical = measured_physical
        self._physical = StereoFallback({
            Molecule.from_smiles(smi).smiles: v
            for smi, v in MEASURED_PHYSICAL.items()
        }, stereo_fallback)
        self._curated_physical = StereoFallback({
            Molecule.from_smiles(smi).smiles: v
            for smi, v in PHYSICAL_PROPERTIES.items()
        }, stereo_fallback)
        # Re-key by canonical SMILES so lookups are form-independent.
        self._curated: dict[str, ThermoData] = {}
        for smi, data in _CURATED_RAW.items():
            self._curated[Molecule.from_smiles(smi).smiles] = data
        for smi, data in (extra_curated or {}).items():
            self._curated[Molecule.from_smiles(smi).smiles] = data
        self._curated = StereoFallback(self._curated, stereo_fallback)
        self._fusion = StereoFallback({
            Molecule.from_smiles(smi).smiles: v
            for smi, v in _CURATED_FUSION.items()
        }, stereo_fallback)
        self._formation = StereoFallback({
            Molecule.from_smiles(smi).smiles: v
            for smi, v in IDEAL_GAS_FORMATION.items()
        }, stereo_fallback)
        self._derived_formation = StereoFallback({
            Molecule.from_smiles(smi).smiles: v
            for smi, v in DERIVED_GAS_FORMATION.items()
        }, stereo_fallback)
        self._cache: dict[str, ThermoData] = {}

    # ---- the physical half --------------------------------------------------

    def _physical_half(self, mol: Molecule, joback) -> _Physical:
        """Resolve Tb/Tc/Pc/Vc/Hvap/Tm/Hfus, best source first."""
        smi = mol.smiles

        # Tier 1: a fully curated physical record, hand-assembled with a fitted
        # Cp. Nine species have one (formic acid, benzaldehyde, DMSO, ...) and
        # they must keep winning: their Tc/Pc/Vc are measured and their Cp is
        # least-squares fitted to the kernel's polynomial form, which neither
        # estimator below can reproduce.
        curated_key = self._curated_physical.key(smi)
        if curated_key is not None:
            return _Physical(
                **self._curated_physical.get(smi),
                source="curated measured (CRC/NIST) with a fitted Cp"
                + fallback_note(smi, curated_key),
            )

        # Tier 2: a measured boiling point, plus critical constants -- measured
        # where the experimental tier has them, Wilson-Jasperson and Fedors
        # otherwise. This is the tier that closes the coverage gap, because
        # Wilson-Jasperson takes Tb as an INPUT: supply a boiling point and the
        # rest follows, for a species Joback cannot fragment at all.
        physical_key = self._physical.key(smi) if self._measured_physical else None
        if physical_key is not None:
            m = self._physical.get(smi)
            if m.Tb is not None:
                try:
                    est = estimate_physical(
                        mol,
                        Tb=m.Tb.value,
                        Tb_source=f"{m.Tb.database} ({m.Tb.tier})",
                        Tc=m.Tc.value if m.Tc else None,
                        Pc=m.Pc.value if m.Pc else None,
                        Vc=m.Vc.value if m.Vc else None,
                        critical_source=(
                            f"{m.Tc.database} ({m.Tc.tier})" if m.Tc else None
                        ),
                        Vc_source=f"{m.Vc.database} ({m.Vc.tier})" if m.Vc else None,
                    )
                except CriticalPropertyError:
                    est = None
                if est is not None:
                    return _Physical(
                        Tb=est.Tb, Tc=est.Tc, Pc=est.Pc, Vc=est.Vc,
                        Hvap=est.Hvap,
                        Tm=m.Tm.value if m.Tm else None,
                        Hfus=m.Hfus.value if m.Hfus else None,
                        Cp_coeffs=None,             # supplied by the formation half
                        source=est.source + fallback_note(smi, physical_key),
                    )
        # Tier 3: Joback, for everything he can fragment.
        if joback is not None:
            half = _Physical(
                Tb=joback.Tb, Tc=joback.Tc, Pc=joback.Pc, Vc=joback.Vc,
                Hvap=joback.Hvap, Tm=joback.Tm, Hfus=joback.Hfus,
                Cp_coeffs=None,                     # supplied by the formation half
                source="Joback",
            )
        else:
            half = _Physical(source="none available")

        # A measured melting point overlays whatever won above. Two cases, and
        # both are real:
        #
        #   * Joback could not give the species a boiling point at all, so
        #     nothing else supplies a fusion pair and the measurement lands.
        #
        # ⚠⚠⚠ THE SECOND HALF OF THAT CASE IS NOT IMPLEMENTED, AND C7 MEASURED
        # WHAT IT COSTS. This comment used to continue "...or his Tm is the weak
        # output it usually is -- a measurement replaces it", and the gate below
        # says ``half.Tb is None``, so a measured melting point NEVER replaces a
        # Joback one: supply a boiling point and Joback's melting point comes
        # with it. **214 species in MEASURED_PHYSICAL hold a Tm that does not
        # reach their record, worst by 877 K** (methotrexate, measured
        # 468.1 K against Joback's 1344.7). Tm drives crystallisation and enters
        # the solubility law exponentially.
        #
        # ⚠⚠ AND THE SENTENCE THAT MADE IT LOOK HARMLESS WAS FALSE. It read
        # "Nothing in the measured table is a species Joback already prices
        # completely (the builder checks and reports), so no existing record's
        # fusion pair moves." ``tools/build_physical_data.py`` classifies each
        # candidate and does NOT exclude on it -- **855 of the 1239 entries are
        # stamped ``Joback: complete`` in the generated file.** A check that
        # reports is not a check that filters.
        #
        # Left as it stands rather than fixed inside a session about spellings:
        # closing it moves 214 melting points at once and the two changes would
        # not be separable. ``validation/stereo_keying.py`` panel 8 is the
        # measurement and the fragility list carries the row.
        #   * NOTHING boils this species. Saccharin, glyphosate, thiourea and
        #     p-toluenesulfonic acid decompose before they boil and no source
        #     tabulates a boiling point for any of them, so non-volatile is the
        #     CORRECT physical answer rather than a shortfall -- and the melting
        #     point still drives crystallisation, which is how those species are
        #     actually handled on a bench.
        overlay_key = self._physical.key(smi) if self._measured_physical else None
        if overlay_key is not None:
            m = self._physical.get(smi)
            if m.Tm is not None and half.Tb is None:
                note = (
                    f"measured Tm ({m.Tm.database}); NO boiling point is "
                    "tabulated for this species in any source consulted, so it "
                    "has no vapour-pressure curve and is correctly non-volatile"
                    + fallback_note(smi, overlay_key)
                )
                half = replace(
                    half,
                    Tm=m.Tm.value,
                    Hfus=m.Hfus.value if m.Hfus else half.Hfus,
                    source=note if half.source == "none available"
                    else f"{half.source}; {note}",
                )
        return half

    # ---- the formation half -------------------------------------------------

    def _formation_half(self, mol: Molecule, joback):
        """Resolve Hf/Gf/Cp, best source first. Returns (Hf, Gf, Cp, source)."""
        smi = mol.smiles

        # Cp is resolved on its own chain -- see the block comment above. Both
        # estimators emit it, so it survives a curated formation entry winning.
        benson = None
        if self._benson:
            try:
                benson = benson_estimate(mol)
            except (BensonError, ValueError):
                benson = None

        Cp = None
        if benson is not None:
            Cp = benson.Cp_coeffs
        elif joback is not None:
            Cp = joback.Cp_coeffs

        # Tier 1: curated measured formation data.
        formation_key = self._formation.key(smi)
        if formation_key is not None:
            Hf, Gf = self._formation.get(smi)
            return (Hf, Gf, Cp, "experimental formation data (CRC/NIST/ATCT)"
                    + fallback_note(smi, formation_key))
        derived_key = self._derived_formation.key(smi)
        if derived_key is not None:
            Hf, Gf = self._derived_formation.get(smi)
            return (Hf, Gf, Cp,
                    "formation data derived from the measured liquid entry"
                    + fallback_note(smi, derived_key))

        # Tier 2: Benson group additivity. BELOW measured data and ABOVE Joback:
        # a better estimator, not a measurement. Measured head to head on the 82
        # curated ideal-gas species, median dGf error 1.56 kJ/mol against
        # Joback's 2.82, mean 2.94 against 6.54, worst 17.1 against 66.7. Benson
        # refuses ~12% of them (unmapped groups, heteroaromatics, anything under
        # three heavy atoms) and those fall through to Joback.
        if benson is not None:
            return (
                benson.Hf, benson.Gf, Cp,
                "Benson group additivity (RMG-database values)",
            )

        # Tier 3: Joback.
        if joback is not None and joback.Hf is not None and joback.Gf is not None:
            return joback.Hf, joback.Gf, Cp, "Joback"
        return None, None, Cp, "none available"

    # ---- the guard ----------------------------------------------------------

    def _refuse_outside_estimator_domain(self, mol: Molecule) -> None:
        """Refuse an ELEMENT or an ION rather than let an estimator price it.

        Joback and Benson are group-contribution methods fitted to NEUTRAL,
        MULTI-ELEMENT molecules. Applied outside that domain they do not fail --
        they return a perfectly well-formed sum that means nothing, and a silent
        wrong answer is the worst failure mode this project has. Three
        instances, all measured in this repo:

            Cl2   Joback: Hf = -74.81 kJ/mol, where the exact answer is 0
                  BY DEFINITION.  ~1e13 in any K involving chlorine.
            F2    Joback: Gf = -440.5 kJ/mol, same class, and still live after
                  Cl2 was fixed -- because Cl2 was fixed SPECIES BY SPECIES.
            S8    Joback: Gf = +275.96 kJ/mol against rhombic sulfur's 0 and
                  gaseous S8's +48.68.  ~e^91 in any K.
            [Cl-] Joback: Gf = -10.43 kJ/mol, against -111.73 from the ion
                  table. So a network built WITHOUT ``electrolyte=True`` priced
                  chloride 101 kJ/mol away from one built with it -- two
                  answers for one species, which is the shape of thing that
                  goes quietly wrong. Bromide is 101.0 apart and fluoride 53.5;
                  IODIDE was priced by Joback in BOTH providers, because HI is
                  not in the pKa table, so it had no second opinion at all.

        The rule is therefore about the estimators' DOMAIN rather than about
        elements: outside it, a value must be curated or refused. That closes
        the class permanently instead of one member of it, which is what the
        species-by-species fix for Cl2 failed to do.

        ⚠ The charge test is on NET charge, not on the presence of formal
        charges. Nitrobenzene is written ``O=[N+]([O-])c1ccccc1`` and is an
        ordinary neutral molecule the estimators must keep pricing, while
        ``[Cl-].[Cl-]`` has net charge -2 and was being priced at -74.74 --
        Cl2's value, for a pair of ions.

        ⚠ And net charge alone is NOT ENOUGH, which is a hole worth naming: a
        salt pair such as ``[Na+].[Cl-]`` sums to zero. It is caught by the
        FRAGMENT test below instead -- a dot-separated SMILES is a MIXTURE of
        molecules, not a molecule, and group additivity is defined for a
        molecule.

        ⚠⚠ **THE FRAGMENT TEST USED TO ASK WHETHER A FRAGMENT WAS CHARGED, AND
        THE NEUTRAL CASE WAS LEFT ALONE ON AN ARGUMENT THAT S7 MEASURED FALSE.**
        The recorded reason was: *"a neutral multi-fragment SMILES (a hydrate, a
        co-crystal) is deliberately left alone: nothing in this project produces
        one, so refusing it would widen the blast radius for no measured gain."*
        Both halves are wrong. ``data/catalog`` carries **eleven** neutral
        multi-fragment SMILES, and the gain is measurable:

            vulcanised-rubber-marker  ``CC(C)=CC.S1SSSSSSS1``
                whole, by Joback   Hf = +273.70 kJ/mol
                its two fragments  -48.83 + 100.42 = +51.59
                                   **+222.11 kJ/mol of nothing**
            nbr-marker                ``CC(C#N).CC=CC``
                whole, by Joback   Hf =  -17.33      fragments +46.16
                                   **-63.49 kJ/mol**

        In an IDEAL GAS there are no intermolecular interactions, so the
        ideal-gas enthalpy of a collection of fragments is the SUM of theirs
        exactly -- an identity, not an estimate. Benson satisfies it because it
        is additive over groups (three of the five that priced came out at
        +0.00, the fourth at -0.82). **Joback does not**: its correlation has a
        constant term and non-linear terms, so applied to two disconnected
        fragments it double-counts the constant and mixes the sums.

        ⚠ So the refusal is now on the FRAGMENT COUNT rather than on the charge,
        and the charge only decides which message is printed. That is a wider
        blast radius, deliberately: it takes five catalog species out of the
        priced set (three rubber markers, the nylon salt, and the vulcanisation
        product), and every one of them was a mixture of two molecules wearing
        one species' name. ⚠ A CURATED entry is unaffected -- ``get`` returns it
        before this guard runs -- so a genuine hydrate with measured data can
        still be priced by curating it, which is the right way in.
        """
        # ---- a mixture of molecules, charged or not ----------------------
        fragments = mol.smiles.split(".")
        if len(fragments) > 1:
            charged = [
                f for f in fragments if Molecule.from_smiles(f).charge != 0
            ]
            if charged:
                # A MINERAL gets its own message, because "no data" would be a
                # FALSE statement: the data is in ``mineral_data``, and what is
                # missing is a dissolution law that can use it. The fusion law --
                # the engine's only route from a solid into solution -- is wrong
                # for an ionic lattice by up to 3 orders of magnitude in EITHER
                # direction, measured. So the honest answer names the
                # representation that does work rather than pretending the
                # species is unknown.
                key = tuple(sorted(fragments))
                for rec in MINERALS.values():
                    if tuple(sorted(rec.ions)) != key:
                        continue
                    raise ValueError(
                        f"refusing to price {mol.smiles!r} as one species: it is "
                        f"{rec.name}, an ionic LATTICE. The only route this "
                        f"engine has from a solid into solution is the "
                        f"ideal-solubility fusion law, and that law is "
                        f"MEASURABLY wrong for a lattice -- it makes NaCl 407x "
                        f"too insoluble and CaCO3 11x too soluble, because Tm "
                        f"and Hfus describe melting while dissolution is "
                        f"lattice into hydrated ions. Charge its IONS instead, "
                        f"individually: {list(rec.ions)}. Its solid-basis "
                        f"formation data IS curated (Gf {rec.Gf_solid} kJ/mol, "
                        f"see properties/mineral_data.py) and is waiting for a "
                        f"solubility product or a solid-phase decomposition to "
                        f"use it."
                    )
                raise ValueError(
                    f"refusing to price {mol.smiles!r} as one species: it is a "
                    f"dot-separated SMILES carrying charged fragments "
                    f"({charged}), i.e. a mixture of ions rather than a "
                    f"molecule, and group additivity is defined for a molecule. "
                    f"Charge each ion separately, with a network built by "
                    f"electrolyte_provider() (or Scenario(electrolyte=True))."
                )
            raise ValueError(
                f"refusing to price {mol.smiles!r} as one species: it is a "
                f"dot-separated SMILES with {len(fragments)} NEUTRAL fragments "
                f"({fragments}), i.e. a mixture of molecules rather than a "
                f"molecule, and group additivity is defined for a molecule. In "
                f"an ideal gas there are no intermolecular interactions, so the "
                f"record for the mixture is the SUM of the fragments' -- an "
                f"identity, not an estimate. Benson honours it and JOBACK DOES "
                f"NOT: it prices 'CC(C)=CC.S1SSSSSSS1' 222.11 kJ/mol above the "
                f"sum of its own two parts, which is ~1e39 in any K. Charge "
                f"each fragment as its own species, or curate the mixture by "
                f"name in properties/formation_data.py if it is a real compound "
                f"with measured data (a curated entry is returned before this "
                f"guard runs)."
            )

        element = element_of(mol)
        if element is not None:
            ref = REFERENCE_STATES.get(element)
            if is_monatomic(mol):
                lattice = LATTICE_ELEMENTS.get(element)
                where = (
                    f" Its standard state is {ref.species} ({lattice})."
                    if ref is not None and lattice
                    else (f" Its standard state is {ref.species}, which this "
                          f"engine holds as {ref.smiles!r} -- charge that "
                          "instead." if ref is not None and ref.smiles else "")
                )
                raise ValueError(
                    f"refusing to price {mol.smiles!r}: a bare element symbol "
                    f"is the most ambiguous way to name an allotrope, and the "
                    f"ideal-gas value for it is the ATOM -- a real number that "
                    f"is not the substance you have in a jar (monatomic carbon "
                    f"is Gf +671 kJ/mol; charcoal is 0).{where} No estimator is "
                    "consulted for an element: see "
                    "properties/element_data.py."
                )
            allotropes = sorted(
                s for s, r in ELEMENTAL.items() if r.element == element
            )
            raise ValueError(
                f"refusing to price {mol.smiles!r}: it is an ELEMENTAL species "
                f"({element}) with no curated entry, and a group-contribution "
                f"estimator applied to an element returns a well-formed number "
                f"that means nothing (Joback prices Cl2 at Hf -74.81 kJ/mol "
                f"where the exact answer is 0 by definition). "
                + (f"Curated allotropes of {element}: {allotropes}. "
                   if allotropes else "")
                + "Add it to properties/element_data.py via "
                  "tools/build_element_data.py."
            )
        if mol.charge != 0:
            raise ValueError(
                f"refusing to price {mol.smiles!r}: it carries a net charge of "
                f"{mol.charge:+d}, and Joback and Benson are fitted to NEUTRAL "
                "molecules -- Joback prices chloride at Gf -10.43 kJ/mol "
                "against the ion table's -111.73, so a network built without "
                "electrolyte support would silently disagree with one built "
                "with it by 101 kJ/mol. An ion is priced from a measured pKa "
                "against this project's own water reference: build the network "
                "with electrolyte_provider() (or Scenario(electrolyte=True)), "
                "and add the pair to properties/electrolyte._PAIRS if it is "
                "not there -- for a CATION the neutral member is the BASE, so "
                "it goes in as AcidPair(<this ion>, <the neutral amine>, pKa)."
            )

    # ---- assembly -----------------------------------------------------------

    def get(self, molecule: Molecule | str) -> ThermoData:
        mol = molecule if isinstance(molecule, Molecule) else Molecule.from_smiles(molecule)
        smi = mol.smiles

        if smi in self._cache:
            return self._cache[smi]

        # A fully curated entry is ONE measured record; splitting it into halves
        # would only let the two drift apart.
        curated_key = self._curated.key(smi)
        if curated_key is not None:
            data = self._curated.get(smi)
            if curated_key != smi:
                data = replace(
                    data, source=data.source + fallback_note(smi, curated_key))
            self._cache[smi] = data
            return data

        # NOTHING BELOW THIS LINE MAY SEE AN ELEMENT OR AN ION. See
        # ``_refuse_outside_estimator_domain``.
        self._refuse_outside_estimator_domain(mol)

        try:
            joback = estimate(mol)
        except JobackError:
            joback = None

        physical = self._physical_half(mol, joback)
        Hf, Gf, Cp, formation_source = self._formation_half(mol, joback)

        if Hf is None or Gf is None:
            raise ValueError(
                f"no thermochemistry available for {smi!r}: no curated entry, "
                f"and no estimator can price its formation "
                f"(physical half: {physical.source}). Joback "
                + ("lacks required contributions"
                   if joback is not None else "cannot fragment it")
                + "; Benson has no value for at least one of its groups."
            )

        # An EMPTY physical half must refuse, even though the formation half
        # resolved. This is the one place the two-half split can go quietly
        # wrong, and it did during development, so the guard is explicit.
        #
        # ``volatility`` treats a record without Tb/Tc/Pc as non-volatile and
        # says "decomposes before it boils" -- correct for a sugar or a
        # guanidine, and a confident lie for acetic anhydride, which boils at
        # 412 K. Before the halves were separated, Joback's refusal raised here
        # and the question never arose; afterwards, a Benson formation half was
        # enough to produce a record that then got silently declared
        # non-volatile. That is precisely the failure mode this project refuses:
        # a silent wrong answer is worse than a loud failure.
        #
        # A melting point is enough to pass. It means the species was looked up
        # and no source tabulates a boiling point for it, which is a finding
        # about the species rather than a hole in our data -- and Tm still
        # drives crystallisation, so the record does real work.
        if not physical.usable and physical.Tm is None:
            raise ValueError(
                f"no thermochemistry available for {smi!r}: its formation half "
                f"resolved ({formation_source}) but there is NO physical half -- "
                "no Tb/Tc/Pc from any source and no measured melting point, so "
                "no vapour-pressure curve can be built. Refusing rather than "
                "returning a record that would be silently treated as "
                "non-volatile. Add a measured boiling point to "
                "properties/physical_data.py (see tools/build_physical_data.py)."
            )

        # Curated fusion data overlays whichever physical half won. Melting is
        # Joback's weakest output by a wide margin -- benzoic acid 40 K low, urea
        # 90 K low -- and the one that matters most, because Tm and Hfus drive
        # the solubility law exponentially, so a 40 K miss is nearly a factor of
        # two in how much dissolves.
        Tm, Hfus = physical.Tm, physical.Hfus
        fusion_source = ""
        fusion_key = self._fusion.key(smi)
        if fusion_key is not None:
            Tm, Hfus = self._fusion.get(smi)
            fusion_source = ("; fusion: experimental Tm/Hfus (CRC/NIST)"
                             + fallback_note(smi, fusion_key))

        data = ThermoData(
            Hf=Hf, Gf=Gf,
            Cp_coeffs=Cp if physical.Cp_coeffs is None else physical.Cp_coeffs,
            Tb=physical.Tb, Tc=physical.Tc, Pc=physical.Pc, Vc=physical.Vc,
            Hvap=physical.Hvap, Tm=Tm, Hfus=Hfus,
            source=(
                f"{_ASSEMBLED_FORMATION.format(formation_source)}; "
                f"{_ASSEMBLED_PHYSICAL.format(physical.source)}{fusion_source}"
            ),
            physical_source=physical.source,
        )
        self._cache[smi] = data
        return data

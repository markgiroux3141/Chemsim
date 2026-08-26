"""Layer 1 -- condensed-phase properties: liquid molar volume and liquid Cp.

Layer 5 needs two things the ideal-gas thermochemistry cannot give it:

  * **molar volume**, because the liquid volume is what turns moles into the
    concentrations the rate law uses -- and what lets a flask boil dry;
  * **liquid heat capacity**, because a vessel's temperature response is set by
    the liquid it contains, and ideal-gas Cp is roughly half the real value.

Both are emitted as cubic polynomials in T, matching the form Joback already uses
for Cp. That is not cosmetic: it means Layer 4 evaluates one polynomial kernel
over one array and never learns that Rackett or Rowlinson-Bondi exist. Anything
non-polynomial (a corresponding-states correlation, in both cases here) is
sampled and fitted at setup time.

Estimation quality, stated honestly:
  * Rackett molar volume is good to a few percent for most organics and ~10% low
    for water, which is anomalous.
  * Rowlinson-Bondi liquid Cp is good (~5%) for non-polar species and poor for
    hydrogen-bonding ones -- it overestimates ethanol by ~40%. Since alcohols,
    water and acids are exactly the solvents this simulator cares about, those
    are curated; Rowlinson-Bondi is the fallback for everything else.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from chemsim.matter import Molecule
from chemsim.properties.thermochemistry import ThermochemistryProvider
from chemsim.properties.volatility import VolatilityProvider

R_CM3_BAR = 83.144626  # cm3 bar / (mol K)
T_REF = 298.15

Cubic = tuple[float, float, float, float]


class CondensedPropertyError(ValueError):
    """Raised when no condensed-phase model can be built for a species."""


@dataclass(frozen=True)
class CondensedData:
    """Liquid-phase properties as cubic-in-T polynomials, with provenance."""

    v_coeffs: Cubic       # L/mol   -- liquid molar volume
    Cp_coeffs: Cubic      # J/(mol K) -- liquid heat capacity
    v_source: str
    Cp_source: str

    def molar_volume(self, T: float) -> float:
        return _poly(self.v_coeffs, T)

    def Cp(self, T: float) -> float:
        return _poly(self.Cp_coeffs, T)


def _poly(c: Cubic, T: float) -> float:
    a, b, cc, d = c
    return a + b * T + cc * T**2 + d * T**3


def fit_cubic(Ts: np.ndarray, ys: np.ndarray) -> Cubic:
    """Exact-form least-squares fit of a + bT + cT^2 + dT^3 (linear in the params).

    The workhorse of the setup/hot-loop split: any property that depends only on
    temperature gets sampled from whatever correlation describes it and handed
    down as four numbers.
    """
    V = np.vander(Ts, 4, increasing=True)
    coeffs, *_ = np.linalg.lstsq(V, ys, rcond=None)
    return tuple(float(x) for x in coeffs)  # type: ignore[return-value]


_fit_cubic = fit_cubic   # historical name, used within this module


def fit_inverse_cubic(Ts: np.ndarray, ys: np.ndarray) -> tuple[Cubic, float]:
    """Least-squares fit of a + b/T + c/T^2 + d/T^3, and the worst residual.

    The van 't Hoff form, extended. Anything that is really a ratio of Boltzmann
    factors -- a Henry constant, an equilibrium constant, an infinite-dilution
    activity coefficient -- is linear in 1/T to leading order and curves gently
    after that, so this basis fits such a quantity an order of magnitude better
    than a plain polynomial in T does. The codebase already relies on the same
    observation for Henry constants, where van 't Hoff turns out to be Antoine
    with C = 0.

    Returns the coefficients and the largest absolute residual in ``ys``, so a
    caller can report a fit that did not take rather than assuming one did.
    """
    M = np.vstack([np.ones_like(Ts), 1.0 / Ts, Ts**-2.0, Ts**-3.0]).T
    coeffs, *_ = np.linalg.lstsq(M, ys, rcond=None)
    residual = float(np.max(np.abs(M @ coeffs - ys))) if len(ys) else 0.0
    return tuple(float(x) for x in coeffs), residual  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Curated liquid heat capacities, J/(mol K) at 298 K
# ---------------------------------------------------------------------------
# Treated as constant over the operating range. That is a real approximation:
# water varies ~1% between 25 and 100 C, but ethanol varies ~30%. It is still far
# better than the estimator for these associating species, and better than using
# the ideal-gas value, which is what the alternative amounts to.
_CURATED_CP = "experimental liquid Cp at 298 K (CRC / NIST), constant"
_CURATED_CP_LIQUID: dict[str, float] = {
    "O": 75.29,           # water
    "CO": 81.1,           # methanol
    "CCO": 112.3,         # ethanol
    "CC(=O)O": 123.1,     # acetic acid
    "CCOC(C)=O": 170.7,   # ethyl acetate
    "COC(C)=O": 141.9,    # methyl acetate
    "CC(C)=O": 125.5,     # acetone
    # ⚠⚠ S10 -- THE TWO METALS, AND THE ESTIMATOR WAS NOT MERELY IMPRECISE HERE:
    # IT RETURNED A NEGATIVE HEAT CAPACITY. get's fit window is the
    # HARDCODED 250-450 K below and every caller takes the default, which is an
    # organic-solvent range. Rowlinson-Bondi is a LIQUID correlation, so for a
    # metal it was being evaluated where there is no liquid and then extrapolated
    # into the range where there is one. Measured, before these two entries:
    #
    #     mercury (liquid 234-630 K)   -25.26 at Tm, -12.62 at 298 K,
    #                                  +22.45 at Tb   against a real 27.98
    #     zinc    (liquid 693-1180 K)  +34.84 at Tm, +462.51 at Tb (15x)
    #                                  against a real 31.38
    #
    # Mercury's has been in the engine since S4 and a NEGATIVE Cp is not an
    # accuracy problem -- adding heat to that liquid LOWERS its temperature. Both
    # are replaced by measurement, and both measurements are unusually clean:
    #   * mercury: CRCSTD 28.000, thermo's "Fit 2023" 27.976 and VDI_TABULAR
    #     28.031 at 298 K -- THREE sources inside 0.2%.
    #   * zinc: the WebBook Shomate liquid curve, whose validity window is
    #     692.73-1180.17 K, i.e. EXACTLY zinc's liquid range, and which is flat
    #     at 31.380 across the whole of it -- so "constant" is this table's
    #     approximation only in name for this row.
    # ⚠ The general fault is NOT fixed: any species whose liquid range falls
    # outside 250-450 K and has no row here is still extrapolated. See
    # get's signature.
    "[Hg]": 27.98,        # mercury -- CRC/VDI/Fit-2023 agree to 0.2%
    "[Zn]": 31.38,        # zinc -- WebBook Shomate, flat over 693-1180 K
}

# Curated liquid molar volumes, L/mol at 298 K (from density and molar mass).
_CURATED_V = "experimental liquid density at 298 K (CRC), constant"
_CURATED_V_LIQUID: dict[str, float] = {
    "O": 0.01807,         # water -- Rackett is ~10% low here, so curate it
    "CO": 0.04071,        # methanol
    "CCO": 0.05868,       # ethanol
    "CC(=O)O": 0.05748,   # acetic acid
    "CCOC(C)=O": 0.09849,  # ethyl acetate
    "CC(C)=O": 0.07395,   # acetone
    # S10 -- the two metals. ⚠ NOT at 298 K for zinc, which is a SOLID there:
    # the value is CRC_INORG_L at 700 K, just above the melting point, because a
    # constant taken outside the liquid range is not this table's convention
    # applied, it is the convention broken. Rackett reads 0.012341 against CRC's
    # 0.009341 at 298 K (+32%) and diverges further over the real liquid range.
    "[Hg]": 0.014822,     # mercury, CRC at 298 K (Rackett was 3% low)
    "[Zn]": 0.009968,     # zinc, CRC at 700 K -- see above
}

# ⚠ S10 -- WHERE A ROW ABOVE IS NOT AT 298 K, OR NOT FROM CRC. The two strings
# above were true of all seven rows in each table and stopped being true when a
# metal arrived: zinc is a SOLID at 298 K, so neither of its constants can be a
# 298 K liquid measurement. Same shape as the shared Antoine stamp
# volatility._CURATED_SOURCE exists to fix -- a provenance string that is
# correct when written and silently wrong after the next addition.
_CURATED_CP_SOURCE: dict[str, str] = {
    "[Hg]": "experimental liquid Cp, CRC 28.000 / VDI 28.031 / thermo Fit-2023 "
            "27.976 at 298 K -- three sources inside 0.2%",
    "[Zn]": "experimental liquid Cp, WebBook Shomate over its OWN validity "
            "window 692.73-1180.17 K, flat at 31.380 across all of it",
}
_CURATED_V_SOURCE: dict[str, str] = {
    "[Zn]": "experimental liquid molar volume, CRC_INORG_L at 700 K -- NOT at "
            "298 K, where zinc is a solid",
}

# A dissolved permanent gas has no liquid state at all -- it is above its critical
# temperature, so Rackett and Rowlinson-Bondi are both meaningless for it (Rackett
# extrapolates off its domain; Rowlinson-Bondi diverges as Tr -> 1). What it does
# have is a *partial molar volume* in solution, which is what actually matters:
# how much room dissolved O2 takes up in the flask. Values are for aqueous
# solution, and are small enough that the choice barely moves the liquid volume.
# Fallbacks for species with no usable critical constants -- ions, and anything
# that decomposes before boiling. Both numbers are deliberately unremarkable: an
# ion's partial molar volume is small and its heat capacity contribution is minor,
# so being approximately right costs little, whereas refusing to model it at all
# would exclude every salt and half the pharmacopoeia.
IONIC_MOLAR_VOLUME = 0.020        # L/mol
IONIC_CP = 75.0                   # J/(mol K)
_IONIC_EST = "nominal ionic partial molar volume (no critical constants available)"
_IONIC_CP_EST = "nominal ionic heat capacity (no critical constants available)"

_DISSOLVED = "partial molar volume in aqueous solution (Wilhelm 1977), constant"
_DISSOLVED_GAS_V: dict[str, float] = {
    "O=O": 0.0310,
    "N#N": 0.0350,
    "[H][H]": 0.0260,
    "[C-]#[O+]": 0.0360,
    "O=C=O": 0.0330,
    "C": 0.0375,
}


def rackett_molar_volume(T: float, Tc: float, Pc: float, Vc: float) -> float:
    """Saturated-liquid molar volume in cm3/mol via the Rackett equation.

        V = Vc * Zc ** ((1 - Tr) ** (2/7)),   Zc = Pc*Vc/(R*Tc)
    """
    Zc = Pc * Vc / (R_CM3_BAR * Tc)
    Tr = min(T / Tc, 0.99)
    return Vc * Zc ** ((1.0 - Tr) ** (2.0 / 7.0))


def rowlinson_bondi_cp_excess(T: float, Tc: float, omega: float) -> float:
    """Cp_liquid - Cp_ideal_gas in J/(mol K), Rowlinson-Bondi corresponding states.

        (CpL - Cp0)/R = 1.45 + 0.45/(1-Tr) + 0.25*omega*
                        [17.11 + 25.2*(1-Tr)**(1/3)/Tr + 1.742/(1-Tr)]
    """
    from chemsim.constants import R

    Tr = min(T / Tc, 0.98)
    u = 1.0 - Tr
    return R * (
        1.45
        + 0.45 / u
        + 0.25 * omega * (17.11 + 25.2 * u ** (1.0 / 3.0) / Tr + 1.742 / u)
    )


class CondensedProvider:
    """Resolves molecules to liquid molar volume and liquid Cp, with provenance."""

    def __init__(
        self,
        thermo: ThermochemistryProvider | None = None,
        volatility: VolatilityProvider | None = None,
    ):
        self._thermo = thermo or ThermochemistryProvider()
        self._vol = volatility or VolatilityProvider(self._thermo)
        self._curated_cp = {
            Molecule.from_smiles(s).smiles: v for s, v in _CURATED_CP_LIQUID.items()
        }
        self._curated_v = {
            Molecule.from_smiles(s).smiles: v for s, v in _CURATED_V_LIQUID.items()
        }
        self._dissolved_v = {
            Molecule.from_smiles(s).smiles: v for s, v in _DISSOLVED_GAS_V.items()
        }
        self._curated_cp_source = {
            Molecule.from_smiles(s).smiles: v
            for s, v in _CURATED_CP_SOURCE.items()
        }
        self._curated_v_source = {
            Molecule.from_smiles(s).smiles: v for s, v in _CURATED_V_SOURCE.items()
        }
        self._cache: dict[str, CondensedData] = {}

    def get(
        self, molecule: Molecule | str, T_lo: float = 250.0, T_hi: float = 450.0
    ) -> CondensedData:
        """Condensed-phase data, with correlations fitted over [T_lo, T_hi]."""
        mol = molecule if isinstance(molecule, Molecule) else Molecule.from_smiles(molecule)
        smi = mol.smiles
        if smi in self._cache:
            return self._cache[smi]

        t = self._thermo.get(mol)
        Ts = np.linspace(T_lo, T_hi, 25)

        # A species above its critical temperature over the operating range is a
        # dissolved gas, not a liquid; both correlations below are off-domain for
        # it, so it takes the curated-solute path instead.
        vol = self._vol.get(mol)
        dissolved = vol.kind == "henry"
        # Ions and decomposing solids: real liquid-phase species, but with no
        # critical constants to drive Rackett or Rowlinson-Bondi.
        nominal = vol.kind == "nonvolatile" and None in (t.Tc, t.Pc, t.Vc)

        # --- molar volume -------------------------------------------------
        if nominal:
            v_coeffs: Cubic = (IONIC_MOLAR_VOLUME, 0.0, 0.0, 0.0)
            v_source = _IONIC_EST
        elif dissolved and smi in self._dissolved_v:
            v_coeffs = (self._dissolved_v[smi], 0.0, 0.0, 0.0)
            v_source = _DISSOLVED
        elif dissolved:
            raise CondensedPropertyError(
                f"{smi!r} is a permanent gas over this range (no liquid state); "
                "it needs a curated partial molar volume in _DISSOLVED_GAS_V"
            )
        elif smi in self._curated_v:
            v_coeffs = (self._curated_v[smi], 0.0, 0.0, 0.0)
            v_source = self._curated_v_source.get(smi, _CURATED_V)
        elif None not in (t.Tc, t.Pc, t.Vc):
            vals = np.array(
                [rackett_molar_volume(T, t.Tc, t.Pc, t.Vc) / 1000.0 for T in Ts]
            )  # cm3/mol -> L/mol
            v_coeffs = _fit_cubic(Ts, vals)
            v_source = "Rackett from Joback Tc/Pc/Vc, fitted"
        else:
            raise CondensedPropertyError(
                f"no liquid molar volume for {smi!r}: needs a curated density or "
                f"Joback Tc/Pc/Vc (have Tc={t.Tc}, Pc={t.Pc}, Vc={t.Vc})"
            )

        # --- liquid heat capacity ----------------------------------------
        if nominal:
            Cp_coeffs: Cubic = (
                t.Cp_coeffs if t.Cp_coeffs is not None else (IONIC_CP, 0.0, 0.0, 0.0)
            )
            Cp_source = _IONIC_CP_EST
        elif dissolved:
            if t.Cp_coeffs is None:
                raise CondensedPropertyError(f"no heat capacity available for {smi!r}")
            # A trace dissolved gas contributes negligibly to the vessel's heat
            # capacity; the ideal-gas value is used and labelled, not smuggled in.
            Cp_coeffs = t.Cp_coeffs
            Cp_source = "ideal-gas Cp (dissolved gas, no liquid state)"
        elif smi in self._curated_cp:
            Cp_coeffs = (self._curated_cp[smi], 0.0, 0.0, 0.0)
            Cp_source = self._curated_cp_source.get(smi, _CURATED_CP)
        elif t.Cp_coeffs is not None and t.Tc is not None and t.Tb is not None and t.Pc is not None:
            from chemsim.properties.volatility import acentric_factor

            omega = acentric_factor(t.Tb, t.Tc, t.Pc)
            vals = np.array(
                [
                    _poly(t.Cp_coeffs, T) + rowlinson_bondi_cp_excess(T, t.Tc, omega)
                    for T in Ts
                ]
            )
            Cp_coeffs = _fit_cubic(Ts, vals)
            Cp_source = f"ideal gas + Rowlinson-Bondi (omega={omega:.3f}), fitted"
        else:
            raise CondensedPropertyError(f"no heat capacity available for {smi!r}")

        data = CondensedData(v_coeffs, Cp_coeffs, v_source, Cp_source)
        self._cache[smi] = data
        return data

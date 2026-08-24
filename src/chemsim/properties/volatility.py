"""Layer 1 -- volatility: how strongly a species wants to be in the vapour.

Every species gets ONE functional form, Antoine:

    log10(P / bar) = A - B / (C + T)

and the whole of Layer 5 asks it exactly one question: given a liquid mole
fraction x_i, what partial pressure is that in equilibrium with?

    p_eq,i = x_i * 10 ** (A - B/(C + T))

For a *condensable* species that coefficient is its vapour pressure and the
relation is Raoult's law. For a *permanent gas* (O2, N2 -- species above their
critical temperature, which have no vapour pressure at all) it is instead a
Henry's-law constant, and the very same expression is Henry's law. Two different
physical laws, one array in the hot loop.

That collapse is deliberate, and it is the same trick as everywhere else in this
codebase: do the model-specific reasoning ONCE at setup, hand the numeric core a
uniform array. Henry constants fall out especially cleanly, because van 't Hoff

    H(T) = H_ref * exp(-C_vh * (1/T - 1/T_ref))

is *already* Antoine-shaped with C = 0 -- no fitting, just algebra.

Three sources, in preference order, each tagged on the result:
  1. curated Antoine constants (NIST) for the solvents that actually matter;
  2. curated Henry constants for permanent gases;
  3. Lee-Kesler estimation from Joback's Tb/Tc/Pc, fitted to Antoine form -- so a
     molecule nobody has ever tabulated still gets a vapour pressure curve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from chemsim.matter import Molecule
from chemsim.properties.critical import (
    P_ATM_BAR,
    CriticalPropertyError,
    acentric_factor,
    lee_kesler_psat,
)
from chemsim.properties.thermochemistry import ThermochemistryProvider

T_REF = 298.15

# ``acentric_factor`` and ``lee_kesler_psat`` are re-exported rather than defined
# here. They moved to ``properties.critical`` to break a cycle: this module
# builds a provider and so imports ``thermochemistry``, while
# ``thermochemistry`` now needs an enthalpy of vaporisation derived from the
# Lee-Kesler curve for a record it assembles from estimated critical constants.
# ``critical`` depends on nothing but ``matter``, so both can use it. The names
# stay exported from here because that is where every caller already looks.
__all__ = [
    "P_ATM_BAR", "T_REF", "Volatility", "VolatilityError", "VolatilityProvider",
    "acentric_factor", "lee_kesler_psat", "NONVOLATILE_A",
    "HENRY_REFERENCE_SOLVENT",
]


class VolatilityError(CriticalPropertyError):
    """Raised when no volatility model can be built for a species.

    A subclass of ``CriticalPropertyError`` because the two failures are the same
    failure seen from two layers: a vapour-pressure curve cannot exist without
    critical constants. Callers that want either can catch the base type, and
    ``except VolatilityError`` keeps meaning exactly what it used to for anything
    this module raises. Note that ``acentric_factor`` now lives in
    ``properties.critical`` and so raises the BASE type when called directly.
    """


@dataclass(frozen=True)
class Volatility:
    """Antoine-form coefficients plus provenance. ``P`` is in bar, ``T`` in K."""

    A: float
    B: float
    C: float
    source: str
    kind: str                 # "vapor_pressure" | "henry" | "nonvolatile"
    T_min: float | None = None
    T_max: float | None = None
    # For a Henry's-law entry only: the solvent the constant was measured in.
    # A Henry constant is not a property of the solute alone, and recording which
    # solvent it belongs to is what lets the activity model transfer it to a
    # different one instead of silently applying an aqueous number everywhere.
    reference_solvent: str | None = None

    def coefficient(self, T: float) -> float:
        """The Antoine value at T (bar): vapour pressure, or Henry constant."""
        denom = self.C + T
        if denom <= 0.0:
            return 0.0
        return 10.0 ** (self.A - self.B / denom)

    @property
    def condensable(self) -> bool:
        return self.kind == "vapor_pressure"

    @property
    def volatile(self) -> bool:
        """False for species that never reach the vapour at all -- ions, and
        anything that decomposes before it boils."""
        return self.kind != "nonvolatile"


# ---------------------------------------------------------------------------
# Curated data
# ---------------------------------------------------------------------------

# NIST Antoine constants, log10(P/bar) = A - B/(C+T), T in K.
_NIST = "experimental Antoine (NIST WebBook)"
_CURATED_ANTOINE: dict[str, tuple[float, float, float, float, float]] = {
    # smiles: (A, B, C, T_min, T_max)
    "O":         (5.40221, 1838.675, -31.737, 255.9, 373.0),   # water
    "CO":        (5.20409, 1581.341, -33.500, 288.0, 357.0),   # methanol
    "CCO":       (5.37229, 1670.409, -40.191, 293.0, 366.0),   # ethanol
    "CC(=O)O":   (4.68206, 1642.540, -39.764, 290.0, 391.0),   # acetic acid
    "CCOC(C)=O": (4.22809, 1245.702, -55.189, 289.0, 349.0),   # ethyl acetate
    "COC(C)=O":  (4.18821, 1164.426, -52.690, 275.0, 330.0),   # methyl acetate
    "CC(C)=O":   (4.42448, 1312.253, -32.445, 259.0, 508.0),   # acetone
    "C=C":       (3.87261,  584.146,  -18.307, 149.0, 188.0),  # ethylene
}

# Henry's law constants for permanent gases IN WATER, as H(T_ref) in bar per unit
# mole fraction, plus the van 't Hoff slope C_vh = -d ln(H) / d(1/T) in K.
# Source: Sander, R. (2015), "Compilation of Henry's law constants", ACP 15, 4399,
# converted to the bar/mole-fraction convention.
#
# These are measured in WATER, which is recorded on each entry rather than left
# implicit. The activity model transfers them to another solvent through the
# ratio of infinite-dilution activity coefficients, so a vessel whose solvent is
# ethanol no longer silently gets the aqueous number.
_SANDER = "experimental Henry constant in water (Sander 2015)"
HENRY_REFERENCE_SOLVENT = "O"     # water
_CURATED_HENRY: dict[str, tuple[float, float]] = {
    # smiles: (H_298 in bar, van 't Hoff slope in K)
    "O=O":       (4.26e4, 1700.0),   # O2
    "N#N":       (8.65e4, 1300.0),   # N2
    "[H][H]":    (7.10e4,  500.0),   # H2
    "[C-]#[O+]": (5.80e4, 1300.0),   # CO
    "O=C=O":     (1.63e3, 2400.0),   # CO2
}


def _henry_to_antoine(H_ref: float, C_vh: float) -> tuple[float, float, float]:
    """van 't Hoff -> Antoine coefficients, exactly (no fit involved).

        H(T) = H_ref * exp(-C_vh * (1/T - 1/T_ref))
        log10 H = [log10 H_ref + C_vh/(ln10 * T_ref)] - [C_vh/ln10] / T

    which is Antoine with C = 0.
    """
    B = C_vh / math.log(10.0)
    A = math.log10(H_ref) + B / T_REF
    return A, B, 0.0


# ---------------------------------------------------------------------------
# Lee-Kesler estimation, for everything not curated
# ---------------------------------------------------------------------------


def _fit_antoine(
    Ts: np.ndarray, Ps: np.ndarray
) -> tuple[float, float, float]:
    """Least-squares fit of Antoine to (T, P) samples, in log10 space.

    Fitting in log space (rather than on P) weights the low-pressure end properly
    -- which is the end that decides whether a contaminant slowly evaporates.
    """
    y = np.log10(Ps)

    # Initial guess: two-point Clausius-Clapeyron, i.e. Antoine with C = 0.
    i, j = 0, len(Ts) - 1
    B0 = (y[i] - y[j]) / (1.0 / Ts[j] - 1.0 / Ts[i])
    A0 = y[i] + B0 / Ts[i]

    def residual(p):
        A, B, C = p
        return A - B / (C + Ts) - y

    # C is bounded away from -T_min so the pole can never land inside the range.
    lo = -0.7 * float(Ts.min())
    fit = least_squares(
        residual, x0=[A0, B0, 0.0], bounds=([-50.0, 0.0, lo], [50.0, 1.0e5, 500.0])
    )
    return float(fit.x[0]), float(fit.x[1]), float(fit.x[2])


# A non-volatile species still needs Antoine coefficients, because the kernel
# evaluates one expression for everything. Giving it A = -30 makes its saturation
# pressure 1e-30 bar, which is zero for every practical purpose and costs no
# special case in the hot loop.
NONVOLATILE_A = -30.0
_IONIC = "non-volatile: charged species do not enter the vapour phase"
_NO_BOIL = (
    "non-volatile: no boiling point could be estimated (decomposes before it boils)"
)


class VolatilityProvider:
    """Resolves molecules to Antoine-form volatility: curated first, then estimated."""

    def __init__(
        self,
        thermo: ThermochemistryProvider | None = None,
        extra_curated: dict[str, Volatility] | None = None,
    ):
        self._thermo = thermo or ThermochemistryProvider()
        self._curated: dict[str, Volatility] = {}

        for smi, (A, B, C, tmin, tmax) in _CURATED_ANTOINE.items():
            key = Molecule.from_smiles(smi).smiles
            self._curated[key] = Volatility(
                A, B, C, _NIST, "vapor_pressure", T_min=tmin, T_max=tmax
            )
        for smi, (H_ref, C_vh) in _CURATED_HENRY.items():
            key = Molecule.from_smiles(smi).smiles
            A, B, C = _henry_to_antoine(H_ref, C_vh)
            self._curated[key] = Volatility(
                A, B, C, _SANDER, "henry",
                reference_solvent=Molecule.from_smiles(
                    HENRY_REFERENCE_SOLVENT
                ).smiles,
            )
        for smi, vol in (extra_curated or {}).items():
            self._curated[Molecule.from_smiles(smi).smiles] = vol

        self._cache: dict[str, Volatility] = {}

    @property
    def thermo(self) -> ThermochemistryProvider:
        """The formation data these vapour pressures were estimated against.

        Exposed because a standard-state shift is a statement about the gap
        between two bases, so whatever computes it needs BOTH the volatility and
        the gas-phase data it is shifting -- and they must be the same records
        the Lee-Kesler fit above used, not a second provider that might resolve
        a species differently.
        """
        return self._thermo

    def get(self, molecule: Molecule | str) -> Volatility:
        mol = molecule if isinstance(molecule, Molecule) else Molecule.from_smiles(molecule)
        smi = mol.smiles

        if smi in self._cache:
            return self._cache[smi]
        if smi in self._curated:
            vol = self._curated[smi]
        elif mol.charge != 0:
            # An ion has no vapour pressure worth the name. Salts do boil, but far
            # above any temperature this simulator cares about, and they travel as
            # ion pairs rather than as the bare ion in solution.
            vol = Volatility(NONVOLATILE_A, 0.0, 0.0, _IONIC, "nonvolatile")
        else:
            try:
                vol = self._estimate(mol)
            except VolatilityError as exc:
                # Rather than refusing to model the species at all, treat it as
                # non-volatile and say so. Plenty of real compounds -- sugars,
                # most drugs, anything with a guanidine -- decompose before they
                # boil, and "stays in the flask" is the correct behaviour for them.
                vol = Volatility(
                    NONVOLATILE_A, 0.0, 0.0, f"{_NO_BOIL} [{exc}]", "nonvolatile"
                )
        self._cache[smi] = vol
        return vol

    def _estimate(self, mol: Molecule) -> Volatility:
        t = self._thermo.get(mol)
        if t.Tb is None or t.Tc is None or t.Pc is None:
            raise VolatilityError(
                f"cannot build a volatility model for {mol.smiles!r}: needs "
                f"Tb/Tc/Pc (have Tb={t.Tb}, Tc={t.Tc}, Pc={t.Pc}). Add a curated "
                "Antoine or Henry entry."
            )
        if t.Tb >= t.Tc:
            raise VolatilityError(
                f"{mol.smiles!r}: estimated Tb={t.Tb:.1f} K is above Tc={t.Tc:.1f} K"
            )

        try:
            omega = acentric_factor(t.Tb, t.Tc, t.Pc)
        except CriticalPropertyError as exc:
            # Raised as a VolatilityError so callers keep their one exception
            # type; the underlying complaint is that Tb is not below Tc.
            raise VolatilityError(str(exc)) from None

        # Fit over a bench-realistic window bracketing the boiling point, kept
        # inside the correlation's valid range (it degrades badly near Tc).
        T_lo = max(0.30 * t.Tc, t.Tb - 120.0, 150.0)
        T_hi = min(0.95 * t.Tc, t.Tb + 120.0)
        if T_hi <= T_lo:
            T_lo, T_hi = 0.5 * t.Tc, 0.9 * t.Tc

        Ts = np.linspace(T_lo, T_hi, 40)
        Ps = np.array([lee_kesler_psat(T, t.Tc, t.Pc, omega) for T in Ts])
        A, B, C = _fit_antoine(Ts, Ps)

        # Name the provenance of Tb/Tc/Pc rather than assuming Joback supplied
        # them -- for a species Joback cannot fragment they are measured, and a
        # source string that says otherwise is exactly the kind of quiet
        # mislabelling the provenance discipline exists to prevent. The record
        # carries the physical half's provenance as its own field precisely so
        # this does not have to be inferred from prose.
        origin = t.physical_source or (
            "measured" if t.source.startswith("experimental") else "Joback"
        )
        return Volatility(
            A, B, C,
            source=f"Lee-Kesler from {origin} Tb/Tc/Pc (omega={omega:.3f}), "
                   "fitted to Antoine",
            kind="vapor_pressure",
            T_min=T_lo,
            T_max=T_hi,
        )

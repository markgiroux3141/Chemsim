"""Layer 1 -- Joback group-contribution estimation.

Estimates thermochemical and critical properties for a molecule from its graph
structure alone. Two steps:

  1. FRAGMENT the molecule into Joback groups -- shared machinery, see
     ``properties/fragmentation.py``. Groups are matched in priority order and
     greedily claim disjoint atom sets, so a carboxylic acid is claimed by -COOH
     before -OH/>C=O can split it, and coverage is verified against the formula
     so an uncovered molecule fails loudly instead of returning nonsense.

  2. APPLY the additive formulas to the group counts.

This is the generalization mechanism for *properties*, mirroring how templates
generalize *reactions*: a novel molecule gets a plausible property estimate from
its structure, with no lookup entry required.
"""

from __future__ import annotations

from dataclasses import dataclass

from chemsim.matter import Molecule
from chemsim.properties import joback_data as jd
from chemsim.properties.fragmentation import FragmentationError
from chemsim.properties.fragmentation import fragment as _fragment


class JobackError(FragmentationError):
    """Raised when a molecule cannot be fully fragmented into Joback groups."""


@dataclass
class JobackResult:
    counts: dict[int, int]          # group_id -> occurrences
    Tb: float | None                # K, normal boiling point
    Tm: float | None                # K, normal melting point
    Tc: float | None                # K
    Pc: float | None                # bar
    Vc: float | None                # cm3/mol
    Hf: float | None                # kJ/mol, ideal gas, 298.15 K
    Gf: float | None                # kJ/mol, ideal gas, 298.15 K
    Hvap: float | None              # kJ/mol, enthalpy of vaporization at Tb
    Hfus: float | None              # kJ/mol, enthalpy of fusion at Tm
    Cp_coeffs: tuple[float, float, float, float] | None  # J/(mol K)

    def Cp(self, T: float) -> float | None:
        if self.Cp_coeffs is None:
            return None
        a, b, c, d = self.Cp_coeffs
        return a + b * T + c * T**2 + d * T**3


def fragment(molecule: Molecule) -> dict[int, int]:
    """Partition a molecule into Joback groups; raise if coverage is incomplete."""
    try:
        return _fragment(
            molecule, jd.GROUPS_BY_PRIORITY, jd.GROUPS_BY_ID, method="Joback"
        )
    except FragmentationError as exc:
        raise JobackError(str(exc)) from None


def _sum(counts: dict[int, int], attr: str) -> float | None:
    """Additive sum of a group attribute; None if any present group lacks it."""
    total = 0.0
    for gid, n in counts.items():
        val = getattr(jd.GROUPS_BY_ID[gid], attr)
        if val is None:
            return None
        total += n * val
    return total


def estimate(molecule: Molecule) -> JobackResult:
    """Estimate properties for a molecule via Joback group contributions."""
    counts = fragment(molecule)
    n_atoms = sum(molecule.element_counts().values())  # total atoms incl H

    tb_sum = _sum(counts, "Tb")
    Tb = jd.TB0 + tb_sum if tb_sum is not None else None

    tm_sum = _sum(counts, "Tm")
    Tm = jd.TM0 + tm_sum if tm_sum is not None else None

    tc_sum = _sum(counts, "Tc")
    Tc = None
    if Tb is not None and tc_sum is not None:
        denom = 0.584 + 0.965 * tc_sum - tc_sum**2
        Tc = Tb / denom if denom > 0 else None

    pc_sum = _sum(counts, "Pc")
    Pc = None
    if pc_sum is not None:
        Pc = (0.113 + 0.0032 * n_atoms - pc_sum) ** -2  # bar

    vc_sum = _sum(counts, "Vc")
    Vc = jd.VC0 + vc_sum if vc_sum is not None else None

    hf_sum = _sum(counts, "Hform")
    Hf = jd.HF0 + hf_sum if hf_sum is not None else None

    gf_sum = _sum(counts, "Gform")
    Gf = jd.GF0 + gf_sum if gf_sum is not None else None

    # Hvap is Joback's value AT the normal boiling point (not at 298 K) -- the
    # phase model rescales it to other temperatures via Watson.
    hv_sum = _sum(counts, "Hvap")
    Hvap = jd.HVAP0 + hv_sum if hv_sum is not None else None

    hfus_sum = _sum(counts, "Hfus")
    Hfus = jd.HFUS0 + hfus_sum if hfus_sum is not None else None

    a, b, c, d = (_sum(counts, x) for x in ("Cpa", "Cpb", "Cpc", "Cpd"))
    Cp_coeffs = None
    if None not in (a, b, c, d):
        Cp_coeffs = (
            a + jd.CPA0, b + jd.CPB0, c + jd.CPC0, d + jd.CPD0,
        )

    return JobackResult(counts, Tb, Tm, Tc, Pc, Vc, Hf, Gf, Hvap, Hfus, Cp_coeffs)

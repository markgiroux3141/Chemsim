"""Layer 1 -- M3: a SOLUBILITY PRODUCT, priced from two tables on one basis.

``AgNO3 + NaCl -> AgCl(down)`` is the whole "add A to B and it goes cloudy" class
of play. For a lattice ``M_a X_b(s) <=> a M(+) + b X(-)``:

    dG_diss = a Gf(M+) + b Gf(X-) - Gf_solid       and    Ksp = exp(-dG/RT)

Both halves are formation values from the elements, so the subtraction means
something **only if both are on the same basis**. That sentence is the entire
history of this module.

## THE TWO MEASUREMENTS, IN ORDER, BECAUSE THE SECOND OVERTURNED THE FIRST

**First (2026-08-23): every lattice REFUSED, and the refusal was right.** The
only ion values in the project were ``thermochemistry``'s spectator zeros and
``electrolyte``'s pKa-derived anions. Measured over the then-13 minerals, a naive
Ksp returned a float for **9 of them and was 25-29 decades out with the sign
flipping** -- blue vitriol came out at 76 mol/L, denser than the crystal.

The cause is worth keeping even though the blockage is gone: **a spectator
cancels from an equilibrium only when it appears on BOTH sides.** Every proton
transfer has the cation unchanged across the arrow, which is why ``[Na+] = 0.0``
is exactly right there and why the five pH invariants hold. A solubility product
is the one consumer where it appears ONCE, so the whole hydration Gibbs energy
the zero stands in for lands in ``dG_diss`` -- ~262 kJ/mol for Na+, **46
decades**. *A zero is not data; it is an assertion about the consumers.*

**Second (2026-08-23, same arc): the blocker was not a curation job.** The first
measurement also recorded that the fix could not be automated, because
``chemicals`` "has no aqueous ion values and hands back the GAS-PHASE ion" --
``Hfs``/``S0s``/``Hfl`` all ``None`` for Na+, ``Hfg`` = +609343 J/mol.

**That was true of the FUNCTIONS and false of the PACKAGE.** ``chemicals`` 1.5.2
ships ``Electrolytes/CRC Thermodynamic Properties of Aqueous Ions.tsv``: 173
ions, one compilation, on the conventional ``Gf(H+,aq) = 0`` scale, which no
accessor function reads. It is now ``properties/ion_data.py`` -- 58 ions, each
cross-checked by re-deriving its ``Gf`` from its own ``Hf`` and ``S(aq)`` against
the element reference states (worst residual 0.85 kJ/mol, tolerance 1.0).

**A REFUSAL FROM AN API IS NOT EVIDENCE THAT THE DATA IS ABSENT** -- the mirror
image of this project's older rule that a *successful* call can be a wrong
answer, and it cost a milestone's worth of planning.

## WHAT IT PRODUCES NOW, MEASURED AGAINST THE SOLUBILITIES ALREADY IN THE REPO

``mineral_data`` carries a measured 298 K solubility for five salts, entered for
the fusion-law verdict long before this module existed. Against those, with
IDEAL activities and no fitting of any kind:

| mineral | log10 Ksp | s predicted / M | s measured / M | ratio |
|---|---:|---:|---:|---:|
| rock salt | +1.57 | 6.09 | 6.15 | **0.99** |
| potash | +5.10 | 31.5 | 8.03 | 3.92 |
| soda ash | +0.83 | 1.19 | 2.06 | 0.58 |
| saltpetre | -0.01 | 0.99 | 3.51 | 0.28 |
| calcite | -8.35 | 6.67e-05 | 1.40e-04 | 0.48 |

**Every one inside a factor of 4, over five decades of solubility**, against
25-29 decades before. That is the "at least three salts within a stated factor"
clause of M3's *done when*, and the stated factor is **4**.

⚠ **The residual factor of 4 has a name and it is not tuning: gamma.** These are
infinite-dilution standard-state values and ``solubility()`` assumes activity
coefficients of 1. At 6 mol/L they are not 1 and nothing here pretends
otherwise. The reductio is in the table above the fold: caustic potash comes out
at **2.2e5 mol/L**, which is not a solubility, it is the ideal-activity law being
extrapolated ten decades past where it means anything. So:

⚠ **``Ksp`` IS THE PRODUCT; ``solubility()`` IS A SCALE.** Above roughly
``DILUTE_LIMIT`` the returned concentration is an order of magnitude, not a
value, and ``SolubilityProduct.dilute`` says which side of that line it is on.
The engine term consumes ``Ksp`` and never ``solubility()`` -- the driving force
``Q/Ksp`` is what precipitation is gated on, and a salt this soluble simply never
reaches it.

## WHAT STILL REFUSES, AND WHY EACH REFUSAL IS A FACT ABOUT CHEMISTRY

* **quicklime**, on ``[O-2]``. The oxide ion is not in the CRC aqueous table
  because it does not exist in water: CaO does not dissolve to Ca2+ + O2-, it
  HYDRATES to Ca(OH)2 and then that dissolves. Refusing is the right answer and
  a Ksp for CaO would be a confident answer to a question with no meaning.
* **chrome yellow (PbCrO4)**, before it even reaches here -- ``mineral_data``
  refuses the lattice because CRC has its Hfs and no S0s in any shared database.
  A named pigment target, refused on the lattice half rather than the ion half,
  which is the first time that has happened.

## THE BASIS GUARD, WHICH IS THE ONE THING THIS MODULE MUST NOT GET WRONG

``ion_data`` and ``electrolyte`` price the same ions on **different zeros** --
chloride is -131.20 in one and -111.73 in the other, worth 3.4 decades of Ksp.
So this module takes a mapping of ``AqueousIon`` and **refuses anything else by
name**, rather than accepting any object with a ``.get``. Passing the electrolyte
provider here is a mistake that would otherwise return a plausible number.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from chemsim.constants import R
from chemsim.properties.ion_data import AQUEOUS_IONS, AqueousIon
from chemsim.properties.mineral_data import MINERALS, MineralRecord

T_REF = 298.15

# Above this concentration the ideal-activity root is an order of magnitude
# rather than a value -- see the module docstring. Not a cutoff the code
# enforces; a line the RESULT reports which side of.
DILUTE_LIMIT = 1.0              # mol/L

# The factor the five measured salts actually come in at. Kept as a constant so
# `validation/` and the tests measure against one number rather than three
# copies of a remembered one.
MEASURED_FACTOR = 4.0


class UnpricedLattice(ValueError):
    """A lattice whose dissolution cannot be priced. Raised with the reason."""


@dataclass(frozen=True)
class SolubilityProduct:
    """One lattice's dissolution equilibrium, on ONE basis or not at all."""

    mineral: str
    ions: tuple[str, ...]
    T: float
    dG_diss: float          # kJ/mol, lattice -> dissolved ions
    dH_diss: float          # kJ/mol, for the van't Hoff slope
    ln_Ksp: float
    source: str

    @property
    def Ksp(self) -> float:
        # ⚠ Returned as a log as well, and the log is the one to compare on. A
        # Ksp of 1e-110 is representable and a Ksp of 1e+400 is not, and the
        # first measurement of this quantity produced both signs of that problem.
        return math.exp(self.ln_Ksp)

    def solubility(self) -> float:
        """s in mol/L for a stoichiometric dissolution, IDEAL activities.

        ``Ksp = prod (nu_i s)^nu_i``, so ``s = (Ksp / prod nu_i^nu_i)^(1/sum
        nu_i)``.

        ⚠ Ideal because there is no ionic-strength model in this project
        (Debye-Huckel is on the backlog and `chemsim-ion-transfer` says why a
        Born term is not a substitute). Sound to a factor of ~4 at the dilute
        end -- see the module docstring's five-salt table -- and meaningless
        above ``DILUTE_LIMIT``, which ``dilute`` reports.
        """
        counts: dict[str, int] = {}
        for ion in self.ions:
            counts[ion] = counts.get(ion, 0) + 1
        total = sum(counts.values())
        ln_pref = sum(c * math.log(c) for c in counts.values())
        return math.exp((self.ln_Ksp - ln_pref) / total)

    @property
    def dilute(self) -> bool:
        """Is the ideal-activity solubility inside the range it means anything?"""
        return self.solubility() <= DILUTE_LIMIT


def _check_basis(ions) -> Mapping[str, AqueousIon]:
    """Refuse anything that is not an aqueous-basis ion table, by name.

    ⚠ The one guard this module cannot do without. ``electrolyte``'s provider
    answers ``get("[Cl-]")`` with a perfectly good number on a DIFFERENT zero,
    and subtracting it from a CRC lattice is 3.4 decades of Ksp that arrives
    looking reasonable. So the type is checked rather than the interface.
    """
    if not isinstance(ions, Mapping):
        raise TypeError(
            f"solubility_product needs a MAPPING of aqueous-basis ions "
            f"(chemsim.properties.ion_data.AQUEOUS_IONS), got "
            f"{type(ions).__name__}. A ThermochemistryProvider will answer, but "
            f"on electrolyte's pKa zero -- chloride reads -111.73 there against "
            f"-131.20 on the conventional aqueous scale, which is 3.4 decades of "
            f"Ksp arriving as a plausible number."
        )
    bad = [k for k, v in ions.items() if not isinstance(v, AqueousIon)]
    if bad:
        raise TypeError(
            f"solubility_product needs AqueousIon records on the conventional "
            f"Gf(H+,aq) = 0 basis; {bad[:3]} are "
            f"{type(ions[bad[0]]).__name__}. A ThermoData is on the IDEAL-GAS "
            f"basis or on electrolyte's pKa zero, and neither can be subtracted "
            f"from a CRC lattice Gf."
        )
    return ions


def _ion_verdict(ion: str, ions: Mapping[str, AqueousIon]) -> str | None:
    """Why ``ion`` cannot enter a Ksp, or None if it can."""
    if ion in ions:
        return None
    return (
        f"{ion} has no entry in the aqueous-basis ion table. Either it is not in "
        f"the CRC compilation, or its row failed the cross-check that re-derives "
        f"Gf from that row's own Hf and S(aq). !! Some of these refusals are "
        f"CHEMISTRY rather than gaps: [O-2] is absent because the oxide ion does "
        f"not exist in water -- an oxide hydrates to the hydroxide and that "
        f"dissolves."
    )


def lattice_verdicts(
    ions: Mapping[str, AqueousIon] = AQUEOUS_IONS, minerals: dict = MINERALS
) -> dict[str, list[str]]:
    """Per mineral, every reason its Ksp cannot be priced. Empty list = it can.

    Exists so the verdict is DATA rather than prose: `validation/` re-measures
    it, a test pins it, and it cannot go stale the way the docstring above could.
    That mattered more than expected -- the verdict it recorded has already been
    overturned once.
    """
    _check_basis(ions)
    out: dict[str, list[str]] = {}
    for name, record in minerals.items():
        seen: list[str] = []
        for ion in dict.fromkeys(record.ions):
            why = _ion_verdict(ion, ions)
            if why is not None:
                seen.append(why)
        out[name] = seen
    return out


def solubility_product(
    mineral: str | MineralRecord,
    ions: Mapping[str, AqueousIon] = AQUEOUS_IONS,
    T: float = T_REF,
) -> SolubilityProduct:
    """``Ksp`` for a lattice against the aqueous ion table, or REFUSE by name.

    ``dG(T)`` is van't Hoff from the 298 K pair, i.e. ``dCp = 0``. ⚠ Stated
    rather than hidden. ``ion_data`` does carry ``Cp(aq)`` for some ions and
    ``mineral_data`` carries none for the lattice, so the honest form is not
    available on both halves and half a correction is worse than none.
    """
    _check_basis(ions)
    record = MINERALS[mineral] if isinstance(mineral, str) else mineral
    name = record.name

    reasons = [
        why
        for ion in dict.fromkeys(record.ions)
        if (why := _ion_verdict(ion, ions)) is not None
    ]
    if reasons:
        joined = "\n  - ".join(reasons)
        raise UnpricedLattice(
            f"refusing to price the solubility product of {name!r} "
            f"({' + '.join(record.ions)}):\n  - {joined}\n"
            f"The LATTICE half is sound -- Gf_solid = {record.Gf_solid:g} kJ/mol, "
            f"{record.source}."
        )

    dG = -record.Gf_solid
    dH = -record.Hf_solid
    for ion in record.ions:
        data = ions[ion]
        dG += data.Gf
        dH += data.Hf
    dS = (dH - dG) / T_REF                       # kJ/(mol K), from the 298 K pair
    dG_T = dH - T * dS
    return SolubilityProduct(
        mineral=name,
        ions=tuple(record.ions),
        T=T,
        dG_diss=dG_T,
        dH_diss=dH,
        ln_Ksp=-dG_T * 1000.0 / (R * T),
        source=(
            f"lattice {record.source}; ions on the conventional Gf(H+,aq) = 0 "
            f"basis from ion_data"
        ),
    )


def measured_agreement(
    ions: Mapping[str, AqueousIon] = AQUEOUS_IONS,
) -> dict[str, tuple[float, float, float]]:
    """``mineral -> (s predicted, s measured, ratio)`` for every salt with both.

    The validation of this whole module, as DATA rather than a docstring table --
    the same move ``mineral_data.fusion_law_bound`` makes, and for the same
    reason: a green test suite is not evidence that a quoted number still holds.
    The measured solubilities come from ``mineral_data``'s ``fusion_law_bound``,
    which predates any of this and was entered for the opposite purpose.
    """
    out: dict[str, tuple[float, float, float]] = {}
    for name, record in MINERALS.items():
        if not record.fusion_law_bound:
            continue
        try:
            ksp = solubility_product(record, ions)
        except UnpricedLattice:
            continue
        predicted = ksp.solubility()
        measured = record.fusion_law_bound[1]
        out[name] = (predicted, measured, predicted / measured)
    return out

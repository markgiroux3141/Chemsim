"""Layer 1 -- critical constants and the Lee-Kesler vapour-pressure shape.

Two jobs, kept together because the second consumes the first.

**Wilson-Jasperson and Fedors** estimate Tc/Pc/Vc for a molecule Joback cannot
fragment. The reason this matters is architectural rather than numerical: Joback
is the only source of critical properties in the project, and Benson -- the
better estimator above him -- supplies formation quantities and says nothing
about Tb/Tc/Pc/Vc, because group additivity is a statement about formation. So a
species Joback refused had no physical half from anywhere, and its Benson
formation half was unreachable no matter how well Benson priced it. Benson gets
acetic anhydride's enthalpy of formation to within 3.7 kJ/mol of measurement, and
before this module that value was computed, correct and unusable.

**Wilson-Jasperson takes Tb as an INPUT**, which is what makes the pair enough:
supply a measured boiling point (``physical_data.MEASURED_PHYSICAL``) and Tc and
Pc follow; Fedors gives Vc from structure alone. The whole coverage problem
collapses to one lookup.

**The Lee-Kesler shape functions** live here rather than in ``volatility`` for a
layering reason. ``volatility`` builds a provider and therefore imports
``thermochemistry``; ``thermochemistry`` needs an enthalpy of vaporisation for a
record it assembles from estimated critical constants, and deriving that from
Lee-Kesler would import ``volatility`` straight back. Putting the correlation in
a module that depends on nothing but ``matter`` breaks the cycle, and it is where
the functions belong anyway: they are a property model, not a provider.
``volatility`` re-exports them so its public surface is unchanged.

Nothing here estimates a boiling point. That is deliberate -- see
``physical_data`` -- and it is why a species with no measured Tb is refused
rather than served a guess.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from chemsim.matter import Molecule
from chemsim.properties.critical_data import (
    FEDORS_ALLOWED_ATOMS,
    FEDORS_BASE,
    FEDORS_CONTRIBUTIONS,
    FEDORS_GROUP_SMARTS,
    WJ_GROUP_SMARTS,
    WJ_PC_GROUPS,
    WJ_PC_INCREMENTS,
    WJ_TC_GROUPS,
    WJ_TC_INCREMENTS,
)

P_ATM_BAR = 1.01325
R_J = 8.314462618          # J/(mol K)


class CriticalPropertyError(ValueError):
    """Raised when a critical property cannot be estimated for a species.

    Raised rather than returned as a sentinel, and never softened into a
    partial answer. A group-contribution method is at its most dangerous when it
    *succeeds* on a molecule it does not cover -- Joback confidently reports
    -74.8 kJ/mol for elemental chlorine, whose true value is zero by definition,
    and that is a factor of 1e13 in an equilibrium constant.
    """


# ---------------------------------------------------------------------------
# Lee-Kesler
# ---------------------------------------------------------------------------


def _lee_kesler_f(Tr: float) -> tuple[float, float]:
    """The two Lee-Kesler shape functions f0(Tr), f1(Tr) for ln(P/Pc)."""
    lnTr = math.log(Tr)
    f0 = 5.92714 - 6.09648 / Tr - 1.28862 * lnTr + 0.169347 * Tr**6
    f1 = 15.2518 - 15.6875 / Tr - 13.4721 * lnTr + 0.43577 * Tr**6
    return f0, f1


def _lee_kesler_df(Tr: float) -> tuple[float, float]:
    """d f0 / d Tr and d f1 / d Tr -- the analytic derivatives of the above.

    Differentiated rather than finite-differenced so the enthalpy of
    vaporisation derived from this curve is exactly the slope of the curve the
    vessel actually integrates, to machine precision.
    """
    df0 = 6.09648 / Tr**2 - 1.28862 / Tr + 6.0 * 0.169347 * Tr**5
    df1 = 15.6875 / Tr**2 - 13.4721 / Tr + 6.0 * 0.43577 * Tr**5
    return df0, df1


def acentric_factor(Tb: float, Tc: float, Pc: float) -> float:
    """Estimate the acentric factor by inverting Lee-Kesler at the boiling point.

    We do not transcribe a closed-form omega correlation; we *derive* omega from
    the definition it has to satisfy -- that the correlation reproduce
    Psat(Tb) = 1 atm. Solving ln(P_atm/Pc) = f0 + omega*f1 for omega:

        omega = (ln(P_atm / Pc) - f0(Tbr)) / f1(Tbr)

    The payoff is self-consistency: the fitted curve passes through the normal
    boiling point exactly, whatever else it does.
    """
    Tbr = Tb / Tc
    if not 0.0 < Tbr < 1.0:
        raise CriticalPropertyError(f"boiling point {Tb} K is not below Tc {Tc} K")
    f0, f1 = _lee_kesler_f(Tbr)
    return (math.log(P_ATM_BAR / Pc) - f0) / f1


def lee_kesler_psat(T: float, Tc: float, Pc: float, omega: float) -> float:
    """Lee-Kesler vapour pressure in bar. Undefined at/above Tc -> returns Pc."""
    Tr = T / Tc
    if Tr >= 1.0:
        return Pc
    f0, f1 = _lee_kesler_f(Tr)
    return Pc * math.exp(f0 + omega * f1)


def hvap_at_tb(Tb: float, Tc: float, Pc: float, omega: float | None = None) -> float:
    """Enthalpy of vaporisation at the normal boiling point, kJ/mol.

    Clausius-Clapeyron applied to the Lee-Kesler curve, analytically:

        dHvap = R * T^2 * dln(Psat)/dT * dz
              = R * Tc * Tr^2 * (df0/dTr + omega * df1/dTr) * dz

    NO NEW CORRELATION IS INTRODUCED, and that is the point. Riedel, Chen and
    Vetere all estimate this quantity from the same Tb/Tc/Pc, but each is an
    independent regression, so pairing one with our Lee-Kesler curve would put
    two tabulations inside one record -- the mistake this project has already
    paid for three times (see ``thermochemical-data-curation``). Differentiating
    the curve we already fitted means the latent heat and the vapour pressure
    cannot disagree with each other: the vessel's boil-off rate is
    (Q - losses)/dHvap while the temperature it pins at comes from Psat, and
    those two have to be two views of one curve or a flask boils at the right
    temperature and the wrong rate.

    ``dz`` is the vapour/liquid compressibility difference. It is taken as 1,
    i.e. an ideal vapour over a liquid of negligible molar volume, which is
    ~3% high at a normal boiling point. The residual is MEASURED against the
    nine curated species that have both a measured dHvap and measured critical
    constants -- see ``validation/physical_estimation.py`` -- rather than
    corrected by a fudge factor.
    """
    if omega is None:
        omega = acentric_factor(Tb, Tc, Pc)
    Tr = Tb / Tc
    df0, df1 = _lee_kesler_df(Tr)
    # d ln P / d T = (1/Tc) * (df0/dTr + omega df1/dTr); times R T^2 gives J/mol.
    dlnP_dT = (df0 + omega * df1) / Tc
    return R_J * Tb**2 * dlnP_dT / 1000.0


# ---------------------------------------------------------------------------
# Wilson-Jasperson: Tc and Pc from a known Tb
# ---------------------------------------------------------------------------


def _wj_group_counts(mol: Molecule) -> dict[str, int]:
    """Wilson-Jasperson's second-order group counts.

    Matched on the implicit-hydrogen graph, which is what the method is written
    against -- unlike Fedors below. The two are not interchangeable; see
    ``Molecule.substructure_matches``.
    """
    counts: dict[str, int] = {}
    elements = mol.element_counts()

    def n(key: str) -> int:
        patterns = WJ_GROUP_SMARTS[key]
        if isinstance(patterns, str):
            patterns = (patterns,)
        return sum(len(mol.substructure_matches(p)) for p in patterns)

    # The hydroxyl term splits on molecule size, not on the hydroxyl itself: a
    # small molecule's OH raises Tc far more than a large one's, because the
    # hydrogen bond is a bigger share of the total cohesion.
    n_oh = n("OH")
    n_carbon = elements.get("C", 0)
    if n_carbon:
        counts["OH_large" if n_carbon >= 5 else "OH_small"] = n_oh

    counts["-O-"] = n("-O-")

    counts["-CN"] = 0
    counts["amine"] = 0
    if "N" in elements:
        counts["-NO2"] = n("-NO2")
        counts["-CN"] = n("-CN")
        # An amine is counted once per NITROGEN, not once per pattern match:
        # the patterns overlap heavily (ten of them, several of which match the
        # same tertiary amine), so counting matches would multiply-count it.
        nitrogens: set[int] = set()
        symbols = mol.atom_symbols()
        for pattern in WJ_GROUP_SMARTS["amine"]:
            for match in mol.substructure_matches(pattern):
                nitrogens.update(i for i in match if symbols[i] == "N")
        counts["amine"] = len(nitrogens)

    if "O" in elements and "C" in elements:
        counts["-CHO"] = n("-CHO")
        counts[">CO"] = n(">CO")
        counts["-COOH"] = n("-COOH")
        counts["-COO-"] = n("-COO-")

    # Halide is a PRESENCE flag, once per molecule, not a count per halogen.
    # That is how the method is parameterised and how the reference
    # implementation applies it; carbon tetrachloride takes 0.002, not 0.008.
    counts["halide"] = 1 if n("halide") else 0

    counts["sulfur_groups"] = n("sulfur_groups") if "S" in elements else 0
    counts["siloxane"] = n("siloxane") if "Si" in elements else 0
    return counts


def wilson_jasperson(
    mol: Molecule, Tb: float, second_order: bool = True
) -> tuple[float, float]:
    """Critical temperature (K) and pressure (bar) from structure and Tb.

    ``second_order=False`` uses the element sums alone, kept so the group terms'
    contribution can be measured rather than assumed -- the same reason
    ``ThermochemistryProvider(benson=False)`` exists.

    Raises rather than reporting a flag for a missing element increment. The
    reference implementation returns ``Tb * 2.5`` when the denominator goes
    negative and sets a boolean beside it; a caller who ignores the boolean gets
    a plausible number with no relationship to the molecule, which is precisely
    the failure mode this project refuses.
    """
    elements = mol.element_counts()
    n_rings = len(mol.ring_atom_indices())

    missing_tc = sorted(set(elements) - set(WJ_TC_INCREMENTS))
    if missing_tc:
        raise CriticalPropertyError(
            f"{mol.smiles!r}: Wilson-Jasperson has no Tc increment for "
            f"{missing_tc} -- refusing rather than omitting the element"
        )
    missing_pc = sorted(
        e for e in elements
        if e not in WJ_PC_INCREMENTS or WJ_PC_INCREMENTS[e] is None
    )
    if missing_pc:
        raise CriticalPropertyError(
            f"{mol.smiles!r}: Wilson-Jasperson has no Pc increment for "
            f"{missing_pc} -- refusing rather than omitting the element"
        )

    tc_inc = sum(WJ_TC_INCREMENTS[e] * n for e, n in elements.items())
    pc_inc = sum(WJ_PC_INCREMENTS[e] * n for e, n in elements.items())  # type: ignore[operator]

    tc_groups = pc_groups = 0.0
    if second_order:
        counts = _wj_group_counts(mol)
        tc_groups = sum(WJ_TC_GROUPS[k] * v for k, v in counts.items())
        pc_groups = sum(WJ_PC_GROUPS[k] * v for k, v in counts.items())

    denominator = 0.048271 - 0.019846 * n_rings + tc_inc + tc_groups
    if denominator <= 0.0:
        raise CriticalPropertyError(
            f"{mol.smiles!r}: Wilson-Jasperson Tc denominator is {denominator:.6f}, "
            "which is not positive -- the correlation has no value here"
        )
    Tc = Tb / denominator**0.2

    Y = -0.00922295 - 0.0290403 * n_rings + 0.041 * (pc_groups + pc_inc)
    pc_denominator = -0.96601 + math.exp(Y)
    if pc_denominator == 0.0:
        raise CriticalPropertyError(
            f"{mol.smiles!r}: Wilson-Jasperson Pc is singular here"
        )
    Pc = 0.0186233 * Tc / pc_denominator
    if Pc <= 0.0:
        raise CriticalPropertyError(
            f"{mol.smiles!r}: Wilson-Jasperson gives a non-physical "
            f"Pc = {Pc:.3f} bar"
        )
    return Tc, Pc


# ---------------------------------------------------------------------------
# Fedors: Vc from structure
# ---------------------------------------------------------------------------


def _rings_attached_to_rings(mol: Molecule) -> int:
    """How many rings are bonded to, or fused with, another ring.

    Fedors carries a term for this because a biphenyl-like linkage packs
    differently from two isolated rings. "Attached" includes a mere bond between
    ring systems, not only a shared wall.
    """
    rings = mol.ring_atom_indices()
    if len(rings) < 2:
        return 0
    views = mol.topology()
    count = 0
    for i, ring in enumerate(rings):
        others: set[int] = set()
        for j, other in enumerate(rings):
            if i != j:
                others.update(other)
        attached = False
        for atom in ring:
            if atom in others or others & set(views[atom].neighbours):
                attached = True
                break
        if attached:
            count += 1
    return count


def fedors(mol: Molecule) -> float:
    """Critical volume in cm3/mol. Raises on an element Fedors does not cover.

    The reference implementation returns a number alongside a ``'errors found'``
    status string when it meets an element outside its table; that signal is the
    same discipline this project uses, so it becomes an exception here rather
    than a value a caller might use without looking. Glyphosate's phosphorus is
    exactly the case it exists for.
    """
    elements = mol.element_counts()
    unknown = sorted(set(elements) - FEDORS_ALLOWED_ATOMS)
    if unknown:
        raise CriticalPropertyError(
            f"{mol.smiles!r}: Fedors has no critical-volume contribution for "
            f"{unknown} (covers {sorted(FEDORS_ALLOWED_ATOMS)})"
        )

    ring_sizes = mol.ring_sizes()
    unhandled = sorted({s for s in ring_sizes if s not in (3, 4, 5, 6)})
    if unhandled:
        raise CriticalPropertyError(
            f"{mol.smiles!r}: Fedors has no ring term for ring size(s) {unhandled}"
        )

    # Alcohol and amine heteroatoms take their own contribution, so they are
    # SUBTRACTED from the plain element count rather than added on top. Both are
    # matched on the EXPLICIT-hydrogen graph, which is how the method is
    # published and which changes what the amine pattern means -- with hydrogens
    # as atoms, ``amine_smarts``'s "no non-carbon neighbour" clause excludes
    # every N-H, so only tertiary amines match. See ``critical_data``.
    n_alcohol = len(
        mol.substructure_matches(
            FEDORS_GROUP_SMARTS["O_alcohol"], explicit_hydrogens=True
        )
    )
    n_amine = len(
        mol.substructure_matches(
            FEDORS_GROUP_SMARTS["N_amine"], explicit_hydrogens=True
        )
    )

    doubles = triples = 0
    for view in mol.topology():
        for neighbour, order in zip(view.neighbours, view.bond_orders):
            if neighbour <= view.index:
                continue                       # count each bond once
            if order == 2.0:
                doubles += 1
            elif order == 3.0:
                triples += 1

    terms = {
        "C": elements.get("C", 0),
        "H": elements.get("H", 0),
        "O": elements.get("O", 0) - n_alcohol,
        "O_alcohol": n_alcohol,
        "N": elements.get("N", 0) - n_amine,
        "N_amine": n_amine,
        "F": elements.get("F", 0),
        "Cl": elements.get("Cl", 0),
        "Br": elements.get("Br", 0),
        "I": elements.get("I", 0),
        "S": elements.get("S", 0),
        "3_ring": ring_sizes.count(3),
        "4_ring": ring_sizes.count(4),
        "5_ring": ring_sizes.count(5),
        "6_ring": ring_sizes.count(6),
        "double_bond": doubles,
        "triple_bond": triples,
        "ring_ring_bonds": _rings_attached_to_rings(mol),
    }
    Vc = FEDORS_BASE + sum(FEDORS_CONTRIBUTIONS[k] * v for k, v in terms.items())
    if Vc <= 0.0:
        raise CriticalPropertyError(
            f"{mol.smiles!r}: Fedors gives a non-physical Vc = {Vc:.1f} cm3/mol"
        )
    return Vc


# ---------------------------------------------------------------------------
# the assembled physical half
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhysicalEstimate:
    """Tb/Tc/Pc/Vc/Hvap for one species, and where each number came from.

    ``source`` names every tabulation involved, because this record is the whole
    reason the provenance discipline has to be explicit here: an assembled
    species can carry a measured Tb from one compilation, a Wilson-Jasperson Tc
    and Pc, a Fedors Vc, and (from the formation half) a Benson Hf. That is four
    sources in one entry, and a caller must be able to see them.
    """

    Tb: float
    Tc: float
    Pc: float
    Vc: float
    Hvap: float                # kJ/mol, at Tb
    omega: float
    source: str
    # True when Tc and Pc are measured rather than estimated. Exposed because
    # Wilson-Jasperson's Pc is the weakest number in the chain by a wide margin
    # (28% mean error on polar species, measured), and a caller judging whether
    # to trust a latent heat needs to know which side of that line it is on.
    critical_measured: bool = False


def estimate_physical(
    mol: Molecule,
    Tb: float,
    Tb_source: str,
    Tc: float | None = None,
    Pc: float | None = None,
    Vc: float | None = None,
    critical_source: str | None = None,
    Vc_source: str | None = None,
) -> PhysicalEstimate:
    """Assemble a physical half from a known boiling point.

    Measured ``Tc``/``Pc``/``Vc`` are used where supplied and estimated where
    not, because curated data outranks an estimate -- the same order the rest of
    Layer 1 obeys. ``Tc`` and ``Pc`` must be supplied together or not at all:
    they combine into the acentric factor, so one measured beside one estimated
    would put two bases inside one derived number.

    Order matters only in that Tc and Pc must exist before the acentric factor
    and hence the latent heat can be derived. Everything raises rather than
    degrading, so a partial record never escapes.
    """
    if (Tc is None) != (Pc is None):
        raise CriticalPropertyError(
            f"{mol.smiles!r}: Tc and Pc must be supplied together or not at all "
            f"(got Tc={Tc}, Pc={Pc}); they combine into the acentric factor"
        )

    parts = [f"Tb {Tb_source}"]
    if Tc is None or Pc is None:
        Tc, Pc = wilson_jasperson(mol, Tb)
        parts.append("Tc/Pc Wilson-Jasperson")
        critical_measured = False
    else:
        parts.append(f"Tc/Pc {critical_source or 'measured'}")
        critical_measured = True
    if Vc is None:
        Vc = fedors(mol)
        parts.append("Vc Fedors")
    else:
        parts.append(f"Vc {Vc_source or 'measured'}")

    omega = acentric_factor(Tb, Tc, Pc)
    Hvap = hvap_at_tb(Tb, Tc, Pc, omega)
    parts.append("Hvap from Lee-Kesler by Clausius-Clapeyron")
    return PhysicalEstimate(
        Tb=Tb, Tc=Tc, Pc=Pc, Vc=Vc, Hvap=Hvap, omega=omega,
        source="; ".join(parts), critical_measured=critical_measured,
    )

"""Regenerate ``chemsim.properties.element_data``.

Run this rather than hand-editing the module:

    python tools/build_element_data.py            # writes the module
    python tools/build_element_data.py --dry-run  # report only, write nothing

## What this table is for, and why it is the cheapest table in the project

**For an element in its standard state the data is FREE AND EXACT.** Hf = Gf = 0
by definition, there is no source to cite and no cross-check that could exist.
That makes an estimator returning a NON-ZERO formation energy for a reference
state a *detectable error* rather than a judgement call -- and this repo has now
paid for that lesson three times:

    Cl2   Joback returns Hf = -74.81 kJ/mol   (~1e13 in any K)
    F2    Joback returns Gf = -440.5  kJ/mol
    S8    Joback returns Gf = +275.96 kJ/mol  (~e^91 in any K)

The first was fixed species by species and so the lesson did not generalise;
the second and third were still live when this module was written. This table
plus the guard in ``thermochemistry`` closes the CLASS: an elemental species is
priced from here or REFUSED BY NAME, and no estimator ever sees one.

## THE STANDARD STATE IS NOT ALWAYS THE OBVIOUS ONE, and a ThermoData is a GAS

This is the trap one level up, and it is the reason two of the four halogens
were wrong in this repo before this module existed.

``ThermoData.Hf/Gf`` are IDEAL-GAS values (the docstring says so, and
``standard_state`` is what moves them into a condensed phase). So:

  * H2 / N2 / O2 / F2 / Cl2 have a GASEOUS reference state, and their ideal-gas
    record is exactly 0. Free and exact.
  * Br2 is a LIQUID and I2 and S8 are SOLIDS. Their reference state is zero in
    THAT phase, so their ideal-gas record is the vaporisation or sublimation
    energy -- a real measured number. Br2(g) is +30.90 / +3.08 kJ/mol and
    I2(g) is +62.40 / +19.29. **Both were pinned to 0.0 here before this
    module**, i.e. the species-by-species fix for the Cl2 bug introduced a
    62 kJ/mol error in iodine while removing a 75 kJ/mol error in chlorine.

## Provenance discipline, same as ``physical_data`` and ``formation_data``

  * **Nothing is transcribed from recall.** Every number is looked up in
    ``chemicals`` 1.5.2 (Hf, S0, Tb, Tm, Hfus) or ``thermo`` 0.6.1 (ideal-gas
    Cp, sampled and fitted), both at BUILD time, and every value carries the
    database that served it.
  * **dGf is DERIVED, never transcribed**: Gf = Hf - T*(S0 - sum over the
    element reference states), so both halves of an entry are consistent with
    each other by construction.
  * **One source per entry.** Hf and S0 for a species are taken from the SAME
    database or the entry is refused, because an ATCT enthalpy beside a CRC
    entropy puts a ~1 kJ/mol inconsistency inside the entry that does not cancel
    across a reaction. The ELEMENT reference entropies are a separate, single,
    pinned basis (CRC) used identically by every derivation, which is the same
    structure ``formation_data`` uses.
  * **Every estimated method is excluded explicitly.** ``chemicals`` serves
    Joback through the same accessor as CRC: ``Hfg('7782-44-7', 'JOBACK')`` is
    -426930 J/mol for OXYGEN, and ``Hfg('10544-50-0', 'JOBACK')`` is 381090 --
    bit-identical to what this project's own Joback computes. Looking either up
    would close a gap with our own number.

## Trap: a crowd-sourced melting point, and it is 100 K wrong for sulfur

``OPEN_NTBKM`` (Open Notebook melting points) sits in the EXPERIMENTAL tier and
comes FIRST in ``chemicals``' preference order for some species. For sulfur it
returns **286.405 K against CRC's 388.36** -- sulfur melts at 115 C, not 13 C.
So Tm/Tb here take a PREFERENCE ORDER with CRC first rather than accepting the
library's own, and the full spread across every method is printed for each entry
so a disagreement is visible instead of arbitrated silently.

## Trap: ``CRC_INORG`` is not an estimation method

``tools/build_physical_data.py`` classifies ``CRC_INORG`` as ESTIMATED. That is
wrong -- ``chemicals`` documents it as "a compilation of data on inorganics as
published in [the CRC Handbook]", the inorganic twin of ``CRC_ORG``, which the
same file classifies as EXPERIMENTAL. It has never mattered there because every
candidate in that script is organic. It matters enormously here: CRC_INORG is
the ONLY source of a melting point for sulfur, iodine and every mineral, so
inheriting that classification would have refused the entire floor.

## What is deliberately NOT in the table

  * **graphite, and every metal.** Their reference state is a metallic or
    covalent LATTICE. This engine's species are molecules, and the ideal-gas
    record for ``[C]`` is the carbon ATOM at Gf +671 kJ/mol -- a real number
    that is not charcoal. Refused, naming the reason.
  * **monatomic elemental symbols** (``[S]``, ``[C]``, ``[Hg]``, ``[Fe]``).
    A bare element symbol is the most ambiguous way to name an allotrope, and
    answering with the gas atom's value is a confident answer to a different
    question. Refused, naming the reference-state SMILES to charge instead.
  * **P4.** The tetrahedral SMILES ``[P]12[P]3[P]1[P]23`` canonicalises through
    RDKit to an AROMATIC-phosphorus form, which is not the species; and
    phosphorus is absent from Joback, Benson and Fedors alike (recorded in the
    coverage audit), so nothing downstream could use it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402

from chemsim.matter import Molecule  # noqa: E402

T_REF = 298.15
R = 8.31446261815324

# Sampling window for the ideal-gas Cp fit. Matches the window
# ``formation_data``'s fitted Cp polynomials use, so the kernel sees one basis.
CP_LO, CP_HI, CP_N = 273.0, 600.0, 40

# ---------------------------------------------------------------------------
# Source tiers
# ---------------------------------------------------------------------------
# CRC_INORG is EXPERIMENTAL -- see the module docstring. ESTIMATED is excluded
# outright; an UNRECOGNISED method refuses rather than defaulting, the same rule
# build_physical_data and build_benson_data apply.
EXPERIMENTAL_METHODS = frozenset({
    "ATCT_G", "ATCT_L", "CRC", "CRC_ORG", "CRC_INORG", "IUPAC", "MATTHEWS",
    "WEBBOOK", "JANAF", "TRC", "HEOS", "COMMON_CHEMISTRY", "OPEN_NTBKM",
})
COMPILATION_METHODS = frozenset({"YAWS", "PSRK", "PINAMARTINES", "PD", "WIKIDATA"})
ESTIMATED_METHODS = frozenset({
    "JOBACK", "WILSON_JASPERSON", "FEDORS", "WEBBOOK_AC", "LASTOVKA_SHAW",
    "POLING_CONST", "CRCSTD", "VDI_TABULAR",
})

TIER_EXPERIMENTAL = "experimental"
TIER_COMPILATION = "compilation"


def tier(method: str) -> str | None:
    if method in EXPERIMENTAL_METHODS:
        return TIER_EXPERIMENTAL
    if method in COMPILATION_METHODS:
        return TIER_COMPILATION
    return None


# Preference order for a TEMPERATURE (Tb/Tm). CRC first, deliberately: see the
# OPEN_NTBKM trap in the module docstring.
TEMPERATURE_PREFERENCE = ("CRC_INORG", "CRC", "CRC_ORG", "JANAF", "WEBBOOK",
                          "COMMON_CHEMISTRY", "IUPAC", "HEOS")
# Preference order for a FORMATION pair. Both halves must come from the same
# entry in this list or the species is refused.
FORMATION_PREFERENCE = ("CRC", "JANAF", "WEBBOOK", "ATCT_G", "TRC")


# ---------------------------------------------------------------------------
# The element reference states -- the basis every derivation below stands on
# ---------------------------------------------------------------------------
# element: (CAS of the reference species, atoms of the element per formula unit
#           of the TABULATED entry, phase of the reference state, human name)
#
# The "atoms per formula unit" column is load-bearing and easy to get wrong:
# ``chemicals`` tabulates sulfur under formula "S", so its S0s of 32.1 is PER
# GRAM-ATOM, while bromine is tabulated as "Br2" and its S0l of 152.2 is per
# mole of Br2. Divide by the wrong one and every sulfur compound's entropy of
# formation is out by a factor of 8.
REFERENCE_STATES: dict[str, tuple[str, int, str, str]] = {
    "H":  ("1333-74-0", 2, "g", "H2(g)"),
    "N":  ("7727-37-9", 2, "g", "N2(g)"),
    "O":  ("7782-44-7", 2, "g", "O2(g)"),
    "F":  ("7782-41-4", 2, "g", "F2(g)"),
    "Cl": ("7782-50-5", 2, "g", "Cl2(g)"),
    "Br": ("7726-95-6", 2, "l", "Br2(l)"),
    "I":  ("7553-56-2", 2, "s", "I2(s)"),
    "S":  ("7704-34-9", 1, "s", "S(rhombic)"),
    "C":  ("7782-42-5", 1, "s", "C(graphite)"),
    "P":  ("7723-14-0", 1, "s", "P(white)"),
    "Na": ("7440-23-5", 1, "s", "Na(s)"),
    "K":  ("7440-09-7", 1, "s", "K(s)"),
    "Ca": ("7440-70-2", 1, "s", "Ca(s)"),
    "Fe": ("7439-89-6", 1, "s", "Fe(s)"),
    "Cu": ("7440-50-8", 1, "s", "Cu(s)"),
    "Zn": ("7440-66-6", 1, "s", "Zn(s)"),
    "Hg": ("7439-97-6", 1, "l", "Hg(l)"),
    # Added for M3's aqueous-ion cross-check: the derivation of Gf(ion,aq) from
    # Hf(ion,aq) and S(ion,aq) needs the entropy of the metal the ion forms
    # FROM, and it is the only thing these entries are used for -- none of them
    # has a molecular reference state, so none reaches the ELEMENTS table.
    "Mg": ("7439-95-4", 1, "s", "Mg(s)"),
    "Al": ("7429-90-5", 1, "s", "Al(s)"),
    "Mn": ("7439-96-5", 1, "s", "Mn(s)"),
    "Ag": ("7440-22-4", 1, "s", "Ag(s)"),
    "Ba": ("7440-39-3", 1, "s", "Ba(s)"),
    "Pb": ("7439-92-1", 1, "s", "Pb(s)"),
    "Li": ("7439-93-2", 1, "s", "Li(s)"),
    "Rb": ("7440-17-7", 1, "s", "Rb(s)"),
    "Cs": ("7440-46-2", 1, "s", "Cs(s)"),
    "Sr": ("7440-24-6", 1, "s", "Sr(s)"),
    "Cr": ("7440-47-3", 1, "s", "Cr(s)"),
    "Co": ("7440-48-4", 1, "s", "Co(s)"),
    "Ni": ("7440-02-0", 1, "s", "Ni(s)"),
    "Cd": ("7440-43-9", 1, "s", "Cd(s)"),
    "Tl": ("7440-28-0", 1, "s", "Tl(s)"),
    # ⚠ LEFT IN DELIBERATELY SO THE REFUSAL IS VISIBLE. CRC's row for this CAS
    # is GREY tin (Hf = -2100 J/mol, S0 = 44.1); the reference state is WHITE
    # tin (S0 = 51.18, WEBBOOK). ``reference_entropies`` refuses it on the
    # definitional zero rather than silently taking the wrong allotrope.
    "Sn": ("7440-31-5", 1, "s", "Sn(white)"),
}

# The SMILES that IS each element's reference state, where this engine can hold
# it as a molecule at all. A missing entry means the reference state is a
# lattice -- see the module docstring.
REFERENCE_SMILES: dict[str, str] = {
    "H": "[H][H]", "N": "N#N", "O": "O=O", "F": "FF", "Cl": "ClCl",
    "Br": "BrBr", "I": "II", "S": "S1SSSSSSS1",
}

LATTICE_ELEMENTS = {
    "C": "graphite -- a covalent lattice",
    "P": "white phosphorus -- a molecular solid whose P4 SMILES RDKit "
         "canonicalises to aromatic phosphorus",
    "Na": "a metallic lattice", "K": "a metallic lattice",
    "Ca": "a metallic lattice", "Fe": "a metallic lattice",
    "Cu": "a metallic lattice", "Zn": "a metallic lattice",
    "Hg": "liquid mercury -- a metal, not a molecule",
}

# ---------------------------------------------------------------------------
# The candidates
# ---------------------------------------------------------------------------
# name, SMILES, CAS, whether this SMILES IS the element's reference state.
# Everything is looked up; what ends up in the table is decided by the script.
CANDIDATES: list[tuple[str, str, str, bool]] = [
    # --- reference states whose own phase is the GAS: exactly zero, for free
    ("hydrogen", "[H][H]", "1333-74-0", True),
    ("nitrogen", "N#N", "7727-37-9", True),
    ("oxygen", "O=O", "7782-44-7", True),
    ("fluorine", "FF", "7782-41-4", True),
    ("chlorine", "ClCl", "7782-50-5", True),
    # --- reference states that are CONDENSED: the gas record is real data
    ("bromine", "BrBr", "7726-95-6", True),
    ("iodine", "II", "7553-56-2", True),
    ("sulfur", "S1SSSSSSS1", "10544-50-0", True),
    # --- elemental but NOT a reference state: real measured values, and
    #     pinning them to zero would be the same error in the other direction
    ("ozone", "[O-][O+]=O", "10028-15-6", False),
    ("disulfur", "S=S", "23550-45-0", False),
]

# For a species tabulated under a DIFFERENT CAS than the one carrying its
# physical data. Sulfur is the case: CAS 10544-50-0 (S8) offers Tb/Tm/Hfus from
# JOBACK ONLY -- 615.0 K and 761.94 K, bit-identical to this project's own
# Joback -- while the measured values live under CAS 7704-34-9 ("sulfur"), whose
# MOLAR quantities are per gram-atom and so need the multiplier.
PHYSICAL_CAS: dict[str, tuple[str, int]] = {
    "S1SSSSSSS1": ("7704-34-9", 8),
}

# Physical halves carried forward VERBATIM from ``thermochemistry._CURATED_RAW``
# rather than re-looked-up. Stated as a decision, not an omission: these five
# are the atmosphere and the dissolved-gas set, their Tc/Pc/Vc feed the PSRK
# Henry extension and the Rackett molar volume, and re-basing them from a
# different compilation would move invariants that have nothing to do with the
# formation bug this module exists to fix. This session is data curation, not a
# re-basing of the air. The script PRINTS the comparison against ``chemicals``
# so any difference is visible rather than hidden.
PINNED_PHYSICAL: dict[str, dict] = {
    "[H][H]": dict(Cp_coeffs=(27.14, 9.274e-3, -1.381e-5, 7.645e-9),
                   Tb=20.37, Tc=33.19, Pc=13.13, Vc=64.1, Hvap=0.90,
                   Tm=13.81, Hfus=0.117),
    "N#N": dict(Cp_coeffs=(31.15, -1.357e-2, 2.680e-5, -1.168e-8),
                Tb=77.35, Tc=126.20, Pc=33.98, Vc=90.1, Hvap=5.58,
                Tm=63.15, Hfus=0.71),
    "O=O": dict(Cp_coeffs=(28.11, -3.680e-6, 1.746e-5, -1.065e-8),
                Tb=90.19, Tc=154.58, Pc=50.43, Vc=73.4, Hvap=6.82,
                Tm=54.36, Hfus=0.444),
    "ClCl": dict(Cp_coeffs=(28.54, 2.380e-2, -2.140e-5, 6.310e-9),
                 Tb=239.11, Tc=417.15, Pc=77.11, Vc=123.8, Hvap=20.41,
                 Tm=171.65, Hfus=6.41),
    "BrBr": dict(Cp_coeffs=(33.86, 1.130e-2, -1.190e-5, 4.130e-9),
                 Tb=331.90, Tc=584.15, Pc=103.40, Vc=127.0, Hvap=29.96,
                 Tm=265.90, Hfus=10.57),
    "II": dict(Cp_coeffs=(35.60, 9.000e-3, -1.000e-5, 3.500e-9),
               Tb=457.50, Tc=819.00, Pc=117.50, Vc=155.0, Hvap=41.57,
               Tm=386.85, Hfus=15.52),
}


# ---------------------------------------------------------------------------
# lookup helpers
# ---------------------------------------------------------------------------
def _methods(methods_fn, cas: str) -> list[str]:
    try:
        return [m for m in methods_fn(cas) if m not in ESTIMATED_METHODS
                and tier(m) is not None]
    except Exception:                                       # noqa: BLE001
        return []


def _value(fn, cas: str, method: str, kw: bool = False):
    try:
        v = fn(CASRN=cas, method=method) if kw else fn(cas, method=method)
    except Exception:                                       # noqa: BLE001
        return None
    return None if v is None else float(v)


def spread(fn, methods_fn, cas: str, kw: bool = False) -> list[tuple[str, float]]:
    """Every non-estimated value on offer, so a disagreement is visible."""
    out = []
    for m in _methods(methods_fn, cas):
        v = _value(fn, cas, m, kw)
        if v is not None:
            out.append((m, v))
    return out


def preferred(fn, methods_fn, cas: str, order: tuple[str, ...], kw: bool = False):
    """The best value under an explicit preference order, as (value, method, tier)."""
    got = dict(spread(fn, methods_fn, cas, kw))
    for m in order:
        if m in got:
            return got[m], m, tier(m)
    for m in _methods(methods_fn, cas):                     # anything left
        if m in got:
            return got[m], m, tier(m)
    return None


def formation_pair(cas: str):
    """(Hf J/mol, S0 J/mol/K, method) with BOTH halves from the same database."""
    from chemicals import Hfg, Hfg_methods, S0g, S0g_methods

    h = dict(spread(Hfg, Hfg_methods, cas))
    s = dict(spread(S0g, S0g_methods, cas))
    for m in FORMATION_PREFERENCE:
        if m in h and m in s:
            return h[m], s[m], m
    shared = sorted(set(h) & set(s))
    if shared:
        m = shared[0]
        return h[m], s[m], m
    return None


# Populated by ``reference_entropies()``: every element whose reference state
# could NOT be established, and why. Reported, never swallowed.
REFERENCE_NOTES: list[str] = []


def reference_entropies() -> dict[str, tuple[float, int, str]]:
    """S0 of each element's reference state, per mole of the TABULATED species.

    ⚠ **THE ENTRY MUST PRICE AT Hf = 0 IN THE SAME DATABASE, OR IT IS REFUSED --
    and that check is free and exact.** For an element in its standard state the
    formation enthalpy is zero by definition (this module's whole thesis), so a
    tabulated Hf that is NOT zero proves the row describes a different allotrope
    from the one the CAS was meant to name.

    Measured, it catches one immediately: CRC's row for tin (7440-31-5) carries
    ``S0s = 44.1`` with ``Hfs = -2100 J/mol``, i.e. GREY tin, while the reference
    state is white tin at ``S0 = 51.18`` -- and WEBBOOK has the white value under
    the same CAS. Taking the CRC entropy would have put 7 J/(mol K) -- 2 kJ/mol
    of Gf -- into every tin derivation, silently. Same shape as ``Br2`` and
    ``I2`` being pinned to zero before this module existed: an allotrope
    mismatch that only the definitional zero can detect.
    """
    from chemicals import (
        Hfg, Hfg_methods, Hfl, Hfl_methods, Hfs, Hfs_methods,
        S0g, S0g_methods, S0l, S0l_methods, S0s, S0s_methods,
    )

    fns = {"g": (S0g, S0g_methods), "l": (S0l, S0l_methods),
           "s": (S0s, S0s_methods)}
    hfns = {"g": (Hfg, Hfg_methods), "l": (Hfl, Hfl_methods),
            "s": (Hfs, Hfs_methods)}
    REFERENCE_NOTES.clear()
    out = {}
    for el, (cas, natoms, phase, name) in REFERENCE_STATES.items():
        fn, mf = fns[phase]
        got = preferred(fn, mf, cas, ("CRC", "WEBBOOK", "JANAF"))
        if got is None:
            REFERENCE_NOTES.append(
                f"{el} ({name}): REFUSED -- no S0 in any consulted database"
            )
            continue
        S0, method, _tier = got
        hfn, hmf = hfns[phase]
        hf = dict(spread(hfn, hmf, cas)).get(method)
        if hf is not None and hf != 0.0:
            REFERENCE_NOTES.append(
                f"{el} ({name}): REFUSED -- {method} prices this CAS at "
                f"Hf = {hf:g} J/mol in the {phase!r} phase, and an element in "
                f"its reference state is zero BY DEFINITION. The row is a "
                f"different allotrope, so its S0 of {S0:g} is not the reference "
                f"state's. (Other databases here: "
                f"{ {m: v for m, v in spread(fn, mf, cas)} })"
            )
            continue
        out[el] = (S0, natoms, method)
    return out


def fit_cubic(Ts, ys):
    V = np.vander(np.asarray(Ts), 4, increasing=True)
    coeffs, *_ = np.linalg.lstsq(V, np.asarray(ys), rcond=None)
    return tuple(float(x) for x in coeffs)


def ideal_gas_cp(cas: str):
    """(coeffs, worst % residual, method) from a fitted ideal-gas Cp curve.

    Sampled from ``thermo`` and FITTED to the cubic the kernel evaluates, which
    is the same move ``formation_data``'s Cp polynomials use -- the alternative
    is transcribing a Shomate or TRC form the kernel has never heard of.
    """
    from thermo import HeatCapacityGas

    try:
        obj = HeatCapacityGas(CASRN=cas)
    except Exception:                                       # noqa: BLE001
        return None
    for method in ("JANAF", "TRCIG", "POLING_POLY", "WEBBOOK_SHOMATE"):
        if method not in obj.all_methods:
            continue
        try:
            obj.method = method
            Ts = np.linspace(CP_LO, CP_HI, CP_N)
            ys = np.array([obj.T_dependent_property(float(T)) for T in Ts])
        except Exception:                                   # noqa: BLE001
            continue
        if not np.all(np.isfinite(ys)) or np.any(ys <= 0.0):
            continue
        coeffs = fit_cubic(Ts, ys)
        pred = np.polyval(list(reversed(coeffs)), Ts)
        worst = float(np.max(np.abs(pred - ys) / ys) * 100.0)
        return coeffs, worst, method
    return None


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------
def collect():
    from chemicals import (
        Hfus, Hfus_methods, Pc, Pc_methods, Tb, Tb_methods, Tc, Tc_methods,
        Tm, Tm_methods, Vc, Vc_methods,
    )

    refs = reference_entropies()
    table: dict[str, dict] = {}
    notes: list[str] = []
    report: list[str] = []

    for name, smiles, cas, is_ref in CANDIDATES:
        mol = Molecule.from_smiles(smiles)
        key = mol.smiles
        counts = mol.element_counts()
        if len(counts) != 1:
            notes.append(f"{name}: {smiles!r} is not a single-element species "
                         f"({counts}) -- RDKit added implicit hydrogens")
            continue
        (element, n_atoms), = counts.items()

        ref_phase = REFERENCE_STATES[element][2] if element in REFERENCE_STATES else None
        gas_reference = is_ref and ref_phase == "g"

        # ---- the formation half ------------------------------------------
        if gas_reference:
            # FREE AND EXACT. No source, no cross-check, no lookup -- and the
            # lookup is still performed below purely to confirm the database
            # agrees, because a database that disagrees with a definition is
            # worth knowing about.
            Hf, Gf = 0.0, 0.0
            f_source = "element reference state (gaseous): Hf = Gf = 0 BY DEFINITION"
            got = formation_pair(cas)
            if got is not None and abs(got[0]) > 1.0:
                notes.append(
                    f"{name}: {cas} tabulates Hfg = {got[0]/1000:.2f} kJ/mol for a "
                    f"GASEOUS reference state via {got[2]} -- pinning 0 anyway"
                )
        else:
            got = formation_pair(cas)
            if got is None:
                notes.append(
                    f"{name}: REFUSED -- no database offers Hfg and S0g from the "
                    f"SAME source (Hfg from {[m for m,_ in spread(__import__('chemicals').Hfg, __import__('chemicals').Hfg_methods, cas)]}), "
                    "and mixing two tabulations inside one entry is what this "
                    "project forbids"
                )
                continue
            H, S, method = got
            dS = S
            missing = []
            for el, k in counts.items():
                r = refs.get(el)
                if r is None:
                    missing.append(el)
                    continue
                S0_ref, per_unit, _src = r
                dS -= (k / per_unit) * S0_ref
            if missing:
                notes.append(f"{name}: REFUSED -- no reference entropy for {missing}")
                continue
            Hf = H / 1000.0
            Gf = (H - T_REF * dS) / 1000.0
            f_source = (
                f"Hf and S0 both from {method} via chemicals 1.5.2; Gf DERIVED "
                f"against the CRC element reference states"
            )

        # ---- the physical half -------------------------------------------
        phys_cas, multiplier = PHYSICAL_CAS.get(key, (cas, 1))
        if key in PINNED_PHYSICAL:
            physical = dict(PINNED_PHYSICAL[key])
            p_source = ("curated measured (Poling/CRC), carried forward verbatim "
                        "from the pre-existing entry")
            live = {
                "Tb": preferred(Tb, Tb_methods, cas, TEMPERATURE_PREFERENCE),
                "Tm": preferred(Tm, Tm_methods, cas, TEMPERATURE_PREFERENCE),
                "Tc": preferred(Tc, Tc_methods, cas, ("MATTHEWS", "HEOS", "IUPAC")),
            }
            report.append(
                f"  {name:10s} PINNED physical half; chemicals offers "
                + ", ".join(
                    f"{k}={v[0]:.2f} ({v[1]})" for k, v in live.items() if v
                )
            )
        else:
            tb = preferred(Tb, Tb_methods, phys_cas, TEMPERATURE_PREFERENCE)
            tm = preferred(Tm, Tm_methods, phys_cas, TEMPERATURE_PREFERENCE)
            hf = preferred(Hfus, Hfus_methods, phys_cas, ("CRC", "JANAF"), kw=True)
            tc = preferred(Tc, Tc_methods, phys_cas, ("MATTHEWS", "HEOS", "IUPAC",
                                                      "WEBBOOK"))
            pc = preferred(Pc, Pc_methods, phys_cas, ("MATTHEWS", "HEOS", "IUPAC",
                                                     "WEBBOOK"))
            vc = preferred(Vc, Vc_methods, phys_cas, ("MATTHEWS", "HEOS", "IUPAC",
                                                     "WEBBOOK"))
            # Tc and Pc as a PAIR or not at all -- they combine into omega.
            if (tc is None) != (pc is None):
                notes.append(f"{name}: Tc/Pc SPLIT (Tc={tc}, Pc={pc}) -- taking "
                             "neither, they combine into the acentric factor")
                tc = pc = None
            if tb is None or tc is None:
                notes.append(
                    f"{name}: REFUSED -- no measured Tb ({_methods(Tb_methods, phys_cas)}) "
                    f"or no measured Tc/Pc pair; without them there is no "
                    "vapour-pressure curve"
                )
                continue
            # Hvap is DIFFERENTIATED out of the same Lee-Kesler curve the
            # vapour pressure comes from, by this project's own ``critical``
            # module, so no new correlation enters and the latent heat cannot
            # disagree with the vapour pressure. Leaving it None would be a
            # SILENT wrong answer rather than a gap: ``vessel`` reads
            # ``Hvap_Tb[i] = (t.Hvap or 0.0)``, so a missing latent heat is a
            # species that evaporates for free.
            from chemsim.properties.critical import (
                CriticalPropertyError, estimate_physical,
            )
            try:
                est = estimate_physical(
                    mol, Tb=tb[0], Tb_source=tb[1],
                    Tc=tc[0], Pc=pc[0] / 1e5,
                    Vc=vc[0] * 1e6 * multiplier if vc else None,
                    critical_source=tc[1],
                    Vc_source=vc[1] if vc else None,
                )
            except CriticalPropertyError as exc:
                notes.append(f"{name}: REFUSED -- {exc}")
                continue
            physical = dict(
                Tb=round(tb[0], 2),
                Tc=round(tc[0], 2),
                Pc=round(pc[0] / 1e5, 3),
                Vc=round(est.Vc, 2),
                Tm=round(tm[0], 2) if tm else None,
                Hfus=round(hf[0] * multiplier / 1000.0, 3) if hf else None,
                Hvap=round(est.Hvap, 3),
            )
            p_source = "; ".join(
                f"{k}={v[1]}"
                for k, v in (("Tb", tb), ("Tm", tm), ("Hfus", hf), ("Tc", tc),
                             ("Pc", pc), ("Vc", vc)) if v is not None
            ) + "; Hvap from Lee-Kesler by Clausius-Clapeyron"
            if multiplier != 1:
                p_source += (
                    f" [molar values from CAS {phys_cas}, tabulated per "
                    f"gram-atom, multiplied by {multiplier}]"
                )
            report.append(
                f"  {name:10s} Tm spread {[(m, round(v,2)) for m,v in spread(Tm, Tm_methods, phys_cas)]}"
            )

        # ---- Cp -----------------------------------------------------------
        cp = ideal_gas_cp(cas)
        if key in PINNED_PHYSICAL:
            cp_source = "carried forward verbatim (Poling appendix A)"
            if cp is not None:
                report.append(
                    f"  {name:10s} pinned Cp(298) = "
                    f"{np.polyval(list(reversed(physical['Cp_coeffs'])), T_REF):.2f}"
                    f" vs {cp[2]} fit "
                    f"{np.polyval(list(reversed(cp[0])), T_REF):.2f} J/(mol K)"
                )
        elif cp is None:
            notes.append(f"{name}: REFUSED -- no non-estimated ideal-gas Cp")
            continue
        else:
            physical["Cp_coeffs"] = tuple(round(c, 12) for c in cp[0])
            cp_source = f"{cp[2]}, sampled {CP_LO:.0f}-{CP_HI:.0f} K and fitted " \
                        f"(worst residual {cp[1]:.2f}%)"

        table[key] = dict(
            name=name, cas=cas, element=element, n_atoms=n_atoms,
            reference_state=is_ref,
            reference_phase=ref_phase,
            Hf=round(Hf, 3), Gf=round(Gf, 3),
            formation_source=f_source,
            physical_source=p_source,
            cp_source=cp_source,
            **physical,
        )

    return table, notes, report, refs


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
HEADER = '''"""Layer 1 -- ELEMENTS: the floor every chain stands on.

GENERATED by ``tools/build_element_data.py`` from ``chemicals`` 1.5.2 and
``thermo`` 0.6.1. Do not hand-edit: regenerate. That script's docstring carries
the full argument; the short version is below.

**For an element in its standard state the data is FREE AND EXACT.** Hf = Gf = 0
by definition, with no source to cite and no cross-check that could exist. That
makes an estimator returning a non-zero formation energy for a reference state a
DETECTABLE ERROR rather than a judgement call, and three have now been detected
in this repo:

    Cl2  Joback: Hf = -74.81 kJ/mol     (~1e13 in any K)  -- fixed 2026-08-16
    F2   Joback: Gf = -440.5  kJ/mol                      -- fixed here
    S8   Joback: Gf = +275.96 kJ/mol    (~e^91 in any K)  -- fixed here

The first was fixed species by species, which is why the lesson did not
generalise. ``thermochemistry`` now REFUSES to let any estimator price an
elemental species at all: it comes from this table or it is refused by name.
That closes the class rather than one member of it.

## THE STANDARD STATE IS NOT ALWAYS THE OBVIOUS ONE

A ``ThermoData`` in this project is on the IDEAL-GAS basis. So a reference state
that is a GAS has an ideal-gas record of exactly zero, and a reference state
that is CONDENSED does not -- its ideal-gas record is the vaporisation or
sublimation energy, which is a real measured number:

    H2 N2 O2 F2 Cl2   gaseous reference state    Hf = Gf = 0   exact, free
    Br2               LIQUID  reference state    Hf = +30.90  Gf = +3.08
    I2                SOLID   reference state    Hf = +62.40  Gf = +19.29
    S8 (rhombic)      SOLID   reference state    Hf = +100.42 Gf = +48.68

**Br2 and I2 were pinned to 0.0 in this repo before this module existed.** The
species-by-species fix for the Cl2 bug put a 62 kJ/mol error into iodine while
taking a 75 kJ/mol error out of chlorine -- the same bug one level up, and the
reason the class fix had to replace it rather than extend it.

The independent cross-check on a condensed reference state is that shifting the
ideal-gas value back down into its own phase must return zero:

    Gf(g) + R T ln(Psat/P_std) - Hfus*(1 - T/Tm)  ==  0

and nothing in that expression touched the formation table -- Psat comes from
Tb/Tc/Pc through Lee-Kesler and Hfus/Tm are separate measurements. It is
measured in ``tests/test_element_data.py`` and reported in
``validation/game_gates.py``.

## WHAT IS NOT HERE, AND WHY IT IS REFUSED RATHER THAN ESTIMATED

  * **graphite and every metal.** The reference state is a metallic or covalent
    LATTICE, and this engine's species are molecules. The ideal-gas record for
    ``[C]`` is the carbon ATOM at Gf +671 kJ/mol -- a real number that is not
    charcoal.
  * **a bare monatomic symbol** (``[S]``, ``[C]``, ``[Fe]``). The most ambiguous
    way there is to name an allotrope; answering with the gas atom's value is a
    confident answer to a different question. The refusal names the
    reference-state SMILES to charge instead.
"""

from __future__ import annotations

from typing import NamedTuple


class ElementalRecord(NamedTuple):
    """One elemental species, on the IDEAL-GAS basis, with provenance."""

    name: str
    cas: str
    element: str
    n_atoms: int
    reference_state: bool          # is this SMILES the element's standard state
    reference_phase: str | None    # "g" / "l" / "s" -- which phase is zero
    Hf: float                      # kJ/mol, ideal gas, 298.15 K
    Gf: float                      # kJ/mol, ideal gas, 298.15 K
    Cp_coeffs: tuple               # J/(mol K), a + bT + cT^2 + dT^3
    Tb: float | None
    Tc: float | None
    Pc: float | None
    Vc: float | None
    Hvap: float | None
    Tm: float | None
    Hfus: float | None
    formation_source: str
    physical_source: str
    cp_source: str


class ReferenceState(NamedTuple):
    """Which species and phase is an element's zero, and its absolute entropy."""

    species: str                   # human name, e.g. "S(rhombic)"
    smiles: str | None             # None where the reference state is a lattice
    phase: str                     # "g" / "l" / "s"
    S0: float                      # J/(mol K), per mole of the TABULATED species
    atoms_per_unit: int            # atoms of the element in that formula unit
    source: str
'''

FOOTER_TEMPLATE = '''

# ---------------------------------------------------------------------------
# Elements whose reference state this engine cannot hold as a molecule
# ---------------------------------------------------------------------------
# Kept as data rather than dropped, so the REFUSAL can name the reason. A
# refusal that says "no data" where the truth is "your representation cannot
# express this" is a worse answer than no answer.
LATTICE_ELEMENTS: dict[str, str] = {lattice!r}


def element_of(molecule) -> str | None:
    """The element symbol if ``molecule`` is a single-element NEUTRAL species.

    NET charge, not the presence of formal charges: nitrobenzene is written
    ``O=[N+]([O-])c1ccccc1`` and is an ordinary neutral molecule that the
    estimators must keep pricing, while ``[Cl-].[Cl-]`` has net charge -2 and is
    two chloride ions that Joback was happily pricing as one neutral species at
    -74.74 kJ/mol -- the Cl2 value, for a pair of ions.

    Returns None for anything with more than one element, so methane (``C`` ->
    C1H4) is not mistaken for elemental carbon.
    """
    if molecule.charge != 0:
        return None
    counts = molecule.element_counts()
    if len(counts) != 1:
        return None
    return next(iter(counts))


def is_monatomic(molecule) -> bool:
    """Whether a species is a bare single atom of one element.

    Separated from ``element_of`` because the two get DIFFERENT refusals: a
    monatomic symbol is an ambiguous way to name an allotrope, whereas a
    polyatomic elemental species missing from the table is simply uncurated.
    """
    counts = molecule.element_counts()
    return len(counts) == 1 and next(iter(counts.values())) == 1
'''


def render(table: dict, refs: dict) -> str:
    out = [HEADER]
    out.append("\n\n# ---------------------------------------------------------"
               "------------------")
    out.append("# The element reference states: the basis every derivation here"
               " stands on")
    out.append("# ---------------------------------------------------------"
               "------------------")
    out.append("# ``atoms_per_unit`` is load-bearing and easy to get wrong:")
    out.append("# ``chemicals`` tabulates sulfur under formula \"S\", so its S0"
               " of 32.1 is PER")
    out.append("# GRAM-ATOM, while bromine is tabulated as \"Br2\" and its 152."
               "2 is per mole of")
    out.append("# Br2. Divide by the wrong one and every sulfur compound's ent"
               "ropy of")
    out.append("# formation is out by a factor of eight.")
    out.append("REFERENCE_STATES: dict[str, ReferenceState] = {")
    for el, (cas, natoms, phase, name) in REFERENCE_STATES.items():
        if el not in refs:
            continue
        S0, per_unit, src = refs[el]
        smi = REFERENCE_SMILES.get(el)
        out.append(f"    {el!r}: ReferenceState(")
        out.append(f"        species={name!r}, smiles={smi!r}, phase={phase!r},")
        out.append(f"        S0={S0!r}, atoms_per_unit={per_unit!r},")
        out.append(f"        source={src + ' via chemicals 1.5.2'!r},")
        out.append("    ),")
    out.append("}")
    out.append("")
    out.append("")
    out.append("# ------------------------------------------------------------"
               "---------------")
    out.append("# The elemental species, on the IDEAL-GAS basis")
    out.append("# ------------------------------------------------------------"
               "---------------")
    out.append("ELEMENTAL: dict[str, ElementalRecord] = {")
    for smi, rec in table.items():
        exact = rec["reference_state"] and rec["reference_phase"] == "g"
        tag = "EXACT by definition" if exact else (
            "reference state, condensed -- the gas record is real data"
            if rec["reference_state"] else "elemental, NOT a reference state"
        )
        out.append(f"    # {rec['name']}  (CAS {rec['cas']}; {tag})")
        out.append(f"    {smi!r}: ElementalRecord(")
        out.append(f"        name={rec['name']!r}, cas={rec['cas']!r}, "
                   f"element={rec['element']!r}, n_atoms={rec['n_atoms']!r},")
        out.append(f"        reference_state={rec['reference_state']!r}, "
                   f"reference_phase={rec['reference_phase']!r},")
        out.append(f"        Hf={rec['Hf']!r}, Gf={rec['Gf']!r},")
        out.append(f"        Cp_coeffs={rec['Cp_coeffs']!r},")
        out.append(f"        Tb={rec['Tb']!r}, Tc={rec['Tc']!r}, "
                   f"Pc={rec['Pc']!r}, Vc={rec['Vc']!r},")
        out.append(f"        Hvap={rec['Hvap']!r}, Tm={rec['Tm']!r}, "
                   f"Hfus={rec['Hfus']!r},")
        out.append(f"        formation_source={rec['formation_source']!r},")
        out.append(f"        physical_source={rec['physical_source']!r},")
        out.append(f"        cp_source={rec['cp_source']!r},")
        out.append("    ),")
    out.append("}")
    out.append(FOOTER_TEMPLATE.format(lattice=LATTICE_ELEMENTS))
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    table, notes, report, refs = collect()

    print("=" * 78)
    print("ELEMENT REFERENCE ENTROPIES (the derivation basis)")
    print("=" * 78)
    for el, (S0, per_unit, src) in sorted(refs.items()):
        name = REFERENCE_STATES[el][3]
        print(f"  {el:3s} {name:12s} S0 = {S0:7.2f} J/(mol K) per {per_unit} "
              f"atom(s)   [{src}]")

    print()
    print("=" * 78)
    print(f"TABLE: {len(table)} elemental species")
    print("=" * 78)
    print(f"  {'species':10s} {'ref':4s} {'phase':6s} {'Hf(g)':>9s} "
          f"{'Gf(g)':>9s} {'Tb':>8s} {'Tm':>8s}")
    for smi, rec in table.items():
        ref = "yes" if rec["reference_state"] else "no"
        tb = f"{rec['Tb']:.2f}" if rec["Tb"] else "--"
        tm = f"{rec['Tm']:.2f}" if rec["Tm"] else "--"
        print(f"  {rec['name']:10s} {ref:4s} {str(rec['reference_phase']):6s} "
              f"{rec['Hf']:9.2f} {rec['Gf']:9.2f} {tb:>8s} {tm:>8s}")

    print()
    print("=" * 78)
    print("WHAT THE LOOKUPS SAID (so a pinned value can be compared, not hidden)")
    print("=" * 78)
    for line in report:
        print(line)

    print()
    print("=" * 78)
    print(f"REFERENCE STATES: {len(refs)} established, "
          f"{len(REFERENCE_NOTES)} REFUSED on the definitional zero")
    print("=" * 78)
    for n in REFERENCE_NOTES:
        print(f"  * {n}")

    print()
    print("=" * 78)
    print(f"REFUSED / NOTED: {len(notes)}")
    print("=" * 78)
    for n in notes:
        print(f"  * {n}")

    target = REPO / "src" / "chemsim" / "properties" / "element_data.py"
    if args.dry_run:
        print(f"\n(dry run -- would write {target})")
        return
    target.write_text(render(table, refs), encoding="utf-8")
    print(f"\nwrote {target}")


if __name__ == "__main__":
    main()

"""Regenerate ``chemsim.properties.ion_data`` -- AQUEOUS ions, conventional basis.

    python tools/build_ion_data.py            # writes the module
    python tools/build_ion_data.py --dry-run  # report only, write nothing

## M3'S BLOCKER, AND WHY IT WAS NOT ACTUALLY A CURATION JOB

M3 needs ``Gf(ion, aq)`` on the conventional ``Gf(H+,aq) = 0`` scale so that a
solubility product is a subtraction *inside one basis*:

    M_a X_b(s) <=> a M(+) + b X(-)     dG_diss = a Gf(M+) + b Gf(X-) - Gf_solid

``mineral_data`` already supplies the lattice half properly. The ion half was
recorded -- in MILESTONES, in HANDOFF, in a memory file and in this repo's own
``validation/solubility_product.py`` -- as *hand-curation, because `chemicals`
has no aqueous ion values and hands back the GAS-PHASE ion instead*.

!! **THAT MEASUREMENT WAS RIGHT ABOUT THE FUNCTIONS AND WRONG ABOUT THE
PACKAGE.** ``Hfs``/``S0s``/``Hfl`` really are ``None`` for Na+ and ``Hfg`` really
is +609343 J/mol -- the gaseous cation with the ionisation energy in it. But
``chemicals`` 1.5.2 SHIPS the table anyway, as a data file no function reads:

    chemicals/Electrolytes/CRC Thermodynamic Properties of Aqueous Ions.tsv

173 ions, CAS-keyed, ``Hf(aq)`` / ``Gf(aq)`` / ``S(aq)`` / ``Cp(aq)``, one
compilation (CRC), with ``H+`` carrying 0 / 0 / 0 / 0 -- which is the
conventional scale, stated by the table itself rather than assumed.

**The generalisable form: A REFUSAL FROM AN API IS NOT EVIDENCE THAT THE DATA IS
ABSENT.** The previous probe asked the accessor functions and believed their
``None``. This project has a standing rule that a *successful* call can be a wrong
answer (``chemicals`` handing back a Joback estimate as "data"); the mirror image
is that a *failed* call can be a wrong answer about availability. Both are fixed
the same way -- look at what the source actually contains.

## THE CROSS-CHECK, AND WHY IT ALSO PROVES THE BASIS

Every entry is checked by DERIVING ``Gf`` from the row's own ``Hf`` and ``S``
against the element reference entropies in ``element_data`` -- the same basis
``mineral_data`` derives a lattice ``Gf`` against, which is the whole point:

    ion of charge z:   elements + z H+(aq) -> ion + (z/2) H2(g)

    dS_f = S(ion,aq) + (z/2) S0(H2,g) - sum_el nu_el * S0(el, ref state)
    Gf_derived = Hf - T dS_f

**The ``(z/2) S0(H2)`` term is the load-bearing one and it is what makes this a
check on the BASIS rather than on arithmetic.** It is there only because the
convention sets ``S(H+,aq) = 0`` and settles the electron against ``1/2 H2``.
Drop it and sodium misses by 19.48 kJ/mol -- T S0(H2)/2 at 298.15 K,
and a quantity no arithmetic slip produces; keep it and every ion in the table
closes to a few hundred J/mol. So an entry passing this check has been shown to
be on the conventional aqueous scale, not merely internally tidy.

Measured residuals over the accepted set are at the ROUNDING FLOOR of the
tabulation: Hf and Gf are given to 100 J/mol and S to 0.1 J/(mol K), which is
+-50 J from each formation column and +-15 J from ``T dS`` per rounded entropy,
so a few hundred J/mol is as close as the table can possibly come to itself. The
acceptance threshold is 1 kJ/mol -- about five times that floor, and one to two
ORDERS below any real basis error (mixing the pKa basis in costs 19.5 kJ/mol for
chloride; the gas-phase cation costs 850).

## WHAT THIS TABLE IS NOT

**It is REFERENCE DATA, not a provider tier, and it must never be merged with
``electrolyte``'s ion entries.** Those are derived from measured pKa against
*this project's* water, with ``Gf(H3O+) = Gf(H2O, liquid)`` as the zero. They
reproduce acidity exactly and they are on a DIFFERENT ZERO from this table.
Chloride reads -111.73 there and -131.20 here. Neither is wrong; subtracting one
from the other is. They are kept in separate modules with no import between them
for exactly that reason, the same way ``mineral_data`` is kept out of the phase
model.

**No ionic-strength model.** These are standard-state values at infinite
dilution. A Ksp built from them is an infinite-dilution Ksp, and turning it into
a solubility assumes gamma = 1 -- see ``properties/solubility_product.py``, which
states the resulting factor rather than hiding it.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from chemsim.matter import Molecule  # noqa: E402
from chemsim.properties.element_data import REFERENCE_STATES  # noqa: E402

T_REF = 298.15

# The tabulation, as shipped inside `chemicals`. Located relative to the
# installed package so the provenance string and the file cannot drift apart.
TSV = os.path.join("Electrolytes", "CRC Thermodynamic Properties of Aqueous Ions.tsv")

# See the module docstring: five times the rounding floor of the tabulation, and
# one to two orders below any basis error this check exists to catch.
CROSSCHECK_TOL = 1.0            # kJ/mol

SOURCE = (
    "CRC 'Thermodynamic Properties of Aqueous Ions', conventional Gf(H+,aq) = 0 "
    "basis, via the data file shipped with chemicals 1.5.2"
)

# ---------------------------------------------------------------------------
# The candidates: CRC formula -> the SMILES this engine uses, and what it is FOR
# ---------------------------------------------------------------------------
# The SMILES is the only hand-written half of an entry, and it is an IDENTITY
# claim rather than a value -- so it is checked, not trusted: RDKit's element
# counts and formal charge must equal the ones parsed out of the CRC formula
# string. That check has already caught one typo (nitrite written as a neutral
# N-oxide), which is why it is a refusal rather than a comment.
CANDIDATES: list[tuple[str, str, str]] = [
    # --- the anchor --------------------------------------------------------
    ("H+", "[H+]", "the zero of the whole scale -- 0/0/0 in the table itself"),
    # --- alkali and alkaline earth ----------------------------------------
    ("Li+", "[Li+]", "lithium"),
    ("Na+", "[Na+]", "rock salt, soda ash, Glauber's salt, caustic soda"),
    ("K+", "[K+]", "saltpetre, potash, caustic potash, bisulfate"),
    ("Rb+", "[Rb+]", "rubidium"),
    ("Cs+", "[Cs+]", "caesium"),
    ("Mg+2", "[Mg+2]", "magnesia, and hard water"),
    ("Ca+2", "[Ca+2]", "calcite, lime, GYPSUM -- M1's three acid-displacement steps"),
    ("Sr+2", "[Sr+2]", "strontium"),
    ("Ba+2", "[Ba+2]", "barium -- BaSO4 is the textbook metathesis precipitate"),
    # --- transition and post-transition metals -----------------------------
    ("Mn+2", "[Mn+2]", "manganese(II)"),
    ("Fe+2", "[Fe+2]", "green vitriol, chain 2's seed"),
    ("Fe+3", "[Fe+3]", "ferric iron"),
    ("Co+2", "[Co+2]", "cobalt(II)"),
    ("Ni+2", "[Ni+2]", "nickel(II)"),
    ("Cu+", "[Cu+]", "copper(I)"),
    ("Cu+2", "[Cu+2]", "blue vitriol"),
    ("Zn+2", "[Zn+2]", "zinc"),
    ("Cd+2", "[Cd+2]", "cadmium"),
    ("Ag+", "[Ag+]", "silver -- AgCl is 'add A to B and it goes cloudy'"),
    ("Hg+2", "[Hg+2]", "mercury(II)"),
    ("Sn+2", "[Sn+2]", "tin(II)"),
    ("Pb+2", "[Pb+2]", "lead -- chrome yellow, and the golden rain of PbI2"),
    ("Al+3", "[Al+3]", "aluminium"),
    ("Tl+", "[Tl+]", "thallium(I)"),
    ("NH4+", "[NH4+]", "ammonium -- the one polyatomic cation a bench sees daily"),
    # --- halides and simple anions ----------------------------------------
    ("OH-", "[OH-]", "hydroxide"),
    ("F-", "[F-]", "fluoride"),
    ("Cl-", "[Cl-]", "chloride"),
    ("Br-", "[Br-]", "bromide"),
    ("I-", "[I-]", "iodide"),
    ("S-2", "[S-2]", "sulfide"),
    ("SH-", "[SH-]", "hydrosulfide -- what H2S actually gives in water"),
    ("S2-2", "[S-][S-]", "disulfide -- pyrite's anion"),
    ("CN-", "[C-]#N", "cyanide"),
    ("SCN-", "[S-]C#N", "thiocyanate"),
    # --- oxyanions ---------------------------------------------------------
    ("NO3-", "O=[N+]([O-])[O-]", "nitrate -- saltpetre, and chain 2"),
    ("NO2-", "[O-]N=O", "nitrite"),
    ("SO4-2", "O=S(=O)([O-])[O-]", "sulfate -- the vitriols and Glauber's salt"),
    ("HSO4-", "O=S(=O)([O-])O", "bisulfate -- what is left in the nitric retort"),
    ("SO3-2", "[O-][S+]([O-])[O-]", "sulfite"),
    ("HSO3-", "[O-][S+]([O-])O", "bisulfite"),
    ("S2O3-2", "[O-]S(=O)(=O)[S-]", "thiosulfate -- photographic hypo"),
    ("CO3-2", "O=C([O-])[O-]", "carbonate -- potash, soda ash, calcite"),
    ("HCO3-", "OC(=O)[O-]", "bicarbonate"),
    ("PO4-3", "O=P([O-])([O-])[O-]", "phosphate"),
    ("HPO4-2", "O=P(O)([O-])[O-]", "hydrogen phosphate"),
    ("H2PO4-", "O=P(O)(O)[O-]", "dihydrogen phosphate"),
    ("ClO-", "[O-]Cl", "hypochlorite -- bleach"),
    ("ClO3-", "O=Cl(=O)[O-]", "chlorate"),
    ("ClO4-", "O=Cl(=O)(=O)[O-]", "perchlorate"),
    ("BrO3-", "O=Br(=O)[O-]", "bromate"),
    ("IO3-", "O=I(=O)[O-]", "iodate"),
    ("MnO4-", "O=[Mn](=O)(=O)[O-]", "permanganate"),
    ("CrO4-2", "O=[Cr](=O)([O-])[O-]", "chromate -- chrome yellow"),
    ("AlO2-", "[O-][Al]=O", "aluminate"),
    # --- carboxylates, so an organic acid's salt can precipitate too --------
    ("CHOO-", "[O-]C=O", "formate"),
    ("CH3COO-", "CC(=O)[O-]", "acetate"),
    ("C2O4-2", "[O-]C(=O)C(=O)[O-]", "oxalate -- and calcium oxalate is a stone"),
]


def tsv_path() -> Path:
    import chemicals

    return Path(chemicals.__file__).parent / TSV


def read_table() -> dict[str, dict]:
    """CRC formula -> the row, as strings. Blank cells stay blank."""
    path = tsv_path()
    rows: dict[str, dict] = {}
    with path.open(encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            cells = line.rstrip("\n").split("\t")
            cells += [""] * (len(header) - len(cells))
            row = dict(zip(header, cells))
            rows[row["Formula"]] = row
    return rows


def parse_formula(formula: str) -> tuple[dict[str, int], int] | None:
    """CRC formula string -> (element counts, charge), or None if not simple.

    Deliberately refuses anything with brackets -- ``Th(OH)+3`` and friends are
    real rows in the table and none of them is a candidate here, so the parser
    declines rather than guessing.
    """
    m = re.match(r"^([A-Za-z0-9]+?)([+-]\d*)$", formula)
    if m is None:
        return None
    body, charge = m.groups()
    sign = 1 if charge[0] == "+" else -1
    z = sign * (int(charge[1:]) if len(charge) > 1 else 1)
    counts: dict[str, int] = {}
    for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", body):
        if not el:
            continue
        counts[el] = counts.get(el, 0) + (int(n) if n else 1)
    return counts, z


def smiles_composition(smiles: str) -> tuple[str, dict[str, int], int]:
    """(canonical SMILES, element counts INCLUDING implicit H, formal charge)."""
    from rdkit import Chem

    mol = Molecule.from_smiles(smiles)
    rd = Chem.MolFromSmiles(mol.smiles)
    counts: dict[str, int] = {}
    for atom in rd.GetAtoms():
        counts[atom.GetSymbol()] = counts.get(atom.GetSymbol(), 0) + 1
        h = atom.GetTotalNumHs()
        if h:
            counts["H"] = counts.get("H", 0) + h
    return mol.smiles, counts, Chem.GetFormalCharge(rd)


def crosscheck(Hf: float, S: float, counts: dict[str, int], z: int):
    """(Gf_derived kJ/mol, note) from the row's own Hf and S, or (None, why).

    ``elements + z H+(aq) -> ion + (z/2) H2(g)``, with S(H+,aq) = 0 by the same
    convention that sets Gf(H+,aq) = 0. See the module docstring for why the
    ``(z/2) S0(H2)`` term is what makes this a check on the basis.
    """
    h2 = REFERENCE_STATES.get("H")
    dS = S + (z / 2.0) * h2.S0
    for el, n in counts.items():
        ref = REFERENCE_STATES.get(el)
        if ref is None:
            return None, f"no reference-state entropy for {el}"
        dS -= (n / ref.atoms_per_unit) * ref.S0
    return (Hf - T_REF * dS) / 1000.0, None


def collect():
    rows = read_table()
    table: dict[str, dict] = {}
    notes: list[str] = []
    report: list[tuple] = []

    for formula, smiles, purpose in CANDIDATES:
        row = rows.get(formula)
        if row is None:
            notes.append(f"{formula}: not in the CRC aqueous-ion table at all")
            continue

        parsed = parse_formula(formula)
        if parsed is None:
            notes.append(f"{formula}: REFUSED -- formula string does not parse")
            continue
        crc_counts, z = parsed

        # IDENTITY: the hand-written SMILES must BE the tabulated ion.
        try:
            key, smi_counts, smi_z = smiles_composition(smiles)
        except Exception as exc:                              # noqa: BLE001
            notes.append(f"{formula}: REFUSED -- SMILES {smiles!r} ({exc})")
            continue
        if smi_counts != crc_counts or smi_z != z:
            notes.append(
                f"{formula}: REFUSED -- SMILES {smiles!r} is {smi_counts} charge "
                f"{smi_z:+d}, the CRC row is {crc_counts} charge {z:+d}. The "
                "SMILES is the one hand-written half of an entry and it names a "
                "DIFFERENT ion"
            )
            continue

        if not row["Hf(aq)"] or not row["Gf(aq)"] or not row["S(aq)"]:
            have = [c for c in ("Hf(aq)", "Gf(aq)", "S(aq)") if row[c]]
            notes.append(
                f"{formula}: REFUSED -- the row carries only {have or 'nothing'}; "
                "with no S(aq) there is no cross-check, and an unchecked value is "
                "what this table exists to avoid"
            )
            continue

        Hf = float(row["Hf(aq)"])
        Gf = float(row["Gf(aq)"])
        S = float(row["S(aq)"])
        Cp = float(row["Cp(aq)"]) if row["Cp(aq)"] else None

        derived, why = crosscheck(Hf, S, crc_counts, z)
        if derived is None:
            notes.append(f"{formula}: REFUSED -- {why}")
            continue
        residual = Gf / 1000.0 - derived
        if abs(residual) > CROSSCHECK_TOL:
            notes.append(
                f"{formula}: REFUSED -- Gf(tabulated) {Gf / 1000:.2f} vs "
                f"Gf DERIVED from this row's own Hf and S(aq) {derived:.2f} "
                f"kJ/mol, residual {residual:+.2f} over the {CROSSCHECK_TOL} "
                "kJ/mol tolerance. Either the row is not on the conventional "
                "aqueous basis or one of its three columns is wrong"
            )
            continue

        table[key] = dict(
            smiles=key, formula=formula, cas=row["CAS"], name=row["Name"],
            charge=z, elements=crc_counts,
            Hf=round(Hf / 1000.0, 3), Gf=round(Gf / 1000.0, 3),
            S0=round(S, 2), Cp=round(Cp, 2) if Cp is not None else None,
            purpose=purpose,
            crosscheck=round(residual, 4),
            source=SOURCE,
        )
        report.append((formula, key, Gf / 1000.0, derived, residual))

    return table, notes, report


HEADER = '''"""Layer 1 -- AQUEOUS IONS on the conventional ``Gf(H+,aq) = 0`` basis.

GENERATED by ``tools/build_ion_data.py`` from the CRC aqueous-ion table shipped
with ``chemicals`` 1.5.2. Do not hand-edit: regenerate. That script's docstring
carries the argument; the short version is below.

## THE ONE THING TO KNOW BEFORE USING THIS MODULE

**THIS IS A DIFFERENT ZERO FROM ``electrolyte``'S IONS AND THE TWO MUST NEVER BE
SUBTRACTED FROM EACH OTHER.** ``electrolyte`` back-calculates each ion from a
measured pKa against *this project's* water, with ``Gf(H3O+) = Gf(H2O, liquid)``.
That reproduces acidity exactly and is the right basis for a proton transfer.
This module is the conventional aqueous formation scale, anchored on
``Gf(H+,aq) = 0``, which is the right basis for a LATTICE subtraction. Chloride
reads -111.73 kJ/mol there and -131.20 here.

Neither number is wrong. Mixing them costs 3.4 decades of Ksp. There is no
import between the two modules and there should not be one -- the same
separation ``mineral_data`` keeps from the phase model.

**So: this module is REFERENCE DATA, not a ``ThermochemistryProvider`` tier.**
Nothing in the engine's RHS reads it. ``properties/solubility_product.py`` is its
only consumer, and it consumes ``mineral_data`` on the other side of the same
subtraction -- both derived against the element reference states in
``element_data``.

## WHERE IT CAME FROM, AND THE MEASUREMENT THAT WAS WRONG ABOUT IT

M3 was recorded as blocked on hand-curation because ``chemicals`` "has no
aqueous ion values and hands back the GAS-PHASE ion" -- measured, ``Hfs``/
``S0s``/``Hfl`` are ``None`` for Na+ and ``Hfg`` is +609343 J/mol.

**That was true of the FUNCTIONS and false of the PACKAGE.** ``chemicals`` 1.5.2
ships ``Electrolytes/CRC Thermodynamic Properties of Aqueous Ions.tsv`` -- 173
ions, one compilation, with the H+ row carrying 0/0/0/0, which is the
conventional scale stated by the table rather than assumed. No accessor function
reads it. **A refusal from an API is not evidence that the data is absent**, the
mirror image of this project's older rule that a successful call can be a wrong
answer.

## THE CROSS-CHECK EVERY ENTRY PASSED, AND WHY IT PROVES THE BASIS

``Gf`` is re-derived from the SAME row's ``Hf`` and ``S(aq)`` against the element
reference entropies in ``element_data``:

    dS_f = S(ion,aq) + (z/2) S0(H2,g) - sum_el nu_el S0(el, reference state)

The ``(z/2) S0(H2)`` term exists only because the convention settles the electron
against half a hydrogen molecule and sets ``S(H+,aq) = 0``. Drop it and sodium
misses by 19.48 kJ/mol -- exactly T S0(H2)/2 at 298.15 K. Keep it and every accepted entry closes to within a few
hundred J/mol -- the rounding floor of a table quoted to 100 J/mol and 0.1
J/(mol K). ``crosscheck`` on each record is that residual, kept as data.

An entry that fails by more than 1 kJ/mol is REFUSED rather than written, and so
is one whose hand-written SMILES does not have the element counts and formal
charge of the CRC formula string it claims to be.
"""

from __future__ import annotations

from typing import NamedTuple


class AqueousIon(NamedTuple):
    """One ion in water, on the conventional ``Gf(H+,aq) = 0`` scale.

    ``Hf``/``Gf`` are NOT on the ideal-gas basis a ``ThermoData`` carries and NOT
    on ``electrolyte``'s pKa basis, which is exactly why this is a separate type
    in a separate module: either confusion is a silent wrong answer worth decades
    of Ksp.
    """

    smiles: str                    # canonical, as the engine names the ion
    formula: str                   # the CRC table's own formula string
    cas: str
    name: str
    charge: int
    elements: dict                 # element counts of the ion
    Hf: float                      # kJ/mol, aqueous, infinite dilution, 298.15 K
    Gf: float                      # kJ/mol, aqueous, infinite dilution, 298.15 K
    S0: float                      # J/(mol K), CONVENTIONAL (S(H+,aq) = 0)
    Cp: float | None               # J/(mol K), where tabulated
    purpose: str                   # what a chain wants it for
    crosscheck: float              # kJ/mol, Gf(tabulated) - Gf(derived from Hf,S)
    source: str
'''

FOOTER = '''

def aqueous_ion(smiles: str) -> AqueousIon | None:
    """The record for a canonical ion SMILES, or None. Never raises."""
    return AQUEOUS_IONS.get(smiles)


def worst_crosscheck() -> tuple:
    """(smiles, residual kJ/mol) for the entry that closes least well.

    Exposed so a test pins the residual rather than the docstring claiming it.
    """
    worst = max(AQUEOUS_IONS.values(), key=lambda r: abs(r.crosscheck))
    return worst.smiles, worst.crosscheck
'''


def render(table: dict) -> str:
    out = [HEADER, "", "", "AQUEOUS_IONS: dict[str, AqueousIon] = {"]
    for key, rec in table.items():
        out.append(f"    # {rec['purpose']}")
        out.append(f"    {key!r}: AqueousIon(")
        out.append(f"        smiles={rec['smiles']!r}, formula={rec['formula']!r},")
        out.append(f"        cas={rec['cas']!r}, name={rec['name']!r},")
        out.append(f"        charge={rec['charge']!r}, elements={rec['elements']!r},")
        out.append(f"        Hf={rec['Hf']!r}, Gf={rec['Gf']!r}, "
                   f"S0={rec['S0']!r}, Cp={rec['Cp']!r},")
        out.append(f"        purpose={rec['purpose']!r},")
        out.append(f"        crosscheck={rec['crosscheck']!r},")
        out.append(f"        source={rec['source']!r},")
        out.append("    ),")
    out.append("}")
    out.append(FOOTER)
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("=" * 78)
    print("SOURCE")
    print("=" * 78)
    print(f"  {tsv_path()}")
    print(f"  {SOURCE}")

    table, notes, report = collect()

    print()
    print("=" * 78)
    print(f"AQUEOUS ION TABLE: {len(table)} entries")
    print("=" * 78)
    print(f"  {'ion':10s} {'smiles':26s} {'Hf':>9s} {'Gf':>9s} {'S0':>7s} {'Cp':>7s}")
    for rec in table.values():
        cp = f"{rec['Cp']:.1f}" if rec["Cp"] is not None else "--"
        print(f"  {rec['formula']:10s} {rec['smiles']:26s} {rec['Hf']:9.2f} "
              f"{rec['Gf']:9.2f} {rec['S0']:7.1f} {cp:>7s}")

    print()
    print("=" * 78)
    print("CROSS-CHECK -- Gf tabulated vs Gf DERIVED from this row's own Hf and S")
    print("=" * 78)
    print("  The (z/2) S0(H2) term is the one that proves the conventional basis;")
    print("  without it a singly charged ion misses by T S0(H2)/2 = 19.48 kJ/mol.")
    print()
    print(f"  {'ion':10s} {'Gf tab':>9s} {'Gf derived':>11s} {'residual':>9s}")
    for formula, _key, gt, gd, res in report:
        print(f"  {formula:10s} {gt:9.2f} {gd:11.2f} {res:+9.3f}")
    if report:
        worst = max(report, key=lambda r: abs(r[4]))
        print(f"\n  worst residual {worst[4]:+.3f} kJ/mol on {worst[0]}, "
              f"tolerance {CROSSCHECK_TOL} kJ/mol")
        print("  Rounding floor of the tabulation: Hf and Gf to 100 J/mol, S to")
        print("  0.1 J/(mol K) -- a few hundred J/mol is as close as it can come.")

    print()
    print("=" * 78)
    print(f"REFUSED: {len(notes)}")
    print("=" * 78)
    for n in notes:
        print(f"  * {n}")

    target = REPO / "src" / "chemsim" / "properties" / "ion_data.py"
    if args.dry_run:
        print(f"\n(dry run -- would write {target})")
        return
    target.write_text(render(table), encoding="utf-8")
    print(f"\nwrote {target}")


if __name__ == "__main__":
    main()

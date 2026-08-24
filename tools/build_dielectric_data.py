"""Regenerate ``chemsim.properties.dielectric_data``.

Run this rather than hand-editing the module. Everything in it is DERIVED from
external sources and the derivation has to stay reproducible and auditable --
the same rule ``tools/build_physical_data.py`` and ``tools/build_benson_data.py``
obey.

    python tools/build_dielectric_data.py            # writes the module
    python tools/build_dielectric_data.py --dry-run  # report only

Two tables come out, because a Born transfer term needs exactly two things it
cannot get anywhere else in this project:

``PERMITTIVITY``    the RELATIVE PERMITTIVITY of each pure liquid as a cubic in
                    temperature, from the CRC compilation shipped with
                    ``chemicals`` 1.5.2 (``Permittivity (Dielectric Constant) of
                    Liquids.tsv``). This is what makes "how polar is this layer"
                    a computed property rather than a label.

``VDW_RADII``       van der Waals radii per ELEMENT, from
                    ``chemicals.elements.periodic_table`` (Alvarez 2013 /
                    Bondi). Used only for the DERIVED tier of the ionic radius
                    -- see ``properties/dielectric.ionic_radius``.

## The polynomial is already the form this project wants

CRC publishes ``eps(T) = A + B T + C T^2 + D T^3``, which is bit-for-bit the
basis ``numerics/vessel_integrator._poly`` evaluates for liquid molar volume and
heat capacity. So nothing is fitted here and nothing is refitted: the
coefficients are transcribed with their validity window and the kernel evaluates
them blind, exactly like Antoine or Rackett. That window is the whole reason the
window is carried -- toluene's fit is quoted over 207-316 K, and a cubic
extrapolated far past its data is how a permittivity goes negative.

## Trap 1: many rows have a MEASURED VALUE and no polynomial

Roughly a third of the table gives ``T`` and ``Permittivity`` with A/B/C/D
blank -- one measurement at one temperature. That is still data, and refusing it
would drop acetaldehyde (a species this project's oxidation template makes for
itself). Such an entry is stored as a CONSTANT with its measurement temperature
recorded, and stamped ``single point`` so a caller can tell the two tiers apart.
A constant permittivity is wrong in a known direction -- every liquid's falls
with temperature -- and saying so is cheaper than pretending to a slope.

## Trap 2: the name is what reaches the database and the SMILES is what keys the
## table, so nothing else in the pipeline ever compares the two

Same guard as ``build_physical_data``: the formula parsed from the resolved CAS
is checked against the formula of the SMILES, and a mismatch is REFUSED rather
than paired. Getting this wrong would put one liquid's polarity on another's
structure, which for a Born term means putting an ion in the wrong layer.

## What is NOT here, deliberately

**No mixture data.** CRC tabulates pure liquids, and the mixing rule that turns
them into a layer's permittivity lives in ``numerics/activity`` because it needs
the composition. It is Oster's rule, and its accuracy is measured in
``validation/ion_partition.py`` rather than asserted here.

**No ionic radii from this source.** ``chemicals`` has none -- not in
``chemicals.elements`` (which carries neutral-atom radii only) and not in its
electrolyte tables. The curated ionic radii are a small hand-entered Shannon
table in ``properties/dielectric.py`` with each value stamped, and everything
else falls to the derived tier built on ``VDW_RADII`` above.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from chemsim.matter import Molecule

OUT = Path(__file__).resolve().parents[1] / "src" / "chemsim" / "properties" / (
    "dielectric_data.py"
)

# Elements the derived ionic radius needs. Kept explicit rather than dumping the
# whole periodic table: an element absent here REFUSES the derived radius, which
# is the right answer for something this project has never seen.
ELEMENTS = ("H", "C", "N", "O", "F", "Na", "Mg", "P", "S", "Cl", "K", "Ca",
            "Br", "I", "Li")

# Every liquid this project might have to price the polarity of: the solvents its
# examples and validation harnesses use, the species its templates make, and the
# common bench solvents a player would reach for. A name that does not resolve,
# or whose formula disagrees with its SMILES, is reported and skipped.
CANDIDATES: list[tuple[str, str]] = [
    # --- water and the alcohols -------------------------------------------
    ("water", "O"),
    ("methanol", "CO"),
    ("ethanol", "CCO"),
    ("1-propanol", "CCCO"),
    ("2-propanol", "CC(C)O"),
    ("1-butanol", "CCCCO"),
    ("2-methyl-2-propanol", "CC(C)(C)O"),
    ("1-octanol", "CCCCCCCCO"),
    ("ethylene glycol", "OCCO"),
    ("glycerol", "OCC(O)CO"),
    ("phenol", "Oc1ccccc1"),
    # --- acids -------------------------------------------------------------
    ("formic acid", "O=CO"),
    ("acetic acid", "CC(=O)O"),
    ("propionic acid", "CCC(=O)O"),
    ("sulfuric acid", "OS(=O)(=O)O"),
    ("nitric acid", "O[N+](=O)[O-]"),
    # --- esters and ethers -------------------------------------------------
    ("methyl acetate", "COC(C)=O"),
    ("ethyl acetate", "CCOC(C)=O"),
    ("methyl formate", "COC=O"),
    ("ethyl formate", "CCOC=O"),
    ("methyl benzoate", "COC(=O)c1ccccc1"),
    ("ethyl benzoate", "CCOC(=O)c1ccccc1"),
    ("diethyl ether", "CCOCC"),
    ("tetrahydrofuran", "C1CCOC1"),
    ("1,4-dioxane", "C1COCCO1"),
    # --- carbonyls ---------------------------------------------------------
    ("acetaldehyde", "CC=O"),
    ("propionaldehyde", "CCC=O"),
    ("acetone", "CC(C)=O"),
    ("2-butanone", "CCC(C)=O"),
    ("benzaldehyde", "O=Cc1ccccc1"),
    ("furfural", "O=Cc1ccco1"),
    # --- hydrocarbons ------------------------------------------------------
    ("benzene", "c1ccccc1"),
    ("toluene", "Cc1ccccc1"),
    ("m-xylene", "Cc1cccc(C)c1"),
    ("pentane", "CCCCC"),
    ("hexane", "CCCCCC"),
    ("heptane", "CCCCCCC"),
    ("octane", "CCCCCCCC"),
    ("cyclohexane", "C1CCCCC1"),
    ("styrene", "C=Cc1ccccc1"),
    # --- halogenated -------------------------------------------------------
    ("dichloromethane", "ClCCl"),
    ("chloroform", "ClC(Cl)Cl"),
    ("carbon tetrachloride", "ClC(Cl)(Cl)Cl"),
    ("1,2-dichloroethane", "ClCCCl"),
    ("chlorobenzene", "Clc1ccccc1"),
    # --- nitrogen and sulfur -----------------------------------------------
    ("acetonitrile", "CC#N"),
    ("nitromethane", "C[N+](=O)[O-]"),
    ("nitrobenzene", "O=[N+]([O-])c1ccccc1"),
    ("pyridine", "c1ccncc1"),
    ("aniline", "Nc1ccccc1"),
    ("ammonia", "N"),
    ("methylamine", "CN"),
    ("triethylamine", "CCN(CC)CC"),
    ("formamide", "NC=O"),
    ("N,N-dimethylformamide", "CN(C)C=O"),
    ("dimethyl sulfoxide", "CS(C)=O"),
    ("carbon disulfide", "S=C=S"),
    # --- small molecules the networks carry --------------------------------
    ("hydrogen peroxide", "OO"),
    ("nitrogen", "N#N"),
    ("oxygen", "O=O"),
    ("carbon dioxide", "O=C=O"),
    ("hydrogen", "[H][H]"),
    ("carbon monoxide", "[C-]#[O+]"),
    ("methane", "C"),
    ("ethylene", "C=C"),
]


def collect() -> tuple[dict, list[str]]:
    """Look up every candidate; return the table and the skipped-with-reason list."""
    import pandas as pd
    from chemicals import CAS_from_any, search_chemical
    from chemicals.elements import simple_formula_parser
    from chemicals.permittivity import folder

    path = os.path.join(folder, "Permittivity (Dielectric Constant) of Liquids.tsv")
    df = pd.read_csv(path, sep="\t", index_col=0)

    table: dict[str, dict] = {}
    notes: list[str] = []

    for name, smiles in CANDIDATES:
        mol = Molecule.from_smiles(smiles)
        key = mol.smiles
        try:
            cas = CAS_from_any(name)
        except Exception as exc:                            # noqa: BLE001
            notes.append(f"{name}: no CAS resolved ({str(exc)[:50]})")
            continue
        if cas not in df.index:
            notes.append(f"{name}: no CRC permittivity entry")
            continue

        # Formula guard -- see Trap 2 in the module docstring.
        try:
            db_formula = simple_formula_parser(search_chemical(cas).formula)
        except Exception:                                   # noqa: BLE001
            db_formula = None
        if db_formula is not None and db_formula != mol.element_counts():
            notes.append(
                f"{name}: FORMULA MISMATCH -- database {db_formula} vs SMILES "
                f"{mol.element_counts()}; refusing rather than pairing them"
            )
            continue

        row = df.loc[cas]

        def num(field):
            value = row[field]
            return None if pd.isna(value) else float(value)

        a, b, c, d = (num("A"), num("B"), num("C"), num("D"))
        eps_point, T_point = num("Permittivity"), num("T")
        if a is not None:
            coeffs = (a, b or 0.0, c or 0.0, d or 0.0)
            tmin, tmax = num("Tmin"), num("Tmax")
            if tmin is None or tmax is None:
                notes.append(f"{name}: polynomial with no validity window")
                continue
            kind = "polynomial"
            source = "CRC Handbook permittivity correlation (via chemicals 1.5.2)"
        elif eps_point is not None and T_point is not None:
            # ⚠ A single measurement, stored as a CONSTANT. See Trap 1: it is
            # wrong in a known direction (every liquid's permittivity falls with
            # temperature) and the alternative is having no value at all.
            coeffs = (eps_point, 0.0, 0.0, 0.0)
            tmin = tmax = T_point
            kind = "single point"
            source = (
                f"CRC Handbook single measured value at {T_point:.1f} K "
                "(via chemicals 1.5.2), held constant"
            )
        else:
            notes.append(f"{name}: row present but empty")
            continue

        table[key] = {
            "name": name,
            "cas": cas,
            "coeffs": coeffs,
            "range": (tmin, tmax),
            "kind": kind,
            "source": source,
            "eps_298": _poly(coeffs, 298.15),
        }
    return table, notes


def _poly(coeffs, T: float) -> float:
    a, b, c, d = coeffs
    return a + T * (b + T * (c + d * T))


def radii() -> dict[str, float]:
    """van der Waals radius per element, in angstrom, from ``chemicals``."""
    from chemicals.elements import periodic_table

    out = {}
    for symbol in ELEMENTS:
        element = getattr(periodic_table, symbol, None)
        if element is None or element.rvdw is None:
            continue
        out[symbol] = float(element.rvdw)
    return out


HEADER = '''"""Layer 1 data -- relative permittivity per liquid, and van der Waals radii.

⚠ GENERATED by ``tools/build_dielectric_data.py``. Do not hand-edit: re-run the
tool. Every value below is transcribed from an external source with its
provenance and, where it has one, its validity window.

``PERMITTIVITY`` maps canonical SMILES to ``(coeffs, T_range, kind, source)``
where ``coeffs`` is ``eps(T) = a + bT + cT^2 + dT^3`` -- the same polynomial
basis this project already evaluates for liquid molar volume and heat capacity,
so nothing here is fitted or refitted.

``kind`` is ``"polynomial"`` for a CRC correlation and ``"single point"`` for a
lone measurement held constant, and the distinction is not cosmetic: a constant
permittivity has no temperature slope, and every real liquid's falls as it warms.

``VDW_RADII`` is per ELEMENT, in angstrom, and feeds only the DERIVED tier of
``properties/dielectric.ionic_radius`` -- the curated ionic radii are a separate
table in that module, because this source has none.
"""

from __future__ import annotations

'''


def render(table: dict, vdw: dict[str, float]) -> str:
    lines = [HEADER]
    lines.append(
        "PERMITTIVITY: dict[str, tuple[tuple[float, float, float, float], "
        "tuple[float, float], str, str]] = {\n"
    )
    for key in sorted(table, key=lambda k: -table[k]["eps_298"]):
        e = table[key]
        a, b, c, d = e["coeffs"]
        lo, hi = e["range"]
        lines.append(
            f"    # {e['name']} [{e['cas']}] -- eps(298 K) = {e['eps_298']:.3f}\n"
            f"    {key!r}: (\n"
            f"        ({a!r}, {b!r}, {c!r}, {d!r}),\n"
            f"        ({lo!r}, {hi!r}),\n"
            f"        {e['kind']!r},\n"
            f"        {e['source']!r},\n"
            f"    ),\n"
        )
    lines.append("}\n\n")
    lines.append("# angstrom. chemicals.elements.periodic_table (Alvarez 2013 / Bondi).\n")
    lines.append("VDW_RADII: dict[str, float] = {\n")
    for symbol in ELEMENTS:
        if symbol in vdw:
            lines.append(f"    {symbol!r}: {vdw[symbol]!r},\n")
    lines.append("}\n")
    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    table, notes = collect()
    vdw = radii()

    print(f"candidates: {len(CANDIDATES)}   permittivity entries: {len(table)}")
    kinds: dict[str, int] = {}
    for e in table.values():
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    for kind, count in sorted(kinds.items()):
        print(f"   {kind:14s} {count}")
    print(f"   elements with a vdW radius: {len(vdw)}")
    if notes:
        print(f"\nSKIPPED ({len(notes)}), each with its reason:")
        for note in notes:
            print(f"   {note}")

    text = render(table, vdw)
    if args.dry_run:
        print(f"\n--dry-run: would write {len(text)} bytes to {OUT}")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"\nwrote {OUT} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

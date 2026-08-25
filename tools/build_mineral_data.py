"""Regenerate ``chemsim.properties.mineral_data``.

    python tools/build_mineral_data.py            # writes the module
    python tools/build_mineral_data.py --dry-run  # report only, write nothing

## THE QUESTION THIS SCRIPT HAD TO ANSWER FIRST: is a lattice a molecule?

"Make it from natural things" bottoms out at an element or a MINERAL, and a
mineral is not a molecule -- it is an ionic lattice. So there were two candidate
honest forms and the brief for this work asked which one is right:

    (a) the LATTICE gets its own entry, priced on the solid basis;
    (b) ion-by-ion, plus a lattice energy.

**The answer is measured, not argued, and it is neither of those two on its
own.** The engine's only route from a solid into solution is the ideal-solubility
FUSION LAW, ``ln a_sat = -(Hfus/R)(1/T - 1/Tm)``, and applied to an ionic
lattice that law is wrong by up to three orders of magnitude IN BOTH
DIRECTIONS -- measured against tabulated aqueous solubilities at 298 K:

    salt      fusion law     measured      ratio
    NaCl      0.015 mol/L    6.15 mol/L    0.0025   407x too INSOLUBLE
    K2CO3     0.014          8.03          0.0017   585x too insoluble
    Na2CO3    0.008          2.06          0.0040   251x too insoluble
    KNO3      8.96           3.51          2.55       2.6x too SOLUBLE
    CaCO3     0.0015         0.00014      11.0       11x too soluble

A spread of 6,400x across five salts, and the sign flips. That is not a bias a
factor could absorb -- it is the wrong law. The reason is plain once stated:
Tm and Hfus describe lattice -> MELT, while dissolution is lattice -> HYDRATED
IONS, and the hydration energy is an independent quantity that appears nowhere
in a fusion pair. Calcite has a huge lattice energy and feeble hydration; rock
salt has enormous hydration. Neither number is in Tm or Hfus.

So:

  * **the lattice DOES need its own entry** -- solid-basis Hf/Gf/S0 is what a
    solubility product or a calcination (CaCO3(s) -> CaO(s) + CO2(g)) would be
    computed from, and both are on the backlog;
  * **but that entry must NOT be handed to the phase model**, because the only
    dissolution law available to it is the one measured wrong above. This table
    is therefore REFERENCE DATA and ``thermochemistry`` refuses a lattice SMILES
    by name, pointing at the ion-by-ion representation instead;
  * **and ion-by-ion is the representation for anything DISSOLVED**, which is
    what a mineral in a flask actually is. That already works: nitrate comes
    from nitric acid's pKa, sulfate from sulfuric acid's, and a spectator cation
    is a zero reference that cancels out of every equilibrium it appears in.

That is the honest form, and the numbers above are re-measured by
``validation/game_gates.py`` so the verdict cannot quietly become stale if a
solubility mechanic ever lands.

## Provenance discipline

Identical to ``tools/build_element_data.py``, whose reference entropies this
script imports rather than re-deriving -- the element table IS the basis a
mineral's Gf is derived against, which is what makes closing the element class
pay for itself here:

  * dGf DERIVED from dHf and S0 against the CRC element reference states, never
    transcribed;
  * **both halves of an entry from the SAME database or the entry is refused.**
    This bites: FeSO4's S0s is 107.5 J/(mol K) from CRC and 120.93 from
    WEBBOOK -- 13.4 apart, which is 4 kJ/mol in Gf;
  * every estimated method excluded explicitly;
  * ``CRC_INORG`` classified as EXPERIMENTAL, which it is -- see the element
    builder's docstring for why inheriting ``build_physical_data``'s
    classification would have refused the entire floor.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from build_element_data import (  # noqa: E402
    TEMPERATURE_PREFERENCE, T_REF, preferred,
    reference_entropies, spread,
)

from chemsim.matter import Molecule  # noqa: E402

# Preference order for a SOLID formation pair. Both halves from the same entry.
SOLID_FORMATION_PREFERENCE = ("CRC", "WEBBOOK")

# ---------------------------------------------------------------------------
# The candidates: what a chain that bottoms out in nature actually digs up
# ---------------------------------------------------------------------------
# name, CAS, the ion-by-ion SMILES this engine uses for the DISSOLVED salt,
# element composition of one formula unit, and what it is FOR in the game.
CANDIDATES: list[tuple[str, str, str, dict, str]] = [
    ("calcite", "471-34-1", "[Ca+2].[O-]C(=O)[O-]",
     {"Ca": 1, "C": 1, "O": 3}, "limestone -- calcination to quicklime"),
    ("quicklime", "1305-78-8", "[Ca+2].[O-2]",
     {"Ca": 1, "O": 1}, "the product of calcining limestone"),
    ("slaked lime", "1305-62-0", "[Ca+2].[OH-].[OH-]",
     {"Ca": 1, "O": 2, "H": 2}, "quicklime + water; a cheap strong base"),
    ("green vitriol", "7720-78-7", "[Fe+2].[O-]S(=O)(=O)[O-]",
     {"Fe": 1, "S": 1, "O": 4},
     "dry-distils to the H2SO4 SEED that bootstraps chain 2"),
    ("pyrite", "1309-36-0", "[Fe+2].[S-][S-]",
     {"Fe": 1, "S": 2}, "fool's gold -- roasts to SO2, an ore route to chain 2"),
    ("potash", "584-08-7", "[K+].[K+].[O-]C(=O)[O-]",
     {"K": 2, "C": 1, "O": 3}, "wood ash -- the lye of chain 1's detour A"),
    ("soda ash", "497-19-8", "[Na+].[Na+].[O-]C(=O)[O-]",
     {"Na": 2, "C": 1, "O": 3}, "the sodium twin of potash"),
    ("saltpetre", "7757-79-1", "[K+].[O-][N+](=O)[O-]",
     {"K": 1, "N": 1, "O": 3}, "the nitre bed -- chain 2's nitrogen carrier"),
    ("rock salt", "7647-14-5", "[Na+].[Cl-]",
     {"Na": 1, "Cl": 1}, "brine, and the chlor-alkali route"),
    ("Glauber's salt", "7757-82-6", "[Na+].[Na+].[O-]S(=O)(=O)[O-]",
     {"Na": 2, "S": 1, "O": 4}, "the neutralised residue of a sulfuric process"),
    ("potassium bisulfate", "7646-93-7", "[K+].[O-]S(=O)(=O)O",
     {"K": 1, "S": 1, "O": 4, "H": 1},
     "what is LEFT in the retort after HNO3 is distilled off saltpetre"),
    ("caustic potash", "1310-58-3", "[K+].[OH-]",
     {"K": 1, "O": 1, "H": 1}, "the lye potash becomes with slaked lime"),
    ("caustic soda", "1310-73-2", "[Na+].[OH-]",
     {"Na": 1, "O": 1, "H": 1}, "lye"),
    ("blue vitriol", "7758-98-7", "[Cu+2].[O-]S(=O)(=O)[O-]",
     {"Cu": 1, "S": 1, "O": 4}, "a second vitriol, for contrast"),
    # --- added for M3: the lattices a METATHESIS actually drops -------------
    # These are here to be PRECIPITATED rather than dug up, which is a
    # different job from the fourteen above -- but the record is identical, so
    # the table is the same table. What changed is that `ion_data` now supplies
    # an aqueous-basis partner for the subtraction, so a Ksp exists.
    ("chlorargyrite", "7783-90-6", "[Ag+].[Cl-]",
     {"Ag": 1, "Cl": 1}, "AgCl -- the canonical 'it went cloudy' precipitate"),
    ("bromargyrite", "7785-23-1", "[Ag+].[Br-]",
     {"Ag": 1, "Br": 1}, "AgBr -- the photographic halide"),
    ("iodargyrite", "7783-96-2", "[Ag+].[I-]",
     {"Ag": 1, "I": 1}, "AgI -- the least soluble silver halide"),
    ("lunar caustic", "7761-88-8", "[Ag+].[O-][N+](=O)[O-]",
     {"Ag": 1, "N": 1, "O": 3},
     "AgNO3 -- the SOLUBLE reagent; it must NOT precipitate, which is a test"),
    ("barite", "7727-43-7", "[Ba+2].[O-]S(=O)(=O)[O-]",
     {"Ba": 1, "S": 1, "O": 4}, "BaSO4 -- gravimetric sulfate, and stone-insoluble"),
    ("barium chloride", "10361-37-2", "[Ba+2].[Cl-].[Cl-]",
     {"Ba": 1, "Cl": 2}, "the soluble barium reagent barite is precipitated from"),
    # ⚠ ANHYDRITE, NOT GYPSUM. M1 re-labelled three `acid-displacement` steps
    # `acid-displacement-precipitating` for a "gypsum" precipitation, and gypsum
    # is the DIHYDRATE, CaSO4.2H2O. This entry is the anhydrous lattice, which
    # is what CRC prices under this CAS and what an anhydrous engine can model.
    # Naming it anhydrite rather than gypsum is the honest form; the hydrate is
    # a separate species with its own lattice and it is not here.
    ("anhydrite", "7778-18-9", "[Ca+2].[O-]S(=O)(=O)[O-]",
     {"Ca": 1, "S": 1, "O": 4},
     "CaSO4 -- what M1's three acid-displacement steps drop (as the anhydrate)"),
    ("anglesite", "7446-14-2", "[Pb+2].[O-]S(=O)(=O)[O-]",
     {"Pb": 1, "S": 1, "O": 4}, "PbSO4"),
    ("lead iodide", "10101-63-0", "[Pb+2].[I-].[I-]",
     {"Pb": 1, "I": 2}, "PbI2 -- the golden rain"),
    ("chrome yellow", "7758-97-6", "[Pb+2].[O-][Cr](=O)(=O)[O-]",
     {"Pb": 1, "Cr": 1, "O": 4},
     "PbCrO4 -- a named pigment target, and a visible REFUSAL if unpriced"),
    ("fluorite", "7789-75-5", "[Ca+2].[F-].[F-]",
     {"Ca": 1, "F": 2}, "CaF2 -- and the source of HF"),
    ("sphalerite", "1314-98-3", "[Zn+2].[S-2]",
     {"Zn": 1, "S": 1}, "ZnS -- the zinc ore, and a sulfide precipitate"),
    ("brucite", "1309-42-8", "[Mg+2].[OH-].[OH-]",
     {"Mg": 1, "O": 2, "H": 2}, "Mg(OH)2 -- milk of magnesia"),
]

# Measured aqueous solubility at 298 K, mol/L, for the FUSION-LAW BOUND. Hand
# entered from the CRC solubility tables and marked as such: this is not used to
# build any record, it exists only so the verdict on the fusion law above is a
# measurement rather than an argument. A value with no auditable source does not
# get written down, so the list is short on purpose.
SOLUBILITY_298: dict[str, tuple[float, str]] = {
    "rock salt": (6.15, "359 g/L (CRC), MW 58.44"),
    "saltpetre": (3.51, "355 g/L (CRC), MW 101.10"),
    "potash": (8.03, "1110 g/L (CRC), MW 138.21"),
    "soda ash": (2.06, "218 g/L (CRC), MW 105.99"),
    "calcite": (1.4e-4, "14 mg/L (CRC), MW 100.09"),
}


def solid_formation_pair(cas: str):
    """(Hfs J/mol, S0s J/mol/K, method), both halves from the SAME database."""
    from chemicals import Hfs, Hfs_methods, S0s, S0s_methods

    h = dict(spread(Hfs, Hfs_methods, cas))
    s = dict(spread(S0s, S0s_methods, cas))
    for m in SOLID_FORMATION_PREFERENCE:
        if m in h and m in s:
            return h[m], s[m], m
    shared = sorted(set(h) & set(s))
    if shared:
        return h[shared[0]], s[shared[0]], shared[0]
    return None


def solid_condensed_pair(cas: str):
    """(Cps J/(mol K), Vm m3/mol) for the crystal, or ``None`` where absent.

    ⚠ THESE TWO ARE FOR THE VESSEL'S BOOKKEEPING, NOT FOR ITS EQUILIBRIA. A
    mineral in the solid block occupies volume and holds heat, and Layer 4 asks
    every species for both; before M6 a lattice had no answer and the block
    borrowed an ion's nominal placeholder. ``Cps`` comes from the SAME CRC row
    as the ``Hfs``/``S0s`` pair above -- one row, one compilation -- and ``Vm``
    from the CRC inorganic solid-density table.

    ⚠ AND ``Cps`` IS NOT USED TO CORRECT ln K, WHICH WAS MEASURED AND REFUSED.
    It is a 298 K constant while a gas Cp here is a real polynomial, so a
    ``dCp(T)`` built from the pair is half-corrected: it moves calcination's
    1 bar decomposition temperature from 1118.2 K to 1107.7 K (literature
    ~1170 K, so WORSE by 10 K) while moving portlandite's from 755.2 to 774.9 K
    (literature ~785 K, BETTER by 20 K). One improves and one degrades, which is
    the signature of a correction that is not consistently applied rather than
    of a missing physics term. ``solid_state.py`` therefore keeps dCp = 0 and
    says so, exactly as ``PrecipitationArrays.ln_Ksp`` does.
    """
    import chemicals.heat_capacity as hc
    import chemicals.volume as vo

    hc._load_Cp_data()
    vo._load_rho_data()
    cp = hc.CRC_standard_data
    vm = vo.rho_data_CRC_inorg_s_const
    c = float(cp.loc[cas, "Cps"]) if cas in cp.index else None
    if c is not None and c != c:                    # NaN
        c = None
    v = float(vm.loc[cas, "Vm"]) if cas in vm.index else None
    if v is not None and v != v:
        v = None
    return c, v


def collect():
    from chemicals import (
        Hfs, Hfs_methods, Hfus, Hfus_methods, S0s, S0s_methods, Tm, Tm_methods,
    )

    refs = reference_entropies()
    table: dict[str, dict] = {}
    notes: list[str] = []
    report: list[str] = []

    for name, cas, smiles, comp, purpose in CANDIDATES:
        # The ion-by-ion SMILES is the identity the game uses; check every
        # fragment parses so a typo cannot become a silent miss later.
        try:
            ions = tuple(Molecule.from_smiles(p).smiles for p in smiles.split("."))
        except Exception as exc:                            # noqa: BLE001
            notes.append(f"{name}: ion SMILES {smiles!r} does not parse ({exc})")
            continue

        got = solid_formation_pair(cas)
        if got is None:
            hs = [m for m, _ in spread(Hfs, Hfs_methods, cas)]
            ss = [m for m, _ in spread(S0s, S0s_methods, cas)]
            notes.append(
                f"{name}: REFUSED -- Hfs from {hs or 'nothing'} and S0s from "
                f"{ss or 'nothing'} share no database, and mixing two "
                "tabulations inside one entry is what this project forbids"
            )
            continue
        H, S, method = got

        dS = S
        missing = []
        for el, k in comp.items():
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

        tm = preferred(Tm, Tm_methods, cas, TEMPERATURE_PREFERENCE)
        hf = preferred(Hfus, Hfus_methods, cas, ("CRC", "JANAF"), kw=True)

        # The FUSION-LAW BOUND, computed against the actual measured
        # solubility. This is the number that decides whether a lattice may
        # enter the phase model, so it is computed here rather than asserted.
        bound = None
        if name in SOLUBILITY_298 and tm is not None and hf is not None:
            import math
            C_WATER = 1.0 / 0.01807
            a = math.exp(-(hf[0] / 8.31446261815324)
                         * (1.0 / T_REF - 1.0 / tm[0]))
            a = min(a, 1.0)
            pred = a * C_WATER / (1.0 - a) if a < 1.0 else float("inf")
            real = SOLUBILITY_298[name][0]
            bound = (round(pred, 6), real, round(pred / real, 5))

        Cps, Vm = solid_condensed_pair(cas)
        table[name] = dict(
            name=name, cas=cas, ions=ions, lattice=Molecule.from_smiles(
                ".".join(ions)).smiles,
            formula=comp, purpose=purpose,
            Hf_solid=round(Hf, 2), Gf_solid=round(Gf, 2), S0_solid=round(S, 2),
            Tm=round(tm[0], 2) if tm else None,
            Hfus=round(hf[0] / 1000.0, 3) if hf else None,
            source=(f"Hfs and S0s both from {method} via chemicals 1.5.2; "
                    f"Gf DERIVED against the CRC element reference states"),
            physical_source="; ".join(
                f"{k}={v[1]}" for k, v in (("Tm", tm), ("Hfus", hf))
                if v is not None
            ) or "no measured Tm or Hfus in any source consulted",
            fusion_law_bound=bound,
            solubility_note=SOLUBILITY_298.get(name, (None, None))[1],
            Cp_solid=round(Cps, 2) if Cps is not None else None,
            Vm_solid=round(Vm * 1000.0, 6) if Vm is not None else None,
            condensed_source=(
                "Cps from the same CRC row as Hfs/S0s; Vm from the CRC "
                "inorganic solid-density table, via chemicals 1.5.2"
                if Cps is not None and Vm is not None
                else "; ".join(
                    f"no {k}" for k, v in (("Cps", Cps), ("Vm", Vm))
                    if v is None)
            ),
        )
        report.append(
            f"  {name:20s} Hfs spread "
            f"{[(m, round(v/1000, 1)) for m, v in spread(Hfs, Hfs_methods, cas)]}"
            f"  S0s spread "
            f"{[(m, round(v, 2)) for m, v in spread(S0s, S0s_methods, cas)]}"
        )

    return table, notes, report


HEADER = '''"""Layer 1 -- MINERALS: the other half of the floor, and a verdict on lattices.

GENERATED by ``tools/build_mineral_data.py`` from ``chemicals`` 1.5.2. Do not
hand-edit: regenerate. That script's docstring carries the argument and the
measurements; the short version is below.

## A LATTICE IS NOT A MOLECULE, AND THE FUSION LAW SAYS SO OUT LOUD

"Make it from natural things" bottoms out at an element or a mineral, and a
mineral is an ionic lattice. The engine's only route from a solid into solution
is the ideal-solubility FUSION LAW, ``ln a_sat = -(Hfus/R)(1/T - 1/Tm)``, and
applied to an ionic lattice that law is wrong by up to three orders of magnitude
IN BOTH DIRECTIONS -- measured against tabulated solubility at 298 K:

    NaCl    407x too INSOLUBLE       KNO3     2.6x too SOLUBLE
    K2CO3   585x too insoluble       CaCO3   11x   too soluble
    Na2CO3  251x too insoluble

6,400x of spread across five salts, with the sign flipping. Not a bias a factor
could absorb -- the wrong law. Tm and Hfus describe lattice -> MELT; dissolution
is lattice -> HYDRATED IONS, and the hydration energy appears in neither.

**Hence: this module is REFERENCE DATA, not a provider tier.** The solid-basis
Hf/Gf/S0 here is what a solubility product or a calcination
(CaCO3(s) -> CaO(s) + CO2(g)) would be computed from -- both on the backlog --
and ``thermochemistry`` REFUSES a lattice SMILES by name rather than handing it
to a dissolution law that is measurably wrong. What a mineral in a flask
actually is, is its IONS, and that already works: nitrate is priced from nitric
acid's pKa, sulfate from sulfuric acid's, and a spectator cation is a zero
reference that cancels out of every equilibrium it appears in.

``validation/game_gates.py`` re-measures the bound above, so the verdict cannot
go stale if a solubility mechanic ever lands.

## ⚠ WHAT M6 CHANGED, AND WHAT IT DID NOT

**The lattice is now a SPECIES the solid block can hold** -- ``lattice`` is its
canonical one-species SMILES and ``by_lattice()`` the index. Nothing above is
softened by that: it still never dissolves, still never boils, and
``thermochemistry`` still refuses it by name, because the fusion law is still
the wrong law. What changed is that a crystal can now REACT while staying a
crystal -- ``CaCO3(s) -> CaO(s) + CO2(g)`` -- which touches none of the
dissolution question.

⚠ **AND THE ION-BY-ION REPRESENTATION CANNOT EXPRESS THE LIME CYCLE, which is
the measurement that forced this.** Quicklime ion-by-ion is ``[Ca+2].[O-2]``,
and the oxide ion is in no aqueous table anywhere because it does not exist in
water -- CaO does not dissolve to Ca2+ + O2-, it HYDRATES. ``thermochemistry``
refuses ``[O-2]`` and ``solubility_product`` refuses quicklime for exactly that
reason. So there was no route to the product of calcining limestone that went
through ions, and the choice was the lattice or nothing.

``Cp_solid`` and ``Vm_solid`` are the price of that: a species in the solid
block occupies volume and holds heat. Both are measured, both from CRC, and
neither enters an equilibrium.

## Provenance

dGf is DERIVED from dHf and S0 against the CRC element reference states in
``element_data`` -- the same basis, which is what makes closing the element class
pay for itself here. Both halves of an entry come from the SAME database or the
entry is refused; that rule bites on FeSO4, whose S0s is 107.5 J/(mol K) from
CRC and 120.93 from WEBBOOK, 13.4 apart and worth 4 kJ/mol in Gf. Every
estimated method is excluded explicitly.
"""

from __future__ import annotations

from typing import NamedTuple


class MineralRecord(NamedTuple):
    """One mineral, on the SOLID basis, plus the ions it dissolves into.

    ``Hf_solid``/``Gf_solid`` are NOT on the ideal-gas basis every ``ThermoData``
    uses, which is exactly why this is a separate type in a separate module: a
    solid-basis number wearing a ThermoData would be silently shifted by
    ``standard_state`` and silently dissolved by the fusion law.
    """

    name: str
    cas: str
    ions: tuple                    # canonical SMILES of the dissolved ions
    # ⚠ THE LATTICE AS ONE SPECIES, canonical. Not a molecule and not a
    # solution: it is the crystal, and M6 is what made it need a name. The
    # solid block can now hold it whole, which is the only representation the
    # lime cycle has -- quicklime ion-by-ion needs ``[O-2]``, and the oxide ion
    # is absent from every aqueous table because it does not exist in water.
    lattice: str
    formula: dict                  # element counts of one formula unit
    purpose: str                   # what a chain wants it FOR
    Hf_solid: float                # kJ/mol, crystalline, 298.15 K
    Gf_solid: float                # kJ/mol, DERIVED
    S0_solid: float                # J/(mol K), absolute
    Tm: float | None               # K -- MELTING is what a fusion pair is for
    Hfus: float | None             # kJ/mol
    source: str
    physical_source: str
    # (fusion-law prediction mol/L, measured mol/L, ratio) where a measured
    # solubility exists. The verdict above, per species, as data.
    fusion_law_bound: tuple | None
    solubility_note: str | None
    # ⚠ THE VESSEL'S BOOKKEEPING HALF, and it is NOT part of any equilibrium.
    # A crystal in the solid block takes up room and holds heat; Layer 4 asks
    # every species for both. ``Cp_solid`` is a 298 K constant from the same
    # CRC row as ``Hf_solid``, and it is deliberately NOT used to put a
    # ``dCp(T)`` on any ln K -- see ``tools/build_mineral_data.py``, where that
    # correction was measured making one row better and one worse.
    Cp_solid: float | None = None      # J/(mol K), crystalline, 298.15 K
    Vm_solid: float | None = None      # L/mol, crystal molar volume
    condensed_source: str = ""
'''

FOOTER = '''

def lattice_smiles() -> frozenset:
    """Every ion-by-ion SMILES that names a mineral in this table.

    ``thermochemistry`` uses it for nothing -- a multi-fragment charged SMILES is
    already refused by the net-charge guard. It is here so a REFUSAL can name
    what the caller probably meant: "that is calcite, whose lattice this engine
    cannot dissolve; charge its ions".
    """
    return frozenset(r.ions for r in MINERALS.values())


def by_ions() -> dict:
    """Reverse index: the tuple of dissolved ions -> the mineral record."""
    return {r.ions: r for r in MINERALS.values()}


def by_lattice() -> dict:
    """Reverse index: the canonical LATTICE SMILES -> the mineral record.

    ⚠ THIS IS THE INDEX THAT LETS A CRYSTAL BE A SPECIES, and it is a different
    claim from ``by_ions``. ``by_ions`` says what a mineral becomes when it
    DISSOLVES, which is the only thing this table was for before M6. This one
    says what it is while it is still a solid -- and a species keyed here is
    priced on the solid basis, never boils, and is never handed to the fusion
    law. See ``properties/solid_state.py``.
    """
    return {r.lattice: r for r in MINERALS.values()}


def priced_solid(name: str) -> bool:
    """Can this mineral sit in a vessel's solid block at all?

    Needs the formation pair (every entry here has one) plus the two BOOKKEEPING
    numbers Layer 4 asks of every species. An entry missing either is reference
    data still, but it cannot be charged into a flask.
    """
    r = MINERALS.get(name)
    return r is not None and r.Cp_solid is not None and r.Vm_solid is not None
'''


def render(table: dict) -> str:
    out = [HEADER, "", "",
           "MINERALS: dict[str, MineralRecord] = {"]
    for name, rec in table.items():
        out.append(f"    # {rec['purpose']}")
        out.append(f"    {name!r}: MineralRecord(")
        out.append(f"        name={rec['name']!r}, cas={rec['cas']!r},")
        out.append(f"        ions={rec['ions']!r},")
        out.append(f"        lattice={rec['lattice']!r},")
        out.append(f"        formula={rec['formula']!r},")
        out.append(f"        purpose={rec['purpose']!r},")
        out.append(f"        Hf_solid={rec['Hf_solid']!r}, "
                   f"Gf_solid={rec['Gf_solid']!r}, "
                   f"S0_solid={rec['S0_solid']!r},")
        out.append(f"        Tm={rec['Tm']!r}, Hfus={rec['Hfus']!r},")
        out.append(f"        source={rec['source']!r},")
        out.append(f"        physical_source={rec['physical_source']!r},")
        out.append(f"        fusion_law_bound={rec['fusion_law_bound']!r},")
        out.append(f"        solubility_note={rec['solubility_note']!r},")
        out.append(f"        Cp_solid={rec['Cp_solid']!r}, "
                   f"Vm_solid={rec['Vm_solid']!r},")
        out.append(f"        condensed_source={rec['condensed_source']!r},")
        out.append("    ),")
    out.append("}")
    out.append(FOOTER)
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    table, notes, report = collect()

    print("=" * 78)
    print(f"MINERAL TABLE: {len(table)} entries")
    print("=" * 78)
    print(f"  {'mineral':20s} {'Hf(s)':>10s} {'Gf(s)':>10s} {'S0':>7s} "
          f"{'Tm':>8s} {'Hfus':>7s}")
    for name, rec in table.items():
        tm = f"{rec['Tm']:.1f}" if rec["Tm"] else "--"
        hf = f"{rec['Hfus']:.2f}" if rec["Hfus"] else "--"
        print(f"  {name:20s} {rec['Hf_solid']:10.1f} {rec['Gf_solid']:10.1f} "
              f"{rec['S0_solid']:7.1f} {tm:>8s} {hf:>7s}")

    print()
    print("=" * 78)
    print("THE FUSION LAW AGAINST MEASURED SOLUBILITY -- the lattice verdict")
    print("=" * 78)
    print(f"  {'mineral':20s} {'predicted':>12s} {'measured':>12s} {'ratio':>10s}")
    ratios = []
    for name, rec in table.items():
        b = rec["fusion_law_bound"]
        if b is None:
            continue
        pred, real, ratio = b
        ratios.append(ratio)
        print(f"  {name:20s} {pred:12.5f} {real:12.5f} {ratio:10.4f}")
    if ratios:
        print(f"\n  spread {max(ratios) / min(ratios):.0f}x, and the sign of the "
              "error FLIPS. The fusion law")
        print("  describes lattice -> melt; dissolution is lattice -> hydrated "
              "ions, and")
        print("  the hydration energy is in neither Tm nor Hfus. A lattice does "
              "NOT go")
        print("  into the phase model.")

    print()
    print("=" * 78)
    print("SOURCE SPREADS (so a same-database choice is auditable)")
    print("=" * 78)
    for line in report:
        print(line)

    print()
    print("=" * 78)
    print(f"REFUSED: {len(notes)}")
    print("=" * 78)
    for n in notes:
        print(f"  * {n}")

    target = REPO / "src" / "chemsim" / "properties" / "mineral_data.py"
    if args.dry_run:
        print(f"\n(dry run -- would write {target})")
        return
    target.write_text(render(table), encoding="utf-8")
    print(f"\nwrote {target}")


if __name__ == "__main__":
    main()

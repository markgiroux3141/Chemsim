"""P3 -- regenerate ``chemsim.engine.shelf_data`` from the corpus and the shelf.

    python tools/build_shelf.py            # writes the module
    python tools/build_shelf.py --dry-run  # report only, write nothing

Two inputs, and they answer two different questions:

``data/catalog/shelf.psv``   WHAT A PLAYER STARTS WITH -- 71 hand-maintained
                            rows, three tiers, an amount and a phase each. A
                            game-design declaration, argued in that file's own
                            header and in ``GAME_DESIGN.md`` 8.4-8.5.

``data/catalog/compounds``   WHAT EXISTS -- all 1583 corpus species, each put
                            through the same audit ``validation/catalog_coverage``
                            uses, so the picker knows which of them can be
                            charged into a flask and what the reason is when one
                            cannot.

## WHY THIS IS A GENERATED PYTHON MODULE AND NOT A RUNTIME PSV READ

``src/chemsim`` reads no file in ``data/`` at run time, ever -- the corpus
reaches the engine as ``physical_data``, ``mineral_data``, ``ion_data``,
``element_data`` and the Benson tables, every one of them generated. Two reasons
hold here as well. The package is installed from ``src`` alone, so ``data/`` is
not there to read; and resolving a shelf row is not a parse -- it is an audit
that prices 1583 species, which is minutes of work and cannot happen while a
player is opening a picker.

## THE RESOLUTION RULE, AND ⚠⚠⚠ A ROCK HAS **TWO** REPRESENTATIONS

A compound id becomes a ``{species: moles}`` charge. For a molecule that is a
parse. For a mineral it is a decision, because **this engine holds a solid in two
incompatible ways and each one has mechanics the other does not**:

    the LATTICE as one species     calcination, roasting, gas-solid reduction
                                   (``solid_state``, ``surface``: the lattice
                                   SMILES IS the species)
    its IONS in the solid block    dissolution and precipitation through a Ksp
                                   (``PrecipitationArrays``: "the lattice is not
                                   a species and never becomes one")

⚠ **AND NOTHING CONVERTS ONE INTO THE OTHER.** ``examples/lime_cycle.py`` says
it out loud -- *the two representations of CaCO3 are different species that do
not know about each other* -- and it is the constraint that decides every mineral
row on the shelf.

⚠⚠⚠ **PREFERRING THE LATTICE EVERYWHERE, WHICH IS THIS SCRIPT'S FIRST RULE AND
IS THE OBVIOUS ONE, PUT FIVE SHELF ROWS IN THE FLASK AS MATTER NO MECHANIC CAN
TOUCH.** Measured, 0.5 mol in 30 mol of water at 298 K for 600 s:

    rock salt as [Na+] + [Cl-] in the solid block   ->  0.5 mol dissolved, block empty
    rock salt as the lattice '[Cl-].[Na+]'          ->  0.5 mol of solid, for ever

Rock salt, fluorite, saltpetre, phosphate rock and anhydrite have NO solid-state
or surface reaction in this engine; dissolving is the only thing they do, and the
lattice cannot. Two of the five are load-bearing -- rock salt is the chlor-alkali
feedstock, and ``validation/phosphate_rock.py`` charges the rock exactly as
``{[Ca+2]: 3, PO4(3-): 2}`` in the solid block and records that *without the
lattice the rock is INERT, its ions sit in the solid block for ever*. C2 had
already measured the failure mode this rule would have walked into.

So the rule is MECHANISM-DRIVEN and the engine's own declarations decide it:

1. a lattice that a ``solid_state`` or ``surface`` reaction consumes is charged
   AS THE LATTICE -- that mechanic is reachable no other way;
2. otherwise a mineral with ions and a priceable ``Ksp`` is charged as its IONS,
   in the declared phase: ``solid`` is a crop that will dissolve, and that is
   what a rock in a bottle should do;
3. otherwise charged fragments are charged as dissolved ions, with the
   multiplicity taken from the dot-separated SMILES -- ``[Ca+2].[F-].[F-]`` is 1
   mol of calcium to 2 of fluoride, and gypsum's two waters of crystallisation
   become real water in the flask;
4. otherwise the species is its own canonical SMILES, one entry.

⚠ **RULES 1 AND 2 COLLIDE ON SIX ROWS AND RULE 1 WINS, WHICH COSTS THEM THEIR
DISSOLUTION**: calcite, covellite, galena, sphalerite, cinnabar and green
vitriol can be calcined or roasted and cannot be dissolved by anything. That is
a NAMED ENGINE GAP rather than a preference -- the way out is a mechanic that
converts a lattice charge into its ions, and until there is one, limestone in
acid does nothing. The report at the bottom of this script prints all six.

⚠ **AND THE AUDIT'S OWN TIER ANSWERS A DIFFERENT QUESTION.** Seven rows --
calcite, fluorite, phosphate rock, anhydrite, green vitriol, saltpetre, rock
salt -- audit as tier ``ion``, because the electrolyte provider prices their
fragments before the mineral fallback is ever reached. The audit asks *can this
be priced at all*; the shelf asks *what species is in the bottle*, and those two
come apart on 7 of 71 rows.

## WHAT THE PHASE COLUMN IS FOR, MEASURED

The engine can answer "solid, liquid or gas at 298 K?" for most neutral species:
gas if the Antoine fit puts p_sat above 1 atm, solid if Tm is above 298.15 K,
liquid otherwise. It cannot answer for a lattice or an ion, and where it can it
is not always right -- so the column is DECLARED and this script reports every
disagreement rather than trusting either side silently.

⚠ **THE DISAGREEMENT THAT MATTERS IS OLIVE OIL, AND IT IS 550 K WIDE.** Triolein
gets ``Tm = 828.9 K`` from Joback, so the engine's own estimate says a bottle of
olive oil is a solid at room temperature; triolein melts at about 278 K. Joback
has no domain over a C57 triglyceride -- the same class of failure as the element
floor, one more rung out. A phase column derived from the estimator would have
put the oil in the solid block and no run would ever have said why.

EVERY PRINTED LINE HERE IS ASCII: the console is cp1252 and a warning glyph in a
``print`` kills the script mid-report.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))
sys.path.insert(0, os.path.join(_ROOT, "validation"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import catalog as cat  # noqa: E402
import catalog_coverage as cc  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    UnifacProvider,
    VolatilityProvider,
    electrolyte_provider,
)
from chemsim.properties import solid_state, surface  # noqa: E402
from chemsim.properties.mineral_data import MINERALS, MineralRecord  # noqa: E402
from chemsim.properties.solubility_product import (  # noqa: E402
    UnpricedLattice,
    solubility_product,
)

SHELF_PSV = os.path.join(_ROOT, "data", "catalog", "shelf.psv")
OUT = os.path.join(_ROOT, "src", "chemsim", "engine", "shelf_data.py")

TIERS = ("natural", "intermediate", "bottle")
PHASES = ("liquid", "gas", "solid")
T_REF = 298.15
ONE_ATM = 1.01325                       # bar


# ---------------------------------------------------------------------------
# the shelf file
# ---------------------------------------------------------------------------


def read_shelf(path: str = SHELF_PSV) -> list[tuple[str, str, float, str, str]]:
    """``shelf.psv`` -> rows, validated structurally and nothing more."""
    rows: list[tuple[str, str, float, str, str]] = []
    seen: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            cells = [c.strip() for c in line.split("|")]
            if len(cells) != 5:
                raise ValueError(
                    f"{path}:{n}: expected 5 fields (id | tier | amount | "
                    f"phase | note), got {len(cells)}: {line!r}"
                )
            cid, tier, amount, phase, note = cells
            if tier not in TIERS:
                raise ValueError(
                    f"{path}:{n}: tier {tier!r} is not one of {TIERS}. The tier "
                    f"is what lets the shelf SHRINK -- see the file header."
                )
            if phase not in PHASES:
                raise ValueError(
                    f"{path}:{n}: phase {phase!r} is not one of {PHASES}"
                )
            try:
                mol = float(amount)
            except ValueError:
                raise ValueError(
                    f"{path}:{n}: amount {amount!r} is not a number"
                ) from None
            if mol <= 0.0:
                raise ValueError(
                    f"{path}:{n}: amount {mol} must be positive -- an empty "
                    f"bottle is not a thing on a shelf"
                )
            if cid in seen:
                raise ValueError(
                    f"{path}:{n}: {cid!r} appears twice. Two bottles of one "
                    f"species is a real bench situation, but the STARTING shelf "
                    f"is one row per species."
                )
            seen.add(cid)
            rows.append((cid, tier, mol, phase, note))
    return rows


# ---------------------------------------------------------------------------
# resolution
# ---------------------------------------------------------------------------


def lattice_index() -> dict[str, MineralRecord]:
    """Canonical lattice SMILES -> the ``mineral_data`` record."""
    return {
        Molecule.from_smiles(rec.lattice).smiles: rec for rec in MINERALS.values()
    }


def reacting_lattices() -> frozenset[str]:
    """Every lattice SMILES a solid-state or surface reaction consumes or makes.

    Read off the engine's own declarations, not a list here, so the rule cannot
    drift from the mechanics it is about. These two are the only terms in which a
    lattice IS a species; everywhere else a solid is its ions.
    """
    return frozenset(solid_state.lattice_species() | surface.lattice_species())


def dissolves(rec: MineralRecord) -> bool:
    """Can ``PrecipitationArrays`` move this lattice between solid and solution?

    Both halves have to hold: it needs dissolved ions at all (a metal's ``ions``
    is empty on purpose) and its Ksp has to price on the aqueous basis. The
    refusals are facts about chemistry -- quicklime has no aqueous Ksp because
    CaO hydrates rather than dissolving -- so a refusal here is not a gap.
    """
    if not rec.ions:
        return False
    try:
        solubility_product(rec)
    except UnpricedLattice:
        return False
    return True


def fragments(smiles: str) -> tuple[list[str], bool]:
    """(canonical fragments with multiplicity, is any of them charged?).

    The multiplicity is the dot-separated SMILES' own: a formula unit written
    ``[Ca+2].[F-].[F-]`` says one calcium to two fluoride, and that is the only
    place the stoichiometry of a salt is recorded in this corpus.
    """
    parts: list[str] = []
    charged = False
    for piece in smiles.split("."):
        mol = Molecule.from_smiles(piece)
        parts.append(mol.smiles)
        if mol.charge != 0:
            charged = True
    return parts, charged


def engine_phase(smiles: str, thermo, vol) -> tuple[str, str]:
    """(phase at 298.15 K, why) as the ENGINE would answer, or ("", reason).

    ⚠ A Henry's-law species is a GAS here and that is not a shortcut. ``kind ==
    "henry"`` means the fit is a solubility constant rather than a vapour
    pressure -- the species does not condense at bench conditions at all -- so
    ``coefficient()`` is not a pressure and must not be compared to one. Reading
    it as a pressure put nitrogen, oxygen and carbon dioxide in the liquid.
    """
    try:
        mol = Molecule.from_smiles(smiles)
        t = thermo.get(mol)
        v = vol.get(mol)
    except Exception as exc:                                    # noqa: BLE001
        return "", f"{type(exc).__name__}: {str(exc)[:80]}"
    if v.kind == "henry":
        return "gas", "a Henry's-law species: it does not condense here"
    p = v.coefficient(T_REF) if v.condensable else 0.0
    if p > ONE_ATM:
        return "gas", f"p_sat({T_REF:.2f} K) = {p:.4g} bar, above 1 atm"
    if t.Tm is not None and t.Tm > T_REF:
        return "solid", f"Tm = {t.Tm:.2f} K, above {T_REF:.2f}"
    tm = "no Tm" if t.Tm is None else f"Tm = {t.Tm:.2f} K"
    return "liquid", f"p_sat = {p:.4g} bar and {tm}"


def resolve(comp, tier_of: dict[str, str], why_of: dict[str, str],
            lattices: dict[str, MineralRecord], reacting: frozenset[str],
            thermo, vol) -> dict:
    """One corpus compound -> everything the picker and the loader need.

    The four-way rule in the module docstring, in order. ``form`` records which
    branch answered, because a mineral's two representations are not
    interchangeable and a caller has to be able to see which one it got.
    """
    row = {
        "id": comp.id,
        "name": comp.name,
        "smiles": "",
        "form": "",
        "charge": (),
        "electrolyte": False,
        "lattice": "",
        "phase": "",
        "phase_why": "",
        "price_tier": tier_of.get(comp.id, "refused"),
        "refusal": "",
    }
    try:
        canon = Molecule.from_smiles(comp.smiles).smiles
    except Exception as exc:                                    # noqa: BLE001
        row["form"] = "unparseable"
        row["refusal"] = (
            f"the SMILES in the catalog does not parse: "
            f"{type(exc).__name__}: {str(exc)[:70]}"
        )
        return row
    row["smiles"] = canon

    if row["price_tier"] == "refused":
        row["refusal"] = why_of.get(comp.id) or (
            "refused a price by the element floor: no provider has a domain "
            "over this species"
        )
        # ⚠ THE CHARGE IS STILL RESOLVED. A greyed row has to be able to say
        # what it WOULD have been, and a curation session that prices the
        # species turns the row on with no edit to this file.

    parts, charged = fragments(comp.smiles)
    counts: dict[str, float] = {}
    for part in parts:
        counts[part] = counts.get(part, 0.0) + 1.0

    rec = lattices.get(canon)
    if rec is not None and (canon in reacting or not dissolves(rec)):
        # RULE 1. The lattice reacts as a solid, and no other representation can
        # reach that mechanic. It costs the row its dissolution where it had one.
        # ⚠ The second clause is not a widening: a lattice that dissolves NOWHERE
        # -- every metal, whose ``ions`` is empty on purpose -- has only this
        # representation, and calling that one a "molecule" would say a bar of
        # nickel and a nickel atom were the same entry.
        row["form"] = "lattice"
        row["lattice"] = rec.name
        row["charge"] = ((canon, 1.0),)
        row["phase"] = "solid"
        row["phase_why"] = (
            f"the lattice {rec.name!r}, on the solid basis"
            + (" -- a solid-state or surface reaction consumes it"
               if canon in reacting else
               " -- and nothing dissolves it, so this is its only form")
        )
        return row
    if rec is not None and dissolves(rec):
        # RULE 2. Nothing reacts it as a crystal, but a Ksp connects it to
        # solution, so a bottle of it is a crop of its OWN IONS in the solid
        # block -- the representation `validation/phosphate_rock.py` charges.
        row["form"] = "ions"
        row["lattice"] = rec.name
        row["electrolyte"] = True
        row["charge"] = tuple(counts.items())
        row["phase"] = "solid"
        row["phase_why"] = (
            f"the ions of {rec.name!r} in the solid block: no solid-state or "
            f"surface reaction consumes this lattice, and its Ksp does dissolve "
            f"it -- charged as the lattice it would be inert for ever"
        )
        return row
    if charged:
        # RULE 3. Charged fragments and no crystal of it in this engine.
        row["form"] = "ions"
        row["electrolyte"] = True
        row["charge"] = tuple(counts.items())
        row["phase"] = "liquid"
        row["phase_why"] = (
            "dissolved ions: charged fragments and no lattice record, so there "
            "is no crystal of it in this engine to charge"
        )
        return row

    # RULE 4. An ordinary molecule.
    row["form"] = "molecule"
    row["charge"] = ((canon, 1.0),)
    row["phase"], row["phase_why"] = engine_phase(canon, thermo, vol)
    if not row["phase"]:
        # The providers refused, so the engine has no opinion. Not a refusal of
        # the SPECIES -- ``price_tier`` already said whether it is chargeable --
        # and a solid is the honest default for something with no volatility.
        row["phase_why"] = f"no phase from the engine ({row['phase_why']})"
        row["phase"] = "solid"
    return row


# ---------------------------------------------------------------------------
# the module
# ---------------------------------------------------------------------------


_HEAD = '''\
"""Layer 6 -- GENERATED. What is on the shelf, and what every species costs.

Regenerate with ``python tools/build_shelf.py``; do not hand-edit. That script's
docstring carries the resolution rule and the measurements behind it. The two
inputs are ``data/catalog/shelf.psv`` (the three tiers, hand-maintained) and
``data/catalog/compounds`` (all {n_corpus} corpus species, audited).

``SHELF``   the {n_shelf} starting rows, in file order.
``ROSTER``  every corpus species by id -- the picker's whole content, including
            the {n_refused} that are REFUSED a price and may never be charged.
            A refused row carries its REASON, because GAME_DESIGN.md 8.3 says a
            player who cannot find sodium metal must be told the engine declines
            to price it rather than left to conclude the game is broken.

MEASURED AT GENERATION:

    corpus species                              {n_corpus:5d}
    ... chargeable                              {n_priced:5d}
    ... REFUSED a price                         {n_refused:5d}
    shelf rows                                  {n_shelf:5d}
    ... natural / intermediate / bottle         {n_nat:5d} /{n_int:4d} /{n_bot:4d}
    ... refused, and kept anyway                {n_shelf_refused:5d}
    ... charged as a reacting mineral LATTICE   {n_lattice:5d}
    ... charged as IONS                         {n_ionic:5d}
    ... a lattice that CANNOT be dissolved
        because it reacts as a crystal instead  {n_collide:5d}
    ... where the declared phase and the
        engine's own estimate DISAGREE          {n_disagree:5d}

Generated {stamp}.
"""

from __future__ import annotations

from typing import NamedTuple


class ShelfEntry(NamedTuple):
    """One row of ``data/catalog/shelf.psv``, as data."""

    id: str
    tier: str                   # natural | intermediate | bottle
    amount: float               # mol of the formula unit
    phase: str                  # liquid | gas | solid -- DECLARED
    note: str


class RosterEntry(NamedTuple):
    """One corpus species, resolved to something chargeable -- or refused.

    ``charge`` is (species SMILES, moles per formula unit): one pair for a
    molecule or a lattice, one per distinct ion for a salt, with the multiplicity
    taken from the dot-separated formula unit.

    ⚠ ``form`` IS NOT DECORATION -- it says which of a mineral's two
    representations this is, and they have disjoint mechanics. ``lattice``
    calcines, roasts and reduces and can never dissolve; ``ions`` in the solid
    block dissolve and precipitate through a Ksp and can never react as a
    crystal. Nothing in this engine converts one into the other. See
    ``tools/build_shelf.py``.

    ``electrolyte`` is True wherever the charge holds an ion, and a ``Scenario``
    that carries such a species must set ``electrolyte=True`` or the network
    cannot price it at all.
    """

    id: str
    name: str
    smiles: str                 # canonical, the whole formula unit
    form: str                   # molecule | lattice | ions | unparseable
    charge: tuple[tuple[str, float], ...]
    phase: str                  # where the engine would put it at 298.15 K
    phase_why: str
    electrolyte: bool
    lattice: str                # the mineral_data name, or ""
    price_tier: str             # the coverage audit's tier
    refusal: str                # "" when chargeable; the reason when not

    @property
    def chargeable(self) -> bool:
        return not self.refusal


'''


def render(shelf_rows, roster, stats) -> str:
    out = [_HEAD.format(**stats)]
    out.append("SHELF: tuple[ShelfEntry, ...] = (\n")
    for cid, tier, amount, phase, note in shelf_rows:
        out.append(
            f"    ShelfEntry({cid!r}, {tier!r}, {amount!r}, {phase!r},\n"
            f"               {note!r}),\n"
        )
    out.append(")\n\n")
    out.append("ROSTER: dict[str, RosterEntry] = {\n")
    for row in roster:
        out.append(
            f"    {row['id']!r}: RosterEntry(\n"
            f"        {row['id']!r}, {row['name']!r},\n"
            f"        {row['smiles']!r}, {row['form']!r},\n"
            f"        {tuple(row['charge'])!r},\n"
            f"        {row['phase']!r}, {row['phase_why']!r},\n"
            f"        {bool(row['electrolyte'])!r}, {row['lattice']!r}, "
            f"{row['price_tier']!r},\n"
            f"        {row['refusal']!r},\n"
            f"    ),\n"
        )
    out.append("}\n")
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    shelf_rows = read_shelf()
    compounds = cat.load_compounds()
    print(f"shelf.psv          {len(shelf_rows):5d} rows")
    print(f"corpus compounds   {len(compounds):5d}")

    missing = [cid for cid, *_ in shelf_rows if cid not in compounds]
    if missing:
        raise SystemExit(
            f"shelf.psv names {len(missing)} id(s) that are not in the compound "
            f"tables: {missing}. A shelf row must be a real species with a "
            f"molecular graph -- a `-marker` has none, and GAME_DESIGN.md 8.6 "
            f"forbids a shelf entry that is not a real VesselState."
        )

    print("auditing every corpus species (this is the slow half) ...")
    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    ionic = electrolyte_provider(base=thermo, volatility=vol)
    unifac = UnifacProvider()
    tier_of: dict[str, str] = {}
    why_of: dict[str, str] = {}
    for cid, rec in compounds.items():
        audit = cc.audit_compound(rec, thermo, vol, ionic, unifac)
        tier_of[cid] = audit["tier"]
        why_of[cid] = audit["why"]

    lattices = lattice_index()
    reacting = reacting_lattices()
    print(f"mineral lattices   {len(lattices):5d}"
          f"   ({len(reacting)} of them react as a crystal)")
    roster = [
        resolve(rec, tier_of, why_of, lattices, reacting, thermo, vol)
        for rec in compounds.values()
    ]
    by_id = {r["id"]: r for r in roster}

    # -- the report, which is the reason to run this rather than trust it ----
    n_refused = sum(1 for r in roster if r["refusal"])
    shelf_refused = [(cid, by_id[cid]["refusal"]) for cid, *_ in shelf_rows
                     if by_id[cid]["refusal"]]
    lattice_rows = [cid for cid, *_ in shelf_rows
                    if by_id[cid]["form"] == "lattice"]
    ionic_rows = [cid for cid, *_ in shelf_rows if by_id[cid]["form"] == "ions"]
    # The collision: it reacts as a crystal AND has a Ksp, so charging it as the
    # lattice is right for one mechanic and takes the other away.
    collide = [cid for cid in lattice_rows
               if dissolves(lattices[by_id[cid]["smiles"]])]
    disagree = [
        (cid, phase, by_id[cid]["phase"], by_id[cid]["phase_why"])
        for cid, _t, _a, phase, _n in shelf_rows
        if by_id[cid]["form"] == "molecule" and by_id[cid]["phase"] != phase
    ]

    print()
    print(f"REFUSED a price          {n_refused:5d} of {len(roster)}")
    print(f"shelf rows refused       {len(shelf_refused):5d}"
          f"   (kept: see shelf.psv's header)")
    for cid, reason in shelf_refused:
        print(f"    {cid:<24} {reason[:88]}")
    print()
    print(f"charged as a LATTICE     {len(lattice_rows):5d}"
          f"   (it reacts as a crystal)")
    for cid in lattice_rows:
        tier = by_id[cid]["price_tier"]
        flag = "   <- and it HAS a Ksp: no longer dissolvable" if cid in collide \
            else ""
        print(f"    {cid:<24} {by_id[cid]['lattice']:<18} "
              f"(audit tier {tier}){flag}")
    print()
    print(f"charged as IONS          {len(ionic_rows):5d}")
    stranded = []
    for cid in ionic_rows:
        _c, _t, _a, phase, _n = next(r for r in shelf_rows if r[0] == cid)
        has_ksp = bool(by_id[cid]["lattice"])
        if phase == "solid":
            where = "a crop that dissolves" if has_ksp else "SOLID IONS, INERT"
            if not has_ksp:
                stranded.append(cid)
        else:
            where = "dissolved"
        print(f"    {cid:<24} {where:<24} {dict(by_id[cid]['charge'])}")
    if stranded:
        print(f"    ^ {len(stranded)} row(s) declare `solid` with no Ksp behind "
              f"them, so their ions would sit")
        print("      in the block for ever. Every one is also REFUSED a price, "
              "so nothing can")
        print("      charge them today -- but a curation session that prices one "
              "inherits this.")
    print()
    print(f"THE COLLISION            {len(collide):5d}"
          f"   rows that react as a crystal AND have a Ksp.")
    print("    Rule 1 takes the lattice, so these can be calcined or roasted")
    print("    and can never be dissolved by anything. NAMED ENGINE GAP: there")
    print("    is no mechanic that turns a lattice charge into its ions.")
    for cid in collide:
        print(f"    {cid:<24} {by_id[cid]['lattice']}")
    print()
    print(f"PHASE DISAGREEMENTS      {len(disagree):5d}"
          f"   (declared vs the engine's own estimate)")
    for cid, declared, got, why in disagree:
        print(f"    {cid:<24} declared {declared:<7} engine {got:<7} {why}")
    if not disagree:
        print("    none -- and that is a claim worth re-reading, not a pass")

    stats = {
        "n_corpus": len(roster),
        "n_priced": len(roster) - n_refused,
        "n_refused": n_refused,
        "n_shelf": len(shelf_rows),
        "n_nat": sum(1 for _c, t, *_ in shelf_rows if t == "natural"),
        "n_int": sum(1 for _c, t, *_ in shelf_rows if t == "intermediate"),
        "n_bot": sum(1 for _c, t, *_ in shelf_rows if t == "bottle"),
        "n_shelf_refused": len(shelf_refused),
        "n_lattice": len(lattice_rows),
        "n_ionic": len(ionic_rows),
        "n_collide": len(collide),
        "n_disagree": len(disagree),
        "stamp": _dt.date.today().isoformat(),
    }
    text = render(shelf_rows, roster, stats)
    if args.dry_run:
        print(f"\n--dry-run: nothing written ({len(text)} bytes would go to {OUT})")
        return 0
    # ⚠ CRLF, matching ``src/chemsim/engine`` and every other generated module in
    # this repo. A generator that flips a file's line endings makes its own output
    # undiffable, and P4 hit that from the other side: rewriting documents with
    # ``newline="\n"`` turned five CRLF files into whole-file diffs and hid a
    # 1700-line change inside a 21000-line one.
    with open(OUT, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(text)
    print(f"\nwrote {OUT}  ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Regenerate ``chemsim.properties.critical_data`` and ``physical_data``.

Run this rather than hand-editing either module. Both hold values DERIVED from
external sources, and the derivation has to stay reproducible and auditable --
the same rule ``tools/build_benson_data.py`` obeys for the Benson tables.

    python tools/build_physical_data.py            # writes both modules
    python tools/build_physical_data.py --dry-run  # report only, write nothing

Two quite different things come out of one script because they are two halves of
one job -- giving a species Tb/Tc/Pc/Vc when Joback cannot:

``critical_data.py``   METHOD PARAMETERS for Wilson-Jasperson (Tc, Pc from a
                       known Tb) and Fedors (Vc), extracted from ``thermo``
                       0.6.1, which is MIT licensed (verified: ``thermo``'s
                       ``LICENSE.txt`` and its wheel metadata both say MIT, and
                       each source module carries the MIT grant in its header).
                       Analogous to ``joback_data.py``.

``physical_data.py``   MEASURED Tb / Tm / Hfus per species, extracted from
                       ``chemicals`` 1.5.2. Analogous to ``formation_data.py``.

## Why extract instead of calling the libraries at runtime

``thermo`` is a TEST-ONLY oracle in this project and ``chemicals`` is a
curation-time source. Promoting either to a runtime dependency would change the
project's dependency story, and worse, it would make a save/load cycle depend on
which version of a third-party package happens to be installed -- a saved vessel
must reproduce exactly. Extracting into pinned in-repo tables keeps the data
auditable and diffable, and leaves ``thermo`` free to stay an oracle that the
test suite can check us against.

## Trap 1: ``chemicals`` serves JOBACK PREDICTIONS through the same accessor as
## measured data, and will hand you your own estimate back as a "measurement"

``chemicals.Tb(cas)`` walks a preference-ordered list of sources and JOBACK is
one of them. For metformin the list is ``['JOBACK']`` and nothing else, and the
value returned -- 609.52 K -- is bit-identical to what ``chemsim``'s own Joback
implementation computes, because it is the same method on the same groups. Its
``Hfg`` is the same story: 279980 J/mol, which is our 279.98 kJ/mol.

Taking that at face value would have "closed" metformin's coverage gap by
looking up an estimate we already had, laundered into a measured-looking table
with a provenance string claiming CRC-grade data. ``_measured`` therefore
excludes JOBACK from every method list and refuses the species if nothing else
remains. Six of the seven coverage-audit failures were checked this way and two
-- metformin and saccharin -- have no measured Tb in this source at all.

## Trap 2: Fedors is published against the EXPLICIT-hydrogen graph, and its
## amine term means something different there

``thermo`` runs Fedors' alcohol and amine patterns against ``AddHs(mol)``. That
is not incidental. ``amine_smarts`` carries the clause ``!$([N]~[!#6])`` -- "no
non-carbon neighbour" -- and once hydrogens are real atoms an N-H bond satisfies
``[!#6]``, so the pattern stops matching primary and secondary amines entirely
and only tertiary ones survive. Ethylamine counts zero amine nitrogens in the
explicit view and one in the implicit view.

We reproduce ``thermo``'s behaviour exactly rather than the behaviour Fedors
arguably intended, so the test suite can cross-check us against the oracle to
the last decimal and catch any future drift. The cost of the choice is bounded
and worth stating: ``N_amine`` is 47.422 against ``N``'s 48.855, so each amine
nitrogen classified the other way moves Vc by 1.4 cm3/mol, which is well under
1% for any species in the table. ``matter.Molecule.substructure_matches``
gained an ``explicit_hydrogens`` flag for this, and its docstring says why the
two views are not interchangeable.

## Trap 3: Wilson-Jasperson's Pc is the weakest number in the chain

Measured against acetic anhydride: Tc 600.9 K vs 606.0 (0.8%), Pc 44.9 bar vs
40.0 (12% high). Pc feeds the acentric factor, which is derived by inverting
Lee-Kesler at Tb, which sets the whole vapour-pressure curve. That is why every
entry this script enables must pass the boils-at-1-atm cross-check in
``validation/physical_estimation.py`` before it is trusted -- Tb/Tc/Pc go in,
and the fitted Antoine curve has to come back out saying the species boils at
1 atm where it is measured to.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from chemsim.matter import Molecule  # noqa: E402

# ---------------------------------------------------------------------------
# The candidate species list -- the curated INPUT to this script
# ---------------------------------------------------------------------------
# Chosen for the classes Joback genuinely lacks (anhydrides, sulfoxides and
# sulfones, aryl and heteroaryl aldehydes, formamides, isocyanates, sulfonic
# acids, guanidines) plus the coverage-audit targets. Whether a species ENDS UP
# needing a measured Tb is decided by the script, not asserted here: everything
# is looked up, and the classification against Joback is printed so a candidate
# that turns out to resolve perfectly well without help is visible rather than
# quietly carried.
#
# Names are what ``chemicals`` resolves to a CAS number, and the SMILES is the
# identity the table is keyed by. Both are recorded so a wrong pairing -- a name
# that resolves to a different compound than the SMILES describes -- can be
# caught by the formula cross-check below rather than becoming a silent swap.
CANDIDATES: list[tuple[str, str]] = [
    # --- anhydrides -------------------------------------------------------
    ("acetic anhydride", "CC(=O)OC(C)=O"),
    ("propionic anhydride", "CCC(=O)OC(=O)CC"),
    ("maleic anhydride", "O=C1OC(=O)C=C1"),
    ("succinic anhydride", "O=C1CCC(=O)O1"),
    ("phthalic anhydride", "O=C1OC(=O)c2ccccc12"),
    ("benzoic anhydride", "O=C(OC(=O)c1ccccc1)c1ccccc1"),
    # --- aryl / heteroaryl aldehydes --------------------------------------
    ("benzaldehyde", "O=Cc1ccccc1"),
    ("vanillin", "O=Cc1ccc(O)c(OC)c1"),
    ("p-anisaldehyde", "O=Cc1ccc(OC)cc1"),
    ("salicylaldehyde", "O=Cc1ccccc1O"),
    ("piperonal", "O=Cc1ccc2OCOc2c1"),
    ("furfural", "O=Cc1ccco1"),
    # --- sulfur oxides ----------------------------------------------------
    ("dimethyl sulfoxide", "CS(C)=O"),
    ("dimethyl sulfone", "CS(C)(=O)=O"),
    ("sulfolane", "O=S1(=O)CCCC1"),
    ("diphenyl sulfoxide", "O=S(c1ccccc1)c1ccccc1"),
    ("methanesulfonic acid", "CS(=O)(=O)O"),
    ("benzenesulfonyl chloride", "O=S(=O)(Cl)c1ccccc1"),
    # --- amides / formamides ----------------------------------------------
    ("formamide", "NC=O"),
    ("N-methylformamide", "CNC=O"),
    ("N,N-dimethylformamide", "CN(C)C=O"),
    # --- isocyanates ------------------------------------------------------
    ("methyl isocyanate", "CN=C=O"),
    ("phenyl isocyanate", "O=C=Nc1ccccc1"),
    ("methylene diphenyl diisocyanate", "O=C=Nc1ccc(Cc2ccc(N=C=O)cc2)cc1"),
    # --- coverage-audit targets that are not in a class above -------------
    ("saccharin", "O=C1NS(=O)(=O)c2ccccc21"),
    ("metformin", "CN(C)C(=N)N=C(N)N"),
    ("glyphosate", "OC(=O)CNCP(=O)(O)O"),
    # --- S11: the oxo process's own three species -------------------------
    # ⚠⚠ ADDED BECAUSE A TEMPLATE NEEDED THEM AND NOT BECAUSE A LIST WAS BEING
    # TIDIED, which is S8's lesson applied the right way round: a species job
    # FOLLOWS the template it enables. ``hydroformylation_linear`` and its twin
    # made propene a reagent this project actually runs, and propene had no
    # measured record here -- so Joback was answering, at **Tb 264.92 K against
    # a measured 225.53 and Tc 427.64 against 364.9**, both about 17% high.
    #
    # ⚠ THE Tc ERROR IS NOT COSMETIC. An oxo reactor sits at 420 K, which is 55 K
    # ABOVE propene's real critical temperature and 8 K BELOW Joback's -- so the
    # engine condensed **0.91 mol of "liquid propene" into a supercritical
    # flask** and the reactor read 167 bar where it was charged to 200. A
    # boiling point is not a decoration in an engine with a still in it.
    #
    # ⚠ AND THE GENERAL CASE IS MUCH LARGER AND IS **NOT** FIXED HERE: 310
    # catalog species have an experimental Tb in ``chemicals`` and are absent
    # from this list, 229 of them price one today, and the mean |error| against
    # the measurement is 5.81% with a worst of 84.89%. See S11 in docs/history/MILESTONES.md;
    # adding them all moves every example's volatility and owes a tolerance
    # audit, which this addition does not (nothing but the oxo route holds any
    # of these three).
    ("propene", "CC=C"),
    # ⚠⚠ AND ETHYLENE, FOR `wacker_oxidation`. Joback gave it **Tb 234.56 K
    # against a measured 169.38** (+38.5%) and a Tc to match; S10 had already
    # flagged the same species from the other end, as an ~1574 J/(mol K) liquid
    # heat capacity at its melting point.
    #
    # ⚠⚠ **AND THE PREDICTION THIS ENTRY WAS MADE ON TURNED OUT TO BE WRONG,
    # WHICH IS WHY IT IS WRITTEN DOWN.** The brief was: a Wacker flask charged
    # with 0.20 mol of ethylene over 20 mol of water DISSOLVES 0.166 of it (83%),
    # the whole of the Wacker process is that a gas must dissolve before it meets
    # the copper, so a measured boiling point should move it. **It does not.**
    # Measured after: 0.16596 against 0.16588 -- four significant figures
    # unchanged -- because ethylene's vapour pressure comes from
    # `volatility._CURATED_ANTOINE` and **Tb does not feed that curve at all**.
    # What the entry actually corrects is Tc, Tm and Hvap.
    #
    # ⚠ The 83% is real and is a SEPARATE fault: a curated Antoine evaluated at
    # 400 K, which is 118 K above ethylene's critical temperature, gives
    # Psat = 219.9 bar and a Raoult-law dissolution where a Henry's-law solute is
    # meant. See S11 in docs/history/MILESTONES.md; nothing here fixes it.
    #
    # ⚠ Unlike the three above this one is NOT free: `competing_pathways` and
    # `named_routes` both hold ethylene. Measured cost, S11: the worst moved
    # number in `competing_pathways` is 0.20380 -> 0.20485 (0.5%) and
    # `named_routes` reports ethanol-hydration at 2.7% instead of 2.9%.
    ("ethylene", "C=C"),
    ("butanal", "CCCC=O"),
    ("2-methylpropanal", "CC(C)C=O"),
    # --- misc bench reagents ----------------------------------------------
    ("formic acid", "O=CO"),
    ("methyl formate", "COC=O"),
    ("carbon disulfide", "S=C=S"),
    ("triethyl phosphate", "CCOP(=O)(OCC)OCC"),
    ("thiourea", "NC(N)=S"),
    ("p-toluenesulfonic acid", "Cc1ccc(cc1)S(=O)(=O)O"),
]

# ---------------------------------------------------------------------------
# Source tiers -- the part of this script that decides what "measured" means
# ---------------------------------------------------------------------------
# ``chemicals`` serves every source through one accessor, in its own preference
# order, and its own documentation is what these tiers are read from -- not
# guesswork about the names.
#
# EXPERIMENTAL: described as critically evaluated experimental data. IUPAC is
# the Ambrose/Tsonopoulos critical-property series, MATTHEWS the inorganic
# equivalent, CRC the TRC compilation, WEBBOOK "mostly experimental and averaged
# values", HEOS values underlying REFPROP reference equations of state.
#
# COMPILATION: published, widely used, and NOT auditable to a measurement.
# ``chemicals`` says of YAWS "no data points are sourced in the work", of PSRK
# "experimental *and estimated* data", and of PINAMARTINES only that it is "a
# series of values in the supporting material" of a cubic-equation-of-state
# paper. The decisive check is empirical: PINAMARTINES gives saccharin a
# critical temperature of 968 K, and saccharin decomposes near 500 K without
# ever boiling, so that number cannot be a measurement of anything. These are
# kept where nothing better exists and STAMPED, never relabelled as measured.
#
# ESTIMATED: a group-contribution method. Excluded outright, because taking one
# means looking up an estimate we can already compute and calling it data. See
# Trap 1 -- for metformin, ``JOBACK`` is the only Tb source ``chemicals``
# offers, and its value is bit-identical to our own.
EXPERIMENTAL_METHODS = frozenset({
    "IUPAC", "MATTHEWS", "CRC", "CRC_ORG", "WEBBOOK", "HEOS",
    "COMMON_CHEMISTRY", "OPEN_NTBKM",
})
COMPILATION_METHODS = frozenset({"YAWS", "PSRK", "PINAMARTINES", "PD", "WIKIDATA"})
ESTIMATED_METHODS = frozenset({
    "JOBACK", "WILSON_JASPERSON", "FEDORS", "CRC_INORG", "WEBBOOK_AC",
})

TIER_EXPERIMENTAL = "experimental"
TIER_COMPILATION = "compilation"


def tier(method: str) -> str | None:
    """Which tier a ``chemicals`` method name belongs to, or None to refuse.

    An UNRECOGNISED method refuses rather than defaulting to either tier. A new
    source appearing in a future ``chemicals`` release must be classified
    deliberately, not swept into whichever bucket the code happened to prefer --
    that is the same rule ``build_benson_data`` applies to an unrecognised unit.
    """
    if method in EXPERIMENTAL_METHODS:
        return TIER_EXPERIMENTAL
    if method in COMPILATION_METHODS:
        return TIER_COMPILATION
    return None


def _measured(fn, methods_fn, cas: str, best_tier_only: bool = False, **kw):
    """The best non-estimated value, as ``(value, method, tier)``, or None.

    ``chemicals`` returns its method list in preference order, so the first
    surviving entry is its own best source. Returning the method name and tier
    alongside the value is the point: a table entry reading ``CRC_ORG`` is a
    different object from one reading ``YAWS``, and a record assembled from a
    measured Tb, a Wilson-Jasperson Tc and a Benson Hf is three tabulations in
    one entry that a caller has to be able to take apart.

    ``best_tier_only`` restricts the result to the experimental tier. Used for
    Tc/Pc/Vc, where an alternative with a KNOWN error exists: Wilson-Jasperson
    and Fedors are measurably wrong (Tc 1.9%, Pc 28% mean on polar species) but
    their provenance is exact, which beats a number of unknown origin that may
    itself be a group-contribution estimate from a method we cannot see. Tb gets
    no such choice -- Wilson-Jasperson takes it as an INPUT and nothing here
    estimates it -- so a compilation Tb is accepted and stamped.
    """
    try:
        methods = methods_fn(cas, **kw)
    except Exception:                                       # noqa: BLE001
        return None
    for method in methods:
        if method in ESTIMATED_METHODS:
            continue
        t = tier(method)
        if t is None:
            continue
        if best_tier_only and t != TIER_EXPERIMENTAL:
            continue
        try:
            value = fn(cas, method=method, **kw)
        except Exception:                                   # noqa: BLE001
            continue
        if value is not None:
            return float(value), method, t
    return None


# ---------------------------------------------------------------------------
# The CORPUS candidate list -- the GENERATED input to this script
# ---------------------------------------------------------------------------
def corpus_candidates(hand: set[str]) -> list[tuple[str, str, tuple[str, ...]]]:
    """Every ``data/catalog`` species with a molecular graph, deduped.

    ⚠⚠ THIS FUNCTION IS THE POINT OF S13. Before it, this script's only input
    was ``CANDIDATES`` above -- 37 hand-typed names -- and everything else in a
    1583-compound corpus fell to Joback. The file it writes LOOKED generated
    from the outside and was a transcription on the inside, and the coverage
    audit could not see the difference, because a Joback record RESOLVES: it
    answers every question put to it, confidently, in the wrong place.

    ⚠ The species returned here are resolved to a CAS number BY GRAPH
    (``"smiles=" + smi``) and not by name, which is both stronger and the only
    thing that could work: a catalog name is a display string, and 1583 of them
    are not going to be database keys. See ``collect(by_smiles=True)`` -- and
    note that the formula cross-check is kept anyway, because a resolver can
    still hand back a hydrate or a salt of what was asked for.

    ⚠ Names are kept for the COMMENT above each entry only. Nothing resolves on
    them once ``by_smiles`` is set.
    """
    import glob
    import os

    rows: list[tuple[str, str, tuple[str, ...]]] = []
    seen: set[str] = set(hand)
    catalog_dir = REPO / "data" / "catalog" / "compounds"
    for path in sorted(glob.glob(os.path.join(str(catalog_dir), "*.psv"))):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                cells = [c.strip() for c in line.split("|")]
                if len(cells) < 3 or cells[0] == "id":
                    continue
                name, smiles = cells[1], cells[2]
                if not smiles:
                    continue
                try:
                    key = Molecule.from_smiles(smiles).smiles
                except Exception:                           # noqa: BLE001
                    continue
                if key in seen:
                    continue
                seen.add(key)
                rows.append((name, key, (cells[0].replace("-", " "),)))
    return rows


def collect(
    candidates: list[tuple] | None = None,
    by_smiles: bool = False,
    quiet_notes: bool = False,
) -> tuple[dict, list[str]]:
    """Look up every candidate; return the table and the excluded-with-reason list.

    ``by_smiles`` resolves the CAS from the GRAPH rather than the name, which is
    what the corpus sweep needs. ``quiet_notes`` suppresses the per-species
    rejection lines: they are worth reading for 37 hand-picked candidates and
    are a 1200-line comment block for 1539 corpus ones, so the corpus pass
    reports COUNTS instead and ``main`` prints them.
    """
    from chemicals import (
        CAS_from_any, Hfus, Hfus_methods, Pc, Pc_methods, Tb, Tb_methods, Tc,
        Tc_methods, Tm, Tm_methods, Vc, Vc_methods, omega, omega_methods,
    )
    from chemicals.elements import simple_formula_parser

    from chemsim.properties.joback import JobackError
    from chemsim.properties.joback import estimate as joback_estimate

    table: dict[str, dict] = {}
    notes: list[str] = []
    counters: dict[str, int] = {
        "no_cas": 0, "formula_mismatch": 0, "no_tb": 0, "dropped": 0,
        "by_graph": 0, "by_name": 0,
    }

    from chemicals import search_chemical

    def db_formula_of(cas):
        """The database's own formula for this CAS, or None if it has none."""
        try:
            return simple_formula_parser(search_chemical(cas).formula)
        except Exception:                                   # noqa: BLE001
            return None

    for entry in (CANDIDATES if candidates is None else candidates):
        name, smiles = entry[0], entry[1]
        aliases = entry[2] if len(entry) > 2 else ()
        mol = Molecule.from_smiles(smiles)
        key = mol.smiles

        # ⚠⚠ TWO KEYS, AND NEITHER ONE ALONE IS ENOUGH. THIS IS S13's LARGEST
        # FINDING AND IT IS ABOUT S13's OWN INSTRUMENT.
        #
        # S11 found that ``CAS_from_any(smi)`` reads a bare SMILES as a FORMULA
        # -- ``"C"`` returns CARBON -- and the recorded fix was "always use
        # ``smiles=``". S13 built its whole corpus sweep on that fix, and the
        # first table it generated had **no aniline, no nitrobenzene and no
        # quinoline in it**, three of the most ordinary organic compounds there
        # are, because ``chemicals``' SMILES index simply does not contain them:
        #
        #     CAS_from_any("smiles=Nc1ccccc1")
        #       -> "A SMILES identifier was recognized, but it is not in the
        #          database."
        #     CAS_from_any("aniline")            -> 62-53-3, Tb 457.15 K
        #
        # ⚠ MEASURED: of 1069 corpus species with no graph-resolved CAS, **874
        # resolve by NAME with a matching formula, and 508 of those carry a
        # measured boiling point.** A sweep keyed only on the graph reported the
        # gap as 322 species when it is 830. **The fix for one trap became the
        # next trap**, and the instrument had to be audited before its finding
        # could be.
        #
        # ⚠ THE FORMULA CROSS-CHECK IS WHAT MAKES THE NAME PATH SAFE, and it
        # earns its place: it refuses 69 name matches outright. The graph is
        # tried FIRST because it is the stronger identity claim; a name is only
        # accepted when the database's own formula agrees with the graph the
        # table is keyed by.
        cas = None
        why = ""
        keys = [("smiles=" + key, True)] if by_smiles else []
        keys += [(name, False)] + [(a, False) for a in aliases]
        for probe, is_graph in keys:
            try:
                found = CAS_from_any(probe)
            except Exception as exc:                        # noqa: BLE001
                why = str(exc)[:60]
                continue
            db_formula = db_formula_of(found)
            if db_formula is not None and db_formula != mol.element_counts():
                counters["formula_mismatch"] += 1
                if not quiet_notes:
                    notes.append(
                        f"{name}: FORMULA MISMATCH via {probe!r} -- database "
                        f"{db_formula} vs SMILES {mol.element_counts()}; "
                        "refusing rather than pairing them"
                    )
                continue
            cas = found
            counters["by_graph" if is_graph else "by_name"] += 1
            break
        if cas is None:
            if not quiet_notes:
                notes.append(f"{name}: no CAS resolved ({why})")
            counters["no_cas"] += 1
            continue

        tb = _measured(Tb, Tb_methods, cas)
        tm = _measured(Tm, Tm_methods, cas)
        # ``Hfus`` takes its CAS as a keyword where Tb/Tm take it positionally,
        # and reports J/mol where this project works in kJ/mol.
        hfus = _measured(
            lambda _cas, method: Hfus(CASRN=_cas, method=method), Hfus_methods, cas
        )
        if hfus is not None:
            hfus = (hfus[0] / 1000.0, hfus[1], hfus[2])

        # Critical constants, EXPERIMENTAL TIER ONLY -- see ``_measured``. Where
        # none exists the record falls to Wilson-Jasperson and Fedors, whose
        # error is known because this repo measures it.
        tc = _measured(Tc, Tc_methods, cas, best_tier_only=True)
        pc = _measured(Pc, Pc_methods, cas, best_tier_only=True)
        vc = _measured(Vc, Vc_methods, cas, best_tier_only=True)
        if pc is not None:
            pc = (pc[0] / 1e5, pc[1], pc[2])                # Pa -> bar
        if vc is not None:
            vc = (vc[0] * 1e6, vc[1], vc[2])                # m3/mol -> cm3/mol
        # Tc and Pc are taken as a PAIR or not at all. They enter through the
        # acentric factor, omega = (ln(P_atm/Pc) - f0(Tb/Tc)) / f1(Tb/Tc), so a
        # measured Tc beside a Wilson-Jasperson Pc would mix two bases inside
        # one derived number -- the same rule that forbids ATCT enthalpy beside
        # CRC entropy inside one formation entry.
        if (tc is None) != (pc is None):
            if not quiet_notes:
                notes.append(
                    f"{name}: Tc/Pc SPLIT -- one measured and one not "
                    f"(Tc={tc}, Pc={pc}); taking neither, because they combine "
                    "into the acentric factor and must share a basis"
                )
            tc = pc = None

        # Recorded for CROSS-CHECKING only, never used to build a record. omega
        # is DERIVED here by inverting Lee-Kesler at Tb so the vapour-pressure
        # curve passes through the boiling point exactly; a tabulated omega is
        # therefore an independent check on that derivation, and independence is
        # the whole value of it.
        om = _measured(omega, omega_methods, cas)
        if om is not None and om[1] == "ACENTRIC_DEFINITION":
            om = None       # back-computed from a vapour pressure, not independent

        if tb is None:
            counters["no_tb"] += 1
            if not quiet_notes:
                offered = Tb_methods(cas)
                why = (
                    f"only estimated sources offered ({offered})"
                    if offered else "no source at all"
                )
                notes.append(
                    f"{name}: Tb REJECTED -- {why}. Wilson-Jasperson takes Tb "
                    "as an input, so this species gets no Tc/Pc from that route "
                    "and cannot reach a Benson formation half. Its Tm is still "
                    "kept below where one exists: a solid that never boils "
                    "still crystallises."
                )
            # Tm/Hfus are still worth keeping: a solid that never boils still
            # crystallises, and Tm drives the solubility law exponentially.
            if tm is None:
                counters["dropped"] += 1
                continue

        # Classify against Joback so a candidate that needs no help is visible.
        try:
            j = joback_estimate(mol)
            complete = None not in (j.Tb, j.Tc, j.Pc, j.Vc)
            joback_state = "complete" if complete else "partial"
        except JobackError:
            joback_state = "unfragmentable"

        table[key] = dict(
            name=name, cas=cas, Tb=tb, Tm=tm, Hfus=hfus, Tc=tc, Pc=pc, Vc=vc,
            omega_ref=om, joback=joback_state,
        )

    collect.counters = counters                             # type: ignore[attr-defined]
    return table, notes


# ---------------------------------------------------------------------------
# emitting
# ---------------------------------------------------------------------------


def critical_data_source() -> str:
    """Wilson-Jasperson and Fedors parameters, extracted from ``thermo``."""
    from thermo.group_contribution import fedors as fed
    from thermo.group_contribution import wilson_jasperson as wj

    from thermo import functional_groups as fg

    # Wilson-Jasperson's second-order terms and Fedors' two group terms are
    # SMARTS-matched, so the patterns are part of the method's parameters and
    # belong in the same pinned table as its numbers. Extracting them from
    # ``thermo`` rather than retyping them is the same discipline as everywhere
    # else here -- a retyped SMARTS is a silent wrong answer waiting to happen,
    # and this project has already paid for that once (PSRK's ``[HH]``).
    wj_smarts = {
        "OH": fg.alcohol_smarts,
        "-O-": fg.ether_smarts,
        "amine": tuple(fg.all_amine_smarts),
        "-CHO": fg.aldehyde_smarts,
        ">CO": fg.ketone_smarts,
        "-COOH": fg.carboxylic_acid_smarts,
        "-COO-": fg.ester_smarts,
        "-CN": fg.nitrile_smarts,
        "-NO2": fg.nitro_smarts,
        "halide": fg.haloalkane_smarts,
        "sulfur_groups": (
            fg.mercaptan_smarts, fg.sulfide_smarts, fg.disulfide_smarts,
        ),
        "siloxane": fg.siloxane_smarts,
    }
    fedors_smarts = {
        "O_alcohol": fg.alcohol_smarts,
        "N_amine": fg.amine_smarts,
    }

    def fmt(d: dict, indent: str = "    ") -> str:
        return "\n".join(f"{indent}{k!r}: {v!r}," for k, v in d.items())

    return f'''"""Layer 1 -- parameters for the Wilson-Jasperson and Fedors methods.

GENERATED by ``tools/build_physical_data.py`` from ``thermo`` 0.6.1 (MIT).
Do not hand-edit: regenerate.

These two methods exist here for one reason. Joback covers Tb/Tc/Pc/Vc but
refuses any molecule his groups cannot partition, and Benson -- the better
estimator sitting above him -- says nothing about critical properties at all,
because group additivity is a statement about formation quantities. So a species
Joback cannot fragment had no physical half available from anywhere, and its
Benson formation half was unreachable however good it was.

**Wilson-Jasperson takes Tb as an INPUT**, which is what makes the pair useful:
supply a boiling point and Tc and Pc follow, and Fedors gives Vc from structure
alone. That collapses the whole coverage problem to one lookup.

Accuracy, measured on acetic anhydride against CRC:

    Tc  600.9 vs 606.0 K      0.8%
    Pc   44.9 vs  40.0 bar   12%    <-- the weak number in the chain
    Vc  290.3 vs 294.0 cm3    1.3%

Pc is the one to watch. It feeds the acentric factor (derived by inverting
Lee-Kesler at Tb), which sets the entire vapour-pressure curve, so every entry
enabled by this route has to pass the boils-at-1-atm cross-check in
``validation/physical_estimation.py``.
"""

from __future__ import annotations

# --- Wilson-Jasperson ------------------------------------------------------
# Zero-order: per-ELEMENT increments, summed over the whole formula including
# hydrogen. ``None`` in the Pc table means the element was never regressed;
# that must refuse the estimate, not contribute zero.
WJ_TC_INCREMENTS: dict[str, float] = {{
{fmt(wj.Wilson_Jasperson_Tc_increments)}
}}

WJ_PC_INCREMENTS: dict[str, float | None] = {{
{fmt(wj.Wilson_Jasperson_Pc_increments)}
}}

# Second-order: functional-group corrections on top of the element sums.
WJ_TC_GROUPS: dict[str, float] = {{
{fmt(wj.Wilson_Jasperson_Tc_groups)}
}}

WJ_PC_GROUPS: dict[str, float] = {{
{fmt(wj.Wilson_Jasperson_Pc_groups)}
}}

# The SMARTS that count those groups. ``OH`` is split into ``OH_small`` and
# ``OH_large`` at match time by carbon count (< 5 vs >= 5), which is why one
# pattern serves two table keys.
WJ_GROUP_SMARTS: dict[str, str | tuple[str, ...]] = {{
{fmt(wj_smarts)}
}}

# --- Fedors ----------------------------------------------------------------
# Vc = 26.6 + sum(contributions), in cm3/mol. Atom counts include hydrogen;
# ring terms are per ring of that size; ``ring_ring_bonds`` counts rings bonded
# to another ring.
FEDORS_BASE: float = 26.6

FEDORS_CONTRIBUTIONS: dict[str, float] = {{
{fmt(fed.fedors_contributions)}
}}

# Outside this set Fedors has no increment, and the published method reports
# "errors found" rather than a number. That signal is kept -- it is the same
# discipline this project uses everywhere, and glyphosate's phosphorus is
# exactly the case it exists for.
FEDORS_ALLOWED_ATOMS: frozenset[str] = frozenset({sorted(fed.fedors_allowed_atoms)!r})

# Matched against the EXPLICIT-hydrogen graph, which changes what they mean.
# See ``tools/build_physical_data.py`` Trap 2: ``amine_smarts`` carries
# ``!$([N]~[!#6])``, and with hydrogens as real atoms an N-H bond satisfies
# ``[!#6]``, so only tertiary amines match. This reproduces ``thermo``'s
# behaviour exactly so the oracle test is exact; the cost is 1.4 cm3/mol per
# amine nitrogen classified the other way.
FEDORS_GROUP_SMARTS: dict[str, str] = {{
{fmt(fedors_smarts)}
}}
'''


def physical_data_source(table: dict, notes: list[str], summary: str = "") -> str:
    note_block = "\n".join(f"#   * {n}" for n in notes) or "#   (none)"
    sweep = sorted(k for k, r in table.items() if r["origin"] == "corpus")
    sweep_block = "\n".join(f"    {k!r}," for k in sweep) or "    # (none)"
    entries: list[str] = []
    for key, rec in sorted(table.items(), key=lambda kv: kv[1]["name"]):
        def half(v):
            if v is None:
                return "None"
            return f"Measured({v[0]!r}, {v[1]!r}, {v[2]!r})"
        entries.append("\n".join([
            f"    # {rec['name']}  (CAS {rec['cas']}; Joback: {rec['joback']}"
            f"{'' if rec['origin'] == 'hand' else '; corpus sweep'})",
            f"    {key!r}: MeasuredPhysical(",
            f"        Tb={half(rec['Tb'])},",
            f"        Tm={half(rec['Tm'])},",
            f"        Hfus={half(rec['Hfus'])},",
            f"        Tc={half(rec['Tc'])},",
            f"        Pc={half(rec['Pc'])},",
            f"        Vc={half(rec['Vc'])},",
            f"        omega_reference={half(rec['omega_ref'])},",
            "    ),",
        ]))

    return f'''"""Layer 1 -- MEASURED physical constants, keyed by canonical SMILES.

GENERATED by ``tools/build_physical_data.py`` from ``chemicals`` 1.5.2.
Do not hand-edit: regenerate.

Primarily this table exists to feed Wilson-Jasperson, which takes Tb as an input
and returns Tc and Pc. That is the coverage gap it closes: a species Joback
cannot fragment has no Tb from anywhere, and without a Tb there is no
vapour-pressure curve, no acentric factor, and no way to reach a Benson
formation half however well Benson prices it. Where measured critical constants
also exist they are here too, and they outrank the estimate.

**Nothing here is a group-contribution estimate, and that was not free.**
``chemicals`` serves Joback predictions through the same accessor as its measured
compilations. For metformin the ONLY Tb source it offers is ``JOBACK``, returning
609.52 K -- bit-identical to what this project's own Joback implementation
computes from the same groups, because it is the same method. Looking that up
would have closed a coverage gap by relabelling our own estimate as measured
data. Every estimated method is excluded and the species refused instead, which
is why metformin and saccharin carry no Tb below rather than a
confident-looking number.

## Two tiers, and why the distinction is kept on every value

``experimental``  critically evaluated measurement (IUPAC, CRC, MATTHEWS,
                  WEBBOOK, HEOS, Common Chemistry, Open Notebook melting points)

``compilation``   published, widely used, and NOT auditable to a measurement.
                  ``chemicals`` says of YAWS "no data points are sourced in the
                  work"; PSRK mixes experimental with estimated; PINAMARTINES is
                  supporting material from an equation-of-state paper. The
                  decisive check is empirical -- PINAMARTINES gives saccharin a
                  critical temperature of 968 K, and saccharin decomposes near
                  500 K without ever boiling, so that is not a measurement of
                  anything.

Tc/Pc/Vc are taken from the EXPERIMENTAL TIER ONLY. Where none exists the record
falls to Wilson-Jasperson and Fedors, and that is the deliberate choice: their
error is known, because ``validation/physical_estimation.py`` measures it, while
a number of unrecorded origin may itself be a group-contribution estimate from a
method we cannot inspect. **Tb gets no such choice** -- Wilson-Jasperson takes it
as an input and nothing in this project estimates a boiling point -- so a
compilation-tier Tb is accepted where it is the only source and stamped as such.
MDI is the case that matters: its Tb comes from YAWS.

Tc and Pc are taken as a PAIR or not at all. They combine into the acentric
factor, omega = (ln(P_atm/Pc) - f0(Tb/Tc)) / f1(Tb/Tc), so a measured Tc beside
an estimated Pc would mix two bases inside one derived number -- the same rule
that forbids an ATCT enthalpy beside a CRC entropy inside one formation entry.

``omega_reference`` is recorded for CROSS-CHECKING ONLY and never used to build a
record. This project derives omega by inverting Lee-Kesler at Tb so the fitted
vapour-pressure curve passes through the boiling point exactly; a tabulated omega
is therefore an INDEPENDENT check on that derivation, and independence is its
entire value. Entries whose only source is ``ACENTRIC_DEFINITION`` are dropped,
because that is omega back-computed from a vapour pressure and so is not
independent of the thing being checked.

## ⚠⚠ WHERE THE CANDIDATE LIST COMES FROM, AND WHY THAT SENTENCE IS THE POINT

Two inputs, and the second one is S13's whole subject:

``CANDIDATES``      a hand-typed list in the builder, for classes Joback
                    genuinely lacks and for species a template needed.

``corpus_candidates``  EVERY species in ``data/catalog`` with a molecular
                    graph, resolved to a CAS number by GRAPH.

Until S13 there was only the first, and it held 37 names. A file generated from
a hand-typed list reads as systematic from the outside and is a transcription on
the inside -- and nothing could see the difference, because a Joback record
RESOLVES. It answers every question put to it, confidently, in the wrong place.
``validation/boiling_points.py`` is the instrument that made that a number.

⚠ THE CORPUS PASS RESOLVES BY ``"smiles=" + smi`` AND NEVER BY NAME.
``chemicals.CAS_from_any("C")`` returns CARBON, because a bare SMILES is read as
a FORMULA and a single-letter SMILES is also an element symbol. The formula
cross-check is kept anyway: a graph query can still come back with a hydrate.

⚠ ``CORPUS_SWEEP`` below names every entry that came from the second input. It
exists so ``tests/test_critical.py`` can tell a batch-costed entry from a
hand-costed one -- see ``DELIBERATE_OVERRIDES`` there, and the batch cost
recorded in docs/history/MILESTONES.md §S13.

{summary}

WHAT WAS LOOKED UP AND REJECTED, with the reason (HAND-LIST CANDIDATES ONLY --
the corpus pass reports counts instead, because 1500 rejection lines is a
comment block nobody reads):
{note_block}
"""

from __future__ import annotations

from typing import NamedTuple


class Measured(NamedTuple):
    """One value, the database it came from, and how far that can be trusted."""

    value: float
    database: str
    tier: str                       # "experimental" | "compilation"


class MeasuredPhysical(NamedTuple):
    """Everything looked up for one species; ``None`` where nothing qualified.

    Tb/Tm/Tc in K, Hfus in kJ/mol, Pc in bar, Vc in cm3/mol. Each is a
    ``Measured`` rather than a bare float so provenance travels with the number
    instead of being reconstructed later by a caller who can only guess.
    """

    Tb: Measured | None = None
    Tm: Measured | None = None
    Hfus: Measured | None = None
    Tc: Measured | None = None
    Pc: Measured | None = None
    Vc: Measured | None = None
    omega_reference: Measured | None = None


# Every entry that came from the CORPUS sweep rather than the hand-typed
# candidate list. ``tests/test_critical.py`` reads this to tell a batch-costed
# override from a hand-costed one; nothing in the engine reads it.
CORPUS_SWEEP: frozenset[str] = frozenset((
{sweep_block}
))


MEASURED_PHYSICAL: dict[str, MeasuredPhysical] = {{
{chr(10).join(entries)}
}}
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    table, notes = collect()
    for rec in table.values():
        rec["origin"] = "hand"
    hand_counters = dict(collect.counters)                  # type: ignore[attr-defined]

    corpus = corpus_candidates(set(table))
    corpus_table, _ = collect(corpus, by_smiles=True, quiet_notes=True)
    corpus_counters = dict(collect.counters)                # type: ignore[attr-defined]
    for key, rec in corpus_table.items():
        if key in table:
            continue                # the hand list wins; it was chosen on purpose
        rec["origin"] = "corpus"
        table[key] = rec

    summary = chr(10).join((
        f"MEASURED AT GENERATION: {len(CANDIDATES)} hand-typed candidates and "
        f"{len(corpus)} corpus species with a",
        "molecular graph. Of the corpus pass:",
        "",
        f"    resolved to a CAS by GRAPH ('smiles=')    "
        f"{corpus_counters['by_graph']:5d}",
        f"    resolved to a CAS by NAME                 "
        f"{corpus_counters['by_name']:5d}   <- see the two-key note above",
        f"    name matched a DIFFERENT formula, refused "
        f"{corpus_counters['formula_mismatch']:5d}",
        f"    no CAS from either key                    "
        f"{corpus_counters['no_cas']:5d}",
        f"    CAS, but no non-estimated Tb anywhere     "
        f"{corpus_counters['no_tb']:5d}",
        f"    entered the table                         "
        f"{len(corpus_table):5d}",
    ))

    with_tb = sum(1 for r in table.values() if r["Tb"])
    n_corpus = sum(1 for r in table.values() if r["origin"] == "corpus")
    print(
        f"hand candidates: {len(CANDIDATES)}   corpus candidates: {len(corpus)}"
        f"   species in table: {len(table)} ({n_corpus} from the corpus)   "
        f"with a measured Tb: {with_tb}   hand-list Tb rejected or absent: "
        f"{len(notes)}"
    )
    print(f"hand-list counters:   {hand_counters}")
    print(f"corpus-pass counters: {corpus_counters}")
    print()
    print(f"{'species':32s} {'joback':15s} {'Tb':21s} {'Tm':12s} {'Hfus':8s} {'Tc':12s} {'Pc':11s} Vc")
    for _, rec in sorted(
        ((k, r) for k, r in table.items() if r["origin"] == "hand"),
        key=lambda kv: kv[1]["name"],
    ):
        def s(v, w=12):
            if not v:
                return f"{'-':<{w}}"
            mark = "" if v[2] == TIER_EXPERIMENTAL else "~"
            return f"{v[0]:.2f}{mark} {v[1][:w-9]:<{max(0, w-9)}}"
        print(
            f"  {rec['name']:30s} {rec['joback']:15s} {s(rec['Tb'], 21):21s} "
            f"{s(rec['Tm']):12s} {s(rec['Hfus'], 8):8s} {s(rec['Tc'], 11):11s} "
            f"{s(rec['Pc'], 11):11s} {s(rec['Vc'])}"
        )
    print("  ('~' marks a COMPILATION-tier value: published but not auditable to "
          "a measurement)")
    print()
    print("Tb REJECTED OR ABSENT, with reason (the species may still carry a Tm):")
    for n in notes:
        print(f"  {n}")

    by_state: dict[str, int] = {}
    for rec in table.values():
        by_state[rec["joback"]] = by_state.get(rec["joback"], 0) + 1
    print()
    print("Joback status of what was kept:", by_state)
    print(
        "  ('complete' entries need no help for coverage; they are kept so the\n"
        "   accuracy of overlaying a measured Tb on a working record can be\n"
        "   MEASURED rather than assumed -- see validation/physical_estimation.py)"
    )

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    out_dir = REPO / "src" / "chemsim" / "properties"
    for filename, source in (
        ("critical_data.py", critical_data_source()),
        ("physical_data.py", physical_data_source(table, notes, summary)),
    ):
        path = out_dir / filename
        path.write_text(source, encoding="utf-8")
        print(f"\nwrote {path.relative_to(REPO)}  ({len(source.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

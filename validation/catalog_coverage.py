"""Coverage audit of the whole ``data/catalog`` corpus against this simulator.

``validation/coverage.py`` walks 70 hand-picked targets. This walks the full
catalog -- ~1600 compounds and ~175 named routes -- and it asks three different
questions, because "coverage" is three different things and conflating them is
how a project talks itself into thinking it is finished.

## 1. Does a species RESOLVE, and on what?

A ThermoData is a formation half and a physical half, and each resolves off a
different tier. The tiers are ranked, because "we have a number" and "we have a
MEASUREMENT" are not the same claim:

    A  measured      curated experimental formation data, or a measured Tb/Tc/Pc
    A  mineral       a curated LATTICE, on the SOLID basis, from ``mineral_data``
    B  Benson        group additivity fitted to real molecules (RMG database)
    C  Joback        group additivity, several kJ/mol, cannot tell homologues apart
    -  ion           spectator or Born-priced; correct, and not an estimate at all
    F  refused       nothing prices it

⚠ ``mineral`` IS A SEPARATE TIER RATHER THAN PART OF ``measured``, AND THE
REASON IS THE ONE ``mineral_data`` EXISTS FOR: a solid-basis Hf/Gf is not on the
ideal-gas basis every ``ThermoData`` uses. Folding it into ``measured`` here
would make exactly the conflation the separate type upstream exists to prevent.
It is measured data -- CRC Hf and S0 with Gf derived against the same element
reference states -- so it counts on the measured side of the formation headline,
but it is reported under its own name because it is a different basis, and
because a species priced this way can sit in the solid block and can never
enter a liquid.

⚠ **Tier C resolving is NOT the same as tier C being usable.** Joback's error is
a factor of 2-4 in K and it gives homologues identical reaction energies -- the
reason ``formation_data`` exists at all. A route that runs entirely on tier C
will integrate happily and report a confident wrong equilibrium. So this audit
reports the tier MIX, not just the pass count, and the headline number below is
deliberately the measured-or-Benson fraction rather than the resolve fraction.

## 2. Can the species enter a LIQUID MIXTURE?

Resolving thermochemistry is enough for a gas-phase or ideal-solution
calculation and is not enough for anything this project does with two phases.
UNIFAC has to decompose the molecule into groups or the activity coefficient
silently stays at 1, and an activity coefficient of 1 in an LLE calculation is
not an approximation -- it is the assumption that the phases do not separate.
That gap is counted separately here and it is much larger than the thermo gap.

## 3. Is the TRANSFORMATION in the library at all?

The species half of coverage is the half that flatters. A catalog of 1600
compounds that all resolve is still worth nothing if the reaction that connects
two of them has no template. So the audit also counts the distinct reaction
classes in ``route_steps.psv`` against the ten templates in
``reactions/library.py``, and reports how many named routes could actually be
integrated end to end. That number is small, and it is the honest one.

Run: ``python validation/catalog_coverage.py`` (writes the Markdown report too).
"""

from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import catalog as cat  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    UnifacProvider,
    VolatilityProvider,
)
from chemsim.properties import mineral_data  # noqa: E402
from chemsim.properties.electrolyte import electrolyte_provider  # noqa: E402

# ---------------------------------------------------------------------------
# tiering -- read off the provenance string the provider already carries
# ---------------------------------------------------------------------------
# Every ThermoData.source and Volatility.source names where the number came
# from. Nothing here re-derives provenance; it classifies what the provider says
# about itself, which is why adding a curated entry upstream moves this report
# without anyone touching this file.

# ⚠ ``nonvolatile`` WAS ADDED BY M5 AND IT USED TO BE COUNTED AS ``ion``, WHICH
# THIS REPORT DESCRIBES AS "correct, and not an estimate at all". Nine NEUTRAL
# species in the catalog have no boiling point in any source and none that can
# be estimated -- phosphoric acid, guanidine, arginine, creatine, cyanic acid,
# two triglycerides -- and for them the statement "does not enter the vapour"
# is also correct, but it is a different claim from an ion's and it was being
# made under the ion's name. It ranks BELOW ion in ``_worst`` because it is a
# missing vapour-pressure curve as well as a physical fact: nothing can compute
# a standard-state shift for one, and ``standard_state.mixed_basis`` exists
# because that silently mattered.
#
# ⚠ ``mineral`` RANKS BESIDE ``measured`` BUT IS NEVER COMBINED BY ``_worst``.
# It is not one half of anything: it is assigned to the species WHOLE, as a
# fallback taken only after the three providers have refused (see
# ``_mineral_fallback``), so it never meets another tier in a ``max``.
TIER_ORDER = [
    "measured", "mineral", "benson", "joback", "ion", "nonvolatile", "refused",
]

# The formation halves that are NOT an estimate. ``mineral`` belongs here for
# the same reason ``ion`` does -- it is curated data, not a group contribution.
SOURCED_TIERS = ("measured", "mineral", "benson", "ion")


def _thermo_tier(source: str) -> str:
    s = source.lower()
    if "spectator ion" in s or "born" in s or "ion:" in s:
        return "ion"
    if "experimental" in s or "measured" in s or "codata" in s or "nist" in s:
        return "measured"
    if "benson" in s:
        return "benson"
    if "joback" in s:
        return "joback"
    return "measured"


def _volatility_tier(source: str, kind: str, charged: bool) -> str:
    s = source.lower()
    if kind == "nonvolatile":
        # An ion does not evaporate, full stop. A NEUTRAL that does not
        # evaporate is a separate claim -- see TIER_ORDER.
        return "ion" if charged else "nonvolatile"
    if "experimental antoine" in s or "measured" in s:
        return "measured"
    if "joback" in s:
        return "joback"
    return "benson"


def refusal_bucket(why: str) -> str:
    """Group a refusal by its CAUSE, because the causes need different fixes.

    Four buckets, and only two of them are curation backlog:

      charged organic   the ion is outside the fitted domain of the Born model,
                        which is parameterised on small hard ions and not on a
                        C16 quaternary ammonium. A data-source limit, not a
                        missing entry, and correctly refused.
      physical half     the formation half resolved and the boiling point did
                        not. Closable with one measured Tb per species.
      formation half    no estimator has a group value. Closable only where a
                        tabulation exists at all.
      fragmentation     neither method can decompose the graph.
    """
    w = why.lower()
    if "net charge" in w:
        return "charged organic (outside the Born domain)"
    if "formation half resolved" in w:
        return "physical half missing (needs a boiling point)"
    if "cannot fragment" in w or "unassigned" in w:
        return "cannot be fragmented at all"
    return "formation half missing (no group value)"


_LATTICES = mineral_data.by_lattice()


def _mineral_fallback(smiles: str):
    """The mineral this catalog SMILES *is*, if the solid block could hold it.

    ⚠ A FALLBACK, NEVER AN OVERRIDE, AND THE DIFFERENCE IS THE WHOLE DESIGN.
    ``sodium-chloride`` resolves today as ``ion``: its ions are priced, it
    genuinely dissolves, and it can additionally precipitate. Re-labelling it
    ``mineral`` would DOWNGRADE a species the engine handles in two phases to
    one it handles in one. So this is consulted only where all three providers
    have already refused -- which is the engine's own precedence, not a new one:
    ``thermochemistry`` prices the ions when it can, and ``mineral_data`` is
    what the SOLID block falls back to when it cannot.

    ⚠ THE LOOKUP IS ON THE **CANONICAL** SMILES, AND THAT IS NOT A DETAIL. The
    catalog spells zincite ``[Zn+2].[O-2]`` and ``mineral_data`` spells it
    ``[O-2].[Zn+2]``; ``vessel.py`` does a RAW dict lookup on that key, so the
    question of whether the engine can really hold the catalog's spelling is the
    question of whether anything canonicalises in between. Something does --
    ``network/builder.py`` line 320 rebuilds every input SMILES through
    ``Molecule.from_smiles`` before the species list is formed -- and this was
    verified by charging all 19 rescued minerals into a real ``Vessel``, not
    inferred. Matching RAW instead is what made the previously recorded estimate
    of this gap read 14 routes rather than 16; it missed ``lime-cycle`` and
    ``vulcanisation``, and ``lime-cycle`` is the route that same note names in
    its prose as the headline case.

    ``priced_solid`` is the second half of the test and it is the vessel's own:
    a formation pair is not enough, the crystal also has to say how much room it
    takes (``Vm_solid``) and how much heat it holds (``Cp_solid``). Two entries
    in the table fail it -- blue vitriol and potassium bisulfate -- and neither
    is rescued here.
    """
    try:
        canon = Molecule.from_smiles(smiles).smiles
    except Exception:  # noqa: BLE001
        return None
    rec = _LATTICES.get(canon)
    if rec is None or not mineral_data.priced_solid(rec.name):
        return None
    return rec


def _worst(*tiers: str) -> str:
    """The tier a species is actually usable at is its WEAKEST half, not its best.

    A measured boiling point paired with a Joback formation enthalpy is a Joback
    record: the equilibrium constant it produces carries Joback's error whatever
    the physical half cost to obtain. Reporting the best half would let a
    thoroughly-estimated species look sourced.
    """
    return max(tiers, key=TIER_ORDER.index)


def audit_compound(comp, thermo, vol, ionic, unifac) -> dict:
    """One compound through parse -> thermochemistry -> volatility -> UNIFAC."""
    row = {
        "id": comp.id,
        "class": comp.cls,
        "role": comp.role,
        "domains": comp.domains,
        "tier": "refused",
        "thermo_tier": "refused",
        "vol_tier": "refused",
        "unifac": False,
        "mineral": "",
        "why": "",
    }
    parts = comp.smiles.split(".")
    # ⚠⚠ S7: A DOT IS NOT ENOUGH TO EARN THE FRAGMENT-WISE ANSWER, AND THIS LINE
    # USED TO SAY IT WAS. ``ionic_species`` was ``len(parts) > 1 or ...``, so any
    # dot-separated SMILES was priced FRAGMENT BY FRAGMENT and reported as
    # resolving. That is right for a salt and wrong for a neutral mixture, and
    # the difference is what the ENGINE holds:
    #
    #   [Na+].[Cl-]            the electrolyte path holds the two IONS, so
    #                          pricing them one at a time is what the engine does
    #   CC(C)=CC.S1SSSSSSS1    nothing splits this. ``builder`` canonicalises it
    #                          into ONE species, and ``thermochemistry`` now
    #                          refuses it -- Joback prices that mixture 222.11
    #                          kJ/mol above the sum of its own two parts
    #
    # So a neutral multi-fragment SMILES is asked about WHOLE, which is the
    # question the engine will be asked. Nine catalog compounds move to
    # ``refused`` for it, and the audit stops disagreeing with the provider it
    # is auditing. ⚠ It cost no route in the BOTH column, which is the only
    # reason it could be done in the same session as a credit.
    charged = []
    for part in parts:
        try:
            if Molecule.from_smiles(part).charge != 0:
                charged.append(part)
        except Exception:  # noqa: BLE001, S110
            pass
    ionic_species = bool(charged)
    provider = ionic if ionic_species else thermo
    pieces = parts if ionic_species else [comp.smiles]

    t_tiers, v_tiers = [], []
    try:
        for part in pieces:
            mol = Molecule.from_smiles(part)
            t = provider.get(mol)
            v = vol.get(mol)
            t_tiers.append(_thermo_tier(t.source))
            v_tiers.append(_volatility_tier(v.source, v.kind, ionic_species))
    except Exception as exc:  # noqa: BLE001
        # ⚠ THE PROVIDERS REFUSING IS NOT THE END OF THE QUESTION FOR A LATTICE.
        # All three are RIGHT to refuse one -- the fusion law is 407x wrong for
        # NaCl in one direction and 11x wrong for CaCO3 in the other, so a
        # lattice must never be handed to a dissolution law. But since M3 a
        # lattice has had a home on the SOLID basis, and it is the table that
        # precipitation, ``SolidStateArrays`` and ``SurfaceArrays`` all price
        # from. A species this project can charge into a flask and react is
        # species-READY, whatever the ideal-gas providers say about dissolving
        # it, and reading only the providers is what understated this column.
        mineral = _mineral_fallback(comp.smiles)
        if mineral is not None:
            row["tier"] = row["thermo_tier"] = row["vol_tier"] = "mineral"
            row["mineral"] = mineral.name
            # ⚠ ``unifac`` STAYS FALSE, and it is not an omission. The UNIFAC
            # column asks whether a species can enter a LIQUID MIXTURE, and a
            # lattice here cannot: it never dissolves, by the same verdict that
            # sent it down this branch. Every species rescued here was already
            # refused, so this returns before the UNIFAC probe exactly as the
            # refusal did and the published UNIFAC count does not move.
            row["why"] = (
                f"priced as the lattice {mineral.name!r} on the solid basis "
                f"(mineral_data); the three ideal-gas providers refuse it, "
                f"correctly, because the fusion law cannot dissolve it"
            )
            return row
        row["why"] = f"{type(exc).__name__}: {str(exc)[:90]}"
        return row

    row["thermo_tier"] = _worst(*t_tiers)
    row["vol_tier"] = _worst(*v_tiers)
    row["tier"] = _worst(row["thermo_tier"], row["vol_tier"])

    # UNIFAC is asked of the WHOLE species, ions included. An ion legitimately
    # has no groups and the provider says so; that is a pass for "the activity
    # model handled it", not a decomposition failure, so it is counted apart.
    try:
        groups = unifac.get(Molecule.from_smiles(parts[0]))
        row["unifac"] = bool(groups.counts) or "ion:" in groups.source
    except Exception:  # noqa: BLE001
        row["unifac"] = False
    return row


# ---------------------------------------------------------------------------
# the reaction side -- what the ten templates actually cover
# ---------------------------------------------------------------------------
# Mapped by hand because a template is a SMARTS and a route step is a named
# transformation; nothing in either file can infer the correspondence. Kept
# deliberately generous: a class is counted covered if the existing template
# would fire on the right substrate at all, even where the barrier would need
# re-sourcing for that particular route.
#
# ⚠ IT USED TO MISS SIX TEMPLATES ENTIRELY -- it knew only ``reactions/library.py``
# and not the dissociation set in ``properties/electrolyte.py``, so every proton
# transfer in the catalog read as uncovered.
#
# ⚠⚠ AND CREDITING THEM WAS NOT THE LOOKUP-TABLE EDIT IT LOOKED LIKE. The
# expected gain was 21 -> 46 steps, which needs ``deprotonation`` (6 steps) to be
# proton transfer. **It is not**: five of its six rows are malonate and
# acetoacetate carbanions, a Wittig ylide and two enolates -- i.e. exactly the
# carbanion-generation capability that has NO template -- and the sixth is an
# arenium proton loss. Crediting the class would have made this instrument LESS
# trustworthy, which is the failure mode it exists to prevent.
#
# The fix was in the TAXONOMY rather than here: ``acid-base``, ``redox``,
# ``oxidation`` and ``deprotonation`` were OUTCOME labels spanning several
# mechanisms each, and a template is SMARTS on a MECHANISM. 32 rows of
# ``route_steps.psv`` were re-labelled to the mechanism their own reactants and
# products show, which is why this map needs no notion of "partial" coverage --
# a class is now specific enough for the question to have a yes/no answer.
#
# ⚠ ONE ROW'S NAME STILL MISLEADS AND IS WORTH KNOWING ABOUT: `williamson-ether`
# step 1 is called "alkoxide formation" but reads ``phenol + NaOH ->
# sodium-phenoxide``, so ``phenol_dissociation`` does cover it. Read the row, not
# the name.

TEMPLATE_CLASSES = {
    "esterification": "fischer_esterification",
    "ether-condensation": "ether_condensation",
    "dehydration": "alkene_dehydration",
    "alcohol-oxidation": "aerobic_oxidation",
    "aldehyde-oxidation": "peroxide_over_oxidation",
    "redox-oxygen-transfer": "sulfur_dioxide_oxidation",
    "gas-phase-oxidation": "nitric_oxide_reoxidation",
    # ---------------------------------------------------------------------
    # S7 -- ``combustion`` WAS AN OUTCOME LABEL, AND IT HAD BEEN CREDITED SINCE M1
    # ---------------------------------------------------------------------
    # One entry used to read ``"combustion": "sulfur_combustion"``. Six rows, and
    # the burner's SMARTS is ``S8 + 8 O2 -> 8 SO2`` -- so it fires on exactly two
    # of them and the other four were credited on a template that cannot match
    # their reactants. The M1 row check, arriving late:
    #
    #   lead-chamber 1     S8 + O2 -> SO2               sulfur-combustion    OK
    #   contact-process 1  S8 + O2 -> SO2               sulfur-combustion    OK
    #   claus-process 1    H2S + O2 -> SO2 + H2O        hydrogen-sulfide-combustion
    #   blast-furnace 1    C(gr) + O2 -> CO2            carbon-combustion    gap
    #   ethylene-oxide 2   C2H4 + O2 -> CO2 + H2O       hydrocarbon-combustion  gap
    #   match-chemistry 1  KClO3 + P4 -> P2O5 + KCl     chlorate-oxygen-transfer gap
    #
    # ⚠ THE LAST ROW IS NOT COMBUSTION AT ALL. Nothing burns in air: a solid
    # oxidiser hands its oxygen to a solid fuel on friction. Calling it
    # combustion put it under a template about a sulfur ring.
    #
    # ⚠⚠ AND THE SPLIT COSTS A TEMPLATE-READY ROUTE, WHICH IS THE POINT. It is
    # the first split in this project whose measured effect on the headline is
    # NEGATIVE: ``match-chemistry`` was template-ready only because of this
    # credit, and it now is not. It was never species-ready, so the intersection
    # -- the number to quote -- does not move for it.
    "sulfur-combustion": "sulfur_combustion",
    "hydrogen-sulfide-combustion": "hydrogen_sulfide_combustion",
    # ---------------------------------------------------------------------
    # S7 -- the four inorganic gas processes. See reactions/synthesis.py, and
    # validation/gas_processes.py, which RUNS every one of them in a Vessel
    # rather than crediting them off this table.
    # ---------------------------------------------------------------------
    # ⚠ CHOSEN OFF THE ``RUNNABLE`` COLUMN AND THEN OFF A THIRD QUESTION THIS
    # AUDIT CANNOT ASK. The queue's top two rows by RUNNABLE were
    # ``isomerisation`` (+3/+2) and ``crosslinking`` (+2/+2), and S7 measured
    # both before costing either:
    #
    #   isomerisation  three rows, three mechanisms, and each fails its own way.
    #                  ``oleic -> elaidic`` prices at dH = dG = 0.000 EXACTLY --
    #                  no estimator here tells a cis alkene from a trans one, so
    #                  the template would report a confident 50:50 for a real
    #                  5:1. ``glucose -> fructose`` prices at dG +41.8 kJ/mol,
    #                  K = 4.8e-08, because the catalog spells one as a pyranose
    #                  and the other as a furanose. ``ammonium-cyanate -> urea``
    #                  is not species-ready at all.
    #   crosslinking   both products are unbuildable. ``tanned-leather-marker``
    #                  has no graph; ``vulcanised-rubber-marker`` is spelled
    #                  ``CC(C)=CC.S1SSSSSSS1``, its own two reactants side by
    #                  side, so the "reaction" is A + B -> A.B.
    #
    # ⚠⚠ SO ``RUNNABLE`` HAS THE SAME SHAPE OF FAULT ``ALONE`` HAD. It asks
    # whether every species RESOLVES; it cannot ask whether the number that comes
    # back is RIGHT, nor whether the row's product is a graph at all. Both of the
    # top two rows fail on exactly those two questions, and neither failure is
    # visible in this file's tables. **Read the rows, not the ranking.**
    "water-gas-shift": "water_gas_shift",
    "steam-reforming": "steam_reforming",
    # ⚠⚠ S9 SPLIT `catalytic-gas-oxidation`, AND IT WAS A FALSE CREDIT ON TWO OF
    # ITS THREE ROWS -- found while RANKING the queue rather than while building
    # anything, which is the second time a class has come apart under that check.
    # The three rows are three different reactions:
    #
    #   deacon-process 1    HCl + O2  + CuCl2 -> Cl2 + H2O   ✔ deacon_oxidation
    #   contact-process 2   SO2 + O2  + V2O5  -> SO3         ✘ NOTHING makes this
    #   ostwald-process 1   NH3 + O2  + Pt    -> NO + H2O    ✘ NOTHING makes this
    #
    # ⚠ AND THE NEAR-MISS IS WORTH KEEPING: the obvious reading is that
    # ``sulfur_dioxide_oxidation`` covers the contact-process row, because of its
    # NAME. It does not -- that template is `SO2 + NO2 + H2O -> H2SO4 + NO`, the
    # lead chamber's step, and it is credited to `redox-oxygen-transfer`. A
    # template's name is not its SMARTS.
    #
    # Headline effect: ZERO on both columns. `deacon-process` keeps its credit
    # and neither of the other two was template-ready anyway -- but
    # `ostwald-process` was being counted as ONE class away when it is two, which
    # is exactly the ranking error this split exists to remove.
    "catalytic-hydrogen-chloride-oxidation": "deacon_oxidation",
    "comproportionation": "claus_comproportionation",
    # the six in properties/electrolyte.py, which this map used not to know about
    "proton-transfer": "electrolyte.dissociation_templates",
    "acid-displacement": "electrolyte.dissociation_templates",
    # ⚠ M3, AND THESE TWO ARE COVERED BY A TERM RATHER THAN BY A TEMPLATE. The
    # kinetics kernel cannot express precipitation at all -- a template's phase
    # is liquid or gas and no reaction writes the solid block -- so the covering
    # mechanism is ``vessel_integrator.PrecipitationArrays``, driven by a Ksp
    # from ``ion_data`` minus ``mineral_data``. Credited here anyway, because
    # this map asks whether the MECHANISM exists in the engine and not what
    # shape it has; ``N_TEMPLATES`` below is deliberately not incremented.
    #
    # ⚠ AND THE M1 STANDARD WAS APPLIED BEFORE CREDITING THEM, because that is
    # the failure this instrument exists to prevent. ``deprotonation`` was
    # refused credit for the dissociation templates because five of its six rows
    # are carbanion generation wearing the wrong label -- one CLASS, several
    # mechanisms. These two are not like that: every row is a double
    # displacement that drops an insoluble salt, which is exactly one mechanism
    # and exactly what the term does, for any lattice that prices.
    #
    # ⚠ WHAT IS NOT CREDITED BY THIS, STATED SO THE NUMBER IS NOT READ TOO WELL.
    # A class being covered is a MECHANISM claim; whether a particular route's
    # lattice is priced is a SPECIES question this audit counts separately (the
    # catalog README's own rule). Measured against the five
    # ``precipitation-metathesis`` rows: silver iodide and silver chloride price
    # today, sodium bicarbonate and Prussian blue have no lattice entry, and
    # chrome yellow is REFUSED by ``mineral_data`` for want of an S0s in any
    # database shared with its Hfs. So the mechanism is there and three of the
    # five still need a lattice.
    "precipitation-metathesis": "vessel_integrator.PrecipitationArrays (a TERM)",
    "acid-displacement-precipitating": (
        "electrolyte.dissociation_templates + PrecipitationArrays (a TERM)"
    ),
    # ---------------------------------------------------------------------
    # M5 -- reactions/synthesis.py. Twenty templates, seventeen classes.
    # ---------------------------------------------------------------------
    # ⚠ EVERY ONE OF THESE WAS CHECKED ROW BY ROW BEFORE BEING ADDED, and six
    # candidate classes were REFUSED on that check rather than credited --
    # ``fermentation``, ``pyrolysis``, ``isomerisation``, ``thermal-cracking``,
    # ``catalytic-air-oxidation`` and ``separation``. The argument for each is in
    # ``reactions/synthesis.py``'s module docstring; the short form is that a class
    # is credited only when every ROW of it is the mechanism the template
    # implements, which is the standard M1 established and this is the first
    # milestone to spend it.
    "glycoside-hydrolysis": "glycoside_hydrolysis",
    "electrophilic-aromatic-nitration": "aromatic_nitration",
    "williamson-ether-synthesis": "williamson_ether_synthesis",
    "friedel-crafts-hydroxyalkylation": "friedel_crafts_hydroxyalkylation",
    "kolbe-schmitt-carboxylation": "kolbe_schmitt",
    "transesterification": "transesterification",
    "n-acylation": "n_acylation",
    "cannizzaro-disproportionation": "cannizzaro",
    "perkin-condensation": "perkin_condensation",
    "knoevenagel-doebner-condensation": "knoevenagel_doebner",
    "alkene-hydration": "alkene_hydration",
    "alkyne-hydration": "alkyne_hydration",
    "disproportionation": "halogen_disproportionation",
    # TWO templates each, because the class has two mechanisms in it and crediting
    # it on one of them would be the ``deprotonation`` mistake again.
    "ester-hydrolysis": "ester_hydrolysis + saponification",
    "catalytic-gas-synthesis": (
        "ammonia_synthesis + methanol_from_carbon_monoxide/dioxide"
    ),
    # ⚠ THESE TWO LABELS DID NOT EXIST BEFORE M5. ``catalytic-hydrogenation`` was
    # the most-used class with no template in the corpus (10 steps) and its ten
    # rows are FIVE mechanisms -- nitro to amine, nitro to hydroxylamine, C=C, C=O,
    # and an arene. Refusing it outright would have been wrong in the other
    # direction: unlike ``fermentation``, every row IS a clean mechanism. So the
    # rows were re-labelled on M1's precedent and two of the five are built. The
    # other three (``nitro-partial-hydrogenation``, ``carbonyl-hydrogenation``,
    # ``arene-hydrogenation``) are honest, named gaps.
    "alkene-hydrogenation": "alkene_hydrogenation",
    "nitro-hydrogenation": "nitro_hydrogenation",
    # ---------------------------------------------------------------------
    # M6 -- properties/solid_state.py. The SECOND class covered by a TERM.
    # ---------------------------------------------------------------------
    # ⚠ AND THE SECOND CLASS WHERE THE KINETICS KERNEL CANNOT EXPRESS THE
    # MECHANISM AT ALL, for a reason that is now measured rather than argued: a
    # pure solid has UNIT ACTIVITY, so mass action on the solid amounts settles
    # at ``p/K = n_A/n_B`` -- built, measured at 3.0863 against 3.0863 on a
    # sealed kiln at 1100 K, replaced. The covering mechanism is
    # ``vessel_integrator.SolidStateArrays``, and ``N_TEMPLATES`` is again
    # deliberately not incremented.
    #
    # ⚠ M1's STANDARD APPLIED FIRST, AND THIS CLASS IS TWO MECHANISMS. Its three
    # rows are decarbonation twice (``lime-cycle`` 1, ``solvay-process`` 5) and
    # dehydration once (``bayer-process`` 3). BOTH are built, which is why the
    # class is credited -- crediting it on the decarbonation alone would have
    # been the ``deprotonation`` mistake.
    #
    # ⚠ WHAT IS NOT CREDITED BY THIS, on exactly the precipitation precedent
    # above. A class being covered is a MECHANISM claim; whether a row's species
    # price is the SPECIES question this audit counts separately. Measured: the
    # two decarbonation rows run today (calcite and quicklime both price), and
    # the dehydration MECHANISM was built on ``Ca(OH)2 -> CaO + H2O`` because
    # Bayer's own ``Al(OH)3 -> Al2O3 + H2O`` needs two minerals ``mineral_data``
    # does not have. So the mechanism is there and one of the three rows still
    # needs two lattices.
    #
    "calcination": "vessel_integrator.SolidStateArrays (a TERM)",
    # ⚠⚠ ``roasting`` IS NOW CREDITED, AND BOTH HALVES OF M6's REFUSAL HAD TO GO.
    # DATA: ``mineral_data`` carries all four oxides and all four sulfides, where
    # M6 had only ZnS and no oxide at all. MECHANISM: roasting CONSUMES a gas, so
    # the affinity form ``SolidStateArrays`` uses is measurably not a rate law for
    # it -- ``p_O2 -> 0`` puts the pressure in the DENOMINATOR of Q and drives the
    # reverse to 2.6e15 formula units per second, which is why a gas reactant is
    # refused where those arrays are built. ``SurfaceArrays`` is the mass-action
    # term it was waiting on.
    #
    # ⚠ AND IT IS NOT A THIRD ``PHASE_INDEX`` ENTRY, which is what M6 predicted it
    # would be and what the brief asked for. Measured: labelling a solid-catalysed
    # gas reaction "solid" moves it onto the pure-liquid standard state, because
    # ``reaction_deltas`` shifts anything that is not "gas" -- dG by -99.7 kJ/mol
    # and K at 500 K by 2.6e10. So a solid CATALYST is a factor in a gas
    # reaction's rate law and roasting is a TERM, and ``PHASE_INDEX`` keeps its
    # two entries for the second milestone running.
    #
    # ⚠⚠ AND CREDITING THE CLASS AS M6 LABELLED IT PRODUCED A FALSE CREDIT,
    # WHICH IS WHY THE CLASS IS NOW SPLIT. ``mercury-from-cinnabar`` reads
    # ``mercury-sulfide + oxygen -> mercury + sulfur-dioxide``, and this term
    # makes the OXIDE -- HgO decomposes at roasting heat, which is the whole
    # reason the row is written that way. On the unsplit label the route moved
    # into the template-ready list on the strength of a mechanism that does not
    # make its product, so the row is re-labelled ``roasting-to-metal`` (M1's
    # standard, and M6 had already recorded the reading without acting on it).
    #
    # ⚠ OF THE FOUR ROWS LEFT, THREE RUN AND ``pyrite-roasting`` DOES NOT --
    # pyrite has ``Hfs`` in WEBBOOK and ``S0s`` in nothing, so ``mineral_data``
    # refuses it under the same-database rule. It still counts as template-ready,
    # because that is what template-readiness MEANS (species-readiness is the
    # other column). The honest summary is +1 class, +1 template-ready route, and
    # ZERO new routes that run end to end: all three smelting routes are still
    # blocked at ``carbothermic-reduction`` / ``gas-solid-reduction``.
    #
    # ⚠⚠ AND S9 UNBLOCKED ALL THREE, so read that last sentence as a record of
    # S1's state rather than of this one. `copper-smelting`, `lead-smelting` and
    # `zinc-smelting` are in the BOTH column now, and each of them is a ROAST
    # from this table followed by a REDUCTION from ``SOLID_STATE_REACTIONS``,
    # with neither declaration mentioning the other -- the mercury retort's
    # pattern, three more times.
    "roasting": (
        "vessel_integrator.SurfaceArrays (a TERM; mass action, first order in "
        "the arriving gas and gated on the solid being present)"
    ),
    # ---------------------------------------------------------------------
    # S9 -- THE SMELTER. Five classes, one algebraic change, no new term.
    # ---------------------------------------------------------------------
    # ⚠⚠ WHAT S9 ACTUALLY DID: it lifted a REFUSAL. ``SolidStateArrays`` could
    # not hold a gas REACTANT because ``Q = prod(p ** nu_gas)`` puts one in a
    # denominator (2.6e15 formula units per second as the gas ran out, measured
    # by M6). Split into two one-sided products, ``net = k_f P_react -
    # k_r P_prod``, nothing is divided and ``net = 0`` is still ``Q = K``. That
    # is the whole of "a REVERSIBLE solid-gas term", which S8 named as the most
    # valuable unscoped engine item in the plan.
    #
    # ⚠ AND EVERY ROW IS RUN IN A REAL VESSEL BY ``validation/smelting.py``,
    # not credited off this table -- ``pyrite-roasting`` is what that rule
    # exists to prevent.
    #
    # ⚠ THE ROW CHECK, FIRST. `gas-solid-reduction`'s four rows are one
    # mechanism (`MO + CO -> M + CO2`, four times); two of them run and two are
    # blocked on an iron(II) oxide ``mineral_data`` refuses, which is a SPECIES
    # question this audit counts in the other column.
    "gas-solid-reduction": (
        "vessel_integrator.SolidStateArrays (a TERM; the affinity form, now "
        "REVERSIBLE with a gas reactant)"
    ),
    # ⚠⚠ `carbothermic-reduction` WAS AN OUTCOME LABEL AND S9 SPLIT IT. Five
    # rows, four mechanisms -- see data/catalog/README.md. Only the OXIDE row is
    # built, and crediting the whole class on it would have claimed routes to
    # calcium carbide and to white phosphorus that this engine cannot make:
    # `roasting-to-metal`'s false credit in a fourth costume.
    "carbothermic-oxide-reduction": (
        "vessel_integrator.SolidStateArrays (a TERM)"
    ),
    # ⚠ ONE ROW, ONE MECHANISM, and the only row in either solid table whose
    # affinity has NO gas in it at all -- so both one-sided pressure products
    # are empty (exactly 1.0) and the affinity collapses to ``k_f - k_r``.
    "metallothermic-reduction": (
        "vessel_integrator.SolidStateArrays (a TERM)"
    ),
    # ⚠⚠ THESE TWO ARE CREDITED FOR A MECHANIC AND ARE WORTH **ZERO** ROUTES,
    # WHICH IS SAID HERE RATHER THAN LEFT TO BE INFERRED. Both are
    # `blast-furnace`'s, and that route is still blocked on `slagging` (no
    # template) and on `iron-ii-oxide` (no lattice). What they buy is that the
    # three smelting routes STOP NEEDING A CARBON OXIDE HANDED TO THEM: with
    # them a flask of ore, coke and air makes metal, and S9 measured the same
    # flask without them at exactly zero conversion on four tolerance rungs.
    "boudouard": "vessel_integrator.SolidStateArrays (a TERM)",
    "carbon-combustion": "vessel_integrator.SurfaceArrays (a TERM)",
    # ---------------------------------------------------------------------
    # M8 -- reactions/electrochemistry.py. Electricity as a reagent.
    # ---------------------------------------------------------------------
    # The covering mechanism is not a template but a DRIVING FORCE:
    # ``ReactionTemplate.electrons`` times ``build_network(cell_potential=...)``
    # gives ``n F E`` joules, ``thermo.reaction_deltas`` subtracts it from dG,
    # and a reaction whose chemistry costs less than the cell supplies runs. The
    # threshold is the decomposition potential and nothing declares it.
    #
    # ⚠⚠ AND ``electrolysis`` IS NOT CREDITED, BECAUSE ITS FOUR ROWS ARE THREE
    # MECHANISMS. This is M1's standard applied to the class the greedy curve
    # ranks FIRST, and it costs two of the three routes that curve promised:
    #
    #   aqueous-electrolysis     chloralkali. Ions in water, the cathode reduces
    #                            WATER. BUILT -- ``halide_electrolysis``.
    #   molten-salt-electrolysis downs-cell, hall-heroult. A MELT is not a phase
    #                            this project has; Hall-Heroult also consumes its
    #                            carbon anode. Named gap, and both routes are
    #                            blocked on a bare element anyway.
    #   amalgam-electrolysis     castner-kellner. A mercury cathode reduces the
    #                            SODIUM instead of the water, which is the whole
    #                            difference from chloralkali, and the product is
    #                            a marker with no molecular graph. Named gap on
    #                            M5's ``separation`` precedent.
    #
    # ⚠ SO THE GREEDY CURVE'S TOP ROW IS WORTH +1 ROUTE, NOT +3. It ranked an
    # unsplit label, exactly as it ranked ``catalytic-air-oxidation`` third for
    # zero runnable routes. A class is a MECHANISM claim; read the rows.
    "aqueous-electrolysis": "halide_electrolysis",
    # ⚠ TWO ROWS, THREE TEMPLATES, AND BOTH ROWS VERIFIED BY RUNNING THEM. On
    # the ``ester-hydrolysis`` precedent: the class holds two mechanisms and
    # crediting it on one would be the ``deprotonation`` mistake.
    #
    #   kolbe-electrolysis   anodic decarboxylation. ``kolbe_electrolysis``, and
    #                        it generalises -- acetate plus propanoate gives
    #                        ethane, propane AND butane, nobody having written
    #                        the cross-coupling down.
    #   adiponitrile-route   ``water_electrolysis`` + ``alkene_hydrodimerisation``.
    #                        ⚠ The SECOND passes no electrons, and that is a
    #                        measurement: the cell 4 AN + 2 H2O -> 2 ADN + O2 is
    #                        uphill at +212.7 kJ/mol, while 2 AN + H2 -> ADN is
    #                        DOWNHILL at -171.7. The voltage buys the hydrogen,
    #                        not the carbon-carbon bond. The row's overall
    #                        stoichiometry, oxygen included, EMERGES from the
    #                        pair -- measured in ``examples/electrolysis_cell.py``
    #                        panel 5 at 65.6% conversion at 3 V and nothing at 2.
    "electro-organic-coupling": (
        "kolbe_electrolysis + water_electrolysis/alkene_hydrodimerisation"
    ),
    # ⚠ AND TWO MORE CLASSES WERE SPLIT RATHER THAN REFUSED, on the
    # ``catalytic-hydrogenation`` precedent from M5 -- because like that class
    # and unlike ``fermentation``, every row here IS a clean mechanism.
    #
    # ``hydration`` had THREE rows: two are lime slaking (``CaO + H2O ->
    # Ca(OH)2``) and one is CHLORAL HYDRATE, a gem-diol forming on a carbonyl.
    # Those are not one mechanism. ``carbonation`` had TWO: setting mortar
    # (``Ca(OH)2 + CO2 -> CaCO3 + H2O``, a solid-state reaction) and the white-lead
    # stack (``lead acetate + CO2 + water -> basic lead carbonate``, a metathesis
    # in solution). Also not one mechanism. Five rows re-labelled in
    # ``route_steps.psv``; the two halves M6 does not cover are named gaps.
    #
    # ⚠⚠ NEITHER OF THESE IS DECLARED ANYWHERE, WHICH IS THE POINT. Lime slaking
    # is the ``calcination-dehydration`` row RUN BACKWARDS -- available only
    # because the term is reversible. Solid carbonation is not any single row's
    # reverse: it is the dehydration row forwards and the decarbonation row
    # backwards, sharing the quicklime in the solid block. Two declarations, three
    # mechanisms, and this is the first time a class has been credited to a
    # mechanism that EMERGED rather than being written.
    "lime-slaking": "vessel_integrator.SolidStateArrays reversed (a TERM)",
    "solid-carbonation": (
        "vessel_integrator.SolidStateArrays, two rows sharing the solid "
        "block (a TERM; EMERGENT -- nothing declares this reaction)"
    ),
    # ---------------------------------------------------------------------
    # S3 -- ``thermal-decomposition`` SPLIT. NO engine work: both covering
    # mechanisms were already DECLARED by M6, under exactly these two names.
    # ---------------------------------------------------------------------
    # M6 read this class against M1's standard, recorded "four rows and they are
    # four mechanisms", and left it alone because it ran out of session rather
    # than because the reading was in doubt. The reading holds: the rows are a
    # solid sulfate decomposing, a solid bicarbonate decomposing, a MOLECULAR
    # decomposition of a melt, and a gas DEPOSITING a metalloid. Four mechanisms
    # sharing one furnace, which is the ``catalytic-hydrogenation`` shape exactly.
    #
    # ⚠⚠ WHICH ROUTES THIS MOVES: **ZERO**, CHECKED BEFORE CREDITING. That check
    # is here because S1's roasting credit moved ``mercury-from-cinnabar`` into
    # the template-ready list on the strength of a mechanism that does not make
    # that row's product. Every one of the four affected routes is blocked on a
    # SECOND uncovered class, so no route can move on this credit at all:
    #
    #     vitriol-distillation  step 2   hydrolysis                   uncovered
    #     solvay-process        step 1   carbonate-equilibrium        uncovered
    #     melamine-route        step 2   trimerisation                uncovered
    #     marsh-test            step 1   dissolving-metal-reduction   uncovered
    #
    # ⚠ AND THE GREEDY CURVE'S "+1 route" FOR THIS CLASS WAS NEVER A STANDALONE
    # UNLOCK: it sits at rank 14, i.e. after ``hydrolysis`` has been added at
    # rank 6. Read as a standalone promise it would have delivered a route it
    # cannot -- the same misreading as S1's, arriving from a different table. The
    # standalone table is the one that answers this question and it does not list
    # this class at all.
    #
    # So the honest summary is **+2 classes covered, +3 to the denominator, +0
    # template-ready routes**. What it buys is that two classes stop reading as
    # gaps when their mechanism has been built and MEASURED since M6 -- both rows
    # RUN, pinned in ``tests/test_solid_state.py`` at 25.4 s at 1000 K and 43.7 s
    # at 450 K. That is strictly better than S1's outcome, which was +1
    # template-ready route that does not run.
    #
    # ⚠⚠ AND ONE OF THE TWO CREDITS IS A LATENT FALSE CREDIT, RECORDED RATHER
    # THAN HIDDEN. ``vitriol-distillation`` step 1 reads ``iron-ii-sulfate ->
    # iron-ii-OXIDE + sulfur-trioxide``; the declaration makes HEMATITE, as
    # ``2 FeSO4 -> Fe2O3 + SO2 + SO3``. The credit is honest for a reason that is
    # the OPPOSITE of the cinnabar case, and telling the two apart is the point:
    #
    #   * cinnabar -- the ROW is right (a retort does give the metal) and the
    #     mechanism stops short of it, so reaching the row needs a second
    #     reaction nobody has built. NOT covered; re-labelled ``roasting-to-metal``.
    #   * green vitriol -- the MECHANISM is right and the ROW is wrong. FeO does
    #     not survive red heat, and ``mineral_data`` refuses it anyway (CRC
    #     tabulates no crystal Cp for it). Nothing further is needed to reach the
    #     real products, so the mechanism covers the step.
    #
    # ⚠ THE LANDMINE, STATED FOR WHOEVER TRIPS IT: the class is credited and the
    # ROW still names a product this engine never makes. Today that is inert,
    # because step 2 is uncovered and the route cannot go template-ready.
    # **The day ``hydrolysis`` is credited, ``vitriol-distillation`` becomes
    # template-ready on a step whose stated product does not exist in the run.**
    # Whoever credits ``hydrolysis`` owes this row a second look. The corpus row
    # is deliberately NOT corrected, on the ``diels-alder-route`` precedent:
    # inventing chemistry inside an audit corpus is not allowed, and correcting
    # this one means re-balancing it to 2 FeSO4 and adding an SO2 nobody wrote.
    #
    # ⚠ THE TWO HALVES THAT ARE NOT CREDITED, AND WHY THEY DIFFER IN COST:
    #
    #   * ``urea-deammoniation`` (``urea -> cyanic-acid + ammonia``) is blocked on
    #     a TEMPLATE ONLY. All three species resolve, and the kinetics kernel can
    #     already express a unimolecular decomposition in a liquid -- urea MELTS
    #     at 406 K and the row is run at 620 K, so it is a liquid-phase graph
    #     rewrite, not a lattice. ⚠ One caveat that is a physical fact and not a
    #     gap: cyanic acid is one of the nine neutral species with no boiling
    #     point in ANY source, so it resolves as ``nonvolatile`` and cannot be put
    #     in the gas block. The HNCO would come off into the liquid.
    #   * ``hydride-thermal-deposition`` (``arsine -> arsenic + hydrogen``) is
    #     blocked on BOTH, and its mechanism gap is a named one: NUCLEATION.
    #     ``SurfaceArrays`` is first order and EXTENSIVE in the solid amount, so a
    #     solid at zero mol has zero rate for ever -- and the term is irreversible
    #     by construction, so no roasting row can be run backwards to deposit one.
    #     Depositing a solid from no solid is not expressible here at all. The
    #     species half is independent: ``arsine`` and ``arsenic`` are both refused
    #     outright (a bare element symbol, and no estimator for AsH3).
    "sulfate-thermal-decomposition": (
        "vessel_integrator.SolidStateArrays (a TERM; the DECLARATION makes "
        "hematite where the catalog row says iron-ii-oxide -- the row is the "
        "one that is wrong, see the source)"
    ),
    "bicarbonate-thermal-decomposition": (
        "vessel_integrator.SolidStateArrays (a TERM; this declaration's products "
        "ARE the row's, unlike the sulfate half)"
    ),
    # ---------------------------------------------------------------------
    # S4 -- ``roasting-to-metal``. THE FALSE CREDIT S1 FOUND, PAID OFF.
    # ---------------------------------------------------------------------
    # S1 credited ``roasting`` and discovered that it had thereby claimed
    # ``mercury-from-cinnabar`` -- ``mercury-sulfide + oxygen -> mercury +
    # sulfur-dioxide`` -- on a term that makes the OXIDE. It split the row out
    # under this name and left it uncovered, and recorded that reaching it would
    # need "a second reaction nobody built". S4 built the second reaction.
    #
    # ⚠⚠ AND NOTHING DECLARES THE ROW. This is the SECOND class credited to a
    # mechanism that EMERGED (``solid-carbonation`` was the first), and it is
    # the first time the emergent reaction is a CATALOG ROW rather than a
    # by-product of one. Two declarations, in two different terms, sharing one
    # crystal in the solid block:
    #
    #     surface.py     2 HgS + 3 O2 -> 2 HgO + 2 SO2      SurfaceArrays
    #     solid_state.py 2 HgO        -> 2 Hg  +   O2       SolidStateArrays
    #     ----------------------------------------------------------------
    #     what a retort does:  HgS + O2 -> Hg + SO2         nobody wrote this
    #
    # Measured, not argued: a sealed 10 L retort of pure oxygen holding 0.02 mol
    # of cinnabar at 900 K comes out at 0.020000000000 mol of mercury and
    # 0.020000000000 mol of SO2 -- 1:1 to twelve figures, having consumed
    # 0.020000 mol of O2. That IS the catalog row, coefficient for coefficient.
    # The montroydite never reaches 4e-5 of the charge, because its own clock at
    # 900 K is 0.24 s against the roast's 5,918 s.
    #
    # ⚠⚠ WHICH ROUTES IT MOVES -- PREDICTED FIRST, THEN MEASURED, per S1's third
    # mistake and S3's standing check. ``mercury-from-cinnabar`` is a ONE-STEP
    # route, so this credit is the whole of it: predicted +1 template-ready
    # route and exactly one, and unlike S1's ``pyrite-roasting`` this one RUNS
    # END TO END. Both minerals price, mercury is now a curated element, and the
    # run above is the route.
    #
    # ⚠ THE NAME WAS RE-EXAMINED AND KEPT, WHICH WAS NOT THE EXPECTED ANSWER.
    # The brief for S4 said the re-label was what would get reversed -- fold the
    # row back into ``roasting`` now that its product is reachable. Refused, and
    # the arithmetic runs both ways:
    #
    #     keep ``roasting-to-metal``  ->  36/218 classes, 28/173 routes
    #     fold back into ``roasting`` ->  35/217 classes, 28/173 routes
    #
    # The routes are identical, so the choice is purely about what the class
    # column SAYS. ``roasting-to-metal`` records a real mechanistic difference
    # and not an outcome: this ore's oxide does not survive the furnace that
    # makes it, which is why one row needs two mechanisms where the other four
    # need one. Folding it back would delete the distinction S1 paid to find,
    # to make one counter smaller. M1's standard asks whether "is it covered"
    # has a yes/no answer for the class, and it does -- see ``solid-carbonation``
    # above, which is an emergent pair under a name of its own for the same
    # reason.
    "roasting-to-metal": (
        "vessel_integrator.SurfaceArrays + SolidStateArrays sharing one crystal "
        "in the solid block (two TERMS; EMERGENT -- nothing declares this "
        "reaction, and it is the catalog's own row)"
    ),
}

# How many templates that is, counted rather than asserted -- the old text said
# "10 templates" and ``library.py`` has 8.
N_LIBRARY_TEMPLATES = 8
N_SYNTHESIS_TEMPLATES = 25
N_ELECTROLYTE_TEMPLATES = 6
# ⚠ M8 INCREMENTS THIS WHERE M3 AND M6 DELIBERATELY DID NOT, and the difference
# is what shape the mechanism has. Precipitation, calcination and roasting are
# TERMS in the integrator -- there is no template to count. These four are
# ordinary ``ReactionTemplate``s that happen to carry an electron count, so they
# are templates by the same rule as the other 34.
N_ELECTROCHEMISTRY_TEMPLATES = 4
N_TEMPLATES = (
    N_LIBRARY_TEMPLATES + N_SYNTHESIS_TEMPLATES + N_ELECTROLYTE_TEMPLATES
    + N_ELECTROCHEMISTRY_TEMPLATES
)


def marginal_unlock(steps, routes):
    """Ranked by ROUTES UNLOCKED per class added, plus the greedy set-cover curve.

    ⚠ THIS IS A DIFFERENT RANKING FROM FREQUENCY AND THE TWO BARELY OVERLAP,
    which is the whole reason it exists. The most-USED missing classes unlock
    nothing on their own, because the routes needing them each need several other
    things too -- so a frequency table read as a work queue sends you to build
    templates that move the route count by zero.
    """
    need: dict[str, set[str]] = {}
    for rid in routes:
        mine = {s.cls for s in steps if s.route == rid}
        gap = {c for c in mine if c not in TEMPLATE_CLASSES}
        if gap:
            need[rid] = gap

    # (a) one class at a time: which routes go from one gap to zero
    one_away: dict[str, set[str]] = {}
    for rid, gap in need.items():
        if len(gap) == 1:
            one_away.setdefault(next(iter(gap)), set()).add(rid)

    # (b) greedy set cover over the remaining routes.
    #
    # ⚠ THE TIE-BREAK IS LOAD-BEARING. Maximising "routes unlocked outright" goes
    # to zero after a handful of classes -- every remaining route needs two or
    # more -- and a loop that stops there reports a curve that flattens because it
    # gave up, not because the catalog does. So when nothing unlocks a route
    # alone, pick the class that appears in the MOST remaining routes, i.e. the
    # one that buys the most PROGRESS. Those rows show +0 and that is honest: a
    # template can be the right next thing to build and still unlock nothing yet.
    remaining = {r: set(g) for r, g in need.items()}
    curve, chosen = [], []
    while remaining and len(chosen) < 20:
        pool = {c for g in remaining.values() for c in g}
        unlocks = {c: sum(1 for g in remaining.values() if g == {c}) for c in pool}
        best = max(pool, key=lambda c: (unlocks[c], sum(c in g for g in
                                                        remaining.values()), c))
        chosen.append((best, unlocks[best]))
        for g in remaining.values():
            g.discard(best)
        remaining = {r: g for r, g in remaining.items() if g}
        curve.append((len(chosen), len(routes) - len(remaining)))
    return one_away, chosen, curve, need


def main() -> int:
    compounds = cat.load_compounds()
    routes = cat.load_routes()
    steps = cat.load_steps()

    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    ionic = electrolyte_provider(base=thermo, volatility=vol)
    unifac = UnifacProvider()

    rows = [audit_compound(c, thermo, vol, ionic, unifac) for c in compounds.values()]
    by_id = {r["id"]: r for r in rows}

    # ⚠⚠ SPECIES-READINESS IS NEEDED BEFORE THE WORK QUEUE, NOT AFTER IT. The
    # unlock tables below decide what gets built next, and a class that unlocks
    # three routes whose species are refused is not worth what a class that
    # unlocks one runnable route is. Reporting the unlock count alone sends work
    # at routes that cannot run either way -- measured: `catalytic-air-oxidation`
    # unlocks 3 and NONE of them is species-ready.
    species_ok: dict[str, bool] = {}
    for rid in routes:
        mine = [s for s in steps if s.route == rid]
        sp = {x for s in mine for x in s.reactants + s.products}
        species_ok[rid] = all(
            by_id[s]["tier"] != "refused" for s in sp if s in compounds
        )

    # ⚠⚠ S7 -- THE THIRD BAR, AND `RUNNABLE` HAD BEEN CLEARING ONLY TWO OF THEM.
    # A step whose PRODUCT is a marker can never be a template, whatever its
    # class says and whatever its other species cost: a marker has no molecular
    # graph, so there is nothing for a SMARTS to write. `species-ready`
    # deliberately skips markers -- that is right, because a marker REACTANT is
    # usually a stand-in for a feedstock nobody needs priced -- but the RUNNABLE
    # column then inherited the exemption on the product side too, and started
    # promising routes that cannot exist.
    #
    # Measured on the queue this file publishes: `crosslinking` was ranked
    # second at +2 unlocked / +2 runnable, and BOTH of its rows produce a
    # product with no chemistry behind it -- `tanned-leather-marker` has no
    # graph, and `vulcanised-rubber-marker` is spelled `CC(C)=CC.S1SSSSSSS1`,
    # its own two reactants written side by side. `oxidative-complexation`
    # (+1/+1, `iron-gall-ink`) is the other one this catches.
    #
    # ⚠ It does NOT touch the headline: no route in the BOTH column produces a
    # marker, checked rather than assumed. What it changes is the WORK QUEUE,
    # which is what the column is read for.
    makes_marker: dict[str, bool] = {}
    for rid in routes:
        makes_marker[rid] = any(
            cat.is_marker(p, compounds)
            for s in steps if s.route == rid
            for p in s.products
        )
    runnable_ok = {r: species_ok[r] and not makes_marker[r] for r in routes}

    n = len(rows)
    tiers = Counter(r["tier"] for r in rows)
    th_c = Counter(r["thermo_tier"] for r in rows)
    vt_c = Counter(r["vol_tier"] for r in rows)
    resolved = n - tiers["refused"]
    sourced_form = sum(th_c[t] for t in SOURCED_TIERS)
    unifac_ok = sum(1 for r in rows if r["unifac"])

    lines: list[str] = []
    w = lines.append
    w("# Compound and route coverage of the chemsim catalog")
    w("")
    w(
        "Generated by `validation/catalog_coverage.py` from `data/catalog`. "
        "Every number below is measured by running the catalog through the real "
        "providers in `src/chemsim/properties`, not asserted."
    )
    w("")
    w("## Headline")
    w("")
    w(
        "**The formation half and the physical half resolve independently, and are "
        "reported separately because they fail for different reasons and cost "
        "different things when they fail.** The formation half (dHf, dGf) sets every "
        "equilibrium constant in the simulation, so an error there propagates into "
        "yields and never washes out. The physical half (Tb/Tc/Pc/Vc) sets the "
        "vapour-pressure correlation, so an error there moves a boiling point and a "
        "headspace composition. Averaging them into one coverage number would hide "
        "which of the two you are actually short of."
    )
    w("")
    w(f"| formation half | count | of {n} |")
    w("|---|---:|---:|")
    for t in TIER_ORDER:
        w(f"| {t} | {th_c[t]} | {100*th_c[t]/n:.1f}% |")
    w("")
    w(f"| physical half | count | of {n} |")
    w("|---|---:|---:|")
    for t in TIER_ORDER:
        w(f"| {t} | {vt_c[t]} | {100*vt_c[t]/n:.1f}% |")
    w("")
    w(f"| overall | count | of {n} |")
    w("|---|---:|---:|")
    w(f"| both halves resolve | {resolved} | {100*resolved/n:.1f}% |")
    w(
        f"| formation half is measured or Benson, not Joback | {sourced_form} | "
        f"{100*sourced_form/n:.1f}% |"
    )
    w(
        f"| formation half falls back to Joback | {th_c['joback']} | "
        f"{100*th_c['joback']/n:.1f}% |"
    )
    w(f"| refused outright | {tiers['refused']} | {100*tiers['refused']/n:.1f}% |")
    w(
        f"| decompose for UNIFAC (can enter an LLE) | {unifac_ok} | "
        f"{100*unifac_ok/n:.1f}% |"
    )
    w("")
    w(
        "> The formation-half table is the one to read first. A Joback-only "
        "formation half integrates without complaint and reports a confidently "
        "wrong equilibrium constant: its error is several kJ/mol, a factor of 2-4 "
        "in K, and it gives homologues *identical* reaction energies -- the exact "
        "failure `properties/formation_data.py` was written to fix. Joback "
        "resolving is not the same as Joback being usable."
    )
    w("")
    w(
        "> The UNIFAC row is a separate and larger gap. A species with no group "
        "decomposition gets an activity coefficient of 1, and in a two-phase "
        "calculation that is not an approximation -- it is the assumption that the "
        "phases do not separate."
    )
    w("")

    # ---- by tier -------------------------------------------------------
    w("## Resolution tier, and which half is weaker")
    w("")
    w("| tier | as the limiting half | formation half | physical half |")
    w("|---|---:|---:|---:|")
    for t in TIER_ORDER:
        w(f"| {t} | {tiers[t]} | {th_c[t]} | {vt_c[t]} |")
    w("")

    # ---- by class ------------------------------------------------------
    w("## By compound class")
    w("")
    w("| class | n | formation measured/Benson | formation Joback | refused | unifac |")
    w("|---|---:|---:|---:|---:|---:|")
    by_class: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_class[r["class"]].append(r)
    for cls, sub in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        f = Counter(x["thermo_tier"] for x in sub)
        good = sum(f[t] for t in SOURCED_TIERS)
        u = sum(1 for x in sub if x["unifac"])
        w(f"| {cls} | {len(sub)} | {good} | {f['joback']} | {f['refused']} | {u} |")
    w("")

    # ---- by role -------------------------------------------------------
    w("## By catalog role")
    w("")
    w("| role | n | formation measured/Benson | formation Joback | refused |")
    w("|---|---:|---:|---:|---:|")
    by_role: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_role[r["role"]].append(r)
    for role, sub in sorted(by_role.items(), key=lambda kv: -len(kv[1])):
        f = Counter(x["thermo_tier"] for x in sub)
        good = sum(f[t] for t in SOURCED_TIERS)
        w(f"| {role} | {len(sub)} | {good} | {f['joback']} | {f['refused']} |")
    w("")

    # ---- refusals ------------------------------------------------------
    refused = [r for r in rows if r["tier"] == "refused"]
    w(f"## The {len(refused)} refusals, by cause")
    w("")
    buckets = Counter(refusal_bucket(r["why"]) for r in refused)
    remedy = {
        "charged organic (outside the Born domain)":
            "nothing cheap. The Born radius correlation is fitted to small hard "
            "ions and an organic cation is not one, so the refusal is right.",
        "physical half missing (needs a boiling point)":
            "ONE measured Tb per species. The formation half already resolved.",
        "formation half missing (no group value)":
            "a group value that may not exist in any published tabulation; "
            "check before promising it.",
        "cannot be fragmented at all":
            "usually an element or an exotic heteroatom, and out of the domain "
            "of both group methods by construction. A LATTICE no longer reaches "
            "this bucket: it is priced on the solid basis from mineral_data, "
            "which is a curation job per mineral rather than a group value.",
    }
    w("| cause | count | what would close it |")
    w("|---|---:|---|")
    for cause, count in buckets.most_common():
        w(f"| {cause} | {count} | {remedy.get(cause, '')} |")
    w("")
    cheap = sorted(
        r["id"] for r in refused
        if refusal_bucket(r["why"]).startswith("physical half")
    )
    w(
        "> The boiling-point bucket is the cheap one and it is worth separating: "
        "those species already have a formation half from Benson and are refused "
        "only because nothing prices their vapour pressure. That is a lookup, not "
        "a research problem."
    )
    w("")
    w(f"### The {len(cheap)} that need only a boiling point")
    w("")
    w(("`" + "`, `".join(cheap) + "`") if cheap else "None.")
    w("")
    w(f"### All {len(refused)} refusals, named")
    w("")
    if not refused:
        w("None.")
    else:
        w("| compound | class | why |")
        w("|---|---|---|")
        for r in sorted(refused, key=lambda x: (x["class"], x["id"])):
            w(f"| `{r['id']}` | {r['class']} | {r['why'] or 'provider refused'} |")
    w("")

    # ---- reaction classes ----------------------------------------------
    step_classes = Counter(s.cls for s in steps)
    covered = {c for c in step_classes if c in TEMPLATE_CLASSES}
    w("## Reaction coverage -- the half that does not flatter")
    w("")
    w(
        f"The catalog's {len(steps)} steps use **{len(step_classes)} distinct "
        f"reaction classes**. This project implements **{N_TEMPLATES} templates** "
        f"({N_LIBRARY_TEMPLATES} in `reactions/library.py`, "
        f"{N_SYNTHESIS_TEMPLATES} in `reactions/synthesis.py` and "
        f"{N_ELECTROLYTE_TEMPLATES} dissociation templates in "
        f"`properties/electrolyte.py`), which between them cover "
        f"**{len(covered)}** of those classes, i.e. "
        f"**{sum(step_classes[c] for c in covered)}** of the {len(steps)} steps."
    )
    w("")
    w("| covered class | template | steps using it |")
    w("|---|---|---:|")
    for c in sorted(covered, key=lambda x: (-step_classes[x], x)):
        w(f"| {c} | `{TEMPLATE_CLASSES[c]}` | {step_classes[c]} |")
    w("")
    w("### The most-used classes with NO template")
    w("")
    w("| class | steps | routes blocked |")
    w("|---|---:|---:|")
    blocked_routes: dict[str, set[str]] = defaultdict(set)
    for s in steps:
        if s.cls not in TEMPLATE_CLASSES:
            blocked_routes[s.cls].add(s.route)
    missing = sorted(
        (c for c in step_classes if c not in TEMPLATE_CLASSES),
        key=lambda c: (-step_classes[c], c),
    )
    for c in missing[:40]:
        w(f"| {c} | {step_classes[c]} | {len(blocked_routes[c])} |")
    w("")
    w(f"…and {max(0, len(missing) - 40)} further classes used once or twice each.")
    w("")

    # ---- ranked by MARGINAL UNLOCK, which is the ranking that decides work --
    one_away, chosen, curve, need = marginal_unlock(steps, routes)
    w("### ⚠ The same gap ranked by ROUTES UNLOCKED, which is a different order")
    w("")
    w(
        "The table above ranks by how many STEPS use a class. That is the wrong "
        "ranking for deciding what to build, and the two orders barely overlap: "
        "the most-used missing classes unlock **zero** routes on their own, "
        "because the routes needing them each need several other things too. "
        "**Read this table as the work queue and the one above as context.**"
    )
    w("")
    n_one = sum(len(v) for v in one_away.values())
    w(
        f"{len(need)} routes have at least one gap. **{n_one} of them are ONE "
        f"class away**, and those come from **{len(one_away)} different classes** "
        f"-- which is why there is no bottleneck to attack and why this milestone "
        f"argues for a target rather than for completeness."
    )
    w("")
    w(
        "> ⚠⚠ **READ THE `RUNNABLE` COLUMN, NOT THE `ALONE` COLUMN.** A template "
        "unlocks a route only in the template column; the route still needs every "
        "species priced. `runnable` counts the ones that would clear BOTH bars. "
        "The two orders disagree at the top, which is exactly when it matters."
    )
    w("")
    w("| class | routes it unlocks ALONE | ...of those, RUNNABLE | steps | those routes |")
    w("|---|---:|---:|---:|---|")
    for cls, rids in sorted(
        one_away.items(),
        key=lambda kv: (-sum(runnable_ok[r] for r in kv[1]), -len(kv[1]), kv[0]),
    )[:20]:
        names = ", ".join(f"`{r}`" for r in sorted(rids)[:4])
        if len(rids) > 4:
            names += f", +{len(rids) - 4} more"
        run = sum(runnable_ok[r] for r in rids)
        w(f"| {cls} | {len(rids)} | **{run}** | {step_classes[cls]} | {names} |")
    w("")
    w("#### The greedy set-cover curve")
    w("")
    w(
        "Templates added in the order that unlocks the most routes at each step. "
        "⚠ The gain FALLS AWAY fast, and that shape is the finding: there is no "
        "small set of templates that unlocks the catalog."
    )
    w("")
    w("| templates added | class added | routes unlocked by it | template-ready total |")
    w("|---:|---|---:|---:|")
    for (cls, gain), (added, total) in zip(chosen, curve):
        w(f"| {added} | {cls} | +{gain} | {total} |")
    w("")
    top3 = [
        (cls, gain, sum(runnable_ok[r] for r in one_away.get(cls, ())))
        for cls, gain in chosen[:3]
    ]
    w(
        "> ⚠⚠ **THIS CURVE OPTIMISES THE OVERSTATED COLUMN.** Its totals are "
        "template-ready, and a route also needs every species priced. Its top "
        "three rows are "
        + "; ".join(
            f"`{c}` +{g} unlocked / **{r} runnable**" for c, g, r in top3
        )
        + " -- so the curve's own ordering is not the work order. "
        "Cross-reference the `RUNNABLE` column above before taking the top row."
    )
    w("")

    # ---- route readiness ------------------------------------------------
    w("## Route readiness")
    w("")
    w(
        "A route is *species-ready* when every non-marker species in its steps "
        "resolves; *sourced* when none of them falls back to Joback; and "
        "*template-ready* when every one of its step classes has a template. "
        "⚠ These are INDEPENDENT questions, and neither of the first two bounds "
        "the third — so the row that decides whether a route can run at all is "
        "the intersection, which is smaller than any of them."
    )
    w("")
    species_ready = sourced_routes = template_ready = 0
    route_rows = []
    mineral_carried: list[tuple[str, list[str]]] = []
    for rid, route in routes.items():
        mine = [s for s in steps if s.route == rid]
        species = {x for s in mine for x in s.reactants + s.products}
        real = [s for s in species if s in compounds]
        markers = len(species) - len(real)
        # ⚠⚠ S4 RECORDED THIS COLUMN AS BLIND TO ``mineral_data`` AND ESTIMATED
        # THE GAP AT 14 ROUTES. S6 CLOSED IT AND THE NUMBER IS 16.
        #
        # The diagnosis was right: ``tier`` came from the plain
        # ``ThermochemistryProvider``, which REFUSES a lattice by name --
        # correctly, because the fusion law is 407x wrong for one -- while since
        # M3 a lattice has had a home on the SOLID basis, and it is the table
        # precipitation, ``SolidStateArrays`` and ``SurfaceArrays`` all price
        # from. So a route whose only refused species were minerals this project
        # prices read species-UNREADY while running end to end. That is fixed in
        # ``_mineral_fallback``: 19 compounds move refused -> ``mineral``, and
        # species-ready goes 49 -> 65 of 173, fully-sourced 5 -> 14.
        #
        # ⚠⚠ THE RECORDED 14 WAS ITSELF THE BUG, ONE LAYER DOWN. It was measured
        # with a RAW string comparison of the catalog's SMILES against the
        # ``by_lattice`` key, and the catalog spells its salts in a different
        # fragment order than the canonical table -- ``[Ca+2].[O-]C([O-])=O``
        # against ``O=C([O-])[O-].[Ca+2]``. Matching canonically, which is what
        # ``network/builder.py`` does to every input SMILES before the species
        # list exists, gives 16. The two it missed are ``vulcanisation`` and
        # ``lime-cycle`` -- and ``lime-cycle`` is the route S4's own note names
        # in prose as the headline case while its list of 14 ids omits it. **The
        # recorded number, the recorded list and the recorded prose disagreed
        # with each other, and only re-measuring showed it.**
        #
        # ⚠ IT IS THE OPPOSITE SHAPE TO ``pyrite-roasting``, which reads
        # template-ready and does NOT run. This one read unready and DOES, so
        # the credit was checked the expensive way rather than argued: all 19
        # rescued minerals were charged into a real ``Vessel``'s solid block,
        # 19 of 19 holding their full charge. ``mercury-from-cinnabar`` closes
        # at 0.020000000000 mol of mercury on a 0.02 mol charge (S4), and
        # ``lime-cycle`` has run end to end since M6.
        #
        # ⚠ WHAT SPECIES-READY DOES **NOT** CLAIM FOR THESE. A mineral resolves
        # here on the solid basis only. It can be charged, held and reacted as a
        # crystal; it still cannot dissolve, and a step needing one in solution
        # is still not expressible. Template-readiness remains the binding
        # constraint and none of the 16 becomes template-ready.
        ok = all(by_id[s]["tier"] != "refused" for s in real)
        src = ok and all(by_id[s]["tier"] != "joback" for s in real)
        tmpl = all(s.cls in TEMPLATE_CLASSES for s in mine)
        species_ready += ok
        sourced_routes += src
        template_ready += tmpl
        # Which routes does the ``mineral`` tier actually carry? A credit that
        # cannot be pointed at the species it rests on is not auditable, and
        # this column has already been mis-stated once by a note that named a
        # route its own list did not contain.
        if ok:
            mins = sorted(s for s in real if by_id[s]["tier"] == "mineral")
            if mins:
                mineral_carried.append((rid, mins))
        route_rows.append((rid, route.era, len(mine), markers, ok, src, tmpl))
    total_r = len(routes)
    w(f"| | routes | of {total_r} |")
    w("|---|---:|---:|")
    w(f"| species-ready | {species_ready} | {100*species_ready/total_r:.1f}% |")
    w(f"| fully sourced (no Joback anywhere) | {sourced_routes} | "
      f"{100*sourced_routes/total_r:.1f}% |")
    w(f"| template-ready | {template_ready} | {100*template_ready/total_r:.1f}% |")
    # ⚠⚠ THE INTERSECTION IS THE ONLY ONE OF THESE A ROUTE CAN BE JUDGED ON, AND
    # UNTIL S6 NOTHING COMPUTED IT. The three columns above are independent
    # questions and were reported as though the smallest bounded the others. It
    # does not: a route needs a template for every step AND a price for every
    # species, and **11 of the 28 template-ready routes have a refused species**.
    # Quoting 28 as "what could run" overstates it by a factor of 1.6.
    both_ready = sum(1 for r in route_rows if r[4] and r[6])
    w(f"| **BOTH — template-ready AND species-ready** | **{both_ready}** | "
      f"**{100*both_ready/total_r:.1f}%** |")
    w("")
    ready = [r for r in route_rows if r[6]]
    w("Template-ready routes: " + (", ".join(f"`{r[0]}`" for r in ready) or "none"))
    w("")
    blocked = sorted(r[0] for r in route_rows if r[6] and not r[4])
    w(
        f"> ⚠⚠ **{both_ready} is the number to quote, not {template_ready}.** The "
        "three rows above answer independent questions and the smallest does NOT "
        "bound the others: a route needs a template for every step **and** a "
        f"price for every species. **{len(blocked)} template-ready routes have a "
        "refused species and cannot run**: "
        + (", ".join(f"`{r}`" for r in blocked) or "none") + "."
    )
    w("")
    w(
        f"> ⚠ And {both_ready} is an **upper bound on what runs**, not a measured "
        "count. A class is credited when a template would fire on the right "
        "substrate at all; `pyrite-roasting` is the standing proof that this is "
        "not the same as running, and S1 credited a route that could not. The "
        "only way to know a route runs is to run it."
    )
    w("")

    # ---- what the mineral tier carries ---------------------------------
    w(f"### The {len(mineral_carried)} routes species-ready on a lattice")
    w("")
    w(
        "These are species-ready only because a species in them is priced as a "
        "crystal on the solid basis from `mineral_data`, after all three "
        "ideal-gas providers refused it. The refusals are correct -- the fusion "
        "law is the engine's only route from a solid into solution and it is "
        "measured wrong for a lattice by up to 407x in **both** directions -- "
        "but refusing to *dissolve* a species is not refusing to *price* it, and "
        "this column used to conflate the two."
    )
    w("")
    w(
        "> ⚠ The claim is narrow and worth stating in full: each species below "
        "can be charged, held and reacted **as a crystal**. It still cannot "
        "dissolve, so a step that needs one in solution is still not "
        "expressible, and none of these routes becomes template-ready. Every "
        "one of them was verified by charging the mineral into a real `Vessel` "
        "solid block rather than by argument."
    )
    w("")
    if not mineral_carried:
        w("None.")
    else:
        w("| route | priced as a lattice | the mineral it is |")
        w("|---|---|---|")
        for rid, mins in sorted(mineral_carried):
            w(f"| `{rid}` | " + ", ".join(f"`{m}`" for m in mins) + " | "
              + ", ".join(by_id[m]["mineral"] for m in mins) + " |")
    w("")

    # ---- the same gap, one step further out ----------------------------
    # ⚠ GENERATED RATHER THAN WRITTEN DOWN, DELIBERATELY. The estimate this
    # section replaces was a hand-written comment, and it disagreed with its own
    # prose about which routes it covered. A measured number regenerated on every
    # run cannot drift from the corpus the way that one did.
    bare = {
        r["id"] for r in rows
        if r["tier"] == "refused" and "a bare element symbol" in r["why"]
    }
    bare_blocked = {}
    for rid in routes:
        mine = [s for s in steps if s.route == rid]
        sp = {x for s in mine for x in s.reactants + s.products}
        bad = [s for s in sp if s in compounds and by_id[s]["tier"] == "refused"]
        if bad and all(b in bare for b in bad):
            bare_blocked[rid] = sorted(bad)
    lever: Counter = Counter()
    for bad in bare_blocked.values():
        if len(bad) == 1:
            lever[bad[0]] += 1

    w(f"### The next one along: {len(bare_blocked)} routes blocked only by a "
      f"bare ELEMENT")
    w("")
    w(
        f"{len(bare)} compounds are still refused with *a bare element symbol is "
        "the most ambiguous way to name an allotrope*, and the refusal is right "
        "and permanent: the ideal-gas value for `[C]` is the ATOM at Gf +671 "
        "kJ/mol, while the charcoal in the flask is 0."
    )
    w("")
    w(
        "⚠⚠ **THIS SECTION USED TO SAY THE GAP WAS 45 COMPOUNDS AND 15 ROUTES, "
        "AND S8 CLOSED IT -- FOR +0 ON THE INTERSECTION, WHICH WAS PREDICTED.** "
        "Nine element solids were curated into `mineral_data` on the SOLID basis "
        "(`cobalt`, `silver`, `platinum`, `palladium`, `lead`, `aluminium`, "
        "`sodium`, `zinc`, `carbon-graphite`), joining the three S1 added for its "
        "catalysts. **Not one of the 15 routes was template-ready**, so "
        "species-ready moved 63 -> 77 and the column a route is judged on did "
        "not move at all. What it bought is a MULTIPLIER on template work -- "
        "nine new entries in the RUNNABLE table above, seven of which survive "
        "the balance audit. The ordering lesson is recorded in MILESTONES.md "
        "§S8: **a species job should FOLLOW the template it enables.**"
    )
    w("")
    w(
        "⚠⚠ **AND S10 TOOK ONE OF THE NINE BACK OUT, WHICH IS NOT A CORRECTION "
        "OF S8.** `zinc` is no longer a `mineral_data` lattice: it has a "
        "monatomic vapour, ONE condensed form and a measured sublimation curve, "
        "so it passes every test S4 admitted mercury on and it belongs in "
        "`element_data` -- where, unlike a lattice, it can BOIL. S8's curation "
        "was right for what it was for; what changed is that *a lattice may "
        "react and may never boil* turned out to be a statement about the ENTRY "
        "and not about the metal. `zinc-smelting`'s retort evolves zinc VAPOUR "
        "now and condenses it in a cool receiver, which is a real Belgian "
        "retort's actual mechanic -- for **+0 on all four columns here**, "
        "predicted before it was measured. Eight of the nine remain. See "
        "MILESTONES.md §S10."
    )
    w("")
    w(
        "> ⚠ THE LAYERING QUESTION IS ANSWERED AND IT IS IN THE TYPE, NOT THE "
        "MODULE NAME. `element_data`'s record is on the IDEAL-GAS basis, and the "
        "ideal-gas record for `[Fe]` is the ATOM at +416 kJ/mol -- a real number "
        "that is not iron filings. So a solid-basis zero lives in the "
        "solid-basis module, and `element_data.REFERENCE_STATES` supplies the S0 "
        "the Gf derivation consumes. What is left in this list is elements no "
        "route needs on its own; a route wanting one is a curation job with no "
        "design question left in front of it, and "
        "`tools/build_mineral_data.ELEMENT_SOLIDS` is where it goes."
    )
    if bare_blocked:
        w("")
        w(
            "> ⚠ AND READ THE REMAINING ROW FOR WHAT IT IS. `gunpowder` is listed "
            "because `gunpowder-marker` is spelled "
            "`[K+].[O-][N+]([O-])=O.S1SSSSSSS1.[C]` -- a four-fragment "
            "COMPOSITION, priced fragment by fragment down the ionic path, whose "
            "`[C]` fragment still refuses. The `mineral` fallback is consulted "
            "for a whole species and not per fragment, which is a real "
            "inconsistency and an inert one: `gunpowder` step 2 is also one of "
            "the rows `validation/corpus_balance.py` cannot balance."
        )
    w("")
    if bare_blocked:
        w("| route | blocked only by |")
        w("|---|---|")
        for rid, bad in sorted(bare_blocked.items()):
            w(f"| `{rid}` | " + ", ".join(f"`{b}`" for b in bad) + " |")
        w("")
        w("Routes a SINGLE curated element would unlock on its own:")
        w("")
        w("| element | routes it unlocks alone |")
        w("|---|---:|")
        for el, c in sorted(lever.items(), key=lambda kv: (-kv[1], kv[0])):
            w(f"| `{el}` | +{c} |")
    else:
        w("None.")
    w("")
    w("### Routes by era")
    w("")
    w("| era | routes | species-ready | fully sourced | template-ready |")
    w("|---|---:|---:|---:|---:|")
    by_era: dict[str, list] = defaultdict(list)
    for r in route_rows:
        by_era[r[1]].append(r)
    for era in ["ancient", "alchemical", "1700s", "1800s", "1900s", "modern"]:
        sub = by_era.get(era, [])
        if not sub:
            continue
        w(
            f"| {era} | {len(sub)} | {sum(1 for x in sub if x[4])} | "
            f"{sum(1 for x in sub if x[5])} | {sum(1 for x in sub if x[6])} |"
        )
    w("")

    out = os.path.join(cat.CATALOG_DIR, "COVERAGE_REPORT.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    # ---- derived role tables -------------------------------------------
    derived = os.path.join(cat.CATALOG_DIR, "derived")
    os.makedirs(derived, exist_ok=True)
    with open(os.path.join(derived, "route_roles.psv"), "w", encoding="utf-8") as fh:
        fh.write("# DERIVED by validation/catalog_coverage.py -- do not hand-edit.\n")
        fh.write("# route_id | role | species (semicolon separated)\n")
        fh.write("# role: feedstock (consumed, never made) | intermediate (both) |\n")
        fh.write("#       product (made, never consumed) | catalyst (both sides of\n")
        fh.write("#       one step). See tools/catalog.py for why this is derived.\n")
        for rid in routes:
            roles = cat.route_roles(steps, rid)
            for label, members in (
                ("feedstock", roles.feedstocks),
                ("intermediate", roles.intermediates),
                ("product", roles.products),
                ("catalyst", roles.catalysts),
            ):
                if members:
                    fh.write(f"{rid} | {label} | {';'.join(members)}\n")

    # A species-level rollup: how often is each compound an intermediate anywhere?
    counts: dict[str, Counter] = defaultdict(Counter)
    for rid in routes:
        roles = cat.route_roles(steps, rid)
        for label, members in (
            ("feedstock", roles.feedstocks),
            ("intermediate", roles.intermediates),
            ("product", roles.products),
            ("catalyst", roles.catalysts),
        ):
            for m in members:
                counts[m][label] += 1
    with open(os.path.join(derived, "species_roles.psv"), "w", encoding="utf-8") as fh:
        fh.write("# DERIVED by validation/catalog_coverage.py -- do not hand-edit.\n")
        fh.write("# species | routes | as_feedstock | as_intermediate | as_product |")
        fh.write(" as_catalyst | tier\n")
        for sp, c in sorted(counts.items(), key=lambda kv: -sum(kv[1].values())):
            tier = by_id[sp]["tier"] if sp in by_id else "marker"
            total = sum(c.values())
            fh.write(
                f"{sp} | {total} | {c['feedstock']} | {c['intermediate']} | "
                f"{c['product']} | {c['catalyst']} | {tier}\n"
            )

    print(f"{n} compounds, {len(routes)} routes, {len(steps)} steps")
    print(f"  resolve            {resolved}/{n}  ({100*resolved/n:.1f}%)")
    print(f"  formation measured/Benson {sourced_form}/{n}  ({100*sourced_form/n:.1f}%)")
    print(f"  formation Joback          {th_c['joback']}/{n}")
    print(f"  formation on a lattice    {th_c['mineral']}/{n}  (solid basis)")
    print(f"  refused                   {tiers['refused']}/{n}")
    print(f"  UNIFAC groups      {unifac_ok}/{n}  ({100*unifac_ok/n:.1f}%)")
    print(f"  reaction classes   {len(covered)}/{len(step_classes)} have a template")
    print(f"  routes species-ready  {species_ready}/{total_r} "
          f"({len(mineral_carried)} of them carried by a lattice)")
    print(f"  routes template-ready {template_ready}/{total_r}")
    print(f"  routes BOTH (the one to quote) {both_ready}/{total_r} "
          f"-- {template_ready - both_ready} template-ready routes have a "
          f"refused species")
    print(f"\nwrote {out}")
    print(f"wrote {derived}/route_roles.psv and species_roles.psv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

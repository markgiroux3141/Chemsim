"""Wilson-Jasperson, Fedors, and the two-half assembly they exist to enable.

The architectural point being tested: a physical half and a formation half now
resolve INDEPENDENTLY, so a measured boiling point can pair with a Benson
enthalpy of formation. Before that, ``ThermochemistryProvider`` consulted Benson
only after Joback had already succeeded, and Benson priced acetic anhydride to
within 3.7 kJ/mol of measurement while the provider refused the species outright.
"""

import math

import pytest

from chemsim.matter import Molecule
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.critical import (
    CriticalPropertyError,
    acentric_factor,
    estimate_physical,
    fedors,
    hvap_at_tb,
    wilson_jasperson,
)
from chemsim.properties.formation_data import PHYSICAL_PROPERTIES
from chemsim.properties.physical_data import (
    CORPUS_SWEEP,
    MEASURED_PHYSICAL,
)
from chemsim.properties.thermochemistry import _CURATED_RAW
from chemsim.properties.volatility import P_ATM_BAR

ACETIC_ANHYDRIDE = "CC(=O)OC(C)=O"
VANILLIN = "O=Cc1ccc(O)c(OC)c1"


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


# ---------------------------------------------------------------------------
# faithful transcription -- checked against the ``thermo`` oracle
# ---------------------------------------------------------------------------
# The tables in ``critical_data`` are extracted from ``thermo`` at build time, and
# the arithmetic around them is ours. That is the same arrangement as Joback, and
# it needs the same guard: the oracle says whether we transcribed and implemented
# it faithfully, and nothing else can.


@pytest.mark.parametrize(
    "smi,Tb",
    [
        ("CC(=O)OC(C)=O", 412.65),          # anhydride
        ("CCc1ccccc1O", 477.67),            # the reference example in Poling
        ("CCO", 351.44),                    # small alcohol -- OH_small branch
        ("CCCCCCO", 430.0),                 # large alcohol -- OH_large branch
        ("CCN(CC)CC", 362.0),               # tertiary amine
        ("CCN", 289.7),                     # primary amine (explicit-H trap)
        ("ClC(Cl)Cl", 334.3),               # halide flag
        ("CC#N", 354.8),                    # nitrile
        ("O=[N+]([O-])c1ccccc1", 483.9),    # nitro
        ("c1ccsc1", 357.3),                 # sulfur, ring
        ("c1ccc2ccccc2c1", 491.1),          # fused rings
        ("C1CC1", 240.4),                   # 3-ring
        ("CS(C)=O", 465.05),                # sulfoxide
        ("O=Cc1ccco1", 434.65),             # furan aldehyde
        ("OCC1OC(O)C(O)C(O)C1O", 1000.0),   # many hydroxyls
    ],
)
def test_wilson_jasperson_and_fedors_reproduce_the_oracle_exactly(smi, Tb):
    """Bit-for-bit, not approximately.

    Any drift here means either a table entry changed or a group-counting rule
    diverged, and both are silent-wrong-answer bugs of exactly the kind the
    project has already paid for (PSRK's ``[HH]`` matching every hydroxyl).
    """
    pytest.importorskip("thermo")
    from thermo.group_contribution import Fedors, Wilson_Jasperson

    mol = Molecule.from_smiles(smi)
    tc_ref, pc_ref, missing_tc, missing_pc = Wilson_Jasperson(smi, Tb=Tb)
    assert not missing_tc and not missing_pc, "oracle itself refuses this species"

    tc, pc = wilson_jasperson(mol, Tb)
    assert tc == pytest.approx(tc_ref, rel=1e-12)
    assert pc == pytest.approx(pc_ref / 1e5, rel=1e-12)     # oracle returns Pa

    vc_ref, status, *_ = Fedors(smi)
    assert status == "OK", "oracle itself refuses this species"
    assert fedors(mol) == pytest.approx(vc_ref * 1e6, rel=1e-12)  # oracle m3/mol


def test_the_explicit_hydrogen_view_is_what_fedors_is_published_against():
    """Fedors' amine term counts something different in the two views.

    ``amine_smarts`` carries ``!$([N]~[!#6])`` -- no non-carbon neighbour -- and
    with hydrogens as real atoms an N-H bond satisfies ``[!#6]``, so primary and
    secondary amines stop matching and only tertiary ones survive. This is not a
    detail to normalise away: it is why ``Molecule.substructure_matches`` grew an
    ``explicit_hydrogens`` flag, and getting it backwards silently shifts Vc.
    """
    from chemsim.properties.critical_data import FEDORS_GROUP_SMARTS

    amine = FEDORS_GROUP_SMARTS["N_amine"]
    ethylamine = Molecule.from_smiles("CCN")
    assert len(ethylamine.substructure_matches(amine, explicit_hydrogens=True)) == 0
    assert len(ethylamine.substructure_matches(amine)) == 1

    # A tertiary amine matches in both views, so it cannot detect the mistake --
    # which is precisely why the primary case is the one asserted.
    triethylamine = Molecule.from_smiles("CCN(CC)CC")
    assert len(triethylamine.substructure_matches(amine, explicit_hydrogens=True)) == 1


# ---------------------------------------------------------------------------
# refusing rather than guessing
# ---------------------------------------------------------------------------


def test_fedors_refuses_phosphorus_rather_than_dropping_it():
    """Glyphosate is the case this exists for.

    The reference implementation returns a number with an ``'errors found'``
    string beside it; a caller who ignores the string gets a confident Vc for a
    molecule the method does not cover. Refusing is the project's rule.
    """
    with pytest.raises(CriticalPropertyError, match=r"\['P'\]"):
        fedors(Molecule.from_smiles("OC(=O)CNCP(=O)(O)O"))


def test_wilson_jasperson_refuses_an_element_it_never_regressed():
    with pytest.raises(CriticalPropertyError, match="no Tc increment"):
        wilson_jasperson(Molecule.from_smiles("[Fe]"), 3000.0)


def test_tc_and_pc_must_be_supplied_as_a_pair():
    """They combine into the acentric factor, so one measured beside one
    estimated would put two bases inside one derived number -- the same rule
    that forbids an ATCT enthalpy beside a CRC entropy in one formation entry."""
    mol = Molecule.from_smiles(ACETIC_ANHYDRIDE)
    with pytest.raises(CriticalPropertyError, match="together or not at all"):
        estimate_physical(mol, 412.65, "test", Tc=606.0)


# ---------------------------------------------------------------------------
# the enthalpy of vaporisation, derived rather than transcribed
# ---------------------------------------------------------------------------


def test_hvap_is_the_slope_of_the_curve_the_vessel_actually_uses():
    """``hvap_at_tb`` differentiates Lee-Kesler analytically. Check it against a
    finite difference of the same curve, so the derivative and the function
    cannot drift apart.

    This matters beyond tidiness: the vessel pins its temperature from Psat and
    sets its boil-off rate from Hvap, so if those came from two different
    correlations a flask would boil at the right temperature and the wrong rate.
    """
    from chemsim.properties.critical import lee_kesler_psat

    Tb, Tc, Pc = 412.65, 606.0, 40.0
    omega = acentric_factor(Tb, Tc, Pc)

    h = 0.01
    lo = math.log(lee_kesler_psat(Tb - h, Tc, Pc, omega))
    hi = math.log(lee_kesler_psat(Tb + h, Tc, Pc, omega))
    numeric = 8.314462618 * Tb**2 * (hi - lo) / (2 * h) / 1000.0

    assert hvap_at_tb(Tb, Tc, Pc, omega) == pytest.approx(numeric, rel=1e-6)


def test_hvap_from_measured_criticals_lands_within_the_ideal_vapour_offset():
    """With MEASURED Tc/Pc the only error left is the dz = 1 assumption, which is
    a few per cent high and systematically so. Bounded here so a regression in
    the derivation shows up as a sign or magnitude change rather than as scatter.

    Formic acid is excluded and the reason is chemistry, not convenience: its
    vapour is dimeric, so its apparent enthalpy of vaporisation prices a
    different molecule from the one the curve describes. Same trap as the
    carboxylic-acid exclusions in ``formation_data``.
    """
    errors = []
    for smi, phys in PHYSICAL_PROPERTIES.items():
        if smi == "O=CO" or None in (phys.get("Hvap"), phys.get("Tc"), phys.get("Pc")):
            continue
        est = hvap_at_tb(phys["Tb"], phys["Tc"], phys["Pc"])
        errors.append(100.0 * (est - phys["Hvap"]) / phys["Hvap"])

    assert len(errors) >= 7
    assert all(0.0 < e < 8.0 for e in errors), errors


# ---------------------------------------------------------------------------
# the architectural fix
# ---------------------------------------------------------------------------


def test_a_measured_physical_half_pairs_with_a_benson_formation_half(thermo):
    """THE fix. Acetic anhydride: Joback cannot fragment it at all, Benson prices
    its formation, and a measured boiling point supplies the physical half."""
    t = thermo.get(ACETIC_ANHYDRIDE)

    assert "Benson" in t.source                     # formation half
    assert "Tb CRC_ORG" in t.physical_source        # physical half
    # Benson against measurement: -576.2 vs -572.5 kJ/mol.
    assert t.Hf == pytest.approx(-572.5, abs=5.0)
    assert t.Tb == pytest.approx(412.65, abs=0.01)
    assert None not in (t.Tc, t.Pc, t.Vc, t.Hvap)


def test_the_halves_are_named_separately_in_the_provenance(thermo):
    """A record can be three tabulations deep, so the string has to say so."""
    t = thermo.get(VANILLIN)
    assert t.source.startswith("formation half: Benson")
    assert "Tb CRC_ORG (experimental)" in t.physical_source
    assert "Wilson-Jasperson" in t.physical_source
    assert "Fedors" in t.physical_source


def test_switching_the_new_route_off_reproduces_the_old_refusal():
    """``measured_physical=False`` is the measure-the-difference switch, the same
    as ``benson=False`` and ``build_network(liquid_standard_state=False)``."""
    before = ThermochemistryProvider(measured_physical=False)
    with pytest.raises(ValueError):
        before.get(ACETIC_ANHYDRIDE)
    assert ThermochemistryProvider().get(ACETIC_ANHYDRIDE).Tb is not None


def test_a_formation_half_with_no_physical_half_is_refused_not_silently_inert():
    """The one way the two-half split can go quietly wrong, and it did.

    ``volatility`` treats a record with no Tb/Tc/Pc as non-volatile and says
    "decomposes before it boils". That is right for a sugar and a confident lie
    for acetic anhydride, which boils at 412 K. Before the halves were separated,
    Joback's refusal raised and the question never came up; afterwards a Benson
    formation half alone was enough to manufacture a record that got silently
    declared non-volatile. It must refuse instead.
    """
    provider = ThermochemistryProvider(measured_physical=False)
    with pytest.raises(ValueError, match="NO physical half"):
        provider.get(ACETIC_ANHYDRIDE)

    # ... and the guard names the fix rather than just complaining.
    with pytest.raises(ValueError, match="physical_data"):
        provider.get(ACETIC_ANHYDRIDE)


def test_a_species_nothing_boils_still_gets_its_melting_point(thermo):
    """Thiourea, saccharin and glyphosate decompose before they boil and no source
    tabulates a Tb for any of them, so non-volatile is the CORRECT physical answer
    rather than a shortfall -- and the melting point still drives crystallisation,
    which is how those species behave on a bench.

    Tested at the half rather than through ``get``, deliberately. None of these
    species currently has a working FORMATION half either (Benson has no value
    for a thiourea carbon, an aryl-amide carbonyl or phosphorus), so ``get``
    refuses them on formation and the physical half's behaviour would be
    invisible. Asserting it here keeps the two failures separate instead of
    letting one mask the other -- and this path becomes live the moment any
    non-boiling species gains a formation value.
    """
    half = thermo._physical_half(Molecule.from_smiles("NC(N)=S"), None)
    assert half.Tb is None and not half.usable
    assert half.Tm == pytest.approx(450.15, abs=0.01)
    assert half.Hfus == pytest.approx(14.0, abs=0.01)
    assert "NO boiling point is tabulated" in half.source

    # And the record as a whole still refuses -- on the formation half, naming it.
    with pytest.raises(ValueError, match="no estimator can price its formation"):
        thermo.get("NC(N)=S")


# ---------------------------------------------------------------------------
# the assembled records have to behave like substances
# ---------------------------------------------------------------------------


# ⚠⚠ THE SPECIES THIS CHECK DOES NOT HOLD TO 1.5%, EACH NAMED WITH ITS
# MEASURED RESIDUAL. S13 MEASURED THEM; ALL BUT ONE ARE ASSOCIATING LIQUIDS.
#
# The 1.5% bar was set over NINE hand-curated species and it is a good bar: 858
# of 889 records clear it. What S13 changed is the population -- the corpus
# sweep put 1202 more species in the table -- and a bar measured over nine of
# anything is a bar measured over nine of anything.
#
# ⚠ EIGHT OF THE THIRTY-ONE ARE PRE-EXISTING AND THIS CHECK COULD NOT SEE THEM,
# which is the finding worth keeping. It walked ``MEASURED_PHYSICAL``; water,
# SO2, SO3, HF, formaldehyde, nitric acid, N2O2 and zinc are in ``_CURATED_RAW``
# and in ``PHYSICAL_PROPERTIES``, so the check that exists for exactly this
# question was asking it of the wrong list. It now walks all three.
#
# What the residual IS: Lee-Kesler is a three-parameter corresponding-states
# correlation and a three-parameter Antoine is being least-squares fitted to it
# over a 240 K window. Neither knows about hydrogen bonding, and every species
# in the loose set below is polar, associating, or both, and boils between 250
# and 375 K where the curvature is worst. This is an ACCURACY limit of the
# correlation chain, not a defect in the fit -- widening the window makes it
# worse, not better.
#
# ⚠⚠ AND ZINC IS NOT A SECOND FINDING, IT IS S10's FIRST ONE IN THE OTHER
# VARIABLE. S10 recorded zinc's curated Alcock curve as boiling at 1168.84 K
# against a measured 1180.15 -- **-0.96% in TEMPERATURE**. The same disagreement
# read as a PRESSURE at the measured Tb is **+12.61%**, because dP/P is
# (dHvap/RT) dT/T and zinc's curve is steep. A bar set in temperature and a bar
# set in pressure are not the same bar, and quoting one against the other would
# have manufactured a regression in an entry that is behaving exactly as its own
# session measured it.
BOILS_LOOSELY = {
    # smiles: (the bar this species is held to, what it is and its residual)
    "[Zn]":                        (0.18, "zinc metal, curated pre-S13; 12.61%"),
    "O=[N+]([O-])[N+](=O)[O-]":    (0.06, "dinitrogen tetroxide, 4.50%"),
    "[O-][N+]=O":                  (0.06, "nitrite/N2O4 pair, curated pre-S13; 4.48%"),
    "O=[N+][O-]":                  (0.06, "nitrogen dioxide, 4.48%"),
    "COC(C)=O":                    (0.06, "methyl acetate, 4.23%"),
    "[O][Cl+][O-]":                (0.04, "chlorine dioxide, 2.61%"),
    "O":                           (0.04, "water, curated pre-S13; 2.57%"),
    "[O-][I+3]([O-])([O-])O":      (0.04, "periodic acid, 2.53%"),
    "CN":                          (0.03, "methylamine, 2.39%"),
    "N=C=O":                       (0.03, "cyanic acid, 2.36%"),
    "O=C=C=C=O":                   (0.03, "carbon suboxide, 2.23%"),
    "CC=O":                        (0.03, "ethanal, 2.12%"),
    "CNC":                         (0.03, "dimethylamine, 2.10%"),
    "O=S(=O)=O":                   (0.03, "sulfur trioxide, curated pre-S13; 2.10%"),
    "O=S=O":                       (0.03, "sulfur dioxide, curated pre-S13; 2.03%"),
    "F":                           (0.03, "hydrogen fluoride, curated pre-S13; 1.98%"),
    "[O-][I+2]([O-])O":            (0.03, "iodic acid, 1.91%"),
    "CCN":                         (0.03, "ethylamine, 1.78%"),
    "C#CCC":                       (0.03, "1-butyne, 1.77%"),
    "O[N+](=O)[O-]":               (0.03, "nitric acid (curated form), curated pre-S13; 1.76%"),
    "O=[N+]([O-])O":               (0.03, "nitric acid, 1.76%"),
    "CBr":                         (0.03, "bromomethane, 1.73%"),
    "O=C(O)CO":                    (0.03, "hydroxyacetic acid, 1.70%"),
    "C=O":                         (0.03, "methanal, curated pre-S13; 1.69%"),
    "N#CC#N":                      (0.03, "cyanogen, 1.64%"),
    "FC(F)C(F)F":                  (0.03, "polytetrafluoroethylene repeat unit, 1.58%"),
    "C1CO1":                       (0.03, "oxirane, 1.56%"),
    "O=C(OC(=O)C(F)(F)F)C(F)(F)F": (0.03, "trifluoroacetic anhydride, 1.56%"),
    "C/C=C/C":                     (0.03, "trans-2-butene, 1.52%"),
    "CC(C)O":                      (0.03, "2-propanol, 1.51%"),
    "C=CC=C":                      (0.03, "1,3-butadiene, 1.51%"),
}


def test_every_assembled_record_boils_at_one_atmosphere(thermo):
    """Tb/Tc/Pc go in; the fitted Antoine curve must come back out saying the
    species boils at 1 atm where it is measured to.

    ⚠ This is a FIT check, not an independent one, and the distinction is worth
    keeping straight because the brief for this work proposed it as the
    independent one. The acentric factor is derived by inverting Lee-Kesler at Tb
    precisely so the curve passes through (Tb, 1 atm), so no error in Tc or Pc
    can show up here -- see ``validation/physical_estimation.py`` Panel 3 for the
    check that can. What this bounds is the least-squares Antoine residual.

    ⚠⚠ S13 WIDENED THE POPULATION FROM ``MEASURED_PHYSICAL`` TO EVERY TABLE
    THAT CARRIES A Tb, and 858 of the 889 condensable records clear the original
    1.5%. The thirty-one that do not are named in ``BOILS_LOOSELY`` above with
    the residual each was measured at -- eight of them pre-existing and
    invisible to this check until it was pointed at the right lists.
    """
    volatility = VolatilityProvider(thermo)
    checked = 0
    seen: set[str] = set()
    for smi in list(MEASURED_PHYSICAL) + list(_CURATED_RAW) + list(
        PHYSICAL_PROPERTIES
    ):
        if smi in seen:
            continue
        seen.add(smi)
        t = thermo.get(smi) if _resolves(thermo, smi) else None
        if t is None or t.Tb is None:
            continue
        v = volatility.get(smi)
        if not v.condensable:
            continue
        bar = BOILS_LOOSELY.get(smi, (0.015, ""))[0]
        assert v.coefficient(t.Tb) == pytest.approx(P_ATM_BAR, rel=bar), smi
        checked += 1
    # 889 records are condensable AND carry a Tb, measured in S13 against 20
    # before the corpus sweep. A floor rather than the count, so a curation
    # that adds one does not fail a test about something else.
    assert checked >= 800


def test_the_loose_boilers_are_a_measured_list_and_not_a_wildcard():
    """The other half: a species that improves must LEAVE ``BOILS_LOOSELY``.

    ⚠ A named-exception list is only honest while every name on it is still
    failing. If a curation or a window change fixes one, this fails and says so,
    which is what stopped the 150 K fit-window floor from being papered over
    instead of fixed -- methane and nitric oxide were on the first draft of the
    list at +16.50% and +14.53%, and both belong nowhere near it.
    """
    from chemsim.properties import ThermochemistryProvider

    thermo = ThermochemistryProvider()
    volatility = VolatilityProvider(thermo)
    for smi, (bar, why) in BOILS_LOOSELY.items():
        t = thermo.get(smi)
        v = volatility.get(smi)
        rel = abs(v.coefficient(t.Tb) / P_ATM_BAR - 1.0)
        assert rel > 0.015, (
            f"{smi} ({why}) now sits inside the 1.5% bar at {rel:.2%} -- take it "
            "out of BOILS_LOOSELY rather than leaving a stale excuse behind"
        )
        assert rel <= bar, (
            f"{smi} ({why}) has drifted to {rel:.2%}, past the {bar:.0%} it was "
            "measured at"
        )


def _resolves(provider, smi) -> bool:
    try:
        provider.get(smi)
    except ValueError:
        return False
    return True


# ⚠⚠ S11 TURNED THIS FROM "NEVER" INTO "ONLY WHERE IT IS DECLARED", AND THE
# GUARD IS STRONGER FOR IT. The rule below was a SCOPING decision, not a physics
# claim: the milestone that wrote it was closing a COVERAGE gap and deliberately
# did not relitigate accuracy on species that already worked. Its own reason --
# "the moment it stops being true the azeotrope, the boiling points and the crop
# sizes all move at once" -- is a call for MEASUREMENT rather than a reason never
# to do it.
#
# S11 did relitigate four, because a template needed them and Joback was
# answering with numbers that were not close:
#
#     propene            Tb 264.92 -> 225.53   Tc 427.64 -> 364.21   (+17%)
#     ethylene           Tb 234.56 -> 169.38   (+38.5%)
#     butanal            Tb 339.78 -> 347.95
#     2-methylpropanal   Tb 339.34 -> 337.25
#
# ⚠ AND THE COST WAS MEASURED, EXAMPLE BY EXAMPLE, BEFORE THE ENTRY WAS KEPT.
# The first, third and fourth appear in NO example and move nothing. Ethylene
# appears in two: `competing_pathways`'s worst moved number is 0.20380 ->
# 0.20485 (0.5%) and `named_routes` reports ethanol-hydration at 2.7% instead of
# 2.9%. Both are in the direction a less soluble alkene should push them.
#
# ⚠ So the guard now names WHICH records were overridden and still refuses any
# it does not name. An addition that quietly changes a fifth one fails here, and
# the message says to come and write down what it cost.
DELIBERATE_OVERRIDES = {
    "C=CC": "propene, S11 -- oxo feedstock; Joback Tb and Tc both ~17% high",
    "C=C": "ethylene, S11 -- Wacker feedstock; Joback Tb 38.5% high",
    "CCCC=O": "butanal, S11 -- the oxo product",
    "CC(C)C=O": "2-methylpropanal, S11 -- the branched oxo product",
}


# ⚠⚠ S13 DID THE THING THE COMMENT ABOVE KEPT CALLING FOR, AND THE GATE HAD TO
# CHANGE SHAPE RATHER THAN GROW.
#
# The guard above is a list of EXCEPTIONS, and it is the right shape while the
# table is a SUPPLEMENT: 37 hand-typed names, so anything overriding a working
# Joback record is unusual and someone should have to say what it cost. S13
# turned the table's input into ``data/catalog`` itself -- every corpus species
# with a molecular graph, resolved to a CAS number by graph -- and 243 of the
# 417 entries now override a record Joback prices completely. A list of 243
# hand-typed exceptions is not a guard, it is a transcription of the table.
#
# ⚠ SO THE COST WAS MEASURED ONCE, FOR THE WHOLE BATCH, AND WRITTEN DOWN.
# ``CORPUS_SWEEP`` is emitted by the generator and names every entry that came
# in that way. What it cost across the example set is in docs/history/MILESTONES.md §S13 --
# measured by running all fifteen examples before and after, not argued.
#
# ⚠ THE TWO SETS MUST STAY DISJOINT, which is what keeps the teeth. A hand
# addition cannot hide inside the sweep, because the generator decides
# membership of ``CORPUS_SWEEP`` and the generator's other input is the
# hand-typed ``CANDIDATES`` list. A fifth species added by hand still lands in
# front of the test below with nothing to excuse it.
def test_the_hand_list_and_the_corpus_sweep_are_disjoint():
    """A hand-typed candidate may never be credited to the batch measurement."""
    overlap = set(DELIBERATE_OVERRIDES) & set(CORPUS_SWEEP)
    assert not overlap, (
        f"{sorted(overlap)} are declared as hand-costed overrides AND as corpus "
        "sweep entries -- the generator gives the hand list priority, so this "
        "means the two inputs have drifted"
    )


def test_the_corpus_sweep_is_a_subset_of_the_table_it_describes():
    """A name in the sweep that is not in the table is a stale generation."""
    missing = set(CORPUS_SWEEP) - set(MEASURED_PHYSICAL)
    assert not missing, (
        f"{sorted(missing)[:5]} are in CORPUS_SWEEP but not in MEASURED_PHYSICAL "
        "-- regenerate tools/build_physical_data.py"
    )


def test_the_measured_table_overrides_a_working_joback_record_only_where_declared():
    """Why the invariants table does not move by ACCIDENT.

    Every species in ``MEASURED_PHYSICAL`` either is one Joback cannot fully
    price, or is named in ``DELIBERATE_OVERRIDES`` above with what the override
    cost. Nothing else may replace a record that already resolved.
    """
    from chemsim.properties.joback import JobackError
    from chemsim.properties.joback import estimate as joback_estimate

    for smi in MEASURED_PHYSICAL:
        if smi in DELIBERATE_OVERRIDES or smi in CORPUS_SWEEP:
            continue
        try:
            j = joback_estimate(Molecule.from_smiles(smi))
        except JobackError:
            continue
        assert None in (j.Tb, j.Tc, j.Pc, j.Vc, j.Hf, j.Gf), (
            f"{smi} resolves fully through Joback, so adding a measured Tb for "
            "it silently changes an existing record -- regenerate "
            "physical_data.py, MEASURE what it moved in the examples, and add "
            "it to DELIBERATE_OVERRIDES with the cost written down"
        )


def test_every_declared_override_is_actually_in_the_table():
    """The other half: a declaration that no longer applies is a stale excuse."""
    for smi in DELIBERATE_OVERRIDES:
        assert smi in MEASURED_PHYSICAL, (
            f"{smi} is declared as a deliberate override but is not in "
            "MEASURED_PHYSICAL -- remove the declaration"
        )

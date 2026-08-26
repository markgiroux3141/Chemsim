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
from chemsim.properties.physical_data import MEASURED_PHYSICAL
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


def test_every_assembled_record_boils_at_one_atmosphere(thermo):
    """Tb/Tc/Pc go in; the fitted Antoine curve must come back out saying the
    species boils at 1 atm where it is measured to. The nine hand-curated
    species were held to 1.4% and these are held to the same bar.

    ⚠ This is a FIT check, not an independent one, and the distinction is worth
    keeping straight because the brief for this work proposed it as the
    independent one. The acentric factor is derived by inverting Lee-Kesler at Tb
    precisely so the curve passes through (Tb, 1 atm), so no error in Tc or Pc
    can show up here -- see ``validation/physical_estimation.py`` Panel 3 for the
    check that can. What this bounds is the least-squares Antoine residual.
    """
    volatility = VolatilityProvider(thermo)
    checked = 0
    for smi in MEASURED_PHYSICAL:
        t = thermo.get(smi) if _resolves(thermo, smi) else None
        if t is None or t.Tb is None:
            continue
        v = volatility.get(smi)
        if not v.condensable:
            continue
        assert v.coefficient(t.Tb) == pytest.approx(P_ATM_BAR, rel=0.015), smi
        checked += 1
    assert checked >= 15


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


def test_the_measured_table_overrides_a_working_joback_record_only_where_declared():
    """Why the invariants table does not move by ACCIDENT.

    Every species in ``MEASURED_PHYSICAL`` either is one Joback cannot fully
    price, or is named in ``DELIBERATE_OVERRIDES`` above with what the override
    cost. Nothing else may replace a record that already resolved.
    """
    from chemsim.properties.joback import JobackError
    from chemsim.properties.joback import estimate as joback_estimate

    for smi in MEASURED_PHYSICAL:
        if smi in DELIBERATE_OVERRIDES:
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

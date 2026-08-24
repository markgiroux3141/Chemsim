"""Layer 1: measured formation data, and the two defects it exists to fix.

The tables themselves are checked at the point they were built (see
``formation_data``'s docstring -- every entry had to satisfy the enthalpy and
Gibbs relations against independently-fitted vapour-pressure correlations).
What is checked HERE is that they are wired in correctly and that the two
failures they were built for are actually gone.
"""

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import standard_state as ss
from chemsim.properties.formation_data import (
    IDEAL_GAS_FORMATION,
    LIQUID_FORMATION,
    PHYSICAL_PROPERTIES,
)
from chemsim.properties.thermochemistry import _CURATED_RAW, ThermochemistryProvider
from chemsim.properties.volatility import VolatilityProvider
from chemsim.reactions import ReactionTemplate, reaction_deltas

FISCHER = ReactionTemplate(
    name="fischer",
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000, reversible=True,
)


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def volatility(thermo):
    return VolatilityProvider(thermo)


# ---------------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------------


def test_the_tables_are_keyed_by_canonical_smiles():
    """A key that is not canonical is a silently dead entry, since every lookup
    canonicalises first."""
    for table in (IDEAL_GAS_FORMATION, LIQUID_FORMATION):
        for smi in table:
            assert Molecule.from_smiles(smi).smiles == smi, smi


def test_the_two_bases_agree_where_they_overlap_with_the_curated_table():
    """Water is in the curated ideal-gas table AND in the measured overlay, from
    different transcriptions. They must not disagree, or which one wins would
    change the answer -- and it is the pH anchor, so it would change it a lot."""
    water = _CURATED_RAW["O"]
    Hf, Gf = IDEAL_GAS_FORMATION["O"]
    assert Hf == pytest.approx(water.Hf, abs=0.1)
    assert Gf == pytest.approx(water.Gf, abs=0.1)


def test_a_fully_curated_entry_still_outranks_the_overlay(thermo):
    """``_CURATED_RAW`` is the top tier. The overlay must not quietly displace
    it, because those entries exist for species where a group estimate is not
    merely imprecise but meaningless (Cl2 at -74.8 kJ/mol, an element)."""
    assert thermo.get("O").source == _CURATED_RAW["O"].source


def test_every_curated_liquid_has_a_volatility_model(volatility):
    """``shift`` consults the volatility model before the curated table, so that
    an ion -- and the ``liquid_standard_state=False`` switch -- can decline the
    whole correction. A curated liquid that came back non-volatile would be
    silently skipped by that ordering, so pin it."""
    refused = [s for s in ss.curated_liquid_species()
               if _resolvable(volatility, s) and not volatility.get(s).volatile]
    assert refused == []


def _resolvable(volatility, smiles):
    try:
        volatility.thermo.get(smiles)
    except Exception:
        return False
    return True


def test_no_curated_liquid_entry_is_inert(volatility):
    """A liquid entry is a shift RELATIVE to the gas basis, so a species with no
    resolvable ideal-gas record cannot use one and its measured data sits inert
    doing nothing. Five entries were in that state -- formic acid, benzaldehyde,
    furfural, DMSO, CS2 -- because Joback cannot fragment any of them and a
    formation entry is only an OVERLAY on his record. ``PHYSICAL_PROPERTIES``
    supplies the missing half. Asserted rather than described because a new
    curated liquid for an unfragmentable species would silently do nothing."""
    inert = {s for s in LIQUID_FORMATION if not _resolvable(volatility, s)}
    assert inert == set()


def test_the_assembled_entries_are_complete_enough_to_use(thermo, volatility):
    """Each assembled species needs formation data AND the physical properties
    the phase model runs on. A half-built record resolves and then fails much
    later, inside the vessel, where the cause is no longer visible."""
    for smi in PHYSICAL_PROPERTIES:
        t = thermo.get(smi)
        assert t.Cp_coeffs is not None and t.Tb and t.Tc and t.Pc, smi
        assert volatility.get(smi).condensable, smi


def test_assembled_volatility_reproduces_the_measured_boiling_point(volatility):
    """The sharpest available check on those records, and an independent one:
    Tb, Tc and Pc go in, and the acentric factor, Lee-Kesler and the Antoine fit
    all have to come back out agreeing that the species boils at 1 atm where it
    is measured to. Nothing in that chain is told the answer."""
    for smi, physical in PHYSICAL_PROPERTIES.items():
        psat = volatility.get(smi).coefficient(physical["Tb"])
        assert psat == pytest.approx(1.01325, rel=0.02), smi


# ---------------------------------------------------------------------------
# defect 1: Joback cannot distinguish homologues
# ---------------------------------------------------------------------------


def _fischer_deltas(thermo, alcohol, ester, liquid):
    net = build_network(
        ["CC(=O)O", alcohol, "O"], [FISCHER], thermo=thermo,
        liquid_standard_state=liquid,
    )
    rxn = next(r for r in net.reactions
               if sorted(r.products) == sorted([ester, "O"]))
    return reaction_deltas(rxn, thermo, net.volatility if liquid else None)


def test_homologues_are_now_distinguishable(thermo):
    """Group contributions are additive, so the CH3 -> C2H5 difference cancels
    EXACTLY between an alcohol and the ester it makes: Joback gave esterifying
    methanol and esterifying ethanol an identical gas-phase dG of -7.35 kJ/mol.
    That is not an accuracy problem -- no downstream correction can recover a
    distinction the estimator never made. Measured data makes it."""
    _, dG_me = _fischer_deltas(thermo, "CO", "COC(C)=O", liquid=False)
    _, dG_et = _fischer_deltas(thermo, "CCO", "CCOC(C)=O", liquid=False)
    assert abs(dG_me - dG_et) > 1.0, f"still identical: {dG_me} vs {dG_et}"


# ---------------------------------------------------------------------------
# defect 2: a carboxylic acid's vapour is not its monomer
# ---------------------------------------------------------------------------


def test_the_acid_shift_no_longer_goes_through_its_vapour_pressure(volatility):
    """Acetic acid vapour is ~95% dimer, so R T ln(Psat) prices a molecule the
    formation data is not about. The measured liquid value and the derived one
    must therefore DISAGREE, and by about the amount the dimerisation is worth
    -- if they agreed, the curated entry would not be doing anything."""
    measured = ss.shift("CC(=O)O", volatility)
    assert "measured" in measured.reason

    derived = _psat_route(volatility, "CC(=O)O")
    assert measured.dGf < derived.dGf - 3.0, (
        f"measured {measured.dGf:.2f} vs derived {derived.dGf:.2f} kJ/mol"
    )


def test_an_ordinary_liquid_agrees_with_the_route_it_replaces(volatility):
    """The counterpart to the test above, and what makes it meaningful. For
    ethanol -- whose vapour is monomeric -- the measured and derived shifts must
    AGREE closely, so the acid's disagreement is a property of the acid rather
    than of curation moving everything it touches."""
    measured = ss.shift("CCO", volatility)
    derived = _psat_route(volatility, "CCO")
    assert measured.dGf == pytest.approx(derived.dGf, abs=1.0)


def _psat_route(volatility, smiles):
    """The R T ln(Psat) shift, bypassing the curated table."""
    saved = dict(ss._CURATED_LIQUID)
    ss._CURATED_LIQUID.clear()
    try:
        return ss.shift(smiles, volatility)
    finally:
        ss._CURATED_LIQUID.update(saved)


def test_esterification_reaction_enthalpy_is_the_measured_one(thermo):
    """Fischer esterification is nearly thermoneutral in the liquid -- all four
    species are stabilised by condensing and the sides very nearly cancel. CRC
    liquid formation data puts it at -3.2 kJ/mol; Joback, on the ideal-gas
    basis it never left, said -18.4. The difference is a factor of 3 in how hot
    an insulated flask gets, which is why it is asserted rather than described."""
    dH, _ = _fischer_deltas(thermo, "CCO", "CCOC(C)=O", liquid=True)
    assert dH == pytest.approx(-3.2, abs=0.3)

"""Competing templates: does side-product formation actually EMERGE?

Until the template library existed, every network this project built had exactly
one template, so purity was ~100% BY CONSTRUCTION and the founding claim that
side products emerge was untested. `spike/spike_reactor.py` demonstrated it in
Phase 0 with hand-written stoichiometry; these tests assert the real code does it
from templates.

The assertions are about ORDERINGS and RESPONSES, not absolute numbers. Absolute
yields depend on the hand-authored pre-exponentials (see ``reactions/library.py``
on how honest each parameter is); the orderings depend on the barriers and the
SMARTS, which are the parts claimed to be chemistry.
"""

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import (
    aerobic_oxidation,
    alcohol_chemistry,
    alkene_dehydration,
    esterification,
    ether_condensation,
    peroxide_over_oxidation,
)
from chemsim.vessel import Vessel

ACOH, ETOH, WATER, O2, N2 = "CC(=O)O", "CCO", "O", "O=O", "N#N"
ESTER, ETHER, ALKENE, ALDEHYDE, PEROXIDE = "CCOC(C)=O", "CCOCC", "C=C", "CC=O", "OO"


@pytest.fixture(scope="module")
def net():
    return build_network(
        [ACOH, ETOH, WATER, O2, N2], alcohol_chemistry(),
        thermo=ThermochemistryProvider(), max_species=200, max_molar_mass=250.0,
    )


def run(net, T, leak=0.0, duration=7200.0):
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=30.0, kla=1.0, k_vent=0.0,
               k_diss=0.0, ingress={O2: leak} if leak else {})
    v.charge({ACOH: 5.0, ETOH: 5.0, WATER: 0.5, N2: 0.02})
    v.run(duration)
    return v.state()


# ---------------------------------------------------------------------------
# every template must balance -- an unbalanced rewrite creates matter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "template,reactants",
    [
        (esterification(), (ACOH, ETOH)),
        (ether_condensation(), (ETOH, ETOH)),
        (alkene_dehydration(), (ETOH,)),
        (aerobic_oxidation(), (ETOH, O2)),
        (peroxide_over_oxidation(), (ALDEHYDE, PEROXIDE)),
    ],
)
def test_every_template_conserves_every_element(template, reactants):
    """`build_network` enforces this, but asserting it per template localises the
    failure to the SMARTS instead of to a network build.

    It is also why the oxidation is written `alcohol + O2 -> carbonyl + H2O2`
    rather than the spike's `alcohol + 1/2 O2 -> carbonyl + H2O`: a graph rewrite
    cannot express half-stoichiometry, and the balanced form turned out to be
    better chemistry because the peroxide then over-oxidises the aldehyde.
    """
    mols = tuple(Molecule.from_smiles(s) for s in reactants)
    outcomes = template.run(mols)
    assert outcomes, f"{template.name} produced nothing from {reactants}"

    lhs: dict[str, int] = {}
    for m in mols:
        for element, n in m.element_counts().items():
            lhs[element] = lhs.get(element, 0) + n
    for products in outcomes:
        rhs: dict[str, int] = {}
        for m in products:
            for element, n in m.element_counts().items():
                rhs[element] = rhs.get(element, 0) + n
        assert rhs == lhs, f"{template.name}: {lhs} -> {rhs}"


# ---------------------------------------------------------------------------
# the network stays bounded, and WHY it does is the useful part
# ---------------------------------------------------------------------------


def test_five_templates_do_not_explode_the_network(net):
    """Adding templates is not what blows up a network; adding a SELF-FEEDING one
    is.

    Polyesterification reached 80 species and 1294 reactions from ONE template,
    because the ester it makes bears another acid and another alcohol, so the
    pattern matches its own product. These five terminate: an ether, an alkene and
    a ketone have no hydroxyl left to attack. Asserting the bound here means a
    future template that quietly regenerates its own group is caught as a jump in
    this number rather than as a slow test.
    """
    assert len(net.species) == 10
    assert len(net.reactions) == 6
    discovered = set(net.species) - {ACOH, ETOH, WATER, O2, N2}
    assert discovered == {ESTER, ETHER, ALKENE, ALDEHYDE, PEROXIDE}


def test_the_reverse_esterification_is_still_derived_not_declared(net):
    """Only the esterification is reversible, and its reverse comes from detailed
    balance. Neither dehydration is reversible: both eliminate water into a large
    excess of it, so declaring them reversible would have detailed balance derive
    a hydration rate for a reaction nobody runs that way."""
    names = {r.name for r in net.reactions}
    # The reverse exists and is a SEPARATE concrete reaction, built by detailed
    # balance rather than declared -- ReactionTemplate has no A_rev/Ea_rev field
    # at all, so there is nowhere to type one.
    assert "fischer_esterification" in names
    assert "fischer_esterification_rev" in names
    for once_only in ("ether_condensation", "alkene_dehydration",
                      "aerobic_oxidation", "peroxide_over_oxidation"):
        assert once_only in names
        assert f"{once_only}_rev" not in names


# ---------------------------------------------------------------------------
# temperature sensitivity -- the spike's first claim
# ---------------------------------------------------------------------------


def test_heat_diverts_the_alcohol_into_dehydration(net):
    """The desired product FALLS as the pot heats, because a competing pathway
    with a higher barrier wakes up and takes the alcohol. Nothing says
    "if too hot, ruin the yield"."""
    cool, hot = run(net, 340.0), run(net, 480.0)
    assert cool.total(ESTER) > 3.0
    assert hot.total(ESTER) < 1.0
    assert hot.total(ETHER) > 10.0 * cool.total(ETHER)


def test_the_purity_ceiling_is_broken(net):
    """THE point of the library. With one template, selectivity was 100% by
    construction -- there was nothing to be impure with. Now it spans a real
    range, and the clean case is clean because conditions are good rather than
    because the model cannot express anything else."""
    def selectivity(st):
        products = {s: st.total(s) for s in (ESTER, ETHER, ALKENE, ALDEHYDE)}
        return products[ESTER] / sum(products.values())

    assert selectivity(run(net, 340.0)) > 0.99
    assert selectivity(run(net, 480.0)) < 0.35


def test_the_ether_route_beats_the_alkene_route_and_that_ordering_collapses(net):
    """The sharpest check that the two dehydration barriers are defensible.

    Ethanol over sulfuric acid gives diethyl ether at ~140 C and ethylene at
    ~180 C, because the alkene route has the higher barrier (160 vs 125 kJ/mol,
    both from their literature bands). So the ether/ethylene ratio must fall
    monotonically as the pot heats. There is no selectivity table anywhere -- it
    is two Arrhenius terms with different barriers diverging.

    Get the barriers the wrong way round and this test fails while the yields
    still look perfectly plausible, which is exactly why it is here.
    """
    ratios = []
    for T in (380.0, 420.0, 450.0, 480.0, 510.0):
        st = run(net, T)
        assert st.total(ALKENE) > 0.0, f"no ethylene at all at {T} K"
        ratios.append(st.total(ETHER) / st.total(ALKENE))

    assert ratios == sorted(ratios, reverse=True), ratios
    assert ratios[0] / ratios[-1] > 100.0, "the ordering barely moved"
    # Ether still dominates throughout the bench range -- ethylene is a
    # high-temperature product, not a co-product.
    assert all(r > 1.0 for r in ratios)


# ---------------------------------------------------------------------------
# contamination sensitivity -- the spike's second claim, plus a cascade
# ---------------------------------------------------------------------------


def test_an_air_leak_makes_an_aldehyde_and_MORE_ACID(net):
    """The cascade is the part nobody wrote.

    Oxidation makes the aldehyde AND hydrogen peroxide; the peroxide
    over-oxidises the aldehyde to acetic acid; that acid re-enters the
    esterification. Three templates, one consequence, and none of them mentions
    the others -- so the acetic acid RISES with the leak even though acetic acid
    is a starting material being consumed by the esterification.
    """
    sealed, leaky = run(net, 360.0), run(net, 360.0, leak=1.0e-4)

    assert sealed.total(ALDEHYDE) == pytest.approx(0.0, abs=1e-9)
    assert leaky.total(ALDEHYDE) > 1e-4                     # the aldehyde appears
    assert leaky.total(PEROXIDE) > 1e-4                     # ... via the peroxide
    assert leaky.total(ACOH) > sealed.total(ACOH) + 0.5     # ... and on to acid
    assert leaky.total(ESTER) < sealed.total(ESTER)         # at the ester's cost


def test_more_air_costs_more_product(net):
    """Monotone in the leak rate, which is what makes "seal the flask" a strategy
    rather than a binary."""
    esters = [run(net, 360.0, leak=q).total(ESTER)
              for q in (0.0, 1.0e-5, 1.0e-4)]
    assert esters == sorted(esters, reverse=True), esters


# ---------------------------------------------------------------------------
# selectivity IS SMARTS specificity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alcohol,expected",
    [
        ("CO", "C=O"),                  # primary   -> formaldehyde
        ("CCO", "CC=O"),                # primary   -> acetaldehyde
        ("CCCO", "CCC=O"),              # primary   -> propanal
        ("CC(C)O", "CC(C)=O"),          # SECONDARY -> a ketone, unasked
    ],
)
def test_one_oxidation_pattern_covers_primary_and_secondary(alcohol, expected):
    """``[CX4;!H0:1][OX2H1:2]`` says only "a carbinol carbon with a hydrogen to
    lose". It never says how many, so ketones arrive without a second template."""
    out = aerobic_oxidation().run(
        (Molecule.from_smiles(alcohol), Molecule.from_smiles(O2))
    )
    assert [p[0].smiles for p in out] == [Molecule.from_smiles(expected).smiles]


def test_a_tertiary_alcohol_refuses_to_oxidise():
    """There is no hydrogen on the carbinol carbon, and you cannot make a carbonyl
    there without breaking a C-C bond. The refusal is the pattern being right, not
    a coverage gap."""
    assert aerobic_oxidation().run(
        (Molecule.from_smiles("CC(C)(C)O"), Molecule.from_smiles(O2))
    ) == []


def test_a_polyol_gives_every_distinct_site_from_one_template():
    """Glycerol has a primary and a secondary carbinol, so one template yields two
    regiochemical products. This is the mechanism that makes a template library
    cheaper than a product list."""
    out = aerobic_oxidation().run(
        (Molecule.from_smiles("OCC(O)CO"), Molecule.from_smiles(O2))
    )
    assert len(out) == 2
    assert {p[0].smiles for p in out} == {
        Molecule.from_smiles("O=CC(O)CO").smiles,       # primary -> aldehyde
        Molecule.from_smiles("O=C(CO)CO").smiles,       # secondary -> ketone
    }


def test_over_oxidation_stops_at_a_ketone():
    """Restricted to an ALDEHYDE, so isopropanol under air stops cleanly at
    acetone while ethanol runs on to acetic acid -- a ketone has no hydrogen on
    the carbonyl carbon to lose. Nobody declared that difference; it is the
    ``[CX3H1:1]=[OX1:2]`` in the pattern."""
    over = peroxide_over_oxidation()
    peroxide = Molecule.from_smiles(PEROXIDE)

    assert over.run((Molecule.from_smiles(ALDEHYDE), peroxide))      # aldehyde: yes
    assert over.run((Molecule.from_smiles("CC(C)=O"), peroxide)) == []   # ketone: no


def test_methanol_cannot_eliminate_to_an_alkene():
    """No beta carbon to eliminate towards. The alkene pattern's ``!H0`` sits on
    the BETA carbon, and putting it on the carbinol carbon instead is a silent
    wrong answer -- ethanol's carbinol carbon has two hydrogens and would match
    happily, but the rewrite is then not an elimination."""
    assert alkene_dehydration().run((Molecule.from_smiles("CO"),)) == []
    assert alkene_dehydration().run((Molecule.from_smiles(ETOH),))

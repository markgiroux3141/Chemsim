"""G5 -- protonation: the ion table's anchor, the sigma row, and the LIMIT.

Three things were built here and the fourth is the finding.

Built: the ion table anchors on the NEUTRAL member of a pair rather than on the
acid, which revived four curated rows that had been producing nothing; a
`ammonio` sigma row, so an anilinium is not priced as an unsubstituted benzene;
and `amine_protonation`, which is the equilibrium the old `ammonium_dissociation`
carried, written in the direction forward-only discovery can find.

The finding: **a species split does not fix aniline, and the reason is not the
split.** The tests at the bottom assert the LIMIT rather than the fix, so a
session that removes it sees them fail rather than having to notice.
"""

from __future__ import annotations

import math

import pytest
from rdkit import Chem

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import (
    ThermochemistryProvider,
    dissociation_templates,
    electrolyte,
    electrolyte_provider,
)
from chemsim.reactions import hammett
from chemsim.reactions.synthesis import NITRATION_RHO, aromatic_nitration, n_acylation
from chemsim.vessel import Vessel


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


ANILINE, ANILINIUM = c("Nc1ccccc1"), c("[NH3+]c1ccccc1")
ACETANILIDE, ANHYDRIDE = c("CC(=O)Nc1ccccc1"), c("CC(=O)OC(C)=O")
BENZENE, NITRIC, SULFURIC = c("c1ccccc1"), c("O[N+](=O)[O-]"), c("OS(=O)(=O)O")
WATER, HYD = c("O"), c("[OH3+]")
PKA_ANILINIUM = 4.62
DECLARED_EA = 60_000.0


@pytest.fixture(scope="module")
def ions():
    return electrolyte.ion_thermochemistry(ThermochemistryProvider())


@pytest.fixture(scope="module")
def electro():
    return electrolyte_provider()


# ---------------------------------------------------------------------------
# 1. the anchor direction
# ---------------------------------------------------------------------------
def test_every_cation_neutral_pair_is_priced_and_they_used_not_to_be(ions):
    """The four rows the acid-anchored form silently dropped.

    ⚠ THE OLD FAILURE WAS SILENT, which is the whole reason this test is worth
    having. `anchored(pair.acid)` refuses a charge -- correctly, Joback and
    Benson are fitted to neutral molecules -- and a bare `except Exception:
    continue` turned four curated pKa values into nothing at all.
    """
    cationic = [p for p in electrolyte.known_pairs()
                if Molecule.from_smiles(p.acid).charge > 0]
    assert len(cationic) == 4
    assert {p.name for p in cationic} == {
        "ammonium", "methylammonium", "pyridinium", "anilinium",
    }
    for pair in cationic:
        key = Molecule.from_smiles(pair.acid).smiles
        assert key in ions, f"{pair.name} still unpriced"
        assert "pKa" in ions[key].source


def test_the_only_cations_in_the_table_are_the_four_plus_the_hydronium(ions):
    """⚠ THE COUNTS ARE PINNED, AND A FAILURE HERE IS A PROMPT AND NOT A BUG.

    Adding a pair to `_PAIRS` moves both numbers, and it should: 24 -> 28 is the
    whole measured result of the anchor fix, and eleven corpus species moved out
    of `refused` on the back of it. If this test fails because the table grew,
    re-measure `validation/catalog_coverage.py` and update BOTH numbers with the
    new refusal count in the commit message.

    ⚠⚠ **C2 GREW IT AGAIN, 28 -> 29, AND THE PROMPT WORKED EXACTLY AS
    WRITTEN.** The new row is phosphoric acid's THIRD dissociation, so the
    addition is an ANION and the cation list above is unchanged -- which is the
    reason both halves are asserted separately. Re-measured as instructed:
    corpus refusals went **419 -> 416** and species-ready **83 -> 85**, and
    `phosphoric-wet` and `superphosphate` became playable on it. See
    `tests/test_phosphate.py` and MILESTONES §C2.
    """
    got = sorted(k for k in ions if Molecule.from_smiles(k).charge > 0)
    assert got == ["C[NH3+]", "[NH3+]c1ccccc1", "[NH4+]", "[OH3+]",
                   "c1cc[nH+]cc1"]
    # ⚠⚠ C5 GREW IT AGAIN, 29 -> 30, AND THE PROMPT WORKED A SECOND
    # TIME. The new row is salicylic acid's SECOND dissociation -- the
    # PHENOL proton, pKa 13.4 -- so the addition is an ANION again and the
    # cation list above is unchanged. ⚠ It was EXPOSED rather than
    # missed: nothing could reach the mono-anion with a template until C5
    # fixed `ReactionTemplate.run`. See `tests/test_furans.py`.
    assert len(ions) == 30


def test_an_anion_is_still_anchored_on_its_acid_bit_for_bit(ions):
    """⚠ BIT FOR BIT, and the grouping of the sum is part of the claim.

    Folding the pKa term and the solvent correction into one `dG_diss` before
    adding moved TEN of the 24 anions in the last bit -- floating-point addition
    is not associative. A data table that shifts by 1e-16 owes
    `tolerance_audit.py` a ten-minute run to prove it did not matter, so the
    cheaper thing is not to shift it.
    """
    base = ThermochemistryProvider()
    acid = electrolyte.AcidPair("CC(=O)O", "CC(=O)[O-]", 4.76, "acetic acid",
                                dH_diss=-0.4)
    anchor = base.get(c(acid.acid))
    from chemsim.properties import standard_state
    from chemsim.properties.volatility import VolatilityProvider

    vol = VolatilityProvider(base)
    shift = standard_state.shift(acid.acid, vol, electrolyte.T_REF)
    Hf, Gf = anchor.Hf + shift.dHf, anchor.Gf + shift.dGf
    expected = (Gf + electrolyte._dG_from_pKa(acid.pKa)
                + electrolyte._solvent_correction(1))
    got = ions[c(acid.base)]
    assert got.Gf == expected
    assert got.Hf == Hf + acid.dH_diss


def test_the_reversed_arithmetic_round_trips_to_the_declared_pKa(ions):
    """A cation priced backwards must give the pKa back.

    Not bit-identical -- `(x - a - b) + a + b` is not `x` -- but the pKa it
    implies has to be the pKa it was derived from, and that is the claim.
    """
    base = ThermochemistryProvider()
    from chemsim.properties import standard_state
    from chemsim.properties.volatility import VolatilityProvider

    vol = VolatilityProvider(base)
    anil = base.get(ANILINE)
    s = standard_state.shift(ANILINE, vol, electrolyte.T_REF)
    Gf_base = anil.Gf + s.dGf
    dG = ions[ANILINIUM].Gf - Gf_base + electrolyte._solvent_correction(1)
    pka = -dG * 1000.0 / (electrolyte.LN10 * electrolyte.R * electrolyte.T_REF)
    assert pka == pytest.approx(PKA_ANILINIUM, abs=1e-9)


# ---------------------------------------------------------------------------
# 2. the template, and the pattern bug it replaces
# ---------------------------------------------------------------------------
def test_the_old_pattern_could_not_deprotonate_an_ammonium():
    """⚠ THE REGRESSION GUARD FOR A BUG THAT SHIPPED FOR TWELVE SESSIONS.

    `ammonium_dissociation` was written on `[NX4H+]`, and a bare `H` in SMARTS
    means EXACTLY ONE hydrogen. So the template named for the ammonium ion
    matched a protonated TERTIARY amine and nothing else. No example caught it
    because nothing in the corpus can put a trialkylammonium in a flask.
    """
    old = Chem.MolFromSmarts("[NX4H+]")
    for smi in ("[NH4+]", "[NH3+]c1ccccc1", "C[NH3+]", "CC[NH2+]C",
                "c1cc[nH+]cc1"):
        assert not Chem.MolFromSmiles(smi).HasSubstructMatch(old), smi
    assert Chem.MolFromSmiles("C[NH+](C)C").HasSubstructMatch(old)


def test_amine_protonation_is_in_the_bundle_and_the_old_name_is_gone():
    names = {t.name for t in dissociation_templates()}
    assert "amine_protonation" in names
    assert "ammonium_dissociation" not in names
    tmpl = next(t for t in dissociation_templates()
                if t.name == "amine_protonation")
    assert tmpl.reversible, "the deprotonation must still be in the network"


@pytest.mark.parametrize("smiles,expected", [
    ("Nc1ccccc1", "[NH3+]c1ccccc1"),        # an aryl amine
    ("N", "[NH4+]"),                        # ammonia
    ("CN", "C[NH3+]"),                      # an alkyl amine
    ("Nc1ccc(O)cc1", "[NH3+]c1ccc(O)cc1"),  # 4-aminophenol
])
def test_what_amine_protonation_protonates(smiles, expected):
    tmpl = next(t for t in dissociation_templates()
                if t.name == "amine_protonation")
    got = tmpl.run((Molecule.from_smiles(smiles), Molecule.from_smiles(HYD)))
    products = {p.smiles for prods in got for p in prods}
    assert c(expected) in products
    assert WATER in products, "the water must come back NEUTRAL"


@pytest.mark.parametrize("smiles", [
    "CC(=O)Nc1ccccc1",       # an amide: a different pair, pKa near zero
    "O=[N+]([O-])c1ccccc1",  # a nitro group: already charged
    "c1ccncc1",              # ⚠ a pyridine: an aromatic ring N is X2, not X3
    "CC#N",                  # a nitrile
    "CCO",                   # an alcohol
])
def test_what_amine_protonation_leaves_alone(smiles):
    tmpl = next(t for t in dissociation_templates()
                if t.name == "amine_protonation")
    got = tmpl.run((Molecule.from_smiles(smiles), Molecule.from_smiles(HYD)))
    # ⚠ NO ESCAPE CLAUSE. The first draft allowed "or the products are the
    # reactants", which is true of nothing here and would have made the test
    # pass whatever the pattern did. Measured: every one of these returns [].
    assert got == [], f"{smiles} should not protonate here"


# ---------------------------------------------------------------------------
# 3. the sigma row
# ---------------------------------------------------------------------------
def test_the_ammonio_row_is_a_labelled_proxy_and_is_meta_directing():
    row = next(s for s in hammett._TABLE if s.label == "ammonio")
    assert row.source == hammett.SIGMA_PROXY
    assert row.meta_directing
    assert row.sigma_m == 0.86
    assert row.sigma_p == 0.60
    assert row.sigma == 0.86


def test_the_ammonio_row_is_the_one_whose_two_constants_invert():
    """⚠ AND IT IS THE SECOND REASON `meta_directing` IS DECLARED.

    Every other meta-directing group has sigma_meta < sigma_para, so
    `meta_directing` picks the SMALLER; -NH3+ has 0.86 / 0.60 and it picks the
    LARGER. A rule of "meta-directing iff sigma_para > sigma_meta" would call an
    anilinium an ortho/para director. The halogens are the first reason and they
    fail the rule the other way.
    """
    inverted = [s for s in hammett._TABLE
                if s.meta_directing and s.sigma_m > s.sigma_p]
    assert [s.label for s in inverted] == ["ammonio"]
    halogens = [s for s in hammett._TABLE if s.label in
                ("fluoro", "chloro", "bromo", "iodo")]
    assert len(halogens) == 4
    assert all(not s.meta_directing and s.sigma_m > 0.0 for s in halogens)


def test_an_anilinium_is_surveyed_and_used_to_come_back_unknown():
    """It read `sum(sigma) = 0.0` with an `unknown` notice, i.e. it was priced
    as an UNSUBSTITUTED BENZENE -- which is a smaller error than the free
    base's and still the wrong direction."""
    s = hammett.survey(Molecule.from_smiles(ANILINIUM)._mol)
    assert s.found == ("ammonio",)
    assert s.unknown == ()
    assert s.sigma_sum == 0.86


def test_a_quaternary_aryl_ammonium_is_reported_and_not_guessed():
    """The aspirin-acyloxy precedent. No sigma is sourced for -N(CH3)3+ here, so
    it must land in `unknown` rather than borrow the anilinium's."""
    s = hammett.survey(Molecule.from_smiles("C[N+](C)(C)c1ccccc1")._mol)
    assert s.found == ()
    assert s.unknown == ("-N on an aromatic carbon",)


def test_the_barrier_ladder_puts_the_anilinium_below_benzene():
    """⚠ THE DIRECTION IS THE POINT. The anilinium has to be SLOWER than
    benzene and the two neutral amines FASTER.

    ⚠⚠ AND G6 COLLAPSED THE TOP TWO RUNGS INTO ONE, WHICH IS NOT A REGRESSION.
    An aniline asks the line for 8.45 decades and an acetanilide for 3.90, and
    the encounter plateau is at 2.686 -- so both are above it and both are priced
    AT it. That is what saturation means: once a ring reacts on every encounter,
    activating it further buys no rate. ⚠ It is also why "protect the amine"
    still works and now works for the right reason -- an amide cannot be
    PROTONATED, rather than being intrinsically slower. The strict ladder is
    asserted with the plateau lifted.
    """
    def Ea(smi, saturation=hammett.SATURATION_DECADES):
        s = hammett.survey(Molecule.from_smiles(smi)._mol)
        return hammett.clamp_barrier(
            DECLARED_EA
            + hammett.barrier_shift(NITRATION_RHO, s.sigma_sum, saturation)
        )

    assert Ea(ANILINE) == Ea(ACETANILIDE) < Ea(BENZENE) < Ea(ANILINIUM)
    assert Ea(ANILINE, math.inf) < Ea(ACETANILIDE, math.inf) < Ea(BENZENE)
    assert Ea(BENZENE) == DECLARED_EA
    ratio = hammett.rate_ratio(NITRATION_RHO, 0.86)
    assert ratio < 1.0
    assert ratio == pytest.approx(10.0 ** (NITRATION_RHO * 0.86), rel=1e-12)


# ---------------------------------------------------------------------------
# 4. the equilibrium, in a running pot
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def protonation_net(electro):
    return build_network([ANILINE, NITRIC, SULFURIC, WATER],
                         dissociation_templates(), thermo=electro,
                         max_species=40)


def _equilibrate(net, charge, volume=2.0, seconds=100.0):
    v = Vessel(net, volume=volume, T=298.15, T_env=298.15, UA=1.0e6, kla=0.0,
               k_vent=0.0, k_diss=0.0, lle=False)
    v.charge(charge)
    v.run(seconds)
    return v


def test_an_aniline_in_dilute_acid_reads_back_its_own_pKa(protonation_net):
    v = _equilibrate(protonation_net,
                     {ANILINE: 1.0, NITRIC: 1.0, WATER: 30.0})
    conc = v.concentrations(v.aqueous_layer())
    b, bh, h = conc[ANILINE], conc[ANILINIUM], conc[HYD]
    assert b > 0.0 and bh > 0.0 and h > 0.0
    assert math.log10(bh / (b * h)) == pytest.approx(PKA_ANILINIUM, abs=0.25)


def test_an_aniline_in_mixed_acid_is_essentially_all_anilinium(protonation_net):
    v = _equilibrate(protonation_net,
                     {ANILINE: 1.0, NITRIC: 3.5, SULFURIC: 3.5, WATER: 30.0})
    conc = v.concentrations(v.aqueous_layer())
    frac = conc[ANILINIUM] / (conc[ANILINE] + conc[ANILINIUM])
    assert frac > 0.99999
    assert v.pH < 0.0


def test_the_protonation_network_conserves_matter(protonation_net):
    v = _equilibrate(protonation_net,
                     {ANILINE: 1.0, NITRIC: 3.5, SULFURIC: 3.5, WATER: 30.0})
    report = v.conservation_report()
    assert "FAIL" not in report, report


# ---------------------------------------------------------------------------
# 5. THE LIMIT -- asserted, so that removing it BREAKS a test
# ---------------------------------------------------------------------------
def test_the_crossover_acidity_is_still_below_what_the_engine_can_reach(
    electro,
):
    """⚠⚠ THE LIMIT, ASSERTED -- AND G6 MOVED IT BY FIVE DECADES, WHICH IS WHY
    THIS TEST NOW ASSERTS TWO NUMBERS INSTEAD OF ONE.

    G5 measured the crossover at pH -9.42 and reported that it lands inside the
    H0 band of the 90-98% sulfuric acid real aniline nitration is run in,
    reading that as the engine's own arithmetic finding the right answer
    unprompted. ⚠⚠ THAT AGREEMENT WAS A PROPERTY OF THE 8.45-DECADE
    EXTRAPOLATION, which G6 replaced with a sourced encounter plateau: the
    crossover is now -3.66. The bare line's -9.42 is kept below as what the
    unsaturated model said, and what survives is the half that never depended on
    the number -- the pot cannot reach either one.

    THE ORIGINAL FINDING, KEPT BECAUSE THE MEASUREMENT THAT MOVED IT ONLY MEANS
    SOMETHING AGAINST IT: real aniline gives largely meta product only in 90-98%
    sulfuric acid, whose H0 falls to roughly -8 at 90 wt% and roughly -10 at 98
    wt%. ⚠ That band is quoted to ONE FIGURE because it is recalled rather than
    sourced here.

    The two channels cross at pH -9.42 -- which is not a wrong number: real
    aniline gives largely meta product only in 90-98% sulfuric acid, whose
    Hammett acidity function H0 falls to roughly -8 at 90 wt% and roughly -10 at
    98 wt%. ⚠ The band is quoted to ONE FIGURE because it is recalled rather than
    sourced here: the claim is that -9.42 lands INSIDE it, not that it matches a
    tabulated value. The assertion below is on the ENGINE's number, not on H0. What it cannot do is GET there,
    because its only handle on acidity is a mass-action molarity and H0 is not
    the concentration of anything.

    ⚠ When somebody gives this engine an acidity function, this test fails. That
    is the intent.
    """
    def crossover(saturation=hammett.SATURATION_DECADES):
        k_free = hammett.rate_ratio(
            NITRATION_RHO,
            hammett.survey(Molecule.from_smiles(ANILINE)._mol).sigma_sum,
            saturation=saturation,
        )
        k_ion = hammett.rate_ratio(
            NITRATION_RHO,
            hammett.survey(Molecule.from_smiles(ANILINIUM)._mol).sigma_sum,
            saturation=saturation,
        )
        return -math.log10(10.0 ** (-PKA_ANILINIUM) * k_free / k_ion)

    pH_cross = crossover()
    assert pH_cross == pytest.approx(-3.66, abs=0.05)
    assert crossover(math.inf) == pytest.approx(-9.42, abs=0.05), (
        "G5's number, kept: the encounter plateau is what moved it"
    )

    net = build_network([NITRIC, SULFURIC, WATER], dissociation_templates(),
                        thermo=electro, max_species=40)
    best = min(_equilibrate(net, {NITRIC: 5.0, SULFURIC: 5.0, WATER: w}).pH
               for w in (40.0, 30.0, 20.0))
    assert -1.0 < best < 0.0
    assert best - pH_cross > 2.5, "the wall has moved -- re-measure the finding"


def test_a_drier_acid_is_a_less_acidic_pot(electro):
    """⚠ NOT A SOLVER ARTEFACT. Every dissociation here is written with water on
    BOTH sides, so [H2O] is a mass-action factor and running out of water
    suppresses the reaction that makes the proton. Real: dry sulfuric acid is
    not a source of hydronium."""
    net = build_network([NITRIC, SULFURIC, WATER], dissociation_templates(),
                        thermo=electro, max_species=40)
    wet = _equilibrate(net, {NITRIC: 5.0, SULFURIC: 5.0, WATER: 30.0})
    dry = _equilibrate(net, {NITRIC: 5.0, SULFURIC: 5.0, WATER: 2.0})
    assert wet.pH < dry.pH - 4.0


def test_the_split_moves_six_decades_and_the_plateau_closes_the_rest(
    protonation_net,
):
    """⚠⚠ THE TWO HALVES TOGETHER, AND THIS IS WHERE G6 IS VISIBLE.

    G5 took aniline from 2.8e8 times benzene to a few hundred times benzene and
    measured that the remaining eight decades were NOT in the protonation model:
    they were `sigma+ = -1.30` priced 8.45 decades off a line fitted on
    |rho*sigma| < 2.6. ⚠ G6 prices that free base at the sourced encounter
    plateau instead, and the effective rate crosses ONE -- aniline in the most
    acidic flask this engine can reach is now SLOWER than benzene, which is the
    observable. The bare-line value is asserted beside it, because the claim is
    about the difference between the two.
    """
    v = _equilibrate(protonation_net,
                     {ANILINE: 1.0, NITRIC: 5.0, SULFURIC: 5.0, WATER: 30.0})
    conc = v.concentrations(v.aqueous_layer())
    frac = conc[ANILINIUM] / (conc[ANILINE] + conc[ANILINIUM])
    # ⚠ THE SIGMA SUMS COME OUT OF `survey`, NOT OUT OF LITERALS. The first
    # draft hard-coded -1.30 and 0.86, and deleting the `ammonio` row from the
    # table left this test passing while three others failed -- a claim about
    # the engine has to be measured against the engine.
    k_free = hammett.rate_ratio(
        NITRATION_RHO, hammett.survey(Molecule.from_smiles(ANILINE)._mol).sigma_sum
    )
    k_ion = hammett.rate_ratio(
        NITRATION_RHO, hammett.survey(Molecule.from_smiles(ANILINIUM)._mol).sigma_sum
    )
    eff = (1.0 - frac) * k_free + frac * k_ion
    assert eff < 1.0, "aniline has to end up SLOWER than benzene"
    assert 1e-4 < eff < 1e-2, eff

    # ⚠ G5's OWN NUMBER, RE-MEASURED HERE RATHER THAN QUOTED, so that the size
    # of what the plateau moved is asserted and not just its direction.
    bare_free = hammett.rate_ratio(
        NITRATION_RHO,
        hammett.survey(Molecule.from_smiles(ANILINE)._mol).sigma_sum,
        saturation=math.inf,
    )
    bare = (1.0 - frac) * bare_free + frac * k_ion
    assert bare > 1e2
    assert math.log10(bare / eff) > 5.0, "at least five decades of the eight"

    # The ion channel matters more than it did only because the free-base
    # channel shrank; it is still not the reaction.
    carried_by_ion = frac * k_ion / eff
    assert carried_by_ion < 1e-2


def test_a_protonation_template_over_a_curated_ion_table_refuses(electro):
    """⚠ AN OPEN-ENDED REWRITE OVER A CURATED LIST, and the refusal is KEPT.

    Nitrate an aniline and the second generation is a nitroanilinium nobody
    curated. Panel 5 of `validation/protonation.py` measures what those nine
    pKa values would buy -- nothing, because the ion channel carries 1e-7% of
    the rate -- so a refusal naming the missing datum beats a number wrong by
    three decades. The element floor's rule, applied to a pKa.
    """
    with pytest.raises(ValueError, match="net charge"):
        build_network([ANILINE, NITRIC, WATER],
                      [aromatic_nitration(), *dissociation_templates()],
                      thermo=electro, max_species=60, max_molar_mass=250.0)


def test_the_pyridinium_is_priced_and_still_unreachable(ions):
    """The same mismatch from the other end, and it is named rather than fixed:
    an aromatic ring nitrogen is X2, so `amine_protonation` cannot make the ion
    whose pKa the table now carries. Closing it lands on the Skraup."""
    assert c("c1ccc[nH+]c1") in ions
    tmpl = next(t for t in dissociation_templates()
                if t.name == "amine_protonation")
    got = tmpl.run((Molecule.from_smiles("c1ccncc1"),
                    Molecule.from_smiles(HYD)))
    assert got == []


# ---------------------------------------------------------------------------
# 6. what the engine CAN do instead
# ---------------------------------------------------------------------------
def test_protecting_the_amine_is_emergent_and_runs(electro):
    """⚠ NOBODY TOLD THE ENGINE THAT AN AMIDE IS A PROTECTING GROUP.

    Two pieces of already-declared data do it: `acylamino`'s sigma+ of -0.600
    against `amino`'s -1.30, and an amide that does not answer
    `amine_protonation`'s pattern. So the acetanilide network BUILDS where the
    aniline one refuses, which is the 1800s dye and analgesic sequence and its
    real reason.
    """
    net1 = build_network([ANILINE, ANHYDRIDE, WATER], [n_acylation()],
                         thermo=electro, max_species=30, max_molar_mass=260.0)
    v = Vessel(net1, volume=1.0, T=330.0, T_env=330.0, UA=1.0e6, kla=0.0,
               k_vent=0.0, k_diss=0.0, lle=False)
    v.charge({ANILINE: 1.0, ANHYDRIDE: 1.2, WATER: 10.0})
    v.run(1800.0)
    st = v.state()
    assert st.liquid_total(ACETANILIDE) > 0.99
    assert st.liquid_total(ANILINE) < 1e-4

    net2 = build_network([ACETANILIDE, NITRIC, WATER],
                        [aromatic_nitration(), *dissociation_templates()],
                        thermo=electro, max_species=60, max_molar_mass=300.0)
    v = Vessel(net2, volume=1.0, T=300.0, T_env=300.0, UA=1.0e6, kla=0.0,
               k_vent=0.0, k_diss=0.0, lle=False)
    v.charge({ACETANILIDE: 1.0, NITRIC: 1.5, WATER: 20.0})
    v.run(600.0)
    st = v.state()
    amides = [s for s in net2.species if "CC(=O)N" in s]
    mono = sum(st.liquid_total(s) for s in amides
               if s.count("[N+](=O)[O-]") == 1)
    assert mono > 0.4, "the acetanilide should nitrate"

    # ⚠ AND THE ISOMER RATIO IS STILL FLAT -- G2's other named limit, asserted
    # here so that closing it breaks a test rather than going unnoticed.
    ortho = st.liquid_total(c("CC(=O)Nc1ccccc1[N+](=O)[O-]"))
    meta = st.liquid_total(c("CC(=O)Nc1cccc([N+](=O)[O-])c1"))
    assert ortho == pytest.approx(meta, rel=1e-6)

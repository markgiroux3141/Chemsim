"""C3 -- vanillin, and the class S11 refused after reading one of its two rows.

`oxidative-cleavage` was attempted in S11 and REFUSED, with the reason recorded
in MILESTONES §S11 §12 and printed by `validation/corpus_balance.py`: the row it
was attempted off, `vanillin-lignin` step 1, destroys two carbons, and naming the
missing C2 fragment would be inventing chemistry inside the corpus.

⚠⚠ **THE CLASS HAS A SECOND ROW AND IT WAS NOT READ.** `vanillin-eugenol` step 2
balances exactly 1:1 and names its C2 fragment. So the class is built off that
one, and the fragment the lignin row omits turns out to be `glycolaldehyde` --
already a corpus compound. Nothing is invented; S11's reason survives exactly
where it was aimed. **C1: a route blocked on a price for a species not in its
chemistry. C2: a route blocked on a price in a different table. C3: a class
refused on the evidence of one of its rows.**

⚠⚠⚠ AND ``test_the_equilibrium_is_exact_on_the_LIQUID_and_not_on_the_inventory``
IS THE FILE'S SHARPEST TEST. C3's first flask read an isoeugenol:eugenol ratio of
15362 against a ``kf/kb`` of 2678 and that 5.7x was nearly written down as
chemistry. It is the HEADSPACE. A rate law is written on one phase; read the
equilibrium on that phase or not at all.

⚠ Every flask here runs at **rtol 1e-8**, and the reference charge is an
AUTOCLAVE -- 0.73 L of alkaline liquor at 470 K under ~30 bar of its own steam,
which is what an alkaline oxidation digester is. A yield without its conditions
is not a number.
"""

from __future__ import annotations

import math
import os
import sys

import pytest

# ⚠ THE COVERAGE AND PLAYABILITY TESTS AT THE BOTTOM READ THE REAL GENERATORS
# RATHER THAN RE-IMPLEMENTING THE SCORER -- G3 spent a commit removing a second
# copy of it. ``build_playable`` runs the deep chain at import, which is ~50 s of
# the user's CPU, paid once for this module.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("src", "tools", "validation"):
    _full = os.path.join(_ROOT, _p)
    if _full not in sys.path:
        sys.path.insert(0, _full)

from chemsim.constants import R  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import VolatilityProvider  # noqa: E402
from chemsim.properties.electrolyte import (  # noqa: E402
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions.synthesis import (  # noqa: E402
    alkene_isomerisation,
    oxidative_cleavage,
    vanillin_chemistry,
)
from chemsim.reactions.thermo import reaction_deltas  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402


def _c(smi: str) -> str:
    """⚠ CANONICALISE EVERY SMILES CONSTANT. ``state().total()`` is keyed by the
    network's own species strings, so the corpus's ``OCC=O`` for glycolaldehyde
    reads ZERO against the network's ``O=CCO`` -- S6's raw-vs-canonical finding,
    which cost `validation/vanillin.py` a panel that printed a 1:1 product as
    0.000000 with nothing raising."""
    return Molecule.from_smiles(smi).smiles


WATER, O2, NA, OH = _c("O"), _c("O=O"), _c("[Na+]"), _c("[OH-]")
EUGENOL = _c("C=CCc1ccc(O)c(OC)c1")
ISO = _c("CC=Cc1ccc(O)c(OC)c1")            # what the template makes
TRANS_ISO = _c("C/C=C/c1ccc(O)c(OC)c1")    # what the corpus spells
CIS_ISO = _c(r"C/C=C\c1ccc(O)c(OC)c1")
VANILLIN, MECHO = _c("COc1cc(C=O)ccc1O"), _c("CC=O")
CONIFERYL, GLYCOL = _c("COc1cc(/C=C/CO)ccc1O"), _c("OCC=O")

TIGHT = {"rtol": 1.0e-8, "atol": 1.0e-11}
VESSEL, WATER_CHARGE, SUBSTRATE, BASE, OXYGEN = 2.0, 40.0, 0.10, 0.10, 0.5


@pytest.fixture(scope="module")
def vol():
    return VolatilityProvider()


@pytest.fixture(scope="module")
def thermo(vol):
    return electrolyte_provider(volatility=vol)


def _net(thermo, vol, species, templates):
    return build_network(species, list(templates), thermo=thermo, volatility=vol)


@pytest.fixture(scope="module")
def net(thermo, vol):
    return _net(thermo, vol, [WATER, EUGENOL, O2, NA, OH], vanillin_chemistry())


@pytest.fixture(scope="module")
def net_isom(thermo, vol):
    return _net(thermo, vol, [WATER, EUGENOL, NA, OH], [alkene_isomerisation()])


@pytest.fixture(scope="module")
def net_cleave(thermo, vol):
    return _net(thermo, vol, [WATER, ISO, O2, NA, OH], [oxidative_cleavage()])


def _flask(network, *, T=470.0, t=3600.0, sub=EUGENOL, oh=BASE, o2=OXYGEN,
           water=WATER_CHARGE, n=SUBSTRATE):
    v = Vessel(network, volume=VESSEL, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    liquid = {WATER: water, sub: n}
    if oh:
        liquid |= {NA: oh, OH: oh}
    v.charge(liquid, phase="liquid")
    if o2:
        v.charge({O2: o2}, phase="gas")
    v.run(t, **TIGHT)
    return v


def _counts(*smiles):
    out: dict[str, int] = {}
    for s in smiles:
        for el, c in Molecule.from_smiles(s).element_counts().items():
            out[el] = out.get(el, 0) + c
    return out


# ---------------------------------------------------------------------------
# 1. THE REFUSAL, AND WHY IT WAS ABOUT A ROW RATHER THAN A CLASS
# ---------------------------------------------------------------------------
def test_the_class_has_two_rows_and_only_one_of_them_balances():
    """S11 read the one that does not.

    ⚠ THIS IS THE WHOLE ARGUMENT FOR BUILDING THE CLASS, in three lines of
    arithmetic. The refusal is kept where it was aimed -- the lignin row IS
    wrong -- and the class is built off its neighbour.
    """
    eugenol_row = (_counts(TRANS_ISO, O2), _counts(VANILLIN, MECHO))
    lignin_row = (_counts(CONIFERYL, O2), _counts(VANILLIN, WATER))
    mechanism = (_counts(CONIFERYL, O2), _counts(VANILLIN, GLYCOL))

    assert eugenol_row[0] == eugenol_row[1], "vanillin-eugenol 2 balances 1:1"
    assert lignin_row[0] != lignin_row[1], "vanillin-lignin 1 does not"
    assert mechanism[0] == mechanism[1], "and the mechanism's product balances"

    # the exact shortfall S11 named: two carbons and four hydrogens
    assert lignin_row[0]["C"] - lignin_row[1]["C"] == 2
    assert lignin_row[0]["H"] - lignin_row[1]["H"] == 2


def test_the_fragment_the_lignin_row_omits_was_already_a_corpus_compound():
    """⚠⚠ S11's reason was that naming it would be *inventing chemistry inside
    the corpus*. It needs no inventing: `glycolaldehyde | OCC=O` has been in
    `data/catalog/compounds/07-carbonyls.psv` all along, as 'simplest sugar'.

    **The mechanism supplies the fragment and the corpus supplies its name.**
    """
    import os

    import catalog as cat

    rows = open(
        os.path.join(cat.CATALOG_DIR, "compounds", "07-carbonyls.psv"),
        encoding="utf-8",
    ).read()
    assert "glycolaldehyde" in rows
    line = next(x for x in rows.splitlines() if x.startswith("glycolaldehyde "))
    assert _c(line.split("|")[2].strip()) == GLYCOL


def test_pricing_the_unbalanced_row_is_SILENT(thermo):
    """⚠⚠ A row that is not a reaction still comes back with a number, and its
    entropy is the tell: +148 J/K against its balanced neighbour's +17, because
    two carbons have been destroyed on the right. **Nothing raises.**

    That is what `corpus_balance`'s own last panel means by its test being weak,
    measured from the downstream side for the first time.
    """
    def dS(left, right):
        dH = (sum(thermo.get(s).Hf for s in right)
              - sum(thermo.get(s).Hf for s in left))
        dG = (sum(thermo.get(s).Gf for s in right)
              - sum(thermo.get(s).Gf for s in left))
        return (dH - dG) / 298.15 * 1000.0

    good = dS((CONIFERYL, O2), (VANILLIN, GLYCOL))
    bad = dS((CONIFERYL, O2), (VANILLIN, WATER))
    assert good == pytest.approx(16.97, abs=0.05)
    assert bad == pytest.approx(148.23, abs=0.05)
    assert bad / good > 8.0


# ---------------------------------------------------------------------------
# 2. THE TWO SMARTS, AND WHAT EACH ONE DELIBERATELY REFUSES
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("substrate", "fires"),
    [
        ("C=CCc1ccc(O)c(OC)c1", True),     # eugenol
        ("C=CCc1ccc2OCOc2c1", True),       # safrole -- the same motif
        ("CC=Cc1ccc(O)c(OC)c1", False),    # its own product: NOT self-feeding
        ("C=Cc1ccccc1", False),            # styrene: no CH2 between ring and C=C
        ("Cc1ccccc1", False),              # toluene
        ("CCC=C", False),                  # 1-butene: no ring
    ],
)
def test_the_isomerisation_pattern_is_narrow(substrate, fires, thermo, vol):
    """⚠ ``[CH2:4]`` is a TERMINAL methylene, so an already-conjugated arene does
    not match -- which is what stops the template feeding itself."""
    n = _net(thermo, vol, [WATER, _c(substrate), NA, OH],
             [alkene_isomerisation()])
    got = any(r.name == "alkene_isomerisation" for r in n.reactions)
    assert got is fires


@pytest.mark.parametrize(
    ("substrate", "fires"),
    [
        ("C/C=C/c1ccc(O)c(OC)c1", True),   # isoeugenol
        ("CC=Cc1ccc(O)c(OC)c1", True),     # and without the geometry
        ("COc1cc(/C=C/CO)ccc1O", True),    # coniferyl alcohol
        ("c1ccccc1/C=C/c1ccccc1", True),   # stilbene -> two benzaldehydes
        ("C=CCc1ccc(O)c(OC)c1", False),    # eugenol: NOT conjugated yet
        ("C=Cc1ccccc1", False),            # styrene: no carbon on the far end
        ("COc1cc(C=O)ccc1O", False),       # vanillin: its own product
    ],
)
def test_the_cleavage_pattern_is_narrow_at_both_ends(substrate, fires,
                                                    thermo, vol):
    """⚠ ``[c:1]`` demands conjugation to a ring and ``[#6:4]`` a carbon on the
    far end. **Eugenol not matching is the load-bearing case** -- it is why the
    two templates are a bundle and why either alone leaves the flask inert."""
    n = _net(thermo, vol, [WATER, _c(substrate), O2, NA, OH],
             [oxidative_cleavage()])
    got = any(r.name == "oxidative_cleavage" for r in n.reactions)
    assert got is fires


def test_the_cleavage_names_the_lignin_rows_missing_fragment(thermo, vol):
    """Charge coniferyl alcohol and the C2 fragment comes out as glycolaldehyde,
    1:1 with the vanillin. ⚠ The corpus row promises WATER, and the row is what
    is wrong -- S3's rule: *"the mechanism doesn't make the row's product" is not
    a verdict; ask which one is WRONG.*"""
    n = _net(thermo, vol, [WATER, CONIFERYL, O2, NA, OH], [oxidative_cleavage()])
    v = _flask(n, T=440.0, sub=CONIFERYL)
    st = v.state()
    assert st.total(VANILLIN) > 0.05
    assert st.total(GLYCOL) == pytest.approx(st.total(VANILLIN), rel=1e-9)


# ---------------------------------------------------------------------------
# 3. IT RUNS, AND WHAT GATES IT
# ---------------------------------------------------------------------------
def test_clove_oil_becomes_vanillin_and_the_balance_is_an_INVARIANT(net):
    """The route, end to end, in one autoclave: 93% at 470 K in four hours.

    ⚠ THE ACETALDEHYDE IS 1:1 WITH THE VANILLIN, which is panel 1's balance
    showing up as an invariant of the run rather than as an assertion about the
    corpus.
    """
    v = _flask(net, t=14400.0)
    st = v.state()
    van = st.total(VANILLIN)
    assert van == pytest.approx(0.0932, abs=0.002)
    assert st.total(MECHO) == pytest.approx(van, rel=1e-9)
    # matter closes: every eugenol is accounted for
    assert (st.total(EUGENOL) + st.total(ISO) + van
            == pytest.approx(SUBSTRATE, rel=1e-6))
    # and it is an AUTOCLAVE -- a yield without its conditions is not a number
    assert 25.0 < v.pressure < 35.0


def test_the_route_needs_its_TEMPERATURE(net):
    """0.43% in four hours at 400 K against 93% at 470. The digester is not
    decoration."""
    cold = _flask(net, T=400.0, t=14400.0).state().total(VANILLIN)
    hot = _flask(net, T=470.0, t=14400.0).state().total(VANILLIN)
    assert cold / SUBSTRATE < 0.01
    assert hot / SUBSTRATE > 0.9


def test_the_base_is_the_gate_and_a_flask_without_it_is_EXACTLY_inert(net):
    """⚠⚠ AND THE GATE IS NOT WHERE EITHER TEMPLATE PUTS IT.
    ``oxidative_cleavage`` declares no catalyst at all and would cleave any
    isoeugenol in the flask. There is none, because the step that MAKES
    isoeugenol is the base-catalysed one. **A two-template route is gated by
    whichever step comes first, and neither template says so on its own.**
    """
    assert _flask(net, oh=0.0).state().total(VANILLIN) == 0.0
    lo = _flask(net, oh=0.01).state().total(VANILLIN)
    hi = _flask(net, oh=0.50).state().total(VANILLIN)
    assert 0.0 < lo < hi


def test_the_isomerisation_is_the_rate_determining_step(net_isom, net_cleave):
    """Knock each template out and run it alone. ⚠ This is what Ea = 115 kJ/mol
    was CALIBRATED against -- 94.6% in four hours, against a real KOH
    isomerisation's 95%+ in 3-6 h at 470-490 K -- and it is why the intermediate
    never accumulates."""
    isom = _flask(net_isom, t=14400.0, o2=0.0).state()
    cleave = _flask(net_cleave, t=3600.0, sub=ISO).state()
    conv = 1.0 - isom.total(EUGENOL) / SUBSTRATE
    assert conv == pytest.approx(0.9465, abs=0.003)
    # the cleavage is the fast one at the same temperature
    assert cleave.total(VANILLIN) / SUBSTRATE > 0.95
    assert _flask(net_cleave, t=600.0, sub=ISO).state().total(VANILLIN) \
        > _flask(net_isom, t=600.0, o2=0.0).state().total(ISO)


# ---------------------------------------------------------------------------
# 4. ⚠⚠⚠ THE EQUILIBRIUM, AND THE 5.7x THAT WAS NEARLY WRITTEN DOWN
# ---------------------------------------------------------------------------
def test_the_equilibrium_is_exact_on_the_LIQUID_and_not_on_the_inventory(
        net_isom, thermo, vol):
    """⚠⚠⚠ C3's FIRST FLASK READ 15362 AGAINST A kf/kb OF 2678 AND THAT WAS
    NEARLY A FINDING ABOUT CHEMISTRY.

    It is the HEADSPACE. The allyl isomer is ~5x the more volatile, so a share of
    the eugenol sits where no rate law can reach it and ``state().total()``
    reports a ratio the kinetics never enforced. The smaller the liquor, the
    bigger the lie: 0.08 L under 1.9 L of headspace reads 10994.

    **On the liquid alone the flask agrees with detailed balance to the last
    digit.** ``state().total()`` is the right number for a YIELD and the wrong
    one for an EQUILIBRIUM.
    """
    F = next(r for r in net_isom.reactions if r.name == "alkene_isomerisation")
    B = next(r for r in net_isom.reactions
             if r.name == "alkene_isomerisation_rev")
    T = 470.0
    kf = F.A * math.exp(-F.Ea / (R * T))
    kb = B.A * math.exp(-B.Ea / (R * T))

    # detailed balance is exact against the van 't Hoff extrapolation
    dH, dG = reaction_deltas(F, thermo, vol)
    dS = (dH - dG) / 298.15 * 1000.0
    lnK = -(dH * 1000.0 - T * dS) / (R * T)
    assert kf / kb == pytest.approx(math.exp(lnK), rel=1e-9)
    assert kf / kb == pytest.approx(2677.83, rel=1e-4)

    # and the flask reaches exactly that -- ON THE LIQUID
    for water, total_ratio in ((5.0, 10993.93), (40.0, 2866.67)):
        st = _flask(net_isom, t=3.6e5, o2=0.0, water=water).state()
        liquid = st.n_liquid[ISO] / st.n_liquid[EUGENOL]
        inventory = st.total(ISO) / st.total(EUGENOL)
        assert liquid == pytest.approx(kf / kb, rel=1e-6)
        assert inventory == pytest.approx(total_ratio, rel=1e-3)
        assert inventory > liquid


# ---------------------------------------------------------------------------
# 5. THE GEOMETRY THE TEMPLATE DOES NOT DECLARE
# ---------------------------------------------------------------------------
def test_nothing_here_can_price_a_double_bonds_geometry(thermo):
    """⚠ cis, trans and geometry-free isoeugenol are BIT-IDENTICAL in Hf and Gf.

    S7 measured this on ``oleic -> elaidic`` and REFUSED a class for it; here the
    same fact LICENSES leaving the geometry out, because declaring one would
    assert a distinction the thermochemistry cannot carry. **The same measurement
    can refuse one template and permit another; what differs is whether the
    distinction is the point of the reaction.**
    """
    a, b, c = (thermo.get(x) for x in (TRANS_ISO, CIS_ISO, ISO))
    assert a.Hf == b.Hf == c.Hf
    assert a.Gf == b.Gf == c.Gf
    # and they are nonetheless three different SPECIES
    assert TRANS_ISO != ISO
    assert CIS_ISO != ISO


def test_forward_only_discovery_is_what_makes_that_decision_safe(thermo, vol):
    """⚠⚠ The template makes an isoeugenol the corpus does not spell, so a flask
    charged with the CORPUS's trans isomer could in principle drain into eugenol
    through the reverse and come back out as the geometry-free one -- a cycle
    with no driving force at all, since the two price identically.

    It cannot, because **discovery is FORWARD-ONLY** (M5): the reverse is in the
    network but never enumerates species, so the trans isomer is simply inert to
    this template. *A rule that has cost this project a template twice does
    useful work here.*
    """
    n = _net(thermo, vol, [WATER, TRANS_ISO, O2, NA, OH], vanillin_chemistry())
    assert [r.name for r in n.reactions] == ["oxidative_cleavage"]
    assert ISO not in n.species
    assert EUGENOL not in n.species

    v = _flask(n, sub=TRANS_ISO)
    st = v.state()
    assert st.total(VANILLIN) > 0.09
    assert st.total(MECHO) == pytest.approx(st.total(VANILLIN), rel=1e-9)


# ---------------------------------------------------------------------------
# 6. WHAT THE BUNDLE MUST NOT BE GIVEN, AND IT WAS MEASURED NOT ASSUMED
# ---------------------------------------------------------------------------
def test_the_dissociation_set_REFUSES_because_eugenol_is_a_phenol(thermo, vol):
    """⚠⚠ The bundle's docstring first claimed it needed ``dissociation_templates()``
    beside it, copied from ``wacker_chemistry``. **Running it is what caught
    that.**

    Eugenol IS a phenol, so ``phenol_dissociation`` fires on it and the network
    refuses for want of a pKa for the eugenolate. G5's rule reaching a new
    substrate: *an open-ended rewrite over a curated table will find the edge of
    the table* -- met on an amine there, on a phenol here. The refusal is KEPT:
    this route needs no phenolate.
    """
    with pytest.raises(ValueError) as exc:
        _net(thermo, vol, [WATER, EUGENOL, O2, NA, OH],
             vanillin_chemistry() + list(dissociation_templates()))
    msg = str(exc.value)
    assert "phenol_dissociation" in msg
    assert "net charge of -1" in msg

    # and without them it builds and runs
    n = _net(thermo, vol, [WATER, EUGENOL, O2, NA, OH], vanillin_chemistry())
    assert sorted(r.name for r in n.reactions) == [
        "alkene_isomerisation", "alkene_isomerisation_rev", "oxidative_cleavage",
    ]


def test_the_bundle_is_two_templates_and_EITHER_ALONE_is_inert(thermo, vol):
    """The pair is the route. ⚠ Eugenol is not a cleavage substrate and
    isoeugenol is not an isomerisation substrate, so one template makes no
    vanillin from clove oil at all."""
    for only in ([alkene_isomerisation()], [oxidative_cleavage()]):
        n = _net(thermo, vol, [WATER, EUGENOL, O2, NA, OH], only)
        assert VANILLIN not in n.species
    assert len(vanillin_chemistry()) == 2


# ---------------------------------------------------------------------------
# 7. WHAT THE TWO CLASSES BOUGHT, AND THE PAIR IS SUPER-ADDITIVE
# ---------------------------------------------------------------------------
def test_the_two_classes_are_credited_and_named():
    """⚠ Credited by NAME against the template functions, so a rename breaks a
    test rather than silently un-crediting a class."""
    import catalog_coverage as cc

    assert cc.TEMPLATE_CLASSES["alkene-isomerisation"] == "alkene_isomerisation"
    assert cc.TEMPLATE_CLASSES["oxidative-cleavage"] == "oxidative_cleavage"
    assert alkene_isomerisation().name == "alkene_isomerisation"
    assert oxidative_cleavage().name == "oxidative_cleavage"


def test_the_PAIR_is_worth_more_than_the_sum_of_its_parts():
    """⚠⚠⚠ THE FINDING PLAYABLE.md §8b EXISTS FOR, AND A TRUNCATED PROBE HID IT.

    `alkene-isomerisation` alone is worth **+0** playable routes and
    `oxidative-cleavage` alone **+1**; together they are **+2**, because
    `vanillin-eugenol` needs both while `vanillin-lignin` needs only the second.
    C3's own scouting probe printed the pair table `[:12]` and the pair fell off
    the bottom, so the session went in expecting +1 and delivered +2.

    ⚠ **§8 RANKS ROUTES AND A SESSION BUILDS TEMPLATES**, which is a different
    question whenever two rows share a class -- and it is why §8b is now
    generated beside it.
    """
    import build_playable as bp
    import catalog as cat
    import catalog_coverage as cc

    def playable(classes):
        tc = {k: v for k, v in cc.TEMPLATE_CLASSES.items() if k not in classes}
        pool = {rid for rid in bp.routes
                if cat.route_reachable(bp.steps, rid, bp.routes[rid].target,
                                       bp.priced, tc, bp.compounds)}
        return len(bp.closure(pool=pool)[0])

    both = playable(set())
    assert both == 20                                        # C4's baseline
    assert playable({"alkene-isomerisation"}) == 19          # -1: cleavage only
    assert playable({"oxidative-cleavage"}) == 18            # -2: neither route
    assert playable({"alkene-isomerisation", "oxidative-cleavage"}) == 18

    # ⚠⚠ READ AS DIFFERENCES, NOT AS LEVELS -- which is why this test
    # survived C4 with four numbers changed and its FINDING untouched. C4 added
    # two playable routes elsewhere, so every level above moved by +2 and every
    # difference below is identical to C3's. **A test that pins a claim about a
    # difference must assert the difference.**
    base = playable({"alkene-isomerisation", "oxidative-cleavage"})
    assert playable({"oxidative-cleavage"}) - base == 0
    assert playable({"alkene-isomerisation"}) - base == 1
    assert both - base == 2


def test_vanillin_feeds_nothing_and_that_is_still_true():
    """⚠ C1 granted one row and the list GREW 21 -> 24. C2 granted two and it
    shrank to 22. C3 granted two and it shrank to 20, with the ceiling UNCHANGED
    at 41 for the second session running: **vanillin feeds nothing.**

    *A work order derived from a fixed point is not a burndown list.*

    ⚠⚠⚠ **C4 IS THE COUNTER-EXAMPLE, AND IT IS WHY THIS TEST WAS RENAMED.**
    It granted one class and the list GREW 20 -> 23 while the ceiling moved
    41 -> 45 -- the first ceiling move since C1 -- because a fermentation's
    products feed four other routes. So "the work order shrank" was never the
    claim worth pinning; **"vanillin feeds nothing" was**, and that is what is
    asserted here. The list and ceiling numbers live in `test_playable.py`,
    which is the file that owns them.
    """
    import build_playable as bp

    assert "vanillin-eugenol" not in bp.FED_BUT_UNRUNNABLE
    assert "vanillin-lignin" not in bp.FED_BUT_UNRUNNABLE
    # nothing new became FED, because vanillin is not a reagent anywhere
    assert not any("vanillin" in bp.needs(r) for r in bp.routes)


def test_section_8b_names_the_one_FALSE_CREDIT_left_in_the_table():
    """⚠⚠⚠ §8b's own detector found a live false credit in the work order:
    `oxidative-complexation` is scored **+1** on `iron-gall-ink`, whose product
    `iron-gallate-marker` the corpus deliberately does not spell. **Build it and
    the route goes template-ready and `build_network` has no graph to make the
    product from.**

    ⚠ AND THE DETECTOR'S FIRST VERSION HAD ITS OWN FALSE CREDIT IN IT -- it
    blamed `pyrolysis`/`coal-gas` too, where the marker is on the LEFT and the
    route was already dead. **A false-credit detector needs the same
    does-it-actually-run check as everything else it audits.**
    """
    import os

    import build_playable as bp
    import catalog as cat

    md = open(os.path.join(cat.CATALOG_DIR, "PLAYABLE.md"),
              encoding="utf-8").read()
    assert "8b. The same table asked the way a SESSION spends it" in md
    assert "CONTAINS A FALSE CREDIT" in md
    assert "`oxidative-complexation` is scored **+1** on `iron-gall-ink`" in md
    assert "coal-gas" not in md.split("CONTAINS A FALSE CREDIT")[1][:400]

    # the marker really is absent from the corpus, deliberately
    assert "iron-gallate-marker" not in bp.compounds
    steps = [s for s in bp.steps if s.route == "iron-gall-ink"]
    assert any("iron-gallate-marker" in s.products for s in steps)


def test_section_8b_says_a_template_cannot_buy_the_top_two_rows():
    """⚠⚠ §8's top row is `hall-heroult` at +3 and `blast-furnace` at +2, and
    NEITHER can be bought by building its class: hall-heroult's cryolite and the
    blast furnace's three species are refused a price as well. Granting
    `slagging` moves **nothing at all**.

    *A row's worth assumes every OTHER blocker away, and a template only removes
    one of them.*
    """
    import build_playable as bp
    import catalog as cat
    import catalog_coverage as cc

    def granted(extra):
        tc = dict(cc.TEMPLATE_CLASSES) | {k: "<hypothetical>" for k in extra}
        return {rid for rid in bp.routes
                if cat.route_reachable(bp.steps, rid, bp.routes[rid].target,
                                       bp.priced, tc, bp.compounds)}

    assert "hall-heroult" not in granted({"molten-salt-electrolysis"})
    assert "downs-cell" in granted({"molten-salt-electrolysis"})
    assert granted({"slagging"}) == bp.RUNNABLE

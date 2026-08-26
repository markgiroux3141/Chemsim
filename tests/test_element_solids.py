"""S8 -- the nine element solids, and the reduction this engine cannot hold.

Two things are pinned here and they are the two halves of one session.

**The nine element solids.** `data/catalog` had 15 routes blocked only by a bare
element symbol, and the refusal was right: the ideal-gas record for `[C]` is the
carbon ATOM at Gf +671 kJ/mol while the charcoal in the flask is 0. The fix is
the one S1 already used for iron, nickel and copper -- an entry in
`mineral_data` on the SOLID basis, `ions=()`, `Hf = Gf = 0` by definition -- and
every one of them is charged into a real `Vessel` below rather than argued for.

⚠ **AND WHAT IT IS WORTH WAS PREDICTED AND MEASURED: +14 species-ready routes
and ZERO on the intersection**, because not one of the 15 is template-ready.
See `chemsim-gas-processes` and MILESTONES §S8.

**The reduction it does not buy.** `gas-solid-reduction` was the only +2 on the
work queue and it is REFUSED by `surface.LN_K_IRREVERSIBLE` on all four of its
rows, because a gas-solid reduction is genuinely reversible -- which is why a
blast furnace's top gas still contains CO. The four ln K values are pinned so
that the refusal cannot quietly become an acceptance.
"""

from __future__ import annotations

import math

import pytest

from chemsim.constants import R
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties import mineral_data as md
from chemsim.properties import surface as sf
from chemsim.properties.element_data import REFERENCE_STATES
from chemsim.vessel import Vessel

# The EIGHT of S8's nine that are still lattices, and the three S1 added before
# them. ⚠⚠ S10 REMOVED "zinc" FROM THIS TUPLE, and that is a milestone rather
# than a correction: S8's curation of zinc-as-a-lattice was right for what it was
# for, and S10 found that zinc also has a monatomic vapour, one condensed form
# and a measured sublimation curve -- so it belongs in ``element_data`` with
# mercury and iodine, where it can BOIL. A lattice may react and may never boil;
# that was the sentence blocking the retort, and it was about the entry.
S8_SOLIDS = (
    "cobalt", "silver", "platinum", "palladium", "lead", "aluminium",
    "sodium", "carbon-graphite",
)
S1_SOLIDS = ("iron", "nickel", "copper")


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def volatility():
    return VolatilityProvider()


# ---------------------------------------------------------------------------
# the free exact number, and it is the whole check on the entry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", S8_SOLIDS + S1_SOLIDS)
def test_an_element_solid_is_zero_by_definition(name):
    """Hf = Gf = 0 EXACTLY on the solid basis, and Gf is DERIVED rather than
    copied -- so a non-zero result would prove the CAS names a different
    allotrope from the reference state. That is the tin lesson: CRC's row for
    7440-31-5 is GREY tin at Hfs = -2.1 kJ/mol, and the generator refuses it."""
    rec = md.MINERALS[name]
    assert rec.Hf_solid == 0.0
    assert rec.Gf_solid == 0.0
    assert rec.ions == ()          # an element solid has no dissolved form
    assert len(rec.formula) == 1   # one element


@pytest.mark.parametrize("name", S8_SOLIDS)
def test_its_entropy_comes_from_the_element_reference_state(name):
    """The Gf derivation subtracts the reference entropies in `element_data`, so
    every row here needs one -- which is why S8 had to add Pt and Pd there."""
    rec = md.MINERALS[name]
    element = next(iter(rec.formula))
    ref = REFERENCE_STATES[element]
    assert ref.phase == "s"
    assert rec.S0_solid == pytest.approx(ref.S0, abs=0.15)


@pytest.mark.parametrize("name", S8_SOLIDS)
def test_it_can_actually_sit_in_a_flask(name):
    """`priced_solid` is the vessel's own bar: a formation pair is not enough,
    the crystal also has to say how much room it takes and how much heat it
    holds."""
    assert md.priced_solid(name)
    rec = md.MINERALS[name]
    assert rec.Cp_solid > 0.0
    assert rec.Vm_solid > 0.0


def test_all_the_element_solids_charge_into_a_real_vessel_and_stay(
    thermo, volatility
):
    """Verified by RUNNING, on S6's precedent -- reading `priced_solid` is not
    the same claim. Nothing reacts, which is correct: no template and no term
    mentions any of them, so each is a constant of the motion."""
    lattices = [md.MINERALS[n].lattice for n in S8_SOLIDS]
    net = build_network(["O=O", "N#N"] + lattices, [], thermo=thermo,
                        volatility=volatility)
    for s in lattices:
        assert s in net.species
    v = Vessel(net, volume=1.0, T=800.0, T_env=800.0, UA=1.0e4, k_vent=0.0)
    v.charge({"O=O": 0.02, "N#N": 0.08}, phase="gas")
    v.charge({s: 0.01 for s in lattices}, phase="solid")
    v.run(600.0, rtol=1.0e-8, atol=1.0e-11)
    st = v.state()
    for s in lattices:
        assert st.total(s) == 0.01
    assert v.conservation_report() == ""


def test_a_bare_element_is_still_refused_on_the_ideal_gas_basis(thermo):
    """Curating the SOLID basis does not soften the ideal-gas refusal by one
    digit, and it must not: the ideal-gas record for `[C]` is the carbon ATOM at
    Gf +671 kJ/mol, which is not the charcoal in the flask."""
    for smiles in ("[C]", "[Pb]", "[Al]", "[Na]"):
        with pytest.raises(ValueError, match="bare element symbol"):
            thermo.get(smiles)


# ---------------------------------------------------------------------------
# the +2 that is not available, and why the bound is not the problem
# ---------------------------------------------------------------------------

# (oxide, metal, moles of CO per formula unit, T_run, expected ln K, refusal)
# ⚠ S10 -- THE LAST COLUMN IS NEW, because the zinc row is now refused for a
# SECOND and independent reason. Three of these are lattices whose ln K is under
# the irreversibility bar; zinc is not a lattice at all any more, so a term
# priced on the SOLID basis cannot reach it -- which is a stronger statement of
# the same conclusion, not a weaker one. Both refusals are real and the row is
# still not a surface reaction.
REDUCTIONS = [
    ("tenorite", "copper", 1, 1500.0, 10.90, "below the bar"),
    ("litharge", "lead", 1, 1400.0, 7.24, "below the bar"),
    ("hematite", "iron", 3, 1300.0, 4.20, "below the bar"),
    ("zincite", "zinc", 1, 1400.0, -4.10, "no mineral called 'zinc'"),
]


@pytest.mark.parametrize(
    "oxide,metal,n_co,T_run,expected,refusal", REDUCTIONS,
    ids=[r[0] for r in REDUCTIONS],
)
def test_a_gas_solid_reduction_cannot_clear_the_irreversibility_bar(
    oxide, metal, n_co, T_run, expected, refusal, thermo,
):
    """`gas-solid-reduction` was the only +2 on the work queue and every one of
    its rows fails `LN_K_IRREVERSIBLE`. The bound is not the problem: a blast
    furnace's top gas still contains CO because these reductions really are
    reversible, and the zinc row is not even downhill -- a real retort works by
    boiling the zinc off at 1180 K, which is product removal and not a
    favourable equilibrium.

    ⚠⚠ S9 -- THIS REFUSAL STANDS AND THE CONCLUSION S8 DREW FROM IT DOES NOT.
    An IRREVERSIBLE term still cannot hold these rows, which is what this test
    asserts and all it asserts. But `SolidStateArrays` can: writing its gas
    quotient as two ONE-SIDED products makes a gas REACTANT bounded, and
    `tenorite-carbon-monoxide-reduction` and
    `litharge-carbon-monoxide-reduction` are ordinary rows of
    `SOLID_STATE_REACTIONS` now. See `tests/test_smelting.py`. **The reading to
    keep is "the reverse is a real flux"; the reading to drop is "so it cannot
    be expressed".**"""
    o = md.MINERALS[oxide]
    co, co2 = thermo.get("[C-]#[O+]"), thermo.get("O=C=O")
    n_m = next(v for k, v in o.formula.items() if k != "O")
    # ⚠ S10 -- THE METAL'S SOLID-BASIS PAIR IS THE DEFINITIONAL ZERO, not a
    # lookup. Every metal in REDUCTIONS is its element's reference state, so
    # Hf = Gf = 0 exactly -- which is why this arithmetic survives zinc leaving
    # ``mineral_data`` unchanged to the digit. The equivalence is asserted rather
    # than assumed for the three that are still lattices.
    if metal in md.MINERALS:
        assert md.MINERALS[metal].Hf_solid == 0.0
        assert md.MINERALS[metal].Gf_solid == 0.0
    dH = (n_co * co2.Hf) - (o.Hf_solid + n_co * co.Hf)
    dG = (n_co * co2.Gf) - (o.Gf_solid + n_co * co.Gf)
    dS = (dH - dG) * 1000.0 / 298.15
    ln_K = -(dH * 1000.0 - T_run * dS) / (R * T_run)
    assert ln_K == pytest.approx(expected, abs=0.05)
    assert ln_K < sf.LN_K_IRREVERSIBLE
    # ... and the term itself refuses the declaration, not just the arithmetic
    decl = sf.SurfaceReaction(
        name=f"{oxide}-reduction",
        solids=((oxide, -1, 1.0), (metal, +n_m, 0.0)),
        gases=(("[C-]#[O+]", -n_co, 1.0), ("O=C=O", +n_co, 0.0)),
        mechanism="gas-solid-reduction",
        T_run=T_run,
        note="S8 measured this and it is refused; see the module docstring",
    )
    with pytest.raises(sf.UnpricedSurfaceReaction, match=refusal):
        sf.price(decl, thermo)


def test_the_roasting_family_still_clears_it(thermo):
    """The bar is not unreachable -- every ROAST is far above it, which is what
    makes the four refusals above a statement about the chemistry.

    ⚠ S9 -- THE ">60" CLAIM IS ABOUT THE ROASTS AND NOT ABOUT THE TABLE.
    `carbon-combustion` joined `SURFACE_REACTIONS` and clears the bar by 1.87
    nats rather than 46, because above ~1000 K carbon dioxide over carbon is
    increasingly taken to CO -- so its own product stops being the stable one.
    That reversal is `solid_state.boudouard-gasification`, declared next door.
    """
    roasts = [d for d in sf.SURFACE_REACTIONS if d.name.endswith("-roasting")]
    assert len(roasts) == 4
    assert len(sf.SURFACE_REACTIONS) == 5
    for decl in roasts:
        priced = sf.price(decl, thermo)
        assert priced.ln_K_run > sf.LN_K_IRREVERSIBLE
        assert priced.ln_K_run > 60.0
    # every row still clears the bar -- that is what makes THIS term's
    # forward-only integration a measurement rather than a simplification
    for decl in sf.SURFACE_REACTIONS:
        assert sf.price(decl, thermo).ln_K_run > sf.LN_K_IRREVERSIBLE


def test_the_zinc_retort_is_a_product_removal_problem_not_an_equilibrium(thermo):
    """Worth its own assertion because it is the one row that is UPHILL: the CO
    route, `ZnO + CO -> Zn + CO2`, is +63.31 kJ/mol and no bound on a rate law
    fixes that.

    ⚠⚠ S9 -- AND THIS IS NOT THE CATALOG'S ROW. `zinc-smelting` step 2 reads
    `zinc-oxide + carbon-graphite -> zinc + carbon-monoxide`, i.e. the CARBON
    route, where the entropy of making a mole of CO carries it. What is measured
    below is the CO route, which nothing in the corpus asks for. **The arithmetic
    here is right and it was about the wrong reaction** -- so this test is kept
    as the measurement it is and the +63.31 must not be read as "the class is
    blocked" again.

    ⚠⚠ S10 -- AND THE PRODUCT REMOVAL IN THE TITLE IS EXPRESSIBLE NOW, which
    is the third sentence in this file to come apart the same way. This test used
    to end "zinc boils at 1180 K and leaves; `mineral_data` holds zinc as a
    lattice with no vapour pressure, so that escape is not expressible here
    either." Both clauses were true and the conclusion did not follow: the
    lattice entry was the obstacle, not the metal. `[Zn]` is an elemental species
    with a boiling point now, and `tests/test_smelting.py` measures the retort
    distilling and the vented flask losing its product up the chimney.

    ⚠ What is UNCHANGED is the number below. Zinc's solid basis is its element
    reference state either way, so Hf = Gf = 0 exactly, and +63.31 does not move
    by a digit -- which is the point worth pinning here.
    """
    zincite = md.MINERALS["zincite"]
    co, co2 = thermo.get("[C-]#[O+]"), thermo.get("O=C=O")
    assert "zinc" not in md.MINERALS               # S10 -- it is an element now
    assert REFERENCE_STATES["Zn"].smiles == "[Zn]"
    assert REFERENCE_STATES["Zn"].phase == "s"     # ...and a SOLID one
    # Gf_solid(Zn) is 0 BY DEFINITION and is written as such
    dG = (0.0 + co2.Gf) - (zincite.Gf_solid + co.Gf)
    assert dG > 0.0
    assert math.isclose(dG, 63.31, abs_tol=0.05)

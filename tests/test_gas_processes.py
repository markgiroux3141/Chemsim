"""S7 -- the four inorganic gas processes, and the neutral-fragment refusal.

Two things are pinned here, and they came out of the same measurement.

**The four templates**, each credited to a catalog class and each verified by
running rather than by reading -- ``validation/gas_processes.py`` is the long
form. What is worth a test rather than a panel is the behaviour NOBODY
DECLARED: the shift's conversion falling as it is heated, the reformer being
inert until it is hot, and Deacon's ceiling and rate crossing.

**The refusal**, which is what stopped ``crosslinking`` being built. Joback
prices ``CC(C)=CC.S1SSSSSSS1`` -- a dot-separated mixture of its own two
reactants -- 222 kJ/mol above the sum of those two parts, and until S7 the
guard only refused a multi-fragment SMILES if one of the fragments was CHARGED.
"""

from __future__ import annotations

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.mineral_data import MINERALS
from chemsim.reactions import ReactionTemplate
from chemsim.reactions.synthesis import (
    claus_chemistry,
    claus_comproportionation,
    deacon_oxidation,
    hydrogen_sulfide_combustion,
    steam_reforming,
    water_gas_shift,
)
from chemsim.vessel import Vessel


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


CO, WATER, CO2, H2 = c("[C-]#[O+]"), c("O"), c("O=C=O"), c("[H][H]")
CH4, HCL, O2, CL2 = c("C"), c("Cl"), c("O=O"), c("ClCl")
H2S, SO2, S8 = c("S"), c("O=S=O"), c("S1SSSSSSS1")

HEMATITE = MINERALS["hematite"].lattice
NICKEL = MINERALS["nickel"].lattice
TENORITE = MINERALS["tenorite"].lattice

TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def volatility():
    return VolatilityProvider()


def gas_flask(net, T, charge, seconds, solid=None, volume=1.0):
    v = Vessel(net, volume=volume, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    v.charge(charge, phase="gas")
    if solid:
        v.charge(solid, phase="solid")
    v.run(seconds, **TIGHT)
    return v


# ---------------------------------------------------------------------------
# each template fires on its catalog row's own reactants, and BALANCES
# ---------------------------------------------------------------------------
# ``build_network`` refuses a rewrite that does not conserve elements and charge,
# so "a reaction survived" IS the balance assertion. That matters most for the
# 24-slot Claus template, whose stoichiometry is easy to get wrong by one atom.

FIRES = [
    ("water_gas_shift", water_gas_shift, [CO, WATER]),
    ("steam_reforming", steam_reforming, [CH4, WATER]),
    ("deacon_oxidation", deacon_oxidation, [HCL, O2]),
    ("hydrogen_sulfide_combustion", hydrogen_sulfide_combustion, [H2S, O2]),
    ("claus_comproportionation", claus_comproportionation, [H2S, SO2]),
]


@pytest.mark.parametrize("name,make,seed", FIRES, ids=[f[0] for f in FIRES])
def test_template_fires_and_balances(name, make, seed, thermo, volatility):
    net = build_network(seed, [make()], thermo=thermo, volatility=volatility,
                        generations=1, max_species=40)
    assert any(r.name == name for r in net.reactions), f"{name} matched nothing"


def test_claus_is_sixteen_eight_three_sixteen():
    """The smallest whole-number multiple that makes S8 crowns, not 2:1:3:2."""
    t = claus_comproportionation()
    assert t.n_reactant_slots == 24
    out = t.run(tuple([Molecule.from_smiles("S")] * 16
                      + [Molecule.from_smiles("O=S=O")] * 8))
    assert out, "the 24-slot rewrite produced nothing"
    products = [m.smiles for m in out[0]]
    assert products.count(S8) == 3
    assert products.count(WATER) == 16


def test_a_declared_order_may_still_not_be_reversible():
    """The burner's rule, restated on a template with twenty-four slots."""
    with pytest.raises(ValueError, match="reversible"):
        ReactionTemplate(
            name="claus_but_reversible",
            smarts=claus_comproportionation().smarts,
            A=1.0e9, Ea=50_000.0, phase="gas", reversible=True,
            orders=(1.0,) + (0.0,) * 15 + (1.0,) + (0.0,) * 7,
        )


# ---------------------------------------------------------------------------
# the three behaviours nobody declared
# ---------------------------------------------------------------------------


def test_the_shift_gets_worse_when_it_is_heated(thermo, volatility):
    """dH is -41 kJ/mol, so K FALLS with T -- which is why a plant shifts twice.

    Nothing in the template says so. The peak sits near 620 K because below it
    the barrier is the limit and above it the equilibrium is.
    """
    net = build_network([CO, WATER], [water_gas_shift()], thermo=thermo,
                        volatility=volatility)
    conv = {}
    for T in (500.0, 620.0, 700.0, 900.0):
        st = gas_flask(net, T, {CO: 0.10, WATER: 0.10}, 3600.0,
                       solid={HEMATITE: 0.1}).state()
        conv[T] = st.total(CO2) / 0.10
        assert st.total(CO) + st.total(CO2) == pytest.approx(0.10, abs=1e-9)
    assert conv[500.0] < conv[620.0]          # cold: the RATE is the limit
    assert conv[620.0] > conv[700.0] > conv[900.0]   # hot: the CEILING is


def test_the_reformer_is_inert_until_it_is_hot(thermo, volatility):
    """+206 kJ/mol and two extra moles of gas: heat has to buy it twice."""
    net = build_network([CH4, WATER], [steam_reforming()], thermo=thermo,
                        volatility=volatility)
    cold = gas_flask(net, 700.0, {CH4: 0.25, WATER: 0.25}, 3600.0,
                     solid={NICKEL: 0.1}).state()
    hot = gas_flask(net, 1300.0, {CH4: 0.25, WATER: 0.25}, 3600.0,
                    solid={NICKEL: 0.1}).state()
    assert cold.total(CH4) > 0.2499           # essentially untouched
    assert hot.total(CH4) < 0.17
    assert hot.total(H2) == pytest.approx(3 * (0.25 - hot.total(CH4)), rel=1e-6)


def test_the_reformer_is_the_one_equilibrium_pressure_hurts(thermo, volatility):
    """Two moles in, four out. The only change between the rows is the charge."""
    net = build_network([CH4, WATER], [steam_reforming()], thermo=thermo,
                        volatility=volatility)
    thick = gas_flask(net, 1100.0, {CH4: 0.25, WATER: 0.25}, 3600.0,
                      solid={NICKEL: 0.1}).state()
    thin = gas_flask(net, 1100.0, {CH4: 0.002, WATER: 0.002}, 3600.0,
                     solid={NICKEL: 0.1}).state()
    assert (1 - thin.total(CH4) / 0.002) > 3 * (1 - thick.total(CH4) / 0.25)


def test_deacons_ceiling_and_rate_cross(thermo, volatility):
    """The squeeze that killed the process, and neither half is declared.

    Below ~600 K an hour is not enough time; from 700 K up ten seconds is
    already equilibrium and every further degree lowers what equilibrium is.
    """
    net = build_network([HCL, O2], [deacon_oxidation()], thermo=thermo,
                        volatility=volatility)

    def conv(T, seconds):
        st = gas_flask(net, T, {HCL: 0.40, O2: 0.10}, seconds,
                       solid={TENORITE: 0.1}).state()
        assert st.total(HCL) + 2 * st.total(CL2) == pytest.approx(0.40, abs=1e-9)
        return 2 * st.total(CL2) / 0.40

    assert conv(450.0, 10.0) < conv(450.0, 3600.0) - 0.2      # rate-limited
    for T in (700.0, 800.0, 900.0):
        assert conv(T, 10.0) == pytest.approx(conv(T, 3600.0), rel=1e-6)
    assert conv(600.0, 3600.0) > conv(700.0, 3600.0) > conv(800.0, 3600.0)


def test_the_claus_feed_ratio_is_not_declared_anywhere(thermo, volatility):
    """Two templates in one flask, and the best air rate is the one that leaves
    exactly the 2:1 H2S:SO2 the second template wants -- 0.10 mol for 0.20 of
    feed. Neither template knows the other exists."""
    net = build_network([H2S, O2], claus_chemistry(), thermo=thermo,
                        volatility=volatility)
    got = {}
    for o2 in (0.05, 0.10, 0.30):
        st = gas_flask(net, 1100.0, {H2S: 0.20, O2: o2}, 3600.0).state()
        got[o2] = 8 * st.total(S8) / 0.20
        closure = st.total(H2S) + st.total(SO2) + 8 * st.total(S8)
        assert closure == pytest.approx(0.20, rel=1e-6)
    assert got[0.10] > got[0.30] > got[0.05]
    assert got[0.10] == pytest.approx(1.0, rel=1e-6)


# ---------------------------------------------------------------------------
# the refusal that stopped `crosslinking` being built
# ---------------------------------------------------------------------------


def test_a_neutral_mixture_is_refused_and_the_message_names_the_fragments(thermo):
    """``CC(C)=CC.S1SSSSSSS1`` is the catalog's vulcanised-rubber marker, and it
    is its own two reactants written side by side. Joback priced it at +273.70
    against the +51.59 its parts sum to."""
    with pytest.raises(ValueError, match="NEUTRAL fragments"):
        thermo.get("CC(C)=CC.S1SSSSSSS1")
    with pytest.raises(ValueError, match="NEUTRAL fragments"):
        thermo.get("NCCCCCCN.OC(=O)CCCCC(=O)O")


def test_the_ideal_gas_sum_is_an_identity_and_benson_honours_it(thermo):
    """Which is why the refusal is not arbitrary: in an ideal gas there are no
    intermolecular interactions, so the record for a mixture IS the sum of the
    fragments'. Benson is additive over groups and comes out at the identity;
    Joback has a constant term and does not."""
    parts = thermo.get("CC(C)=CC").Hf + thermo.get("S1SSSSSSS1").Hf
    assert parts == pytest.approx(51.59, abs=0.02)
    # and the two Benson-priced fragment pairs the catalog carries are additive
    butyl = thermo.get("CC(C)(C)").Hf + thermo.get("CC(C)=CC").Hf
    assert butyl == pytest.approx(-184.81, abs=0.02)


def test_a_charged_mixture_still_gets_its_own_message(thermo):
    """The lattice and the salt-pair refusals are unchanged: they name what to
    charge instead, and a mineral names itself."""
    with pytest.raises(ValueError, match="ionic LATTICE"):
        thermo.get("[Na+].[Cl-]")


def test_a_single_neutral_molecule_is_untouched(thermo):
    """The blast radius stops at the dot."""
    assert thermo.get("CC(C)=CC").Hf == pytest.approx(-48.83, abs=0.01)
    assert thermo.get("O").Hf == pytest.approx(-241.83, abs=0.01)


# ---------------------------------------------------------------------------
# the corpus rows S7's balance audit found, pinned so they cannot go quiet
# ---------------------------------------------------------------------------
# ``validation/corpus_balance.py`` sweeps all 377 steps and takes ~15 s; these
# two rows are the ones the sweep's conclusions rest on, so they are pinned here
# rather than left to the audit alone.


def _balances(reactants, products):
    """Is there a strictly positive coefficient vector? The audit's own test."""
    import numpy as np
    from scipy.optimize import linprog

    counts = []
    for smi in list(reactants) + list(products):
        m = Molecule.from_smiles(smi)
        d = dict(m.element_counts())
        d["<charge>"] = m.charge
        counts.append(d)
    keys = sorted({k for d in counts for k in d if d[k]})
    A = np.array(
        [[(d.get(k, 0) if j < len(reactants) else -d.get(k, 0))
          for j, d in enumerate(counts)] for k in keys], dtype=float,
    )
    return bool(linprog(c=np.zeros(A.shape[1]), A_eq=A,
                        b_eq=np.zeros(A.shape[0]),
                        bounds=[(1.0, None)] * A.shape[1],
                        method="highs").success)


OLEIC = r"CCCCCCCC/C=C\CCCCCCCC(=O)O"
ELAIDIC = "CCCCCCCC/C=C/CCCCCCCC(=O)O"


def test_the_margarine_row_cannot_be_balanced_and_dropping_the_h2_fixes_it():
    """`oleic + H2 + Ni -> elaidic + Ni`: a cis/trans pair is C18H34O2 both
    sides, so the hydrogen's only coefficient is zero."""
    assert not _balances([OLEIC, "[H][H]", "[Ni]"], [ELAIDIC, "[Ni]"])
    assert _balances([OLEIC, "[Ni]"], [ELAIDIC, "[Ni]"])
    assert _balances([OLEIC, "[H][H]", "[Ni]"], [ELAIDIC, "[H][H]", "[Ni]"])


def test_the_cis_trans_pair_prices_at_exactly_zero(thermo):
    """Which is why the row would not be buildable even balanced. No estimator
    here tells a cis alkene from a trans one, so K would come out at 1 for a
    reaction whose real equilibrium is about 5:1 toward the trans isomer."""
    assert thermo.get(OLEIC).Hf == thermo.get(ELAIDIC).Hf
    assert thermo.get(OLEIC).Gf == thermo.get(ELAIDIC).Gf


def test_the_one_headline_route_with_an_unbalanceable_row_is_inert():
    """`perkin-route` step 1 is in the BOTH column and does not balance: its
    sodium acetate is the BASE, written as consumed. It is inert because the
    template that covers the class never mentions the base -- so the ROW is
    wrong and the MECHANISM is right, which is `vitriol-distillation`'s landmine
    in a milder form."""
    from chemsim.reactions.synthesis import perkin_condensation

    benzaldehyde, anhydride = "O=Cc1ccccc1", "CC(=O)OC(C)=O"
    acetate, cinnamic, acetic = "CC(=O)[O-].[Na+]", "OC(=O)/C=C/c1ccccc1", "CC(=O)O"
    assert not _balances([benzaldehyde, anhydride, acetate], [cinnamic, acetic])
    assert "Na" not in perkin_condensation().smarts

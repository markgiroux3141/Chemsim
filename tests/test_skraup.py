"""S12 -- the Skraup, and the first template whose OXIDANT becomes a reagent.

``skraup-route`` step 2 writes aniline on BOTH sides. That is not
``library._maybe_catalyse``'s case and it is not ``corpus_balance``'s
``spurious`` case either: the aniline coming out is the NITROBENZENE oxidant,
reduced. Reading the class name instead of the row would have thrown the row
away, and reading only the balance check would have kept a row that is not the
reaction it is written as -- ``vanillin-lignin`` sat next to this one on the
same queue and is exactly that.

⚠⚠ AND IT HAD TO BE PRICED TWICE. Seven molecules become nine, so counting
molecules gives a POSITIVE dS -- and that is a statement about an ideal gas.
This template is ``phase="liquid"``, so ``reaction_deltas`` puts every
condensable species on its own pure liquid and NINE product molecules condense
against SEVEN reactant ones. dS comes out NEGATIVE and dH moves by 163 kJ/mol.
``test_the_two_standard_states_disagree_on_the_sign_of_dS`` pins both, because
the gas-basis numbers were written into the source comment first.
"""

from __future__ import annotations

import pytest

from chemsim.network import build_network
from chemsim.properties import VolatilityProvider
from chemsim.properties.electrolyte import electrolyte_provider
from chemsim.reactions.synthesis import quinoline_chemistry, skraup_cyclisation
from chemsim.reactions.thermo import reaction_deltas
from chemsim.vessel import Vessel

ANILINE = "Nc1ccccc1"
ACROLEIN = "C=CC=O"
NITROBENZENE = "O=[N+]([O-])c1ccccc1"
QUINOLINE = "c1ccc2ncccc2c1"
HYDRONIUM = "[OH3+]"
BISULFATE = "O=S(=O)([O-])O"
WATER = "O"
TOLUIDINE = "Cc1ccc(N)cc1"
METHYLQUINOLINE = "Cc1ccc2ncccc2c1"

TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)


@pytest.fixture(scope="module")
def vol():
    return VolatilityProvider()


@pytest.fixture(scope="module")
def thermo(vol):
    return electrolyte_provider(volatility=vol)


@pytest.fixture(scope="module")
def net(thermo, vol):
    return build_network(
        [ANILINE, ACROLEIN, NITROBENZENE, HYDRONIUM, BISULFATE, WATER],
        quinoline_chemistry(), thermo=thermo, volatility=vol,
    )


def _flask(net, thermo, vol, *, T=450.0, acid=0.2, nitro=1.0, acrolein=1.0,
           amine=ANILINE, vent=0.0):
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e6, k_vent=vent,
               thermo=thermo, volatility=vol)
    v.charge({WATER: 5.0}, phase="liquid")
    if acid:
        v.charge({HYDRONIUM: acid, BISULFATE: acid}, phase="liquid")
    v.charge({amine: 3.0, ACROLEIN: acrolein, NITROBENZENE: nitro},
             phase="liquid")
    return v


def test_the_row_is_three_anilines_and_one_nitrobenzene(net):
    """The stoichiometry is the electron count's, not the catalog row's face."""
    rxn = next(r for r in net.reactions if r.name == "skraup_cyclisation")
    assert rxn.reactants.count(ANILINE) == 3
    assert rxn.reactants.count(ACROLEIN) == 3
    assert rxn.reactants.count(NITROBENZENE) == 1
    assert rxn.products.count(QUINOLINE) == 3
    # ⚠ The aniline on the RIGHT is one molecule, and it is the nitrobenzene.
    assert rxn.products.count(ANILINE) == 1
    assert rxn.products.count(WATER) == 5
    # The acid is on both sides and cancels out of the stoichiometry.
    assert rxn.reactants.count(HYDRONIUM) == 1
    assert rxn.products.count(HYDRONIUM) == 1


def test_the_template_is_seven_slots_in_and_nine_out():
    tmpl = skraup_cyclisation()
    assert tmpl.n_reactant_slots == 8          # 7 + the explicit acid
    assert tmpl._rxn.GetNumProductTemplates() == 10
    assert tmpl.orders == (1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0)
    # Declared orders may never be reversible -- claus_comproportionation's rule.
    assert tmpl.reversible is False
    # Evans-Polanyi off: this is one reaction, not a family being ranked.
    assert tmpl.alpha == 0.0


def test_every_species_it_consumes_keeps_at_least_order_one(net):
    """S11's rule: the kernel has no availability gate, so an order-0 reactant
    keeps reacting after it has run out and is driven negative.

    Read off the CONCRETE reaction rather than the SMARTS, because that is where
    the three amine slots collapse onto one species and the exponents add.
    """
    rxn = next(r for r in net.reactions if r.name == "skraup_cyclisation")
    assert len(rxn.orders) == len(rxn.reactants)
    total: dict[str, float] = {}
    for smi, order in zip(rxn.reactants, rxn.orders):
        total[smi] = total.get(smi, 0.0) + order
    assert total == {
        ANILINE: 1.0, ACROLEIN: 1.0, NITROBENZENE: 1.0, HYDRONIUM: 1.0,
    }
    # Everything the reaction consumes is in there, and none of it is at zero.
    consumed = {s for s in rxn.reactants
                if rxn.reactants.count(s) > rxn.products.count(s)}
    assert consumed == {ANILINE, ACROLEIN, NITROBENZENE}
    assert all(total[s] >= 1.0 for s in consumed)


def test_the_two_standard_states_disagree_on_the_sign_of_dS(net, thermo, vol):
    """⚠⚠ A PHASE LABEL CARRIES A STANDARD STATE, and the easy basis is wrong.

    Seven molecules to nine says dS is positive. That is an ideal-gas statement;
    this template is liquid-phase, nine products condense against seven
    reactants, and the sign flips. Both halves are pinned so the source comment
    cannot rot back to the hand calculation it started as.
    """
    rxn = next(r for r in net.reactions if r.name == "skraup_cyclisation")
    gas_H = sum(thermo.get(s).Hf for s in rxn.products) - sum(
        thermo.get(s).Hf for s in rxn.reactants)
    gas_G = sum(thermo.get(s).Gf for s in rxn.products) - sum(
        thermo.get(s).Gf for s in rxn.reactants)
    gas_S = (gas_H - gas_G) / 298.15 * 1000.0
    dH, dG = reaction_deltas(rxn, thermo, vol)
    dS = (dH - dG) / 298.15 * 1000.0

    assert gas_H == pytest.approx(-561.63, abs=0.5)
    assert gas_S == pytest.approx(36.65, abs=0.5)
    assert gas_S > 0.0

    assert dH == pytest.approx(-725.16, abs=0.5)
    assert dG == pytest.approx(-627.05, abs=0.5)
    assert dS == pytest.approx(-329.08, abs=0.5)
    assert dS < 0.0

    # And irreversible is safe anyway: dG crosses zero at ~2204 K.
    assert dH / dS * 1000.0 == pytest.approx(2204.0, abs=10.0)


def test_it_runs_and_the_oxidant_stoichiometry_is_exact(net, thermo, vol):
    v = _flask(net, thermo, vol)
    v.run(3600.0, **TIGHT)
    st = v.state()
    q = st.total(QUINOLINE)
    assert q == pytest.approx(1.0, abs=1.0e-6)          # acrolein-limited
    assert st.total(ACROLEIN) == pytest.approx(0.0, abs=1.0e-6)
    # One nitrobenzene per THREE quinolines, and two net anilines per three.
    assert st.total(NITROBENZENE) == pytest.approx(1.0 - q / 3.0, abs=1.0e-9)
    assert st.total(ANILINE) == pytest.approx(3.0 - 2.0 * q / 3.0, abs=1.0e-9)
    assert st.total(WATER) == pytest.approx(5.0 + 5.0 * q / 3.0, abs=1.0e-9)
    # The acid is a constant of the motion.
    assert st.total(HYDRONIUM) == pytest.approx(0.2, abs=1.0e-12)
    assert not v.conservation_report()


def test_a_flask_with_no_acid_does_nothing(net, thermo, vol):
    v = _flask(net, thermo, vol, acid=0.0)
    v.run(3600.0, **TIGHT)
    assert v.state().total(QUINOLINE) == 0.0


def test_the_oxidant_is_stoichiometric_and_starving_it_caps_the_yield(
        net, thermo, vol):
    """Three quinolines per nitrobenzene. Below 1/3 mol the acrolein sits there."""
    for nitro in (0.10, 0.20):
        v = _flask(net, thermo, vol, nitro=nitro)
        v.run(3600.0, **TIGHT)
        st = v.state()
        assert st.total(QUINOLINE) == pytest.approx(3.0 * nitro, abs=1.0e-6)
        assert st.total(ACROLEIN) == pytest.approx(1.0 - 3.0 * nitro, abs=1.0e-6)
        assert st.total(NITROBENZENE) == pytest.approx(0.0, abs=1.0e-6)


def test_an_open_flask_loses_its_acrolein_before_it_can_react(net, thermo, vol):
    """⚠ Why the preparation makes its acrolein in situ, measured rather than told.

    Acrolein boils at 314 K and this runs at 450, so a vent is a leak of the
    limiting reagent. Nothing declares that; it is the vapour-pressure curve
    against the vent conductance.
    """
    sealed = _flask(net, thermo, vol, vent=0.0)
    sealed.run(3600.0, **TIGHT)
    open_flask = _flask(net, thermo, vol, vent=1.0e3)
    open_flask.run(3600.0, **TIGHT)
    assert sealed.state().total(QUINOLINE) == pytest.approx(1.0, abs=1.0e-6)
    assert open_flask.state().total(QUINOLINE) < 0.05
    assert open_flask.state().total(QUINOLINE) == pytest.approx(0.0169, abs=2e-3)


def test_a_substituted_aniline_makes_the_parent_quinoline_too(thermo, vol):
    """⚠⚠ THE OXIDANT'S REDUCTION PRODUCT IS ITSELF A SUBSTRATE.

    p-Toluidine alone in the flask, and the network finds 6-methylquinoline AND
    plain quinoline at exactly 2:1 -- because one event in three has to spend the
    aniline the nitrobenzene became. That is a real nuisance of the real
    preparation and nobody declared it.
    """
    net2 = build_network(
        [TOLUIDINE, ACROLEIN, NITROBENZENE, HYDRONIUM, BISULFATE, WATER],
        quinoline_chemistry(), thermo=thermo, volatility=vol,
    )
    assert METHYLQUINOLINE in net2.species
    assert QUINOLINE in net2.species
    assert ANILINE in net2.species

    v = _flask(net2, thermo, vol, amine=TOLUIDINE)
    v.run(3600.0, **TIGHT)
    st = v.state()
    methyl, parent = st.total(METHYLQUINOLINE), st.total(QUINOLINE)
    assert methyl + parent == pytest.approx(1.0, abs=1.0e-6)
    assert methyl == pytest.approx(2.0 / 3.0, abs=1.0e-6)
    assert parent == pytest.approx(1.0 / 3.0, abs=1.0e-6)
    # The aniline is entirely consumed: it never accumulates.
    assert st.total(ANILINE) == pytest.approx(0.0, abs=1.0e-6)
    assert not v.conservation_report()

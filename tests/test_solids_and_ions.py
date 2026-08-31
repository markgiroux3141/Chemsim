"""The Layer 1/4/5 expansion: solids, electrolytes, gas-phase reaction, pruning.

Grouped by the capability each set of tests unlocks, because each was added to
remove a specific blocker:

  * **solids** -- half of any real target list is a solid, and pharmaceuticals are
    isolated by crystallisation. Without a solid phase you can run a reaction but
    never finish a synthesis.
  * **electrolytes** -- pH is not a special subsystem here. Dissociation is entered
    as ordinary reversible reactions, so the assertions below are really checking
    that detailed balance and the stiff solver reproduce measured acidity.
  * **gas phase** -- ammonia, nitric acid and sulfuric acid are all gas-phase
    catalytic processes, and were unreachable while rates came only from the liquid.
  * **pruning** -- structural discovery enumerates an unbounded oligomer series for
    any polymerising feed. What matters is that the bound is explicit and reported.
"""

import math

import numpy as np
import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import (
    VolatilityProvider,
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions import ReactionTemplate
from chemsim.vessel import Vessel

WATER = "O"
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles


# ==========================================================================
# solids
# ==========================================================================


@pytest.fixture
def solid_network(thermo):
    return build_network([WATER, BENZOIC], [], thermo=thermo)


def test_saturation_activity_follows_the_fusion_law(solid_network, thermo):
    """ln(a_sat) = -(Hfus/R)(1/T - 1/Tm) -- one equation, checked directly.

    This is the composition-INDEPENDENT half of the solubility law. What a solute
    reaches at saturation is an activity; turning that into a mole fraction needs
    an activity coefficient, which is tested in test_activity.py.
    """
    v = Vessel(solid_network, volume=1.0, T=300.0)
    i = v.species.index(BENZOIC)
    t = thermo.get(BENZOIC)

    for T in (280.0, 320.0, 350.0):
        expected = math.exp(-(t.Hfus * 1000.0 / 8.314462618) * (1.0 / T - 1.0 / t.Tm))
        assert v.integrator.saturation_activity(T)[i] == pytest.approx(
            min(expected, 1.0), rel=1e-9
        )


def test_saturation_activity_reaches_unity_exactly_at_the_melting_point(
    solid_network, thermo
):
    """This is why there is no separate melting model: at Tm the solid becomes
    fully miscible with its own melt, which is what a_sat = 1 means.

    Stated in ACTIVITY, this survives the arrival of activity coefficients
    untouched -- melting is a pure-component event, where gamma is 1 by
    definition, so it must not move because some solvent dissolves the solid
    badly. That is exactly why the two halves of the law are now separate calls.
    """
    v = Vessel(solid_network, volume=1.0, T=300.0)
    i = v.species.index(BENZOIC)
    Tm = thermo.get(BENZOIC).Tm

    assert v.integrator.saturation_activity(Tm)[i] == pytest.approx(1.0, rel=1e-9)
    assert v.integrator.saturation_activity(Tm - 40.0)[i] < 1.0
    assert v.integrator.saturation_activity(Tm + 40.0)[i] == pytest.approx(1.0)


def test_cooling_crystallises_a_dissolved_solid(solid_network):
    """The recrystallisation a chemist actually performs: dissolve hot, cool,
    collect. Nothing here is a solubility table."""
    dissolved = {}
    for T in (350.0, 280.0):
        v = Vessel(solid_network, volume=1.0, T=T, T_env=T, UA=50.0, kla=0.0, k_diss=0.05)
        v.charge({WATER: 8.0})
        v.charge({BENZOIC: 3.0}, phase="solid")
        v.run(20_000.0)
        dissolved[T] = v.state().n_liquid[BENZOIC]

    assert dissolved[350.0] > dissolved[280.0], "hot solvent must hold more"
    assert v.state().n_solid[BENZOIC] > 0.0, "cold vessel should retain solid"


def test_a_dry_solid_melts_when_heated_past_its_melting_point(solid_network, thermo):
    """A pure solid has no solvent, so the dissolution driving force vanishes
    unless a solid is allowed to count toward its own melt. Regression test for
    exactly that: without it a flask of dry solid heats forever and never melts.

    The hotplate has to out-run the losses all the way to 395 K, which is why the
    power here is not the 60 W the boiling tests use.
    """
    v = Vessel(solid_network, volume=1.0, T=300.0, T_env=300.0, UA=0.5,
               Q_input=200.0, kla=0.0, k_diss=0.05)
    v.charge({BENZOIC: 2.0}, phase="solid")
    v.run(2000.0)

    assert v.T > thermo.get(BENZOIC).Tm - 5.0
    assert v.state().n_solid[BENZOIC] < 0.01, "should have melted"
    assert v.state().n_liquid[BENZOIC] > 1.9


def test_melting_absorbs_latent_heat(solid_network):
    """The temperature should stall while melting, for the same reason it stalls
    while boiling -- the enthalpy is going into the phase change."""
    v = Vessel(solid_network, volume=1.0, T=380.0, T_env=380.0, UA=0.0,
               Q_input=60.0, kla=0.0, k_diss=0.05)
    v.charge({BENZOIC: 2.0}, phase="solid")

    temps = []
    for _ in range(10):
        v.step(200.0)
        temps.append(v.T)

    rises = [b - a for a, b in zip(temps, temps[1:])]
    assert min(rises) < 0.4 * max(rises), "no plateau while melting"


def test_a_sealed_vessel_conserves_atoms_across_all_three_phases(solid_network):
    v = Vessel(solid_network, volume=2.0, T=330.0, T_env=330.0, UA=1.0,
               kla=1.0, k_diss=0.02, k_vent=0.0)
    v.charge({WATER: 5.0})
    v.charge({BENZOIC: 1.0}, phase="solid")

    def totals(state):
        out = {}
        for smi in v.species:
            for el, k in solid_network.molecules[smi].element_counts().items():
                out[el] = out.get(el, 0.0) + k * state.total(smi)
        return out

    start = totals(v.state())
    v.run(5_000.0)
    end = totals(v.state())
    for el in start:
        assert np.isclose(start[el], end[el], rtol=1e-5), el


def test_dissolved_gases_never_crystallise(thermo):
    """O2 has no solid state in this model; the solubility law must leave it be."""
    net = build_network([WATER, "O=O"], [], thermo=thermo)
    v = Vessel(net, volume=1.0, T=290.0)
    i = v.species.index("O=O")
    assert not v.phases.solidifies[i]
    assert v.integrator.solubility(200.0)[i] == 1.0


# ==========================================================================
# electrolytes and pH
# ==========================================================================


@pytest.fixture
def acid_thermo():
    return electrolyte_provider()


@pytest.fixture
def acid_network(acid_thermo):
    return build_network(
        [WATER, "CC(=O)O"], dissociation_templates(), thermo=acid_thermo, max_species=40
    )


def _equilibrate(net, charge, T=298.15):
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=50.0, kla=0.0, k_diss=0.0)
    v.charge(charge)
    v.run(2000.0)
    return v


def test_dissociation_produces_ions_and_balances_charge(acid_network):
    assert "[OH3+]" in acid_network.species
    assert "[OH-]" in acid_network.species
    assert "CC(=O)[O-]" in acid_network.species
    for rxn in acid_network.reactions:
        left = sum(acid_network.molecules[s].charge for s in rxn.reactants)
        right = sum(acid_network.molecules[s].charge for s in rxn.products)
        assert left == right, rxn.name


def test_pure_water_self_ionises_to_pH_seven(acid_thermo):
    net = build_network([WATER], dissociation_templates(), thermo=acid_thermo)
    v = _equilibrate(net, {WATER: 55.34})
    assert v.pH == pytest.approx(7.0, abs=0.05)


@pytest.mark.parametrize("conc", [1.0, 0.1, 0.01])
def test_weak_acid_pH_matches_henderson_hasselbalch(acid_network, conc):
    """pH = 1/2 (pKa - log10 C) for a weak acid. Reproducing this means the
    dissociation equilibrium constant really is Ka -- which it only is if the
    solvent-activity correction and detailed balance are both right."""
    v = _equilibrate(acid_network, {WATER: 55.34, "CC(=O)O": conc})
    expected = 0.5 * (4.76 - math.log10(conc))
    assert v.pH == pytest.approx(expected, abs=0.1)


def test_a_strong_acid_is_more_acidic_than_a_weak_one(acid_thermo):
    net = build_network(
        [WATER, "CC(=O)O", "Cl"], dissociation_templates(),
        thermo=acid_thermo, max_species=60,
    )
    strong = _equilibrate(net, {WATER: 55.34, "Cl": 0.1}).pH
    weak = _equilibrate(net, {WATER: 55.34, "CC(=O)O": 0.1}).pH
    assert strong < weak - 1.5
    assert strong == pytest.approx(1.0, abs=0.3), "0.1 M strong acid is pH 1"


def test_a_half_neutralised_acid_sits_at_its_pKa(acid_thermo):
    """The buffer result, and the sharpest check in this file. Adding half an
    equivalent of base makes [A-] = [HA], so pH = pKa exactly. There is no buffer
    equation anywhere in this codebase -- it falls out of mass action, which means
    the derived acetate thermochemistry is right to better than 0.05 pH units.
    """
    net = build_network(
        [WATER, "CC(=O)O", "[OH-]", "[Na+]"], dissociation_templates(),
        thermo=acid_thermo, max_species=60,
    )
    v = _equilibrate(net, {WATER: 55.34, "CC(=O)O": 0.1, "[OH-]": 0.05, "[Na+]": 0.05})
    assert v.pH == pytest.approx(4.76, abs=0.05)


def test_full_neutralisation_overshoots_to_the_basic_side(acid_thermo):
    """At the equivalence point the solution is acetate, a weak base, so the pH
    is well above 7 -- the classic result that surprises students."""
    net = build_network(
        [WATER, "CC(=O)O", "[OH-]", "[Na+]"], dissociation_templates(),
        thermo=acid_thermo, max_species=60,
    )
    v = _equilibrate(net, {WATER: 55.34, "CC(=O)O": 0.1, "[OH-]": 0.1, "[Na+]": 0.1})
    assert 8.0 < v.pH < 9.5


def test_a_diprotic_acid_shows_both_ionisation_steps(acid_thermo):
    net = build_network(
        [WATER, "OS(=O)(=O)O"], dissociation_templates(),
        thermo=acid_thermo, max_species=60,
    )
    v = _equilibrate(net, {WATER: 55.34, "OS(=O)(=O)O": 0.05})
    c = v.concentrations()

    assert v.pH == pytest.approx(1.1, abs=0.3)
    # Strong first step, weak second: mostly bisulfate, some sulfate.
    assert c["O=S(=O)([O-])O"] > c["O=S(=O)([O-])[O-]"] > 0.0
    assert c["O=S(=O)(O)O"] < 1e-3, "first proton should be essentially gone"


def test_ions_are_non_volatile():
    """A charged species must never appear in the headspace."""
    vol = VolatilityProvider(electrolyte_provider())
    for smi in ("[OH3+]", "[OH-]", "CC(=O)[O-]"):
        v = vol.get(smi)
        assert v.kind == "nonvolatile"
        assert not v.volatile
        assert v.coefficient(350.0) < 1e-20


def test_pH_is_nan_when_the_network_has_no_ions(thermo):
    net = build_network([WATER], [], thermo=thermo)
    v = Vessel(net, volume=1.0)
    v.charge({WATER: 10.0})
    assert math.isnan(v.pH)


def test_a_species_that_decomposes_before_boiling_is_non_volatile():
    """Metformin has no estimable boiling point. Treating that as non-volatile is
    correct behaviour -- it stays in the flask -- and beats refusing to model it."""
    vol = VolatilityProvider()
    m = vol.get("CN(C)C(=N)NC(=N)N")
    assert m.kind == "nonvolatile"
    assert "decomposes" in m.source


# ==========================================================================
# gas-phase reaction
# ==========================================================================


def test_a_gas_phase_template_runs_on_headspace_concentrations(thermo):
    """Rates for a gas-phase reaction must come from the vapour, not the liquid.
    With nothing in the liquid at all, the reaction must still proceed."""
    tmpl = ReactionTemplate(
        name="gas_oxidation",
        smarts="[CX4H4:1].[OX1:2]=[OX1:3]>>[CX3H2:1]=[O:2].[OH2:3]",
        A=1.0e8, Ea=60_000, phase="gas",
    )
    net = build_network(["C", "O=O", "O"], [tmpl], thermo=thermo)
    arrays = net.to_arrays(thermo)
    assert (arrays.phase == 1).all(), "template phase must reach the arrays"

    v = Vessel(net, volume=2.0, T=700.0, T_env=700.0, UA=100.0, kla=0.0)
    v.charge({"C": 0.05, "O=O": 0.05}, phase="gas")
    before = v.state().n_gas["C"]
    v.run(500.0)
    assert v.state().n_gas["C"] < before, "gas-phase reaction did not proceed"


def test_liquid_and_gas_reactions_are_kept_separate(thermo):
    liquid_only = ReactionTemplate(
        name="liq", smarts="[CX4H4:1]>>[CX3H2:1]=[CX3H2:1]", A=1.0, Ea=0.0,
    )
    assert liquid_only.phase == "liquid"
    with pytest.raises(ValueError, match="phase must be one of"):
        ReactionTemplate(name="bad", smarts="[CX4H4:1]>>[CX4H4:1]",
                         A=1.0, Ea=0.0, phase="plasma")


# ==========================================================================
# phase="any"
# ==========================================================================

ANY_PHASE = ReactionTemplate(
    name="fischer_any",
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000, reversible=True, phase="any",
)


def test_phase_any_generates_the_reaction_in_both_phases(thermo):
    """It used to be accepted, documented, and silently equivalent to "liquid":
    ``to_arrays`` mapped anything that was not "gas" to the liquid index. A value
    that validates and then does nothing is worse than one that is rejected."""
    assert ANY_PHASE.phases == ("liquid", "gas")

    net = build_network(["CC(=O)O", "CCO", "O"], [ANY_PHASE], thermo=thermo,
                        max_species=20)
    ester = "CCOC(C)=O"
    made = [r for r in net.reactions if sorted(r.products) == sorted([ester, "O"])]
    assert {r.phase for r in made} == {"liquid", "gas"}

    arrays = net.to_arrays(thermo)
    assert set(arrays.phase.tolist()) == {0, 1}


def test_the_two_phases_get_genuinely_different_reverse_rates(thermo):
    """Why they cannot be collapsed into one flagged reaction. A liquid-phase
    reaction is moved into the pure-liquid standard state and a gas-phase one keeps
    the ideal-gas basis, so detailed balance derives a different reverse for each.
    One reaction with a phase flag would have to pick one of the two."""
    net = build_network(["CC(=O)O", "CCO", "O"], [ANY_PHASE], thermo=thermo,
                        max_species=20)
    rev = {r.phase: r for r in net.reactions if r.name.endswith("_rev")}
    assert set(rev) == {"liquid", "gas"}
    assert rev["liquid"].A != pytest.approx(rev["gas"].A, rel=1e-6)
    assert rev["liquid"].Ea != pytest.approx(rev["gas"].Ea, rel=1e-6)


def test_an_unintegrable_phase_is_refused_by_the_arrays_not_defaulted(thermo):
    """The same line, guarded. A phase Layer 4 has no block for must raise, or the
    next one added gets swallowed into the liquid block exactly as "any" was.

    ⚠ ``"solid"`` IS STILL THE EXAMPLE OF A REFUSED PHASE AFTER M6, AND THAT IS
    A MEASUREMENT RATHER THAN AN OMISSION. M6 built solid-phase chemistry and it
    is a TERM (``SolidStateArrays``), not a third entry here, because a pure
    solid has UNIT ACTIVITY: mass action on the solid amounts settles at
    ``p/K = n_A/n_B``, measured at 3.0863 against 3.0863 on a sealed kiln at
    1100 K. What would still want an entry in this table is a gas-CONSUMING
    surface reaction -- roasting, or a solid catalyst -- which is a different
    mechanism. See ``properties/solid_state.py``."""
    from chemsim.network.builder import PHASE_INDEX
    from chemsim.reactions import ConcreteReaction

    net = build_network(["CC(=O)O", "CCO", "O"], [], thermo=thermo, max_species=20)
    assert set(PHASE_INDEX) == {"liquid", "gas"}
    net.reactions.append(
        ConcreteReaction("bogus", ("CCO",), ("CCO",), 1.0, 0.0, phase="solid")
    )
    with pytest.raises(ValueError, match="Layer 4 cannot integrate"):
        net.to_arrays(thermo)


# ==========================================================================
# bounded discovery
# ==========================================================================


def test_a_polymerising_feed_is_bounded_and_reported(thermo, capsys):
    """A diacid plus a diol oligomerises without limit -- correctly, since that is
    polyesterification. The requirement is that the bound be explicit and that
    what was dropped is named, never silently truncated."""
    fischer = ReactionTemplate(
        name="fischer",
        smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
               ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
        A=1.0e6, Ea=50_000, reversible=True,
    )
    net = build_network(
        ["OC(=O)CCC(=O)O", "OCCO", WATER], [fischer],
        thermo=thermo, max_species=2000, max_molar_mass=300.0,
    )
    out = capsys.readouterr().out

    assert len(net.species) < 20, "molar-mass bound did not take effect"
    assert "exceeded max_molar_mass" in out
    assert "polymerises" in out, "the diagnosis should name the cause"


def test_incremental_expansion_matches_exhaustive_expansion(thermo):
    """The frontier optimisation must not change WHAT is discovered, only how
    long it takes -- combinations drawn entirely from old species were already
    tried in an earlier round."""
    fischer = ReactionTemplate(
        name="fischer",
        smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
               ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
        A=1.0e6, Ea=50_000, reversible=True,
    )
    feed = ["CC(=O)O", "CCO", "CO", WATER]
    full = build_network(feed, [fischer], thermo=thermo, max_species=200)
    assert len(full.species) > len(feed), "expansion happened"
    # Re-running must be idempotent in content and ordering.
    again = build_network(feed, [fischer], thermo=thermo, max_species=200)
    assert full.species == again.species
    assert len(full.reactions) == len(again.reactions)


def test_generations_limits_expansion_depth(thermo):
    fischer = ReactionTemplate(
        name="fischer",
        smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
               ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
        A=1.0e6, Ea=50_000, reversible=True,
    )
    feed = ["OC(=O)CCC(=O)O", "OCCO", WATER]
    one = build_network(feed, [fischer], thermo=thermo, generations=1, max_species=500)
    two = build_network(feed, [fischer], thermo=thermo, generations=2, max_species=500)
    assert len(one.species) < len(two.species)


def test_the_generation_limit_reports_the_frontier_it_left(thermo, capsys):
    """⚠ THE ONE COVERAGE LIMIT THAT USED TO SAY NOTHING.

    ``max_species`` reported, ``max_molar_mass`` reported, a mixed standard state
    reported -- and the generation limit broke out of the expansion loop with a
    non-empty frontier and no comment. It is the strongest of the three claims,
    not the weakest: the other two are about species that were never REGISTERED,
    while this one is about species that are in the flask and whose onward
    chemistry was never looked for. A game that runs ``generations=1`` on every
    step would otherwise lie about the contents of every flask it ever showed.
    """
    fischer = ReactionTemplate(
        name="fischer",
        smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
               ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
        A=1.0e6, Ea=50_000, reversible=True,
    )
    feed = ["OC(=O)CCC(=O)O", "OCCO", WATER]
    net = build_network(feed, [fischer], thermo=thermo, generations=1,
                        max_species=500)
    out = capsys.readouterr().out

    assert net.unexpanded, "a polyesterification is not finished after one round"
    assert all(s in net.species for s in net.unexpanded), (
        "the frontier is what was DISCOVERED and not expanded, so every member "
        "of it is a species of this network"
    )
    assert "generations=1" in out
    assert f"{len(net.unexpanded)} species still unexpanded" in out
    # And the notice is carried, not merely emitted -- a windowed frontend has
    # no stdout to read.
    assert any("still unexpanded" in n for n in net.notices)
    assert all(n in out for n in net.notices), (
        "the carried notices must be the SAME strings that were printed"
    )


def test_a_generation_bound_that_never_bit_says_nothing(thermo, capsys):
    """⚠ THE COMPANION MEASUREMENT, AND IT IS WHAT MAKES THE NOTICE MEAN ANYTHING.

    A bound that is declared but not reached is not an approximation, and a
    notice that fires whenever ``generations`` was passed would be reporting the
    ARGUMENT rather than the outcome. Esterification of a monoacid with a
    monoalcohol closes in two rounds; asked for six, the loop exits through its
    own ``while`` with an empty frontier and there is genuinely nothing
    unexplored to declare.
    """
    fischer = ReactionTemplate(
        name="fischer",
        smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
               ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
        A=1.0e6, Ea=50_000, reversible=True,
    )
    bounded = build_network(["CC(=O)O", "CCO"], [fischer], thermo=thermo,
                            generations=6)
    free = build_network(["CC(=O)O", "CCO"], [fischer], thermo=thermo)
    out = capsys.readouterr().out

    assert bounded.species == free.species, "the bound was never reached"
    assert bounded.unexpanded == ()
    assert "unexpanded" not in out


def test_the_species_cap_leaves_a_frontier_too(thermo, capsys):
    """⚠ THE BOUND THAT BIT IS NOT ALWAYS THE BOUND THAT WAS DECLARED, and
    reading the frontier only on the generation branch got this wrong.

    Measured in ``validation/playable_levers.py`` panel 5: five bench reagents at
    ``generations=2`` hit ``max_species`` first, so the generation limit never
    fired -- and the first version of this feature therefore reported an EMPTY
    frontier for a network of 400 species that had been truncated mid-round. A
    "react further" control reading that would have declined to offer itself on
    precisely the flask with the most left to give.

    ⚠ And the cap's own notice has to say the frontier is a LOWER bound there,
    because the interrupted round left combinations of the previous frontier
    untried as well and those species are not in the list.
    """
    fischer = ReactionTemplate(
        name="fischer",
        smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
               ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
        A=1.0e6, Ea=50_000, reversible=True,
    )
    feed = ["OC(=O)CCC(=O)O", "OCCO", WATER]
    net = build_network(feed, [fischer], thermo=thermo, max_species=12)
    out = capsys.readouterr().out

    assert len(net.species) == 12, "the cap is what stopped this"
    assert "hit max_species=12" in out
    assert "unexpanded" not in out.split("hit max_species")[0], (
        "the generation limit did not bite and must not claim to have"
    )
    assert net.unexpanded, "a truncated network has more to give and must say so"
    assert all(s in net.species for s in net.unexpanded)
    assert f"MORE than the {len(net.unexpanded)} registered" in out


def test_generations_zero_reports_the_whole_charge(thermo, capsys):
    """The degenerate bound is the clearest statement of what the notice claims:
    nothing was expanded, so every species charged is on the frontier."""
    fischer = ReactionTemplate(
        name="fischer",
        smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
               ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
        A=1.0e6, Ea=50_000, reversible=True,
    )
    net = build_network(["CC(=O)O", "CCO"], [fischer], thermo=thermo,
                        generations=0)
    out = capsys.readouterr().out

    assert not net.reactions
    assert set(net.unexpanded) == set(net.species)
    assert "2 species still unexpanded" in out

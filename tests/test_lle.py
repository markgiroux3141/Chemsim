"""Liquid-liquid equilibrium: does a flask know when it holds two layers?

The claim being tested is not "two blocks of state exist". It is that the
SEPARATION and everything that follows from it are consequences of the activity
model this project already had, not of a table saying which solvents mix:

  * which pairs split, and which do not;
  * which layer ends up on the bottom (from computed densities, so swapping the
    solvent swaps the layers);
  * how a solute divides between them, and therefore why three small washes beat
    one big one;
  * that two immiscible liquids boil BELOW either of them.

And the guard that matters most: **with one liquid phase, every number this
project has ever measured has to be unchanged.** The second block is not a
refactor of the first, it is an addition that must vanish when it is empty.
"""

import numpy as np
import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties.electrolyte import electrolyte_provider
from chemsim.numerics.lle import (
    IDEAL_FRACTION_REPORT,
    IDEAL_TIE_LINE_SENSITIVITY,
    stability_test,
)
from chemsim.properties import ThermochemistryProvider, UnifacProvider, build_activity_arrays
from chemsim.vessel import Vessel

WATER, ETOH = "O", "CCO"
TOLUENE = Molecule.from_smiles("Cc1ccccc1").smiles
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
DCM = Molecule.from_smiles("ClCCl").smiles
HEXANE = "CCCCCC"


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def net(thermo):
    return build_network(
        [WATER, TOLUENE, BENZOIC, ETOH], [], thermo=thermo, max_species=20
    )


@pytest.fixture(scope="module")
def dense_net(thermo):
    return build_network([WATER, DCM, BENZOIC], [], thermo=thermo, max_species=20)


def funnel(net, volume=2.0, T=298.15, **kw):
    return Vessel(net, volume=volume, T=T, T_env=T, UA=50.0, kla=0.0,
                  k_diss=0.0, k_vent=0.0, **kw)


# ---------------------------------------------------------------------------
# the test itself, before any vessel is involved
# ---------------------------------------------------------------------------


def test_the_stability_test_knows_which_liquids_are_immiscible():
    """Tangent-plane distance over the pairs, straight from UNIFAC. No table of
    miscibilities exists in this project and none was added."""
    prov = UnifacProvider()

    def unstable(species, amounts):
        arr = build_activity_arrays(species, prov)
        return stability_test(
            np.array(amounts, float), arr.nu, arr.R_k, arr.Q_k, arr.a_mn,
            arr.active, 298.15,
        ).unstable

    assert unstable([WATER, TOLUENE], [0.5, 0.5])
    assert unstable([WATER, HEXANE], [0.5, 0.5])
    assert unstable([WATER, "c1ccccc1"], [0.5, 0.5])
    # ... and the ones that do NOT split, which is the half that protects the
    # existing invariants: an ethanol/water azeotrope must never become a
    # two-layer system.
    assert not unstable([WATER, ETOH], [0.5, 0.5])
    assert not unstable([WATER, "CC(C)=O"], [0.5, 0.5])
    assert not unstable([TOLUENE, "c1ccccc1"], [0.5, 0.5])


def test_a_dilute_solution_does_not_split(thermo):
    """Below the solubility limit there is only one phase, and the test has to
    say so -- otherwise every trace of an organic in water would separate."""
    prov = UnifacProvider()
    arr = build_activity_arrays([WATER, TOLUENE], prov)
    dilute = stability_test(
        np.array([0.9999, 0.0001]), arr.nu, arr.R_k, arr.Q_k, arr.a_mn,
        arr.active, 298.15,
    )
    assert not dilute.unstable


def test_an_ideal_liquid_never_splits(thermo):
    """With no group parameters every gamma is 1, so the tangent plane is flat
    and nothing is unstable. Not a special case in the code -- it is what the
    equations give, and it means a network outside the UNIFAC table cannot
    invent a phase separation."""
    n = 3
    result = stability_test(
        np.array([0.4, 0.3, 0.3]), np.zeros((n, 0)), np.zeros(0), np.zeros(0),
        np.zeros((0, 0, 3)), np.ones(n, dtype=bool), 298.15,
    )
    assert not result.unstable
    assert result.tm == 0.0


# ---------------------------------------------------------------------------
# a flask with two layers in it
# ---------------------------------------------------------------------------


def test_water_and_toluene_separate_with_the_right_densities(net):
    v = funnel(net)
    v.charge({WATER: 27.7, TOLUENE: 4.7})       # ~500 mL of each
    assert not v.two_phase, "nothing has happened yet"
    v.run(600.0)

    assert v.two_phase
    layers = v.layers()
    assert len(layers) == 2
    light, heavy = layers                        # sorted lightest first
    assert light["composition"][TOLUENE] > 0.95
    assert heavy["composition"][WATER] > 0.95
    # Real densities: toluene 0.867, water 0.997 kg/L. Nothing tabulates these
    # -- they come out of the molar masses and the Rackett molar volumes the
    # RHS is already integrating.
    assert light["density"] == pytest.approx(0.867, abs=0.03)
    assert heavy["density"] == pytest.approx(0.997, abs=0.03)


def test_which_layer_is_on_the_bottom_is_computed_not_declared(net, dense_net):
    """The point of deriving the density: an ether extraction has the organic
    layer on top and a dichloromethane one has it underneath, and neither is
    special-cased. ``pour_into(phase="lower")`` means the same thing in both."""
    light = funnel(net)
    light.charge({WATER: 27.7, TOLUENE: 4.7})
    light.run(600.0)

    heavy = funnel(dense_net)
    heavy.charge({WATER: 27.7, DCM: 7.8})        # ~500 mL of DCM
    heavy.run(600.0)

    def lower_layer_is_organic(v, organic):
        drained = funnel(v.network)
        v.pour_into(drained, phase="lower")
        st = drained.state()
        return st.liquid_total(organic) > st.liquid_total(WATER)

    assert not lower_layer_is_organic(light, TOLUENE), "toluene floats"
    assert lower_layer_is_organic(heavy, DCM), "dichloromethane sinks"


def test_conservation_survives_a_phase_split(net):
    """The split is a redistribution, never a source. Both the seeding at the
    boundary and the flux in the RHS are antisymmetric, so every species' total
    is untouched by either."""
    v = funnel(net)
    charged = {WATER: 27.7, TOLUENE: 4.7, BENZOIC: 0.02}
    v.charge(charged)
    v.run(900.0)

    for species, amount in charged.items():
        assert v.state().total(species) == pytest.approx(amount, abs=1e-9), species


def test_adding_a_cosolvent_merges_the_layers_again(net):
    """Two layers are not a latch. Enough ethanol makes water and toluene one
    phase, and the vessel has to notice -- otherwise a phantom second layer
    would sit there and a separatory funnel would happily drain it."""
    v = funnel(net, volume=6.0)
    v.charge({WATER: 5.0, TOLUENE: 1.0})
    v.run(600.0)
    assert v.two_phase

    v.charge({ETOH: 40.0})                       # a lot of co-solvent
    v.run(600.0)
    assert not v.two_phase, v.lle_report()


# ---------------------------------------------------------------------------
# what a two-layer flask is FOR
# ---------------------------------------------------------------------------


def test_a_solute_partitions_between_the_layers(net):
    """The distribution coefficient is not tabulated anywhere. It is whatever
    equality of activity produces, and benzoic acid prefers toluene."""
    v = funnel(net)
    v.charge({WATER: 27.7, TOLUENE: 4.7, BENZOIC: 0.02})
    v.run(900.0)

    assert v.two_phase
    # partition() is layer0/layer1 by concentration; layer 0 is the water it was
    # charged into, so a number well below 1 means the acid went organic.
    assert v.partition(BENZOIC) < 0.5
    aq = v.layers()[-1]                          # densest = aqueous
    org = v.layers()[0]
    assert org["composition"][BENZOIC] > 5.0 * aq["composition"].get(BENZOIC, 0.0)


def test_three_small_washes_beat_one_big_one(net):
    """The classic result, and nothing here knows it.

    Extraction efficiency compounds: each contact removes the same FRACTION, so
    n portions of V/n beat one portion of V. It falls out of the partition
    equilibrium being re-established every time fresh solvent arrives, which is
    the whole reason a chemist extracts three times.
    """
    def extract(portions: int, total_toluene: float) -> float:
        aq = funnel(net, volume=4.0)
        aq.charge({WATER: 27.7, BENZOIC: 0.02})
        combined = funnel(net, volume=4.0)
        for _ in range(portions):
            aq.charge({TOLUENE: total_toluene / portions})
            aq.run(600.0)
            if aq.two_phase:
                aq.pour_into(combined, phase="upper")
        return combined.state().total(BENZOIC)

    one = extract(1, 3.0)
    three = extract(3, 3.0)
    assert one > 0.0, "a single extraction must recover something"
    assert three > one, f"three portions {three} should beat one {one}"


def test_shaking_the_funnel_is_what_equilibrates_it(net):
    """``k_lle`` is agitation, not a numerical constant. A funnel that is barely
    swirled has not reached partition equilibrium when you drain it, and that is
    a mistake a player should be able to make."""
    def extracted(k_lle: float) -> float:
        v = funnel(net, k_lle=k_lle)
        v.charge({WATER: 27.7, TOLUENE: 4.7, BENZOIC: 0.02})
        v.run(60.0)                              # a short contact time
        if not v.two_phase:
            return 0.0
        organic = funnel(net)
        v.pour_into(organic, phase="upper")
        return organic.state().total(BENZOIC)

    assert extracted(5.0) > extracted(0.02)


def test_two_immiscible_liquids_boil_below_either_of_them(net, thermo):
    """Steam distillation, and it is not modelled anywhere.

    Each layer is nearly pure in its own component, so each contributes close to
    its FULL vapour pressure to the same headspace; the total therefore reaches
    ambient before either component's own boiling point. That is the whole basis
    of steam distillation -- it is how you distil something that would decompose
    at its own boiling point.

    ⚠ The flask is HEATED rather than asked for its ``bubble_point``, and the
    difference matters. A bubble point scans temperature at frozen composition,
    so the two layers drift off their tie line as the scan moves and the answer
    reads several kelvin high. Heating it for real lets the layers re-equilibrate
    as they warm, which is what a flask does.
    """
    def boils_at(charge: dict) -> float:
        # Stop at the PLATEAU -- where latent heat balances the hotplate -- not
        # after a fixed time. Running on boils the flask dry, and a dry
        # superheated flask is a pre-existing robustness limit (it reproduces
        # with lle=False) as well as not being a boiling point.
        v = Vessel(net, volume=2.0, T=298.15, T_env=298.15, UA=0.0,
                   Q_input=120.0, kla=5.0, k_diss=0.0)
        v.charge(charge)
        last = v.T
        for _ in range(40):
            v.step(100.0)
            if v.is_boiling and abs(v.T - last) < 0.02:
                return v.T
            last = v.T
        return v.T

    mixed = boils_at({WATER: 27.7, TOLUENE: 4.7})
    water = boils_at({WATER: 27.7})
    toluene = boils_at({TOLUENE: 4.7})

    assert mixed < water - 5.0, f"mixed {mixed} vs water {water}"
    assert mixed < toluene - 5.0, f"mixed {mixed} vs toluene {toluene}"
    # Measured: water/toluene co-distils at ~84 C = 357.3 K, water alone at
    # 373.1 and toluene alone at 383.8.
    assert 350.0 < mixed < 365.0, mixed


# ---------------------------------------------------------------------------
# the guard: one phase must be exactly what it always was
# ---------------------------------------------------------------------------


def test_turning_lle_off_reproduces_a_single_phase_and_says_so(net):
    """``lle=False`` is an escape hatch, not a lie. The liquid is held as one
    phase AND the vessel reports that it wanted to split -- a silently
    single-phase extraction is precisely the confident wrong answer this
    project refuses to give."""
    v = funnel(net, lle=False)
    v.charge({WATER: 27.7, TOLUENE: 4.7})
    v.run(600.0)

    assert not v.two_phase
    report = v.lle_report()
    assert "UNSTABLE as one phase" in report
    assert "lle=False" in report
    assert np.isnan(v.partition(TOLUENE))


def test_an_electrolyte_splits_now_with_the_salt_left_in_the_water(thermo):
    """⚠ THIS TEST USED TO ASSERT THE OPPOSITE, and the change is the point.

    An electrolyte was refused a split outright, because an ion held at gamma = 1
    partitions to EQUAL MOLE FRACTION between water and toluene -- so splitting a
    brine invented a strongly ionic organic phase and ran aqueous-anchored
    dissociation inside it. The refusal was the honest answer available at the
    time. It has been REPLACED by a better one rather than relaxed: the Born
    transfer term prices what it costs a charge to leave the water (see
    ``properties/dielectric`` and ``tests/test_born.py``).

    What is checked here is the LLE consequence only -- that the funnel separates,
    and that the salt does not go with the toluene. The model itself is pinned in
    ``test_born.py``; keeping the two apart means a future change to the ion model
    breaks the model's tests rather than quietly re-labelling this one.
    """
    # The ELECTROLYTE provider: the plain one refuses a chloride ion, because
    # Joback prices it 101 kJ/mol away from the value the ion table derives from
    # HCl's pKa (see properties/element_data and the guard in thermochemistry).
    net = build_network(
        [WATER, TOLUENE, "[Na+]", "[Cl-]"], [],
        thermo=electrolyte_provider(), max_species=20
    )
    v = funnel(net)
    v.charge({WATER: 27.7, TOLUENE: 4.7, "[Na+]": 0.5, "[Cl-]": 0.5})
    v.run(600.0)

    assert v.two_phase, "an electrolyte may be two layers now"
    st = v.state()
    for ion in ("[Na+]", "[Cl-]"):
        assert st.n_liquid[ion] > 0.4999, f"{ion} left the aqueous layer"
        assert st.n_liquid2[ion] < 1.0e-5, f"{ion} got into the toluene"
    # The refusal must not have been replaced by silence either: the report says
    # what the layers ARE.
    assert "two liquid layers" in v.lle_report()

    # ... and the identical system without the salt still splits, so nothing about
    # the solvent pair was disturbed on the way.
    clean = funnel(net)
    clean.charge({WATER: 27.7, TOLUENE: 4.7})
    clean.run(600.0)
    assert clean.two_phase


def test_a_miscible_liquid_is_untouched_by_any_of_this(thermo):
    """The ethanol/water system carries several of this project's invariants
    (the azeotrope, the still, the reflux pot). It must not acquire a second
    phase, and the report must stay empty rather than merely harmless."""
    net = build_network([ETOH, WATER, "N#N", "O=O"], [], thermo=thermo)
    v = Vessel(net, volume=1.0, T=298.15, T_env=298.15, UA=0.5, Q_input=60.0,
               kla=5.0)
    v.charge({ETOH: 3.0, WATER: 3.0})
    v.fill_headspace_with_air()
    v.run(1200.0)

    assert not v.two_phase
    assert v.lle_report() == ""
    assert sum(v.state().n_liquid2.values()) == 0.0


# ---------------------------------------------------------------------------
# the species that were never modelled at all
# ---------------------------------------------------------------------------
# ⚠ THE ERROR THESE TESTS ARE ABOUT IS ONE-DIRECTIONAL, which is why silence was
# the wrong default. A neutral species with no UNIFAC decomposition is held at
# gamma = 1; an ideal liquid never splits; so everything held ideal argues for
# ONE PHASE and for two layers being more alike than they are. The missing model
# does not add noise around the right answer, it leans on the verdict.

SULFURIC = Molecule.from_smiles("OS(=O)(=O)O").smiles


def test_the_flag_is_bounded_by_arithmetic_not_chosen():
    """The threshold is a reporting decision derived from a measured slope, and
    the derivation is pinned here so a later edit has to redo it rather than
    nudge a number: it is the ideal mole fraction at which the worst measured
    sensitivity moves a layer composition by 0.01, one unit in the last digit
    ``lle_report`` prints."""
    assert IDEAL_FRACTION_REPORT * IDEAL_TIE_LINE_SENSITIVITY == pytest.approx(
        0.01, rel=0.05
    )


def test_holding_one_species_ideal_really_does_move_the_tie_line():
    """⚠ AND THE SLOPE IS NOT A GUESS EITHER. The measurement behind
    ``IDEAL_TIE_LINE_SENSITIVITY``, reduced to its one worst case: a hydrocarbon
    at 5% of a water/toluene mixture, held ideal, drags the organic layer's
    composition by far more than its own mole fraction -- because it is not
    merely given the wrong gamma, it is dropped out of the group composition
    every other species' gamma is computed against, so the species that should
    DEFINE that layer is kept out of it."""
    prov = UnifacProvider()
    species = [WATER, TOLUENE, "CCCCCCC"]
    arr = build_activity_arrays(species, prov)
    amounts = np.array([0.7125, 0.2375, 0.05])

    truth = stability_test(
        amounts, arr.nu, arr.R_k, arr.Q_k, arr.a_mn, arr.active, 298.15
    )
    ideal_mask = arr.active.copy()
    ideal_mask[2] = False
    lie = stability_test(
        amounts, arr.nu, arr.R_k, arr.Q_k, arr.a_mn, ideal_mask, 298.15
    )

    assert truth.unstable and lie.unstable
    moved = 0.5 * float(np.abs(truth.composition - lie.composition).sum())
    assert moved > 0.05, "5% held ideal moved the tie line by less than 0.05"
    # ... and it moved by more than the amount held ideal, which is the point:
    # the error is not bounded by the size of the omission.
    assert moved > 0.05 * 1.0


def test_a_stable_liquid_with_an_unmodelled_species_is_NOT_silent(thermo):
    """⚠ THE CASE THE WHOLE FLAG EXISTS FOR, and the only one where the empty
    string was itself the wrong answer.

    Sulfuric acid has no UNIFAC decomposition -- the 1975 table has no group for
    a sulfate's S(=O)(=O) -- so 14% of this liquid enters the tangent-plane test
    with an activity coefficient that was never computed. The test duly reports
    one stable phase. That verdict is the one an ideal species was always going
    to produce, and returning "" for it made a foregone conclusion look like a
    finding."""
    net = build_network([WATER, SULFURIC], [], thermo=thermo, max_species=20)
    v = funnel(net)
    v.charge({WATER: 30.0, SULFURIC: 5.0})
    v.run(600.0)

    assert not v.two_phase
    report = v.lle_report()
    assert "stable as one phase" in report
    assert "held at gamma = 1" in report
    assert "never splits" in report
    assert SULFURIC in report

    fraction, named = v.held_ideal()
    assert fraction == pytest.approx(5.0 / 35.0, rel=1e-9)
    assert list(named) == [SULFURIC]


def test_the_flag_is_weighted_by_amount_and_not_by_presence(thermo):
    """gamma = 1 on a trace changes nothing and must not be reported as though
    it did -- a warning that fires on every flask is a warning nobody reads. The
    same species at the same threshold, at two amounts."""
    net = build_network([WATER, SULFURIC], [], thermo=thermo, max_species=20)

    trace = funnel(net)
    trace.charge({WATER: 30.0, SULFURIC: 0.02})
    trace.run(600.0)
    assert trace.held_ideal()[0] < IDEAL_FRACTION_REPORT
    assert trace.lle_report() == ""

    enough = funnel(net)
    enough.charge({WATER: 30.0, SULFURIC: 0.2})
    enough.run(600.0)
    assert enough.held_ideal()[0] > IDEAL_FRACTION_REPORT
    assert "held at gamma = 1" in enough.lle_report()


def test_an_ION_is_not_counted_as_held_ideal(thermo):
    """⚠ TWO DIFFERENT THINGS WEAR gamma = 1 AND ONLY ONE OF THEM IS A GAP.

    An ion is held ideal by a stated policy -- there is no Debye-Huckel term in
    this project -- and it has the Born term for the part that actually decides
    partitioning between layers. Counting it here would fire the flag on every
    electrolyte in the project and bury the case the flag is for."""
    net = build_network(
        [WATER, "[Na+]", "[Cl-]"], [], thermo=electrolyte_provider(), max_species=20
    )
    v = funnel(net)
    v.charge({WATER: 55.0, "[Na+]": 1.0, "[Cl-]": 1.0})
    v.run(600.0)

    # The ions really are held at gamma = 1 by UNIFAC ...
    assert not v.phases.gamma_active[v._idx["[Na+]"]]
    assert not v.phases.gamma_active[v._idx["[Cl-]"]]
    # ... and they really are a large fraction of the liquid ...
    assert 1.0 / 57.0 < 0.05
    # ... and none of it counts, so brine stays quiet.
    assert v.held_ideal()[0] == 0.0
    assert v.lle_report() == ""


def test_two_layers_say_which_of_them_is_soft(thermo):
    """With a split in hand the flag rides along with the compositions rather
    than replacing them, and it is computed PER LAYER -- a species can be a
    rounding error in one layer and a third of the other."""
    net = build_network(
        [WATER, TOLUENE, SULFURIC], [], thermo=thermo, max_species=20
    )
    v = funnel(net, volume=3.0)
    v.charge({WATER: 27.7, TOLUENE: 4.7, SULFURIC: 2.0})
    v.run(600.0)

    assert v.two_phase
    report = v.lle_report()
    assert "two liquid layers" in report
    assert "compositions are soft" in report
    assert "layer 0" in report and "layer 1" in report

    # ⚠ AND THE SIGNATURE OF THE LIE IS VISIBLE IN THE NUMBERS IT PRODUCED.
    # Equality of activity with gamma = 1 on both sides of an interface IS
    # equality of mole fraction, so an unmodelled neutral partitions evenly
    # between water and toluene -- exactly the failure the Born term was built
    # to fix for ions, still running for neutrals.
    x1 = v.mole_fractions(0)[SULFURIC]
    x2 = v.mole_fractions(1)[SULFURIC]
    assert x1 == pytest.approx(x2, rel=1e-3)


def test_the_unstable_branch_carries_the_flag_too(thermo):
    """A liquid that wants to split says so AND says the tie line is soft; the
    two statements are not alternatives."""
    net = build_network(
        [WATER, TOLUENE, SULFURIC], [], thermo=thermo, max_species=20
    )
    v = funnel(net, volume=3.0, lle=False)
    v.charge({WATER: 27.7, TOLUENE: 4.7, SULFURIC: 2.0})
    v.run(600.0)

    report = v.lle_report()
    assert "UNSTABLE as one phase" in report
    assert "held at gamma = 1" in report
    assert "lle=False" in report


def test_the_ions_and_the_neutrals_are_reported_apart():
    """``ActivityArrays.report`` used to run them together, which made the gap
    look like the policy."""
    arr = build_activity_arrays([WATER, SULFURIC, "[Na+]", "[Cl-]", TOLUENE])
    text = arr.report()
    assert "1 NEUTRAL species" in text
    assert "2 ION(S)" in text
    assert text.index("NEUTRAL") < text.index("ION(S)")

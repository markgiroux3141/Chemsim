"""Explicit acid catalysis: a species with exponent 1 and stoichiometry 0.

The claim this file exists to check is that homogeneous catalysis needed NO ENGINE
WORK -- that putting a species on both sides of a reaction SMARTS already gives it
a mass-action exponent of 1 and a net stoichiometry of 0, in Layer 3, with nothing
added to Layer 4. And the claim that matters more: that making the catalysis
explicit did not silently re-calibrate every esterification in the project, which
it would have done if the folded-in catalyst concentration had not been declared.
"""

from __future__ import annotations

import numpy as np
import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.reactions.library import (
    ACID_CATALYST,
    CATALYST_REFERENCE,
    acid_catalysed_chemistry,
    alcohol_chemistry,
    alkene_dehydration,
    esterification,
    ether_condensation,
)
from chemsim.vessel import Vessel

ACETIC, ETOH, WATER = "CC(=O)O", "CCO", "O"
ESTER = Molecule.from_smiles("CCOC(C)=O").smiles
PROTON = "[OH3+]"


@pytest.fixture(scope="module")
def thermo():
    return electrolyte_provider()


def network(templates, thermo, species=(ACETIC, ETOH, WATER, "[Na+]", "[OH-]")):
    return build_network(
        list(species), [*templates, *dissociation_templates()],
        thermo=thermo, max_species=80,
    )


def find(net, arrays, fragment):
    """The (index, reaction) whose name contains ``fragment`` and is forward."""
    for j, rxn in enumerate(net.reactions):
        if fragment in rxn.name and not rxn.name.endswith("_rev"):
            return j, rxn
    raise AssertionError(f"no forward reaction matching {fragment!r}")


def test_the_catalyst_is_a_reactant_with_no_net_stoichiometry(thermo):
    """The whole mechanism, in two array rows.

    ``order`` is what the rate law raises the concentration to; ``delta`` is what
    the reaction consumes and produces. A catalyst has to appear in the first and
    cancel out of the second, and ``builder.to_arrays`` does exactly that for a
    species written on both sides -- ``order += 1`` as a reactant, then
    ``delta -= 1`` and ``delta += 1``.
    """
    net = network([esterification(catalyst=ACID_CATALYST)], thermo)
    arrays = net.to_arrays(thermo)
    i = net.species.index(PROTON)
    j, _ = find(net, arrays, "fischer_esterification")

    assert arrays.order[j, i] == 1.0, "the rate must depend on the catalyst"
    assert arrays.delta[j, i] == 0.0, "the catalyst must not be consumed"
    # ... and it is still an ordinary reaction in every other respect.
    assert arrays.order[j, net.species.index(ACETIC)] == 1.0
    assert arrays.delta[j, net.species.index(ESTER)] == 1.0


def test_the_reverse_is_catalysed_too_so_the_equilibrium_cannot_move(thermo):
    """⚠ THE THING THAT WOULD HAVE BEEN EASY TO GET WRONG.

    Detailed balance derives the reverse from the forward, so the catalyst arrives
    in the reverse direction with the same exponent and cancels out of K exactly --
    which is the definition of a catalyst. Had it been declared on the forward
    direction only, adding acid would have MOVED the equilibrium, and the error
    would have looked like a plausible rate effect.
    """
    net = network([esterification(catalyst=ACID_CATALYST)], thermo)
    arrays = net.to_arrays(thermo)
    i = net.species.index(PROTON)
    fwd = rev = None
    for j, rxn in enumerate(net.reactions):
        if "fischer_esterification" in rxn.name:
            (rev, fwd) = (j, fwd) if rxn.name.endswith("_rev") else (rev, j)
    assert fwd is not None and rev is not None
    assert arrays.order[fwd, i] == arrays.order[rev, i] == 1.0
    assert arrays.delta[fwd, i] == arrays.delta[rev, i] == 0.0

    # K = A_f/A_r * exp(-(Ea_f - Ea_r)/RT), and both A's scale by the same
    # 1/CATALYST_REFERENCE, so the ratio is untouched.
    plain = network([esterification()], thermo).to_arrays(thermo)
    pf = pr = None
    for j, rxn in enumerate(network([esterification()], thermo).reactions):
        if "fischer_esterification" in rxn.name:
            (pr, pf) = (j, pf) if rxn.name.endswith("_rev") else (pr, j)
    assert arrays.A[fwd] / arrays.A[rev] == pytest.approx(
        plain.A[pf] / plain.A[pr], rel=1e-12
    )
    assert arrays.Ea[fwd] == pytest.approx(plain.Ea[pf], rel=1e-12)
    assert arrays.Ea[rev] == pytest.approx(plain.Ea[pr], rel=1e-12)


def test_the_folded_catalyst_concentration_is_declared_not_refitted(thermo):
    """The point of ``CATALYST_REFERENCE``.

    An apparent rate is ``A_app [acid][alcohol]`` and an explicit one is
    ``A_int [acid][alcohol][H3O+]``, so the two agree at exactly one catalyst
    loading and ``A_app = A_int * [H3O+]_folded``. Declaring that loading is what
    makes the change a re-EXPRESSION rather than a re-calibration; without it,
    making the catalysis explicit would have slowed every esterification in this
    project by a factor of ten.
    """
    plain = network([esterification()], thermo).to_arrays(thermo)
    cat = network([esterification(catalyst=ACID_CATALYST)], thermo).to_arrays(thermo)
    jp, _ = find(network([esterification()], thermo), plain, "fischer_esterification")
    jc, _ = find(
        network([esterification(catalyst=ACID_CATALYST)], thermo), cat,
        "fischer_esterification",
    )
    assert cat.A[jc] == pytest.approx(plain.A[jp] / CATALYST_REFERENCE)
    # So at the reference loading the two rate expressions are the same number.
    assert cat.A[jc] * CATALYST_REFERENCE == pytest.approx(plain.A[jp])


def test_all_three_acid_catalysed_routes_carry_the_catalyst(thermo):
    """Esterification and BOTH dehydrations, which are the three the library
    documented as having catalysis folded into the barrier."""
    for tmpl, fragment in (
        (esterification(catalyst=ACID_CATALYST), "fischer"),
        (ether_condensation(catalyst=ACID_CATALYST), "ether"),
        (alkene_dehydration(catalyst=ACID_CATALYST), "alkene"),
    ):
        net = network([tmpl], thermo, species=(ETOH, WATER, ACETIC, "[Na+]", "[OH-]"))
        arrays = net.to_arrays(thermo)
        i = net.species.index(PROTON)
        found = [
            j for j, rxn in enumerate(net.reactions)
            if fragment in rxn.name and not rxn.name.endswith("_rev")
        ]
        assert found, f"{fragment} produced no forward reaction"
        for j in found:
            assert arrays.order[j, i] == 1.0, fragment
            assert arrays.delta[j, i] == 0.0, fragment


def test_the_oxidation_pair_is_deliberately_left_uncatalysed(thermo):
    """Autoxidation and peroxide oxidation are not acid-catalysed, and making the
    bundle uniform for tidiness would cost a fact."""
    catalysed = acid_catalysed_chemistry()
    names = {t.name for t in catalysed}
    assert "aerobic_oxidation" in names
    assert "peroxide_over_oxidation" in names
    assert "fischer_esterification_acid" in names
    # ... and the plain bundle is untouched, so no existing network moved.
    assert {t.name for t in alcohol_chemistry()} == {
        "fischer_esterification", "ether_condensation", "alkene_dehydration",
        "aerobic_oxidation", "peroxide_over_oxidation",
    }
    for plain, cat in zip(alcohol_chemistry(), catalysed):
        if not cat.name.endswith("_acid"):
            assert plain.smarts == cat.smarts
            assert plain.A == cat.A


def test_more_acid_is_a_faster_reaction_and_the_slope_is_first_order(thermo):
    """What the whole thing buys: pH is a lever on RATE, not only on speciation.

    Rate is first order in the catalyst, so ten times the acid is ten times the
    rate. Measured on the rate law directly rather than on a trajectory -- a
    trajectory would also move the ester's own concentration and confound the two.
    """
    net = network([esterification(catalyst=ACID_CATALYST)], thermo)
    arrays = net.to_arrays(thermo)
    j, _ = find(net, arrays, "fischer_esterification")
    T = 353.0
    k = arrays.A[j] * np.exp(-arrays.Ea[j] / (8.31446 * T))

    def rate(proton: float) -> float:
        C = np.zeros(len(net.species))
        C[net.species.index(ACETIC)] = 1.0
        C[net.species.index(ETOH)] = 1.0
        C[net.species.index(PROTON)] = proton
        return float(k * np.prod(C ** arrays.order[j]))

    assert rate(0.1) > 0.0
    assert rate(1.0) / rate(0.1) == pytest.approx(10.0, rel=1e-9)
    assert rate(0.0) == 0.0, "no catalyst, no catalysed reaction -- by design"


def test_a_catalysed_template_in_a_network_with_no_catalyst_is_inert(thermo):
    """⚠ The failure mode the library docstring warns about, pinned so it stays
    visible: a catalysed bundle in a network with no ``[OH3+]`` silently becomes an
    oxidation-only network. ``build_network`` cannot warn -- "matched nothing" is
    indistinguishable from a template that legitimately does not apply."""
    from chemsim.properties import ThermochemistryProvider

    plain_thermo = ThermochemistryProvider()
    net = build_network(
        [ACETIC, ETOH, WATER], [esterification(catalyst=ACID_CATALYST)],
        thermo=plain_thermo, max_species=40,
    )
    assert ESTER not in net.species, (
        "with no hydronium in the network the catalysed esterification cannot fire"
    )
    # ... whereas the uncatalysed form does.
    plain = build_network(
        [ACETIC, ETOH, WATER], [esterification()],
        thermo=plain_thermo, max_species=40,
    )
    assert ESTER in plain.species


def test_a_catalysed_esterification_actually_runs(thermo):
    """End to end: the catalyst comes from the dissociation set rather than being
    charged, so the acid the reaction consumes is also the acid that catalyses it.

    ⚠ Run AQUEOUS, and the reason is a real consequence of this session's other
    change rather than a convenience. The ionic rate correction (see
    ``vessel_integrator._phase_rates``) suppresses dissociation in a low-dielectric
    medium, so in a NEAT acid/alcohol mixture -- permittivity about 12 -- acetic
    acid is roughly a million times less dissociated than in water and its own
    autocatalysis all but stops. That is the right chemistry, and it is why a bench
    Fischer esterification uses added sulfuric acid rather than relying on the
    substrate: glacial acetic acid is a poor conductor. It also means a neat
    mixture is the wrong system in which to demonstrate that a catalysed template
    fires at all.
    """
    net = network([esterification(catalyst=ACID_CATALYST)], thermo)
    assert ESTER in net.species
    v = Vessel(net, volume=1.5, T=353.0, T_env=353.0, UA=50.0, kla=0.0, k_diss=0.0)
    v.charge({WATER: 40.0, ACETIC: 1.0, ETOH: 1.0})
    v.run(600.0)
    assert v.state().total(ESTER) > 1.0e-6, "the catalysed route made no ester"

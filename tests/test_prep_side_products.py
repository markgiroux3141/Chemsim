"""The benzoic-acid prep's purity figure has to MEAN something.

``examples/multistep_prep.py`` used to run on one template, and the consequence
was not cosmetic: **a network with one template cannot produce a side product**,
so its ~100% purity was true by construction and no loss model calibrated against
it could have been trusted. That is also why crystal occlusion was untestable --
it would have had nothing to trap but ions and unreacted starting material.

What makes this route's side products interesting is that nothing charges them:
saponification liberates ETHANOL, and the ethanol is what the oxidation family
attacks. The prep supplies its own contaminant.

As in ``test_competing_templates.py``, the assertions are ORDERINGS and
RESPONSES, never absolute amounts -- absolute yields are hostage to the
hand-authored pre-exponentials, while the cascade's existence and its direction
are not.
"""

import pytest

from chemsim import recipes
from chemsim.recipes import BENZOATE, WATER
from chemsim.recipes import BENZOIC_ACID_PREP as PREP
from chemsim.vessel import Vessel

ACETIC = recipes.ACETIC_ACID
ACID = recipes.BENZOIC_ACID
ETOH = recipes.ETHANOL
ESTER = recipes.ETHYL_BENZOATE

ALDEHYDE, PEROXIDE, ETHYL_ACETATE, ETHER = "CC=O", "OO", "CCOC(C)=O", "CCOCC"


@pytest.fixture(scope="module")
def net():
    # ⚠ ONE HOME FOR THE RECIPE. This pot used to be spelled out here, in
    # ``examples/multistep_prep.py`` and in ``validation/process_losses.py``, and
    # its conditions are load-bearing -- ``k_lle = 0.5`` rather than the default
    # 5.0, or it does not integrate. Three hand-kept copies of a number like that
    # is how a harness ends up measuring something the example does not do.
    return PREP.network()


def saponify(net, air: bool, hours: float = 2.0):
    """The prep's first step: ester + hydroxide at 80 C, open to its own
    headspace or not.

    ⚠ ``k_lle`` is below its default of 5.0 mol/s, and it has to be. This pot
    genuinely wants to be TWO LAYERS -- ethyl benzoate is barely water-soluble --
    and until an ion transfer model existed the split was refused outright, which
    is what held this file's numbers steady while the pot was quietly single-phase.
    At the default transfer rate the two-phase system does not integrate; see
    ``examples/multistep_prep.py`` and NEXT_SESSION.md item 1.

    The answer does not depend on the number, which is what makes it reportable
    rather than a fudge: 0.5 and 0.05 mol/s give the same benzoate to five decimal
    places, because at either rate the 0.2 mol of ester crosses the interface in
    well under a second and the saponification is not transfer-limited on a
    two-hour timescale.

    ⚠ "SEALED" IS A NITROGEN BLANKET, not ``kla = 0``, and the change is worth
    recording because the old form stopped working for a structural reason rather
    than a chemical one. Turning mass transfer off entirely leaves the gas block
    identically zero AND FLAT, which is the ``num_jac`` pathology this project has
    documented twice (a vessel at rest, and an empty second liquid layer): every
    finite difference in that column comes back below the "too small" threshold,
    the perturbation factor inflates without bound, overflows to inf, and BDF gets
    a NaN Jacobian. It was survivable while the pot was held single-phase and stops
    being survivable once there is a second layer to find columns for.

    A nitrogen headspace is also the more honest statement of the same experiment --
    it is what the docstrings have described all along ("blanket it with nitrogen")
    -- and it keeps the oxygen budget as the thing under test rather than the
    existence of a vapour phase.
    """
    pot = PREP.pot(net, air=air, lossless=True)
    pot.run(hours * 3600.0)
    return pot.state()


# ---------------------------------------------------------------------------
# the network must stay bounded -- adding templates is not what explodes one
# ---------------------------------------------------------------------------


def test_four_templates_do_not_explode_the_prep_network(net):
    """Explosion comes from a template that REGENERATES its own matched group
    (polyesterification reached 80 species from one template). None of these
    does: an ether, an ester and an acid have no free carbinol left to attack.

    Asserted as a bound so that a future self-feeding template shows up here as a
    jump in the number rather than as a mysteriously slow test.
    """
    assert len(net.species) <= 24, sorted(net.species)
    assert len(net.reactions) <= 24


# ---------------------------------------------------------------------------
# the cascade, and the lever that turns it off
# ---------------------------------------------------------------------------


def test_the_prep_makes_its_own_contaminant_from_the_alcohol_it_liberates(net):
    """Nobody charges acetaldehyde or acetic acid. Saponification liberates
    ethanol; headspace O2 oxidises it to the aldehyde and hydrogen peroxide; the
    peroxide over-oxidises the aldehyde to acetic acid; the acid re-esterifies
    with the remaining ethanol. Four templates meeting, none mentioning another,
    all of them started by a species the route made for itself."""
    st = saponify(net, air=True)

    assert st.total(ETOH) > 0.15, "saponification must actually liberate ethanol"
    for species in (ALDEHYDE, PEROXIDE, ACETIC, ETHYL_ACETATE):
        assert st.total(species) > 0.0, species
    # The cascade's ORDERING: over-oxidation is the faster step (Ea 50 vs 65),
    # so the acid outruns the aldehyde it comes from rather than piling up
    # behind it.
    assert st.total(ACETIC) > 10.0 * st.total(ALDEHYDE)


def test_sealing_the_flask_removes_the_oxidation_products(net):
    """The countermeasure, and the thing that makes it a mechanic rather than
    background noise: the oxygen budget is the headspace, so 'stopper it' or
    'blanket it with nitrogen' is a real decision with a measurable result."""
    air = saponify(net, air=True)
    sealed = saponify(net, air=False)

    assert sealed.total(ACETIC) < 1e-6
    assert sealed.total(ALDEHYDE) < 1e-6
    assert air.total(ACETIC) > 1000.0 * max(sealed.total(ACETIC), 1e-12)
    # ... and the benzoyl chemistry is untouched by it, which is why this is a
    # PURITY mechanic and not a yield one.
    assert air.total(BENZOATE) == pytest.approx(sealed.total(BENZOATE), rel=1e-3)


def test_the_side_products_are_bounded_by_the_oxygen_in_the_flask(net):
    """Scale dependence, in the form this particular mechanic takes: the amount
    of contaminant is set by how much air was shut in with the reaction, not by
    a rate constant alone. A longer cook cannot make more than the O2 allows."""
    two_hours = saponify(net, air=True, hours=2.0)
    eight_hours = saponify(net, air=True, hours=8.0)

    assert eight_hours.total(ACETIC) >= two_hours.total(ACETIC)
    assert eight_hours.total(ACETIC) < 2.0 * two_hours.total(ACETIC), (
        "the headspace oxygen is the budget; four times the time must not give "
        "anything like four times the acid"
    )


def test_the_impurity_is_dissolved_not_crystallised(net):
    """Which is what makes it occlusion's business rather than co-crystallisation's.

    Acetic acid melts at 289.7 K and the crop is filtered at 275 K, so it is
    worth checking that it does not simply freeze out alongside the product --
    it does not, because it is far below its saturation activity at that
    dilution. Anything that DID co-crystallise would be a purity problem no wash
    and no occlusion model could describe.
    """
    pot = Vessel(net, volume=2.0, T=275.0, T_env=275.0, UA=5.0, kla=0.0,
                 k_diss=0.05, k_vent=0.0)
    pot.charge({WATER: 55.0, ACETIC: 0.0067, ACID: 0.19})
    pot.run(3600.0)

    st = pot.state()
    assert st.n_solid[ACID] > 0.15, "the product must still crop out"
    assert st.n_solid[ACETIC] == pytest.approx(0.0, abs=1e-9)

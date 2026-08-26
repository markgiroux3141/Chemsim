"""M8 -- electricity as a reagent, and the gate that is a comparison of two energies.

Grouped by the claim each set pins:

  * **the contract, and it is the one that matters most** -- a network built
    without ``cell_potential`` is BIT-IDENTICAL to the one this project built
    before M8. Not close: identical, because ``reaction_deltas`` skips the term
    on a falsy ``electrical_work`` and every non-electrode template leaves it at
    exactly 0.0.
  * **the gate is a threshold and not a flag** -- the same flask at 1.5 V and at
    3.0 V, with the crossing where ``dG_chem / (n F)`` says it is.
  * **the decomposition potentials are DERIVED**, and land within a quarter of a
    volt of the electrochemical series without this project curating a single
    electrode potential.
  * **the reverse carries minus the work**, so ``dH_rev == -dH_fwd`` exactly and
    a round trip through the pair creates no energy.
  * **the templates balance in MASS AND CHARGE**, which is what makes a whole-cell
    reaction legal where a half-cell reaction is not.
  * **what is refused** -- a negative electron count, and ``electrons`` together
    with ``orders``.
  * **what is NOT modelled**, pinned so it cannot be quietly claimed later: no
    current budget, and the selectivity that washes out because of it.
"""

from __future__ import annotations

import math

import pytest

from chemsim.constants import FARADAY, R
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.electrolyte import (
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions import (
    ReactionTemplate,
    alkene_hydrodimerisation,
    electrochemistry,
    esterification,
    halide_electrolysis,
    kolbe_electrolysis,
    water_electrolysis,
)
from chemsim.reactions.reaction import ConcreteReaction
from chemsim.reactions.thermo import decomposition_potential, reaction_deltas

WATER, CL, NA = "O", "[Cl-]", "[Na+]"
CL2, H2, O2, OH = "ClCl", "[H][H]", "O=O", "[OH-]"
ACETATE, ETHANE, CO2 = "CC(=O)[O-]", "CC", "O=C=O"
AN, ADN = "C=CC#N", "N#CCCCCC#N"


@pytest.fixture(scope="module")
def providers():
    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    return electrolyte_provider(base=thermo, volatility=vol), vol


def _cell(providers, feed, E, extra=()):
    prov, vol = providers
    return build_network(
        list(feed), list(electrochemistry()) + list(dissociation_templates())
        + list(extra),
        thermo=prov, volatility=vol, max_species=80, generations=3,
        cell_potential=E,
    )


def _named(net, name):
    return next(r for r in net.reactions if r.name == name)


def _k(rxn, T=298.15):
    return rxn.A * T ** rxn.n_exp * math.exp(-rxn.Ea / (R * T))


# ---------------------------------------------------------------------------
# THE CONTRACT: no supply is EXACTLY the old engine
# ---------------------------------------------------------------------------

def test_no_cell_potential_is_bit_identical_to_before_M8(providers):
    """The default argument must be the old arithmetic, not a near copy of it.

    Built twice from the same non-electrode templates -- once with the keyword
    absent, once with it explicitly 0.0 -- and every A, Ea and dH compared bit
    for bit. This is the invariant that lets M8 be added to a project whose
    other examples are pinned to exact numbers.
    """
    prov, vol = providers
    feed = ["CC(=O)O", "CCO", WATER]
    tmpls = [esterification()]
    a = build_network(feed, tmpls, thermo=prov, volatility=vol, generations=2)
    b = build_network(feed, tmpls, thermo=prov, volatility=vol, generations=2,
                      cell_potential=0.0)
    c = build_network(feed, tmpls, thermo=prov, volatility=vol, generations=2,
                      cell_potential=3.0)
    assert a.species == b.species == c.species
    for ra, rb, rc in zip(a.reactions, b.reactions, c.reactions):
        assert (ra.name, ra.reactants, ra.products) == (rb.name, rb.reactants,
                                                        rb.products)
        assert ra.A == rb.A == rc.A          # bit for bit
        assert ra.Ea == rb.Ea == rc.Ea
        assert ra.electrical_work == 0.0
    # And a voltage cannot reach a reaction that passes no electrons.
    assert a.to_arrays().dH.tolist() == c.to_arrays().dH.tolist()


def test_electrical_work_is_exactly_zero_without_electrons(providers):
    """Not 1e-30, not -0.0 -- the falsy check in reaction_deltas depends on it."""
    prov, vol = providers
    net = _cell(providers, [AN, WATER], 3.0)
    for rxn in net.reactions:
        if rxn.name.startswith("alkene_hydrodimerisation"):
            assert rxn.electrical_work == 0.0
            assert not rxn.electrical_work


def test_a_zero_volt_cell_leaves_the_driving_force_untouched(providers):
    """0 V is not "electrolysis at zero" -- it is no term at all."""
    prov, vol = providers
    rx = ConcreteReaction("probe", (CL, CL, WATER, WATER), (CL2, H2, OH, OH),
                          A=1.0, Ea=0.0, phase="liquid")
    plain = reaction_deltas(rx, prov, vol)
    driven = reaction_deltas(
        ConcreteReaction("probe", rx.reactants, rx.products, A=1.0, Ea=0.0,
                         phase="liquid", electrical_work=0.0),
        prov, vol,
    )
    assert plain == driven


# ---------------------------------------------------------------------------
# THE GATE
# ---------------------------------------------------------------------------

def test_decomposition_potential_matches_the_electrochemical_series(providers):
    """Derived from dGf and divided by n F. Nothing in src/ curates an E0.

    The tolerance is a quarter of a volt and it is deliberately loose: this is a
    pure-liquid-standard-state dG for a real mixture against standard electrode
    potentials at unit activity. Agreement to a few tenths is the claim; closer
    would be luck and tighter would turn an independent check into a target.
    """
    prov, vol = providers
    for reactants, products, n, book in (
        ((WATER, WATER), (H2, H2, O2), 4, 1.229),
        ((CL, CL, WATER, WATER), (CL2, H2, OH, OH), 2, 2.186),
        (("[Br-]", "[Br-]", WATER, WATER), ("BrBr", H2, OH, OH), 2, 1.894),
    ):
        rx = ConcreteReaction("probe", reactants, products, A=1.0, Ea=0.0,
                              phase="liquid")
        E = decomposition_potential(rx, prov, n, 298.15, vol)
        assert abs(E - book) < 0.25, (reactants, E, book)
        # and on the correct side: this project's dG runs high, every time
        assert E > book


def test_the_gate_crosses_where_E_dec_says_it_does(providers):
    """Below the decomposition potential the cell is at equilibrium the OTHER
    way round -- which is a stronger statement than "slow", and the one the
    equilibrium constant makes."""
    prov, vol = providers
    ks = {}
    for E in (1.5, 2.0, 2.5, 3.0):
        net = _cell(providers, [NA, CL, WATER], E)
        ks[E] = _k(_named(net, "halide_electrolysis"))
    # E_dec for brine is 2.362 V; 2.5 is over it and 2.0 is not.
    assert ks[1.5] < ks[2.0] < ks[2.5] <= ks[3.0]
    assert ks[2.0] < 1e-12          # dead below the threshold
    assert ks[2.5] > 1e-9           # alive above it
    assert ks[2.5] / ks[2.0] > 1e6  # and the crossing is sharp


def test_raising_the_voltage_only_ever_helps(providers):
    """Monotone in E, for every electrode reaction. A cell that ran slower when
    turned up would mean the work had landed on the wrong side of something."""
    prov, vol = providers
    for name, feed in (("halide_electrolysis", [NA, CL, WATER]),
                       ("water_electrolysis", [WATER]),
                       ("kolbe_electrolysis", [NA, ACETATE, WATER])):
        last = -1.0
        for E in (0.0, 1.0, 2.0, 3.0, 4.0):
            k = _k(_named(_cell(providers, feed, E), name))
            assert k >= last, (name, E)
            last = k


# ---------------------------------------------------------------------------
# THE REVERSE
# ---------------------------------------------------------------------------

def test_the_reverse_carries_minus_the_work(providers):
    """dH_rev == -dH_fwd exactly, so a round trip creates no energy.

    Without the sign flip the forward would see ``dH - w`` and the reverse
    ``-dH - w``, and the pair detailed balance had just made consistent would
    reach Layer 4 inconsistent by ``2 n F E`` per cycle.
    """
    net = _cell(providers, [NA, CL, WATER], 3.0)
    for stem in ("water_electrolysis", "halide_electrolysis"):
        fwd, rev = _named(net, stem), _named(net, stem + "_rev")
        assert fwd.electrical_work == -rev.electrical_work
        assert fwd.electrical_work != 0.0


def test_the_work_is_n_times_faraday_times_the_potential(providers):
    """The one arithmetic identity the whole mechanic rests on."""
    for E in (1.5, 3.0):
        net = _cell(providers, [NA, CL, WATER], E)
        for name, n in (("water_electrolysis", 4), ("halide_electrolysis", 2)):
            got = _named(net, name).electrical_work
            assert got == pytest.approx(n * FARADAY * E, rel=1e-12)


# ---------------------------------------------------------------------------
# THE TEMPLATES THEMSELVES
# ---------------------------------------------------------------------------

def test_every_cell_reaction_balances_in_mass_and_charge(providers):
    """A whole-cell reaction is legal where a half-cell reaction is not, and this
    is why: the electrons cancel and the charge closes. The builder rejects a
    rewrite that does not, so a reaction APPEARING here is the check."""
    from rdkit import Chem

    from chemsim.matter import Molecule

    for feed in ([NA, CL, WATER], [NA, ACETATE, WATER], [AN, WATER]):
        net = _cell(providers, feed, 3.0)
        for rxn in net.reactions:
            ra = rb = 0
            counts: dict[str, int] = {}
            for side, sign in ((rxn.reactants, 1), (rxn.products, -1)):
                for smi in side:
                    m = Molecule.from_smiles(smi)._mol
                    for a in Chem.AddHs(m).GetAtoms():
                        counts[a.GetSymbol()] = counts.get(a.GetSymbol(), 0) + sign
                    if sign > 0:
                        ra += Chem.GetFormalCharge(m)
                    else:
                        rb += Chem.GetFormalCharge(m)
            assert all(v == 0 for v in counts.values()), (rxn.name, counts)
            assert ra == rb, (rxn.name, ra, rb)


def test_the_halide_template_is_one_template_over_three_halides(providers):
    """Bromide gives bromine by the same declaration, at a LOWER voltage, and
    nothing had to be told that bromide is easier to oxidise than chloride."""
    prov, vol = providers
    net = _cell(providers, ["[K+]", "[Br-]", WATER], 3.0)
    assert "BrBr" in net.species
    rx_br = ConcreteReaction("p", ("[Br-]", "[Br-]", WATER, WATER),
                             ("BrBr", H2, OH, OH), A=1.0, Ea=0.0, phase="liquid")
    rx_cl = ConcreteReaction("p", (CL, CL, WATER, WATER), (CL2, H2, OH, OH),
                             A=1.0, Ea=0.0, phase="liquid")
    E_br = decomposition_potential(rx_br, prov, 2, 298.15, vol)
    E_cl = decomposition_potential(rx_cl, prov, 2, 298.15, vol)
    assert E_br < E_cl


def test_kolbe_gives_the_cross_coupling_nobody_wrote_down(providers):
    """Two independent reactant slots meeting a two-component mixture is three
    reactions, not two. Real Kolbe chemistry and a real Kolbe nuisance."""
    net = _cell(providers, [NA, ACETATE, "CCC(=O)[O-]", WATER], 3.0)
    assert {"CC", "CCC", "CCCC"} <= set(net.species)


def test_kolbe_needs_the_carboxylate_and_not_the_acid(providers):
    """A flask of glacial acetic acid does not electrolyse. The template says so
    by matching [O-], and nothing else has to enforce it."""
    prov, vol = providers
    net = build_network(
        ["CC(=O)O"], [kolbe_electrolysis()], thermo=prov, volatility=vol,
        generations=2, cell_potential=3.0,
    )
    assert not [r for r in net.reactions if r.name.startswith("kolbe")]


def test_the_adiponitrile_route_runs_and_is_not_an_electrode_reaction(providers):
    """The catalog row emerges from two declarations that do not mention each
    other -- and the coupling half passes NO electrons, which is a measurement
    and not an omission: 2 AN + H2 -> ADN is downhill on its own."""
    prov, vol = providers
    net = _cell(providers, [AN, WATER], 3.0)
    assert ADN in net.species
    assert O2 in net.species
    assert alkene_hydrodimerisation().electrons == 0
    coupling = ConcreteReaction("p", (AN, AN, H2), (ADN,), A=1.0, Ea=0.0,
                                phase="liquid")
    _, dG = reaction_deltas(coupling, prov, vol)
    assert dG < 0.0, "the C-C coupling is not what the voltage pays for"


# ---------------------------------------------------------------------------
# WHAT IS REFUSED
# ---------------------------------------------------------------------------

def test_a_negative_electron_count_is_refused():
    with pytest.raises(ValueError, match="galvanic"):
        ReactionTemplate(name="battery", smarts="[OX2H2:1]>>[OX2H2:1]",
                         A=1.0, Ea=0.0, electrons=-2)


def test_electrons_with_declared_orders_is_refused():
    """An irreversible electrode reaction would keep the electron count and
    throw away the only thing it does: below E_dec it would still run."""
    with pytest.raises(ValueError, match="electrons"):
        ReactionTemplate(
            name="bad", smarts="[OX2H2:1].[OX2H2:2]>>[H][H].[H][H].[O:1]=[O:2]",
            A=1.0, Ea=0.0, electrons=4, orders=(1.0, 0.0),
        )


def test_decomposition_potential_refuses_an_already_driven_reaction(providers):
    """Driven, it would return E_dec - E: the overpotential wearing the units of
    an answer."""
    prov, vol = providers
    rx = ConcreteReaction("p", (WATER, WATER), (H2, H2, O2), A=1.0, Ea=0.0,
                          phase="liquid", electrical_work=1.0e5)
    with pytest.raises(ValueError, match="electrical_work"):
        decomposition_potential(rx, prov, 4, 298.15, vol)


def test_decomposition_potential_refuses_a_zero_electron_count(providers):
    prov, vol = providers
    rx = ConcreteReaction("p", (WATER, WATER), (H2, H2, O2), A=1.0, Ea=0.0,
                          phase="liquid")
    with pytest.raises(ValueError, match="positive electron count"):
        decomposition_potential(rx, prov, 0, 298.15, vol)


# ---------------------------------------------------------------------------
# WHAT IS NOT MODELLED -- pinned so it cannot be quietly claimed later
# ---------------------------------------------------------------------------

def test_the_activation_selectivity_washes_out_at_high_voltage(providers):
    """Chlorine outruns oxygen by eighteen orders of magnitude at 2.5 V and by
    less than one at 3.0 V, because both barriers reach the floor at zero.

    A real cell holds its selectivity there, because the supply's electrons are
    FINITE and the fast reaction takes them. This engine budgets no current, so
    both reactions draw as much as they like. Pinned as a LIMIT: if a later
    milestone makes this ratio hold at 4 V, this test should fail and be
    rewritten, not deleted.
    """
    ratios = {}
    for E in (2.5, 3.0, 4.0):
        net = _cell(providers, [NA, CL, WATER], E)
        ratios[E] = (_k(_named(net, "halide_electrolysis"))
                     / _k(_named(net, "water_electrolysis")))
    assert ratios[2.5] > 1e15
    assert ratios[3.0] < 1e2
    assert ratios[4.0] == pytest.approx(1.0, rel=1e-9)


def test_the_electrode_pre_exponential_is_a_current_not_a_collision(providers):
    """An electrode reaction happens on a SURFACE; its rate is proportional to
    area, not volume. Declared at a collision frequency it consumed 0.2 mol of
    chloride inside a nanosecond and killed the solver -- so the value is a
    current density over an electrode area, and this pins the order of magnitude
    rather than the digits.
    """
    for t in electrochemistry():
        if t.electrons:
            assert 1e-9 < t.A < 1e-6, t.name
            # and far below the homogeneous ceiling, which is the wrong one
            assert t.A < 1e11


def test_the_barrier_is_an_overpotential_in_energy_units():
    """Ea = n F eta_a, with eta_a the volts a real cell needs on top of E_dec.
    Oxygen evolution is the sluggish one and the gap is the mechanism."""
    eta = {t.name: t.Ea / (t.electrons * FARADAY)
           for t in electrochemistry() if t.electrons}
    assert eta["water_electrolysis"] == pytest.approx(0.80, abs=1e-6)
    assert eta["halide_electrolysis"] == pytest.approx(0.40, abs=1e-6)
    assert eta["kolbe_electrolysis"] == pytest.approx(1.20, abs=1e-6)
    assert eta["water_electrolysis"] > eta["halide_electrolysis"]


def test_alpha_is_the_transfer_coefficient(providers):
    """0.5, and it is the same coefficient in both readings -- Evans-Polanyi's
    and Butler-Volmer's. Not a resemblance; see ReactionTemplate's docstring."""
    for t in electrochemistry():
        if t.electrons:
            assert t.alpha == 0.5
    assert water_electrolysis().alpha == halide_electrolysis().alpha

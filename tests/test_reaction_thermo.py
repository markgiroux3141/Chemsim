"""Layer 1 -> Layer 2: equilibrium derived from molecular structure.

The point of these tests: the esterification equilibrium we previously hand-tuned
(K ~ 6) now falls out of group-contribution thermochemistry, with no equilibrium
constant entered anywhere.
"""

from chemsim.network import build_network
from chemsim.reactions import equilibrium_constant, reaction_deltas


def _forward(net):
    return next(r for r in net.reactions if r.name == "fischer_esterification")


def test_esterification_is_mildly_thermoneutral(fischer_template, thermo):
    net = build_network(["CC(=O)O", "CCO", "O"], [fischer_template], thermo=thermo)
    dH, dG = reaction_deltas(_forward(net), thermo)
    # Fischer esterification is close to thermoneutral (small |dH|, |dG|).
    assert abs(dH) < 30.0, f"dH={dH}"
    assert abs(dG) < 20.0, f"dG={dG}"


def test_equilibrium_constant_is_physical_and_falls_with_temperature(fischer_template, thermo):
    """Note the standard state. Called without a volatility model this is the
    IDEAL-GAS constant, which is genuinely ~300 at 298 K -- it is not comparable
    to the ~4 measured in the liquid, and comparing them is what this test used
    to do. The two are reconciled in ``test_standard_state``; here the claim is
    only that the constant is finite, large, and falls with temperature."""
    net = build_network(["CC(=O)O", "CCO", "O"], [fischer_template], thermo=thermo)
    fwd = _forward(net)

    K298 = equilibrium_constant(fwd, thermo, 298.15)
    K340 = equilibrium_constant(fwd, thermo, 340.0)

    assert 1.0 < K340 < K298 < 1.0e4, f"K298={K298} K340={K340}"
    # Exothermic forward reaction -> K decreases with temperature (Le Chatelier).
    assert K340 < K298


def test_provenance_distinguishes_measured_from_estimated(thermo):
    """Every value carries where it came from, and all four tiers are visible:
    fully curated, a measured overlay on an otherwise estimated record, Benson
    group additivity, and a bare Joback estimate.

    The Joback example has to be a species Benson cannot price AND that has no
    curated formation overlay, which takes some finding now: 3-methylpyridine
    qualifies because RMG's group table has no aromatic-nitrogen entry and no
    pyridine ring correction, and it is not in the curated tables. 1,4-dioxane
    used to serve here and no longer does -- it gained a ring correction, so
    Benson now outranks Joback on it.

    A record's ``source`` now names BOTH HALVES, because they are resolved
    independently -- see the resolution table in ``thermochemistry``. The halves
    genuinely differ in provenance for most species, which is the whole reason
    the string is composite rather than a single label: ethyl acetate below has a
    measured formation half sitting on a Joback physical one.
    """
    assert thermo.get("O").source.startswith("experimental")            # curated

    ester = thermo.get("CCOC(C)=O")                                     # overlay
    assert "formation half: experimental formation data" in ester.source
    assert "physical half: Joback" in ester.source

    assert "Benson group additivity" in thermo.get("C1COCCO1").source   # estimator

    picoline = thermo.get("Cc1cccnc1")                                  # fallback
    assert picoline.source == "formation half: Joback; physical half: Joback"
    # The physical half's provenance is also a field of its own, so a caller
    # building a vapour-pressure curve does not have to parse the prose.
    assert picoline.physical_source == "Joback"

"""ELECTRICITY AS A REAGENT -- M8, and the gate is a comparison of two energies.

    a flask of brine, a pair of electrodes, and a dial

      1.5 V   nothing.  0.20 mol of chloride, and 3.8e-17 mol of chlorine
      2.5 V   chlorine.  0.0177 mol, and 8.9e-19 mol of oxygen with it
      3.0 V   oxygen takes over.  the same chlorine, and 5x as much oxygen
      4.0 V   0.53 mol of oxygen.  the barriers have run out

Nothing below scripts any of that. One field on a template says how many
electrons cross the circuit; one argument to ``build_network`` says what the
supply is set to; ``reaction_deltas`` subtracts ``n F E`` from the reaction's
Gibbs energy. Everything else -- the threshold, its value, which product wins,
and where the winning stops -- falls out of formation data this project already
had for other reasons.

WHAT IS EMERGENT HERE, STATED SO IT CAN BE CHECKED

  * nobody wrote down a decomposition potential. Panel 1 derives 1.441 V for
    water and 2.362 V for brine from dGf and divides by ``n F``; the
    electrochemical series says 1.229 and 2.186. **This project has never
    curated an electrode potential.**
  * nobody wrote "brine gives chlorine". Panel 2 puts water splitting and halide
    oxidation in the SAME flask competing for the same volts, and which one wins
    is a ratio of two barriers that were declared in volts of overpotential --
    0.80 V for oxygen evolution, 0.40 V for chlorine, both measured quantities
    with a century of Tafel data behind them.
  * nobody wrote "turn it up too far and you lose selectivity". Panel 2's last
    two rows are the barrier floor arriving.
  * nobody enumerated Kolbe's products. Panel 4 feeds acetate AND propanoate and
    gets ethane, propane and butane, because the two reactant slots fill
    independently -- which is real Kolbe chemistry and a real Kolbe nuisance.
  * nobody wrote the adiponitrile route at all. Panel 5 charges acrylonitrile and
    water, turns the dial to 3 V, and adiponitrile appears -- because the cell
    splits water and the hydrogen it makes couples two acrylonitriles. The
    catalog row's overall stoichiometry, oxygen included, is the SUM of two
    declarations that do not mention each other.

WHAT IT COST: ``ReactionTemplate.electrons``, ``ConcreteReaction.electrical_work``,
one ``if`` in ``reaction_deltas`` and a keyword on ``build_network``. No new term
in Layer 4, no new phase, no new gate. The reason is in
``ReactionTemplate``'s docstring: **Evans-Polanyi with the cell's work inside dH
IS the Butler-Volmer equation, and ``alpha`` IS the transfer coefficient.**

⚠ AND WHAT IT DOES NOT MODEL, BECAUSE PANEL 3 MEASURES IT. There is no CURRENT
BUDGET. A real supply delivers a fixed number of electrons per second and the
electrode reactions divide them; here they divide nothing, so every reaction the
cell clears runs at its own full rate at once. That is why the selectivity window
in this engine is 2.2-2.7 V while a real chloralkali cell holds 99% selectivity
at 3 V and above. Same shape as the site balance: right at low loading, wrong at
high.

⚠ AND ONE NUMBER HERE IS KNOWN WRONG: see ``validation/cell_potentials.py``
panel 2. dG survives the ion table's mixed basis and dS does not, so E_dec at
298 K is quotable to about 8% and its TEMPERATURE DERIVATIVE has the wrong sign.
Nothing below heats a cell, for that reason.
"""

from rdkit import RDLogger

from chemsim.constants import R
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.electrolyte import (
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions import electrochemistry
from chemsim.reactions.reaction import ConcreteReaction
from chemsim.reactions.thermo import decomposition_potential
from chemsim.vessel import Vessel

# See validation/cell_potentials.py for why, and for why it is not set in src/.
RDLogger.DisableLog("rdApp.*")

NA, CL, WATER = "[Na+]", "[Cl-]", "O"
CL2, H2, O2, OH = "ClCl", "[H][H]", "O=O", "[OH-]"
ACETATE, PROPANOATE = "CC(=O)[O-]", "CCC(=O)[O-]"
ETHANE, PROPANE, BUTANE, CO2 = "CC", "CCC", "CCCC", "O=C=O"
AN, ADN = "C=CC#N", "N#CCCCCC#N"

# S2 swept the default tolerance across eleven examples and found nothing
# quotable moves. This file follows the stiff examples' setting because an
# electrode reaction at a floored barrier is as fast as anything in the project.
CONVERGED = dict(rtol=1.0e-8, atol=1.0e-11)

VOLTAGES = (1.5, 2.0, 2.5, 3.0, 4.0)


def brine_cell(templates, thermo, vol, E, feed=None):
    """A network for one flask at one voltage. Two cells at two voltages are two
    networks -- see ``build_network``'s note on why the potential is declared at
    build time rather than on the vessel."""
    return build_network(
        feed or [NA, CL, WATER], templates, thermo=thermo, volatility=vol,
        max_species=80, generations=3, cell_potential=E,
    )


def charged(net, *, volume=1.0, T=298.15, **amounts):
    """A sealed, thermostatted cell. Sealed so the gases stay countable."""
    v = Vessel(net, volume=volume, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge(amounts, phase="liquid")
    return v


def _yield_of(v, species):
    """Totals across every phase -- the gases leave the liquid and must still count."""
    st = v.state()
    return {s: st.total(s) for s in species}


def main() -> None:
    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    prov = electrolyte_provider(base=thermo, volatility=vol)
    templates = electrochemistry() + dissociation_templates()

    # ------------------------------------------------------------------ 1
    print("=" * 74)
    print("PANEL 1 -- THE THRESHOLD, DERIVED AND NOT DECLARED")
    print("=" * 74)
    print("   E_dec = dG_chem / (n F). Nothing in src/ curates an electrode")
    print("   potential; these come out of the same dGf table that fixes every")
    print("   other equilibrium in the project.")
    print()
    for label, r, p, n, book in (
        ("2 H2O -> 2 H2 + O2", (WATER, WATER), (H2, H2, O2), 4, 1.229),
        ("2 Cl- + 2 H2O -> Cl2 + H2 + 2 OH-",
         (CL, CL, WATER, WATER), (CL2, H2, OH, OH), 2, 2.186),
    ):
        rx = ConcreteReaction("panel1", r, p, A=1.0, Ea=0.0, phase="liquid")
        E = decomposition_potential(rx, prov, n, 298.15, vol)
        print(f"   {label:36s} n={n}   E_dec = {E:.3f} V"
              f"   (book {book:.3f} V, {E - book:+.3f})")
    print()
    print("   Below those voltages the cell is not slow. It is at equilibrium")
    print("   the other way round, which is a different statement and the one")
    print("   panel 2 measures.")

    # ------------------------------------------------------------------ 2
    print()
    print("=" * 74)
    print("PANEL 2 -- ONE FLASK OF BRINE, FIVE SETTINGS OF THE DIAL")
    print("=" * 74)
    print("   0.20 mol NaCl in 1 L of water, sealed, 298 K, one hour.")
    print("   water splitting and halide oxidation are BOTH in the network,")
    print("   competing for the same volts. Nothing picks the winner.")
    print()
    print(f"   {'E (V)':>6s} {'Cl2 (mol)':>12s} {'O2 (mol)':>12s} "
          f"{'H2 (mol)':>12s} {'OH- (mol)':>12s}   what it is")
    for E in VOLTAGES:
        net = brine_cell(templates, prov, vol, E)
        v = charged(net, **{NA: 0.20, CL: 0.20, WATER: 55.35})
        v.run(3600.0, **CONVERGED)
        y = _yield_of(v, [CL2, O2, H2, OH])
        if y[CL2] < 1e-9 and y[O2] < 1e-9:
            verdict = "nothing -- below both thresholds"
        elif y[O2] < y[CL2] * 1e-3:
            verdict = "chlorine, clean"
        elif y[O2] < y[CL2]:
            verdict = "chlorine, and oxygen with it"
        else:
            verdict = "mostly oxygen -- selectivity gone"
        print(f"   {E:6.2f} {y[CL2]:12.3e} {y[O2]:12.3e} {y[H2]:12.3e} "
              f"{y[OH]:12.3e}   {verdict}")
    print()
    print("   ! THE CHLORINE PLATEAUS AND THE OXYGEN DOES NOT, AND THAT IS THE")
    print("   WHOLE MECHANIC IN ONE COLUMN. Above 2.5 V the halide reaction's")
    print("   barrier is already floored, so more volts buy it nothing and it")
    print("   sits at 0.0177 mol. Oxygen's barrier is still coming down, so it")
    print("   goes 8.9e-19 -> 0.091 -> 0.53 mol. The chloride is a charge that")
    print("   runs out; the water is the solvent and does not.")

    # ------------------------------------------------------------------ 3
    print()
    print("=" * 74)
    print("PANEL 3 -- WHY IT WINS, AND WHERE THE WINNING STOPS")
    print("=" * 74)
    print("   Ea on an electrode template is the ACTIVATION OVERPOTENTIAL in")
    print("   energy units, n F eta_a: the volts a real cell needs ON TOP of")
    print("   its decomposition potential. Oxygen evolution is the sluggish")
    print("   one at 0.80 V; chlorine on a coated anode is 0.40 V.")
    print()
    print(f"   {'E (V)':>6s} {'Ea water':>12s} {'Ea brine':>12s} "
          f"{'k_brine/k_water':>18s}")
    import math
    tmpl = {t.name: t for t in electrochemistry()}
    for E in (1.5, 2.0, 2.5, 3.0, 4.0):
        net = brine_cell(templates, prov, vol, E)
        ks, eas = {}, {}
        for rxn in net.reactions:
            if rxn.name in ("water_electrolysis", "halide_electrolysis"):
                eas[rxn.name] = rxn.Ea
                ks[rxn.name] = rxn.A * math.exp(-rxn.Ea / (R * 298.15))
        ratio = ks["halide_electrolysis"] / ks["water_electrolysis"]
        print(f"   {E:6.2f} {eas['water_electrolysis']/1000:9.1f} kJ "
              f"{eas['halide_electrolysis']/1000:9.1f} kJ {ratio:18.2e}")
    print()
    print("   Both barriers reach the floor at zero, and once they do the two")
    print("   reactions run at the same bare pre-exponential. A real cell is")
    print("   transport-limited there; this one is limited by nothing, because")
    print("   nothing here budgets CURRENT. That is the named gap, measured.")
    del tmpl

    # ------------------------------------------------------------------ 4
    print()
    print("=" * 74)
    print("PANEL 4 -- KOLBE, AND THE PRODUCT NOBODY ASKED FOR")
    print("=" * 74)
    print("   0.10 mol sodium acetate AND 0.10 mol sodium propanoate, 3.0 V.")
    print("   The template couples [#6] to [#6] across two independent slots,")
    print("   so the mixture is not two reactions. It is three.")
    print()
    net = brine_cell(templates, prov, vol, 3.0,
                     feed=[NA, ACETATE, PROPANOATE, WATER])
    v = charged(net, **{NA: 0.20, ACETATE: 0.10, PROPANOATE: 0.10,
                        WATER: 55.35})
    v.run(3600.0, **CONVERGED)
    y = _yield_of(v, [ETHANE, PROPANE, BUTANE, CO2])
    for s, label in ((ETHANE, "ethane   (acetate + acetate)"),
                     (PROPANE, "propane  (acetate + propanoate)  <- the CROSS"),
                     (BUTANE, "butane   (propanoate + propanoate)"),
                     (CO2, "carbon dioxide")):
        print(f"      {label:44s} {y[s]:12.4e} mol")
    print()
    print("   Nobody wrote the cross-coupling down. It is what happens when a")
    print("   two-slot template meets a two-component mixture, and it is the")
    print("   reason preparative Kolbe is run on ONE carboxylate.")
    print()
    print("   ! READ THE RATIO AS RATE CONSTANTS, NOT AS A SELECTIVITY")
    print("   PREDICTION. 1.49 : 0.98 : 0.57 is exactly the three k's, which")
    print("   Evans-Polanyi set from three slightly different dH. The")
    print("   STATISTICAL factor is not in it: A + B has two ordered pairings")
    print("   and A + A has one, so a symmetric treatment would put the cross")
    print("   at twice the homo-couplings rather than level with them. That is")
    print("   this engine's mass-action convention everywhere, not something")
    print("   the cell does -- the rate constant absorbs it.")

    # ------------------------------------------------------------------ 5
    print()
    print("=" * 74)
    print("PANEL 5 -- A ROUTE FROM TWO DECLARATIONS THAT DO NOT MENTION EACH OTHER")
    print("=" * 74)
    print("   The catalog reads: acrylonitrile + water -> adiponitrile + oxygen.")
    print("   Charged below: acrylonitrile and water. Nothing else.")
    print()
    print("      reactions/electrochemistry.py   2 H2O -> 2 H2 + O2   (electrons=4)")
    print("      reactions/electrochemistry.py   2 AN + H2 -> ADN     (electrons=0)")
    print("      " + "-" * 58)
    print("      what the flask does             2 AN + H2O -> ADN + 1/2 O2")
    print()
    for E in (1.0, 2.0, 3.0):
        net = brine_cell(templates, prov, vol, E, feed=[AN, WATER])
        v = charged(net, **{AN: 0.20, WATER: 55.35})
        v.run(3600.0, **CONVERGED)
        y = _yield_of(v, [ADN, O2, AN])
        conv = 100.0 * (0.20 - y[AN]) / 0.20
        print(f"      {E:.1f} V   adiponitrile {y[ADN]:10.4e} mol"
              f"   O2 {y[O2]:10.4e} mol   AN converted {conv:6.2f}%")
    print()
    print("   ! THE COUPLING IS NOT WHAT THE VOLTAGE PAYS FOR, AND THAT IS A")
    print("   MEASUREMENT. 2 AN + H2 -> ADN is downhill on its own at")
    print("   -171.7 kJ/mol; the whole cell 4 AN + 2 H2O -> 2 ADN + O2 is uphill")
    print("   at +212.7. What the supply buys is the hydrogen, not the bond.")
    print("   ! The cost of decomposing it that way is that the route cannot")
    print("   start until WATER can split, at 1.441 V, where the real cell")
    print("   reduces acrylonitrile at its own cathode from 0.551 V. Baizer's")
    print("   cell runs near 4 V, so nothing about whether it RUNS turns on it.")


if __name__ == "__main__":
    main()

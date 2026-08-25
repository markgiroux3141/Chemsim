"""A GAS ARRIVING AT A CRYSTAL -- roasting an ore, and the gate a catalyst is.

    NATURE                        THE ROASTER
      sphalerite  --air, red heat-->  zincite  +  SO2 (to the acid plant)
      (ZnS ore)                        |
                                       | reduction furnace
                                       v
                                      zinc

    AND THE OTHER HALF OF THE SAME FEATURE

      N2 + 3 H2  --over IRON-->  2 NH3          (and with no iron: nothing)

M6 built the reaction that happens INSIDE a crystal and evolves a gas -- a lime
kiln. It could not build the reaction where the gas ARRIVES, and it measured why:
an affinity quotient puts a gas REACTANT's pressure in a denominator, so an
atmosphere depleted of it drives the reverse flux to 2.6e15 formula units per
second. This is that reaction, and nothing below scripts an outcome:

  * there is no "blow air through it" rule. Panel 2 is a sealed flask and it
    stalls at 1.5%, because a litre of air holds 2.3 mmol of oxygen and 0.1 mol
    of ore needs 150.
  * nothing declares that a roaster needs no fuel. Panel 3 insulates one and it
    heats itself from 1100 K to over 1900 K, which is -883 kJ/mol of reaction
    enthalpy doing what it does.
  * nothing declares "you need a catalyst" either. Panel 4 is a flask of nitrogen
    and hydrogen at 700 K, and it makes EXACTLY ZERO ammonia until iron is put in
    it -- which is a wrong answer this project reported for several sessions
    rather than hid.

⚠ **AND THE BRIEF FOR THIS ASKED FOR A THIRD ``PHASE_INDEX`` ENTRY, WHICH IT IS
NOT.** Panel 5 is that measurement. Labelling a solid-catalysed gas reaction
"solid" moves it onto the pure-liquid standard state, because ``reaction_deltas``
shifts anything that is not ``"gas"``: dG by -99.7 kJ/mol, K by 2.6e10 at 500 K.
So the catalyst is a factor in a GAS reaction's rate law, and roasting -- whose
reactant is a lattice no gas-basis provider will price -- is a TERM.
``properties/surface.py`` carries the whole argument.
"""

from chemsim.constants import R_L_BAR
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties import surface as sf
from chemsim.properties.mineral_data import MINERALS
from chemsim.reactions.library import SOLID_CATALYST_REFERENCE
from chemsim.reactions.synthesis import ammonia_synthesis
from chemsim.vessel import Vessel

SPHALERITE = MINERALS["sphalerite"].lattice        # ZnS, the zinc ore
ZINCITE = MINERALS["zincite"].lattice              # ZnO, what roasting gives
GALENA = MINERALS["galena"].lattice                # PbS
LITHARGE = MINERALS["litharge"].lattice            # PbO
IRON = MINERALS["iron"]
O2, SO2, N2, H2, AMMONIA = "O=O", "O=S=O", "N#N", "[H][H]", "N"

# ⚠ THE DEFAULT SOLVER TOLERANCE IS NOT CONVERGED FOR A FLASK ON A VENT, and M6
# measured that at 2.6x in a kiln's conversion -- with the tight run also being
# several times FASTER, because the loose one thrashes. Every number below is at
# the tight setting for that reason.
CONVERGED = dict(rtol=1.0e-8, atol=1.0e-11)

ORE = [SPHALERITE, ZINCITE, GALENA, LITHARGE, O2, SO2, N2]


def air_at(T: float) -> dict:
    """One bar of air, as moles in a litre at T."""
    return {O2: 0.21 / (R_L_BAR * T), N2: 0.79 / (R_L_BAR * T)}


def roaster(net, T, *, blown, charge, UA=1.0e4, volume=1.0):
    """A flask of ore. ``blown`` feeds air in the way a real roaster does."""
    ingress = {}
    if blown:
        # Three times the stoichiometric oxygen over the run, so that the roast
        # is never oxygen-limited. This is the blast, and it is the only thing
        # panels 2 and 3 differ from panel 2 by.
        ingress = {O2: 0.45 / 1800.0, N2: 0.45 * (79.0 / 21.0) / 1800.0}
    v = Vessel(net, volume=volume, T=T, T_env=T, UA=UA, ingress=ingress,
               k_vent=1.0e3 if blown else 0.0)
    v.charge(charge, phase="solid")
    v.charge(air_at(T), phase="gas")
    return v


def main() -> None:
    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    ore_net = build_network(ORE, [], thermo=thermo, volatility=vol)

    print("=" * 74)
    print("PANEL 1 -- the declarations, and the CLOCK (there is no threshold)")
    print("=" * 74)
    v = roaster(ore_net, 1100.0, blown=False, charge={SPHALERITE: 0.1})
    print(v.surface_report())
    print()
    print("   NOTE WHAT IS MISSING: a threshold temperature. M6's kiln has one,")
    print("   because it is under THERMODYNAMIC control and stops at Q = K. A")
    print("   roast is under KINETIC control -- ln K is 67.6 to 78.8 at these")
    print("   temperatures, so the reverse is 20-25 decades down and there is no")
    print("   temperature below which nothing happens. What there is instead is")
    print("   a clock, and the clock does NOT depend on how much ore you charge:")
    print("   first order in the solid means tau = 1/(k C_O2). A bigger bed is")
    print("   more throughput, not a longer roast.")
    print()
    priced = {d.name: sf.price(d, thermo) for d in sf.SURFACE_REACTIONS}
    print(f"   {'row':24} {'dH/kJ':>8} {'ln K':>7} {'k(T_run)':>9} "
          f"{'tau/s':>9}   what it is")
    for name, p in priced.items():
        C = 0.21 / (R_L_BAR * p.decl.T_run)
        print(f"   {name:24} {p.dH / 1000:8.1f} {p.ln_K_run:7.1f} "
              f"{sf.rate_constant(p, p.decl.T_run):9.4g} "
              f"{sf.time_constant(p, p.decl.T_run, C):9.0f}   "
              f"{p.decl.T_run:.0f} K, {p.decl.mechanism}")
    print()
    print("   AND THE SHARED CLOCK IS A CLAIM, WHICH THIS PANEL LETS YOU CHECK.")
    print("   One barrier and one pre-exponential cover every row -- the claim")
    print("   being that an O2 molecule arriving at a sulfide surface is the same")
    print("   event each time. It is only partly true: cinnabar's own retort runs")
    print("   at 900 K and one shared barrier makes it 31x slower there than a")
    print("   zinc roaster at 1100 K, which the catalog contradicts. The one")
    print("   mechanism this project has for fixing that -- Evans-Polanyi on the")
    print("   reaction enthalpy -- gets the ordering BACKWARDS: sphalerite is the")
    print("   MOST exothermic row and needs the HOTTEST furnace.")

    print()
    print("=" * 74)
    print("PANEL 2 -- SEAL THE FLASK and it stalls. Nobody wrote this rule.")
    print("=" * 74)
    v = roaster(ore_net, 1100.0, blown=False, charge={SPHALERITE: 0.1})
    v.run(20_000.0, **CONVERGED)
    st = v.state()
    print("   charged 0.1 mol of sphalerite and 1 bar of air, sealed, 20 ks")
    print(f"     oxygen available   {air_at(1100.0)[O2]:.6f} mol")
    print(f"     oxygen NEEDED      {0.1 * 1.5:.6f} mol   (3 O2 per 2 ZnS)")
    print(f"     converted          {100 * st.total(ZINCITE) / 0.1:.2f}%")
    print(f"     oxygen left        {st.total(O2):.3e} mol")
    print(f"     zinc, in / out     0.1 / {st.total(SPHALERITE) + st.total(ZINCITE):.12f}")
    print()
    print("   THAT is why a roaster blows air, and it is the same shape as M6's")
    print("   kiln needing its CO2 swept away -- an open end, not a temperature.")

    print()
    print("=" * 74)
    print("PANEL 3 -- BLOW AIR THROUGH IT. And then take the wall away.")
    print("=" * 74)
    print(f"   {'wall':>12} {'converted':>10} {'T end / K':>10} "
          f"{'zinc closure':>14}   ")
    for label, UA in (("UA 1e4 W/K", 1.0e4), ("INSULATED", 0.0)):
        v = roaster(ore_net, 1100.0, blown=True, charge={SPHALERITE: 0.1},
                    UA=UA)
        v.run(1800.0, **CONVERGED)
        st = v.state()
        zn = st.total(SPHALERITE) + st.total(ZINCITE)
        print(f"   {label:>12} {100 * st.total(ZINCITE) / 0.1:9.2f}% "
              f"{st.T:10.1f} {zn:14.12f}")
    print()
    print("   THE INSULATED ROW IS AUTOTHERMAL ROASTING AND NOTHING DECLARES IT.")
    print("   A zinc roaster burns no fuel; -883 kJ per mole of reaction is why.")
    print("   The vent is what stops it running away -- gas leaving at T carries")
    print("   the heat out, which is also what a real off-gas duct does.")

    print()
    print("   TWO ORES IN ONE FLASK, sharing one blast of air:")
    v = roaster(ore_net, 1100.0, blown=True,
                charge={SPHALERITE: 0.05, GALENA: 0.05})
    v.run(1800.0, **CONVERGED)
    st = v.state()
    print(f"     zincite  {st.total(ZINCITE):.6f} mol   "
          f"zinc closure {st.total(SPHALERITE) + st.total(ZINCITE):.12f}")
    print(f"     litharge {st.total(LITHARGE):.6f} mol   "
          f"lead closure {st.total(GALENA) + st.total(LITHARGE):.12f}")
    print(f"     SO2 in the flask {st.total(SO2):.6f} mol (the rest went out the")
    print("       vent, which is where an acid plant would be)")

    print()
    print("=" * 74)
    print("PANEL 4 -- THE GATE. A flask with no iron in it makes NO ammonia.")
    print("=" * 74)
    net = build_network([N2, H2], [ammonia_synthesis()], thermo=thermo,
                        volatility=vol)
    print("   the network carries the catalyst whether or not you charge it:")
    print(f"     species  {net.species}")
    print()
    print(f"   {'iron / mol':>12} {'NH3 / mol':>12} {'% of theory':>12}")
    for iron in (0.0, 1.0e-6, 1.0e-3, SOLID_CATALYST_REFERENCE, 1.0):
        v = Vessel(net, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4, k_vent=0.0)
        v.charge({N2: 0.25, H2: 0.75}, phase="gas")
        if iron:
            v.charge({IRON.lattice: iron}, phase="solid")
        v.run(600.0, **CONVERGED)
        st = v.state()
        note = ""
        if iron == 0.0:
            note = "   <- EXACTLY zero, not small"
        elif iron == SOLID_CATALYST_REFERENCE:
            note = "   <- the reference charge"
        print(f"   {iron:12.4g} {st.total(AMMONIA):12.8f} "
              f"{100 * st.total(AMMONIA) / 0.5:11.2f}%{note}")
        assert st.total(IRON.lattice) == iron    # a constant of the motion
    print()
    print("   THE IRON DOES NOT MOVE BY ONE BIT in any of those runs, and that is")
    print("   what makes it unable to seed itself -- the failure mode a")
    print("   round-off-seeded lead chamber reached 89% yield on. A catalyst has")
    print("   zero stoichiometry on both sides, so its row of the state")
    print("   derivative is identically zero and there is no gain to have.")
    print()
    print("   AND AT THE REFERENCE CHARGE IT IS THE SAME REACTION IT ALWAYS WAS.")
    print(f"   A(catalysed) * {SOLID_CATALYST_REFERENCE} = "
          f"{ammonia_synthesis().A * SOLID_CATALYST_REFERENCE:.6g}, against the")
    print(f"   {ammonia_synthesis(catalyst=None).A:.6g} the folded template")
    print("   declares -- equal, exactly. So every ammonia number this project")
    print("   has ever measured is reproduced with 0.1 mol of iron in the flask,")
    print("   and `examples/named_routes.py` still reads 76.3% at 700 K.")
    print("   What is NOT modelled is the site balance: ten times the iron is")
    print("   ten times the rate, for ever. Right at low coverage, wrong at high.")

    print()
    print("=" * 74)
    print("PANEL 5 -- WHY THIS IS NOT A THIRD PHASE, WHICH THE BRIEF ASKED FOR")
    print("=" * 74)
    from chemsim.reactions.thermo import reaction_deltas
    import dataclasses
    import math
    from chemsim.constants import R

    fwd = next(r for r in net.reactions if r.name == "ammonia_synthesis")
    dH_g, dG_g = reaction_deltas(fwd, thermo, vol)
    dH_s, dG_s = reaction_deltas(
        dataclasses.replace(fwd, phase="solid"), thermo, vol
    )
    print("   N2 + 3 H2 -> 2 NH3, over iron, priced two ways:")
    print(f"     as phase='gas'     dH {dH_g:+9.3f}  dG {dG_g:+9.3f} kJ/mol")
    print(f"     as phase='solid'   dH {dH_s:+9.3f}  dG {dG_s:+9.3f} kJ/mol")
    print(f"     SHIFT              dH {dH_s - dH_g:+9.3f}  "
          f"dG {dG_s - dG_g:+9.3f} kJ/mol")
    for T in (500.0, 700.0):
        r = math.exp(-(dG_s - dG_g) * 1000.0 / (R * T))
        print(f"     K({T:.0f} K) would be {r:.4g}x what it is")
    print()
    print("   `reaction_deltas` shifts anything that is not 'gas' onto the")
    print("   pure-liquid standard state. So the phase LABEL is not a name, it is")
    print("   a choice of thermodynamics -- and this is verbatim the failure the")
    print("   PHASE_INDEX comment was written to prevent, arriving at the line it")
    print("   is written on ('phase=any silently became liquid').")
    print()
    print("   A solid-catalysed gas reaction IS a gas-phase reaction: every")
    print("   participant that has an ACTIVITY is a gas, and a pure solid's")
    print("   activity is 1. And roasting cannot be priced on the ideal-gas basis")
    print("   at all -- its reactant is a lattice, which `thermochemistry`")
    print("   refuses by name. So one is a rate-law factor and the other is a")
    print("   term, and PHASE_INDEX has two entries for the SECOND milestone")
    print("   running, for a different reason each time.")


if __name__ == "__main__":
    main()

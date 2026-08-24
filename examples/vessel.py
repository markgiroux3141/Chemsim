"""Layer 5 demo: a flask that works out its own temperature.

Every number printed below is computed. There is no boiling point in the code, no
"if boiling then hold temperature", no distillation model, no yield table. There
is a reaction template, a set of molecules, and an energy balance.

  Part 1  heating ethanol -- the temperature plateau IS the boiling point
  Part 2  the same flask boiled dry -- and what happens next
  Part 3  cooled vs. insulated esterification -- an exotherm that spoils its
          own yield by heating itself
  Part 4  the vapour above a mixture -- distillation, for free
"""

from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import ReactionTemplate, equilibrium_constant_c
from chemsim.vessel import Vessel

THERMO = ThermochemistryProvider()
FISCHER = ReactionTemplate(
    name="fischer_esterification",
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000, reversible=True,
)
NET = build_network(["CC(=O)O", "CCO", "O"], [FISCHER], thermo=THERMO)
INERT = build_network(["CCO", "O"], [], thermo=THERMO)

ACID, ETHANOL, WATER, ESTER = "CC(=O)O", "CCO", "O", "CCOC(C)=O"


print("=== Part 1: heat 3 mol of ethanol with a 60 W hotplate ===")
v = Vessel(NET, volume=0.5, T=298.15, T_env=298.15, UA=0.5, Q_input=60.0, kla=5.0)
v.charge({ETHANOL: 3.0})
print("  ethanol's real boiling point: 351.4 K")
print(f"  bubble point from our own vapour-pressure model: {v.bubble_point():.2f} K")
print(f"  {'t (s)':>6}{'T (K)':>9}{'P (bar)':>10}{'V_liq (mL)':>12}   state")
for _ in range(10):
    v.step(90.0)
    print(f"  {v.t:>6.0f}{v.T:>9.2f}{v.pressure:>10.3f}{v.liquid_volume * 1000:>12.1f}"
          f"   {'boiling' if v.is_boiling else 'heating'}")
print("  The plateau is not a cap that was set anywhere -- evaporation runs away")
print("  once the vapour pressure reaches ambient, and the latent heat eats the 60 W.")


print("\n=== Part 2: a small charge, boiled dry ===")
v = Vessel(NET, volume=0.5, T=340.0, UA=0.2, Q_input=80.0, kla=5.0)
v.charge({ETHANOL: 0.3})
for _ in range(9):
    v.step(35.0)
    liq = sum(v.state().n_liquid.values())
    print(f"  t={v.t:>5.0f}s  T={v.T:>7.2f} K  liquid={liq:.5f} mol"
          f"   {'boiling' if v.is_boiling else ''}")
print("  Once there is nothing left to vaporize, the plateau ends by itself.")


print("\n=== Part 3: the same esterification in two different flasks ===")
print(f"  {'flask':<12}{'UA (W/K)':>10}{'T final':>10}{'K(T)':>8}{'ester (mol)':>13}")
for label, UA in (("cooled", 2.0), ("insulated", 0.02)):
    v = Vessel(NET, volume=1.0, T=298.15, T_env=298.15, UA=UA, kla=2.0)
    v.charge({ACID: 4.0, ETHANOL: 4.0})
    v.run(7200.0)
    fwd = next(r for r in NET.reactions if r.name == FISCHER.name)
    K = equilibrium_constant_c(fwd, THERMO, v.T, NET.volatility)
    print(f"  {label:<12}{UA:>10.2f}{v.T:>10.2f}{K:>8.2f}"
          f"{v.state().n_liquid[ESTER]:>13.4f}")
print("  The insulated flask runs hotter and ends up with LESS product: its own")
print("  exotherm pushed the equilibrium constant down. Nobody wrote that rule.")


print("\n=== Part 4: the vapour above a 50/50 ethanol/water mixture ===")
v = Vessel(INERT, volume=1.0, T=298.15, T_env=298.15, UA=5.0, kla=2.0)
v.charge({ETHANOL: 2.0, WATER: 2.0})
v.run(20000.0)
x, p = v.mole_fractions(), v.partial_pressures()
total = sum(p.values())
print(f"  {'species':<10}{'liquid x':>10}{'vapour y':>10}")
for s, name in ((ETHANOL, "ethanol"), (WATER, "water")):
    print(f"  {name:<10}{x[s]:>10.3f}{p[s] / total:>10.3f}")
alpha = (p[ETHANOL] / p[WATER]) / (x[ETHANOL] / x[WATER])
print(f"  relative volatility alpha = {alpha:.2f}")
print("  A vapour richer than the liquid is the whole basis of distillation, and")
print("  it is just Raoult's law -- no separation model exists in this codebase.")
print("  (Ideal Raoult, so no azeotrope: real ethanol/water stalls at 95.6%.")
print("   Activity coefficients are the next refinement, not an oversight.)")

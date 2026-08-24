"""Layers 5-6 demo: three phases, ions, and a headless engine driving it all.

Everything below is computed. There is no boiling point, no melting point, no
solubility table, no pH solver, no buffer equation and no separation model
anywhere in the codebase.

  Part 1  crystallisation -- dissolve hot, cool, collect
  Part 2  melting a dry solid, and the latent-heat plateau on the way
  Part 3  acid/base -- pH, buffers and a titration, from mass action alone
  Part 4  the engine -- scheduled events, two vessels, save and reload
"""

import json

from chemsim.engine import Scenario, TemplateSpec, VesselSpec, World
from chemsim.engine.events import CHARGE, SET_HEAT, TRANSFER
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import (
    ThermochemistryProvider,
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.vessel import Vessel

THERMO = ThermochemistryProvider()
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
WATER = "O"


print("=== Part 1: recrystallisation of benzoic acid ===")
solid_net = build_network([WATER, BENZOIC], [], thermo=THERMO)
t = THERMO.get(BENZOIC)
print(f"  Tm = {t.Tm:.1f} K, Hfus = {t.Hfus:.1f} kJ/mol  (both estimated from structure)")
print(f"  {'T (K)':>7}{'dissolved':>12}{'solid':>10}   x / x_sat")
for T in (350.0, 320.0, 295.0, 275.0):
    v = Vessel(solid_net, volume=1.0, T=T, T_env=T, UA=50.0, kla=0.0, k_diss=0.05)
    v.charge({WATER: 8.0})
    v.charge({BENZOIC: 3.0}, phase="solid")
    v.run(20000.0)
    st = v.state()
    print(f"  {T:>7.1f}{st.n_liquid[BENZOIC]:>12.4f}{st.n_solid[BENZOIC]:>10.4f}"
          f"   {v.saturation().get(BENZOIC, 0):.3f}")
print("  Solubility is exp(-Hfus/R (1/T - 1/Tm)) -- one equation, no table.")


print("\n=== Part 2: melting a dry solid ===")
v = Vessel(solid_net, volume=1.0, T=300.0, T_env=300.0, UA=0.0,
           Q_input=60.0, kla=0.0, k_diss=0.05)
v.charge({BENZOIC: 2.0}, phase="solid")
for _ in range(9):
    v.step(200.0)
    st = v.state()
    bar = "#" * int(20 * st.n_solid[BENZOIC] / 2.0)
    print(f"  t={v.t:5.0f}s  T={v.T:7.2f} K  solid {st.n_solid[BENZOIC]:6.4f} {bar}")
print(f"  The stall near {t.Tm:.0f} K is latent heat of fusion. Same mechanism as")
print("  the boiling plateau, and equally unscripted.")


print("\n=== Part 3: acid/base chemistry ===")
ACID_THERMO = electrolyte_provider()
TEMPLATES = dissociation_templates()
acid_net = build_network(
    [WATER, "CC(=O)O", "[OH-]", "[Na+]"], TEMPLATES,
    thermo=ACID_THERMO, max_species=60,
)
print("  ions discovered by the network builder:",
      [s for s in acid_net.species if Molecule.from_smiles(s).charge != 0])


def equilibrate(charge):
    v = Vessel(acid_net, volume=1.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0, k_diss=0.0)
    v.charge(charge)
    v.run(3000.0)
    return v


print(f"\n  {'system':<36}{'pH':>6}   expected")
print(f"  {'pure water':<36}{equilibrate({WATER: 55.34}).pH:>6.2f}   7.00")
for c in (1.0, 0.1, 0.01):
    v = equilibrate({WATER: 55.34, "CC(=O)O": c})
    print(f"  {f'{c} M acetic acid':<36}{v.pH:>6.2f}   "
          f"{0.5 * (4.76 - __import__('math').log10(c)):.2f} (Henderson-Hasselbalch)")

print("\n  titrating 0.1 M acetic acid with NaOH:")
for naoh in (0.0, 0.025, 0.05, 0.075, 0.099, 0.1, 0.12):
    v = equilibrate({WATER: 55.34, "CC(=O)O": 0.1, "[OH-]": naoh, "[Na+]": naoh})
    note = ""
    if abs(naoh - 0.05) < 1e-9:
        note = "  <- half-neutralised: pH = pKa exactly"
    if abs(naoh - 0.1) < 1e-9:
        note = "  <- equivalence point (basic, because acetate is a weak base)"
    print(f"    {naoh:5.3f} equiv NaOH -> pH {v.pH:5.2f}{note}")
print("  No buffer equation exists in this codebase. Dissociation is entered as")
print("  ordinary reversible reactions and detailed balance supplies every Ka.")


print("\n=== Part 4: the engine ===")
FISCHER = TemplateSpec(
    name="fischer", A=1.0e6, Ea=50_000, reversible=True,
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
)
scenario = Scenario(
    templates=[FISCHER],
    feed_species=["CC(=O)O", "CCO", WATER],
    vessels={
        "flask": VesselSpec(volume=1.0, T=298.15, UA=0.5),
        "receiver": VesselSpec(volume=1.0, T=290.0, UA=0.5),
    },
)
world = World(scenario=scenario, seed=7)
world.schedule(0.0, CHARGE, "flask", amounts={"CC(=O)O": 3.0, "CCO": 3.0})
world.schedule(60.0, SET_HEAT, "flask", watts=40.0)
world.schedule(1800.0, TRANSFER, "flask", to="receiver", fraction=0.5)
world.run(3600.0, dt=300.0)
print(world.describe())
for line in world.transfer_log:
    print(f"  {line}")

blob = json.dumps(world.save())
reloaded = World.load(json.loads(blob))
a = world.vessels["flask"].state()
b = reloaded.vessels["flask"].state()
print(f"\n  save = {len(blob)} bytes of JSON. The reaction network is REBUILT on load,")
print("  not stored -- a save holds templates and moles, never molecules.")
print(f"  round trip exact: T {a.T == b.T}, contents {a.n_liquid == b.n_liquid}")

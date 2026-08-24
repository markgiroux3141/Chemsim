"""Liquid-liquid extraction: a separatory funnel, driven entirely by events.

Two things are being shown at once, and they are independent.

**The chemistry.** Nothing here declares that water and toluene are immiscible,
which layer is on the bottom, or how benzoic acid divides between them. The
liquid separates because a tangent-plane test finds the single phase unstable;
the layers order themselves by densities computed from molar masses and molar
volumes the vessel already had; and the acid partitions until its ACTIVITY is
equal on both sides, which is the same equality the vapour and the solid use.

**The protocol.** Every action below is a scheduled EVENT against a ``World``,
not a method call on a vessel. That is the difference between a script and a
recipe: a run is a pure function of (scenario, event list), so this prep can be
saved mid-way, reloaded, and finished -- which is what the last panel does, and
which is the property a user interface would need.
"""
from chemsim.engine import Scenario, VesselSpec, World
from chemsim.engine.events import (
    CHARGE,
    SET_SHAKING,
    TRANSFER,
)
from chemsim.matter import Molecule

WATER = "O"
TOLUENE = Molecule.from_smiles("Cc1ccccc1").smiles
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
MW = Molecule.from_smiles(BENZOIC).molar_mass

CHARGED = 0.020          # mol of benzoic acid to recover
WATER_MOL = 27.7         # ~500 mL
TOLUENE_MOL = 4.7        # ~500 mL in total, split between the portions

funnel = VesselSpec(volume=3.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)
receiver = VesselSpec(volume=3.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0)

SCENARIO = Scenario(
    feed_species=[WATER, TOLUENE, BENZOIC],
    templates=[],                 # no reaction at all: this is pure separation
    vessels={"funnel": funnel, "organic": receiver, "waste": receiver},
    max_species=20,
)


def rule(title: str) -> None:
    print()
    print("=" * 76)
    print(title)
    print("=" * 76)


def extract(portions: int, total_toluene: float, shake: float = 5.0) -> float:
    """Run the whole extraction as an event list. Returns mol recovered."""
    w = World(SCENARIO)
    t = 0.0
    w.schedule(t, CHARGE, "funnel",
               amounts={WATER: WATER_MOL, BENZOIC: CHARGED})
    w.schedule(t, SET_SHAKING, "funnel", k_lle=shake)
    for _ in range(portions):
        t += 600.0
        w.schedule(t, CHARGE, "funnel",
                   amounts={TOLUENE: total_toluene / portions})
        # ... let it stand and separate, then draw the UPPER layer off. Which
        # layer that is was never declared; it is whichever is less dense.
        t += 600.0
        w.schedule(t, TRANSFER, "funnel", to="organic", phase="upper")
    w.run(duration=t + 600.0, dt=300.0)
    return w.vessels["organic"].state().total(BENZOIC)


# ---------------------------------------------------------------------------
rule("THE SEPARATION -- nothing declares that these two do not mix")
# ---------------------------------------------------------------------------
w = World(SCENARIO)
w.schedule(0.0, CHARGE, "funnel",
           amounts={WATER: WATER_MOL, TOLUENE: TOLUENE_MOL, BENZOIC: CHARGED})
w.run(duration=1800.0, dt=600.0)
v = w.vessels["funnel"]

print(f"  charged {WATER_MOL:.1f} mol water + {TOLUENE_MOL:.1f} mol toluene "
      f"+ {CHARGED * 1000:.0f} mmol benzoic acid, shaken and left to stand")
print()
print(f"  {'':6s} {'volume':>9s} {'density':>9s}   composition")
for d in v.layers():
    top = sorted(d["composition"].items(), key=lambda kv: -kv[1])
    print(f"  layer{d['layer']} {d['volume'] * 1e3:8.1f} mL "
          f"{d['density']:8.3f} kg/L   " +
          ", ".join(f"{s} {x:.4f}" for s, x in top[:3]))
print("""
  Real densities are water 0.997 and toluene 0.867 kg/L, and neither is
  tabulated here -- each layer's density comes out of its own composition
  through the molar masses and the same Rackett molar volumes the integrator
  uses. That is what makes "drain the lower layer" mean the aqueous one here
  and the ORGANIC one if you swap toluene for dichloromethane, with no
  special case and no label attached to a phase index.""")

# ---------------------------------------------------------------------------
rule("THE PARTITION -- and why three small washes beat one big one")
# ---------------------------------------------------------------------------
aq = v.layers()[-1]                       # densest = aqueous
org = v.layers()[0]
print(f"  benzoic acid mole fraction: aqueous {aq['composition'].get(BENZOIC, 0):.2e}"
      f"   organic {org['composition'].get(BENZOIC, 0):.2e}")
print(f"  distribution coefficient (organic/aqueous, by concentration): "
      f"{1.0 / v.partition(BENZOIC):.1f}")
print("""
  Not a tabulated number: it is whatever equality of activity produced, and it
  comes from the same UNIFAC model that puts benzoic acid's water solubility at
  3.26 g/L. Because each contact removes the same FRACTION, splitting the same
  solvent into more portions compounds -- which is the entire reason a chemist
  extracts three times with 30 mL instead of once with 90 mL.
""")
print(f"  {'portions':>9s} {'each':>9s} {'recovered':>12s} {'of charge':>11s}")
for portions in (1, 2, 3, 5):
    got = extract(portions, TOLUENE_MOL)
    print(f"  {portions:9d} {TOLUENE_MOL / portions * 18.0:7.0f} mL "
          f"{got * MW * 1000:9.1f} mg {100 * got / CHARGED:10.1f}%")
print("""
  Monotone, and nothing was told to make it so.""")

# ---------------------------------------------------------------------------
rule("CHOOSING THE SOLVENT -- and the layers swap over by themselves")
# ---------------------------------------------------------------------------
# Same acid, same water, same volume of organic. Everything that differs comes
# out of the activity model and the molar volumes.
SOLVENTS = [
    (TOLUENE, 4.7, "toluene"),
    (Molecule.from_smiles("ClCCl").smiles, 7.8, "dichloromethane"),
    ("CCCCCC", 3.8, "hexane"),
    (Molecule.from_smiles("CCOCC").smiles, 4.8, "diethyl ether"),
]
print(f"  {'solvent':>16s} {'K(org/aq)':>10s} {'organic is':>12s} "
      f"{'3 x 28 mL recovers':>19s}")
for smiles, moles, name in SOLVENTS:
    sc = Scenario(
        feed_species=[WATER, smiles, BENZOIC], templates=[],
        vessels={"funnel": funnel, "organic": receiver, "waste": receiver},
        max_species=20,
    )
    w2 = World(sc)
    w2.schedule(0.0, CHARGE, "funnel",
                amounts={WATER: WATER_MOL, smiles: moles, BENZOIC: CHARGED})
    w2.run(duration=1800.0, dt=600.0)
    f = w2.vessels["funnel"]
    if not f.two_phase:
        print(f"  {name:>16s} {'--':>10s} {'MISCIBLE':>12s} "
              f"{'(no two layers)':>19s}")
        continue
    layers = f.layers()
    organic_index = max(layers, key=lambda d: d["composition"].get(smiles, 0.0))
    side = "on top" if organic_index is layers[0] else "underneath"
    k = f.partition(BENZOIC)
    k = (1.0 / k) if organic_index["layer"] == 1 else k

    w3 = World(sc)
    t = 0.0
    w3.schedule(t, CHARGE, "funnel", amounts={WATER: WATER_MOL, BENZOIC: CHARGED})
    for _ in range(3):
        t += 600.0
        w3.schedule(t, CHARGE, "funnel", amounts={smiles: moles / 3})
        t += 600.0
        w3.schedule(t, TRANSFER, "funnel", to="organic",
                    phase="upper" if side == "on top" else "lower")
    w3.run(duration=t + 600.0, dt=300.0)
    got = w3.vessels["organic"].state().total(BENZOIC)
    print(f"  {name:>16s} {k:10.1f} {side:>12s} {100 * got / CHARGED:17.1f}%")
print("""
  Dichloromethane sinks and toluene floats, so the same recipe has to draw off
  the OTHER layer -- and it does, because "lower" is resolved from the computed
  densities rather than from a label. Diethyl ether is the interesting one: it
  is only partly miscible with water, so its layer carries a lot of dissolved
  water and its numbers are the least trustworthy here.

  WHAT IS NOT SHOWN, and deliberately: how hard the funnel was SHAKEN. One
  coefficient (``k_lle``) carries both the separation of the bulk layers and the
  equilibration of a solute across them, and those are physically different
  processes -- gravity versus interfacial area. Turning it down far enough does
  not model a badly shaken funnel, it models two liquids that never separated,
  which is not a state a bench produces. Splitting them would need a settling
  model this project does not have, so the knob is not offered as one.""")

# ---------------------------------------------------------------------------
rule("IT IS A RECIPE, NOT A SCRIPT -- saved and reloaded mid-extraction")
# ---------------------------------------------------------------------------
w = World(SCENARIO)
w.schedule(0.0, CHARGE, "funnel",
           amounts={WATER: WATER_MOL, BENZOIC: CHARGED})
w.schedule(600.0, CHARGE, "funnel", amounts={TOLUENE: TOLUENE_MOL})
w.schedule(1800.0, TRANSFER, "funnel", to="organic", phase="upper")
w.run(duration=1200.0, dt=600.0)          # stop BEFORE the transfer fires

blob = w.save()
reloaded = World.load(blob)
reloaded.run(duration=1200.0, dt=600.0)   # the pending transfer comes with it
w.run(duration=1200.0, dt=600.0)

a = reloaded.vessels["organic"].state().total(BENZOIC)
b = w.vessels["organic"].state().total(BENZOIC)
print("  saved at t=1200 s with the separation done and the draw still pending")
print(f"  continued in-process:  {b * MW * 1000:.4f} mg recovered")
print(f"  continued from a save: {a * MW * 1000:.4f} mg recovered")
print(f"  difference: {abs(a - b) * MW * 1e6:.3g} ug")
print("""
  The save carries the second liquid layer as its own block, so the funnel comes
  back separated rather than remixed -- and the queued draw is still queued. A
  run is a pure function of (scenario, event list), which is the property an
  interface needs and the reason every action above is an event.""")

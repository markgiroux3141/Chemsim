""""Wait until": the last thing standing between the protocol layer and a frontend.

A real procedure has no durations in it. "Heat until it refluxes, then hold two
hours", "cool until crystals appear", "distil until the pot reaches 110 C" -- every
one of those is a CONDITION, and until now every duration in this project was a
fixed number of seconds. A recipe written against fixed durations encodes the wrong
shape into every screen built on top of it, which is why this is ahead of the
interface rather than behind it.

It is also a RESPONSIVENESS feature, and that is the less obvious half. Wall-clock
cost here is concentrated in stiff transients rather than in elapsed time (see
``validation/wall_clock.py``), so a fixed duration forces a choice between
overshooting the interesting instant and paying for steps that resolve nothing.

    python examples/wait_until.py

⚠ Printed text is ASCII only. The Windows console is cp1252 and a warning glyph
inside a print() kills the script at that line. Docstrings are fine.
"""

import time

from chemsim.engine import Scenario, VesselSpec, World
from chemsim.engine.events import CHARGE, FILL_HEADSPACE, SET_ENVIRONMENT
from chemsim.matter import Molecule
from chemsim.vessel import boils, crystals, reaches, temperature_steady

WATER, ETOH, N2, O2 = "O", "CCO", "N#N", "O=O"

print(__doc__.split("\n\n")[0])
print("=" * 74)
print("PART 1  heat a flask until it refluxes -- and find out WHEN, not guess")
print("=" * 74)

spec = VesselSpec(volume=2.0, T=298.15, T_env=298.15, UA=0.5, Q_input=60.0,
                  kla=5.0)
scenario = Scenario(feed_species=[WATER, ETOH, N2, O2], templates=[],
                    vessels={"pot": spec}, max_species=20)
w = World(scenario)
w.now(CHARGE, "pot", amounts={ETOH: 3.0, WATER: 3.0})
w.now(FILL_HEADSPACE, "pot")
w.step(1.0)

pot = w.vessels["pot"]
print(f"\n   charged 50/50 ethanol/water over 60 W. It is at {pot.T:.2f} K and its")
print(f"   bubble point is {pot.bubble_point():.2f} K. Nobody knows how long that")
print("   takes, and nobody should have to.\n")

for label, condition in (
    ("until it passes 340 K", reaches(340.0)),
    ("until it boils", boils()),
    ("until the temperature steadies (0.01 K/s)", temperature_steady(0.01)),
):
    t0 = time.perf_counter()
    out = w.wait_until("pot", condition, timeout=7200.0)
    wall = time.perf_counter() - t0
    print(f"   {label:>42s}  ->  t = {w.t:8.2f} s   T = {pot.T:7.3f} K"
          f"   ({wall:.2f} s of wall)")

print(f"""
   Each instant is a ROOT of a function of the state, located to solver
   tolerance, so it does not depend on how the caller chopped up the interval --
   and the third one is the interesting case. "The temperature has stabilised" is
   dT/dt -> 0, which is approached ASYMPTOTICALLY and never crossed: as an
   equality it would wait forever. As a TOLERANCE it is a root, and it is also
   what a chemist actually means by 'the thermometer has stopped moving'.

   The flask is boiling at {pot.T:.2f} K against a predicted bubble point of
   {pot.bubble_point():.2f} K. There is no boiling-point table in this codebase.""")

# ---------------------------------------------------------------------------
print("\n" + "=" * 74)
print("PART 2  cool a solution until it CROPS -- and be told exactly when")
print("=" * 74)

BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
# 0.02 mol in ~0.5 L is 4.9 g/L: comfortably dissolved at 340 K and comfortably
# over the 1.62 g/L this holds at 275. The margin matters -- charge more and it has
# already cropped before the wait begins, and the wait then correctly reports
# "already true" rather than demonstrating anything.
cold = VesselSpec(volume=1.0, T=340.0, T_env=275.0, UA=5.0, kla=0.0)
crys = Scenario(feed_species=[WATER, BENZOIC], templates=[],
                vessels={"beaker": cold}, max_species=20)


def build():
    world = World(crys)
    world.now(CHARGE, "beaker", amounts={WATER: 27.7, BENZOIC: 0.02})
    world.now(SET_ENVIRONMENT, "beaker", T_env=275.0)
    world.step(5.0)
    return world


guessed = build()
t0 = time.perf_counter()
guessed.step(7200.0)                       # "two hours ought to do it"
guess_wall = time.perf_counter() - t0
guess_crop = guessed.vessels["beaker"].state().n_solid[BENZOIC]

discovered = build()
t0 = time.perf_counter()
out = discovered.wait_until("beaker", crystals(BENZOIC), timeout=7200.0)
found_wall = time.perf_counter() - t0

print(f"""
   {'a guessed two hours':>28s}: t = {guessed.t:8.1f} s   {guess_wall:6.2f} s of wall  (crop {guess_crop:.4f} mol)
   {'wait until crystals appear':>28s}: t = {discovered.t:8.1f} s   {found_wall:6.2f} s of wall
                                 {out.describe()}

   The second one stops the moment the answer exists, and it SAYS when -- which a
   fixed duration cannot. The instant IS the measurement.

   Note what the wall-clock column does NOT show: much of a saving. Cooling a
   solution is cheap, because the derivative is small and BDF takes enormous steps.
   Cost here is concentrated in stiff TRANSIENTS rather than in elapsed time (see
   validation/wall_clock.py, where ten seconds of an acid quench costs more than
   four hours of crystal growth), so the responsiveness half of this feature pays
   off on the quench and not here. What it buys HERE is expressiveness: the recipe
   says what the chemist meant.

   NOTE: what the threshold has to be. nS starts at EXACTLY zero and LEAVES it
   rather than crossing it, and at the solver's own 1e-9 atol the crossing is
   inside the tolerance -- so 'crystals appear' is a micromole, three decades
   clear of that and still far below anything a bench could see. It is a
   RESOLUTION limit, not a claim about nucleation, and there is no nucleation
   barrier here at all: a metastable solution would not crop at the bench and
   will here.""")

# ---------------------------------------------------------------------------
print("\n" + "=" * 74)
print("PART 3  and it is still a RECIPE -- the fork that had to be taken")
print("=" * 74)

saved = discovered.save()
waits = [e for e in saved["script"] if e["do"] == "wait_until"]
print(f"""
   The save's script holds {len(saved['script'])} entries, of which {len(waits)} is a wait:

     {waits[0]}

   THE CONDITION IS STORED AND THE INSTANT IS NOT, and that was a real fork. The
   alternative -- recording the discovered instant -- makes replay exact and makes
   the artifact a TRANSCRIPT rather than a recipe: run it against a different
   charge and it waits the wrong number of seconds, which is exactly the failure
   that made fixed durations the wrong shape to begin with.

   The deciding argument is that this project already made the same call once: a
   Scenario stores templates and feed species rather than the reaction network
   they generate, because a derived quantity stored beside its source is how the
   two drift apart. A discovered instant is derived data of that kind.""")

again = World.replay(saved)
print(f"""   Replayed from the recipe alone:
     original t = {discovered.t:.6f} s      replayed t = {again.t:.6f} s
     original T = {discovered.vessels['beaker'].T:.6f} K   replayed T = """
      f"{again.vessels['beaker'].T:.6f} K"
      f"""

   The instant was RE-DISCOVERED, not read back, which is why that is a tolerance
   and not an equality -- and it is the check that the recipe is complete: anything
   the run depended on and the script does not record would show up right there as
   a disagreement.""")

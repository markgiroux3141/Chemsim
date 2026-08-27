"""The dropping funnel: add it too fast and it runs away.

    "Toss a handful of materials in a vessel, heat it, drip an acid in -- and
     if you drip too much at once it heats up and changes the reaction, so you
     have to cool it and add slowly -- then collect the vapour, run it through
     a condenser, and take the drops in a temperature range."

That is the target vignette for the game, in the user's own words, and this is
it running. Nothing below scripts an outcome. There is no "if added too fast,
overheat": there is a funnel with a tap, a reaction with an enthalpy, and a bath
with a finite conductance, and the pot's temperature is what comes out of the
race between them.

⚠ **THE MECHANIC WAS ALREADY BUILT AND NOBODY HAD ASKED IT FOR THIS.** G1 was
scoped as new engine work -- a feed vector on ``VesselConditions``, a ``feed_T``
beside it, a ``SET_FEED`` event. Measured first (``validation/dropwise.py``), the
rig's ``meter`` edge has been a dropping funnel since Layer 5: it delivers a set
rate, it carries the donor's sensible heat, and its reservoir empties exactly.
What was genuinely missing was one layer up and is what ``add_dropwise`` is --
see panel 3.

⚠ **WHY THIS IS THE MONO-NITRATION AND NOTHING ELSE.** ``max_species=5`` stops
the network at benzene -> nitrobenzene, one reaction. That is a deliberate
simplification and it is worth saying which one: the full network runs on to di-
and tri-nitro, and the engine gives EVERY nitration the same barrier, so a
deactivated ring reacts exactly as fast as a fresh one and there is no stage for
a temperature to catch. G1 is about the addition RATE; the stages are G2.

The ``hit max_species=5`` notices interleaved with the output below are that cap
doing its job -- the network is telling you it stopped early, once per world it
builds. They are the honest kind of noise and are left in.

Runs in about a minute and a half.
"""

from __future__ import annotations

import time

from chemsim.engine import EdgeSpec, Scenario, VesselSpec, World
from chemsim.engine.events import SET_EDGE
from chemsim.engine.scenario import TemplateSpec
from chemsim.matter import Molecule
from chemsim.reactions.synthesis import aromatic_nitration
from chemsim.vessel import consumed, reaches


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


BENZENE, NITRIC, WATER, N2 = c("c1ccccc1"), c("O[N+](=O)[O-]"), c("O"), c("N#N")
NITROBENZENE = c("O=[N+]([O-])c1ccccc1")
NAMES = {BENZENE: "benzene", NITRIC: "nitric acid", WATER: "water",
         N2: "nitrogen", NITROBENZENE: "NITROBENZENE"}
BAR = "=" * 78
t_start = time.time()

FUNNEL = VesselSpec(volume=1.0, T=278.0, T_env=278.0, UA=1.0e6, kla=0.0,
                    k_vent=0.0, k_diss=0.0, lle=False, heat_capacity=200.0)


def bench(UA: float = 8.0, still: bool = False) -> Scenario:
    """A cold funnel over a cooled pot, optionally under a still head.

    ``UA`` is the pot's coupling to its bath in W/K -- how hard it is being
    cooled. It is the other side of the race the drip rate is one side of.
    """
    vessels = {
        "funnel": FUNNEL,
        "pot": VesselSpec(volume=2.0, T=278.0, T_env=278.0, UA=UA, kla=5.0,
                          k_vent=0.0, k_diss=0.0, lle=False,
                          heat_capacity=50.0),
    }
    edges = [EdgeSpec("meter", "funnel", "pot", 0.0)]
    if still:
        vessels["head"] = VesselSpec(volume=0.10, T=278.0, T_env=290.0, UA=0.3,
                                     kla=5.0, k_vent=0.0, k_diss=0.0,
                                     lle=False, heat_capacity=5.0)
        vessels["receiver"] = VesselSpec(volume=0.5, T=283.0, T_env=283.0,
                                         UA=40.0, kla=5.0, k_vent=10.0,
                                         k_diss=0.0, lle=False,
                                         heat_capacity=20.0)
        edges += [EdgeSpec("vapour", "pot", "head", 20.0),
                  EdgeSpec("drain", "head", "receiver", 0.5)]
    return Scenario(
        feed_species=[BENZENE, NITRIC, WATER, N2],
        templates=[TemplateSpec.of(aromatic_nitration())],
        max_species=5, vessels=vessels, edges=edges,
    )


def charged(UA: float = 8.0, benzene: float = 1.0, acid: float = 1.0,
            still: bool = False, air: bool = False) -> World:
    w = World(bench(UA, still))
    w.vessels["funnel"].charge({NITRIC: acid, WATER: 2.0 * acid})
    w.vessels["pot"].charge({BENZENE: benzene})
    if air:
        for v in w.vessels.values():
            v.fill_headspace({N2: 1.0})
    return w


def drip_and_watch(w: World, rate: float, total_time: float,
                   samples: int = 40) -> tuple[float, float]:
    """Open the tap at ``rate``, hold it open, and follow the thermometer.

    Returns (peak T, T at the end). The sampling is only for the peak -- the
    trajectory is one continuous solve either way.
    """
    w.now(SET_EDGE, edge=0, k=rate)
    peak = w.vessels["pot"].T
    for _ in range(samples):
        w.step(total_time / samples)
        peak = max(peak, w.vessels["pot"].T)
    return peak, w.vessels["pot"].T


# ---------------------------------------------------------------------------
print(BAR)
print("THE APPARATUS")
print(BAR)
probe = charged()
print(f"   {len(probe.network.species)} species, "
      f"{len(probe.network.reactions)} reaction: "
      + " + ".join(NAMES[s] for s in probe.network.reactions[0].reactants)
      + " -> "
      + " + ".join(NAMES[s] for s in probe.network.reactions[0].products))
print("""
   funnel  1.0 mol nitric acid in 2.0 mol water, held at 278 K
     |
     |  a METER edge -- a tap, in mol/s of SOLUTION
     v
   pot     1.0 mol benzene, in a bath, cooled at UA W/K

   The funnel is a VESSEL, not a parameter. Its temperature is solved, not
   declared, so an ice bath on the funnel is a thermal edge rather than a
   number -- and it runs out by itself when it is empty.
""")
w = charged()
print(f"   {'t (s)':>7s} {'funnel HNO3':>13s} {'pot HNO3+PhNO2':>16s}")
w.now(SET_EDGE, edge=0, k=0.05)
last = 0.0
for t in (5.0, 10.0, 19.0, 20.0, 40.0):
    w.step(t - last)
    last = t
    f = w.vessels["funnel"].state().total(NITRIC)
    p = w.vessels["pot"].state()
    print(f"   {t:7.1f} {f:13.6f} "
          f"{p.total(NITRIC) + p.total(NITROBENZENE):16.6f}")
print("""
   1.0 mol of acid in 3.0 mol of solution, at 0.05 mol/s: the acid leaves at a
   third of that and the funnel is dry at 60 s. It is empty, and it STAYS
   empty -- nothing keeps pumping from a dry funnel.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 1  TOO FAST -- the same charge, four taps, one weak ice bath")
print(BAR)
print("""   Identical in every respect except the tap setting: 1.0 mol of nitric
   acid into 1.0 mol of benzene, over a bath at 278 K coupled at 5 W/K. The
   nitration is -141 kJ/mol, so heat arrives at rate*dH and leaves at
   UA*(T - 278). Two rates, racing.
""")
print(f"   {'tap mol/s':>10s} {'adds in':>9s} {'PEAK T':>9s} {'end T':>9s} "
      f"{'benzene left':>13s} {'nitrobenzene':>13s}")
for rate in (0.05, 0.01, 0.002, 0.0005):
    w = charged(UA=5.0)
    dur = 1.0 / rate
    peak, end = drip_and_watch(w, rate, dur)
    w.step(dur)
    st = w.vessels["pot"].state()
    print(f"   {rate:10.4f} {dur:8.0f}s {peak:9.2f} {end:9.2f} "
          f"{st.total(BENZENE):13.5f} {st.total(NITROBENZENE):13.5f}")
print("""
   A hundred kelvin of spread on nothing but the tap. The fast pour takes the
   pot 29 K past benzene's normal boiling point -- in a flask with k_vent=0, so
   what that buys is pressure rather than a lost charge -- and the slowest one
   never gets 5 K off the bath. Nobody wrote a runaway: it is q_rxn against
   UA*(T - T_env), and the tap is what sets q_rxn.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 2  ...SO COOL IT AND ADD SLOWLY -- the same four taps, better bath")
print(BAR)
print("""   The other half of the sentence. 50 W/K instead of 5 -- a bigger bath,
   or a stirred one -- and the same four additions.
""")
print(f"   {'tap mol/s':>10s} {'adds in':>9s} {'PEAK T':>9s} {'end T':>9s} "
      f"{'benzene left':>13s} {'nitrobenzene':>13s}")
for rate in (0.05, 0.01, 0.002, 0.0005):
    w = charged(UA=50.0)
    dur = 1.0 / rate
    peak, end = drip_and_watch(w, rate, dur)
    w.step(dur)
    st = w.vessels["pot"].state()
    print(f"   {rate:10.4f} {dur:8.0f}s {peak:9.2f} {end:9.2f} "
          f"{st.total(BENZENE):13.5f} {st.total(NITROBENZENE):13.5f}")
print("""
   The fastest pour still runs hot, but the whole curve has come down and the
   three slower ones are flat. That is the bench skill the vignette is about:
   there is no safe rate and no unsafe one, there is a rate the cooling can
   keep up with.

   AND THE NITROBENZENE COLUMN DOES NOT MOVE, WHICH IS THE RIGHT ANSWER FOR
   THIS CHARGE. One mole of acid onto one mole of benzene has exactly one
   substitution to make, and since G2 the ring knows it: a nitro group raises the
   next barrier by 25 kJ/mol, so the reaction STOPS. Before G2 it did not -- the
   same sweep left 0.13 to 0.19 mol of nitrobenzene and made 0.055 mol of
   dinitrobenzene at every single setting, because one barrier covered every
   nitration on every substrate.

   Where the drip rate DOES pick the product is where there is acid to spend on
   a second and third substitution. validation/ring_deactivation.py panel 3 is
   that: toluene with 3.5 mol of nitric acid is mononitrated at 300 K in ten
   seconds, dinitrated at 340 K, and only reaches TNT at 380 K -- the escalating
   sequence real manufacture uses, out of three barriers 25 kJ/mol apart.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 3  DRIP UNTIL IT WARMS, THEN STOP -- and why that is a new verb")
print(BAR)
print("""   "Add it until the pot reaches 320 K" is what a chemist says, and it is
   not the same instruction as "add it for 43 seconds". The first survives being
   run at a different scale; the second is this run's answer written down.

   An Event carries an absolute t, so scheduling the tap-close after a
   wait_until bakes the discovered instant into the recipe. add_dropwise stores
   the CONDITION -- the same fork collect_fraction was built for.
""")
w = charged(UA=5.0)
out = w.add_dropwise(edge=0, rate=0.02, watch="pot",
                     until=reaches(320.0), timeout=300.0)
print("   drip at 0.02 mol/s until the pot reaches 320 K:")
print(f"     it got there at t = {out['elapsed']:.3f} s with "
      f"{out['delivered']:.4f} mol in, and the funnel has "
      f"{out['donor_left']:.4f} mol left")
w.step(120.0)
print(f"     two minutes later the pot is back to {w.vessels['pot'].T:.2f} K "
      f"with {w.vessels['pot'].state().total(NITROBENZENE):.4f} mol of product")
script = w.save()["script"]
print(f"\n   the recipe: {[e['do'] for e in script]}")
print(f"     and the drip entry is {script[0]}")
print("     -- a condition and a timeout. No instant anywhere in it.")

print("\n   REPLAYED AT TWICE THE SCALE (2 mol benzene, 2 mol acid):")
big = charged(UA=5.0, benzene=2.0, acid=2.0)
big.run_script(script)
print(f"     it found its own crossing at a different time and ran: "
      f"pot {big.vessels['pot'].T:.2f} K, "
      f"{big.vessels['pot'].state().total(NITROBENZENE):.4f} mol product")

print("\n   THE SAME PROTOCOL WRITTEN AS AN EVENT, FOR CONTRAST:")
stamped = charged(UA=5.0)
stamped.now(SET_EDGE, edge=0, k=0.02)
stamped.step(1.0)
stamped.wait_until("pot", reaches(320.0), timeout=300.0)
stamped.now(SET_EDGE, edge=0, k=0.0)
stamped.step(120.0)
try:
    charged(UA=5.0, benzene=2.0, acid=2.0).run_script(stamped.save()["script"])
    print("     replayed at 2x without complaint")
except ValueError as exc:
    print(f"     replayed at 2x: REFUSED -- {exc}")
print("""
     A loud refusal is the GOOD case. Had the bigger charge crossed 320 K a
     little EARLIER instead, the recorded event would still be in the future
     and the tap would have shut at an instant this run never found -- with no
     complaint at all.""")

print('\n   AND "ADD ALL OF IT" IS ALSO A CONDITION, ON THE FUNNEL:')
w = charged(UA=50.0, acid=0.3)
out = w.add_dropwise(0, 0.01, "funnel", consumed(NITRIC, 1.0e-4), timeout=300.0)
print(f"     0.3 mol of acid in 0.9 mol of solution at 0.01 mol/s took "
      f"{out['elapsed']:.1f} s")
print("     -- NOT the 30 s that total/rate predicts, because a tap moves the "
      "funnel's SOLUTION")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 4  ...AND TAKE THE DROPS IN A TEMPERATURE RANGE -- AND WHAT IT COSTS")
print(BAR)
print("""   The last clause of the vignette is the one clause this example does
   NOT run, and that is a measurement rather than an omission.

   It is not a missing capability. A cut has been sayable since M2 --
   `collect_fraction` waits for the head to enter a band, re-points the drain at
   a receiver, waits for it to leave, and parks -- and `examples/
   fractional_distillation.py` and `examples/plate_column.py` are both that,
   running, with the second reaching a 0.8548 heart cut on eight plates.

   What was tried here was bolting a head and a receiver onto THIS bench, so
   that one apparatus carried the whole sentence. Measured, twice:

     * the same 20-second addition cost 3.9 s of wall clock on the two-vessel
       bench and 220 s with the still attached -- 56x, because a rig integrates
       every vessel as ONE stiff system and a vapour edge couples the pressures
       across all of it;
     * and the cut it then produced was poor: from a pot held at 385 K, the head
       entered the 345-368 K band at 89 s and had still not left it 2911 s
       later, having passed 0.016 mol of benzene. The head is 5 J/K under a
       0.3 W/K jacket, so what warms it is arriving vapour, and a pot that is
       80% water and nitrobenzene does not send much.

   Both of those are real and neither is a bug -- the first is the price of
   coupled glassware and the second is a still that wants designing rather than
   assembling. They are recorded here because "the example does not show it"
   and "the engine cannot do it" are different sentences, and only one of them
   is true.""")

print()
print(f"[{time.time() - t_start:.0f} s]")

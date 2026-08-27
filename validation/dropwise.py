"""G1 -- the dropping funnel: what already existed, and what did not.

A standing audit, ~2 minutes. It exists because G1's brief named the wrong gap,
and the only way anyone will know that a session later is if the measurements
that overturned it are re-runnable.

**The brief said:** "drip an acid in slowly" is MISSING; build
``VesselConditions.feed``, a ``feed_T`` beside it, a ``SET_FEED`` event, and
derive the funnel's duration as ``total / rate``.

**Measured:** the rig's ``meter`` edge has been a dropping funnel since Layer 5.
It delivers a set rate, it carries the donor's sensible heat, its reservoir runs
out exactly, and ``SET_EDGE`` opens and shuts it inside a saveable scenario.
Panels 1-3 are those three claims, measured. Panel 4 is the one that matters for
the game -- whether an ADDITION RATE can actually control an outcome -- and
panel 5 is the gap that turned out to be real.

Run: ``python validation/dropwise.py``
"""

from __future__ import annotations

import time

from chemsim.engine import EdgeSpec, Scenario, VesselSpec, World
from chemsim.engine.events import SET_EDGE
from chemsim.engine.scenario import TemplateSpec
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import alcohol_chemistry
from chemsim.reactions.synthesis import aromatic_nitration
from chemsim.vessel import Rig, Vessel, reaches


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


ACOH, ETOH, WATER, O2, N2 = c("CC(=O)O"), c("CCO"), c("O"), c("O=O"), c("N#N")
BENZENE, NITRIC = c("c1ccccc1"), c("O[N+](=O)[O-]")
NITROBENZENE = c("O=[N+]([O-])c1ccccc1")
DINITRO = c("O=[N+]([O-])c1ccc([N+](=O)[O-])cc1")

thermo = ThermochemistryProvider()
esters = build_network([ACOH, ETOH, WATER, O2, N2], alcohol_chemistry(),
                       thermo=thermo, max_species=200, max_molar_mass=250.0)
nitro = build_network([BENZENE, NITRIC, WATER], [aromatic_nitration()],
                      thermo=thermo, max_species=60, max_molar_mass=300.0)

t0 = time.time()
BAR = "=" * 78


def funnel(net, T: float, volume: float = 2.0) -> Vessel:
    """A reservoir with no chemistry to do: cold, sealed, well-thermostatted."""
    return Vessel(net, volume=volume, T=T, T_env=T, UA=1.0e6, kla=0.0,
                  k_vent=0.0, k_diss=0.0, lle=False, heat_capacity=200.0)


# ---------------------------------------------------------------------------
print(BAR)
print("PANEL 1  DOES A METER EDGE DELIVER ITS RATE, AND DOES THE FUNNEL RUN OUT?")
print(BAR)
print("""   The brief's item 4 -- "THE RESERVOIR IS NOT STATE ... it is a DURATION,
   total/rate, derived". It is state, it is a VESSEL, and it empties by itself.
   What matters is whether it empties CLEANLY: a meter's flux is intensive in
   the donor (k mol/s of solution, whatever is left), so nothing in the flux law
   slows it down as the funnel drains. If the clamp at zero were leaky the pot
   would receive matter the funnel never had.
""")
print("   0.5 mol of acetic acid, drained at four rates, read at t = 1000 s")
print(f"   {'rate mol/s':>11s} {'funnel left':>18s} {'pot got':>18s} "
      f"{'the pair':>18s}")
for rate in (0.001, 0.1, 1.0, 10.0):
    rig = Rig()
    fn = rig.add("funnel", funnel(esters, 298.15, volume=1.0))
    pot = rig.add("pot", Vessel(esters, volume=1.0, T=298.15, T_env=298.15,
                                UA=0.0, kla=0.0, k_vent=0.0, k_diss=0.0,
                                lle=False))
    rig.meter("funnel", "pot", rate=rate)
    fn.charge({ACOH: 0.5})
    rig.run(1000.0)
    f, p = fn.state().total(ACOH), pot.state().total(ACOH)
    print(f"   {rate:11.3f} {f:18.12f} {p:18.12f} {f + p:18.12f}")
print("""
   Exact at every rate, including one that empties the funnel in 50 ms. A feed
   term whose reservoir was a DERIVED DURATION would have had to reproduce this
   and could not have done it better than exactly.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 2  DOES THE DRIP CARRY SENSIBLE HEAT?  (the brief's 'whole point')")
print(BAR)
print("""   "Without it, dripping ice-cold acid warms the flask exactly as fast as
   dripping boiling acid and the mechanic is COSMETIC." Correct, and already
   built: rig_integrator carries `flux @ Cp_donor * (T_src - T_dst)` on every
   liquid edge. Same 1.0 mol into the same insulated pot from three funnels.
""")
print(f"   {'funnel T':>10s} {'pot T after 100 s':>20s} {'moved':>10s}")
for T_funnel in (270.0, 298.15, 370.0):
    rig = Rig()
    fn = rig.add("funnel", funnel(esters, T_funnel, volume=1.0))
    pot = rig.add("pot", Vessel(esters, volume=1.0, T=330.0, T_env=330.0,
                                UA=0.0, kla=0.0, k_vent=0.0, k_diss=0.0,
                                lle=False, heat_capacity=5.0))
    rig.meter("funnel", "pot", rate=0.01)
    fn.charge({ACOH: 5.0})
    pot.charge({ETOH: 0.5})
    rig.run(100.0)
    print(f"   {T_funnel:10.2f} {pot.T:20.4f} {pot.state().total(ACOH):10.4f}")
print("""
   66 K of spread on 0.549-0.553 mol either way. (The moles are not identical
   to four figures and cannot be: a meter moves the donor's SOLUTION at a molar
   rate, and the same acid at 270 K and at 370 K is not the same solution.)
   `feed_T` would have been this number as a
   DECLARED CONSTANT; here it is a vessel's own solved temperature, which is
   also a thing you can put in an ice bath with a thermal edge.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 3  WHAT AN ADDITION RATE CANNOT DO ON ITS OWN")
print(BAR)
print("""   The vignette is "drip too much at once and it heats up". Sensible heat
   alone cannot produce that, and this is the panel that says why: the same
   moles carry the same joules however fast they arrive, so an INSULATED pot
   lands in the same place. A rate only matters against another rate.
""")
print(f"   {'rate mol/s':>11s} {'time s':>8s} {'pot T':>9s} {'ester':>9s} "
      f"{'ether':>9s}")
for rate, dur in ((0.05, 100.0), (0.01, 500.0), (0.002, 2500.0)):
    rig = Rig()
    fn = rig.add("funnel", funnel(esters, 280.0))
    pot = rig.add("pot", Vessel(esters, volume=2.0, T=380.0, T_env=380.0,
                                UA=0.0, kla=0.0, k_vent=0.0, k_diss=0.0,
                                lle=False, heat_capacity=5.0))
    rig.meter("funnel", "pot", rate=rate)
    fn.charge({ACOH: 5.0})
    pot.charge({ETOH: 5.0})
    rig.run(dur)
    st = pot.state()
    print(f"   {rate:11.3f} {dur:8.0f} {pot.T:9.3f} "
          f"{st.total(c('CCOC(C)=O')):9.4f} {st.total(c('CCOCC')):9.5f}")
print("""
   0.15 K of spread across a 25x rate change, and the ester is the same to
   three figures. Nothing is broken here -- this is the energy balance being
   right. Panel 4 is what the vignette actually needs.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 4  THE RUNAWAY: an EXOTHERM racing a COOLING RATE")
print(BAR)
print("""   1.0 mol of nitric acid dripped into 1.0 mol of benzene over an ice
   bath at 280 K. Nitration is -141.2 kJ/mol on the first substitution, against
   an esterification's -3.2, and that is why the playground is here rather than
   in the ester family. Heat in is rate * dH; heat out is UA * (T - 280). The
   drip rate is one side of a race and the bath is the other.
""")
print(f"   {'UA W/K':>7s} {'rate mol/s':>11s} {'adds in s':>10s} "
      f"{'PEAK T':>9s} {'end T':>9s} {'PhNO2':>9s} {'p-di':>9s}")
for UA in (5.0, 50.0):
    for rate in (0.05, 0.01, 0.002, 0.0005):
        rig = Rig()
        fn = rig.add("funnel", funnel(nitro, 280.0))
        pot = rig.add("pot", Vessel(nitro, volume=2.0, T=280.0, T_env=280.0,
                                    UA=UA, kla=1.0, k_vent=0.0, k_diss=0.0,
                                    lle=False, heat_capacity=50.0))
        rig.meter("funnel", "pot", rate=rate)
        fn.charge({NITRIC: 1.0, WATER: 2.0})
        pot.charge({BENZENE: 1.0})
        peak, dur = pot.T, 1.0 / rate
        for _ in range(40):
            rig.run(dur / 40.0)
            peak = max(peak, pot.T)
        rig.run(dur)
        st = pot.state()
        print(f"   {UA:7.1f} {rate:11.4f} {dur:10.0f} {peak:9.2f} {pot.T:9.2f} "
              f"{st.total(NITROBENZENE):9.5f} {st.total(DINITRO):9.5f}")
print("""
   THE MECHANIC IS REAL AND IT IS EMERGENT. Over a weak bath the peak runs from
   285 K to 390 K on nothing but the tap setting; over a strong one the same
   sweep is 280.5 K to 328 K. Nobody wrote a runaway: it is q_rxn against
   UA*(T - T_env), and the drip rate is what sets q_rxn.

   AND THE PRODUCT COLUMNS ARE FLAT, WHICH THEY WERE ALSO FLAT BEFORE G2 AND
   FOR THE OPPOSITE REASON. Measured on this same sweep before ring deactivation
   existed: nitrobenzene 0.133 at the fastest tap and 0.190 at the slowest, with
   0.0555 mol of dinitrobenzene at EVERY setting -- one barrier for every
   nitration, so the acid ran on past the mononitro product and temperature had
   no stage to select between. With rho = -6.5 the same sweep gives 0.663-0.666
   mol of nitrobenzene and 1e-5 to 4e-4 of the dinitro: the reaction now STOPS,
   which is why the column is flat.

   So the drip rate here controls the TEMPERATURE and not the product, and
   after G2 that is the correct answer for this charge rather than a gap: 1.0 mol
   of acid onto 1.0 mol of benzene cannot go past one substitution once the
   second barrier is 25 kJ/mol higher. The staging G2 buys is visible where there
   is acid to spend -- validation/ring_deactivation.py panel 3, toluene with 3.5
   mol of it.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 5  THE GAP THAT WAS REAL: a conditional drip could not be a RECIPE")
print(BAR)
print("""   The brief: "it composes with wait_until for free -- 'drip until the pot
   reaches 340 K, then stop' needs no new machinery." Measured below, twice: once
   written the free way, once as add_dropwise. An Event carries an absolute t, so
   the free way records THIS run's crossing and the recipe stops meaning what the
   chemist meant. Same fork collect_fraction was built for, same answer.
""")


def scenario() -> Scenario:
    return Scenario(
        feed_species=[BENZENE, NITRIC, WATER],
        templates=[TemplateSpec.of(aromatic_nitration())], max_species=60,
        vessels={
            "funnel": VesselSpec(volume=2.0, T=280.0, T_env=280.0, UA=1.0e6,
                                 kla=0.0, k_vent=0.0, k_diss=0.0, lle=False,
                                 heat_capacity=200.0),
            "pot": VesselSpec(volume=2.0, T=280.0, T_env=280.0, UA=5.0,
                              kla=1.0, k_vent=0.0, k_diss=0.0, lle=False,
                              heat_capacity=50.0),
        },
        edges=[EdgeSpec(kind="meter", a="funnel", b="pot", k=0.0)],
    )


def charged(scale: float = 1.0) -> World:
    w = World(scenario())
    w.vessels["funnel"].charge({NITRIC: 1.0 * scale, WATER: 2.0 * scale})
    w.vessels["pot"].charge({BENZENE: 1.0 * scale})
    return w


stamped = charged()
stamped.now(SET_EDGE, edge=0, k=0.02)
stamped.step(1.0)
stamped.wait_until("pot", reaches(340.0), timeout=200.0)
print(f"   the free way:  340 K discovered at t = {stamped.t:.6f} s")
stamped.now(SET_EDGE, edge=0, k=0.0)
stamped.step(10.0)
free_script = stamped.save()["script"]
closing = [e for e in free_script if e["do"] == "schedule"][-1]["event"]["t"]
print(f"                  and the recipe records set_edge at t = {closing:.6f}")
for scale in (1.0, 2.0):
    try:
        charged(scale).run_script(free_script)
        print(f"     replay at {scale:g}x: ran")
    except ValueError as exc:
        print(f"     replay at {scale:g}x: REFUSED -- {str(exc)[:66]}")

verb = charged()
out = verb.add_dropwise(0, 0.02, "pot", reaches(340.0), timeout=200.0)
verb.step(10.0)
print(f"\n   as a verb:     340 K discovered at t = {out['elapsed']:.6f} s, "
      f"{out['delivered']:.5f} mol in, funnel has {out['donor_left']:.4f} left")
verb_script = verb.save()["script"]
print(f"                  the recipe records "
      f"{[e['do'] for e in verb_script]} and NO timestamp")
for scale in (1.0, 2.0):
    again = charged(scale)
    again.run_script(verb_script)
    print(f"     replay at {scale:g}x: ran, tap shut at t = "
          f"{again.t - 10.0:.6f} s, pot {again.vessels['pot'].T:.3f} K")
print("""
   THE 2x REPLAY IS THE WHOLE FINDING. A bigger charge takes longer to reach
   340 K, so the recorded timestamp lands in the past and schedule() refuses it.
   That refusal is the GOOD case -- a crossing that landed a hair EARLIER would
   still be in the future, and the tap would shut at an instant this run never
   found, silently. Storing the condition is what makes a drip a recipe.""")

print()
print(f"   [{time.time() - t0:.1f} s]")

"""M2 -- a still as a PROTOCOL: three receivers, cut by head temperature.

The physics in here is not new. A pot, a vapour edge and a cold receiver have
been a working still since Layer 5, the enrichment is real, and reflux holds a
plateau indefinitely. What was missing was a way to SAY a cut.

    "collect the fraction boiling between 351 and 355 K"

was not merely unimplemented -- it was unsayable. ``World``, the layer that can
be saved, scripted and replayed, had no rig at all: its verbs were CHARGE,
SET_HEAT, SET_ENVIRONMENT, SET_VENT, SET_STIRRING, SET_SHAKING, FILL_HEADSPACE,
TRANSFER and FILTER. No vapour edge, no condenser, no receiver, and no way to
stop and change the one you had. So everything came over into a single pot and
the enrichment the column genuinely achieved WASHED BACK OUT -- measured on a
50/50 ethanol/water charge, head mole fraction 0.655 at 200 s and 0.500 by
1200 s. Nothing was wrong with the chemistry; the protocol could not express the
one operation that makes fractional distillation fractional.

Three things closed it, and none of them is science:

  * ``Scenario.edges`` -- the APPARATUS is saved data now, not Python assembled
    in an example. SAVE_VERSION 5.
  * ``SWAP_RECEIVER`` -- re-point one end of an edge at another declared vessel.
  * ``collect_fraction`` -- wait for the band, swap in, wait, swap out.

!! AND THE TRAP, WHICH IS THE INTERESTING PART. A cut is a DISCOVERED INSTANT,
so the recipe stores the CONDITION and never the timestamp. That is why
collect_fraction is a scripted verb rather than sugar over a scheduled
SWAP_RECEIVER: an event carries an absolute t, so building the swap from one
would bake THIS run's crossing into the recipe. A replayed distillation has to
locate its own cut points. Same rule wait_until already followed.

!! AND A THIRD THING, FOUND LATER AND WORSE THAN EITHER: THIS APPARATUS HAD NO
OPEN END. Vessels vent at ``k_vent`` and the receivers are reached only by a
DRAIN, so the pot, head and condenser were one sealed volume. Measured, same
charge and the same 250 W: 3.09 bar by t=100 s, the pot boiling at 370 K rather
than 353, and once dry an empty flask superheating to 548 K. Every head
temperature this example reported was a boiling point at three atmospheres, and
the three cut bands had been fitted to that trace. The condenser now vents, which
is where a real distillation is open to the room, and the bands moved with it.
!! It also explains a failure this file's own closing note got wrong: the first
plate-column attempt was diagnosed as a startup problem, and it was not. A sealed
column pressurises HARDER the taller it is, so its plates ran hotter than the
correlations cover and its head never came near a band chosen at one atmosphere.
See ``examples/plate_column.py``, where the same column at 1 atm works.

!! A second trap, and it needed engine work. World used to satisfy a wait by
integrating the OWNER vessel alone and stepping the others forward by however
long that took. That is right for separate flasks on a bench and wrong for
glassware: a head's temperature is set almost entirely by what arrives from the
pot, so a head integrated on its own reaches 353 K at an instant the real run
never passes through -- and a cut is called off exactly that number. Hence
``RigIntegrator.step_until`` and ``Rig.wait_until``: the condition is on ONE
vessel, the trajectory is the WHOLE rig's.

Run: python examples/fractional_distillation.py
"""

from __future__ import annotations

from chemsim.engine import EdgeSpec, Scenario, VesselSpec, World
from chemsim.matter import Molecule
from chemsim.vessel import Condition


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


ACETONE = c("CC(C)=O")      # bp 329.2 K
ETHANOL = c("CCO")          # bp 351.4 K
WATER = c("O")              # bp 373.1 K
AIR = ["N#N", "O=O"]

RECEIVERS = ("forerun", "heart", "tail")


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def still() -> World:
    """Pot -> HEAD -> condenser -> receivers, declared as a SCENARIO.

    ⚠ THE HEAD IS NOT THE CONDENSER, and conflating them was the first thing
    this example got wrong. A still head is the UNCOOLED junction where the
    thermometer sits: its temperature is set by the latent heat of the vapour
    passing through, which is why "the head is at 351 K" tells you what is
    coming over. Put the thermometer in the condenser instead -- cold, UA=40
    against a 288 K bath -- and it reads the COOLANT, sitting near 290 K for the
    whole run whatever is distilling. Every cut band then misses, and the first
    receiver quietly collects the lot.
    """
    pot = VesselSpec(volume=1.0, T=298.15, T_env=298.15, UA=1.0,
                     Q_input=250.0, kla=5.0, k_vent=0.0, lle=False)
    # Small, thin-walled, barely coupled to the room: the vapour dominates it.
    head = VesselSpec(volume=0.10, T=298.15, T_env=298.15, UA=0.3, kla=5.0,
                      k_vent=0.0, heat_capacity=5.0, lle=False)
    # ⚠⚠ ``k_vent`` ON THE CONDENSER IS THE STILL'S OPEN END, AND WITHOUT IT THIS
    # APPARATUS WAS NOT A STILL. Every vessel above vents at 0 and the receivers
    # are reached only by a DRAIN, so gas had nowhere to go: the pot, head and
    # condenser were one sealed volume. MEASURED with k_vent=0 here, same charge
    # and same 250 W: the rig pressurises to **3.09 bar by t=100 s**, the pot
    # boils at **370 K instead of 353**, and once it runs dry the empty flask
    # superheats to **548 K**. Every head temperature this example reports was
    # therefore a boiling point at three atmospheres, and the cut bands had been
    # fitted to that trace rather than to a distillation. A real distillation is
    # OPEN to the room at the condenser outlet, and this is where.
    cond = VesselSpec(volume=0.5, T=288.0, T_env=288.0, UA=40.0, kla=5.0,
                      k_vent=1.0, heat_capacity=20.0, lle=False)
    # ⚠ kla > 0 AND a vent, both deliberately. A receiver with kla=0 leaves its
    # gas block identically flat -- the fragility ``check_state`` names -- and in
    # a RIG that is worse than in a lone flask: the two receivers not currently
    # connected are isolated blocks inside one coupled Jacobian, and BDF's LU
    # factorisation of it was singular outright. The vent is where the far end of
    # a real still is open, and it stops a sealed rig pressurising.
    jar = VesselSpec(volume=0.5, T=288.0, T_env=288.0, UA=5.0, kla=5.0,
                     k_vent=10.0, lle=False)
    return World(Scenario(
        feed_species=[ACETONE, ETHANOL, WATER, *AIR],
        templates=[],
        max_species=30,
        vessels={"pot": pot, "head": head, "condenser": cond,
                 **{r: jar for r in RECEIVERS}},
        # ⚠ EDGE 2 IS THE ONE THAT MOVES. 0 and 1 carry vapour up the column;
        # 2 is the drain out of the condenser, and swapping its far end is what
        # taking a cut IS.
        edges=[
            EdgeSpec("vapour", "pot", "head", k=20.0),
            EdgeSpec("vapour", "head", "condenser", k=20.0),
            EdgeSpec("drain", "condenser", "forerun", k=0.5),
        ],
    ))


DRAIN = 2


def charge(w: World) -> None:
    w.now("charge", "pot", amounts={ACETONE: 0.4, ETHANOL: 0.4, WATER: 0.4})
    for v in ("pot", "head", "condenser", *RECEIVERS):
        w.now("fill_headspace", v)
    w.flush()


def composition(w: World, vid: str) -> tuple[float, dict]:
    st = w.vessels[vid].state()
    held = {s: st.n_liquid.get(s, 0.0) + st.n_liquid2.get(s, 0.0)
            for s in (ACETONE, ETHANOL, WATER)}
    total = sum(held.values())
    return total, held


def report(w: World) -> None:
    print(f"   {'receiver':>10s} {'mol held':>10s} {'acetone':>9s} "
          f"{'ethanol':>9s} {'water':>9s}   purest")
    for r in RECEIVERS:
        total, held = composition(w, r)
        if total <= 0.0:
            print(f"   {r:>10s} {0.0:10.4f} {'--':>9s} {'--':>9s} {'--':>9s}")
            continue
        x = {k: v / total for k, v in held.items()}
        best = max(x, key=x.get)
        name = {ACETONE: "acetone", ETHANOL: "ethanol", WATER: "water"}[best]
        print(f"   {r:>10s} {total:10.4f} {x[ACETONE]:9.3f} {x[ETHANOL]:9.3f} "
              f"{x[WATER]:9.3f}   {name} {x[best]:.3f}")


def distil(w: World) -> list[dict]:
    """Three cuts, each named by the head temperature that opens and closes it."""
    charge(w)
    cuts = []
    # ⚠ THE BANDS ARE READ OFF THE HEAD'S OWN TRACE, not off the pure boiling
    # points. A 3-component charge does not boil at 329/351/373 K -- it boils at
    # its BUBBLE POINT, which climbs continuously as the pot depletes, and the
    # head follows that. Choosing bands from a table of pure bp's is how you get
    # three cuts that all miss.
    # ⚠ AND THESE BANDS MOVED WHEN THE CONDENSER WAS OPENED. They used to be
    # 300-366 / 366-374 / 374-500 K, which are not the boiling points of anything
    # in this flask -- they were fitted to a SEALED rig running at 3.1 bar. At one
    # atmosphere the head climbs 336 -> 341 -> 346 -> 352 -> 366 K and then falls
    # as the pot runs down, so the bands come down with it.
    bands = [
        ("forerun", 300.0, 342.0, 200.0),   # acetone-rich, comes over first
        ("heart", 342.0, 356.0, 200.0),     # the middle
        # ⚠ THE TAIL HAS NO UPPER BAND IT CAN REACH, and that is the honest
        # shape of a tail cut: once the pot runs down the head FALLS rather than
        # climbing past 500 K, so this one is closed by its timeout. ``left:
        # False`` is the truthful report -- "still collecting when we stopped" --
        # and a cut that never closes is a result, not an error.
        #
        # ⚠ THE TIMEOUT IS ALSO WHAT KEEPS THIS RUN INSIDE THE LIQUID. 250 W boils
        # this 1.2 mol charge dry at about 280 s, and an EMPTY flask under a mantle
        # runs away -- 548 K, which is the "dry superheated flask" fragility
        # ``VesselIntegrator.diagnose`` already names. A tail cut that ran for
        # 900 s would spend most of it there.
        ("tail", 356.0, 500.0, 30.0),
    ]
    for into, enter, leave, timeout in bands:
        out = w.collect_fraction("head", DRAIN, into, enter, leave, timeout)
        cuts.append(dict(out, band=(enter, leave)))
    return cuts


# ---------------------------------------------------------------------------
rule("PANEL 1 -- ONE RECEIVER: the enrichment WASHES BACK OUT")
# ---------------------------------------------------------------------------
w1 = still()
charge(w1)
print()
print("   Everything drains into one jar, which is all a still could do before.")
print()
print(f"   {'t / s':>7s} {'pot T':>8s} {'head T':>8s} {'jar mol':>9s} "
      f"{'x(acetone)':>11s} {'x(ethanol)':>11s}")
for _ in range(6):
    w1.step(45.0)
    total, held = composition(w1, "forerun")
    xa = held[ACETONE] / total if total else 0.0
    xe = held[ETHANOL] / total if total else 0.0
    print(f"   {w1.t:7.0f} {w1.vessels['pot'].T:8.2f} "
          f"{w1.vessels['head'].T:8.2f} {total:9.4f} {xa:11.3f} {xe:11.3f}")
print("""
   The acetone that came over FIRST is still in the jar when the water arrives,
   so the mole fraction falls back toward the charge. That is not a modelling
   failure -- it is what one receiver means.""")

# ---------------------------------------------------------------------------
rule("PANEL 2 -- THREE RECEIVERS, CUT BY HEAD TEMPERATURE")
# ---------------------------------------------------------------------------
w2 = still()
cuts = distil(w2)
print()
print("   collect_fraction('head', edge 1, into, enter, leave) x 3:")
print()
print(f"   {'cut':>10s} {'band / K':>14s} {'entered':>8s} {'left':>6s} "
      f"{'wait / s':>9s} {'collect / s':>12s}")
for cut in cuts:
    lo, hi = cut["band"]
    print(f"   {cut['into']:>10s} {f'{lo:.0f} - {hi:.0f}':>14s} "
          f"{str(cut['entered']):>8s} {str(cut['left']):>6s} "
          f"{cut['wait']:9.1f} {cut['collected']:12.1f}")
print()
report(w2)

heart_total, heart_held = composition(w2, "heart")
heart_x = (max(heart_held.values()) / heart_total) if heart_total else 0.0
print(f"""
   !! THE CUTS ARE REPORTED AS COMPOSITION, NOT ASSERTED, and the honest
   headline is that THE PROTOCOL WORKS AND THE SEPARATION IS MEDIOCRE. Three
   receivers each hold a different mixture where one receiver held the charge
   back, so the cut is real -- but the heart is only {heart_x:.3f} mole fraction
   in its dominant component, against a target of 0.85.

   !! AND THE REASON IS APPARATUS, NOT PROTOCOL. This is a SIMPLE still: pot,
   one head, condenser. That is about ONE theoretical plate, and one plate
   cannot deliver 0.85 from a three-component charge no matter where the bands
   are put -- moving them trades yield for purity along a curve that tops out
   well below it. Real fractional distillation gets its purity from PLATES: a
   packed column is tens of them, and each one is (in this engine's terms)
   another vessel with a vapour edge up and a drain back down.

   So the honest statement is that M2 delivered the VERB and the apparatus to
   say a cut, and that reaching a high-purity heart is a matter of building a
   column out of the pieces now available -- which needs no new engine work at
   all, only more edges. That is ``examples/plate_column.py``, and it does reach
   0.85 -- but only after the sealed-rig defect above was found, because a
   sealed column pressurises harder the taller it is.""")

# ---------------------------------------------------------------------------
rule("PANEL 3 -- IT REPLAYS, AND IT FINDS ITS OWN CUT POINTS")
# ---------------------------------------------------------------------------
saved = w2.save()
w3 = World.replay(saved)
print()
print("   The script stores the BAND, never the instant. So the replay re-runs")
print("   the root solve and lands on its own crossings.")
print()
print(f"   {'receiver':>10s} {'original':>12s} {'replayed':>12s} {'delta':>12s}")
worst = 0.0
for r in RECEIVERS:
    a, _ = composition(w2, r)
    b, _ = composition(w3, r)
    worst = max(worst, abs(a - b))
    print(f"   {r:>10s} {a:12.8f} {b:12.8f} {abs(a - b):12.3e}")
print(f"\n   worst disagreement: {worst:.3e} mol")
print(f"   pot T {w2.vessels['pot'].T:.6f} vs {w3.vessels['pot'].T:.6f} K")

script = [e for e in w2.script if e.get("do") == "collect_fraction"]
print(f"""
   {len(script)} collect_fraction entries in the script, and not one of them
   carries a timestamp -- {', '.join(str(e['enter']) + '-' + str(e['leave']) for e in script)} K.
   That is the whole point: a recipe is a set of CONDITIONS.""")

# ---------------------------------------------------------------------------
rule("PANEL 4 -- WHAT THE HEAD IS FOR, AND WHY IT NEEDED ENGINE WORK")
# ---------------------------------------------------------------------------
w4 = still()
charge(w4)
out = w4.wait_until("head", Condition("temperature_above", 320.0), timeout=900.0)
print(f"""
   wait_until on the HEAD -- not the pot -- fired after {out.elapsed:.2f} s with
   the head at {w4.vessels['head'].T:.2f} K and the pot at {w4.vessels['pot'].T:.2f} K.

   !! THE ROOT HAS TO BE FOUND ON THE COUPLED TRAJECTORY. World used to satisfy
   a wait by integrating the owner vessel ALONE, then advancing the others by
   however long that took. For a bench of separate flasks that is exactly right.
   For a still it is not: nearly all of the head's heat arrives through the
   vapour edge, so a head integrated by itself just sits at its bath temperature
   and either never crosses the band or crosses it at an instant the real run
   never passes through. Every cut above is called off that number, so
   RigIntegrator.step_until lifts the condition onto the rig's own state vector.""")

rule("WHAT M2 COST")
print("""   ENGINE:  one new method on the rig integrator (step_until), one on the
            rig (wait_until). NO new physics -- the condenser is still just a
            cold vessel with two edges.
   PROTOCOL: Scenario.edges, SWAP_RECEIVER, SET_EDGE, collect_fraction.
            SAVE_VERSION 4 -> 5, because a v4 save has no edges and would
            replay as an uncoupled bench: a different experiment, not a
            missing field.
   PRESERVED: a world with NO edges keeps the old per-vessel stepping path
            exactly, so every number measured before rigs existed is
            bit-identical. Edges are the signal that the glassware is
            actually connected.""")
print()

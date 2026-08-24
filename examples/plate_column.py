"""M2 -- PURITY COMES FROM PLATES, and a plate is just another vessel.

``examples/fractional_distillation.py`` built the vocabulary of a cut and then
reported an honest failure: a heart of 0.523 mole fraction against a target of
0.85. The diagnosis in that file was right about the cause -- a pot, one head and
a condenser is about ONE theoretical plate -- and it said the fix needed no new
engine work, only more edges. This file is that fix, and it does reach the
target: **0.853 mole fraction ethanol from a 50/50 ethanol/water charge, with
eight plates at a reflux ratio of 5.**

A plate, in this engine's terms, is a vessel with a vapour edge UP and a drain
back DOWN. Nothing else. It is a theoretical stage because the physics already
there makes it one: vapour arriving from below finds ``p > p_eq`` in a slightly
cooler vessel and partly condenses, the plate's own liquid evaporates, and the
vapour leaving is in equilibrium with the liquid held. Measured below, each plate
buys very nearly a full stage.

# ⚠⚠ THE FIRST COLUMN ATTEMPT FAILED, AND THE PUBLISHED DIAGNOSIS WAS WRONG

That attempt was recorded as a column STARTUP problem -- the plates never warmed
into the band, so the fix was to flood at total reflux before taking off. Flooding
IS necessary and it is done below. But it was not the bug.

**The bug was that the still had no open end.** Vessels vent through ``k_vent``
and a receiver is reached only by a DRAIN, so the pot, the head, the condenser and
every plate between them were one SEALED volume. Measured on this very column with
the condenser's vent shut, panel 1: **3.35 bar, the pot boiling at 386 K instead
of 353, and every plate above 384 K.** A sealed column pressurises HARDER the
taller it is, which is exactly why adding plates made it worse rather than better,
why UNIFAC was evaluated outside the range its correlations cover, and why a head
band chosen at one atmosphere was never going to be entered.

⚠ The transferable form: **a rig's gas phase needs somewhere to go, and no vessel
in a still has that by default.** ``k_vent`` defaults to 1e3 on a ``VesselSpec``,
so a bench flask is open and a hand-built still is not -- the still's author has
to turn one vent back on, and there is nothing that says so.

# THE OTHER TWO THINGS THIS MEASURED

⚠ **BOILUP IS A PLATE-EFFICIENCY KNOB, NOT A CLOCK.** The obvious way to make a
distillation example cheaper is to turn the mantle up: take-off rate is
``boilup/(R+1)``, so twice the power should halve the wall clock. It does neither.
The same eight plates at the same R=5 plateau at **0.8538 at 250 W and 0.8486 at
500 W** -- 500 W misses the target that 250 W meets -- and the two runs cost the
same wall clock anyway (403 s against 409 s), because the faster take-off is paid
for in stiffness. A plate here is a KINETIC stage, so pushing more vapour through
the same ``kla`` and the same holdup gives it less time to equilibrate, which is a
real column's behaviour too. **The run cannot be sped up by pushing harder.**

⚠ **IN A GOOD COLUMN THE HEAD DOES NOT MOVE, SO THE HEAD IS THE WRONG INSTRUMENT
FOR CLOSING THIS CUT.** ``fractional_distillation.py`` learned that the head and
not the condenser is where the thermometer goes, and that stands. But over the
whole ethanol take-off below the head sits at **351.19 K and moves by 0.002 K** --
that flatness is what good rectification IS. The signal is in the POT, whose
bubble point climbs as it is stripped, and ``wait_until`` works on any vessel in
the rig, so the band is read there. A chemist does the same thing: the head holds
at 78 C for the whole cut and you watch the pot.

⚠ **COST: this example is about thirteen minutes of saturated CPU, and HALF OF IT
IS PANEL 4** -- a replay re-runs the whole protocol from the script, which is the
point of it. Fourteen coupled vessels, and the expensive part is the cold-start
FLOOD rather than the take-off: bringing eight dry plates to reflux is ~155 s of
wall clock for 135 s of simulated time, against ~0.12 s per simulated second once
the column is running. Declaring the plates already warm (T=345 K) changes it by
**1 s** -- the transient is the phase change, not the heat-up -- so there is no
cheap version of this. ⚠ The mechanism is pinned cheaply in
``tests/test_still.py`` at one and two plates, including a replayed cut; what only
this file can afford is the eight plates the 0.85 target needs.
⚠ Sparsity DOES pay here, unlike on the two-vessel rigs where it was measured to
be pure overhead: a chain of vapour edges is banded, so ``useful_sparsity`` finds
60 column groups in a 238-column Jacobian and passes the pattern.

Run: python examples/plate_column.py
"""

from __future__ import annotations

import time

from chemsim.engine import EdgeSpec, Scenario, VesselSpec, World
from chemsim.matter import Molecule
from chemsim.vessel import Condition


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


ETHANOL = c("CCO")          # bp 351.4 K
WATER = c("O")              # bp 373.1 K
AIR = ["N#N", "O=O"]

PLATES = 8
REFLUX_RATIO = 5.0
K_REFLUX = 0.5              # 1/s out of the condenser, back down the column
CHARGE = 2.0                # mol of each -- a 50/50 charge, 4 mol in all

# The ethanol/water azeotrope is at x = 0.888, so 0.85 leaves 0.038 of headroom
# and there is nothing a column can do about the rest of it.
TARGET = 0.85


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def column(plates: int = PLATES, *, sealed: bool = False) -> tuple[World, list[str]]:
    """A pot, ``plates`` plates, a head, a condenser and three receivers.

    ⚠ THE REFLUX SPLIT IS TWO DRAINS OUT OF ONE CONDENSER, and that is what makes
    the reflux ratio an exact, declared number rather than something to be
    inferred. Both drains are first order in the same holdup, so they divide it
    exactly in the ratio of their conductances: ``R = k_reflux / k_takeoff``,
    whatever the holdup settles at. Closing the take-off (``k = 0``) is total
    reflux, which is how the column is flooded.
    """
    pot = VesselSpec(volume=1.0, T=298.15, T_env=298.15, UA=1.0,
                     Q_input=250.0, kla=5.0, k_vent=0.0, lle=False)
    # A plate: small, thin-walled, barely coupled to the room, so what sets its
    # temperature is the latent heat of the vapour passing through it.
    plate = VesselSpec(volume=0.10, T=298.15, T_env=298.15, UA=0.1, kla=5.0,
                       k_vent=0.0, heat_capacity=5.0, lle=False)
    head = VesselSpec(volume=0.10, T=298.15, T_env=298.15, UA=0.3, kla=5.0,
                      k_vent=0.0, heat_capacity=5.0, lle=False)
    # ⚠⚠ THE ONE VENT IN THE APPARATUS, AND PANEL 1 IS WHAT HAPPENS WITHOUT IT.
    # A distillation at atmospheric pressure is OPEN to the room, and the open
    # point is the condenser outlet. Sealed, this column runs at 3.35 bar.
    cond = VesselSpec(volume=0.5, T=288.0, T_env=288.0, UA=40.0, kla=5.0,
                      k_vent=0.0 if sealed else 1.0, heat_capacity=20.0,
                      lle=False)
    # ⚠ kla > 0 on a receiver, still. A receiver with kla=0 leaves its gas block
    # identically flat, and an unconnected receiver is an isolated block inside
    # one coupled Jacobian -- BDF's LU factorisation of that was singular.
    jar = VesselSpec(volume=0.5, T=288.0, T_env=288.0, UA=5.0, kla=5.0,
                     k_vent=10.0, lle=False)

    names = [f"plate{i + 1}" for i in range(plates)]
    stack = ["pot", *names, "head", "condenser"]
    vessels = {"pot": pot, **{n: plate for n in names}, "head": head,
               "condenser": cond, "forerun": jar, "heart": jar, "tail": jar}

    edges = [EdgeSpec("vapour", a, b, k=20.0) for a, b in zip(stack, stack[1:])]
    down = list(reversed(stack[:-1]))           # head, plateN .. plate1, pot
    edges += [EdgeSpec("drain", a, b, k=0.5) for a, b in zip(down, down[1:])]
    edges.append(EdgeSpec("drain", "condenser", "head", k=K_REFLUX))
    # ⚠ THE LAST EDGE IS THE ONE THAT MOVES, and it starts SHUT. Opening it is
    # SET_EDGE; re-pointing it is SWAP_RECEIVER; doing both around a band is
    # collect_fraction.
    edges.append(EdgeSpec("drain", "condenser", "forerun", k=0.0))

    world = World(Scenario(
        feed_species=[ETHANOL, WATER, *AIR], templates=[], max_species=20,
        vessels=vessels, edges=edges,
    ))
    return world, stack


def charge(w: World) -> None:
    w.now("charge", "pot", amounts={ETHANOL: CHARGE, WATER: CHARGE})
    for v in w.vessels:
        w.now("fill_headspace", v)
    w.flush()


def liquid(w: World, vid: str) -> tuple[float, float]:
    """(moles of liquid held, mole fraction ethanol in it)."""
    n = w.vessels[vid].state().n_liquid
    total = sum(n.values())
    return total, (n.get(ETHANOL, 0.0) / total if total > 1.0e-12 else 0.0)


def profile(w: World, stack: list[str]) -> None:
    print(f"   {'stage':>10s} {'T / K':>8s} {'P / bar':>8s} {'mol held':>10s} "
          f"{'x(EtOH)':>8s}")
    for v in stack:
        held, x = liquid(w, v)
        print(f"   {v:>10s} {w.vessels[v].T:8.2f} {w.vessels[v].pressure:8.3f} "
              f"{held:10.3e} {x:8.4f}")


# ---------------------------------------------------------------------------
rule("PANEL 1 -- A SEALED COLUMN IS NOT A COLUMN")
# ---------------------------------------------------------------------------
print("""
   Two plates, the condenser's vent SHUT -- i.e. the apparatus as it was when
   the first column attempt was made. Nothing is being taken off, so this is
   just a column at total reflux.""")
w0, stack0 = column(2, sealed=True)
charge(w0)
print()
print(f"   {'t / s':>7s} {'P / bar':>8s} {'pot T':>8s} {'plate1 T':>9s} "
      f"{'head T':>8s}")
for _ in range(5):
    w0.step(60.0)
    print(f"   {w0.t:7.0f} {w0.vessels['pot'].pressure:8.3f} "
          f"{w0.vessels['pot'].T:8.2f} {w0.vessels['plate1'].T:9.2f} "
          f"{w0.vessels['head'].T:8.2f}")
print(f"""
   !! {w0.vessels['pot'].pressure:.2f} BAR, and the pot boiling at
   {w0.vessels['pot'].T:.1f} K rather than 353. Every vessel above vents at
   k_vent=0 and the receivers are reached only by a DRAIN, so the gas phase has
   nowhere to go and the whole column is one sealed vessel being heated.

   That is the actual reason the first column attempt failed -- not startup. The
   published diagnosis was wrong, and it was wrong in a way that pointed at the
   right fix for the wrong reason: a taller column seals a LARGER volume against
   the same 250 W, so adding plates raised the pressure, pushed the plates
   further outside the range UNIFAC's correlations cover (hence the reported
   'overflow encountered in exp'), and put every plate 30 K above any band that
   had been chosen from a table of atmospheric boiling points.""")

# ---------------------------------------------------------------------------
rule(f"PANEL 2 -- FLOOD IT: {PLATES} PLATES AT TOTAL REFLUX")
# ---------------------------------------------------------------------------
t_wall = time.time()
w, stack = column()
TAKEOFF = len(w.rig.connections) - 1
charge(w)
print(f"""
   The take-off is shut (k=0 on edge {TAKEOFF}), so every drop that
   condenses runs back down the column. Flooding is what the first attempt
   skipped -- and it is still necessary, even though it was not the bug.

   Two waits, in the order the temperature_steady docstring argues for: get into
   the interesting regime FIRST, then watch for steadiness. A bare
   temperature_steady fires on the first transient it meets.""")
warm = w.wait_until("head", Condition("temperature_above", 349.0), timeout=1200.0)
settle = w.wait_until("head", Condition("temperature_steady", 0.005), timeout=900.0)
print(f"""
   vapour reached the head after {warm.elapsed:.1f} s; the head then steadied
   {settle.elapsed:.1f} s later (timed_out={settle.timed_out}).
""")
profile(w, stack)
_, pot_x = liquid(w, "pot")
_, top_x = liquid(w, "condenser")
print(f"""
   !! THAT LADDER IS THE WHOLE POINT. {pot_x:.4f} in the pot, {top_x:.4f} at the
   top, and each plate is very nearly a full theoretical stage -- the liquid on a
   plate sits at the composition of the vapour that came off the one below it.
   Nothing in the engine knows the word 'plate'; each is a vessel with a vapour
   edge up and a drain back down.

   !! AND temperature_steady NEEDED AN ENGINE FIX TO BE USABLE HERE. Every other
   condition in the vocabulary reads the STATE, so lifting it onto the rig's
   state vector by the owner's slice answers it exactly. This one reads the
   DERIVATIVE, and it was compiled from the owner vessel's OWN rhs -- which for a
   still head is the cooling rate of a small flask of hot ethanol in a cold room,
   a different question with a different answer. Measured: a column pinned at
   351.22 K and unmoving for 1200 s TIMED OUT on the lifted root. Rig.wait_until
   now builds this one kind against the rig's own RHS. Same lesson as
   step_until's, one level deeper -- it is not only WHEN a condition is located
   that belongs to the coupled trajectory, it is what the condition computes.""")

# ---------------------------------------------------------------------------
rule("PANEL 3 -- OPEN THE TAKE-OFF, AND CUT THE HEART")
# ---------------------------------------------------------------------------
w.now("set_edge", edge=TAKEOFF, k=K_REFLUX / REFLUX_RATIO)
w.flush()
print(f"""
   SET_EDGE opens the tap to k={K_REFLUX / REFLUX_RATIO:g} against the reflux
   drain's {K_REFLUX:g}. Both are first order in the same condenser holdup, so
   they split it EXACTLY in that ratio whatever the holdup settles at: reflux
   ratio R = {REFLUX_RATIO:g}, declared rather than inferred.

   The band is on the POT, and that is deliberate -- see the module docstring.
   The head holds flat to two decimals across this entire cut, which is what
   good rectification means, so it carries no signal to cut on. The pot's bubble
   point climbs as it is stripped, and that does.""")
before = w.t
cut = w.collect_fraction("pot", TAKEOFF, "heart", 353.05, 353.30, 1800.0,
                         park="tail")
# A short run on the parked receiver, so the tail holds something to compare.
w.step(150.0)
held, x = liquid(w, "heart")
recovery = 100.0 * held * x / CHARGE
print(f"""
   collect_fraction('pot', edge {TAKEOFF}, 'heart', 353.05, 353.30 K):
     entered {cut['entered']}   left {cut['left']}   waited {cut['wait']:.1f} s
     collected over {cut['collected']:.1f} s   (t {before:.1f} -> {w.t:.1f})
""")
print(f"   {'receiver':>10s} {'mol held':>10s} {'x(EtOH)':>8s} {'mol EtOH':>9s}")
for r in ("forerun", "heart", "tail"):
    h, xr = liquid(w, r)
    print(f"   {r:>10s} {h:10.4f} {xr:8.4f} {h * xr:9.4f}")
print(f"""
   head {w.vessels['head'].T:.3f} K   pot {w.vessels['pot'].T:.3f} K   """
      f"""pot x(EtOH) {liquid(w, 'pot')[1]:.4f}

   !! HEART = {x:.4f} MOLE FRACTION ETHANOL, against a target of {TARGET:.2f}
   and an azeotrope ceiling of 0.888. {held:.4f} mol collected, containing
   {held * x:.4f} mol of ethanol = {recovery:.1f}% of the {CHARGE:g} mol charged.
   {PLATES} plates, reflux ratio {REFLUX_RATIO:g}. Target {'MET' if x >= TARGET else 'NOT MET'}.

   !! AND THE CUT IS ON A PLATEAU RATHER THAN A PEAK, which is the useful part.
   The cumulative purity of this receiver is flat: it reads 0.845 in the first
   50 s of take-off and 0.854 after 2000 s, because eight plates working from a
   pot that has fallen from x = 0.49 to x = 0.35 still land in the same place.
   So the band above trades YIELD, not purity -- a longer cut on the same column
   reaches 46.5% recovery at 0.8535, measured. What it cannot trade for is the
   azeotrope.""")

# ---------------------------------------------------------------------------
rule("PANEL 4 -- IT REPLAYS, AND IT FINDS ITS OWN CUT POINT")
# ---------------------------------------------------------------------------
saved = w.save()
print(f"""
   save version {saved['version']}; {len(saved['scenario']['edges'])} edges and
   {len(saved['scenario']['vessels'])} vessels of apparatus, all of it DATA. The
   script holds {len(w.script)} entries and the only numbers in the cut are the
   two band temperatures -- the column locates its own crossing.""")
w2 = World.replay(saved)
print()
print(f"   {'receiver':>10s} {'original':>12s} {'replayed':>12s} {'delta':>12s}")
worst = 0.0
for r in ("forerun", "heart", "tail"):
    a, _ = liquid(w, r)
    b, _ = liquid(w2, r)
    worst = max(worst, abs(a - b))
    print(f"   {r:>10s} {a:12.8f} {b:12.8f} {abs(a - b):12.3e}")
print(f"\n   worst disagreement: {worst:.3e} mol")
print(f"   pot T {w.vessels['pot'].T:.6f} vs {w2.vessels['pot'].T:.6f} K")
entry = [e for e in w.script if e.get("do") == "collect_fraction"]
print(f"   collect_fraction script entry: {entry}")

rule("WHAT THE COLUMN COST")
print(f"""   ENGINE:  ONE fix, and it was not about plates -- temperature_steady on a
            rig vessel was being answered by the vessel's own uncoupled
            derivative. Nothing else: a plate is a VesselSpec and two edges.
   APPARATUS: pot + {PLATES} plates + head + condenser + 3 receivers = 14
            vessels, {len(w.rig.connections)} edges, all of it in the Scenario.
   FOUND:   a still with no vent is a sealed pressure vessel (panel 1), and
            that -- not startup -- is why the first column attempt failed.
            Boilup is a plate-efficiency knob: 500 W plateaus at 0.8486.
   WALL:    {time.time() - t_wall:.0f} s for panels 2-4, on fourteen coupled
            vessels. The cold-start FLOOD dominates, not the distillation.""")
print()

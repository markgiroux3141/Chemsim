"""How long does a bench operation take to SIMULATE? Not what you would guess.

Wall-clock cost here has almost nothing to do with simulated duration, and knowing
which way round it goes is what a user interface has to be designed against.

    python validation/wall_clock.py

⚠ Printed text is ASCII only. The Windows console is cp1252 and a warning glyph
inside a print() kills the script at that line. Docstrings are fine.
"""

from __future__ import annotations

import time

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.reactions.library import (
    aerobic_oxidation,
    esterification,
    ether_condensation,
    peroxide_over_oxidation,
)
from chemsim.vessel import Vessel


def smi(s: str) -> str:
    return Molecule.from_smiles(s).smiles


WATER, ETOH, NA, OH = "O", "CCO", "[Na+]", "[OH-]"
O2, N2 = "O=O", "N#N"
TOLUENE = smi("Cc1ccccc1")
ESTER = smi("CCOC(=O)c1ccccc1")
ACID = smi("OC(=O)c1ccccc1")
BENZOATE = smi("[O-]C(=O)c1ccccc1")
THERMO = electrolyte_provider()

print(__doc__.split("\n\n")[0])
print("\n" + "=" * 78)
print("WALL CLOCK PER OPERATION -- ratio > 1 means FASTER than real time")
print("=" * 78)

ROWS: list[tuple[str, float, float, str]] = []


def timed(label: str, simulated: float, note: str, build):
    """Build a vessel, run it for ``simulated`` seconds, and time the run."""
    v = build()
    t0 = time.perf_counter()
    try:
        v.run(simulated)
        wall = time.perf_counter() - t0
    except Exception as exc:                                    # noqa: BLE001
        ROWS.append((label, simulated, float("nan"), f"FAILED: {str(exc)[:30]}"))
        return None
    ROWS.append((label, simulated, wall, note))
    return v


# --- an idle flask: the common case in a game, and it gets no solver at all ---
idle_net = build_network([WATER, ETOH], [], thermo=THERMO, max_species=10)


def idle():
    v = Vessel(idle_net, volume=1.0, T=298.15, T_env=298.15, UA=0.0, kla=0.0,
               k_diss=0.0, k_vent=0.0)
    v.charge({WATER: 30.0})
    v.run(1.0)          # let it settle, so the second run is the resting case
    return v


timed("an idle flask, settled", 3600.0, "no solver at all -- see run()'s "
      "stationary short-circuit", idle)

# --- a flask heated to boiling and held there --------------------------------
boil_net = build_network([WATER, ETOH, N2, O2], [], thermo=THERMO, max_species=20)


def boiling():
    v = Vessel(boil_net, volume=2.0, T=298.15, T_env=298.15, UA=0.5,
               Q_input=60.0, kla=5.0)
    v.charge({ETOH: 3.0, WATER: 3.0})
    v.fill_headspace_with_air()
    v.run(600.0)        # get it to the plateau first
    return v


timed("ethanol/water at the plateau", 1200.0, "steady state: derivative nearly "
      "zero", boiling)

# --- a separatory funnel: a phase split plus interphase transport ------------
funnel_net = build_network(
    [WATER, TOLUENE, NA, "[Cl-]"], [], thermo=THERMO, max_species=20
)


def funnel():
    v = Vessel(funnel_net, volume=4.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0,
               k_diss=0.0, k_vent=0.0)
    v.charge({WATER: 27.7, TOLUENE: 4.7, NA: 1.0, "[Cl-]": 1.0})
    return v


timed("brine + toluene separating", 600.0, "a phase split and an ion model",
      funnel)

# --- the prep, step by step -------------------------------------------------
prep_net = build_network(
    [ESTER, ACID, ETOH, WATER, OH, NA, "OS(=O)(=O)O", O2, N2],
    [esterification(), aerobic_oxidation(), peroxide_over_oxidation(),
     ether_condensation(), *dissociation_templates()],
    thermo=THERMO, max_species=120,
)


def pot():
    v = Vessel(prep_net, volume=2.0, T=353.0, T_env=353.0, UA=20.0, kla=5.0,
               k_diss=0.05, k_vent=0.0, k_lle=0.5)
    v.charge({WATER: 55.0, ESTER: 0.20, OH: 0.30, NA: 0.30})
    v.fill_headspace_with_air()
    return v


# ⚠ SEQUENTIALLY ON ONE VESSEL, which is both what the prep actually does and the
# only affordable way to measure it: rebuilding the post-saponification state for
# each row would re-run the two-hour cook three times over.
prep_pot = pot()


def step_of(label: str, simulated: float, note: str, before=None):
    if before is not None:
        before(prep_pot)
    t0 = time.perf_counter()
    prep_pot.run(simulated)
    ROWS.append((label, simulated, time.perf_counter() - t0, note))


step_of("a 2 h two-phase saponification", 7200.0,
        "18 species, 15 reactions; splits and re-merges")


def quench(v):
    v.charge({"OS(=O)(=O)O": 0.28})
    v.set_environment(275.0)


step_of("... then 10 s of the acid quench", 10.0,
        "THE EXPENSIVE ONE -- everything at once", before=quench)
step_of("... then the rest of that hour", 3590.0,
        "the transient is what costs, not the hour")
step_of("... then 4 h of crystals growing", 14400.0,
        "cheap again once supersaturation has relaxed")

# ---------------------------------------------------------------------------
print(f"\n  {'operation':>34s} {'simulated':>11s} {'wall':>9s} "
      f"{'x real time':>13s}")
for label, simulated, wall, note in ROWS:
    if wall != wall:                                   # NaN
        print(f"  {label:>34s} {simulated:10.0f}s {'--':>9s} {'--':>13s}  {note}")
        continue
    ratio = simulated / wall if wall > 0 else float("inf")
    shown = f"{ratio:,.0f}x faster" if ratio >= 1 else f"{1 / ratio:,.1f}x SLOWER"
    print(f"  {label:>34s} {simulated:10.0f}s {wall:8.2f}s {shown:>13s}")
print()
for label, simulated, wall, note in ROWS:
    print(f"    {label}: {note}")

print("""
==============================================================================
WHAT THIS MEANS, AND IT IS THE WRONG WAY ROUND FOR A GAME
==============================================================================

  COST IS CONCENTRATED IN STIFF TRANSIENTS, NOT IN ELAPSED TIME. A two-hour
  reflux at steady state is nearly free, because the derivative is nearly zero
  and BDF can take enormous steps; a flask that is genuinely at rest gets no
  solver at all, which is a correctness fix as much as a speed one (num_jac
  cannot discover a vanishing derivative -- it inflates its perturbation to
  infinity and then rejects every step forever).

  What costs is the moment when everything happens at once: a strong acid
  meeting a strong base, a supersaturation collapsing, two layers separating.
  Ten seconds of an acid quench costs more than four hours of crystal growth.

  WARNING: SO THE EXPENSIVE MOMENTS ARE EXACTLY THE ONES A PLAYER IS WATCHING, and a
  frontend cannot assume that a short action is a cheap one. Two consequences:

    an interface must be able to show an operation IN PROGRESS rather than
    blocking on it -- the engine is already stepped rather than run, so this is
    a frontend concern and not an engine one;

    and "wait until" (a scipy solve_ivp ROOT EVENT) is about responsiveness as
    well as expressiveness. Fixed durations force a choice between overshooting
    the interesting instant and paying for steps that resolve nothing.

  AND THE TEST SUITE'S COST IS A DIFFERENT PROBLEM. Five tests are 77% of it,
  four of them coupled RIGS, and they are slow for a reason nothing above
  touches: the rig marks each vessel's whole block dense in jac_sparsity, so an
  empty second liquid layer costs a full set of Jacobian columns in every
  vessel. That is the lever, and it is unspent.""")

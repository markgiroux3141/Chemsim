"""IS "WAIT UNTIL" A ROOT AT ALL? Bounding each condition before implementing it.

"Reflux until the head stabilises", "cool until crystals appear", "distil until
the pot hits X" are the shape a real procedure has, and none of them is a number
of seconds. The mechanism for expressing them is not in doubt -- scipy's
``solve_ivp`` locates a root of a scalar function of state to solver tolerance,
independently of the caller's step size, which is exactly the determinism the
event layer already rests on.

⚠ WHAT IS IN DOUBT IS WHETHER EACH CONDITION IS A ROOT. Two of the three obvious
ones are suspect on their face:

  * "the temperature has stabilised" is dT/dt -> 0, and it approaches zero
    ASYMPTOTICALLY. A function that never crosses is not a root, and a root
    function that only grazes zero is worse than one that never reaches it,
    because the solver will find it somewhere arbitrary;
  * "crystals appear" is nS crossing a threshold, and nS sitting at exactly zero
    is the flat-column trap this project has already paid for twice.

So each candidate is sampled along a REAL trajectory here, and what is being
looked for is specific: does the function cross, does it cross ONCE, and how
steeply. A condition that grazes or that crosses many times is reported as
unsuitable rather than implemented and hoped for. This is the same discipline that
killed crystal occlusion before it was built.

    python validation/wait_conditions.py

⚠ Printed text is ASCII only. The Windows console is cp1252 and a warning glyph
inside a print() kills the script at that line. Docstrings are fine.
"""

from __future__ import annotations


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


def rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def smi(s: str) -> str:
    return Molecule.from_smiles(s).smiles


WATER, ETOH, NA, OH = "O", "CCO", "[Na+]", "[OH-]"
O2, N2, SULFURIC = "O=O", "N#N", "OS(=O)(=O)O"
ESTER = smi("CCOC(=O)c1ccccc1")
ACID = smi("OC(=O)c1ccccc1")

print(__doc__.split("\n\n")[0])


def sample(v: Vessel, span: float, points: int) -> list[dict]:
    """Walk a vessel forward, recording every candidate root function.

    Sampled on a real trajectory rather than on a sketch, because the question is
    empirical: a function is a usable root if it crosses zero once, cleanly, on
    the trajectory the player will actually be driving.
    """
    n = v.integrator.n
    idx = {s: i for i, s in enumerate(v.species)}
    rows = []
    dt = span / points
    for k in range(points + 1):
        y = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
        # The derivative is available for free: the RHS is a pure function of
        # state, so "how fast is it changing" costs one call and no bookkeeping.
        dy = v.integrator.make_rhs(y)(0.0, y)
        p_eq = v.integrator.equilibrium_pressures(v._nL, v.T, v._nL2)
        rows.append({
            "t": k * dt,
            "T": v.T,
            "dTdt": float(dy[-1]),
            "excess_p": float(p_eq.sum()) - v.P_ambient,
            "nS": float(v._nS[idx[ACID]]) if ACID in idx else 0.0,
            "dnS": float(dy[3 * n + idx[ACID]]) if ACID in idx else 0.0,
            "pH": v.pH,
        })
        if k < points:
            v.step(dt)
    return rows


def crossings(rows: list[dict], key: str, level: float) -> list[float]:
    """Times at which ``key`` crosses ``level``, by linear interpolation."""
    out = []
    for a, b in zip(rows, rows[1:]):
        fa, fb = a[key] - level, b[key] - level
        if fa == 0.0:
            out.append(a["t"])
        elif fa * fb < 0.0:
            out.append(a["t"] + (b["t"] - a["t"]) * fa / (fa - fb))
    return out


def verdict(rows, key, level, name, unit="") -> None:
    xs = crossings(rows, key, level)
    vals = [r[key] for r in rows]
    lo, hi = min(vals), max(vals)
    # Steepness AT the crossing is what decides whether a root solve is
    # well-conditioned: a function that grazes gives the solver nothing to bite on.
    slope = 0.0
    if xs:
        t0 = xs[0]
        for a, b in zip(rows, rows[1:]):
            if a["t"] <= t0 <= b["t"] and b["t"] > a["t"]:
                slope = (b[key] - a[key]) / (b["t"] - a["t"])
                break
    if not xs:
        note = "NEVER CROSSES -- not a root on this trajectory"
    elif len(xs) > 3:
        note = f"crosses {len(xs)}x -- ambiguous, needs a direction"
    elif slope == 0.0:
        note = "GRAZES -- zero slope at the crossing"
    else:
        note = f"crosses once at t={xs[0]:.1f} s, slope {slope:.3e}{unit}/s"
    print(f"  {name:>40s} range [{lo:10.3e}, {hi:10.3e}]  {note}")


THERMO = electrolyte_provider()

# ---------------------------------------------------------------------------
rule("PANEL 1 -- A FLASK HEATED TO BOILING: three candidate conditions")
# ---------------------------------------------------------------------------
print("""
  50/50 ethanol/water over a 60 W hotplate, sampled for 20 minutes. This is the
  case "heat until it refluxes, then hold two hours" is asking about, and it also
  contains the asymptote: once the flask reaches its bubble point the temperature
  stops rising, and it stops rising SMOOTHLY.
""")
boil_net = build_network([WATER, ETOH, N2, O2], [], thermo=THERMO, max_species=20)
b = Vessel(boil_net, volume=2.0, T=298.15, T_env=298.15, UA=0.5, Q_input=60.0,
           kla=5.0)
b.charge({ETOH: 3.0, WATER: 3.0})
b.fill_headspace_with_air()
boil_rows = sample(b, 1200.0, 60)

print(f"  {'t / s':>7s} {'T / K':>8s} {'dT/dt / K/s':>13s} "
      f"{'sum p_eq - P / bar':>19s}")
for r in boil_rows[::6]:
    print(f"  {r['t']:7.0f} {r['T']:8.2f} {r['dTdt']:13.3e} {r['excess_p']:19.4e}")

print()
verdict(boil_rows, "T", 340.0, "T - 340 K  ('until the pot hits X')", " K")
verdict(boil_rows, "excess_p", 0.0,
        "sum p_eq - P_ambient  ('until it boils')", " bar")
verdict(boil_rows, "dTdt", 0.01, "dT/dt - 0.01 K/s  ('until T stabilises')",
        " K/s")
verdict(boil_rows, "dTdt", 0.001, "dT/dt - 0.001 K/s  (ten times tighter)",
        " K/s")
verdict(boil_rows, "dTdt", 0.0, "dT/dt - 0  (the naive form)", " K/s")

# ---------------------------------------------------------------------------
rule("PANEL 2 -- THE PREP'S QUENCH: crystals appearing out of nothing")
# ---------------------------------------------------------------------------
print("""
  The other two conditions a recipe needs, on the trajectory that actually
  produces them: acidify a benzoate solution, cool it, and wait for a crop. Note
  what is being asked of nS -- it starts at EXACTLY zero, which is the state this
  project has twice paid for putting a switch at.
""")
prep_net = build_network(
    [ESTER, ACID, ETOH, WATER, OH, NA, SULFURIC, O2, N2],
    [esterification(), aerobic_oxidation(), peroxide_over_oxidation(),
     ether_condensation(), *dissociation_templates()],
    thermo=THERMO, max_species=120,
)
p = Vessel(prep_net, volume=2.0, T=353.0, T_env=353.0, UA=20.0, kla=5.0,
           k_diss=0.05, k_vent=0.0, k_lle=0.5)
p.charge({WATER: 55.0, ESTER: 0.20, OH: 0.30, NA: 0.30})
p.fill_headspace_with_air()
p.run(7200.0)
p.charge({SULFURIC: 0.28})
p.set_environment(275.0)
prep_rows = sample(p, 3600.0, 36)

print(f"  {'t / s':>7s} {'T / K':>8s} {'pH':>7s} {'nS(acid) / mol':>15s} "
      f"{'dnS/dt':>12s}")
for r in prep_rows[::3]:
    print(f"  {r['t']:7.0f} {r['T']:8.2f} {r['pH']:7.3f} {r['nS']:15.6e} "
          f"{r['dnS']:12.3e}")

print()
verdict(prep_rows, "nS", 1.0e-6, "nS - 1 umol  ('until crystals appear')",
        " mol")
verdict(prep_rows, "nS", 1.0e-9, "nS - 1 nmol  (at the solver's own atol)",
        " mol")
verdict(prep_rows, "nS", 0.0, "nS - 0  (the naive form)", " mol")
verdict(prep_rows, "pH", 7.0, "pH - 7  ('until it is acidic')", "")
verdict(prep_rows, "pH", 2.0, "pH - 2  ('until pH 2')", "")
verdict(prep_rows, "T", 280.0, "T - 280 K  ('until it is cold')", " K")
verdict(prep_rows, "dTdt", -0.001, "dT/dt + 0.001 K/s  ('until it stops cooling')",
        " K/s")

# ---------------------------------------------------------------------------
rule("PANEL 3 -- WHAT THE SAMPLING SAYS, AND WHAT IT IMPLIES FOR THE VERB")
# ---------------------------------------------------------------------------
print("""
  Read the two panels together and the conditions sort themselves into three
  kinds, which is the useful outcome:

  A THRESHOLD ON A STATE COMPONENT works and needs nothing special. T, pH and a
  pressure sum are monotone over the interesting stretch and cross with a healthy
  slope. These are safe to offer.

  A THRESHOLD ON AN AMOUNT THAT STARTS AT ZERO works only with the threshold
  ABOVE the solver's tolerance. At exactly zero the function does not cross -- it
  leaves zero -- and at 1e-9 it is being asked to resolve a crossing inside its
  own atol. A micromole is three orders of magnitude clear of that and is still
  far below anything a bench could see, which is the same argument the Born
  ceiling rests on.

  A DERIVATIVE APPROACHING ZERO IS NOT A ROOT and must not be offered as one. The
  naive form (dT/dt = 0) is the row to look at above: it is approached and not
  crossed. What IS a root is a TOLERANCE on the derivative -- 'the thermometer has
  stopped moving', which is a statement a chemist makes and a number a player can
  be given. So the verb takes the tolerance and the condition is
  ``abs(dT/dt) < rate``, never ``dT/dt == 0``.

  AND ONE THING THE SAMPLING CANNOT SEE, so it is stated rather than measured: a
  condition that is ALREADY TRUE at the start of a span. scipy does not fire an
  event at t0, so 'wait until it is above 300 K' on a flask already at 340 K would
  wait forever. That has to be checked before the solve, not inside it, and it is
  the difference between a verb that refuses cleanly and one that hangs.""")

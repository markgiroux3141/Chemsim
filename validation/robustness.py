"""EVERY STATE A PLAYER CAN REACH MUST WORK, OR REFUSE CLEANLY WITH A REASON.

Never a crash, and never a plausible-looking wrong number. That is the whole rule,
and it is a different rule from the one the rest of this project's harnesses check:
they ask whether a number is right, and this asks whether a state that nobody
designed for is handled at all.

It exists because handing the driving to a frontend hands it to somebody who will
boil things dry, mix arbitrary solvents, add acid to base, cool things past their
freezing points, seal flasks, forget to stopper them, overfill them, and retry the
same experiment in the same glassware. Every one of those is already a documented
fragility here -- four separate integration failures came out of ORDINARY setups in
one session, and the sharpest bug of that session reported ``sol.success`` and
returned a cancelling dipole of 3.07e9 mol that the non-negative projection then
tidied into something plausible.

So each row below is classified into exactly one of four outcomes:

    OK        it ran, and the resulting state is physically sane
    REFUSED   it raised, with a message that names a cause or a fix
    UNCLEAR   it raised, but the message would not help anybody
    WRONG     it ran and the state is not sane -- the failure mode that matters

⚠ AND THE SANITY CHECK IS ON THE RAW SOLVER OUTPUT, NOT THE PROJECTED STATE. That
is how the unclipped-gamma bug hid for a session: ``sol.success`` is necessary and
is nowhere near sufficient.

    python validation/robustness.py

⚠ Printed text is ASCII only. The Windows console is cp1252 and a warning glyph
inside a print() kills the script at that line. Docstrings are fine.
"""

from __future__ import annotations

import numpy as np

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.numerics.vessel_integrator import DRYOUT_MOLES, LAYER_EPS
from chemsim.properties import (
    ThermochemistryProvider,
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions.library import esterification
from chemsim.vessel import Vessel


def rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def smi(s: str) -> str:
    return Molecule.from_smiles(s).smiles


WATER, ETOH, N2, O2 = "O", "CCO", "N#N", "O=O"
TOLUENE, HEXANE, DCM = smi("Cc1ccccc1"), smi("CCCCCC"), smi("ClCCl")
BENZOIC = smi("OC(=O)c1ccccc1")
ACETIC, NA, OH = "CC(=O)O", "[Na+]", "[OH-]"
SULFURIC = "OS(=O)(=O)O"

print(__doc__.split("\n\n")[0])

PLAIN = ThermochemistryProvider()
IONIC = electrolyte_provider()

SOLVENT_NET = build_network([WATER, ETOH, TOLUENE, HEXANE, DCM, N2, O2], [],
                            thermo=PLAIN, max_species=40)
IONIC_NET = build_network(
    [WATER, ETOH, ACETIC, NA, OH, SULFURIC, BENZOIC, TOLUENE, N2, O2],
    dissociation_templates(), thermo=IONIC, max_species=80,
)
ESTER_NET = build_network([ACETIC, ETOH, WATER, N2, O2], [esterification()],
                          thermo=PLAIN, max_species=40)

ROWS: list[tuple[str, str, str]] = []


def sane(v: Vessel) -> str:
    """Is this state physically possible? Returns "" or what is wrong with it.

    Deliberately narrow. It is not asking whether a number is a good prediction --
    that is what every other harness here is for. It is asking whether the state
    could exist at all, which is the question a crash-free wrong answer fails.
    """
    y = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    if not np.all(np.isfinite(y)):
        return "non-finite entries in the state"
    n = v.integrator.n
    for name, block in (("liquid1", v._nL), ("liquid2", v._nL2),
                        ("gas", v._nG), ("solid", v._nS)):
        worst = float(np.min(block)) if block.size else 0.0
        if worst < -1.0e-6:
            return f"{name} holds {worst:.3e} mol of something"
    if not 1.0 <= v.T <= 5000.0:
        return f"temperature {v.T:.4g} K"
    if v.pressure > 1.0e4:
        return f"pressure {v.pressure:.3e} bar"
    del n
    return ""


def attempt(label: str, build, drive) -> None:
    """Run one abusive setup and classify the outcome."""
    try:
        v = build()
    except Exception as exc:                                    # noqa: BLE001
        ROWS.append((label, "REFUSED", f"at setup: {str(exc).splitlines()[0][:64]}"))
        return
    try:
        drive(v)
    except Exception as exc:                                    # noqa: BLE001
        first = str(exc).splitlines()[0]
        # A refusal earns its name by saying something actionable. A bare
        # LinAlgError or a KeyError does not.
        useful = len(first) > 40 and not isinstance(
            exc, (KeyError, IndexError, AttributeError, TypeError, ZeroDivisionError)
        )
        ROWS.append((label, "REFUSED" if useful else "UNCLEAR", first[:64]))
        return
    bad = sane(v)
    ROWS.append((label, "WRONG" if bad else "OK",
                 bad or f"T={v.T:7.2f} K  P={v.pressure:6.3f} bar"))


def flask(net, **kw):
    base = dict(volume=1.0, T=298.15, T_env=298.15, UA=5.0, kla=5.0)
    base.update(kw)
    return Vessel(net, **base)


# ---------------------------------------------------------------------------
rule("PANEL 1 -- THINGS A PLAYER DOES WRONG")
# ---------------------------------------------------------------------------


def _boil_dry():
    v = flask(SOLVENT_NET, volume=0.5, T=340.0, UA=0.2, Q_input=80.0)
    v.charge({ETOH: 0.3})
    return v


attempt("boil it dry, then keep heating", _boil_dry,
        lambda v: (v.run(150.0), v.run(400.0)))
attempt("... and keep heating a lot longer", _boil_dry,
        lambda v: (v.run(150.0), v.run(4000.0)))


def _all_the_solvents():
    v = flask(SOLVENT_NET, volume=2.0, kla=1.0)
    v.charge({WATER: 10.0, ETOH: 3.0, TOLUENE: 2.0, HEXANE: 2.0, DCM: 2.0})
    v.fill_headspace_with_air()
    return v


attempt("mix five arbitrary solvents", _all_the_solvents, lambda v: v.run(600.0))


def _acid_into_base():
    v = flask(IONIC_NET, volume=2.0, kla=0.0, k_diss=0.0)
    v.charge({WATER: 55.0, OH: 0.5, NA: 0.5})
    v.fill_headspace({"N#N": 1.0})
    return v


def _quench_it(v):
    v.run(60.0)
    v.charge({SULFURIC: 0.5})            # a strong acid, all at once
    v.run(600.0)


attempt("add 0.5 mol H2SO4 to 0.5 mol NaOH", _acid_into_base, _quench_it)


def _cool_it_hard():
    v = flask(SOLVENT_NET, volume=1.0, T=298.15, T_env=100.0, UA=20.0, kla=1.0)
    v.charge({WATER: 30.0})
    v.fill_headspace_with_air()
    return v


attempt("cool water to 100 K", _cool_it_hard, lambda v: v.run(3600.0))


def _overfill():
    v = flask(SOLVENT_NET, volume=0.1, kla=1.0)
    v.charge({WATER: 20.0})              # ~360 mL into a 100 mL flask
    return v


attempt("charge 360 mL into a 100 mL flask", _overfill, lambda v: v.run(600.0))


def _sealed_hot():
    v = flask(SOLVENT_NET, volume=0.5, T=298.15, UA=0.5, Q_input=80.0, k_vent=0.0)
    v.charge({ETOH: 3.0})
    v.fill_headspace({"N#N": 1.0})
    return v


attempt("heat a SEALED flask (vent shut)", _sealed_hot, lambda v: v.run(1200.0))


def _retry_the_experiment():
    v = flask(SOLVENT_NET, volume=1.0, kla=1.0)
    v.charge({WATER: 20.0})
    v.run(60.0)
    v.reset()                            # "let me try that again"
    v.charge({ETOH: 5.0})
    return v


attempt("reset and retry in the same flask", _retry_the_experiment,
        lambda v: v.run(600.0))

# ---------------------------------------------------------------------------
rule("PANEL 2 -- DEGENERATE STATES, which a game reaches constantly")
# ---------------------------------------------------------------------------

attempt("an empty vessel", lambda: flask(SOLVENT_NET), lambda v: v.run(3600.0))
attempt("gas only, no liquid",
        lambda: flask(SOLVENT_NET).fill_headspace_with_air(),
        lambda v: v.run(3600.0))


def _solid_only():
    v = flask(IONIC_NET, k_diss=0.05)
    v.charge({BENZOIC: 0.05}, phase="solid")
    return v


attempt("solid only, no solvent", _solid_only, lambda v: v.run(3600.0))


def _at_rest():
    v = flask(SOLVENT_NET, kla=1.0)
    v.charge({WATER: 20.0})
    v.fill_headspace_with_air()
    v.run(2000.0)                        # settle it
    return v


attempt("a vessel at rest (the common case)", _at_rest, lambda v: v.run(3600.0))


def _no_headspace_sealed():
    v = flask(SOLVENT_NET, kla=0.0, k_vent=0.0)
    v.charge({WATER: 20.0, ETOH: 2.0})
    return v


attempt("kla=0 AND an empty headspace", _no_headspace_sealed,
        lambda v: v.run(3600.0))


def _trace_second_layer():
    """A layer sitting between DRYOUT_MOLES and LAYER_EPS -- the band that made
    the acidification unsolvable once, and which the two gates now avoid."""
    v = flask(SOLVENT_NET, volume=1.0, kla=0.0, k_lle=0.5)
    v.charge({WATER: 30.0})
    v.charge({TOLUENE: 0.5 * (DRYOUT_MOLES + LAYER_EPS)}, phase="liquid2")
    return v


attempt("a second layer in the DRYOUT..LAYER_EPS band", _trace_second_layer,
        lambda v: v.run(600.0))


def _vacuum():
    v = flask(SOLVENT_NET, volume=1.0, kla=5.0, k_vent=1.0e3, P_ambient=0.001)
    v.charge({ETOH: 2.0})
    return v


attempt("pull a vacuum on a volatile", _vacuum, lambda v: v.run(600.0))

# ---------------------------------------------------------------------------
rule("PANEL 3 -- THE DEFAULTS, driven by somebody who did not read the docs")
# ---------------------------------------------------------------------------


def _default_shaking():
    """The default k_lle is 5.0 mol/s, and the prep's pot needs 0.5 to integrate.
    A player never sets it, so this is what they get."""
    v = flask(IONIC_NET, volume=2.0, T=353.0, T_env=353.0, UA=20.0, kla=5.0,
              k_diss=0.05, k_vent=0.0)
    v.charge({WATER: 55.0, TOLUENE: 0.3, BENZOIC: 0.1, NA: 0.1, OH: 0.1})
    v.fill_headspace_with_air()
    return v


attempt("two layers + salt at the DEFAULT k_lle", _default_shaking,
        lambda v: v.run(1800.0))


def _brine_and_toluene():
    v = flask(IONIC_NET, volume=4.0, kla=0.0, k_diss=0.0, k_vent=0.0)
    v.charge({WATER: 27.7, TOLUENE: 4.7, NA: 1.0, OH: 1.0})
    return v


attempt("saturated-ish brine against toluene", _brine_and_toluene,
        lambda v: v.run(600.0))


def _esterify_open():
    v = flask(ESTER_NET, volume=1.0, T=350.0, T_env=350.0, UA=20.0, kla=5.0)
    v.charge({ACETIC: 3.0, ETOH: 3.0})
    v.fill_headspace_with_air()
    return v


attempt("an ordinary esterification, open", _esterify_open,
        lambda v: v.run(3600.0))

# ---------------------------------------------------------------------------
rule("PANEL 4 -- STATES THAT MUST BE REFUSED, not survived")
# ---------------------------------------------------------------------------


def _nan_charge():
    v = flask(SOLVENT_NET)
    v.charge({WATER: 20.0})
    v._nL[v._index(ETOH)] = float("nan")
    return v


attempt("a NaN in the state vector", _nan_charge, lambda v: v.run(10.0))


def _absurd_temperature():
    v = flask(SOLVENT_NET)
    v.charge({WATER: 20.0})
    v.T = 20000.0
    return v


attempt("T = 20000 K", _absurd_temperature, lambda v: v.run(10.0))


def _unknown_species():
    v = flask(SOLVENT_NET)
    v.charge({"CCCCCCCCCCCCCCCC": 1.0})
    return v


attempt("charge a species not in the network", _unknown_species,
        lambda v: v.run(10.0))

# ---------------------------------------------------------------------------
print(f"\n  {'situation':>42s}  {'verdict':>8s}  what happened")
print("  " + "-" * 76)
for label, verdict, note in ROWS:
    print(f"  {label:>42s}  {verdict:>8s}  {note}")

counts: dict[str, int] = {}
for _, verdict, _ in ROWS:
    counts[verdict] = counts.get(verdict, 0) + 1
print("\n  " + "   ".join(f"{k}: {v}" for k, v in sorted(counts.items())))

bad = [r for r in ROWS if r[1] in ("WRONG", "UNCLEAR")]
if bad:
    print("\n  THE RULE IS BROKEN BY:")
    for label, verdict, note in bad:
        print(f"    {verdict:>8s}  {label}: {note}")
else:
    print("\n  Every situation above either worked or refused with a reason.")

print("""
==============================================================================
WHAT THIS PANEL IS FOR, AND WHAT IT IS NOT
==============================================================================

  IT IS NOT AN ACCURACY HARNESS. Every other validation script here asks whether
  a number is right. This one asks whether an unplanned-for state is handled, and
  the two questions have different answers: "cool water to 100 K" produces a
  physically meaningless trajectory and still has to not crash, because a player
  is entitled to try it and be told what happened.

  THE FOUR VERDICTS ARE ORDERED BY HOW BAD THEY ARE, and WRONG is much worse than
  UNCLEAR. A crash is visible; a plausible number is not. The unclipped Born term
  was the case that made the point -- BDF reported SUCCESS and returned chloride
  at plus and minus 3.07e9 mol as a cancelling dipole, and the non-negative
  projection, doing exactly its job, turned that into a state nothing downstream
  could tell from a real one. Hence check_raw_solution, and hence the raw-state
  test in this harness's own sanity function.

  RUN THIS BEFORE PUTTING A UI IN FRONT OF THE ENGINE, not after. A robustness bug
  that arrives as a UI bug report has two layers to debug instead of one.""")

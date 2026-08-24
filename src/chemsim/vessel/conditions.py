"""Layer 5 -- "wait until": a bench instruction as a root of the state vector.

Every duration in this project used to be a number of seconds, and a real
procedure does not have any. "Reflux until the head stabilises", "cool until
crystals appear", "distil until the pot reaches 110 C", "stir until it all
dissolves" -- none of those is a time, and a recipe written against fixed
durations encodes the wrong shape into every screen built on top of it.

The mechanism is scipy's: ``solve_ivp`` locates a root of a scalar function of
state to solver tolerance, independently of the caller's step size, so **the
instant becomes DISCOVERED rather than declared** and the determinism guarantee
extends rather than breaks. Layer 4 does the driving (``step_until``); this module
is the vocabulary, and it exists at Layer 5 because a root function over
``[nL1 | nL2 | nG | nS | T]`` needs to know which index is benzoic acid.

## The sign convention, which is the whole contract

    f(state) < 0   not yet
    f(state) >= 0  satisfied

Uniform across every condition, upward crossings only. That is not cosmetic: with
a direction flag per condition there are two ways to write each one and one of them
is silently backwards, and "is it already true?" stops being a single comparison.

## ⚠ WHAT IS NOT OFFERED, AND WHY -- see ``validation/wait_conditions.py``

Each condition below was sampled along a real trajectory BEFORE it was
implemented, which is the discipline that killed crystal occlusion for the cost of
an afternoon. Three findings shaped this list:

* **A DERIVATIVE APPROACHING ZERO IS NOT A ROOT.** "The temperature has
  stabilised" is dT/dt -> 0, and it gets there asymptotically -- it is approached
  and never crossed, so ``dT/dt == 0`` would wait forever. What IS a root is a
  TOLERANCE on the derivative: "the thermometer has stopped moving", which is what
  a chemist actually means and is a number a player can be given. Hence
  ``temperature_steady(rate)`` takes the rate and there is no zero-derivative
  form.
* **AN AMOUNT THAT STARTS AT EXACTLY ZERO NEEDS A THRESHOLD ABOVE THE SOLVER'S
  OWN TOLERANCE.** "Crystals appear" is nS leaving zero, not crossing it, and at
  1e-9 mol the crossing is inside atol. A micromole is three orders of magnitude
  clear of that and still far below anything a bench could see -- the same
  argument the Born ceiling rests on. ``SOLID_VISIBLE`` is that default and it is
  a resolution limit, not a claim about nucleation.
* **A CONDITION ALREADY TRUE IS NOT A ROOT EITHER**, because scipy locates sign
  changes. Layer 4 checks for it before integrating and reports it as such, so
  "wait until it is above 300 K" asked of a flask at 340 K returns immediately
  instead of hanging.
* **AND A RATE TOLERANCE FIRES ON THE FIRST TRANSIENT, NOT ON THE PLATEAU** -- the
  one this arc's own probe was too coarse to see, and it was caught by a test
  instead. A flask whose headspace has just been filled evaporates hard for a
  moment: dT/dt starts at -24 K/s, crosses zero inside a second, and only then
  climbs to its steady +0.096 K/s. So ``temperature_steady`` on its own fires at
  298 K rather than at the boil. Say what you meant instead -- ``boils()`` first,
  ``temperature_steady()`` after -- which is what a chemist does anyway. See
  ``temperature_steady``.

There is no nucleation barrier in this project, so "crystals appear" means the
solubility limit was passed and the dissolution term ran backwards. A metastable
solution would not crop at the bench and will here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from chemsim.constants import R_L_BAR

# Moles of solid at which a crop counts as visible. ⚠ A RESOLUTION LIMIT, not a
# nucleation threshold: the binding constraint is that the crossing be resolvable
# above the solver's own 1e-9 atol, and a micromole is three decades clear of it
# while being far below the milligram a bench could see. Measured in
# ``validation/wait_conditions.py`` -- at 1e-9 the root sits inside the tolerance
# and at exactly 0 there is no crossing at all, only a departure.
SOLID_VISIBLE = 1.0e-6

# K/s below which a temperature counts as steady. 0.01 K/s is 0.6 K per minute --
# roughly the point at which a thermometer read by eye stops moving.
STEADY_RATE = 0.01

KINDS = frozenset({
    "temperature_above",
    "temperature_below",
    "temperature_steady",
    "boiling",
    "solid_at_least",
    "solid_at_most",
    "dissolved_at_least",
    "dissolved_at_most",
    "pH_below",
    "pH_above",
    "pressure_above",
})


@dataclass(frozen=True)
class Condition:
    """One "wait until" clause, as plain serializable data.

    A dataclass of strings and floats rather than a closure, for the same reason a
    ``Scenario`` stores templates rather than a built network: it has to survive a
    save file. ``Vessel.root_function`` is what turns it into the callable Layer 4
    integrates against.
    """

    kind: str
    value: float = 0.0
    species: str = ""

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(
                f"unknown condition {self.kind!r}; expected one of {sorted(KINDS)}"
            )
        needs_species = self.kind.startswith(("solid_", "dissolved_"))
        if needs_species and not self.species:
            raise ValueError(f"{self.kind!r} needs a species")
        if not needs_species and self.species:
            raise ValueError(f"{self.kind!r} takes no species, got {self.species!r}")
        if self.kind == "temperature_steady" and self.value <= 0.0:
            raise ValueError(
                "temperature_steady needs a POSITIVE rate tolerance in K/s -- "
                "dT/dt approaches zero asymptotically and never crosses it, so "
                "'the temperature stopped changing' has to be a tolerance rather "
                "than an equality. See validation/wait_conditions.py."
            )

    def describe(self) -> str:
        what = f" {self.species}" if self.species else ""
        return f"{self.kind}{what} = {self.value:g}"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "value": self.value, "species": self.species}

    @classmethod
    def from_dict(cls, d: dict) -> Condition:
        return cls(
            kind=str(d["kind"]),
            value=float(d.get("value", 0.0)),
            species=str(d.get("species", "")),
        )


# ---------------------------------------------------------------------------
# The vocabulary. Free functions rather than classmethods so a protocol reads
# like a procedure: ``until(reaches(353.0), crystals(ACID))``.
# ---------------------------------------------------------------------------


def reaches(kelvin: float) -> Condition:
    """Until the contents get UP to a temperature -- 'distil until the pot hits X'."""
    return Condition("temperature_above", kelvin)


def cools_to(kelvin: float) -> Condition:
    """Until the contents come DOWN to a temperature."""
    return Condition("temperature_below", kelvin)


def temperature_steady(rate: float = STEADY_RATE) -> Condition:
    """Until |dT/dt| falls below ``rate`` K/s -- 'until the head stabilises'.

    ⚠ A TOLERANCE AND NOT AN EQUALITY, deliberately -- see the module docstring.

    ⚠ **AND IT FIRES AT THE FIRST INSTANT THE RATE IS SMALL, WHICH MAY BE A
    TRANSIENT RATHER THAN THE PLATEAU.** Measured, not feared: a flask whose
    headspace has just been filled with air evaporates hard for a moment, so its
    dT/dt starts at **-24 K/s**, swings through zero within a second, and settles at
    +0.096 K/s on its way to the boil. A bare ``temperature_steady(0.01)`` therefore
    fires in that first second, at 297.8 K, and reports -- correctly -- that the
    temperature was momentarily steady.

    That is not a defect in the root; it is what "the thermometer has stopped
    moving" means if you start watching at the wrong moment. The fix is to say what
    you meant, and it is already expressible: reach the interesting regime first and
    then watch for steadiness --

        v.wait_until(boils(), timeout=7200.0)
        v.wait_until(temperature_steady(0.01), timeout=3600.0)

    -- which is also what a chemist does. Combining the two into one race would NOT
    work, because a race fires on whichever comes first.

    ⚠ **AND IN A RIG THIS IS THE ONE CONDITION THAT NEEDS THE COUPLED RHS**, because
    it is the only one that reads a DERIVATIVE rather than the state. The version
    compiled below is the OWNER VESSEL's dT/dt and knows nothing about the edges;
    on a still head, where nearly all the heat arrives through the vapour edge, that
    is a different question with a different answer -- a column at steady total
    reflux times out on it. ``Rig.wait_until`` builds this kind against the rig's
    own RHS for exactly that reason; the lifted form here stays correct for a lone
    flask, which is what it is for.
    """
    return Condition("temperature_steady", rate)


def boils() -> Condition:
    """Until the equilibrium vapour pressure reaches ambient -- 'until it refluxes'.

    The same expression the RHS evaporates against, so the condition and the
    dynamics cannot disagree about what boiling is. A flask boiled dry does not
    satisfy it, however hot: there is no liquid left to have a vapour pressure.
    """
    return Condition("boiling")


def crystals(species: str, moles: float = SOLID_VISIBLE) -> Condition:
    """Until a crop appears -- 'cool until crystals appear'."""
    return Condition("solid_at_least", moles, species)


def dissolves(species: str, moles: float = SOLID_VISIBLE) -> Condition:
    """Until the last of a solid goes into solution -- 'stir until it dissolves'."""
    return Condition("solid_at_most", moles, species)


def consumed(species: str, moles: float) -> Condition:
    """Until a dissolved species falls to ``moles`` -- 'until the ester is gone'."""
    return Condition("dissolved_at_most", moles, species)


def accumulates(species: str, moles: float) -> Condition:
    """Until a dissolved species reaches ``moles``."""
    return Condition("dissolved_at_least", moles, species)


def acidic_to(pH: float) -> Condition:
    """Until the aqueous layer falls to a pH -- 'acidify until pH 2'."""
    return Condition("pH_below", pH)


def basic_to(pH: float) -> Condition:
    """Until the aqueous layer rises to a pH."""
    return Condition("pH_above", pH)


def pressure_above(bar: float) -> Condition:
    """Until the headspace reaches a pressure -- 'until it starts to blow off'."""
    return Condition("pressure_above", bar)


# ---------------------------------------------------------------------------
# compilation: Condition -> f(t, y) -> float
# ---------------------------------------------------------------------------


def compile_condition(condition: Condition, vessel) -> callable:
    """Turn a ``Condition`` into the root function Layer 4 integrates against.

    Takes the vessel rather than living on it so that the sign convention and the
    per-kind arithmetic are stated once, in one readable block, instead of being
    spread over a method per condition. Everything it closes over is an index or a
    scalar; the returned function sees only the state vector.

    ⚠ EVERY ONE OF THESE IS READ OFF THE STATE VECTOR THE SOLVER IS TRYING, never
    off the vessel's own attributes. A root function that consulted ``vessel.T``
    would return the same value at every trial point and the root solve would be
    measuring nothing.
    """
    integ = vessel.integrator
    n = integ.n
    kind, level = condition.kind, float(condition.value)

    if kind == "temperature_above":
        return lambda t, y: float(y[-1]) - level
    if kind == "temperature_below":
        return lambda t, y: level - float(y[-1])

    if kind == "temperature_steady":
        # ⚠ ONE RHS CALL PER EVALUATION, and scipy evaluates an event at every
        # accepted step. That is the cost of asking about a derivative, it is
        # bounded (one call against the dozens a Jacobian costs), and the
        # alternative -- differencing the temperature across steps -- would make
        # the answer depend on the step size, which is the entire thing this
        # module exists to avoid.
        #
        # abs() has a kink at dT/dt = 0, which is INSIDE the satisfied region and
        # so is never where the root is located.
        # Composition-dependent permittivity (no ``y0``), unlike the RHS the run
        # itself integrates -- see FREEZE_LAYER_PERMITTIVITY. The two therefore
        # disagree about dT/dt in about its third decimal place, which moves a
        # located instant by about the same amount the root solve's own tolerance
        # does. Threading the frozen block through would tie the vocabulary to the
        # solver's internals to buy nothing measurable.
        rhs = integ.make_rhs()
        return lambda t, y: level - abs(float(rhs(t, y)[-1]))

    if kind == "boiling":
        from chemsim.numerics.vessel_integrator import DRYOUT_MOLES

        def boiling(t, y):
            nL1, nL2 = y[:n], y[n : 2 * n]
            if float(np.maximum(nL1, 0.0).sum() + np.maximum(nL2, 0.0).sum()) <= (
                DRYOUT_MOLES
            ):
                return -1.0        # a dry flask is not boiling, however hot
            # Condensables only -- dissolved air would otherwise make this true
            # at room temperature. See ``VesselIntegrator.volatile_pressure``.
            return integ.volatile_pressure(
                np.maximum(nL1, 0.0), float(y[-1]), np.maximum(nL2, 0.0)
            ) - vessel.P_ambient

        return boiling

    if kind == "pressure_above":
        def pressure(t, y):
            T = float(y[-1])
            nG = np.maximum(y[2 * n : 3 * n], 0.0)
            v_mol = np.maximum(_vmol(integ, T), 0.0)
            held = np.maximum(y[:n], 0.0) + np.maximum(y[n : 2 * n], 0.0) + (
                np.maximum(y[3 * n : 4 * n], 0.0)
            )
            V_G = max(vessel.volume - float(held @ v_mol), 1.0e-9)
            return float(nG.sum()) * R_L_BAR * T / V_G - level

        return pressure

    if kind in ("pH_below", "pH_above"):
        idx = vessel._index("[OH3+]")
        water = vessel._index("O")
        sign = -1.0 if kind == "pH_below" else 1.0

        def pH(t, y):
            # The aqueous layer is whichever holds more water, exactly as
            # ``Vessel.pH`` decides -- an electrode goes in the water, and
            # diluting a proton count by an organic layer it was never in would be
            # arithmetic rather than chemistry.
            L1 = np.maximum(y[:n], 0.0)
            L2 = np.maximum(y[n : 2 * n], 0.0)
            n1, n2 = float(L1.sum()), float(L2.sum())
            x1 = L1[water] / n1 if n1 > 0.0 else 0.0
            x2 = L2[water] / n2 if n2 > 0.0 else 0.0
            block = L2 if (n2 > 0.0 and x2 > x1) else L1
            v_mol = np.maximum(_vmol(integ, float(y[-1])), 0.0)
            V_L = float(block @ v_mol)
            if V_L <= 0.0 or block[idx] <= 0.0:
                return -1.0        # no aqueous phase, or no protons in it
            value = -float(np.log10(block[idx] / V_L))
            return sign * (value - level)

        return pH

    i = vessel._index(condition.species)
    if kind == "solid_at_least":
        return lambda t, y: float(y[3 * n + i]) - level
    if kind == "solid_at_most":
        return lambda t, y: level - float(y[3 * n + i])
    if kind == "dissolved_at_least":
        return lambda t, y: float(y[i]) + float(y[n + i]) - level
    if kind == "dissolved_at_most":
        return lambda t, y: level - float(y[i]) - float(y[n + i])

    raise ValueError(f"no root function for condition kind {kind!r}")


def _vmol(integ, T: float) -> np.ndarray:
    from chemsim.numerics.vessel_integrator import _poly

    return _poly(integ.ph.v_liq, T)

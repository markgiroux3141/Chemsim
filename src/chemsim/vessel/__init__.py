"""Layer 5 -- vessel: phases, energy balance, pressure and boundary fluxes.

Assembles molecular property estimates into the numeric arrays Layer 4 integrates,
and reports the result back in chemist's terms. See ``vessel.Vessel``.
"""

from chemsim.vessel.conditions import (
    SOLID_VISIBLE,
    STEADY_RATE,
    Condition,
    accumulates,
    acidic_to,
    basic_to,
    boils,
    compile_condition,
    consumed,
    cools_to,
    crystals,
    dissolves,
    pressure_above,
    reaches,
    temperature_steady,
)
from chemsim.vessel.rig import Connection, Rig
from chemsim.vessel.vessel import (
    SPHERE_SHAPE_FACTOR,
    FiltrationResult,
    TransferLosses,
    Vessel,
    VesselState,
    WaitOutcome,
    build_phase_arrays,
    infinite_dilution_reference,
)

__all__ = [
    "SOLID_VISIBLE",
    "SPHERE_SHAPE_FACTOR",
    "STEADY_RATE",
    "Condition",
    "Connection",
    "FiltrationResult",
    "Rig",
    "TransferLosses",
    "Vessel",
    "VesselState",
    "WaitOutcome",
    "accumulates",
    "acidic_to",
    "basic_to",
    "boils",
    "build_phase_arrays",
    "compile_condition",
    "consumed",
    "cools_to",
    "crystals",
    "dissolves",
    "infinite_dilution_reference",
    "pressure_above",
    "reaches",
    "temperature_steady",
]

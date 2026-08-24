"""Layer 6 -- player events: the only way the outside world touches the simulation.

An event is a timestamped, serializable intention: "at t=300 s, pour 40% of flask
A into flask B". Nothing else may mutate a vessel. That single rule is what buys
determinism -- a run is fully described by (scenario, event list), so a save file
does not need to capture the solver's internal state, and replaying the same
events on the same scenario reproduces the same trajectory exactly.

Events are applied at step boundaries, never inside an integration. A player
action is instantaneous relative to the chemistry; interleaving it with the
solver's internal timesteps would make the outcome depend on the solver's
adaptive step size, which is precisely the kind of non-determinism this design
exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class Event:
    """A scheduled player action.

    Ordering is by (t, seq) so that events scheduled for the same instant apply
    in the order they were submitted -- ties must not depend on dict or set
    iteration, or replay stops being deterministic.
    """

    t: float
    seq: int = field(compare=True, default=0)
    kind: str = field(compare=False, default="")
    vessel: str = field(compare=False, default="")
    payload: dict[str, Any] = field(compare=False, default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "t": self.t,
            "seq": self.seq,
            "kind": self.kind,
            "vessel": self.vessel,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Event:
        return cls(
            t=float(d["t"]),
            seq=int(d.get("seq", 0)),
            kind=str(d["kind"]),
            vessel=str(d.get("vessel", "")),
            payload=dict(d.get("payload", {})),
        )


# The verbs a player has. Kept as plain strings so a save file stays readable and
# a frontend can construct them without importing anything from the engine.
CHARGE = "charge"            # payload: {amounts: {smiles: mol}, phase: "liquid"}
SET_HEAT = "set_heat"        # payload: {watts: float}
SET_ENVIRONMENT = "set_env"  # payload: {T_env: float}
SET_VENT = "set_vent"        # payload: {k_vent: float}  -- 0.0 seals the vessel
SET_STIRRING = "set_stir"    # payload: {kla: float}
# payload: {k_lle: float} -- how hard the separatory funnel is shaken. Distinct
# from SET_STIRRING, which is liquid<->vapour: you can stir a flask vigorously
# under a condenser without ever shaking two layers together.
SET_SHAKING = "set_shake"
# payload: {to: vessel_id, fraction: float, phase: str}. ``phase`` may be
# "liquid" (both layers), "lower"/"upper" (ONE layer -- a separatory funnel,
# with which is which decided by the computed densities), "gas" or "solid".
TRANSFER = "transfer"
# payload: {filtrate: vessel_id|None, cake: vessel_id|None,
#           porosity: float, passthrough: float}
# ``porosity`` is the cake's VOID FRACTION, not a fraction of the liquor -- see
# ``Vessel.filter_into``. The old ``retention`` key is refused, loudly.
FILTER = "filter"
# payload: {composition: {smiles: mole fraction}} -- defaults to air. Fills the
# headspace to ambient pressure. A verb of its own because the AMOUNT depends on
# the headspace volume at the moment it happens, which a fixed CHARGE cannot
# express: the same "open the flask to the room" means different moles once
# there is liquid in it.
FILL_HEADSPACE = "fill_headspace"

# payload: {edge: int, to: vessel_id, end: "b"} -- RE-POINT one end of an
# apparatus edge at a different vessel.
#
# ⚠ THIS IS THE VERB THAT MAKES A FRACTIONAL DISTILLATION SAYABLE, and its name
# is the player's word for it. "Collect the fraction boiling between 351 and
# 355 K" was not merely unimplemented before: there was no way to stop and change
# the receiver, so everything came over into one pot and the enrichment a still
# had genuinely achieved WASHED BACK OUT (measured: head mole fraction 0.655 at
# 200 s, back to 0.500 by 1200 s).
#
# ⚠ It re-points an edge at a vessel the SCENARIO ALREADY DECLARES rather than
# creating one, and that is deliberate. A world is (scenario, events, script);
# a verb that conjures a vessel would put part of the apparatus outside the
# scenario, which is the very thing M2 set out to fix. Declare receiver_1..n as
# glassware on the bench and swap between them, which is also what a chemist
# does.
SWAP_RECEIVER = "swap_receiver"
# payload: {edge: int, k: float} -- open or close a tap. Zero closes it.
# Distinct from SWAP_RECEIVER because a dropping funnel is throttled, not moved.
SET_EDGE = "set_edge"

ALL_KINDS = frozenset({
    CHARGE, SET_HEAT, SET_ENVIRONMENT, SET_VENT, SET_STIRRING, SET_SHAKING,
    TRANSFER, FILTER, FILL_HEADSPACE, SWAP_RECEIVER, SET_EDGE,
})

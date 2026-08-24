"""Layer 7 -- a user interface for the engine. Nothing below this layer imports it.

Two halves, deliberately separable:

``session``   the engine-facing half, with no widgets in it. A ``World`` driven
              from a worker thread, chunked so that an operation renders as IN
              PROGRESS rather than blocking, published as immutable snapshots.
              This is the half that is tested.
``app``       the Tkinter view. Polls the session and produces commands, and is
              allowed to know nothing else about the engine.

⚠ The split is not tidiness. The interesting behaviour of a frontend for THIS
engine is entirely in the first half -- cost is concentrated in stiff transients,
so what matters is the threading and the chunking, and neither is testable through
a GUI toolkit.
"""

from chemsim.ui.session import (
    DEFAULT_CHUNK,
    Do,
    Load,
    Reset,
    Session,
    Snapshot,
    Step,
    VesselView,
    WaitUntil,
)

__all__ = [
    "Session", "Snapshot", "VesselView",
    "Do", "Step", "WaitUntil", "Reset", "Load", "DEFAULT_CHUNK",
]

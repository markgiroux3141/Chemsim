"""Cap the BLAS/OpenMP thread pools at one thread -- R2.

Measured on identical work (MILESTONES.md section R2): uncapped scipy/BLAS
spread over **7.21 cores**; capped it used **0.99 cores and was FASTER** --
5.9 s against 10.1 s. There is no trade-off: this engine's arrays are small
enough that threading is pure overhead, and *"single process" is not "one
core"* -- sample it rather than assume.

And the cap is NUMERICALLY NEUTRAL, measured rather than assumed: R1 ran the
tolerance audit capped twice and uncapped once and all three outputs were
identical to the digit (NEXT_PROMPT.md, the ``workshop`` chase).

⚠ WHO CALLS THIS, AND WHO MUST NOT. Entry points call it -- the UI's
``__main__`` (a worker thread would otherwise spread a player's whole machine
over one flask), the long validation harnesses, the test suite's ``conftest``.
``chemsim/__init__`` must NOT: a library that silently reconfigures BLAS for
whoever imports it is rude, and an embedder may have real work for their own
pools. A process decides this for itself, once, at its own front door.

⚠ THE MECHANISM IS AN ENVIRONMENT VARIABLE, SO ORDER MATTERS. OpenBLAS, MKL
and OpenMP size their pools when numpy first loads them; a variable set after
that is a no-op. Call this before anything that imports numpy -- which for
most of this project means before importing anything under ``chemsim`` except
this module (``chemsim/__init__`` is import-light by design and stays so).
"""

from __future__ import annotations

import os
import sys

# The four knobs the R2 measurement used, and the only four it vouches for.
_VARS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def cap_blas_threads() -> bool:
    """Default the BLAS/OpenMP pools to one thread. Call BEFORE numpy loads.

    ``setdefault`` on purpose: a thread count somebody set by hand is a
    decision rather than an accident, and it wins over this default.

    Returns False when numpy was already imported, in which case anything set
    here arrived too late to size a pool this process will use. The caller
    loses nothing but speed -- the cap is measured to be numerically neutral
    -- which is why being late is a return value and not an exception.
    """
    late = "numpy" in sys.modules
    for var in _VARS:
        os.environ.setdefault(var, "1")
    return not late

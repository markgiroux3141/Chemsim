"""``python -m chemsim.ui`` -- open the window.

An optional example key picks what is already loaded: ``flask``, ``boil``,
``ester``, ``prep`` or ``bench``.

⚠ ``bench`` is the playable one (P4): a flask holding whatever was taken off
``data/catalog/shelf.psv``, explored ONE GENERATION deep, with every template in
the project loaded. The Bench tab re-picks the shelf and REACT FURTHER on the
Drive tab raises the bound.
"""

from __future__ import annotations

import sys

from chemsim.threads import cap_blas_threads

# R2: BEFORE ``chemsim.ui.app`` -- importing it loads numpy, which is when the
# pools are sized. Here and not in ``chemsim/__init__``: an entry point may
# decide this for its own process; a library import may not. Measured: 7.21
# cores -> 0.99, and FASTER (5.9 s vs 10.1 s on identical work).
cap_blas_threads()

from chemsim.ui.app import launch  # noqa: E402

if __name__ == "__main__":
    launch(sys.argv[1] if len(sys.argv) > 1 else "flask")

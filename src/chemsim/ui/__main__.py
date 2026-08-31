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

from chemsim.ui.app import launch

if __name__ == "__main__":
    launch(sys.argv[1] if len(sys.argv) > 1 else "flask")

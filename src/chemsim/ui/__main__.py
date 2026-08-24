"""``python -m chemsim.ui`` -- open the window.

An optional example key picks what is already loaded: ``flask``, ``boil``,
``ester`` or ``prep``.
"""

from __future__ import annotations

import sys

from chemsim.ui.app import launch

if __name__ == "__main__":
    launch(sys.argv[1] if len(sys.argv) > 1 else "flask")

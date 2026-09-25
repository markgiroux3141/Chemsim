"""Profile one import on a CI runner and publish the costliest calls as notices.

`import build_playable` is 46 s on the user's machine and over 900 s on a
windows runner, and a session cannot read a runner's log without a token. So
the profile goes out as annotations: `python tools/ci_status.py --slowest`.
"""

import contextlib
import cProfile
import io
import os
import pstats
import sys
import time

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("src", "tools", "validation"):
    sys.path.insert(0, os.path.join(root, sub))

module = sys.argv[1]
prof = cProfile.Profile()
t0 = time.perf_counter()
with contextlib.redirect_stdout(io.StringIO()):
    prof.enable()
    __import__(module)
    prof.disable()
total = time.perf_counter() - t0
print(f"::notice title=import {module}::{total:.0f} s on this runner")
stats = pstats.Stats(prof)
rows = sorted(stats.stats.items(), key=lambda kv: -kv[1][2])[:9]  # by tottime
for (path, line, func), (_cc, calls, tottime, cumtime, _) in rows:
    where = f"{os.path.basename(path)}:{line} {func}"
    print(f"::notice title=self time::{tottime:.0f} s self, {cumtime:.0f} s cum, "
          f"{calls} calls -- {where}")

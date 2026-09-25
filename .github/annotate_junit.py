"""Publish each failing test id, and the slowest modules, as job annotations.

Annotations are readable through the public API without a token, which is what
lets ``tools/ci_status.py`` name the failing tests. GitHub keeps at most ten
error annotations per step, so the first ten are named and the rest counted.
"""

import os
import sys
import xml.etree.ElementTree as ET

if not os.path.exists(sys.argv[1]) or not os.path.getsize(sys.argv[1]):
    print("::error title=pytest::no junit report: the run died before writing one")
    sys.exit(0)

failed = []
seconds: dict[str, float] = {}
for case in ET.parse(sys.argv[1]).getroot().iter("testcase"):
    module = (case.get("classname") or "?").split(".")[-1]
    seconds[module] = seconds.get(module, 0.0) + float(case.get("time") or 0.0)
    for bad in list(case.findall("failure")) + list(case.findall("error")):
        test = f"{case.get('classname')}::{case.get('name')}"
        first = (bad.get("message") or "").strip().splitlines()[:1]
        failed.append((test, first[0][:200] if first else ""))

for test, why in failed[:9]:
    print(f"::error title={test}::{why or 'failed'}")
if failed:
    print(f"::error title=pytest::{len(failed)} failing test(s)"
          f"{'; the first nine are named' if len(failed) > 9 else ''}")

# The ten slowest modules as notices: the per-module cost a fast subset (T0.4)
# needs, readable without a token.
for module, s in sorted(seconds.items(), key=lambda kv: -kv[1])[:10]:
    print(f"::notice title=slow module::{module} {s:.0f} s")

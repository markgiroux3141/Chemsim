"""Publish each failing test id, and the slowest modules, as job annotations.

Annotations are readable through the public API without a token, which is what
lets ``tools/ci_status.py`` name the failing tests. GitHub keeps at most ten
error annotations per step, so the first ten are named and the rest counted.
"""

import os
import sys
import xml.etree.ElementTree as ET

def unfinished(path: str) -> None:
    """Name what the reportlog saw start and never finish, and what finished last.

    The reportlog is written test by test, so it survives the run being killed;
    junit is written at the end and does not.
    """
    import json

    started, done, order = set(), set(), []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("$report_type") != "TestReport":
                continue
            node = rec.get("nodeid", "?")
            if rec.get("when") == "setup":
                started.add(node)
            if rec.get("when") == "teardown":
                done.add(node)
                order.append((node, rec.get("duration", 0.0)))
    hung = sorted(started - done)
    for node in hung[:9]:
        print(f"::error title=never finished::{node}")
    print(f"::error title=reportlog::{len(done)} tests finished, {len(hung)} started "
          f"and never finished")
    for node, _ in order[-5:]:
        print(f"::notice title=finished last::{node}")


if not os.path.exists(sys.argv[1]) or not os.path.getsize(sys.argv[1]):
    print("::error title=pytest::no junit report: the run died before writing one")
    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        unfinished(sys.argv[2])
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
label = os.environ.get("ANNOTATE_LABEL", "slow module")
for module, s in sorted(seconds.items(), key=lambda kv: -kv[1])[:10]:
    print(f"::notice title={label}::{module} {s:.0f} s")

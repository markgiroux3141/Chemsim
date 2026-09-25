"""Publish each failing test id as a job annotation.

Annotations are readable through the public API without a token, which is what
lets ``tools/ci_status.py`` name the failing tests. GitHub keeps at most ten
error annotations per step, so the first ten are named and the rest counted.
"""

import sys
import xml.etree.ElementTree as ET

failed = []
for case in ET.parse(sys.argv[1]).getroot().iter("testcase"):
    for bad in list(case.findall("failure")) + list(case.findall("error")):
        test = f"{case.get('classname')}::{case.get('name')}"
        first = (bad.get("message") or "").strip().splitlines()[:1]
        failed.append((test, first[0][:200] if first else ""))

for test, why in failed[:9]:
    print(f"::error title={test}::{why or 'failed'}")
if failed:
    print(f"::error title=pytest::{len(failed)} failing test(s)"
          f"{'; the first nine are named' if len(failed) > 9 else ''}")

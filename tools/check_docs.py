"""Enforce the documentation working set, mechanically.

The repo's prose reached 1.5 MB of append-only diary because every cap on it was
a soft one, and a model blows through a soft cap. This is the hard one. It runs
from ``check.ps1`` and exits non-zero.

Two kinds of rule:

* **Caps** apply to the five files of the working set, which are new and small,
  and are absolute. `CLAUDE.md` may not exceed 150 lines; a `CHANGELOG.md` entry
  may not exceed 12.
* **Ratchets** apply to the debt that already exists -- 662 lines of `README.md`,
  1,050 warning glyphs in `src/chemsim` — where an absolute rule would fail on
  the day it was written and be deleted. A ratchet records today's count and
  fails when it *moves*, in either direction: upward because the debt grew,
  downward because a number in this file is now wrong and rule 4 says a number
  that cannot be regenerated is deleted. Paying debt down therefore costs one
  line here, and the budget can never quietly drift.

Run ``python tools/check_docs.py`` to check, ``--fix-budgets`` to rewrite the
ratchet block after a deliberate reduction.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- caps: absolute, on the working set ------------------------------------

LINE_CAPS = {
    "CLAUDE.md": 150,
    "NEXT.md": 120,
    "BACKLOG.md": 300,
}

CHANGELOG_ENTRY_CAP = 12

ROOT_MARKDOWN = {
    "README.md",
    "CLAUDE.md",
    "NEXT.md",
    "BACKLOG.md",
    "CHANGELOG.md",
    "GAME_DESIGN.md",
}

# No warning glyph may appear in anything written under the new rules.
GLYPH_FREE = ("CLAUDE.md", "NEXT.md", "BACKLOG.md", "CHANGELOG.md")

DESIGN_DOC_CAP = 300

# --- ratchets: today's counts, which may not move without an edit here ------

LINE_BUDGETS = {
    # path: (lines today, the target a backlog item is driving it to)
    "README.md": (561, 400),  # C1
    "GAME_DESIGN.md": (1002, 300),  # C3
}

GLYPH_BUDGETS = {
    # tree: glyphs today. C1 drives src/chemsim to under 50.
    "README.md": 0,
    "GAME_DESIGN.md": 74,
    "src/chemsim": 1050,
    "tests": 829,
    "validation": 336,
    "tools": 145,
    "examples": 38,
}

GLYPH = chr(0x26A0)  # by codepoint, so this file is not its own violation
GLYPH_NAME = "warning glyphs"  # never printed literally; the console here is cp1252


def _lines(path: Path) -> int:
    with open(path, encoding="utf-8", newline="") as fh:
        return len(fh.read().splitlines())


def _glyphs(target: Path) -> int:
    if target.is_file():
        paths = [target]
    else:
        paths = sorted(target.rglob("*.py"))
    total = 0
    for path in paths:
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                total += fh.read().count(GLYPH)
        except UnicodeDecodeError:
            continue
    return total


def _changelog_entries(text: str) -> list[tuple[str, int]]:
    """(heading, body line count) for each ``## `` entry."""
    entries: list[tuple[str, int]] = []
    heading: str | None = None
    body = 0
    for line in text.splitlines():
        if line.startswith("## "):
            if heading is not None:
                entries.append((heading, body))
            heading, body = line[3:].strip(), 0
        elif heading is not None and line.strip():
            body += 1
    if heading is not None:
        entries.append((heading, body))
    return entries


def _latest_commit_date() -> str | None:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short"],
            cwd=ROOT, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def check() -> list[str]:
    fail: list[str] = []

    for name, cap in LINE_CAPS.items():
        path = ROOT / name
        if not path.exists():
            fail.append(f"{name} is missing; it is one of the five working files")
            continue
        n = _lines(path)
        if n > cap:
            fail.append(f"{name} is {n} lines, cap is {cap}")

    stray = {p.name for p in ROOT.glob("*.md")} - ROOT_MARKDOWN
    for name in sorted(stray):
        fail.append(
            f"{name} is at the root; the root holds only "
            f"{', '.join(sorted(ROOT_MARKDOWN))}. History goes to docs/history/, "
            f"rationale to docs/design/"
        )

    for name in GLYPH_FREE:
        path = ROOT / name
        if path.exists() and _glyphs(path):
            fail.append(
                f"{name} contains {GLYPH_NAME}; emphasis that is everywhere is nowhere. "
                f"Use NOTE: or WARNING:"
            )

    changelog = ROOT / "CHANGELOG.md"
    if not changelog.exists():
        fail.append("CHANGELOG.md is missing")
    else:
        with open(changelog, encoding="utf-8", newline="") as fh:
            for heading, body in _changelog_entries(fh.read()):
                if body > CHANGELOG_ENTRY_CAP:
                    fail.append(
                        f"CHANGELOG.md entry {heading!r} is {body} lines, "
                        f"cap is {CHANGELOG_ENTRY_CAP}"
                    )

    design = ROOT / "docs" / "design"
    if design.is_dir():
        for path in sorted(design.glob("*.md")):
            n = _lines(path)
            if n > DESIGN_DOC_CAP:
                fail.append(
                    f"docs/design/{path.name} is {n} lines, cap is {DESIGN_DOC_CAP}; "
                    f"one topic per file"
                )

    for name, (budget, target) in LINE_BUDGETS.items():
        path = ROOT / name
        if not path.exists():
            continue
        n = _lines(path)
        if n > budget:
            fail.append(
                f"{name} grew to {n} lines against a budget of {budget} "
                f"(target {target}); it is meant to shrink"
            )
        elif n < budget:
            fail.append(
                f"{name} is down to {n} lines from {budget}: set its budget to "
                f"{n} in tools/check_docs.py (or run --fix-budgets)"
            )

    for name, budget in GLYPH_BUDGETS.items():
        target = ROOT / name
        if not target.exists():
            continue
        n = _glyphs(target)
        if n > budget:
            fail.append(
                f"{name} carries {n} {GLYPH_NAME} against a budget of {budget}; "
                f"new text does not use it"
            )
        elif n < budget:
            fail.append(
                f"{name} is down to {n} {GLYPH_NAME} from {budget}: set its budget to "
                f"{n} in tools/check_docs.py (or run --fix-budgets)"
            )

    nxt = ROOT / "NEXT.md"
    if nxt.exists():
        with open(nxt, encoding="utf-8", newline="") as fh:
            head = fh.read(400)
        stamp = re.search(r"overwritten (\d{4}-\d{2}-\d{2})", head)
        if not stamp:
            fail.append("NEXT.md's first line must read '# NEXT — overwritten YYYY-MM-DD'")
        else:
            latest = _latest_commit_date()
            if latest and stamp.group(1) < latest:
                fail.append(
                    f"NEXT.md was overwritten {stamp.group(1)} and the latest commit "
                    f"is {latest}; it is rewritten every session, not appended to"
                )

    return fail


def fix_budgets() -> int:
    """Rewrite the two budget blocks from today's counts."""
    path = Path(__file__)
    text = path.read_text(encoding="utf-8")
    for name, (_, target) in LINE_BUDGETS.items():
        n = _lines(ROOT / name)
        text = re.sub(
            rf'("{re.escape(name)}"): \(\d+, {target}\)',
            rf'\1: ({n}, {target})',
            text,
        )
    for name in GLYPH_BUDGETS:
        n = _glyphs(ROOT / name)
        text = re.sub(rf'("{re.escape(name)}"): \d+,', rf'\1: {n},', text)
    path.write_text(text, encoding="utf-8")
    print("budgets rewritten from today's counts")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix-budgets", action="store_true",
                        help="rewrite the ratchet block after a deliberate reduction")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if args.fix_budgets:
        return fix_budgets()

    fail = check()
    if fail:
        print(f"check_docs: {len(fail)} problem(s)")
        for line in fail:
            print(f"  - {line}")
        return 1
    print("check_docs: the working set is within its caps")
    return 0


if __name__ == "__main__":
    sys.exit(main())

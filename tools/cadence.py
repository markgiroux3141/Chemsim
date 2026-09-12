"""When each expensive check was last run, and which are due now.

``./check.ps1`` is 70 seconds and runs after every change. The checks that
matter most do not fit in it: the full suite is ~30 minutes on the user's own
machine, ``validation/tolerance_audit.py`` ~10, and the reachability sweep ~35.
The standing rule is to ask before running any of them, which in practice means
they get run when somebody remembers -- and "when somebody remembers" is not a
cadence, it is a hope.

So this file is the ledger, and the point of it is that a session can do a lot
of work cheaply and still know, in one command, what it owes.

TWO KINDS OF ROW, AND ONLY ONE NEEDS BOOKKEEPING
------------------------------------------------
A check that writes a COMMITTED ARTEFACT records itself: the last run is the
commit that last touched its output, and ``git log -1 -- <artefact>`` is the
whole answer. Nothing to stamp, nothing to forget, nothing that can drift from
the truth.

A check that only passes or fails -- the suite, the tolerance audit -- leaves no
trace, so it carries a stamp written by ``--record``. A row that has never been
stamped reports ``never``, and ``never`` is due. It does not report a guess.

THE CLOCK IS COMMITS ON MAIN, NOT DAYS
--------------------------------------
Work in this repo arrives one session and one commit at a time, and a suite is
owed after a number of CHANGES rather than after a number of days. So a row is
due when ``git rev-list --count <last>..HEAD`` reaches its ``due_after``. A
quiet fortnight owes nothing; five sessions in one day owe the suite.

WHAT TO DO WITH AN UNEXPECTED RESULT
------------------------------------
Every row carries an ``on_surprise`` cell naming where the fix goes, because the
moment a 30-minute suite comes back red is the worst moment to be deciding that
from scratch. A red result is RECORDED as red -- ``--record NAME --result fail
--note ...`` -- and the note is what the next session reads first. A failing
check is never stamped green to get a clean board.

    python tools/cadence.py                      # what is due
    python tools/cadence.py --record suite --result pass
    python tools/cadence.py --record suite --result fail --note "test_lle::x"
    python tools/cadence.py --due                # exit 1 if anything is due
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "checks" / "cadence.psv"

COLUMNS = ("check", "command", "minutes", "due_after", "artefact",
           "last_run", "last_commit", "last_result", "note", "on_surprise")


def rows() -> list[dict[str, str]]:
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) != len(COLUMNS):
            raise SystemExit(
                f"{LEDGER.name}: {cells[0]!r} has {len(cells)} cells, "
                f"not {len(COLUMNS)}")
        out.append(dict(zip(COLUMNS, cells)))
    return out


def _git(*args: str) -> str:
    done = subprocess.run(("git", *args), cwd=ROOT, capture_output=True,
                          text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def last_run(row: dict[str, str]) -> tuple[str, str]:
    """(commit, date) of this check's last run, DERIVED where it can be.

    An artefact-backed row is answered by the file it writes, so it cannot go
    stale and cannot be stamped green by hand.
    """
    if row["artefact"]:
        out = _git("log", "-1", "--format=%h %ad", "--date=short", "--",
                   row["artefact"])
        if out:
            commit, _, date = out.partition(" ")
            return commit, date
        return "", ""
    return row["last_commit"], row["last_run"]


def behind(commit: str) -> int | None:
    """Commits on this branch since that one. ``None`` if it is not known."""
    if not commit:
        return None
    out = _git("rev-list", "--count", f"{commit}..HEAD")
    return int(out) if out.isdigit() else None


def status():
    """(row, commit, date, behind, due) for every check, in file order."""
    out = []
    for row in rows():
        commit, date = last_run(row)
        gap = behind(commit)
        due = gap is None or gap >= int(row["due_after"])
        out.append((row, commit, date, gap, due))
    return out


def report(only_due: bool = False) -> int:
    lines, due_now = [], 0
    for row, commit, date, gap, due in status():
        due_now += due
        if only_due and not due:
            continue
        when = f"{date} {commit}" if commit else "never recorded"
        ago = "unknown" if gap is None else f"{gap} commit(s) ago"
        mark = "DUE " if due else "ok  "
        lines.append(f"{mark}{row['check']:<16} {row['minutes']:>3} min  "
                     f"every {row['due_after']:>2}  last: {when} ({ago})"
                     + (f"  [{row['last_result']}]" if row["last_result"]
                        else ""))
        if row["note"]:
            lines.append(f"      note: {row['note']}")
        if due:
            lines.append(f"      run:  {row['command']}")
            lines.append(f"      if it surprises you: {row['on_surprise']}")
    print("\n".join(lines) if lines else "nothing is due")
    print(f"\n{due_now} of {len(rows())} expensive checks are due.")
    return due_now


def record(name: str, result: str, note: str) -> int:
    found = [r for r in rows() if r["check"] == name]
    if not found:
        known = ", ".join(r["check"] for r in rows())
        print(f"no such check: {name}. Known: {known}")
        return 1
    if found[0]["artefact"]:
        print(f"{name} is artefact-backed -- its last run is the commit that "
              f"last touched {found[0]['artefact']}. Commit the artefact "
              "instead of stamping it.")
        return 1
    head = _git("rev-parse", "--short", "HEAD")
    today = datetime.date.today().isoformat()
    text = LEDGER.read_text(encoding="utf-8")
    out = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) == len(COLUMNS) and cells[0] == name:
            cells[5], cells[6], cells[7] = today, head, result
            cells[8] = note.replace("|", "/")
            line = " | ".join(cells)
        out.append(line)
    LEDGER.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{name}: {result} at {head} on {today}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--due", action="store_true",
                    help="list only what is due, and exit 1 if anything is")
    ap.add_argument("--record", metavar="CHECK",
                    help="stamp a check that leaves no artefact")
    ap.add_argument("--result", choices=("pass", "fail"), default="pass")
    ap.add_argument("--note", default="",
                    help="what a failure was, for the next session to read")
    args = ap.parse_args()
    if args.record:
        return record(args.record, args.result, args.note)
    due = report(only_due=args.due)
    return 1 if (args.due and due) else 0


if __name__ == "__main__":
    sys.exit(main())

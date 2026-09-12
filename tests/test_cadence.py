"""The expensive-check ledger: what it can derive, and what it must not invent.

The ledger exists because the three checks that matter most -- the suite, the
tolerance audit, the reachability sweep -- are too slow to run after every
change, so they get run when somebody remembers. These tests pin the two
properties that make the file worth trusting: an artefact-backed row is DERIVED
from git and cannot be stamped by hand, and a row nobody has ever run reports
``never`` rather than a guess, which counts as due.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("src", "tools"):
    _full = os.path.join(_ROOT, _p)
    if _full not in sys.path:
        sys.path.insert(0, _full)

import cadence  # noqa: E402


def test_every_row_has_every_column_and_a_command_to_copy():
    for row in cadence.rows():
        assert row["check"], "a row with no name cannot be recorded"
        assert row["command"].startswith(("python", "pwsh", "./")), row
        assert int(row["minutes"]) > 0
        assert int(row["due_after"]) > 0
        assert row["on_surprise"], (
            f"{row['check']} has no answer for a red result, and the moment "
            "one arrives is the worst moment to work one out")


def test_an_artefact_backed_row_is_derived_and_carries_no_stamp():
    """The point of the artefact column: the sweep needs no bookkeeping, so
    there is nothing to forget and nothing that can drift from the truth."""
    backed = [r for r in cadence.rows() if r["artefact"]]
    assert backed, "at least the reachability sweep writes a committed file"
    for row in backed:
        assert (cadence.ROOT / row["artefact"]).exists(), row
        assert not row["last_run"] and not row["last_commit"], (
            f"{row['check']} is artefact-backed; its stamp columns are ignored "
            "and an ignored value that looks authoritative is worse than none")
        commit, date = cadence.last_run(row)
        assert commit and date, f"git knows nothing about {row['artefact']}"


def test_a_check_never_run_is_due_rather_than_clean():
    """``never`` is not a hash, so the gap is unknown -- and an unknown gap is
    owed. The alternative is a ledger that reads clean because it is empty."""
    never = {"artefact": "", "last_commit": "never", "last_run": "never"}
    assert cadence.behind(cadence.last_run(never)[0]) is None
    assert cadence.behind("") is None


def test_recording_refuses_a_row_that_git_already_answers():
    """Stamping an artefact-backed row would put a second, hand-written answer
    beside the derived one, and two answers is one more than a ledger can have."""
    backed = next(r for r in cadence.rows() if r["artefact"])
    assert cadence.record(backed["check"], "pass", "") == 1
    assert cadence.record("not-a-check", "pass", "") == 1


def test_a_due_row_is_one_whose_commit_gap_reached_its_cadence():
    for row, commit, _date, gap, due in cadence.status():
        if gap is None:
            assert due, f"{row['check']} has no last run and is not due"
        else:
            assert due == (gap >= int(row["due_after"])), row["check"]
            assert commit


@pytest.mark.parametrize("name", ["suite", "tolerance", "reachable"])
def test_the_three_checks_the_repo_keeps_asking_about_are_all_here(name):
    assert name in {r["check"] for r in cadence.rows()}

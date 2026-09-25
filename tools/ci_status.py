"""What CI said about a commit, read from GitHub's public API with no token.

    python tools/ci_status.py                  # HEAD, or the newest commit CI has seen
    python tools/ci_status.py --sha 44fd3a0    # one commit
    python tools/ci_status.py --record         # stamp cadence.psv from a finished run

The full suite is thirty minutes and runs in ``.github/workflows/ci.yml`` on every
push, so a session reads its result instead of asking for the user's machine.
A failing test id is published as a job annotation by
``.github/annotate_junit.py``, which is what lets this name it without a token.

``--record`` writes the ``suite`` row (and ``tolerance``, when the slow workflow
ran on the commit) through ``tools/cadence.py``, pass or fail, with the run's URL
as the note. It refuses a run that has not finished: a stamp says a check ran.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"

# workflow job name -> cadence.psv row it satisfies
RECORDS = {"pytest (full suite)": "suite", "tolerance audit": "tolerance"}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def _repo() -> str:
    url = _git("remote", "get-url", "origin")
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    if not m:
        raise SystemExit(f"origin is not a GitHub remote: {url}")
    return m.group(1)


def _get(path: str):
    req = urllib.request.Request(API + path,
                                 headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as fh:
            return json.load(fh)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"GitHub API {exc.code} on {path}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"GitHub API unreachable: {exc.reason}") from exc


def runs_for(repo: str, sha: str) -> list[dict]:
    return _get(f"/repos/{repo}/actions/runs?head_sha={sha}&per_page=20")["workflow_runs"]


def jobs_for(repo: str, run: dict) -> list[dict]:
    return _get(f"/repos/{repo}/actions/runs/{run['id']}/jobs")["jobs"]


def annotations(repo: str, job: dict, level: str = "failure") -> list[str]:
    rows = _get(f"/repos/{repo}/check-runs/{job['id']}/annotations")
    return [f"{a.get('title') or ''}: {a.get('message') or ''}".strip(": ")
            for a in rows if a.get("annotation_level") == level]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sha", help="commit to report (default HEAD)")
    ap.add_argument("--record", action="store_true",
                    help="stamp tools/cadence.py rows from finished jobs")
    ap.add_argument("--slowest", action="store_true",
                    help="also print the slowest test modules the suite job reported")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    repo = _repo()
    sha = _git("rev-parse", args.sha or "HEAD")
    if args.record and sha != _git("rev-parse", "HEAD"):
        # cadence.py stamps HEAD, so a run on another commit would be misfiled.
        raise SystemExit("--record stamps HEAD; it cannot record another commit's run")
    runs = runs_for(repo, sha)
    if not runs:
        print(f"{sha[:7]}: CI has no run for this commit (not pushed yet, or "
              f"still queued)")
        return 2

    worst = 0
    for run in sorted(runs, key=lambda r: r["name"]):
        for job in jobs_for(repo, run):
            state = job["conclusion"] or job["status"]
            print(f"{sha[:7]}  {run['name']:6s} {job['name']:22s} {state:12s} "
                  f"{job['html_url']}")
            if job["conclusion"] == "failure":
                worst = max(worst, 1)
                for line in annotations(repo, job):
                    print(f"          {line}")
            elif job["conclusion"] is None:
                worst = max(worst, 3)
            if args.slowest and job["conclusion"] is not None:
                for line in annotations(repo, job, level="notice"):
                    print(f"          {line}")
            row = RECORDS.get(job["name"])
            if args.record and row and job["conclusion"] in ("success", "failure"):
                result = "pass" if job["conclusion"] == "success" else "fail"
                subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "cadence.py"),
                     "--record", row, "--result", result,
                     "--note", f"CI {run['name']} at {sha[:7]}: {job['html_url']}"],
                    cwd=ROOT, check=True)
    # 0 green, 1 a job failed, 3 still running
    return worst


if __name__ == "__main__":
    raise SystemExit(main())

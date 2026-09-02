"""R2 -- the BLAS thread cap.

The measurement lives in docs/history/MILESTONES.md (7.21 cores -> 0.99 and faster; and R1's
finding that capping is numerically neutral). What a test can hold is the
CONTRACT: the four variables, the deference to a value somebody already set,
and the ordering rule being loud in the return value rather than silent.

Each check runs in a subprocess because the contract is about process start-up
state -- this pytest process imported numpy long ago, so asserting anything
about it in-process would test the wrong process.
"""

import os
import subprocess
import sys

VARS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)

PROBE = (
    "import os\n"
    "{prelude}"
    "from chemsim.threads import cap_blas_threads\n"
    "ok = cap_blas_threads()\n"
    "vars = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',"
    " 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')\n"
    "print(ok, [os.environ.get(v) for v in vars])\n"
)


def _probe(prelude: str = "", extra_env: dict | None = None) -> str:
    # A fresh environment with the four knobs removed: the box running the
    # suite may itself be capped, and the test is about what the FUNCTION sets.
    env = {k: v for k, v in os.environ.items() if k not in VARS}
    env.update(extra_env or {})
    out = subprocess.run(
        [sys.executable, "-c", PROBE.format(prelude=prelude)],
        capture_output=True, text=True, env=env, check=True,
    )
    return out.stdout.strip()


def test_cap_sets_all_four_variables_and_reports_it_was_in_time():
    assert _probe() == "True ['1', '1', '1', '1']"


def test_a_count_somebody_set_by_hand_wins_over_the_default():
    got = _probe(extra_env={"OMP_NUM_THREADS": "3"})
    assert got == "True ['3', '1', '1', '1']", (
        "setdefault is the contract: an explicit environment value is a "
        "decision and the cap must not overwrite it"
    )


def test_calling_after_numpy_loaded_says_so_in_the_return_value():
    got = _probe(prelude="import numpy\n")
    assert got.startswith("False "), (
        "the pools are sized when numpy first loads; a cap set after that is "
        "a no-op and the function must say so rather than pretend it bound"
    )


def test_the_library_itself_does_not_cap_anything():
    """``chemsim/__init__`` stays import-light and does NOT reconfigure BLAS.

    The rude place was considered and rejected (MILESTONES section R2): a
    library import must not silently reconfigure threading for its importer.
    Entry points opt in; this asserts importing the package does not.
    """
    code = (
        "import os, chemsim\n"
        "vars = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',"
        " 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')\n"
        "print([os.environ.get(v) for v in vars])\n"
    )
    env = {k: v for k, v in os.environ.items() if k not in VARS}
    out = subprocess.run([sys.executable, "-c", code],
                         capture_output=True, text=True, env=env, check=True)
    assert out.stdout.strip() == "[None, None, None, None]"

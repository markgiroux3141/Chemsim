"""Re-run every example at a TIGHT solver tolerance and diff, line by line.

## WHY THIS EXISTS: TWO MILESTONES RUNNING QUOTED A TOLERANCE-LIMITED NUMBER

M6 measured a swept lime kiln converting **39.04%** at the default tolerance and
**13.97%** at rtol 1e-8 -- a factor of 2.6, in a number this project had already
written down as a result. S1 measured a sealed roast closing its sulfur balance to
1.3e-6 at the default and 9.4e-11 tight. In BOTH cases the tight run was several
times FASTER (3.67 s against 19.94 s), because the loose solver was thrashing.

Neither was a bug in the term being built. The cause is the VENT: ``k_vent`` is
1e3 mol/(bar s), so the gas balance is far stiffer than the chemistry feeding it,
and any slow source feeding it inherits the problem. **Nobody had swept the rest
of the examples**, which is what this does.

## ⚠ WHAT "TIGHT" MEANS HERE, AND WHY IT IS NOT AN EDIT TO EVERY EXAMPLE

``VesselIntegrator.run`` and ``RigIntegrator.run`` both default to
``rtol=1e-6, atol=1e-9``. This module rebinds those two DEFAULTS and re-imports
nothing else, so an example that passes its own tolerance explicitly is left
exactly alone -- which is right, because those are the ones already converged
(``lime_cycle``, ``roasting_and_the_catalyst_gate`` and ``mercury_retort`` all
pass ``rtol=1e-8``). What gets swept is every call that took the default, and
those three are the audit's own self-check: they must come out byte-identical.

## ⚠ HOW A DIFFERENCE IS JUDGED, WHICH IS THE ONLY SUBTLE PART

Comparing two stdout dumps as text finds every digit that moved, and most of
them are noise: a wall clock differs on every run, and a mole printed to twelve
decimals differs in its last one for reasons no reader cares about. So each
numeric token is compared as a NUMBER with a relative tolerance, and a line is
reported only when a token moves by more than ``REPORT_REL``.

⚠⚠ **AND A WALL CLOCK IS EXCISED AS A TOKEN, NOT AS A LINE, BECAUSE THE FIRST
VERSION OF THIS AUDIT MANUFACTURED A FINDING BY GETTING THAT WRONG.** It
reported ``wait_until`` moving by 12.5%, and the 12.5% was "0.07 s of wall"
against "0.08 s of wall"; the same example's worst real move is 1.0e-4. See
``SCRUB``, which also records why keying on the word "wall" is not merely coarse
but wrong.

**A CONVERGED EXAMPLE IS ONE WHOSE OUTPUT DOES NOT MOVE.** That is the claim
being tested, and a difference is not automatically a defect in the example: it
says the number a reader would quote depends on a solver setting, which is the
thing M6 and S1 both got caught by.
"""

from __future__ import annotations

import argparse
import io
import math
import re
import runpy
import sys
import time
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from chemsim.threads import cap_blas_threads  # noqa: E402

# R2: numpy is not loaded yet -- the examples this audit runs load it -- so the
# cap binds. This audit is its own evidence that capping is safe here: R1 ran
# it capped twice and uncapped once and all three outputs were identical.
cap_blas_threads()

TIGHT = (1.0e-8, 1.0e-11)

# Relative move that counts as a difference. 1e-6 is well above the round-off two
# BDF runs will always differ by and well below anything a reader would quote.
REPORT_REL = 1.0e-6

# Absolute floor: below this, two numbers are both "zero" and their ratio is
# meaningless. Set at the LOOSE run's own atol, because a quantity smaller than
# the solver's absolute tolerance was never resolved in the first place.
REPORT_ABS = 1.0e-9

# THE SECOND FLOOR, AND IT IS ASYMMETRIC ON PURPOSE -- S11, engine queue item 6.
# A token that is SMALL and is getting SMALLER as the solver is refined is a
# residual converging, not a result moving. A token that is small and getting
# BIGGER is exactly the defect this audit exists to catch, and it is still
# reported at the strict ``REPORT_ABS`` floor. So the relaxation is applied in
# ONE DIRECTION only.
#
# THE NUMBER IS NOT INVENTED HERE -- it is the project's own measurement of the
# very column that forced this. ``NEXT_SESSION.md`` carries the burner's
# O2-limiting residual as **NOT AN INVARIANT**, with the reason stated as a
# measurement: an INERT N2 nudge of 0.5%, which changes no chemistry at all,
# swings that column from **2.5e-09 to 4.5e-04**. A quantity that moves five
# decades under a perturbation that cannot change the answer is not a quantity
# anybody quotes, at any value inside that swing. 5e-04 is the top of the
# measured swing, rounded up to one figure.
#
# AND THE SUPPRESSION IS NEVER SILENT. A line whose only moves are converging
# tokens is still PRINTED, under its own heading and with its own count, so a
# reader can see what was set aside and disagree. Blunting a test quietly is the
# failure this file was written to avoid.
CONVERGING_ABS = 5.0e-4

# ⚠⚠ WALL CLOCKS ARE SCRUBBED AS TOKENS, NOT AS LINES, AND THE FIRST VERSION OF
# THIS AUDIT GOT THAT WRONG IN BOTH DIRECTIONS AT ONCE.
#
# Dropping a whole LINE that mentions a wall time is too coarse: this project
# prints physics and timing on one line all the time --
#
#     until it boils  ->  t =  1353.13 s   T = 352.999 K   (0.89 s of wall)
#
# -- so dropping the line hides a move in ``t``, which is a number a reader
# quotes. And keying on the word "wall" is worse than coarse, it is WRONG:
# ``lime_cycle`` prints "-14.374 W solid-state against +14.374 W wall", where
# "wall" is a heat flux through the flask and is exactly the kind of number this
# audit exists to check.
#
# Measured, the first version reported ``wait_until`` as moving by **12.5%**, and
# that number was "0.07 s of wall" against "0.08 s of wall". Its real worst move
# is 1.0e-4. **An instrument that cannot tell a wall clock from a result will
# manufacture findings**, which is the same failure mode as a coverage number
# that counts a route the engine cannot run.
#
# So: excise the TIME EXPRESSION itself from both lines, symmetrically, and
# compare what is left. Every pattern requires a unit of SECONDS adjacent to the
# number, which is what keeps watts out of it.
#
# ⚠⚠ A SERIALIZED SIZE IN BYTES IS THE SAME CLASS OF THING, AND IT WAS FOUND THE
# SAME WAY -- BY A RECORDED NUMBER MOVING FOR A REASON THAT WAS NOT PHYSICS.
# ``workshop``'s worst move stood at 1.98e-04 across P1 and C7 and came back
# 1.95e-04 when R1 finally ran the audit P4 owed. Bisected to the commit
# (05609c4, P3+P4), and the moved line is:
#
#     save = 10113 bytes of JSON      P2 and before
#     save = 10237 bytes of JSON      P4 and after
#
# **The loose/tight gap is 2 bytes in both and is unchanged** -- the saved JSON
# holds a float whose decimal form is two characters longer at rtol 1e-8. What
# moved is the DENOMINATOR: P4 added six fields to ``TemplateSpec``, so every
# save file grew by 124 bytes and 2/10113 became 2/10237. Nothing physical
# changed, and the proof is that ``workshop``'s default-tolerance stdout is
# BYTE-IDENTICAL across those two commits.
#
# So this row was never evidence about convergence, and anyone quoting
# *"workshop's worst move is 1.98e-04"* was quoting the size of a JSON blob.
# Scrubbed, its real worst move is **1.33e-04 on a molarity** and it moves 1 line
# rather than 2. ⚠ The unit is required adjacent to the number for exactly the
# reason SECONDS is: it is what stops the pattern eating a mole or a watt.
SCRUB = [
    re.compile(p, re.IGNORECASE) for p in (
        r"\(?\s*\d+(?:\.\d+)?\s*s(?:ec(?:onds)?)?\s+of\s+wall\s*\)?",
        r"\d+(?:\.\d+)?\s*s(?:ec(?:onds)?)?\s+wall\b",
        r"\bwall[:=]?\s*\d+(?:\.\d+)?\s*s\b",
        r"\bin\s+\d+(?:\.\d+)?\s*s\b",
        r"\b\d+m\d+(?:\.\d+)?s\b",
        r"\b\d+(?:\.\d+)?\s*[KMG]?B(?:ytes?)?\b",
    )
]


def scrub(line: str) -> str:
    """Blank out wall clocks and serialized SIZES, leaving every other number.

    Both are numbers a run prints that say nothing about whether it CONVERGED,
    and each has manufactured a finding in this file once -- the wall clock in
    the first version, the byte count three milestones later. The test a pattern
    has to pass is the same for both: a unit adjacent to the number, so that a
    mole, a watt and a molarity are never touched.

    ⚠ THE SIZE PATTERN IS COMPILED ``IGNORECASE`` LIKE THE REST, SO WHAT KEEPS
    ``1.25 bar`` OUT OF IT IS THE TRAILING ``\b`` AND NOTHING ELSE. ``b``
    matches, ``ytes?`` does not match ``ar``, and the word boundary then fails
    against the ``a``. That is load-bearing rather than incidental: drop the
    ``\b`` and this audit starts scrubbing every pressure it prints. Asserted in
    the self-check below.
    """
    for pat in SCRUB:
        line = pat.sub("<scrubbed>", line)
    return line


# THE INSTRUMENT CHECKS ITSELF BEFORE IT CHECKS ANYTHING ELSE, because both
# findings this file has ever manufactured came from ``scrub`` and not from a
# solver. The left column MUST be scrubbed and the right column MUST NOT, and
# ``1.25 bar`` is in the second for the reason ``scrub``'s docstring gives.
_MUST_SCRUB = (
    "save = 10237 bytes of JSON",
    "written in 3.5 kB",
    "t = 1353.13 s   T = 352.999 K   (0.89 s of wall)",
    "elapsed 1m04.2s",
)
_MUST_NOT_SCRUB = (
    "-14.374 W solid-state against +14.374 W wall",
    "O   liq 0.8876 mol (7.490 M)   vap 0.00972 mol",
    "gas 0.0160000000 mol SO2, 1.25 bar",
    "p = 3.0863 bar at 1100 K",
    "yield 84.0 % and 0.5 mol",
)
for _line in _MUST_SCRUB:
    assert scrub(_line) != _line, f"scrub() missed a non-physical token: {_line!r}"
for _line in _MUST_NOT_SCRUB:
    assert scrub(_line) == _line, f"scrub() ate a RESULT: {_line!r}"

NUMBER = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")

# Every example that integrates something. ``thermochemistry`` is a property
# table and cannot be tolerance-limited, so it is not here and that is not an
# omission.
#
# ⚠ THE LAST THREE ARE EXPENSIVE AND ARE OPT-IN. ``plate_column`` runs a
# 403 s column twice and ``fractional_distillation`` a long rig; sweeping both
# means four such runs. ``oil_of_vitriol`` joined them in S5, when the bound in
# ``numerics/jacobian.py`` turned its refusal into a run -- one of its calls
# still takes ~50 s at rtol 1e-8 against 0.8 s at the default. ``--all``
# includes them.
CHEAP = [
    "activity",
    "esterification",
    "vessel",
    "extraction",
    "competing_pathways",
    "multistep_prep",
    "wait_until",
    "workshop",
    "named_routes",
    "lime_cycle",
    "roasting_and_the_catalyst_gate",
    # S4. Its third self-check example: it passes rtol 1e-8 on every call, so
    # rebinding the defaults must leave its output BYTE-IDENTICAL at a speedup
    # of 1.00. If that row ever moves, the rebinding has stopped working and
    # every other row in the report is suspect.
    "mercury_retort",
]
EXPENSIVE = ["plate_column", "fractional_distillation", "oil_of_vitriol"]

# ⚠⚠ THIS DICT IS EMPTY NOW, AND THE MACHINERY BELOW IS KEPT FOR THE NEXT ONE.
# "IT MOVED" AND "IT REFUSED" ARE DIFFERENT FINDINGS AND MUST NOT SHARE A ROW,
# which is why a refusal has its own dict, its own verdict code (-1) and its own
# summary line rather than a large "worst rel".
#
# ⚠ S5 CLOSED THE ONE ENTRY THIS EVER HELD. ``oil_of_vitriol`` used to RAISE at
# rtol 1e-8 in ``burn(690.0, o2=0.10, s8=0.002)``; the cause was BDF's
# perturbation factor overflowing to ``inf`` on a column it could never
# difference, and the bound in ``numerics/jacobian.py`` stops that at the state's
# own extent. The run now COMPLETES and gives 0.0160000000 mol of SO2 -- the same
# number the diagnosis below already said was correct -- so the example has moved
# to EXPENSIVE rather than being excluded. It is expensive because that one call
# still takes ~50 s at rtol 1e-8 against 0.8 s at the default: BDF is genuinely
# struggling with a liquid layer holding 1e-29 mol, and the bound stops the
# struggle ending in a NaN without stopping the struggle.
#
# The diagnosis it carried, kept because it is what a future refusal should look
# like:
#
# ``oil_of_vitriol`` RAISES at rtol 1e-8, in one specific call --
# ``burn(690.0, o2=0.10, s8=0.002)``, the panel that demonstrates the dryout-band
# fix. ``lu_factor`` gets ``array must not contain infs or NaNs`` on ``I - c J``:
# a NaN Jacobian, which is the trap ``chemsim-zero-jacobian-column`` and
# ``LAYER_REABSORB`` both document -- an identically zero Jacobian column makes
# ``num_jac``'s perturbation factor inflate without bound.
#
# ⚠ ITS NUMBERS ARE NOT WRONG, WHICH IS THE POINT OF DIAGNOSING RATHER THAN
# FLAGGING. Measured on that call:
#
#     default tolerance                 SO2 0.016000     0.7 s
#     rtol 1e-8                         RAISES          50.7 s of thrashing
#     rtol 1e-8 + 1e-9 mol of SO2       SO2 0.016000     1.6 s
#     rtol 1e-8 + 1e-6 mol of SO2       SO2 0.016001     2.5 s
#     rtol 1e-7                         SO2 0.016000     1.5 s
#
# A trace of the absent product removes the failure and the answer is unchanged to
# six figures, which is the same diagnostic that identified the trap before. So
# the example's quoted results are CONFIRMED, and what is exposed is a
# pre-existing engine fragility with a SECOND trigger: not only "a species absent
# from a sealed flask" but "a tight tolerance on a flask holding a trace".
#
# It was excluded by default because sweeping it cost 1049 s to reach a refusal
# already understood -- and it was named here, and printed in the summary, rather
# than dropped, because a coverage limit in this project is never silent.
#
# ⚠ THE DIAGNOSIS WAS RIGHT ABOUT THE ANSWER AND WRONG ABOUT THE COLUMN, which is
# worth keeping too. It read "the documented zero-column trap -- a species absent
# from a sealed flask". Measured in S5, the column that actually overflows is
# LIQUID LAYER 2's SO2 holding 8.21e-29 mol: not absent, not flat, and FROZEN by
# the RHS's own ``np.maximum(y, 0.0)`` because ``LAYER_REABSORB`` makes its ``f``
# negative and ``num_jac`` therefore steps downward. Same overflow, a different
# route in -- and the fix the trap was scheduled for (a diagonal on the GAS
# block) could not have reached it.
KNOWN_REFUSAL: dict[str, str] = {
    "named_routes": (
        "aniline-route (nitrobenzene + 5 mol H2 over nickel at 470 K) raises "
        "'Required step size is less than spacing between numbers' after "
        "2.377e-05 s of 3600. PRE-EXISTING: it raises on the PRE-S13 data too, "
        "at rtol 1e-7, which this sweep does not sample. The default-tolerance "
        "answer is CONFIRMED -- 1.000000 mol of aniline on both bases, complete "
        "conversion, and the liquid/gas split moves 2.5967 -> 2.6114 mol (0.6%). "
        "See the block below."
    ),
}

# ⚠⚠ THE ENTRY ABOVE, AND THE REASON IT IS A DIAGNOSIS AND NOT A REGRESSION.
#
# S13's corpus sweep gave nitrobenzene a measured boiling point (483.85 K
# against Joback's 515.40) and aniline one (457.25 against 436.09), and this
# audit -- which samples ONE tight point, rtol 1e-8 -- went from "2 lines moved"
# to "CANNOT BE SWEPT". That reads as a regression caused by the data change.
#
# It is not. Measured on BOTH bases, in one script, by rebuilding the same
# vessel through ``ThermochemistryProvider(measured_physical=...)``:
#
#     basis            default (1e-6)      rtol 1e-7        rtol 1e-8
#     pre-S13 Joback   1.000000 mol        RAISES           1.000000 mol
#     S13 measured     1.000000 mol        RAISES           RAISES
#
# ⚠⚠ **A ONE-POINT TOLERANCE SWEEP CANNOT TELL "NEWLY BROKEN" FROM "ALREADY
# BROKEN AT A POINT IT DOES NOT SAMPLE."** The fragility was reachable before
# S13 and one decade CLOSER to the default than the point this file tests; what
# the data change moved is which tolerances happen to step over it.
#
# The state is a violent opening transient: 5 mol of hydrogen charged as a
# LIQUID into 1 L at 470 K, where it is a Henry's-law solute and flashes into
# the headspace inside 24 microseconds. Nothing about it is subtle and nothing
# about the ANSWER is in doubt -- the conversion is complete on every run that
# finishes, on both data bases.

# ⚠⚠ AND RUNNING THAT SWEEP FOR THE FIRST TIME EXPOSED A FAULT IN THIS FILE.
# ``--only oil_of_vitriol`` completes in 1061 s tight against 57 s loose and
# reports "QUOTABLE DIGITS MOVE, worst 99.85%". **That headline is wrong.** Four
# of its five moved lines are the CREATED-MATTER residual, and every one gets
# SMALLER at the tight tolerance:
#
#     900 K   4.038e-08 -> 6.166e-11        675 K   5.620e-07 -> 1.587e-09
#     690 K   2.935e-05 -> 2.728e-07        730 K   5.233e-06 -> 7.357e-07
#
# i.e. a residual converging toward zero, which is a residual behaving -- and
# they are exactly the rows NEXT_SESSION.md already carries as "NOT AN
# INVARIANT". The single physical number among the five (liquid held at 450 K)
# moves 1.5154e-03 -> 1.5155e-03, **rel 6.6e-05, three decades under this file's
# own 1e-3 reportable band**.
#
# ⚠⚠ A RELATIVE-DIFFERENCE TEST IS MEANINGLESS ON A COLUMN WHOSE CONVERGED VALUE
# IS ZERO. ``0.000e+00 -> 2.728e-07`` gives rel 0.991 and reads as "99% moved";
# it means "a residual got smaller".
#
# ⚠⚠ FIXED IN S11, AND **NOT** BY RAISING ``REPORT_ABS``. That was the obvious
# move and it is the wrong one: ``REPORT_ABS`` is symmetric, so raising it to
# cover 2.9e-05 would blind this audit to a small quantity GROWING as well as
# shrinking -- and a residual growing under refinement is the defect the whole
# file exists to catch. The fix is a SECOND floor, ``CONVERGING_ABS``, applied
# only when the tight run's value is SMALLER than the loose one's. Direction is
# the information the old test threw away.
#
# ⚠ AND THE NUMBER CAME OUT OF A MEASUREMENT THIS PROJECT ALREADY HAD rather
# than out of this file: the same column swings 2.5e-09 to 4.5e-04 under an
# INERT 0.5% N2 nudge (``NEXT_SESSION.md``). See ``CONVERGING_ABS``.
#
# ⚠ PREDICTED BEFORE IT WAS RUN: 5 moved lines -> 1, worst 0.9985 -> 6.6e-05,
# the headline flips from QUOTABLE DIGITS MOVE to "(below 0.1%)", and no other
# example changes. Measured: see the session notes.


def set_tolerance(rtol: float | None, atol: float | None) -> None:
    """Rebind the two ``run`` defaults, or restore them with ``None``.

    ⚠ DEFAULTS AND NOT A WRAPPER, so that a caller passing its own tolerance is
    untouched. That distinction is the whole point: the examples already using
    rtol 1e-8 must come out identical, and if they do not, this harness is what
    is wrong rather than they are.
    """
    from chemsim.numerics.rig_integrator import RigIntegrator
    from chemsim.numerics.vessel_integrator import VesselIntegrator

    for cls in (VesselIntegrator, RigIntegrator):
        fn = cls.run
        base = getattr(fn, "_audit_defaults", None)
        if base is None:
            base = fn.__defaults__
            fn._audit_defaults = base
        if rtol is None:
            fn.__defaults__ = base
            continue
        # ``run(self, y0, t_span, rtol=..., atol=..., **kw)`` -- the two
        # tolerances are the first two defaults in both signatures. Asserted
        # rather than assumed, because a signature change here would silently
        # make this whole audit a no-op.
        assert base[:2] == (1.0e-6, 1.0e-9), (cls.__name__, base)
        fn.__defaults__ = (rtol, atol) + tuple(base[2:])


def run_example(name: str) -> tuple[str, float]:
    """Run one example in-process, capturing stdout. Returns (output, seconds)."""
    path = REPO / "examples" / f"{name}.py"
    buf = io.StringIO()
    t0 = time.time()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            runpy.run_path(str(path), run_name="__main__")
    except SystemExit:
        pass
    except Exception as exc:                                  # noqa: BLE001
        buf.write(f"\n!! RAISED {type(exc).__name__}: {exc}\n")
    return buf.getvalue(), time.time() - t0


def moved(a: str, b: str) -> tuple[float, int]:
    """The WORST relative move between these two lines, and how many tokens were
    set aside as CONVERGING. ``(0.0, k)`` means nothing moved that counts.

    ⚠ A MAGNITUDE RATHER THAN A BOOLEAN, AND THAT IS THE DIFFERENCE BETWEEN A
    FINDING AND A LIST. M6's kiln moved by a factor of 2.6 -- 160% -- in a
    conversion this project had written down. A dry flask's temperature ramp
    moves by 0.01 K in 442, which is 2e-5 and is not a number anyone quotes.
    Both are "the output changed"; only one is a defect, and a report that
    cannot tell them apart would bury the second finding of this kind under the
    first hundred harmless ones.

    ``inf`` means the two lines are not comparable term by term (a token count
    change, or a NaN on one side), which is always worth a human look.
    """
    na, nb = NUMBER.findall(a), NUMBER.findall(b)
    if len(na) != len(nb):
        return math.inf, 0
    worst = 0.0
    converging = 0
    for x, y in zip(na, nb):
        try:
            fx, fy = float(x), float(y)
        except ValueError:                                    # pragma: no cover
            return math.inf, 0
        if math.isnan(fx) != math.isnan(fy):
            return math.inf, 0
        if math.isnan(fx):
            continue
        if abs(fx) < REPORT_ABS and abs(fy) < REPORT_ABS:
            continue
        denom = max(abs(fx), abs(fy))
        if denom == 0.0:
            continue
        rel = abs(fx - fy) / denom
        if rel <= REPORT_REL:
            continue
        # A RESIDUAL CONVERGING, not a result moving. Both ends inside the band
        # the project has MEASURED this column to be meaningless within, and the
        # TIGHT run smaller than the loose one. See ``CONVERGING_ABS``.
        if (abs(fx) < CONVERGING_ABS and abs(fy) < CONVERGING_ABS
                and abs(fy) < abs(fx)):
            converging += 1
            continue
        worst = max(worst, rel)
    return (worst if worst > REPORT_REL else 0.0), converging


def diff(
    loose: str, tight: str
) -> tuple[list[tuple[int, float, str, str]], list[tuple[int, int, str, str]]]:
    """Lines whose numbers MOVED, worst first -- and, separately, the lines
    whose only differences were tokens that CONVERGED toward zero.

    Two lists rather than one, because they are two findings. The first is what
    the verdict is computed from; the second is printed so that the relaxation
    ``CONVERGING_ABS`` applies is visible rather than silent. A line can appear
    in the first list while still having converging tokens on it -- the 690 K
    burner row moves in ``liquid held`` and converges in ``created O``.
    """
    la, lb = loose.splitlines(), tight.splitlines()
    if len(la) != len(lb):
        return [(-1, math.inf, f"{len(la)} lines of output",
                 f"{len(lb)} lines of output")], []
    out = []
    conv = []
    for i, (a, b) in enumerate(zip(la, lb), start=1):
        if a == b:
            continue
        sa, sb = scrub(a), scrub(b)
        if sa == sb:
            continue                    # the only difference was a wall clock
        rel, n_conv = moved(sa, sb)
        if rel:
            out.append((i, rel, a.strip(), b.strip()))
        elif n_conv:
            conv.append((i, n_conv, a.strip(), b.strip()))
    out.sort(key=lambda r: -r[1])
    return out, conv


def show_converging(conv: list[tuple[int, int, str, str]]) -> None:
    """Print the lines set aside by ``CONVERGING_ABS``, so nothing is silent."""
    for lineno, n_conv, a, b in conv[:6]:
        print(f"     line {lineno}, {n_conv} token(s) shrank")
        print(f"       default: {a[:150]}")
        print(f"       tight  : {b[:150]}")
    if len(conv) > 6:
        print(f"     ... and {len(conv) - 6} more")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="include plate_column and fractional_distillation")
    ap.add_argument("--only", nargs="*", help="just these examples")
    args = ap.parse_args()

    names = args.only or (
        CHEAP + EXPENSIVE + list(KNOWN_REFUSAL) if args.all else CHEAP
    )

    print("=" * 78)
    print("TOLERANCE AUDIT -- every example at the DEFAULT vs rtol 1e-8/atol 1e-11")
    print("=" * 78)
    print(f"  default: rtol 1e-6, atol 1e-9      tight: rtol {TIGHT[0]:g}, "
          f"atol {TIGHT[1]:g}")
    print(f"  a token counts as MOVED at rel > {REPORT_REL:g}; both-below "
          f"{REPORT_ABS:g} is a shared zero")
    print(f"  {len(names)} examples"
          + ("" if args.all or args.only else
             f"; {len(EXPENSIVE)} expensive ones skipped (--all)"))
    print()

    verdicts = []
    for name in names:
        print(f"-- {name} " + "-" * (72 - len(name)))
        set_tolerance(None, None)
        loose, t_loose = run_example(name)
        set_tolerance(*TIGHT)
        tight, t_tight = run_example(name)
        set_tolerance(None, None)

        rows, conv = diff(loose, tight)
        raised = [ln for ln in tight.splitlines() if ln.startswith("!! RAISED")]
        faster = "FASTER" if t_tight < t_loose else "slower"
        ratio = t_loose / t_tight if t_tight > 0 else float("inf")
        print(f"   wall: loose {t_loose:7.2f} s   tight {t_tight:7.2f} s   "
              f"tight is {ratio:5.2f}x {faster}")
        if raised:
            # A REFUSAL IS NOT A MOVED NUMBER. Reported as its own thing, with
            # ``worst`` left at zero, so it can never be counted as a quotable
            # digit that shifted -- and never quietly counted as converged either.
            print(f"   !! CANNOT BE SWEPT -- {raised[0][11:130]}")
            known = KNOWN_REFUSAL.get(name)
            print(f"      {'DIAGNOSED: ' + known if known else 'NEW -- diagnose it'}")
            verdicts.append((name, -1, 0.0, t_loose, t_tight))
            print()
            continue
        if not rows:
            if conv:
                print("   NO RESULT MOVED. "
                      f"{len(conv)} line(s) differ only in RESIDUAL tokens that "
                      "got SMALLER under refinement:")
                show_converging(conv)
            else:
                print("   OUTPUT IDENTICAL -- converged at the default tolerance")
            verdicts.append((name, 0, 0.0, t_loose, t_tight))
            print()
            continue
        worst = rows[0][1]
        print(f"   !! {len(rows)} LINE(S) MOVED; worst is {worst:.3g} relative "
              f"({100 * worst:.4g}%)")
        for lineno, rel, a, b in rows[:10]:
            where = "STRUCTURE" if lineno < 0 else f"line {lineno}"
            print(f"     {where}, rel {rel:.3g}")
            print(f"       default: {a[:150]}")
            print(f"       tight  : {b[:150]}")
        if len(rows) > 10:
            print(f"     ... and {len(rows) - 10} more, all smaller")
        if conv:
            print(f"   plus {len(conv)} line(s) whose ONLY moves were residual "
                  "tokens converging toward zero:")
            show_converging(conv)
        verdicts.append((name, len(rows), worst, t_loose, t_tight))
        print()

    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"   {'example':34} {'lines':>6} {'worst rel':>11} "
          f"{'loose/s':>9} {'tight/s':>9} {'speedup':>8}")
    # ⚠ THE SEVERITY BANDS ARE DECLARED, NOT INFERRED. 1e-3 is the point at which
    # a move shows up in a number written to three or four significant figures,
    # i.e. the way every quoted result in this project IS written. Below that a
    # difference is real and not reportable; above it, a reader could copy the
    # wrong digit out of the panel.
    serious = [v for v in verdicts if v[2] >= 1.0e-3]
    minor = [v for v in verdicts if 0.0 < v[2] < 1.0e-3]
    refused = [v for v in verdicts if v[1] < 0]
    for name, n, worst, tl, tt in verdicts:
        flag = ""
        if n < 0:
            flag = "   <-- CANNOT BE SWEPT (raises)"
        elif worst >= 1.0e-3:
            flag = "   <-- QUOTABLE DIGITS MOVE"
        elif worst > 0.0:
            flag = "   (below 0.1%)"
        rel = "--" if not worst else f"{worst:.2e}"
        lines = "raise" if n < 0 else str(n)
        print(f"   {name:34} {lines:>6} {rel:>11} {tl:9.2f} {tt:9.2f} "
              f"{(tl / tt if tt else 0):8.2f}{flag}")
    print()
    # Named whether or not it was run this time, so the limit is never silent.
    for name, why in KNOWN_REFUSAL.items():
        if name not in [v[0] for v in verdicts]:
            print(f"   NOT SWEPT: {name} -- {why}")
    if refused:
        print(f"   {len(refused)} example(s) RAISED at rtol 1e-8. That is a")
        print("   refusal, not a wrong number -- see KNOWN_REFUSAL.")
    if [v for v in verdicts if v[0] in KNOWN_REFUSAL] or refused:
        print()
    if serious:
        print(f"!! {len(serious)} example(s) print a QUOTABLE digit that depends "
              f"on the solver tolerance:")
        for name, _n, worst, _tl, _tt in serious:
            print(f"!!     {name}  --  worst {100 * worst:.4g}%")
        print("!! Those numbers must not be quoted from a default run. Give the")
        print("!! example its own tight tolerance, the way lime_cycle.py and")
        print("!! roasting_and_the_catalyst_gate.py do.")
    else:
        print("NO example prints a quotable digit that moves. That is the")
        print("audit's finding, and it is a real one: the exposure M6 and S1 both")
        print("hit is CONTAINED to the vented solid-gas examples, both of which")
        print("already pass an explicit rtol 1e-8.")
    if minor:
        print()
        print(f"   {len(minor)} example(s) move below 0.1% -- real, and not a")
        print("   number anyone quotes. Listed above rather than hidden:")
        for name, _n, worst, _tl, _tt in minor:
            print(f"     {name}  --  worst {worst:.2e}")
    # ⚠⚠ AND THIS IS THE ROW THAT REFUTED A CLAIM THIS PROJECT HAD ALREADY
    # WRITTEN DOWN IN FOUR PLACES. M6 measured its kiln running FASTER tight
    # (1.4-3.3 s against 5-13 s), S1 measured the same on a roast (3.67 against
    # 19.94 s), and "the tight run is also faster" got generalised into
    # MILESTONES, HANDOFF, NEXT_PROMPT and a memory file. Swept across every
    # example it is FALSE: tightening is usually SLOWER, sometimes by an order of
    # magnitude, and the speedup was a property of a vented solid-gas flask
    # rather than of tightening. The generalisation would have told the next
    # session that tightening is free.
    faster = [v for v in verdicts if v[4] < v[3]]
    slower = [v for v in verdicts if v[4] > v[3]]
    worst_cost = max((v[4] / v[3] for v in verdicts if v[3] > 0), default=1.0)
    print()
    print(f"   COST: the tight run is FASTER in {len(faster)} of "
          f"{len(verdicts)} cases and SLOWER in {len(slower)}, "
          f"worst {worst_cost:.1f}x.")
    print("   !! SO 'THE TIGHT RUN IS ALSO FASTER' IS NOT A GENERAL PROPERTY.")
    print("   It held for M6's vented kiln and S1's roast -- a stiff vent fed by")
    print("   slow chemistry, where the loose solver thrashes -- and it does NOT")
    print("   generalise. Tightening usually costs time. Budget for it.")
    return 1 if serious else 0


if __name__ == "__main__":
    raise SystemExit(main())

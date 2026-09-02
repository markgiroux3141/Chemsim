"""P0: the measurements the P-series was chosen from, pinned.

A direction was changed on these numbers. `PLAYABLE.md` rotted for three
milestones because nothing asserted it (`ROUTE_INDEX.md` did worse), and the
lesson C4 drew was to lift a generated table to module level *so a test can read
it*. Same treatment here.

⚠ These are SLOW-ish (the scorer's deep chain is ~50 s) so they share one
module-scoped import, and they assert the SHAPE of each finding rather than an
exact count -- a content session is allowed to move the numbers, but not to make
the argument false without noticing.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

import catalog as cat  # noqa: E402


@pytest.fixture(scope="module")
def bp():
    """``tools/build_playable.py``, imported for its fixed point (~50 s)."""
    spec = importlib.util.spec_from_file_location(
        "bp_test", os.path.join(_ROOT, "tools", "build_playable.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bp_test"] = mod
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


def _runnable(bp, classes=(), price_all=False):
    tc2 = set(bp.TC) | set(classes)
    pr = (lambda x: x in bp.compounds) if price_all else bp.priced
    return {rid for rid in bp.routes
            if cat.route_reachable(bp.steps, rid, bp.routes[rid].target,
                                   pr, tc2, bp.compounds)}


def test_the_two_work_streams_are_super_additive(bp):
    """⚠⚠⚠ **THE FINDING THAT PAUSED THE C-SERIES.** `PLAYABLE.md` §8b ranks
    each missing class at "+1" holding prices fixed, and its ceiling of 45 is a
    JOINT grant of templates AND prices. Templates alone are worth far less than
    the ceiling implies, and the joint is worth more than the sum of the parts.

    If this ever stops holding, §8b becomes a defensible work order again and
    `docs/history/MILESTONES.md` §THE P-SERIES has to be re-argued.
    """
    base = len(bp.PLAYABLE)
    allc = sorted(bp.CLASS_GAPS)
    templates = len(bp.closure(pool=_runnable(bp, allc))[0]) - base
    prices = len(bp.closure(pool=_runnable(bp, (), True))[0]) - base
    joint = len(bp.closure(pool=_runnable(bp, allc, True))[0]) - base

    assert templates > 0 and prices > 0
    assert joint > templates + prices, (
        f"templates +{templates}, prices +{prices}, joint +{joint} -- the "
        "super-additivity is the whole argument for the P-series"
    )
    # and the headline: templates alone are worth well under the ceiling
    assert templates < joint / 2


def test_routes_are_stranded_rather_than_missing_chemistry(bp):
    """⚠⚠ The engine can already RUN more routes than a player can REACH, and
    the gap is feedstocks rather than templates. This is what makes a starting
    shelf the cheapest distance on the board."""
    base = len(bp.PLAYABLE)
    stranded = bp.BLOCKED + bp.BOTTLE
    assert len(stranded) >= 15, "the stranded bucket is the P-series' premise"

    want = {x for _rid, miss, _o in bp.BLOCKED for x in miss}
    want |= {x for _rid, _m, orphan in bp.BOTTLE for x in orphan}
    granted = len(bp.closure(extra=want)[0])
    assert granted - base >= len(stranded) - 5, (
        f"granting {len(want)} species moved playable by {granted - base} "
        f"against {len(stranded)} stranded routes"
    )
    # and it beats the whole template work order
    allc = sorted(bp.CLASS_GAPS)
    assert granted > len(bp.closure(pool=_runnable(bp, allc))[0])


def test_the_chain_and_bottle_buckets_are_different_problems(bp):
    """⚠ The shelf's `intermediate` and `bottle` tiers exist because these two
    are not interchangeable: a chain species is MADE by a route that is itself
    stranded, so it can be earned later and the shelf row deleted; a bottle is
    made by nothing in the corpus at all. `GAME_DESIGN.md` §8.5."""
    chain = {x for _rid, miss, _o in bp.BLOCKED for x in miss}
    bottle = {x for _rid, _m, orphan in bp.BOTTLE for x in orphan}
    assert chain and bottle
    assert not (chain & bottle)
    assert chain <= bp.MADE_SOMEWHERE
    assert not (bottle & bp.MADE_SOMEWHERE)


def test_a_named_process_is_a_one_off_and_that_is_the_slog(bp):
    """⚠⚠ The catalog is a list of named industrial processes, so most of its
    classes serve exactly one route step. That is a fact about the TARGET LIST,
    and it is why grinding §8b is slow while the engine is general -- see
    `test_one_template_is_thousands_of_reactions`."""
    sizes: dict[str, int] = {}
    for s in bp.steps:
        sizes[s.cls] = sizes.get(s.cls, 0) + 1
    singletons = sum(1 for n in sizes.values() if n == 1)
    assert singletons / len(sizes) > 0.6, (
        f"{singletons} of {len(sizes)} classes are used once"
    )


def test_one_template_is_thousands_of_reactions():
    """⚠⚠⚠ **THE ANSWER TO 'ARE WE WRITING CODE PER REACTION'.** One SMARTS rule
    against the corpus is four orders of magnitude more chemistry than the
    scoreboard can see. Needs no scorer, so it is fast."""
    import csv

    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    from chemsim.reactions import library

    t = library.esterification()
    pats = [Chem.MolFromSmarts(p)
            for p in t.smarts.partition(">>")[0].split(".")]
    assert all(p is not None for p in pats)
    slots = [0] * len(pats)
    path = os.path.join(_ROOT, "data", "catalog", "compounds")
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".psv"):
            continue
        with open(os.path.join(path, fn), encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="|"):
                if not row or row[0].strip().startswith("#") or len(row) < 3:
                    continue
                m = Chem.MolFromSmiles(row[2].strip())
                if m is None:
                    continue
                for i, p in enumerate(pats):
                    if m.HasSubstructMatch(p):
                        slots[i] += 1
    grid = 1
    for n in slots:
        grid *= n
    credited = sum(1 for s in cat.load_steps() if "esterif" in s.cls)
    assert grid > 10_000, f"esterification fan-out is {slots} = {grid}"
    assert grid > 1000 * credited


# ---------------------------------------------------------------------------
# P3 -- and the shelf FILE has to be the measurement, not a memory of it
# ---------------------------------------------------------------------------


def test_the_shelf_file_holds_exactly_what_this_audit_measured(bp):
    """⚠⚠ `data/catalog/shelf.psv`'s three tiers, against the numbers they came
    from. This is the assertion that stops the shelf rotting: the file is
    hand-maintained, its CONTENT is derived from panel 3, and nothing else
    compares the two. A route that becomes reachable should DELETE its
    intermediate rows -- if that happens and the file is not edited, this test is
    what says so, and the failure message is the work order.

    ⚠ The natural tier is asserted as an equality MINUS THE MARKERS, which is the
    one deliberate difference: `coal-marker` and `collagen-marker` are declared
    natural and have no molecular graph, so they cannot be shelf rows at all.
    """
    from chemsim.engine.shelf_data import SHELF

    rows = {e.tier: {x.id for x in SHELF if x.tier == e.tier} for e in SHELF}
    chain = {x for _rid, miss, _o in bp.BLOCKED for x in miss}
    bottle = {x for _rid, _m, orphan in bp.BOTTLE for x in orphan}
    markers = {c for c in bp.NATURAL_IDS if c not in bp.compounds}

    assert markers == {"coal-marker", "collagen-marker"}, (
        f"the marker set moved: {sorted(markers)}. A marker has no graph and "
        f"cannot be a shelf row -- see shelf.psv's header."
    )
    assert rows["natural"] == set(bp.NATURAL_IDS) - markers, (
        f"shelf.psv's natural tier and build_playable's NATURAL disagree.\n"
        f"  missing from the file: {sorted(set(bp.NATURAL_IDS) - markers - rows['natural'])}\n"
        f"  in the file and not natural: {sorted(rows['natural'] - set(bp.NATURAL_IDS))}"
    )
    assert rows["intermediate"] == chain, (
        f"the CHAIN-blocked species moved -- this is the tier that is supposed "
        f"to shrink, so this is a work order rather than a bug.\n"
        f"  now earnable, DELETE from shelf.psv: "
        f"{sorted(rows['intermediate'] - chain)}\n"
        f"  newly stranded, ADD to shelf.psv: {sorted(chain - rows['intermediate'])}"
    )
    assert rows["bottle"] == bottle, (
        f"the BOTTLE species moved: file {sorted(rows['bottle'])} vs measured "
        f"{sorted(bottle)}"
    )

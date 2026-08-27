"""G3 -- the PLAYABLE scoreboard, asserted so the artefact cannot rot.

⚠⚠ **THIS FILE EXISTS BECAUSE `ROUTE_INDEX.md` ROTTED FOR THREE MILESTONES AND
NOTHING NOTICED**, for exactly one reason: no test read it. A generated artefact
with no assertion behind it is a snapshot of whenever somebody last remembered to
run the generator. So every headline number in `data/catalog/PLAYABLE.md` is
pinned here, and the scoring rules that were measured wrong first are pinned as
the WRONG answer too -- a rule that silently reverts would otherwise look like a
scoreboard going up.

⚠ The expensive half of the generator -- the deep chain, ~45 s of it -- is NOT
re-run here. `tools/build_playable.py` runs it and writes the numbers into the
report; what this file asserts is the classification, the rules, and that the
report on disk is the one the current code produces. The chain's own chemistry is
covered where it lives: `validation/smelting.py` for the retort and the two
smelters, `tests/test_named_routes.py` for the methanol template.
"""

from __future__ import annotations

import importlib
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("src", "tools", "validation"):
    _full = os.path.join(_ROOT, _p)
    if _full not in sys.path:
        sys.path.insert(0, _full)


@pytest.fixture(scope="module")
def bp():
    """The generator, imported with its chain run suppressed.

    ⚠ ``build_playable`` runs the deep chain at import time, which is 45 s of the
    user's CPU and is not what these tests are about. Importing it once per module
    and monkeypatching nothing is still the honest way to get at the same
    functions the report was built from -- a re-implementation here would be a
    second copy of the scorer, which is the thing G3 spent a commit removing.
    """
    return importlib.import_module("build_playable")


# ---------------------------------------------------------------------------
# 1. THE HEADLINE
# ---------------------------------------------------------------------------
def test_the_answer_is_fourteen_playable_three_tiers_deep(bp):
    """14 of 173, and the corpus's deepest chain is still 3 tiers.

    ⚠ G3 measured 12 of 36 runnable. C1 built ``sulfur_trioxide_hydration`` and
    corrected the ``vitriol-distillation`` rows, which put oil of vitriol on the
    shelf from a natural mineral and carried ``saltpetre-nitric`` up with it.
    """
    assert len(bp.routes) == 173
    assert len(bp.PLAYABLE) == 14
    assert max(bp.PLAYABLE.values()) == 3
    assert len(bp.RUNNABLE) == 37
    assert bp.PLAYABLE["vitriol-distillation"] == 1
    assert bp.PLAYABLE["saltpetre-nitric"] == 2


def test_the_tech_tree_is_a_shallow_bush(bp):
    """9 of the 14 are tier 1 -- they touch nothing another route made.

    The GOAL asks for a connected tech tree. This is the measurement that says it
    is not one yet, and it is the reason the file exists. ⚠ C1 added one route to
    each of the first two tiers, so the SHAPE did not change: the corpus is still
    a fan off the ground with one thin chain hanging off it.
    """
    tier1 = [r for r, d in bp.PLAYABLE.items() if d == 1]
    assert len(tier1) == 9
    assert len(tier1) > len(bp.PLAYABLE) / 2


def test_the_ceiling_is_the_goal_and_it_is_a_finite_named_list(bp):
    """Granting all 24 fed-but-unrunnable routes reaches 41, against a goal of ~40.

    This is the whole point of the work order: the distance from 14 to 41 is a
    named table, not an open-ended grind against 173 routes.

    ⚠⚠ AND THE TABLE GREW WHEN A ROW WAS TAKEN OFF IT. C1 granted one of G3's 21
    and the list went to 24, because sulfuric acid on the shelf FEEDS four routes
    that were not fed before (`guncotton`, `hmf-route`, `phosphoric-wet`,
    `superphosphate`). The ceiling moved 37 -> 41 with it. *A work order derived
    from a fixed point is not a burndown list; granting a row can lengthen it.*
    """
    assert len(bp.FED_BUT_UNRUNNABLE) == 24
    ceiling, _ = bp.closure(pool=bp.RUNNABLE | set(bp.FED_BUT_UNRUNNABLE))
    assert len(ceiling) == 41
    # three fall out for free once the shelf grows -- G3 had four, and
    # `saltpetre-nitric` is the one C1 promoted into PLAYABLE outright
    free = set(ceiling) - set(bp.PLAYABLE) - set(bp.FED_BUT_UNRUNNABLE)
    assert free == {"acetic-fermentation", "haber-bosch", "thermite"}


# ---------------------------------------------------------------------------
# 2. THE FOUR RULES, AND EACH ONE PINNED AT ITS WRONG ANSWER TOO
# ---------------------------------------------------------------------------
def test_a_need_is_decided_by_order_not_by_route_roles(bp):
    """The first version read ``route_roles().feedstocks`` and over-credited.

    ⚠ A closed cycle derives an EMPTY feedstock list. ``lime-cycle`` regenerates
    its own limestone in row 3, so under the roles rule it needed *nothing at
    all* and was playable for free.
    """
    wrong, _ = bp.closure(needs_rule=bp.needs_by_roles)
    assert len(wrong) == 15
    assert len(bp.PLAYABLE) == 14, "the correction moves the headline DOWN"

    assert bp.needs_by_roles("lime-cycle") == set()
    assert bp.needs("lime-cycle") == {"calcium-carbonate", "water"}


def test_the_lead_chambers_nox_carrier_is_a_starting_charge(bp):
    """Row 2 wants NO2 and row 3 makes it, so ``route_roles`` calls it an
    intermediate -- and it is a charge the player must already hold.

    G4's own run of this route handed it 0.004 mol of NO2 by hand and then
    measured it recovered, which is what a catalytic carrier does. The scorer has
    to ask for it even though the route gives it back.
    """
    assert "nitrogen-dioxide" not in bp.needs_by_roles("lead-chamber")
    assert "nitrogen-dioxide" in bp.needs("lead-chamber")
    assert "lead-chamber" not in bp.PLAYABLE
    # and it is blocked on ONLY that
    assert bp.needs("lead-chamber") - bp.SHELF == {"nitrogen-dioxide"}


def test_the_fouling_row_takes_the_target_off_the_shelf(bp):
    """``lead-chamber`` row 4 consumes its own sulfuric acid to make chamber
    crystals, so the acid is an INTERMEDIATE and not a product.

    Crediting ``route_roles().products`` alone therefore loses the thing the
    route exists to make. Same catalog row as the test above and as G4's, read
    from a third side.
    """
    import catalog as cat

    roles = cat.route_roles(bp.steps, "lead-chamber")
    assert "sulfuric-acid" in roles.intermediates
    assert "sulfuric-acid" not in roles.products
    assert "sulfuric-acid" in bp.shelves("lead-chamber")

    # ⚠⚠⚠ AND C1 DISSOLVED THIS RULE'S ONLY EVIDENCE, WHICH IS WHY THE GRID IS
    # STILL HERE RATHER THAN DELETED. G3 measured the products-only shelf costing
    # a route (13 against 14) under the WRONG needs rule and nothing under the
    # right one. It now costs nothing in EITHER row:
    #
    #                  shelf=target   +byproducts   +target unioned in
    #     needs=roles   G3 10 / C1 11  G3 13 / C1 15  G3 14 / C1 15
    #     needs=order   G3  8 / C1 10  G3 12 / C1 14  G3 12 / C1 14
    #
    # The route the shelf rule used to buy was `saltpetre-nitric`, and it got its
    # sulfuric acid from the lead chamber's fouling row. C1 gave the acid a route
    # of its own, so losing the chamber's copy costs nothing anywhere.
    #
    # ⚠⚠ THE RULE IS KEPT ANYWAY AND THE REASON IS NOT SENTIMENT. It is a
    # statement about ``route_roles`` -- asserted above and still true -- and its
    # measured cost is a property of TODAY'S corpus. A rule justified by a
    # difference must not be reverted the day the difference goes away; that is
    # how a corrected instrument un-corrects itself. *What is measured here now
    # is that the cost is zero, and that is written down rather than hidden.*
    kw = dict(needs_rule=bp.needs_by_roles)
    assert len(bp.closure(shelf_rule="products", **kw)[0]) == 15
    assert len(bp.closure(shelf_rule="both", **kw)[0]) == 15
    assert len(bp.closure(shelf_rule="products")[0]) == 14
    assert len(bp.closure(shelf_rule="both")[0]) == 14


def test_target_only_shelving_never_starts_the_deep_chain(bp):
    """The whole of tier 3 hangs off a BYPRODUCT, so a shelf that holds only
    targets is 4 routes short and has no third tier.

    ⚠ G3 measured 8 at depth 1. C1's own route is a tier-1 whose TARGET feeds
    `saltpetre-nitric`, so a target-only shelf now reaches depth 2 -- but the
    deep chain still does not start, because the zinc retort's carbon monoxide
    is a byproduct and no shelf rule that reads targets can see it.
    """
    target_only, _ = bp.closure(shelf_rule="target")
    assert len(target_only) == 10
    assert max(target_only.values()) == 2
    assert "methanol-synthesis" not in target_only
    assert len(bp.PLAYABLE) - len(target_only) == 4


def test_a_catalyst_is_a_feedstock_and_that_rule_makes_the_third_tier(bp):
    """Drop it and the corpus has no third tier at all.

    Methanol needs no tier-2 *reagent* -- its CO is tier 1 and its hydrogen is
    tier 1 (chloralkali throws hydrogen off making caustic soda from rock salt).
    It is tier 3 for exactly one reason: the copper has to be smelted first.
    """
    free_catalysts, _ = bp.closure(with_catalysts=False)
    assert max(free_catalysts.values()) == 2
    assert max(bp.PLAYABLE.values()) == 3
    # and granting copper collapses the third tier
    with_copper, _ = bp.closure(extra={"copper"})
    assert with_copper["methanol-synthesis"] == 2
    assert max(with_copper.values()) == 2
    # the two routes the rule costs are blocked on metals nobody makes
    assert set(free_catalysts) - set(bp.PLAYABLE) == {
        "haber-bosch", "hydrogenation-margarine"}


def test_the_target_may_not_be_charged_still_holds(bp):
    """G4's rule, now in ``catalog.route_reachable`` and shared by both audits.

    ``bayer-process`` purifies bauxite and ``contact-process`` recycles its own
    acid; both write their target on the left of step 1.
    """
    assert "bayer-process" not in bp.RUNNABLE
    assert "contact-process" not in bp.RUNNABLE


# ---------------------------------------------------------------------------
# 3. THE SHAPE OF THE TREE
# ---------------------------------------------------------------------------
def test_the_deep_chain_hangs_off_a_zinc_retorts_byproduct(bp):
    """Nothing else a player can reach makes carbon monoxide, and three tier-2
    routes plus one tier-3 route all want it."""
    assert bp.PLAYABLE["zinc-smelting"] == 1
    assert "carbon-monoxide" in bp.shelves("zinc-smelting")
    assert "carbon-monoxide" != bp.routes["zinc-smelting"].target

    makers = [r for r in bp.PLAYABLE if "carbon-monoxide" in bp.shelves(r)]
    assert makers == ["zinc-smelting"]

    wants = {r for r in bp.PLAYABLE if "carbon-monoxide" in bp.needs(r)}
    assert wants == {"copper-smelting", "lead-smelting", "water-gas-shift",
                     "methanol-synthesis"}


def test_the_only_tier_three_route_is_methanol(bp):
    tier3 = [r for r, d in bp.PLAYABLE.items() if d == 3]
    assert tier3 == ["methanol-synthesis"]


def test_hydrogen_reaches_tier_one_as_a_byproduct_of_caustic_soda(bp):
    """Which is why methanol is not gated on the water-gas shift."""
    assert bp.PLAYABLE["chloralkali"] == 1
    assert "hydrogen" in bp.shelves("chloralkali")
    assert bp.routes["chloralkali"].target == "sodium-hydroxide"


# ---------------------------------------------------------------------------
# 4. THE LEVER, AND THE HISTOGRAM THAT DISAGREES WITH IT
# ---------------------------------------------------------------------------
def test_there_is_no_lever_and_the_frequent_blocker_is_not_the_valuable_one(bp):
    """The most-frequent blocker is worth +1; the most valuable one blocks ONE.

    A histogram of blockers is not a work order, and this is the measurement that
    says so.

    ⚠⚠ C1 RE-MEASURED THIS AND THE FINDING SURVIVED WITH ALL NEW NUMBERS. G3's
    example was `sulfuric-acid`, 4 routes and worth +1 -- and C1 put the acid on
    the shelf, so it is not a blocker at all any more. The shape held: `nickel`
    and `benzaldehyde` now block three routes each and are worth +1, while
    `aluminium` blocks ONE and is worth +2. *A finding that survives having its
    own example removed was about the shape and not about the example.*
    ⚠ And `nitrogen-dioxide` fell from +2 to +1 for the same reason -- fragility
    31's lead-chamber pinch is worth half what G3 priced it at, because
    `saltpetre-nitric` no longer needs the chamber's acid.
    """
    from collections import Counter

    blockers: Counter[str] = Counter()
    for rid in bp.RUNNABLE - set(bp.PLAYABLE):
        for x in bp.needs(rid) - bp.SHELF:
            blockers[x] += 1

    def worth(x: str) -> int:
        return len(bp.closure(extra={x})[0]) - len(bp.PLAYABLE)

    assert "sulfuric-acid" not in blockers, "C1 put it on the shelf"
    top = blockers.most_common(1)[0][1]
    assert top == 3
    for x, n in blockers.items():
        if n == top:
            assert worth(x) == 1, x

    assert worth("aluminium") == 2
    assert blockers["aluminium"] == 1
    assert worth("nitrogen-dioxide") == 1   # G3 priced it at 2
    # nothing is worth more than 2 -- there is no lever
    assert max(worth(x) for x in blockers) == 2


def test_the_top_content_row_is_hall_heroult_and_it_opens_the_deepest_chain(bp):
    """aluminium unblocks thermite, thermite's iron unblocks haber-bosch."""
    def worth_route(rid: str) -> int:
        return len(bp.closure(pool=bp.RUNNABLE | {rid})[0]) - len(bp.PLAYABLE)

    assert worth_route("hall-heroult") == 3
    assert worth_route("hall-heroult") == max(
        worth_route(r) for r in bp.FED_BUT_UNRUNNABLE)


def test_four_of_the_work_order_need_no_template_at_all(bp):
    """They are blocked purely on a species the engine refuses to price, which
    makes a DATA refusal measurably a playability blocker.

    ⚠⚠ G3 FOUND TWO AND C1 DOUBLED IT WITHOUT MEANING TO. Sulfuric acid on the
    shelf FED `phosphoric-wet` and `superphosphate`, and both are then blocked on
    one entry: `calcium-phosphate`, phosphate rock, which is already on the
    NATURAL list and which the engine refuses to price. **One mineral is worth
    +2 playable routes and needs no chemistry at all** -- the cheapest row in the
    work order and it is a data job.
    """
    species_only = [r for r in bp.FED_BUT_UNRUNNABLE
                    if not {s.cls for s in bp.route_steps(r)} - set(bp.TC)]
    assert sorted(species_only) == ["hypochlorite-bleach", "phosphoric-wet",
                                    "pyrite-roasting", "superphosphate"]
    # pyrite is the engine queue's own source-blocked entry
    assert not bp.priced("iron-disulfide")
    # and the new pair share ONE blocker, which is a declared natural material
    assert not bp.priced("calcium-phosphate")
    assert "calcium-phosphate" in bp.NATURAL_IDS
    both = bp.closure(pool=bp.RUNNABLE | {"phosphoric-wet", "superphosphate"})[0]
    assert len(both) - len(bp.PLAYABLE) == 2


# ---------------------------------------------------------------------------
# 5. THE HAND JUDGEMENT IS PRINTED, AND IT IS THE THING TO ARGUE WITH
# ---------------------------------------------------------------------------
def test_every_natural_species_is_a_real_compound_or_a_declared_marker(bp):
    """A typo in the natural list would silently shrink the tree."""
    for cid in bp.NATURAL_IDS:
        assert cid in bp.compounds or cid.endswith("-marker"), cid


def test_the_natural_list_is_generous_so_the_answer_is_an_upper_bound(bp):
    """The GOAL says ~10 natural starting materials; 45 are declared.

    That matters for how the headline reads: 12 playable is an UPPER bound on
    playability under a deliberately loose judgement, not a lower one.
    """
    assert len(bp.NATURAL_IDS) == 45
    assert len(bp.NATURAL_IDS) > 4 * 10


def test_the_report_on_disk_matches_the_code(bp):
    """⚠ THE ROUTE_INDEX LESSON. A generated artefact nobody asserts goes stale.

    This does not diff the whole file -- §5's yields are floating point and
    `chemsim-generated-artefacts` records that a report which cannot be diffed is
    a report nobody diffs. It checks the headline numbers, which is what a reader
    quotes.
    """
    import catalog as cat

    path = os.path.join(cat.CATALOG_DIR, "PLAYABLE.md")
    assert os.path.exists(path), "run tools/build_playable.py"
    text = open(path, encoding="utf-8").read()
    assert f"**{len(bp.PLAYABLE)} of {len(bp.routes)} named routes are playable" in text
    assert f"{len(bp.FED_BUT_UNRUNNABLE)} of the {len(bp.UNRUNNABLE)} routes" in text
    assert f"{len(bp.NATURAL_IDS)} species are declared natural" in text
    assert "## 2. The one hand judgement, printed so it can be argued with" in text
    # the judgement itself is IN the file, which is the requirement G3 was given
    for cid in ("zinc-sulfide", "sulfur-s8", "salicin"):
        assert f"`{cid}`" in text, cid

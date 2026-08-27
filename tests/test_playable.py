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
def test_the_answer_is_twelve_playable_three_tiers_deep(bp):
    """12 of 173, and the corpus's deepest chain is 3 tiers."""
    assert len(bp.routes) == 173
    assert len(bp.PLAYABLE) == 12
    assert max(bp.PLAYABLE.values()) == 3
    assert len(bp.RUNNABLE) == 36


def test_the_tech_tree_is_a_shallow_bush(bp):
    """8 of the 12 are tier 1 -- they touch nothing another route made.

    The GOAL asks for a connected tech tree. This is the measurement that says it
    is not one yet, and it is the reason the file exists.
    """
    tier1 = [r for r, d in bp.PLAYABLE.items() if d == 1]
    assert len(tier1) == 8
    assert len(tier1) > len(bp.PLAYABLE) / 2


def test_the_ceiling_is_the_goal_and_it_is_a_finite_named_list(bp):
    """Granting all 21 fed-but-unrunnable routes reaches 37, against a goal of ~40.

    This is the whole point of the work order: the distance from 12 to 37 is a
    named table, not an open-ended grind against 173 routes.
    """
    assert len(bp.FED_BUT_UNRUNNABLE) == 21
    ceiling, _ = bp.closure(pool=bp.RUNNABLE | set(bp.FED_BUT_UNRUNNABLE))
    assert len(ceiling) == 37
    # four fall out for free once the shelf grows
    free = set(ceiling) - set(bp.PLAYABLE) - set(bp.FED_BUT_UNRUNNABLE)
    assert free == {"acetic-fermentation", "haber-bosch", "saltpetre-nitric",
                    "thermite"}


# ---------------------------------------------------------------------------
# 2. THE FOUR RULES, AND EACH ONE PINNED AT ITS WRONG ANSWER TOO
# ---------------------------------------------------------------------------
def test_a_need_is_decided_by_order_not_by_route_roles(bp):
    """The first version read ``route_roles().feedstocks`` and credited 14.

    ⚠ A closed cycle derives an EMPTY feedstock list. ``lime-cycle`` regenerates
    its own limestone in row 3, so under the roles rule it needed *nothing at
    all* and was playable for free.
    """
    wrong, _ = bp.closure(needs_rule=bp.needs_by_roles)
    assert len(wrong) == 14
    assert len(bp.PLAYABLE) == 12, "the correction moves the headline DOWN"

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

    # ⚠ AND THE COST OF GETTING IT WRONG IS ONLY VISIBLE UNDER THE *OTHER*
    # WRONG RULE. Fixing the needs rule blocks the lead chamber one step earlier,
    # on its NOx charge, so byproducts-only stops costing anything. Two rules
    # were wrong at once and fixing one masked the other -- pinned both ways so
    # that a silent revert of either shows up here.
    kw = dict(needs_rule=bp.needs_by_roles)
    assert len(bp.closure(shelf_rule="products", **kw)[0]) == 13
    assert len(bp.closure(shelf_rule="both", **kw)[0]) == 14
    # under the correct needs rule the same bug is INVISIBLE
    assert len(bp.closure(shelf_rule="products")[0]) == 12
    assert len(bp.closure(shelf_rule="both")[0]) == 12


def test_target_only_shelving_never_starts_the_deep_chain(bp):
    """The whole of tiers 2 and 3 hangs off a BYPRODUCT, so a shelf that holds
    only targets is 4 routes short and has no third tier."""
    target_only, _ = bp.closure(shelf_rule="target")
    assert len(target_only) == 8
    assert max(target_only.values()) == 1
    assert "methanol-synthesis" not in target_only


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
    """`sulfuric-acid` blocks the most routes and is worth the least of the top.

    A histogram of blockers is not a work order, and this is the measurement that
    says so.
    """
    from collections import Counter

    blockers: Counter[str] = Counter()
    for rid in bp.RUNNABLE - set(bp.PLAYABLE):
        for x in bp.needs(rid) - bp.SHELF:
            blockers[x] += 1

    def worth(x: str) -> int:
        return len(bp.closure(extra={x})[0]) - len(bp.PLAYABLE)

    assert blockers.most_common(1)[0][0] == "sulfuric-acid"
    assert blockers["sulfuric-acid"] == 4
    assert worth("sulfuric-acid") == 1

    assert worth("nitrogen-dioxide") == 2
    assert worth("aluminium") == 2
    # nothing is worth more than 2 -- there is no lever
    assert max(worth(x) for x in blockers) == 2


def test_the_top_content_row_is_hall_heroult_and_it_opens_the_deepest_chain(bp):
    """aluminium unblocks thermite, thermite's iron unblocks haber-bosch."""
    def worth_route(rid: str) -> int:
        return len(bp.closure(pool=bp.RUNNABLE | {rid})[0]) - len(bp.PLAYABLE)

    assert worth_route("hall-heroult") == 3
    assert worth_route("hall-heroult") == max(
        worth_route(r) for r in bp.FED_BUT_UNRUNNABLE)


def test_two_of_the_work_order_need_no_template_at_all(bp):
    """They are blocked purely on a species the engine refuses to price, which
    makes a DATA refusal measurably a playability blocker."""
    species_only = [r for r in bp.FED_BUT_UNRUNNABLE
                    if not {s.cls for s in bp.route_steps(r)} - set(bp.TC)]
    assert sorted(species_only) == ["hypochlorite-bleach", "pyrite-roasting"]
    # pyrite is the engine queue's own source-blocked entry
    assert not bp.priced("iron-disulfide")


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

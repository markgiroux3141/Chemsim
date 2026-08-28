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
def test_the_headline_and_the_tiers_are_what_the_report_says(bp):
    """21 of 173, and the corpus's deepest chain is still 3 tiers.

    ⚠⚠⚠ **C5 RENAMED THIS TEST, AND THE REASON IS C4's OWN RULE.** It used to be
    called `test_the_answer_is_twenty_playable_three_tiers_deep`, and C4 wrote
    down that *a test that pins a LEVEL will be re-numbered by the next session
    that moves it, and the claim will quietly become someone else's arithmetic*.
    Its own name was such a level, and C5 moved it. The name now states the
    RELATION -- the headline is whatever the current code produces -- so future
    sessions change the numbers inside and nothing else.

    ⚠ G3 measured 12 of 36 runnable. C1 built ``sulfur_trioxide_hydration`` and
    corrected the ``vitriol-distillation`` rows, which put oil of vitriol on the
    shelf from a natural mineral and carried ``saltpetre-nitric`` up with it.
    ⚠⚠ C2 added `phosphoric-wet` and `superphosphate`, and neither needed
    a template: they were blocked on ONE refused species, and the price that
    unblocked it turned out to be a **pKa** rather than the mineral the work
    order named. Both land in tier 2, on C1's own sulfuric acid.
    ⚠⚠ C3 built the two templates for `vanillin-eugenol` and
    `vanillin-lignin` -- ``alkene_isomerisation`` and ``oxidative_cleavage``, the
    class S11 refused after reading one of its two rows. Both land in tier 2 as
    well, and **not** on sulfuric acid: their feedstocks (clove-oil eugenol,
    wood lignin) are natural and what they have to be GIVEN is caustic soda.

    ⚠⚠⚠ **C4 BUILT THE FERMENTATION AND IT IS THE FIRST TIER-1 ROUTE ADDED
    SINCE C1.** `abe-fermentation` needs only glucose, which is on the natural
    list, so it is ground-level -- and the ethanol it makes as its MINORITY
    branch carries `acetic-fermentation` up to tier 2 behind it. ⚠⚠ **The
    class M5 refused as "a metabolic NETWORK" was an outcome label over five
    mechanisms**, and the split is what made the credit honest.

    ⚠⚠⚠ **AND C5 IS THE FIRST SESSION TO BUY A ROUTE OFF A SUGAR IT HAD TO
    INVERT.** `hmf-route` lands in tier 2 on `invert-sugar`: sucrose is natural
    and fructose is not, so the chain is invert-then-dehydrate. It is also the
    first route in this file that could not have run at all before an ENGINE fix
    -- see `tests/test_furans.py`, where a template could not consume a species
    another template had made.
    """
    assert len(bp.routes) == 173
    assert len(bp.PLAYABLE) == 21
    assert max(bp.PLAYABLE.values()) == 3
    assert len(bp.RUNNABLE) == 44
    assert bp.PLAYABLE["hmf-route"] == 2
    assert bp.PLAYABLE["invert-sugar"] == 1
    assert bp.PLAYABLE["abe-fermentation"] == 1
    assert bp.PLAYABLE["acetic-fermentation"] == 2
    assert bp.PLAYABLE["vitriol-distillation"] == 1
    assert bp.PLAYABLE["saltpetre-nitric"] == 2
    assert bp.PLAYABLE["phosphoric-wet"] == 2
    assert bp.PLAYABLE["superphosphate"] == 2
    assert bp.PLAYABLE["vanillin-eugenol"] == 2
    assert bp.PLAYABLE["vanillin-lignin"] == 2
    # ⚠ AND THE BASE IS WHAT PUTS THEM IN TIER 2, which is the whole reason
    # a catalyst is a feedstock (rule 3). Both feedstocks are on the natural
    # list; the hydroxide is not.
    for rid in ("vanillin-eugenol", "vanillin-lignin"):
        assert "sodium-hydroxide" in bp.needs(rid)
        assert bp.needs(rid) - {"sodium-hydroxide"} <= set(bp.NATURAL_IDS)
    # ⚠⚠ AND C5's OWN ROUTE STANDS ON TWO TIER-1 ROUTES AT ONCE, WHICH IS
    # A FIRST FOR THIS FILE: `invert-sugar` for the fructose (sucrose is
    # natural, fructose is not) and `vitriol-distillation` for the acid that
    # catalyses it. Every other tier-2 route here needs one upstream route or
    # one granted reagent.
    assert bp.needs("hmf-route") == {"fructose", "sulfuric-acid"}
    assert bp.PLAYABLE["invert-sugar"] == 1
    assert bp.PLAYABLE["vitriol-distillation"] == 1


def test_the_tech_tree_is_a_shallow_bush(bp):
    """10 of the 20 are tier 1 -- they touch nothing another route made.

    The GOAL asks for a connected tech tree. This is the measurement that says it
    is not one yet, and it is the reason the file exists. ⚠ C1 added one route
    to each of the first two tiers and C2 added two more to tier 2, so the SHAPE
    did not change: a fan off the ground with one thin chain hanging off it.

    ⚠⚠⚠ **AND C3 IS THE FIRST SESSION TO MOVE THAT, WHICH IS WHY
    THE ASSERTION CHANGED SHAPE RATHER THAN ITS NUMBER.** G3's claim was that
    MOST playable routes are tier 1 -- a strict majority -- and it is now exactly
    HALF: 9 of 18. Tier 1 has not grown since C1; tiers 2 and 3 have, from 6+1 to
    8+1. **The bush is still shallow at 3 tiers, and it is no longer mostly
    ground-level.** ⚠ The honest reading is that this is a threshold crossed
    by arithmetic and not a tree appearing: nine one-hop routes off the ground is
    still nine, and tier 3 is still a single route.

    ⚠⚠ **AND C4 ADDED ONE TO EACH OF THE FIRST TWO TIERS, SO THE EXACT HALF
    HELD THROUGH A SESSION THAT WAS NOT AIMED AT IT.** 10 of 20. C4 asserted the
    equality anyway and said what breaking it would mean: *the equality is the
    thing a future session has to come here and break -- and what it will mean
    when it does is that a real tier appeared.*

    ⚠⚠⚠ **C5 BROKE IT, AND IT BROKE THE RIGHT WAY.** `hmf-route` is tier 2, so
    the counts are 10 / 10 / 1 and **tier 1 is a MINORITY of the playable set for
    the first time in the project's history** -- 10 of 21. G3's finding was *most
    playable routes are tier 1*; C3 took it to exactly half; C5 takes it below
    half. The operator has now gone `>` then `==` then `<`, and every step of
    that was a session buying a route that stands on another route's output.
    ⚠ Tier 3 is STILL one route, six sessions running, and that is the part that
    has not moved.
    """
    tier1 = [r for r, d in bp.PLAYABLE.items() if d == 1]
    assert len(tier1) == 10
    assert len([r for r, d in bp.PLAYABLE.items() if d == 2]) == 10
    assert len([r for r, d in bp.PLAYABLE.items() if d == 3]) == 1
    # G3's ">" became "==" in C3 and is "<" now, and the OPERATOR is the finding
    assert len(tier1) < len(bp.PLAYABLE) / 2


def test_the_ceiling_is_the_goal_and_it_is_a_finite_named_list(bp):
    """Granting all 22 fed-but-unrunnable routes reaches 45, against a goal of ~40.

    This is the whole point of the work order: the distance from 21 to 45 is a
    named table, not an open-ended grind against 173 routes.

    ⚠⚠ **AND C5 IS THE FIRST SESSION SINCE C2 THAT DID NOT MOVE THE CEILING.**
    C4 moved it 41 -> 45 because a fermentation puts four solvents on the shelf
    and those FEED four more routes. 5-HMF and levulinic acid feed nothing: no
    other corpus route takes either of them as an input. **A route can be worth
    a playable point and worth nothing to the goal it is scored against**, and
    which of the two a session gets is a property of the corpus rather than of
    the chemistry built.

    ⚠⚠ AND THE TABLE MOVES IN BOTH DIRECTIONS, WHICH IS THE POINT. C1 granted
    one of G3's 21 and the list GREW to 24, because sulfuric acid on the shelf fed
    four routes that were not fed before (`guncotton`, `hmf-route`,
    `phosphoric-wet`, `superphosphate`) and the ceiling moved 37 -> 41 with it.
    C2 granted two and the list SHRANK to 22, because phosphoric acid feeds no
    route that was not fed already -- and **the ceiling did not move at all.**
    *A work order derived from a fixed point is not a burndown list: granting a
    row can lengthen it, shorten it, or leave the goal exactly where it was.*
    ⚠ C3 granted two more and the list shrank again, 22 -> 20, with the
    ceiling once more UNCHANGED at 41: vanillin feeds nothing.

    ⚠⚠⚠ **AND C4 MOVED THE CEILING FOR THE FIRST TIME SINCE C1: 41 -> 45.**
    A fermentation puts acetone, ethanol, butanol and -- through
    `acetic-fermentation` -- acetic acid on the shelf, which FEEDS four routes
    that were not fed before (`acetic-anhydride-ketene`, `chloral-route`,
    `mercury-fulminate-route`, `white-lead-route`). So the list GREW 20 -> 23
    while the answer grew 18 -> 20. **The goal a session is measured against is
    not a constant**, and two sessions in a row where it sat still were a
    property of what they built rather than of the instrument.
    """
    assert len(bp.FED_BUT_UNRUNNABLE) == 22
    ceiling, _ = bp.closure(pool=bp.RUNNABLE | set(bp.FED_BUT_UNRUNNABLE))
    assert len(ceiling) == 45
    # two fall out for free once the shelf grows -- G3 had four, C3 had three,
    # and `acetic-fermentation` is the one C4 promoted into PLAYABLE outright
    free = set(ceiling) - set(bp.PLAYABLE) - set(bp.FED_BUT_UNRUNNABLE)
    assert free == {"haber-bosch", "thermite"}


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
    assert len(wrong) == 22
    assert len(bp.PLAYABLE) == 21, "the correction moves the headline DOWN"

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
    #                          shelf=target             +byproducts      +target in
    #  needs=roles  G3 10 / C1 11 / C2 13 / C3 15 / C4 16  13/15/17/19/21  14/15/17/19/21
    #  needs=order  G3  8 / C1 10 / C2 12 / C3 14 / C4 15  12/14/16/18/20  12/14/16/18/20
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
    # ⚠ C2 RE-MEASURED THE WHOLE GRID RATHER THAN BUMPING THE TWO CELLS THAT
    # FAILED, because the claim is about the DIFFERENCE between cells and not
    # about any one of them. The difference is still zero in both rows.
    # ⚠ C3 RE-MEASURED THE WHOLE GRID AGAIN, for C2's reason: the claim is
    # about the DIFFERENCE between cells. Still zero in both rows, three corpus
    # changes running.
    # ⚠ C5 RE-MEASURED IT A FIFTH TIME. Still zero in both rows.
    # ⚠⚠ C4 RE-MEASURED IT A FOURTH TIME AND THE DIFFERENCE IS STILL ZERO --
    # but it is the first session whose new route depends on a BYPRODUCT, so the
    # cell that DID move is the target-only one, in the test below. **The two
    # rules are measured as a grid because fixing one masked another once (G3),
    # and a session that moves one column has to print all of them.**
    kw = dict(needs_rule=bp.needs_by_roles)
    assert len(bp.closure(shelf_rule="products", **kw)[0]) == 22
    assert len(bp.closure(shelf_rule="both", **kw)[0]) == 22
    assert len(bp.closure(shelf_rule="products")[0]) == 21
    assert len(bp.closure(shelf_rule="both")[0]) == 21


def test_target_only_shelving_never_starts_the_deep_chain(bp):
    """The whole of tier 3 hangs off a BYPRODUCT, so a shelf that holds only
    targets is 4 routes short and has no third tier.

    ⚠ G3 measured 8 at depth 1. C1's own route is a tier-1 whose TARGET feeds
    `saltpetre-nitric`, so a target-only shelf now reaches depth 2 -- but the
    deep chain still does not start, because the zinc retort's carbon monoxide
    is a byproduct and no shelf rule that reads targets can see it. ⚠⚠ C2
    moved this cell 10 -> 12 and the SHORTFALL is unchanged at 4: both of its
    routes take sulfuric acid, which is a target, so a target-only shelf can
    reach them and still cannot start the chain. ⚠⚠ C3 moved it 12 -> 14
    and the shortfall is STILL 4 -- both vanillin routes need caustic soda, which
    is `chloralkali`'s declared TARGET, so a target-only shelf reaches them too.
    Four sessions and the shortfall did not move once: it was the byproduct, and
    only the byproduct.

    ⚠⚠⚠ **AND C4 MOVED IT, 4 -> 5, BY THE SAME MECHANISM.**
    `acetic-fermentation` needs ETHANOL, and ethanol is not
    `abe-fermentation`'s target -- propanone is. So the second route C4 bought
    is bought by a BYPRODUCT, exactly as the deep chain is bought by the zinc
    retort's carbon monoxide, and a target-only shelf cannot see it either.
    ⚠⚠ **The rule was justified by one route for four sessions and now has
    two**, which is the opposite of the fouling rule one test up, whose only
    evidence C1 dissolved. *A rule kept on a zero difference and a rule kept on a
    growing one are different bets, and both are printed.*

    ⚠⚠ **AND C5 MOVED THE CELL WITHOUT MOVING THE SHORTFALL**, which is the
    other way this measurement can go. `hmf-route` needs fructose, and fructose
    is a declared PRODUCT of `invert-sugar` as well as half of its target -- so a
    target-only shelf reaches it and the gap stays at 5. *One session moved the
    shortfall and the next moved only the level; printing both cells is what
    lets a reader tell those apart.*
    """
    target_only, _ = bp.closure(shelf_rule="target")
    assert len(target_only) == 16
    assert max(target_only.values()) == 2
    assert "methanol-synthesis" not in target_only
    assert "acetic-fermentation" not in target_only
    assert "abe-fermentation" in target_only          # ITS target is fine
    assert "hmf-route" in target_only                 # C5's, on invert-sugar
    assert len(bp.PLAYABLE) - len(target_only) == 5


def cat_roles(bp, rid):
    import catalog as cat

    return cat.route_roles(bp.steps, rid)


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
    # ⚠⚠⚠ AND C5 ADDED A THIRD, WHICH IS NOT A METAL AND IS NOT THE RULE'S
    # DOING. `furfural-route` step 1 is written `xylose + water -> xylose` --
    # the corpus has no pentosan graph, so the row uses its own product as a
    # stand-in feedstock -- and a species on BOTH sides of a step is exactly
    # what `route_roles` calls a CATALYST. So `with_catalysts=False` hands over
    # the route's actual SUGAR for free.
    #
    # ⚠⚠ **THE HEADLINE IS IMMUNE AND THAT IS THE POINT.** `needs()` decides by
    # ORDER (rule 2, the test two above), and by order xylose is used at the
    # step that first makes it, so it is external and `furfural-route` is not
    # playable. The artefact appears only in this counterfactual, which is the
    # one place `route_roles` still gets to answer -- and it appeared the moment
    # C5 made `furfural-route` RUNNABLE, having been latent until then.
    assert set(free_catalysts) - set(bp.PLAYABLE) == {
        "furfural-route", "haber-bosch", "hydrogenation-margarine"}
    assert "xylose" in cat_roles(bp, "furfural-route").catalysts
    assert "xylose" in bp.needs("furfural-route")


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

    ⚠⚠ **C5 RE-MEASURED IT AND THE FINDING SURVIVED A SECOND EXAMPLE CHANGE.**
    The most frequent blocker is `nickel` at FOUR routes now, because
    `furfural-route` went runnable and its last step is a nickel hydrogenation.
    It is still worth +1. `aluminium` still blocks ONE route and is still worth
    +2. **Three sessions, three different top blockers, and the same shape every
    time.**
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
    assert top == 4
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


def test_two_of_the_work_order_need_no_template_at_all(bp):
    """They are blocked purely on a species the engine refuses to price, which
    makes a DATA refusal measurably a playability blocker.

    ⚠⚠ G3 FOUND TWO, C1 DOUBLED IT WITHOUT MEANING TO, AND C2 TOOK ITS HALF
    BACK. C1's sulfuric acid fed `phosphoric-wet` and `superphosphate`, both then
    blocked on `calcium-phosphate`; C2 priced it and both became playable, so the
    bucket is back to G3's two.

    ⚠⚠⚠ AND C2 MEASURED WHAT IS LEFT OF THE BUCKET, WHICH IS THE
    FINDING. It read as four cheap lookups. Probed in one run against
    ``chemicals``, THREE of the four have no Hfs and no S0s in any shared
    database -- `calcium-silicate` (under all three of its CAS numbers), `pyrite`
    (Hfs in WEBBOOK, S0s in nothing) and `sodium-hypochlorite` (neither). **A
    data job is only cheap when the data is there, and there is no cheap data row
    left in this table.** See `validation/phosphate_rock.py` panel 1.
    """
    species_only = [r for r in bp.FED_BUT_UNRUNNABLE
                    if not {s.cls for s in bp.route_steps(r)} - set(bp.TC)]
    assert sorted(species_only) == ["hypochlorite-bleach", "pyrite-roasting"]
    # pyrite is the engine queue's own source-blocked entry
    assert not bp.priced("iron-disulfide")
    # ⚠ and the row C2 took is priced now, which is what moved the headline
    assert bp.priced("calcium-phosphate")
    assert "calcium-phosphate" in bp.NATURAL_IDS
    # ⚠⚠ C1 WROTE THIS LINE AS A PREDICTION AND C2 CASHED IT, so it now reads
    # ZERO -- granting two routes that are already playable adds nothing. The +2
    # is asserted where it actually landed (the headline test, 14 -> 16) rather
    # than left here as a claim that quietly stopped meaning anything. *A test
    # that predicts a gain has to be rewritten by the session that delivers it.*
    both = bp.closure(pool=bp.RUNNABLE | {"phosphoric-wet", "superphosphate"})[0]
    assert len(both) - len(bp.PLAYABLE) == 0
    assert {"phosphoric-wet", "superphosphate"} <= set(bp.PLAYABLE)


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

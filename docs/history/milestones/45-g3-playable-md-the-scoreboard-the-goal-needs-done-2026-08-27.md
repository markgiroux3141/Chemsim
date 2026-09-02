## G3 -- `PLAYABLE.md`, the scoreboard the goal needs ✔✔ **DONE 2026-08-27** *(and the answer is that the tech tree is a BUSH, not a tree)*

**WHAT IT IS.** `tools/build_playable.py` writes `data/catalog/PLAYABLE.md` (326
lines, ~50 s because it RUNS the deep chain) and `tests/test_playable.py` (18
tests) pins every headline in it. The question no other artefact asks:
*what can a player make, starting from what?*

    tier 1 -- from the ground                8 routes
    tier 2 -- one step up                    3
    tier 3 -- two steps up                   1     <- methanol, and that is all
    runnable but unfed                      24
    not runnable                           137
                                           173

**12 of 173 playable, against a GOAL of ~40, and the deepest chain is 3 tiers.**

### ⚠⚠⚠ 1. THE HEADLINE IS THE SHAPE, NOT THE COUNT: 8 OF THE 12 ARE TIER 1

The GOAL asks for a *connected tech tree*. This corpus is not a short tree; it is
a **fan of one-step routes off the ground with one thin chain hanging off it**.
Two thirds of what a player can make touches nothing another route made. That is
a different problem from "not enough routes" and it is the reason this artefact
had to exist rather than a bigger coverage number.

### ⚠⚠⚠ 2. THE DEEPEST CHAIN IN THE CORPUS RUNS THROUGH A BYPRODUCT, AND THE THIRD TIER IS ONE CATALYST

    zinc-smelting  1400 K  ->  zinc 0.032793 mol  AND  carbon monoxide 0.054290
      copper-smelting 1500 K on that CO  ->  copper 0.039995 mol
      water-gas-shift  700 K on that CO  ->  hydrogen 0.053445 mol
        methanol-synthesis 520 K, copper in the solid block -> 0.004154 mol

⚠⚠ **NOTHING ELSE A PLAYER CAN REACH MAKES CARBON MONOXIDE**, and the retort
makes MORE of it than of its own target. Three tier-2 routes and one tier-3 route
all want it. ⚠⚠ **AND METHANOL IS TIER 3 FOR EXACTLY ONE REASON: ITS CATALYST.**
Its CO is tier 1 and its hydrogen is tier 1 too (`chloralkali` throws hydrogen
off making caustic soda from rock salt) -- it is tier 3 only because **the copper
has to be smelted first, and smelting it needs the byproduct of smelting a
different metal.** Grant free copper and the corpus has no third tier at all.
⚠ *A catalyst is a tech-tree node, and treating one as free was measured at two
routes and one whole tier.*

### ⚠⚠⚠ 3. FOUR SCORING RULES, ALL FOUR MEASURED WRONG FIRST -- AND FIXING ONE MASKED ANOTHER

G4's rule (**the target may not be CHARGED**) was reused rather than re-derived;
it lives in `catalog.route_reachable` now and both audits call it. The three new
ones:

* **a need is decided by ORDER, not by `route_roles`** -- `lime-cycle` derives an
  EMPTY feedstock list because row 3 regenerates the limestone row 1 calcined, so
  a closed cycle scored playable while needing *nothing at all*;
* **a route shelves its target AND its byproducts**, target unioned in
  explicitly, because a route's target is not always among its products;
* **a catalyst is a feedstock**.

⚠⚠⚠ **AND THE INTERACTION IS THE FINDING.** Measured as a 2x3 grid: under the
CORRECT needs rule, shelving byproducts-only costs nothing (12 either way), so
the fouling-row bug is **invisible**; it is worth one route only under the wrong
needs rule (13 against 14). **Two rules were wrong at once and fixing the first
masked the second** -- had they been done in the other order, the shelf rule
would have looked like a distinction without a difference, gone in wrong, and
started costing routes silently the moment the lead chamber became reachable.
⚠ *Measure two suspected rules as a GRID, not as a list.*

### ⚠⚠ 4. THE SAME TWO CATALOG ROUTES BROKE THREE OF THE FOUR RULES, AND G4 HAD ALREADY FOUND ONE OF THEM

`lead-chamber` is in it twice. Row 4 (the nitrosylsulfuric acid that fouls a
chamber) is what made G4's ROW scorer call the route blocked -- and the same row
makes `route_roles` classify sulfuric acid as an INTERMEDIATE, so a shelf built
from products alone does not hold the thing the route exists to make. Row 2 then
wants nitrogen dioxide and row 3 makes it, so the **NOx carrier reads as an
intermediate when it is a starting charge** -- G4's own run had to hand it
0.004 mol by hand and measured it recovered.
⚠⚠ **AND THAT COSTS THE 18TH CENTURY ITS SULFURIC ACID.** `lead-chamber` is
blocked on a *pinch* of NO2 that nothing reachable makes; the corpus has
saltpetre as a natural material and **no step that turns it into NOx**, though
that is historically exactly where the charge came from. A **corpus** gap, and
one of the two most valuable single species in the file.

### ⚠⚠ 5. WHAT RUNNING IT BOUGHT, WHICH IS G1's QUESTION ANSWERED

⚠ **THE COPPER SMELTER IS ORE-LIMITED, NOT CO-LIMITED** -- doubling the retort's
CO moves the copper in the sixth decimal. That is the *opposite* of what the
contention above suggests and only running it settled which.
⚠ **THE CATALYST IS A GATE, NOT A MULTIPLIER** -- 0.01 mol of copper already
reaches 99.3% of the reference rate, so one ore charge is 4x more catalyst than
the route needs. A player must *reach* copper and need not stockpile it.
⚠⚠ **WHAT DOES BITE IS SCALE.** At the retort's own scale methanol converts at
**7.7%**; the same route, template and loading at the corpus's declared charge of
3 mol CO + 12 mol H2 gives **99.8%**. *"Reachable" and "worth doing" are
different questions and a static scoreboard can only answer the first.*
⚠ And the first version of the generator shadowed its own output buffer and wrote
a 200-byte file of route names. **`test_the_report_on_disk_matches_the_code`
caught it on its first run**, which is the whole argument for asserting a
generated artefact -- see §6.

### ⚠⚠ 6. THE ARTEFACT HAS TESTS, BECAUSE `ROUTE_INDEX.md` DID NOT

S3 found the route index stale by three milestones for one reason: no audit read
it. So `tests/test_playable.py` pins the headline, the tier shape, all four rules
*and their wrong answers*, the lever, and the fact that the file on disk is the
one the current code produces. ⚠ It does not diff the whole report --
`chemsim-generated-artefacts` records that a report which cannot be diffed is a
report nobody diffs -- it pins the numbers a reader would quote.

### ⚠⚠⚠ 7. THE DELIVERABLE IS A WORK ORDER, AND IT IS FINITE

**21 of the 137 unrunnable routes are ALREADY FED from natural materials.** Grant
all 21 and the fixed point reaches **37** playable -- the GOAL's own ~40, because
four more (`acetic-fermentation`, `haber-bosch`, `saltpetre-nitric`, `thermite`)
fall out free once the shelf grows. Ranked by what each is worth:

    +3  hall-heroult      1 class (molten-salt-electrolysis)  -- aluminium
                            unblocks thermite, whose iron unblocks haber-bosch
    +2  abe-fermentation, blast-furnace, iron-gall-ink, vitriol-distillation
    +1  the other sixteen

⚠⚠ **THE C-SERIES IS THIS TABLE AND NOT A GRIND AGAINST 173 ROUTES.** The other
116 move a coverage number no player can reach. ⚠ **AND THE TWO RANKINGS
DISAGREE**: `COVERAGE_REPORT.md`'s greedy curve maximises classes per template;
this maximises routes a player can walk to.
⚠ **TWO OF THE 21 NEED NO TEMPLATE AT ALL** -- `hypochlorite-bleach` and
`pyrite-roasting` are blocked purely on a refused price, and pyrite is the engine
queue's own source-blocked entry (enthalpy in WEBBOOK, entropy in nothing).
**A data refusal is now measurably a PLAYABILITY blocker and not just a coverage
one.**

### ⚠⚠ 8. NO LEVER, AND THE FREQUENT BLOCKER IS NOT THE VALUABLE ONE

The biggest single species grant is **+2** (`nitrogen-dioxide`, `aluminium`) --
the same shape as coverage's "no lever". ⚠⚠ And `sulfuric-acid` **blocks the most
routes (4) and is worth +1**, because every route it blocks is blocked by
something else too. *A histogram of blockers is not a work order; the fixed point
is, and they disagree.*

### ⚠ 9. THE HAND JUDGEMENT, PRINTED

45 species are declared NATURAL in three groups with a sourced reason each, and
the rule is stated: obtainable without running any chemistry. **The GOAL says
~10, so the list is generous by 4x and 12 is an UPPER bound.** What is
deliberately NOT natural is printed too, because that half is the arguable half:
the catalyst metals, the metals as opposed to their ores, methane, the
benzaldehyde bottle, and the fermentation products.

*The original brief follows.*

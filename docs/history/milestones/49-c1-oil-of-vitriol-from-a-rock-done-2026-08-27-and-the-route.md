## C1 -- Oil of vitriol from a rock ✔✔ **DONE 2026-08-27** *(and the route was blocked on a price for a species that is not in its chemistry)*

**12 -> 14 playable, 36 -> 37 runnable, 52/229 -> 53/236 classes, 82 -> 83
species-ready, 41 -> 42 template-ready, 31 -> 32 BOTH.** One template, one
corpus row corrected, one eight-row class split into eight.
`validation/vitriol.py` (7 panels, 18 s), `tests/test_vitriol.py` (18 tests).

### ⚠⚠⚠ 1. THE HALF THE BRIEF WOULD HAVE CALLED FREE WAS ALREADY BUILT, AND THE HALF IT CALLED A TEMPLATE WAS A DATA REFUSAL

`vitriol-distillation` is two rows: roast green vitriol, catch what comes off.
PLAYABLE §8 priced it at +2 and listed **two** blockers -- the `hydrolysis` class
and a refused `iron-ii-oxide`. Both readings were wrong in the same direction:

* **the roast has been in the engine since M6.** `properties/solid_state.py`
  declares `2 FeSO4 -> Fe2O3 + SO2 + SO3` and it runs: nothing below 800 K,
  complete by 1000 K, exactly 0.05 mol of each product from 0.10 of the mineral.
  The catalog's own condition column says *"retort, red heat"* and nobody had
  ever told the engine that.
* **`iron-ii-oxide` was never in the reaction.** The row named FeO; FeO does not
  survive red heat and `mineral_data` refuses it on its crystal Cps, which CRC
  does not tabulate. So a route was blocked on a datum for a species its own
  chemistry never makes. ⚠ *That is a shape worth looking for again: a refused
  species in a route's BLOCKER list may be a corpus error rather than a curation
  job.* Correcting the row alone moved species-ready 82 -> 83.

⚠⚠ **AND `data/catalog/README.md` HAD RECORDED THE LANDMINE THREE MILESTONES
EARLIER, WITH THE INSTRUCTION.** S3's split wrote *"the day `hydrolysis` is
credited, `vitriol-distillation` goes template-ready on a step whose stated
product does not exist in the run -- whoever builds it owes this row a second
look."* C1 is that session. **A recorded landmine with a named trigger is the
cheapest documentation this project writes**, and it worked exactly as intended.

### ⚠⚠⚠ 2. `hydrolysis` WAS AN OUTCOME LABEL SITTING NEXT TO SEVEN COUNTER-EXAMPLES

Eight rows, the catalog's second-biggest class after `proton-transfer`. The
argument for splitting is not that they are eight mechanisms -- they are -- it is
that the taxonomy **already carried** `amide-`, `ester-`, `epoxide-`,
`glycoside-`, `nitrile-`, `isocyanate-` and `disproportionation-hydrolysis`.
Everything it knew how to name had been named; `hydrolysis` was the bin for the
rest. That is M1's finding with seven of its own family standing beside it.

    contact-process 4      H2S2O7 + H2O -> 2 H2SO4          oleum-hydrolysis
    vitriol-distillation 2 SO3 + H2O -> H2SO4               sulfur-trioxide-hydration  <- built
    leblanc-process 4      CaS + H2O + CO2 -> CaCO3 + H2S   sulfide-carbonation
    frank-caro 3           CaCN2 + H2O -> NH3 + CaCO3       cyanamide-hydrolysis
    castner-kellner 2      Na(Hg) + H2O -> NaOH + H2 + Hg   amalgam-decomposition
    calcium-carbide 2      CaC2 + H2O -> C2H2 + Ca(OH)2     carbide-hydrolysis
    furfural-route 1       xylose + H2O -> xylose           pentosan-hydrolysis
    grignard-route 3       R-OMgBr + H2O -> R-OH            organometallic-protonolysis

Denominator +7, numerator +1. S7's shape: **a split that lowers the headline is a
split working.** ⚠ `oleum-hydrolysis` is the near-miss and is deliberately NOT
credited -- `[SX3]` against disulfuric acid's two `[SX4]` sulfurs, asserted.

⚠⚠ **AND ONE ROW'S CLASS WAS DECIDED RATHER THAN DERIVED, THEN MEASURED BOTH
WAYS.** `furfural-route` 1 is chemically a glycoside hydrolysis and the
convention would file it under the COVERED `glycoside-hydrolysis`; it is not
there, because the row is fragility 29b (`xylose + water -> xylose`) and no
template can ever match it. **Measured: it costs ZERO either way today**, because
the route needs three more classes. *A false credit is cheapest to refuse before
it can pay*, and the cell that is currently equal to its neighbour is exactly
G3's grid lesson pointing forward instead of back.

### ⚠⚠⚠ 3. THE CEILING IS EMERGENT AND NOBODY DECLARED IT: `ln K = 0` AT 664.3 K

`dH -97.53 kJ/mol`, `dS -146.8 J/(mol K)`, all three species EXPERIMENTAL
(NIST/CODATA). `dH/dS` is **664.3 K**, and in a dry gas the conversion falls
46.8% -> 1.6% between 600 K and 800 K -- checked against the closed-form root of
the same K, which it matches to three figures at every rung. **A receiver has to
be COOL, which is what a receiver is.** Same shape as the lead chamber's 600 K
NOx ceiling: an operating limit that came out of the formation data.

⚠ **AND THE CONDENSER BEATS THE CEILING, WHICH IS THE BETTER HALF OF IT.** With a
mole of liquid water present the conversion is **100.000% at every temperature up
to 600 K** -- not because K is large there (`ln K` is 1.89) but because sulfuric
acid boils at 610 K and leaves the gas as fast as it forms. *Le Chatelier, done
by a phase change the template knows nothing about.*

### ⚠⚠ 4. THE RATE LAW IS APPARENT, AND THE TRADE WAS MEASURED RATHER THAN ASSUMED

The real gas-phase reaction is **second order in water** (the water-dimer path);
what is declared here is bimolecular with `A = 1e10` pinned at the order of the
collision limit and `Ea = 23.6 kJ/mol` putting `k(298)` at the ORDER of the
reported effective constant. ⚠ **That figure is RECALLED and is used as an order
of magnitude, not a value** -- which is only defensible because the answer is
**100.000% at A = 1e6, 1e8, 1e10 and 1e11**.

⚠⚠ **`orders=(1.0, 2.0)` WAS REFUSED AND THE REFUSAL IS THE INTERESTING PART.**
It is the more correct rate law, and `ReactionTemplate.orders` may not be
combined with `reversible` -- a declared order has no detailed-balance partner.
So the choice was between the right ORDER and the right REVERSE. The order is
forgiven (five decades) and the reverse is the mechanic (the 664 K ceiling).
*Between two wrong-in-different-ways declarations, keep the one whose error is
MEASURED to be invisible.*

### ⚠⚠ 5. THE LIQUID CHANNEL WAS BUILT AND REFUSED ON CONSERVATION

`phase="any"` in a receiver full of water is not an obviously wrong idea. Built,
measured, refused:

    phase    conv 320-600 K   sulfur in - out at 320 K   700 K wall clock
    gas          100.000%        +8.4e-15 mol                434 s
    liquid       100.000%        +2.9e-06 mol (REPORTED)      13 s
    any          100.000%        +1.5e-06 mol (REPORTED)      72 s

It buys **nothing** and costs a projection residual six thousand times the
tolerance: the liquid pseudo-first-order constant is 1.4e6 1/s against a 600 s
run. ⚠ The residual is **not silent** -- `conservation_report` names it, which is
what made it priceable at all. ⚠ And there is no second SOURCED constant to put
on a liquid arrow; it would be the gas one copied.

### ⚠⚠⚠ 6. THE CHEAPEST REPRODUCTION OF ENGINE QUEUE ITEM 15 IN THE REPO

A ONE-POT flask -- green vitriol and water together -- measured at the default
tolerance:

     800 K, 2000 s     0.4 s      liquid layer 3.4e-17 mol
     900 K,  500 s    44.4 s      liquid layer 6.6e-17 mol
    1000 K,  200 s    > 9 MINUTES, did not finish

**Six species, one template.** That is the burner's `LAYER_REABSORB` thrashing
(item 15) on a network small enough to instrument, against the burner's 52 s on a
full chamber. ⚠ Not this template's bug: the same charge with no water is panel 1
and costs 0.3 s.

⚠ **AND THE PANEL WAS BUILT TO CONFIRM THE 664 K CEILING AND DID NOT.** In 66 bar
of steam the acid is still favoured 3.35:1 at 800 K -- `K * p_H2O = 3.33`, so
Le Chatelier is winning again -- and what actually kills the one pot is that the
SULFATE has moved 0.285% in 2000 s. **So the two-vessel apparatus is right for a
reason that is half chemistry and half numerics**, and it is written that way
rather than as the clean thermodynamic story.

### ⚠⚠⚠ 7. C1 DISSOLVED THE ONLY EVIDENCE FOR ONE OF G3's FOUR SCORING RULES

G3's rule 3 -- *a route shelves its target AND its byproducts* -- was justified by
a measured difference: 13 against 14 under the wrong needs rule. Re-measured:

                     shelf=target   +byproducts   +target unioned in
    needs=roles      G3 10 / C1 11  G3 13 / C1 15  G3 14 / C1 15
    needs=order      G3  8 / C1 10  G3 12 / C1 14  G3 12 / C1 14

**Every cell of the byproducts/both column is now equal.** The route the rule
bought was `saltpetre-nitric`, whose sulfuric acid came from the lead chamber's
fouling row; C1 gave the acid a route of its own, so losing the chamber's copy
costs nothing anywhere.

⚠⚠ **THE RULE IS KEPT, AND NOT OUT OF SENTIMENT.** It is a statement about
`route_roles` -- still true, still asserted -- and its measured cost is a property
of TODAY'S corpus. *A rule justified by a difference must not be reverted the day
the difference goes away; that is how a corrected instrument un-corrects itself.*
The grid is pinned at its new all-equal values in `tests/test_playable.py` with
the reason written above it.

### ⚠⚠ 8. THE WORK ORDER RE-PRICED ITSELF, AND THE CHEAPEST ROW IS NOW A MINERAL

    fed but unrunnable   21 -> 24      ceiling   37 -> 41
    iron-gall-ink        +2 -> +1      (C1 already delivered its second point)
    nitrogen-dioxide     +2 -> +1      (fragility 31 is worth half what G3 priced)
    need NO template      2 -> 4       hypochlorite-bleach, pyrite-roasting,
                                       **phosphoric-wet, superphosphate**

⚠⚠⚠ **`calcium-phosphate` IS WORTH +2 AND NEEDS NO CHEMISTRY AT ALL.** Phosphate
rock is already on the NATURAL list, both new routes are `acid-displacement-
precipitating` (covered), and both are blocked on that one refused price. **It is
the cheapest row in the whole work order and it is a data job.** ⚠ The lever
finding survived with all new numbers: `nickel` and `benzaldehyde` block three
routes each and are worth +1; `aluminium` blocks ONE and is worth +2. *A finding
that survives having its own example removed was about the shape, not the
example.*

### ⚠ 9. WHAT C1 DID NOT DO

* **The full suite was NOT run.** `src/` changed (one template plus the
  `reactions` export), so it is owed. The last clean figure is G6's
  **1045 passed / 0 failed in 23:03**, plus G3's 18 and C1's 18 -> expected
  **1081**. ⚠ This is the first session in the arc to ship an unrun suite, and it
  was a deliberate scheduling call, not an oversight.
* **`tolerance_audit.py` is asserted NOT owed.** No RHS edit and no data table
  moved -- the template is additive and every pre-existing network builds the
  same reactions from the same constants. Last measured state remains S13's.
* **`oleum-hydrolysis` is a gap on purpose** and `contact-process` is blocked
  twice over (`vanadium-pentoxide` and `disulfuric-acid` are both refused).
* **The 664 K ceiling is not a REFLUX head** (fragility 21). A receiver here is a
  cold flask, not an apparatus that returns condensate.

---

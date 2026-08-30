# The tech tree: what can you make starting from a rock?

Chapter 29's reports ask whether the *engine* can do a reaction and whether the
*corpus* has a route. Neither asks the question a player would ask.

`PLAYABLE.md` does, and it is the only artefact in the repository whose
generation actually **runs** chemistry.

## The answer

| tier | routes | meaning |
|---|---:|---|
| **1 --- from the ground** | 10 | every feedstock and every catalyst is a natural material |
| **2 --- one step up** | 10 | needs the output of a tier-1 route |
| **3 --- two steps up** | 1 | needs the output of a tier-2 route |
| *runnable but unfed* | 23 | the engine can run it; nothing can supply it |
| *not runnable* | 129 | see the coverage report |
| | **173** | |

**21 of 173 named routes are playable from natural materials**, against a stated
goal of about 40. The deepest chain in the corpus is **three tiers**.

::: {.keypoint title="The tech tree is a shallow BUSH, not a tree"}
Ten of the 21 playable routes are tier 1 --- they touch nothing another route
made. The corpus is not a connected progression that happens to be short; it is
a **fan of one-step routes off the ground with one thin chain hanging off it.**

That is a different problem from "not enough routes", and it changes what to
build: the shortage is *connections*, not leaves.
:::

## The one hand judgement, printed so it can be argued with

**A species is NATURAL if a player could obtain it without running any chemistry**
--- dig it, pump it, breathe it, press it out of a plant, or scrape it off an
animal. Nothing about the engine or the catalog decides this. It is a
game-design decision about where the tech tree starts, and it is the single input
that most changes every number in the file.

45 species are declared natural, in four groups:

- **air and water** (4): CO₂, N₂, O₂, water.
- **native elements and rocks you can dig** (26): limestone, gypsum, rock salt,
  pyrite, galena, cinnabar, sphalerite, haematite, pyrolusite, saltpetre, native
  sulfur, graphite, gold, silver, fluorspar, cryolite, sand, bauxite, phosphate
  rock, borax, magnesite, anhydrite, covellite, pyrrhotite, melanterite, Chile
  saltpetre.
- **pressed, fermented or scraped off something living** (15): turpentine's
  $\alpha$-pinene, clove oil's eugenol, citronellal, glucose, cellulose, hide
  collagen, coal.

The goal says ~10, so this list is already generous by a factor of four --- and
therefore **21 is an upper bound on playability, not a lower one.**

## The deep chain, run end to end

This is the part that could not be answered by a static scorer, and running it
produced four findings.

**Tier 1 --- the zinc retort.** 10 L sealed, 1400 K. Sphalerite plus graphite
plus air:

| species | mol | |
|---|---:|---|
| zinc | 0.032793 | the target |
| **carbon monoxide** | **0.054290** | **a byproduct, and the whole of tiers 2 and 3** |
| sulfur dioxide | 0.032793 | a byproduct |

::: {.keypoint title="The retort makes more carbon monoxide than zinc, and nothing else makes any"}
It is the only carbon-monoxide source a player can reach; it is **not charged**
--- carbon burns in the blast and the Boudouard reaction hands the CO back --- and
**three tier-2 routes and one tier-3 route all want it.**

A reachability scorer says "carbon monoxide is on the shelf" and attaches no
quantity to that at all.
:::

**Tier 2 --- the copper smelter, on the retort's own CO.**

| CO charged | copper |
|---:|---:|
| 0.054290 (one retort) | 0.039995 |
| 0.108580 (two retorts) | 0.039996 |

Doubling the CO changes the copper in the sixth decimal, so this charge is
**ore-limited, not CO-limited**. That is the *opposite* of what the contention
above suggests, and only running it settles which.

**Tier 2 --- the water-gas shift, on the same CO.** Gives 0.053445 mol hydrogen
--- and **consumes** the carbon monoxide to get there. The shift, the smelter and
the methanol synthesis are not three routes sharing a shelf entry; they are three
claims on one retort's gas.

**Tier 3 --- methanol, where the catalyst is the gate.**

| copper / mol | methanol / mol | conversion |
|---:|---:|---:|
| 0 | 0.000000 | **nothing at all** |
| 0.0001 | 0.000209 | 0.38% |
| 0.0010 | 0.001669 | 3.08% |
| 0.0100 | 0.004127 | 7.60% |
| 0.039995 | 0.004154 | 7.65% --- *smelted at tier 2* |
| 0.1 | 0.004157 | 7.66% |

::: {.keypoint title="The entire third tier of this corpus is one copper catalyst"}
Methanol needs no tier-2 *reagent*: its carbon monoxide is tier 1, and its
hydrogen is tier 1 too, because the chlor-alkali cell throws hydrogen off as a
byproduct of making caustic soda from rock salt.

It is tier 3 for exactly one reason --- **its catalyst has to be smelted first,
and smelting it needs the byproduct of smelting a different metal.** Grant a
player free copper and methanol moves to tier 2 and the corpus has no third tier
left.
:::

And the gate **saturates well below the smelter's output**: 0.01 mol of copper
already reaches 99.3% of the reference rate, so one ore charge yields about four
times more catalyst than the route needs. The catalyst is a *gate*, not a rate
multiplier, so a player needs to *reach* copper and does not need to stockpile
it.

::: {.keypoint title="What does bite is SCALE, and it is the point of running any of this"}
At the retort's own scale the methanol conversion is **7.7%**. The same route,
same template, same catalyst loading, at the corpus's own declared charge of
3 mol CO + 12 mol H₂ gives **2.994 mol --- 99.8%.**

Methanol synthesis is pressure-driven, and one zinc retort is not a pressure
vessel.

**"Reachable" and "worth doing" are different questions, and a static scoreboard
can only answer the first.**
:::

## A warning printed on every number in that file

::: {.trap}
Every yield in `PLAYABLE.md` is a property of *the declared constants on the day*
and of *the conditions beside it*, not of the route. One milestone changed no
species, no template and no route, and moved one substrate's rate by
**2400$\times$** while leaving three nitration yields identical to four decimal
places.

A yield there is evidence that a route **works**. It is not a corpus property,
and it will move under sessions that were not about it.
:::

## Measuring the scoreboard itself

The scoring rules are hand-written judgements, and a granularity audit went
looking for how wrong they are.

::: {.keypoint title="The BOTH column understates by five, and five is SMALL"}
137 of 142 gaps are real work. That is the useful finding: the instrument is
approximately right, so the queue it produces can be trusted.
:::

Three specific faults, all caught by *running* things rather than by reading:

::: {.trap title="1. The scorer scores ROWS while a route is a DAG"}
A route is a directed graph of steps with shared intermediates. Scoring it as a
list of rows loses the structure, and structure is exactly what tier depth is.
:::

::: {.trap title="2. A scorer that lets you charge the TARGET credits every recycle loop"}
If the feasibility check may charge the route's own product as a reagent, then
any route with a recycle loop trivially passes. Three false credits came from
this, and all three were caught by running the route rather than by scoring it.
:::

::: {.trap title="3. Fixing one scoring rule MASKED another"}
Two rules were wrong. Fixing the first hid the second, because the first's error
compensated for it. **Measure two rules as a grid**, not one at a time --- which
is the same reasoning as the three-point tolerance sweep in Chapter 20.
:::

## What the queue looks like now

The project's current work order is a per-class table in `PLAYABLE.md` §8b:
22 rows, projected to take playability from 21 to about 45.

Six sessions have worked through it --- oil of vitriol from a rock, phosphate
rock digested in sulfuric acid, vanillin from clove oil, the ABE fermentation,
the sugar-to-furan dehydrations --- and the shape of the findings has been
consistent enough to be worth stating as a pattern:

::: {.keypoint title="What a content session actually finds"}
1. **The blocker is rarely where the work order says.** One route was blocked on
   a *price for a species that is not in its chemistry*; another on a pKa sitting
   in a different table entirely.
2. **A class refused in an earlier session is often refused on the evidence of
   one of its two rows.** This happened three sessions running.
3. **A +0 row is what makes the +1 row mean anything.** Doing the work that
   changes no headline number is how you find out that the headline number is
   measuring the right thing.
4. **Granting a work-order row makes the work order longer**, because a newly
   reachable route unblocks routes that then become visible as blocked.
:::

And one finding from that series that is pure engine, and the best single
illustration of why an integration test is not enough:

::: {.trap title="The engine could not ferment sugar it had inverted itself"}
A flag on the template machinery meant a template could not run on a species that
*another template had made*. Invisible to every single-template test, because
every such test charges its own substrate.

Removing it removed an accidental generation cap, exposed a preparation that was
making an ester in caustic soda, and turned up a green test that had been resting
on the order of two identical rows.
:::

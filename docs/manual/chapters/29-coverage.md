# Measuring how much chemistry this covers

## Why there is a corpus

"How much chemistry does this simulator cover?" is the question that decides
what to build next, and it is very easy to answer by feel and be wrong.

So `data/catalog/` holds a hand-authored corpus: **1,583 compounds and 173 named
synthetic routes over 377 steps**, from the lime cycle and Tyrian purple through
the lead chamber and Leblanc to the Hock process, SOHIO ammoxidation and PLA.

::: {.keypoint}
It is **data, not code**. Nothing in `src/chemsim` imports it. It exists to be
pointed at the simulator, and the numbers it produces are deliberately
unflattering.
:::

```
python tools/catalog.py                # structural validation
python tools/build_route_index.py      # feedstocks -> intermediates -> products
python validation/catalog_coverage.py  # the audit
python tools/build_playable.py         # the tech tree (runs things; ~1 min)
```

## Three reports that answer three different questions

::: {.trap title="And they are routinely confused for one"}
| report | asks | is a property of |
|---|---|---|
| `COVERAGE_REPORT.md` | *can the engine do this chemistry?* | the **engine** |
| `ROUTE_INDEX.md` | *what is a feedstock here?* | the **corpus** |
| `PLAYABLE.md` | *can a player get to it from a rock?* | **neither** |

The third is neither, because a route's yield was measured moving **4.5$\times$**
on a change that touched no species and no template.

**A route can be fully covered, fully indexed, and unreachable.**
:::

## Three readiness tests, and the one to quote

A route is judged on three independent questions:

- **species-ready** --- does every species in it resolve to a full property set?
- **template-ready** --- is there a template for every reaction class it uses?
- **BOTH** --- the intersection.

![The funnel, and it is not a funnel.\label{fig:playable}](figures/playable.pdf)

| | routes |
|---|---:|
| named routes in the corpus | 173 |
| species-ready | 85 |
| template-ready | 46 |
| **BOTH --- the one to quote** | **38** |
| playable from natural materials | 21 |

::: {.keypoint title="46 is not what could run; 38 is --- and even 38 is an upper bound"}
The three columns answer **independent** questions and the smallest does not
bound the others: a route needs a template for every step *and* a price for every
species. **Eight of the 46 template-ready routes have a refused species** and
cannot run.

Nothing computed the intersection until milestone S6.

And 38 is an *upper bound on what runs*, not a measured count: a class is
credited when a template would fire on the right substrate **at all**, which is
not the same as running. One route is the standing proof of that difference.
:::

## Five instrument findings, which are the real content

The coverage audit has been wrong more often than the engine has, and each
correction is a lesson about measuring your own work.

::: {.trap title="1. A reaction class must name a MECHANISM, not an outcome"}
A template is *SMARTS on a mechanism*. So a class named for what a step
*achieves* cannot answer "is there a template for this", and four classes in the
original corpus were outcome labels spanning several mechanisms each. **32 rows
were re-labelled** to the mechanism their own reactants and products show.

The cost of not doing it: crediting six proton-transfer templates was supposed to
take covered steps from 21 to 46 in one line. That arithmetic needed
`deprotonation` (6 steps) to be proton transfer. **Five of its six rows are
carbanion generation** --- precisely the capability with no template. Crediting
the class would have made the audit *less* truthful.

Two rules follow. **The class says what the mechanism is; whether a reagent is
priced is a species question**, counted separately, or one gap is double-counted
as two. And **a step's NAME can lie; its reactants cannot** --- one route's step 1
is called "alkoxide formation" and reads `phenol + NaOH -> sodium-phenoxide`,
which is a phenoxide, which *is* covered.
:::

::: {.trap title="2. The class denominator MOVES, and that is correct"}
Because a class is a mechanism claim, reading a class's rows sometimes splits it:
the denominator went 212 $\to$ 224 over five milestones and is 240 now. A
coverage percentage whose denominator is itself a live measurement has to be
quoted with its date.

One split had a **negative** effect on the headline --- `combustion` turned out
to be six rows and five mechanisms, credited since the first milestone to a
template that fires on two of them --- and that is a split doing its job.
:::

::: {.trap title="3. species-ready was blind to a whole provider"}
It asked only the three ideal-gas providers, which refuse an ionic lattice **by
name and correctly**. But `mineral_data` had been pricing those on the solid
basis for milestones. 19 compounds and 16 routes moved on that one line ---
including a route the project had already declared complete and whose example
ran (Chapter 17).
:::

::: {.trap title="4. The recorded size of a gap was itself wrong, by 60%"}
Twice. Once because a comparison was made on *raw* rather than canonical SMILES;
once because a tier classifier was **parsing prose** out of provenance strings,
which the properties layer had already written down would fail.

An instrument's own output is data and needs the same auditing as the thing it
measures.
:::

::: {.trap title="5. Nothing had ever checked that a catalog row BALANCES"}
**75 of 367 rows do not.** The corpus is hand-authored data and had never been
subjected to the conservation check that every template has passed since Layer 3
was written.
:::

## And two findings about generated files

::: {.trap title="ROUTE_INDEX.md was stale by three milestones and nobody noticed"}
It is the one generated file no audit reads --- the coverage audit parses the
raw route steps directly --- so a stale index changes no measured number and
produces no failure. It had not been regenerated since the initial commit while
the underlying data was re-labelled three times. Regenerating it moved **21 class
labels**.

Anyone who read that index to find a step's class over that period got a stale
answer, silently.
:::

::: {.trap title="And COVERAGE_REPORT.md was not byte-stable"}
`sorted(covered, ...)` sorted a *set* with no tie-break, so regenerating it
produced about 17 lines of `PYTHONHASHSEED` noise with every number identical ---
enough to hide a real one-line change in review, which is what regenerating it is
*for*.

It is now byte-identical across hash seeds. If a regeneration ever produces a
diff again, that diff is real.
:::

## The finding the report itself does not give

The coverage report ranks missing classes by **frequency**. That is the wrong
ranking for deciding what to build, because a class used in many routes may
unlock none of them --- those routes each need three other things too.

Ranked by **marginal unlock** instead:

- 127 routes have at least one gap, and **44 of them are one class away ---
  from 35 different classes.**
- The best single class unlocks **3 routes** on the template column, and
  **2** that could actually run.
- Twelve templates take template-ready from 46 to 68, and the gain falls away
  fast after the first few.

::: {.trap title="And that curve optimises the OVERSTATED column"}
Its totals are template-ready, and a route also needs every species priced. Its
top three rows are `isomerisation` at +3 unlocked / **2 runnable**,
`catalytic-air-oxidation` at +3 / **1**, and `pyrolysis` at +2 / **1**.

So the greedy curve's own ordering is *not* the work order --- which is why the
report prints a `RUNNABLE` column beside the `ALONE` column and says to read the
second one.
:::

And the two rankings barely overlap:

| ranked by routes it would make RUNNABLE | ranked by steps it covers |
|---|---|
| isomerisation (2) | nucleophilic-substitution (6 steps) |
| catalytic-air-oxidation (1) | radical-polymerisation (6) |
| metal-ion-aldehyde-oxidation (1) | carbanion-generation (5) |
| molten-salt-electrolysis (1) | polycondensation (5) |

Several of the most-used missing classes unlock **zero** routes on their own,
because the routes needing them each need three other things too.

::: {.keypoint title="There is no lever"}
"Full template coverage" is a ~150-template grind **with no bottleneck to
attack**. Twenty templates in one milestone took the route count from 7 to 25,
and the reason it took twenty rather than five is the finding: *the gap is a long
tail*. Before that milestone, 63 routes sat one class away from 50 distinct
classes; today 44 sit one class away from 35.

Eighteen routes cost twenty templates, and the next eighteen will cost about the
same. So: **plan for a target ("twenty playable routes"), never for
completeness.**
:::

## The species side pays as a multiplier, not as a headline

One more measured shape, and it changed how work is scheduled.

Curating nine bare elements moved `species-ready` from 63 to 77 and moved the
intersection by **exactly zero** --- and that was *predicted before it was done*,
because none of the 15 routes it unblocked were template-ready.

What it did move is the **shape** of the queue: six reaction classes went from 0
runnable routes to 1, and one went from 1 to 2.

::: {.keypoint}
Species work is a **multiplier on template work** rather than a headline of its
own. A species job should follow its template, not precede it.
:::

## The finding the coverage report does not give: there is no lever

The report ranks missing classes by frequency, which is the wrong ranking for
deciding what to build. Ranked by **marginal unlock** instead:

* 61 routes are **one class** away — from **46 different classes**.
* The best single template unlocks **6 routes (3%)**.
* The best **twelve** templates reach **31/173 (18%)**.

And the two rankings barely overlap. The most-used classes (`acid-base`,
`catalytic-hydrogenation`, `hydrolysis`) unlock **zero** routes on their own,
because those routes each need three other things too.

| ranked by routes unlocked | ranked by steps covered |
|---|---|
| catalytic-air-oxidation (6) | acid-base (15) |
| acid-displacement (6) | catalytic-hydrogenation (10) |
| electrolysis (6) | hydrolysis (8) |
| redox (6) | deprotonation (6) |

**"Full template coverage" is a ~150-template grind with no bottleneck to
attack.** Plan for a *target* ("twenty playable routes"), never for completeness.

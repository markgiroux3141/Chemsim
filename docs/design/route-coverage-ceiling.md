# 173 is not the target; about 66 is, and the gap is twenty routes

Derived 2026-09-13 from `data/catalog/` with the script at the foot of this
file. Nothing here is typed from memory. The question it answers is the one the
scoreboard invited and never addressed: **if the project kept going, where does
route coverage stop?**

## The three bars, and where each one tops out

A route is credited only when every step has a template **and** every species
has a price. Those are independent questions and neither bounds the other.

| | today | ceiling | what caps the ceiling |
|---|---:|---:|---|
| template-ready | 46 | **110** | 7 routes name a species with no molecular graph — a rock, an alloy, a mixture, a protein. 14 reaction classes are credited to integrator terms (calcination, roasting, precipitation and the rest) where a lattice is not a graph and no SMARTS can exist. The remaining routes have at least one step that does not balance, so there is no stoichiometry for a template to carry. |
| species-ready | 90 | not derived here | the pricing half; `COVERAGE_REPORT.md` owns it |
| **intersection** | **40** | **~66** | T1.0, 2026-09-02: 44 of the 110 would still hold a species nothing can price |
| runnable | 47 | — | `PLAYABLE.md` scores this separately and more strictly |

So the honest headline is **47 of ~66**, not 47 of 173. The remaining gap is
about twenty routes. It is bounded, it is countable, and it has an end.

## Why the curve went flat

`template-ready` climbed 38 → 46 between 2026-08-26 and 2026-08-28 and has not
moved since — 43 commits and 24 sessions at the time of writing. That is not a
stall, it is the hand-written template supply running out: every reaction class
cheap enough to write by hand as a Python function got one by 2026-08-28.

What has moved since is the other bar and the instruments. Refused species 416 →
408, species-ready 85 → 90, priced ions 34 → 42, templates the bench loads 50 →
59, templates that fire from the shelf 25 → 33, `cannot-fire` 2 → 0. Real work,
scored against a board it does not move.

## What is left, by name

174 of the 377 catalog steps sit in an uncovered class and are extractable — they
resolve to graphs and they balance. They span **132 classes**, of which 102 hold
exactly one step and 6 hold three or more. The six are family candidates (T3):

| steps | routes | class |
|---:|---:|---|
| 6 | 6 | `nucleophilic-substitution` |
| 4 | 4 | `nucleophilic-addition` |
| 4 | 3 | `catalytic-air-oxidation` |
| 4 | 2 | `ammoxidation` |
| 3 | 3 | `esterification-nitration` |
| 3 | 3 | `intramolecular-williamson` |

Behind them, two steps each and two routes each: `diazotisation`,
`friedel-crafts-alkylation`, `electrophilic-aromatic-sulfonation`,
`diels-alder-cycloaddition`, `phosgenation`, `swarts-halogen-exchange`,
`oxime-formation`, `decarboxylation`, `halohydrin-formation`, `autoxidation`,
`oxidative-dimerisation`, `polycondensation`, `molten-salt-electrolysis`,
`carbide-formation`, `oxidative-dissolution`, `halide-oxidation` and the rest.

These are named mechanisms, not data rows. Each one is a transformation the
engine has never been able to perform on any substrate.

## The decision this supports

Hand-writing a template has run at three to five per session. 132 classes at
that rate is thirty-odd sessions. T2's extractor writes them mechanically from
the steps themselves, which is the whole argument of Tier 1 and the reason the
rate matters more than the queue. **T2 is therefore the decisive test**, and it
is decisive in both directions: if the intersection moves 40 → 55 or better,
there are six to ten productive coverage sessions left and a real ending; if it
moves by less than five, extraction does not work on this corpus and the route
scoreboard should be retired rather than fed.

Per-row curation — a sourced pKa at a time — is not the lever. 444 corpus ions
want one, the rate is two to four a session, and two consecutive sessions (T23,
T27) recorded "coverage does not move" as their own result. It still earns its
place: T18's derived plateau took stearic acid from 4 reactions to 21. It is
playability work, and it should be scored and scheduled as such.

## The script

```python
import catalog as cat, corpus_balance as cb
from catalog_coverage import TEMPLATE_CLASSES

compounds, steps = cat.load_compounds(), cat.load_steps()
covered = set(TEMPLATE_CLASSES)

def extractable(s):
    """T1.0's gate: every species resolves to a graph and the step balances."""
    sp = list(s.reactants) + list(s.products)
    if any(cat.is_marker(x, compounds) for x in sp):
        return False
    try:
        counts = [cb.formula(compounds[x].smiles) for x in sp]
    except Exception:
        return False
    return cb.coefficients(counts, len(s.reactants)) is not None

by_route = {}
for s in steps:
    by_route.setdefault(s.route, []).append(s)

ceiling = sum(1 for ss in by_route.values()
              if all(s.cls in covered or extractable(s) for s in ss))
print(ceiling, "of", len(by_route))   # 110 of 173 on 2026-09-13
```

Run it from `validation/` with `src` and `tools` on the path. If it returns
something other than 110, the corpus has changed and this page is stale — which
is the point of printing the script rather than the number alone.

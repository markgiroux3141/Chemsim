## S3 — Split `thermal-decomposition`  ✅ **DONE 2026-08-25 — +2 classes, ZERO routes, and the report was not byte-stable**

M6 read this class against M1's standard, recorded "four rows and they are **four
mechanisms**", and ran out of session rather than acting on it. The reading held.
Four rows re-labelled in `route_steps.psv`, no engine work, because **both
covering mechanisms were already declared under exactly these two names**:

| route | became | covered? |
|---|---|---|
| `vitriol-distillation` 1 | `sulfate-thermal-decomposition` | ✔ built by M6, **runs** (25.4 s at 1000 K) |
| `solvay-process` 3 | `bicarbonate-thermal-decomposition` | ✔ built by M6, **runs** (43.7 s at 450 K) |
| `melamine-route` 1 | `urea-deammoniation` | ✘ a template only |
| `marsh-test` 2 | `hydride-thermal-deposition` | ✘ nucleation, and species |

**Measured: 33/215 classes → 35/218, covered steps 95 → 97, template-ready routes
27 → 27.** Unlike S1, the two credited rows are rows that RUN.

### ⚠⚠ THE INSTRUMENT FIRST — THE COVERAGE REPORT WAS NOT BYTE-STABLE

Regenerating `COVERAGE_REPORT.md` at HEAD (this project's own rule: a committed
generated report is not a baseline) gave a **17-line diff with every number
identical**. `sorted(covered, key=lambda x: -step_classes[x])` sorts a **set**
with no tie-break, so equal step counts came out in `PYTHONHASHSEED` order — while
the `missing` table eight lines below already had `(-count, name)`.

⚠ **A report you cannot diff is a weak instrument**: 17 lines of noise per
regeneration is more than enough to hide a real one-line change in review, which
is what the file is regenerated for. Fixed in one line and verified S2's way —
**byte-identical across `PYTHONHASHSEED=0` and `=1`**. It was the only unstable
site: the greedy `max` already carried a `c` tie-break and the dict-item sorts are
insertion-ordered.

### ⚠⚠ AND THE OTHER GENERATED FILE WAS STALE BY THREE MILESTONES

`ROUTE_INDEX.md` had **not been regenerated since the initial commit**, while
`route_steps.psv` was re-labelled by M5, M6 and S1. Regenerating it moved **21
class labels: 11 from M5, 5 from M6, 1 from S1 and 4 from S3.**

⚠ **It is the one generated file no audit reads** — `catalog_coverage.py` parses
`route_steps.psv` directly — so a stale index changes no measured number, fails no
test and warns nobody. Anyone reading it for a step's class between M5 and S3 got a
pre-M5 answer. The standing rule was "a committed generated report is not a
baseline"; what this adds is that it has to cover the artefact **nothing checks**,
because that is the one that rots in silence.

### ⚠⚠ WHICH ROUTES IT MOVED: ZERO — PREDICTED FIRST, THEN MEASURED

S1's third mistake ("a coverage number moving is not evidence the engine moved")
is now a standing check, and this is the first time it ran *before* the credit
rather than after. All four affected routes are blocked on a **second** uncovered
class — `hydrolysis`, `carbonate-equilibrium`, `trimerisation`,
`dissolving-metal-reduction` — so no route could move, and none did.

⚠ **The greedy curve's "+1 route" for this class was never a standalone unlock.**
It sat at rank 14, i.e. *after* `hydrolysis` was added at rank 6. Read as a
promise it would have delivered a route it cannot deliver — the same misreading as
S1's, arriving from a different table. The standalone table answers that question
and never listed the class.

**What did move is the shape of the remaining work**, and that is the part worth
acting on: `solvay-process` and `vitriol-distillation` both went from two classes
away to **one**, so routes-one-class-away went 58 → 60 from 44 → 46 distinct
classes, and **`hydrolysis` jumped to greedy rank 4 (+2 routes)**.

### ⚠⚠ ONE OF THE TWO CREDITS IS A LATENT FALSE CREDIT, AND THE SPLIT MADE IT NEARER

`vitriol-distillation` step 1 reads `iron-ii-sulfate -> iron-ii-OXIDE +
sulfur-trioxide`; the declaration makes **hematite**, `2 FeSO4 -> Fe2O3 + SO2 +
SO3`. The credit is honest for the **opposite** reason to cinnabar's, and telling
the two apart is the entire value of the check:

* **cinnabar** — the ROW is right (a retort does give the metal) and the mechanism
  stops short of it, so the row needs a second reaction nobody built. Not covered.
* **green vitriol** — the MECHANISM is right and the ROW is wrong. FeO does not
  survive red heat, and `mineral_data` refuses it anyway on its crystal Cp.
  Nothing further is needed to reach the real products.

⚠ **The landmine:** the class is credited and the row still names a product this
engine never makes. Inert today, because step 2 is uncovered. **The day
`hydrolysis` is credited, `vitriol-distillation` goes template-ready on a step
whose stated product does not exist in the run** — and this split just made
`hydrolysis` the 4th-best template to build. Not corrected in the corpus, on the
`diels-alder-route` precedent.

⚠⚠ **Measured, and sharper than "someday": `hydrolysis` unlocks exactly ONE route
on its own, and it is `vitriol-distillation`.** The entire standalone payoff of the
4th-ranked template is the one route carrying a step whose product the engine does
not make.

### The two gaps cost different amounts, which is why they are two classes

* **`urea-deammoniation` is blocked on a TEMPLATE ONLY.** All three species
  resolve and the kernel can already express a unimolecular decomposition in a
  liquid — urea melts at 406 K and the row runs at 620 K, so it is a liquid-phase
  graph rewrite, not a lattice. ⚠ One caveat that is a physical fact rather than a
  gap: cyanic acid is one of the nine neutral species with no boiling point in any
  source, so it is `nonvolatile` and cannot enter the gas block.
* **`hydride-thermal-deposition` is blocked on BOTH, and its mechanism gap has a
  name: NUCLEATION.** `SurfaceArrays` is first order and **extensive** in the
  solid amount, so a solid at zero mol has zero rate for ever — and the term is
  irreversible by construction, so no roasting row can be run backwards to deposit
  one. Depositing a solid from no solid is not expressible here at all. `arsine`
  and `arsenic` are both refused outright, independently of that.

---

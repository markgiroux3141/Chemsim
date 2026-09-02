## S8 — The bare-element gap, and the +2 it was supposed to enable  ✅ **DONE 2026-08-26 — the curation landed, the template it was for is REFUSED, and both were predicted**

**+14 species-ready (63 → 77), +0 on the intersection (24), and the reason for
the second number is the whole milestone.** Nine element solids curated,
`element_data` given two reference entropies it was missing, zero new templates,
and `gas-solid-reduction` — the only +2 on the work queue — measured and refused.

| | before | after |
|---|---:|---:|
| routes species-ready | 63 / 173 | **77 / 173** |
| ... of them carried by a lattice | 14 | **28** |
| compounds refused | 455 | **444** |
| classes with a template | 43 / 224 | 43 / 224 |
| ⚠⚠ **routes BOTH — the one to quote** | **24** | **24** |

### ⚠⚠ 1. THE ELEMENT GAP IS WORTH +14 SPECIES-READY AND EXACTLY ZERO ON THE INTERSECTION

`NEXT_PROMPT` called this "the cheapest item here, and untouched since S6" for two
sessions. **S7 predicted it at +0 on the intersection by reading the two lists
against each other; S8 did it and measured +0.** None of the 15 routes blocked
only by a bare element is template-ready, so curating every one of them moves the
column a route is judged on by nothing.

⚠ **WHAT IT ACTUALLY BUYS IS A MULTIPLIER, AND THAT IS VISIBLE IN THE QUEUE.**
Before and after, on the RUNNABLE column:

| class | before | after | its routes |
|---|---:|---:|---|
| `gas-solid-reduction` | 1 | **2** | `copper-smelting`, `lead-smelting` |
| `catalytic-air-oxidation` | 0 | **1** | `p-xylene-oxidation` |
| `carbothermic-reduction` | 0 | **1** | `zinc-smelting` |
| `metal-ion-aldehyde-oxidation` | 0 | **1** | `tollens-test` |
| `molten-salt-electrolysis` | 0 | **1** | `downs-cell` |
| `pyrolysis` | 0 | **1** | `wood-distillation` |
| `disproportionation-hydrolysis` | — | **1** | `ostwald-process` (new entry) |
| `hydroformylation` | — | **1** | `oxo-process` (new entry) |
| `metallothermic-reduction` | — | **1** | `thermite` (new entry) |

**So the honest summary is +0 today and +9 opportunities that did not exist
before**, and the ordering lesson is that species work should follow the template
it enables rather than lead it.

### 2. THE CURATION, AND WHY `element_data` WAS THE WRONG HOME

Nine rows in `mineral_data`, on the SOLID basis, `ions=()`, `Hf = Gf = 0` by
definition: `cobalt`, `silver`, `platinum`, `palladium`, `lead`, `aluminium`,
`sodium`, `zinc`, `carbon-graphite`. **No new machinery** — S1 had already built
the shape for `iron`, `nickel` and `copper`, and
`tools/build_mineral_data.py` carried the whole argument in a block comment above
a three-item list.

⚠ **THE LAYERING QUESTION S6 RAISED HAS AN ANSWER AND IT IS IN THE TYPE, NOT THE
MODULE NAME.** `element_data`'s record is on the IDEAL-GAS basis, and the
ideal-gas record for `[Fe]` is the ATOM at +416 kJ/mol — a real number that is
not iron filings. A solid-basis zero belongs in the solid-basis module.
`element_data.REFERENCE_STATES` still carries each element's S0, which is what
the Gf derivation consumes, and **S8 had to add two: Pt and Pd were missing**, so
platinum and palladium could not have been derived without touching that file.
The regeneration is purely additive — 10 lines, nothing existing moved.

⚠ **THE LIST WAS CALLED `METALS` AND THE NAME WAS WRONG BY ONE ROW.**
`carbon-graphite` is a COVALENT lattice. Every property the entry needs is about
the REPRESENTATION rather than the bonding — no dissolved form, a crystalline
reference state, a definitional zero, and a solid block that holds it exactly as
it holds iron — so renaming the list to `ELEMENT_SOLIDS` was cheaper than an
exception, and an exception was the only alternative.

⚠ **AND THE DEFINITIONAL-ZERO CHECK FIRED, WHICH IS WHY TIN IS NOT IN THE LIST.**
CRC's row for 7440-31-5 is GREY tin at `Hfs = -2.1 kJ/mol` against a white-tin
reference state. The generator refuses it rather than taking the wrong allotrope
— the same check `reference_entropies` has made since the element floor was built.

⚠ **VERIFIED BY RUNNING.** All nine charged into a real `Vessel` at 800 K with
air, held to twelve figures over 600 s, `conservation_report` empty. S6's
precedent: reading `priced_solid` is a different claim from charging it.

⚠ **AND THE IDEAL-GAS REFUSAL IS NOT SOFTENED BY ONE DIGIT.** `thermo.get("[C]")`
still refuses, with the same message; `validation/game_gates.py` still reports
graphite, Na, K, Ca, Fe, Cu, Zn as REFUSED on that basis. Curating the solid
basis and refusing the gas basis are the same statement made twice.

### ⚠⚠ 3. `gas-solid-reduction` IS REFUSED, AND THE REFUSAL IS THE CHEMISTRY

The only +2 on the queue. Its four rows are `MO(s) + CO(g) -> M(s) + CO2(g)` —
the same shape as a roast, a gas arriving at a crystal — so it looked like four
rows of `SURFACE_REACTIONS` and no code. **Every one fails
`surface.LN_K_IRREVERSIBLE`, priced against this project's own tables at each
row's own furnace temperature:**

    tenorite + CO  -> copper  + CO2    dG -127.72 kJ/mol   ln K  10.90 @ 1500 K
    litharge + CO  -> lead    + CO2    dG  -68.31          ln K   7.24 @ 1400 K
    hematite + 3CO -> 2 iron  + 3CO2   dG  -29.48          ln K   4.20 @ 1300 K
    zincite  + CO  -> zinc    + CO2    dG  +63.31          ln K  -4.10 @ 1400 K

⚠⚠ **AND THE BOUND IS NOT THE PROBLEM — THE CHEMISTRY IS.** A blast furnace's top
gas still contains carbon monoxide, and it does because these reductions really
are reversible: the CO/CO2 ratio over an oxide is the equilibrium a furnace's
entire design is built around. The zinc row is not even downhill; a real zinc
retort works because the zinc **boils off at 1180 K**, which is product removal
rather than a favourable equilibrium — and `mineral_data` holds zinc as a lattice
with no vapour pressure, so that escape is not expressible here either.

⚠ Softening `LN_K_IRREVERSIBLE` would admit a real reverse flux into a term that
is integrated FORWARD ONLY, and the refusal message already says why that cannot
be traded: mass action written on a solid AMOUNT settles at `p/K = n_A/n_B`
rather than at unit activity (M6's measurement), so a reversible declaration
would reach a wrong equilibrium while looking like one that does not.

**So `gas-solid-reduction` is a NAMED ENGINE GAP: it needs a REVERSIBLE
solid-gas term.** It is the second gap of that shape after NUCLEATION, and unlike
nucleation it has **two species-ready routes waiting on it** — which makes it the
most valuable engine item in the plan that nobody has scoped.

### ⚠ 4. WHAT THE SESSION DID NOT DO, AND WHY THAT IS THE RIGHT ANSWER

No template was written. The queue's only +2 turned out to need engine work, and
the alternatives are all +1 — `wacker-oxidation`, `oxidative-cleavage`,
`skraup-cyclisation`, `metallothermic-reduction` and the six the curation just
created. Picking one at random would have been worth less than measuring which
ones are real, and S7's own lesson is that the ranking lies. **The queue is now
ranked against three bars instead of one; the next session picks off it.**

**Files:** `tools/build_element_data.py` (Pt/Pd reference states),
`tools/build_mineral_data.py` (`METALS` → `ELEMENT_SOLIDS`, +9 rows),
`src/chemsim/properties/element_data.py` (regenerated, +10 lines),
`src/chemsim/properties/mineral_data.py` (regenerated, +144 lines),
`src/chemsim/properties/surface.py` (the refusal, recorded),
`tests/test_element_solids.py` (new, 38 tests),
`tests/test_element_data.py` (the exemption list), `README.md`,
`data/catalog/COVERAGE_REPORT.md` and both `derived/*.psv` (regenerated).

---

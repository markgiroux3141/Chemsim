# `data/catalog` — the coverage corpus

A hand-authored corpus of **1,583 compounds** and **173 named synthetic routes
(377 steps)**, built so that "how much chemistry does this simulator actually
cover?" can be *measured* instead of estimated.

It is data, not code. Nothing in `src/chemsim` imports it. It exists to be
pointed at the simulator, and the numbers it produces are deliberately
unflattering.

---

## The files

| file | what it is |
|---|---|
| `compounds/*.psv` | the compound catalog, split by family; `id \| name \| smiles \| class \| role \| domains \| notes` |
| `routes.psv` | route headers; `route_id \| name \| era \| domain \| target \| notes` |
| `route_steps.psv` | the steps; `route_id \| step \| name \| reactants \| products \| conditions \| class` |
| `COVERAGE_REPORT.md` | **generated.** The audit result. |
| `ROUTE_INDEX.md` | **generated.** Every route as feedstocks → intermediates → products. |
| `derived/route_roles.psv` | **generated.** The same split, machine-readable. |
| `derived/species_roles.psv` | **generated.** Per species: how often it is a feedstock / intermediate / product / catalyst across all routes, plus its resolution tier. |

Regenerate everything:

```
python tools/catalog.py             # structural validation only
python tools/build_route_index.py   # writes ROUTE_INDEX.md
python validation/catalog_coverage.py  # writes COVERAGE_REPORT.md + derived/
```

⚠⚠ **RUN ALL THREE. `ROUTE_INDEX.md` WAS STALE BY THREE MILESTONES AND NOBODY
NOTICED**, because it is the one generated file no audit reads — the coverage
audit parses `route_steps.psv` directly, so a stale index changes no measured
number and produces no failure. Found in S3: it had not been regenerated since
the **initial commit**, while `route_steps.psv` was re-labelled by M5, M6 and S1.
Regenerating it moved **21 class labels — 11 from M5, 5 from M6, 1 from S1 and 4
from S3.** Anyone who read this index to find a step's class between M5 and S3
got a pre-M5 answer.

⚠ **AND `COVERAGE_REPORT.md` WAS NOT BYTE-STABLE UNTIL S3 FIXED IT.**
`sorted(covered, ...)` sorted a *set* with no tie-break, so regenerating it
produced ~17 lines of `PYTHONHASHSEED` noise with every number identical — enough
to hide a real one-line change in review, which is what regenerating it is *for*.
It is now byte-identical across hash seeds; if a regeneration ever produces a
diff again, that diff is real.

---

## ⚠ The reaction class is a MECHANISM, not an outcome (settled 2026-08-23)

A template in this simulator is **SMARTS on a mechanism**. So a class named for
what a step *achieves* cannot answer "is there a template for this", and four
classes in the original corpus were outcome labels spanning several mechanisms
each. **32 rows were re-labelled** to the mechanism their own reactants and
products show. Read the row, not the step's name.

**Why it mattered:** crediting the six `properties/electrolyte.py` dissociation
templates was supposed to be a one-line lookup change taking covered steps from
21 to 46. That arithmetic needed `deprotonation` (6 steps) to be proton transfer.
**Five of its six rows are carbanion generation** — malonate and acetoacetate
anions, a Wittig ylide, two enolates — which is precisely the capability with no
template. Crediting the class would have made the audit *less* truthful.

| was | steps | became | why |
|---|---:|---|---|
| `acid-base` | 15 | `proton-transfer` (11) | water-mediated, on a tabulated pKa |
| | | `carbonate-equilibrium` (1) | CO₂ **hydration** then transfer; the hydration has no template and both carbonate ions are refused |
| | | `nitronium-generation` (1) | protonation **then dehydration**; the dehydration is the step |
| | | `polysaccharide-alkoxide` (1) | cellulose OH; there is no **aliphatic** alcohol template, only phenol |
| | | `imide-deprotonation` (1) | phthalimide N–H |
| `deprotonation` | 6 | `carbanion-generation` (5) | needs **C–H pKa values** the electrolyte table does not have |
| | | `arenium-deprotonation` (1) | the rearomatising half of SEAr, not an aqueous equilibrium |
| `redox` | 4 | `halide-oxidation` (2) | HNO₃ / MnO₂ oxidising chloride to Cl₂ |
| | | `metal-ion-aldehyde-oxidation` (2) | Ag(I) and Cu(II) on an aldehyde — Tollens and Fehling |
| `oxidation` | 4 | `leuco-dye-oxidation` (2) | PbO₂ and O₂ on a leuco dye — same mechanism, different oxidant |
| | | `arene-oxidation-to-quinone` (1) | Cr(VI) on anthracene |
| | | `permanganate-alcohol-oxidation` (1) | ⚠ **not** `aerobic_oxidation`: that template fires on the alcohol but supplies O₂, and permanganate is a different oxidant with different stoichiometry |
| `acid-displacement` | 4 | `acid-displacement` (1) | saltpetre + H₂SO₄: nothing leaves solution, the volatile acid is distilled off |
| | | `acid-displacement-precipitating` (3) | gypsum or calcium sulfate must **leave solution** — gated on a Ksp, i.e. on milestone M3 |

**This also reconciled a contradiction in the plan**: `acid-displacement` was
listed both as covered-by-proton-transfer and as a top *missing* class. Both were
right about different rows — 1 of its 4 steps needs only proton transfer and 3
need a solubility product.

### Two rules that follow

⚠ **The class says what the MECHANISM is; whether a particular reagent is priced
is a SPECIES question.** The audit counts those separately, so `kjeldahl`'s
boric-acid titration is `proton-transfer` even though boron has no oxyacid
template — the missing pricing shows up on the species side, where it belongs.
Putting it in the class name would double-count one gap as two.

⚠ **A step's NAME can lie; its reactants cannot.** `williamson-ether` step 1 is
called "alkoxide formation" and reads `phenol + NaOH → sodium-phenoxide`. It is a
**phenoxide**, so `phenol_dissociation` covers it. Two of the re-labels above
turn on reading the row instead of the name.


## Why pipe-separated

Chemical names are full of commas (`2,4-dinitrophenol`) and free of pipes.
SMILES are free of both. One record per line is the form a human can review in a
diff, which matters for a file whose entire value is that someone checked it.
No YAML, no JSON, no dependency past the standard library and RDKit.

## Every SMILES parses

`tools/catalog.py` asserts it, and the catalog is currently clean: 1,583 rows,
zero unparseable structures, zero duplicate ids, zero dangling references from
`route_steps.psv` into the compound tables, and zero routes whose declared
target is never produced by their own steps. That last check caught six header
slips during authoring, which is the sort of thing the check exists for.

## The one design decision worth defending

**A route does not declare which of its species are feedstocks and which are
intermediates.** It declares only its steps. `catalog.route_roles` derives the
split from the step graph:

```
consumed, never produced   ->  primary feedstock
produced and consumed      ->  intermediate
produced, never consumed   ->  product or byproduct
both sides of one step     ->  catalyst
```

A declared split would drift the first time someone edited a step and forgot the
declaration, and the drift would be silent. A derived one cannot drift. It also
answers the actual question — *what is an intermediate here* — rather than
restating an author's opinion of it.

Two consequences worth knowing:

* **The roles are per route, and the same species is routinely both.**
  Acetaldehyde is an intermediate in `ethanol-fermentation` and a feedstock in
  `petn-route`. Sulfuric acid is a product of `contact-process`, a catalyst in
  `aspirin-route` and a feedstock in `leblanc-process`. That is not a conflict.
* **A closed cycle correctly has no feedstocks.** `lime-cycle` returns
  limestone to limestone, so every one of its five species is an intermediate
  and the derivation says so. Reading that as a bug would be reading it wrong.

## The eight markers

Eight species in `route_steps.psv` end in `-marker` *and* have no compound entry:
coal, coal tar, collagen, sodium amalgam, alkali cellulose, an iron-gallate
complex, a lactic oligomer, and tanned leather. They are rocks, mixtures, alloys
and proteins — things with no single molecular graph. They are carried so the
routes stay balanced and readable, and the audit excludes them rather than
inventing a structure for them.

⚠ Some ids *ending* in `-marker` do have catalog entries (`sbr-marker`,
`viscose-marker`, `gunpowder-marker`, …) and are audited normally. Absence from
the compound table is what makes something a marker; the suffix is just a signal
that it was deliberate rather than a typo.

## What the audit found

Read `COVERAGE_REPORT.md` for the full breakdown. The four numbers that matter:

| | before M5 | after M5 |
|---|---|---|
| formation half is **measured or Benson** | 709 / 1583 (45%) | **715 / 1583 (45%)** |
| formation half falls back to **Joback** | 402 / 1583 (25%) | 402 / 1583 (25%) |
| **refused** outright | 472 / 1583 (30%) | 466 / 1583 (29%) |
| **UNIFAC**-decomposable (can enter an LLE) | 830 / 1583 (52%) | 836 / 1583 (53%) |
| reaction classes with a **template** | 12 / 206 | **29 / 212** |
| routes that are **template-ready** end to end | 3 → 7 / 173 | **25 / 173** |

⚠ **Both columns were re-measured on 2026-08-24; the "before" column is not what
this file used to claim.** The committed report predated M4's UNIFAC work, so the
numbers it carried (790 decomposable, 8 classes, 3 routes) were stale rather than
wrong-at-the-time. Regenerating at the previous commit gives the "before" column
above, and that is what M5 should be measured against.

The species side is in decent shape and the reaction side is still the binding
one, but it is no longer the same shape of problem: the reaction half moved from
12 classes to 29 and from 7 routes to 25 in one milestone, and what limits the
next 25 is that **the remaining classes unlock about one route each**. Before M5,
63 routes sat one class away from 50 distinct classes; after, 56 sit one class
away from 43. There is no lever left to pull.

### ⚠ M5 re-labelled 11 more rows, on the same standard M1 set

Two classes were outcome labels and are now mechanisms. The audit numbers above
already include this; read the row, not the class name.

| was | rows | became | why |
|---|---:|---|---|
| `electrophilic-aromatic-nitration` | 1 of 6 | `ipso-nitrodesulfonation` | `picric-acid-route` step 2 replaces **three sulfonate groups** with nitro. That is ipso substitution, not the Ar–H nitration the other five rows are. |
| `catalytic-hydrogenation` | all 10 | five labels | the **most-used class with no template** in the corpus, and its ten rows are five mechanisms sharing a reactor |

The hydrogenation split, in full — and note that it was split rather than
refused, because unlike `fermentation` every one of these rows *is* a clean
mechanism:

| became | rows | has a template |
|---|---:|---|
| `nitro-hydrogenation` | 3 | ✔ `nitro_hydrogenation` |
| `alkene-hydrogenation` | 3 | ✔ `alkene_hydrogenation` |
| `nitro-partial-hydrogenation` | 1 | ✘ — nitrobenzene stopped at the hydroxylamine is a different stoichiometry, and it is the whole difficulty of the paracetamol route |
| `arene-hydrogenation` | 2 | ✘ |
| `carbonyl-hydrogenation` | 1 | ✘ |

⚠ **One catalog row is unbalanced and was labelled rather than corrected.**
`diels-alder-route` step 3 reads `norbornene-dicarboxylic-anhydride + hydrogen →
norbornane`, which loses the whole anhydride. It is labelled
`alkene-hydrogenation` because that is the mechanism it means; the imbalance is
recorded here rather than fixed, because inventing the missing products would be
authoring chemistry inside an audit corpus.

### ⚠ M6 read `calcination` and `roasting`, and re-labelled NOTHING

M6's two classes were read against the same standard before any code was
written. The verdicts differ, and neither produced a re-label:

| class | rows | verdict |
|---|---:|---|
| `calcination` | 3 | **TWO mechanisms.** `lime-cycle` 1 and `solvay-process` 5 are DECARBONATION (`carbonate -> oxide + CO2`); `bayer-process` 3 is DEHYDRATION (`hydroxide -> oxide + H2O`). Both are built. |
| `roasting` | 5 | **ONE mechanism** -- `metal sulfide + O2 -> metal oxide + SO2` -- in four rows. ⚠ `mercury-from-cinnabar` gives the METAL, because HgO decomposes at roasting temperature, so one template will not cover that row honestly. |

⚠ **The class names were left alone, and that is deliberate.** M1's rule is that
a class must name a MECHANISM, and `calcination` names two. The reason not to
split the label is that the split does not change what anything scores: the two
decarbonation rows are covered by M6's `calcination-decarbonation` and the
dehydration row is not covered by anything, so a re-label would move the same
rows between the same buckets. **What M6 recorded instead is that its
dehydration TEMPLATE is not the catalog's dehydration ROW.** Bayer's
`Al(OH)3 -> Al2O3 + H2O` needs two minerals `mineral_data` does not have, so M6
built the same mechanism on `Ca(OH)2 -> CaO + H2O` -- **the mechanism is covered
and the row still reads uncovered**, which is the standard costing something in
the honest direction.

`roasting` remains at zero rows covered, and now for two independent reasons:
of its five sulfides only ZnS prices and **none of the five oxides does** (data);
and roasting CONSUMES a gas, which M6's affinity form is measurably not a rate
law for (mechanism -- see `properties/solid_state.py`). The second reason is the
useful one, because it says which engine feature the class is waiting on.

### ⚠ AND THE NEXT MILESTONE CLOSED IT -- AND SPLIT THE CLASS ON M1's STANDARD

Both of M6's reasons are gone: `mineral_data` carries all four roasting oxides and
all four sulfides, and `properties/surface.py` is the mass-action term the class
was waiting on. But crediting `roasting` as M6 labelled it made
`mercury-from-cinnabar` read template-ready, and **the engine cannot run that
row** -- so the class was read again and split.

| was | rows | became | has a mechanism |
|---|---:|---|---|
| `roasting` | 4 of 5 | `roasting` | ✔ `SurfaceArrays`, three of the four rows runnable |
| `roasting` | 1 of 5 | `roasting-to-metal` | ✔ **as of S4** -- see below. ✘ when S1 split it out |

⚠⚠ **S4 UPDATE: `roasting-to-metal` IS NOW COVERED, AND THE SPLIT WAS KEPT.**
S1 named what was missing -- "a second reaction nobody built" -- and it is one
more row of `SOLID_STATE_REACTIONS`: `2 HgO -> 2 Hg + O2`. Neither declaration
mentions the other; they share one crystal in the solid block and the catalog's
own row falls out of the pair, measured at **0.020000000000 mol of mercury and
0.020000000000 mol of SO2** from 0.02 mol of cinnabar. The class is credited to
the EMERGENT pair, the way `solid-carbonation` is.

⚠ **The obvious move was to fold the row back into `roasting` now that its
product is reachable. Both arithmetics were measured and the split was kept:**

| | classes | template-ready routes |
|---|---|---|
| keep `roasting-to-metal` | **36/218** | 28/173 |
| fold back into `roasting` | 35/217 | 28/173 |

The routes are identical, so the choice is only about what the class column
SAYS -- and `roasting-to-metal` records a mechanism difference rather than an
outcome: **this ore's oxide does not survive the furnace that makes it**, which
is why one row needs two mechanisms where the other four need one. Folding back
would delete the distinction S1 paid to find, for a smaller denominator.

⚠⚠ **THE SPLIT WAS FORCED BY A FALSE CREDIT, WHICH IS WHY IT IS RECORDED HERE.**
M6 read `roasting` as ONE mechanism in five rows and flagged that
`mercury-from-cinnabar` "gives the METAL, because HgO decomposes at roasting
temperature, so one template will not cover that row honestly". That flag was
right and it was not a label. Crediting the unsplit class moved
`mercury-from-cinnabar` into the template-ready list on the strength of a
mechanism that does not make its product -- the `deprotonation` mistake M1 named,
arriving from the other direction. `cinnabar-roasting` IS built and runs; what it
makes is montroydite, and the metal step needs mercury metal as a species and a
second reaction. So the mechanism is credited and the row is not.

The four rows that remain in `roasting`:

| row | runnable? | why |
|---|---|---|
| `zinc-smelting` 1 | ✔ | `sphalerite-roasting` |
| `lead-smelting` 1 | ✔ | `galena-roasting` |
| `copper-smelting` 1 | ✔ | `covellite-roasting` |
| `pyrite-roasting` 1 | ✘ **but it reads template-ready** | **DATA.** Pyrite has `Hfs` in WEBBOOK and `S0s` in nothing, so `mineral_data` refuses the entry under the same-database rule. |

⚠⚠ **AND S4 FOUND THE MIRROR OF THAT ROW, WHICH IS WHAT MAKES THE PAIR
INFORMATIVE.** `pyrite-roasting` reads template-ready and does NOT run.
`mercury-from-cinnabar` reads **species-UNREADY and DOES run** — closing at
0.020000000000 mol of mercury on a 0.02 mol charge — because the species column
asks the plain `ThermochemistryProvider`, which REFUSES A LATTICE BY NAME. That
refusal is right (the fusion law is 407x wrong for a lattice) and the conclusion
drawn from it is not: since M3 a lattice has had a home in `mineral_data`, which
is what precipitation, `SolidStateArrays` and `SurfaceArrays` all price from.

**Measured: 14 routes read species-UNREADY while every one of their refused
species is a mineral this project prices** — 49 of 173, where the honest number
is at most 63. Among them **`lime-cycle`**, which M6 declared complete end to end
from limestone and which `examples/lime_cycle.py` runs, and **`haber-bosch`** and
**`methanol-synthesis`**, whose only "refused" species is the solid CATALYST S1
curated so that it could be put in the flask.

⚠ Not corrected in S4: it redefines a published column, so it owes the standing
"which routes does it move" check and a verification pass. Recorded at the line
that computes it, in `validation/catalog_coverage.py`. **Two columns, two
directions of error, and neither is a bug in the engine.**

⚠ **AND THE ONE ROUTE THIS MILESTONE ADDS TO THE TEMPLATE-READY LIST IS
`pyrite-roasting`, WHICH DOES NOT RUN.** That is not a bug in the number, it is
what the number MEANS: template-readiness asks whether every step class has a
mechanism, and species-readiness asks separately whether the species price. Pyrite
is a species gap and the audit counts it as one. Read together: the three smelting
routes are the ones whose roasting step actually runs, and all three are still
blocked further down the chain (`carbothermic-reduction`, `gas-solid-reduction`).
So the honest summary is **+1 class and +1 template-ready route, and zero new
routes that run end to end** -- which is the second time this corpus has had to
say that a headline moved further than the engine did.

⚠ **WHAT DID NOT SURVIVE BEING BUILT: THE IMPLIED SHARED CLOCK.** One barrier and
one pre-exponential cover all four declarations, which is M6's "one mechanism"
reading holding. What it does not license is that they run at the same
temperature: the catalog's own equipment column puts cinnabar in a 900 K retort
and sphalerite in an 1100 K roaster, and a shared clock makes cinnabar **31x
slower** at its own temperature. This project's one mechanism for fixing that --
Evans-Polanyi on the reaction enthalpy -- is measured getting the ordering
BACKWARDS, because sphalerite is the most exothermic row and needs the hottest
furnace. So M6's "a constant shared between rows is a claim that they are the same
event" arrives here as a claim that is partly refuted and stated, rather than
hidden. See `properties/surface.py`.

### ⚠ M6 DID re-label five rows, in two classes it had not been asked about

Reading `calcination`'s rows led straight into the two classes that finish the
`lime-cycle` route, and both of them were two mechanisms. Split rather than
refused, on the `catalytic-hydrogenation` precedent -- every row here IS a clean
mechanism:

| was | rows | became | has a mechanism |
|---|---:|---|---|
| `hydration` | 2 of 3 | `lime-slaking` | ✔ `SolidStateArrays` reversed |
| `hydration` | 1 of 3 | `carbonyl-hydration` | ✘ -- chloral hydrate is a gem-diol on a carbonyl, not a lattice taking on water |
| `carbonation` | 1 of 2 | `solid-carbonation` | ✔ `SolidStateArrays`, EMERGENT |
| `carbonation` | 1 of 2 | `basic-carbonate-precipitation` | ✘ -- the white-lead stack is a metathesis in solution |

⚠⚠ **`solid-carbonation` IS THE FIRST CLASS IN THIS CORPUS CREDITED TO A
MECHANISM NOBODY WROTE.** It is not a template and it is not one row's reverse:
it is the `calcination-dehydration` row forwards and the
`calcination-decarbonation` row backwards, sharing the quicklime in the solid
block. `lime-slaking` is the dehydration row's own reverse. **Two declarations,
three credited classes**, and `lime-cycle` becomes the 26th template-ready route.

### ⚠⚠ M8 SPLIT `electrolysis` — AND IT WAS THE GREEDY CURVE'S TOP ROW

The set-cover curve has ranked `electrolysis` first since M1: **+3 routes, more
than any other single class.** M8 built the mechanism and the row check took two
of the three away, which is the fourth time this standard has cost a headline
number and the first time it has cost the number at the very top of the queue.

Four rows, and they are **three mechanisms** — the `catalytic-hydrogenation`
shape again, and the distinction is at the CATHODE:

| route | step | became | what it is | covered? |
|---|---|---|---|---|
| `chloralkali` 1 | `NaCl + H2O -> NaOH + Cl2 + H2` | `aqueous-electrolysis` | ions in water; the cathode reduces **water** | ✔ built, **runs** — `halide_electrolysis` |
| `downs-cell` 1 | `NaCl -> Na + Cl2` | `molten-salt-electrolysis` | a **melt**, which is not a phase this project has | ✘ named gap |
| `hall-heroult` 1 | `Al2O3 + C -> Al + CO2` | `molten-salt-electrolysis` | a melt, and a **consumable** carbon anode | ✘ named gap |
| `castner-kellner` 1 | `NaCl + Hg -> Na/Hg + Cl2` | `amalgam-electrolysis` | a mercury cathode reduces the **sodium** instead | ✘ marker, no graph |

⚠ **THE CATHODE IS THE WHOLE DIFFERENCE AND IT IS NOT A DETAIL.** Chloralkali
and Castner-Kellner take the same feed and give the same chlorine; one makes
caustic soda and the other makes sodium metal, and the reason is which species
the cathode reduces. Calling both "electrolysis" and crediting the class on one
of them would have claimed a route to sodium metal that this engine cannot make
— the `roasting-to-metal` false credit in a new costume.

⚠ **AND THE MELT ROWS COST NOTHING TODAY.** Both `downs-cell` and `hall-heroult`
are blocked on a bare element as well (`sodium`, `aluminium`, `carbon-graphite`),
so they were never one class away from running. The split moves them from
"blocked on one thing we could build" to "blocked on two things, honestly named".

`electro-organic-coupling` was NOT split, on the `ester-hydrolysis` precedent:
its two rows are two mechanisms and **both are built**, which is exactly when a
class with several mechanisms in it may be credited.

| route | step | what covers it |
|---|---|---|
| `kolbe-electrolysis` 1 | `2 AcO- -> C2H6 + 2 CO2` | `kolbe_electrolysis`, and it generalises — acetate + propanoate gives ethane, propane **and** butane |
| `adiponitrile-route` 1 | `AN + H2O -> ADN + O2` | `water_electrolysis` + `alkene_hydrodimerisation`, and the row's stoichiometry EMERGES from the pair |

⚠ The second of those pays no electrons, and that is a measurement rather than an
omission: the whole cell `4 AN + 2 H2O -> 2 ADN + O2` is uphill at +212.7 kJ/mol,
while `2 AN + H2 -> ADN` is **downhill** at −171.7. The voltage buys the hydrogen,
not the carbon–carbon bond. The cost of decomposing it that way is stated where
it can be found: the route cannot start until water splits at 1.441 V, where the
real cell reduces acrylonitrile at its own cathode from 0.551 V.

### ⚠ S3 SPLIT `thermal-decomposition` — AND CHECKED WHICH ROUTES THE NUMBER MOVED

M6 read this class, recorded "four rows and they are **four mechanisms**", and
left it alone because splitting it was a separate self-contained job and the
session ran out — not because the reading was in doubt. The reading held. Four
mechanisms sharing one furnace, which is the `catalytic-hydrogenation` shape:

| route | step | became | what it is | covered? |
|---|---|---|---|---|
| `vitriol-distillation` 1 | `FeSO4 -> FeO + SO3` | `sulfate-thermal-decomposition` | a solid sulfate decomposing to a solid oxide plus gas | ✔ built, **runs** (25.4 s at 1000 K) |
| `solvay-process` 3 | `NaHCO3 -> Na2CO3 + CO2 + H2O` | `bicarbonate-thermal-decomposition` | a solid bicarbonate, two gases | ✔ built, **runs** (43.7 s at 450 K) |
| `melamine-route` 1 | `urea -> cyanic acid + ammonia` | `urea-deammoniation` | a MOLECULAR decomposition; urea melts first | ✘ a graph rewrite, not a lattice |
| `marsh-test` 2 | `arsine -> arsenic + hydrogen` | `hydride-thermal-deposition` | a gas decomposing and DEPOSITING a metalloid | ✘ nucleation — see below |

**No engine work: both covering mechanisms were already declared by M6 under
exactly these two names**, and both are pinned by `tests/test_solid_state.py`.

⚠⚠ **WHICH ROUTES IT MOVED: ZERO — PREDICTED BEFORE CREDITING AND THEN
MEASURED.** That check exists because S1's `roasting` credit moved
`mercury-from-cinnabar` into the template-ready list on the strength of a
mechanism that does not make that row's product. Here every one of the four
affected routes is blocked on a **second** uncovered class:

| route | its other gap | covered? |
|---|---|---|
| `vitriol-distillation` | step 2 `hydrolysis` | ✘ |
| `solvay-process` | step 1 `carbonate-equilibrium` | ✘ |
| `melamine-route` | step 2 `trimerisation` | ✘ |
| `marsh-test` | step 1 `dissolving-metal-reduction` | ✘ |

Measured: **33/215 classes → 35/218**, covered steps **95 → 97**, template-ready
routes **27 → 27**. So the honest summary is **+2 classes, +3 to the denominator,
+2 steps, and no route moved at all**.

⚠ **AND THE GREEDY CURVE'S "+1 route" FOR THIS CLASS WAS NEVER A STANDALONE
UNLOCK.** It sat at rank 14 — i.e. *after* `hydrolysis` was added at rank 6. Read
as a standalone promise it would have delivered a route it cannot; the standalone
table is the one that answers that question, and it never listed this class. Same
misreading as S1's, arriving from a different table.

**What did move is the shape of the remaining work**, and it is the one thing
here worth acting on: `solvay-process` and `vitriol-distillation` both went from
two classes away to **ONE**, so routes-one-class-away went 58 → 60 from 44 → 46
distinct classes, and `hydrolysis` jumped to **greedy rank 4 (+2 routes)**.

### ⚠⚠ ONE OF THE TWO CREDITS IS A LATENT FALSE CREDIT, AND IT IS NOW RANK 4 AWAY

`vitriol-distillation` step 1 reads `iron-ii-sulfate -> iron-ii-OXIDE +
sulfur-trioxide`. The declaration makes **hematite**: `2 FeSO4 -> Fe2O3 + SO2 +
SO3`. The credit is honest for a reason that is the **opposite** of the cinnabar
case, and telling the two apart is the whole point of the check:

* **cinnabar** — the ROW is right (a retort does give the metal) and the mechanism
  stops short of it, so reaching the row needs a second reaction nobody built.
  Not covered; re-labelled `roasting-to-metal`.
* **green vitriol** — the MECHANISM is right and the ROW is wrong. FeO does not
  survive red heat, and `mineral_data` refuses it anyway — on the half nobody
  would guess, its crystal heat capacity, which CRC does not tabulate for it at
  all. Nothing further is needed to reach the real products.

⚠ **THE LANDMINE, STATED FOR WHOEVER TRIPS IT:** the class is credited and the
row still names a product this engine never makes. Today that is inert, because
step 2 is uncovered. **The day `hydrolysis` is credited, `vitriol-distillation`
goes template-ready on a step whose stated product does not exist in the run** —
and this split just made `hydrolysis` the 4th-best template to build. Whoever
builds it owes this row a second look.

⚠⚠ **AND IT IS SHARPER THAN "SOMEDAY": measured, `hydrolysis` unlocks exactly
ONE route on its own, and that route is `vitriol-distillation`.** So the entire
standalone payoff of the 4th-ranked template is the one route carrying a step
whose product the engine does not make. That is not an argument against building
`hydrolysis` — it is the reason to read this paragraph first.

The corpus row is deliberately **not** corrected, on the `diels-alder-route`
precedent: inventing chemistry inside an audit corpus is not allowed, and
correcting this one means re-balancing it to 2 FeSO₄ and adding an SO₂ nobody
wrote. Recorded rather than reproduced quietly.

### ⚠ THE TWO GAPS COST DIFFERENT AMOUNTS, WHICH IS WHY THEY ARE TWO CLASSES

* **`urea-deammoniation` is blocked on a TEMPLATE ONLY.** All three species
  resolve, and the kinetics kernel can already express a unimolecular
  decomposition in a liquid — urea melts at 406 K and the row runs at 620 K, so
  it is a liquid-phase graph rewrite, not a lattice. ⚠ One caveat that is a
  physical fact rather than a gap: cyanic acid is one of the nine neutral species
  with no boiling point in **any** source, so it resolves as `nonvolatile` and
  cannot be put in the gas block — the HNCO would come off into the liquid.
* **`hydride-thermal-deposition` is blocked on BOTH, and its mechanism gap has a
  name: NUCLEATION.** `SurfaceArrays` is first order and **extensive** in the
  solid amount, so a solid at zero mol has zero rate for ever — and the term is
  irreversible by construction, so no roasting row can be run backwards to
  deposit one. Depositing a solid from no solid is not expressible here at all.
  The species half is independent and also missing: `arsine` and `arsenic` are
  both refused outright (no estimator for AsH₃; a bare element symbol for As).

Three further findings the report makes explicit:

* **10 refusals need only a boiling point.** Their formation half already
  resolves off Benson; nothing prices their vapour pressure. That is a lookup,
  not a research problem, and it is the cheapest coverage available.
* **195 refusals are charged organics** — quaternary ammoniums, bipyridiniums,
  organic diazonium salts. The Born model is fitted to small hard ions and these
  are not, so the refusal is correct behaviour and not a gap to close. Counting
  them as failures would measure the catalog's ambition, not the simulator.
* **The UNIFAC gap is bigger than the thermo gap.** Half the catalog cannot be
  decomposed into groups, which silently sets its activity coefficient to 1 —
  and in a two-phase calculation that is not an approximation, it is the
  assumption that the phases do not separate.

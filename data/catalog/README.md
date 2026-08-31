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
| `shelf.psv` | **P3: what a player STARTS WITH**; `id \| tier \| amount \| phase \| note`. 71 rows in three tiers (43 natural / 24 intermediate / 4 bottle), and the tier is what lets the shelf SHRINK -- an `intermediate` row is deleted the day its stranded route becomes reachable. Read by `tools/build_shelf.py`, which resolves each row against the compound tables and writes `chemsim.engine.shelf_data`. ⚠ Its header carries the resolution rule, and that rule is a chemistry decision rather than a parse: a mineral has TWO representations in this engine -- a reacting lattice, or its ions in the solid block -- with disjoint mechanics and nothing converting between them. |
| `COVERAGE_REPORT.md` | **generated.** The audit result. |
| `ROUTE_INDEX.md` | **generated.** Every route as feedstocks → intermediates → products. |
| `PLAYABLE.md` | **generated.** *What can a player make, starting from what?* The tech tree scored from natural materials, and the only artefact here that RUNS anything. |
| `derived/route_roles.psv` | **generated.** The same split, machine-readable. |
| `derived/species_roles.psv` | **generated.** Per species: how often it is a feedstock / intermediate / product / catalyst across all routes, plus its resolution tier. |

Regenerate everything:

```
python tools/catalog.py             # structural validation only
python tools/build_route_index.py   # writes ROUTE_INDEX.md
python validation/catalog_coverage.py  # writes COVERAGE_REPORT.md + derived/
python tools/build_playable.py      # writes PLAYABLE.md -- ~1 min, it RUNS the deep chain
```

⚠⚠ **THE THREE REPORTS ANSWER THREE DIFFERENT QUESTIONS AND ARE ROUTINELY
CONFUSED FOR ONE.** `COVERAGE_REPORT.md` asks *can the engine do this chemistry*,
which is a question about the ENGINE. `ROUTE_INDEX.md` asks *what is a feedstock
here*, which is a question about the CORPUS. `PLAYABLE.md` asks *can a player get
to it from a rock* -- and it is the only one of the three whose answer is not a
property of either, because G1 measured a route's yield moving 4.5x on a change
that touched no species and no template. **A route can be fully covered, fully
indexed, and unreachable.** Measured: 36 routes are runnable and **12** are
playable.

⚠ **AND `PLAYABLE.md` HAS TESTS BEHIND IT, WHICH IS THE ONE THING THE STALE-INDEX
FINDING BELOW ASKED FOR.** `tests/test_playable.py` pins its headline numbers and
its four scoring rules, so it cannot go stale in silence the way the index did --
and that assertion caught a real bug in the generator on its first run.

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



### ⚠⚠⚠ C4: `fermentation` was the fifth outcome label, and its lump was a LINE BREAK

M5 refused `fermentation` as *"a metabolic **network**, not a transformation"* and
left it as one class over five rows. It is the same fault as `acid-base` and
`combustion` above, with one extra twist: **the row the class is sold on looked
like a lumped network because three reactions were written on one line.**

| was | steps | became | why |
|---|---:|---|---|
| `fermentation` | 5 | `solventogenic-fermentation` (1) | `abe-fermentation`: anaerobic clostridial ABE. **BUILT** — three templates, one per branch |
| | | `homolactic-fermentation` (1) | `lactic-acid-pla`: two lactates per hexose and **no gas at all**. **BUILT** |
| | | `aerobic-overflow-fermentation` (1) | `citric-acid-fermentation`: a mould, O₂ consumed, overflow of a blocked TCA cycle. Gap |
| | | `amino-acid-fermentation` (1) | `msg-route`: overflow **plus reductive amination** — a nitrogen source in the equation. Gap |
| | | `secondary-metabolite-fermentation` (1) | `penicillin-route`: biosynthesis on a **fed precursor** (phenylacetic acid). Gap |

⚠⚠⚠ **THE SPLIT IS WHAT MADE THE CREDIT HONEST, AND THE FALSE CREDIT WAS FOUND
BY READING THE ROWS RATHER THAN BY RUNNING ANYTHING.** A template written off
`abe-fermentation` cannot make citric acid, glutamic acid or penicillin G out of
a sugar. Crediting the old five-row class off it would have made four routes
template-ready that `build_network` cannot run — G4's *only RUNNING it said so*,
arriving **before** the run for once. ⚠⚠ **The headline cost is +4 on the
DENOMINATOR (236 → 240) against +2 covered**, which is S7's rule: *a split that
lowers the headline is a split working.*

⚠⚠ **AND THE LUMP WAS NOT A NETWORK.** `abe-fermentation` 1 is written 1:1 and
balances only at `5 C6H12O6 -> 2 acetone + 2 butanol + 2 ethanol + 12 CO2 +
8 H2` — five sugars in and six carbon skeletons out. Split into the branches it
actually is, each balances **exactly on ONE glucose**:

    glucose        -> 2 ethanol + 2 CO2            C6H12O6 both sides, EXACT
    glucose        -> 1-butanol + 2 CO2 + H2O      C6H12O6 both sides, EXACT
    glucose + H2O  -> acetone + 3 CO2 + 4 H2       C6H14O7 both sides, EXACT

⚠⚠⚠ **SO `corpus_balance` NOW HAS TWO STANDING EXAMPLES OF A ROW THAT PASSES AND
IS NOT ITS OWN REACTION, AND THEY NEED OPPOSITE ANSWERS.** `vanillin-lignin` is
short a **PRODUCT** and is deliberately left wrong, because the missing fragment
is a mixture in lignin liquor. `abe-fermentation` was short a **LINE BREAK** and
could just be split. *A coefficient vector cannot tell those apart; only reading
the chemistry can.* Both rows are inside the BOTH column now.

⚠ **THE ROW THAT IS NOT IN THIS SPLIT IS THE ONE THE CORPUS ALREADY DID RIGHT.**
`ethanol-fermentation` never carried `fermentation`: its four steps are
`glycoside-hydrolysis`, `glycolysis`, `decarboxylation` and
`biological-reduction`. **The corpus asks for a LUMP by labelling five rows
`fermentation` and asks for a mechanism by labelling those four**, and reading
that distinction is what said a lump was the honest template here rather than a
shortcut.

### ⚠ And a spelling in the compound files can select a DATA TIER (C4)

Not a taxonomy point, but it lives in these files. **146 of 1583 compound rows
spell a stereocentre**, and for **31** of them flattening the SMILES changes
which source prices the compound — because the property tables are keyed by
canonical SMILES and the two halves of a record are keyed the **opposite way
round**:

* the **PHYSICAL** tables carry the chiral spelling. Sorbitol reaches a measured
  Tb chiral (704.0 K) and falls to Joback flat (888.2 K) — **184 K apart**. 29
  rows are that shape: limonene, the pinenes, camphene, menthol, borneol,
  linalool, camphor, carvone, menthone, fenchone, xylitol, lindane.
* the **FORMATION** table carries the FLAT spelling. `lactic-acid` flat reaches
  an experimental record; the corpus's `C[C@H](O)C(=O)O` misses it and falls to
  Benson, 107 K apart in Tb.

⚠⚠ **A spelling carries no thermochemical information at all** — no estimator
here tells one enantiomer from another (S7, re-measured on lactic acid in C4) —
**so for these 31 compounds the data tier is an orthographic accident.** The fix
is a stereo-insensitive **FALLBACK** in the provider's lookup (S6's rule: a
fallback, never an override), which touches every number in the project and is
therefore a session of its own. `validation/fermentation.py` panel 8 measures it;
`tests/test_fermentation.py` pins the 146 so a data session has to come here and
say what it changed.


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

### ⚠⚠ S7 SPLIT `combustion` — AND IT IS THE FIRST SPLIT THAT COST A ROUTE

Six rows under one label, credited to `sulfur_combustion` since M1. That
template's SMARTS is `S8 + 8 O2 -> 8 SO2`, so it fires on **two** of the six and
the other four were credited on a template that cannot match their reactants.
The M1 row check, arriving eight milestones late:

| route | step | became | what it is | covered? |
|---|---|---|---|---|
| `lead-chamber` 1 | `S8 + O2 -> SO2` | `sulfur-combustion` | the burner, unchanged | ✔ `sulfur_combustion` |
| `contact-process` 1 | `S8 + O2 -> SO2` | `sulfur-combustion` | the same burner | ✔ `sulfur_combustion` |
| `claus-process` 1 | `H2S + O2 -> SO2 + H2O` | `hydrogen-sulfide-combustion` | a HYDRIDE burning; it makes water | ✔ **built by S7** |
| `blast-furnace` 1 | `C(gr) + O2 -> CO2` | `carbon-combustion` | a solid lattice burning | ✘ named gap |
| `ethylene-oxide-route` 2 | `C2H4 + O2 -> CO2 + H2O` | `hydrocarbon-combustion` | total combustion of an organic | ✘ named gap |
| `match-chemistry` 1 | `KClO3 + P4 -> P2O5 + KCl` | `chlorate-oxygen-transfer` | **nothing burns in air** | ✘ named gap |

⚠ **THE LAST ROW IS NOT COMBUSTION AT ALL, AND THAT IS THE CLEAREST SIGN THE
LABEL WAS AN OUTCOME.** A match head is a solid oxidiser handing its oxygen to a
solid fuel on friction. There is no air in it and no flame until after it goes.
Calling it combustion filed it under a template about a sulfur ring.

⚠⚠ **AND THE SPLIT COSTS A TEMPLATE-READY ROUTE. THAT IS NEW.** Every previous
split here (`roasting`, `thermal-decomposition`, `electrolysis`) either held the
headline or moved it up. This one moves it DOWN: `match-chemistry` was
template-ready only because of this credit, and it now is not. It was never
species-ready, so the intersection — the only column a route can be judged on —
does not move for it. **A split whose measured effect is negative is a split
doing its job, and this is the first one to prove it.**

### ⚠⚠ S9 SPLIT `carbothermic-reduction` — FIVE ROWS, FOUR MECHANISMS

The class was one label over four different things that happen to have coke on
the left. S9 built the OXIDE one and split the rest out rather than credit them:

| route | step | became | what it is | covered? |
|---|---|---|---|---|
| `zinc-smelting` 2 | `ZnO + C -> Zn(g) + CO` | `carbothermic-oxide-reduction` | carbon takes the oxygen and leaves as CO; the metal is freed **as a VAPOUR that condenses in a cool receiver** | ✔ **built by S9, and S10 made the zinc a gas** — dG = 0 moved 1264.2 → **1197.8 K**, toward the literature |
| `frank-caro` 1 | `CaO + C -> CaC2 + CO` | `carbide-formation` | ⚠ **the carbon ends up IN the product** as well as leaving | ✘ named gap |
| `calcium-carbide` 1 | `CaO + C -> CaC2 + CO` | `carbide-formation` | the same furnace | ✘ named gap |
| `white-phosphorus` 1 | `Ca3(PO4)2 + SiO2 + C -> P4 + CO + CaSiO3` | `carbothermic-phosphate-reduction` | needs a SLAG FORMER to displace the phosphate first | ✘ named gap |
| `leblanc-process` 2 | `Na2SO4 + C + CaCO3 -> Na2CO3 + CaS + CO2` | `carbothermic-sulfate-reduction` | the SULFUR is reduced, not removed, and there is a metathesis on top | ✘ named gap |

⚠ **CREDITING THE WHOLE CLASS ON THE OXIDE ROW WOULD HAVE BEEN
`roasting-to-metal`'s FALSE CREDIT IN A FOURTH COSTUME.** A term that turns an
oxide into its metal cannot make a carbide — the carbon is on the wrong side of
the reaction — and it cannot slag a phosphate. Two of those routes would have
moved into the template-ready list on the strength of a mechanism that does not
make their products.

⚠ **THE SPLIT COSTS NOTHING AND MOVES THE DENOMINATOR (224 → 227; S9's second
split takes it to 229).** None
of the four uncovered rows was ever credited, so no route loses anything —
unlike S7's `combustion` split, which cost `match-chemistry` its
template-readiness. Both are correct; the difference is only whether the old
credit was live.

⚠ **AND THE QUEUE HAD PRICED THE WRONG REACTION FOR THE ROW THAT DID GET BUILT.**
`NEXT_PROMPT` carried S8's measurement that `ZnO + CO -> Zn + CO2` is **uphill at
+63.3 kJ/mol** and warned the class might need engine work. The catalog's own row
is not that reaction — it is the CARBON one, where the entropy of making a mole
of CO carries it, dG = 0 at **1264.3 K** against a real Belgian retort's
1200–1300. It needed no engine work at all: two solid reactants and one gas
PRODUCT is an ordinary row of M6's table. **Read the row, not the class name.**

### ⚠⚠ S9 ALSO SPLIT `catalytic-gas-oxidation` — A FALSE CREDIT ON TWO OF ITS THREE ROWS

Found while RANKING the work queue, not while building anything, which is the
second time a class has come apart under that check. All three rows are "a gas
oxidised in air over a solid catalyst" and **all three are different reactions**:

| route | step | became | covered? |
|---|---|---|---|
| `deacon-process` 1 | `HCl + O2 + CuCl2 -> Cl2 + H2O` | `catalytic-hydrogen-chloride-oxidation` | ✔ `deacon_oxidation` |
| `contact-process` 2 | `SO2 + O2 + V2O5 -> SO3` | `catalytic-sulfur-dioxide-oxidation` | ✘ **nothing makes this** |
| `ostwald-process` 1 | `NH3 + O2 + Pt -> NO + H2O` | `catalytic-ammonia-oxidation` | ✘ **nothing makes this** |

⚠⚠ **AND THE NEAR-MISS IS THE PART WORTH KEEPING: THE OBVIOUS READING IS THAT
`sulfur_dioxide_oxidation` COVERS THE CONTACT-PROCESS ROW, AND IT DOES NOT.**
That template is `SO2 + NO2 + H2O -> H2SO4 + NO` — the lead chamber's core step —
and it is credited to `redox-oxygen-transfer`. **A template's NAME is not its
SMARTS**, and the same trap already caught `combustion`/`sulfur_combustion` in S7.

⚠ **HEADLINE EFFECT: ZERO ON BOTH COLUMNS.** `deacon-process` keeps its credit,
and neither of the other two routes was template-ready anyway. What it removes is
a RANKING error: `ostwald-process` was being counted as **one class away** when
it is two, so it was sitting near the top of the work queue on a credit it never
had. Classes 227 → 229.

### S9 CREDITED `gas-solid-reduction` — AND THE FOUR ROWS ARE ONE MECHANISM

No split needed, which is worth recording because the row check is usually where
a class comes apart. All four are `MO + CO -> M(or a lower oxide) + CO2`:

| route | step | runs? |
|---|---|---|
| `copper-smelting` 2 | `CuO + CO -> Cu + CO2` | ✔ |
| `lead-smelting` 2 | `PbO + CO -> Pb + CO2` | ✔ |
| `blast-furnace` 3 | `Fe2O3 + CO -> FeO + CO2` | ✘ `iron-ii-oxide` has no lattice |
| `blast-furnace` 4 | `FeO + CO -> Fe + CO2` | ✘ the same mineral |

⚠ The two that do not run are blocked on a SPECIES and not on the mechanism —
`mineral_data` refuses FeO because CRC does not tabulate its crystal Cp — which
is the column this taxonomy counts separately.

### S9 ALSO CREDITED `boudouard` AND `carbon-combustion` FOR **ZERO** ROUTES

Both are `blast-furnace`'s, and that route is still blocked on `slagging` (no
template, and neither `silicon-dioxide` nor `calcium-silicate` has a lattice) as
well as on the FeO above. So they are here for a MECHANIC, said out loud rather
than left to be inferred from a class count: **with them a flask of ore, coke and
air makes metal, and without them the same flask has to be handed a carbon
oxide.** S9 measured that flask at exactly zero conversion on four tolerance
rungs. `blast-furnace` is now **one class and one mineral away**, the closest any
five-step route has been.

### S7 BUILT FOUR INORGANIC GAS PROCESSES — AND CHOSE THEM OFF A THIRD COLUMN

| route | step | class | what covers it |
|---|---|---|---|
| `water-gas-shift` 1 | `CO + H2O <=> CO2 + H2` | `water-gas-shift` | `water_gas_shift`, over hematite |
| `steam-reforming` 1 | `CH4 + H2O <=> CO + 3 H2` | `steam-reforming` | `steam_reforming`, over nickel |
| `deacon-process` 1 | `4 HCl + O2 <=> 2 Cl2 + 2 H2O` | `catalytic-hydrogen-chloride-oxidation` (⚠ S9 renamed it — see below) | `deacon_oxidation`, over tenorite |
| `claus-process` 1,2 | `H2S + O2`, then `2 H2S + SO2` | two classes | `hydrogen_sulfide_combustion` + `claus_comproportionation` |

**Every one of the four was charged into a real `Vessel` and integrated** —
`validation/gas_processes.py`, which is a standing audit. What it measures is the
part nothing declares:

* the **shift** peaks at 620 K (81.3%) and falls to 55.6% at 900 K, because dH is
  −41.15 kJ/mol and K falls with T. Below 620 K it is the barrier that limits it,
  above it the equilibrium. That is why a real ammonia plant shifts twice;
* the **reformer** is 0.01% converted at 700 K and 36.1% at 1300 K, and thinning
  the same 1100 K flask from 54 bar to 0.63 bar takes it from 18.6% to 73.5% —
  the one gas equilibrium in this project that pressure *hurts*;
* **Deacon**'s ceiling and rate cross between 600 and 700 K: 90.6% in ten seconds
  at 600 K rising to 91.2% in an hour, against 84.6% at 700 K reached in ten
  seconds and never bettered. The whole industrial history of the process;
* **Claus** recovers 100.0% of its sulfur at exactly the stoichiometric air rate
  and less on either side, because burning one third of the H2S is what leaves
  the 2:1 H2S:SO2 the second template wants. **Neither template knows the other
  exists.**

⚠⚠ **THE TWO CLASSES AT THE TOP OF THE `RUNNABLE` QUEUE WERE MEASURED FIRST AND
BOTH ARE WORTH ZERO HONEST ROUTES.** That measurement is why the four above are
the four:

| class | queue said | measured |
|---|---|---|
| `isomerisation` | +3 / **+2 runnable** | **three rows, three mechanisms, three separate failures** |
| `crosslinking` | +2 / **+2 runnable** | **both products are unbuildable** |

`isomerisation`, row by row — the split M5 refused to do blind, done:

* `hydrogenation-margarine` 2, `oleic + H2 + Ni -> elaidic + Ni`. **The row does
  not balance** (an H2 goes in and nothing comes out) — and behind that, the
  engine prices oleic and elaidic acid at **dH = dG = 0.000 EXACTLY**, because no
  estimator here can tell a cis alkene from a trans one. A template would report
  a confident 50:50 for a real ~5:1. ⚠ The data to fix it EXISTS and is not
  usable as it stands: WEBBOOK has both liquid enthalpies, −764.8 and −769.0
  kJ/mol, a 4.2 kJ/mol difference that agrees with Benson's own historical cis
  correction of 4.18 — but neither has an S0, so no Gf can be derived, and
  grafting Benson's old NNI term onto RMG-fitted group values mixes two bases;
* `starch-hydrolysis` 3, `glucose -> fructose`. Priced at **dG +41.8 kJ/mol,
  K = 4.8e-08** — the engine would say high-fructose corn syrup is impossible.
  The cause is in the corpus rather than the engine: glucose is spelled as a
  **pyranose** and fructose as a **furanose**, and Benson charges the ring-size
  difference. Two independent problems, one row;
* `wohler-urea` 2, `ammonium-cyanate -> urea`. Not species-ready at all —
  `[NH4+].[O-]C#N` is a dot-separated ionic pair and cyanate is in no ion table
  here.

`crosslinking`, both rows:

* `tanning-route` 2 makes `tanned-leather-marker`, which has no molecular graph;
* `vulcanisation` 1 makes `vulcanised-rubber-marker`, spelled
  `CC(C)=CC.S1SSSSSSS1` — **its own two reactants written side by side.** The
  "reaction" is `A + B -> A.B`, which nothing makes. Joback priced that mixture
  at **+222.11 kJ/mol above the sum of its own two parts**, and that measurement
  is what closed the neutral-fragment hole in `properties/thermochemistry.py`.

⚠⚠ **SO `RUNNABLE` HAS THE SAME SHAPE OF FAULT `ALONE` HAD, AND IT IS WORTH
STATING AS A RULE.** `ALONE` counts a template's routes and cannot ask whether
the species are priced. `RUNNABLE` adds that bar and cannot ask two more:

1. **is the number that comes back RIGHT?** Both `isomerisation` rows that price
   price *wrongly* — one at exactly zero, one by 40 kJ/mol. No column can see it;
   only pricing the row and reading the answer can.
2. **is the row's PRODUCT a graph at all?** This one *can* be mechanised, and S7
   did: a route with a marker on the product side of any step is now excluded
   from the RUNNABLE column, which takes `crosslinking` to **+0** and
   `oxidative-complexation` off the top twenty. ⚠ It moves no route in the BOTH
   column — checked, not assumed.

**Read the rows, not the ranking.** Three milestones running, the ranking has
been wrong about its own top entry.

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

### ⚠⚠⚠ C1 TRIPPED THIS LANDMINE ON PURPOSE, AND THE ROW IS CORRECTED NOW

The paragraph above ends *"whoever builds it owes this row a second look"*, and
C1 is that session: it built `sulfur-trioxide-hydration`, which is the half of
the old `hydrolysis` bucket that `vitriol-distillation` step 2 needed. **The row
is corrected**, to the reaction the engine has declared since M6:

    was   iron-ii-sulfate -> iron-ii-oxide + sulfur-trioxide
    now   iron-ii-sulfate -> iron-iii-oxide + sulfur-dioxide + sulfur-trioxide

⚠ **AND THE `diels-alder-route` PRECEDENT ABOVE DOES NOT COVER IT, WHICH IS THE
DISTINCTION WORTH KEEPING.** That precedent forbids *inventing* chemistry inside
the corpus — writing a product nobody sourced so that a row will balance. Here
the product is already sourced, by a `SolidStateReaction` that has been in
`properties/solid_state.py` for six milestones with its own written argument for
why FeO is wrong. The corpus was disagreeing with the engine, and the engine's
side of the disagreement is the one with a citation on it. *A corpus edit that
copies a sourced declaration is not the same act as one that fills a gap.*

⚠ Measured before making it: `validation/corpus_balance.py`'s headline is
**unchanged at 75 unbalanceable steps across 61 routes**, and it was unchanged
before too — the OLD row balances as well (`FeSO4 -> FeO + SO3` conserves every
element). **So the balance audit could not have found this and cannot confirm
it**, which is S12's finding pointing the other way: there, a row that looked
spurious was real; here, a row that balances perfectly was wrong.

⚠ What the correction moved, measured: `iron-ii-oxide` is REFUSED a price and
`iron-iii-oxide` is not, so species-ready routes went **82 → 83** on the row
alone. The route was blocked on a datum for a species that was never in its
chemistry.

### ⚠⚠ AND `hydrolysis` ITSELF WAS AN OUTCOME LABEL, WHICH IS WHY C1 SPLIT IT

The paragraph above calls `hydrolysis` *"the 4th-best template to build"*. It was
not a template-shaped thing at all. Eight rows sat under it and this taxonomy
already carried `amide-`, `ester-`, `epoxide-`, `glycoside-`, `nitrile-`,
`isocyanate-` and `disproportionation-hydrolysis`: everything it knew how to
name had been named, and `hydrolysis` was the bin for the rest.

| row | reaction | new class | covered |
|---|---|---|:-:|
| `contact-process` 4 | H2S2O7 + H2O -> 2 H2SO4 | `oleum-hydrolysis` | ✘ |
| `vitriol-distillation` 2 | SO3 + H2O -> H2SO4 | `sulfur-trioxide-hydration` | ✔ |
| `leblanc-process` 4 | CaS + H2O + CO2 -> CaCO3 + H2S | `sulfide-carbonation` | ✘ |
| `frank-caro` 3 | CaCN2 + H2O -> NH3 + CaCO3 | `cyanamide-hydrolysis` | ✘ |
| `castner-kellner` 2 | Na(Hg) + H2O -> NaOH + H2 + Hg | `amalgam-decomposition` | ✘ |
| `calcium-carbide` 2 | CaC2 + H2O -> C2H2 + Ca(OH)2 | `carbide-hydrolysis` | ✘ |
| `furfural-route` 1 | xylose + H2O -> xylose | `pentosan-hydrolysis` | ✘ |
| `grignard-route` 3 | R-OMgBr + H2O -> R-OH | `organometallic-protonolysis` | ✘ |

⚠ **THE SPLIT MOVES THE DENOMINATOR BY SEVEN AND THE NUMERATOR BY ONE** —
`52/229 → 53/236`. That is S7's shape: a split that lowers the headline is a
split working. Crediting all eight off one SMARTS is the false credit S1, S9 and
G4 each measured separately.

⚠ **`oleum-hydrolysis` IS THE NEAR-MISS AND IT IS DELIBERATELY NOT CREDITED.**
`sulfur_trioxide_hydration` matches `[SX3]` with three terminal oxygens;
disulfuric acid's two sulfurs are both `[SX4]` and it does not match — asserted
in `tests/test_vitriol.py`. `contact-process` step 4 stays a gap, and its
`disulfuric-acid` is refused a price anyway, so that route is blocked twice.

⚠⚠ **AND ONE ROW'S CLASS WAS DECIDED RATHER THAN DERIVED.** `furfural-route`
step 1 is chemically a glycoside hydrolysis, and this taxonomy's own convention
would file it under the **covered** `glycoside-hydrolysis`. It is not there,
because the row as spelled is `xylose + water -> xylose` — its products a subset
of its reactants, one of the five rows no template can ever match — so a covered
class would manufacture a credit for a row that cannot run. ⚠ Measured both ways:
it costs **zero either way today**, because the route needs three more classes as
well. *A false credit is cheapest to refuse before it can pay*, and the
measurement of what it is worth is in `validation/vitriol.py` panel 6.

### ⚠⚠⚠ C2's LANDMINE, WITH ITS TRIGGER NAMED — A SULFIDE ROUTE WILL SCORE AND NOT RUN

C1 proved that a recorded landmine with a named trigger is the cheapest
documentation this project writes. Here is C2's, in the same form, and it is the
same failure C2 itself walked into.

**A compound spelled as its IONS is priced fragment by fragment, through
`electrolyte_provider` — which reaches an ion only through a pKa pair somebody
typed into `properties/electrolyte.py`.** `properties/ion_data.py` is a *different*
table on a *different* zero, and it is bigger. Nothing anywhere compares which
ions the two of them HAVE. `phosphoric-wet` and `superphosphate` read
species-UNREADY for three milestones and the recorded reason was a missing
**mineral price**; the actual reason was that phosphoric acid's chain stopped at
the second proton, so `[O-]P([O-])([O-])=O` had no price and the salt could not
resolve.

⚠⚠ **THE TRIGGER: the day anything credits a route through a metal SULFIDE in
solution — `[S-2]` — that route will read species-ready and its network will
REFUSE to build.** `_PAIRS` carries `H2S -> [SH-]` at pKa 7.00 and stops there,
exactly as phosphoric acid did. Five lattices are already in this state, priced
with a real Ksp and unbuildable in a flask: **`sphalerite`, `galena`,
`covellite`, `chalcocite`, `cinnabar`** (the last two also on `[Cu+]` and
`[Hg+2]`, which have no neutral conjugate base at all).

⚠⚠⚠ **C3 SCOUTED ONE OF THOSE FIVE AND NARROWED THIS TRIGGER — THE THREE WORDS "IN SOLUTION" ABOVE ARE LOAD-BEARING AND EVERY SHORT RESTATEMENT OF THIS SECTION DROPS THEM.** This section's own heading says *"a sulfide route will score and not run"*, and so did the one-liners in `NEXT_PROMPT.md` and the memory notes. **`vermilion-route` is a sulfide route and, read out of the code, it is not in danger:** its product is cinnabar as a SOLID, and `SurfaceArrays` prices a lattice off `mineral_data` on the solid basis without ever reaching for an ion pKa — `cinnabar-roasting` has charged that same lattice into a flask since S1. **What this landmine actually covers is a sulfide that has to DISSOLVE**, which is the precipitation path and nothing else.

⚠ Not verified in a flask; C3 read it out of `vessel.py` while pricing a row it did not take. What blocks `vermilion-route` instead is that a `SurfaceReaction` solid participant must be a `mineral_data` lattice and **there is no `sulfur` MineralRecord** — native sulfur is the molecular `S1SSSSSSS1`. *A landmine is only as well-scoped as its shortest restatement.*

⚠⚠ **AND THE FIX IS NOT A ONE-LINE pKa, WHICH IS WHY THIS IS A LANDMINE AND NOT
A TO-DO.** `HS- -> S2-` is quoted anywhere between about **12.9 and 19**
depending on the compilation — six decades of disagreement about one number —
so `element_data`'s rule applies: report it, do not invent it. Phosphoric acid's
third pKa was takeable *because* the two rows above it in the same table fix
which series it has to come from (2.15 / 7.20 / **12.35**). There is no such
anchor for the sulfide.

⚠ `validation/phosphate_rock.py` panel 3 re-measures the whole gap every time it
is run, so the count cannot go stale and the next session does not have to
rediscover the shape.

⚠⚠ **AND THE SECOND HALF OF C2 IS THE WARNING THAT PRICING THE ION IS NOT
ENOUGH.** A pKa makes the route SCORE; a `MineralRecord` in
`properties/mineral_data.py` is what gives the lattice a Ksp and lets it actually
dissolve. C2 measured both, one at a time: with the pKa and no mineral row,
`phosphoric-wet` counts as species-ready, counts in the BOTH column, counts as
playable — and the rock sits in the solid block at **0.0000 % converted, for
ever.** *Whoever closes a sulfide route owes it both rows and a run.*


### ⚠⚠⚠ C3 BUILT A CLASS S11 HAD REFUSED — AND THE REFUSAL WAS ABOUT ONE OF ITS TWO ROWS

S11 attempted `oxidative-cleavage`, found its row unbalanceable, and refused the
class. The reason it gave was correct and its SCOPE was not:

| row | 1:1 balance | the C2 fragment |
|---|---|---|
| `vanillin-lignin` 1 — `coniferyl alcohol + O2 + NaOH -> vanillin + water + NaOH` | **C10H12O5 → C8H10O4, NO** | not named |
| `vanillin-eugenol` 2 — `isoeugenol + O2 -> vanillin + acetaldehyde` | **C10H12O4 both sides, EXACT** | **named** |

S11 read the first line. The second is the same class, balances exactly, and
names the fragment — so the class is built off it, and the fragment the lignin
row omits turns out to be **`glycolaldehyde`, which `07-carbonyls.psv` has
carried all along** as "simplest sugar". **The mechanism supplies the fragment
and the corpus supplies its name; nothing is invented.**

⚠⚠ **THE RULE, AND IT IS THE THIRD SESSION RUNNING TO FIND ONE OF THIS SHAPE.**

* **C1** — a route blocked on a price for a species **not in its chemistry**.
* **C2** — a route blocked on a price **in a different table** from the one named.
* **C3** — a **class refused on the evidence of one of its rows.**

**Read every row of a class before refusing the class**, exactly as C1 and C2
say to print the refusal before costing it. ⚠ S11's own reason survives intact
where it was aimed: the lignin row IS still wrong, and
`validation/corpus_balance.py`'s last panel now says which half of the refusal
stands and which was over-scoped.

⚠ **AND THE ROW WAS LEFT WRONG ON PURPOSE.** On coniferyl alcohol the mechanism
is unambiguous — the side chain leaves as glycolaldehyde and the flask says so.
The catalog row is about alkaline **lignin liquor**, where the C2 fragment is a
mixture depending on which monolignol reacted, so writing one name into the
corpus would over-commit it in exactly the way S11 refused to. **The template
names the fragment where it can be known; the row keeps its wrong product and a
panel that says so.**

⚠ `alkene-isomerisation` is **not** S7's refused `isomerisation`. That class was
refused because its three rows are three mechanisms and one of them —
`oleic -> elaidic` — prices at **dH = dG = 0.000 exactly**, no estimator here
telling a cis alkene from a trans one. This is a *constitutional* isomerisation,
the allyl migrating into conjugation with the ring, and it prices at dH −56.56
kJ/mol with ln K +7.89 at 470 K. **The distinction is measured, not asserted** —
and the same cis/trans finding that refused one class is what LICENSES this
template leaving its product's geometry undeclared.

### ⚠⚠⚠ C3's LANDMINE, WITH ITS TRIGGER NAMED — A MARKER ON THE RIGHT SCORES AND CANNOT BUILD

The eight markers above have no molecular graph, deliberately.
`catalog.route_reachable` blocks a route whose **reactant** is one — `coal-gas`
is correctly dead, its only feedstock being a rock with no graph. **It does not
look at one the route MAKES.**

⚠⚠ **THE TRIGGER: the day anybody builds `oxidative-complexation`,
`iron-gall-ink` will read template-ready and `build_network` will have no graph
to make `iron-gallate-marker` from.** `PLAYABLE.md` §8b scores that class at
**+1** today, which makes it a live false credit in the work order rather than a
hypothetical. The same shape sits at +0 on `castner-kellner` /
`sodium-amalgam-marker`, through `amalgam-decomposition` and
`amalgam-electrolysis`.

⚠ This is G4's *"three false credits in one session, all three caught by
charging a flask"* reached through the marker convention instead of through the
chemistry — and §8b's own detector had this same bug in its first version,
blaming `pyrolysis`/`coal-gas` where the marker is on the LEFT and the route was
already dead. **A false-credit detector needs the same does-it-actually-run
check as everything it audits.** *Whoever takes that row owes it a graph first.*

### ⚠⚠ C5's WART, FOUND WHEN A ROUTE WENT RUNNABLE AND NOT WHEN THE ROW WAS WRITTEN

`furfural-route` step 1 reads **`xylose + water -> xylose`**. The corpus has no
pentosan or xylan graph — a hemicellulose is a polymer, and the marker convention
above is for things exactly like it — so the row uses its own PRODUCT as a
stand-in feedstock. That is an honest placeholder and it stayed harmless for as
long as the route was unrunnable.

⚠⚠ **A SPECIES ON BOTH SIDES OF A STEP IS EXACTLY WHAT `catalog.route_roles`
CALLS A CATALYST.** So the moment C5 made `furfural-route` runnable,
`PLAYABLE.md`'s `with_catalysts=False` counterfactual began handing the route's
actual SUGAR over for free and calling it playable — a route whose only feedstock
nothing in 173 routes makes.

⚠⚠⚠ **THE HEADLINE IS IMMUNE, AND THAT IS WORTH KNOWING RATHER THAN FIXING.**
`PLAYABLE.md`'s rule 2 — *a need is decided by ORDER, not by `route_roles`* — was
measured wrong first in G3 and corrected, and by order xylose is used at the step
that first makes it, so it is external and the route is correctly not playable.
**The artefact can only appear in the one counterfactual where `route_roles` still
gets to answer**, and it is asserted there in `tests/test_playable.py` so it
cannot be mistaken for a scoreboard going up. *A rule already known to be right is
what kept this out of the number the project quotes.*

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

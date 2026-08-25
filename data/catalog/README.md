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

## S7 — The four inorganic gas processes  ✅ **DONE 2026-08-26 — and the queue's top two rows measured ZERO before a line was written**

**+5 classes (38 → 43 of 224), +3 template-ready (31 → 34), +4 RUNNABLE
(20 → 24).** Five templates, no engine work in Layers 3–4, one refusal widened
in Layer 1, and two new standing audits. **The intersection moved +4, which is
the largest single-session move it has had.**

| | before | after |
|---|---:|---:|
| classes with a template | 38 / 220 | **43 / 224** |
| templates | 38 | **43** |
| routes species-ready | 65 | **63** |
| routes template-ready | 31 | **34** |
| ⚠⚠ **routes BOTH — the one to quote** | **20** | **24** |

⚠ **PREDICTED FIRST, ALL FIVE EXACTLY**: 43/224 classes, 43 templates, 34
template-ready, 24 BOTH, and species-ready holding at 65 before the refusal was
widened. The refusal then took it to 63, which was predicted as "≤ 4, and 0 in
the BOTH column" and measured at 2 and 0.

### ⚠⚠ 1. THE QUEUE'S TOP TWO ROWS WERE MEASURED BEFORE BEING COSTED, AND BOTH ARE WORTH NOTHING

`catalog_coverage`'s work queue is ranked by RUNNABLE — routes a class unlocks
that are also species-ready — which is the column M8 proved to be the
trustworthy one. Its top two rows were `isomerisation` (+3 / **+2 runnable**)
and `crosslinking` (+2 / **+2 runnable**). **Neither is worth a single honest
route, and the three reasons are all different:**

| row | measured |
|---|---|
| `hydrogenation-margarine` 2 `oleic + H2 + Ni -> elaidic + Ni` | **the row cannot be balanced** (an H2 in, none out) AND the pair prices at **dH = dG = 0.000 exactly** |
| `starch-hydrolysis` 3 `glucose -> fructose` | **dG +41.784 kJ/mol, K = 4.8e-08** — the engine would call high-fructose corn syrup impossible |
| `wohler-urea` 2 `ammonium-cyanate -> urea` | not species-ready: a dot-separated ionic pair, cyanate in no ion table here |
| `tanning-route` 2 | product is `tanned-leather-marker` — no molecular graph |
| `vulcanisation` 1 | product is `CC(C)=CC.S1SSSSSSS1` — **its own two reactants side by side** |

⚠ **THE CIS/TRANS ZERO IS THE ONE WORTH READING.** Benson has no cis correction
in the RMG group set this project uses, so oleic and elaidic acid come back with
*identical* Hf and Gf. A template on that row reports a confident 50:50 for a
real ~5:1. **The data to fix it exists and is not usable as it stands:** WEBBOOK
carries both liquid enthalpies, −764.8 and −769.0 kJ/mol, and that 4.2 kJ/mol
gap agrees with Benson's own historical cis NNI term of 4.18 to 0.4% — two
independent sources. But neither has an S0, so no Gf can be derived; and
grafting Benson's original correction onto RMG-fitted group values mixes two
bases, which is the trap `chemsim-benson-status` names. **Recorded as a route
in, not taken.**

⚠ **AND THE GLUCOSE ROW'S FAULT IS IN THE CORPUS, NOT THE ESTIMATOR.** Glucose
is spelled as a PYRANOSE and fructose as a FURANOSE, and Benson charges the
ring-size difference. Two independent problems on one row, and S3's *which one
is WRONG* question has a clear answer here for once: the corpus is.

⚠⚠ **SO `RUNNABLE` HAS THE SAME SHAPE OF FAULT `ALONE` HAD, AND IT IS WORTH
STATING AS A RULE.** `ALONE` counts routes and cannot ask whether the species
are priced. `RUNNABLE` adds that bar and cannot ask two more:

1. **is the number that comes back RIGHT?** Not mechanisable. One row prices at
   exactly zero and another 40 kJ/mol out, and no column can see either.
2. **is the row's PRODUCT a graph at all?** This one IS mechanisable, and S7
   mechanised it: a route with a marker on the PRODUCT side of any step is now
   excluded from the RUNNABLE column. `crosslinking` goes to **+0** and
   `oxidative-complexation` leaves the top twenty. ⚠ It moves no route in the
   BOTH column — checked, not assumed.

### 2. THE FOUR PROCESSES, AND THREE OF THEM ARE INTERESTING ONLY BECAUSE THEY ARE REVERSIBLE

| class | template | route |
|---|---|---|
| `water-gas-shift` | `water_gas_shift` over hematite | `water-gas-shift` |
| `steam-reforming` | `steam_reforming` over nickel | `steam-reforming` |
| `catalytic-gas-oxidation` (⚠ S9 SPLIT IT — see §S9) | `deacon_oxidation` over tenorite | `deacon-process` |
| `comproportionation` | `claus_comproportionation` | `claus-process` |
| `hydrogen-sulfide-combustion` | `hydrogen_sulfide_combustion` | `claus-process` |

Every equilibrium came out at its textbook value off this project's own tables
before a template existed — dH −41.15 against a book −41.2 for the shift, +206.2
against +206 for the reformer, −114.4 against −114.5 for Deacon. **What the
templates buy is behaviour nobody declared**, measured in
`validation/gas_processes.py`:

* the **shift** peaks at **81.3% at 620 K** and falls to 55.6% at 900 K. Below
  620 K the barrier limits it and above it the equilibrium does. Two reactors,
  hot then cold, and nothing says so;
* the **reformer** is **0.01% converted at 700 K and 36.1% at 1300 K**, and
  thinning the same 1100 K flask from 54 bar to 0.63 bar takes it from 18.6% to
  **73.5%** — the one gas equilibrium in this project that pressure *hurts*,
  because two moles go in and four come out;
* **Deacon**'s ceiling and rate cross between 600 and 700 K: 90.6% in ten
  seconds at 600 K climbing to 91.2% over an hour, against 84.6% at 700 K
  reached in ten seconds and never bettered. **The whole industrial history of
  the process is those two columns**;
* **Claus** recovers **100.0% of its sulfur at exactly 0.10 mol of O2 for 0.20
  of H2S** and less on either side, because burning one third of the feed is
  what leaves the 2:1 H2S:SO2 the second template wants. **Neither template
  knows the other exists.**

⚠ **THE CLAUS TEMPLATE HAS TWENTY-FOUR REACTANT SLOTS, AND S8 IS THE REASON.**
The chemistry is `2 H2S + SO2 -> 3 S + 2 H2O`; this project's sulfur is the S8
crown and a graph rewrite cannot write 3/8 of a ring, so the smallest whole
multiple is `16 H2S + 8 SO2 -> 3 S8 + 16 H2O`. Declared first order in each
reagent — the burner's decision, with a bigger number in it — and therefore
**not reversible**, which costs nothing at ln K +232.

⚠ **AND THE CONVERSION CEILING A REAL CLAUS TRAIN HAS IS NOT THERMODYNAMIC
HERE, YET THE VESSEL STILL FINDS ONE.** This equilibrium says 100%; what the
flask does at 500 K is CONDENSE the sulfur, because S8 boils at 717.8 K. That is
the sulfur condenser between the stages, and it is the vapour-pressure curve
rather than the equilibrium.

### ⚠⚠ 3. `combustion` WAS AN OUTCOME LABEL — AND THIS IS THE FIRST SPLIT WHOSE HEADLINE EFFECT IS NEGATIVE

Six rows under one label, credited to `sulfur_combustion` since M1. That
template's SMARTS is `S8 + 8 O2 -> 8 SO2`, so it fires on **two** of the six.

| route | step | became | covered? |
|---|---|---|---|
| `lead-chamber` 1, `contact-process` 1 | `S8 + O2 -> SO2` | `sulfur-combustion` | ✔ unchanged |
| `claus-process` 1 | `H2S + O2 -> SO2 + H2O` | `hydrogen-sulfide-combustion` | ✔ **built here** |
| `blast-furnace` 1 | `C(gr) + O2 -> CO2` | `carbon-combustion` | ✘ named gap |
| `ethylene-oxide-route` 2 | `C2H4 + O2 -> CO2 + H2O` | `hydrocarbon-combustion` | ✘ named gap |
| `match-chemistry` 1 | `KClO3 + P4 -> P2O5 + KCl` | `chlorate-oxygen-transfer` | ✘ named gap |

⚠ **THE MATCH ROW IS NOT COMBUSTION AT ALL**, which is the clearest sign the
label was an outcome: a solid oxidiser hands its oxygen to a solid fuel on
friction, with no air and no flame until after it goes.

⚠⚠ **`match-chemistry` LOSES TEMPLATE-READY FOR IT.** Every previous split here
— `roasting`, `thermal-decomposition`, `electrolysis` — held the headline or
raised it. This one lowers it. It was never species-ready, so the intersection
does not move, and **a split whose measured effect is negative is a split doing
its job.** This is the first one in the project to prove that.

### ⚠⚠ 4. A NEUTRAL MULTI-FRAGMENT SMILES WAS PRICED, AND THE RECORDED REASON FOR ALLOWING IT WAS MEASURED FALSE

`thermochemistry._refuse_outside_estimator_domain` refused a dot-separated
SMILES only when a fragment carried CHARGE. Its docstring said why: *"a neutral
multi-fragment SMILES (a hydrate, a co-crystal) is deliberately left alone:
nothing in this project produces one, so refusing it would widen the blast
radius for no measured gain."* **Both halves are false.** The catalog carries
**eleven**, and:

| species | whole | its fragments | gap |
|---|---:|---:|---:|
| `vulcanised-rubber-marker` `CC(C)=CC.S1SSSSSSS1` | **+273.70** (Joback) | −48.83 + 100.42 = +51.59 | **+222.11** |
| `nbr-marker` `CC(C#N).CC=CC` | −17.33 (Joback) | +46.16 | **−63.49** |
| `sbr-marker` | +15.61 (Benson) | +16.43 | −0.82 |
| `butyl-rubber-marker`, `nylon-66-salt` | Benson | — | **+0.00 exactly** |

⚠⚠ **IN AN IDEAL GAS THE SUM IS AN IDENTITY, NOT AN ESTIMATE.** There are no
intermolecular interactions, so the record for a collection of fragments IS the
sum of theirs. **Benson honours it because it is additive over groups; Joback
does not**, because its correlation has a constant term and non-linear terms, so
two disconnected fragments double-count the constant. So the refusal is now on
the FRAGMENT COUNT and the charge only decides which message is printed.

⚠ **AND THE AUDIT WAS DISAGREEING WITH THE PROVIDER IT AUDITS.**
`catalog_coverage.audit_compound` treated *any* dot as ionic and priced
fragment-by-fragment, so all nine kept resolving after the engine stopped
pricing them. That is right for a salt — the electrolyte path really does hold
the two ions — and wrong for a neutral mixture, which `builder` canonicalises
into ONE species. Fixed to ask about the whole species unless a fragment is
charged. **Cost: 9 compounds to `refused`, 2 routes out of species-ready
(`vulcanisation` and `nylon66-route`, both lattice-carried), and 0 in the BOTH
column.**

### ⚠⚠ 5. NOTHING HAS EVER CHECKED THAT A CATALOG ROW BALANCES

`tools/catalog.py`'s `validate` checks that every SMILES parses, every species id
exists and every route's target is made by one of its own steps. **It has never
checked that a step conserves matter.** `validation/corpus_balance.py` is that
check, and the question is not "does it balance as written" — the corpus carries
no coefficients on purpose — but **does a strictly positive coefficient vector
exist**, an LP feasibility problem over the element-and-charge matrix.

**Measured: 75 of 367 testable rows cannot be balanced by any positive
coefficients.** Classified, because the three kinds cost different things:

| kind | n | what it is |
|---|---:|---|
| `spurious` | 17 | a reagent consumed on paper and nowhere else. `hydrogenation-margarine`'s hydrogen; `perkin-route`'s sodium acetate, which is the BASE |
| `charge` | 1 | elements balance, charge does not — an ionic half-row |
| `atoms` | 57 | an element with no source. Mostly deliberate (`anthracene + K2Cr2O7 -> anthraquinone + water` never says what became of the chromium); a few are plain mistakes (`indican + oxygen -> tyrian-purple + water` needs bromine and there is none on the left) |

⚠⚠ **AND IT TOUCHES THE HEADLINE EXACTLY ONCE.** One of the 24 BOTH routes
carries an unbalanceable step: `perkin-route` step 1. It is **inert**, because
`perkin_condensation`'s SMARTS is on the aldehyde and the anhydride and never
mentions the base. `vitriol-distillation`'s landmine in a milder form: the class
is credited, the ROW is wrong, and the two do not meet.

⚠ **NOT FIXED, ON THE `diels-alder-route` PRECEDENT.** Inventing chemistry
inside an audit corpus is not allowed. 61 of 173 routes carry at least one such
row; this is a third readiness bar, reported so it cannot rot, not a to-do list.

### ⚠ 6. THE NEW ROW IN THE RATE-CEILING AUDIT, FOUND ON ITS FIRST RUN

`deacon_oxidation_rev` crosses the bimolecular collision ceiling at **1141 K** —
the COLDEST of the high-order reverse rows, below `ammonia_synthesis_rev`'s
1335 K and `methanol_from_carbon_dioxide_rev`'s 1248 K. **Reported, not
guarded**, on exactly the policy those two already sit under: the cap scales both
pre-exponentials by one factor, so it moves a CLOCK and not an equilibrium, and
the process is run to 900 K.
⚠ And the crossing temperature is **not a physical statement** for these rows:
the reverse of Deacon is `2 Cl2 + 2 H2O -> 4 HCl + O2`, a FOURTH-order rate
constant in L³/(mol³ s), against a ceiling in L/(mol s). M8's unit error, and
the column is good for RANKING rather than for a verdict.

### ⚠ 7. THE SMALL THINGS

* `deacon_oxidation`'s brief said A = 1e13 puts equilibrium "on a scale of
  minutes at 700 K". **The run said ten seconds.** The number stayed and the
  claim was corrected — ten seconds is the defensible one and a converter's
  contact time is seconds.
* `synthesis_gas_chemistry`'s docstring still said "there is no catalyst species
  — the flask will make ammonia with no iron in it". **S1 made that false and
  nothing caught it until S7 read it.** Corrected in place, with the history.
* the WGS product template first came out as `O=C=[O+]` — the CO's `[O+]` was
  never neutralised. Caught by reading the product SMILES, which is the second
  time that has been the catch (see `sulfur_dioxide_oxidation`).

**Files:** `properties/thermochemistry.py` (the fragment refusal),
`reactions/synthesis.py` (5 templates, 3 bundles, 1 stale claim),
`reactions/__init__.py` (exports), `data/catalog/route_steps.psv` (6 rows
re-labelled), `data/catalog/README.md` (+110 lines),
`validation/catalog_coverage.py` (the class map, the fragment rule, the marker
bar), `validation/rate_ceiling.py` (the three new reversible templates),
`validation/gas_processes.py` (new, standing audit),
`validation/corpus_balance.py` (new, standing audit),
`tests/test_gas_processes.py` (new, 19 tests), `README.md`.

---

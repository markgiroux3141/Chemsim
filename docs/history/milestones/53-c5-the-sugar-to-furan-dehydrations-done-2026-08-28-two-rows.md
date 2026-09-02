## C5 -- The sugar-to-furan dehydrations ✔✔ **DONE 2026-08-28** *(two rows, one mechanism, and a bug that took two generations to see)*

**20 -> 21 playable (tiers 10 / 10 / 1), 42 -> 44 runnable, 57/240 -> 59/240
classes, 45 -> 46 template-ready, 37 -> 38 BOTH, species-ready UNCHANGED at 85.**
Three templates, one bundle, **one ENGINE fix**, one data row, no taxonomy split.
`validation/furans.py` (9 panels, ~2 min), `tests/test_furans.py` (20 tests,
~2 min). **§8b's top row, and the first C-series session that had to change the
engine to spend it.**

### ⚠⚠⚠ 1. THE SAME RULE THAT SPLIT C4's CLASS SAYS *DO NOT SPLIT* HERE

`dehydration-cyclisation` was §8b's top row after C4: **+1 playable, +2
runnable**, the largest runnable gain on a table C4 had flattened. Its two rows:

    hmf-route      1   fructose + H2SO4 -> 5-HMF    + water + H2SO4
    furfural-route 2   xylose   + H2SO4 -> furfural + water + H2SO4

C3 bought a class by reading its SECOND row; C4 bought one by SPLITTING it five
ways. **Both were applying *read every row before crediting the class*, and here
that rule says the opposite.** These are one mechanism — an acid-catalysed triple
dehydration of a sugar into a furan, a pentose giving furfural and a ketohexose
giving 5-HMF — and each balances exactly 1:1 on its own sugar with three waters.

⚠⚠ **SO THE CLASS STANDS AND THE CREDIT NEEDS BOTH TEMPLATES.** Grant it off the
HMF row alone and `furfural-route` goes template-ready with nothing in the engine
able to make furfural. *The check that catches a false credit and the check that
catches a lazy lump are the same check; which way it points is a property of the
rows and not of the session reading them.*

### ⚠⚠⚠ 2. THE CORPUS SPELLING C4 BOOKED AS A LOST SUBSTRATE IS LOAD-BEARING HERE -- FOR ONE ROW OF TWO

C4 measured that its hexopyranose pattern does not fire on fructose *"because the
corpus spells fructose as a FURANOSE: a five-ring sugar is a different pattern"*,
and booked it as a corpus limit. It is not a defect, and the two rows use it
differently — measured out of RDKit's own reactant-to-product atom tags rather
than read off the SMARTS:

| row | product ring atoms from the SUGAR'S OWN ring |
|---|---:|
| fructose -> 5-HMF | **5 of 5** |
| xylose -> furfural | **3 of 5** |

* **fructose** — the β-D-fructofuranose ring C2-C3-C4-C5-O **IS** 5-HMF's furan
  ring. No ring bond is formed or broken; three hydroxyls leave, C6 goes to the
  aldehyde, and aromaticity perception does the rest.
* **xylose** — the xylofuranose ring is C1-C2-C3-C4-O and furfural's is
  C2-C3-C4-C5-O. **The WRONG RING.** C5 and its hydroxyl are pulled IN, the
  sugar's own ring oxygen leaves as one of the three waters, and C1 is pushed OUT
  to become the aldehyde.

⚠ **A COEFFICIENT VECTOR CANNOT SEE THAT**: both rows are 1:1:3. It is the same
blindness `corpus_balance` has, arriving on two rows that are both RIGHT.

⚠ Neither template moves an oxygen between carbons, so C4's atom-map standard
holds on both. The rehydration below is the one that cannot meet it and says so.

### ⚠⚠⚠ 3. THE ENGINE COULD NOT FERMENT SUGAR IT HAD INVERTED ITSELF

Found two generations deep in C5's own chain and then measured on C4's.
**`ReactionTemplate.run` handed back products carrying RDKit's `noImplicit` flag,
and no template can run on such a molecule.** A product-template atom written
with an H count (`[CH3:2]`, `[OH1:8]`) comes back with its hydrogens counted as
EXPLICIT; substructure matching cannot see the difference, because the total H
count is identical, so the species is discovered, priced, charged and reported
exactly as normal — and then `RunReactants` hands the flag to the NEXT template's
products, any product atom that template did not itself spell an H count for
inherits an H it must not have, and `run` catches the valence error and returns
an **empty list**.

    the glucose sucrose inversion makes    OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O
    the same SMILES, parsed                ... identical, and equal by Molecule.__eq__

    template                     BEFORE   AFTER
    ethanolic_fermentation            0        1
    butanolic_fermentation            0        1
    acetonic_fermentation             0        1
    homolactic_fermentation           1        1

    charge SUCROSE + water   4 species,  1 reaction,  ethanol FALSE   ->  9 / 4 / TRUE
    charge GLUCOSE + water   7 species,  3 reactions, ethanol TRUE    ->  7 / 3 / TRUE

⚠⚠⚠ **C4's DOCSTRING SAYS A BREWER *"has to invert the sugar first"*, AND A
BREWER WHO DID GOT NOTHING.** The claim was right about the chemistry and false
about the engine. **It is invisible to every single-template test**, because
catching it takes one template to MAKE what another consumes, and every
fermentation test C4 wrote charges glucose directly.

⚠ The general sweep — every unimolecular template against every species any
template can make from a corpus substrate — found **8 disagreements before and
0 after**, and **every one of them was C4's chemistry**: seven a fermentation
template on sugar `glycoside_hydrolysis` had inverted, and the eighth C4's own
lactic acid failing to reach `alkene_dehydration`.

⚠⚠ **THE FOURTH ROW IS THE INSTRUCTIVE ONE.** `homolactic_fermentation` was never
broken — not because it is more careful in general, but because it happens to
spell an H count for the ONE atom that carried the flag (the anomeric hydroxyl
`glycoside_hydrolysis` writes `[OX2H1:5]`), where the other three send that atom
into a CO2 they wrote `[O:6]=[C:9]=[O:10]`. **Spelling an H count on every
product atom IS a valid fix — and it is a rule an author has to remember on every
atom of every template, which is why the fix went into the TYPE instead.**

The fix is one line: re-parse every product from its own canonical SMILES.
`Molecule`'s docstring already states the identity contract — *two Molecules are
equal iff their canonical SMILES match* — and **two molecules were satisfying it
while behaving differently**. A round trip through the SMILES this engine already
uses as identity cannot lose anything that was part of the identity.

⚠⚠ **AND REMOVING THE BUG REMOVED AN ACCIDENTAL GENERATION CAP.**
`kolbe_schmitt` feeds itself: it carboxylates a phenoxide to salicylate,
dissociation takes salicylate's PHENOL proton, and the dianion is a phenoxide the
same template carboxylates again. The old behaviour stopped that walk at
generation 2. Generation 4 wants 2-hydroxyisophthalate, which the corpus does not
price, so `tests/test_named_routes.py` DECLARES `generations=3` now — which is
what `aromatic_chemistry` already tells a reader to do for a self-feeding
template. **An accidental cap is still a cap: removing the accident means writing
the cap down**, and it costs the other five cases in that test nothing.

⚠ **THE pKa ROW WAS EXPOSED, NOT MISSED.** Salicylic acid's second dissociation
(pKa 13.4, against phenol's own 9.95 — the same ortho hydrogen bond that makes
the FIRST proton come off at 2.97 instead of benzoic acid's 4.20) was never asked
for, because nothing could reach the mono-anion with a template. *C2's rule from
the other side: a table can be short a row for years if nothing can get far
enough to ask for it.*

### ⚠⚠ 4. THE +0 ROW IS WHAT MAKES THE +1 ROW MEAN ANYTHING

`hmf-route` row 2 is `hydration-ring-opening`, priced **+0** in `PLAYABLE.md`
because the route's target is already reached at row 1 — and the corpus names it
*"the side reaction that limits yield"*. It was built anyway, and re-measuring
confirms the +0 is real: removing it moves the playable count by nothing.

**Without it a flask of fructose in acid runs to 100% HMF and reports a number no
laboratory has ever seen.** With it the HMF rises, peaks and falls, and where the
peak sits is a property of two barriers rather than of a declared stopping time.
*A row worth nothing on the scoreboard can be the row that makes the scoreboard's
number mean something.*

### ⚠⚠⚠ 5. AND ITS BARRIER IS THE LOWER ONE, WHICH PREDICTED SOMETHING NOTHING WAS AIMED AT

Formation 140 kJ/mol, destruction 110 kJ/mol, both literature bands. The
destruction is therefore the **less** temperature-sensitive step:

     T/K    peak HMF yield     at t/h
     390          39.85%      155.71
     405          46.31%       42.01
     420          52.34%       11.33
     435          58.28%        3.06
     450          63.33%        0.83

**SELECTIVITY IMPROVES WITH TEMPERATURE, AND THE BATCH GETS SHORTER.** Hot-and-
short is exactly how this process is operated. Only the LEVEL of the yield is
fitted; the DIRECTION is the part that could have come out wrong. *S11's
competing-templates finding, arriving on a CONSECUTIVE pair instead of a parallel
one.*

⚠⚠ **AND A SECOND LEVER FELL OUT THAT NOBODY ASKED FOR: AN INERT SPECTATOR.**
Glucose does nothing in this network — no template touches it — and adding
0.5 mol of it takes the peak yield from **52.4% to 61.6%**. It occupies liquid
volume, the water concentration falls, and the rehydration is second order in
water while the dehydration is zeroth. **A chemically inert species moves the
yield, through the volume.** That is the corpus row's own condition column
explaining itself — `hmf-route` step 1 reads *"420 K, DMSO or biphasic"*, and
what those solvents are FOR is taking the water away from the HMF. **This engine
has no solvent model and reproduces the direction of the trick anyway, because
water is a REACTANT in the rate law rather than a background.**

### ⚠⚠ 6. ONE NUMBER IS FITTED, AND IT CHECKS AGAINST SOMETHING IT WAS NOT FITTED TO

C4 fitted three pre-exponentials and could check none of them. C5 fits **one** —
the rehydration's `A` — because a peak yield is a RATIO of two rates, and two
barriers fix only how that ratio moves with temperature, never its value at any
one temperature. 5.0e5 L²/mol²/s puts the peak at **52.5% at 420 K** against a
reported ~50-55% for fructose in dilute aqueous acid.

⚠ **THE CHECK:** folded against the flask's own water (~52.6 mol/L) that is an
effective first-order 1.4e9 /s — about 7000× below a bare transition-state
frequency factor, an entropy of activation near **−74 J/(mol K)**. That is what
ordering TWO water molecules into a transition state costs. *A fitted constant
that lands on a physically sensible ΔS‡ is a different kind of number from one
that only reproduces its own target.*

### ⚠⚠ 7. THE TEMPLATES ARE STEREO-BLIND AND EVERY EXTRA HIT IS RIGHT

Swept over all 1583 corpus compounds:

    ketofuranose_dehydration   fructose, sorbose            -> 5-HMF    (2 hits)
    aldofuranose_dehydration   ribose, xylose, arabinose    -> furfural (3 hits)
    hmf_rehydration            5-hydroxymethylfurfural      -> LA + FA  (1 hit)

**All five substrate hits are correct chemistry and none was aimed at.** Every
pentose gives furfural in hot acid — that is what a pentosan assay IS — and
L-sorbose is a ketohexose that dehydrates like fructose. C4's `[C;H1;@,@@:n]`
device is what makes it stereo-blind, and here the generalisation it buys is the
chemistry's own.

⚠ **SUCROSE IS INERT TO BOTH** — a glycoside has no free anomeric -OH, C4's
narrowing on a different ring size — so a syrup has to be inverted first. **That
inversion is the chain §3 fixed**, and it is why `hmf-route` is tier 2.

⚠ **AND FURFURAL IS INERT TO THE REHYDRATION**, which is correct: it has no
hydroxymethyl, and it is indeed the furan that survives what destroys HMF.

### ⚠⚠ 8. THE SCOREBOARD, AND THE TIER-1 MAJORITY IS GONE

| session | granted | fed-but-unrunnable | ceiling | playable | tiers |
|---|---|---:|---:|---:|---|
| G3 | — | 21 | 37 | 12 | 8 / 3 / 1 |
| C1 | 1 route | 24 | 41 | 14 | 9 / 4 / 1 |
| C2 | 2 rows | 22 | 41 | 16 | 9 / 6 / 1 |
| C3 | 2 classes | 20 | 41 | 18 | 9 / 8 / 1 |
| C4 | 1 class | 23 | **45** | 20 | 10 / 9 / 1 |
| **C5** | **1 class** | **22** | **45** | **21** | **10 / 10 / 1** |

⚠⚠⚠ **TIER 1 IS A MINORITY OF THE PLAYABLE SET FOR THE FIRST TIME.** G3's finding
was *most playable routes are tier 1* — a bush, not a tree. C3 took it to exactly
half and asserted the equality, saying that whoever broke it would be the session
where a real tier appeared. C5 broke it: **10 of 21.** The operator in
`test_the_tech_tree_is_a_shallow_bush` has now gone `>` then `==` then `<`, and
every step of that was a session buying a route that stands on another route's
output. ⚠ **Tier 3 is STILL one route, six sessions running**, and that is the
half of G3's finding that has not moved at all.

⚠⚠ **AND C5 IS THE FIRST SESSION SINCE C2 THAT DID NOT MOVE THE CEILING.** C4
moved it 41 → 45 because four solvents on the shelf FEED four more routes. 5-HMF
and levulinic acid feed nothing — no corpus route takes either as an input.
**A route can be worth a playable point and worth nothing to the goal it is
scored against**, and which of the two a session gets is a property of the corpus
rather than of the chemistry built.

⚠⚠ **`hmf-route` STANDS ON TWO TIER-1 ROUTES AT ONCE, WHICH IS A FIRST.**
`invert-sugar` for the fructose and C1's `vitriol-distillation` for the acid that
catalyses it. Every other tier-2 route in the file needs one upstream route or
one granted reagent.

⚠ **AND THE HEADLINE TEST HAD TO BE RENAMED, BY C4's OWN RULE.**
`test_the_answer_is_twenty_playable_three_tiers_deep` carried a LEVEL in its name,
and C4 had written down that *a test that pins a level will be re-numbered by the
next session that moves it, and the claim will quietly become someone else's
arithmetic*. It is `test_the_headline_and_the_tiers_are_what_the_report_says`
now. **Two sessions running, that rule has cost a test its name — and both times
`test_the_PAIR_is_worth_more_than_the_sum_of_its_parts` survived untouched,
because it asserts differences.**

### ⚠ 9. AND A LATENT SCORING ARTEFACT SURFACED THE MOMENT A ROUTE WENT RUNNABLE

`furfural-route` step 1 is written `xylose + water -> xylose`: the corpus has no
pentosan graph, so the row uses its own product as a stand-in feedstock. **A
species on both sides of a step is exactly what `route_roles` calls a CATALYST**,
so the `with_catalysts=False` counterfactual hands the route's actual SUGAR over
for free and calls it playable.

⚠⚠ **THE HEADLINE IS IMMUNE, AND THAT IS THE POINT.** `needs()` decides by ORDER
(PLAYABLE.md's rule 2, measured wrong first in G3), and by order xylose is used
at the step that first makes it, so it is external and the route is correctly not
playable. **The artefact appears only in the one counterfactual where
`route_roles` still gets to answer** — and it was latent until C5 made
`furfural-route` runnable. *A rule that was already known to be right is what
kept a corpus wart out of the headline.*

### ⚠ 10. WHAT C5 DID NOT DO, SAID OUT LOUD

* **`furfural-route` is runnable and NOT playable**, and the blocker is xylose:
  nothing in 173 routes makes a pentose. It is +1 on the runnable count and +0 on
  playability, measured rather than assumed.
* **Furfural runs to 100% and that is an upper bound.** Real yields stop near 50%
  because furfural RESINIFIES into humins, and this project has no representation
  for an amorphous polymer. `hmf-route` got a yield-limiting row because the
  CORPUS wrote one down; `furfural-route` did not. **The difference between the
  two flasks is a property of the catalog, not of the chemistry.**
* **`aldofuranose_dehydration` is NOT in `furan_chemistry`.** Same class,
  different feedstock — a bundle carrying both would report a flask nobody runs.
* **The sugars MIX STANDARD STATES for the third session running.** The
  dehydration's dH is −14.4 (gas) against −191.3 (liquid); the rehydration, which
  has no sugar in it, differs by 9. **It costs the K and nothing else** — all
  three templates are irreversible and dG is strongly negative on either basis.
  ⚠ Do not quote a K for these reactions. C3's notice, C4's notice, and now
  printed beside the numbers it applies to.
* **The stereo-keying job C4 handed forward is still open.** 31 corpus compounds
  select a data tier by an orthographic accident. Nothing here touched it.

### ⚠⚠⚠ 11. THE SUITE FOUND NINE, AND TWO OF THE NINE WERE NOT LEVELS

C5 green-lit ~150 tests across the files most likely to be affected and the full
suite still found nine. **Five were level-pins C5 legitimately moved** — three in
`test_fermentation.py` (the §8b table it owns), one in `test_protonation.py` (the
ion count, 29 → 30, an ANION again exactly as its own docstring predicts) and one
in `test_vitriol.py` (`furfural-route`'s uncovered classes, 4 → 3). **The other
four were real, and neither of them is what a green subset would have suggested.**

#### ⚠⚠⚠ THE FLAGSHIP PREP HAD BEEN MAKING AN ESTER IN CAUSTIC SODA

`test_prep_side_products.py` failed three ways, all reading `total(ACETIC) == 0`
where it used to be positive. The cause is the fix working:

    charge, 2 h, air, saponified          BEFORE        AFTER
    acetic acid                          positive      0.000000e+00
    acetate                                 0.0        6.848146e-03
    ethyl acetate                        positive      0.000000e+00
    free hydroxide in the pot                       9.312816e-02 mol

**The pot is a SAPONIFICATION and holds 0.093 mol of free hydroxide.** A
carboxylic acid in that liquor is a carboxylATE — and until C5,
`carboxylic_acid_dissociation` could not fire on the acetic acid, because
`peroxide_over_oxidation` had MADE it and the product carried the flag. So the
acid sat there neutral in caustic soda **and then Fischer-esterified with the
ethanol.** ⚠⚠ **There is no Fischer esterification at pH 13, and the engine had
been reporting one since the prep's side-product model was written.** The cascade
itself is unchanged and correct — 6.85 mmol of acetyl at two hours, exactly as
before — it is the SPECIATION that was wrong. The tests count acid plus conjugate
base now, which is what *"the prep makes its own contaminant"* always meant.

⚠ *A two-generation bug hid a one-generation wrong answer: the dissociation is
the SECOND template to touch that species, and nothing in the project charges
acetic acid into that pot by hand.*

#### ⚠⚠⚠ AND A GREEN TEST WAS RESTING ON THE ORDER OF TWO IDENTICAL ROWS

`test_dropping_funnel.py::test_the_funnel_itself_can_be_what_is_watched` died
with `RuntimeError: Factor is exactly singular` out of BDF's `I - c*J`. C5's fix
changes the order in which `run` returns product sets, so two nitration
reactions — **same name, same reactants, same products' KIND, same A, same Ea** —
swap places in the stoichiometry matrix. Nothing else about the network moves:
species set, species ORDER, every A, every Ea, every dH, every molecule-derived
property diff to zero.

⚠⚠ **MEASURED BOTH WAYS ROUND RATHER THAN ASSUMED, WHICH IS WHAT DECIDED IT:**

    pre-C5 engine + pre-C5 order      OK,   elapsed 29.985 s
    post-C5 engine + post-C5 order    RuntimeError: Factor is exactly singular
    post-C5 engine + PRE-C5 order     OK,   elapsed 29.985 s
    pre-C5 engine + POST-C5 order     RuntimeError: Factor is exactly singular

**The ordering is the whole cause and neither engine is.** ⚠ The first three
attempts at that experiment were no-ops, because `World` imports `build_network`
into its own module namespace and the monkeypatch was going onto
`chemsim.network.builder`. *An experiment that returns the answer you expected is
the one to check hardest — the "order is not the cause" reading survived two
rounds of that before the patch was pointed at the right module.*

⚠⚠ **THE SCENARIO IS WHAT IS FRAGILE, AND IT IS FRAGILE FOR A DOCUMENTED REASON.**
`aromatic_nitration` FEEDS ITSELF, and the funnel scenario let it run to
`max_species=60` — 15 species, all the way to HEXAnitrobenzene, twelve of which
cannot form at 280 K in the seconds the test runs and sit at structural zero.
Capped, it is robust: **elapsed is 29.985 s at every cap from 4 to 14 and the run
only fails at 15.** The answer not moving across ten caps is what says the cap is
not tuning. ⚠ `aromatic_chemistry`'s docstring has said *"CAP THE EXPANSION"* for
a self-feeding template since M5; this is the second place in one session where
removing the accidental cap meant writing a real one down, the other being the
Kolbe cascade in §3.

⚠ **AND THE SAME TEST HAD A SECOND, SMALLER VERSION OF THE SAME DISEASE.** With
the network capped it then failed on `assert funnel.total(NITRIC) < 1.0e-4`,
reading **1.0000000000000826e-04**. `consumed` is a ROOT, and a root is zero to
solver precision; a strict `<` asserts which SIDE of a root the solver stopped
on, which nothing guarantees. It is `pytest.approx(1.0e-4, rel=1e-9)` now.

⚠⚠⚠ **THE FRAGILITY ITSELF IS NOT FIXED AND IS HANDED FORWARD.** What C5 fixed is
a test that was passing for the wrong reason. **A 15-species rig network with
twelve structurally-zero columns can factor exactly singular, and whether it does
depends on a row permutation that changes nothing physical.** That is the rig
integrator's, it is now reproducible in four lines, and it belongs to a numerics
session rather than to a content one.

### ⚠ 12. THE SUITE, AND THE CLOCK

**The clock:** C5 RAN THE SUITE TWICE IN ONE SESSION, AND THAT IS THE BEST NOISE MEASUREMENT THIS PROJECT HAS

**1179 passed / 0 failed in 28:59**, run alone. C5 owed a second run after fixing
the nine the first one found, so for once there are TWO full runs of the same box
in the same session, 18 minutes apart:

                        run 1     run 2   change     touched between?
    total / s          1660.8    1739.0    +4.7%
    tests                1179      1179       --
    the ONE RIG test    160.8     158.5    -1.4%     no
    catalysis            72.2      72.4    +0.2%     no
    burner @1e-8         50.8      85.0   **+67.3%** NO
    rig azeotrope        22.2      34.3   **+54.5%** NO

⚠⚠⚠ **TWO ROWS MOVED MORE THAN HALF THEIR OWN VALUE WITH NOTHING TOUCHED, IN THE
SAME SESSION, WHILE THE TOTAL MOVED 4.7%.** Neither test nor anything either one
depends on was edited between the runs. **That settles what four sessions of
cross-session comparison could only bound: a single `--durations` row is not an
instrument, and the per-test total is.** C3 measured the between-run spread at
~20% on every big row; C5 measures it at **67% on one row and 0.2% on another in
the same pair of runs**, which is a stronger and less flattering answer.

Against the session series:

                        G6        C2        C3        C4        C5     C4->C5
    total / s         1383.0    1795.0    1494.6    1569.5    1739.0    +10.8%
    tests               1045      1097      1128      1159      1179     +1.7%
    the ONE RIG test   176.9     199.3     163.2     156.2     158.5     +1.5%
    catalysis           75.1      91.5      73.5      81.0      72.4    -10.6%
    burner @1e-8        52.8      64.8      51.0      52.9      85.0    +60.7%
    SECONDS PER TEST  1.3234    1.6363    1.3250    1.3542    1.4750     +8.9%

⚠⚠ **PER TEST, C5 IS 1.4750 s AGAINST C4's 1.3542 -- AND MOST OF THAT IS WORK
THAT WAS ADDED RATHER THAN SLOWED.** `tests/test_furans.py` is ~125 s of new
integration; take it out and C5 is **1.3927 s per test, +2.8% on C4**, back
inside the band G6/C3/C4 sit in. ⚠ The rest is the burner row, and the two-run
control above says what that is worth.

⚠ **THE S12->S13 EIGHT MINUTES IS STILL UNBISECTED**, and it is now measured
against a noise floor that is much wider on a single row than anyone had
allowed for.

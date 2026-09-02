## C4 -- The ABE fermentation ✔✔ **DONE 2026-08-28** *(the class M5 refused was an outcome label, and its lump was a formatting artefact)*

**18 -> 20 playable, 41 -> 42 runnable, 55/236 -> 57/240 classes, 44 -> 45
template-ready, 36 -> 37 BOTH, species-ready UNCHANGED at 85.** Four templates,
one bundle, a five-way TAXONOMY SPLIT, no data rows and no engine code.
`validation/fermentation.py` (8 panels, ~30 s), `tests/test_fermentation.py`
(31 tests). **§8b's only +2 row, taken — and there is no +2 row left.**

### ⚠⚠⚠ 1. THE CLASS WAS REFUSED IN M5, AND THE REFUSAL WAS ABOUT THE LABEL

M5 refused `fermentation` as *"a metabolic **network**, not a transformation"*.
`PLAYABLE.md` §8b priced it as **the biggest single class left, +2 playable**, and
NEXT_PROMPT recorded C3's own measurement of the row it is sold on:

    abe-fermentation 1, as written  C6H12O6 -> C10H24O5              NO
    ... balances only at            5 C6H12O6 -> 2 acetone + 2 butanol
                                    + 2 ethanol + 12 CO2 + 8 H2

with the verdict *"five glucoses in and six carbon skeletons out is not a graph
rewrite"*. **Every word of that is true and none of it is about the mechanism.**

⚠⚠⚠ **THE LUMP WAS A FORMATTING ARTEFACT.** Clostridial solventogenesis is three
independent branches off one pyruvate node, and each balances **exactly on ONE
glucose**:

    glucose        -> 2 ethanol + 2 CO2            C6H12O6 both sides, EXACT
    glucose        -> 1-butanol + 2 CO2 + H2O      C6H12O6 both sides, EXACT
    glucose + H2O  -> acetone + 3 CO2 + 4 H2       C6H14O7 both sides, EXACT

**Nothing consumes five sugars. It was three reactions written on one line, and
the 5:2:2:2:12:8 vector was the arithmetic of that line rather than of any
chemistry.** ⚠ So `corpus_balance`'s weak test passed the row for the same reason
it passes `vanillin-lignin`, and the two rows need **opposite** answers: the
lignin row is short a PRODUCT and must be left wrong; this one was short a LINE
BREAK and could just be split. *A coefficient vector cannot tell those apart.*

⚠⚠⚠ **FOUR SESSIONS RUNNING HAVE FOUND ONE OF THIS SHAPE.** C1: a route blocked
on a price for a species **not in its chemistry**. C2: a route blocked on a price
**in a different table**. C3: a **class refused on the evidence of one of its
rows**. C4: a **class refused on the evidence of its row's FORMATTING**. *Read
the mechanism, not the line.*

### ⚠⚠⚠ 2. AND THE CLASS HAD TO BE SPLIT FIVE WAYS, BECAUSE THE +2 WAS OTHERWISE A FALSE CREDIT

Five catalog rows carried `fermentation` and they are five mechanisms:

| row | mechanism | C4 |
|---|---|---|
| `abe-fermentation` 1 | anaerobic clostridial **solventogenesis** | **BUILT** |
| `lactic-acid-pla` 1 | anaerobic **homolactic** glycolysis, no gas at all | **BUILT** |
| `citric-acid-fermentation` 1 | **aerobic overflow** of a blocked TCA cycle | gap |
| `msg-route` 1 | aerobic overflow plus **reductive amination** | gap |
| `penicillin-route` 1 | **secondary-metabolite** biosynthesis on a fed precursor | gap |

**A template written off `abe-fermentation` cannot make citric acid, glutamic
acid or penicillin G out of a sugar.** Crediting the old five-row class off it
would have template-readied four routes `build_network` cannot run — G4's *only
RUNNING it said so*, **arriving before the run for once, because the rows were
read first.** So `route_steps.psv` names five classes, on S7's `combustion`
precedent and M5's own `catalytic-hydrogenation` one.

⚠⚠ **THE HEADLINE COST IS +4 ON THE DENOMINATOR** — 236 classes to 240 — against
+2 covered. **S7's rule again: a split that lowers the headline is a split
working.** ⚠ And the split is what makes the three gaps *costable*: each now has
a yes/no answer instead of a fifth of one.

### ⚠⚠⚠ 3. M10's CHEAP VERSION IS REFUTED, AND IT FAILS WORSE THAN ITS OWN DOCSTRINGS SAY

§M10 scopes the Michaelis-Menten plateau as *"a declared order of ZERO in the
substrate IS the saturated limit ... needs no kernel change"*, and a fermentation
substrate is the one slot it would sit in. **It needs one.** There is no
availability gate outside the solid block (`_avail`), so the rate law cannot know
the substrate is gone — and two docstrings in this project say the reactant *"is
driven negative"*. Run to 1500 h at order zero (`validation/fermentation.py`
panel 5):

    orders               t/h      glucose        EtOH    EtOH/max
    mass action (ours)  1500     0.015087     0.96983       0.970
    (0.0,) -- M10's      200     0.382801     0.23440       0.234
    (0.0,) -- M10's     1100     0.000000     1.27577       1.276  IMPOSSIBLE
    (0.0,) -- M10's     1500     0.000000     1.79388       1.794  IMPOSSIBLE
    (0.0,) -- M10's     3000     REFUSED -- RuntimeError, species reached -1.74 mol

⚠⚠⚠ **THE SUBSTRATE IS CLAMPED AT ZERO IN THE REPORTED STATE WHILE THE PRODUCTS
GROW PAST THE STOICHIOMETRIC CEILING, AND THE RUN REPORTS SUCCESS FOR ~1900
SIMULATED HOURS.** 1.79 mol of ethanol out of 0.5 mol of glucose is 3.6x what
that sugar can give. **`state()` does not go negative — it hides the negative,
and the products are where the violation shows.**

⚠⚠ **THE GUARD IS LOAD-BEARING AND ITS LABEL IS NOT.** `conservation_report()`
sees every mole:

    non-negative projection created 1 species' worth of round-off it could not
    settle against a positive holding: <glucose> 3.97e-01 mol

**Four tenths of a mole, called "round-off".** The wording is calibrated for the
case the method was written for, and it is the only witness a caller has. *Same
shape as "energy_terms lies unless given the run's own boundary state" and as
"state().total() is the right number for a yield and the wrong one for an
equilibrium": the check exists, is correct, and its own prose mis-sizes what it
found.* ⚠ **M10 stays OPEN and its cheap door is measured shut**: a saturating
form needs the denominator, or the kernel needs the gate the solid block has.

### ⚠⚠ 4. WHAT IS FITTED, WHAT IS NOT, AND THE ONE NUMBER THAT CHECKS THE MODEL

Reference flask: 0.5 mol glucose in 10 mol water — ~0.19 L of a 2.6 M mash — in a
sealed 2 L vessel at **310 K**, which is blood heat.

     t/h   glucose     EtOH     BuOH  acetone      CO2       H2   conv%   A:B:E
    12.0   0.34598  0.02335  0.08755  0.05480   0.3628   0.2192  30.80  2.35:3.75:1
    48.0   0.11223  0.05830  0.21863  0.13999   0.9155   0.5600  77.55  2.40:3.75:1
    96.0   0.02459  0.07125  0.26719  0.17260   1.1234   0.6904  95.08  2.42:3.75:1

**FITTED:** the batch time (77.6% in 48 h is an ABE batch) and the **solvent
slate** — the classical 3:6:1 by MASS is 2.38:3.73:1 by mole, and three
pre-exponentials were set to it.

⚠⚠ **AND THAT FIT IS DECLARED RATHER THAN HIDDEN BEHIND AN ALPHA, WHICH IS THE
SESSION'S DESIGN DECISION.** Evans-Polanyi over three branches that differ by
**220 kJ/mol** in dH would predict a slate of nothing but butanol. A real slate
is set by the organism's regulation and its pH. **Selectivity between two
CHEMICAL templates is derivable in this project (S11); selectivity between two
METABOLIC branches is not**, and saying so is worth more than a plausible alpha.

⚠⚠⚠ **NOT FITTED, AND IT IS THE ONE NUMBER THAT CHECKS THE MODEL: THE
FERMENTATION GAS COMES OUT AT CO2 61.94% / H2 38.06% AGAINST A REPORTED ~60/40.**
H2 comes **only** from the acetonic branch, so the gas ratio is a consequence of
the solvent slate and the three stoichiometries and nothing was aimed at it.

⚠ **AND TWO INVARIANTS HOLD TO SOLVER PRECISION AT EVERY POINT** — §1's balance
showing up as a property of the trajectory: **H2/acetone is exactly 4.000000000000**,
and CO2 is `3A + 2B + E` to nine figures.

### ⚠⚠ 5. THE ORGANISM IS NOT A SPECIES, AND THAT IS THE SESSION'S HONEST HOLE

Every other gate in this project is a mechanism you can charge: an acid, a base,
a lattice, a voltage, a pinch of NO2. **A fermentation's gate is ALIVE.** The
corpus has no graph for a Clostridium and `_maybe_catalyse` needs one, so the
four templates take a `catalyst` parameter, default it to None, and **a flask of
sterile sugar water ferments.** ⚠ The hole is under all eight of M10's biological
routes, not this one, and it is why `Ea` is an APPARENT barrier over twenty
enzymatic steps. *An inventory item for a culture is a GAME_DESIGN answer, not an
engine one.*

⚠ **AND EVERY YIELD IS AN UPPER BOUND, FOR C3's REASON WITH A NEW MECHANISM.** A
real ABE batch stalls near 20 g/L of butanol because butanol dissolves the
organism that makes it, and **nothing here can express a product poisoning its
own catalyst when the catalyst is not in the flask.**

⚠ A sealed fermenter reaches **24.7 bar** at 96 h on its own CO2 and H2, and
nothing was told to do that. Vented (`k_vent` 1e-3) it sits at 1.01 bar and the
**conversion is unchanged to 1%** — no branch is reversible, so the pressure
cannot push back. *A hazard, not a ceiling*, unlike the vanillin digester where
30 bar of steam is what makes the route go.

### ⚠⚠ 6. WHAT THE SMARTS REFUSES, AND BOTH REFUSALS ARE THE POINT

The four templates share one hexopyranose pattern, narrow in one place: **the
anomeric carbon must carry an -OH**.

* **sucrose is inert to all four.** A glycoside does not match, so a brewer has to
  invert the sugar first — which is `ethanol-fermentation` step 1
  (`glycoside-hydrolysis`) being load-bearing rather than decorative.
* **fructose is inert too, and that one is a corpus limit.** Real clostridia eat
  it; the corpus spells it a **FURANOSE**, and a five-ring sugar is a different
  pattern. **S7's pyranose/furanose finding, costing a SUBSTRATE this time rather
  than an equilibrium constant.**
* **mannose IS eaten**, which is correct: same constitution, and the pattern
  queries no stereochemistry.

⚠ Every branch prints M5's **MIXES STANDARD STATES** notice, because glucose's
vapour pressure at 298 K is below the standard-state floor (its Tb is an
unanchored 825.6 K estimate on a sugar that decomposes) while its products all
shift. The two conventions differ by **64-219 kJ/mol** in dH and **flip the sign
of dS** (+466.41 -> -32.26 J/K on the ethanolic branch). ⚠⚠ **What that costs is
the EQUILIBRIUM CONSTANT and nothing else**: dG is between -121 and -353 kJ/mol
on *either* basis, so nothing is reversible under any reading. **Do not quote a K
for a fermentation in this project.** C3's notice, arriving on a SUBSTRATE.

### ⚠⚠⚠ 7. AND A STEREOCENTRE TURNED UP A KEYING BUG IN THE PROVIDER, WHICH IS THE FINDING NOTHING WAS LOOKING FOR

`homolactic_fermentation` makes a **new stereocentre** out of a sugar carbon.
RDKit inherits an unspecified chirality, so the plain pattern emits **one
L-lactic acid and one D-** from the same glucose — two species where the corpus
has one. The fix is RDKit's own rule (chirality specified in the reactant
template and absent from the product template is REMOVED), so the pattern spells
its four centres `[C;H1;@,@@:n]` and the product is geometry-free. **That is C3's
isoeugenol decision reached through a stereocentre instead of a double bond.**

⚠⚠⚠ **AND MEASURING IT FOUND SOMETHING GENERAL: THE TWO HALVES OF A ThermoData
ARE KEYED THE OPPOSITE WAY ROUND WITH RESPECT TO STEREOCHEMISTRY.**

    corpus rows whose SMILES carries a stereo marker     146
    ... which PRICE OFF A DIFFERENT SOURCE when flat       31
          the PHYSICAL half is what moved                  30
          the FORMATION half is what moved                  2
          the STEREO spelling prices better                29
          the FLAT spelling prices better                   2

* **the PHYSICAL tables carry the chiral spelling.** Sorbitol chiral reaches a
  measured Tb (YAWS, 704.0 K); flattened it falls to Joback at 888.2 K, **184 K
  away**. 29 rows are that shape — limonene, the pinenes, menthol, borneol,
  linalool, camphor, carvone, xylitol, lindane.
* **the FORMATION table carries the FLAT spelling.** Lactic acid flat reaches an
  **experimental** formation record; the corpus's chiral spelling misses it and
  falls to **Benson**, with the Tb 107 K apart.

⚠⚠⚠ **SO FOR 31 COMPOUNDS THE DATA TIER IS SELECTED BY AN ORTHOGRAPHIC
ACCIDENT** — and a spelling carries no thermochemical information at all, because
no estimator here tells one enantiomer from another (S7, re-measured).
⚠ **NOT FIXED, deliberately**: the fix is a stereo-insensitive **FALLBACK** in
the lookup (S6's rule — a fallback, never an override), and it touches the
provider every number in this project comes out of. **Recorded with a size, which
is what makes it costable.** `validation/fermentation.py` panel 8;
`tests/test_fermentation.py` pins the 146.

### ⚠⚠⚠ 8. THE WORK ORDER GREW, THE CEILING MOVED FOR THE FIRST TIME SINCE C1, AND THE CHEAP END IS OVER

| session | granted | FED_BUT_UNRUNNABLE | ceiling | playable |
|---|---|---:|---:|---:|
| G3 | — | 21 | 37 | 12 |
| C1 | 1 route | **24** | **41** | 14 |
| C2 | 2 rows | 22 | 41 | 16 |
| C3 | 2 classes | 20 | 41 | 18 |
| **C4** | **1 class** | **23** | **45** | **20** |

⚠⚠⚠ **THE CEILING IS NOT A CONSTANT, AND TWO SESSIONS OF IT SITTING STILL WERE A
PROPERTY OF WHAT THEY BUILT.** A fermentation puts acetone, ethanol, butanol and
— through `acetic-fermentation` — acetic acid on the shelf, which FEEDS four
routes that were not fed before: `acetic-anhydride-ketene`, `chloral-route`,
`mercury-fulminate-route`, `white-lead-route`. **The goal a session is measured
against moves with the session.**

⚠⚠ **AND §8b HAS NO +2 ROW LEFT.** C4 took the only one. What remains is six
classes tied at **+1** (`dehydration-cyclisation`, `biological-transformation`,
`direct-combination`, `molten-salt-electrolysis`, `oxidative-complexation`,
`pyrolysis`) and 23 at **+0**, ten of which no template can buy at any price.
**From here every row buys one route or none.**

⚠ **AND `ethylene` WAS RE-PRICED BY A SESSION THAT NEVER TOUCHED IT**: joint-
biggest single species grant at **+2** in §7 before C4, **+1** after. `aluminium`
is now the sole +2. *A content item re-prices a lever it never went near — re-run
`tools/build_playable.py` after every one.*

⚠⚠ **THE SECOND ROUTE IS BOUGHT BY A BRANCH THAT IS NOT THE TARGET, AND IT MOVED
A RULE'S EVIDENCE.** `abe-fermentation`'s catalog target is propanone; what
unblocks `acetic-fermentation` is the **ethanol**, the minority branch at a
seventh of the butanol. So it is a route bought by a BYPRODUCT, and the
target-only shortfall in `test_playable.py` **moved 4 -> 5 for the first time in
five sessions** — the same mechanism as the zinc retort's carbon monoxide.
⚠ *Which is the opposite of the fouling rule one test above it, whose only
evidence C1 dissolved and which is kept on a measured zero. A rule kept on a zero
difference and a rule kept on a growing one are different bets, and both are
printed.*

### ⚠ 9. WHAT C4 DID NOT DO, SAID OUT LOUD

* **The three aerobic rows are not built**, and two of them do not balance on one
  substrate either: `citric-acid-fermentation` reads sucrose and balances at
  `sucrose + 3 O2 -> 2 citric + 3 H2O`, and `msg-route` needs
  `2 glucose + 2 NH3 + 3 O2 -> 2 glutamate + 2 CO2 + 6 H2O` because one hexose
  wants one-and-a-half O2. **Both are honest lumps** -- the citric row at 1:1 in
  its own sugar, the glutamate row only at a twofold multiple -- which is a
  smaller sin than the one this session undid — but neither is fed, so neither
  buys a playable route.
* **`homolactic_fermentation` buys +0 playability.** `lactic-acid-pla` needs a
  polymerisation as well. It was built for the class and for §7's stereo finding,
  and it is measured at +0 rather than assumed at +1.
* **It is NOT in `fermentation_chemistry`.** A clostridial flask does not make
  lactate in quantity, and a bundle carrying it beside the ABE three would report
  a slate no organism produces.
* **The solvent slate drifts, and it is the water slot.** 2.31:3.75:1 at the
  first step and 2.42:3.75:1 at 96 h, because the acetonic branch consumes a
  water and has it in its rate law while the other two do not (S11's rule: every
  slot a template consumes keeps order 1). **Measured, stated, not corrected** —
  the alternative is order zero in water and §3 is what that does.
* **`tools/build_playable.py`'s §8b table was lifted to module level** as
  `CLASS_WORTH`, so a test can assert it. C3 generated it inside the writer, and
  *a generated table nothing asserts is a table that rots* — `ROUTE_INDEX.md`
  went three milestones that way.
* **The ethanol here is not `ethanol-fermentation`.** That route spells its four
  steps out as `glycolysis`, `decarboxylation` and `biological-reduction` and is
  a finer job with three uncovered classes. **The corpus asks for the LUMP by
  labelling five rows `fermentation` and those four by mechanism**, and reading
  that distinction is what told C4 a lump was the honest template here.

### ⚠ 10. THE SUITE, AND THE CLOCK

**1159 passed / 0 failed in 26:09**, run alone.

                        G6        C2        C3        C4     C3->C4
    total / s         1383.0    1795.0    1494.6    1569.5     +5.0%
    tests               1045      1097      1128      1159     +2.7%
    the ONE RIG test   176.9     199.3     163.2     156.2     -4.3%
    catalysis           75.1      91.5      73.5      81.0    +10.2%
    burner @1e-8        52.8      64.8      51.0      52.9     +3.7%
    SECONDS PER TEST  1.3234    1.6363    1.3250    1.3542     +2.2%

⚠⚠⚠ **C3's RE-PRICING HOLDS.** Per test, G6 / C3 / C4 are within **2.4%** of each other
and C2 sat **24% above all three** — so C2's *"+30% that nothing explains"* was the
machine, and the ~8%/~1% floor recorded before it came from two quiet runs.
⚠⚠ **AND INDIVIDUAL BIG ROWS STILL MOVE 4-10% WITH NO CAUSE** — catalysis +10.2% here
while the rig test went **down** 4.3% in the same run. *One row's change is not a signal;* 
the per-test total is, and the `--durations` list is a per-row diff rather than an alarm.
⚠ The S12->S13 eight minutes is still unbisected.

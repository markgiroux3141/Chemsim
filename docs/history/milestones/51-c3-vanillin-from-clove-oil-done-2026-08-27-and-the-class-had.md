## C3 -- Vanillin from clove oil ✔✔ **DONE 2026-08-27** *(and the class had been refused on the evidence of one of its two rows)*

**16 -> 18 playable, 39 -> 41 runnable, 53/236 -> 55/236 classes, 42 -> 44
template-ready, 34 -> 36 BOTH, species-ready UNCHANGED at 85.** Two templates,
two classes, no data rows and no engine code. `validation/vanillin.py`
(9 panels, ~2 min), `tests/test_vanillin.py` (31 tests).

### ⚠⚠⚠ 1. THE CLASS WAS REFUSED IN S11, AND THE REFUSAL WAS ABOUT A ROW

S11 went to build `oxidative-cleavage`, read `vanillin-lignin` step 1, found that
a C10 monolignol cannot make one C8 vanillin and a water, and **refused the
class** — on the ground that naming the missing C2 fragment would be inventing
chemistry inside the corpus. That refusal is recorded in §S11 §12 and printed by
`validation/corpus_balance.py`'s last panel, and it was **right about the row.**

The class has two rows. Measured, before anything was written:

    isoeugenol + O2 -> vanillin + acetaldehyde      C10H12O4 both sides, EXACT
    coniferyl  + O2 -> vanillin + glycolaldehyde    C10H12O5 both sides, EXACT
    coniferyl  + O2 -> vanillin + water             C10H12O5 -> C8H10O4    NO

**`vanillin-eugenol` step 2 balances 1:1 and names its C2 fragment.** So the
template is written off that row — and applied to coniferyl alcohol it produces
the fragment the lignin row omits, which is **`glycolaldehyde`, a compound
`data/catalog/compounds/07-carbonyls.psv` has carried all along.** *The mechanism
supplies the fragment and the corpus supplies its name; nothing is invented.*

⚠⚠⚠ **THREE SESSIONS RUNNING HAVE FOUND ONE OF THIS SHAPE.** C1: a route blocked
on a price for a species **not in its chemistry**. C2: a route blocked on a price
**in a different table**. C3: a **class refused on the evidence of one of its
rows.** *Read every row of a class before refusing the class* — and the cost of
not doing so was two playable routes for two SMARTS strings and no new data.

⚠ **AND THE CORPUS ROW WAS LEFT WRONG ON PURPOSE**, which is the half of S11's
reason that stands. On coniferyl alcohol the mechanism is unambiguous. The
catalog row is about alkaline **lignin liquor**, where the C2 fragment is a
mixture depending on which monolignol reacted, so writing one name into it would
over-commit the corpus in exactly the way S11 declined to.

### ⚠⚠ 2. AND THE ROW S11 REFUSED IS NOW INSIDE THE HEADLINE

`vanillin-lignin` was outside the BOTH column when S11 wrote its panel. C3
covered its only class, so it is inside it now: **`corpus_balance`'s own standing
example of a row that PASSES the balance test and is not the reaction it is
written as is counted in the number the project quotes.** The one row that audit
FLAGS inside BOTH is `perkin-route`; the row that is actually wrong is the one it
cannot see. Panel updated rather than remembered.

### ⚠⚠⚠ 3. THE SESSION'S SHARPEST FINDING IS NUMERICAL: AN EQUILIBRIUM IS EXACT ON THE LIQUID AND NOT ON THE INVENTORY

C3's first flask read an isoeugenol:eugenol ratio of **15362** where `kf/kb` is
**2677.83**, and that 5.7x was nearly written into a template comment as
chemistry. It is the **HEADSPACE**:

    liquor / L    t / s    TOTAL ratio   LIQUID ratio   eug in gas   iso in gas
         0.082   3.6e+05      10993.93        2677.83       60.14%       22.27%
         0.730   3.6e+05       2866.67        2677.83       10.25%        2.12%

**The liquid ratio is `kf/kb` to the last digit**; detailed balance is exact and
was never in question. The allyl isomer is ~5x the more volatile, so a share of
the eugenol sits where no rate law can reach it — and the smaller the liquor, the
bigger the lie. ⚠⚠ **`state().total()` is the right number for a YIELD and the
wrong one for an EQUILIBRIUM.** A rate law is written on one phase; read the
equilibrium on that phase or not at all. Same shape as *"energy_terms lies unless
given the run's own boundary state"*.

### ⚠⚠ 4. §8 RANKS ROUTES AND A SESSION BUILDS TEMPLATES — SO `PLAYABLE.md` GREW A §8b

The work order's `worth` column grants a **route**. A C-series session grants a
**class**. Measured, they disagree at the top of the table:

| §8 row | its worth | grant its CLASS instead |
|---|---:|---|
| `hall-heroult` | **+3** — the top row | **still not runnable**: cryolite is refused a price too. The class lands +1, on `downs-cell` |
| `blast-furnace` | **+2** | **+0 runnable, +0 playable**: three refused species |
| `abe-fermentation` | **+2** | +3 runnable, +2 playable — the only one of the three a template can buy |

**A row's worth assumes every OTHER blocker away, and a template only removes one
of them.** 9 of the 20 rows cannot be bought by templates at all, and only 7 of
the 23 missing classes are worth a single point. `tools/build_playable.py` now
generates both tables.

⚠⚠⚠ **AND THE PAIR C3 BUILT IS SUPER-ADDITIVE, WHICH THE SESSION'S OWN PROBE
HID.** `alkene-isomerisation` alone is worth **+0** and `oxidative-cleavage`
alone **+1**; together they are **+2**, because `vanillin-eugenol` needs both
while `vanillin-lignin` needs only the second. C3's scouting probe printed its
pair table `[:12]` and the row fell off the bottom, so the session went in
expecting +1 and delivered +2. *A probe that truncates its own output can hide
the row it was written to find.*

### ⚠⚠⚠ 5. AND §8b's DETECTOR FOUND A LIVE FALSE CREDIT — THEN HAD ONE OF ITS OWN

`route_reachable` blocks a route whose **reactant** has no molecular graph, and
does **not** look at one the route MAKES. So:

* **`oxidative-complexation` is scored +1 on `iron-gall-ink`**, whose product
  `iron-gallate-marker` the corpus deliberately does not spell. **Build it and
  the route goes template-ready and `build_network` has no graph to make its
  product from.** The trigger is written into `data/catalog/README.md` in C1's
  and C2's landmine form.
* the same shape sits at **+0** on `castner-kellner` / `sodium-amalgam-marker`.
* ⚠ **and the detector's first version blamed `pyrolysis`/`coal-gas` too**,
  where the marker is on the LEFT and the route was already dead. **A
  false-credit detector needs the same does-it-actually-run check as everything
  it audits.**

### ⚠⚠ 6. THE FLASK: WHAT RUNS, AND UNDER WHAT

An **autoclave**, and that is not decoration: 0.73 L of alkaline liquor in a 2 L
vessel at 470 K sits under ~30 bar of its own steam, which is what an alkaline
oxidation digester is.

    T / K   t / h   P / bar   vanillin   yield
      400     4.0     15.67   0.000432    0.43%
      440     4.0     21.73   0.026878   26.88%
      470     4.0     29.29   0.093150   93.15%
      490     4.0     38.19   0.099985   99.98%

⚠ **The acetaldehyde is 1:1 with the vanillin at every row** — §1's balance
showing up as an invariant of the run rather than as a claim about the corpus.
⚠ **The isomerisation is rate-determining** (94.65% in 4 h alone, against the
cleavage's 97% in 1 h), so the intermediate never accumulates, which is the real
preparation's shape. ⚠⚠ **There is no over-oxidation channel**, so every yield
above is an UPPER BOUND against a real 60-80%; what is calibrated is the
isomerisation.

⚠⚠ **AND THE BASE IS THE GATE, IN A PLACE NEITHER TEMPLATE NAMES.** Zero
hydroxide gives **exactly zero** vanillin. `oxidative_cleavage` declares no
catalyst and would cleave any isoeugenol in the flask; there is none, because the
step that MAKES isoeugenol is the base-catalysed one. *A two-template route is
gated by whichever step comes first, and neither template says so on its own.*

⚠ **Both routes land in tier 2 and NOT on sulfuric acid.** Eugenol (clove oil)
and coniferyl alcohol (wood lignin) are both on the natural list; what has to be
made is the **caustic soda**. So rule 3 — *a catalyst is a feedstock* — is what
puts vanillin one hop up, and C3 is the first session to move the tree away from
being mostly tier-1: **9 of 18 is exactly half**, where G3's assertion was a
strict majority. The bush is still 3 tiers deep and tier 3 is still one route.

### ⚠⚠ 7. TWO CLAIMS C3 WROTE AND THEN MEASURED FALSE

* **The bundle does NOT need `dissociation_templates()` — it must not be given
  them.** That line was copied from `wacker_chemistry` and is the opposite of the
  truth: eugenol IS a phenol, so `phenol_dissociation` fires on it and
  `build_network` refuses the whole network for want of an **eugenolate pKa**.
  G5's rule reaching a new substrate — *an open-ended rewrite over a curated
  table will find the edge of the table*, met on an amine there and a phenol
  here. **The refusal is KEPT**: this route needs no phenolate, and G5 measured
  what curating pKa values for an unused template buys.
* **Ea 110 kJ/mol was 8x too fast, and the arithmetic that chose it assumed a
  ONE-LITRE liquid.** The flask's liquor is 0.73 L, so its hydroxide is
  correspondingly more concentrated. Corrected to **115**, calibrated against the
  flask. *An apparent barrier calibrated against a rate has to be calibrated
  against the rate the FLASK computes, not the one the envelope does.*

### ⚠ 8. AND THE PRE-BUILD ARITHMETIC WAS DONE ON THE WRONG STANDARD STATE

|  | ideal gas | | pure liquid | |
|---|---:|---:|---:|---:|
| | dH | ln K 470 | dH | ln K 470 |
| eugenol -> isoeugenol | −21.80 | +8.04 | **−56.56** | **+7.89** |
| isoeugenol + O2 -> vanillin + MeCHO | −325.58 | +85.71 | **−320.92** | **+94.37** |

Both templates are `phase="liquid"`, so the second pair is what the flask uses.
⚠⚠ **The two ln K values for the isomerisation agree to 2% while their dH values
differ by 35 kJ/mol and the sign of dS flips** (+20.45 against −54.72 J/K).
**That agreement is a coincidence, not a licence** — two errors cancelling at one
temperature. S12's rule; the template comment was corrected against the audit
rather than the other way round.

### ⚠ 9. WHAT C3 DID NOT DO, SAID OUT LOUD

* **The lignin row runs and its ln K may not be read.** Coniferyl alcohol has no
  vapour-pressure curve, so `build_network` prints M5's MIXES STANDARD STATES
  notice on it. The reaction is irreversible so no rate depends on the number.
  ⚠ **Which is a second, independent reason the eugenol row was the right one to
  build from: all four of its species carry a curve. S11 picked the row that is
  worse in both ways.**
* **The product's double-bond geometry is not declared.** cis, trans and
  geometry-free isoeugenol price at Hf −216.705 and Gf −49.315, identical to
  three decimals — S7's `oleic -> elaidic` finding re-measured. So the template's
  product is a **different species string** from the corpus's trans isoeugenol
  and thermochemically the same molecule. ⚠ **It makes no spurious cycle, because
  discovery is FORWARD-ONLY** (M5): charge the corpus's trans isomer and the
  isomerisation is not in the network at all. *A rule that has cost this project
  a template twice does useful work here.*
* **No over-oxidation, no vanillic acid, no polymerisation.** The three things
  that cap a real vanillin yield. `peroxide_over_oxidation` exists and is
  deliberately NOT in this bundle, because a bundle carrying it would also
  oxidise the acetaldehyde.
* **`tolerance_audit.py` is NOT owed**: no RHS edit, no data-table edit, and
  nothing outside the new bundle can reach either template.

### ⚠⚠⚠ 10. THE SUITE IS GREEN, AND ITS CLOCK CLOSED ONE OF C2's OPEN ITEMS

**1128 passed / 0 failed in 24:54, run alone.** C3 ran **31 more tests than C2 in
300 fewer seconds**:

                        G6        C2        C3     C2->C3    G6->C3
    total / s         1383.0    1795.0    1494.6    -16.7%     +8.1%
    tests               1045      1097      1128     +2.8%     +7.9%
    the ONE RIG test   176.9     199.3     163.2    -18.1%     -7.7%
    catalysis           75.1      91.5      73.5    -19.7%     -2.2%
    burner @1e-8        52.8      64.8      51.0    -21.3%     -3.4%
    SECONDS PER TEST  1.3234    1.6363    1.3250   -19.0%    +0.12%

**Per test, C3 is within 0.12% of G6 and C2 sat 24% above both.** Nothing changed
that either number could depend on, so **C2's *"+30% that nothing explains"* was
the machine and not the code** — C2's own *a plausible cause measured once is a
guess*, applied to the timing note it wrote about itself.

⚠⚠ **AND THAT MAKES THE RECORDED NOISE FLOOR WRONG.** *"~8% on the biggest
single row and ~1% on the mid rows"* (G5 against G6) came from two runs that
happened to be quiet; the observed between-run spread on this box is **~20% on
every big row**. ⚠ **The S12->S13 eight minutes has to be re-priced against
that** — it was called *20x outside the floor and a real unexplained regression*
on the strength of the floor that is now wrong, and against ~20% an eight-minute
gap on a ~23-minute suite is not clearly outside it. Neither gap has been
bisected and neither should be believed without a controlled repeat.
**A wall clock compared across SESSIONS is not an instrument; the same box in the
same session is.** What survives is the `--durations` LIST as a per-row diff, not
the total as a regression alarm.

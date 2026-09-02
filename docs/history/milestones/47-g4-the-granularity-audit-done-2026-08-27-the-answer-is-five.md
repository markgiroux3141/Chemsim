## G4 -- The granularity audit ✔✔ **DONE 2026-08-27 — the answer is FIVE, and the value of the session is that FIVE IS SMALL**

**The brief, kept because the answer only means something against it:** how many
routes are, like `benzene-nitration`, chemically runnable but scored as blocked
because the catalog spells a mechanism out in steps the engine does in one?
**Nobody had counted.** Until someone did, the BOTH column was an unknown amount
too low, and content work may have been aimed at gaps that are not gaps.

**The deliverable is `validation/granularity.py` (~18 s, five panels) and
`tests/test_granularity.py` (9 tests, 9.3 s).** Every route counted is charged
into a real `Vessel` and its moles are printed. Nothing is credited on an
argument.

### ⚠⚠⚠ 1. THE ANSWER: 31 + 5, AND EACH OF THE FIVE WAS RUN

    benzene-nitration        1.000000 mol nitrobenzene   (340 K, 2 h)
    aniline-route            0.998860 mol aniline        (470 K, 2 h, Ni charged)
    hydrogenation-margarine  1.000000 mol tristearin     (450 K, 2 h, Ni charged)
    tanning-route            1.999999 mol gallic acid    (360 K, 2 h)
    lead-chamber             0.104063 mol sulfuric acid  (650 K burn -> 350 K chamber)

**The reported 31 understates what the engine does by 16%.** But the number that
matters is the other one: **142 routes are outside the BOTH column and only 5 of
them are catalog artefacts — 4%.** ⚠⚠ **THE BOTH COLUMN WAS NOT HIDING A CONTENT
BACKLOG.** The remaining 137 can now be treated as real work rather than as
possible bookkeeping, and that retirement of an unknown is what the session
bought. M1 is the precedent both ways: it fixed this same instrument and its
corrected baseline went DOWN.

### ⚠⚠⚠ 2. THE BRIEF'S OWN WORKED EXAMPLE IS NOT IN THE BUCKET THE BRIEF POINTS AT

`benzene-nitration` is **species**-blocked, not template-blocked: `nitronium` and
`arenium-benzene` are refused a price, correctly — a mechanism has them and a
flask never holds them. The obvious search (walk the species-ready, not
template-ready routes) **would have missed the case that started the audit.**
Granularity has two forms:

* **STEP granularity** — one transformation spelled as several rows whose classes
  have no template;
* **SPECIES granularity** — one transformation spelled through intermediates the
  engine never materialises, and those intermediates have no price.

### ⚠⚠ 3. THE INSTRUMENT SCORES ROWS, AND A ROUTE IS A DAG

That is the finding underneath the count. Four of the five are blocked by a row
that **is not on the path to the target at all**:

    aniline-route            rows 1 and 2 are ALTERNATIVES, read as a sequence
    hydrogenation-margarine  row 2 is the corpus's own "trans isomer byproduct"
    tanning-route            row 2 crosslinks collagen into a MARKER, past the target
    lead-chamber             row 4 makes CHAMBER CRYSTALS -- the FOULING product

⚠ **THE CORPUS SAYS SO IN ITS OWN PROSE AND NOTHING READ IT.** Nine rows in eight
routes are named `... byproduct`, `side reaction` or `alternative`, and five more
rows in five routes have products that are a **subset** of their reactants — they
are workup (crystallisation, salting out, lixiviation, kieselguhr) and cannot ever
match a template. A coverage number that scores them as uncovered mechanisms is
counting gaps no template can close.

### ⚠⚠⚠ 4. THE SCORER MADE THREE FALSE CREDITS AND RUNNING CAUGHT ALL THREE

**This is the most transferable thing in the session.** A `TARGET-REACHABLE`
scorer — does the DAG get from feedstocks to the target — first said 38, not 36:

* `bayer-process` and `contact-process` scored reachable **by BUYING the target**,
  because in both the target is also a step-1 reactant. Bayer *purifies* bauxite;
  the contact process recycles its own acid. ⚠ **A scorer that does not forbid
  charging the target will credit every recycle loop in the corpus.** Rule added,
  38 → 36.
* `starch-hydrolysis` survived that rule and **the RUN refuted it.** `starch-unit`
  is spelled in the corpus as a single α-D-glucopyranose ring, and row 1 reads
  `starch-unit + water -> maltose` — a hydrolysis making a disaccharide out of a
  monosaccharide. The engine matched **nothing at all**: zero reactions, not a
  slow one. 36 → 35, and `benzene-nitration` (found by the other mechanism) puts
  it back to 36.

⚠⚠ **S1's *"crediting a class made a FALSE route credit"* is now a THREE-time
finding, and the only thing that caught it each time was charging a flask.**

### ⚠⚠ 5. ONE CLASS THE INSTRUMENT HAD SIMPLY NEVER KEYED

`TEMPLATE_CLASSES` mapped the M5 `saponification` template under
`ester-hydrolysis`'s name, and the catalog **also** has a class literally called
`saponification`. It read as an uncovered mechanism for eight milestones. Checked
the S1 way before crediting it — tristearin + hydroxide builds 10 species and 7
`saponification` reactions, all three esters off down to glycerol.

    reaction classes covered   51 -> 52        steps covered   114 -> 115
    routes ONE class away      46 -> 47        from classes    36 -> 37
    template-ready / BOTH      41 / 31         UNCHANGED

⚠ **+0 routes, and it was credited anyway**, because a class that reads as a gap
sends work at a template that is already built. `soap-saponification` still cannot
run: its other row is `salting-out` (a phase split) and its target
`sodium-stearate` is REFUSED — the stearate anion has no pKa in the ion table.

### ⚠ 6. WHAT WAS DELIBERATELY *NOT* DONE

**The BOTH column in `COVERAGE_REPORT.md` still says 31.** That table is a
mechanical measure of the CORPUS; the five rest on a hand judgement about five
specific rows (*this row is a byproduct, that one is fouling, that one makes a
marker*). Folding a judgement into a mechanical column is how the `deprotonation`
credit happened in M1. The report gained a **pointer** instead, so the judgement
can be argued with where it is written down.

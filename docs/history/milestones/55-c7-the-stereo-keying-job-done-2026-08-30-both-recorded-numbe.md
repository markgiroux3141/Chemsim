## C7 -- The stereo-keying job ✔✔ **DONE 2026-08-30** *(both recorded numbers were right, about different questions -- and the biggest thing in the session is not stereochemistry)*

**No route, no class, no species, no data row: one new module and six lookup
sites.** Playable stays **21** (tiers 10 / 10 / 1), classes **59/240**, BOTH
**38**, ceiling 45. `PLAYABLE.md` §8b is untouched for the second session
running. What moved is NUMBERS: **43 pairs of spellings that resolved
differently now resolve the same**, and four catalog steps the engine actually
runs stopped pricing their product off an estimator. New:
`properties/stereo_keys.py`, `matter.stereo_free_smiles`,
`validation/stereo_keying.py`.

⚠ The regenerated artefacts say what moved and what did not.
`COVERAGE_REPORT.md`'s **formation half measured goes 146 -> 148** -- lactic acid
and pla-unit -- and `lactic-acid`'s LIMITING tier becomes `compilation`, because
its formation half is measured now and its physical half is a YAWS boiling point.
`PLAYABLE.md` comes back **byte-identical**.

### ⚠⚠⚠ 1. THE FIRST DELIVERABLE WAS A RE-MEASUREMENT, AND BOTH RECORDED NUMBERS REPRODUCED

C4 filed this at **31 of 146**. C6 re-measured **145 of 205** and could not
reconcile them, and NEXT_PROMPT said *"a 4.7x gap on a headline is not a
methodological rounding"*. **It is exactly a methodological difference, and C7
reproduced both numbers to the unit.**

    what was asked                                      count
    canonical spelling carries stereochemistry            212
    ... of those, TETRAHEDRAL ('@')                       146   <- C4's population
    ... of those, E/Z only                                 66
    the two spellings reach different TABLES              149   <- C6's question
    the two spellings resolve to a different SOURCE        49   <- C4's question
    ... of those, tetrahedral                              31   <- C4's headline

C4 filtered candidates on `"@"` in the raw SMILES column, which is a filter on
TETRAHEDRAL stereochemistry -- a double bond carries a spelling too, and 66 more
corpus rows have one. C6 asked about table MEMBERSHIP over the wider population.

⚠⚠⚠ **AND THE 100 COMPOUNDS BETWEEN THE TWO ANSWERS ARE A SEPARATE BUG, WHICH IS
HOW C7 FOUND ITS LARGEST ITEM.** For 102 compounds the record exists under one
spelling and changes nothing: it holds a melting point and no boiling point, and
the Tm overlay is gated on `half.Tb is None`, so a species Joback can fragment
keeps Joback's boiling point *and Joback's melting point*. See §7.

*Membership counts records; only the resolved value counts numbers. Both
sessions measured correctly and only one of them measured the cost.*

### ⚠⚠⚠ 2. THE MECHANISM ON RECORD WAS TWO ROWS OF FORTY-NINE, AND THE REAL ONE IS STRUCTURAL

Fragility 0c said *the two halves of a record are keyed OPPOSITE ways* -- physical
chiral, formation flat. That is **lactic acid and pla-unit**, and nothing else.
The real shape is one table against all the others:

    table                        keys   keys carrying stereochemistry
    MEASURED_PHYSICAL            1239                            146   GENERATED
    PHYSICAL_PROPERTIES             9                              0   hand-typed
    IDEAL_GAS_FORMATION            82                              0   hand-typed
    LIQUID_FORMATION               58                              0   hand-typed
    _CURATED_RAW                   50                              0   hand-typed
    _CURATED_FUSION                 4                              0   hand-typed
    electrolyte._PAIRS             29                              0   hand-typed

**The only table with a spelling in its keys is the one a GENERATOR wrote.** S13
built `MEASURED_PHYSICAL` by resolving corpus SMILES to CAS numbers, so it
inherited the corpus's spelling; every other table was typed by hand and a human
types the simple form. ⚠ *That is a rule about how a table came to exist, not
about chemistry, and it predicts the direction of every one of the 147 one-sided
rows C6 measured.*

### ⚠⚠⚠ 3. IT WAS LIVE, AND WHAT MADE IT LIVE IS A TEMPLATE

A missed record costs nothing unless something looks a species up FLAT, and the
corpus never does. **No template in the library spells stereochemistry on its
product side: 0 of 50.** A rewrite cannot emit a spelling its SMARTS does not
name, so every centre a template makes or touches comes out unspecified -- and
the unspecified species is not the corpus's. Four catalog steps, run:

    step                     emitted                     Tb was      Tb now
    perkin-route 1           O=C(O)C=Cc1ccccc1        581.9 Job    573.1 CRC
    knoevenagel-route 1      O=C(O)C=Cc1ccccc1        581.9 Job    573.1 CRC
    menthol-route 2          CC1CCC(C(C)C)C(O)C1      530.3 Job    487.1 CRC
    lactic-acid-pla 1        CC(O)C(=O)O              505.5 Job    398.1 YAWS
    biodiesel-route 1        CCCCCCCC/C=C\CCC...        the CONTROL: unchanged

The control is the one that matters as much as the three: `transesterification`
does not touch the C=C, so RDKit carries the spelling through and the emitted
methyl oleate IS the corpus's. **A template loses a spelling only where it
rewrites one.**

⚠ `matter/molecule.py` had said this in prose since v1 -- *"templates do not
yet control stereochemistry, so a rewrite can lose it; the identity model is
ahead of the reaction model here"* -- and nothing had ever measured what it
costs. *A limitation written down is not a limitation priced.*

### ⚠⚠ 4. THE FIX: A FALLBACK WITH TWO LIMITS, AND THE SECOND ONE FIRES

`properties/stereo_keys.py`. S6's rule -- a fallback and never an override -- with
the two limits that are the whole of its safety:

1. **It may cross an AMBIGUITY and never a DIFFERENCE.** A query naming no
   stereochemistry may take a record that names some; a query naming some may
   take a flat record. Two differently specified spellings never share one --
   those are two species, which is what `matter/molecule.py` says and this must
   not contradict.
2. **The unspecified side must be answered by EXACTLY ONE record.**

⚠⚠ **The second guard is not defensive programming: `MEASURED_PHYSICAL` holds
seven skeletons carrying more than one stereoisomer, and the worst of them is
`O=C(O)C=CC(=O)O` -- maleic and fumaric acid, 230.1 K apart in Tb.** A flat
butenedioic acid without the guard takes one of them depending on dictionary
order. The aldohexose skeleton offers glucose, mannose and galactose; `CC=CC`
offers cis-2-butene, trans-2-butene *and* the flat spelling. **A fallback that
guesses is worse than the estimator it replaces, because it is wrong with a
measurement's authority.**

Every value that arrives this way says so: the provenance string gains
`(matched on the stereochemistry-free spelling: <key>)`. The provider takes a
`stereo_fallback=False` flag, for the same reason `benson=False` and
`measured_physical=False` exist -- the difference is measured, not described.

### ⚠⚠ 5. THE STRIP HAD A TRAP IN IT AND IT IS ONE CHARACTER OF API

`Chem.MolToSmiles(mol, isomericSmiles=False)` is the obvious way to flatten a
spelling and it is the wrong one: **it drops ISOTOPE labels too.** It turns
`[2H][2H]` into `[H][H]` and `[13CH4]` into `C`. Built on that flag, the fallback
would hand **deuterium hydrogen's record** -- two species merged by a flag
reached for to do something else. `matter.stereo_free_smiles` uses
`Chem.RemoveStereochemistry`, which touches only stereochemistry, and says why.

⚠ It also explains part of the 212-vs-205 gap between C7's population and C6's,
and it is why C7's own first probe counted deuterium as a stereoisomer.
*The instrument had the bug it was looking for.*

### ⚠ 6. WHAT THE RULE REFUSES, AND IT IS RIGHT ABOUT HALF OF IT

Two corpus rows have a sibling record the fallback will not take:

    elaidic-acid   dTb 128.0 K   the table holds oleic acid, the CIS isomer
    pla-unit       dTb 107.3 K   the table holds L-lactic acid; this is the D

**The rule is right about the first and costs the second.** Elaidic and oleic
acid are different compounds; taking one for the other would be a wrong number
with a measurement's authority. D- and L-lactic acid have the same scalar
thermochemistry, so that record IS pla-unit's, and 107 K of Joback is a real
loss. *A rule that took the sibling would be right once and wrong once.*
Separating them means inverting every centre and comparing -- cheap to state,
easy to get wrong on a diastereomer, and worth exactly one row. **Priced rather
than guessed at.**

### ⚠⚠⚠ 7. THE LARGEST THING C7 FOUND IS NOT ABOUT STEREOCHEMISTRY, AND IT IS NOT FIXED

Chasing why 102 compounds have a record that changes nothing:

    MEASURED_PHYSICAL entries                                    1239
    ... holding a melting point and NO boiling point               376
    ... whose measured Tm never reaches the resolved record        214

The physical half reads `if m.Tm is not None and half.Tb is None:`, so a
measured melting point is overlaid only where nothing else supplied a boiling
point. Joback supplies one for anything he can fragment -- **and then he supplies
the melting point too.** Worst case is **877 K**: methotrexate melts at 468.1 K
and the record says 1344.7.

⚠⚠ **AND THE COMMENT BESIDE THAT GATE ARGUED IT WAS HARMLESS ON A CLAIM THE
GENERATED FILE CONTRADICTS.** It read *"Nothing in the measured table is a
species Joback already prices completely (the builder checks and reports), so no
existing record's fusion pair moves."* `tools/build_physical_data.py` classifies
each candidate and does **not** exclude on it: **855 of the 1239 entries are
stamped `Joback: complete` in the generated file itself.** *A check that reports
is not a check that filters.*

Tm drives crystallisation and enters the solubility law exponentially, so this is
worth more than the thing the session was about. **Deliberately not fixed here**:
closing it moves 214 melting points at once, and inside a session about spellings
neither change would be attributable. It is fragility 0c-i and it is the top of
the queue.

### ⚠ 8. WHAT ELSE IS STILL KEYED FLAT, WITH ITS SIZE

`electrolyte._PAIRS` prices lactic acid as `CC(O)C(=O)O` and the corpus spells it
`C[C@H](O)C(=O)O`, so **a corpus-spelled lactic acid in water does not
dissociate.** Two rows (`lactic-acid`, `pla-unit`), measured, live. Left out of
this session's fallback on purpose: `_PAIRS` decides WHICH IONS EXIST, so
widening it changes the state vector rather than a number in it, and C6's rule
makes that a network-construction change owing its own audit. Fragility 0c-ii.

### ⚠ 9. AN INSTRUMENT ERROR THE AUDIT CAUGHT ON ITSELF

Panel 5 first reported **16** compounds still disagreeing after the fix. Ten of
them agree to 2e-16. **Benson sums its group contributions in the order the atoms
come out of the SMILES, and a stereochemistry-free spelling numbers the atoms
differently**, so the same molecule spelled two ways gives Cp coefficients that
differ in the last bits. Compared with `==` that reads as a failure to fix them.
The panel compares to 1e-12 now and reports the bit-noise separately. ⚠ *A
group-contribution sum is not bit-reproducible across spellings*, which is worth
knowing on its own and is nowhere else recorded.

### 10. THE SUITE AND THE TOLERANCE AUDIT

    1191 passed / 0 failed in 28:00        <- run ALONE, nothing else on the box

C6 was **1181 in 29:01**. C7 adds ten tests: one in `test_fermentation.py` for
the template-made species, and `tests/test_stereo_keys.py` (9).

⚠⚠⚠ **AND C7 RAN THE SUITE TWICE ON IDENTICAL SOURCE, WHICH SETTLES A
METHODOLOGICAL CLAIM C6 MADE.** The first run was **1182 in 29:58**, the second
**1191 in 28:00** with 1.14 s of new tests between them:

    run          tests    total / s    SECONDS PER TEST
    C6            1181       1741.4              1.4745
    C7 run 1      1182       1798.2              1.5214
    C7 run 2      1191       1681.0              1.4114

**The same source, the same session, the same box, and the per-test total moves
6.6%.** C6 offered that statistic as the stable one -- *"quote the per-test
total, never a row"* -- on the strength of landing within **0.03%** of C5 across
an engine change. ⚠ **That agreement was a coincidence.** The per-test total is
not reliable to better than ~7%, and C7 measured that CONTROLLED rather than
across sessions, which is the first time anything here has. *Two runs can say a
statistic is noisy; only two runs of the SAME code can say how noisy.*

```bash
python -m pytest -q --durations=25
```



⚠⚠⚠ **THE AUDIT IS ~10 MINUTES, NOT 2 h 35 m -- C6's CORRECTION WAS ITSELF
WRONG, AND C7 QUOTED IT FORWARD BEFORE MEASURING IT.** Timed **01:33:22 ->
01:43:53, 10 m 31 s**, and the run's own summary bounds it independently: the
twelve examples' loose and tight wall clocks sum to **622 s**, which is the
whole of the work it does. C6 recorded 16:26:05 -> 19:01:39 and attributed that
entire interval to the audit. **The repo's original "ten minutes" was right, was
replaced by a measurement of something else, and was then quoted forward twice
-- into C7's plan and into the question C7 put to the user about what the
session would cost.** ⚠ *A wall-clock interval is not a duration unless
something was watching the process.*

⚠⚠ **AND THE AUDIT IS CLEAN FOR C7: EVERY ROW C6 RECORDED COMES BACK EXACTLY.**
`named_routes` raises (the diagnosed entry), `workshop` 2 lines / 1.98e-04,
`activity` 1.28e-03, `mercury_retort` -- the harness's own self-check -- 0 lines
and 1.00x, and **`multistep_prep` 8 lines / worst 1.07e-03**, which is where
C5's speciation fix left it and where C6 found it. **Nothing moved**, which is
the right answer for a change that gives two spellings of one substance the same
numbers rather than changing what any single species integrates.

The two quotable-digit rows are unchanged and still quotable-digit rows:
`activity` at 0.1277% and `multistep_prep` at 0.1073%. Four more move below
0.1%. Tight is faster in 5 of 12 and slower in 7, worst 4.6x.

```bash
python validation/tolerance_audit.py            # ~10 min, and OWED by any change
                                                # to an RHS, a data table, or
                                                # network CONSTRUCTION
```


### ⚠ 11. WHAT C7 DID NOT DO, SAID OUT LOUD

* **Nothing on the scoreboard**, for the second session running. 21 playable,
  59/240 classes, 38 BOTH, ceiling 45. §8b is untouched and still has five
  classes tied at +1. ⚠ `COVERAGE_REPORT.md` did move: **formation half
  measured 146 -> 148**, lactic acid and pla-unit, and `PLAYABLE.md` regenerates
  byte-identical.
* ⚠ **The root README's coverage table was several regenerations behind and is
  now copied from the generated report.** It was quoting a formation coverage
  **155 compounds too high** (921 against 766), a class count against the wrong
  denominator (51/229 against 59/240) and a BOTH column of 31 against 38. C7 did
  not cause that drift and the memory note about it said "one regeneration
  behind"; it was more. **The front door of the repo is the one number nobody
  re-runs.**

* **The Tm gate is measured and open** (§7). It is the biggest live number in
  this file.
* **`electrolyte._PAIRS` is not wrapped** (§8). Two rows.
* **The enantiomer extension is priced and not built** (§6). One row.
* **Templates still do not control stereochemistry.** The identity half of the
  mismatch stands; only the lookup half is closed.
* **No other SMILES-keyed table was swept for the same shape beyond the eight in
  §2** -- `psrk_data`, `unifac_data` and `mineral_data` are keyed by group or by
  mineral name rather than by species, and `dielectric_data` was measured at 0
  stereo keys, but nothing checked the SOLID tables.

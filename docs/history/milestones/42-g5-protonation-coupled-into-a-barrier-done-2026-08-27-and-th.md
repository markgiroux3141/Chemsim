## G5 -- Protonation coupled into a barrier ✔✔ **DONE 2026-08-27** *(and the answer is that it is a DATA job, and it does not close the gap)*

⚠ **NUMBERED G5 AND PLACED HERE ON PURPOSE.** It was not in the original
G-series list -- G2 created it as *"the best-scoped new item"* and NEXT_PROMPT
carried it above G3. Done items are kept in completion order at the top of this
section, so G5 sits between G2 and the unbuilt G3/G4 rather than after them.

⚠⚠⚠ **THE BRIEF'S FIRST DESIGN QUESTION WAS THE RIGHT ONE AND THE ANSWER
KILLED THE DESIGN.** G2 asked: *"Is it a barrier shift or a species split? ... 
Measure that before designing a coupling -- it would be a data job, not an
engine one."* It IS a species split, `dissociation_templates()` DOES already
make the ion, and the table row is three lines. **And the arithmetic bound,
taken before any of it was written, says the split does not fix aniline.**

Two channels run in parallel and the pot's acidity weights them:

    free base   -NH2   sigma+ -1.300   k/k0 = 2.8184e+08
    anilinium   -NH3+  sigma  +0.860   k/k0 = 2.5704e-06     ratio 1.10e14

    crossover at [H3O+] = Ka * k_free / k_ion = 2.630e+09 mol/L,  pH -9.42

⚠⚠ **AND -9.42 IS NOT A WRONG NUMBER.** Real aniline gives largely meta product
only in 90-98% sulfuric acid, whose Hammett acidity function H0 falls to
roughly -8 at 90 wt% and roughly -10 at 98 wt%. ⚠ The band is quoted to ONE
FIGURE because it is recalled rather than sourced here: the claim is that -9.42
lands INSIDE the band real aniline nitration is run in. The engine's own two
table rows land it there without being told about it. **The split is the right model; the flask
cannot get there.**

⚠⚠⚠ **AND THE WALL IS A SECOND MEASUREMENT NOBODY HAD TAKEN: THE POT GETS LESS
ACIDIC AS THE ACID GETS DRIER.** 5 + 5 mol of HNO3/H2SO4 in 30 mol of water
reads **pH -0.789**; the same acid in 10 mol reads -0.233 and in 2 mol reads
**+4.899**. Every dissociation here is written with water on both sides, so
`[H2O]` is a mass-action factor and running out of water suppresses the reaction
that makes the proton -- real chemistry the engine gets for free, and also the
ceiling. **The reachable floor is pH -0.79, ten decades above the crossover.**

⚠ **SO THE LIMIT IS RENAMED RATHER THAN REMOVED. It is not "no protonation in a
barrier" any more; it is "NO ACIDITY FUNCTION"** -- H0 is not the concentration
of anything, and this engine's only handle on acidity is a mass-action molarity.
That is a better-posed gap than the one G2 named, and it is the honest state of
the aromatic branch.

**What was built, and what it buys:**

* `ion_thermochemistry` anchors on the **NEUTRAL** member of a pair rather than
  on the acid. ⚠⚠ **FOUR CURATED ROWS HAD BEEN PRODUCING NOTHING** -- ammonium,
  methylammonium, pyridinium, anilinium are CATION/neutral pairs whose acid is
  the ion, and a bare `except Exception: continue` swallowed the (correct)
  refusal to price a charge. **Refused species 430 -> 419, ion-resolvable
  84 -> 95, species-ready routes 80 -> 82, `solvay-process` 0 -> species-ready.**
  Eleven corpus species -- every ammonium salt in the catalog -- and
  `COVERAGE_REPORT.md` had been printing the refusal for twelve of them, session
  after session. The 24 anions are BIT-IDENTICAL.
* an `ammonio` sigma row (0.86 / 0.60, labelled PROXY, meta-directing DECLARED),
  so an anilinium is no longer priced as an unsubstituted benzene. ⚠ It is the
  one row whose two constants are ordered the wrong way round, which is the
  second reason `meta_directing` is not derived.
* `amine_protonation` replaces `ammonium_dissociation`, whose `[NX4H+]` matched
  a protonated TERTIARY amine and nothing else -- **the template named for the
  ammonium ion was the one ion it could not touch.** Written
  protonation-forward, because discovery is forward-only.

**Measured in the engine: 2.8e8 -> 380 x benzene. Six of the fourteen decades.**
⚠⚠ **And the other eight are not in the protonation model** -- the anilinium is
100.000% of the aniline in the pot and carries **1e-7 %** of the rate. The
residual is a FREE-BASE LEAK, and the next item is named with its arithmetic
done: `rho * sigma+` = 8.45 decades off a line fitted on |rho*sigma| < 2.6, where
the real relation SATURATES because nitration of an activated arene is
encounter-controlled. See HANDOFF §101 and `validation/protonation.py` panel 5.
⚠⚠ **AND ITS DESIGN QUESTION IS WHICH OF TWO THINGS IT IS**: a capped RATIO of
decades (SETUP, free, but asserts a temperature-independent selectivity at the
ceiling) or an absolute ENCOUNTER RATE (physically right, but the two rate laws
have different temperature dependences, so it is an RHS edit with the tolerance
audit attached). **Measure the temperature spread over 300-380 K first** -- if
the capped rates stay well under the encounter limit there, the two forms are
indistinguishable and the cheap one wins. See NEXT_PROMPT.

⚠ **A NEW STRUCTURAL MISMATCH, AND THE REFUSAL IS KEPT:** a protonation
TEMPLATE is open-ended where the ion table is a CURATED LIST, so nitrating an
aniline refuses to build on a nitroanilinium nobody curated. Curating the nine
pKa values is measured to buy nothing, so the refusal stands -- the element
floor's rule applied to a pKa.

⚠⚠ **AND THE PLAYABLE RESULT IS THE ONE REAL CHEMISTRY USES, ALREADY
BUILDABLE:** nobody nitrates an aniline, you acetylate it first. An amide does
not answer `amine_protonation`'s pattern, so the acetanilide network BUILDS where
the aniline one refuses. **Nobody told the engine that an amide is a protecting
group.**
⚠ **G6 CHANGED WHY THIS WORKS AND NOT WHETHER IT DOES.** G5 wrote it as a
BARRIER difference -- acetanilide activated by 22.3 kJ/mol against aniline's 48.2
-- and under the encounter plateau both rings are activated by the same 15.3
kJ/mol, because both ask the line for more than 2.686 decades. The protection is
therefore entirely about PROTONATION, which is the real mechanism: an amide has
no lone pair to protonate and an aniline in mixed acid is an anilinium.

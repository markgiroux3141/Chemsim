## S12 — The Skraup, whose oxidant becomes one of its own reagents  ✅ **DONE 2026-08-26 — +1 on every column as predicted, and the source comment's own hand-priced numbers were wrong by 163 kJ/mol before the audit caught them**

**+1 class, +1 template-ready, +0 species-ready, +1 RUNNABLE — all four predicted
before the audit ran and all four came out.** The coverage queue's top row, taken
for the mechanic S11 named it for: a row that reads like a bookkeeping error and
is not one.

| | before | after |
|---|---:|---:|
| classes with a template | 50 / 229 | **51 / 229** |
| routes template-ready | 40 / 173 | **41 / 173** |
| routes species-ready | 77 / 173 | 77 / 173 |
| ⚠⚠ **routes BOTH — the one to quote** | **30** | **31** |
| templates | 45 | **46** |

⚠ **NO ENGINE CODE CHANGED, THIRD MILESTONE RUNNING.** Not one line of
`numerics/` or `vessel/`, and no data table either — so `tolerance_audit.py`
carries no new exposure and was not re-run. Everything below is one template, one
class registration, one standing audit and one test file.

### ⚠⚠ 1. THE ROW HAS ANILINE ON BOTH SIDES AND IT IS NOT THE `spurious` PATTERN

    skraup-route 2 | aniline + acrolein + nitrobenzene + sulfuric-acid
                   -> quinoline + aniline + water + sulfuric-acid

`corpus_balance`'s `spurious` bucket is 17 rows of a reagent written as consumed
that is really a catalyst. This is not one of them: **the aniline coming out is
the NITROBENZENE, reduced.** Each ring closure sheds two hydrogens and one
nitroarene takes six, which forces the multiple:

        3 x  aniline + acrolein  ->  quinoline + H2O + 2 [H]
             PhNO2 + 6 [H]       ->  PhNH2 + 2 H2O
        ---------------------------------------------------------
        3 aniline + 3 acrolein + PhNO2 -> 3 quinoline + PhNH2 + 5 H2O

C33H38N4O5 on both sides, four aromatic rings in and four out. **Seven reactant
slots and nine product slots**, plus the acid on both sides as an eighth — the
`claus_comproportionation` shape, at a third of the size. The SMARTS was written
from the electron count and balanced first time.

### ⚠⚠⚠ 2. THE BIGGEST FINDING IS THAT MY OWN PRICED NUMBERS WERE WRONG, AND THE AUDIT CAUGHT THEM

The block comment in `synthesis.py` was written BEFORE the audit ran, off a hand
calculation summing `ThermoData.Hf` and `.Gf` over both sides. It said
**dH −561.63, dG298 −572.55, dS +36.65 J/(mol K)**, and it built an argument on
the sign of that dS: seven molecules become nine, so heating the flask makes the
forward direction more favourable, so irreversible is safe. Then panel 2 printed
what `reaction_deltas` actually returns:

|  basis | dH / kJ | dG298 / kJ | dS / J/(mol K) |
|---|---:|---:|---:|
| ideal gas | −561.63 | −572.55 | **+36.65** |
| pure liquid | −725.16 | −627.05 | **−329.08** |
| difference | **−163.53** | −54.49 | **−365.73** |

⚠⚠ **THE TWO BASES DO NOT AGREE ON THE SIGN OF dS, AND THE EASY ONE IS THE WRONG
ONE.** The template is `phase="liquid"`, so `reaction_deltas` puts every
condensable species on its own pure liquid — and **NINE product molecules
condense against SEVEN reactant ones.** That is worth 163.53 kJ/mol in dH and it
flips the entropy.

⚠ **THE CONCLUSION SURVIVED AND THE REASON FOR IT DID NOT.** Irreversible is
still safe: ln K on the basis the engine uses is **252.9 at 298 K, 154.2 at 450
and 105.8 at 600**, and dG crosses zero at **2204 K**. But the argument that made
it safe was about the wrong standard state, and *"seven molecules become nine"* is
exactly the kind of sentence that reads as a physical fact and is a basis-
dependent one. **A PHASE LABEL CARRIES A STANDARD STATE** — S1 recorded that
about a surface rate law, and it is the same trap in a comment.

`test_the_two_standard_states_disagree_on_the_sign_of_dS` pins BOTH rows, so the
comment cannot rot back to the hand calculation it started as.

### ⚠⚠ 3. THE PREPARATION'S OWN ODDITY FALLS OUT OF THE FLASK, NOT OUT OF A DECLARATION

A real Skraup makes its acrolein in situ from glycerol and never charges it. The
textbook reason is that neat acrolein polymerises. Here is the other half,
measured — acrolein boils at 314 K and this reaction runs at 450:

    k_vent      quinoline   acrolein left
    0 (sealed)   1.000000       0.000000
    1e-3         0.919592       0.000000
    1e+0         0.061473       0.000000
    1e+3         0.016883       0.000000

**An open flask loses 98% of the yield**, and nothing declares that: it is the
vapour-pressure curve against the vent conductance, the same mechanic that gives
the Claus train its sulfur condenser. ⚠ It is also why `run()` in the audit is
sealed — this project has no reflux head that returns a vapour to the pot, so
`k_vent=0` IS the condenser, and the pressure that buys (13.7 bar at 450 K) is
printed rather than hidden.

### ⚠⚠ 4. THE OXIDANT'S REDUCTION PRODUCT IS ITSELF A SUBSTRATE, AND THE NETWORK FOUND IT

Charge **p-toluidine** instead of aniline and nothing else, and the flask makes:

    Cc1ccc2ncccc2c1   6-methylquinoline    0.666667 mol
    c1ccc2ncccc2c1    quinoline            0.333333 mol
    Nc1ccccc1         aniline              0.000000 mol

**Exactly 2:1, totalling the 1.0 mol of acrolein charged.** The nitrobenzene is
reduced to aniline and the aniline then goes round again as a SUBSTRATE, because
the template's three amine slots do not have to be the same molecule — so one
event in three has to spend an aniline. That is a real nuisance of the real
preparation (a Skraup on a substituted aniline with nitrobenzene as the oxidant
contaminates its product with the parent quinoline) and **nobody declared it**.
It is the clearest emergence this project has produced from a single template.

### ⚠ 5. THE SMALL THINGS THAT WERE STILL DECISIONS

* **Every slot it consumes keeps order 1** — S11's rule, and here it costs
  nothing to obey. `orders=(1,1,0,0,0,0,1,1)`: first order in the amine, the
  enal, the oxidant and the acid, so nitrobenzene carries an exponent rather than
  being driven negative. Unlike the Wacker, where the same rule forces an oxygen
  order the real rate law says is zero, **a real Skraup DOES slow as its oxidant
  is spent**, so the honest declaration is also the right one. Measured:
  0.10 / 0.20 mol of nitrobenzene cap the yield at exactly 3x, and the acrolein
  sits there.
* **The acid is spelled as the hydronium it makes**, not as `sulfuric-acid`.
  That is `ACID_CATALYST` and the same choice `esterification`,
  `ether_condensation` and `alkene_dehydration` already make; it is also why the
  network needs `electrolyte_provider()`, which is the Wacker's gate again.
  A flask with no acid makes **exactly zero**.
* **Ea 80 kJ/mol, A 3.0e6 (3.0e7 declared, after `CATALYST_REFERENCE`).** An
  APPARENT barrier over a four-step sequence, fitted to the one thing the
  preparation reports — a Skraup at violent reflux is over in an hour or two.
  Measured at one minute: 1.85% at 350 K, 36.6% at 400, 69.7% at 420, 98.4% at
  450.
* ⚠ **`validation/rate_ceiling.py` GAINED A SKRAUP PANEL**, because a template
  that is not in that file is not audited and "it is obviously small" is not a
  measurement. 2.90e-18 of the bimolecular ceiling — and the crossing column is
  meaningless for it for the Deacon's reason, since a fourth-order `A` is in
  L^3/(mol^3 s).
* `validation/skraup.py` is a new standing audit, ~10 s, seven panels. Every
  claim above is one of its panels; the class is credited on an INTEGRATION and
  not on the coverage table, which is the S1 standard.
* `COVERAGE_REPORT.md` and both `derived/*.psv` re-checked byte-identical across
  `PYTHONHASHSEED`.
* **The whole suite: 961 passed / 0 failed in 13:20**, run after every `src/`
  edit. ⚠ 952 + 9 would have given the same number, which is exactly why it was
  RUN rather than computed.
* ⚠ **A `⚠` inside a `print()` did NOT ship this time.** Twenty-six sessions.

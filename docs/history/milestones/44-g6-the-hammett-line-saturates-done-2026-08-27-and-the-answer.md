## G6 -- The Hammett line SATURATES ✔✔ **DONE 2026-08-27** *(and the answer to its design question was a measurement, not a preference)*

⚠ **NUMBERED G6 AND PLACED HERE FOR G5's REASON.** It was not in the original
G-series list either: G5 created it, measured its arithmetic and deliberately
did not build it because the CONSTANT needed sourcing. NEXT_PROMPT carried it as
item 1 of the work order. Done items are kept in completion order.

**WHAT IT IS.** `rho * sum(sigma+)` priced aniline **8.45 decades** above
benzene off a line fitted on arenes with |rho·sigma| < 2.6 -- a 3.25x
extrapolation of the abscissa -- and the real relation does not go there:
nitration of a strongly activated arene is **ENCOUNTER-CONTROLLED**, so past a
plateau further activation buys no rate at all.
`hammett.SATURATION_DECADES = 2.686`, one-sided, declared per template as
`ReactionTemplate.hammett_saturation`. **At SETUP, so no RHS edit and no
tolerance-audit exposure**, and everything under the plateau is bit-identical.

⚠⚠⚠ **THE BRIEF'S DESIGN QUESTION -- CAPPED RATIO OR ABSOLUTE ENCOUNTER CEILING
-- ANSWERED ITSELF IN A MEASUREMENT, AND NOT THE COST ARGUMENT THE BRIEF
EXPECTED.** `min(k_hammett, k_enc)` is the physically correct form for an
ELEMENTARY step, and it can only ever fire on the one case a floor already
catches: with the plateau lifted, every substrate with a positive barrier runs
at 0.9-1.2% of a diffusion ceiling or less, and only 4-aminophenol reaches it
*because* `clamp_barrier` has already floored its barrier at zero, leaving
`k = A = 1e10`. ⚠⚠ **AND THE REASON IS STRUCTURAL: THIS RATE LAW IS NOT
ELEMENTARY.** `aromatic_nitration` is written on the arene and HNO3, so the
nitronium pre-equilibrium is folded into `Ea`; an absolute ceiling in these units
would have to be `k_enc * [NO2+]/[HNO3]`, a property of the medium's ACIDITY --
the thing G5 measured this engine has nowhere to put. The observable plateau
sits **six decades below** any diffusion constant. **The capped ratio is not the
cheap approximation to the right model; it is the only one that can express what
was measured.**

⚠⚠ **THE CONSTANT IS HAND-AUTHORED AND THE BOUND IS THE DELIVERABLE**, which is
the licence § STATED NON-GOALS gives an A-factor. Belson & Strachan, *J. Chem.
Soc., Perkin Trans. 2*, **1989**, 15 (aq. HNO3, 293-333 K):
benzene : toluene : p-xylene : mesitylene = **1 : 22 : 256 : 485**, with
p-xylene and mesitylene *diffusion-controlled and the others not*; log10(485) =
2.686. Coombes, Moodie & Schofield, *J. Chem. Soc. B*, **1968**, 800: the limit
exists and IS the encounter rate, with benzene within a SIXTH of it in the
strongest acids.
⚠⚠⚠ **AND THE SECOND SOURCE IS THE LOWER BOUND RATHER THAN A RIVAL VALUE.**
Benzene-within-a-sixth reads as 0.778 decades and applying it caps **toluene at
6.0 against a measured 22** -- damaging a substrate the same literature says is
NOT diffusion-controlled. **A plateau cannot sit below the fastest substrate that
does not saturate**, so the band is 2.02-2.69 and the declared value is its top.

**THE RESULT.** mesitylene 1.16e6 -> **485** (the datum; a 2400x correction),
p-xylene 1.10e4 -> 485 against a measured 256 (1.9x high, the factor the
plateau's own two data differ by), toluene **untouched** at 105 against 22
(that 4.8x is `rho`'s). ⚠⚠ **And the aniline in the engine's most acidic
reachable flask goes from 1.10e3 x benzene to 1.89e-3 x -- 5.8 decades and
across the line that matters**, because the observable is that aniline in strong
acid nitrates SLOWER than benzene. **It took G5 and G6 together**: the split
supplies the deactivated species, the plateau stops the free base being priced
off the end of the line.

⚠⚠ **THE CORPUS COST IS MEASURED AT ZERO** -- `benzene-nitration` 1.0000,
`tnt-route` 0.0643, `picric-acid-route` 0.1250 mol, unchanged to four decimals,
with phenol's first nitration slowed **1968x** to get there because that step was
never rate-limiting. G4's number says why that was predictable. ⚠ **G2's
four-route cost table is a script now** rather than a HANDOFF paragraph.

⚠⚠ **AND IT COST G5 ITS HEADLINE, WHICH IS THE THING TO CARRY FORWARD.** G5
reported the free-base/anilinium crossover at pH **-9.42** landing inside the
real H0 band *"without being told about it"*, and read that as evidence the split
was right. **That agreement was a property of the extrapolation**: with the free
base at a sourced plateau the crossover is **-3.66**. The split is still the
right model and the pot still cannot reach either number, but the coincidence was
not evidence. **A number that agrees with reality is only evidence if the model
behind it is inside its own domain.**

⚠ The one-sided decision was measured too: a two-sided cap at the same value
puts 0.0345 mol of trinitro in the flask in ten seconds at 300 K and finishes at
340 K, which is G2's failure restored.

See HANDOFF §103, `validation/saturation.py` (six panels, 27 s),
`tests/test_saturation.py` (12 tests).

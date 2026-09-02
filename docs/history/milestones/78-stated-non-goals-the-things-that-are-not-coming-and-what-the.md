# ⚠ STATED NON-GOALS — the things that are NOT coming, and what they cost

This section exists because the audit that produced M10 and M11 also found three
gaps that appear in **no** planning document, and silence is how a limitation
turns into a surprise. Each is written down here with its measured cost so that
the decision to skip it is a decision rather than an oversight.

**PHOTOCHEMISTRY — not planned, and it costs ONE STEP.** Light is not a driver
anywhere in the engine, and doing it PROPERLY means an intensity field, a quantum
yield per transition and a path length. Measured against `data/catalog`: exactly
**one step** in 377 is `photoreduction`. ⚠ The honest reading is that this is a
CATALOG artefact rather than a fact about chemistry — photochlorination and
photographic development are real, cinematic, and absent from the corpus — so if
either ever gets added, this line has to be re-costed rather than cited.

⚠ **AND THERE IS A CHEAP APPROXIMATION THAT NEEDS NO ENGINE WORK, so "not
planned" must not be read as "impossible".** Explicit catalysis (HANDOFF 37)
folds a catalyst concentration into `A` and DECLARES it — `_maybe_catalyse` and
`_kinetics` in `reactions/library.py`. A lamp is the same shape: a photon flux
folded into the pre-exponential of a template that only exists while the lamp is
on. That buys "the reaction goes in the light and not in the dark", which is the
whole of the game mechanic, and it buys none of the photophysics. It is subject
to the same rule as any other folded constant: **declare it, and say what bounds
it.**

**STEREOCHEMISTRY CONTROL — not planned, and it costs ZERO catalog steps.**
⚠ The cheap approximation here is a DECLARATION rather than a model: a template
could state `retention` / `inversion` / `racemic` on a mapped centre without the
engine gaining any stereochemical reasoning at all. That is worth doing the day a
chiral template is written, and not before.
`matter/molecule.py` is explicit that identity DISTINGUISHES stereoisomers
(RDKit's canonical SMILES is isomeric, so R/S and E/Z are different species) but
that templates cannot SET them. So asymmetric synthesis, chiral resolution and
enantioselective catalysis are out. **No catalog route needs one**, which is why
this is a non-goal rather than a milestone — but note the asymmetry: the engine
would happily let a template produce the wrong enantiomer *silently*, because a
rewrite that does not specify stereochemistry is not an error. ⚠ If M5 ever
authors a template on a chiral centre, that template must say what it does to the
centre or the project acquires exactly the kind of confident wrong answer it
exists to refuse.

**ABSOLUTE REACTION TIME — not achievable, and this one is permanent.**
Pre-exponentials are the last hand-authored parameter and there is no route to
deriving them: barriers set the temperature response and the competition between
pathways (and are sourced), while A-factors set only the absolute timescale.
⚠ **The risk is EROSION, not error** — that a simulated reaction time eventually
gets quoted as a prediction. The sulfur burner is the standing counter-example
(A pinned to the collision limit, the resulting soft threshold asserted rather
than tuned away), and the rule stays: bound an A against a stated observable, or
declare it hand-authored and say what bounds it.

⚠ **What none of these three is: a blocked reaction.** Photochemistry costs one
catalog step, stereochemistry costs none, and the A-factor limitation degrades a
NUMBER rather than removing a transformation. Measured, **121 of the catalog's
173 routes (70%) sit behind no wall at all** and are pure template-and-data work;
of the 52 that do, **32 are behind M6, M8 and M9**, 8 behind M10 and 16 behind
M11. **There is no permanent hard wall in this project's way — only unbuilt
milestones.**

---

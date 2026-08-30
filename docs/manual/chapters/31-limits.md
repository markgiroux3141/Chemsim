\part{Limits}

# What it cannot do, and what each gap would cost

Every item here is deliberate, measured, and has a stated route out. They are
grouped by what kind of thing is missing, because that determines what fixing one
would take.

## Missing accuracy

**Group-contribution formation data is the dominant error in $K$.** With the
standard state fixed, Fischer esterification sits at 8.1 against a measured
$\approx$ 4. Joback's $\Delta G_f$ carries several kJ/mol of uncertainty, which
is a factor of 2--4 in $K$ (Chapter 4). *Route:* more curated $\Delta G_f$, or
wider Benson coverage. Ongoing.

**UNIFAC understates how fast an associating solute's solubility climbs with
temperature.** Benzoic acid in water is 0.95$\times$ measured at 298 K and
0.48$\times$ at 333 K. The absolute scale is right; the slope is not.

**Gas solubility is transferred, not measured.** Only the aqueous Henry
constants are experimental; every other solvent is predicted through
$\gamma^\infty$, and runs about 25% low for the common solvents and 2.6$\times$
high for acetone.

**Carbon monoxide's reference state fits poorly** --- 3.6% against 0.15% for O₂,
because PSRK's parameters for it are strongly quadratic in $T$. Reported by the
activity model rather than absorbed.

**The gas extension mixes two regressions.** Organic pairs are UNIFAC-VLE, gas
pairs are PSRK. Sound because PSRK's organic backbone *is* UNIFAC's (1124 of
1174 pairs bit-identical), but it is a join, not one self-consistent fit.

## Missing models

**Equilibrium is on a concentration basis, not an activity basis.** $\gamma$
corrects phase equilibria and solubility but **not the reaction quotient**, so a
strongly non-ideal mixture equilibrates to the wrong quotient. *Route:* rates on
activities --- which redefines every rate constant's units, and is a distinct
project.

**No electrolyte activity model.** Ions sit at $\gamma = 1$ within a phase, so
ionic strength does not affect anything and salting-out does not exist.
Debye--Hückel or a UNIFAC extension is the fix. Note this is a *different* gap
from ion transfer between phases, which the Born term does cover (Chapter 10).

**No nucleation barrier or metastable zone.** Precipitation is ungated by design,
so a supersaturated solution crashes out instantly. No seeding, no supersaturation,
no oiling-out. Named as an engine gap.

**Rate laws are power-law mass action**, so Langmuir--Hinshelwood and
Michaelis--Menten have nowhere to live. The measured consequence: a solid
catalyst is strictly first order in catalyst amount for ever, so ten times the
iron is ten times the rate at any loading. Right at low coverage, wrong at high
(Chapter 18).

**Non-aqueous acidity.** The engine's pH floor is $-0.79$, set by the
concentration of water itself, and a real nitrating mixture needs about $-9.4$.
Fixing it means a Hammett acidity function $H_0$, not a parameter (Chapter 10).

**No melt phase.** A molten salt is not a phase this project has, which is why
two industrially important electrolysis cells cannot be expressed at all
regardless of their species.

**Energy is not conserved to an invariant.** There is no equivalent of
`conservation_report` for energy, and a leak is therefore invisible to the
instrument that exists to catch leaks (Chapter 27).

## Missing representations

**Polymers and extended solids need a different representation entirely** ---
chain-length *distributions*, not graphs. That is 12 routes in the corpus, and
the design has met the problem three times: bounded discovery, the lattice
question, and the coal/cellulose markers that have no molecular graph at all.

**No tautomer resolution.** Keto and enol forms are separate species.

**Stereochemistry is distinguished but not controlled.** A template rewrite can
scramble a centre.

**Joback gaps**: no anhydride, sulfoxide/sulfonyl, formamide or aryl-aldehyde
groups, and no metals, Si, B or P. Curated data covers the common reagents;
Benson is the general fix and it inherits the critical-property gap that Chapter
13's Wilson--Jasperson chain exists to close.

**A cell's two electrodes cannot be paired freely.** Each pairing is a separate
whole-cell template.

## Missing budgets

**Nothing budgets current.** Far above the decomposition potential every
electrode reaction runs out of barrier and the selectivity goes with it. A real
cell is transport-limited there; this one is not limited by anything.

**Nothing budgets surface area.** The shrinking-core law was refused for
numerical reasons (Chapter 21), so a crystal's reactivity does not fall as it is
consumed.

## The honest headline

::: {.keypoint}
**The mechanism is fully general; the library is not.** A player can mix two
arbitrary things and the machinery will discover what happens --- that is
architecture, and it works. What is short is *content*: 47 templates cover **59
of 240** reaction classes and 124 of 377 corpus steps, and closing the rest is a
~150-template grind with no bottleneck in it (Chapter 29).

That is a content problem, not a design one, and it is the correct kind of
problem to have after this much work.
:::

## And the sentence to keep

Everything in this chapter is *stated*. None of it is absorbed into a fudge
factor, and several items exist as printed refusals rather than as silent
approximations --- a species held at $\gamma = 1$ is named, a capped rate
constant is reported, a compilation-tier datum is stamped, an unbalanced catalog
row is counted.

::: {.keypoint}
That is the project's actual thesis, more than emergence is. A simulator's
numbers are only worth what its account of its own uncertainty is worth, and the
only defence against a confidently wrong number is to write down, beside every
choice, what was measured and what was refused.
:::

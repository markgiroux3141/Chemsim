# Water, ions, acids and bases

## Ions

An atom or molecule that has lost or gained electrons carries a net charge and
is called an **ion** --- Na⁺ (a sodium that lost one), Cl⁻ (a chlorine that
gained one), SO₄²⁻ (a whole polyatomic group carrying two extra electrons).

Ions exist in water because water is extremely polar: each molecule has a
partial negative charge on the oxygen and partial positives on the hydrogens, so
water molecules cluster around an ion with the appropriate end inward and
stabilise it enormously --- hundreds of kJ/mol. That energy is called
**solvation** or **hydration** energy, and it is the entire reason salt
dissolves and the entire reason it does not dissolve in oil.

::: {.physics}
Quantitatively, the leading term is just electrostatics in a dielectric. Charging
a sphere of radius $r$ carrying charge $ze$ inside a medium of relative
permittivity $\varepsilon$ costs (Born, 1920)

$$ G_{\mathrm{el}} = -\frac{N_A z^2 e^2}{8\pi\varepsilon_0 r}\left(1 - \frac1\varepsilon\right), $$

which is the self-energy of a charged sphere with the medium's screening in it.
Water has $\varepsilon \approx 78$; toluene has $\varepsilon \approx 2.4$. The
difference between those two is why an ion stays in the aqueous layer when you
shake a separating funnel.
:::

## Acids and bases

An **acid** is a proton donor; a **base** is a proton acceptor. In water:

$$ \mathrm{HA} + \mathrm{H_2O} \rightleftharpoons \mathrm{A^-} + \mathrm{H_3O^+} $$

The equilibrium constant of that reaction is the **acid dissociation constant**
$K_a$, and because it spans about twenty orders of magnitude it is always quoted
as $\mathrm{p}K_a = -\log_{10}K_a$. Small $\mathrm{p}K_a$ = strong acid.
Sulfuric acid's first proton is around $-3$; acetic acid is 4.76; water itself
is about 15.7.

**pH** is $-\log_{10}[\mathrm{H_3O^+}]$. Pure water at 298 K has
$[\mathrm{H_3O^+}] = 10^{-7}$ M, hence pH 7. Below 7 is acidic, above is basic.

::: {.keypoint title="There is no pH solver in this codebase, and there should not be one"}
Acid dissociation is *chemistry*, so it enters as ordinary reversible reactions:

$$ \mathrm{HA} + \mathrm{H_2O} \rightleftharpoons \mathrm{A^-} + \mathrm{H_3O^+},
\qquad 2\,\mathrm{H_2O} \rightleftharpoons \mathrm{H_3O^+} + \mathrm{OH^-} $$

and everything already built handles them. Detailed balance fixes each reverse
rate from the thermochemistry; the stiff integrator resolves the (very fast)
equilibrium; and the network builder's charge-balance check --- which has been
enforcing electroneutrality on every reaction since Layer 3 was written ---
finally earns its keep.

pH is then a *readout*, $-\log_{10}[\mathrm{H_3O^+}]$, not a state variable.
:::

The results, all emergent:

| result | chemsim | reference |
|---|---|---|
| pure water | pH 7.00 | 7.00 |
| 0.1 M acetic acid | pH 2.89 | 2.88 |
| half-neutralised | pH 4.76 | $=\mathrm{p}K_a$, exactly |
| equivalence point | pH 8.88 | basic, as acetate is a weak base |
| 0.05 M H₂SO₄ | pH 1.24 | ~1.1, with the correct HSO₄⁻/SO₄²⁻ split |

![A titration curve, which is what a stiff integrator does to two reversible reactions.\label{fig:titration}](figures/titration.pdf)

## Two decisions that make this work

**Write dissociation with water on both sides.** $\mathrm{HA} + \mathrm{H_2O}
\rightleftharpoons \mathrm{A^-} + \mathrm{H_3O^+}$ has $\Delta n = 0$, where the
more familiar $\mathrm{HA} \rightleftharpoons \mathrm{A^-} + \mathrm{H^+}$ has
$\Delta n = +1$. That matters more than it looks: a mole-changing reaction drags
in the activity-to-molarity standard-state conversion (Chapter 4), and this
project's formation data is ideal-gas while aqueous ion data is on the molarity
scale. Writing it the balanced way makes the conversion **cancel exactly**, so
the two unit systems never have to be reconciled.

**Derive ion formation data from pKa, against this project's own water entry.**
Rather than importing tabulated aqueous ion values --- which are referenced to
liquid water and would silently disagree with our ideal-gas water --- each ion's
Gibbs energy is back-calculated so the measured pKa comes out right *with the
water value this project already uses*:

$$ \Delta G_{\mathrm{rxn}} = 2.303\,RT\,\mathrm{p}K_a,
\qquad \Delta G_f(\mathrm{A^-}) = \Delta G_f(\mathrm{HA}) + \Delta G_{\mathrm{rxn}}, $$

with the convention $\Delta G_f(\mathrm{H_3O^+}) = \Delta G_f(\mathrm{H_2O})$,
i.e. the proton is the zero. The resulting numbers are not literature aqueous
values and are not labelled as such. They are internally consistent constants
that reproduce measured acidity.

::: {.trap title="Two different zeros, three decades apart, that must never be subtracted"}
This project now has **two** ion tables on **two** different conventions, and
the distinction is load-bearing:

- `properties/electrolyte.py` back-calculates each ion from a measured pKa
  against this project's water, with $\Delta G_f(\mathrm{H_3O^+}) =
  \Delta G_f(\mathrm{H_2O},\ell)$. Right basis for a **proton transfer**.
  Chloride reads $-111.73$ kJ/mol.
- `properties/ion_data.py` is the conventional aqueous scale, anchored on
  $\Delta G_f(\mathrm{H^+},\mathrm{aq}) = 0$. Right basis for a **lattice
  subtraction**. Chloride reads $-131.20$ kJ/mol.

Neither number is wrong. Mixing them costs **3.4 decades of $K_{\mathrm{sp}}$**.
There is no import between the two modules and there should not be one.
:::

::: {.trap title="The anchor was the acid, and four rows of the table are cations"}
`electrolyte.py` anchored each ion on its *acid*, unconditionally. But four rows
of the pKa table are **cation/neutral** pairs whose acid *is* the ion --- an
anilinium ion, for example --- and the ordinary providers refuse to price a
charge. Those four rows were dead.

The rule is now: a neutral acid anchors its anion, a neutral base anchors its
cation, and the second is the first read backwards. And the neutral member must
be taken in its **liquid** standard state, because a pKa is a solution-phase
measurement --- skip that and every pKa moves by about three units.
:::

## An ion in a two-phase system: the Born term

Everything above is inside one liquid. Across a **liquid--liquid interface**,
$\gamma = 1$ for ions is not a bounded error: equality of activity with
$\gamma = 1$ on both sides means an ion partitions to *equal mole fraction*
between water and toluene. So the project's phase-splitting code refused to split
any electrolyte at all, and the most common workup in preparative chemistry ---
acidify, extract, wash the organic layer --- was not expressible.

::: {.keypoint title="Two ionic gaps, and only one of them is this one"}
- **(a) ionic strength *within* one phase** --- Debye--Hückel / Davies. It is
  what makes a concentrated brine's ions less active than its concentration
  says, and it is what salting-out is. **Not modelled here.**
- **(b) ion transfer *between* phases** --- **Born**. The electrostatic cost of
  moving a charge out of a high-dielectric medium into a low one. That is what
  holds an ion in the aqueous layer, and it is what
  `properties/dielectric.py` computes.

Conflating the two wastes the work, and the project says so at the top of the
module.
:::

Only *differences* of the Born energy are used. An ion's reference state here is
infinite dilution in water, so the quantity wanted is the transfer:

$$ \ln\gamma_i(\text{phase}) = \frac{A_i}{RT}
   \left(\frac{1}{\varepsilon_{\text{phase}}} - \frac{1}{\varepsilon_{\text{water}}(T)}\right),
   \qquad A_i = \frac{N_A z_i^2 e^2}{8\pi\varepsilon_0 r_i}. $$

**In water this is exactly zero, at every temperature, by construction.** That
is why it is written as a transfer rather than as a solvation energy, and it is
what makes the existing pH invariants safe --- the anchors were derived at
$\gamma = 1$ against water, and in water $\gamma$ is still exactly 1. (Every pKa
in the table was re-measured afterwards anyway, because "safe by construction" is
a claim and not a check.)

::: {.aside title="A permittivity is a mixture property, so it cannot fully collapse"}
$\varepsilon_{\text{phase}}$ depends on composition, so the Born term lands in
the same place UNIFAC did. The project's standard question --- *what uniform
array form does this collapse to?* --- has a clean answer: an $(n,4)$ block that
is a function of temperature alone, $[A_i \mid \varepsilon_{\mathrm{pure},i}(T)
\mid v_i(T) \mid \varepsilon_{\mathrm{water}}(T)]$. Three of those four columns
already existed; the only thing left in the hot loop is the mixing rule, which is
three array operations. The kernel still evaluates one polynomial form and has
never heard the word "Born".

The mixing rule is Oster's (1946), Onsager's theory applied to a mixture:
$f(\varepsilon) = \sum_i \phi_i f(\varepsilon_i)$ with
$f(e) = (e-1)(2e+1)/9e$ and $\phi$ the **volume** fractions --- permittivity is
a bulk polarisation property, so volume is the right weighting.
:::

::: {.trap title="An unclipped gamma reports SUCCESS with a 1e9 mol dipole"}
The Born exponential is unbounded. An ion in a very low-dielectric phase gets an
enormous positive $\ln\gamma$, and the transfer term then drives a quantity that
should be zero to something like $10^9$ mol --- a number with no physical
referent at all, produced by a run that reports success. The fix is a ceiling on
the exponent, justified as a resolution limit rather than as physics, and stated
as such.
:::

## What protonation buys, and what it cannot fix

Milestone G5 added the ability for a molecule's *protonated form* to be a
distinct species with its own reactivity --- an aniline that becomes an anilinium
ion in acid, and stops being nucleophilic. It is the right model, and it is
honest about its own limit:

::: {.trap title="The engine's pH floor is -0.79 and the crossover it needed is -9.42"}
The anilinium split is the correct chemistry, and it **cannot** fix aniline. The
crossover pH at which the split matters is $-9.42$; the engine's floor, set by
the concentration of water itself, is $-0.79$. Real nitrating mixtures are
*drier* than water --- and a drier acid is a **less** acidic pot on this model,
because the model's acidity is mediated by hydronium and there is not enough
water to make it. The gap is a missing model of non-aqueous acidity (the Hammett
acidity function $H_0$), not a missing parameter.

Reporting a bound like that, rather than fudging a constant until aniline
behaves, is the project's standard.
:::

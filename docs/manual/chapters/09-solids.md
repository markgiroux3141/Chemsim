# Solids: melting, dissolving, and the law that is wrong for salt

## One equation for two phenomena

Consider a solid in contact with a liquid. Equilibrium requires the solid's
chemical potential to equal that of the same substance dissolved in the liquid.
Working that out with an ideal solution and constant enthalpy of fusion gives

$$ \boxed{\ \ln a_{\mathrm{sat}} = -\frac{\Delta H_{\mathrm{fus}}}{R}
   \left(\frac{1}{T} - \frac{1}{T_m}\right)\ } $$

where $\Delta H_{\mathrm{fus}}$ is the enthalpy of fusion (the heat needed to
melt it) and $T_m$ the melting point.

Look at what happens at $T = T_m$: the right-hand side is zero, so
$a_{\mathrm{sat}} = 1$ --- the solid becomes fully miscible with its own melt.

::: {.keypoint title="So there is no separate melting model"}
Melting and dissolving are the same equation evaluated at different
temperatures. That is why melting shows a latent-heat plateau in this simulator
for exactly the reason boiling does (Chapter 7), and why nothing in the code
contains a melting point either. $\Delta H_{\mathrm{fus}}$ and $T_m$ come from
group contributions or a curated table.
:::

## Melting and dissolving had to be separated after all

The equation above is written in **activity**, not mole fraction, and that
distinction was a bug for a while. Written in $x$ it was right for melting and
badly wrong for dissolution. Written in $a$:

- **dissolution** divides by the activity coefficient,
  $x_{\mathrm{sat}} = a_{\mathrm{sat}}/\gamma$, so a solute that a solvent
  dislikes ($\gamma \gg 1$) dissolves far less;
- **melting** does not divide, because a pure solid in equilibrium with its own
  melt must not care how badly some solvent dissolves it.

The difference is enormous. Benzoic acid in water at 298 K:

![The same law, with and without one factor.\label{fig:solub}](figures/solubility.pdf)

| | value |
|---|---:|
| ideal law, $\gamma = 1$ | 1347 g/L |
| with UNIFAC $\gamma$ | 3.24 g/L |
| measured | 3.44 g/L |

Both curves in Figure \ref{fig:solub} are engine output and differ by exactly
one factor.

::: {.aside title="An honest limitation, stated where it was measured"}
UNIFAC understates how fast an associating solute's solubility climbs with
temperature. Benzoic acid in water comes out at 0.95$\times$ the measured value
at 298 K but 0.48$\times$ at 333 K --- the absolute scale is right and the slope
is not. You can see it in Figure \ref{fig:solub}: the blue curve passes through
the low-temperature squares and falls under the high-temperature ones. The
project reports this rather than tuning it away.
:::

## Crystallisation is a rate, not an event

A solute above its solubility limit crystallises out. In the RHS that is a
transport term next to evaporation: a driving force
$(x_{\mathrm{sat}} - x)$ times a rate constant, with the sign deciding whether
crystals grow or dissolve. Growth from a supersaturated solution and dissolution
of an existing crop are the *same term* running in two directions.

Cooling a solution therefore crops it, with no declaration anywhere:

| $T$ / K | benzoic acid dissolved | as solid |
|---:|---:|---:|
| 330.0 | 0.050000 | 0.000000 |
| 298.1 | 0.026681 | 0.023319 |
| 275.0 | 0.012236 | 0.037764 |

::: {.trap title="There is no nucleation barrier, and that is a real gap"}
Real solutions can be *supersaturated*: they hold more than the equilibrium
amount because starting a crystal is harder than growing one. Real chemists
exploit this constantly --- you cool slowly to get big pure crystals, you seed,
you scratch the glass.

Here, precipitation is ungated by design: "anything can nucleate", so a
supersaturated solution crashes out immediately. A metastable solution that
would not crop at the bench will crop here. `NUCLEATION` is a named engine gap
in the project's own notes, arrived at in milestone S3.
:::

## Filtration and where yield actually goes

Once solids exist you can filter them, and this is where a simulator can either
be honest or quietly generous. The project's rule is stated as a principle:

::: {.keypoint}
**A loss must be a mechanic, never a tax.** A yield loss has to come from
something the model does, so that a player can act on it --- not from a
multiplier applied at the end.
:::

Applied to the benzoic-acid preparation, that rule produced three findings, two
of which were *refusals*:

- **the crystal crust is real and it is worth 9 points of yield.** Mother liquor
  clings to the crystal surface; it is a genuine holdup, and modelling it takes
  the preparation from 93% to 84%. Kept.
- **film holdup on the glassware is worth nothing here.** Measured, then
  dropped.
- **crystal occlusion --- solvent trapped inside growing crystals --- was killed
  by arithmetic before it was built.** Somebody sampled the trajectory, worked
  out the size of the effect, found it negligible at these crystal growth rates,
  and did not write the code.

That last one is the project's habit at its best: *sample the trajectory before
implementing the term*, which is the same discipline that shaped the `wait_until`
vocabulary in Chapter 23.

## Ionic solids, and the law that does not apply to them

Now the hard part. Table salt is not a molecule. It is a **lattice**: a repeating
three-dimensional array of Na⁺ and Cl⁻ ions held together electrostatically. It
has no molecular graph in any useful sense --- `[Na+].[Cl-]` is a formula, not a
structure.

And the fusion law does not describe it dissolving. Applied to an ionic lattice
it is wrong by up to three orders of magnitude **in both directions**, measured
against tabulated 298 K solubilities:

| salt | error |
|---|---|
| NaCl | 407$\times$ too **insoluble** |
| K₂CO₃ | 585$\times$ too insoluble |
| Na₂CO₃ | 251$\times$ too insoluble |
| KNO₃ | 2.6$\times$ too **soluble** |
| CaCO₃ | 11$\times$ too soluble |

::: {.keypoint title="6,400x of spread with the sign flipping is not a bias, it is the wrong law"}
$T_m$ and $\Delta H_{\mathrm{fus}}$ describe lattice $\to$ **melt**. Dissolution
is lattice $\to$ **hydrated ions**, and the hydration energy --- which is
enormous, hundreds of kJ/mol --- appears in neither quantity.

So `properties/thermochemistry.py` **refuses a lattice SMILES by name** rather
than handing it to a law that is measurably wrong, and `mineral_data.py` is
reference data rather than a provider tier. What a mineral in a flask actually
*is*, is its ions, and that already works.
:::

## The solubility product

The right law for a lattice dissolving is a **solubility product**. For
$\mathrm{M}_a\mathrm{X}_b(s) \rightleftharpoons a\,\mathrm{M}^+ + b\,\mathrm{X}^-$:

$$ \Delta G_{\mathrm{diss}} = a\,\Delta G_f(\mathrm{M}^+) + b\,\Delta G_f(\mathrm{X}^-)
   - \Delta G_f(\text{solid}), \qquad K_{\mathrm{sp}} = e^{-\Delta G_{\mathrm{diss}}/RT}. $$

Both halves are formation values from the elements, so **the subtraction means
something only if both are on the same basis**. That sentence is the entire
history of `properties/solubility_product.py` and it produced two of the
project's most instructive findings.

::: {.trap title="A zero is not data; it is an assertion about the consumers"}
Before this module, the only ion values in the project were "spectator zeros" ---
$\Delta G_f(\mathrm{Na^+}) = 0$, on the reasoning that a spectator ion cancels
out of every equilibrium. Measured over 13 minerals, a naive $K_{\mathrm{sp}}$
built on those zeros returned a float for nine of them and was **25--29 decades
out with the sign flipping**; blue vitriol came out at 76 mol/L, denser than the
crystal.

The cause is exact and worth carrying: *a spectator cancels from an equilibrium
only when it appears on both sides.* Every proton transfer has the cation
unchanged across the arrow, which is why $\mathrm{[Na^+]} = 0.0$ is exactly
right there and why the project's five pH invariants hold. A solubility product
is the one consumer where it appears **once**, so the entire hydration Gibbs
energy that the zero stands in for lands in $\Delta G_{\mathrm{diss}}$ --- about
262 kJ/mol for sodium, which is 46 decades.
:::

::: {.trap title="A refusal from an API is not evidence that the data is absent"}
The first measurement also recorded that the fix could not be automated, because
the `chemicals` package "has no aqueous ion values and hands back the gas-phase
ion" --- and that was *measured*: `Hfs`, `S0s` and `Hfl` are all `None` for Na⁺,
and `Hfg` is $+609{,}343$ J/mol.

**That was true of the functions and false of the package.** `chemicals` 1.5.2
ships a file, *CRC Thermodynamic Properties of Aqueous Ions*, with 173 ions on
the conventional scale --- and no accessor function reads it. It is now
`properties/ion_data.py`, 58 ions, each cross-checked by re-deriving its
$\Delta G_f$ from its own $\Delta H_f$ and $S(\mathrm{aq})$ against the element
reference states, worst residual 0.85 kJ/mol against a tolerance of 1.0.

This is the exact mirror image of the project's older rule that *a successful
call can be a wrong answer*, and it cost a milestone's worth of planning.
:::

## Reactions inside and at the surface of a crystal

A crystal can react while staying a crystal --- a lime kiln,
$\mathrm{CaCO_3(s)} \to \mathrm{CaO(s)} + \mathrm{CO_2(g)}$, is matter changing
identity without leaving the solid phase. Chapter 21 covers how that is
represented; the chemistry to know now is one fact:

**A pure solid has unit activity.** It does not appear in the equilibrium
expression at all. So calcite and quicklime sitting together fix
$p_{\mathrm{CO_2}}$ at $K(T)$ regardless of how much of each is present.

![Engine data. The kiln has a threshold, and forward-only chemistry deletes it.\label{fig:lime}](figures/lime.pdf)

That is why a real kiln has a threshold temperature (Figure \ref{fig:lime},
left: about 1120 K under 1 bar of air on the engine's own curated data) and why
sweeping the CO₂ away makes it go at lower temperature. The right-hand panel is
the measured consequence of getting this wrong: a forward-only model calcines
completely at any temperature you are willing to wait at, which deletes the
kiln's entire mechanic.

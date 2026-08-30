# Layer 1: how a property actually resolves

Part II covered the estimation *methods*. This chapter is about the plumbing:
what happens when something upstream asks for a number, and what the layer emits.

## The providers

Layer 1 exposes a handful of provider objects, each of which answers one
question about one species and stamps its answer with a source.

| provider | answers | file |
|---|---|---|
| `ThermochemistryProvider` | $\Delta H_f$, $\Delta G_f$, $S^\circ$, $C_p(T)$, $T_b$, $T_m$, $T_c$, $P_c$, $V_c$, $\Delta H_{\mathrm{fus}}$, $\Delta H_{\mathrm{vap}}$ | `thermochemistry.py` |
| `VolatilityProvider` | Antoine $(A,B,C)$, and whether it is a vapour pressure or a Henry constant | `volatility.py` |
| `CondensedProvider` | liquid molar volume, liquid $C_p$, as cubics in $T$ | `condensed.py` |
| `UnifacProvider` | group decomposition, $R_k$, $Q_k$, the interaction matrix | `unifac.py` |
| `DielectricProvider` | permittivity, Born radii | `dielectric.py` |
| electrolyte provider | pKa-anchored ion formation data and the dissociation templates | `electrolyte.py` |

Everything is keyed by **canonical SMILES**, which is the only identity in the
system --- and canonical SMILES is *isomeric*, so a spelling is part of the key.

::: {.trap title="A spelling used to select a data tier"}
Exactly one property table carries stereochemistry in its keys: the **generated**
one, `MEASURED_PHYSICAL`, which inherited the corpus's spelling when it was built
from the corpus. Every hand-typed table is flat, because a human types the simple
form --- 0 of 82 ideal-gas formation entries, 0 of 58 liquid, 0 of 50 curated
records, 0 of 29 pKa rows. For 49 of the 212 corpus compounds spelled with
stereochemistry that meant the two spellings of one substance resolved to
*different sources*, and for lactic acid it meant neither spelling reached the
best available record for both halves at once.

`properties/stereo_keys.py` lets a lookup cross that, under two limits that are
the whole of its safety. It may cross an **ambiguity** and never a
**difference**: a query naming no stereochemistry may take a record that names
some, and a query naming some may take a flat record, but two differently
specified spellings never share one --- those are two species. And the
unspecified side must be answered by **exactly one** record. That second guard
fires: `MEASURED_PHYSICAL` holds seven skeletons with more than one stereoisomer,
and without it a flat butenedioic acid would take maleic or fumaric acid's
boiling point depending on dictionary order --- **230 K apart**. Every value that
arrives this way says so in its provenance string.
:::

## Resolution order

`ThermochemistryProvider.get(smiles)` walks a tier list:

1. is it an **element**? Then `element_data` or refuse by name. No estimator may
   price a reference state (Chapter 3).
2. is it an **ionic lattice**? Then `mineral_data` --- and note that this
   *prices* it without making it *dissolvable*, because the fusion law is the
   wrong law for a lattice (Chapter 9).
3. is there a **curated measured record**? Use it.
4. can **Benson** fragment it? Use Benson for the formation half.
5. can **Joback** fragment it? Use Joback.
6. otherwise **refuse**, with a reason.

The physical half resolves on its own track --- measured $T_b$ where one exists,
then Wilson--Jasperson and Fedors for the critical constants --- which is why
the coverage report has two independent columns and why a species can be
Benson-priced and physically refused, or vice versa.

::: {.keypoint title="Refusing to dissolve is not refusing to price"}
This distinction was worth 16 routes and it was found by an audit rather than by
a failure. `species-ready` --- the coverage instrument's question "does every
species in this route resolve?" --- was asking only the three ideal-gas
providers, which refuse an ionic lattice **by name and correctly**.

But `mineral_data` had been pricing those lattices on the solid basis since
milestone M3. Nineteen compounds moved from *refused* to *mineral*, and sixteen
routes with them --- including the lime cycle, which the project had already
declared complete end to end and whose example ran. **The audit was measuring
the wrong provider set, and the number it produced was wrong in the safe
direction, which is why nobody noticed.**
:::

## What the layer emits, and why it is polynomials

Nothing upstream ever sees a correlation. Layer 5 assembles `PhaseArrays` by
asking each provider for each species and packing the answers into numpy:

```
Antoine (A, B, C)          one row per species    -> p_eq = x * gamma * 10^(A - B/(C+T))
Cp_liq, Cp_gas             cubic coefficients     -> Cp = a + bT + cT^2 + dT^3
v_liq                      cubic coefficients     -> liquid volume, hence concentration
Hfus, Tm                   scalars                -> the fusion law
latent heat                cubic                  -> the energy balance's q_vap
UNIFAC nu, R_k, Q_k, a_mn  matrices               -> gamma, evaluated in the RHS
Born A_i, eps_i(T)         (n,4) block            -> ion transfer between layers
```

Anything non-polynomial --- a corresponding-states correlation, in both the
Rackett and Rowlinson--Bondi cases --- is **sampled and fitted at setup**. That
is not cosmetic. It means Layer 4 evaluates one polynomial kernel over one array
and never learns that Rackett exists.

## Two properties Layer 5 could not do without

`condensed.py` exists for two reasons that are easy to overlook:

- **liquid molar volume**, because the liquid volume is what turns moles into
  the concentrations the rate law uses --- *and what lets a flask boil dry*;
- **liquid heat capacity**, because a vessel's temperature response is set by
  the liquid it contains, and ideal-gas $C_p$ is roughly half the real value.

Estimation quality is stated honestly rather than assumed: Rackett is good to a
few percent for most organics and about 10% low for water, which is anomalous;
Rowlinson--Bondi is good (~5%) for non-polar species and poor for
hydrogen-bonding ones, overestimating ethanol by ~40%. Since alcohols, water and
acids are exactly the solvents this simulator cares about, those are curated and
the correlation is the fallback for everything else.

## A layering cycle, and how it was broken

A small but instructive piece of structure. `volatility` builds a provider and
therefore imports `thermochemistry`. But `thermochemistry` needs an enthalpy of
vaporisation for a record it assembles from *estimated* critical constants, and
deriving that from Lee--Kesler would import `volatility` straight back.

The fix was to put the Lee--Kesler shape functions in `critical.py`, a module
that depends on nothing but `matter`. That breaks the cycle --- and it is where
they belong anyway: they are a property *model*, not a *provider*. `volatility`
re-exports them so its public surface is unchanged.

::: {.aside}
This is a general pattern worth naming: when two modules need each other, the
thing they both need is usually a third, more primitive thing that has been
misfiled inside one of them.
:::

## The report

Every provider can say what it did not know. `vessel.activity_model.report()`
names the species held at $\gamma = 1$ and the main-group pairs missing from the
published matrix; `electrolyte_report()` names ions with no data;
`integrability_report()` names species that will make the solver unhappy.

Those strings are surfaced in the user interface rather than logged (Chapter 24),
on the reasoning that "nothing is silently approximated" is only worth anything
if somebody is shown what it said.

::: {.trap title="A channel that was reported all along and that nothing read"}
The refluxing rig destroyed 0.34 mol of its air for months. The loss was
reported by `conservation_report` the whole time. Nothing was reading it.

That is why the reports panel exists in the UI, and why several validation
scripts now assert on report contents rather than merely printing them.
:::

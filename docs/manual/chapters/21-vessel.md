# Layer 5: the vessel, term by term

This is where the simulation stops being a reaction and starts being an
*experiment*. It is also the largest single piece of physics in the project ---
`numerics/vessel_integrator.py` is 3,100 lines --- so this chapter goes through
it term by term.

## The state vector

$$ \mathbf y = \big[\ \underbrace{n_{L1}}_{n}\ \big|\ \underbrace{n_{L2}}_{n}\ \big|\
   \underbrace{n_{G}}_{n}\ \big|\ \underbrace{n_{S}}_{n}\ \big|\ T\ \big],
   \qquad \text{length } 4n+1. $$

Four blocks --- two liquid layers, the headspace, and the solid --- plus one
temperature, solved as **one stiff system**.

::: {.keypoint title="Moles, not concentrations, and one system rather than several"}
**Moles**, because concentration needs a volume and the liquid volume is itself
a state-dependent quantity that shrinks as things boil off or crystallise out.
Moles stay meaningful when the flask boils dry.

**One system**, because the feedback loops are the entire point and
operator-splitting them across separately-stepped subsystems would smear them
and make the answer depend on the stepping interval:

- an exothermic reaction heats the vessel;
- the higher temperature accelerates it (Arrhenius) *but also lowers its
  equilibrium constant* (detailed balance);
- heating raises the vapour pressure, so the solvent evaporates and latent heat
  pulls the temperature back down;
- it also raises solubility, so a product that had crystallised redissolves.

None of that is scripted. It is four terms in one right-hand side and a solver.
:::

## Where matter can go

![The four blocks and every path between them.\label{fig:phases}](figures/phases.pdf)

Reaction runs in liquid 1, in liquid 2, in the headspace, inside a crystal, and
at a crystal's surface. Transport moves matter between blocks without changing
its identity, which is why element conservation is exact across all four.

## The terms

Here is the RHS assembly, essentially verbatim from the source:

```python
return np.concatenate([
    dn_rxn1 - evap1 - evap_dry + solute1 - lle - precipitate,   # liquid 1
    dn_rxn2 - evap2              + solute2 + lle,               # liquid 2
    dn_gas_rxn + dn_gas_srxn + dn_gas_surf + evap - vent + ingress,   # vapour
    -solute + precipitate + dn_solid_rxn + dn_solid_surf,       # solid
    [dT],
])
```

Term by term:

**`dn_rxn`** --- mass action in each liquid layer and in the gas, at that
block's concentrations. Layer 2's contribution is multiplied by a gate that is
zero when the second layer is empty.

**`evap`** --- the phase-change flux, and it is one expression doing two jobs:

$$ \dot n_i^{\text{evap}} = k_{la}\,\big(a_i\,P^{\mathrm{sat}}_i(T) - p_i\big),
   \qquad a_i = x_i\gamma_i. $$

Positive means evaporating, negative means condensing. **Nothing in the code
knows what a condenser is**: vapour arriving in a cold vessel finds
$p > p_{\mathrm{eq}}$ at that temperature, so this term runs backwards, the
latent heat term changes sign and *releases* heat, and a thermal edge carries it
to the coolant. That is Chapter 22's entire content.

**`solute`** --- dissolution and crystallisation, driven by
$(x_{\mathrm{sat}}\,N - n_L)$ with $x_{\mathrm{sat}}$ from the fusion law divided
by $\gamma$ (Chapter 9). One term, two directions.

**`precipitate`** --- ionic precipitation against a solubility product. A
separate term from `solute` because a lattice is not priced by the fusion law
and its ions are not priced on the same basis (Chapter 9).

**`lle`** --- transfer between the two liquid layers, driving
$\gamma_i^{\mathrm I}x_i^{\mathrm I} - \gamma_i^{\mathrm{II}}x_i^{\mathrm{II}}$
toward zero. The *decision* that a second layer should exist is made outside the
RHS.

**`vent`** --- gas leaving when $P > P_{\mathrm{ambient}}$, carrying the
headspace composition, with backflow from the room when the pressure drops.

**`ingress`** --- the leaky-flask boundary flux. Contamination as a term rather
than as a special case.

**`dn_solid_rxn`, `dn_gas_srxn`** --- a reaction happening *inside* a crystal.

**`dn_solid_surf`, `dn_gas_surf`** --- a gas reacting *at* a crystal's surface.

Those last two are separate, and the reason is instructive enough to have its
own section below.

## The energy balance

$$ \frac{\dd T}{\dd t} = \frac{q_{\mathrm{rxn}} + q_{\mathrm{vap}} +
  q_{\mathrm{fus}} + q_{\mathrm{solid}} + q_{\mathrm{surf}} + q_{\mathrm{loss}}
  + q_{\mathrm{vent}} + Q_{\mathrm{input}}}{C_{p,\mathrm{total}}} $$

with

$$ C_{p,\mathrm{total}} = C_{p,\mathrm{vessel}} + (n_{L1}+n_{L2}+n_S)\cdot C_{p,\ell}(T)
   + n_G\cdot C_{p,g}(T), $$
$$ q_{\mathrm{loss}} = -UA\,(T - T_{\mathrm{env}}), \qquad
   q_{\mathrm{vap}} = -\dot{\mathbf n}^{\text{evap}}\cdot \Delta H_{\mathrm{vap}}(T). $$

Every mechanic in Chapter 7 is in those two lines. The plateau is
$q_{\mathrm{vap}}$ growing until it cancels $Q_{\mathrm{input}}$; the dryout
superheat is $q_{\mathrm{vap}}$ going to zero when there is nothing left to
evaporate; the flask that boils dry and then *stops* climbing is
$q_{\mathrm{loss}}$ catching up.

::: {.aside title="Crossing between liquid layers is athermal, deliberately"}
This project models no excess enthalpy of mixing anywhere --- the energy balance
is a sum of pure-component heat capacities --- so charging a heat of mixing to
this one transfer would be the only place it existed, and would disagree with the
enthalpy every other transfer carries. Consistency beats a partial improvement.
:::

## The gates, and a bug that created matter

Several terms have to switch off smoothly as a phase disappears. Doing that
badly is how you manufacture matter, and this project did.

::: {.trap title="Three overlapping gates on one scale, and a flask reporting 111% yield"}
The dryout gate was written as a ramp, $w = N/(N + \varepsilon)$, which is
non-zero for **every** $N > 0$. So layer 1's evaporation at strength $w$ and the
dry-flask branch at strength $1-w$ were **both live** inside the band. Worse,
mole fractions were floored on the *same* scale, $x = n_L/\max(N,\varepsilon)$,
so inside the band they summed to **less than one** --- 0.57 at
$N = 5.7\times10^{-7}$ --- and every activity was understated as well.

Measured on a sulfur burner, which walks into this because sulfur boils at 717.8 K
and a burn near that holds only a trace of condensate:

| $T$ / K | liquid held / mol | oxygen created, relative |
|---:|---:|---:|
| 550 | $6.85\times10^{-3}$ | $1.8\times10^{-12}$ |
| 650 | $1.52\times10^{-3}$ | $1.1\times10^{-9}$ |
| 675 | $8.29\times10^{-7}$ *(in band)* | $2.3\times10^{-3}$ |
| 690 | $5.43\times10^{-7}$ *(in band)* | **$1.1\times10^{-1}$ --- reads 111% yield** |

Three things came out of the fix and all three are general:

1. **The bug was the $0/0$ clamp sharing the gate's scale.** Two different
   guards, one constant.
2. **Disjoint gates are wrong here.** The obvious fix --- make the two branches
   never overlap --- creates a *dead zone* in which neither runs, and a dead zone
   stalls a condenser.
3. **A green test suite is no evidence the invariants table holds.** The suite
   passed throughout.
:::

The scale that survived is $10^{-6}$ mol --- 18 µg of water, far below anything a
bench would call a pool, and *three decades above the solver's own $10^{-9}$
atol*, which is the gap that makes the transition resolvable at all. A constant's
**units** are what make its value defensible.

::: {.keypoint title="With the second liquid block empty, every term reduces EXACTLY to the one-liquid RHS"}
Not approximately --- term by term. `gate2` is zero, layer 2's volume is below
the minimum so no reaction runs in it, its dissolution pool is zero, and the
liquid--liquid flux carries the product of both gates.

That is deliberate and load-bearing: it is what lets a vessel that never splits
reproduce every number the project has ever measured, so **a moved invariant
means a real phase split and never an accounting change.**
:::

## A reaction inside a crystal

$\mathrm{CaCO_3(s)} \to \mathrm{CaO(s)} + \mathrm{CO_2(g)}$ is a lime kiln, and
it is the first reaction in this project that neither the liquid block nor the
gas block could write. Not a liquid-phase reaction, not a gas-phase one, and not
a transport term either: **matter changes identity while staying a solid.**

The question was whether to add a third `PHASE_INDEX` entry or write a term. It
was decided by arithmetic.

A pure solid has **unit activity**, so its equilibrium is a statement about the
gas *alone*. Write the pair as mass action on the solid amounts and you get

$$ k_f\,n(\mathrm{CaCO_3}) = k_r\,n(\mathrm{CaO})\,p_{\mathrm{CO_2}}
   \quad\Longrightarrow\quad
   p_{\mathrm{CO_2}} = \frac{k_f}{k_r}\cdot\frac{n_A}{n_B} $$

which sweeps from infinity to zero as the charge converts. **That is not a
perturbation of the right answer, it is a different shape of answer**: real
calcite either decomposes completely ($p < K$) or not at all ($p > K$), and the
mass-action form always stops somewhere in between.

And forward-only is not a way out, as Figure \ref{fig:lime} showed. So the form
used is an **affinity**:

$$ \text{flux} = k(T)\left[\ \text{units}_{\mathrm{fwd}}
   - \text{units}_{\mathrm{rev}}\,e^{\,\ln Q - \ln K}\ \right]\ \text{mol/s} $$

with $\ln Q$ summed over the *gas* participants only (solids contribute 1) and
$\ln K$ from van 't Hoff.

## A gas arriving at a crystal's surface

$2\,\mathrm{ZnS(s)} + 3\,\mathrm{O_2(g)} \to 2\,\mathrm{ZnO(s)} +
2\,\mathrm{SO_2(g)}$ is a roaster, and it is a *different* term.

::: {.keypoint title="The line that holds is REVERSIBLE OR NOT"}
The affinity form is only a rate law while every gas participant is a
**product**. Put a gas on the reactant side and its pressure lands in the
*denominator* of $Q$, so an atmosphere depleted of it drives the reverse flux
without bound --- measured on a roasting declaration at
$2.6\times10^{15}$ formula units per second as $p_{\mathrm{O_2}}\to 0$.

So the two solid tables split on a rule the project already had:

- **reversible, exponents forced** by detailed balance $\to$ `solid_state.py`;
- **irreversible, orders declarable** $\to$ `surface.py`.

which is the standing invariant *a declared rate order may never be reversible*,
arriving as a module boundary.
:::

The surface form is mass action, and its **basis is mixed**, which is the one
thing that module must get right:

$$ \text{rate} = k(T)\prod_{\text{solid}} n_{S,i}^{\alpha_i}
   \prod_{\text{gas}} C_i^{\alpha_i}\quad [\text{mol/s}] $$

- **a solid's "concentration" has no referent.** The solid block is an inventory
  in mol and its nominal volume is a convention. $n_S/V$ would be a number
  divided by a convention.
- **a gas's amount is not what a surface sees.** The flux of molecules onto a
  crystal face goes with the collision rate, i.e. with **concentration**.
  Written on $n_G$ instead, compressing the flask would not speed the reaction
  up --- and a roaster is a machine for blowing air through a bed.

So the rate is *extensive* in the solid and *intensive* in the gas, and one
consequence is a mechanic: with order 1 in the solid,
$\tau = n/\text{rate} = 1/(k\,C_{\mathrm{gas}})$ does **not** depend on how much
ore is charged. Doubling the bed doubles the throughput and does not change the
time.

::: {.aside title="A physically better law, refused"}
$n_S^{2/3}$ --- the shrinking-core law, which accounts for a crystal's surface
area falling as it is consumed --- is physically better and is **refused**,
because its slope at $n_S \to 0$ is infinite and that makes the solver's life
impossible near the end of a burn. The refusal is recorded with the constant
that would have been needed.
:::

## Two things that emerged from putting those two terms in the same flask

::: {.keypoint title="A route nobody declared"}
Ore + coke + air $\to$ metal. Neither term declares that reaction. One term
burns the coke to carbon monoxide; the other reduces the ore with it. Charge all
three into one vessel and a *smelter* emerges from two independent declarations
--- and the project's coverage audit credited a catalog route that nothing in
the code had ever named.

That is the strongest single piece of evidence for the emergent-design thesis in
the repository.
:::

And an equally instructive negative: a carrier-free lead chamber is now **inert**
--- both walls it found are closed --- and a zinc retort evolves zinc *vapour*
and condenses it in a cool receiver at 1180.15 K, which is a real Belgian
retort's actual mechanic, **with no engine code changed at all.** What changed
was one data entry: zinc moved out of the lattice table (where it could react and
never boil) into the element table (where it can).

::: {.trap title="\"A lattice may never boil\" was a statement about an ENTRY"}
That sentence had been recorded as a fact about metals. It is a fact about how
the *record* was filed. Zinc has a monatomic vapour, one condensed form and a
measured sublimation curve, so it passes every test mercury was admitted on.
Moving it took a route from thermodynamically-correct-but-static to a working
distillation, for +0 on every coverage column and zero lines of engine code.
:::

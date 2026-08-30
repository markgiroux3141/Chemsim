# Rigs: glassware as a graph

## A vessel that can only see the room cannot reflux

Every piece of glassware that matters --- condenser, still head, rotovap,
Dean--Stark trap, dropping funnel, cold trap --- is **two containers with
something flowing between them**, and the flow is what the apparatus is *for*.

::: {.keypoint title="The physics a condenser needs was already written"}
Vapour arriving in a cold vessel finds $p > p_{\mathrm{eq}}$ at that
temperature, so the existing evaporation term runs backwards, $q_{\mathrm{vap}}$
changes sign and **releases** latent heat, and a thermal edge carries it to the
coolant.

Nothing in `vessel_integrator` had to learn about condensers. What was missing
was only a way for two vessels to see each other.
:::

So `Rig` adds exactly that, and "condenser" is not a class:

```python
rig   = Rig()
flask = rig.add("flask",     Vessel(net, volume=1.0, Q_input=80.0))
cond  = rig.add("condenser", Vessel(net, volume=0.5, T_env=288.0, UA=40.0))
rig.vapour("flask", "condenser", k=2.0)   # vapour rises
rig.drain("condenser", "flask",  k=0.5)   # condensate runs back
rig.run(1800.0)
```

That is reflux. A condenser is a cold vessel with a vapour path in and a liquid
path back --- built the same way a flask is, differing only in its parameters and
its edges.

## One state vector, not several vessels stepped in turn

$$ \mathbf y = \big[\ \text{vessel}_0\ (4n{+}1)\ \big|\ \text{vessel}_1\ (4n{+}1)\
   \big|\ \cdots\ \big|\ \text{vessel}_{m-1}\ (4n{+}1)\ \big] $$

::: {.keypoint}
Reflux is a **feedback loop** --- boil, rise, condense, return, reboil --- with
latent heat coupling the two temperatures. Operator-splitting a loop like that
across independently-stepped vessels smears it and, worse, makes the answer
depend on the stepping interval. That is precisely the non-determinism Layer 6
exists to prevent.

So the rig solves one system and lets BDF resolve the loop.
:::

Blocks are uniform because **every vessel in a rig shares one reaction
network**, which Layer 5 already required for pouring one flask into another.
The cost is that a condenser carries state for species it will never see; the
benefit is that the coupled system is a uniform array rather than a ragged one.

Each vessel's own physics enters *unchanged*: `VesselIntegrator.make_rhs`
already closes over a whole $4n{+}1$ state, so the rig calls it on a slice and
adds edge terms on top. There is no second copy of the vessel RHS to keep in
step with the first.

## The four edges

\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
  ves/.style={draw=csrule,fill=csbluebg,rounded corners=2pt,
              minimum width=27mm,minimum height=14mm,align=center,
              font=\sffamily\scriptsize},
  cool/.style={draw=csrule,fill=csgoldbg,rounded corners=2pt,
              minimum width=22mm,minimum height=9mm,align=center,
              font=\sffamily\scriptsize},
  ed/.style={->,>=Latex,thick},
  lb/.style={font=\sffamily\scriptsize,csgrey,align=center,
             fill=white,inner sep=1pt}]

  \node[ves]  (fun)  at (0,4.6)    {DROPPING\\FUNNEL};
  \node[ves]  (pot)  at (0,0)      {POT\\\scriptsize $Q_{\text{in}} = 80$ W};
  \node[ves]  (head) at (6.0,3.0)  {CONDENSER\\\scriptsize $T_{\text{env}} = 288$ K};
  \node[cool] (bath) at (6.0,5.6)  {COOLANT};
  \node[ves]  (rec)  at (12.0,0)   {RECEIVER};

  \draw[ed,csred] (fun) -- node[lb,left=1mm,pos=0.55]
       {METER\\\scriptsize fixed mol/s} (pot);
  \draw[ed,csblue] (pot.north east) to[bend left=22]
       node[lb,pos=0.5,above left=-0.5mm]
       {VAPOUR\\\scriptsize $k(P_a-P_b)\,x_{g,i}$} (head.west);
  \draw[ed,csgreen] (head.south west) to[bend left=22]
       node[lb,pos=0.5,below right=-0.5mm]
       {DRAIN\\\scriptsize reflux} (pot.east);
  \draw[ed,csgreen] (head.south east) to[bend left=22]
       node[lb,pos=0.5,above right=-0.5mm]
       {DRAIN\\\scriptsize $k\,n_{L,i}$} (rec.north west);
  \draw[ed,csgold,<->] (bath) -- node[lb,right=1mm]
       {THERMAL\\\scriptsize $q = UA(T_a-T_b)$} (head);
\end{tikzpicture}
\caption{The whole vocabulary. Every apparatus in the project is some
arrangement of these four edge types.}
\label{fig:rig}
\end{figure}

**`VAPOUR`** --- bidirectional, pressure-driven, carrying the *donor's* headspace
composition: $\dot n_i = k\,(P_a - P_b)\,x_{g,i}$. Venting to the room is the
same law with a fixed far end, which is why the existing vent constant did not
need generalising.

**`DRAIN`** --- one-directional liquid, first order in the donor's holdup,
$\dot n_i = k\,n_{L,i}$. This is a *drain*, not a level-driven flow: no geometry
is modelled and none is implied. It is what returns condensate down a reflux
column.

**`THERMAL`** --- $q = UA\,(T_a - T_b)$. Jackets, coolant, a flask in a bath.

**`METER`** --- one-directional liquid at a fixed molar rate: a dropping funnel
or a syringe pump. The rate is a **parameter an event sets**, deliberately *not*
a time window evaluated inside the RHS --- a hard on/off in $t$ is a
discontinuity mid-solve, whereas an event at a step boundary is not.

After `rig.arrays()` nothing downstream knows what a condenser is.

## What a still turns out to need

The physics of distillation worked immediately. The *protocol* did not, and the
gap is worth stating because it is a general shape.

::: {.trap title="The enrichment washes back out, and that is the point"}
Measured on 2 mol ethanol + 2 mol water at 300 W:

| $t$ / s | pot $T$ | head $T$ | $x$(EtOH) in the head |
|---:|---:|---:|---:|
| 200 | 302.43 | 300.62 | **0.655** |
| 600 | 303.63 | 299.57 | 0.618 |
| 1200 | 313.00 | 290.00 | **0.500** |

The enrichment is real and then it *disappears*, because everything comes over
eventually and there was no way to stop and change the receiver.

**Fractional distillation IS taking a cut, and the cut could not be expressed.**
Not merely unimplemented --- unsayable: `World` had no rig at all, no
`SWAP_RECEIVER` verb, and `wait_until` could only watch the vessel it was given
while the head was not a vessel `World` knew about.

That was the single largest gap between "the physics is there" and "you can play
it", and it was plumbing rather than science.
:::

## The plate column

Once cuts are expressible, a real fractionating column is a stack of vessels ---
each one a *plate*, with vapour rising and liquid falling. Eight plates at a
reflux ratio of 5 reach **0.8544** mole fraction.

::: {.trap title="The first attempt's diagnosis was wrong, and the real cause was pressure"}
The first plate column separated poorly and the finding was recorded as a
startup transient. It was not. **The still had no open end**, so it ran at
3--3.8 bar --- and at 3.8 bar the entire vapour--liquid equilibrium is different.

Check the pressure before you check the model.
:::

## The dropping funnel

Adding a reagent *slowly* is one of the most important controls a preparative
chemist has: it keeps an exotherm manageable by making the reaction
addition-rate-limited rather than kinetics-limited.

::: {.keypoint title="The mechanic already existed; what was missing was a way to SAY it"}
`METER` was already an edge type. What milestone G1 added was the ability to
express a **conditional** drip --- "add at 0.5 mmol/s until the pot reaches
340 K, then stop" --- which needed a save-format version bump and nothing else.

And it turned up a real physical finding: **sensible heat alone cannot make an
addition rate matter.** If the added reagent only has to be warmed up, the pot's
thermal mass swamps it. The rate matters when the addition *drives a reaction*
whose heat is large --- which is the actual reason a dropping funnel exists.
:::

Drip it too fast and the pot runs away. That is `examples/dropping_funnel.py`,
and the yield of the route it belongs to moved **4.5$\times$** on that change ---
with no species and no template touched. Chapter 30 is about why that matters
for measuring what the simulator can do.

::: {.trap title="A rig singularity that was a pump running dry"}
The most recent numerics session was handed "the rig integrator goes singular"
and expected a solver problem. It was a **METER edge pumping from a dry donor**:
the funnel had emptied, the meter kept demanding a fixed molar rate, and the
donor's composition --- which is scale-invariant --- reported back the solver's
own probe size rather than anything physical.

Two lessons recorded: a composition is scale-invariant, so `num_jac` can end up
measuring its own perturbation; and **an RHS is not only evaluated on its
trajectory** --- the solver probes states the physical system never visits, and
every guard has to hold there too.
:::

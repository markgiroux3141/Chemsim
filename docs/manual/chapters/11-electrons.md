# Electricity as a reagent

## Oxidation and reduction

Some reactions transfer electrons rather than atoms. Losing electrons is
**oxidation**; gaining them is **reduction**; the two always happen together,
because electrons have to come from somewhere.

$$ \mathrm{Zn} + \mathrm{Cu^{2+}} \to \mathrm{Zn^{2+}} + \mathrm{Cu} $$

Zinc is oxidised, copper reduced, and two electrons crossed over. If you
physically separate the two halves and connect them by a wire, the electrons
have to travel through the wire, and you have a battery.

## The cell, and $nFE$

Run it backwards --- push electrons through the wire from an external supply ---
and you can drive reactions that would not otherwise go. That is
**electrolysis**, and it is how aluminium, chlorine, sodium hydroxide and pure
hydrogen are made industrially.

The bookkeeping is one equation. Moving $n$ moles of electrons through a
potential difference $E$ does electrical work

$$ w_{\mathrm{el}} = nFE, \qquad F = N_A e = 96{,}485\ \text{C/mol}, $$

and that work is available to the reaction. So the criterion becomes

$$ \Delta G_{\mathrm{effective}} = \Delta G_{\mathrm{chem}} - nFE, $$

and **a reaction whose chemistry costs less than the cell supplies runs**. The
voltage at which the two balance is the **decomposition potential**:

$$ E_{\mathrm{dec}} = \frac{\Delta G_{\mathrm{chem}}}{nF}. $$

::: {.keypoint title="The whole of electrochemistry here is one subtraction"}
`ReactionTemplate` grew one field, `electrons`; `build_network(cell_potential=...)`
says what the supply is set to; $nFE$ joules come off the reaction's Gibbs
energy. **No gate, no flag, no new term, and no Layer 4 code at all.**

Nothing declares a decomposition potential, and the numbers fall out of
formation data alone: **1.441 V for water** against a book 1.229, and **2.362 V
for brine** against 2.186.
:::

## A half reaction does not conserve charge, so every template here is a whole cell

$\mathrm{2\,Cl^-} \to \mathrm{Cl_2} + 2e^-$ does not balance charge, and a
species list that does not balance charge is exactly what the network builder
rejects. There is no electron species in this project and there should not be:
an electron here would be a state-vector entry with a concentration, and the
electrons in a cell are not in the flask, they are in the wire.

So every electrode template is a **whole cell** --- anode half plus cathode
half, electrons cancelled, charge balanced. That is not a compromise; it is what
the catalog rows already say. "sodium-chloride + water $\to$ sodium-hydroxide +
chlorine + hydrogen" *is* the cell, not the anode. And it makes the arithmetic
honest, because $\Delta G$ of a half reaction is not measurable without a
reference electrode and $\Delta G$ of a cell is.

::: {.aside title="The price"}
A real cell's anode and cathode reactions are chosen independently by the
electrode material and the potential. Here each pairing is a separate template
that has to be written: four templates are four pairings, not two anodes times
two cathodes. That is a representation limit, and it is stated.
:::

## What the barrier means on an electrode reaction, and why it is not invented

An electrode reaction still needs an $E_a$, and here the identity that makes it
meaningful is nice enough to be worth spelling out.

Evans--Polanyi (Chapter 18) says $E_a = E_a^\circ + \alpha\,\Delta H$. Put the
cell's electrical work inside $\Delta H$, and

$$ E_a = E_a^\circ + \alpha\,(\Delta H_{\mathrm{chem}} - nFE) $$

which is **exactly the Butler--Volmer equation**, with $\alpha$ the
electrochemical transfer coefficient at its conventional value of 0.5. So
$E_a^\circ$ is the **activation overpotential** in energy units,
$E_a = nF\eta_a$, where $\eta_a$ is the extra volts a real cell needs on top of
its decomposition potential before it passes appreciable current.

::: {.keypoint}
Those are measured quantities with a century of Tafel data behind them, and the
two that matter here are wide apart: oxygen evolution is notoriously sluggish
($\eta_a \approx 0.5$ V on most anodes), chlorine evolution is not
($\approx 0.1$ V on a coated titanium anode).

**That gap is the entire reason a brine cell makes chlorine rather than the
oxygen its thermodynamics prefers**, and declaring it as a barrier in joules is
the only way this engine can express it. It is also a clean example of kinetics
beating thermodynamics --- the same phenomenon as Figure \ref{fig:selectivity},
in a different costume.
:::

## Where it stops, measured rather than assumed

`barrier` floors at zero, so far above $E_{\mathrm{dec}}$ every electrode
reaction runs out of barrier at its own rate and the selectivity goes with it. A
real cell is transport-limited there; this one is not limited by anything,
because **nothing here budgets current**. That is reported by
`validation/cell_potentials.py` rather than tuned away.

::: {.trap title="The milestone's own headline class did not survive its row check"}
M8 was scheduled because `electrolysis` was the top row of the coverage queue,
worth "+3 routes". Reading its four rows found **three different mechanisms**:
aqueous electrolysis (built), molten-salt electrolysis (a melt is not a phase
this project has), and amalgam electrolysis (a marker with no molecular graph).
Split on the project's own standard that *a reaction class names a mechanism,
not an outcome*, the top row is worth **+1**.

The other +2 came from a different class entirely, which happened to be fully
built. Net: +3 routes, from a curve that promised +3 from one class and was
wrong about which one.
:::

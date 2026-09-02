## M10 — Saturation-form rate laws  *(8 routes, one of them the oldest chemistry there is)*

⚠ **THIS IS THE LARGEST UNOWNED WALL, and it was not in any milestone until an
audit went looking.** Every rate in this project is power-law mass action, so
**Langmuir-Hinshelwood and Michaelis-Menten have nowhere to live** — a surface
or an enzyme has a SITE BALANCE, which is a denominator term, and the kernel
admits no rate form beyond `A·exp(-Ea/RT)·∏cᵛ`. That is exactly why homogeneous
catalysis was free (HANDOFF 37, a folded concentration) and this is not.

What it blocks, measured against `data/catalog`:

| route | era |
|---|---|
| **ethanol by fermentation** | ancient |
| Tyrian purple from murex | ancient |
| acetone-butanol-ethanol fermentation | 1900s |
| citric acid by fermentation | 1900s |
| monosodium glutamate | 1900s |
| penicillin fermentation and semisynthesis | 1900s |
| lactic acid to polylactide | modern |
| *(plus `biological-oxidation` / `biological-reduction` steps)* | |

**Brewing is the oldest applied chemistry in the catalog and the engine cannot
express it.** For a game inspired by preparative chemistry that is a worse hole
than aluminium.

⚠ Note the field to hang it off ALREADY EXISTS: `orders` (declared rate orders,
HANDOFF's declared-rate-order work) was the cheap first case of this backlog item
and explicitly does NOT close it — there is still no denominator. Adding one is a
kernel change, so it needs the full suite behind it.

⚠ **A declared rate order may never be reversible**, and the same will hold of a
saturating form: detailed balance derives the reverse pair from the forward
kinetics, and a Michaelis-Menten forward rate has no Arrhenius reverse. Expect to
declare these irreversible and say so.

⚠⚠ **CHECK THE CHEAP APPROXIMATION FIRST — AND IT NEEDS NO KERNEL CHANGE AT
ALL.** `orders` is a per-slot exponent tuple summed into the exponent matrix the
kernel has always carried, and **zero is already a legal order** — the sulfur
burner declares `(1, 1, 0, 0, 0, 0, 0, 0, 0)`. A declared order of **0 in the
substrate** IS the saturated limit of Michaelis-Menten: the reaction runs at a
constant rate set by enzyme loading until the substrate is exhausted, which is
most of what a fermentation looks like from outside. That gets the plateau, the
loading dependence and the sharp end-point today, for the cost of one tuple.

What it does NOT get is the TRANSITION — the approach to saturation, and the
crossover to first order as substrate runs out. So measure whether any catalog
route actually depends on the transition before building a denominator term. If
none does, M10 collapses from a kernel change into a template exercise, and the
milestone should say so rather than being built out of tidiness.

**Done when:** a fermentation runs to a substrate-limited plateau rather than to
completion, and the plateau moves with enzyme loading.

---

## G2 -- Ring deactivation, so nitration is a PROCESS and not an EVENT ✔✔ **DONE 2026-08-27**

✔ **BUILT AS THE BRIEF SCOPED IT, AND ITS FOUR DESIGN QUESTIONS ALL ANSWERED
THE WAY IT GUESSED.** It lives at SETUP (`build_network` bakes the shifted `Ea`
into the kinetics array -- no RHS edit, no tolerance-audit exposure); the
basis is Hammett; an unsubstituted ring keeps the declared barrier BIT FOR
BIT; and the corpus cost is four measured routes. See HANDOFF §100 and
`src/chemsim/reactions/hammett.py`.

⚠⚠ **THE ONE THING THE BRIEF DID NOT SAY, AND IT IS S12'S FINDING AGAIN: A rho
IS MEANINGLESS WITHOUT ITS SIGMA SCALE.** The table is **sigma-PLUS** (Brown &
Okamoto 1958), because electrophilic substitution builds positive charge on
the ring -- methoxy is -0.27 on sigma and -0.778 on sigma+, amino -0.66 and
-1.30. A sigma+-fitted rho applied to aqueous sigma is two bases multiplied
together.

**The result**: three barriers 25.0 kJ/mol apart, and 1.0 mol toluene + 3.5 mol
nitric acid is mono at 300 K/10 s, di at 300 K/100 s and 340 K/1 h, and TNT
only at 380 K -- the escalating sequence real manufacture uses. `tnt-route`
0.1528 -> 0.0662 mol (worse and righter); `benzene-nitration` 0.1762 ->
**0.8000** and `picric-acid-route` 0.0481 -> **0.1208** (both improvements,
because a mononitration can now STOP); `ddt-route` unchanged.

⚠ **THREE THINGS IT DOES NOT DO AND THEY ARE NAMED**: no regioselectivity (the
sum has no attacked carbon in it), no PROTONATION (aniline is priced as a free
base at 2.8e8 x benzene where the real anilinium is slower than benzene, and
4-aminophenol drives the barrier through a reported clamp), no sterics.
**Protonation coupled into a barrier is the next item on this branch.**

*The original brief follows.*


⚠⚠ **THE OBVIOUS DEMO REACTION WAS TESTED FIRST AND IT DOES NOT WORK.** Nitration
is the canonical add-slowly-or-it-runs-away reaction in all of chemistry, so it
was the natural choice for G1. Measured, 1.0 toluene + 3.5 nitric acid, staged by
nitro count:

      T/K      t/s  toluene     mono       di      tri
      300       10   0.0008   0.0098   0.0278   0.9616
      300      100   0.0000   0.0000   0.0000   1.0000
      340       10   0.0000   0.0000   0.0000   1.0000
      380     1000   0.0000   0.0000   0.0000   1.0000

**96% TRINITRO IN TEN SECONDS AT ROOM TEMPERATURE, AND THE ENDPOINT DOES NOT MOVE
WITH TEMPERATURE AT ALL.** There is no stage to catch and nothing for an addition
rate to control.

⚠ **THE CAUSE IS EXACT AND IT IS ONE LINE**: `aromatic_nitration(A=1.0e10,
Ea=60_000.0, alpha=0.0)` gives **one A and one Ea to every nitration on every
substrate**, so 2,4-dinitrotoluene nitrates exactly as fast as toluene. In
reality each nitro group deactivates the ring by 4-6 orders of magnitude, which is
precisely why TNT manufacture is a THREE-STAGE process with escalating acid and
temperature.

⚠⚠ **AND THE CHEAP FIX IS THE WRONG ONE. DO NOT JUST RAISE `alpha`.** S11
measured that Evans-Polanyi names the WRONG major product when kinetics fight
thermodynamics, and set `alpha = 0.0` on both hydroformylation templates for
exactly that reason. A substituent effect on an aromatic ring is an ELECTRONIC
property of the substrate, not a function of the reaction enthalpy, and dressing
one up as the other would be the `chemsim-competing-templates` trap again.

⚠ What this is really asking for is a **substituent-aware barrier** -- a term that
reads the ring's existing substituents and shifts Ea. That is new capability and
it is worth scoping properly. ⚠⚠ **AND IT IS THE HIGHEST-VALUE ITEM IN THE
G-SERIES**, because the same missing effect gates the whole 1800s aromatic tree:
dyes, explosives and painkillers all live on selective substitution, and the
engine currently cannot tell a deactivated ring from a fresh one.

## G1 -- The dropping funnel, and the first playground  ~~*(the fastest testable slice)*~~ ✔✔ **DONE 2026-08-27**

⚠⚠ **AND THE BRIEF BELOW NAMED THE WRONG GAP. READ HANDOFF §99 FIRST.** Every
one of the four items in the build list already existed as the rig's `meter`
edge, which `rig_integrator` documents as *"a dropping funnel or a syringe
pump"*: it delivers a set rate, it CARRIES THE DONOR'S SENSIBLE HEAT (270 K
funnel -> pot at 298.13 K, 370 K funnel -> 364.12 K, same moles), its reservoir
runs out exactly (0.001 to 10 mol/s, conserved to 1e-12), and `SET_EDGE`
already opens and shuts it inside a saveable scenario. A `feed` vector was
REFUSED as a second home for all of it, with a `feed_T` that is a declared
constant where a funnel VESSEL's temperature is a solved one.

⚠⚠ **WHAT WAS REAL IS THE ONE THING THE BRIEF SAID CAME FOR FREE.** *"It
composes with `wait_until` for free"* is FALSE, for exactly the reason
`collect_fraction` exists: an Event carries an absolute `t`, so a tap-close
scheduled after a discovered instant bakes THIS run's crossing into the recipe
and the same recipe REFUSES at twice the charge. `World.add_dropwise` stores
the condition. **SAVE_VERSION 5 -> 6** -- for a different reason than the brief
gave: an unknown SCRIPT VERB is discovered part-way through `run_script`, so a
v5 reader stops half-way through a recipe holding a world that looks finished.

⚠ **NO RHS EDIT, SO `tolerance_audit.py` WAS NOT OWED.** Playground:
`examples/dropping_funnel.py` (39 s). Audit: `validation/dropwise.py` (78 s).

*The original brief follows, kept because the measurement that overturned it
only means something against it.*


⚠⚠ **THE TARGET VIGNETTE, IN THE USER'S OWN WORDS**: toss a handful of materials
in a vessel, heat it, drip an acid in -- and *if you drip too much at once it
heats up and changes the reaction*, so you have to cool it and add slowly -- then
collect the vapour, run it through a condenser, and take the drops in a
temperature range.

⚠ **MEASURED AGAINST THE ENGINE, 2026-08-27. EXACTLY ONE MECHANIC IS MISSING:**

| the vignette | the engine |
|---|---|
| a handful of materials in a vessel | ✔ `Vessel.charge` |
| heat it up | ✔ `Q_input` / `SET_HEAT` |
| **drip an acid in slowly** | **MISSING** |
| too fast -> it heats up -> the reaction changes | ✔ emergent, once a feed exists |
| cool it down | ✔ `SET_ENVIRONMENT`, `UA` |
| collect the vapour, condense it | ✔ `Rig` vapour + drain edges |
| take the drops in a temperature range | ✔ `collect_fraction(enter, leave)` -- M2 |

⚠ **`ingress` IS NOT THE MECHANIC AND MUST NOT BE STRETCHED INTO IT.** It is
mol/s into the HEADSPACE, it is a constant, and it models an air leak. A dropping
funnel adds to LIQUID LAYER 1, carries SENSIBLE HEAT, and RUNS OUT.

**The build, and it is small:**

1. `VesselConditions.feed` -- an (n,) mol/s vector added to the **liquid layer 1**
   block of the RHS, beside where `ingress` is added to the vapour block.
2. `VesselConditions.feed_T` -- the temperature of what is being added, so the
   energy equation gets `sum(feed * Cp) * (feed_T - T)`. ⚠ **THIS TERM IS THE
   WHOLE POINT**: without it, dripping ice-cold acid warms the flask exactly as
   fast as dripping boiling acid, and the "cool it and add slowly" mechanic is
   cosmetic.
3. **THE RESERVOIR IS NOT STATE.** A funnel that runs out looks like a new state
   block and must not become one -- see the block-order trap. It is a DURATION:
   `total / rate`, derived, with the feed set back to zero afterwards. That is
   also what makes it a RECIPE rather than a script, and it composes with
   `wait_until` for free ("drip until the pot reaches 340 K, then stop").
4. A `SET_FEED` event so a drip saves and replays. **SAVE_VERSION 5 -> 6.**

⚠ **IT TOUCHES THE RHS**, so: `feed=None` must reproduce the current engine BIT
FOR BIT, and `tolerance_audit.py` is owed. S9's bit-identical test is the template.

⚠ **THE PLAYGROUND ITSELF SHOULD USE A FAMILY THAT ALREADY RACES**, and one
exists: `competing_pathways`' five templates on ethanol / acetic acid / air. Its
ester yield is measured at **85.6% at 420 K falling to 6.4% at 510 K**, so
temperature genuinely selects the product -- and both feedstocks are
**from-the-ground** (fermentation, then vinegar). ⚠⚠ **DO NOT BUILD IT ON
NITRATION -- MEASURED AND REFUSED, SEE G2.**

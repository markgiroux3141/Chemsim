## P4 -- The step UI, and then play it ✔✔ **DONE 2026-08-31** *(and playing it found six template fields that never reached the engine)*

Both controls are built and both are in the window.

**THE BENCH TAB IS THE PICKER.** 71 tiered rows, or all 1167 priced species, or
all 1583 with the 416 refusals **greyed and carrying their reason**; tier
checkboxes, a search box, a `generations` field and a species cap. ⚠ Choosing
rows BUILDS THE WORLD rather than filling a list -- P2's handoff -- so
`inventory.scenario_for` owns the two guarantees a widget cannot be trusted with:
every charged species in `feed_species`, and `electrolyte` on whenever an ion is
charged. `examples.bench` is an `Example` like the other four, so Reset, Save and
Load need no special case.

**REACT FURTHER raises the bound.** ⚠⚠ **AND IT RAISES THE SPECIES CAP TOO, which
is not a convenience**: at `generations=2` four bench reagents hit 400 species, so
the bound that BITES is the cap and a button that only bumped `generations` would
rebuild an identical network and look broken. Measured: glucose, water and air
give 400 species and 653 reactions at *both* 2 and 3 generations. **P1 found the
same competition from the other side.** The Drive tab now says which bound is in
force at all times, because "built to a fixpoint" and "bounded with nothing left
over" are different states of the world.

⚠ And it replays the RECIPE against a deeper reaction set, which is *the
experiment re-done knowing more chemistry* and not *the flask carried on from
here*. Stated in the message rather than left to be inferred from a number that
moved.

**The save format had to be fixed first.** It held `{"example": key, "script":
[...]}`, which is enough only while every world is one of four hard-coded ones. A
bench world is a shelf selection and has no key; a reacted-further world differs
from its key's scenario by exactly the bound that was raised. Both would have
reloaded as something else, silently. It carries `Scenario.to_dict()` now, and a
pre-P4 file still opens.

### ⚠⚠⚠ THEN IT WAS PLAYED, AND THE PLAY FOUND SIX FIELDS THE ENGINE NEVER SAW

Sulfur, air, water and a trace of NO2 off the shelf -- the game's own chain 2 --
**would not make vitriol at one atmosphere.** Two causes, in the order they were
found, and *neither one was findable from a green suite*:

**1. The bench's library was false by more than half.** It collected only
`*_chemistry` bundles -- the rule `validation/playable_levers.py` panel 5 uses --
and silently skipped every template exported as a function of its own:
`sulfur_combustion`, `sulfur_trioxide_hydration`, `lead_chamber`,
`esterification`, `cannizzaro` and about forty more. The flask gave **four
species, no reactions and an EMPTY FRONTIER at every generation count**, which is
the engine correctly reporting a library with no sulfur chemistry in it, while a
blurb claiming *every template in the project* was on screen. The sweep is by
RESULT TYPE now, so a naming convention nobody promised to keep cannot fool it.

**2. ⚠⚠⚠ `TemplateSpec` WAS DROPPING SIX `ReactionTemplate` FIELDS, AND A
FRONTEND CAN ONLY REACH THE ENGINE THROUGH A `Scenario`.** `sulfur_combustion`
declares `orders=(1, 1, 0...)` -- first order in oxygen, which S11 spent a
session establishing -- and the network ran the SMARTS' own **ninth-body mass
action** instead. 0.02 mol of S8 in a sealed litre at 700 K for an hour:

    O2 charged     declared 1st order     mass action (9 bodies)
      0.05 mol         15.23%                    0.0000%
      0.20 mol         99.44%                    0.0736%
      0.50 mol        100.00%                   77.85%

**A threshold where the declared law is a straight line**, and the shelf's own
oxygen bottle sits at 0.05. The same drop silently **un-gated every heterogeneous
catalyst** (`solid_catalyst`, S1 -- eleven templates declare one, and without it
ammonia synthesis runs in a flask with no iron), **took the driving force out of
every electrode reaction** (`electrons`, M8), and **lost G2's ring
deactivation** (`hammett_rho`, and `aromatic_nitration()` ships with **-6.5**, so
this was the DEFAULT being lost -- every stage of a staged nitration ran at the
same rate). `SAVE_VERSION` is **8**: the same bytes mean something different now,
which is the strongest reason to bump there is.

⚠ **THREE OF THE SIX WERE FOUND BY A TEST AND THREE BY THE PLAY, AND THE TEST
ONLY FOUND THEM BECAUSE IT ASSERTED THE *SET* OF FIELDS.** The play reached
`orders`; writing `tmpl_fields <= spec_fields` turned up the three `hammett_*`
ones immediately. *The lesson is not "add the field" -- `alpha`'s own comment
already said a template field is not finished until it round-trips. It is that
the assertion has to be about the set rather than about whichever field somebody
remembered.*

### And then it worked

    gens  species  frontier  what appeared
       1        6         1  SO2
       2        8         2  SULFURIC ACID, and NO
       3        8         0  nothing -- the network is complete and says so

**Chain 2 out of the picker in two presses of a button**, from four natural rows
and one intermediate. ⚠ The NO2 is why the `intermediate` tier exists: there is
no template for SO2 + O2 -> SO3 without a carrier, so sulfur, air and water alone
stop at SO2 **with an empty frontier** -- the engine saying it knows no further
chemistry rather than declining to look.

⚠ **The bench flask VENTS**, so an open flask at 700 K passes its steam and its
oxygen out of the top (S12's lesson again) and makes 3e-5 mol of SO2 in an hour.
And the shelf's gas amounts are deliberately small -- 0.05 mol is about a litre
at room conditions -- so an oxidation in a 1 L flask is oxygen-starved by
construction, which is a true thing about a bench rather than a bug: 0.2 mol of
S8 wants 1.6 mol of O2.

⚠⚠ **AND THE SHELF'S OWN WATER BOTTLE STOPS THE SHELF'S OWN SULFUR
BURNING, WHICH IS THE PLAY'S LAST FINDING AND IS EMERGENT.** A gas-phase
combustion is first order in GASEOUS S8, and 5 mol of water (90 mL) holds the
sulfur in the liquid. Sealed, 700 K, one hour, 0.05 mol of oxygen throughout:

    S8 charged   water    S8 in the gas    burnt
      0.20 mol   5.0 mol      4.30e-04     0.0001%
      0.20 mol   0.5 mol      3.32e-03     1.7369%
      0.02 mol   5.0 mol      4.70e-05     0.0003%
      0.02 mol   0.5 mol      3.92e-04    15.2266%

**A tenth of the water is 7.7x the sulfur in the vapour and four orders of
magnitude of conversion.** Nothing declares that: it is the phase model
partitioning S8 into whichever liquid is there. *You do not burn sulfur in a wet
flask*, and the engine says so without being told. ⚠ An earlier draft of this
section said "seal it and the same charge burns", which is FALSE and was written
from the 0.02 mol row: sealing changes almost nothing at 5 mol of water. The
lever is how much water you pour, and the shelf's bottle is 5.0.


`validation/shelf.py` is the standing audit for all four panels above.

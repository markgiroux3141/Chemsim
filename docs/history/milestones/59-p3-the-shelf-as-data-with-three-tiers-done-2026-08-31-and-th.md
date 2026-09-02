## P3 -- The shelf as data, with three tiers ✔✔ **DONE 2026-08-31** *(and the obvious resolution rule strands five rows in a form no mechanic can touch)*

`data/catalog/shelf.psv` exists: **71 rows**, `id | tier | amount | phase | note`,
diffable and tested like the rest of the corpus. `tools/build_shelf.py` resolves
it against the whole compound catalog and writes
`src/chemsim/engine/shelf_data.py` (`SHELF`, 71 rows; `ROSTER`, all 1583 species
with a verdict each); `src/chemsim/engine/inventory.py` turns a row into a real
`Stock`, and `scenario_for` turns a SELECTION into a world.

    natural       43 rows   out of the ground, the air, or something living
    intermediate  24 rows   a STRANDED route makes it -- EARNABLE, so DELETE it
                            the day that route becomes reachable
    bottle         4 rows   nothing in 173 catalog routes makes it at all
    ---
    all_priced()  1167      the cheat axis. NOT a fourth tier.
    roster()      1583      the picker's content, 416 of them greyed

⚠ **45 natural species, 43 rows, and the two missing ones cannot be added.**
`coal-marker` and `collagen-marker` have no molecular graph -- a marker is a
rock, a mixture or a protein carried so the catalog's routes stay balanced -- so
neither can be a `VesselState`, which §8.6 forbids outright. The generator
refuses an unresolvable id and `tests/test_playable_levers.py` pins the marker
set as an equality, so a third one cannot appear silently.

⚠ **Seven natural rows are REFUSED a price and stay on the shelf anyway** --
gold, quartz, pyrite, pyrrhotite, pyrolusite, borax, cryolite. "You can dig this
up" is a true statement about the world whatever the estimators say; the picker
greys them WITH the engine's own reason, and the day one is curated the row
lights up with no edit to the file.

### ⚠⚠⚠ THE FINDING: A ROCK HAS TWO REPRESENTATIONS AND THEY ARE NOT INTERCHANGEABLE

The obvious rule -- *charge a mineral as its `mineral_data` lattice* -- reads
correctly, generates a clean report, and **puts five shelf rows into the flask as
matter no mechanic in this engine can touch.** Measured, 0.5 mol into 30 mol of
water at 298 K for 600 s:

    rock salt as [Na+] + [Cl-] in the solid block   0.5 mol dissolved, block empty
    rock salt as the lattice '[Cl-].[Na+]'          0.5 mol of solid, for ever

Because the engine holds a solid **two incompatible ways**, and each has
mechanics the other does not:

    the LATTICE as one species     calcination, roasting, gas-solid reduction
                                   (`solid_state`, `surface`: the lattice IS the
                                   species)
    its IONS in the solid block    dissolution and precipitation through a Ksp
                                   (`PrecipitationArrays`: "the lattice is not a
                                   species and never becomes one")

and **nothing converts one into the other** -- `examples/lime_cycle.py` says so
in a comment: *the two representations of CaCO3 are different species that do not
know about each other.* Rock salt, fluorite, saltpetre, phosphate rock and
anhydrite have NO solid-state or surface reaction, so dissolving is the only
thing they do. Two of the five are load-bearing: rock salt is the chlor-alkali
feedstock, and `validation/phosphate_rock.py` charges the rock as
`{[Ca+2]: 3, PO4(3-): 2}` in the solid block and had already recorded that
*without the lattice the rock is INERT.* **C2 measured the failure mode this rule
would have walked into, a session before it was written.**

So the rule is MECHANISM-DRIVEN, read off the engine's own declarations:

    1. a lattice a solid_state/surface reaction consumes  -> the LATTICE
    2. else a mineral with ions and a priceable Ksp       -> its IONS, solid
    3. else charged fragments                            -> its ions, dissolved
    4. else                                              -> the molecule

⚠ **Rules 1 and 2 COLLIDE on six rows and rule 1 wins, which costs them their
dissolution**: calcite, covellite, galena, sphalerite, cinnabar, green vitriol
can be calcined or roasted and **cannot be dissolved by anything**. Limestone in
acid does nothing. That is a **NAMED ENGINE GAP** rather than a preference, and
the way out is a mechanic that turns a lattice charge into its ions.

⚠ **And the coverage audit's own tier answers a different question.** Seven rows
audit as `ion` and are rocks: the audit asks *can this be priced at all*, the
shelf asks *what species is in the bottle*, and the two come apart on 7 of 71.

### The phase column is a DECLARATION, and olive oil is why

The engine can answer "solid, liquid or gas at 298 K" for a neutral molecule --
gas if p_sat is above 1 atm, solid if Tm is above 298.15, liquid otherwise -- and
it is wrong about **triolein by 550 K**: Joback gives it `Tm = 828.9 K`, so a
derived phase puts a bottle of olive oil in the SOLID block. One shelf row in 71
disagrees with the engine and it is that one. *An estimator outside its domain
again, one rung further out than the element floor.*

⚠ A Henry's-law species is a GAS here, and reading `coefficient()` as a pressure
put nitrogen, oxygen and carbon dioxide in the liquid on the first pass.

`tolerance_audit.py` is **not owed by the PSV** -- a shelf row feeds no property
estimator and no rate -- but see P4, which changed what a network is built from.

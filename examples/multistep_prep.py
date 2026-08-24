"""Multistep prep: benzoic acid from ethyl benzoate.

saponify -> acidify -> crystallise -> filter -> wash -> assay.
Nothing below is scripted: no saponification rule, no solubility table, no pH
solver, no separation model, and no side-reaction script -- the impurities come
from the curated template library meeting a species this route makes for itself.

Two things are deliberately NOT ideal here, and both are mechanisms rather than
multipliers (see ``vessel.TransferLosses`` and ``validation/process_losses.py``):

  * the flask is left OPEN, so its headspace air oxidises the ethanol that
    saponification liberates -- three templates cascading, none of which mentions
    the others;
  * transfers leave a wall film and collections leave a crust of crystals stuck
    to the glass, which is what stands between a simulated yield and a bench one.

Run it with ``losses=None`` and under nitrogen and it returns to the old ideal
93.25% at 100.0001% closure. That is how you tell a loss from a bug.
"""
from chemsim import recipes
from chemsim.matter import Molecule
from chemsim.recipes import BENZOIC_ACID_PREP as PREP
from chemsim.recipes import BENZOYL, WATER
from chemsim.vessel import Vessel

# ⚠ THE RECIPE HAS ONE HOME NOW -- ``chemsim.recipes``. It used to be spelled out
# here, in ``validation/process_losses.py`` and in
# ``tests/test_prep_side_products.py``, and its conditions are load-bearing rather
# than incidental: this pot needs ``k_lle = 0.5`` instead of the default 5.0 or the
# two-phase system does not integrate at all. Three hand-kept copies of a number
# like that is how a harness ends up measuring something the example does not do.
ESTER = recipes.ETHYL_BENZOATE
ACID = recipes.BENZOIC_ACID
BENZOATE = recipes.BENZOATE
ACETIC = recipes.ACETIC_ACID
ETOH, NA, OH = recipes.ETHANOL, recipes.SODIUM, recipes.HYDROXIDE
O2, N2 = recipes.OXYGEN, recipes.NITROGEN

net = PREP.network()
CHARGED = [s for s in net.species if Molecule.from_smiles(s).charge != 0]
ORGANIC = [s for s in net.species
           if Molecule.from_smiles(s).charge == 0 and s not in (WATER, O2, N2)]
MW = {s: Molecule.from_smiles(s).molar_mass for s in net.species}


def show(v, label, keys=None):
    st = v.state()
    print(f"\n{label}")
    print(f"   T = {v.T:6.1f} K    pH = {v.pH:5.2f}    liquid = "
          f"{v.liquid_volume * 1000:.0f} mL")
    for s in keys or net.species:
        liq, sol = st.n_liquid[s], st.n_solid[s]
        if max(liq, sol) < 1e-5:
            continue
        tag = f"  <-- {sol * MW[ACID]:.2f} g crystals" if s == ACID and sol > 1e-5 else ""
        print(f"     {s:26s} dissolved {liq:8.4f}   solid {sol:8.4f}{tag}")


made: list[Vessel] = []


def flask(volume):
    """A receiver. Every one is remembered, because the mass balance at the
    bottom has to look everywhere the material could be -- including the
    intermediate cakes the wash loop replaces, which hold withheld film and a
    crust of crystals. Leaving them out once made closure read 99.97%, which
    looked like a loss destroying matter when it was the harness failing to look
    where the matter went."""
    f = PREP.receiver(net, volume)
    made.append(f)
    return f


# ---------------------------------------------------------------- step 1
# k_lle is BELOW its default of 5.0 mol/s here, and the reason is worth stating
# plainly rather than dressing up. This pot genuinely wants to be two layers --
# ethyl benzoate is barely water-soluble -- and until an ion transfer model existed
# the split was refused outright, which is what held every number in this file
# steady for three sessions. The refusal is gone now. What replaced it is a
# genuinely stiff two-phase system: 55 mol of strongly basic water beside 30 mL of
# nearly pure ester, and at the default transfer rate it does not integrate (see
# the note printed below, and NEXT_SESSION.md).
#
# ⚠ WHAT MAKES THAT REPORTABLE RATHER THAN A FUDGE: the answer does not depend on
# the number. 0.5 and 0.05 mol/s give the same benzoate to five decimal places, so
# the saponification is NOT transfer-limited on a two-hour timescale either way.
# That is the measurement step 2 of this session's arc asked for.
pot = PREP.pot(net, air=True)
made.append(pot)
print("=" * 74)
print("STEP 1  saponify: 0.20 mol ethyl benzoate + 0.30 mol NaOH, 80 C, 2 h")
print("        ... in a flask that still has air in it")
print("=" * 74)
show(pot, "  charged:")
print("\n   THE POT IS TWO LAYERS NOW, and it did not use to be allowed to be:")
print(f"     {pot.lle_report()}")
print(f"     aqueous layer permittivity {pot.layer_permittivity(1):.1f}")
print("\n   " + pot.electrolyte_report().replace("\n", "\n   "))
pot.run(7200.0)
show(pot, "  after 2 h:")
print(f"\n   {pot.lle_report() or 'one liquid again -- the layers merged'}")
print("\n   The ester is GONE and the product is the benzoATE, not the acid.")
print("   There is no saponification template in this network -- the only ester")
print("   reaction is the reversible Fischer esterification. Hydrolysis ran to")
print("   completion because hydroxide removes the benzoic acid as fast as the")
print("   reverse reaction makes it, so the equilibrium has nowhere to sit.")

side = {s: pot.state().total(s) for s in ORGANIC if s not in BENZOYL}
print("\n   AND THE ETHANOL IT LIBERATED HAS STARTED GOING WRONG:")
for s, n in sorted(side.items(), key=lambda kv: -kv[1]):
    if n > 1e-7 and s != ETOH:
        print(f"     {s:26s} {n * 1000:9.3f} mmol")
print("""
   Nobody added acetaldehyde or acetic acid to this network. Dissolved O2 from
   the headspace oxidises the ethanol to acetaldehyde and hydrogen peroxide;
   that peroxide over-oxidises the aldehyde to acetic acid; and the acid then
   re-esterifies with the remaining ethanol. Three templates meeting, none of
   which mentions the others, all of them engaged by an alcohol this prep made
   for itself. Fill the headspace with nitrogen instead and every line above
   except the trace of ether goes to zero.

   The oxygen budget is the headspace, so the amount is set by how much air was
   in the flask -- which makes 'stopper it' and 'stir it less' real levers
   rather than flavour text.""")

# ---------------------------------------------------------------- step 2
print("\n" + "=" * 74)
print("STEP 2  acidify: 0.28 mol H2SO4, then cool to 2 C")
print("=" * 74)
PREP.acidify(pot)
pot.run(3600.0)
show(pot, "  after acidifying and cooling:")

pot.run(14400.0)
show(pot, "  after 4 more hours (crystals growing):")
sat = pot.saturation().get(ACID, 0.0)
print("\n   benzoate -> benzoic acid on acidification, and the free acid is only")
print(f"   sparingly soluble, so it crops out. x/x_sat = {sat:.3f} (1.000 = saturated).")

# ---------------------------------------------------------------- step 3
print("\n" + "=" * 74)
print("STEP 3  filter (Buchner, a cake 40% void -- see Vessel.filter_into)")
print("=" * 74)
cake, filtrate = flask(1.0), flask(3.0)
res = pot.filter_into(filtrate=filtrate, cake=cake, porosity=0.4)
print(f"   cake: {res.cake_solid:.4f} mol solid + {res.cake_liquid:.3f} mol wet")
print(f"   filtrate: {res.filtrate_liquid:.3f} mol liquid")
print(f"   LEFT IN THE POT: {res.retained_solid:.4f} mol "
      f"({res.retained_solid * MW[ACID]:.2f} g) of crystals stuck to the glass "
      f"-- {100 * (1 - res.recovered):.1f}% of the crop")
print(f"   {pot.crust_report()}")


def assay(v, label):
    st = v.state()
    product = st.total(ACID)
    ions = sum(st.total(s) for s in CHARGED)
    mass_p = product * MW[ACID]
    mass_i = sum(st.total(s) * MW[s] for s in CHARGED)
    mass_o = sum(st.total(s) * MW[s] for s in ORGANIC if s != ACID)
    dry = mass_p + mass_i + mass_o
    print(f"   {label:22s} product {product:7.4f} mol ({mass_p:6.2f} g)   "
          f"ions {ions:7.4f} mol   purity(dry) {100 * mass_p / dry:5.1f}%   "
          f"yield {100 * product / 0.20:5.1f}%")
    return product, 100 * mass_p / dry


assay(cake, "cake as filtered")

# ---------------------------------------------------------------- step 4
print("\n" + "=" * 74)
print("STEP 4  wash the cake with 20 mL ice water, then re-filter")
print("=" * 74)
cake.charge({WATER: 1.1})
cake.run(600.0)
washed, liquor = flask(1.0), flask(2.0)
cake.filter_into(filtrate=liquor, cake=washed, porosity=0.4)
assay(washed, "after one wash")

cake2 = washed
cake2.charge({WATER: 1.1})
cake2.run(600.0)
washed2, liquor2 = flask(1.0), flask(2.0)
cake2.filter_into(filtrate=liquor2, cake=washed2, porosity=0.4)
assay(washed2, "after two washes")
print("\n   Each wash buys purity and costs product TWICE over: some dissolves,")
print("   and some stays stuck to the flask it was washed in. Both are visible")
print("   in the balance below rather than being differenced out of a yield.")

print("\n" + "=" * 74)
print("MASS BALANCE across the whole route")
print("=" * 74)
holdings = [("cake", washed2), ("pot", pot), ("first filtrate", filtrate),
            ("wash cake 1", cake), ("wash liquor 1", liquor),
            ("wash liquor 2", liquor2)]
for name, v in holdings:
    st = v.state()
    print(f"   {name:16s} benzoyl {sum(st.total(s) for s in BENZOYL):8.5f} mol")
total = sum(sum(v.state().total(s) for s in BENZOYL) for v in made)
print(f"   {'TOTAL (all ' + str(len(made)) + ' vessels)':16s} benzoyl {total:8.5f} mol"
      f"   (charged 0.20000)")
print(f"   closure: {100 * total / 0.20:.4f}%")
print("""
   Closure stays at 100% with the losses ON, and that is the point: every loss
   here is material that FAILED TO MOVE, not material destroyed. The film is on
   the pot wall, the crust is stuck to the glass beside it, and both are still
   in the vessel they were left in -- which is why 'rinse it and re-filter' is
   a recovery a player can perform and why it needed no code of its own.""")

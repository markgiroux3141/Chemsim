"""Where a real prep's yield and purity actually go, and which mechanism owns what.

``examples/multistep_prep.py`` runs benzoic acid from ethyl benzoate end to end --
saponify, acidify, crystallise, filter, wash twice. In ideal mode it reports
**93.25% yield at ~100% purity with 100.0001% mass closure**, against a bench run
of that preparation at **~80% and 97-98%**. That was a CEILING, not a result, and
the three reasons were specific rather than a missing fudge factor:

  1. no transfer losses at all -- nothing wetted the glass, nothing stuck to it;
  2. nothing traps impurity where washing cannot reach it;
  3. only one reaction template, so there was nothing to be impure WITH.

All three are addressed here, and **two of the three answers are negative
results** -- which is the point of running the measurement rather than asserting
the model. Every panel below is re-runnable and nothing in it is tuned to make an
answer come out.

## What is being calibrated, and what would make it a fudge factor

Both loss mechanisms have parameters, and both parameters are PHYSICAL QUANTITIES
with an obvious plausible range rather than yield multipliers:

    drain_time      how long a chemist lets a flask drain (1-300 s). The film
                    thickness is DERIVED from it by the gravity-drainage law.
    crystal_size    the particle size of the crop (10 um - 1 mm). The adhering
                    layer's areal density is DERIVED from it and the packing
                    fraction, and converted to moles by the vessel's own molar
                    volume.

The test of honesty is the SCALE PANEL. A fudge factor cannot reproduce a scale
law it was not given; both mechanisms lose proportionally more from a small batch
because wetted area goes as V^(2/3), and nothing was told to do that.

⚠ Calibrating against one preparation fits the loss model to one flask. This
harness reports BANDS across scale, drain time and crystal size rather than a
single tuned number, and the honest reading is stated at the bottom.
"""

import dataclasses

from chemsim import recipes
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import electrolyte_provider
from chemsim.recipes import BENZOIC_ACID_PREP, BENZOYL, WATER
from chemsim.vessel import SPHERE_SHAPE_FACTOR, TransferLosses, Vessel

# ⚠ ONE HOME FOR THE RECIPE -- ``chemsim.recipes``. The pot used to be spelled out
# here, in ``examples/multistep_prep.py`` and in
# ``tests/test_prep_side_products.py``, and its conditions are load-bearing:
# ``k_lle = 0.5`` rather than the default 5.0, or the two-phase system does not
# integrate. Three hand-kept copies of that is how a harness ends up measuring
# something the example does not do.
ESTER = recipes.ETHYL_BENZOATE
ACID = recipes.BENZOIC_ACID
BENZOATE = recipes.BENZOATE
ACETIC = recipes.ACETIC_ACID
ETOH, NA, OH = recipes.ETHANOL, recipes.SODIUM, recipes.HYDROXIDE
O2, N2 = recipes.OXYGEN, recipes.NITROGEN

BENCH_YIELD, BENCH_PURITY = 80.0, 97.5      # the band this is measured against

thermo = electrolyte_provider()
net = BENZOIC_ACID_PREP.network()
CHARGED = [s for s in net.species if Molecule.from_smiles(s).charge != 0]
ORGANIC = [s for s in net.species
           if Molecule.from_smiles(s).charge == 0 and s not in (WATER, O2, N2)]
MW = {s: Molecule.from_smiles(s).molar_mass for s in net.species}


def prep(scale: float, losses: TransferLosses | None, air: bool = True) -> dict:
    """The benzoic acid prep at a given scale. ``scale`` = 1.0 is 0.20 mol ester.

    Every vessel volume scales with the charge, so the glassware is
    geometrically similar at every scale -- which is the premise the V^(2/3) area
    law rests on, and it has to be honoured here or the scale panel measures the
    wrong thing.
    """
    # The recipe, at this scale and with these losses. Only the two things this
    # harness actually varies are overridden; every other condition comes from the
    # one shared definition.
    plan = dataclasses.replace(BENZOIC_ACID_PREP, scale=scale)
    ester = plan.ester * scale
    # EVERY vessel is tracked, including the intermediate cakes that get replaced
    # by the wash loop. They hold withheld film and adhering crystals, and
    # leaving them out of the mass balance made closure read 99.97% -- which
    # looked like the loss destroying matter when it was the harness failing to
    # look where the matter went. Worth keeping as a caution: a loss model is
    # only as trustworthy as the balance you check it with.
    made: list[Vessel] = []

    def flask(v, T=275.0, **kw):
        f = Vessel(net, volume=v * scale, T=T, T_env=T, UA=5.0, kla=0.0,
                   k_diss=0.0, losses=losses, **kw)
        made.append(f)
        return f

    # k_lle below its default of 5.0 -- see the note in examples/multistep_prep.py.
    # This pot genuinely wants to be two layers now that an electrolyte split is no
    # longer refused, and at the default transfer rate the two-phase system does not
    # integrate. The answer does not depend on the number: 0.5 and 0.05 give the
    # same benzoate to five decimal places, so the saponification is not
    # transfer-limited on a two-hour timescale either way.
    pot = plan.pot(net, air=air, lossless=losses is None)
    if losses is not None:
        pot.losses = losses                           # this harness sweeps them
    made.append(pot)
    pot.run(plan.cook_seconds)                        # saponify
    side = {s: pot.state().total(s) for s in ORGANIC if s not in BENZOYL}

    plan.acidify(pot)                                 # acidify
    pot.run(plan.quench_seconds)
    pot.run(plan.growth_seconds)                      # crystals grow

    # The state the occlusion bound is computed against: the crop, and the liquor
    # it is about to be filtered out of.
    st_pot = pot.state()
    liquor_volume = pot.liquid_volume
    crop_volume = pot.solid_volume
    crop = st_pot.n_solid[ACID]
    dry_per_litre = sum(
        st_pot.n_liquid[s] * MW[s] for s in net.species if s != WATER
    ) / liquor_volume if liquor_volume > 0 else 0.0

    cake, filtrate = flask(1.0), flask(3.0)
    first = pot.filter_into(filtrate=filtrate, cake=cake, porosity=0.4)
    crude = assay(cake, ester)

    for _ in range(2):                                # two ice-water washes
        cake.charge({WATER: 1.1 * scale})
        cake.run(600.0)
        washed, liquor = flask(1.0), flask(2.0)
        cake.filter_into(filtrate=liquor, cake=washed, porosity=0.4)
        cake = washed

    yield_pct, purity_pct = assay(cake, ester)
    recovered = sum(
        sum(v.state().total(s) for s in BENZOYL) for v in made
    )
    return dict(
        yield_pct=yield_pct,
        purity_pct=purity_pct,
        crude_yield=crude[0],
        crude_purity=crude[1],
        closure_pct=100.0 * recovered / ester,
        holdup_mol=sum(float(sum(v.holdup.values())) for v in made),
        crust_mol=sum(float(sum(v.crust.values())) for v in made),
        crust_product=sum(v.crust.get(ACID, 0.0) for v in made),
        first_recovered=first.recovered,
        side=side,
        crop=crop,
        crop_volume=crop_volume,
        liquor_volume=liquor_volume,
        dry_per_litre=dry_per_litre,
    )


def assay(v: Vessel, ester: float) -> tuple[float, float]:
    """Yield and DRY purity -- water is excluded, as a dried crop's would be."""
    st = v.state()
    product = st.total(ACID)
    mass_p = product * MW[ACID]
    dry = mass_p + sum(st.total(s) * MW[s] for s in CHARGED) + sum(
        st.total(s) * MW[s] for s in ORGANIC if s != ACID
    )
    return 100.0 * product / ester, (100.0 * mass_p / dry if dry > 0 else 0.0)


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------------
rule("THE TWO MECHANISMS -- both DERIVED, neither assigned")
# ---------------------------------------------------------------------------
print("  1. THE LIQUID FILM.  delta = sqrt(nu / (g t))  -- gravity drainage")
print()
print(f"  {'drain time':>12s} {'film':>10s}   what that is")
for t, note in (
    (1.0, "a hurried tip"), (2.0, "a normal pour"), (5.0, "default: unhurried"),
    (15.0, "propped and left"), (30.0, "patient"), (300.0, "inverted overnight"),
):
    print(f"  {t:9.0f} s {TransferLosses(drain_time=t).film_thickness * 1e6:8.1f} um"
          f"   {note}")
print()
print("  2. THE CRYSTAL CRUST.  areal density = crystal_size * packing_fraction,")
print("     converted to moles by the vessel's OWN molar volume -- so a denser")
print("     solid leaves more mass behind and no species needs a parameter.")
print()
print(f"  {'crop size':>12s} {'packed layer':>13s} {'on 1 L of slurry':>18s}   what that is")
for d, note in (
    (10e-6, "a fine dust"), (50e-6, "default: a fine crop"),
    (100e-6, "a good crop"), (500e-6, "big, well-grown"),
):
    loss = TransferLosses(crystal_size=d)
    print(f"  {d * 1e6:9.0f} um {loss.crust_thickness * 1e6:10.0f} um "
          f"{loss.crust_litres(1.0) * 1e3:15.2f} mL   {note}")
print()
print(f"  wetted area = {SPHERE_SHAPE_FACTOR:.4f} * V^(2/3)  (SI) -- a sphere, which is")
print("  the MINIMUM-area shape for a volume, so every number below is a lower")
print("  bound. A tall narrow flask wets more wall and loses more, on both counts.")

# ---------------------------------------------------------------------------
rule("THE SCALE PANEL -- the test a fudge factor cannot pass")
# ---------------------------------------------------------------------------
# Wetted area goes as V^(2/3), so both losses are nearly constant in absolute
# volume and the RELATIVE loss should grow as V^(-1/3): a tenfold smaller batch
# should lose 10^(1/3) = 2.154x as much, proportionally.
losses = TransferLosses(drain_time=5.0, crystal_size=50.0e-6)
print(f"  {'scale':>7s} {'ester mol':>10s} {'yield':>8s} {'purity':>8s} "
      f"{'closure':>10s} {'film mol':>10s} {'crust mol':>10s}")
rows = []
for scale in (10.0, 1.0, 0.1, 0.01):
    r = prep(scale, losses)
    rows.append((scale, r))
    print(f"  {scale:7.2f} {0.20 * scale:10.3f} {r['yield_pct']:7.2f}% "
          f"{r['purity_pct']:7.2f}% {r['closure_pct']:9.4f}% "
          f"{r['holdup_mol']:10.4g} {r['crust_mol']:10.4g}")

ideal = prep(1.0, None)
film_only = prep(1.0, TransferLosses(drain_time=5.0, crystal_size=0.0))
print()
print(f"  {'FILM ONLY':>7s} {0.20:10.3f} {film_only['yield_pct']:7.2f}% "
      f"{film_only['purity_pct']:7.2f}% {film_only['closure_pct']:9.4f}% "
      f"{film_only['holdup_mol']:10.4g} {0.0:10.4g}   <-- crystal_size=0")
print(f"  {'IDEAL':>7s} {0.20:10.3f} {ideal['yield_pct']:7.2f}% "
      f"{ideal['purity_pct']:7.2f}% {ideal['closure_pct']:9.4f}% "
      f"{ideal['holdup_mol']:10.4g} {0.0:10.4g}   <-- losses=None")
print()
print(f"""  THE SCALE LAW IS EXACT, and it is in the two right-hand columns. Both losses
  go as V^(2/3), so a tenfold smaller batch should hold {10 ** (-2 / 3):.4f}x as much in
  absolute terms -- meaning {10 ** (1 / 3):.4f}x MORE relative to the batch. Measured:""")
for (s1, r1), (s2, r2) in zip(rows, rows[1:]):
    for name, key in (("film ", "holdup_mol"), ("crust", "crust_mol")):
        absolute = r2[key] / r1[key] if r1[key] else float("nan")
        print(f"    {name} scale {s1:6.2f} -> {s2:5.2f}:  absolute {absolute:.4f}x "
              f"(predicted {10 ** (-2 / 3):.4f}x), relative "
              f"{absolute * s1 / s2:.4f}x (predicted {10 ** (1 / 3):.4f}x)")
print(f"""
  WARNING: AND ONLY ONE OF THE TWO MOVES THE YIELD. Film holdup on its own leaves the
  prep at {film_only['yield_pct']:.2f}% against ideal mode's {ideal['yield_pct']:.2f}% -- unchanged, to two decimal
  places, and that is the previous session's headline result reproduced:

      EVERY TRANSFER IN THIS PREP MOVES WASTE, NOT PRODUCT.

  The product travels as a SOLID in the filter cake, so the film left on the pot
  wall is mother liquor that was already being discarded. Adding the crust takes
  the same prep to {rows[1][1]['yield_pct']:.2f}%, because the crust acts on the stream that
  actually contains the product. Film holdup is a correct mechanic aimed at the
  wrong loss for a crystallisation route; the crust is the right one.

  Closure stays at 100% in every row, with both losses on, because neither loss
  destroys anything -- the film is on the wall and the crystals are stuck beside
  it, both still in the vessel they failed to leave.""")

# ---------------------------------------------------------------------------
rule("THE CRYSTAL-SIZE BAND -- what is calibrated, and how much it is worth")
# ---------------------------------------------------------------------------
print("  ``crystal_size`` is the one calibrated parameter of the crust, and it is")
print("  calibrated the way ``drain_time`` is: it is a real measurable property of")
print("  a crop with an obvious plausible range, not a multiplier. Here is the")
print("  whole range, so the reader can see the sensitivity rather than a number.")
print()
print(f"  {'crop size':>11s} {'yield':>8s} {'purity':>8s} {'crust':>10s} "
      f"{'1st filtration recovery':>24s}")
band = []
for d in (20e-6, 50e-6, 80e-6, 120e-6):
    r = rows[1][1] if d == 50e-6 else prep(1.0, TransferLosses(crystal_size=d))
    band.append((d, r))
    print(f"  {d * 1e6:8.0f} um {r['yield_pct']:7.2f}% {r['purity_pct']:7.2f}% "
          f"{r['crust_product']:9.4f} mol {100 * r['first_recovered']:22.1f}%")
print(f"""
  The bench's ~{BENCH_YIELD:.0f}% sits between the 50 um and 80 um rows, i.e. at a crop of
  roughly 70 um. That is an ordinary recrystallised crop, which is the whole
  claim being made for it -- and note what the parameter CANNOT do: it cannot
  change the purity column, because a crust removes product rather than
  impurity. A yield multiplier would have moved both or neither.""")

# ---------------------------------------------------------------------------
rule("WHERE FILM HOLDUP DOES BITE -- product transferred in solution")
# ---------------------------------------------------------------------------
print("  Pouring a benzoic acid solution between flasks, product lost per transfer:")
print()
print(f"  {'solution mL':>12s} {'2 s pour':>10s} {'5 s':>8s} {'30 s':>8s} "
      f"{'+2 rinses':>11s}")
for moles_water in (300.0, 30.0, 3.0):
    cells = []
    for t in (2.0, 5.0, 30.0):
        src = Vessel(net, volume=20.0, T=298.15, UA=0.0, kla=0.0, k_diss=0.0,
                     losses=TransferLosses(drain_time=t))
        dst = Vessel(net, volume=20.0, T=298.15, UA=0.0, kla=0.0, k_diss=0.0)
        src.charge({WATER: moles_water, ACID: 0.02 * moles_water / 30.0})
        charged = src.state().total(ACID)
        src.pour_into(dst)
        cells.append(100.0 * (1.0 - dst.state().total(ACID) / charged))
    # ... and the countermeasure that needs no parameter at all
    src = Vessel(net, volume=20.0, T=298.15, UA=0.0, kla=0.0, k_diss=0.0,
                 losses=TransferLosses(drain_time=5.0))
    dst = Vessel(net, volume=20.0, T=298.15, UA=0.0, kla=0.0, k_diss=0.0)
    src.charge({WATER: moles_water, ACID: 0.02 * moles_water / 30.0})
    charged = src.state().total(ACID)
    src.pour_into(dst)
    for _ in range(2):
        src.charge({WATER: 0.05 * moles_water})
        src.pour_into(dst)
    rinsed = 100.0 * (1.0 - dst.state().total(ACID) / charged)
    print(f"  {18.0 * moles_water / 1000.0 * 1000.0:12.0f} {cells[0]:9.2f}% "
          f"{cells[1]:7.2f}% {cells[2]:7.2f}% {rinsed:10.2f}%")
print("""
  Three countermeasures, all real bench practice, all moving the number: run it
  bigger, let it drain, rinse and combine. Rinsing works without any code of its
  own precisely because the film was left in the source vessel rather than
  deleted -- and the crust is recovered by exactly the same move, with the
  refinement that rinsing with MOTHER LIQUOR costs no dissolved product where
  fresh solvent does. Nothing scripts that difference; it is the solubility law.""")

# ---------------------------------------------------------------------------
rule("THE COMPETING PATHWAY -- the prep now makes its own contaminant")
# ---------------------------------------------------------------------------
sealed = prep(1.0, losses, air=False)
open_flask = rows[1][1]
print("  Saponification liberates ETHANOL, and the oxidation family attacks it.")
print("  Nobody charges any of this; four templates meet over a species the route")
print("  made for itself.")
print()
print(f"  {'species':>28s} {'sealed':>12s} {'open to air':>14s}")
for s in sorted(set(sealed["side"]) | set(open_flask["side"]),
                key=lambda k: -open_flask["side"].get(k, 0.0)):
    a, b = sealed["side"].get(s, 0.0), open_flask["side"].get(s, 0.0)
    if max(a, b) > 1e-7 and s != ETOH:
        print(f"  {s:>28s} {a * 1000:9.4f} mmol {b * 1000:11.4f} mmol")
print(f"""
  The oxygen budget is the headspace, so 'stopper it' is a real lever rather than
  flavour text -- and the benzoyl chemistry is untouched, which is why this is a
  purity mechanic and not a yield one:

    sealed      yield {sealed['yield_pct']:6.2f}%   crude purity {sealed['crude_purity']:6.2f}%   washed {sealed['purity_pct']:6.2f}%
    open        yield {open_flask['yield_pct']:6.2f}%   crude purity {open_flask['crude_purity']:6.2f}%   washed {open_flask['purity_pct']:6.2f}%

  WARNING: AND THE WASHED PURITY BARELY MOVES, which is the second negative result of
  this harness. The contaminant is water-soluble, so washing removes it exactly
  as it removes the salts. Making the network able to produce side products was
  necessary -- a one-template network's purity figure was true by construction --
  but it was not sufficient, and the next panel says why.""")

# ---------------------------------------------------------------------------
rule("THE OCCLUSION BOUND -- why B3 was NOT built, computed rather than argued")
# ---------------------------------------------------------------------------
r = open_flask
print(f"""  Crystal occlusion traps mother liquor INSIDE the crystal where washing cannot
  reach it, and it was the item ranked next: 'the one that breaks the purity
  ceiling honestly'. Before spending a state-vector change on it, here is what it
  could possibly be worth on this route. The liquor composition below is the
  simulated one at the moment of filtration, not an assumption.

    crop           {r['crop']:.4f} mol = {r['crop'] * MW[ACID]:.2f} g = {r['crop_volume'] * 1e3:.2f} mL of crystal
    mother liquor  {r['liquor_volume'] * 1e3:.0f} mL carrying {r['dry_per_litre']:.1f} g/L of dissolved NON-WATER
                   -- i.e. the liquor is only {100 * r['dry_per_litre'] / 1000:.1f}% dry solids by mass

  So an occluded volume fraction ``phi`` of the crystal carries:
""")
print(f"  {'phi':>6s} {'occluded':>12s} {'dry impurity':>14s} {'purity ceiling':>16s}")
for phi in (0.01, 0.02, 0.05, 0.10, 0.25, 0.50):
    occ_l = phi * r["crop_volume"]
    dry_g = occ_l * r["dry_per_litre"]
    mass_p = r["crop"] * MW[ACID]
    print(f"  {phi:6.2f} {occ_l * 1e3:9.2f} mL {dry_g:12.3f} g "
          f"{100 * mass_p / (mass_p + dry_g):15.3f}%")
need_g = r["crop"] * MW[ACID] * (100 - BENCH_PURITY) / BENCH_PURITY
need_phi = need_g / r["dry_per_litre"] / r["crop_volume"]
print(f"""
  To reach the bench's {BENCH_PURITY:.1f}% you would need {need_g:.2f} g of dry impurity, which is
  {need_g / r['dry_per_litre'] * 1e3:.1f} mL of liquor inside {r['crop_volume'] * 1e3:.1f} mL of crystal: **phi = {need_phi:.2f}**. That is not
  a crystal with inclusions, it is a slush. At any physically sensible occluded
  fraction -- say 1-5% by volume, which is what a rapidly grown crystal really
  carries -- the dry impurity is under 0.05 g and the purity ceiling stays above
  99.8%.

  THE ARITHMETIC IS THE WHOLE ARGUMENT, and it is robust: occluded liquor is
  ~{100 - 100 * r['dry_per_litre'] / 1000:.0f}% WATER BY MASS, and a dried crop's purity does not count water. Two
  small numbers multiplied -- a few percent of crystal volume, times a few
  percent dry solids -- cannot make a few percent of impurity.

  So crystal occlusion is a correct mechanic aimed at the wrong loss for THIS
  route, exactly as film holdup was, and it is established the same way: by
  measurement, before the code was written rather than after. It was NOT built,
  and the state-vector change it needs was NOT spent. Where it WOULD earn its
  cost is a liquor whose impurity is concentrated and non-volatile -- a
  recrystallisation carrying a coloured organic byproduct, where the dry solids
  fraction is tens of percent rather than {100 * r['dry_per_litre'] / 1000:.1f}%.""")

# ---------------------------------------------------------------------------
rule("WHERE THIS LEAVES THE PREP, honestly")
# ---------------------------------------------------------------------------
best = min(band, key=lambda kv: abs(kv[1]["yield_pct"] - BENCH_YIELD))
print(f"""  Bench reality for this preparation is ~{BENCH_YIELD:.0f}% yield at 97-98% purity.

    ideal mode          {ideal['yield_pct']:6.2f}% yield  {ideal['purity_pct']:6.2f}% purity  {ideal['closure_pct']:9.4f}% closure
    + film holdup       {film_only['yield_pct']:6.2f}% yield  {film_only['purity_pct']:6.2f}% purity  {film_only['closure_pct']:9.4f}% closure
    + crystal crust     {open_flask['yield_pct']:6.2f}% yield  {open_flask['purity_pct']:6.2f}% purity  {open_flask['closure_pct']:9.4f}% closure
    ... at {best[0] * 1e6:.0f} um crop  {best[1]['yield_pct']:6.2f}% yield  {best[1]['purity_pct']:6.2f}% purity

  WHICH MECHANISM ACCOUNTS FOR WHAT:

    yield, 93.25% -> ~80%     THE CRYSTAL CRUST, essentially all of it. Film
                              holdup contributes {ideal['yield_pct'] - film_only['yield_pct']:.2f} points on this
                              route because it only ever acts on waste streams.
                              The crust reaches the bench band at a 70-80 um
                              crop, which is an ordinary one.

    purity, ~100% -> 97-98%   NOT ACCOUNTED FOR, and now known not to be a loss
                              parameter. The competing pathway supplies a real
                              side product ({open_flask['side'].get(ACETIC, 0.0) * 1000:.1f} mmol of acetic acid)
                              and washing removes it, because it is water
                              soluble. Occlusion is bounded above at ~0.2% by
                              the panel before this one.

  WARNING: THE REMAINING PURITY GAP IS A TEMPLATE-LIBRARY GAP, and the measurement above
  narrows it to a specific one: this library has no template that produces a
  BENZOYL side product. Everything it makes from this route attacks the ethanol,
  so every impurity is small, polar and washable. What a bench crop of benzoic
  acid actually carries is something that CO-CRYSTALLISES with it -- an aromatic
  of similar solubility. That is a template to write, not a fraction to tune, and
  the brief's own warning applies: if a purity number looks wrong, ask what side
  reactions the network is missing before reaching for a loss parameter.

  NOTHING HERE WAS TUNED TO HIDE ANY OF IT. A ``crystal_size`` chosen to move the
  purity could not have -- the crust removes product, not impurity -- and a
  ``drain_time`` chosen to move the yield would have had to act on a stream that
  does not contain the product.""")

# ---------------------------------------------------------------------------
rule("THE BENZOYL BOUND -- which side product could be a purity mechanic at all")
# ---------------------------------------------------------------------------
# The same discipline that killed crystal occlusion an order of magnitude more
# cheaply than building it would have cost: bound the mechanism arithmetically
# against the actual simulated state BEFORE writing the template.
#
# The named gap is that nothing in the library makes a BENZOYL side product, so
# every impurity this route can generate is small, polar and washable. A candidate
# has to clear one bar to be a purity mechanic at all: it must be LESS soluble at
# 275 K than the amount the route could possibly make of it. Otherwise it stays in
# the mother liquor and washes out with the salts, and writing the template buys a
# species and no mechanic.
print("""
  A candidate benzoyl side product is only a purity mechanic if it CO-CRYSTALLISES
  -- i.e. if the route can make more of it than 1 L of cold liquor will hold. The
  peroxide budget is what bounds "could possibly make": the oxygen comes from the
  headspace, and the whole cascade turns over about 7 mmol of it. So the threshold
  is 7 mmol against the solubility at 275 K.
""")
CANDIDATES = (
    ("benzoic acid (the product)", "OC(=O)c1ccccc1"),
    ("perbenzoic acid", "OOC(=O)c1ccccc1"),
    ("peracetic acid", "OOC(C)=O"),
    ("benzoyl peroxide", "O=C(OOC(=O)c1ccccc1)c1ccccc1"),
    ("benzaldehyde", "O=Cc1ccccc1"),
    ("benzyl alcohol", "OCc1ccccc1"),
)
BUDGET = 0.007          # mol, the route's whole peroxide turnover
print(f"  {'candidate':>26s} {'Tm / K':>7s} {'gamma':>10s} {'sol / mol/L':>12s}"
      f" {'g/L':>8s}  verdict at {BUDGET * 1000:.0f} mmol")
for name, smiles in CANDIDATES:
    key = Molecule.from_smiles(smiles).smiles
    try:
        record = thermo.get(key)
    except Exception:                                            # noqa: BLE001
        print(f"  {name:>26s} {'--':>7s} {'--':>10s} {'--':>12s} {'--':>8s}"
              "  REFUSED: no thermochemistry (Joback cannot fragment it)")
        continue
    probe = build_network([WATER, key], [], thermo=thermo, max_species=10)
    cell = Vessel(probe, volume=2.0, T=275.0, T_env=275.0, UA=50.0, kla=0.0,
                  k_diss=0.0, k_vent=0.0)
    cell.charge({WATER: 55.0, key: 1.0e-4})
    gamma = cell.activity_coefficients()[key]
    x_sat = float(
        cell.integrator.solubility(
            275.0, cell.integrator.activity_coefficients(cell._nL, 275.0)
        )[cell._idx[key]]
    )
    molar = x_sat * 55.5 / max(1.0 - x_sat, 1e-30)
    mass = molar * Molecule.from_smiles(key).molar_mass
    crops = "CO-CRYSTALLISES" if molar < BUDGET else "stays dissolved -- washable"
    print(f"  {name:>26s} {record.Tm:7.1f} {gamma:10.1f} {molar:12.4g} "
          f"{mass:8.2f}  {crops}")
print("""
  TWO OF THREE CANDIDATES ARE KILLED BY ARITHMETIC, WITHOUT WRITING A TEMPLATE.

    perbenzoic acid is the obvious one to reach for -- the route already makes
    hydrogen peroxide from its own liberated ethanol, and R-COOH + H2O2 is a real
    named equilibrium (it is how peracetic acid is manufactured). But it holds
    0.30 mol/L at 275 K against a 7 mmol budget: forty times too soluble. It would
    wash out exactly as the acetic acid does. DO NOT BUILD IT.

    peracetic acid is fully miscible and would be washable even in quantity, which
    is the useful contrast: one template acting on two substrates, and only the
    aromatic product could ever have been a problem.

    BENZOYL PEROXIDE is the one that works, and decisively -- 10 umol/L, so
    anything above about ten micromoles crops out with the product and cannot be
    washed off it. Its activity coefficient in water is 1.5e5, which is what a
    diaroyl peroxide should look like.

  SO THE RECOMMENDATION IS BOUNDED RATHER THAN OPEN. The threshold is 10 umol and
  the budget is 7 mmol, so the route has almost three orders of magnitude of
  headroom -- but it has to get there through TWO successive condensations
  (acid + H2O2 -> peracid, then peracid + acid -> diacyl peroxide), both
  unfavourable in water, and neither is currently in the library. Whether the
  product of two unfavourable equilibria clears 10 umol is the thing to measure
  next, and it is measurable with one template at a time.

  ⚠ AND NOTE WHICH WAY THE ARITHMETIC POINTS. Being unfavourable is not an
  objection here, it is the mechanism: the impurity only has to be a trace,
  because the threshold is a trace. That is the opposite of the occlusion case,
  where two small numbers multiplied could not make a big one.""")

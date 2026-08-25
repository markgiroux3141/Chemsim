"""M5: the named historical routes, run end to end from templates.

`data/catalog` holds 173 named synthetic routes and asks an unflattering
question of this simulator: how many of them could actually be integrated? At
the start of M5 the answer was **7**. It is now **25**, and this script runs the
ones whose species also price -- because "template-ready" and "runs" are two
different claims and the catalog counts them separately.

⚠ **FOURTEEN OF THE SEVENTEEN BELOW ARE TEMPLATE-READY ROUTES. THE LAST THREE
ARE NOT, AND ARE MARKED.** `aniline-route`, `paracetamol-route` and
`hydrogenation-margarine` each still need a class M5 did not build -- a
dissolving-metal reduction, a nitro reduction STOPPED at the hydroxylamine, and
an alkene isomerisation. They are here because the step shown is the template's
own demonstration, not because the route is finished. Saying so is the point:
the difference between "a template fires" and "a route runs" is the whole reason
the audit counts them apart.

⚠ **NOTHING BELOW SCRIPTS A YIELD.** Each entry charges a flask and integrates.
The products, the isomers, the equilibrium positions and the stoichiometric
ratios are what the network does. Four of them are worth watching for:

  * **Cannizzaro** gives benzyl alcohol and benzoate in a 1:1 ratio and consumes
    two aldehydes to do it. Nobody wrote the 2:1; it is the template's two
    aldehyde slots.
  * **DDT** comes out as ONE SIXTH of the chloral charged, because chlorobenzene's
    ortho, meta and para positions all match and the six isomers share the
    product. The historical product is a mixture for exactly that reason.
  * **Haber-Bosch** stops at 76% of the theoretical ammonia at 700 K and stays
    there. That is the equilibrium, derived by detailed balance from the
    formation data -- no ceiling is declared anywhere.
  * **Ethylene hydration** converts 2.9% per pass in the vapour phase, against a
    real plant's ~5%, and 99.7% in the liquid one. The difference is the standard
    state, and it is why that template takes a ``phase`` argument.

⚠ **RDKit may print "Explicit valence for atom # 1 O, 2, is greater than
permitted" once or twice while this runs, and that is the system working.** It is
RDKit's own log line for a rewrite whose product does not sanitise --
``ReactionTemplate.run`` catches the exception and discards that product set, the
same way a tertiary alcohol is silently refused by the oxidation template. The
species lists are unaffected. It is logged rather than suppressed because
suppressing RDKit's logger project-wide would also hide the ones that matter.

Run: ``python examples/named_routes.py`` (about half a minute).
"""

from __future__ import annotations

import time

from chemsim.network import build_network
from chemsim.properties import (
    VolatilityProvider,
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions import (
    aromatic_nitration,
    alkene_hydration,
    alkene_hydrogenation,
    alkyne_hydration,
    ammonia_synthesis,
    cannizzaro,
    ester_hydrolysis,
    friedel_crafts_hydroxyalkylation,
    glycoside_hydrolysis,
    knoevenagel_doebner,
    kolbe_schmitt,
    methanol_from_carbon_dioxide,
    methanol_from_carbon_monoxide,
    n_acylation,
    nitro_hydrogenation,
    perkin_condensation,
    williamson_ether_synthesis,
)
from chemsim.properties.mineral_data import MINERALS
from chemsim.reactions.library import SOLID_CATALYST_REFERENCE
from chemsim.vessel import Vessel

THERMO = electrolyte_provider()
VOLATILITY = VolatilityProvider()
DISSOCIATION = list(dissociation_templates())

WATER, SULFURIC, HYDROXIDE, SODIUM = "O", "OS(=O)(=O)O", "[OH-]", "[Na+]"
SUCROSE = (
    "OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)"
    "[C@@H](O)[C@@H]1O"
)
SALICIN = "OC[C@H]1O[C@@H](Oc2ccccc2CO)[C@H](O)[C@@H](O)[C@@H]1O"
GLUCOSE = "OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O"
BENZALDEHYDE, CINNAMIC = "O=Cc1ccccc1", "O=C(O)C=Cc1ccccc1"
OLEIC = "CCCCCCCC/C=C\\CCCCCCCC(=O)O"


# Each row is: label, the catalog route it comes from, the species charged, the
# templates, the flask, and the ONE number the route is about. Conditions are the
# catalog's own ``conditions`` column wherever it names a temperature.
ROUTES = [
    dict(
        route="invert-sugar", label="sucrose inversion",
        templates=lambda: [glycoside_hydrolysis()] + DISSOCIATION,
        seed=[SUCROSE, WATER, SULFURIC],
        charge={SUCROSE: 0.5, WATER: 40.0, SULFURIC: 0.1},
        T=360.0, seconds=3600.0, of=0.5, watch=(GLUCOSE, "glucose"),
    ),
    dict(
        route="salicin-hydrolysis", label="salicin -> salicyl alcohol",
        templates=lambda: [glycoside_hydrolysis()] + DISSOCIATION,
        seed=[SALICIN, WATER, SULFURIC],
        charge={SALICIN: 0.2, WATER: 40.0, SULFURIC: 0.1},
        T=360.0, seconds=3600.0, of=0.2, watch=("OCc1ccccc1O", "salicyl alcohol"),
    ),
    dict(
        route="aspirin-impurity", label="aspirin in a damp cabinet",
        templates=lambda: [ester_hydrolysis()],
        seed=["CC(=O)Oc1ccccc1C(=O)O", WATER],
        charge={"CC(=O)Oc1ccccc1C(=O)O": 0.1, WATER: 50.0},
        T=340.0, seconds=2.6e6, of=0.1,
        watch=("O=C(O)c1ccccc1O", "salicylic acid"),
    ),
    dict(
        route="cannizzaro-route", label="Cannizzaro disproportionation",
        templates=lambda: [cannizzaro()] + DISSOCIATION,
        seed=[BENZALDEHYDE, WATER, HYDROXIDE, SODIUM],
        charge={BENZALDEHYDE: 1.0, WATER: 40.0, HYDROXIDE: 2.0, SODIUM: 2.0},
        T=340.0, seconds=7200.0, of=1.0,
        watch=("OCc1ccccc1", "benzyl alcohol"),
        also=("O=C([O-])c1ccccc1", "benzoate"),
    ),
    dict(
        route="ddt-route", label="chloral + chlorobenzene",
        templates=lambda: [friedel_crafts_hydroxyalkylation()],
        seed=["Clc1ccccc1", "O=CC(Cl)(Cl)Cl", SULFURIC],
        charge={"Clc1ccccc1": 4.0, "O=CC(Cl)(Cl)Cl": 1.0, SULFURIC: 2.0},
        T=330.0, seconds=7200.0, of=1.0, build={"generations": 1},
        watch=("Clc1ccc(C(c2ccc(Cl)cc2)C(Cl)(Cl)Cl)cc1", "p,p'-DDT"),
    ),
    dict(
        route="ethanol-hydration", label="ethylene hydration, VAPOUR phase",
        templates=lambda: [alkene_hydration(phase="gas")],
        seed=["C=C", WATER], charge={"C=C": 2.0, WATER: 20.0}, gas=True,
        T=570.0, seconds=3600.0, of=2.0, watch=("CCO", "ethanol"),
    ),
    dict(
        route="knoevenagel-route", label="Knoevenagel-Doebner",
        templates=lambda: [knoevenagel_doebner()],
        seed=[BENZALDEHYDE, "OC(=O)CC(=O)O"],
        charge={BENZALDEHYDE: 1.0, "OC(=O)CC(=O)O": 1.2},
        T=390.0, seconds=7200.0, of=1.0, watch=(CINNAMIC, "cinnamic acid"),
    ),
    dict(
        route="perkin-route", label="Perkin condensation",
        templates=lambda: [perkin_condensation()],
        seed=[BENZALDEHYDE, "CC(=O)OC(C)=O"],
        charge={BENZALDEHYDE: 1.0, "CC(=O)OC(C)=O": 3.0},
        T=450.0, seconds=28800.0, of=1.0, watch=(CINNAMIC, "cinnamic acid"),
    ),
    dict(
        route="salicylic-kolbe", label="Kolbe-Schmitt carboxylation",
        templates=lambda: [kolbe_schmitt()] + DISSOCIATION,
        seed=["Oc1ccccc1", "O=C=O", WATER, HYDROXIDE, SODIUM],
        charge={"Oc1ccccc1": 1.0, "O=C=O": 3.0, WATER: 30.0,
                HYDROXIDE: 1.0, SODIUM: 1.0},
        T=400.0, seconds=7200.0, of=1.0,
        watch=("O=C([O-])c1ccccc1O", "salicylate"),
    ),
    dict(
        route="williamson-ether", label="phenoxide + iodomethane",
        templates=lambda: [williamson_ether_synthesis()] + DISSOCIATION,
        seed=["Oc1ccccc1", "CI", WATER, HYDROXIDE, SODIUM],
        charge={"Oc1ccccc1": 1.0, "CI": 1.0, WATER: 30.0,
                HYDROXIDE: 1.0, SODIUM: 1.0},
        T=350.0, seconds=7200.0, of=1.0, watch=("COc1ccccc1", "anisole"),
    ),
    dict(
        route="haber-bosch", label="ammonia synthesis, 700 K, over IRON",
        templates=lambda: [ammonia_synthesis()],
        seed=["N#N", "[H][H]"], charge={"N#N": 5.0, "[H][H]": 15.0}, gas=True,
        catalyst=("iron",),
        T=700.0, seconds=3600.0, of=10.0, watch=("N", "ammonia"),
    ),
    dict(
        route="methanol-synthesis", label="CO and CO2 hydrogenation",
        templates=lambda: [methanol_from_carbon_monoxide(),
                           methanol_from_carbon_dioxide()],
        seed=["[C-]#[O+]", "O=C=O", "[H][H]"],
        charge={"[C-]#[O+]": 3.0, "O=C=O": 1.0, "[H][H]": 12.0}, gas=True,
        catalyst=("copper",),
        T=520.0, seconds=3600.0, of=4.0, watch=("CO", "methanol"),
    ),
    dict(
        route="tnt-route", label="toluene -> TNT, three nitrations",
        templates=lambda: [aromatic_nitration()],
        seed=["Cc1ccccc1", "O[N+](=O)[O-]", WATER],
        charge={"Cc1ccccc1": 1.0, "O[N+](=O)[O-]": 3.5, WATER: 5.0},
        T=340.0, seconds=7200.0, of=1.0,
        build={"generations": 3, "max_species": 60},
        watch=("Cc1cc([N+](=O)[O-])cc([N+](=O)[O-])c1[N+](=O)[O-]", "2,4,6-TNT"),
    ),
    dict(
        route="aniline-route *", label="nitrobenzene -> aniline",
        templates=lambda: [nitro_hydrogenation()],
        seed=["O=[N+]([O-])c1ccccc1", "[H][H]"],
        charge={"O=[N+]([O-])c1ccccc1": 1.0, "[H][H]": 5.0},
        catalyst=("nickel",),
        T=470.0, seconds=3600.0, of=1.0, watch=("Nc1ccccc1", "aniline"),
    ),
    dict(
        route="paracetamol-route *", label="4-aminophenol + acetic anhydride",
        templates=lambda: [n_acylation()],
        seed=["Nc1ccc(O)cc1", "CC(=O)OC(C)=O"],
        charge={"Nc1ccc(O)cc1": 1.0, "CC(=O)OC(C)=O": 1.5},
        T=360.0, seconds=3600.0, of=1.0,
        watch=("CC(=O)Nc1ccc(O)cc1", "paracetamol"),
    ),
    dict(
        route="acetylene-acetaldehyde", label="Kucherov hydration",
        templates=lambda: [alkyne_hydration()],
        seed=["C#C", WATER, SULFURIC],
        charge={"C#C": 1.0, WATER: 40.0, SULFURIC: 0.5},
        T=370.0, seconds=7200.0, of=1.0, watch=("CC=O", "acetaldehyde"),
    ),
    dict(
        route="hydrogenation-margarine *", label="oleic -> stearic acid",
        templates=lambda: [alkene_hydrogenation()],
        seed=[OLEIC, "[H][H]"], charge={OLEIC: 1.0, "[H][H]": 5.0},
        catalyst=("nickel",),
        T=450.0, seconds=3600.0, of=1.0,
        watch=("CCCCCCCCCCCCCCCCCC(=O)O", "stearic acid"),
    ),
]


def run_one(spec: dict) -> tuple[int, int, float, list[tuple[str, float, float]]]:
    net = build_network(
        spec["seed"], spec["templates"](), thermo=THERMO,
        volatility=VOLATILITY, **spec.get("build", {}),
    )
    vessel = Vessel(
        net, volume=1.0, T=spec["T"], T_env=spec["T"], UA=1.0e4,
        kla=1.0, k_vent=0.0, k_diss=0.0,
    )
    vessel.charge(spec["charge"], phase="gas" if spec.get("gas") else "liquid")
    # THE CATALYST GOES IN THE SOLID BLOCK, and a route that needs one and does
    # not get it makes NOTHING. Five of these templates declare a heterogeneous
    # catalyst, so the charge is part of the recipe now rather than folded into a
    # barrier -- see ``ReactionTemplate.solid_catalyst``.
    if spec.get("catalyst"):
        vessel.charge(
            {MINERALS[m].lattice: SOLID_CATALYST_REFERENCE
             for m in spec["catalyst"]},
            phase="solid",
        )
    vessel.run(spec["seconds"])
    state = vessel.state()
    got = []
    for key in ("watch", "also"):
        if key in spec:
            smiles, name = spec[key]
            n = state.total(smiles)
            got.append((name, n, 100.0 * n / spec["of"]))
    return len(net.species), len(net.reactions), vessel.T, got


def main() -> None:
    print("=" * 78)
    print("NAMED ROUTES FROM data/catalog, INTEGRATED")
    print("=" * 78)
    print("   The catalog names 173 routes. 25 are template-ready; these are the")
    print("   ones whose species price as well. Every number is integrated.")
    print("   * = ONE STEP of a route that is not template-ready yet. See the")
    print("       module docstring for what each of the three still needs.")
    print()
    print(f"   {'route':26s} {'sp':>3s} {'rx':>4s}  {'product':22s} "
          f"{'mol':>9s} {'of charge':>10s}")
    print("   " + "-" * 73)
    started = time.perf_counter()
    for spec in ROUTES:
        n_sp, n_rx, _T, got = run_one(spec)
        first = True
        for name, mol, pct in got:
            label = spec["route"] if first else ""
            sp = f"{n_sp:3d}" if first else "   "
            rx = f"{n_rx:4d}" if first else "    "
            print(f"   {label:26s} {sp} {rx}  {name:22s} {mol:9.4f} {pct:9.1f}%")
            first = False
    print()
    print(f"   {len(ROUTES)} routes in {time.perf_counter() - started:.1f} s.")

    print()
    print("=" * 78)
    print("THE FOUR RESULTS THAT ARE NOT ARITHMETIC")
    print("=" * 78)
    print("""
   CANNIZZARO  benzyl alcohol and benzoate come out EQUAL, and each is ~47% of
     the aldehyde rather than ~94%. The template has two aldehyde slots, so two
     molecules are consumed per turn. Nobody declared the 2:1.

   DDT  p,p'-DDT is one sixth of the chloral charged. ``[cH]`` matches
     chlorobenzene's ortho, meta and para positions independently, so six
     isomers form and share the product. The historical insecticide was a
     mixture, and this is why -- not a purity model, a pattern.

   HABER-BOSCH  ammonia stops at 76% of theoretical at 700 K and does not move
     again. That is the equilibrium: detailed balance derived the reverse rate
     from the formation data, and the reaction is exothermic and loses moles, so
     it is self-limiting hot. No maximum temperature is declared anywhere in
     this project.

   ETHYLENE HYDRATION  2.9% per pass. A real plant gets about 5%, and is mostly
     a recycle loop for that reason. Run the SAME template in the liquid phase
     and it reads 99.7% -- the standard state is the difference, which is why
     ``alkene_hydration`` makes the caller choose.
""")


if __name__ == "__main__":
    main()

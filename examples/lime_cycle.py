"""M6 -- THE LIME CYCLE, and the first reaction that happens inside a crystal.

    NATURE                            THE KILN
      limestone  --red heat-->        quicklime  +  CO2 (up the chimney)
                                          |
                                          | + water
                                          v
                                     slaked lime  --+ CO2, months-->  limestone
                                     (mortar)                        (the wall)

`data/catalog` calls this three steps -- ``lime-cycle`` 1, 2 and 3 -- and
`solvay-process` step 5 is the first of them again. **Two declarations cover all
three**, because the second and third are the first two run backwards. Nothing
below scripts an outcome, and in particular:

  * there is no kiln TEMPERATURE anywhere. Panel 1 finds one, and it is where
    the CO2 pressure the crystals sit at overtakes what the room is pushing back
    with -- a number that comes out of the CRC formation pair.
  * there is no "sweep the kiln or it stalls" rule. Panel 3 is a sealed tube and
    it stalls at a few percent, because the reverse reaction exists.
  * SLAKING is not declared. It is panel 4, and it is the dehydration row run
    backwards.
  * CARBONATION is not declared either, and it is not even one row's reverse.
    Panel 5 is two rows sharing the quicklime in the solid block.

⚠ **AND THE FIRST IMPLEMENTATION OF THIS WAS WRONG IN A WAY WORTH KEEPING.**
M6's brief asked whether a solid-phase reaction is a third phase for the
kinetics kernel or a term of its own. Mass action was written first, on the
solid amounts, and a sealed tube settled at

    p / K  =  n(calcite) / n(quicklime)

exactly -- 3.0863 against 3.0863 at 1100 K. That is what a PURE SOLID HAVING
UNIT ACTIVITY forbids, and it is why ``PHASE_INDEX`` still has two entries.
``properties/solid_state.py`` carries the whole argument.
"""

from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.properties.mineral_data import MINERALS
from chemsim.vessel import Vessel

CALCITE = MINERALS["calcite"].lattice          # limestone
QUICKLIME = MINERALS["quicklime"].lattice      # burnt lime
PORTLANDITE = MINERALS["slaked lime"].lattice  # slaked lime, i.e. mortar
CO2 = "O=C=O"
WATER = "O"

# ⚠ THE LATTICE IS THE SPECIES YOU CHARGE, NOT ITS IONS, and that is the one
# thing to know before using this. Every other solid in this project sits in the
# solid block ION BY ION -- which is what makes a precipitation conserve matter
# by construction. A crystal that REACTS cannot: quicklime ion by ion needs the
# oxide ion, and ``[O-2]`` is in no aqueous table anywhere, because CaO does not
# dissolve to Ca2+ plus O2-, it HYDRATES. So the lattice had to become a species,
# and the two representations of CaCO3 are different species that do not know
# about each other.
LATTICES = (CALCITE, QUICKLIME, PORTLANDITE)

# ⚠ A SEALED TUBE CARRIES NO AIR, and leaving it out is not tidiness. A species
# that is in the network but absent from a flask with no vent, no liquid and no
# reaction has an identically ZERO Jacobian column, which is the ``num_jac``
# trap ``LAYER_REABSORB`` documents -- it can hand BDF a NaN Jacobian. It
# refuses loudly rather than lying (``check_raw_solution``), and modelling a
# sealed tube as sealed avoids it entirely.
SEALED = [*LATTICES, CO2, WATER]
OPEN = [*SEALED, "N#N", "O=O"]


def kiln(net, T, *, sealed, charge, volume=1.0):
    v = Vessel(
        net, volume=volume, T=T, T_env=T, UA=1.0e4,
        k_vent=0.0 if sealed else 1.0e3,
        atmosphere={} if sealed else {"N#N": 0.79, "O=O": 0.21},
    )
    v.charge(charge, phase="solid")
    if not sealed:
        v.fill_headspace()          # an open kiln starts full of air, not vacuum
    return v


def held(v, smiles):
    return v.solids().get(smiles, 0.0)


def main() -> None:
    thermo = ThermochemistryProvider()
    open_net = build_network(OPEN, [], thermo=thermo)
    sealed_net = build_network(SEALED, [], thermo=thermo)

    print("=" * 74)
    print("PANEL 1 -- what the two declarations are, and the kiln temperature")
    print("           NOBODY TYPED")
    print("=" * 74)
    v = Vessel(open_net, volume=1.0, T=1200.0)
    print(v.solid_state_report())
    print()
    print("   Both of those temperatures are solved for, not stored: K(T) is the")
    print("   gas pressure a pair of crystals sits at, and the reaction can only")
    print("   run to completion once it beats the room. Literature puts calcite")
    print("   at ~1170 K and slaked lime at ~785 K, so this table runs its kilns")
    print("   30-50 K cool -- which is what `dCp = 0` costs, stated rather than")
    print("   hidden. A dCp correction was built and MEASURED: it improves one")
    print("   row by 20 K and makes the other WORSE by 10, so it was dropped.")

    print()
    print("=" * 74)
    print("PANEL 2 -- THE GATE. Under one bar of air, does limestone burn?")
    print("=" * 74)
    print(f"   {'T / K':>7} {'K(T) / bar':>11} {'vs room':>9} "
          f"{'converted':>10}   what a kiln operator sees")
    for T in (1000.0, 1073.0, 1100.0, 1150.0, 1200.0):
        v = kiln(open_net, T, sealed=False, charge={CALCITE: 0.1})
        K = float(v.solid_state_arrays.equilibrium_pressure(T)[0])
        v.run(20_000.0)
        conv = (0.1 - held(v, CALCITE)) / 0.1
        verdict = "nothing happens" if conv < 0.5 else "BURNS to quicklime"
        print(f"   {T:7.0f} {K:11.4f} {'below' if K < v.P_ambient else 'ABOVE':>9} "
              f"{conv * 100:9.2f}%   {verdict}")
    print()
    print("   The threshold sits between 1100 and 1150 K and nothing declares")
    print("   it. It is exactly where K(T) crosses 1.013 bar. A forward-only")
    print("   reaction would have calcined every row in this table.")

    print()
    print("=" * 74)
    print("PANEL 3 -- SEAL THE TUBE and it stalls. This is the mechanic that a")
    print("           reaction without a reverse cannot have.")
    print("=" * 74)
    print(f"   {'T / K':>7} {'converted':>10} {'p(CO2) / bar':>13} "
          f"{'K(T) / bar':>11}   {'p/K':>7}")
    for T in (900.0, 1000.0, 1100.0, 1200.0):
        v = kiln(sealed_net, T, sealed=True, charge={CALCITE: 0.1})
        v.run(60_000.0)
        K = float(v.solid_state_arrays.equilibrium_pressure(T)[0])
        p = v.partial_pressures()[CO2]
        print(f"   {T:7.0f} {(0.1 - held(v, CALCITE)) / 0.1 * 100:9.2f}% "
              f"{p:13.5f} {K:11.5f}   {p / K:7.5f}")
    print()
    print("   Forward-only reads 100% on every one of those rows. And the last")
    print("   column is the claim a pure solid has UNIT ACTIVITY: four")
    print("   different conversions, one pressure each, all of them K(T).")
    print()
    print("   The same charge test, which is what caught the first attempt:")
    for charge in (0.05, 0.2, 0.8):
        v = kiln(sealed_net, 1100.0, sealed=True, charge={CALCITE: charge})
        v.run(60_000.0)
        ratio = held(v, CALCITE) / max(held(v, QUICKLIME), 1e-30)
        print(f"      charged {charge:4.2f} mol -> n(calcite)/n(quicklime) = "
              f"{ratio:6.2f}, p(CO2) = {v.partial_pressures()[CO2]:.6f} bar")
    print("   Mass action would have made that pressure track the ratio.")

    print()
    print("=" * 74)
    print("PANEL 4 -- SLAKING, which nothing declares: it is the dehydration")
    print("           row run backwards.")
    print("=" * 74)
    v = Vessel(sealed_net, volume=1.0, T=400.0, T_env=400.0, UA=1.0e4,
               k_vent=0.0, atmosphere={})
    v.charge({QUICKLIME: 0.05}, phase="solid")
    v.charge({WATER: 0.05}, phase="gas")
    for t in (0.0, 10.0, 100.0, 1000.0):
        if t > v.t:
            v.run(t - v.t)
        print(f"   t = {v.t:6.0f} s   quicklime {held(v, QUICKLIME):.6f}   "
              f"slaked lime {held(v, PORTLANDITE):.6f}   "
              f"p(H2O) {v.partial_pressures()[WATER]:.5f} bar")
    print()
    print("   !! Priced against water VAPOUR. Slake with LIQUID water and the")
    print("   condensation enthalpy comes from the vessel's own evaporation")
    print("   term instead -- which is why this row must not also carry it.")

    print()
    print("=" * 74)
    print("PANEL 5 -- CARBONATION: the wall setting. Ca(OH)2 + CO2 -> CaCO3.")
    print("           Not declared, and not any single row's reverse either.")
    print("=" * 74)
    v = Vessel(sealed_net, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4,
               k_vent=0.0, atmosphere={})
    v.charge({PORTLANDITE: 0.02}, phase="solid")
    v.charge({CO2: 0.02}, phase="gas")
    for t in (0.0, 100.0, 1000.0, 50_000.0):
        if t > v.t:
            v.run(t - v.t)
        print(f"   t = {v.t:7.0f} s   slaked {held(v, PORTLANDITE):.6f}   "
              f"quick {held(v, QUICKLIME):.6f}   "
              f"LIMESTONE {held(v, CALCITE):.6f}   "
              f"p(CO2) {v.partial_pressures()[CO2]:.4f}  "
              f"p(H2O) {v.partial_pressures()[WATER]:.4f}")
    total = held(v, CALCITE) + held(v, QUICKLIME) + held(v, PORTLANDITE)
    print(f"   calcium: {total:.9f} mol against 0.020000000 charged")
    print()
    print("   Limestone, from mortar and air, through a quicklime intermediate")
    print("   that neither declaration mentions in that role. Two rows sharing")
    print("   one solid block is all that is going on.")

    print()
    print("=" * 74)
    print("PANEL 6 -- what the kiln COSTS, which is the energy balance M12")
    print("           built the instrument for.")
    print("=" * 74)
    v = kiln(open_net, 1200.0, sealed=False, charge={CALCITE: 0.1})
    v.run(300.0)
    print(v.energy_report())
    print()
    print("   The `solid-state` line is the charge absorbing its own reaction")
    print("   enthalpy and the wall line is the burner supplying it. They are")
    print("   equal and opposite because the kiln is being held at 1200 K, and")
    print("   that is the fuel bill of a lime kiln falling out of a formation")
    print("   pair rather than being quoted.")

    print()
    print("=" * 74)
    print("PANEL 7 -- and a crystal STILL cannot dissolve.")
    print("=" * 74)
    v = Vessel(sealed_net, volume=1.0, T=298.15, k_vent=0.0, atmosphere={})
    v.charge({CALCITE: 0.01}, phase="solid")
    v.charge({WATER: 5.0})
    v.run(1000.0)
    print("   0.01 mol of limestone under 90 mL of water for 1000 s:")
    print(f"     still solid      {held(v, CALCITE):.9f} mol")
    print(f"     in solution      {v.state().n_liquid[CALCITE]:.9e} mol")
    print()
    print("   M6 does not soften `mineral_data`'s verdict, it works beside it.")
    print("   The only route this engine has from a solid into solution is the")
    print("   ideal-solubility fusion law, and that law is measured wrong for a")
    print("   lattice by up to 407x IN BOTH DIRECTIONS. So a crystal may now")
    print("   react while staying a crystal, and it still may not dissolve.")
    print("   The two questions never touch.")

    print()
    print("""WHAT THIS DEMONSTRATES

   ONE MEASUREMENT DECIDED THE ARCHITECTURE. A pure solid has unit activity, so
   mass action on the solid amounts gives an equilibrium pressure that tracks
   n_A/n_B -- built, measured at 3.0863 against 3.0863, and replaced. Solid-state
   reaction is a TERM, next to precipitation, for the same reason precipitation
   is one.

   Ea IS DERIVED, NOT DECLARED. A decomposition whose reverse is barrierless has
   Ea = dH, which is also the floor detailed_balance enforces everywhere else
   here. Calcite comes out at 179.2 kJ/mol against experimental values quoted at
   170-200, and the reverse rate constant loses its temperature dependence
   entirely -- which is what keeps a cold flask full of CO2 solvable.

   FOUR MECHANICS THAT NOBODY WROTE: a kiln temperature, a sealed tube that
   stalls, slaking, and carbonation.

   TWO DECLARATIONS FOR THREE CATALOG STEPS, and M5's standard is why there are
   two: the catalog calls both `calcination` and they are DIFFERENT MECHANISMS
   -- decarbonation and dehydration -- so crediting the class on one of them
   would have been M1's `deprotonation` mistake again.

   AND ONE CLASS STILL REFUSED. `roasting` is one mechanism across all five of
   its rows, and none of the five is complete: only ZnS prices among the
   sulfides and NONE of the oxides does. That is a data refusal, not an engine
   one -- but roasting also CONSUMES a gas, and the affinity form above is not
   a rate law for that. It is the case that still wants a third PHASE_INDEX
   entry, and so are the five heterogeneous templates that fold a catalyst into
   an apparent barrier.""")


if __name__ == "__main__":
    main()

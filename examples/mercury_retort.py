"""A ROUTE NOBODY DECLARED -- mercury out of cinnabar, from two half-reactions.

    NATURE                       THE RETORT (900 K)
      cinnabar  --air-->  [montroydite]  -->  mercury VAPOUR  +  SO2
      (HgS ore)            never seen           |
                                                | condenser
                                                v
                                          liquid mercury

The catalog has read ``mercury-sulfide + oxygen -> mercury + sulfur-dioxide``
since the corpus was written. S1 built the roast, discovered it makes the OXIDE,
and re-labelled the row ``roasting-to-metal`` rather than claim it -- naming what
was missing as "a second reaction nobody built".

The second reaction is one more row of ``SOLID_STATE_REACTIONS``, three lines
long. Neither declaration mentions the other. They share one crystal:

    properties/surface.py       2 HgS + 3 O2 -> 2 HgO + 2 SO2
    properties/solid_state.py   2 HgO        -> 2 Hg  +   O2
    ------------------------------------------------------------
    what this file runs           HgS +   O2 ->   Hg  +   SO2

Nothing below scripts an outcome:

  * nobody wrote "the oxide is an intermediate". Panel 2 never catches it above
    6e-7 mol of a 0.02 mol charge, because its own clock at 900 K is a quarter
    of a second against the roast's hour and a half.
  * nobody wrote "a retort gives the metal and a cooler one gives the oxide".
    Panel 4 is the same two declarations at five temperatures, and the oxide
    goes from 2e-6 of the product to 91% of it. That is two Arrhenius factors
    with different exponents, written a milestone apart.
  * nobody wrote "the oxide cannot come back". Panel 3 cools the retort 289 K
    BELOW the oxide's own decomposition threshold and it does not re-form, for
    the honest reason: there is none left to grow on, and this engine cannot
    nucleate a crystal out of nothing.

WHAT IT COST: mercury as a curated element (panel 5), and one bound in
``SolidStateArrays.units`` -- this is the first row here whose products are ALL
GAS, and the minimum over an empty product side was ``+inf``.
"""

from chemsim.constants import R, R_L_BAR
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties import solid_state as ss
from chemsim.properties import standard_state
from chemsim.properties import surface as sf
from chemsim.properties.element_data import ELEMENTAL
from chemsim.properties.mineral_data import MINERALS
from chemsim.vessel import Vessel
from chemsim.vessel.vessel import build_solid_state_arrays

CINNABAR = MINERALS["cinnabar"].lattice            # HgS -- vermilion, the ore
MONTROYDITE = MINERALS["montroydite"].lattice      # HgO
HG, O2, SO2, N2 = "[Hg]", "O=O", "O=S=O", "N#N"
ORE = [CINNABAR, MONTROYDITE, HG, O2, SO2, N2]

# The tolerance every number here is measured at. S2 swept the default across
# eleven examples and found nothing quotable moves; this file follows the
# roasting example's setting anyway, because both of its terms are stiff.
CONVERGED = dict(rtol=1.0e-8, atol=1.0e-11)

DECOMPOSITION = "oxide-thermal-decomposition"


def retort(net, T, *, charge, volume=10.0, oxygen_bar=1.0):
    """A SEALED retort with oxygen enough that nothing is O2-limited.

    Sealed, unlike S1's roaster, and for a reason: a vent carries mercury OUT of
    the flask, and the point of this file is that what comes out of the crystal
    is exactly what the catalog row says.
    """
    v = Vessel(net, volume=volume, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge({CINNABAR: charge}, phase="solid")
    v.charge({O2: oxygen_bar * volume / (R_L_BAR * T)}, phase="gas")
    return v


def main() -> None:
    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    net = build_network(ORE, [], thermo=thermo, volatility=vol)
    roast = sf.price(
        next(d for d in sf.SURFACE_REACTIONS if d.name == "cinnabar-roasting"),
        thermo,
    )
    dec = ss.price(
        next(d for d in ss.SOLID_STATE_REACTIONS if d.name == DECOMPOSITION),
        thermo,
    )

    print("=" * 74)
    print("PANEL 1 -- TWO DECLARATIONS, AND NEITHER OF THEM IS THE ROUTE")
    print("=" * 74)
    v = retort(net, 900.0, charge=0.02)
    print("   a gas ARRIVING at the crystal   (properties/surface.py)")
    print("      " + v.surface_report())
    print()
    print("   a reaction INSIDE the crystal   (properties/solid_state.py)")
    print("      " + v.solid_state_report())
    print()
    print("   2 HgS + 3 O2 -> 2 HgO + 2 SO2      the first one")
    print("   2 HgO        -> 2 Hg  +   O2       the second one")
    print("   " + "-" * 52)
    print("     HgS +   O2 ->   Hg  +   SO2      the catalog's own row")
    print()
    print("   The oxide cancels. Nothing in either module knows that, and the")
    print("   two barriers were written a milestone apart for different")
    print("   reactions -- 150 kJ/mol DECLARED for a sulfide surface, and")
    print(f"   {dec.Ea / 1000:.1f} kJ/mol DERIVED as the decomposition's own enthalpy.")

    print()
    print("=" * 74)
    print("PANEL 2 -- THE RETORT. It runs the row, and the oxide is INVISIBLE.")
    print("=" * 74)
    v = retort(net, 900.0, charge=0.02)
    charged_O2 = 10.0 / (R_L_BAR * 900.0)
    peak = 0.0
    for _ in range(20):
        v.run(2_000.0, **CONVERGED)
        peak = max(peak, v.state().total(MONTROYDITE))
    v.run(360_000.0, **CONVERGED)
    st = v.state()
    print("   sealed 10 L retort, 1 bar of oxygen, 0.02 mol of cinnabar, 900 K")
    print()
    print(f"      cinnabar left      {st.total(CINNABAR):18.12f} mol")
    print(f"      MERCURY            {st.total(HG):18.12f} mol")
    print(f"      sulfur dioxide     {st.total(SO2):18.12f} mol")
    print(f"      oxygen consumed    {charged_O2 - st.total(O2):18.12f} mol")
    print(f"      montroydite, MOST  {peak:18.12f} mol   (of 20 samples)")
    print()
    print("   One mole of mercury and one of SO2 per mole of ore, on one mole of")
    print("   oxygen. That is the catalog row coefficient for coefficient, and")
    print("   the declarations that produced it are 2:3:2:2 and 2:2:1.")
    print()
    tau_roast = sf.time_constant(roast, 900.0, 1.0 / (R_L_BAR * 900.0)) / 2.0
    tau_dec = 1.0 / (dec.A * pow(2.718281828459045, -dec.Ea / (R * 900.0)))
    print(f"   the roast's clock at 900 K   {tau_roast:12.1f} s")
    print(f"   the oxide's clock at 900 K   {tau_dec:12.4f} s")
    print(f"   ratio                        {tau_roast / tau_dec:12.0f} x")
    print("   -- which is why the intermediate is real and never accumulates.")
    print("   Its standing inventory is the roast's rate times its own clock, so")
    print("   it FALLS as the ore is consumed rather than peaking: 8e-7 mol at")
    print("   the start and 3.4e-8 by 20 ks, never more than 4e-5 of the charge.")

    print()
    print("=" * 74)
    print("PANEL 3 -- CONDENSE IT. And the oxide does NOT come back.")
    print("=" * 74)
    print(f"   at 900 K:  mercury in the gas {st.n_gas[HG]:.9f} mol, "
          f"in the liquid {st.n_liquid[HG]:.9f}")
    for T in (500.0, 400.0):
        v.set_environment(T)
        v.run(50_000.0, **CONVERGED)
        st = v.state()
        print(f"   at {T:.0f} K:  mercury in the gas {st.n_gas[HG]:.9f} mol, "
              f"in the liquid {st.n_liquid[HG]:.9f}")
    print()
    print("   Mercury boils at 629.8 K, so it is a gas in the retort and a POOL")
    print("   in the receiver. That is the whole of what a retort is for, and it")
    print("   needs a vapour-pressure curve good at 400 K -- see panel 6.")
    print()
    frac, per_species = v.held_ideal()
    print(f"   ...AND THE POOL SAYS SO: {100 * frac:.2f}% of this liquid is HELD")
    print("   IDEAL. Liquid mercury has no UNIFAC groups -- a metal is not a set")
    print("   of organic fragments -- so its activity coefficient is DECLARED 1")
    print("   rather than assumed, which is what M4 built that flag for.")
    print(f"      dissolved in it: O2 {st.n_liquid[O2]:.3e} mol, "
          f"SO2 {st.n_liquid[SO2]:.3e} mol")
    print("   Those two are the visible cost. Their Henry constants were measured")
    print("   IN WATER and transfer through a ratio of activity coefficients that")
    print("   is 1 here, so the model dissolves gases in a liquid metal about as")
    print("   readily as in water. It is 0.14% of the SO2 and it is a wrong")
    print("   number, bounded and named rather than hidden.")
    print()
    arr, _ = build_solid_state_arrays(net.species)
    i = arr.names.index(DECOMPOSITION)
    print(f"   montroydite now:   {st.n_solid[MONTROYDITE]:.12f} mol, at 400 K")
    print(f"   its threshold is:  {float(arr.threshold_temperature(1.013)[i]):.1f} K")
    print()
    print("   So the flask is 289 K BELOW the temperature at which the oxide is")
    print("   the stable form, full of mercury vapour and oxygen -- and no oxide")
    print("   forms. Not a clip and not a gate: the reverse of this term is")
    print("   bounded by the crystal it has to grow ON, and there is none. This")
    print("   engine cannot nucleate a solid out of nothing (S3 named that), and")
    print("   this is what that gap looks like when it is stated honestly.")

    print()
    print("=" * 74)
    print("PANEL 4 -- COOL THE FURNACE and the SAME two rows give the OXIDE")
    print("=" * 74)
    print("   fraction of the mercury released from the cinnabar that is still")
    print("   sitting in the solid block as the oxide:")
    print()
    print(f"   {'T/K':>6} {'duration/s':>12} {'converted':>10} "
          f"{'HgO/mol':>12} {'Hg/mol':>12} {'oxide share':>12}")
    for T, duration in ((900.0, 2.0e4), (773.0, 2.0e5), (700.0, 1.0e6),
                        (650.0, 5.0e6), (600.0, 5.0e7)):
        w = retort(net, T, charge=0.02)
        w.run(duration, **CONVERGED)
        s = w.state()
        released = s.total(MONTROYDITE) + s.total(HG)
        print(f"   {T:6.0f} {duration:12.3g} {1 - s.total(CINNABAR) / 0.02:10.5f} "
              f"{s.total(MONTROYDITE):12.4e} {s.total(HG):12.4e} "
              f"{s.total(MONTROYDITE) / released:12.6f}")
    print()
    print("   Nothing gates on temperature in either term. The decomposition's")
    print("   barrier is twice the roast's, so cooling slows it far faster, and")
    print("   the two clocks cross at 611.7 K under a bar of oxygen. Above it a")
    print("   retort makes metal; below it the same retort makes a red oxide.")

    print()
    print("=" * 74)
    print("PANEL 5 -- THE OXIDE ALONE, AND THE BOUND THIS ROW COST")
    print("=" * 74)
    w = Vessel(net, volume=1.0, T=900.0, T_env=900.0, UA=1.0e4, k_vent=0.0)
    w.charge({MONTROYDITE: 0.5}, phase="solid")
    w.charge({N2: 1.0 / (R_L_BAR * 900.0)}, phase="gas")
    w.run(60.0, **CONVERGED)
    s = w.state()
    p = w.partial_pressures()
    Q = p[HG] ** 2 * p[O2]
    K = float(arr.equilibrium_pressure(900.0)[i])
    print("   0.5 mol of montroydite, sealed in ONE litre at 900 K:")
    print(f"      oxide left     {s.total(MONTROYDITE):.9f} mol "
          f"({100 * (1 - s.total(MONTROYDITE) / 0.5):.1f}% converted)")
    print(f"      Q = p_Hg^2 p_O2 = {Q:12.1f} bar^3")
    print(f"      K(900 K)        = {K:12.1f} bar^3")
    print()
    print("   It STOPS, at Q = K, and it stops there however much crystal is")
    print("   left -- which is the property the affinity form exists to have.")
    print()
    print("   AND THIS RUN USED TO DIE. This is the first row in the table whose")
    print("   products are all gas, so the reverse bound -- a minimum over the")
    print("   solids FORMED -- was a minimum over an empty set, i.e. +inf. The")
    print("   instant Q crossed K the term returned -inf and BDF got a NaN")
    print("   Jacobian: 'array must not contain infs or NaNs'. At 0.05 mol in")
    print("   the same flask Q never reaches K, so the failure had a CHARGE")
    print("   threshold as well as a temperature one, and the small charge is")
    print("   the one an example would have been written with.")

    print()
    print("=" * 74)
    print("PANEL 6 -- MERCURY, and why it was refused here until now")
    print("=" * 74)
    rec = ELEMENTAL[HG]
    data = thermo.get(HG)
    shift = standard_state.shift(HG, vol, 298.15)
    print(f"   Hf(g) {rec.Hf:+7.2f}   Gf(g) {rec.Gf:+7.3f} kJ/mol, "
          f"reference phase {rec.reference_phase!r}")
    print()
    print("   It was refused TWICE OVER, and both refusals were about the")
    print("   representation rather than the chemistry:")
    print("     - 'a metallic lattice'. Mercury's reference state is a LIQUID")
    print("       with a boiling point, which the liquid block holds.")
    print("     - 'the ideal-gas record is the ATOM, not the substance'. True of")
    print("       [C] and [S] and [Fe]. Mercury's vapour IS the atom.")
    print()
    print("   TWO FREE EXACT CHECKS CAME WITH IT, and nothing was fitted:")
    cp = sum(c * 298.15 ** k for k, c in enumerate(rec.Cp_coeffs))
    print(f"     - Cp(298 K) = {cp:.3f} against 5R/2 = {2.5 * R:.3f} J/(mol K)")
    print("       exactly, at every temperature, because a monatomic gas has no")
    print("       modes to excite. Every other Cp in that table is a fit.")
    print(f"     - Gf(g) {data.Gf:+.3f} + RT ln(Psat/P0) {shift.dGf:+.3f} "
          f"= {data.Gf + shift.dGf:+.3f} kJ/mol,")
    print("       which must be zero for a reference state. CRC's formation pair")
    print("       and the WebBook's vapour-pressure curve never met.")
    print()
    print("   AND ONE ESTIMATOR HAD TO GO. Lee-Kesler builds every other")
    print("   element's vapour pressure here from Tb/Tc/Pc, and over a liquid")
    print("   METAL it reads 38.3 kPa at 523 K against CRC's 10.0 -- 3.8x, while")
    print("   agreeing at the boiling point to five figures because it is")
    print("   ANCHORED there. Panel 3 is a condenser and would have been wrong")
    print("   by that factor. The curated Antoine that replaced it is within 2%")
    print("   of CRC over five decades of pressure.")
    print()
    print("   the residual above without it:  +2.808 kJ/mol")
    print(f"   the residual above with it:     {data.Gf + shift.dGf:+.3f} kJ/mol")


if __name__ == "__main__":
    main()

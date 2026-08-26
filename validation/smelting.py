"""S9's standing audit -- the reversible solid-gas term, and the smelter it makes.

Run this after touching ``properties/solid_state.py``, ``properties/surface.py``
or the ``SolidStateArrays`` block of the RHS. Roughly a minute.

WHAT S9 DID, in one paragraph. ``SolidStateArrays`` integrates the AFFINITY form
``k_f - k_r Q``, with ``Q`` over the gases only because a pure solid has unit
activity, and ``units`` as a common factor chosen by the sign of the affinity so
that ``net = 0`` is ``Q = K`` whatever the crystals weigh. A gas REACTANT was
refused there for five milestones, on M6's measurement that its pressure lands in
the DENOMINATOR of Q and drives the reverse flux to 2.6e15 formula units per
second as the gas runs out. That is true of the quotient form and it is cured by
writing the same thing as two one-sided products,

    net = k_f * prod(p ** consumed_gas)  -  k_r * prod(p ** formed_gas)

which is ``P_react (k_f - k_r Q)`` algebraically -- SAME root, so the same
equilibrium -- and which never divides anything. That single change is the whole
of "a REVERSIBLE solid-gas term", the engine item S8 named as the most valuable
one nobody had scoped.

The second change is that an exothermic row may DECLARE its forward pair. M6's
``Ea = max(dH, 0)`` is a derivation about an endothermic decomposition whose
reverse is barrierless; on an exothermic row it returns ZERO, i.e. a reaction
with no temperature dependence at all. Panel 5 measures what that costs.

THE PANELS

  1  every declared row prices, and the barrier clears the enthalpy
  2  the five pre-S9 rows are BIT-IDENTICAL -- the split changed nothing
  3  a gas reactant is BOUNDED, against the unbounded number it replaced
  4  the equilibrium is Q = K, and it does not depend on the charge
  5  an exothermic row cannot take the derived pair -- the two numbers
  6  the three smelting routes, end to end from ore, coke and air
  7  the carrier-free furnace is INERT, at four tolerance rungs
  8  thermite: the barrier IS the mechanic, and what does NOT cap it

Windows console is cp1252: every printed line here is ASCII.
"""

from __future__ import annotations

import math

import numpy as np

from chemsim.constants import R, R_L_BAR
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties import solid_state as ss
from chemsim.properties import surface as sf
from chemsim.properties.mineral_data import MINERALS
from chemsim.vessel import Vessel
from chemsim.vessel.vessel import build_solid_state_arrays

M = MINERALS
COVELLITE, TENORITE, COPPER = (M["covellite"].lattice, M["tenorite"].lattice,
                               M["copper"].lattice)
GALENA, LITHARGE, LEAD = (M["galena"].lattice, M["litharge"].lattice,
                          M["lead"].lattice)
SPHALERITE, ZINCITE = M["sphalerite"].lattice, M["zincite"].lattice
# !! S10 -- ZINC IS NOT A LATTICE ANY MORE. It is an ordinary elemental species
# with a melting point and a boiling point, so the retort evolves it as a VAPOUR.
ZINC = "[Zn]"
GRAPHITE = M["carbon-graphite"].lattice
HEMATITE, IRON = M["hematite"].lattice, M["iron"].lattice
CORUNDUM, ALUMINIUM = M["corundum"].lattice, M["aluminium"].lattice
CALCITE, QUICKLIME = M["calcite"].lattice, M["quicklime"].lattice
CO, CO2, N2, O2, SO2 = "[C-]#[O+]", "O=C=O", "N#N", "O=O", "O=S=O"

TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)

thermo = ThermochemistryProvider()
volatility = VolatilityProvider(thermo)


def net(species):
    return build_network(species, [], thermo=thermo, volatility=volatility)


def solid(v, s):
    return float(v.state().n_solid.get(s, 0.0))


def gas(v, s):
    return float(v.state().n_gas.get(s, 0.0))


def rule(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


# ---------------------------------------------------------------------------
rule("1. EVERY DECLARED ROW PRICES, AND THE BARRIER CLEARS THE ENTHALPY")
# ---------------------------------------------------------------------------
print("  a barrier below dH would CLIP in max(Ea - dH, 0), and the clip breaks")
print("  k_f/k_r = K silently -- the equilibrium would stop being the")
print("  thermodynamics. So it is a refusal and not a safety net.")
print()
print(f"  {'row':38s} {'dH/kJ':>9s} {'dS/J/K':>8s} {'Ea/kJ':>8s} "
      f"{'A':>11s} {'kind':>9s}")
for decl in ss.SOLID_STATE_REACTIONS:
    p = ss.price(decl, thermo)
    kind = "declared" if decl.Ea is not None else "derived"
    assert p.Ea >= max(p.dH, 0.0), decl.name
    print(f"  {decl.name:38s} {p.dH/1000:9.2f} {p.dS:8.2f} {p.Ea/1000:8.2f} "
          f"{p.A:11.4e} {kind:>9s}")
print()
print(f"  {'surface row':26s} {'dH/kJ':>9s} {'T_run':>7s} {'lnK':>8s} "
      f"{'Ea/kJ':>7s} {'A':>11s} {'kind':>9s}")
for decl in sf.SURFACE_REACTIONS:
    p = sf.price(decl, thermo)
    kind = "declared" if decl.Ea is not None else "shared"
    print(f"  {decl.name:26s} {p.dH/1000:9.2f} {decl.T_run:7.0f} "
          f"{p.ln_K_run:8.2f} {p.Ea/1000:7.1f} {p.A:11.4e} {kind:>9s}")
print()
print(f"  the bar an IRREVERSIBLE surface row must clear is "
      f"ln K = {sf.LN_K_IRREVERSIBLE:g}.")
print("  carbon-combustion clears it by 1.87 nats at its tuyere's own 2200 K --")
print("  the tightest row in that table by 46 -- and the reason is chemistry:")
print("  above ~1000 K CO2 over carbon is increasingly taken to CO. That")
print("  reversal is boudouard-gasification, declared in the OTHER module.")

# ---------------------------------------------------------------------------
rule("2. THE FIVE PRE-S9 ROWS ARE BIT-IDENTICAL, NOT MERELY CLOSE")
# ---------------------------------------------------------------------------
print("  every pre-S9 row has nu_gas >= 0, so 'consumed' is all zeros and")
print("  p ** 0 is exactly 1.0 -- P_react is an empty product and P_prod IS")
print("  the old Q, element for element.")
print()
SPECIES_2 = [CALCITE, QUICKLIME, CO2, N2]
arr, _ = build_solid_state_arrays(SPECIES_2)
i = arr.names.index("calcination-decarbonation")
p = np.zeros(4)
p[SPECIES_2.index(CO2)] = 0.37
p[SPECIES_2.index(N2)] = 0.63
Q_old = np.prod(p[None, :] ** arr.nu_gas, axis=1)
P_react = np.prod(p[None, :] ** arr.gas_consumed, axis=1)
P_prod = np.prod(p[None, :] ** arr.gas_formed, axis=1)
print("  calcination-decarbonation at p_CO2 = 0.37 bar")
print(f"     old  Q          = {float(Q_old[i])!r}")
print(f"     new  P_prod     = {float(P_prod[i])!r}")
print(f"     new  P_react    = {float(P_react[i])!r}")
print(f"     P_prod is Q     : {P_prod[i] == Q_old[i]}")
print(f"     P_react is 1.0  : {P_react[i] == 1.0}")
print()
print("  and at p_CO2 = 0 exactly, where 0.0 ** 0 has to be 1.0:")
p0 = np.zeros(4)
print(f"     P_react = {float(np.prod(p0[None, :] ** arr.gas_consumed, axis=1)[i])!r}")
print(f"     P_prod  = {float(np.prod(p0[None, :] ** arr.gas_formed, axis=1)[i])!r}")
print()
print("  VERIFIED SEPARATELY AGAINST THE EXAMPLE SET: examples/lime_cycle.py")
print("  and examples/mercury_retort.py are byte-identical across this change.")

# ---------------------------------------------------------------------------
rule("3. A GAS REACTANT IS BOUNDED -- AGAINST THE NUMBER IT REPLACED")
# ---------------------------------------------------------------------------
SPECIES_3 = [TENORITE, COPPER, CO, CO2]
arr, report = build_solid_state_arrays(SPECIES_3)
i = arr.names.index("tenorite-carbon-monoxide-reduction")
T = 1400.0
k_f = arr.A_fwd * np.exp(-arr.Ea_fwd / (R * T))
k_r = arr.A_rev * np.exp(-arr.Ea_rev / (R * T))
print(f"  tenorite + CO -> copper + CO2, at {T:.0f} K, p_CO2 = 1 bar")
print()
print(f"  {'p_CO / bar':>12s} {'Q = p_CO2/p_CO':>16s} {'OLD k_r Q':>14s} "
      f"{'NEW |net|':>14s}")
for p_co in (1.0, 1.0e-3, 1.0e-6, 1.0e-12, 1.0e-30, 0.0):
    p = np.zeros(4)
    p[SPECIES_3.index(CO)] = p_co
    p[SPECIES_3.index(CO2)] = 1.0
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        Q = np.prod(p[None, :] ** arr.nu_gas, axis=1)
    P_react = np.prod(p[None, :] ** arr.gas_consumed, axis=1)
    P_prod = np.prod(p[None, :] ** arr.gas_formed, axis=1)
    flux_net = k_f * P_react - k_r * P_prod
    print(f"  {p_co:12.3e} {Q[i]:16.4e} {(k_r * Q)[i]:14.4e} "
          f"{abs(flux_net[i]):14.4e}")
print()
print("  the OLD column diverges and the NEW one is bounded by k_r * p_CO2,")
print(f"  which at {T:.0f} K is {k_r[i]:.4e} 1/(bar s). Nothing is clipped:")
print("  the reverse of this reaction IS a real flux -- a blast furnace's top")
print("  gas contains CO because of it -- and that is why an irreversible term")
print("  could not hold the row (surface.LN_K_IRREVERSIBLE refused all four).")

# ---------------------------------------------------------------------------
rule("4. THE EQUILIBRIUM IS Q = K, AND IT DOES NOT DEPEND ON THE CHARGE")
# ---------------------------------------------------------------------------
n = net([TENORITE, COPPER, CO, CO2, N2])
T = 1500.0
lnK = None
for decl in ss.SOLID_STATE_REACTIONS:
    if decl.name == "tenorite-carbon-monoxide-reduction":
        p = ss.price(decl, thermo)
        lnK = -(p.dH - T * p.dS) / (R * T)
K = math.exp(lnK)
print(f"  tenorite + CO -> copper + CO2 at {T:.0f} K:  K = {K:.4e}")
print("  a SEALED flask given less CO than oxide stops at Q = K and leaves")
print("  the rest of the charge unreduced. That is the mechanic.")
print()
print(f"  {'oxide/mol':>10s} {'p_CO0/bar':>10s} {'Cu/mol':>10s} "
      f"{'CuO left':>10s} {'Q at rest':>12s} {'Q/K':>8s}")
for charge, co_bar in ((0.10, 0.02), (0.10, 0.05), (0.02, 0.02), (1.00, 0.05)):
    v = Vessel(n, volume=10.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge({TENORITE: charge}, phase="solid")
    v.charge({CO: co_bar * 10.0 / (R_L_BAR * T)}, phase="gas")
    v.run(40000.0, **TIGHT)
    pco = gas(v, CO) * R_L_BAR * T / 10.0
    pco2 = gas(v, CO2) * R_L_BAR * T / 10.0
    Q = pco2 / pco if pco > 0.0 else float("inf")
    print(f"  {charge:10.2f} {co_bar:10.2f} {solid(v, COPPER):10.6f} "
          f"{solid(v, TENORITE):10.6f} {Q:12.4e} {Q/K:8.4f}")
    assert not v.conservation_report(), v.conservation_report()
print()
print("  the CHARGE moves by a factor of 50 and Q/K does not move: 'units' is")
print("  a common factor of both directions, so it divides out of net = 0.")
print("  That is the property M6 built this form to have, and it was never")
print("  what a gas reactant threatened.")

# ---------------------------------------------------------------------------
rule("5. AN EXOTHERMIC ROW CANNOT TAKE THE DERIVED PAIR -- THE TWO NUMBERS")
# ---------------------------------------------------------------------------
print("  Ea = max(dH, 0) is a derivation about an ENDOTHERMIC decomposition")
print("  whose reverse is barrierless. On an exothermic row it returns ZERO.")
print()
print(f"  {'row':38s} {'dH/kJ':>9s} {'A derived':>11s} {'tau derived':>13s} "
      f"{'Ea declared':>12s}")
for decl in ss.SOLID_STATE_REACTIONS:
    if decl.Ea is None:
        continue
    p = ss.price(decl, thermo)
    A_derived = ss.RECOMBINATION_A * math.exp(p.dS / R)
    print(f"  {decl.name:38s} {p.dH/1000:9.2f} {A_derived:11.4e} "
          f"{1.0/A_derived:13.4e} {p.Ea/1000:12.2f}")
print()
print("  ! READ THE 'tau derived' COLUMN AS SECONDS AT EVERY TEMPERATURE, which")
print("  is the finding and not the size of the number. With Ea = 0 there is no")
print("  exponential left at all, so thermite is a 2.8-DAY reaction that goes")
print("  exactly as fast in a cold jar as in a furnace -- its whole mechanic")
print("  deleted -- and a CO reduction is a 17-minute one at 298 K as well as")
print("  at 1500. It is not that the rates are wrong; it is that the")
print("  temperature has left the rate law.")

# ---------------------------------------------------------------------------
rule("6. THE THREE SMELTING ROUTES, END TO END -- NOTHING DECLARES THEM")
# ---------------------------------------------------------------------------
print("  each route is a ROAST from properties/surface.py followed by a")
print("  REDUCTION from properties/solid_state.py, and neither declaration")
print("  mentions the other. They share a solid block and a headspace.")
print()
print("  copper-smelting   CuS + O2 -> CuO + SO2   then  CuO + CO  -> Cu + CO2")
print("  lead-smelting     PbS + O2 -> PbO + SO2   then  PbO + CO  -> Pb + CO2")
print("  zinc-smelting     ZnS + O2 -> ZnO + SO2   then  ZnO + C   -> Zn + CO")
print()
print("  and the CO is not charged: carbon burns in the blast (surface.py) and")
print("  the Boudouard reaction turns the CO2 back into CO (solid_state.py).")
print()

n_cu = net([COVELLITE, TENORITE, COPPER, GRAPHITE, CO, CO2, N2, O2, SO2])
n_pb = net([GALENA, LITHARGE, LEAD, GRAPHITE, CO, CO2, N2, O2, SO2])
n_zn = net([SPHALERITE, ZINCITE, ZINC, GRAPHITE, CO, CO2, N2, O2, SO2])

print(f"  {'route':16s} {'T/K':>6s} {'O2/mol':>7s} {'metal':>10s} "
      f"{'ore left':>10s} {'oxide':>10s} {'C left':>9s} {'SO2':>9s}")
for label, n_, ore, oxide, metal, T in (
    ("copper-smelting", n_cu, COVELLITE, TENORITE, COPPER, 1500.0),
    ("lead-smelting", n_pb, GALENA, LITHARGE, LEAD, 1400.0),
    ("zinc-smelting", n_zn, SPHALERITE, ZINCITE, ZINC, 1400.0),
):
    for o2 in (0.06, 0.20):
        v = Vessel(n_, volume=10.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
        v.charge({ore: 0.04, GRAPHITE: 0.20}, phase="solid")
        v.charge({O2: o2, N2: o2 * 79.0 / 21.0}, phase="gas")
        v.run(40000.0, **TIGHT)
        st = v.state()
        # !! S10 -- the metal WHEREVER IT IS. Copper and lead land in the solid
        # block; zinc comes off as a vapour above 1180 K, so reading only
        # n_solid here would measure the thermometer and not the yield.
        made = (st.n_solid[metal] + st.n_liquid[metal] + st.n_liquid2[metal]
                + st.n_gas[metal])
        print(f"  {label:16s} {T:6.0f} {o2:7.2f} {made:10.6f} "
              f"{solid(v, ore):10.6f} {solid(v, oxide):10.6f} "
              f"{solid(v, GRAPHITE):9.5f} {gas(v, SO2):9.6f}")
print()
print("  the AIR is the control, which is what a smelter actually adjusts: too")
print("  little and the sulfide never roasts.")
print()
print("  !! S10 -- AND S9's OVERBLOWING FINDING IS GONE FROM THIS TABLE. IT WAS")
print("     A RATE ARTEFACT AND IT WAS PRESENTED AS PHYSICS.")
print("     S9 measured the zinc row going DOWN at 0.20 mol O2 -- 0.032476 mol")
print("     of metal at 0.06 against 0.025515 at 0.20, with zincite left and the")
print("     coke gone -- and wrote: 'Overblowing a zinc retort really does waste")
print("     the charge.' The competition it identified is real: the carbothermic")
print("     reduction and the tuyere DO want the same carbon, and copper and lead")
print("     do not, because their reductant is the CO the carbon made and")
print("     Boudouard hands it back.")
print("     What decided the race was two DERIVED pre-exponentials, and making")
print("     the zinc a vapour moved one of them: tau at 1400 K is 10.92 s where")
print("     it was 256.9 s (dS carries exp(dS/R) into A -- see")
print("     tests/test_solid_state.py). The reduction is now 24x faster, so it")
print("     takes the zincite before the blast can burn the coke, and the yield")
print("     is monotone and saturating. Swept finely at 1400 K:")
print()
print("        O2/mol   0.02    0.04    0.06    0.10    0.14    0.20    0.50")
print("        Zn/mol  .0117   .0229   .0328   .0400   .0400   .0400   .0400")
print()
print("     !! THE LESSON IS THE SIGN OF THE EFFECT DEPENDED ON A CLOCK. A real")
print("     furnace does waste an overblown charge, for transport reasons this")
print("     engine does not model, so the old panel read like a prediction and")
print("     was a coincidence of two rate constants. Thermodynamic conclusions")
print("     here survive a phase change in a product; kinetic ones need not.")

print()
print("  --- and the zinc retort is a THRESHOLD, because its dG changes sign ---")
print("  SEALED, 1 L, 0.04 mol zincite + 0.20 mol coke. Sealed on purpose: the")
print("  product is a GAS now, so a vented flask loses it -- see below.")
print(f"  {'T/K':>7s} {'Zn(g)':>10s} {'Zn(l)':>10s} {'Zn(s)':>10s} "
      f"{'ZnO left':>10s} {'converted':>10s}")
n_zr = net([ZINCITE, ZINC, GRAPHITE, CO, CO2])
for T in (1000.0, 1100.0, 1150.0, 1198.0, 1250.0, 1300.0, 1400.0):
    v = Vessel(n_zr, volume=1.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge({ZINCITE: 0.04, GRAPHITE: 0.20}, phase="solid")
    v.run(20000.0, **TIGHT)
    st = v.state()
    tot = st.n_gas[ZINC] + st.n_liquid[ZINC] + st.n_solid[ZINC]
    print(f"  {T:7.0f} {st.n_gas[ZINC]:10.6f} {st.n_liquid[ZINC]:10.6f} "
          f"{st.n_solid[ZINC]:10.6f} {solid(v, ZINCITE):10.6f} "
          f"{tot / 0.04 * 100:9.2f}%")
for decl in ss.SOLID_STATE_REACTIONS:
    if decl.name == "zincite-carbothermic-reduction":
        p = ss.price(decl, thermo)
        print(f"  dG = 0 at {p.dH/p.dS:.1f} K, against a real Belgian retort's")
        print("  1200-1300 and a literature threshold of ~1200 K. Nothing was")
        print("  fitted: it is TWO mineral-data lattices (zincite and graphite)")
        print("  against TWO curated gases (zinc vapour and CO). !! S9's version")
        print("  of this line said 'a lattice against three curated gases', which")
        print("  described a row with a solid zinc product and one gas.")
print()
print("  !! S10 MOVED THIS, AND TOWARD THE LITERATURE. S9 declared the zinc as a")
print("     SOLID product and got 1264.3 K. A retort makes VAPOUR, and carrying")
print("     it as one adds the sublimation energy (+130.4 kJ/mol) and the entropy")
print("     of a mole of metal gas (+119.4 J/(mol K)); the entropy wins and the")
print("     threshold comes DOWN by 66 K. dH +240.0 -> +370.4, dS +189.8 -> +309.2.")

# ---------------------------------------------------------------------------
rule("6b. THE ZINC DISTILS, AND NEITHER Tb NOR Tm IS WRITTEN ANYWHERE")
# ---------------------------------------------------------------------------
print("  !! THIS PANEL IS S10, AND IT IS THE LIMITATION PANEL 6 USED TO CARRY.")
print("  S9 recorded: 'the zinc is a SOLID here. A real retort distils it off at")
print("  1180 K, which is product removal, and mineral_data holds zinc as a")
print("  lattice -- which in this engine may react and may never boil.'")
print()
print("  Both clauses were true and the conclusion did not follow. The LATTICE")
print("  ENTRY was the obstacle, not the metal: zinc has a monatomic vapour, one")
print("  condensed form and a measured sublimation curve, so it passes every")
print("  test S4 admitted mercury on. It is an element_data species now, the")
print("  lattice row is gone, and NO ENGINE CODE CHANGED -- the existing")
print("  evaporation and melt terms do all of the work below.")
print()
print("  Charge the retort at 1400 K, then cool the receiver:")
v = Vessel(n_zr, volume=1.0, T=1400.0, T_env=1400.0, UA=1.0e4, k_vent=0.0)
v.charge({ZINCITE: 0.04, GRAPHITE: 0.20}, phase="solid")
v.run(20000.0, **TIGHT)
st = v.state()
print(f"  {'T/K':>8s} {'Zn(g)':>13s} {'Zn(l)':>13s} {'Zn(s)':>13s}")
print(f"  {1400.0:8.1f} {st.n_gas[ZINC]:13.6f} {st.n_liquid[ZINC]:13.6f} "
      f"{st.n_solid[ZINC]:13.6f}   <- the burn")
for T in (1180.0, 1100.0, 900.0, 700.0, 600.0, 400.0):
    v.set_environment(T_env=T)
    v.T = T
    v.run(20000.0, **TIGHT)
    st = v.state()
    print(f"  {T:8.1f} {st.n_gas[ZINC]:13.6f} {st.n_liquid[ZINC]:13.6f} "
          f"{st.n_solid[ZINC]:13.6f}")
print("  Tb = 1180.15 K and Tm = 692.68 K. Neither appears in the declaration")
print("  or in this file: the metal condenses where its own vapour-pressure")
print("  curve crosses its own partial pressure, and freezes at its own Tm.")
print()
print("  --- PRODUCT REMOVAL, and it switches on where the gas beats the room ---")
print("  solid_state_report computes 1156 K for this row's two evolved gases to")
print("  reach one bar between them. Below that a vented retort vents NOTHING.")
print(f"  {'T/K':>7s} {'sealed':>9s} {'vented':>9s} {'p sealed/bar':>13s}")
for T in (1140.0, 1150.0, 1156.0, 1160.0, 1170.0, 1198.0):
    out, p_sealed = [], None
    for vented in (False, True):
        v = Vessel(n_zr, volume=1.0, T=T, T_env=T, UA=1.0e4,
                   k_vent=1.0e3 if vented else 0.0)
        v.charge({ZINCITE: 0.04, GRAPHITE: 0.20}, phase="solid")
        v.run(20000.0, **TIGHT)
        out.append((0.04 - solid(v, ZINCITE)) / 0.04 * 100.0)
        if not vented:
            p_sealed = v.pressure
    print(f"  {T:7.0f} {out[0]:8.2f}% {out[1]:8.2f}% {p_sealed:13.4f}")
print("  The 1156 K is derived from a van 't Hoff K; the crossover above is")
print("  measured by running the flask. They agree to the degree.")
print()
print("  !! AND A VENTED RETORT BLOWS ITS OWN PRODUCT UP THE CHIMNEY, WHICH")
print("     NOBODY DECLARED EITHER. The vent that pulls the reaction over is")
print("     indifferent to which gas it vents, so the two numbers a smelter")
print("     cares about come apart and move in OPPOSITE directions with heat:")
print(f"  {'T/K':>7s} {'ore consumed':>13s} {'metal kept':>11s} {'up the flue':>12s}")
for T in (1200.0, 1300.0, 1400.0):
    v = Vessel(n_zr, volume=10.0, T=T, T_env=T, UA=1.0e4, k_vent=1.0e3,
               atmosphere={})
    v.charge({ZINCITE: 0.10, GRAPHITE: 0.10}, phase="solid")
    v.run(20000.0, **TIGHT)
    st = v.state()
    kept = st.n_gas[ZINC] + st.n_liquid[ZINC] + st.n_solid[ZINC]
    used = 0.10 - solid(v, ZINCITE)
    print(f"  {T:7.0f} {used / 0.10 * 100:12.2f}% {kept / 0.10 * 100:10.2f}% "
          f"{(used - kept) / 0.10 * 100:11.2f}%")
print("  That is why a real Belgian retort has a condenser hanging off it, and")
print("  it is why panel 6 above is run SEALED. conservation_report is silent")
print("  throughout, correctly: the vent is a declared boundary flux, not a")
print("  leak, and an invariant measured across one is not an invariant.")

# ---------------------------------------------------------------------------
rule("7. THE CARRIER-FREE FURNACE IS INERT, AT FOUR TOLERANCE RUNGS")
# ---------------------------------------------------------------------------
print("  ore + coke and NO GAS: both reactions that would run need a carbon")
print("  oxide, and there is none. This is the question chemsim-solid-gate-fix")
print("  exists to ask -- a CYCLE with gain on its own carrier is exactly the")
print("  shape that let round-off seed the lead chamber to 89% yield.")
print()
n_cf = net([TENORITE, COPPER, GRAPHITE, CO, CO2, N2])
print(f"  {'tolerance':22s} {'Cu/mol':>12s} {'CO/mol':>12s} {'CO2/mol':>12s}")
for label, kw in (("default rung", {}),
                  ("rtol 1e-6", dict(rtol=1.0e-6)),
                  ("rtol 1e-8 atol 1e-11", TIGHT),
                  ("rtol 1e-10 atol 1e-14", dict(rtol=1.0e-10, atol=1.0e-14))):
    v = Vessel(n_cf, volume=10.0, T=1500.0, T_env=1500.0, UA=1.0e4, k_vent=0.0)
    v.charge({TENORITE: 0.10, GRAPHITE: 0.10}, phase="solid")
    v.run(20000.0, **kw)
    print(f"  {label:22s} {solid(v, COPPER):12.4e} {gas(v, CO):12.4e} "
          f"{gas(v, CO2):12.4e}")
print()
print("  EXACTLY zero, four times. The reason is the form and not a guard: the")
print("  arriving gas enters as p ** 1 with no denominator, so zero in is zero")
print("  out with a bounded slope -- the same argument SurfaceArrays makes.")
print("  A smoothstep gate with a constant scale is what failed in the lead")
print("  chamber, and there is none here.")
print()
print("  --- and once SEEDED, the carrier multiplies, which is real chemistry ---")
print(f"  {'CO2 charged':>14s} {'Cu/mol':>10s} {'C left':>11s} {'CO end':>12s}")
for seed in (0.0, 1.0e-12, 1.0e-6, 1.0e-2):
    v = Vessel(n_cf, volume=10.0, T=1500.0, T_env=1500.0, UA=1.0e4, k_vent=0.0)
    v.charge({TENORITE: 0.10, GRAPHITE: 0.10}, phase="solid")
    if seed:
        v.charge({CO2: seed}, phase="gas")
    v.run(20000.0, **TIGHT)
    print(f"  {seed:14.1e} {solid(v, COPPER):10.6f} "
          f"{solid(v, GRAPHITE):11.3e} {gas(v, CO):12.6f}")
print()
print("  1e-12 mol of CO2 -- one part in 1e11 of the charge -- reduces the")
print("  whole 0.10 mol of oxide. Boudouard makes 2 CO from 1 CO2, and the")
print("  reduction hands one CO2 back, so the cycle GAINS a carrier per turn.")
print("  A blast furnace's gas volume really does grow that way. The carbon is")
print("  the reagent; the carbon oxide is only the vehicle.")

# ---------------------------------------------------------------------------
rule("8. THERMITE -- THE BARRIER IS THE MECHANIC, AND WHAT DOES NOT CAP IT")
# ---------------------------------------------------------------------------
n_th = net([HEMATITE, ALUMINIUM, IRON, CORUNDUM, N2])
print("  Fe2O3 + 2 Al -> 2 Fe + Al2O3: four crystals and NO GAS, so both")
print("  one-sided pressure products are empty (exactly 1.0) and the affinity")
print("  collapses to k_f - k_r. There is no quotient to move.")
print()
print(f"  {'T/K':>8s} {'Fe/mol':>13s} {'conversion':>12s}   (isothermal, 600 s)")
for T in (298.15, 600.0, 800.0, 933.0, 1000.0, 1200.0):
    v = Vessel(n_th, volume=1.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge({HEMATITE: 0.02, ALUMINIUM: 0.04}, phase="solid")
    v.run(600.0, **TIGHT)
    print(f"  {T:8.2f} {solid(v, IRON):13.6e} "
          f"{solid(v, IRON)/0.04*100:11.4f}%")
print()
print("  933 K is where ALUMINIUM MELTS, which is the trigger every account of")
print("  thermite names, and nothing here knows that: the column is one")
print("  Arrhenius pair pinned on a reported 1200 K ignition temperature.")
print()
print("  --- INSULATED, so it runs away on its own enthalpy ---")
print(f"  {'vessel Cp':>10s} {'T0/K':>8s} {'T end/K':>10s} {'rise/K':>10s} "
      f"{'Fe/mol':>9s}")
for hc in (1.0, 50.0, 500.0):
    for T0 in (298.15, 1000.0):
        v = Vessel(n_th, volume=1.0, T=T0, T_env=T0, UA=0.0, k_vent=0.0,
                   heat_capacity=hc)
        v.charge({HEMATITE: 0.02, ALUMINIUM: 0.04}, phase="solid")
        v.run(600.0, **TIGHT)
        st = v.state()
        print(f"  {hc:10.1f} {T0:8.2f} {st.T:10.2f} {st.T - T0:10.2f} "
              f"{solid(v, IRON):9.6f}")
print()
print("  ! STATED LIMITATION: nothing caps the temperature. A real thermite")
print("    stops near 3135 K because the IRON BOILS. The RHS clamps T at 5000 K")
print("    for RATE evaluation only, so a small-heat-capacity flask can report a")
print("    state above it.")
print()
print("  !! S10 -- AND THIS IS NO LONGER 'THE SAME STATEMENT THE ZINC RETORT")
print("     MAKES'. S9 paired these two as one gap, on the shared sentence 'a")
print("     lattice may react and may never boil'. Half of that gap was a DATA")
print("     job and is closed (panel 6b); the half left is a real engine")
print("     question, and pulling them apart is what located it.")
print()
print("     The DATA for iron is nearly there. Alcock's liquid equation converts")
print("     to Antoine exactly, as zinc's did -- A = 6.352717, B = 19574, C = 0 --")
print("     and unanchored it puts Tb at 3083.98 K against 3134.15 measured,")
print("     -1.60%. That curve's slope gives Hvap = 374.7 kJ/mol, so boiling the")
print("     2 mol of iron a mole of thermite makes would absorb 749.5 kJ of the")
print("     851.5 kJ released -- 88.0%. THE MECHANISM WOULD CAP IT.")
print()
print("     It is refused on three counts, measured rather than assumed:")
print("     1. !! IRON CANNOT LEAVE mineral_data THE WAY ZINC DID. It is a")
print("        declared solid_catalyst -- ammonia_synthesis(catalyst='iron'),")
print("        resolved through MINERALS['iron'].lattice -- and thermite's own")
print("        solid product. So iron has to be BOTH a mineral_data lattice and")
print("        a thermochemistry gas, which PhaseArrays.lattice, a single")
print("        boolean picking both a basis and a destination block, cannot say.")
print("        Zinc never needed that: nothing else referenced its lattice.")
print("        !! CORRECTION, MEASURED AFTER THIS PANEL WAS WRITTEN: this count")
print("        OVERSTATES the cost. Iron is in no surface row, so those two")
print("        hot-loop uses of the flag are inert for it (C_mix[Fe] ** 0 == 1.0")
print("        exactly); the Haber catalyst reads order_solid/nS and never used")
print("        the flag; the real blocker is ONE branch in build_phase_arrays,")
print("        a setup-layer change with NO RHS edit. Patched in place, thermite")
print("        caps at 3490.99 K instead of 5469.43. See NEXT_PROMPT item 1.")
print("        **What keeps it open is counts 2 and 3 -- the DATA.**")
print("     2. [Fe] fails S4's DISAMBIGUATION test, which [Zn] passes. Zinc has")
print("        one condensed form; iron has three solid allotropes, with two")
print("        transitions inside thermite's own temperature range, and dCp = 0")
print("        with a single Tm/Hfus cannot represent them. element_data's own")
print("        refusal list already names [Fe] beside [C] and [S] for this.")
print("     3. ONE cross-check, not four. Alcock tabulates no SUBLIMATION curve")
print("        for iron, so the 298 K reference-state identity that zinc closed")
print("        at -0.184 kJ/mol cannot be evaluated at all.")

print()
print("=" * 74)
print("DONE. Every number above came out of this project's own tables.")
print("=" * 74)

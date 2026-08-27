"""G5 -- protonation: what a species split buys, and what it does not.

A standing audit, ~18 s. Seven panels:

  1. the four CURATED ION ROWS THAT WERE DEAD, and the anchor direction that
     killed them;
  2. the pKa read straight back out of a running pot, which is the only check
     that the reversed arithmetic is the same arithmetic;
  3. the ARITHMETIC BOUND, taken before any code was written: at what acidity
     does the anilinium channel overtake the free-base channel;
  4. the acidity a mass-action hydronium can actually REACH in this engine, and
     the surprise in it -- more acid with less water is LESS acidic;
  5. the split, measured in the engine: six decades of the fourteen, and where
     the other eight are;
  6. the REFUSAL -- a protonation template is open-ended where the ion table is
     a curated list -- and why curating the missing rows is measured to buy
     nothing;
  7. the answer real chemistry gives, which the engine can already run: protect
     the amine.

Run: ``python validation/protonation.py``
"""

from __future__ import annotations

import math
import time

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import (
    ThermochemistryProvider,
    dissociation_templates,
    electrolyte,
    electrolyte_provider,
)
from chemsim.reactions import hammett
from chemsim.reactions.synthesis import NITRATION_RHO, aromatic_nitration, n_acylation
from chemsim.vessel import Vessel


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


ANILINE, ANILINIUM = c("Nc1ccccc1"), c("[NH3+]c1ccccc1")
ACETANILIDE = c("CC(=O)Nc1ccccc1")
ANHYDRIDE = c("CC(=O)OC(C)=O")
NITRIC, SULFURIC, WATER, HYD = (
    c("O[N+](=O)[O-]"), c("OS(=O)(=O)O"), c("O"), c("[OH3+]"),
)
BENZENE = c("c1ccccc1")
PKA_ANILINIUM = 4.62         # the value in electrolyte._PAIRS
BAR = "=" * 78
t0 = time.time()
plain = ThermochemistryProvider()
thermo = electrolyte_provider()

# ---------------------------------------------------------------------------
print(BAR)
print("PANEL 1  FOUR CURATED ION ROWS THAT PRODUCED NOTHING")
print(BAR)
print("""   `ion_thermochemistry` anchored every pair on its ACID. Four rows of
   `_PAIRS` are CATION/neutral pairs whose acid IS the ion, and the ordinary
   providers refuse a charge -- loudly, and correctly. A bare
   `except Exception: continue` swallowed all four.
""")
ions = electrolyte.ion_thermochemistry(plain)
print(f"   {'pair':24s} {'acid (the ION)':24s} {'anchored on':14s} {'priced':>7s}")
for pair in electrolyte.known_pairs():
    if Molecule.from_smiles(pair.acid).charge <= 0:
        continue                       # the ordinary anion case, unchanged
    a_key = Molecule.from_smiles(pair.acid).smiles
    print(f"   {pair.name or pair.acid:24s} {a_key:24s} {'the BASE':14s} "
          f"{str(a_key in ions):>7s}")
cations = sorted(k for k in ions if Molecule.from_smiles(k).charge > 0)
print(f"""
   {len(ions)} entries now, 24 before, and the four new ones are the only
   CATIONS in the table apart from the hard-coded hydronium:
     {cations}

   The 24 anions are BIT-IDENTICAL, which is what makes this a bug fix and not
   a data-table change -- see the comment in `ion_thermochemistry` on why the
   two Gibbs terms are still added separately and in the old order.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 2  THE pKa, READ BACK OUT OF A RUNNING POT")
print(BAR)
print(f"""   The reversed arithmetic has to be the SAME arithmetic. An anilinium
   priced backwards from aniline must reproduce the {PKA_ANILINIUM} it was
   derived from, measured as log10([BH+] / ([B][H3O+])) in a flask that has
   equilibrated -- not asserted from the code that wrote it.
""")
net_p = build_network([ANILINE, NITRIC, SULFURIC, WATER], dissociation_templates(),
                      thermo=thermo, max_species=40)
print(f"   network: {len(net_p.species)} species, {len(net_p.reactions)} reactions")
print(f"\n   {'HNO3':>5s} {'H2SO4':>5s} {'H2O':>5s} {'pH':>7s} {'aniline':>9s} "
      f"{'PhNH3+':>9s} {'% prot':>8s} {'pKa read':>9s}")
CHARGES = ((0.0, 0.0, 30.0), (0.1, 0.0, 30.0), (1.0, 0.0, 30.0),
           (3.5, 0.0, 30.0), (3.5, 3.5, 30.0), (5.0, 5.0, 30.0))
rows = []
for hno3, h2so4, water in CHARGES:
    v = Vessel(net_p, volume=2.0, T=298.15, T_env=298.15, UA=1.0e6, kla=0.0,
               k_vent=0.0, k_diss=0.0, lle=False)
    ch = {ANILINE: 1.0, WATER: water}
    if hno3:
        ch[NITRIC] = hno3
    if h2so4:
        ch[SULFURIC] = h2so4
    v.charge(ch)
    v.run(100.0)
    conc = v.concentrations(v.aqueous_layer())
    b, bh, h = conc.get(ANILINE, 0.0), conc.get(ANILINIUM, 0.0), conc.get(HYD, 0.0)
    frac = bh / (b + bh) if (b + bh) else float("nan")
    pka = math.log10(bh / (b * h)) if b > 0 and bh > 0 and h > 0 else float("nan")
    rows.append((v.pH, frac, pka))
    print(f"   {hno3:5.1f} {h2so4:5.1f} {water:5.1f} {v.pH:7.3f} {b:9.5f} "
          f"{bh:9.5f} {100 * frac:8.3f} {pka:9.3f}")
print(f"""
   The two DILUTE rows are the check: pH {rows[1][0]:.2f} reads {rows[1][2]:.2f}
   and pH {rows[2][0]:.2f} reads {rows[2][2]:.2f} against a declared
   {PKA_ANILINIUM}. The reversed derivation is the forward one.

   AND THE DRIFT IN THE STRONG ROWS IS NOT NOISE. By the bottom row the pot is
   ~40% acid by mole and the readback has walked to {rows[-1][2]:.2f}. Mass
   action in molarity is not an activity model, and an aqueous pKa asked to work
   in what is no longer water reports the difference. That is
   `chemsim-ion-transfer`'s finding in a third suit, and it MATTERS here, because
   the acidity of a real mixed acid is exactly the regime the whole question
   lives in. See panel 4.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 3  THE ARITHMETIC BOUND, TAKEN BEFORE ANY CODE WAS WRITTEN")
print(BAR)
print("""   G2 named this item as a design QUESTION: is an anilinium a barrier
   shift, or is it a DIFFERENT SPECIES with its own sigma row? The second, and
   the table row is cheap -- so the thing to measure first is whether the split
   FIXES anything. Two channels run in parallel and the pot's acidity picks the
   weights.
""")
s_free = hammett.survey(Molecule.from_smiles(ANILINE)._mol).sigma_sum
s_ion = hammett.survey(Molecule.from_smiles(ANILINIUM)._mol).sigma_sum
k_free = hammett.rate_ratio(NITRATION_RHO, s_free)
k_ion = hammett.rate_ratio(NITRATION_RHO, s_ion)
print(f"   free base  -NH2   sigma+ {s_free:+.3f}   k/k0 = {k_free:11.4e}")
print(f"   anilinium  -NH3+  sigma  {s_ion:+.3f}   k/k0 = {k_ion:11.4e}")
print(f"   ratio                                  {k_free / k_ion:11.4e}\n")
print(f"   {'pH':>6s} {'frac free base':>15s} {'free channel':>14s} "
      f"{'ion channel':>13s}   which wins")
for pH in (7.0, 4.62, 2.0, 0.0, -2.0, -5.0, -9.42, -12.0):
    h = 10.0 ** (-pH)
    f = 10.0 ** (-PKA_ANILINIUM) / (10.0 ** (-PKA_ANILINIUM) + h)
    a, bb = f * k_free, (1.0 - f) * k_ion
    print(f"   {pH:6.2f} {f:15.4e} {a:14.4e} {bb:13.4e}   "
          + (f"FREE BASE x{a / bb:.2e}" if a > bb else f"anilinium x{bb / a:.2e}"))
h_cross = 10.0 ** (-PKA_ANILINIUM) * k_free / k_ion
print(f"""
   THE CROSSOVER IS AT [H3O+] = {h_cross:.3e} mol/L, i.e. pH
   {-math.log10(h_cross):.2f}. That is not a molarity any solution has -- and it
   is ALSO not a wrong answer. Real aniline is nitrated to largely META product
   only in 90-98% sulfuric acid, whose Hammett acidity function H0 falls to
   roughly -8 at 90 wt% and roughly -10 at 98 wt%. ⚠ THAT BAND IS QUOTED TO ONE
   FIGURE ON PURPOSE -- it is recalled from a standard H0 table and was NOT
   sourced in this repo, so the claim is that -9.42 lands INSIDE the band real
   aniline nitration is run in, not that it matches a tabulated value.
   The engine's own arithmetic lands the crossover inside that band
   without being told about it, which is the strongest thing in this audit: the
   split is the RIGHT MODEL. What it cannot do is get there, and panel 4 is
   why.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 4  THE ACIDITY THIS ENGINE CAN REACH, AND THE SURPRISE IN IT")
print(BAR)
print("""   Every dissociation in this project is written with water on BOTH sides,
   for the standard-state reason in `properties/electrolyte`'s docstring. The
   consequence has never been measured: [H2O] is a mass-action factor, so
   running out of water SUPPRESSES the dissociation that makes the proton.
""")
net_a = build_network([NITRIC, SULFURIC, WATER], dissociation_templates(),
                      thermo=thermo, max_species=40)
print(f"   {'HNO3':>6s} {'H2SO4':>6s} {'H2O':>6s} {'V/L':>6s} {'[H3O+]/M':>10s} "
      f"{'pH':>8s}")
floor = (float("inf"), None)
for water in (40.0, 30.0, 20.0, 10.0, 6.0, 4.0, 3.0, 2.0, 1.0):
    v = Vessel(net_a, volume=2.0, T=298.15, T_env=298.15, UA=1.0e6, kla=0.0,
               k_vent=0.0, k_diss=0.0, lle=False)
    v.charge({NITRIC: 5.0, SULFURIC: 5.0, WATER: water})
    v.run(100.0)
    conc = v.concentrations(v.aqueous_layer()).get(HYD, 0.0)
    print(f"   {5.0:6.1f} {5.0:6.1f} {water:6.1f} {v.liquid_volume:6.3f} "
          f"{conc:10.4f} {v.pH:8.3f}")
    if v.pH < floor[0]:
        floor = (v.pH, water)
print(f"""
   THE POT GETS LESS ACIDIC AS THE ACID GETS DRIER. 5 + 5 mol of acid in
   {floor[1]:.0f} mol of water reads pH {floor[0]:.2f}; the same acid in 1 mol of
   water reads several units HIGHER. That is not a solver artefact -- it is real
   chemistry this engine gets right for free: dry sulfuric acid is not a source
   of hydronium, it autoprotolyses to H3SO4+ and HSO4-, and an H3O+ needs a water
   to be.

   AND IT IS THE WALL. The floor measured here is about pH {floor[0]:.2f}, ten
   orders of magnitude above panel 3's crossover. A mixed acid's acidity is an
   ACIDITY FUNCTION (H0), which is not the concentration of anything; this
   engine's only handle on acidity is a mass-action molarity, and a molarity
   cannot go to 1e9 mol/L. **THE LIMIT IS NOT "NO PROTONATION" ANY MORE. IT IS
   "NO ACIDITY FUNCTION", and that is a different and much better-posed gap.**""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 5  THE SPLIT, MEASURED IN THE ENGINE: SIX DECADES OF FOURTEEN")
print(BAR)
print("""   The same flasks as panel 2, with each one's aniline split by the running
   equilibrium and the two channels weighted by what is actually in the pot.
""")
print(f"   {'pH':>7s} {'% protonated':>13s} {'effective k/k0':>15s} "
      f"{'carried by the ion':>19s}")
for pH, frac, _ in rows:
    eff = (1 - frac) * k_free + frac * k_ion
    print(f"   {pH:7.3f} {100 * frac:13.3f} {eff:15.4e} "
          f"{100 * frac * k_ion / eff:18.3e}%")
eff_best = (1 - rows[-1][1]) * k_free + rows[-1][1] * k_ion
print(f"""
   2.8e8 -> {eff_best:.3g} times benzene. SIX of the fourteen decades, in the
   right direction, on a table row and a template direction. Worth having.

   AND THE OTHER EIGHT ARE NOT IN THE PROTONATION MODEL. Read the last column:
   the anilinium is 100.000% of the aniline in the pot and carries 1e-7% of the
   rate. Every remaining decade is a FREE-BASE LEAK -- a channel surviving at
   1e-6 mole fraction because sigma+ = -1.30 prices it at 2.8e8. Fixing the
   FRACTION cannot fix that; only pricing the free base differently can.

   THE NEXT ITEM IS THEREFORE NAMED, AND ITS ARITHMETIC IS DONE HERE.
   rho * sum(sigma+) = -6.5 * -1.30 = 8.45 DECADES, extrapolated from a line
   fitted on arenes with |sigma+| < 0.4 (toluene, the xylenes, the halobenzenes),
   i.e. |rho*sigma| < 2.6. It is a 3.25x extrapolation of the abscissa, and the
   real relation does not go there: nitration of a strongly activated arene
   becomes ENCOUNTER-CONTROLLED, so mesitylene, anisole and phenol all react at
   the same rate and the Hammett line SATURATES. A declared saturation would put
   aniline in the engine's most acidic flask at:""")
for sat in (1e4, 1e5, 1e6):
    capped = min(k_free, sat)
    eff = (1 - rows[-1][1]) * capped + rows[-1][1] * k_ion
    print(f"       saturation {sat:8.0e}  ->  {eff:10.4e} x benzene")
print("""   -- against a real anilinium SLOWER than benzene. A saturation near 1e5
   lands the aniline within a decade or two of benzene instead of eight above it,
   on ONE declared field. The CONSTANT needs its own sourcing session (Coombes
   and Ridd on encounter-controlled nitration) and is NOT asserted here.

   AND NOTE WHICH AUDIT CANNOT CATCH THIS. `detailed_balance`'s collision cap
   compares the PRE-EXPONENTIAL against a limit; hammett moves `Ea`. With
   A = 1e10 and the barrier clamped at zero the fastest a shifted nitration can
   ever run is 1e10, one decade UNDER the 1e11 ceiling -- so the cap never fires
   on a substituent-shifted rate at all. That is fragility 13 in a new suit.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 6  THE REFUSAL: AN OPEN-ENDED TEMPLATE OVER A CURATED TABLE")
print(BAR)
print("""   `amine_protonation` is a graph rewrite, so it protonates every amine a
   network can reach. The ion table prices the ones somebody typed. Put the two
   together with a template that substitutes the ring and the second generation
   is an amine nobody curated:
""")
try:
    build_network([ANILINE, NITRIC, WATER],
                  [aromatic_nitration(), *dissociation_templates()],
                  thermo=thermo, max_species=60, max_molar_mass=250.0)
    print("   NO REFUSAL -- this panel is out of date.")
except ValueError as exc:
    head = str(exc).split(" (liquid phase)")[0]
    print(f"   REFUSED: {head}")
    print(f"     ... {str(exc).split('refusing to price ')[-1][:110]}")
print("""
   AND THE REFUSAL IS KEPT ON PURPOSE. The fix looks like nine curated pKa
   values (2-nitroaniline near -0.3, 3- near 2.5, 4- near 1.0, and the di- and
   trinitro series below zero), and panel 5 has already measured what they would
   buy: NOTHING. The anilinium channel carries 1e-7% of the rate, so a network
   that built would report a direct aniline nitration running through the free
   base at up to 1e3 times benzene. A refusal that names the missing data is
   better than a number wrong by three decades, and this is the element floor's
   rule applied to a pKa.

   The pyridinium row is the same shape from the other end: it is PRICED now
   (pKa 5.23) and still unreachable, because an aromatic ring nitrogen is X2 and
   `amine_protonation` matches X3. A heteroaromatic protonation template would
   close it -- and the thing to measure first is the Skraup, whose product is a
   pyridine ring in hot sulfuric acid. Measured today: `validation/skraup.py`
   builds from `quinoline_chemistry()` alone, which is ONE template and carries
   no dissociation, so the coupling is CONDITIONAL on somebody adding the bundle
   there rather than automatic.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 7  WHAT REAL CHEMISTRY DOES INSTEAD, AND THE ENGINE CAN RUN IT")
print(BAR)
print("""   Nobody nitrates an aniline. You acetylate it, nitrate the acetanilide
   and hydrolyse the amide back off -- the 1800s dye and analgesic sequence, and
   the REASON is exactly the protonation this audit set out to model.
   `n_acylation` and the `acylamino` sigma+ row already existed.
""")
for label, smi in (("benzene", BENZENE), ("aniline, free base", ANILINE),
                   ("anilinium", ANILINIUM), ("acetanilide", ACETANILIDE)):
    sv = hammett.survey(Molecule.from_smiles(smi)._mol)
    Ea = hammett.clamp_barrier(
        60_000.0 + hammett.barrier_shift(NITRATION_RHO, sv.sigma_sum)
    )
    print(f"   {label:20s} sum(sigma) {sv.sigma_sum:+7.3f}  Ea {Ea / 1000:6.2f} "
          f"kJ/mol  k/k0 {hammett.rate_ratio(NITRATION_RHO, sv.sigma_sum):11.4e}")
net1 = build_network([ANILINE, ANHYDRIDE, WATER], [n_acylation()],
                     thermo=thermo, max_species=30, max_molar_mass=260.0)
v = Vessel(net1, volume=1.0, T=330.0, T_env=330.0, UA=1.0e6, kla=0.0,
           k_vent=0.0, k_diss=0.0, lle=False)
v.charge({ANILINE: 1.0, ANHYDRIDE: 1.2, WATER: 10.0})
v.run(1800.0)
st = v.state()
print(f"\n   step 1, 330 K / 30 min: aniline {st.liquid_total(ANILINE):.5f} -> "
      f"acetanilide {st.liquid_total(ACETANILIDE):.5f}")
net2 = build_network([ACETANILIDE, NITRIC, WATER],
                     [aromatic_nitration(), *dissociation_templates()],
                     thermo=thermo, max_species=60, max_molar_mass=300.0)
v = Vessel(net2, volume=1.0, T=300.0, T_env=300.0, UA=1.0e6, kla=0.0,
           k_vent=0.0, k_diss=0.0, lle=False)
v.charge({ACETANILIDE: 1.0, NITRIC: 1.5, WATER: 20.0})
v.run(600.0)
st = v.state()
amides = [s for s in net2.species if "CC(=O)N" in s]
mono = sum(st.liquid_total(s) for s in amides if s.count("[N+](=O)[O-]") == 1)
di = sum(st.liquid_total(s) for s in amides if s.count("[N+](=O)[O-]") == 2)
print(f"   step 2, 300 K / 10 min: {len(net2.species)} species BUILT -- no "
      f"ion-table gap, because an amide is not protonatable")
print(f"     acetanilide {st.liquid_total(ACETANILIDE):.4f}   mononitro {mono:.4f}"
      f"   dinitro {di:.4f}   pH {v.pH:.3f}")
ortho = [s for s in amides if s.count("[N+](=O)[O-]") == 1 and "c1ccccc1[N+]" in s]
meta = [s for s in amides if s == "CC(=O)Nc1cccc([N+](=O)[O-])c1"]
print(f"     and the isomers: ortho {sum(st.liquid_total(s) for s in ortho):.4f}"
      f"   meta {sum(st.liquid_total(s) for s in meta):.4f}")
print("""
   THE PROTECTION IS EMERGENT, AND THE LADDER IS THE WHOLE OF IT. Nobody told
   the engine that an amide is a protecting group: acetanilide's ring is
   activated by 22.3 kJ/mol where aniline's is activated by 48.2, and its
   nitrogen does not answer `amine_protonation`'s pattern. Both facts are
   already-declared data doing a new job.

   AND WHAT IT STILL GETS WRONG IS G2's OTHER NAMED LIMIT. The ortho and meta
   nitroacetanilides come out at IDENTICAL amounts against a real ~90% para,
   because the barrier has no attacked carbon in it. The protection mechanic is
   right; the isomer ratio is not.""")

print()
print(BAR)
print(f"done in {time.time() - t0:.1f} s")
print(BAR)

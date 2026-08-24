"""M3: a solubility product, from where the data actually was.

This script was written to condemn a mechanic and now measures one. Both
verdicts are below, in order, because the second overturned the first and the
reason is the useful part.

    PANEL 1  where the data was, and the refusal that was wrong about it
    PANEL 2  the cross-check that proves the basis, per ion
    PANEL 3  every lattice's Ksp, and five of them against measured solubility
    PANEL 4  what still refuses, and why each refusal is chemistry
    PANEL 5  the metathesis, as an actual integration

Run: python validation/solubility_product.py       (a few seconds)
"""

from __future__ import annotations

import math

from chemsim.properties.electrolyte import electrolyte_provider
from chemsim.properties.element_data import REFERENCE_STATES
from chemsim.properties.ion_data import AQUEOUS_IONS, worst_crosscheck
from chemsim.properties.mineral_data import MINERALS
from chemsim.properties.solubility_product import (
    MEASURED_FACTOR,
    UnpricedLattice,
    lattice_verdicts,
    measured_agreement,
    solubility_product,
)

T = 298.15


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------------
rule("PANEL 1 -- WHERE THE DATA WAS, AND THE REFUSAL THAT WAS WRONG ABOUT IT")
# ---------------------------------------------------------------------------
print("""
   The first run of this script concluded, correctly, that a Ksp could not be
   priced: a cation was a SPECTATOR ZERO and an anion was on the pKa basis, so
   the naive number came out 25-29 decades wrong with the sign flipping. It also
   concluded, INCORRECTLY, that fixing it was hand-curation -- because
   `chemicals` has no aqueous ion values and hands back the gas-phase ion.

   !! THAT WAS TRUE OF THE FUNCTIONS AND FALSE OF THE PACKAGE.""")
from chemicals import Hfg, Hfs, S0s                              # noqa: E402

NA = "17341-25-2"
print(f"\n   chemicals.Hfs('{NA}')  -> {Hfs(NA)}")
print(f"   chemicals.S0s('{NA}')  -> {S0s(NA)}")
print(f"   chemicals.Hfg('{NA}')  -> {Hfg(NA)}   <- the GAS-PHASE cation")
print(f"   ion_data['[Na+]'].Hf   -> {AQUEOUS_IONS['[Na+]'].Hf * 1000:.0f}"
      "   <- the aqueous one, same package")
print("""
   The table was shipped all along, as a data file no accessor reads:

       chemicals/Electrolytes/CRC Thermodynamic Properties of Aqueous Ions.tsv

   !! A REFUSAL FROM AN API IS NOT EVIDENCE THAT THE DATA IS ABSENT. This
   project already knew that a SUCCESSFUL call can be a wrong answer (a Joback
   estimate arriving as 'data'). This is the mirror image, and it cost a
   milestone's worth of planning.""")
print(f"\n   ion_data now carries {len(AQUEOUS_IONS)} ions on the conventional "
      "Gf(H+,aq) = 0 basis.")
proton = AQUEOUS_IONS["[H+]"]
print(f"   The anchor is stated by the source, not assumed: H+ reads "
      f"Hf={proton.Hf:g} Gf={proton.Gf:g} S={proton.S0:g}")

# ---------------------------------------------------------------------------
rule("PANEL 2 -- THE CROSS-CHECK, AND WHY IT PROVES THE BASIS")
# ---------------------------------------------------------------------------
print("""
   Every entry's Gf is re-derived from that same row's Hf and S(aq), against the
   element reference entropies in element_data -- a basis the ion table knows
   nothing about:

       ion of charge z:  elements + z H+(aq) -> ion + (z/2) H2(g)
       dS_f = S(ion,aq) + (z/2) S0(H2) - sum nu_el S0(el, reference state)

   !! The (z/2) S0(H2) term is the load-bearing one. It is there ONLY because
   the convention settles the electron against half a hydrogen molecule and sets
   S(H+,aq) = 0. Drop it and a singly charged ion misses by T S0(H2)/2 exactly.
""")
half = T * REFERENCE_STATES["H"].S0 / 2000.0
print(f"   T S0(H2) / 2 at {T} K = {half:.2f} kJ/mol")
na = AQUEOUS_IONS["[Na+]"]
without = na.Hf - T * (na.S0 - REFERENCE_STATES["Na"].S0) / 1000.0
print(f"   Na+ without the term: {without:.2f}  with it: {na.Gf:.2f} kJ/mol"
      f"  gap {abs(na.Gf - without):.2f}")

print(f"\n   {'ion':10s} {'Gf/kJ':>9s} {'residual':>9s}      "
      f"{'ion':10s} {'Gf/kJ':>9s} {'residual':>9s}")
rows = list(AQUEOUS_IONS.values())
half_way = (len(rows) + 1) // 2
for i in range(half_way):
    left = rows[i]
    line = f"   {left.formula:10s} {left.Gf:9.2f} {left.crosscheck:+9.3f}"
    if i + half_way < len(rows):
        right = rows[i + half_way]
        line += (f"      {right.formula:10s} {right.Gf:9.2f} "
                 f"{right.crosscheck:+9.3f}")
    print(line)
worst_ion, worst = worst_crosscheck()
print(f"\n   worst residual {worst:+.3f} kJ/mol on {worst_ion}, tolerance 1.0")
print("   The tabulation is quoted to 100 J/mol and 0.1 J/(mol K), so a few")
print("   hundred J/mol is as close as it can possibly come to itself.")

# ---------------------------------------------------------------------------
rule("PANEL 3 -- EVERY LATTICE, AND FIVE AGAINST A MEASURED SOLUBILITY")
# ---------------------------------------------------------------------------
print()
print(f"   {'mineral':22s} {'dG/kJ':>8s} {'log10 Ksp':>10s} {'s pred/M':>10s} "
      f"{'s meas/M':>10s} {'ratio':>7s}")
for name, record in MINERALS.items():
    try:
        ksp = solubility_product(record)
    except UnpricedLattice:
        print(f"   {name:22s} {'--':>8s} {'--':>10s} {'--':>10s} "
              f"{'--':>10s}  REFUSED")
        continue
    s = ksp.solubility()
    meas = record.fusion_law_bound[1] if record.fusion_law_bound else None
    print(f"   {name:22s} {ksp.dG_diss:8.1f} {ksp.ln_Ksp / math.log(10):10.2f} "
          f"{s:10.3e} {(f'{meas:.3e}' if meas else '--'):>10s} "
          f"{(f'{s / meas:.2f}' if meas else '--'):>7s}"
          f"{'' if ksp.dilute else '   (not dilute -- see below)'}")

agreement = measured_agreement()
worst_ratio = max(max(r, 1.0 / r) for _, _, r in agreement.values())
lo = min(m for _, m, _ in agreement.values())
hi = max(m for _, m, _ in agreement.values())
print(f"""
   {len(agreement)} salts carry a measured 298 K solubility -- entered long ago to condemn
   the FUSION law, and untouched since. Against those, with IDEAL activities and
   nothing fitted anywhere: worst ratio {worst_ratio:.2f}x, over a measured range of
   {hi / lo:.3g}x ({lo:.2e} to {hi:.2e} mol/L).

   Before the aqueous basis landed the same calculation was 25-29 decades out.
   M3's clause is 'at least three salts within a stated factor' and the stated
   factor is {MEASURED_FACTOR:.0f}.

   !! THE RESIDUAL FACTOR HAS A NAME AND IT IS NOT TUNING: gamma. These are
   infinite-dilution values and solubility() assumes activity coefficients of 1.
   The reductio is in the table above -- caustic potash comes out at 1e5 mol/L,
   which is the ideal law extrapolated ten decades past where it means anything.
   Ksp is the product; solubility() is a SCALE, and `dilute` says which side of
   the line a result is on. The engine term consumes Ksp and never solubility().""")

# ---------------------------------------------------------------------------
rule("PANEL 4 -- WHAT STILL REFUSES, AND EACH REFUSAL IS CHEMISTRY")
# ---------------------------------------------------------------------------
verdicts = lattice_verdicts()
refused = {k: v for k, v in verdicts.items() if v}
print(f"\n   {len(verdicts) - len(refused)} of {len(verdicts)} lattices price. "
      f"{len(refused)} refuse:\n")
for name in refused:
    try:
        solubility_product(name)
    except UnpricedLattice as exc:
        for line in str(exc).splitlines():
            print(f"     {line}")
print("""
     !! That refusal is a FACT rather than a gap. CaO does not dissolve to
     Ca(2+) + O(2-); it hydrates to Ca(OH)2 and that dissolves. No aqueous
     compilation carries an oxide ion, and a Ksp for quicklime would be a
     confident answer to a question with no meaning.

     One more target is lost EARLIER, on the lattice half, which had not
     happened before: chrome yellow (PbCrO4) never reaches this module because
     mineral_data refuses it -- CRC has its Hfs and no S0s in any shared
     database, and mixing two tabulations inside one entry is forbidden. The
     ION half was ready for it: [Pb+2] and the chromate basis are both here.""")

# ---------------------------------------------------------------------------
rule("PANEL 5 -- THE METATHESIS, AS AN ACTUAL INTEGRATION")
# ---------------------------------------------------------------------------
print("""
   Nothing below is declared. There is no AgCl species, no template and no
   recipe: four ions go into water and the solubility product decides.
""")
from chemsim.network import build_network                        # noqa: E402
from chemsim.properties import dissociation_templates            # noqa: E402
from chemsim.vessel import Vessel                                # noqa: E402

thermo = electrolyte_provider()
net = build_network(
    ["O", "[Ag+]", "[Cl-]", "[Na+]", "O=[N+]([O-])[O-]"],
    list(dissociation_templates()), thermo=thermo, max_species=40,
)
vessel = Vessel(net, volume=1.0, thermo=thermo, UA=0.0, heat_capacity=0.0)
print(f"   lattices this flask could drop: {', '.join(vessel.precipitation_arrays.names)}")
vessel.charge({"O": 55.0, "[Ag+]": 0.01, "O=[N+]([O-])[O-]": 0.01,
               "[Na+]": 0.01, "[Cl-]": 0.01})
print()
print(f"   {'t/s':>6s} {'Ag+(aq)':>11s} {'Cl-(aq)':>11s} {'Na+(aq)':>11s} "
      f"{'AgCl(s)':>11s} {'T/K':>9s}")
for t in (0.0, 10.0, 60.0, 150.0, 300.0, 600.0, 1200.0):
    if t > vessel.t:
        vessel.run(t - vessel.t)
    st = vessel.state()
    print(f"   {vessel.t:6.0f} {st.n_liquid['[Ag+]']:11.4e} "
          f"{st.n_liquid['[Cl-]']:11.4e} {st.n_liquid['[Na+]']:11.4e} "
          f"{st.n_solid['[Ag+]']:11.4e} {st.T:9.4f}")

state = vessel.state()
ksp = solubility_product("chlorargyrite")
saturated = math.sqrt(ksp.Ksp)
print(f"""
   The supernatant sits at sqrt(Ksp) = {saturated:.4e} M; measured
   {state.n_liquid['[Ag+]'] / vessel.liquid_volume:.4e} M.
   The precipitate is 1:1 to {abs(state.n_solid['[Ag+]'] / state.n_solid['[Cl-]'] - 1):.1e} relative --
   the solid block holds IONS, not a lattice species, so nothing enforces that
   except the stoichiometry row.
   Sodium stays dissolved: {state.n_liquid['[Na+]']:.6f} mol of the 0.010000 charged.
   Conservation report: {vessel.conservation_report()!r}

   And the flask WARMED. AgCl dissolves endothermically ({ksp.dH_diss:+.1f} kJ/mol), so
   precipitation releases that: {vessel.T - 298.15:.4f} K against""")
print(f"   {state.n_solid['[Ag+]'] * ksp.dH_diss * 1000.0 / (55.0 * 75.29):.4f} K "
      "predicted from the two tables and water's heat capacity.")
print("""
   !! DO NOT READ THAT TEMPERATURE OFF A LONGER RUN AT DEFAULT TOLERANCE. The
   same flask taken to 3600 s in ONE call reads 0.038 K -- extent unmoved, so
   not the chemistry; chunking recovers it exactly, and so does rtol 1e-9. The
   likely mechanism is generic (an insulated flask above an open room loses its
   excess to evaporation, and BDF weights T against rtol * 298) but the control
   run did not finish, so 'pre-existing' is a hypothesis and not a measurement
   here. Assert convergence, never a default-tolerance value at a time nothing
   is happening.""")

rule("WHAT M3 STILL OWES")
print("""   Nothing on the data or the term. What is deliberately NOT here:

   * A NUCLEATION BARRIER / metastable zone, which M3 offered to bundle so that
     supersaturation is reachable and seeding becomes a mechanic. The code is
     three lines -- hold the flux at zero until the saturation ratio passes some
     S_crit -- and S_crit is a measured, substance-specific width this project
     has no source for. Inventing it would be exactly the hand-tuned constant
     the sulfur burner's collision-limit A exists as the counter-example to.

   * AN IONIC-STRENGTH MODEL. The factor of 4 in panel 3 is gamma, and closing
     it means Debye-Huckel -- which chemsim-ion-transfer already records as NOT
     substitutable by the Born term. Backlog, and stated rather than hidden.

   * WHICH CRYSTAL A SOLID ION BELONGS TO. The solid block is an ion inventory,
     so two coexisting lattices sharing an ion cannot be told apart. The gate
     bounds it -- a lattice can only dissolve while every one of its ions is in
     the solid -- and the residual case is reported as latent, not refused.""")
print()

"""G2 -- ring deactivation: nitration as a PROCESS rather than an EVENT.

A standing audit, ~1 minute. Five panels:

  1. the table, read back as rate ratios, against what is measured in the
     literature -- including the two places it is WRONG and by how much;
  2. the barrier ladder a nitration network now builds;
  3. the trajectory, which is the finding: 96% trinitro in ten seconds at room
     temperature with no temperature dependence at all, against a staged
     nitration that temperature and time now select between;
  4. what an unsubstituted ring does, which must be nothing;
  5. the reachable clamp, and the physics that is missing behind it.

Run: ``python validation/ring_deactivation.py``
"""

from __future__ import annotations

import time

from rdkit import Chem

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import hammett
from chemsim.reactions.synthesis import NITRATION_RHO, aromatic_nitration
from chemsim.vessel import Vessel


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


TOLUENE, BENZENE = c("Cc1ccccc1"), c("c1ccccc1")
NITRIC, WATER = c("O[N+](=O)[O-]"), c("O")
TNT = c("Cc1cc([N+](=O)[O-])cc([N+](=O)[O-])c1[N+](=O)[O-]")
BAR = "=" * 78
t0 = time.time()
thermo = ThermochemistryProvider()


def nitro_count(smiles: str) -> int:
    return smiles.count("[N+](=O)[O-]")


def by_stage(v: Vessel) -> dict[int, float]:
    """Moles of aromatic material, bucketed by how many nitro groups it carries."""
    st = v.state()
    out: dict[int, float] = {}
    for s in v.species:
        if s in (NITRIC, WATER) or "c" not in s:
            continue
        out[nitro_count(s)] = out.get(nitro_count(s), 0.0) + st.total(s)
    return out


# ---------------------------------------------------------------------------
print(BAR)
print("PANEL 1  THE TABLE, READ BACK AS RATE RATIOS AT rho = %+.1f" % NITRATION_RHO)
print(BAR)
print("""   Every row is sigma-plus (Brown & Okamoto 1958) except the two labelled
   PROXY, which are acceptors with no published sigma-plus and use the aqueous
   sigma -- the case where the two scales agree, argued in reactions/hammett.py.
   `k/k0` is what this template says the substituted ring's nitration rate is,
   relative to benzene's, at 298.15 K.
""")
print(f"   {'substituent':18s} {'sig_m':>7s} {'sig_p':>7s} {'directs':>9s} "
      f"{'used':>7s} {'dEa kJ':>8s} {'k/k0':>11s}  source")
for sub in hammett._TABLE:
    shift = hammett.barrier_shift(NITRATION_RHO, sub.sigma)
    ratio = hammett.rate_ratio(NITRATION_RHO, sub.sigma)
    print(f"   {sub.label:18s} {sub.sigma_m:+7.3f} {sub.sigma_p:+7.3f} "
          f"{'meta' if sub.meta_directing else 'ortho/para':>9s} "
          f"{sub.sigma:+7.3f} {shift / 1000:+8.2f} {ratio:11.3e}  "
          f"{'PROXY' if sub.source != hammett.BROWN_OKAMOTO else ''}")

print("""
   AND THE TWO PLACES IT IS MEASURABLY WRONG, because a model that only prints
   its successes is not an audit:
""")
for smi, label, claim in [
    ("Cc1ccccc1", "toluene", "measured k(toluene)/k(benzene) in mixed acid ~25"),
    ("Nc1ccccc1", "aniline",
     "real aniline in mixed acid is an ANILINIUM ion and is SLOWER than benzene"),
]:
    s = hammett.survey(Chem.MolFromSmiles(smi))
    print(f"   {label:10s} predicted k/k0 = "
          f"{hammett.rate_ratio(NITRATION_RHO, s.sigma_sum):11.3e}   {claim}")
print("""   Toluene is high by about 4x -- half an order of magnitude out of a
   one-parameter model whose rho is quoted over a -6.0 to -7.3 band, and the
   direction (activating, ortho/para) is right. Aniline is wrong by eight orders
   AND in the wrong direction, and it is not a fitting problem: this engine does
   not protonate an amine. That is named in hammett.py and it is panel 5.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 2  THE BARRIER LADDER A NITRATION NETWORK NOW BUILDS")
print(BAR)
print("""   One template, one declared Ea of 60 kJ/mol, and the substrate's own
   substituents doing the rest -- at SETUP, so the RHS is untouched and no
   tolerance-audit exposure is created.
""")
ladders = {}
for rho in (0.0, NITRATION_RHO):
    net = build_network([TOLUENE, NITRIC, WATER], [aromatic_nitration(rho=rho)],
                        thermo=thermo, max_species=80, max_molar_mass=300.0)
    arr = net.to_arrays(thermo)
    rungs: dict[int, set[float]] = {}
    for j, r in enumerate(net.reactions):
        substrate = next(x for x in r.reactants if x != NITRIC)
        rungs.setdefault(nitro_count(substrate), set()).add(
            round(float(arr.Ea[j]) / 1000.0, 2)
        )
    ladders[rho] = (net, rungs)
    tag = "PRE-G2 (rho = 0)" if rho == 0.0 else f"rho = {rho:+.1f}"
    print(f"   {tag}: {len(net.species)} species, {len(net.reactions)} reactions")
    for k in sorted(rungs):
        vals = ", ".join(f"{x:.2f}" for x in sorted(rungs[k]))
        print(f"     substrate carrying {k} nitro group(s):  Ea = {vals} kJ/mol")
print("""
   25.0 kJ/mol per nitro group, and it is not a constant anybody typed: it is
   -ln(10) * R * 298.15 * rho * sigma+_meta(NO2), i.e. -5708 * -6.5 * 0.674.
   Toluene's own 48.46 is the methyl group activating the ring by 11.5 kJ/mol.

   AND NOTE WHAT IS STILL FLAT: each rung is ONE number, so the three isomers of
   dinitrotoluene are still made at identical rates. The sum has no attacked
   carbon in it -- see hammett.py's "no regioselectivity". Staging, yes;
   isomer ratios, no.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 3  THE TRAJECTORY -- and this is the finding")
print(BAR)
print("""   1.0 mol toluene, 3.5 mol nitric acid, 5.0 mol water, 1 L, insulated
   and held at T. Exactly the experiment that refused nitration as G1's
   playground; the top block is what it measured.
""")
for rho in (0.0, NITRATION_RHO):
    net = ladders[rho][0]
    print(f"   {'PRE-G2 (rho = 0)' if rho == 0.0 else f'rho = {rho:+.1f}'}")
    print(f"     {'T/K':>5s} {'t/s':>7s} {'toluene':>9s} {'mono':>9s} "
          f"{'di':>9s} {'tri':>9s}")
    for T, seconds in ((300.0, 10.0), (300.0, 100.0), (340.0, 10.0),
                       (340.0, 3600.0), (380.0, 1000.0)):
        v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e6, kla=0.0,
                   k_vent=0.0, k_diss=0.0, lle=False)
        v.charge({TOLUENE: 1.0, NITRIC: 3.5, WATER: 5.0})
        v.run(seconds)
        s = by_stage(v)
        print(f"     {T:5.0f} {seconds:7.0f} {s.get(0, 0.0):9.4f} "
              f"{s.get(1, 0.0):9.4f} {s.get(2, 0.0):9.4f} {s.get(3, 0.0):9.4f}")
print("""
   THE TOP BLOCK DOES NOT MOVE AT ALL. Same four numbers at 300 K after ten
   seconds and at 380 K after a thousand: there is no stage to catch and nothing
   for an addition rate or a hotplate to control. That is what "one A and one Ea
   for every nitration on every substrate" looks like from the outside.

   THE BOTTOM BLOCK IS A THREE-STAGE PROCESS. At 300 K the pot is mono at ten
   seconds and di at a hundred; at 340 K it is di within ten seconds and STAYS
   di for an hour; only 380 K takes it to tri. That is the escalating-acid,
   escalating-temperature sequence real TNT manufacture uses, and nobody wrote a
   stage: it is three barriers 25 kJ/mol apart.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 4  AN UNSUBSTITUTED RING MUST GIVE THE OLD NUMBER, BIT FOR BIT")
print(BAR)
print("""   The contract every optional term in this engine carries. Benzene's
   sum(sigma+) is 0.0, and `barrier_shift` returns a literal 0.0 rather than a
   small float, so the addition is exact rather than nearly so.
""")
# ⚠ max_species=4 -- benzene, nitric acid, water, nitrobenzene, and nothing
# else. The first draft of this panel used 5, which lets ONE dinitrobenzene in,
# and then reported "Ea identical: False" while printing two numbers that both
# read 60000.000000: the disagreeing entry was the SECOND reaction, on a ring
# that is no longer unsubstituted. A bit-identity claim has to be made about the
# thing it is a claim about.
old = build_network([BENZENE, NITRIC, WATER], [aromatic_nitration(rho=0.0)],
                    thermo=thermo, max_species=4)
new = build_network([BENZENE, NITRIC, WATER], [aromatic_nitration()],
                    thermo=thermo, max_species=4)
a_old, a_new = old.to_arrays(thermo), new.to_arrays(thermo)
print(f"   {len(old.reactions)} reaction on an unsubstituted ring:")
print(f"     species identical:    {old.species == new.species}")
print(f"     Ea identical:         {(a_old.Ea == a_new.Ea).all()}  "
      f"({a_old.Ea[0]:.6f} vs {a_new.Ea[0]:.6f} J/mol)")
print(f"     A identical:          {(a_old.A == a_new.A).all()}")
print(f"     delta identical:      {(a_old.delta == a_new.delta).all()}")
print(f"     shift is literally 0: {hammett.barrier_shift(NITRATION_RHO, 0.0)!r}")
print("""
   And the same holds one level out: every OTHER template in the library leaves
   `hammett_rho` at its default of 0.0, so `substituent_barrier` is never called
   and no network that does not nitrate an arene has moved at all.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 5  THE CLAMP, WHICH IS REACHABLE, AND WHAT IS BEHIND IT")
print(BAR)
print("""   A shift can drive a barrier negative, and a negative activation energy
   is a rate that RISES as the flask cools -- not a fast reaction, a wrong one.
   `hammett.clamp_barrier` floors it at zero and `build_network` says so.
""")
print(f"   {'substrate':22s} {'sum sig+':>9s} {'dEa kJ':>9s} {'Ea kJ':>8s} "
      f"{'clamped':>8s}")
for smi, label in [
    ("c1ccccc1", "benzene"),
    ("Cc1ccccc1", "toluene"),
    ("Oc1ccccc1", "phenol"),
    ("Nc1ccccc1", "aniline"),
    ("Nc1ccc(O)cc1", "4-aminophenol"),
    ("O=[N+]([O-])c1ccccc1", "nitrobenzene"),
    ("CC(=O)Oc1ccccc1C(=O)O", "aspirin"),
]:
    s = hammett.survey(Chem.MolFromSmiles(smi))
    shift = hammett.barrier_shift(NITRATION_RHO, s.sigma_sum)
    raw = 60_000.0 + shift
    print(f"   {label:22s} {s.sigma_sum:+9.3f} {shift / 1000:+9.2f} "
          f"{hammett.clamp_barrier(raw) / 1000:8.2f} "
          f"{'YES' if raw < 0.0 else '':>8s}"
          + (f"   unknown: {', '.join(s.unknown)}" if s.unknown else ""))
print("""
   4-aminophenol goes through the floor and phenol and aniline come close.
   THE CLAMP IS NOT THE FIX. What really happens to an amine or a phenol in
   mixed acid is that it PROTONATES, and an anilinium ion is meta-directing and
   strongly deactivating -- the opposite of what this table says about a free
   base. Coupling protonation into a barrier needs a pKa and the medium's
   acidity, and this engine has the pKa machinery (M3, the ion tables) but
   nothing joining it to a rate. That is the next item, and it is named rather
   than papered over.

   Aspirin's acetoxy oxygen is the other kind of honesty: no sigma-plus for it
   is sourced here, so it is REPORTED as unknown and priced at zero rather than
   being lumped in with a methoxy, which would have made aspirin's ring more
   reactive than anisole's.""")

print()
print(f"   [{time.time() - t0:.1f} s]")

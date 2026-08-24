"""Competing pathways: the Phase-0 spike, reproduced from TEMPLATES.

`spike/spike_reactor.py` hand-wrote four reactions with hand-written stoichiometry
and proved that temperature sensitivity and contamination sensitivity emerge from
integrating a network rather than being scripted. That was the founding
demonstration of this project -- and until now the real code had never reproduced
it, because every network it built had exactly ONE template and therefore no
competition.

Nothing below scripts an outcome. There is no "if too hot, ruin the yield" and no
"if oxygen, contaminate". There are five transformations with barriers, and the
vessel integrates them.

What is different from the spike, and it is not cosmetic:

  * the spike wrote `EtOH + 1/2 O2 -> AcH + H2O` by hand. A graph rewrite cannot
    express half-stoichiometry, and `build_network` REFUSES an unbalanced
    reaction, so the oxidation is written the way it actually balances --
    `alcohol + O2 -> carbonyl + H2O2`. The peroxide is real, it is a curated
    species, and it then over-oxidises the aldehyde to the acid. A single air leak
    therefore produces an aldehyde AND extra acetic acid, which re-enters the
    esterification. That cascade is three templates meeting; nobody wrote it.
  * the spike's reverse esterification rate was a hand-typed A and Ea. Here it is
    DERIVED by detailed balance, so the equilibrium cannot contradict the
    thermochemistry.
  * the spike ran at fixed concentration in a fixed volume. This runs in a real
    vessel with a headspace, an energy balance and activity coefficients, so at
    390 K the pot is above ethanol's boiling point and the sealed flask
    pressurises.
  * the spike's products were four names in a list. Here they are DISCOVERED --
    nobody told the network that diethyl ether or acetaldehyde exists.
"""

from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import alcohol_chemistry
from chemsim.vessel import Vessel

ACOH, ETOH, WATER, O2, N2 = "CC(=O)O", "CCO", "O", "O=O", "N#N"
ESTER, ETHER, ALKENE, ALDEHYDE, PEROXIDE = "CCOC(C)=O", "CCOCC", "C=C", "CC=O", "OO"
NAMES = {
    ESTER: "ethyl acetate", ETHER: "diethyl ether", ALKENE: "ethylene",
    ALDEHYDE: "acetaldehyde", PEROXIDE: "hydrogen peroxide",
    ACOH: "acetic acid", ETOH: "ethanol", WATER: "water",
}
BYPRODUCTS = [ETHER, ALKENE, ALDEHYDE]

thermo = ThermochemistryProvider()
net = build_network(
    [ACOH, ETOH, WATER, O2, N2], alcohol_chemistry(),
    thermo=thermo, max_species=200, max_molar_mass=250.0,
)


def flask(T: float, o2_leak: float = 0.0) -> Vessel:
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=30.0, kla=1.0, k_vent=0.0,
               k_diss=0.0, ingress={O2: o2_leak} if o2_leak else {})
    v.charge({ACOH: 5.0, ETOH: 5.0, WATER: 0.5, N2: 0.02})
    return v


def organics(v: Vessel) -> dict[str, float]:
    st = v.state()
    return {s: st.total(s) for s in (ESTER, *BYPRODUCTS)}


def selectivity(v: Vessel) -> float:
    """Ester as a percentage of all organic PRODUCT formed. This is the number
    that was structurally stuck at 100% before the library existed: with one
    template there was nothing to be impure with."""
    o = organics(v)
    total = sum(o.values())
    return 100.0 * o[ESTER] / total if total > 0 else 0.0


print("=" * 78)
print("WHAT THE NETWORK DISCOVERED  (nobody named the products)")
print("=" * 78)
print(f"   fed:        {', '.join(NAMES.get(s, s) for s in (ACOH, ETOH, WATER, O2, N2))}")
found = sorted(set(net.species) - {ACOH, ETOH, WATER, O2, N2})
print(f"   discovered: {', '.join(NAMES.get(s, s) for s in found)}")
print(f"\n   {len(net.species)} species, {len(net.reactions)} reactions "
      f"from 5 templates -- and it is BOUNDED.")
print("""   Worth understanding rather than being relieved about: explosion comes
   from a template that REGENERATES its own matched group. Polyesterification
   makes an ester bearing another acid and another alcohol, and reached 80
   species from ONE template. These five terminate -- an ether, an alkene and a
   ketone have no hydroxyl left to attack. Adding templates is not what blows up
   a network; adding a self-feeding one is.""")

# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("THE SPIKE'S FOUR SCENARIOS")
print("=" * 78)
print(f"   {'scenario':24s} {'T':>5s} {'ester':>7s} {'ether':>7s} "
      f"{'ethylene':>9s} {'acetald':>8s} {'AcOH':>7s} {'selectivity':>12s}")
for label, T, leak in [
    ("A. clean, controlled T", 340.0, 0.0),
    ("B. too hot (sealed)",    460.0, 0.0),
    ("C. air leak (cool)",     340.0, 1.0e-4),
    ("D. hot AND leaky",       460.0, 1.0e-4),
]:
    v = flask(T, leak)
    v.run(7200.0)
    o = organics(v)
    print(f"   {label:24s} {T:5.0f} {o[ESTER]:7.3f} {o[ETHER]:7.3f} "
          f"{o[ALKENE]:9.4f} {o[ALDEHYDE]:8.4f} {v.state().total(ACOH):7.3f} "
          f"{selectivity(v):11.2f}%")
print("""
   Both failure modes are back, and both are emergent. Heat diverts the alcohol
   into dehydration; air burns it to the aldehyde and on to more acid.""")

# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("THE ORDERING THAT MATTERS: ether BEFORE ethylene")
print("=" * 78)
print("""   Ethanol over sulfuric acid gives diethyl ether at ~140 C and ethylene at
   ~180 C, because the alkene route has the higher barrier (160 vs 125 kJ/mol,
   both from their literature bands). If that ordering is right, the
   ether/ethylene ratio must COLLAPSE as the pot heats up. It is the sharpest
   check that these two barriers are defensible rather than merely plausible.
""")
print(f"   {'T (K)':>6s} {'ester':>8s} {'ether':>9s} {'ethylene':>10s} "
      f"{'ether/ene':>10s} {'selectivity':>12s}")
for T in (340.0, 380.0, 420.0, 450.0, 480.0, 510.0):
    v = flask(T)
    v.run(7200.0)
    o = organics(v)
    ratio = o[ETHER] / o[ALKENE] if o[ALKENE] > 1e-12 else float("inf")
    shown = f"{ratio:10.1f}" if ratio != float("inf") else f"{'--':>10s}"
    print(f"   {T:6.0f} {o[ESTER]:8.3f} {o[ETHER]:9.4f} {o[ALKENE]:10.5f} "
          f"{shown} {selectivity(v):11.2f}%")
print("""
   The ratio falls monotonically by more than two orders of magnitude. There is
   no ether/ethylene selectivity table anywhere in this codebase -- it is two
   Arrhenius terms with different barriers, diverging as T rises.""")

# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("HOW MUCH AIR IT TAKES, and the cascade it sets off")
print("=" * 78)
print(f"   {'O2 in':>10s} {'ester':>8s} {'acetald':>9s} {'H2O2':>9s} "
      f"{'AcOH':>8s} {'selectivity':>12s}")
for leak in (0.0, 1.0e-5, 1.0e-4, 1.0e-3):
    v = flask(360.0, leak)
    v.run(7200.0)
    st = v.state()
    print(f"   {leak:10.0e} {st.total(ESTER):8.3f} {st.total(ALDEHYDE):9.5f} "
          f"{st.total(PEROXIDE):9.5f} {st.total(ACOH):8.3f} "
          f"{selectivity(v):11.2f}%")
print("""
   Read the acetic acid column. It RISES with the leak, because the cascade runs
   ethanol -> acetaldehyde -> acetic acid: the oxidation makes peroxide, the
   peroxide over-oxidises the aldehyde, and the acid it produces re-enters the
   esterification. Three templates, one consequence, and none of them mentions
   the others.

   At the largest leak the ester is gone entirely -- past stoichiometric oxygen
   there is no ethanol left to esterify. That is not a "contamination penalty"
   being applied; it is the alcohol having been consumed by something else.""")

# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("SELECTIVITY IS SMARTS SPECIFICITY -- one template, four answers")
print("=" * 78)
print("""   The oxidation pattern is [CX4;!H0][OX2H1]: a carbinol carbon that still
   has a hydrogen to lose. Everything below follows from that clause alone.
""")
from chemsim.matter import Molecule                                     # noqa: E402
from chemsim.reactions import aerobic_oxidation                         # noqa: E402

ox = aerobic_oxidation()
for smi, note in [
    ("CO", "primary  -> formaldehyde"),
    ("CCO", "primary  -> acetaldehyde"),
    ("CC(C)O", "secondary -> a KETONE, unasked"),
    ("CC(C)(C)O", "tertiary -> REFUSED: no H on the carbinol carbon"),
    ("OCC(O)CO", "a polyol -> BOTH of its distinct sites"),
]:
    out = ox.run((Molecule.from_smiles(smi), Molecule.from_smiles(O2)))
    got = " | ".join(p[0].smiles for p in out) or "(refused)"
    print(f"   {smi:12s} {got:26s} {note}")
print("""
   And the over-oxidation is restricted to an ALDEHYDE, so isopropanol under air
   stops cleanly at acetone while ethanol runs on to acetic acid -- a ketone has
   no hydrogen on the carbonyl carbon to lose. Nobody declared that difference.""")

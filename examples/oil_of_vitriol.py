"""CHAIN 2 -- oil of vitriol, and a catalytic cycle you can watch and lose.

The historical answer to "where does battery acid come from", and the first
GAS-PHASE chain in this project. `GAME_DESIGN.md` section 5 has the graph:

    NATURE                                THE LEAD CHAMBER
      native sulfur   --burn in air-->      SO2
      saltpetre       --+ a little H2SO4--> HNO3 ---> NOx
        (nitre bed: manure + ash + time)              |
                                                      v
           SO2 + NO2 + H2O  --->  H2SO4 + NO     the core step
           NO + 1/2 O2      --->  NO2            regenerates the carrier
           -------------------------------------------------------
           net:  SO2 + 1/2 O2 + H2O -> H2SO4,  catalysed by NOx

Nothing below scripts an outcome. There are two transformations with barriers
and an acid/base table, and the vessel integrates them. In particular there is
no "if too hot, lose the carrier" and no "if vented, fail" -- both of those
happen, and both are consequences of the thermochemistry.

⚠ **THE FIRST ARROW USED TO BE MISSING AND IS NOT ANY MORE.** Burning the
sulfur was not expressible: a global combustion stoichiometry written as one
elementary step is NINTH ORDER in a kernel that takes its exponents from
stoichiometry, and the measurement that disqualified it is kept in
``reactions/library.py``. ``ReactionTemplate.orders`` closed that, so panel 0
now BURNS NATIVE SULFUR and hands the SO2 to the chamber. The chain bottoms out
in a mineral you can dig up, which was the whole point of the framing.
"""

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.electrolyte import (
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions import lead_chamber, sulfur_combustion
from chemsim.vessel import Vessel


def canonical(smiles: str) -> str:
    """!! Every species key must be CANONICAL, and this is not pedantry.

    ``VesselState.total`` is a dict lookup keyed by canonical SMILES, so asking
    it for ``"OS(=O)(=O)O"`` when the network stored ``"O=S(=O)(O)O"`` returns
    0.0 -- a silent zero that reads exactly like a reaction that did not happen.
    It cost real time while this example was being written: the chamber appeared
    to destroy all of its sulfur.
    """
    return Molecule.from_smiles(smiles).smiles


S8 = canonical("S1SSSSSSS1")            # rhombic sulfur -- the element, pinned
SO2 = canonical("O=S=O")
SO3 = canonical("O=S(=O)=O")
NO = canonical("[N]=O")
NO2 = canonical("[O-][N+]=O")
H2O = canonical("O")
O2 = canonical("O=O")
N2 = canonical("N#N")
H2SO4 = canonical("OS(=O)(=O)O")
HNO3 = canonical("O[N+](=O)[O-]")
NO3 = canonical("[O-][N+](=O)[O-]")
HSO4 = canonical("[O-]S(=O)(=O)O")
POTASSIUM = canonical("[K+]")           # saltpetre's spectator cation

NAMES = {
    S8: "sulfur (S8)", SO2: "sulfur dioxide", SO3: "sulfur trioxide",
    NO: "nitric oxide", NO2: "nitrogen dioxide", H2O: "water", O2: "oxygen",
    N2: "nitrogen", H2SO4: "SULFURIC ACID", HNO3: "nitric acid",
    NO3: "nitrate", HSO4: "bisulfate",
}

BAR = "=" * 78
thermo = ThermochemistryProvider()
volatility = VolatilityProvider(thermo)


def rule(title: str) -> None:
    print()
    print(BAR)
    print(title)
    print(BAR)


# ---------------------------------------------------------------------------
rule("PANEL 0 -- THE FLOOR THIS CHAIN STANDS ON, and the one arrow missing")
# ---------------------------------------------------------------------------
print("   Every species in the chain, and where its number comes from:")
print()
print(f"   {'species':18s} {'Gf kJ/mol':>10s} {'Tb K':>8s}  source")
for smi in (S8, SO2, SO3, NO, NO2, H2O, O2, H2SO4, HNO3):
    d = thermo.get(smi)
    tb = f"{d.Tb:.1f}" if d.Tb else "--"
    print(f"   {NAMES[smi]:18s} {d.Gf:10.2f} {tb:>8s}  {d.source[:36]}")
print("""
   SULFUR IS THE ONE THAT MOVED. It read Gf = +276.0 kJ/mol until this
   session -- Joback's estimate for a species whose reference state is zero by
   definition -- which is e^91 in any equilibrium constant. Rhombic S8 is the
   reference state, so the SOLID is 0 and the ideal-gas record above is its
   sublimation energy, +48.68 kJ/mol from JANAF. See properties/element_data.py.

   AND THE BURNER IS IN THE LIBRARY NOW. It was refused once, on measurement,
   and what changed is worth more than the arrow itself.""")

# ---------------------------------------------------------------------------
rule("PANEL 0b -- BURNING THE SULFUR, which needed a DECLARED RATE ORDER")
# ---------------------------------------------------------------------------
burn_net = build_network(
    [S8, O2, N2], [sulfur_combustion()],
    thermo=thermo, volatility=volatility, max_species=40,
)
arr = burn_net.to_arrays()
bidx = {sp: i for i, sp in enumerate(burn_net.species)}
print(f"""   S8 + 8 O2 -> 8 SO2. Thermochemistry excellent (dG = -2449.7 kJ,
   ln K = 988, a hard attractor); network bounded ({len(burn_net.species)} species,
   {len(burn_net.reactions)} reaction). What failed was the RATE LAW.

   THE KERNEL TAKES MASS-ACTION EXPONENTS FROM STOICHIOMETRY, so a GLOBAL
   stoichiometry written as one elementary step was NINTH ORDER, eighth in O2.
   Nine molecules do not meet. Four measurements disqualified it:

     * it needed A = 7e24 to run at all, in units of (L/mol)^8/s -- which is
       not a pre-exponential's;
     * where O2 was in EXCESS the attractor forgave the wrong form entirely:
       100.0% at 550 / 700 / 900 K and at A = 1e20 and 1e24 alike;
     * where O2 was LIMITING it did not: 86.5 / 92.8% against 96.4 / 98.0%, so
       the yield read the author's A rather than the chemistry -- and that
       corrupts the headspace-budget gate, one of the six that work;
     * forced to A = 1e26 the projection created matter: 334.8% yield.

   THE FIX WAS ONE FIELD AND NO HOT-LOOP WORK. ReactionTemplate.orders declares
   the exponents independently of the stoichiometry, and the kernel had ALWAYS
   carried `order` as a matrix separate from `delta` -- it simply never had
   anything to put in it. The burner declares (1, 1, 0, 0, 0, 0, 0, 0, 0):

     order  S8 = {arr.order[0][bidx[S8]]:.0f}   O2 = {arr.order[0][bidx[O2]]:.0f}      <- the rate law (was 1, 8)
     delta  S8 = {arr.delta[0][bidx[S8]]:.0f}  O2 = {arr.delta[0][bidx[O2]]:.0f}   SO2 = +{arr.delta[0][bidx[SO2]]:.0f}   <- the stoichiometry, untouched

   A DECLARED ORDER MAY NOT BE REVERSIBLE, and that is refused at construction.
   Detailed balance derives the reverse from k_f/k_r = K(T), which holds only
   because the exponents ARE the coefficients. With an apparent order it is not,
   so the derived reverse would reach the WRONG equilibrium while looking like
   one that does not. An apparent order says this is not an elementary step, and
   a non-elementary step has no reverse to derive. This one does not need one:
   ln K = 988.""")

print("""
   SO THE CHAIN BOTTOMS OUT IN A MINERAL YOU CAN DIG UP. Everything from here
   down runs on SO2, and panel 0b is where that SO2 comes from: 0.02 mol of
   native sulfur under air at 650 K gives 0.16 mol of it, quantitatively. The
   panels below charge SO2 directly only so each mechanic can be isolated.""")


def burn(T, s8=0.02, o2=0.40, t=600.0):
    v = Vessel(burn_net, volume=1.0, T=T, T_env=T, UA=1.0e4, kla=5.0,
               k_vent=0.0, k_diss=0.05, lle=False)
    v.charge({S8: s8, O2: o2, N2: 0.02})
    v.run(t)
    st = v.state()
    # The OXYGEN balance, not the SO2 shortfall: 2 per O2 plus 2 per SO2 against
    # what was charged. A shortfall is unburnt sulfur; this is created matter.
    created = (2 * st.total(O2) + 2 * st.total(SO2) - 2 * o2) / (2 * o2)
    return st.total(SO2), created, float(v._nL.sum()), v.integrability_report()


print()
print("   THE ANSWER HAS STOPPED READING THE PRE-EXPONENTIAL. O2 limiting")
print("   (0.02 S8 under 0.10 O2, which needs 0.16), 650 K, 600 s:")
print()
print(f"   {'A':>10s} {'SO2 / mol':>12s} {'yield':>8s}")
for A in (1.0e7, 1.0e8, 1.0e9, 1.0e10, 1.0e11):
    bn = build_network([S8, O2, N2], [sulfur_combustion(A=A)], thermo=thermo,
                       volatility=volatility, max_species=40)
    vb = Vessel(bn, volume=1.0, T=650.0, T_env=650.0, UA=1.0e4, kla=5.0,
                k_vent=0.0, k_diss=0.05, lle=False)
    vb.charge({S8: 0.02, O2: 0.10, N2: 0.02})
    vb.run(600.0)
    got = vb.state().total(SO2)
    print(f"   {A:10.0e} {got:12.6f} {100 * got / 0.10:7.3f}%")
print("""
   Four decades of A, one answer. The 1e7 row is not the old stall coming back:
   the burn is merely SLOW and finishes given ten times as long, which is what a
   rate constant is supposed to mean. The old form never finished at all.""")

print()
print("   AND IT NEEDS HEAT. 0.02 S8 under 0.40 O2 (S8 limiting), 600 s:")
print()
print(f"   {'T / K':>7s} {'SO2 / mol':>12s} {'yield':>8s}")
for T in (298.15, 400.0, 450.0, 500.0, 550.0, 650.0):
    so2, _, _, _ = burn(T)   # noqa: F841 -- only the yield is wanted here
    print(f"   {T:7.1f} {so2:12.4e} {100 * so2 / 0.16:7.3f}%")
print("""
   !! BOTH PARAMETERS ARE HAND-AUTHORED and the rate law is an APPARENT one --
   real sulfur combustion is a branched chain, not a bimolecular collision. They
   are BOUNDED rather than fitted: A = 1e10 L/(mol s) is held at the order of
   the gas-kinetic COLLISION LIMIT so it cannot be dialled to taste, which
   leaves Ea as the only freedom. The cost is a SOFT threshold -- 68% at 500 K
   is more than real sulfur does below its ~523 K ignition point. A sharper knee
   needs A = 1e14, a thousand times the collision limit, and buying a prettier
   threshold with an impossible pre-exponential is the wrong trade.""")

print()
print("   !! BURNING IT WALKED INTO A WALL, AND THE WALL IS NOW DOWN. Sulfur")
print("   boils at 717.8 K, so a burn run near that holds only a TRACE:")
print()
print(f"   {'T / K':>7s} {'liquid held':>13s} {'created O':>12s}  {'':4s}")
for T in (550.0, 650.0, 675.0, 690.0, 730.0, 900.0):
    so2, created, n1, _ = burn(T, o2=0.10)
    band = "was IN BAND" if T in (675.0, 690.0) else ""
    print(f"   {T:7.0f} {n1:13.3e} {created:12.3e}  {band}")
print()
print("   ...and the SAME 690 K flask with O2 made non-limiting, so that nothing")
print("   is driven to zero beside the trace of condensate:")
print()
_, created_clean, n1_clean, _ = burn(690.0, o2=0.10, s8=0.002)
print(f"   {690.0:7.0f} {n1_clean:13.3e} {created_clean:12.3e}  the gates alone")
print("""
   WHAT WAS WRONG. If the trace landed inside DRYOUT_MOLES (1e-6 mol) the flask's
   two liquid gates OVERLAPPED -- layer 1's evaporation gated by a `wet` ramp,
   the dry-flask branch by `1 - wet` -- while the mole fractions were floored on
   the SAME scale, so inside the band they summed to 0.57, every activity was
   understated by that factor, and 690 K reported 111% YIELD. Clean on both sides
   and wrong only inside: two gates meeting, not one bad one.

   WHAT FIXED IT, AND THE PART THAT IS COUNTER-INTUITIVE. The clamp was the bug:
   a `max(N, eps)` that exists to keep 0/0 out must not share a scale with a
   gate, so it moved 24 decades down and the mole fractions now sum to ONE at
   every holding. The gates themselves stayed COMPLEMENTARY. Making them
   disjoint -- which is what fixed the second liquid layer, panel 9's story --
   was tried and is WRONG here: disjoint halves are both zero AT the scale, and a
   condenser is exactly the thing that comes to rest there. It stalled at
   9.998e-07 mol, the pot lost its latent-heat sink, and the REFLUX PLATEAU went
   352.89 -> 370.39 K. The same fix, one vessel over.

   WHAT IS LEFT, NAMED. With O2 limiting the row above still reads ~1e-5, and
   that is the OXYGEN CROSSING ZERO, not the band: make O2 non-limiting and the
   same flask closes to 1.9e-11. It is the ordinary stiff-reactant-at-zero
   residual (M7's), it CONVERGES under refinement where the band did not, and
   its value at default tolerance is LUCK -- nudging the inert nitrogen charge by
   0.5% swings it five orders of magnitude, which is why no number in this panel
   is asserted anywhere as a tolerance.""")

# ---------------------------------------------------------------------------
rule("PANEL 1 -- WHAT THE CHAMBER DISCOVERED (nobody named the products)")
# ---------------------------------------------------------------------------
chamber_net = build_network(
    [SO2, NO, NO2, H2O, O2, N2], lead_chamber(),
    thermo=thermo, volatility=volatility, max_species=40,
)
print(f"   fed:        {', '.join(NAMES[s] for s in (SO2, NO, NO2, H2O, O2, N2))}")
found = sorted(set(chamber_net.species) - {SO2, NO, NO2, H2O, O2, N2})
print(f"   discovered: {', '.join(NAMES.get(s, s) for s in found)}")
print(f"\n   {len(chamber_net.species)} species, {len(chamber_net.reactions)} "
      f"reactions from 2 templates -- and it is BOUNDED.")
for r in chamber_net.reactions:
    print(f"     {r.name:46s} A={r.A:.3e}  Ea={r.Ea:9.1f} J/mol")
print("""
   Two of those four were DERIVED by detailed balance, not typed. And the
   regeneration's forward pair is not hand-authored either: 2 NO + O2 -> 2 NO2
   is genuinely termolecular, so its measured k = 1.2e-31 exp(530/T)
   cm^6 molecule^-2 s^-1 converts straight into these units. Its activation
   energy is NEGATIVE, which is real -- the reaction runs through an ONOONO
   dimer and goes faster as it gets colder.""")


def chamber(T=350.0, k_vent=0.0, nox=0.004, duration=3600.0, so2=0.04):
    v = Vessel(chamber_net, volume=2.0, T=T, T_env=T, UA=1.0e4, kla=5.0,
               k_vent=k_vent, k_diss=0.05, lle=False)
    v.charge({SO2: so2, O2: 0.05, N2: 0.10, H2O: 0.60, NO2: nox})
    v.run(duration)
    return v


# ---------------------------------------------------------------------------
rule("PANEL 2 -- THE CYCLE TURNS, AND IT HAS A TEMPERATURE CEILING")
# ---------------------------------------------------------------------------
print("   0.04 mol SO2, 0.05 O2, 0.60 water, 4 mmol of NOx carrier, sealed, 1 h.")
print()
print(f"   {'T / K':>6s} {'H2SO4':>9s} {'SO2 left':>9s} {'NO':>9s} {'NO2':>9s} "
      f"{'yield':>8s}")
for T in (320.0, 350.0, 400.0, 500.0, 650.0):
    st = chamber(T=T).state()
    print(f"   {T:6.0f} {st.total(H2SO4):9.5f} {st.total(SO2):9.5f} "
          f"{st.total(NO):9.5f} {st.total(NO2):9.5f} "
          f"{100 * st.total(H2SO4) / 0.04:7.1f}%")
print("""
   !! READ THE LAST ROW. At 650 K the carrier has FLIPPED: essentially all of it
   sits as NO and almost none as NO2, and NO cannot oxidise sulfur dioxide. The
   regeneration is written reversible, so above ~600 K its reverse -- NO2 falling
   apart to NO and O2 -- takes over and the chamber loses its oxidant.

   NOTHING DECLARES A MAXIMUM OPERATING TEMPERATURE. Detailed balance derives
   that ceiling from the formation data, and it is why a real lead chamber is a
   big cool room rather than a furnace. Combined with the negative barrier on the
   regeneration, "run it cool" is right for two independent reasons and neither
   was written down.""")


# ---------------------------------------------------------------------------
rule("PANEL 3 -- THE CARRIER IS CATALYTIC, AND THE TURNOVER IS THE PROOF")
# ---------------------------------------------------------------------------
print("   If NOx were a reagent the acid would be capped by how much was")
print("   charged. It is not: 0.5 mmol of carrier makes 40 mmol of acid.")
print()
print(f"   {'NOx charged':>12s} {'H2SO4 / mol':>12s} {'turnovers':>10s}")
for nox in (0.0400, 0.0080, 0.0020, 0.0005):
    st = chamber(nox=nox, duration=7200.0).state()
    print(f"   {nox:12.4f} {st.total(H2SO4):12.5f} "
          f"{st.total(H2SO4) / nox:10.2f}")
print("""
   80 turnovers on the smallest charge. THIS IS WHAT A FOLDED CATALYST CANNOT
   DO. The acid catalysis in reactions/library.py puts hydronium on both sides
   of one SMARTS, so its exponent is 1 and its stoichiometry is 0 -- one
   reaction, no cycle, nothing to watch. Here NO2 is genuinely consumed and NO
   genuinely regenerated, so the carrier has an integrated concentration that
   rises and falls, and CATALYST_REFERENCE has nothing to do with it.""")


# ---------------------------------------------------------------------------
rule("PANEL 4 -- AND YOU CAN LOSE IT BY VENTING")
# ---------------------------------------------------------------------------
print("   The carrier is a GAS. Open the chamber and it leaves.")
print()
print(f"   {'k_vent':>10s} {'H2SO4':>9s} {'NOx left':>9s} {'yield':>8s}")
for kv in (0.0, 1.0, 10.0, 1.0e3):
    st = chamber(k_vent=kv).state()
    print(f"   {kv:10.1f} {st.total(H2SO4):9.5f} "
          f"{st.total(NO) + st.total(NO2):9.5f} "
          f"{100 * st.total(H2SO4) / 0.04:7.1f}%")
print("""
   Sealed 100%, open 22-42%. "Keep the chamber shut" is a skill, and it runs on
   the headspace-budget mechanic that already existed.

   !! IT IS NOT MONOTONE IN k_vent, and that is worth stating rather than
   smoothing over. A vent is bidirectional bulk flow: a LARGE conductance holds
   the chamber at ambient pressure so little net volume moves, while a small one
   needs a real pressure difference to pass the same flux and sweeps more
   carrier out with it. The loss is set by how much gas crosses the boundary,
   not by the conductance.""")


# ---------------------------------------------------------------------------
rule("PANEL 5 -- THE NITRE BED, AND THE TEMPLATE THAT TURNED OUT NOT TO EXIST")
# ---------------------------------------------------------------------------
print("""   The brief for this chain asked for a "nitrate-liberation template".
   There is no such template here, because none is needed -- and finding that
   out is worth more than writing one would have been.

   Liberating nitric acid from saltpetre is a PROTON TRANSFER:

       NO3-  +  H2SO4  <=>  HNO3  +  HSO4-

   and both pKa values are already in properties/electrolyte._PAIRS (sulfuric
   acid -3.0, nitric acid -1.4). The existing mineral_oxyacid_dissociation
   template plus detailed balance is the whole mechanism. Sulfuric acid is the
   stronger acid by 1.6 pKa units, so it protonates nitrate; nitric acid boils
   at 356 K and the bisulfate does not, so distillation takes it away.""")
ions = electrolyte_provider(base=thermo, volatility=volatility)
print()
print(f"   {'species':14s} {'Gf kJ/mol':>10s}  basis")
for smi, label in ((NO3, "nitrate"), (HSO4, "bisulfate"),
                   (HNO3, "nitric acid"), (H2SO4, "sulfuric acid")):
    d = ions.get(smi)
    print(f"   {label:14s} {d.Gf:10.2f}  {d.source[:44]}")
print("""
   !! AND DO NOT SUBTRACT THOSE FOUR NUMBERS DIRECTLY -- two of them are on
   different standard states. The ions are anchored on the acid in its LIQUID
   standard state (see properties/electrolyte) while the neutrals above are
   ideal-gas, so a naive difference reads dG = -46.2 kJ where the pKa gap says
   -9.1. reactions.thermo applies standard_state.reaction_shift and gets it
   right; a script doing its own arithmetic on provider output does not. That
   error was made while writing this example.""")

nitre_net = build_network(
    [HNO3, H2SO4, H2O, POTASSIUM, N2], dissociation_templates(),
    thermo=ions, volatility=volatility, max_species=60,
)
print(f"\n   nitre-bed network: {len(nitre_net.species)} species, "
      f"{len(nitre_net.reactions)} reactions, from the dissociation set alone")


# ---------------------------------------------------------------------------
rule("PANEL 6 -- IT BOOTSTRAPS, AND THAT IS A DESIGN FEATURE")
# ---------------------------------------------------------------------------
print("""   Liberating HNO3 from saltpetre needs sulfuric acid, and sulfuric acid
   is what the chamber makes. The chain cannot start itself: the FIRST batch
   needs a seed from somewhere else, and historically that is green vitriol --
   FeSO4, dry-distilled. Which is literally where the name "oil of vitriol"
   comes from.

   The seed is in the mineral table and the arithmetic works:""")
from chemsim.properties.mineral_data import MINERALS   # noqa: E402
gv = MINERALS["green vitriol"]
print(f"     {gv.name}: Gf(solid) = {gv.Gf_solid} kJ/mol  [{gv.source[:44]}]")
print(f"       ions when dissolved: {list(gv.ions)}")
print(f"       purpose: {gv.purpose}")
print("""
   !! WHAT IS NOT BUILT: the dry distillation itself. FeSO4 -> Fe2O3 + SO3 is a
   SOLID-PHASE DECOMPOSITION, and this engine has no solid-phase reactions --
   its solids dissolve and react in a liquid, which a dry retort has none of.
   That is a named engine gap on the backlog, not a data gap: green vitriol's
   solid-basis formation energy is curated and waiting for it.

   So the seed is an INPUT to the chain today. The dependency is real and the
   player still feels it -- you cannot make the first batch of acid from
   saltpetre alone -- which is the beat the design asked for.""")


# ---------------------------------------------------------------------------
rule("PANEL 7 -- CONSERVATION, AND THE RESIDUAL THAT WENT AWAY")
# ---------------------------------------------------------------------------
v = chamber(T=350.0)
st = v.state()
s_in, s_out = 0.04, st.total(SO2) + st.total(H2SO4)
n_in, n_out = 0.004, st.total(NO) + st.total(NO2)
print(f"   SULFUR    charged {s_in:.6f}  found {s_out:.6f}  "
      f"closure {100 * s_out / s_in:.4f}%")
print(f"   CARRIER N charged {n_in:.6f}  found {n_out:.6f}  "
      f"closure {100 * n_out / n_in:.4f}%")
print(f"\n   {v.conservation_report() or 'conservation clean'}")
print("""
   !! THE CARRIER USED TO CLOSE ~0.5% OUT, AND IT NOW CLOSES EXACTLY. That row
   was written as a residual worth naming rather than a defect: the NO/NO2 pair
   is stiff -- the derived reverse of the regeneration runs at A = 2.4e19 -- so
   the non-negative projection had a fast mode to settle and created ~2e-5 mol
   of NO it could not take back from a positive holding. It was small against
   the total nitrogen charged (0.01%, N2 included), which is why the excursion
   ratio never tripped, and it was REPORTED on the channel that exists for it.

   It was the same solid-gate knee panel 8 is about, seen at a charge four
   orders larger. Fixing that made this row exact and the report empty, which is
   the cleanest confirmation available that the two were one defect: nothing in
   this panel was touched.""")

# ---------------------------------------------------------------------------
rule("PANEL 8 -- THE REAL BUG THIS CHAIN FOUND, AND WHAT CLOSING IT TOOK")
# ---------------------------------------------------------------------------
print("""   Charge the chamber with SO2, water and air and NO CARRIER AT ALL --
   the carrier species in the network, but at exactly zero. It should do
   nothing. Until this session it reached 89% yield.""")
print()


def carrier_free(duration, chunks=1):
    v = Vessel(chamber_net, volume=2.0, T=350.0, T_env=350.0, UA=1.0e4,
               kla=5.0, k_vent=0.0, k_diss=0.05, lle=False)
    v.charge({SO2: 0.04, O2: 0.05, N2: 0.10, H2O: 0.60})
    for _ in range(chunks):
        v.run(duration / chunks)
    return v


print(f"   {'t / s':>8s} {'NOx created':>13s} {'H2SO4':>12s} "
      f"{'was (NOx)':>12s} {'was (H2SO4)':>12s}")
WAS = {1.0: (1.40e-07, 3.27e-06), 100.0: (3.22e-05, 5.34e-04),
       3600.0: (1.21e-04, 3.58e-02)}
for t in (1.0, 10.0, 100.0, 600.0, 3600.0):
    st = carrier_free(t).state()
    nox = st.total(NO) + st.total(NO2)
    old = WAS.get(t)
    cols = (f"{old[0]:12.2e} {old[1]:12.2e}" if old else f"{'':12s} {'':12s}")
    print(f"   {t:8.0f} {nox:13.4e} {st.total(H2SO4):12.4e} {cols}")
v = carrier_free(3600.0)
print()
print(f"   {v.conservation_report() or 'conservation clean'}")
print("""
   THE CHAMBER IS INERT NOW, AND THE REPORT IS CLEAN RATHER THAN QUIET. 1.6e-20
   mol is round-off on 0.11 mol of nitrogen -- eleven orders below the 1e-6 mol
   scale anything downstream can see.

   AND THE CHUNKING DEPENDENCE IS GONE WITH IT. It used to matter which is the
   sharpest possible statement that the amount was numerical: each run() builds
   a fresh BDF, so the overshoot was per-solve.""")
print()
print(f"   {'chunks':>8s} {'NOx created':>13s} {'H2SO4':>12s}   was")
WAS_CHUNKS = {1: (1.2089e-04, 3.5786e-02), 6: (1.2086e-04, 3.4511e-02),
              60: (8.2571e-06, 5.3901e-03)}
for chunks in (1, 6, 60):
    st = carrier_free(3600.0, chunks).state()
    w = WAS_CHUNKS[chunks]
    print(f"   {chunks:8d} {st.total(NO) + st.total(NO2):13.4e} "
          f"{st.total(H2SO4):12.4e}   {w[0]:.2e} / {w[1]:.2e}")
print("""
   TWO HALVES, EACH INDIVIDUALLY CORRECT -- WHICH IS WHY IT SURVIVED SO LONG.

   THE SEED WAS A KNEE IN THE CRYSTALLISATION TERM. Dissolution was gated with
   avail = nS/(nS + SOLID_EPS), SOLID_EPS = 1e-9: zero at nS = 0, but with a
   SLOPE of 1e9 there, so an EMPTY solid block carried a Jacobian diagonal of
   k_diss * excess / eps. Measured on this flask, for blocks holding NOTHING:

       NO     -3.61e+07        H2SO4  -3.95e+07
       NO2    -3.95e+07        water  -1.83e+06

   BDF overshot those blocks negative, project_non_negative zeroed them, and a
   species with no positive holding to settle against had matter CREATED. That
   is the same 4e6-to-1.4e8 band recorded for the second liquid layer's
   identical N/(N+eps) knee, which had already been fixed once. The solid twin
   had never got the same treatment.

   THE AMPLIFICATION WAS THE CHEMISTRY, AND IT HAD NO BOUND. A catalytic cycle
   has no fixed gain on its catalyst -- panel 3 measured 80 turnovers -- so a
   round-off-sized carrier charge produced a MACROSCOPIC amount of acid. 296x.

   NO LOCAL GUARD COULD HAVE CAUGHT IT, AND THAT IS STRUCTURAL. check_raw_solution
   bounds an excursion as a RATIO against the amount present, with a 1e-3 mol
   floor for species legitimately at zero, so 1.4e-7 was four orders under the
   threshold and was correctly REPORTED rather than refused. No check on one
   integration step can see that a round-off residual is about to be multiplied
   300x by a downstream cycle. It had to be fixed where it was made.

   !! AND THE FIX IS NOT THE SMOOTHSTEP THE LIQUID GATE USED. A smoothstep is
   zero AND FLAT at zero, which is why the liquid layer needed a companion
   reabsorption term to keep num_jac from inflating its perturbation factor on
   an undifferentiable column. A companion here would have sat opposite the
   PRECIPITATION branch -- which is ungated by design, because anything can
   nucleate -- i.e. exactly the overlapping-gate arrangement that made the
   benzoic-acid acidification unsolvable the last time. One term has to govern
   this block near zero.

   SO THE GATE'S SCALE BECAME THE DRIVING FORCE INSTEAD OF A CONSTANT:

       eps = SOLID_GATE_TIME * k_diss * excess        (SOLID_GATE_TIME = 10 ms)

   which is a resistance-in-series form -- 1/rate = 1/(k_diss*excess) + tau/nS --
   so dissolution is limited BOTH by distance from saturation AND by how much
   solid is there. The empty-block slope collapses to exactly 1/tau = 100 for
   EVERY species. That independence is the point: the old knee got WORSE the
   more dilute a species was, which is precisely why the most dilute one seeded
   the cycle.

   THE VALUE IS A MEASUREMENT, NOT A PREFERENCE. Swept on this flask, the solid
   columns' largest entry stops shrinking at tau = 1e-2 (1.41e6 at 1e-4, 1.36e5
   at 1e-3, 1.29e4 at 1e-2, and 1.49e4 at 1e-1 -- slightly WORSE). So 1e-2 is the
   smallest tau, i.e. the least distortion of real dissolution, at which this
   gate has stopped being the stiffest thing in the block.

   IT MOVED NO SOLUBILITY. excess -> 0 drives the scale to zero and the gate to
   1, so equilibrium is untouched: benzoic acid under water dissolves the same
   0.026826 mol at every tau in the sweep, identical to six decimals, and a
   1e-5 mol crop now dissolves to EXACTLY 0.0 where the constant knee left
   -9.4e-10 behind.

   AND THE CLASS IS CLOSED BY MEASUREMENT RATHER THAN BY ASSERTION. The two
   other candidates were checked:
     * MELT_BLEND is NOT a member -- it is a clip, slope 10, not a knee.
     * DRYOUT_MOLES WAS the same shape (a dry flask's wet-ramp entry read
       4.6e5) and was judged LATENT on this evidence -- a dry flask conserves
       matter to 3.5e-18 mol at 3600 s, because a species with no LIQUID still
       has a GAS holding for the projection to settle against. !! THAT VERDICT
       WAS ONLY AS GOOD AS THE PROBE: the same gate at 690 K, 7 bar and with a
       CONDENSING species created 11% of its oxygen. A gate's damage scales with
       what multiplies it. It is closed now -- panel 0b -- and the ramp's 4.6e5
       entry went with it, because a smoothstep is flat at zero.
     * a dry flask's largest entry is not a gate at all: d(T)/d(liquid) at
       -2.2e6, which is an empty flask having no thermal mass. That is the
       superheated-flask fragility VesselIntegrator.diagnose already names.

   SO GAME_DESIGN SECTION 3(d) KEEPS ITS CONVERSE, now as a property rather
   than a warning: NO CATALYTIC CYCLE MAY START FROM ZERO CATALYST. The nitre
   is a reagent you have to supply, and panel 3's 80 turnovers only mean
   something because zero turnovers is also reachable.""")


rule("WHAT THIS CHAIN COST")
print("""   DATA:    one element pinned (S8), and nothing else. Every gas in the
            chain was already priced experimentally.
   TEMPLATES: THREE now, and one of them has BOTH parameters measured. The
            burner's two are hand-authored and say so.
   ENGINE:  THREE walls, all closed, and NONE needed hot-loop work.
            SOLID_GATE_TIME made the gate's scale the driving force instead of
            a constant; ReactionTemplate.orders put an exponent where the
            kernel already had a matrix waiting for one; and the dryout band
            took the SCALE out of a 0/0 clamp that was never meant to gate.
   STILL OPEN: solid-phase reactions, for the green-vitriol seed. The DRYOUT
            BAND the burner found on its way in is CLOSED -- see panel 0b --
            and what is left in the O2-limiting column is the depleted
            reactant, which M7 owns.

   FOUR MECHANICS THAT NOBODY WROTE: a catalytic cycle with 80 turnovers, a
   temperature ceiling at ~600 K, a carrier you lose by opening the vessel, and
   an ignition threshold that comes out of one barrier.

   AND ONE THAT NOBODY CAN WRITE ANY MORE: the chain used to start from nothing,
   because the solver's own round-off seeded the catalyst. It does not. A
   carrier-free chamber is inert to eleven orders below anything the game can
   see, so the nitre is a REAGENT YOU MUST SUPPLY -- which is what makes panel
   3's 80 turnovers mean something.""")

"""G6 -- the encounter plateau: where the Hammett line stops being a line.

A standing audit, ~27 s. Six panels:

  1. THE FORM QUESTION, MEASURED. The physically-correct-sounding form is an
     absolute encounter ceiling, ``min(k_hammett, k_enc)``. It cannot fire here,
     and this panel is the measurement that says so -- which is why the declared
     model is a capped RATIO and why there is no RHS edit and no tolerance audit
     in this session;
  2. the line against the two SOURCED observables, and the FLOOR that toluene
     puts under the constant -- the sulfuric-acid plateau is measurably too low;
  3. the corpus cost, route by route, plateau against bare line. ⚠ It is ZERO,
     and one route's first step is slowed 2000x to get there;
  4. the ONE-SIDED decision, measured on the TNT ladder: a two-sided cap at the
     same value destroys G2's staging;
  5. aniline -- what the plateau plus G5's split buy, and the one thing they
     COST: G5's crossover moves five decades and its agreement with the real H0
     band went with it;
  6. the clamp that is now unreachable, and why the function stays.

Run: ``python validation/saturation.py``
"""

from __future__ import annotations

import contextlib
import io
import math
import time

from chemsim.constants import R
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import hammett
from chemsim.reactions.synthesis import NITRATION_RHO, aromatic_nitration
from chemsim.reactions.thermo import COLLISION_LIMIT, T_REF
from chemsim.vessel import Vessel

BAR = "=" * 78
t0 = time.time()
thermo = ThermochemistryProvider()


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


BENZENE, TOLUENE, PHENOL = c("c1ccccc1"), c("Cc1ccccc1"), c("Oc1ccccc1")
NITRIC, WATER = c("O[N+](=O)[O-]"), c("O")
ANILINE, ANILINIUM = c("Nc1ccccc1"), c("[NH3+]c1ccccc1")
NB = c("O=[N+]([O-])c1ccccc1")
TNT = c("Cc1cc([N+](=O)[O-])cc([N+](=O)[O-])c1[N+](=O)[O-]")
PICRIC = c("Oc1c([N+](=O)[O-])cc([N+](=O)[O-])cc1[N+](=O)[O-]")
PKA_ANILINIUM = 4.62          # the value in electrolyte._PAIRS
POT_FLOOR_PH = -0.789         # the acidity floor measured in G5, panel 4
DECLARED_EA = aromatic_nitration().Ea
DECLARED_A = aromatic_nitration().A
NO_PLATEAU = math.inf


def sigma(smiles: str) -> float:
    return hammett.survey(Molecule.from_smiles(smiles)._mol).sigma_sum


def k(Ea: float, T: float, A: float = DECLARED_A) -> float:
    return A * math.exp(-Ea / (R * T))


def k_diffusion(T: float) -> float:
    """A Smoluchowski diffusion ceiling in water, for scale.

    ⚠ ANCHORED AND LABELLED: 7e9 L/(mol s) at 298 K with the 16 kJ/mol
    temperature dependence of water's viscosity. It is quoted to ONE FIGURE and
    is here only to be compared against, never to be used as a rate.
    """
    return 7.0e9 * math.exp(-16_000.0 / R * (1.0 / T - 1.0 / 298.15))


def barrier(smiles: str, saturation: float = hammett.SATURATION_DECADES) -> float:
    return hammett.clamp_barrier(
        DECLARED_EA + hammett.barrier_shift(NITRATION_RHO, sigma(smiles), saturation)
    )


def run(seed, charge, T, seconds, watch, saturation, generations=1,
        max_species=60) -> float:
    """One route, charged and integrated. ⚠ Nothing here is credited on an
    argument -- S1's precedent, and G4 made it a three-time finding."""
    with contextlib.redirect_stdout(io.StringIO()):
        net = build_network(
            seed, [aromatic_nitration(saturation=saturation)], thermo=thermo,
            generations=generations, max_species=max_species,
        )
        v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e6, kla=0.0,
                   k_vent=0.0, k_diss=0.0, lle=False)
        v.charge(charge)
        v.run(seconds)
    return v.state().total(watch)


# ---------------------------------------------------------------------------
print(BAR)
print("PANEL 1  THE FORM QUESTION: AN ABSOLUTE ENCOUNTER CEILING CANNOT FIRE")
print(BAR)
print(f"""   The item was posed as a choice between a capped RATIO and an absolute
   ENCOUNTER CEILING, `min(k_hammett, k_enc)`, with the second called the
   physically correct one. It is -- for an ELEMENTARY step. This template's rate
   law is written on the arene and HNO3, so the nitronium pre-equilibrium is
   folded into Ea and k is a STOICHIOMETRIC constant. Below, the whole model in
   the band the nitration routes run in.

   A = {DECLARED_A:.1e} L/(mol s), declared Ea = {DECLARED_EA:.0f} J/mol, rho = {NITRATION_RHO:+.1f}
""")
SUBS = [("benzene", BENZENE), ("toluene", TOLUENE), ("mesitylene",
        c("Cc1cc(C)cc(C)c1")), ("phenol", PHENOL), ("aniline", ANILINE),
        ("4-aminophenol", c("Nc1ccc(O)cc1"))]
print("   k(T), L/(mol s), with THE PLATEAU LIFTED -- the worst case the line can ask for")
print(f"   {'T/K':>5s} " + " ".join(f"{n[:12]:>12s}" for n, _ in SUBS)
      + f" {'diffusion':>12s} {'COLL_LIMIT':>12s}")
for T in (300.0, 320.0, 340.0, 360.0, 380.0):
    print(f"   {T:5.0f} " + " ".join(
        f"{k(barrier(s, NO_PLATEAU), T):12.4e}" for _, s in SUBS)
        + f" {k_diffusion(T):12.4e} {COLLISION_LIMIT:12.4e}")
CLAMPS = c("Nc1ccc(O)cc1")
unclamped = max(
    k(barrier(s, NO_PLATEAU), T) / k_diffusion(T)
    for _, s in SUBS if s != CLAMPS for T in (300.0, 340.0, 380.0)
)
clamped = k(barrier(CLAMPS, NO_PLATEAU), 300.0) / k_diffusion(300.0)
print(f"""
   THE CEILING BINDS ON EXACTLY ONE ROW, AND IT IS THE ROW THAT WAS ALREADY
   GUARDED. Every substrate whose barrier is still positive sits well under a
   diffusion ceiling -- the fastest of them anywhere in the band is
   {100 * unclamped:.2f}%. The single exception is 4-aminophenol, and only because
   `clamp_barrier` has already floored its barrier at zero, which leaves k = A =
   {DECLARED_A:.0e} and {100 * clamped:.0f}% of the ceiling at 300 K. So
   `min(k_hammett, k_enc)` would fire on precisely the case a floor already
   catches, for the price of an RHS edit and ten minutes of tolerance audit --
   and `clamp_barrier` is a cruder version of the same guard, pinning k at the
   declared A rather than at a diffusion rate. A is {DECLARED_A:.0e}, a decade
   under this project's own COLLISION_LIMIT of {COLLISION_LIMIT:.0e} at T_REF =
   {T_REF:.2f}.

   AND THE REASON THAT IS THE WRONG GUARD ANYWAY: THE OBSERVABLE IS SIX
   DECADES BELOW THE CEILING. Real nitration
   saturates at a RELATIVE reactivity of a few hundred times benzene (panel 2),
   and benzene at 340 K here runs at {k(DECLARED_EA, 340.0):.3g} L/(mol s), so the
   measured plateau lands near {k(DECLARED_EA, 340.0) * 10 ** hammett.SATURATION_DECADES:.3g} --
   six decades below any diffusion constant. An absolute ceiling in THESE units
   would have to be k_enc * [NO2+]/[HNO3], which is a property of the MEDIUM'S
   ACIDITY, and G5 measured that this engine has nowhere to put one.
   So the capped ratio is not the cheap approximation to the right model. It is
   the only one of the two that can express the thing that was measured.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 2  THE TWO SOURCED OBSERVABLES, AND THE FLOOR TOLUENE PUTS ON THE CAP")
print(BAR)
print("""   Belson & Strachan, J. Chem. Soc. Perkin Trans. 2, 1989, 15. Aqueous
   nitric acid, 24-41 mol% HNO3, 293-333 K:

     benzene : toluene : p-xylene : mesitylene = 1 : 22 : 256 : 485
     at ~30 mol% and 25 C, and "with p-xylene and mesitylene the nitration is
     diffusion-controlled, but not so with the others"

   Coombes, Moodie & Schofield, J. Chem. Soc. B, 1968, 800. Concentrated
   sulphuric and perchloric acids: a limit exists beyond which further
   activation does not increase the rate and it IS the encounter rate; at the
   top of their acidity range benzene's own rate comes within a SIXTH of it.
""")
MEASURED = [("benzene", BENZENE, 1.0, False), ("toluene", TOLUENE, 22.0, False),
            ("p-xylene", c("Cc1ccc(C)cc1"), 256.0, True),
            ("mesitylene", c("Cc1cc(C)cc(C)c1"), 485.0, True)]
CANDIDATES = [(NO_PLATEAU, "no plateau"), (2.686, "2.686 DECLARED"),
              (2.408, "2.408 p-xylene"), (0.778, "0.778 H2SO4")]
print(f"   {'substrate':12s} {'measured':>9s} {'diff-ctl':>9s} "
      + " ".join(f"{lbl:>14s}" for _, lbl in CANDIDATES))
for name, smi, meas, diff in MEASURED:
    print(f"   {name:12s} {meas:9.0f} {('yes' if diff else 'no'):>9s} " + " ".join(
        f"{hammett.rate_ratio(NITRATION_RHO, sigma(smi), saturation=cap):14.4g}"
        for cap, _ in CANDIDATES))
_tol = NITRATION_RHO * sigma(TOLUENE)
print(f"""
   THE DECLARED VALUE IS THE MESITYLENE DATUM, log10(485) = 2.686. It
   reproduces that point exactly, because it IS that point; p-xylene it puts 1.9x
   high, which is the factor the plateau's own two data differ by.

   AND TOLUENE IS WHAT BOUNDS THE CONSTANT FROM BELOW, WHICH IS THE ONE THING
   IN THIS PANEL THAT WAS NOT KNOWN BEFORE IT WAS RUN. The 1968 sulfuric-acid
   plateau -- benzene within a sixth of encounter -- reads as 0.778 decades, and
   applied here it caps TOLUENE at 6.0 against a measured 22. Toluene is measured
   NOT to be diffusion-controlled, so a plateau that caps it is wrong by
   construction. The line's own toluene value is {_tol:.3f} decades, so the
   honest band for this constant is {_tol:.2f} to 2.69 and the declared value sits
   at the top of it.
   Toluene at 105 against 22 is UNTOUCHED by every candidate above 2.02. That
   4.8x is rho's error, quoted over a -6.0 to -7.3 band in G2, and a plateau is
   not asked to fix it.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 3  THE CORPUS COST, ROUTE BY ROUTE -- ZERO TO FOUR DECIMALS")
print(BAR)
print("""   G2 costed its four routes and the numbers went into HANDOFF and nowhere
   else, so nothing could re-measure them. They are a script now.
   `ddt-route` is included because it must NOT move: it does not nitrate.
""")
ROUTES = [
    ("benzene-nitration", [BENZENE, NITRIC, WATER],
     {BENZENE: 1.0, NITRIC: 1.2, WATER: 5.0}, 340.0, 7200.0, NB, 1,
     "nitrobenzene"),
    ("tnt-route", [TOLUENE, NITRIC, WATER],
     {TOLUENE: 1.0, NITRIC: 3.5, WATER: 5.0}, 340.0, 7200.0, TNT, 3, "2,4,6-TNT"),
    ("picric-acid-route", [PHENOL, NITRIC, WATER],
     {PHENOL: 1.0, NITRIC: 3.5, WATER: 5.0}, 380.0, 7200.0, PICRIC, 3,
     "picric acid"),
]
print(f"   {'route':20s} {'target':13s} {'bare line':>12s} {'PLATEAU':>12s} "
      f"{'moved':>8s}")
for rid, seed, charge, T, secs, watch, gen, label in ROUTES:
    bare = run(seed, charge, T, secs, watch, NO_PLATEAU, gen)
    capped = run(seed, charge, T, secs, watch, hammett.SATURATION_DECADES, gen)
    print(f"   {rid:20s} {label:13s} {bare:12.4f} {capped:12.4f} "
          f"{abs(capped - bare):8.1e}")
_ph = NITRATION_RHO * sigma(PHENOL)
print(f"""
   NOT ONE OF THEM MOVES, AND `picric-acid-route` IS THE INTERESTING ROW.
   Phenol asks the line for {_ph:.2f} decades and the plateau hands it 2.686, a
   {10 ** (_ph - hammett.SATURATION_DECADES):.0f}x slowdown of its FIRST nitration --
   and the two-hour yield does not move at the fourth decimal, because that step
   was never rate-limiting. A measurement of what a rate change buys is not the
   same as a measurement of the rate change.

   SO THIS BUYS NO ROUTE, and that was predicted before it was run: G4 measured
   that 137 of the 142 routes outside the BOTH column are blocked on capability
   or on data, not on numbers being wrong. What it buys is the number being right
   where it was wrong by 2400x, and panel 5.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 4  WHY THE CAP IS ONE-SIDED -- MEASURED ON G2's OWN LADDER")
print(BAR)
print("""   An encounter limit is a ceiling on the FAST side. Nothing caps how slow
   a deactivated ring gets: 1,3,5-trinitrobenzene really is some thirteen
   decades below benzene, which is exactly why real TNT manufacture escalates
   its acid and its temperature through three stages. A cap written on
   |rho*sigma| rather than on rho*sigma would flatten BOTH ends.
""")


def stages(T: float, seconds: float, saturation: float,
           two_sided: bool = False) -> dict[int, float]:
    shift = hammett.barrier_shift

    def two(rho, sigma_sum, sat=saturation):
        d = max(min(rho * sigma_sum, sat), -sat)
        return -hammett._PER_DECADE * d

    if two_sided:
        hammett.barrier_shift = two
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            net = build_network(
                [TOLUENE, NITRIC, WATER],
                [aromatic_nitration(saturation=saturation)],
                thermo=thermo, generations=3, max_species=60,
            )
            v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e6, kla=0.0,
                       k_vent=0.0, k_diss=0.0, lle=False)
            v.charge({TOLUENE: 1.0, NITRIC: 3.5, WATER: 5.0})
            v.run(seconds)
        out: dict[int, float] = {}
        st = v.state()
        for s in v.species:
            if s in (NITRIC, WATER) or "c" not in s:
                continue
            n = s.count("[N+](=O)[O-]")
            out[n] = out.get(n, 0.0) + st.total(s)
        return out
    finally:
        hammett.barrier_shift = shift


LADDER = ((300.0, 10.0), (300.0, 100.0), (340.0, 3600.0), (380.0, 3600.0))
for label, sat, two_sided in (
    ("the bare line (G2 as shipped)", NO_PLATEAU, False),
    ("ONE-SIDED plateau 2.686 (this session)", hammett.SATURATION_DECADES, False),
    ("TWO-SIDED plateau 2.686 (refused)", hammett.SATURATION_DECADES, True),
):
    print(f"\n   {label}")
    print(f"   {'T/K':>5s} {'t/s':>6s} " + " ".join(
        f"{n:>8s}" for n in ("toluene", "mono", "di", "TRI")))
    for T, secs in LADDER:
        d = stages(T, secs, sat, two_sided)
        print(f"   {T:5.0f} {secs:6.0f} " + " ".join(
            f"{d.get(n, 0.0):8.4f}" for n in range(4)))
print("""
   THE ONE-SIDED PLATEAU LEAVES THE LADDER BIT FOR BIT, because toluene and
   every nitrotoluene on it sit UNDER the plateau -- the whole ladder is on the
   deactivating side. The two-sided version puts 0.0345 mol of trinitro in the
   flask in ten seconds at room temperature and finishes at 340 K, which is the
   pre-G2 failure the ring-deactivation session existed to remove.
   A cap on the magnitude would have looked more symmetrical and been wrong.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 5  ANILINE: WHAT THE PLATEAU BUYS, AND THE ONE THING IT COSTS")
print(BAR)
h = 10.0 ** (-POT_FLOOR_PH)
f_ion = h / (10.0 ** (-PKA_ANILINIUM) + h)
k_ion = hammett.rate_ratio(NITRATION_RHO, sigma(ANILINIUM))
print(f"""   G5 split the aniline into a free base and an anilinium and measured
   that the split cannot fix it: at the engine's acidity floor of pH
   {POT_FLOOR_PH:.3f} the ion is {100 * f_ion:.6f}% of the aniline and carries 1e-7% of the
   rate, because sigma+ = -1.300 prices the free base 8.45 decades up. The
   remaining leak was never in the FRACTION; it was in the PRICE.
""")
print(f"   {'plateau':>14s} {'k_free/k0':>12s} {'effective':>12s} "
      f"{'vs benzene':>12s} {'carried by ion':>15s}")
for cap, lbl in ((NO_PLATEAU, "none (G5)"), (2.686, "2.686 (G6)"),
                 (2.408, "2.408"), (0.778, "0.778")):
    k_free = hammett.rate_ratio(NITRATION_RHO, sigma(ANILINE), saturation=cap)
    eff = (1.0 - f_ion) * k_free + f_ion * k_ion
    print(f"   {lbl:>14s} {k_free:12.4e} {eff:12.4e} "
          f"{('FASTER' if eff > 1 else 'slower'):>12s} "
          f"{100 * f_ion * k_ion / eff:14.3e}%")
k_free_now = hammett.rate_ratio(NITRATION_RHO, sigma(ANILINE))
k_free_bare = hammett.rate_ratio(NITRATION_RHO, sigma(ANILINE),
                                 saturation=NO_PLATEAU)
eff_now = (1.0 - f_ion) * k_free_now + f_ion * k_ion
eff_bare = (1.0 - f_ion) * k_free_bare + f_ion * k_ion
cross_now = -math.log10(10.0 ** (-PKA_ANILINIUM) * k_free_now / k_ion)
cross_bare = -math.log10(10.0 ** (-PKA_ANILINIUM) * k_free_bare / k_ion)
print(f"""
   THE HEADLINE. Aniline goes from {eff_bare:.3g} times benzene to
   {eff_now:.3g} times benzene -- {math.log10(eff_bare / eff_now):.1f} decades, and
   across the line that matters, because the observable is that nitration of
   aniline in strong acid runs SLOWER than benzene's and gives largely meta
   product. It took both halves: G5's split supplies the deactivated species and
   G6 stops the surviving free base being priced off the end of the line.

   AND IT COSTS SOMETHING THAT WAS G5's STRONGEST CLAIM, WHICH IS SAID HERE
   RATHER THAN LEFT TO BE FOUND. The two channels' crossover moves:

       bare line   [H3O+] crossover at pH {cross_bare:6.2f}     (G5's headline)
       plateau     [H3O+] crossover at pH {cross_now:6.2f}
       reachable in this engine    pH {POT_FLOOR_PH:6.2f}

   G5 reported that {cross_bare:.2f} lands INSIDE the H0 band of the 90-98%
   sulfuric acid real aniline nitration is run in (roughly -8 to -10, quoted to
   one figure and recalled rather than sourced), and read that as the engine's own
   arithmetic finding the right answer without being told. THAT COINCIDENCE WAS
   A PROPERTY OF THE 8.45-DECADE EXTRAPOLATION. With the free base priced at a
   plateau that IS sourced, the crossover sits at {cross_now:.2f}, which the pot
   would have to reach by getting {POT_FLOOR_PH - cross_now:.2f} decades more
   acidic than its floor -- against {POT_FLOOR_PH - cross_bare:.2f} decades
   before. The wall shrank by {cross_now - cross_bare:.1f} decades, is still
   there, and the agreement went with it.
   Both cannot be right, and the one with a source under it wins. What survives
   of G5 is the direction and the species split; what does not is the number being
   evidence for anything.""")

# ---------------------------------------------------------------------------
print()
print(BAR)
print("PANEL 6  THE CLAMP IS NOW UNREACHABLE, AND THE FUNCTION STAYS")
print(BAR)
worst_sum = min(sigma(s) for _, s in SUBS)
print(f"""   `clamp_barrier` was documented as REACHABLE and not defensive, and it
   was: 4-aminophenol's sum(sigma+) of {worst_sum:+.3f} is worth
   {hammett.barrier_shift(NITRATION_RHO, worst_sum, NO_PLATEAU) / 1000:.1f} kJ/mol against a
   declared {DECLARED_EA / 1000:.0f}, so the barrier went through zero and
   `build_network` said so. Under the plateau the largest acceleration ANY ring
   can be given is {hammett.SATURATION_DECADES * hammett._PER_DECADE / 1000:.1f} kJ/mol:
""")
print(f"   {'substrate':14s} {'sum sigma+':>11s} {'bare Ea':>10s} {'plateau Ea':>11s} "
      f"{'clamped?':>9s}")
for name, smi in SUBS:
    bare = DECLARED_EA + hammett.barrier_shift(NITRATION_RHO, sigma(smi), NO_PLATEAU)
    print(f"   {name:14s} {sigma(smi):+11.3f} {bare:10.0f} {barrier(smi):11.0f} "
          f"{('WAS' if bare < 0 else '-'):>9s}")
floor_dec = DECLARED_EA / hammett._PER_DECADE
print(f"""
   The floor needs {floor_dec:.2f} decades of acceleration and the plateau allows
   {hammett.SATURATION_DECADES:.3f}, so it cannot fire on this template again.
   THE FUNCTION IS NOT DEAD CODE AND IS KEPT. The plateau is declared PER
   TEMPLATE, so a template with a barrier under
   {hammett.SATURATION_DECADES * hammett._PER_DECADE / 1000:.1f} kJ/mol reaches the floor
   immediately, and so does anything run with `hammett_saturation=math.inf` --
   which is how every "bare line" column above was measured.
   A reported notice that stops appearing is worth a line in an audit. The
   `hammett-floor` NOTICE no longer fires on any corpus substrate, and a new
   `hammett-plateau` NOTICE fires in its place -- a latent gap is REPORTED, not
   silently priced.""")

print(f"\n   {time.time() - t0:.1f} s")

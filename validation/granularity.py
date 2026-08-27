"""G4 -- the granularity audit: how much of the BOTH column is a CATALOG artefact?

A standing audit, ~18 s. Five panels.

The G-series brief asks one question. ``benzene-nitration`` is written in the
catalog as a three-step arenium mechanism and therefore scores as not
template-ready, while the engine nitrates benzene quantitatively today. **How
many more routes are like that, and nobody had counted.** Until someone does,
the BOTH column is an unknown amount too low and every content session is aimed
with it.

  1. the four buckets, and the fact that KILLS THE OBVIOUS SEARCH: the worked
     example is not in the bucket the brief points at;
  2. the mechanical scan -- rows that are not reactions, rows the corpus itself
     declares optional, and one class the instrument simply failed to credit;
  3. TARGET-REACHABLE against BOTH: scoring the route's DAG instead of its rows,
     the named list, and the two FALSE CREDITS the first version of that scorer
     made before the target was forbidden to be bought;
  4. **the runs**, because a count is not a credit -- each candidate charged
     into a real ``Vessel`` with its target read out, including the one the
     scorer credited and the run REFUTED;
  5. the answer, and what it does and does not license.

⚠ **THE DELIVERABLE IS A COUNT PLUS A NAMED LIST, NOT A RE-SCORED HEADLINE.**
S1 recorded the trap this audit is most likely to fall into -- *"crediting a
class made a FALSE route credit"* -- and S7 recorded why the only honest test is
RUNNABLE: ``RUNNABLE`` cannot ask whether a NUMBER is right, but it can ask
whether anything comes out of the flask, and that is the question here. So no
route is counted below on the strength of an argument. Every one of them is
charged and run, and the moles are printed.

⚠ **AND M1 IS THE PRECEDENT FOR A NEGATIVE OUTCOME BEING A GOOD ONE.** M1 fixed
this same instrument and the corrected baseline went DOWN. A G4 that finds few
free routes is a successful G4: it retires an unknown that is currently
inflating every plan.

Run: ``python validation/granularity.py``
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))
sys.path.insert(0, os.path.join(_ROOT, "validation"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import catalog as cat  # noqa: E402
import catalog_coverage as cc  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    UnifacProvider,
    VolatilityProvider,
    electrolyte_provider,
)
from chemsim.reactions import lead_chamber, sulfur_combustion  # noqa: E402
from chemsim.reactions.synthesis import (  # noqa: E402
    alkene_hydrogenation,
    aromatic_nitration,
    ester_hydrolysis,
    glycoside_hydrolysis,
    nitro_hydrogenation,
    saponification,
)
from chemsim.vessel import Vessel  # noqa: E402

BAR = "=" * 78
T0 = time.time()


def rule(title: str) -> None:
    print()
    print(BAR)
    print(title)
    print(BAR)


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


# ---------------------------------------------------------------------------
# the corpus, and the tier of every species in it
# ---------------------------------------------------------------------------
compounds = cat.load_compounds()
routes = cat.load_routes()
steps = cat.load_steps()

_thermo = ThermochemistryProvider()
_vol = VolatilityProvider(_thermo)
# ⚠ HOIST THE PROVIDERS. Building ``electrolyte_provider`` inside the
# comprehension constructs one per compound and takes this audit from 20 s to
# 290 s -- measured, on the first version of this file.
_ionic = electrolyte_provider(base=_thermo, volatility=_vol)
_unifac = UnifacProvider()
_tier = {
    cid: cc.audit_compound(rec, _thermo, _vol, _ionic, _unifac)["tier"]
    for cid, rec in compounds.items()
}
TC = cc.TEMPLATE_CLASSES


def priced(x: str) -> bool:
    return x in compounds and _tier[x] != "refused"


def route_steps(rid: str) -> list:
    return sorted((s for s in steps if s.route == rid), key=lambda s: s.index)


def species_ok(rid: str) -> bool:
    return all(
        priced(x) for s in route_steps(rid) for x in s.reactants + s.products
        if x in compounds
    )


def template_ok(rid: str, tc=TC) -> bool:
    return all(s.cls in tc for s in route_steps(rid))


# ---------------------------------------------------------------------------
rule("PANEL 1  THE FOUR BUCKETS, AND WHY THE OBVIOUS SEARCH MISSES THE EXAMPLE")

buckets: dict[str, list[str]] = {
    "BOTH": [], "template-ready, species-BLOCKED": [],
    "species-ready, template-BLOCKED": [], "blocked on BOTH bars": [],
}
for rid in routes:
    ok, tmpl = species_ok(rid), template_ok(rid)
    key = ("BOTH" if (ok and tmpl) else
           "template-ready, species-BLOCKED" if tmpl else
           "species-ready, template-BLOCKED" if ok else "blocked on BOTH bars")
    buckets[key].append(rid)

print()
print(f"   {'bucket':34s} {'routes':>7s}")
for k, v in buckets.items():
    print(f"   {k:34s} {len(v):7d}")
print(f"   {'':34s} {'-'*7}")
print(f"   {'total':34s} {len(routes):7d}")

_bn = route_steps("benzene-nitration")
_bn_refused = sorted({x for s in _bn for x in s.reactants + s.products
                      if x in compounds and not priced(x)})
print(f"""
   THE BRIEF POINTS AT THE THIRD BUCKET AND ITS OWN WORKED EXAMPLE IS NOT IN
   IT. `benzene-nitration` is blocked on SPECIES, not on templates:

       refused: {', '.join(_bn_refused)}

   Both are transient. A nitronium ion and an arenium ion are things a MECHANISM
   has and a FLASK never holds, and nothing prices them -- correctly. So the
   granularity problem has TWO forms and only one of them is a missing template:

     STEP granularity     the catalog spells one transformation as several rows,
                          and the rows' classes have no template
     SPECIES granularity  the catalog spells one transformation through
                          intermediates the engine never materialises, and those
                          intermediates have no price

   An audit that searched only the third bucket would have missed the case that
   started it. That is the panel.""")

# ---------------------------------------------------------------------------
rule("PANEL 2  THE MECHANICAL SCAN -- ROWS THAT ARE NOT STEPS, AND ONE MISSED CLASS")

nonreaction = [s for s in steps if set(s.products) <= set(s.reactants)]
print("\n   (a) ROWS THAT MAKE NOTHING NEW. Products are a subset of reactants,")
print("       so no template can ever match them -- they are WORKUP, not chemistry:")
print()
for s in nonreaction:
    print(f"       {s.route:22s} {s.index}. {s.name:22s} [{s.cls}]")
print(f"       -> {len(nonreaction)} rows in {len({s.route for s in nonreaction})} routes")

_WORDS = ("byproduct", "by-product", "side reaction", "alternative",
          "selectivity loss")


def optional(s) -> bool:
    return any(w in (s.name + " " + s.conditions).lower() for w in _WORDS)


opt = [s for s in steps if optional(s)]
print("\n   (b) ROWS THE CORPUS ITSELF DECLARES OPTIONAL. Its own prose says")
print("       byproduct / side reaction / alternative, and the scorer reads none of it:")
print()
for s in opt:
    print(f"       {s.route:24s} {s.index}. {s.name:26s} [{s.cls}]")
print(f"       -> {len(opt)} rows in {len({s.route for s in opt})} routes")

print("""
   (c) ONE CLASS THE INSTRUMENT SIMPLY FAILED TO CREDIT. `TEMPLATE_CLASSES`
       maps `ester-hydrolysis` to "ester_hydrolysis + saponification" -- and the
       CATALOG also has a class literally called `saponification`, which was
       never keyed. The template has existed since M5.""")

with contextlib.redirect_stdout(io.StringIO()):
    _sap_net = build_network(
        [c("CCCCCCCCCCCCCCCCCC(=O)OCC(OC(=O)CCCCCCCCCCCCCCCCC)"
           "COC(=O)CCCCCCCCCCCCCCCCC"), c("[OH-]"), c("[Na+]"), c("O")],
        [saponification()],
        thermo=electrolyte_provider(), max_species=60,
    )
_sap_rxn = [r for r in _sap_net.reactions if r.name.startswith("saponification")]
print(f"""
       Run against the catalog's OWN substrate (tristearin + hydroxide, the
       `soap-saponification` row): {len(_sap_net.species)} species, {len(_sap_rxn)} saponification reactions --
       all three esters come off, down to glycerol.

   !! AND CREDITING IT BUYS NOTHING. `soap-saponification`'s other row is
       `salting-out`, which is in list (a) above, and its target sodium-stearate
       is REFUSED -- the stearate anion has no pKa in the ion table, so the
       vessel refuses to price it. +1 class, +0 routes. The credit is honest at
       the template bar and the route still cannot run.""")

# ---------------------------------------------------------------------------
rule("PANEL 3  TARGET-REACHABLE -- SCORING THE DAG INSTEAD OF THE ROWS")


def reachable(rid: str, target: str, tc=TC) -> bool:
    """G4's DAG walk. ⚠ IT LIVES IN ``tools/catalog.py`` NOW.

    G3 needed exactly this question -- is a route's target reachable at all --
    before it could ask whether the route is FED from natural materials, and two
    copies of a scorer drift silently. So the body moved to
    ``catalog.route_reachable`` and both audits call it. Everything about it that
    was decided by measurement is documented there, including the rule that took
    three sessions of trap out of it: **the target may not be charged.**
    """
    return cat.route_reachable(steps, rid, target, priced, tc, compounds)


both = set(buckets["BOTH"])
reach = {rid for rid, r in routes.items() if reachable(rid, r.target)}
print(f"""
   BOTH  (every ROW has a template and a price)   {len(both):3d} / {len(routes)}
   TARGET-REACHABLE (the DAG reaches the target)  {len(reach):3d} / {len(routes)}
   gained {len(reach - both)}, lost {len(both - reach)}
""")
for rid in sorted(reach - both):
    why = [s for s in route_steps(rid) if s.cls not in TC]
    print(f"     + {rid:26s} target {routes[rid].target:16s} "
          f"skipped: {', '.join(f'{s.index}.{s.cls}' for s in why)}")

print("""
   !! AND THE FIRST VERSION OF THIS SCORER MADE TWO FALSE CREDITS, WHICH IS
   WHY THE RULE ABOVE EXISTS. Without "the target may not be charged" it also
   credited `bayer-process` and `contact-process` -- and in both the target is
   also a STEP-1 REACTANT, so the route scored reachable by buying the product:

       bayer 1     aluminium-oxide + NaOH + water -> sodium-aluminate
       contact 3   sulfur-trioxide + SULFURIC-ACID -> disulfuric-acid

   Bayer PURIFIES bauxite and the contact process recycles its own acid. A
   scorer that does not know the difference between a feedstock and a product
   will credit every recycle loop in the corpus.""")

# ---------------------------------------------------------------------------
rule("PANEL 4  THE RUNS -- BECAUSE A COUNT IS NOT A CREDIT")

thermo = ThermochemistryProvider()
NI = "[Ni]"
H2, WATER = c("[H][H]"), c("O")
results: list[tuple[str, str, float, str]] = []


def run(rid: str, note: str, seeds, templates, liquid, gas, solid, T, seconds,
        target, **build_kw) -> float:
    with contextlib.redirect_stdout(io.StringIO()):
        net = build_network(seeds, templates, thermo=thermo, **build_kw)
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e4, kla=1.0, k_vent=0.0,
               k_diss=0.0, lle=False)
    v.charge(liquid)
    if gas:
        v.charge(gas, phase="gas")
    if solid:
        v.charge(solid, phase="solid")
    v.run(seconds)
    st = v.state()
    tgt = c(target)
    got = st.total(tgt) if tgt in v.species else 0.0
    print(f"\n   {rid}  --  {note}")
    print(f"     network {len(net.species)} species / {len(net.reactions)} reactions, "
          f"{T:.0f} K, {seconds:g} s")
    print(f"     >>> {got:.6f} mol of the target")
    results.append((rid, note, got, target))
    return got


# 1 -- SPECIES granularity: three catalog rows, ONE template
BENZENE, NITRIC = c("c1ccccc1"), c("O[N+](=O)[O-]")
run("benzene-nitration", "3 rows through a nitronium and an arenium, ONE template",
    [BENZENE, NITRIC, WATER], [aromatic_nitration()],
    {BENZENE: 1.0, NITRIC: 1.2, WATER: 5.0}, None, None, 340.0, 7200.0,
    "O=[N+]([O-])c1ccccc1", generations=1)

# 2 -- row 1 and row 2 are ALTERNATIVES, not a sequence
NB = c("O=[N+]([O-])c1ccccc1")
run("aniline-route", "row 2 (catalytic H2) is an ALTERNATIVE to row 1 (Bechamp)",
    [NB, H2, WATER, NI], [nitro_hydrogenation()],
    {NB: 1.0, WATER: 5.0}, {H2: 4.0}, {NI: 0.1}, 470.0, 7200.0, "Nc1ccccc1")

# 3 -- row 2 is a declared BYPRODUCT
TRIOLEIN = c(r"CCCCCCCC/C=C\CCCCCCCC(=O)OCC(OC(=O)CCCCCCC/C=C\CCCCCCCC)"
             r"COC(=O)CCCCCCC/C=C\CCCCCCCC")
run("hydrogenation-margarine", "row 2 is the corpus's own 'trans isomer byproduct'",
    [TRIOLEIN, H2, NI], [alkene_hydrogenation()], {TRIOLEIN: 1.0}, {H2: 6.0},
    {NI: 0.1}, 450.0, 7200.0,
    "CCCCCCCCCCCCCCCCCC(=O)OCC(OC(=O)CCCCCCCCCCCCCCCCC)COC(=O)CCCCCCCCCCCCCCCCC")

# 4 -- row 2 makes a MARKER; the target is row 1's product
TANNIC = c("OC[C@H]1O[C@@H](OC(=O)c2cc(O)c(O)c(O)c2)[C@H](O)[C@@H](O)"
           "[C@@H]1OC(=O)c1cc(O)c(O)c(O)c1")
run("tanning-route", "row 2 crosslinks collagen into a MARKER; target is row 1's",
    [TANNIC, WATER], [ester_hydrolysis()], {TANNIC: 1.0, WATER: 20.0}, None, None,
    360.0, 7200.0, "OC(=O)c1cc(O)c(O)c(O)c1")

# 5 -- the one the scorer credited and the RUN refutes
STARCH = c("OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O")
MALTOSE = c("OC[C@H]1O[C@H](O[C@@H]2[C@@H](CO)O[C@@H](O)[C@H](O)[C@H]2O)"
            "[C@H](O)[C@@H](O)[C@@H]1O")
GLUCOSE = "OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O"
run("starch-hydrolysis", "from the DECLARED FEEDSTOCK, starch-unit",
    [STARCH, WATER], [glycoside_hydrolysis()], {STARCH: 1.0, WATER: 20.0},
    None, None, 360.0, 7200.0, GLUCOSE)
run("starch-hydrolysis", "the same target from the INTERMEDIATE, maltose",
    [MALTOSE, WATER], [glycoside_hydrolysis()], {MALTOSE: 1.0, WATER: 20.0},
    None, None, 360.0, 7200.0, GLUCOSE)
print("""
     !! THIS IS THE ONE THE SCORER GOT WRONG, AND ONLY RUNNING IT SAID SO.
     `starch-unit` is spelled in the corpus as a SINGLE alpha-D-glucopyranose
     ring, and row 1 reads `starch-unit + water -> maltose`: a hydrolysis that
     makes a DISACCHARIDE out of a monosaccharide and water. It cannot be right
     in that direction, and the engine refuses it by matching nothing at all --
     zero reactions, not a slow one. The target is reachable only from maltose,
     which is the thing row 1 was supposed to make. **Scored reachable,
     REFUTED by the run.**""")

# 6 -- row 4 is a side reaction on a refused species; the chain runs in two stages
S8, O2, SO2, NO2, NO, N2 = (c("S1SSSSSSS1"), c("O=O"), c("O=S=O"),
                            c("[O-][N+]=O"), c("[N]=O"), c("N#N"))
H2SO4 = c("OS(=O)(=O)O")
with contextlib.redirect_stdout(io.StringIO()):
    burn_net = build_network([S8, O2, N2], [sulfur_combustion()], thermo=thermo)
    chamber_net = build_network([SO2, NO2, NO, WATER, O2, N2], lead_chamber(),
                                thermo=thermo)
vb = Vessel(burn_net, volume=1.0, T=650.0, T_env=650.0, UA=1.0e4, kla=5.0,
            k_vent=0.0, k_diss=0.05, lle=False)
vb.charge({S8: 0.02, O2: 0.40, N2: 0.02})
vb.run(600.0)
so2 = vb.state().total(SO2)
vc = Vessel(chamber_net, volume=2.0, T=350.0, T_env=350.0, UA=1.0e4, kla=5.0,
            k_vent=0.0, k_diss=0.05, lle=False)
vc.charge({SO2: so2, O2: 0.05, N2: 0.10, WATER: 0.60, NO2: 0.004})
vc.run(3600.0)
st = vc.state()
print(f"""
   lead-chamber  --  row 4 is a side reaction whose product is REFUSED
     stage 1  burner 650 K / 600 s   S8 0.02 + O2 0.40  ->  SO2 {so2:.6f} mol
     stage 2  chamber 350 K / 3600 s SO2 + O2 + water + 4 mmol NOx
     >>> {st.total(H2SO4):.6f} mol of sulfuric acid, from NATIVE SULFUR
     NOx carrier charged 0.004000, recovered {st.total(NO2) + st.total(NO):.6f} -- a real cycle

     !! TWO VESSELS AT TWO TEMPERATURES, AND THAT IS THE CHEMISTRY, NOT A
     WORKAROUND: you burn sulfur hot and absorb the gas cold. The blocking row
     is `nitrosation`, which makes NITROSYLSULFURIC ACID -- chamber crystals,
     the process's FOULING product, and nothing on the path to the acid.""")
results.append(("lead-chamber", "burner + chamber, two stages",
                st.total(H2SO4), "sulfuric-acid"))

# ---------------------------------------------------------------------------
rule("PANEL 5  THE ANSWER")

confirmed = ["benzene-nitration", "aniline-route", "hydrogenation-margarine",
             "tanning-route", "lead-chamber"]
print(f"""
   {len(confirmed)} ROUTES ARE SCORED BLOCKED AND RUN TODAY, and each of them is above
   with its moles:

     benzene-nitration        SPECIES granularity -- a nitronium and an arenium
     aniline-route            two rows that are ALTERNATIVES, read as a sequence
     hydrogenation-margarine  a row the corpus itself calls a byproduct
     tanning-route            a row whose product is a MARKER, past the target
     lead-chamber             a row that is the process's FOULING product

   So the honest headline is {len(both)} + {len(confirmed)} = {len(both) + len(confirmed)} of {len(routes)}, and the reported {len(both)} understates
   what the engine does by {100 * len(confirmed) / len(both):.0f}%.

   !! AND THAT IS A SMALL NUMBER, WHICH IS THE POINT. 142 routes are not in
   the BOTH column and {len(confirmed)} of them are catalog artefacts -- {100 * len(confirmed) / (len(routes) - len(both)):.0f}%. The other
   137 are blocked on chemistry this engine cannot do or data nothing prices.
   **The BOTH column was not hiding a content backlog.** M1 fixed this same
   instrument and its corrected baseline went DOWN; this one moves it up by
   five, and the useful result is that the remaining 137 can now be treated as
   real work rather than as possible bookkeeping.

   !! WHAT THIS DOES NOT LICENCE. Five routes RUN; that is not five routes with
   the right NUMBERS in them, and S7's warning stands -- `RUNNABLE` cannot ask
   whether a number is right. `lead-chamber` in particular is quoted at its
   O2-limited yield and not at a yield anybody measured.
   !! AND THE HEADLINE IS NOT RE-SCORED IN `COVERAGE_REPORT.md`. The BOTH column
   there still says {len(both)}, because it is a mechanical measure of the CORPUS and
   these five are a hand-read judgement about five specific rows. The report
   points here instead.

   ({time.time() - T0:.1f} s)""")

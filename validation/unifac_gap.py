"""M4: what the UNIFAC gap actually IS, and what the two halves of it cost.

MILESTONES M4 said 41% of molecular organics have no group decomposition, that
this silently sets gamma = 1, and that it lies about phase separation. The first
two were true and the third is the important one. What measurement added, before
anything was built, is that "the gap" was never one problem:

    PANEL 1  the coverage number, and the ceiling it is against
    PANEL 2  the work-list: which atom environments still go unassigned
    PANEL 3  !! the matcher half -- what the two fixes bought, and where we now
             deliberately refuse a molecule `thermo` decomposes
    PANEL 4  !! the OTHER half, and it is not coverage at all: how far a split
             moves when a species is held ideal, and the threshold that bounds
    PANEL 5  ... shown firing on a flask

Run: python validation/unifac_gap.py       (about a minute)
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from catalog import load_compounds                          # noqa: E402
from rdkit import Chem                                      # noqa: E402

from chemsim.matter import Molecule                         # noqa: E402
from chemsim.network import build_network                   # noqa: E402
from chemsim.numerics.lle import (                          # noqa: E402
    IDEAL_FRACTION_REPORT,
    IDEAL_TIE_LINE_SENSITIVITY,
    stability_test,
)
from chemsim.properties import (                            # noqa: E402
    ThermochemistryProvider,
    UnifacProvider,
    build_activity_arrays,
)
from chemsim.properties import fragmentation as fr          # noqa: E402
from chemsim.properties import unifac                       # noqa: E402
from chemsim.properties import unifac_data as ud            # noqa: E402
from chemsim.vessel import Vessel                           # noqa: E402


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def organics():
    """Every neutral single-fragment carbon-containing species in the catalog."""
    out = []
    for comp in load_compounds().values():
        smi = comp.smiles
        if not smi or "." in smi:
            continue
        try:
            mol = Molecule.from_smiles(smi)
        except Exception:                                   # noqa: BLE001
            continue
        if mol.charge != 0 or mol.element_counts().get("C", 0) == 0:
            continue
        out.append((comp.name, mol))
    return out


SPECIES = organics()
BASE = unifac.UnifacProvider()
FAILING = [(n, m) for n, m in SPECIES if not BASE.get(m).modelled]

# ---------------------------------------------------------------------------
rule("PANEL 1 -- THE COVERAGE NUMBER")
# ---------------------------------------------------------------------------
n = len(SPECIES)
ok = n - len(FAILING)
print(f"""
   Neutral, single-fragment, carbon-containing species in data/catalog: {n}
     decompose into UNIFAC subgroups   {ok:5d}   ({100 * ok / n:.1f}%)
     no decomposition, held at gamma=1 {len(FAILING):5d}   ({100 * len(FAILING) / n:.1f}%)

   Was 730 (63.2%) before the matcher work in PANEL 3.

   !! And the table is NOT missing rows. Ours is {len(ud.GROUPS_BY_ID)} subgroups in
   {len(ud.MAIN_GROUPS)} main groups with {len(ud.INTERACTIONS)} interaction pairs, which is
   EXACTLY thermo's UFSG/UFIP -- the complete published UNIFAC-VLE table. Unlike
   M3, there is no data file sitting uncollected in an installed package. What
   thermo has beyond it are DIFFERENT MODELS (Dortmund 124/62, NIST 201/86) with
   their own combinatorial terms, and joining one of those to this table is the
   basis error M3 exists as the warning about. So the number above is near its
   ceiling and the rest of the gap is a decision, not a bug.""")

# ---------------------------------------------------------------------------
rule("PANEL 2 -- THE WORK-LIST: WHICH ATOM ENVIRONMENTS GO UNASSIGNED")
# ---------------------------------------------------------------------------


def env(atom) -> str:
    sym = ("ar-" if atom.GetIsAromatic() else "") + atom.GetSymbol()
    nbrs = "".join(sorted(
        ("=" if b.GetBondTypeAsDouble() == 2 else
         "#" if b.GetBondTypeAsDouble() == 3 else "-")
        + b.GetOtherAtom(atom).GetSymbol()
        for b in atom.GetBonds()
    ))
    return f"{sym}H{atom.GetTotalNumHs()}{nbrs}"


by_env: collections.Counter = collections.Counter()
example: dict = collections.defaultdict(list)
for name, mol in FAILING:
    try:
        unifac.fragment(mol)
        continue
    except Exception as exc:                                # noqa: BLE001
        msg = str(exc)
    rd = Chem.MolFromSmiles(mol.smiles)
    if "unassigned heavy atoms" not in msg:
        by_env["<group tally != formula>"] += 1
        if len(example["<group tally != formula>"]) < 3:
            example["<group tally != formula>"].append(name)
        continue
    left = collections.Counter(re.findall(r"'([^']+)'", msg))
    for atom in rd.GetAtoms():
        if left.get(atom.GetSymbol(), 0) > 0:
            left[atom.GetSymbol()] -= 1
            key = env(atom)
            by_env[key] += 1
            if len(example[key]) < 2:
                example[key].append(name)

print(f"\n   {'count':>6s}  {'environment':26s} example")
for key, count in by_env.most_common(14):
    print(f"   {count:6d}  {key:26s} {', '.join(example[key])[:40]}")
print("""
   Read the top rows as chemistry rather than as a list. `OH0=C` is a carbonyl
   oxygen the table has no group for -- anhydrides, acid chlorides, ureas,
   carbonates; UNIFAC-VLE covers ketone, aldehyde, ester, acid and amide
   carbonyls and stops there. `ar-N` is aromatic nitrogen outside a pyridine
   RING (the PYRIDINE main group's subgroups are whole rings, so a triazine has
   nowhere to go). `OH0-N` and `NH0-O` are nitrate esters. `PH0-O` is a
   phosphate. None of those is an oversight; they are the edge of a 1975 table
   regressed against the VLE data that existed.""")

# ---------------------------------------------------------------------------
rule("PANEL 3 -- !! THE MATCHER HALF: A WRONG TURN IS NOT A TABLE GAP")
# ---------------------------------------------------------------------------
print("""
   The headline treated all 425 failures as one gap. They were two, and the
   boundary was sharp: `thermo` ships the same SMARTS we transcribed AND a
   matcher that BACKTRACKS when a greedy choice strands atoms. 37 species
   decomposed for thermo and not for us with identical patterns -- our bug, not
   the table's. Two fixes went in, and they are measured here by switching each
   off in turn.
""")

# Measured by switching the fallback search off, rather than quoted.
saved = fr._search
fr._search = lambda *a, **k: (None, True)                   # noqa: SLF001
_greedy = unifac.UnifacProvider()
greedy_only = sum(1 for _n, m in SPECIES if _greedy.get(m).modelled)
fr._search = saved

print(f"   {'before either fix':44s} {730:5d}   (63.2%)")
print(f"   {'+ ketone SMARTS given the ;H0 they meant':44s} {greedy_only:5d}   "
      f"({100 * greedy_only / n:.1f}%)")
print(f"   {'+ backtracking fallback when greedy fails':44s} {ok:5d}   "
      f"({100 * ok / n:.1f}%)")
print("""
   (a) THE SMARTS. `CH3CO` was `[CX4;H3][CX3](=O)` with no H0 on the carbonyl
       carbon, which every other group in the family carries -- so the KETONE
       group matched an ALDEHYDE, won the greedy pass by being the bigger match,
       and left a hydrogen unaccounted for. The tally check then refused the
       whole molecule, which is it doing its job: a wrong decomposition became a
       REFUSAL rather than a wrong gamma. It cost the entire aliphatic aldehyde
       series, ethanal through dodecanal.

   (b) THE SEARCH. Priority says which group is PREFERRED, not which is
       POSSIBLE, so greedy can eat an atom the only workable cover needed
       elsewhere. On failure the atoms are re-covered by depth-first search with
       the running atom tally bounded by the formula.

   !! THE ORDERING IS THE SAFETY PROPERTY, not the speed one: the search runs
   only where greedy was REFUSED, so it can turn a refusal into an answer and
   can never turn one answer into another. Measured over the whole catalog,
   Joback -- which shares this matcher -- is unmoved at 1057 species with zero
   changed decompositions, and Benson does not use it at all.
""")

# where do we and thermo now differ?
import thermo.unifac as tu                                   # noqa: E402
from thermo.group_contribution.group_contribution_base import (  # noqa: E402
    smarts_fragment_priority,
)

CATALOG = list(tu.UFSG.values())
still = []
for name, mol in FAILING:
    rd = Chem.MolFromSmiles(mol.smiles)
    try:
        out = smarts_fragment_priority(catalog=CATALOG, rdkitmol=rd)
        if out[2] and len(out[2]) == rd.GetNumAtoms():
            still.append((name, mol, out[0]))
    except Exception:                                       # noqa: BLE001
        pass
print(f"   thermo still decomposes {len(still)} species that we refuse:")
for name, mol, assignment in still:
    names = {tu.UFSG[k].group: v for k, v in assignment.items()}
    print(f"     {name[:34]:36s} {mol.smiles:20s} {names}")
print("""
   !! AND WE ARE RIGHT TO REFUSE ALL THREE, which is why the ceiling this
   session was planned against (66.4%, thermo's number) is not the target. Each
   of them is thermo counting hydrogens off the MOLECULE instead of off the
   GROUP, so a group gets applied outside the structure its R and Q were fitted
   to: `CF2` onto a CHF2 carbon, the whole-molecule FURFURAL group onto a
   substituted furan whose ring carbon has lost its hydrogen, and the ether
   group `CH3O` onto a methoxy RADICAL, whose oxygen is not an ether oxygen at
   all. That last one is caught by one of this module's own documented pattern
   corrections. A refusal is the right answer three times.""")

# ---------------------------------------------------------------------------
rule("PANEL 4 -- !! THE OTHER HALF, AND IT IS NOT COVERAGE")
# ---------------------------------------------------------------------------
print("""
   M4's 'done when' has three clauses and calls the last one the important half:
   *a species with no decomposition is FLAGGED rather than silently given
   gamma = 1 whenever it would enter a two-phase calculation.* Nothing above
   touches it. The flag needs a threshold, and the threshold has to be MEASURED
   against a split that actually moves rather than chosen.

   The experiment: water/toluene 3:1 -- the standing example -- at 298.15 K and
   at the 358.31 K of the steam distillation, with a third component added at
   mole fraction f. Run the tangent-plane test twice, once with that component
   MODELLED and once with it forced ideal, and measure how far the trial
   composition moves. Slope is d(displacement)/df in the small-f limit.
""")

U = UnifacProvider()
WATER = "O"
TOLUENE = Molecule.from_smiles("Cc1ccccc1").smiles
THIRD = {
    "methanol": "CO", "ethanol": "CCO", "acetone": "CC(C)=O",
    "acetic acid": "CC(=O)O", "acetonitrile": "CC#N", "THF": "C1CCOC1",
    "diethyl ether": "CCOCC", "ethyl acetate": "CCOC(C)=O", "DMSO": "CS(C)=O",
    "dichloromethane": "ClCCl", "chloroform": "ClC(Cl)Cl", "benzene": "c1ccccc1",
    "cyclohexane": "C1CCCCC1", "hexane": "CCCCCC", "heptane": "CCCCCCC",
}


def probe(third: str, T: float, f: float, ideal: bool):
    species = [WATER, TOLUENE, Molecule.from_smiles(third).smiles]
    arr = build_activity_arrays(species, U)
    active = arr.active.copy()
    if ideal:
        active[2] = False
    rest = 1.0 - f
    amounts = np.array([0.75 * rest, 0.25 * rest, f])
    return stability_test(amounts, arr.nu, arr.R_k, arr.Q_k, arr.a_mn, active, T)


slopes = []
for label, third in THIRD.items():
    worst = 0.0
    for T in (298.15, 358.31):
        for f in (0.0005, 0.001, 0.002, 0.004):
            a, b = probe(third, T, f, False), probe(third, T, f, True)
            if not (a.unstable and b.unstable):
                continue
            d = 0.5 * float(np.abs(a.composition - b.composition).sum())
            worst = max(worst, d / f)
    slopes.append((worst, label))
slopes.sort()
print(f"   {'third component held ideal':30s} {'slope':>8s}   belongs in the")
for slope, label in slopes:
    where = "MINOR (toluene) layer" if slope > 0.5 else "major (aqueous) layer"
    print(f"   {label:30s} {slope:8.2f}   {where}")

worst_slope, worst_label = slopes[-1]
print(f"""
   !! THE SLOPES DO NOT SCATTER, THEY SPLIT IN TWO, and the boundary is which
   layer the species belongs in. Held ideal, a species is not merely given the
   wrong gamma -- it is dropped out of the group composition every OTHER
   species' gamma is computed against. For a cosolvent that mostly stays in the
   bulk aqueous layer that is a small perturbation. For a hydrocarbon that ought
   to DEFINE the organic layer it is the whole answer, and the tie line moves by
   two to three and a half times the mole fraction held ideal.

   !! AND THERE IS NO DEAD ZONE. The displacement is LINEAR in f down to the
   smallest f measured, so there is no fraction below which the model becomes
   correct -- only one below which the error is too small to print. That is what
   makes the threshold a REPORTING decision and not a physical one, and it is
   the honest way to state it:

       worst measured sensitivity   {worst_slope:.2f}  ({worst_label})
       lle_report prints layer mole fractions to 3 decimals, so the error
       becomes visible at f = 0.01 / {worst_slope:.2f} = {0.01 / worst_slope:.4f}
       IDEAL_FRACTION_REPORT        {IDEAL_FRACTION_REPORT}
       IDEAL_TIE_LINE_SENSITIVITY   {IDEAL_TIE_LINE_SENSITIVITY}

   For scale at the other end: sweeping the same systems to f = 0.6, the
   stable/unstable VERDICT never flipped below an ideal mole fraction of 0.44.
   So between 0.003 and 0.44 the flag is saying "the numbers are soft", and
   above 0.44 it would be saying "the answer may be wrong".

   !! IONS ARE NOT COUNTED IN IT. An ion at gamma = 1 is a stated POLICY (no
   Debye-Huckel here) and it has the Born term for the part that decides
   partitioning. A neutral organic at gamma = 1 is the silent one.""")

# ---------------------------------------------------------------------------
rule("PANEL 5 -- THE FLAG, FIRING")
# ---------------------------------------------------------------------------
TH = ThermochemistryProvider()
H2SO4 = Molecule.from_smiles("OS(=O)(=O)O").smiles


def flask(species, amounts, T=298.15):
    net = build_network(species, [], thermo=TH, max_species=20)
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=50.0, kla=0.0, k_diss=0.0,
               k_vent=0.0)
    v.charge(amounts)
    v.run(600.0)
    return v


print("""
   Sulfuric acid has no UNIFAC decomposition -- there is no group for a
   sulfate's S(=O)(=O) in the 1975 table -- so it is one of the 388.
""")
for title, species, amounts in (
    ("ethanol + water, everything modelled",
     ["CCO", WATER], {"CCO": 3.0, WATER: 3.0}),
    ("sulfuric acid + water, one phase",
     [WATER, H2SO4], {WATER: 30.0, H2SO4: 5.0}),
    ("sulfuric acid + water + toluene, two layers",
     [WATER, TOLUENE, H2SO4], {WATER: 27.7, TOLUENE: 4.7, H2SO4: 2.0}),
):
    v = flask(species, amounts)
    report = v.lle_report() or "(nothing to report)"
    print(f"   {title}")
    for line in (report[i:i + 72] for i in range(0, len(report), 72)):
        print(f"       {line}")
    print()
print("""   !! THE MIDDLE ONE IS THE WHOLE POINT. It used to return the empty
   string -- "one stable phase", stated with no qualification, on the strength
   of a gamma that was never computed for 14% of the liquid. An ideal liquid
   never splits, so that verdict was the one the missing model was always going
   to give, and silence made it look like a finding.

   !! AND THE THIRD ONE SHOWS THE SIGNATURE. Sulfuric acid comes out at 0.058
   mole fraction in BOTH layers, because equality of activity with gamma = 1 on
   both sides of an interface is equality of MOLE FRACTION. That is the same
   failure the Born term was built to fix for ions, still running for neutrals,
   and now it says so.""")
print()

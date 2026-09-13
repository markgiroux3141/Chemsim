"""T14 -- the fatty-acid pKa wall, counted before a single row is written.

T8 priced the oleate and the cascade in ``gypsum + oleic-acid`` promptly reached
a stearate and an elaidate that ``_PAIRS`` does not carry. Every unbranched
aliphatic carboxylic acid sits on the same plateau -- formic 3.75, acetic 4.76,
propanoic 4.87, octanoic 4.89, nonanoic 4.96, oleic 5.02 -- so the fix is either
a dozen more hand-typed rows or one rule with a stated domain, and nobody knows
which because nobody has counted. This counts.

Three panels, and the third is the one that decides:

  1. THE CORPUS. All 1,583 catalog compounds, every carboxyl group found and
     deprotonated the way ``carboxylic_acid_dissociation`` would. Each conjugate
     pair lands in one of three buckets: already in ``_PAIRS``, inside the
     plateau domain, or needing its own measurement -- the last grouped by the
     structural reason, since the reason is what a second rule would have to
     handle.

  2. THE POOL. The natural shelf's only organic carboxyl is oleic acid, so the
     pool half is its 36 pairs expanded to a fixpoint. A lower bound twice over
     and it says so: pairs that hit the 400-species cap were cut short, and a
     carboxyl reachable only from two non-acid rows (an alcohol oxidised twice)
     is invisible to a sweep anchored on the acid.

  3. WHAT A ROW WOULD BUY. ``ion_thermochemistry`` skips any pair whose NEUTRAL
     half it cannot price -- there is nothing to anchor the ion to. So a pKa is
     necessary and not sufficient, and the count that matters is not how many
     acids are missing a pKa but how many would actually price if given one.

THE DOMAIN, AND WHY IT IS LOCAL
-------------------------------
Acidity is inductive and inductive effects die off by roughly a factor of three
per bond: chloroacetic acid is 2.86 against acetic's 4.76, 3-chloropropanoic is
4.0, 4-chlorobutanoic 4.5, and by the fifth carbon the substituent is silent.
So the plateau is not a property of the whole molecule, it is a property of the
three carbons nearest the carboxyl. This audit reports two nested domains rather
than choosing between them, because the choice is exactly the judgement the
follow-up item has to make:

  ``strict``   the whole molecule is a plain acyclic unbranched C/H chain with
               one carboxyl and no other oxygen. The textbook n-alkanoic series.
  ``local``    alpha, beta and gamma are unbranched saturated CH2 carbons with
               no heteroatom, ring, charge or unsaturation among them, whatever
               the far end of the molecule does. 12-hydroxystearic acid is here
               and not in ``strict``: its hydroxyl is nine bonds away.

Run: ``python validation/fatty_acid_pka.py``   (the pool is 36 flasks)
     ``python validation/fatty_acid_pka.py --corpus-only``
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
import time

from rdkit import Chem, RDLogger

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

from catalog import load_compounds, load_steps  # noqa: E402

from chemsim.engine import inventory as inv  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    VolatilityProvider,
    electrolyte,
    electrolyte_provider,
)
from chemsim.properties.thermochemistry import ThermochemistryProvider  # noqa: E402
from chemsim.ui.examples import full_library  # noqa: E402

RDLogger.DisableLog("rdApp.*")

# The template's own slot, minus the requirement that the proton still be on:
# this has to find the anion as well, because the corpus spells 34 compounds as
# a carboxylate salt and the pool is full of them.
CARBOXYL = Chem.MolFromSmarts("[CX3](=[OX1])[OX2H1,OX1H0-]")

# The bench's bound, so the pool and ``reachable.psv`` stop in the same place.
MAX_SPECIES = 400

# How far inductive withdrawal is still worth a decimal place. Alpha, beta and
# gamma; the fourth carbon moves a pKa by less than the spread of the plateau
# itself and cannot be resolved by a rule that quotes one number.
LOCAL_DEPTH = 3

# A basic nitrogen anywhere in the molecule takes it out of the domain however
# far away it sits, and this exclusion was added because the first run of this
# audit put GABA in the plateau bucket. GABA's carboxyl is measured at 4.03 and
# 6-aminohexanoic acid's at 4.43, both a long way below the 4.87 the plateau
# claims -- because at any pH where the carboxyl is titrated the amine is
# already protonated, so what sits four bonds away is not a neutral dipole
# dying off by a factor of three per bond but a FULL POSITIVE CHARGE. The
# molecule being titrated is a zwitterion and a different acid.
#
# The pattern is the amine and not the amide: an amide nitrogen is not basic,
# which is why every nylon unit below still has to be read one N at a time. A
# nitrile N is X1 and a nitro N is either charged or doubly bonded, so all three
# fall out without a clause of their own. An aromatic ring nitrogen is ``n`` and
# is NOT matched -- a pyridine carboxylic acid is left in whatever bucket its
# ring puts it in, which is a limit of this exclusion and not a claim about it.
BASIC_N = Chem.MolFromSmarts("[NX3;!$(N[#6]=[O,N,S]);!$(N=*);!$([N+])]")


def canon(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


def carboxyl_sites(mol) -> list[tuple[int, int]]:
    """``(carboxyl carbon, acidic oxygen)`` for every carboxyl in the molecule."""
    return [(m[0], m[2]) for m in mol.GetSubstructMatches(CARBOXYL)]


def as_pair(mol, c_idx: int, o_idx: int) -> tuple[str, str] | None:
    """The conjugate acid and base this one carboxyl would give the table.

    Written by editing the acidic oxygen in both directions rather than by
    firing the template, so a compound the corpus already spells as a salt gives
    the same pair as the free acid does. Returns ``None`` if either half will
    not sanitise.
    """
    out = []
    for charge, hs in ((0, 1), (-1, 0)):
        rw = Chem.RWMol(mol)
        atom = rw.GetAtomWithIdx(o_idx)
        atom.SetFormalCharge(charge)
        atom.SetNoImplicit(True)
        atom.SetNumExplicitHs(hs)
        try:
            Chem.SanitizeMol(rw)
            out.append(canon(Chem.MolToSmiles(rw)))
        except Exception:  # noqa: BLE001
            return None
    return (out[0], out[1])


def _heavy(atom) -> int:
    return sum(1 for n in atom.GetNeighbors() if n.GetAtomicNum() > 1)


def domain(mol, c_idx: int, o_idx: int, n_sites: int) -> tuple[str, str]:
    """Which domain this carboxyl sits in, and the reason if it sits outside.

    Returns ``("strict"|"local"|"outside", reason)``. The reason is empty inside
    the domain and names one structural fact outside it -- the first that
    applies, in order of how far it moves a pKa -- because the grouped reasons
    are the work order for whatever a second rule would have to be.
    """
    if n_sites > 1:
        return "outside", f"polyprotic ({n_sites} carboxyls)"
    if mol.HasSubstructMatch(BASIC_N):
        return "outside", "zwitterion (basic nitrogen in the molecule)"

    carboxyl = {c_idx, o_idx}
    for nb in mol.GetAtomWithIdx(c_idx).GetNeighbors():
        if nb.GetAtomicNum() == 8 and nb.GetIdx() != o_idx:
            carboxyl.add(nb.GetIdx())

    alpha = [n for n in mol.GetAtomWithIdx(c_idx).GetNeighbors()
             if n.GetIdx() not in carboxyl]
    if not alpha:
        return "outside", "formyl (no carbon on the carboxyl)"
    if len(alpha) > 1:
        return "outside", "two carbons on the carboxyl carbon"
    if alpha[0].GetAtomicNum() != 6:
        return "outside", "heteroatom acyl (not a carboxylic acid at all)"
    if alpha[0].GetIsAromatic():
        return "outside", "aromatic ring on the carboxyl"

    # Breadth-first over bonds, carboxyl oxygens excluded, to LOCAL_DEPTH.
    #
    # Only carbons are ever queued, and a heteroatom is found by LOOKING OUT
    # from the carbon it hangs off rather than by being walked onto. Both halves
    # of that matter, and the second is why: lactic acid's alpha carbon bears a
    # methyl and a hydroxyl, so walking onto it reports an "alpha branch" -- true
    # and beside the point, since what moves lactic acid to 3.86 is the hydroxyl
    # and not the methyl. Naming the substituent by the carbon it sits on is
    # also what a chemist means by alpha-hydroxy: that oxygen is TWO bonds from
    # the carboxyl carbon, so its own depth would call it beta.
    seen, frontier = set(carboxyl), [(alpha[0], 1)]
    labels = {1: "alpha", 2: "beta", 3: "gamma"}
    while frontier:
        atom, d = frontier.pop(0)
        if atom.GetIdx() in seen:
            continue
        seen.add(atom.GetIdx())
        where = labels[d]
        if any(n.GetAtomicNum() not in (1, 6) and n.GetIdx() not in carboxyl
               for n in atom.GetNeighbors()):
            return "outside", f"heteroatom on the {where} carbon"
        if atom.GetFormalCharge():
            return "outside", f"formal charge on the {where} carbon"
        if atom.IsInRing():
            return "outside", f"{where} ring atom"
        if atom.GetHybridization() != Chem.HybridizationType.SP3:
            return "outside", f"{where} unsaturation"
        if _heavy(atom) > 2:
            return "outside", f"{where} branch"
        if d < LOCAL_DEPTH:
            frontier += [(n, d + 1) for n in atom.GetNeighbors()
                         if n.GetIdx() not in seen and n.GetAtomicNum() == 6]

    # Inside the local domain. Strict is the whole molecule saying the same.
    for atom in mol.GetAtoms():
        if atom.GetIdx() in carboxyl:
            continue
        if atom.GetAtomicNum() not in (1, 6):
            return "local", ""
        if atom.IsInRing() or _heavy(atom) > 2:
            return "local", ""
    return "strict", ""


def table_series() -> list[tuple[int, float, str, str]]:
    """The rows of ``_PAIRS`` that are themselves inside the plateau domain.

    The plateau's width is the one number this audit must not assert: if the
    table's own unbranched acids spread over two pKa units there is no single
    value to give anyone. So the series is derived by running the SAME domain
    test over ``_PAIRS`` that the corpus sweep runs, rather than by listing the
    four rows a docstring remembers.
    """
    out = []
    for pair in electrolyte.known_pairs():
        mol = Chem.MolFromSmiles(pair.acid)
        if mol is None:
            continue
        sites = carboxyl_sites(mol)
        if len(sites) != 1:
            continue
        where, _ = domain(mol, sites[0][0], sites[0][1], len(sites))
        if where == "outside":
            continue
        carbons = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 6)
        out.append((carbons, pair.pKa, pair.name, where))
    return sorted(out)


ESTER = Chem.MolFromSmarts("[CX3](=[OX1])[OX2][#6]")


def _oligomer(smiles: str) -> bool:
    """Does this acid carry an ester, i.e. is it a condensate and not an acid?"""
    mol = Chem.MolFromSmiles(smiles)
    return mol is not None and mol.HasSubstructMatch(ESTER)


def routes_touched(ids: set[str]) -> dict[str, set[str]]:
    """Catalog routes naming any of these compounds in a step.

    A pKa is not a route on its own -- the route still needs its templates and
    the rest of its species -- so this is an upper bound on what the bucket can
    unblock, and it is here because a count of ions says nothing about coverage
    until it is asked which routes are standing behind it.
    """
    out: dict[str, set[str]] = {}
    for step in load_steps():
        hit = ids & (set(step.reactants) | set(step.products))
        if hit:
            out.setdefault(step.route, set()).update(hit)
    return out


def fragments(smiles: str) -> list[str]:
    """The species the engine would actually hold, one per dot-separated part.

    Measured, not assumed: ``thermochemistry`` refuses ``CC(=O)[O-].[K+]`` as
    one species and prices ``CC(=O)[O-]`` and ``[K+]`` separately, so a table
    row for potassium acetate would be a row for a species that cannot exist
    here. Keeping the counter-ion in the key is what made the first run of this
    audit report sodium acetate as an unpriced pair when acetate has been in
    ``_PAIRS`` since the beginning.

    This is the fragment-wise answer S7 refused to give a NEUTRAL mixture,
    and the difference is that a carboxyl carries its own charge: the acid half
    and the base half of a pair differ by one proton on one fragment, so the
    OTHER fragments are spectators to the equilibrium whatever they are.
    """
    return smiles.split(".")


def sweep(mols: dict[str, str], priced: set[str]) -> list[dict]:
    """Classify every carboxyl in a set of ``label -> SMILES``."""
    rows = []
    pieces = {}
    for label, smiles in mols.items():
        for part in fragments(smiles):
            pieces.setdefault(part, label)
    for smiles, label in sorted(pieces.items(), key=lambda kv: (kv[1], kv[0])):
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            continue
        sites = carboxyl_sites(mol)
        for c_idx, o_idx in sites:
            pair = as_pair(mol, c_idx, o_idx)
            if pair is None:
                rows.append({"label": label, "acid": smiles, "base": "",
                             "domain": "outside", "reason": "will not sanitise",
                             "covered": False})
                continue
            acid, base = pair
            where, why = domain(mol, c_idx, o_idx, len(sites))
            rows.append({"label": label, "acid": acid, "base": base,
                         "domain": where, "reason": why,
                         "covered": base in priced})
    return rows


def by_pair(rows: list[dict]) -> dict[str, dict]:
    """One row per distinct conjugate pair -- the unit a table row would be."""
    out: dict[str, dict] = {}
    for r in rows:
        key = r["base"] or r["acid"]
        keep = out.setdefault(key, dict(r, labels=[]))
        keep["labels"].append(r["label"])
    return out


def panel(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def report(pairs: dict[str, dict], thermo, *, anchors: bool) -> None:
    covered = {k: v for k, v in pairs.items() if v["covered"]}
    missing = {k: v for k, v in pairs.items() if not v["covered"]}
    strict = {k: v for k, v in missing.items() if v["domain"] == "strict"}
    local = {k: v for k, v in missing.items() if v["domain"] == "local"}
    outside = {k: v for k, v in missing.items() if v["domain"] == "outside"}

    print(f"  distinct conjugate pairs        {len(pairs):5d}")
    print(f"  already priced by _PAIRS        {len(covered):5d}")
    print(f"  missing                         {len(missing):5d}")
    print(f"    inside the strict domain      {len(strict):5d}   "
          "one plateau value, whole molecule")
    print(f"    inside the local domain       {len(local):5d}   "
          "one plateau value, three carbons")
    print(f"    needs its own measurement     {len(outside):5d}")

    reasons: dict[str, int] = {}
    for v in outside.values():
        reasons[v["reason"]] = reasons.get(v["reason"], 0) + 1
    for why, n in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"      {n:4d}  {why}")

    # NOTE: without this line the plateau count lies, and it lied for one run. The
    # pool's 249 are not 249 fatty acids: they are one self-condensing ester
    # series, oleic acid hydrated and then esterified onto itself over and over,
    # every member of which happens to END in the same plain -CH2CH2CH2COOH. The
    # split is printed rather than described because it is the whole argument
    # for a rule -- an oligomer series has no last member, so no table can hold
    # it, and the flask only stopped where it did because of the species cap.
    esters = sum(1 for v in dict(strict, **local).values() if _oligomer(v["acid"]))
    if esters:
        print(f"    of the plateau pairs, {esters} carry an ester and are "
              "oligomers of")
        print("    the same acid rather than distinct acids")

    if not anchors:
        return
    # Panel 3. A pKa without a priceable neutral half buys nothing: see
    # ``ion_thermochemistry``, which skips such a pair silently and correctly.
    plateau = dict(strict, **local)
    ok, no_anchor = [], []
    for key, v in sorted(plateau.items()):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                thermo.get(v["acid"])
        except Exception:  # noqa: BLE001
            no_anchor.append((key, v))
            continue
        ok.append((key, v))
    print()
    print(f"  of the {len(plateau)} plateau pairs, {len(ok)} have a priceable "
          "neutral anchor")
    print(f"  and {len(no_anchor)} do not, so a pKa row for them would be "
          "skipped by")
    print("  ion_thermochemistry and buy nothing at all")
    named = [(k, v) for k, v in ok if not _oligomer(v["acid"])]
    for key, v in named:
        print(f"      {v['domain']:6s}  {v['labels'][0]:34s}  {key}")
    if len(named) < len(ok):
        print(f"      ... and {len(ok) - len(named)} oligomers of the same acid, "
              "not listed")
    if no_anchor:
        print("  no neutral anchor, so not writable today:")
        for key, v in no_anchor:
            print(f"      {v['domain']:6s}  {v['labels'][0]:34s}  {key}")
    routes = routes_touched({v["labels"][0] for _, v in ok})
    print()
    print(f"  {len(routes)} of the catalog's 173 routes name one of those "
          f"{len(ok)} compounds in a step:")
    for route, species in sorted(routes.items()):
        print(f"      {route:34s}  {', '.join(sorted(species))}")


def pool(thermo, volatility) -> dict[str, str]:
    """Every carboxyl-bearing species a natural oleic-acid flask reaches."""
    library = full_library()
    natural = {i.id: i for i in inv.shelf(("natural",)) if i.chargeable}
    oleic = natural.pop("oleic-acid")
    out: dict[str, str] = {}
    capped = 0
    started = time.perf_counter()
    for n, (pid, partner) in enumerate(sorted(natural.items()), 1):
        print(f"  [{n}/{len(natural)}] oleic-acid + {pid}",
              file=sys.stderr, flush=True)
        species = sorted(set(oleic.species) | set(partner.species))
        with contextlib.redirect_stdout(io.StringIO()):
            net = build_network(species, library, thermo=thermo,
                                volatility=volatility,
                                max_species=MAX_SPECIES, generations=None)
        capped += len(net.species) >= MAX_SPECIES
        for s in net.species:
            mol = Chem.MolFromSmiles(s)
            if mol is not None and mol.HasSubstructMatch(CARBOXYL):
                out.setdefault(s, s)
    print(f"  {len(natural)} flasks in {time.perf_counter() - started:.0f} s; "
          f"{capped} of them hit the {MAX_SPECIES}-species cap and were cut "
          "short, so this half is a lower bound")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-only", action="store_true",
                    help="skip the 36-flask pool half")
    args = ap.parse_args()

    thermo = electrolyte_provider()
    volatility = VolatilityProvider(thermo)
    neutral = ThermochemistryProvider()
    priced = set(electrolyte.ion_thermochemistry(neutral, volatility=volatility))

    print(__doc__.split("Run:")[0].rstrip())

    panel("0. THE PLATEAU, MEASURED OFF _PAIRS RATHER THAN ASSERTED")
    series = table_series()
    for carbons, pKa, name, where in series:
        print(f"      C{carbons:<3d} {pKa:5.2f}  {where:6s}  {name}")
    flat = [pKa for carbons, pKa, _, _ in series if carbons >= 3]
    print(f"  {len(series)} of the {len(electrolyte.known_pairs())} curated "
          "pairs are inside the domain this audit uses.")
    if flat:
        print(f"  From C3 up they span {min(flat):.2f} to {max(flat):.2f}, a "
              f"width of {max(flat) - min(flat):.2f} pKa units, against the "
              f"{series[0][1]:.2f} of the")
        print(f"  C{series[0][0]} the same series starts at. That width is what "
              "a single value would")
        print("  cost, and it is the number the follow-up item has to accept or "
              "refuse.")
        print("  Formic acid is NOT in this list and the domain test is why: it "
              "has no")
        print("  carbon on its carboxyl, which is also why 3.75 is a full unit "
              "off the rest.")

    panel("1. THE CORPUS -- every catalog compound carrying a carboxyl")
    compounds = load_compounds()
    rows = sweep({c.id: c.smiles for c in compounds.values()}, priced)
    corpus_pairs = by_pair(rows)
    print(f"  compounds carrying a carboxyl   "
          f"{len({r['label'] for r in rows}):5d}")
    report(corpus_pairs, neutral, anchors=False)

    pool_pairs: dict[str, dict] = {}
    if not args.corpus_only:
        panel("2. THE POOL -- oleic acid against each other natural shelf row")
        reached = pool(thermo, volatility)
        pool_pairs = by_pair(sweep(reached, priced))
        report(pool_pairs, neutral, anchors=False)

    panel("3. WHAT A ROW WOULD BUY -- the corpus and the pool together")
    both = dict(corpus_pairs)
    for k, v in pool_pairs.items():
        both.setdefault(k, v)
    if pool_pairs:
        shared = set(corpus_pairs) & set(pool_pairs)
        print(f"  the corpus has {len(corpus_pairs)} pairs and the pool "
              f"{len(pool_pairs)}, and they share {len(shared)}.")
        print("  The corpus is the table coverage is SCORED against; the pool "
              "is what a")
        print("  flask actually makes. They are very nearly disjoint sets.")
        print()
    report(both, neutral, anchors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

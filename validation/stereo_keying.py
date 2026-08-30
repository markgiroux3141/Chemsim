"""C7's standing audit: a SPELLING selects a data tier, and what that costs.

C4 found this and put it at **31 of 146** corpus rows; C6 re-measured it as
**145 of 205** and could not reconcile the two. They are not the same question,
and this file settles which one is worth asking.

⚠⚠⚠ **BOTH NUMBERS ARE RIGHT AND NEITHER IS THE COST.** C4 asked which SOURCE a
species resolves to and filtered candidates on ``"@"`` in the raw SMILES column,
so it saw 146 tetrahedral compounds and 31 movers -- panel 1 reproduces both
exactly. C6 asked whether the two spellings reach the same TABLES, over a wider
population that includes E/Z, and got ~150. Panel 3 shows they differ by **103
compounds where the record exists and contributes nothing**: it holds a melting
point and no boiling point, the species is one Joback can fragment, and the Tm
overlay is gated on ``half.Tb is None``. Membership is not the question.
**Asking the right question moved the headline from 145 to 49 -- and 49 is the
number that costs something.**

⚠⚠⚠ **AND THE ADVERTISED MECHANISM -- "the two halves of a record are keyed
OPPOSITE ways" -- IS TWO ROWS OUT OF FIFTY.** The real shape is one table
against all the others, and it is structural rather than accidental: panel 2
shows that **the ONLY table with stereochemistry in its keys is the GENERATED
one**, ``MEASURED_PHYSICAL``, which inherited the corpus's spelling when S13
built it from the corpus. Every hand-typed table is flat, because a human types
the simple form. 0 of 82 formation entries, 0 of 58 liquid, 0 of 50 curated
records, 0 of 29 pKa rows.

⚠⚠⚠ **IT IS LIVE, WHICH IS WHAT MADE IT A SESSION RATHER THAN A FOOTNOTE.** A
missed record costs nothing unless something looks a species up flat, and the
corpus never does -- it spells them chirally and hits. **A TEMPLATE does.** Panel
4: no template in this library spells stereochemistry on its product side (0 of
50), so a rewrite that makes or touches a centre emits the flat species, and the
flat species is not the corpus's. Three catalog steps run in panel 4 and all
three move; the fourth is the control that does not.

⚠⚠ **THE FIX IS A FALLBACK WITH TWO LIMITS AND THE SECOND ONE FIRES.** Panels 5
and 6. A flat spelling may take a chiral record only where **exactly one**
record answers that skeleton -- and ``MEASURED_PHYSICAL`` holds seven skeletons
that carry more than one. Without the guard, a flat butenedioic acid takes
maleic or fumaric acid's boiling point depending on dict order, and **those are
230 K apart**. A fallback that guesses is worse than the estimator it replaces,
because it is wrong with a measurement's authority.

Panel 7 is what is still keyed flat and NOT wrapped, with its size: TWO rows,
both lactic acid, in ``electrolyte._PAIRS`` -- so a corpus-spelled lactic acid in
water does not dissociate. Left out on purpose, because that table decides which
IONS EXIST and widening it is a network-construction change, not a number.

⚠⚠⚠ **PANEL 8 IS NOT ABOUT STEREOCHEMISTRY AT ALL, AND IT IS THE LARGEST
THING THIS AUDIT FOUND.** It is where panel 3's gap of 102 comes from. The
physical half overlays a measured melting point only ``if half.Tb is None`` --
so a species Joback can fragment keeps JOBACK's melting point and the measured
one in the table is discarded. **214 species**, worst by **877 K** -- Joback
puts methotrexate's melting point at 1344.7 K against a measured 468.1. The code
comment beside that gate rests on a claim that is false: *"Nothing in the
measured table is a species Joback already prices completely (the builder checks
and reports)"* -- the builder classifies and does NOT exclude, and **855 of the
1239 entries are marked ``Joback: complete`` in the generated file itself.**
⚠ NOT fixed here, deliberately: it moves the melting point of 214 species,
which drives crystallisation and the solubility law, and mixing it into a
session about spellings would make neither change attributable.

Run: ``python validation/stereo_keying.py`` (~60 s).

⚠ EVERY PRINTED LINE HERE IS ASCII. The console is cp1252 and a warning glyph in
a ``print`` kills the script mid-panel. Glyphs belong in docstrings and comments.
"""

from __future__ import annotations

import csv
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from rdkit import Chem  # noqa: E402

from chemsim.matter import Molecule, stereo_free_smiles  # noqa: E402
from chemsim.properties import ThermochemistryProvider, electrolyte  # noqa: E402
from chemsim.properties.formation_data import (  # noqa: E402
    IDEAL_GAS_FORMATION,
    LIQUID_FORMATION,
    PHYSICAL_PROPERTIES,
)
from chemsim.properties.physical_data import MEASURED_PHYSICAL  # noqa: E402
from chemsim.properties.thermochemistry import (  # noqa: E402
    _CURATED_FUSION,
    _CURATED_RAW,
    DERIVED_GAS_FORMATION,
)
from chemsim.reactions import library, synthesis  # noqa: E402

ON = ThermochemistryProvider()
OFF = ThermochemistryProvider(stereo_fallback=False)


def c(smi: str) -> str:
    return Molecule.from_smiles(smi).smiles


def flat(smi: str) -> str:
    return stereo_free_smiles(smi)


def isotope_flat(smi: str) -> str:
    """The OTHER way to strip a spelling, and the one that is wrong here."""
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(Chem.MolFromSmiles(
        Chem.MolToSmiles(m, isomericSmiles=False)))


def rule(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


def load_corpus():
    """Every compound id in data/catalog, with its raw SMILES column."""
    path = os.path.join(_ROOT, "data", "catalog", "compounds")
    out = {}
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".psv"):
            continue
        with open(os.path.join(path, fn), encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="|"):
                if not row or row[0].strip().startswith("#") or len(row) < 3:
                    continue
                out[row[0].strip()] = row[2].strip()
    return out


CORPUS = load_corpus()

# (id, canonical, flat, raw) for every compound whose canonical spelling
# carries stereochemistry. Built once; panels 1, 3, 5 and 6 all walk it.
STEREO = []
for _cid, _raw in sorted(CORPUS.items()):
    try:
        _canon = c(_raw)
    except Exception:                                       # noqa: BLE001
        continue
    _f = flat(_canon)
    if _f != _canon:
        STEREO.append((_cid, _canon, _f, _raw))


def resolved(provider, smi):
    try:
        return provider.get(smi)
    except Exception:                                       # noqa: BLE001
        return None


def source_of(d):
    return None if d is None else d.source


def numbers_of(d):
    if d is None:
        return None
    return (d.Hf, d.Gf, d.Tb, d.Tc, d.Pc, d.Tm, d.Cp_coeffs)


def _flatten(t):
    out = []
    for v in t:
        if isinstance(v, tuple):
            out.extend(v)
        else:
            out.append(v)
    return out


def same_numbers(a, b, rtol=1e-12):
    """Whether two records agree to within floating-point reproducibility.

    ⚠⚠ THIS TOLERANCE IS NOT A CONVENIENCE, AND MEASURING IT WRONG COST THIS
    AUDIT A FALSE FINDING. Benson sums its group contributions in the order the
    atoms come out of the SMILES, and a stereochemistry-free spelling numbers
    the atoms differently -- so the SAME molecule spelled two ways gives Cp
    coefficients that differ in the last bits. Compared with ``==`` that reads
    as twelve compounds still disagreeing after the fix; the largest of those
    disagreements is 2e-16 relative. **A group-contribution sum is not
    bit-reproducible across spellings**, which is worth knowing on its own.
    """
    if (a is None) != (b is None):
        return False
    if a is None:
        return True
    for x, y in zip(_flatten(numbers_of(a)), _flatten(numbers_of(b))):
        if (x is None) != (y is None):
            return False
        if x is None:
            continue
        if abs(x - y) > rtol * max(1.0, abs(x), abs(y)):
            return False
    return True


# ---------------------------------------------------------------------------


def panel1():
    rule("PANEL 1 -- THE POPULATION, AND WHY TWO SESSIONS COUNTED IT DIFFERENTLY")
    parsed = 0
    for _cid, raw in CORPUS.items():
        try:
            c(raw)
            parsed += 1
        except Exception:                                   # noqa: BLE001
            pass
    tet = [r for r in STEREO if "@" in r[1]]
    ez = [r for r in STEREO if "@" not in r[1]]
    raw_at = [r for r in STEREO if "@" in r[3]]
    print(f"  corpus compound ids                              {len(CORPUS):5d}")
    print(f"  ... parsed                                       {parsed:5d}")
    print(f"  ... canonical spelling carries stereochemistry   {len(STEREO):5d}")
    print(f"        of those, TETRAHEDRAL ('@')                {len(tet):5d}"
          "   <- C4 counted 146")
    print(f"        of those, E/Z only                         {len(ez):5d}"
          "   <- C4's filter never saw these")
    print(f"  ... '@' in the RAW corpus column (C4's filter)   {len(raw_at):5d}")
    print()
    print("  C4's population reproduces EXACTLY. The extra ground is E/Z: a")
    print("  filter on '@' is a filter on TETRAHEDRAL stereochemistry, and a")
    print("  double bond carries a spelling too.")
    print()
    print("  AND THERE IS A SECOND WAY TO STRIP A SPELLING THAT IS WRONG HERE.")
    print("  MolToSmiles(mol, isomericSmiles=False) drops ISOTOPE labels with")
    print("  the stereochemistry:")
    trap = []
    for cid, raw in sorted(CORPUS.items()):
        try:
            canon = c(raw)
        except Exception:                                   # noqa: BLE001
            continue
        if isotope_flat(canon) != flat(canon):
            trap.append((cid, canon, isotope_flat(canon)))
    for cid, canon, iso in trap[:6]:
        print(f"     {cid:22s} {canon:22s} -> {iso:14s} (a DIFFERENT species)")
    print(f"  corpus compounds that flag would merge            {len(trap):5d}")
    print("  RemoveStereochemistry touches only stereochemistry, which is why")
    print("  matter/molecule.py's stereo_free_smiles uses it and says so.")


def panel2():
    rule("PANEL 2 -- WHICH TABLES CARRY A SPELLING, AND THE PATTERN IS NOT SUBTLE")
    tables = [
        ("MEASURED_PHYSICAL", list(MEASURED_PHYSICAL), "GENERATED from the corpus"),
        ("PHYSICAL_PROPERTIES", list(PHYSICAL_PROPERTIES), "hand-typed"),
        ("IDEAL_GAS_FORMATION", list(IDEAL_GAS_FORMATION), "hand-typed"),
        ("DERIVED_GAS_FORMATION", list(DERIVED_GAS_FORMATION), "hand-typed"),
        ("LIQUID_FORMATION", list(LIQUID_FORMATION), "hand-typed"),
        ("_CURATED_RAW", list(_CURATED_RAW), "hand-typed"),
        ("_CURATED_FUSION", list(_CURATED_FUSION), "hand-typed"),
        ("electrolyte._PAIRS acids", [p.acid for p in electrolyte._PAIRS],
         "hand-typed"),
    ]
    print(f"     {'table':28s} {'keys':>6s} {'stereo':>7s}  origin")
    for nm, keys, origin in tables:
        n = 0
        for k in keys:
            try:
                kk = c(k)
            except Exception:                               # noqa: BLE001
                continue
            if flat(kk) != kk:
                n += 1
        print(f"     {nm:28s} {len(keys):6d} {n:7d}  {origin}")
    print()
    print("  ONE table carries stereochemistry and it is the one a GENERATOR")
    print("  wrote. S13 built it by resolving corpus SMILES to CAS numbers, so")
    print("  it inherited the corpus's spelling; every other table was typed by")
    print("  hand, and a human types the simple form.")
    print()
    print("  lactic acid is the compound where that costs BOTH halves at once:")
    chi, fla = c("C[C@H](O)C(=O)O"), c("CC(O)C(=O)O")
    for nm, keys, _ in tables:
        ks = set()
        for k in keys:
            try:
                ks.add(c(k))
            except Exception:                               # noqa: BLE001
                pass
        if chi in ks or fla in ks:
            print(f"     {nm:28s} chiral={str(chi in ks):5s} flat={fla in ks}")
    print("  The corpus spells it CHIRAL. Before this session, that spelling")
    print("  reached the physical record and missed the formation one, and the")
    print("  flat spelling a template makes did the reverse -- so NEITHER")
    print("  spelling of lactic acid got both halves off the best source.")


def panel3():
    rule("PANEL 3 -- THE TWO QUESTIONS, AND THE 103 COMPOUNDS BETWEEN THEM")
    phys = {c(k) for k in MEASURED_PHYSICAL} | {c(k) for k in PHYSICAL_PROPERTIES}
    form = ({c(k) for k in IDEAL_GAS_FORMATION}
            | {c(k) for k in DERIVED_GAS_FORMATION}
            | {c(k) for k in LIQUID_FORMATION}
            | {c(k) for k in _CURATED_RAW})

    def member(s):
        return (s in phys, s in form)

    mem, moved, refused = [], [], []
    for cid, canon, f, _raw in STEREO:
        if member(canon) != member(f):
            mem.append((cid, canon, f, member(canon), member(f)))
        a, b = resolved(OFF, canon), resolved(OFF, f)
        if (a is None) != (b is None):
            refused.append((cid, canon, f))
        elif a is not None and a.source != b.source:
            moved.append((cid, canon, f))
    print(f"  MEMBERSHIP differs chiral vs flat                {len(mem):5d}"
          "   <- C6's question")
    print(f"  RESOLVED SOURCE differs chiral vs flat           {len(moved):5d}"
          "   <- C4's question")
    print(f"  one spelling REFUSED and the other priced        {len(refused):5d}")
    tet = sum(1 for cid, canon, _f in moved if "@" in canon)
    print(f"        of the movers, TETRAHEDRAL                 {tet:5d}"
          "   <- C4 reported 31")
    print()
    mem_ids = {r[0] for r in mem}
    mov_ids = {r[0] for r in moved}
    print(f"  membership differs AND the value moves           "
          f"{len(mem_ids & mov_ids):5d}")
    print(f"  membership differs and the value does NOT        "
          f"{len(mem_ids - mov_ids):5d}   <- the gap")
    print(f"  the value moves and membership does NOT          "
          f"{len(mov_ids - mem_ids):5d}")
    print()
    print("  WHY THE RECORD CAN EXIST AND CHANGE NOTHING: it holds a melting")
    print("  point and no boiling point. Tier 2 of the physical half is gated")
    print("  on 'm.Tb is not None', and the Tm overlay below it on")
    print("  'half.Tb is None' -- so a species Joback CAN fragment keeps")
    print("  Joback's Tb and Joback's Tm, and the measured Tm never lands.")
    no_tb = with_tb = 0
    keyed = {c(k): v for k, v in MEASURED_PHYSICAL.items()}
    for cid in sorted(mem_ids - mov_ids):
        canon = next(r[1] for r in STEREO if r[0] == cid)
        m = keyed.get(canon)
        if m is None:
            continue
        if m.Tb is None:
            no_tb += 1
        else:
            with_tb += 1
    print(f"     of those, the record has NO Tb                {no_tb:5d}")
    print(f"     of those, the record HAS a Tb                 {with_tb:5d}")
    print()
    print("  So membership counts records; only the second question counts")
    print("  NUMBERS. That is the 4.7x, and it is a methodological difference")
    print("  after all -- but only because someone went and looked.")


def panel4():
    rule("PANEL 4 -- IS IT LIVE? WHAT A TEMPLATE EMITS, AND IT IS NOT THE CORPUS'S")
    tmpls = {}
    for mod in (synthesis, library):
        for nm in dir(mod):
            fn = getattr(mod, nm)
            if not callable(fn) or nm.startswith("_"):
                continue
            try:
                r = fn()
            except Exception:                               # noqa: BLE001
                continue
            for t in (r if isinstance(r, list) else [r]):
                if hasattr(t, "smarts"):
                    tmpls[t.name] = t.smarts
    r_st = p_st = 0
    for _nm, sm in tmpls.items():
        react, _, prod = sm.partition(">>")
        r_st += any(ch in react for ch in "@/\\")
        p_st += any(ch in prod for ch in "@/\\")
    print(f"  templates reachable with default arguments       {len(tmpls):5d}")
    print(f"  ... whose REACTANT side names stereochemistry    {r_st:5d}")
    print(f"  ... whose PRODUCT  side names stereochemistry    {p_st:5d}")
    print()
    print("  A rewrite cannot emit a spelling its SMARTS does not name, so")
    print("  every centre a template makes or touches comes out UNSPECIFIED.")
    print("  matter/molecule.py said this in prose -- 'templates do not yet")
    print("  control stereochemistry, so a rewrite can lose it' -- and nothing")
    print("  had measured what it costs. Four catalog steps, run:")
    print()
    cases = [
        ("perkin-route 1", synthesis.perkin_condensation(),
         ("benzaldehyde", "acetic-anhydride"), "cinnamic-acid"),
        ("knoevenagel-route 1", synthesis.knoevenagel_doebner(),
         ("benzaldehyde", "malonic-acid"), "cinnamic-acid"),
        ("menthol-route 2", synthesis.alkene_hydrogenation(),
         ("isopulegol", "hydrogen"), "menthol"),
        ("lactic-acid-pla 1", synthesis.homolactic_fermentation(),
         ("glucose",), "lactic-acid"),
        ("biodiesel-route 1", synthesis.transesterification(),
         ("triolein", "methanol"), "methyl-oleate"),
    ]
    for label, t, reactant_ids, target_id in cases:
        mols = tuple(Molecule.from_smiles(CORPUS[i]) for i in reactant_ids)
        outs = t.run(mols)
        target = c(CORPUS[target_id])
        made = sorted({p.smiles for tup in outs for p in tup})
        hit = [s for s in made if flat(s) == flat(target)]
        if not hit:
            print(f"  {label:22s} did not make {target_id}")
            continue
        spelling = hit[0]
        same = "SAME SPELLING" if spelling == target else "DIFFERENT SPELLING"
        print(f"  {label:22s} {t.name}")
        print(f"     corpus    {target_id:16s} {target}")
        print(f"     emitted   {'':16s} {spelling}   <- {same}")
        if spelling == target:
            print("     (the control: this template does not touch the C=C, so")
            print("      RDKit carries the spelling through untouched)")
            continue
        for who, smi in (("corpus  ", target), ("template", spelling)):
            for tag, prov in (("was", OFF), ("now", ON)):
                d = resolved(prov, smi)
                tb = f"{d.Tb:7.1f}" if d and d.Tb else "      -"
                half = (d.source.split("physical half: ")[-1][:34]
                        if d else "REFUSED")
                print(f"     {tag} {who} Tb={tb}  {half}")


def panel5():
    rule("PANEL 5 -- WHAT THE FALLBACK MOVED, MEASURED BOTH WAYS")
    changed, still, agree_now, noise = [], [], 0, 0
    for cid, canon, f, _raw in STEREO:
        a_off, b_off = resolved(OFF, canon), resolved(OFF, f)
        a_on, b_on = resolved(ON, canon), resolved(ON, f)
        if not same_numbers(a_off, a_on):
            changed.append((cid, canon, a_off, a_on))
        if a_off is None or b_off is None:
            continue
        if not same_numbers(a_off, b_off):
            if same_numbers(a_on, b_on):
                agree_now += 1
            else:
                still.append((cid, canon, f))
        if same_numbers(a_on, b_on) and numbers_of(a_on) != numbers_of(b_on):
            noise += 1
    print(f"  corpus compounds spelled with stereochemistry    {len(STEREO):5d}")
    print(f"  ... whose OWN resolved numbers changed           {len(changed):5d}")
    print("      (Hf, Gf, Tb, Tc, Pc, Tm and the Cp polynomial, compared as a")
    print("       tuple -- a wider test than the source string panel 3 uses)")
    print(f"  ... whose two spellings DISAGREED and now agree  {agree_now:5d}")
    print(f"  ... whose two spellings disagree STILL           {len(still):5d}")
    print(f"  ... agreeing to 1e-12 but not BIT-IDENTICAL      {noise:5d}")
    print("      (Benson sums groups in SMILES atom order, so a re-spelled")
    print("       molecule gives Cp coefficients differing in the last bits.")
    print("       Compared with '==' that reads as a failure to fix them.)")
    print()
    if still:
        print("  the ones that still disagree, and why:")
        for cid, _canon, fk in still:
            print(f"     {cid:26s} its flat key is answered by "
                  f"{len(_skeleton_index().get(fk, [])):d} record(s)")
        print("     -- more than one is the AMBIGUITY guard; exactly one is a")
        print("        SIBLING the query may not take (see panel 6).")
    print()
    if changed:
        print("  the corpus rows that moved, and by how much:")
        print(f"     {'compound':24s} {'Tb was':>9s} {'Tb now':>9s}"
              f" {'Hf was':>10s} {'Hf now':>10s}")
        for cid, _canon, a, b in changed[:18]:
            tb0 = f"{a.Tb:9.1f}" if a.Tb else "        -"
            tb1 = f"{b.Tb:9.1f}" if b.Tb else "        -"
            print(f"     {cid:24s} {tb0} {tb1} {a.Hf:10.1f} {b.Hf:10.1f}")
    print()
    print("  EVERY ONE OF THOSE IS A CHIRAL CORPUS ROW REACHING A FLAT RECORD.")
    print("  The other direction -- a FLAT species reaching a chiral record --")
    print("  does not appear here because the corpus does not spell one; it is")
    print("  what a TEMPLATE makes, and panel 4 is where it shows up.")


_SKEL = {}


def _skeleton_index():
    """flat key -> the MEASURED_PHYSICAL spellings that answer it."""
    if not _SKEL:
        for k in MEASURED_PHYSICAL:
            kk = c(k)
            _SKEL.setdefault(flat(kk), []).append(kk)
    return _SKEL


def panel6():
    rule("PANEL 6 -- WHAT THE FALLBACK REFUSES, AND WHY IT HAS TO")
    idx = _skeleton_index()
    multi = {k: v for k, v in idx.items() if len(v) > 1}
    print(f"  skeletons in MEASURED_PHYSICAL with >1 spelling  {len(multi):5d}")
    print()
    print("  what a fallback WITHOUT the uniqueness guard would hand a flat")
    print("  query, and what the spread between the candidates is:")
    for bare, keys in sorted(multi.items(), key=lambda kv: -len(kv[1])):
        tbs = []
        for k in keys:
            m = MEASURED_PHYSICAL[
                next(orig for orig in MEASURED_PHYSICAL if c(orig) == k)]
            tbs.append(m.Tb.value if m.Tb else None)
        real = [t for t in tbs if t is not None]
        spread = (f"{max(real) - min(real):8.1f} K" if len(real) > 1
                  else "        -")
        print(f"     {bare[:44]:44s} {len(keys)} spellings, dTb {spread}")
    print()
    print("  A flat butenedioic acid would take maleic or fumaric acid's")
    print("  boiling point depending on dict order. THE GUARD IS NOT")
    print("  DEFENSIVE PROGRAMMING -- it is the difference between a fallback")
    print("  and a wrong measurement wearing a measurement's authority.")
    print()
    print("  what it ALSO refuses, deliberately: a chiral query whose skeleton")
    print("  has no flat record does not take a SIBLING chiral record, even")
    print("  its own enantiomer. Cost of that refusal, measured:")
    sib = []
    for cid, canon, f, _raw in STEREO:
        if canon in idx.get(f, []):
            continue
        cands = [k for k in idx.get(f, []) if k != canon]
        if len(cands) == 1 and f not in idx.get(f, []):
            a, b = resolved(ON, canon), resolved(ON, f)
            gap = (abs(a.Tb - b.Tb)
                   if a and b and a.Tb and b.Tb else 0.0)
            sib.append((gap, cid, cands[0]))
    print(f"     corpus rows a sibling record could have priced   {len(sib):5d}")
    for gap, cid, cand in sorted(sib, reverse=True):
        print(f"        {cid:24s} dTb {gap:7.1f} K   the table holds "
              f"{cand[:30]}")
    print()
    print("  TWO ROWS, AND THE RULE IS RIGHT ABOUT ONE AND COSTS THE OTHER --")
    print("  WHICH IS THE WHOLE ARGUMENT IN TWO LINES.")
    print("    * elaidic-acid is the TRANS fatty acid and the table holds the")
    print("      CIS one, oleic acid. Those are different compounds that boil")
    print("      128 K apart. Refusing is CORRECT and the number is not a")
    print("      cost at all.")
    print("    * pla-unit is D-lactic acid and the table holds the L. Two")
    print("      enantiomers have the same scalar thermochemistry, so that")
    print("      record IS its record, and 107 K of Joback is a real loss.")
    print("  A rule that took the sibling would be right once and wrong once.")
    print("  Separating them means inverting every centre and comparing --")
    print("  cheap to state, easy to get wrong on a diastereomer, and worth")
    print("  exactly the one row above. Priced rather than guessed at.")


def panel7():
    rule("PANEL 7 -- WHAT IS STILL KEYED FLAT AND IS NOT WRAPPED")
    acids = {p.acid for p in electrolyte._PAIRS}
    canon_acids = set()
    for a in acids:
        try:
            canon_acids.add(c(a))
        except Exception:                                   # noqa: BLE001
            pass
    hits = []
    for cid, canon, f, _raw in STEREO:
        if f in canon_acids and canon not in canon_acids:
            hits.append((cid, canon, f))
    print(f"  corpus compounds spelled with stereochemistry    {len(STEREO):5d}")
    print(f"  ... whose FLAT spelling is a priced ACID and      {len(hits):5d}")
    print("      whose own spelling is not")
    for cid, canon, f in hits:
        print(f"     {cid:20s} {canon:26s} the table holds {f}")
    print()
    print("  electrolyte._PAIRS is NOT wrapped by this session's fallback, and")
    print("  that is a scope decision rather than an oversight: _PAIRS decides")
    print("  WHICH IONS EXIST, so widening it changes the state vector, not a")
    print("  number in it. Both rows above are lactic acid and both are LIVE")
    print("  -- a corpus-spelled lactic acid in water does not dissociate --")
    print("  and the honest place to fix it is a session that owns the")
    print("  network-construction change and the audit it owes.")


def panel8():
    rule("PANEL 8 -- WHERE PANEL 3's GAP COMES FROM, AND IT IS NOT STEREOCHEMISTRY")
    with_tm_no_tb = discarded = 0
    worst = []
    for raw, m in MEASURED_PHYSICAL.items():
        if m.Tb is not None or m.Tm is None:
            continue
        with_tm_no_tb += 1
        d = resolved(ON, c(raw))
        if d is None or d.Tb is None or d.Tm is None:
            continue
        if abs(d.Tm - m.Tm.value) > 1.0:
            discarded += 1
            worst.append((abs(d.Tm - m.Tm.value), raw, m.Tm.value, d.Tm))
    print(f"  MEASURED_PHYSICAL entries                        "
          f"{len(MEASURED_PHYSICAL):5d}")
    print(f"  ... holding a melting point and NO boiling point {with_tm_no_tb:5d}")
    print(f"  ... whose measured Tm never reaches the record   {discarded:5d}")
    print()
    print("  the physical half reads:")
    print("     if m.Tm is not None and half.Tb is None:")
    print("  so a measured melting point is overlaid only where NOTHING else")
    print("  supplied a boiling point. Joback supplies one for anything he can")
    print("  fragment, and then he supplies the melting point too:")
    print()
    print(f"     {'species':44s} {'measured':>9s} {'record':>9s} {'off by':>8s}")
    for gap, raw, meas, rec in sorted(worst, reverse=True)[:8]:
        print(f"     {raw[:44]:44s} {meas:9.1f} {rec:9.1f} {gap:8.1f}")
    print()
    print("  THE COMMENT BESIDE THAT GATE ARGUES IT IS HARMLESS ON A CLAIM THE")
    print("  GENERATED FILE CONTRADICTS: 'Nothing in the measured table is a")
    print("  species Joback already prices completely (the builder checks and")
    print("  reports)'. The builder CLASSIFIES and does not exclude -- it")
    print("  stamps each entry - and the file says:")
    path = os.path.join(_ROOT, "src", "chemsim", "properties", "physical_data.py")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for state in ("complete", "partial", "unfragmentable"):
        print(f"     Joback: {state:16s} {text.count('Joback: ' + state):5d} entries")
    print()
    print("  Tm drives crystallisation and enters the solubility law")
    print("  exponentially, so this is worth more than the thing this audit")
    print("  was written about. NOT fixed here: it would move 214 species in a")
    print("  session about spellings, and neither change would be attributable.")


def main() -> None:
    panel1()
    panel2()
    panel3()
    panel4()
    panel5()
    panel6()
    panel7()
    panel8()
    print()


if __name__ == "__main__":
    main()

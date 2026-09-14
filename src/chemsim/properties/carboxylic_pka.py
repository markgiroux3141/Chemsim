"""Layer 1 -- the carboxylic plateau, as a rule with a stated domain.

``electrolyte._PAIRS`` is thirty-odd hand-typed rows and it cannot be the whole
answer for carboxylic acids. T14 counted why, over the 1,583-compound catalog
and over a 36-flask sweep of the only carboxyl on the natural shelf: 624
distinct conjugate pairs, 12 priced, 270 inside the domain below -- and 243 of
those 270 are oligomers of ONE self-esterifying acid, a condensation series with
no last member that stopped where it did only because the flask hit its species
cap. A table closes a list, and that is not a list. So this is a rule.

WHAT THE RULE SAYS
------------------
Every unbranched aliphatic carboxylic acid sits on the same plateau: acetic
4.76, propanoic 4.87, octanoic 4.89, nonanoic 4.96, oleic 5.02. The plateau
value is NOT written down here -- ``plateau()`` derives it from whichever rows
of ``_PAIRS`` the domain test below admits, so the rule and the table it
generalises cannot drift apart. Formic acid is outside the domain and that is
why it is a full unit away at 3.75: it has no carbon on its carboxyl.

WHY THE DOMAIN IS LOCAL
-----------------------
Acidity is inductive and inductive effects die off by roughly a factor of three
per bond: chloroacetic 2.86 against acetic's 4.76, 3-chloropropanoic 4.0,
4-chlorobutanoic 4.5, silent by the fifth carbon. The plateau is therefore a
property of the three carbons nearest the carboxyl and not of the molecule, so
the domain is alpha, beta and gamma being unbranched saturated CH2 with no
heteroatom, ring, charge or unsaturation among them -- whatever the far end of
the molecule does. 12-hydroxystearic acid is inside it, with its hydroxyl nine
bonds away; ``strict`` is the narrower statement that the whole molecule is a
plain C/H chain, reported separately because the audit wanted both.

THE OTHER CLASSES WERE ASKED THE SAME QUESTION AND REFUSED
----------------------------------------------------------
This is the only rule, and T23 wrote down why rather than leaving the next
session to re-derive it: ``docs/design/phenol-pka-rule-refused.md``, measured by
``validation/pka_domains.py`` panels 0 and 4.

The one exclusion that is not local is the basic nitrogen, and it is chemistry
rather than caution: at any pH that titrates the carboxyl an amine four bonds
away is already protonated, so what the carboxyl feels is a FULL POSITIVE
CHARGE and not a dipole dying off per bond. GABA is measured at 4.03 and
6-aminohexanoic acid at 4.43, both a long way below the plateau. The molecule
being titrated is a zwitterion and a different acid.

The predicate was written and pinned in ``validation/fatty_acid_pka.py`` for
T14, which is where its 14 worked examples still live (``tests/``). T18 moved
it here and left the audit importing it, so there is one predicate rather than
two. Nothing here imports RDKit: the graph questions go through ``Molecule``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from chemsim.matter import Molecule

# The dissociation template's own slot, minus the requirement that the proton
# still be on -- this has to find the anion as well, which is the direction the
# engine asks in.
CARBOXYL = "[CX3](=[OX1])[OX2H1,OX1H0-]"

# How far inductive withdrawal is still worth a decimal place. Alpha, beta and
# gamma; the fourth carbon moves a pKa by less than the spread of the plateau
# itself and cannot be resolved by a rule that quotes one number.
LOCAL_DEPTH = 3

# The amine and not the amide: an amide nitrogen is not basic, which is why a
# nylon unit still has to be read one N at a time. A nitrile N is X1 and a nitro
# N is either charged or doubly bonded, so all three fall out without a clause
# of their own. An aromatic ring nitrogen is ``n`` and is NOT matched -- a
# pyridine carboxylic acid is left in whatever bucket its ring puts it in, which
# is a limit of this exclusion and not a claim about it.
BASIC_N = "[NX3;!$(N[#6]=[O,N,S]);!$(N=*);!$([N+])]"

_LABELS = {1: "alpha", 2: "beta", 3: "gamma"}


def carboxyl_sites(mol: Molecule) -> list[tuple[int, int]]:
    """``(carboxyl carbon, acidic oxygen)`` for every carboxyl in the molecule."""
    return [(m[0], m[2]) for m in mol.substructure_matches(CARBOXYL)]


def as_pair(mol: Molecule, c_idx: int, o_idx: int) -> tuple[str, str] | None:
    """The conjugate acid and base this one carboxyl would give the table.

    ``(acid SMILES, base SMILES)``, or ``None`` if either half will not
    sanitise. Written by editing the acidic oxygen in both directions, so a
    compound spelled as a salt gives the same pair as the free acid does.
    """
    acid = mol.reprotonated(o_idx, 0, 1)
    base = mol.reprotonated(o_idx, -1, 0)
    if acid is None or base is None:
        return None
    return acid.smiles, base.smiles


def domain(
    mol: Molecule, c_idx: int, o_idx: int, n_sites: int
) -> tuple[str, str]:
    """Which domain this carboxyl sits in, and the reason if it sits outside.

    Returns ``("strict"|"local"|"outside", reason)``. The reason is empty inside
    the domain and names one structural fact outside it -- the first that
    applies, in order of how far it moves a pKa -- because the grouped reasons
    are the work order for whatever a second rule would have to be.
    """
    if n_sites > 1:
        return "outside", f"polyprotic ({n_sites} carboxyls)"
    if mol.substructure_matches(BASIC_N):
        return "outside", "zwitterion (basic nitrogen in the molecule)"

    atoms = mol.topology()
    carboxyl = {c_idx, o_idx}
    for nb in atoms[c_idx].neighbours:
        if atoms[nb].element == "O" and nb != o_idx:
            carboxyl.add(nb)

    alpha = [nb for nb in atoms[c_idx].neighbours if nb not in carboxyl]
    if not alpha:
        return "outside", "formyl (no carbon on the carboxyl)"
    if len(alpha) > 1:
        return "outside", "two carbons on the carboxyl carbon"
    if atoms[alpha[0]].element != "C":
        return "outside", "heteroatom acyl (not a carboxylic acid at all)"
    if atoms[alpha[0]].aromatic:
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
    while frontier:
        idx, d = frontier.pop(0)
        if idx in seen:
            continue
        seen.add(idx)
        atom, where = atoms[idx], _LABELS[d]
        if any(atoms[nb].element != "C" and nb not in carboxyl
               for nb in atom.neighbours):
            return "outside", f"heteroatom on the {where} carbon"
        if atom.charge:
            return "outside", f"formal charge on the {where} carbon"
        if atom.in_ring:
            return "outside", f"{where} ring atom"
        # sp3 is every bond single and the atom not aromatic. RDKit's
        # hybridization flag said the same thing for a carbon and cost a
        # Boundary 0 breach to ask.
        if atom.aromatic or any(o > 1.0 for o in atom.bond_orders):
            return "outside", f"{where} unsaturation"
        if len(atom.neighbours) > 2:
            return "outside", f"{where} branch"
        if d < LOCAL_DEPTH:
            frontier += [(nb, d + 1) for nb in atom.neighbours
                         if nb not in seen and atoms[nb].element == "C"]

    # Inside the local domain. Strict is the whole molecule saying the same.
    for atom in atoms:
        if atom.index in carboxyl:
            continue
        if atom.element != "C":
            return "local", ""
        if atom.in_ring or len(atom.neighbours) > 2:
            return "local", ""
    return "strict", ""


@dataclass(frozen=True)
class Plateau:
    """The plateau as measured off the table it generalises."""

    pKa: float          # the value the rule quotes
    low: float          # the narrowest row inside the domain, from C3 up
    high: float
    n: int              # how many curated rows it was measured from

    @property
    def width(self) -> float:
        return self.high - self.low

    def describe(self) -> str:
        return (
            f"pKa {self.pKa:.2f} (the mean of the {self.n} curated unbranched "
            f"aliphatic rows from C3 up, which span {self.low:.2f} to "
            f"{self.high:.2f})"
        )


def in_domain(smiles: str) -> tuple[int, int] | None:
    """The single carboxyl site this rule may price, or ``None``.

    Takes the acid OR the base spelling -- the pattern finds both -- and returns
    the ``(carbon, oxygen)`` indices in that same molecule, so the caller can
    edit the proton back on.
    """
    mol = Molecule.from_smiles(smiles)
    sites = carboxyl_sites(mol)
    if len(sites) != 1:
        return None
    c_idx, o_idx = sites[0]
    where, _ = domain(mol, c_idx, o_idx, len(sites))
    return (c_idx, o_idx) if where != "outside" else None


@lru_cache(maxsize=8)
def plateau(pairs) -> Plateau | None:
    """The plateau value, derived from the curated rows inside the domain.

    Derived and NEVER asserted, which is the T0.5 lesson applied to a
    constant: a rule that hard-codes 4.9 while ``_PAIRS`` moves underneath it
    would go on being green for ever. Formic acid is excluded by the domain test
    itself rather than by a carbon count, and the C1/C2 rows are excluded from
    the SPAN (not from the mean's domain test) the same way the audit does it,
    because acetic at 4.76 is the shoulder of the plateau and not the plateau.

    Returns ``None`` if fewer than two rows survive, which is the honest answer
    for a table that no longer supports the generalisation. Cached on the tuple
    of pairs, because it is asked once per ion priced by the rule and the answer
    depends on nothing else.
    """
    values = []
    for pair in pairs:
        try:
            mol = Molecule.from_smiles(pair.acid)
        except ValueError:
            continue
        sites = carboxyl_sites(mol)
        if len(sites) != 1:
            continue
        where, _ = domain(mol, sites[0][0], sites[0][1], len(sites))
        if where == "outside":
            continue
        carbons = sum(1 for a in mol.topology() if a.element == "C")
        if carbons >= 3:
            values.append(pair.pKa)
    if len(values) < 2:
        return None
    return Plateau(pKa=sum(values) / len(values), low=min(values),
                   high=max(values), n=len(values))

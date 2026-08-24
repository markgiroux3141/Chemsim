"""Regenerate ``chemsim.properties.benson_data`` from a RMG-database clone.

Run this rather than hand-editing ``benson_data.py``: the values are DERIVED
from an external source and the derivation has to stay reproducible and
auditable, which is the same rule the rest of the project's curated data obeys.

    git clone --depth 1 --filter=blob:none --sparse \
        https://github.com/ReactionMechanismGenerator/RMG-database.git
    cd RMG-database && git sparse-checkout set input/thermo/groups
    python tools/build_benson_data.py <path-to>/RMG-database/input/thermo/groups

RMG-database is MIT licensed. It is the open machine-readable form of Benson's
tabulation plus later revisions; each entry keeps its node label and source note
so a straight-from-Benson value stays distinguishable from a CBS-QB3 refit.

## Trap 1: RMG mixes kcal/mol and kJ/mol WITHIN ONE FILE

Entries sourced from Benson are kcal and cal; later revisions are kJ and J.
``Cs-CsHHH`` reads -10.2 and ``Cs-OsHHH`` reads -42.9 -- the same quantity to
within a revision, printed 4.184 apart. A whole-file unit assumption makes every
oxygen group four times too large, and it **validates perfectly on alkanes**
before wrecking anything with a functional group. ``_convert`` reads the declared
unit per entry and raises on one it does not recognise; do not "simplify" that
away.

## Trap 2: RMG's group tree is not flat, and several nodes share our key

RMG has ~2700 entries where we have ~750 keys, because RMG's tree carries
*second-order* nodes -- ``Cs-(N3dCd)HHH`` is a methyl on an N3d that is itself
bonded to a Cd -- and generic nodes with bracketed alternatives. Our keys are
strictly first-order (a central atom plus its ligands' types), so many RMG nodes
collapse onto one key. Whichever parsed first used to win, which is file order
deciding chemistry.

``SPECIFICITY`` is the rule now: fewest atoms beyond the first shell, then fewest
generic alternatives, then file order. Every collision is PRINTED with the spread
between the candidates, so a regeneration that starts picking differently says so.
This was not cosmetic. Three measured cases:

  * ``C-(C)(H)2(N)`` had ``Cs-NCsHH`` (generic N, -26.18 kJ/mol) beating
    ``Cs-N3sCsHH`` (concrete amine N, -10.93). Propylamine came out 15.8 kJ/mol
    too negative; with the concrete value it lands within 0.5 of measurement.
  * ``Cd-(Cd)(H)(S)`` had ``Cds-CdsSH`` (generic S, whose thermo ALIAS points at
    the S(IV) value, 115.31) beating ``Cds-CdsS2H`` (divalent S, 79.16). Every
    vinyl thioether and every thiophene carbon was priced as a sulfoxide.
  * ``CO-(C)(Cl)`` did not exist at all, because RMG writes acetyl chloride's
    carbonyl oxygen as a plain ``O`` with a double bond rather than as ``Od``.

## Trap 3: the oxo must be folded by BOND ORDER, not by atom type

Benson folds a terminal double-bonded oxygen into the central atom's identity: a
carbonyl is ONE group ``CO-(...)``, not a carbon group plus an oxygen group. RMG
names that oxygen ``Od``/``O2d`` in most entries and plain ``O`` in others. Keying
the fold on the atom type therefore counted the carbonyl oxygen as an ordinary
ligand in the ``O``-typed entries -- ``COCsClO`` came out as ``CO-(C)(Cl)(O)``,
which is a chloroformate, not an acyl chloride. ``_fold`` uses the declared bond
order, which is also exactly what ``benson._is_terminal_oxo`` does, so the two
sides of the pipeline agree by construction.

## Trap 4: group values from different tabulations cannot be mixed

RMG carries Benson's original ester split alongside Paraskevas's CBS-QB3 refit,
and the two divide the same ester linkage differently. Their SUMS agree to 3
kJ/mol; their splits differ by ~78. Mixing one tabulation's carbonyl with the
other's ester oxygen is a ~78 kJ/mol error that neither table shows on its own.
``INCOMPATIBLE_SPLIT`` names the affected keys and drops them, with the measured
residual; see its comment. This is the group-level form of the rule already in
``formation_data``: never mix sources within one entry.

## What is NOT wired in

``radical.py`` (hydrogen bond increments) and ``polycyclic.py``. Note also that
**RMG no longer ships ``gauche.py``** -- the gauche/branching corrections the
older layout kept there now live in ``longDistanceInteraction_noncyclic.py``,
which this script does read.
"""
import pathlib
import sys
from collections import Counter, defaultdict

import numpy as np

# Set from the command line -- see __main__.
BASE = ""


# RMG's group.py MIXES UNITS WITHIN THE FILE. The entries sourced straight from
# Benson are kcal/mol and cal/(mol K); the later CBS-QB3 revisions are kJ/mol and
# J/(mol K). Cs-CsHHH is -10.2 kcal while Cs-OsHHH is -42.9 kJ -- the same
# quantity to within Benson's own revision, but a factor of 4.184 apart on the
# page. Assuming one unit throughout makes every oxygen group 4x too large,
# which validates fine on alkanes and destroys anything with a functional group.
_ENERGY = {"kcal/mol": 4.184, "kJ/mol": 1.0, "J/mol": 1.0e-3}
_ENTROPY = {"cal/(mol*K)": 4.184, "J/(mol*K)": 1.0, "kJ/(mol*K)": 1000.0}


def _convert(spec, table, what):
    """(value, unit, ...) -> value in our units, or raise on an unknown unit."""
    if spec is None:
        return None
    value, unit = spec[0], spec[1]
    if unit not in table:
        raise ValueError(f"unknown {what} unit {unit!r} in RMG data")
    factor = table[unit]
    if isinstance(value, (list, tuple)):
        return [v * factor for v in value]
    return value * factor


class ThermoData:
    """H298 in kJ/mol, S298 and Cp in J/(mol K), whatever the file declared."""

    def __init__(self, Tdata=None, Cpdata=None, H298=None, S298=None, **kw):
        self.Cp = _convert(Cpdata, _ENTROPY, "heat capacity")
        self.H298 = _convert(H298, _ENERGY, "enthalpy")
        self.S298 = _convert(S298, _ENTROPY, "entropy")


class Wilhoit:                      # a few entries use this form
    def __init__(self, *a, **k):
        self.H298 = self.S298 = self.Cp = None


class NASA:
    def __init__(self, *a, **k):
        self.H298 = self.S298 = self.Cp = None


def load(path):
    entries = []

    def entry(**kw):
        entries.append(kw)

    ns = {"entry": entry, "ThermoData": ThermoData, "Wilhoit": Wilhoit,
          "tree": lambda *a, **k: None,
          "NASA": NASA, "NASAPolynomial": lambda *a, **k: None,
          "name": "", "shortDesc": "", "longDesc": ""}
    src = open(path, encoding="utf-8").read()
    exec(compile(src, path, "exec"), ns)
    return entries


def resolver(entries):
    """A function following RMG's ``thermo = 'other-label'`` aliases to a value.

    Worth knowing that these aliases exist: ``Cds-CdsSH`` carries no data of its
    own and points at ``Cds-CdsS4H``, so a generic sulfur node silently inherits
    the S(IV) number. That is one of the collisions the specificity rule settles.
    """
    by_label = {e["label"]: e for e in entries}

    def resolve(e, seen=()):
        t = e.get("thermo")
        if isinstance(t, str):
            if t in seen or t not in by_label:
                return None
            return resolve(by_label[t], seen + (t,))
        return t

    return resolve


# ---------------------------------------------------------------------------
# adjacency lists
# ---------------------------------------------------------------------------

_ORDERS = {"S": 1.0, "D": 2.0, "T": 3.0, "B": 1.5, "Q": 4.0}


def parse_adjacency(text):
    """RMG adjacency list -> (central index, {index: (atomtype, {nbr: order})}).

    Lines look like::

        1 * Cs u0 {2,S} {3,S} {4,S} {5,S}
        2   Cs u0 {1,S}

    The starred atom is the group's central atom. Atom types may be a single
    token (``Cs``) or a bracketed alternative list (``[Cs,Cd]``); bond orders may
    likewise be a single letter or an alternative list. Orders come back as
    floats where the file names exactly one, and ``None`` where it names several
    -- a generic bond cannot decide whether an oxygen is a carbonyl.
    """
    atoms = {}
    central = None
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        idx = int(parts[0])
        pos = 1
        # Long-distance-interaction files star TWO atoms (*1, *2); plain group
        # files star one (*). Either way the marker is its own token.
        while pos < len(parts) and parts[pos].startswith("*"):
            if parts[pos] == "*":
                central = idx
            pos += 1
        atomtype = parts[pos]
        pos += 1
        bonds = {}
        for tok in parts[pos:]:
            if tok.startswith("{") and tok.endswith("}"):
                # A bond may name alternatives -- "{2,[S,D]}" -- so split on the
                # first comma only; the rest is the (possibly generic) order.
                a, _, b = tok[1:-1].partition(",")
                bonds[int(a)] = _ORDERS.get(b)
            atoms[idx] = (atomtype, bonds)
        atoms.setdefault(idx, (atomtype, bonds))
    return central, atoms


# RMG atom type -> our Benson ligand/central type.
#
# CONCRETE TYPES ONLY. RMG's bare-element tokens (``C``, ``N``, ``O``, ``S``) are
# generic tree nodes meaning "any atom of this element", and mapping them onto our
# specific types is what let a generic node outrank a concrete one -- see Trap 2.
# The halogens are the exception and stay: RMG has exactly one type per halogen,
# so ``Cl`` and ``Cl1s`` are the same thing and dropping the bare form used to
# refuse every halide.
ATOM_MAP = {
    "Cs": "C", "Cd": "Cd", "Cb": "Cb", "Ct": "Ct", "CO": "CO", "CS": "CS",
    "Cdd": "Cdd", "Cbf": "Cbf",
    "H": "H",
    "Os": "O", "O2s": "O", "Od": "Od", "O2d": "Od", "O0sc": "O",
    "N3s": "N", "N3d": "Nd", "N3b": "Nb", "N3t": "Nt",
    "N5sc": "N5sc", "N5dc": "N5dc", "N5ddc": "N5ddc", "N5tc": "N5tc",
    "S2s": "S", "S2d": "Sd", "S4d": "S4d", "S6dd": "S6dd", "S4s": "S4s",
    "S6d": "S6d", "S6s": "S6s", "S2t": "S2t", "S4dd": "S4dd",
    "F1s": "F", "Cl1s": "Cl", "Br1s": "Br", "I1s": "I",
    "F": "F", "Cl": "Cl", "Br": "Br", "I": "I",
    "Sis": "Si", "Sid": "Si",
}

# Central types our assigner never emits, because it folds them into a
# neighbour's identity. An entry centred on one of these describes a group that
# does not exist in our scheme, so it is dropped rather than written out under a
# key nothing will ever look up. ``Od`` is the carbonyl oxygen; ``Nt`` is the
# nitrile nitrogen.
FOLDED_CENTRES = frozenset({"Od", "Nt"})


def _members(token):
    """RMG atom-type token -> its alternative type names, bracketed or not."""
    if token.startswith("[") and token.endswith("]"):
        return [p.strip() for p in token[1:-1].split(",")]
    return [token]


def _element(token):
    """The element an RMG atom-type token names, or None if it is ambiguous.

    Used for the oxo and nitrile folds, which must key on the ELEMENT and the
    BOND ORDER rather than on the atom type -- RMG writes a carbonyl oxygen as
    ``Od`` in most entries and as a bare ``O`` in others, and typing the fold off
    ``Od`` alone turned acetyl chloride's carbonyl oxygen into an ordinary ligand
    (Trap 3).
    """
    els = set()
    for m in _members(token):
        if not m or not m[0].isalpha():
            return None
        # Two-letter elements first; the rest are the leading capital.
        el = m[:2] if m[:2] in {"Cl", "Br", "Si"} else m[:1]
        if el not in {"C", "H", "N", "O", "S", "F", "Cl", "Br", "I", "Si"}:
            return None
        els.add(el)
    return els.pop() if len(els) == 1 else None


def _alternatives(token):
    """RMG atom-type token -> the tuple of our types it could mean.

    A bare token means one type. A bracketed list -- ``[S4s,S4d,S4b,S4t]``, "any
    tetravalent sulfur" -- means several, and its value is a single number
    covering all of them. Those are kept but ranked below any concrete entry, so
    a specific value always wins where one exists. Without them the sulfoxide
    groups are unreachable: RMG has no ``Cs-S4dHHH``, only the bracketed
    ``Cs-S4HHH``, so DMSO's methyls have no other source.

    A member we cannot type is DROPPED rather than failing the whole token, but
    only when every dropped member is the same element as one we kept --
    ``[S4s,S4d,S4b,S4t]`` loses the exotic aromatic and triple-bonded sulfurs and
    still means "S(IV)", whereas ``[C,H,N,O,S]`` means nothing we can express and
    must fail.
    """
    members = _members(token)
    out, dropped = [], []
    for p in members:
        m = ATOM_MAP.get(p)
        if m is None:
            dropped.append(p)
            continue
        if m not in out:
            out.append(m)
    if not out:
        return ()
    if dropped:
        kept_elements = {_element(p) for p in members if ATOM_MAP.get(p) is not None}
        if any(_element(p) not in kept_elements for p in dropped):
            return ()
    return tuple(out)


# Sulfur oxidation states, for turning a bracketed S(IV)/S(VI) alternative into
# the types our assigner actually emits. Our types name the number of terminal
# oxo oxygens, because that is what the molecular graph shows.
_S_STATE = {
    "S4s": ("SO", "S4s"),      # any S(IV): the sulfoxide, or a bare S(IV)
    "S4d": ("SO",),
    "S4dd": ("SO2",),
    "S6dd": ("SO2",),
    "S6d": ("SO2",),
    "S6s": ("SO2", "S6s"),
}


class Group:
    """One RMG entry reduced to our key, plus how specific it was.

    ``extra`` counts atoms beyond the central atom's first shell that were not
    folded -- a second-order refinement our first-order key cannot express.
    ``generic`` counts bracketed alternatives used. Both are penalties.

    ``role`` is ``"group"`` for an ordinary entry and ``"nitrile_n"`` for one
    centred on a nitrile nitrogen. We fold that nitrogen into its carbon and RMG
    prices it separately, so its value has to be ADDED to the carbon's rather than
    written out under a key nothing looks up -- see ``build``.
    """

    __slots__ = ("key", "extra", "generic", "role")

    def __init__(self, key, extra, generic, role="group"):
        self.key, self.extra, self.generic = key, extra, generic
        self.role = role

    @property
    def specificity(self):
        """Ranking key: fewest generic alternatives first, then least depth.

        Genericity outranks depth, and that order is measured rather than
        assumed. All three known mis-picks were a generic node beating a concrete
        one -- the amine nitrogen, the divalent sulfur, and the vinyl-ester
        carbonyl, where ``Cds-OdCdsOs`` (generic ligand, no depth) would beat
        ``Cds-O2d(Cds-Cd)O2s`` (concrete, one atom of depth) by 84 kJ/mol in the
        wrong direction. Depth is often RMG restating what an atom type already
        implies -- ``(Cds-Cd)`` just means "a Cd" -- so it is the weaker signal.
        """
        return (self.generic, self.extra)


def _central_type(base, oxo, nitrile):
    """Fold terminal oxo oxygens and a nitrile nitrogen into the central type."""
    if nitrile:
        return "CN" if base in {"Ct", "C", "Cd"} else None
    if not oxo:
        return base
    if base == "C":
        return "CO"
    if base == "CO":
        return "CO"                  # RMG's atom type already names the carbonyl
    if base in {"S", "S4s", "S4d", "S4dd", "S6dd", "S6d", "S6s"}:
        return {1: "SO", 2: "SO2"}.get(oxo)
    if base in {"N", "Nd", "N5dc", "N5ddc"}:
        return "NO2" if oxo >= 2 else None
    return None


def rmg_key(text):
    """Convert one RMG group definition to our canonical Benson key, or None.

    ``None`` means the definition is generic, unmapped, or centred on an atom our
    scheme folds away. Returns just the key; ``analyse`` returns the specificity
    alongside it and is what the build uses.
    """
    g = analyse(text)
    return None if g is None else g.key


def analyse(text):
    """One RMG group definition -> a ``Group``, or None if unusable.

    Three folding conventions have to match ``benson.assign`` exactly, or the two
    halves of the pipeline write and read different keys:

    * a terminal double-bonded oxygen belongs to its neighbour's identity, by BOND
      ORDER not by atom type (Trap 3);
    * a nitrile nitrogen belongs to its carbon, which becomes ``CN`` -- so RMG's
      ``Ct`` + ``N3t`` pair is one of our atoms, and the nitrogen sitting two
      bonds from the centre is folded rather than counted as depth;
    * RMG names an aromatic or alkyne centre by its substituent alone, because
      the ring neighbours (or the triple-bond partner) are implied by the atom
      type. Our keys name every ligand, so those are put back.
    """
    central, atoms = parse_adjacency(text)
    if central is None or central not in atoms:
        return None

    # A nitrile nitrogen is not a group of its own here: it is folded into its
    # carbon, exactly as a carbonyl oxygen is folded into its. RMG prices it
    # separately, so re-root the analysis at the carbon -- the entry then lands on
    # the same ``CN-(...)`` key as the carbon's own entry and ``build`` sums the
    # two. Without that the partitions disagree and acetonitrile comes out
    # 115 kJ/mol high.
    role = "group"
    if _element(atoms[central][0]) == "N" and len(atoms[central][1]) == 1:
        (partner, order), = atoms[central][1].items()
        if order == 3.0 and partner in atoms and _element(atoms[partner][0]) == "C":
            central, role = partner, "nitrile_n"

    ctype, cbonds = atoms[central]

    generic = 0

    def one(token):
        nonlocal generic
        alt = _alternatives(token)
        if not alt:
            return None
        if len(alt) > 1:
            generic += 1
        return alt

    calt = one(ctype)
    if calt is None:
        return None

    # -- fold the central atom's own terminal oxo oxygens, by bond order -------
    oxo = 0
    nitrile = False
    folded = set()
    ligand_tokens = []
    for nbr, order in cbonds.items():
        if nbr not in atoms:
            return None
        ntype, nbonds = atoms[nbr]
        # A terminal oxygen double-bonded to the centre is the carbonyl/sulfonyl
        # oxygen; a terminal nitrogen triple-bonded to it makes a nitrile carbon.
        # Both tests are on the ELEMENT and the BOND ORDER, never on the atom
        # type -- see ``_element``. Terminal means no other bond in the group.
        el = _element(ntype)
        if el == "O" and order == 2.0 and len(nbonds) <= 1:
            oxo += 1
            folded.add(nbr)
            continue
        if el == "N" and order == 3.0 and len(nbonds) <= 1:
            nitrile = True
            folded.add(nbr)
            continue
        if not _alternatives(ntype):
            return None
        ligand_tokens.append((nbr, ntype, nbonds))

    cen_candidates = []
    for base in calt:
        t = _central_type(base, oxo, nitrile)
        if t is not None and t not in cen_candidates:
            cen_candidates.append(t)
        if oxo == 0 and not nitrile and base in _S_STATE:
            # A bracketed S(IV)/S(VI) node carries no oxo of its own, but the
            # sulfur it stands for does. Expand to the types our assigner emits.
            for t in _S_STATE[base]:
                if t not in cen_candidates:
                    cen_candidates.append(t)
    if not cen_candidates:
        return None
    if len(cen_candidates) > 1:
        generic += 1
    cen = cen_candidates[0]
    if cen in FOLDED_CENTRES:
        return None

    # -- ligand types ---------------------------------------------------------
    ligands = Counter()
    for nbr, ntype, nbonds in ligand_tokens:
        alt = one(ntype)
        if alt is None:
            return None
        lig = alt[0]
        if lig in FOLDED_CENTRES:
            return None               # a ligand our scheme folds away elsewhere
        # A ligand carbon triple-bonded to a terminal nitrogen is a nitrile
        # carbon: our type CN, with the nitrogen folded into it rather than
        # counted as a second-shell atom.
        if lig in {"Ct", "C", "Cd"}:
            for far, forder in nbonds.items():
                if far == central or far not in atoms:
                    continue
                if (
                    _element(atoms[far][0]) == "N"
                    and forder == 3.0 and len(atoms[far][1]) <= 1
                ):
                    lig = "CN"
                    folded.add(far)
        elif lig in _S_STATE:
            # Same expansion as for a central atom: a ligand sulfur's oxidation
            # state is part of our type. Only usable when the entry shows the
            # oxo explicitly; otherwise take the class value.
            n_oxo = sum(
                1 for f, fo in nbonds.items()
                if f in atoms and fo == 2.0 and _element(atoms[f][0]) == "O"
            )
            if n_oxo:
                lig = {1: "SO", 2: "SO2"}.get(n_oxo, lig)
                for f, fo in nbonds.items():
                    if fo == 2.0 and f in atoms:
                        folded.add(f)
            else:
                lig = _S_STATE[lig][0]
                generic += 1
        ligands[lig] += 1

    ligands.pop("Od", None)

    # RMG names an aromatic or alkyne centre by its SUBSTITUENT alone. Put the
    # implied neighbours back -- but not for a nitrile carbon, whose "partner" is
    # the nitrogen we just folded in.
    if cen == "Cb":
        ligands["Cb"] = 2
        # Benson names an ordinary benzenoid carbon's ring neighbours ``Cb`` even
        # when one is a fusion carbon, and ``benson.assign`` matches that; a
        # ``Cbf`` ligand on a ``Cb`` centre would be a key no tabulation has.
        ligands["Cb"] += ligands.pop("Cbf", 0)
    elif cen == "Ct":
        ligands.setdefault("Ct", 1)
    elif cen == "Cbf" and "Cbf" not in ligands and "Cb" not in ligands:
        return None                  # a bare Cbf tree node names no ring at all

    # -- specificity: atoms beyond the first shell that were not folded --------
    first_shell = set(cbonds) | {central} | folded
    extra = len([i for i in atoms if i not in first_shell])

    return Group(_key(cen, ligands), extra, generic, role)


def _key(cen, ligands):
    """Canonical key text: central type, then every ligand type, sorted."""
    parts = "".join(
        f"({k})" if v == 1 else f"({k}){v}"
        for k, v in sorted(ligands.items()) if v
    )
    return f"{cen}-{parts}"


def _substitute_ligand(key, old, new):
    """Rewrite a key with one ligand type replaced, re-canonicalising the order.

    Needed because sorting is on the type NAME: ``Cb-(CN)(Cb)2`` and
    ``Cb-(Cb)2(Ct)`` are the same group with the ligand renamed, but the rename
    moves it, so a textual replace would produce a key nothing matches.
    """
    cen, _, rest = key.partition("-")
    ligands = Counter()
    i = 0
    while i < len(rest):
        if rest[i] != "(":
            i += 1
            continue
        j = rest.index(")", i)
        name = rest[i + 1 : j]
        k = j + 1
        digits = ""
        while k < len(rest) and rest[k].isdigit():
            digits += rest[k]
            k += 1
        ligands[name] += int(digits) if digits else 1
        i = k
    if old not in ligands:
        return None
    ligands[new] += ligands.pop(old)
    return _key(cen, ligands)


T_CP = np.array([300.0, 400.0, 500.0, 600.0, 800.0, 1000.0, 1500.0])


# ---------------------------------------------------------------------------
# groups whose RMG value is on an incompatible tabulation
# ---------------------------------------------------------------------------
# RMG's group.py carries Benson's original ester partition next to Paraskevas's
# CBS-QB3 refit, and the two split the same ester linkage very differently:
#
#     aliphatic ester   CO-(C)(O)   -222.0  +  O-(C)(CO)  -102.2  = -324.2
#                       (both Paraskevas, and the sum is right)
#     aryl ester        CO-(Cb)(O)  -153.1  +  O-(C)(CO)  -102.2  = -255.3
#                       (Benson's carbonyl, Paraskevas's oxygen -- 78 kJ/mol out)
#
# RMG has no Paraskevas aryl-ester carbonyl to pair with, and re-anchoring
# Benson's onto the other split would mean introducing a number that is not in
# the clone. Measured on the curated set the mixture puts methyl benzoate
# +70.2 kJ/mol and ethyl benzoate +32.6 kJ/mol out in dGf, against Joback's -0.5
# and -25.1 -- so it is not merely worse, it is worse than the estimator it is
# supposed to improve on. Dropped, which sends aromatic esters back to Joback and
# says so, rather than returning a confident wrong number.
INCOMPATIBLE_SPLIT = {
    "CO-(Cb)(O)": (
        "Benson's aryl-ester carbonyl pairs only with Benson's ester oxygen, "
        "which RMG replaced with Paraskevas's CBS-QB3 value; the two splits "
        "differ by 78 kJ/mol. Methyl benzoate was +70 kJ/mol out."
    ),
}


# Rings we can identify from the molecular graph and have a value for. The key is
# the name ``benson.ring_key`` derives from the ring's canonical cyclic
# signature; the value is the RMG ring.py label. Anything not here is REFUSED
# rather than approximated -- a missing correction is up to 115 kJ/mol
# (cyclopropane).
#
# Absent on purpose, because RMG has no value for them: pyridine and every other
# nitrogen heteroaromatic, pyrrole, imidazole, and all fused heteroaromatics.
# ``ring.py`` simply does not contain them, so those species keep Joback.
RING_LABELS = {
    # 3-membered
    "cyclopropane": "Cyclopropane",
    "cyclopropene": "Cyclopropene",
    "cyclopropanone": "cyclopropanone",
    "oxirane": "Ethylene_oxide",
    "aziridine": "Ethyleneimine",
    "thiirane": "thiirane",
    "dioxirane": "dioxirane",
    # 4-membered
    "cyclobutane": "Cyclobutane",
    "cyclobutene": "Cyclobutene",
    "cyclobutanone": "Cyclobutanone",
    "oxetane": "Oxetane",
    "azetidine": "Azetidine",
    "thietane": "thietane",
    # 5-membered
    "cyclopentane": "Cyclopentane",
    "cyclopentene": "Cyclopentene",
    "cyclopentadiene": "Cyclopentadiene",
    "cyclopentanone": "Cyclopentanone",
    "tetrahydrofuran": "Tetrahydrofuran",
    "23dihydrofuran": "2,3-Dihydrofuran",
    "25dihydrofuran": "25dihydrofuran",
    "furan": "Furan",
    "13dioxolane": "1,3-Dioxolane",
    "12dioxolane": "12dioxolane",
    "pyrrolidine": "Pyrrolidine",
    "thiolane": "thiolane",
    "thiophene": "thiophene",
    "13dithiolane": "1,3-dithiolane",
    "12dithiolane": "1,2-dithiolane",
    "succinic_anhydride": "Dihydro-2,5-furandione",
    "maleic_anhydride": "2,5-Furandione",
    # 6-membered
    "benzene": "Benzene",
    "cyclohexane": "Cyclohexane",
    "cyclohexene": "Cyclohexene",
    "13cyclohexadiene": "1,3-Cyclohexadiene",
    "14cyclohexadiene": "1,4-Cyclohexadiene",
    "cyclohexanone": "Cyclohexanone",
    "piperidine": "Piperidine",
    "tetrahydropyran": "36dihydro2hpyran",
    "14dioxane": "1,4-Dioxane",
    "13dioxane": "1,3-Dioxane",
    "12dioxane": "12dioxane",
    # 7-membered
    "cycloheptane": "Cycloheptane",
    "cycloheptene": "Cycloheptene",
    # 8-membered
    "cyclooctane": "Cyclooctane",
}


# ---------------------------------------------------------------------------
# non-nearest-neighbour corrections
# ---------------------------------------------------------------------------
# RMG's ``longDistanceInteraction_cyclic.py`` and ``_noncyclic.py``. These are the
# terms a first-order group scheme structurally cannot see: two groups that are
# not neighbours but still interact.
#
# Note for anyone following the older RMG layout: there is no ``gauche.py`` any
# more. Benson's gauche/branching corrections are the ``CsCs-ST``.. family in the
# NONCYCLIC file, and that is where they are read from.
#
# The label grammar, reverse-engineered from the adjacency lists and checked
# against every entry:
#
#   ``<type1><type2>-<rank1><rank2>``  two atoms one bond apart (a 1,3 interaction
#       between their substituents). ``rank`` is the count of SINGLE-BONDED heavy
#       neighbours: 2 = S(econdary), 3 = T(ertiary), 4 = Q(uaternary). A double-bond
#       partner is not counted, which is what makes ``CdCs-ST`` consistent -- the
#       Cd has two single-bonded heavy neighbours, so it is S.
#   ``<type1><bridge><type2>-<rank1><rank2>``  the same, two bonds apart.
#   ``[omp]_<class>_<class>``  two substituted benzene carbons ortho/meta/para to
#       each other, each substituent one of six named classes.
#
# THE HALVING TRAP. RMG's matcher tries both assignments of its two labelled
# atoms, so an entry whose two sides are identical would be counted twice, and
# RMG stores such entries at HALF value -- announced only in prose, in
# ``shortDesc`` or ``longDesc``. We enumerate each unordered pair once, so those
# entries must be DOUBLED. Miss it and every symmetric case (o-xylene, catechol,
# 2,3-dimethylbutane) is exactly half-corrected, which is small enough to look
# like ordinary scatter.
_RANKS = ("S", "T", "Q")

# RMG atom-type token -> the token our correction keys use. Deliberately small:
# only the atom kinds RMG actually gives interaction values for.
_NN_TYPES = {"Cs": "Cs", "O2s": "Os", "Os": "Os", "S2s": "Ss", "Ss": "Ss",
             "Cd": "Cd", "CO": "CO"}

_SUB_CLASSES = ("OH", "MeO", "CHO", "vinyl", "CH3", "C2H5")


def _is_halved(entry) -> bool:
    """Whether RMG stored this correction at half value -- stated only in prose."""
    text = f"{entry.get('shortDesc') or ''} {entry.get('longDesc') or ''}".lower()
    return "half value" in text


def nn_key(label):
    """One long-distance-interaction label -> our correction key, or None.

    Skips radical entries (a ``j`` in the label): this scheme has no radicals, and
    a radical correction applied to a closed-shell molecule would be nonsense.
    Skips the zero-valued single-substituent parents too -- they are tree nodes.
    """
    if "j" in label:
        return None

    # aromatic ortho / meta / para
    parts = label.split("_")
    if len(parts) == 3 and parts[0] in ("o", "m", "p"):
        pos, a, b = parts
        if a in _SUB_CLASSES and b in _SUB_CLASSES:
            return f"{pos}_" + "_".join(sorted((a, b)))
        return None

    head, _, ranks = label.partition("-")
    if not ranks or len(ranks) != 2 or any(r not in _RANKS for r in ranks):
        return None

    # split the head into 2- or 3-character type tokens
    tokens = []
    rest = head
    while rest:
        for size in (3, 2):
            if rest[:size] in _NN_TYPES:
                tokens.append(_NN_TYPES[rest[:size]])
                rest = rest[size:]
                break
        else:
            return None

    if len(tokens) == 2:
        pair = sorted(zip(tokens, ranks))
        return "nn13_" + "_".join(f"{t}{r}" for t, r in pair)
    if len(tokens) == 3:
        ends = sorted(zip((tokens[0], tokens[2]), ranks))
        return (
            f"nn14_{tokens[1]}_"
            + "_".join(f"{t}{r}" for t, r in ends)
        )
    return None


def load_corrections(base):
    """Both long-distance-interaction files -> (applied, rejected) correction tables.

    Split on a MEASUREMENT, not on taste. Run
    ``python validation/benson_accuracy.py`` -- it re-measures both families every
    time and prints the two panels this split rests on:

    * The BRANCHING family (``nn13_``/``nn14_``) is Benson's own gauche
      correction, tabulated on the same Benson alkane groups we use, and it helps
      a great deal: mean |Hf| error over four branched alkanes 13.1 -> 3.1 kJ/mol,
      with 2,2,3,3-tetramethylbutane going 25.9 -> 5.8 and 2,2,3-trimethylbutane
      14.8 -> 1.5. Applied.

    * The AROMATIC family (``o_``/``m_``/``p_``) is Ince & Reyniers (2015), who
      regressed their interaction terms TOGETHER WITH their own group values. Those
      corrections do not transfer to RMG's Benson-basis ``Cb`` groups: over eleven
      disubstituted benzenes the mean |Hf| error goes 7.94 -> 9.57 kJ/mol, and
      salicylaldehyde goes 6.0 -> 33.4 because the -27.4 kJ/mol ortho OH/CHO term
      double-counts a hydrogen bond the ``Cb`` values already partly carry.
      Extracted and reported, NOT applied.

    That is the same rule that dropped the aryl-ester carbonyl, seen a third time:
    a correction is only meaningful against the group basis it was fitted with.
    """
    out, rejected, seen, skipped = {}, {}, {}, Counter()
    for fname in ("longDistanceInteraction_cyclic.py",
                  "longDistanceInteraction_noncyclic.py"):
        entries = load(f"{base}/{fname}")
        resolve = resolver(entries)
        for e in entries:
            t = resolve(e)
            if t is None or t.H298 is None:
                skipped["no thermo"] += 1
                continue
            key = nn_key(e["label"])
            if key is None:
                skipped[f"unread label ({fname.split('_')[1][:3]})"] += 1
                continue
            if abs(t.H298) < 1e-9 and abs(t.S298 or 0.0) < 1e-9:
                skipped["zero-valued tree node"] += 1
                continue
            factor = 2.0 if _is_halved(e) else 1.0
            table = rejected if key[:2] in ("o_", "m_", "p_") else out
            if key in table:
                skipped[f"duplicate {key}"] += 1
                continue
            seen[key] = e["label"]
            table[key] = {
                "H298": round(t.H298 * factor, 4),
                "S298": round((t.S298 or 0.0) * factor, 4),
                "Cp": [round(c * factor, 4) for c in (t.Cp or [])],
                "rmg_label": e["label"],
                "source": (
                    ("doubled from RMG's half value; " if factor == 2.0 else "")
                    + (e.get("shortDesc") or "").strip().replace("\n", " ")
                )[:110],
            }
    print(f"\nnon-nearest-neighbour corrections: {len(out)} applied (branching), "
          f"{len(rejected)} extracted but NOT applied (aromatic)")
    for k, v in skipped.most_common(8):
        print(f"   skipped {v:5d}  {k}")
    doubled = [
        k for t in (out, rejected) for k, v in t.items()
        if v["source"].startswith("doubled")
    ]
    print(f"   {len(doubled)} were stored at half value and have been doubled: "
          f"{', '.join(sorted(doubled))}")
    print("   the aromatic family is rejected on a MEASUREMENT -- mean |Hf| error "
          "over 11\n   disubstituted benzenes goes 7.94 -> 9.57 kJ/mol. See "
          "load_corrections' docstring\n   and validation/benson_accuracy.py, "
          "which re-measures it.")
    return out, rejected


def fit_cp(cp):
    """7 tabulated Cp points -> the cubic a + bT + cT^2 + dT^3 the kernel uses."""
    if not cp or len(cp) != len(T_CP):
        return None, None
    X = np.vander(T_CP, 4, increasing=True)
    beta, *_ = np.linalg.lstsq(X, np.array(cp), rcond=None)
    rms = float(np.sqrt(np.mean((X @ beta - np.array(cp)) ** 2)))
    return tuple(float(b) for b in beta), rms


def emit(groups: dict, rings: dict, corrections: dict, rejected: dict) -> None:
    """Write benson_data.py from the parsed tables."""
    lines, cp_bad = [], 0
    for key in sorted(groups):
        rec = groups[key]
        cp, _rms = fit_cp(rec["Cp"])
        if cp is None:
            cp_bad += 1
            cp = (0.0, 0.0, 0.0, 0.0)
        src = rec["source"].replace('"', "'").strip("\\ ") or rec["rmg_label"]
        lines.append(
            f'    "{key}": ({rec["H298"]:.3f}, {rec["S298"]:.3f},\n'
            f'        ({cp[0]:.6g}, {cp[1]:.6g}, {cp[2]:.6g}, {cp[3]:.6g}),\n'
            f'        "{rec["rmg_label"]}: {src[:70]}"),'
        )

    ring_lines = []
    for our, rmg in RING_LABELS.items():
        t = rings.get(rmg)
        if t is None:
            print(f"!! ring {rmg} not in ring.py -- '{our}' will refuse")
            continue
        cp, _ = fit_cp(t.Cp)
        cp = cp or (0.0, 0.0, 0.0, 0.0)
        ring_lines.append(
            f'    "{our}": ({t.H298:.3f}, {t.S298:.3f},\n'
            f'        ({cp[0]:.6g}, {cp[1]:.6g}, {cp[2]:.6g}, {cp[3]:.6g}), "{rmg}"),'
        )

    def correction_lines(table):
        got = []
        for key in sorted(table):
            rec = table[key]
            cp, _ = fit_cp(rec["Cp"])
            cp = cp or (0.0, 0.0, 0.0, 0.0)
            src = rec["source"].replace('"', "'").strip("\\ ") or rec["rmg_label"]
            got.append(
                f'    "{key}": ({rec["H298"]:.3f}, {rec["S298"]:.3f},\n'
                f'        ({cp[0]:.6g}, {cp[1]:.6g}, {cp[2]:.6g}, {cp[3]:.6g}),\n'
                f'        "{rec["rmg_label"]}: {src[:88]}"),'
            )
        return got

    nn_lines = correction_lines(corrections)
    rej_lines = correction_lines(rejected)

    DOC = '''"""Layer 1 -- Benson group additivity values, from the RMG-database.

GENERATED FILE -- do not hand-edit. Run ``tools/build_benson_data.py`` against a
RMG-database clone instead; the derivation is where the reasoning lives, and it
prints a collision report this file cannot carry.

Group VALUES for the scheme implemented in ``benson``. Source: MIT's Reaction
Mechanism Generator database (``input/thermo/groups/``), which is the open
machine-readable form of Benson's tabulation plus later revisions. Every entry
keeps the RMG node label and its source note, so a value that came straight from
Benson is distinguishable from one refitted against CBS-QB3 calculations -- and
several here are the latter.

Format: ``key -> (H298 kJ/mol, S298 J/(mol K), Cp cubic, provenance)``.

## Units: RMG MIXES THEM WITHIN ONE FILE

This is the trap, and it is silent. Entries sourced from Benson are in kcal/mol
and cal/(mol K); the later revisions are in kJ/mol and J/(mol K). ``Cs-CsHHH``
reads -10.2 and ``Cs-OsHHH`` reads -42.9 -- values that agree to within a
revision, printed 4.184 apart. Assuming one unit throughout makes every oxygen
group four times too large, which validates *fine on alkanes* and then destroys
anything with a functional group. The parser reads the declared unit per entry
and raises on one it does not recognise. Everything below is already kJ/mol and
J/(mol K).

## One RMG node per key, chosen by specificity

RMG has ~2700 entries against our ~750 keys: its tree carries second-order nodes
and generic bracketed alternatives that all collapse onto one first-order key.
The build picks the most specific candidate and prints every collision with its
spread. Letting file order decide instead had measured consequences -- a generic
nitrogen node made propylamine 15.8 kJ/mol too negative, and a generic sulfur
node priced every vinyl thioether as a sulfoxide.

## Cp is fitted, not tabulated

RMG gives Cp at 300/400/500/600/800/1000/1500 K. Those seven points are
least-squares fitted here to the ``a + bT + cT^2 + dT^3`` form the rest of the
codebase uses -- the same move as fitting Lee-Kesler to Antoine, so one
functional form reaches the kernel.

## S298 is INTRINSIC entropy

It carries no symmetry correction, and Benson's scheme does not intend it to:
the caller must apply ``-R ln(sigma)`` afterwards. ``benson.symmetry_number``
does that. Omitting it leaves alkanes looking fine and every symmetric molecule
wrong -- benzene by ``R ln 12`` = 20.7 J/(mol K), which is 6 kJ/mol in dGf.

## Ring corrections

Ring strain is not additive over atoms, so it enters per ring, keyed by the
canonical cyclic signature ``benson.ring_key`` derives from the graph -- which is
why 1,3-dioxane and 1,4-dioxane are separate entries rather than one "6-ring with
two oxygens". Anything not named here is REFUSED rather than approximated,
because a missing correction is a silent error of up to 115 kJ/mol
(cyclopropane). RMG has no value for pyridine or any other nitrogen
heteroaromatic, so those refuse.

Aromatic benzene rings correctly need no correction at all -- the ``Cb`` groups
already carry the resonance, which is why six of them reproduce benzene's
formation enthalpy to 0.1 kJ/mol.
"""
    '''

    src = DOC + f'''
from __future__ import annotations

# key -> (H298 kJ/mol, S298 J/(mol K), Cp(T) cubic coefficients, provenance)
GROUP_VALUES: dict[str, tuple[float, float, tuple[float, float, float, float], str]] = {{
{chr(10).join(lines)}
}}


# Per-ring corrections, keyed by the ring identity ``benson`` derives from the
# molecular graph. Same layout as above.
RING_CORRECTIONS: dict[str, tuple[float, float, tuple[float, float, float, float], str]] = {{
{chr(10).join(ring_lines)}
}}


# Non-nearest-neighbour corrections, keyed by the interaction identity
# ``benson.corrections`` derives from the graph. Same layout again.
#
# ``nn13_``/``nn14_`` are Benson's branching (gauche) terms: two substituted
# centres one or two bonds apart, ranked S/T/Q by their single-bonded heavy
# neighbour count. ``o_``/``m_``/``p_`` are the aromatic interactions between two
# benzene-ring substituents.
#
# ENTRIES RMG STORES AT HALF VALUE HAVE BEEN DOUBLED HERE, because RMG's matcher
# counts a symmetric pair twice and ``benson.corrections`` counts each unordered
# pair once. The provenance string says so for every entry it applies to.
#
# Unlike a group or a ring correction, an ABSENT entry means zero rather than a
# refusal -- these refine a complete estimate rather than completing it.
CORRECTIONS: dict[str, tuple[float, float, tuple[float, float, float, float], str]] = {{
{chr(10).join(nn_lines)}
}}


# Aromatic ortho/meta/para interactions -- EXTRACTED AND DELIBERATELY NOT APPLIED.
#
# Ince & Reyniers (AIChE 2015, DOI 10.1002/aic.15008) regressed these interaction
# terms together with THEIR OWN group values, so they do not transfer to the
# Benson-basis ``Cb`` groups above. Measured over eleven disubstituted benzenes
# with reference enthalpies from the ``chemicals`` package, applying them moves the
# mean |Hf| error 7.94 -> 9.57 kJ/mol: it helps o-xylene (3.1 -> 1.1) and
# o-diethylbenzene (9.0 -> 4.8), and wrecks salicylaldehyde (6.0 -> 33.4), because
# the -27.4 kJ/mol ortho OH/CHO term double-counts a hydrogen bond the ``Cb``
# values already partly carry.
#
# Kept here rather than dropped for two reasons: the ortho hydrogen bond is real
# chemistry no group scheme can reach, so this is the right table to reach for once
# there is an aromatic group basis it matches; and
# ``validation/benson_accuracy.py`` re-measures the rejection every run, so it is a
# standing check rather than a one-off verdict. ``benson.corrections`` already
# recognises every interaction here -- only the values are withheld.
AROMATIC_INTERACTIONS: dict[str, tuple[float, float, tuple[float, float, float, float], str]] = {{
{chr(10).join(rej_lines)}
}}
    '''

    open(str(OUT), "w", encoding="utf-8", newline="\n").write(src)
    print(f"\nwrote {len(lines)} groups, {len(ring_lines)} ring corrections, "
          f"{len(nn_lines)} applied and {len(rej_lines)} withheld interaction "
          f"corrections ({cp_bad} groups had no usable Cp)")


def _compose_nitriles(out: dict, nitrile_n: dict) -> None:
    """Reconcile the two nitrile conventions, in the two places they differ.

    **The nitrogen.** We fold it into its carbon; RMG gives it its own group. So a
    ``CN-(X)`` value has to be the sum of RMG's nitrile-carbon group and its
    matching nitrile-nitrogen group. The match is automatic because ``analyse``
    re-roots a nitrogen-centred entry at the carbon, so both land on the same key.
    Acetonitrile: -42.68 (methyl) + 132.39 (carbon) - 15.95 (nitrogen) = 73.8
    against a measured 74.0. Without the nitrogen term it reads 189.8.

    **The neighbour.** Our types distinguish a nitrile carbon (``CN``) from an
    alkyne carbon (``Ct``) as a LIGAND, and RMG's nitrile-specific neighbour
    groups are single-species ridge fits: ``Cs-(CtN3t)HHH`` prices a methyl at
    +72.5 kJ/mol where every other methyl group is about -42.7, with a stated
    uncertainty of +-16. That is the collinearity failure this project already
    documented in its own regression attempt -- the methyl and the nitrile carbon
    are determined by the same single molecule, so the fit split the total
    arbitrarily between them. The reliable value is the generic one, so a
    ``(CN)`` ligand takes its ``(Ct)`` counterpart: to its neighbours a nitrile
    carbon is an alkyne-like carbon, which is what RMG's non-degenerate values
    assume. Our finer type resolution therefore costs no accuracy where RMG
    cannot support it.
    """
    added = 0
    for key, rows in nitrile_n.items():
        rec = out.get(key)
        if rec is None:
            continue
        rows.sort(key=lambda r: (r[0], r[1]))
        _spec, _order, e, t = rows[0]
        rec["H298"] = round(rec["H298"] + t.H298, 4)
        rec["S298"] = round(rec["S298"] + t.S298, 4)
        if rec["Cp"] and t.Cp and len(rec["Cp"]) == len(t.Cp):
            rec["Cp"] = [round(a + b, 4) for a, b in zip(rec["Cp"], t.Cp)]
        rec["rmg_label"] = f"{rec['rmg_label']}+{e['label']}"
        rec["source"] = "nitrile carbon plus its folded nitrogen; " + rec["source"]
        added += 1

    generalised = 0
    for key in [k for k in out if "(CN)" in k and not k.startswith("CN-")]:
        alt = _substitute_ligand(key, "CN", "Ct")
        if alt and alt in out:
            src = out[alt]
            out[key] = dict(
                src,
                rmg_label=src["rmg_label"],
                source="CN ligand taken from the Ct value; " + src["source"],
            )
            generalised += 1
        else:
            del out[key]
            generalised -= 1
    print(f"   nitriles: {added} CN groups absorbed their folded nitrogen, "
          f"{max(generalised, 0)} (CN) ligand keys generalised from (Ct)")


def build(base: str) -> None:
    global BASE
    BASE = base

    entries = load(f"{BASE}/group.py")
    resolve = resolver(entries)
    print(f"{len(entries)} entries in group.py")

    # Collect EVERY candidate per key, then choose. Choosing as we go is what
    # made file order decide chemistry.
    candidates = defaultdict(list)
    nitrile_n = defaultdict(list)
    skipped = Counter()
    for order, e in enumerate(entries):
        t = resolve(e)
        if t is None or t.H298 is None or t.S298 is None:
            skipped["no thermo"] += 1
            continue
        g = analyse(e["group"])
        if g is None:
            skipped["generic, unmapped, or a folded centre"] += 1
            continue
        target = nitrile_n if g.role == "nitrile_n" else candidates
        target[g.key].append((g.specificity, order, e, t))

    out, collisions = {}, []
    for key, rows in candidates.items():
        rows.sort(key=lambda r: (r[0], r[1]))
        if len(rows) > 1:
            spread = max(r[3].H298 for r in rows) - min(r[3].H298 for r in rows)
            collisions.append((spread, key, rows))
        _spec, _order, e, t = rows[0]
        if key in INCOMPATIBLE_SPLIT:
            skipped["incompatible tabulation split"] += 1
            continue
        out[key] = {
            "H298": round(t.H298, 4),               # already kJ/mol
            "S298": round(t.S298, 4),               # already J/(mol K)
            "Cp": [round(c, 4) for c in (t.Cp or [])],
            "rmg_label": e["label"],
            "source": (e.get("shortDesc") or "").strip().replace("\n", " ")[:90],
        }

    print(f"mapped {len(out)} concrete Benson groups")
    for k, v in skipped.most_common(6):
        print(f"   skipped {v:5d}  {k}")

    _compose_nitriles(out, nitrile_n)

    print(f"\nDROPPED for an incompatible tabulation split: "
          f"{len(INCOMPATIBLE_SPLIT)}")
    for key, why in INCOMPATIBLE_SPLIT.items():
        print(f"   {key}: {why}")

    # Report every collision. Silence here is how a wrong number gets in.
    collisions.sort(reverse=True)
    wide = [c for c in collisions if c[0] > 10.0]
    print(f"\n{len(collisions)} keys had more than one RMG candidate; "
          f"{len(wide)} disagree by over 10 kJ/mol. Widest 12, chosen first:")
    for spread, key, rows in wide[:12]:
        print(f"   {key:26s} spread {spread:8.1f} kJ/mol")
        for spec, _o, e, t in rows[:4]:
            print(f"      {'->' if rows[0][2] is e else '  '} "
                  f"{e['label']:32s} extra={spec[0]} generic={spec[1]} "
                  f"H={t.H298:9.2f}")

    print("\nspot checks against Benson's published values:")
    for key in ("C-(C)(H)3", "C-(C)2(H)2", "C-(C)3(H)", "C-(C)4",
                "O-(C)(H)", "CO-(C)2", "CO-(C)(O)", "O-(C)(CO)",
                "Cb-(Cb)2(H)", "C-(H)3(O)", "C-(CO)(H)3",
                "CN-(C)", "C-(CN)(H)3", "C-(H)3(SO)", "SO-(C)2",
                "CO-(C)(Cl)", "C-(C)(H)2(N)", "N-(C)(H)2", "Cd-(Cd)(H)(S)"):
        r = out.get(key)
        print(f"   {key:16s} " + (
            f"H {r['H298']:9.2f} kJ/mol   S {r['S298']:8.2f} J/(mol K)   "
            f"[{r['rmg_label']}] {r['source'][:34]}" if r else "MISSING"))

    rings = {}
    for e in load(f"{BASE}/ring.py"):
        t = e.get("thermo")
        if isinstance(t, ThermoData) and t.H298 is not None:
            rings[e["label"]] = t
    applied, withheld = load_corrections(BASE)
    emit(out, rings, applied, withheld)


OUT = (
    pathlib.Path(__file__).resolve().parent.parent
    / "src" / "chemsim" / "properties" / "benson_data.py"
)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: python tools/build_benson_data.py "
            "<path-to>/RMG-database/input/thermo/groups"
        )
    build(sys.argv[1])

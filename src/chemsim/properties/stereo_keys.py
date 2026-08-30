"""Layer 1 -- reading a property table across a stereochemical spelling.

Every property table in this project is keyed by canonical SMILES, and canonical
SMILES is ISOMERIC -- so a SPELLING decides which record a species reaches. This
module is the one place that is allowed to look past that, and the two limits
below are the whole of why it is safe.

Measured (``validation/stereo_keying.py``): of the 212 corpus
compounds whose canonical spelling carries stereochemistry, 49 resolve to a
DIFFERENT source flat than chiral, and the split is not an accident of two
tables. ONE table carries stereochemistry in its keys -- ``MEASURED_PHYSICAL``,
the one that is GENERATED from the corpus -- and every hand-typed table is
flat: 0 of 82 ideal-gas formation entries, 0 of 58 liquid, 0 of 50 curated
records, 0 of 4 fusion pairs. A human types the simple form; a generator
inherits the corpus's.

⚠⚠ AND IT IS LIVE, WHICH IS THE FINDING THAT MADE IT WORTH FIXING. No
template in this library spells stereochemistry on its product side (0 of 50),
so a rewrite that makes or touches a centre emits the FLAT species -- and the
flat species is not the corpus's. Three catalog steps, run:

  perkin / knoevenagel  ->  O=C(O)C=Cc1ccccc1        Tb 581.9 (Joback)
    the corpus's            O=C(O)/C=C/c1ccccc1      Tb 573.1 (CRC)
  alkene_hydrogenation  ->  CC1CCC(C(C)C)C(O)C1      Tb 530.3 (Joback)
    the corpus's menthol    CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O   Tb 487.1 (CRC)
  homolactic_fermentation -> CC(O)C(=O)O   -- and this one runs the OTHER way:
    the flat spelling reaches the EXPERIMENTAL formation record while the
    corpus's C[C@H](O)C(=O)O misses it and falls to Benson. Neither spelling
    of lactic acid got both halves off the best source available.

The rule below is S6's -- a FALLBACK and never an override -- with two limits
that are the whole of its safety:

  1. IT MAY ONLY CROSS AN AMBIGUITY, NEVER A DIFFERENCE. A query that names no
     stereochemistry may take a record that names some (the unspecified centre
     IS one of them, and no estimator in this project tells them apart -- both
     Joback and Benson return one number for every stereoisomer). A query that
     names some may take a record that names none. Two DIFFERENT specified
     spellings may never share a record: those are two species, which is what
     ``matter/molecule.py`` says and this must not contradict.
  2. THE UNSPECIFIED SIDE MUST BE ANSWERED BY EXACTLY ONE RECORD, and that
     guard FIRES -- ``MEASURED_PHYSICAL`` has 7 skeletons carrying more than
     one stereoisomer. Without it a flat butenedioic acid takes maleic or
     fumaric acid's boiling point depending on dict order, and those are
     **230 K apart**; flat 2-butene picks between cis and trans; and the
     aldohexose skeleton offers glucose, mannose and galactose. A fallback
     that picks one arbitrarily is worse than the estimator it replaces,
     because it is wrong with a measurement's authority.

What it deliberately does NOT do: a chiral query whose skeleton has no flat
record does not take a SIBLING chiral record, even where that sibling is its
own enantiomer and therefore thermochemically identical.

⚠⚠ That refusal costs exactly TWO corpus rows and the rule is right about one
of them, which is the argument in two lines. ``elaidic-acid`` is the trans fatty
acid and the table holds the cis one, oleic acid -- different compounds, 128 K
apart, and refusing is CORRECT. ``pla-unit`` is D-lactic acid and the table holds
the L -- the same scalar thermochemistry, so that record IS its record, and 107 K
of Joback is a real loss. **A rule that took the sibling would be right once and
wrong once.** Separating them means inverting every centre and comparing, which
is cheap to state and easy to get wrong on a diastereomer, and it is worth
exactly one row. Priced rather than guessed at:
``validation/stereo_keying.py`` panel 6.
"""

from __future__ import annotations

from chemsim.matter import stereo_free_smiles

FALLBACK_NOTE = "matched on the stereochemistry-free spelling"


def fallback_note(query: str, key: str | None) -> str:
    """The provenance suffix a value earns by arriving through the fallback.

    A number that came from a record spelled differently from the species asking
    for it has to say so: this project's whole discipline is that a caller can
    tell where a value came from, and "the same compound, spelled without its
    stereochemistry" is a real qualification on a measurement.
    """
    return "" if key is None or key == query else f" ({FALLBACK_NOTE}: {key})"


# The three characters that can carry stereochemistry in a SMILES. A CANONICAL
# spelling with none of them is already stereochemistry-free, and canonical
# SMILES is idempotent, so its bare form is itself -- which is worth a special
# case rather than an RDKit parse: this fast path skips ~1090 of the 1239
# parses ``MEASURED_PHYSICAL`` would otherwise cost at import, and with them the
# RDKit sanitizer warnings that re-parsing ``[H][H]`` prints to stderr.
# ⚠ It is valid ONLY for canonical input, which is what these tables are keyed
# by; ``stereo_free_smiles`` itself takes any spelling and always parses.
_STEREO_CHARS = "@/\\"


def _bare(canonical: str) -> str:
    if not any(ch in canonical for ch in _STEREO_CHARS):
        return canonical
    return stereo_free_smiles(canonical)


class StereoFallback:
    """A canonical-SMILES table that answers across an UNSPECIFIED centre.

    Wraps a dict keyed by canonical SMILES. ``key(smi)`` returns the key to
    READ -- the exact one where it exists, otherwise the stereochemistry-free
    counterpart under the two rules in this module's docstring, otherwise None.
    It returns the key rather than the value so that a caller can see whether it
    got the spelling it asked for: ``fallback_note`` turns that into the
    provenance suffix, because a value that arrived through a fallback has to
    say so.
    """

    __slots__ = ("_table", "_unique", "_memo", "_enabled")

    def __init__(self, table: dict, enabled: bool = True):
        # ``enabled=False`` is exact-key-only -- the behaviour before this
        # existed, kept switchable for the same reason ``benson=False`` and
        # ``measured_physical=False`` are: so the difference this makes can be
        # MEASURED rather than only described. ``validation/stereo_keying.py``
        # panel 5 runs both.
        self._enabled = enabled
        self._table = dict(table)
        # A miss costs an RDKit parse, and the provider asks the same tables
        # about the same species repeatedly while assembling one record.
        self._memo: dict[str, str | None] = {}
        bare_to_keys: dict[str, list[str]] = {}
        for k in self._table:
            bare_to_keys.setdefault(_bare(k), []).append(k)
        # Only skeletons with exactly ONE record may answer an unspecified
        # query; the rest are ambiguous and refuse. A skeleton whose one record
        # IS the flat spelling never reaches here -- that is an exact hit.
        self._unique = {
            bare: keys[0] for bare, keys in bare_to_keys.items() if len(keys) == 1
        }

    def __contains__(self, smi: str) -> bool:
        return self.key(smi) is not None

    def __iter__(self):
        return iter(self._table)

    def __len__(self) -> int:
        return len(self._table)

    def key(self, smi: str) -> str | None:
        if smi in self._table:
            return smi
        if not self._enabled:
            return None
        if smi in self._memo:
            return self._memo[smi]
        resolved = self._resolve(smi)
        self._memo[smi] = resolved
        return resolved

    def _resolve(self, smi: str) -> str | None:
        bare = _bare(smi)
        if bare == smi:
            # The query names no stereochemistry: an ambiguity, which exactly
            # one record may resolve.
            return self._unique.get(bare)
        # The query names some. Only the flat record may serve it -- never a
        # differently-specified sibling.
        return bare if bare in self._table else None

    def get(self, smi: str, default=None):
        k = self.key(smi)
        return self._table[k] if k is not None else default

"""Validation harness: how good is Benson group additivity, against Joback?

Run this before and after any change to ``properties/benson.py``,
``benson_data.py`` or ``tools/build_benson_data.py``. It is the measurement the
Benson work is judged on, and the numbers it prints are quoted in HANDOFF.md --
so the metric must not drift. Specifically:

    median |dGf error| over the species BOTH estimators can price.

Restricting to the common subset is the point. Benson refuses some species and
Joback refuses others, so a median taken over each estimator's own coverage
compares two different sets of molecules and can improve by dropping the hard
ones. The panel therefore reports the paired median first, then each estimator's
coverage separately, then what each one refuses and why.

The reference is ``formation_data.IDEAL_GAS_FORMATION`` -- 82 measured ideal-gas
species, each already cross-checked two ways in that module. Both estimators are
asked for the SAME quantity in the SAME standard state, so nothing in the
comparison depends on the standard-state chain, the activity model or the
network.

Reading the output:

  * ``paired median`` is the headline. Lower is better, and the Benson column
    must stay below the Joback one -- that is the entire justification for
    Benson sitting above Joback in ``ThermochemistryProvider``.
  * ``refused`` is the honest cost of accuracy. Benson refuses rather than
    omitting a group value or a ring correction, so a refusal is a *feature*
    (those species keep Joback) but a growing count is a regression in reach.
  * The tail lists every refusal with its reason, so a new gap names itself
    instead of hiding inside an aggregate.

## The second panel, and why it has to exist

The 82-species set cannot measure the non-nearest-neighbour corrections. Measured,
not assumed: NONE of the 82 has two adjacent branched sp3 centres, and none has
two halogens on adjacent carbons, so the whole branching family is invisible to
it -- only the three xylenes exercise anything at all. A brief that calls the
branching corrections "the main reason branched species carry avoidable error" is
therefore untestable on this set, in either direction.

So ``interaction_panel`` uses a second, small set chosen BECAUSE it exercises the
corrections, with reference enthalpies taken from the ``chemicals`` package (the
same CRC/NIST compilation the curated tables were built from) rather than from
recall. It reports each species with and without the correction, so the term earns
its place per case instead of on aggregate faith.
"""

from __future__ import annotations

import statistics

from chemsim.matter import Molecule
from chemsim.properties import benson
from chemsim.properties.formation_data import IDEAL_GAS_FORMATION
from chemsim.properties.joback import estimate as joback_estimate


def _joback_gf(mol: Molecule) -> float | None:
    try:
        j = joback_estimate(mol)
    except Exception:                                    # noqa: BLE001
        return None
    return j.Gf


def _benson_gf(mol: Molecule) -> tuple[float | None, str]:
    try:
        return benson.estimate(mol).Gf, ""
    except Exception as exc:                             # noqa: BLE001
        return None, str(exc)


# Species chosen because they exercise a non-nearest-neighbour correction.
# Reference Hf(ideal gas, 298 K) is pulled from ``chemicals`` at run time by CAS,
# so no number here is transcribed and none can rot.
BRANCHING_SET = [
    # (name, SMILES, CAS)
    ("2,3-dimethylbutane",        "CC(C)C(C)C",       "79-29-8"),
    ("2,2,3,3-tetramethylbutane", "CC(C)(C)C(C)(C)C", "594-82-1"),
    ("2,2,3-trimethylbutane",     "CC(C)C(C)(C)C",    "464-06-2"),
    ("2,2-dimethylbutane",        "CCC(C)(C)C",       "75-83-2"),
    ("2,2,4-trimethylpentane",    "CC(C)CC(C)(C)C",   "540-84-1"),
    ("n-hexane (control)",        "CCCCCC",           "110-54-3"),
]

AROMATIC_SET = [
    ("o-xylene",              "Cc1ccccc1C",       "95-47-6"),
    ("m-xylene",              "Cc1cccc(C)c1",     "108-38-3"),
    ("p-xylene",              "Cc1ccc(C)cc1",     "106-42-3"),
    ("catechol",              "Oc1ccccc1O",       "120-80-9"),
    ("resorcinol",            "Oc1cccc(O)c1",     "108-46-3"),
    ("hydroquinone",          "Oc1ccc(O)cc1",     "123-31-9"),
    ("guaiacol",              "COc1ccccc1O",      "90-05-1"),
    ("veratrole",             "COc1ccccc1OC",     "91-16-7"),
    ("1,4-dimethoxybenzene",  "COc1ccc(OC)cc1",   "150-78-7"),
    ("4-methoxyphenol",       "COc1ccc(O)cc1",    "150-76-5"),
    ("salicylaldehyde",       "O=Cc1ccccc1O",     "90-02-8"),
    ("4-hydroxybenzaldehyde", "O=Cc1ccc(O)cc1",   "123-08-0"),
    ("o-diethylbenzene",      "CCc1ccccc1CC",     "135-01-3"),
    ("2-methylstyrene",       "C=Cc1ccccc1C",     "611-15-4"),
    ("styrene (control)",     "C=Cc1ccccc1",      "100-42-5"),
]


def _panel(title, species, table, note):
    """Per-species first-order vs corrected error, against `chemicals` references."""
    from chemicals import Hfg

    print()
    print("=" * 78)
    print(title)
    print("=" * 78)
    print(f"  {'species':29}{'ref Hf':>9}{'1st order':>11}{'+corr':>9}"
          f"{'err':>7}{'->':>4}{'err':>7}   interaction")

    before, after = [], []
    for name, smiles, cas in species:
        ref = Hfg(cas)
        if ref is None:
            print(f"  {name:29}no reference Hf(g) in `chemicals`")
            continue
        ref /= 1000.0
        try:
            plain = benson.estimate(smiles, nn=False)
        except Exception as exc:                         # noqa: BLE001
            print(f"  {name:29}refused: {str(exc)[:40]}")
            continue
        terms = benson.corrections(smiles, table)
        dH = sum(n * table[k][0] for k, n in terms.items())
        corrected = plain.Hf + dH
        e0, e1 = abs(plain.Hf - ref), abs(corrected - ref)
        before.append(e0)
        after.append(e1)
        print(f"  {name:29}{ref:9.1f}{plain.Hf:11.1f}{corrected:9.1f}"
              f"{e0:7.1f}{'->':>4}{e1:7.1f}   {', '.join(terms) or '-'}")

    if before:
        print()
        print(f"  mean |Hf error|    first order {statistics.fmean(before):6.2f}"
              f"  ->  corrected {statistics.fmean(after):6.2f} kJ/mol")
        print(f"  median             first order {statistics.median(before):6.2f}"
              f"  ->  corrected {statistics.median(after):6.2f} kJ/mol")
        verdict = "HELPS" if statistics.fmean(after) < statistics.fmean(before) else "HURTS"
        print(f"  verdict: this family {verdict} on this set.")
    print()
    for line in note:
        print(f"  {line}")


def interaction_panel() -> None:
    """Re-measure both correction families: the applied one and the withheld one.

    Both panels run every time on purpose. The decision to apply the branching
    family and withhold the aromatic one rests on these numbers, so it is a
    standing check rather than a verdict recorded once in a comment -- and if a
    later change to the group table makes the aromatic family start helping, this
    is what will say so.
    """
    try:
        from chemsim.properties.benson_data import (
            AROMATIC_INTERACTIONS,
            CORRECTIONS,
        )
    except ImportError:
        print("\n(benson_data has no correction tables; panels skipped)")
        return
    try:
        import chemicals                                  # noqa: F401
    except ImportError:
        print("\n(chemicals not installed; interaction panels skipped)")
        return

    _panel(
        "APPLIED: Benson's branching (gauche) corrections",
        BRANCHING_SET,
        CORRECTIONS,
        [
            "These are Benson's own values on the same alkane groups we use, and",
            "they are the largest single accuracy gain available to this scheme.",
            "n-hexane is the control: no adjacent branched pair, so no term fires.",
        ],
    )
    _panel(
        "WITHHELD: Ince & Reyniers' aromatic ortho/meta/para interactions",
        AROMATIC_SET,
        AROMATIC_INTERACTIONS,
        [
            "Extracted from RMG but NOT in CORRECTIONS. They were regressed",
            "together with their authors' own group values and do not transfer to",
            "the Benson-basis Cb groups: salicylaldehyde's -27.4 kJ/mol ortho",
            "OH/CHO term double-counts a hydrogen bond the Cb values already",
            "partly carry. Real chemistry, wrong basis -- the same rule that",
            "dropped the aryl-ester carbonyl. Adopting them needs an aromatic",
            "group basis they match, not a threshold change here.",
        ],
    )


def main() -> None:
    rows = []
    for smi, (_Hf, Gf) in IDEAL_GAS_FORMATION.items():
        mol = Molecule.from_smiles(smi)
        b, why = _benson_gf(mol)
        rows.append((smi, Gf, _joback_gf(mol), b, why))

    both = [(s, r, j, b) for s, r, j, b, _ in rows if j is not None and b is not None]
    j_only = [(s, r, j) for s, r, j, b, _ in rows if j is not None and b is None]
    b_only = [(s, r, b) for s, r, j, b, _ in rows if j is None and b is not None]
    neither = [s for s, _r, j, b, _ in rows if j is None and b is None]

    print("=" * 78)
    print("Benson vs Joback -- dGf(ideal gas, 298 K) against curated measured data")
    print("=" * 78)
    print(f"  reference set                     {len(rows):5d} species")
    print(f"  both estimators can price         {len(both):5d}")
    print(f"  Joback only (Benson refuses)      {len(j_only):5d}")
    print(f"  Benson only (Joback refuses)      {len(b_only):5d}")
    print(f"  neither                           {len(neither):5d}")

    if both:
        je = [abs(j - r) for _s, r, j, _b in both]
        be = [abs(b - r) for _s, r, _j, b in both]
        print()
        print(f"  {'':34}{'Benson':>10}{'Joback':>10}")
        print(f"  paired median |dGf error|, kJ/mol {statistics.median(be):10.2f}"
              f"{statistics.median(je):10.2f}   <-- THE metric")
        print(f"  paired mean                       {statistics.fmean(be):10.2f}"
              f"{statistics.fmean(je):10.2f}")
        print(f"  paired worst                      {max(be):10.2f}{max(je):10.2f}")
        wins = sum(1 for (_s, r, j, b) in both if abs(b - r) < abs(j - r))
        print(f"  Benson closer on                  {wins:10d}{len(both) - wins:10d}"
              "   species")

    print()
    print("  biggest Benson errors on the paired set (kJ/mol)")
    for smi, r, j, b in sorted(both, key=lambda t: -abs(t[3] - t[1]))[:10]:
        print(f"    {smi:26s} ref {r:9.1f}   benson {b:9.1f} ({b - r:+7.1f})"
              f"   joback {j:9.1f} ({j - r:+7.1f})")

    print()
    print("  where Benson wins most (kJ/mol of error removed)")
    gains = sorted(both, key=lambda t: -(abs(t[2] - t[1]) - abs(t[3] - t[1])))
    for smi, r, j, b in gains[:8]:
        print(f"    {smi:26s} joback {abs(j - r):8.1f} -> benson {abs(b - r):8.1f}")

    print()
    print("=" * 78)
    print("REFUSALS -- what Benson declines, and why. These keep Joback's estimate.")
    print("=" * 78)
    for smi, _r, j, b, why in rows:
        if b is not None:
            continue
        tag = "joback covers it" if j is not None else "NEITHER -- no data at all"
        print(f"  {smi:26s} [{tag}]")
        print(f"      {why[:150]}")
    if all(b is not None for _s, _r, _j, b, _w in rows):
        print("  (none)")

    interaction_panel()


if __name__ == "__main__":
    main()

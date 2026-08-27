"""Standing audit: how many catalog species have a MEASURED boiling point that
this engine is not using, how wrong the estimate it uses instead is, and which
of them anything can actually reach.

Run: ``python validation/boiling_points.py``            (~2 min)
     ``python validation/boiling_points.py --examples`` (~5 min; runs the
                                                         cheap example set)

## Why this file exists

``properties/physical_data.py`` is GENERATED, and a generated file reads as
systematic. What it is generated FROM is ``CANDIDATES`` in
``tools/build_physical_data.py`` -- a HAND-TYPED list of names. Anything not on
that list falls to Joback, whether or not ``chemicals`` holds several
experimental sources for it. There is no refusal and no warning, and the
coverage audit cannot see it, **because the record RESOLVES**: a species priced
by Joback answers every question put to it, confidently, in the wrong place.

⚠⚠ **A GENERATED FILE IS ONLY AS SYSTEMATIC AS ITS INPUT LIST.** That is the
whole finding, and this file is the instrument that makes it a number instead of
a sentence.

## Two numbers, and the second is the headline

**322** catalog species have a measured boiling point this engine is not using.
**213** of them would actually change the resolved record if it were installed;
the other 109 are curated at tier 1 already, or resolve identically, and quoting
322 would be this project's own recurring mistake told about itself. Panel 1
prints both and says which is which.

## Panel 5 is the one to read first

The gap is not exotic. Measured here, all of them priced by JOBACK: **acetylene
14.60% high (216.60 K against 189.00), methanol 6.80% low (314.66 against
337.63), ethanol 3.99% low (337.54 against 351.57), diethyl ether 1.93% low,
n-hexane 1.46% low** -- the bench solvents nearly every example in this project
runs on, in a project whose flagship rig is a distillation column. A boiling
point is not a decoration in an engine with a still in it.

⚠ And the panel is written so that CLOSING the gap makes it say so: when no
bench species is left absent it prints the list under "NONE", so the panel
records the fix rather than going quietly empty.

## The trap this instrument fell into first, demonstrated live in panel 3

``chemicals.CAS_from_any("C")`` returns **CARBON**, not methane: a bare SMILES is
read as a FORMULA, and a single-letter SMILES is also an element symbol. The
first sweep of this gap therefore listed borane boiling at 2823 K and methane at
4273. Every lookup here goes through ``"smiles=" + smi``, and panel 3 asserts the
difference rather than describing it, so the fix cannot be undone silently.

## What "measured" means here, and why this file does not decide it

Nothing. The tier rules -- which ``chemicals`` source names count as
experimental, which as an unauditable compilation, and which are group
contribution wearing a database's name -- live in ``tools/build_physical_data``
and are imported. An audit that reimplemented them could agree with the builder
while both were wrong, which is the failure mode ``AUDIT THE INSTRUMENT BEFORE
THE FINDINGS`` exists for.

## What this audit deliberately does NOT do

It does not decide readiness. ``catalog_coverage.py`` owns template-ready /
species-ready / BOTH, and a second implementation of that here would agree with
the first until the day it quietly did not. Exposure is reported as the plain
thing this file can compute without duplicating anything: **how many catalog
route steps name the species**, and -- under ``--examples`` -- which species the
example set actually asks the provider to price.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))
sys.path.insert(0, os.path.join(_ROOT, "validation"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import catalog as cat  # noqa: E402
from build_physical_data import _measured  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.properties import ThermochemistryProvider  # noqa: E402
from chemsim.properties.physical_data import MEASURED_PHYSICAL  # noqa: E402

# The bench set: the species this project's own examples charge. Named here
# because "the gap is 300 obscure compounds" and "the gap is the solvent in the
# flask" are different findings, and only the second one changes what anybody
# does about it.
BENCH = {
    "CCO": "ethanol", "CO": "methanol", "CC(=O)O": "acetic acid",
    "CC=O": "acetaldehyde", "CCOCC": "diethyl ether", "CCCCCC": "n-hexane",
    "C#C": "acetylene", "CI": "iodomethane", "CCC(=O)O": "propanoic acid",
}


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def census(compounds) -> tuple[list[dict], dict[str, int]]:
    """Walk the corpus once. Returns the absent-with-a-measurement rows."""
    from chemicals import CAS_from_any, Tb, Tb_methods

    thermo = ThermochemistryProvider()
    in_table = {Molecule.from_smiles(s).smiles for s in MEASURED_PHYSICAL}

    counts = dict(graph=0, in_table=0, no_cas=0, no_source=0, absent=0)
    rows: list[dict] = []
    seen: set[str] = set()
    for cid, c in sorted(compounds.items()):
        try:
            mol = Molecule.from_smiles(c.smiles)
        except Exception:                                     # noqa: BLE001
            continue
        if mol is None:
            continue
        key = mol.smiles
        if key in seen:
            continue
        seen.add(key)
        counts["graph"] += 1
        if key in in_table:
            counts["in_table"] += 1
            continue
        # "smiles=" IS LOAD-BEARING. See panel 3.
        try:
            cas = CAS_from_any("smiles=" + key)
        except Exception:                                     # noqa: BLE001
            counts["no_cas"] += 1
            continue
        got = _measured(Tb, Tb_methods, cas)
        if got is None:
            counts["no_source"] += 1
            continue
        counts["absent"] += 1
        try:
            td = thermo.get(mol)
            tb_now, src = td.Tb, (td.physical_source or td.source)
        except Exception as exc:                              # noqa: BLE001
            tb_now, src = None, "REFUSED " + type(exc).__name__
        rows.append(dict(id=cid, name=c.name, smiles=key, cas=cas,
                         tb=got[0], method=got[1], tier=got[2],
                         tb_now=tb_now, source=src))
    return rows, counts


def would_move(rows) -> int:
    """Mark each row with whether installing it would CHANGE the answer.

    ⚠ THE COUNT OF ABSENT SPECIES IS NOT THE COUNT OF WRONG ONES, and the
    difference is not small. Water, oxygen and hydrogen chloride are all absent
    from ``MEASURED_PHYSICAL`` and all irrelevant to it: they are curated at
    tier 1 in ``thermochemistry._CURATED_RAW``, which short-circuits the whole
    resolution. Reporting 322 as though it were 322 wrong numbers would be
    exactly the kind of headline this project keeps catching itself writing.

    So this installs every absent species into a SECOND provider, resolves each
    one twice, and counts the records that actually differ. Returns the number
    that move; the rows gain a ``moves`` key.
    """
    from chemsim.properties.physical_data import (
        MEASURED_PHYSICAL as TABLE, Measured, MeasuredPhysical,
    )
    from chemicals import (
        Hfus, Hfus_methods, Pc, Pc_methods, Tb, Tb_methods, Tc, Tc_methods,
        Tm, Tm_methods, Vc, Vc_methods,
    )

    def half(mol, provider):
        try:
            t = provider.get(mol)
        except Exception as exc:                              # noqa: BLE001
            return ("REFUSED", type(exc).__name__)
        return (t.Tb, t.Tc, t.Pc, t.Vc, t.Hvap, t.Tm, t.Hfus, t.physical_source)

    before_p = ThermochemistryProvider()
    before = {r["smiles"]: half(Molecule.from_smiles(r["smiles"]), before_p)
              for r in rows}

    def m(t, scale=1.0):
        return None if t is None else Measured(float(t[0]) * scale, t[1], t[2])

    saved = dict(TABLE)
    try:
        for r in rows:
            cas = r["cas"]
            hf = _measured(lambda _c, method: Hfus(CASRN=_c, method=method),
                           Hfus_methods, cas)
            tc = _measured(Tc, Tc_methods, cas, best_tier_only=True)
            pc = _measured(Pc, Pc_methods, cas, best_tier_only=True)
            vc = _measured(Vc, Vc_methods, cas, best_tier_only=True)
            if (tc is None) != (pc is None):
                tc = pc = None          # the acentric factor needs one basis
            TABLE[r["smiles"]] = MeasuredPhysical(
                Tb=m(_measured(Tb, Tb_methods, cas)),
                Tm=m(_measured(Tm, Tm_methods, cas)),
                Hfus=m(hf, 1e-3), Tc=m(tc), Pc=m(pc, 1e-5), Vc=m(vc, 1e6),
            )
        after_p = ThermochemistryProvider()
        for r in rows:
            mol = Molecule.from_smiles(r["smiles"])
            r["moves"] = half(mol, after_p) != before[r["smiles"]]
    finally:
        TABLE.clear()
        TABLE.update(saved)
    return sum(1 for r in rows if r["moves"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", action="store_true",
                    help="also run the cheap example set and report which of "
                         "these species it actually prices (~3 min more)")
    args = ap.parse_args()

    t0 = time.time()
    compounds = cat.load_compounds()
    steps = cat.load_steps()
    rows, counts = census(compounds)
    n_moves = would_move(rows)

    rule("1. THE CENSUS -- what the corpus holds against what the table holds")
    print(f"  catalog compounds                        {len(compounds):5d}")
    print(f"  ...with a molecular graph                {counts['graph']:5d}")
    print(f"  already in MEASURED_PHYSICAL             {counts['in_table']:5d}"
          f"   <- the hand-typed list")
    print(f"  no CAS resolvable from the graph         {counts['no_cas']:5d}")
    print(f"  CAS, but no non-estimated Tb anywhere    {counts['no_source']:5d}")
    print(f"  ** measured Tb available, NOT in table   {counts['absent']:5d} **")
    tiers = {}
    for r in rows:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    print("  of those, by source tier: " + ", ".join(
        f"{k} {v}" for k, v in sorted(tiers.items())))
    print(f"  ** and would CHANGE the resolved record  {n_moves:5d} **")
    print(f"     (the other {counts['absent'] - n_moves} are already curated at "
          f"tier 1, or resolve identically)")
    print()
    print("  The second number is the honest one. Water, oxygen and hydrogen")
    print("  chloride are all 'absent from the table' and all irrelevant to")
    print("  it: they are curated in `_CURATED_RAW`, which short-circuits the")
    print("  whole resolution. A headline of the first number would be this")
    print("  project's own recurring mistake, told about itself.")
    print()
    print("  Every one of these is a species for which a measurement exists,")
    print("  is already installed on this machine, and is not being used --")
    print("  not because it was weighed and rejected, but because nobody typed")
    print("  its name into a list.")

    rule("2. WHAT THE ENGINE PRICES INSTEAD, AND HOW WRONG IT IS")
    priced = [r for r in rows if r["tb_now"] is not None]
    errs = sorted(((abs(r["tb_now"] - r["tb"]) / r["tb"] * 100.0, r)
                   for r in priced), key=lambda t: -t[0])
    print(f"  of the {len(rows)} absent, price a Tb today     {len(priced):5d}")
    print(f"  ...and carry no boiling point at all      {len(rows)-len(priced):5d}")
    if errs:
        vals = [e for e, _ in errs]
        print("  mean / median / worst |error|   %6.2f%% / %5.2f%% / %5.2f%%"
              % (statistics.mean(vals), statistics.median(vals), vals[0]))
        print("  over  2%% / 5%% / 10%% / 20%%       %5d / %4d / %4d / %4d" % tuple(
            sum(1 for v in vals if v > t) for t in (2, 5, 10, 20)))
        print()
        print("  worst 12:")
        print("    %7s  %-28s %10s %10s  %s"
              % ("err", "species", "engine", "measured", "source"))
        for e, r in errs[:12]:
            print("    %6.2f%%  %-28s %10.2f %10.2f  %s"
                  % (e, r["name"][:28], r["tb_now"], r["tb"], r["method"]))
        print()
        print("  A mean of a few per cent is not the finding. The finding is")
        print("  that the error is UNSIGNED and UNBOUNDED: nothing in the")
        print("  engine knows which of these numbers is the 3% one and which")
        print("  is the 85% one, because all of them resolve.")

    rule("3. THE INSTRUMENT'S OWN TRAP, DEMONSTRATED RATHER THAN DESCRIBED")
    from chemicals import CAS_from_any, Tb
    bare = CAS_from_any("C")
    smi = CAS_from_any("smiles=C")

    def _tb(cas):
        try:
            v = Tb(cas)
        except Exception:                                     # noqa: BLE001
            return float("nan")
        return float("nan") if v is None else float(v)

    print("  CAS_from_any('C')          -> %-12s  Tb %8.2f K" % (bare, _tb(bare)))
    print("  CAS_from_any('smiles=C')   -> %-12s  Tb %8.2f K" % (smi, _tb(smi)))
    assert bare != smi, "the formula/SMILES ambiguity has gone away -- reread this"
    print()
    print("  A bare SMILES is read as a FORMULA, and a single-letter SMILES is")
    print("  also an element symbol. The first sweep of this gap counted 360")
    print("  and had methane boiling at 4273 K, because it had asked about")
    print("  carbon. Every lookup in this file goes through 'smiles=' + smi.")

    rule("4. EXPOSURE -- how much of the corpus names these species")
    named: dict[str, int] = {}
    for st in steps:
        for sp in set(st.reactants) | set(st.products):
            c = compounds.get(sp)
            if c is None:
                continue
            try:
                k = Molecule.from_smiles(c.smiles).smiles
            except Exception:                                 # noqa: BLE001
                continue
            named[k] = named.get(k, 0) + 1
    by_use = sorted(((named.get(r["smiles"], 0), r) for r in rows),
                    key=lambda t: -t[0])
    reached = sum(1 for n, _ in by_use if n)
    print(f"  absent species named by at least one route step   {reached:5d}"
          f"  of {len(rows)}")
    print(f"  named by five or more steps                       "
          f"{sum(1 for n, _ in by_use if n >= 5):5d}")
    print()
    print("  NOTE: this is NOT a readiness claim. `catalog_coverage.py` owns")
    print("  template-ready / species-ready / BOTH, and reimplementing that")
    print("  here would give two answers that agree until they do not.")
    print()
    print("  the 16 most-named ('*' = installing it would change the answer):")
    for n, r in by_use[:16]:
        err = ("%6.2f%%" % (abs(r["tb_now"] - r["tb"]) / r["tb"] * 100.0)
               if r["tb_now"] is not None else "   n/a")
        print("    %3d steps %s %-28s %s  meas %8.2f K"
              % (n, "*" if r["moves"] else " ", r["name"][:28], err, r["tb"]))
    print()
    print(f"  of the {reached} named by a route step, {sum(1 for n, r in by_use if n and r['moves'])}"
          " would change the answer.")

    rule("5. THE BENCH SET -- and this is the panel that changes what to do")
    idx = {r["smiles"]: r for r in rows}
    hits = [(BENCH[s], idx[s]) for s in BENCH if s in idx]
    if not hits:
        print("  NONE. Every bench solvent below now carries a measured record,")
        print("  which is what this panel exists to confirm:")
        for s, nm in sorted(BENCH.items(), key=lambda kv: kv[1]):
            print("    %-16s %s" % (nm, s))
    else:
        print("  %-16s %10s %10s %8s  %s"
              % ("species", "engine", "measured", "error", "what prices it now"))
        for nm, r in sorted(hits):
            e = (abs(r["tb_now"] - r["tb"]) / r["tb"] * 100.0
                 if r["tb_now"] is not None else float("nan"))
            print("  %-16s %10.2f %10.2f %7.2f%%  %s"
                  % (nm, r["tb_now"] or float("nan"), r["tb"], e,
                     r["source"][:34]))
        print()
        print("  These are not exotic compounds from the far end of the")
        print("  catalog. They are what the examples charge into the flask.")

    if args.examples:
        rule("6. LIVE EXPOSURE -- which of them the example set actually prices")
        import tolerance_audit as ta
        seen: dict[str, set[str]] = {}
        orig = ThermochemistryProvider.get
        current: set[str] = set()

        def patched(self, mol, *a, **kw):
            try:
                current.add(mol.smiles)
            except Exception:                                 # noqa: BLE001
                pass
            return orig(self, mol, *a, **kw)

        ThermochemistryProvider.get = patched
        try:
            for name in ta.CHEAP:
                current.clear()
                ta.run_example(name)
                seen[name] = set(current)
        finally:
            ThermochemistryProvider.get = orig
        absent = {r["smiles"] for r in rows}
        total = set()
        for name in ta.CHEAP:
            hit = sorted(seen[name] & absent)
            total |= set(hit)
            print("  %-32s %3d priced, %2d of them absent from the table"
                  % (name, len(seen[name]), len(hit)))
        print()
        print(f"  distinct absent species the example set prices: {len(total)}")
        for s in sorted(total):
            print("    %-28s %s" % (idx[s]["name"][:28], s))

    rule("VERDICT")
    print(f"  {counts['absent']} catalog species have a measured boiling point "
          f"this engine is not using.")
    if errs:
        print(f"  {len(priced)} of them price one anyway, mean |error| "
              f"{statistics.mean([e for e, _ in errs]):.2f}%, worst "
              f"{errs[0][0]:.2f}%.")
    print(f"  {len(hits)} of the {len(BENCH)} named bench species are among them.")
    print(f"  {n_moves} of the {counts['absent']} would actually change a "
          f"resolved record; the rest are curated at tier 1.")
    print()
    print(f"  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

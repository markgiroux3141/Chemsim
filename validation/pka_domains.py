"""T5 -- what the 33-row pKa table still bounds, counted class by class.

T14 asked this question for ONE acid class and the answer was a rule with a
stated domain rather than a dozen hand-typed rows
(``validation/fatty_acid_pka.py``, and ``properties/carboxylic_pka.py`` is what
it produced). T18 then built the hook that rule hangs on:
``ThermochemistryProvider`` takes an ``ion_fallback`` consulted after the
curated table misses, and the carboxylic plateau is its ONE caller. This audit
is the same measurement over the OTHER classes, and it is deliberately done
before any pKa is written: an estimator for an unmeasured quantity is what
``element_data`` exists to refuse, so the number has to argue for the rule
first.

T13 raised the stakes. An unpriceable species used to ride along inside a
network and fail later at ``to_arrays``; now ``build_network`` drops the
rewrite that made it (with a notice naming it) or refuses the charge outright.
So the pKa table no longer bounds only what a flask can INTEGRATE -- it bounds
what the engine can BUILD, and every ion below that this table cannot reach is
a graph edge the player never gets.

THE CLASSES ARE THE TEMPLATE ROWS, NOT A LIST OF FUNCTIONAL GROUPS
------------------------------------------------------------------
What the engine can ionise is exactly what ``dissociation_templates`` can
rewrite, so this sweep fires those rows rather than re-typing their SMARTS as
predicates -- the mistake T18 corrected in the other direction when it moved
``carboxyl_sites`` out of the audit and into the engine. Seven rows carry a
substrate slot (``water_autoionization`` has none and is not a class); the
partner slot takes water for a dissociation and hydronium for a protonation,
read off the row rather than declared.

Three panels:

  0. THE TABLE, BUCKETED BY CLASS. Each curated pair is assigned to the class
     whose row actually interconverts its two halves, and the pKa spread inside
     each class is printed. That spread is the rule test: the carboxylic
     plateau is supportable because five unbranched rows from C3 up span 0.15
     units. A class whose curated rows span three units supports no single
     value, and the honest output for it is a refusal.

  1. THE CORPUS. All 1,583 catalog compounds, fragment by fragment, driven to a
     fixpoint under the seven rows -- so a second dissociation is counted, which
     is where the salicylate dianion and the phosphate trianion live. Every ion
     the sweep makes is asked of the live provider: priced by a curated row,
     priced by a rule and saying so, or refused.

  2. THE SHELF. The same fixpoint over the species of the shelf's chargeable
     rows. A lower bound and a different question: the corpus is what coverage
     is SCORED against, the shelf is what a player can actually pour. It does
     NOT expand a network, so an acid a flask MAKES (an ester hydrolysed, an
     alcohol oxidised twice) is invisible here; ``fatty_acid_pka.py`` pays 36
     flasks for that and finds the two sets nearly disjoint.

A MISSING ION HAS TWO POSSIBLE GAPS AND ONLY ONE IS A pKa
---------------------------------------------------------
``ion_thermochemistry`` skips any pair it cannot anchor, so an ion can be
missing because nothing measured its acidity, or because the neutral half it
would hang off has no thermochemistry of its own. The first is a row or a rule;
the second is not fixed by writing a pKa at all. The sweep asks the provider
about the PARENT as well and splits the count, because handing the follow-up
item a single number would hand it the wrong work.

Run: ``python validation/pka_domains.py``            (~5 s: no flask is built)
     ``python validation/pka_domains.py --corpus-only``
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys

from rdkit import RDLogger

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

from catalog import load_compounds, load_steps  # noqa: E402

from chemsim.engine import inventory as inv  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.properties import (  # noqa: E402
    VolatilityProvider,
    electrolyte,
    electrolyte_provider,
)
from chemsim.properties import carboxylic_pka  # noqa: E402
from chemsim.properties.thermochemistry import ThermochemistryProvider  # noqa: E402

RDLogger.DisableLog("rdApp.*")

WATER = "O"
HYDRONIUM = "[OH3+]"

# A dissociation strips one proton, a protonation adds one to a site the row's
# own SMARTS then refuses, so the fixpoint is reached in a handful of rounds.
# The cap is here to bound a row someone writes later, and it reports itself.
MAX_ROUNDS = 8


def molecule(smiles: str) -> Molecule | None:
    """``Molecule`` or ``None`` -- the corpus is allowed to hold a bad SMILES."""
    try:
        return Molecule.from_smiles(smiles)
    except ValueError:
        return None


def classes():
    """``[(template, partner Molecule)]`` -- the rows that carry a substrate.

    The partner is read off the row's second slot rather than declared, so a
    row added to ``dissociation_templates`` in the protonation direction is
    swept in the direction it was written. ``water_autoionization`` matches
    water in BOTH slots and has no substrate; it is dropped here and its two
    ions are hard-coded in ``ion_thermochemistry`` anyway.
    """
    water, hydronium = Molecule.from_smiles(WATER), Molecule.from_smiles(HYDRONIUM)
    out = []
    for tmpl in electrolyte.dissociation_templates():
        if tmpl.n_reactant_slots != 2:
            continue
        first = tmpl.reactant_pattern(0)
        if water._mol.HasSubstructMatch(first):
            continue                      # water_autoionization: no substrate
        second = tmpl.reactant_pattern(1)
        for partner in (water, hydronium):
            if partner._mol.HasSubstructMatch(second):
                out.append((tmpl, partner))
                break
    return out


# The solvent, in every spelling the rows hand back. A dissociation takes water
# in and returns HYDRONIUM, so filtering the product tuple on the partner it was
# GIVEN drops nothing -- the first run of this sweep reached zero ions that way.
SOLVENT = {"O", "[OH3+]", "[OH-]"}


def ion_of(products) -> Molecule | None:
    """The charged half of a product tuple, dropping the solvent it rode on."""
    rest = [p for p in products if p.smiles not in SOLVENT]
    if len(rest) != 1:
        return None
    return rest[0] if rest[0].charge != 0 else None


def fixpoint(start: dict[str, str], rows) -> list[dict]:
    """Every ion these rows reach from ``start``, with the edge that made it.

    ``start`` is ``SMILES -> label``, the label being the catalog compound or
    shelf row the species came from, so a route can be named later. Each edge
    is recorded once per (parent, class); the same ion reached twice keeps both
    edges, because the question "which class is this gap in" has two answers
    when two classes make the same anion.
    """
    edges: list[dict] = []
    seen = dict(start)
    frontier = dict(start)
    rounds = 0
    while frontier and rounds < MAX_ROUNDS:
        rounds += 1
        made: dict[str, str] = {}
        for smiles, label in sorted(frontier.items()):
            mol = molecule(smiles)
            if mol is None:
                continue
            for tmpl, partner in rows:
                if not mol._mol.HasSubstructMatch(tmpl.reactant_pattern(0)):
                    continue
                try:
                    runs = tmpl.run((mol, partner))
                except Exception:  # noqa: BLE001 -- a refusal is an answer here
                    continue
                for products in runs:
                    ion = ion_of(products)
                    if ion is None:
                        continue
                    edges.append({"class": tmpl.name, "parent": smiles,
                                  "ion": ion.smiles, "label": label,
                                  "round": rounds})
                    if ion.smiles not in seen:
                        made[ion.smiles] = label
        seen.update(made)
        frontier = made
    if frontier:
        print(f"  the fixpoint was cut off at {MAX_ROUNDS} rounds with "
              f"{len(frontier)} species still new -- this is a lower bound:")
        for smiles, label in sorted(frontier.items()):
            print(f"      {smiles}  ({label})")
    return edges


def tier_test(provider):
    """``SMILES -> "table" | "rule" | ""`` -- how this ion prices today.

    The tier is read off the record's own ``source``, which is the string
    ``build_network`` reports to the player, rather than inferred from which
    call answered. Copied from ``fatty_acid_pka.priced_test`` for that reason.
    """
    def tier(smiles: str) -> str:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                data = provider.get(smiles)
        except Exception:  # noqa: BLE001
            return ""
        return "rule" if electrolyte.PLATEAU_RULE in data.source else "table"
    return tier


def anchored(provider, smiles: str) -> bool:
    """Can the provider price this species at all -- the anchor question."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            provider.get(smiles)
    except Exception:  # noqa: BLE001
        return False
    return True


def pair_class(rows) -> dict[str, str]:
    """``AcidPair.name -> class`` for every curated row a template reaches.

    Membership is measured, not typed: the row belongs to the class whose
    template turns one half of the pair into the other. A pair no template
    interconverts is reported as ``unreachable`` -- pyridinium is the known
    case, and it is a LIMIT the amine row's comment already names.
    """
    out: dict[str, str] = {}
    for pair in electrolyte.known_pairs():
        acid, base = molecule(pair.acid), molecule(pair.base)
        if acid is None or base is None:
            continue
        found = ""
        for tmpl, partner in rows:
            for start, target in ((acid, base.smiles), (base, acid.smiles)):
                if not start._mol.HasSubstructMatch(tmpl.reactant_pattern(0)):
                    continue
                try:
                    runs = tmpl.run((start, partner))
                except Exception:  # noqa: BLE001
                    continue
                if any(p.smiles == target for prods in runs for p in prods):
                    found = tmpl.name
                    break
            if found:
                break
        out[pair.name or pair.acid] = found or "unreachable"
    return out


def routes_touched(labels: set[str]) -> dict[str, set[str]]:
    """Catalog routes naming any of these compounds in a step.

    An upper bound on what the bucket can unblock and nothing more: the route
    still needs its templates and the rest of its species. It is here because a
    count of ions says nothing about coverage until it is asked which routes
    are standing behind it.
    """
    out: dict[str, set[str]] = {}
    for step in load_steps():
        hit = labels & (set(step.reactants) | set(step.products))
        if hit:
            out.setdefault(step.route, set()).update(hit)
    return out


def panel(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def report(edges: list[dict], tier, provider) -> dict[str, list[dict]]:
    """Per-class counts, and the missing ions split by which gap they are."""
    ions: dict[str, dict] = {}
    for e in edges:
        keep = ions.setdefault(e["ion"], {"class": e["class"], "parents": set(),
                                          "labels": set()})
        keep["parents"].add(e["parent"])
        keep["labels"].add(e["label"])
    for smiles, v in ions.items():
        v["tier"] = tier(smiles)

    missing: dict[str, list[dict]] = {}
    print(f"  distinct ions the rows reach   {len(ions):5d}")
    print(f"  {'class':34s} {'ions':>6s} {'table':>6s} {'rule':>6s} "
          f"{'missing':>8s}")
    order = sorted({v["class"] for v in ions.values()})
    for name in order:
        mine = {k: v for k, v in ions.items() if v["class"] == name}
        table = sum(1 for v in mine.values() if v["tier"] == "table")
        rule = sum(1 for v in mine.values() if v["tier"] == "rule")
        gap = [dict(v, ion=k) for k, v in mine.items() if not v["tier"]]
        missing[name] = gap
        print(f"  {name:34s} {len(mine):6d} {table:6d} {rule:6d} "
              f"{len(gap):8d}")
    total = sum(len(v) for v in missing.values())
    print(f"  {'':34s} {'':6s} {'':6s} {'':6s} {total:8d}  unpriceable today")

    # NOTE: without this line the headline lies, and the shelf panel is where it
    # shows. An ion count is not a compound count: a species with n acidic sites
    # deprotonates to a POWERSET, so tannic acid's five phenols alone are 35 of
    # the shelf's 39 gaps. A table row is written per PAIR, so the ion count is
    # the honest unit for "what is missing"; the compound count is the honest
    # unit for "how much chemistry is behind it", and they differ by an order of
    # magnitude here.
    flat = [g for v in missing.values() for g in v]
    sources: dict[str, int] = {}
    for g in flat:
        for label in g["labels"]:
            sources[label] = sources.get(label, 0) + 1
    if flat:
        worst = sorted(sources.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        print(f"  those {len(flat)} ions come from {len(sources)} compounds; "
              "the three that make the most are")
        for label, n in worst:
            print(f"      {n:4d}  {label}")

    # A compound with two acidic sites has more than one ion, and only one
    # protonation ORDER is the one anyone measures: salicylic acid's phenol
    # proton taken while its carboxyl is still on is a microspecies, reachable
    # by the rows and priced by no compilation. Counting it beside a missing
    # benzoate would overstate what curation can buy, so it is split out.
    priced_labels = {label for k, v in ions.items() if v["tier"]
                     for label in v["labels"]}
    micro = sum(1 for g in flat if set(g["labels"]) & priced_labels)
    if flat:
        print(f"  {micro} of them come from a compound the table already "
              "reaches by another proton,")
        print("  so they are alternative protonation orders and not "
              "un-ionisable compounds.")

    print()
    print("  the missing ions, split by which gap they actually are:")
    for name in order:
        gap = missing[name]
        if not gap:
            continue
        for g in gap:
            g["gap"] = ("pKa" if any(anchored(provider, p) for p in g["parents"])
                        else "parent")
        wants = sum(1 for g in gap if g["gap"] == "pKa")
        print(f"  {name:34s} {wants:4d} want a pKa, {len(gap) - wants:4d} "
              "have no priced parent")
    return missing


def spreads(where: dict[str, str]) -> None:
    """Panel 0 -- the curated table by class, and the width of each class."""
    by_class: dict[str, list] = {}
    for pair in electrolyte.known_pairs():
        by_class.setdefault(where[pair.name or pair.acid], []).append(pair)
    print(f"  {len(electrolyte.known_pairs())} curated pairs over "
          f"{len(by_class)} classes. The width is the whole class, so it is an")
    print("  upper bound on what one value would cost -- a domain inside the "
          "class can be")
    print("  narrower, and for the carboxylic row it is: the plateau rule's own "
          "domain")
    level = carboxylic_pka.plateau(electrolyte.known_pairs())
    if level is not None:
        print(f"  holds {level.n} of those rows and spans {level.width:.2f} "
              "units, against the whole class below.")
    for name in sorted(by_class):
        members = sorted(by_class[name], key=lambda p: p.pKa)
        lo, hi = members[0].pKa, members[-1].pKa
        print(f"  {name:34s} {len(members):3d} rows  "
              f"{lo:6.2f} .. {hi:6.2f}   width {hi - lo:5.2f}")
        for pair in members:
            print(f"      {pair.pKa:6.2f}  {pair.name or pair.acid}")


PHENOL = "[c][OX2H1]"


def phenol_electronics(missing: dict[str, list[dict]],
                       where: dict[str, str]) -> None:
    """Panel 4 -- is the phenol gap electronically inside the curated sample?

    Phenol is the only remaining rule CANDIDATE: the carboxylic class already
    has one, the amine class's three rows span six pKa units, and the mineral
    oxyacid class wants no pKa at all. Its own three rows span 3.45, but the
    13.40 is salicylate's second proton -- an intramolecular hydrogen bond to
    the ortho carboxylate, already argued in ``_PAIRS`` -- so the plain-phenol
    sample is two rows 0.24 apart, which is exactly the shape the carboxylic
    plateau was built on.

    What decides it is not the width of the sample but where the gap sits
    relative to it. Both curated phenols carry electron donors; the gap holds
    nitrophenols, whose measured pKa is nearly three units lower. So this panel
    sums the ring substituents of each side with ``hammett.survey`` and reports
    how far outside the curated range the gap reaches.

    And the scale is the wrong one for a pKa, which is the point rather than
    a caveat. ``hammett`` carries sigma-plus (with two labelled aqueous
    proxies), fitted on electrophilic substitution rates; phenol ionisation is
    fitted on sigma-MINUS. This panel therefore measures DISTANCE from the
    curated sample and never a pKa -- a rho quoted against the wrong sigma scale
    is the error that module's docstring exists to prevent.
    """
    from chemsim.reactions import hammett

    def sigma(smiles: str) -> tuple[float, int] | None:
        mol = molecule(smiles)
        if mol is None or not mol.substructure_matches(PHENOL):
            return None
        found = hammett.survey(mol._mol)
        return found.sigma_sum, len(found.unknown)

    # The class, not the ring. Salicylic acid's ring answers the phenol
    # pattern and its 2.97 is the CARBOXYL's, so keying this list on the
    # substructure put a carboxylic pKa in a list of phenol pKas -- the first
    # run of this panel did exactly that. ``pair_class`` asks which row
    # interconverts the pair, which is the question.
    curated = []
    for pair in electrolyte.known_pairs():
        if where.get(pair.name or pair.acid) != "phenol_dissociation":
            continue
        got = sigma(pair.acid)
        if got is not None:
            curated.append((got[0], pair.pKa, pair.name or pair.acid))
    print("  the curated phenols, summed on the scale the engine has:")
    for sigma_sum, pKa, name in sorted(curated):
        print(f"      sigma_sum {sigma_sum:+6.3f}   pKa {pKa:5.2f}   {name}")
    lo = min(x for x, _, _ in curated)
    hi = max(x for x, _, _ in curated)
    # Derived rather than argued: the largest pKa difference between two curated
    # phenols the substituent sum CANNOT tell apart. Anything a rule reads off
    # this scale gives both of them one value.
    ties = [(abs(a[1] - b[1]), a[2], b[2])
            for i, a in enumerate(curated) for b in curated[i + 1:]
            if abs(a[0] - b[0]) < 1e-9]
    if ties:
        gap, one, two = max(ties)
        print(f"  {one} and {two} share a sigma_sum and are "
              f"{gap:.2f} pKa units apart.")

    seen: dict[str, tuple[float, int]] = {}
    for g in missing.get("phenol_dissociation", ()):
        if g["gap"] != "pKa":
            continue
        for parent in g["parents"]:
            got = sigma(parent)
            if got is not None:
                seen[parent] = got
    outside = {k: v for k, v in seen.items() if not lo <= v[0] <= hi}
    unknown = {k: v for k, v in seen.items() if v[1]}
    print()
    print(f"  {len(seen)} gap phenols carry a ring the survey can read. "
          f"{len(outside)} of them sit outside")
    print(f"  the curated {lo:+.3f} .. {hi:+.3f}, and {len(unknown)} carry at "
          "least one substituent no")
    print("  pattern claims -- which the survey reports rather than scoring as "
          "zero.")
    ranked = sorted(seen.items(), key=lambda kv: kv[1][0])
    for smiles, (sigma_sum, _) in ranked[:3] + ranked[-3:]:
        print(f"      sigma_sum {sigma_sum:+6.3f}   {smiles[:60]}")


def corpus_start() -> dict[str, str]:
    """``SMILES -> compound id`` for every catalog compound, fragment-wise.

    Fragment-wise because ``thermochemistry`` refuses a dot-separated mixture as
    one species and prices the parts: a row for potassium acetate would be a row
    for a species that cannot exist here. ``fatty_acid_pka.fragments`` makes the
    same split for the same reason.
    """
    out: dict[str, str] = {}
    for compound in load_compounds().values():
        for part in compound.smiles.split("."):
            out.setdefault(part, compound.id)
    return out


def shelf_start() -> dict[str, str]:
    """``SMILES -> shelf row id`` for every chargeable shelf row."""
    out: dict[str, str] = {}
    for item in inv.shelf():
        if not item.chargeable:
            continue
        for smiles in item.species:
            out.setdefault(smiles, item.id)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-only", action="store_true",
                    help="skip the shelf panel")
    args = ap.parse_args()

    thermo = electrolyte_provider()
    neutral = ThermochemistryProvider()
    VolatilityProvider(neutral)
    tier = tier_test(thermo)
    rows = classes()

    print(__doc__.split("Run:")[0].rstrip())

    panel("0. THE CURATED TABLE, BUCKETED BY THE ROW THAT REACHES IT")
    where = pair_class(rows)
    spreads(where)

    panel("1. THE CORPUS -- every catalog compound, driven to a fixpoint")
    edges = fixpoint(corpus_start(), rows)
    missing = report(edges, tier, thermo)

    panel("2. THE SHELF -- the chargeable rows, same fixpoint")
    if args.corpus_only:
        print("  skipped (--corpus-only)")
    else:
        shelf_missing = report(fixpoint(shelf_start(), rows), tier, thermo)
        print()
        print("  by shelf row, with one ion each -- a row with more than one is "
              "a species")
        print("  with more than one acidic site, not more than one gap in the "
              "chemistry:")
        per_row: dict[str, list[str]] = {}
        for v in shelf_missing.values():
            for g in v:
                for label in g["labels"]:
                    per_row.setdefault(label, []).append(g["ion"])
        for label, ions in sorted(per_row.items(),
                                  key=lambda kv: (-len(kv[1]), kv[0])):
            shown = sorted(ions, key=len)[0]
            extra = f"  (+{len(ions) - 1} more)" if len(ions) > 1 else ""
            print(f"      {label:28s}  {shown[:60]}{extra}")

    panel("3. WHAT IS STANDING BEHIND THE CORPUS GAP")
    n_routes = len({step.route for step in load_steps()})
    print("  Only the ions that WANT A pKa are counted here: an ion whose "
          "parent has no")
    print("  thermochemistry is not unblocked by writing one, and mixing the "
          "two would")
    print("  hand the follow-up item the wrong work. Every route count is an "
          "upper")
    print("  bound -- the route still needs its templates and the rest of its "
          "species.")
    print()
    for name in sorted(missing, key=lambda k: -sum(
            1 for g in missing[k] if g["gap"] == "pKa")):
        gap = [g for g in missing[name] if g["gap"] == "pKa"]
        if not gap:
            continue
        labels = {label for g in gap for label in g["labels"]}
        routes = routes_touched(labels)
        print(f"  {name}: {len(gap)} ions over {len(labels)} compounds, and "
              f"{len(routes)} of the")
        print(f"  catalog's {n_routes} routes name one of those compounds in a "
              "step.")
        for route, species in sorted(routes.items())[:12]:
            print(f"      {route:34s}  {', '.join(sorted(species))}")
        if len(routes) > 12:
            print(f"      ... and {len(routes) - 12} more routes")
        # The pick order for whoever writes rows next: a compound is worth a
        # curated pair in proportion to how many routes are standing behind it,
        # and one row can only ever be written per PAIR.
        demand: dict[str, int] = {}
        for route, species in routes.items():
            for label in species:
                demand[label] = demand.get(label, 0) + 1
        ranked = sorted(demand.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
        print("  the compounds in it that the most routes name:")
        for label, n in ranked:
            word = "route " if n == 1 else "routes"
            print(f"      {n:3d} {word}  {label}")
        print()

    panel("4. THE ONE RULE CANDIDATE LEFT, AND HOW FAR THE GAP REACHES")
    phenol_electronics(missing, where)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

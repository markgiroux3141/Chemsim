"""S7's second standing audit: can each catalog row be balanced AT ALL?

``tools/catalog.py``'s ``validate`` checks that every SMILES parses, every
species id exists and every route's target is produced by one of its own steps.
**It has never checked that a step conserves matter**, and 377 steps have gone
past it.

⚠ THE QUESTION IS NOT "DOES IT BALANCE AS WRITTEN". The corpus deliberately
carries no stoichiometric coefficients -- ``methane + water -> carbon-monoxide +
hydrogen`` is the steam reformer, and its coefficients are 1, 1, 1, 3. So the
question is whether a **strictly positive** coefficient vector exists at all.
That is an LP feasibility problem: find x with ``A x = 0`` and every ``x_i >= 1``,
where A is the element-and-charge matrix with the products' columns negated. If
it is infeasible, no stoichiometry can express the row and the row is a bug.

⚠⚠ AND A ROW WITH A ZERO COEFFICIENT IS THE INTERESTING FAILURE, not an
edge case. ``hydrogenation-margarine`` step 2 reads ``oleic-acid + hydrogen +
nickel -> elaidic-acid + nickel``: oleic and elaidic acid are both C18H34O2, so
the only balance available sets the hydrogen's coefficient to ZERO. An H2 goes
in and nothing comes out. The row cannot be written down.

## WHAT THIS AUDIT IS AND IS NOT FOR

It is **not** a to-do list of 60-odd rows to rewrite. The corpus is an audit
CORPUS: inventing chemistry inside it is not allowed (the ``diels-alder-route``
precedent, and ``vitriol-distillation``'s deliberately uncorrected row). What it
is for is that a route cannot RUN through a step that cannot balance, so this is
a third bar beside species-readiness and template-readiness -- and unlike those
two it was never measured. A template built for an unbalanceable row will be
refused by ``build_network``'s own element check, at the end of the work rather
than the start.

⚠ THE FAILURES ARE CLASSIFIED, because the three kinds cost completely
different things to fix and one count over all of them would be the
outcome-label mistake in a new place. Measured: **75 of 367 testable rows**, as
**17 spurious / 1 charge / 57 atoms**.

  * **`spurious` -- a reagent consumed on paper and nowhere else.** The row
    balances the moment that one species is dropped. ``hydrogenation-margarine``
    step 2's hydrogen; ``perkin-route`` step 1's sodium acetate, which is the
    BASE and is not consumed by anything;
  * **`charge` -- the elements balance and the charge does not.** An ionic
    half-row. Only one row in the corpus fails this way alone;
  * **`atoms` -- an element has no source at all.** The large class, and mostly
    a deliberate simplification rather than a slip: ``anthracene +
    potassium-dichromate -> anthraquinone + water`` never says what became of
    the chromium, and ``nitrobenzene + iron + HCl -> aniline + Fe2O3 + water``
    never says what became of the chloride. A few are plain mistakes --
    ``indican + oxygen -> tyrian-purple + water`` needs bromine and there is
    none on the left, and ``picric-acid-route`` step 1 sulfonates phenol and
    hands back BENZENEsulfonic acid, losing the phenol's own oxygen.

⚠⚠ **AND IT TOUCHES THE HEADLINE EXACTLY ONCE, WHICH IS THE MEASUREMENT THAT
DECIDES WHETHER ANY OF THIS MATTERS TODAY.** One of the 24 routes in the BOTH
column carries an unbalanceable step: ``perkin-route`` step 1, and it is a
`spurious` -- the sodium acetate is the base. It is INERT, because
``perkin_condensation``'s SMARTS is on the aldehyde and the anhydride and does
not mention the base at all, so the template balances even though the row does
not. That is ``vitriol-distillation``'s landmine in a milder form: **the class
is credited, the ROW is wrong, and the two do not meet.**

Run: ``python validation/corpus_balance.py`` (~15 s).
"""

from __future__ import annotations

import os
import sys
from collections import Counter

import numpy as np
from scipy.optimize import linprog

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import catalog as cat  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402

# The row that S7 put in front of this audit, and the reason it exists.
HEADLINE = "hydrogenation-margarine"


def formula(smiles: str):
    m = Molecule.from_smiles(smiles)
    counts = Counter(m.element_counts())
    counts["<charge>"] = m.charge
    return counts


def _matrix(counts, n_react, keys):
    return np.array(
        [[(c.get(k, 0) if j < n_react else -c.get(k, 0)) for j, c in enumerate(counts)]
         for k in keys],
        dtype=float,
    )


def _feasible(A) -> bool:
    """Is there an x with A x = 0 and every x_i >= 1?"""
    n = A.shape[1]
    return bool(linprog(
        c=np.zeros(n), A_eq=A, b_eq=np.zeros(A.shape[0]),
        bounds=[(1.0, None)] * n, method="highs",
    ).success)


def balanceable(counts, n_react, names):
    """Is there a strictly positive coefficient vector? (LP feasibility.)

    ``A x = 0`` with every ``x_i >= 1``. The lower bound of 1 rather than 0 is
    what makes this the right question: a solution that zeroes a species is a
    balance for a DIFFERENT row from the one written down.

    On failure the row is CLASSIFIED, because the four kinds of failure cost
    completely different things to fix and lumping them into one count would be
    the outcome-label mistake in a new place:

      ``spurious``  it balances as soon as one species is dropped -- a reagent
                    consumed on paper only. ``hydrogenation-margarine``.
      ``charge``    it balances if charge is ignored -- an ionic half-row.
      ``atoms``     it fails on the elements alone. A missing atom.
    """
    elements = sorted({k for c in counts for k in c if c[k] and k != "<charge>"})
    keys = elements + ["<charge>"]
    A = _matrix(counts, n_react, keys)
    if _feasible(A):
        return True, "", ""

    # (a) does dropping exactly one species fix it?
    for j in range(len(counts)):
        keep = [i for i in range(len(counts)) if i != j]
        sub = [counts[i] for i in keep]
        n_r = sum(1 for i in keep if i < n_react)
        sub_keys = sorted({k for c in sub for k in c if c[k]})
        if not sub_keys:
            continue
        if _feasible(_matrix(sub, n_r, sub_keys)):
            return False, "spurious", (
                f"balances as soon as {names[j]!r} is dropped -- it is consumed "
                f"on paper and nowhere else"
            )

    # (b) is CHARGE the only thing that fails?
    if elements and _feasible(_matrix(counts, n_react, elements)):
        return False, "charge", (
            "the elements balance and the CHARGE does not: an ionic half-row, "
            "which build_network refuses by name"
        )

    return False, "atoms", "the elements themselves do not balance: an atom has no source"


def main() -> int:
    compounds = cat.load_compounds()
    steps = cat.load_steps()

    bad, skipped = [], []
    for s in steps:
        sp = list(s.reactants) + list(s.products)
        if any(cat.is_marker(x, compounds) for x in sp):
            skipped.append((s, "a marker has no formula"))
            continue
        try:
            counts = [formula(compounds[x].smiles) for x in sp]
        except Exception as exc:  # noqa: BLE001
            skipped.append((s, f"{type(exc).__name__}"))
            continue
        ok, kind, why = balanceable(counts, len(s.reactants), sp)
        if not ok:
            bad.append((s, kind, why))

    n = len(steps)
    print("=" * 74)
    print("CAN EACH CATALOG ROW BE BALANCED AT ALL?")
    print("=" * 74)
    print(f"   {n} steps")
    print(f"   {len(skipped):3d} not testable (a marker, or a SMILES that will not parse)")
    print(f"   {n - len(skipped) - len(bad):3d} balance with some positive coefficient vector")
    print(f"   {len(bad):3d} CANNOT be balanced by any positive coefficients")
    print()
    print("   Charge is a conserved quantity here beside the elements, which is")
    print("   why an ionic half-row fails: it is not an accounting choice, a")
    print("   half reaction genuinely does not conserve charge and")
    print("   build_network refuses one.")

    kinds = Counter(k for _, k, _ in bad)
    print()
    print("   BY KIND, because the three cost different things to fix:")
    for k, label in (
        ("spurious", "a reagent consumed on paper and nowhere else"),
        ("charge", "an ionic half-row: elements balance, charge does not"),
        ("atoms", "an atom with no source on the other side"),
    ):
        print(f"     {kinds[k]:3d}  {k:9s} {label}")

    by_route = {}
    for s, kind, why in bad:
        by_route.setdefault(s.route, []).append((s, kind, why))

    print()
    print("=" * 74)
    print(f"THE ROW THIS AUDIT WAS WRITTEN FOR -- {HEADLINE}")
    print("=" * 74)
    for s, kind, why in by_route.get(HEADLINE, []):
        print(f"   step {s.index}: {' + '.join(s.reactants)}")
        print(f"        -> {' + '.join(s.products)}")
        print(f"        [{kind}] {why}")
    print()
    print("   Oleic and elaidic acid are both C18H34O2 -- a cis/trans pair -- so")
    print("   the hydrogen has nowhere to go. The real mechanism needs it and")
    print("   REGENERATES it (half-hydrogenation on the metal, then loss of the")
    print("   other H), so the row wants hydrogen on both sides. It is left")
    print("   alone on the diels-alder-route precedent: this audit REPORTS, it")
    print("   does not rewrite the corpus.")
    print()
    print("   AND IT WOULD STILL NOT BE BUILDABLE. No estimator here tells a cis")
    print("   alkene from a trans one, so the engine prices that pair at")
    print("   dH = dG = 0.000 exactly. See data/catalog/README.md, S7.")

    print()
    print("=" * 74)
    print("EVERY UNBALANCEABLE ROW, BY ROUTE")
    print("=" * 74)
    for rid in sorted(by_route):
        print(f"   {rid}")
        for s, kind, why in by_route[rid]:
            print(f"     step {s.index}  {' + '.join(s.reactants)}")
            print(f"     {'':8s} -> {' + '.join(s.products)}")
            print(f"     {'':8s} [{kind}] {why}")

    print()
    print("=" * 74)
    print("DOES IT TOUCH THE HEADLINE? -- the only question that decides whether")
    print("this audit is a finding or a footnote")
    print("=" * 74)
    print(f"   {len(by_route)} of the 173 routes carry at least one unbalanceable step.")
    print()
    # The BOTH column, recomputed here rather than read off the report, so this
    # panel cannot go stale against it.
    import catalog_coverage as cc

    from chemsim.properties import (
        ThermochemistryProvider,
        UnifacProvider,
        VolatilityProvider,
    )
    from chemsim.properties.electrolyte import electrolyte_provider

    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    ionic = electrolyte_provider(base=thermo, volatility=vol)
    unifac = UnifacProvider()
    by_id = {
        c.id: cc.audit_compound(c, thermo, vol, ionic, unifac)
        for c in compounds.values()
    }
    routes = cat.load_routes()
    both = []
    for rid in routes:
        mine = [s for s in steps if s.route == rid]
        if not all(s.cls in cc.TEMPLATE_CLASSES for s in mine):
            continue
        sp = {x for s in mine for x in s.reactants + s.products}
        if all(by_id[x]["tier"] != "refused" for x in sp if x in by_id):
            both.append(rid)
    hit = sorted(set(both) & set(by_route))
    print(f"   the BOTH column holds {len(both)} routes, of which {len(hit)} carry")
    print("   an unbalanceable step:")
    for rid in hit:
        for s, kind, _ in by_route[rid]:
            print(f"     {rid:26s} step {s.index}  [{kind}]")
    if not hit:
        print("     (none)")
    print()
    print("   A route in the BOTH column with an unbalanceable step is a route")
    print("   whose template will be REFUSED by build_network's own element")
    print("   check -- at the END of the work rather than the start. That is what")
    print("   this list is worth: it is the cheapest thing to read before")
    print("   choosing the next template.")

    print()
    print("=" * 74)
    print("WHAT THIS AUDIT DOES **NOT** SAY -- S11, and it cost a template")
    print("=" * 74)
    print("   The test above is: does ANY positive coefficient vector conserve")
    print("   every element and the charge. That is a necessary condition and it")
    print("   is a WEAK one, because element conservation does not forbid")
    print("   rearranging carbon skeletons.")
    print()
    print("   THE STANDING EXAMPLE IS `vanillin-lignin` step 1, which this audit")
    print("   passes:")
    print()
    print("       coniferyl alcohol + oxygen -> vanillin + water")
    print("       balances at   8 C10H12O3 + 7 O2 -> 10 C8H8O3 + 8 H2O")
    print()
    print("   EIGHT AROMATIC RINGS IN AND TEN OUT. The row is written 1:1 and")
    print("   cannot be: a C10 monolignol makes one C8 vanillin and a C2 fragment")
    print("   the row does not name. S11 went to build `oxidative-cleavage` off")
    print("   this row, found that, and REFUSED the CLASS -- naming the missing")
    print("   product would be inventing chemistry inside the corpus, which is")
    print("   the `diels-alder-route` precedent this file already follows.")
    print()
    print("   !!! AND C3 BUILT THE CLASS ANYWAY, WHICH DOES NOT OVERTURN THIS")
    print("   PANEL -- IT NARROWS IT FROM A CLASS TO A ROW. `oxidative-cleavage`")
    print("   has a SECOND row that S11 did not read:")
    print()
    print("       vanillin-eugenol 2 | isoeugenol + O2 -> vanillin + MeCHO")
    print("       C10H12O4 both sides, EXACT at 1:1, C2 fragment NAMED")
    print()
    print("   The template is written off THAT row, and applied to coniferyl")
    print("   alcohol it produces glycolaldehyde -- which the corpus has carried")
    print("   in 07-carbonyls.psv all along. So the missing product needed no")
    print("   inventing: the mechanism supplies the fragment and the corpus")
    print("   supplies its name. S11's reason survives exactly where it was")
    print("   aimed. READ EVERY ROW OF A CLASS BEFORE REFUSING THE CLASS.")
    print()
    print("   !! AND THE ROW IS NOW INSIDE THE HEADLINE, WHICH IS NEW.")
    print("   `vanillin-lignin` was not in the BOTH column when S11 wrote this;")
    print("   it is now, because C3 covered its only class. So this audit's own")
    print("   standing example of a row that PASSES and is not the reaction it")
    print("   is written as sits inside the number the project quotes -- and it")
    print("   does NOT appear in the unbalanceable list above, because passing")
    print("   is the entire point of the example. THE ONE ROW THIS AUDIT FLAGS")
    print("   INSIDE THE BOTH COLUMN IS `perkin-route`; the row that is actually")
    print("   wrong is the one it cannot see.")
    print()
    print("   AND C3 DELIBERATELY DID NOT CORRECT THE ROW, for a reason that is")
    print("   about the row and not about caution. On CONIFERYL ALCOHOL the")
    print("   mechanism is unambiguous -- the side chain leaves as")
    print("   glycolaldehyde, and the flask says so. The catalog row is about")
    print("   alkaline LIGNIN LIQUOR, where the C2 fragment is a MIXTURE that")
    print("   depends on which monolignol reacted. Writing one name into it")
    print("   would over-commit the corpus in exactly the way S11 refused to.")
    print("   So the row keeps its wrong product, the template names the right")
    print("   one where it can be known, and this panel is the record of which")
    print("   is which.")
    print()
    print("   !!! AND C4 ADDS A SECOND STANDING EXAMPLE, WHICH IS THE SAME")
    print("   SHAPE WITH THE OPPOSITE VERDICT. `abe-fermentation` step 1 reads")
    print()
    print("       glucose -> acetone + 1-butanol + ethanol + CO2 + H2")
    print("       balances at  5 C6H12O6 -> 2 + 2 + 2 + 12 CO2 + 8 H2")
    print()
    print("   FIVE SUGARS IN AND SIX CARBON SKELETONS OUT, so this audit passes")
    print("   it and it is not the reaction as written. M5 read exactly that and")
    print("   refused the class as a metabolic NETWORK. !! BUT UNLIKE THE LIGNIN")
    print("   ROW, THE LUMP WAS A FORMATTING ARTEFACT AND NOT A MISSING")
    print("   PRODUCT: it is THREE reactions on one line, and each of the three")
    print("   balances exactly on ONE glucose --")
    print()
    print("       glucose       -> 2 ethanol + 2 CO2         C6H12O6 both sides")
    print("       glucose       -> 1-butanol + 2 CO2 + H2O   C6H12O6 both sides")
    print("       glucose + H2O -> acetone + 3 CO2 + 4 H2    C6H14O7 both sides")
    print()
    print("   C4 built all three, so this row is ALSO inside the BOTH column now.")
    print("   !!! SO A ROW THAT PASSES AND IS NOT ITS OWN REACTION HAS TWO")
    print("   DIFFERENT CAUSES AND THEY NEED OPPOSITE ANSWERS: the lignin row")
    print("   is short a PRODUCT and must be left wrong, and the fermentation")
    print("   row was short a LINE BREAK and could just be split. The audit")
    print("   cannot tell them apart, and neither can a coefficient vector --")
    print("   only reading the chemistry can.")
    print()
    print("   THE CHECK THIS AUDIT CANNOT MAKE is whether the balanced vector is")
    print("   the row's OWN. A cheap proxy: compare ring counts, or heavy-atom")
    print("   counts per molecule, between the smallest feasible vector and the")
    print("   1:1 reading. Not built -- named, so the next reader does not take a")
    print("   pass here as permission to write a SMARTS.")
    print()
    print("   AND THE CONVERSE ROW, MEASURED THE SAME DAY: `skraup-route` step 2")
    print("   passes AND is real. It reads with aniline on BOTH sides, which")
    print("   looks like the `spurious` pattern and is not -- the nitrobenzene")
    print("   oxidant is REDUCED to aniline. It balances at")
    print()
    print("       3 aniline + 3 acrolein + 1 nitrobenzene")
    print("           -> 3 quinoline + 1 aniline + 5 water")
    print()
    print("   with FOUR aromatic rings in and four out. That is the real Skraup")
    print("   stoichiometry, and it is what a template for that class has to")
    print("   carry: 7 reactant slots and 9 product slots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

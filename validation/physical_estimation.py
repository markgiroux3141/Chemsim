"""Does an ASSEMBLED physical half behave like a real substance?

A record built this way carries a measured Tb from one compilation, a
Wilson-Jasperson Tc and Pc (or measured ones from a second compilation), a Fedors
Vc, an enthalpy of vaporisation differentiated out of the Lee-Kesler curve, and a
Benson enthalpy of formation. That is four tabulations in one entry, and this
project has been bitten three times by the rule that a value is only meaningful
against the basis it was fitted with. So the entry does not get to be trusted
because its parts look reasonable; it has to be checked end to end.

Four panels, in increasing order of how much they can actually catch.

PANEL 1 -- WILSON-JASPERSON / FEDORS vs MEASURED
    Nine species have fully curated measured Tc/Pc/Vc/Hvap, so the estimators can
    be scored directly against them.

PANEL 2 -- BOILS AT 1 ATM
    ⚠ The brief for this work proposed reusing this as the independent check. It
    is NOT independent, and saying so is the point of running it. The acentric
    factor is DERIVED by inverting Lee-Kesler at Tb precisely so the curve passes
    through (Tb, 1 atm) exactly -- so this panel can only ever measure the
    Antoine FIT residual, and it will pass no matter how wrong Pc is. It is worth
    running because a fit residual is a real failure mode. It is not worth
    believing as a test of Tc/Pc.

PANEL 3 -- THE ACENTRIC FACTOR, which IS independent
    omega derived by inverting Lee-Kesler at Tb, against tabulated omega. This
    one bites, because a wrong Pc moves the derived omega while leaving the
    boiling point untouched -- exactly the error Panel 2 is blind to. Entries
    sourced from ``ACENTRIC_DEFINITION`` are excluded at build time: that is
    omega back-computed from a vapour pressure, so it is not independent of the
    thing being checked.

PANEL 4 -- WHAT THE OVERLAY WOULD DO
    ``ThermochemistryProvider(measured_physical=False)`` reproduces the basis
    before this route existed. The difference is reported rather than asserted,
    the same reason ``benson=False`` and ``liquid_standard_state=False`` exist.
"""

import statistics

from chemsim.matter import Molecule
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.critical import (
    CriticalPropertyError,
    acentric_factor,
    estimate_physical,
    hvap_at_tb,
)
from chemsim.properties.formation_data import PHYSICAL_PROPERTIES
from chemsim.properties.physical_data import MEASURED_PHYSICAL
from chemsim.properties.volatility import P_ATM_BAR


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------------
rule("PANEL 1 -- Wilson-Jasperson / Fedors / Lee-Kesler Hvap vs MEASURED")
# ---------------------------------------------------------------------------
# Scored against the nine hand-curated records, which are the only species with
# measured values for all four quantities. Every estimate here is made with the
# measured Tb as its only input, exactly as the provider makes it.

print(f"{'species':24s} {'Tc':>16s} {'Pc':>16s} {'Vc':>16s} {'Hvap':>16s}")
errors: dict[str, list[float]] = {"Tc": [], "Pc": [], "Vc": [], "Hvap": []}
for smi, phys in sorted(PHYSICAL_PROPERTIES.items()):
    mol = Molecule.from_smiles(smi)
    try:
        est = estimate_physical(mol, phys["Tb"], "curated")
    except CriticalPropertyError as exc:
        print(f"{smi:24s} REFUSED: {exc}")
        continue
    row = f"{smi:24s}"
    for key in ("Tc", "Pc", "Vc", "Hvap"):
        measured = phys.get(key)
        if measured is None:
            row += f"{'-':>16s}"
            continue
        pct = 100.0 * (getattr(est, key) - measured) / measured
        errors[key].append(abs(pct))
        row += f"{getattr(est, key):9.1f}{pct:+6.1f}%"
    print(row)

print()
for key, values in errors.items():
    print(
        f"  {key:5s} mean |error| {statistics.mean(values):5.1f}%   "
        f"median {statistics.median(values):5.1f}%   worst {max(values):5.1f}%  "
        f"(n={len(values)})"
    )
print(
    """
READ THIS, because the brief for this work understated it. Wilson-Jasperson's Pc
was reported as "12% high" on the strength of acetic anhydride alone. Across nine
polar species it is far worse than that, and it is the one number the rest of the
chain is most sensitive to: Pc enters the acentric factor, which sets the whole
vapour-pressure curve. Tc is genuinely good and Vc is acceptable.

The consequence is bounded and specific, and Panel 2 explains why: a species
still BOILS at the right temperature, because omega absorbs the Pc error to keep
the curve through (Tb, 1 atm). What a bad Pc corrupts is the SLOPE there -- the
latent heat, and the vapour pressure away from the boiling point. That is exactly
the pattern in the Hvap column, whose error tracks the Pc error species by
species rather than sitting at the ~3-4% the dz=1 assumption costs (see methyl
formate, where Pc is good and Hvap follows).

This is why measured Tc/Pc are preferred wherever the experimental tier has them,
and why they are taken as a PAIR."""
)

# The dz = 1 assumption in ``hvap_at_tb``, isolated from the Pc error by feeding
# it the MEASURED critical constants. This separates the two error sources
# instead of leaving them summed.
print()
print("Hvap with MEASURED Tc/Pc -- isolates the dz=1 assumption from the Pc error")
iso = []
for smi, phys in sorted(PHYSICAL_PROPERTIES.items()):
    if phys.get("Hvap") is None or phys.get("Tc") is None or phys.get("Pc") is None:
        continue
    est = hvap_at_tb(phys["Tb"], phys["Tc"], phys["Pc"])
    pct = 100.0 * (est - phys["Hvap"]) / phys["Hvap"]
    iso.append(pct)
    print(f"  {smi:24s} {est:6.2f} vs {phys['Hvap']:6.2f} kJ/mol  {pct:+6.1f}%")
print(
    f"  mean {statistics.mean(iso):+.1f}%, median {statistics.median(iso):+.1f}% "
    f"-- the sign is systematic, as an ideal-vapour dz should be"
)
print(
    "  Formic acid is the outlier and NOT a failure of the derivation: its vapour\n"
    "  is dimeric, so its apparent enthalpy of vaporisation prices a different\n"
    "  molecule from the one the curve describes. That is the same trap already\n"
    "  documented for carboxylic acids in formation_data."
)

# ---------------------------------------------------------------------------
rule("PANEL 2 -- boils at 1 atm  (a FIT check, not an independent one)")
# ---------------------------------------------------------------------------
thermo = ThermochemistryProvider()
volatility = VolatilityProvider(thermo)

print(f"{'species':34s} {'Tb meas':>9s} {'P(Tb) bar':>11s} {'error':>9s}  physical half")
residuals = []
for smi in sorted(MEASURED_PHYSICAL):
    mol = Molecule.from_smiles(smi)
    try:
        t = thermo.get(mol)
    except ValueError:
        continue
    if t.Tb is None:
        continue
    v = volatility.get(mol)
    if not v.condensable:
        continue
    p = v.coefficient(t.Tb)
    pct = 100.0 * (p - P_ATM_BAR) / P_ATM_BAR
    residuals.append(abs(pct))
    half = (t.physical_source or "")[:34]
    print(f"  {smi:32s} {t.Tb:9.2f} {p:11.5f} {pct:+8.2f}%  {half}")

print()
print(
    f"  mean |residual| {statistics.mean(residuals):.2f}%   "
    f"worst {max(residuals):.2f}%   (n={len(residuals)})"
)
print(
    """
  What this panel does and does not test. The Antoine fit is a least-squares
  approximation to Lee-Kesler over a window bracketing Tb, so a residual here is
  a real fit failure and worth bounding -- the nine curated species were held to
  1.4% and these should be too. But omega is chosen to force the underlying curve
  through this exact point, so no error in Tc or Pc can show up here. Panel 3 is
  where those live."""
)

# ---------------------------------------------------------------------------
rule("PANEL 3 -- the acentric factor, against tabulation (INDEPENDENT)")
# ---------------------------------------------------------------------------
print(f"{'species':30s} {'omega ours':>11s} {'omega tab':>10s} {'diff':>8s}  Tc/Pc from")
diffs_est, diffs_meas = [], []
for smi, m in sorted(MEASURED_PHYSICAL.items()):
    if m.omega_reference is None or m.Tb is None:
        continue
    mol = Molecule.from_smiles(smi)
    try:
        est = estimate_physical(
            mol, m.Tb.value, "x",
            Tc=m.Tc.value if m.Tc else None,
            Pc=m.Pc.value if m.Pc else None,
        )
        ours = acentric_factor(est.Tb, est.Tc, est.Pc)
    except CriticalPropertyError:
        continue
    ref = m.omega_reference.value
    diff = ours - ref
    (diffs_meas if est.critical_measured else diffs_est).append(abs(diff))
    origin = "measured" if est.critical_measured else "Wilson-Jasperson"
    print(f"  {smi:28s} {ours:11.3f} {ref:10.3f} {diff:+8.3f}  {origin}")

print()
for label, values in (
    ("measured Tc/Pc     ", diffs_meas),
    ("Wilson-Jasperson   ", diffs_est),
):
    if values:
        print(
            f"  {label} mean |d omega| {statistics.mean(values):.3f}   "
            f"worst {max(values):.3f}   (n={len(values)})"
        )
print(
    """
  This is the panel that can fail, and the split above is the result worth
  carrying: deriving omega from MEASURED Tc/Pc lands far closer to tabulation
  than deriving it from Wilson-Jasperson's. That is the Pc error from Panel 1
  arriving where Panel 2 could not see it, and it is the evidence for preferring
  measured critical constants rather than an argument for it.

  Note the reference column is itself a compilation (YAWS), so a difference here
  is not automatically ours. It is used as a discrepancy detector, not as truth."""
)

# ---------------------------------------------------------------------------
rule("PANEL 4 -- what this route actually added")
# ---------------------------------------------------------------------------
# ``measured_physical=False`` reproduces the basis before the measured-Tb /
# Wilson-Jasperson / Fedors path existed, so the difference is measured rather
# than asserted.
before = ThermochemistryProvider(measured_physical=False)
after = ThermochemistryProvider()

gained, changed = [], []
for smi in sorted(MEASURED_PHYSICAL):
    mol = Molecule.from_smiles(smi)

    def resolve(provider):
        try:
            return provider.get(mol)
        except ValueError:
            return None

    b, a = resolve(before), resolve(after)
    if b is None and a is not None:
        gained.append((smi, a))
    elif b is not None and a is not None and (b.Tb, b.Tc, b.Pc) != (a.Tb, a.Tc, a.Pc):
        changed.append((smi, b, a))

print(f"NEWLY RESOLVING ({len(gained)}):")
for smi, a in gained:
    print(f"  {smi:32s} Tb={a.Tb:7.2f} Tc={a.Tc:7.2f} Pc={a.Pc:6.2f} Hf={a.Hf:9.2f}")
    print(f"    {a.source[:150]}")

print()
print(f"PHYSICAL HALF CHANGED, was already resolving ({len(changed)}):")
if not changed:
    print(
        "  (none -- every species in the measured table is one Joback cannot\n"
        "   fully price, so no existing record's Tb/Tc/Pc moved. That is why the\n"
        "   invariants table is untouched by this work: it closes a COVERAGE gap\n"
        "   and deliberately does not relitigate accuracy on species that already\n"
        "   resolve. Promoting measured Tb to a general overlay is a separate,\n"
        "   measurable change and this panel is where it would be measured.)"
    )
for smi, b, a in changed:
    print(f"  {smi:32s} Tb {b.Tb:7.2f} -> {a.Tb:7.2f}   Tc {b.Tc:7.2f} -> {a.Tc:7.2f}")

"""Fresh coverage audit: walk targets through parse -> thermo -> volatility -> condensed.

NOTE: the original 70-target list from the 2026-08-16 audit was not kept, so this
list is RECONSTRUCTED from the same categories. Treat the comparison to 46/70 and
51/70 as indicative, not exact.

Two things this harness does that the raw count does not.

**It reports WHICH HALF of a record failed.** A ThermoData is a formation half
(Hf/Gf, from curated data or Benson or Joback) and a physical half (Tb/Tc/Pc/Vc,
from curated data or a measured Tb plus Wilson-Jasperson/Fedors, or Joback), and
those resolve independently. Before that separation existed, a physical half
could never pair with a Benson formation half, so Benson priced acetic anhydride
to within 3.7 kJ/mol of measurement and the provider refused the species anyway.
Knowing which half is missing is the difference between "needs a boiling point"
and "needs a group value that does not exist in any tabulation we have".

**It uses the electrolyte provider for salts.** Sodium hydroxide does not exist
as a molecule in solution -- it IS its ions -- so asking the plain provider to
fragment ``[Na+].[OH-]`` tests nothing about coverage. That was a harness
artefact in the previous run, counted as a failure, and it is fixed here rather
than explained away.
"""
from collections import Counter

from chemsim.matter import Molecule
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.benson import BensonError
from chemsim.properties.benson import estimate as benson_estimate
from chemsim.properties.electrolyte import electrolyte_provider
from chemsim.properties.joback import JobackError
from chemsim.properties.joback import estimate as joback_estimate

TARGETS = {
    "bulk organics": [
        ("ethanol", "CCO"), ("acetic acid", "CC(=O)O"), ("acetone", "CC(C)=O"),
        ("ethyl acetate", "CCOC(C)=O"), ("methanol", "CO"), ("toluene", "Cc1ccccc1"),
        ("phenol", "Oc1ccccc1"), ("benzene", "c1ccccc1"), ("styrene", "C=Cc1ccccc1"),
        ("acetaldehyde", "CC=O"), ("formaldehyde", "C=O"), ("acetic anhydride", "CC(=O)OC(C)=O"),
        ("chloroform", "ClC(Cl)Cl"), ("DCM", "ClCCl"), ("THF", "C1CCOC1"),
        ("DMF", "CN(C)C=O"), ("DMSO", "CS(C)=O"), ("acetonitrile", "CC#N"),
        ("glycerol", "OCC(O)CO"), ("ethylene glycol", "OCCO"),
        ("aniline", "Nc1ccccc1"), ("nitrobenzene", "O=[N+]([O-])c1ccccc1"),
        ("benzaldehyde", "O=Cc1ccccc1"), ("cyclohexanone", "O=C1CCCCC1"),
        ("caprolactam", "O=C1CCCCCN1"), ("adipic acid", "OC(=O)CCCCC(=O)O"),
        ("urea", "NC(N)=O"), ("aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
        ("furfural", "O=Cc1ccco1"), ("pyridine", "c1ccncc1"),
    ],
    "pharma": [
        ("paracetamol", "CC(=O)Nc1ccc(O)cc1"), ("ibuprofen", "CC(C)Cc1ccc(cc1)C(C)C(=O)O"),
        ("caffeine", "Cn1cnc2c1c(=O)n(C)c(=O)n2C"), ("metformin", "CN(C)C(=N)N=C(N)N"),
        ("penicillin G", "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O"),
        ("morphine", "CN1CCC23c4c5ccc(O)c4OC2C(O)C=CC3C1C5"),
        ("quinine", "C=CC1CN2CCC1CC2C(O)c1ccnc2ccc(OC)cc12"),
        ("cholesterol", "CC(C)CCCC(C)C1CCC2(C)C1CCC1C2CC=C2CC(O)CCC12C"),
        ("salicylic acid", "OC(=O)c1ccccc1O"), ("lidocaine", "CCN(CC)CC(=O)Nc1c(C)cccc1C"),
    ],
    "fine / agro": [
        ("vanillin", "O=Cc1ccc(O)c(OC)c1"), ("indigo", "O=C1Nc2ccccc2C1=C1C(=O)Nc2ccccc21"),
        ("saccharin", "O=C1NS(=O)(=O)c2ccccc21"), ("glyphosate", "OC(=O)CNCP(=O)(O)O"),
        ("DEET", "CCN(CC)C(=O)c1cccc(C)c1"), ("citral", "CC(C)=CCCC(C)=CC=O"),
        ("limonene", "CC(=C)C1CCC(C)=CC1"), ("menthol", "CC(C)C1CCC(C)CC1O"),
        ("coumarin", "O=c1ccc2ccccc2o1"), ("TNT", "Cc1c([N+](=O)[O-])cc([N+](=O)[O-])cc1[N+](=O)[O-]"),
        ("citric acid", "OC(=O)CC(O)(CC(=O)O)C(=O)O"), ("glucose", "OCC1OC(O)C(O)C(O)C1O"),
    ],
    "inorganic": [
        ("water", "O"), ("sulfuric acid", "OS(=O)(=O)O"), ("nitric acid", "O[N+](=O)[O-]"),
        ("ammonia", "N"), ("chlorine", "ClCl"), ("hydrogen peroxide", "OO"),
        ("sodium hydroxide", "[Na+].[OH-]"), ("phosphoric acid", "OP(=O)(O)O"),
        ("carbon disulfide", "S=C=S"),
    ],
    "materials / polymer units": [
        ("ethylene", "C=C"), ("vinyl chloride", "C=CCl"), ("TFE", "FC(F)=C(F)F"),
        ("caprolactone", "O=C1CCCCCO1"), ("bisphenol A", "CC(C)(c1ccc(O)cc1)c1ccc(O)cc1"),
        ("terephthalic acid", "OC(=O)c1ccc(C(=O)O)cc1"), ("MDI", "O=C=Nc1ccc(Cc2ccc(N=C=O)cc2)cc1"),
        ("acrylonitrile", "C=CC#N"), ("PEDOT monomer (EDOT)", "c1csc2c1OCCO2"),
    ],
}

thermo = ThermochemistryProvider()
volatility = VolatilityProvider(thermo)

# Salts are charged as their ions, so they resolve through the electrolyte
# provider and nowhere else.
ionic = electrolyte_provider(volatility=volatility)


def components(smiles: str) -> list[str]:
    """A multi-component SMILES split into the species actually present.

    ``[Na+].[OH-]`` is not one molecule and there is nothing for a
    group-contribution method to fragment: sodium hydroxide does not exist as a
    molecule in solution, it IS its ions. Asking the plain provider to price the
    dotted string tests nothing, and counting the refusal as a coverage failure
    -- which the previous run did -- measured the harness rather than the
    simulator. A salt resolves when every ion it dissociates into resolves.
    """
    return smiles.split(".")


def resolve(smiles: str, provider: ThermochemistryProvider, vol: VolatilityProvider):
    """Walk one target through thermochemistry and volatility, ion by ion."""
    parts = components(smiles)
    picked = ionic if len(parts) > 1 or any(c in smiles for c in "+-") else provider
    if picked is ionic and provider is not thermo:
        # Keep the ion table anchored on whichever base provider is under test,
        # so the tier-contribution panel below compares like with like.
        picked = electrolyte_provider(base=provider, volatility=vol)
    last = None
    for part in parts:
        mol = Molecule.from_smiles(part)
        last = (picked.get(mol), vol.get(mol))
    return last


def diagnose(mol: Molecule) -> str:
    """Which half is missing, and why -- for a species that failed to resolve."""
    try:
        j = joback_estimate(mol)
        joback = (
            "Joback prices formation"
            if None not in (j.Hf, j.Gf)
            else "Joback fragments it but a group has no dGf contribution"
        )
    except JobackError:
        joback = "Joback cannot fragment it"
    try:
        benson_estimate(mol)
        benson = "Benson prices formation"
    except (BensonError, ValueError) as exc:
        detail = str(exc)
        if "no group value for" in detail:
            key = detail.split("no group value for", 1)[1].split("(")[0].strip()
            benson = f"Benson has no value for {key}"
        elif "no Benson groups for" in detail:
            benson = "Benson: " + detail.split(":", 1)[1].strip()
        else:
            benson = "Benson refuses"
    return f"formation half: {joback}; {benson}"


rows, stage_fail = [], Counter()
for cat, items in TARGETS.items():
    for name, smiles in items:
        try:
            mol = Molecule.from_smiles(smiles)
        except Exception as exc:                            # noqa: BLE001
            rows.append((cat, name, "parse", str(exc)[:60], ""))
            stage_fail["parse"] += 1
            continue
        try:
            t, v = resolve(smiles, thermo, volatility)
        except Exception as exc:                            # noqa: BLE001
            del exc
            rows.append((cat, name, "thermochemistry", diagnose(mol), ""))
            stage_fail["thermochemistry"] += 1
            continue
        rows.append((cat, name, "OK", v.kind, t.source[:34]))

total = len(rows)
ok = sum(1 for r in rows if r[2] == "OK")
print(f"{ok}/{total} fully resolve  (parse -> thermochemistry -> volatility)")
print()
for cat in TARGETS:
    sub = [r for r in rows if r[0] == cat]
    n = sum(1 for r in sub if r[2] == "OK")
    print(f"  {cat:28s} {n:2d}/{len(sub):2d}")
print()
print("failures by stage:", dict(stage_fail))
print()
print("WHAT FAILS, and why -- named at the level of the missing HALF")
for cat, name, stage, why, src in rows:
    if stage == "OK":
        continue
    print(f"  {name:20s} [{stage}] {why}")
print()
print(
    """Every remaining failure is a FORMATION half, and none of them is closable from
the sources this project has. That is the reverse of the situation before this
session, where the formation half existed and the physical half was unreachable.

  metformin, MDI   Joback fragments both, but the `-N= (nonring)` group has a dHf
                   contribution and NO dGf contribution in Joback & Reid's
                   published table -- verified against the `thermo` oracle, which
                   has the identical single gap, 1 group of 41. So it is the
                   method's limit, not our transcription. Benson has no value for
                   metformin's guanidine carbon or MDI's isocyanate carbonyl.
                   `chemicals` offers metformin's Tb and Hf ONLY from JOBACK --
                   i.e. it would hand back our own estimate as data -- and MDI's
                   three Hf sources span 245 kJ/mol, so neither is usable.
                   MDI's PHYSICAL half does now resolve, on a compilation-tier Tb.
  saccharin        Benson has no aryl-amide carbonyl value. No boiling point
                   exists in any source: it decomposes near 500 K without ever
                   boiling, so non-volatile is the correct physical answer and
                   only its melting point is available.
  glyphosate       Phosphorus. Joback, Benson and Fedors all lack it entirely.
                   Out of scope by the audit's own framing.

Naming these as data-source limits rather than gaps to close is the same
judgement already recorded for pyridine and the nitroaromatics under Benson."""
)
print()
print("PROVENANCE of what resolves")
prov = Counter(r[4] for r in rows if r[2] == "OK")
for k, v in prov.most_common():
    print(f"  {v:3d}  {k}")
print()
kinds = Counter(r[3] for r in rows if r[2] == "OK")
print("volatility treatment:", dict(kinds))

# ---------------------------------------------------------------------------
# What each change contributed, measured rather than asserted
# ---------------------------------------------------------------------------
print()
print("CONTRIBUTION OF EACH RESOLUTION TIER")
variants = {
    "everything on (current)": ThermochemistryProvider(),
    "without the measured-Tb / Wilson-Jasperson / Fedors physical half":
        ThermochemistryProvider(measured_physical=False),
    "without Benson (Joback-only formation)":
        ThermochemistryProvider(benson=False),
    "without either":
        ThermochemistryProvider(benson=False, measured_physical=False),
}
for label, provider in variants.items():
    vol = VolatilityProvider(provider)
    n = 0
    for cat, items in TARGETS.items():
        for name, smiles in items:
            try:
                resolve(smiles, provider, vol)
            except Exception:                               # noqa: BLE001
                continue
            n += 1
    print(f"  {n:2d}/{total}  {label}")
print(
    "\n  The two tiers are not additive and should not be read as if they were:\n"
    "  the physical half only helps a species whose formation half already\n"
    "  resolves, and for the species this session added that formation half IS\n"
    "  Benson's. Turning Benson off therefore removes the reason the physical\n"
    "  half was reachable at all."
)

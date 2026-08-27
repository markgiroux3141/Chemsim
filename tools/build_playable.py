"""G3 -- render ``data/catalog/PLAYABLE.md``: what can a player make, from what?

The question no existing artefact asks. ``ROUTE_INDEX.md`` knows every route's
feedstocks but never asks whether the engine can run it; ``COVERAGE_REPORT.md``
knows what runs but never asks whether a feedstock is *obtainable*. Neither of
them answers *"what can I make starting from a rock?"*, which is the only
question the GOAL in MILESTONES § THE G-SERIES is stated in.

Run: ``python tools/build_playable.py``   (~1 min: it RUNS the deep chain)

## Why this one has to run a flask, when the other two do not

G1 measured ``benzene-nitration`` going from 0.1762 to 0.8000 mol on a change
that touched no species and no template, so **what a player can make is not a
property of the corpus alone**; G4 then found three routes its own static scorer
credited and a run refuted. So the tiers below are static, and every claim about
the *deepest* chain -- the one nothing else in the repo exercises -- is charged
into a real ``Vessel`` with its conditions printed beside the number.

⚠ **AND A YIELD IS A PROPERTY OF THE DECLARED CONSTANTS ON THE DAY, NOT OF THE
ROUTE (G6).** G6 changed no species, no template and no route and moved one
substrate's rate by 2400x. So every number printed in the runs section carries
its temperature, its charge, its tolerance and its catalyst loading, and the
report says what it ran. A yield here is evidence that a route *works*; it is not
a property of the corpus.

## The three rules, and every one of them was measured wrong first

1. **The target may not be CHARGED** -- G4's rule, in ``catalog.route_reachable``.
2. **The target must always be SHELVED.** Crediting a playable route with only
   ``route_roles.products`` loses ``lead-chamber``'s sulfuric acid, because the
   route's own fouling row consumes it and that makes it an *intermediate*. The
   same catalog row broke G4's scorer from the other side.
3. **A CATALYST IS A FEEDSTOCK.** A route whose catalyst nobody can make is not
   playable, and this is the rule that gives the corpus its third tier at all.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))
sys.path.insert(0, os.path.join(_ROOT, "validation"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import catalog as cat  # noqa: E402
import catalog_coverage as cc  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    UnifacProvider,
    VolatilityProvider,
    electrolyte_provider,
)
from chemsim.properties.mineral_data import MINERALS  # noqa: E402
from chemsim.reactions import (  # noqa: E402
    methanol_from_carbon_monoxide,
    water_gas_shift,
)
from chemsim.reactions.library import SOLID_CATALYST_REFERENCE  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402

T0 = time.time()

# ---------------------------------------------------------------------------
# THE ONE HAND JUDGEMENT IN THIS FILE, AND IT IS PRINTED SO IT CAN BE ARGUED WITH
# ---------------------------------------------------------------------------
# The rule: a species is NATURAL if a player could obtain it without running any
# chemistry -- dig it, pump it, breathe it, press it out of a plant or scrape it
# off an animal. Everything else has to be MADE. Nothing about the engine or the
# catalog decides this; it is a game-design decision about where the tech tree
# starts, and it is the single input that most changes the answer below.
NATURAL: dict[str, dict[str, str]] = {
    "air and water": {
        "water": "rain, a river, the sea",
        "oxygen": "air, 21%",
        "nitrogen": "air, 78%",
        "carbon-dioxide": "air, and every fire",
    },
    "native elements and rocks you can dig": {
        "sulfur-s8": "native sulfur, Sicilian or salt-dome",
        "carbon-graphite": "graphite, or charcoal from wood",
        "gold": "native metal, panned",
        "silver": "native metal",
        "sodium-chloride": "rock salt, or evaporated brine",
        "calcium-carbonate": "limestone, chalk, shell",
        "silicon-dioxide": "sand, quartz, flint",
        "iron-iii-oxide": "haematite ore",
        "aluminium-oxide": "bauxite",
        "calcium-fluoride": "fluorspar",
        "cryolite": "Ivigtut cryolite, mined until 1987",
        "copper-sulfide": "covellite ore",
        "lead-sulfide": "galena ore",
        "zinc-sulfide": "sphalerite ore",
        "iron-disulfide": "pyrite, fool's gold",
        "iron-ii-sulfide": "pyrrhotite",
        "mercury-sulfide": "cinnabar ore",
        "potassium-nitrate": "saltpetre from a nitre bed or a cave floor",
        "sodium-nitrate": "Chile saltpetre, caliche",
        "calcium-phosphate": "phosphate rock, and bone ash",
        "calcium-sulfate": "anhydrite",
        "gypsum": "gypsum rock",
        "magnesium-carbonate": "magnesite",
        "iron-ii-sulfate": "melanterite -- green vitriol weathers out of pyrite",
        "manganese-dioxide": "pyrolusite",
        "borax": "tincal, from a dry lake bed",
    },
    "pressed, fermented or scraped off something living": {
        "sucrose": "cane or beet",
        "glucose": "grape sugar, honey",
        "starch-unit": "grain, potato",
        "cellulose-unit": "cotton, wood pulp",
        "triolein": "olive oil",
        "oleic-acid": "tallow, olive oil",
        "tannic-acid-core": "oak gall, chestnut",
        "indican": "woad, indigo plant",
        "salicin": "willow bark",
        "eugenol": "clove oil",
        "alpha-pinene": "turpentine from pine resin",
        "citronellal": "citronella oil",
        "lignin-monomer-coniferyl": "wood lignin",
        "coal-marker": "coal seam",
        "collagen-marker": "hide, hoof, bone",
    },
}
NATURAL_IDS = {k for group in NATURAL.values() for k in group}

# What is deliberately NOT natural, and why -- the arguable half of the judgement.
NOT_NATURAL_NOTES = [
    ("the catalyst metals -- `nickel`, `cobalt`, `platinum`, `palladium`",
     "a player who cannot smelt them cannot have them, and nothing in the "
     "corpus smelts them. This is the rule that decides the third tier."),
    ("`iron` and `copper` and `aluminium` as METAL",
     "the ore is natural and the metal is not. `blast-furnace`, "
     "`copper-smelting` and `hall-heroult` are how you get them, and two of "
     "the three are the routes under test."),
    ("`methane`",
     "arguably natural gas, and calling it natural would light up "
     "`steam-reforming`. Left out because the corpus's own step reads it as a "
     "cracker product, and because a seep is not a bench reagent."),
    ("`benzaldehyde`, `malonic-acid`, `4-nitrophenol`, `bromoethane`",
     "the reagent bottle. Nothing in 173 industrial routes makes any of them, "
     "and they block four named syntheses -- see the fourth bucket."),
    ("`ethanol` and `acetic-acid`",
     "both are fermentation products and `fermentation` is a class M5 refused "
     "as a metabolic network rather than a transformation. They are natural in "
     "a brewery and not in this engine."),
]

# ---------------------------------------------------------------------------
compounds = cat.load_compounds()
routes = cat.load_routes()
steps = cat.load_steps()

_thermo = ThermochemistryProvider()
_vol = VolatilityProvider(_thermo)
# ⚠ HOIST THE PROVIDERS -- G4 measured 290 s against 18 s for building
# ``electrolyte_provider`` inside the comprehension.
_ionic = electrolyte_provider(base=_thermo, volatility=_vol)
_unifac = UnifacProvider()
_tier = {
    cid: cc.audit_compound(rec, _thermo, _vol, _ionic, _unifac)["tier"]
    for cid, rec in compounds.items()
}
TC = cc.TEMPLATE_CLASSES


def priced(x: str) -> bool:
    return x in compounds and _tier[x] != "refused"


def route_steps(rid: str) -> list[cat.Step]:
    return sorted((s for s in steps if s.route == rid), key=lambda s: s.index)


def needs(rid: str) -> set[str]:
    """What a player must ALREADY HOLD to attempt this route.

    ⚠⚠ **THIS IS NOT ``route_roles().feedstocks``, AND USING THAT WAS THE FIRST
    VERSION'S BUG.** ``route_roles`` calls a species that is both produced and
    consumed anywhere in the route an INTERMEDIATE, which is the right answer to
    the question ROUTE_INDEX asks and the wrong answer to this one. A player
    cannot start a route with an intermediate they have not made yet, so the
    question here is ORDER: a species is external if the route WANTS it at or
    before the step that first makes it.

    It cost two false credits, both of them cycles:

    * ``lime-cycle`` derives an EMPTY feedstock list -- limestone is regenerated
      by its own row 3 -- so it scored playable while needing nothing at all. A
      closed cycle is credited for free by any rule that reads roles.
    * ``lead-chamber`` wants nitrogen dioxide in row 2 and makes it in row 3, so
      the NOx carrier reads as an intermediate. **It is a starting charge**, and
      G4's own run of this route had to hand it 0.004 mol of NO2 by hand.

    ⚠ THE CATALYSTS ARE UNIONED IN. A route whose catalyst nobody in the corpus
    can make is not playable however good its chemistry is, and that rule is what
    gives this corpus a third tier rather than stopping at two.
    """
    mine = route_steps(rid)
    first_made: dict[str, int] = {}
    first_used: dict[str, int] = {}
    for s in mine:
        for p in s.products:
            first_made.setdefault(p, s.index)
        for x in s.reactants:
            first_used.setdefault(x, s.index)
    external = {x for x, i in first_used.items()
                if i <= first_made.get(x, 1 << 30)}
    return external | set(cat.route_roles(steps, rid).catalysts)


def needs_by_roles(rid: str) -> set[str]:
    """The rule above, done the wrong way, kept so §3 can price the difference."""
    roles = cat.route_roles(steps, rid)
    return set(roles.feedstocks) | set(roles.catalysts)


def shelves(rid: str) -> set[str]:
    """What running this route puts on the player's shelf.

    ⚠ THE TARGET IS UNIONED IN AND THAT IS NOT REDUNDANT. ``route_roles``
    classifies a species that is both produced and consumed as an INTERMEDIATE,
    and ``lead-chamber``'s row 4 consumes its own sulfuric acid to make chamber
    crystals -- the process's fouling product. Crediting products alone loses the
    acid, and with it ``saltpetre-nitric``. Same catalog row as G4's, opposite
    direction.
    """
    return {routes[rid].target} | set(cat.route_roles(steps, rid).products)


def reachable(rid: str) -> bool:
    return cat.route_reachable(steps, rid, routes[rid].target, priced, TC, compounds)


RUNNABLE = {rid for rid in routes if reachable(rid)}


def closure(pool=None, extra=frozenset(), with_catalysts=True, shelf_rule="both",
            needs_rule=None):
    """Iterate the tech tree to a fixed point. Returns (depth per route, shelf)."""
    pool = RUNNABLE if pool is None else pool
    nd = needs_rule or needs
    shelf = set(NATURAL_IDS) | set(extra)
    depth: dict[str, int] = {}
    d = 0
    while True:
        d += 1
        grew = False
        for rid in sorted(pool):
            if rid in depth:
                continue
            want = nd(rid)
            if not with_catalysts:
                want = want - set(cat.route_roles(steps, rid).catalysts)
            if want <= shelf:
                depth[rid] = d
                grew = True
        for rid, dd in depth.items():
            if dd != d:
                continue
            if shelf_rule == "target":
                shelf.add(routes[rid].target)
            elif shelf_rule == "products":
                shelf |= set(cat.route_roles(steps, rid).products)
            else:
                shelf |= shelves(rid)
        if not grew:
            return depth, shelf


PLAYABLE, SHELF = closure()
MADE_SOMEWHERE = {p for s in steps for p in s.products} | {
    r.target for r in routes.values()
}

# the four buckets -----------------------------------------------------------
GROUND = sorted(r for r, d in PLAYABLE.items() if d == 1)
DEEPER = sorted((d, r) for r, d in PLAYABLE.items() if d > 1)
BLOCKED, BOTTLE = [], []
for rid in sorted(RUNNABLE - set(PLAYABLE)):
    miss = sorted(needs(rid) - SHELF)
    orphan = [x for x in miss if x not in MADE_SOMEWHERE]
    (BOTTLE if orphan else BLOCKED).append((rid, miss, orphan))

# the work order -------------------------------------------------------------
UNRUNNABLE = set(routes) - RUNNABLE
FED_BUT_UNRUNNABLE = sorted(r for r in UNRUNNABLE if needs(r) <= SHELF)


# ---------------------------------------------------------------------------
# THE RUNS. Only the deep chain -- see the module docstring.
# ---------------------------------------------------------------------------
M = MINERALS
SPHALERITE, ZINCITE = M["sphalerite"].lattice, M["zincite"].lattice
COVELLITE, TENORITE, COPPER = (M["covellite"].lattice, M["tenorite"].lattice,
                               M["copper"].lattice)
GRAPHITE, HEMATITE = M["carbon-graphite"].lattice, M["hematite"].lattice
ZINC = "[Zn]"
CO, CO2, N2, O2, SO2, H2, H2O, MEOH = ("[C-]#[O+]", "O=C=O", "N#N", "O=O",
                                       "O=S=O", "[H][H]", "O", "CO")
TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)
_volatility = VolatilityProvider(_thermo)


def _net(species, templates=()):
    with contextlib.redirect_stdout(io.StringIO()):
        return build_network(species, list(templates), thermo=_thermo,
                            volatility=_volatility)


def run_chain() -> dict[str, float]:
    """The zinc retort, and the three routes that live off what it throws away."""
    out: dict[str, float] = {}

    # tier 1 -- the retort. S9/S10's own charge and conditions, unchanged.
    n = _net([SPHALERITE, ZINCITE, ZINC, GRAPHITE, CO, CO2, N2, O2, SO2])
    v = Vessel(n, volume=10.0, T=1400.0, T_env=1400.0, UA=1.0e4, k_vent=0.0)
    v.charge({SPHALERITE: 0.04, GRAPHITE: 0.20}, phase="solid")
    v.charge({O2: 0.06, N2: 0.06 * 79.0 / 21.0}, phase="gas")
    v.run(40000.0, **TIGHT)
    st = v.state()
    out["zinc"] = float(st.n_solid[ZINC] + st.n_liquid[ZINC]
                        + st.n_liquid2[ZINC] + st.n_gas[ZINC])
    out["co"] = float(st.n_gas[CO])
    out["so2"] = float(st.n_gas[SO2])

    # tier 2 -- the copper smelter, on the retort's own carbon monoxide
    n = _net([COVELLITE, TENORITE, COPPER, GRAPHITE, CO, CO2, N2, O2, SO2])
    for label, co_in in (("copper_1x", out["co"]), ("copper_2x", 2 * out["co"])):
        v = Vessel(n, volume=10.0, T=1500.0, T_env=1500.0, UA=1.0e4, k_vent=0.0)
        v.charge({COVELLITE: 0.04}, phase="solid")
        v.charge({CO: co_in, O2: 0.06, N2: 0.06 * 79.0 / 21.0}, phase="gas")
        v.run(40000.0, **TIGHT)
        out[label] = float(v.state().n_solid[COPPER])

    # tier 2 -- the shift, on the same carbon monoxide
    n = _net([CO, H2O, CO2, H2, HEMATITE], [water_gas_shift()])
    v = Vessel(n, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4, k_vent=0.0, kla=1.0)
    v.charge({H2O: 0.50})
    v.charge({CO: out["co"]}, phase="gas")
    v.charge({HEMATITE: 0.01}, phase="solid")
    v.run(3600.0, **TIGHT)
    out["h2"] = float(v.state().total(H2))

    # tier 3 -- methanol, gated on a catalyst the tier below had to smelt
    n = _net([CO, H2, MEOH, CO2, H2O], [methanol_from_carbon_monoxide()])

    def meoh(cu, co, h2, T=520.0):
        v = Vessel(n, volume=1.0, T=T, T_env=T, UA=1.0e4, kla=1.0, k_vent=0.0,
                   k_diss=0.0)
        v.charge({CO: co, H2: h2}, phase="gas")
        if cu:
            v.charge({COPPER: cu}, phase="solid")
        v.run(3600.0, **TIGHT)
        return float(v.state().total(MEOH))

    out["meoh_no_cu"] = meoh(0.0, out["co"], 2 * out["co"])
    out["meoh_smelted_cu"] = meoh(out["copper_1x"], out["co"], 2 * out["co"])
    out["meoh_ref_cu"] = meoh(SOLID_CATALYST_REFERENCE, out["co"], 2 * out["co"])
    out["gate"] = [(cu, meoh(cu, out["co"], 2 * out["co"]))
                   for cu in (1.0e-4, 1.0e-3, 1.0e-2, 2.0e-2)]
    # the same route at the corpus's OWN declared charge, 55x the scale
    out["meoh_corpus_scale"] = meoh(SOLID_CATALYST_REFERENCE, 3.0, 12.0)
    return out


print("running the deep chain (this is the slow part) ...")
CHAIN = run_chain()
print(f"  zinc {CHAIN['zinc']:.6f}  CO {CHAIN['co']:.6f}  "
      f"copper {CHAIN['copper_1x']:.6f}  H2 {CHAIN['h2']:.6f}  "
      f"methanol {CHAIN['meoh_smelted_cu']:.6f}    ({time.time() - T0:.0f} s)")


# ---------------------------------------------------------------------------
def name(x: str) -> str:
    c = compounds.get(x)
    return c.name if c else f"{x} (no molecular graph)"


def main() -> int:
    o: list[str] = []
    w = o.append
    n_goal = 40

    w("# PLAYABLE: what a player can make, and what they must start from")
    w("")
    w("*Generated by `tools/build_playable.py`. Do not edit.*")
    w("")
    w("The GOAL in `MILESTONES.md` § THE G-SERIES is stated as **~10 natural "
      "starting materials to ~40 targets, every one reachable from the ground**. "
      "This file is the only thing in the repo that scores against it.")
    w("")
    w("`ROUTE_INDEX.md` knows every route's feedstocks and never asks whether "
      "the engine can run it. `COVERAGE_REPORT.md` knows what runs and never "
      "asks whether a feedstock is *obtainable*. Neither answers **\"what can I "
      "make starting from a rock?\"**")
    w("")

    # --- 1 the answer ---------------------------------------------------
    w("## 1. The answer")
    w("")
    w("| tier | routes | what it means |")
    w("|---|---:|---|")
    w(f"| **1 — from the ground** | {len(GROUND)} | every feedstock and every "
      "catalyst is a natural material |")
    for d in sorted({d for d, _ in DEEPER}):
        k = sum(1 for dd, _ in DEEPER if dd == d)
        w(f"| **{d} — {d - 1} step{'s' if d > 2 else ''} up** | {k} | needs the "
          f"output of a tier-{d - 1} route |")
    w(f"| *runnable but unfed* | {len(BLOCKED) + len(BOTTLE)} | the engine can "
      "run it; nothing can supply it |")
    w(f"| *not runnable* | {len(UNRUNNABLE)} | see `COVERAGE_REPORT.md` |")
    w(f"| | **{len(routes)}** | |")
    w("")
    w(f"**{len(PLAYABLE)} of {len(routes)} named routes are playable from natural "
      f"materials**, against a goal of ~{n_goal} targets. The deepest chain in "
      f"the corpus is **{max(PLAYABLE.values())} tiers**.")
    w("")
    w("⚠ **THE TECH TREE IS A SHALLOW BUSH, NOT A TREE.** "
      f"{len(GROUND)} of the {len(PLAYABLE)} playable routes are tier 1 — they "
      "touch nothing another route made. The corpus is not a connected "
      "progression that happens to be short; it is a fan of one-step routes off "
      "the ground with one thin chain hanging off it, and §5 is that chain.")
    w("")

    # --- 2 the hand judgement -------------------------------------------
    w("## 2. The one hand judgement, printed so it can be argued with")
    w("")
    w("**The rule: a species is NATURAL if a player could obtain it without "
      "running any chemistry** — dig it, pump it, breathe it, press it out of a "
      "plant, or scrape it off an animal. Nothing about the engine or the "
      "catalog decides this. It is a game-design decision about where the tech "
      "tree starts, and **it is the single input that most changes every number "
      "in this file.**")
    w("")
    w(f"{len(NATURAL_IDS)} species are declared natural. The GOAL says ~10, so "
      "this list is already generous by a factor of four and the answer in §1 is "
      "an **upper** bound on playability, not a lower one.")
    w("")
    for group, members in NATURAL.items():
        w(f"**{group}** ({len(members)})")
        w("")
        w("| species | where a player gets it |")
        w("|---|---|")
        for cid, why in sorted(members.items()):
            w(f"| {name(cid)} `{cid}` | {why} |")
        w("")
    w("### What is deliberately NOT natural")
    w("")
    w("This half of the judgement is the arguable half, because every row here "
      "is a species that blocks a route the engine can already run.")
    w("")
    for what, why in NOT_NATURAL_NOTES:
        w(f"- **{what}** — {why}")
    w("")

    # --- 3 the rules -----------------------------------------------------
    d_t, _ = closure(shelf_rule="target")
    d_p, _ = closure(shelf_rule="products")
    d_nc, _ = closure(with_catalysts=False)
    d_roles, _ = closure(needs_rule=needs_by_roles)
    w("## 3. The four scoring rules, and every one was measured wrong first")
    w("")
    w("1. **The target may not be CHARGED** (G4's rule, in "
      "`catalog.route_reachable`) — or every recycle loop in the corpus scores "
      "reachable. `bayer-process` purifies bauxite; `contact-process` recycles "
      "its own acid.")
    w("2. **A need is decided by ORDER, not by `route_roles`** — a species is "
      "external if the route wants it at or before the step that first makes it. "
      "Otherwise a closed cycle needs *nothing* and is playable for free.")
    w("3. **A route shelves its target AND its byproducts** — the target unioned "
      "in explicitly, because a route's target is not always among its products.")
    w("4. **A catalyst is a feedstock** — a metal nobody can smelt is not free.")
    w("")
    w("Rules 2 and 3 are two axes and they had to be measured as a grid, "
      "because **they interact**:")
    w("")
    w("| | shelf = target only | + byproducts | + target unioned in |")
    w("|---|---:|---:|---:|")
    for label, nd in (("needs = `route_roles` *(wrong)*", needs_by_roles),
                      ("needs = **order** *(correct)*", needs)):
        cells = []
        for rule in ("target", "products", "both"):
            # NOT ``o`` -- that is the output buffer, and shadowing it here wrote
            # a 200-byte file of route names instead of the report. Caught by
            # ``test_the_report_on_disk_matches_the_code`` on its first run,
            # which is the whole argument for asserting a generated artefact.
            grid, _ = closure(shelf_rule=rule, needs_rule=nd)
            cells.append(f"{len(grid)} / depth {max(grid.values())}")
        w(f"| {label} | " + " | ".join(cells) + " |")
    w("")
    w(f"⚠⚠⚠ **THE BOTTOM-RIGHT CELL IS THE ANSWER ({len(PLAYABLE)}), AND THE TWO "
      "CELLS BESIDE IT ARE EQUAL — WHICH IS THE FINDING.** Under the correct "
      "needs rule, shelving byproducts-only costs *nothing*, so the fouling-row "
      "bug in rule 3 is **invisible**. It is only visible along the top row, "
      "where it is worth one route. **Two of the four rules were wrong at once "
      "and fixing the first one masked the second.** Had the needs rule been "
      "fixed first, rule 3 would have looked like a distinction without a "
      "difference and gone in wrong — and it would have started costing routes "
      "silently the moment the lead chamber became reachable.")
    w("")
    w("⚠⚠⚠ **THREE OF THE FOUR ROWS ARE THE SAME TWO CATALOG ROUTES, READ FROM "
      "THREE DIFFERENT SIDES — AND ONE OF THEM IS THE ROUTE G4 ALREADY FOUND.**")
    w("")
    w("- G4 found `lead-chamber` row 4 — the nitrosylsulfuric acid that fouls a "
      "chamber — making its *row* scorer call the route blocked. "
      "The same row makes `route_roles` classify sulfuric acid as an "
      "**intermediate**, so a shelf built from `products` alone does not contain "
      "the thing the route exists to make. **A route's target is not always "
      "among its products.**")
    w("- And `lead-chamber` row 2 wants nitrogen dioxide, which row 3 makes, so "
      "the NOx carrier reads as an intermediate too — **when it is a starting "
      "charge.** G4's own run of this route had to hand it 0.004 mol of NO₂ by "
      "hand and then measured it recovered. See §6.")
    w("- `lime-cycle` derives an **empty** feedstock list, because its row 3 "
      "regenerates the limestone row 1 calcined. Under the roles rule it scored "
      "playable while needing *nothing at all*.")
    w("")
    w("⚠ **AND THE THIRD BULLET IS WHY THE ACID FALLS OFF THE SHELF TWICE OVER.** "
      "The lead chamber is blocked on its NOx charge before the fouling row ever "
      "gets a chance to matter, which is exactly the masking the grid shows.")
    w("")
    w(f"⚠⚠ **AND THE FIX MOVED THE HEADLINE DOWN, FROM {len(d_roles)} TO "
      f"{len(PLAYABLE)}.** That is the fourth time in this project that "
      "correcting a coverage instrument lowered its own number — M1, G4, and now "
      "twice inside one file. **A scoreboard that only ever goes up is not "
      "measuring anything.**")
    w("")
    w("⚠ **AND THE CATALYST RULE IS WHAT MAKES THE TREE THREE DEEP AT ALL.** "
      f"Without it {len(d_nc)} routes are playable and the tree is "
      f"{max(d_nc.values())} tiers; with it {len(PLAYABLE)} are, and there is a "
      "third tier holding exactly one route. Dropping the rule frees "
      "`haber-bosch` (iron) and `hydrogenation-margarine` (nickel) — two metals "
      "nothing in 173 industrial routes makes.")
    w("")

    # --- 4 the tiers -----------------------------------------------------
    w("## 4. The tiers, route by route")
    w("")
    for d in sorted(set(PLAYABLE.values())):
        ids = sorted(r for r, dd in PLAYABLE.items() if dd == d)
        w(f"### Tier {d} ({len(ids)})")
        w("")
        w("| route | target | needs | puts on the shelf |")
        w("|---|---|---|---|")
        for rid in ids:
            got = sorted(shelves(rid) - {routes[rid].target})
            w(f"| `{rid}` | {name(routes[rid].target)} | "
              f"{', '.join(sorted(needs(rid)))} | "
              f"**{routes[rid].target}**"
              + (f", {', '.join(got)}" if got else "") + " |")
        w("")
    w(f"After every tier has run, the shelf holds **{len(SHELF)} species** "
      f"(the {len(NATURAL_IDS)} natural ones plus "
      f"{len(SHELF) - len(NATURAL_IDS)} made).")
    w("")

    # --- 5 the runs ------------------------------------------------------
    c = CHAIN
    w("## 5. The runs: the deep chain, end to end")
    w("")
    w("⚠ **EVERY NUMBER HERE IS A PROPERTY OF THE DECLARED CONSTANTS ON THE DAY "
      "AND OF THE CONDITIONS BESIDE IT, NOT OF THE ROUTE (G6).** G6 changed no "
      "species, no template and no route, and moved one substrate's rate by "
      "2400x while leaving three nitration yields identical to four decimals. A "
      "yield below is evidence that a route *works*. It is not a corpus "
      "property, and it will move under sessions that were not about it.")
    w("")
    w("The other tier-1 routes are exercised elsewhere — `zinc-smelting`, "
      "`copper-smelting` and `lead-smelting` in `validation/smelting.py`, "
      "`lead-chamber`, `tanning-route` and `starch-hydrolysis` in "
      "`validation/granularity.py`, `lime-cycle` in `tests/test_solid_state.py`, "
      "`mercury-from-cinnabar` in `tests/test_mercury_retort.py`, `chloralkali` "
      "in `validation/cell_potentials.py`, and `invert-sugar`, "
      "`salicin-hydrolysis` and `methanol-synthesis` in "
      "`examples/named_routes.py`. **What nothing else runs is the CHAIN**, so "
      "that is what this section runs.")
    w("")
    w("### Tier 1 — the zinc retort, and the thing it throws away")
    w("")
    w("*10 L sealed, 1400 K, 40 000 s, rtol 1e-8 / atol 1e-11. Charge: "
      "sphalerite 0.04 mol + graphite 0.20 mol solid, O₂ 0.06 mol + N₂ 0.2257 "
      "mol gas. S9's and S10's own charge, unchanged.*")
    w("")
    w("| species | mol | |")
    w("|---|---:|---|")
    w(f"| zinc | {c['zinc']:.6f} | the target |")
    w(f"| **carbon monoxide** | **{c['co']:.6f}** | **a byproduct, and the "
      "whole of tiers 2 and 3** |")
    w(f"| sulfur dioxide | {c['so2']:.6f} | a byproduct |")
    w("")
    w("⚠ **THE RETORT MAKES MORE CARBON MONOXIDE THAN ZINC "
      f"({c['co']:.6f} AGAINST {c['zinc']:.6f} MOL), AND NOTHING ELSE IN THE "
      "PLAYABLE SET MAKES ANY.** It is the only carbon-monoxide source a player "
      "can reach, it is not charged — carbon burns in the blast and the "
      "Boudouard reaction hands the CO back — and **three tier-2 routes and one "
      "tier-3 route all want it**. A reachability scorer says \"carbon monoxide "
      "is on the shelf\" and attaches no quantity to that at all.")
    w("")
    w("### Tier 2 — the copper smelter, on the retort's own carbon monoxide")
    w("")
    w("*10 L, 1500 K, 40 000 s, rtol 1e-8. Charge: covellite 0.04 mol solid, "
      "O₂ 0.06 mol + N₂ 0.2257 mol, and the CO above rather than a bottle.*")
    w("")
    w("| CO charged | copper | |")
    w("|---:|---:|---|")
    w(f"| {c['co']:.6f} | {c['copper_1x']:.6f} | one retort's worth |")
    w(f"| {2 * c['co']:.6f} | {c['copper_2x']:.6f} | two retorts' worth |")
    w("")
    w("**Doubling the carbon monoxide changes the copper in the sixth decimal**, "
      "so this charge is ore-limited and not CO-limited: one retort already pays "
      "for a 0.04 mol charge of copper ore with CO to spare. That is worth "
      "stating because it is the *opposite* of what the contention above "
      "suggests, and only running it settles which.")
    w("")
    w("### Tier 2 — the water-gas shift, on the same carbon monoxide")
    w("")
    w("*1 L, 700 K, 3600 s, rtol 1e-8. Charge: water 0.50 mol liquid, "
      f"CO {c['co']:.6f} mol gas (the retort's own), haematite 0.01 mol solid.*")
    w("")
    w(f"→ **hydrogen {c['h2']:.6f} mol.** ⚠ And it CONSUMES the carbon monoxide "
      "to get there. The shift and the smelter and the methanol synthesis are "
      "not three routes sharing a shelf entry; they are three claims on one "
      "retort's gas.")
    w("")
    w("### Tier 3 — methanol, and the catalyst is the gate")
    w("")
    w("*1 L, 520 K, 3600 s, rtol 1e-8. Charge: "
      f"CO {c['co']:.6f} + H₂ {2 * c['co']:.6f} mol gas (1:2, the "
      "stoichiometric ratio), copper in the solid block.*")
    w("")
    w("| copper / mol | methanol / mol | conversion |")
    w("|---:|---:|---:|")
    w(f"| 0 | {c['meoh_no_cu']:.6f} | **nothing at all** |")
    for cu, m in c["gate"]:
        w(f"| {cu:.4f} | {m:.6f} | {100 * m / c['co']:.2f}% |")
    w(f"| {c['copper_1x']:.6f} | {c['meoh_smelted_cu']:.6f} | "
      f"{100 * c['meoh_smelted_cu'] / c['co']:.2f}% — **smelted at tier 2** |")
    w(f"| {SOLID_CATALYST_REFERENCE} | {c['meoh_ref_cu']:.6f} | "
      f"{100 * c['meoh_ref_cu'] / c['co']:.2f}% — the declared reference |")
    w("")
    w("⚠⚠ **THE ENTIRE THIRD TIER OF THIS CORPUS IS ONE COPPER CATALYST.** "
      "Methanol needs no tier-2 *reagent*: its carbon monoxide is tier 1 and its "
      "hydrogen is tier 1 too, because `chloralkali` throws hydrogen off as a "
      "byproduct of making caustic soda from rock salt. It is tier 3 for exactly "
      "one reason — **its catalyst has to be smelted first, and smelting it "
      "needs the byproduct of smelting a different metal.** Grant a player free "
      "copper and methanol moves to tier 2 and the corpus has no third tier "
      "left.")
    w("")
    w(f"⚠ **AND THE GATE SATURATES WELL BELOW THE SMELTER'S OUTPUT.** "
      f"{c['gate'][2][0]:.2f} mol of copper already reaches "
      f"{100 * c['gate'][2][1] / c['meoh_ref_cu']:.1f}% of the reference rate, "
      f"so the {c['copper_1x']:.4f} mol one ore charge yields is about "
      f"{c['copper_1x'] / c['gate'][2][0]:.0f}x more catalyst than the route "
      "needs. **The catalyst is a gate and not a rate multiplier** (see "
      "`chemsim-solid-gate-fix`), so a player needs to reach copper and does "
      "not need to stockpile it.")
    w("")
    w(f"⚠⚠ **WHAT DOES BITE IS SCALE, AND IT IS THE POINT OF RUNNING ANY OF "
      f"THIS.** At the retort's own scale the conversion is "
      f"{100 * c['meoh_smelted_cu'] / c['co']:.1f}%. The same route, same "
      f"template, same catalyst loading, at the corpus's own declared charge of "
      f"3 mol CO + 12 mol H₂ gives **{c['meoh_corpus_scale']:.6f} mol — "
      f"{100 * c['meoh_corpus_scale'] / 3.0:.1f}%**. Methanol synthesis is "
      "pressure-driven, and one zinc retort is not a pressure vessel. "
      "**\"Reachable\" and \"worth doing\" are different questions and the "
      "static scoreboard can only answer the first.**")
    w("")

    # --- 6 the buckets ---------------------------------------------------
    w("## 6. What blocks the rest")
    w("")
    w(f"### Blocked on something the corpus MAKES but cannot RUN ({len(BLOCKED)})")
    w("")
    w("These are the routes a player can see the shape of and not reach. Each "
      "one is runnable today and waiting on a route that is not.")
    w("")
    w("| route | target | missing |")
    w("|---|---|---|")
    for rid, miss, _ in BLOCKED:
        w(f"| `{rid}` | {name(routes[rid].target)} | {', '.join(miss)} |")
    w("")
    w("⚠⚠ **THE MOST IMPORTANT ROW IN THAT TABLE IS `lead-chamber`, AND IT IS "
      "BLOCKED ON A PINCH.** The lead chamber is the 18th century's sulfuric "
      "acid and G4 measured it running end to end from native sulfur — but its "
      "NOx carrier is *catalytic*, so it needs a starting charge of nitrogen "
      "dioxide that it then recovers, and **nothing a player can reach makes "
      "any.** Three routes in the corpus make NO₂ — `birkeland-eyde`, "
      "`ostwald-process` and the lead chamber itself — and none of the first two "
      "is runnable. Historically the charge came from saltpetre, and the corpus "
      "has saltpetre as a natural material and **no step that turns it into "
      "NOx**. So this is a *corpus* gap and not an engine one, and it is one of "
      "the two most valuable single species in the file — see §7, where it ties "
      "with aluminium at the top.")
    w("")
    w(f"### Blocked on a reagent bottle ({len(BOTTLE)})")
    w("")
    w("Nothing in 173 named industrial routes makes these at all, so no amount "
      "of engine work reaches them. They are a **corpus** gap, and the cheapest "
      "of the four buckets to close: a route that makes benzaldehyde would free "
      "three of the four.")
    w("")
    w("| route | the bottle | also waiting on |")
    w("|---|---|---|")
    for rid, miss, orph in BOTTLE:
        rest = [x for x in miss if x not in orph]
        w(f"| `{rid}` | **{', '.join(orph)}** | {', '.join(rest) or '—'} |")
    w("")

    # --- 7 the lever -----------------------------------------------------
    from collections import Counter

    blockers: Counter[str] = Counter()
    for rid in sorted(RUNNABLE - set(PLAYABLE)):
        for x in needs(rid) - SHELF:
            blockers[x] += 1
    gains = []
    for x in blockers:
        gains.append((len(closure(extra={x})[0]) - len(PLAYABLE), blockers[x], x))
    gains.sort(reverse=True)
    w("## 7. Is there a lever? No — and the frequent blocker is not the "
      "valuable one")
    w("")
    w("Grant a player one species free and re-run the fixed point. "
      f"Base is {len(PLAYABLE)}.")
    w("")
    w("| grant | playable | gain | routes it blocks |")
    w("|---|---:|---:|---:|")
    for g, n, x in gains[:10]:
        w(f"| {x} | {len(PLAYABLE) + g} | {g:+d} | {n} |")
    w("")
    best_g = gains[0][0]
    best_xs = [x for g, _, x in gains if g == best_g]
    w(f"⚠ **THE BIGGEST SINGLE GRANT IS {best_g:+d}** "
      f"({', '.join(f'`{x}`' for x in best_xs)}), which is the same shape as the "
      "coverage report's finding that there is no lever — 47 routes one class "
      "away from 37 different classes. **Playability has no lever either**, and "
      "that is worth having measured rather than assumed: the two scoreboards "
      "disagree about almost everything else.")
    w("")
    freq = blockers.most_common(1)[0]
    freq_gain = next(g for g, _, x in gains if x == freq[0])
    w(f"⚠⚠ **AND THE MOST FREQUENT BLOCKER IS NOT THE MOST VALUABLE ONE.** "
      f"`{freq[0]}` blocks {freq[1]} routes and granting it is worth "
      f"{freq_gain:+d}, because every route it blocks is blocked by something "
      "else as well. **A histogram of blockers is not a work order** — the "
      "fixed point is, and they disagree.")
    w("")

    # --- 8 the work order ------------------------------------------------
    w("## 8. The work order this file exists to produce")
    w("")
    w(f"**{len(FED_BUT_UNRUNNABLE)} of the {len(UNRUNNABLE)} routes the engine "
      f"cannot run are ALREADY FED from the shelf above.** A template built for "
      "one of these lights up the tech tree the moment it lands. A template "
      f"built for the other {len(UNRUNNABLE) - len(FED_BUT_UNRUNNABLE)} moves a "
      "coverage number and no player can reach it.")
    w("")
    w("⚠ **THIS IS THE ONLY RANKING IN THE REPO THAT IS ABOUT PLAYABILITY "
      "RATHER THAN COVERAGE**, and it is what the C-series should take its order "
      "from. `COVERAGE_REPORT.md`'s greedy set-cover curve maximises classes "
      "covered per template; this maximises routes a player can actually walk "
      "to. They are not the same list.")
    w("")
    w("**Ranked by what each one is WORTH**: grant it, re-run the fixed point, "
      "and count. The gain includes the route itself, so `+1` means it unblocks "
      "nothing else.")
    w("")
    w("| worth | route | target | classes needed | refused species |")
    w("|---:|---|---|---|---|")
    rows = []
    for rid in FED_BUT_UNRUNNABLE:
        bad = sorted({s.cls for s in route_steps(rid) if s.cls not in TC})
        ref = sorted({x for s in route_steps(rid)
                      for x in s.reactants + s.products
                      if x in compounds and not priced(x)})
        gain = len(closure(pool=RUNNABLE | {rid})[0]) - len(PLAYABLE)
        rows.append((gain, len(bad), rid, bad, ref))
    rows.sort(key=lambda t: (-t[0], t[1], t[2]))
    for gain, _, rid, bad, ref in rows:
        w(f"| **{gain:+d}** | `{rid}` | {name(routes[rid].target)} | "
          f"{', '.join(f'`{b}`' for b in bad) or '— *none*' } | "
          f"{', '.join(ref) or '—'} |")
    w("")
    top_gain, _, top_rid, top_bad, top_ref = rows[0]
    w(f"⚠⚠ **THE TOP ROW IS `{top_rid}` AT {top_gain:+d} FOR ONE CLASS**, and "
      "the chain it opens is the deepest one available: aluminium unblocks "
      "`thermite`, thermite's iron unblocks `haber-bosch`. ⚠ Its class "
      f"(`{top_bad[0] if top_bad else '—'}`) is the one the coverage queue "
      "already records as **engine** work — *\"a MELT is not a phase this "
      "project has\"* — and its cryolite is refused a price, so the cheapest "
      "row in the table is not the top one.")
    w("")
    only_species = [r for r in FED_BUT_UNRUNNABLE
                    if not {s.cls for s in route_steps(r)} - set(TC)]
    w(f"⚠⚠ **{len(only_species)} OF THEM NEED NO TEMPLATE AT ALL** — every class "
      "they use is already covered and they are blocked purely on a species the "
      f"engine refuses to price: {', '.join(f'`{r}`' for r in only_species)}. "
      "**That is a data job, not a chemistry job**, and `pyrite-roasting` in "
      "particular is blocked on exactly the entry the engine queue already "
      "records as source-blocked — pyrite has an enthalpy in WEBBOOK and an "
      "entropy in nothing. **A data refusal is now measurably a playability "
      "blocker and not just a coverage one.**")
    w("")
    ceiling, _ = closure(pool=RUNNABLE | set(FED_BUT_UNRUNNABLE))
    w("### The ceiling, and it is the goal")
    w("")
    w(f"Grant **all {len(FED_BUT_UNRUNNABLE)}** of them and the fixed point "
      f"reaches **{len(ceiling)} playable routes** at depth "
      f"{max(ceiling.values())} — because four more routes fall out for free "
      "once the shelf grows: "
      f"{', '.join(f'`{r}`' for r in sorted(set(ceiling) - set(PLAYABLE) - set(FED_BUT_UNRUNNABLE)))}.")
    w("")
    w(f"⚠⚠⚠ **THAT IS THE GOAL, AND IT IS NOW A FINITE NAMED LIST.** The G-series "
      f"goal is ~40 targets reachable from the ground; this corpus tops out at "
      f"**{len(ceiling)}** on the natural list in §2, and the entire distance "
      f"from today's {len(PLAYABLE)} to that {len(ceiling)} is the "
      f"{len(FED_BUT_UNRUNNABLE)} rows above. **The C-series is not an open-ended "
      "grind against 173 routes; it is this table.** Everything outside it is "
      "coverage work that no player can reach until something in it lands "
      "first.")
    w("")

    # --- footer ----------------------------------------------------------
    w("## What this file does NOT license")
    w("")
    w("- **A yield is not a corpus property.** §5's numbers move whenever a "
      "declared constant moves. Read them with their conditions or not at all.")
    w("- **`RUNNABLE` cannot ask whether a number is RIGHT** (S7). Every route "
      "in §4 produces its target; none of it says the amount is what a real "
      "process gives.")
    w("- **The tiers rest on §2's hand judgement.** Argue with that list and "
      "every number here moves. That is why it is printed.")
    w("- **`COVERAGE_REPORT.md`'s BOTH column is not re-scored here**, and this "
      f"file's {len(RUNNABLE)} runnable routes include G4's five. See "
      "MILESTONES §G4 §6 for why a hand judgement does not go into a mechanical "
      "column.")
    w("")
    w(f"*{len(routes)} routes, {len(compounds)} compounds, "
      f"{len(NATURAL_IDS)} declared natural, {len(RUNNABLE)} runnable, "
      f"{len(PLAYABLE)} playable, {max(PLAYABLE.values())} tiers deep.*")

    path = os.path.join(cat.CATALOG_DIR, "PLAYABLE.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(o) + "\n")
    print(f"wrote {path}")
    print(f"  {len(PLAYABLE)} playable of {len(routes)}, "
          f"{max(PLAYABLE.values())} tiers, {len(FED_BUT_UNRUNNABLE)} fed but "
          f"unrunnable   ({time.time() - T0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

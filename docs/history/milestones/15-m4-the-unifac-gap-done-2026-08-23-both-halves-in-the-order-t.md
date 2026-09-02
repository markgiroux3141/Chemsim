## M4 — The UNIFAC gap  ✔ **DONE 2026-08-23 — both halves, in the order the measurement put them: the flag first, the matcher second**

41% of molecular organics had no group decomposition, which silently set
γ = 1. A missing template *refuses*; this *lied*, and it lied about phase
separation — the mechanic every workup runs on. That framing stood. What the
measurement added, before anything was built, is that "the gap" was never one
problem, and the half the section led with had a hard ceiling.
`validation/unifac_gap.py` is the measurement and now also the verification; it
runs in about a minute.

**Coverage: 730 → 764 of 1155 organics, 63.2% → 66.1%.**

### ⚠⚠ The important half: silence was not a neutral default, it was an argument

`numerics/lle.py` has always said, as a virtue, that **an ideal liquid never
splits** — the tangent-plane test returns "stable" for free with no group
parameters. Put that next to "a neutral species with no decomposition is held at
γ = 1" and the omission is not noise around the right answer: **everything held
ideal argues for one phase, and the answer it argues for is exactly the one
`Vessel.lle_report()` used to return as the empty string.**

It now says so, in all three branches — including the stable-single-phase one
that used to be silent:

    this liquid is stable as one phase -- but 14.3% is NEUTRAL species with no
    UNIFAC decomposition, held at gamma = 1 rather than computed
    (O=S(=O)(O)O 0.143). An ideal liquid never splits, so that verdict is the
    one the missing model was always going to give

⚠ **And the two-layer case prints the signature of the lie beside the warning:**
water/toluene/sulfuric acid comes out with H₂SO₄ at **0.058 mole fraction in
BOTH layers**, because equality of activity with γ = 1 on both sides of an
interface is equality of MOLE FRACTION. The same failure the Born term was built
to fix for ions, still running for neutrals, now visible rather than inferable.

**The threshold was bounded arithmetically and the bound said something.**
Water/toluene 3:1 at 298.15 K and at the 358.31 K of the steam distillation,
fifteen third components each added at mole fraction `f` and the tangent-plane
test run twice — once modelled, once forced ideal:

| held ideal | displacement per unit `f` | |
|---|---:|---|
| acetone, ethers, esters, alcohols, DMSO | **0.03 – 0.25** | belongs in the MAJOR layer |
| DCM, chloroform, benzene, hexane, cyclohexane, heptane | **0.99 – 3.46** | belongs in the MINOR layer |

⚠ **The slopes do not scatter, they split in two, and the boundary is which
layer the species belongs in.** A species held ideal is not merely given the
wrong γ — `activity_coefficients` drops it out of the group composition every
OTHER species' γ is computed against, so a hydrocarbon that ought to DEFINE the
organic layer is kept out of the layer it defines.

⚠ **And there is no dead zone:** the displacement is LINEAR in `f` down to
0.0005, so there is no fraction below which the model becomes correct, only one
below which the error is too small to print. That is what makes the threshold a
REPORTING decision, stated as one: `lle_report` prints mole fractions to three
decimals, so `IDEAL_FRACTION_REPORT = 0.01 / IDEAL_TIE_LINE_SENSITIVITY =
0.01 / 3.46 = 0.003`. For scale at the other end, sweeping to `f = 0.6`, the
stable/unstable **verdict** never flipped below an ideal mole fraction of
**0.44**.

⚠ **Ions are not counted**, and `ActivityArrays.report()` now lists them
separately too. An ion at γ = 1 is a stated policy with the Born term doing the
part that decides partitioning; a neutral at γ = 1 is a gap. Running them
together made the gap look like the policy.

### The matcher half: two fixes, and the second one's safety is an ordering

* **(a) the ketone SMARTS, +14.** `CH3CO` was `[CX4;H3][CX3](=O)` with no `;H0`
  on the carbonyl carbon, so the KETONE group matched an ALDEHYDE, won the
  greedy pass by being the larger match, and stranded the aldehyde hydrogen —
  the tally check then refused the whole molecule, which is it doing its job. It
  cost the entire aliphatic aldehyde series, ethanal through dodecanal. Added to
  the `_SMARTS_CORRECTIONS` mechanism that already existed; ketones verified
  unmoved; `unifac_data`'s docstring claim that the patterns *are* thermo's is
  corrected, and `test_only_the_documented_patterns_differ_from_the_oracle`
  enumerates all ten divergences.
* **(b) a backtracking fallback, +20.** Priority says which group is PREFERRED,
  not which is POSSIBLE, so greedy can eat an atom the only workable cover
  needed elsewhere. `fragmentation._search` is a depth-first search over covers
  with the atom tally bounded by the formula at every node.

⚠⚠ **What makes (b) safe in a matcher Joback also uses is not what it finds, it
is WHEN IT RUNS: only after the greedy pass has been refused.** For any molecule
that fragments today the search is unreachable, so it can turn a refusal into an
answer and can never turn one answer into another. Measured over the catalog:
**Joback unmoved at 1057 species, zero gained and zero changed**; Benson does not
use this matcher. ⚠ And a search that exhausts its budget refuses with a
*different message* — "I did not find a cover" is not "there is no cover".
Measured, nothing comes close: deepest success 18 nodes, most expensive refusal
718, budget 20 000, 0.01 s of search over the whole catalog.

### ⚠ We stop three short of the planned ceiling, on purpose

The 66.4% ceiling was thermo's number on the identical patterns. We reach
**66.1%**, and the three species thermo still decomposes are three it gets by
counting hydrogens off the MOLECULE instead of off the GROUP — `CF2` onto a CHF₂
carbon, the whole-molecule `FURFURAL` group onto a substituted furan, and the
ether group `CH3O` onto a methoxy RADICAL (caught by one of our own documented
pattern corrections). **A refusal is the right answer three times.** The
transferable form: *a number measured off another implementation is a
measurement of that implementation, not a target.*

### What is still missing, named

391 organics still have no decomposition, and `unifac_gap.py` PANEL 2 names them
by unassigned atom environment: 171 carbonyl oxygens outside the
ketone/aldehyde/ester/acid/amide set (anhydrides, acid chlorides, ureas,
carbonates), 75 sulfonyl oxygens, 91 aromatic nitrogens outside a pyridine RING,
nitrate esters, phosphates. Ethene and ethyne have no UNIFAC-VLE decomposition at
all. **None of it is an oversight — it is the edge of a 1975 table, and going
past it means a different model (Dortmund, NIST-UNIFAC) with its own
combinatorial term. That is the basis error M3 exists as the warning about: a
separate, argued decision, not a table merge.**

---

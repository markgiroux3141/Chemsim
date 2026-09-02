## R1 -- AN UNPRICEABLE SPECIES BECOMES A REPORTED COVERAGE LIMIT. ✔✔ **DONE 2026-09-01, AND IT CHANGED THE ANSWER RATHER THAN JUST THE FAILURE MODE.**

Drop it, do not expand it, notice it -- exactly as `max_species`,
`max_molar_mass` and `generations` already behave, on the same
`_ExpansionState.reports` channel, carried on `ReactionNetwork.notices` and
published through `Snapshot`. **Nothing deeper than one generation is safe until
this exists** (finding 5).

⚠⚠ **THERE IS A REAL DESIGN QUESTION INSIDE IT AND IT MUST BE ARGUED, NOT
WRAPPED IN A `try`/`except`.** A species that cannot be priced **is not in the
model**, so dropping it changes what is in the flask -- and `GAME_DESIGN.md` §3
forbids that being silent. The argument that makes it admissible is the same one
§8.2 makes for the generation bound: *the limit is a choice the moment the
player can see it.* Which means the notice has to name the species, name which
half of its record resolved, and say what would fix it (a measured boiling point
in `properties/physical_data.py`) -- the refusal already says all three, so the
work is routing it rather than writing it.

⚠ And it must drop **the reaction, not just the species**, the way the
`max_molar_mass` branch in `_expand_once` already does with `too_big` -- a
half-registered reaction whose product has no thermochemistry is worse than
either alternative.

### WHAT WAS BUILT

`network/builder.py` grew a **fourth reported coverage limit**, on exactly the
channel the other three use. `_unpriceable` screens every NEW product BEFORE
`_concrete_reactions` runs, because pricing is what that call does; a species no
provider can price is recorded against its own refusal in
`_ExpansionState.unpriced`, the whole rewrite is dropped the way the `too_big`
branch drops one, and `_ExpansionState.reports` emits a notice that is printed
AND carried on `ReactionNetwork.notices` -> `Snapshot.notices`. The structured
companion is **`ReactionNetwork.unpriced`**, a `{smiles: refusal}` map on the
same footing as `unexpanded`.

The notice quotes the refusal **verbatim** for the first three species, because
the refusal already names the species, says which half of its record resolved,
and says what would fix it -- so the work was ROUTING it, not writing it,
exactly as this milestone predicted. `_NOTICE_REASONS = 3` because a refusal runs
~400 characters and twelve of them is a notice that has hidden itself in its own
length.

### ⚠⚠⚠ THE CRASH WAS HIDING THE REAL ANSWER, AND THAT IS THE FINDING

A traceback reports the FIRST refusal and stops. Closing it showed the picker's
own pick is not one species:

    picker rows '5-HMF' + 'oxygen', generations=1
      aerobic_oxidation                 2,5-diformylfuran
      ether_condensation                its ether dimer
      friedel_crafts_hydroxyalkylation  three bis-furylmethanes
      ------------------------------------------------------------
      5 species dropped, 5 rewrites discarded, and the flask has
      8 species and **ZERO REACTIONS**

**The engine cannot price ANY chemistry it can find between 5-HMF and oxygen.**
That is a fact about the pick that the exception could not state, and it is a
different fact from "something went wrong". *A crash says a thing failed; a
notice says what is missing and what would fix it, and only the second is a
limit a player can act on.* ⚠ It also re-prices the earlier write-up: the
handoff called this *"deeper exploration crashes"*, panel 5E corrected that to
*one generation off the picker's own roster*, and R1 corrects it again to
**five species from three templates**.

### ⚠⚠ THE DESIGN QUESTION WAS NOT THE ONE THIS MILESTONE PREDICTED

It predicted the hard part would be arguing that dropping a species is
admissible at all -- it touches matter, which §3 forbids being silent -- and that
argument is §8.2's and went in as written. **The hard part was that ONE PROVIDER
RAISES TWO REFUSALS AND ONLY ONE OF THEM IS A COVERAGE LIMIT.**

    no thermochemistry available    NO SOURCE IN THIS PROJECT prices this
                                    species, with any provider.  A DATA gap.
    OutsideEstimatorDomain          THIS provider is the wrong one.  The
                                    species IS priceable and the message says
                                    by what.  A SETUP gap.

Treating them alike is what the first implementation did, and it **broke two
green tests**, which is how the distinction was found rather than argued:

* `test_granularity.py::test_saponification_fires_on_the_catalog_s_own_substrate`
  -- saponification under a NEUTRAL provider makes a stearate ion that
  `electrolyte_provider()` prices perfectly well. 5 reactions became 0.
* `test_furans.py::test_the_kolbe_cascade_needs_its_generation_cap_declared`
  -- the kolbe dianion, which that file pins as a RAISE.

So the element floor's refusal is passed through untouched, and the fix is a
**type**, not a string match: `properties/thermochemistry.OutsideEstimatorDomain`,
a `ValueError` subclass, so every existing `except ValueError` still catches it
and nothing else changed by adding it. Both tests went green again **with no
test edits**, which is the evidence that the distinction is the code's and not
the tests'.

⚠ **AND THE REASON THE SETUP GAP IS SAFE TO PASS THROUGH IS MEASURED, NOT
ASSUMED.** `VolatilityProvider` short-circuits a charged species to non-volatile
*before* consulting thermochemistry, which is why an ionic product under a
neutral provider has always built rather than raised. The one path that does
price it is a REVERSIBLE template, and `_concrete_in_phase` already catches that
and re-raises naming the reaction, the phase and the provider to use. **A loud
refusal that names its own fix is the right answer to a misconfigured network;
a missing MEASUREMENT is the one nobody can act on, and that is the only one
that drops.**

### WHAT IT COST AND WHAT IT DID NOT

Nothing. `ThermochemistryProvider.get` caches on success, so a species that
survives the screen is priced once and read from the cache by the reaction
construction two lines later; `state.unpriced` is consulted first and is the
failure cache the provider does not keep. `validation/shelf.py` panel 5E is
rewritten from *"if this line prints, R1 is done"* to asserting the notice, and
four tests are pinned in `tests/test_robustness.py` -- the file whose docstring
is *every state a player can reach must WORK, or REFUSE CLEANLY WITH A REASON.*

### ⚠⚠ AND THE AUDIT R1 OWED FOUND A NUMBER THAT HAD BEEN WRONG FOR THREE SESSIONS

`validation/tolerance_audit.py` was owed from P4 and from R1 -- both are network
CONSTRUCTION. Eleven of its twelve rows held byte-for-byte. `workshop` came back
**1.95e-04** against a standing record of **1.98e-04** stable across P1 and C7.

Three causes were refuted before the real one was found: **not R1** (all four of
`workshop`'s networks report `unpriced` empty, and a worktree at HEAD already
reads 1.95e-04), **not BLAS threading** (capped twice and uncapped once, all
1.95e-04 -- so R2's capping is numerically neutral here), **not noise** (it is
deterministic in every repeat). Bisected to **`05609c4`, P3+P4**.

⚠⚠⚠ **THE MOVED LINE IS A JSON SAVE-FILE SIZE IN BYTES.**

    save = 10113 bytes of JSON      P2 and before
    save = 10237 bytes of JSON      P4 and after

**The loose/tight gap is 2 bytes in both and never changed** -- the saved JSON
holds a float whose decimal form is two characters longer at rtol 1e-8. What
moved is the DENOMINATOR: P4's six new `TemplateSpec` fields grew every save file
by 124 bytes, so 2/10113 became 2/10237. **`workshop`'s default-tolerance stdout
is byte-identical across those commits**, which is the proof. *That row was never
evidence about convergence; every session that quoted 1.98e-04 was quoting the
size of a JSON blob.*

Fixed in the instrument, on the file's own precedent: it already excises a wall
clock as a TOKEN because the first version manufactured a `wait_until` finding
out of *"0.07 s of wall"*. A serialized size is the same class of number, so
`scrub` now takes both -- and the module **asserts its own behaviour on import**,
because both findings this audit has ever manufactured came out of `scrub` rather
than out of a solver. ⚠ `1.25 bar` survives the size pattern only through its
trailing ``, which is load-bearing and is now asserted.

**New standing record** (thread-capped; `serious` unchanged at two):

    activity            1 line    1.28e-03   <-- quotable digits move
    multistep_prep      8 lines   1.07e-03   <-- quotable digits move
    workshop            1 line    1.33e-04   (was 2 lines / 1.98e-04)
    wait_until          4 lines   1.03e-04
    vessel              2 lines   2.40e-05
    competing_pathways  1 line    1.77e-05
    named_routes        RAISES -- the diagnosed entry, unchanged
    esterification, lime_cycle, roasting_and_the_catalyst_gate,
    mercury_retort      0 lines, and mercury_retort at 1.00x is the
                        harness's own self-check

⚠ **The lesson is the one this audit already taught once**: *an instrument that
cannot tell a wall clock from a result will manufacture findings.* It took three
sessions of a stable wrong number and a full bisect to notice it was doing it
again with a byte count -- and the only reason it was catchable is that the
number had been WRITTEN DOWN.

## R3 -- WIRE OR DELETE `Scenario.prune_threshold`  *(~30 min)*  ✔ **DONE 2026-09-01: DELETED, SAVE_VERSION 9**

It is declared, documented as *"0 disables pruning (structural discovery)"*,
round-trips through `to_dict`/`from_dict` into every save file, and **reaches
nothing** -- `build_network` has no pruning parameter at all. Its partner
`T_build` **is** wired, to `T_ref`. **A save-file field that does nothing is a
lie in the format**, and it is the same class as P4's `TemplateSpec` bug: a
field a frontend can set, that the engine never sees.

⚠ Deleting it is a `SAVE_VERSION` bump. Wiring it is R4. **Do not leave it as it
is**, which is the only option that is wrong on its own terms.

### WHAT WAS DECIDED (2026-09-01): DELETED, AND THE ARGUMENT IS STRUCTURAL

**The field could not be wired honestly even if R4 shipped tomorrow, because
it sits on the wrong class.** The machinery it gestured at already exists and
is DORMANT -- `discovery.refine_network` (Layer 4.5), zero callers and zero
tests, which already implements exactly R4's defensible form: promote an edge
species by k x the CONCENTRATIONS ACTUALLY CHARGED, integrating the core-only
network to get them. Its signature is the tell -- it takes `feed:
{SMILES: mol/L}`. **A `Scenario` does not contain the charge**: vessels are
filled by script EVENTS after the world is built, so at `World.__post_init__`
-- the only place a Scenario-resident threshold could act -- there is nothing
to evaluate a rate against. If R4 ships, its knob belongs wherever the charge
lives (the bench pick, or a rebuild-after-charging), not on `Scenario`; the
note where the field used to be says so.

So: field, `to_dict` and `from_dict` entries deleted; `SAVE_VERSION` 8 -> 9,
**the only version that REMOVES a field and the only one where every old save
would replay bit-identically** -- the bump is for the format's contract (a v8
producer could set the field believing it pruned), not the bytes. `T_build`'s
comment lied too ("temperature used for rate-aware pruning") and now says what
it does: the `T_ref` the network's thermochemistry is priced at.
`tests/test_protocol.py` now pins the scenario dict's **key SET** -- P4's
set-of-fields discipline pointed the other way, so the next dead field has to
edit a test to get in. Five version pins moved 8 -> 9 (all already compared
against the CONSTANT, P4's `test_stock` lesson holding); the stale-version
loops learned `8`. Targeted: 42/42 across the six save-format files, ruff
clean. ⚠ Not owed: the suite (nothing read the field, so no trajectory can
move -- the pins were the blast radius and they were run) and the tolerance
audit (no RHS edit, and no argument `build_network` receives changed).

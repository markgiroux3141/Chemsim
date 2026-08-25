We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M12, S1, S2 and S3 are DONE.**

**START WITH: `mercury-from-cinnabar`'s second step.** It is the most interesting
thing left on the list and the cheapest real EMERGENCE. `cinnabar-roasting`
already gives montroydite, and montroydite decomposes at the same heat to the
metal, which M6's term already does — so roast-then-decompose would be
**emergent**, the way M6's carbonation was: two declarations, a mechanic nobody
wrote. It needs mercury curated as a species — a LIQUID at room temperature and a
gas in a retort, so its ideal-gas record is a real vaporisation number. Curation,
not research.

⚠ **AND THAT ROUTE IS THE ONE S1 RE-LABELLED `roasting-to-metal` BECAUSE IT WAS
FALSELY CREDITED.** If you build this, the re-label is what gets reversed — so
re-read S1's mistake 3 and S3's landmine below before touching the class name.

After that, in order:

1. **The `LAYER_REABSORB`-style honest diagonal on the gas block.** S2 widened
   the case: the zero-Jacobian-column trap has TWO triggers, and one of them
   means `oil_of_vitriol` cannot be run at a tight tolerance at all. Hot loop,
   moves invariants, wants a session of its own.
2. **Pyrite** — one mineral entry from `pyrite-roasting` running. Blocked on the
   same-database rule (`Hfs` in WEBBOOK, `S0s` in nothing), which is a rule worth
   keeping, so this needs a SOURCE and not a workaround.
3. **⚠ `hydrolysis` IS NOW GREEDY RANK 4 — AND READ S3's LANDMINE FIRST.**
   Measured: it unlocks **exactly ONE route alone, `vitriol-distillation`**, and
   that route's step 1 reads `-> iron-ii-OXIDE` while the engine makes HEMATITE.
   The whole standalone payoff of the 4th-ranked template is a route carrying a
   step whose product the engine does not make. Build it with that in hand.
4. **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
   re-scope before scheduling)**, then **M8+ (electrochemistry — ⚠ that one WILL
   break the spectator zeros)** and **M10 (the site balance S1 did not build)**.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§S1, §S2 and §S3 are the ones to read**: S1's brief
  asked for one mechanism and the arithmetic said two, S2 had to audit its own
  instrument before its findings could be trusted, and S3 found that the
  instrument's own OUTPUT was not diffable.
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1, 86 is S2, 87 is
  S3.**
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **S3's split of
  `thermal-decomposition`**, and `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-surface-reactions,
  chemsim-solid-state-reactions, chemsim-zero-jacobian-column,
  chemsim-tolerance-audit and chemsim-generated-artefacts.

```bash
python validation/tolerance_audit.py         # S2's standing audit, ~8 min
python examples/roasting_and_the_catalyst_gate.py   # S1, five panels, ~11 s
python examples/lime_cycle.py                # M6, eight panels, ~17 s
python examples/named_routes.py              # M5's 17 routes, ~24 s
python validation/rate_ceiling.py            # M12's standing audit, seconds
python validation/catalog_coverage.py        # 35/218, 27/173, ~3 min
python tools/build_route_index.py            # ⚠ RUN THIS TOO -- see below
python -m pytest -q tests/test_surface.py        # S1's 38 tests, ~12 s
python -m pytest -q tests/test_solid_state.py    # M6's 31 tests, ~24 s
python -m pytest -q                          # the whole suite, 797 tests, ~11:50
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE IS MINUTES OF SATURATED CPU ON THE USER'S OWN MACHINE.** Run it to
establish a baseline and to verify at the end, not after each change. Say what a
long run will cost before starting one. The tolerance audit is another ~8 minutes.

⚠⚠ **THE FULL SUITE HAS STILL NOT BEEN RE-RUN SINCE S1's LAST FIX.** It last ran
**796 passed / 1 failed in 11:50**; the failure was real, is fixed, and the fixed
file passes in a targeted run — but the green number is not measured. S2 then
touched `examples/workshop.py`. S3 touched **no `src/` file at all** (one line in
`validation/catalog_coverage.py`, data labels and docs) and re-ran
`test_surface.py` + `test_solid_state.py` green at **69 passed in 35 s**. Re-run
the suite before quoting a green number.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 34 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, and a catalyst you have to actually put
in the flask. `SAVE_VERSION` is **5**.
Coverage: **27/173 template-ready routes**, **35/218 classes**, **34 templates**.

---

# ⚠⚠ WHAT S3 TURNED OUT TO BE: THE SPLIT WAS THE EASY HALF

The brief was "split `thermal-decomposition`, +2 classes for four rows
re-labelled, no engine work". All of that was true and it took twenty minutes.
**Both covering mechanisms were already declared, under exactly the two names the
split needed** (`sulfate-thermal-decomposition`,
`bicarbonate-thermal-decomposition` in `properties/solid_state.py`), and both
RUN. Measured: **33/215 → 35/218 classes, 95 → 97 steps, and 27 → 27 routes.**

**The two findings worth carrying are both about the INSTRUMENT, not the split.**

## ⚠⚠ 1. THE COVERAGE REPORT WAS NOT BYTE-STABLE, SO IT COULD NOT BE DIFFED

Regenerating `COVERAGE_REPORT.md` at HEAD — the project's own rule, because a
committed generated report is not a baseline — produced a **17-line diff with
every single number identical.** `sorted(covered, key=lambda x:
-step_classes[x])` sorts a **SET** with no tie-break, so classes with equal step
counts came out in `PYTHONHASHSEED` order. The `missing` table eight lines below
it already had `(-count, name)`; this one had been missed since the file was
written.

⚠ **A REPORT YOU CANNOT DIFF IS A WEAK INSTRUMENT.** Seventeen lines of noise per
regeneration is more than enough to hide a real one-line change in review — which
is exactly what regenerating the file is *for*. Fixed in one line and verified
S2's way: **byte-identical across `PYTHONHASHSEED=0` and `=1`**. It was the only
unstable site (the greedy `max` already carried a `c` tie-break; the dict-item
sorts are insertion-ordered). **If a regeneration produces a diff now, that diff
is real.**

## ⚠⚠ 2. AND THE OTHER GENERATED FILE WAS STALE BY THREE MILESTONES

`ROUTE_INDEX.md` had **not been regenerated since the initial commit**, while
`route_steps.psv` was re-labelled by M5, M6 and S1. Regenerating it moved **21
class labels: 11 from M5, 5 from M6, 1 from S1 and 4 from S3.**

⚠ **It is the one generated file no audit reads** — `catalog_coverage.py` parses
`route_steps.psv` directly — so a stale index changes no measured number, fails no
test, and warns nobody. Anyone who read the index to find a step's class between
M5 and S3 got a pre-M5 answer. The standing rule was "a committed generated report
is not a baseline"; **what S3 adds is that the rule has to cover the artefact
NOTHING CHECKS, because that is the one that rots in silence.**

---

# ⚠⚠ THE MISTAKES AND NEAR-MISSES. THESE ARE THE VALUABLE PART.

**1. ⚠⚠ THE STANDING "WHICH ROUTES DID IT MOVE" CHECK PAID OFF — BY PREDICTING
ZERO AND BEING RIGHT.** S1's third mistake (a coverage number moving is not
evidence the engine moved) is now run BEFORE crediting rather than after. All four
affected routes are blocked on a SECOND uncovered class — `hydrolysis`,
`carbonate-equilibrium`, `trimerisation`, `dissolving-metal-reduction` — so no
route could move, and none did. **Predict the number, then measure it; a
prediction that comes out right is how you know the model of the instrument is
right.**

**2. ⚠⚠ A GREEDY-CURVE RANK IS NOT A STANDALONE UNLOCK.** The old report showed
`thermal-decomposition` at rank 14 with "+1 route", and that +1 exists only
because `hydrolysis` was added at rank 6. Read as a standalone promise it would
have delivered a route it cannot. **The standalone table is the one that answers
"what does this class unlock", and it never listed the class at all.** Same
misreading as S1's, arriving from a different table.

**3. ⚠⚠ THE CREDIT THAT IS HONEST FOR THE OPPOSITE REASON TO THE ONE THAT WASN'T.**
`vitriol-distillation` step 1 reads `-> iron-ii-OXIDE`; the declaration makes
HEMATITE. That looks exactly like S1's false credit and is not:

  * **cinnabar** — the ROW is right (a retort does give the metal) and the
    mechanism stops short of it, so the row needs a second reaction nobody built.
    NOT covered.
  * **green vitriol** — the MECHANISM is right and the ROW is wrong. FeO does not
    survive red heat. Nothing further is needed to reach the real products, so the
    step IS covered.

**Being able to tell those two apart is the entire value of the check.** "The
mechanism does not make the row's product" is not by itself a verdict — you have
to ask WHICH of the two is wrong.

**4. `sed -i` DESTROYED A CRLF FILE ON THE FIRST EDIT OF THE SESSION.** One
intended line change came out as **826 insertions and 826 deletions** — Git Bash
`sed -i` rewrote every ending. The repo is MIXED and this one is CRLF. Reverted
and redone with a binary-mode anchored patcher that never decodes. **Check
`git diff --stat` after the first edit to a file, every time.**

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ S3's LANDMINE: A LATENT FALSE CREDIT WITH A MEASURED FUSE.**
`sulfate-thermal-decomposition` is credited, and `vitriol-distillation` step 1
still names a product this engine never makes. Inert **today** only because step 2
`hydrolysis` is uncovered so the route cannot go template-ready.

⚠⚠ **AND THE FUSE IS SHORT, MEASURED: `hydrolysis` unlocks exactly ONE route
alone, and it is `vitriol-distillation`.** The whole standalone payoff of the
4th-ranked template is the landmine route. The corpus row is deliberately NOT
corrected, on the `diels-alder-route` precedent — inventing chemistry inside an
audit corpus is not allowed, and correcting this one means re-balancing to
2 FeSO4 and adding an SO2 nobody wrote.

**2. ⚠⚠ THE ZERO-JACOBIAN-COLUMN TRAP HAS TWO TRIGGERS, AND ONE MAKES AN EXAMPLE
UNRUNNABLE.** Documented as *a species in the network but absent from a sealed
flask*: the column is identically zero, `num_jac`'s perturbation factor inflates
to inf, BDF gets a NaN Jacobian. S2 found the second: **a TIGHT TOLERANCE on a
flask holding a trace.** `oil_of_vitriol` RAISES at rtol 1e-8 in
`burn(690 K, s8=0.002, o2=0.10)` — `lu_factor` gets `array must not contain infs
or NaNs` after 50.7 s of thrashing. ⚠ Its numbers are CONFIRMED, not suspect:
SO2 = 0.016000 at the default and 0.016000 at rtol 1e-8 with a 1e-9 mol trace
charged. **The fix is item 1 on the list above.** ⚠ A declared solid CATALYST does
not trip it — its column is populated even at zero amount and what is zero is its
ROW, which is what a catalyst should be.

**3. THE DEFAULT TOLERANCE, BOUNDED RATHER THAN OPEN.** S2 swept it: **ZERO
examples print a quotable digit that moves**, 5 move below 0.1%, 6 are identical.
⚠ `validation/tolerance_audit.py` is a STANDING audit: run it after touching the
RHS, and it self-checks (`lime_cycle` and `roasting_and_the_catalyst_gate` must
come out byte-identical at speedup 1.00).

**4. ⚠ `detailed_balance`'s RATE CAP COMPARES A CATALYSED PRE-EXPONENTIAL AGAINST
A LIMIT THAT IS NOT IN ITS UNITS**, so it would fire 10x too eagerly. Bounded in
the class this project forgives, and **it does not fire on any of the five
catalysed templates**, pinned by a test. `validation/rate_ceiling.apparent_A`
undoes the units and the audit is at baseline (`ammonia_synthesis_rev` crosses at
**1335.1 K**; raw it reads 1178.1 K, which is the units error).

**5. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever, so
ten times the iron is ten times the rate. Right at low coverage, wrong at high.
M10.

**6. NOT EXPRESSIBLE: NUCLEATION** — S3 named this one. `SurfaceArrays` is first
order and EXTENSIVE in the solid amount, so a solid at **zero mol has zero rate
for ever**, and the term is irreversible by construction, so no roasting row can
be run backwards to deposit one. **Depositing a solid from no solid cannot be
written here at all**, which is why `hydride-thermal-deposition`
(`arsine -> arsenic + hydrogen`) is a mechanism gap and not just a missing
template.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's clamp is
`T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Fifteen times now.
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS — AND THEN AUDIT ITS OUTPUT.** S2's
harness invented a 12.5% finding; S1's coverage audit credited a route that cannot
run; S3's report could not be diffed and its sibling index had rotted for three
milestones. **Three sessions running, the instrument was the story.**
⚠ **A GENERATED FILE NOTHING READS IS THE ONE THAT ROTS.** Regenerate all three
catalog artefacts, not just the one whose numbers you are quoting.
⚠ **PREDICT THE NUMBER BEFORE YOU MEASURE IT.** S3 predicted +2 classes and +0
routes and got exactly that; the prediction is what makes the measurement
evidence rather than a reading.
⚠ **A PHASE LABEL CARRIES A STANDARD STATE.** Adding one is a thermodynamic
change, not a naming change.
⚠ A CLASS IS A MECHANISM CLAIM. Read the rows, not the name — and check which
ROUTES a credit moves. When a mechanism does not make a row's product, ask which
of the two is WRONG before deciding the verdict.
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS, and neither is a
converged-looking number at the default tolerance. Re-measure before quoting.
⚠ Windows console is cp1252: a warning glyph inside a `print()` kills a script.
Docstrings fine, printed text ASCII. (EIGHTEEN sessions running.)
⚠⚠ **`sed -i` REWRITES EVERY LINE ENDING IN A CRLF FILE.** S3 lost a file to it on
its first edit — 826/826 on a one-line change. This repo is MIXED: markdown and
`.psv` are CRLF, most Python is LF, `validation/catalog_coverage.py` is CRLF while
`src/chemsim/vessel/vessel.py` is LF. Use a binary-mode anchored patcher that
reads the anchor and replacement from FILES (so no shell or heredoc can eat a
backslash) and never decodes. **Check `git diff --stat` after the first edit to
any file.**
⚠ **HEREDOCS EAT ESCAPES:** `\\n` written into a `python - <<'PY'` heredoc arrives
as `\n` and becomes a real newline inside a Python string, so an anchored patch
silently matches nothing. Use the Write tool for anything containing a backslash,
and run it as a file.
⚠ An em dash in a markdown anchor will not match a `--` you typed. MILESTONES.md
uses both.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u` — and
do not pipe a long run through `tail`, which holds everything until EOF.

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays; RDKit stays in matter.
NO silent approximations. REFUSE loudly rather than return a confident wrong
number — and a LATENT fragility is a third case: report it, do not refuse it.
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?"
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; `solid_state=False`
exactly no crystal reacting; `surface=False` exactly no gas attacking one, and an
all-zero `order_solid` exactly the old kinetics kernel; the Born term exactly
zero in PURE water; the five pH values; SAVE_VERSION stores the CONDITION, never
the instant; every gaseous element reference state Hf = Gf = 0 EXACTLY; every
METAL Hf = Gf = 0 EXACTLY on the solid basis, and a non-zero result REFUSED as an
allotrope mismatch; a reference state its own database does not price at Hf = 0
is REFUSED; no mineral pricing differently under the two providers; `ion_data`
and `electrolyte` never subtracted from each other; a declared rate order may
never be reversible; a surface row whose `ln K` is under +20 is REFUSED; the
reflux ratio is the ratio of two drain conductances out of one condenser,
declared rather than inferred; the fragmentation SEARCH runs only after the
greedy pass has been REFUSED; an ion is never counted in the held-ideal flag; a
rate CAP scales BOTH pre-exponentials by one factor; a template that moves a
hydrogen ATOM must collapse explicit Hs; a declared catalyst is a CONSTANT OF THE
MOTION — bit for bit, at every charge; the tolerance audit's two self-check
examples come out byte-identical; **`COVERAGE_REPORT.md` comes out byte-identical
across `PYTHONHASHSEED` values**;
**a lattice may REACT and may never DISSOLVE — the fusion law is still 407x wrong
in both directions, and neither M6 nor S1 nor S3 softened that by one digit.**

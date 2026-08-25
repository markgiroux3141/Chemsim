We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M12, S1 and S2 are DONE.**

**START WITH: split `thermal-decomposition`.** It is the cheapest honest coverage
left in the corpus, it needs NO engine work, and M6 read it and ran out of session
rather than doubting the reading. Its four rows are **four mechanisms**, so by M1's
standard the label is an outcome label. Two of the four are already covered by M6's
term, so the split is **+2 classes for four rows re-labelled**.

⚠ **AND READ S1's THIRD MISTAKE BEFORE YOU CREDIT ANYTHING** (below): crediting a
class moved a route into the template-ready list on the strength of a mechanism
that does not make that route's product. When you split this class, check WHICH
routes the number moves, not just that it moved.

After that, in order:

1. **`mercury-from-cinnabar`'s second step** — the most interesting thing on the
   list. `cinnabar-roasting` already gives montroydite, and montroydite
   decomposes at the same heat to the metal, which M6's term already does. So
   roast-then-decompose would be **emergent**, the way M6's carbonation was: two
   declarations, a mechanic nobody wrote. It needs mercury curated as a species —
   a LIQUID at room temperature and a gas in a retort, so its ideal-gas record is
   a real vaporisation number. Curation, not research.
2. **The `LAYER_REABSORB`-style honest diagonal on the gas block.** S2 widened the
   case for this: the zero-Jacobian-column trap now has TWO triggers, and one of
   them means `oil_of_vitriol` cannot be run at a tight tolerance at all. Hot
   loop, moves invariants, wants a session of its own.
3. **Pyrite** — one mineral entry from `pyrite-roasting` running. Blocked on the
   same-database rule (`Hfs` in WEBBOOK, `S0s` in nothing), which is a rule worth
   keeping, so this needs a SOURCE and not a workaround.
4. **M7 (dissociation as an equilibrium — ⚠ M12 took most of its case away;
   re-scope before scheduling)**, then **M8+ (electrochemistry — ⚠ that one WILL
   break the spectator zeros)** and **M10 (the site balance S1 did not build)**.

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan. ⚠ **§S1 and §S2 are the ones to read**: S1's brief asked
  for one mechanism and the arithmetic said two, and S2 had to audit its own
  instrument before its findings could be trusted.
HANDOFF.md — what exists, and the ethos to preserve. **Item 85 is S1, 86 is S2.**
NEXT_SESSION.md — the invariants table at the bottom is the contract. ⚠ Read the
  two warnings above it before trusting any row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, including **S1's re-label of
  `mercury-from-cinnabar`**, and `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially chemsim-surface-reactions,
  chemsim-solid-state-reactions, chemsim-zero-jacobian-column and
  chemsim-tolerance-audit.

```bash
python validation/tolerance_audit.py         # S2's standing audit, ~8 min
python examples/roasting_and_the_catalyst_gate.py   # S1, five panels, ~11 s
python examples/lime_cycle.py                # M6, eight panels, ~17 s
python examples/named_routes.py              # M5's 17 routes, ~24 s
python validation/rate_ceiling.py            # M12's standing audit, seconds
python validation/catalog_coverage.py         # 33/215, 27/173, ~3 min
python -m pytest -q tests/test_surface.py        # S1's 38 tests, ~12 s
python -m pytest -q tests/test_solid_state.py    # M6's 31 tests, ~24 s
python -m pytest -q                          # the whole suite, 797 tests, ~11:50
python -m ruff check src tests examples validation tools
```

⚠ **THE SUITE IS MINUTES OF SATURATED CPU ON THE USER'S OWN MACHINE.** Run it to
establish a baseline and to verify at the end, not after each change. Say what a
long run will cost before starting one. The tolerance audit is another ~8 minutes.

⚠⚠ **AND THE FULL SUITE HAS NOT BEEN RE-RUN SINCE S1's LAST FIX OR S2 AT ALL.** It
ran **796 passed / 1 failed in 11:50**; the failure was real, is fixed, and the
fixed file passes in a targeted run — but the green number is not measured. S2
then touched `examples/workshop.py`. Re-run before quoting a green suite.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a plate
column that reaches its purity target, an ionic lattice that can leave solution, a
solvent mixture that says when it was never modelled, an energy balance it can
report the way it reports a mass one, 34 templates, a reaction that happens INSIDE
a crystal, a gas that ATTACKS a crystal, and a catalyst you have to actually put in
the flask. `SAVE_VERSION` is **5**.
Coverage: **27/173 template-ready routes**, **33/215 classes**, **34 templates**.

---

# ⚠⚠ WHAT S1 TURNED OUT TO BE: A PHASE LABEL CARRIES A STANDARD STATE

S1's brief said: add `PHASE_INDEX["solid"] = 2`, and treat a solid catalyst and a
roasting sulfide as ONE mechanism, because "both are `nu` on the solid block".
**Both halves are refuted, by arithmetic done before any code.**

**A CATALYST'S STOICHIOMETRY IS ZERO ON BOTH SIDES**, so its `delta` never leaves
the gas block — only its EXPONENT reaches the solid one. That is one extra `(r, n)`
matrix, `KineticArrays.order_solid`.

⚠⚠ **AND THE PHASE LABEL IS NOT A NAME.** `reaction_deltas` applies the
pure-liquid standard-state shift to any phase that is not `"gas"`:

| `N2 + 3 H2 -> 2 NH3` | dH / kJ/mol | dG / kJ/mol | K(500 K) |
|---|---:|---:|---:|
| `phase="gas"` | -91.880 | -32.820 | 2.683e+03 |
| `phase="solid"` | -114.769 | -132.542 | 7.019e+13 |
| shift | **-22.889** | **-99.722** | **x 2.616e+10** |

That is verbatim the failure the `PHASE_INDEX` comment was written to prevent —
`phase="any"` validated, documented, and silently meaning liquid — arriving at
the line that comment sits on. A solid-catalysed gas reaction IS a gas-phase
reaction: every participant with an activity is a gas, and a pure solid's is 1.
Roasting cannot take the label either, because `thermochemistry` refuses a lattice
by name, so it cannot be priced on the ideal-gas basis at all.

⚠⚠ **`PHASE_INDEX` HAS TWO ENTRIES AFTER TWO MILESTONES THAT EACH EXPECTED TO ADD
A THIRD, FOR DIFFERENT REASONS.** M6's: *the kernel cannot express this rate law*.
S1's: *the label would change the thermodynamics*. `builder.PHASE_INDEX`'s comment
carries both.

**Five mechanics nobody wrote:** a sealed roast STALLS (1.53% in 20 ks — a litre of
air holds 2.296 mmol of O2 and 0.1 mol of ore needs 150), a blown one goes
(78.26%), **autothermal roasting** (insulated, 100% while heating itself 1100 →
1908.6 K, the VENT the only thing stopping the runaway), two ores sharing one blast
(0.039131 mol each, closures exact to 1e-12), and a clock that ignores the charge.

---

# ⚠⚠ SIX MISTAKES FROM THE LAST TWO SESSIONS. THESE ARE THE VALUABLE PART.

**1. AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT.**
`A_cat * SOLID_CATALYST_REFERENCE == A_folded` exactly, so the catalysed and
folded templates must agree. In a VENTED flask they differ by **+0.086%** — and
the first explanation offered (displaced volume) was tested by enlarging the flask
and **made it worse**, because the two runs vent differently. SEALED, with the
flask enlarged by the 0.0007096 L that 0.1 mol of iron occupies: **-4.6e-11 mol**.
The residual IS displaced volume; the vent was hiding it.

**2. A RATE CLAIM MEASURED AS A YIELD MEASURES TWO THINGS.** "Ten times the
catalyst is ten times the rate" reads 9.75 after a 1 s run — that 2.5% is
DEPLETION. Off the RHS via `energy_terms` it is 10.0 to 1e-9.

**3. ⚠⚠ A COVERAGE NUMBER MOVING IS NOT EVIDENCE THE ENGINE MOVED.** Crediting
`roasting` as M6 labelled it moved `mercury-from-cinnabar` into the template-ready
list — and that row reads `... -> mercury + sulfur-dioxide` while the term makes
the OXIDE. **M6 had recorded the reading** ("one template will not cover that row
honestly") and not acted on it. Re-labelled `roasting-to-metal`. ⚠ And the one
route that remains added — `pyrite-roasting` — does not run either. **Honest
summary of S1's coverage: +1 class, +1 template-ready route, ZERO new routes that
run end to end.** CHECK WHICH ROUTES A CREDIT MOVES.

**4. ⚠⚠ AN INSTRUMENT THAT CANNOT TELL A CLOCK FROM A RESULT MANUFACTURES
FINDINGS.** S2's first version reported `wait_until` moving **12.5%**, and that
was `0.07 s of wall` against `0.08 s of wall`; the real worst move is **1.04e-4**.
Wall clocks are now excised as TOKENS, not by dropping the line — because this
project prints physics and timing together (`t = 1353.13 s ... (0.89 s of wall)`),
so dropping the line hides the move in `t`. And keying on the word "wall" would
have been actively wrong: `lime_cycle` prints `±14.374 W wall`, a heat flux.

**5. ⚠⚠ "THE TIGHT RUN IS ALSO FASTER" DOES NOT GENERALISE.** M6 measured it
(1.4–3.3 s against 5–13 s), S1 measured it again (3.67 against 19.94 s), and it
was on its way into being a rule. Swept across 11 examples: **faster in 2, slower
in 9, worst 7.2x.** Each local measurement was right; the pattern is not there.
Tightening usually COSTS time — budget for it.

**6. "IT MOVED" AND "IT REFUSED" ARE DIFFERENT FINDINGS.** `oil_of_vitriol` cannot
be swept at all, and its numbers are still correct. Putting those in one row would
have read as "the example is wrong", which it is not.

---

# ⚠ THE FRAGILITIES, AND WHAT S2 LEARNED ABOUT THE BIGGEST ONE

**1. ⚠⚠ THE ZERO-JACOBIAN-COLUMN TRAP HAS TWO TRIGGERS NOW, AND ONE OF THEM MAKES
AN EXAMPLE UNRUNNABLE.** It was documented as *a species in the network but absent
from a sealed flask*: the column is identically zero, `num_jac`'s perturbation
factor inflates to inf, and BDF gets a NaN Jacobian. S2 found the second: **a
TIGHT TOLERANCE on a flask holding a trace.** `oil_of_vitriol` RAISES at rtol 1e-8
in `burn(690 K, s8=0.002, o2=0.10)` — `lu_factor` gets
`array must not contain infs or NaNs` on `I - c J` after 50.7 s of thrashing.

⚠ **Its numbers are CONFIRMED, not suspect**, and the diagnostic is the original
one: SO2 = **0.016000** at the default, **0.016000** at rtol 1e-8 with a 1e-9 mol
trace of SO2 charged, 0.016001 with 1e-6 mol, **0.016000** at rtol 1e-7. A trace
of the absent species removes the failure and the answer does not move.

**THE FIX IS ITEM 2 ON THE LIST ABOVE**: a `LAYER_REABSORB`-style honest diagonal
on the gas block. Hot loop, moves invariants, wants a session of its own — and it
is now worth more than it was, because it unblocks running an example at all.

⚠ **A declared solid CATALYST does not trip it**, measured: its column is
populated even at zero amount (the gas rates depend on it with slope
`k prod(C**order)`), and what is zero is its ROW — which is what a catalyst should
be.

**2. THE DEFAULT TOLERANCE, NOW BOUNDED RATHER THAN OPEN.** S2 swept it: **ZERO
examples print a quotable digit that moves**, 5 move below 0.1%, 6 are identical.
The one real move was `workshop` Part 2's melting plateau (`T 389.50 K / solid
2.0000` default against **388.38 K / 1.9656** converged — the default says melting
has not started when 1.7% is gone), and it is fixed for **one second** of runtime.
⚠ `validation/tolerance_audit.py` is a STANDING audit: run it after touching the
RHS, and it self-checks (`lime_cycle` and `roasting_and_the_catalyst_gate` must
come out byte-identical at speedup 1.00, because they pass their own tolerance and
the harness patches DEFAULTS).

**3. ⚠ `detailed_balance`'s RATE CAP COMPARES A CATALYSED PRE-EXPONENTIAL AGAINST
A LIMIT THAT IS NOT IN ITS UNITS.** A declared `solid_catalyst` puts an order-1
factor in MOL into the rate law, so `A` carries an extra `mol^-1`.
`validation/rate_ceiling.apparent_A` multiplies by `SOLID_CATALYST_REFERENCE` to
undo exactly that and the audit is at its baseline (`ammonia_synthesis_rev` crosses
at **1335.1 K**; raw it reads 1178.1 K, which is the units error).
`detailed_balance` does not, so it would fire **10x too eagerly**. Bounded in the
class this project forgives — the cap scales BOTH pre-exponentials so K is
invariant, cost is a clock at most 10x slow — and **it does not fire on any of the
five catalysed templates**, pinned by a test. The proper fix wants the reference
charge as an ARGUMENT, not a Layer-2 import cycle.

**4. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever, so ten
times the iron is ten times the rate. Right at low coverage, wrong at high. M10.

**UNCHANGED: `psi = np.exp(-a / T)` in `activity.activity_coefficients` overflows
for the PSRK quadratic `H2O <-> N2` pair below 4.28 K**, and the RHS's clamp is
`T_MIN = 1.0`, inside that band. PRE-EXISTING, **measured inert**.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. Fourteen times now — and S1 is the first time the arithmetic
overturned the brief's own design decision rather than confirming it.
⚠ **A PHASE LABEL CARRIES A STANDARD STATE.** Adding one is a thermodynamic
change, not a naming change.
⚠ **AUDIT THE INSTRUMENT BEFORE THE FINDINGS.** S2's harness invented a 12.5%
finding; the coverage audit credited a route that cannot run. Both were caught by
asking "what would this tool report if it were wrong?" — and in S2's case by
running the fixed filter against four hand-built cases and three simulated
mistakes.
⚠ **A CONSTANT SHARED BETWEEN ROWS IS A CLAIM THAT THEY ARE THE SAME EVENT** —
S1's is partly refuted and says so: one clock makes cinnabar 31x slower at its own
retort's temperature, and Evans-Polanyi would get the ordering BACKWARDS because
sphalerite is the most exothermic row and needs the hottest furnace.
⚠ A CLASS IS A MECHANISM CLAIM. Read the rows, not the name — and check which
ROUTES a credit moves.
⚠ AN INVARIANT MEASURED ACROSS A BOUNDARY FLUX IS NOT AN INVARIANT. Seal it first.
⚠ A GREEN SUITE IS NOT EVIDENCE THE INVARIANTS TABLE HOLDS, and neither is a
converged-looking number at the default tolerance. Re-measure before quoting.
⚠ **A COMMITTED GENERATED REPORT IS NOT A BASELINE.** Regenerate at HEAD.
⚠ Windows console is cp1252: a warning glyph inside a `print()` kills a script.
Docstrings fine, printed text ASCII. (SEVENTEEN sessions running.)
⚠⚠ **HEREDOCS ATE AN ESCAPE AGAIN, AND WORSE THAN LAST TIME:** `\\n` written into
a `python - <<'PY'` heredoc arrived as `\n` and became a real newline inside a
Python string, so an anchored patch silently matched nothing. Use the Write tool
for anything containing a backslash, and run it as a file.
⚠ **AND WRITING A FILE THROUGH PYTHON'S TEXT MODE ON WINDOWS EMITS CRLF.** This
repo is MIXED — markdown and `.psv` are CRLF, most Python is LF,
`tools/build_mineral_data.py` is CRLF while `src/chemsim/vessel/vessel.py` is LF.
S1/S2 used a binary-mode anchored patch helper that detects and preserves each
file's own endings; check `git diff --stat` before committing and normalise if a
file you barely touched shows as rewritten.
⚠ An em dash in a markdown anchor will not match a `--` you typed. MILESTONES.md
uses both.
⚠ Redirecting a long Python run to a file BLOCK-BUFFERS it. Use `python -u` — and
do not pipe a long run through `tail`, which holds everything until EOF.

ALSO PRESERVE:

Strict downward layering; numerics sees ONLY numpy arrays; RDKit stays in matter.
NO silent approximations. REFUSE loudly rather than return a confident wrong
number — and a LATENT fragility is a third case: report it, do not refuse it.
The setup/hot-loop split: when adding a physical model, first ask "what uniform
array form does this collapse to?" (S1's two declared exponent matrices collapse
to ONE in `SurfaceArrays.__post_init__`, and the halves survive only as the
declaration a builder can refuse.)
`World.rig is None` exactly the old per-vessel path; `losses=None` exactly
lossless; `precipitation=False` exactly no ionic lattice; `solid_state=False`
exactly no crystal reacting; **`surface=False` exactly no gas attacking one, and
an all-zero `order_solid` exactly the old kinetics kernel**; the Born term exactly
zero in PURE water; the five pH values; SAVE_VERSION stores the CONDITION, never
the instant; every gaseous element reference state Hf = Gf = 0 EXACTLY; **every
METAL Hf = Gf = 0 EXACTLY on the solid basis, and a non-zero result REFUSED as an
allotrope mismatch**; a reference state its own database does not price at Hf = 0
is REFUSED; no mineral pricing differently under the two providers; `ion_data` and
`electrolyte` never subtracted from each other; a declared rate order may never be
reversible; **a surface row whose `ln K` is under +20 is REFUSED, because mass
action on a solid AMOUNT reaches the wrong equilibrium**; the reflux ratio is the
ratio of two drain conductances out of one condenser, declared rather than
inferred; the fragmentation SEARCH runs only after the greedy pass has been
REFUSED; an ion is never counted in the held-ideal flag; a rate CAP scales BOTH
pre-exponentials by one factor; a template that moves a hydrogen ATOM must collapse
explicit Hs; **a declared catalyst is a CONSTANT OF THE MOTION — bit for bit, at
every charge — which is what makes it unable to seed itself**; **the tolerance
audit's two self-check examples come out byte-identical**;
**a lattice may REACT and may never DISSOLVE — the fusion law is still 407x wrong
in both directions, and neither M6 nor S1 softened that by one digit.**

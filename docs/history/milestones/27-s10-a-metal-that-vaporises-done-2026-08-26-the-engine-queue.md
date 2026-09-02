## S10 — A metal that vaporises  ✅ **DONE 2026-08-26 — the engine queue's top item was HALF a data job, and separating the halves is what located the engine gap**

**+0 classes, +0 template-ready, +0 species-ready, +0 RUNNABLE — all four
predicted before the audit ran, and all four came out.** This is an honesty and
mechanic milestone and it was taken as one. What it buys is a **zinc retort that
distils**, three corrected instruments, and an engine gap that is now one
sentence instead of two.

| | before | after |
|---|---:|---:|
| classes with a template | 48 / 229 | 48 / 229 |
| routes template-ready | 38 / 173 | 38 / 173 |
| routes species-ready | 77 / 173 | 77 / 173 |
| routes BOTH — the one to quote | **28** | **28** |

⚠ **NO ENGINE CODE CHANGED.** Not one line of `numerics/` or `vessel/`. The
existing evaporation and melt terms do all of the work below.

### ⚠⚠ 1. "A LATTICE MAY REACT AND MAY NEVER BOIL" WAS A STATEMENT ABOUT AN ENTRY

S9 handed this forward as the plan's top engine item, and as ONE gap covering two
symptoms: the zinc retort makes solid zinc, and nothing caps thermite's
temperature. Both cited the same sentence. **They are not one gap**, and the
pairing is what hid the real one.

Zinc's half needed no engine work at all. `mineral_data` held zinc as a lattice,
so `PhaseArrays` gave it `vol_A` = 1e-30 bar and `solidifies` = False — but that
was a property of the ENTRY. Measured against S4's own three tests for admitting
mercury, zinc passes all three:

* **the atom IS the vapour** — zinc boils monatomic at 1180.15 K (group 12,
  closed d10 s2, so there is no Zn2 to be wrong about), so `[Zn]`'s ideal-gas
  record is what is in the retort;
* **there is nothing to disambiguate** — zinc has ONE condensed form, which is
  what fails for `[S]`, `[C]` and `[Fe]`;
* **and its reference state is expressible** — a SOLID with a melting point.
  ⚠ Mercury passed this one on the liquid block; zinc passes it on the SOLID
  block, which this table already relied on twice for I2 and S8. **A solid
  reference state is not a new thing here.**

So `[Zn]` went into `element_data` and out of `mineral_data`, and the retort row
became `ZnO + C -> Zn(g) + CO`. One edit to a tuple.

### ⚠⚠ 2. THE VAPOUR PRESSURE IS ALGEBRA, NOT A FIT, AND IT HAS FOUR INDEPENDENT CHECKS

Lee-Kesler has no domain over a liquid metal — S4 measured it 3.8x high for
mercury at 523 K — so zinc needed a curated curve for mercury's reason. Alcock,
Itkin & Horrigan (1984), the standard compilation for exactly this problem,
publish the liquid range as **two constants**:

    log10(p / atm) = 5.378 - 6286 / T          692.677-1180 K

With C = D = 0 that IS Antoine form with C = 0, so the conversion is a change of
base and of pressure unit and **nothing is fitted** — and the round trip
reproduces Alcock's own published 5.378 / 6286 to four figures. The two forms
agree to 4e-15 over 700-3000 K.

⚠⚠ **AND ALCOCK'S FIT IS NOT ANCHORED AT Tb, WHICH MAKES THE BOILING POINT A
REAL CHECK HERE.** `chemsim-physical-data-sourcing` records that "boils at 1 atm"
is NOT independent for a Lee-Kesler curve, because ω is inverted at Tb precisely
to make it pass. Alcock's fit was made over 692.7-750 K and never saw Tb, so
where it lands the boiling point is genuine evidence. **The same trap, read from
the other side.** Four checks, and CRC never meets Alcock in any of them:

| check | result |
|---|---|
| `Gf(g) + RT ln(Psub/P0) = 0`, on the SUBLIMATION curve at 298 K | **-0.184 kJ/mol** (Br2 -0.053, Hg +0.012, I2 +0.139, S8 +3.052) |
| Alcock's sublimation SLOPE vs CRC's Hf(g) = 130.400 | **130.674, +0.21%** |
| the unanchored boiling point | **1168.84 K vs 1180.15, -0.96%** |
| the sublimation and liquid fits meeting at the triple point | **+0.103%** |

⚠ The derived `Gf(g)` is **94.801 kJ/mol** against CRC's tabulated 95.2, -0.42%.
⚠ Tc/Pc/Vc are YAWS only — the **compilation** tier — and are stamped as such;
they reach nothing but the Watson factor and Rackett/Rowlinson-Bondi.
⚠ And the price of taking Hvap from the curve the engine evaluates (which is this
project's rule) is that Alcock's two-constant fit measures the latent heat NEAR
THE MELTING POINT: 120.344 kJ/mol against CRC's 115.3 at Tb, **+4.4%**. Taking
CRC's instead would put two tabulations in one record. Stated, not corrected.

### ⚠⚠ 3. THE RETORT'S THRESHOLD MOVED 66 K, TOWARD THE LITERATURE

Carrying the zinc as a vapour adds its sublimation energy and its entropy to the
row, and the entropy wins:

    Zn(s) product, S9    dH +240.0 kJ/mol   dS +189.8   dG = 0 at 1264.2 K
    Zn(g) product, S10   dH +370.4 kJ/mol   dS +309.2   dG = 0 at 1197.8 K

against a real Belgian retort's 1200-1300 and a literature threshold of ~1200 K.

⚠ **AND THE BARRIER WENT UP BY THE SAME 130.4 kJ/mol**, because M6 derives it as
`max(dH, 0)`. 370.4 kJ/mol is inside the 300-400 range reported for apparent
activation energies of carbothermic zinc reduction, so the derived barrier is
defensible rather than merely arithmetic. ⚠⚠ **The row is nevertheless FASTER**,
because an Arrhenius pair is not separable: the derived `A` carries `exp(dS/R)`,
and at 1400 K `exp(119.4/R) = 1.7e6` beats `exp(-130400/RT) = 1.4e-5` by ~24x.
**tau went 256.9 s -> 10.9 s.** The equilibrium is untouched — both directions
scale by one factor — and `rate_ceiling` says the new A is still under the limit.

### ⚠⚠ 4. THE DISTILLATION, AND TWO MECHANICS NOBODY DECLARED

A sealed 1 L retort at 1400 K: **0.040000 mol of zinc, every atom in the
headspace**, no ore and no coke left, conservation clean. Cool the receiver and
it comes back:

     T/K       Zn(g)       Zn(l)       Zn(s)
    1400    0.040000    0.000000    0.000000    <- the burn
    1180    0.011596    0.028404    0.000000
     900    0.000335    0.039665    0.000000
     600    0.000000    0.000000    0.040000

**Tb = 1180.15 K and Tm = 692.68 K appear in no declaration and in no script.**

⚠⚠ **AND THE VENT DOES NOTHING UNTIL THE RETORT BEATS THE ROOM.**
`solid_state_report` computes 1156 K for this row's two evolved gases to reach one
bar between them. Measured, sealed against vented: **12.29% / 12.29% at 1150 K**
(sealed pressure 0.9325 bar) and **13.52% / 18.63% at 1156 K** (1.0312 bar),
rising to 25.67% / 99.84% at 1198 K. A derived van 't Hoff number and a flask
that was actually run, agreeing to the degree.

⚠⚠ **AND A VENTED RETORT BLOWS ITS OWN PRODUCT UP THE CHIMNEY.** Once the product
is a gas, the vent that pulls the reaction over carries the metal away, so the two
numbers a smelter cares about come apart and move in OPPOSITE directions:

     T/K   ore consumed   metal kept   up the flue
    1200         99.91%       51.04%        48.87%
    1400        100.00%       43.53%        56.47%

**That is why a real Belgian retort has a condenser hanging off it**, and it is
why the threshold panel is run SEALED. ⚠ `conservation_report` is silent
throughout, correctly: the vent is a declared boundary flux. *An invariant
measured across a boundary flux is not an invariant.*

### ⚠⚠ 5. AND S9's OVERBLOWING FINDING IS GONE — IT WAS A RATE ARTEFACT PRESENTED AS PHYSICS

S9 measured the zinc smelter's yield going DOWN at 0.20 mol O2 (0.032476 at 0.06
against 0.025515 at 0.20) and wrote: *"Overblowing a zinc retort really does waste
the charge."* The competition it identified is real — the carbothermic reduction
and the tuyere DO want the same carbon, and copper and lead do not, because their
reductant is the CO the carbon made and Boudouard hands it back.

**What decided the race was two derived pre-exponentials, and §3 moved one of them
by 24x.** The reduction now takes the zincite before the blast can burn the coke,
and the yield is monotone and saturating:

    O2/mol   0.02    0.04    0.06    0.10    0.14    0.20    0.50
    Zn/mol  .0117   .0229   .0328   .0400   .0400   .0400   .0400

⚠⚠ **THE SIGN OF THE EFFECT DEPENDED ON A CLOCK.** A real furnace does waste an
overblown charge, for transport reasons this engine does not model, so the old
panel read like a prediction and was a coincidence of two rate constants.
**Thermodynamic conclusions here survive a phase change in a product; kinetic ones
need not.** New rule, and it is the sharpest thing in this session.

### ⚠⚠ 6. THE ESTIMATOR WAS RETURNING A NEGATIVE HEAT CAPACITY, AND MERCURY HAD CARRIED IT SINCE S4

Found by walking into it: `CondensedProvider.get` fits Rowlinson-Bondi over a
**hardcoded 250-450 K** and every caller takes the default — an organic-solvent
window. For a metal that is a LIQUID correlation evaluated where there is no
liquid, then extrapolated into the range where there is one:

    mercury (liquid 234-630 K)   -25.26 at Tm, -12.62 at 298 K, +22.45 at Tb
                                 against a real 27.98
    zinc    (liquid 693-1180 K)  +34.84 at Tm, +462.51 at Tb (15x)
                                 against a real 31.38

⚠ **A negative Cp is not an accuracy problem — adding heat to that liquid LOWERS
its temperature — AND IT WAS REACHABLE.** The default glassware is 50 J/K, so a
flask holding more than **3.96 mol of liquid mercury (795 g, 59 mL)** had a
NEGATIVE TOTAL thermal mass. Measured at 5 mol: **-12.808 J/K.**

Both are replaced by measurement, and both measurements are unusually clean:
mercury from CRCSTD 28.000 / VDI 28.031 / thermo Fit-2023 27.976 — **three
sources inside 0.2%** — and zinc from the WebBook Shomate liquid curve, whose
validity window is 692.73-1180.17 K, i.e. **exactly zinc's liquid range**, flat at
31.380 across all of it.

⚠⚠ **THE GENERAL FAULT IS REPORTED AND NOT FIXED, AND IT IS LARGE.** Swept over
`data/catalog`: **103 compound rows still return a negative liquid Cp somewhere
inside their own liquid range** and 41 more swing over 5x across it — worst,
carminic acid at **-21482 J/(mol K)**. Most of those have a JOBACK-estimated
Tm/Tb that is itself meaningless (carminic acid "melts" at 1398 K and really
decomposes), which is what made the two metals the clean cases: their transition
temperatures are MEASURED and the Cp was still wrong. ⚠ And it bites at BOTH ends
— ethylene reads ~1574 J/(mol K) at its 113.9 K melting point. Nothing runs a
flask there today, so this is a LATENT fragility: reported, not refused.

⚠ Measured cost of the fix on the pinned example: `examples/mercury_retort.py`
moves by **one digit in the ninth decimal** (0.012636665 -> 0.012636666), 1 part
in 1e8.

### ⚠⚠ 7. TWO MORE INSTRUMENTS WERE WRONG, AND ONE INVENTED A 90 kJ/mol FINDING

* **`validation/game_gates.py` printed a residual whether or not the shift it
  differences had been applied.** `standard_state.shift` REFUSES a shift whose
  298 K vapour pressure is under `PSAT_FLOOR_BAR` = 1e-12 — correctly, since the
  correlation is then extrapolated far past its data — and returns `dGf = 0.0`
  with a reason. Differencing that zero printed **"zinc, residual +90.78 kJ/mol"**
  for a formation pair that is fine. ⚠ An INSTRUMENT-GENERATED FINDING, which is
  S2's fault in a new place, and every other row has an applied shift, so the
  hole was unreachable until a solid with a 2e-16 bar vapour pressure arrived.
  The panel reports REFUSED with the reason now, and gives zinc the check it CAN
  have — the sublimation route, one step, no Hfus term, **-0.184 kJ/mol.**
* **`volatility._CURATED_ANTOINE` stamped every entry `NIST WebBook`.** True of
  all nine rows and false the moment a tenth came from Alcock. ⚠ **That is the
  shape S9's false citation had: correct when written, silently wrong after the
  next addition.** Per-entry overrides now, in `volatility` and in `condensed` —
  where the shared strings claimed "at 298 K" for a zinc liquid volume taken at
  700 K, because zinc is a solid at 298 K.

### ⚠⚠ 8. IRON IS REFUSED, AND THAT REFUSAL IS WHERE THE ENGINE GAP ACTUALLY IS

Thermite's cap is the other half of S9's item, and it does NOT yield to the same
move. **The data is nearly there and the mechanism would work:** Alcock's liquid
equation converts to Antoine exactly (A = 6.352717, B = 19574, C = 0) and
unanchored puts Tb at 3083.98 K against 3134.15 measured, **-1.60%**; that curve's
slope gives Hvap = 374.7 kJ/mol, so boiling the 2 mol of iron a mole of thermite
makes would absorb **749.5 of the 851.5 kJ it releases, 88.0%**. Three counts
against, measured rather than assumed:

1. ⚠⚠ **IRON CANNOT LEAVE `mineral_data` THE WAY ZINC DID.** It is a declared
   `solid_catalyst` — `ammonia_synthesis(catalyst="iron")`, resolved through
   `MINERALS["iron"].lattice` — as well as thermite's own solid product. So iron
   has to be BOTH a `mineral_data` lattice and a `thermochemistry` gas, and
   `PhaseArrays.lattice` is one boolean picking both a species' basis and its
   destination block. **Zinc never needed that: nothing else referenced its
   lattice entry.** This is the engine gap, and it is smaller and sharper than
   the one S9 handed forward.
2. `[Fe]` fails S4's **disambiguation** test, which `[Zn]` passes: three solid
   allotropes with two transitions inside thermite's own temperature range, and
   `dCp = 0` with a single Tm/Hfus cannot represent them. `element_data`'s own
   refusal list already names `[Fe]` beside `[C]` and `[S]` for this.
3. **ONE cross-check, not four.** Alcock tabulates no sublimation curve for iron,
   so the 298 K reference-state identity zinc closed at -0.184 kJ/mol cannot be
   evaluated at all.

⚠⚠ **CORRECTION, MEASURED AFTER THIS SECTION WAS WRITTEN — COUNT 1 ABOVE
OVERSTATES THE COST, AND NEXT_PROMPT ENGINE QUEUE ITEM 1 CARRIES THE MEASUREMENT.**
Patching iron's volatility in place and running thermite insulated CAPS it
(5469.43 → 3490.99 K at 1 J/K, conservation clean, and the 50 J/K flask
identical because it never reaches Tm). Three things count 1 got wrong:
`PhaseArrays.lattice`'s two hot-loop uses are in the SURFACE term only and **iron
is in no surface row**, so `C_mix[Fe] ** 0 == 1.0` exactly and they are inert;
the Haber catalyst reads `order_solid`/`nS` and **never depended on the flag** —
what needs `MINERALS["iron"]` is NAME RESOLUTION, which is separable from
volatility; so the real blocker is **one branch in `build_phase_arrays`** pinning
`NONVOLATILE_A`/`solidifies = False`, i.e. a setup-layer change with **no RHS
edit**. Counts 2 and 3 stand and are the reason this is still not done: they are
DATA objections, and the engine fix does not touch them. **The general
one-boolean-two-jobs form is still worth fixing** — and note
`build_surface_arrays` already splits `order_solid`/`order_gas` from the
declaration and then throws the `nu` split away.

### 9. WHAT THE FUSION LAW DOES TO A METAL IN WATER, MEASURED BEFORE IT WAS ACCEPTED

`solidifies = True` exposes zinc to the ideal fusion-law solubility, and zinc has
no UNIFAC groups so its gamma is 1. Measured at 298 K, x_sat = 0.197 — 89 g/100 mL
against a real ~1e-8. ⚠ **That wrongness is PRE-EXISTING and shared**, which is
why zinc joining it is consistent rather than new: iodine is over by **1.5e4x**
and sulfur by **1.1e8x** on the same law, and zinc's mole fraction (0.197) is
SMALLER than iodine's (0.238), sulfur's (0.275) or naphthalene's (0.302). It is
reachable only by putting metal in water, which no route does. Reported.

### 10. THE SMALL THINGS

* `data/catalog/derived/species_roles.psv` moves zinc from the `mineral`
  provenance tier to **`measured`**, which is an upgrade in the audit's own terms.
* All three catalog artefacts regenerated and byte-identical across
  `PYTHONHASHSEED` 0 / 1 / 12345.
* ⚠ Three separate pieces of prose had rotted inside this session's own edits:
  the audit's overblowing paragraph, its "a lattice against three curated gases"
  (the row now has two of each), and its "the same statement the zinc retort
  makes". **A generated file's prose rots exactly like a hand-written one**, and
  so does an audit's.
* ⚠ `validation/smelting.py` is **CRLF**, contrary to the handoff's note that the
  newer `validation/*.py` are LF. Check, do not assume.
* ⚠ The cp1252 trap again, twenty-fifth session running — a warning glyph inside
  a `print()` in a scratch probe.

⚠ **THE SUITE: 932 passed / 0 failed in 13:20**, run after every `src/` edit — a
real baseline rather than arithmetic, which is the first time in four sessions.

**Files:** `tools/build_element_data.py` (`REFERENCE_SMILES` +Zn with the
argument, `LATTICE_ELEMENTS` -Zn, `CANDIDATES` +Zn),
`tools/build_mineral_data.py` (`ELEMENT_SOLIDS` -zinc),
`src/chemsim/properties/element_data.py` and `mineral_data.py` (regenerated),
`src/chemsim/properties/volatility.py` (Alcock entry + `_CURATED_SOURCE`),
`src/chemsim/properties/condensed.py` (two liquid Cp, two liquid volumes, two
source-override tables), `src/chemsim/properties/solid_state.py` (the retort row
evolves a vapour), `validation/smelting.py` (panel 6 rewritten, panel 6b new, the
iron refusal), `validation/game_gates.py` (the `applied` bug + zinc's sublimation
check), `validation/catalog_coverage.py` (the S8 paragraph), `tests/test_smelting.py`
(+3 tests, 3 rewritten), `tests/test_element_solids.py`, `tests/test_element_data.py`
(+3 tests), `tests/test_phase_properties.py` (+2 tests), `tests/test_solid_state.py`,
`data/catalog/COVERAGE_REPORT.md` and `derived/species_roles.psv` (regenerated).

---

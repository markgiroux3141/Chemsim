## M5 — Templates to a target, chosen by unlock  ✅ **DONE 2026-08-24**

**Target was 20+ template-ready routes. Measured: 7 → 25 of 173, and 12 → 29 of
212 reaction classes**, from **20 new templates** in `reactions/synthesis.py`.
`examples/named_routes.py` runs 17 of them end to end in ~24 s.

⚠ **THE GREEDY ORDER M1 HANDED FORWARD WAS MOSTLY OUTCOME LABELS, AND THAT IS
THE MILESTONE'S REAL FINDING.** Six of the ten classes at the top of that queue
have no template here, and only one of the six is a difficulty problem:

| refused class | routes it would have unlocked | why |
|---|---:|---|
| `catalytic-air-oxidation` | 3 | three mechanisms — liquid-phase radical autoxidation, Mars–van Krevelen vapour oxidation, and an oxidative ring cleavage |
| `fermentation` | 2 | a metabolic **network**, not a transformation |
| `pyrolysis` | 2 | two of three rows read `coal-marker → coal-tar-marker` |
| `isomerisation` | 2 | three mechanisms under one label |
| `thermal-cracking` | 1 | a lumped product slate from a radical chain |
| `separation` | 1 | the engine *does* fractionate — but a distillation is not a reaction class, and that route's feedstock is a marker |

**M1 built the standard; M5 is the first milestone that had to SPEND it, and
spending it cost six routes off the top of the queue.** What replaced them is a
long tail, and M5 barely shortened it: **63 routes one class away from 50
distinct classes before, 56 from 43 after**. So the work was 20 templates for 18
routes rather than 5 templates for 18, and the next 18 will cost about the same.

⚠ **One class was SPLIT rather than refused, and the distinction matters.**
`catalytic-hydrogenation` is the most-used class with no template in the corpus
(10 steps) and its rows are five mechanisms — but unlike `fermentation`, every
one of them *is* a clean mechanism. So the rows were re-labelled on M1's
precedent and two of the five built. The other three are named gaps. See
`data/catalog/README.md`.

### What it also turned up, none of it planned

* **A reversible template is discovered in the FORWARD direction only.** An ester
  and water in a flask find nothing, however reversible the esterification is,
  because `build_network` matches reactant patterns. General to every reversible
  template in the project; **not fixed** — M5 wrote `ester_hydrolysis` from the
  ester side instead.
* **A neutral species with no vapour-pressure curve MIXES standard states**, and
  it was silent. Worth **+323 kJ/mol** on the first reaction that hit it.
  `standard_state.mixed_basis` now names it and `build_network` prints a notice.
* **An estimator outside its domain arrived as a scipy traceback.** Joback gives
  triolein Tb 1690 K / Tc 4020 K, hence a **negative acentric factor**, hence a
  saturation pressure that falls with temperature. Now a refusal that names the
  species.
* **The audit was calling 9 neutral species "ion".** A neutral that does not boil
  is a different claim from an ion that cannot; it has its own tier now.
* One engine change was needed: `ReactionTemplate.run` collapses explicit
  hydrogens, or the ammonia the Haber template makes is a *different species*
  from the ammonia in the bottle, with the mass balance closing perfectly.

---

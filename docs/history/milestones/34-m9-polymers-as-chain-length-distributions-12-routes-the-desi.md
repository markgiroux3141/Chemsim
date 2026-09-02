## M9 — Polymers as chain-length distributions  *(12 routes; the design has seen this problem twice before)*

**Species enumeration is the wrong representation for a polymer**, and this is
the same failure as the network explosion, seen a third time: a self-feeding
template that regenerates its own matched group runs to the species cap. The
catalog wants **Bakelite, nylon 66, PET, polyethylene, PVC, PTFE, polyurethane,
neoprene, urea-formaldehyde, polylactide, MMA and styrene** — twelve routes, and
the most recognisable industrial chemistry of the 20th century.

The representation is a population balance, most likely method-of-moments: carry
the first few moments of the chain-length distribution as state rather than one
species per degree of polymerisation. ⚠ **That is a new KIND of state variable**
— not a species count — so `PHASE_INDEX`, the conservation report and the
non-negative projection all have to be told what it is. Scope this before
promising it.

⚠ **And check the cheap approximation FIRST, as M3 and M4 both should have
taught:** a route whose *target* is the polymer but whose interesting chemistry
is the MONOMER (vinyl chloride, styrene, MMA, caprolactam) may only need the
monomer step, with polymerisation as a terminal sink. Measure how many of the
twelve that covers before building a moment closure.

**Done when:** a polymerisation runs without enumerating species, and the number
average and dispersity come out of the integration.

---

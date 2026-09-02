## R4 -- RATE-AWARE PRUNING  *(one session)*

The real answer to the objection, and the headline above is the case for it: the
cost is the solver evaluating 644 reactions, nearly all dead at 298 K, on every
RHS call. Start from `properties/` and `network/builder.py`'s `_expand_once`.

⚠⚠ **THE DESIGN TRAP: PRUNING ON THE RATE CONSTANT ALONE IS WRONG**, because a
slow reaction at high concentration still matters. The defensible form is
**k x the concentrations actually charged**, which makes the network depend on
the charge -- **that is a design decision and not a coding job**, and it has a
consequence worth staring at before starting: two flasks holding the same
species in different amounts would get **different networks**, so a scenario's
network stops being a pure function of (templates, feed species). Everything
`scenario.py`'s own docstring says about determinism has to be re-argued
against that.

⚠ And finding 3 is the warning: a bound that looks like it shrinks the problem
can enlarge it. **Measure the reaction count, not just the clock.**

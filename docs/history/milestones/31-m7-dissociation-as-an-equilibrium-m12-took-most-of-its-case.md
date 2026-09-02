## M7 -- Dissociation as an equilibrium  *(M12 TOOK MOST OF ITS CASE AWAY)*

**RE-SCOPE THIS BEFORE SCHEDULING IT.** The headline was a stiffness ratio of
**7.05e21**, essentially all acid/base recombination -- and 9.431e18 of that was
water's reverse autoionization, **a rate constant 9.4e7 times the collision
limit**. M12 capped it at 1.0e11 (HANDOFF 82), so the ratio is now **8.6e12**:
still stiff, no longer the largest number in the project by eight orders, and
the flask it was worst on now integrates 6.6x FASTER than before rather than
needing a new representation to be affordable.

What genuinely survives, and it is the real argument:

* **The value integrating gives IS the equilibrium value.** That was always the
  principled reason and it is untouched by how fast the pair runs.
* **It still owns the stiff-reactant-at-zero residual** (1e-4 level, reported,
  converges) -- and M12 made that MORE visible at the default rung, not less:
  the prep creates 2.53e-05 mol of benzoyl there now, against 3.5e-12, because
  fewer and larger steps cover the same span. It converges to -4.4e-15 by rtol
  1e-8, and `conservation_report` says so unprompted.

**Done when:** the five pH invariants come back IDENTICAL and the stiffness ratio
falls by orders of magnitude. Measure the ratio again first -- the number in
every previous planning document is the pre-M12 one.

---

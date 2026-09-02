## R5 -- THE BENCH `generations` BOX SILENTLY RESETS A RAISED BOUND  *(~20 min, UI)*  ✔ **DONE 2026-09-01**

Observed live by the user, who went from 3 generations back to 1 without being
told. `_react_further` (`ui/app.py:645`) raises `scenario.generations` and
`scenario.max_species` and **never writes either back to `self.bench_gens` /
`self.bench_cap`**; `_pour_bench` (`ui/app.py:609`) reads those boxes. So the
next pour silently discards the bound the player raised. **The fix is to write
the raised bounds back into the boxes**, which also makes the current bound
visible in the one place a player would look for it.

### WHAT WAS BUILT (2026-09-01)

Exactly that: `_react_further` writes `gens` and `cap` into the two boxes after
`rebuilt(...)`, both of them, every press -- the boxes show the LIVE scenario's
bounds, so a value typed but never poured is overwritten, which is the honest
reading (after REACT FURTHER the world's bounds ARE these). ⚠ Verified by a
LIVE PROBE rather than a widget test, because the repo has no Tk in tests
anywhere and this is pure widget plumbing over the already-tested `rebuilt`:
a real `App` on a withdrawn root, water+glucose at gens=1, one programmatic
press -- boxes read `2 / 400`, equal to the scenario, and `_pour_bench`'s own
`_float` read of them returns the raised bounds. The P2 Filter-button
precedent, done deliberately the same way.

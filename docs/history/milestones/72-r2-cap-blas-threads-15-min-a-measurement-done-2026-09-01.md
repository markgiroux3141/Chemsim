## R2 -- CAP BLAS THREADS  *(~15 min + a measurement)*  ✔ **DONE 2026-09-01**

Measured on identical work: uncapped scipy/BLAS used **7.21 cores**; with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1` it used **0.99 cores and was FASTER (5.9 s vs 10.1 s)**.
**There is no trade-off**: this engine's arrays are small enough that threading
is pure overhead, and *"single process" is not "one core"* -- sample it rather
than assume.

⚠ **DECIDE WHERE IT BELONGS, BECAUSE THE OBVIOUS PLACE IS THE RUDE ONE.**
`chemsim/__init__` is tempting and would silently reconfigure BLAS for anyone
who imports this as a library. The UI's worker thread is the case that actually
matters -- it would otherwise spread a player's whole machine over one flask --
so `chemsim/ui/__main__.py` and the validation harness are the defensible
places. Nothing in the repo caps threads anywhere today (`grep`ped: zero hits).

### WHAT WAS BUILT (2026-09-01)

`chemsim/threads.py` -- `cap_blas_threads()`, `setdefault` on the four
variables so a count somebody set by hand wins. Called from **four entry
points and no library code**: `chemsim/ui/__main__.py` (before the app import,
which is what loads numpy), `validation/shelf.py` and
`validation/tolerance_audit.py` (both before rdkit/numpy), and
`tests/conftest.py` -- the suite's standing 1260-green record was taken
thread-capped, and capping in `conftest` is what makes that condition
reproducible rather than ambient. `chemsim/__init__` stays import-light and
`tests/test_threads.py` **asserts it does not cap** (plus the other three
contract points: all four variables, hand-set wins, and being called after
numpy loads is loud in the return value -- the pools are sized when numpy
first loads, so a late cap is a no-op and must say so). ⚠ The owed measurement
was already discharged by R1: capped twice and uncapped once, the tolerance
audit's output is identical -- the cap is numerically neutral, so being late
costs speed and nothing else, which is why late is a `bool` and not a raise.

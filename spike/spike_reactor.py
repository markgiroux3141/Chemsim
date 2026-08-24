"""
PHASE-0 SPIKE  --  THROWAWAY VALIDATION, NOT THE REAL ARCHITECTURE.

Thesis under test:
    Temperature-sensitivity and contamination-sensitivity should EMERGE from
    integrating a reaction network, not be scripted. Nowhere in this file does
    it say "if too hot, ruin the yield" or "if oxygen, contaminate". There are
    just reactions with rate laws. Bad outcomes fall out of the physics.

Chemistry (illustrative -- see PARAMETER HONESTY note below):
    R1  Fischer esterification (reversible, acid-catalysed, the DESIRED product):
            AcOH + EtOH  <=>  EtOAc + H2O
    R2  Aerobic oxidation (needs O2 contamination):
            EtOH + 1/2 O2  ->  AcH + H2O
    R3  Thermal dehydration (high activation energy -> only matters when hot):
            2 EtOH  ->  Et2O + H2O

Physics knobs, all emergent in their effect:
    - Temperature T enters every rate constant via Arrhenius k = A*exp(-Ea/RT).
    - O2 ingress models a leaky vs. sealed vessel: dO2/dt += k_leak*(O2_sat - O2).

PARAMETER HONESTY: the A / Ea values below are hand-tuned for a legible demo,
NOT literature values. The STRUCTURE (Arrhenius + mass-action + competing
pathways) is real chemistry; the specific numbers are illustrative.
"""

import numpy as np
from scipy.integrate import solve_ivp

R = 8.314  # J / (mol K)

# ---- Species: fixed index order for the state vector ------------------------
SPECIES = ["AcOH", "EtOH", "EtOAc", "H2O", "O2", "AcH", "Et2O"]
IDX = {s: i for i, s in enumerate(SPECIES)}
N = len(SPECIES)


# ---- Reactions: each is (Arrhenius A, Ea, {reactant: order}, {species: dstoich})
# 'orders' drives the rate law (mass action); 'delta' is the net stoichiometry
# applied to the state vector. Kept separate so a reaction's kinetics and its
# bookkeeping don't get tangled -- this is the seed of the real design.
def arrhenius(A, Ea, T):
    return A * np.exp(-Ea / (R * T))


REACTIONS = [
    # R1 forward: esterification
    dict(name="ester_fwd", A=1.0e6, Ea=50_000,
         orders={"AcOH": 1, "EtOH": 1},
         delta={"AcOH": -1, "EtOH": -1, "EtOAc": +1, "H2O": +1}),
    # R1 reverse: hydrolysis (higher Ea -> K falls a little as T rises, Le Chatelier)
    dict(name="ester_rev", A=1.0e6, Ea=55_000,
         orders={"EtOAc": 1, "H2O": 1},
         delta={"AcOH": +1, "EtOH": +1, "EtOAc": -1, "H2O": -1}),
    # R2: aerobic oxidation of ethanol (needs O2)
    dict(name="oxidation", A=1.0e9, Ea=65_000,
         orders={"EtOH": 1, "O2": 1},
         delta={"EtOH": -1, "O2": -0.5, "AcH": +1, "H2O": +1}),
    # R3: thermal dehydration to diethyl ether (high Ea -> only wakes up hot)
    dict(name="dehydration", A=6.7e9, Ea=90_000,
         orders={"EtOH": 2},
         delta={"EtOH": -2, "Et2O": +1, "H2O": +1}),
]

# Precompute reactions as arrays for a vectorised RHS.
_A = np.array([r["A"] for r in REACTIONS])
_Ea = np.array([r["Ea"] for r in REACTIONS])
_order = np.zeros((len(REACTIONS), N))
_delta = np.zeros((len(REACTIONS), N))
for j, r in enumerate(REACTIONS):
    for sp, o in r["orders"].items():
        _order[j, IDX[sp]] = o
    for sp, d in r["delta"].items():
        _delta[j, IDX[sp]] = d


def make_rhs(T, k_leak, O2_sat):
    """Build the dC/dt function for a fixed temperature and leak setting."""
    k = arrhenius(_A, _Ea, T)  # rate constants at this T

    def rhs(t, C):
        C = np.maximum(C, 0.0)  # guard tiny negative excursions from the solver
        # mass-action rate for each reaction: k_j * prod_i C_i^order_ji
        rates = k * np.prod(C ** _order, axis=1)
        dC = _delta.T @ rates
        # O2 ingress from the atmosphere (0 when sealed)
        dC[IDX["O2"]] += k_leak * (O2_sat - C[IDX["O2"]])
        return dC

    return rhs


def run(label, T, k_leak, O2_sat=0.25, t_end=3600.0):
    C0 = np.zeros(N)
    C0[IDX["AcOH"]] = 5.0
    C0[IDX["EtOH"]] = 5.0
    C0[IDX["H2O"]] = 0.5
    C0[IDX["O2"]] = 0.0  # starts sealed; ingress is what fills it if leaky

    sol = solve_ivp(
        make_rhs(T, k_leak, O2_sat), (0, t_end), C0,
        method="BDF",  # stiff solver -- the CVODE lineage, runs in C
        rtol=1e-7, atol=1e-10, dense_output=True,
    )
    return label, T, sol


def summarize(results):
    limiting = 5.0  # initial EtOH / AcOH
    print(f"\n{'scenario':<26}{'T (K)':>7}{'EtOAc yield':>13}"
          f"{'  lost to ->':>13}{'ether':>9}{'aldehyde':>10}")
    print("-" * 88)
    for label, T, sol in results:
        Cf = sol.y[:, -1]
        yield_ester = Cf[IDX["EtOAc"]] / limiting
        print(f"{label:<26}{T:>7.0f}{yield_ester:>12.1%}"
              f"{'':>13}{Cf[IDX['Et2O']]:>8.2f}M{Cf[IDX['AcH']]:>9.2f}M")


if __name__ == "__main__":
    scenarios = [
        run("A. clean, controlled T", T=340.0, k_leak=0.0),      # sealed, cool
        run("B. too hot (sealed)",    T=380.0, k_leak=0.0),      # sealed, hot
        run("C. air leak (cool)",     T=340.0, k_leak=0.05),     # leaky, cool
        run("D. hot AND leaky",       T=380.0, k_leak=0.05),     # both go wrong
    ]
    summarize(scenarios)

    # Optional plot; skip silently if matplotlib is missing.
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import os

        fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
        t = np.linspace(0, 3600, 400)
        for ax, (label, T, sol) in zip(axes.flat, scenarios):
            Y = sol.sol(t)
            for sp in ["AcOH", "EtOH", "EtOAc", "Et2O", "AcH"]:
                ax.plot(t / 60, Y[IDX[sp]], label=sp)
            ax.set_title(label)
            ax.set_ylabel("conc (mol/L)")
            ax.grid(alpha=0.3)
        for ax in axes[1]:
            ax.set_xlabel("time (min)")
        axes[0, 0].legend(loc="upper right", fontsize=8)
        fig.suptitle("Phase-0 spike: same reactions, different conditions -> "
                     "different outcomes (all emergent)", fontsize=13)
        fig.tight_layout()
        out = os.path.join(os.path.dirname(__file__), "spike_result.png")
        fig.savefig(out, dpi=110)
        print(f"\nplot -> {out}")
    except Exception as e:
        print(f"\n(plot skipped: {e})")

"""Layer 4 -- the numerical core.

This is the hot loop, and it is deliberately ignorant of chemistry: it consumes
``KineticArrays`` (plain numpy + names) and integrates mass-action kinetics with
Arrhenius temperature dependence. No Molecule, no RDKit, no units objects. That
is exactly what makes it the clean swap point for a Rust/PyO3 kernel later --
the interface is arrays in, arrays out.

Rate law (assumed elementary, mass action):
    rate_j(T, C) = k_j(T) * prod_i C_i ** order_ji ,   k_j(T) = A_j * exp(-Ea_j / R T)
    dC/dt        = deltaᵀ @ rate   (+ optional external source term)

The optional ``source(t, C) -> dC`` hook is where higher layers (a vessel's O2
ingress, inter-phase transport, dosing) inject non-reactive flux without the
core needing to know what it means.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp

from chemsim.constants import R
from chemsim.network import KineticArrays
from chemsim.numerics.jacobian import BoundedJacobian

Source = Callable[[float, np.ndarray], np.ndarray]


class Integrator:
    def __init__(self, system: KineticArrays):
        self.sys = system

    def rate_constants(self, T: float) -> np.ndarray:
        """Modified-Arrhenius k(T) = A T**n exp(-Ea/RT) for every reaction.

        ``n`` is zero for every declared rate; detailed balance is the only thing
        that sets it, to carry the T**delta_n of the standard-state conversion
        exactly rather than folding it into A at one temperature.
        """
        return self.sys.A * T**self.sys.n_exp * np.exp(-self.sys.Ea / (R * T))

    def make_rhs(self, T: float, source: Source | None = None):
        """Compile dC/dt for a fixed temperature into a closure."""
        k = self.rate_constants(T)
        order = self.sys.order
        delta_T = self.sys.delta.T

        def rhs(t: float, C: np.ndarray) -> np.ndarray:
            C = np.maximum(C, 0.0)  # clamp solver undershoot below zero
            rates = k * np.prod(C ** order, axis=1)
            dC = delta_T @ rates
            if source is not None:
                dC = dC + source(t, C)
            return dC

        return rhs

    def run(
        self,
        C0: np.ndarray,
        T: float,
        t_span: tuple[float, float],
        source: Source | None = None,
        rtol: float = 1e-7,
        atol: float = 1e-10,
        dense_output: bool = False,
    ):
        """Integrate over t_span with a stiff BDF solver. Returns the scipy solution."""
        rhs = self.make_rhs(T, source)
        return solve_ivp(
            rhs,
            t_span,
            np.asarray(C0, dtype=float),
            method="BDF",
            rtol=rtol,
            atol=atol,
            dense_output=dense_output,
            # The same ceiling every other solver in this project runs under.
            # See ``numerics/jacobian.py``: BDF's own differencing has a floor on
            # the perturbation factor and no roof, so a column it cannot
            # difference is probed harder until the factor overflows.
            jac=BoundedJacobian(rhs, atol),
        )

    def step(
        self, C: np.ndarray, T: float, dt: float, source: Source | None = None, **kw
    ) -> np.ndarray:
        """Advance the state by dt and return the new concentration vector.

        This is the entry point the headless engine's stepper will call each tick.
        """
        sol = self.run(C, T, (0.0, dt), source=source, **kw)
        return sol.y[:, -1]

"""Layer 4 -- several vessels, coupled, integrated as ONE stiff system.

A vessel that can only see the room is a vessel that cannot reflux. Every piece
of glassware that matters -- condenser, still head, rotovap, Dean-Stark, dropping
funnel, cold trap -- is two containers with something flowing between them, and
the flow is what the apparatus is *for*.

**The physics a condenser needs is already written.** Vapour arriving in a cold
vessel finds ``p > p_eq`` at that temperature, so the existing evaporation term
runs backwards, ``q_vap`` changes sign and *releases* latent heat, and a thermal
edge carries it to the coolant. Nothing in ``vessel_integrator`` had to learn
about condensers. What was missing was only a way for two vessels to see each
other, and that is all this module adds.

## Why one state vector rather than two vessels stepped in turn

Reflux is a feedback loop -- boil, rise, condense, return, reboil -- with latent
heat coupling the two temperatures. Operator-splitting a loop like that across
independently-stepped vessels smears it, and worse, makes the answer depend on
the stepping interval. That is precisely the non-determinism Layer 6 exists to
prevent. So the rig solves

    y = [ vessel_0 (3n+1) | vessel_1 (3n+1) | ... | vessel_{m-1} (3n+1) ]

as one system and lets BDF resolve the loop. Blocks are uniform because every
vessel shares one reaction network, which is an invariant Layer 5 already
enforces for ``pour_into``.

Each vessel's own physics enters UNCHANGED: ``VesselIntegrator.make_rhs`` already
closes over a whole ``3n+1`` state, so the rig calls it on a slice and adds edge
terms on top. There is no second copy of the vessel RHS to keep in step with the
first.

## The four edges

``VAPOUR``
    Bidirectional, pressure-driven, carrying the donor's headspace composition:
    ``flux_i = k (P_a - P_b) x_gas,i``. Venting to the room is the same law with
    a fixed far end, which is why ``k_vent`` did not need generalising.
``DRAIN``
    One-directional liquid, first order in the donor's holdup: ``flux_i = k
    nL_i``. This is a *drain*, not a level-driven flow -- no geometry is modelled
    and none is implied. It is what returns condensate down a reflux column.
``THERMAL``
    ``q = UA (T_a - T_b)``. Jackets, coolant, a flask sitting in a bath.
``METER``
    One-directional liquid at a fixed molar rate -- a dropping funnel or a
    syringe pump. The rate is a parameter an event sets, deliberately NOT a
    time window evaluated inside the RHS: a hard on/off in ``t`` is a
    discontinuity mid-solve, whereas an event at a step boundary is exactly the
    mechanism Layer 6 already uses to stay deterministic.

## Two things that are easy to get wrong

**Enthalpy has to travel with the material.** Venting to ambient never needed an
explicit term -- gas leaves at ``T`` and the shrinking heat capacity accounts for
it -- but an edge into another vessel does. Without it, hot vapour entering a
cold condenser is a free lunch and reflux runs on invented energy. Material
leaving at ``T_a`` does not change ``T_a``; arriving in ``T_b`` it does:

    dT_b += sum_i flux_i Cp_i (T_a - T_b) / Cp_total,b

**Sparsity is not automatically a win, and this rig is where that was measured.**
``jac_sparsity`` buys exactly one thing -- column GROUPS in ``num_jac`` -- and for
two vessels joined by a vapour edge it buys none of them, because a pressure
difference reaches every amount in both vessels through the gas VOLUME. See
``useful_sparsity``: the pattern is passed when it groups anything and skipped when
it would only add sparse overhead to a dense amount of work.

**Upwinding must be self-limiting, and that is NOT the same as smooth.** Which
vessel donates flips at ``P_a == P_b``, so the obvious move is the one this
codebase reaches for everywhere else -- blend the two compositions with a tanh, as
``DRYOUT_MOLES`` and ``MELT_BLEND`` do. ⚠ **That is wrong here and it destroyed
0.34 mol of a refluxing rig's air for several sessions.** A blended composition is
a mixed-sign product: at a small POSITIVE ``dP`` the flow is out of *a*, but the
blend still gives half of it *b*'s composition, so *a* exports species it does not
have and its gas block runs negative without bound. The flux is written instead as
a full stream of the donor's composition plus an inflow-only correction, so every
outward term is proportional to the donor's own amount. See ``backflow_part`` in
``vessel_integrator``, which is also where the smoothing scale is argued -- it is
zero, and the sweep that put it there is in ``validation/vent_leak.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from chemsim.constants import R_L_BAR
from chemsim.numerics import vessel_integrator as vessel_core
from chemsim.numerics.jacobian import BoundedJacobian
from chemsim.numerics.vessel_integrator import (
    CP_MIN,
    V_GAS_MIN,
    VesselIntegrator,
    _Stationary,
    _poly,
    backflow_part,
    project_non_negative,
)

# Edge kinds, as ints so the hot loop indexes rather than branches on strings.
VAPOUR, DRAIN, THERMAL, METER = 0, 1, 2, 3
EDGE_NAMES = {VAPOUR: "vapour", DRAIN: "drain", THERMAL: "thermal", METER: "meter"}

# Pressure scale over which the donor of a vapour edge switches, bar. Zero: the
# switch is exact. ⚠ 1e-4 WAS NOT SMALL ENOUGH TO BE DECISIVE, and that was half of
# the vent bug -- a reflux runs at dP ~ 2e-4 bar, so the blending band reached the
# operating point and carried the condenser's air back down into the pot, taking
# the plateau 352.89 -> 351.10 K. See DP_VENT_SMOOTH in ``vessel_integrator``, where
# the choice is argued and swept; the two are one constant for one reason and are
# kept equal deliberately.
DP_SMOOTH = 0.0


@dataclass
class EdgeArrays:
    """Topology as flat arrays -- the Layer 4 contract, no vessel objects.

    Index arrays plus coefficient arrays, exactly as ``KineticArrays`` splits
    reactions by phase at setup. Nothing here knows what a condenser is.
    """

    kind: np.ndarray     # (e,) int, one of VAPOUR/DRAIN/THERMAL/METER
    a: np.ndarray        # (e,) vessel index -- the donor for directional kinds
    b: np.ndarray        # (e,) vessel index
    k: np.ndarray        # (e,) conductance; mol/s for METER, W/K for THERMAL

    def __post_init__(self):
        self.kind = np.asarray(self.kind, dtype=int)
        self.a = np.asarray(self.a, dtype=int)
        self.b = np.asarray(self.b, dtype=int)
        self.k = np.asarray(self.k, dtype=float)
        if not (len(self.kind) == len(self.a) == len(self.b) == len(self.k)):
            raise ValueError("edge arrays must all be the same length")

    @property
    def count(self) -> int:
        return len(self.kind)


class RigIntegrator:
    """Integrates several coupled vessels as one system."""

    def __init__(self, integrators: list[VesselIntegrator], edges: EdgeArrays):
        if not integrators:
            raise ValueError("a rig needs at least one vessel")
        self.integrators = list(integrators)
        self.edges = edges
        self.m = len(self.integrators)
        self.n = self.integrators[0].n
        self.block = 4 * self.n + 1

        for i, integ in enumerate(self.integrators):
            if integ.n != self.n:
                raise ValueError(
                    f"vessel {i} has {integ.n} species but vessel 0 has {self.n}"
                    " -- a rig requires one shared network so its blocks align"
                )
        for name in ("a", "b"):
            bad = [int(v) for v in getattr(edges, name) if not 0 <= v < self.m]
            if bad:
                raise ValueError(f"edge endpoint {bad} is not a vessel index")

    # -- layout --------------------------------------------------------------

    def slice_of(self, vessel: int) -> slice:
        return slice(vessel * self.block, (vessel + 1) * self.block)

    def pack(self, states: list[np.ndarray]) -> np.ndarray:
        """Concatenate per-vessel state vectors into the rig vector."""
        if len(states) != self.m:
            raise ValueError(f"expected {self.m} vessel states, got {len(states)}")
        return np.concatenate([np.asarray(s, dtype=float) for s in states])

    def unpack(self, y: np.ndarray) -> list[tuple]:
        """Rig vector -> [(nL1, nL2, n_gas, n_solid, T), ...] per vessel."""
        return [
            self.integrators[v].unpack(y[self.slice_of(v)]) for v in range(self.m)
        ]

    # -- the coupled right-hand side ----------------------------------------

    def _vessel_scalars(self, y: np.ndarray, v: int):
        """(nL1, nL2, nG, T, pressure, Cp_total, Cp_liq, Cp_gas) for a slice."""
        integ = self.integrators[v]
        n, ph, cond = self.n, integ.ph, integ.cond
        blk = y[self.slice_of(v)]
        nL1 = np.maximum(blk[:n], 0.0)
        nL2 = np.maximum(blk[n : 2 * n], 0.0)
        nG = np.maximum(blk[2 * n : 3 * n], 0.0)
        nS = np.maximum(blk[3 * n : 4 * n], 0.0)
        T = float(blk[-1])

        v_mol = np.maximum(_poly(ph.v_liq, T), 0.0)
        V_G = max(
            cond.volume - float((nL1 + nL2 + nS) @ v_mol), V_GAS_MIN
        )
        P = float(nG.sum()) * R_L_BAR * T / V_G

        Cp_l = _poly(ph.Cp_liq, T)
        Cp_total = cond.heat_capacity + float(
            (nL1 + nL2 + nS) @ Cp_l + nG @ _poly(ph.Cp_gas, T)
        )
        return nL1, nL2, nG, T, P, max(Cp_total, CP_MIN), Cp_l, _poly(ph.Cp_gas, T)

    def make_rhs(self, y0: np.ndarray | None = None):
        """Compile the coupled dy/dt.

        ``y0`` is threaded down to each vessel's own ``make_rhs`` ON ITS SLICE,
        which is all the plumbing the frozen layer permittivity needs here -- the
        rig adds edge terms on top of the vessel RHS and does not have a polarity
        of its own. Passing ``None`` leaves every vessel recomputing it in the
        loop, which is what this did before.
        """
        sub = [
            integ.make_rhs(None if y0 is None else y0[self.slice_of(v)])
            for v, integ in enumerate(self.integrators)
        ]
        B, n, m = self.block, self.n, self.m
        e = self.edges

        def rhs(t: float, y: np.ndarray) -> np.ndarray:
            out = np.empty_like(y)

            # Diagonal blocks: each vessel's own chemistry, phase equilibria and
            # energy balance, evaluated by the existing single-vessel RHS on its
            # slice. Untouched and unaware it is part of a rig.
            for v in range(m):
                out[v * B : (v + 1) * B] = sub[v](t, y[v * B : (v + 1) * B])

            if e.count == 0:
                return out

            scal = [self._vessel_scalars(y, v) for v in range(m)]

            for j in range(e.count):
                a, b, k, kind = int(e.a[j]), int(e.b[j]), float(e.k[j]), int(e.kind[j])
                nL1_a, nL2_a, nG_a, T_a, P_a, Cp_a, CpL_a, CpG_a = scal[a]
                nL1_b, nL2_b, nG_b, T_b, P_b, Cp_b, CpL_b, CpG_b = scal[b]

                if kind == THERMAL:
                    q = k * (T_a - T_b)          # W, positive = a heats b
                    out[a * B + 4 * n] -= q / Cp_a
                    out[b * B + 4 * n] += q / Cp_b
                    continue

                # Each edge yields a list of (block offset, flux) pairs, because
                # a liquid edge now has TWO blocks to move. ⚠ A DRAIN or a METER
                # moves both layers in the proportion the donor holds them --
                # a well-mixed line, not a decanter. Taking one layer
                # selectively is what a separatory funnel does, and that is a
                # deliberate Layer 5 operation (``pour_into(phase="lower")``)
                # rather than something a pipe does by itself.
                if kind == VAPOUR:
                    dP = P_a - P_b
                    # Upwinding, written as a full stream from a plus an
                    # INFLOW-ONLY correction toward b's composition. ⚠ Blending
                    # the two compositions instead is what destroyed 0.34 mol of
                    # a refluxing rig's air: at a small positive dP half of an
                    # outflow from a left carrying b's composition, so a could
                    # export a species it did not have. See ``backflow_part``.
                    # This still sums to ``k dP`` exactly at any dP, so the
                    # pressure coupling reflux rests on is unchanged.
                    back = backflow_part(dP, DP_SMOOTH)
                    tot_a, tot_b = nG_a.sum(), nG_b.sum()
                    x_a = nG_a / tot_a if tot_a > 0.0 else np.zeros(n)
                    x_b = nG_b / tot_b if tot_b > 0.0 else np.zeros(n)
                    moves = [(2 * n, k * (dP * x_a + back * (x_b - x_a)))]
                    Cp_donor = CpG_a if dP >= 0.0 else CpG_b
                elif kind == DRAIN:
                    moves = [(0, k * nL1_a), (n, k * nL2_a)]      # one-way, a -> b
                    Cp_donor = CpL_a
                elif kind == METER:
                    tot_a = float(nL1_a.sum() + nL2_a.sum())
                    # A pump moves the donor's solution, not pure anything. With
                    # a dry donor it moves nothing rather than dividing by zero.
                    moves = (
                        [(0, k * nL1_a / tot_a), (n, k * nL2_a / tot_a)]
                        if tot_a > 0.0
                        else [(0, np.zeros(n))]
                    )
                    Cp_donor = CpL_a
                else:
                    raise ValueError(f"unknown edge kind {kind}")

                total_flux = 0.0
                carried = 0.0
                for off, flux in moves:
                    out[a * B + off : a * B + off + n] -= flux
                    out[b * B + off : b * B + off + n] += flux
                    total_flux += float(flux.sum())
                    carried += float(flux @ Cp_donor)

                # Enthalpy travels with the material. Leaving at T_a costs the
                # donor no temperature change; arriving, it drags the receiver
                # toward where it came from. Signed, so a reversed vapour edge
                # warms the other way round without a special case.
                src_T, dst_T = (T_a, T_b) if total_flux >= 0.0 else (T_b, T_a)
                carried *= src_T - dst_T
                if total_flux >= 0.0:
                    out[b * B + 4 * n] += carried / Cp_b
                else:
                    out[a * B + 4 * n] -= carried / Cp_a

            return out

        return rhs

    # -- sparsity ------------------------------------------------------------

    def jac_sparsity(self) -> np.ndarray:
        """Which entries of the Jacobian can be non-zero.

        What this buys is COLUMN GROUPS: ``num_jac`` perturbs together any set of
        columns that share no non-zero row, so a group count below the state size
        is the entire saving and a group count equal to it is no saving at all.

        ⚠ **AND THAT IS EXACTLY WHERE THIS USED TO BE.** Marking a connected pair's
        WHOLE off-diagonal block looked harmlessly conservative and was not:
        measured with ``scipy.optimize._numdiff.group_columns`` on a two-vessel
        twenty-species rig it gave **162 groups out of 162 columns** -- every
        column blocked from grouping with every other, i.e. precisely the dense
        Jacobian the sparsity was passed to avoid, plus the cost of the sparse
        machinery. A four-vessel rig gave 324 of 324.

        The reason is not the one that was expected. It is not the empty second
        liquid layer, and it is not the diagonal blocks -- those are honestly dense
        (perturbing any amount moves the liquid volume, hence the gas volume, hence
        every partial pressure, hence every row). **It is the TEMPERATURE ROW.**
        Marking vessel a's ``dT`` against the whole of vessel b's block means every
        one of b's columns touches a's T row, so no column of b can ever group with
        a column of a, whatever else is or is not marked.

        So the marking is now per edge kind, and each entry below is read straight
        off what that branch of the RHS writes:

        ``THERMAL``   q = UA (T_a - T_b) touches the two T rows and nothing else.
        ``VAPOUR``    the flux is pressure-driven, and a pressure depends on ALL of
                      its vessel's amounts through the gas VOLUME -- so the donor's
                      whole block is marked, but only against the receiver's GAS
                      rows and T row. Both directions: the edge reverses.
        ``DRAIN``     first order in the donor's liquid holdup, so only the donor's
                      two LIQUID blocks (plus its T, which the enthalpy carried
                      depends on) against the receiver's liquid rows and T row.
                      ONE direction only: the flux is ``k * nL_a``, so it is
                      non-negative and the enthalpy always lands on the receiver.
        ``METER``     the same shape as a drain -- a pump moves the donor's solution.

        Measured on that same two-vessel rig: **162 groups -> 102**, a 37% cut in
        RHS evaluations per Jacobian, with more to come on bigger rigs because the
        blocks an edge does NOT touch grow with the species count.

        ⚠ UNDER-MARKING IS SILENTLY WRONG ANSWERS, which is why the reasoning above
        is not the guarantee. ``test_rig`` differences the real Jacobian on a live
        rig state and asserts that every non-negligible entry of it is marked here;
        that test is what makes this safe rather than merely argued.
        """
        size = self.m * self.block
        n, B = self.n, self.block
        s = np.zeros((size, size), dtype=bool)
        for v in range(self.m):
            sl = self.slice_of(v)
            s[sl, sl] = True

        def block_slice(v: int, k: int) -> slice:
            """Amount block ``k`` of vessel ``v``; k == 4 is its temperature."""
            if k == 4:
                return slice(v * B + 4 * n, v * B + 4 * n + 1)
            return slice(v * B + k * n, v * B + (k + 1) * n)

        def couple(rows_v: int, row_blocks, cols_v: int, col_blocks) -> None:
            for rk in row_blocks:
                for ck in col_blocks:
                    s[block_slice(rows_v, rk), block_slice(cols_v, ck)] = True

        LIQUID, GAS, TEMP = (0, 1), (2,), 4
        for j in range(self.edges.count):
            a, b = int(self.edges.a[j]), int(self.edges.b[j])
            kind = int(self.edges.kind[j])
            if kind == THERMAL:
                couple(a, (TEMP,), b, (TEMP,))
                couple(b, (TEMP,), a, (TEMP,))
            elif kind == VAPOUR:
                # A pressure difference reaches every amount in both vessels.
                everything = (0, 1, 2, 3, TEMP)
                couple(b, (*GAS, TEMP), a, everything)
                couple(a, (*GAS, TEMP), b, everything)
            elif kind in (DRAIN, METER):
                couple(b, (*LIQUID, TEMP), a, (*LIQUID, TEMP))
            else:
                raise ValueError(f"unknown edge kind {kind}")
        return s

    def useful_sparsity(self) -> np.ndarray | None:
        """The pattern, or ``None`` when passing it would be pure overhead.

        ⚠ **AND FOR EVERY RIG IN THIS REPO'S TEST SUITE IT IS PURE OVERHEAD**,
        which was not what anybody expected and is the useful finding here.

        Sparsity only ever buys column GROUPS. Measured with the same
        ``group_columns`` that BDF's own sparse path uses, on the topology the slow
        tests actually have -- a pot and a receiver joined by a VAPOUR edge -- the
        refined pattern still gives one group per column, i.e. exactly the dense
        number of RHS evaluations per Jacobian, and then charges sparse ``num_jac``
        and sparse LU on top of it.

        The reason is physical and not a marking mistake. A vapour edge is driven by
        a PRESSURE DIFFERENCE, a pressure is ``nG R T / V_G``, and ``V_G`` is the
        vessel volume minus the volume its LIQUID and SOLID occupy -- so the
        receiver's gas rows genuinely depend on every amount in the donor. Every
        column of the donor therefore marks into the receiver, whose own diagonal
        block already covers all of its rows, so no column of either vessel can
        group with any column of the other. Two vapour-coupled vessels are a dense
        Jacobian, honestly.

        Where it still pays is a rig whose vessels are NOT all fluid-coupled: a
        four-vessel still with a thermal-only leg came out at 52 groups of 68 (76%),
        because a thermal edge touches two temperature rows and nothing else.

        So the pattern is passed when it earns its keep and skipped when it does
        not, which is measured per rig rather than assumed once.
        """
        s = self.jac_sparsity()
        try:
            from scipy.optimize._numdiff import group_columns
            from scipy.sparse import csc_matrix
        except ImportError:                                       # pragma: no cover
            return s
        groups = int(group_columns(csc_matrix(s)).max()) + 1
        return s if groups < s.shape[0] else None

    # -- driving -------------------------------------------------------------

    def split_phases(self, y: np.ndarray) -> np.ndarray:
        """Run each vessel's liquid-liquid phase decision on its own slice.

        Per vessel, unlike ``project``, and the asymmetry is the point: the
        non-negative projection settles a numerical dipole that genuinely
        crosses vessel boundaries, whereas whether a flask holds two layers is a
        fact about what is in THAT flask. Nothing here moves material between
        vessels.
        """
        out = np.array(y, dtype=float, copy=True)
        for v in range(self.m):
            sl = self.slice_of(v)
            out[sl] = self.integrators[v].split_phases(out[sl])
        return out

    def merge_phases(self, y: np.ndarray) -> np.ndarray:
        """Each vessel's merge check, on its own slice. See the vessel's."""
        out = np.array(y, dtype=float, copy=True)
        for v in range(self.m):
            sl = self.slice_of(v)
            out[sl] = self.integrators[v].merge_phases(out[sl])
        return out

    def run(self, y0, t_span, rtol: float = 1e-6, atol: float = 1e-9, **kw):
        y0 = np.asarray(y0, dtype=float)
        for v, integ in enumerate(self.integrators):
            integ.check_state(y0[self.slice_of(v)])
        y0 = self.split_phases(y0)
        rhs = self.make_rhs(
            y0 if vessel_core.FREEZE_LAYER_PERMITTIVITY else None
        )
        t0, t1 = float(t_span[0]), float(t_span[1])

        # Same short-circuit as a single vessel, and for the same reason: the
        # RHS is autonomous, so a vanishing derivative means the constant
        # trajectory is exact, and BDF's num_jac cannot discover that without
        # inflating its perturbation to infinity. A rig sitting idle between
        # steps is the common case, not a corner one.
        dy = rhs(t0, y0)
        if np.all(np.abs(dy) * abs(t1 - t0) <= atol + rtol * np.abs(y0)):
            return _Stationary(t=np.array([t0, t1]), y=np.column_stack([y0, y0]))

        if "jac_sparsity" not in kw:
            pattern = self.useful_sparsity()
            if pattern is not None:
                kw["jac_sparsity"] = pattern
        # ⚠ THE SPARSITY PATTERN HAS TO GO THROUGH ``BoundedJacobian`` RATHER THAN
        # ALONGSIDE IT. BDF ignores ``jac_sparsity`` the moment ``jac`` is
        # callable, so passing both would silently drop the column groups this
        # rig computed -- which is the whole of what the pattern buys, and the
        # 10x it exists to avoid paying. See ``useful_sparsity``.
        if "jac" not in kw:
            kw["jac"] = BoundedJacobian(rhs, atol, kw.pop("jac_sparsity", None))
        return solve_ivp(rhs, t_span, y0, method="BDF", rtol=rtol, atol=atol, **kw)

    def step_until(self, y, dt: float, roots: list, **kw):
        """Advance the whole rig by at most ``dt``, stopping on the first root.

        ⚠ THE POINT OF THIS EXISTING AT ALL IS THAT THE ROOT MUST BE FOUND ON THE
        COUPLED TRAJECTORY. ``World`` used to satisfy a wait by integrating the
        owner vessel ALONE and then stepping the others forward by however long
        that took -- correct for a bench of separate flasks and wrong for
        glassware. A still head's temperature is set almost entirely by what is
        arriving from the pot, so locating "the head reaches 353 K" against a
        decoupled head finds an instant that does not exist in the real run. Every
        cut in a fractional distillation is called off exactly that number.

        Same contract as ``VesselIntegrator.step_until`` and deliberately so:
        ``roots`` are plain ``f(t, y) -> float`` over the RIG's state vector, with
        **f < 0 meaning "not yet" and f >= 0 meaning "satisfied"**, and the three
        cases that version handles are handled the same way here -- already true
        before integrating, a rig at rest, and a failed solve told apart from a
        terminal event. See that docstring for why each one matters.
        """
        from chemsim.numerics.vessel_integrator import RootStop

        y0 = np.asarray(y, dtype=float)
        for i, f in enumerate(roots):
            if float(f(0.0, y0)) >= 0.0:
                return RootStop(y=y0.copy(), elapsed=0.0, fired=i, already=True)

        events = []
        for f in roots:
            def event(t, yy, _f=f):
                return float(_f(t, yy))
            event.terminal = True
            event.direction = 1.0        # upward only -- see the sign convention
            events.append(event)

        sol = self.run(y0, (0.0, float(dt)), events=events, **kw)
        if not sol.success:
            raise RuntimeError(
                f"rig integration failed after {float(sol.t[-1]):.4g} s of "
                f"{dt:.4g} s while waiting for a condition: {sol.message}"
            )
        # ⚠ RAW AND PER VESSEL, before the rig-wide projection tidies anything --
        # the same reason ``Rig.run`` does it this way: a cancelling dipole
        # straddling two vessels would be settled and invisible afterwards.
        for v, sub in enumerate(self.integrators):
            sub.check_raw_solution(sol.y[self.slice_of(v), -1])
        fired = None
        for i, times in enumerate(getattr(sol, "t_events", None) or []):
            if times is not None and len(times):
                fired = i
                break
        elapsed = float(sol.t[-1]) if fired is not None else float(dt)
        return RootStop(
            y=self.project(sol.y[:, -1]),
            elapsed=elapsed,
            fired=fired,
            already=False,
        )

    def project(self, y: np.ndarray) -> np.ndarray:
        """Non-negative projection over the WHOLE rig, conserving every species.

        Deliberately across all vessels at once rather than vessel by vessel. A
        cancelling numerical pair does not respect vessel boundaries: in the
        measured two-vessel case water finished 2.4e-7 mol short in the hot vessel
        and 2.4e-7 long in the cold one, so a per-vessel projection would have had
        nothing to settle the hot side against and would have created the amount
        that the cold side was holding. The rig conserves each species as one
        system -- that is the whole reason it is one state vector -- so the
        projection has to see it as one too.

        See ``project_non_negative`` for what the projection is and why the
        ``np.maximum`` it replaces was creating matter.
        """
        out = np.array(y, dtype=float, copy=True)
        n, B = self.n, self.block
        blocks = [
            out[v * B + k * n : v * B + (k + 1) * n]
            for v in range(self.m)
            for k in range(4)
        ]
        fixed, created = project_non_negative(blocks)
        for j, (v, k) in enumerate(
            (v, k) for v in range(self.m) for k in range(4)
        ):
            out[v * B + k * n : v * B + (k + 1) * n] = fixed[j]
        # Attributed to the first vessel: the residual is a property of the
        # coupled system, and picking a block to hang it on beats dropping it.
        self.integrators[0].created += created
        return out

    def step(self, y: np.ndarray, dt: float, **kw) -> np.ndarray:
        sol = self.run(y, (0.0, dt), **kw)
        if not sol.success:
            # Per vessel, and named, because a rig is one stiff system but the
            # fragile state is always in a particular flask.
            lines = [f"rig integration failed: {sol.message}"]
            for v, integ in enumerate(self.integrators):
                for note in integ.diagnose(y[self.slice_of(v)]):
                    lines.append(f"  - vessel {v}: {note}")
            raise RuntimeError(chr(10).join(lines))
        # ⚠ RAW, per vessel, BEFORE the projection -- which for a rig runs across
        # all vessels at once, so a dipole that straddles two of them would be
        # cancelled and gone before anything looked. See
        # ``VesselIntegrator.check_raw_solution``.
        for v, integ in enumerate(self.integrators):
            integ.check_raw_solution(sol.y[self.slice_of(v), -1])
        return self.merge_phases(self.project(sol.y[:, -1]))

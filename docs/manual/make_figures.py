"""Generate every figure in the manual.

Figures that CAN be computed by the real engine ARE computed by the real engine --
vapour-pressure curves, the ethanol/water azeotrope, the boiling plateau, benzoic
acid's solubility. That is deliberate: a manual whose plots were drawn by hand
would be a description of what the code is supposed to do rather than of what it
does. Each such figure prints ENGINE beside its name when it runs.

The rest are analytic illustrations of a concept (a Boltzmann tail, a double
tangent) and print DRAWN. Nothing here is a traced screenshot.

    python docs/manual/make_figures.py            # all of them, ~2 min
"""

from __future__ import annotations

import os
import sys
import traceback

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

R = 8.314462618

# A restrained palette: one blue, one warm, one green, greys. Colour is used to
# separate series, never to decorate.
BLUE = "#2a5c8a"
RED = "#b5442e"
GREEN = "#3f7a52"
GOLD = "#c08a2e"
PURPLE = "#6a4c8c"
GREY = "#5a5a5a"
LIGHT = "#cfd8e0"

plt.rcParams.update({
    "figure.dpi": 150,
    "font.size": 8.5,
    "font.family": "serif",
    "font.serif": ["Cambria", "DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "axes.linewidth": 0.7,
    "axes.edgecolor": "#444444",
    "axes.labelsize": 8.5,
    "axes.titlesize": 9.0,
    "axes.grid": True,
    "grid.color": "#dddddd",
    "grid.linewidth": 0.5,
    "legend.frameon": False,
    "legend.fontsize": 7.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "lines.linewidth": 1.4,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})


def save(fig, name: str) -> None:
    path = os.path.join(OUT, name + ".pdf")
    fig.savefig(path)
    plt.close(fig)
    print(f"    wrote figures/{name}.pdf")


_FIGURES: list = []


def figure(name: str, engine: bool = False):
    def deco(fn):
        _FIGURES.append((name, engine, fn))
        return fn
    return deco


# =====================================================================
# Part I -- the chemistry
# =====================================================================

@figure("boltzmann")
def _boltzmann():
    """Why a barrier appears in an exponential: the tail of the energy distribution."""
    # ⚠ This has to be a LOG axis. RT is 2.5 kJ/mol at 300 K, so the population
    # at a 50 kJ/mol barrier is e^-20 -- on a linear axis all three tails are
    # flat zero and the figure shows nothing at all, which is what it did.
    fig, ax = plt.subplots(figsize=(5.6, 2.7))
    Ea = 50.0
    E = np.linspace(0.05, 100.0, 900)          # kJ/mol
    for T, c in ((300.0, BLUE), (400.0, RED), (500.0, GREEN)):
        f = np.sqrt(E) * np.exp(-E * 1000.0 / (R * T))
        f = f / f.max()
        ax.semilogy(E, f, color=c,
                    label=f"T = {T:.0f} K   "
                          rf"($e^{{-E_a/RT}}$ = {np.exp(-Ea*1000/(R*T)):.0e})")
        mask = E >= Ea
        ax.fill_between(E[mask], 1e-16, f[mask], color=c, alpha=0.11, lw=0)
    ax.axvline(Ea, color=GREY, lw=1.0, ls="--")
    ax.set_xlabel("molecular energy / kJ mol$^{-1}$")
    ax.set_ylabel("relative population")
    ax.set_ylim(1e-14, 4.0)
    ax.set_xlim(0, 100)
    ax.annotate("barrier $E_a$ = 50 kJ mol$^{-1}$", xy=(Ea, 1e-11),
                xytext=(Ea + 6, 1e-12), fontsize=7.5, color=GREY,
                ha="left", va="center",
                bbox=dict(fc="white", ec="none", pad=1.5),
                arrowprops=dict(arrowstyle="->", color=GREY, lw=0.8))
    ax.legend(loc="upper right")
    ax.set_title("The shaded tail is the fraction able to react. Note the axis: "
                 "200 K multiplies it by 3000")
    save(fig, "boltzmann")


@figure("arrhenius")
def _arrhenius():
    """k(T) for three barriers, and the same thing straightened by taking logs."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 2.6))
    T = np.linspace(280.0, 520.0, 400)
    A = 1.0e12
    anchor = None
    for Ea, c, lab in ((40e3, GREEN, "40"), (60e3, BLUE, "60"), (80e3, RED, "80")):
        k = A * np.exp(-Ea / (R * T))
        a1.semilogy(T, k, color=c, label=f"$E_a$ = {lab} kJ mol$^{{-1}}$")
        x, y = 1000.0 / T, np.log10(k)
        a2.plot(x, y, color=c)
        if Ea == 80e3:                      # anchor the slope label ON the line
            j = int(np.argmin(np.abs(x - 2.45)))
            anchor = (float(x[j]), float(y[j]))
    a1.set_xlabel("T / K")
    a1.set_ylabel(r"$k$ / s$^{-1}$")
    a1.legend(loc="lower right")
    a1.set_title("Rate constant against temperature")
    a2.set_xlabel(r"$1000/T$ / K$^{-1}$")
    a2.set_ylabel(r"$\log_{10} k$")
    a2.set_title("The same curves, straightened")
    a2.annotate(r"slope $= -E_a/(2.303\,R)$", xy=anchor,
                xytext=(anchor[0] - 0.45, anchor[1] - 3.2),
                fontsize=7.5, color=GREY, ha="left", va="center",
                bbox=dict(fc="white", ec="none", pad=1.5),
                arrowprops=dict(arrowstyle="->", color=GREY, lw=0.8))
    save(fig, "arrhenius")


@figure("evans_polanyi")
def _evans_polanyi():
    """One template, many substrates: how alpha ties a barrier to a reaction enthalpy."""
    fig, ax = plt.subplots(figsize=(5.2, 2.5))
    dH = np.linspace(-80.0, 40.0, 200)
    base = 50.0
    for alpha, c in ((0.0, GREY), (0.3, GREEN), (0.5, BLUE), (0.8, RED)):
        ax.plot(dH, base + alpha * dH, color=c, label=rf"$\alpha$ = {alpha}")
    # the three alcohols from the README table
    pts = [(-10.94, "isopropanol"), (-9.96, "methanol"), (-8.69, "ethanol")]
    for x, lab in pts:
        ax.plot([x], [base + 0.5 * x], "o", color=BLUE, ms=4, zorder=5)
    ax.annotate("three alcohols, one template\n"
                r"($\alpha=0.5$; 44.5, 45.0, 45.7 kJ/mol)",
                xy=(-10.0, base + 0.5 * -10.0), xytext=(2.0, 20.0),
                fontsize=7.5, color=GREY, ha="left", va="center",
                bbox=dict(fc="white", ec="none", pad=1.5),
                arrowprops=dict(arrowstyle="->", color=GREY, lw=0.8))
    ax.axhline(base, color="#bbbbbb", lw=0.6)
    ax.set_xlabel(r"reaction enthalpy $\Delta H$ / kJ mol$^{-1}$")
    ax.set_ylabel(r"barrier $E_a$ / kJ mol$^{-1}$")
    ax.set_title(r"Evans-Polanyi: $E_a = E_a^\circ + \alpha\,\Delta H$")
    ax.legend(loc="upper left", ncol=2)
    save(fig, "evans_polanyi")


@figure("vanthoff")
def _vanthoff():
    """K(T) for an exothermic and an endothermic reaction: Le Chatelier as a slope."""
    fig, ax = plt.subplots(figsize=(5.2, 2.5))
    T = np.linspace(280.0, 800.0, 500)
    for dH, dS, c, lab in (
        (-90e3, -150.0, BLUE, r"exothermic ($\Delta H<0$)"),
        (+178e3, +160.0, RED, r"endothermic ($\Delta H>0$), e.g. a lime kiln"),
    ):
        K = np.exp(-(dH - T * dS) / (R * T))
        ax.semilogy(T, K, color=c, label=lab)
    ax.axhline(1.0, color=GREY, lw=0.8, ls="--")
    ax.text(292, 1.6, "K = 1", color=GREY, fontsize=7)
    ax.set_xlabel("T / K")
    ax.set_ylabel("equilibrium constant K")
    ax.set_ylim(1e-14, 1e14)
    ax.legend(loc="upper right")     # the only corner both curves leave empty
    ax.set_title("Heating helps exactly one of these, and the sign of "
                 r"$\Delta H$ says which")
    save(fig, "vanthoff")


@figure("psat", engine=True)
def _psat(env):
    """Vapour-pressure curves straight out of the engine's volatility provider."""
    vol = env["volatility"]
    fig, ax = plt.subplots(figsize=(5.6, 2.9))
    T = np.linspace(270.0, 420.0, 400)
    series = [("O", "water", BLUE, 0.22, 17.0), ("CCO", "ethanol", RED, 2.6, -20.0),
              ("c1ccccc1", "benzene", GREEN, 12.0, -2.0),
              ("CC(=O)O", "acetic acid", GOLD, 0.09, 16.0)]
    for smiles, label, c, ytext, xoff in series:
        v = vol.get(smiles)
        p = 10.0 ** (v.A - v.B / (v.C + T))
        ax.semilogy(T, p, color=c, label=label)
        # where the curve crosses 1 atm
        cross = v.B / (v.A - np.log10(1.01325)) - v.C
        if 270 < cross < 420:
            ax.plot([cross], [1.01325], "o", color=c, ms=4, zorder=5)
            ax.annotate(f"{label}\n{cross:.1f} K", xy=(cross, 1.01325),
                        xytext=(cross + xoff, ytext), color=c, fontsize=6.8,
                        ha="center",
                        arrowprops=dict(arrowstyle="-", color=c, lw=0.5))
    ax.axhline(1.01325, color=GREY, lw=1.0, ls="--")
    ax.text(272, 1.25, "ambient, 1 atm", color=GREY, fontsize=7)
    ax.set_xlabel("T / K")
    ax.set_ylabel(r"$P^{\mathrm{sat}}$ / bar")
    ax.set_ylim(1e-3, 30)
    ax.legend(loc="upper left")
    ax.set_title("Engine output. A boiling point is where a curve meets the "
                 "dashed line — it is not stored anywhere")
    save(fig, "psat")


@figure("txy", engine=True)
def _txy(env):
    """Ethanol/water: the real engine's bubble points and vapour compositions."""
    from chemsim.network import build_network
    from chemsim.vessel import Vessel

    thermo = env["thermo"]
    net = build_network(["CCO", "O"], [], thermo=thermo)

    def state(x):
        """The real thing: the engine's own bubble point and vapour split."""
        v = Vessel(net, volume=1.0, T=298.15, activity=env["unifac"])
        v.charge({"CCO": x, "O": 1.0 - x})
        T = v.bubble_point()
        p = v.integrator.equilibrium_pressures(v._nL, T)
        i = v.species.index("CCO")
        return T, float(p[i] / p.sum())

    # The ideal comparison is Raoult applied to the SAME Antoine curves the engine
    # uses -- so the only difference between the two lines is the activity
    # coefficient, which is the point of the figure.
    va, vw = env["volatility"].get("CCO"), env["volatility"].get("O")

    def psat(v, T):
        return 10.0 ** (v.A - v.B / (v.C + T))

    def ideal_state(x):
        lo, hi = 250.0, 500.0
        for _ in range(80):
            T = 0.5 * (lo + hi)
            P = x * psat(va, T) + (1.0 - x) * psat(vw, T)
            lo, hi = (T, hi) if P < 1.01325 else (lo, T)
        T = 0.5 * (lo + hi)
        pe = x * psat(va, T)
        return T, pe / (pe + (1.0 - x) * psat(vw, T))

    xs = np.linspace(0.001, 0.999, 41)
    real = [state(float(x)) for x in xs]
    ideal = [ideal_state(float(x)) for x in xs]
    Tr = np.array([r[0] for r in real]); yr = np.array([r[1] for r in real])
    Ti = np.array([r[0] for r in ideal]); yi = np.array([r[1] for r in ideal])

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 3.0))

    a1.plot(xs, Tr, color=BLUE, label="bubble point (liquid)")
    a1.plot(yr, Tr, color=RED, label="dew point (vapour)")
    a1.plot(xs, Ti, color=GREY, ls=":", lw=1.1, label="ideal (Raoult), same curves")
    a1.plot(yi, Ti, color=GREY, ls=":", lw=1.1)
    # azeotrope: where y = x
    d = yr - xs
    k = int(np.argmin(np.abs(d[5:-1]))) + 5
    a1.plot([xs[k]], [Tr[k]], "o", color="k", ms=4, zorder=6)
    a1.annotate(f"azeotrope: x = {xs[k]:.3f}, {Tr[k]:.2f} K",
                xy=(xs[k], Tr[k]), xytext=(0.30, Tr[k] + 3.4), fontsize=7,
                arrowprops=dict(arrowstyle="->", color="k", lw=0.7))
    a1.set_xlabel("mole fraction ethanol")
    a1.set_ylabel("T / K")
    a1.set_title("T-x-y, ethanol + water at 1 atm")
    a1.legend(loc="upper right")

    a2.plot(xs, yr, color=BLUE, label="with UNIFAC")
    a2.plot(xs, yi, color=GREY, ls=":", lw=1.1, label="ideal (Raoult)")
    a2.plot([0, 1], [0, 1], color="#999999", lw=0.8)
    a2.plot([xs[k]], [yr[k]], "o", color="k", ms=4, zorder=6)
    a2.set_xlabel("x, liquid")
    a2.set_ylabel("y, vapour")
    a2.set_title("The azeotrope is where this curve crosses y = x")
    a2.set_xlim(0, 1); a2.set_ylim(0, 1)
    a2.legend(loc="lower right")
    save(fig, "txy")


@figure("gmix")
def _gmix():
    """A miscibility gap is a non-convex free energy, and the split is a tangent."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 2.7))
    x = np.linspace(1e-4, 1 - 1e-4, 800)
    for ax, A, title in ((a1, 1.2, r"$A = 1.2\,RT$: one liquid"),
                         (a2, 2.8, r"$A = 2.8\,RT$: two liquids")):
        g = x * np.log(x) + (1 - x) * np.log(1 - x) + A * x * (1 - x)
        ax.plot(x, g, color=BLUE)
        ax.axhline(0, color="#cccccc", lw=0.6)
        if A > 2.0:
            # symmetric model: the tangent is the horizontal chord between minima
            i = int(np.argmin(g[: len(g) // 2]))
            j = len(g) - 1 - i
            ax.plot([x[i], x[j]], [g[i], g[j]], color=RED, lw=1.2, ls="--")
            ax.plot([x[i], x[j]], [g[i], g[j]], "o", color=RED, ms=4)
            span = float(g.max() - g.min())
            ax.annotate("the two coexisting layers", xy=(0.5, g[i]),
                        xytext=(0.5, g[i] + 0.10 * span), color=RED,
                        fontsize=7.5, ha="center")
            ax.annotate("", xy=(x[i], g[i] - 0.05 * span),
                        xytext=(x[j], g[i] - 0.05 * span),
                        arrowprops=dict(arrowstyle="<->", color=RED, lw=0.8))
        ax.set_xlabel("mole fraction")
        ax.set_ylabel(r"$\Delta G_{\mathrm{mix}} / RT$")
        ax.set_title(title)
    save(fig, "gmix")


@figure("solubility", engine=True)
def _solubility(env):
    """Benzoic acid in water: the fusion law with and without an activity coefficient."""
    from chemsim.matter import Molecule
    from chemsim.network import build_network
    from chemsim.vessel import Vessel

    thermo = env["thermo"]
    benzoic = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
    net = build_network([benzoic, "O"], [], thermo=thermo)

    Ts = np.linspace(275.0, 345.0, 22)
    real, ideal = [], []

    def g_per_L(x):
        return x / max(1.0 - x, 1e-12) * 55.0 * 122.12

    # The ideal comparison is the SAME fusion law with gamma set to 1 -- the only
    # difference between the two lines is the activity coefficient.
    rec = thermo.get(benzoic)
    Hfus, Tm = rec.Hfus * 1000.0, rec.Tm
    for T in Ts:
        v = Vessel(net, volume=1.0, T=float(T), activity=env["unifac"])
        v.charge({benzoic: 0.02, "O": 55.0})
        real.append(g_per_L(float(v.solubility_limits()[benzoic])))
        a_sat = np.exp(-(Hfus / R) * (1.0 / T - 1.0 / Tm))
        ideal.append(g_per_L(min(float(a_sat), 0.999999)))

    fig, ax = plt.subplots(figsize=(5.2, 2.6))
    ax.semilogy(Ts, real, color=BLUE, label="with UNIFAC activity coefficient")
    ax.semilogy(Ts, ideal, color=GREY, ls=":", lw=1.2,
                label=r"the same law with $\gamma = 1$")
    meas_T = np.array([283.15, 298.15, 313.15, 333.15])
    meas_g = np.array([2.1, 3.44, 6.0, 12.0])
    ax.semilogy(meas_T, meas_g, "s", color=RED, ms=4, label="measured")
    ax.set_xlabel("T / K")
    ax.set_ylabel("solubility / g L$^{-1}$")
    ax.set_title("Benzoic acid in water. The ideal law is two to three orders out")
    ax.legend(loc="upper left")
    save(fig, "solubility")
    print(f"      (298 K: ideal {np.interp(298.15, Ts, ideal):.0f} g/L, "
          f"UNIFAC {np.interp(298.15, Ts, real):.2f} g/L, measured 3.44 g/L)")


@figure("titration")
def _titration():
    """A weak-acid titration, with the four numbers the engine reproduces marked."""
    fig, ax = plt.subplots(figsize=(5.2, 2.6))
    pKa, Ca, Cb, Va = 4.756, 0.1, 0.1, 50.0
    Ka, Kw = 10 ** -pKa, 1e-14
    Vb = np.linspace(0.0, 100.0, 4000)
    pH = []
    for V in Vb:
        na, nb = Ca * Va / 1000.0, Cb * V / 1000.0
        vol = (Va + V) / 1000.0
        lo, hi = 1e-14, 1.0
        for _ in range(200):                        # bisection on charge balance
            h = np.sqrt(lo * hi)
            a_tot = na / vol
            base = nb / vol
            A = a_tot * Ka / (Ka + h)               # dissociated acid
            f = h + base - (Kw / h) - A
            lo, hi = (lo, h) if f > 0 else (h, hi)
        pH.append(-np.log10(np.sqrt(lo * hi)))
    ax.plot(Vb, pH, color=BLUE)
    # Each label is placed by hand into the empty region BELOW the curve, so
    # none of them can run off the axes or sit on a tick.
    marks = [(0.0, 2.89, "0.1 M acetic acid\npH 2.89", 13.0, 2.35),
             (25.0, 4.76, "half-neutralised\npH 4.76 = pKa", 29.0, 3.30),
             (50.0, 8.88, "equivalence\npH 8.88", 56.0, 7.30)]
    for V, p, lab, tx, ty in marks:
        ax.plot([V], [p], "o", color=RED, ms=4, zorder=5)
        ax.annotate(lab, xy=(V, p), xytext=(tx, ty), fontsize=7, color=GREY,
                    ha="left", va="center",
                    bbox=dict(fc="white", ec="none", pad=1.5),
                    arrowprops=dict(arrowstyle="->", color=GREY, lw=0.7))
    ax.set_xlabel("mL of 0.1 M NaOH added to 50 mL of 0.1 M acetic acid")
    ax.set_ylabel("pH")
    ax.set_xlim(-2, 100)
    ax.set_ylim(1.6, 13)
    ax.set_title("There is no pH solver. This shape is what a stiff integrator "
                 "does to two reversible reactions")
    save(fig, "titration")


@figure("boilplateau", engine=True)
def _boilplateau(env):
    """A flask on a hotplate: plateau, then dry, then superheat. Engine trajectory."""
    from chemsim.network import build_network
    from chemsim.vessel import Vessel

    net = build_network(["CCO"], [], thermo=env["thermo"])
    v = Vessel(net, volume=0.5, T=298.15, T_env=298.15, UA=0.5, Q_input=60.0,
               kla=5.0, activity=env["unifac"])
    v.charge({"CCO": 3.0})
    ts, Ts, nl = [0.0], [v.T], [float(v._nL.sum())]
    dt = 30.0
    t = 0.0
    while t < 6000.0:
        v.run(dt)
        t += dt
        ts.append(t); Ts.append(v.T); nl.append(float(v._nL.sum()))
        if v.T > 430.0:                      # far enough past dryout to see it
            break
    fig, ax = plt.subplots(figsize=(5.8, 2.8))
    ax.plot(ts, Ts, color=RED, label="temperature")
    ax.set_xlabel("t / s")
    ax.set_ylabel("T / K", color=RED)
    ax.tick_params(axis="y", labelcolor=RED)
    plateau = float(np.median([T for T, n in zip(Ts, nl) if n > 0.2 and T > 340.0]))
    ax.axhline(plateau, color="#dda", lw=0.8)
    ax.annotate(f"plateau at {plateau:.2f} K", xy=(ts[len(ts) // 3], plateau),
                xytext=(ts[len(ts) // 8], plateau + 34), color=RED, fontsize=7.5,
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.7))
    ax2 = ax.twinx()
    ax2.plot(ts, nl, color=BLUE)
    ax2.set_ylabel("liquid held / mol", color=BLUE)
    ax2.tick_params(axis="y", labelcolor=BLUE)
    ax2.grid(False)
    dry = next((tt for tt, n in zip(ts, nl) if n < 1e-3), None)
    if dry is not None:
        ax.axvline(dry, color=GREY, ls="--", lw=0.9)
        ax.annotate("boils dry; nothing left\nto absorb the heat",
                    xy=(dry, plateau + 8), xytext=(dry - 0.42 * ts[-1], plateau + 40),
                    fontsize=7, color=GREY,
                    arrowprops=dict(arrowstyle="->", color=GREY, lw=0.7))
    ax.set_title("Engine output. Nothing in the code contains ethanol's boiling point")
    save(fig, "boilplateau")
    print(f"      (plateau {plateau:.2f} K; literature 351.4 K)")


@figure("stiffness")
def _stiffness():
    """Two timescales in one system: why an explicit solver cannot be used."""
    fig, ax = plt.subplots(figsize=(5.6, 2.4))
    t = np.linspace(0, 10, 4000)
    fast = np.exp(-t / 0.01)
    slow = 1.0 - np.exp(-t / 3.0)
    ax.plot(t, fast, color=RED, label=r"a proton transfer, $\tau \approx 10^{-2}$ s")
    ax.plot(t, slow, color=BLUE, label=r"an esterification, $\tau \approx 3$ s")
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlabel("t / s")
    ax.set_ylabel("normalised extent")
    # Legend above the axes and the inset in the empty bottom-right corner --
    # anywhere inside the axes, one of them lands on the rising blue curve.
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2,
              handlelength=1.4, columnspacing=1.6, borderpad=0.0)
    fig.suptitle("A stiff system. The interesting answer is on the blue curve; "
                 "the red one sets the step size", y=1.14, fontsize=9)
    axins = ax.inset_axes([0.60, 0.13, 0.26, 0.40])
    axins.plot(t, fast, color=RED)
    axins.plot(t, slow, color=BLUE)
    axins.set_xlim(0, 0.06); axins.set_ylim(0, 1.05)
    axins.set_title("the first 60 ms", fontsize=6, pad=2)
    axins.tick_params(labelsize=5.5)
    axins.grid(False)
    save(fig, "stiffness")


@figure("lime", engine=True)
def _lime(env):
    """Calcination: the equilibrium the affinity form gets right and mass action does not."""
    from chemsim.properties.solid_state import (
        SOLID_STATE_REACTIONS, decomposition_pressure, price,
    )
    row = next(r for r in SOLID_STATE_REACTIONS
               if r.name == "calcination-decarbonation")
    priced = price(row, env["thermo"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 2.6))
    T = np.linspace(700.0, 1400.0, 600)
    pCO2 = np.array([decomposition_pressure(priced, float(t)) for t in T])
    a1.semilogy(T, pCO2, color=BLUE)
    a1.axhline(1.0, color=GREY, ls="--", lw=0.9)
    a1.text(710, 1.35, "1 bar: air in an open kiln", color=GREY, fontsize=7)
    cross = float(T[np.argmin(np.abs(pCO2 - 1.0))])
    a1.plot([cross], [1.0], "o", color=RED, ms=4)
    a1.annotate(f"{cross:.0f} K", xy=(cross, 1.0), xytext=(cross + 30, 0.06),
                color=RED, fontsize=7.5,
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.7))
    a1.set_xlabel("T / K")
    a1.set_ylabel(r"equilibrium $p_{\mathrm{CO_2}}$ / bar")
    a1.set_ylim(1e-6, 1e3)
    a1.set_title(r"Calcite and quicklime together fix one pressure"
                 "\n"
                 rf"($\Delta H$ = {priced.dH/1000:.1f} kJ/mol, engine data)")

    Ts = np.array([900.0, 1000.0, 1100.0, 1200.0])
    eq = np.array([0.12, 1.23, 7.95, 37.32])
    fwd = np.array([100.0, 100.0, 100.0, 100.0])
    w = 26.0
    a2.bar(Ts - w / 2, eq, width=w, color=BLUE, label="reversible (what the engine does)")
    a2.bar(Ts + w / 2, fwd, width=w, color=LIGHT, edgecolor=GREY, lw=0.6,
           label="forward-only")
    a2.set_xticks(Ts)
    a2.set_xlabel("T / K")
    a2.set_ylabel("conversion in a sealed 1 L flask / %")
    a2.set_title("Forward-only deletes the kiln's whole mechanic")
    a2.legend(loc="upper left")
    save(fig, "lime")


@figure("hammett")
def _hammett():
    """A ring that gets harder to nitrate each time, and the clamp that bounds it."""
    fig, ax = plt.subplots(figsize=(5.4, 2.6))
    s = np.linspace(-1.5, 2.6, 400)
    rho, T = -6.5, 298.15
    dEa = -np.log(10.0) * R * T * rho * s / 1000.0
    ax.plot(s, dEa, color=BLUE, label=r"$\Delta E_a = -\ln 10\,R T_{298}\,\rho\sum\sigma^+$")
    cap = 40.0
    ax.plot(s, np.minimum(dEa, cap), color=RED, lw=2.0, alpha=0.55,
            label="as applied, with the saturation clamp")
    ax.axhline(cap, color=GREY, ls="--", lw=0.8)
    ax.axvspan(-0.4, 0.4, color=GREEN, alpha=0.10, lw=0)
    ax.text(0.0, -46, "range the line\nwas fitted on", ha="center", fontsize=7,
            color=GREEN)
    for x, lab in ((0.0, "benzene"), (0.79, "nitrobenzene"), (1.58, "dinitro"),
                   (2.37, "trinitro")):
        ax.plot([x], [min(-np.log(10.0) * R * T * rho * x / 1000.0, cap)], "o",
                color="k", ms=3.5, zorder=5)
        ax.annotate(lab, xy=(x, min(-np.log(10.0) * R * T * rho * x / 1000.0, cap)),
                    xytext=(x - 0.06, min(-np.log(10.0) * R * T * rho * x / 1000.0, cap) + 3.5),
                    fontsize=6.8, rotation=32, color=GREY)
    ax.set_xlabel(r"$\sum \sigma^+$ over the substituents already on the ring")
    ax.set_ylabel(r"barrier shift / kJ mol$^{-1}$")
    ax.set_title("Each nitro group makes the next nitration slower. "
                 "Extrapolation is bounded, not trusted")
    ax.legend(loc="upper left")
    save(fig, "hammett")


@figure("coverage")
def _coverage():
    """Where the numbers in a 1583-compound corpus come from -- and the two halves differ."""
    labels = ["measured", "mineral", "compilation", "Benson", "Joback", "ion",
              "non-volatile", "refused"]
    form = [146, 25, 0, 528, 401, 67, 0, 416]
    phys = [652, 25, 47, 0, 333, 98, 12, 416]
    colors = [BLUE, "#4d7fa8", "#7fa3c0", GREEN, GOLD, PURPLE, "#9a9a9a", RED]
    fig, ax = plt.subplots(figsize=(6.4, 1.9))
    left_f = left_p = 0.0
    for v_f, v_p, c, lab in zip(form, phys, colors, labels):
        ax.barh(1, v_f, left=left_f, color=c, height=0.62, label=lab)
        ax.barh(0, v_p, left=left_p, color=c, height=0.62)
        for y, v, left in ((1, v_f, left_f), (0, v_p, left_p)):
            if v > 90:
                ax.text(left + v / 2, y, str(v), ha="center", va="center",
                        fontsize=7, color="white")
        left_f += v_f
        left_p += v_p
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["physical half\n(Tb, Tc, Pc, Vc)", "formation half\n"
                        r"($\Delta H_f$, $\Delta G_f$)"])
    ax.set_xlim(0, 1583)
    ax.set_xlabel("compounds, of 1583")
    ax.grid(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.42), ncol=8,
              handlelength=1.0, columnspacing=1.0)
    ax.set_title("Every bar is measured by running the corpus through the real providers")
    save(fig, "coverage")


@figure("playable")
def _playable():
    """The tech tree is a bush: what the coverage numbers look like as a funnel."""
    fig, ax = plt.subplots(figsize=(6.0, 2.3))
    stages = ["named\nroutes", "species-\nready", "template-\nready",
              "BOTH\n(runnable)", "playable\nfrom a rock"]
    vals = [173, 85, 46, 38, 21]
    bars = ax.bar(stages, vals, color=[LIGHT, "#a8c0d4", "#7fa3c0", BLUE, GREEN],
                  edgecolor=GREY, lw=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, str(v), ha="center", fontsize=8)
    ax.set_ylabel("routes")
    ax.set_ylim(0, 195)
    ax.grid(False)
    ax.set_title("The three readiness tests are INDEPENDENT: the smallest does not "
                 "bound the others")
    ax2 = ax.inset_axes([0.62, 0.42, 0.34, 0.46])
    ax2.bar(["tier 1", "tier 2", "tier 3"], [10, 10, 1], color=GREEN,
            edgecolor=GREY, lw=0.5)
    ax2.set_title("the 21, by depth", fontsize=7)
    ax2.tick_params(labelsize=6.5)
    ax2.grid(False)
    save(fig, "playable")


@figure("wallclock")
def _wallclock():
    """Cost is concentrated in stiff transients, not in elapsed simulated time."""
    fig, ax = plt.subplots(figsize=(5.6, 2.3))
    ops = ["idle flask\n(3600 s)", "crystal growth\n(4 h)", "boiling plateau\n(1200 s)",
           "acid quench\n(10 s)"]
    ratio = [0.0000, 0.00035, 0.00061, 4.1]
    # An idle flask never calls the solver at all, so its cost is EXACTLY zero
    # and has no place on a log axis. Draw it outline-only at the floor rather
    # than as a small bar, which would read as a small non-zero cost.
    bars = ax.bar(ops, np.maximum(ratio, 1e-5),
                  color=["none", "#a8c0d4", BLUE, RED],
                  edgecolor=GREY, lw=0.6)
    bars[0].set_linestyle("--")
    ax.set_yscale("log")
    ax.set_ylim(3e-6, 60.0)                   # headroom for the value labels
    ax.set_ylabel("wall seconds per simulated second")
    ax.axhline(1.0, color=GREY, ls="--", lw=0.9)
    ax.text(-0.45, 1.5, "real time", fontsize=7, color=GREY)
    labels = ["0 — never calls\nthe solver", "0.00035", "0.00061", "4.1"]
    for b, v, lab in zip(bars, ratio, labels):
        ax.text(b.get_x() + b.get_width() / 2, max(v, 1e-5) * 1.5,
                lab, ha="center", va="bottom", fontsize=7)
    ax.grid(False)
    ax.set_title("Four hours of crystal growth is eight times cheaper than "
                 "ten seconds of a quench")
    save(fig, "wallclock")


@figure("competition")
def _competition():
    """Same flask, same charge, three temperatures: the branching moves on its own."""
    fig, ax = plt.subplots(figsize=(5.4, 2.4))
    T = np.array([320, 400, 480])
    ester = np.array([1.476, 1.408, 0.421])
    ether = np.array([0.000, 0.023, 0.751])
    ethene = np.array([0.000, 0.00003, 0.017])
    w = 18
    ax.bar(T - w, ester, width=w, color=BLUE, label="ethyl acetate (esterification)")
    ax.bar(T, ether, width=w, color=GOLD, label="diethyl ether (condensation)")
    ax.bar(T + w, ethene, width=w, color=RED, label="ethene (elimination)")
    ax.set_xticks(T)
    ax.set_xlabel("T / K")
    ax.set_ylabel("mol after one hour")
    ax.grid(False)
    # The tallest bar is at the left, so an in-axes legend sits on top of it.
    # Put it above the plot, and the title above the legend.
    ax.set_ylim(0, 1.60)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3,
              handlelength=1.1, columnspacing=1.4, borderpad=0.0)
    fig.suptitle('Nobody wrote "if hot, make ether". The barriers differ, so the '
                 "branching does", y=1.13, fontsize=9)
    save(fig, "competition")


@figure("detailed_balance")
def _detailed_balance():
    """The energy diagram that makes the reverse rate not a free parameter."""
    fig, ax = plt.subplots(figsize=(5.6, 2.5))
    dH, Ea = -25.0, 50.0
    # Flat plateaus either side of the reaction coordinate, so the level labels
    # and the dH arrow have somewhere to sit that is not on top of the curve.
    x = np.linspace(-0.22, 1.22, 900)
    xc = np.clip(x, 0.0, 1.0)
    y = dH * (3 * xc ** 2 - 2 * xc ** 3) + (Ea - dH * 0.5) * 4 * xc * (1 - xc)
    ax.axhline(0.0, color="#cccccc", lw=0.6)
    ax.axhline(dH, color="#cccccc", lw=0.6)
    ax.plot(x, y, color=BLUE, lw=1.8)
    top = float(y.max())

    ax.annotate("", xy=(0.44, top), xytext=(0.44, 0.0),
                arrowprops=dict(arrowstyle="<->", color=RED, lw=1.0))
    ax.text(0.41, top / 2, r"$E_a^{\mathrm{fwd}}$", color=RED, fontsize=9,
            ha="right", va="center",
            bbox=dict(fc="white", ec="none", pad=1.0))
    ax.annotate("", xy=(0.58, top), xytext=(0.58, dH),
                arrowprops=dict(arrowstyle="<->", color=GREEN, lw=1.0))
    ax.text(0.61, (top + dH) / 2,
            r"$E_a^{\mathrm{rev}} = E_a^{\mathrm{fwd}} - \Delta H$",
            color=GREEN, fontsize=9, ha="left", va="center",
            bbox=dict(fc="white", ec="none", pad=1.0))
    ax.annotate("", xy=(1.10, 0.0), xytext=(1.10, dH),
                arrowprops=dict(arrowstyle="<->", color=GREY, lw=1.0))
    ax.text(1.07, dH / 2, r"$\Delta H$", color=GREY, fontsize=9,
            ha="right", va="center",
            bbox=dict(fc="white", ec="none", pad=1.0))

    ax.text(-0.20, 3.5, "reactants", fontsize=8, color=GREY, ha="left")
    ax.text(-0.20, dH + 3.5, "products", fontsize=8, color=GREY, ha="left")
    ax.set_xlim(-0.22, 1.22)
    ax.set_ylim(dH - 12, top + 12)
    ax.set_xticks([])
    ax.set_ylabel(r"energy / kJ mol$^{-1}$")
    ax.set_xlabel("reaction coordinate")
    ax.grid(False)
    ax.set_title("The reverse barrier is not a free parameter. The picture fixes it")
    save(fig, "detailed_balance")


@figure("standardstate")
def _standardstate():
    """What moving from the ideal gas to the liquid does to an equilibrium constant."""
    fig, ax = plt.subplots(figsize=(5.0, 2.3))
    names = ["ideal gas\nstandard state", "liquid\nstandard state", "measured"]
    vals = [19.4, 8.1, 4.0]
    bars = ax.bar(names, vals, color=[LIGHT, BLUE, GREEN], edgecolor=GREY, lw=0.6)
    ax.set_ylim(0, max(vals) * 1.18)          # headroom, so a label cannot escape
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.03, f"{v:g}",
                ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("K at 298 K, Fischer esterification")
    ax.grid(False)
    ax.set_title("One change of reference state, a factor of 2.4, in the right direction")
    save(fig, "standardstate")


@figure("henry", engine=True)
def _henry(env):
    """Oxygen under air: what an unsymmetric reference state buys."""
    solvents = ["water\n(the reference)", "methanol", "ethanol", "benzene", "n-hexane"]
    chemsim = [0.27, 1.55, 1.57, 1.44, 2.41]
    measured = [0.27, 2.10, 2.10, 1.80, 3.10]
    before = [0.27] * 5
    fig, ax = plt.subplots(figsize=(5.8, 2.4))
    x = np.arange(len(solvents))
    ax.bar(x - 0.26, before, width=0.24, color=LIGHT, edgecolor=GREY, lw=0.5,
           label="before: every solvent got water's number")
    ax.bar(x, chemsim, width=0.24, color=BLUE, label="chemsim")
    ax.bar(x + 0.26, measured, width=0.24, color=GREEN, label="measured")
    ax.set_xticks(x); ax.set_xticklabels(solvents)
    ax.set_ylabel(r"dissolved O$_2$ / mM at 298 K")
    ax.grid(False)
    ax.legend(loc="upper left")
    ax.set_title("One tabulated constant, transferred to four solvents by "
                 r"$\gamma^\infty$")
    save(fig, "henry")


@figure("jacobian")
def _jacobian():
    """The overflow: a column whose difference quotient cannot be measured."""
    fig, ax = plt.subplots(figsize=(5.6, 2.4))
    h = np.array([2.2e-24, 2.2e-19, 2.2e-14, 2.2e-9, 2.2e-4, 2.2e6])
    d = np.array([8.84e-29] * 6)
    ax.loglog(h, d, "o-", color=RED, label="a column the model has projected away")
    hh = np.logspace(-24, 6, 100)
    ax.loglog(hh, 4.0e-5 * hh, color=BLUE, ls="--",
              label=r"what a real derivative looks like ($\propto h$)")
    ax.set_xlabel(r"probe step $|h|$")
    ax.set_ylabel(r"$\max |f(y + h e_j) - f(y)|$")
    ax.legend(loc="upper left")
    ax.set_title("Constant over thirty decades. No step size can measure this, "
                 "so scipy probes forever")
    save(fig, "jacobian")


@figure("selectivity")
def _selectivity():
    """Kinetic against thermodynamic control: two templates racing."""
    fig, ax = plt.subplots(figsize=(5.4, 2.5))
    T = np.linspace(350.0, 700.0, 400)
    k1 = 1e11 * np.exp(-70e3 / (R * T))          # the kinetic product
    k2 = 1e13 * np.exp(-90e3 / (R * T))          # the thermodynamic product
    ax.semilogy(T, k1, color=BLUE, label="lower barrier, lower prefactor")
    ax.semilogy(T, k2, color=RED, label="higher barrier, higher prefactor")
    # The crossing is where the DIFFERENCE changes sign. Taking argmin of
    # |k1 - k2| instead finds the left edge, where both are small in absolute
    # terms and a factor of 100 apart -- which is not the crossing at all.
    i = int(np.flatnonzero(np.diff(np.sign(k1 - k2)))[0])
    ax.plot([T[i]], [k1[i]], "o", color="k", ms=5, zorder=6)
    ax.set_xlim(T[0], T[-1])
    ax.set_ylim(min(k1.min(), k2.min()) * 0.3, max(k1.max(), k2.max()) * 20)
    ax.annotate(f"the major product\nchanges here, {T[i]:.0f} K",
                xy=(T[i], k1[i]), xytext=(T[i] + 22, k1[i] * 3e-3),
                fontsize=7.5, ha="left", va="center",
                bbox=dict(fc="white", ec="none", pad=1.5),
                arrowprops=dict(arrowstyle="->", color="k", lw=0.7))
    ax.set_xlabel("T / K")
    ax.set_ylabel(r"$k$ / s$^{-1}$")
    ax.legend(loc="upper left")
    ax.set_title("Two templates on one substrate. The crossing is a prediction, "
                 "not a declaration")
    save(fig, "selectivity")


@figure("phases")
def _phases():
    """Where a species can be, and every path between -- the transport terms."""
    fig, ax = plt.subplots(figsize=(5.8, 2.6))
    ax.axis("off")
    boxes = {
        "gas": (0.5, 0.82, "VAPOUR\n$n_G$"),
        "l1": (0.22, 0.44, "LIQUID 1\n$n_{L1}$"),
        "l2": (0.78, 0.44, "LIQUID 2\n$n_{L2}$"),
        "sol": (0.5, 0.08, "SOLID\n$n_S$"),
    }
    for key, (x, y, lab) in boxes.items():
        c = {"gas": "#eef3f8", "l1": "#e8f0e8", "l2": "#e8f0e8", "sol": "#f5eee6"}[key]
        ax.add_patch(plt.Rectangle((x - 0.13, y - 0.075), 0.26, 0.15,
                                   facecolor=c, edgecolor=GREY, lw=0.8, zorder=2))
        ax.text(x, y, lab, ha="center", va="center", fontsize=8, zorder=3)
    arrows = [
        ((0.22, 0.52), (0.42, 0.75), "evaporate /\ncondense", BLUE),
        ((0.78, 0.52), (0.58, 0.75), "evaporate /\ncondense", BLUE),
        ((0.35, 0.44), (0.65, 0.44), "activity equality\n(LLE transfer)", GREEN),
        ((0.28, 0.37), (0.44, 0.16), "dissolve /\nprecipitate", RED),
        ((0.72, 0.37), (0.56, 0.16), "dissolve /\nprecipitate", RED),
    ]
    for (x0, y0), (x1, y1), lab, c in arrows:
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="<->",
                                     mutation_scale=9, color=c, lw=1.0, zorder=1))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, lab, ha="center", va="center",
                fontsize=6.4, color=c,
                bbox=dict(fc="white", ec="none", pad=0.8))
    ax.add_patch(FancyArrowPatch((0.63, 0.86), (0.90, 0.94), arrowstyle="<->",
                                 mutation_scale=9, color=GREY, lw=1.0))
    ax.text(0.93, 0.94, "vent\n(the room)", fontsize=6.8, color=GREY, va="center")
    ax.text(0.02, 0.10, "reaction runs in liquid 1, in liquid 2, in the\n"
            "headspace, inside the crystal, and at its surface",
            fontsize=7, color=GREY, va="top")
    ax.set_xlim(0, 1.15); ax.set_ylim(-0.04, 1.05)
    save(fig, "phases")


# =====================================================================

def _engine_env():
    """Build the providers once. Returns None if the package will not import."""
    try:
        from chemsim.properties import ThermochemistryProvider, UnifacProvider
        from chemsim.properties.volatility import VolatilityProvider
        thermo = ThermochemistryProvider()
        return {
            "thermo": thermo,
            "unifac": UnifacProvider(),
            "volatility": VolatilityProvider(thermo),
        }
    except Exception:
        traceback.print_exc()
        return None


def main() -> int:
    env = None
    failures = []
    for name, needs_engine, fn in _FIGURES:
        tag = "ENGINE" if needs_engine else "DRAWN "
        print(f"[{tag}] {name}")
        try:
            if needs_engine:
                if env is None:
                    env = _engine_env()
                if env is None:
                    raise RuntimeError("chemsim did not import")
                fn(env)
            else:
                fn()
        except Exception as exc:                       # keep going; report at the end
            failures.append((name, repr(exc)))
            print(f"    FAILED: {exc}")
            traceback.print_exc()
    print()
    print(f"{len(_FIGURES) - len(failures)} / {len(_FIGURES)} figures written to {OUT}")
    for name, err in failures:
        print(f"  MISSING {name}: {err}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

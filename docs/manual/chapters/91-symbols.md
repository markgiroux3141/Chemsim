# Symbols, units and constants

## Unit conventions

Internal units are SI-ish and unit objects never enter the numeric core. Units
live only at domain boundaries.

| quantity | unit |
|---|---|
| amount | mol |
| concentration | mol/L, written M |
| mole fraction | dimensionless, $\sum_i x_i = 1$ |
| temperature | K |
| energy | J/mol (tables often quote kJ/mol; the code stores J/mol) |
| entropy, heat capacity | J/(mol K) |
| pressure | bar ($1\ \text{atm} = 1.01325$ bar) |
| volume | L |
| time | s |
| power | W |
| $UA$ | W/K |
| potential | V |
| rate | mol/(L s) for solution, mol/s for a surface reaction |
| Arrhenius $A$ | whatever makes rate come out in the above |

::: {.trap}
The units of $A$ depend on the overall reaction order: s⁻¹ for first order,
L mol⁻¹ s⁻¹ for second, and (L/mol)⁸ s⁻¹ for a ninth-order declaration. A
pre-exponential quoted without its order is meaningless, and this is why the
rate-ceiling audit compares against a limit computed *per molecularity*.
:::

## Constants

| symbol | value | |
|---|---|---|
| $N_A$ | $6.02214076\times10^{23}$ mol⁻¹ | Avogadro |
| $R$ | 8.314462618 J/(mol K) | gas constant, $= N_Ak_B$ |
| $k_B$ | $1.380649\times10^{-23}$ J/K | Boltzmann |
| $F$ | 96,485 C/mol | Faraday, $= N_Ae$ |
| $h$ | $6.62607015\times10^{-34}$ J s | Planck |
| $P\std$ | 1 bar | standard pressure |
| $T\std$ | 298.15 K | standard temperature |
| $RT$ at 298 K | 2.479 kJ/mol | the number to keep in your head |
| $k_BT/h$ at 300 K | $6.25\times10^{12}$ s⁻¹ | the attempt frequency |

## Symbols

**Thermodynamic**

| | |
|---|---|
| $H$, $\Delta H$ | enthalpy; $\Delta H_f$ of formation, $\Delta H_{\mathrm{vap}}$ of vaporisation, $\Delta H_{\mathrm{fus}}$ of fusion |
| $S$, $\Delta S$ | entropy |
| $G$, $\Delta G$ | Gibbs free energy; $\Delta G_f$ of formation |
| $\mu_i$ | chemical potential of species $i$ |
| $C_p$ | heat capacity at constant pressure |
| $K$ | equilibrium constant |
| $Q$ | reaction quotient |
| $K_a$, $\mathrm{p}K_a$ | acid dissociation constant |
| $K_{\mathrm{sp}}$ | solubility product |
| $\std$ | superscript: standard state |
| $\ddagger$ | superscript: transition state |

**Kinetic**

| | |
|---|---|
| $k(T)$ | rate constant |
| $A$ | Arrhenius pre-exponential |
| $E_a$ | activation energy |
| $n$ | modified-Arrhenius temperature exponent, $k = AT^ne^{-E_a/RT}$ |
| $\alpha$ | Evans--Polanyi transfer coefficient |
| $\rho$, $\sigma^+$ | Hammett reaction constant and substituent constant |
| $r_j$ | rate of reaction $j$ |
| $\nu_i$, $\Delta$ | stoichiometric coefficient; the $(m,n)$ matrix |
| $\alpha_{ji}$ | rate-law exponent of species $i$ in reaction $j$ |
| $\Delta n$ | $\sum_i\nu_i$, the change in mole count |

**Phase and composition**

| | |
|---|---|
| $n_i$ | moles of species $i$ |
| $C_i$ | concentration |
| $x_i$, $y_i$ | liquid and vapour mole fraction |
| $\phi_i$ | volume fraction |
| $\gamma_i$ | activity coefficient; $\gamma^*$ unsymmetric, $\gamma^\infty$ at infinite dilution |
| $a_i$ | activity, $\gamma_ix_i$ |
| $P^{\mathrm{sat}}$, $p_i$ | saturation vapour pressure; partial pressure |
| $H_i$ | Henry constant |
| $T_b$, $T_m$ | normal boiling point, melting point |
| $T_c$, $P_c$, $V_c$ | critical constants |
| $\omega$ | acentric factor |
| $\varepsilon$ | relative permittivity |
| $R_k$, $Q_k$, $a_{mn}$ | UNIFAC group volume, surface area, interaction |

**Vessel and rig**

| | |
|---|---|
| $\mathbf y$ | state vector, $[n_{L1}\mid n_{L2}\mid n_G\mid n_S\mid T]$, length $4n{+}1$ |
| $k_{la}$ | mass-transfer coefficient for evaporation |
| $k_{\mathrm{diss}}$ | dissolution rate constant |
| $k_{\mathrm{lle}}$ | liquid--liquid transfer rate constant |
| $UA$ | heat-transfer coefficient to the environment |
| $Q_{\mathrm{input}}$ | hotplate power, W |
| $q_{\mathrm{rxn}}$, $q_{\mathrm{vap}}$, $q_{\mathrm{fus}}$, $q_{\mathrm{loss}}$, $q_{\mathrm{vent}}$ | the energy-balance terms |
| $E$ | cell potential, V |
| $\eta_a$ | activation overpotential, V |

## Numbers worth remembering

| | |
|---|---|
| $RT$ at 298 K | 2.48 kJ/mol |
| 6 kJ/mol in $\Delta G\std$ | a factor of 10 in $K$ |
| 10 kJ/mol in $E_a$ | a factor of 55 in rate at 298 K |
| a 10 K rise | roughly doubles a rate |
| bond energy | 300--500 kJ/mol |
| $\Delta H_{\mathrm{vap}}$ | 20--50 kJ/mol for common solvents |
| $\Delta S_{\mathrm{vap}}$ | $\approx +90$ J/(mol K) (Trouton) |
| diffusion limit in solution | $\sim10^{10}$ L mol⁻¹ s⁻¹ |
| bond vibration | $\sim10^{13}$ s⁻¹ |
| water's permittivity | 78 |
| toluene's permittivity | 2.4 |

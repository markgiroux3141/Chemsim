"""Physical constants and the project's unit conventions.

UNIT CONVENTIONS (enforced by discipline, not types -- for now):
    amount / concentration : mol / L   (molar, "M")
    temperature            : K
    energy                 : J / mol
    time                   : s
    Arrhenius A            : units that make rate come out in mol/(L*s);
                             depends on overall reaction order.

Units live only at the domain boundaries. Inside ``numerics`` everything is a
bare float in these units -- no unit objects in the hot loop.
"""

# Universal gas constant, J / (mol K)
R = 8.314462618

# The same constant in L bar / (mol K). 1 L bar = 100 J, so this is just a unit
# change, not a second measured value. Needed to convert an activity-basis
# equilibrium constant (ideal gas, 1 bar standard state -- what group-contribution
# thermochemistry gives us) to the concentration basis the rate law works in.
R_L_BAR = R / 100.0

# Standard states for that conversion.
P_STD_BAR = 1.0   # bar   -- reference pressure of the thermochemical data
C_STD_M = 1.0     # mol/L -- reference concentration of the kinetic state vector

# Faraday constant, C/mol -- the charge on a mole of electrons. Exact, since the
# 2019 SI redefinition fixed both the elementary charge and the Avogadro number.
#
# It is here rather than in an electrochemistry module because of what it is used
# for: ``n * FARADAY * E`` converts a VOLTAGE, which is an apparatus setting, into
# JOULES PER MOLE, which is the only unit Layer 2's algebra speaks. That is a unit
# conversion at a domain boundary, which is exactly what this module is for.
FARADAY = 96485.33212  # C/mol

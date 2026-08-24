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

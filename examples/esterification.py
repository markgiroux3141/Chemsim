"""Vertical-slice demo: matter -> reactions -> network -> numerics.

Unlike the Phase-0 spike, NOTHING here hand-writes "acid + alcohol -> ester".
We give the builder three starting molecules (as SMILES) and ONE reaction
*template*, and it discovers the concrete reaction, canonicalizes the product,
and integrates the kinetics to equilibrium.

Then we prove genericity: the SAME template, pointed at methanol instead of
ethanol, discovers methyl acetate with zero extra code.

Note what the template does NOT contain: reverse kinetics. Only the forward rate
is declared; hydrolysis is derived from the reaction's thermochemistry by detailed
balance, so the equilibrium the integrator settles at is the thermodynamic one.
"""

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.numerics import Integrator
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import ReactionTemplate, equilibrium_constant_c

# Fischer esterification as a graph rewrite: carboxylic acid + alcohol
# <=> ester + water. Atom maps carry identity across the arrow.
FISCHER = ReactionTemplate(
    name="fischer_esterification",
    # The alcohol's OH must sit on an sp3 carbon ([CX4]); this deliberately
    # excludes a carboxylic acid's own OH, which would otherwise self-condense
    # to an anhydride. Selectivity lives in the pattern, not in a product list.
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000,   # forward only -- the reverse follows from thermo
    reversible=True,
)

THERMO = ThermochemistryProvider()


def demo(acid, alcohol, label, T=340.0):
    print(f"\n=== {label} @ {T:.0f} K ===")
    net = build_network([acid, alcohol, "O"], templates=[FISCHER], thermo=THERMO)
    print(net.describe())

    sys = net.to_arrays()
    integ = Integrator(sys)

    C0 = sys.vector({acid: 5.0, alcohol: 5.0, "O": 0.5})
    sol = integ.run(C0, T=T, t_span=(0.0, 3600.0))
    final = sys.as_dict(sol.y[:, -1])

    # Identify the ester: the species that appeared and isn't a starting material.
    starts = {acid, alcohol, "O"}
    esters = [s for s in sys.species if s not in starts]
    print("  equilibrium (mol/L):")
    for s in sys.species:
        print(f"    {s:<18} {final[s]:.3f}")
    for e in esters:
        print(f"  -> ester {Molecule.from_smiles(e).formula} yield: "
              f"{final[e] / 5.0:.1%}")

    # The reverse rate was never typed in: it was derived so that k_f/k_r = K(T).
    fwd = next(r for r in net.reactions if r.name == FISCHER.name)
    rev = next(r for r in net.reactions if r.name == f"{FISCHER.name}_rev")
    print(f"  forward  A={fwd.A:.3e}  Ea={fwd.Ea:.0f} J/mol   (declared)")
    print(f"  reverse  A={rev.A:.3e}  Ea={rev.Ea:.0f} J/mol   (derived)")
    Q = (final[esters[0]] * final["O"]) / (final[acid] * final[alcohol])
    print(f"  reaction quotient at rest Q={Q:.2f}  vs  "
          f"K({T:.0f} K)="
          f"{equilibrium_constant_c(fwd, THERMO, T, net.volatility):.2f}")


if __name__ == "__main__":
    demo("CC(=O)O", "CCO", "acetic acid + ethanol")    # -> ethyl acetate
    demo("CC(=O)O", "CO", "acetic acid + methanol")     # -> methyl acetate (same template!)

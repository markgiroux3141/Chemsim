\part{Appendices}

\appendix

# Glossary

Chemistry terms first, then the project's own vocabulary.

## Chemistry

**Activity** ($a_i$) --- the effective concentration that appears in an
equilibrium expression: $a_i = \gamma_i x_i$. Reduces to mole fraction in an
ideal mixture.

**Activity coefficient** ($\gamma_i$) --- the correction from ideal. Above 1
means the species is less comfortable in the mixture than in its own pure
liquid. See Chapter 8.

**Acid / base** --- a proton donor / acceptor.

**Activation energy** ($E_a$) --- the barrier a reaction must clear.

**Antoine equation** --- the three-parameter fit
$\log_{10}P^{\mathrm{sat}} = A - B/(C+T)$ used for every volatile species here.

**Aromatic** --- a ring with delocalised electrons (benzene), unusually stable.

**Arrhenius equation** --- $k = A e^{-E_a/RT}$.

**Azeotrope** --- a liquid mixture that boils without changing composition;
distillation cannot pass it.

**Bond** --- a shared pair of electrons; a bound state, 300--500 kJ/mol deep.

**Born energy** --- the electrostatic cost of charging an ion inside a dielectric.
Used here for ion *transfer between phases*.

**Catalyst** --- a species that speeds a reaction and is not consumed. Appears on
both sides, so stoichiometry 0 and rate-law exponent 1.

**Clausius--Clapeyron** --- $\dd\ln P^{\mathrm{sat}}/\dd T = \Delta H_{\mathrm{vap}}/RT^2$.

**Concentration** --- amount per volume; molarity is mol/L, written M.

**Detailed balance** --- $k_f/k_r = K$ at every temperature. Chapter 6.

**Elementary step** --- a reaction that really is one collision, so that
stoichiometry and rate-law order coincide.

**Enthalpy** ($H = U + pV$) --- heat absorbed at constant pressure.

**Entropy** ($S$) --- $R\ln\Omega$ per mole.

**Ester** --- the product of an acid and an alcohol losing water; ethyl acetate
is the running example.

**Equilibrium constant** ($K = e^{-\Delta G\std/RT}$) --- where a reversible
reaction stops.

**Exothermic / endothermic** --- releases / absorbs heat.

**Fusion** --- melting. $\Delta H_{\mathrm{fus}}$, $T_m$.

**Gibbs free energy** ($G = H - TS$) --- minimised at constant $T$ and $p$.

**Hammett relation** --- $\log_{10}(k/k_0) = \rho\sum\sigma$; how substituents on
an aromatic ring change a rate.

**Henry's law** --- $p_i = x_i H_i$ for a gas dissolved in a liquid. Same
functional shape as Raoult, different constant.

**Ion** --- a charged atom or molecule.

**Ionic lattice** --- an extended crystal of alternating ions; salt. Not a
molecule and has no useful graph.

**Isomers** --- same formula, different substance: *structural* (different
connectivity), *stereo* (different arrangement in space), *tautomers*
(interconverting by moving an H and a bond).

**Le Chatelier's principle** --- a system at equilibrium shifts to oppose a
change. Quantitatively, the van 't Hoff equation.

**Mole** --- $6.022\times10^{23}$ entities.

**Mole fraction** ($x_i$) --- $n_i/\sum n_j$.

**Oxidation / reduction** --- losing / gaining electrons.

**pH** --- $-\log_{10}[\mathrm{H_3O^+}]$.

**pKa** --- $-\log_{10}K_a$; small means strong acid.

**Raoult's law** --- $p_i = x_i P^{\mathrm{sat}}_i$ for an ideal liquid.

**Reaction quotient** ($Q$) --- the same product of activities as $K$, evaluated
away from equilibrium.

**Solubility product** ($K_{\mathrm{sp}}$) --- the equilibrium constant for a
lattice dissolving into ions.

**Standard state** --- the reference condition against which formation data is
quoted. Ideal gas at 1 bar, or the pure liquid, or infinite dilution in water.
Getting this wrong is the most consequential silent error in the project's
history.

**Stoichiometry** --- the integer coefficients in a balanced equation.

**Transition state theory** --- the framework that identifies Arrhenius's $A$
with $(k_BT/h)e^{\Delta S^\ddagger/R}$.

**van 't Hoff equation** --- $\dd\ln K/\dd T = \Delta H\std/RT^2$.

**Vapour pressure** ($P^{\mathrm{sat}}$) --- the pressure of vapour in
equilibrium with its own liquid.

## The project's vocabulary

**Affinity form** --- the rate law used for a reversible reaction inside a
crystal: $k[\,\text{units}_f - \text{units}_r e^{\ln Q - \ln K}]$.

**BOTH column** --- the intersection of *species-ready* and *template-ready*; the
number to quote for how many corpus routes can run. Currently 38 of 173.

**Class** --- a reaction *mechanism* label on a corpus step. Never an outcome
label; 32 rows were re-labelled to enforce that.

**Concrete reaction** --- what a template produces once it has matched real
species: a reactant multiset, a product multiset, and kinetics.

**Discovery** --- the fixpoint that finds every reaction a set of templates can
run on a set of species.

**Dryout band** --- the range of tiny liquid holdings over which the liquid-phase
terms switch off. Historically the source of a matter-creating bug.

**Edge** --- a connection between vessels in a rig: `VAPOUR`, `DRAIN`,
`THERMAL`, `METER`.

**Emergent** --- a behaviour that follows from integrating existing terms rather
than from a rule. Chapter 28 lists twenty-four.

**Event** --- a timestamped, serialisable player action; the only thing that may
mutate a vessel, and it fires only between integrations.

**KineticArrays / PhaseArrays** --- the numpy handoff from the chemistry layers
to the numeric core.

**Lattice** --- an ionic solid, held as a single species that may react and (with
one recorded exception) may not dissolve or boil.

**Marker** --- a corpus entry with no molecular graph: `coal-marker`,
`collagen-marker`. Cannot be simulated, deliberately present so the corpus is
honest about what it contains.

**Playable** --- reachable from natural materials by running routes. 21 of 173.

**Provenance / tier** --- where a number came from: `measured`, `mineral`,
`compilation`, `benson`, `joback`, `ion`, `nonvolatile`, `refused`.

**Refusal** --- a named, explained "no" from a provider or a guard. Treated as
content rather than as an error.

**Rig** --- vessels plus typed connections, integrated as one system.

**Scenario / script** --- what a save contains. A run is a pure function of the
two.

**Seam** --- an inversion boundary designed to be replaceable: `matter` hides
RDKit; `numerics` sees only arrays.

**Species-ready** --- every species in a route resolves to a full property set.

**Template** --- a SMARTS graph-rewrite rule plus forward kinetics.

**Template-ready** --- every reaction class in a route has a template.

**`wait_until`** --- the verb that turns a bench instruction into a root of the
state vector.

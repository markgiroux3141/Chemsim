\part{The machine}

# The architecture, and its two seams

## Eight layers, strictly downward

\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
  lay/.style={draw=csrule,fill=csbluebg,rounded corners=1.2pt,
              minimum height=9.5mm,text width=132mm,inner xsep=3mm,
              font=\small,align=left},
  seam/.style={csred,font=\sffamily\scriptsize\bfseries}]
  \foreach \i/\n/\t in {
    0/{7}/{\textbf{ui} \quad a window over the engine: worker thread, chunked ops, snapshots},
    1/{6}/{\textbf{engine} \quad headless deterministic stepper: world state, \texttt{step(dt)}, save/load, events},
    2/{5}/{\textbf{vessel} \quad four phases, VLE + Henry + solubility, energy balance, pressure, pH},
    3/{4.5}/{\textbf{discovery} \quad rate-based network refinement (needs a simulator, so it sits above one)},
    4/{4}/{\textbf{numerics} \quad RHS builders, ODE integrators, activity coefficients},
    5/{3}/{\textbf{network} \quad discover concrete reactions; derive reverse kinetics; project to arrays},
    6/{2}/{\textbf{reactions} \quad \texttt{ReactionTemplate} (SMARTS graph rewrite) + kinetics + reaction thermo},
    7/{1}/{\textbf{properties} \quad thermochemistry, volatility, condensed phase --- estimated + curated},
    8/{0}/{\textbf{matter} \quad molecular graphs, canonical identity}}
  {
    \node[lay] (L\i) at (0,-\i*1.16) {\makebox[9mm][l]{\color{csblue}\sffamily\bfseries\footnotesize \n}\t};
  }
  \draw[csred,thick] ($(L8.north west)+(-1mm,1mm)$) -- ($(L8.north east)+(1mm,1mm)$);
  \node[seam,anchor=west] at ($(L8.north east)+(2mm,1mm)$) {seam 1};
  \draw[csred,thick] ($(L4.south west)+(-1mm,-1mm)$) -- ($(L4.south east)+(1mm,-1mm)$);
  \node[seam,anchor=west] at ($(L4.south east)+(2mm,-1mm)$) {seam 2};
  \draw[->,csgrey,thick] ($(L0.west)+(-6mm,0)$) -- ($(L8.west)+(-6mm,0)$)
    node[midway,rotate=90,anchor=south,font=\sffamily\scriptsize,csgrey] {depends on};
\end{tikzpicture}
\caption{The stack. Dependencies point strictly downward, and the two red lines
are the interfaces that were designed to be replaceable.}
\label{fig:stack}
\end{figure}

Nothing above a layer is imported by it. That is enforced by convention rather
than by a tool, but it holds, and two of the boundaries are load-bearing enough
to have names.

## Seam 1: `matter` hides RDKit

**Nothing above Layer 0 imports rdkit.** Parsing, canonicalisation, substructure
matching and template application all happen inside
`chemsim/matter/molecule.py`, behind a domain type.

Two things this buys. The cheminformatics backend is replaceable --- a Rust
library, a different toolkit --- without touching anything else. And RDKit types
cannot leak into the engine, which matters more than it sounds: an RDKit `Mol`
is unhashable, unpicklable and mutable, and a `Molecule` here is none of those.
That is why a species can be a dictionary key and why a save file contains no
molecule objects.

## Seam 2: `numerics` sees only arrays

**The hot integration loop consumes `KineticArrays` and `PhaseArrays` --- numpy
plus a list of species names --- and knows nothing about molecules.**

\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
  box/.style={draw=csrule,rounded corners=1.2pt,minimum height=8mm,
              inner xsep=2.5mm,font=\footnotesize,align=center},
  setupb/.style={box,fill=csgreenbg},
  loopb/.style={box,fill=csbluebg},
  ar/.style={->,>=Latex,csgrey,thin}]
  \node[setupb,text width=30mm] (m)  at (0,0)    {SMILES\\molecular graphs};
  \node[setupb,text width=30mm] (p)  at (3.9,0)  {property models\\Antoine, Rackett,\\Lee--Kesler, Joback};
  \node[setupb,text width=30mm] (t)  at (7.8,0)  {templates\\SMARTS + kinetics};
  \node[setupb,text width=30mm] (n)  at (11.7,0) {network build\\detailed balance};
  \node[loopb,text width=118mm]  (a)  at (5.85,-1.9)
    {\textbf{numpy arrays only:} $\Delta$, $A$, $E_a$, orders, Antoine $(A,B,C)$,
     $C_p$ cubics, $v_{\text{liq}}$ cubics, UNIFAC $\nu/R_k/Q_k/a_{mn}$, Born block};
  \node[loopb,text width=118mm]  (r)  at (5.85,-3.4)
    {\textbf{the RHS}, called $10^3$--$10^6$ times: one polynomial kernel, one
     matrix product, one activity evaluation};
  \foreach \x in {m,p,t,n} \draw[ar] (\x.south) -- ++(0,-0.55) -| (a.north);
  \draw[ar] (a) -- (r);
  \node[font=\sffamily\scriptsize\bfseries,csgreen,anchor=west] at (-2.6,0) {SETUP};
  \node[font=\sffamily\scriptsize\bfseries,csblue,anchor=west] at (-2.6,-2.65) {HOT LOOP};
  \draw[csrule,thick] (-2.7,-0.95) -- (12.9,-0.95);
\end{tikzpicture}
\caption{The setup/hot-loop split. Everything model-specific happens once,
above the line.}
\label{fig:split}
\end{figure}

::: {.keypoint title="Cheminformatics happens at setup time, never inside the loop"}
This is the discipline that makes the whole design tractable, and it is applied
to property *models* as well as to molecules. Antoine, Lee--Kesler, Rackett and
Rowlinson--Bondi are all evaluated and fitted to plain polynomial coefficients
during assembly, so **the kernel evaluates one polynomial form and has never
heard of any of them.**

Raoult's law and Henry's law arrive as the same array. A forward reaction and
its thermodynamically derived reverse arrive as two rows of the same matrix. A
melting model and a dissolution model arrive as one equation with one factor
switched.
:::

## The one exception, and why it is not a leak

Activity coefficients depend on **composition**, and composition is the state
vector --- so unlike every other property they cannot be fitted in advance
(Chapter 8).

The split *moves* rather than breaking. What is precomputed is the UNIFAC
*parameter block*: group counts, size and surface parameters, the interaction
matrix, all expanded to a dense subgroup basis at assembly time. What runs per
step is the evaluation. Layer 4 still receives nothing but numpy; the arrays are
simply richer, and the loop finally does real work.

The Born term (Chapter 10) lands in the same place for the same reason, and
collapses to an $(n,4)$ block that is a function of temperature alone plus a
three-operation mixing rule.

## Why Python, stated as a measurement rather than a preference

The hot loop's cost scales with the number of **species and reactions in a
vessel** --- a small, stiff ODE system, milliseconds in SciPy's C solvers --- and
**not** with the number of molecules. Python becomes a bottleneck for spatial
gradients, large auto-generated networks, or many simultaneous vessels, and for
those the `numerics` boundary lets a Rust kernel drop in surgically with nothing
above it changing.

The measurement that bears on this, from Chapter 8: adding UNIFAC took the RHS
from 140 µs to 231 µs, and the $\gamma$ kernel itself is *flat* from 4 species to
25 --- both numbers are numpy dispatch overhead on small arrays, not arithmetic.

::: {.keypoint}
So the case for Rust does not rest on any one model being slow. It rests on
**fixed per-call overhead**, which a Rust kernel would collapse for the whole
RHS rather than for one part of it. That is a different argument, and the project
defers the work until real numbers justify it.
:::

## What lives where

| you want to know | look in |
|---|---|
| how a molecule is represented | `matter/molecule.py` |
| where a number came from | `properties/*_data.py` and the `source` field |
| what reactions exist | `reactions/library.py`, `reactions/synthesis.py` |
| how a reaction becomes numbers | `network/builder.py` |
| the actual differential equations | `numerics/vessel_integrator.py` |
| what a flask does | `vessel/vessel.py` |
| how a run is made reproducible | `engine/world.py`, `engine/scenario.py` |
| how much chemistry is covered | `data/catalog/`, `validation/catalog_coverage.py` |
| why any decision was made | `MILESTONES.md`, and the module docstrings |

Appendix C is a fuller version of that table.

## A note on the module docstrings

They are long, and they are the primary documentation of this project. They do
not describe what the code does --- the code does that --- they record *what was
measured, what was tried and rejected, and what the alternative would have
cost*. `numerics/jacobian.py` opens with a 200-line argument for a single
inequality; `properties/solid_state.py` contains a four-row table showing why
one modelling choice was rejected.

This manual is largely a reorganisation of that material into an order somebody
can read it in.

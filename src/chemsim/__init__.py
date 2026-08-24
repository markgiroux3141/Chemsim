"""chemsim -- an emergent chemistry simulation engine.

The design goal: outcomes (yields, side products, temperature and contamination
sensitivity) EMERGE from integrating a reaction network, rather than being
scripted. Molecules are graphs; reactions are graph-rewrite templates; the
system's evolution is computed, not looked up.

Layering (strict downward dependencies):

    engine     -> vessel -> numerics -> network -> reactions -> properties -> matter

Two inversion boundaries keep the important parts swappable:
  * ``matter`` hides RDKit behind our own molecule type.
  * ``numerics`` receives plain numeric arrays only -- no domain types -- so the
    hot integration loop can later drop to a Rust/PyO3 kernel untouched.

``recipes`` sits above all of it: curated PREPARATIONS as data, with the same
provenance discipline every other parameter table here has. It exists because the
benzoic-acid prep was living in three hand-synchronised copies and one of its
conditions is load-bearing and counter-intuitive.
"""

__version__ = "0.0.1"

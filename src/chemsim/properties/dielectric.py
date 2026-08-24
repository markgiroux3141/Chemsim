"""Layer 1 -- how polar is this liquid, and what does that cost an ion?

This module exists to answer one question the rest of the project could not:
**why does a dissolved salt stay in the water when you shake the flask?**

Until now it did not. UNIFAC is a non-electrolyte model, so an ion had no
activity coefficient at all and sat at gamma = 1. Inside one liquid that is a
bounded error. Across a liquid-liquid interface it is not: equality of activity
with gamma = 1 on both sides means an ion partitions to EQUAL MOLE FRACTION
between water and toluene. So ``split_phases`` refused to split any electrolyte
at all, and the most common workup in preparative chemistry -- acidify, extract,
wash the organic layer -- was not expressible.

⚠ **THIS IS NOT DEBYE-HUCKEL, AND CONFLATING THE TWO WASTES THE WORK.** There
are two separate ionic gaps and only one of them is this one:

  (a) ionic strength WITHIN one phase -- Debye-Huckel / Davies. It is what makes
      a concentrated brine's ions less active than its concentration says, and it
      is what salting-out is. NOT modelled here, and see the note at the bottom
      of this docstring for why adding it would presently change nothing.

  (b) ion transfer BETWEEN phases -- BORN. The electrostatic cost of moving a
      charge out of a high-dielectric medium into a low one. THAT is what holds
      an ion in the aqueous layer, and it is what this module computes.

## The model, and why it collapses so neatly into what is already here

Born (1920): the work of charging a sphere of radius ``r`` carrying charge ``z e``
inside a continuum of relative permittivity ``eps`` is

    G_el(eps) = - (N_A z^2 e^2) / (8 pi eps_0 r) * (1 - 1/eps)

Only DIFFERENCES of that are used here. An ion's reference state in this project
is infinite dilution in WATER -- every ion's formation data is back-derived from a
measured aqueous pKa (see ``electrolyte.py``) -- so the quantity wanted is the
transfer from water into whatever phase the ion is actually in:

    ln gamma_i(phase) = A_i / (R T) * ( 1/eps_phase - 1/eps_water(T) )

    A_i = (N_A z_i^2 e^2) / (8 pi eps_0 r_i)        [J/mol, a pure constant]

⚠ **In water this is EXACTLY ZERO, by construction, at every temperature.** That
is the whole reason it is written as a transfer rather than as a solvation energy,
and it is what makes the existing pH invariants safe: the anchors were derived at
gamma = 1 against water, and in water gamma is still exactly 1. They do not need
re-deriving, and a term that needed them re-derived would have been the wrong
term. (Every pKa in the table was re-measured afterwards to confirm it, because
"safe by construction" is a claim and not a check.)

This is the same UNSYMMETRIC CONVENTION the Henry's-law solutes already use --
``ln_gamma_ref`` in ``numerics/activity.py`` divides gamma by its value at a
reference state, so the correction is 1 there by definition. The difference, and
it is the interesting one:

⚠ **A Born term cannot fully collapse to setup-time polynomials, because
``eps_phase`` is a MIXTURE property and therefore depends on composition.** So it
lands in the same place UNIFAC did, and the project's standard question -- what
uniform array form does this collapse to? -- has a clean answer:

    an (n, 4) block, a function of TEMPERATURE ALONE:
        [ A_i | eps_pure,i(T) | v_i(T) | eps_water(T) ]

Three of those four columns are already computed at setup or from an existing
polynomial; the only thing left in the hot loop is the mixing rule, which is
three array operations. The kernel still evaluates one polynomial form and has
never heard the word "Born".

## The mixing rule is Oster's, and its accuracy is measured not asserted

A layer's permittivity is not the sum of its parts. Oster (1946), which is
Onsager's theory applied to a mixture:

    f(eps) = sum_i phi_i f(eps_i),      f(e) = (e - 1)(2e + 1) / (9 e)

with ``phi`` the VOLUME fractions -- permittivity is a bulk polarisation
property, so volume is the physically right weighting, and this project already
integrates a molar volume for every species. The inverse is closed-form (it is a
quadratic in eps), which matters: an iterative solve inside the RHS would have to
be differenced by ``num_jac``.

⚠ **Oster and a plain volume-fraction average agree to well under a percent for
every mixture this project can currently make**, which is measured in
``validation/ion_partition.py`` rather than claimed here. Oster is used anyway,
because it is the published rule and the agreement is a finding rather than a
licence.

## The ionic radius, in two tiers, and one of them is deliberately small

    CURATED   Shannon (1976) effective ionic radii, 6-coordinate. Monatomic ions
              and hydroxide. Nine values, each stamped.
    DERIVED   the sphere of equal ADDITIVE VAN DER WAALS VOLUME, from the
              element radii in ``dielectric_data.VDW_RADII``:
                  r = ( sum_atoms rvdw_a^3 ) ** (1/3)
              This is what prices benzoate, acetate and phenolate, for which no
              crystallographic radius exists to look up.

⚠ **The curated table is restricted on purpose.** There is no ionic-radius table
in ``chemicals`` or in any other source this project already depends on, so every
curated value is hand-entered -- and the project's curation rule is that a value
with no auditable source does not get written down. Shannon's monatomic set is
standard reference data; the polyatomic-anion compilations are not carried here,
and those ions fall to the derived tier instead of acquiring a number of
uncertain provenance.

⚠ **The radius is NOT a calibration knob, and it is also not universally
irrelevant.** Measured over a 5x radius sweep in
``validation/ion_partition.py``: for a hydrocarbon layer the transfer energy
spans ln gamma 23 to 145, i.e. a partition coefficient between 1e-10 and 1e-64,
so "the ion stays in the water" does not depend on the radius at all. For a
moderately polar layer (eps ~ 9, octanol or dichloromethane) the same sweep
spans ln gamma 5.6 to 28 -- four orders of magnitude of partition coefficient --
and there the radius is a real parameter. Read the sweep before reading a number
off a polar-solvent extraction.

## What Born does NOT contain, and it matters for one real class of chemistry

Born is the ELECTROSTATIC term only. There is no cavity term and no dispersion
term, so a large, weakly-hydrated, greasy ion -- tetrabutylammonium and its
relatives -- is over-excluded here, when in reality it partitions into an organic
phase readily enough to be sold as a phase-transfer catalyst. Likewise there are
no ION PAIRS in this project's species set, and a salt entering a low-dielectric
solvent really does travel as a neutral pair. **Both omissions err the same way:
too little ion transfer, never too much.** That is the same safe direction the
UNIFAC-VLE parameters err in, and it is why the refusal this replaces could be
lifted rather than merely loosened.

## Where this term is USED, which is three places and one of them is a surprise

  * the LIQUID-LIQUID FLUX -- the ion stays in the water;
  * the TANGENT-PLANE TEST -- so a trial organic phase converges with its ions
    expelled, which is what lets an electrolyte be tested for splitting at all;
  * ⚠ the RATE LAW of any ION-PRODUCING REACTION, which was not foreseen and is
    the second half of the same problem. Getting the ions to stay in the water
    does nothing about the reactions that MAKE ions: every pKa here is anchored
    to water, so running that constant unchanged inside an organic layer makes
    benzoic acid as dissociated in toluene as in water -- the exact opposite of
    what an acid/base extraction relies on. See ``_phase_rates`` in
    ``numerics/vessel_integrator.py`` for the correction and for why it goes on
    the direction that CREATES the ions rather than the one that destroys them.

## And a note on why (a) above is still not worth doing yet

Reaction rates are otherwise on a CONCENTRATION basis, not an activity basis (a
known, recorded gap), and the correction above deliberately carries the BORN term
only -- never a UNIFAC gamma -- precisely because the Born term is exactly 1 in
water and a UNIFAC gamma is not. That is what keeps every calibrated number in
this project untouched.

So a Debye-Huckel term would still change no equilibrium constant, no pKa and no
solubility: it would only adjust ion activities inside terms already dominated by
a factor of e^12. **Salting-out needs the activity basis for NEUTRAL species
first**, not an ionic-strength term for the ions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from chemsim.matter import Molecule
from chemsim.properties.dielectric_data import PERMITTIVITY, VDW_RADII

__all__ = [
    "BORN_PREFACTOR",
    "BornArrays",
    "Dielectric",
    "DielectricProvider",
    "IonicRadius",
    "born_coefficient",
    "build_born_arrays",
    "ionic_radius",
    "REFERENCE_SOLVENT",
]

# N_A e^2 / (8 pi eps_0), in J*m/mol. Multiply by z^2 and divide by the radius in
# METRES to get the Born charging energy per (1 - 1/eps). Assembled from SI
# constants rather than transcribed, so it cannot drift from them: 6.9468e-5,
# i.e. 694.7 kJ/mol for a unit charge on a 1 angstrom sphere.
_N_A = 6.02214076e23
_E_CHARGE = 1.602176634e-19
_EPS_0 = 8.8541878128e-12
BORN_PREFACTOR = _N_A * _E_CHARGE * _E_CHARGE / (8.0 * math.pi * _EPS_0)

# The reference state every ion's activity coefficient is measured against: it is
# water because the ion THERMOCHEMISTRY is water-anchored (see ``electrolyte``),
# not because water happens to be present. A non-aqueous vessel holding ions
# still refers to this one.
REFERENCE_SOLVENT = Molecule.from_smiles("O").smiles

_ANGSTROM = 1.0e-10

_SHANNON = "Shannon (1976) effective ionic radius, 6-coordinate"
_DERIVED = "derived: sphere of equal additive van der Waals volume"

# ⚠ Deliberately only the classical monatomic set plus hydroxide -- see the
# module docstring. Angstrom.
_CURATED_RADII: dict[str, float] = {
    "[Li+]": 0.76,
    "[Na+]": 1.02,
    "[K+]": 1.38,
    "[NH4+]": 1.48,
    "[F-]": 1.33,
    "[Cl-]": 1.81,
    "[Br-]": 1.96,
    "[I-]": 2.20,
    "[OH-]": 1.37,
}


@dataclass(frozen=True)
class Dielectric:
    """A liquid's relative permittivity, as the polynomial the kernel evaluates.

    ``coeffs`` is ``eps(T) = a + bT + cT^2 + dT^3``; ``T_range`` is the window it
    was published over, and evaluating outside it is extrapolating a cubic --
    which is how a permittivity goes negative. ``kind`` distinguishes a CRC
    correlation from a lone measurement held constant.
    """

    coeffs: tuple[float, float, float, float]
    T_range: tuple[float, float]
    kind: str
    source: str

    @property
    def known(self) -> bool:
        return self.kind != "none"

    def at(self, T: float) -> float:
        """eps at T, with T clamped to the published window."""
        lo, hi = self.T_range
        t = min(max(T, lo), hi)
        a, b, c, d = self.coeffs
        return a + t * (b + t * (c + d * t))


_UNKNOWN = Dielectric((0.0, 0.0, 0.0, 0.0), (0.0, 0.0), "none", "")


@dataclass(frozen=True)
class IonicRadius:
    """An ion's Born radius in metres, and which tier it came from."""

    value: float
    source: str

    @property
    def known(self) -> bool:
        return self.value > 0.0


class DielectricProvider:
    """Resolves molecules to a relative permittivity, with provenance.

    A species absent from the table gets an explicit "not known" record rather
    than a plausible default. That is the whole point: an unknown liquid is
    EXCLUDED from a layer's mixing rule and REPORTED, because the alternative --
    guessing a polarity -- decides which layer an ion lives in.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Dielectric] = {}
        self._table = {
            Molecule.from_smiles(s).smiles: v for s, v in PERMITTIVITY.items()
        }

    def get(self, molecule: Molecule | str) -> Dielectric:
        mol = (
            molecule
            if isinstance(molecule, Molecule)
            else Molecule.from_smiles(molecule)
        )
        smi = mol.smiles
        hit = self._cache.get(smi)
        if hit is not None:
            return hit
        entry = self._table.get(smi)
        if entry is None:
            record = _UNKNOWN
        else:
            coeffs, window, kind, source = entry
            record = Dielectric(tuple(coeffs), tuple(window), kind, source)
        self._cache[smi] = record
        return record


def ionic_radius(molecule: Molecule | str) -> IonicRadius:
    """Born radius of an ion, in METRES: curated Shannon, else derived.

    Returns an unknown record for a neutral species -- it has no Born term, and
    saying "radius zero" would divide by it.
    """
    mol = (
        molecule if isinstance(molecule, Molecule) else Molecule.from_smiles(molecule)
    )
    if mol.charge == 0:
        return IonicRadius(0.0, "neutral: no Born term")

    curated = _CURATED_RADII.get(mol.smiles)
    if curated is not None:
        return IonicRadius(curated * _ANGSTROM, _SHANNON)

    # Additive van der Waals volume -> the sphere of equal volume. The 4/3 pi
    # cancels between the sum and the inversion, so this is just the cube root of
    # the summed cubes. Hydrogens are included: it is the volume of the ION.
    counts = mol.element_counts()
    missing = [el for el in counts if el not in VDW_RADII]
    if missing:
        return IonicRadius(
            0.0,
            f"no van der Waals radius for {', '.join(sorted(missing))}, and no "
            "curated ionic radius: this ion cannot be priced",
        )
    cubes = sum(count * VDW_RADII[el] ** 3 for el, count in counts.items())
    if cubes <= 0.0:
        return IonicRadius(0.0, "empty formula")
    return IonicRadius(cubes ** (1.0 / 3.0) * _ANGSTROM, _DERIVED)


def born_coefficient(molecule: Molecule | str) -> tuple[float, str]:
    """``A_i = N_A z^2 e^2 / (8 pi eps_0 r)`` in J/mol, and its provenance.

    Zero for a neutral species and for an ion whose radius cannot be resolved --
    in the second case the caller must REPORT it rather than treat the ion as
    freely transferable, which is what ``build_born_arrays`` does.
    """
    mol = (
        molecule if isinstance(molecule, Molecule) else Molecule.from_smiles(molecule)
    )
    z = mol.charge
    if z == 0:
        return 0.0, "neutral: no Born term"
    r = ionic_radius(mol)
    if not r.known:
        return 0.0, r.source
    value = BORN_PREFACTOR * float(z * z) / r.value
    return value, (
        f"Born charging energy from z = {z:+d} and r = {r.value / _ANGSTROM:.2f} "
        f"angstrom [{r.source}]"
    )


@dataclass
class BornArrays:
    """The Born parameter block, plus the coverage statement Layer 5 reports.

    ``A`` is (n,) J/mol and is zero for every neutral species -- so ``A > 0`` is
    also the "this species is an ion with a Born term" mask, and no separate flag
    is needed. ``eps_coeffs`` is (n, 4) and ``eps_range`` (n, 2), per species,
    because each CRC correlation carries its own validity window. ``eps_ref`` is
    the reference solvent's own (4,) / (2,) pair.
    """

    A: np.ndarray
    eps_coeffs: np.ndarray
    eps_range: np.ndarray
    eps_ref_coeffs: np.ndarray
    eps_ref_range: np.ndarray
    # species -> why it has no permittivity, so a layer made of it is reportable
    unpriced: dict[str, str] = field(default_factory=dict)
    # ion -> why it has no Born coefficient. An ion in here is a REFUSAL case:
    # it would otherwise be treated as freely transferable between layers.
    unpriced_ions: dict[str, str] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)

    @property
    def any_ions(self) -> bool:
        return bool(np.any(self.A > 0.0))

    def report(self) -> str:
        """What this model does NOT cover, in the shape Layer 5 prints."""
        lines = []
        if self.unpriced_ions:
            lines.append(
                f"{len(self.unpriced_ions)} ION(S) have no Born coefficient and "
                "would transfer freely between liquid layers:"
            )
            lines += [f"    {s}: {why}" for s, why in self.unpriced_ions.items()]
        if self.unpriced:
            lines.append(
                f"{len(self.unpriced)} species have no relative permittivity and "
                "are excluded from the mixing rule (the layer's polarity is that "
                "of the species that ARE priced):"
            )
            lines += [f"    {s}: {why}" for s, why in self.unpriced.items()]
        return "\n".join(lines)


def build_born_arrays(
    species: list[str], provider: DielectricProvider | None = None
) -> BornArrays:
    """Assemble the Born parameter block for one vessel's species list."""
    provider = provider or DielectricProvider()
    n = len(species)
    A = np.zeros(n)
    eps_coeffs = np.zeros((n, 4))
    eps_range = np.zeros((n, 2))
    unpriced: dict[str, str] = {}
    unpriced_ions: dict[str, str] = {}
    sources: dict[str, str] = {}

    for i, smi in enumerate(species):
        mol = Molecule.from_smiles(smi)
        d = provider.get(mol)
        if d.known:
            eps_coeffs[i] = d.coeffs
            eps_range[i] = d.T_range
            sources[smi] = d.source
        else:
            # eps stays 0, which is the "no data" sentinel the mixing rule masks
            # on -- a real permittivity is never below 1.
            unpriced[smi] = (
                "no relative permittivity in the CRC compilation"
                if mol.charge == 0
                else "an ion has no bulk permittivity of its own (by design)"
            )
        if mol.charge != 0:
            value, why = born_coefficient(mol)
            A[i] = value
            sources[smi] = why
            if value <= 0.0:
                unpriced_ions[smi] = why
            # An ion is never part of the medium: the Born model puts a charge
            # INSIDE a continuum, so it cannot also be the continuum. The
            # dielectric decrement a real salt causes is an ionic-strength
            # effect and belongs with Debye-Huckel, not here.
            eps_coeffs[i] = 0.0
            eps_range[i] = 0.0
            unpriced.pop(smi, None)

    ref = provider.get(REFERENCE_SOLVENT)
    if not ref.known:                       # pragma: no cover -- water is curated
        raise ValueError(
            "the Born reference solvent (water) has no permittivity entry; "
            "every ion activity coefficient is measured against it"
        )
    return BornArrays(
        A=A,
        eps_coeffs=eps_coeffs,
        eps_range=eps_range,
        eps_ref_coeffs=np.array(ref.coeffs),
        eps_ref_range=np.array(ref.T_range),
        unpriced=unpriced,
        unpriced_ions=unpriced_ions,
        sources=sources,
    )

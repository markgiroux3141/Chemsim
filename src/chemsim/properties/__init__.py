"""Layer 1 -- properties: structure-based thermochemistry estimation.

Group contribution (Joback) estimates properties from a molecular graph, so novel
molecules get plausible numbers with no lookup entry. A curated table overrides
estimates for species where the method breaks (water, O2, ...), and every value
carries its provenance.
"""

from chemsim.properties.fragmentation import FragmentationError
from chemsim.properties.joback import JobackError, JobackResult, estimate, fragment
from chemsim.properties.unifac import (
    ActivityArrays,
    UnifacError,
    UnifacGroups,
    UnifacProvider,
    build_activity_arrays,
)
from chemsim.properties.condensed import (
    CondensedData,
    CondensedProvider,
    CondensedPropertyError,
    fit_cubic,
    fit_inverse_cubic,
)
from chemsim.properties.dielectric import (
    BORN_PREFACTOR,
    BornArrays,
    Dielectric,
    DielectricProvider,
    IonicRadius,
    born_coefficient,
    build_born_arrays,
    ionic_radius,
)
from chemsim.properties.electrolyte import (
    AcidPair,
    dissociation_templates,
    electrolyte_provider,
    ion_thermochemistry,
    known_pairs,
)
from chemsim.properties.thermochemistry import (
    OutsideEstimatorDomain,
    ThermoData,
    ThermochemistryProvider,
)
from chemsim.properties.volatility import (
    Volatility,
    VolatilityError,
    VolatilityProvider,
    acentric_factor,
)

__all__ = [
    "estimate",
    "fragment",
    "JobackResult",
    "JobackError",
    "FragmentationError",
    "UnifacProvider",
    "UnifacGroups",
    "UnifacError",
    "ActivityArrays",
    "build_activity_arrays",
    "ThermoData",
    "OutsideEstimatorDomain",
    "ThermochemistryProvider",
    "Volatility",
    "VolatilityProvider",
    "VolatilityError",
    "acentric_factor",
    "CondensedData",
    "CondensedProvider",
    "CondensedPropertyError",
    "fit_cubic",
    "fit_inverse_cubic",
    "AcidPair",
    "electrolyte_provider",
    "dissociation_templates",
    "ion_thermochemistry",
    "known_pairs",
    "BORN_PREFACTOR",
    "BornArrays",
    "Dielectric",
    "DielectricProvider",
    "IonicRadius",
    "born_coefficient",
    "build_born_arrays",
    "ionic_radius",
]

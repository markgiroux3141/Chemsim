import pytest

from chemsim.threads import cap_blas_threads

# R2: before the chemsim imports below pull numpy in and the pools get sized.
# The standing suite record (1260 green, 2026-09-01) was taken thread-capped;
# capping here is what makes that condition reproducible instead of ambient.
# Numerically neutral, measured (R1); setdefault, so an explicit env wins.
cap_blas_threads()

from chemsim.properties import ThermochemistryProvider  # noqa: E402
from chemsim.reactions import ReactionTemplate  # noqa: E402


@pytest.fixture
def fischer_template():
    """Reversible Fischer esterification: acid + (sp3) alcohol <=> ester + water.

    Forward kinetics only -- the reverse (hydrolysis) is derived from reaction
    thermochemistry at network-build time, so there is no free parameter here.
    """
    return ReactionTemplate(
        name="fischer_esterification",
        smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
               ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
        A=1.0e6, Ea=50_000,
        reversible=True,
    )


@pytest.fixture
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def thermo_module():
    """The same provider, for module-scoped fixtures that build a network once.

    Safe to share: the provider is a pure cache over immutable data.
    """
    return ThermochemistryProvider()

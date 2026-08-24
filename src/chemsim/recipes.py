"""The curated PREPARATIONS, as data. One home for a recipe that has three readers.

Every other parameter table in this project has one home and a provenance note --
``reactions/library.py`` for templates, ``properties/formation_data.py`` for
thermochemistry, ``properties/dielectric_data.py`` for permittivities. A recipe is
the same kind of thing and did not have one, with the predictable result:
**the benzoic-acid prep existed in three copies** -- ``examples/multistep_prep.py``,
``validation/process_losses.py`` and ``tests/test_prep_side_products.py`` -- which
had to be kept in step by hand.

That was not a tidiness complaint. The pot's conditions are load-bearing and one of
them is counter-intuitive: this flask needs ``k_lle = 0.5`` rather than the default
5.0, because it genuinely wants to be two layers and at the default transfer rate
the two-phase system does not integrate. Every time that number moved, three files
had to move with it, and the harness and the example silently disagreeing is
exactly how a measured yield stops describing the example it was measured on.

⚠ **WHAT THIS MODULE IS NOT.** It is not a protocol runner and it does not step
anything. It holds the numbers and hands back a ``Vessel``; the three readers keep
their own narratives, assertions and instrumentation, which are genuinely different
jobs. Consolidating those would have been the wrong consolidation.
"""

from __future__ import annotations

from dataclasses import dataclass

from chemsim.matter import Molecule
from chemsim.network import ReactionNetwork, build_network
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.reactions.library import (
    aerobic_oxidation,
    esterification,
    ether_condensation,
    peroxide_over_oxidation,
)
from chemsim.vessel import TransferLosses, Vessel


def _smi(s: str) -> str:
    return Molecule.from_smiles(s).smiles


# The benzoic-acid route's species, resolved once so every reader indexes the same
# way. Named rather than inlined because "the benzoyl set" is what a mass balance
# has to be taken over.
ETHYL_BENZOATE = _smi("CCOC(=O)c1ccccc1")
BENZOIC_ACID = _smi("OC(=O)c1ccccc1")
BENZOATE = _smi("[O-]C(=O)c1ccccc1")
ACETIC_ACID = _smi("CC(=O)O")
ETHANOL, WATER, SODIUM, HYDROXIDE = "CCO", "O", "[Na+]", "[OH-]"
SULFURIC_ACID = "OS(=O)(=O)O"
OXYGEN, NITROGEN = "O=O", "N#N"

# Benzoyl-bearing species: what the route's mass closure is measured over. Ethanol
# and everything downstream of it is a side product, not a lost product.
BENZOYL = (BENZOIC_ACID, BENZOATE, ETHYL_BENZOATE)


@dataclass(frozen=True)
class BenzoicAcidPrep:
    """Benzoic acid from ethyl benzoate: saponify, acidify, crystallise, filter.

    Plain numbers, so the whole recipe is inspectable and a frontend could offer
    it as a starting point. ``scale`` multiplies every amount and every volume, and
    is a real lever rather than a convenience: the crust loss goes as
    ``V^(2/3)/V``, so a tenth-scale prep is punished and nothing tells it to be.
    """

    scale: float = 1.0
    ester: float = 0.20            # mol of ethyl benzoate charged
    water: float = 55.0            # mol
    hydroxide: float = 0.30        # mol of NaOH -- an excess, to drive hydrolysis
    acid: float = 0.28             # mol of H2SO4 for the quench
    pot_volume: float = 2.0        # L
    cook_T: float = 353.0          # K, 80 C
    crystallise_T: float = 275.0   # K, an ice bath
    # ⚠ BELOW THE DEFAULT OF 5.0 MOL/S, AND IT HAS TO BE. This pot is 55 mol of
    # strongly basic water beside 30 mL of nearly pure ester, and at the default
    # transfer rate the two-phase system does not integrate at all. What makes that
    # reportable rather than a fudge is that the answer does not depend on it: 0.5
    # and 0.05 give the same benzoate to five decimal places, because the ester
    # crosses the interface in well under a second either way and the
    # saponification is not transfer-limited on a two-hour timescale.
    k_lle: float = 0.5
    kla: float = 5.0
    k_diss: float = 0.05
    UA: float = 20.0
    cook_seconds: float = 7200.0
    quench_seconds: float = 3600.0
    growth_seconds: float = 14400.0
    # Cake void fraction for the filtrations. A property of the CAKE, not of the
    # liquor -- see ``Vessel.filter_into``.
    porosity: float = 0.4
    # The losses, both physical parameters with a plausible band rather than knobs
    # chosen to make the answer come out: a 5 s drain is an unhurried pour and a
    # 50 um crop is a fine one.
    drain_time: float = 5.0
    crystal_size: float = 50.0e-6

    # -- the pieces a reader assembles ---------------------------------------

    def network(self) -> ReactionNetwork:
        """The four library templates plus the dissociation set, over the feed.

        ⚠ The saponification has NO template. The only ester reaction here is the
        reversible Fischer esterification; hydrolysis runs to completion because
        hydroxide removes the benzoic acid as fast as the reverse makes it. The
        other three templates are the ways the route goes wrong, and they only
        engage because saponification hands them an alcohol.
        """
        return build_network(
            [ETHYL_BENZOATE, BENZOIC_ACID, ETHANOL, WATER, HYDROXIDE, SODIUM,
             SULFURIC_ACID, OXYGEN, NITROGEN],
            [esterification(), aerobic_oxidation(), peroxide_over_oxidation(),
             ether_condensation(), *dissociation_templates()],
            thermo=electrolyte_provider(), max_species=120,
        )

    def losses(self) -> TransferLosses:
        return TransferLosses(
            drain_time=self.drain_time, crystal_size=self.crystal_size
        )

    def pot(self, net: ReactionNetwork, *, air: bool = True,
            lossless: bool = False) -> Vessel:
        """The reaction flask, charged and with its headspace set.

        ⚠ "SEALED" IS A NITROGEN BLANKET, NOT ``kla = 0``, and ``air=False`` gives
        the blanket. Turning liquid-vapour transfer off entirely leaves the gas
        block identically zero AND FLAT, which is the ``num_jac`` pathology this
        project has documented three times over -- and it is also the less honest
        experiment, because it makes the existence of a vapour phase the variable
        instead of the oxygen budget.
        """
        s = self.scale
        v = Vessel(
            net, volume=self.pot_volume * s, T=self.cook_T, T_env=self.cook_T,
            UA=self.UA, kla=self.kla, k_diss=self.k_diss, k_vent=0.0,
            k_lle=self.k_lle, losses=None if lossless else self.losses(),
        )
        v.charge({
            WATER: self.water * s,
            ETHYL_BENZOATE: self.ester * s,
            HYDROXIDE: self.hydroxide * s,
            SODIUM: self.sodium_charge * s,
        })
        v.fill_headspace() if air else v.fill_headspace({NITROGEN: 1.0})
        return v

    @property
    def sodium_charge(self) -> float:
        """The counter-ion, which must match the hydroxide or the pot is not neutral."""
        return self.hydroxide

    def acidify(self, pot: Vessel) -> None:
        """The quench: sulfuric acid in, then straight into the ice bath.

        The most expensive integration in this project -- see
        ``validation/wall_clock.py``. Ten seconds of it costs more wall time than
        four hours of crystal growth.
        """
        pot.charge({SULFURIC_ACID: self.acid * self.scale})
        pot.set_environment(self.crystallise_T)

    def receiver(self, net: ReactionNetwork, volume: float,
                 *, lossless: bool = False) -> Vessel:
        """A cold flask to collect into. Every one has to be REMEMBERED by the
        caller, because a mass balance has to look everywhere the material could
        be -- including the intermediate cakes a wash loop replaces, which hold
        withheld film and a crust of crystals. Omitting them once made closure
        read 99.97%, which looked like a loss destroying matter when it was the
        harness failing to look where the matter went."""
        return Vessel(
            net, volume=volume * self.scale, T=self.crystallise_T,
            T_env=self.crystallise_T, UA=5.0, kla=0.0, k_diss=0.0,
            losses=None if lossless else self.losses(),
        )


BENZOIC_ACID_PREP = BenzoicAcidPrep()

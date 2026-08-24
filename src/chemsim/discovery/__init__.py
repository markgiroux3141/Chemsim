"""Layer 4.5 -- discovery: rate-based refinement of a reaction network.

Sits above ``numerics`` because deciding which species matter requires simulating
them. See ``refine.refine_network``.
"""

from chemsim.discovery.refine import RefinementReport, refine_network

__all__ = ["refine_network", "RefinementReport"]

"""
Random Routing Protocol baseline.
Models stochastic exploratory walk across active links.
"""

import random
from typing import Optional, Dict, Any
from .base_routing import BaseRoutingProtocol
from core.packet import Packet


class RandomRoutingProtocol(BaseRoutingProtocol):
    """Selects an active outgoing link uniformly at random."""

    def __init__(self, name: str = "Random-Walk"):
        super().__init__(name=name)

    def select_next_hop(
        self,
        current_node_id: int,
        destination_id: int,
        packet: Packet,
        current_time: float
    ) -> Optional[int]:
        if current_node_id == destination_id:
            return current_node_id

        active_neighbors = self.network.get_active_neighbors(current_node_id)
        if not active_neighbors:
            return None

        # If destination is a direct neighbor, route immediately
        if destination_id in active_neighbors:
            return destination_id

        # Avoid bouncing immediately back to the previous hop if other paths exist
        prev_node = packet.path_history[-2] if len(packet.path_history) >= 2 else None
        candidates = [n for n in active_neighbors if n != prev_node]
        if not candidates:
            candidates = active_neighbors

        return random.choice(candidates)

    def get_routing_table(self, node_id: int) -> Dict[str, Any]:
        return {"policy": "Uniform Random Selection over Active Neighbors"}

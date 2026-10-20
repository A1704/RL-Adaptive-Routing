"""
Shortest Path First (Dijkstra) Routing Protocol.
Models traditional static/link-state protocols like OSPF.
"""

from typing import Dict, Optional, Tuple, Any
from .base_routing import BaseRoutingProtocol
from core.network import Network
from core.packet import Packet


class DijkstraRoutingProtocol(BaseRoutingProtocol):
    """
    Computes shortest paths using Dijkstra's algorithm.
    Can operate in purely static mode (routes fixed at start) or dynamic OSPF mode.
    """

    def __init__(self, name: str = "Dijkstra-SPF", dynamic_reroute: bool = False):
        super().__init__(name=name)
        self.dynamic_reroute = dynamic_reroute
        # Precomputed next-hop table: (src, dst) -> next_hop
        self.routing_tables: Dict[Tuple[int, int], Optional[int]] = {}

    def initialize(self, network: Network):
        super().initialize(network)
        self._recompute_all_tables()

    def _recompute_all_tables(self):
        """Precompute all-pairs shortest paths using Dijkstra."""
        if not self.network:
            return
        self.routing_tables.clear()
        for src in self.network.nodes:
            distances, predecessors = self.network.dijkstra_shortest_paths(src, cost_metric="delay")
            for dst in self.network.nodes:
                if src == dst:
                    self.routing_tables[(src, dst)] = src
                    continue
                if distances[dst] == float('inf'):
                    self.routing_tables[(src, dst)] = None
                    continue

                # Walk back to find the first hop from src
                curr = dst
                prev = None
                while curr is not None and curr != src:
                    prev = curr
                    curr = predecessors[curr]
                self.routing_tables[(src, dst)] = prev

    def select_next_hop(
        self,
        current_node_id: int,
        destination_id: int,
        packet: Packet,
        current_time: float
    ) -> Optional[int]:
        if current_node_id == destination_id:
            return current_node_id

        if self.dynamic_reroute:
            # Dynamically compute based on current active links
            return self.network.get_shortest_path_next_hop(
                current_node_id, destination_id, cost_metric="delay"
            )

        # Static lookup
        next_hop = self.routing_tables.get((current_node_id, destination_id))
        
        # Check if the chosen link is currently UP
        if next_hop is not None:
            link = self.network.get_link(current_node_id, next_hop)
            if link and link.is_up:
                return next_hop

        # If static link is down and no dynamic reroute, packet cannot proceed
        return None

    def on_link_state_changed(self, u: int, v: int, is_up: bool, current_time: float):
        if self.dynamic_reroute:
            self._recompute_all_tables()

    def get_routing_table(self, node_id: int) -> Dict[str, Any]:
        """Export table for node_id."""
        return {
            f"dst_{dst}": hop
            for (src, dst), hop in self.routing_tables.items()
            if src == node_id
        }

    def reset(self):
        self._recompute_all_tables()

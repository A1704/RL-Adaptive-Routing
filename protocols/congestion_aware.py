"""
Congestion-Aware Dynamic Routing Protocol.
A heuristic baseline that balances shortest path distance with neighbor queue lengths.
"""

from typing import Optional, Dict, Any
from .base_routing import BaseRoutingProtocol
from core.packet import Packet


class CongestionAwareRoutingProtocol(BaseRoutingProtocol):
    """
    Evaluates next hops by combining physical link delay, neighbor buffer queue occupancy,
    and remaining topological distance to destination.
    """

    def __init__(
        self,
        name: str = "Congestion-Aware",
        queue_weight: float = 1.2,
        distance_weight: float = 1.0
    ):
        super().__init__(name=name)
        self.queue_weight = queue_weight
        self.distance_weight = distance_weight
        self.dist_cache: Dict[int, Dict[int, float]] = {}

    def initialize(self, network):
        super().initialize(network)
        self._build_distance_cache()

    def _build_distance_cache(self):
        """Cache baseline topological shortest path distances."""
        self.dist_cache.clear()
        for src in self.network.nodes:
            dists, _ = self.network.dijkstra_shortest_paths(src, cost_metric="delay")
            self.dist_cache[src] = dists

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

        if destination_id in active_neighbors:
            return destination_id

        prev_node = packet.path_history[-2] if len(packet.path_history) >= 2 else None
        
        best_cost = float('inf')
        best_hop = None

        for neighbor in active_neighbors:
            # Skip bouncing back unless it's the only option
            if neighbor == prev_node and len(active_neighbors) > 1:
                continue

            link = self.network.get_link(current_node_id, neighbor)
            link_delay = link.total_link_delay if link else 1.0
            
            # Estimate queue delay at the neighbor node
            neighbor_node = self.network.nodes[neighbor]
            queue_delay = neighbor_node.estimate_queue_delay()

            # Remaining distance to destination from neighbor
            rem_dist = self.dist_cache.get(neighbor, {}).get(destination_id, 10.0)

            total_cost = link_delay + (self.queue_weight * queue_delay) + (self.distance_weight * rem_dist)

            if total_cost < best_cost:
                best_cost = total_cost
                best_hop = neighbor

        return best_hop if best_hop is not None else (active_neighbors[0] if active_neighbors else None)

    def on_link_state_changed(self, u: int, v: int, is_up: bool, current_time: float):
        self._build_distance_cache()

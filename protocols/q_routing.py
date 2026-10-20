"""
Reinforcement Learning Q-Routing Protocol (Boyan & Littman, 1994).
Multi-Agent Reinforcement Learning where each router node acts as an autonomous agent.
"""

import random
import math
from typing import Dict, Tuple, Optional, Any, List
from .base_routing import BaseRoutingProtocol
from core.network import Network
from core.packet import Packet
from config.simulation_config import RLConfig


class QRoutingProtocol(BaseRoutingProtocol):
    """
    Multi-Agent Q-Routing protocol.
    Each router node maintains a Q-table Q_x(d, y) representing the estimated delivery
    latency from node x to destination d when forwarding via neighbor y.
    """

    def __init__(
        self,
        name: str = "Q-Routing",
        config: Optional[RLConfig] = None
    ):
        super().__init__(name=name)
        self.config = config or RLConfig()
        
        # Q-tables: node_id -> { (destination_id, neighbor_id): q_value }
        self.q_tables: Dict[int, Dict[Tuple[int, int], float]] = {}
        
        # Exploration probability
        self.epsilon = self.config.epsilon
        self.total_updates = 0
        self.total_explorations = 0

    def initialize(self, network: Network):
        super().initialize(network)
        self._initialize_q_tables()

    def _initialize_q_tables(self):
        """
        Initialize Q-tables using baseline link propagation delays.
        Q_x(d, y) = link_delay(x, y) + shortest_path_hops(y, d) * default_delay
        """
        if not self.network:
            return

        self.q_tables.clear()
        for node_id in self.network.nodes:
            self.q_tables[node_id] = {}

        # Warm start Q-values using baseline topological distances
        for u in self.network.nodes:
            dists, _ = self.network.dijkstra_shortest_paths(u, cost_metric="delay")
            for neighbor in self.network.nodes[u].neighbors:
                link = self.network.get_link(u, neighbor)
                link_delay = link.total_link_delay if link else 0.1

                for dst in self.network.nodes:
                    if dst == u:
                        continue
                    if neighbor == dst:
                        # Direct neighbor is the destination
                        self.q_tables[u][(dst, neighbor)] = link_delay
                    else:
                        # Neighbor to destination estimate
                        rem_dist = dists.get(dst, 5.0)
                        self.q_tables[u][(dst, neighbor)] = link_delay + rem_dist

    def get_q_value(self, node_id: int, dst: int, neighbor: int) -> float:
        """Get current Q-value Q_x(d, y), initializing on demand if unseen."""
        if node_id not in self.q_tables:
            self.q_tables[node_id] = {}
        
        key = (dst, neighbor)
        if key not in self.q_tables[node_id]:
            link = self.network.get_link(node_id, neighbor) if self.network else None
            self.q_tables[node_id][key] = (link.total_link_delay if link else 0.1) * 2.0
            
        return self.q_tables[node_id][key]

    def get_best_estimate(self, node_id: int, dst: int) -> float:
        """
        Calculate V_y(d) = min_{z in Neighbors(y)} Q_y(d, z).
        If node_id == dst, remaining cost is 0.0.
        """
        if node_id == dst:
            return 0.0

        active_neighbors = self.network.get_active_neighbors(node_id)
        if not active_neighbors:
            return float('inf')

        # If destination is directly reachable
        if dst in active_neighbors:
            return self.get_q_value(node_id, dst, dst)

        min_q = min(self.get_q_value(node_id, dst, n) for n in active_neighbors)
        return min_q

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

        # Immediate routing if destination is directly adjacent and link is UP
        if destination_id in active_neighbors:
            return destination_id

        prev_node = packet.path_history[-2] if len(packet.path_history) >= 2 else None
        
        # Filter candidates to avoid immediate loop-back if alternatives exist
        candidates = [n for n in active_neighbors if n != prev_node]
        if not candidates:
            candidates = active_neighbors

        # Epsilon-Greedy Exploration
        if random.random() < self.epsilon:
            self.total_explorations += 1
            chosen_hop = random.choice(candidates)
        else:
            # Greedy: Select neighbor with minimum estimated Q-value
            q_values = {n: self.get_q_value(current_node_id, destination_id, n) for n in candidates}
            min_q = min(q_values.values())
            # Handle ties randomly
            best_neighbors = [n for n, q in q_values.items() if math.isclose(q, min_q, rel_tol=1e-5)]
            chosen_hop = random.choice(best_neighbors)

        # Decay exploration rate over time
        self.epsilon = max(self.config.epsilon_min, self.epsilon * self.config.epsilon_decay)
        return chosen_hop

    def on_packet_forwarded(
        self,
        from_node: int,
        to_node: int,
        destination: int,
        queue_delay: float,
        link_delay: float,
        current_time: float
    ):
        """
        Q-Learning Update rule:
        Target = q_x + s_{xy} + min_z Q_y(d, z)
        Q_x(d, y) <- Q_x(d, y) + alpha * (Target - Q_x(d, y))
        """
        if from_node not in self.q_tables:
            return

        current_q = self.get_q_value(from_node, destination, to_node)
        
        # Target estimate from neighbor to_node
        best_neighbor_estimate = self.get_best_estimate(to_node, destination)
        
        # Total experienced transmission cost
        experienced_cost = (
            self.config.queue_weight * queue_delay +
            self.config.link_weight * link_delay +
            best_neighbor_estimate
        )

        # Temporal difference error
        td_error = experienced_cost - current_q
        alpha = self.config.learning_rate

        # Bellman update
        new_q = current_q + alpha * td_error
        self.q_tables[from_node][(destination, to_node)] = max(0.001, new_q)
        self.total_updates += 1

    def on_packet_dropped(
        self,
        packet: Packet,
        node_id: int,
        reason: str,
        current_time: float
    ):
        """Penalize Q-values leading to dropped packet paths."""
        if len(packet.path_history) >= 2:
            prev_node = packet.path_history[-2]
            key = (packet.destination_id, node_id)
            if prev_node in self.q_tables and key in self.q_tables[prev_node]:
                # Apply penalty for buffer overflow drop
                self.q_tables[prev_node][key] += 5.0

    def on_link_state_changed(self, u: int, v: int, is_up: bool, current_time: float):
        """Adjust Q-values when physical links change state."""
        if not is_up:
            # Assign heavy penalty to down links
            for dst in self.network.nodes:
                if (dst, v) in self.q_tables.get(u, {}):
                    self.q_tables[u][(dst, v)] = float('inf')
                if (dst, u) in self.q_tables.get(v, {}):
                    self.q_tables[v][(dst, u)] = float('inf')
        else:
            # Reinitialize recovered link
            link = self.network.get_link(u, v)
            cost = link.total_link_delay if link else 0.1
            for dst in self.network.nodes:
                if (dst, v) in self.q_tables.get(u, {}):
                    self.q_tables[u][(dst, v)] = cost + 2.0
                if (dst, u) in self.q_tables.get(v, {}):
                    self.q_tables[v][(dst, u)] = cost + 2.0

    def get_routing_table(self, node_id: int) -> Dict[str, Any]:
        """Export Q-table for node_id formatted as {dst: {neighbor: q_val}}."""
        table: Dict[int, Dict[int, float]] = {}
        if node_id in self.q_tables:
            for (dst, nbr), val in self.q_tables[node_id].items():
                if dst not in table:
                    table[dst] = {}
                table[dst][nbr] = round(val, 4)
        return {f"dst_{k}": v for k, v in table.items()}

    def reset(self):
        self.epsilon = self.config.epsilon
        self.total_updates = 0
        self.total_explorations = 0
        self._initialize_q_tables()

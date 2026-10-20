"""
Dual Reinforcement Routing (Dual Q-Routing / CQ-Routing).
Extends Q-Routing with bidirectional learning (forward and backward exploration)
and confidence tracking metrics to accelerate convergence.
"""

import random
import math
from typing import Dict, Tuple, Optional, Any, List
from .base_routing import BaseRoutingProtocol
from core.network import Network
from core.packet import Packet
from config.simulation_config import RLConfig


class DualQRoutingProtocol(BaseRoutingProtocol):
    """
    Dual Q-Routing updates Q-values in both directions:
    1. Forward update: Node x updates Q_x(d, y) using feedback from next-hop y.
    2. Backward update: Node y learns the reverse path to source s via x.
    3. Confidence metric: C_x(d, y) tracks how recently/reliably each path was updated.
    """

    def __init__(
        self,
        name: str = "Dual-Q-Routing",
        config: Optional[RLConfig] = None
    ):
        super().__init__(name=name)
        self.config = config or RLConfig()
        
        # Q-tables: node_id -> { (dst, neighbor): q_value }
        self.q_tables: Dict[int, Dict[Tuple[int, int], float]] = {}
        
        # Confidence tables: node_id -> { (dst, neighbor): confidence in [0, 1] }
        self.c_tables: Dict[int, Dict[Tuple[int, int], float]] = {}
        
        # Exploration probability
        self.epsilon = self.config.epsilon
        self.total_updates = 0
        self.backward_updates = 0

    def initialize(self, network: Network):
        super().initialize(network)
        self._initialize_tables()

    def _initialize_tables(self):
        if not self.network:
            return

        self.q_tables.clear()
        self.c_tables.clear()

        for node_id in self.network.nodes:
            self.q_tables[node_id] = {}
            self.c_tables[node_id] = {}

        for u in self.network.nodes:
            dists, _ = self.network.dijkstra_shortest_paths(u, cost_metric="delay")
            for neighbor in self.network.nodes[u].neighbors:
                link = self.network.get_link(u, neighbor)
                link_delay = link.total_link_delay if link else 0.1

                for dst in self.network.nodes:
                    if dst == u:
                        continue
                    key = (dst, neighbor)
                    if neighbor == dst:
                        self.q_tables[u][key] = link_delay
                        self.c_tables[u][key] = 1.0
                    else:
                        rem_dist = dists.get(dst, 5.0)
                        self.q_tables[u][key] = link_delay + rem_dist
                        self.c_tables[u][key] = 0.5  # Baseline initial confidence

    def get_q_value(self, node_id: int, dst: int, neighbor: int) -> float:
        if node_id not in self.q_tables:
            self.q_tables[node_id] = {}
            self.c_tables[node_id] = {}

        key = (dst, neighbor)
        if key not in self.q_tables[node_id]:
            link = self.network.get_link(node_id, neighbor) if self.network else None
            self.q_tables[node_id][key] = (link.total_link_delay if link else 0.1) * 2.0
            self.c_tables[node_id][key] = 0.5

        return self.q_tables[node_id][key]

    def get_confidence(self, node_id: int, dst: int, neighbor: int) -> float:
        key = (dst, neighbor)
        return self.c_tables.get(node_id, {}).get(key, 0.5)

    def get_best_estimate(self, node_id: int, dst: int) -> Tuple[float, float]:
        """
        Returns (best_q_value, confidence).
        """
        if node_id == dst:
            return 0.0, 1.0

        active_neighbors = self.network.get_active_neighbors(node_id)
        if not active_neighbors:
            return float('inf'), 0.0

        if dst in active_neighbors:
            return self.get_q_value(node_id, dst, dst), self.get_confidence(node_id, dst, dst)

        best_q = float('inf')
        best_conf = 0.0
        for n in active_neighbors:
            q = self.get_q_value(node_id, dst, n)
            if q < best_q:
                best_q = q
                best_conf = self.get_confidence(node_id, dst, n)

        return best_q, best_conf

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
        candidates = [n for n in active_neighbors if n != prev_node]
        if not candidates:
            candidates = active_neighbors

        # Epsilon-Greedy with confidence-weighted exploration
        if random.random() < self.epsilon:
            # Prefer exploring paths with lower confidence (uncertainty-driven exploration)
            confidences = [1.0 - self.get_confidence(current_node_id, destination_id, n) for n in candidates]
            total_c = sum(confidences)
            if total_c > 0:
                probs = [c / total_c for c in confidences]
                chosen_hop = random.choices(candidates, weights=probs, k=1)[0]
            else:
                chosen_hop = random.choice(candidates)
        else:
            q_values = {n: self.get_q_value(current_node_id, destination_id, n) for n in candidates}
            min_q = min(q_values.values())
            best_candidates = [n for n, q in q_values.items() if math.isclose(q, min_q, rel_tol=1e-5)]
            chosen_hop = random.choice(best_candidates)

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
        # 1. Forward Update at from_node
        current_q = self.get_q_value(from_node, destination, to_node)
        best_est, conf = self.get_best_estimate(to_node, destination)
        
        experienced_cost = (
            self.config.queue_weight * queue_delay +
            self.config.link_weight * link_delay +
            best_est
        )

        effective_alpha = self.config.learning_rate * max(0.5, conf)
        new_q = current_q + effective_alpha * (experienced_cost - current_q)
        
        self.q_tables[from_node][(destination, to_node)] = max(0.001, new_q)
        # Update confidence
        self.c_tables[from_node][(destination, to_node)] = min(1.0, conf * self.config.confidence_decay + 0.1)
        self.total_updates += 1

        # 2. Backward Update at to_node (learning route back to source)
        # The node to_node now has fresh evidence about reaching from_node
        hop_cost = queue_delay + link_delay
        back_key = (from_node, from_node)
        self.q_tables[to_node][back_key] = hop_cost
        self.c_tables[to_node][back_key] = 1.0
        self.backward_updates += 1

    def on_packet_dropped(self, packet: Packet, node_id: int, reason: str, current_time: float):
        if len(packet.path_history) >= 2:
            prev_node = packet.path_history[-2]
            key = (packet.destination_id, node_id)
            if prev_node in self.q_tables and key in self.q_tables[prev_node]:
                self.q_tables[prev_node][key] += 6.0
                self.c_tables[prev_node][key] = 0.1

    def on_link_state_changed(self, u: int, v: int, is_up: bool, current_time: float):
        if not is_up:
            for dst in self.network.nodes:
                if (dst, v) in self.q_tables.get(u, {}):
                    self.q_tables[u][(dst, v)] = float('inf')
                    self.c_tables[u][(dst, v)] = 0.0
                if (dst, u) in self.q_tables.get(v, {}):
                    self.q_tables[v][(dst, u)] = float('inf')
                    self.c_tables[v][(dst, u)] = 0.0
        else:
            link = self.network.get_link(u, v)
            cost = link.total_link_delay if link else 0.1
            for dst in self.network.nodes:
                if (dst, v) in self.q_tables.get(u, {}):
                    self.q_tables[u][(dst, v)] = cost + 1.5
                    self.c_tables[u][(dst, v)] = 0.6
                if (dst, u) in self.q_tables.get(v, {}):
                    self.q_tables[v][(dst, u)] = cost + 1.5
                    self.c_tables[v][(dst, u)] = 0.6

    def get_routing_table(self, node_id: int) -> Dict[str, Any]:
        table: Dict[int, Dict[int, Dict[str, float]]] = {}
        if node_id in self.q_tables:
            for (dst, nbr), q_val in self.q_tables[node_id].items():
                if dst not in table:
                    table[dst] = {}
                c_val = self.c_tables.get(node_id, {}).get((dst, nbr), 0.0)
                table[dst][nbr] = {"q": round(q_val, 4), "confidence": round(c_val, 3)}
        return {f"dst_{k}": v for k, v in table.items()}

    def reset(self):
        self.epsilon = self.config.epsilon
        self.total_updates = 0
        self.backward_updates = 0
        self._initialize_tables()

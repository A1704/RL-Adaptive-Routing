"""
Network Link representation connecting two nodes.
"""

from typing import Tuple, Optional
import random


class Link:
    """Represents a full-duplex communication link between two network nodes."""

    def __init__(
        self,
        node_a: int,
        node_b: int,
        bandwidth: float = 10.0,
        propagation_delay: float = 0.05,
        drop_probability: float = 0.0
    ):
        # Canonical order for undirected identification
        self.node_a = min(node_a, node_b)
        self.node_b = max(node_a, node_b)
        self.bandwidth = bandwidth  # Packets per second
        self.propagation_delay = propagation_delay  # Seconds
        self.drop_probability = drop_probability
        self.is_up = True
        
        # Performance metrics
        self.packets_transmitted = 0
        self.packets_dropped = 0
        self.last_state_change = 0.0

    @property
    def key(self) -> Tuple[int, int]:
        """Unique identifier tuple for the link."""
        return (self.node_a, self.node_b)

    @property
    def transmission_delay(self) -> float:
        """Time to push one packet onto the physical wire."""
        if self.bandwidth <= 0:
            return float('inf')
        return 1.0 / self.bandwidth

    @property
    def total_link_delay(self) -> float:
        """Total baseline delay across this link with zero queueing."""
        return self.transmission_delay + self.propagation_delay

    def connects(self, u: int, v: int) -> bool:
        """Check if this link connects nodes u and v."""
        return (self.node_a == min(u, v)) and (self.node_b == max(u, v))

    def other_end(self, node_id: int) -> int:
        """Get the node ID at the other end of the link."""
        if node_id == self.node_a:
            return self.node_b
        elif node_id == self.node_b:
            return self.node_a
        raise ValueError(f"Node {node_id} is not attached to link {self.key}")

    def should_drop_packet(self) -> bool:
        """Stochastically simulate link noise/loss."""
        if not self.is_up:
            return True
        if self.drop_probability > 0:
            return random.random() < self.drop_probability
        return False

    def set_down(self, current_time: float = 0.0):
        """Simulate a physical link cut/failure."""
        self.is_up = False
        self.last_state_change = current_time

    def set_up(self, current_time: float = 0.0):
        """Restore physical link."""
        self.is_up = True
        self.last_state_change = current_time

    def __repr__(self) -> str:
        status = "UP" if self.is_up else "DOWN"
        return f"Link({self.node_a} <-> {self.node_b}, bw={self.bandwidth}, delay={self.propagation_delay}s, {status})"


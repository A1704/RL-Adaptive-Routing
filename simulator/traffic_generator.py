"""
Traffic Generator for Network Routing Simulation.
Generates stochastic packet arrival events (Poisson, Bursty, Hotspot).
"""

import random
import math
from typing import List, Tuple, Optional
from core.packet import Packet
from config.simulation_config import TrafficConfig


class TrafficGenerator:
    """Generates synthetic network traffic following various load patterns."""

    def __init__(
        self,
        node_ids: List[int],
        config: Optional[TrafficConfig] = None
    ):
        self.node_ids = list(node_ids)
        self.config = config or TrafficConfig()
        self.packet_counter = 0

    def sample_interarrival_time(self, current_time: float) -> float:
        """
        Sample the next inter-arrival delay using exponential distribution (Poisson process).
        Applies burst multiplier if currently within a burst window.
        """
        rate = self.config.packet_rate

        if self.config.traffic_pattern == "bursty":
            cycle_pos = current_time % self.config.burst_interval
            if cycle_pos < self.config.burst_duration:
                # Currently in burst period!
                rate *= self.config.burst_multiplier

        if rate <= 0:
            return 1.0

        # Exponential distribution: -ln(U) / lambda
        u = max(1e-9, random.random())
        return -math.log(u) / rate

    def sample_source_and_destination(self) -> Tuple[int, int]:
        """Choose source and destination node IDs based on traffic pattern."""
        if len(self.node_ids) < 2:
            raise ValueError("Network must have at least 2 nodes to route packets.")

        src = random.choice(self.node_ids)

        if self.config.traffic_pattern == "hotspot" and self.config.hotspot_nodes:
            # 70% chance to target a hotspot node
            valid_hotspots = [h for h in self.config.hotspot_nodes if h in self.node_ids and h != src]
            if valid_hotspots and random.random() < 0.70:
                dst = random.choice(valid_hotspots)
                return src, dst

        # Uniform selection
        candidates = [n for n in self.node_ids if n != src]
        dst = random.choice(candidates)
        return src, dst

    def create_packet(self, current_time: float) -> Packet:
        """Instantiate a new packet."""
        self.packet_counter += 1
        src, dst = self.sample_source_and_destination()
        return Packet(
            packet_id=self.packet_counter,
            source_id=src,
            destination_id=dst,
            creation_time=current_time
        )

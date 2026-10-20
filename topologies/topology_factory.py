"""
Network Topology Factory.
Generates benchmark topologies: Grid 6x6 (Boyan-Littman), NSFNet (14-node), ARPANET, Ring-Chord, and Bottleneck.
"""

import math
from typing import Dict, Tuple, Optional
from core.network import Network
from config.simulation_config import NetworkConfig


class TopologyFactory:
    """Factory for generating standardized networking topologies with 2D visual layouts."""

    @staticmethod
    def create_bottleneck_topology(
        buffer_capacity: int = 20,
        bw_fast: float = 20.0,
        bw_slow: float = 5.0
    ) -> Network:
        r"""
        Simple 6-node Diamond topology with a fast path and an alternate detour path:
             [1] (fast, narrow bandwidth bottleneck)
           /     \
        [0]       [3] --- [4] --- [5]
           \     /
             [2] (slower propagation, high bandwidth)
        """
        net = Network()
        positions = {
            0: (100, 250),
            1: (250, 150),
            2: (250, 350),
            3: (400, 250),
            4: (550, 250),
            5: (700, 250)
        }

        for nid, pos in positions.items():
            net.add_node(nid, buffer_capacity=buffer_capacity, name=f"R{nid}", pos=pos)

        # Primary path: low propagation delay, but low bandwidth (bottlenecks under load)
        net.add_link(0, 1, bandwidth=bw_slow, propagation_delay=0.02)
        net.add_link(1, 3, bandwidth=bw_slow, propagation_delay=0.02)

        # Detour path: higher propagation delay, but high bandwidth (absorbs excess load)
        net.add_link(0, 2, bandwidth=bw_fast, propagation_delay=0.06)
        net.add_link(2, 3, bandwidth=bw_fast, propagation_delay=0.06)

        # Tail links
        net.add_link(3, 4, bandwidth=bw_fast, propagation_delay=0.02)
        net.add_link(4, 5, bandwidth=bw_fast, propagation_delay=0.02)

        return net

    @staticmethod
    def create_grid_topology(
        rows: int = 6,
        cols: int = 6,
        buffer_capacity: int = 25,
        default_bandwidth: float = 12.0,
        default_prop_delay: float = 0.04
    ) -> Network:
        """
        Classic Boyan & Littman 6x6 Grid network topology (36 nodes).
        Standard benchmark in Q-Routing literature.
        """
        net = Network()
        spacing_x = 110
        spacing_y = 70
        offset_x = 80
        offset_y = 60

        for r in range(rows):
            for c in range(cols):
                nid = r * cols + c
                pos = (offset_x + c * spacing_x, offset_y + r * spacing_y)
                net.add_node(nid, buffer_capacity=buffer_capacity, name=f"N{nid}", pos=pos)

        for r in range(rows):
            for c in range(cols):
                u = r * cols + c
                # Horizontal link to right neighbor
                if c + 1 < cols:
                    v = r * cols + (c + 1)
                    net.add_link(u, v, bandwidth=default_bandwidth, propagation_delay=default_prop_delay)
                # Vertical link to bottom neighbor
                if r + 1 < rows:
                    v = (r + 1) * cols + c
                    net.add_link(u, v, bandwidth=default_bandwidth, propagation_delay=default_prop_delay)

        return net

    @staticmethod
    def create_nsfnet_topology(
        buffer_capacity: int = 25,
        default_bandwidth: float = 15.0,
        default_prop_delay: float = 0.03
    ) -> Network:
        """
        14-node, 21-link NSFNet (National Science Foundation Network) backbone topology.
        """
        net = Network()
        positions = {
            0: (80, 180),    # Seattle
            1: (180, 120),   # Salt Lake City
            2: (120, 360),   # San Francisco
            3: (220, 380),   # Los Angeles
            4: (380, 420),   # Houston
            5: (320, 240),   # Denver
            6: (450, 160),   # Lincoln
            7: (520, 240),   # Chicago
            8: (600, 360),   # Atlanta
            9: (640, 160),   # Pittsburgh
            10: (720, 120),  # Ithaca
            11: (740, 260),  # Washington DC
            12: (760, 180),  # Princeton
            13: (820, 140)   # Boston
        }

        for nid, pos in positions.items():
            net.add_node(nid, buffer_capacity=buffer_capacity, name=f"Node-{nid}", pos=pos)

        # 21 bidirectional links
        nsf_links = [
            (0, 1), (0, 2), (0, 3),
            (1, 2), (1, 7),
            (2, 5),
            (3, 4), (3, 5),
            (4, 5), (4, 8),
            (5, 6),
            (6, 7), (6, 9),
            (7, 8), (7, 10),
            (8, 11),
            (9, 10), (9, 12),
            (10, 13),
            (11, 12), (11, 13),
            (12, 13)
        ]

        for u, v in nsf_links:
            net.add_link(u, v, bandwidth=default_bandwidth, propagation_delay=default_prop_delay)

        return net

    @staticmethod
    def create_ring_chord_topology(
        num_nodes: int = 12,
        buffer_capacity: int = 25,
        default_bandwidth: float = 12.0,
        default_prop_delay: float = 0.04
    ) -> Network:
        """
        Circular ring with cross-chord shortcuts.
        Useful for observing route divergence and shortcut adaptation.
        """
        net = Network()
        center_x, center_y = 400, 250
        radius = 180

        for i in range(num_nodes):
            angle = (2 * math.pi * i) / num_nodes
            pos = (
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle)
            )
            net.add_node(i, buffer_capacity=buffer_capacity, name=f"R{i}", pos=pos)

        # Ring links
        for i in range(num_nodes):
            nxt = (i + 1) % num_nodes
            net.add_link(i, nxt, bandwidth=default_bandwidth, propagation_delay=default_prop_delay)

        # Cross chords
        for i in range(0, num_nodes // 2, 2):
            opposite = (i + num_nodes // 2) % num_nodes
            net.add_link(i, opposite, bandwidth=default_bandwidth * 1.5, propagation_delay=default_prop_delay * 0.8)

        return net

    @classmethod
    def get_topology(cls, name: str, **kwargs) -> Network:
        """Helper to get topology by string name."""
        name_lower = name.lower().replace("-", "").replace("_", "")
        if "grid" in name_lower:
            return cls.create_grid_topology(**kwargs)
        elif "nsf" in name_lower:
            return cls.create_nsfnet_topology(**kwargs)
        elif "ring" in name_lower:
            return cls.create_ring_chord_topology(**kwargs)
        elif "bottleneck" in name_lower or "diamond" in name_lower:
            return cls.create_bottleneck_topology(**kwargs)
        else:
            raise ValueError(f"Unknown topology '{name}'. Available: 'grid', 'nsfnet', 'ring', 'bottleneck'")

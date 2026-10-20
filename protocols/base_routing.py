"""
Abstract Base Class for Network Routing Protocols.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from core.network import Network
from core.packet import Packet


class BaseRoutingProtocol(ABC):
    """Abstract interface that all routing protocols (RL and baselines) implement."""

    def __init__(self, name: str):
        self.name = name
        self.network: Optional[Network] = None

    def initialize(self, network: Network):
        """Bind the protocol to the network environment and initialize tables."""
        self.network = network

    @abstractmethod
    def select_next_hop(
        self,
        current_node_id: int,
        destination_id: int,
        packet: Packet,
        current_time: float
    ) -> Optional[int]:
        """
        Choose the next neighbor node to forward the packet to.
        Returns the next hop node ID, or None if no valid route exists.
        """
        pass

    def on_packet_forwarded(
        self,
        from_node: int,
        to_node: int,
        destination: int,
        queue_delay: float,
        link_delay: float,
        current_time: float
    ):
        """Hook called when a node forwards a packet (used for RL state updates)."""
        pass

    def on_packet_delivered(self, packet: Packet, current_time: float):
        """Hook called when a packet successfully reaches its destination."""
        pass

    def on_packet_dropped(
        self,
        packet: Packet,
        node_id: int,
        reason: str,
        current_time: float
    ):
        """Hook called when a packet is dropped due to queue overflow, TTL, or link failure."""
        pass

    def on_link_state_changed(self, u: int, v: int, is_up: bool, current_time: float):
        """Hook called when a network link fails or recovers."""
        pass

    def get_routing_table(self, node_id: int) -> Dict[str, Any]:
        """Export current routing table / Q-table for inspection or debugging."""
        return {}

    def reset(self):
        """Reset internal routing states or Q-tables."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"

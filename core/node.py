"""
Network Node (Router) representation with finite FIFO queue buffer.
"""

from collections import deque
from typing import List, Dict, Optional, Any
from .packet import Packet
from .link import Link


class Node:
    """Represents a network router with finite packet buffer and routing capabilities."""

    def __init__(
        self,
        node_id: int,
        buffer_capacity: int = 25,
        name: Optional[str] = None
    ):
        self.node_id = node_id
        self.name = name or f"Node-{node_id}"
        self.buffer_capacity = buffer_capacity
        
        # FIFO Packet queue
        self.packet_queue: deque[Packet] = deque()
        
        # Topology connections: neighbor_id -> Link
        self.links: Dict[int, Link] = {}
        
        # Statistics
        self.total_received = 0
        self.total_forwarded = 0
        self.total_delivered = 0
        self.total_buffer_drops = 0
        self.peak_queue_size = 0
        self.queue_history: List[int] = []

    @property
    def neighbors(self) -> List[int]:
        """List of all neighboring node IDs."""
        return list(self.links.keys())

    @property
    def active_neighbors(self) -> List[int]:
        """List of active neighboring node IDs whose links are UP."""
        return [nid for nid, link in self.links.items() if link.is_up]

    @property
    def current_queue_size(self) -> int:
        """Current number of packets waiting in buffer."""
        return len(self.packet_queue)

    @property
    def buffer_occupancy_ratio(self) -> float:
        """Fraction of buffer capacity currently occupied [0.0, 1.0]."""
        if self.buffer_capacity <= 0:
            return 1.0
        return len(self.packet_queue) / self.buffer_capacity

    def add_link(self, neighbor_id: int, link: Link):
        """Register an adjacent link connecting to a neighbor."""
        self.links[neighbor_id] = link

    def enqueue_packet(self, packet: Packet, current_time: float) -> bool:
        """
        Attempt to enqueue a packet into this node's buffer.
        Returns True if successfully buffered, False if dropped due to buffer overflow.
        """
        self.total_received += 1
        if len(self.packet_queue) >= self.buffer_capacity:
            self.total_buffer_drops += 1
            packet.mark_dropped(f"Buffer overflow at Node {self.node_id}", current_time)
            return False
        
        packet.in_queue_since = current_time
        self.packet_queue.append(packet)
        self.peak_queue_size = max(self.peak_queue_size, len(self.packet_queue))
        return True

    def dequeue_packet(self, current_time: float) -> Optional[Packet]:
        """Dequeue the next FIFO packet for transmission."""
        if not self.packet_queue:
            return None
        packet = self.packet_queue.popleft()
        queue_wait = current_time - packet.in_queue_since
        packet.total_queue_delay += max(0.0, queue_wait)
        return packet

    def peek_packet(self) -> Optional[Packet]:
        """Inspect the front packet without removing it."""
        if not self.packet_queue:
            return None
        return self.packet_queue[0]

    def estimate_queue_delay(self, neighbor_id: Optional[int] = None) -> float:
        """
        Estimate queue delay (in seconds) for a packet arriving at this node.
        Queue delay ≈ (packets ahead) / bandwidth.
        """
        if not self.links:
            return 0.0
        
        # If neighbor specified, use that link bandwidth; otherwise average bandwidth
        if neighbor_id is not None and neighbor_id in self.links:
            bw = self.links[neighbor_id].bandwidth
        else:
            bw = sum(l.bandwidth for l in self.links.values()) / max(1, len(self.links))
            
        return (len(self.packet_queue) + 1) / max(0.1, bw)

    def reset_stats(self):
        """Clear operational statistics."""
        self.packet_queue.clear()
        self.total_received = 0
        self.total_forwarded = 0
        self.total_delivered = 0
        self.total_buffer_drops = 0
        self.peak_queue_size = 0
        self.queue_history.clear()

    def __repr__(self) -> str:
        return f"Node({self.node_id}, q={len(self.packet_queue)}/{self.buffer_capacity}, drops={self.total_buffer_drops})"


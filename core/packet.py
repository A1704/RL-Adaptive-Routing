"""
Packet representation in the simulated network.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Packet:
    """Represents a network data packet traversing routers."""
    packet_id: int
    source_id: int
    destination_id: int
    creation_time: float
    ttl: int = 64
    size_bytes: int = 1500
    
    # State tracking
    current_node_id: int = -1
    path_history: List[int] = field(default_factory=list)
    hop_count: int = 0
    in_queue_since: float = 0.0
    total_queue_delay: float = 0.0
    arrival_time: Optional[float] = None
    dropped: bool = False
    drop_reason: Optional[str] = None

    def __post_init__(self):
        if self.current_node_id == -1:
            self.current_node_id = self.source_id
        if not self.path_history:
            self.path_history.append(self.source_id)

    @property
    def end_to_end_delay(self) -> Optional[float]:
        """Total latency from packet creation to destination delivery."""
        if self.arrival_time is not None:
            return max(0.0, self.arrival_time - self.creation_time)
        return None

    def record_hop(self, next_node_id: int, current_time: float):
        """Record forwarding to the next node."""
        self.hop_count += 1
        self.current_node_id = next_node_id
        self.path_history.append(next_node_id)
        self.ttl -= 1

    def is_expired(self) -> bool:
        """Check if packet TTL has expired."""
        return self.ttl <= 0

    def mark_dropped(self, reason: str, drop_time: float):
        """Mark packet as dropped."""
        self.dropped = True
        self.drop_reason = reason


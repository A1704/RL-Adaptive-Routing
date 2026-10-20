"""
Performance Metrics Collector for Network Routing Simulations.
Tracks latency, throughput, delivery ratios, drops, and time-series trends.
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict
import math
from core.packet import Packet


class MetricsCollector:
    """Collects and aggregates networking and routing performance metrics."""

    def __init__(self, time_window_size: float = 1.0):
        self.time_window_size = time_window_size  # Bucket size in seconds for time-series
        self.reset()

    def reset(self):
        """Reset all tracked metrics."""
        self.total_generated = 0
        self.total_delivered = 0
        self.total_dropped = 0
        self.drop_reasons: Dict[str, int] = defaultdict(int)

        self.delivered_packets: List[Packet] = []
        self.dropped_packets: List[Packet] = []

        # Time series buckets: window_index -> count/sum
        self.ts_delivered = defaultdict(int)
        self.ts_generated = defaultdict(int)
        self.ts_latency_sum = defaultdict(float)
        self.ts_latency_count = defaultdict(int)
        self.ts_drops = defaultdict(int)
        
        # Periodic snapshot history
        self.history_timestamps: List[float] = []
        self.history_avg_latency: List[float] = []
        self.history_throughput: List[float] = []
        self.history_pdr: List[float] = []
        self.history_drops: List[int] = []

    def record_packet_generated(self, packet: Packet, current_time: float):
        """Record packet generation."""
        self.total_generated += 1
        w = int(current_time / self.time_window_size)
        self.ts_generated[w] += 1

    def record_packet_delivered(self, packet: Packet, current_time: float):
        """Record successful delivery at destination."""
        self.total_delivered += 1
        packet.arrival_time = current_time
        self.delivered_packets.append(packet)

        w = int(current_time / self.time_window_size)
        self.ts_delivered[w] += 1
        delay = packet.end_to_end_delay or 0.0
        self.ts_latency_sum[w] += delay
        self.ts_latency_count[w] += 1

    def record_packet_dropped(self, packet: Packet, reason: str, current_time: float):
        """Record packet loss event."""
        self.total_dropped += 1
        self.drop_reasons[reason] += 1
        packet.mark_dropped(reason, current_time)
        self.dropped_packets.append(packet)

        w = int(current_time / self.time_window_size)
        self.ts_drops[w] += 1

    def record_periodic_snapshot(self, current_time: float):
        """Take a snapshot of current cumulative/windowed performance."""
        self.history_timestamps.append(round(current_time, 2))
        
        # Latency
        avg_lat = self.get_average_latency()
        self.history_avg_latency.append(round(avg_lat, 4))
        
        # Throughput
        tp = self.get_throughput(current_time)
        self.history_throughput.append(round(tp, 2))
        
        # PDR
        pdr = self.get_delivery_ratio()
        self.history_pdr.append(round(pdr * 100.0, 2))
        
        # Drops
        self.history_drops.append(self.total_dropped)

    def get_average_latency(self) -> float:
        """Calculate mean end-to-end latency for delivered packets."""
        if not self.delivered_packets:
            return 0.0
        delays = [p.end_to_end_delay for p in self.delivered_packets if p.end_to_end_delay is not None]
        return sum(delays) / len(delays) if delays else 0.0

    def get_delivery_ratio(self) -> float:
        """Packet Delivery Ratio (PDR) = delivered / generated."""
        if self.total_generated == 0:
            return 1.0
        return self.total_delivered / self.total_generated

    def get_throughput(self, current_time: float) -> float:
        """Delivered packets per second over simulation duration."""
        if current_time <= 0.0:
            return 0.0
        return self.total_delivered / current_time

    def get_average_hops(self) -> float:
        """Average number of hops traveled by delivered packets."""
        if not self.delivered_packets:
            return 0.0
        return sum(p.hop_count for p in self.delivered_packets) / len(self.delivered_packets)

    def get_summary(self, current_time: float) -> Dict[str, Any]:
        """Compile a comprehensive metrics summary."""
        avg_lat = self.get_average_latency()
        pdr = self.get_delivery_ratio()
        tp = self.get_throughput(current_time)
        avg_hops = self.get_average_hops()

        # Latency standard deviation
        if len(self.delivered_packets) > 1:
            delays = [p.end_to_end_delay for p in self.delivered_packets if p.end_to_end_delay is not None]
            var = sum((d - avg_lat) ** 2 for d in delays) / (len(delays) - 1)
            std_lat = math.sqrt(var)
        else:
            std_lat = 0.0

        return {
            "simulation_time": round(current_time, 2),
            "packets_generated": self.total_generated,
            "packets_delivered": self.total_delivered,
            "packets_dropped": self.total_dropped,
            "packet_delivery_ratio_pct": round(pdr * 100.0, 2),
            "drop_rate_pct": round((self.total_dropped / max(1, self.total_generated)) * 100.0, 2),
            "average_latency_s": round(avg_lat, 4),
            "std_latency_s": round(std_lat, 4),
            "average_hops": round(avg_hops, 2),
            "throughput_pps": round(tp, 2),
            "drop_reasons": dict(self.drop_reasons),
        }

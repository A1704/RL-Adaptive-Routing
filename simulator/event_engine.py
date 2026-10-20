"""
Discrete Event Simulation (DES) Engine for Network Routing.
Coordinates packet generation, queue processing, link transmission, and metrics collection.
"""

import heapq
from typing import Dict, List, Tuple, Optional, Callable, Any
from core.network import Network
from core.packet import Packet
from protocols.base_routing import BaseRoutingProtocol
from .traffic_generator import TrafficGenerator
from .metrics_collector import MetricsCollector
from config.simulation_config import SimulationConfig


# Event Types
EVENT_PACKET_GENERATE = 1
EVENT_NODE_SERVICE = 2
EVENT_PACKET_ARRIVE = 3
EVENT_LINK_FAIL = 4
EVENT_LINK_RESTORE = 5
EVENT_SNAPSHOT = 6


class SimulationEngine:
    """Discrete Event Simulator driving the network routing environment."""

    def __init__(
        self,
        network: Network,
        protocol: BaseRoutingProtocol,
        config: Optional[SimulationConfig] = None
    ):
        self.network = network
        self.protocol = protocol
        self.config = config or SimulationConfig()

        self.current_time = 0.0
        self.event_queue: List[Tuple[float, int, int, Any]] = []  # (timestamp, seq, event_type, data)
        self.event_counter = 0

        # Node transmission state: node_id -> time when transmitter becomes free
        self.node_transmitter_busy_until: Dict[int, float] = {nid: 0.0 for nid in self.network.nodes}

        self.traffic_gen = TrafficGenerator(
            node_ids=list(self.network.nodes.keys()),
            config=self.config.traffic
        )
        self.metrics = MetricsCollector(time_window_size=1.0)

        # Step listeners for live visualizer
        self.step_listeners: List[Callable[[float, int, Any], None]] = []
        
        # Track currently in-flight packets for GUI animation: id -> (src, dst, start_time, arrive_time)
        self.in_flight_transmissions: Dict[int, Dict[str, Any]] = {}

        self._is_initialized = False

    def initialize(self):
        """Initialize simulation, bind protocol, and schedule initial events."""
        self.current_time = 0.0
        self.event_queue.clear()
        self.event_counter = 0
        self.node_transmitter_busy_until = {nid: 0.0 for nid in self.network.nodes}
        self.in_flight_transmissions.clear()

        self.network.reset_network_state()
        self.metrics.reset()
        self.protocol.initialize(self.network)

        # Schedule initial packet generation
        first_gen_time = self.traffic_gen.sample_interarrival_time(0.0)
        self.schedule_event(first_gen_time, EVENT_PACKET_GENERATE, None)

        # Schedule periodic metrics snapshot
        self.schedule_event(1.0, EVENT_SNAPSHOT, None)

        self._is_initialized = True

    def schedule_event(self, timestamp: float, event_type: int, data: Any):
        """Push an event into the priority queue."""
        self.event_counter += 1
        heapq.heappush(self.event_queue, (timestamp, self.event_counter, event_type, data))

    def register_step_listener(self, callback: Callable[[float, int, Any], None]):
        """Register a callback invoked after every event execution."""
        self.step_listeners.append(callback)

    def schedule_link_failure(self, u: int, v: int, fail_time: float, restore_time: Optional[float] = None):
        """Schedule a planned link cut and optional recovery."""
        self.schedule_event(fail_time, EVENT_LINK_FAIL, (u, v))
        if restore_time is not None and restore_time > fail_time:
            self.schedule_event(restore_time, EVENT_LINK_RESTORE, (u, v))

    def step(self) -> bool:
        """
        Execute the single next earliest event from the event queue.
        Returns False if event queue is empty or duration exceeded, True otherwise.
        """
        if not self._is_initialized:
            self.initialize()

        if not self.event_queue:
            return False

        timestamp, _, event_type, data = heapq.heappop(self.event_queue)

        if timestamp > self.config.duration:
            return False

        self.current_time = timestamp

        # Dispatch event handler
        if event_type == EVENT_PACKET_GENERATE:
            self._handle_packet_generate()
        elif event_type == EVENT_NODE_SERVICE:
            self._handle_node_service(node_id=data)
        elif event_type == EVENT_PACKET_ARRIVE:
            self._handle_packet_arrive(arrival_data=data)
        elif event_type == EVENT_LINK_FAIL:
            self._handle_link_fail(link_pair=data)
        elif event_type == EVENT_LINK_RESTORE:
            self._handle_link_restore(link_pair=data)
        elif event_type == EVENT_SNAPSHOT:
            self._handle_snapshot()

        # Clean up finished in-flight transmissions
        finished_transmissions = [
            pid for pid, info in self.in_flight_transmissions.items()
            if self.current_time >= info["arrive_time"]
        ]
        for pid in finished_transmissions:
            del self.in_flight_transmissions[pid]

        # Notify visualizer / listeners
        for listener in self.step_listeners:
            listener(self.current_time, event_type, data)

        return True

    def _handle_packet_generate(self):
        """Generate a new packet and place it in the source node buffer."""
        packet = self.traffic_gen.create_packet(self.current_time)
        self.metrics.record_packet_generated(packet, self.current_time)

        src_node = self.network.nodes[packet.source_id]
        buffered = src_node.enqueue_packet(packet, self.current_time)
        
        if not buffered:
            self.metrics.record_packet_dropped(packet, "Buffer overflow at source", self.current_time)
            self.protocol.on_packet_dropped(packet, packet.source_id, "Source buffer overflow", self.current_time)
        else:
            # If source transmitter is idle, trigger transmission immediately
            if self.node_transmitter_busy_until[packet.source_id] <= self.current_time:
                self.schedule_event(self.current_time, EVENT_NODE_SERVICE, packet.source_id)

        # Schedule next packet generation
        next_dt = self.traffic_gen.sample_interarrival_time(self.current_time)
        self.schedule_event(self.current_time + next_dt, EVENT_PACKET_GENERATE, None)

    def _handle_node_service(self, node_id: int):
        """Node pops front packet from FIFO queue and forwards along chosen link."""
        node = self.network.nodes[node_id]
        if not node.packet_queue:
            return

        packet = node.peek_packet()
        if packet is None:
            return

        # Use protocol to select next hop
        next_hop = self.protocol.select_next_hop(
            current_node_id=node_id,
            destination_id=packet.destination_id,
            packet=packet,
            current_time=self.current_time
        )

        if next_hop is None:
            # No path available! Drop packet
            popped = node.dequeue_packet(self.current_time)
            if popped:
                self.metrics.record_packet_dropped(popped, "No route to destination", self.current_time)
                self.protocol.on_packet_dropped(popped, node_id, "No route", self.current_time)
            # Schedule service for next queued packet if any
            if node.packet_queue:
                self.schedule_event(self.current_time, EVENT_NODE_SERVICE, node_id)
            return

        link = self.network.get_link(node_id, next_hop)
        if not link or not link.is_up:
            # Route chosen is unavailable
            popped = node.dequeue_packet(self.current_time)
            if popped:
                self.metrics.record_packet_dropped(popped, "Link down", self.current_time)
                self.protocol.on_packet_dropped(popped, node_id, "Link down", self.current_time)
            if node.packet_queue:
                self.schedule_event(self.current_time, EVENT_NODE_SERVICE, node_id)
            return

        # Dequeue packet from node buffer
        popped = node.dequeue_packet(self.current_time)
        if popped is None:
            return

        # Calculate transmission and propagation times
        tx_delay = link.transmission_delay
        prop_delay = link.propagation_delay
        total_delay = tx_delay + prop_delay

        # Mark node transmitter as busy
        self.node_transmitter_busy_until[node_id] = self.current_time + tx_delay

        # Protocol hook for RL learning update
        queue_delay = max(0.0, self.current_time - popped.in_queue_since)
        self.protocol.on_packet_forwarded(
            from_node=node_id,
            to_node=next_hop,
            destination=popped.destination_id,
            queue_delay=queue_delay,
            link_delay=total_delay,
            current_time=self.current_time
        )

        link.packets_transmitted += 1
        node.total_forwarded += 1

        # Track in-flight transmission for GUI
        arrival_time = self.current_time + total_delay
        self.in_flight_transmissions[popped.packet_id] = {
            "packet": popped,
            "src": node_id,
            "dst": next_hop,
            "start_time": self.current_time,
            "arrive_time": arrival_time
        }

        # Check for link packet drop (channel error / noise)
        if link.should_drop_packet():
            link.packets_dropped += 1
            self.metrics.record_packet_dropped(popped, "Link physical transmission error", arrival_time)
        else:
            # Schedule arrival at next hop
            self.schedule_event(
                arrival_time,
                EVENT_PACKET_ARRIVE,
                (popped, node_id, next_hop)
            )

        # If more packets remain in queue, schedule next transmission once transmitter frees up
        if node.packet_queue:
            self.schedule_event(
                self.current_time + tx_delay,
                EVENT_NODE_SERVICE,
                node_id
            )

    def _handle_packet_arrive(self, arrival_data: Tuple[Packet, int, int]):
        """Packet arrives at intermediate node or final destination."""
        packet, from_node, to_node = arrival_data
        packet.record_hop(to_node, self.current_time)

        # Check TTL
        if packet.is_expired():
            self.metrics.record_packet_dropped(packet, "TTL exceeded", self.current_time)
            self.protocol.on_packet_dropped(packet, to_node, "TTL exceeded", self.current_time)
            return

        # Reached destination!
        if to_node == packet.destination_id:
            dest_node = self.network.nodes[to_node]
            dest_node.total_delivered += 1
            self.metrics.record_packet_delivered(packet, self.current_time)
            self.protocol.on_packet_delivered(packet, self.current_time)
            return

        # Intermediate router node: enqueue in buffer
        target_node = self.network.nodes[to_node]
        buffered = target_node.enqueue_packet(packet, self.current_time)

        if not buffered:
            self.metrics.record_packet_dropped(packet, f"Buffer overflow at Node {to_node}", self.current_time)
            self.protocol.on_packet_dropped(packet, to_node, "Buffer overflow", self.current_time)
        else:
            # If transmitter is idle, trigger transmission
            if self.node_transmitter_busy_until[to_node] <= self.current_time:
                self.schedule_event(self.current_time, EVENT_NODE_SERVICE, to_node)

    def _handle_link_fail(self, link_pair: Tuple[int, int]):
        u, v = link_pair
        self.network.kill_link(u, v, self.current_time)
        self.protocol.on_link_state_changed(u, v, is_up=False, current_time=self.current_time)

    def _handle_link_restore(self, link_pair: Tuple[int, int]):
        u, v = link_pair
        self.network.restore_link(u, v, self.current_time)
        self.protocol.on_link_state_changed(u, v, is_up=True, current_time=self.current_time)

    def _handle_snapshot(self):
        self.metrics.record_periodic_snapshot(self.current_time)
        self.schedule_event(self.current_time + 1.0, EVENT_SNAPSHOT, None)

    def run(self) -> Dict[str, Any]:
        """Run the simulation to completion."""
        self.initialize()
        while self.step():
            pass
        return self.metrics.get_summary(self.current_time)

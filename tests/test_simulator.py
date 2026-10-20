"""
Unit tests for Simulation Engine, Traffic Generator, and Metrics.
"""

import unittest
from core.network import Network
from protocols.q_routing import QRoutingProtocol
from protocols.dijkstra_routing import DijkstraRoutingProtocol
from simulator.event_engine import SimulationEngine
from simulator.metrics_collector import MetricsCollector
from simulator.traffic_generator import TrafficGenerator
from config.simulation_config import SimulationConfig, TrafficConfig, RLConfig


class TestSimulationEngine(unittest.TestCase):

    def setUp(self):
        self.net = Network()
        self.net.add_link(0, 1, bandwidth=20.0, propagation_delay=0.02)
        self.net.add_link(1, 2, bandwidth=20.0, propagation_delay=0.02)
        self.net.add_link(0, 2, bandwidth=20.0, propagation_delay=0.05)

    def test_traffic_generator(self):
        cfg = TrafficConfig(packet_rate=10.0, traffic_pattern="uniform")
        gen = TrafficGenerator(node_ids=[0, 1, 2], config=cfg)
        
        pkt = gen.create_packet(current_time=1.0)
        self.assertIn(pkt.source_id, [0, 1, 2])
        self.assertIn(pkt.destination_id, [0, 1, 2])
        self.assertNotEqual(pkt.source_id, pkt.destination_id)

    def test_simulation_run_dijkstra(self):
        proto = DijkstraRoutingProtocol()
        cfg = SimulationConfig(duration=10.0, traffic=TrafficConfig(packet_rate=5.0))
        engine = SimulationEngine(network=self.net, protocol=proto, config=cfg)

        summary = engine.run()
        self.assertGreater(summary["packets_generated"], 0)
        self.assertGreater(summary["packets_delivered"], 0)
        self.assertGreater(summary["average_latency_s"], 0.0)
        self.assertEqual(summary["drop_rate_pct"], 0.0)

    def test_simulation_run_q_routing(self):
        proto = QRoutingProtocol(config=RLConfig(learning_rate=0.2, epsilon=0.1))
        cfg = SimulationConfig(duration=10.0, traffic=TrafficConfig(packet_rate=5.0))
        engine = SimulationEngine(network=self.net, protocol=proto, config=cfg)

        summary = engine.run()
        self.assertGreater(summary["packets_generated"], 0)
        self.assertGreater(summary["packets_delivered"], 0)
        self.assertGreaterEqual(proto.total_updates, 1)

    def test_link_failure_resilience(self):
        proto = QRoutingProtocol(config=RLConfig(learning_rate=0.3, epsilon=0.1))
        cfg = SimulationConfig(duration=15.0, traffic=TrafficConfig(packet_rate=5.0))
        engine = SimulationEngine(network=self.net, protocol=proto, config=cfg)

        # Cut link 0-1 at t=3.0s, restore at t=10.0s
        engine.schedule_link_failure(0, 1, fail_time=3.0, restore_time=10.0)
        summary = engine.run()

        self.assertGreater(summary["packets_delivered"], 0)
        # Network remained connected via alternate link 0-2


if __name__ == "__main__":
    unittest.main()


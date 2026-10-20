"""
Unit tests for Routing Protocols (Q-Routing, Dual-Q, Dijkstra, Congestion-Aware, Random).
"""

import unittest
from core.network import Network
from core.packet import Packet
from config.simulation_config import RLConfig
from protocols.dijkstra_routing import DijkstraRoutingProtocol
from protocols.random_routing import RandomRoutingProtocol
from protocols.congestion_aware import CongestionAwareRoutingProtocol
from protocols.q_routing import QRoutingProtocol
from protocols.dual_q_routing import DualQRoutingProtocol


class TestRoutingProtocols(unittest.TestCase):

    def setUp(self):
        # 3-node linear network: 0 <-> 1 <-> 2
        self.net = Network()
        self.net.add_link(0, 1, bandwidth=10.0, propagation_delay=0.05)
        self.net.add_link(1, 2, bandwidth=10.0, propagation_delay=0.05)

    def test_dijkstra_routing(self):
        proto = DijkstraRoutingProtocol(dynamic_reroute=False)
        proto.initialize(self.net)

        pkt = Packet(packet_id=1, source_id=0, destination_id=2, creation_time=0.0)
        next_hop = proto.select_next_hop(current_node_id=0, destination_id=2, packet=pkt, current_time=0.0)
        self.assertEqual(next_hop, 1)

        pkt.record_hop(1, current_time=0.1)
        next_hop_2 = proto.select_next_hop(current_node_id=1, destination_id=2, packet=pkt, current_time=0.1)
        self.assertEqual(next_hop_2, 2)

    def test_q_routing_learning_update(self):
        rl_conf = RLConfig(learning_rate=0.5, epsilon=0.0)  # Pure greedy
        proto = QRoutingProtocol(config=rl_conf)
        proto.initialize(self.net)

        # Initial Q-value for (dst=2, via neighbor=1)
        initial_q = proto.get_q_value(node_id=0, dst=2, neighbor=1)
        self.assertGreater(initial_q, 0.0)

        # Simulate forwarding packet from 0 to 1 with known queue & link delay
        proto.on_packet_forwarded(
            from_node=0,
            to_node=1,
            destination=2,
            queue_delay=0.10,
            link_delay=0.15,
            current_time=0.0
        )

        updated_q = proto.get_q_value(node_id=0, dst=2, neighbor=1)
        # Verify update occurred and changed Q-value towards experienced cost
        self.assertNotEqual(initial_q, updated_q)

    def test_dual_q_routing_bidirectional_update(self):
        rl_conf = RLConfig(learning_rate=0.5, epsilon=0.0)
        proto = DualQRoutingProtocol(config=rl_conf)
        proto.initialize(self.net)

        # Forward packet from 0 to 1 with destination 2
        proto.on_packet_forwarded(
            from_node=0,
            to_node=1,
            destination=2,
            queue_delay=0.05,
            link_delay=0.10,
            current_time=0.0
        )

        # In Dual Q-routing, Node 1 also updated its backward knowledge towards Node 0
        back_q = proto.get_q_value(node_id=1, dst=0, neighbor=0)
        back_conf = proto.get_confidence(node_id=1, dst=0, neighbor=0)
        self.assertAlmostEqual(back_q, 0.15)
        self.assertEqual(back_conf, 1.0)

    def test_congestion_aware_routing(self):
        # Create diamond network
        net = Network()
        net.add_link(0, 1, bandwidth=10.0, propagation_delay=0.05)
        net.add_link(1, 3, bandwidth=10.0, propagation_delay=0.05)
        net.add_link(0, 2, bandwidth=10.0, propagation_delay=0.05)
        net.add_link(2, 3, bandwidth=10.0, propagation_delay=0.05)

        # Fill Node 1 queue with dummy packets to simulate severe congestion
        for i in range(15):
            dummy = Packet(packet_id=100 + i, source_id=1, destination_id=3, creation_time=0.0)
            net.nodes[1].enqueue_packet(dummy, current_time=0.0)

        proto = CongestionAwareRoutingProtocol()
        proto.initialize(net)

        pkt = Packet(packet_id=1, source_id=0, destination_id=3, creation_time=0.0)
        # Should intelligently steer packet to Node 2 rather than congested Node 1
        chosen_hop = proto.select_next_hop(current_node_id=0, destination_id=3, packet=pkt, current_time=0.0)
        self.assertEqual(chosen_hop, 2)


if __name__ == "__main__":
    unittest.main()


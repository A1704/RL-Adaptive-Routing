"""
Unit tests for Core Network components (Node, Link, Network graph, Dijkstra).
"""

import unittest
from core.packet import Packet
from core.link import Link
from core.node import Node
from core.network import Network


class TestNetworkCore(unittest.TestCase):

    def test_packet_creation_and_hop(self):
        pkt = Packet(packet_id=1, source_id=0, destination_id=3, creation_time=1.0)
        self.assertEqual(pkt.current_node_id, 0)
        self.assertEqual(pkt.hop_count, 0)
        self.assertEqual(pkt.path_history, [0])

        pkt.record_hop(1, current_time=1.05)
        self.assertEqual(pkt.current_node_id, 1)
        self.assertEqual(pkt.hop_count, 1)
        self.assertEqual(pkt.path_history, [0, 1])
        self.assertEqual(pkt.ttl, 63)

    def test_link_delays_and_cut(self):
        link = Link(node_a=0, node_b=1, bandwidth=10.0, propagation_delay=0.05)
        self.assertTrue(link.is_up)
        self.assertAlmostEqual(link.transmission_delay, 0.1)
        self.assertAlmostEqual(link.total_link_delay, 0.15)
        self.assertEqual(link.other_end(0), 1)
        self.assertEqual(link.other_end(1), 0)

        link.set_down()
        self.assertFalse(link.is_up)
        self.assertTrue(link.should_drop_packet())

        link.set_up()
        self.assertTrue(link.is_up)

    def test_node_buffer_and_overflow(self):
        node = Node(node_id=0, buffer_capacity=2)
        p1 = Packet(packet_id=1, source_id=0, destination_id=2, creation_time=0.0)
        p2 = Packet(packet_id=2, source_id=0, destination_id=2, creation_time=0.1)
        p3 = Packet(packet_id=3, source_id=0, destination_id=2, creation_time=0.2)

        # Enqueue p1 and p2 -> succeed
        self.assertTrue(node.enqueue_packet(p1, current_time=0.0))
        self.assertTrue(node.enqueue_packet(p2, current_time=0.1))
        self.assertEqual(node.current_queue_size, 2)

        # Enqueue p3 -> buffer overflow drop
        self.assertFalse(node.enqueue_packet(p3, current_time=0.2))
        self.assertTrue(p3.dropped)
        self.assertEqual(node.total_buffer_drops, 1)

        # Dequeue
        popped = node.dequeue_packet(current_time=0.5)
        self.assertEqual(popped.packet_id, 1)
        self.assertAlmostEqual(popped.total_queue_delay, 0.5)
        self.assertEqual(node.current_queue_size, 1)

    def test_network_dijkstra_and_connectivity(self):
        net = Network()
        net.add_link(0, 1, bandwidth=10.0, propagation_delay=0.05)
        net.add_link(1, 2, bandwidth=10.0, propagation_delay=0.05)
        net.add_link(0, 2, bandwidth=10.0, propagation_delay=0.20)  # Slower direct link

        self.assertTrue(net.is_connected())

        # Optimal path from 0 to 2 should be via 1 (0.15s + 0.15s = 0.30s vs direct 0.30s)
        next_hop = net.get_shortest_path_next_hop(0, 2, cost_metric="delay")
        self.assertIn(next_hop, [1, 2])

        # Cut link 0-1
        net.kill_link(0, 1)
        self.assertNotIn(1, net.get_active_neighbors(0))
        
        # Path must now go directly 0 -> 2
        next_hop_after_cut = net.get_shortest_path_next_hop(0, 2, cost_metric="delay")
        self.assertEqual(next_hop_after_cut, 2)


if __name__ == "__main__":
    unittest.main()


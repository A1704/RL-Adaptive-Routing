"""
Live Console Demo for Reinforcement Learning Adaptive Routing.
Runs in your terminal with animated real-time progress and live Q-table updates.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.simulation_config import SimulationConfig, RLConfig, TrafficConfig
from core.network import Network
from topologies.topology_factory import TopologyFactory
from protocols.q_routing import QRoutingProtocol
from simulator.event_engine import SimulationEngine


def run_live_console():
    print("\n" + "=" * 70)
    print("  LIVE TERMINAL RUN: Multi-Agent Q-Routing Protocol")
    print("=" * 70)

    net = TopologyFactory.create_nsfnet_topology()
    proto = QRoutingProtocol(config=RLConfig(learning_rate=0.25, epsilon=0.15))
    cfg = SimulationConfig(duration=40.0, traffic=TrafficConfig(packet_rate=12.0))
    engine = SimulationEngine(network=net, protocol=proto, config=cfg)
    engine.initialize()

    # Schedule a link cut at t=12s
    engine.schedule_link_failure(0, 1, fail_time=12.0, restore_time=25.0)

    print("[*] Simulating NSFNet (14 nodes, 21 links) with Q-Routing agents...")
    print("[*] Scheduled Event: Link 0 <-> 1 will FAIL at t=12.0s, RESTORE at t=25.0s\n")

    step_count = 0
    last_print_time = 0.0

    while engine.step():
        step_count += 1
        curr_t = engine.current_time

        # Print live status update every 1.5 simulated seconds
        if curr_t - last_print_time >= 1.5:
            last_print_time = curr_t
            m = engine.metrics
            
            # Check link status
            l01 = net.get_link(0, 1)
            status_l01 = "UP" if (l01 and l01.is_up) else "DOWN (CUT!)"

            # Node 0 Q-values to destination 1 via neighbors
            q_via = {}
            for nbr in net.nodes[0].neighbors:
                q_via[nbr] = round(proto.get_q_value(0, 1, nbr), 3)

            pdr = m.get_delivery_ratio() * 100.0
            avg_lat = m.get_average_latency()

            print(f"[t = {curr_t:5.1f}s] Pkts Sent: {m.total_generated:4d} | Delivered: {m.total_delivered:4d} | "
                  f"PDR: {pdr:5.1f}% | Avg Latency: {avg_lat:.3f}s | Link(0-1): {status_l01:<10} | Q(0->1 via nbrs): {q_via}")

            # Small sleep to allow visual observation in terminal
            time.sleep(0.12)

    print("\n" + "=" * 70)
    print("  SIMULATION COMPLETE!")
    summary = engine.metrics.get_summary(engine.current_time)
    print(f"  Total Generated : {summary['packets_generated']}")
    print(f"  Total Delivered : {summary['packets_delivered']}")
    print(f"  Total Dropped   : {summary['packets_dropped']}")
    print(f"  Delivery Ratio  : {summary['packet_delivery_ratio_pct']}%")
    print(f"  Average Latency : {summary['average_latency_s']:.4f} s")
    print(f"  Total RL Updates: {proto.total_updates}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_live_console()


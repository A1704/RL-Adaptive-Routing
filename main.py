"""
Unified CLI Entry Point for Reinforcement Learning based Adaptive Routing Protocol.
Supports single-run simulations, multi-protocol benchmarks, link failure resilience tests,
and launching the interactive visualizer.
"""

import argparse
import sys
import os
import json
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.simulation_config import SimulationConfig, RLConfig, TrafficConfig
from core.network import Network
from topologies.topology_factory import TopologyFactory
from protocols.q_routing import QRoutingProtocol
from protocols.dual_q_routing import DualQRoutingProtocol
from protocols.dijkstra_routing import DijkstraRoutingProtocol
from protocols.congestion_aware import CongestionAwareRoutingProtocol
from protocols.random_routing import RandomRoutingProtocol
from simulator.event_engine import SimulationEngine
from visualizer.html_dashboard import HTMLDashboardGenerator


def print_banner():
    banner = r"""
  ========================================================================
   REINFORCEMENT LEARNING BASED ADAPTIVE ROUTING PROTOCOL SIMULATOR
   Multi-Agent Q-Routing vs. Dynamic & Static Baseline Protocols
  ========================================================================
    """
    print(banner)


def format_table(rows, headers):
    """Format and print a terminal ASCII table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header_row = "| " + " | ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers)) + " |"

    print(sep)
    print(header_row)
    print(sep)
    for row in rows:
        r_str = "| " + " | ".join(f"{str(v):<{widths[i]}}" for i, v in enumerate(row)) + " |"
        print(r_str)
    print(sep)


def run_benchmark(args):
    """Run full comparative benchmark across all protocols."""
    print_banner()
    print(f"[*] Initializing Benchmark Suite")
    print(f"    - Topology: {args.topology}")
    print(f"    - Duration: {args.duration}s per protocol")
    print(f"    - Traffic Pattern: {args.traffic}")
    print(f"    - Packet Injection Rate: {args.rate} pkts/s\n")

    protocols = [
        ("Dual-Q-Routing", DualQRoutingProtocol(config=RLConfig(learning_rate=args.lr, epsilon=args.epsilon))),
        ("Q-Routing", QRoutingProtocol(config=RLConfig(learning_rate=args.lr, epsilon=args.epsilon))),
        ("Congestion-Aware", CongestionAwareRoutingProtocol()),
        ("Dijkstra-SPF", DijkstraRoutingProtocol(dynamic_reroute=False)),
        ("Random-Walk", RandomRoutingProtocol())
    ]

    benchmark_results = {}
    table_rows = []

    for name, proto in protocols:
        print(f"[*] Running protocol: {name:<18} ...", end="", flush=True)
        start_wall = time.time()

        # Build fresh network topology
        net = TopologyFactory.get_topology(args.topology)
        
        sim_config = SimulationConfig(
            duration=args.duration,
            seed=args.seed,
            rl=RLConfig(learning_rate=args.lr, epsilon=args.epsilon),
            traffic=TrafficConfig(packet_rate=args.rate, traffic_pattern=args.traffic)
        )

        engine = SimulationEngine(network=net, protocol=proto, config=sim_config)
        summary = engine.run()
        elapsed_wall = time.time() - start_wall

        benchmark_results[name] = {
            "summary": summary,
            "wall_time_s": round(elapsed_wall, 2),
            "history_latency": engine.metrics.history_avg_latency,
            "history_pdr": engine.metrics.history_pdr,
            "history_throughput": engine.metrics.history_throughput
        }

        print(f" Done ({elapsed_wall:.2f}s wall time)")

        table_rows.append([
            name,
            f"{summary['average_latency_s']:.4f}",
            f"{summary['packet_delivery_ratio_pct']:.2f}%",
            f"{summary['throughput_pps']:.2f}",
            summary['packets_dropped'],
            f"{summary['average_hops']:.2f}"
        ])

    print("\n[+] Benchmark Results:")
    headers = ["Protocol", "Avg Latency (s)", "PDR (%)", "Throughput (pps)", "Drops", "Avg Hops"]
    format_table(table_rows, headers)

    # Save JSON results
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)
    print(f"\n[+] Saved JSON results to: {json_path}")

    # Generate HTML Dashboard
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "simulation_report.html")
    HTMLDashboardGenerator.generate_report(
        benchmark_results=benchmark_results,
        topology_name=args.topology,
        config_dict=sim_config.to_dict(),
        output_file=html_path
    )
    print(f"[+] Generated Interactive HTML Dashboard: {html_path}")
    print("    (Open this file in any web browser to view comparative charts and graphs!)")


def run_failure_test(args):
    """Demonstrate resilience under dynamic link cuts."""
    print_banner()
    print("[*] Link Failure & Resilience Test")
    print(f"    - Topology: {args.topology}")
    print(f"    - Link to cut: Node {args.cut_u} <-> Node {args.cut_v} at t = {args.cut_time}s\n")

    protocols = [
        ("Dual-Q-Routing", DualQRoutingProtocol(config=RLConfig(learning_rate=args.lr))),
        ("Q-Routing", QRoutingProtocol(config=RLConfig(learning_rate=args.lr))),
        ("Dijkstra-SPF (Static)", DijkstraRoutingProtocol(dynamic_reroute=False)),
    ]

    table_rows = []

    for name, proto in protocols:
        net = TopologyFactory.get_topology(args.topology)
        sim_config = SimulationConfig(
            duration=args.duration,
            seed=args.seed,
            traffic=TrafficConfig(packet_rate=args.rate, traffic_pattern=args.traffic)
        )

        engine = SimulationEngine(network=net, protocol=proto, config=sim_config)
        # Schedule the link failure
        engine.schedule_link_failure(args.cut_u, args.cut_v, fail_time=args.cut_time, restore_time=args.restore_time)

        print(f"[*] Simulating {name} with link cut at t={args.cut_time}s...")
        summary = engine.run()

        table_rows.append([
            name,
            f"{summary['average_latency_s']:.4f}",
            f"{summary['packet_delivery_ratio_pct']:.2f}%",
            f"{summary['throughput_pps']:.2f}",
            summary['packets_dropped'],
            summary['drop_reasons']
        ])

    print("\n[+] Link Cut Resilience Comparison:")
    headers = ["Protocol", "Avg Latency (s)", "PDR (%)", "Throughput (pps)", "Drops", "Loss Breakdown"]
    format_table(table_rows, headers)


def run_single_simulation(args):
    """Run a single protocol simulation with detailed output."""
    print_banner()
    print(f"[*] Single Run: {args.protocol} on {args.topology}")

    net = TopologyFactory.get_topology(args.topology)
    
    if args.protocol.lower() in ["qrouting", "q-routing"]:
        proto = QRoutingProtocol(config=RLConfig(learning_rate=args.lr, epsilon=args.epsilon))
    elif args.protocol.lower() in ["dualq", "dual-q-routing"]:
        proto = DualQRoutingProtocol(config=RLConfig(learning_rate=args.lr, epsilon=args.epsilon))
    elif args.protocol.lower() in ["dijkstra", "ospf", "spf"]:
        proto = DijkstraRoutingProtocol()
    elif args.protocol.lower() in ["congestion", "congestion-aware"]:
        proto = CongestionAwareRoutingProtocol()
    else:
        proto = RandomRoutingProtocol()

    sim_config = SimulationConfig(
        duration=args.duration,
        seed=args.seed,
        traffic=TrafficConfig(packet_rate=args.rate, traffic_pattern=args.traffic)
    )

    engine = SimulationEngine(network=net, protocol=proto, config=sim_config)
    summary = engine.run()

    print("\n[+] Simulation Completed Successfully!")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Reinforcement Learning based Adaptive Routing Protocol Simulator")
    parser.add_argument("--gui", action="store_true", help="Launch the interactive desktop Tkinter visualizer")
    parser.add_argument("--benchmark", action="store_true", help="Run multi-protocol comparative benchmark")
    parser.add_argument("--failure-test", action="store_true", help="Run link failure and recovery resilience test")
    parser.add_argument("--protocol", type=str, default="Q-Routing", help="Protocol: Q-Routing, Dual-Q-Routing, Dijkstra-SPF, Congestion-Aware, Random-Walk")
    parser.add_argument("--topology", type=str, default="nsfnet", help="Topology: nsfnet, grid, ring, bottleneck")
    parser.add_argument("--duration", type=float, default=60.0, help="Simulation time in seconds")
    parser.add_argument("--rate", type=float, default=15.0, help="Packet generation rate (packets/s)")
    parser.add_argument("--traffic", type=str, default="uniform", help="Traffic pattern: uniform, bursty, hotspot")
    parser.add_argument("--lr", type=float, default=0.15, help="RL learning rate (alpha)")
    parser.add_argument("--epsilon", type=float, default=0.15, help="RL exploration factor (epsilon)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--cut-u", type=int, default=0, help="Node U for link cut test")
    parser.add_argument("--cut-v", type=int, default=1, help="Node V for link cut test")
    parser.add_argument("--cut-time", type=float, default=20.0, help="Time in seconds to cut link")
    parser.add_argument("--restore-time", type=float, default=45.0, help="Time in seconds to restore link (or 0 for never)")

    args = parser.parse_args()

    if args.gui:
        from visualizer.gui_app import launch_gui
        launch_gui()
    elif args.benchmark:
        run_benchmark(args)
    elif args.failure_test:
        run_failure_test(args)
    else:
        # Default action if no flag specified: run benchmark
        run_benchmark(args)


if __name__ == "__main__":
    main()


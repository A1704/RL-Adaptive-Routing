# Reinforcement Learning based Adaptive Routing Protocol

An end-to-end, modular, and production-grade implementation of **Multi-Agent Reinforcement Learning (MARL) for Adaptive Packet Routing** in dynamic communication networks.

This project simulates realistic packet-switched networks under fluctuating traffic loads and dynamic network disruptions (link failures and traffic surges). It compares **Q-Routing (Boyan & Littman, 1994)** and **Dual Q-Routing** against traditional protocols (**Static Dijkstra Shortest Path / OSPF**, **Congestion-Aware Routing**, and **Random Walk**) across latency, throughput, packet delivery ratio (PDR), and buffer loss metrics.

---

## 🌟 Key Features

1. **Multi-Agent Q-Routing (MARL)**:
   - Each router node acts as an autonomous learning agent maintaining its local Q-table.
   - Learns optimal forwarding policies dynamically by observing local queue waiting times and neighbor feedback.
   - $\epsilon$-greedy and uncertainty-guided exploration to bypass congested bottlenecks.

2. **Dual Q-Routing (CQ-Routing)**:
   - Extends Q-routing with **bidirectional credit assignment**: updates forward estimates on transmission and backward estimates on reverse paths.
   - Incorporates route confidence metrics $C(d, y) \in [0, 1]$ that decay over idle periods, accelerating adaptation to link cuts.

3. **Traditional Baseline Comparisons**:
   - **Static Shortest Path First (Dijkstra / OSPF)**: Computes routes based solely on static link propagation delays.
   - **Congestion-Aware Dynamic Routing**: Heuristic baseline balancing hop distance with neighbor buffer occupancy.
   - **Random Walk**: Stochastic routing baseline.

4. **Realistic Discrete-Event Simulator (DES)**:
   - Priority-queue event scheduling (`heapq`).
   - Finite router FIFO queues with configurable buffer limits and buffer overflow drops.
   - Poisson packet arrival processes, periodic burst spikes, and hotspot server traffic.
   - Dynamic link failure and recovery scheduling.

5. **Built-in Interactive Desktop GUI (Tkinter)**:
   - Live visual network canvas with color-coded node buffer gauges (Green $\to$ Yellow $\to$ Red).
   - Real-time animated in-flight packet dots traveling along links.
   - Click-to-cut or click-to-restore links in real time to observe live route recovery.
   - Live latency sparkline chart and node/link inspector.

6. **Interactive HTML5 Reporting Dashboard**:
   - Automatically exports standalone interactive HTML dashboard (`simulation_report.html`) with native Canvas comparative bar charts, metrics tables, and JSON data.

7. **Zero C-Dependency Architecture**:
   - 100% pure Python standard library (`math`, `random`, `heapq`, `tkinter`, `json`, `dataclasses`, `unittest`).
   - Completely immune to Windows Application Control DLL / C-extension loading errors.

---

## 📐 Mathematical Formulation

### 1. The Adaptive Routing Problem
Let a network be represented by a graph $G = (V, E)$, where $V$ is the set of router nodes and $E$ is the set of communication links. Each node $x \in V$ maintains a finite FIFO packet buffer of capacity $B_x$. When a packet arrives destined for $d \in V$, router $x$ must select an active neighbor $y \in \mathcal{N}(x)$ to forward the packet.

### 2. Standard Q-Routing (Boyan & Littman, 1994)
In Q-Routing, node $x$ maintains a Q-value $Q_x(d, y)$ representing the **estimated delivery latency** (or cost) to route a packet to destination $d$ via neighbor $y$:

$$Q_x(d, y) \approx q_x + s_{xy} + \min_{z \in \mathcal{N}(y)} Q_y(d, z)$$

where:
- $q_x$: Waiting time experienced by the packet in node $x$'s queue buffer.
- $s_{xy}$: Transmission delay ($1/\text{bandwidth}$) plus propagation delay across link $(x, y)$.
- $V_y(d) = \min_{z \in \mathcal{N}(y)} Q_y(d, z)$: Neighbor $y$'s minimum estimated time to reach destination $d$ ($V_y(d) = 0$ if $y = d$).

#### Bellman Update Equation:
When node $x$ sends a packet to $y$, neighbor $y$ sends back its current estimate $V_y(d)$ (via acknowledgment or feedback). Node $x$ then updates:

$$Q_x(d, y) \leftarrow Q_x(d, y) + \alpha \left( q_x + s_{xy} + V_y(d) - Q_x(d, y) \right)$$

where $\alpha \in (0, 1]$ is the learning rate.

#### Exploration Policy:
To discover alternative uncongested routes, agents follow an $\epsilon$-greedy policy:
$$\pi_x(d) = \begin{cases} 
\text{random neighbor from } \mathcal{N}(x) & \text{with probability } \epsilon \\
\arg\min_{y \in \mathcal{N}(x)} Q_x(d, y) & \text{with probability } 1 - \epsilon 
\end{cases}$$

$\epsilon$ decays over time towards $\epsilon_{\min}$.

### 3. Dual Q-Routing (CQ-Routing)
Dual Q-Routing updates Q-values in both directions:
1. **Forward Update**: Node $x$ updates $Q_x(d, y)$ using the estimate from $y$.
2. **Backward Update**: Node $y$ learns the route back to source $s$ via $x$ using elapsed hop delay.
3. **Confidence Tracking**: Each Q-value has a confidence score $C_x(d, y) \in [0, 1]$. When a route sits idle, $C \leftarrow C \times \gamma_c$. When fresh packets traverse the route, confidence is boosted. Exploration is guided towards lower-confidence paths to ensure fresh route information during topology shifts.

---

## 📂 Project Structure

```
RL_Adaptive_Routing/
├── config/
│   ├── __init__.py
│   └── simulation_config.py      # Dataclasses for network, traffic, and RL parameters
├── core/
│   ├── __init__.py
│   ├── packet.py                 # Packet dataclass (ID, hops, latency, drop tracking)
│   ├── link.py                   # Bidirectional link with bandwidth, propagation delay, error rate
│   ├── node.py                   # Router node with finite FIFO buffer and drop counters
│   └── network.py                # Graph manager, link cut/restore, pure Python Dijkstra
├── protocols/
│   ├── __init__.py
│   ├── base_routing.py           # Abstract Base Class for routing protocols
│   ├── dijkstra_routing.py       # Static Shortest Path First (OSPF baseline)
│   ├── random_routing.py         # Stochastic random walk baseline
│   ├── congestion_aware.py       # Heuristic least-loaded dynamic baseline
│   ├── q_routing.py              # Classic Multi-Agent Q-Routing (Boyan & Littman)
│   └── dual_q_routing.py         # Dual Reinforcement Routing with confidence metrics
├── simulator/
│   ├── __init__.py
│   ├── event_engine.py           # Priority-queue discrete event simulation (DES) engine
│   ├── traffic_generator.py      # Poisson, bursty, and hotspot traffic generators
│   └── metrics_collector.py      # Latency, throughput, PDR, and drop analytics
├── topologies/
│   ├── __init__.py
│   └── topology_factory.py       # 6x6 Grid, NSFNet (14 nodes), Ring-Chord, Bottleneck
├── visualizer/
│   ├── __init__.py
│   ├── gui_app.py                # Desktop GUI (Tkinter) with live animation & link cut toggles
│   └── html_dashboard.py         # Standalone HTML5/Canvas interactive report generator
├── tests/
│   ├── __init__.py
│   ├── test_network.py           # Unit tests for core network components & Dijkstra
│   ├── test_protocols.py         # Unit tests for Q-learning updates & baselines
│   └── test_simulator.py         # Unit tests for event engine & link cuts
├── main.py                       # Unified CLI runner (benchmark, failure-test, simulate, gui)
├── run_gui.py                    # One-click desktop GUI launcher
├── requirements.txt              # Standard requirements (notes standard library portability)
└── README.md                     # Comprehensive documentation and project report
```

---

## 🚀 Quick Start Guide

### 1. Launch the Desktop GUI
To open the real-time visualizer with animated packet flows:
```bash
python run_gui.py
```
*(or `python main.py --gui`)*

**GUI Features**:
- **Play/Pause/Step**: Control simulation playback in real time.
- **Speed Slider**: Adjust simulation speed from 0.2x to 5.0x.
- **Protocol & Topology Selectors**: Switch between Q-Routing, Dual-Q, Dijkstra, and NSFNet or 6x6 Grid on the fly.
- **Click to Cut/Restore**: Click on any link in the canvas and press **Toggle Selected Link** to simulate a physical wire cut.
- **Node Queue Gauges**: Watch nodes turn from green (empty) to yellow to red (congested) as queues fill.

---

### 2. Run Comparative Benchmark
Run a head-to-head benchmark comparing all 5 protocols:
```bash
python main.py --benchmark --topology nsfnet --duration 30.0 --rate 15.0
```

**Output**:
- Displays a formatted comparative ASCII table in your terminal.
- Generates `benchmark_results.json`.
- Exports `simulation_report.html` (open in Chrome/Edge/Firefox to view comparative bar charts).

---

### 3. Run Dynamic Link Failure Resilience Test
Demonstrate how Q-Routing autonomously routes around a severed link while static Dijkstra fails:
```bash
python main.py --failure-test --topology nsfnet --cut-u 0 --cut-v 1 --cut-time 5.0 --restore-time 15.0
```

---

### 4. Run Single Protocol Simulation
Simulate a specific protocol with custom parameters:
```bash
python main.py --protocol Q-Routing --topology grid --duration 20.0 --rate 10.0 --lr 0.20 --epsilon 0.10
```

---

### 5. Run the Automated Test Suite
Verify all core components, graph algorithms, and RL updates:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 📊 Benchmark Topologies

| Topology | Nodes | Links | Description |
| :--- | :---: | :---: | :--- |
| **NSFNet** | 14 | 21 | Real-world optical backbone topology across the US. |
| **6x6 Grid** | 36 | 60 | Canonical benchmark topology from Boyan & Littman (1994). |
| **Ring-Chord** | 12 | 18 | Ring network with high-speed shortcut chords. |
| **Bottleneck** | 6 | 6 | Diamond topology testing detour routing when a fast link congests. |

---

## 📈 Evaluation Metrics

- **Average Latency (s)**: Mean end-to-end packet transmission and queue waiting time.
- **Packet Delivery Ratio (PDR %)**: Percentage of generated packets successfully delivered to their destination.
- **Throughput (pps)**: Packets delivered per simulated second.
- **Packet Loss / Drops**: Number of packets dropped due to buffer overflows, TTL expiration, or link outages.
- **Average Hop Count**: Mean path length in router hops.

---

## 📜 License
This project is released under the MIT License for educational and research purposes.


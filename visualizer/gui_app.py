"""
Desktop GUI Visualizer for Reinforcement Learning Adaptive Routing.
Built with pure Python Tkinter (zero external dependencies).
Features live network topology animation, node queue gauges, packet flows,
link failure triggers, and dynamic performance charts.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math
import time
from typing import Optional, Dict, Tuple

from core.network import Network
from protocols.q_routing import QRoutingProtocol
from protocols.dual_q_routing import DualQRoutingProtocol
from protocols.dijkstra_routing import DijkstraRoutingProtocol
from protocols.congestion_aware import CongestionAwareRoutingProtocol
from protocols.random_routing import RandomRoutingProtocol
from simulator.event_engine import SimulationEngine
from topologies.topology_factory import TopologyFactory
from config.simulation_config import SimulationConfig


class RoutingVisualizerGUI:
    """Real-time Desktop GUI for observing and interacting with RL Adaptive Routing."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RL Adaptive Routing Protocol - Live Network Simulator")
        self.root.geometry("1200x820")
        self.root.minsize(1000, 700)

        # Simulation state
        self.is_running = False
        self.sim_speed = 1.0  # Multiplier
        self.selected_link_key: Optional[Tuple[int, int]] = None
        self.selected_node_id: Optional[int] = None

        self.config = SimulationConfig(duration=1000.0)
        self.network: Optional[Network] = None
        self.engine: Optional[SimulationEngine] = None
        self.current_protocol_name = "Q-Routing"

        # Theme colors
        self.c_bg = "#0f172a"
        self.c_panel = "#1e293b"
        self.c_border = "#334155"
        self.c_text = "#f8fafc"
        self.c_accent = "#38bdf8"
        self.c_emerald = "#34d399"
        self.c_rose = "#fb7185"
        self.c_amber = "#fbbf24"

        self.root.configure(bg=self.c_bg)

        self._create_layout()
        self.load_simulation(topology_name="nsfnet", protocol_name="Q-Routing")

        # Start animation loop
        self.root.after(30, self._simulation_tick)

    def _create_layout(self):
        """Construct GUI panels: Top Controls, Center Network Canvas, Right Analytics Panel."""
        # --- Top Control Bar ---
        top_bar = tk.Frame(self.root, bg=self.c_panel, padx=12, pady=10, highlightthickness=1, highlightbackground=self.c_border)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        # Protocol dropdown
        tk.Label(top_bar, text="Protocol:", bg=self.c_panel, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.proto_var = tk.StringVar(value="Q-Routing")
        proto_cb = ttk.Combobox(top_bar, textvariable=self.proto_var, values=[
            "Q-Routing", "Dual-Q-Routing", "Congestion-Aware", "Dijkstra-SPF", "Random-Walk"
        ], state="readonly", width=16)
        proto_cb.pack(side=tk.LEFT, padx=(0, 12))
        proto_cb.bind("<<ComboboxSelected>>", self._on_protocol_changed)

        # Topology dropdown
        tk.Label(top_bar, text="Topology:", bg=self.c_panel, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.topo_var = tk.StringVar(value="NSFNet (14 Nodes)")
        topo_cb = ttk.Combobox(top_bar, textvariable=self.topo_var, values=[
            "NSFNet (14 Nodes)", "Grid 6x6 (36 Nodes)", "Bottleneck (6 Nodes)", "Ring-Chord (12 Nodes)"
        ], state="readonly", width=18)
        topo_cb.pack(side=tk.LEFT, padx=(0, 12))
        topo_cb.bind("<<ComboboxSelected>>", self._on_topology_changed)

        # Traffic Pattern
        tk.Label(top_bar, text="Traffic:", bg=self.c_panel, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.traffic_var = tk.StringVar(value="Uniform")
        traffic_cb = ttk.Combobox(top_bar, textvariable=self.traffic_var, values=["Uniform", "Bursty", "Hotspot"], state="readonly", width=10)
        traffic_cb.pack(side=tk.LEFT, padx=(0, 14))
        traffic_cb.bind("<<ComboboxSelected>>", self._on_traffic_changed)

        # Action Buttons
        self.btn_play = tk.Button(top_bar, text="▶ Run", command=self.toggle_play, bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), padx=12, relief=tk.FLAT)
        self.btn_play.pack(side=tk.LEFT, padx=4)

        btn_step = tk.Button(top_bar, text="⏭ Step", command=self.step_simulation, bg="#475569", fg="white", font=("Segoe UI", 9), padx=10, relief=tk.FLAT)
        btn_step.pack(side=tk.LEFT, padx=4)

        btn_reset = tk.Button(top_bar, text="🔄 Reset", command=self.reset_simulation, bg="#475569", fg="white", font=("Segoe UI", 9), padx=10, relief=tk.FLAT)
        btn_reset.pack(side=tk.LEFT, padx=4)

        # Speed Slider
        tk.Label(top_bar, text="Speed:", bg=self.c_panel, fg=self.c_text, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(14, 4))
        self.speed_scale = tk.Scale(top_bar, from_=0.2, to=5.0, resolution=0.2, orient=tk.HORIZONTAL, bg=self.c_panel, fg=self.c_text, highlightthickness=0, length=100)
        self.speed_scale.set(1.0)
        self.speed_scale.pack(side=tk.LEFT, padx=4)

        # Network Disruption Actions
        btn_cut = tk.Button(top_bar, text="⚡ Toggle Selected Link", command=self.toggle_selected_link, bg="#e11d48", fg="white", font=("Segoe UI", 9, "bold"), padx=8, relief=tk.FLAT)
        btn_cut.pack(side=tk.RIGHT, padx=4)

        btn_burst = tk.Button(top_bar, text="💥 Inject Traffic Surge", command=self.inject_traffic_burst, bg="#d97706", fg="white", font=("Segoe UI", 9, "bold"), padx=8, relief=tk.FLAT)
        btn_burst.pack(side=tk.RIGHT, padx=4)

        # --- Main Workspace ---
        main_frame = tk.Frame(self.root, bg=self.c_bg)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Canvas on Left
        self.canvas = tk.Canvas(main_frame, bg="#090d16", highlightthickness=1, highlightbackground=self.c_border)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Sidebar on Right
        side_panel = tk.Frame(main_frame, bg=self.c_panel, width=320, padx=14, pady=14, highlightthickness=1, highlightbackground=self.c_border)
        side_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        side_panel.pack_propagate(False)

        tk.Label(side_panel, text="LIVE METRICS", bg=self.c_panel, fg=self.c_accent, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        # Metrics Labels
        self.lbl_time = self._create_metric_row(side_panel, "Sim Time:", "0.00 s")
        self.lbl_generated = self._create_metric_row(side_panel, "Packets Sent:", "0")
        self.lbl_delivered = self._create_metric_row(side_panel, "Delivered:", "0")
        self.lbl_dropped = self._create_metric_row(side_panel, "Drops / Loss:", "0", val_color=self.c_rose)
        self.lbl_pdr = self._create_metric_row(side_panel, "Delivery Ratio (PDR):", "100.0 %", val_color=self.c_emerald)
        self.lbl_latency = self._create_metric_row(side_panel, "Avg Latency:", "0.000 s", val_color=self.c_accent)
        self.lbl_throughput = self._create_metric_row(side_panel, "Throughput:", "0.00 pps", val_color=self.c_amber)

        # Divider
        tk.Frame(side_panel, bg=self.c_border, height=1).pack(fill=tk.X, pady=14)

        # Real-time Latency Sparkline Chart
        tk.Label(side_panel, text="Latency Trend (Time)", bg=self.c_panel, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self.chart_canvas = tk.Canvas(side_panel, bg="#090d16", height=130, highlightthickness=1, highlightbackground=self.c_border)
        self.chart_canvas.pack(fill=tk.X, pady=(0, 10))

        # Node / Link Inspector Box
        tk.Label(side_panel, text="Selected Element Inspector", bg=self.c_panel, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 4))
        self.txt_inspector = tk.Text(side_panel, bg="#090d16", fg=self.c_accent, font=("Consolas", 8), height=9, wrap=tk.WORD, highlightthickness=1, highlightbackground=self.c_border)
        self.txt_inspector.pack(fill=tk.BOTH, expand=True)
        self.txt_inspector.insert(tk.END, "Click on any Node or Link to inspect live Q-values, buffer queue, and status.")

    def _create_metric_row(self, parent, label_text: str, default_val: str, val_color: str = "#f8fafc") -> tk.Label:
        row = tk.Frame(parent, bg=self.c_panel)
        row.pack(fill=tk.X, pady=3)
        tk.Label(row, text=label_text, bg=self.c_panel, fg="#94a3b8", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        val_lbl = tk.Label(row, text=default_val, bg=self.c_panel, fg=val_color, font=("Segoe UI", 9, "bold"))
        val_lbl.pack(side=tk.RIGHT)
        return val_lbl

    def load_simulation(self, topology_name: str, protocol_name: str):
        """Build network topology, instantiate protocol, and initialize simulation engine."""
        self.is_running = False
        self.btn_play.config(text="▶ Run", bg="#0284c7")

        # 1. Topology
        if "nsf" in topology_name.lower():
            self.network = TopologyFactory.create_nsfnet_topology()
        elif "grid" in topology_name.lower():
            self.network = TopologyFactory.create_grid_topology(rows=6, cols=6)
        elif "ring" in topology_name.lower():
            self.network = TopologyFactory.create_ring_chord_topology()
        else:
            self.network = TopologyFactory.create_bottleneck_topology()

        # 2. Protocol
        self.current_protocol_name = protocol_name
        if protocol_name == "Q-Routing":
            proto = QRoutingProtocol(config=self.config.rl)
        elif protocol_name == "Dual-Q-Routing":
            proto = DualQRoutingProtocol(config=self.config.rl)
        elif protocol_name == "Congestion-Aware":
            proto = CongestionAwareRoutingProtocol()
        elif protocol_name == "Dijkstra-SPF":
            proto = DijkstraRoutingProtocol(dynamic_reroute=False)
        else:
            proto = RandomRoutingProtocol()

        # 3. Engine
        self.engine = SimulationEngine(network=self.network, protocol=proto, config=self.config)
        self.engine.initialize()
        
        self.selected_link_key = None
        self.selected_node_id = None
        self._update_ui_elements()
        self._redraw_network()

    def toggle_play(self):
        """Toggle simulation playback."""
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_play.config(text="⏸ Pause", bg="#d97706")
        else:
            self.btn_play.config(text="▶ Run", bg="#0284c7")

    def step_simulation(self):
        """Execute a single step while paused."""
        if self.engine:
            self.engine.step()
            self._update_ui_elements()
            self._redraw_network()

    def reset_simulation(self):
        """Reset current topology and protocol."""
        topo_str = self.topo_var.get()
        proto_str = self.proto_var.get()
        self.load_simulation(topo_str, proto_str)

    def inject_traffic_burst(self):
        """Simulate sudden traffic spike."""
        if self.engine:
            self.engine.config.traffic.packet_rate *= 3.0
            messagebox.showinfo("Traffic Surge Injected", "Traffic generation rate tripled for high load test!")

    def toggle_selected_link(self):
        """Sever or restore the currently selected link."""
        if not self.selected_link_key or not self.network or not self.engine:
            messagebox.showwarning("No Link Selected", "Please click on a link line in the canvas first!")
            return

        u, v = self.selected_link_key
        link = self.network.get_link(u, v)
        if link:
            if link.is_up:
                self.network.kill_link(u, v, self.engine.current_time)
                self.engine.protocol.on_link_state_changed(u, v, False, self.engine.current_time)
            else:
                self.network.restore_link(u, v, self.engine.current_time)
                self.engine.protocol.on_link_state_changed(u, v, True, self.engine.current_time)
            self._update_inspector()
            self._redraw_network()

    def _on_protocol_changed(self, event=None):
        self.load_simulation(self.topo_var.get(), self.proto_var.get())

    def _on_topology_changed(self, event=None):
        self.load_simulation(self.topo_var.get(), self.proto_var.get())

    def _on_traffic_changed(self, event=None):
        pat = self.traffic_var.get().lower()
        if self.engine:
            self.engine.config.traffic.traffic_pattern = pat

    def _simulation_tick(self):
        """Periodic GUI timer loop (runs ~30 times/sec)."""
        if self.is_running and self.engine:
            # Advance simulation based on speed multiplier
            steps = max(1, int(self.speed_scale.get() * 8))
            for _ in range(steps):
                if not self.engine.step():
                    self.is_running = False
                    self.btn_play.config(text="▶ Run", bg="#0284c7")
                    break

            self._update_ui_elements()
            self._redraw_network()

        self.root.after(30, self._simulation_tick)

    def _update_ui_elements(self):
        """Update metrics in the right panel and redraw mini sparkline chart."""
        if not self.engine:
            return

        m = self.engine.metrics
        t = self.engine.current_time

        self.lbl_time.config(text=f"{t:.2f} s")
        self.lbl_generated.config(text=f"{m.total_generated}")
        self.lbl_delivered.config(text=f"{m.total_delivered}")
        self.lbl_dropped.config(text=f"{m.total_dropped}")
        self.lbl_pdr.config(text=f"{m.get_delivery_ratio()*100:.1f} %")
        self.lbl_latency.config(text=f"{m.get_average_latency():.4f} s")
        self.lbl_throughput.config(text=f"{m.get_throughput(t):.2f} pps")

        # Update Inspector if an item is selected
        self._update_inspector()

        # Redraw mini sparkline chart
        self._redraw_sparkline()

    def _redraw_sparkline(self):
        """Draw live latency trend on mini canvas."""
        self.chart_canvas.delete("all")
        if not self.engine:
            return
        
        hist = self.engine.metrics.history_avg_latency
        if len(hist) < 2:
            return

        w = self.chart_canvas.winfo_width() or 280
        h = self.chart_canvas.winfo_height() or 130
        pad = 12

        # Draw last 40 data points
        data = hist[-40:]
        max_val = max(data) * 1.2 or 0.5
        min_val = 0.0

        coords = []
        step_x = (w - 2 * pad) / max(1, len(data) - 1)
        for i, val in enumerate(data):
            x = pad + i * step_x
            norm = (val - min_val) / (max_val - min_val)
            y = (h - pad) - norm * (h - 2 * pad)
            coords.extend([x, y])

        # Draw line
        if len(coords) >= 4:
            self.chart_canvas.create_line(coords, fill=self.c_accent, width=2, smooth=True)

    def _update_inspector(self):
        """Display details of selected node or link in text inspector."""
        if not self.network or not self.engine:
            return

        if self.selected_node_id is not None:
            node = self.network.nodes[self.selected_node_id]
            q_table = self.engine.protocol.get_routing_table(self.selected_node_id)
            info = f"--- NODE {self.selected_node_id} ---\n"
            info += f"Queue: {len(node.packet_queue)} / {node.buffer_capacity}\n"
            info += f"Drops: {node.total_buffer_drops}\n"
            info += f"Forwarded: {node.total_forwarded}\n"
            info += f"Delivered: {node.total_delivered}\n"
            info += f"Neighbors: {node.neighbors}\n\n"
            info += f"Q-Table / Routes:\n"
            for k, v in list(q_table.items())[:6]:
                info += f"{k}: {v}\n"
            
            self.txt_inspector.delete("1.0", tk.END)
            self.txt_inspector.insert(tk.END, info)

        elif self.selected_link_key is not None:
            u, v = self.selected_link_key
            link = self.network.get_link(u, v)
            if link:
                status = "ACTIVE (UP)" if link.is_up else "BROKEN (DOWN)"
                info = f"--- LINK {u} <-> {v} ---\n"
                info += f"Status: {status}\n"
                info += f"Bandwidth: {link.bandwidth} pkt/s\n"
                info += f"Delay: {link.propagation_delay*1000:.1f} ms\n"
                info += f"Transmitted: {link.packets_transmitted}\n"
                info += f"Dropped: {link.packets_dropped}\n"
                info += f"\nClick 'Toggle Selected Link' above to cut/restore!"
                
                self.txt_inspector.delete("1.0", tk.END)
                self.txt_inspector.insert(tk.END, info)

    def _redraw_network(self):
        """Render network graph on Tkinter canvas with dynamic queue color coding and packet dots."""
        self.canvas.delete("all")
        if not self.network:
            return

        canvas_w = self.canvas.winfo_width() or 800
        canvas_h = self.canvas.winfo_height() or 650

        # Auto-scale coordinates to fit canvas
        coords = list(self.network.positions.values())
        if not coords:
            return
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = max(1.0, max_x - min_x)
        range_y = max(1.0, max_y - min_y)

        margin = 60
        scale_x = (canvas_w - 2 * margin) / range_x
        scale_y = (canvas_h - 2 * margin) / range_y

        node_coords = {}
        for nid, (x, y) in self.network.positions.items():
            cx = margin + (x - min_x) * scale_x
            cy = margin + (y - min_y) * scale_y
            node_coords[nid] = (cx, cy)

        # 1. Draw Links
        for (u, v), link in self.network.links.items():
            if u not in node_coords or v not in node_coords:
                continue
            x1, y1 = node_coords[u]
            x2, y2 = node_coords[v]

            is_selected = (self.selected_link_key == (u, v))
            
            if not link.is_up:
                # Broken link
                line_color = self.c_rose
                dash = (6, 4)
                w = 3 if not is_selected else 5
            else:
                line_color = "#38bdf8" if is_selected else "#334155"
                dash = ()
                w = 4 if is_selected else 2

            self.canvas.create_line(x1, y1, x2, y2, fill=line_color, width=w, dash=dash)

        # 2. Draw In-Flight Packets (Animated traveling dots)
        if self.engine:
            for pid, tx in list(self.engine.in_flight_transmissions.items()):
                u = tx["src"]
                v = tx["dst"]
                if u in node_coords and v in node_coords:
                    x1, y1 = node_coords[u]
                    x2, y2 = node_coords[v]

                    duration = max(0.001, tx["arrive_time"] - tx["start_time"])
                    progress = (self.engine.current_time - tx["start_time"]) / duration
                    progress = max(0.0, min(1.0, progress))

                    px = x1 + (x2 - x1) * progress
                    py = y1 + (y2 - y1) * progress

                    # Glowing animated packet dot
                    pr = 5
                    self.canvas.create_oval(px - pr, py - pr, px + pr, py + pr, fill=self.c_amber, outline="white", width=1.5)

        # 3. Draw Nodes (Color-coded based on queue fill ratio)
        r = 18
        for nid, (cx, cy) in node_coords.items():
            node = self.network.nodes[nid]
            ratio = node.buffer_occupancy_ratio

            # Color gradient: Green -> Yellow -> Red
            if ratio < 0.3:
                node_fill = self.c_emerald  # Low load
            elif ratio < 0.7:
                node_fill = self.c_amber    # Medium load
            else:
                node_fill = self.c_rose     # Congested / Near overflow!

            is_sel = (self.selected_node_id == nid)
            outline_color = "#ffffff" if is_sel else self.c_panel
            outline_width = 3 if is_sel else 2

            # Node circle
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=node_fill, outline=outline_color, width=outline_width
            )

            # Node ID Label
            self.canvas.create_text(cx, cy, text=str(nid), fill="#090d16", font=("Segoe UI", 9, "bold"))

            # Queue count badge above node
            q_str = f"{len(node.packet_queue)}"
            self.canvas.create_text(cx, cy - r - 8, text=q_str, fill="#94a3b8", font=("Segoe UI", 8))

    def _on_canvas_click(self, event):
        """Detect clicks on nodes or links to inspect or trigger cuts."""
        if not self.network:
            return

        canvas_w = self.canvas.winfo_width() or 800
        canvas_h = self.canvas.winfo_height() or 650
        coords = list(self.network.positions.values())
        if not coords:
            return
        xs, ys = [c[0] for c in coords], [c[1] for c in coords]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        margin = 60
        scale_x = (canvas_w - 2 * margin) / max(1.0, max_x - min_x)
        scale_y = (canvas_h - 2 * margin) / max(1.0, max_y - min_y)

        node_coords = {
            nid: (margin + (x - min_x) * scale_x, margin + (y - min_y) * scale_y)
            for nid, (x, y) in self.network.positions.items()
        }

        # Check Node click
        clicked_node = None
        for nid, (nx, ny) in node_coords.items():
            dist = math.hypot(event.x - nx, event.y - ny)
            if dist <= 20:
                clicked_node = nid
                break

        if clicked_node is not None:
            self.selected_node_id = clicked_node
            self.selected_link_key = None
            self._update_inspector()
            self._redraw_network()
            return

        # Check Link click
        clicked_link = None
        for (u, v) in self.network.links:
            if u not in node_coords or v not in node_coords:
                continue
            x1, y1 = node_coords[u]
            x2, y2 = node_coords[v]

            # Distance from point to line segment
            line_len = math.hypot(x2 - x1, y2 - y1)
            if line_len == 0:
                continue
            u_proj = ((event.x - x1) * (x2 - x1) + (event.y - y1) * (y2 - y1)) / (line_len ** 2)
            if 0.0 <= u_proj <= 1.0:
                proj_x = x1 + u_proj * (x2 - x1)
                proj_y = y1 + u_proj * (y2 - y1)
                d = math.hypot(event.x - proj_x, event.y - proj_y)
                if d <= 8:
                    clicked_link = (u, v)
                    break

        if clicked_link is not None:
            self.selected_link_key = clicked_link
            self.selected_node_id = None
            self._update_inspector()
            self._redraw_network()


def launch_gui():
    """Main function to launch the desktop visualizer."""
    root = tk.Tk()
    app = RoutingVisualizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()

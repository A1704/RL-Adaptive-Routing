"""
Lightweight Web-Based Visualizer for RL Adaptive Routing.
Built entirely using Python's standard library (http.server, json, urllib).
Zero external dependencies. Runs on any browser.
"""

import http.server
import socketserver
import json
import urllib.parse
import webbrowser
import threading
import time
import os
import sys

# Ensure root is in sys.path
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


HTML_FRONTEND = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RL Adaptive Routing Protocol - Live Visualizer</title>
    <style>
        :root {
            --bg: #0b1120;
            --panel: #1e293b;
            --border: #334155;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --accent: #38bdf8;
            --green: #34d399;
            --yellow: #fbbf24;
            --red: #fb7185;
            --purple: #c084fc;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, sans-serif; }
        body { background: var(--bg); color: var(--text); display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        header { background: var(--panel); border-bottom: 1px solid var(--border); padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
        .logo-title { font-size: 1.15rem; font-weight: 700; color: var(--accent); display: flex; align-items: center; gap: 8px; }
        
        .controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        select, button, input[type="range"] { background: #0f172a; color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px; font-size: 0.85rem; outline: none; }
        button { cursor: pointer; font-weight: 600; transition: all 0.15s; }
        button:hover { filter: brightness(1.2); }
        .btn-primary { background: #0284c7; color: white; border: none; }
        .btn-danger { background: #e11d48; color: white; border: none; }
        .btn-warn { background: #d97706; color: white; border: none; }

        .workspace { display: flex; flex: 1; overflow: hidden; }
        #canvasContainer { flex: 1; position: relative; background: radial-gradient(circle at center, #0f172a 0%, #080d1a 100%); overflow: hidden; }
        canvas { display: block; width: 100%; height: 100%; }

        .sidebar { width: 340px; background: var(--panel); border-left: 1px solid var(--border); display: flex; flex-direction: column; padding: 14px; overflow-y: auto; gap: 14px; }
        
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .stat-card { background: #0f172a; border: 1px solid var(--border); border-radius: 8px; padding: 10px; }
        .stat-label { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; margin-bottom: 4px; }
        .stat-val { font-size: 1.25rem; font-weight: 700; }
        
        .panel-box { background: #0f172a; border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
        .panel-title { font-size: 0.85rem; font-weight: 700; color: var(--accent); margin-bottom: 8px; text-transform: uppercase; }
        
        .inspector-pre { font-family: 'Consolas', monospace; font-size: 0.78rem; color: #a5f3fc; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto; }
        
        .legend { display: flex; gap: 12px; font-size: 0.75rem; color: var(--text-dim); align-items: center; }
        .legend-item { display: flex; align-items: center; gap: 4px; }
        .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    </style>
</head>
<body>
    <header>
        <div class="logo-title">
            <span>⚡ RL Adaptive Routing</span>
            <span style="font-size:0.75rem; background:#0369a1; padding:2px 8px; border-radius:12px; color:#e0f2fe;">Live Web Visualizer</span>
        </div>
        
        <div class="controls">
            <label style="font-size:0.8rem; color:var(--text-dim);">Protocol:</label>
            <select id="selProtocol" onchange="changeProtocol()">
                <option value="Q-Routing" selected>Q-Routing (RL)</option>
                <option value="Dual-Q-Routing">Dual-Q-Routing (Bidirectional RL)</option>
                <option value="Congestion-Aware">Congestion-Aware (Dynamic Heuristic)</option>
                <option value="Dijkstra-SPF">Dijkstra SPF (Static OSPF)</option>
                <option value="Random-Walk">Random Walk (Baseline)</option>
            </select>

            <label style="font-size:0.8rem; color:var(--text-dim);">Topology:</label>
            <select id="selTopology" onchange="changeTopology()">
                <option value="nsfnet" selected>NSFNet (14 Nodes)</option>
                <option value="grid">6x6 Grid (36 Nodes)</option>
                <option value="bottleneck">Bottleneck Diamond (6 Nodes)</option>
                <option value="ring">Ring-Chord (12 Nodes)</option>
            </select>

            <button id="btnPlay" class="btn-primary" onclick="togglePlay()">▶ Run</button>
            <button onclick="stepSim()">⏭ Step</button>
            <button onclick="resetSim()">🔄 Reset</button>

            <label style="font-size:0.8rem; color:var(--text-dim);">Speed:</label>
            <input type="range" id="speedRange" min="1" max="15" value="4" style="width:70px;">

            <button class="btn-warn" onclick="injectBurst()">💥 Traffic Surge</button>
            <button class="btn-danger" onclick="toggleSelectedLink()">⚡ Toggle Link</button>
        </div>
    </header>

    <div class="workspace">
        <div id="canvasContainer">
            <canvas id="netCanvas"></canvas>
        </div>

        <div class="sidebar">
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">Sim Time</div>
                    <div class="stat-val" id="valTime" style="color:var(--text);">0.00s</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Delivery (PDR)</div>
                    <div class="stat-val" id="valPdr" style="color:var(--green);">100%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Avg Latency</div>
                    <div class="stat-val" id="valLat" style="color:var(--accent);">0.000s</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Throughput</div>
                    <div class="stat-val" id="valTp" style="color:var(--yellow);">0.0 pps</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Packets Sent</div>
                    <div class="stat-val" id="valSent" style="color:var(--text-dim);">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Packet Drops</div>
                    <div class="stat-val" id="valDrops" style="color:var(--red);">0</div>
                </div>
            </div>

            <div class="panel-box">
                <div class="panel-title">Element Inspector</div>
                <div class="legend" style="margin-bottom:8px;">
                    <span class="legend-item"><span class="dot" style="background:var(--green)"></span> Empty</span>
                    <span class="legend-item"><span class="dot" style="background:var(--yellow)"></span> Busy</span>
                    <span class="legend-item"><span class="dot" style="background:var(--red)"></span> Full/Drop</span>
                </div>
                <pre class="inspector-pre" id="inspectorText">Click any node to view live Q-table entries and queue status.
Click any link and press 'Toggle Link' to sever or restore it!</pre>
            </div>

            <div class="panel-box" style="flex:1;">
                <div class="panel-title">Q-Routing Learning Activity</div>
                <div style="font-size:0.8rem; color:var(--text-dim); line-height:1.5;">
                    <p>• <strong>RL Agent</strong>: Every node maintains estimated delivery latency $\min_z Q(d, z)$.</p>
                    <p style="margin-top:4px;">• <strong>Adaptive Reroute</strong>: Under congestion or link failure, Q-values rise, dynamically shifting packets to alternative routes.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('netCanvas');
        const ctx = canvas.getContext('2d');
        let isRunning = false;
        let selectedNode = null;
        let selectedLink = null;
        let state = null;

        function resizeCanvas() {
            const rect = canvas.parentElement.getBoundingClientRect();
            canvas.width = rect.width;
            canvas.height = rect.height;
            draw();
        }
        window.addEventListener('resize', resizeCanvas);

        async function fetchState() {
            try {
                const res = await fetch('/api/state');
                state = await res.json();
                updateUI();
                draw();
            } catch (e) {
                console.error(e);
            }
        }

        async function stepSim(steps = 1) {
            try {
                const res = await fetch(`/api/step?count=${steps}`);
                state = await res.json();
                updateUI();
                draw();
            } catch (e) {
                console.error(e);
            }
        }

        function updateUI() {
            if (!state) return;
            const m = state.metrics;
            document.getElementById('valTime').textContent = state.time.toFixed(2) + 's';
            document.getElementById('valPdr').textContent = (m.pdr * 100).toFixed(1) + '%';
            document.getElementById('valLat').textContent = m.avg_latency.toFixed(4) + 's';
            document.getElementById('valTp').textContent = m.throughput.toFixed(1) + ' pps';
            document.getElementById('valSent').textContent = m.generated;
            document.getElementById('valDrops').textContent = m.dropped;

            updateInspector();
        }

        function updateInspector() {
            if (!state) return;
            const insp = document.getElementById('inspectorText');
            if (selectedNode !== null && state.nodes[selectedNode]) {
                const n = state.nodes[selectedNode];
                let txt = `=== NODE ${selectedNode} ===\nQueue: ${n.queue_len} / ${n.capacity}\nBuffer Drops: ${n.drops}\nDelivered: ${n.delivered}\nNeighbors: [${n.neighbors.join(', ')}]\n\nQ-Table / Routes:\n`;
                const qEntries = Object.entries(n.q_table || {});
                if (qEntries.length === 0) {
                    txt += "No entries yet.";
                } else {
                    for (const [k, v] of qEntries.slice(0, 10)) {
                        txt += `${k}: ${JSON.stringify(v)}\n`;
                    }
                }
                insp.textContent = txt;
            } else if (selectedLink) {
                const [u, v] = selectedLink;
                const link = state.links.find(l => (l.u === u && l.v === v) || (l.u === v && l.v === u));
                if (link) {
                    insp.textContent = `=== LINK ${u} <-> ${v} ===\nStatus: ${link.is_up ? 'ACTIVE (UP)' : 'BROKEN (DOWN)'}\nBandwidth: ${link.bandwidth} pkt/s\nDelay: ${(link.delay*1000).toFixed(1)} ms\nPackets Carried: ${link.packets_transmitted}\n\nClick 'Toggle Link' above to sever or restore!`;
                }
            }
        }

        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            if (!state || !state.nodes) return;

            const nodes = state.nodes;
            const links = state.links;
            const margin = 60;

            // Compute coordinate bounds
            const coords = Object.values(nodes).map(n => n.pos);
            const xs = coords.map(c => c[0]);
            const ys = coords.map(c => c[1]);
            const minX = Math.min(...xs), maxX = Math.max(...xs);
            const minY = Math.min(...ys), maxY = Math.max(...ys);
            const scaleX = (canvas.width - 2 * margin) / Math.max(1, maxX - minX);
            const scaleY = (canvas.height - 2 * margin) / Math.max(1, maxY - minY);

            const screenCoords = {};
            for (const [id, n] of Object.entries(nodes)) {
                screenCoords[id] = {
                    x: margin + (n.pos[0] - minX) * scaleX,
                    y: margin + (n.pos[1] - minY) * scaleY
                };
            }

            // Draw Links
            links.forEach(l => {
                const p1 = screenCoords[l.u];
                const p2 = screenCoords[l.v];
                if (!p1 || !p2) return;

                const isSel = selectedLink && ((selectedLink[0] === l.u && selectedLink[1] === l.v) || (selectedLink[0] === l.v && selectedLink[1] === l.u));
                
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                if (!l.is_up) {
                    ctx.strokeStyle = '#fb7185';
                    ctx.setLineDash([8, 6]);
                    ctx.lineWidth = 3;
                } else if (isSel) {
                    ctx.strokeStyle = '#38bdf8';
                    ctx.setLineDash([]);
                    ctx.lineWidth = 4;
                } else {
                    ctx.strokeStyle = '#334155';
                    ctx.setLineDash([]);
                    ctx.lineWidth = 2;
                }
                ctx.stroke();
                ctx.setLineDash([]);
            });

            // Draw In-Flight Packets (Animated traveling dots)
            if (state.in_flight) {
                state.in_flight.forEach(pkt => {
                    const p1 = screenCoords[pkt.src];
                    const p2 = screenCoords[pkt.dst];
                    if (!p1 || !p2) return;

                    const totalTime = Math.max(0.001, pkt.arrive_time - pkt.start_time);
                    const progress = Math.max(0, Math.min(1, (state.time - pkt.start_time) / totalTime));

                    const curX = p1.x + (p2.x - p1.x) * progress;
                    const curY = p1.y + (p2.y - p1.y) * progress;

                    ctx.beginPath();
                    ctx.arc(curX, curY, 5, 0, Math.PI * 2);
                    ctx.fillStyle = '#fbbf24';
                    ctx.fill();
                    ctx.strokeStyle = '#ffffff';
                    ctx.lineWidth = 1.5;
                    ctx.stroke();
                });
            }

            // Draw Nodes
            const r = 18;
            for (const [id, n] of Object.entries(nodes)) {
                const p = screenCoords[id];
                const occ = n.queue_len / n.capacity;
                let fill = '#34d399';
                if (occ > 0.6) fill = '#fb7185';
                else if (occ > 0.2) fill = '#fbbf24';

                const isSel = (parseInt(id) === selectedNode);

                ctx.beginPath();
                ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
                ctx.fillStyle = fill;
                ctx.fill();
                ctx.strokeStyle = isSel ? '#ffffff' : '#1e293b';
                ctx.lineWidth = isSel ? 3 : 2;
                ctx.stroke();

                // ID
                ctx.fillStyle = '#0f172a';
                ctx.font = 'bold 11px Segoe UI, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(id, p.x, p.y);

                // Queue indicator badge
                ctx.fillStyle = '#94a3b8';
                ctx.font = '10px Segoe UI, sans-serif';
                ctx.fillText(`q:${n.queue_len}`, p.x, p.y - r - 8);
            }
        }

        // Canvas Click handler
        canvas.addEventListener('click', (e) => {
            if (!state || !state.nodes) return;
            const rect = canvas.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;

            const margin = 60;
            const coords = Object.values(state.nodes).map(n => n.pos);
            const xs = coords.map(c => c[0]), ys = coords.map(c => c[1]);
            const minX = Math.min(...xs), maxX = Math.max(...xs);
            const minY = Math.min(...ys), maxY = Math.max(...ys);
            const scaleX = (canvas.width - 2 * margin) / Math.max(1, maxX - minX);
            const scaleY = (canvas.height - 2 * margin) / Math.max(1, maxY - minY);

            const screenCoords = {};
            for (const [id, n] of Object.entries(state.nodes)) {
                screenCoords[id] = {
                    x: margin + (n.pos[0] - minX) * scaleX,
                    y: margin + (n.pos[1] - minY) * scaleY
                };
            }

            // Check node click
            let clickedNode = null;
            for (const [id, p] of Object.entries(screenCoords)) {
                const d = Math.hypot(clickX - p.x, clickY - p.y);
                if (d <= 20) {
                    clickedNode = parseInt(id);
                    break;
                }
            }

            if (clickedNode !== null) {
                selectedNode = clickedNode;
                selectedLink = null;
                updateInspector();
                draw();
                return;
            }

            // Check link click
            let clickedLink = null;
            for (const l of state.links) {
                const p1 = screenCoords[l.u];
                const p2 = screenCoords[l.v];
                if (!p1 || !p2) continue;

                const lineLen = Math.hypot(p2.x - p1.x, p2.y - p1.y);
                if (lineLen === 0) continue;
                const u = ((clickX - p1.x) * (p2.x - p1.x) + (clickY - p1.y) * (p2.y - p1.y)) / (lineLen ** 2);
                if (u >= 0 && u <= 1) {
                    const px = p1.x + u * (p2.x - p1.x);
                    const py = p1.y + u * (p2.y - p1.y);
                    if (Math.hypot(clickX - px, clickY - py) <= 8) {
                        clickedLink = [l.u, l.v];
                        break;
                    }
                }
            }

            if (clickedLink) {
                selectedLink = clickedLink;
                selectedNode = null;
                updateInspector();
                draw();
            }
        });

        function togglePlay() {
            isRunning = !isRunning;
            const btn = document.getElementById('btnPlay');
            if (isRunning) {
                btn.textContent = '⏸ Pause';
                btn.className = 'btn-warn';
            } else {
                btn.textContent = '▶ Run';
                btn.className = 'btn-primary';
            }
        }

        async function resetSim() {
            isRunning = false;
            document.getElementById('btnPlay').textContent = '▶ Run';
            document.getElementById('btnPlay').className = 'btn-primary';
            await fetch('/api/reset');
            await fetchState();
        }

        async function changeProtocol() {
            const proto = document.getElementById('selProtocol').value;
            await fetch(`/api/set_protocol?protocol=${encodeURIComponent(proto)}`);
            await fetchState();
        }

        async function changeTopology() {
            const topo = document.getElementById('selTopology').value;
            await fetch(`/api/set_topology?topology=${encodeURIComponent(topo)}`);
            await fetchState();
        }

        async function injectBurst() {
            await fetch('/api/burst');
            alert('💥 Traffic surge injected!');
        }

        async function toggleSelectedLink() {
            if (!selectedLink) {
                alert('Please click on a link line in the canvas first!');
                return;
            }
            await fetch(`/api/toggle_link?u=${selectedLink[0]}&v=${selectedLink[1]}`);
            await fetchState();
        }

        // Animation Loop
        setInterval(() => {
            if (isRunning) {
                const speed = parseInt(document.getElementById('speedRange').value);
                stepSim(speed);
            }
        }, 50);

        // Initial setup
        resizeCanvas();
        fetchState();
    </script>
</body>
</html>
"""


class WebSimulationManager:
    """Coordinates the backend network and protocol state for the web visualizer."""

    def __init__(self):
        self.topology_name = "nsfnet"
        self.protocol_name = "Q-Routing"
        self.config = SimulationConfig(duration=10000.0)
        self.lock = threading.Lock()
        self.rebuild()

    def rebuild(self):
        with self.lock:
            self.network = TopologyFactory.get_topology(self.topology_name)
            if self.protocol_name == "Q-Routing":
                proto = QRoutingProtocol(config=self.config.rl)
            elif self.protocol_name == "Dual-Q-Routing":
                proto = DualQRoutingProtocol(config=self.config.rl)
            elif self.protocol_name == "Congestion-Aware":
                proto = CongestionAwareRoutingProtocol()
            elif self.protocol_name == "Dijkstra-SPF":
                proto = DijkstraRoutingProtocol(dynamic_reroute=False)
            else:
                proto = RandomRoutingProtocol()

            self.engine = SimulationEngine(network=self.network, protocol=proto, config=self.config)
            self.engine.initialize()

    def step(self, count: int = 1):
        with self.lock:
            for _ in range(count):
                if not self.engine.step():
                    break

    def toggle_link(self, u: int, v: int):
        with self.lock:
            link = self.network.get_link(u, v)
            if link:
                if link.is_up:
                    self.network.kill_link(u, v, self.engine.current_time)
                    self.engine.protocol.on_link_state_changed(u, v, False, self.engine.current_time)
                else:
                    self.network.restore_link(u, v, self.engine.current_time)
                    self.engine.protocol.on_link_state_changed(u, v, True, self.engine.current_time)

    def inject_burst(self):
        with self.lock:
            self.engine.config.traffic.packet_rate *= 3.0

    def get_state_dict(self):
        with self.lock:
            nodes_data = {}
            for nid, node in self.network.nodes.items():
                q_table = self.engine.protocol.get_routing_table(nid)
                nodes_data[nid] = {
                    "queue_len": len(node.packet_queue),
                    "capacity": node.buffer_capacity,
                    "drops": node.total_buffer_drops,
                    "delivered": node.total_delivered,
                    "neighbors": node.neighbors,
                    "pos": self.network.positions.get(nid, (100, 100)),
                    "q_table": q_table
                }

            links_data = []
            for (u, v), link in self.network.links.items():
                links_data.append({
                    "u": u,
                    "v": v,
                    "is_up": link.is_up,
                    "bandwidth": link.bandwidth,
                    "delay": link.propagation_delay,
                    "packets_transmitted": link.packets_transmitted
                })

            in_flight = []
            for pid, tx in self.engine.in_flight_transmissions.items():
                in_flight.append({
                    "src": tx["src"],
                    "dst": tx["dst"],
                    "start_time": tx["start_time"],
                    "arrive_time": tx["arrive_time"]
                })

            m = self.engine.metrics
            t = self.engine.current_time

            return {
                "time": round(t, 2),
                "protocol": self.protocol_name,
                "topology": self.topology_name,
                "nodes": nodes_data,
                "links": links_data,
                "in_flight": in_flight,
                "metrics": {
                    "generated": m.total_generated,
                    "delivered": m.total_delivered,
                    "dropped": m.total_dropped,
                    "pdr": m.get_delivery_ratio(),
                    "avg_latency": m.get_average_latency(),
                    "throughput": m.get_throughput(t)
                }
            }


SIM_MANAGER = WebSimulationManager()


class RequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request Handler providing HTML frontend and JSON simulation API."""

    def log_message(self, format, *args):
        # Suppress spammy HTTP server logs
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_FRONTEND.encode("utf-8"))

        elif path == "/api/state":
            data = SIM_MANAGER.get_state_dict()
            self._send_json(data)

        elif path == "/api/step":
            count = int(query.get("count", ["1"])[0])
            SIM_MANAGER.step(count)
            data = SIM_MANAGER.get_state_dict()
            self._send_json(data)

        elif path == "/api/reset":
            SIM_MANAGER.rebuild()
            self._send_json({"status": "ok"})

        elif path == "/api/burst":
            SIM_MANAGER.inject_burst()
            self._send_json({"status": "ok"})

        elif path == "/api/toggle_link":
            u = int(query.get("u", ["0"])[0])
            v = int(query.get("v", ["1"])[0])
            SIM_MANAGER.toggle_link(u, v)
            self._send_json({"status": "ok"})

        elif path == "/api/set_protocol":
            proto = query.get("protocol", ["Q-Routing"])[0]
            SIM_MANAGER.protocol_name = proto
            SIM_MANAGER.rebuild()
            self._send_json({"status": "ok"})

        elif path == "/api/set_topology":
            topo = query.get("topology", ["nsfnet"])[0]
            SIM_MANAGER.topology_name = topo
            SIM_MANAGER.rebuild()
            self._send_json({"status": "ok"})

        else:
            self.send_error(404, "Not Found")

    def _send_json(self, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)


def start_server(port: int = 8080):
    """Start local web server and open the browser."""
    # Find free port if 8080 is occupied
    server = None
    for p in range(port, port + 10):
        try:
            server = socketserver.TCPServer(("127.0.0.1", p), RequestHandler)
            port = p
            break
        except OSError:
            continue

    if not server:
        print("Could not bind to a local port.")
        return

    url = f"http://127.0.0.1:{port}"
    print(f"\n=======================================================")
    print(f"  RL Adaptive Routing - Live Web Visualizer")
    print(f"  Running locally at: {url}")
    print(f"=======================================================\n")

    # Open browser
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    start_server(8080)


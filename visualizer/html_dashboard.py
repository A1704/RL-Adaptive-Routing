"""
HTML Dashboard Generator for RL Adaptive Routing Benchmarks.
Generates an interactive, standalone HTML5 report with embedded SVG topologies,
charts, and comparative tables without requiring any external dependencies.
"""

import json
from typing import Dict, Any, List


class HTMLDashboardGenerator:
    """Produces a clean, standalone HTML visualization report."""

    @staticmethod
    def generate_report(
        benchmark_results: Dict[str, Dict[str, Any]],
        topology_name: str,
        config_dict: Dict[str, Any],
        output_file: str = "simulation_report.html"
    ) -> str:
        """
        Generate standalone HTML report from multi-protocol benchmark results.
        benchmark_results: mapping { protocol_name: { summary_dict, time_series_dict } }
        """
        protocols = list(benchmark_results.keys())
        pdr_data = [benchmark_results[p]["summary"]["packet_delivery_ratio_pct"] for p in protocols]
        latency_data = [benchmark_results[p]["summary"]["average_latency_s"] for p in protocols]
        throughput_data = [benchmark_results[p]["summary"]["throughput_pps"] for p in protocols]
        drops_data = [benchmark_results[p]["summary"]["packets_dropped"] for p in protocols]
        hops_data = [benchmark_results[p]["summary"]["average_hops"] for p in protocols]

        results_json = json.dumps(benchmark_results, indent=2)

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RL Adaptive Routing Protocol - Benchmark Dashboard</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-emerald: #34d399;
            --accent-rose: #fb7185;
            --accent-amber: #fbbf24;
            --accent-purple: #c084fc;
            --border-color: #475569;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }}
        body {{ background-color: var(--bg-primary); color: var(--text-primary); padding: 24px; line-height: 1.5; }}
        header {{ margin-bottom: 28px; border-bottom: 1px solid var(--border-color); padding-bottom: 16px; }}
        h1 {{ font-size: 2rem; font-weight: 700; color: var(--accent-blue); margin-bottom: 8px; }}
        p.subtitle {{ color: var(--text-secondary); font-size: 1.05rem; }}
        
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; background: #0369a1; color: #e0f2fe; margin-right: 8px; }}
        
        .grid-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 28px; }}
        .card {{ background: var(--bg-secondary); border-radius: 12px; padding: 20px; border: 1px solid var(--border-color); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); }}
        .card-title {{ font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-bottom: 8px; }}
        .card-value {{ font-size: 1.8rem; font-weight: 700; color: var(--accent-emerald); }}
        .card-desc {{ font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px; }}

        .section-title {{ font-size: 1.3rem; margin: 28px 0 16px 0; color: #e2e8f0; display: flex; align-items: center; gap: 8px; }}
        .section-title::before {{ content: ''; display: inline-block; width: 4px; height: 1.2rem; background: var(--accent-blue); border-radius: 2px; }}

        table {{ width: 100%; border-collapse: collapse; background: var(--bg-secondary); border-radius: 12px; overflow: hidden; margin-bottom: 28px; }}
        th, td {{ padding: 14px 18px; text-align: left; border-bottom: 1px solid var(--border-color); }}
        th {{ background: #182234; font-weight: 600; color: var(--accent-blue); font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        tr:hover {{ background: rgba(56, 189, 248, 0.05); }}
        .winner {{ color: var(--accent-emerald); font-weight: bold; }}

        .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; margin-bottom: 28px; }}
        .chart-box {{ background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; }}
        .chart-header {{ font-weight: 600; margin-bottom: 16px; color: var(--text-primary); font-size: 1rem; }}
        canvas {{ width: 100%; height: 260px; }}

        .details-pre {{ background: #090d16; padding: 16px; border-radius: 8px; font-family: 'Consolas', monospace; font-size: 0.85rem; overflow-x: auto; color: #38bdf8; max-height: 350px; border: 1px solid var(--border-color); }}
        footer {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border-color); }}
    </style>
</head>
<body>
    <header>
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <h1>Adaptive Routing Protocol Benchmark</h1>
                <p class="subtitle">Multi-Agent Reinforcement Learning vs. Traditional Routing Protocols</p>
            </div>
            <div>
                <span class="badge">Topology: {topology_name}</span>
                <span class="badge" style="background:#047857;">DES Simulator</span>
                <span class="badge" style="background:#6d28d9;">Q-Routing</span>
            </div>
        </div>
    </header>

    <div class="grid-cards">
        <div class="card">
            <div class="card-title">Top Protocol (Latency)</div>
            <div class="card-value" id="bestLatencyProtocol">-</div>
            <div class="card-desc" id="bestLatencyValue">Lowest end-to-end delivery time</div>
        </div>
        <div class="card">
            <div class="card-title">Top Protocol (PDR)</div>
            <div class="card-value" id="bestPdrProtocol" style="color:var(--accent-blue);">-</div>
            <div class="card-desc" id="bestPdrValue">Highest packet delivery percentage</div>
        </div>
        <div class="card">
            <div class="card-title">Max Throughput</div>
            <div class="card-value" id="bestTpProtocol" style="color:var(--accent-amber);">-</div>
            <div class="card-desc" id="bestTpValue">Packets delivered per second</div>
        </div>
        <div class="card">
            <div class="card-title">Simulated Packets</div>
            <div class="card-value" style="color:var(--accent-purple);" id="totalPacketsCount">-</div>
            <div class="card-desc">Total traffic load tested</div>
        </div>
    </div>

    <div class="section-title">Comparative Performance Summary</div>
    <table id="summaryTable">
        <thead>
            <tr>
                <th>Protocol</th>
                <th>Avg Latency (s)</th>
                <th>Packet Delivery Ratio (PDR)</th>
                <th>Throughput (pps)</th>
                <th>Packets Dropped</th>
                <th>Avg Hop Count</th>
            </tr>
        </thead>
        <tbody>
            <!-- Populated by JS -->
        </tbody>
    </table>

    <div class="section-title">Visual Performance Metrics</div>
    <div class="charts-grid">
        <div class="chart-box">
            <div class="chart-header">Average Latency Comparison (Lower is Better)</div>
            <canvas id="chartLatency"></canvas>
        </div>
        <div class="chart-box">
            <div class="chart-header">Packet Delivery Ratio % (Higher is Better)</div>
            <canvas id="chartPDR"></canvas>
        </div>
        <div class="chart-box">
            <div class="chart-header">Throughput - Packets/Sec (Higher is Better)</div>
            <canvas id="chartThroughput"></canvas>
        </div>
        <div class="chart-box">
            <div class="chart-header">Buffer Drops & Packet Loss (Lower is Better)</div>
            <canvas id="chartDrops"></canvas>
        </div>
    </div>

    <div class="section-title">Raw Simulation Data (JSON)</div>
    <pre class="details-pre" id="jsonViewer"></pre>

    <footer>
        <p>Reinforcement Learning Adaptive Routing Protocol Project &bull; Discrete Event Simulation Engine &bull; Pure Python Architecture</p>
    </footer>

    <script>
        const results = {results_json};
        document.getElementById('jsonViewer').textContent = JSON.stringify(results, null, 2);

        const protocols = Object.keys(results);
        const tbody = document.querySelector('#summaryTable tbody');

        let minLat = Infinity, bestLatProto = '';
        let maxPdr = -1, bestPdrProto = '';
        let maxTp = -1, bestTpProto = '';
        let totalPkts = 0;

        protocols.forEach(p => {{
            const s = results[p].summary;
            totalPkts = Math.max(totalPkts, s.packets_generated);

            if (s.average_latency_s > 0 && s.average_latency_s < minLat) {{
                minLat = s.average_latency_s;
                bestLatProto = p;
            }}
            if (s.packet_delivery_ratio_pct > maxPdr) {{
                maxPdr = s.packet_delivery_ratio_pct;
                bestPdrProto = p;
            }}
            if (s.throughput_pps > maxTp) {{
                maxTp = s.throughput_pps;
                bestTpProto = p;
            }}

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${{p}}</strong></td>
                <td>${{s.average_latency_s.toFixed(4)}} s</td>
                <td>${{s.packet_delivery_ratio_pct.toFixed(2)}}%</td>
                <td>${{s.throughput_pps.toFixed(2)}} pps</td>
                <td>${{s.packets_dropped}}</td>
                <td>${{s.average_hops.toFixed(2)}}</td>
            `;
            tbody.appendChild(tr);
        }});

        document.getElementById('bestLatencyProtocol').textContent = bestLatProto;
        document.getElementById('bestLatencyValue').textContent = `${{minLat.toFixed(4)}} s average latency`;
        document.getElementById('bestPdrProtocol').textContent = bestPdrProto;
        document.getElementById('bestPdrValue').textContent = `${{maxPdr.toFixed(2)}}% delivery ratio`;
        document.getElementById('bestTpProtocol').textContent = bestTpProto;
        document.getElementById('bestTpValue').textContent = `${{maxTp.toFixed(2)}} packets / sec`;
        document.getElementById('totalPacketsCount').textContent = totalPkts.toLocaleString();

        // Native HTML5 Canvas Bar Chart Renderer
        function drawBarChart(canvasId, labels, values, color, suffix = '', higherIsBetter = true) {{
            const canvas = document.getElementById(canvasId);
            const ctx = canvas.getContext('2d');
            const dpr = window.devicePixelRatio || 1;
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            ctx.scale(dpr, dpr);

            const w = rect.width;
            const h = rect.height;
            const padding = {{ top: 20, right: 30, bottom: 40, left: 60 }};
            const chartW = w - padding.left - padding.right;
            const chartH = h - padding.top - padding.bottom;

            ctx.clearRect(0, 0, w, h);

            const maxVal = Math.max(...values) * 1.15 || 1.0;
            const barWidth = chartW / labels.length * 0.55;
            const gap = chartW / labels.length;

            // Gridlines
            ctx.strokeStyle = '#334155';
            ctx.lineWidth = 1;
            for (let i = 0; i <= 4; i++) {{
                const y = padding.top + (chartH / 4) * i;
                ctx.beginPath();
                ctx.moveTo(padding.left, y);
                ctx.lineTo(w - padding.right, y);
                ctx.stroke();

                const val = maxVal * (1 - i / 4);
                ctx.fillStyle = '#94a3b8';
                ctx.font = '11px Segoe UI, sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText(val.toFixed(2), padding.left - 8, y + 4);
            }}

            // Bars
            labels.forEach((label, i) => {{
                const val = values[i];
                const barH = (val / maxVal) * chartH;
                const x = padding.left + i * gap + (gap - barWidth) / 2;
                const y = padding.top + chartH - barH;

                // Gradient
                const grad = ctx.createLinearGradient(0, y, 0, y + barH);
                grad.addColorStop(0, color);
                grad.addColorStop(1, '#0f172a');

                ctx.fillStyle = grad;
                ctx.fillRect(x, y, barWidth, barH);
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.5;
                ctx.strokeRect(x, y, barWidth, barH);

                // Value on top
                ctx.fillStyle = '#f8fafc';
                ctx.font = 'bold 11px Segoe UI, sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(val.toFixed(2) + suffix, x + barWidth / 2, y - 6);

                // X-Axis Label
                ctx.fillStyle = '#94a3b8';
                ctx.font = '12px Segoe UI, sans-serif';
                ctx.fillText(label, x + barWidth / 2, h - padding.bottom + 20);
            }});
        }}

        // Render all charts
        const pNames = protocols;
        drawBarChart('chartLatency', pNames, {latency_data}, '#38bdf8', 's', false);
        drawBarChart('chartPDR', pNames, {pdr_data}, '#34d399', '%', true);
        drawBarChart('chartThroughput', pNames, {throughput_data}, '#fbbf24', ' pps', true);
        drawBarChart('chartDrops', pNames, {drops_data}, '#fb7185', '', false);

        window.addEventListener('resize', () => {{
            drawBarChart('chartLatency', pNames, {latency_data}, '#38bdf8', 's', false);
            drawBarChart('chartPDR', pNames, {pdr_data}, '#34d399', '%', true);
            drawBarChart('chartThroughput', pNames, {throughput_data}, '#fbbf24', ' pps', true);
            drawBarChart('chartDrops', pNames, {drops_data}, '#fb7185', '', false);
        }});
    </script>
</body>
</html>
"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_template)

        return output_file


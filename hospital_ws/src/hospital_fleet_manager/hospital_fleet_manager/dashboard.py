#!/usr/bin/env python3
"""Hospital Fleet Manager web dashboard with real-time ROS metrics."""

import json
import os
import threading
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta

import rclpy
from flask import Flask, jsonify, render_template_string, request
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Hospital Fleet Command Center</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #06141f;
      --bg-soft: #0f2433;
      --panel: rgba(8, 27, 39, 0.78);
      --stroke: rgba(112, 187, 222, 0.24);
      --text-main: #eff8ff;
      --text-muted: #a4c2d4;
      --accent: #2ad4c5;
      --warn: #ffb020;
      --busy: #ff6f61;
      --idle: #22c55e;
      --unknown: #8fa9bb;
      --glow: rgba(42, 212, 197, 0.3);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: "Space Grotesk", "Trebuchet MS", "Segoe UI", sans-serif;
      color: var(--text-main);
      background:
        radial-gradient(circle at 12% 18%, rgba(32, 123, 166, 0.33), transparent 35%),
        radial-gradient(circle at 88% 12%, rgba(24, 222, 194, 0.2), transparent 42%),
        radial-gradient(circle at 50% 110%, rgba(255, 176, 32, 0.12), transparent 55%),
        linear-gradient(150deg, #04111b, #071b28 40%, #0a2331 100%);
      min-height: 100vh;
      padding: 28px 16px 40px;
    }

    .shell {
      max-width: 1240px;
      margin: 0 auto;
      display: grid;
      gap: 18px;
    }

    .hero {
      position: relative;
      overflow: hidden;
      border: 1px solid var(--stroke);
      background: linear-gradient(140deg, rgba(14, 46, 64, 0.86), rgba(7, 23, 34, 0.82));
      border-radius: 24px;
      padding: 24px;
      box-shadow: 0 18px 46px rgba(2, 8, 16, 0.45);
    }

    .hero::after {
      content: "";
      position: absolute;
      width: 220px;
      height: 220px;
      top: -90px;
      right: -60px;
      background: radial-gradient(circle, rgba(42, 212, 197, 0.35), transparent 65%);
      filter: blur(4px);
      pointer-events: none;
    }

    .hero h1 {
      margin: 0;
      font-size: clamp(1.6rem, 3.2vw, 2.5rem);
      letter-spacing: 0.02em;
    }

    .hero-meta {
      margin-top: 10px;
      color: var(--text-muted);
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      font-size: 0.96rem;
    }

    .pulse {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(43, 212, 198, 0.35);
      background: rgba(42, 212, 197, 0.1);
      font-weight: 600;
      color: #b8fff7;
    }

    .pulse::before {
      content: "";
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 10px var(--glow);
      animation: pulse 1.4s infinite ease-in-out;
    }

    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 0.8; }
      50% { transform: scale(1.35); opacity: 1; }
    }

    .kpis {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 14px;
    }

    .card {
      border: 1px solid var(--stroke);
      background: var(--panel);
      border-radius: 18px;
      padding: 16px;
      backdrop-filter: blur(4px);
      box-shadow: 0 8px 24px rgba(5, 16, 24, 0.35);
      animation: rise 0.45s ease both;
    }

    @keyframes rise {
      from { transform: translateY(8px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    .kpi-value {
      font-size: 2rem;
      font-weight: 700;
      line-height: 1.1;
      margin-bottom: 4px;
    }

    .kpi-label {
      color: var(--text-muted);
      font-size: 0.88rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .layout {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 16px;
    }

    .grid-two {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .section-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
    }

    .section-title h2 {
      margin: 0;
      font-size: 1.12rem;
      letter-spacing: 0.01em;
    }

    .muted {
      color: var(--text-muted);
      font-size: 0.86rem;
    }

    .robot-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 12px;
    }

    .robot-card {
      border: 1px solid var(--stroke);
      border-radius: 14px;
      background: rgba(8, 30, 44, 0.7);
      padding: 12px;
    }

    .robot-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      gap: 8px;
    }

    .robot-name {
      font-weight: 700;
      letter-spacing: 0.02em;
    }

    .badge {
      font-size: 0.76rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid transparent;
      font-weight: 700;
    }

    .busy { color: #ffd4cf; background: rgba(255, 111, 97, 0.18); border-color: rgba(255, 111, 97, 0.35); }
    .idle { color: #cffff0; background: rgba(34, 197, 94, 0.16); border-color: rgba(34, 197, 94, 0.35); }
    .unknown { color: #d3e5f2; background: rgba(143, 169, 187, 0.18); border-color: rgba(143, 169, 187, 0.3); }

    .robot-meta {
      display: grid;
      gap: 6px;
      font-size: 0.88rem;
      color: var(--text-muted);
    }

    .history {
      max-height: 410px;
      overflow: auto;
      display: grid;
      gap: 8px;
      padding-right: 4px;
    }

    .history-item {
      border: 1px solid var(--stroke);
      border-radius: 10px;
      padding: 10px;
      background: rgba(7, 22, 33, 0.72);
      font-size: 0.9rem;
      line-height: 1.35;
    }

    .ts {
      color: #a8deff;
      font-family: "IBM Plex Mono", "Consolas", monospace;
      font-size: 0.78rem;
      margin-bottom: 4px;
      display: block;
    }

    canvas {
      min-height: 240px;
      max-height: 300px;
    }

    .alert {
      display: none;
      border: 1px solid rgba(255, 176, 32, 0.34);
      background: rgba(255, 176, 32, 0.14);
      color: #ffe8b3;
      border-radius: 12px;
      padding: 10px 12px;
      font-size: 0.92rem;
    }

    @media (max-width: 980px) {
      .layout, .grid-two { grid-template-columns: 1fr; }
      body { padding: 16px 12px 28px; }
      .hero { padding: 18px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Hospital Fleet Command Center</h1>
      <div class="hero-meta">
        <span class="pulse">Live Feed</span>
        <span id="last-update">Last update: waiting for ROS data...</span>
      </div>
    </section>

    <div id="warning" class="alert"></div>

    <section class="kpis">
      <article class="card"><div class="kpi-value" id="total-robots">0</div><div class="kpi-label">Robots</div></article>
      <article class="card"><div class="kpi-value" id="utilization">0%</div><div class="kpi-label">Utilization</div></article>
      <article class="card"><div class="kpi-value" id="busy-robots">0</div><div class="kpi-label">Busy</div></article>
      <article class="card"><div class="kpi-value" id="idle-robots">0</div><div class="kpi-label">Idle</div></article>
      <article class="card"><div class="kpi-value" id="unknown-robots">0</div><div class="kpi-label">Unknown</div></article>
      <article class="card"><div class="kpi-value" id="tasks-10m">0</div><div class="kpi-label">Assignments / 10m</div></article>
    </section>

    <section class="layout">
      <article class="card">
        <div class="section-title">
          <h2>Robot Fleet</h2>
          <span class="muted" id="robot-count-label">0 robots</span>
        </div>
        <div id="robot-grid" class="robot-grid"></div>
      </article>

      <article class="card">
        <div class="section-title">
          <h2>Recent Assignments</h2>
          <span class="muted">Newest first</span>
        </div>
        <div id="history" class="history"></div>
      </article>
    </section>

    <section class="grid-two">
      <article class="card">
        <div class="section-title">
          <h2>Status Split</h2>
          <span class="muted">Busy vs Idle vs Unknown</span>
        </div>
        <canvas id="statusChart"></canvas>
      </article>
      <article class="card">
        <div class="section-title">
          <h2>Assignments by Robot</h2>
          <span class="muted">Last 50 assignments</span>
        </div>
        <canvas id="loadChart"></canvas>
      </article>
    </section>
  </div>

  <script>
    const REFRESH_MS = 2000;
    let statusChart = null;
    let loadChart = null;

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    function statusClass(state) {
      if (state === 'busy') return 'busy';
      if (state === 'idle') return 'idle';
      return 'unknown';
    }

    function showWarning(msg) {
      const box = document.getElementById('warning');
      if (!msg) {
        box.style.display = 'none';
        box.textContent = '';
        return;
      }
      box.style.display = 'block';
      box.textContent = msg;
    }

    function parseRobotName(assignment) {
      if (!assignment || !assignment.includes(':')) return 'unknown';
      return assignment.split(':', 1)[0].trim();
    }

    function renderRobots(robots) {
      const grid = document.getElementById('robot-grid');
      const entries = Object.entries(robots || {});
      document.getElementById('robot-count-label').textContent = `${entries.length} robots`;

      if (!entries.length) {
        grid.innerHTML = '<div class="muted">No robot status data available yet.</div>';
        return;
      }

      grid.innerHTML = entries.map(([name, data]) => {
        const state = data.status || 'unknown';
        const task = data.current_task || 'None';
        const location = data.location || 'Unknown';
        return `
          <article class="robot-card">
            <div class="robot-head">
              <div class="robot-name">${escapeHtml(name)}</div>
              <span class="badge ${statusClass(state)}">${escapeHtml(state)}</span>
            </div>
            <div class="robot-meta">
              <span><strong>Task:</strong> ${escapeHtml(task)}</span>
              <span><strong>Location:</strong> ${escapeHtml(location)}</span>
            </div>
          </article>
        `;
      }).join('');
    }

    function renderHistory(history) {
      const root = document.getElementById('history');
      if (!history || !history.length) {
        root.innerHTML = '<div class="muted">No assignments published yet.</div>';
        return;
      }

      root.innerHTML = history.slice().reverse().map(item => `
        <div class="history-item">
          <span class="ts">${escapeHtml(item.timestamp || '-')}</span>
          <span>${escapeHtml(item.assignment || '-')}</span>
        </div>
      `).join('');
    }

    function drawStatusChart(stats) {
      const ctx = document.getElementById('statusChart').getContext('2d');
      const values = [stats.busy_robots || 0, stats.idle_robots || 0, stats.unknown_robots || 0];
      if (statusChart) statusChart.destroy();

      statusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Busy', 'Idle', 'Unknown'],
          datasets: [{
            data: values,
            backgroundColor: ['#ff6f61', '#22c55e', '#8fa9bb'],
            borderColor: 'rgba(239, 248, 255, 0.3)',
            borderWidth: 1.5
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: '#d7edf9' }
            }
          }
        }
      });
    }

    function drawLoadChart(history) {
      const ctx = document.getElementById('loadChart').getContext('2d');
      const counter = {};
      (history || []).slice(-50).forEach(item => {
        const robot = parseRobotName(item.assignment || '');
        counter[robot] = (counter[robot] || 0) + 1;
      });

      const labels = Object.keys(counter);
      const values = Object.values(counter);

      if (loadChart) loadChart.destroy();
      loadChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Assignments',
            data: values,
            backgroundColor: 'rgba(42, 212, 197, 0.55)',
            borderColor: '#2ad4c5',
            borderWidth: 1.4,
            borderRadius: 8
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              ticks: { color: '#c2e0f0' },
              grid: { color: 'rgba(143, 169, 187, 0.2)' }
            },
            x: {
              ticks: { color: '#c2e0f0' },
              grid: { display: false }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    function applyStats(stats) {
      document.getElementById('total-robots').textContent = stats.total_robots || 0;
      document.getElementById('busy-robots').textContent = stats.busy_robots || 0;
      document.getElementById('idle-robots').textContent = stats.idle_robots || 0;
      document.getElementById('unknown-robots').textContent = stats.unknown_robots || 0;
      document.getElementById('utilization').textContent = `${stats.utilization_percent || 0}%`;
      document.getElementById('tasks-10m').textContent = stats.tasks_last_10m || 0;
    }

    async function updateDashboard() {
      try {
        const [statusResp, historyResp, statsResp] = await Promise.all([
          fetch('/status'),
          fetch('/history?limit=50'),
          fetch('/stats')
        ]);

        const [statusData, historyData, statsData] = await Promise.all([
          statusResp.json(),
          historyResp.json(),
          statsResp.json()
        ]);

        if (statusData.error || historyData.error || statsData.error) {
          showWarning(statusData.error || historyData.error || statsData.error || 'Dashboard data unavailable');
          return;
        }

        showWarning('');
        document.getElementById('last-update').textContent = `Last update: ${statusData.timestamp} (${statusData.source_age_seconds}s ago)`;

        renderRobots(statusData.robots || {});
        renderHistory(historyData.history || []);
        applyStats(statsData);
        drawStatusChart(statsData);
        drawLoadChart(historyData.history || []);
      } catch (error) {
        showWarning(`Live update failed: ${error.message}`);
      }
    }

    updateDashboard();
    setInterval(updateDashboard, REFRESH_MS);
  </script>
</body>
</html>
"""


class DashboardNode(Node):
    """ROS node that stores a thread-safe in-memory dashboard state."""

    def __init__(self):
        super().__init__('dashboard_node')
        self._lock = threading.Lock()
        self._robot_status = {}
        self._task_history = []
        self._max_history = 200
        self._last_update = datetime.now()

        self.create_subscription(String, 'robot_status', self._status_callback, 10)
        self.create_subscription(String, 'task_assignments', self._assignment_callback, 10)

    def _status_callback(self, msg):
        try:
            payload = json.loads(msg.data)
            if not isinstance(payload, dict):
                raise ValueError('robot_status payload must be a JSON object')
            with self._lock:
                self._robot_status = payload
                self._last_update = datetime.now()
        except (json.JSONDecodeError, ValueError) as exc:
            self.get_logger().error(f'Invalid robot_status payload: {exc}')

    def _assignment_callback(self, msg):
        item = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'assignment': msg.data,
        }
        with self._lock:
            self._task_history.append(item)
            if len(self._task_history) > self._max_history:
                self._task_history = self._task_history[-self._max_history :]

    def snapshot(self):
        with self._lock:
            return {
                'robots': deepcopy(self._robot_status),
                'history': deepcopy(self._task_history),
                'last_update': self._last_update,
            }


dashboard_node = None


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/health')
def health():
    return jsonify({'ready': dashboard_node is not None})


@app.route('/status')
def status():
    if dashboard_node is None:
        return jsonify({'error': 'Dashboard not initialized'}), 503

    snap = dashboard_node.snapshot()
    age = max(0, int((datetime.now() - snap['last_update']).total_seconds()))
    return jsonify(
        {
            'robots': snap['robots'],
            'timestamp': snap['last_update'].strftime('%H:%M:%S'),
            'source_age_seconds': age,
        }
    )


@app.route('/history')
def history():
    if dashboard_node is None:
        return jsonify({'error': 'Dashboard not initialized'}), 503

    limit = request.args.get('limit', default=20, type=int)
    limit = 20 if limit is None else max(1, min(200, limit))
    snap = dashboard_node.snapshot()
    return jsonify({'history': snap['history'][-limit:]})


@app.route('/stats')
def stats():
    if dashboard_node is None:
        return jsonify({'error': 'Dashboard not initialized'}), 503

    snap = dashboard_node.snapshot()
    robots = snap['robots']
    history_items = snap['history']

    busy = sum(1 for status in robots.values() if status.get('status') == 'busy')
    idle = sum(1 for status in robots.values() if status.get('status') == 'idle')
    unknown = max(0, len(robots) - busy - idle)

    utilization = 0
    if robots:
        utilization = round((busy / len(robots)) * 100)

    cutoff = datetime.now() - timedelta(minutes=10)
    tasks_last_10m = 0
    robot_load = Counter()

    for item in history_items:
        try:
            ts = datetime.strptime(item.get('timestamp', ''), '%H:%M:%S').time()
            ts_dt = datetime.combine(datetime.now().date(), ts)
            if ts_dt < cutoff and datetime.now().hour == 0:
                ts_dt = ts_dt + timedelta(days=1)
            if ts_dt >= cutoff:
                tasks_last_10m += 1
        except ValueError:
            pass

        assignment = item.get('assignment', '')
        if ':' in assignment:
            robot = assignment.split(':', 1)[0].strip()
            if robot:
                robot_load[robot] += 1

    return jsonify(
        {
            'total_robots': len(robots),
            'busy_robots': busy,
            'idle_robots': idle,
            'unknown_robots': unknown,
            'total_tasks': len(history_items),
            'tasks_last_10m': tasks_last_10m,
            'utilization_percent': utilization,
            'top_robot': robot_load.most_common(1)[0][0] if robot_load else 'n/a',
        }
    )


def ros_thread_main():
    global dashboard_node
    rclpy.init()
    dashboard_node = DashboardNode()
    try:
        rclpy.spin(dashboard_node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if dashboard_node is not None:
            dashboard_node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def main():
    thread = threading.Thread(target=ros_thread_main, daemon=True)
    thread.start()
    time.sleep(1.5)
    port = int(os.environ.get('DASHBOARD_PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()

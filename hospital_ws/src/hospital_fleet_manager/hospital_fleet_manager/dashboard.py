#!/usr/bin/env python3
"""
Hospital Fleet Manager Web Dashboard
Real-time monitoring interface for robot fleet operations
"""

import json
import threading
import time
from datetime import datetime

import rclpy
from flask import Flask, render_template_string
from rclpy.node import Node
from std_msgs.msg import String

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Hospital Robot Fleet Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0b3d91 0%, #2f80ed 100%);
            color: #f8f9fa;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            margin-bottom: 24px;
            font-size: 2.7rem;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 18px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 16px;
            padding: 18px;
            min-height: 120px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        }
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .stat-label {
            font-size: 0.94rem;
            opacity: 0.8;
        }
        .section {
            margin-bottom: 24px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 18px;
            padding: 22px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14);
        }
        .section h2 {
            margin-top: 0;
            margin-bottom: 16px;
            color: #ffffff;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 12px;
        }
        th,
        td {
            padding: 14px 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        }
        th {
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.88rem;
        }
        .status-busy {
            color: #ff6b6b;
            font-weight: 700;
        }
        .status-idle {
            color: #51cf66;
            font-weight: 700;
        }
        .task-history {
            max-height: 280px;
            overflow-y: auto;
        }
        .task-item {
            background: rgba(255, 255, 255, 0.08);
            margin-bottom: 10px;
            padding: 12px;
            border-radius: 12px;
            font-size: 0.95rem;
            line-height: 1.4;
        }
        .timestamp {
            color: #a5d8ff;
            font-weight: 700;
            margin-right: 10px;
        }
        #last-update {
            text-align: center;
            margin-bottom: 20px;
            opacity: 0.9;
        }
        .chart-container {
            position: relative;
            min-height: 300px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Hospital Robot Fleet Dashboard</h1>
        <div id="last-update">Last update: loading...</div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="total-robots">-</div>
                <div class="stat-label">Total Robots</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="busy-robots">-</div>
                <div class="stat-label">Busy Robots</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="idle-robots">-</div>
                <div class="stat-label">Idle Robots</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="total-tasks">-</div>
                <div class="stat-label">Task History Length</div>
            </div>
        </div>

        <div class="section">
            <h2>Robot Status</h2>
            <table>
                <thead>
                    <tr>
                        <th>Robot</th>
                        <th>Status</th>
                        <th>Current Task</th>
                        <th>Location</th>
                    </tr>
                </thead>
                <tbody id="robot-table-body">
                    <tr><td colspan="4">Loading robot data...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Recent Assignments</h2>
            <div id="task-history" class="task-history">Loading task history...</div>
        </div>

        <div class="section">
            <h2>Fleet Activity</h2>
            <div class="chart-container">
                <canvas id="activityChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        let activityChart;

        function updateDashboard() {
            fetch('/stats')
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        document.getElementById('total-robots').textContent = data.total_robots;
                        document.getElementById('busy-robots').textContent = data.busy_robots;
                        document.getElementById('idle-robots').textContent = data.idle_robots;
                        document.getElementById('total-tasks').textContent = data.total_tasks;
                        updateChart(data);
                    }
                })
                .catch(console.error);

            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        updateRobotTable(data.robots);
                        document.getElementById('last-update').textContent = `Last update: ${data.timestamp}`;
                    }
                })
                .catch(console.error);

            fetch('/history')
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        updateTaskHistory(data.history);
                    }
                })
                .catch(console.error);
        }

        function updateRobotTable(robots) {
            const body = document.getElementById('robot-table-body');
            body.innerHTML = '';
            const entries = Object.entries(robots || {});
            if (!entries.length) {
                body.innerHTML = '<tr><td colspan="4">No robot data available</td></tr>';
                return;
            }

            for (const [robot, status] of entries) {
                const row = document.createElement('tr');
                const statusClass = status.status === 'busy' ? 'status-busy' : 'status-idle';
                row.innerHTML = `
                    <td>${robot}</td>
                    <td class="${statusClass}">${status.status || 'unknown'}</td>
                    <td>${status.current_task || 'None'}</td>
                    <td>${status.location || 'Unknown'}</td>
                `;
                body.appendChild(row);
            }
        }

        function updateTaskHistory(history) {
            const container = document.getElementById('task-history');
            container.innerHTML = '';
            if (!history || history.length === 0) {
                container.textContent = 'No assignments yet.';
                return;
            }

            history.slice(-20).reverse().forEach(item => {
                const div = document.createElement('div');
                div.className = 'task-item';
                div.innerHTML = `<span class="timestamp">${item.timestamp}</span> ${item.assignment}`;
                container.appendChild(div);
            });
        }

        function updateChart(data) {
            const ctx = document.getElementById('activityChart').getContext('2d');
            if (activityChart) {
                activityChart.destroy();
            }
            activityChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Busy', 'Idle'],
                    datasets: [{
                        data: [data.busy_robots, data.idle_robots],
                        backgroundColor: ['#ff6b6b', '#51cf66'],
                        borderColor: ['rgba(255,255,255,0.4)', 'rgba(255,255,255,0.4)'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#f8f9fa'
                            }
                        }
                    }
                }
            });
        }

        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

class DashboardNode(Node):
    def __init__(self):
        super().__init__('dashboard_node')
        self.robot_status = {}
        self.task_history = []
        self.last_update = datetime.now()

        self.create_subscription(String, 'robot_status', self._status_callback, 10)
        self.create_subscription(String, 'task_assignments', self._assignment_callback, 10)

    def _status_callback(self, msg):
        try:
            self.robot_status = json.loads(msg.data)
            self.last_update = datetime.now()
        except json.JSONDecodeError:
            self.get_logger().error('Invalid JSON in robot_status message')

    def _assignment_callback(self, msg):
        assignment = msg.data
        self.task_history.append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'assignment': assignment
        })
        if len(self.task_history) > 50:
            self.task_history = self.task_history[-50:]


dashboard_node = None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    return {
        'robots': dashboard_node.robot_status,
        'timestamp': dashboard_node.last_update.strftime('%H:%M:%S')
    }

@app.route('/history')
def history():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    return {'history': dashboard_node.task_history[-20:]}

@app.route('/stats')
def stats():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    robots = dashboard_node.robot_status
    return {
        'total_robots': len(robots),
        'busy_robots': sum(1 for status in robots.values() if status.get('status') == 'busy'),
        'idle_robots': sum(1 for status in robots.values() if status.get('status') == 'idle'),
        'total_tasks': len(dashboard_node.task_history)
    }


def ros_thread_main():
    global dashboard_node
    rclpy.init()
    dashboard_node = DashboardNode()
    try:
        rclpy.spin(dashboard_node)
    except KeyboardInterrupt:
        pass
    finally:
        dashboard_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    thread = threading.Thread(target=ros_thread_main, daemon=True)
    thread.start()
    time.sleep(2)
    app.run(host='0.0.0.0', port=5000, debug=False)

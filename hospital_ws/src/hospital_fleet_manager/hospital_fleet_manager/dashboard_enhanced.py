#!/usr/bin/env python3
"""
Enhanced Hospital Fleet Manager Web Dashboard
Real-time monitoring with specialization, battery, and priority tracking
"""

import json
import threading
import time
from datetime import datetime

import rclpy
from flask import Flask, render_template_string, jsonify
from rclpy.node import Node
from std_msgs.msg import String

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Hospital Robot Fleet Dashboard - Enhanced</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0b3d91 0%, #2f80ed 100%);
            color: #f8f9fa;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.8rem;
        }
        .subtitle {
            text-align: center;
            opacity: 0.9;
            margin-bottom: 20px;
            font-size: 1.1rem;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 14px;
            padding: 16px;
            min-height: 100px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
            transition: transform 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-number {
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.8;
        }
        .section {
            margin-bottom: 24px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14);
        }
        .section h2 {
            margin-top: 0;
            margin-bottom: 16px;
            font-size: 1.5rem;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 12px;
            font-size: 0.95rem;
        }
        th, td {
            padding: 12px 10px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        }
        th {
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.85rem;
            background: rgba(255, 255, 255, 0.04);
        }
        .robot-name {
            font-weight: 600;
            color: #a5d8ff;
        }
        .spec-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .spec-delivery { background: rgba(100, 200, 255, 0.3); }
        .spec-cleaning { background: rgba(100, 255, 200, 0.3); }
        .spec-patient_mover { background: rgba(255, 100, 100, 0.3); }
        .spec-lab_courier { background: rgba(200, 100, 255, 0.3); }
        .spec-heavy_supply { background: rgba(255, 200, 100, 0.3); }
        .spec-emergency_response { background: rgba(255, 100, 100, 0.4); }
        .spec-general { background: rgba(150, 150, 150, 0.3); }
        .status-busy { color: #ff6b6b; font-weight: 700; }
        .status-idle { color: #51cf66; font-weight: 700; }
        .battery-bar {
            display: inline-block;
            width: 60px;
            height: 16px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            overflow: hidden;
            vertical-align: middle;
            margin-right: 6px;
        }
        .battery-fill {
            height: 100%;
            background: linear-gradient(90deg, #51cf66, #94d82d);
            transition: width 0.3s, background 0.3s;
        }
        .battery-low .battery-fill { background: #ff6b6b; }
        .battery-medium .battery-fill { background: #ffd43b; }
        .priority-tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .priority-critical { background: #ff6b6b; }
        .priority-high { background: #ffd43b; }
        .priority-medium { background: #a5d8ff; }
        .priority-low { background: #b3b3b3; }
        .task-history {
            max-height: 350px;
            overflow-y: auto;
        }
        .task-item {
            background: rgba(255, 255, 255, 0.08);
            margin-bottom: 8px;
            padding: 10px;
            border-radius: 10px;
            font-size: 0.9rem;
            line-height: 1.4;
            border-left: 3px solid #a5d8ff;
        }
        .task-item.generated {
            border-left-color: #94d82d;
        }
        .timestamp {
            color: #a5d8ff;
            font-weight: 600;
            margin-right: 10px;
        }
        #last-update {
            text-align: center;
            margin-bottom: 16px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            opacity: 0.9;
            font-size: 0.95rem;
        }
        .chart-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .chart-container {
            position: relative;
            min-height: 250px;
        }
        .chart-container canvas {
            max-height: 250px;
        }
        @media (max-width: 1024px) {
            .chart-row {
                grid-template-columns: 1fr;
            }
        }
        .legend-item {
            display: inline-block;
            margin-right: 20px;
            font-size: 0.9rem;
        }
        .scroll-indicator {
            text-align: right;
            font-size: 0.8rem;
            opacity: 0.6;
            margin-top: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Hospital Robot Fleet</h1>
        <div class="subtitle">Advanced Fleet Management & Monitoring System</div>
        <div id="last-update">Last update: loading...</div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="total-robots">-</div>
                <div class="stat-label">Total Robots</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="busy-robots">-</div>
                <div class="stat-label">Robots Busy</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="idle-robots">-</div>
                <div class="stat-label">Robots Idle</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="avg-battery">-</div>
                <div class="stat-label">Avg Battery %</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="total-tasks">-</div>
                <div class="stat-label">Tasks Assigned</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="pending-tasks">-</div>
                <div class="stat-label">Pending Tasks</div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Robot Status & Specialization</h2>
            <table>
                <thead>
                    <tr>
                        <th>Robot ID</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Battery</th>
                        <th>Current Task</th>
                        <th>Location</th>
                    </tr>
                </thead>
                <tbody id="robot-table-body">
                    <tr><td colspan="6" style="text-align: center;">Loading robot data...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📈 Fleet Analytics</h2>
            <div class="chart-row">
                <div class="chart-container">
                    <h3 style="margin-top: 0; font-size: 1.1rem;">Robot Status Distribution</h3>
                    <canvas id="statusChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 style="margin-top: 0; font-size: 1.1rem;">Fleet Specialization</h3>
                    <canvas id="specializationChart"></canvas>
                </div>
            </div>
            <div class="chart-row">
                <div class="chart-container">
                    <h3 style="margin-top: 0; font-size: 1.1rem;">Battery Health</h3>
                    <canvas id="batteryChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 style="margin-top: 0; font-size: 1.1rem;">Task Priority Distribution</h3>
                    <canvas id="priorityChart"></canvas>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📋 Recent Task Assignments</h2>
            <div id="task-history" class="task-history">Loading task history...</div>
            <div class="scroll-indicator">↓ Scroll for older assignments ↓</div>
        </div>
    </div>

    <script>
        let statusChart, specializationChart, batteryChart, priorityChart;

        function updateDashboard() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        document.getElementById('total-robots').textContent = data.total_robots;
                        document.getElementById('busy-robots').textContent = data.busy_robots;
                        document.getElementById('idle-robots').textContent = data.idle_robots;
                        document.getElementById('avg-battery').textContent = (data.avg_battery || 0).toFixed(1);
                        document.getElementById('total-tasks').textContent = data.total_tasks;
                        document.getElementById('pending-tasks').textContent = data.pending_tasks;
                        updateCharts(data);
                    }
                })
                .catch(console.error);

            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        updateRobotTable(data.robots);
                        document.getElementById('last-update').textContent = `Last update: ${data.timestamp}`;
                    }
                })
                .catch(console.error);

            fetch('/api/history')
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
            const entries = Object.entries(robots || {}).sort((a, b) => a[0].localeCompare(b[0]));
            
            if (!entries.length) {
                body.innerHTML = '<tr><td colspan="6" style="text-align: center;">No robot data available</td></tr>';
                return;
            }

            entries.forEach(([robot, status]) => {
                const row = document.createElement('tr');
                const statusClass = status.status === 'busy' ? 'status-busy' : 'status-idle';
                const battery = status.battery || 'N/A';
                const batteryPercentage = typeof battery === 'number' ? battery.toFixed(1) : battery;
                
                let batteryClass = '';
                if (typeof battery === 'number') {
                    batteryClass = battery < 30 ? 'battery-low' : (battery < 60 ? 'battery-medium' : '');
                }
                
                const specType = status.type || 'general';
                const specBadge = `<span class="spec-badge spec-${specType}">${specType}</span>`;
                
                const taskDisplay = status.current_task ? `<span class="priority-tag priority-${status.task_priority || 'medium'}">${status.task_priority}</span> ${status.current_task}` : 'None';
                
                row.innerHTML = `
                    <td><span class="robot-name">${robot}</span></td>
                    <td>${specBadge}</td>
                    <td class="${statusClass}">${status.status || 'unknown'}</td>
                    <td class="${batteryClass}">
                        <div class="battery-bar"><div class="battery-fill" style="width: ${Math.min(100, Math.max(0, parseFloat(batteryPercentage) || 0))}%"></div></div>
                        ${batteryPercentage}%
                    </td>
                    <td>${taskDisplay}</td>
                    <td>${status.location || 'Unknown'}</td>
                `;
                body.appendChild(row);
            });
        }

        function updateTaskHistory(history) {
            const container = document.getElementById('task-history');
            container.innerHTML = '';
            if (!history || history.length === 0) {
                container.textContent = 'No assignments yet.';
                return;
            }

            history.slice(-30).reverse().forEach(item => {
                const div = document.createElement('div');
                div.className = 'task-item' + (item.generated ? ' generated' : '');
                const priorityBadge = item.priority ? `<span class="priority-tag priority-${item.priority}">${item.priority}</span>` : '';
                div.innerHTML = `<span class="timestamp">${item.timestamp}</span> ${priorityBadge} ${item.assignment}`;
                container.appendChild(div);
            });
        }

        function updateCharts(data) {
            updateStatusChart(data);
            updateSpecializationChart(data);
            updateBatteryChart(data);
            updatePriorityChart(data);
        }

        function updateStatusChart(data) {
            const ctx = document.getElementById('statusChart').getContext('2d');
            if (statusChart) statusChart.destroy();
            
            statusChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Busy', 'Idle'],
                    datasets: [{
                        data: [data.busy_robots, data.idle_robots],
                        backgroundColor: ['#ff6b6b', '#51cf66'],
                        borderColor: ['rgba(255,255,255,0.3)', 'rgba(255,255,255,0.3)'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#f8f9fa', font: { weight: 'bold' } } }
                    }
                }
            });
        }

        function updateSpecializationChart(data) {
            const ctx = document.getElementById('specializationChart').getContext('2d');
            if (specializationChart) specializationChart.destroy();
            
            const specs = data.specialization_counts || {};
            const labels = Object.keys(specs);
            const values = Object.values(specs);
            const colors = {
                'delivery': '#64c8ff',
                'cleaning': '#64ffc8',
                'patient_mover': '#ff6464',
                'lab_courier': '#c864ff',
                'heavy_supply': '#ffc864',
                'emergency_response': '#ff6b6b',
                'general': '#999999'
            };
            
            specializationChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels.map(l => l.replace(/_/g, ' ').toUpperCase()),
                    datasets: [{
                        label: 'Robot Count',
                        data: values,
                        backgroundColor: labels.map(l => colors[l] || '#999999'),
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { ticks: { color: '#f8f9fa' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                    }
                }
            });
        }

        function updateBatteryChart(data) {
            const ctx = document.getElementById('batteryChart').getContext('2d');
            if (batteryChart) batteryChart.destroy();
            
            const batteries = data.battery_ranges || {};
            batteryChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['High (75-100%)', 'Medium (50-74%)', 'Low (25-49%)', 'Critical (<25%)'],
                    datasets: [{
                        label: 'Robot Count',
                        data: [
                            batteries.high || 0,
                            batteries.medium || 0,
                            batteries.low || 0,
                            batteries.critical || 0
                        ],
                        backgroundColor: ['#51cf66', '#ffd43b', '#ff8787', '#ff6b6b'],
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { ticks: { color: '#f8f9fa' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                    }
                }
            });
        }

        function updatePriorityChart(data) {
            const ctx = document.getElementById('priorityChart').getContext('2d');
            if (priorityChart) priorityChart.destroy();
            
            const priorities = data.priority_counts || {};
            const priorityOrder = ['critical', 'high', 'medium', 'low'];
            const labels = priorityOrder.filter(p => priorities[p] > 0);
            const values = labels.map(p => priorities[p] || 0);
            const colorMap = { 'critical': '#ff6b6b', 'high': '#ffd43b', 'medium': '#a5d8ff', 'low': '#b3b3b3' };
            
            priorityChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
                    datasets: [{
                        data: values,
                        backgroundColor: labels.map(l => colorMap[l]),
                        borderColor: ['rgba(255,255,255,0.3)'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#f8f9fa', font: { weight: 'bold' } } }
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

class EnhancedDashboardNode(Node):
    def __init__(self):
        super().__init__('enhanced_dashboard_node')
        self.robot_status = {}
        self.task_history = []
        self.last_update = datetime.now()
        self.total_tasks_assigned = 0
        self.pending_tasks = 0

        self.create_subscription(String, 'robot_status', self._status_callback, 10)
        self.create_subscription(String, 'task_assignments', self._assignment_callback, 10)

    def _status_callback(self, msg):
        try:
            self.robot_status = json.loads(msg.data)
            self.last_update = datetime.now()
        except json.JSONDecodeError:
            self.get_logger().error('Invalid JSON in robot_status message')

    def _assignment_callback(self, msg):
        try:
            data = json.loads(msg.data) if msg.data.startswith('{') else {'task': msg.data}
            self.task_history.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'assignment': data.get('task', msg.data),
                'robot': data.get('robot', 'Unknown'),
                'priority': data.get('priority', 'medium'),
                'generated': data.get('generated', False)
            })
            self.total_tasks_assigned += 1
            if len(self.task_history) > 100:
                self.task_history = self.task_history[-100:]
        except:
            self.task_history.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'assignment': msg.data,
                'robot': 'Unknown',
                'priority': 'medium',
                'generated': False
            })


dashboard_node = None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def status():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    return {
        'robots': dashboard_node.robot_status,
        'timestamp': dashboard_node.last_update.strftime('%H:%M:%S')
    }

@app.route('/api/history')
def history():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    return {'history': dashboard_node.task_history[-30:]}

@app.route('/api/stats')
def stats():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    
    robots = dashboard_node.robot_status
    total_robots = len(robots)
    busy_robots = sum(1 for status in robots.values() if status.get('status') == 'busy')
    idle_robots = total_robots - busy_robots
    
    # Calculate battery stats
    batteries = [status.get('battery', 100.0) for status in robots.values() if isinstance(status.get('battery'), (int, float))]
    avg_battery = sum(batteries) / len(batteries) if batteries else 0.0
    
    # Battery ranges
    battery_ranges = {
        'high': sum(1 for b in batteries if b >= 75),
        'medium': sum(1 for b in batteries if 50 <= b < 75),
        'low': sum(1 for b in batteries if 25 <= b < 50),
        'critical': sum(1 for b in batteries if b < 25)
    }
    
    # Specialization counts
    specialization_counts = {}
    for status in robots.values():
        spec = status.get('type', 'general')
        specialization_counts[spec] = specialization_counts.get(spec, 0) + 1
    
    # Priority counts from recent tasks
    priority_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for task in dashboard_node.task_history:
        priority = task.get('priority', 'medium')
        if priority in priority_counts:
            priority_counts[priority] += 1
    
    return {
        'total_robots': total_robots,
        'busy_robots': busy_robots,
        'idle_robots': idle_robots,
        'avg_battery': avg_battery,
        'total_tasks': dashboard_node.total_tasks_assigned,
        'pending_tasks': dashboard_node.pending_tasks,
        'battery_ranges': battery_ranges,
        'specialization_counts': specialization_counts,
        'priority_counts': priority_counts
    }


def ros_thread_main():
    global dashboard_node
    rclpy.init()
    dashboard_node = EnhancedDashboardNode()
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

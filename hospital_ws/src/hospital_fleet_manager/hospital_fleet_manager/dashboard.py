import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import threading
import json
from flask import Flask, render_template_string

app = Flask(__name__)
robot_status = {}

def ros_spin():
    rclpy.init()
    node = Node('dashboard_bridge')
    sub = node.create_subscription(String, 'robot_status', lambda msg: update_status(msg.data), 10)
    rclpy.spin(node)

def update_status(data):
    global robot_status
    robot_status = json.loads(data)

HTML_TEMPLATE = &#34;&#34;&#34;
<!DOCTYPE html>
<html>
<head>
<title>Hospital Robot Fleet Dashboard</title>
<script>
function updateTable() {
    fetch('/status').then(r => r.json()).then(data => {
        let table = '<table border=1><tr><th>Robot</th><th>Status</th><th>Task</th><th>Location</th></tr>';
        for (let robot in data) {
            table += `<tr><td>${robot}</td><td>${data[robot].status}</td><td>${data[robot].current_task || '-'}</td><td>${data[robot].location || 'unknown'}</td></tr>`;
        }
        table += '</table>';
        document.getElementById('table').innerHTML = table;
    });
}
setInterval(updateTable, 5000);
updateTable();
</script>
</head>
<body>
<h1>AI Hospital Robot Fleet Status</h1>
<div id='table'>Loading...</div>
</body>
</html>&#34;&#34;&#34;

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    return robot_status

if __name__ == '__main__':
    ros_thread = threading.Thread(target=ros_spin, daemon=True)
    ros_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=False)

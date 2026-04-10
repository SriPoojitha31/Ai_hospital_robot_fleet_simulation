#!/bin/bash

# Run Visual Dashboard with Hospital Map and Robot Tracking
# Automatically finds available port and launches dashboard
# Requires: ROS 2 Jazzy, Flask, and other dependencies

# Source ROS setup
source /opt/ros/jazzy/setup.bash

# Activate Python virtual environment
if [ -d "$HOME/venv-ai-hospital" ]; then
    source "$HOME/venv-ai-hospital/bin/activate"
fi

# Navigate to workspace
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORKSPACE_DIR"

# Export Python path
export PYTHONPATH="${WORKSPACE_DIR}/src:${PYTHONPATH}"
export ROS_LOG_DIR="${WORKSPACE_DIR}/.ros/log"
mkdir -p "${ROS_LOG_DIR}"

# Find available port starting from 5000
find_available_port() {
    local port=5000
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; do
        port=$((port + 1))
        if [ $port -gt 5100 ]; then
            echo "5000"
            return
        fi
    done
    echo $port
}

AVAILABLE_PORT=$(find_available_port)

echo "🏥 Starting Visual Dashboard with Hospital Map..."
echo "📱 Dashboard will be available at: http://localhost:${AVAILABLE_PORT}"
echo "⏹️  Press Ctrl+C to stop"
echo ""

# Set port environment variable and run dashboard
export DASHBOARD_PORT=$AVAILABLE_PORT
python3 -u src/hospital_fleet_manager/hospital_fleet_manager/dashboard_visual.py

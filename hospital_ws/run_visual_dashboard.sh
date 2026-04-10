#!/bin/bash

# Run Visual Dashboard with Hospital Map and Robot Tracking
# Requires: ROS 2 Jazzy, Flask, and other dependencies

set -e

# Source ROS setup
source /opt/ros/jazzy/setup.bash

# Activate Python virtual environment
if [ -d "$HOME/venv-ai-hospital" ]; then
    source $HOME/venv-ai-hospital/bin/activate
fi

# Navigate to workspace
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Export Python path
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

echo "🏥 Starting Visual Dashboard with Hospital Map..."
echo "📱 Dashboard will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

# Run the visual dashboard
python3 -u src/hospital_fleet_manager/hospital_fleet_manager/dashboard_visual.py

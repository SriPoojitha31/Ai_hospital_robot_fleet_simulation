#!/bin/bash
# Launch fleet scheduler node

WORKSPACE_ROOT="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="${WORKSPACE_ROOT}/src/hospital_fleet_manager"

# Activate venv which has scipy/networkx
source ${HOME}/venv-ai-hospital/bin/activate

# Source ROS in venv environment
source /opt/ros/jazzy/setup.bash

# Export package path
export PYTHONPATH="${PACKAGE_DIR}:${PYTHONPATH}"

# Use python from venv
exec python3 "${PACKAGE_DIR}/hospital_fleet_manager/fleet_scheduler.py"

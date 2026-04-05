#!/bin/bash
# Launch fleet scheduler node
set -eo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="${WORKSPACE_ROOT}/src/hospital_fleet_manager"
VENV_PATH="${HOME}/venv-ai-hospital"

if [[ ! -d "${VENV_PATH}" ]]; then
  echo "Virtual environment not found at ${VENV_PATH}"
  echo "Create it with: python3 -m venv ${VENV_PATH}"
  exit 1
fi

# Activate venv which has scipy/networkx
source "${VENV_PATH}/bin/activate"

# Source ROS in venv environment
source /opt/ros/jazzy/setup.bash

# Keep ROS logs in workspace to avoid permission issues on restricted systems.
export ROS_LOG_DIR="${WORKSPACE_ROOT}/.ros/log"
mkdir -p "${ROS_LOG_DIR}"

# Export package path
export PYTHONPATH="${PACKAGE_DIR}:${PYTHONPATH}"

# Use python from venv
exec python3 "${PACKAGE_DIR}/hospital_fleet_manager/fleet_scheduler.py"

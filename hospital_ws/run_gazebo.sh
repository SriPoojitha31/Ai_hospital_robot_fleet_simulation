#!/bin/bash
# Launch Gazebo hospital simulation
set -eo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="${WORKSPACE_ROOT}/src/hospital_fleet_manager"
VENV_PATH="${HOME}/venv-ai-hospital"

if [[ ! -d "${VENV_PATH}" ]]; then
  echo "Virtual environment not found at ${VENV_PATH}"
  exit 1
fi

source "${VENV_PATH}/bin/activate"
source /opt/ros/jazzy/setup.bash
[[ -f "${WORKSPACE_ROOT}/install/setup.bash" ]] && source "${WORKSPACE_ROOT}/install/setup.bash"

export PYTHONPATH="${PACKAGE_DIR}:${PYTHONPATH}"

echo "Launching Gazebo hospital simulation..."
exec ros2 launch hospital_fleet_manager gazebo_hospital.launch.py

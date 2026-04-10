#!/bin/bash
# Launch Flask dashboard for the hospital fleet
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
export ROS_LOG_DIR="${WORKSPACE_ROOT}/.ros/log"
mkdir -p "${ROS_LOG_DIR}"
export DASHBOARD_PORT="${DASHBOARD_PORT:-5000}"

echo "Starting dashboard at http://localhost:${DASHBOARD_PORT}"
exec python3 -m hospital_fleet_manager.dashboard

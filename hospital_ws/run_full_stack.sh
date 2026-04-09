#!/bin/bash
# Launch the full hospital fleet stack: Gazebo, scheduler, simulator, and dashboard
set -eo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="${HOME}/venv-ai-hospital"

if [[ ! -d "${VENV_PATH}" ]]; then
  echo "Virtual environment not found at ${VENV_PATH}"
  exit 1
fi

source "${VENV_PATH}/bin/activate"
source /opt/ros/jazzy/setup.bash
[[ -f "${WORKSPACE_ROOT}/install/setup.bash" ]] && source "${WORKSPACE_ROOT}/install/setup.bash"

export PYTHONPATH="${WORKSPACE_ROOT}/src/hospital_fleet_manager:${PYTHONPATH}"
export ROS_LOG_DIR="${WORKSPACE_ROOT}/.ros/log"
mkdir -p "${ROS_LOG_DIR}"

bash "${WORKSPACE_ROOT}/run_gazebo.sh" &
bash "${WORKSPACE_ROOT}/run_scheduler.sh" &
bash "${WORKSPACE_ROOT}/run_simulator.sh" &
bash "${WORKSPACE_ROOT}/run_dashboard.sh" &

wait

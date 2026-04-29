#!/bin/bash
set -eo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="${HOME}/venv-ai-hospital"

if [[ ! -d "${VENV_PATH}" ]]; then
  echo "Virtual environment not found at ${VENV_PATH}, creating..."
  python3 -m venv "${VENV_PATH}"
  source "${VENV_PATH}/bin/activate"
  python3 -m pip install --upgrade pip setuptools wheel
  # Install the package in editable mode so console scripts are available
  if [[ -f "${WORKSPACE_ROOT}/src/hospital_fleet_manager/setup.py" ]]; then
    python3 -m pip install -e "${WORKSPACE_ROOT}/src/hospital_fleet_manager"
  fi
  deactivate
fi

source "${VENV_PATH}/bin/activate"
source /opt/ros/jazzy/setup.bash
[[ -f "${WORKSPACE_ROOT}/install/setup.bash" ]] && source "${WORKSPACE_ROOT}/install/setup.bash"

# Ensure system-invoked scripts can import packages from the virtualenv
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
VENV_SITE_PACKAGES="${VENV_PATH}/lib/python${PY_VER}/site-packages"
export PYTHONPATH="${VENV_SITE_PACKAGES}:${PYTHONPATH}"
HOSPITAL_PYTHON="${VENV_PATH}/bin/python3"
export HOSPITAL_PYTHON
export HOSPITAL_USE_GUNICORN="${HOSPITAL_USE_GUNICORN:-1}"

export ROS_LOG_DIR="${WORKSPACE_ROOT}/.ros/log"
mkdir -p "${ROS_LOG_DIR}"

# Auto-select a dashboard port if not provided (prefer 5000..5010)
if [[ -z "${HOSPITAL_DASHBOARD_PORT}" ]]; then
  for p in {5000..5010}; do
    if ! ss -ltn "( sport = :$p )" >/dev/null 2>&1 && ! lsof -i :"$p" >/dev/null 2>&1; then
      export HOSPITAL_DASHBOARD_PORT="$p"
      break
    fi
  done
  if [[ -z "${HOSPITAL_DASHBOARD_PORT}" ]]; then
    # fallback: ask OS for a free ephemeral port
    HOSPITAL_DASHBOARD_PORT=$(python3 - <<PY
import socket
s=socket.socket()
s.bind(("",0))
print(s.getsockname()[1])
s.close()
PY
)
    export HOSPITAL_DASHBOARD_PORT
  fi
fi

# Export GZ/GAZEBO model paths from the workspace if present
MODELS_DIR="${WORKSPACE_ROOT}/install/hospital_fleet_manager/share/hospital_fleet_manager/models"
if [[ -d "${MODELS_DIR}" ]]; then
  export GZ_MODEL_PATH="${MODELS_DIR}:${GZ_MODEL_PATH:-}"
  export GAZEBO_MODEL_PATH="${MODELS_DIR}:${GAZEBO_MODEL_PATH:-}"
fi

# Detect if any installed gz/gzserver binaries come from snap (core20) which
# can cause GLIBC_PRIVATE symbol lookup errors. Warn the user if detected.
HOSPITAL_GZ_SNAP_DETECTED=0
for BIN in gz gzserver gz-sim gz-sim-cli gzserver-ignite; do
  if command -v "${BIN}" >/dev/null 2>&1; then
    BINPATH=$(readlink -f "$(command -v ${BIN})") || BINPATH="$(command -v ${BIN})"
    if [[ "${BINPATH}" == *"/snap/"* || "${BINPATH}" == *"/core20/"* ]]; then
      echo "WARNING: ${BIN} appears to be provided by snap (${BINPATH})."
      echo "This can cause GLIBC_PRIVATE symbol lookup errors with system libraries."
      HOSPITAL_GZ_SNAP_DETECTED=1
    fi
  fi
done
if [[ "${HOSPITAL_GZ_SNAP_DETECTED}" -eq 1 ]]; then
  echo "Suggested fix: remove/avoid the snap-installed gz binaries and install the distro/apt packages for ROS Jazzy (e.g. 'sudo apt install ros-jazzy-gz-sim' or the ros_gz_sim packages)."
fi

SCENARIO_FILE="${HOSPITAL_SCENARIO_FILE:-${WORKSPACE_ROOT}/src/hospital_fleet_manager/hospital_fleet_manager/config/scenario_default.yaml}"
USE_GAZEBO="${USE_GAZEBO:-false}"
USE_NAV2="${USE_NAV2:-false}"
USE_STATE_PUBLISHERS="${USE_STATE_PUBLISHERS:-false}"
USE_GZ_GUI="${USE_GZ_GUI:-true}"

python3 - <<'PY'
import importlib.util
required = ("flask", "networkx", "sklearn")
missing = [m for m in required if importlib.util.find_spec(m) is None]
if missing:
    raise SystemExit(
        "Missing Python modules in active environment: "
        + ", ".join(missing)
        + ". Install them in venv-ai-hospital before launching."
    )
PY

exec ros2 launch hospital_fleet_manager hospital_stack.launch.py \
  scenario_file:="${SCENARIO_FILE}" \
  use_visual_dashboard:=true \
  use_gazebo:="${USE_GAZEBO}" \
  use_nav2:="${USE_NAV2}" \
  use_state_publishers:="${USE_STATE_PUBLISHERS}" \
  use_gz_gui:="${USE_GZ_GUI}"

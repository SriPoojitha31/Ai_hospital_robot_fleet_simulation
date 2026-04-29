#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="${HOME}/venv-ai-hospital"

if [[ -d "${VENV_PATH}" ]]; then
  echo "Virtualenv already exists at ${VENV_PATH}"
  exit 0
fi

python3 -m venv "${VENV_PATH}"
source "${VENV_PATH}/bin/activate"
python3 -m pip install --upgrade pip setuptools wheel
if [[ -f "${WORKSPACE_ROOT}/requirements.txt" ]]; then
  python3 -m pip install -r "${WORKSPACE_ROOT}/requirements.txt"
fi
# Install package in editable mode to enable console scripts
if [[ -f "${WORKSPACE_ROOT}/src/hospital_fleet_manager/setup.py" ]]; then
  python3 -m pip install -e "${WORKSPACE_ROOT}/src/hospital_fleet_manager"
fi

deactivate

echo "Virtualenv created at ${VENV_PATH} and dependencies installed." 

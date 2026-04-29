#!/bin/bash
# Launch simulator + scheduler + visual dashboard together.
set -eo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${WORKSPACE_ROOT}/.logs"

mkdir -p "${LOG_DIR}"

SIM_LOG="${LOG_DIR}/simulator.log"
SCH_LOG="${LOG_DIR}/scheduler.log"
VIS_LOG="${LOG_DIR}/visual_dashboard.log"

PIDS=()

cleanup() {
  echo ""
  echo "Stopping all services..."
  for pid in "${PIDS[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
  echo "All services stopped."
}

trap cleanup INT TERM EXIT

echo "Starting simulator..."
bash "${WORKSPACE_ROOT}/run_simulator.sh" >"${SIM_LOG}" 2>&1 &
PIDS+=($!)
sleep 1

echo "Starting scheduler..."
bash "${WORKSPACE_ROOT}/run_scheduler.sh" >"${SCH_LOG}" 2>&1 &
PIDS+=($!)
sleep 1

echo "Starting visual dashboard..."
bash "${WORKSPACE_ROOT}/run_visual_dashboard.sh" >"${VIS_LOG}" 2>&1 &
PIDS+=($!)
sleep 1

echo ""
echo "All services started."
echo "Logs:"
echo "  Simulator: ${SIM_LOG}"
echo "  Scheduler: ${SCH_LOG}"
echo "  Dashboard: ${VIS_LOG}"
echo ""
echo "Tip: open dashboard URL shown in ${VIS_LOG}"
echo "Press Ctrl+C here to stop everything."
echo ""

wait

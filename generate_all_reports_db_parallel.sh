#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
PYTHON_BIN="$VENV_PATH/bin/python3"
LOG_DIR="$SCRIPT_DIR/db_parallel/reports"
LOG_FILE="$LOG_DIR/generation.log"

mkdir -p "$LOG_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Starting DB-parallel Report Generation ===" | tee -a "$LOG_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Using script dir: $SCRIPT_DIR" | tee -a "$LOG_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Activating venv: $VENV_PATH" | tee -a "$LOG_FILE"
if [ -f "$VENV_PATH/bin/activate" ]; then
    # shellcheck disable=SC1090
    source "$VENV_PATH/bin/activate"
else
    echo "ERROR: Virtual environment not found at $VENV_PATH" | tee -a "$LOG_FILE"
    exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
    echo "ERROR: Python interpreter not found at $PYTHON_BIN" | tee -a "$LOG_FILE"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running DB-parallel pipeline (API -> DB -> 3 HTML reports)..." | tee -a "$LOG_FILE"
"$PYTHON_BIN" -m db_parallel.generate_all_reports_db >> "$LOG_FILE" 2>&1

if [ -f "$SCRIPT_DIR/db_parallel/reports/speaker_workload_report.html" ] && \
   [ -f "$SCRIPT_DIR/db_parallel/reports/completed_projects_report.html" ] && \
   [ -f "$SCRIPT_DIR/db_parallel/reports/late_report.html" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ DB-parallel reports generated successfully" | tee -a "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: One or more expected HTML reports are missing" | tee -a "$LOG_FILE"
    exit 1
fi

deactivate || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === DB-parallel Report Generation Completed ===" | tee -a "$LOG_FILE"

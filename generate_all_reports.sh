#!/bin/bash

# Automated Report Generation Script for Trello API
# This script generates all HTML reports and can be used with cronjob
# Usage: ./generate_all_reports.sh [--no-upload]

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
REPORTS_DIR="$SCRIPT_DIR/reports"
LOG_FILE="$SCRIPT_DIR/reports/generation.log"

# Upload configuration
UPLOAD_ENABLED=true
REMOTE_HOST=""
REMOTE_USER=""
REMOTE_PATH=""
SSH_KEY=""

# Parse arguments (backward compat)
if [[ "$1" == "--no-upload" ]]; then
    UPLOAD_ENABLED=false
fi

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Start logging
log_message "=== Starting Report Generation ==="

# Change to script directory
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    log_message "Virtual environment activated"
else
    log_message "ERROR: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Always refresh trello_cards_detailed.json
log_message "Fetching fresh data from Trello..."
python3 trello_client.py >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log_message "ERROR: Failed to fetch Trello data"
    exit 1
fi

# Generate Speaker Workload Report
log_message "Generating Speaker Workload Report..."
python3 generate_html_report.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log_message "✓ Speaker Workload Report generated successfully"
else
    log_message "ERROR: Failed to generate Speaker Workload Report"
    exit 1
fi

# Generate Completed Projects Report
log_message "Generating Completed Projects Report..."
python3 generate_completed_html.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log_message "✓ Completed Projects Report generated successfully"
else
    log_message "ERROR: Failed to generate Completed Projects Report"
    exit 1
fi

# Upload reports via SFTP (IONOS_*)
if [ "$UPLOAD_ENABLED" = true ]; then
    log_message "Uploading reports via SFTP..."
    python3 upload_reports.py >> "$LOG_FILE" 2>&1
    UPLOAD_EXIT=$?
    if [ $UPLOAD_EXIT -eq 0 ]; then
        log_message "✓ Reports uploaded successfully"
    elif [ $UPLOAD_EXIT -eq 2 ]; then
        log_message "Upload skipped (missing IONOS_* config in .env)"
    else
        log_message "ERROR: Failed to upload reports"
        exit 1
    fi
fi

log_message "=== Report Generation Completed Successfully ==="
log_message ""

# Deactivate virtual environment
deactivate

exit 0

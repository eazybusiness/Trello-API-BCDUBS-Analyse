#!/bin/bash

# Automated Report Generation Script for Trello API
# This script generates all HTML reports and can be used with cronjob
# Usage: ./generate_all_reports.sh [--upload]

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
REPORTS_DIR="$SCRIPT_DIR/reports"
LOG_FILE="$SCRIPT_DIR/reports/generation.log"

# SSH Upload Configuration (optional)
UPLOAD_ENABLED=false
REMOTE_HOST=""
REMOTE_USER=""
REMOTE_PATH=""
SSH_KEY=""

# Parse arguments
if [[ "$1" == "--upload" ]]; then
    UPLOAD_ENABLED=true
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

# Upload to remote server if enabled
if [ "$UPLOAD_ENABLED" = true ]; then
    log_message "Uploading reports to remote server..."
    
    # Check if SSH configuration is set
    if [ -z "$REMOTE_HOST" ] || [ -z "$REMOTE_USER" ] || [ -z "$REMOTE_PATH" ]; then
        log_message "WARNING: SSH upload enabled but configuration incomplete"
        log_message "Please edit this script and set REMOTE_HOST, REMOTE_USER, and REMOTE_PATH"
    else
        # Upload HTML reports
        if [ -n "$SSH_KEY" ]; then
            SSH_CMD="ssh -i $SSH_KEY"
            SCP_CMD="scp -i $SSH_KEY"
        else
            SSH_CMD="ssh"
            SCP_CMD="scp"
        fi
        
        # Create remote directory if it doesn't exist
        $SSH_CMD "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_PATH}" >> "$LOG_FILE" 2>&1
        
        # Upload reports
        $SCP_CMD "$REPORTS_DIR/speaker_workload_report.html" \
                 "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/" >> "$LOG_FILE" 2>&1
        
        $SCP_CMD "$REPORTS_DIR/completed_projects_report.html" \
                 "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/" >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            log_message "✓ Reports uploaded successfully to ${REMOTE_HOST}:${REMOTE_PATH}"
        else
            log_message "ERROR: Failed to upload reports"
            exit 1
        fi
    fi
fi

log_message "=== Report Generation Completed Successfully ==="
log_message ""

# Deactivate virtual environment
deactivate

exit 0

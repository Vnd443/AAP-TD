# ================================================================================
# IBM CONSULTING ADVANTAGE (ICA) - CODE GENERATION
# ================================================================================
# 
# [STEP 1/5] Connecting to IBM Consulting Advantage (ICA)...
#   ✓ Authenticating with ICA API
#   ✓ API endpoint: https://servicesessentials.ibm.com/apis/v1/sidekick-ai
#   ✓ Chat session established: 69aa70b99355f2523869...
# 
# [STEP 2/5] Analyzing Ticket Requirements...
#   ✓ Ticket ID: Disk_Space_Cleanup
#   ✓ Problem Pattern: Disk Space Cleanup
#   ✓ Description: Automated resolution for Disk Space Cleanup based on service...
#   ✓ Runbook context loaded (923 characters)
# 
# [STEP 3/5] Generating Automation Code with ICA AI...
#   ✓ Building code generation prompt
#   ✓ Applying best practices and patterns
#   ✓ Sending request to ICA AI engine...
#   ✓ Code generated successfully
# 
# [STEP 4/5] AI Code Review in Progress...
#   ✓ Syntax validation: PASSED
#   ✓ Security scan: PASSED
#   ✓ Best practices check: PASSED
#   ✓ Error handling verification: PASSED
#   ✓ Idempotency check: PASSED
# 
#   ✓ Code type: Shell Script
# 
# [STEP 5/5] Generating Execution Documentation...
#   ✓ Prerequisites documented
#   ✓ Execution steps added
#   ✓ Rollback procedures included
#   ✓ Troubleshooting guide added
# 
# ================================================================================
# CODE GENERATION COMPLETED SUCCESSFULLY
# ================================================================================
# 
# ============================================================================
# EXECUTION INSTRUCTIONS
# ============================================================================
# 
# Prerequisites:
#   - Appropriate permissions (sudo/root if required)
#   - Target system access
#   - Backup of current configuration (recommended)
# 
# Execution Steps:
#   1. Review the generated code thoroughly
#   2. Test in non-production environment first
#   3. Execute with appropriate permissions
#   4. Monitor logs during execution
#   5. Verify the resolution
# 
# For Shell Scripts:
#   chmod +x Disk_Space_Cleanup.sh
#   ./Disk_Space_Cleanup.sh
# 
# For Ansible Playbooks:
#   ansible-playbook -i inventory Disk_Space_Cleanup.yml --check  # Dry run
#   ansible-playbook -i inventory Disk_Space_Cleanup.yml          # Execute
# 
# Rollback Procedure:
#   - Refer to the manual runbook for rollback steps
#   - Restore from backup if needed
#   - Contact support team if issues persist
# 
# Troubleshooting:
#   - Check logs in /var/log/ directory
#   - Verify network connectivity
#   - Ensure all prerequisites are met
#   - Review error messages carefully
# 
# ============================================================================

```bash
#!/bin/bash

# Disk Space Cleanup Automation Script
# Service Request ID: Disk_Space_Cleanup
# Purpose: Automated disk space cleanup based on runbook procedures

set -euo pipefail

# ==============================================================================
# CONFIGURATION PARAMETERS
# ==============================================================================

# Configurable parameters with defaults
TARGET_PATH="${TARGET_PATH:-/var/log}"
DAYS_OLD="${DAYS_OLD:-30}"
THRESHOLD="${THRESHOLD:-90}"
TEMP_PATH="/tmp"
LOG_FILE="/var/log/disk_cleanup_$(date +%Y%m%d_%H%M%S).log"

# Email notification settings (optional)
NOTIFY_EMAIL="${NOTIFY_EMAIL:-}"
HOSTNAME=$(hostname)

# ==============================================================================
# LOGGING FUNCTION
# ==============================================================================

log() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo "$message" | tee -a "$LOG_FILE"
}

# ==============================================================================
# ERROR HANDLER
# ==============================================================================

error_exit() {
    log "ERROR: $1"
    exit 1
}

# ==============================================================================
# PREREQUISITES CHECK
# ==============================================================================

log "=========================================="
log "Disk Space Cleanup Script - Started"
log "=========================================="

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
    error_exit "This script must be run as root or with sudo privileges"
fi

# Verify required commands exist
for cmd in df du find sort head; do
    if ! command -v "$cmd" &> /dev/null; then
        error_exit "Required command '$cmd' not found"
    fi
done

# Validate target path exists
if [[ ! -d "$TARGET_PATH" ]]; then
    error_exit "Target path $TARGET_PATH does not exist"
fi

log "Prerequisites check: PASSED"
log "Configuration: TARGET_PATH=$TARGET_PATH, DAYS_OLD=$DAYS_OLD, THRESHOLD=$THRESHOLD"

# ==============================================================================
# STEP 1: CHECK DISK USAGE
# ==============================================================================

log "Step 1: Checking disk usage..."

# Get disk usage for all mounted filesystems
df -h | tee -a "$LOG_FILE"

# Function to get disk usage percentage for a given path
get_disk_usage() {
    local path=$1
    df -h "$path" | awk 'NR==2 {print $5}' | sed 's/%//'
}

# Check each major partition
for partition in / /var /tmp /home; do
    if mountpoint -q "$partition" 2>/dev/null || [[ -d "$partition" ]]; then
        usage=$(get_disk_usage "$partition" 2>/dev/null || echo "0")
        log "Partition $partition usage: ${usage}%"
        
        if [[ $usage -ge $THRESHOLD ]]; then
            log "WARNING: Partition $partition exceeds threshold (${usage}% >= ${THRESHOLD}%)"
            CLEANUP_NEEDED=true
        fi
    fi
done

# ==============================================================================
# STEP 2: IDENTIFY LARGE FILES
# ==============================================================================

log "Step 2: Identifying large files and directories..."

if [[ -d "$TARGET_PATH" ]]; then
    log "Top 10 largest items in $TARGET_PATH:"
    du -sh "$TARGET_PATH"/* 2>/dev/null | sort -rh | head -10 | tee -a "$LOG_FILE" || log "No items found or permission denied"
fi

# ==============================================================================
# STEP 3: REVIEW LOG FILES
# ==============================================================================

log "Step 3: Reviewing log files in $TARGET_PATH..."

if [[ -d "$TARGET_PATH" ]]; then
    log "Large log files (>100MB):"
    find "$TARGET_PATH" -type f -size +100M -exec ls -lh {} \; 2>/dev/null | tee -a "$LOG_FILE" || log "No large log files found"
fi

# ==============================================================================
# STEP 4: CLEAN OLD LOG FILES
# ==============================================================================

log "Step 4: Cleaning old log files older than $DAYS_OLD days..."

# Count files before cleanup
OLD_FILES_COUNT=$(find "$TARGET_PATH" -type f -mtime +$DAYS_OLD 2>/dev/null | wc -l || echo "0")
log "Found $OLD_FILES_COUNT files older than $DAYS_OLD days in $TARGET_PATH"

if [[ $OLD_FILES_COUNT -gt 0 ]]; then
    # Create backup list of files to be deleted
    CLEANUP_LIST="/tmp/cleanup_list_$(date +%Y%m%d_%H%M%S).txt"
    find "$TARGET_PATH" -type f -mtime +$DAYS_OLD 2>/dev/null > "$CLEANUP_LIST" || true
    
    log "Deleting old log files from $TARGET_PATH..."
    DELETED_COUNT=0
    
    while IFS= read -r file; do
        if [[ -f "$file" ]]; then
            rm -f "$file" && ((DELETED_COUNT++)) && log "Deleted: $file"
        fi
    done < "$CLEANUP_LIST"
    
    log "Deleted $DELETED_COUNT files from $TARGET_PATH"
    rm -f "$CLEANUP_LIST"
else
    log "No old files to clean in $TARGET_PATH"
fi

# Clean compressed log files older than DAYS_OLD
log "Cleaning compressed log files (*.gz, *.bz2, *.xz)..."
COMPRESSED_COUNT=$(find "$TARGET_PATH" -type f \( -name "*.gz" -o -name "*.bz2" -o -name "*.xz" \) -mtime +$DAYS_OLD 2>/dev/null | wc -l || echo "0")

if [[ $COMPRESSED_COUNT -gt 0 ]]; then
    find "$TARGET_PATH" -type f \( -name "*.gz" -o -name "*.bz2" -o -name "*.xz" \) -mtime +$DAYS_OLD -delete 2>/dev/null || true
    log "Deleted $COMPRESSED_COUNT compressed log files"
fi

# ==============================================================================
# CLEAN TEMPORARY FILES
# ==============================================================================

log "Cleaning temporary files from $TEMP_PATH older than $DAYS_OLD days..."

if [[ -d "$TEMP_PATH" ]]; then
    TEMP_FILES_COUNT=$(find "$TEMP_PATH" -type f -mtime +$DAYS_OLD 2>/dev/null | wc -l || echo "0")
    
    if [[ $TEMP_FILES_COUNT -gt 0 ]]; then
        find "$TEMP_PATH" -type f -mtime +$DAYS_OLD -delete 2>/dev/null || log "Some temp files could not be deleted"
        log "Cleaned $TEMP_FILES_COUNT temporary files from $TEMP_PATH"
    else
        log "No old temporary files to clean"
    fi
    
    # Clean empty directories in /tmp
    find "$TEMP_PATH" -type d -empty -mtime +$DAYS_OLD -delete 2>/dev/null || true
fi

# ==============================================================================
# CLEAN COMMON LOG LOCATIONS
# ==============================================================================

log "Cleaning additional common log locations..."

# Clean journal logs if systemd is present
if command -v journalctl &> /dev/null; then
    log "Cleaning systemd journal logs older than ${DAYS_OLD} days..."
    journalctl --vacuum-time=${DAYS_OLD}d 2>&1 | tee -a "$LOG_FILE" || log "Journal cleanup skipped"
fi

# Clean package manager caches
if command -v apt-get &> /dev/null; then
    log "Cleaning apt cache..."
    apt-get clean 2>&1 | tee -a "$LOG_FILE" || log "APT cache cleanup skipped"
fi

if command -v yum &> /dev/null; then
    log "Cleaning yum cache..."
    yum clean all 2>&1 | tee -a "$LOG_FILE" || log "YUM cache cleanup skipped"
fi

# ==============================================================================
# STEP 5: VERIFY SPACE AFTER CLEANUP
# ==============================================================================

log "Step 5: Verifying disk space after cleanup..."

df -h | tee -a "$LOG_FILE"

# Check if cleanup was successful
CLEANUP_SUCCESS=true
for partition in / /var /tmp; do
    if [[ -d "$partition" ]]; then
        usage=$(get_disk_usage "$partition" 2>/dev/null || echo "0")
        log "Final partition $partition usage: ${usage}%"
        
        if [[ $usage -ge $THRESHOLD ]]; then
            log "WARNING: Partition $partition still exceeds threshold (${usage}% >= ${THRESHOLD}%)"
            CLEANUP_SUCCESS=false
        fi
    fi
done

# ==============================================================================
# NOTIFICATION
# ==============================================================================

log "Generating cleanup summary..."

SUMMARY="Disk Space Cleanup Summary for $HOSTNAME
========================================
Cleanup completed at: $(date)
Target path: $TARGET_PATH
Days old threshold: $DAYS_OLD
Disk usage threshold: $THRESHOLD%

Files cleaned from $TARGET_PATH: $OLD_FILES_COUNT
Compressed files cleaned: $COMPRESSED_COUNT
Temporary files cleaned: $TEMP_FILES_COUNT

Current disk usage:
$(df -h)

Detailed log: $LOG_FILE
"

echo "$SUMMARY" | tee -a "$LOG_FILE"

# Send email notification if configured
if [[ -n "$NOTIFY_EMAIL" ]] && command -v mail &> /dev/null; then
    echo "$SUMMARY" | mail -s "Disk Space Cleanup Report - $HOSTNAME" "$NOTIFY_EMAIL"
    log "Notification sent to $NOTIFY_EMAIL"
fi

# ==============================================================================
# COMPLETION
# ==============================================================================

if [[ "$CLEANUP_SUCCESS" == true ]]; then
    log "=========================================="
    log "Disk Space Cleanup Script - Completed Successfully"
    log "=========================================="
    exit 0
else
    log "=========================================="
    log "Disk Space Cleanup Script - Completed with Warnings"
    log "Manual intervention may be required"
    log "=========================================="
    exit 0
fi
```
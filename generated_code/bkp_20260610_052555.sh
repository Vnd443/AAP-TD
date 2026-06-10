```bash
#!/bin/bash

################################################################################
# Disk Space Cleanup Automation Script
# Description: Automatically monitors and cleans disk space when threshold exceeded
# Author: Auto-generated
# Version: 1.0
################################################################################

set -o pipefail

#------------------------------------------------------------------------------
# CONFIGURABLE PARAMETERS
#------------------------------------------------------------------------------
TARGET_PATH="${TARGET_PATH:-/var/log}"
DAYS_OLD="${DAYS_OLD:-30}"
THRESHOLD="${THRESHOLD:-90}"
DRY_RUN="${DRY_RUN:-false}"
LOG_FILE="${LOG_FILE:-/var/log/disk_cleanup_$(date +%Y%m%d_%H%M%S).log}"
NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-}"
TEMP_CLEANUP="${TEMP_CLEANUP:-true}"
TEMP_DAYS_OLD="${TEMP_DAYS_OLD:-7}"

#------------------------------------------------------------------------------
# GLOBAL VARIABLES
#------------------------------------------------------------------------------
SCRIPT_NAME=$(basename "$0")
CLEANUP_PERFORMED=false
SPACE_FREED=0
ERRORS_OCCURRED=false

#------------------------------------------------------------------------------
# LOGGING FUNCTIONS
#------------------------------------------------------------------------------
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
    ERRORS_OCCURRED=true
}

#------------------------------------------------------------------------------
# VALIDATION FUNCTIONS
#------------------------------------------------------------------------------
validate_parameters() {
    log_info "Validating input parameters..."
    
    # Validate THRESHOLD is a number between 1-100
    if ! [[ "${THRESHOLD}" =~ ^[0-9]+$ ]] || [ "${THRESHOLD}" -lt 1 ] || [ "${THRESHOLD}" -gt 100 ]; then
        log_error "THRESHOLD must be a number between 1 and 100. Got: ${THRESHOLD}"
        return 1
    fi
    
    # Validate DAYS_OLD is a positive number
    if ! [[ "${DAYS_OLD}" =~ ^[0-9]+$ ]] || [ "${DAYS_OLD}" -lt 1 ]; then
        log_error "DAYS_OLD must be a positive number. Got: ${DAYS_OLD}"
        return 1
    fi
    
    # Validate TARGET_PATH exists
    if [ ! -d "${TARGET_PATH}" ]; then
        log_error "TARGET_PATH does not exist: ${TARGET_PATH}"
        return 1
    fi
    
    # Check if running with sufficient privileges
    if [ ! -w "${TARGET_PATH}" ]; then
        log_error "No write permission for TARGET_PATH: ${TARGET_PATH}"
        return 1
    fi
    
    log_info "Parameter validation successful"
    return 0
}

#------------------------------------------------------------------------------
# DISK SPACE CHECK FUNCTIONS
#------------------------------------------------------------------------------
get_disk_usage() {
    local path="$1"
    local usage=$(df -h "${path}" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ -z "${usage}" ]; then
        log_error "Failed to get disk usage for: ${path}"
        return 1
    fi
    
    echo "${usage}"
}

get_partition_from_path() {
    local path="$1"
    df "${path}" | awk 'NR==2 {print $1}'
}

check_disk_space() {
    log_info "Checking disk space usage..."
    
    local partition=$(get_partition_from_path "${TARGET_PATH}")
    local usage=$(get_disk_usage "${TARGET_PATH}")
    
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    log_info "Partition: ${partition}, Current usage: ${usage}%, Threshold: ${THRESHOLD}%"
    
    if [ "${usage}" -ge "${THRESHOLD}" ]; then
        log_warn "Disk usage (${usage}%) exceeds threshold (${THRESHOLD}%)"
        return 0
    else
        log_info "Disk usage (${usage}%) is below threshold (${THRESHOLD}%)"
        return 2
    fi
}

#------------------------------------------------------------------------------
# CLEANUP FUNCTIONS
#------------------------------------------------------------------------------
get_current_space() {
    local path="$1"
    df -k "${path}" | awk 'NR==2 {print $4}'
}

find_large_files() {
    log_info "Identifying large files in ${TARGET_PATH}..."
    
    if [ -d "${TARGET_PATH}" ]; then
        du -sh "${TARGET_PATH}"/* 2>/dev/null | sort -rh | head -10 | while read -r line; do
            log_info "  ${line}"
        done
    fi
}

clean_old_logs() {
    log_info "Cleaning old log files from ${TARGET_PATH}..."
    
    local space_before=$(get_current_space "${TARGET_PATH}")
    local files_deleted=0
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "DRY RUN: Would delete files older than ${DAYS_OLD} days"
        find "${TARGET_PATH}" -type f \( -name "*.log" -o -name "*.log.*" -o -name "*.gz" \) -mtime +"${DAYS_OLD}" -ls 2>/dev/null | while read -r line; do
            log_info "  Would delete: ${line}"
        done
        return 0
    fi
    
    # Find and delete old log files
    while IFS= read -r -d '' file; do
        if [ -f "${file}" ]; then
            local file_size=$(stat -f%z "${file}" 2>/dev/null || stat -c%s "${file}" 2>/dev/null)
            if rm -f "${file}" 2>/dev/null; then
                log_info "Deleted: ${file} ($(numfmt --to=iec-i --suffix=B ${file_size} 2>/dev/null || echo ${file_size} bytes))"
                ((files_deleted++))
            else
                log_warn "Failed to delete: ${file}"
            fi
        fi
    done < <(find "${TARGET_PATH}" -type f \( -name "*.log" -o -name "*.log.*" -o -name "*.gz" \) -mtime +"${DAYS_OLD}" -print0 2>/dev/null)
    
    local space_after=$(get_current_space "${TARGET_PATH}")
    local space_freed=$((space_after - space_before))
    
    log_info "Log cleanup completed: ${files_deleted} files deleted"
    
    if [ ${space_freed} -gt 0 ]; then
        SPACE_FREED=$((SPACE_FREED + space_freed))
        log_info "Space freed from logs: $(numfmt --to=iec-i --suffix=B $((space_freed * 1024)) 2>/dev/null || echo $((space_freed)) KB)"
        CLEANUP_PERFORMED=true
    fi
}

clean_temp_files() {
    if [ "${TEMP_CLEANUP}" != "true" ]; then
        log_info "Temp file cleanup disabled"
        return 0
    fi
    
    local temp_dir="/tmp"
    
    if [ ! -d "${temp_dir}" ]; then
        log_warn "Temp directory does not exist: ${temp_dir}"
        return 0
    fi
    
    log_info "Cleaning temporary files from ${temp_dir}..."
    
    local space_before=$(get_current_space "${temp_dir}")
    local files_deleted=0
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "DRY RUN: Would delete temp files older than ${TEMP_DAYS_OLD} days"
        find "${temp_dir}" -type f -mtime +"${TEMP_DAYS_OLD}" -ls 2>/dev/null | head -20 | while read -r line; do
            log_info "  Would delete: ${line}"
        done
        return 0
    fi
    
    # Clean old temp files (be careful with /tmp)
    while IFS= read -r -d '' file; do
        if [ -f "${file}" ]; then
            if rm -f "${file}" 2>/dev/null; then
                ((files_deleted++))
            fi
        fi
    done < <(find "${temp_dir}" -maxdepth 2 -type f -mtime +"${TEMP_DAYS_OLD}" -print0 2>/dev/null)
    
    local space_after=$(get_current_space "${temp_dir}")
    local space_freed=$((space_after - space_before))
    
    log_info "Temp cleanup completed: ${files_deleted} files deleted"
    
    if [ ${space_freed} -gt 0 ]; then
        SPACE_FREED=$((SPACE_FREED + space_freed))
        log_info "Space freed from temp: $(numfmt --to=iec-i --suffix=B $((space_freed * 1024)) 2>/dev/null || echo $((space_freed)) KB)"
        CLEANUP_PERFORMED=true
    fi
}

clean_package_cache() {
    log_info "Cleaning package manager cache..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "DRY RUN: Would clean package cache"
        return 0
    fi
    
    # Clean apt cache (Debian/Ubuntu)
    if command -v apt-get &> /dev/null; then
        log_info "Cleaning apt cache..."
        apt-get clean 2>&1 | tee -a "${LOG_FILE}"
        CLEANUP_PERFORMED=true
    fi
    
    # Clean yum cache (RHEL/CentOS)
    if command -v yum &> /dev/null; then
        log_info "Cleaning yum cache..."
        yum clean all 2>&1 | tee -a "${LOG_FILE}"
        CLEANUP_PERFORMED=true
    fi
}

#------------------------------------------------------------------------------
# NOTIFICATION FUNCTIONS
#------------------------------------------------------------------------------
send_notification() {
    local subject="$1"
    local body="$2"
    
    if [ -z "${NOTIFICATION_EMAIL}" ]; then
        log_info "No notification email configured"
        return 0
    fi
    
    if command -v mail &> /dev/null; then
        echo "${body}" | mail -s "${subject}" "${NOTIFICATION_EMAIL}"
        log_info "Notification sent to: ${NOTIFICATION_EMAIL}"
    elif command -v sendmail &> /dev/null; then
        echo -e "Subject: ${subject}\n\n${body}" | sendmail "${NOTIFICATION_EMAIL}"
        log_info "Notification sent to: ${NOTIFICATION_EMAIL}"
    else
        log_warn "No mail command available for notifications"
    fi
}

#------------------------------------------------------------------------------
# REPORTING FUNCTIONS
#------------------------------------------------------------------------------
generate_report() {
    log_info "=== Disk Space Cleanup Report ==="
    log_info "Execution time: $(date)"
    log_info "Target path: ${TARGET_PATH}"
    log_info "Threshold: ${THRESHOLD}%"
    log_info "Days old: ${DAYS_OLD}"
    log_info "Cleanup performed: ${CLEANUP_PERFORMED}"
    
    if [ ${SPACE_FREED} -gt 0 ]; then
        log_info "Total space freed: $(numfmt --to=iec-i --suffix=B $((SPACE_FREED * 1024)) 2>/dev/null || echo ${SPACE_FREED} KB)"
    fi
    
    log_info "Current disk usage:"
    df -h "${TARGET_PATH}" | tee -a "${LOG_FILE}"
    
    log_info "==================================="
}

#------------------------------------------------------------------------------
# MAIN EXECUTION
#------------------------------------------------------------------------------
main() {
    log_info "Starting disk space cleanup automation..."
    log_info "Script: ${SCRIPT_NAME}"
    log_info "Log file: ${LOG_FILE}"
    
    # Validate parameters
    if ! validate_parameters; then
        log_error "Parameter validation failed"
        exit 1
    fi
    
    # Check initial disk space
    find_large_files
    
    check_disk_space
    local check_result=$?
    
    if [ ${check_result} -eq 1 ]; then
        log_error "Failed to check disk space"
        exit 1
    elif [ ${check_result} -eq 2 ]; then
        log_info "Disk space is within acceptable limits. No cleanup needed."
        generate_report
        exit 0
    fi
    
    # Perform cleanup operations
    log_info "Starting cleanup operations..."
    
    clean_old_logs
    clean_temp_files
    clean_package_cache
    
    # Verify cleanup results
    log_info "Verifying cleanup results..."
    local final_usage=$(get_disk_usage "${TARGET_PATH}")
    
    if [ $? -eq 0 ]; then
        log_info "Final disk usage: ${final_usage}%"
        
        if [ "${final_usage}" -ge "${THRESHOLD}" ]; then
            log_warn "Disk usage still above threshold after cleanup"
            send_notification "Disk Cleanup Warning" "Disk usage (${final_usage}%) still exceeds threshold (${THRESHOLD}%) after cleanup on $(hostname)"
        else
            log_info "Disk usage successfully reduced below threshold"
            if [ "${CLEANUP_PERFORMED}" = "true" ]; then
                send_notification "Disk Cleanup Success" "Disk cleanup completed successfully on $(hostname). Usage reduced to ${final_usage}%"
            fi
        fi
    fi
    
    # Generate final report
    generate_report
    
    # Exit with appropriate code
    if [ "${ERRORS_OCCURRED}" = "true" ]; then
        log_warn "Script completed with errors"
        exit 1
    else
        log_info "Script completed successfully"
        exit 0
    fi
}

# Execute main function
main "$@"
```
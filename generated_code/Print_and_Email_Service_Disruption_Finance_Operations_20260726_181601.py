#!/usr/bin/env python3
"""
Print and Email Service Disruption - Finance Operations Automation Script
Runbook: Disk Space Cleanup for Print/Email Service Recovery
Handles: Print spooler recovery, email service restoration, disk space remediation
for Finance Operations environments
"""

import os
import sys
import shutil
import subprocess
import logging
import smtplib
import socket
import platform
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional

# ─────────────────────────────────────────────
# CONFIGURATION BLOCK - Modify as needed
# ─────────────────────────────────────────────
CONFIG = {
    # Disk space thresholds
    "DISK_THRESHOLD_CRITICAL": 90,        # Trigger cleanup above this %
    "DISK_THRESHOLD_WARNING": 80,         # Warning level %
    "DAYS_OLD_LOGS": 30,                  # Log files older than X days to remove
    "DAYS_OLD_TEMP": 7,                   # Temp files older than X days to remove

    # Paths to clean
    "LOG_PATHS": [
        "/var/log",
        "/var/spool/cups",                # CUPS print spooler logs
        "/var/spool/postfix",             # Postfix email spooler
        "/tmp",
    ],
    "PRINT_SPOOL_PATH": "/var/spool/cups",
    "EMAIL_SPOOL_PATH": "/var/spool/postfix/deferred",
    "TEMP_PATHS": ["/tmp", "/var/tmp"],

    # Print service settings
    "PRINT_SERVICE_NAME": "cups",         # systemd service name for print
    "PRINT_MAX_QUEUE_AGE_HOURS": 24,      # Max age for stuck print jobs
    "PRINT_MAX_STUCK_JOBS": 10,           # Alert if queue exceeds this

    # Email service settings
    "EMAIL_SERVICE_NAME": "postfix",      # systemd service name for email
    "EMAIL_MAX_QUEUE_SIZE": 500,          # Alert if deferred queue exceeds this
    "EMAIL_MAX_RETRY_HOURS": 48,          # Remove deferred mail older than X hours

    # Notification settings
    "SMTP_SERVER": "smtp.finance.corp",
    "SMTP_PORT": 587,
    "SMTP_USE_TLS": True,
    "SMTP_USERNAME": "alerts@finance.corp",
    "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD", ""),  # Load from env
    "NOTIFY_FROM": "it-automation@finance.corp",
    "NOTIFY_TO": [
        "it-ops@finance.corp",
        "finance-it-support@finance.corp",
    ],
    "NOTIFY_CC": ["it-manager@finance.corp"],
    "ESCALATION_TO": ["it-director@finance.corp"],

    # Log settings
    "LOG_FILE": "/var/log/finance_service_automation.log",
    "LOG_LEVEL": "INFO",
    "MAX_LOG_SIZE_MB": 50,

    # Safety settings
    "DRY_RUN": False,                     # Set True to simulate without changes
    "BACKUP_BEFORE_CLEAN": True,          # Create manifest before deletion
    "BACKUP_MANIFEST_PATH": "/var/log/cleanup_manifests",
    "MAX_DELETE_SIZE_GB": 10,             # Safety cap on total deletion size
    "REQUIRE_CONFIRMATION": False,        # Set True for interactive mode

    # Retry settings
    "SERVICE_RESTART_RETRIES": 3,
    "SERVICE_RESTART_DELAY_SECONDS": 10,
}

# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────
def setup_logging() -> logging.Logger:
    """Configure rotating file and console logging."""
    log_dir = Path(CONFIG["LOG_FILE"]).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, CONFIG["LOG_LEVEL"].upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger("FinanceServiceAutomation")
    logger.setLevel(log_level)

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with size rotation
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            CONFIG["LOG_FILE"],
            maxBytes=CONFIG["MAX_LOG_SIZE_MB"] * 1024 * 1024,
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        logger.warning(f"Cannot write to {CONFIG['LOG_FILE']} - logging to console only")

    return logger


# Initialize logger
logger = setup_logging()


# ─────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────
def bytes_to_human(num_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"


def run_command(
    cmd: list,
    capture_output: bool = True,
    timeout: int = 60,
    check: bool = False
) -> subprocess.CompletedProcess:
    """
    Execute a system command safely with error handling.
    Returns CompletedProcess object.
    """
    cmd_str = " ".join(str(c) for c in cmd)
    logger.debug(f"Executing command: {cmd_str}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            check=check
        )
        if result.returncode != 0 and result.stderr:
            logger.debug(f"Command stderr: {result.stderr.strip()}")
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd_str}")
        raise
    except FileNotFoundError:
        logger.error(f"Command not found: {cmd[0]}")
        raise
    except Exception as e:
        logger.error(f"Command execution failed [{cmd_str}]: {e}")
        raise


def is_root() -> bool:
    """Check if script is running with root privileges."""
    return os.geteuid() == 0 if hasattr(os, "geteuid") else False


def is_linux() -> bool:
    """Check if running on Linux."""
    return platform.system().lower() == "linux"
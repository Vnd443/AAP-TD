```python
#!/usr/bin/env python3
"""
Log Rotation Configuration Script
Automates the setup and management of log rotation for applications.
Provides comprehensive error handling, validation, and idempotent operations.
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/log_rotation_config.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class LogRotationConfigurator:
    """Manages log rotation configuration for applications."""
    
    def __init__(self, app_name: str, log_path: str, rotate_frequency: str = "daily",
                 keep_logs: int = 30, compress: bool = True, max_size: Optional[str] = None):
        """
        Initialize log rotation configurator.
        
        Args:
            app_name: Name of the application
            log_path: Path to log directory or file
            rotate_frequency: Rotation frequency (daily, weekly, monthly)
            keep_logs: Number of rotated logs to keep
            compress: Whether to compress rotated logs
            max_size: Maximum size before rotation (e.g., '100M', '1G')
        """
        self.app_name = app_name
        self.log_path = log_path
        self.rotate_frequency = rotate_frequency
        self.keep_logs = keep_logs
        self.compress = compress
        self.max_size = max_size
        self.config_path = f"/etc/logrotate.d/{app_name}"
        self.backup_path = f"{self.config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def validate_parameters(self) -> bool:
        """
        Validate configuration parameters.
        
        Returns:
            bool: True if all parameters are valid
        """
        logger.info("Validating configuration parameters...")
        
        # Validate app name
        if not self.app_name or not self.app_name.replace('_', '').replace('-', '').isalnum():
            logger.error(f"Invalid app name: {self.app_name}")
            return False
        
        # Validate log path
        log_path_obj = Path(self.log_path)
        if not log_path_obj.exists():
            logger.warning(f"Log path does not exist: {self.log_path}")
            try:
                log_path_obj.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created log directory: {self.log_path}")
            except Exception as e:
                logger.error(f"Failed to create log directory: {e}")
                return False
        
        # Validate rotation frequency
        valid_frequencies = ['daily', 'weekly', 'monthly', 'yearly']
        if self.rotate_frequency not in valid_frequencies:
            logger.error(f"Invalid rotation frequency: {self.rotate_frequency}. Must be one of {valid_frequencies}")
            return False
        
        # Validate keep_logs count
        if self.keep_logs < 1 or self.keep_logs > 365:
            logger.error(f"Invalid keep_logs value: {self.keep_logs}. Must be between 1 and 365")
            return False
        
        # Validate max_size format if provided
        if self.max_size:
            import re
            if not re.match(r'^\d+[kKmMgG]$', self.max_size):
                logger.error(f"Invalid max_size format: {self.max_size}. Use format like '100M' or '1G'")
                return False
        
        logger.info("All parameters validated successfully")
        return True
    
    def check_logrotate_installed(self) -> bool:
        """
        Check if logrotate is installed on the system.
        
        Returns:
            bool: True if logrotate is installed
        """
        try:
            result = subprocess.run(['which', 'logrotate'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                logger.info("logrotate is installed")
                return True
            else:
                logger.error("logrotate is not installed")
                return False
        except Exception as e:
            logger.error(f"Error checking for logrotate: {e}")
            return False
    
    def check_current_log_sizes(self) -> Dict[str, int]:
        """
        Check current log file sizes.
        
        Returns:
            Dict[str, int]: Dictionary of log files and their sizes in bytes
        """
        logger.info(f"Checking log sizes in {self.log_path}...")
        log_sizes = {}
        
        try:
            log_path_obj = Path(self.log_path)
            
            if log_path_obj.is_file():
                # Single log file
                log_sizes[str(log_path_obj)] = log_path_obj.stat().st_size
            elif log_path_obj.is_dir():
                # Directory of log files
                for log_file in log_path_obj.glob('*.log'):
                    if log_file.is_file():
                        log_sizes[str(log_file)] = log_file.stat().st_size
            
            # Log the results
            for log_file, size in log_sizes.items():
                size_mb = size / (1024 * 1024)
                logger.info(f"  {log_file}: {size_mb:.2f} MB")
            
            total_size = sum(log_sizes.values()) / (1024 * 1024)
            logger.info(f"Total log size: {total_size:.2f} MB")
            
        except Exception as e:
            logger.error(f"Error checking log sizes: {e}")
        
        return log_sizes
    
    def backup_existing_config(self) -> bool:
        """
        Backup existing logrotate configuration if it exists.
        
        Returns:
            bool: True if backup successful or no existing config
        """
        try:
            if Path(self.config_path).exists():
                shutil.copy2(self.config_path, self.backup_path)
                logger.info(f"Backed up existing configuration to {self.backup_path}")
            else:
                logger.info("No existing configuration to backup")
            return True
        except Exception as e:
            logger.error(f"Failed to backup existing configuration: {e}")
            return False
    
    def generate_logrotate_config(self) -> str:
        """
        Generate logrotate configuration content.
        
        Returns:
            str: Configuration file content
        """
        logger.info("Generating logrotate configuration...")
        
        # Determine log file pattern
        log_path_obj = Path(self.log_path)
        if log_path_obj.is_file():
            log_pattern = str(log_path_obj)
        else:
            log_pattern = f"{self.log_path}/*.log"
        
        # Build configuration
        config_lines = [
            f"# Log rotation configuration for {self.app_name}",
            f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"{log_pattern} {{",
            f"    {self.rotate_frequency}",
            f"    rotate {self.keep_logs}",
        ]
        
        # Add size-based rotation if specified
        if self.max_size:
            config_lines.append(f"    size {self.max_size}")
        
        # Add compression options
        if self.compress:
            config_lines.extend([
                "    compress",
                "    delaycompress",
            ])
        
        # Add common options
        config_lines.extend([
            "    missingok",
            "    notifempty",
            "    create 0644 root root",
            "    sharedscripts",
        ])
        
        # Add postrotate script to reload application if it's a service
        config_lines.extend([
            "    postrotate",
            f"        systemctl reload {self.app_name} > /dev/null 2>&1 || true",
            "    endscript",
            "}",
        ])
        
        return "\n".join(config_lines)
    
    def write_config(self, config_content: str) -> bool:
        """
        Write configuration to file.
        
        Args:
            config_content: Configuration content to write
            
        Returns:
            bool: True if write successful
        """
        try:
            # Check if we have write permissions
            config_dir = Path(self.config_path).parent
            if not os.access(config_dir, os.W_OK):
                logger.error(f"No write permission for {config_dir}. Run with sudo.")
                return False
            
            # Write configuration
            with open(self.config_path, 'w') as f:
                f.write(config_content)
            
            # Set proper permissions
            os.chmod(self.config_path, 0o644)
            
            logger.info(f"Configuration written to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write configuration: {e}")
            return False
    
    def test_config(self) -> bool:
        """
        Test logrotate configuration using debug mode.
        
        Returns:
            bool: True if configuration is valid
        """
        logger.info("Testing logrotate configuration...")
        
        try:
            result = subprocess.run(
                ['logrotate', '-d', self.config_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Configuration test passed")
                logger.debug(f"Test output:\n{result.stdout}")
                return True
            else:
                logger.error(f"Configuration test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Configuration test timed out")
            return False
        except Exception as e:
            logger.error(f"Error testing configuration: {e}")
            return False
    
    def force_rotation(self) -> bool:
        """
        Force immediate log rotation.
        
        Returns:
            bool: True if rotation successful
        """
        logger.info("Forcing log rotation...")
        
        try:
            result = subprocess.run(
                ['logrotate', '-f', self.config_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("Forced rotation completed successfully")
                if result.stdout:
                    logger.debug(f"Rotation output:\n{result.stdout}")
                return True
            else:
                logger.error(f"Forced rotation failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Forced rotation timed out")
            return False
        except Exception as e:
            logger.error(f"Error forcing rotation: {e}")
            return False
    
    def verify_rotation_status(self) -> bool:
        """
        Verify that log rotation is working by checking logrotate status.
        
        Returns:
            bool: True if status check successful
        """
        logger.info("Verifying rotation status...")
        
        try:
            status_file = "/var/lib/logrotate/status"
            if Path(status_file).exists():
                result = subprocess.run(
                    ['grep', self.log_path, status_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout:
                    logger.info(f"Rotation status: {result.stdout.strip()}")
                    return True
            else:
                logger.warning("Logrotate status file not found")
            return False
        except Exception as e:
            logger.error(f"Error verifying rotation status: {e}")
            return False
    
    def configure(self, force_rotate: bool = False) -> bool:
        """
        Main configuration method - orchestrates the entire process.
        
        Args:
            force_rotate: Whether to force immediate rotation after configuration
            
        Returns:
            bool: True if configuration successful
        """
        logger.info(f"Starting log rotation configuration for {self.app_name}")
        
        # Validate parameters
        if not self.validate_parameters():
            logger.error("Parameter validation failed")
            return False
        
        # Check if logrotate is installed
        if not self.check_logrotate_installed():
            logger.error("logrotate is not installed. Please install it first.")
            return False
        
        # Check current log sizes
        self.check_current_log_sizes()
        
        # Backup existing configuration
        if not self.backup_existing_config():
            logger.warning("Failed to backup existing configuration, continuing anyway...")
        
        # Generate configuration
        config_content = self.generate_logrotate_config()
        
        # Write configuration
        if not self.write_config(config_content):
            logger.error("Failed to write configuration")
            return False
        
        # Test configuration
        if not self.test_config():
            logger.error("Configuration test failed")
            # Restore backup if exists
            if Path(self.backup_path).exists():
                shutil.copy2(self.backup_path, self.config_path)
                logger.info("Restored previous configuration")
            return False
        
        # Force rotation if requested
        if force_rotate:
            if not self.force_rotation():
                logger.warning("Forced rotation failed, but configuration is valid")
        
        # Verify rotation status
        self.verify_rotation_status()
        
        logger.info(f"Log rotation configuration completed successfully for {self.app_name}")
        return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Configure log rotation for applications',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --app myapp --log-path /var/log/myapp
  %(prog)s --app myapp --log-path /var/log/myapp --force-rotate
  %(prog)s --app myapp --log-path /var/log/myapp --frequency weekly --keep 52
  %(prog)s --app myapp --log-path /var/log/myapp/app.log --max-size 100M
        """
    )
    
    parser.add_argument(
        '--app',
        required=True,
        help='Application name'
    )
    parser.add_argument(
        '--log-path',
        required=True,
        help='Path to log directory or file'
    )
    parser.add_argument(
        '--frequency',
        choices=['daily', 'weekly', 'monthly', 'yearly'],
        default='daily',
        help='Rotation frequency (default: daily)'
    )
    parser.add_argument(
        '--keep',
        type=int,
        default=30,
        help='Number of rotated logs to keep (default: 30)'
    )
    parser.add_argument(
        '--no-compress',
        action='store_true',
        help='Disable compression of rotated logs'
    )
    parser.add_argument(
        '--max-size',
        help='Maximum size before rotation (e.g., 100M, 1G)'
    )
    parser.add_argument(
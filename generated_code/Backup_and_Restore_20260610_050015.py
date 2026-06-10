```python
#!/usr/bin/env python3
"""
Backup and Restore Automation Script

This script automates database backup and restore operations with comprehensive
error handling, logging, and validation checks.

Features:
- Database backup with compression
- Backup verification and integrity checks
- Automated cleanup of old backups
- Restore functionality with safety checks
- Idempotent operations with proper error handling
"""

import os
import sys
import subprocess
import logging
import argparse
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/backup_restore.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BackupRestoreManager:
    """Manages database backup and restore operations."""

    def __init__(self, db_name: str, db_user: str, backup_dir: str, 
                 retention_days: int = 30, db_password: Optional[str] = None,
                 db_host: str = 'localhost', db_port: int = 3306):
        """
        Initialize backup/restore manager.

        Args:
            db_name: Name of the database to backup/restore
            db_user: Database user with backup privileges
            backup_dir: Directory to store backups
            retention_days: Number of days to retain backups
            db_password: Database password (optional, can use .my.cnf)
            db_host: Database host
            db_port: Database port
        """
        self.db_name = db_name
        self.db_user = db_user
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.db_password = db_password
        self.db_host = db_host
        self.db_port = db_port
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def _ensure_backup_directory(self) -> bool:
        """
        Ensure backup directory exists with proper permissions.

        Returns:
            bool: True if directory exists or was created successfully
        """
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Backup directory ready: {self.backup_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup directory: {e}")
            return False

    def _build_mysql_command(self, command_type: str) -> list:
        """
        Build MySQL command with authentication parameters.

        Args:
            command_type: Type of command ('dump' or 'restore')

        Returns:
            list: Command components
        """
        base_cmd = []
        
        if command_type == 'dump':
            base_cmd = ['mysqldump']
        elif command_type == 'restore':
            base_cmd = ['mysql']
        
        base_cmd.extend([
            f'-h{self.db_host}',
            f'-P{self.db_port}',
            f'-u{self.db_user}'
        ])
        
        if self.db_password:
            base_cmd.append(f'-p{self.db_password}')
        
        if command_type == 'dump':
            base_cmd.extend([
                '--single-transaction',
                '--quick',
                '--lock-tables=false',
                self.db_name
            ])
        elif command_type == 'restore':
            base_cmd.append(self.db_name)
        
        return base_cmd

    def _calculate_checksum(self, filepath: Path) -> str:
        """
        Calculate SHA256 checksum of a file.

        Args:
            filepath: Path to the file

        Returns:
            str: Hexadecimal checksum
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def backup_database(self) -> Tuple[bool, Optional[str]]:
        """
        Perform database backup with compression and verification.

        Returns:
            Tuple[bool, Optional[str]]: Success status and backup file path
        """
        # Ensure backup directory exists
        if not self._ensure_backup_directory():
            return False, None

        backup_file = self.backup_dir / f"{self.db_name}_{self.timestamp}.sql.gz"
        checksum_file = self.backup_dir / f"{self.db_name}_{self.timestamp}.sql.gz.sha256"

        try:
            logger.info(f"Starting backup of database '{self.db_name}'...")

            # Build mysqldump command
            dump_cmd = self._build_mysql_command('dump')

            # Execute backup with compression
            with gzip.open(backup_file, 'wb') as gz_file:
                process = subprocess.Popen(
                    dump_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Stream data to compressed file
                for line in process.stdout:
                    gz_file.write(line)
                
                process.wait()
                
                if process.returncode != 0:
                    error_output = process.stderr.read().decode('utf-8')
                    logger.error(f"Backup failed: {error_output}")
                    if backup_file.exists():
                        backup_file.unlink()
                    return False, None

            logger.info(f"Backup completed: {backup_file}")

            # Verify backup integrity
            if not self._verify_backup(backup_file):
                logger.error("Backup verification failed")
                backup_file.unlink()
                return False, None

            # Calculate and save checksum
            checksum = self._calculate_checksum(backup_file)
            with open(checksum_file, 'w') as f:
                f.write(f"{checksum}  {backup_file.name}\n")
            logger.info(f"Checksum saved: {checksum}")

            # Display backup size
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            logger.info(f"Backup size: {size_mb:.2f} MB")

            # Clean old backups
            self._cleanup_old_backups()

            return True, str(backup_file)

        except Exception as e:
            logger.error(f"Backup operation failed: {e}")
            if backup_file.exists():
                backup_file.unlink()
            return False, None

    def _verify_backup(self, backup_file: Path) -> bool:
        """
        Verify backup file integrity.

        Args:
            backup_file: Path to backup file

        Returns:
            bool: True if backup is valid
        """
        try:
            logger.info("Verifying backup integrity...")
            
            # Test gzip file integrity
            with gzip.open(backup_file, 'rb') as gz_file:
                # Read in chunks to verify entire file
                chunk_size = 8192
                while True:
                    chunk = gz_file.read(chunk_size)
                    if not chunk:
                        break
            
            logger.info("Backup verification successful")
            return True
        
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def _cleanup_old_backups(self) -> None:
        """Remove backups older than retention period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            removed_count = 0

            logger.info(f"Cleaning backups older than {self.retention_days} days...")

            for backup_file in self.backup_dir.glob(f"{self.db_name}_*.sql.gz"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    # Remove backup file
                    backup_file.unlink()
                    removed_count += 1
                    
                    # Remove associated checksum file if exists
                    checksum_file = Path(str(backup_file) + '.sha256')
                    if checksum_file.exists():
                        checksum_file.unlink()
                    
                    logger.info(f"Removed old backup: {backup_file.name}")

            logger.info(f"Cleanup completed. Removed {removed_count} old backup(s)")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def list_backups(self) -> list:
        """
        List all available backups.

        Returns:
            list: List of backup file paths
        """
        backups = sorted(
            self.backup_dir.glob(f"{self.db_name}_*.sql.gz"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        logger.info(f"Found {len(backups)} backup(s):")
        for backup in backups:
            size_mb = backup.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            logger.info(f"  - {backup.name} ({size_mb:.2f} MB, {mtime})")
        
        return [str(b) for b in backups]

    def restore_database(self, backup_file: Optional[str] = None, 
                        force: bool = False) -> bool:
        """
        Restore database from backup.

        Args:
            backup_file: Path to backup file (uses latest if None)
            force: Skip confirmation prompts

        Returns:
            bool: True if restore successful
        """
        try:
            # Determine backup file to use
            if backup_file:
                backup_path = Path(backup_file)
                if not backup_path.exists():
                    logger.error(f"Backup file not found: {backup_file}")
                    return False
            else:
                # Use latest backup
                backups = list(self.backup_dir.glob(f"{self.db_name}_*.sql.gz"))
                if not backups:
                    logger.error("No backups found")
                    return False
                backup_path = max(backups, key=lambda x: x.stat().st_mtime)
                logger.info(f"Using latest backup: {backup_path.name}")

            # Verify backup before restore
            if not self._verify_backup(backup_path):
                logger.error("Backup verification failed, aborting restore")
                return False

            # Verify checksum if available
            checksum_file = Path(str(backup_path) + '.sha256')
            if checksum_file.exists():
                with open(checksum_file, 'r') as f:
                    stored_checksum = f.read().split()[0]
                current_checksum = self._calculate_checksum(backup_path)
                if stored_checksum != current_checksum:
                    logger.error("Checksum mismatch! Backup may be corrupted")
                    if not force:
                        return False
                    logger.warning("Continuing restore despite checksum mismatch (force=True)")
                else:
                    logger.info("Checksum verification passed")

            # Safety confirmation
            if not force:
                logger.warning(f"WARNING: This will restore database '{self.db_name}'")
                logger.warning("All current data will be replaced!")
                response = input("Continue? (yes/no): ")
                if response.lower() != 'yes':
                    logger.info("Restore cancelled by user")
                    return False

            logger.info(f"Starting restore of database '{self.db_name}'...")

            # Build mysql restore command
            restore_cmd = self._build_mysql_command('restore')

            # Execute restore
            with gzip.open(backup_path, 'rb') as gz_file:
                process = subprocess.Popen(
                    restore_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Stream decompressed data to mysql
                shutil.copyfileobj(gz_file, process.stdin)
                process.stdin.close()
                process.wait()
                
                if process.returncode != 0:
                    error_output = process.stderr.read().decode('utf-8')
                    logger.error(f"Restore failed: {error_output}")
                    return False

            logger.info("Database restore completed successfully")
            return True

        except Exception as e:
            logger.error(f"Restore operation failed: {e}")
            return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Database Backup and Restore Automation'
    )
    parser.add_argument(
        'action',
        choices=['backup', 'restore', 'list'],
        help='Action to perform'
    )
    parser.add_argument(
        '--db-name',
        required=True,
        help='Database name'
    )
    parser.add_argument(
        '--db-user',
        required=True,
        help='Database user'
    )
    parser.add_argument(
        '--db-password',
        help='Database password (optional, can use .my.cnf)'
    )
    parser.add_argument(
        '--db-host',
        default='localhost',
        help='Database host (default: localhost)'
    )
    parser.add_argument(
        '--db-port',
        type=int,
        default=3306,
        help='Database port (default: 3306)'
    )
    parser.add_argument(
        '--backup-dir',
        default='/backup/mysql',
        help='Backup directory (default: /backup/mysql)'
    )
    parser.add_argument(
        '--retention-days',
        type=int,
        default=30,
        help='Backup retention in days (default: 30)'
    )
    parser.add_argument(
        '--backup-file',
        help='Specific backup file to restore (for restore action)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompts'
    )

    args = parser.parse_args()

    # Initialize manager
    manager = BackupRestoreManager(
        db_name=args.db_name,
        db_user=args.db_user,
        backup_dir=args.backup_dir,
        retention_days=args.retention_days,
        db_password=args.db_password,
        db_host=args.db_host,
        db_port=args.db_port
    )

    # Execute requested action
    try:
        if args.action == 'backup':
            success, backup_file = manager.backup_database()
            sys.exit(0 if success else 1)
        
        elif args.action == 'restore':
            success = manager.restore_database(
                backup_file=args.backup_file,
                force=args.force
            )
            sys.exit(0 if success else 1)
        
        elif args.action == 'list':
            manager.list_backups()
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
```
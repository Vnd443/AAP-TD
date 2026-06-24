# Backup and Restore Runbook

## Problem Description

This runbook handles backup and restore operations\.

- Database backup failed
- Need to restore from backup
- Backup verification required
- Automated backup not running

## Manual Resolution Steps

1\. Check backup location: ls \-lh /backup/

2\. Verify backup integrity

3\. Stop application if needed

4\. Restore from backup

5\. Verify restored data

6\. Restart application

## Automation Script

Shell Script Template:

\#\!/bin/bash  
\# Database Backup Script  
  
DB\_NAME="mydb"  
DB\_USER="backup\_user"  
BACKUP\_DIR="/backup/mysql"  
DATE=$\(date \+%Y%m%d\_%H%M%S\)  
BACKUP\_FILE="$\{BACKUP\_DIR\}/$\{DB\_NAME\}\_$\{DATE\}\.sql\.gz"  
RETENTION\_DAYS=30  
  
\# Create backup directory if not exists  
mkdir \-p $\{BACKUP\_DIR\}  
  
\# Perform backup  
echo "Starting backup of $\{DB\_NAME\}\.\.\."  
mysqldump \-u $\{DB\_USER\} $\{DB\_NAME\} | gzip > $\{BACKUP\_FILE\}  
  
if \[ $? \-eq 0 \]; then  
    echo "Backup completed: $\{BACKUP\_FILE\}"  
      
    \# Verify backup  
    gunzip \-t $\{BACKUP\_FILE\}  
    if \[ $? \-eq 0 \]; then  
        echo "Backup verification successful"  
    else  
        echo "ERROR: Backup verification failed"  
        exit 1  
    fi  
      
    \# Clean old backups  
    find $\{BACKUP\_DIR\} \-name "$\{DB\_NAME\}\_\*\.sql\.gz" \-mtime \+$\{RETENTION\_DAYS\} \-delete  
    echo "Old backups cleaned \(older than $\{RETENTION\_DAYS\} days\)"  
else  
    echo "ERROR: Backup failed"  
    exit 1  
fi  
  
\# Display backup size  
ls \-lh $\{BACKUP\_FILE\}  


## Configurable Parameters

- DB\_NAME: Database name to backup
- DB\_USER: Database user with backup privileges
- BACKUP\_DIR: Backup destination directory
- RETENTION\_DAYS: Number of days to keep backups


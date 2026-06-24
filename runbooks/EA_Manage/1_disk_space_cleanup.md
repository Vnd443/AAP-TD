# Disk Space Cleanup Runbook

## Problem Description

This runbook addresses issues related to disk space exhaustion on Linux servers\.

- Server disk space exceeds 90% utilization
- /var or /tmp partition full
- Log files consuming excessive disk space
- Application unable to write due to disk full

## Manual Resolution Steps

1\. Check disk usage: df \-h

2\. Identify large files: du \-sh /var/\* | sort \-rh | head \-10

3\. Review log files: ls \-lh /var/log/

4\. Clean old logs: find /var/log \-type f \-mtime \+30 \-delete

5\. Verify space: df \-h

## Automation Approach

This runbook can be automated using Shell Script to:

- Automatically check disk usage percentage
- Clean old log files based on age threshold
- Remove temporary files from /tmp directory
- Send notifications when cleanup is performed

## Configurable Parameters

- TARGET\_PATH: Directory to clean \(default: /var/log\)
- DAYS\_OLD: Age threshold in days \(default: 30\)
- THRESHOLD: Disk usage percentage to trigger cleanup \(default: 90\)


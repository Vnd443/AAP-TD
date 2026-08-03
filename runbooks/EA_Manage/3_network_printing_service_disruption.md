Network Printing Service Disruption

# Problem Description

This runbook handles network printer outages where users are unable to print, jobs are stuck in the queue, or the printer reports offline\. It covers restarting the print spooler service, clearing the print queue, and reconnecting the network print device\.

Common scenarios:

- Printer reported offline on a floor or department
- Users unable to print invoices or documents
- Print jobs stuck or queued and not processing
- Print spooler service stopped or hung

# Manual Resolution Steps

1\. Check print spooler status

   systemctl status cups   \# or: sc query spooler \(Windows\)

2\. List stuck print jobs

   lpstat \-o   \# or: Get\-PrintJob \-PrinterName <printer>

3\. Clear the print queue

   cancel \-a <printer>   \# or: Restart\-Service Spooler

4\. Restart the print spooler service

   systemctl restart cups

5\. Verify printer connectivity

   ping <printer\_ip>

6\. Send a test print

   echo test | lp \-d <printer>

# Automation Approach

The automation uses Ansible to:

- Detect the print service name based on OS \(cups / spooler\)
- Clear stuck jobs from the print queue
- Restart the print spooler with retry logic
- Verify printer network reachability after restart
- Log all actions for audit trail

# Configurable Parameters

- printer\_name: Name of the target printer/queue
- printer\_ip: IP address of the network printer for health checks
- clear\_queue: Whether to purge stuck jobs before restart \(default: true\)
- max\_restart\_attempts: Number of retry attempts \(default: 3\)
- health\_check\_delay: Delay between connectivity checks in seconds \(default: 10\)

# Prerequisites

- Ansible installed on control node
- SSH/WinRM access to the print server
- Sudo/administrator privileges on the print server
- Printer IP is reachable from the print server

# Execution Instructions

1\. Review the generated playbook

2\. Update inventory file with the print server host

3\. Perform dry run:

   ansible\-playbook \-i inventory printer\_recovery\.yml \-\-check

4\. Execute playbook:

   ansible\-playbook \-i inventory printer\_recovery\.yml

5\. Monitor execution logs

6\. Confirm printing is restored

# Validation Steps

After execution, verify:

- Print spooler service status is "active"
- Print queue is empty of stuck jobs
- Printer responds to ping / is reachable
- Test print completes successfully
- No errors in spooler logs

# Rollback Procedure

If recovery fails:

1\. Check spooler logs for errors

2\. Verify the printer IP and port configuration

3\. Power\-cycle the physical printer

4\. Re\-add the printer/queue manually

5\. Contact the network team if the device is unreachable

# Troubleshooting

Common Issues:

- Printer offline \- Verify network cable / IP and power
- Stuck queue \- Purge jobs before restarting the spooler
- Driver mismatch \- Reinstall the correct print driver
- Permission issues \- Verify admin/sudo access
- Firewall blocking port 631/9100 \- Check firewall rules

Log Locations:

- Ansible execution log: /var/log/ansible\_printer\_recovery\_\*\.log
- CUPS logs: /var/log/cups/
- Windows spooler: Event Viewer > Microsoft\-Windows\-PrintService

# Best Practices

- Confirm the printer IP before restart
- Purge only stuck jobs, preserve active ones where possible
- Schedule bulk restarts during low\-usage windows
- Keep a record of printer\-to\-queue mappings
- Monitor spooler health and set up offline alerts


Service Restart

# Problem Description

This runbook handles service failures and restart procedures for various services including web servers, application servers, and database services\.

Common scenarios:

- Application service not responding
- Web server down or unresponsive
- Database service stopped unexpectedly
- Service failed health checks

# Manual Resolution Steps

1\. Check service status

   systemctl status <service>

2\. Review service logs

   journalctl \-u <service> \-n 50

3\. Test configuration \(for Apache/Nginx\)

   apache2ctl \-t  \# or httpd \-t

4\. Restart service

   systemctl restart <service>

5\. Verify service is running

   systemctl status <service>

6\. Test service functionality

   curl http://localhost:<port>

# Automation Approach

The automation uses Ansible to:

- Detect the correct service name based on OS
- Validate configuration before restart
- Perform restart with retry logic
- Verify service health after restart
- Log all actions for audit trail

# Configurable Parameters

- service\_name: Name of the service to restart \(e\.g\., httpd, apache2, nginx, tomcat\)
- service\_port: Port number for health checks \(default: 80\)
- max\_restart\_attempts: Number of retry attempts \(default: 3\)
- health\_check\_retries: Health check retry count \(default: 5\)
- health\_check\_delay: Delay between health checks in seconds \(default: 10\)

# Prerequisites

- Ansible installed on control node
- SSH access to target servers
- Sudo/root privileges on target servers
- Service configuration files are valid

# Execution Instructions

1\. Review the generated playbook

2\. Update inventory file with target hosts

3\. Perform dry run:

   ansible\-playbook \-i inventory service\_restart\.yml \-\-check

4\. Execute playbook:

   ansible\-playbook \-i inventory service\_restart\.yml

5\. Monitor execution logs

6\. Verify service is operational

# Validation Steps

After execution, verify:

- Service status is "active"
- Service is listening on expected port
- HTTP/HTTPS requests return valid responses
- Application functionality is restored
- No errors in service logs

# Rollback Procedure

If restart fails:

1\. Check service logs for errors

2\. Verify configuration syntax

3\. Restore previous configuration from backup

4\. Attempt manual restart

5\. Contact support team if issues persist

# Troubleshooting

Common Issues:

- Configuration syntax errors \- Run config test before restart
- Port conflicts \- Check if port is already in use
- Permission issues \- Verify sudo access
- Service dependencies \- Ensure dependent services are running
- Firewall blocking \- Check firewall rules

Log Locations:

- Ansible execution log: /var/log/ansible\_service\_restart\_\*\.log
- Service logs: /var/log/<service>/
- System logs: journalctl \-u <service>

# Best Practices

- Always test configuration before restart
- Perform dry run in non\-production first
- Schedule restarts during maintenance windows
- Keep backup of working configuration
- Document all changes
- Monitor service after restart
- Set up alerts for service failures


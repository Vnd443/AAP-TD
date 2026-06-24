#!/usr/bin/env pwsh

param(
    [string]$service_name = "nginx",
    [int]$service_port = 80,
    [int]$max_restart_attempts = 3,
    [int]$health_check_retries = 5,
    [int]$health_check_delay = 10
)

$logFile = "/var/log/service_restart_$(Get-Date -Format yyyyMMdd_HHmmss).log"

function Log {
    param([string]$msg)
    $timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    "$timestamp $msg" | Tee-Object -FilePath $logFile -Append
}

function RunCmd {
    param([string]$cmd)
    Log "Executing: $cmd"
    $output = bash -c "$cmd" 2>&1
    Log $output
    return $output
}

Log "=== Service Restart Script Started ==="
Log "Service: $service_name Port: $service_port"

Log "Checking service status..."
RunCmd "systemctl status $service_name"

Log "Reviewing last 50 log lines..."
RunCmd "journalctl -u $service_name -n 50"

if ($service_name -eq "apache2" -or $service_name -eq "httpd") {
    Log "journalctl -u $service_name -n 50"

if ($service_name -eq "apache2" -or $service_name -eq "httpd") {
    Log "Running Apache configuration test..."
    $confTest = RunCmd "apache2ctl -t 2>/dev/null || httpd -t 2>/dev/null"
    if ($confTest -notmatch "Syntax OK") {
        Log "Configuration test failed. Aborting restart."
        exit 1
    }
}

$attempt = 1
$restartSuccess = $false

while ($attempt -le $max_restart_attempts -and -not $restartSuccess) {
    Log "Restart attempt $attempt of $max_restart_attempts"
    RunCmd "systemctl restart $service_name"

    Start-Sleep -Seconds 3

    $status = RunCmd "systemctl is-active $service_name"
    if ($status -match "active") {
        Log "Service restart successful."
        $restartSuccess = $true
    } else {
        Log "Service restart failed."
    }

    $attempt++
}

if (-not $restartSuccess) {
    Log "All restart attempts failed. Exiting."
    exit 1
}

Log "Verifying service health..."
$healthy = $false
for ($i = 1; $i -le $health_check_retries -and -not $healthy; $i++) {
    Log "Health check $i of $health_check_retries"
    $curl = RunCmd "curl -s -o /dev/null -w '%{http_code}' http://localhost:$service_port"
    if ($curl -eq "200") {
        Log "Health check passed."
        $healthy = $true
    } else {
        Log "Health check failed. Waiting $health_check_delay seconds."
        Start-Sleep -Seconds $health_check_delay
    }
}

if (-not $healthy) {
    Log "Service did not pass health checks. Manual intervention required."
    exit 1
}

Log "Final service status:"
RunCmd "systemctl status $service_name"

Log "=== Service Restart Completed Successfully ==="
exit 0
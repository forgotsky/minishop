<#
.SYNOPSIS
    Setup Checkpoint Service - Windows Task Scheduler

.DESCRIPTION
    Creates a scheduled task that monitors Claude sessions for context warnings
    and automatically creates checkpoints.

.PARAMETER Action
    The action to perform: install, uninstall, or status

.EXAMPLE
    .\setup-checkpoint-service.ps1 -Action install
    .\setup-checkpoint-service.ps1 -Action uninstall
    .\setup-checkpoint-service.ps1 -Action status

.NOTES
    Version: 1.0.0
    Requires: PowerShell 5.1+, Python 3.9+, Administrator rights for install/uninstall
#>

#Requires -Version 5.1

param(
    [ValidateSet("install", "uninstall", "status")]
    [string]$Action = "install"
)

# Configuration
$script:ProjectRoot = (Get-Item "$PSScriptRoot\.." -ErrorAction SilentlyContinue).FullName
$script:ScriptPath = Join-Path $script:ProjectRoot "tooling\scripts\context_checkpoint.py"
$script:TaskName = "ClaudeCheckpointService"
$script:LogDir = Join-Path $script:ProjectRoot "tooling\.automation\logs"

function Write-Header {
    Write-Host ""
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor Blue
    Write-Host "  Context Checkpoint Service Setup (Windows)" -ForegroundColor Blue
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor Blue
    Write-Host ""
}

function Test-Prerequisites {
    Write-Host "[i] Checking prerequisites..." -ForegroundColor Blue

    # Check Python
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Host "X Python 3 is required but not installed" -ForegroundColor Red
        Write-Host "  Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
        return $false
    }

    # Check script exists
    if (-not (Test-Path $script:ScriptPath)) {
        Write-Host "X Checkpoint script not found at: $script:ScriptPath" -ForegroundColor Red
        return $false
    }

    Write-Host "[OK] Prerequisites OK" -ForegroundColor Green
    return $true
}

function Install-CheckpointService {
    Write-Host "[i] Creating Windows Task Scheduler task..." -ForegroundColor Blue

    # Ensure log directory exists
    if (-not (Test-Path $script:LogDir)) {
        New-Item -ItemType Directory -Path $script:LogDir -Force | Out-Null
    }

    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName $script:TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "[i] Removing existing task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $script:TaskName -Confirm:$false
    }

    # Create the action
    $watchLog = Join-Path $script:LogDir "current.log"
    $pythonPath = (Get-Command python).Source
    $arguments = "`"$script:ScriptPath`" --watch-log `"$watchLog`""

    $action = New-ScheduledTaskAction `
        -Execute $pythonPath `
        -Argument $arguments `
        -WorkingDirectory $script:ProjectRoot

    # Create trigger (at logon)
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

    # Create settings
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Days 365)

    # Create principal (run as current user)
    $principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Limited

    try {
        # Register the task
        Register-ScheduledTask `
            -TaskName $script:TaskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Principal $principal `
            -Description "Monitors Claude Code sessions for context warnings and creates checkpoints" `
            -Force | Out-Null

        Write-Host "[OK] Task created: $script:TaskName" -ForegroundColor Green

        # Start the task
        Start-ScheduledTask -TaskName $script:TaskName -ErrorAction SilentlyContinue
        Write-Host "[OK] Task started" -ForegroundColor Green

        return $true
    }
    catch {
        Write-Host "X Failed to create task: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Try running PowerShell as Administrator" -ForegroundColor Yellow
        return $false
    }
}

function Uninstall-CheckpointService {
    Write-Host "[i] Uninstalling checkpoint service..." -ForegroundColor Blue

    $task = Get-ScheduledTask -TaskName $script:TaskName -ErrorAction SilentlyContinue
    if ($task) {
        # Stop the task if running
        Stop-ScheduledTask -TaskName $script:TaskName -ErrorAction SilentlyContinue

        # Unregister the task
        Unregister-ScheduledTask -TaskName $script:TaskName -Confirm:$false
        Write-Host "[OK] Service uninstalled" -ForegroundColor Green
    }
    else {
        Write-Host "[i] Task not found, nothing to uninstall" -ForegroundColor Yellow
    }
}

function Get-ServiceStatus {
    Write-Host "[i] Checking service status..." -ForegroundColor Blue
    Write-Host ""

    $task = Get-ScheduledTask -TaskName $script:TaskName -ErrorAction SilentlyContinue

    if (-not $task) {
        Write-Host "Status: NOT INSTALLED" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To install, run:" -ForegroundColor Gray
        Write-Host "  .\setup-checkpoint-service.ps1 -Action install" -ForegroundColor Cyan
        return
    }

    $taskInfo = Get-ScheduledTaskInfo -TaskName $script:TaskName -ErrorAction SilentlyContinue

    Write-Host "Task Name:    $($task.TaskName)" -ForegroundColor White
    Write-Host "State:        $($task.State)" -ForegroundColor $(if ($task.State -eq 'Running') { 'Green' } else { 'Yellow' })
    Write-Host "Last Run:     $($taskInfo.LastRunTime)" -ForegroundColor Gray
    Write-Host "Next Run:     $($taskInfo.NextRunTime)" -ForegroundColor Gray
    Write-Host "Last Result:  $($taskInfo.LastTaskResult)" -ForegroundColor $(if ($taskInfo.LastTaskResult -eq 0) { 'Green' } else { 'Yellow' })
}

function Write-Usage {
    Write-Host ""
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor Green
    Write-Host "  Setup Complete!" -ForegroundColor Green
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor Green
    Write-Host ""
    Write-Host "The context checkpoint service is now running as a scheduled task."
    Write-Host ""
    Write-Host "Service Management:" -ForegroundColor Blue
    Write-Host "  * Start:   Start-ScheduledTask -TaskName '$script:TaskName'"
    Write-Host "  * Stop:    Stop-ScheduledTask -TaskName '$script:TaskName'"
    Write-Host "  * Status:  .\setup-checkpoint-service.ps1 -Action status"
    Write-Host "  * Remove:  .\setup-checkpoint-service.ps1 -Action uninstall"
    Write-Host ""
    Write-Host "Or use Task Scheduler GUI:" -ForegroundColor Blue
    Write-Host "  taskschd.msc"
    Write-Host ""
    Write-Host "Logs:" -ForegroundColor Blue
    Write-Host "  * Watch log:     $script:LogDir\current.log"
    Write-Host "  * Checkpoints:   tooling\.automation\checkpoints\"
    Write-Host ""
    Write-Host "Quick Commands:" -ForegroundColor Blue
    Write-Host "  * Create checkpoint:  python tooling\scripts\context_checkpoint.py --checkpoint"
    Write-Host "  * List checkpoints:   python tooling\scripts\context_checkpoint.py --list"
    Write-Host "  * Resume session:     python tooling\scripts\context_checkpoint.py --resume <id>"
    Write-Host ""
}

# Main execution
Write-Header

switch ($Action) {
    "install" {
        if (Test-Prerequisites) {
            if (Install-CheckpointService) {
                Write-Usage
            }
        }
    }
    "uninstall" {
        Uninstall-CheckpointService
    }
    "status" {
        Get-ServiceStatus
    }
}

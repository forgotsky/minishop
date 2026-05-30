<#
.SYNOPSIS
    Checkpoint Integration Library for Windows

.DESCRIPTION
    Functions to integrate context checkpointing into existing automation workflows.
    PowerShell equivalent of checkpoint-integration.sh for Windows compatibility.

.NOTES
    Version: 1.0.0
    Requires: PowerShell 5.1+, Python 3.9+
#>

#Requires -Version 5.1

# Script paths
$script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:ProjectRoot = (Get-Item "$script:ScriptDir\..\..\.." -ErrorAction SilentlyContinue).FullName
if (-not $script:ProjectRoot) {
    $script:ProjectRoot = (Get-Location).Path
}
$script:CheckpointScript = Join-Path $script:ProjectRoot "tooling\scripts\context_checkpoint.py"
$script:CheckpointDir = Join-Path $script:ProjectRoot "tooling\.automation\checkpoints"

#region Checkpoint Monitor Functions

function Start-CheckpointMonitor {
    <#
    .SYNOPSIS
        Start checkpoint monitor in background
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$LogFile,

        [string]$SessionId = "auto"
    )

    if (-not (Test-Path $script:CheckpointScript)) {
        Write-Host "!! Checkpoint script not found, skipping monitoring" -ForegroundColor Yellow
        return $null
    }

    Write-Host "[i] Starting context checkpoint monitor..." -ForegroundColor Blue
    Write-Host "   Watching: $LogFile" -ForegroundColor Gray

    # Start monitor as background job
    $job = Start-Job -ScriptBlock {
        param($script, $logFile, $sessionId)
        python $script --watch-log $logFile --session-id $sessionId
    } -ArgumentList $script:CheckpointScript, $LogFile, $SessionId

    # Save PID to file
    $pidFile = "$LogFile.checkpoint.pid"
    $job.Id | Out-File -FilePath $pidFile -Force

    Write-Host "[OK] Checkpoint monitor started (Job ID: $($job.Id))" -ForegroundColor Green
    return $job.Id
}

function Stop-CheckpointMonitor {
    <#
    .SYNOPSIS
        Stop checkpoint monitor by PID file
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$LogFile
    )

    $pidFile = "$LogFile.checkpoint.pid"

    if (Test-Path $pidFile) {
        $jobId = Get-Content $pidFile -Raw
        $jobId = $jobId.Trim()

        $job = Get-Job -Id $jobId -ErrorAction SilentlyContinue
        if ($job) {
            Write-Host "[i] Stopping checkpoint monitor (Job ID: $jobId)" -ForegroundColor Blue
            Stop-Job -Id $jobId -ErrorAction SilentlyContinue
            Remove-Job -Id $jobId -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Checkpoint monitor stopped" -ForegroundColor Green
        }

        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

#endregion

#region Checkpoint Management Functions

function New-StoryCheckpoint {
    <#
    .SYNOPSIS
        Create manual checkpoint with context
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$StoryKey,

        [string]$Reason = "manual"
    )

    Write-Host "[i] Creating checkpoint for story: $StoryKey" -ForegroundColor Blue

    $result = python $script:CheckpointScript --checkpoint --session-id $StoryKey 2>&1
    Write-Host $result

    return $LASTEXITCODE
}

function Test-HasCheckpoint {
    <#
    .SYNOPSIS
        Check if checkpoint exists for story
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$StoryKey
    )

    $checkpoints = Get-ChildItem -Path $script:CheckpointDir -Filter "*$StoryKey*.json" -ErrorAction SilentlyContinue

    return ($null -ne $checkpoints -and $checkpoints.Count -gt 0)
}

function Get-LatestCheckpoint {
    <#
    .SYNOPSIS
        Get latest checkpoint for story
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$StoryKey
    )

    $checkpoints = Get-ChildItem -Path $script:CheckpointDir -Filter "*$StoryKey*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($checkpoints) {
        return $checkpoints.FullName
    }
    return $null
}

function Resume-FromCheckpoint {
    <#
    .SYNOPSIS
        Resume from latest checkpoint
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$StoryKey
    )

    $checkpointFile = Get-LatestCheckpoint -StoryKey $StoryKey

    if (-not $checkpointFile) {
        Write-Host "X No checkpoint found for story: $StoryKey" -ForegroundColor Red
        return 1
    }

    $checkpointId = [System.IO.Path]::GetFileNameWithoutExtension($checkpointFile)

    Write-Host "[i] Resuming from checkpoint: $checkpointId" -ForegroundColor Blue

    python $script:CheckpointScript --resume $checkpointId

    return $LASTEXITCODE
}

function Remove-OldCheckpoints {
    <#
    .SYNOPSIS
        Clean up old checkpoints (keep last N)
    #>
    param(
        [int]$KeepCount = 10
    )

    Write-Host "[i] Cleaning up old checkpoints (keeping last $KeepCount)..." -ForegroundColor Blue

    $checkpoints = Get-ChildItem -Path $script:CheckpointDir -Filter "checkpoint_*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending

    if (-not $checkpoints -or $checkpoints.Count -le $KeepCount) {
        Write-Host "[OK] No cleanup needed ($($checkpoints.Count) checkpoints)" -ForegroundColor Green
        return
    }

    $toDelete = $checkpoints | Select-Object -Skip $KeepCount
    $deleteCount = $toDelete.Count

    foreach ($file in $toDelete) {
        $summaryFile = $file.FullName -replace '\.json$', '_summary.md'
        Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
        Remove-Item $summaryFile -Force -ErrorAction SilentlyContinue
    }

    Write-Host "[OK] Deleted $deleteCount old checkpoints" -ForegroundColor Green
}

#endregion

#region Logging Functions

function Write-CheckpointInfo {
    <#
    .SYNOPSIS
        Add checkpoint info to log
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$LogFile
    )

    $info = @"

===============================================================
  CONTEXT CHECKPOINT MONITORING ACTIVE
===============================================================

Thresholds:
  * Warning:   75% - Log notification
  !! Critical:  85% - Auto-checkpoint created
  XX Emergency: 95% - Force checkpoint + alert

Checkpoint directory: $script:CheckpointDir

To manually checkpoint: python tooling\scripts\context_checkpoint.py --checkpoint
To list checkpoints:    python tooling\scripts\context_checkpoint.py --list

===============================================================

"@

    Add-Content -Path $LogFile -Value $info
}

#endregion

# Export functions
Export-ModuleMember -Function * -ErrorAction SilentlyContinue

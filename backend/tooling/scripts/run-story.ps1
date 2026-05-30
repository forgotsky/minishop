<#
.SYNOPSIS
    RUN-STORY - Automated Story Implementation with Live Monitoring

.DESCRIPTION
    Invokes Claude Code to implement a story automatically while keeping
    the main terminal available for live monitoring of context usage,
    costs, and agent status.

.PARAMETER StoryKey
    The story key to process (e.g., "3-5" or full key)

.PARAMETER Develop
    Run development phase only

.PARAMETER Review
    Run review phase only

.PARAMETER Context
    Create story context only

.PARAMETER NoCommit
    Disable auto-commit after development

.PARAMETER WithPR
    Enable auto-PR creation (requires gh CLI)

.PARAMETER Model
    Claude model to use (sonnet|opus|haiku)

.PARAMETER NoMonitor
    Disable live monitoring (run in foreground)

.EXAMPLE
    .\run-story.ps1 -StoryKey "3-5"
    .\run-story.ps1 -StoryKey "3-5" -Develop
    .\run-story.ps1 -StoryKey "3-5" -Model opus -WithPR

.NOTES
    Version: 1.0.0
    Core tasks run as background jobs with live monitoring in the main terminal.
#>

#Requires -Version 5.1

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$StoryKey,

    [switch]$Develop,
    [switch]$Review,
    [switch]$Context,
    [switch]$NoCommit,
    [switch]$WithPR,
    [switch]$NoMonitor,

    [ValidateSet("sonnet", "opus", "haiku")]
    [string]$Model = "sonnet"
)

# Script paths
$script:ScriptDir = $PSScriptRoot
$script:ProjectRoot = (Get-Item "$script:ScriptDir\.." -ErrorAction SilentlyContinue).FullName
$script:LogsDir = Join-Path $script:ProjectRoot "tooling\.automation\logs"
$script:CheckpointDir = Join-Path $script:ProjectRoot "tooling\.automation\checkpoints"

# Source libraries
. (Join-Path $script:ScriptDir "lib\claude-cli.ps1")
$checkpointLib = Join-Path $script:ScriptDir "lib\checkpoint-integration.ps1"
if (Test-Path $checkpointLib) {
    . $checkpointLib
}

# Load config
$configFile = Join-Path $script:ProjectRoot "tooling\.automation\config.ps1"
if (Test-Path $configFile) {
    . $configFile
}

# Set environment
$env:CLAUDE_MODEL = $Model
$env:AUTO_COMMIT = if ($NoCommit) { "false" } else { "true" }
$env:AUTO_PR = if ($WithPR) { "true" } else { "false" }

#region Helper Functions

function Expand-StoryKey {
    <#
    .SYNOPSIS
        Expand abbreviated story key (e.g., "3-5" -> full key)
    #>
    param([string]$InputKey)

    # If already a full key (has more than two dashes)
    if ($InputKey -match '^[0-9]+-[0-9]+-[a-z]') {
        return $InputKey
    }

    # If abbreviated (e.g., "3-5"), look up full key
    if ($InputKey -match '^[0-9]+-[0-9]+$') {
        $sprintStatus = Join-Path $script:ProjectRoot "docs\sprint-status.yaml"
        if (Test-Path $sprintStatus) {
            $content = Get-Content $sprintStatus -Raw
            $pattern = "^\s+($InputKey-[a-z][^\s:]*):"
            if ($content -match $pattern) {
                return $Matches[1]
            }
        }
    }

    return $InputKey
}

function Write-Header {
    Clear-Host
    Write-Host ""
    Write-Host ("{0}" -f ("=" * 70)) -ForegroundColor Cyan
    Write-Host "  AUTOMATED STORY RUNNER - Live Monitoring" -ForegroundColor Cyan
    Write-Host ("{0}" -f ("=" * 70)) -ForegroundColor Cyan
    Write-Host ""
}

function Write-Status {
    param(
        [string]$StoryKey,
        [string]$Mode,
        [string]$Phase,
        [datetime]$StartTime,
        [int]$ContextPercent = 0,
        [decimal]$CostUSD = 0,
        [string]$AgentStatus = "Initializing"
    )

    $elapsed = (Get-Date) - $StartTime
    $elapsedStr = "{0:mm\:ss}" -f $elapsed

    # Context bar
    $contextBar = ""
    $contextColor = "Green"
    if ($ContextPercent -gt 0) {
        $filled = [math]::Floor($ContextPercent / 5)
        $empty = 20 - $filled
        $contextBar = ("[" + ("=" * $filled) + ("-" * $empty) + "]")

        if ($ContextPercent -ge 85) { $contextColor = "Red" }
        elseif ($ContextPercent -ge 75) { $contextColor = "Yellow" }
    }

    # Clear and redraw status
    $cursorTop = [Console]::CursorTop
    if ($cursorTop -gt 10) {
        [Console]::SetCursorPosition(0, 10)
    }

    Write-Host ""
    Write-Host ("{0}" -f ("-" * 70)) -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Story:    " -NoNewline -ForegroundColor Gray
    Write-Host $StoryKey -ForegroundColor White
    Write-Host "  Mode:     " -NoNewline -ForegroundColor Gray
    Write-Host $Mode -ForegroundColor Cyan
    Write-Host "  Phase:    " -NoNewline -ForegroundColor Gray
    Write-Host $Phase -ForegroundColor Yellow
    Write-Host "  Elapsed:  " -NoNewline -ForegroundColor Gray
    Write-Host $elapsedStr -ForegroundColor White
    Write-Host ""
    Write-Host "  Agent:    " -NoNewline -ForegroundColor Gray
    Write-Host $AgentStatus -ForegroundColor $(if ($AgentStatus -eq "Running") { "Green" } else { "Yellow" })
    Write-Host "  Context:  " -NoNewline -ForegroundColor Gray
    Write-Host "$contextBar $ContextPercent%" -ForegroundColor $contextColor
    Write-Host "  Cost:     " -NoNewline -ForegroundColor Gray
    Write-Host ('${0:F2} USD' -f $CostUSD) -ForegroundColor $(if ($CostUSD -gt 10) { "Yellow" } else { "Green" })
    Write-Host ""
    Write-Host ("{0}" -f ("-" * 70)) -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Press Ctrl+C to stop monitoring (task continues in background)" -ForegroundColor DarkGray
    Write-Host ""
}

function Get-LogStats {
    <#
    .SYNOPSIS
        Parse log file for context usage and cost estimates
    #>
    param([string]$LogFile)

    $stats = @{
        ContextPercent = 0
        CostUSD = 0.0
        Status = "Unknown"
    }

    if (-not (Test-Path $LogFile)) {
        return $stats
    }

    try {
        $content = Get-Content $LogFile -Tail 100 -ErrorAction SilentlyContinue

        foreach ($line in $content) {
            # Look for context patterns
            if ($line -match 'Context:\s*(\d+)%') {
                $stats.ContextPercent = [int]$Matches[1]
            }
            if ($line -match 'Token usage:\s*(\d+)/(\d+)') {
                $used = [int]$Matches[1]
                $total = [int]$Matches[2]
                $stats.ContextPercent = [math]::Floor(($used / $total) * 100)
            }

            # Look for cost patterns
            if ($line -match '\$(\d+\.?\d*)') {
                $stats.CostUSD = [decimal]$Matches[1]
            }

            # Status indicators
            if ($line -match 'PERSONA SWITCH|Starting|Implementing') {
                $stats.Status = "Running"
            }
            if ($line -match 'Complete|Done|Finished') {
                $stats.Status = "Completed"
            }
            if ($line -match 'Error|Failed|Exception') {
                $stats.Status = "Error"
            }
        }
    }
    catch {
        # Ignore errors reading log
    }

    return $stats
}

function Start-AgentJob {
    <#
    .SYNOPSIS
        Start a Claude agent as a background job
    #>
    param(
        [string]$Phase,
        [string]$StoryKey,
        [string]$LogFile
    )

    $job = Start-Job -ScriptBlock {
        param($scriptDir, $storyKey, $phase, $logFile)

        # Source libraries in job context
        . (Join-Path $scriptDir "lib\claude-cli.ps1")

        $result = 0
        switch ($phase) {
            "context" {
                $result = Invoke-SMStoryContext -StoryKey $storyKey
            }
            "develop" {
                $result = Invoke-DevStory -StoryKey $storyKey
            }
            "review" {
                $result = Invoke-SMCodeReview -StoryKey $storyKey
            }
        }

        return $result
    } -ArgumentList $script:ScriptDir, $StoryKey, $Phase, $LogFile

    return $job
}

function Watch-AgentProgress {
    <#
    .SYNOPSIS
        Monitor agent job progress with live updates
    #>
    param(
        [System.Management.Automation.Job]$Job,
        [string]$StoryKey,
        [string]$Mode,
        [string]$Phase,
        [string]$LogFile
    )

    $startTime = Get-Date

    Write-Host "  >> Agent started for phase: $Phase" -ForegroundColor Cyan
    Write-Host "  >> Log: $LogFile" -ForegroundColor Gray
    Write-Host ""

    while ($Job.State -eq 'Running') {
        $stats = Get-LogStats -LogFile $LogFile

        Write-Status `
            -StoryKey $StoryKey `
            -Mode $Mode `
            -Phase $Phase `
            -StartTime $startTime `
            -ContextPercent $stats.ContextPercent `
            -CostUSD $stats.CostUSD `
            -AgentStatus "Running"

        Start-Sleep -Seconds 2
    }

    # Final status
    $stats = Get-LogStats -LogFile $LogFile
    $finalStatus = if ($Job.State -eq 'Completed') { "Completed" } else { "Failed" }

    Write-Status `
        -StoryKey $StoryKey `
        -Mode $Mode `
        -Phase $Phase `
        -StartTime $startTime `
        -ContextPercent $stats.ContextPercent `
        -CostUSD $stats.CostUSD `
        -AgentStatus $finalStatus

    # Get job result
    $result = Receive-Job -Job $Job
    Remove-Job -Job $Job -Force

    return $result
}

#endregion

#region Main Execution

function Main {
    # Expand story key
    $fullStoryKey = Expand-StoryKey -InputKey $StoryKey

    # Determine mode
    $mode = "full"
    if ($Develop) { $mode = "develop" }
    elseif ($Review) { $mode = "review" }
    elseif ($Context) { $mode = "context" }

    Write-Header

    Write-Host "  Story:      $fullStoryKey" -ForegroundColor White
    Write-Host "  Mode:       $mode" -ForegroundColor Cyan
    Write-Host "  Model:      $Model" -ForegroundColor Blue
    Write-Host "  Auto-Commit: $($env:AUTO_COMMIT)" -ForegroundColor Gray
    Write-Host "  Auto-PR:    $($env:AUTO_PR)" -ForegroundColor Gray
    Write-Host ""

    # Check for existing checkpoint
    if (Get-Command Test-HasCheckpoint -ErrorAction SilentlyContinue) {
        if (Test-HasCheckpoint -StoryKey $fullStoryKey) {
            Write-Host "  [!] Found existing checkpoint for story: $fullStoryKey" -ForegroundColor Cyan
            $resume = Read-Host "  Would you like to resume from checkpoint? (y/n)"
            if ($resume -match '^[Yy]') {
                Resume-FromCheckpoint -StoryKey $fullStoryKey
                return
            }
            Write-Host "  >> Starting fresh implementation..." -ForegroundColor Green
            Write-Host ""
        }
    }

    # Create pre-start checkpoint
    if (Get-Command New-StoryCheckpoint -ErrorAction SilentlyContinue) {
        Write-Host "  >> Creating pre-start checkpoint..." -ForegroundColor Blue
        New-StoryCheckpoint -StoryKey $fullStoryKey -Reason "pre-start" | Out-Null
    }

    $exitCode = 0

    if ($NoMonitor) {
        # Run in foreground (no monitoring)
        switch ($mode) {
            "context" {
                $exitCode = Invoke-SMStoryContext -StoryKey $fullStoryKey
            }
            "develop" {
                $exitCode = Invoke-DevStory -StoryKey $fullStoryKey
                if ($exitCode -eq 0) {
                    Update-StoryStatus -StoryKey $fullStoryKey -NewStatus "review"
                    if ($env:AUTO_COMMIT -eq "true") { Invoke-AutoCommit -StoryKey $fullStoryKey }
                    if ($env:AUTO_PR -eq "true") { New-AutoPR -StoryKey $fullStoryKey }
                }
            }
            "review" {
                $exitCode = Invoke-SMCodeReview -StoryKey $fullStoryKey
            }
            "full" {
                $exitCode = Start-FullPipeline -StoryKey $fullStoryKey
            }
        }
    }
    else {
        # Run as background jobs with monitoring
        switch ($mode) {
            "context" {
                $logFile = Join-Path $script:LogsDir "$fullStoryKey-context.log"
                $job = Start-AgentJob -Phase "context" -StoryKey $fullStoryKey -LogFile $logFile
                $exitCode = Watch-AgentProgress -Job $job -StoryKey $fullStoryKey -Mode $mode -Phase "Context Creation" -LogFile $logFile
            }
            "develop" {
                $logFile = Join-Path $script:LogsDir "$fullStoryKey-develop.log"
                $job = Start-AgentJob -Phase "develop" -StoryKey $fullStoryKey -LogFile $logFile
                $exitCode = Watch-AgentProgress -Job $job -StoryKey $fullStoryKey -Mode $mode -Phase "Development" -LogFile $logFile

                if ($exitCode -eq 0) {
                    Update-StoryStatus -StoryKey $fullStoryKey -NewStatus "review"
                    if ($env:AUTO_COMMIT -eq "true") { Invoke-AutoCommit -StoryKey $fullStoryKey }
                    if ($env:AUTO_PR -eq "true") { New-AutoPR -StoryKey $fullStoryKey }
                }
            }
            "review" {
                $logFile = Join-Path $script:LogsDir "$fullStoryKey-review.log"
                $job = Start-AgentJob -Phase "review" -StoryKey $fullStoryKey -LogFile $logFile
                $exitCode = Watch-AgentProgress -Job $job -StoryKey $fullStoryKey -Mode $mode -Phase "Code Review" -LogFile $logFile
            }
            "full" {
                # Full pipeline with monitoring for each phase
                $contextFile = Join-Path $script:ProjectRoot "docs\$fullStoryKey.context.xml"

                # Phase 1: Context
                if (-not (Test-Path $contextFile)) {
                    $logFile = Join-Path $script:LogsDir "$fullStoryKey-context.log"
                    $job = Start-AgentJob -Phase "context" -StoryKey $fullStoryKey -LogFile $logFile
                    $exitCode = Watch-AgentProgress -Job $job -StoryKey $fullStoryKey -Mode $mode -Phase "1/3: Context Creation" -LogFile $logFile
                    if ($exitCode -ne 0) {
                        Write-Host "`n  [X] Context creation failed" -ForegroundColor Red
                        return
                    }
                }

                # Phase 2: Development
                $logFile = Join-Path $script:LogsDir "$fullStoryKey-develop.log"
                $job = Start-AgentJob -Phase "develop" -StoryKey $fullStoryKey -LogFile $logFile
                $exitCode = Watch-AgentProgress -Job $job -StoryKey $fullStoryKey -Mode $mode -Phase "2/3: Development" -LogFile $logFile

                if ($exitCode -ne 0) {
                    Write-Host "`n  [X] Development failed" -ForegroundColor Red
                    return
                }

                Update-StoryStatus -StoryKey $fullStoryKey -NewStatus "review"
                if ($env:AUTO_COMMIT -eq "true") { Invoke-AutoCommit -StoryKey $fullStoryKey }
                if ($env:AUTO_PR -eq "true") { New-AutoPR -StoryKey $fullStoryKey }

                # Phase 3: Review
                $logFile = Join-Path $script:LogsDir "$fullStoryKey-review.log"
                $job = Start-AgentJob -Phase "review" -StoryKey $fullStoryKey -LogFile $logFile
                $exitCode = Watch-AgentProgress -Job $job -StoryKey $fullStoryKey -Mode $mode -Phase "3/3: Code Review" -LogFile $logFile

                if ($exitCode -eq 0) {
                    Update-StoryStatus -StoryKey $fullStoryKey -NewStatus "done"
                }
            }
        }
    }

    # Create completion checkpoint
    if ($exitCode -eq 0 -and $mode -ne "context") {
        if (Get-Command New-StoryCheckpoint -ErrorAction SilentlyContinue) {
            Write-Host "`n  >> Creating completion checkpoint..." -ForegroundColor Blue
            New-StoryCheckpoint -StoryKey $fullStoryKey -Reason "complete" | Out-Null
        }
    }

    # Cleanup old checkpoints
    if (Get-Command Remove-OldCheckpoints -ErrorAction SilentlyContinue) {
        Remove-OldCheckpoints -KeepCount 10
    }

    # Final message
    Write-Host ""
    if ($exitCode -eq 0) {
        Write-Host "  [OK] Complete!" -ForegroundColor Green
    }
    else {
        Write-Host "  [X] Failed with exit code: $exitCode" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "  Log files:    $script:LogsDir" -ForegroundColor Gray
    Write-Host "  Checkpoints:  $script:CheckpointDir" -ForegroundColor Gray
    Write-Host ""

    exit $exitCode
}

#endregion

# Run main
Main

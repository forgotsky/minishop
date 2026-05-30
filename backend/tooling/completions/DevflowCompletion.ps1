# Devflow PowerShell Tab Completion
#
# Installation:
# 1. Add to your PowerShell profile ($PROFILE):
#    . /path/to/devflow/tooling/completions/DevflowCompletion.ps1
#
# 2. Or import as module:
#    Import-Module /path/to/devflow/tooling/completions/DevflowCompletion.ps1

# Agent personas
$script:DevflowAgents = @(
    [PSCustomObject]@{ Name = 'SM'; Description = 'Scrum Master - Sprint coordination' }
    [PSCustomObject]@{ Name = 'DEV'; Description = 'Developer - Code implementation' }
    [PSCustomObject]@{ Name = 'BA'; Description = 'Business Analyst - Requirements' }
    [PSCustomObject]@{ Name = 'ARCHITECT'; Description = 'Architect - System design' }
    [PSCustomObject]@{ Name = 'PM'; Description = 'Product Manager - Roadmap' }
    [PSCustomObject]@{ Name = 'WRITER'; Description = 'Technical Writer - Documentation' }
    [PSCustomObject]@{ Name = 'MAINTAINER'; Description = 'Maintainer - Code quality' }
    [PSCustomObject]@{ Name = 'REVIEWER'; Description = 'Code Reviewer - Quality assurance' }
)

$script:DevflowModels = @('opus', 'sonnet', 'haiku')
$script:DevflowModes = @('swarm', 'pair', 'auto', 'sequential')

# Argument completer for run-story.ps1
Register-ArgumentCompleter -CommandName 'run-story.ps1', 'run-story' -Native -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $params = @(
        @{ Name = '-Swarm'; Tooltip = 'Enable swarm mode (multi-agent debate)' }
        @{ Name = '-Pair'; Tooltip = 'Enable pair programming mode' }
        @{ Name = '-Auto'; Tooltip = 'Enable auto-routing mode' }
        @{ Name = '-Sequential'; Tooltip = 'Enable sequential mode' }
        @{ Name = '-Agents'; Tooltip = 'Comma-separated agent list' }
        @{ Name = '-MaxIterations'; Tooltip = 'Max iterations (default: 3)' }
        @{ Name = '-Model'; Tooltip = 'Claude model (opus, sonnet, haiku)' }
        @{ Name = '-Budget'; Tooltip = 'Budget limit in USD' }
        @{ Name = '-Memory'; Tooltip = 'Show shared memory' }
        @{ Name = '-Query'; Tooltip = 'Query knowledge graph' }
        @{ Name = '-RouteOnly'; Tooltip = 'Only show routing decision' }
        @{ Name = '-Quiet'; Tooltip = 'Reduce output verbosity' }
        @{ Name = '-Help'; Tooltip = 'Show help' }
    )

    # Get the current word being typed
    $commandElements = $commandAst.CommandElements
    $lastWord = if ($commandElements.Count -gt 1) {
        $commandElements[-1].Extent.Text
    } else { '' }

    # Check if completing a parameter value
    $previousWord = if ($commandElements.Count -gt 2) {
        $commandElements[-2].Extent.Text
    } else { '' }

    # Model completion
    if ($previousWord -eq '-Model') {
        $script:DevflowModels | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new(
                $_,
                $_,
                'ParameterValue',
                "Claude model: $_"
            )
        }
        return
    }

    # Agent completion
    if ($previousWord -eq '-Agents') {
        # Support comma-separated completion
        $existingAgents = if ($wordToComplete -match ',') {
            $wordToComplete -replace ',[^,]*$', ','
        } else { '' }

        $currentPart = if ($wordToComplete -match ',') {
            ($wordToComplete -split ',')[-1]
        } else { $wordToComplete }

        $script:DevflowAgents | Where-Object { $_.Name -like "$currentPart*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new(
                "$existingAgents$($_.Name)",
                $_.Name,
                'ParameterValue',
                $_.Description
            )
        }
        return
    }

    # Parameter completion
    $params | Where-Object { $_.Name -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new(
            $_.Name,
            $_.Name,
            'ParameterName',
            $_.Tooltip
        )
    }
}

# Argument completer for run-collab.ps1
Register-ArgumentCompleter -CommandName 'run-collab.ps1', 'run-collab' -Native -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $params = @(
        @{ Name = '-Swarm'; Tooltip = 'Enable swarm mode' }
        @{ Name = '-Pair'; Tooltip = 'Enable pair programming' }
        @{ Name = '-Auto'; Tooltip = 'Enable auto-routing' }
        @{ Name = '-Sequential'; Tooltip = 'Sequential pipeline' }
        @{ Name = '-Agents'; Tooltip = 'Comma-separated agents' }
        @{ Name = '-MaxIterations'; Tooltip = 'Max iterations' }
        @{ Name = '-Model'; Tooltip = 'Claude model' }
        @{ Name = '-Budget'; Tooltip = 'Budget limit USD' }
        @{ Name = '-Memory'; Tooltip = 'Show shared memory' }
        @{ Name = '-Query'; Tooltip = 'Query knowledge graph' }
        @{ Name = '-RouteOnly'; Tooltip = 'Routing only' }
        @{ Name = '-Quiet'; Tooltip = 'Quiet mode' }
        @{ Name = '-StoryKey'; Tooltip = 'Story key or description' }
    )

    $commandElements = $commandAst.CommandElements
    $previousWord = if ($commandElements.Count -gt 2) {
        $commandElements[-2].Extent.Text
    } else { '' }

    # Model completion
    if ($previousWord -eq '-Model') {
        $script:DevflowModels | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
        return
    }

    # Agent completion
    if ($previousWord -eq '-Agents') {
        $existingAgents = if ($wordToComplete -match ',') {
            $wordToComplete -replace ',[^,]*$', ','
        } else { '' }

        $currentPart = if ($wordToComplete -match ',') {
            ($wordToComplete -split ',')[-1]
        } else { $wordToComplete }

        $script:DevflowAgents | Where-Object { $_.Name -like "$currentPart*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new(
                "$existingAgents$($_.Name)",
                $_.Name,
                'ParameterValue',
                $_.Description
            )
        }
        return
    }

    # Parameter completion
    $params | Where-Object { $_.Name -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new(
            $_.Name,
            $_.Name,
            'ParameterName',
            $_.Tooltip
        )
    }
}

# Helper function to show available commands
function Get-DevflowCommands {
    @"

Devflow Collaboration Commands
==============================

run-story.ps1 / run-story.sh
  Main story runner with collaboration modes

  Modes:
    -Swarm        Multi-agent debate/consensus
    -Pair         DEV + REVIEWER pair programming
    -Auto         Intelligent auto-routing (default)
    -Sequential   Traditional sequential pipeline

run-collab.ps1 / run-collab.py
  Direct Python collaboration CLI

  Same modes as run-story with additional:
    -Memory       View shared memory
    -Query        Query knowledge graph
    -RouteOnly    Preview routing without execution

Available Agents:
  SM          Scrum Master
  DEV         Developer
  BA          Business Analyst
  ARCHITECT   Architect
  PM          Product Manager
  WRITER      Technical Writer
  MAINTAINER  Maintainer
  REVIEWER    Code Reviewer

Examples:
  run-story.ps1 -StoryKey "PROJ-123" -Swarm
  run-story.ps1 -StoryKey "PROJ-123" -Pair
  run-story.ps1 -StoryKey "PROJ-123" -Agents SM,DEV,ARCHITECT
  run-collab.ps1 -StoryKey "fix auth bug" -Auto -RouteOnly

"@
}

# Export alias
Set-Alias -Name devflow-help -Value Get-DevflowCommands

Write-Host "Devflow tab completion loaded. Use 'devflow-help' for command reference." -ForegroundColor Cyan

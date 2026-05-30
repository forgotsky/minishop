<#
.SYNOPSIS
    Collaborative Story Runner for Windows - Multi-Agent Collaboration CLI

.DESCRIPTION
    Integrates all collaboration features:
    - Agent routing (auto-select best agents)
    - Swarm mode (multi-agent debate)
    - Pair programming (DEV + REVIEWER interleaved)
    - Shared memory and knowledge graph

.PARAMETER StoryKey
    Story key or task description (required)

.PARAMETER Swarm
    Enable swarm mode (multi-agent debate/consensus)

.PARAMETER Pair
    Enable pair programming mode (DEV + REVIEWER interleaved)

.PARAMETER Auto
    Enable auto-route mode (intelligent agent selection)

.PARAMETER Sequential
    Enable sequential mode (traditional pipeline)

.PARAMETER Agents
    Comma-separated list of agents for swarm mode

.PARAMETER MaxIterations
    Maximum iterations for swarm/pair modes (default: 3)

.PARAMETER Model
    Claude model to use (opus, sonnet, haiku)

.PARAMETER Budget
    Budget limit in USD (default: 20.0)

.PARAMETER Memory
    Show shared memory and knowledge graph

.PARAMETER Query
    Query the knowledge graph

.PARAMETER RouteOnly
    Only show routing decision, don't execute

.PARAMETER Quiet
    Reduce output verbosity

.EXAMPLE
    .\run-collab.ps1 -StoryKey "3-5" -Swarm
    Run swarm mode with default agents

.EXAMPLE
    .\run-collab.ps1 -StoryKey "3-5" -Pair
    Run pair programming mode

.EXAMPLE
    .\run-collab.ps1 -StoryKey "fix auth bug" -Auto
    Auto-route to best agents

.EXAMPLE
    .\run-collab.ps1 -StoryKey "3-5" -Memory
    Show shared memory for story
#>

param(
    [Parameter(Position=0)]
    [string]$StoryKey,

    [switch]$Swarm,
    [switch]$Pair,
    [switch]$Auto,
    [switch]$Sequential,

    [string]$Agents,
    [int]$MaxIterations = 3,

    [ValidateSet("opus", "sonnet", "haiku")]
    [string]$Model = "opus",

    [double]$Budget = 20.0,

    [switch]$Memory,
    [string]$Query,
    [switch]$RouteOnly,
    [switch]$Quiet
)

# Script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Colors
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Banner {
    Write-ColorOutput @"

╔═══════════════════════════════════════════════════════════════╗
║        DEVFLOW COLLABORATIVE STORY RUNNER                     ║
╠═══════════════════════════════════════════════════════════════╣
║  Multi-agent collaboration with swarm, pair, and auto-routing ║
╚═══════════════════════════════════════════════════════════════╝

"@ -Color Cyan
}

function Show-Usage {
    Write-ColorOutput "Usage: .\run-collab.ps1 -StoryKey <key> [options]" -Color Yellow
    Write-Host ""
    Write-Host "Modes:"
    Write-Host "  -Auto          Auto-route to best agents (default)"
    Write-Host "  -Swarm         Multi-agent debate/consensus"
    Write-Host "  -Pair          DEV + REVIEWER pair programming"
    Write-Host "  -Sequential    Traditional sequential pipeline"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Agents <list>      Comma-separated agent list (for swarm)"
    Write-Host "  -MaxIterations <n>  Max iterations (default: 3)"
    Write-Host "  -Model <name>       Claude model (opus, sonnet, haiku)"
    Write-Host "  -Budget <amount>    Budget limit in USD (default: 20.0)"
    Write-Host "  -Memory             Show shared memory"
    Write-Host "  -Query <question>   Query knowledge graph"
    Write-Host "  -RouteOnly          Just show routing, don't execute"
    Write-Host "  -Quiet              Reduce verbosity"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run-collab.ps1 -StoryKey '3-5' -Swarm"
    Write-Host "  .\run-collab.ps1 -StoryKey '3-5' -Pair"
    Write-Host "  .\run-collab.ps1 -StoryKey 'fix auth bug' -Auto"
}

# Build Python command arguments
function Build-PythonArgs {
    $args = @()

    if ($StoryKey) {
        $args += $StoryKey
    }

    if ($Swarm) {
        $args += "--swarm"
    } elseif ($Pair) {
        $args += "--pair"
    } elseif ($Sequential) {
        $args += "--sequential"
    } else {
        $args += "--auto"
    }

    if ($Agents) {
        $args += "--agents"
        $args += $Agents
    }

    if ($MaxIterations -ne 3) {
        $args += "--max-iterations"
        $args += $MaxIterations.ToString()
    }

    if ($Model -ne "opus") {
        $args += "--model"
        $args += $Model
    }

    if ($Budget -ne 20.0) {
        $args += "--budget"
        $args += $Budget.ToString()
    }

    if ($Memory) {
        $args += "--memory"
    }

    if ($Query) {
        $args += "--query"
        $args += $Query
    }

    if ($RouteOnly) {
        $args += "--route-only"
    }

    if ($Quiet) {
        $args += "--quiet"
    }

    return $args
}

# Main execution
if (-not $StoryKey -and -not $Memory) {
    Show-Usage
    exit 1
}

Write-Banner

Write-ColorOutput "Story/Task: $StoryKey" -Color White
Write-Host ""

# Determine mode for display
$mode = "Auto-Route"
if ($Swarm) { $mode = "Swarm" }
elseif ($Pair) { $mode = "Pair Programming" }
elseif ($Sequential) { $mode = "Sequential" }

Write-ColorOutput "Mode: $mode" -Color Blue

# Build arguments and run Python script
$pythonArgs = Build-PythonArgs
$pythonScript = Join-Path $ScriptDir "run-collab.py"

# Check if Python is available
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} else {
    Write-ColorOutput "Error: Python not found. Please install Python 3.9+" -Color Red
    exit 1
}

Write-Host ""
Write-ColorOutput "Running: $pythonCmd $pythonScript $($pythonArgs -join ' ')" -Color Gray
Write-Host ""

# Execute
& $pythonCmd $pythonScript @pythonArgs
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-ColorOutput "════════════════════════════════════════════════════════════" -Color Green
    Write-ColorOutput " Collaboration complete!" -Color Green
} else {
    Write-Host ""
    Write-ColorOutput " Failed with exit code: $exitCode" -Color Red
}

exit $exitCode

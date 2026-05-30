<#
.SYNOPSIS
    Claude CLI Integration Library for Windows

.DESCRIPTION
    Wrapper functions for invoking Claude Code CLI to execute workflows.
    PowerShell equivalent of claude-cli.sh for Windows compatibility.

.NOTES
    Version: 1.0.0
    Requires: PowerShell 5.1+, Claude Code CLI
#>

#Requires -Version 5.1

# Script paths
$script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:ProjectRoot = (Get-Item "$script:ScriptDir\..\..\.." -ErrorAction SilentlyContinue).FullName
if (-not $script:ProjectRoot) {
    $script:ProjectRoot = (Get-Location).Path
}
$script:AutomationDir = Join-Path $script:ProjectRoot ".automation"
$script:AgentsDir = Join-Path $script:AutomationDir "agents"
$script:LogsDir = Join-Path $script:AutomationDir "logs"
$script:StoriesDir = Join-Path $script:ProjectRoot "docs"

# Source dependencies (silently continue if not found)
$checkpointIntegration = Join-Path $script:ScriptDir "checkpoint-integration.ps1"
if (Test-Path $checkpointIntegration) {
    . $checkpointIntegration
}

# Claude CLI configuration
$script:ClaudeCLI = if ($env:CLAUDE_CLI) { $env:CLAUDE_CLI } else { "claude" }
$script:ClaudeModel = if ($env:CLAUDE_MODEL) { $env:CLAUDE_MODEL } else { "sonnet" }
$script:PermissionMode = if ($env:PERMISSION_MODE) { $env:PERMISSION_MODE } else { "dangerouslySkipPermissions" }

#region Helper Functions

function Get-PermissionFlags {
    <#
    .SYNOPSIS
        Build permission flags based on mode
    #>
    switch ($script:PermissionMode) {
        { $_ -in "dangerouslySkipPermissions", "skip" } {
            return "--dangerously-skip-permissions"
        }
        default {
            return "--permission-mode $script:PermissionMode"
        }
    }
}

function Read-FileContent {
    <#
    .SYNOPSIS
        Read file content for prompt
    #>
    param([string]$FilePath)

    if (Test-Path $FilePath) {
        return Get-Content $FilePath -Raw
    }
    return "[File not found: $FilePath]"
}

function Build-Prompt {
    <#
    .SYNOPSIS
        Create a combined prompt from agent and workflow
    #>
    param(
        [string]$AgentFile,
        [string]$TaskDescription
    )

    $agentPrompt = ""
    if (Test-Path $AgentFile) {
        $agentPrompt = Get-Content $AgentFile -Raw
    }

    return @"
$agentPrompt

---

## Current Task

$TaskDescription
"@
}

#endregion

#region Persona Banner Functions

function Write-PersonaBanner {
    <#
    .SYNOPSIS
        Print a colored persona banner for agent switches
    #>
    param(
        [string]$Persona,
        [string]$Role,
        [string]$Color = "Cyan",
        [string]$Model = ""
    )

    Write-Host ""
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor $Color
    Write-Host "                    PERSONA SWITCH" -ForegroundColor $Color
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor $Color
    Write-Host "  Agent: " -NoNewline -ForegroundColor $Color
    Write-Host $Persona
    Write-Host "  Role:  " -NoNewline -ForegroundColor $Color
    Write-Host $Role
    if ($Model) {
        Write-Host "  Model: " -NoNewline -ForegroundColor $Color
        Write-Host $Model
    }
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor $Color
    Write-Host ""
}

#endregion

#region Workflow Invocation Functions

function Invoke-SMStoryContext {
    <#
    .SYNOPSIS
        SM agent for story context creation
    #>
    param([string]$StoryKey)

    $storyFile = Join-Path $script:StoriesDir "$StoryKey.md"
    $contextFile = Join-Path $script:StoriesDir "$StoryKey.context.xml"
    $logFile = Join-Path $script:LogsDir "$StoryKey-context.log"
    $model = "sonnet"

    Write-PersonaBanner -Persona "SM (Scrum Master)" -Role "Story Context Creation & Planning" -Color "Yellow" -Model $model

    Write-Host ">> Creating story context for: $StoryKey" -ForegroundColor Cyan

    if (-not (Test-Path $storyFile)) {
        Write-Host "X Story file not found: $storyFile" -ForegroundColor Red
        return 1
    }

    $storyContent = Get-Content $storyFile -Raw

    $prompt = @"
Create a technical context file for implementing this story.

## Story Specification
$storyContent

## Instructions
1. Read the story requirements carefully
2. Explore the codebase to find relevant patterns and existing code
3. Identify files that need to be created or modified
4. Create the context file at: $contextFile

The context.xml should include:
- story-key, title, status
- files-to-create list
- files-to-modify list
- dependencies
- testing-requirements
- project-paths (app-root: app, lib-path: app/lib, test-path: app/test)

After creating the context file, update sprint-status.yaml to set this story to 'ready-for-dev'.
"@

    $agentFile = Join-Path $script:AgentsDir "sm.md"
    $agentPrompt = ""
    if (Test-Path $agentFile) {
        $agentPrompt = Get-Content $agentFile -Raw
    }

    $permFlags = Get-PermissionFlags

    Push-Location $script:ProjectRoot
    try {
        $prompt | & $script:ClaudeCLI -p `
            --model $model `
            $permFlags `
            --append-system-prompt $agentPrompt `
            --tools "Read,Write,Edit,Grep,Glob,Bash" `
            --max-budget-usd 3.00 2>&1 | Tee-Object -FilePath $logFile

        return $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}

function Invoke-DevStory {
    <#
    .SYNOPSIS
        DEV agent for story implementation
    #>
    param([string]$StoryKey)

    $storyFile = Join-Path $script:StoriesDir "$StoryKey.md"
    $contextFile = Join-Path $script:StoriesDir "$StoryKey.context.xml"
    $logFile = Join-Path $script:LogsDir "$StoryKey-develop.log"
    $model = "opus"

    Write-PersonaBanner -Persona "DEV (Developer)" -Role "Story Implementation & Coding" -Color "Green" -Model $model

    Write-Host ">> Implementing story: $StoryKey" -ForegroundColor Cyan

    if (-not (Test-Path $storyFile)) {
        Write-Host "X Story file not found: $storyFile" -ForegroundColor Red
        return 1
    }

    if (-not (Test-Path $contextFile)) {
        Write-Host "X Context file not found: $contextFile" -ForegroundColor Red
        return 1
    }

    Write-Host ">> Checking context feasibility..." -ForegroundColor Blue

    $storyContent = Get-Content $storyFile -Raw
    $contextContent = Get-Content $contextFile -Raw

    $prompt = @"
IMPLEMENT THIS STORY NOW. Create all required files and code.

$storyContent

---

CONTEXT (files to create/modify):
$contextContent

---

START IMMEDIATELY:
1. Read existing code in app/lib/features/ to understand patterns
2. Create ALL files listed in files-to-create using the Write tool
3. Modify files listed in files-to-modify using the Edit tool
4. Write tests in app/test/
5. Run: cd app && flutter test

DO NOT explain or ask questions. Just implement the code.
"@

    # Start checkpoint monitor if available
    if (Get-Command Start-CheckpointMonitor -ErrorAction SilentlyContinue) {
        Start-CheckpointMonitor -LogFile $logFile -SessionId $StoryKey
        Write-CheckpointInfo -LogFile $logFile
    }

    # Create symlink to current.log
    $currentLog = Join-Path $script:LogsDir "current.log"
    if (Test-Path $currentLog) { Remove-Item $currentLog -Force }
    try {
        New-Item -ItemType SymbolicLink -Path $currentLog -Target $logFile -Force -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Symlinks may require admin on Windows, fallback to copy later
    }

    $agentFile = Join-Path $script:AgentsDir "dev.md"
    $agentPrompt = ""
    if (Test-Path $agentFile) {
        $agentPrompt = Get-Content $agentFile -Raw
    }

    $permFlags = Get-PermissionFlags

    Push-Location $script:ProjectRoot
    try {
        $prompt | & $script:ClaudeCLI -p `
            --model $model `
            $permFlags `
            --append-system-prompt $agentPrompt `
            --tools "Read,Write,Edit,Grep,Glob,Bash" `
            --max-budget-usd 15.00 2>&1 | Tee-Object -FilePath $logFile

        $exitCode = $LASTEXITCODE

        # Stop checkpoint monitor if available
        if (Get-Command Stop-CheckpointMonitor -ErrorAction SilentlyContinue) {
            Stop-CheckpointMonitor -LogFile $logFile
        }

        return $exitCode
    }
    finally {
        Pop-Location
    }
}

function Invoke-SMCodeReview {
    <#
    .SYNOPSIS
        SM agent for code review
    #>
    param([string]$StoryKey)

    $storyFile = Join-Path $script:StoriesDir "$StoryKey.md"
    $reviewFile = Join-Path $script:StoriesDir "$StoryKey.code-review.md"
    $logFile = Join-Path $script:LogsDir "$StoryKey-review.log"
    $model = "opus"

    Write-PersonaBanner -Persona "SM (Scrum Master)" -Role "Code Review & Quality Assurance" -Color "Magenta" -Model $model

    Write-Host ">> Reviewing implementation: $StoryKey" -ForegroundColor Cyan

    if (-not (Test-Path $storyFile)) {
        Write-Host "X Story file not found: $storyFile" -ForegroundColor Red
        return 1
    }

    $storyContent = Get-Content $storyFile -Raw

    $prompt = @"
Perform a code review for this implemented story.

## Story Specification
$storyContent

## Instructions
1. Read all acceptance criteria in the story
2. For each AC, verify it has been implemented correctly
3. Check code quality and patterns
4. Run 'cd app && flutter test' to verify tests pass
5. Create a review report at: $reviewFile

The review file should include:
- Overall verdict: APPROVED or CHANGES REQUESTED
- Score out of 100
- AC verification checklist (each AC marked as met/not met)
- Code quality notes
- Any issues found

If APPROVED, update sprint-status.yaml to 'done'.
If CHANGES REQUESTED, update sprint-status.yaml to 'in-progress' and list required changes.
"@

    # Start checkpoint monitor if available
    if (Get-Command Start-CheckpointMonitor -ErrorAction SilentlyContinue) {
        Start-CheckpointMonitor -LogFile $logFile -SessionId $StoryKey
        Write-CheckpointInfo -LogFile $logFile
    }

    # Create symlink to current.log
    $currentLog = Join-Path $script:LogsDir "current.log"
    if (Test-Path $currentLog) { Remove-Item $currentLog -Force }
    try {
        New-Item -ItemType SymbolicLink -Path $currentLog -Target $logFile -Force -ErrorAction SilentlyContinue | Out-Null
    } catch {}

    $agentFile = Join-Path $script:AgentsDir "sm.md"
    $agentPrompt = ""
    if (Test-Path $agentFile) {
        $agentPrompt = Get-Content $agentFile -Raw
    }

    $permFlags = Get-PermissionFlags

    Push-Location $script:ProjectRoot
    try {
        $prompt | & $script:ClaudeCLI -p `
            --model $model `
            $permFlags `
            --append-system-prompt $agentPrompt `
            --tools "Read,Write,Edit,Grep,Glob,Bash" `
            --max-budget-usd 5.00 2>&1 | Tee-Object -FilePath $logFile

        $exitCode = $LASTEXITCODE

        if (Get-Command Stop-CheckpointMonitor -ErrorAction SilentlyContinue) {
            Stop-CheckpointMonitor -LogFile $logFile
        }

        return $exitCode
    }
    finally {
        Pop-Location
    }
}

function Invoke-SMDraftStory {
    <#
    .SYNOPSIS
        SM agent for story drafting
    #>
    param([string]$StoryKey)

    $storyFile = Join-Path $script:StoriesDir "$StoryKey.md"
    $epicsFile = Join-Path $script:ProjectRoot "docs\epics.md"
    $logFile = Join-Path $script:LogsDir "$StoryKey-draft.log"
    $model = "sonnet"

    Write-PersonaBanner -Persona "SM (Scrum Master)" -Role "Story Drafting & Specification" -Color "Yellow" -Model $model

    Write-Host ">> Drafting story: $StoryKey" -ForegroundColor Cyan

    # Extract epic number from story key
    $epicNum = ($StoryKey -split '-')[0]

    $prompt = @"
Draft a detailed story specification.

Story Key: $StoryKey
Epic: $epicNum

## Instructions
1. Read the epics file at $epicsFile to understand the epic context
2. Find the story entry for $StoryKey in the epic
3. Create a detailed story specification at: $storyFile

The story file should include:
- # Title
- ## Summary
- ## Acceptance Criteria (numbered as AC X.Y.Z)
- ## Technical Notes
- ## Dependencies (if any)
- ## Testing Requirements

After creating the story, update sprint-status.yaml to set this story to 'drafted'.
"@

    $agentFile = Join-Path $script:AgentsDir "sm.md"
    $agentPrompt = ""
    if (Test-Path $agentFile) {
        $agentPrompt = Get-Content $agentFile -Raw
    }

    $permFlags = Get-PermissionFlags

    Push-Location $script:ProjectRoot
    try {
        $prompt | & $script:ClaudeCLI -p `
            --model $model `
            $permFlags `
            --append-system-prompt $agentPrompt `
            --tools "Read,Write,Edit,Grep,Glob" `
            --max-budget-usd 2.00 2>&1 | Tee-Object -FilePath $logFile

        return $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}

function Invoke-BARequirements {
    <#
    .SYNOPSIS
        BA agent for requirements analysis
    #>
    param([string]$FeatureName)

    $outputFile = Join-Path $script:ProjectRoot "docs\requirements\$FeatureName.md"
    $logFile = Join-Path $script:LogsDir "$FeatureName-requirements.log"
    $model = "sonnet"

    Write-PersonaBanner -Persona "BA (Business Analyst)" -Role "Requirements Analysis & User Stories" -Color "Blue" -Model $model

    Write-Host ">> Analyzing requirements for: $FeatureName" -ForegroundColor Cyan

    # Ensure directory exists
    $reqDir = Join-Path $script:ProjectRoot "docs\requirements"
    if (-not (Test-Path $reqDir)) {
        New-Item -ItemType Directory -Path $reqDir -Force | Out-Null
    }

    $prompt = @"
Analyze and document requirements for the feature: $FeatureName

## Instructions
1. Read the PRD at tooling/docs/prd.md for product context
2. Read the epics at tooling/docs/epics.md for feature context
3. Create a detailed requirements document at: $outputFile

The requirements document should include:
- User stories with acceptance criteria
- Business rules
- Data requirements
- Edge cases and error scenarios
- Dependencies

Use the INVEST criteria for user stories.
"@

    $agentFile = Join-Path $script:AgentsDir "ba.md"
    $agentPrompt = ""
    if (Test-Path $agentFile) {
        $agentPrompt = Get-Content $agentFile -Raw
    }

    $permFlags = Get-PermissionFlags

    Push-Location $script:ProjectRoot
    try {
        $prompt | & $script:ClaudeCLI -p `
            --model $model `
            $permFlags `
            --append-system-prompt $agentPrompt `
            --tools "Read,Write,Edit,Grep,Glob" `
            --max-budget-usd 3.00 2>&1 | Tee-Object -FilePath $logFile

        return $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}

function Invoke-ArchitectDesign {
    <#
    .SYNOPSIS
        Architect agent for technical design
    #>
    param([string]$FeatureName)

    $outputFile = Join-Path $script:StoriesDir "tech-spec-$FeatureName.md"
    $logFile = Join-Path $script:LogsDir "$FeatureName-architecture.log"
    $model = "sonnet"

    Write-PersonaBanner -Persona "ARCHITECT" -Role "Technical Design & Architecture" -Color "Cyan" -Model $model

    Write-Host ">> Creating technical specification for: $FeatureName" -ForegroundColor Cyan

    $prompt = @"
Create a technical specification for: $FeatureName

## Instructions
1. Read the architecture documentation at tooling/docs/architecture.md
2. Explore the existing codebase to understand current patterns
3. Read any related story or epic files
4. Create a technical specification at: $outputFile

The tech spec should include:
- Component architecture
- Data model and database schema
- API design (if applicable)
- Non-functional requirements
- Implementation notes
- Risks and mitigations

Follow the existing project structure and patterns.
"@

    $agentFile = Join-Path $script:AgentsDir "architect.md"
    $agentPrompt = ""
    if (Test-Path $agentFile) {
        $agentPrompt = Get-Content $agentFile -Raw
    }

    $permFlags = Get-PermissionFlags

    Push-Location $script:ProjectRoot
    try {
        $prompt | & $script:ClaudeCLI -p `
            --model $model `
            $permFlags `
            --append-system-prompt $agentPrompt `
            --tools "Read,Write,Edit,Grep,Glob" `
            --max-budget-usd 5.00 2>&1 | Tee-Object -FilePath $logFile

        return $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}

function Invoke-PMEpic {
    <#
    .SYNOPSIS
        PM agent for epic planning
    #>
    param([string]$EpicNum)

    $epicsFile = Join-Path $script:ProjectRoot "docs\epics.md"
    $logFile = Join-Path $script:LogsDir "epic-$EpicNum-planning.log"
    $model = "sonnet"

    Write-PersonaBanner -Persona "PM (Product Manager)" -Role "Epic Planning & Prioritization" -Color "Red" -Model $model

    Write-Host ">> Planning epic: $EpicNum" -ForegroundColor Cyan

    $prompt = @"
Plan and refine Epic $EpicNum

## Instructions
1. Read the PRD at tooling/docs/prd.md for product context
2. Read the current epics file at $epicsFile
3. Analyze Epic $EpicNum and refine its definition
4. Break down into well-defined stories
5. Update the epics file with refined content

Ensure each story is:
- Clearly defined with user value
- Appropriately sized (1-3 days of work)
- Properly sequenced with dependencies

Use RICE scoring to prioritize stories within the epic.
"@

    $agentFile = Join-Path $script:AgentsDir "pm.md"
    $agentPrompt = ""
    if (Test-Path $agentFile) {
        $agentPrompt = Get-Content $agentFile -Raw
    }

    $permFlags = Get-PermissionFlags

    Push-Location $script:ProjectRoot
    try {
        $prompt | & $script:ClaudeCLI -p `
            --model $model `
            $permFlags `
            --append-system-prompt $agentPrompt `
            --tools "Read,Write,Edit,Grep,Glob" `
            --max-budget-usd 3.00 2>&1 | Tee-Object -FilePath $logFile

        return $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}

function Invoke-WriterDocs {
    <#
    .SYNOPSIS
        Writer agent for documentation
    #>
    param(
        [string]$DocType,
        [string]$Subject
    )

    $outputDir = Join-Path $script:ProjectRoot "docs"
    $logFile = Join-Path $script:LogsDir "$Subject-docs.log"
    $model = "sonnet"

    Write-PersonaBanner -Persona "WRITER (Technical Writer)" -Role "Documentation & Content Creation" -Color "White" -Model $model

    Write-Host ">> Creating documentation: $DocType for $Subject" -ForegroundColor Cyan

    $prompt = @"
Create $DocType documentation for: $Subject

## Instructions
1. Explore the codebase to understand the implementation
2. Read any existing documentation for context
3. Create appropriate documentation

Documentation type: $DocType

For user guides: Write step-by-step instructions with examples
For API docs: Document endpoints, parameters, and responses
For release notes: Summarize changes in user-friendly language
For README: Create a comprehensive project overview

Save the documentation to an appropriate location in $outputDir/
"@

    $agentFile = Join-Path $script:AgentsDir "writer.md"
    $agentPrompt = ""
    if (Test-Path $agentFile) {
        $agentPrompt = Get-Content $agentFile -Raw
    }

    $permFlags = Get-PermissionFlags

    Push-Location $script:ProjectRoot
    try {
        $prompt | & $script:ClaudeCLI -p `
            --model $model `
            $permFlags `
            --append-system-prompt $agentPrompt `
            --tools "Read,Write,Edit,Grep,Glob" `
            --max-budget-usd 3.00 2>&1 | Tee-Object -FilePath $logFile

        return $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}

#endregion

#region Sprint Status Management

function Update-StoryStatus {
    <#
    .SYNOPSIS
        Update story status in sprint-status.yaml
    #>
    param(
        [string]$StoryKey,
        [string]$NewStatus
    )

    $sprintStatusFile = Join-Path $script:ProjectRoot "docs\sprint-status.yaml"

    Write-Host ">> Updating sprint status: $StoryKey -> $NewStatus" -ForegroundColor Cyan

    if (-not (Test-Path $sprintStatusFile)) {
        Write-Host "!! Sprint status file not found: $sprintStatusFile" -ForegroundColor Yellow
        return 1
    }

    $content = Get-Content $sprintStatusFile -Raw

    # Check if story exists
    if ($content -notmatch "^\s+${StoryKey}:") {
        Write-Host "!! Story $StoryKey not found in sprint-status.yaml" -ForegroundColor Yellow
        return 1
    }

    # Update status
    $pattern = "(?m)^(\s+${StoryKey}:)\s*.*$"
    $replacement = "`$1 $NewStatus"
    $newContent = $content -replace $pattern, $replacement

    # Update timestamp
    $today = (Get-Date).ToString("yyyy-MM-dd")
    $newContent = $newContent -replace "(?m)^#?\s*updated:.*$", "updated: $today"

    Set-Content -Path $sprintStatusFile -Value $newContent -NoNewline

    Write-Host "[OK] Status updated: $StoryKey -> $NewStatus" -ForegroundColor Green
    return 0
}

#endregion

#region Auto-Commit and PR Functions

function Invoke-AutoCommit {
    <#
    .SYNOPSIS
        Auto-commit changes after development
    #>
    param([string]$StoryKey)

    $storyFile = Join-Path $script:StoriesDir "$StoryKey.md"

    Write-Host ">> Auto-committing changes..." -ForegroundColor Cyan

    Push-Location $script:ProjectRoot
    try {
        # Check for changes
        $status = git status --porcelain
        if (-not $status) {
            Write-Host "[i] No changes to commit" -ForegroundColor Blue
            return 0
        }

        Write-Host "[i] Detected changes to commit" -ForegroundColor Blue

        # Extract story title
        $storyTitle = $StoryKey
        if (Test-Path $storyFile) {
            $firstLine = (Get-Content $storyFile -First 1) -replace '^#\s*', ''
            if ($firstLine) { $storyTitle = $firstLine }
        }

        # Stage all changes
        git add -A

        # Create commit message
        $commitMsg = @"
feat: $storyTitle

Automated implementation via Claude Code CLI

Story: $StoryKey

Generated with Claude Code (https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
"@

        git commit -m $commitMsg

        if ($LASTEXITCODE -eq 0) {
            $shortHash = git rev-parse --short HEAD
            Write-Host "[OK] Changes committed successfully" -ForegroundColor Green
            Write-Host "[i] Commit: $shortHash" -ForegroundColor Blue
            return 0
        }
        else {
            Write-Host "!! Commit failed or no changes to commit" -ForegroundColor Yellow
            return 1
        }
    }
    finally {
        Pop-Location
    }
}

function New-AutoPR {
    <#
    .SYNOPSIS
        Create pull request after commit
    #>
    param([string]$StoryKey)

    $storyFile = Join-Path $script:StoriesDir "$StoryKey.md"

    Write-Host ">> Creating pull request..." -ForegroundColor Cyan

    # Check if gh CLI is available
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Host "!! GitHub CLI (gh) not found. Skipping PR creation." -ForegroundColor Yellow
        Write-Host "   Install with: winget install GitHub.cli" -ForegroundColor Blue
        return 1
    }

    Push-Location $script:ProjectRoot
    try {
        $currentBranch = git rev-parse --abbrev-ref HEAD

        # Extract title and body
        $prTitle = $StoryKey
        $prBody = "Story: $StoryKey`n`nGenerated via Claude Code CLI automation"

        if (Test-Path $storyFile) {
            $content = Get-Content $storyFile -Raw
            $firstLine = (Get-Content $storyFile -First 1) -replace '^#\s*', ''
            if ($firstLine) { $prTitle = $firstLine }

            $prBody = @"
## Story: $StoryKey

$content

---

Auto-generated via Claude Code CLI automation
"@
        }

        gh pr create --title $prTitle --body $prBody --base main --head $currentBranch

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Pull request created" -ForegroundColor Green
            return 0
        }
        else {
            Write-Host "!! PR creation failed. Create manually with:" -ForegroundColor Yellow
            Write-Host "   gh pr create --title `"$prTitle`" --base main" -ForegroundColor Blue
            return 1
        }
    }
    finally {
        Pop-Location
    }
}

#endregion

#region Full Pipeline

function Start-FullPipeline {
    <#
    .SYNOPSIS
        Run complete story pipeline
    #>
    param([string]$StoryKey)

    $autoCommit = if ($env:AUTO_COMMIT) { $env:AUTO_COMMIT -eq "true" } else { $true }
    $autoPR = if ($env:AUTO_PR) { $env:AUTO_PR -eq "true" } else { $false }

    Write-Host ""
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor Cyan
    Write-Host "  AUTOMATED STORY PIPELINE: $StoryKey" -ForegroundColor Cyan
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor Cyan
    Write-Host ""

    # Phase 1: Create context if needed
    $contextFile = Join-Path $script:StoriesDir "$StoryKey.context.xml"
    if (-not (Test-Path $contextFile)) {
        Write-Host ">> Phase 1: Creating story context..." -ForegroundColor Yellow
        $result = Invoke-SMStoryContext -StoryKey $StoryKey
        if ($result -ne 0) {
            Write-Host "X Context creation failed" -ForegroundColor Red
            return 1
        }
        Write-Host "[OK] Context created" -ForegroundColor Green
        Write-Host ""
    }
    else {
        Write-Host "[OK] Context already exists, skipping..." -ForegroundColor Green
        Write-Host ""
    }

    # Phase 2: Development
    Write-Host ">> Phase 2: Implementing story..." -ForegroundColor Yellow
    $result = Invoke-DevStory -StoryKey $StoryKey
    if ($result -ne 0) {
        Write-Host "X Development failed" -ForegroundColor Red
        return 1
    }
    Write-Host "[OK] Development complete" -ForegroundColor Green
    Write-Host ""

    # Phase 2.5: Update status to 'review'
    Update-StoryStatus -StoryKey $StoryKey -NewStatus "review"
    Write-Host ""

    # Phase 2.6: Auto-commit
    if ($autoCommit) {
        Invoke-AutoCommit -StoryKey $StoryKey
        Write-Host ""
    }

    # Phase 2.7: Auto-PR
    if ($autoPR) {
        New-AutoPR -StoryKey $StoryKey
        Write-Host ""
    }

    # Phase 3: Code review
    Write-Host ">> Phase 3: Code review..." -ForegroundColor Yellow
    $result = Invoke-SMCodeReview -StoryKey $StoryKey
    if ($result -ne 0) {
        Write-Host "X Code review failed" -ForegroundColor Red
        return 1
    }
    Write-Host "[OK] Code review complete" -ForegroundColor Green
    Write-Host ""

    # Phase 4: Update status to 'done'
    Update-StoryStatus -StoryKey $StoryKey -NewStatus "done"
    Write-Host ""

    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor Cyan
    Write-Host "  PIPELINE COMPLETE" -ForegroundColor Cyan
    Write-Host ("{0}" -f ("=" * 65)) -ForegroundColor Cyan

    return 0
}

#endregion

# Export functions for use when dot-sourcing
Export-ModuleMember -Function * -ErrorAction SilentlyContinue

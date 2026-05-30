<#
.SYNOPSIS
    NEW-DOC - Documentation Template Generator for Windows

.DESCRIPTION
    Creates new documentation files following the documentation standard.

.PARAMETER Type
    Document type: guide, spec, status, reference, example

.PARAMETER Name
    Document name (kebab-case)

.PARAMETER Author
    Author name (default: current user)

.EXAMPLE
    .\new-doc.ps1 -Type guide -Name "checkpoint-setup"
    .\new-doc.ps1 -Type spec -Name "epic-4" -Author "SM Agent"

.NOTES
    Version: 1.0.0
#>

#Requires -Version 5.1

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("guide", "spec", "status", "reference", "example")]
    [string]$Type,

    [Parameter(Mandatory=$true)]
    [string]$Name,

    [string]$Author = $env:USERNAME
)

$script:ScriptDir = $PSScriptRoot
$script:ProjectRoot = (Get-Item "$script:ScriptDir\.." -ErrorAction SilentlyContinue).FullName
$script:DocsDir = Join-Path $script:ProjectRoot "tooling\docs"

function Get-GuideTemplate {
    param([string]$Name, [string]$Author, [string]$Date)

    return @"
# [Document Title]

**Type**: Guide
**Version**: 1.0
**Last Updated**: $Date
**Author**: $Author
**Status**: Draft

---

## Purpose

[1-2 sentence description of what this guide helps users accomplish]

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Step-by-Step Instructions](#step-by-step-instructions)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Prerequisites

Before starting, ensure you have:

- [ ] Prerequisite 1
- [ ] Prerequisite 2
- [ ] Prerequisite 3

---

## Quick Start

For experienced users:

``````powershell
# Quick command to get started
``````

---

## Step-by-Step Instructions

### Step 1: [First Step]

Description of what to do.

``````powershell
# Command to run
``````

**Expected output**:
``````
Output here
``````

### Step 2: [Second Step]

Description of what to do.

---

## Examples

### Example 1: [Common Use Case]

**Problem**: [What problem this solves]

**Solution**:
``````powershell
# Commands
``````

**Result**: [What happens]

---

## Troubleshooting

### Issue: [Common Problem]

**Symptoms**: [What you see]

**Cause**: [Why it happens]

**Solution**:
``````powershell
# Fix commands
``````

---

## Next Steps

After completing this guide:

1. [Next logical step]
2. [Another option]
3. [Advanced topics]

---

## Changelog

### 1.0 ($Date)
- Initial version

---

**Document Control**
- **Created**: $Date
- **Owner**: $Author
"@
}

function Get-SpecTemplate {
    param([string]$Name, [string]$Author, [string]$Date)

    return @"
# [Technical Specification Title]

**Type**: Spec
**Version**: 1.0
**Last Updated**: $Date
**Author**: $Author
**Status**: Draft

---

## Overview

[High-level description of what is being specified]

## Table of Contents

- [Objectives and Scope](#objectives-and-scope)
- [Architecture](#architecture)
- [Implementation Details](#implementation-details)
- [Dependencies](#dependencies)
- [Testing Requirements](#testing-requirements)
- [Acceptance Criteria](#acceptance-criteria)

---

## Objectives and Scope

### In Scope
- Feature 1
- Feature 2
- Feature 3

### Out of Scope
- Feature A
- Feature B

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

---

## Architecture

### System Components

``````
[ASCII diagram or description]
``````

### Data Flow

``````
[Flow description]
``````

---

## Implementation Details

### Component 1: [Name]

**Purpose**: [What it does]

**Files to Create**:
- ``path/to/file1``
- ``path/to/file2``

**Files to Modify**:
- ``path/to/existing``

---

## Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| package_name | ^1.0.0 | Description |

---

## Testing Requirements

### Unit Tests
- [ ] Test scenario 1
- [ ] Test scenario 2

### Integration Tests
- [ ] Test scenario 1
- [ ] Test scenario 2

### Test Coverage Target
- Minimum: 80%
- Target: 90%

---

## Acceptance Criteria

- [ ] AC 1: [Specific, measurable criterion]
- [ ] AC 2: [Specific, measurable criterion]
- [ ] AC 3: [Specific, measurable criterion]

---

## Changelog

### 1.0 ($Date)
- Initial specification

---

**Document Control**
- **Created**: $Date
- **Owner**: $Author
"@
}

function Get-StatusTemplate {
    param([string]$Name, [string]$Author, [string]$Date)

    return @"
# [Status Report Title]

**Type**: Status
**Version**: 1.0
**Last Updated**: $Date
**Author**: $Author
**Status**: Active

---

## Current Status

**Overall**: [Green/Yellow/Red]

**Summary**: [1-sentence current state]

---

## Integration Points

| Component | Status | Notes |
|-----------|--------|-------|
| Component 1 | Complete | Working as expected |
| Component 2 | In Progress | 75% complete |
| Component 3 | Not Started | Planned for next week |

---

## What's Working

- Feature 1 - Fully operational
- Feature 2 - Deployed and tested
- Feature 3 - In production

---

## What's Not Working

- Issue 1 - Description
- Issue 2 - Description

---

## Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Coverage | 85% | 80% | OK |
| Performance | 200ms | <300ms | OK |
| Bugs | 3 | <5 | OK |

---

## Next Steps

### Immediate (This Week)
1. [ ] Task 1
2. [ ] Task 2

### Short Term (Next Week)
1. [ ] Task 3
2. [ ] Task 4

---

## Changelog

### 1.0 ($Date)
- Initial status report

---

**Document Control**
- **Created**: $Date
- **Owner**: $Author
"@
}

# Main execution
$date = (Get-Date).ToString("yyyy-MM-dd")
$filename = "$($Type.ToUpper())-$Name.md"
$outputFile = Join-Path $script:DocsDir $filename

# Check if file exists
if (Test-Path $outputFile) {
    Write-Host "File already exists: $outputFile" -ForegroundColor Yellow
    $overwrite = Read-Host "Overwrite? (y/n)"
    if ($overwrite -notmatch '^[Yy]') {
        Write-Host "Aborted." -ForegroundColor Blue
        exit 0
    }
}

Write-Host "Creating $Type document: $filename" -ForegroundColor Blue

# Generate template
$template = switch ($Type) {
    "guide" { Get-GuideTemplate -Name $Name -Author $Author -Date $date }
    "spec" { Get-SpecTemplate -Name $Name -Author $Author -Date $date }
    "status" { Get-StatusTemplate -Name $Name -Author $Author -Date $date }
    "reference" { Get-GuideTemplate -Name $Name -Author $Author -Date $date }
    "example" { Get-GuideTemplate -Name $Name -Author $Author -Date $date }
}

# Write file
Set-Content -Path $outputFile -Value $template

Write-Host "[OK] Created: $outputFile" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Blue
Write-Host "  1. Edit the document: $outputFile"
Write-Host "  2. Fill in the template placeholders"
Write-Host "  3. Review against: tooling\docs\DOC-STANDARD.md"
Write-Host ""

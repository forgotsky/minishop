#!/usr/bin/env bash
################################################################################
# NEW-DOC - Documentation Template Generator
#
# Creates new documentation files following the Stronger documentation standard
#
# Usage:
#   ./new-doc.sh --type guide --name "checkpoint-setup"
#   ./new-doc.sh --type spec --name "epic-4"
#   ./new-doc.sh --type status --name "integration-report"
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCS_DIR="$PROJECT_ROOT/tooling/docs"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_usage() {
    cat << EOF
Usage: ./new-doc.sh --type <type> --name <name> [options]

Options:
  --type <type>        Document type (guide|spec|status|reference|example)
  --name <name>        Document name (kebab-case)
  --author <name>      Author name (default: current user)
  --help               Show this help message

Examples:
  ./new-doc.sh --type guide --name "checkpoint-setup"
  ./new-doc.sh --type spec --name "epic-4" --author "SM Agent"
  ./new-doc.sh --type status --name "sprint-report"

Document types:
  guide      - User-facing guides and tutorials
  spec       - Technical specifications
  status     - Status reports and tracking
  reference  - Quick reference sheets
  example    - Code examples and patterns

EOF
}

create_guide_template() {
    local name="$1"
    local author="$2"
    local date=$(date +%Y-%m-%d)

    cat << 'EOF'
# [Document Title]

**Type**: Guide
**Version**: 1.0
**Last Updated**: ${date}
**Author**: ${author}
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
- [Related Documents](#related-documents)

---

## Prerequisites

Before starting, ensure you have:

- [ ] Prerequisite 1
- [ ] Prerequisite 2
- [ ] Prerequisite 3

---

## Quick Start

For experienced users:

```bash
# Quick command to get started
```

---

## Step-by-Step Instructions

### Step 1: [First Step]

Description of what to do.

```bash
# Command to run
```

**Expected output**:
```
Output here
```

### Step 2: [Second Step]

Description of what to do.

```bash
# Command to run
```

---

## Examples

### Example 1: [Common Use Case]

**Problem**: [What problem this solves]

**Solution**:
```bash
# Commands
```

**Result**: [What happens]

---

## Troubleshooting

### Issue: [Common Problem]

**Symptoms**: [What you see]

**Cause**: [Why it happens]

**Solution**:
```bash
# Fix commands
```

---

## Next Steps

After completing this guide:

1. [Next logical step]
2. [Another option]
3. [Advanced topics]

---

## Related Documents

- [Link](path) - Description
- [Link](path) - Description

---

## Changelog

### 1.0 (${date})
- Initial version

---

**Document Control**
- **Created**: ${date}
- **Last Reviewed**: ${date}
- **Next Review**: [Date +1 month]
- **Owner**: ${author}
EOF
}

create_spec_template() {
    local name="$1"
    local author="$2"
    local date=$(date +%Y-%m-%d)

    cat << 'EOF'
# [Technical Specification Title]

**Type**: Spec
**Version**: 1.0
**Last Updated**: ${date}
**Author**: ${author}
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
- Feature C

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

---

## Architecture

### System Components

```
[ASCII diagram or description]
```

### Data Flow

```
[Flow description]
```

---

## Implementation Details

### Component 1: [Name]

**Purpose**: [What it does]

**Files to Create**:
- `path/to/file1.dart`
- `path/to/file2.dart`

**Files to Modify**:
- `path/to/existing.dart`

**Implementation**:
```dart
// Code example
```

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

## Related Documents

- [Link](path) - Description

---

## Changelog

### 1.0 (${date})
- Initial specification

---

**Document Control**
- **Created**: ${date}
- **Last Reviewed**: ${date}
- **Next Review**: [Date +1 month]
- **Owner**: ${author}
EOF
}

create_status_template() {
    local name="$1"
    local author="$2"
    local date=$(date +%Y-%m-%d)

    cat << 'EOF'
# [Status Report Title]

**Type**: Status
**Version**: 1.0
**Last Updated**: ${date}
**Author**: ${author}
**Status**: Active

---

## Current Status

**Overall**: [Green/Yellow/Red]

**Summary**: [1-sentence current state]

---

## Integration Points

| Component | Status | Notes |
|-----------|--------|-------|
| Component 1 |  Complete | Working as expected |
| Component 2 |  In Progress | 75% complete |
| Component 3 |  Not Started | Planned for next week |

---

## What's Working

 Feature 1 - Fully operational
 Feature 2 - Deployed and tested
 Feature 3 - In production

---

## What's Not Working

 Issue 1 - Description
  Issue 2 - Description

---

## Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Coverage | 85% | 80% |  |
| Performance | 200ms | <300ms |  |
| Bugs | 3 | <5 |  |

---

## Next Steps

### Immediate (This Week)
1. [ ] Task 1
2. [ ] Task 2

### Short Term (Next Week)
1. [ ] Task 3
2. [ ] Task 4

### Long Term
1. [ ] Goal 1
2. [ ] Goal 2

---

## Related Documents

- [Link](path) - Description

---

## Changelog

### 1.0 (${date})
- Initial status report

---

**Document Control**
- **Created**: ${date}
- **Last Reviewed**: ${date}
- **Next Review**: [Weekly/Monthly]
- **Owner**: ${author}
EOF
}

main() {
    local doc_type=""
    local doc_name=""
    local author="$(whoami)"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --type)
                doc_type="$2"
                shift 2
                ;;
            --name)
                doc_name="$2"
                shift 2
                ;;
            --author)
                author="$2"
                shift 2
                ;;
            --help)
                print_usage
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                print_usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$doc_type" || -z "$doc_name" ]]; then
        echo -e "${RED}Error: --type and --name are required${NC}"
        print_usage
        exit 1
    fi

    # Validate document type
    case "$doc_type" in
        guide|spec|status|reference|example)
            ;;
        *)
            echo -e "${RED}Error: Invalid type '$doc_type'${NC}"
            echo -e "${YELLOW}Valid types: guide, spec, status, reference, example${NC}"
            exit 1
            ;;
    esac

    # Create filename
    local filename="${doc_type^^}-${doc_name}.md"
    local subdir="$DOCS_DIR"
    local output_file="$subdir/$filename"

    # Create subdirectory if needed (future organization)
    # mkdir -p "$subdir"

    # Check if file exists
    if [[ -f "$output_file" ]]; then
        echo -e "${YELLOW}File already exists: $output_file${NC}"
        echo -e "${YELLOW}Overwrite? (y/n)${NC}"
        read -r OVERWRITE
        if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}Aborted.${NC}"
            exit 0
        fi
    fi

    # Generate template
    echo -e "${BLUE}Creating $doc_type document: $filename${NC}"

    local template=""
    case "$doc_type" in
        guide)
            template=$(create_guide_template "$doc_name" "$author")
            ;;
        spec)
            template=$(create_spec_template "$doc_name" "$author")
            ;;
        status)
            template=$(create_status_template "$doc_name" "$author")
            ;;
        reference)
            template=$(create_guide_template "$doc_name" "$author")  # Similar to guide
            ;;
        example)
            template=$(create_guide_template "$doc_name" "$author")  # Similar to guide
            ;;
    esac

    # Substitute variables in template
    local date=$(date +%Y-%m-%d)
    template="${template//\$\{date\}/$date}"
    template="${template//\$\{author\}/$author}"

    # Write file
    echo "$template" > "$output_file"

    echo -e "${GREEN} Created: $output_file${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Edit the document: $output_file"
    echo "  2. Fill in the template placeholders"
    echo "  3. Review against: tooling/docs/DOC-STANDARD.md"
    echo "  4. Validate: ./tooling/scripts/validate-doc.sh $output_file"
    echo ""
}

main "$@"

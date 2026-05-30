# Technical Debt: [DEBT-ID]

**Priority**: [Critical/High/Medium/Low]
**Status**: Identified
**Created**: YYYY-MM-DD
**Category**: [Code Quality/Architecture/Dependencies/Testing/Documentation]

## Summary

[One-line description of the technical debt]

## Description

[Detailed description of the technical debt and its impact]

## Impact

### Current Pain
- [How this affects developers]
- [How this affects performance]
- [How this affects maintainability]

### Risk if Not Addressed
- [Risk 1]
- [Risk 2]

### Business Impact
- [Slower feature development]
- [Increased bug rate]
- [Other impacts]

## Location

| File/Component | Issue |
|----------------|-------|
| `path/to/file1` | [specific issue] |
| `path/to/file2` | [specific issue] |

## Root Cause

[How did this debt accumulate?]

- [ ] Time pressure
- [ ] Lack of understanding
- [ ] Changing requirements
- [ ] Outdated dependencies
- [ ] Missing tests
- [ ] Other: [describe]

## Proposed Resolution

### Option A: [Name]
- **Effort**: [estimate]
- **Risk**: [low/medium/high]
- **Description**: [approach]

### Option B: [Name]
- **Effort**: [estimate]
- **Risk**: [low/medium/high]
- **Description**: [approach]

### Recommended: [Option X]
[Why this option is recommended]

## Success Criteria

- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] All existing tests pass
- [ ] No performance regression

## Dependencies

- [What needs to happen first]
- [Related debt items]

## Notes

[Additional context]

---

**To resolve this tech debt:**
```bash
./run-story.sh [DEBT-ID] --tech-debt
```

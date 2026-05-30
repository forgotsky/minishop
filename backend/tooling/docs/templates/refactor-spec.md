# Refactoring Specification: [REFACTOR-ID]

**Priority**: [High/Medium/Low]
**Status**: Planned
**Created**: YYYY-MM-DD
**Estimated Effort**: [Small/Medium/Large]

## Target

[What code/component/module is being refactored]

## Current State

[Description of the current implementation and its problems]

### Pain Points

- [Pain point 1]
- [Pain point 2]
- [Pain point 3]

### Code Smells

- [ ] Long methods
- [ ] Duplicate code
- [ ] Complex conditionals
- [ ] Poor naming
- [ ] Missing abstractions
- [ ] Tight coupling
- [ ] Other: [describe]

## Desired State

[Description of what the code should look like after refactoring]

### Goals

- [ ] Improve readability
- [ ] Reduce duplication
- [ ] Improve testability
- [ ] Improve performance
- [ ] Reduce complexity
- [ ] Other: [describe]

## Affected Files

| File | Changes |
|------|---------|
| `path/to/file1.ts` | [brief description] |
| `path/to/file2.ts` | [brief description] |

## Approach

### Phase 1: [Name]
[Description of first phase]

### Phase 2: [Name]
[Description of second phase]

## Testing Strategy

- [ ] Existing tests should continue to pass
- [ ] Add tests for: [specific areas]
- [ ] Manual testing needed for: [specific scenarios]

## Risks

| Risk | Mitigation |
|------|------------|
| [Risk 1] | [How to mitigate] |
| [Risk 2] | [How to mitigate] |

## Rollback Plan

[How to revert if something goes wrong]

## Notes

[Any additional context]

---

**To run this refactoring:**
```bash
./run-story.sh [REFACTOR-ID] --refactor
```

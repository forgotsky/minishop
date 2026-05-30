# Bug Report: [BUG-ID]# Bug Report: [BUG-ID]



**Severity**: [Critical/High/Medium/Low]**Severity**: [Critical/High/Medium/Low]

**Status**: Open**Status**: Open

**Reported**: YYYY-MM-DD**Reported**: YYYY-MM-DD

**Component**: [affected component/module]**Component**: [affected component/module]

**Regression**: [Yes/No - was this working before?]

## Summary

## Summary

[One-line description of the bug]

[One-line description of the bug]

## Steps to Reproduce

## Steps to Reproduce

1. [First step]

1. [First step]2. [Second step]

2. [Second step]3. [Third step]

3. [Third step]

## Expected Behavior

**Reproducibility**: [Always / Sometimes (X%) / Rare / Unknown]

[What should happen]

## Expected Behavior

## Actual Behavior

[What should happen]

[What actually happens]

## Actual Behavior

## Environment

[What actually happens]

- **OS**: [e.g., macOS 14.0, Windows 11, Ubuntu 22.04]

## Environment- **Version**: [app version or commit hash]

- **Browser/Runtime**: [if applicable]

- **OS**: [e.g., macOS 14.0, Windows 11, Ubuntu 22.04]

- **Version**: [app version or commit hash]## Logs/Screenshots

- **Browser/Runtime**: [if applicable]

- **Device/Hardware**: [if applicable]```

- **Network**: [online/offline/slow connection if relevant][Paste relevant error logs here]

```

## Logs/Screenshots

## Possible Root Cause

```

[Paste relevant error logs here][If you have any ideas about what might be causing this]

```

## Related Files

## Root Cause Analysis

- `path/to/file1.ts` - [why this file might be relevant]

### 5 Whys Analysis- `path/to/file2.ts` - [why this file might be relevant]



Use this technique to dig deeper into the root cause:## Notes



1. **Why did this happen?**[Any additional context or information]

   [First level cause]

---

2. **Why did that happen?**

   [Second level cause]**To fix this bug, run:**

```bash

3. **Why did that happen?**./run-story.sh [BUG-ID] --bugfix

   [Third level cause]```


4. **Why did that happen?**
   [Fourth level cause]

5. **Why did that happen?**
   [Root cause - this is usually the systemic issue]

### Fault Tree

Visualize possible causes:

```
[Bug Symptom]
├── [Possible Cause A]
│   ├── [Sub-cause A1]
│   └── [Sub-cause A2]
├── [Possible Cause B]
│   └── [Sub-cause B1]
└── [Possible Cause C] <- [Most likely]
```

### Root Cause Category

Check the category that best describes this bug:

- [ ] **Code Logic** - Algorithm or logic error
- [ ] **Data Handling** - Incorrect data processing/validation
- [ ] **State Management** - Race condition or state corruption
- [ ] **Integration** - API/service communication issue
- [ ] **Configuration** - Misconfiguration or environment issue
- [ ] **Resource** - Memory, CPU, or resource exhaustion
- [ ] **Concurrency** - Threading or async timing issue
- [ ] **Edge Case** - Unhandled boundary condition
- [ ] **Dependency** - Third-party library issue
- [ ] **User Input** - Invalid input not properly handled
- [ ] **Unknown** - Requires further investigation

### Hypothesis

**Most Likely Cause**: [Your best hypothesis about what's causing this]

**Evidence Supporting This**:
- [Evidence 1]
- [Evidence 2]

**Evidence Against This**:
- [Counter-evidence 1]

### Investigation Steps Taken

| Step | What I Checked | Result |
|------|----------------|--------|
| 1 | [e.g., Checked logs] | [What I found] |
| 2 | [e.g., Added debug output] | [What I found] |
| 3 | [e.g., Tested in isolation] | [What I found] |

## Related Files

| File | Relevance | Confidence |
|------|-----------|------------|
| `path/to/file1.ts` | [why relevant] | High/Medium/Low |
| `path/to/file2.ts` | [why relevant] | High/Medium/Low |

## Impact Analysis

### Users Affected
- [ ] All users
- [ ] Specific user segment: [describe]
- [ ] Internal only
- [ ] Rare edge case

### Workaround Available
- [ ] **Yes**: [describe workaround]
- [ ] **No**: Users are blocked

### Related Issues
- Related to: #[issue-number]
- Blocks: #[issue-number]
- Caused by: [commit/PR reference]

## Proposed Fix

### Approach
[Brief description of the fix approach]

### Files to Modify
1. `path/to/file1.ts` - [what to change]
2. `path/to/file2.ts` - [what to change]

### Tests to Add
- [ ] Unit test for [specific scenario]
- [ ] Integration test for [specific scenario]
- [ ] Regression test to prevent recurrence

### Rollback Plan
[How to revert if the fix causes issues]

## Prevention

### How to Prevent Similar Bugs

- [ ] Add input validation for [specific case]
- [ ] Add automated test for [scenario]
- [ ] Add monitoring/alerting for [condition]
- [ ] Update documentation about [edge case]
- [ ] Code review checklist item for [pattern]

## Notes

[Any additional context or information]

---

**To fix this bug, run:**
```bash
./run-story.sh [BUG-ID] --bugfix
```

**To investigate first:**
```bash
./run-story.sh [BUG-ID] --investigate
```

# Migration Specification: [MIGRATION-ID]

**Priority**: [Critical/High/Medium/Low]
**Status**: Planned
**Created**: YYYY-MM-DD
**Target Date**: YYYY-MM-DD
**Estimated Downtime**: [None/Minutes/Hours]
**Risk Level**: [Low/Medium/High/Critical]

## Overview

[Brief description of what is being migrated]

## Motivation

[Why this migration is necessary]

- [Reason 1]
- [Reason 2]
- [Reason 3]

## Current State

| Component | Current Version | Target Version | Notes |
|-----------|-----------------|----------------|-------|
| [Dependency/Framework] | [current] | [target] | [breaking changes?] |

## Impact Analysis

### Users/Systems Affected
- [ ] All users
- [ ] Internal systems only
- [ ] Specific feature: [describe]
- [ ] Background processes

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| [Risk 1] | Low/Med/High | Low/Med/High | [Strategy] |
| [Risk 2] | Low/Med/High | Low/Med/High | [Strategy] |

## Pre-Migration Checklist

### Preparation (1-2 weeks before)
- [ ] Create rollback point: `./rollback-migration.sh --create [MIGRATION-ID]-pre`
- [ ] Backup database (if applicable)
- [ ] Review breaking changes documentation
- [ ] Update test environment
- [ ] Run full test suite on current version
- [ ] Notify stakeholders
- [ ] Schedule maintenance window (if needed)

### Day Before
- [ ] Verify rollback point exists
- [ ] Test rollback procedure in staging
- [ ] Confirm all team members are available
- [ ] Prepare communication for users

### Immediately Before
- [ ] Final backup check
- [ ] Verify monitoring is active
- [ ] Clear deployment queue

## Migration Steps

### Phase 1: Preparation
1. **Create rollback checkpoint**
   ```bash
   cd tooling/scripts
   ./rollback-migration.sh --create [MIGRATION-ID]-pre
   ```

2. **Verify current state**
   ```bash
   # Run tests before migration
   [test command here]
   ```

### Phase 2: Dependencies
1. **Update package files**
   - Files affected: `package.json` / `pubspec.yaml` / `requirements.txt`
   - Changes:
     ```diff
     - "package": "^old-version"
     + "package": "^new-version"
     ```

2. **Install new dependencies**
   ```bash
   # npm / yarn / flutter pub get / pip install
   [install command]
   ```

### Phase 3: Code Changes
1. **[Change Description 1]**
   - Files affected: `path/to/file`
   - Changes needed: [describe the code changes]

2. **[Change Description 2]**
   - Files affected: `path/to/file`
   - Changes needed: [describe the code changes]

3. **[Change Description 3]**
   - Files affected: `path/to/file`
   - Changes needed: [describe the code changes]

### Phase 4: Configuration
1. **Update configuration files**
   - Files: `config/...`
   - Changes: [describe]

### Phase 5: Verification
1. **Run test suite**
   ```bash
   [test command]
   ```

2. **Manual smoke test**
   - [ ] [Critical path 1]
   - [ ] [Critical path 2]
   - [ ] [Critical path 3]

## Post-Migration

- [ ] Run full test suite
- [ ] Verify all critical paths manually
- [ ] Check error logs for anomalies
- [ ] Monitor performance metrics
- [ ] Update documentation
- [ ] Notify stakeholders of completion
- [ ] Keep rollback point for [X days]

## Breaking Changes

| Change | What Breaks | How to Fix | Automated? |
|--------|-------------|------------|------------|
| [Change 1] | [What breaks] | [How to fix] | Yes/No |
| [Change 2] | [What breaks] | [How to fix] | Yes/No |

## Rollback Plan

### Rollback Triggers
Execute rollback if ANY of these occur:
- [ ] Test suite failure rate > [X]%
- [ ] Critical functionality broken
- [ ] Performance degradation > [X]%
- [ ] User-reported blocking issues
- [ ] Deployment time exceeds [X] hours

### Automated Rollback

```bash
# Quick rollback using saved checkpoint
cd tooling/scripts
./rollback-migration.sh [MIGRATION-ID]

# Or restore from specific point
./rollback-migration.sh --restore [MIGRATION-ID]-pre
```

### Manual Rollback Steps

If automated rollback fails:

1. **Restore dependencies**
   ```bash
   # Restore package files from backup
   git checkout [pre-migration-commit] -- package.json package-lock.json
   # Reinstall
   npm install
   ```

2. **Restore code changes**
   ```bash
   # Revert to pre-migration commit
   git checkout [pre-migration-commit] -- src/
   ```

3. **Restore configuration**
   ```bash
   git checkout [pre-migration-commit] -- config/
   ```

4. **Verify rollback**
   ```bash
   [test command]
   ```

5. **Notify stakeholders**
   - Reason for rollback
   - Next steps
   - Timeline for retry

### Rollback Verification
- [ ] All tests pass
- [ ] Critical paths working
- [ ] No data corruption
- [ ] Performance restored

## Testing Plan

### Automated Tests
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Performance benchmarks acceptable

### Manual Testing Checklist
- [ ] [Critical user flow 1]
- [ ] [Critical user flow 2]
- [ ] [Edge case 1]
- [ ] [Edge case 2]

### Regression Tests
- [ ] [Feature that might regress 1]
- [ ] [Feature that might regress 2]

## Communication Plan

### Before Migration
- **Who**: [stakeholders]
- **When**: [X days before]
- **What**: [brief about upcoming changes]

### During Migration
- **Channel**: [Slack/Email/Status page]
- **Updates**: Every [X] minutes

### After Migration
- **Success**: [communication template]
- **Failure/Rollback**: [communication template]

## Dependencies

| Dependency | Status | Owner | Notes |
|------------|--------|-------|-------|
| [Dep 1] | Ready/Pending | [Name] | [Notes] |
| [Dep 2] | Ready/Pending | [Name] | [Notes] |

## Lessons Learned

*To be filled after migration*

### What Went Well
-

### What Could Be Improved
-

### Action Items
-

## Notes

[Additional context, links to documentation, etc.]

---

**Commands:**

```bash
# Create pre-migration checkpoint
./rollback-migration.sh --create [MIGRATION-ID]-pre

# Run migration with Claude
./run-story.sh [MIGRATION-ID] --migrate

# Rollback if needed
./rollback-migration.sh [MIGRATION-ID]

# Preview rollback without executing
./rollback-migration.sh [MIGRATION-ID] --dry-run
```

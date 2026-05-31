---
description: Handle URS change — re-run affected pipeline phases
argument-hint: <story-key> <what changed in the URS>
---

## Change Request: $ARGUMENTS

Handle a change to the User Requirement Specification for an existing story.

### Change Impact Assessment

1. **Read the current URS** — `docs/stories/<story-key>/1-urs.md`
2. **Identify what changed** — which user stories, acceptance criteria, or scope items
3. **Determine impact level:**

| Level | Trigger | What to re-run |
|-------|---------|---------------|
| LIGHT | Clarification, wording | Update URS doc only |
| MEDIUM | New acceptance criteria, scope change | URS → Story → Review |
| HEAVY | New user story, API change, data model change | Full pipeline: URS → Story → Arch → Dev → Review |

### Pipeline Re-run Strategy

For MEDIUM/HEAVY changes:

```
Updated URS
  ↓
BA: revise 1-urs.md (add change log at the bottom)
  ↓
PM: revise 2-story.md (mark changed stories, re-estimate)
  ↓
Architect: revise 3-architecture.md (if API/data model affected)
  ↓
Dev: implement the delta (only the changed parts)
  ↓
Reviewer: re-review changed files only
```

### Change Log Format

Append to the bottom of `1-urs.md`:

```markdown
## Change Log

### v1.1 (2026-06-01)
- Added: US-004 用户注销功能
- Changed: AC-001 登录流程增加微信授权弹窗说明
- Removed: US-003 的管理员角色（P3, 下个版本做）
```

### Implementation Rules
1. **NEVER delete old requirements** — mark them as "Removed in v1.X"
2. **Add, don't overwrite** — new AC appended, not replacing old
3. **Re-run the minimum needed** — LIGHT changes don't need code review
4. **Keep story status updated** — if a story goes from Done → In Progress, note why

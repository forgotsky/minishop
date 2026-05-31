---
description: Run comprehensive code review on pending changes
---

Run a code review on the current uncommitted changes. Use the `code-reviewer` agent to:

1. Check all modified files for bugs and security issues
2. Verify WeChat miniprogram compatibility (no `?.`, no `??`)
3. Check for `datetime.utcnow()` (should be `datetime.now(timezone.utc)`)
4. Report findings with severity levels

Then fix any issues found.

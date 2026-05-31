---
description: Fix a bug in the MiniShop project
argument-hint: <bug description>
---

Fix the following bug: $ARGUMENTS

Steps:
1. Reproduce and understand the root cause
2. Check server logs if needed: `kubectl logs -n shop deployment/shop-app --tail=50`
3. Fix the bug in the appropriate file
4. If backend: verify the fix locally, push with descriptive commit message
5. If frontend: verify WeChat DevTools compatibility
6. If the fix is urgent, push to `simple` branch and merge to `main`

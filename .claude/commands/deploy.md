---
description: Trigger CD deployment to production
---

Push current changes from `simple` to `main` branch to trigger CD deployment:

```bash
git push origin simple:main
```

This will trigger:
1. Run backend tests
2. Build Docker image
3. Push to ghcr.io/forgotsky/minishop
4. Deploy to K3s server (43.156.92.63)
5. Rolling update with zero downtime

After pushing, monitor at: https://github.com/forgotsky/minishop/actions

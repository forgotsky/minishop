---
description: Develop a new feature using the backend-dev agent
argument-hint: <feature description>
---

Develop the following feature for MiniShop: $ARGUMENTS

Use the `backend-dev` agent for backend changes and `miniprogram-dev` agent for frontend changes.

Workflow:
1. Understand the requirement
2. Plan the approach (which files need changes)
3. Implement backend changes first (main.py, models.py, etc.)
4. Update the miniprogram API layer (utils/api.js)
5. Update miniprogram pages if needed
6. Test the full flow
7. Commit with a descriptive message

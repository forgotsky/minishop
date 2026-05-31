---
description: Run full story pipeline — URS → Story → Architecture → Code → Review → Docs
argument-hint: <story-key> <feature description>
---

## Story Pipeline: $ARGUMENTS

Run the FULL automated story pipeline. Extract the story key and description from: $ARGUMENTS

### Pipeline Steps

Each phase produces a REAL file in `docs/stories/<story-key>/`:

**Phase 1 — URS (Business Analyst)**
→ Output: `docs/stories/<story-key>/1-urs.md`
Analyze the requirement. Write User Requirement Specification with:
- Feature summary
- User stories (As a / I want / So that)
- Acceptance criteria (Given/When/Then)
- Scope (In/Out)
- Dependencies

**Phase 2 — Story Breakdown (Product Manager)**
→ Output: `docs/stories/<story-key>/2-story.md`
Break down into implementable stories with:
- Story key + priority (P0-P3)
- Effort estimate (S/M/L/XL)
- Frontend tasks (pages/components)
- Backend tasks (endpoints/models)
- K8s changes (if any)

**Phase 3 — Architecture (Architect)**
→ Output: `docs/stories/<story-key>/3-architecture.md`
Design the technical solution:
- API endpoint design (method, path, request/response)
- Database changes (new tables/columns/migrations)
- Frontend component tree
- Data flow diagram (text)
- Security considerations

**Phase 4 — Implementation (Developer)**
→ Output: actual code changes
Implement the feature following the architecture:
- Backend: FastAPI routes, models, Pydantic schemas
- Frontend: WXML pages, JS logic, API calls
- Ensure WeChat compatibility (no `?.`, no `??`)

**Phase 5 — Code Review (Reviewer)**
→ Output: `docs/stories/<story-key>/5-review.md`
Critical review with:
- Correctness bugs found
- Security issues found
- WeChat compatibility check
- Recommendations

**Phase 6 — Documentation (Tech Writer)**
→ Output: `docs/stories/<story-key>/README.md`
Final summary document with:
- What was built
- How to test
- API documentation
- Screenshots checklist

### Auto-Commit
After all phases pass review, commit with: `feat: <story-key> <summary>`

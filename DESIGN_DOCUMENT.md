# Skill Trainer Design Document

## 1. Objective
Build a mini-app that helps learners:
- Browse skill categories and top skills
- See L1-L6 progression with knowledge points
- Generate weekly plans based on daily time
- Track completion and progress
- Create subject templates that auto-generate skill trees

## 2. Architecture
Two-service architecture:
- Frontend: uni-app (Vue syntax), compiled to WeChat/Douyin/Alipay mini-apps and H5
- Backend: Python FastAPI REST API

Communication:
- Frontend calls backend over HTTP JSON APIs (`/api/skills`, `/api/template`, `/api/plan`)
- Client stores progress locally (storage) to keep the backend stateless

## 3. Frontend Design (uni-app)
Location:
- `uni-app/pages/index/index.vue`
- `uni-app/pages/skill/skill.vue`
- `uni-app/pages/template/template.vue`

Responsibilities:
- Render categories and Top3 skills
- Show L1-L6 knowledge points
- Trigger template generation (backend, fallback local)
- Trigger plan generation (backend, fallback local)
- Persist plan progress locally

State management:
- Local component state + storage
- API base URL stored in `API_BASE_URL` (storage)

## 4. Backend Design (FastAPI)
Location:
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/db.py`

Responsibilities:
- Serve base skills data from DB
- Generate subject templates and persist them
- Generate weekly plans and persist them

Database:
- Default: SQLite for local (`sqlite:///./app.db`)
- Production: Postgres via `DATABASE_URL`

## 5. API Contract
### GET `/api/skills`
Response:
- `{ "categories": [ ... ] }`

### POST `/api/template`
Request body:
- `{ "subject": "英语" }`

Response:
- `{ "category": { ... } }`

### POST `/api/plan`
Request body:
- `hour_tasks`: array of tasks with `slot`, `wordsText`, `sentence`, `usage`
- `daily_minutes`: int (20-180)
- `days_per_week`: int (1-7)

Response:
- `{ "plan": { planId, dailyMinutes, daysPerWeek, schedule, flatTasks } }`

## 6. Deployment Design
Containers:
- `backend/Dockerfile`: serves FastAPI via Uvicorn on port 8000
- `uni-app/Dockerfile`: builds H5 bundle and serves via Nginx on port 80

Kubernetes:
- Backend Deployment + Service
- Postgres Deployment + Service + PVC
- uni-frontend Deployment + Service
- Optional ALB Ingress routes:
  - `/api` -> backend service
  - `/uni` -> uni-frontend service

## 7. Security and Validation Notes
- Backend validates plan inputs and constraints
- CORS allowlist should be restricted in production
- TLS should be enabled at Ingress/Load Balancer

## 8. Scalability Notes
- Stateless services; horizontal scaling via replica count
- Skills data is seeded into DB on startup if empty
- For production, use managed Postgres and backups

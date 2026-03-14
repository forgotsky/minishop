# Skill Trainer Design Document (Simple)

## 1. Objective
Provide a minimal, docker-only deployment of the skill trainer:
- Browse skill categories and Top3 skills
- See L1-L6 knowledge points
- Generate weekly plans
- Track completion locally (front-end storage)
- Generate templates

## 2. Architecture
Two-service + database:
- Frontend: uni-app H5 build served by Nginx
- Backend: FastAPI REST API
- Database: Postgres

## 3. Frontend (uni-app H5)
Location:
- `uni-app/pages/index/index.vue`
- `uni-app/pages/skill/skill.vue`
- `uni-app/pages/template/template.vue`

Responsibilities:
- Render categories and skills
- Call backend APIs
- Persist progress locally

## 4. Backend (FastAPI)
Location:
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/db.py`

Responsibilities:
- Serve skills from DB
- Generate templates and persist
- Generate plans and persist

## 5. API
- `GET /api/skills`
- `POST /api/template`
- `POST /api/plan`

## 6. Deployment (Simple)
Docker only:
- `backend/Dockerfile`
- `uni-app/Dockerfile`
- Postgres official image

No Kubernetes in this branch.

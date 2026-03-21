# Skill Trainer (Simple Docker) 

Minimal deployment using Docker only.

## What you get
- Backend: FastAPI API service
- Frontend: uni-app H5 build served by Nginx
- Database: Postgres container

## Quick Start (Linux)

1. Build images
```bash
cd /root/codex/backend
docker build -t skill-backend:latest .

cd /root/codex/uni-app
# edit DEFAULT_BASE_URL before build (see Deployment Guide)
docker build -t skill-frontend:latest .
```

2. Run containers
```bash
# create network
docker network create skill-net

# run postgres
docker run -d --name skill-postgres --network skill-net \
  -e POSTGRES_DB=skill_trainer \
  -e POSTGRES_USER=skill_user \
  -e POSTGRES_PASSWORD=skill_pass \
  -p 5432:5432 postgres:15-alpine

# run backend
docker run -d --name skill-backend --network skill-net \
  -e DATABASE_URL=postgresql+psycopg2://skill_user:skill_pass@skill-postgres:5432/skill_trainer \
  -e ALLOWED_ORIGINS=http://<SERVER_IP>:5174 \
  -p 8000:8000 skill-backend:latest

# run frontend
docker run -d --name skill-frontend --network skill-net \
  -p 5174:80 skill-frontend:latest
```

3. Open
- API: `http://<SERVER_IP>:8000/api/health`
- H5: `http://<SERVER_IP>:5174`

## Docs
- `DEPLOYMENT_GUIDE.md`
- `FRONTEND_GUIDE.md`
- `DESIGN_DOCUMENT.md`

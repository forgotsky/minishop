# Deployment Guide (Simple Docker)

This branch provides a minimal Docker-only deployment (no Kubernetes, no compose required).

## Requirements
- Linux server with Docker
- Open ports: 8000 (backend), 5174 (frontend)

## Step 1. Set API base URL for H5 build
Edit `uni-app/utils/api.js`:

```js
const DEFAULT_BASE_URL = "http://<SERVER_IP>:8000";
```

This is required so the H5 build calls the correct backend host.

## Step 2. Build images
```bash
cd /root/codex/backend
docker build -t skill-backend:latest .

cd /root/codex/uni-app
docker build -t skill-frontend:latest .
```

## Step 3. Run containers
```bash
# create isolated network
docker network create skill-net

# postgres
docker run -d --name skill-postgres --network skill-net \
  -e POSTGRES_DB=skill_trainer \
  -e POSTGRES_USER=skill_user \
  -e POSTGRES_PASSWORD=skill_pass \
  -p 5432:5432 postgres:15-alpine

# backend
docker run -d --name skill-backend --network skill-net \
  -e DATABASE_URL=postgresql+psycopg2://skill_user:skill_pass@skill-postgres:5432/skill_trainer \
  -e ALLOWED_ORIGINS=http://<SERVER_IP>:5174 \
  -p 8000:8000 skill-backend:latest

# frontend
docker run -d --name skill-frontend --network skill-net \
  -p 5174:80 skill-frontend:latest
```

## Step 4. Verify
```bash
curl http://<SERVER_IP>:8000/api/health
```
Open in browser:
- `http://<SERVER_IP>:5174`

## Stop / Remove
```bash
docker stop skill-frontend skill-backend skill-postgres
```
```bash
docker rm skill-frontend skill-backend skill-postgres
```
```bash
docker network rm skill-net
```

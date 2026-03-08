# Skill Trainer Mini App

Stack:
- Frontend: uni-app (Vue-based) for multi-platform mini apps + H5 build
- Backend: Python FastAPI REST API
- Database: Postgres (SQLite fallback for local)
- Deployment: Docker + Kubernetes

Main docs:
- `DESIGN_DOCUMENT.md`
- `FRONTEND_GUIDE.md`
- `DEPLOYMENT_GUIDE.md`

## Project Layout
- `uni-app/` uni-app source (mini-app + H5)
- `backend/` FastAPI app
- `k8s/` Kubernetes manifests
- `scripts/` utility scripts

## Local Development
Backend:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (H5):
```bash
cd uni-app
npm install
npm run dev:h5
```

Optional Docker local:
```bash
docker compose up --build
```

## Notes
- Mini-app builds are done via HBuilderX or `uni-app` CLI.
- H5 preview runs on `http://localhost:5174` when using Docker Compose.

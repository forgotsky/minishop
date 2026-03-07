# Web Shop Application

Stack:
- Frontend: React (Vite)
- Backend: Python FastAPI
- Deployment: Docker + Kubernetes (EKS)

Main docs:
- `DESIGN_DOCUMENT.md`
- `FRONTEND_GUIDE.md`
- `DEPLOYMENT_GUIDE.md`

## Project Layout
- `frontend/` React app
- `backend/` FastAPI app
- `k8s/` Kubernetes manifests
- `scripts/deploy.sh` one-command EKS deploy

## Local Development
Backend:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Optional Docker local:
```bash
docker compose up --build
```

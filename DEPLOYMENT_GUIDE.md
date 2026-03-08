# Deployment Guide (uni-app + FastAPI + Postgres)

## 1. Docker Compose (Local)
```bash
docker compose up --build
```

Services:
- Postgres: `localhost:5432`
- Backend: `http://localhost:8000`
- uni-app H5: `http://localhost:5174`

## 2. Build Images
Backend:
```bash
docker build -t your-registry/skill-backend:latest ./backend
```

uni-app (H5):
```bash
cd uni-app
npm install
npm run build:h5
cd ..
docker build -t your-registry/uni-frontend:latest ./uni-app
```

## 3. Push Images
```bash
docker push your-registry/skill-backend:latest
docker push your-registry/uni-frontend:latest
```

## 4. Kubernetes Apply
```bash
kubectl apply -f k8s/postgres/pvc.yaml
kubectl apply -f k8s/postgres/deployment.yaml
kubectl apply -f k8s/postgres/service.yaml
kubectl apply -f k8s/backend/service.yaml
kubectl apply -f k8s/backend/deployment.yaml
kubectl apply -f k8s/uni-frontend/service.yaml
kubectl apply -f k8s/uni-frontend/deployment.yaml
kubectl apply -f k8s/gateway/ingress.yaml
```

## 5. Configure Ingress
Edit `k8s/gateway/ingress.yaml`:
- `host` change to your domain
- paths:
  - `/api` -> backend
  - `/uni` -> uni-frontend

## 6. Environment Variables
Backend:
- `ALLOWED_ORIGINS`
- `DATABASE_URL`

Example:
```
ALLOWED_ORIGINS=https://yourdomain.com
DATABASE_URL=postgresql+psycopg2://skill_user:skill_pass@postgres:5432/skill_trainer
```

## 7. Mini-App Deployment
Use HBuilderX to build for each platform:
1. Open `uni-app/` in HBuilderX
2. Fill `manifest.json` AppID per platform
3. 发行 -> 小程序 -> 选择平台
4. Use platform devtools to预览/上传

## 8. Production Notes
- Prefer managed Postgres
- Configure backups and TLS
- Restrict CORS in production

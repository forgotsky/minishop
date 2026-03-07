# Deployment Guide (React + FastAPI)

## Prerequisites
- AWS CLI configured
- Docker installed
- kubectl installed
- EKS cluster created
- AWS Load Balancer Controller installed (if using ALB ingress)

## One-command EKS Deploy
Use script:

```bash
cd /root/codex
./scripts/deploy.sh \
  --aws-region <AWS_REGION> \
  --aws-account-id <AWS_ACCOUNT_ID> \
  --cluster-name <EKS_CLUSTER_NAME> \
  --frontend-repo web-shop-frontend \
  --backend-repo web-shop-backend \
  --namespace web-shop \
  --image-tag v1 \
  --allowed-origins https://shop.yourdomain.com \
  --host shop.yourdomain.com \
  --apply-ingress
```

What it does:
- Ensures ECR repositories exist
- Builds and pushes frontend/backend images
- Applies k8s service/deployment manifests
- Sets deployment images
- Sets backend `ALLOWED_ORIGINS`
- Optionally applies ingress with your host
- Waits for rollout

## Manual Kubernetes Deploy
Apply manifests:

```bash
kubectl apply -f k8s/frontend/service.yaml
kubectl apply -f k8s/frontend/deployment.yaml
kubectl apply -f k8s/backend/service.yaml
kubectl apply -f k8s/backend/deployment.yaml
kubectl apply -f k8s/gateway/ingress.yaml
```

Then set images:

```bash
kubectl set image deployment/web-shop-frontend web-shop-frontend=<FRONTEND_ECR_URI>
kubectl set image deployment/web-shop-backend web-shop-backend=<BACKEND_ECR_URI>
```

## Deploy Separately (Frontend and Backend)
Frontend:
- Deploy `frontend` image to ECS/EKS or static build to S3+CloudFront

Backend:
- Deploy `backend` image to EKS/ECS
- Set CORS env:
  - `ALLOWED_ORIGINS=https://shop.yourdomain.com`

Frontend config:
- Set `frontend/public/config.js` with backend URL

## Local Docker Test
```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000/api/health`

## Download Code Package
Archive path:
- `/root/codex/web-shop-app.tar.gz`

Create/update archive:
```bash
cd /root/codex
tar --exclude='node_modules' --exclude='frontend/node_modules' --exclude='.git' -czf web-shop-app.tar.gz .
```

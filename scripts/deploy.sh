#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage:
  ./scripts/deploy.sh \
    --aws-region <region> \
    --aws-account-id <account_id> \
    --cluster-name <eks_cluster_name> \
    --frontend-repo <ecr_repo_name> \
    --backend-repo <ecr_repo_name> \
    [--namespace <k8s_namespace>] \
    [--image-tag <tag>] \
    [--allowed-origins <origins_csv>] \
    [--host <shop_domain>] \
    [--apply-ingress]
USAGE
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

AWS_REGION=""
AWS_ACCOUNT_ID=""
CLUSTER_NAME=""
FRONTEND_REPO=""
BACKEND_REPO=""
NAMESPACE="default"
IMAGE_TAG="latest"
ALLOWED_ORIGINS=""
HOST="shop.yourdomain.com"
APPLY_INGRESS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --aws-region) AWS_REGION="$2"; shift 2 ;;
    --aws-account-id) AWS_ACCOUNT_ID="$2"; shift 2 ;;
    --cluster-name) CLUSTER_NAME="$2"; shift 2 ;;
    --frontend-repo) FRONTEND_REPO="$2"; shift 2 ;;
    --backend-repo) BACKEND_REPO="$2"; shift 2 ;;
    --namespace) NAMESPACE="$2"; shift 2 ;;
    --image-tag) IMAGE_TAG="$2"; shift 2 ;;
    --allowed-origins) ALLOWED_ORIGINS="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --apply-ingress) APPLY_INGRESS="true"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$AWS_REGION" || -z "$AWS_ACCOUNT_ID" || -z "$CLUSTER_NAME" || -z "$FRONTEND_REPO" || -z "$BACKEND_REPO" ]]; then
  echo "Missing required arguments." >&2
  usage
  exit 1
fi

require_cmd aws
require_cmd docker
require_cmd kubectl
require_cmd sed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FRONTEND_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FRONTEND_REPO}:${IMAGE_TAG}"
BACKEND_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO}:${IMAGE_TAG}"

aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" >/dev/null
kubectl get namespace "$NAMESPACE" >/dev/null 2>&1 || kubectl create namespace "$NAMESPACE"

ensure_repo() {
  local repo="$1"
  if ! aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$repo" >/dev/null 2>&1; then
    aws ecr create-repository --region "$AWS_REGION" --repository-name "$repo" >/dev/null
  fi
}

ensure_repo "$FRONTEND_REPO"
ensure_repo "$BACKEND_REPO"

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build -t "$FRONTEND_IMAGE" "$PROJECT_ROOT/frontend"
docker build -t "$BACKEND_IMAGE" "$PROJECT_ROOT/backend"

docker push "$FRONTEND_IMAGE"
docker push "$BACKEND_IMAGE"

kubectl apply -n "$NAMESPACE" -f "$PROJECT_ROOT/k8s/frontend/service.yaml"
kubectl apply -n "$NAMESPACE" -f "$PROJECT_ROOT/k8s/frontend/deployment.yaml"
kubectl apply -n "$NAMESPACE" -f "$PROJECT_ROOT/k8s/backend/service.yaml"
kubectl apply -n "$NAMESPACE" -f "$PROJECT_ROOT/k8s/backend/deployment.yaml"

kubectl set image deployment/web-shop-frontend web-shop-frontend="$FRONTEND_IMAGE" -n "$NAMESPACE"
kubectl set image deployment/web-shop-backend web-shop-backend="$BACKEND_IMAGE" -n "$NAMESPACE"

if [[ -n "$ALLOWED_ORIGINS" ]]; then
  kubectl set env deployment/web-shop-backend ALLOWED_ORIGINS="$ALLOWED_ORIGINS" -n "$NAMESPACE"
fi

if [[ "$APPLY_INGRESS" == "true" ]]; then
  TMP_INGRESS="$(mktemp)"
  sed "s/shop.yourdomain.com/${HOST}/g" "$PROJECT_ROOT/k8s/gateway/ingress.yaml" > "$TMP_INGRESS"
  kubectl apply -n "$NAMESPACE" -f "$TMP_INGRESS"
  rm -f "$TMP_INGRESS"
fi

kubectl rollout status deployment/web-shop-frontend -n "$NAMESPACE"
kubectl rollout status deployment/web-shop-backend -n "$NAMESPACE"

echo "Deployment complete"
echo "Frontend image: $FRONTEND_IMAGE"
echo "Backend image: $BACKEND_IMAGE"

kubectl get svc -n "$NAMESPACE"
if [[ "$APPLY_INGRESS" == "true" ]]; then
  kubectl get ingress -n "$NAMESPACE"
fi

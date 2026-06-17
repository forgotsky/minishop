#!/bin/bash
# ================================================================
# K3s 服务器一键初始化脚本
# 在服务器上运行一次即可：bash scripts/k3s-setup.sh
# ================================================================

set -e

echo "=============================================="
echo "  1/6  安装 K3s"
echo "=============================================="
if command -v kubectl &>/dev/null; then
  echo "✓ K3s 已安装，跳过"
else
  curl -sfL https://get.k3s.io | sh
  mkdir -p ~/.kube
  cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
  chmod 600 ~/.kube/config
  echo 'export KUBECONFIG=~/.kube/config' >> ~/.bashrc
  export KUBECONFIG=~/.kube/config
  echo "✓ K3s 安装完成"
fi

echo ""
echo "=============================================="
echo "  2/6  安装 Git（如果没有）"
echo "=============================================="
which git &>/dev/null || apt-get update && apt-get install -y git

echo ""
echo "=============================================="
echo "  3/6  克隆项目"
echo "=============================================="
APP_DIR="/opt/shop-app"
if [ -d "$APP_DIR" ]; then
  echo "✓ 项目目录已存在，执行 git pull"
  cd "$APP_DIR"
  git checkout main
  git pull origin main
else
  git clone https://github.com/forgotsky/minishop.git "$APP_DIR"
  cd "$APP_DIR"
  echo "✓ 项目克隆完成"
fi

echo ""
echo "=============================================="
echo "  4/6  创建 K8s Secret（数据库密码）"
echo "=============================================="
# 生成随机密码
DB_PASS=$(openssl rand -hex 16 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 32)
echo "  生成数据库密码: $DB_PASS"

kubectl create namespace shop --dry-run=client -o yaml | kubectl apply -f -
kubectl -n shop delete secret shop-secret --ignore-not-found
kubectl -n shop create secret generic shop-secret \
  --from-literal=DB_PASSWORD="$DB_PASS" \
  --from-literal=POSTGRES_PASSWORD="$DB_PASS"

echo "✓ Secret 已创建"
echo ""
echo "  ⚠️  请把以下密码保存在安全的地方："
echo "  DB 密码: $DB_PASS"

echo ""
echo "=============================================="
echo "  5/6  部署所有 K8s 资源"
echo "=============================================="
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/app.yaml
kubectl apply -f k8s/ingress.yaml

echo ""
echo "=============================================="
echo "  6/6  等待服务就绪"
echo "=============================================="
kubectl -n shop wait --for=condition=available deployment/shop-app --timeout=120s 2>/dev/null || true
kubectl -n shop wait --for=condition=available deployment/postgres --timeout=120s 2>/dev/null || true

echo ""
echo "=============================================="
echo "  ✓ 所有部署完成！"
echo ""
echo "  查看状态:  kubectl get all -n shop"
echo "  查看日志:  kubectl logs -f -n shop deployment/shop-app"
echo "  访问地址:  http://<服务器IP>  (修改 k8s/ingress.yaml 的域名后)"
echo "=============================================="

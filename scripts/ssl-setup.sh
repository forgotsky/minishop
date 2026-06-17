#!/bin/bash
# ================================================================
# SSL 证书自动申请 & HTTPS 配置脚本
# 在 K3s 服务器上运行：bash scripts/ssl-setup.sh
# ================================================================

set -e

echo "=============================================="
echo "  1/3  安装 cert-manager"
echo "=============================================="
if kubectl get ns cert-manager &>/dev/null && kubectl -n cert-manager get deployment cert-manager &>/dev/null; then
  echo "✓ cert-manager 已安装，跳过"
else
  kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml
  echo "等待 cert-manager 就绪..."
  kubectl -n cert-manager wait --for=condition=available deployment/cert-manager --timeout=120s
  kubectl -n cert-manager wait --for=condition=available deployment/cert-manager-webhook --timeout=120s
  echo "✓ cert-manager 安装完成"
fi

echo ""
echo "=============================================="
echo "  2/3  创建 Let's Encrypt 颁发者"
echo "=============================================="
kubectl apply -f /opt/shop-app/k8s/issuer.yaml
sleep 3
echo "✓ ClusterIssuer 已创建"

echo ""
echo "=============================================="
echo "  3/3  更新 Ingress 开启 HTTPS"
echo "=============================================="
kubectl apply -f /opt/shop-app/k8s/ingress.yaml
echo "✓ Ingress 已更新"

echo ""
echo "=============================================="
echo "  等待证书签发..."
echo "=============================================="
sleep 10
kubectl get certificate -n shop
kubectl get certificaterequest -n shop
kubectl describe certificaterequest -n shop 2>/dev/null || true

echo ""
echo "=============================================="
echo "  SSL 配置完成！"
echo ""
echo "  查看证书状态:  kubectl get certificate -n shop"
echo "  等待状态变成 'True' 即可访问 https://renewshuttle.cn"
echo ""
echo "  如果超过 5 分钟还是 False:"
echo "  kubectl describe certificaterequest -n shop"
echo "  kubectl describe order -n shop"
echo "=============================================="

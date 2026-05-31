# MiniShop — 微信商城项目

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy / PostgreSQL 16 |
| 前端 | 微信小程序原生框架 (WXML + WXSS + JS) |
| 部署 | Docker → GitHub Container Registry → K3s |
| CI/CD | GitHub Actions (`.github/workflows/cd.yml`) |

## 项目结构

```
backend/                  ← FastAPI 后端
  app/
    main.py               ← API 路由、模型定义、业务逻辑
    models.py              ← SQLAlchemy 数据模型
    auth.py                ← JWT 认证
    db.py                  ← 数据库连接配置
  static/images/           ← 商品图片
  Dockerfile               ← 容器构建文件
  requirements.txt         ← Python 依赖

wechat-miniprogram/        ← 微信小程序前端
  pages/
    index/                 ← 首页（商品列表）
    product/               ← 商品详情
    cart/                  ← 购物车
    checkout/              ← 下单
    order/                 ← 订单列表
    order-detail/          ← 订单详情
    coupon/                ← 优惠券
    address/               ← 地址管理
    address-edit/          ← 地址编辑
  utils/api.js             ← API 请求封装（BASE_URL: https://renewshuttle.cn）
  app.js                   ← 启动入口、登录流程

k8s/                       ← K3s 部署清单
  app.yaml                 ← FastAPI Deployment + Service
  postgres.yaml            ← PostgreSQL Deployment + PVC + Service
  ingress.yaml             ← Traefik Ingress（域名 renewshuttle.cn）
  configmap.yaml           ← 环境变量配置
  secret.example.yaml      ← 密码 Secret 模板
  issuer.yaml              ← Let's Encrypt ClusterIssuer

scripts/
  k3s-setup.sh             ← 服务器 K3s 初始化
  ssl-setup.sh             ← SSL 证书安装
```

## 开发约定

- 后端代码风格：匹配现有代码，中文注释
- 前端兼容性：**禁止 `?.` 可选链**（微信小程序不支持），用 `(obj || {}).prop` 替代
- 前端兼容性：**禁止 `??` 空值合并**，用 `||` 替代
- Git：修改在 `simple` 分支，PR → `main` 触发 CI/CD
- K8s 命令：`kubectl` 对 K3s 就是 `kubectl`
- 数据库密码不写在代码里，通过 K8s Secret 注入

## 关键 URL

- 线上 API: `https://renewshuttle.cn`
- 服务器 IP: `43.156.92.63`
- K3s 集群: 单节点，K3s 内置 Traefik
- GitHub: `https://github.com/forgotsky/minishop`
- GHCR 镜像: `ghcr.io/forgotsky/minishop:latest`

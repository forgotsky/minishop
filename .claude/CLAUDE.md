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

## 编码准则 (Karpathy Guidelines)

以下准则旨在减少常见的 LLM 编码错误。对简单任务（单行修改、拼写错误）可灵活处理。

### 1. 先想后写

**不假设、不隐藏困惑、主动列出权衡方案。**

- 写代码前，先说明你的假设。如果不确定，直接问
- 有多个方案时，都列出来——不要默默选一个
- 有更简单的方法，直接说。该反对时反对
- 有不清楚的地方，停下来，把困惑说出来，问

### 2. 极简优先

**用最少代码解决问题。不写任何未经要求的逻辑。**

- 不加需求之外的功能
- 不为只用一次的代码建抽象层
- 不加没人要的"灵活性"和"可配置性"
- 不处理不可能发生的错误
- 写了 200 行但 50 行能搞定的，重写

自问：资深工程师会觉得这是过度设计吗？如果是，简化。

### 3. 精准修改

**只改你该改的。只清理你自己造成的垃圾。**

- 不顺手"改进"旁边的代码、注释、格式
- 不重构没坏的东西
- 匹配现有代码风格，即使你觉得你的写法更好
- 看到无关的遗留死代码，提出来——但别删
- 如果是你的修改导致某个 import/变量/函数不再使用，清理掉

检验标准：diff 里每一行改动都应该能追溯到用户的具体需求。

### 4. 目标驱动

**定义成功标准。循环直到验证通过。**

- "加个功能" → 先写测试，测试通过才算完成
- "修 bug" → 先写能复现的测试，修到测试通过
- "重构 X" → 重构前后测试都通过才算成功

多步骤任务先列计划：
```
1. [步骤] → 验证: [检查项]
2. [步骤] → 验证: [检查项]
3. [步骤] → 验证: [检查项]
```

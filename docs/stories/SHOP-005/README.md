# SHOP-005: 微信支付功能

## 概述

为 MiniShop 实现真实的微信支付 JSAPI 集成。用户下单后在小程序内调起微信支付完成付款，支付结果通过微信回调自动更新订单状态。支持 Dev（模拟支付）和 Prod（真实微信支付）双模式。

## 技术方案

- **微信支付 API v3** — RSA-SHA256 签名 + AES-256-GCM 加密
- **Dev/Prod 双模式** — `RUN_MODE=dev` 跳过真实支付 API
- **回调验签** — 时间戳防重放 + 金额校验
- **前端 `wx.requestPayment()`** — 小程序原生支付接口

## 文件变更

| 文件 | 变更 |
|------|------|
| `backend/app/wechat_pay.py` | **新建** — 微信支付核心服务 |
| `backend/app/main.py` | 修改 — 3 个支付 endpoint |
| `backend/app/models.py` | 修改 — Order 表 +2 字段 |
| `backend/app/auth.py` | 修改 — 支付环境变量 |
| `backend/requirements.txt` | 修改 — +cryptography |
| `wechat-miniprogram/utils/api.js` | 修改 — +wechatPay |
| `wechat-miniprogram/pages/order-detail/order-detail.js` | 修改 — 真实支付流程 |
| `wechat-miniprogram/pages/checkout/checkout.js` | 修改 — 下单后跳转 |
| `k8s/configmap.yaml` | 修改 — 支付配置 |
| `k8s/secret.example.yaml` | 修改 — 支付密钥 |
| `backend/tests/test_wechat_pay.py` | **新建** — 13 个测试 |

## API

### `POST /api/orders/{id}/pay`
- Dev 模式：直接标记 PAID
- Prod 模式：返回 400

### `POST /api/orders/{id}/wechat-pay`
- 调用微信 JSAPI 下单
- 返回 `{ appId, timeStamp, nonceStr, package, signType, paySign }`

### `POST /api/wechat-pay/notify`
- 微信支付回调
- 验签 + 解密 + 更新订单 + 金额校验

## 配置

```bash
# Dev 模式（默认）
RUN_MODE=dev  # 不需要微信商户号，模拟支付

# Prod 模式
RUN_MODE=prod
WECHAT_APPID=wxXXXXXXXXXX
WECHAT_MCHID=1234567890
WECHAT_PAY_API_V3_KEY=32位密钥
WECHAT_PAY_CERT_PATH=/etc/wechatpay/apiclient_key.pem
WECHAT_PAY_CERT_SERIAL=证书序列号
WECHAT_PAY_NOTIFY_URL=https://renewshuttle.cn/api/wechat-pay/notify
```

## 测试

```bash
cd backend && pytest tests/test_wechat_pay.py -v   # 13 passed
cd backend && pytest tests/ -v                       # 179 passed
```

## 详细文档

| 文档 | 路径 |
|------|------|
| URS | [1-urs.md](./1-urs.md) |
| Story 拆分 | [2-story.md](./2-story.md) |
| 架构设计 | [3-architecture.md](./3-architecture.md) |
| 测试报告 | [5-tests.md](./5-tests.md) |
| Code Review | [6-review.md](./6-review.md) |

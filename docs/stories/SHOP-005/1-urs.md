# SHOP-005 微信支付功能 — 用户需求规格说明书 (URS)

## 1. 功能概述 (Feature Summary)

将 MiniShop 当前的"模拟支付"替换为真实的微信支付集成。用户下单后调用微信支付 JSAPI，在小程序内完成支付，支付结果通过微信回调通知服务端。支持开发/生产双模式，dev 模式保持模拟支付以方便本地测试。

**目标用户**：所有有真实支付需求的下单用户。

## 2. 现状分析

| 现状 | 问题 |
|------|------|
| `POST /api/orders/{id}/pay` | 直接改状态为 PAID，无真实支付 |
| 前端 `api.payOrder()` | 调用 mock 接口，无支付流程 |
| 无微信支付 SDK 调用 | 用户实际无需付款 |
| 微信登录已有 APPID | 可复用，但支付需要额外的商户号 |

## 3. 用户故事 (User Stories)

| # | 角色 | 想做什么 | 以便 |
|---|------|---------|------|
| US-01 | 下单用户 | 点击"提交订单"后调起微信支付 | 在小程序内安全完成付款 |
| US-02 | 下单用户 | 支付成功后自动跳转到订单详情 | 查看已支付的订单 |
| US-03 | 下单用户 | 支付失败时看到明确提示 | 知道原因并重试 |
| US-04 | 回调系统 | 收到微信支付成功通知 | 自动更新订单状态为 PAID |
| US-05 | 开发者 | 在 dev 模式保持 mock 支付 | 本地开发调试不受影响 |

## 4. 验收标准 (Acceptance Criteria)

### AC-01: 微信支付调起
- **Given** 用户已创建待付款订单
- **When** 用户点击"立即支付"
- **Then** 调用 `wx.requestPayment()` 调起微信支付界面

### AC-02: 支付成功
- **Given** 用户在微信支付界面完成付款
- **When** 支付成功后
- **Then** 订单状态变为 PAID，显示支付成功，跳转订单详情

### AC-03: 支付回调
- **Given** 微信支付平台向服务端发送支付通知
- **When** 服务端接收到 `/api/wechat-pay/notify` POST 请求
- **Then** 验签通过后更新订单状态，记录 transaction_id 和支付时间

### AC-04: 支付失败/取消
- **Given** 用户在微信支付界面取消支付
- **When** 支付被取消
- **Then** 订单保持 PENDING 状态，提示用户可稍后重试

### AC-05: Dev 模式
- **Given** 服务端 `RUN_MODE=dev`
- **When** 用户触发支付
- **Then** 不调用微信 API，直接标记为 PAID（保持现有行为）

### AC-06: 重复支付保护
- **Given** 订单已经是 PAID 状态
- **When** 用户再次尝试支付
- **Then** 返回错误 "订单已支付"

## 5. 范围 (Scope)

### 包含 (In Scope)

| 项目 | 说明 |
|------|------|
| 微信支付 JSAPI 统一下单 | 服务端调用 /v3/pay/transactions/jsapi |
| 预支付参数生成 | 签名、nonceStr、timeStamp、package 等 |
| 支付回调接口 | `/api/wechat-pay/notify` |
| 签名验证 | 回调验签 + 应答 |
| 前端 `wx.requestPayment()` | 调起微信支付 |
| Dev 模式兼容 | `RUN_MODE=dev` 保持 mock 支付 |
| 新数据库字段 | `transaction_id`, `prepay_id` |
| 环境变量/Secret | `WECHAT_MCHID`, `WECHAT_PAY_API_V3_KEY`, `WECHAT_PAY_CERT_PATH` |

### 不包含 (Out of Scope)

| 项目 | 说明 |
|------|------|
| 退款功能 | 不实现退款 API |
| 企业付款/提现 | 不实现 |
| 支付分/代扣 | 不实现 |
| 微信支付分账 | 不实现 |
| 多商户号支持 | 单商户号 |
| 小程序支付以外的支付方式 | JSAPI only |

## 6. 依赖关系 (Dependencies)

### 前端依赖
- `pages/order-detail/order-detail.js` — `onPay()` 改为调用 WeChat Pay 流程
- `pages/checkout/checkout.js` — 支付成功后 redirect
- `utils/api.js` — 可能新增 `wechatPay(orderId)` API

### 后端依赖
- WeChat Pay API v3 SDK 或 httpx 调用
- 微信商户号 (mchid) + API v3 Key + 商户证书
- 公网可访问的回调 URL (`https://renewshuttle.cn/api/wechat-pay/notify`)

### K8s 依赖
- ConfigMap 增加 `WECHAT_MCHID`
- Secret 增加 `WECHAT_PAY_API_V3_KEY` + `wechatpay_cert.pem`

### 文件清单

| 文件 | 变更类型 |
|------|----------|
| `backend/app/main.py` | **大幅修改** — 支付相关 endpoint |
| `backend/app/models.py` | 修改 — Order 表新增字段 |
| `backend/app/auth.py` | 修改 — 支付相关环境变量 |
| `backend/requirements.txt` | 可能修改 — 加密库依赖 |
| `wechat-miniprogram/utils/api.js` | 修改 — 新增支付 API |
| `wechat-miniprogram/pages/order-detail/order-detail.js` | 修改 — 支付流程 |
| `wechat-miniprogram/pages/checkout/checkout.js` | 修改 — 下单后支付 |
| `k8s/configmap.yaml` | 修改 — 支付环境变量 |
| `k8s/secret.example.yaml` | 修改 — 支付密钥模板 |

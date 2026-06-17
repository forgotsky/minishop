# SHOP-005 微信支付功能 — Story 拆分

## 概述

| 字段 | 值 |
|------|-----|
| Story Key | SHOP-005 |
| 需求 | 微信支付功能 |
| 总预估工时 | **XL (10-14h)** |
| 涉及文件数 | **12+ 个** 跨前后端 + K8s |

---

## Story 拆分

### ST-005-01: Order 模型增加支付字段 + DB Migration `P0`

| 字段 | 值 |
|------|-----|
| 优先级 | **P0** — 数据层基础 |
| 工时 | **S (0.5h)** |
| 后端任务 | `models.py` 新增 `transaction_id`, `prepay_id` 列 |
| 前端任务 | 无 |

**具体工作**：
- `Order.transaction_id = Column(String(64), nullable=True)` — 微信交易单号
- `Order.prepay_id = Column(String(64), nullable=True)` — 微信预支付 ID
- 启动时自动 `create_all` 创建新列（已有机制）

---

### ST-005-02: WeChat Pay Service 模块 `P0`

| 字段 | 值 |
|------|-----|
| 优先级 | **P0** — 核心支付逻辑 |
| 工时 | **L (3h)** |
| 后端任务 | 新建 `backend/app/wechat_pay.py` |
| 前端任务 | 无 |

**具体工作**：
1. `WechatPayConfig` — 从环境变量读取 mchid, api_v3_key, cert 路径, appid, notify_url
2. `generate_nonce_str()` — 随机字符串
3. `generate_signature(method, url, timestamp, nonce_str, body)` — RSA256 签名
4. `create_jsapi_order(openid, order_no, amount, description)` — 调用 `/v3/pay/transactions/jsapi`
5. `verify_notify_signature(headers, body)` — 验签
6. `decrypt_notify_resource(ciphertext, nonce, associated_data)` — AES-256-GCM 解密
7. Dev 模式：返回 mock prepay_id
8. 返回前端调起支付需要的参数：`{ appId, timeStamp, nonceStr, package, signType, paySign }`

**依赖**：
- `cryptography` 库（用于 RSA 签名和 AES 解密）
- 商户号 + API v3 Key + 证书文件

---

### ST-005-03: 支付 API Endpoints `P0`

| 字段 | 值 |
|------|-----|
| 优先级 | **P0** |
| 工时 | **M (2h)** |
| 后端任务 | 修改 `main.py` |
| 前端任务 | 无 |

**具体工作**：

**3.1 `POST /api/orders/{order_id}/wechat-pay`**
- 验证订单属于当前用户 + 状态为 PENDING
- 调用 `wechat_pay.create_jsapi_order()`
- 保存 `prepay_id` 到订单
- 计算 `paySign`（二次签名给前端）
- 返回 prepay 参数

**3.2 `POST /api/wechat-pay/notify`** (无需认证)
- 读取 raw body
- 验签
- 解密 resource
- 更新订单状态：`PENDING → PAID`，记录 `transaction_id`
- 返回 `{ code: "SUCCESS", message: "成功" }`

**3.3 `POST /api/orders/{order_id}/pay` (保留兼容)**
- Dev 模式：直接标记 PAID（保持现有行为）
- Prod 模式：返回错误提示使用 /wechat-pay

---

### ST-005-04: 前端支付流程改造 `P1`

| 字段 | 值 |
|------|-----|
| 优先级 | **P1** |
| 工时 | **M (2h)** |
| 后端任务 | 无 |
| 前端任务 | 修改 `pages/order-detail/` + `utils/api.js` |

**具体工作**：
1. `utils/api.js` 新增：
   - `wechatPay(orderId)` → `POST /api/orders/{id}/wechat-pay`
2. `order-detail.js` `onPay()` 改造：
   - 调用 `api.wechatPay(orderId)`
   - 获取 prepay 参数
   - 调用 `wx.requestPayment({ timeStamp, nonceStr, package, signType, paySign, ... })`
   - 成功：Toast + 刷新订单
   - 失败：区分取消 vs 错误
3. `checkout.js` 支付流程：
   - 下单 → 直接跳转订单详情页（用户在那里支付）
   - 不在下单页自动调用支付

---

### ST-005-05: 支付状态 UI `P2`

| 字段 | 值 |
|------|-----|
| 优先级 | **P2** |
| 工时 | **S (0.5h)** |
| 后端任务 | `models.py` `CouponTemplate` `CouponType` `CouponStatus` |
| 前端任务 | 修改 `pages/order-detail/` + i18n |

**具体工作**：
- 订单详情页增加"支付中" loading 状态
- 支付按钮在 PROD 模式显示"微信支付"图标
- 支付成功后按钮消失，显示支付时间
- i18n 增加支付相关文本

---

### ST-005-06: K8s 配置更新 `P2`

| 字段 | 值 |
|------|-----|
| 优先级 | **P2** |
| 工时 | **S (0.5h)** |
| 后端任务 | K8s yaml 文件 |
| 前端任务 | 无 |

**具体工作**：
- `configmap.yaml` 增加 `WECHAT_MCHID`, `WECHAT_APPID`
- `secret.example.yaml` 增加 `WECHAT_PAY_API_V3_KEY`
- Secret 增加商户证书（base64 编码的 pem 文件）
- `app.yaml` 增加 secret volume mount for cert

---

### ST-005-07: 集成测试 `P2`

| 字段 | 值 |
|------|-----|
| 优先级 | **P2** |
| 工时 | **M (1.5h)** |
| 后端任务 | pytest + httpx |
| 前端任务 | 无 |

---

## 推荐实施顺序

```
ST-005-01 (DB) → ST-005-02 (Pay Service) → ST-005-03 (API)
→ ST-005-04 (Frontend) → ST-005-05 (UI) → ST-005-06 (K8s) → ST-005-07 (Tests)
```

## 风险提示

| 风险 | 等级 | 缓解 |
|------|------|------|
| 微信商户号未申请 | 🔴 高 | Prod 部署前需完成商户认证 |
| 回调 URL 需公网可达 | 🟡 中 | `renewshuttle.cn` 已具备 |
| 证书安全管理 | 🟡 中 | K8s Secret + 文件挂载 |
| 支付签名算法复杂 | 🟢 低 | 参考微信官方文档实现 |

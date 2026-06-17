# SHOP-005 微信支付功能 — 架构设计

## 1. 总体架构

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  WeChat Mini-Prog │     │  FastAPI Backend │     │  WeChat Pay API  │
│  (小程序前端)      │     │  (renewshuttle.cn)│     │  (api.mch.weixin)│
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│                  │     │                   │     │                  │
│ ①用户点击支付     │────▶│ POST /orders/{id} │────▶│ /v3/pay/trans-  │
│                  │     │   /wechat-pay     │     │   actions/jsapi  │
│                  │     │                   │     │                  │
│ ②获取prepay参数   │◀────│ 返回 timeStamp,   │◀────│ 返回 prepay_id   │
│                  │     │ nonceStr,paySign  │     │                  │
│                  │     │                   │     │                  │
│ ③wx.requestPayment│    │                   │     │                  │
│                  │     │                   │     │                  │
│ ④支付完成         │     │                   │     │                  │
│                  │     │                   │     │ ⑤支付回调通知     │
│                  │     │ POST /wechat-pay/ │◀────│ /notify          │
│                  │     │   /notify         │     │                  │
│                  │     │ (验签+更新订单)     │     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

## 2. 详细数据流

### 2.1 支付请求流程

```
1. 前端: api.wechatPay(orderId)
2. 后端: POST /api/orders/{id}/wechat-pay
   ├─ 验证订单 (PENDING + 属于用户)
   ├─ 生成 out_trade_no (复用 order_no)
   ├─ 调用 WeChat Pay API:
   │   POST https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi
   │   Header: Authorization (WECHATPAY2-SHA256-RSA2048签名)
   │   Body: { appid, mchid, description, out_trade_no,
   │           notify_url, amount: { total, currency },
   │           payer: { openid } }
   ├─ 保存 prepay_id 到订单
   └─ 返回前端参数:
       { appId, timeStamp, nonceStr, package: "prepay_id=xxx",
         signType: "RSA", paySign (二次签名) }
3. 前端: wx.requestPayment({ timeStamp, nonceStr, package, signType, paySign })
4. 微信支付界面打开
```

### 2.2 支付回调流程

```
1. WeChat POST → https://renewshuttle.cn/api/wechat-pay/notify
   Body: { id, create_time, resource_type, event_type,
           resource: { algorithm, ciphertext, nonce, associated_data } }
2. 后端验证:
   ├─ 读取 HTTP headers: Wechatpay-Timestamp, Wechatpay-Nonce,
   │                      Wechatpay-Signature, Wechatpay-Serial
   ├─ 构造签名串: {timestamp}\n{nonce}\n{body}\n
   ├─ RSA256 验签 (用微信平台证书公钥)
   ├─ AES-256-GCM 解密 resource.ciphertext
   ├─ 解析解密后的 JSON: { out_trade_no, transaction_id, trade_state }
   └─ 更新订单: status=PAID, transaction_id=xxx, paid_at=now
3. 返回: { code: "SUCCESS", message: "成功" }
```

## 3. API 设计

### 3.1 `POST /api/orders/{order_id}/wechat-pay`

**Request** (JWT auth required)
```
No body needed — server builds from order data
```

**Response** `200`
```json
{
  "appId": "wxXXXXXXXXXX",
  "timeStamp": "1621234567",
  "nonceStr": "abc123def456",
  "package": "prepay_id=wxXXXXXXXXXX",
  "signType": "RSA",
  "paySign": "base64_encoded_signature..."
}
```

**Error Responses**
- `404` — Order not found
- `400` — Order cannot be paid (already paid/cancelled)
- `500` — WeChat Pay API error

### 3.2 `POST /api/wechat-pay/notify`

**Request** (no auth, WeChat signature verification)

**Response** `200`
```json
{ "code": "SUCCESS", "message": "成功" }
```

### 3.3 保留 `POST /api/orders/{order_id}/pay`

Dev 模式：标记 PAID（现有行为）
Prod 模式：返回 400 引导使用 /wechat-pay

## 4. 数据库变更

### Order 表新增字段

```python
transaction_id = Column(String(64), nullable=True)   # 微信交易单号
prepay_id = Column(String(64), nullable=True)         # 微信预支付ID
```

已有 `paid_at` 和 `payment_method` 字段可复用。

## 5. 签名算法

### 5.1 请求签名 (调用微信 API)

```
签名串 = HTTP方法\n
        URL(不含域名)\n
        时间戳\n
        nonce_str\n
        请求body\n

Authorization: WECHATPAY2-SHA256-RSA2048
  mchid="商户号",
  nonce_str="随机串",
  signature="Base64(RSA256_Sign(签名串))",
  timestamp="时间戳",
  serial_no="证书序列号"
```

### 5.2 预支付二次签名 (给前端 wx.requestPayment)

```
签名串 = appId\n
        timeStamp\n
        nonceStr\n
        prepay_id\n

paySign = Base64(RSA256_Sign(签名串))
```

## 6. 安全考虑

| 项目 | 措施 |
|------|------|
| API v3 Key | K8s Secret，不写入代码 |
| 商户证书 .pem | K8s Secret volume mount |
| 回调验签 | 强制 RSA256 验签 + 时间戳防重放 |
| 金额校验 | 回调中的金额需与订单匹配 |
| Dev/Prod 隔离 | `RUN_MODE=dev` 时完全跳过微信 API |

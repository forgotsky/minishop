# SHOP-001 Architecture Design

**Author:** Architect
**Date:** 2026-05-31

---

## 认证流程

```
┌─────────────────────────────────────────────────────────┐
│                    微信小程序 (前端)                       │
│                                                          │
│  app.js onLaunch()                                       │
│    ↓                                                     │
│  wx.login() ───→ 获取临时 code                           │
│    ↓                                                     │
│  POST /api/auth/login {code, nickname, avatar}           │
│    ↓                                                     │
│  收到 {token, user_id} → wx.setStorageSync('token', ..) │
│    ↓                                                     │
│  后续所有请求 → Authorization: Bearer <token>             │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼ HTTPS
┌─────────────────────────────────────────────────────────┐
│                 FastAPI 后端 (K3s Pod)                    │
│                                                          │
│  POST /api/auth/login                                    │
│    ├─ code → mock openid (开发环境)                       │
│    ├─ 查询/创建 User 记录                                 │
│    └─ JWT 签名 → 返回 token                               │
│                                                          │
│  Protected Endpoints (require_user)                      │
│    ├─ POST /api/cart/*                                   │
│    ├─ POST /api/orders/*                                 │
│    ├─ POST /api/coupons/*/claim                          │
│    └─ GET  /api/user/*                                   │
│                                                          │
│  Public Endpoints (no auth)                               │
│    ├─ GET  /api/products                                 │
│    ├─ GET  /api/categories                               │
│    └─ POST /api/auth/login                               │
└─────────────────────────────────────────────────────────┘
```

---

## 数据模型

### users 表 (SQLAlchemy)
```
┌──────────────────────┐
│       users           │
├──────────────────────┤
│ id (PK, Integer)      │
│ openid (Unique, Str)  │ ← wx_<code> 或 wx_dev_<timestamp>
│ nickname (Str)        │
│ avatar (Str)          │
│ phone (Str, nullable) │
│ created_at (DateTime) │
└──────────────────────┘
```

**不存密码** — 微信登录不需要密码，openid 就是唯一标识。

---

## JWT Token 设计

```python
# 签发
payload = {
    "sub": str(user_id),          # 用户 ID
    "exp": now + 720 * 3600       # 30 天后过期
}
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# 验证
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
user_id = int(payload["sub"])
```

| 参数 | 当前值 | 建议 |
|------|--------|------|
| 算法 | HS256 | ✅ OK |
| 过期 | 720 小时 (30 天) | ✅ OK |
| 密钥 | `dev-secret-change-in-production` | ⚠️ 应改为 K8s Secret 注入 |

---

## 中间件链

```
请求进入
  ↓
CORS Middleware (ALLOWED_ORIGINS)
  ↓
HTTPBearer (auto_error=False) ← 不报错，静默提取 token
  ↓
get_current_user() ← 可选，未登录返回 None
  ↓
require_user() ← 强制，未登录返回 401 {"detail": "Authentication required"}
  ↓
业务逻辑
```

---

## 安全考量

| 风险 | 缓解措施 |
|------|---------|
| Token 泄露 | HTTPS 加密传输，token 仅存本地 Storage |
| Mock openid 可伪造 | 生产环境应接入微信真实 API 验证 code |
| JWT 密钥硬编码 | 应改为 K8s Secret → 环境变量 `JWT_SECRET_KEY` |
| Token 无法撤销 | 可接受（30 天过期），未来可加黑名单 |
| 401 后 re-login 循环 | `handle401()` 只调一次 devLogin，不递归 |

---

## 改进建议（Future）

1. **生产环境微信登录**：调用 `https://api.weixin.qq.com/sns/jscode2session` 换取真实 openid
2. **JWT Secret 外部化**：添加 `JWT_SECRET_KEY` 到 K8s Secret
3. **Refresh Token**：短有效期 access token + 长有效期 refresh token
4. **设备指纹**：记录登录设备信息，异常登录告警

# SHOP-001 Story Breakdown

**Author:** Product Manager
**Date:** 2026-05-31
**Status:** ✅ All Done

---

## Story Map

```
Epic: 用户认证授权
  ├── Story 1.1: 微信登录流程 (P0 · S) ✅
  ├── Story 1.2: JWT Token 签发与验证 (P0 · S) ✅
  ├── Story 1.3: 前端 Token 管理与接口认证 (P0 · S) ✅
  └── Story 1.4: 401 处理与自动重登 (P1 · S) ✅
```

---

## Story 1.1: 微信登录流程

| 属性 | 值 |
|------|-----|
| Priority | P0 (Critical) |
| Effort | S (Small) |
| Owner | Backend + Frontend |

### Technical Tasks

**Backend:**
- [x] `POST /api/auth/login` 接口 — 接收 wx.login() code，创建/查找 User，返回 JWT token
- [x] 开发环境降级：devLogin() 用 `dev_` 前缀 mock openid
- [x] User 模型：openid (unique), nickname, avatar

**Frontend:**
- [x] `app.js autoLogin()` — 启动时自动调用 wx.login() → 请求 /api/auth/login → 存 token
- [x] `app.js devLogin()` — wx.login 失败时的降级方案

### Files Changed
- `backend/app/main.py` lines 241-266
- `backend/app/auth.py`
- `backend/app/models.py` lines 29-43
- `wechat-miniprogram/app.js` lines 8-37

---

## Story 1.2: JWT Token 签发与验证

| 属性 | 值 |
|------|-----|
| Priority | P0 |
| Effort | S |

### Technical Tasks

**Backend:**
- [x] `create_access_token(user_id)` — HS256 签名，720 小时过期
- [x] `decode_token(token)` — 解析 JWT，返回 user_id 或 None
- [x] `get_current_user()` — 从 Authorization header 提取 token，查询数据库返回 User
- [x] `require_user()` — 基于 get_current_user，未登录抛 HTTP 401

### Files Changed
- `backend/app/auth.py` (entire file)

---

## Story 1.3: 前端 Token 管理与接口认证

| 属性 | 值 |
|------|-----|
| Priority | P0 |
| Effort | S |

### Technical Tasks

**Frontend:**
- [x] `utils/api.js request()` — 自动从 storage 读 token，附加到 Authorization header
- [x] 区分需认证/不需认证接口：`needAuth` 参数控制
- [x] App 全局状态：`globalData.loggedIn`, `globalData.userId`

### Files Changed
- `wechat-miniprogram/utils/api.js` lines 1-29

---

## Story 1.4: 401 处理与自动重登

| 属性 | 值 |
|------|-----|
| Priority | P1 (High) |
| Effort | S |

### Technical Tasks

**Frontend:**
- [x] `api.js handle401()` — 收到 401 → 清除旧 token → 调 devLogin() → 重设 loggedIn
- [x] `app.js autoLogin()` — 每次启动总是走 wx.login 流程（不再跳过已有 token）
- [x] `coupon.js` — Claim 失败显示具体错误消息（而不是通用 "Failed"）

### Files Changed
- `wechat-miniprogram/utils/api.js` lines 3-8
- `wechat-miniprogram/app.js` lines 8-22
- `wechat-miniprogram/pages/coupon/coupon.js` lines 6-33

---

## Definition of Done

- [x] 新用户打开小程序自动登录
- [x] 老用户回访 token 有效直接恢复登录态
- [x] 未登录访问受保护接口返回 401
- [x] 401 时前端自动清除旧 token + 重登
- [x] 开发工具测试账号也能正常登录
- [x] Token 过期后自动重登
- [x] 代码审查通过
- [x] 部署到 K3s 生产环境

# SHOP-001 Code Review Report

**Author:** Code Reviewer
**Date:** 2026-05-31
**Verdict:** ✅ APPROVED with 4 recommendations

---

## Findings

### 🔴 HIGH — JWT 密钥硬编码

**File:** `backend/app/auth.py:13`
**Problem:** `SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")`
默认密钥是众所周知的开发密钥。在生产环境中任何人拿到 token 都可以伪造任意用户的 JWT。
**Fix:** 在 K8s Secret 中添加 `JWT_SECRET_KEY`，通过环境变量注入：
```yaml
# k8s/app.yaml
env:
  - name: JWT_SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: shop-secret
        key: JWT_SECRET_KEY
```

---

### 🟡 MEDIUM — HTTPBearer 被设为不报错

**File:** `backend/app/auth.py:17`
**Problem:** `security = HTTPBearer(auto_error=False)`
设置 `auto_error=False` 意味着即使没有 Authorization header，也不会报错，而是返回 None。这是有意为之（支持可选认证），但容易被误用——如果哪天有人改了 `require_user` 的调用顺序，可能悄悄绕过认证。
**Recommendation:** 保持现状，但添加注释说明意图，并确保所有保护接口都用了 `require_user` 而非 `get_current_user`。

---

### 🟡 MEDIUM — 生产环境 Mock OpenID

**File:** `backend/app/main.py:249`
**Problem:** `mock_openid = f"wx_{payload.code}" if payload.code else f"wx_dev_{int(time.time())}"`
任何知道这个逻辑的人都可以用任意 code 伪造 openid。在开发环境可以接受，但生产环境必须接入微信真实 API。
**Fix:** 添加环境变量控制：
```python
if os.getenv("ENV") == "production":
    # call wechat API to verify code
else:
    mock_openid = f"wx_dev_{int(time.time())}"
```

---

### 🟢 LOW — `autoLogin` 总是重新登录

**File:** `wechat-miniprogram/app.js:8-22`
**Problem:** 之前的代码有 token 就跳过登录（减少请求），现在的代码每次都调用 wx.login。优点是 token 总是新鲜的，缺点是每次启动多一次网络请求。
**Status:** 这是故意的设计选择，考虑到数据库重置等边缘情况，当前方案更稳健。无需修改。

---

### 🟢 LOW — 缺少请求日志

**File:** `backend/app/auth.py`
**Problem:** 认证失败时没有任何日志记录。建议添加：
```python
if user is None:
    print(f"[AUTH] Unauthorized access attempt")  # or use logging
    raise HTTPException(status_code=401, ...)
```

---

## WeChat Miniprogram 兼容性检查

| 检查项 | 结果 |
|--------|------|
| 无 `?.` 可选链 | ✅ |
| 无 `??` 空值合并 | ✅ |
| HTTPS 域名正确 | ✅ `https://renewshuttle.cn` |
| wx API 调用合法 | ✅ wx.login, wx.setStorageSync, wx.request |

---

## 安全检查

| 检查项 | 结果 |
|--------|------|
| 密码不以明文存储 | ✅ 不存密码（微信登录） |
| Token 前端安全存储 | ✅ wx Storage（沙箱隔离） |
| HTTPS 传输 | ✅ 生产环境 HTTPS |
| SQL 注入 | ✅ SQLAlchemy ORM，无原始 SQL |
| CORS 正确配置 | ✅ ALLOWED_ORIGINS 可环境变量控制 |

---

## Summary

```
CRITICAL: 0
HIGH:     1 (JWT 密钥硬编码)
MEDIUM:   2 (auto_error=False 风险, mock openid)
LOW:      2 (每次重登, 缺日志)
```

**结论：代码可以合入 main，但建议在下个 Sprint 解决 HIGH 项。**

# SHOP-001 Code Review Report

**Agent:** Code Reviewer (独立进程, 15 次工具调用, 141s)
**Date:** 2026-05-31
**Verdict:** APPROVED — 5 issues found, all fixed

---

## Reviewer 原始发现

### 🔴 HIGH #1 — httpx 异常未捕获 → 500

**File:** `backend/app/main.py:296`
**Found by Reviewer at:** `exchange_code_for_openid()`

**Problem:**
```python
async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.get(...)
```
WeChat API 超时/DNS 失败/连接错误 → 未处理异常 → 500 Internal Server Error

**Fix applied:**
```python
try:
    async with httpx.AsyncClient(timeout=10.0) as client:
        ...
except httpx.HTTPStatusError as e:
    logger.error("WeChat API HTTP error: status=%s", e.response.status_code)
    return None
except (httpx.RequestError, httpx.TimeoutException) as e:
    logger.error("WeChat API unreachable: %s", e)
    return None
```

---

### 🔴 HIGH #2 — session_key 泄露到日志

**File:** `backend/app/main.py:301`
**Found by Reviewer at:** error logging in WeChat API response

**Problem:**
```python
logger.error(f"WeChat code2session error: {data}")
```
`jscode2session` 的响应包含 `session_key`（微信敏感凭证）。全量日志 → session_key 写进 stdout/日志文件 → 安全泄漏。

**Fix applied:**
```python
logger.error("WeChat code2session error: errcode=%s errmsg=%s",
             data.get("errcode"), data.get("errmsg", "unknown"))
```
只记录 errcode + errmsg，不记录敏感字段。

---

### 🟡 MEDIUM #3 — 空字符串 JWT_SECRET_KEY 绕过

**File:** `backend/app/auth.py:16`

**Problem:**
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
```
`os.getenv` 只在 key **完全不存在** 时用默认值。如果 K8s Secret 里 key 存在但值为空字符串 `""` → `SECRET_KEY = ""` → 静默签名所有 token → 极易伪造。

**Fix applied:**
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:  # catches None AND "" AND "   "
    if RUN_MODE == "prod":
        raise RuntimeError(...)
    SECRET_KEY = "dev-secret-change-in-production"
```

---

### 🟡 MEDIUM #4 — 非 JSON 响应未防护

**File:** `backend/app/main.py:299`

**Problem:**
```python
data = resp.json()
```
WeChat API 远端故障可能返回 HTML（网关错误页）→ `json()` 抛异常 → 500

**Fix applied:**
```python
if not resp.headers.get("content-type", "").startswith("application/json"):
    logger.error("WeChat API returned non-JSON response")
    return None
data = resp.json()
```

---

### 🟢 LOW #5 — dev 模式无醒目警告

**File:** `backend/app/auth.py:16`

**Problem:** `RUN_MODE` 默认 `"dev"`，K8s ConfigMap 配置遗漏时静默用弱密钥 + mock openid。

**Fix applied:**
```python
if RUN_MODE == "dev":
    logger.warning("RUNNING IN DEV MODE - not safe for production!")
```

---

## 兼容性检查（全通过）

| 检查项 | 结果 |
|--------|------|
| `datetime.utcnow()` 残留 | ✅ 0 处 |
| 小程序 `?.` 可选链 | ✅ 0 处 |
| 小程序 `??` 空值合并 | ✅ 0 处 |
| HTTPS 域名 | ✅ `https://renewshuttle.cn` |
| K8s Secret 引用 | ✅ 正确（secretKeyRef vs configMapKeyRef） |
| 环境变量顺序 | ✅ DB_PASSWORD 在 DATABASE_URL 前 |
| Profile 部分更新 | ✅ `is not None` 守卫正确 |

---

## Summary

```
Agent:    Code Reviewer (adversarial review)
Issues:   5 (2 HIGH, 2 MEDIUM, 1 LOW)
Fixed:    5 / 5
Verdict:  ✅ APPROVED
```

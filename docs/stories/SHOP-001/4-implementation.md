# SHOP-001 代码实现报告

**Agent:** Backend Dev (独立进程, 35 次工具调用, 180s)
**Date:** 2026-05-31
**Status:** ✅ Complete + Review fixes applied

---

## 变更清单（8 文件, 196 行新增）

| 文件 | 操作 | 行数 | 说明 |
|------|------|------|------|
| `backend/app/log_config.py` | **新建** | +34 | 集中化日志系统, LOG_LEVEL 环境变量 |
| `backend/app/auth.py` | 修改 | +28 | JWT 外部化, RUN_MODE, 空密钥检测, 401 日志 |
| `backend/app/main.py` | 修改 | +134 | WeChat API 路由, Profile 端点, 日志启动 |
| `k8s/app.yaml` | 修改 | +16 | JWT_SECRET_KEY 等 4 个新环境变量 |
| `k8s/configmap.yaml` | 修改 | +4 | RUN_MODE + WECHAT_APPID |
| `k8s/secret.example.yaml` | 修改 | +3 | JWT_SECRET_KEY + WECHAT_APP_SECRET |
| `wechat-miniprogram/utils/api.js` | 修改 | +4 | getProfile() + updateProfile() |
| `docs/stories/SHOP-001/5-review.md` | 修改 | +10 | Reviewer 发现记录 |

---

## 改进 1: JWT_SECRET_KEY 外部化

### Before (auth.py:13)
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
# 问题：生产环境静默使用弱密钥，无警告
```

### After
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    if RUN_MODE == "prod":
        raise RuntimeError("JWT_SECRET_KEY must be set in production mode")
    SECRET_KEY = "dev-secret-change-in-production"
    logger.warning("Using default JWT_SECRET_KEY - not safe for production!")
```
**效果**: 生产环境缺密钥 → CrashLoopBackOff（醒目）；dev 模式 → WARNING 日志

---

## 改进 2: 环境感知的微信 API 路由

### Before (main.py:278-306)
```python
# 永远 mock openid
mock_openid = f"wx_{payload.code}" if payload.code else f"wx_dev_{int(time.time())}"
```

### After
```python
async def exchange_code_for_openid(code: str) -> Optional[str]:
    if RUN_MODE != "prod":
        return f"wx_{code or 'dev_fallback'}"  # dev mock

    # Production: real WeChat API call
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(WECHAT_CODE2SESSION_URL, params=params)
            resp.raise_for_status()
            if not resp.headers.get("content-type", "").startswith("application/json"):
                return None
            data = resp.json()
    except httpx.HTTPStatusError:
        return None
    except (httpx.RequestError, httpx.TimeoutException):
        return None
    # ...
```
**效果**: dev 模式向后兼容 / prod 模式调用真实微信 API / 全异常路径覆盖

---

## 改进 3: Auth 日志系统

新增 `log_config.py` 集中管理日志：

```python
def setup_logging() -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))
    root.addHandler(handler)
```

**日志事件覆盖：**
- `auth.py`: Token 过期 vs 格式错误 → 区分日志 / 401 事件
- `main.py`: 登录成功/失败 / WeChat API 调用失败
- `on_startup`: 服务启动日志

---

## 改进 4: User Profile 端点

### 新增 API
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/user/profile` | require_user | 获取用户资料（openid 脱敏） |
| PUT | `/api/user/profile` | require_user | 更新昵称/头像（部分更新） |

### 前端 Stubs
```javascript
getProfile: () => request('GET', '/api/user/profile'),
updateProfile: (data) => request('PUT', '/api/user/profile', data),
```

---

## 部署说明

### 1. 更新 K8s Secret
```bash
kubectl -n shop delete secret shop-secret --ignore-not-found
kubectl -n shop create secret generic shop-secret \
  --from-literal=DB_PASSWORD="<your-db-password>" \
  --from-literal=POSTGRES_PASSWORD="<your-db-password>" \
  --from-literal=JWT_SECRET_KEY="<random-32-char-string>" \
  --from-literal=WECHAT_APP_SECRET="<your-wechat-app-secret>"
```

### 2. 更新 ConfigMap
```bash
kubectl apply -f k8s/configmap.yaml
```

### 3. 部署新镜像
CD pipeline 自动处理，或手动：
```bash
kubectl rollout restart deployment/shop-app -n shop
```

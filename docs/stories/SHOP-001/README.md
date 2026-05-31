# SHOP-001: 微信小程序用户登录认证授权

**Status:** ✅ Done | **Sprint:** Current | **Priority:** P0

---

## 概述

实现了微信小程序的完整认证授权流程：

- 用户打开小程序 → **自动静默登录**
- 后端签发 **JWT Token**（30 天有效）
- 受保护接口强制要求登录
- Token 过期或失效 → **自动重登**

---

## 产出文件

| Phase | 文件 | 作者 |
|-------|------|------|
| URS | [1-urs.md](1-urs.md) | BA |
| Story | [2-story.md](2-story.md) | PM |
| Architecture | [3-architecture.md](3-architecture.md) | Architect |
| Implementation | [4-implementation.md](4-implementation.md) | Developer |
| Code Review | [5-review.md](5-review.md) | Reviewer |

---

## 如何测试

### 开发者工具测试
1. 打开微信开发者工具，导入 `wechat-miniprogram` 项目
2. 确认 Console 无报错
3. 点"领券"按钮 → 应该正常领取（说明已登录）
4. 清缓存 → 重新编译 → 再点领券 → 应自动重登后成功

### API 直接测试
```bash
# 1. 登录获取 token
curl -X POST https://renewshuttle.cn/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"code":"test123","nickname":"测试用户"}'

# 2. 用 token 访问受保护接口
curl https://renewshuttle.cn/api/user/coupons \
  -H "Authorization: Bearer <token>"

# 3. 无 token 访问 → 应返回 401
curl https://renewshuttle.cn/api/user/coupons
```

---

## 关键 API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login` | No | 微信登录，返回 JWT token |

**Request:**
```json
{"code": "wx_login_code", "nickname": "User", "avatar": ""}
```

**Response:**
```json
{"token": "eyJ...", "user_id": 1, "nickname": "User"}
```

---

## Known Issues

1. ⚠️ **JWT 密钥硬编码** — `backend/app/auth.py:13`，生产环境应通过 K8s Secret 注入
2. 📝 **Mock OpenID** — 当前为开发模式，未接入微信真实 openid 验证
3. 📝 **缺登录日志** — 建议加 login/401 事件日志

---

## Screenshots Checklist

- [ ] 开发者工具 Console 无认证报错
- [ ] 网络请求 `/api/auth/login` 返回 200
- [ ] 受保护接口请求带 `Authorization` header
- [ ] 手动删 token → 重新打开 → 自动重建 token
